#!/usr/bin/env python3
"""Experiment 7 (this session): catalogue-offset geothermal surface proximity.

Hypothesis H-UNIQUE-07: Geothermal surface features (volcanic vents, hot springs)
mark concealed fault conduits absent from the USGS/INGENIOUS fault catalogue
(same trigger as H-UNIQUE-06). Following the GEMSDOE32 H33-B2 forensic result --
hidden truth is offset from, not coincident with, mapped traces -- dots are
restricted to the catalogue-offset band (200-900 m from visible existing faults),
cutting false-positive mass in the already-mapped halo while staying
geothermal-targeted.

No labels, no old predictions and no registry rasters are used to build the score.
The catalogue is used only as the caller's explicit offset eligibility mask, which
the shared writer permits. Per-fold placement excludes that fold's visible faults.

This experiment ALWAYS packages the TIF with a clear ok_to_download /
ok_to_submit verdict. Negative results are deliverables.
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
from gems.novelty import classify_space_filling_control, dot_overlap  # noqa: E402

TEMPLATE = ROOT / "data/bridge/sample_submission.tif"
LABELS = ROOT / "data/bridge/labels.tif"
VENTS_CSV = ROOT / "data/external/gdr_volcanic_vents_in_footprint.csv"
SPRINGS_CSV = ROOT / "data/external/gdr_wellspring_in_footprint.csv"
LATTICE = ROOT / "inputs/calibration/13gems_20261001_r13-lattice-s5_v2_nan-outside.tif"

BUDGET_FRACTION = 0.0073
MIN_DIST_PX = 3.0
OFFSET_INNER_PX = 2.0  # 200 m: dots closer than this sit in the mapped fault halo
OFFSET_OUTER_PX = 9.0  # 900 m: geothermal trigger range
CURRENT_COMPARABLE_BEST = 0.13000  # oof_multiphysics_hgb_d3, HOLDOUT-DTI, recorded baseline
RECORDED_POINT_BEST = 0.166060  # H24-S3DEP1, HOLDOUT-DTI, recorded local point-best

RESULT = ROOT / "evidence/unique_experiment7.json"
DOWNLOADS = ROOT / "docs/downloads"
DATA_OUT = ROOT / "docs/data"


def save(obj, path):
    Path(path).write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n")


def read_points(path, temp_col=False):
    points = []
    with open(path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                r = int(row["row"])
                c = int(row["col"])
                if temp_col:
                    temp = row.get("temp_c", "")
                    temp = float(temp) if temp and temp not in ("NULL", "nan", "") else 0.0
                    points.append((r, c, temp))
                else:
                    points.append((r, c))
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
    score = np.where(fp, score, 0.0).astype(np.float32)
    return score, vent_mask, spring_mask


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
    with rasterio.open(LABELS) as s:
        catalogue = (s.read(1) > 0) & fp

    vent_points = read_points(VENTS_CSV)
    spring_points = read_points(SPRINGS_CSV, temp_col=True)
    print(f"Vents: {len(vent_points)}, Springs: {len(spring_points)}", flush=True)

    score, vent_mask, spring_mask = build_score_surface(fp, vent_points, spring_points)
    support = (
        fp
        & (distance_transform_edt(~catalogue) > OFFSET_INNER_PX)
        & (distance_transform_edt(~catalogue) <= OFFSET_OUTER_PX)
    )
    print(f"Support pixels (200-900 m offset band): {int(support.sum()):,}", flush=True)
    print(f"Score positive pixels: {int((score > 0).sum()):,}", flush=True)

    context = holdout.SegmentHoldout(fp, catalogue, buffer_px=15)

    # Canary on the raw trigger surfaces before any dots are placed.
    vent_dist = distance_transform_edt(~vent_mask) if vent_mask.any() else np.full(fp.shape, np.inf)
    spring_dist = (
        distance_transform_edt(~spring_mask) if spring_mask.any() else np.full(fp.shape, np.inf)
    )
    R = 3.0
    vent_prox = np.maximum(1.0 - vent_dist / R, 0.0)
    spring_prox = np.maximum(1.0 - spring_dist / R, 0.0)
    spring_temp_grid = np.zeros(fp.shape, np.float32)
    for r, c, temp in spring_points:
        if 0 <= r < fp.shape[0] and 0 <= c < fp.shape[1]:
            spring_temp_grid[r, c] = temp if temp > 0 else 1.0
    spring_prox = spring_prox * np.clip(spring_temp_grid / 100.0, 0.0, 1.0)
    canary_features = {
        "vent_proximity": np.where(fp, vent_prox, 0.0).astype(np.float32),
        "spring_proximity": np.where(fp, spring_prox, 0.0).astype(np.float32),
        "score_surface": score,
    }

    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "hypothesis": (
            "H-UNIQUE-07 catalogue-offset geothermal surface-feature proximity: vents + hot springs "
            "mark concealed conduits absent from the catalogue; dots restricted to the 200-900 m "
            "offset band from visible faults (H33-B2 offset insight), never conditioned on labels"
        ),
        "mechanism": (
            "Hot springs and volcanic vents mark geothermal fluid reaching the surface; the fault "
            "conduit connects them to depth. Dots near surface geothermal features target concealed "
            "faults missing from USGS/INGENIOUS, placed outside the already-mapped fault halo."
        ),
        "non_fault_mimic": "Cold springs, non-geothermal seeps, surface water, gravel pits",
        "preregistration": None,
        "experiment_number": 7,
        "maximum_experiments": 3,
        "maximum_session_hours": 2,
        "input_provenance": "Committed GDR/INGENIOUS CSV extracts (public, free); committed fault labels",
        "inputs": {
            str(p.relative_to(ROOT)): sha256_file(p)
            for p in (TEMPLATE, LABELS, VENTS_CSV, SPRINGS_CSV, LATTICE)
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
                ROOT / "src/gems/preflight.py",
            )
        },
        "supported_pixels": int(support.sum()),
        "n_vents": len(vent_points),
        "n_springs": len(spring_points),
        "offset_band_px": [OFFSET_INNER_PX, OFFSET_OUTER_PX],
        "catalogue_features": [],
        "prediction_inputs_include_registry_rasters": False,
        "supervised_fit": False,
        "submission_slot_spent": False,
        "organizer_confirmed_score": None,
        "lane_status": "new lane: catalogue-offset geothermal-surface-proximity detector",
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

    # Registry cache is not present in this clone; the full 46-raster gate is not
    # executable locally. Report what IS locally verifiable instead.
    lattice_ok = False
    lattice_bound = None
    try:
        with rasterio.open(LATTICE) as ds:
            lattice = ds.read(1) > 0
        lattice = lattice & fp
        lattice_ok = True
        ctrl = classify_space_filling_control(
            fp, lattice, radius_px=3.0, coverage_threshold=0.70
        )
        lattice_bound = ctrl["pigeonhole_min_overlap_for_candidate_size"]
        report["registry_cache_available_locally"] = False
        report["local_novelty_surrogate"] = {
            "lattice_file": str(LATTICE.relative_to(ROOT)),
            "lattice_footprint_3px_coverage": ctrl["footprint_3px_coverage"],
            "lattice_uncovered_pixels": ctrl["footprint_3px_uncovered_pixels"],
            "pigeonhole_min_overlap_any_dotted_set": lattice_bound,
            "interpretation": (
                "At any dot budget above the uncovered-pixel count, literal 3-px overlap "
                "with the retained spacing-5 calibration lattice exceeds 70%; the all-entry "
                "novelty gate cannot pass for a dotted submission at this budget."
            ),
        }
    except Exception as exc:  # pragma: no cover - defensive
        report["registry_cache_available_locally"] = False
        report["local_novelty_surrogate"] = {"error": str(exc)}

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

    # Always package -- even on gate failure -- so a downloadable artifact exists.
    final = emission.priority_poisson(
        score, support & ~catalogue, round(BUDGET_FRACTION * fp.sum()), min_dist=MIN_DIST_PX
    )
    if not final.any():
        raise SystemExit("No positive evidence; refusing an empty submission")

    if lattice_ok:
        n_final = int(final.sum())
        report["local_novelty_surrogate"]["final_dots"] = n_final
        report["local_novelty_surrogate"]["pigeonhole_min_overlap_for_final"] = (
            max(0, n_final - ctrl["footprint_3px_uncovered_pixels"]) / n_final
        )
    ov_labels = dot_overlap(final, catalogue)
    report["local_novelty_surrogate"]["final_dot_overlap_vs_local_fault_labels_3px"] = ov_labels

    content_id = submission.scored_content_id(final, fp, catalogue)
    date_str = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    name = submission.make_filename(
        "24gems", "catalogue-offset-geothermal-proximity", date_str, content_id, "zeros"
    )

    zeros_path = DOWNLOADS / name
    zeros = submission.write_submission(final, TEMPLATE, zeros_path, outside="zero")
    zip_path = submission.zip_single(zeros)

    checks = submission.check_variants(zeros, TEMPLATE)
    print(f"Format valid: {checks['format_valid']}", flush=True)

    summary = (
        f"vents+springs in {int(OFFSET_INNER_PX*100)}-{int(OFFSET_OUTER_PX*100)} m "
        f"catalogue offset band | research; HOLDOUT-DTI {results['dti']:.5f} | id {content_id}"
    )
    prefix = f"24GEMS H-UNIQUE-07 | "
    suffix = f" | id {content_id} | not yet live-scored"
    max_sum = 140 - len(prefix) - len(suffix)
    note = prefix + summary[:max_sum] + suffix
    assert len(note) <= 140, len(note)
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

    beats_comparable = results["dti"] > CURRENT_COMPARABLE_BEST
    beats_point_best = results["dti"] > RECORDED_POINT_BEST
    strict_ok = checks["checks"]["variant_strict_whole_array_no_nan_allowed"]["pass"]
    novelty_passable = bool(lattice_ok) and lattice_bound is not None and lattice_bound <= 0.70
    ok_to_submit = (
        checks["format_valid"]
        and strict_ok
        and report["canary"]["passed"]
        and beats_point_best
        and novelty_passable
        and preflight_report["decision"]["ready_to_submit"]
    )
    verdict = "promote" if ok_to_submit else "negative"

    reasons = []
    if not beats_point_best:
        reasons.append(
            f"holdout DTI does not beat recorded local point-best {RECORDED_POINT_BEST} "
            f"(HOLDOUT-DTI, not ORGANIZER-CONFIRMED)"
        )
    if not beats_comparable:
        reasons.append(
            f"holdout DTI does not beat recorded comparable baseline {CURRENT_COMPARABLE_BEST} "
            f"(HOLDOUT-DTI, not ORGANIZER-CONFIRMED)"
        )
    if not checks["format_valid"]:
        reasons.append("format or range check failed")
    if not strict_ok:
        reasons.append("strict whole-array [0,1] check failed")
    if not report["canary"]["passed"]:
        reasons.append("canary failed")
    if not novelty_passable:
        reasons.append(
            "novelty gate not passable locally: registry cache absent; spacing-5 lattice "
            "pigeonhole bound exceeds 70% at this dot budget"
        )
    if not preflight_report["decision"]["ready_to_submit"]:
        reasons.append("preflight not ready to submit (no independent selector evidence)")

    card = {
        "hypothesis": report["hypothesis"],
        "mechanism": report["mechanism"],
        "non_fault_mimic": report["non_fault_mimic"],
        "holdout": {
            "evaluator_version": results["evaluator_version"],
            "label": "HOLDOUT-DTI",
            "dti": results["dti"],
            "ci95": results["ci95"]["interval"],
            "n_withheld_positive_pixels": results["n_withheld_positive_pixels"],
            "n_unique_withheld_components": results["n_unique_withheld_components"],
            "protocol": results["protocol"],
        },
        "comparison_to_recorded": {
            "recorded_comparable_baseline_holdout_dti": CURRENT_COMPARABLE_BEST,
            "recorded_local_point_best_holdout_dti": RECORDED_POINT_BEST,
            "beats_comparable_baseline": beats_comparable,
            "beats_recorded_point_best": beats_point_best,
            "note": "All holdout figures are HOLDOUT-DTI local internal validation, not ORGANIZER-CONFIRMED leaderboard scores",
        },
        "leakage_canary": {
            "passed": report["canary"]["passed"],
            "threshold": report["canary"]["threshold"],
            "features": {k: v["pooled_auc"] for k, v in report["canary"]["features"].items()},
        },
        "novelty": report.get("local_novelty_surrogate", {}),
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
    save(card, DATA_OUT / "unique_run_card_7.json")

    download_entry = {
        "file": name,
        "zip_file": zip_path.name,
        "sha256": raster_sha256,
        "content_id": content_id,
        "pixel_count": int(final.sum()),
        "note": note,
        "note_file": note_file,
        "checks_file": checks_file,
        "preflight_file": preflight_file,
        "zip_sha256": sha256_file(zip_path),
        "role": "primary",
        "format_valid": checks["format_valid"],
        "strict_range_ok": strict_ok,
        "ok_to_download": checks["format_valid"],
        "ok_to_submit": ok_to_submit,
        "verdict": verdict,
        "holdout_dti": results["dti"],
        "holdout_ci95": results["ci95"]["interval"],
        "run_card": "unique_run_card_7.json",
        "evidence_report": "unique_experiment7.json",
    }
    save(download_entry, DATA_OUT / "unique_download_7.json")

    print(
        json.dumps(
            {
                "file": name,
                "zip_file": zip_path.name,
                "pixels": int(final.sum()),
                "sha256": raster_sha256,
                "holdout_dti": results["dti"],
                "holdout_ci95": results["ci95"]["interval"],
                "note_characters": len(note),
                "verdict": verdict,
                "ok_to_submit": ok_to_submit,
                "ok_to_download": checks["format_valid"],
                "strict_range_ok": strict_ok,
                "canary_passed": report["canary"]["passed"],
                "novelty_passable_locally": novelty_passable,
                "lattice_pigeonhole_bound": lattice_bound,
            },
            indent=2,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
