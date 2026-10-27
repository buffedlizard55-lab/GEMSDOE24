#!/usr/bin/env python3
"""Patch H-UNIQUE-07 reports with the actual measured lattice overlap."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems import footprint, novelty  # noqa: E402
from gems.preflight import preflight  # noqa: E402
from gems.submission import check_variants  # noqa: E402

NAME = "24gems-catalogue-offset-geothermal-proximity-20261027T114303Z-578c30176163-zeros.tif"
TEMPLATE = ROOT / "data/bridge/sample_submission.tif"
LATTICE = ROOT / "inputs/calibration/13gems_20261001_r13-lattice-s5_v2_nan-outside.tif"
RUN_CARD = ROOT / "docs/data/unique_run_card_7.json"
EXPERIMENT = ROOT / "evidence/unique_experiment7.json"
DOWNLOAD = ROOT / "docs/data/unique_download_7.json"
PREFLIGHT = ROOT / "docs/downloads" / f"preflight-{NAME[:-4]}.json"

fp = footprint.load_footprint()
with rasterio.open(ROOT / "docs/downloads" / NAME) as ds:
    arr = ds.read(1)
dots = (arr > 0) & fp
print("Final dots:", int(dots.sum()))

with rasterio.open(LATTICE) as ds:
    lattice = (ds.read(1) > 0) & fp
ov_lattice = novelty.dot_overlap(dots, lattice)
print("Overlap vs lattice:", ov_lattice)

with rasterio.open(ROOT / "data/bridge/labels.tif") as ds:
    labels = (ds.read(1) > 0) & fp
ov_labels = novelty.dot_overlap(dots, labels)
print("Overlap vs labels:", ov_labels)

ctrl = novelty.classify_space_filling_control(
    fp, lattice, radius_px=3.0, coverage_threshold=0.70, candidate_dot_count=int(dots.sum())
)
print("Pigeonhole control:", ctrl)

novelty_block = {
    "registry_cache_available_locally": False,
    "lattice_file": str(LATTICE.relative_to(ROOT)),
    "lattice_footprint_3px_coverage": ctrl["footprint_3px_coverage"],
    "lattice_uncovered_pixels": ctrl["footprint_3px_uncovered_pixels"],
    "pigeonhole_min_overlap_any_dotted_set": ctrl["pigeonhole_min_overlap_for_candidate_size"],
    "final_dots": int(dots.sum()),
    "pigeonhole_min_overlap_for_final": ctrl["pigeonhole_min_overlap_for_candidate_size"],
    "measured_final_dot_overlap_within_3px_vs_lattice": ov_lattice[
        "candidate_within_3px_of_reference"
    ],
    "measured_final_dot_overlap_within_3px_vs_local_fault_labels": ov_labels[
        "candidate_within_3px_of_reference"
    ],
    "local_dot_overlap_vs_labels": ov_labels,
    "interpretation": (
        "Registry cache (data/research/priority_review) is not present in this clone, so the "
        "full 46-raster registry gate is not executable locally. Measured surrogate: "
        f"{ov_lattice['candidate_within_3px_of_reference']:.1%} of final dots within 3 px of the "
        "retained spacing-5 calibration lattice (>70% limit) and "
        f"{ov_labels['candidate_within_3px_of_reference']:.1%} vs local fault labels. The "
        "all-entry literal novelty gate cannot be shown to pass locally."
    ),
}

meas_ov = ov_lattice["candidate_within_3px_of_reference"]
meas_ov_lab = ov_labels["candidate_within_3px_of_reference"]
reasons = [
    "holdout DTI does not beat recorded local point-best 0.16606 (HOLDOUT-DTI, not ORGANIZER-CONFIRMED)",
    "holdout DTI does not beat recorded comparable baseline 0.13 (HOLDOUT-DTI, not ORGANIZER-CONFIRMED)",
    f"novelty gate not passable locally: {meas_ov:.1%} of final dots within 3 px of the retained spacing-5 calibration lattice (>70% limit); registry cache absent so the full registry gate is not executable locally",
    "preflight not ready to submit (no independent selector evidence)",
]

for path in (RUN_CARD, EXPERIMENT):
    card = json.loads(path.read_text())
    card["novelty"] = novelty_block
    card["reasons"] = reasons
    path.write_text(json.dumps(card, indent=2, allow_nan=False) + "\n")
    print("updated", path)

download = json.loads(DOWNLOAD.read_text())
download["novelty_surrogate"] = novelty_block
download["verdict"] = "negative"
download["ok_to_submit"] = False
download["ok_to_download"] = True
DOWNLOAD.write_text(json.dumps(download, indent=2, allow_nan=False) + "\n")
print("updated", DOWNLOAD)

# Re-run preflight bound to the saved run card for hash-linked evidence.
pf = preflight(
    ROOT / "docs/downloads" / NAME,
    TEMPLATE,
    run_card_path=RUN_CARD,
    note=card["note"],
    expected_template_sha256=str(__import__("hashlib").sha256(TEMPLATE.read_bytes()).hexdigest()),
)
PREFLIGHT.write_text(json.dumps(pf, indent=2, allow_nan=False) + "\n")
print("preflight decision:", pf["decision"]["submission_status"], "| ready:", pf["decision"]["ready_to_submit"])
print("updated", PREFLIGHT)
