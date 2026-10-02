#!/usr/bin/env python
"""Geology-only view against the torus-shift null (apples-to-apples with V1clean)."""
import json, sys, time
from pathlib import Path
import numpy as np, rasterio
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT/"src")); sys.path.insert(0, str(ROOT/"scripts"))
from gems import c2s2, footprint, paths
import run_geology_audit as A

fp, lab_bin, labf, known, conf, keys = A.load_env()
H, W = fp.shape
geod = A.geology_feats(H, W)
fold = A.quadrant_fold(fp)
preds = []
for tag in ("h19-4", "h19-5", "h16-1"):
    with rasterio.open(sorted((ROOT/"inputs").glob(f"*{tag}*-nan.tif"))[-1]) as d:
        preds.append(np.nan_to_num(d.read(1).astype(np.float32), nan=0.0))
emit = np.maximum.reduce(preds)
out = []
for refname, ref in (("labels", lab_bin.astype(bool)), ("pred_union", emit >= 0.3)):
    t0=time.time()
    r = c2s2.c2s2_test(f"{refname}::V2shift", ref, geod, fold, fp, model_kind="hgb",
                       n_per_class=30_000, n_null=8, seed=20261001, null_mode="shift",
                       shift_fn=lambda dy, dx, ref=ref: A.torus_shift_mask(ref, dy, dx))
    d1 = r.as_dict(); d1["view"] = f"{refname}::Vgeology_shift"; out.append(d1)
    print(json.dumps({k: d1[k] for k in ("view","observed_auc","p_value","margin_vs_p95")}), round(time.time()-t0,1), flush=True)
p = paths.EVIDENCE_DIR / "geoaudit.json"
full = json.loads(p.read_text()); full["views"] += out
p.write_text(json.dumps(full, indent=2)); (ROOT/"docs"/"data"/"geoaudit.json").write_text(json.dumps(full, indent=2))
print("done")
