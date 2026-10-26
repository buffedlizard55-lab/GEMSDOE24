#!/usr/bin/env python3
"""H24-GSD: Geodetic Strain Rate Divergence at Isostatic Gravity Saddles."""

from __future__ import annotations

import json
import os
import time
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")

from pathlib import Path
import sys
import gc

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import numpy as np
import rasterio

from gems import holdout, submission
from gems.validator import sha256_file

BUDGET_FRAC = 0.0073
SEED = 20261027

def save_json(o, p):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(o, indent=2, allow_nan=False) + "\n")

def load_prepared_channel(name, fp, stack, meta):
    idx = meta["names"].index(name)
    arr = np.full(fp.shape, np.nan, dtype=np.float32)
    arr.ravel()[np.flatnonzero(fp.ravel())] = stack[:, idx]
    return arr

def robust_sigmoid(x, support):
    vals = x[support]
    med = float(np.median(vals))
    q25, q75 = np.percentile(vals, [25, 75])
    iqr = max(float(q75 - q25), 1e-6)
    z = np.clip((np.where(np.isfinite(x), x, med) - med) / iqr, -10, 10)
    out = (1 / (1 + np.exp(-z))).astype(np.float32)
    out[~support] = 0
    return out

def main():
    started = time.monotonic()
    template = ROOT / "data/bridge/sample_submission.tif"
    labels_path = ROOT / "data/bridge/labels.tif"
    with rasterio.open(template) as t:
        fp = np.isfinite(t.read(1))
    with rasterio.open(labels_path) as ds:
        catalogue = ds.read(1) > 0

    prep_meta = json.loads((ROOT / "data/prepared/features.json").read_text())
    prep_path = ROOT / "data/prepared/features.npy"
    stack = np.load(prep_path, mmap_mode="r")
    
    needed = ["geod_dilaterate", "geod_shearrate", "iso_grav_anom", "det_local_relief"]
    raw_valid = fp.copy()
    for n in needed:
        a = load_prepared_channel(n, fp, stack, prep_meta)
        raw_valid &= np.isfinite(a)
        del a

    from scipy.ndimage import binary_erosion
    support = binary_erosion(raw_valid, structure=np.ones((5, 5), bool), border_value=False)
    
    dil = load_prepared_channel("geod_dilaterate", fp, stack, prep_meta)
    shr = load_prepared_channel("geod_shearrate", fp, stack, prep_meta)
    grav = load_prepared_channel("iso_grav_anom", fp, stack, prep_meta)
    relief = load_prepared_channel("det_local_relief", fp, stack, prep_meta)

    # 1. Strain Rate Divergence/Product
    strain = np.where(support, np.clip(dil * shr, 0, None), 0).astype(np.float32)
    s95 = max(float(np.percentile(strain[support], 95)), 1e-6)
    strain_n = np.where(support, np.clip(strain / s95, 0, 1), 0).astype(np.float32)

    # 2. Gravity Saddles (negative Hessian determinant)
    grav_safe = np.where(raw_valid, grav, 0).astype(np.float32)
    gy, gx = np.gradient(grav_safe)
    hyy, hyx = np.gradient(gy)
    hxy, hxx = np.gradient(gx)
    hdet = hxx * hyy - hxy * hyx
    saddle = np.where(support, np.maximum(-hdet, 0), 0).astype(np.float32)
    gs95 = max(float(np.percentile(saddle[support], 95)), 1e-6)
    saddle_n = np.where(support, np.clip(saddle / gs95, 0, 1), 0).astype(np.float32)

    # Relief gate (favor lower relief / basins)
    flat_gate = np.where(support, np.exp(-np.clip(relief, 0, 100) / 10.0), 0).astype(np.float32)

    candidate = np.where(support, strain_n * saddle_n * flat_gate, 0).astype(np.float32)

    del dil, shr, grav, relief, strain, strain_n, grav_safe, gy, gx, hyy, hyx, hxy, hxx, hdet, saddle, saddle_n, flat_gate
    gc.collect()

    context = holdout.SegmentHoldout(fp, catalogue, buffer_px=15)
    
    canary = context.canary({"candidate": candidate}, seed=SEED, max_per_class=15000)
    if not canary["passed"]:
        save_json({"canary": canary, "verdict": "negative"}, ROOT / "evidence/gsd_experiment_20261026.json")
        raise SystemExit("Canary failed")

    from gems import emission
    per_fold_dots = []
    for fold in context.folds:
        eligible = support & fold["valid"] & ~fold["visible"]
        k = round(BUDGET_FRAC * int(fold["valid"].sum()))
        dots = emission.priority_poisson(candidate, eligible, k, min_dist=3)
        per_fold_dots.append(dots)

    results = context.summarize(per_fold_dots, ci_draws=1999)
    baseline = 0.16370
    delta = results["dti"] - baseline
    print(f"HOLDOUT-DTI {results['dti']:.5f} Delta: {delta:.5f}")

    eligible_final = support & ~catalogue
    full_budget = round(BUDGET_FRAC * int(fp.sum()))
    final_dots = emission.priority_poisson(candidate, eligible_final, full_budget, min_dist=3)
    
    content_id = submission.scored_content_id(final_dots, fp, catalogue)
    name = submission.make_filename("gems24", "gsd-strain-gravity", "20261026", content_id, "zeros")
    out_dir = ROOT / "docs/downloads"
    out_dir.mkdir(parents=True, exist_ok=True)
    zeros = submission.write_submission(final_dots.astype(np.float32), template, out_dir / name, outside="zero")
    
    checks = {"zero_outside": submission.check_variants(zeros, template)}
    
    card = {
        "hypothesis": "H24-GSD: Geodetic Strain Rate Divergence at Isostatic Gravity Saddles",
        "mechanism": "Spatial coincidence of geodetic strain rate anomalies (high shear/dilation) intersecting gravity saddles.",
        "non_fault_mimic": "Diffuse basin strain not localized on discrete structures.",
        "holdout": {
            "label": "HOLDOUT-DTI",
            "evaluator_version": "gems-segment-pooled-v1",
            "dti": results["dti"],
            "ci95": results["ci95"],
            "n_withheld_positive_pixels": 60988,
            "paired_delta_vs_oof_baseline_0_13": delta,
            "baseline_dti": baseline
        },
        "correlation_overlap_vs_registry": {},
        "raster_sha256": sha256_file(zeros),
        "validator_output": checks["zero_outside"],
        "submission_name": name,
        "note": "GEMS24 GSD | strain x gravity | research",
        "verdict": "promote" if delta > 0 else "negative",
        "ok_to_download": True,
        "ok_to_submit": bool(delta > 0)
    }
    save_json(card, ROOT / "evidence/gsd_run_card_20261026.json")
    print(json.dumps({"file": name, "dti": results["dti"], "verdict": card["verdict"]}, indent=2))

if __name__ == "__main__":
    main()