#!/usr/bin/env python3
"""Inspect late merged local files separately; never alter the frozen nine-site audit."""

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems.github_archive import git_blob_sha, safe_relative  # noqa: E402
from gems.novelty import compare_registry  # noqa: E402
from gems.submission import check_variants  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ref", required=True, help="Full immutable integrated main commit")
    args = ap.parse_args()
    if not re.fullmatch(r"[0-9a-f]{40}", args.ref):
        raise ValueError("Full immutable commit required")
    snapshot = json.loads(
        (ROOT / "registry/priority_source_snapshot_20261026_portfolio.json").read_text()
    )
    original = next(s for s in snapshot["sources"] if s["repo"].endswith("GEMSDOE24"))
    prior = {entry["path"]: entry["blob_sha"] for entry in original["files"]}
    tree = subprocess.check_output(
        ["git", "ls-tree", "-r", "-z", args.ref, "docs/downloads"], cwd=ROOT
    ).decode()
    changed = []
    for record in tree.split("\0"):
        if not record:
            continue
        info, path = record.split("\t", 1)
        mode, kind, blob = info.split()
        if kind == "blob" and path.lower().endswith((".tif", ".tiff")) and prior.get(path) != blob:
            if mode != "100644":
                raise ValueError("Only regular cached TIFF files are accepted")
            changed.append((path, blob))
    template = ROOT / "data/bridge/sample_submission.tif"
    with rasterio.open(template) as ds:
        fp = np.isfinite(ds.read(1))
    with rasterio.open(ROOT / "data/bridge/existing_faults.tif") as ds:
        known = fp & (ds.read(1) > 0)
    rows, unique = [], {}
    for path, blob in changed:
        file = ROOT / safe_relative(path)
        if git_blob_sha(file.read_bytes()) != blob:
            raise ValueError("Working file differs from integrated immutable source")
        checks = check_variants(file, template)
        row = {
            "file": path,
            "source_ref": args.ref,
            "blob_sha": blob,
            "source_url": f"https://github.com/buffedlizard55-lab/GEMSDOE24/blob/{args.ref}/{path}",
            "sha256": checks["sha256"],
            "validator_output": checks,
            "new_to_frozen_snapshot": path not in prior,
            "generated_by_this_session": False,
            "scientific_replay": False,
            "source_gates_endorsed": False,
            "ok_to_submit": False,
        }
        if checks["format_valid"]:
            with rasterio.open(file) as ds:
                a = ds.read(1)
            row["positive_on_catalogue"] = int(((a > 0) & known).sum())
            row["positive_outside_template"] = int(((a > 0) & ~fp).sum())
            digest = hashlib.sha256(np.asarray(a[fp], dtype="<f4").tobytes()).hexdigest()
            row["footprint_sha256"] = digest
            unique.setdefault(
                digest,
                {
                    "id": "late-" + digest[:16],
                    "file": path,
                    "cache_path": path,
                    "sha256": checks["sha256"],
                    "footprint_sha256": digest,
                },
            )
        rows.append(row)
    current = json.loads((ROOT / "docs/data/current_best_review.json").read_text())
    with rasterio.open(ROOT / "docs/downloads" / current["submission_name"]) as ds:
        p = fp & (ds.read(1) > 0)
    comparisons = compare_registry(p, fp, list(unique.values()), ROOT, dots=p)
    result = {
        "checked_utc": datetime.now(timezone.utc).isoformat(),
        "source_ref": args.ref,
        "frozen_base_ref": original["ref"],
        "scope": "Late integrated GEMSDOE24 files only; complements, never replaces, the 326-file pinned audit. Other newer peer commits remain unaudited.",
        "new_experiments": 0,
        "new_tiffs_generated_by_this_session": 0,
        "files": rows,
        "distinct_new_contents": len(unique),
        "existing_DPRF1_sha256": current["raster_sha256"],
        "existing_DPRF1_final_dots_vs_late_files": comparisons,
        "preplacement_or_training_replayed": False,
        "source_scientific_claims_endorsed": False,
        "organizer_scores": [],
        "leaderboard_estimate": None,
        "submission_authorized": False,
        "verdict": "negative",
    }
    output = ROOT / "evidence/portfolio_concurrent_local_files_20261026.json"
    if output.exists():
        raise ValueError(
            "Concurrent-file receipt is frozen; use a new versioned audit, not overwrite"
        )
    output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {
                "files": len(rows),
                "distinct_contents": len(unique),
                "DPRF1_final_dot_pass_against_additions_only": comparisons["passed"],
                "max_new_overlap": comparisons["max_dot_overlap"],
                "verdict": "negative",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
