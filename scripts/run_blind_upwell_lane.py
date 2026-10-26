#!/usr/bin/env python3
"""H24-BLIND-UPWELL: concealed-fault geothermal upwelling detector.

Single method lane (preregistered in knowledge/25_preregistered_blind_upwell_2026-10-26.md).

Hypothesis (H1): blind faults hosting geothermal upwelling express subtle
curvature flexure (LiDAR ex_mean), potassium enrichment (GeoDAWN K), low Th/K
(argillic overprint) and shallow thermal anomalies (INGENIOUS vents/springs)
WITHOUT a mappable surface trace -- so they are MISSING from the USGS/INGENIOUS
catalogue. The score surface is fully catalogue-independent; catalogue faults
are used ONLY for holdout masking and evaluation. Emission excludes catalogue
pixels from dots (catalogue-conditioned dot rasters are the novelty-failure mode
that stopped H-UNIQUE-01 at 99.85% final-dot overlap with the H19-5 mirror).

Layers (all committed, hash-pinned, grid-aligned to EPSG:32611 3730x3292 @100 m):
  * lidar_scarp_features_u8.tif band 2 ex_mean  (short-wavelength slope excess)
  * geodawn_rad_u8.tif        band 1 K          (potassic alteration halo)
  * geodawn_extensions_u8.tif band 1 ThK        (low Th/K = argillic overprint)
  * gdr_volcanic_vents_in_footprint.csv + gdr_wellspring_in_footprint.csv
                              (vents + springs with geothermometry, rasterized +
                               triangular-kernel-convolved R=300 m thermal field)

Non-fault mimic (named): K-rich alluvial fans / paleochannels with shallow warm
groundwater produce steep + K + warm coincidence without a fault.

Protocol: SegmentHoldout hide-and-recover (buffer 15 px = 1.5 km, four spatial
quadrants, pooled DTI alpha 0.2 beta 0.8, 300 m triangular kernel), pooled
emission priority_poisson dots, leakage canary per channel + surface, registry
novelty surface + final dots, exact-grid TIF zeros outside (finite [0,1]).

Outputs:
  docs/downloads/24gems-blind-upwelling-<date>-<content_id>-zeros.tif
  docs/downloads/checks-*.json, preflight-*.json, note-*.txt (<=140 chars)
  evidence/blind_upwell_experiment.json, docs/data/blind_upwell_run_card.json
  docs/data/blind_upwell_download.json

Verdict set by the gates, never assumed. No DrivenData upload; no slot spent.
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
VENTS_CSV = ROOT / "data/external/gdr_volcanic_vents_in_footprint.csv"
SPRINGS_CSV = ROOT / "data/external/gdr_wellspring_in_footprint.csv"

BUDGET_FRACTION = 0.0073
MIN_DIST_PX = 3.0
THERMAL_BOOST = 1.0  # score multiplier near thermal features: 1.0 + thermal_norm
CURRENT_BEST_HOLDOUT = 0.13000  # OOF multiphysics baseline, gems-segment-pooled-v1

RESULT = ROOT / "evidence/blind_upwell_experiment.json"
DOWNLOADS = ROOT / "docs/downloads"
DATA_OUT = ROOT / "docs/data"


def save(obj, path):
    Path(path).write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n")


def read_u8_band(path, band):
    with rasterio.open(path) as ds:
        return ds.read(band).astype(np.float32)


def norm01(a, valid_mask):
    """Normalise to [0,1] over 2nd-98th percentile of valid pixels."""
    v = np.where(valid_mask & np.isfinite(a), a, np.nan)
    lo, hi = np.nanpercentile(v, 2), np.nanpercentile(v, 98)
    if not (np.isfinite(lo) and np.isfinite(hi)) or hi <= lo:
        return np.zeros_like(a)
    out = np.clip((a - lo) / (hi - lo), 0.0, 1.0)
    out[~valid_mask] = 0.0
    return out


def thermal_surface(fp):
    """Rasterize vents + geothermometry springs, triangular-kernel credit field."""
    import csv

    mask = np.zeros(fp.shape, bool)
    n_vents = 0
    with open(VENTS_CSV, newline="") as f:
        for row in csv.DictReader(f):
            r = int(float(row["row"]))
            c = int(float(row["col"]))
            if 0 <= r < fp.shape[0] and 0 <= c < fp.shape[1] and fp[r, c]:
                mask[r, c] = True
                n_vents += 1
    n_springs = 0
    with open(SPRINGS_CSV, newline="") as f:
        for row in csv.DictReader(f):
            r = int(float(row["row"]))
            c = int(float(row["col"]))
            gq = row.get("geothermquartz_c", "")
            if gq in (None, "", "nan", "NaN"):
                continue
            if 0 <= r < fp.shape[0] and 0 <= c < fp.shape[1] and fp[r, c]:
                mask[r, c] = True
                n_springs += 1
    credit = emission.kernel_credit(mask, radius=3.0)  # max(1 - d/300m, 0)
    valid = fp & (credit > 0)
    thermal = norm01(credit, valid)
    return thermal, int(mask.sum()), n_vents, n_springs


def build_score_surface(fp):
    lidar_valid = read_u8_band(LIDAR, 12) > 0
    ex_mean = read_u8_band(LIDAR, 2)  # short-wavelength steepness / flexure
    k_band = read_u8_band(RAD, 1)  # potassium alteration halo
    thk_band = read_u8_band(EXT, 1)  # Th/K; low = argillic overprint

    for name, arr in (
        ("lidar_valid", lidar_valid.astype(np.float32)),
        ("ex_mean", ex_mean),
        ("k_band", k_band),
        ("thk_band", thk_band),
    ):
        if arr.shape != fp.shape:
            raise SystemExit(f"{name} shape {arr.shape} != template {fp.shape}")

    thermal, n_thermal_px, n_vents, n_springs = thermal_surface(fp)

    curvature = norm01(ex_mean, lidar_valid)
    k_anom = norm01(k_band, lidar_valid & (k_band > 0))
    alteration = 1.0 - norm01(thk_band, lidar_valid & (thk_band > 0))

    score = curvature * k_anom * alteration * (1.0 + THERMAL_BOOST * thermal)
    support = fp & lidar_valid & (k_band > 0) & (thk_band > 0)
    score = np.where(support, score, 0.0).astype(np.float32)
    return (
        score,
        support,
        dict(
            lidar_valid_px=int(lidar_valid.sum()),
            thermal_px=n_thermal_px,
            n_vents=n_vents,
            n_springs=n_springs,
        ),
    )


def main():
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
    with rasterio.open(LABELS) as s:
        catalogue = (s.read(1) > 0) & fp

    score, support, layer_stats = build_score_surface(fp)
    n_support = int(support.sum())
    n_score_pos = int((score > 0).sum())
    print(f"Support pixels: {n_support:,}  Score-positive pixels: {n_score_pos:,}", flush=True)

    context = holdout.SegmentHoldout(fp, catalogue, buffer_px=15)

    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "hypothesis": (
            "H24-BLIND-UPWELL H1: concealed-fault geothermal upwelling -- "
            "LiDAR ex_mean flexure x GeoDAWN K x low Th/K x INGENIOUS vent/spring "
            "thermal field; catalogue-independent scoring; emission excludes catalogue pixels"
        ),
        "mechanism": (
            "Blind faults hosting geothermal upwelling express subtle curvature "
            "flexure, K enrichment, low Th/K (argillic) and shallow thermal "
            "anomalies without a mappable surface trace, so they are missing from "
            "the USGS/INGENIOUS catalogue; catalogue faults are used only for "
            "holdout masking/evaluation, never to build the score surface."
        ),
        "non_fault_mimic": (
            "K-rich alluvial fans / paleochannels with shallow warm groundwater "
            "produce steep + K + warm coincidence without a fault."
        ),
        "preregistration": "knowledge/25_preregistered_blind_upwell_2026-10-26.md",
        "experiment_number": 1,
        "maximum_experiments": 3,
        "maximum_session_hours": 2,
        "input_provenance": "Committed external mirrors (USGS GeoDAWN DOI 10.5066/P93LGLVQ, INGENIOUS/OpenEI GDR 1391, USGS 3DEP LiDAR derivatives)",
        "inputs": {
            str(p.relative_to(ROOT)): sha256_file(p)
            for p in (TEMPLATE, LABELS, LIDAR, RAD, EXT, VENTS_CSV, SPRINGS_CSV)
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
        "layer_stats": layer_stats,
        "catalogue_features": [],
        "prediction_inputs_include_registry_rasters": False,
        "supervised_fit": False,
        "submission_slot_spent": False,
        "organizer_confirmed_score": None,
        "lane_status": "H24-BLIND-UPWELL: catalogue-independent concealed-conduit detector",
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

    # Leakage canary: each channel and the combined surface alone.
    lidar_valid = read_u8_band(LIDAR, 12) > 0
    ex_mean = read_u8_band(LIDAR, 2)
    k_band = read_u8_band(RAD, 1)
    thk_band = read_u8_band(EXT, 1)
    thermal, *_ = thermal_surface(fp)
    thermal = np.where(fp & lidar_valid, thermal, 0.0).astype(np.float32)
    canary_features = {
        "curvature_ex_mean": np.where(fp & lidar_valid, norm01(ex_mean, lidar_valid), 0.0).astype(
            np.float32
        ),
        "k_anomaly": np.where(
            fp & lidar_valid & (k_band > 0), norm01(k_band, lidar_valid & (k_band > 0)), 0.0
        ).astype(np.float32),
        "alteration_low_thk": np.where(
            fp & lidar_valid & (thk_band > 0),
            1.0 - norm01(thk_band, lidar_valid & (thk_band > 0)),
            0.0,
        ).astype(np.float32),
        "thermal_vent_spring": thermal,
        "score_surface": score,
    }
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

    # Surface novelty before placement.
    registry = json.loads((ROOT / "registry/priority_rasters.json").read_text())
    report["surface_novelty"] = novelty.compare_prospective_registry(
        score, fp, registry["unique_rasters"], ROOT
    )
    surf = report["surface_novelty"]
    print(
        f"Surface novelty: method_lane_passed={surf.get('method_lane_passed')} "
        f"literal={surf.get('literal_all_entries_passed')} "
        f"max|rho|={surf.get('max_abs_rank_correlation')}",
        flush=True,
    )
    if not surf.get("method_lane_passed"):
        report.update(
            verdict="negative",
            stopped_reason="duplicate-surface",
            elapsed_seconds=time.monotonic() - started,
        )
        save(report, RESULT)
        raise SystemExit("Duplicate surface; stopped before placement")

    # Per-fold holdout predictions.
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
    print(f"HOLDOUT-DTI {results['dti']:.5f} CI {results['ci95']['interval']}", flush=True)

    # Final dots on full support, excluding catalogue pixels.
    final = emission.priority_poisson(
        score, support & ~catalogue, round(BUDGET_FRACTION * fp.sum()), min_dist=MIN_DIST_PX
    )
    if not final.any():
        raise SystemExit("No positive evidence; refusing an empty submission")

    report["final_novelty"] = novelty.compare_prospective_registry(
        final.astype(np.float32), fp, registry["unique_rasters"], ROOT, dots=final
    )
    fin = report["final_novelty"]
    print(
        f"Final novelty: method_lane_passed={fin.get('method_lane_passed')} "
        f"literal={fin.get('literal_all_entries_passed')} "
        f"max_overlap={fin.get('max_dot_overlap')}",
        flush=True,
    )
    if not fin.get("method_lane_passed"):
        report.update(
            verdict="negative",
            stopped_reason="duplicate-final-dots",
            elapsed_seconds=time.monotonic() - started,
        )
        save(report, RESULT)
        raise SystemExit("Duplicate final dots; stopped without packaging")

    # Package TIF: zeros outside -> finite [0,1] everywhere (portal-range compatible).
    content_id = submission.scored_content_id(final, fp, catalogue)
    date_str = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    name = submission.make_filename("24gems", "blind-upwelling", date_str, content_id, "zeros")
    zeros_path = DOWNLOADS / name
    submission.write_submission(final, TEMPLATE, zeros_path, outside="zero")

    checks = submission.check_variants(zeros_path, TEMPLATE)
    if not checks["format_valid"]:
        raise SystemExit("Exact-file format checks failed; do not publish")

    note = (
        f"24GEMS blind-upwelling LiDARxKxThKxthermal | catalogue-independent | "
        f"research; HOLDOUT-DTI {results['dti']:.5f} | id {content_id}"
    )
    if len(note) > 140:
        note = note[:137] + "..."
    note_file = f"note-{name[:-4]}.txt"
    (DOWNLOADS / note_file).write_text(note + "\n")

    checks_file = f"checks-{name[:-4]}.json"
    save(checks, DOWNLOADS / checks_file)

    raster_sha256 = sha256_file(zeros_path)
    preflight_report = preflight(
        zeros_path,
        TEMPLATE,
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
        and fin.get("method_lane_passed")
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
            "surface_max_abs_rank_correlation": surf["max_abs_rank_correlation"],
            "final_max_abs_rank_correlation": fin["max_abs_rank_correlation"],
            "final_max_overlap_within_3px": fin["max_dot_overlap"],
            "method_lane_passed": fin.get("method_lane_passed"),
            "literal_all_entries_passed": fin.get("literal_all_entries_passed"),
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
                [
                    f"holdout DTI {results['dti']:.5f} does not beat current comparable best {CURRENT_BEST_HOLDOUT}"
                ]
                if not beats_current_best
                else []
            )
            + (["format or range check failed"] if not checks["format_valid"] else [])
            + (["novelty gate failed"] if not fin.get("method_lane_passed") else [])
            + (["canary failed"] if not report["canary"]["passed"] else [])
        ),
        "organizer_confirmed_score": None,
        "experiments_run": 1,
        "submission_slots_used": 0,
        "elapsed_seconds": time.monotonic() - started,
    }
    save(card, RESULT)
    save(card, DATA_OUT / "blind_upwell_run_card.json")

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
        "run_card": "blind_upwell_run_card.json",
    }
    save(download_entry, DATA_OUT / "blind_upwell_download.json")

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
                "novelty_method_lane_passed": fin.get("method_lane_passed"),
                "canary_passed": report["canary"]["passed"],
            },
            indent=2,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
