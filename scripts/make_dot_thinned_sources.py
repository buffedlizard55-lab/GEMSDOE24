#!/usr/bin/env python3
"""Write the exact dot-thinned H19-5 source rasters that the promotion path re-derives.

Candidate = ``gems.thinning.dot_thin`` of the pinned H19-5 emission with catalogue pixels removed
(the scorer masks them). Reads no labels or scores. Deterministic. No slot is spent.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems import footprint, submission  # noqa: E402
from gems.thinning import dot_thin  # noqa: E402
from gems.validator import sha256_file  # noqa: E402

H19_5_SHA = "ec1f9b56b83ce33cad781ceb9f104b18fb4f2ff785263a4e89616af4aabdee8d"
TEMPLATE = ROOT / "data/bridge/sample_submission.tif"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--spacing", type=float, action="append", required=True)
    ap.add_argument("--out-dir", type=Path, default=ROOT / "out")
    args = ap.parse_args()
    ref = next((ROOT / "inputs").glob("*h19-5*-nan.tif"))
    if sha256_file(ref) != H19_5_SHA:
        raise SystemExit("Pinned H19-5 reference differs from its recorded SHA-256")
    fp = footprint.load_footprint()
    known = footprint.load_band(ROOT / "data/bridge/existing_faults.tif") > 0
    with rasterio.open(ref) as d:
        base = (d.read(1) > 0) & fp & ~known
    args.out_dir.mkdir(exist_ok=True)
    for d in args.spacing:
        thinned = dot_thin(base, d)
        path = args.out_dir / f"h25-1-dotthin-d{d:g}-h19-5.tif"
        submission.write_submission(thinned.astype(np.float32), TEMPLATE, path, outside="nan")
        print(path.name, int(thinned.sum()), f"{thinned.sum() / base.sum():.3f}", sha256_file(path))


if __name__ == "__main__":
    main()
