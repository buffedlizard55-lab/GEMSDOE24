#!/usr/bin/env python
"""Holdout gate, 24-style: raw vs accessibility-residualized emission, judged
with gems.holdout (the 19GEMSDOE convention: quadrant folds, 20%-thin
new-fault truth, per-quadrant top-budget emission). Nothing is submitted from
here; this decides what may be. Writes evidence/gate24.json and splices the
summary into evidence/geoaudit.json['gate_foldprotocol'].
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from gems import confounds as cf, footprint, holdout, paths  # noqa: E402
import run_geology_audit as A  # noqa: E402  (strat_id, within_stratum_rank)

TAGS = ("h19-4", "h19-5", "h16-1")


def main() -> None:
    t0 = time.time()
    fp = footprint.load_footprint()
    labf = footprint.load_band(paths.DATA_DIR / "bridge" / "labels.tif")
    lab_bin = np.nan_to_num(labf) > 0
    conf = np.load(cf.CONF / "confounds.npz")
    sid = A.strat_id(conf, [], fp)
    ho = holdout.Holdout(fp, lab_bin)
    out = {"generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "protocol": {"module": "gems.holdout", "budget": holdout.BUDGET_FRAC,
                        "note": "quadrant folds; within fold 20% of components held as 'new'; emission = per-quadrant top-budget"},
           "results": {}, "decision": {}}
    base_res = None
    for tag in TAGS:
        cand = sorted((ROOT / "inputs").glob(f"*{tag}*-nan.tif"))[-1]
        with rasterio.open(cand) as d:
            e = np.nan_to_num(d.read(1).astype(np.float32), nan=0.0)
        rk = A.within_stratum_rank(e, sid, fp)
        w = 0.5 + np.nan_to_num(rk, nan=0.5)
        new = e * w
        new = new * (float(e.sum()) / max(float(new.sum()), 1e-9))
        new = np.clip(new, 0.0, 1.0)
        for name, surf in ((f"{tag}-raw", e), (f"{tag}-resid", new)):
            p_fp = surf.ravel()[np.flatnonzero(fp.ravel())]
            r = ho.evaluate(p_fp, ridge=True)
            out["results"][name] = {k: r[k] for k in ("mean_dense_dti", "mean_sparse_dti", "fold_dense", "fold_sparse")}
            print(f"{name}: dense {r['mean_dense_dti']} sparse {r['mean_sparse_dti']}", flush=True)
            if name == "h19-4-raw":
                base_res = out["results"][name]
    for tag in TAGS:
        c = out["results"][f"{tag}-resid"]
        b = base_res
        out["decision"][tag] = {
            "beats_h19-4-raw_dense": bool(c["mean_dense_dti"] > b["mean_dense_dti"]),
            "beats_h19-4-raw_sparse": bool(c["mean_sparse_dti"] > b["mean_sparse_dti"]),
            "delta_dense": round(c["mean_dense_dti"] - b["mean_dense_dti"], 5),
            "delta_sparse": round(c["mean_sparse_dti"] - b["mean_sparse_dti"], 5),
            "worst_fold_dense": round(min(c["fold_dense"]) - min(b["fold_dense"]), 5),
        }
    paths.EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    (paths.EVIDENCE_DIR / "gate24.json").write_text(json.dumps(out, indent=2))
    ga = paths.EVIDENCE_DIR / "geoaudit.json"
    if ga.exists():
        d = json.loads(ga.read_text())
        d["gate_foldprotocol"] = {"results": out["results"], "decision": out["decision"], "protocol": out["protocol"]}
        ga.write_text(json.dumps(d, indent=2))
    print("DONE", round(time.time() - t0, 1), "s")
    print(json.dumps(out["decision"], indent=2))


if __name__ == "__main__":
    main()
