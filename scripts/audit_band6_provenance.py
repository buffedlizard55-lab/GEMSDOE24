#!/usr/bin/env python3
"""Compare the owner-mirror band 6 to cached GeoDAWN radiometrics, without fitting.

This establishes correlation of the cached bytes, not official provenance,
physical units or the hidden-label utility of the channel.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy.stats import pearsonr, spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems.validator import sha256_file  # noqa: E402

TRAINING_SHA256 = "4371c82e3b8339b807bdffcf4ef59a225520fe2988d521be208ae33743123bc5"
SAMPLE_SIZE = 250_000
SEED = 20261027


def audit() -> dict:
    training = ROOT / "data/training_features.tif"
    raster = ROOT / "data/external/geodawn_rad_u8.tif"
    metadata_path = ROOT / "data/external/geodawn_rad.json"
    doc = (
        ROOT
        / "data/external/audit_sources/GeoDAWN_NV_WestCentral_Geophysical_2020_D21_Report.pdf.txt"
    )
    template = ROOT / "data/bridge/sample_submission.tif"
    metadata = json.loads(metadata_path.read_text())
    if sha256_file(training) != TRAINING_SHA256:
        raise ValueError("Training feature mirror is absent or differs from its pinned hash")
    if sha256_file(raster) != metadata["product_sha256"]:
        raise ValueError("Cached radiometric product differs from its metadata")
    members = [v["member"] for v in metadata["files"]["TC"]["sources"]]
    if metadata["channels"] != ["K", "Th", "U", "TC"] or not all("22103_tc_" in x for x in members):
        raise ValueError("Expected cached GeoDAWN radiometric metadata is missing")
    quote = "22103_tc.grd:  Total Count Grid in Geosoft Grid Format"
    if quote not in doc.read_text():
        raise ValueError(
            "The cached contractor report no longer contains the referenced description"
        )
    with rasterio.open(template) as t:
        footprint = np.isfinite(t.read(1))
        grid = (t.shape, t.crs, t.transform)
    with rasterio.open(training) as ds:
        if (ds.shape, ds.crs, ds.transform) != grid or ds.count < 6:
            raise ValueError("Feature mirror is not aligned to the sample grid")
        x = ds.read(6)
        nodata, band_tags = ds.nodata, ds.tags(6)
    with rasterio.open(raster) as ds:
        if (ds.shape, ds.crs, ds.transform) != grid or ds.count != 4:
            raise ValueError("Cached radiometric product is not aligned to the sample grid")
        rad = ds.read()
    valid = footprint & np.isfinite(x) & (x != nodata) & np.all(rad > 0, axis=0)
    ids = np.flatnonzero(valid.ravel())
    if len(ids) < SAMPLE_SIZE:
        raise ValueError("Insufficient joint valid support for the fixed sample")
    sample = np.random.default_rng(SEED).choice(ids, SAMPLE_SIZE, replace=False)
    x_sample = x.ravel()[sample].astype(np.float64)
    results = {}
    for i, name in enumerate(metadata["channels"]):
        y = rad[i].ravel()[sample].astype(np.float64)
        results[name] = {
            "pearson": float(pearsonr(x_sample, y).statistic),
            "spearman": float(spearmanr(x_sample, y).statistic),
        }
    return {
        "schema": "band6-provenance-audit-v1",
        "checked_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "Correlation of cached aligned bytes, not organizer authentication or a fault-score experiment",
        "training_file": "data/training_features.tif",
        "training_sha256": TRAINING_SHA256,
        "band": 6,
        "legacy_feature_alias": "bouguer_tc_mgal",
        "training_band_tags": band_tags,
        "radiometric_product": "data/external/geodawn_rad_u8.tif",
        "radiometric_sha256": metadata["product_sha256"],
        "radiometric_metadata_sha256": sha256_file(metadata_path),
        "radiometric_quantization": metadata["quantisation"],
        "cached_contractor_report_text_sha256": sha256_file(doc),
        "cached_report_quote": quote,
        "source_members_as_recorded": members,
        "source_link": "https://www.sciencebase.gov/catalog/item/657e1d85d34e23d3533209f7",
        "total_joint_valid_pixels": len(ids),
        "sample_size": SAMPLE_SIZE,
        "sample_seed": SEED,
        "sample_policy": "uniform without replacement from joint finite template, band-6 and all four nonzero u8 channels",
        "correlations": results,
        "interpretation": (
            "Band 6 is almost monotonically related to the cached u8 total-count product. "
            "This is strong evidence consistent with radiometric total count, not proof of "
            "the band source, units or the independent authenticity of either cache. The "
            "mirror tag instead says magnetic tilt/curvature; a positive numeric range "
            "cannot establish Bouguer terrain correction. The historic feature alias is "
            "preserved for reproducibility, not asserted as physical truth."
        ),
        "organizer_authentication": "not established",
        "new_experiments": 0,
        "competition_slots_used": 0,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, help="Optional JSON evidence path inside the workspace"
    )
    args = parser.parse_args()
    result = audit()
    text = json.dumps(result, indent=2, allow_nan=False) + "\n"
    if args.output:
        target = args.output.resolve()
        if not target.is_relative_to(ROOT / "evidence"):
            raise ValueError("Audit output must be inside evidence/")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
    print(text)


if __name__ == "__main__":
    main()
