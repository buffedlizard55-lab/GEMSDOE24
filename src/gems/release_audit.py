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
    """Revalidate the current S3DEP1 research download without rerunning it.

    H24-S3DEP1 is the repository's recorded local point-best. It remains a
    negative, research-only artifact; its current metadata, run card and
    selector must bind to the same exact TIFF. This audit does not replay the
    scientific measurement or confer submission authorization.
    """
    metadata = json.loads((root / "docs/data/s3dep1_download.json").read_text())
    card = json.loads((root / "evidence/s3dep1_run_card_20261026.json").read_text())
    selector = json.loads((root / "evidence/s3dep1_selector_20261026.json").read_text())
    if (
        metadata.get("verdict") != "negative"
        or metadata.get("ok_to_submit") is not False
        or metadata.get("submission_authorized") is not False
        or card.get("verdict") != "negative"
        or card.get("ok_to_submit") is not False
        or card.get("submission_authorized") is not False
        or selector.get("decision") != "DO_NOT_SUBMIT"
        or selector.get("ok_to_submit") is not False
    ):
        raise ValueError("Current research download must remain negative")
    name = metadata.get("file", "")
    if (
        not name
        or Path(name).name != name
        or not name.endswith(".tif")
        or card.get("submission_name") != name
    ):
        raise ValueError("Download metadata and run-card filename disagree")
    digest = metadata.get("sha256")
    if digest != card.get("raster_sha256") or digest != selector.get("artifact_sha256"):
        raise ValueError("Download metadata, run card and selector hashes disagree")
    note = metadata.get("note")
    if not isinstance(note, str) or not 0 < len(note) <= 140 or note != card.get("note"):
        raise ValueError("Research note is missing, inconsistent or outside 1–140 characters")
    note_file = metadata.get("note_file", "")
    if not note_file or Path(note_file).name != note_file:
        raise ValueError("Download note filename is unsafe or missing")
    if (root / "docs/downloads" / note_file).read_text().strip() != note:
        raise ValueError("Download note file disagrees with its receipt")
    fresh = check_variants(
        root / "docs/downloads" / name, root / "data/bridge/sample_submission.tif"
    )
    if not fresh["format_valid"] or fresh["sha256"] != digest:
        raise ValueError("Current download hash or format verification failed")
    stored = card.get("validator_output", {})
    if not stored:
        raise ValueError("Current download validator receipt is absent")
    with rasterio.open(root / "docs/downloads" / name) as dataset:
        expected = {
            "sha256": fresh["sha256"],
            "format_valid": fresh["format_valid"],
            "format_acceptable": fresh["format_acceptable"],
            "strict_whole_array_values_in_0_1": fresh["checks"][
                "variant_strict_whole_array_no_nan_allowed"
            ]["pass"],
            "no_nan_in_footprint": fresh["checks"]["footprint_all_finite"]["pass"],
            "footprint_range_0_1": fresh["checks"]["footprint_range_0_1"]["pass"],
            "crs": str(dataset.crs),
            "shape": list(dataset.shape),
            "transform": list(dataset.transform)[:6],
            "positive_pixels": fresh["in_footprint_positive_pixels"],
        }
    # S3DEP1's frozen run card records format, CRS and shape, but not a
    # transform field. check_variants independently reopens the exact TIFF and
    # verifies both shape and geotransform against the submission template.
    required = set(expected) - {"transform"}
    if not required.issubset(stored):
        raise ValueError("Current download validator receipt is incomplete")
    if (
        not fresh["checks"]["shape_matches_template"]["pass"]
        or not fresh["checks"]["geotransform_matches_template"]["pass"]
    ):
        raise ValueError("Current download shape or transform differs from template")
    for key, value in expected.items():
        if key in stored and stored[key] != value:
            raise ValueError(f"Current download receipt disagrees: {key}")
    if not fresh["checks"]["variant_strict_whole_array_no_nan_allowed"]["pass"]:
        raise ValueError("First-screen download must be finite and in [0,1] everywhere")
    return {
        "audit_kind": "current exact-file revalidation; no experiment rerun",
        "run_card": "evidence/s3dep1_run_card_20261026.json",
        "selector": "evidence/s3dep1_selector_20261026.json",
        "validator_output": fresh,
        "scientific_evidence": "recorded; not rerun or independently confirmed",
        "ok_to_download": True,
        "ok_to_submit": False,
        "submission_authorized": False,
        "verdict": "negative",
    }


def verify_featured_downloads(root: Path) -> dict:
    """Audit the two featured negative packets, rather than a historical default.

    Check actual bytes with the shared validator; this is not a scientific replay
    or selector. Any contradictory identity or authorization fails closed.
    """
    rows = []
    for lane in ("gvc1", "rshg1"):
        metadata = json.loads((root / f"docs/data/{lane}_download.json").read_text())
        card = json.loads((root / f"evidence/{lane}_run_card_20261025.json").read_text())
        for record in (metadata, card):
            if record.get("verdict") != "negative" or record.get("ok_to_submit") is not False:
                raise ValueError(f"{lane}: featured research packet cannot authorize submission")
            if record.get("submission_authorized", False) is not False:
                raise ValueError(f"{lane}: contradictory authorization")
        name, note = metadata.get("file", ""), metadata.get("note")
        if not name or Path(name).name != name or not name.endswith("-zeros.tif"):
            raise ValueError(f"{lane}: unsafe or non-zero-outside filename")
        if not isinstance(note, str) or not 0 < len(note) <= 140:
            raise ValueError(f"{lane}: invalid note")
        note_name = metadata.get("note_file", "")
        if not note_name or Path(note_name).name != note_name:
            raise ValueError(f"{lane}: unsafe note filename")
        if (root / "docs/downloads" / note_name).read_text().strip() != note:
            raise ValueError(f"{lane}: note content mismatch")
        if card.get("submission_name") != name or card.get("note") != note:
            raise ValueError(f"{lane}: card identity mismatch")
        fresh = check_variants(
            root / "docs/downloads" / name, root / "data/bridge/sample_submission.tif"
        )
        if not fresh["format_valid"] or not (
            fresh["sha256"] == metadata.get("sha256") == card.get("raster_sha256")
        ):
            raise ValueError(f"{lane}: format or SHA-256 mismatch")
        if not fresh["checks"]["variant_strict_whole_array_no_nan_allowed"]["pass"]:
            raise ValueError(f"{lane}: whole-array finite [0,1] check failed")
        stored = card.get("validator_output", {})
        if not stored or any(fresh.get(k) != v for k, v in stored.items()):
            raise ValueError(f"{lane}: stored validator output mismatch")
        rows.append({"lane": lane, "file": name, "note": note, "validator_output": fresh})
    return {
        "audit_kind": "featured exact-file revalidation; no experiment rerun",
        "files": rows,
        "ok_to_download": True,
        "ok_to_submit": False,
        "submission_authorized": False,
        "scientific_evidence": "recorded, not replayed; novelty gates remain failed",
        "verdict": "negative",
    }
