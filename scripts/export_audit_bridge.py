#!/usr/bin/env python3
"""Export small derived receipts when the sandbox cannot reach Actions' blob host.

Run on CI after anonymous official-source fetching. Raw claims and flight paths
stay out of Git. Only a reproducible 100 m claim-distance raster and small USGS
acquisition documentation may be bridged onto the fixed Arena working branch.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
import shutil
import sys

import numpy as np
import rasterio
from rasterio.features import rasterize
from scipy.ndimage import distance_transform_edt
import shapefile
from shapely.geometry import shape
from shapely import make_valid

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data/raw/official_audit"
OUTPUT = ROOT / "data/external/audit_sources"
TRANSFORM = rasterio.transform.Affine(100,0,243350,0,-100,4508550)
PAD = 200  # 20 km: retain nearest sources outside the rectangular output grid


def quality_code(value):
    match = re.match(r"^\s*(\d+(?:\.\d+)?)", str(value))
    return float(match.group(1)) if match else None


def main():
    OUTPUT.mkdir(parents=True,exist_ok=True)
    receipt = json.loads((INPUT/"receipt.json").read_text())
    # Preserve the official document bytes, not just an interpretation of them.
    for name in ("GeoDAWN Metadata FINAL.csv", "GeoDAWN_ReadMe.pdf",
         "GeoDAWN_NV_WestCentral_Geophysical_2020_D21_Report.pdf", "GeoDAWN_data_extent.zip", "Figure1_index.PNG"):
        for suffix in ("", ".txt", ".inventory.json"):
            p=INPUT/(name+suffix)
            if p.exists() and p.stat().st_size < 10_000_000:
                shutil.copy2(p,OUTPUT/p.name)
    for p in INPUT.glob("*flight_path.zip.inventory.json"):
        shutil.copy2(p,OUTPUT/p.name)
    compact = {k:v for k,v in receipt.items() if k not in ("assets","claims")}
    compact["bridged_utc"] = datetime.now(timezone.utc).isoformat()
    compact["fetch_script_commit"] = "cda5a208fff34cc0c3f2cf98ffc5805a33a50466"
    compact["source_run"] = 36956856546
    compact["assets"] = []
    for asset in receipt["assets"]:
        a={k:v for k,v in asset.items() if k not in ("query_parameters",)}
        if a["file"].startswith("claims_page_"):
            # Thousands of live object IDs belong in the raw external receipt,
            # not a 20 MB report. Keep byte and complete-request hashes.
            a["request_sha256"]=hashlib.sha256(a["url"].encode()).hexdigest()
            a["url"]=a["url"].split("?")[0]
        compact["assets"].append(a)
    if "claims" in receipt:
        codes=Counter()
        for key,count in receipt["claims"]["quality_counts"].items():
            codes[str(quality_code(key))]+=count
        compact["claims"]={"count":receipt["claims"]["count"],"quality_code_case_counts":dict(codes),
            "disposition_counts":receipt["claims"]["disposition_counts"]}
    claims = INPUT/"blm_closed_claims.json"
    if claims.exists():
        d=json.loads(claims.read_text())
        if d.get("count_expected")!=d.get("count_received") or d.get("spatialReference",{}).get("wkid")!=32611:
            raise SystemExit("Refusing an incomplete/wrong-CRS claim bridge")
        seeds=np.zeros((3730+2*PAD,3292+2*PAD),np.uint8)
        burn_transform = TRANSFORM * rasterio.transform.Affine.translation(-PAD,-PAD)
        rejected=Counter()
        batch=[]
        accepted=0
        seen_geometries=set()
        for f in d["features"]:
            q=quality_code(f["attributes"].get("QLTY"))
            if q is None or q > 10 or f["attributes"].get("CSE_DISP") != "Closed":
                rejected["county_only" if q == 25 else "unknown_or_degraded_quality_or_not_closed"]+=1;continue
            rings=(f.get("geometry") or {}).get("rings")
            if not rings:
                rejected["missing_geometry"]+=1;continue
            # Esri shell/hole orientation is preserved by pyshp's polygon
            # conversion; do NOT assume every ring after the first is a hole.
            key=hashlib.sha256(json.dumps(rings,separators=(",", ":")).encode()).hexdigest()
            if key in seen_geometries:
                rejected["coincident_geometry_deduplicated"]+=1;continue
            seen_geometries.add(key)
            points=[xy for ring in rings for xy in ring]
            parts=np.cumsum([0]+[len(r) for r in rings[:-1]]).tolist()
            geometry=shapefile.Shape(shapeType=shapefile.POLYGON,points=points,parts=parts).__geo_interface__
            pg=shape(geometry)
            if not pg.is_valid:
                pg=make_valid(pg)
            if pg.is_empty or pg.area > 1e9:
                rejected["empty_or_broader_than_1000km2"]+=1;continue
            batch.append((pg.__geo_interface__,1));accepted+=1
            if len(batch)==1000:
                seeds |= rasterize(batch,out_shape=seeds.shape,transform=burn_transform,all_touched=True,dtype="uint8");batch=[]
        if batch:
            seeds |= rasterize(batch,out_shape=seeds.shape,transform=burn_transform,all_touched=True,dtype="uint8")
        if not seeds.any():
            raise SystemExit("No real claim geometry; cannot create a distance layer")
        dist=(distance_transform_edt(seeds==0)*100)[PAD:-PAD,PAD:-PAD].astype(np.float32)
        with rasterio.open(ROOT/"data/bridge/sample_submission.tif") as t:
            fp=np.isfinite(t.read(1));profile=t.profile.copy()
        if dist[fp].max() >= PAD*100:
            raise SystemExit("Claim-distance buffer is too short for this footprint")
        dist[~fp]=np.nan
        profile.update(dtype="float32",count=1,nodata=np.nan,compress="deflate",predictor=3)
        dst=OUTPUT/"blm_closed_claim_distance_m.tif"
        with rasterio.open(dst,"w",**profile) as s:s.write(dist,1)
        compact["claim_distance"]={"file":str(dst.relative_to(ROOT)),
            "sha256":hashlib.sha256(dst.read_bytes()).hexdigest(),
            "source_url":d["source"],"raw_sha256":hashlib.sha256(claims.read_bytes()).hexdigest(),
            "complete_id_check":True,"n_source_cases":d["count_received"],
            "accepted_unique_geometries":accepted,"rejected":dict(rejected),
            "quality_code_case_counts":compact["claims"]["quality_code_case_counts"],
            "disposition_case_counts":compact["claims"]["disposition_counts"],
            "quality_policy":"leading numeric QLTY code <=10; unknown/degraded/25 county-only excluded; broad geometries rejected",
            "seed_grid_buffer_m":PAD*100,
            "seed_pixels":int(seeds.sum()),"units":"metres on 100 m raster",
            "limitation":"PLSS legal-land approximations, often quarter-section precision; not exact historic claim stakes or workings"}
    (OUTPUT/"receipt.json").write_text(json.dumps(compact,indent=2)+"\n")
    print(json.dumps(compact.get("claim_distance",{"missing":"closed claims"}),indent=2))


if __name__=="__main__":main()
