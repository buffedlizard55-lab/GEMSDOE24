#!/usr/bin/env python3
"""Recompute geometric ancestry of the nine user-named best artifacts; no scores inferred."""

import hashlib
import json
import os
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]


def main():
    os.chdir(ROOT)
    rows = json.load(open("registry/peer_rasters_20261025.json"))["entries"]
    patterns = {
        24: "h25-1-dotted-h19-5-d1-5-",
        25: "gems25-dotted-h19-5-d2-8-",
        27: "gems27-topo-gap-closure-t-v2-on-d1-5-",
        28: "gems28-h36-1-rung30-blind-r1-",
        30: "gemsdoe30-d28-poisson300m-offcat-44090-",
        31: "gemsdoe31-h27-4-solo-d28-",
        32: "gemsdoe32-h33-h33-2-b2-",
        33: "GEMSDOE33-h33d-analog-tip-stepover-r30-",
        36: "gemsdoe36-anderson-geothermal-pinn-38854-",
    }
    with rasterio.open("data/bridge/sample_submission.tif") as d:
        fp = np.isfinite(d.read(1))
    with rasterio.open("data/bridge/labels.tif") as d:
        known = d.read(1) > 0
    distance = distance_transform_edt(~known)
    selected = []
    for n, pat in patterns.items():
        rr = [r for r in rows if r["repo"] == f"GEMSDOE{n}" and pat in r["path"]]
        if not rr:
            raise ValueError(f"Missing named artifact in pinned registry: GEMSDOE{n}")
        r = sorted(rr, key=lambda r: "nan" in r["path"])[0]
        path = ROOT / r["cache_path"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != r["sha256"]:
            raise ValueError("Peer raster hash mismatch")
        with rasterio.open(path) as d:
            if d.shape != fp.shape:
                raise ValueError("Peer raster grid shape mismatch")
            a = d.read(1)
        p = fp & (a > 0)
        selected.append((n, r, p))
        print(n, Path(r["path"]).name, int(p.sum()))
    best = next(p for n, r, p in selected if n == 32)
    evidence = []
    for n, r, p in selected:
        with rasterio.open(r["cache_path"]) as ds:
            a = ds.read(1)
        evidence.append(
            {
                "repo": r["repo"],
                "file": Path(r["path"]).name,
                "sha256": r["sha256"],
                "url": r["url"],
                "dot_count": int(p.sum()),
                "on_catalogue": int((p & known).sum()),
                "within_200m_catalogue": int((p & (distance <= 2)).sum()),
                "binary": bool(np.isin(a[fp], [0, 1]).all()),
                "same_as_h33": bool(np.array_equal(p, best)),
                "jaccard_h33": float((p & best).sum() / (p | best).sum()),
                "h33_is_subset": bool(not (best & ~p).any()),
                "score_status": "UNVERIFIED-OWNER-REPORT; no artifact-linked organizer receipt recovered",
            }
        )
    pruned = {}
    for n in [24, 25, 31]:
        p = next(p for k, r, p in selected if k == n)
        pruned[str(n)] = {
            "matches_h33_after_200m_clearance": bool(np.array_equal(p & (distance > 2), best)),
            "removed_dots": int((p & ~best).sum()),
            "added_dots": int((best & ~p).sum()),
        }
    output = {
        "evidence_class": "COMPUTED-ARTIFACT-FORENSICS, not a score",
        "review_scope": "User-named best artifacts in nine repositories; hashes verified from pinned GitHub blobs",
        "artifacts": evidence,
        "h33_lineage_tests": pruned,
        "organizer_confirmed_scores": [],
        "official_reference": {
            "repository": "https://github.com/drivendataorg/gems-prize-reference-solution",
            "tree": "aebe92f7c8a990f0e3443451b7a825d9afd6336b",
            "notebook_sha256": "1a7622732ba00f67237058bc0efe79b45ba4e87c449fc9c1e5d6ea659de92ca0",
            "verification_scope": "Recorded official-source snapshot from the 2026-10-25 review; this geometry replay does not fetch or reauthenticate the notebook",
            "verified_claims": [
                "Fault detection target, not geothermal vent classification",
                "Training Tversky alpha 0.2 beta 0.8",
                "CPU option documented; GPU faster, not required",
            ],
        },
    }
    Path("evidence/peer_forensics_20261025.json").write_text(json.dumps(output, indent=2) + "\n")


if __name__ == "__main__":
    main()
