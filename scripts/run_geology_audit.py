#!/usr/bin/env python
"""Geology-vs-accessibility C2S2 audit, full-data edition (24GEMSDOE).

Distribution-shift test (Lopez-Paz & Oquab, ICLR 2017) distinguishing NEAR
(<=3 px, metric-kernel TP range) from FAR (>=9 px, >=300 m off every mapped
trace) pixels, spatially quadrant-blocked, permutation nulls (and torus-shift
nulls on the labels reference):

  V1 confounds-only  acquisition-window + distance proxies (probe/sinter/vent/
                     well) + lidar coverage — "can geologists get there?"
  V2 geology-only    the 19 competition bands + det_elev derivatives ONLY —
                     does "geology" alone separate near/far (survey-footprint
                     smuggling), and by how much MORE does V3 (geology+confounds)
                     beat V1 (increment)?
  Run on BOTH references: catalogue labels (premise) and our own emission
  rasters h19-4 / h19-5 / h16-1 (union) — if predictions are as explained by
  access as the labels are, the gain is mapping-process overfitting.

Second half: residualization. Emission rasters get within-stratum (acq_window x
road-distance quintile) rank reweighting (mass-preserving, [0,1], zstd tif,
unique 24GEMSDOE filename); gate = new-fault holdout DTI vs h19-4-as-emitted
using gems.metric.dti_components_exact with the 19-convention known-fault
masking. Writes evidence/geoaudit.json + docs/data/geoaudit.json.
Research tooling; nothing here leaks labels into a saved raster.
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

from gems import c2s2, confounds as cf, footprint, metric, paths  # noqa: E402
from gems import geofeatures as gf  # noqa: E402

GEAT = np.uint8  # geology stack quantized to 8 bits for RAM (order-preserving)
TAGS = ("h19-4", "h19-5", "h16-1")


def load_env():
    fp = footprint.load_footprint()
    labf = footprint.load_band(paths.DATA_DIR / "bridge" / "labels.tif", 1)          # float, NaN outside footprint
    knownb = footprint.load_band(paths.DATA_DIR / "bridge" / "existing_faults.tif", 1)
    conf = np.load(cf.CONF / "confounds.npz")
    keys = [k for k in ("acq_window", "acq_block", "d_road_px", "d_claim_px", "d_probe_px", "d_sinter_px", "d_vent_px", "d_well_px", "lidar_cov")
            if k in conf.files]
    lab_bin = (np.nan_to_num(labf) > 0).astype(np.uint8)
    known = (np.nan_to_num(knownb) > 0)
    return fp, lab_bin, labf, known, conf, keys


def conf_feats(conf, keys) -> dict[str, np.ndarray]:
    return {k: np.asarray(conf[k], np.float32) for k in keys}


def geology_feats(H: int, W: int) -> dict[str, np.ndarray]:
    stack, feats, _ = gf.open_stack()
    return {f"geo_{nm}": (np.asarray(stack[:, i], np.uint16) >> 8).astype(np.uint8).reshape(H, W)
            for i, nm in enumerate(feats)}


def quadrant_fold(fp: np.ndarray) -> np.ndarray:
    H, W = fp.shape
    yy, xx = np.mgrid[0:H, 0:W]
    fold = ((yy * 2 // H) + (xx * 2 // W) * 2).clip(0, 3).astype(np.int8)
    fold[~fp] = -1
    return fold


def torus_shift_mask(mask: np.ndarray, dy: int, dx: int) -> np.ndarray:
    return np.roll(np.roll(mask, dy, axis=0), dx, axis=1)


def strat_id(conf, keys, fp: np.ndarray) -> np.ndarray:
    """acq_window (0..2) x quintile of the best available access-distance layer."""
    w = np.asarray(conf["acq_window"], np.int64) if "acq_window" in conf.files else np.zeros(fp.shape, np.int64)
    dkey = next((k for k in ("d_road_px", "d_claim_px", "d_probe_px") if k in conf.files), None)
    q = np.zeros(fp.shape, np.int64)
    if dkey:
        d = np.asarray(conf[dkey], np.float32)
        qs = np.quantile(d[fp], [0.2, 0.4, 0.6, 0.8])
        q = (np.searchsorted(qs, d.ravel(), side="right").reshape(fp.shape) if d.ndim == 2 else 0)
    return (w * 5 + q).astype(np.int64)


def within_stratum_rank(vals2d: np.ndarray, strata2d: np.ndarray, fp: np.ndarray) -> np.ndarray:
    rows = np.flatnonzero(fp.ravel())
    v = vals2d.ravel()[rows].astype(np.float64)
    s = strata2d.ravel()[rows]
    order = np.lexsort((v, s))
    ss = s[order]
    starts = np.r_[0, np.flatnonzero(ss[1:] != ss[:-1]) + 1]
    grp = np.searchsorted(starts, np.arange(len(ss)), side="right") - 1
    rank = np.arange(len(ss)) - starts[grp]
    counts = np.r_[np.diff(starts), len(ss) - starts[-1]].astype(np.float64)
    frac = rank / np.maximum(counts[grp] - 1.0, 1.0)
    out = np.full(vals2d.size, np.nan)
    out[rows[order]] = frac
    return out.reshape(vals2d.shape)


def run_views(ref_name: str, reference: np.ndarray, confd: dict, geod: dict, fold: np.ndarray,
              fp: np.ndarray, npc: int, seed: int, with_shift: bool) -> list[dict]:
    out = []
    combos = [("confounds", confd, 41), ("geology", geod, 16), ("geology+confounds", {**confd, **geod}, 16)]
    npc_hgb = min(npc, 45_000)
    for vname, feats, n_null in combos:
        t0 = time.time()
        r = c2s2.c2s2_test(f"{ref_name}::{vname}", reference, feats, fold, fp,
                           model_kind="hgb", n_per_class=npc_hgb, n_null=n_null, seed=seed, null_mode="perm")
        d = r.as_dict()
        d["view"], d["secs"] = f"{ref_name}::V{vname}_hgb", round(time.time() - t0)
        out.append(d)
        print(json.dumps({k: d[k] for k in ("view", "observed_auc", "p_value", "margin_vs_p95")}), flush=True)
        if vname == "confounds":
            rl = c2s2.c2s2_test(f"{ref_name}::confounds-logit", reference, feats, fold, fp,
                                model_kind="logit", n_per_class=npc, n_null=41, seed=seed, null_mode="perm")
            dl = rl.as_dict()
            dl["view"] = f"{ref_name}::V1_logit"
            out.append(dl)
            print(json.dumps({k: dl[k] for k in ("view", "observed_auc", "p_value", "margin_vs_p95")}), flush=True)
        if vname == "geology":
            rg = c2s2.c2s2_test(f"{ref_name}::geology-logit", reference, feats, fold, fp,
                                model_kind="logit", n_per_class=npc, n_null=25, seed=seed, null_mode="perm")
            dg = rg.as_dict()
            dg["view"] = f"{ref_name}::V2_logit"
            out.append(dg)
            print(json.dumps({k: dg[k] for k in ("view", "observed_auc", "p_value", "margin_vs_p95")}), flush=True)
    if with_shift:  # torus-shift null on labels reference (spatially structured)
        def shift_fn(dy, dx):
            return torus_shift_mask(reference, dy, dx)
        r = c2s2.c2s2_test(f"{ref_name}::confounds", reference, confd, fold, fp,
                           model_kind="hgb", n_per_class=npc, n_null=12, seed=seed,
                           null_mode="shift", shift_fn=shift_fn)
        d = r.as_dict()
        d["view"] = f"{ref_name}::V1_shift"
        out.append(d)
        print(json.dumps({k: d[k] for k in ("view", "observed_auc", "p_value", "margin_vs_p95")}), flush=True)
    # drop-one for the confounds view (labels only, cheap & informative)
    if with_shift:
        for k in sorted(confd):
            sub = {kk: v for kk, v in confd.items() if kk != k}
            r = c2s2.c2s2_test(f"drop::{k}", reference, sub, fold, fp, model_kind="logit",
                                n_per_class=npc, n_null=1, seed=seed, null_mode="perm")
            d = r.as_dict()
            d.pop("info", None)
            d["view"] = f"{ref_name}::drop1-{k}"
            out.append(d)
            print(json.dumps({k2: d[k2] for k2 in ("view", "observed_auc")}), flush=True)
    return out


def main() -> None:
    t0 = time.time()
    fp, lab_bin, labf, known, conf, keys = load_env()
    known_or_label = known
    H, W = fp.shape
    fold = quadrant_fold(fp)
    confd = conf_feats(conf, keys)
    geod = geology_feats(H, W)
    preds = {}
    for tag in TAGS:
        cands = sorted((ROOT / "inputs").glob(f"*{tag}*-nan.tif"))
        if not cands:
            raise SystemExit(f"missing input raster for {tag}")
        with rasterio.open(cands[-1]) as d:
            preds[tag] = np.nan_to_num(d.read(1).astype(np.float32), nan=0.0)
        report_inputs = None
    emit_union = np.maximum.reduce([preds[t] for t in TAGS])
    report = {"generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              "confound_names": keys, "n_geology": len(geod), "views": [], "resid": {}, "gate": {},
              "inputs": {t_: sorted((ROOT / "inputs").glob(f"*{t_}*-nan.tif"))[0].name for t_ in TAGS}}

    near_ref = lab_bin.astype(bool)
    report["views"] += run_views("labels", near_ref, confd, geod, fold, fp, 60_000, 20261001, True)
    pred_ref = emit_union >= 0.3
    report["views"] += run_views("pred_union", pred_ref, confd, geod, fold, fp, 60_000, 20261002, False)
    (paths.EVIDENCE_DIR / "geoaudit_partial.json").write_text(json.dumps(report, indent=2))

    # increments (V3 over V1) per reference
    byv = {(d["view"]): d for d in report["views"]}
    report["increments"] = {}
    for ref in ("labels", "pred_union"):
        try:
            v1 = byv[f"{ref}::Vconfounds_hgb"]["observed_auc"]
            v2 = byv[f"{ref}::Vgeology_hgb"]["observed_auc"]
            v3 = byv[f"{ref}::Vgeology+confounds_hgb"]["observed_auc"]
            report["increments"][ref] = {"V1": v1, "V2": v2, "V3": v3, "V3_minus_V1": round(v3 - v1, 5),
                                         "V1_p": byv[f"{ref}::Vconfounds_hgb"]["p_value"],
                                         "V2_p": byv[f"{ref}::Vgeology_hgb"]["p_value"]}
        except Exception as e:  # noqa: BLE001
            report["increments"][ref] = {"error": repr(e)[:200]}
    print("increments:", json.dumps(report["increments"]), flush=True)
    # ---------------- residualized emission surfaces + holdout gate ----------------
    sid = strat_id(conf, keys, fp)
    valid = np.isfinite(labf) & fp
    gap_truth = (np.nan_to_num(labf) > 0) & ~known  # NEW faults only (labels minus existing catalogue)
    base = preds["h19-4"]
    def score(p2d: np.ndarray) -> dict:
        return metric.dti_components_exact(pred=p2d, truth=gap_truth.astype(np.float64),
                                           valid_mask=valid & ~known_or_label,
                                           catalogue_mask=known_or_label, mask_predictions=True)
    g0 = score(base)
    report["gate"]["h19-4-as-emitted"] = {k: round(v, 5) for k, v in g0.items() if isinstance(v, float)}
    for tag in TAGS:
        rk = within_stratum_rank(preds[tag], sid, fp)
        w = 0.5 + np.nan_to_num(rk, nan=0.5)
        emit = preds[tag]
        mass0 = float(emit.sum())
        new = emit * w
        new = new * (mass0 / max(float(new.sum()), 1e-9))
        new = np.where(fp & (new > 1e-6), np.clip(new, 0.0, 1.0), np.nan).astype(np.float32)
        s = score(np.nan_to_num(new, nan=0.0))
        outp = ROOT / "out" / f"gems24-{tag}-resid-rank-UTM11N-float32.tif"
        outp.parent.mkdir(exist_ok=True)
        with rasterio.open(outp, "w", **footprint_profile(H, W)) as d:
            d.write(new, 1)
        report["resid"][tag] = {"path": str(outp.relative_to(ROOT)), "sha256": metric_sha(outp)}
        report["gate"][f"{tag}-resid"] = {k: round(v, 5) for k, v in s.items() if isinstance(v, float)}
        raw = score(emit)
        report["gate"][f"{tag}-raw"] = {k: round(v, 5) for k, v in raw.items() if isinstance(v, float)}
        print(f"gate {tag}: raw {raw['dti']:.4f} resid {s['dti']:.4f} (h19-4 {g0['dti']:.4f})", flush=True)
    report["decision"] = {
        f"{tag}_beats_h194": bool(report["gate"][f"{tag}-resid"]["dti"] > report["gate"]["h19-4-as-emitted"]["dti"])
        for tag in TAGS}
    txt = json.dumps(report, indent=2)
    (paths.EVIDENCE_DIR / "geoaudit.json").write_text(txt)
    (ROOT / "docs" / "data" / "geoaudit.json").parent.mkdir(parents=True, exist_ok=True)
    (ROOT / "docs" / "data" / "geoaudit.json").write_text(txt)
    print("DONE", round(time.time() - t0, 1), "s")


def footprint_profile(H: int, W: int) -> dict:
    import rasterio
    from gems.footprint import CRS, TRANSFORM
    return dict(driver="GTiff", width=W, height=H, count=1, dtype="float32", crs=CRS,
                transform=TRANSFORM, nodata=np.nan, compress="zstd", tiled=True)


def metric_sha(p: Path) -> str:
    import hashlib
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()[:16]


if __name__ == "__main__":
    main()
