#!/usr/bin/env python
"""V1-clean: confounds WITHOUT the two INGENIOUS fault-distance layers
(d_wc_px/d_inf_px are catalogue geometry in disguise, so keeping them lets the
catalogue predict itself). Same protocol as the main audit. Appends to
evidence/geoaudit.json views as 'V1clean_*'."""
import json, sys, time
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT/"src")); sys.path.insert(0, str(ROOT/"scripts"))
from gems import c2s2, confounds as cf, footprint, paths
import run_geology_audit as A

fp, lab_bin, labf, known, conf, keys = A.load_env()
keys_clean = [k for k in keys if k not in ("d_wc_px", "d_inf_px")]
confd = A.conf_feats(conf, keys_clean)
fold = A.quadrant_fold(fp)
H, W = fp.shape
import rasterio
preds = []
for tag in ("h19-4", "h19-5", "h16-1"):
    cand = sorted((ROOT/"inputs").glob(f"*{tag}*-nan.tif"))[-1]
    with rasterio.open(cand) as d:
        preds.append(np.nan_to_num(d.read(1).astype(np.float32), nan=0.0))
emit = np.maximum.reduce(preds)
out = []
for refname, ref in (("labels", lab_bin.astype(bool)), ("pred_union", emit >= 0.3)):
    t0 = time.time()
    r = c2s2.c2s2_test(f"{refname}::V1clean", ref, confd, fold, fp, model_kind="hgb",
                       n_per_class=45_000, n_null=25, seed=20261001, null_mode="perm")
    d1 = r.as_dict(); d1["view"] = f"{refname}::V1clean_hgb"; d1["n_confounds"] = len(keys_clean)
    out.append(d1); print(json.dumps({k: d1[k] for k in ("view","observed_auc","p_value","margin_vs_p95")}), flush=True)
    r2 = c2s2.c2s2_test(f"{refname}::V1clean-shift", ref, confd, fold, fp, model_kind="hgb",
                        n_per_class=30_000, n_null=8, seed=20261001, null_mode="shift",
                        shift_fn=lambda dy, dx, ref=ref: A.torus_shift_mask(ref, dy, dx))
    d2 = r2.as_dict(); d2["view"] = f"{refname}::V1clean_shift"
    out.append(d2); print(json.dumps({k: d2[k] for k in ("view","observed_auc","p_value","margin_vs_p95")}), flush=True)
p = paths.EVIDENCE_DIR / "geoaudit.json"
full = json.loads(p.read_text())
full["views"] += out
full["v1clean_confounds"] = keys_clean
p.write_text(json.dumps(full, indent=2))
(ROOT/"docs"/"data"/"geoaudit.json").parent.mkdir(parents=True, exist_ok=True)
(ROOT/"docs"/"data"/"geoaudit.json").write_text(json.dumps(full, indent=2))
print("merged into geoaudit.json; DONE", round(time.time()-t0, 1), "s")
