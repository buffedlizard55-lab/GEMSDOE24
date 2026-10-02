#!/usr/bin/env python3
"""Refresh official-source snapshots on hosted CI; never fabricate a live score.

Failure retains a clearly marked last verified snapshot. This script performs
anonymous read-only HTTP requests, with TLS verification and bounded timeouts.
It does not write Git branches or submit predictions.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
LEADERBOARD = "https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/"
TOPICS = [
    (
        "https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516.json",
        "Known-pixel masking discussion",
    ),
    (
        "https://community.drivendata.org/t/how-were-the-new-test-faults-identified-data-sources-and-fault-types/11527.json",
        "Hidden test-source discussion",
    ),
]


def parse_leaderboard(html):
    soup = BeautifulSoup(html, "html.parser")
    rows = []
    for row in soup.select("table tr"):
        cols = row.find_all("td")
        if len(cols) < 4:
            continue
        rank = re.fullmatch(r"#?(\d+)", cols[0].get_text(" ", strip=True))
        score = re.fullmatch(r"(?:0|1)\.\d{4,}", cols[3].get_text(" ", strip=True))
        if not rank or not score:
            continue
        value = float(score.group())
        if not 0 <= value <= 1:
            raise ValueError("Leaderboard probability outside [0,1]")
        link = cols[2].find("a", href=re.compile(r"/users/"))
        name = link.get_text(" ", strip=True) if link else next(cols[2].stripped_strings, "")
        if not name:
            raise ValueError("Missing leaderboard participant")
        count = re.search(r"(\d+)\s+submissions", cols[2].get_text(" ", strip=True))
        rows.append(
            {
                "rank": int(rank.group(1)),
                "participant": name,
                "best_score": value,
                "submissions": int(count.group(1)) if count else None,
            }
        )
    if not rows or not any(r["rank"] == 1 for r in rows):
        raise ValueError("No verified rank-1 table row; login/layout page is not a leaderboard")
    leader = next(r for r in rows if r["rank"] == 1)
    if leader["best_score"] != max(r["best_score"] for r in rows):
        raise ValueError("Rank/score order inconsistent")
    return leader, rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--offline", action="store_true", help="validate the existing local snapshot only"
    )
    args = ap.parse_args()
    path = ROOT / "docs/data/source_health.json"
    old = json.loads(path.read_text())
    if args.offline:
        b = old.get("leaderboard", {})
        if not isinstance(b.get("best_score"), (float, int)) or not 0 <= b["best_score"] <= 1:
            raise SystemExit("Invalid offline source snapshot")
        print("Offline snapshot valid; no fresh network check or deployment claimed")
        return
    now = datetime.now(timezone.utc).isoformat()
    data = {**old, "checked_utc": now, "errors": [], "updates": []}
    session = requests.Session()
    session.headers["User-Agent"] = "GEMS-source-health/2.0"
    try:
        response = session.get(LEADERBOARD, timeout=30)
        response.raise_for_status()
        if len(response.content) > 5_000_000:
            raise ValueError("Unexpectedly large leaderboard response")
        leader, rows = parse_leaderboard(response.text)
        data.update(
            status="verified",
            last_success_utc=now,
            verification_method="anonymous HTTPS with parsed rank/score validation",
            leaderboard={**leader, "url": LEADERBOARD, "account_artifact_mapping_verified": False},
            leaderboard_rows=rows,
            leaderboard_html_sha256=hashlib.sha256(response.content).hexdigest(),
        )
        data["updates"].append(
            {
                "title": f"Official leader snapshot: {leader['participant']} {leader['best_score']:.4f}",
                "kind": "Official leaderboard HTTPS snapshot",
                "checked_utc": now,
                "url": LEADERBOARD,
            }
        )
    except (requests.RequestException, ValueError) as exc:
        data["status"] = "stale"
        data["errors"].append({"source": LEADERBOARD, "error": str(exc)[:250]})
        data["updates"] = old.get("updates", [])
    for url, title in TOPICS:
        try:
            response = session.get(url, timeout=30)
            response.raise_for_status()
            obj = response.json()
            if not obj.get("id") or not obj.get("post_stream"):
                raise ValueError("Not a public Discourse topic response")
            data["updates"].append(
                {
                    "title": obj.get("title") or title,
                    "kind": "Forum discussion; not every participant is organizer staff",
                    "checked_utc": now,
                    "last_post_utc": obj.get("last_posted_at"),
                    "url": url[:-5],
                    "response_sha256": hashlib.sha256(response.content).hexdigest(),
                }
            )
        except (requests.RequestException, ValueError) as exc:
            data["errors"].append({"source": url, "error": str(exc)[:250]})
    path.write_text(json.dumps(data, indent=2) + "\n")
    print(json.dumps({"status": data["status"], "errors": data["errors"]}, indent=2))


if __name__ == "__main__":
    main()
