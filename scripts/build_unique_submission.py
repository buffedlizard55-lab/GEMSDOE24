#!/usr/bin/env python3
"""Build a UNIQUE, catalogue-independent GEMS submission GeoTIFF.

Hypothesis (H-UNIQUE-01): Blind hydrothermal-conduit detection via
LiDAR scarp x radiometric potassium concordance.

Layers:
  * lidar_scarp_features_u8.tif  -> ex_max, step_max, relief (subtle scarps)
  * geodawn_rad_u8.tif           -> K band (potassic alteration halo)
  * geodawn_extensions_u8.tif    -> ThK channel (low Th/K = argillic overprint)

Mechanism: Geothermal systems localise at blind faults where hydrothermal
K-enrichment coincides with subtle LiDAR-expressed scarps. The USGS /
INGENIOUS catalogue maps only well-expressed traces; this detector does NOT
condition on any catalogue fault, so it can score concealed / blind conduits
absent from the catalogue. Catalogue faults are used ONLY for holdout masking
and evaluation, never for building the score surface.

Non-fault mimic: K-rich alluvial-fan toes with steep slopes can produce a
false scarp + K coincidence.

Protocol: SegmentHoldout hide-and-recover, pooled DTI (alpha 0.2, beta 0.8,
300 m triangular kernel), leakage canary on each channel, registry novelty
(< 0.90 rank, < 70% dots within 3 px), exact-grid TIF with zeros outside the
footprint (finite [0,1] everywhere — fixes the "[0, 1]" portal rejection).

Outputs:
  docs/downloads/24gems-doer-blind-conduit-<date>-<content_id>-zeros.tif
  docs/downloads/checks-*.json
  docs/downloads/note-*.txt
  docs/downloads/preflight-*.json
  evidence/unique_experiment.json
  docs/data/unique_run_card.json
  docs/data/unique_download.json

Verdict is set by the gates, not assumed. No upload occurs.
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
from gems.preflight import preflight  # noqa: E402
from gems.validator import sha256_file  # noqa: E402

TEMPLATE = ROOT / "data/bridge/sample_submission.tif"
LABELS = ROOT / "data/bridge/labels.tif"
LIDAR = ROOT / "data/external/lidar_scarp_features_u8.tif"
RAD = ROOT / "data/external/geodawn_rad_u8.tif"
EXT = ROOT / "data/external/geodawn_extensions_u8.tif"

BUDGET_FRACTION = 0.0073
MIN_DIST_PX = 3.0
CURRENT_BEST_HOLDOUT = 0.13000

RESULT = ROOT / "evidence/unique_experiment.json"
DOWNLOADS = ROOT / "docs/downloads"
DATA_OUT = ROOT / "docs/data"


def save(obj, path):
    Path(path).write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n")


def read_u8_band(path, band):
    with rasterio.open(path) as ds:
        a = ds.read(band).astype(np.float32)
    return a


def norm01(a, valid_mask):
    """Normalise to [0,1] over 2nd-98th percentile of valid pixels."""
    v = np.where(valid_mask & np.isfinite(a), a, np.nan)
    lo, hi = np.nanpercentile(v, 2), np.nanpercentile(v, 98)
    if not np.isfinite(lo) or not np.isfinite(hi) or hi <= lo:
        return np.zeros_like(a)
    out = np.clip((a - lo) / (hi - lo), 0.0, 1.0)
    out[~valid_mask] = 0.0
    return out


def build_score_surface(fp):
    """Catalogue-independent score surface from LiDAR + radiometric layers."""
    with rasterio.open(TEMPLATE) as t:
        t_shape, _t_crs, _t_tr = t.shape, t.crs, t.transform
        t_fp = np.isfinite(t.read(1))

    lidar_valid = read_u8_band(LIDAR, 12) > 0
    ex_max = read_u8_band(LIDAR, 1)
    step_max = read_u8_band(LIDAR, 3)
    relief = read_u8_band(LIDAR, 9)
    k_band = read_u8_band(RAD, 1)
    thk_band = read_u8_band(EXT, 1)

    for name, arr in (
        ("lidar_valid", lidar_valid.astype(np.float32)),
        ("ex_max", ex_max),
        ("step_max", step_max),
        ("relief", relief),
        ("k_band", k_band),
        ("thk_band", thk_band),
    ):
        if arr.shape != t_shape:
            raise SystemExit(f"{name} shape {arr.shape} != template {t_shape}")

    scarp = norm01(ex_max, lidar_valid) * norm01(step_max, lidar_valid)
    relief_n = norm01(relief, lidar_valid)
    scarp = scarp * (0.5 + 0.5 * relief_n)

    k_anom = norm01(k_band, lidar_valid & (k_band > 0))
    thk_n = norm01(thk_band, lidar_valid & (thk_band > 0))
    alteration = 1.0 - thk_n

    score = scarp * k_anom * alteration
    support = fp & lidar_valid & (k_band > 0) & (thk_band > 0)
    score = np.where(support & t_fp, score, 0.0).astype(np.float32)
    return score, support


def main():
    raise SystemExit(
        "Retired: frozen historical lane; no reruns, retuning or slot authorization. "
        "Inspect the recorded evidence and original code at commit caeda657e63c1136de98888fb70aa4c232542dd6."
    )
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--verify-recorded",
        action="store_true",
        help="Inspect recorded evidence; do not run a new experiment",
    )
    args = ap.parse_args()

    if args.verify_recorded:
        if RESULT.exists():
            print(RESULT.read_text())
        else:
            print(json.dumps({"status": "no_recorded_experiment"}))
        return

    started = time.monotonic()
    fp = footprint.load_footprint()
    with rasterio.open(TEMPLATE) as t:
        t.profile.copy()

    with rasterio.open(LABELS) as s:
        catalogue = (s.read(1) > 0) & fp

    # ---- Build the unique score surface ------------------------------------
    score, support = build_score_surface(fp)
    print(f"Support pixels: {int(support.sum()):,}", flush=True)
    print(f"Score positive pixels: {int((score > 0).sum()):,}", flush=True)

    # ---- Holdout context -----------------------------------------------------
    context = holdout.SegmentHoldout(fp, catalogue, buffer_px=15)

    # ---- Leakage canary: each channel alone ----------------------------------
    ex_max = read_u8_band(LIDAR, 1)
    k_band = read_u8_band(RAD, 1)
    thk_band = read_u8_band(EXT, 1)
    lidar_valid = read_u8_band(LIDAR, 12) > 0

    canary_features = {
        "scarps_ex_max": np.where(fp & lidar_valid, norm01(ex_max, lidar_valid), 0.0).astype(
            np.float32
        ),
        "k_anomaly": np.where(
            fp & lidar_valid & (k_band > 0), norm01(k_band, lidar_valid & (k_band > 0)), 0.0
        ).astype(np.float32),
        "alteration_thk": np.where(
            fp & lidar_valid & (thk_band > 0),
            1.0 - norm01(thk_band, lidar_valid & (thk_band > 0)),
            0.0,
        ).astype(np.float32),
        "score_surface": score,
    }

    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "hypothesis": (
            "H-UNIQUE-01 blind hydrothermal conduit: LiDAR scarps x radiometric K x low Th/K"
        ),
        "mechanism": (
            "Hydrothermal K-enrichment coincides with subtle "
            "LiDAR-expressed fault scarps; catalogue-independent so "
            "blind conduits absent from USGS/INGENIOUS are detectable"
        ),
        "non_fault_mimic": "K-rich alluvial-fan toes with steep slopes",
        "preregistration": "knowledge/unique_hypothesis_2026-10-25.md",
        "experiment_number": 1,
        "maximum_experiments": 3,
        "maximum_session_hours": 2,
        "input_provenance": ("Committed external mirrors (USGS GeoDAWN, 3DEP LiDAR derivatives)"),
        "inputs": {
            str(p.relative_to(ROOT)): sha256_file(p) for p in (TEMPLATE, LABELS, LIDAR, RAD, EXT)
        },
        "code_sha256": {
            str(p.relative_to(ROOT)): sha256_file(p)
            for p in (
                Path(__file__),
                ROOT / "src/gems/holdout.py",
                ROOT / "src/gems/metric.py",
                ROOT / "src/gems/emission.py",
                ROOT / "src/gems/novelty.py",
                ROOT / "src/gems/submission.py",
            )
        },
        "supported_pixels": int(support.sum()),
        "catalogue_features": [],
        "prediction_inputs_include_registry_rasters": False,
        "supervised_fit": False,
        "submission_slot_spent": False,
        "organizer_confirmed_score": None,
        "lane_status": "new lane: catalogue-independent blind-conduit detector",
    }

    # ---- Fold integrity ------------------------------------------------------
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
    report["canary"] = context.canary(canary_features)
    if not report["canary"]["passed"]:
        report.update(
            verdict="negative",
            stopped_reason="leakage-canary",
            elapsed_seconds=time.monotonic() - started,
        )
        save(report, RESULT)
        raise SystemExit("Leakage canary failed; no candidate packaged")
    print("Canaries passed", flush=True)

    # ---- Surface novelty (before dot placement) ------------------------------
    registry = json.loads((ROOT / "registry/priority_rasters.json").read_text())
    report["surface_novelty"] = novelty.compare_registry(
        score, fp, registry["unique_rasters"], ROOT
    )
    if not report["surface_novelty"]["passed"]:
        report.update(
            verdict="negative",
            stopped_reason="duplicate-surface",
            elapsed_seconds=time.monotonic() - started,
        )
        save(report, RESULT)
        raise SystemExit("Duplicate surface; stopped before placement")
    print("Surface registry check passed", flush=True)

    # ---- Per-fold holdout predictions ----------------------------------------
    predictions = []
    for f in context.folds:
        eligible = support & f["valid"] & ~f["visible"]
        predictions.append(
            emission.priority_poisson(
                score, eligible, round(BUDGET_FRACTION * f["valid"].sum()), min_dist=MIN_DIST_PX
            )
        )

    results = context.summarize(predictions)
    report["holdout"] = results
    print(f"HOLDOUT-DTI {results['dti']} CI {results['ci95']['interval']}", flush=True)

    # ---- Final dots on full support, excluding catalogue ---------------------
    final = emission.priority_poisson(
        score, support & ~catalogue, round(BUDGET_FRACTION * fp.sum()), min_dist=MIN_DIST_PX
    )
    if not final.any():
        raise SystemExit("No positive evidence; refusing an empty submission")

    report["final_novelty"] = novelty.compare_registry(
        final.astype(np.float32), fp, registry["unique_rasters"], ROOT, dots=final
    )
    if not report["final_novelty"]["passed"]:
        report.update(
            verdict="negative",
            stopped_reason="duplicate-final-dots",
            elapsed_seconds=time.monotonic() - started,
        )
        save(report, RESULT)
        raise SystemExit("Duplicate final dots; stopped without packaging")
    print("Final dots novelty check passed", flush=True)

    # ---- Package TIF (zeros outside = finite [0,1] everywhere) ---------------
    content_id = submission.scored_content_id(final, fp, catalogue)
    date_str = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    name = submission.make_filename("24gems", "doer-blind-conduit", date_str, content_id, "zeros")

    zeros_path = DOWNLOADS / name
    zeros = submission.write_submission(final, TEMPLATE, zeros_path, outside="zero")

    checks = submission.check_variants(zeros, TEMPLATE)
    if not checks["format_valid"]:
        raise SystemExit("Exact-file format checks failed; do not publish")

    # ---- Note (<= 140 chars) --------------------------------------------------
    note = (
        f"24GEMS blind-conduit LiDARxK | catalogue-independent | "
        f"research; HOLDOUT-DTI {results['dti']:.5f} | id {content_id}"
    )
    if len(note) > 140:
        note = note[:137] + "..."
    note_file = f"note-{name[:-4]}.txt"
    (DOWNLOADS / note_file).write_text(note + "\n")

    checks_file = f"checks-{name[:-4]}.json"
    save(checks, DOWNLOADS / checks_file)

    raster_sha256 = sha256_file(zeros)

    # ---- Preflight -----------------------------------------------------------
    preflight_report = preflight(
        zeros,
        TEMPLATE,
        run_card_path=None,
        note=note,
        expected_template_sha256=sha256_file(TEMPLATE),
    )
    preflight_file = f"preflight-{name[:-4]}.json"
    save(preflight_report, DOWNLOADS / preflight_file)

    # ---- Run card ------------------------------------------------------------
    beats_current_best = results["dti"] > CURRENT_BEST_HOLDOUT
    ok_to_submit = (
        checks["format_valid"]
        and checks["checks"]["variant_strict_whole_array_no_nan_allowed"]["pass"]
        and report["final_novelty"]["passed"]
        and report["canary"]["passed"]
        and beats_current_best
    )
    verdict = "promote" if ok_to_submit else "negative"

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
            "surface_max_abs_rank_correlation": report["surface_novelty"][
                "max_abs_rank_correlation"
            ],
            "final_max_abs_rank_correlation": report["final_novelty"]["max_abs_rank_correlation"],
            "final_max_overlap_within_3px": report["final_novelty"]["max_dot_overlap"],
            "passed": report["final_novelty"]["passed"],
            "method_lane_passed": report["final_novelty"].get("method_lane_passed"),
            "scope": registry["scope"],
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
        "reasons": (
            []
            if ok_to_submit
            else (
                [f"holdout DTI does not beat current comparable best {CURRENT_BEST_HOLDOUT}"]
                if not beats_current_best
                else []
            )
            + (["format or range check failed"] if not checks["format_valid"] else [])
            + (["novelty gate failed"] if not report["final_novelty"]["passed"] else [])
            + (["canary failed"] if not report["canary"]["passed"] else [])
        ),
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
        "strict_range_ok": checks["checks"]["variant_strict_whole_array_no_nan_allowed"]["pass"],
        "ok_to_download": checks["format_valid"],
        "ok_to_submit": ok_to_submit,
        "verdict": verdict,
        "holdout_dti": results["dti"],
        "holdout_ci95": results["ci95"]["interval"],
        "run_card": "unique_run_card.json",
    }
    save(download_entry, DATA_OUT / "unique_download.json")

    print(
        json.dumps(
            {
                "file": name,
                "pixels": int(final.sum()),
                "sha256": raster_sha256,
                "holdout_dti": results["dti"],
                "holdout_ci95": results["ci95"]["interval"],
                "note_characters": len(note),
                "verdict": verdict,
                "ok_to_submit": ok_to_submit,
                "ok_to_download": checks["format_valid"],
                "strict_range_ok": checks["checks"]["variant_strict_whole_array_no_nan_allowed"][
                    "pass"
                ],
                "novelty_passed": report["final_novelty"]["passed"],
                "canary_passed": report["canary"]["passed"],
            },
            indent=2,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
