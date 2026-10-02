#!/usr/bin/env python3
"""Quick, reproducible review of every owner-listed sibling repository/site.

GitHub source HTML is pinned to a commit. A sibling's page/score is team evidence,
NOT an organizer-confirmed per-file score. Download links are inventories, not
proof that every referenced TIFF is distinct or scientifically validated.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
REPOS = [
    "GEMSDOE",
    "6GEMSDOE",
    "GEMSDOE3",
    "GEMSDOE2",
    "GEMSDOE4",
    "5GEMSDOE",
    "7GEMSDOE",
    "8GEMSDOE",
    "GEMSDOE9",
    "11GEMSDOE",
    "12GEMSDOE",
    "15GEMSDOE",
    "14GEMSDOE",
    "17GEMSDOE",
    "18GEMSDOE",
    "19GEMSDOE",
    "GEMSDOE10",
    "13GEMSDOE",
    "16GEMSDOE",
    "20GEMSDOE",
    "GEMSDOE21",
]
DOCS = {
    "GEMSDOE",
    "GEMSDOE3",
    "GEMSDOE2",
    "5GEMSDOE",
    "GEMSDOE9",
    "11GEMSDOE",
    "12GEMSDOE",
    "15GEMSDOE",
    "14GEMSDOE",
    "19GEMSDOE",
    "16GEMSDOE",
    "20GEMSDOE",
}


def gh(endpoint: str) -> bytes:
    return subprocess.check_output(
        ["gh", "api", endpoint, "-H", "Accept: application/vnd.github.raw"], stderr=subprocess.PIPE
    )


def review(repo: str) -> dict:
    row = {"repo": repo, "evidence_type": "team-authored source, not official score receipt"}
    try:
        info = json.loads(gh(f"repos/buffedlizard55-lab/{repo}"))
        branch = info["default_branch"]
        ref = json.loads(gh(f"repos/buffedlizard55-lab/{repo}/commits/{branch}"))["sha"]
        path = "docs/index.html" if repo in DOCS else "index.html"
        url = f"https://buffedlizard55-lab.github.io/{repo}/{path}"
        raw = gh(f"repos/buffedlizard55-lab/{repo}/contents/{path}?ref={ref}")
        d = ROOT / "data/research/group" / repo
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_bytes(raw)
        soup = BeautifulSoup(raw, "html.parser")
        links = sorted(
            {
                urllib.parse.urljoin(url, a["href"])
                for a in soup.select("a[href]")
                if ".tif" in a["href"] or ".zip" in a["href"]
            }
        )
        row.update(
            commit=ref,
            source_path=path,
            site_url=url,
            source_url=f"https://github.com/buffedlizard55-lab/{repo}/blob/{ref}/{path}",
            html_sha256=hashlib.sha256(raw).hexdigest(),
            title=soup.title.get_text() if soup.title else None,
            download_links=links,
            status="source_read",
        )
        # Read any small registry and core hypothesis implementations that exist.
        consulted = []
        tree = json.loads(gh(f"repos/buffedlizard55-lab/{repo}/git/trees/{ref}?recursive=1"))
        for f in tree.get("tree", []):
            p = f["path"]
            if (
                p
                in (
                    "registry/submissions.json",
                    "src/gems/hypotheses.py",
                    "src/gems/detectors.py",
                    "docs/research/hypothesis_register.md",
                    "scripts/evaluate_h19_and_build_submissions.py",
                )
                and f.get("size", 0) < 300000
            ):
                b = gh(f"repos/buffedlizard55-lab/{repo}/contents/{p}?ref={ref}")
                dest = d / p
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(b)
                consulted.append({"path": p, "sha256": hashlib.sha256(b).hexdigest()})
        row["consulted_files"] = consulted
    except (subprocess.CalledProcessError, KeyError, ValueError) as e:
        row.update(status="failed", error=str(e)[:180])
    return row


def main():
    with ThreadPoolExecutor(max_workers=4) as ex:
        rows = list(ex.map(review, REPOS))
    output = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "rows": rows,
        "unreported_scores": [
            "22GEMSDOE",
            "23GEMSDOE",
            "24GEMSDOE",
            "25GEMSDOE",
            "26GEMSDOE",
            "27GEMSDOE",
        ],
        "warning": "Blank scores are unknown, never zero. Source HTML can differ from deployed Pages; official current leaderboard is checked separately.",
    }
    (ROOT / "evidence/group_review.json").write_text(json.dumps(output, indent=2) + "\n")
    print(
        json.dumps(
            [{k: r.get(k) for k in ("repo", "status", "title", "error")} for r in rows], indent=2
        )
    )


if __name__ == "__main__":
    main()
