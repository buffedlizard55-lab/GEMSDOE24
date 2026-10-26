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
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError, ValueError) as exc:
        return {
            **base,
            "latest_main_ref": None,
            "changed_since_review": None,
            "status": "failed",
            "error": str(exc)[:160],
        }


def validate_feed(data, sources):
    """Fail closed on fake leaderboard data, omitted repositories or inconsistent states."""
    if data.get("scope") != "GitHub source freshness only; not a leaderboard or scoring API":
        raise ValueError("Unexpected feed scope")
    if data.get("leaderboard") is not None or data.get("organizer_score_receipts") != []:
        raise ValueError("A source freshness feed cannot contain competition scores")
    stamp = datetime.fromisoformat(data["checked_utc"])
    if stamp.tzinfo is None:
        raise ValueError("Feed timestamp must include timezone")
    expected = {r["repo"]: r["ref"] for r in sources}
    rows = data["rows"]
    if len(rows) != len(expected) or {r["repo"] for r in rows} != set(expected):
        raise ValueError("Feed must include every pinned priority repository exactly once")
    for row in rows:
        if row["pinned_ref"] != expected[row["repo"]]:
            raise ValueError("Feed silently changed the scientific review pin")
        latest = row["latest_main_ref"]
        if row["status"] == "checked":
            if (
                not isinstance(latest, str)
                or len(latest) != 40
                or any(c not in "0123456789abcdef" for c in latest)
            ):
                raise ValueError("Invalid checked Git commit")
            if row["changed_since_review"] is not (latest != row["pinned_ref"]):
                raise ValueError("Source change marker disagrees with the returned commit")
        elif (
            row["status"] != "failed"
            or latest is not None
            or row["changed_since_review"] is not None
        ):
            raise ValueError("Failed checks must remain explicitly unknown")
    state = "stale" if any(r["status"] == "failed" for r in rows) else "checked"
    if data["status"] != state:
        raise ValueError("Feed status must acknowledge failed checks")
    return data


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--offline", action="store_true")
    ap.add_argument(
        "--from-owner-snapshot",
        type=Path,
        help="Reuse an already checked all-owner source snapshot; keep its original timestamp",
    )
    ap.add_argument("--registry", type=Path, default=ROOT / "registry/priority_rasters.json")
    ap.add_argument("--output", type=Path, default=ROOT / "docs/data/priority_feed.json")
    args = ap.parse_args()
    path, registry_path = args.output.resolve(), args.registry.resolve()
    if not path.is_relative_to(ROOT) or not registry_path.is_relative_to(ROOT):
        raise ValueError("Feed and registry paths must stay inside the workspace")
    sources = json.loads(registry_path.read_text())["sources"]
    if args.offline:
        validate_feed(json.loads(path.read_text()), sources)
        print("Offline priority feed schema valid; source timestamps unchanged")
        return
    if args.from_owner_snapshot:
        from review_owner_sites import validate

        snapshot = validate(json.loads(args.from_owner_snapshot.read_text()))
        if snapshot.get("refresh_status") == "error":
            raise ValueError("Cannot convert a stale all-owner snapshot into fresh priority checks")
        by_repo = {row["repo"]: row for row in snapshot["rows"]}
        rows = [
            {
                "repo": row["repo"],
                "pinned_ref": row["ref"],
                "url": "https://github.com/" + row["repo"],
                "latest_main_ref": by_repo[row["repo"]]["commit"],
                "changed_since_review": by_repo[row["repo"]]["commit"] != row["ref"],
                "status": "checked",
            }
            for row in sources
        ]
        now = snapshot["checked_utc"]  # never advance freshness without a new request
    else:
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
    validate_feed(feed, sources)
    path.parent.mkdir(parents=True, exist_ok=True)
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
