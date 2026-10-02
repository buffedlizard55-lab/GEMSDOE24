#!/usr/bin/env python3
"""Anonymous Census roads acquisition with an independently buffered source window.

Unlike the inherited clipped-road mirror, this selects whole official county
files for a buffered geographic box. Raw ZIPs stay external/ignored; only a small
100 m nearest-road raster and full source receipts are exported by the workflow.
TLS verification is never disabled. Missing county downloads fail the derivation.
"""

from __future__ import annotations

import hashlib
import io
import json
import time
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
import shapefile
from pyproj import CRS, Transformer
from rasterio.features import rasterize
from scipy.ndimage import distance_transform_edt
from shapely.geometry import mapping, shape
from shapely.ops import transform

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/external/audit_sources"
BOX = (-120.5, 37.0, -115.9, 41.0)
PAD = 200
TF = rasterio.transform.Affine(100, 0, 243350, 0, -100, 4508550)
BASE = "https://www2.census.gov/geo/tiger/TIGER2024"


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "GEMS-reproducible-source-audit/2.0"})
    last_error = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                if r.status != 200:
                    raise ValueError(f"Census HTTP {r.status}")
                b = r.read()
            return b, {"url": url, "bytes": len(b), "sha256": hashlib.sha256(b).hexdigest()}
        except Exception as exc:  # retain TLS verification; retry transient transport failures
            last_error = f"{type(exc).__name__}: {exc}"
            if attempt < 2:
                time.sleep(2**attempt)
    failure = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "url": url,
        "attempts": 3,
        "tls_verification_disabled": False,
        "error": last_error,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "tiger_road_fetch_failure.json").write_text(json.dumps(failure, indent=2) + "\n")
    print(json.dumps(failure), flush=True)
    raise RuntimeError(
        f"Official Census download failed after 3 verified-TLS attempts: {last_error}"
    )


def reader(raw):
    z = zipfile.ZipFile(io.BytesIO(raw))
    stem = next(p[:-4] for p in z.namelist() if p.endswith(".shp"))
    r = shapefile.Reader(
        shp=io.BytesIO(z.read(stem + ".shp")),
        shx=io.BytesIO(z.read(stem + ".shx")),
        dbf=io.BytesIO(z.read(stem + ".dbf")),
    )
    return r, CRS.from_wkt(z.read(stem + ".prj").decode())


def intersects(b):
    return b[0] <= BOX[2] and b[2] >= BOX[0] and b[1] <= BOX[3] and b[3] >= BOX[1]


def _main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "tiger_road_fetch_failure.json").unlink(missing_ok=True)
    raw, county_receipt = fetch(BASE + "/COUNTY/tl_2024_us_county.zip")
    r, crs = reader(raw)
    if not crs.equals(CRS.from_epsg(4269)):
        raise SystemExit("Unexpected Census county CRS; no silent assumption")
    fields = [f[0] for f in r.fields[1:]]
    fips = sorted(
        {
            str(dict(zip(fields, sr.record))["GEOID"])
            for sr in r.iterShapeRecords()
            if intersects(sr.shape.bbox)
        }
    )
    seeds = np.zeros((3730 + 2 * PAD, 3292 + 2 * PAD), np.uint8)
    burn_tf = TF @ rasterio.transform.Affine.translation(-PAD, -PAD)
    receipt = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "source_bbox_wgs84": BOX,
        "source_window_verified": True,
        "seed_grid_buffer_m": 20000,
        "counties": fips,
        "county_download": county_receipt,
        "assets": [],
        "geometry_counts": {},
        "mtfcc_counts": {},
    }

    def county(code):
        return code, fetch(BASE + f"/ROADS/tl_2024_{code}_roads.zip")

    from collections import Counter

    counts = Counter()
    with ThreadPoolExecutor(max_workers=4) as ex:
        for code, (raw, entry) in ex.map(county, fips):
            rr, source_crs = reader(raw)
            projector = Transformer.from_crs(source_crs, 32611, always_xy=True)
            fields = [f[0] for f in rr.fields[1:]]
            batch = []
            accepted = 0
            for sr in rr.iterShapeRecords():
                if not intersects(sr.shape.bbox):
                    continue
                attrs = dict(zip(fields, sr.record))
                mtfcc = str(attrs.get("MTFCC", ""))
                if not mtfcc.startswith("S"):
                    continue
                counts[mtfcc] += 1
                geom = mapping(transform(projector.transform, shape(sr.shape.__geo_interface__)))
                batch.append((geom, 1))
                accepted += 1
                if len(batch) == 1000:
                    seeds |= rasterize(
                        batch,
                        out_shape=seeds.shape,
                        transform=burn_tf,
                        dtype="uint8",
                        all_touched=True,
                    )
                    batch = []
            if batch:
                seeds |= rasterize(
                    batch, out_shape=seeds.shape, transform=burn_tf, dtype="uint8", all_touched=True
                )
            entry["county"] = code
            entry["source_crs"] = source_crs.to_string()
            receipt["assets"].append(entry)
            receipt["geometry_counts"][code] = accepted
            print(code, accepted, flush=True)
    if not seeds.any():
        raise SystemExit("No official road geometry")
    d = (distance_transform_edt(seeds == 0) * 100)[PAD:-PAD, PAD:-PAD].astype(np.float32)
    with rasterio.open(ROOT / "data/bridge/sample_submission.tif") as t:
        fp = np.isfinite(t.read(1))
        profile = t.profile.copy()
    if not np.isfinite(d[fp]).all() or d[fp].max() >= PAD * 100:
        raise SystemExit("Road source buffer too short for the footprint")
    d[~fp] = np.nan
    profile.update(dtype="float32", count=1, nodata=np.nan, compress="deflate", predictor=3)
    dst = OUT / "tiger_road_distance_m.tif"
    with rasterio.open(dst, "w", **profile) as s:
        s.write(d, 1)
    receipt.update(
        file=str(dst.relative_to(ROOT)),
        sha256=hashlib.sha256(dst.read_bytes()).hexdigest(),
        mtfcc_counts=dict(counts),
        seed_pixels=int(seeds.sum()),
        complete_county_check=True,
        limitation="Nearest Census road/vehicular-trail segment on a 100 m raster; not a complete pedestrian-path or travel-time model",
    )
    (OUT / "tiger_road_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({k: v for k, v in receipt.items() if k not in ("assets",)}, indent=2))


def main():
    try:
        _main()
    except BaseException as exc:
        OUT.mkdir(parents=True, exist_ok=True)
        failure = {
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "stage": "unhandled_source_or_derivation_error",
            "exception_type": type(exc).__name__,
            "error": str(exc)[:1000],
            "tls_verification_disabled": False,
        }
        (OUT / "tiger_road_failure.json").write_text(json.dumps(failure, indent=2) + "\n")
        print(json.dumps(failure), flush=True)
        raise


if __name__ == "__main__":
    main()
