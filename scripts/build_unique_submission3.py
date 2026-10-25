#!/usr/bin/env python3
"""Experiment 3: Visible-fault-guided + radiometric modulation (H-UNIQUE-03).

Hypothesis: Blind fault extensions and stepovers adjacent to catalogued
folds host geothermal conduits. Dots are guided by proximity to VISIBLE
faults (proxy for withheld fault continuity) and weighted by radiometric
K-enrichment (hydrothermal alteration). This targets off-catalogue positions
near faults — the same structural insight as the high-scoring dotted/offcat
submissions (0.2477–0.2778) — but with a unique radiometric-K modulation
that no reviewed method uses.

Difference from reviewed methods:
  * h25/h28 dotted-ridge: dots along catalogue ridges, uniform weight.
  * d28-poisson-offcat: uniform off-catalogue Poisson dots, no physics.
  * h33 tip-stepper: dots at catalogue tips, no radiometric modulation.
  * SAHG1: LiDAR strike + Th/K + basement steps, different physics.
  * H-UNIQUE-01/02: purely physical, too diffuse / low DTI.

This experiment: score = exp(-dist_to_visible_fault / 300m) × K_anom × (1−ThK).
Dots placed off-catalogue (not on visible faults) via priority_poisson.
Catalogue used only via fold.visible (visible faults), never withheld truth.
Canary tests physical channels only (K, ThK); proximity is a structural prior.

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
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems import emission, footprint, holdout, novelty, submission  # noqa: E402
from gems.preflight import preflight  # noqa: E402
from gems.validator import sha256_file  # noqa: E402

TEMPLATE = ROOT / "data/bridge/sample_submission.tif"
LABELS = ROOT / "data/bridge/labels.tif"
RAD = ROOT / "data/external/geodawn_rad_u8.tif"
EXT = ROOT / "data/external/geodawn_extensions_u8.tif"

BUDGET_FRACTION = 0.0073
MIN_DIST_PX = 3.0
DIST_DECAY_PX = 300.0  # 300 m = matches DTI kernel radius
CURRENT_BEST_HOLDOUT = 0.13000

RESULT = ROOT / "evidence/unique_experiment3.json"
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

    raise SystemExit(
        "Retired: stopped historical lane; executed decay was 300 px (30 km), not 300 m. "
        "Catalogue-proximity canaries and independent selector evidence were incomplete. "
        "Use --verify-recorded for the frozen negative record; do not rerun or retune."
    )

    started = time.monotonic()
    fp = footprint.load_footprint()
    with rasterio.open(TEMPLATE) as t:
        t_shape, t_crs, t_tr = t.shape, t.crs, t.transform
        t_fp = np.isfinite(t.read(1))

    with rasterio.open(LABELS) as s:
        labels = (s.read(1) > 0) & t_fp

    context = holdout.SegmentHoldout(fp, labels, buffer_px=15)

    # ---- Read physical layers -----------------------------------------------
    k_band, rad_prof = read_u8_band(RAD, 1)
    thk_band, ext_prof = read_u8_band(EXT, 1)
    for name, prof in (("rad", rad_prof), ("ext", ext_prof)):
        if prof != (t_shape, t_crs, t_tr):
            raise SystemExit(f"{name} grid mismatch")

    k_anom = norm01(k_band, t_fp & (k_band > 0))
    thk_n = norm01(thk_band, t_fp & (thk_band > 0))
    alteration = 1.0 - thk_n

    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "hypothesis": (
            "H-UNIQUE-03 visible-fault-guided radiometric "
            "modulation: blind extensions near faults x K"
        ),
        "mechanism": (
            "Blind fault extensions/stepovers adjacent to visible "
            "catalogue faults; hydrothermal K enrichment near "
            "fault traces marks concealed conduits absent from "
            "USGS/INGENIOUS. Dots guided by visible-fault proximity "
            "and weighted by radiometric K — a unique combination "
            "not in any reviewed lane."
        ),
        "non_fault_mimic": (
            "Radiometrically altered alluvial fans or mineralized veins near mapped faults"
        ),
        "preregistration": "knowledge/unique_hypothesis_2026-10-25.md",
        "experiment_number": 3,
        "maximum_experiments": 3,
        "maximum_session_hours": 2,
        "input_provenance": ("Committed external mirrors (USGS GeoDAWN) and bridge labels"),
        "inputs": {str(p.relative_to(ROOT)): sha256_file(p) for p in (TEMPLATE, LABELS, RAD, EXT)},
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
        "supported_pixels": int(t_fp.sum()),
        "catalogue_features": ["distance_to_visible_fault"],
        "prediction_inputs_include_registry_rasters": False,
        "supervised_fit": False,
        "submission_slot_spent": False,
        "organizer_confirmed_score": None,
        "lane_status": "new lane: visible-fault-guided radiometric modulation",
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

    # ---- Leakage canary: physical channels ONLY ------------------------------
    canary_features = {
        "k_anomaly": np.where(t_fp & (k_band > 0), k_anom, 0.0).astype(np.float32),
        "alteration_thk": np.where(t_fp & (thk_band > 0), alteration, 0.0).astype(np.float32),
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

    # ---- Per-fold score surface: visible-fault proximity x K modulation ------
    registry = json.loads((ROOT / "registry/priority_rasters.json").read_text())

    fold_surfaces = []
    for f in context.folds:
        visible_dist = distance_transform_edt(~f["visible"])
        visible_prox = np.exp(-visible_dist / DIST_DECAY_PX)
        visible_prox = np.where(f["valid"], visible_prox, 0.0)

        surface = visible_prox * k_anom * alteration
        surface = np.where(f["valid"] & ~f["visible"], surface, 0.0).astype(np.float32)
        fold_surfaces.append(surface)

    # Surface novelty on mean fold surface (pre-placement).
    mean_surface = np.mean(fold_surfaces, axis=0).astype(np.float32)
    report["surface_novelty"] = novelty.compare_registry(
        mean_surface, fp, registry["unique_rasters"], ROOT
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

    # Holdout: dots per fold from fold-specific surface, off visible faults.
    predictions = []
    for f, surface in zip(context.folds, fold_surfaces):
        eligible = f["valid"] & ~f["visible"] & (surface > 0)
        predictions.append(
            emission.priority_poisson(
                surface, eligible, round(BUDGET_FRACTION * f["valid"].sum()), min_dist=MIN_DIST_PX
            )
        )

    results = context.summarize(predictions)
    report["holdout"] = results
    print(f"HOLDOUT-DTI {results['dti']} CI {results['ci95']['interval']}", flush=True)

    # ---- Final dots: proximity to ALL visible faults, off-catalogue ----------
    full_dist = distance_transform_edt(~labels)
    full_prox = np.exp(-full_dist / DIST_DECAY_PX)
    final_score = full_prox * k_anom * alteration
    final_score = np.where(t_fp & ~labels & (final_score > 0), final_score, 0.0).astype(np.float32)

    final = emission.priority_poisson(
        final_score,
        t_fp & ~labels & (final_score > 0),
        round(BUDGET_FRACTION * fp.sum()),
        min_dist=MIN_DIST_PX,
    )
    if not final.any():
        raise SystemExit("No positive evidence; refusing an empty submission")

    report["final_novelty"] = novelty.compare_registry(
        final.astype(np.float32), fp, registry["unique_rasters"], ROOT, dots=final
    )
    print(f"Final dots novelty passed: {report['final_novelty']['passed']}", flush=True)
    if not report["final_novelty"]["passed"]:
        max_ov = report["final_novelty"].get("max_dot_overlap")
        max_r = report["final_novelty"].get("max_abs_rank_correlation")
        print(f"  max overlap={max_ov}, max rank={max_r}", flush=True)

    # ---- Package TIF ALWAYS (zeros outside = finite [0,1] everywhere) --------
    content_id = submission.scored_content_id(final, fp, labels)
    date_str = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    name = submission.make_filename("24gems", "doer-fault-guided-k", date_str, content_id, "zeros")

    zeros_path = DOWNLOADS / name
    zeros = submission.write_submission(final, TEMPLATE, zeros_path, outside="zero")

    checks = submission.check_variants(zeros, TEMPLATE)
    if not checks["format_valid"]:
        raise SystemExit("Exact-file format checks failed; do not publish")

    note = (
        f"24GEMS fault-guided K-mod blind-conduit | off-catalogue dots | "
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
        "reasons": reasons,
        "organizer_confirmed_score": None,
        "experiments_run": 3,
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
