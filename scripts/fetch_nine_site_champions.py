#!/usr/bin/env python3
"""Fetch the nine focus-site champion TIFFs at their pinned immutable commits.

Reads evidence/peer_forensics_20261025.json (pinned URL, commit and SHA-256 per site),
downloads each file through the same gh-contents path as restore_data.py, verifies
the SHA-256, and writes data/research/nine_site/fetch_receipt.json (gitignored bytes).
Read-only with respect to organizer systems: no DrivenData access.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))
from restore_data import gh_bytes  # noqa: E402

from gems.validator import sha256_file  # noqa: E402


def main() -> None:
    records = json.loads((ROOT / "evidence/peer_forensics_20261025.json").read_text())["artifacts"]
    out = ROOT / "data/research/nine_site"
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for r in records:
        m = re.fullmatch(
            r"https://github.com/(buffedlizard55-lab/GEMSDOE\d+)/blob/([0-9a-f]{40})/(docs/downloads/[^/]+\.tif)",
            r["url"],
        )
        if not m:
            raise SystemExit(f"Unexpected URL shape: {r['url']}")
        repo, ref, path = m.groups()
        dest = out / f"{r['repo']}__{r['file']}"
        if not dest.exists() or sha256_file(dest) != r["sha256"]:
            gh_bytes(repo, path, ref, dest)
        actual = sha256_file(dest)
        rows.append(
            {
                "site": r["repo"],
                "file": r["file"],
                "local": str(dest.relative_to(ROOT)),
                "url": r["url"],
                "sha256_expected": r["sha256"],
                "sha256_actual": actual,
                "match": actual == r["sha256"],
            }
        )
        print(r["repo"], actual == r["sha256"], flush=True)
    if not all(x["match"] for x in rows):
        raise SystemExit("Hash mismatch; do not use these bytes")
    (out / "fetch_receipt.json").write_text(json.dumps(rows, indent=2) + "\n")


if __name__ == "__main__":
    main()
