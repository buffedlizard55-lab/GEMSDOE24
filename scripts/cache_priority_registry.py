#!/usr/bin/env python3
"""Pin nine priority sites' GitHub source and comparison-only submission rasters.

Only GitHub is requested; no automatic requests to DrivenData or Pages hosts.
Use --refresh to discover new commits explicitly. Otherwise retain the pinned
snapshot and validate/download its inputs. Bulk TIFF caches remain ignored.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems.footprint import TRANSFORM, load_footprint  # noqa: E402
from gems.validator import sha256_file  # noqa: E402

REPOS = (24, 25, 27, 28, 30, 31, 32, 33, 36)
CACHE = ROOT / "data/research/priority_review"
MANIFEST = ROOT / "registry/priority_rasters.json"


def gh(endpoint, retries: int = 4):
    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            return subprocess.check_output(
                ["gh", "api", endpoint, "-H", "Accept: application/vnd.github.raw"],
                stderr=subprocess.PIPE,
            )
        except subprocess.CalledProcessError as exc:
            last_exc = exc
            if attempt + 1 < retries:
                time.sleep(1.5 * (attempt + 1))
    assert last_exc is not None
    raise last_exc


def discover(number):
    repo = f"buffedlizard55-lab/GEMSDOE{number}"
    info = json.loads(gh(f"repos/{repo}"))
    ref = json.loads(gh(f"repos/{repo}/commits/{info['default_branch']}"))["sha"]
    tree = json.loads(gh(f"repos/{repo}/git/trees/{ref}?recursive=1"))
    files = []
    for x in tree["tree"]:
        path = x["path"]
        if x["type"] != "blob":
            continue
        if (
            path.endswith(".tif")
            and path.startswith("docs/downloads/")
            or path in ("README.md", "index.html", "docs/index.html", "registry/submissions.json")
            or path.startswith("src/")
            and path.endswith(".py")
        ):
            files.append({"path": path, "blob_sha": x["sha"], "bytes": x.get("size")})
    return {"repo": repo, "ref": ref, "files": files}


_GIT_LOCK = threading.Lock()
_REPO_LOCKS: dict[str, threading.Lock] = {}


def _repo_lock(repo: str) -> threading.Lock:
    with _GIT_LOCK:
        if repo not in _REPO_LOCKS:
            _REPO_LOCKS[repo] = threading.Lock()
        return _REPO_LOCKS[repo]


def _git_repo_dir(repo: str) -> Path:
    repo_dir = Path("/tmp/gems_git_blob_cache") / repo.replace("/", "__")
    with _repo_lock(repo):
        if not (repo_dir / "HEAD").exists():
            repo_dir.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(
                [
                    "git",
                    "clone",
                    "--bare",
                    "--filter=blob:none",
                    f"https://github.com/{repo}.git",
                    str(repo_dir),
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
    return repo_dir


def _git_blob_bytes(repo: str, ref: str, path: str, blob_sha: str | None = None) -> bytes:
    repo_dir = _git_repo_dir(repo)
    spec = blob_sha if blob_sha else f"{ref}:{path}"
    with _repo_lock(repo):
        try:
            return subprocess.check_output(
                ["git", "-C", str(repo_dir), "cat-file", "blob", spec],
                stderr=subprocess.PIPE,
            )
        except subprocess.CalledProcessError:
            subprocess.run(
                ["git", "-C", str(repo_dir), "fetch", "origin", ref],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return subprocess.check_output(
                ["git", "-C", str(repo_dir), "show", f"{ref}:{path}"],
                stderr=subprocess.PIPE,
            )


def cache_one(task):
    repo, ref, entry = task
    path = entry["path"]
    dest = CACHE / repo.split("/")[-1] / path
    if not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            dest.write_bytes(gh(f"repos/{repo}/contents/{path}?ref={ref}", retries=1))
        except subprocess.CalledProcessError:
            dest.write_bytes(_git_blob_bytes(repo, ref, path, entry.get("blob_sha")))
    raw = dest.read_bytes()
    blob = hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()
    if blob != entry["blob_sha"]:
        raise ValueError(f"Git object mismatch: {repo}@{ref}/{path}")
    return {
        "repo": repo,
        "ref": ref,
        "file": path,
        "cache_path": str(dest.relative_to(ROOT)),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "source_url": f"https://github.com/{repo}/blob/{ref}/{path}",
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--refresh", action="store_true")
    args = ap.parse_args()
    snapshot_file = ROOT / "registry/priority_source_snapshot.json"
    if snapshot_file.exists() and not args.refresh:
        sources = json.loads(snapshot_file.read_text())["sources"]
    else:
        with ThreadPoolExecutor(max_workers=4) as pool:
            sources = list(pool.map(discover, REPOS))
        snapshot_file.write_text(json.dumps({"sources": sources}, indent=2) + "\n")
    tasks = [(s["repo"], s["ref"], e) for s in sources for e in s["files"]]
    with ThreadPoolExecutor(max_workers=6) as pool:
        cached = list(pool.map(cache_one, tasks))
    # Local historic references are also registry members, never detector inputs.
    for p in sorted((ROOT / "inputs").rglob("*.tif")):
        cached.append(
            {
                "repo": "local historic references",
                "ref": "07345ea",
                "file": str(p.relative_to(ROOT)),
                "cache_path": str(p.relative_to(ROOT)),
                "sha256": sha256_file(p),
            }
        )
    fp, seen, rasters, rejected, aliases = load_footprint(), {}, [], [], []
    for row in cached:
        if not row["file"].endswith(".tif"):
            continue
        with rasterio.open(ROOT / row["cache_path"]) as s:
            if (
                s.shape != fp.shape
                or s.crs is None
                or s.crs.to_epsg() != 32611
                or s.transform != TRANSFORM
                or s.count != 1
            ):
                rejected.append(
                    {**row, "reason": "not a single-band aligned competition-grid submission"}
                )
                continue
            a = s.read(1)
        if not np.isfinite(a[fp]).all() or np.any((a[fp] < 0) | (a[fp] > 1)):
            rejected.append({**row, "reason": "invalid probability values inside footprint"})
            continue
        key = hashlib.sha256(np.asarray(a[fp], dtype="<f4").tobytes()).hexdigest()
        row["footprint_sha256"] = key
        if key in seen:
            aliases.append({**row, "same_footprint_as": seen[key]})
            continue
        row["id"] = f"registry-{len(rasters) + 1:03d}"
        seen[key] = row["id"]
        row["positive_pixels"] = int((a[fp] > 0).sum())
        rasters.append(row)
    existing = json.loads(MANIFEST.read_text()) if MANIFEST.exists() and not args.refresh else {}
    result = {
        "generated_utc": existing.get("generated_utc", datetime.now(timezone.utc).isoformat()),
        "scope": "All published docs/downloads/*.tif in the nine pinned priority repositories plus local inputs; not every unseen registry in parallel sessions",
        "sources": [{"repo": s["repo"], "ref": s["ref"]} for s in sources],
        "source_files_checked": len(cached),
        "unique_rasters": rasters,
        "duplicate_content_variants": aliases,
        "rejected": rejected,
        "official_score_receipts": [],
        "score_status": "Team source and user claims are NOT ORGANIZER-CONFIRMED scores",
    }
    MANIFEST.write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {
                k: len(result[k])
                for k in ("unique_rasters", "duplicate_content_variants", "rejected")
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
