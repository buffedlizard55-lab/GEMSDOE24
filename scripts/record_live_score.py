#!/usr/bin/env python3
"""Record a leaderboard score that the OWNER read from the DrivenData submissions page.

This script never contacts DrivenData (its terms forbid robots/automation). It appends to
``registry/submissions.json`` (matching candidate row) and ``registry/live_scores.json`` (ledger),
keeping the full history. Unknown stays unknown: a missing score is simply not recorded.

    python scripts/record_live_score.py --file <downloaded-file-name-or-sha256-prefix> --score 0.2134 \
        [--when 2026-10-03T14:05Z] [--note "portal row id / comment"]
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def record(file_or_sha: str, score: float, when: str | None, note: str, root: Path = ROOT) -> dict:
    if not 0.0 < score < 1.0:
        raise ValueError("score must be a probability-like DTI strictly between 0 and 1")
    when = when or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    reg_path = root / "registry/submissions.json"
    led_path = root / "registry/live_scores.json"
    reg = json.loads(reg_path.read_text())
    matches = [
        s
        for s in reg.get("submissions", [])
        if s.get("file") == file_or_sha
        or (len(file_or_sha) >= 8 and str(s.get("sha256", "")).startswith(file_or_sha))
    ]
    if len(matches) != 1:
        raise ValueError(
            f"expected exactly one registry row for {file_or_sha!r}, found {len(matches)}"
        )
    row = matches[0]
    entry = {
        "score": score,
        "recorded_for_time": when,
        "evidence": "owner report from the submissions page",
        "note": note,
    }
    row.setdefault("score_history", []).append(entry)
    row["live_dti"] = score
    row["score_evidence"] = "owner report"
    reg_path.write_text(json.dumps(reg, indent=2) + "\n")
    ledger = json.loads(led_path.read_text())
    ident = f"gems24_{row['content_id']}"
    art = next((a for a in ledger.setdefault("artifacts", []) if a.get("id") == ident), None)
    if art is None:
        art = {
            "id": ident,
            "label": f"{row['family']} {row['hypothesis']}",
            "repo": "buffedlizard55-lab/GEMSDOE24",
            "path": f"docs/downloads/{row['file']}",
            "sha256": row["sha256"],
            "corroboration": "owner_report_recorded_by_script",
        }
        ledger["artifacts"].append(art)
    art.setdefault("score_history", []).append(entry)
    art["owner_reported_public_score"] = score
    led_path.write_text(json.dumps(ledger, indent=2) + "\n")
    return {"file": row["file"], "score": score, "when": when}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True)
    ap.add_argument("--score", type=float, required=True)
    ap.add_argument("--when")
    ap.add_argument("--note", default="")
    args = ap.parse_args()
    try:
        print(json.dumps(record(args.file, args.score, args.when, args.note), indent=2))
    except (ValueError, OSError, KeyError) as exc:
        sys.exit(str(exc))


if __name__ == "__main__":
    main()
