#!/usr/bin/env python3
"""Recompute the nine-site uniqueness matrix and candidate checks; write evidence JSON.

Inputs (all hash-checked):
  data/research/nine_site/   nine focus-site champions fetched at pinned commits
                             (run: python scripts/fetch_nine_site_champions.py)
  docs/downloads/gems24-nine-complement-seghgb-20261029-zeros.tif   candidate

Writes evidence/nine_site_overlap_20261029.json. Never writes a leaderboard estimate.
Overlap definition (protocol): share of A's dots within 3 px of B's dots.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems.validator import sha256_file  # noqa: E402

TEMPLATE = ROOT / "data/bridge/sample_submission.tif"
RECEIPT = ROOT / "data/research/nine_site/fetch_receipt.json"
CANDIDATE = ROOT / "docs/downloads/gems24-nine-complement-seghgb-20261029-zeros.tif"
OUT = ROOT / "evidence/nine_site_overlap_20261029.json"
RADIUS = 3.0


def dots_of(path, fp):
    with rasterio.open(path) as ds:
        a = ds.read(1)
        grid_ok = (
            ds.crs.to_epsg() == 32611
            and ds.shape == fp.shape
            and ds.transform == TEMPLATE_TRANSFORM
        )
        values = a.astype(np.float64)
    return fp & (values > 0), grid_ok, values


with rasterio.open(TEMPLATE) as t:
    TEMPLATE_TRANSFORM = t.transform
    FP = np.isfinite(t.read(1))


def main() -> None:
    rows = json.loads(RECEIPT.read_text())
    sites, dots, info = [], {}, {}
    for r in rows:
        if sha256_file(Path(r["local"])) != r["sha256_expected"]:
            raise SystemExit(f"Hash mismatch for {r['site']}; refusing to analyse")
        d, grid_ok, values = dots_of(r["local"], FP)
        inside = values[FP]
        if not np.isfinite(inside).all() or not np.isin(inside, [0, 1]).all():
            raise SystemExit(f"{r['site']} is not finite binary inside the footprint")
        sites.append(r["site"])
        dots[r["site"]] = d
        info[r["site"]] = {
            "file": r["file"],
            "sha256": r["sha256_expected"],
            "url": r["url"],
            "dots": int(d.sum()),
            "grid_ok": bool(grid_ok),
            "outside_footprint_values": sorted({float(x) for x in np.unique(values[~FP])})[:3],
        }

    dist = {s: distance_transform_edt(~dots[s]) for s in sites}
    matrix = {
        a: {b: float(((dist[b] <= RADIUS) & dots[a]).sum() / dots[a].sum()) for b in sites}
        for a in sites
    }
    max_other = {a: max(v for b, v in matrix[a].items() if b != a) for a in sites}
    union = np.zeros(FP.shape, bool)
    for s in sites:
        union |= dots[s]
    near_union = (distance_transform_edt(~union) <= RADIUS) & FP
    coverage = float(near_union.sum() / FP.sum())

    cand_dots, cand_grid_ok, cand_values = dots_of(CANDIDATE, FP)
    cand_inside = cand_values[FP]
    cand = {
        "file": CANDIDATE.name,
        "sha256": sha256_file(CANDIDATE),
        "dots": int(cand_dots.sum()),
        "grid_ok": bool(cand_grid_ok),
        "strict_whole_array_0_1": bool(np.all((cand_values >= 0) & (cand_values <= 1))),
        "nan_inside_footprint": int(np.isnan(cand_inside).sum()),
        "overlap_vs_nine_max": None,
        "overlap_vs_nine": {},
        "pearson_vs_nine_max": None,
    }
    cd = cand_dots
    for s in sites:
        cand["overlap_vs_nine"][s] = float(((dist[s] <= RADIUS) & cd).sum() / cd.sum())
    cand["overlap_vs_nine_max"] = max(cand["overlap_vs_nine"].values())
    cand["pearson_vs_nine_max"] = max(
        float(np.corrcoef(cand_values[FP], np.where(dots[s][FP], 1.0, 0.0))[0, 1]) for s in sites
    )

    out = {
        "generated_by": "scripts/build_nine_site_summary.py",
        "overlap_definition": "share of row-site dots within 3 px of column-site dots",
        "footprint_px": int(FP.sum()),
        "nine_site_matrix_row_to_col": matrix,
        "max_overlap_with_any_other_focus_site": max_other,
        "nine_union_within_3px_of_footprint": round(coverage, 4),
        "champions": info,
        "candidate": cand,
        "uniqueness_rule_user_threshold": 0.70,
        "unique_vs_nine_sites": bool(cand["overlap_vs_nine_max"] <= 0.70),
        "note": "Overlap is geometry only; it is not a score and not proof of copying.",
    }
    OUT.write_text(json.dumps(out, indent=2, allow_nan=False) + "\n")
    print(json.dumps({k: out[k] for k in ("max_overlap_with_any_other_focus_site",)}, indent=1))
    print("candidate overlap vs nine (max):", round(cand["overlap_vs_nine_max"], 6))
    print("candidate pearson vs nine (max):", round(cand["pearson_vs_nine_max"], 6))
    print("unique_vs_nine_sites:", out["unique_vs_nine_sites"])


if __name__ == "__main__":
    main()
