#!/usr/bin/env python3
"""Shared CLI for the existing strict writer; never authorizes a weekly slot."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems.submission import _same_file, check_variants, write_submission  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("prediction", type=Path, help="2D .npy or aligned single-band .tif")
    ap.add_argument("output", type=Path)
    ap.add_argument("--template", type=Path, default=ROOT / "data/bridge/sample_submission.tif")
    ap.add_argument(
        "--outside",
        choices=("nan", "zero"),
        default="zero",
        help="exterior encoding; zero tests strict all-finite validation and does not authorize upload",
    )
    args = ap.parse_args()
    if _same_file(args.output, args.prediction):
        raise SystemExit("Output must not overwrite the prediction input")
    if _same_file(args.output, args.template):
        raise SystemExit("Output must not overwrite the template")
    if args.prediction.suffix == ".npy":
        a = np.load(args.prediction, allow_pickle=False)
    else:
        with rasterio.open(args.prediction) as s, rasterio.open(args.template) as t:
            if (s.shape, s.crs, s.transform, s.count) != (t.shape, t.crs, t.transform, 1):
                raise SystemExit("Prediction must match the template grid and be single-band")
            a = s.read(1, masked=True)

    # Validate in a private directory on the destination filesystem before
    # replacing an existing output. A failed check must not leave a plausible
    # but invalid .tif at the requested path or destroy an earlier artifact.
    def reject_output_sidecars():
        for suffix in (".msk", ".aux.xml", ".ovr"):
            sidecar = Path(str(args.output) + suffix)
            if sidecar.exists() or sidecar.is_symlink():
                raise ValueError(f"Output has an existing external sidecar: {sidecar}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    reject_output_sidecars()
    with tempfile.TemporaryDirectory(prefix=".submission-", dir=args.output.parent) as temp_dir:
        p = write_submission(
            a, args.template, Path(temp_dir) / args.output.name, outside=args.outside
        )
        checks = check_variants(p, args.template, strict=True)
        if not checks["format_valid"]:
            print(json.dumps(checks, indent=2))
            raise SystemExit("Written file failed pinned-grid format validation")
        reject_output_sidecars()
        os.replace(p, args.output)
    # The validated bytes were atomically renamed; do not report a vanished
    # temporary pathname as the file's GDAL dependency.
    checks["checks"]["raster_self_contained"]["detail"] = f"files={[str(args.output)]}"
    print(json.dumps(checks, indent=2))


if __name__ == "__main__":
    main()
