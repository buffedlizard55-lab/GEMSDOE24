#!/usr/bin/env python3
"""Frozen paired spatial retraining for H24-2A; never consumes submission slots.

Historical binary rasters are scored AS EMITTED, not incorrectly re-ranked.
They are imperfect diagnostics (their original OOF caches are unavailable).
Only a fresh same-split baseline/challenger comparison is a retraining result.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import binary_dilation, distance_transform_edt, label
from sklearn.ensemble import HistGradientBoostingClassifier
from threadpoolctl import threadpool_limits

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems import confounds, footprint, holdout, metric, submission  # noqa: E402
from gems.residualize import NuisanceResidualizer  # noqa: E402
from gems.validator import sha256_file  # noqa: E402

SEED = 20261002
PARAMS = dict(
    max_iter=80,
    max_leaf_nodes=15,
    learning_rate=0.08,
    l2_regularization=5,
    early_stopping=False,
    random_state=SEED,
)
BUDGET = 0.0245


def select_ridges(score, valid, fraction=BUDGET, *, support=None, catalogue=None):
    # NMS uses a complete independently predicted halo, never a zero-padded
    # quadrant or a surface zeroed along catalogue traces.
    support = valid if support is None else support
    eligible = metric.ridge_nms(score, support, sigma=1) & valid
    if catalogue is not None:
        eligible &= ~catalogue
    requested = int(round(fraction * valid.sum()))
    out = metric.select_top_positive(score, eligible, requested)
    return out, {
        "eligible_ridges": int(eligible.sum()),
        "selected": int(out.sum()),
        "requested": requested,
        "zero_score_padding": 0,
    }


def summary(rows):
    return {
        "mean_dense_dti": float(np.mean([r["dense"]["dti"] for r in rows])),
        "mean_sparse_dti": float(np.mean([r["sparse"]["dti"] for r in rows])),
        "fold_dense": [r["dense"]["dti"] for r in rows],
        "fold_sparse": [r["sparse"]["dti"] for r in rows],
        "details": rows,
    }


def run() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--allow-partial-audit-inputs", action="store_true")
    args = ap.parse_args()
    t0 = time.time()
    fp = footprint.load_footprint()
    fp_idx = np.flatnonzero(fp)
    with rasterio.open(ROOT / "data/bridge/labels.tif") as d:
        labels = (d.read(1) > 0) & fp
    folds, names = holdout.make_quadrant_folds(fp)
    prepared = ROOT / "data/prepared/features.npy"
    meta = json.loads((prepared.parent / "features.json").read_text())
    G = np.load(prepared, mmap_mode="r")
    prov = json.loads((confounds.CONF / "provenance.json").read_text())
    if not prov["full_requested_audit_available"] and not args.allow_partial_audit_inputs:
        raise SystemExit(
            "Full acquisition confounds missing; explicitly allow only a BLOCKED exploratory run"
        )
    with np.load(confounds.CONF / "confounds.npz") as conf:
        cfeat = confounds.classifier_features(conf)
    if "road_m" not in cfeat or "claim_m" not in cfeat:
        raise SystemExit("True road and closed-claim distances required for this experiment")
    ckeys = ["road_m", "claim_m"] + sorted(set(cfeat) - {"road_m", "claim_m"})
    C = np.column_stack([cfeat[k].ravel()[fp_idx] for k in ckeys]).astype(np.float32)
    del cfeat
    if not np.isfinite(C).all():
        raise SystemExit("Nuisance input missing inside footprint")
    comps, _ = label(labels, structure=np.ones((3, 3), int))
    arms = ("physics_raw", "physics_arc_raw", "physics_residualized", "physics_arc_residualized")
    results = {a: [] for a in arms}
    historical = {}
    for tag in ("h19-4", "h19-5"):
        p = next((ROOT / "inputs").glob(f"*{tag}*-nan.tif"))
        with rasterio.open(p) as s:
            historical[tag] = ((s.read(1) > 0.5) & fp, p)
    hist_results = {k: [] for k in historical}
    evidence = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "hypothesis": "H24-2A radial-gradient arc coherence",
        "preregistration": "knowledge/02_preregistered_2026-10-02.md",
        "protocol": {
            "seed": SEED,
            "detector_params": PARAMS,
            "budget": BUDGET,
            "buffer_m": 1500,
            "nuisance_training_only": True,
            "nuisance_regression": "training-only uniform 30000-pixel sample; quadratic splines and interactions; Ridge alpha=100",
            "positives": "catalogue trace pixels only",
            "negatives": "unlabelled >=900 m from all catalogue traces (NOT verified fault absence)",
            "component_exclusion": "every component touching held-out quadrant or 1.5 km collar removed from supervised training",
            "historical_comparability": "as-emitted diagnostics only; cannot certify original H19 OOF cache reproduction",
        },
        "features": meta,
        "nuisance_names": ckeys,
        "access_inputs_complete": prov["full_requested_audit_available"],
        "missing_required": prov["missing_required"],
        "folds": [],
        "results": {},
        "historical_diagnostics": {},
        "submission_slot_spent": False,
    }
    path = ROOT / "evidence/h24_2_experiment.json"
    # Fold-independent truth distance only excludes ambiguous negatives. No
    # validation label enters a fitted feature, normalization or nuisance model.
    distance_all = distance_transform_edt(~labels)
    for f_id, name in enumerate(names):
        rng = np.random.default_rng(SEED + f_id)
        val = (folds == f_id) & fp
        collar = distance_transform_edt(~val) <= 15
        excluded = np.unique(comps[collar & labels])
        train = fp & ~collar
        # Components can cross a collar; exclude their pixels everywhere.
        positive = labels & train & ~np.isin(comps, excluded)
        negative = train & (distance_all >= 9)
        pos_ids = np.flatnonzero(positive.ravel()[fp_idx])
        neg_ids = np.flatnonzero(negative.ravel()[fp_idx])
        if min(len(pos_ids), len(neg_ids)) < 100:
            raise SystemExit(f"Insufficient independent components in {name}")
        pos_ids = rng.choice(pos_ids, min(20000, len(pos_ids)), replace=False)
        neg_ids = rng.choice(neg_ids, min(60000, len(neg_ids)), replace=False)
        train_ids = np.r_[pos_ids, neg_ids]
        y = np.r_[np.ones(len(pos_ids), np.int8), np.zeros(len(neg_ids), np.int8)]
        uniform = np.flatnonzero(train.ravel()[fp_idx])
        uniform = rng.choice(uniform, min(30000, len(uniform)), replace=False)
        # Scalar transforms are fitted once from training-only pixels, shared
        # between all arms. No validation-dependent parameter choice.
        resid = NuisanceResidualizer().fit(C[uniform], G[uniform])
        support = binary_dilation(val, structure=np.ones((3, 3), bool), iterations=7) & fp
        val_ids = np.flatnonzero(support.ravel()[fp_idx])
        yd, xd = np.nonzero(val)
        sl = (slice(yd.min(), yd.max() + 1), slice(xd.min(), xd.max() + 1))
        td = labels & val
        ts = holdout.thin_components(td, 0.20, 4242 + f_id)
        known_sparse = td & ~ts

        def evaluate(pred):
            return {
                "fold": name,
                "dense": metric.dti_score_fast(pred[sl], td[sl], valid_mask=val[sl]),
                "sparse": metric.dti_score_fast(
                    pred[sl], ts[sl], valid_mask=val[sl], catalogue_mask=known_sparse[sl]
                ),
            }

        for tag, (pred, _) in historical.items():
            hist_results[tag].append(evaluate(pred))
        evidence["folds"].append(
            {
                "name": name,
                "n_positive_train": len(pos_ids),
                "n_unlabelled_train": len(neg_ids),
                "n_excluded_components": len(excluded),
                "held_out_trace_pixels": int(td.sum()),
                "held_out_sparse_pixels": int(ts.sum()),
                "training_touches_validation": bool((train & val).any()),
                "training_component_leak": bool(np.isin(comps[positive], excluded).any()),
            }
        )
        for arm in arms:
            remove = "residualized" in arm
            nc = G.shape[1] if "arc" in arm else meta["base_count"]
            X_train = resid.transform(C[train_ids], G[train_ids], remove=remove)[:, :nc]
            model = HistGradientBoostingClassifier(**PARAMS).fit(X_train, y)
            score = np.zeros(fp.shape, np.float32)
            for begin in range(0, len(val_ids), 50000):
                ii = val_ids[begin : begin + 50000]
                X = resid.transform(C[ii], G[ii], remove=remove)[:, :nc]
                score.ravel()[fp_idx[ii]] = model.predict_proba(X)[:, 1].astype(np.float32)
            # The complete quadrant score surface is assembled before ridge
            # thinning. Histograms or thresholds are not tuned on its labels.
            pred, selection = select_ridges(score, val, support=support)
            row = evaluate(pred)
            row["selection"] = selection
            results[arm].append(row)
            print(name, arm, row["dense"]["dti"], row["sparse"]["dti"], flush=True)
        evidence["results"] = {a: summary(rows) for a, rows in results.items()}
        evidence["historical_diagnostics"] = {a: summary(rows) for a, rows in hist_results.items()}
        path.write_text(json.dumps(evidence, indent=2) + "\n")
    evidence["paired_gate"] = {}
    candidate = evidence["results"]["physics_arc_residualized"]
    for base in ("physics_raw", "physics_residualized"):
        b = evidence["results"][base]
        g = holdout.gate(candidate, b)
        g["minimum_effect_passed"] = bool(
            g["delta_mean_dense"] > 0.001 and g["delta_mean_sparse"] > 0.001
        )
        evidence["paired_gate"][base] = g
    historical_gates = {
        tag: holdout.gate(candidate, summary(rows)) for tag, rows in hist_results.items()
    }
    evidence["historical_diagnostic_gate"] = historical_gates
    evidence["decision"] = {
        "candidate_beats_paired_baselines": all(
            g["passed"] and g["minimum_effect_passed"] for g in evidence["paired_gate"].values()
        ),
        "candidate_beats_historical_diagnostics": all(
            g["passed"] for g in historical_gates.values()
        ),
        "original_h19_holdout_reproduced": False,
        "promoted": False,
        "reason": "Requires paired gains, complete accessibility audit, and a comparable current-best OOF reconstruction. Historical rasters alone cannot certify that.",
    }
    # Fit a full-region experimental detector even if it fails. Re-audit this
    # exact raster before any slot; it is not silently published as a winner.
    rng = np.random.default_rng(SEED)
    pos = np.flatnonzero(labels.ravel()[fp_idx])
    neg = np.flatnonzero((distance_all >= 9).ravel()[fp_idx])
    ti = np.r_[
        rng.choice(pos, min(30000, len(pos)), replace=False),
        rng.choice(neg, min(90000, len(neg)), replace=False),
    ]
    y = np.r_[np.ones(min(30000, len(pos)), np.int8), np.zeros(min(90000, len(neg)), np.int8)]
    ui = rng.choice(len(fp_idx), min(50000, len(fp_idx)), replace=False)
    resid = NuisanceResidualizer().fit(C[ui], G[ui])
    model = HistGradientBoostingClassifier(**PARAMS).fit(resid.transform(C[ti], G[ti]), y)
    score = np.zeros(fp.shape, np.float32)
    for begin in range(0, len(fp_idx), 50000):
        ii = np.arange(begin, min(begin + 50000, len(fp_idx)))
        score.ravel()[fp_idx[ii]] = model.predict_proba(resid.transform(C[ii], G[ii]))[:, 1].astype(
            np.float32
        )
    pred = np.zeros(fp.shape, bool)
    for f_id in range(4):
        pm, _ = select_ridges(score, (folds == f_id) & fp, support=fp, catalogue=labels)
        pred |= pm
    dest = ROOT / "out/h24-2a-residualized-experimental.tif"
    dest.parent.mkdir(exist_ok=True)
    submission.write_submission(
        pred.astype(np.float32), ROOT / "data/bridge/sample_submission.tif", dest
    )
    checks = submission.check_variants(dest, ROOT / "data/bridge/sample_submission.tif")
    if not checks["format_valid"]:
        raise SystemExit("Experimental artifact failed format validation")
    evidence["experimental_raster"] = {
        "path": str(dest.relative_to(ROOT)),
        "sha256": sha256_file(dest),
        "positive_pixels": int(pred.sum()),
        "format_checks": checks,
        "recommended_to_upload": False,
    }
    import joblib

    joblib.dump(
        {
            "model": model,
            "residualizer": resid,
            "feature_names": meta["names"],
            "nuisance_names": ckeys,
            "seed": SEED,
            "feature_matrix_sha256": meta["sha256"],
            "confounds_sha256": sha256_file(confounds.CONF / "confounds.npz"),
        },
        ROOT / "out/h24-2a-experimental-model.joblib",
        compress=3,
    )
    evidence["seconds"] = time.time() - t0
    evidence["complete_run"] = True
    path.write_text(json.dumps(evidence, indent=2) + "\n")
    print("DONE", json.dumps(evidence["decision"]), flush=True)


if __name__ == "__main__":
    with threadpool_limits(limits=2):
        run()
