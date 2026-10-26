#!/usr/bin/env python3
"""Quarantined H-UNIQUE-GAPFILL lane: verify archived bytes only; never execute or promote.

Original PR #55 runner is quarantined for three protocol violations:
1. Target leakage (Rule 2): computed ``distance_transform_edt(~labels)`` on global
   ``labels.tif`` including all 60,988 withheld test fault pixels across all 4 folds,
   producing an invalid leaked HOLDOUT-DTI of 0.60183.
2. Post-hoc dot avoidance (Rule 1): ingested ``docs/downloads/*.tif`` to push dots
   around existing submissions (``gap_boost = 1 - dot_penalty``).
3. Registry/selector bypass (Rule 6): omitted ``registry/priority_rasters.json``
   (99.5% 3-px overlap vs ``registry-039``) and bypassed ``gems.selector.verify_selector``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems.submission import check_variants  # noqa: E402
from gems.validator import sha256_file  # noqa: E402

ARTIFACT_NAME = "24gems-gapfill-near-fault-20261026T203338Z-1b2b4ccc37b0-zeros.tif"
EXPECTED_SHA256 = "cc0d061f915fef34288a09df990dde229d6efd95521bc73013bd5c652eb14f24"


def verify_recorded(root: Path = ROOT) -> dict:
    exp = json.loads((root / "evidence/unique_experiment_gapfill.json").read_text())
    if (
        exp.get("quarantined") is not True
        or exp.get("verdict") != "negative"
        or exp.get("ok_to_submit") is not False
    ):
        raise ValueError("Quarantined gapfill experiment receipt must remain negative")
    artifact = root / "docs/downloads" / ARTIFACT_NAME
    checks = check_variants(artifact, root / "data/bridge/sample_submission.tif")
    matched = sha256_file(artifact) == EXPECTED_SHA256
    return {
        "scope": "Archived bytes and format check only; scientific score quarantined",
        "artifact": ARTIFACT_NAME,
        "sha256_matches_record": matched,
        "validator_output": checks,
        "verification_passed": matched
        and checks.get("format_valid") is True
        and checks["checks"]["variant_strict_whole_array_no_nan_allowed"]["pass"] is True,
        "quarantined": True,
        "scientific_gate_claims_trusted": False,
        "verdict": "negative",
        "decision": "DO_NOT_SUBMIT",
        "ok_to_submit": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-recorded", action="store_true")
    args = parser.parse_args()
    if not args.verify_recorded:
        raise SystemExit(
            "H-UNIQUE-GAPFILL is quarantined (global labels.tif target leakage + Rule-1 "
            "dot avoidance around existing submissions); execution refused. "
            "Use --verify-recorded to inspect archived bytes."
        )
    out = verify_recorded()
    print(json.dumps(out, indent=2))
    if not out["verification_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
