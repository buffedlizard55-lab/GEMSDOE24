#!/usr/bin/env python3
"""Read-only audit of a pinned peer's existing research TIFF and reported evidence.

This does not train, place dots, replay a holdout, authenticate an organizer
mirror, query a competition site, certify the full registry, or authorize upload.
The peer TIFF is cached under Git-ignored data/research; the original evidence
bytes are pinned separately. --fetch uses GitHub only at an immutable commit.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from audit_current_focus_files import fetch  # noqa: E402
from check_uniqueness_feasibility import TEMPLATE, WITNESS  # noqa: E402
from check_uniqueness_feasibility import audit as audit_witness  # noqa: E402

from gems import novelty, submission  # noqa: E402
from gems.github_archive import git_blob_sha  # noqa: E402
from gems.validator import sha256_file  # noqa: E402

REPO = "buffedlizard55-lab/GEMSDOE36"
REF = "4b717aaff6eaf5de9b53030e637f8e1cf0d56e43"
NAME = "gemsdoe36-s2d36-exp2-20261027-31189d084a83-zeros.tif"
SOURCES = {
    "raster": {
        "source": f"docs/downloads/{NAME}",
        "local": f"data/research/focus-20261028/GEMSDOE36/docs/downloads/{NAME}",
        "blob": "6e07be6811545c8022d52a942d941b5fdb33b18c",
        "sha256": "d3ba2fdb987bec34fc0c61148829032a431a95b8921b1bd66d61ddd047f56b72",
    },
    "card": {
        "source": "evidence/s2d36_run_card_20261027.json",
        "local": "evidence/external/s2d36-4b717aaf.json",
        "blob": "fa8b5e3403fb4965a9e1f33cc2e52f6aaf328ab5",
        "sha256": "5df79bfe5d1da5c04bac8e57d78333385105a31f5777eabfe452441ba2f2114c",
    },
    "holdout": {
        "source": "evidence/s2d36_holdout_experiments_20261027.json",
        "local": "evidence/external/s2d36-holdout-4b717aaf.json",
        "blob": "d99dd80faf0e05fe135eef224577b3acdf195099",
        "sha256": "2a6dc20fb835ce227b506582d7d88b480a257c7d210f9061309f4d1fa213f9c2",
    },
    "canary": {
        "source": "evidence/s2d36_leakage_canary_20261027.json",
        "local": "evidence/external/s2d36-canary-4b717aaf.json",
        "blob": "7963061a465eaa5b19bb5c1ec79c7ce3caa259d3",
        "sha256": "e41216e203a00c147aebd8ab1ac3a4a7e46f930752a26423208fb644d54c534a",
    },
    "preregistration": {
        "source": "evidence/s2d36_preregistration_20261027.json",
        "local": "evidence/external/s2d36-preregistration-4b717aaf.json",
        "blob": "02a67b6aeaf0e7c66fc05ecb3c1207352f03e260",
        "sha256": "0cb39811a8caf986cd503b3e194923745e6819bfe3f3fc155c049462c91c9ac1",
    },
}


def verify_source_bytes(root: Path, *, download: bool = False) -> dict:
    """Reject a missing/altered Git blob; never discover an unpinned replacement."""
    identities = {}
    for name, pin in SOURCES.items():
        path = root / pin["local"]
        if download:
            got = fetch(REPO, REF, pin["source"], path)
            if got["git_blob"] != pin["blob"] or got["sha256"] != pin["sha256"]:
                raise ValueError(f"GitHub identity does not match pinned {name}")
        if not path.is_file():
            raise ValueError(f"Pinned {name} missing; use --fetch to retrieve it from GitHub")
        if sha256_file(path) != pin["sha256"] or git_blob_sha(path.read_bytes()) != pin["blob"]:
            raise ValueError(f"Pinned {name} bytes changed")
        identities[name] = {
            "source_url": f"https://github.com/{REPO}/blob/{REF}/{pin['source']}",
            "git_blob": pin["blob"],
            "sha256": pin["sha256"],
            "bytes": path.stat().st_size,
        }
    return identities


def check_reported_evidence(card: dict, holdout: dict, canary: dict, preregistration: dict) -> dict:
    """Check only cross-document identities and arithmetic, not scientific replay."""
    selected = holdout["summaries"]["EXP-2"]
    source_arm = card["holdout"]["arms"]["EXP-2"]
    protocol = selected["protocol"]
    result = selected["TP_w"] / (selected["TP_w"] + 0.2 * selected["FP_w"] + 0.8 * selected["FN_w"])
    if (
        card.get("lane_id") != "S2D-36"
        or card.get("best_arm") != "EXP-2"
        or card.get("verdict") != "negative"
        or card.get("slot_approved") is not False
        or card.get("organizer_score") is not None
        or holdout.get("best_candidate_arm") != "EXP-2"
        or card["submission"]["sha256"] != SOURCES["raster"]["sha256"]
        or Path(card["submission"]["file"]).name != NAME
        or card["submission"]["dots"] != 37654
        or card["preregistration"]["sha256"] != SOURCES["preregistration"]["sha256"]
        or holdout["preregistration_sha256"] != SOURCES["preregistration"]["sha256"]
        or preregistration["lane_id"] != "S2D-36"
        or holdout["label"] != "HOLDOUT-DTI"
        or holdout["evaluator_version"] != "gems-segment-pooled-v1"
        or holdout["withheld_positives"] != 60988
        or source_arm["dti"] != selected["dti"]
        or source_arm["ci95"] != selected["ci95"]["interval"]
        or not math.isclose(result, selected["dti"], abs_tol=1e-10)
        or protocol["alpha"] != 0.2
        or protocol["beta"] != 0.8
        or protocol["triangular_kernel_radius_m"] != 300
        or canary["threshold"] != 0.9
        or canary["passed"] is not True
    ):
        raise ValueError("Pinned peer source claims are inconsistent")
    return {
        "label": "HOLDOUT-DTI",
        "value": selected["dti"],
        "ci95": selected["ci95"]["interval"],
        "evaluator_version": holdout["evaluator_version"],
        "withheld_positive_pixels": holdout["withheld_positives"],
        "source_ci_method": selected["ci95"]["method"],
        "source_ci_resamples": selected["ci95"]["resamples"],
        "scope": "Source-recorded only; pooled arithmetic rechecked, no model/fold/bootstrap replay.",
        "canary_scope": (
            f"Source reports {canary['total_stage1_features']} value features using reused receipts; "
            f"this canary file contains {len(canary['features'])} new value rows. "
            "No complete independent missingness-canary replay was performed."
        ),
        "source_document_discrepancy": (
            "The peer research prose describes 1,000 segment-cluster resamples, while the "
            "pinned holdout JSON records 1,999 spatial-block resamples for this CI; not reconciled."
        ),
    }


def audit(root: Path, *, download: bool = False) -> dict:
    root = Path(root)
    identities = verify_source_bytes(root, download=download)
    data = {
        key: json.loads((root / SOURCES[key]["local"]).read_text())
        for key in ("card", "holdout", "canary", "preregistration")
    }
    recorded = check_reported_evidence(**data)
    # This rechecks the exact pinned witness, footprint, mask, grid and bound.
    witness = audit_witness(root, [37654])
    raster, template = root / SOURCES["raster"]["local"], root / TEMPLATE
    validation = submission.check_variants(raster, template)
    if (
        validation["sha256"] != SOURCES["raster"]["sha256"]
        or validation["format_valid"] is not True
        or validation["checks"]["variant_strict_whole_array_no_nan_allowed"]["pass"] is not True
        or validation["in_footprint_positive_pixels"] != 37654
    ):
        raise ValueError("Peer TIFF identity or local format/range check failed")
    with (
        rasterio.open(template) as t,
        rasterio.open(raster) as candidate,
        rasterio.open(root / WITNESS) as reference,
    ):
        fp = np.isfinite(t.read(1))
        values, control = candidate.read(1), reference.read(1)
        if not np.isin(values[fp], [0, 1]).all() or (values[~fp] != 0).any():
            raise ValueError("Expected binary footprint dots and zero exterior")
        dots, lattice = fp & (values > 0), fp & np.isfinite(control) & (control > 0)
    overlap = novelty.dot_overlap(dots, lattice)
    fraction = overlap["candidate_within_3px_of_reference"]
    claimed = data["card"]["uniqueness"]["literal_all_198_max_3px_dot_overlap"]
    if (
        fraction is None
        or not math.isclose(fraction, claimed, abs_tol=0.000001)
        or fraction <= 0.70
    ):
        raise ValueError(
            "Peer/source lattice result inconsistent or unexpectedly below the stop gate"
        )
    return {
        "schema": "peer-s2d36-research-audit-v1",
        "checked_utc": datetime.now(timezone.utc).isoformat(),
        "scope": (
            "Exact peer TIFF, source evidence identity/arithmetic, and one lattice comparator; "
            "not a current nine-site census, full novelty audit, or scientific replay."
        ),
        "source_commit": REF,
        "source_identities": identities,
        "recorded_holdout": recorded,
        "local_format_validation": validation,
        "literal_lattice_overlap": overlap,
        "literal_lattice_limit": 0.70,
        "literal_uniqueness_pass": False,
        "source_control_witness": witness["witness"],
        "source_control_budget_bound": witness["budgets"][0],
        "preplacement_surface_test": "NOT REPLAYED",
        "full_registry_test": "NOT REPLAYED; one decisive literal comparator fails",
        "leaderboard_score": None,
        "organizer_receipt": None,
        "submission_authorized": False,
        "verdict": "negative",
        "new_experiments": 0,
        "new_geological_tiffs": 0,
        "competition_slots_used": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fetch", action="store_true", help="retrieve pinned bytes from GitHub")
    parser.add_argument("--output", type=Path, help="write the JSON research receipt")
    args = parser.parse_args()
    result = audit(ROOT, download=args.fetch)
    text = json.dumps(result, indent=2, allow_nan=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text)
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
