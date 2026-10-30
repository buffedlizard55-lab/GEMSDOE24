#!/usr/bin/env python3
"""Map each local nine-site file to its exact path in the owner's GitHub repo.

Matches by git blob SHA-1 (sha1(b"blob <n>\\0" + bytes)), so a link is only written
when the local bytes are identical to a blob in the owner's default branch.
Read-only against GitHub (gh api). Output: evidence/nine_site_owner_paths_20261030.json.
"""

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data/research/nine_site_verify"
OUT = ROOT / "evidence/nine_site_owner_paths_20261030.json"
SITES = [
    "GEMSDOE24",
    "GEMSDOE25",
    "GEMSDOE27",
    "GEMSDOE28",
    "GEMSDOE30",
    "GEMSDOE31",
    "GEMSDOE32",
    "GEMSDOE33",
    "GEMSDOE36",
]


def blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def tree(site: str) -> list:
    raw = subprocess.check_output(
        ["gh", "api", f"repos/buffedlizard55-lab/{site}/git/trees/main?recursive=1"], text=True
    )
    return json.loads(raw)["tree"]


def main() -> int:
    result = {"schema": "nine-owner-paths-v1", "branch": "main", "sites": {}}
    for site in SITES:
        local = SRC / f"{site}.tif"
        sha = blob_sha(local)
        matches = [
            t["path"]
            for t in tree(site)
            if t.get("sha") == sha and t["path"].lower().endswith(".tif")
        ]
        result["sites"][site] = {
            "local_blob_sha1": sha,
            "repo_paths_with_identical_bytes": matches,
            "url": (
                f"https://github.com/buffedlizard55-lab/{site}/blob/main/{matches[0]}"
                if matches
                else None
            ),
        }
        print(site, matches or "NO MATCH")
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print("wrote", OUT.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
