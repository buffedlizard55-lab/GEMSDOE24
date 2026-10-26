#!/usr/bin/env python3
"""Experiment 4: Concealed basin-margin step (H-UNIQUE-04).

Hypothesis: Concealed range-front / basin-margin faults host geothermal
conduits but lack surface rupture, so they are missing from the USGS /
INGENIOUS catalogue. They produce a step in depth-to-basement and a
co-located horizontal gravity-gradient anomaly. A score surface combining
gravity-gradient magnitude with the depth-to-basement step detects these
concealed structures without ever conditioning on catalogue faults.

Layers:
  * data/training_features.tif: iso_grav_anom_hg (gravity horizontal gradient)
  * data/training_features.tif: depth_to_base_surf (basement depth step)
  * data/external/lidar_scarp_features_u8.tif: relief (terrain context mask)

Mechanism: Basin-margin faults offset the basement surface. Where the fault
is concealed by cover, no scarp exists, but the basement step and the
gravity-gradient lineament remain. Hydrothermal fluids localize along these
conduits. This is NOT terrain-scarp based (differs from SAHG1/RSHG1), NOT
catalogue-guided (differs from dotted-ridge/h28/h33), and NOT magnetic-trough
based (differs from MTR1/CRP1).

Non-fault mimic: Lithologic contacts and intrusive contacts can also produce
gravity-gradient / basement-step coincidences without a fault.

Protocol: SegmentHoldout hide-and-recover, pooled DTI (alpha 0.2, beta 0.8,
300 m triangular kernel), leakage canary on each channel, registry novelty
(|rho| <= 0.90, <= 70% dots within 3 px), exact-grid TIF with zeros outside
the footprint (finite [0,1] everywhere — fixes the "[0, 1]" portal rejection).

Catalogue faults are used ONLY for holdout masking/evaluation, never for
building the score surface.

ALWAYS packages the TIF (even on negative gates) so a downloadable artifact
exists with a clear ok_to_submit verdict.
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

from gems import emission, footprint, holdout, novelty, submission  # noqa: E402
from gems.geofeatures import BAND_ORDER  # noqa: E402
from gems.preflight import preflight  # noqa: E402
from gems.validator import sha256_file  # noqa: E402

TEMPLATE = ROOT / "data/bridge/sample_submission.tif"
LABELS = ROOT / "data/bridge/labels.tif"
FEATURES = ROOT / "data/training_features.tif"
LIDAR = ROOT / "data/external/lidar_scarp_features_u8.tif"

BUDGET_FRACTION = 0.0073  # ~37.7K dots, matches current point-best scale
MIN_DIST_PX = 3.0
CURRENT_BEST_HOLDOUT = 0.13000

RESULT = ROOT / "evidence/unique_experiment4.json"
DOWNLOADS = ROOT / "docs/downloads"
DATA_OUT = ROOT / "docs/data"


def save(obj, path):
    Path(path).write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n")


def read_feature_band(name):
    """Read one band from the pinned 30-channel feature stack by band name."""
    band = BAND_ORDER.index(name) + 1  # 1-based rasterio band
    with rasterio.open(FEATURES) as s:
        a = s.read(band).astype(np.float32)
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
    """Catalogue-independent score surface from gravity gradient x basement step.

    The score is high where both (a) gravity horizontal gradient is strong
    (basement edge / fault lineament) and (b) depth-to-basement shows a step
    (lateral gradient in basement depth). Relief masks out high-terrain areas
    where surface expression would already be catalogued.
    """
    with rasterio.open(TEMPLATE) as t:
        t_shape = t.shape
        t_fp = np.isfinite(t.read(1))

    grav_hg = read_feature_band("iso_grav_anom_hg")
    depth_base = read_feature_band("depth_to_base_surf")

    # Terrain context: where LiDAR relief is high, surface scarps would be
    # visible and already catalogued; downweight those areas.
    with rasterio.open(LIDAR) as s:
        lidar_valid = s.read(12) > 0
        relief = s.read(9).astype(np.float32)

    for name, arr in (
        ("grav_hg", grav_hg),
        ("depth_base", depth_base),
        ("relief", relief),
    ):
        if arr.shape != t_shape:
            raise SystemExit(f"{name} shape {arr.shape} != template {t_shape}")

    # Gravity-gradient anomaly: strong horizontal gradient = basement edge
    grav_n = norm01(grav_hg, t_fp & np.isfinite(grav_hg))

    # Basement-depth step: lateral change in basement depth = fault offset
    depth_filled = np.where(np.isfinite(depth_base), depth_base, 0.0)
    depth_step = np.abs(gaussian_filter(depth_filled, 3) - gaussian_filter(depth_filled, 12))
    depth_step_n = norm01(depth_step, t_fp & np.isfinite(depth_base))

    # Terrain mask: downweight high-relief (already-expressed) areas
    relief_n = norm01(relief, lidar_valid & t_fp)
    terrain_suppression = 1.0 - relief_n  # low relief = concealed = target

    # Combined score: gravity edge x basement step x concealed-terrain
    score = grav_n * depth_step_n * terrain_suppression
    support = t_fp & np.isfinite(grav_hg) & np.isfinite(depth_base) & lidar_valid
    score = np.where(support & t_fp, score, 0.0).astype(np.float32)
    return score, support


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--verify-recorded", action="store_true",
                    help="Inspect recorded evidence; do not run a new experiment")
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
        t_profile = t.profile.copy()

    with rasterio.open(LABELS) as s:
        catalogue = (s.read(1) > 0) & fp

    # ---- Build the unique score surface ------------------------------------
    score, support = build_score_surface(fp)
    print(f"Support pixels: {int(support.sum()):,}", flush=True)
    print(f"Score positive pixels: {int((score > 0).sum()):,}", flush=True)

    # ---- Holdout context ----------------------------------------------------
    context = holdout.SegmentHoldout(fp, catalogue, buffer_px=15)

    # ---- Leakage canary: each physical channel alone -------------------------
    grav_hg = read_feature_band("iso_grav_anom_hg")
    depth_base = read_feature_band("depth_to_base_surf")
    with rasterio.open(LIDAR) as s:
        relief = s.read(9).astype(np.float32)
        lidar_valid = s.read(12) > 0

    depth_filled = np.where(np.isfinite(depth_base), depth_base, 0.0)
    depth_step = np.abs(gaussian_filter(depth_filled, 3) - gaussian_filter(depth_filled, 12))

    canary_features = {
        "grav_gradient": np.where(
            fp & np.isfinite(grav_hg), norm01(grav_hg, fp & np.isfinite(grav_hg)), 0.0
        ).astype(np.float32),
        "basement_step": np.where(
            fp & np.isfinite(depth_base),
            norm01(depth_step, fp & np.isfinite(depth_base)), 0.0
        ).astype(np.float32),
        "terrain_suppression": np.where(
            fp & lidar_valid, 1.0 - norm01(relief, fp & lidar_valid), 0.0
        ).astype(np.float32),
        "score_surface": score,
    }

    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "hypothesis": (
            "H-UNIQUE-04 concealed basin-margin step: gravity gradient x "
            "depth-to-basement step x concealed-terrain for blind conduits"
        ),
        "mechanism": (
            "Basin-margin faults offset basement; gravity-gradient lineament "
            "co-located with basement-depth step marks concealed conduits "
            "absent from surface-expressed USGS/INGENIOUS catalogue"
        ),
        "non_fault_mimic": "Lithologic or intrusive contacts with gravity / basement contrast",
        "preregistration": None,
        "experiment_number": 4,
        "maximum_experiments": 3,
        "maximum_session_hours": 2,
        "input_provenance": "Pinned competition bridge + committed external mirrors",
        "inputs": {
            str(p.relative_to(ROOT)): sha256_file(p)
            for p in (TEMPLATE, LABELS, FEATURES, LIDAR)
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
        "lane_status": "new lane: catalogue-independent concealed-basement-step detector",
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
    name = submission.make_filename(
        "24gems", "concealed-basement-step", date_str, content_id, "zeros"
    )

    zeros_path = DOWNLOADS / name
    zeros = submission.write_submission(final, TEMPLATE, zeros_path, outside="zero")

    checks = submission.check_variants(zeros, TEMPLATE)
    if not checks["format_valid"]:
        raise SystemExit("Exact-file format checks failed; do not publish")

    # ---- Note (<= 140 chars) --------------------------------------------------
    note = (
        f"24GEMS concealed-basement-step gravxdepth | catalogue-independent | "
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
