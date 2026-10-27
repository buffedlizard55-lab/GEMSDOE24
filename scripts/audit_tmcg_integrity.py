#!/usr/bin/env python3
"""Read-only audit of the concurrent TMCG TIFF against one decisive comparator.

No training, placement, TIFF writing, network access or slot use. The registered
lattice alone is enough to prove a literal-gate failure; this is not a complete
registry audit or a replay of the pre-placement surface or holdout experiment.
"""

from __future__ import annotations

import argparse
import json
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

SOURCE_REF = "6e4a85a3456dfe6312d25b6d81187c765a10c847"
TIFF = "gems24-tmcg-b-decoupled-basin-20261027T113937Z-6f8d042d5ee4-zeros.tif"
TIFF_BLOB = "650354982c3d9d37fb07747fb8a529db967b1624"
CARD_BLOB = "4b7627241d99fc26b4d48eca88f7a1718f21ff70"
LATTICE = "inputs/calibration/13gems_20261001_r13-lattice-s5_v2_nan-outside.tif"
NOTE = "GEMS24 TMCG basin | HOLDOUT-DTI 0.07157 | duplicate audit; research only; DO NOT SUBMIT"


def audit() -> dict:
    template = ROOT / "data/bridge/sample_submission.tif"
    raster = ROOT / "docs/downloads" / TIFF
    card_path = ROOT / "evidence/tmcg_run_card_20261027.json"
    if (
        git_blob_sha(raster.read_bytes()) != TIFF_BLOB
        or git_blob_sha(card_path.read_bytes()) != CARD_BLOB
    ):
        raise ValueError("Concurrent source bytes differ from the integrated immutable Git blobs")
    card = json.loads(card_path.read_text())
    if card.get("raster_sha256") != sha256_file(raster) or card.get("submission_name") != TIFF:
        raise ValueError("TIFF and original run card do not match")
    check = submission.check_variants(raster, template)
    if (
        not check["format_valid"]
        or not check["checks"]["variant_strict_whole_array_no_nan_allowed"]["pass"]
    ):
        raise ValueError("Concurrent raster failed fresh exact-file format checks")
    zip_path = raster.with_suffix(".zip")
    with zipfile.ZipFile(zip_path) as zf:
        if zf.namelist() != [TIFF] or zf.read(TIFF) != raster.read_bytes():
            raise ValueError("Research ZIP must contain exactly the audited TIFF bytes")
    manifest = json.loads((ROOT / "registry/priority_rasters_20261026_portfolio.json").read_text())
    rows = [row for row in manifest["unique_rasters"] if row["file"] == LATTICE]
    if len(rows) != 1 or sha256_file(ROOT / LATTICE) != rows[0]["sha256"]:
        raise ValueError("Registered calibration lattice missing, ambiguous or changed")
    with rasterio.open(template) as ds:
        footprint = np.isfinite(ds.read(1))
    with rasterio.open(raster) as ds:
        values = ds.read(1)
    dots = footprint & (values > 0)
    with rasterio.open(ROOT / LATTICE) as ds:
        ref = ds.read(1)
    control = novelty.classify_space_filling_control(
        footprint, footprint & np.isfinite(ref) & (ref > 0), candidate_dot_count=int(dots.sum())
    )
    comparison = novelty.compare_registry(values, footprint, rows, ROOT, dots=dots)
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
        "schema": "tmcg-read-only-integrity-v1",
        "checked_utc": datetime.now(timezone.utc).isoformat(),
        "source_ref": SOURCE_REF,
        "source_url": f"https://github.com/buffedlizard55-lab/GEMSDOE24/blob/{SOURCE_REF}/docs/downloads/{TIFF}",
        "source_pr": "https://github.com/buffedlizard55-lab/GEMSDOE24/pull/63",
        "original_card_blob": CARD_BLOB,
        "raster_git_blob": TIFF_BLOB,
        "generated_by_this_session": False,
        "new_experiments": 0,
        "competition_slots_used": 0,
        "hypothesis": card["hypothesis"],
        "mechanism": card["mechanism"],
        "named_non_fault_mimic": card["named_non_fault_mimic"],
        "holdout": {
            **card["holdout"],
            "status": "SOURCE-RECORDED, NOT INDEPENDENTLY REPLAYED; NOT A LEADERBOARD SCORE",
        },
        "original_novelty_issue": (
            "Original local-download-only proxy recorded drifted=false but omitted the retained "
            "registered lattice and did not evaluate a pre-placement surface. Its 55-file count "
            "is not a complete all-registry comparison. Original evidence is retained unchanged."
        ),
        "preplacement_surface_novelty": None,
        "final_dots": int(dots.sum()),
        "comparison_scope": "One hash-pinned registered lattice, a decisive failure witness; not all registries",
        "correlation_overlap_vs_registry": comparison,
        "pigeonhole_bound_for_this_dot_count": control,
        "validator_output": check,
        "submission_name": TIFF,
        "raster_sha256": check["sha256"],
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
    result = audit()
    text = json.dumps(result, indent=2, allow_nan=False) + "\n"
    if args.output:
        target = args.output.resolve()
        if not target.is_relative_to(ROOT / "evidence"):
            raise ValueError("Audit output must be inside evidence/")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
    print(text)


if __name__ == "__main__":
    main()
