#!/usr/bin/env python3
"""Refresh the source feed WITHOUT touching drivendata.org; never fabricate a live score.

DrivenData's Terms of Use (https://www.drivendata.org/termsofuse/) prohibit using "any robot, spider or other
automatic device, process or means to access the Website for any purpose, including monitoring or copying", and
the prize rules bind competitors to them. So this script NEVER requests a drivendata.org host (leaderboard, forum,
data pages). Leaderboard rows are HUMAN-READ snapshots: a person saves the page and runs
``--leaderboard-file``; nothing is fetched. The only automatic request is the USGS ScienceBase JSON API (an
interface intended for programmatic use) to detect changes to the GeoDAWN release. TLS verified, bounded timeouts,
no Git writes, no submissions.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
SCIENCEBASE_ITEM = "https://www.sciencebase.gov/catalog/item/657e1d85d34e23d3533209f7?format=json"
FORBIDDEN_HOSTS = ("drivendata.org",)
LEADERBOARD_URL = (
    "https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/"  # link only
)


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


def assert_allowed(url: str) -> str:
    """Refuse any automatic request to a forbidden host (DrivenData Terms of Use)."""
    host = urlparse(url).hostname or ""
    if any(host == h or host.endswith("." + h) for h in FORBIDDEN_HOSTS):
        raise ValueError(f"automatic access to {host} is not permitted by its Terms of Use")
    return url


def ingest_leaderboard_file(data: dict, path: Path, now: str, reader: str) -> dict:
    """Update the snapshot from a leaderboard page a HUMAN saved; no network request."""
    leader, rows = parse_leaderboard(Path(path).read_text(errors="replace"))
    data.update(
        status="human_read_snapshot",
        last_success_utc=now,
        verification_method=f"leaderboard page saved and supplied by {reader}; parsed with rank/score validation; not fetched by this script",
        leaderboard={**leader, "url": LEADERBOARD_URL, "account_artifact_mapping_verified": False},
        leaderboard_rows=rows[:60],
    )
    data["updates"] = [
        u
        for u in data.get("updates", [])
        if not str(u.get("title", "")).startswith("Official leader")
    ] + [
        {
            "title": f"Official leader snapshot: {leader['participant']} {leader['best_score']:.4f}",
            "kind": f"Human-read leaderboard snapshot ({reader}); not a permanent result",
            "checked_utc": now,
            "url": LEADERBOARD_URL,
        }
    ]
    return data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--offline", action="store_true", help="validate the existing local snapshot only"
    )
    ap.add_argument("--leaderboard-file", type=Path, help="leaderboard HTML/text a human saved")
    ap.add_argument("--reader", default="owner", help="who read the leaderboard page")
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
    data = {**old, "errors": []}
    data["updates"] = [
        u for u in old.get("updates", []) if "sciencebase" not in str(u.get("url", ""))
    ]
    if args.leaderboard_file:
        data["checked_utc"] = now
        data = ingest_leaderboard_file(data, args.leaderboard_file, now, args.reader)
    try:
        session = requests.Session()
        session.headers["User-Agent"] = "GEMS-source-health/3.0 (USGS ScienceBase JSON API)"
        response = session.get(assert_allowed(SCIENCEBASE_ITEM), timeout=30)
        response.raise_for_status()
        obj = response.json()
        if not obj.get("id") or "GeoDAWN" not in str(obj.get("title", "")):
            raise ValueError("Not the GeoDAWN ScienceBase item")
        data["updates"].append(
            {
                "title": f"GeoDAWN release (USGS ScienceBase) last updated {obj.get('provenance', {}).get('lastUpdated', 'unknown')}",
                "kind": "Official USGS ScienceBase JSON API (automatic check)",
                "checked_utc": now,
                "url": SCIENCEBASE_ITEM.split("?")[0],
                "response_sha256": hashlib.sha256(response.content).hexdigest(),
            }
        )
        data["checked_utc"] = now
        if data.get("status") not in ("human_read_snapshot",):
            data["status"] = "manual_source_read"
        data["automatic_checks_utc"] = now
    except (requests.RequestException, ValueError) as exc:
        data["errors"].append({"source": SCIENCEBASE_ITEM.split("?")[0], "error": str(exc)[:250]})
    data["drivendata_automation"] = (
        "none: drivendata.org is never requested by scheduled or CI jobs"
    )
    path.write_text(json.dumps(data, indent=2) + "\n")
    print(json.dumps({"status": data.get("status"), "errors": data["errors"]}, indent=2))


if __name__ == "__main__":
    main()
