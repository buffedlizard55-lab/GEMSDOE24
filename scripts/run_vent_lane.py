#!/usr/bin/env python3
"""Verify bytes only. Original VENT experiment quarantined for dummy audit fallbacks.

Frozen source: archive/legacy/vent/run_vent_lane.py.txt and upstream commit
8d850d9. Neither archived C2ST nor registry PASS claims certify real measurements.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems.submission import check_variants  # noqa: E402


def verify_recorded(root: Path) -> dict:
    card = json.loads((root / "evidence/vent_run_card_20261026.json").read_text())
    name = card.get("submission_name", "")
    if not name or Path(name).name != name or not name.endswith("-zeros.tif"):
        raise ValueError("Unsafe VENT filename")
    if card.get("verdict") != "negative" or card.get("ok_to_submit") is not False:
        raise ValueError("Quarantined packet must remain negative")
    checks = check_variants(
        root / "docs/downloads" / name, root / "data/bridge/sample_submission.tif"
    )
    if not checks["format_valid"] or checks["sha256"] != card.get("raster_sha256"):
        raise ValueError("VENT hash or format mismatch")
    if checks["checks"]["variant_strict_whole_array_no_nan_allowed"]["pass"] is not True:
        raise ValueError("VENT strict finite range check failed")
    return {
        "scope": "exact-file identity/format only; scientific audits quarantined",
        "validator_output": checks,
        "scientific_gate_claims_trusted": False,
        "reason": "Original script substituted dummy C2ST and plausible novelty statistics on audit exceptions",
        "experiment_rerun": False,
        "ok_to_submit": False,
        "verdict": "negative",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-recorded", action="store_true")
    args = parser.parse_args()
    if not args.verify_recorded:
        parser.error("VENT quarantined: audit fallbacks fabricated PASS; no rerun permitted")
    print(json.dumps(verify_recorded(ROOT), indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
