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
from pathlib import Path
import shutil
import sys

import numpy as np
import rasterio
from rasterio.features import rasterize
from scipy.ndimage import distance_transform_edt
import shapefile

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data/raw/official_audit"
OUTPUT = ROOT / "data/external/audit_sources"
TRANSFORM = rasterio.transform.Affine(100,0,243350,0,-100,4508550)


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
    compact = {k:v for k,v in receipt.items() if k != "assets"}
    compact["assets"] = [{k:v for k,v in a.items() if k != "query_parameters"} for a in receipt["assets"]]
    claims = INPUT/"blm_closed_claims.json"
    if claims.exists():
        d=json.loads(claims.read_text())
        if d.get("count_expected")!=d.get("count_received") or d.get("spatialReference",{}).get("wkid")!=32611:
            raise SystemExit("Refusing an incomplete/wrong-CRS claim bridge")
        seeds=np.zeros((3730,3292),np.uint8)
        rejected=Counter()
        batch=[]
        accepted=0
        seen_geometries=set()
        for f in d["features"]:
            if str(f["attributes"].get("QLTY"))=="25":
                rejected["county_only"]+=1;continue
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
            batch.append((geometry,1));accepted+=1
            if len(batch)==1000:
                seeds |= rasterize(batch,out_shape=seeds.shape,transform=TRANSFORM,all_touched=True,dtype="uint8");batch=[]
        if batch:
            seeds |= rasterize(batch,out_shape=seeds.shape,transform=TRANSFORM,all_touched=True,dtype="uint8")
        if not seeds.any():
            raise SystemExit("No real claim geometry; cannot create a distance layer")
        dist=(distance_transform_edt(seeds==0)*100).astype(np.float32)
        with rasterio.open(ROOT/"data/bridge/sample_submission.tif") as t:
            fp=np.isfinite(t.read(1));profile=t.profile.copy()
        dist[~fp]=np.nan
        profile.update(dtype="float32",count=1,nodata=np.nan,compress="deflate",predictor=3)
        dst=OUTPUT/"blm_closed_claim_distance_m.tif"
        with rasterio.open(dst,"w",**profile) as s:s.write(dist,1)
        compact["claim_distance"]={"file":str(dst.relative_to(ROOT)),
            "sha256":hashlib.sha256(dst.read_bytes()).hexdigest(),
            "source_url":d["source"],"raw_sha256":hashlib.sha256(claims.read_bytes()).hexdigest(),
            "complete_id_check":True,"n_source_cases":d["count_received"],
            "accepted_unique_geometries":accepted,"rejected":dict(rejected),
            "quality_case_counts":d.get("quality_case_counts"),"disposition_case_counts":d.get("disposition_case_counts"),
            "seed_pixels":int(seeds.sum()),"units":"metres on 100 m raster",
            "limitation":"PLSS legal-land approximations, often quarter-section precision; not exact historic claim stakes or workings"}
    (OUTPUT/"receipt.json").write_text(json.dumps(compact,indent=2)+"\n")
    print(json.dumps(compact.get("claim_distance",{"missing":"closed claims"}),indent=2))


if __name__=="__main__":main()
