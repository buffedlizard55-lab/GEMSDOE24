#!/usr/bin/env python3
"""Read-only audit of the concurrent H-UNIQUE-07 TIFF and its historic fold code.

No model, placement, TIFF write or slot use. The code review is tied to the
original Git blob, not the now-stopped working-tree runner.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems import novelty, submission  # noqa: E402
from gems.github_archive import git_blob_sha  # noqa: E402
from gems.validator import sha256_file  # noqa: E402

SOURCE_REF = "a1ecb683a9fda2aa4612f27e28896ebb8b19ad08"
TIFF = "24gems-catalogue-offset-geothermal-proximity-20261027T114303Z-578c30176163-zeros.tif"
TIFF_BLOB = "b756808d355df853168199f568d5dedcaffaec91"
CARD_BLOB = "d489c4b5a93ad25db6e41006d5d8b45f2905c1fa"
RUNNER_BLOB = "7311f5ec95a1a2122669e446e63d68bf7c641848"
LATTICE = "inputs/calibration/13gems_20261001_r13-lattice-s5_v2_nan-outside.tif"
NOTE = "GEMS24 H-UNIQUE-07 | leaked holdout; duplicate; research only; DO NOT SUBMIT"


def audit() -> dict:
    template = ROOT / "data/bridge/sample_submission.tif"
    raster = ROOT / "docs/downloads" / TIFF
    card_path = ROOT / "evidence/unique_experiment7.json"
    if (
        git_blob_sha(raster.read_bytes()) != TIFF_BLOB
        or git_blob_sha(card_path.read_bytes()) != CARD_BLOB
    ):
        raise ValueError("Concurrent source bytes differ from integrated immutable Git blobs")
    runner = subprocess.check_output(
        ["git", "show", f"{SOURCE_REF}:scripts/build_unique_submission7.py"], cwd=ROOT, timeout=30
    )
    if git_blob_sha(runner) != RUNNER_BLOB:
        raise ValueError("Historical runner Git blob changed")
    code = runner.decode()
    # Full catalogue is loaded from labels.tif, then used in a distance-based
    # support outside the fold loop; each fold's eligibility reuses that support.
    for required in (
        "with rasterio.open(LABELS) as s:",
        "catalogue = (s.read(1) > 0) & fp",
        "distance_transform_edt(~catalogue) > OFFSET_INNER_PX",
        "distance_transform_edt(~catalogue) <= OFFSET_OUTER_PX",
        'eligible = support & f["valid"] & ~f["visible"]',
    ):
        if required not in code:
            raise ValueError("Historical full-catalogue support evidence changed")
    card = json.loads(card_path.read_text())
    if card.get("raster_sha256") != sha256_file(raster) or card.get("submission_name") != TIFF:
        raise ValueError("TIFF and original run card do not match")
    checks = submission.check_variants(raster, template)
    if (
        not checks["format_valid"]
        or not checks["checks"]["variant_strict_whole_array_no_nan_allowed"]["pass"]
    ):
        raise ValueError("Concurrent raster failed fresh exact-file format checks")
    with zipfile.ZipFile(raster.with_suffix(".zip")) as zf:
        if zf.namelist() != [TIFF] or zf.read(TIFF) != raster.read_bytes():
            raise ValueError("Research ZIP must contain exactly the audited TIFF bytes")
    manifest = json.loads((ROOT / "registry/priority_rasters_20261026_portfolio.json").read_text())
    rows = [row for row in manifest["unique_rasters"] if row["file"] == LATTICE]
    if len(rows) != 1 or sha256_file(ROOT / LATTICE) != rows[0]["sha256"]:
        raise ValueError("Registered calibration lattice missing, ambiguous or changed")
    with rasterio.open(template) as ds:
        fp = np.isfinite(ds.read(1))
    with rasterio.open(raster) as ds:
        values = ds.read(1)
    dots = fp & (values > 0)
    comparison = novelty.compare_registry(values, fp, rows, ROOT, dots=dots)
    witness = comparison["rows"][0]
    if (
        comparison["passed"]
        or not witness["duplicate"]
        or witness["candidate_dot_overlap_within_3px"] <= 0.70
    ):
        raise ValueError("Expected literal duplicate witness was not reproduced")
    if len(NOTE) > 140:
        raise ValueError("Research note exceeds 140 characters")
    return {
        "schema": "unique07-read-only-integrity-v1",
        "checked_utc": datetime.now(timezone.utc).isoformat(),
        "source_ref": SOURCE_REF,
        "source_url": f"https://github.com/buffedlizard55-lab/GEMSDOE24/blob/{SOURCE_REF}/docs/downloads/{TIFF}",
        "source_pr": "https://github.com/buffedlizard55-lab/GEMSDOE24/pull/64",
        "historic_runner_blob": RUNNER_BLOB,
        "original_card_blob": CARD_BLOB,
        "raster_git_blob": TIFF_BLOB,
        "generated_by_this_session": False,
        "new_experiments": 0,
        "competition_slots_used": 0,
        "hypothesis": card["hypothesis"],
        "mechanism": card["mechanism"],
        "named_non_fault_mimic": card["non_fault_mimic"],
        "recorded_holdout": {
            **card["holdout"],
            "status": "INVALID FOR COMPARISON: fold placement used a support derived from the full label catalogue, including withheld components",
        },
        "fold_leakage": {
            "detected": True,
            "explanation": (
                "The original runner computes the 200–900 m support from labels.tif before "
                "splitting and reuses it for every fold. The hidden catalogue therefore affects "
                "placement eligibility; removing visible pixels afterwards does not remove this leak. "
                "Canaries on the raw trigger surfaces do not test the eligibility mask."
            ),
            "source_code_review_only": True,
            "scientific_replay": False,
        },
        "preplacement_surface_novelty": None,
        "final_dots": int(dots.sum()),
        "comparison_scope": "One hash-pinned registered lattice, a decisive failure witness; not all registries",
        "correlation_overlap_vs_registry": comparison,
        "validator_output": checks,
        "submission_name": TIFF,
        "raster_sha256": checks["sha256"],
        "note": NOTE,
        "ok_to_download": True,
        "ok_to_submit": False,
        "verdict": "negative",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, help="Optional JSON evidence path inside the workspace"
    )
    args = parser.parse_args()
    text = json.dumps(audit(), indent=2, allow_nan=False) + "\n"
    if args.output:
        target = args.output.resolve()
        if not target.is_relative_to(ROOT / "evidence"):
            raise ValueError("Audit output must be inside evidence/")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
    print(text)


if __name__ == "__main__":
    main()
