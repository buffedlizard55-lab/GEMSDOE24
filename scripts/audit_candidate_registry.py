#!/usr/bin/env python3
"""Compare one candidate GeoTIFF against every local registry-like binary raster.

Registry set = docs/downloads/*.tif + inputs/**/*.tif + data/research/nine_site/*.tif.
Reports, per file: share of candidate dots within 3 px of that file's dots, and
Pearson correlation on the footprint. Writes JSON evidence; never a score.
Usage: python scripts/audit_candidate_registry.py CANDIDATE.tif --out evidence/x.json
"""

from __future__ import annotations

import argparse
import glob
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


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("candidate", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--top", type=int, default=12)
    args = ap.parse_args()
    with rasterio.open(TEMPLATE) as t:
        fp = np.isfinite(t.read(1))
    with rasterio.open(args.candidate) as c:
        cv = c.read(1).astype(np.float64)
    cd = fp & (cv > 0)
    n = int(cd.sum())
    files = sorted(
        {
            *glob.glob(str(ROOT / "docs/downloads/*.tif")),
            *glob.glob(str(ROOT / "inputs/**/*.tif"), recursive=True),
            *glob.glob(str(ROOT / "data/research/nine_site/*.tif")),
        }
    )
    cand_sha = sha256_file(args.candidate)
    rows, skipped = [], []
    for f in files:
        if sha256_file(Path(f)) == cand_sha:
            skipped.append({"file": str(Path(f).relative_to(ROOT)), "reason": "self (same bytes)"})
            continue
        with rasterio.open(f) as ds:
            if ds.shape != fp.shape:
                skipped.append({"file": str(Path(f).relative_to(ROOT)), "reason": "shape"})
                continue
            a = ds.read(1).astype(np.float64)
        a = np.where(np.isfinite(a), a, 0.0)
        bd = fp & (a > 0)
        if not bd.any():
            skipped.append({"file": str(Path(f).relative_to(ROOT)), "reason": "no dots"})
            continue
        d = distance_transform_edt(~bd)
        ov = float(((d <= 3.0) & cd).sum() / n)
        rho = float(np.corrcoef(cv[fp], a[fp])[0, 1]) if a[fp].std() > 0 else 0.0
        rows.append(
            {
                "file": str(Path(f).relative_to(ROOT)),
                "sha256": sha256_file(Path(f)),
                "dots": int(bd.sum()),
                "overlap_candidate_within_3px": round(ov, 6),
                "pearson_on_footprint": round(rho, 6),
            }
        )
    rows.sort(key=lambda r: -r["overlap_candidate_within_3px"])
    out = {
        "candidate": str(args.candidate.relative_to(ROOT))
        if args.candidate.is_absolute()
        else str(args.candidate),
        "candidate_sha256": sha256_file(args.candidate),
        "candidate_dots": n,
        "files_compared": len(rows),
        "skipped": skipped,
        "max_overlap": rows[0]["overlap_candidate_within_3px"] if rows else None,
        "max_abs_pearson": max((abs(r["pearson_on_footprint"]) for r in rows), default=None),
        "threshold_overlap": 0.70,
        "threshold_pearson": 0.90,
        "top": rows[: args.top],
        "all": rows,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=2, allow_nan=False) + "\n")
    print(json.dumps({k: out[k] for k in ("files_compared", "max_overlap", "max_abs_pearson")}))
    for r in rows[:5]:
        print(r["overlap_candidate_within_3px"], r["file"])


if __name__ == "__main__":
    main()
