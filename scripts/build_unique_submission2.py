#!/usr/bin/env python3
"""Experiment 2: Focused physical detector (H-UNIQUE-02).

Hypothesis: Hydrothermal K-enrichment coinciding with subtle LiDAR-expressed
scarps marks blind fault conduits absent from the USGS/INGENIOUS catalogue.
Unlike diffuse broad-coverage detectors, this uses a HIGHLY SELECTIVE score
surface (top-decile K x scarp coincidence only) so dots cluster at the
strongest physical anomalies rather than spreading across the domain.

Difference from reviewed methods:
  * Dotted-ridge/h28, h25: dots conditioned on catalogue ridge features;
    no radiometric selectivity.
  * Tip-stepper/h33: dots at catalogue fault tips; no LiDAR x K physics.
  * SAHG1: strike-projected LiDAR + Th/K + basement steps; different
    combination and receptive field.
  * H-UNIQUE-01 (exp 1): catalogue-independent but too diffuse (0.0668 DTI);
    this experiment is selective and physically focused.

Catalogue faults are used ONLY for holdout masking/evaluation, never for
building the score surface. Purely physical layers: LiDAR scarps + radiometric
K + Th/K.
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

BUDGET_FRACTION = 0.003  # smaller, more selective budget (~11K dots)
MIN_DIST_PX = 3.0
CURRENT_BEST_HOLDOUT = 0.13000
K_THRESHOLD = 0.80  # only top-decile K pixels eligible
SCARP_THRESHOLD = 0.50

RESULT = ROOT / "evidence/unique_experiment2.json"
DOWNLOADS = ROOT / "docs/downloads"
DATA_OUT = ROOT / "docs/data"


def save(obj, path):
    Path(path).write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n")


def read_u8_band(path, band):
    with rasterio.open(path) as ds:
        return ds.read(band).astype(np.float32), (ds.shape, ds.crs, ds.transform)


def norm01(a, valid_mask):
    v = np.where(valid_mask & np.isfinite(a), a, np.nan)
    lo, hi = np.nanpercentile(v, 2), np.nanpercentile(v, 98)
    if not np.isfinite(lo) or not np.isfinite(hi) or hi <= lo:
        return np.zeros_like(a)
    out = np.clip((a - lo) / (hi - lo), 0.0, 1.0)
    out[~valid_mask] = 0.0
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--verify-recorded", action="store_true")
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
        t_shape, t_crs, t_tr = t.shape, t.crs, t.transform
        t_fp = np.isfinite(t.read(1))

    with rasterio.open(LABELS) as s:
        labels = (s.read(1) > 0) & t_fp

    context = holdout.SegmentHoldout(fp, labels, buffer_px=15)

    # ---- Read physical layers -----------------------------------------------
    ex_max, lidar_prof = read_u8_band(LIDAR, 1)
    step_max, _ = read_u8_band(LIDAR, 3)
    relief, _ = read_u8_band(LIDAR, 9)
    lidar_valid, _ = read_u8_band(LIDAR, 12)
    lidar_valid = lidar_valid > 0

    k_band, rad_prof = read_u8_band(RAD, 1)
    thk_band, ext_prof = read_u8_band(EXT, 1)
    for name, prof in (("lidar", lidar_prof), ("rad", rad_prof), ("ext", ext_prof)):
        if prof != (t_shape, t_crs, t_tr):
            raise SystemExit(f"{name} grid mismatch")

    # ---- Normalise -----------------------------------------------------------
    scarp = norm01(ex_max, lidar_valid) * norm01(step_max, lidar_valid)
    relief_n = norm01(relief, lidar_valid)
    scarp = scarp * (0.5 + 0.5 * relief_n)

    k_anom = norm01(k_band, t_fp & (k_band > 0))
    thk_n = norm01(thk_band, t_fp & (thk_band > 0))
    alteration = 1.0 - thk_n

    # ---- Selective score surface: only strongest coincidences ---------------
    strong_k = k_anom >= K_THRESHOLD
    strong_scarp = scarp >= SCARP_THRESHOLD
    strong_alt = alteration > 0.3

    score = np.zeros(t_shape, np.float32)
    score[strong_k & strong_scarp & strong_alt & t_fp] = (
        k_anom[strong_k & strong_scarp & strong_alt & t_fp]
        * scarp[strong_k & strong_scarp & strong_alt & t_fp]
        * alteration[strong_k & strong_scarp & strong_alt & t_fp]
    ).astype(np.float32)
    score[~t_fp] = 0.0
    score[~lidar_valid] = 0.0

    support = (t_fp & lidar_valid & strong_k & strong_scarp & strong_alt)
    print(f"Support pixels: {int(support.sum()):,}", flush=True)
    print(f"Score positive pixels: {int((score > 0).sum()):,}", flush=True)

    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "hypothesis": ("H-UNIQUE-02 focused physical: top-decile K x scarp "
                       "coincidence for blind conduits"),
        "mechanism": ("Hydrothermal K-enrichment (top decile) coincides with "
                      "subtle LiDAR-expressed scarps and alteration Th/K "
                      "signature; blind conduits absent from USGS/INGENIOUS"),
        "non_fault_mimic": ("K-rich alluvial-fan toes with steep slopes "
                            "and alteration"),
        "preregistration": "knowledge/unique_hypothesis_2026-10-25.md",
        "experiment_number": 2,
        "maximum_experiments": 3,
        "maximum_session_hours": 2,
        "input_provenance": ("Committed external mirrors (USGS GeoDAWN, "
                             "3DEP LiDAR derivatives)"),
        "inputs": {
            str(p.relative_to(ROOT)): sha256_file(p)
            for p in (TEMPLATE, LABELS, LIDAR, RAD, EXT)
        },
        "code_sha256": {
            str(p.relative_to(ROOT)): sha256_file(p)
            for p in (Path(__file__), ROOT / "src/gems/holdout.py",
                      ROOT / "src/gems/metric.py", ROOT / "src/gems/emission.py",
                      ROOT / "src/gems/novelty.py", ROOT / "src/gems/submission.py")
        },
        "supported_pixels": int(support.sum()),
        "catalogue_features": [],
        "prediction_inputs_include_registry_rasters": False,
        "supervised_fit": False,
        "submission_slot_spent": False,
        "organizer_confirmed_score": None,
        "lane_status": "new lane: focused selective physical detector",
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

    # ---- Leakage canary: physical channels ONLY (no catalogue-derived) ------
    canary_features = {
        "k_anomaly_top_decile": np.where(
            t_fp & lidar_valid & strong_k, k_anom, 0.0
        ).astype(np.float32),
        "scarps_ex_max": np.where(
            t_fp & lidar_valid & strong_scarp, norm01(ex_max, lidar_valid), 0.0
        ).astype(np.float32),
        "alteration_thk": np.where(
            t_fp & lidar_valid & strong_alt, alteration, 0.0
        ).astype(np.float32),
        "score_surface": score,
    }

    report["canary"] = context.canary(canary_features)
    if not report["canary"]["passed"]:
        report.update(verdict="negative", stopped_reason="leakage-canary",
                      elapsed_seconds=time.monotonic() - started)
        save(report, RESULT)
        raise SystemExit("Leakage canary failed; no candidate packaged")
    print("Canaries passed", flush=True)

    # ---- Surface novelty (pre-placement) ------------------------------------
    registry = json.loads((ROOT / "registry/priority_rasters.json").read_text())
    report["surface_novelty"] = novelty.compare_registry(
        score, fp, registry["unique_rasters"], ROOT
    )
    if not report["surface_novelty"]["passed"]:
        report.update(verdict="negative", stopped_reason="duplicate-surface",
                      elapsed_seconds=time.monotonic() - started)
        save(report, RESULT)
        raise SystemExit("Duplicate surface; stopped before placement")
    print("Surface registry check passed", flush=True)

    # ---- Per-fold holdout ----------------------------------------------------
    predictions = []
    for f in context.folds:
        eligible = f["valid"] & ~f["visible"] & support
        predictions.append(
            emission.priority_poisson(
                score, eligible,
                round(BUDGET_FRACTION * f["valid"].sum()), min_dist=MIN_DIST_PX
            )
        )

    results = context.summarize(predictions)
    report["holdout"] = results
    print(f"HOLDOUT-DTI {results['dti']} CI {results['ci95']['interval']}",
          flush=True)

    # ---- Final dots ----------------------------------------------------------
    final = emission.priority_poisson(
        score, support & ~labels,
        round(BUDGET_FRACTION * fp.sum()), min_dist=MIN_DIST_PX
    )
    if not final.any():
        raise SystemExit("No positive evidence; refusing an empty submission")

    report["final_novelty"] = novelty.compare_registry(
        final.astype(np.float32), fp, registry["unique_rasters"], ROOT, dots=final
    )
    if not report["final_novelty"]["passed"]:
        report.update(verdict="negative", stopped_reason="duplicate-final-dots",
                      elapsed_seconds=time.monotonic() - started)
        save(report, RESULT)
        raise SystemExit("Duplicate final dots; stopped without packaging")
    print("Final dots novelty check passed", flush=True)

    # ---- Package TIF ---------------------------------------------------------
    content_id = submission.scored_content_id(final, fp, labels)
    date_str = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    name = submission.make_filename(
        "24gems", "doer-focused-k-scarp", date_str, content_id, "zeros"
    )

    zeros_path = DOWNLOADS / name
    zeros = submission.write_submission(final, TEMPLATE, zeros_path, outside="zero")

    checks = submission.check_variants(zeros, TEMPLATE)
    if not checks["format_valid"]:
        raise SystemExit("Exact-file format checks failed; do not publish")

    note = (f"24GEMS focused K-scarp blind-conduit | selective physical | "
            f"research; HOLDOUT-DTI {results['dti']:.5f} | id {content_id}")
    if len(note) > 140:
        note = note[:137] + "..."
    note_file = f"note-{name[:-4]}.txt"
    (DOWNLOADS / note_file).write_text(note + "\n")

    checks_file = f"checks-{name[:-4]}.json"
    save(checks, DOWNLOADS / checks_file)

    raster_sha256 = sha256_file(zeros)

    preflight_report = preflight(
        zeros, TEMPLATE,
        run_card_path=None,
        note=note,
        expected_template_sha256=sha256_file(TEMPLATE),
    )
    preflight_file = f"preflight-{name[:-4]}.json"
    save(preflight_report, DOWNLOADS / preflight_file)

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
            "surface_max_abs_rank_correlation": report["surface_novelty"]["max_abs_rank_correlation"],
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
        "reasons": ([] if ok_to_submit else
                    (["holdout DTI does not beat current comparable best "
                      f"{CURRENT_BEST_HOLDOUT}"] if not beats_current_best else [])
                    + (["format or range check failed"] if not checks["format_valid"] else [])
                    + (["novelty gate failed"]
                       if not report["final_novelty"]["passed"] else [])
                    + (["canary failed"] if not report["canary"]["passed"] else [])),
        "organizer_confirmed_score": None,
        "experiments_run": 2,
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
        "strict_range_ok": checks["checks"]["variant_strict_whole_array_no_nan_allowed"]["pass"],
        "novelty_passed": report["final_novelty"]["passed"],
        "canary_passed": report["canary"]["passed"],
    }, indent=2), flush=True)


if __name__ == "__main__":
    main()