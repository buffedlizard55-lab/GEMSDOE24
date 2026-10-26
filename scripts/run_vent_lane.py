#!/usr/bin/env python3
"""Quarantined VENT lane: verify existing bytes only, never scientific gates.

The historical source contained fabricated fallback C2ST and novelty values.
Preserved verbatim in archive/legacy/vent/run_vent_lane.py.txt for auditing.
Recorded numerical science claims are untrusted pending independent replay.
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


def verify_recorded(root: Path = ROOT) -> dict:
    card = json.loads((root / "evidence/vent_run_card_20261026.json").read_text())
    name = card["submission_name"]
    if not isinstance(name, str) or Path(name).name != name:
        raise ValueError("Invalid VENT artifact name")
    artifact = root / "docs/downloads" / name
    checks = check_variants(artifact, root / "data/bridge/sample_submission.tif")
    matched = sha256_file(artifact) == card["raster_sha256"]
    return {
        "scope": "Exact existing bytes and format only; no scientific replay",
        "artifact": name,
        "sha256_matches_record": matched,
        "validator_output": checks,
        "verification_passed": matched and checks.get("format_valid") is True,
        "recorded_scientific_claims_trusted": False,
        "reason": "Historical runner fabricated fallback C2ST/novelty values; quarantined",
        "verdict": "negative",
        "decision": "DO_NOT_SUBMIT",
        "ok_to_submit": False,
        "experiments_run": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-recorded", action="store_true")
    args = parser.parse_args()
    if not args.verify_recorded:
        parser.error("VENT is quarantined; only --verify-recorded is permitted. No rerun.")
    try:
        result = verify_recorded()
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(
            json.dumps(
                {"decision": "DO_NOT_SUBMIT", "verification_passed": False, "error": str(exc)}
            )
        )
        return 1
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0 if result["verification_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
