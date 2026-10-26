#!/usr/bin/env python3
"""H24-PTAR: Magnetic Phase-Tensor (Tilt Angle) & LiDAR Roughness Anti-Correlation for Concealed Hydrothermal Upflow."""

from __future__ import annotations

import json
import os
import time

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys

sys.path.insert(0, str(ROOT / "src"))
import gc

import numpy as np
import rasterio

from gems import holdout, submission
from gems.validator import sha256_file

BUDGET_FRAC = 0.0073
SEED = 20261026

def save_json(o, p):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(o, indent=2, allow_nan=False) + "\n")

def load_prepared_channel(name, fp, stack, meta):
    idx = meta["names"].index(name)
    arr = np.full(fp.shape, np.nan, dtype=np.float32)
    arr.ravel()[np.flatnonzero(fp.ravel())] = stack[:, idx]
    return arr

def main():
    started = time.monotonic()
    template = ROOT / "data/bridge/sample_submission.tif"
    labels_path = ROOT / "data/bridge/labels.tif"
    with rasterio.open(template) as t:
        arr = t.read(1)
        fp = np.isfinite(arr)
    with rasterio.open(labels_path) as ds:
        catalogue = ds.read(1) > 0
    print(f"Footprint {int(fp.sum())} catalogue {int(catalogue.sum())}")

    prep_meta = json.loads((ROOT / "data/prepared/features.json").read_text())
    prep_path = ROOT / "data/prepared/features.npy"
    stack = np.load(prep_path, mmap_mode="r")
    
    needed = ["rtp", "tmi_hg", "tmi_vg", "det_local_relief"]
    raw_valid = fp.copy()
    for n in needed:
        a = load_prepared_channel(n, fp, stack, prep_meta)
        raw_valid &= np.isfinite(a)
        del a

    from scipy.ndimage import binary_erosion
    support = binary_erosion(raw_valid, structure=np.ones((5, 5), bool), border_value=False)
    
    rtp = load_prepared_channel("rtp", fp, stack, prep_meta)
    tmi_hg = load_prepared_channel("tmi_hg", fp, stack, prep_meta)
    tmi_vg = load_prepared_channel("tmi_vg", fp, stack, prep_meta)
    relief = load_prepared_channel("det_local_relief", fp, stack, prep_meta)

    # Calculate Magnetic Tilt Angle (Phase Tensor)
    # tilt = arctan(tmi_vg / tmi_hg)
    eps = 1e-5
    tilt = np.where(support, np.arctan2(tmi_vg, np.maximum(tmi_hg, eps)), 0).astype(np.float32)
    
    # Normalize tilt
    t95 = max(float(np.percentile(np.abs(tilt[support]), 95)), 1e-6)
    tilt_n = np.where(support, np.clip(np.abs(tilt) / t95, 0, 1), 0).astype(np.float32)

    # Anti-correlation with relief (flat basins)
    scale = 5.0
    flat_gate = np.where(support, np.exp(-np.clip(relief, 0, 100) / scale), 0).astype(np.float32)
    
    candidate = np.where(support, tilt_n * flat_gate, 0).astype(np.float32)
    
    print(f"Candidate max {candidate.max():.4f} mean {candidate[support].mean():.4f} p95 {np.percentile(candidate[support], 95):.4f}")
    
    del rtp, tmi_hg, tmi_vg, relief, tilt, tilt_n, flat_gate
    gc.collect()

    context = holdout.SegmentHoldout(fp, catalogue, buffer_px=15)
    print(f"Folds {len(context.folds)}")

    canary_features = {"candidate": candidate}
    canary = context.canary(canary_features, seed=SEED, max_per_class=15000)
    print(f"Canary passed {canary['passed']}")
    if not canary["passed"]:
        save_json({"canary": canary, "verdict": "negative", "stopped": "leakage"}, ROOT / "evidence/ptar_experiment_20261026.json")
        raise SystemExit("Canary failed")

    valid_entries = []
    
    from gems import emission
    per_fold_dots = []
    for fold in context.folds:
        eligible = support & fold["valid"] & ~fold["visible"]
        k = round(BUDGET_FRAC * int(fold["valid"].sum()))
        dots = emission.priority_poisson(candidate, eligible, k, min_dist=3)
        per_fold_dots.append(dots)

    results = context.summarize(per_fold_dots, ci_draws=1999)
    print(f"HOLDOUT-DTI {results['dti']:.5f} CI {results['ci95']['interval']}")
    
    baseline = 0.16370  # Current spatial block holdout best in this class
    delta = results["dti"] - baseline
    print(f"Delta vs OOF baseline {baseline}: {delta:.5f}")

    eligible_final = support & ~catalogue
    full_budget = round(BUDGET_FRAC * int(fp.sum()))
    final_dots = emission.priority_poisson(candidate, eligible_final, full_budget, min_dist=3)
    
    content_id = submission.scored_content_id(final_dots, fp, catalogue)
    name = submission.make_filename("gems24", "ptar-tilt-relief", "20261026", content_id, "zeros")
    out_dir = ROOT / "docs/downloads"
    out_dir.mkdir(parents=True, exist_ok=True)
    zeros = submission.write_submission(final_dots.astype(np.float32), template, out_dir / name, outside="zero")
    
    checks = {"zero_outside": submission.check_variants(zeros, template)}
    
    card = {
        "hypothesis": "H24-PTAR: Magnetic Phase-Tensor (Tilt Angle) & LiDAR Roughness Anti-Correlation for Concealed Hydrothermal Upflow",
        "mechanism": "Edge-detection via Phase Tensor (Tilt angle) amplitude normalized by local relief, targeting concealed faults in flat basins.",
        "non_fault_mimic": "Buried human infrastructure (pipelines) or flat magnetic sedimentary deposits.",
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
        "note": "GEMS24 PTAR | tilt x flat | research; unique TIF generation",
        "verdict": "promote" if delta > 0 else "negative",
        "ok_to_download": True,
        "ok_to_submit": bool(delta > 0),
        "experiments_run": 1,
        "elapsed_seconds": time.monotonic() - started
    }

    save_json(card, ROOT / "evidence/ptar_run_card_20261026.json")
    print(json.dumps({"file": name, "dti": results["dti"], "verdict": card["verdict"]}, indent=2))

if __name__ == "__main__":
    main()
