#!/usr/bin/env python3
"""Verify the frozen negative receipt and exact files, without running an experiment."""

from __future__ import annotations

import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems import holdout, submission  # noqa: E402
from gems.validator import sha256_file  # noqa: E402

SOURCE_COMMIT = "b6b4cc06f5842a5b5fdde5d9fca388f0e334fdf9"


def verify_sources(report):
    """Fingerprint the actual committed code used, not later integration refactors."""
    for name, digest in report["code_sha256"].items():
        try:
            code = subprocess.check_output(
                ["git", "show", f"{SOURCE_COMMIT}:{name}"], cwd=ROOT, stderr=subprocess.PIPE
            )
        except subprocess.CalledProcessError as exc:
            raise ValueError("Original source commit unavailable; fetch full Git history") from exc
        if hashlib.sha256(code).hexdigest() != digest:
            raise ValueError(f"Frozen experiment source fingerprint mismatch: {name}")
    return {"source_commit": SOURCE_COMMIT, "source_files_verified": len(report["code_sha256"])}


def verify():
    def load(name):
        return json.loads((ROOT / name).read_text())

    report = load("evidence/mtr1_experiment.json")
    card = load("evidence/mtr1_run_card.json")
    metadata = load("docs/data/independent_download.json")
    registry = load("registry/priority_rasters.json")
    if report["verdict"] != "negative" or report["stopped_reason"] != "duplicate-final-dots":
        raise ValueError("Frozen negative stop is missing or changed")
    provenance = verify_sources(report)
    for name, arm in report["results"].items():
        pooled = holdout.pooled_components(arm["folds"])
        for key in ("dti", "TP_w", "FP_w", "FN_w", "n_truth", "n_emitted"):
            if not math.isclose(pooled[key], arm[key], rel_tol=1e-12, abs_tol=1e-10):
                raise ValueError(f"Recorded {name} pooled {key} disagrees with its fold components")
        lo, hi = arm["ci95"]["interval"]
        if not 0 <= lo <= arm["dti"] <= hi <= 1:
            raise ValueError("Invalid recorded confidence interval")
        if arm["evaluator_version"] != holdout.MTR_EVALUATOR_VERSION:
            raise ValueError("Recorded MTR evaluator policy version changed")
    if card["holdout"] != report["results"]["candidate"]:
        raise ValueError("Run card is not the frozen tested candidate result")
    if card["holdout"]["n_withheld_positive_pixels"] != sum(
        f["withheld_positive_pixels"] for f in report["fold_integrity"]
    ):
        raise ValueError("Withheld-positive count disagrees across evidence")
    if (
        card["ok_to_submit"] is not False
        or metadata["ok_to_submit"] is not False
        or card["lane_uniqueness_gate_passed"] is not False
        or card["verdict"] != "negative"
        or card["submission_slots_used"] != 0
        or report["submission_slot_spent"] is not False
    ):
        raise ValueError("Negative result or zero-slot policy was weakened")
    template = ROOT / "data/bridge/sample_submission.tif"
    with rasterio.open(template) as ds:
        fp = np.isfinite(ds.read(1))
    names = (card["submission_name"], card["nan_outside_artifact"])
    sidecars = load("docs/downloads/" + metadata["checks_file"])
    arrays, actual_checks = [], []
    for name, key in zip(names, ("zero_outside", "nan_outside")):
        path = ROOT / "docs/downloads" / name
        digest = sha256_file(path)
        if digest != sidecars[key]["sha256"] or name != sidecars[key]["file"]:
            raise ValueError("Exact-file sidecar mismatch")
        checks = submission.check_variants(path, template)
        if not checks["format_valid"] or checks["ok_to_upload"] or checks["submission_authorized"]:
            raise ValueError("Format validity is not scientific authorization")
        with rasterio.open(path) as ds:
            arrays.append(ds.read(1))
        actual_checks.append(checks)
    if (
        sha256_file(ROOT / "docs/downloads" / names[0]) != card["raster_sha256"]
        or card["raster_sha256"] != metadata["sha256"]
        or metadata["file"] != names[0]
    ):
        raise ValueError("Primary bytes/name disagree with the run card")
    if not np.array_equal(arrays[0][fp], arrays[1][fp]):
        raise ValueError("Outside-footprint variants changed the predictions")
    if not np.isfinite(arrays[0]).all() or not np.isnan(arrays[1][~fp]).all():
        raise ValueError("Outside-footprint conventions changed")
    content = hashlib.sha256(np.asarray(arrays[0][fp], dtype="<f4").tobytes()).hexdigest()
    if any(content == row["footprint_sha256"] for row in registry["unique_rasters"]):
        raise ValueError("Audit TIFF is byte-different but duplicates previous footprint content")
    if metadata["note"] != card["note"] or len(card["note"]) > 140:
        raise ValueError("Note changed or exceeds 140 characters")
    note = (ROOT / "docs/downloads" / metadata["note_file"]).read_text().strip()
    if note != card["note"]:
        raise ValueError("Note file disagrees with metadata")
    final = report["final_novelty"]
    if final["passed"] is not False or final["max_dot_overlap"] != 1.0:
        raise ValueError("Duplicate-overlap veto was changed")
    return {
        "verified": True,
        "experiment_rerun": False,
        **provenance,
        "pooled_arms_verified": len(report["results"]),
        "variant_files_verified": len(actual_checks),
        "raster_sha256": card["raster_sha256"],
        "no_nan_inside_footprint": True,
        "range_0_1": True,
        "crs_shape_transform_match": True,
        "content_identical_to_registry": False,
        "lane_uniqueness_passed": False,
        "ok_to_submit": False,
        "verdict": "negative",
    }


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2, allow_nan=False))
