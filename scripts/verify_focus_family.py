#!/usr/bin/env python3
"""Reproducible byte-level verification of the nine focus-site submissions.

Reads GeoTIFFs that were obtained from the public GitHub repositories
(pinned by commit in the manifest below) and writes an evidence JSON with:

* SHA-256, grid (CRS / shape / transform), finite and [0, 1] range checks;
* dot counts (binary value == 1, finite cells only);
* directed 3-px overlap matrix (fraction of ROW dots within 3 px of COL dots);
* exact subset tests (is ROW a subset of COL?).

It does NOT score anything and does NOT authorise a submission. The 'score'
column is the owner-reported figure from the prompt, labelled as such.

Usage (paths are relative to --root, which holds one clone per site):
    python scripts/verify_focus_family.py --root /path/to/peer_scratch \
        --out evidence/focus_family_verification_20261026.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone

import numpy as np
import rasterio
from scipy import ndimage

# label -> (owner-reported score, repo-relative path inside the site clone)
MANIFEST: dict[str, tuple[float, str, str]] = {
    "GEMSDOE32 h33-h33-2-b2": (
        0.2778,
        "GEMSDOE32",
        "docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif",
    ),
    "GEMSDOE30 d28-poisson300m": (
        0.2600,
        "GEMSDOE30",
        "docs/downloads/gemsdoe30-d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca.tif",
    ),
    "GEMSDOE25 dotted-h19-5-d2-8": (
        0.2600,
        "GEMSDOE25",
        "docs/downloads/gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif",
    ),
    "GEMSDOE31 h27-4-solo-d28": (
        0.2708,
        "GEMSDOE31",
        "docs/downloads/gemsdoe31-h27-4-solo-d28-20261004-8acb75e1-nan.tif",
    ),
    "GEMSDOE28 h36-1-rung30-blind-r1": (
        0.2710,
        "GEMSDOE28",
        "docs/downloads/gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan.tif",
    ),
    "GEMSDOE33 h33d-analog-tip-stepover": (
        0.2632,
        "GEMSDOE33",
        "docs/downloads/GEMSDOE33-h33d-analog-tip-stepover-r30-20261004-cb490425926e.tif",
    ),
    "GEMSDOE24 h25-1-dotted-h19-5-d1.5": (
        0.2477,
        "GEMSDOE24",
        "docs/downloads/gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif",
    ),
    "GEMSDOE27 topo-gap-closure-t-v2": (
        0.2449,
        "GEMSDOE27",
        "docs/downloads/gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan.tif",
    ),
    "GEMSDOE36 anderson-geothermal-pinn": (
        0.2750,
        "GEMSDOE36",
        "docs/downloads/gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif",
    ),
}


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load(path: str):
    with rasterio.open(path) as ds:
        arr = ds.read(1)
        meta = {
            "driver": ds.driver,
            "dtype": ds.dtypes[0],
            "count": ds.count,
            "crs": ds.crs.to_string() if ds.crs else None,
            "shape": list(ds.shape),
            "transform": [float(v) for v in ds.transform][:6],
            "nodata": ds.nodata,
        }
    return arr, meta


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, help="directory holding one clone per site")
    ap.add_argument("--out", required=True)
    ap.add_argument("--extra", nargs="*", default=[], help="extra local TIFs as label=path")
    args = ap.parse_args()

    files: dict[str, dict] = {}
    masks: dict[str, np.ndarray] = {}
    for label, (score, site, rel) in MANIFEST.items():
        path = os.path.join(args.root, site, rel)
        if not os.path.exists(path):
            files[label] = {"status": "MISSING", "path": path}
            continue
        arr, meta = load(path)
        fin = np.isfinite(arr)
        dot = fin & (arr == 1)
        files[label] = {
            "status": "OK",
            "owner_reported_score": score,
            "score_evidence": "OWNER-REPORTED (prompt); not an organizer receipt",
            "site": site,
            "source_path": rel,
            "sha256": sha256(path),
            "bytes": os.path.getsize(path),
            **meta,
            "nonfinite_cells": int((~fin).sum()),
            "outside_0_1_finite_cells": int((fin & ((arr < 0) | (arr > 1))).sum()),
            "dots_value_eq_1": int(dot.sum()),
        }
        masks[label] = dot

    for item in args.extra:
        label, path = item.split("=", 1)
        arr, meta = load(path)
        fin = np.isfinite(arr)
        files[label] = {
            "status": "OK",
            "source_path": path,
            "sha256": sha256(path),
            "bytes": os.path.getsize(path),
            **meta,
            "nonfinite_cells": int((~fin).sum()),
            "outside_0_1_finite_cells": int((fin & ((arr < 0) | (arr > 1))).sum()),
            "dots_value_eq_1": int((fin & (arr == 1)).sum()),
        }
        masks[label] = fin & (arr == 1)

    keys = list(masks)
    dt = {k: ndimage.distance_transform_edt(~masks[k]) for k in keys}
    overlap: dict[str, dict[str, float | None]] = {}
    subset: dict[str, dict[str, object]] = {}
    for a in keys:
        overlap[a] = {}
        subset[a] = {}
        for b in keys:
            if a == b:
                continue
            A = masks[a]
            overlap[a][b] = round(float((dt[b][A] <= 3).mean()), 6) if A.any() else None
            inter = int((A & masks[b]).sum())
            only_a = int((A & ~masks[b]).sum())
            subset[a][b] = {
                "intersection": inter,
                "row_only": only_a,
                "row_subset_of_col": only_a == 0,
            }

    doc = {
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "evaluator_version": "not-run (pairwise geometry only; no DTI computed here)",
        "statement": "Pixel-geometry evidence only. Not a leaderboard estimate and not a submission authorisation.",
        "files": files,
        "directed_3px_overlap_row_within_3px_of_col": overlap,
        "exact_dot_subset": subset,
    }
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2, sort_keys=True)
    print(f"wrote {args.out} ({len(files)} files)")


if __name__ == "__main__":
    main()
