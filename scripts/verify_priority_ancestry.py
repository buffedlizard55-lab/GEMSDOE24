#!/usr/bin/env python3
"""Replay the nine named artifact geometries; never infer organizer scores."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import rasterio
from restore_data import ROOT, gh_bytes, sha256_file
from scipy.ndimage import distance_transform_edt


def main():
    recorded = json.loads((ROOT / "evidence/peer_forensics_20261025.json").read_text())
    with rasterio.open(ROOT / "data/bridge/sample_submission.tif") as ds:
        fp, grid = np.isfinite(ds.read(1)), (ds.shape, ds.crs, ds.transform)
    with rasterio.open(ROOT / "data/bridge/labels.tif") as ds:
        known = fp & (ds.read(1) > 0)
    distance = distance_transform_edt(~known)
    arrays, receipts = {}, []
    for row in recorded["artifacts"]:
        parts = row["url"].split("/")
        if parts[:3] != ["https:", "", "github.com"] or parts[5] != "blob":
            raise ValueError("Pinned GitHub blob URL required")
        repo, ref, source = "/".join(parts[3:5]), parts[6], "/".join(parts[7:])
        path = ROOT / "data/research/ancestry" / row["repo"] / Path(source).name
        if not path.exists():
            gh_bytes(repo, source, ref, path)
        if sha256_file(path) != row["sha256"]:
            raise ValueError("Named artifact hash mismatch")
        with rasterio.open(path) as ds:
            if (ds.shape, ds.crs, ds.transform) != grid or ds.count != 1:
                raise ValueError("Named artifact grid mismatch")
            a = ds.read(1)
        if not np.isfinite(a[fp]).all() or not np.isin(a[fp], [0, 1]).all():
            raise ValueError("Expected finite binary reference")
        p = fp & (a > 0)
        arrays[row["repo"]] = p
        for key, actual in {
            "dot_count": int(p.sum()),
            "on_catalogue": int((p & known).sum()),
            "within_200m_catalogue": int((p & (distance <= 2)).sum()),
        }.items():
            if row[key] != actual:
                raise ValueError(f"Recorded {row['repo']} {key} differs")
        receipts.append(
            {
                "repo": row["repo"],
                "url": row["url"],
                "sha256": row["sha256"],
                "dot_count": int(p.sum()),
                "recorded_counts_reproduced": True,
            }
        )
    best = arrays["GEMSDOE32"]
    tests = {
        "GEMSDOE25_equals_GEMSDOE30": np.array_equal(arrays["GEMSDOE25"], arrays["GEMSDOE30"]),
        "GEMSDOE32_equals_GEMSDOE25_after_200m_clearance": np.array_equal(
            arrays["GEMSDOE25"] & (distance > 2), best
        ),
        "GEMSDOE32_equals_GEMSDOE31_after_200m_clearance": np.array_equal(
            arrays["GEMSDOE31"] & (distance > 2), best
        ),
        "GEMSDOE36_contains_every_GEMSDOE32_dot": not (best & ~arrays["GEMSDOE36"]).any(),
    }
    if not all(tests.values()):
        raise ValueError("Recorded ancestry does not reproduce")
    output = {
        "evidence_class": "COMPUTED-ARTIFACT-FORENSICS; counts and geometry, NOT scores",
        "artifacts": receipts,
        "tests": {k: bool(v) for k, v in tests.items()},
        "removed_from_GEMSDOE25": int((arrays["GEMSDOE25"] & ~best).sum()),
        "removed_from_GEMSDOE31": int((arrays["GEMSDOE31"] & ~best).sum()),
        "added_by_GEMSDOE36": int((arrays["GEMSDOE36"] & ~best).sum()),
        "organizer_confirmed_scores": [],
        "interpretation_limit": "Geometry does not reveal hidden TP/FP, vent discoveries, or why an unconfirmed score changed.",
    }
    (ROOT / "evidence/oj1_priority_ancestry_replay.json").write_text(
        json.dumps(output, indent=2, allow_nan=False) + "\n"
    )
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
