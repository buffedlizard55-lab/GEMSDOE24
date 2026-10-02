"""Strict non-geological nuisance inputs; missing sources never become proxies.

Allowed families: Census road/trail distance; BLM closed mining-claim distance;
official acquisition-block/Area membership. No wells, sinter, vents, probes,
fault-confidence distances or label-derived seam detection is permitted here.
TIGER S1400 is a road, S1500 a vehicular trail; rails are R codes, not roads.
Distance rasters are approximations on a 100 m grid, not survey-grade distances.
"""

from __future__ import annotations

import io
import json
import re
import zipfile
from collections import Counter
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

from . import footprint
from .paths import DATA_DIR, ROOT
from .validator import sha256_file

CONF = DATA_DIR / "access"


def distance_to_seeds(seeds: np.ndarray, fp: np.ndarray, *, padding: int = 0) -> np.ndarray:
    expected_shape = tuple(n + 2 * padding for n in fp.shape)
    if padding < 0 or seeds.shape != expected_shape or not seeds.any():
        raise ValueError("Missing/empty distance source; no implicit corner seed allowed")
    # Do not delete roads/claims outside the scoring footprint. They can be the
    # nearest source to a boundary pixel. The buffered vector window is retained.
    d = (distance_transform_edt(~seeds) * 100).astype(np.float32)
    if padding:
        d = d[padding:-padding, padding:-padding]
        if d[fp].max() >= padding * 100:
            raise ValueError("Buffered seed window too short for nearest-distance certification")
    d[~fp] = np.nan
    return d


def quality_code(value):
    match = re.match(r"^\s*(\d+(?:\.\d+)?)", str(value))
    return float(match.group(1)) if match else None


def esri_polygon(rings):
    """Preserve multiple clockwise shells and counterclockwise holes."""
    points = [p for ring in rings for p in ring]
    parts = np.cumsum([0] + [len(r) for r in rings[:-1]]).tolist()
    return shapefile.Shape(
        shapeType=shapefile.POLYGON, points=points, parts=parts
    ).__geo_interface__


def burn_distance(vectors, fp, padding=200):
    grid_shape = tuple(n + 2 * padding for n in fp.shape)
    tf = footprint.TRANSFORM * rasterio.transform.Affine.translation(-padding, -padding)
    seeds = rasterize(
        vectors, out_shape=grid_shape, transform=tf, all_touched=True, dtype="uint8"
    ).astype(bool)
    return distance_to_seeds(seeds, fp, padding=padding), int(seeds.sum())


def _outline(zpath: Path, fp: np.ndarray) -> np.ndarray:
    with zipfile.ZipFile(zpath) as z:
        stem = next(n[:-4] for n in z.namelist() if n.endswith(".shp"))
        reader = shapefile.Reader(
            shp=io.BytesIO(z.read(stem + ".shp")),
            shx=io.BytesIO(z.read(stem + ".shx")),
            dbf=io.BytesIO(z.read(stem + ".dbf")),
        )
        crs = CRS.from_wkt(z.read(stem + ".prj").decode())
        tf = Transformer.from_crs(crs, "EPSG:32611", always_xy=True)
        shapes = [
            (mapping(transform(tf.transform, shape(s.__geo_interface__))), 1)
            for s in reader.shapes()
        ]
    return rasterize(
        shapes, out_shape=fp.shape, transform=footprint.TRANSFORM, all_touched=False, dtype="uint8"
    ).astype(bool)


def acquisition_areas(fp: np.ndarray) -> np.ndarray:
    # Area 2 overlaps Area 1: the finer Area 1 survey must have explicit priority.
    a2 = _outline(DATA_DIR / "external/GeoDAWN_area2_outline.zip", fp)
    a1 = _outline(DATA_DIR / "external/GeoDAWN_area1_outline.zip", fp)
    out = np.zeros(fp.shape, np.uint8)
    out[a2 & fp] = 2
    out[a1 & fp] = 1
    return out


def build_all(out_dir: Path | None = None, *, force: bool = False) -> dict:
    out = out_dir or CONF
    out.mkdir(parents=True, exist_ok=True)
    if (out / "confounds.npz").exists() and not force:
        return json.loads((out / "provenance.json").read_text())
    fp = footprint.load_footprint()
    feats = {}
    prov = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "features": {},
        "missing_required": [],
        "excluded": [
            "MRDS (mineral occurrences, not claims)",
            "label geometry/FTYPE distances",
            "wells/probes/sinter/vents",
            "label-derived block seams",
        ],
    }
    road_files = sorted((DATA_DIR / "raw/access_mirrors").glob("tiger_ROADS_*_clipped.geojson"))
    road_bridge = DATA_DIR / "external/audit_sources/tiger_road_distance_m.tif"
    if road_bridge.exists():
        entry = json.loads((road_bridge.parent / "tiger_road_receipt.json").read_text())
        if (
            not entry.get("source_window_verified")
            or not entry.get("complete_county_check")
            or sha256_file(road_bridge) != entry.get("sha256")
        ):
            raise ValueError("Official road source window/completeness/integrity failed")
        with rasterio.open(road_bridge) as d:
            if (
                d.shape != fp.shape
                or d.crs is None
                or d.crs.to_epsg() != 32611
                or d.transform != footprint.TRANSFORM
            ):
                raise ValueError("Official road grid mismatch")
            a = d.read(1)
        if not np.isfinite(a[fp]).all() or np.any(a[fp] < 0):
            raise ValueError("Invalid official road distances")
        feats["road_m"] = a
        prov["features"]["road_m"] = entry
    elif road_files:
        tf = Transformer.from_crs("EPSG:4269", "EPSG:32611", always_xy=True)
        vectors, codes = [], Counter()
        for p in road_files:
            d = json.loads(p.read_text())
            for f in d["features"]:
                code = str(f["props"].get("MTFCC", ""))
                codes[code] += 1
                # Only road/trail codes. Do not conflate rail accessibility.
                if not code.startswith("S"):
                    continue
                vectors.append((mapping(transform(tf.transform, shape(f["geom"]))), 1))
        feats["road_m"], seed_count = burn_distance(vectors, fp)
        prov["features"]["road_m"] = {
            "source_window_verified": False,
            "mirror_clip_box_wgs84": [-120.0024, 37.3641, -116.1415, 40.7247],
            "source": "Census TIGER/Line 2024 ROADS, NAD83",
            "url": "https://www2.census.gov/geo/tiger/TIGER2024/ROADS/",
            "n_geometries": len(vectors),
            "mtfcc_counts": dict(codes),
            "seed_pixels": seed_count,
            "seed_grid_buffer_m": 20000,
            "files": {p.name: sha256_file(p) for p in road_files},
            "limitations": "Census roads/vehicular and available pedestrian trails; not a complete hiking-trail inventory. 100 m rasterization.",
        }
        prov["missing_required"].append(
            "buffered nearest-road coverage (legacy mirror was clipped tightly)"
        )
    else:
        prov["missing_required"].append("road/trail vector distances")
    claims = DATA_DIR / "raw/official_audit/blm_closed_claims.json"
    bridge = DATA_DIR / "external/audit_sources/blm_closed_claim_distance_m.tif"
    if bridge.exists():
        receipt = json.loads((bridge.parent / "receipt.json").read_text())
        entry = receipt.get("claim_distance", {})
        if (
            not entry.get("complete_id_check")
            or not entry.get("quality_policy")
            or entry.get("seed_grid_buffer_m", 0) < 20000
            or sha256_file(bridge) != entry.get("sha256")
        ):
            raise ValueError("Incomplete/unstable claim bridge or unverified quality/buffer policy")
        with rasterio.open(bridge) as d:
            if (
                d.shape != fp.shape
                or d.crs.to_epsg() != 32611
                or d.transform != footprint.TRANSFORM
            ):
                raise ValueError("Claim bridge grid mismatch")
            a = d.read(1)
        if not np.isfinite(a[fp]).all() or np.any(a[fp] < 0):
            raise ValueError("Invalid claim distance inside footprint")
        feats["claim_m"] = a
        prov["features"]["claim_m"] = entry
    elif claims.exists():
        d = json.loads(claims.read_text())
        if d.get("spatialReference", {}).get("wkid") != 32611 or d.get("count_expected") != d.get(
            "count_received"
        ):
            raise ValueError("Incomplete/wrong-CRS BLM closed claims")
        vectors, rejected, codes = [], Counter(), Counter()
        for f in d["features"]:
            attrs = f["attributes"]
            q = str(attrs.get("QLTY"))
            codes[q] += 1
            code = quality_code(q)
            if code is None or code > 10 or attrs.get("CSE_DISP") != "Closed":
                rejected["unknown/degraded/county-only geocode or not closed"] += 1
                continue
            geometry = f.get("geometry")
            if not geometry or not geometry.get("rings"):
                rejected["no geometry"] += 1
                continue
            pg = shape(esri_polygon(geometry["rings"]))
            if not pg.is_valid:
                from shapely import make_valid

                pg = make_valid(pg)
            if pg.is_empty or pg.area > 1e9:
                rejected["empty or implausibly broad (>1000 km2) geocode"] += 1
                continue
            vectors.append((mapping(pg), 1))
        if not vectors:
            raise ValueError("No located historic claims survived quality checks")
        feats["claim_m"], seed_count = burn_distance(vectors, fp)
        prov["features"]["claim_m"] = {
            "source": d["source"],
            "sha256": sha256_file(claims),
            "n_source_cases": len(d["features"]),
            "n_located_cases": len(vectors),
            "rejected": dict(rejected),
            "quality_counts": dict(codes),
            "seed_pixels": seed_count,
            "seed_grid_buffer_m": 20000,
            "limitation": "Closed MLRS legal-land polygons, often quarter-section resolution. Not exact historic workings/claim stakes; mining selection can reflect geology.",
        }
    else:
        prov["missing_required"].append("BLM historic closed-claim distances")
    area = acquisition_areas(fp)
    feats["area1"] = (area == 1).astype(np.uint8)
    prov["features"]["area1"] = {
        "source": "USGS official Area1/Area2 outline shapefiles (Area1 priority)",
        "url": "https://doi.org/10.5066/P93LGLVQ",
        "counts": {str(i): int(np.count_nonzero(fp & (area == i))) for i in (0, 1, 2)},
        "not_four_blocks": True,
    }
    block_path = DATA_DIR / "raw/official_audit/acquisition_blocks.geojson"
    if block_path.exists():
        d = json.loads(block_path.read_text())
        if d.get("boundary_status") != "verified_official_coordinates" or not d.get("source_url"):
            raise ValueError(
                "Unverified acquisition-block boundaries cannot enter the primary audit"
            )
        pairs = [(f["geometry"], int(f["properties"]["block_id"])) for f in d["features"]]
        block = rasterize(pairs, out_shape=fp.shape, transform=footprint.TRANSFORM, dtype="uint8")
        if not np.all(np.isin(block[fp], [1, 2, 3, 4])) or set(np.unique(block[fp])) != {
            1,
            2,
            3,
            4,
        }:
            raise ValueError("Four official block memberships must cover the footprint")
        for b in (1, 2, 3, 4):
            feats[f"block_{b}"] = (block == b).astype(np.uint8)
        prov["features"]["acquisition_blocks"] = {
            "url": d["source_url"],
            "sha256": sha256_file(block_path),
        }
    else:
        prov["missing_required"].append(
            "verified geographic boundaries of the four acquisition blocks"
        )
    prov["full_requested_audit_available"] = not prov["missing_required"]
    prov["feature_names"] = sorted(feats)
    prov["distance_units"] = "metres on a 100 m seed raster; boundary/PLSS uncertainty retained"
    np.savez_compressed(out / "confounds.npz", **feats)
    (out / "provenance.json").write_text(json.dumps(prov, indent=2) + "\n")
    (ROOT / "evidence/access_inputs.json").write_text(json.dumps(prov, indent=2) + "\n")
    return prov


def classifier_features(conf) -> dict[str, np.ndarray]:
    allowed = {"road_m", "claim_m", "area1", "block_1", "block_2", "block_3", "block_4"}
    keys = set(conf.files)
    if not keys <= allowed:
        raise ValueError(f"Forbidden nuisance inputs: {sorted(keys - allowed)}")
    if {"block_1", "block_2", "block_3", "block_4"} <= keys:
        keys.discard("area1")  # Full primary test uses ONLY the owner-requested families.
    return {
        k: np.log1p(conf[k]) if k.endswith("_m") else conf[k].astype(np.float32)
        for k in sorted(keys)
    }
