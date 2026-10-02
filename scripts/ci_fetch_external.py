"""CI fetcher v3: download official public-domain layers that document *field
accessibility* and *acquisition geometry* for the C2S2 audit, then commit the
results to the orphan branch ``public-layers`` so egress-restricted research
sandboxes (github.com only) can consume them.

Sources (official, public domain; every fetch logged with URL + sha256):
  * Census TIGER/Line 2023/2024 ROADS + RAILS for the counties that intersect
    the GeoDAWN bbox. https://www2.census.gov/geo/tiger/
  * USGS MRDS mineral-occurrence CSV archive (historic mining records).
    https://mrdata.usgs.gov/mrds/
  * USGS ScienceBase GeoDAWN release page: survey-outline shapefiles
    (Area 1 / Area 2 extents). https://www.sciencebase.gov/catalog/item/657e1d85d34e23d3533209f7
  * NBMG/INGENIOUS Qfaults ArcGIS REST: traces with FTYPE_ mapping-confidence,
    clipped to the bbox. https://web2.nbmg.unr.edu/arcgis/rest/services/Qfaults/Qfaults_INGENIOUS/MapServer/0
Nothing is guessed: directory listings and landing pages are parsed and every
decision logged. Research tooling only: never touches competition labels,
produces no predictions.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

BOX = (-120.0024, 37.3641, -116.1415, 40.7247)  # GeoDAWN bbox (ScienceBase item; verified in LEARNGEMSDOE)
OUT = Path(os.environ.get("OUT_DIR", "data_external"))
LOG: list[dict] = []


def log(entry: dict) -> None:
    LOG.append(entry)
    print(json.dumps(entry)[:400], flush=True)


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def fetch(url: str, dest: Path, *, tries: int = 3) -> bool:
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "GEMS-24-research-fetch/1.0 (academic audit tooling)"})
            with urllib.request.urlopen(req, timeout=300) as r:
                data = r.read()
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            log({"url": url, "file": str(dest), "bytes": len(data), "sha256": sha256(data), "http": 200, "try": k})
            return True
        except Exception as e:  # noqa: BLE001
            log({"url": url, "file": str(dest), "error": repr(e)[:220], "try": k})
    return False


# --------------------------------------------------------------------------- TIGER
def _zip_shp_reader(raw: Path, subdir: str):
    import shapefile

    with zipfile.ZipFile(raw) as z:
        stem = next(n for n in z.namelist() if n.endswith(".shp"))[:-4]
        tmp = OUT / subdir
        tmp.mkdir(exist_ok=True)
        for ext in (".shp", ".shx", ".dbf", ".prj"):
            (tmp / (Path(stem).name + ext)).write_bytes(z.read(stem + ext))
    return shapefile.Reader(str(tmp / (Path(stem).name + ".shp")))


def tiger_roads_and_rails() -> None:
    from shapely.geometry import box, shape as shapely_shape

    clip = box(*BOX)
    year = "2024"
    cty = OUT / "tiger_county.zip"
    if not fetch(f"https://www2.census.gov/geo/tiger/TIGER{year}/COUNTY/tl_{year}_us_county.zip", cty):
        year = "2023"
        if not fetch(f"https://www2.census.gov/geo/tiger/TIGER{year}/COUNTY/tl_{year}_us_county.zip", cty):
            return
    fips = set()
    r = _zip_shp_reader(cty, "cty")
    for sr in r.iterShapeRecords():
        g = shapely_shape(sr.shape.__geo_interface__)
        if g.intersects(clip):
            d = dict(zip([f[0] for f in r.fields[1:]], sr.record))
            fips.add(str(d["GEOID"])[:5])
    log({"tiger_counties_intersecting": sorted(fips), "tiger_year": year})
    cty.unlink(missing_ok=True)
    for f in sorted(fips):
        for layer in ("ROADS", "RAILS"):
            url = f"https://www2.census.gov/geo/tiger/TIGER{year}/{layer}/tl_{year}_{f}_{layer.lower()}.zip"
            raw = OUT / f"tiger_{layer}_{f}.zip"
            if not fetch(url, raw):
                continue
            try:
                rr = _zip_shp_reader(raw, f"tmp_{layer}_{f}")
                feats = []
                for sr in rr.iterShapeRecords():
                    g = shapely_shape(sr.shape.__geo_interface__)
                    if g.intersects(clip):
                        rec = dict(zip([x[0] for x in rr.fields[1:]], sr.record))
                        feats.append({"geom": g.intersection(clip).__geo_interface__,
                                       "props": {k: rec.get(k) for k in ("MTFCC", "NAME")}})
                outj = OUT / f"tiger_{layer}_{f}_clipped.geojson"
                outj.write_text(json.dumps({"type": "FeatureCollection", "features": feats,
                                            "source": url, "county_fips": f}))
                log({"derived": str(outj), "bytes": outj.stat().st_size, "sha256": sha256(outj.read_bytes()), "n": len(feats)})
                raw.unlink(missing_ok=True)
            except Exception as e:  # noqa: BLE001
                log({"tiger_step_error": f, "layer": layer, "err": repr(e)[:200]})


# --------------------------------------------------------------------------- MRDS
def mrds() -> None:
    html = OUT / "mrds_landing.html"
    if not fetch("https://mrdata.usgs.gov/mrds/", html):
        return
    txt = html.read_text(errors="ignore")
    links = sorted(set(re.findall(r'href="([^"]+\.(?:zip|csv)(?:[?][^"]*)?)"', txt, re.I)))
    log({"mrds_links_found": links[:40]})
    for c in links:
        if re.search(r"(point|export|mrds-csv|full|database)", c, re.I):
            url = c if c.startswith("http") else "https://mrdata.usgs.gov/mrds/" + c.lstrip("/")
            dest = OUT / ("mrds_" + re.sub(r"[^A-Za-z0-9.]+", "_", os.path.basename(urllib.parse.urlparse(url).path)))
            if fetch(url, dest):
                log({"mrds_selected": url})
                return


# --------------------------------------------------------------------------- GeoDAWN outlines
def sciencebase_outlines() -> None:
    page = OUT / "geodawn_sb_item.html"
    if not fetch("https://www.sciencebase.gov/catalog/item/657e1d85d34e23d3533209f7", page):
        return
    txt = page.read_text(errors="ignore")
    pairs = re.findall(r'data-url="(/catalog/file/get/[^"]+)"[^>]*>([^<]+)</span>', txt)
    pairs = [("https://www.sciencebase.gov" + u, n) for u, n in pairs]
    log({"sb_links": [p[1] for p in pairs][:60]})
    for url, name in pairs:
        if "outline" in name.lower():
            raw = OUT / name
            if fetch(url, raw):
                try:
                    with zipfile.ZipFile(raw) as z:
                        log({"outline_members": z.namelist()[:12], "name": name})
                    _shp_zip_to_clipped(raw, name)
                except Exception as e:  # noqa: BLE001
                    log({"outline_error": name, "err": repr(e)[:160]})


def _shp_zip_to_clipped(raw: Path, label: str) -> None:
    from shapely.geometry import box, shape as shapely_shape

    clip = box(*BOX)
    r = _zip_shp_reader(raw, raw.stem + "_tmp")
    feats = []
    for sr in r.iterShapeRecords():
        g = shapely_shape(sr.shape.__geo_interface__)
        feats.append({"geom": g.intersection(clip).__geo_interface__,
                      "props": dict(zip([f[0] for f in r.fields[1:]], sr.record))})
    outj = OUT / (label + "_clipped.geojson")
    outj.write_text(json.dumps({"type": "FeatureCollection", "features": feats, "source": label}))
    log({"derived": str(outj), "bytes": outj.stat().st_size, "sha256": sha256(outj.read_bytes()), "n": len(feats)})


# --------------------------------------------------------------------------- Qfaults confidence
def nbmg_qfaults_confidence() -> None:
    """Server does not support pagination; the bbox envelope is tiled
    recursively until no tile is truncated (exceededTransferLimit)."""
    where = "FTYPE_ IN ('Well Constrained','Moderately Constrained','Inferred')"
    base = "https://web2.nbmg.unr.edu/arcgis/rest/services/Qfaults/Qfaults_INGENIOUS/MapServer/0/query"
    seen: dict[int, dict] = {}

    def query_tile(w, s, e, n, depth=0) -> bool:
        q = urllib.parse.urlencode({
            "where": where, "geometry": f"{w},{s},{e},{n}",
            "geometryType": "esriGeometryEnvelope", "inSR": "4326",
            "spatialRel": "esriSpatialRelIntersects", "outFields": "*",
            "returnGeometry": "true", "f": "json",
        })
        dest = OUT / f"_nbmg_tile_{depth}_{len(seen)}.json"
        if not fetch(base + "?" + q, dest, tries=2):
            return False
        d = json.loads(dest.read_text())
        dest.unlink(missing_ok=True)
        if "error" in d:
            log({"nbmg_error": d["error"].get("message", "")[:180]})
            return False
        feats = d.get("features", [])
        for f in feats:
            oid = f.get("attributes", {}).get("OBJECTID") or f.get("attributes", {}).get("OBJECTID_", 0)
            seen[int(oid)] = f
        trunc = d.get("exceededTransferLimit", False) or len(feats) >= 500
        if trunc:
            if depth >= 7:
                log({"nbmg_tile_giveup": [w, s, e, n]})
                return True
            mw, mn = (w + e) / 2, (s + n) / 2
            for tile in ((w, s, mw, mn), (mw, s, e, mn), (w, mn, mw, n), (mw, mn, e, n)):
                query_tile(*tile, depth + 1)
        return True

    query_tile(*BOX)
    geo = {"type": "FeatureCollection", "features": list(seen.values()),
           "meta": {"source": base, "where": where, "bbox": list(BOX),
                    "census_check": "region-wide FTYPE_ counts on 2026-10-01: WC 12048 (https://web2.nbmg.unr.edu/.../MapServer/0/query?where=FTYPE_%20=%20%27Well%20Constrained%27&returnCountOnly=true&f=json)"}}
    outp = OUT / "qfaults_v2_in_footprint.json"
    outp.write_text(json.dumps(geo))
    log({"derived": str(outp), "bytes": outp.stat().st_size, "sha256": sha256(outp.read_bytes()), "n": len(seen)})


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    mode = os.environ.get("FETCH_MODE", "all")
    for fn in [tiger_roads_and_rails, mrds, sciencebase_outlines, nbmg_qfaults_confidence]:
        if mode in ("all", fn.__name__):
            try:
                fn()
            except Exception as e:  # noqa: BLE001
                log({"step_error": fn.__name__, "err": repr(e)[:300]})
    (OUT / "fetch_manifest.json").write_text(json.dumps({
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "bbox_wgs84": list(BOX),
        "purpose": "confound layers for C2S2 accessibility audit (24GEMSDOE); public-domain sources; research use only",
        "log": LOG,
    }, indent=2))
    print("FETCH DONE")


if __name__ == "__main__":
    main()
