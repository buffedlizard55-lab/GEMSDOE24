#!/usr/bin/env python3
"""
H24-SIGNED-CGMAG prototype: signed gravity-magnetic cross-gradient reversal + terrain.
Attempts to beat S3DEP1 0.16606 via orthogonal geophysical geometry.
"""
from __future__ import annotations
import json, sys, time, hashlib
from pathlib import Path
import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt, gaussian_filter
from sklearn.ensemble import HistGradientBoostingClassifier
from threadpoolctl import threadpool_limits

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"src"))
from gems import footprint, holdout, novelty, submission
from gems.validator import sha256_file

BUDGET_TOTAL = 37654
SEED = 20261027
TEMPLATE = ROOT/"data/bridge/sample_submission.tif"
LABELS = ROOT/"data/bridge/labels.tif"
PREP_META = ROOT/"data/prepared/features.json"
PREP_NPY = ROOT/"data/prepared/features.npy"

def save_json(o,p:Path):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(o, indent=2, allow_nan=False)+"\n")

def build_signed_crossgrad(rtp, grav, det_elev, fp):
    """Compute signed cross-gradient c and its along-terrain reversal."""
    # Fill NaN with nearest for gradient compute
    def fill(a):
        a = np.asarray(a, dtype=np.float32)
        mask = np.isfinite(a) & fp
        if not mask.any():
            return np.zeros_like(a)
        # simple fill via distance_transform_edt nearest
        idx = distance_transform_edt(~mask, return_indices=True, return_distances=False)
        filled = a[tuple(idx)]
        filled[~fp] = 0
        return filled
    rtp_f = fill(rtp)
    grav_f = fill(grav)
    elev_f = fill(det_elev)
    # Smooth at two scales
    def grad(field, sigma):
        sm = gaussian_filter(field, sigma) if sigma>0 else field
        gy,gx = np.gradient(sm, 100) # 100m per px
        return gx, gy
    gx_r1, gy_r1 = grad(rtp_f, 1.2)
    gx_g1, gy_g1 = grad(grav_f, 1.2)
    gx_r3, gy_r3 = grad(rtp_f, 3.0)
    gx_g3, gy_g3 = grad(grav_f, 3.0)
    # magnitude
    def cross_signed(gx1, gy1, gx2, gy2):
        mag1 = np.hypot(gx1, gy1)
        mag2 = np.hypot(gx2, gy2)
        denom = mag1*mag2 + 1e-6
        c = (gx1*gy2 - gy1*gx2) / denom
        return np.clip(c, -1, 1)
    c1 = cross_signed(gx_r1, gy_r1, gx_g1, gy_g1)
    c3 = cross_signed(gx_r3, gy_r3, gx_g3, gy_g3)
    # terrain tangent from det_elev structure tensor (simplified: gradient direction)
    gx_e, gy_e = grad(elev_f, 1.2)
    # tangent = perpendicular to gradient
    # We'll compute directional derivative of c along terrain tangent
    # tangent vector = (-gy_e, gx_e) normalized
    mag_e = np.hypot(gx_e, gy_e) + 1e-6
    tx = -gy_e / mag_e
    ty = gx_e / mag_e
    # directional derivative of c via gradient of c
    gc1y, gc1x = np.gradient(c1)
    gc3y, gc3x = np.gradient(c3)
    # along-tangent change (approx reversal = magnitude of tx*dc/dx + ty*dc/dy)
    # To capture reversal, compute second difference across 600m baseline: use smoothed c and difference
    # Simpler: compute absolute directional derivative
    d1 = np.abs(tx*gc1x + ty*gc1y)
    d3 = np.abs(tx*gc3x + ty*gc3y)
    # Also signed cross-gradient magnitude for baseline
    # Return channels: c1, c3, d1, d3, plus terrain slope
    slope = np.hypot(gx_e, gy_e)
    return {"c1": c1.astype(np.float32), "c3": c3.astype(np.float32), "d1": d1.astype(np.float32), "d3": d3.astype(np.float32), "slope": slope.astype(np.float32)}

def main():
    t0=time.monotonic()
    fp=footprint.load_footprint()
    fp_ids=np.flatnonzero(fp.ravel())
    with rasterio.open(LABELS) as ds:
        catalogue=(ds.read(1)>0) & fp
    meta=json.loads(PREP_META.read_text())
    base_mm=np.load(PREP_NPY, mmap_mode="r")
    base_names=list(meta["names"])
    # Build 2D grids for needed layers
    def to2d(vec):
        g=np.full(fp.shape, np.nan, dtype=np.float32)
        g.ravel()[fp_ids]=vec
        return g
    rtp_idx=base_names.index("rtp")
    grav_idx=base_names.index("iso_grav_anom")
    elev_idx=base_names.index("det_elev")
    rtp2d=to2d(base_mm[:,rtp_idx])
    grav2d=to2d(base_mm[:,grav_idx])
    elev2d=to2d(base_mm[:,elev_idx])
    sg = build_signed_crossgrad(rtp2d, grav2d, elev2d, fp)
    print(f"Signed cross-grad built: c1 mean {np.nanmean(sg['c1']):.4f} d1 mean {np.nanmean(sg['d1']):.4f}")
    # Stack extra channels onto base_mm for training: we have 30 base + 5 new =35
    # Create extended mm in memory (5M x 35 float32 ~700MB — too large). Instead create per-fold extended features on fly? Simpler: create memmap for extended
    # We'll create extended npy memmap
    ext_path=ROOT/"data/prepared/new_unique_v3.npy"
    ext_meta_path=ROOT/"data/prepared/new_unique_v3.json"
    n_fp=len(fp_ids); n_base=30; n_new=5; n_tot=n_base+n_new
    # Build extended memmap if not exists or force
    if not ext_path.exists() or ext_path.stat().st_size != n_fp*n_tot*4:
        print("Building extended memmap 35ch...")
        mm=np.memmap(ext_path, dtype=np.float32, mode="w+", shape=(n_fp, n_tot))
        mm[:,:n_base]=base_mm[:]
        # fill new channels
        new_names=["c1_cgmag","c3_cgmag","d1_reversal","d3_reversal","terrain_slope"]
        for i,k in enumerate(new_names):
            # mapping from new name to sg key
            key_map={"c1_cgmag":"c1","c3_cgmag":"c3","d1_reversal":"d1","d3_reversal":"d3","terrain_slope":"slope"}
            a2d=sg[key_map[k]]
            mm[:, n_base+i]=a2d.ravel()[fp_ids]
        mm.flush(); del mm
        save_json({"names": base_names+new_names, "n_fp": n_fp, "sha256": sha256_file(ext_path)}, ext_meta_path)
        print(f"Extended saved {ext_path} sha {sha256_file(ext_path)[:12]}")
    else:
        print("Extended memmap exists")
    meta_ext=json.loads(ext_meta_path.read_text())
    ext_names=meta_ext["names"]
    ext_mm=np.memmap(ext_path, dtype=np.float32, mode="r", shape=(n_fp, n_tot))
    # Holdout context
    context=holdout.SegmentHoldout(fp, catalogue, buffer_px=15)
    print(f"Folds {len(context.folds)}")
    total_offcat=int((fp & ~catalogue).sum())
    preds=[]
    oof=np.zeros(fp.shape, dtype=np.float32)
    # Train per fold
    for fold in context.folds:
        fid=fold["id"]
        dist_vis=distance_transform_edt(~fold["visible"])
        pos_mask=fold["train"] & fold["visible"]
        neg_mask=fold["train"] & ~fold["visible"] & (dist_vis>=9)
        pos_ids=np.flatnonzero(pos_mask.ravel()[fp_ids])
        neg_ids=np.flatnonzero(neg_mask.ravel()[fp_ids])
        rng=np.random.default_rng(SEED+fid)
        n_pos=min(15000,len(pos_ids)); n_neg=min(45000,len(neg_ids))
        pos_sel=rng.choice(pos_ids, n_pos, replace=False); neg_sel=rng.choice(neg_ids, n_neg, replace=False)
        tr_sel=np.r_[pos_sel,neg_sel]; y_tr=np.r_[np.ones(n_pos,dtype=np.int8), np.zeros(n_neg,dtype=np.int8)]
        x_tr=np.asarray(ext_mm[tr_sel], dtype=np.float32)
        x_tr=np.where(np.isfinite(x_tr), x_tr, 0)
        with threadpool_limits(limits=2):
            clf=HistGradientBoostingClassifier(max_iter=80, max_leaf_nodes=15, learning_rate=0.08, l2_regularization=5.0, early_stopping=False, random_state=SEED+fid)
            clf.fit(x_tr,y_tr)
        val_ids=np.flatnonzero(fold["valid"].ravel()[fp_ids])
        surf=np.zeros(len(val_ids), dtype=np.float32)
        for s in range(0,len(val_ids),150000):
            ch=val_ids[s:s+150000]
            x_ch=np.asarray(ext_mm[ch], dtype=np.float32)
            x_ch=np.where(np.isfinite(x_ch), x_ch, 0)
            surf[s:s+len(ch)]=clf.predict_proba(x_ch)[:,1]
        oof.ravel()[fp_ids[val_ids]]=np.maximum(oof.ravel()[fp_ids[val_ids]], surf)
        # emit for holdout eval
        f_offcat=int((fold["valid"] & ~fold["visible"]).sum())
        k_fold=int(round(BUDGET_TOTAL * f_offcat/total_offcat))
        score_grid=np.zeros(fp.shape, dtype=np.float32)
        score_grid.ravel()[fp_ids[val_ids]]=surf
        eligible=fold["valid"] & ~fold["visible"]
        from gems.emission import priority_poisson
        pred=priority_poisson(score_grid, eligible, k_fold, min_dist=3)
        preds.append(pred.astype(np.uint8))
        print(f"Fold {fold['name']} k={k_fold} dti pending")
    summary=context.summarize(preds, ci_draws=1999)
    print(f"HOLDOUT-DTI {summary['dti']:.5f} CI {summary['ci95']['interval']}")
    # final
    eligible_final=fp & ~catalogue
    from gems.emission import priority_poisson
    final_pred=priority_poisson(oof, eligible_final, BUDGET_TOTAL, min_dist=3)
    print(f"Final dots {final_pred.sum()}")
    # novelty
    priority_reg=json.loads((ROOT/"registry/priority_rasters_20261026_portfolio.json").read_text())
    pre_nov=novelty.compare_prospective_registry(oof, fp, priority_reg["unique_rasters"], ROOT, sample_size=200000)
    final_nov=novelty.compare_prospective_registry(oof, fp, priority_reg["unique_rasters"], ROOT, dots=final_pred, sample_size=200000)
    print(f"Pre method_passed {pre_nov['method_lane_passed']} max_rho {pre_nov['method_lane_max_abs_rank_correlation']:.4f}")
    print(f"Final method_passed {final_nov['method_lane_passed']} max_overlap {final_nov['method_lane_max_dot_overlap']:.4f} literal {final_nov['literal_all_entries_passed']}")
    # lattice overlap
    lattice_path=ROOT/"inputs/calibration/13gems_20261001_r13-lattice-s5_v2_nan-outside.tif"
    with rasterio.open(lattice_path) as ds:
        lat=ds.read(1)>0
    lat_fp=lat & fp
    from scipy.spatial import cKDTree
    lat_yx=np.argwhere(lat_fp); cand_yx=np.argwhere(final_pred & fp)
    if len(lat_yx) and len(cand_yx):
        tree=cKDTree(lat_yx)
        overlap=float(np.mean(tree.query(cand_yx)[0]<=3))
        print(f"Lattice overlap {overlap:.4f}")
    else:
        overlap=None
    # write tif
    content_id=submission.scored_content_id(final_pred, fp, catalogue)
    slug="signed-cgmag-reversal-hgb" if final_nov["method_lane_passed"] else "signed-cgmag-negative"
    zeros_name=submission.make_filename("gems24", slug, "20261027", content_id, "zeros")
    nan_name=submission.make_filename("gems24", slug, "20261027", content_id, "nan")
    downloads=ROOT/"docs/downloads"
    zeros_path=submission.write_submission(final_pred.astype(np.float32), TEMPLATE, downloads/zeros_name, outside="zero")
    nan_path=submission.write_submission(final_pred.astype(np.float32), TEMPLATE, downloads/nan_name, outside="nan")
    zip_path=submission.zip_single(zeros_path, downloads/zeros_name.replace(".tif",".zip"))
    zero_checks=submission.check_variants(zeros_path, TEMPLATE)
    print(f"SHA {zero_checks['sha256']} dots {final_pred.sum()} holdout {summary['dti']:.5f}")
    # run card
    note=f"GEMS24 SIGNED-CGMAG | K={BUDGET_TOTAL} | id {content_id} | HOLDOUT-DTI {summary['dti']:.4f} | research; see executive guide"
    if len(note)>140: note=note[:140]
    note_file=f"note-{zeros_name[:-4]}.txt"
    (downloads/note_file).write_text(note+"\n")
    save_json({"zero_outside": zero_checks, "nan_outside": submission.check_variants(nan_path, TEMPLATE)}, downloads/f"checks-{zeros_name[:-4]}.json")
    run_card={
        "lane_id": "H24-SIGNED-CGMAG",
        "hypothesis": "Signed gravity-magnetic cross-gradient reversal across terrain tangent",
        "mechanism": "Oblique buried splay rotates relative orientation of RTP vs gravity gradients; signed c reversal along terrain fabric marks it",
        "non_fault_mimic": "Intrusive contact or GeoDAWN seam",
        "holdout": summary,
        "evaluator_version": "gems-segment-pooled-v1",
        "n_withheld": int(summary["n_truth"]),
        "budget": BUDGET_TOTAL,
        "lattice_overlap": overlap,
        "correlation_overlap_vs_registry": {"method_passed": final_nov["method_lane_passed"], "literal_passed": final_nov["literal_all_entries_passed"], "max_overlap": final_nov["method_lane_max_dot_overlap"]},
        "raster_sha256": zero_checks["sha256"],
        "submission_name": zeros_name,
        "note": note,
        "verdict": "negative",
        "ok_to_download": True,
        "ok_to_submit": False,
    }
    save_json(run_card, ROOT/"evidence/h24_signed_cgmag_run_card.json")
    save_json(run_card, ROOT/"docs/data/signed_cgmag_run_card.json")
    save_json({"file": zeros_name, "sha256": zero_checks["sha256"], "holdout": summary["dti"], "method_passed": final_nov["method_lane_passed"], "lattice_overlap": overlap}, ROOT/"docs/data/signed_cgmag_download.json")
    print(json.dumps({"file": zeros_name, "holdout": summary["dti"], "method_passed": final_nov["method_lane_passed"]}, indent=2))

if __name__=="__main__":
    main()
