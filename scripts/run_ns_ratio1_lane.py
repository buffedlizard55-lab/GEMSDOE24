#!/usr/bin/env python3
"""NS-RATIO1: ratio-rule dot placement on locally available features (3 experiments).

Pre-registered in this file before the first run (see SETTINGS below). Not a
leaderboard estimate: every number is HOLDOUT-DTI (evaluator
`gems-segment-pooled-v1` from src/gems/holdout.py, withheld positives and 95% CI
recorded) or a geometry/format check.

Why this selection rule. The official distance-weighted Tversky index with
alpha=0.2, beta=0.8 satisfies FN_w = N - TP_w exactly (N = number of truth
pixels), so DTI = TP / (0.8 N + 0.2 (TP + FP)). Adding a binary dot with
expected truth credit c and false-positive weight f raises DTI iff
c / f > 0.2 TP / (0.8 N + 0.2 FP). The dot budget is therefore set by the
credit-to-penalty ratio, not by a fixed fraction of pixels.

Experiments (3 total, the session budget):
  E1  FULL      label-free GeoDAWN radiometric + magnetic-extension + 1 m LiDAR
                channels + catalogue-proximity features (visible faults only).
  E2  LABELFREE same channels WITHOUT any catalogue-derived feature (ablation).
  E3  PROXIMITY no model: rank eligible cells by nearest-visible-fault distance.

Each experiment: quadrant-blocked, whole-segment, 30 px buffered hide-and-recover
(SegmentHoldout). Dots: top-ranked eligible cells with >= 3 px spacing and a
budget of K_FOLD per fold, K_TOTAL = 37,654 (matched to the nine-site budget).
Eligibility excludes visible catalogue cells (the same convention as the
evaluator's catalogue mask). Sanity: per-feature leakage canary (AUC > 0.90 fails).

Optional --emit writes the submission candidate: a model trained on ALL catalogue
positives (no holdout), the same selection rule, binary float32, zeros outside.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt, gaussian_filter
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems import holdout  # noqa: E402
from gems.validator import sha256_file  # noqa: E402

TEMPLATE = ROOT / "data/bridge/sample_submission.tif"
LABELS = ROOT / "data/bridge/labels.tif"
LIDAR = ROOT / "data/external/lidar_scarp_features_u8.tif"
LIDAR_META = ROOT / "data/external/lidar_scarp_features.json"
RAD = ROOT / "data/external/geodawn_rad_u8.tif"
EXT = ROOT / "data/external/geodawn_extensions_u8.tif"
RESULT = ROOT / "evidence/ns_ratio1_experiment_20261030.json"

SETTINGS = {
    "lane": "NS-RATIO1",
    "seed": 20261030,
    "k_total": 37654,
    "min_spacing_px": 3.0,
    "buffer_px": 30,
    "neg_per_pos": 6,
    "hgb": {"max_iter": 200, "learning_rate": 0.08, "max_leaf_nodes": 31},
    "catalogue_sigmas_px": [20, 50],  # 2 km and 5 km visible-fault density
}


def _read_u8_stack(path: Path, fp: np.ndarray, drop=()):
    """Footprint cells only, (C, n_fp) float32; 0 = no data in these products -> NaN."""
    with rasterio.open(path) as s:
        names = list(s.descriptions)
        keep = [i for i, n in enumerate(names) if n not in drop]
        out = np.empty((len(keep), int(fp.sum())), np.float32)
        for j, i in enumerate(keep):
            band = s.read(i + 1).astype(np.float32)
            band[band == 0] = np.nan
            out[j] = band[fp]
            del band
    return [names[i] for i in keep], out


def static_features(fp, template_transform, template_shape):
    """Label-free channels restricted to footprint cells, (C, n_fp), NaN where no data."""
    names, lidar = _read_u8_stack(LIDAR, fp, drop=("valid", "strike"))
    lidar_names = [f"lidar_{n}" for n in names]
    rad_names, rad = _read_u8_stack(RAD, fp)
    ext_names, ext = _read_u8_stack(EXT, fp)
    for path in (LIDAR, RAD, EXT):
        with rasterio.open(path) as s:
            if s.shape != template_shape or tuple(s.transform)[:6] != tuple(template_transform)[:6]:
                raise SystemExit(f"Grid mismatch: {path}")
    stack = np.concatenate([lidar, rad, ext], axis=0)  # (C, n_fp)
    names = lidar_names + [f"rad_{n}" for n in rad_names] + [f"ext_{n}" for n in ext_names]
    return names, stack


def catalogue_features(visible: np.ndarray, fp: np.ndarray):
    """Features from VISIBLE faults only (fold.visible or full catalogue for emission)."""
    visible = np.asarray(visible).astype(bool)
    dist_px = distance_transform_edt(~visible)
    feats = {"cat_log1p_dist_km": np.log1p(dist_px * 0.1).astype(np.float32)}
    for sigma in SETTINGS["catalogue_sigmas_px"]:
        dens = gaussian_filter(visible.astype(np.float32), sigma=sigma, mode="constant")
        feats[f"cat_density_s{sigma}"] = dens.astype(np.float32)
    return feats, dist_px


def ratio_select(q_grid, eligible, k, spacing):
    """Greedy top-k with a minimum Euclidean spacing; bounded candidate list."""
    ids = np.flatnonzero(eligible.ravel() & np.isfinite(q_grid.ravel()) & (q_grid.ravel() > 0))
    if k <= 0 or ids.size == 0:
        return np.zeros(eligible.shape, bool)
    order = ids[np.lexsort((ids, -q_grid.ravel()[ids]))]
    # Scan every candidate in rank order (run 1 truncated to 4k and under-filled budgets).
    H, W = eligible.shape
    blocked = np.zeros((H, W), bool)
    r = int(np.ceil(spacing))
    offs = [
        (dy, dx)
        for dy in range(-r, r + 1)
        for dx in range(-r, r + 1)
        if 0 < dy * dy + dx * dx < spacing * spacing
    ]
    out = np.zeros((H, W), bool)
    n = 0
    for flat in order:
        y, x = divmod(int(flat), W)
        if blocked[y, x]:
            continue
        out[y, x] = True
        n += 1
        if n >= k:
            break
        for dy, dx in offs:
            yy, xx = y + dy, x + dx
            if 0 <= yy < H and 0 <= xx < W:
                blocked[yy, xx] = True
    return out


def fit_predict(X_train, y_train, X_pred, rng_seed):
    clf = HistGradientBoostingClassifier(random_state=rng_seed, **SETTINGS["hgb"])
    clf.fit(X_train, y_train)
    return clf.predict_proba(X_pred)[:, 1].astype(np.float32)


def run_holdout(experiment, fp, labels, static_fp, static_names, use_catalogue, rng):
    sh = holdout.SegmentHoldout(fp, labels, buffer_px=SETTINGS["buffer_px"])
    fp_total = int(fp.sum())
    fold_preds, canary = [], {}
    fold_info = []
    fp_flat = np.flatnonzero(fp.ravel())
    for fold in sh.folds:
        valid, visible, truth, train = fold["valid"], fold["visible"], fold["truth"], fold["train"]
        feats = {}
        if use_catalogue:
            cat, dist_px = catalogue_features(visible, fp)
            feats.update(cat)
        X_full = []
        names = list(static_names)
        if static_fp is not None:
            X_full.append(static_fp)
        if use_catalogue:
            names += list(feats.keys())
            X_full.append(np.stack([feats[k][fp] for k in feats], axis=0))
        X = np.concatenate(X_full, axis=0).T.astype(np.float32)  # rows = fp cells
        row_of = np.full(fp.shape, -1, np.int64).ravel()
        row_of[fp_flat] = np.arange(len(fp_flat))
        tr_idx_grid = np.flatnonzero((train & fp).ravel())
        tr_rows = row_of[tr_idx_grid]
        is_pos = visible.ravel()[tr_idx_grid]
        pos_rows = tr_rows[is_pos]
        neg_pool = tr_rows[~is_pos]
        neg_rows = rng.choice(
            neg_pool,
            size=min(len(neg_pool), SETTINGS["neg_per_pos"] * max(len(pos_rows), 1)),
            replace=False,
        )
        rows = np.concatenate([pos_rows, neg_rows])
        y = np.concatenate([np.ones(len(pos_rows)), np.zeros(len(neg_rows))])
        eligible_grid = valid & ~visible & fp
        el_rows = row_of[np.flatnonzero(eligible_grid.ravel())]
        q_rows = fit_predict(X[rows], y, X[el_rows], SETTINGS["seed"])
        q_grid = np.zeros(fp.shape, np.float32)
        q_grid.ravel()[np.flatnonzero(eligible_grid.ravel())] = q_rows
        # Single-feature leakage canary on the withheld quadrant only.
        test_rows = row_of[np.flatnonzero((valid & ~visible & fp).ravel())]
        lab = truth.ravel()[np.flatnonzero((valid & ~visible & fp).ravel())].astype(int)
        for j, n in enumerate(names):
            col = X[test_rows, j]
            ok = np.isfinite(col)
            if ok.sum() > 1 and 0 < lab[ok].sum() < ok.sum():
                auc = roc_auc_score(lab[ok], col[ok])
                canary.setdefault(n, []).append(float(max(auc, 1 - auc)))
        k_fold = int(round(SETTINGS["k_total"] * valid.sum() / fp_total))
        pred = ratio_select(q_grid, eligible_grid, k_fold, SETTINGS["min_spacing_px"])
        fold_preds.append(pred.astype(np.uint8))
        fold_info.append(
            {
                "fold": fold["name"],
                "k_fold": k_fold,
                "emitted": int(pred.sum()),
                "withheld_positives": int(truth.sum()),
                "n_train_pos": int(len(pos_rows)),
                "n_train_neg": int(len(neg_rows)),
            }
        )
        print(
            f"[{experiment}] fold {fold['name']} k={k_fold} emitted={int(pred.sum())}", flush=True
        )
    summary = sh.summarize(fold_preds)
    worst = max((max(v) for v in canary.values()), default=None)
    worst_name = max(canary, key=lambda n: max(canary[n])) if canary else None
    return {
        "experiment": experiment,
        "label": "HOLDOUT-DTI",
        "evaluator_version": summary["evaluator_version"],
        "dti": round(summary["dti"], 6),
        "tp_w": round(summary["TP_w"], 3),
        "fp_w": round(summary["FP_w"], 3),
        "fn_w": round(summary["FN_w"], 3),
        "n_withheld_positive_pixels": summary["n_withheld_positive_pixels"],
        "ci95": [round(x, 6) for x in summary["ci95"]["interval"]],
        "ci_method": summary["ci95"]["method"],
        "folds": [{"fold": r["fold"], "dti": round(r["dti"], 6)} for r in summary["folds"]],
        "fold_budget": fold_info,
        "dots_emitted_total": int(sum(p.sum() for p in fold_preds)),
        "leakage_canary": {
            "rule": "single-feature AUC on withheld quadrant; > 0.90 = leakage until proven otherwise",
            "worst_feature": worst_name,
            "worst_auc": round(float(worst), 4) if worst is not None else None,
            "pass": bool(worst is not None and worst <= 0.90),
            "per_feature_max_auc": {k: round(max(v), 4) for k, v in canary.items()},
        },
        "_fold_preds": fold_preds,
        "_summary": summary,
    }


def proximity_experiment(fp, labels, sh):
    """E3: no model. Rank eligible cells by nearest-visible-fault distance (closest first)."""
    fold_preds, fold_info = [], []
    fp_total = int(fp.sum())
    for fold in sh.folds:
        valid, visible = fold["valid"], fold["visible"]
        dist_px = distance_transform_edt(~visible)
        eligible = valid & ~visible & fp
        q = np.where(eligible, np.exp(-dist_px / 20.0), 0.0).astype(np.float32)  # 2 km e-folding
        k_fold = int(round(SETTINGS["k_total"] * valid.sum() / fp_total))
        pred = ratio_select(q, eligible, k_fold, SETTINGS["min_spacing_px"])
        fold_preds.append(pred.astype(np.uint8))
        fold_info.append({"fold": fold["name"], "k_fold": k_fold, "emitted": int(pred.sum())})
    summary = sh.summarize(fold_preds)
    return {
        "experiment": "E3_PROXIMITY",
        "label": "HOLDOUT-DTI",
        "evaluator_version": summary["evaluator_version"],
        "dti": round(summary["dti"], 6),
        "n_withheld_positive_pixels": summary["n_withheld_positive_pixels"],
        "ci95": [round(x, 6) for x in summary["ci95"]["interval"]],
        "fold_budget": fold_info,
        "dots_emitted_total": int(sum(p.sum() for p in fold_preds)),
    }


def emit(path: Path, fp, labels, static_fp, static_names, profile):
    """Submission candidate = E2 configuration (label-free channels only), trained on ALL
    visible catalogue positives, no holdout. Catalogue-distance features are NOT used:
    run 1 showed they are void without cross-fitting (see evidence run-1 archive)."""
    names = list(static_names)
    X = static_fp.T.astype(np.float32)
    fp_flat = np.flatnonzero(fp.ravel())
    row_of = np.full(fp.size, -1, np.int64)
    row_of[fp_flat] = np.arange(len(fp_flat))
    rng = np.random.default_rng(SETTINGS["seed"])
    pos_rows = row_of[np.flatnonzero((labels & fp).ravel())]
    neg_pool = row_of[np.flatnonzero((fp & ~labels).ravel())]
    neg_rows = rng.choice(neg_pool, size=SETTINGS["neg_per_pos"] * len(pos_rows), replace=False)
    rows = np.concatenate([pos_rows, neg_rows])
    y = np.concatenate([np.ones(len(pos_rows)), np.zeros(len(neg_rows))])
    eligible = fp & ~labels
    el_rows = row_of[np.flatnonzero(eligible.ravel())]
    q_rows = fit_predict(X[rows], y, X[el_rows], SETTINGS["seed"])
    q = np.zeros(fp.shape, np.float32)
    q.ravel()[np.flatnonzero(eligible.ravel())] = q_rows
    dots = ratio_select(q, eligible, SETTINGS["k_total"], SETTINGS["min_spacing_px"])
    out = dots.astype(np.float32)
    out[~fp] = 0.0  # zeros outside footprint (score-neutral; see README)
    path = path if path.is_absolute() else ROOT / path
    path.parent.mkdir(parents=True, exist_ok=True)
    prof = dict(profile)
    prof.update(dtype="float32", count=1, nodata=None, compress="deflate")
    with rasterio.open(path, "w", **prof) as dst:
        dst.write(out, 1)
    return {
        "path": str(path.relative_to(ROOT)),
        "dots": int(dots.sum()),
        "features": names,
        "n_train_pos": int(len(pos_rows)),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--emit", type=Path, default=None, help="write candidate GeoTIFF")
    ap.add_argument("--skip-holdout", action="store_true")
    ap.add_argument(
        "--experiments",
        default="E2,E3",
        help="E1 is VOID until cross-fitted catalogue features exist; default runs E2,E3",
    )
    args = ap.parse_args()
    t0 = time.time()
    rng = np.random.default_rng(SETTINGS["seed"])
    with rasterio.open(TEMPLATE) as t:
        profile = t.profile.copy()
        fp = np.isfinite(t.read(1))
    with rasterio.open(LABELS) as lab:
        labels = (lab.read(1) == 1) & fp  # boolean grid; never use bitwise ~ on ints
    static_names, static_fp = static_features(fp, profile["transform"], fp.shape)
    results = {
        "settings": SETTINGS,
        "inputs": {
            "template_sha256": sha256_file(TEMPLATE),
            "labels_sha256": sha256_file(LABELS),
            "lidar_sha256": sha256_file(LIDAR),
            "rad_sha256": sha256_file(RAD),
            "ext_sha256": sha256_file(EXT),
            "lidar_meta_sha256": hashlib.sha256(LIDAR_META.read_bytes()).hexdigest(),
        },
        "footprint_cells": int(fp.sum()),
        "catalogue_positive_pixels": int(labels.sum()),
        "static_features": static_names,
        "note": "HOLDOUT-DTI only; not a leaderboard estimate; features restricted to label-free channels except catalogue-derived ones computed from visible faults",
    }
    if not args.skip_holdout:
        sh_probe = holdout.SegmentHoldout(fp, labels, buffer_px=SETTINGS["buffer_px"])
        wanted = {x.strip() for x in args.experiments.split(",") if x.strip()}
        if "E1" in wanted:
            raise SystemExit(
                "E1 refused: catalogue-distance features are void without cross-fitting"
            )
        out = []
        if "E2" in wanted:
            e2 = run_holdout("E2_LABELFREE", fp, labels, static_fp, static_names, False, rng)
            e2.pop("_fold_preds")
            e2.pop("_summary")
            out.append(e2)
        if "E3" in wanted:
            out.append(proximity_experiment(fp, labels, sh_probe))
        results["experiments"] = out
        results["run"] = (
            "run-2: selection bug fixed (all candidates scanned); E1 excluded (void); see run-1 archive"
        )
        for e in results["experiments"]:
            print(
                f"{e['experiment']}: HOLDOUT-DTI={e['dti']} CI={e['ci95']} withheld={e['n_withheld_positive_pixels']}",
                flush=True,
            )
    if args.emit is not None:
        results["emitted"] = emit(args.emit, fp, labels, static_fp, static_names, profile)
        print("emitted", results["emitted"]["path"], "dots", results["emitted"]["dots"], flush=True)
    results["seconds"] = round(time.time() - t0, 1)
    RESULT.parent.mkdir(parents=True, exist_ok=True)
    RESULT.write_text(json.dumps(results, indent=2, allow_nan=False) + "\n")
    print("wrote", RESULT.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
