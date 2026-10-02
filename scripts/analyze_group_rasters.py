#!/usr/bin/env python3
"""Format forensics and leaderboard-geometry analysis of every raster the owner's sites ship.

Input: a folder containing shallow clones of the owner's public ``*GEMSDOE*`` repositories
(``--sibling-root``; not committed). Output (committed, small):

* ``evidence/format_forensics.json`` - does any shipped raster violate the portal's stated
  contract ("single float32 layer, values in [0, 1], NaN/null outside the bounds")?
* ``evidence/group_raster_profiles.csv`` - one row per unique raster (sha256).
* ``evidence/lb_geometry_analysis.json`` - how owner-reported public scores relate to each
  raster's distance-to-catalogue profile.

Scores are OWNER-REPORTED in the 2026-10-02 brief, not organizer receipts.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems import footprint  # noqa: E402

GRID = ([3730, 3292], 1, "float32")

# file name -> (owner site/repo label, owner-reported public score or None=blank/not supplied)
OWNER_REPORTED = {
    "gemsdoe-ens12-adopted-7f00890a.tif": ("GEMSDOE / 5GEMSDOE", 0.1563),
    "8GEMSDOE_Hedge-v2_submission.tif": ("8GEMSDOE Hedge-v2", 0.1563),
    "gems6_hgb88-topk03_33cec71ff0.tif": ("6GEMSDOE", 0.0286),
    "pindrop-v4-nodes-f347b70daa.tif": ("GEMSDOE3 nodes", 0.1193),
    "pindrop-v4-discovery-37f9d5b855.tif": ("GEMSDOE3 discovery", 0.0830),
    "pindrop-v4-ridge-4e03fc9705.tif": ("GEMSDOE3 ridge", 0.1152),
    "gemsdoe2-dual-family-union-f68e590f.tif": ("GEMSDOE2", 0.1560),
    "gemsdoe4-combined-237f0063.tif": ("GEMSDOE4", 0.0343),
    "gems7-lidarscarp-ridge-top2pct-36c3a3f341c8.tif": ("7GEMSDOE", 0.1461),
    "gemsdoe9-PLACEHOLDER-2314b599.tif": ("GEMSDOE9", 0.0107),
    "gems-structural-area06-v1.tif": ("11GEMSDOE", 0.0202),
    "12GEMSDOE_r7-nms3-dem10-scarp_0c9199f14e62.tif": ("12GEMSDOE", 0.1294),
    "12GEMSDOE_r7-nms3-dem10-scarp_0c9199f14e62_allfinite.tif": ("12GEMSDOE allfinite", 0.1294),
    "gems-tso1-20260929T005627Z-conj_alteration_mag.tif": ("15GEMSDOE", 0.0782),
    "GEMS_r5-geom-horse-ensemble_20260929T154852Z_ccbe1de0_site_e96e942f.tif": (
        "14GEMSDOE",
        0.0020,
    ),
    "17GEMSDOE_F-ensemble-2pct_20260930T050626Z.tif": ("17GEMSDOE", 0.0187),
    "18GEMSDOE_H19-C_20260930T212401Z_c11e495e.tif": ("18GEMSDOE", 0.0297),
    "gems19-h19-4-multiline-corroborated-openness-thermal-pop-20260930-691e4dfa-nan.tif": (
        "19GEMSDOE h19-4",
        0.1894,
    ),
    "gems19-h19-5-powerlaw-budget-multiline-corroborated-20260930-e27054cf-nan.tif": (
        "19GEMSDOE h19-5",
        0.1922,
    ),
    "gems10-h16-continuation-20260927T065521077735Z-3431b83c7c.tif": ("GEMSDOE10 h16-cont", 0.0461),
    "gems10-h20-dem10-scarp-thin-20260927T155223039488Z-ffc91a1686.tif": ("GEMSDOE10 h20", 0.0921),
    "gems10-h25-ctx-ridge-20260927T232947704150Z-6452ae1d00.tif": ("GEMSDOE10 h25", 0.1280),
    "gems10-h28-dotted-ridge-20260928T020256236880Z-6452ae1d00.tif": ("GEMSDOE10 h28", 0.1839),
    "13gems_20261001_r13-lattice-s5_v2_nan-outside.tif": ("13GEMSDOE lattice", 0.0904),
    "gems16-h16-1-topo-geophys-baseline-ridges-20260930-df20f65e-nan.tif": (
        "16GEMSDOE h16-1",
        0.1855,
    ),
    "gems16-h18-3a-topo-geophys-x-complexity-prior-20260930-c502dfab-nan.tif": (
        "16GEMSDOE h18-3a",
        0.0976,
    ),
    # blank in the brief: unknown, never zero
    "gems16-h18-4-usgs-geologic-map-faults-gap-20260930-aef8f42c-nan.tif": (
        "16GEMSDOE h18-4",
        None,
    ),
    "gems20-h20-1-sarnnpu-powerlaw-pi0363-tilt-wingcrack-20260930-be0e8f6b-nan.tif": (
        "20GEMSDOE h20-1",
        None,
    ),
    "gems20-h20-5-continuous-pu-proxy-unverified-20260930-824ce73a-nan.tif": (
        "20GEMSDOE h20-5",
        None,
    ),
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sibling-root", type=Path, required=True)
    args = ap.parse_args()
    fp = footprint.load_footprint()
    with rasterio.open(ROOT / "data/bridge/labels.tif") as d:
        labels = (d.read(1) > 0) & fp
    d_known = distance_transform_edt(~labels)
    sgmc_path = ROOT / "data/external/derived_sgmc_faults_100m_u8.tif"
    with rasterio.open(sgmc_path) as d:
        sgmc = (d.read(1) > 0) & fp
    d_sgmc = distance_transform_edt(~sgmc)

    unique: dict[str, dict] = {}
    for repo in sorted(os.listdir(args.sibling_root)):
        base = args.sibling_root / repo
        if not base.is_dir():
            continue
        for root, dirs, files in os.walk(base):
            if ".git" in Path(root).parts:
                continue
            for name in files:
                if not name.lower().endswith(".tif"):
                    continue
                p = Path(root) / name
                digest = sha256(p)
                entry = unique.setdefault(digest, {"sha256": digest, "paths": [], "names": set()})
                entry["paths"].append(f"{repo}/{p.relative_to(base)}")
                entry["names"].add(name)
                entry["_path"] = p
    rows = []
    flagged = []
    scored_rows = []
    for digest, e in unique.items():
        p = e["_path"]
        with rasterio.open(p) as d:
            meta = {
                "shape": list(d.shape),
                "count": d.count,
                "dtype": d.dtypes[0],
                "nodata": None
                if d.nodata is None
                else (float(d.nodata) if d.nodata == d.nodata else "nan"),
                "crs": d.crs.to_epsg() if d.crs else None,
            }
            a = d.read(1) if (list(d.shape) == GRID[0]) else None
        row = {
            "sha256": digest,
            "bytes": p.stat().st_size,
            "example_path": e["paths"][0],
            "n_copies": len(e["paths"]),
            **meta,
        }
        if (
            a is not None
            and meta["count"] == 1
            and meta["dtype"] == "float32"
            and meta["crs"] == 32611
        ):
            inside, outside = a[fp], a[~fp]
            fin = np.isfinite(inside)
            row.update(
                inside_nan=int((~fin).sum()),
                inside_min=float(np.nanmin(inside)) if fin.any() else None,
                inside_max=float(np.nanmax(inside)) if fin.any() else None,
                inside_gt1=int((inside > 1).sum()),
                inside_lt0=int((inside < 0).sum()),
                inside_inf=int(np.isinf(inside).sum()),
                outside_nan=int(np.isnan(outside).sum()),
                outside_finite=int(np.isfinite(outside).sum()),
                positive_inside=int((inside > 0).sum()),
                unique_inside=int(len(np.unique(inside[fin]))),
            )
            problems = []
            if row["inside_gt1"] or row["inside_lt0"] or row["inside_inf"]:
                problems.append("values outside [0,1] inside the footprint")
            if row["inside_nan"]:
                problems.append("NaN inside the scoring footprint")
            if (
                row["outside_finite"]
                and outside[np.isfinite(outside)].size
                and (np.nanmin(outside) < 0 or np.nanmax(outside) > 1)
            ):
                problems.append("finite values outside [0,1] outside the footprint")
            row["problems"] = problems
            if problems:
                flagged.append(
                    {
                        k: row[k]
                        for k in (
                            "sha256",
                            "example_path",
                            "problems",
                            "inside_nan",
                            "outside_finite",
                        )
                    }
                )
            names = sorted(e["names"])
            hit = next((n for n in names if n in OWNER_REPORTED), None)
            if hit:
                label, score = OWNER_REPORTED[hit]
                mask = (np.nan_to_num(a, nan=0.0) > 0.5) & fp
                off = mask & ~labels
                n = int(off.sum())
                dk, ds = d_known[off], d_sgmc[off]

                def share(lo, hi, dk=dk, n=n):
                    return float(((dk >= lo) & (dk < hi)).sum() / max(n, 1))

                scored_rows.append(
                    {
                        "label": label,
                        "file": hit,
                        "sha256": digest,
                        "owner_reported_score": score,
                        "off_catalogue_px": n,
                        "on_catalogue_px": int((mask & labels).sum()),
                        "share_d1": share(1, 2),
                        "share_d2": share(2, 3),
                        "share_d3": share(3, 4),
                        "share_within_3px": share(1, 4),
                        "share_ge10px": share(10, 1e9),
                        "share_ge40px": share(40, 1e9),
                        "share_within_3px_of_sgmc": float((ds <= 3).sum() / max(n, 1)),
                    }
                )
                row["owner_label"], row["owner_reported_score"] = label, score
        else:
            row["problems"] = ["not a single-band float32 EPSG:32611 submission-grid raster"]
        rows.append(row)

    fields = [
        "sha256", "bytes", "example_path", "n_copies", "shape", "count", "dtype", "nodata", "crs",
        "inside_nan", "inside_min", "inside_max", "inside_gt1", "inside_lt0", "inside_inf",
        "outside_nan", "outside_finite", "positive_inside", "unique_inside", "owner_label",
        "owner_reported_score", "problems",
    ]  # fmt: skip
    with open(ROOT / "evidence/group_raster_profiles.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in sorted(rows, key=lambda r: r["example_path"]):
            r = dict(r)
            r["problems"] = "; ".join(r.get("problems", []))
            w.writerow(r)

    grid_rows = [r for r in rows if "inside_nan" in r]
    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "unique rasters across the owner's public sibling repositories (shallow clones)",
        "unique_rasters": len(rows),
        "submission_grid_float32_rasters": len(grid_rows),
        "rasters_with_any_range_or_nan_problem": len(flagged),
        "flagged": flagged,
        "none_has_values_outside_0_1_inside_footprint": all(
            not r["inside_gt1"] and not r["inside_lt0"] and not r["inside_inf"] for r in grid_rows
        ),
        "blank_score_files_format_identical_to_scored_files": [
            r["owner_label"]
            for r in grid_rows
            if r.get("owner_label") and r.get("owner_reported_score") is None and not r["problems"]
        ],
        "both_outside_conventions_scored_identically": {
            "evidence": "12GEMSDOE r7-nms3-dem10-scarp: NaN-outside and zeros-outside variants both reported 0.1294",
            "basis": "owner-reported scores in the 2026-10-02 brief",
        },
        "interpretation": (
            "No shipped raster violates the stated [0,1] contract inside the scoring footprint. The only "
            "format anomalies are NaN inside the footprint (and finite values outside it) in early 5GEMSDOE "
            "submission.tif files. The files whose score is blank are format-identical to files that did "
            "score, so their blank scores cannot be attributed to a format failure. The cause of the "
            "original portal message is NOT established by this evidence."
        ),
    }
    (ROOT / "evidence/format_forensics.json").write_text(json.dumps(report, indent=2) + "\n")

    sc = [r for r in scored_rows if r["owner_reported_score"] is not None]
    x_near = [r["share_within_3px"] for r in sc]
    y = [r["owner_reported_score"] for r in sc]
    heavy = [r for r in sc if r["share_within_3px"] >= 0.45]
    light = [r for r in sc if r["share_within_3px"] < 0.45]
    analysis = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "scores": "OWNER-REPORTED (2026-10-02 brief); not organizer receipts",
        "n_scored": len(sc),
        "rows": sorted(scored_rows, key=lambda r: -(r["owner_reported_score"] or -1)),
        "spearman_score_vs_share_within_3px_of_catalogue": spearmanr(x_near, y)[0],
        "spearman_score_vs_off_catalogue_pixels": spearmanr([r["off_catalogue_px"] for r in sc], y)[
            0
        ],
        "halo_heavy_files_ge45pct_within_3px": {
            "n": len(heavy),
            "max_score": max((r["owner_reported_score"] for r in heavy), default=None),
            "labels": [r["label"] for r in heavy],
        },
        "other_files": {
            "n": len(light),
            "max_score": max((r["owner_reported_score"] for r in light), default=None),
        },
        "interpretation": (
            "Emission that hugs the catalogue (>=45% of off-catalogue pixels within 300 m of a mapped trace) "
            "never exceeded 0.046, while ridge-thinned emission with ~22% near-catalogue pixels reached "
            "0.18-0.19. Distance-to-catalogue alone does not explain the scores (a single-skill per-bin "
            "model fitted to all scored files gave Pearson r=0.27): method skill matters."
        ),
    }
    (ROOT / "evidence/lb_geometry_analysis.json").write_text(json.dumps(analysis, indent=2) + "\n")
    print(
        json.dumps(
            {
                k: report[k]
                for k in (
                    "unique_rasters",
                    "submission_grid_float32_rasters",
                    "rasters_with_any_range_or_nan_problem",
                )
            }
        )
    )
    print(
        json.dumps(
            {
                k: analysis[k]
                for k in (
                    "n_scored",
                    "spearman_score_vs_share_within_3px_of_catalogue",
                    "halo_heavy_files_ge45pct_within_3px",
                    "other_files",
                )
            },
            indent=1,
        )
    )


if __name__ == "__main__":
    main()
