#!/usr/bin/env python
"""Build the two OPTIONAL accessibility confounds the audit asked for:

  data/confounds/d_road_px.tif    distance (100 m cells) to the nearest TIGER
                                  road/trail segment
  data/confounds/d_claim_px.tif  distance to the nearest historic mining claim record
                                  (USGS MRDS)

Sources: the CI-as-proxy fetcher's ``public-layers`` branch (data_external/):
Census TIGER2024 ROADS county files clipped to the GeoDAWN bbox, and
https://mrdata.usgs.gov/mrds/mrds-csv.zip (public domain, USGS). Reprojection
UTM 11N via pyproj. Distances are exact to ~half a cell; adequate for a
distribution-shift audit (we test ordering, not metric accuracy).

Also builds d_wc_px / d_inf_px — distance to Well-Constrained vs
Inferred INGENIOUS Qfaults traces (server-native NAD83
Albers(-117) geometry from data_external/qfaults_v2_in_footprint.json).
"""
from __future__ import annotations

if __name__ == "__main__":
    raise SystemExit("Historical source only: this protocol is retired; see the root README")

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


def _save_dist(seeds: np.ndarray, key: str) -> dict:
    from scipy.ndimage import distance_transform_edt

    fp = footprint.load_footprint()
    d = distance_transform_edt(~seeds).astype(np.float32)
    d = np.where(fp, d, np.nan).astype(np.float32)
    p = OUT / f"{key}.tif"
    prof = dict(driver="GTiff", width=fp.shape[1], height=fp.shape[0], count=1, dtype="float32",
                crs=footprint.CRS, transform=footprint.TRANSFORM, compress="zstd", nodata=np.nan)
    with rasterio.open(p, "w", **prof) as dst:
        dst.write(d, 1)
    return {"file": str(p), "seed_px": int(seeds.sum()), "min": float(np.nanmin(d)),
            "max": round(float(np.nanmax(d)), 3), "mean_px": round(float(np.nanmean(d)), 2)}


def build_roads() -> dict:
    feats = []
    for f_ in sorted(EXT.glob("tiger_ROADS_*_clipped.geojson")):
        feats.extend(json.loads(f_.read_text())["features"])
    pts = []
    for f in feats:
        for x, y in _densify_ll(f["geom"]):
            pts.append((x, y))
    pts_a = np.asarray(pts, dtype=np.float64)
    m = (pts_a[:, 0] > -121.5) & (pts_a[:, 0] < -114.5) & (pts_a[:, 1] > 36.0) & (pts_a[:, 1] < 42.0)
    seeds = _rasterize_points(pts_a[m])
    out = _save_dist(seeds, "d_road_px")
    out["n_source_features"] = len(feats)
    return out


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
    out = _save_dist(seeds, "d_claim_px")
    out["n_records_in_window"] = int(len(pts_a))
    return out


def build_fault_confidence() -> dict:
    """Distance to Well-Constrained / Inferred+Moderate INGENIOUS Qfaults traces
    (NBMG ArcGIS REST, fetched via the public-layers CI branch; server-native
    NAD83 Albers(-117) geometry). These encode *mapping accessibility*:
    near-WC = the mappers could see it; far-WC/near-Inf = covered terrain where
    the catalogue thins out."""
    src = EXT / "qfaults_v2_in_footprint.json"
    if not src.exists():
        return {"skipped": "qfaults_v2_in_footprint.json not present"}
    d = json.loads(src.read_text())
    albers = "+proj=aea +lat_1=29.5 +lat_2=45.5 +lat_0=23 +lon_0=-117 +x_0=0 +y_0=0 +ellps=GRS80 +units=m +no_defs"
    t1 = Transformer.from_proj(albers, "EPSG:32611", always_xy=True)
    fp = footprint.load_footprint()
    H, W = fp.shape
    out = {}
    for cls, key in (("Well Constrained", "d_wc_px"), ("Inferred", "d_inf_px")):
        pts = []
        for f in d["features"]:
            ft = f["attributes"].get("FTYPE_")
            if ft != cls:
                continue
            for path_ in f["geometry"]["paths"]:
                for x, y in path_:
                    pts.append((x, y))
        a = np.asarray(pts, float)
        x, y = t1.transform(a[:, 0], a[:, 1])
        row, col = cf._utm_to_grid(x, y)
        ok = (row >= 0) & (row < H) & (col >= 0) & (col < W)
        seeds = np.zeros(fp.shape, bool)
        seeds[row[ok], col[ok]] = True
        seeds &= fp
        r = _save_dist(seeds, key)
        r["class"] = cls
        r["n_points"] = int(len(pts))
        out[key] = r
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rep = {"roads": build_roads(), "claims": build_claims(), "fault_confidence": build_fault_confidence()}
    (OUT / "access_layers.json").write_text(json.dumps(rep, indent=2))
    print(json.dumps(rep, indent=2))
    print("now re-run: python scripts/build_confounds.py --force  (confounds.npz picks up d_road_px/d_claim_px)")


if __name__ == "__main__":
    main()
