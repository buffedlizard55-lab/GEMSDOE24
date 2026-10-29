#!/usr/bin/env python3
"""Read-only exact-artifact verifier for the recorded GEO1 research TIFF.

This reopens the saved run card, download metadata, validator receipt, note,
ZIP member, exact GeoTIFF bytes and recorded source hashes. It does not rerun
feature construction, holdout, placement, or submission writing, and it never
promotes or uploads the artifact. A successful check is not authorization.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems.submission import check_variants  # noqa: E402
from gems.validator import sha256_file  # noqa: E402


def _read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot read JSON evidence: {path}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def verify(root: Path = ROOT) -> dict:
    root = Path(root).resolve()
    evidence = _read_json(root / "evidence/geo1_experiment.json")
    card = _read_json(root / "evidence/geo1_run_card.json")
    docs_card = _read_json(root / "docs/data/geo1_run_card.json")
    download = _read_json(root / "docs/data/geo1_download.json")
    if card != docs_card:
        raise ValueError("Evidence and docs GEO1 run cards disagree")
    if card.get("verdict") != "negative" or card.get("ok_to_submit") is not False:
        raise ValueError("GEO1 must remain negative and not authorized to submit")
    if evidence.get("verdict") != "negative" or evidence.get("submission_slot_spent") is not False:
        raise ValueError("Experiment receipt must retain its negative/no-slot decision")

    name = card.get("submission_name")
    if not isinstance(name, str) or Path(name).name != name or not name.endswith(".tif"):
        raise ValueError("Invalid GEO1 submission filename")
    tif = root / "docs/downloads" / name
    digest = sha256_file(tif)
    if digest != card.get("raster_sha256") or digest != evidence.get("raster_sha256"):
        raise ValueError("GEO1 GeoTIFF SHA-256 does not match its run cards")
    if download.get("file") != name or download.get("sha256") != digest:
        raise ValueError("GEO1 download metadata does not match the exact GeoTIFF")
    if (
        download.get("ok_to_submit") is not False
        or download.get("recommended_for_new_slot") is not False
    ):
        raise ValueError("GEO1 download metadata must not recommend submission")

    note = card.get("note")
    if not isinstance(note, str) or len(note) > 140:
        raise ValueError("GEO1 note is missing or exceeds 140 characters")
    note_path = root / "docs/downloads" / download.get("note_file", "")
    if (
        not note_path.is_file()
        or note_path.read_text().strip() != note
        or evidence.get("note") != note
    ):
        raise ValueError("GEO1 note file and run card do not match")

    checks_path = root / "docs/downloads" / download.get("checks_file", "")
    checks = _read_json(checks_path)
    recorded = checks.get("zero_outside")
    if not isinstance(recorded, dict) or recorded.get("sha256") != digest:
        raise ValueError("Saved zero-outside validator receipt does not match the GeoTIFF")
    template = root / "data/bridge/sample_submission.tif"
    fresh = check_variants(tif, template)
    if not fresh.get("format_valid") or fresh.get("sha256") != digest:
        raise ValueError("Fresh shared exact-file validator rejected the GEO1 GeoTIFF")
    strict = fresh.get("checks", {}).get("variant_strict_whole_array_no_nan_allowed", {})
    if strict.get("pass") is not True:
        raise ValueError("GEO1 zero-outside TIFF fails strict whole-array [0,1] check")

    # Re-open the one-TIFF archive and verify that its member has identical bytes.
    zip_path = tif.with_name(tif.name.replace("-zeros.tif", "-zeros.zip"))
    with zipfile.ZipFile(zip_path) as archive:
        if archive.namelist() != [name]:
            raise ValueError("GEO1 ZIP must contain exactly the selected TIFF")
        if hashlib.sha256(archive.read(name)).hexdigest() != digest:
            raise ValueError("GEO1 ZIP member does not match the selected TIFF")

    # The experiment receipt pins the code used at execution. Verify those bytes,
    # but do not execute or reconstruct the geological experiment.
    for relpath, expected in evidence.get("code_sha256", {}).items():
        path = root / relpath
        if not path.is_file() or sha256_file(path) != expected:
            raise ValueError(f"GEO1 recorded source hash mismatch: {relpath}")

    holdout = card.get("holdout", {})
    if holdout.get("label") != "HOLDOUT-DTI":
        raise ValueError("GEO1 holdout evidence lacks its required label")
    if download.get("holdout_dti") != holdout.get("dti"):
        raise ValueError("GEO1 download and run-card HOLDOUT-DTI values disagree")
    return {
        "verified": True,
        "scope": "Exact-file and receipt integrity only; no holdout replay or submission authorization",
        "submission_name": name,
        "raster_sha256": digest,
        "format_valid": True,
        "strict_whole_array_0_1": True,
        "holdout_label": holdout["label"],
        "holdout_evaluator_version": holdout.get("evaluator_version"),
        "holdout_value": holdout.get("dti"),
        "withheld_positive_pixels": holdout.get("n_withheld_positive_pixels"),
        "holdout_ci95": holdout.get("ci95"),
        "verdict": "negative",
        "ok_to_submit": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", type=Path, default=ROOT, help="repository root (for audits/tests)"
    )
    args = parser.parse_args()
    print(json.dumps(verify(args.root), indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
