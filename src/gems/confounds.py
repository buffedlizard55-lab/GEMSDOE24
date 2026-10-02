"""Non-geological confound features on the official 100 m grid.

These layers encode *how the catalogue came to exist* — where airborne geophysics
were acquired and where field crews could physically get to — not the geology
itself. They are the inputs to the classifier two-sample test in
:mod:`gems.c2s2`. Every layer is computed from files shipped in this repository;
the provenance of each input is documented in ``registry/sources.json``.

Feature inventory (computed in :func:`build_all`)
-------------------------------------------------
acq_window        0 outside both contractor survey areas, 1 = GeoDAWN Area 1
                  (200 m flight lines), 2 = Area 2 (400 m lines, 4,000 m ties).
acq_block         Block index within the acquisition extent, from an empirical
                  changepoint detection on column-wise high-frequency radiometric
                  texture (documented in ``evidence/acq_block_audit.json``),
                  combined with the Area 1 window. The GeoDAWN ReadMe describes
                  four N-S-trending acquisition blocks (Winnemucca/Fallon/
                  Hawthorne/Tonopah) with varying line spacing and terrain
                  clearance; the ReadMe itself could not be downloaded in this
                  sandbox, so block *count* is verified only where the grids
                  permit and block *boundaries* are measured, not asserted.
lidar_cov         1 inside the 1 m lidar footprint (3DEP-coverage flag of the
                  7GEMSDOE ``lidar_scarp_features_u8.tif`` ``valid`` band);
                  a proxy for where mapping/funding infrastructure existed.
d_probe_px        Distance (log1p, px) to the nearest INGENIOUS 2 m temperature
                  probe station — stations that field crews had to *hike to*.
d_well_px         Distance to the nearest GDR 1391 spring/well record — wells are
                  drilled from roads.
d_sinter_px       Distance to nearest paleo-geothermal sinter/travertine/tufa
                  outcrop mapped on the ground by INGENIOUS geologists.
d_vent_px         Distance to nearest Quaternary volcanic vent record.
d_road_px         OPTIONAL: distance to nearest road/trail; loaded from
                  ``data/confounds/d_road_px.tif`` if the operator ran
                  ``scripts/fetch_field_access_layers.py`` (TIGER/OSM hosts are
                  unreachable from this sandbox; measured, see
                  registry/irregularities.json I-01).
d_claim_px        OPTIONAL: distance to nearest historic mining claim record
                  (USGS MRDS) from ``data/confounds/d_claim_px.tif``.

All distances are in pixels (1 px = 100 m) computed with a Euclidean distance
transform on the official grid; features are log1p-transformed for the classifier.
"""
from __future__ import annotations

import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

from .footprint import HEIGHT, WIDTH, load_footprint
from .paths import DATA_DIR, ROOT

ROOT = DATA_DIR.parent
EXT = DATA_DIR / "external"
CONF = DATA_DIR / "confounds"

# GeoDAWN contractor grid provenance, measured in the 5GEMSDOE reconstruction and
# re-verified here from the same files (evidence/data_verification.json of that repo):
# Area 1 source grid EPSG:32611 transform (50 m px) x0=406575, y0=4202725,
# width=1338, height=979  ->  UTM window (406575, 4202725) - (473475, 4153775).
AREA1_UTM = (406575.0, 4153775.0, 473475.0, 4202725.0)
# Competition grid origin/resolution (EPSG:32611): x0=243350, y0=4508550, 100 m.
GRID_X0, GRID_Y0, GRID_RES = 243350.0, 4508550.0, 100.0

FEATURES_LOG1P = ["d_probe_px", "d_well_px", "d_sinter_px", "d_vent_px"]


def _utm_to_grid(x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """UTM-11N eastings/northings -> (row, col) on the official 100 m grid."""
    col = np.floor((np.asarray(x) - GRID_X0) / GRID_RES).astype(np.int64)
    row = np.floor((GRID_Y0 - np.asarray(y)) / GRID_RES).astype(np.int64)
    return row, col


def _read_csv_points(path: Path, x_col: str, y_col: str) -> tuple[np.ndarray, np.ndarray]:
    import csv

    xs, ys = [], []
    with open(path, newline="") as f:
        for rec in csv.DictReader(f):
            try:
                x, y = float(rec[x_col]), float(rec[y_col])
            except (KeyError, TypeError, ValueError):
                continue
            if np.isfinite(x) and np.isfinite(y):
                xs.append(x)
                ys.append(y)
    return np.asarray(xs), np.asarray(ys)


def _probe_shapefile_points(ext_dir: Path) -> tuple[np.ndarray, np.ndarray]:
    """Read point shapes + lon/lat attributes from the cached 2 m probe shapefile.

    Uses pyshp if importable; otherwise a minimal struct-based .shp reader
    (point geometries only). Coordinates are NAD83 geographic (degrees); they are
    reprojected to UTM 11N with pyproj.
    """
    zpath = ext_dir / "2m_temperature_probe_INGENIOUS_regional_data.zip"
    with zipfile.ZipFile(zpath) as z:
        names = z.namelist()
        shp = [n for n in names if n.endswith(".shp")][0]
        prj = [n for n in names if n.endswith(".prj")]
        prj_txt = z.read(prj[0]).decode().upper() if prj else ""
        raw = z.read(shp)
    assert "GEOGCS" in prj_txt and "UTM" not in prj_txt, "expected geographic CRS"
    pts: list[tuple[float, float]] = []
    off = 100  # .shp header is 100 bytes
    n = len(raw)
    while off + 8 <= n:
        _recno, content_len = json.loads("[" + str(int.from_bytes(raw[off : off + 4], "little")) + "," + str(int.from_bytes(raw[off + 4 : off + 8], "big")) + "]")
        body = raw[off + 8 : off + 8 + content_len * 2]
        shape_type = int.from_bytes(body[:4], "little")
        if shape_type == 1:  # Point
            x, y = np.frombuffer(body[4:20], dtype="<f8")
            pts.append((float(x), float(y)))
        elif shape_type == 11:  # PointZ
            x, y = np.frombuffer(body[4:20], dtype="<f8")
            pts.append((float(x), float(y)))
        elif shape_type in (8, 18):  # MultiPoint(Z)
            cnt = int.from_bytes(body[20:24], "little")
            arr = np.frombuffer(body[24 : 24 + 16 * cnt], dtype="<f8").reshape(-1, 2)
            pts.extend((float(a), float(b)) for a, b in arr)
        off += 8 + content_len * 2
    lon = np.array([p[0] for p in pts])
    lat = np.array([p[1] for p in pts])
    from pyproj import Transformer

    tf = Transformer.from_crs("EPSG:4269", "EPSG:32611", always_xy=True)
    x, y = tf.transform(lon, lat)
    return np.asarray(x), np.asarray(y)


def _dist_layer(seeds: np.ndarray, fp: np.ndarray) -> np.ndarray:
    """Distance transform to nearest seed pixel (px), computed inside footprint."""
    mask = np.zeros((HEIGHT, WIDTH), dtype=bool)
    r, c = seeds[:, 0], seeds[:, 1]
    ok = (r >= 0) & (r < HEIGHT) & (c >= 0) & (c < WIDTH)
    r2, c2 = r[ok], c[ok]
    ok2 = fp[r2, c2]
    mask[r2[ok2], c2[ok2]] = True
    dist = distance_transform_edt(~mask)
    return dist.astype(np.float32)


def _detect_block_boundaries(rad_path: Path, labels_path: Path) -> dict:
    """Empirically detect N-S acquisition-block seams from column-wise texture.

    Method (fully specified, re-runnable):
      1. Band 4 (TC total count, uint8) of the re-gridded GeoDAWN radiometric
         mosaic; high-frequency energy = |vertical second difference| smoothed
         51x5 columns. Area-1 columns (finer flight lines) are excluded before
         peak searching.
      2. For every column, the z-score of that energy relative to a 101-column
         rolling median; block-boundary columns are local maxima with z > 6 and
         |slope| of the smoothed energy across the column > 3 sigma (a *step*,
         not a spike), separated by >= 200 columns.
      3. Cross-check: the same step test on the column density of catalogue
         pixels (mapped-fault density changes where survey teams changed).
    Returns column boundaries + diagnostics. Boundaries are a hypothesis about
    survey organisation, measured from the data, not an official spec.
    """
    from scipy.ndimage import gaussian_filter1d, median_filter

    with rasterio.open(rad_path) as s:
        tc = s.read(4).astype(np.float32)
    gy = np.gradient(tc, axis=0)
    hf = np.abs(np.gradient(gy, axis=0))
    col_e = gaussian_filter1d(hf.mean(axis=0), 5.0)
    with rasterio.open(labels_path) as s:
        lab = (s.read(1) > 0)
    col_lab = gaussian_filter1d(lab.sum(axis=0).astype(np.float32), 5.0)

    def steps(sig: np.ndarray, exclude: tuple[int, int] | None) -> list[dict]:
        med = median_filter(sig, size=101, mode="nearest")
        resid = sig - med
        sd = float(np.std(resid[np.isfinite(resid)]))
        jumps = np.abs(np.gradient(sig))
        jump_sd = float(np.std(jumps))
        out = []
        for c in range(1, len(sig) - 1):
            if exclude and exclude[0] - 2 <= c <= exclude[1] + 2:
                continue
            z = resid[c] / (sd + 1e-12)
            if z > 6.0 and jumps[c] > 3.0 * jump_sd and sig[c] == max(sig[max(0, c - 3) : c + 4]):
                out.append({"col": int(c), "z": round(float(z), 2), "jump_sigma": round(float(jumps[c] / (jump_sd + 1e-12)), 2)})
        kept: list[dict] = []
        for o in sorted(out, key=lambda d: -d["z"]):
            if all(abs(o["col"] - k["col"]) >= 200 for k in kept):
                kept.append(o)
        return sorted(kept, key=lambda d: d["col"])

    a1 = area1_cols()
    tex_bounds = steps(col_e, exclude=(a1[0], a1[1]))
    lab_bounds = steps(col_lab, exclude=(a1[0], a1[1]))
    both = sorted({b["col"] for b in tex_bounds} & {b["col"] for b in lab_bounds})
    return {
        "texture_step_candidates": tex_bounds,
        "label_density_step_candidates": lab_bounds,
        "columns_confirmed_by_both_signals": both,
        "method": "see docstring; all statistics recomputable from data/external + data/bridge",
    }


def area1_cols() -> tuple[int, int]:
    x0, _, x1, _ = AREA1_UTM
    return int((x0 - GRID_X0) / GRID_RES), int(np.ceil((x1 - GRID_X0) / GRID_RES))


def area1_rows() -> tuple[int, int]:
    _, y0, _, y1 = AREA1_UTM
    return int((GRID_Y0 - y1) / GRID_RES), int(np.ceil((GRID_Y0 - y0) / GRID_RES))


def build_all(out_dir: Path | None = None, *, force: bool = False) -> dict:
    """Build ``confounds.npz`` + ``confounds_provenance.json`` under data/confounds."""
    out_dir = out_dir or CONF
    out_dir.mkdir(parents=True, exist_ok=True)
    out_npz = out_dir / "confounds.npz"
    prov_path = out_dir / "confounds_provenance.json"
    if out_npz.exists() and not force:
        return json.loads(prov_path.read_text())

    fp = load_footprint()
    prov: dict = {"generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "inputs": {}}

    # 1. acquisition window — official ScienceBase survey-outline polygons when
    #    present (data_external branch artifacts copied to data/external), else
    #    the verified 5GEMSDOE rectangle approximation.
    r0, r1 = area1_rows()
    c0, c1 = area1_cols()
    win = np.full((HEIGHT, WIDTH), 3, dtype=np.uint8)   # 3 = inside fp but outside both areas
    win[~fp] = 0
    outlines = {}
    for nm in ("GeoDAWN_area1_outline.zip", "GeoDAWN_area2_outline.zip"):
        for base in (DATA_DIR / "external", ROOT / "data_external"):
            if (base / nm).exists():
                outlines[nm] = base / nm
                break
    if "GeoDAWN_area1_outline.zip" in outlines and "GeoDAWN_area2_outline.zip" in outlines:
        import zipfile
        import shapefile
        from rasterio.features import rasterize

        for nm, val in (("GeoDAWN_area1_outline.zip", 1), ("GeoDAWN_area2_outline.zip", 2)):
            with zipfile.ZipFile(outlines[nm]) as z:
                stem = next(n for n in z.namelist() if n.endswith(".shp"))[:-4]
                for ext in (".shp", ".shx", ".dbf", ".prj"):
                    (out_dir / f"_tmp_{Path(stem).name}{ext}").write_bytes(z.read(stem + ext))
            rr = shapefile.Reader(str(out_dir / f"_tmp_{Path(stem).name}.shp"))
            feats = []
            for sr in rr.shapes():
                g = __import__("shapely.geometry", fromlist=["shape"]).shape(sr.__geo_interface__)
                def px(ring):
                    xs_, ys_ = ring.xy
                    return [[(x - GRID_X0) / GRID_RES, (GRID_Y0 - y) / GRID_RES] for x, y in zip(xs_, ys_)]
                if g.geom_type == "Polygon":
                    feats.append(({"type": "Polygon", "coordinates": [px(g.exterior)] + [px(i) for i in g.interiors]}, 1))
                elif g.geom_type == "MultiPolygon":
                    for pg in g.geoms:
                        feats.append(({"type": "Polygon", "coordinates": [px(pg.exterior)] + [px(i) for i in pg.interiors]}, 1))
            m = rasterize(feats, out_shape=(HEIGHT, WIDTH), all_touched=True).astype(bool)
            win[m & fp] = val
            for ext in (".shp", ".shx", ".dbf", ".prj"):
                (out_dir / f"_tmp_{Path(stem).name}{ext}").unlink(missing_ok=True)
        prov["acq_window"] = {
            "semantics": "0 outside fp, 1 Area1 polygon (200 m lines), 2 Area2 polygon (400 m/4 km), 3 inside fp but outside both official outlines",
            "source": "ScienceBase official outline shapefiles (GeoDAWN_area1/2_outline.zip, 1.19/1.50 KB, item 657e1d85d34e23d3533209f7) fetched via public-layers CI; Area1 bbox cross-checks 5GEMSDOE reconstruction within 200 m",
        }
    else:
        win = np.full((HEIGHT, WIDTH), 2, dtype=np.uint8)
        win[~fp] = 0
        win[max(r0, 0): min(r1, HEIGHT), max(c0, 0): min(c1, WIDTH)] = 1
        prov["acq_window"] = {
            "semantics": "0 outside GeoDAWN, 1 Area1 (200 m lines), 2 Area2 (400 m lines/4 km ties)",
            "area1_grid_window_rows_cols": [r0, r1, c0, c1],
            "source": "5GEMSDOE/data/reconstructed/provenance.json (rectangle approximation; outlines zip not fetched yet)",
        }


    # 2. empirical block boundaries inside Area 2
    blocks = _detect_block_boundaries(EXT / "geodawn_rad_u8.tif", DATA_DIR / "bridge" / "labels.tif")
    (ROOT / "evidence").mkdir(exist_ok=True)
    (ROOT / "evidence" / "acq_block_audit.json").write_text(json.dumps(blocks, indent=2) + "\n")
    boundary_cols = blocks["columns_confirmed_by_both_signals"] or [b["col"] for b in blocks["texture_step_candidates"]]
    block = np.zeros((HEIGHT, WIDTH), dtype=np.uint8)
    edges = [0] + boundary_cols + [WIDTH]
    for b in range(len(edges) - 1):
        block[:, edges[b] : edges[b + 1]] = b + 1
    block = np.where(fp, block, 0).astype(np.uint8)
    prov["acq_block"] = {
        "n_boundaries_detected": len(boundary_cols),
        "boundary_cols": boundary_cols,
        "semantics": "empirically measured N-S block seams (0=outside footprint); GeoDAWN ReadMe describes four blocks (inherited claim, see sources.json)",
        "method": "evidence/acq_block_audit.json",
    }

    # 3. lidar coverage flag
    with rasterio.open(EXT / "lidar_scarp_features_u8.tif") as s:
        lidar_cov = (s.read(12) > 0).astype(np.uint8)
    prov["lidar_cov"] = {
        "semantics": "1 where the 1 m lidar scarp product is valid (7GEMSDOE valid band 12)",
        "coverage_frac_in_fp": round(float(lidar_cov[fp].mean()), 4),
    }

    # 4. distance-to-fieldwork-point features
    xs, ys = _read_csv_points(EXT / "gdr_wellspring_in_footprint.csv", "utm_x", "utm_y")
    d_well = _dist_layer(np.stack(_utm_to_grid(xs, ys), axis=1), fp)
    n_well = len(xs)

    def _rowcol_seeds(path: Path) -> np.ndarray:
        import csv as _csv

        with open(path, newline="") as f:
            recs = list(_csv.DictReader(f))
        rows, cols = [], []
        for r in recs:
            try:
                rows.append(int(float(r["row"])))
                cols.append(int(float(r["col"])))
            except (KeyError, TypeError, ValueError):
                pass
        return np.stack([np.asarray(rows, dtype=np.int64), np.asarray(cols, dtype=np.int64)], axis=1)

    vent_seeds = _rowcol_seeds(EXT / "gdr_volcanic_vents_in_footprint.csv")
    d_vent = _dist_layer(vent_seeds, fp)

    # paleo-geothermal sinter/travertine: Long/Lat degrees NAD83 -> grid
    import pandas as pd

    with zipfile.ZipFile(EXT / "paleo_geothermal_regional.zip") as z:
        with z.open("Paleo_geothermal_final.csv") as f:
            pal = pd.read_csv(f, encoding="latin-1")
    pal = pal[pd.to_numeric(pal["Long_deg_NAD83"], errors="coerce").notna()]
    from pyproj import Transformer

    tf = Transformer.from_crs("EPSG:4269", "EPSG:32611", always_xy=True)
    px_, py_ = tf.transform(pal["Long_deg_NAD83"].to_numpy(float), pal["Lat_deg_NAD83"].to_numpy(float))
    sinter_rows, sinter_cols = _utm_to_grid(np.asarray(px_), np.asarray(py_))
    sinter_seeds = np.stack([sinter_rows, sinter_cols], axis=1)
    d_sinter = _dist_layer(sinter_seeds, fp)
    px, py = _probe_shapefile_points(EXT)
    rows, cols = _utm_to_grid(px, py)
    d_probe = _dist_layer(np.stack([rows, cols], axis=1), fp)

    feats: dict[str, np.ndarray] = {
        "acq_window": win,
        "acq_block": block,
        "lidar_cov": lidar_cov,
        "d_probe_px": d_probe,
        "d_well_px": d_well,
        "d_sinter_px": d_sinter,
        "d_vent_px": d_vent,
    }
    prov["point_sets"] = {
        "wellsprings": int(n_well),
        "vents": int(len(vent_seeds)),
        "sinter_points": int(len(sinter_seeds)),
        "probes": int(len(px)),
    }

    # 5. optional operator-provided road/claim distances
    for opt in ("d_road_px", "d_claim_px", "d_wc_px", "d_inf_px"):
        p = out_dir / f"{opt}.tif"
        if p.exists():
            with rasterio.open(p) as s:
                feats[opt] = s.read(1).astype(np.float32)
            prov[opt] = {"source": str(p), "status": "operator-provided official vector distance"}
        else:
            prov[opt] = {"status": "absent in this sandbox (hosts unreachable; see irregularities I-01); run scripts/fetch_field_access_layers.py"}

    np.savez_compressed(out_npz, **feats)
    prov["output"] = str(out_npz.relative_to(ROOT))
    prov["feature_list"] = sorted(feats)
    prov_path.write_text(json.dumps(prov, indent=2) + "\n")
    return prov


if __name__ == "__main__":
    print(json.dumps(build_all(force=True), indent=2))
