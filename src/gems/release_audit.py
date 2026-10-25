"""Reopen current research downloads; never treat stored receipts as validation.

This verifies a frozen negative result, not a new experiment or selector decision.
Scientific findings remain recorded evidence, not independently rerun measurements.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import rasterio

from .submission import check_variants


def verify_research_release(root: Path) -> dict:
    def load(path):
        return json.loads(path.read_text())

    report = load(root / "evidence/aspc_run_20261025.json")
    card = load(root / "evidence/aspc_run_card_20261025.json")
    if (
        report.get("submission_authorized") is not False
        or card.get("submission_authorized") is not False
        or card.get("verdict") != "negative"
        or report.get("slot_spent") is not False
    ):
        raise ValueError("Frozen research release cannot authorize a submission")
    if not report.get("blockers") or report["blockers"] != card.get("blockers"):
        raise ValueError("Report/card promotion blockers disagree or are absent")
    if report.get("template_convention_companion") != card.get("template_convention_companion"):
        raise ValueError("Report/card companion identity disagree")
    primary = report["artifact"]
    if (
        card.get("submission_name") != primary["file"]
        or card.get("raster_sha256") != primary["sha256"]
    ):
        raise ValueError("Run card and artifact identity disagree")
    if card.get("holdout_dti") != report.get("holdout"):
        raise ValueError("Run card and recorded holdout disagree")
    if not isinstance(primary.get("note"), str) or not 0 < len(primary["note"]) <= 140:
        raise ValueError("Research note must contain 1–140 characters")
    if card.get("note") != primary["note"]:
        raise ValueError("Run card and artifact note disagree")
    template = root / "data/bridge/sample_submission.tif"
    results, arrays = [], []
    for row, card_receipt in (
        (primary, card["validator_output"]),
        (
            report["template_convention_companion"],
            card["template_convention_companion"]["validator_output"],
        ),
    ):
        name = row["file"]
        if Path(name).name != name or not name.endswith(".tif"):
            raise ValueError("Download must be a plain TIFF filename")
        if row.get("submission_authorized") is not False:
            raise ValueError("Research artifact cannot authorize a submission")
        path = root / "docs/downloads" / name
        fresh = check_variants(path, template)
        stored = load(path.with_suffix(".checks.json"))
        if not fresh["format_valid"] or fresh["sha256"] != row["sha256"]:
            raise ValueError("Exact-file hash or format verification failed")
        # Validators may add explanatory fields after a frozen run. Every
        # recorded field must still match; never rewrite historical receipts.
        if not stored == row.get("validator_output", card_receipt) == card_receipt or any(
            fresh.get(key) != value for key, value in stored.items()
        ):
            raise ValueError("Fresh validator output disagrees with stored receipts")
        with rasterio.open(path) as ds:
            arrays.append(ds.read(1))
        results.append(fresh)
    with rasterio.open(template) as ds:
        footprint = np.isfinite(ds.read(1))
    if not np.array_equal(arrays[0][footprint], arrays[1][footprint]):
        raise ValueError("Companion changed in-footprint predictions")
    if not np.isfinite(arrays[0]).all() or not np.isnan(arrays[1][~footprint]).all():
        raise ValueError("Outside-footprint conventions disagree with release labels")
    return {
        "audit_kind": "exact-file revalidation, not a new geological experiment",
        "files": results,
        "same_in_footprint_predictions": True,
        "scientific_evidence": "recorded; confirmation folds not rerun",
        "submission_authorized": False,
        "verdict": "negative",
    }


def verify_current_download(root: Path) -> dict:
    """Revalidate the first-screen negative download without rerunning its lane.

    Does not certify novelty or scientific measurements; those remain frozen
    observations. A valid TIFF alone can never authorize an upload.
    """
    card = json.loads((root / "docs/data/unique_run_card.json").read_text())
    if card.get("verdict") != "negative" or card.get("ok_to_submit") is not False:
        raise ValueError("Current research download must remain negative")
    name = card.get("submission_name", "")
    if not name or Path(name).name != name or not name.endswith(".tif"):
        raise ValueError("Download must be a plain TIFF filename")
    note = card.get("note")
    if not isinstance(note, str) or not 0 < len(note) <= 140:
        raise ValueError("Research note must contain 1–140 characters")
    fresh = check_variants(
        root / "docs/downloads" / name, root / "data/bridge/sample_submission.tif"
    )
    if not fresh["format_valid"] or fresh["sha256"] != card.get("raster_sha256"):
        raise ValueError("Current download hash or format verification failed")
    stored = card.get("validator_output", {})
    if not stored:
        raise ValueError("Current download receipt is absent")
    for key, value in stored.items():
        if value != fresh.get(key):
            raise ValueError(f"Current download receipt disagrees: {key}")
    if not fresh["checks"]["variant_strict_whole_array_no_nan_allowed"]["pass"]:
        raise ValueError("First-screen download must be finite and in [0,1] everywhere")
    return {
        "audit_kind": "current exact-file revalidation; no experiment rerun",
        "run_card": "docs/data/unique_run_card.json",
        "validator_output": fresh,
        "scientific_evidence": "recorded; not rerun or independently confirmed",
        "ok_to_download": True,
        "ok_to_submit": False,
        "submission_authorized": False,
        "verdict": "negative",
    }
