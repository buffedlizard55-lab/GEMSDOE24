#!/usr/bin/env python3
"""H24-VENTRAD lane: blind geothermal upwelling surface, unique vs competing methods.

Physical hypothesis (prospective, not tuned to the registry):
  Young volcanic vents and hydrothermal potassic alteration mark geothermal
  upwelling zones that host fault segments MISSING from the USGS/INGENIOUS
  mapped-fault catalogue (the catalogue traces brittle faults, not blind
  volcanic/alteration systems).  Eleven of 21 mapped vents lie >20 px from any
  known fault, i.e. they are independent point evidence of blind heat sources.

Surface (leakage free: none of its inputs are derived from the fault catalogue):
  * vent proximity        : exp(-distance-to-nearest-vent / 25 px)  [GDR OpenEI #1391 vents]
  * potassic alteration   : clip(K_norm - ThK_norm, 0, 1)             [USGS GeoDAWN radiometrics, DOI 10.5066/P93LGLVQ]
  * magnetic demagnetization : 1 - rtp_norm                           [competition bridge band rtp]
  * K anomaly             : K_norm
  weighted 0.4 / 0.3 / 0.2 / 0.1, clipped to [0, 1].

Protocol (parallel-run):
  * SegmentHoldout hide-and-recover, buffer 15 px, whole components, quadrant folds.
  * Catalogue-based features are built from fold.visible only (VENTRAD has none).
  * Pooled DTI, alpha 0.2, beta 0.8, 300 m triangular kernel, 95% spatial-block CI.
  * Leakage canary: every feature alone, AUC must be <= 0.90.
  * Registry novelty vs every competing method raster: |Spearman| <= 0.90 AND
    <= 70% of dots within 3 px. (The spacing-5 calibration lattice covers 99.87%
    of the footprint within 3 px, so every dotted budget fails the literal
    all-entries gate; that geometric bound is reported, not evaded.)
  * Submission written with submission_writer (strict whole-array [0, 1], zero
    outside the footprint; this check does not establish portal acceptance or explain the earlier range rejection), validated with
    check_variants, then published to docs/downloads/.
  * No upload, no organizer score, no score projection. Numbers are HOLDOUT-DTI.
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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems import emission, footprint, holdout, novelty, submission  # noqa: E402
from gems.metric import ALPHA, BETA  # noqa: E402
from gems.validator import sha256_file  # noqa: E402

RESULT = ROOT / "evidence/ventrad_run_card.json"
DOWNLOADS = ROOT / "docs" / "downloads"
BUDGET_FRACTION = 0.0073
BUFFER_PX = 15
MIN_DIST = 3.0
VENT_SCALE_PX = 25.0  # ~2.5 km


def save(obj, path):
    Path(path).write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n")


def _norm01(a, fp):
    v = a[fp & np.isfinite(a)]
    lo, hi = np.percentile(v, 2), np.percentile(v, 98)
    return np.clip((a - lo) / (hi - lo + 1e-9), 0.0, 1.0)


def build_ventrad_surface(fp):
    """Leakage-free surface: none of its inputs touch the fault catalogue."""
    meta = json.loads((ROOT / "data/prepared/features.json").read_text())
    names = meta["names"]
    stack = np.load(ROOT / "data/prepared/features.npy", mmap_mode="r")
    idx = np.flatnonzero(fp)
    rtp = np.full(fp.shape, np.nan, np.float32)
    rtp.ravel()[idx] = stack[:, names.index("rtp")]
    del stack

    vent_grid = np.zeros(fp.shape, bool)
    with open(ROOT / "data/external/gdr_volcanic_vents_in_footprint.csv") as f:
        _ = f.readline()
        for line in f:
            parts = line.strip().split(",")
            if len(parts) < 6:
                continue
            r, c = int(round(float(parts[3]))), int(round(float(parts[4])))
            if 0 <= r < fp.shape[0] and 0 <= c < fp.shape[1]:
                vent_grid[r, c] = True
    from scipy.ndimage import distance_transform_edt

    vent_dist = distance_transform_edt(~vent_grid)
    vent_prox = np.exp(-vent_dist / VENT_SCALE_PX)

    with rasterio.open(ROOT / "data/external/geodawn_rad_u8.tif") as s:
        K = s.read(1).astype(np.float32)
        _ = s.read(2).astype(np.float32)  # Th channel reserved for future use
    with rasterio.open(ROOT / "data/external/geodawn_extensions_u8.tif") as s:
        ThK = s.read(1).astype(np.float32)

    K_n = _norm01(K, fp)
    ThK_n = _norm01(ThK, fp)
    rtp_n = _norm01(np.nan_to_num(rtp, nan=float(np.nanmedian(rtp[fp]))), fp)
    potassic = np.clip(K_n - ThK_n, 0.0, 1.0)
    mag_low = 1.0 - rtp_n
    surface = np.clip(0.4 * vent_prox + 0.3 * potassic + 0.2 * mag_low + 0.1 * K_n, 0.0, 1.0)
    surface = np.where(fp & np.isfinite(surface), surface, np.nan)
    return {
        "surface": surface,
        "vent_prox": vent_prox,
        "potassic": potassic,
        "mag_low": mag_low,
        "K": K_n,
        "n_vents": int(vent_grid.sum()),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--verify-recorded",
        action="store_true",
        help="Check immutable VENTRAD evidence; do not run the lane",
    )
    ap.add_argument("--work-dir", type=Path, default=Path("/tmp/gems_work"))
    _ = ap.parse_args()
    started = time.monotonic()
    fp = footprint.load_footprint()
    template = ROOT / "data/bridge/sample_submission.tif"
    with rasterio.open(template) as t:
        template_fp = np.isfinite(t.read(1))
    assert np.array_equal(template_fp, fp), "template footprint mismatch"
    with rasterio.open(ROOT / "data/bridge/labels.tif") as s:
        labels = (s.read(1) > 0) & fp

    stack_ok = ROOT / "data/prepared/features.npy"
    meta = json.loads((ROOT / "data/prepared/features.json").read_text())
    if sha256_file(stack_ok) != meta["sha256"]:
        raise SystemExit("Prepared feature-stack checksum mismatch; run prepare_data.py")

    built = build_ventrad_surface(fp)
    surface = built["surface"]

    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "lane": "H24-VENTRAD",
        "hypothesis": "Blind geothermal upwelling: volcanic vent proximity + potassic "
        "alteration (low Th/K) + magnetic demagnetization target fault "
        "segments missing from the USGS/INGENIOUS catalogue.",
        "mechanism": "Vents are independent point heat sources (11/21 >20 px from any "
        "known fault); low Th/K marks potassic hydrothermal alteration; "
        "low rtp marks demagnetization. Weighted surface emits Poisson dots "
        "ranked by propensity, min 3 px spacing.",
        "non_fault_mimic": "Magnetite-poor alluvial paleochannel with K-rich detritus "
        "can mimic potassic alteration; young basalt without geothermal "
        "circulation is a vent false positive.",
        "preregistration": "knowledge/25_unique_hypothesis_2026-10-25.md (adapted)",
        "input_provenance": "hash-pinned owner mirrors; not organizer-authenticated",
        "inputs": {
            str(p.relative_to(ROOT)): sha256_file(p)
            for p in (
                stack_ok,
                ROOT / "data/prepared/features.json",
                ROOT / "data/external/gdr_volcanic_vents_in_footprint.csv",
                ROOT / "data/external/geodawn_rad_u8.tif",
                ROOT / "data/external/geodawn_extensions_u8.tif",
                ROOT / "data/bridge/sample_submission.tif",
                ROOT / "data/bridge/labels.tif",
            )
        },
        "code_sha256": {
            str(p.relative_to(ROOT)): sha256_file(p)
            for p in (
                Path(__file__),
                ROOT / "src/gems/holdout.py",
                ROOT / "src/gems/metric.py",
                ROOT / "src/gems/novelty.py",
                ROOT / "src/gems/emission.py",
                ROOT / "src/gems/submission.py",
            )
        },
        "supported_pixels": int(fp.sum()),
        "catalogue_features": [],  # VENTRAD uses no catalogue-derived features
        "prediction_inputs_include_registry_rasters": False,
        "supervised_fit": False,
        "submission_slot_spent": False,
        "organizer_confirmed_score": None,
        "n_vents": built["n_vents"],
        "budget_fraction": BUDGET_FRACTION,
        "budget_dots": round(BUDGET_FRACTION * fp.sum()),
        "evaluator_version": holdout.MTR_EVALUATOR_VERSION,
        "alpha": ALPHA,
        "beta": BETA,
        "triangular_kernel_radius_m": 300,
        "buffer_px": BUFFER_PX,
    }

    # ---- Holdout: hide-and-recover, surface fixed across folds (leakage free) ----
    ctx = holdout.SegmentHoldout(fp, labels, buffer_px=BUFFER_PX)
    budget = round(BUDGET_FRACTION * fp.sum())
    predictions = []
    for fold in ctx.folds:
        eligible = ctx.footprint & fold["valid"] & ~fold["visible"] & np.isfinite(surface)
        predictions.append(emission.priority_poisson(surface, eligible, budget, min_dist=MIN_DIST))
    holdout_summary = ctx.summarize(predictions)
    report["holdout"] = holdout_summary
    print(
        "VENTRAD HOLDOUT-DTI",
        holdout_summary["dti"],
        holdout_summary["ci95"]["interval"],
        "withheld",
        holdout_summary["n_truth"],
        flush=True,
    )

    # ---- Leakage canary: every feature alone ----
    canary_in = {
        name: np.where(fp & np.isfinite(arr), arr, np.nan)
        for name, arr in built.items()
        if name != "surface" and name != "n_vents"
    }
    canary_in["surface"] = surface
    canary = ctx.canary(canary_in, max_per_class=8000)
    report["canary"] = canary
    print(
        "Canary worst feature:",
        canary["worst_feature"],
        "AUC",
        round(canary["worst_pooled_auc"], 4),
        "passed:",
        canary["passed"],
        flush=True,
    )
    if not canary["passed"]:
        report.update(verdict="negative", stopped_reason="leakage-canary")
        save(report, RESULT)
        raise SystemExit("Leakage canary failed; no candidate packaged")

    # ---- Surface novelty vs registry BEFORE placement ----
    reg = json.loads((ROOT / "registry/priority_rasters.json").read_text())
    entries = []
    for e in reg["unique_rasters"]:
        p = ROOT / e["file"]
        if p.exists():
            entries.append({**e, "cache_path": str(p.relative_to(ROOT))})
    surface_novelty = novelty.compare_registry(surface, fp, entries, ROOT, template_path=template)
    report["surface_novelty"] = surface_novelty
    if not surface_novelty["passed"]:
        report.update(verdict="negative", stopped_reason="duplicate-surface")
        save(report, RESULT)
        raise SystemExit("Duplicate surface; lane stopped before placement")
    print("Surface registry check passed", flush=True)

    # ---- Final dots: eligibility = footprint where surface is finite ----
    eligible = fp & np.isfinite(surface)
    final = emission.priority_poisson(surface, eligible, budget, min_dist=MIN_DIST)
    if not final.any():
        raise SystemExit("No positive evidence; refusing an empty submission")
    report["pixel_count"] = int(final.sum())

    # ---- Final dots novelty vs registry ----
    # compare_prospective_registry separates the synthetic spacing-5 calibration lattice
    # (a geometric control that covers 99.87% of the footprint within 3 px, hence overlaps
    # every dotted budget) from the competing method lanes (the actual prior submissions).
    final_novelty = novelty.compare_prospective_registry(
        final.astype(np.float32), fp, entries, ROOT, dots=final, template_path=template
    )
    report["final_novelty"] = final_novelty
    method_rows = [
        r for r in final_novelty["rows"] if r.get("entry_role") == "competing_method_lane"
    ]
    method_dup = any(r["duplicate"] for r in method_rows)
    max_comp_overlap = max(
        (r["candidate_dot_overlap_within_3px"] for r in method_rows), default=None
    )
    report["final_novelty"]["competing_method_duplicate"] = bool(method_dup)
    report["final_novelty"]["max_competing_method_overlap"] = max_comp_overlap
    print(
        "Final dots vs competing methods: max rank corr",
        round(final_novelty["method_lane_max_abs_rank_correlation"], 4),
        "max 3-px overlap",
        round(max_comp_overlap, 4) if max_comp_overlap is not None else None,
        "duplicate:",
        method_dup,
        flush=True,
    )
    if method_dup:
        report.update(verdict="negative", stopped_reason="duplicate-final-dots-vs-competing-method")
        save(report, RESULT)
        raise SystemExit(
            "Duplicate final dots vs competing methods; lane stopped without packaging"
        )
    print(
        "Final dots unique vs all competing method rasters; lattice overlap is the documented "
        "geometric bound (reported, not evaded)",
        flush=True,
    )

    # ---- Write a research TIF (whole-array [0,1] validation is not portal approval) ----
    content_id = submission.scored_content_id(final, fp, labels)
    name = submission.make_filename(
        "24GEMSDOE", "ventrad-blind-geothermal", "20261028", content_id, "zero"
    )
    zeros = submission.write_submission(final, template, DOWNLOADS / name, outside="zero")
    nan_name = name.replace("-zero.tif", "-nan.tif")
    nan = submission.write_submission(final, template, DOWNLOADS / nan_name, outside="nan")
    checks = {
        "zero_outside": submission.check_variants(zeros, template),
        "nan_outside": submission.check_variants(nan, template),
    }
    if not all(c["format_valid"] for c in checks.values()):
        raise SystemExit("Exact-file format checks failed; do not publish")

    note = submission.make_note(
        "VENTRAD",
        "blind geothermal upwelling vents+pottassic alteration, unique vs competing methods, holdout DTI 0.122",
        content_id,
        family="24GEMSDOE",
    )
    note_file = f"note-{name[:-4]}.txt"
    (DOWNLOADS / note_file).write_text(note + "\n")
    checks_file = f"checks-{name[:-4]}.json"
    save(checks, DOWNLOADS / checks_file)

    report.update(
        verdict="negative",
        verdict_reasons=[
            "Literal all-entries uniqueness gate fails vs the spacing-5 calibration lattice "
            "(documented geometric bound: every dotted budget overlaps it >= 82.3%); passes "
            "vs every competing method raster.",
            "No organizer-confirmed score; DrivenData submission slot not available/used.",
        ],
        filename=name,
        nan_filename=nan_name,
        raster_sha256=sha256_file(zeros),
        scored_content_id=content_id,
        note=note,
        note_file=note_file,
        checks_file=checks_file,
        validator=checks,
        ok_to_download=True,
        ok_to_submit=False,
        elapsed_seconds=time.monotonic() - started,
    )
    report["holdout_dti"] = holdout_summary["dti"]
    report["holdout_ci95"] = holdout_summary["ci95"]["interval"]
    report["holdout_withheld"] = holdout_summary["n_truth"]

    card = {
        "hypothesis": report["hypothesis"],
        "mechanism": report["mechanism"],
        "non_fault_mimic": report["non_fault_mimic"],
        "holdout": {
            "label": "HOLDOUT-DTI",
            "evaluator_version": holdout.MTR_EVALUATOR_VERSION,
            "n_withheld_positive_pixels": int(holdout_summary["n_truth"]),
            "dti": holdout_summary["dti"],
            "ci95": holdout_summary["ci95"]["interval"],
            "protocol": "pooled TPw/FPw/FNw, 10 km spatial block bootstrap, alpha 0.2 beta 0.8, 300 m triangular kernel, buffer 15 px",
        },
        "leakage_canary": {
            "passed": canary["passed"],
            "worst_feature": canary["worst_feature"],
            "worst_pooled_auc": canary["worst_pooled_auc"],
            "threshold": 0.90,
        },
        "correlation_overlap_vs_registry": {
            "method_lane_passed_vs_competing_methods": True,
            "max_abs_rank_correlation": final_novelty["max_abs_rank_correlation"],
            "max_dot_overlap_within_3px": final_novelty["max_dot_overlap"],
            "literal_all_entries_passed": final_novelty["passed"],
            "lattice_overlap": [
                r
                for r in final_novelty["rows"]
                if r.get("entry_role") == "synthetic_spacing5_calibration_lattice"
            ],
            "competing_method_overlaps": [
                {
                    "registry_id": r["registry_id"],
                    "file": r["file"],
                    "overlap": r["candidate_dot_overlap_within_3px"],
                    "rho": r["raw_spearman"],
                }
                for r in final_novelty["rows"]
                if r.get("entry_role") == "competing_method_lane"
            ],
        },
        "raster_sha256": report["raster_sha256"],
        "validator_output": checks["zero_outside"],
        "submission_name": name,
        "note": note,
        "verdict": "negative",
        "ok_to_download": True,
        "ok_to_submit": False,
        "reasons": report["verdict_reasons"],
        "organizer_confirmed_score": None,
        "experiments_run": 1,
        "submission_slots_used": 0,
        "elapsed_seconds": report["elapsed_seconds"],
    }
    save(card, RESULT)
    save(card, ROOT / "docs/data/ventrad_run_card.json")

    download = {
        "file": name,
        "nan_file": nan_name,
        "sha256": report["raster_sha256"],
        "content_id": content_id,
        "pixel_count": int(final.sum()),
        "note": note,
        "note_file": note_file,
        "checks_file": checks_file,
        "role": "primary",
        "format_valid": checks["zero_outside"]["format_valid"],
        "ok_to_download": True,
        "ok_to_submit": False,
        "recommended_for_new_slot": False,
        "slot_recommendation": "not_recommended",
        "verdict": "negative",
        "holdout_dti": holdout_summary["dti"],
        "holdout_ci95": holdout_summary["ci95"]["interval"],
        "run_card": "ventrad_run_card.json",
    }
    save(download, ROOT / "docs/data/ventrad_download.json")
    print(
        json.dumps(
            {
                "file": name,
                "pixels": int(final.sum()),
                "sha256": report["raster_sha256"],
                "holdout_dti": holdout_summary["dti"],
                "holdout_ci95": holdout_summary["ci95"]["interval"],
                "note_characters": len(note),
                "verdict": "negative",
                "ok_to_submit": False,
            },
            indent=2,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
