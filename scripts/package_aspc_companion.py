#!/usr/bin/env python3
"""Encode the SAME research predictions with the pinned template's NaN convention.

This is packaging, not another experiment or another promoted candidate.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems import submission  # noqa: E402
from gems.validator import sha256_file  # noqa: E402


def package(root, report, card):
    row = report["artifact"]
    source = root / "docs/downloads" / row["file"]
    if sha256_file(source) != row["sha256"]:
        raise ValueError("Research source differs from its exact-file receipt")
    template = root / "data/bridge/sample_submission.tif"
    with rasterio.open(source) as ds:
        a = ds.read(1)
    name = row["file"].replace("-zeros.tif", "-nan.tif")
    dest = source.with_name(name)
    submission.write_submission(a, template, dest, outside="nan")
    checks = submission.check_variants(dest, template)
    if not checks["official_format_compliant"]:
        raise ValueError("Companion does not match pinned template convention")
    with rasterio.open(template) as ds:
        fp = np.isfinite(ds.read(1))
    with rasterio.open(dest) as ds:
        if not np.array_equal(a[fp], ds.read(1)[fp]):
            raise AssertionError("Packaging changed in-footprint predictions")
    checks_path = dest.with_suffix(".checks.json")
    checks_path.write_text(json.dumps(checks, indent=2, allow_nan=False) + "\n")
    twin = {
        "file": name,
        "sha256": checks["sha256"],
        "validator_output": checks,
        "same_in_footprint_predictions": True,
        "submission_authorized": False,
        "purpose": "Same research artifact, pinned-template NaN-outside convention; do not submit",
    }
    report["template_convention_companion"] = twin
    card["template_convention_companion"] = twin


def main():
    rp = ROOT / "evidence/aspc_run_20261025.json"
    cp = ROOT / "evidence/aspc_run_card_20261025.json"
    report, card = json.loads(rp.read_text()), json.loads(cp.read_text())
    package(ROOT, report, card)
    for path, obj in ((rp, report), (cp, card)):
        path.write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n")
    print("Same predictions packaged with NaN outside; still NOT AUTHORIZED")


if __name__ == "__main__":
    main()
