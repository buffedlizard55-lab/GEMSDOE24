#!/usr/bin/env python3
"""Freeze a union of old pins, current nine-site pins, peer blobs and local TIFFs.

No predictions are generated. Identical footprint content is deduplicated, with
all alias provenance retained. Missing/changed registered bytes are fatal.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems.github_archive import safe_relative  # noqa: E402
from gems.validator import sha256_file  # noqa: E402

OUTPUT = ROOT / "registry/tnr1_union_20261026.json"


def main():
    if OUTPUT.exists():
        raise SystemExit("TNR1 registry is frozen; do not change comparators after the experiment")
    with rasterio.open(ROOT / "data/bridge/sample_submission.tif") as ds:
        fp = np.isfinite(ds.read(1))
        grid = ds.shape, ds.crs, ds.transform, 1
    original = json.loads((ROOT / "registry/priority_rasters.json").read_text())
    restored = json.loads((ROOT / "data/research/tnr1/legacy_priority.json").read_text())
    restored_by_sha = {row["sha256"]: row for row in restored["unique_rasters"]}
    restored_by_sha.update({row["sha256"]: row for row in restored["duplicate_content_variants"]})
    rows = []
    for row in original["unique_rasters"]:
        replacement = restored_by_sha[row["sha256"]]
        rows.append({**row, "cache_path": replacement["cache_path"], "origin": "legacy_priority"})
    current = json.loads((ROOT / "registry/priority_rasters_20261026_tnr1.json").read_text())
    rows.extend({**row, "origin": "current_priority"} for row in current["unique_rasters"])
    peers = json.loads((ROOT / "registry/peer_rasters_20261025.json").read_text())
    for row in peers["entries"]:
        if row.get("role") == "format_demo_not_submission":
            continue
        rows.append(
            {
                **row,
                "file": row["path"],
                "id": "peer-" + row["blob"],
                "origin": "legacy_peer",
            }
        )
    rows.extend(
        {
            "file": str(path.relative_to(ROOT)),
            "cache_path": str(path.relative_to(ROOT)),
            "sha256": sha256_file(path),
            "id": "local-" + path.stem,
            "origin": "current_local",
        }
        for path in sorted((ROOT / "docs/downloads").glob("*.tif"))
    )
    seen, unique, aliases = {}, [], []
    for row in rows:
        path = ROOT / safe_relative(row["cache_path"])
        if sha256_file(path) != row["sha256"]:
            raise ValueError(f"Registered file changed: {row['file']}")
        with rasterio.open(path) as ds:
            if (ds.shape, ds.crs, ds.transform, ds.count) != grid:
                raise ValueError(f"Registered file is off-grid: {row['file']}")
            values = ds.read(1)
        inside = values[fp]
        if not np.isfinite(inside).all() or np.any((inside < 0) | (inside > 1)):
            raise ValueError(f"Registered values are invalid: {row['file']}")
        digest = hashlib.sha256(np.asarray(inside, dtype="<f4").tobytes()).hexdigest()
        if row.get("footprint_sha256", digest) != digest:
            raise ValueError("Registered footprint identity changed")
        row["footprint_sha256"] = digest
        row["positive_pixels"] = int((inside > 0).sum())
        row["source_id"] = row["id"]
        if digest in seen:
            aliases.append({**row, "same_footprint_as": seen[digest]})
        else:
            row["id"] = f"tnr1-registry-{len(unique) + 1:03d}"
            seen[digest] = row["id"]
            unique.append(row)
    result = {
        "scope": "Union of frozen priority/peer pins, refreshed nine priority repositories, and all pre-run local TIFFs; not every unseen parallel artifact or all 92 sites",
        "unique_rasters": unique,
        "aliases": aliases,
        "literal_all_entry_rule": True,
        "no_calibration_control_excluded": True,
        "template_sha256": sha256_file(ROOT / "data/bridge/sample_submission.tif"),
        "source_manifests": {
            str(path.relative_to(ROOT)): sha256_file(path)
            for path in (
                ROOT / "registry/priority_rasters.json",
                ROOT / "registry/peer_rasters_20261025.json",
                ROOT / "registry/priority_rasters_20261026_tnr1.json",
            )
        },
        "organizer_confirmed_scores": [],
    }
    OUTPUT.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"unique_rasters": len(unique), "aliases": len(aliases)}))


if __name__ == "__main__":
    main()
