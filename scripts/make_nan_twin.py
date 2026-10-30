#!/usr/bin/env python3
"""Make the NaN-outside twin of a zeros-outside candidate (read-only on the source).

Same dots, same grid; only the cells outside the template footprint change from
finite 0.0 to NaN, matching data/bridge/sample_submission.tif and the official
text ("data outside bounds null or NaN"). Then runs verify_candidate_tif.py on it.
"""
import subprocess
import sys
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "data/bridge/sample_submission.tif"
SRC = ROOT / "docs/downloads/gems24-ns-ratio1-labelfree-ratio-20261030-b49138fa-zeros.tif"
DST = ROOT / "docs/downloads/gems24-ns-ratio1-labelfree-ratio-20261030-b49138fa-nan.tif"


def main() -> int:
    with rasterio.open(TEMPLATE) as t:
        fp = np.isfinite(t.read(1))
    with rasterio.open(SRC) as s:
        a = s.read(1).astype(np.float32)
        prof = s.profile.copy()
    if not np.isin(a[fp], (0.0, 1.0)).all():
        raise SystemExit("source has non-binary values inside footprint")
    out = a.copy()
    out[~fp] = np.float32("nan")
    prof.update(dtype="float32", count=1, nodata=None, compress="deflate")
    with rasterio.open(DST, "w", **prof) as d:
        d.write(out, 1)
    print("wrote", DST.relative_to(ROOT))
    print("dots in footprint:", int((out[fp] == 1).sum()))
    return subprocess.call([sys.executable, str(ROOT / "scripts/verify_candidate_tif.py"), str(DST.relative_to(ROOT))])


if __name__ == "__main__":
    raise SystemExit(main())
