#!/usr/bin/env python3
"""Byte-level verification of the nine focus-site "best" files (read-only).

For each GEMSDOE focus file (downloaded from its public GitHub repo into a
gitignored folder) this script records:
  * sha256 and byte size,
  * the official format checks from the DrivenData page (EPSG:32611, 100 m grid,
    single float32 band, identical shape/transform to the bridge template,
    values in [0, 1], NaN/null only outside the footprint),
  * dot count (value > 0 inside footprint) and whether values are binary,
  * the pairwise 3-px overlap: fraction of A's dots with a dot of B within 3 px
    (the same test as the uniqueness gate in docs/executive-summary.html).

Output: evidence/nine_site_verify_20261030.json. No score is computed here.
Scores are OWNER-REPORTED (taken from the request text), not organizer receipts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "data/bridge/sample_submission.tif"
DEFAULT_DIR = ROOT / "data/research/nine_site_verify"
OUT = ROOT / "evidence/nine_site_verify_20261030.json"
SITES = [
    "GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30",
    "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36",
]
RADIUS_PX = 3.0


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def format_check(path: Path, template_profile: dict, footprint: np.ndarray) -> dict:
    with rasterio.open(path) as ds:
        a = ds.read(1).astype(np.float64)
        info = {
            "crs": str(ds.crs),
            "shape": list(ds.shape),
            "transform": list(ds.transform)[:6],
            "dtype": ds.dtypes[0],
            "count": ds.count,
            "nodata": ds.nodata,
        }
    info["crs_ok"] = info["crs"] == "EPSG:32611"
    info["shape_ok"] = tuple(info["shape"]) == tuple(template_profile["shape"])
    info["transform_ok"] = np.allclose(
        info["transform"], list(template_profile["transform"])[:6]
    )
    info["single_band_float32"] = info["count"] == 1 and info["dtype"] == "float32"
    finite = np.isfinite(a)
    info["nan_inside_footprint"] = int((~finite & footprint).sum())
    info["finite_outside_footprint"] = int((finite & ~footprint).sum())
    fin_vals = a[finite]
    info["min_finite"] = float(fin_vals.min()) if fin_vals.size else None
    info["max_finite"] = float(fin_vals.max()) if fin_vals.size else None
    info["values_in_0_1"] = bool(fin_vals.size and fin_vals.min() >= 0 and fin_vals.max() <= 1)
    info["binary_values"] = bool(np.isin(fin_vals, (0.0, 1.0)).all()) if fin_vals.size else False
    info["dots_gt0_in_footprint"] = int(((a > 0) & footprint).sum())
    info["dots_gt0_outside_footprint"] = int(((a > 0) & ~footprint).sum())
    info["official_format_pass"] = bool(
        info["crs_ok"]
        and info["shape_ok"]
        and info["transform_ok"]
        and info["single_band_float32"]
        and info["nan_inside_footprint"] == 0
        and info["values_in_0_1"]
        and info["dots_gt0_outside_footprint"] == 0
    )
    return info, a


def dot_mask(a: np.ndarray, footprint: np.ndarray) -> np.ndarray:
    return np.isfinite(a) & (a > 0) & footprint


def overlap_3px(a_dots: np.ndarray, b_dots: np.ndarray) -> float:
    """Fraction of A's dots lying within 3 px (Euclidean) of at least one B dot."""
    n = int(a_dots.sum())
    if n == 0:
        return float("nan")
    dist_to_b = distance_transform_edt(~b_dots)
    return float(((dist_to_b <= RADIUS_PX) & a_dots).sum() / n)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dir", type=Path, default=DEFAULT_DIR)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    with rasterio.open(TEMPLATE) as t:
        template_profile = {
            "shape": t.shape,
            "transform": t.transform,
        }
        footprint = np.isfinite(t.read(1))

    results, masks = {}, {}
    for site in SITES:
        path = args.dir / f"{site}.tif"
        if not path.exists():
            print(f"MISSING {path}", file=sys.stderr)
            return 1
        info, a = format_check(path, template_profile, footprint)
        info["file"] = path.name
        info["bytes"] = path.stat().st_size
        info["sha256"] = sha256(path)
        masks[site] = dot_mask(a, footprint)
        info["dot_count"] = int(masks[site].sum())
        results[site] = info

    names = list(SITES)
    matrix = {}
    for a_name in names:
        matrix[a_name] = {}
        for b_name in names:
            if a_name == b_name:
                continue
            matrix[a_name][b_name] = round(overlap_3px(masks[a_name], masks[b_name]), 6)

    max_pair = {}
    for a_name in names:
        others = {k: v for k, v in matrix[a_name].items()}
        worst = max(others, key=others.get)
        max_pair[a_name] = {"max_overlap_vs": worst, "max_overlap": others[worst]}

    payload = {
        "schema": "nine-site-verify-v1",
        "scope": "Byte, format and 3-px overlap audit of nine focus files; no score computed",
        "owner_reported_scores_not_organizer_confirmed": {
            "GEMSDOE24": 0.2477, "GEMSDOE25": 0.2600, "GEMSDOE27": 0.2449,
            "GEMSDOE28": 0.2710, "GEMSDOE30": 0.2600, "GEMSDOE31": 0.2708,
            "GEMSDOE32": 0.2778, "GEMSDOE33": 0.2632, "GEMSDOE36": 0.2750,
        },
        "template": {"path": "data/bridge/sample_submission.tif",
                     "sha256": sha256(TEMPLATE)},
        "footprint_cells": int(footprint.sum()),
        "files": results,
        "overlap_3px_A_dots_within_3px_of_B_dots": matrix,
        "max_pairwise_overlap": max_pair,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(f"wrote {args.out}")
    for s in names:
        r = results[s]
        print(
            f"{s}: dots={r['dot_count']} format_pass={r['official_format_pass']} "
            f"nan_in_fp={r['nan_inside_footprint']} max_overlap={max_pair[s]['max_overlap']:.4f} "
            f"vs {max_pair[s]['max_overlap_vs']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
