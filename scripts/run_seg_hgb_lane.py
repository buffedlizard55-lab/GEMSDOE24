#!/usr/bin/env python3
"""Exploratory detector on the shared whole-segment holdout (budget-matched to the nine champions).

Uses only label-free features from data/prepared/features.npy (built by prepare_data.py).
The catalogue is read ONLY as visible training positives inside each fold's training
region (SegmentHoldout.folds[i]["train"]); withheld segments never reach the model.
No catalogue-derived distance features are used, so the leakage canary is trivially
clean for them. Each feature alone is also AUC-tested on the holdout (canary).

Outputs (never a leaderboard estimate):
  evidence/seg_hgb_experiment.json   holdout DTI + CI, per-feature canary, budget, hashes
  --emit PATH                        optional binary GeoTIFF candidate (zeros outside footprint)

Not preregistered. Counts toward the 3-experiment session budget.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems import holdout  # noqa: E402
from gems.metric import select_top_positive  # noqa: E402
from gems.validator import sha256_file  # noqa: E402

FEATURES = ROOT / "data/prepared/features.npy"
FEATURE_META = ROOT / "data/prepared/features.json"
TEMPLATE = ROOT / "data/bridge/sample_submission.tif"
LABELS = ROOT / "data/bridge/labels.tif"
RESULT = ROOT / "evidence/seg_hgb_experiment.json"
BUDGET = 37654  # matched to the GEMSDOE32 B2 dot count for a like-for-like comparison
SEED = 20261029


def load_grid():
    with rasterio.open(TEMPLATE) as t:
        fp = np.isfinite(t.read(1))
        profile = t.profile
    with rasterio.open(LABELS) as lab:
        labels = lab.read(1)
    labels = (labels == 1) & fp
    return fp, labels, profile


def to_grid(vec, fp_idx, shape, fill=np.nan):
    out = np.full(shape, fill, dtype=np.float32)
    out.ravel()[fp_idx] = vec
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--emit", type=Path, default=None)
    ap.add_argument("--budget", type=int, default=BUDGET)
    ap.add_argument(
        "--exclude-nine-champions",
        action="store_true",
        help="Uniqueness-by-construction: emit only pixels >3 px from every nine-site champion dot",
    )
    args = ap.parse_args()
    result_path = RESULT
    champion_far = None
    if args.exclude_nine_champions:
        result_path = ROOT / "evidence/seg_hgb_complement_experiment.json"
        from scipy.ndimage import distance_transform_edt

        receipt = json.loads((ROOT / "data/research/nine_site/fetch_receipt.json").read_text())
        with rasterio.open(TEMPLATE) as t:
            fp_c = np.isfinite(t.read(1))
        union = np.zeros(fp_c.shape, bool)
        for row in receipt:
            if not row["match"]:
                raise SystemExit("Champion receipt hash mismatch")
            with rasterio.open(row["local"]) as ds:
                union |= (ds.read(1) > 0) & fp_c
        champion_far = distance_transform_edt(~union) > 3.0
    t0 = time.time()

    fp, labels, profile = load_grid()
    meta = json.loads(FEATURE_META.read_text())
    names = meta["names"]
    X = np.load(FEATURES, mmap_mode="r")
    fp_idx = np.flatnonzero(fp.ravel())
    if X.shape != (len(fp_idx), len(names)):
        raise SystemExit("Prepared feature cache layout mismatch")
    X = np.asarray(X, dtype=np.float32)
    shape = fp.shape

    sh = holdout.SegmentHoldout(fp, labels, buffer_px=30)
    rng = np.random.default_rng(SEED)
    fold_preds, canary, fold_info = [], {n: [] for n in names}, []
    total_k = int(args.budget)
    fp_total = int(fp.sum())

    for fold in sh.folds:
        valid, visible, truth, train = fold["valid"], fold["visible"], fold["truth"], fold["train"]
        train_idx = np.flatnonzero((train & fp).ravel())
        pos = train_idx[visible.ravel()[train_idx]]
        neg = train_idx[~visible.ravel()[train_idx]]
        neg = rng.choice(neg, size=min(len(neg), 6 * max(len(pos), 1)), replace=False)
        sel = np.concatenate([pos, neg])
        y = np.concatenate([np.ones(len(pos)), np.zeros(len(neg))])
        # Map full-grid flat indices into footprint-vector row indices.
        row_of = np.full(fp.size, -1, dtype=np.int64)
        row_of[fp_idx] = np.arange(len(fp_idx))
        clf = HistGradientBoostingClassifier(
            max_iter=200, learning_rate=0.08, max_leaf_nodes=31, random_state=SEED
        )
        clf.fit(X[row_of[sel]], y)
        prob = clf.predict_proba(X)[:, 1].astype(np.float32)
        score = to_grid(prob, fp_idx, shape, fill=0.0)

        # Per-feature canary on this fold's holdout quadrant (labels = withheld truth).
        test_mask = (valid & ~visible).ravel()[fp_idx]
        lab_vec = truth.ravel()[fp_idx][test_mask]
        for j, n in enumerate(names):
            col = X[test_mask, j]
            ok = np.isfinite(col)
            if ok.sum() > 1 and 0 < lab_vec[ok].sum() < ok.sum():
                auc = roc_auc_score(lab_vec[ok], col[ok])
                canary[n].append(max(auc, 1 - auc))

        eligible = valid & ~visible
        if champion_far is not None:
            eligible = eligible & champion_far
        k_fold = int(round(total_k * valid.sum() / fp_total))
        pred = select_top_positive(score, eligible, k_fold)
        fold_preds.append(pred)
        fold_info.append(
            {
                "fold": fold["name"],
                "k_budget": k_fold,
                "emitted": int(pred.sum()),
                "withheld_positives": int(truth.sum()),
                "n_train_pos": int(len(pos)),
                "n_train_neg": int(len(neg)),
            }
        )
        print(f"fold {fold['name']}: k={k_fold} emitted={int(pred.sum())}", flush=True)

    summary = sh.summarize(fold_preds)
    canary_rows = {}
    for n, aucs in canary.items():
        if aucs:
            canary_rows[n] = {"max_auc_over_folds": round(float(max(aucs)), 4)}
    worst = max((v["max_auc_over_folds"] for v in canary_rows.values()), default=None)
    full = np.zeros(shape, dtype=bool)
    for p in fold_preds:
        full |= p
    result = {
        "lane": "exploratory-seg-hgb-label-free",
        "preregistered": False,
        "submit": "NO",
        "budget_dots": int(full.sum()),
        "holdout_dti": {
            "label": summary["label"],
            "evaluator_version": summary["evaluator_version"],
            "dti": round(summary["dti"], 6),
            "n_withheld_positive_pixels": summary["n_withheld_positive_pixels"],
            "ci95": [round(x, 6) for x in summary["ci95"]["interval"]],
            "ci_method": summary["ci95"]["method"],
        },
        "folds": [
            {
                "fold": r["fold"],
                "dti": round(r["dti"], 6),
                "TP_w": round(r["TP_w"], 3),
                "FP_w": round(r["FP_w"], 3),
                "FN_w": round(r["FN_w"], 3),
            }
            for r in summary["folds"]
        ],
        "fold_budget": fold_info,
        "leakage_canary": {
            "rule": "per-feature AUC on holdout quadrant; > 0.90 means leakage until proven otherwise",
            "worst_single_feature_auc": worst,
            "per_feature": canary_rows,
            "pass": worst is not None and worst <= 0.90,
        },
        "inputs": {
            "features_sha256": sha256_file(FEATURES),
            "labels_sha256": sha256_file(LABELS),
            "template_sha256": sha256_file(TEMPLATE),
        },
        "seconds": round(time.time() - t0, 1),
        "emitted_pixels_full_grid": int(full.sum()),
    }
    result["variant"] = (
        "complement-of-nine-champions (emit only >3 px from any champion dot)"
        if champion_far is not None
        else "baseline (unrestricted)"
    )
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({k: result[k] for k in ("holdout_dti", "budget_dots")}, indent=2))
    print("canary worst AUC:", worst)

    if args.emit is not None:
        out = np.where(full, np.float32(1.0), np.float32(0.0))
        out[~fp] = 0.0  # zeros-outside variant (see README on NaN-outside convention)
        args.emit.parent.mkdir(parents=True, exist_ok=True)
        prof = dict(profile)
        prof.update(dtype="float32", count=1, nodata=None, compress="deflate")
        with rasterio.open(args.emit, "w", **prof) as dst:
            dst.write(out, 1)
        print("wrote", args.emit)


if __name__ == "__main__":
    main()
