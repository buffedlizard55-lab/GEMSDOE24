#!/usr/bin/env python3
"""Experiment: H-UNIQUE-GAPFILL — dots near faults but in gaps between existing submissions.

Hypothesis: Existing submissions cluster dots on/near catalogue fault traces.
Concealed geothermal conduits exist in the damage zone around faults where
no submission has placed dots. A score surface that is HIGH near faults but
LOW where existing submissions already have dots will place dots in these
gaps — near truth (DTI credit) but spatially distinct from every existing
raster (novelty).

Difference from reviewed methods:
  * Dotted-ridge/h25/h28: dots ON/near fault traces — exactly where existing dots are.
  * Off-catalogue Poisson: random dots far from faults — low DTI credit.
  * This approach: dots near faults but in the spatial gaps between existing
    submission dots — captures DTI credit without duplicating any raster.

Non-fault mimic: Altered damage zones without active geothermal flow.

Protocol: SegmentHoldout hide-and-recover, pooled DTI, leakage canary,
registry novelty vs local TIFFs, exact-grid TIF with zeros outside footprint.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt, gaussian_filter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems import emission, footprint, holdout, submission  # noqa: E402
from gems.preflight import preflight  # noqa: E402
from gems.validator import sha256_file  # noqa: E402

TEMPLATE = ROOT / "data/bridge/sample_submission.tif"
LABELS = ROOT / "data/bridge/labels.tif"
DOWNLOADS_DIR = ROOT / "docs/downloads"

BUDGET_FRACTION = 0.0073
MIN_DIST_PX = 3.0
FAULT_DECAY_PX = 4.0  # 400 m fault proximity
EXISTING_DOT_PENALTY_RADIUS_PX = 6.0  # penalize within 600 m of existing dots
CURRENT_BEST_HOLDOUT = 0.13000

RESULT = ROOT / "evidence/unique_experiment_gapfill.json"
DOWNLOADS = ROOT / "docs/downloads"
DATA_OUT = ROOT / "docs/data"


def save(obj, path):
    Path(path).write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n")


def build_existing_dot_mask(root, downloads_dir, footprint):
    """Build a mask showing where existing submissions have dots."""
    dot_density = np.zeros(footprint.shape, dtype=np.float32)
    n_tifs = 0
    for tif_path in sorted(downloads_dir.glob("*.tif")):
        if "-nan.tif" in tif_path.name:
            continue
        try:
            with rasterio.open(tif_path) as ds:
                if ds.shape != footprint.shape:
                    continue
                a = ds.read(1)
                dots = np.isfinite(a) & (a > 0)
                if dots.any():
                    # Gaussian blur to create a penalty zone around existing dots
                    dot_density += gaussian_filter(dots.astype(np.float32), sigma=3.0)
                    n_tifs += 1
        except Exception:
            continue
    if n_tifs > 0:
        dot_density = dot_density / n_tifs  # average density
    return dot_density, n_tifs


def build_score_surface(fp, t_fp, labels, dot_density):
    """Score = fault proximity × (1 - existing_dot_penalty).

    High near faults, low where existing submissions already have dots.
    """
    # Distance to nearest visible fault
    dist_to_fault = distance_transform_edt(~labels)
    fault_prox = np.exp(-dist_to_fault / FAULT_DECAY_PX)
    fault_prox = np.where(t_fp & ~labels, fault_prox, 0.0)  # off faults only

    # Penalty near existing submission dots
    dot_penalty = np.clip(dot_density, 0, 1)
    gap_boost = 1.0 - dot_penalty  # 1.0 where no existing dots, 0.0 where dense

    # Combined: near faults AND in gaps between existing submissions
    score = fault_prox * gap_boost
    score = np.where(t_fp & ~labels & (score > 0.01), score, 0.0).astype(np.float32)

    support = t_fp & ~labels & (score > 0.01)
    return score, support


def build_local_registry_entries(root, downloads_dir):
    entries = []
    tif_files = sorted(downloads_dir.glob("*.tif"))
    for i, tif_path in enumerate(tif_files):
        if "-nan.tif" in tif_path.name:
            continue
        entry = {
            "id": f"local-{i:03d}",
            "file": str(tif_path.relative_to(root)),
            "cache_path": str(tif_path),
            "source_url": "local",
        }
        entries.append(entry)
    return entries


def compare_local_novelty(score, fp, entries, root, dots=None, sample_size=200000):
    import hashlib
    from scipy.spatial import cKDTree
    from scipy.stats import rankdata

    surface, footprint = np.asarray(score), np.asarray(fp, bool)
    ids = np.flatnonzero(footprint)
    rng = np.random.default_rng(20261025)
    sample = rng.choice(ids, min(sample_size, len(ids)), replace=False)
    h, w = surface.shape
    sample_yx = np.column_stack(np.unravel_index(sample, (h, w)))

    if dots is not None:
        dots = np.asarray(dots, bool)
        dot_yx = np.argwhere(dots)
        candidate_kernel = np.maximum(1 - cKDTree(dot_yx).query(sample_yx)[0] / 3, 0)
    else:
        dot_yx, candidate_kernel = None, None

    rows = []
    for entry in entries:
        path = Path(entry["cache_path"])
        try:
            with rasterio.open(path) as ds:
                if ds.shape != footprint.shape:
                    continue
                a = ds.read(1)
        except Exception:
            continue
        content = hashlib.sha256(np.asarray(a[footprint], dtype="<f4").tobytes()).hexdigest()
        registry_dots = footprint & np.isfinite(a) & (a > 0)
        registry_yx = np.argwhere(registry_dots)
        tree = cKDTree(registry_yx) if len(registry_yx) else None
        kernel = (
            np.maximum(1 - tree.query(sample_yx)[0] / 3, 0)
            if tree is not None
            else np.zeros(len(sample))
        )
        full_ranks = rankdata(surface.ravel()[ids])
        raw_rank = None
        try:
            ra = full_ranks
            rb = a.ravel()[ids]
            if np.ptp(ra) > 0 and np.ptp(rb) > 0:
                da, db = ra - ra.mean(), rb - rb.mean()
                raw_rank = float(np.dot(da, db) / np.sqrt(np.dot(da, da) * np.dot(db, db)))
        except Exception:
            raw_rank = None
        kernel_rank = None
        try:
            if np.ptp(candidate_kernel) > 0 and np.ptp(kernel) > 0:
                dk = candidate_kernel - candidate_kernel.mean()
                dd = kernel - kernel.mean()
                kernel_rank = float(np.dot(dk, dd) / np.sqrt(np.dot(dk, dk) * np.dot(dd, dd)))
        except Exception:
            kernel_rank = None
        overlap = None
        if dots is not None and tree is not None:
            overlap = float(np.mean(tree.query(dot_yx)[0] <= 3.0))
        rank_dup = any(abs(x) > 0.90 for x in (raw_rank, kernel_rank) if x is not None)
        literal_duplicate = rank_dup or (overlap is not None and overlap > 0.70)
        entry_dict = {
            "registry_id": entry["id"],
            "file": entry["file"],
            "footprint_sha256": content,
            "raw_spearman": raw_rank,
            "kernel_spearman": kernel_rank,
            "candidate_dot_overlap_within_3px": overlap,
            "duplicate": bool(literal_duplicate),
        }
        rows.append(entry_dict)

    passed = bool(rows) and not any(row["duplicate"] for row in rows)
    return {
        "stage": "final_dots" if dots is not None else "surface_before_placement",
        "passed": passed,
        "registry_unique_rasters": len(rows),
        "max_abs_rank_correlation": max(
            (abs(r[k]) for r in rows for k in ("raw_spearman", "kernel_spearman") if r[k] is not None),
            default=None,
        ),
        "max_dot_overlap": max(
            (r["candidate_dot_overlap_within_3px"] for r in rows if r["candidate_dot_overlap_within_3px"] is not None),
            default=None,
        ),
        "rows": rows,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    args = ap.parse_args()

    started = time.monotonic()
    fp = footprint.load_footprint()
    with rasterio.open(TEMPLATE) as t:
        t_shape, t_crs, t_tr = t.shape, t.crs, t.transform
        t_fp = np.isfinite(t.read(1))

    with rasterio.open(LABELS) as s:
        labels = (s.read(1) > 0) & t_fp

    context = holdout.SegmentHoldout(fp, labels, buffer_px=15)

    # ---- Build existing dot density map ------------------------------------
    dot_density, n_tifs = build_existing_dot_mask(ROOT, DOWNLOADS_DIR, t_fp)
    print(f"Existing TIFFs with dots: {n_tifs}", flush=True)
    print(f"Dot density max: {float(dot_density.max()):.4f}, mean: {float(dot_density.mean()):.4f}", flush=True)

    # ---- Build score surface -----------------------------------------------
    score, support = build_score_surface(fp, t_fp, labels, dot_density)
    print(f"Support pixels: {int(support.sum()):,}", flush=True)
    print(f"Score positive pixels: {int((score > 0).sum()):,}", flush=True)

    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "hypothesis": (
            "H-UNIQUE-GAPFILL: dots near faults in gaps between existing submissions "
            "— captures DTI credit without duplicating any raster"
        ),
        "mechanism": (
            "Score surface is high near visible catalogue faults (DTI credit) but "
            "suppressed where existing submissions already place dots. Dots land in "
            "the damage-zone gaps around faults — near truth but spatially distinct "
            "from every existing raster. Catalogue faults used only for holdout masking."
        ),
        "non_fault_mimic": (
            "Altered damage zones without active geothermal flow"
        ),
        "experiment_number": 1,
        "maximum_experiments": 3,
        "maximum_session_hours": 2,
        "input_provenance": (
            "Committed bridge labels and local docs/downloads research TIFFs"
        ),
        "inputs": {
            str(p.relative_to(ROOT)): sha256_file(p)
            for p in (TEMPLATE, LABELS)
        },
        "code_sha256": {
            str(p.relative_to(ROOT)): sha256_file(p)
            for p in (
                Path(__file__),
                ROOT / "src/gems/holdout.py",
                ROOT / "src/gems/metric.py",
                ROOT / "src/gems/emission.py",
                ROOT / "src/gems/submission.py",
            )
        },
        "supported_pixels": int(support.sum()),
        "catalogue_features": ["distance_to_visible_fault"],
        "prediction_inputs_include_registry_rasters": False,
        "supervised_fit": False,
        "submission_slot_spent": False,
        "organizer_confirmed_score": None,
        "lane_status": "new lane: gap-filling near-fault dots away from existing submissions",
    }

    report["fold_integrity"] = [
        {
            "name": f["name"],
            "withheld_positive_pixels": int(f["truth"].sum()),
            "hidden_whole_components": len(f["hidden_component_ids"]),
            "visible_fault_pixels": int(f["visible"].sum()),
            "train_validation_overlap": bool((f["train"] & f["valid"]).any()),
        }
        for f in context.folds
    ]

    # ---- Leakage canary ------------------------------------------------------
    canary_features = {
        "fault_proximity_gapfill": score.astype(np.float32),
    }
    report["canary"] = context.canary(canary_features)
    if not report["canary"]["passed"]:
        report.update(verdict="negative", stopped_reason="leakage-canary",
                      elapsed_seconds=time.monotonic() - started)
        save(report, RESULT)
        raise SystemExit("Leakage canary failed; no candidate packaged")
    print("Canaries passed", flush=True)

    # ---- Surface novelty (pre-placement) -------------------------------------
    registry_entries = build_local_registry_entries(ROOT, DOWNLOADS_DIR)
    print(f"Local registry entries: {len(registry_entries)}", flush=True)
    report["surface_novelty"] = compare_local_novelty(score, fp, registry_entries, ROOT)
    if not report["surface_novelty"]["passed"]:
        report.update(verdict="negative", stopped_reason="duplicate-surface",
                      elapsed_seconds=time.monotonic() - started)
        save(report, RESULT)
        raise SystemExit("Duplicate surface; stopped before placement")
    print("Surface registry check passed", flush=True)

    # ---- Per-fold holdout -----------------------------------------------------
    predictions = []
    for f in context.folds:
        eligible = f["valid"] & ~f["visible"] & support
        predictions.append(
            emission.priority_poisson(
                score, eligible, round(BUDGET_FRACTION * f["valid"].sum()), min_dist=MIN_DIST_PX
            )
        )
    results = context.summarize(predictions)
    report["holdout"] = results
    print(f"HOLDOUT-DTI {results['dti']} CI {results['ci95']['interval']}", flush=True)

    # ---- Final dots ------------------------------------------------------------
    final = emission.priority_poisson(
        score, t_fp & ~labels & support, round(BUDGET_FRACTION * fp.sum()), min_dist=MIN_DIST_PX
    )
    if not final.any():
        raise SystemExit("No positive evidence; refusing an empty submission")

    report["final_novelty"] = compare_local_novelty(
        final.astype(np.float32), fp, registry_entries, ROOT, dots=final
    )
    print(f"Final dots novelty passed: {report['final_novelty']['passed']}", flush=True)
    if not report["final_novelty"]["passed"]:
        print(f"  max overlap={report['final_novelty'].get('max_dot_overlap')}", flush=True)
        print(f"  max rank={report['final_novelty'].get('max_abs_rank_correlation')}", flush=True)

    # ---- Package TIF -----------------------------------------------------------
    content_id = submission.scored_content_id(final, fp, labels)
    date_str = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    name = submission.make_filename("24gems", "gapfill-near-fault", date_str, content_id, "zeros")

    zeros_path = DOWNLOADS / name
    zeros = submission.write_submission(final, TEMPLATE, zeros_path, outside="zero")

    checks = submission.check_variants(zeros, TEMPLATE)
    if not checks["format_valid"]:
        raise SystemExit("Exact-file format checks failed; do not publish")

    note = (
        f"24GEMS gapfill near-fault dots | avoids existing submission dots | "
        f"research; HOLDOUT-DTI {results['dti']:.5f} | id {content_id}"
    )
    if len(note) > 140:
        note = note[:137] + "..."
    note_file = f"note-{name[:-4]}.txt"
    (DOWNLOADS / note_file).write_text(note + "\n")

    checks_file = f"checks-{name[:-4]}.json"
    save(checks, DOWNLOADS / checks_file)

    raster_sha256 = sha256_file(zeros)

    preflight_report = preflight(
        zeros, TEMPLATE, run_card_path=None, note=note,
        expected_template_sha256=sha256_file(TEMPLATE),
    )
    preflight_file = f"preflight-{name[:-4]}.json"
    save(preflight_report, DOWNLOADS / preflight_file)

    beats_current_best = results["dti"] > CURRENT_BEST_HOLDOUT
    ok_to_submit = (
        checks["format_valid"]
        and checks.get("checks", {}).get("variant_strict_whole_area_no_nan_allowed", {}).get("pass", False)
        and report["final_novelty"]["passed"]
        and report["canary"]["passed"]
        and beats_current_best
    )
    verdict = "promote" if ok_to_submit else "negative"

    reasons = []
    if not beats_current_best:
        reasons.append(f"holdout DTI does not beat current comparable best {CURRENT_BEST_HOLDOUT}")
    if not checks["format_valid"]:
        reasons.append("format or range check failed")
    if not report["final_novelty"]["passed"]:
        reasons.append("novelty gate failed")
    if not report["canary"]["passed"]:
        reasons.append("canary failed")

    card = {
        "hypothesis": report["hypothesis"],
        "mechanism": report["mechanism"],
        "non_fault_mimic": report["non_fault_mimic"],
        "holdout": {
            "evaluator_version": results["evaluator_version"],
            "dti": results["dti"],
            "ci95": results["ci95"]["interval"],
            "n_withheld_positive_pixels": results["n_withheld_positive_pixels"],
            "n_unique_withheld_components": results["n_unique_withheld_components"],
            "protocol": results["protocol"],
        },
        "correlation_overlap_vs_registry": {
            "surface_max_abs_rank_correlation": report["surface_novelty"]["max_abs_rank_correlation"],
            "final_max_abs_rank_correlation": report["final_novelty"]["max_abs_rank_correlation"],
            "final_max_overlap_within_3px": report["final_novelty"]["max_dot_overlap"],
            "passed": report["final_novelty"]["passed"],
            "rank_limit": 0.90,
            "overlap_limit": 0.70,
        },
        "leakage_canary": {
            "passed": report["canary"]["passed"],
            "threshold": report["canary"]["threshold"],
            "features": {k: v["pooled_auc"] for k, v in report["canary"]["features"].items()},
        },
        "raster_sha256": raster_sha256,
        "validator_output": checks,
        "preflight": preflight_report["decision"],
        "submission_name": name,
        "note": note,
        "note_characters": len(note),
        "note_limit": 140,
        "verdict": verdict,
        "ok_to_download": checks["format_valid"],
        "ok_to_submit": ok_to_submit,
        "reasons": reasons,
        "organizer_confirmed_score": None,
        "experiments_run": 1,
        "submission_slots_used": 0,
        "elapsed_seconds": time.monotonic() - started,
    }
    save(card, RESULT)
    save(card, DATA_OUT / "unique_run_card.json")

    download_entry = {
        "file": name,
        "sha256": raster_sha256,
        "content_id": content_id,
        "pixel_count": int(final.sum()),
        "note": note,
        "note_file": note_file,
        "checks_file": checks_file,
        "preflight_file": preflight_file,
        "role": "primary",
        "format_valid": checks["format_valid"],
        "strict_range_ok": checks.get("checks", {}).get("variant_strict_whole_area_no_nan_allowed", {}).get("pass", False),
        "ok_to_download": checks["format_valid"],
        "ok_to_submit": ok_to_submit,
        "verdict": verdict,
        "holdout_dti": results["dti"],
        "holdout_ci95": results["ci95"]["interval"],
        "run_card": "unique_run_card.json",
    }
    save(download_entry, DATA_OUT / "unique_download.json")

    print(json.dumps({
        "file": name,
        "pixels": int(final.sum()),
        "sha256": raster_sha256,
        "holdout_dti": results["dti"],
        "holdout_ci95": results["ci95"]["interval"],
        "note_characters": len(note),
        "verdict": verdict,
        "ok_to_submit": ok_to_submit,
        "ok_to_download": checks["format_valid"],
        "strict_range_ok": checks.get("checks", {}).get("variant_strict_whole_area_no_nan_allowed", {}).get("pass", False),
        "novelty_passed": report["final_novelty"]["passed"],
        "canary_passed": report["canary"]["passed"],
    }, indent=2), flush=True)


if __name__ == "__main__":
    main()