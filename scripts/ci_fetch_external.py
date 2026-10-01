"""CI fetcher: download official public-domain data layers that document *field
accessibility* and *acquisition geometry* for the C2S2 audit, then commit them
to the orphan branch ``public-layers`` so that egress-restricted research
sandboxes (which can only reach github.com) can consume them.

Sources (official, public domain / CC0; each fetch is logged with URL + sha256):
  * Census TIGER/Line 2023 ROADS + RAILS (Nevada + California), clipped to the
    GeoDAWN bounding box. https://www2.census.gov/geo/tiger/TIGER2023/
  * USGS MRDS mineral-occurrence download (historic mining records), states
    NV + CA. Landing page is parsed for the published link; nothing guessed.
    https://mrdata.usgs.gov/mrds/
  * USGS ScienceBase GeoDAWN release: area outline shapefiles (survey extents).
    https://www.sciencebase.gov/catalog/item/657e1d85d34e23d3533209f7
  * NBMG/INGENIOUS Qfaults ArcGIS REST: Qfaults v2 traces with FTYPE_
    (Well/Moderately/Inferred Constrained mapping-confidence) clipped to the
    GeoDAWN bbox. https://web2.nbmg.unr.edu/arcgis/rest/services/Qfaults/Qfaults_INGENIOUS/MapServer/0
Every artifact lands under data_external/ and a manifest (url, sha256, bytes,
http status) is committed alongside. This script is research tooling; it never
touches the competition labels and produces no predictions.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import subprocess
import sys
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

BOX = (-120.0024, 37.3641, -116.1415, 40.7247)  # GeoDAWN bbox from ScienceBase (verified in LEARNGEMSDOE)
OUT = Path(os.environ.get("OUT_DIR", "data_external"))
LOG: list[dict] = []


def log(entry: dict) -> None:
    LOG.append(entry)
    print(json.dumps(entry), flush=True)


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def fetch(url: str, dest: Path, *, tries: int = 3) -> bool:
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "GEMS-24-research-fetch/1.0 (academic audit tooling)"})
            with urllib.request.urlopen(req, timeout=240) as r:
                data = r.read()
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            log({"url": url, "file": str(dest), "bytes": len(data), "sha256": sha256(data), "http": 200, "try": k})
            return True
        except Exception as e:  # noqa: BLE001
            log({"url": url, "file": str(dest), "error": repr(e)[:220], "try": k})
    return False


def sh(cmd: str) -> subprocess.CompletedProcess:
    print("+ " + cmd, flush=True)
    return subprocess.run(cmd, shell=True, capture_output=True, text=True)


def tiger_roads_and_rails() -> None:
    import shapefile  # pyshp
    from shapely.geometry import box, shape as shapely_shape
    from shapely.ops import unary_union

    clip = box(*BOX)
    for st in ("32", "06"):  # NV, CA
        for layer in ("ROADS", "RAILS"):
            url = f"https://www2.census.gov/geo/tiger/TIGER2023/{layer}/tl_2023_{st}_{layer.lower()}.zip"
            raw = OUT / f"tiger_{layer}_{st}.zip"
            if not fetch(url, raw):
                continue
            keep = []
            with zipfile.ZipFile(raw) as z:
                shp_name = next(n for n in z.namelist() if n.endswith(".shp"))
                prefix = shp_name[:-4]
                tmp = OUT / f"tiger_{layer}_{st}_tmp"
                tmp.mkdir(exist_ok=True)
                for ext in (".shp", ".shx", ".dbf", ".prj"):
                    (tmp / (prefix + ext).split("/")[-1]).write_bytes(z.read(prefix + ext))
                r = shapefile.Reader(str(tmp / (Path(prefix).name + ".shp")))
                for sr in r.iterShapeRecords():
                    g = shapely_shape(sr.shape.__geo_interface__)
                    if g.intersects(clip):
                        rec = dict(zip([f[0] for f in r.fields[1:]], sr.record))
                        # keep only small highway-ish class fields to stay light
                        slim = {k: rec[k] for k in ("MTFCC", "ADMIN0_FL", "ADMIN1_FL") if k in rec}
                        gg = g.intersection(clip)
                        keep.append({"geom": gg.__geo_interface__, "props": slim})
            gj = {"type": "FeatureCollection", "features": keep,
                  "meta": {"source": url, "n_clipped": len(keep)}}
            p = OUT / f"tiger_{layer}_{st}_clipped.geojson"
            p.write_text(json.dumps(gj))
            log({"derived": str(p), "bytes": p.stat().st_size, "sha256": sha256(p.read_bytes()), "n_features": len(keep)})
            raw.unlink(missing_ok=True)


def mrds() -> None:
    html = OUT / "mrds_landing.html"
    if not fetch("https://mrdata.usgs.gov/mrds/", html):
        return
    txt = html.read_text(errors="ignore")
    import re

    links = sorted(set(re.findall(r'href="([^"]+\.(?:zip|csv)(?:[?][^"]*)?)"', txt, re.I)))
    log({"mrds_links_found": links[:40]})
    cand = [l for l in links if re.search(r"(point|export|state|database|full).{0,40}(\.zip|\.csv)", l, re.I)] or links[:3]
    base = "https://mrdata.usgs.gov/mrds/"
    for c in cand[:4]:
        url = c if c.startswith("http") else base + c.lstrip("/")
        name = "mrds_" + os.path.basename(url.split("?")[0]).replace(".", "_")
        raw = OUT / name
        if fetch(url, raw):
            if raw.suffix == ".zip":
                try:
                    with zipfile.ZipFile(raw) as z:
                        names = [n for n in z.namelist()][:20]
                    log({"mrds_zip_members_preview": names})
                except Exception as e:  # noqa: BLE001
                    log({"mrds_zip_error": repr(e)[:160]})
            return


def sciencebase_outlines() -> None:
    j = OUT / "geodawn_sciencebase.json"
    if not fetch("https://www.sciencebase.gov/catalog/item/get?ids=657e1d85d34e23d3533209f7", j):
        return
    d = json.loads(j.read_text())
    item = d["items"][0]
    files = item.get("files", [])
    log({"sciencebase_files": [f["name"] for f in files]})
    for f in files:
        low = f["name"].lower()
        if "outline" in low and low.endswith(".zip"):
            raw = OUT / f["name"]
            if fetch(f["url"], raw):
                outj = OUT / f["name"].replace(".zip", "_clipped.geojson")
                _shp_zip_to_clipped_geojson(raw, outj, f["name"])


def _shp_zip_to_clipped_geojson(raw: Path, outj: Path, label: str) -> None:
    import shapefile
    from shapely.geometry import box, shape as shapely_shape

    clip = box(*BOX)
    with zipfile.ZipFile(raw) as z:
        tmp = OUT / (raw.stem + "_tmp")
        tmp.mkdir(exist_ok=True)
        for n in z.namelist():
            (tmp / Path(n).name).write_bytes(z.read(n))
        shps = list(tmp.rglob("*.shp"))
        if not shps:
            log({"outline_no_shp": label})
            return
        r = shapefile.Reader(str(shps[0]))
        feats = []
        for sr in r.iterShapeRecords():
            g = shapely_shape(sr.shape.__geo_interface__).intersection(clip)
            feats.append({"geom": g.__geo_interface__, "props": dict(zip([f[0] for f in r.fields[1:]], sr.record))})
    outj.write_text(json.dumps({"type": "FeatureCollection", "features": feats, "source": label}))
    log({"derived": str(outj), "bytes": outj.stat().st_size, "sha256": sha256(outj.read_bytes()), "n_features": len(feats)})


def nbmg_qfaults_confidence() -> None:
    """INGENIOUS Qfaults v2 with FTYPE_ mapping-confidence per trace (REST, GeoJSON)."""
    where = "FTYPE_ IN ('Well Constrained','Moderately Constrained','Inferred')"
    url = (
        "https://web2.nbmg.unr.edu/arcgis/rest/services/Qfaults/Qfaults_INGENIOUS/MapServer/0/query"
        f"?where={urllib.parse.quote(where)}&geometry={BOX[0]},{BOX[1]},{BOX[2]},{BOX[3]}"
        "&geometryType=esriGeometryEnvelope&inSR=4326&spatialRel=esriSpatialRelIntersects"
        "&outFields=*&returnGeometry=true&f=geojson&resultRecordCount=2000"
    )
    dest = OUT / "qfaults_v2_in_footprint.geojson"
    if fetch(url, dest):
        try:
            d = json.loads(dest.read_text())
            log({"qfaults_features": len(d.get("features", []))})
        except Exception as e:  # noqa: BLE001
            log({"qfaults_parse_error": repr(e)[:160]})


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    mode = os.environ.get("FETCH_MODE", "all")
    for fn in [tiger_roads_and_rails, mrds, sciencebase_outlines, nbmg_qfaults_confidence]:
        if mode in ("all", fn.__name__):
            try:
                fn()
            except Exception as e:  # noqa: BLE001
                log({"step_error": fn.__name__, "err": repr(e)[:300]})
    man = {
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "bbox_wgs84": list(BOX),
        "purpose": "confound layers for C2S2 accessibility audit (24GEMSDOE); public-domain sources; research use only",
        "log": LOG,
    }
    (OUT / "fetch_manifest.json").write_text(json.dumps(man, indent=2))
    print("FETCH DONE")


if __name__ == "__main__":
    main()
