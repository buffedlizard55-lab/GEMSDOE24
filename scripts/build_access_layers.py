#!/usr/bin/env python
"""Build the two OPTIONAL accessibility confounds the audit asked for:

  data/confounds/d_road_px.tif    distance (100 m cells) to the nearest TIGER
                                  road/trail segment
  data/confounds/d_claim_px.tif  distance to the nearest USGS MRDS record

Sources: the CI-as-proxy fetcher's ``public-layers`` branch (data_external/):
Census TIGER2024 ROADS county files clipped to the GeoDAWN bbox, and
https://mrdata.usgs.gov/mrds/mrds-csv.zip (public domain, USGS). Reprojection
UTM 11N via pyproj. Distances are exact to ~half a cell; adequate for a
distribution-shift audit (we test ordering, not metric accuracy).
"""
from __future__ import annotations

import csv
import io
import json
import sys
import zipfile
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems import confounds as cf, footprint, paths  # noqa: E402
from pyproj import Transformer  # noqa: E402

EXT = ROOT / "data_external"
OUT = paths.DATA_DIR / "confounds"


def _rasterize_points(pts_ll: np.ndarray) -> np.ndarray:
    """pts_ll: (N,2) lon/lat WGS84 -> boolean seed grid on the footprint."""
    tr11 = Transformer.from_crs("EPSG:4326", "EPSG:32611", always_xy=True)
    x, y = tr11.transform(pts_ll[:, 0], pts_ll[:, 1])
    row, col = cf._utm_to_grid(x, y)
    fp = footprint.load_footprint()
    H, W = fp.shape
    ok = (row >= 0) & (row < H) & (col >= 0) & (col < W)
    seeds = np.zeros((H, W), bool)
    seeds[row[ok], col[ok]] = True
    seeds &= fp
    return seeds


def _densify_ll(geom: dict, step_deg: float = 0.0009) -> list[tuple[float, float]]:
    """Sample lon/lat points along (Multi)LineString/MultiPolygon geometry."""
    out: list[tuple[float, float]] = []

    def line(coords):
        for (x0, y0), (x1, y1) in zip(coords, coords[1:]):
            n = max(int(np.hypot(x1 - x0, y1 - y0) / step_deg), 1)
            for t in np.linspace(0, 1, n + 1):
                out.append((x0 + t * (x1 - x0), y0 + t * (y1 - y0)))

    if geom["type"] == "LineString":
        line(geom["coordinates"])
    elif geom["type"] == "MultiLineString":
        for g in geom["coordinates"]:
            line(g)
    elif geom["type"] == "Polygon":
        for ring in geom["coordinates"]:
            line(ring)
    elif geom["type"] == "MultiPolygon":
        for poly in geom["coordinates"]:
            for ring in poly:
                line(ring)
    elif geom["type"] == "Point":
        out.append(tuple(geom["coordinates"][:2]))
    return out


def build_roads() -> dict:
    feats = []
    for p in sorted(EXT.glob("tiger_ROADS_*_clipped.geojson")):
        feats.extend(json.loads(p.read_text())["features"])
    pts = []
    for f in feats:
        for x, y in _densify_ll(f["geom"]):
            pts.append((x, y))
    pts_a = np.asarray(pts, dtype=np.float64)
    m = (pts_a[:, 0] > -121.5) & (pts_a[:, 0] < -114.5) & (pts_a[:, 1] > 36.0) & (pts_a[:, 1] < 42.0)
    seeds = _rasterize_points(pts_a[m])
    from scipy.ndimage import distance_transform_edt

    d = distance_transform_edt(~seeds).astype(np.float32)
    fp = footprint.load_footprint()
    d = np.where(fp, d, np.nan).astype(np.float32)
    p = OUT / "d_road_px.tif"
    prof = dict(driver="GTiff", width=d.shape[1], height=d.shape[0], count=1, dtype="float32",
                crs=footprint.CRS, transform=footprint.TRANSFORM, compress="zstd", nodata=np.nan)
    with rasterio.open(p, "w", **prof) as dst:
        dst.write(d, 1)
    return {"file": str(p), "n_source_features": len(feats), "n_seed_px": int(seeds.sum()),
             "min": float(np.nanmin(d)), "max": float(np.nanmax(d)), "mean": round(float(np.nanmean(d)), 3)}


def build_claims() -> dict:
    src = None
    for cand in ("mrds_mrds_csv.zip", "mrds_mrds-csv_zip", "mrds_mrds-csv.zip"):
        if (EXT / cand).exists():
            src = EXT / cand
            break
    if src is None:
        return {"skipped": "mrds zip not fetched"}
    pts = []
    with zipfile.ZipFile(src) as z:
        name = next(n for n in z.namelist() if n.endswith(".csv"))
        with z.open(name) as f:
            rd = csv.DictReader(io.TextIOWrapper(f, encoding="latin-1", newline=""))
            for rec in rd:
                st = (rec.get("state") or "").strip().upper()
                if st not in ("NV", "CA", "NEVADA", "CALIFORNIA"):
                    continue
                try:
                    lat, lon = float(rec["latitude"]), float(rec["longitude"])
                except (TypeError, ValueError, KeyError):
                    continue
                if -121.5 < lon < -114.5 and 36.0 < lat < 42.0:
                    pts.append((lon, lat))
    pts_a = np.asarray(pts, dtype=np.float64)
    seeds = _rasterize_points(pts_a)
    from scipy.ndimage import distance_transform_edt

    d = distance_transform_edt(~seeds).astype(np.float32)
    fp = footprint.load_footprint()
    d = np.where(fp, d, np.nan).astype(np.float32)
    p = OUT / "d_claim_px.tif"
    prof = dict(driver="GTiff", width=d.shape[1], height=d.shape[0], count=1, dtype="float32",
                crs=footprint.CRS, transform=footprint.TRANSFORM, compress="zstd", nodata=np.nan)
    with rasterio.open(p, "w", **prof) as dst:
        dst.write(d, 1)
    return {"file": str(p), "n_records_in_window": len(pts_a), "n_seed_px": int(seeds.sum()),
            "min": float(np.nanmin(d)), "max": float(np.nanmax(d)), "mean": round(float(np.nanmean(d)), 3)}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rep = {"roads": build_roads(), "claims": build_claims()}
    (OUT / "access_layers.json").write_text(json.dumps(rep, indent=2))
    print(json.dumps(rep, indent=2))
    print("now re-run: python scripts/build_confounds.py --force  (confounds.npz picks up d_road_px/d_claim_px)")


if __name__ == "__main__":
    main()
