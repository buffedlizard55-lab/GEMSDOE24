#!/usr/bin/env python3
"""Restore the pinned nine-repository raster registry via GitHub, never DrivenData.

Raw raster references stay in ignored data/research. Default uses pinned blob IDs;
--snapshot explicitly refreshes the review scope and hashes. No credentials logged.
"""

from __future__ import annotations

import argparse
import base64
import concurrent.futures
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "registry/peer_rasters_20261025.json"
OWNER = "buffedlizard55-lab"
REPOS = [f"GEMSDOE{n}" for n in (24, 25, 27, 28, 30, 31, 32, 33, 36)]


def api(path):
    return json.loads(subprocess.check_output(["gh", "api", path]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", action="store_true")
    args = parser.parse_args()
    if args.snapshot:
        rows = []
        for repo in REPOS:
            tree = api(f"repos/{OWNER}/{repo}/git/trees/HEAD?recursive=1")
            if tree.get("truncated"):
                raise ValueError("Truncated GitHub tree: cannot certify registry coverage")
            for x in tree["tree"]:
                p = x["path"]
                if p.endswith(".tif") and ("downloads/" in p or "submissions/" in p):
                    rows.append(
                        {
                            "repo": repo,
                            "path": p,
                            "blob": x["sha"],
                            "revision": tree["sha"],
                            "bytes": x["size"],
                            "url": f"https://github.com/{OWNER}/{repo}/blob/{tree['sha']}/{p}",
                        }
                    )
    else:
        rows = json.loads(REGISTRY.read_text())["entries"]
    dest = ROOT / "data/research/peer_review/rasters"
    dest.mkdir(parents=True, exist_ok=True)

    def restore(row):
        p = dest / (row["blob"] + ".tif")
        if not p.exists():
            d = api(f"repos/{OWNER}/{row['repo']}/git/blobs/{row['blob']}")
            b = base64.b64decode(d["content"], validate=False)
            if hashlib.sha1(b"blob " + str(len(b)).encode() + b"\0" + b).hexdigest() != row["blob"]:
                raise ValueError("Git blob identity mismatch")
            tmp = p.with_suffix(".partial")
            tmp.write_bytes(b)
            tmp.replace(p)
        b = p.read_bytes()
        digest = hashlib.sha256(b).hexdigest()
        if len(b) != row["bytes"] or (row.get("sha256") and row["sha256"] != digest):
            raise ValueError(f"Pinned raster mismatch: {row['repo']}/{row['path']}")
        return row["blob"], digest

    blobs = {r["blob"]: r for r in rows}
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        hashes = dict(pool.map(restore, blobs.values()))
    for r in rows:
        r["sha256"] = hashes[r["blob"]]
        r["cache_path"] = str((dest / (r["blob"] + ".tif")).relative_to(ROOT))
    if args.snapshot:
        REGISTRY.write_text(
            json.dumps(
                {
                    "scope": "Every downloadable TIFF under docs/downloads or "
                    "submissions in the nine requested repositories; not all "
                    "possible unpublished registry rasters.",
                    "entries": rows,
                },
                indent=2,
            )
            + "\n"
        )
    print(f"Verified {len(rows)} references, {len(blobs)} unique blobs; no slots used")


if __name__ == "__main__":
    main()
