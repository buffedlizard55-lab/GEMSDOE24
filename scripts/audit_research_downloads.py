#!/usr/bin/env python3
"""Read-only exact-byte audit; does not generate, select, or authorize a candidate."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems.receipts import research_receipt  # noqa: E402


def audit(root: Path) -> dict:
    report = json.loads((root / "evidence/aspc_run_20261025.json").read_text())
    card = json.loads((root / "evidence/aspc_run_card_20261025.json").read_text())
    if (
        report.get("submission_authorized") is not False
        or card.get("submission_authorized") is not False
    ):
        raise ValueError("Research audit cannot authorize submission")
    rows = [report["artifact"], report["template_convention_companion"]]
    checks = [
        research_receipt(
            root / "docs/downloads", row, template=root / "data/bridge/sample_submission.tif"
        )
        for row in rows
    ]
    if card["submission_name"] != rows[0]["file"] or card["raster_sha256"] != rows[0]["sha256"]:
        raise ValueError("Run card identity disagrees")
    if card["validator_output"] != checks[0]:
        raise ValueError("Run card primary checks disagree")
    if card["template_convention_companion"] != rows[1]:
        raise ValueError("Run card companion disagrees")
    if card["verdict"] != "negative" or not report["blockers"]:
        raise ValueError("Research promotion decision disagrees")
    return {
        "audit": "fresh-exact-file-validation-v1",
        "files": [
            {"file": r["file"], "sha256": c["sha256"], "format_valid": True}
            for r, c in zip(rows, checks, strict=True)
        ],
        "submission_authorized": False,
        "new_experiments": 0,
        "verdict": "negative",
        "blockers": report["blockers"],
    }


if __name__ == "__main__":
    print(json.dumps(audit(ROOT), indent=2, allow_nan=False))
