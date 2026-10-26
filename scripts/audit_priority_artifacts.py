#!/usr/bin/env python3
"""Snapshot changed Git artifacts without mutating the scientific registry.

No rasters are downloaded, trained, scored or authorized. Even identical Git blobs
are not proof of lane uniqueness. Every API failure leaves the site's status unknown.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems.artifact_inventory import SCOPE, compare, git_sha, inventory, summarize  # noqa: E402


def api(path):
    return json.loads(
        subprocess.check_output(["gh", "api", path], text=True, stderr=subprocess.PIPE, timeout=60)
    )


def snapshot(repo, ref):
    commit = api(f"repos/{repo}/commits/{ref}")
    sha = git_sha(commit["sha"])
    if ref != "main" and sha != ref:
        raise ValueError("Resolved pin differs from requested commit")
    tree_sha = git_sha(commit["commit"]["tree"]["sha"])
    tree = api(f"repos/{repo}/git/trees/{tree_sha}?recursive=1")
    return sha, tree_sha, inventory(tree, tree_sha)


def audit(source):
    repo, pin = source["repo"], git_sha(source["ref"])
    base = {
        "repo": repo,
        "pinned_commit": pin,
        "ok_to_submit": False,
        "pixel_uniqueness": "unknown_not_recomputed",
    }
    try:
        _, old_tree, old = snapshot(repo, pin)
        current, new_tree, new = snapshot(repo, "main")
        rows = compare(old, new)
        for row in rows:
            for side, ref in (("before", pin), ("after", current)):
                if row[side] is not None:
                    row[side]["source_url"] = (
                        f"https://github.com/{repo}/blob/{ref}/{quote(row['path'], safe='/')}"
                    )
        return {
            **base,
            "status": "inventoried_not_raster_validated",
            "current_commit": current,
            "pinned_tree": old_tree,
            "current_tree": new_tree,
            "counts": summarize(rows),
            "artifacts": rows,
        }
    except (OSError, subprocess.SubprocessError, ValueError, KeyError, TypeError) as exc:
        return {
            **base,
            "status": "unknown",
            "current_commit": None,
            "counts": None,
            "artifacts": [],
            "error": str(exc)[:240],
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="New versioned JSON path; existing evidence is never overwritten",
    )
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; choose a new snapshot path")
    sources = json.loads((ROOT / "registry/priority_rasters.json").read_text())["sources"]
    with ThreadPoolExecutor(max_workers=3) as pool:
        rows = list(pool.map(audit, sources))
    packet = {
        "schema_version": "priority-git-artifact-inventory-v1",
        "checked_utc": datetime.now(timezone.utc).isoformat(),
        "scope": SCOPE,
        "baseline": "registry/priority_rasters.json source pins (not modified)",
        "warning": "Git SHA-1 IDs are not raster SHA-256 or pixel hashes. No score, range, grid, overlap, archive or LFS content validation performed.",
        "status": "partial_unknown"
        if any(r["status"] == "unknown" for r in rows)
        else "complete_git_inventory_only",
        "sites": rows,
        "new_experiments": 0,
        "submission_slots_used": 0,
        "ok_to_submit": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as handle:
        json.dump(packet, handle, indent=2, allow_nan=False)
        handle.write("\n")
    print(
        json.dumps(
            {
                "status": packet["status"],
                "sites": [{k: r[k] for k in ("repo", "status", "counts")} for r in rows],
            },
            indent=2,
        )
    )
    return int(packet["status"] == "partial_unknown")


if __name__ == "__main__":
    raise SystemExit(main())
