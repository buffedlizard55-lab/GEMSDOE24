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
import re
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems.footprint import TRANSFORM, load_footprint  # noqa: E402
from gems.github_archive import cache_archive, git_blob_sha, safe_relative  # noqa: E402
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
    if tree.get("truncated"):
        raise ValueError("Truncated GitHub tree; registry discovery cannot be complete")
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


def cache_one(task, cache_dir=None):
    """Cache immutable repo/ref/path bytes; never reuse a mutable path across refs."""
    repo, ref, entry = task
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        raise ValueError("Expected GitHub owner/repository")
    if not re.fullmatch(r"[0-9a-f]{40}", ref):
        raise ValueError("A complete immutable commit SHA is required")
    path = str(safe_relative(entry["path"]))
    base = (Path(cache_dir) if cache_dir is not None else CACHE).resolve()
    dest = base / repo / ref / path
    if not dest.resolve().is_relative_to(base):
        raise ValueError("Cache path escapes its root")
    if not dest.exists():
        raw = gh(f"repos/{repo}/contents/{path}?ref={ref}")
        if git_blob_sha(raw) != entry["blob_sha"]:
            raise ValueError(f"Git object mismatch: {repo}@{ref}/{path}")
        dest.parent.mkdir(parents=True, exist_ok=True)
        temporary = dest.with_suffix(dest.suffix + ".partial")
        temporary.write_bytes(raw)
        temporary.replace(dest)
    raw = dest.read_bytes()
    if git_blob_sha(raw) != entry["blob_sha"]:
        raise ValueError(f"Git object mismatch: {repo}@{ref}/{path}")
    if not dest.is_relative_to(ROOT):
        raise ValueError("Cache must remain inside the repository workspace")
    return {
        "repo": repo,
        "ref": ref,
        "file": path,
        "cache_path": str(dest.relative_to(ROOT)),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "blob_sha": entry["blob_sha"],
        "source_url": f"https://github.com/{repo}/blob/{ref}/{path}",
    }


def archive_sources(sources, cache_dir):
    """Discover/cache immutable public archives without using authenticated API quota."""

    def one(source):
        repo = source["repo"]
        ref = source.get("ref")
        if ref is None:
            line = subprocess.check_output(
                ["git", "ls-remote", f"https://github.com/{repo}.git", "HEAD"],
                text=True,
                timeout=60,
            ).strip()
            ref = line.split()[0]

        def selected(path):
            return (
                path.endswith(".tif")
                and path.startswith("docs/downloads/")
                or path
                in ("README.md", "index.html", "docs/index.html", "registry/submissions.json")
                or path.startswith("src/")
                and path.endswith(".py")
            )

        requested = (
            {e["path"]: e["blob_sha"] for e in source["files"]} if "files" in source else None
        )
        files = cache_archive(
            repo,
            ref,
            cache_dir,
            requested=requested,
            select=selected if requested is None else None,
        )
        for entry in files:
            entry["cache_path"] = str(entry["cache_path"].relative_to(ROOT))
        return {"repo": repo, "ref": ref, "files": files}

    with ThreadPoolExecutor(max_workers=3) as pool:
        return list(pool.map(one, sources))


def preserve_frozen_manifest(existing, restored):
    """Restore cache paths without rewriting scientific pins, IDs or historical JSON."""
    if existing["sources"] != restored["sources"]:
        raise ValueError("Frozen registry source pins changed; use a new versioned manifest")
    old_policy = existing.get("footprint_identity", {}).get("policy", "legacy-science")
    if old_policy != restored["footprint_identity"]["policy"]:
        raise ValueError("Frozen footprint policy changed; use a new versioned manifest")
    if (
        existing.get("footprint_identity")
        and existing["footprint_identity"] != restored["footprint_identity"]
    ):
        raise ValueError("Frozen footprint identity changed; use a new versioned manifest")

    def keyed(data):
        rows = [
            r for k in ("unique_rasters", "duplicate_content_variants", "rejected") for r in data[k]
        ]
        mapping = {(r["repo"], r["ref"], r["file"]): r for r in rows}
        if len(mapping) != len(rows):
            raise ValueError("Duplicate artifact key in frozen manifest")
        return mapping

    before, after = keyed(existing), keyed(restored)
    if set(before) != set(after):
        raise ValueError("Frozen registry membership changed; use a new versioned manifest")
    for key, original in before.items():
        current = after[key]
        if any(
            original.get(field) != current.get(field)
            for field in ("sha256", "footprint_sha256", "reason")
        ):
            raise ValueError("Frozen artifact identity or validity changed")
        destination = ROOT / safe_relative(original["cache_path"])
        if not destination.resolve().is_relative_to(ROOT):
            raise ValueError("Frozen cache path escapes workspace")
        source = ROOT / safe_relative(current["cache_path"])
        if destination.exists():
            if sha256_file(destination) != original["sha256"]:
                raise ValueError("Existing frozen cache bytes changed")
        else:
            if not str(safe_relative(original["cache_path"])).startswith("data/research/"):
                raise ValueError("Refusing to restore cache over non-cache project paths")
            destination.parent.mkdir(parents=True, exist_ok=True)
            temporary = destination.with_suffix(destination.suffix + ".partial")
            shutil.copyfile(source, temporary)
            temporary.replace(destination)
    return existing


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--transport", choices=("api", "archive"), default="api")
    ap.add_argument("--manifest", type=Path, default=MANIFEST)
    ap.add_argument(
        "--snapshot", type=Path, default=ROOT / "registry/priority_source_snapshot.json"
    )
    ap.add_argument("--cache-dir", type=Path, default=CACHE)
    ap.add_argument(
        "--footprint-policy",
        choices=("legacy-science", "sample-template"),
        default="legacy-science",
        help="Explicit mask identity; never silently rewrite historical footprint hashes",
    )
    args = ap.parse_args()
    manifest_path = args.manifest.resolve()
    snapshot_file = args.snapshot.resolve()
    cache_dir = args.cache_dir.resolve()
    for path in (manifest_path, snapshot_file, cache_dir):
        if not path.is_relative_to(ROOT):
            raise ValueError("Registry/cache output must remain inside the workspace")
    if args.refresh and (manifest_path.exists() or snapshot_file.exists()):
        raise ValueError(
            "Frozen snapshots cannot be refreshed in place; supply new versioned paths"
        )
    if args.transport == "archive":
        prior = (
            json.loads(snapshot_file.read_text())["sources"]
            if snapshot_file.exists() and not args.refresh
            else [{"repo": f"buffedlizard55-lab/GEMSDOE{n}"} for n in REPOS]
        )
        sources = archive_sources(prior, cache_dir)
        if not snapshot_file.exists() or args.refresh:
            snapshot_file.parent.mkdir(parents=True, exist_ok=True)
            snapshot_file.write_text(json.dumps({"sources": sources}, indent=2) + "\n")
    elif snapshot_file.exists() and not args.refresh:
        sources = json.loads(snapshot_file.read_text())["sources"]
    else:
        with ThreadPoolExecutor(max_workers=4) as pool:
            sources = list(pool.map(discover, REPOS))
        snapshot_file.parent.mkdir(parents=True, exist_ok=True)
        snapshot_file.write_text(json.dumps({"sources": sources}, indent=2) + "\n")
    if args.transport == "archive":
        cached = [
            {
                "repo": s["repo"],
                "ref": s["ref"],
                "file": e["path"],
                "cache_path": e["cache_path"],
                "sha256": sha256_file(ROOT / e["cache_path"]),
                "source_url": f"https://github.com/{s['repo']}/blob/{s['ref']}/{e['path']}",
            }
            for s in sources
            for e in s["files"]
        ]
    else:
        tasks = [(s["repo"], s["ref"], e) for s in sources for e in s["files"]]
        with ThreadPoolExecutor(max_workers=6) as pool:
            cached = list(pool.map(lambda task: cache_one(task, cache_dir), tasks))
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
    if args.footprint_policy == "sample-template":
        template = ROOT / "data/bridge/sample_submission.tif"
        with rasterio.open(template) as ds:
            fp = np.isfinite(ds.read(1))
            if (
                ds.shape != load_footprint().shape
                or ds.crs.to_epsg() != 32611
                or ds.transform != TRANSFORM
            ):
                raise ValueError("Pinned sample grid mismatch")
        footprint_source = str(template.relative_to(ROOT))
    else:
        fp = load_footprint()
        footprint_source = "docs/data/footprint.bin"
    seen, rasters, rejected, aliases = {}, [], [], []
    for row in cached:
        if not row["file"].lower().endswith((".tif", ".tiff")):
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
    existing = (
        json.loads(manifest_path.read_text()) if manifest_path.exists() and not args.refresh else {}
    )
    result = {
        "generated_utc": existing.get("generated_utc", datetime.now(timezone.utc).isoformat()),
        "scope": json.loads(snapshot_file.read_text()).get(
            "scope", "All published docs/downloads/*.tif in the nine pinned priority repositories"
        )
        + "; local inputs/calibration references retained; not every TIFF in all 92 sites or all historical refs",
        "sources": [{"repo": s["repo"], "ref": s["ref"]} for s in sources],
        "footprint_identity": {
            "policy": args.footprint_policy,
            "source": footprint_source,
            "source_sha256": sha256_file(ROOT / footprint_source),
            "pixels": int(fp.sum()),
            "mask_sha256": hashlib.sha256(fp.astype("uint8").tobytes()).hexdigest(),
        },
        "source_files_checked": len(cached),
        "unique_rasters": rasters,
        "duplicate_content_variants": aliases,
        "rejected": rejected,
        "official_score_receipts": [],
        "score_status": "Team source and user claims are NOT ORGANIZER-CONFIRMED scores",
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    if existing:
        result = preserve_frozen_manifest(existing, result)
    else:
        manifest_path.write_text(json.dumps(result, indent=2) + "\n")
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
