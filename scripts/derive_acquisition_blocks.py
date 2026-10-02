#!/usr/bin/env python3
"""Derive and audit the four GeoDAWN acquisition blocks (see src/gems/acquisition.py).

Inputs (all committed, all official): the report PDF (Figure 3), the extent polygon, the flight-path
line summaries/samples extracted on CI, and the template footprint. No label is read.
Outputs: ``acquisition_block_id_100m.tif`` (uint8 1..4, 0 outside the footprint) and a receipt
with the georeferencing residual, polygons and the line-km audit against the published totals.
"""

from __future__ import annotations

import gzip
import hashlib
import io
import json
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
import shapefile
from PIL import Image
from pypdf import PdfReader
from pyproj import Transformer
from rasterio.features import rasterize
from shapely.geometry import Polygon, mapping, shape

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems import acquisition as acq  # noqa: E402
from gems import footprint  # noqa: E402

SRC = ROOT / "data/external/audit_sources"
PDF = SRC / "GeoDAWN_NV_WestCentral_Geophysical_2020_D21_Report.pdf"
FIG_PAGE = 4  # zero-based page of "Figure 3. The Four GeoDAWN Acquisition Blocks"
EXPECTED = {  # edge positions in native figure pixels (located by projection, then line-fitted)
    "blue": {"left": 387, "right": 970, "top": 326, "bottom": 685},
    "green": {"left": 657, "right": 1079, "top": 676, "bottom": 994},
    "white": {"left": 424, "right": 1408, "top": 77, "bottom": 316},
}


def figure_image() -> tuple[np.ndarray, str]:
    page = PdfReader(str(PDF)).pages[FIG_PAGE]
    best = max(page.images, key=lambda im: len(im.data))
    arr = np.array(Image.open(io.BytesIO(best.data)).convert("RGB")).astype(int)
    return arr, hashlib.sha256(best.data).hexdigest()


def extent_ring() -> np.ndarray:
    z = zipfile.ZipFile(SRC / "GeoDAWN_data_extent.zip")
    stem = next(n[:-4] for n in z.namelist() if n.endswith(".shp"))
    r = shapefile.Reader(
        shp=io.BytesIO(z.read(stem + ".shp")),
        shx=io.BytesIO(z.read(stem + ".shx")),
        dbf=io.BytesIO(z.read(stem + ".dbf")),
    )
    sh = r.shape(0)
    pts = np.array(sh.points)
    end = list(sh.parts)[1] if len(sh.parts) > 1 else len(pts)
    return pts[:end]  # outer ring; remaining parts are exclusion holes


def main() -> None:
    img, fig_sha = figure_image()
    R, G, B = img[..., 0], img[..., 1], img[..., 2]
    yellow = (R > 175) & (G > 175) & (B < 125) & (np.abs(R - G) < 70)
    masks = {
        "blue": (B > 200) & (R < 90) & (G < 90),
        "green": (G > 215) & (R > 60) & (R < 190) & (B < 110),
        # The yellow survey line is drawn over parts of the white rectangle: accept it as edge evidence
        "white": ((R > 238) & (G > 238) & (B > 238)) | yellow,
    }
    ring = acq.densify(extent_ring())
    to_ll = Transformer.from_crs(32611, 4326, always_xy=True)
    lon, lat = to_ll.transform(ring[:, 0], ring[:, 1])
    geo, chamfer = acq.fit_georef(lon, lat, yellow)
    print("georef", geo.as_dict(), "chamfer_px", round(chamfer, 3), flush=True)

    polys_img = {}
    for name, e in EXPECTED.items():
        m = masks[name]
        h_span = (e["left"] + 20, e["right"] - 20)
        v_span = (e["top"] + 20, e["bottom"] - 20)
        edges = {
            "left": acq.fit_line(
                acq.edge_pixels(m, vertical=True, expected=e["left"], span=v_span), True
            ),
            "right": acq.fit_line(
                acq.edge_pixels(m, vertical=True, expected=e["right"], span=v_span), True
            ),
            "top": acq.fit_line(
                acq.edge_pixels(m, vertical=False, expected=e["top"], span=h_span), False
            ),
            "bottom": acq.fit_line(
                acq.edge_pixels(m, vertical=False, expected=e["bottom"], span=h_span), False
            ),
        }
        corners = acq.rect_corners(edges["left"], edges["right"], edges["top"], edges["bottom"])
        polys_img[name] = corners
    from_ll = Transformer.from_crs(4326, 32611, always_xy=True)

    def img_to_utm(pts):
        u, v = np.array([p[0] for p in pts]), np.array([p[1] for p in pts])
        lo, la = geo.inverse(u, v)
        x, y = from_ll.transform(lo, la)
        return list(zip(np.asarray(x).tolist(), np.asarray(y).tolist()))

    utm = {k: img_to_utm(v) for k, v in polys_img.items()}
    fp = footprint.load_footprint()
    with rasterio.open(ROOT / "data/bridge/sample_submission.tif") as t:
        transform = t.transform
    # Tonopah = everything south of the Hawthorne block's base line (its north edge is that line)
    hx = np.array([p[0] for p in utm["green"]])
    hy = np.array([p[1] for p in utm["green"]])
    base_y = float(np.mean(hy[2:4]))  # bottom-left / bottom-right corners (lowest northing)
    south = Polygon(
        [
            (hx.min() - 5e5, base_y),
            (hx.max() + 5e5, base_y),
            (hx.max() + 5e5, base_y - 5e5),
            (hx.min() - 5e5, base_y - 5e5),
        ]
    )
    shapes = {
        1: Polygon(utm["white"]),
        2: Polygon(utm["blue"]),
        3: Polygon(utm["green"]),
        4: south,
    }
    block = np.zeros(fp.shape, np.uint8)
    for bid in (1, 2, 3, 4):  # later ids win in a few-pixel overlap strip
        part = rasterize(
            [(mapping(shapes[bid]), bid)], out_shape=fp.shape, transform=transform, dtype="uint8"
        )
        block[part > 0] = bid
    block[~fp] = 0
    block, filled = acq.fill_unassigned(block, fp)
    counts = {acq.BLOCK_NAMES[b]: int(np.count_nonzero((block == b) & fp)) for b in acq.BLOCK_NAMES}
    print("pixels per block", counts, "filled gap pixels", filled, flush=True)

    # --- audit against the published line-km totals ---------------------------------------------
    summary = pd.read_csv(SRC / "geodawn_flight_line_summary.csv")
    sample = pd.read_csv(gzip.open(SRC / "geodawn_flight_path_sample.csv.gz", "rt"))
    inv = ~transform

    def lookup(x, y):
        cols, rows = inv * (np.asarray(x), np.asarray(y))
        return np.floor(cols).astype(int), np.floor(rows).astype(int)

    with zipfile.ZipFile(ROOT / "data/external/GeoDAWN_area1_outline.zip") as z:
        stem = next(n[:-4] for n in z.namelist() if n.endswith(".shp"))
        rd = shapefile.Reader(
            shp=io.BytesIO(z.read(stem + ".shp")),
            shx=io.BytesIO(z.read(stem + ".shx")),
            dbf=io.BytesIO(z.read(stem + ".dbf")),
        )
        a1 = rasterize(
            [(mapping(shape(s.__geo_interface__)), 1) for s in rd.shapes()],
            out_shape=fp.shape,
            transform=transform,
            dtype="uint8",
        ).astype(bool)
    variants = {}
    for variant, drop_a2_in_area1 in (
        ("a1_plus_a2_all", False),
        ("a1_plus_a2_outside_area1", True),
    ):
        per_line = []
        for (area, line), grp in sample.groupby(["area", "line"]):
            km = float(summary[(summary.area == area) & (summary.line == line)]["km"].iloc[0])
            xy = grp[["x", "y"]].to_numpy()
            if drop_a2_in_area1 and area == "a2":
                c, r = lookup(xy[:, 0], xy[:, 1])
                ok = (r >= 0) & (r < fp.shape[0]) & (c >= 0) & (c < fp.shape[1])
                inside = np.zeros(len(xy), bool)
                inside[ok] = a1[r[ok], c[ok]]
                if inside.all():
                    continue
                km *= float(np.mean(~inside))
                xy = xy[~inside]
            per_line.append((km, xy))
        derived = acq.block_line_km(per_line, block, lambda x, y: lookup(x, y))
        variants[variant] = {
            "derived_km_by_block": {acq.BLOCK_NAMES[b]: v for b, v in derived.items()}
        }
        variants[variant]["audit"] = acq.audit_line_km(derived)
    primary = variants["a1_plus_a2_outside_area1"]["audit"]
    comps = acq.connected_components_per_block(block)
    receipt = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "status": "derived_audited" if primary["passed"] else "derived_audit_failed",
        "label_free": True,
        "official_coordinates": False,
        "source": {
            "report_figure": "Figure 3, The Four GeoDAWN Acquisition Blocks (report page 5 of the PDF)",
            "figure_sha256": fig_sha,
            "extent_polygon": "GeoDAWN_data_extent.zip (official)",
            "report": "https://www.sciencebase.gov/catalog/item/657e1d85d34e23d3533209f7",
            "doi": "10.5066/P93LGLVQ",
        },
        "georeference": {
            **geo.as_dict(),
            "mean_chamfer_residual_px": chamfer,
            "px_per_km_east": geo.a / 111.32,
            "px_per_km_north": -geo.b / 111.32,
        },
        "polygons_utm_11n": {k: v for k, v in utm.items()},
        "tonopah_rule": "footprint south of the Hawthorne rectangle's base line (northing %.0f m)"
        % base_y,
        "pixels_per_block": counts,
        "gap_pixels_assigned_to_nearest_block": filled,
        "connected_components_per_block": comps,
        "line_km_audit": variants,
        "primary_audit_variant": "a1_plus_a2_outside_area1",
        "audit_tolerances_fixed_before_derivation": {
            "per_block": acq.TOLERANCE_PER_BLOCK,
            "total": acq.TOLERANCE_TOTAL,
        },
        "limitations": [
            "Boundaries are read from a figure, not published coordinates; edge uncertainty is a few km.",
            "Tie lines extend at least 2 km into adjacent blocks (report), so membership within ~2 km of a boundary is inherently ambiguous.",
            "Official flight-number to block mapping exists (report) but the profile CSV archives are S3-hosted and not anonymously downloadable.",
        ],
    }
    profile = {
        "driver": "GTiff",
        "dtype": "uint8",
        "count": 1,
        "height": fp.shape[0],
        "width": fp.shape[1],
        "crs": "EPSG:32611",
        "transform": transform,
        "nodata": 0,
        "compress": "deflate",
    }
    out = SRC / "acquisition_block_id_100m.tif"
    with rasterio.open(out, "w", **profile) as dst:
        dst.write(np.where(fp, block, 0).astype(np.uint8), 1)
    receipt["raster"] = {
        "path": str(out.relative_to(ROOT)),
        "sha256": hashlib.sha256(out.read_bytes()).hexdigest(),
    }
    (SRC / "acquisition_blocks_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(
        json.dumps(
            {
                k: receipt[k]
                for k in ("status", "pixels_per_block", "connected_components_per_block")
            },
            indent=2,
        )
    )
    for name, v in variants.items():
        print(name, json.dumps(v["audit"]["total"]), "passed:", v["audit"]["passed"])
        for b, row in v["audit"]["blocks"].items():
            print("   ", b, row)


if __name__ == "__main__":
    main()
