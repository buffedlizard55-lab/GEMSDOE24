#!/usr/bin/env python3
"""Timestamp GitHub-source freshness only. Never contact DrivenData.

A changed source does not rerun experiments, change pinned registry membership,
consume a competition slot or replace a scientific decision.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def check(row):
    repo, ref = row["repo"], row["ref"]
    base = {"repo": repo, "pinned_ref": ref, "url": f"https://github.com/{repo}"}
    try:
        value = subprocess.check_output(
            ["gh", "api", f"repos/{repo}/commits/main", "--jq", ".sha"],
            text=True,
            stderr=subprocess.PIPE,
            timeout=30,
        ).strip()
        if len(value) != 40 or any(c not in "0123456789abcdef" for c in value):
            raise ValueError("Invalid Git commit returned")
        return {
            **base,
            "latest_main_ref": value,
            "changed_since_review": value != ref,
            "status": "checked",
        }
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, ValueError) as exc:
        return {
            **base,
            "latest_main_ref": None,
            "changed_since_review": None,
            "status": "failed",
            "error": str(exc)[:160],
        }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--offline", action="store_true")
    args = ap.parse_args()
    path = ROOT / "docs/data/priority_feed.json"
    if args.offline:
        data = json.loads(path.read_text())
        if data.get("scope") != "GitHub source freshness only; not a leaderboard or scoring API":
            raise SystemExit("Unexpected feed scope")
        print("Offline priority feed schema valid; source timestamps unchanged")
        return
    sources = json.loads((ROOT / "registry/priority_rasters.json").read_text())["sources"]
    with ThreadPoolExecutor(max_workers=4) as pool:
        rows = list(pool.map(check, sources))
    now = datetime.now(timezone.utc).isoformat()
    feed = {
        "scope": "GitHub source freshness only; not a leaderboard or scoring API",
        "checked_utc": now,
        "status": "stale" if any(r["status"] == "failed" for r in rows) else "checked",
        "rows": rows,
        "updates": [
            {
                "title": r["repo"].split("/")[-1]
                + (
                    ": source changed after pinned review"
                    if r["changed_since_review"]
                    else ": pinned source unchanged"
                    if r["status"] == "checked"
                    else ": source check unavailable"
                ),
                "url": r["url"],
                "kind": "GitHub commit freshness; no score verification",
                "checked_utc": now,
            }
            for r in rows
        ],
        "leaderboard": None,
        "organizer_score_receipts": [],
        "warning": "Registry/experiment snapshots stay pinned. New commits require a new audit; the stopped negative candidate stays DO NOT SUBMIT.",
    }
    path.write_text(json.dumps(feed, indent=2) + "\n")
    print(
        json.dumps(
            {
                "checked_utc": now,
                "source_count": len(rows),
                "changed": sum(r["changed_since_review"] is True for r in rows),
                "failures": sum(r["status"] == "failed" for r in rows),
            }
        )
    )


if __name__ == "__main__":
    main()
