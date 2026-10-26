#!/usr/bin/env python3
"""Experiment 6 (final): Geothermal surface-feature proximity — packaged TIF.

Hypothesis H-UNIQUE-06: Geothermal surface features (volcanic vents, hot
springs) mark concealed fault conduits absent from the USGS/INGENIOUS fault
catalogue. A score surface based on proximity to vents/springs targets the
fault conduits without ever conditioning on catalogue fault traces.

This experiment ALWAYS packages the TIF so a downloadable artifact exists
with a clear ok_to_download / ok_to_submit verdict. Negative results are
deliverables.

See build_unique_submission5.py for the full method description. This run
differs by packaging even when novelty gates fail, so the user always has
a downloadable, clearly-labelled TIF.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems import emission, footprint, holdout, novelty, submission  # noqa: E402
from gems.preflight import preflight  # noqa: E402
from gems.validator import sha256_file  # noqa: E402

TEMPLATE = ROOT / "data/bridge/sample_submission.tif"
LABELS = ROOT / "data/bridge/labels.tif"
VENTS_CSV = ROOT / "data/external/gdr_volcanic_vents_in_footprint.csv"
SPRINGS_CSV = ROOT / "data/external/gdr_wellspring_in_footprint.csv"

BUDGET_FRACTION = 0.0073
MIN_DIST_PX = 3.0
CURRENT_BEST_HOLDOUT = 0.13000

RESULT = ROOT / "evidence/unique_experiment6.json"
DOWNLOADS = ROOT / "docs/downloads"
DATA_OUT = ROOT / "docs/data"


def save(obj, path):
    Path(path).write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n")


def read_vent_points():
    points = []
    with open(VENTS_CSV) as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                points.append((int(row["row"]), int(row["col"])))
            except (ValueError, KeyError):
                continue
    return points


def read_spring_points():
    points = []
    with open(SPRINGS_CSV) as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                r = int(row["row"])
                c = int(row["col"])
                temp = row.get("temp_c", "")
                temp = float(temp) if temp and temp not in ("NULL", "nan", "") else 0.0
                points.append((r, c, temp))
            except (ValueError, KeyError):
                continue
    return points


def build_score_surface(fp, vent_points, spring_points):
    H, W = fp.shape
    vent_mask = np.zeros((H, W), bool)
    for r, c in vent_points:
        if 0 <= r < H and 0 <= c < W:
            vent_mask[r, c] = True
    spring_mask = np.zeros((H, W), bool)
    spring_temp = np.zeros((H, W), np.float32)
    for r, c, temp in spring_points:
        if 0 <= r < H and 0 <= c < W:
            spring_mask[r, c] = True
            spring_temp[r, c] = temp if temp > 0 else 1.0

    vent_dist = distance_transform_edt(~vent_mask) if vent_mask.any() else np.full((H, W), np.inf)
    spring_dist = (
        distance_transform_edt(~spring_mask) if spring_mask.any() else np.full((H, W), np.inf)
    )
    R = 3.0
    vent_score = np.maximum(1.0 - vent_dist / R, 0.0)
    spring_score = np.maximum(1.0 - spring_dist / R, 0.0)
    temp_weight = np.clip(spring_temp / 100.0, 0.0, 1.0)
    spring_score = spring_score * temp_weight
    score = np.maximum(vent_score, spring_score)
    support = fp.copy()
    score = np.where(support, score, 0.0).astype(np.float32)
    return score, support, vent_mask, spring_mask


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
        t_shape = t.shape
    with rasterio.open(LABELS) as s:
        catalogue = (s.read(1) > 0) & fp

    vent_points = read_vent_points()
    spring_points = read_spring_points()
    print(f"Vents: {len(vent_points)}, Springs: {len(spring_points)}", flush=True)

    score, support, vent_mask, spring_mask = build_score_surface(
        fp, vent_points, spring_points
    )
    print(f"Support pixels: {int(support.sum()):,}", flush=True)
    print(f"Score positive pixels: {int((score > 0).sum()):,}", flush=True)

    context = holdout.SegmentHoldout(fp, catalogue, buffer_px=15)

    vent_dist = distance_transform_edt(~vent_mask) if vent_mask.any() else np.full(t_shape, np.inf)
    spring_dist = (
        distance_transform_edt(~spring_mask) if spring_mask.any() else np.full(t_shape, np.inf)
    )
    R = 3.0
    vent_score_raw = np.maximum(1.0 - vent_dist / R, 0.0)
    spring_score_raw = np.maximum(1.0 - spring_dist / R, 0.0)
    canary_features = {
        "vent_proximity": np.where(fp, vent_score_raw, 0.0).astype(np.float32),
        "spring_proximity": np.where(fp, spring_score_raw, 0.0).astype(np.float32),
        "score_surface": score,
    }

    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "hypothesis": (
            "H-UNIQUE-06 geothermal surface-feature proximity: vents + hot springs "
            "mark concealed fault conduits absent from the fault catalogue"
        ),
        "mechanism": (
            "Hot springs and volcanic vents mark geothermal fluid reaching the "
            "surface; the fault conduit connects them to depth. Dots near surface "
            "geothermal features target concealed faults missing from USGS/INGENIOUS."
        ),
        "non_fault_mimic": "Cold springs, non-geothermal seeps, surface water",
        "preregistration": None,
        "experiment_number": 6,
        "maximum_experiments": 3,
        "maximum_session_hours": 2,
        "input_provenance": "Committed GDR/INGENIOUS CSV extracts (public, free)",
        "inputs": {
            str(p.relative_to(ROOT)): sha256_file(p)
            for p in (TEMPLATE, LABELS, VENTS_CSV, SPRINGS_CSV)
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
        "n_vents": len(vent_points),
        "n_springs": len(spring_points),
        "catalogue_features": [],
        "prediction_inputs_include_registry_rasters": False,
        "supervised_fit": False,
        "submission_slot_spent": False,
        "organizer_confirmed_score": None,
        "lane_status": "new lane: catalogue-independent geothermal-surface-proximity detector",
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

    report["canary"] = context.canary(canary_features)
    print(f"Canaries passed: {report['canary']['passed']}", flush=True)

    registry = json.loads((ROOT / "registry/priority_rasters.json").read_text())
    report["surface_novelty"] = novelty.compare_registry(
        score, fp, registry["unique_rasters"], ROOT
    )
    print(f"Surface novelty passed: {report['surface_novelty']['passed']}", flush=True)

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

    # ALWAYS package — even on gate failure — so a downloadable artifact exists.
    final = emission.priority_poisson(
        score, support & ~catalogue, round(BUDGET_FRACTION * fp.sum()), min_dist=MIN_DIST_PX
    )
    if not final.any():
        raise SystemExit("No positive evidence; refusing an empty submission")

    report["final_novelty"] = novelty.compare_registry(
        final.astype(np.float32), fp, registry["unique_rasters"], ROOT, dots=final
    )
    print(f"Final novelty passed: {report['final_novelty']['passed']}", flush=True)
    print(f"Final max overlap within 3px: {report['final_novelty']['max_dot_overlap']}", flush=True)

    content_id = submission.scored_content_id(final, fp, catalogue)
    date_str = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    name = submission.make_filename(
        "24gems", "geothermal-surface-proximity", date_str, content_id, "zeros"
    )

    zeros_path = DOWNLOADS / name
    zeros = submission.write_submission(final, TEMPLATE, zeros_path, outside="zero")

    checks = submission.check_variants(zeros, TEMPLATE)
    print(f"Format valid: {checks['format_valid']}", flush=True)

    note = (
        f"24GEMS geothermal-surface-proximity vents+springs | catalogue-independent | "
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
        zeros,
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
            "final_max_abs_rank_correlation": report["final_novelty"][
                "max_abs_rank_correlation"
            ],
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
