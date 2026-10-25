#!/usr/bin/env python3
"""One fixed OJ1 experiment; preserve negative outcomes and never select a slot."""

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
from gems import emission, holdout, novelty, orientation_junction, submission  # noqa: E402
from gems.preflight import preflight  # noqa: E402
from gems.validator import sha256_file  # noqa: E402

CARD = ROOT / "evidence/oj1_run_card_20261025.json"
REPORT = ROOT / "evidence/oj1_experiment_20261025.json"
TEMPLATE = ROOT / "data/bridge/sample_submission.tif"
LABELS = ROOT / "data/bridge/labels.tif"
LIDAR = ROOT / "data/external/lidar_scarp_features_u8.tif"
REGISTRY = ROOT / "registry/priority_rasters.json"
PREREG_COMMIT = "4a112db"


def save(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n")


def verify_recorded(root=ROOT):
    """Reopen bytes and recompute pooled metrics; never rerun or tune a lane."""
    card = json.loads((root / CARD.relative_to(ROOT)).read_text())
    report = json.loads((root / REPORT.relative_to(ROOT)).read_text())
    if card["verdict"] != "negative" or card["submission_authorized"] is not False:
        raise ValueError("OJ1 negative decision changed")
    if report["run_card"] != card:
        raise ValueError("OJ1 report and run-card identity disagree")
    if card["holdout"] is not None:
        result = card["holdout"]
        pooled = holdout.pooled_components(result["folds"])
        for key in ("dti", "TP_w", "FP_w", "FN_w", "n_truth", "n_emitted"):
            if not np.isclose(result[key], pooled[key], rtol=1e-12, atol=1e-10):
                raise ValueError(f"OJ1 pooled {key} does not match folds")
    if card["submission_name"] is not None:
        path = root / "docs/downloads" / card["submission_name"]
        if sha256_file(path) != card["raster_sha256"]:
            raise ValueError("OJ1 raster checksum mismatch")
        checks = submission.check_variants(path, root / TEMPLATE.relative_to(ROOT))
        if checks != card["validator_output"]:
            raise ValueError("OJ1 exact-file validator output changed")
        if not checks["checks"]["variant_strict_whole_array_no_nan_allowed"]["pass"]:
            raise ValueError("OJ1 strict range failed")
    return card


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-recorded", action="store_true")
    args = parser.parse_args()
    if args.verify_recorded:
        print(json.dumps(verify_recorded(), indent=2, allow_nan=False))
        return
    if REPORT.exists() or CARD.exists():
        raise SystemExit(
            "Frozen lane already executed; use --verify-recorded. No reruns or tuning."
        )
    started = time.monotonic()
    manifest = json.loads((ROOT / "data/manifest.json").read_text())["files"]
    for path in (TEMPLATE, LABELS, LIDAR):
        relative = str(path.relative_to(ROOT / "data"))
        if sha256_file(path) != manifest[relative]["sha256"]:
            raise ValueError(f"Input checksum mismatch: {relative}")
    with rasterio.open(TEMPLATE) as ds:
        fp = np.isfinite(ds.read(1))
        grid = ds.shape, ds.crs, ds.transform
    with rasterio.open(LABELS) as ds:
        if (ds.shape, ds.crs, ds.transform) != grid:
            raise ValueError("Label grid mismatch")
        labels = fp & (ds.read(1) > 0)
    with rasterio.open(LIDAR) as ds:
        if (ds.shape, ds.crs, ds.transform) != grid:
            raise ValueError("LiDAR grid mismatch")
        bands = {name: ds.read(spec[0]) for name, spec in orientation_junction.BANDS.items()}
    registry = json.loads(REGISTRY.read_text())
    # Fail before any scientific result if the pinned comparison set is incomplete.
    for row in registry["unique_rasters"]:
        if sha256_file(ROOT / row["cache_path"]) != row["sha256"]:
            raise ValueError(f"Registry blob mismatch: {row['id']}")
    context = holdout.SegmentHoldout(fp, labels, buffer_px=15)
    surface, features, support = orientation_junction.factors(bands, fp)
    card = {
        "hypothesis": "OJ1: locally coherent scarp orientation junctions expose short unmapped branches",
        "mechanism": "5x5 doubled-angle dispersion x cell coherence x balanced curvature x sqrt(step)",
        "non_fault_mimic": "Dendritic stream confluences and road junctions",
        "lane_status": "provisional unassigned research lane; no assigned method paragraph supplied",
        "holdout": None,
        "correlation_overlap_vs_registry": {},
        "raster_sha256": None,
        "validator_output": None,
        "submission_name": None,
        "note": "OJ1 orientation-junction hypothesis | research only; DO NOT SUBMIT",
        "verdict": "negative",
        "submission_authorized": False,
        "ok_to_submit": False,
        "ok_to_download": False,
        "organizer_confirmed_score": None,
        "submission_slots_used": 0,
    }
    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "preregistration": "knowledge/17_preregistered_OJ1_2026-10-25.md",
        "preregistration_commit": PREREG_COMMIT,
        "inputs": {
            str(p.relative_to(ROOT)): sha256_file(p) for p in (TEMPLATE, LABELS, LIDAR, REGISTRY)
        },
        "code_sha256": {
            str(p.relative_to(ROOT)): sha256_file(p)
            for p in (
                Path(__file__),
                ROOT / "src/gems/orientation_junction.py",
                ROOT / "src/gems/holdout.py",
                ROOT / "src/gems/novelty.py",
                ROOT / "src/gems/metric.py",
                ROOT / "src/gems/submission.py",
            )
        },
        "supported_pixels": int(support.sum()),
        "prediction_inputs_include_registry_rasters": False,
        "surface_reads_catalogue": False,
        "experiments_run": 1,
        "maximum_experiments": 3,
        "maximum_session_seconds": 7200,
        "registry_scope": registry["scope"],
    }

    def finish(reason):
        card["stopped_reason"] = reason
        report.update(elapsed_seconds=time.monotonic() - started, run_card=card)
        save(CARD, card)
        save(REPORT, report)
        save(ROOT / "docs/data/oj1_run_card.json", card)
        if card["submission_name"]:
            artifact = ROOT / "docs/downloads" / card["submission_name"]
            receipt = preflight(
                artifact,
                TEMPLATE,
                run_card_path=CARD,
                expected_template_sha256=manifest["bridge/sample_submission.tif"]["sha256"],
            )
            save(artifact.with_suffix(".preflight.json"), receipt)
        print(json.dumps(card, indent=2, allow_nan=False), flush=True)

    card["leakage_canary"] = context.canary(features)
    del features, bands
    print("All source/transform canaries tested", flush=True)
    if not card["leakage_canary"]["passed"]:
        return finish("leakage-canary; stopped before placement")
    if time.monotonic() - started >= 7200:
        return finish("time-budget; stopped before placement")
    before = novelty.compare_registry(surface, fp, registry["unique_rasters"], ROOT)
    card["correlation_overlap_vs_registry"]["surface"] = before
    if not before["passed"]:
        return finish("duplicate-surface; stopped before placement")
    print("Pre-placement full-registry check passed", flush=True)
    predictions = [
        emission.priority_poisson(
            surface,
            fold["valid"] & ~fold["visible"] & (surface > 0),
            round(0.0073 * fold["valid"].sum()),
            min_dist=3.0,
        )
        for fold in context.folds
    ]
    card["holdout"] = context.summarize(predictions)
    del predictions
    baseline_path = ROOT / "evidence/sahg1_run_card_20261025.json"
    baseline = json.loads(baseline_path.read_text())["reconstructed_oof_multiphysics_baseline"]
    comparable = (
        baseline["evaluator_version"] == card["holdout"]["evaluator_version"]
        and baseline["protocol"] == card["holdout"]["protocol"]
        and baseline["n_withheld_positive_pixels"] == card["holdout"]["n_withheld_positive_pixels"]
    )
    card["recorded_baseline_comparison"] = {
        "label": "HOLDOUT-DTI",
        "source": str(baseline_path.relative_to(ROOT)),
        "source_sha256": sha256_file(baseline_path),
        "holdout": baseline,
        "same_declared_protocol": comparable,
        "baseline_replayed_this_session": False,
        "candidate_beats_recorded_baseline": comparable
        and card["holdout"]["dti"] > baseline["dti"],
        "limit": "Comparison with recorded OOF result, not a newly reconstructed baseline certificate or hidden-score forecast.",
    }
    if time.monotonic() - started >= 7200:
        return finish("time-budget; no final placement")
    final = emission.priority_poisson(
        surface, fp & ~labels & (surface > 0), round(0.0073 * fp.sum()), min_dist=3.0
    )
    content_id = submission.scored_content_id(final, fp, labels)
    name = f"gems24-oj1-{content_id}-RESEARCH-NOT-SUBMISSION-zeros.tif"
    path = ROOT / "docs/downloads" / name
    submission.write_submission(final, TEMPLATE, path, outside="zero")
    card.update(
        raster_sha256=sha256_file(path),
        validator_output=submission.check_variants(path, TEMPLATE),
        submission_name=name,
        note=f"OJ1 coherent orientation junctions | research only; DO NOT SUBMIT | id {content_id}",
    )
    card["ok_to_download"] = card["validator_output"]["format_valid"] is True
    if not card["ok_to_download"]:
        return finish("exact-file format failed")
    after = novelty.compare_registry(
        final.astype(np.float32), fp, registry["unique_rasters"], ROOT, dots=final
    )
    card["correlation_overlap_vs_registry"]["final_dots"] = after
    # Do not alter the dots, try another hypothesis, or select a slot after failure.
    if not after["passed"]:
        return finish("duplicate-final-dots; lane stopped without tuning or slot selection")
    finish(
        "research complete; independent exact-file nuisance audit and selector/quota evidence absent"
    )


if __name__ == "__main__":
    main()
