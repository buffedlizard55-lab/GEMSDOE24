#!/usr/bin/env python3
"""Anonymous official-source acquisition; run locally or on GitHub-hosted CI.

No GitHub writes, no tokens, no new branches. Each asset/failed request gets a
receipt. Large flight paths are summarized and omitted from the uploaded bundle.
BLM full closed-claims layer is used, not MRDS occurrences or the HUB last-year
subset. Only public geospatial attributes needed for this audit are retained.
"""
from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import hashlib
import io
import json
from pathlib import Path
import re
import time
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timezone

SB = "https://www.sciencebase.gov/catalog/item/657e1d85d34e23d3533209f7?format=json"
BLM = "https://gis.blm.gov/nlsdb/rest/services/Mining_Claims/MiningClaims/MapServer/2"
BOX = (-120.5, 37.0, -115.9, 41.0)  # Buffered bounding box, not scoring-footprint claim.


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=Path("data/raw/official_audit"))
    ap.add_argument("--flight-paths", action="store_true")
    args = ap.parse_args()
    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    receipt = {"generated_utc": datetime.now(timezone.utc).isoformat(), "assets": [], "errors": []}

    def fetch(url: str, name: str) -> bytes:
        req = urllib.request.Request(url, headers={"User-Agent": "GEMS-reproducible-source-audit/2.0"})
        data = None
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=240) as r:
                    if r.status != 200:
                        raise ValueError(f"HTTP {r.status}")
                    data = r.read()
                break
            except Exception:
                if attempt == 2:
                    raise
                time.sleep(2 ** attempt)
        (out / name).write_bytes(data)
        receipt["assets"].append({"file": name, "url": url, "bytes": len(data),
                                   "sha256": hashlib.sha256(data).hexdigest()})
        return data

    def safe(job, name: str) -> None:
        try:
            job()
        except Exception as e:
            receipt["errors"].append({"operation": name, "error": str(e)[:300]})
            print(name, str(e), flush=True)
        (out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")

    def claims() -> None:
        meta = json.loads(fetch(BLM + "?f=json", "blm_closed_metadata.json"))
        if "error" in meta or meta.get("name") != "Closed Mining Claims":
            raise ValueError("Unexpected BLM layer; no substitute used")
        fields = {f["name"] for f in meta["fields"]}
        oid = meta.get("objectIdField") or next(f["name"] for f in meta["fields"] if f["type"] == "esriFieldTypeOID")
        params = {"f": "json", "where": "QLTY <> 25", "geometry": ",".join(map(str, BOX)),
                  "geometryType": "esriGeometryEnvelope", "inSR": "4326", "spatialRel": "esriSpatialRelIntersects"}
        def url(extra):
            return BLM + "/query?" + urllib.parse.urlencode({**params, **extra})
        ids = json.loads(fetch(url({"returnIdsOnly": "true"}), "blm_closed_ids.json"))
        if "error" in ids:
            raise ValueError(ids["error"])
        object_ids = sorted(ids.get("objectIds") or [])
        if not object_ids:
            raise ValueError("No closed claims returned in buffered study bbox")
        wanted = [f for f in (oid, "CSE_DISP", "QLTY", "CSE_TYPE_NR") if f in fields]
        def page(offset):
            extra = {"outFields": ",".join(wanted), "returnGeometry": "true", "outSR": "32611",
                     "maxAllowableOffset": "25", "resultOffset": offset,
                     "resultRecordCount": "2000", "orderByFields": oid + " ASC"}
            name = f"claims_page_{offset//2000:04}.json"
            result = json.loads(fetch(url(extra), name))
            if result.get("error"):
                raise ValueError(result["error"])
            if result.get("spatialReference", {}).get("wkid") != 32611:
                raise ValueError("BLM did not return requested UTM 11N coordinates")
            (out / name).unlink()
            return result.get("features", [])
        seen, geoms = set(), {}
        quality, dispositions = Counter(), Counter()
        with ThreadPoolExecutor(max_workers=8) as ex:
            for features in ex.map(page, range(0,len(object_ids),2000)):
                for f in features:
                    attrs = f["attributes"]; identifier = attrs[oid]
                    if identifier in seen:
                        raise ValueError("Duplicate BLM object ID across pages")
                    seen.add(identifier)
                    quality[str(attrs.get("QLTY"))] += 1
                    dispositions[str(attrs.get("CSE_DISP"))] += 1
                    if f.get("geometry"):
                        key = hashlib.sha256(json.dumps(f["geometry"],sort_keys=True).encode()).hexdigest()
                        geoms.setdefault(key,f)
                print("BLM cases received",len(seen),"/",len(object_ids),flush=True)
        if seen != set(object_ids):
            raise ValueError("BLM case-ID completeness check failed; live service may have changed")
        result = {"source":BLM,"spatialReference":{"wkid":32611},"features":list(geoms.values()),
                  "count_expected":len(object_ids),"count_received":len(seen),"unique_geometry_count":len(geoms),
                  "server_filter":"QLTY <> 25 (exclude county-only geocodes)",
                  "quality_case_counts":dict(quality),"disposition_case_counts":dict(dispositions),
                  "precision_warning":"Deduplicated PLSS legal-land polygons, NOT surveyed claim boundaries; missing geometries are not imputed"}
        p = out / "blm_closed_claims.json"
        p.write_text(json.dumps(result,separators=(",",":")))
        receipt["claims"] = {"count":len(seen),"unique_geometries":len(geoms),"quality_counts":dict(quality),
                             "disposition_counts":dict(dispositions),"assembled_sha256":hashlib.sha256(p.read_bytes()).hexdigest()}

    def geodawn() -> None:
        item = json.loads(fetch(SB, "geodawn_item.json"))
        files = item.get("files", [])
        wanted = ["GeoDAWN Metadata FINAL.csv", "GeoDAWN_ReadMe.pdf",
                  "GeoDAWN_NV_WestCentral_Geophysical_2020_D21_Report.pdf", "GeoDAWN_data_extent.zip", "Figure1_index.PNG"]
        if args.flight_paths:
            wanted += ["area1_flight_path.zip", "area2_flight_path.zip"]
        found = {}
        for name in wanted:
            record = next((f for f in files if f.get("name") == name), None)
            if record is None:
                receipt["errors"].append({"operation": "geodawn_file", "error": f"not attached: {name}"})
                continue
            raw = fetch(record["url"], name)
            found[name] = record["url"]
            if name.endswith(".pdf"):
                from pypdf import PdfReader
                text = "\n\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(raw)).pages)
                (out / (name + ".txt")).write_text(text)
            if name.endswith(".zip"):
                import shapefile
                with zipfile.ZipFile(io.BytesIO(raw)) as z:
                    names = z.namelist()
                    stems = [n[:-4] for n in names if n.endswith(".shp")]
                    summary = []
                    for stem in stems:
                        reader = shapefile.Reader(shp=io.BytesIO(z.read(stem + ".shp")),
                                                  shx=io.BytesIO(z.read(stem + ".shx")),
                                                  dbf=io.BytesIO(z.read(stem + ".dbf")))
                        flds = [f[0] for f in reader.fields[1:]]
                        cnt = {f: Counter() for f in flds}
                        for rec in reader.iterRecords():
                            for f, v in zip(flds, rec):
                                # Cap high-cardinality values; do not silently infer block membership.
                                if len(cnt[f]) < 10000:
                                    cnt[f][str(v)] += 1
                        summary.append({"shapefile": stem, "bbox": list(reader.bbox), "fields": flds,
                                        "n": len(reader), "attributes": {f: dict(c) for f, c in cnt.items()}})
                    (out / (name + ".inventory.json")).write_text(json.dumps(summary, indent=2))
                if "flight_path" in name:
                    (out / name).unlink()  # Do not upload large redundant flight geometries.
        receipt["geodawn_files"] = found

    safe(claims, "closed_claims")
    safe(geodawn, "geodawn")
    print(json.dumps(receipt, indent=2))
    # Partial data are retained for review, but cannot be mistaken for success.
    if receipt["errors"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
