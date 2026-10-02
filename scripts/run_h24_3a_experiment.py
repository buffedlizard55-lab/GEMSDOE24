#!/usr/bin/env python3
"""Preregistered H24-3A potential-field contact-persistence experiment.

Four arms share identical folds, training-only standardization/nuisance fits,
and model parameters. Historical rasters are evaluated as emitted only. The
full-scene upward continuation is transductive in the unlabeled geology; a
20 km training exclusion collar limits (but cannot eliminate) its long-range
spatial dependence. This script never consumes a competition submission slot.
"""

from __future__ import annotations

import argparse
import hashlib
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
from gems.scale_space import contact_persistence  # noqa: E402
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
FOLD_BUFFER_M = 20_000
HEIGHTS_M = (100.0, 200.0, 400.0)
FIELDS = ("rtp", "tmi", "iso_grav_anom")


def select_ridges(score, valid, fraction=BUDGET, *, support=None, catalogue=None):
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


def build_persistence_maps(
    fp: np.ndarray,
    G: np.ndarray,
    names: list[str],
    cache: Path,
    *,
    source_matrix_sha256: str,
    force: bool,
):
    cache.parent.mkdir(parents=True, exist_ok=True)
    name_to_idx = {name: i for i, name in enumerate(names)}
    missing = sorted(set(FIELDS) - set(name_to_idx))
    if missing:
        raise SystemExit(f"Required preregistered potential fields missing: {missing}")
    input_hash = hashlib.sha256(
        json.dumps(
            {
                "source_feature_names": names,
                "source_matrix_sha256": source_matrix_sha256,
                "scale_space_code_sha256": sha256_file(ROOT / "src/gems/scale_space.py"),
                "selected_fields": FIELDS,
                "heights_m": HEIGHTS_M,
                "shape": fp.shape,
                "cell_size_m": 100,
                "edge_guard_m": 1600,
            },
            sort_keys=True,
        ).encode()
    ).hexdigest()
    meta_path = cache.with_suffix(".json")
    if cache.exists() and meta_path.exists() and not force:
        meta = json.loads(meta_path.read_text())
        if meta.get("input_manifest_sha256") == input_hash and meta.get("sha256") == sha256_file(
            cache
        ):
            return np.load(cache, mmap_mode="r"), meta

    temp = cache.with_suffix(".tmp.npy")
    maps = np.lib.format.open_memmap(
        temp, mode="w+", dtype=np.float32, shape=(*fp.shape, len(FIELDS))
    )
    maps[:] = np.nan
    for field_id, field_name in enumerate(FIELDS):
        source = np.full(fp.shape, np.nan, dtype=np.float32)
        source.ravel()[np.flatnonzero(fp)] = np.asarray(
            G[:, name_to_idx[field_name]], dtype=np.float32
        )
        feature = contact_persistence(
            source,
            heights_m=HEIGHTS_M,
            cell_size_m=100.0,
            edge_guard_m=4.0 * HEIGHTS_M[-1],
        )
        maps[:, :, field_id] = feature
        del source, feature
        maps.flush()
        print(f"computed {field_name} scale-space persistence", flush=True)
    del maps
    temp.replace(cache)
    meta = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "input_manifest_sha256": input_hash,
        "sha256": sha256_file(cache),
        "shape": [*fp.shape, len(FIELDS)],
        "feature_names": [f"{name}_upward_persistence_100_400m" for name in FIELDS],
        "source_fields": list(FIELDS),
        "heights_m": list(HEIGHTS_M),
        "cell_size_m": 100.0,
        "edge_guard_m": 1600.0,
        "formula": "min(max3x3(|grad U200|), max3x3(|grad U400|))/max3x3(|grad U100|), clipped [0,1], times unoriented gradient alignment (100 m vs 400 m); U_h transfer exp(-2*pi*h*|k|)",
        "missing_cells": "nearest-finite fill for convolution only; restored to NaN, and 1.6 km edge guard excluded",
        "transform_scope": "full-scene unlabeled geology; transductive physical context, no label access",
        "limitation": "Poisson upward-continuation kernel is nonlocal; 20 km holdout training collar leaves residual dependence",
    }
    meta_path.write_text(json.dumps(meta, indent=2) + "\n")
    return np.load(cache, mmap_mode="r"), meta


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-partial-audit-inputs", action="store_true")
    parser.add_argument("--force-features", action="store_true")
    args = parser.parse_args()
    t0 = time.time()

    fp = footprint.load_footprint()
    fp_idx = np.flatnonzero(fp)
    with rasterio.open(ROOT / "data/bridge/labels.tif") as ds:
        labels = (ds.read(1) > 0) & fp
    folds, names = holdout.make_quadrant_folds(fp)
    feature_path = ROOT / "data/prepared/features.npy"
    feature_meta = json.loads((feature_path.parent / "features.json").read_text())
    G = np.load(feature_path, mmap_mode="r")
    if G.shape[1] != len(feature_meta["names"]) or feature_meta["base_count"] != 27:
        raise SystemExit("Prepared geology matrix disagrees with its signed feature manifest")
    cache = ROOT / "data/prepared/h24_3a_persistence.npy"
    P, pmeta = build_persistence_maps(
        fp,
        G,
        feature_meta["names"],
        cache,
        source_matrix_sha256=feature_meta["sha256"],
        force=args.force_features,
    )
    Pfp = np.asarray(P.reshape(-1, len(FIELDS))[fp_idx], dtype=np.float32)

    provenance = json.loads((confounds.CONF / "provenance.json").read_text())
    audit_complete = bool(provenance["full_requested_audit_available"])
    if not audit_complete and not args.allow_partial_audit_inputs:
        raise SystemExit(
            "Verified four-block membership is absent; pass --allow-partial-audit-inputs "
            "only for an explicitly provisional, no-slot experiment"
        )
    with np.load(confounds.CONF / "confounds.npz") as conf:
        cfeat = confounds.classifier_features(conf)
    if not {"road_m", "claim_m"} <= set(cfeat):
        raise SystemExit("Verified road and closed mining-claim distances are required")
    ckeys = ["road_m", "claim_m"] + sorted(set(cfeat) - {"road_m", "claim_m"})
    C = np.column_stack([cfeat[k].ravel()[fp_idx] for k in ckeys]).astype(np.float32)
    del cfeat
    if not np.isfinite(C).all():
        raise SystemExit("A requested nuisance source is missing inside the footprint")
    if any(f"block_{i}" in ckeys for i in range(1, 5)) and not all(
        f"block_{i}" in ckeys for i in range(1, 5)
    ):
        raise SystemExit("Partial acquisition-block categories cannot enter the experiment")

    comps, _ = label(labels, structure=np.ones((3, 3), int))
    arms = (
        "physics_raw",
        "physics_persistence_raw",
        "physics_residualized",
        "physics_persistence_residualized",
    )
    results = {arm: [] for arm in arms}
    historical = {}
    for tag in ("h19-4", "h19-5"):
        paths = sorted((ROOT / "inputs").glob(f"*{tag}*-nan.tif"))
        if len(paths) != 1:
            raise SystemExit(f"Expected exactly one immutable {tag} reference raster")
        with rasterio.open(paths[0]) as ds:
            historical[tag] = ((ds.read(1) > 0.5) & fp, paths[0])
    historical_scores = {tag: [] for tag in historical}

    evidence = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "hypothesis": "H24-3A multiscale potential-field contact persistence",
        "preregistration": "knowledge/04_remaining_hypotheses_2026-10-02.md",
        "protocol": {
            "seed": SEED,
            "detector_params": PARAMS,
            "budget": BUDGET,
            "folds": "same four contiguous quadrants as the preregistered holdout",
            "training_exclusion_collar_m": FOLD_BUFFER_M,
            "collar_rationale": "pre-implementation amendment: exact 400 m upward-continuation Poisson kernel has about 2% integrated mass outside 20 km",
            "labels": "catalogue trace pixels only; not verified fault absence",
            "negatives": "training-region unlabelled cells at least 900 m from training-region catalogue traces",
            "components": "every 8-connected trace component touching the held-out quadrant or 20 km collar is removed from supervised training",
            "nuisance_training_only": True,
            "nuisance_regression": "training-only uniform 30000-pixel sample; quadratic splines and interactions; Ridge alpha=100",
            "missing_block_policy": "use only verified road and closed-claim distances; no Area1/Area2 substitution; experiment is provisional",
            "transform_scope": "full-scene unlabeled geology; transductive physical field calculation, never labels",
            "historical_comparability": "as-emitted DTI diagnostic on identical held-out quadrants; original H19 training/OOF cache is unavailable",
        },
        "feature_transform": pmeta,
        "geology_features": {
            "baseline": feature_meta["names"][: feature_meta["base_count"]],
            "candidate_additions": pmeta["feature_names"],
            "base_feature_manifest_sha256": feature_meta["sha256"],
        },
        "nuisance_names": ckeys,
        "access_inputs_complete": audit_complete,
        "missing_required": provenance["missing_required"],
        "folds": [],
        "results": {},
        "historical_diagnostics": {},
        "submission_slot_spent": False,
        "promoted": False,
    }

    d_labels = distance_transform_edt(~labels)
    for fold_id, name in enumerate(names):
        rng = np.random.default_rng(SEED + fold_id)
        val = (folds == fold_id) & fp
        collar = distance_transform_edt(~val) <= FOLD_BUFFER_M / 100.0
        excluded_components = np.unique(comps[collar & labels])
        excluded_components = excluded_components[excluded_components > 0]
        train_mask = fp & ~collar
        positive_mask = labels & train_mask & ~np.isin(comps, excluded_components)
        # Use only training labels to define the negative buffer; held-out labels
        # never influence class membership in supervised training.
        d_train_labels = distance_transform_edt(
            ~(labels & train_mask & ~np.isin(comps, excluded_components))
        )
        negative_mask = train_mask & (d_train_labels >= 9)
        pos_ids = np.flatnonzero(positive_mask.ravel()[fp_idx])
        neg_ids = np.flatnonzero(negative_mask.ravel()[fp_idx])
        if min(len(pos_ids), len(neg_ids)) < 100:
            raise SystemExit(
                f"Insufficient independent components after the preregistered 20 km collar in {name}; fail closed"
            )
        pos_ids = rng.choice(pos_ids, min(20000, len(pos_ids)), replace=False)
        neg_ids = rng.choice(neg_ids, min(60000, len(neg_ids)), replace=False)
        train_ids = np.r_[pos_ids, neg_ids]
        y = np.r_[np.ones(len(pos_ids), np.int8), np.zeros(len(neg_ids), np.int8)]
        uniform = np.flatnonzero(train_mask.ravel()[fp_idx])
        uniform = rng.choice(uniform, min(30000, len(uniform)), replace=False)

        X_uniform = np.column_stack((G[uniform, : feature_meta["base_count"]], Pfp[uniform]))
        residualizer = NuisanceResidualizer(distance_columns=2).fit(C[uniform], X_uniform)
        support = binary_dilation(val, structure=np.ones((3, 3), bool), iterations=7) & fp
        val_ids = np.flatnonzero(support.ravel()[fp_idx])
        yy, xx = np.nonzero(val)
        sl = (slice(yy.min(), yy.max() + 1), slice(xx.min(), xx.max() + 1))
        truth = labels & val
        sparse_truth = holdout.thin_components(truth, 0.20, 4242 + fold_id)
        known_sparse = truth & ~sparse_truth

        def score_mask(prediction):
            return {
                "fold": name,
                "dense": metric.dti_score_fast(prediction[sl], truth[sl], valid_mask=val[sl]),
                "sparse": metric.dti_score_fast(
                    prediction[sl],
                    sparse_truth[sl],
                    valid_mask=val[sl],
                    catalogue_mask=known_sparse[sl],
                ),
            }

        for tag, (prediction, _) in historical.items():
            historical_scores[tag].append(score_mask(prediction))

        evidence["folds"].append(
            {
                "name": name,
                "n_positive_train": len(pos_ids),
                "n_unlabelled_train": len(neg_ids),
                "n_excluded_components": int(len(excluded_components)),
                "held_out_trace_pixels": int(truth.sum()),
                "held_out_sparse_pixels": int(sparse_truth.sum()),
                "training_touches_validation": bool((train_mask & val).any()),
                "training_component_leak": bool(
                    np.isin(comps[positive_mask], excluded_components).any()
                ),
            }
        )

        for arm in arms:
            remove_nuisance = arm.endswith("residualized")
            add_persistence = "persistence" in arm
            X_train = np.column_stack((G[train_ids, : feature_meta["base_count"]], Pfp[train_ids]))
            Z_train = residualizer.transform(C[train_ids], X_train, remove=remove_nuisance)
            if not add_persistence:
                Z_train = Z_train[:, : feature_meta["base_count"]]
            model = HistGradientBoostingClassifier(**PARAMS).fit(Z_train, y)
            scores = np.zeros(fp.shape, dtype=np.float32)
            for begin in range(0, len(val_ids), 30000):
                ids = val_ids[begin : begin + 30000]
                X = np.column_stack((G[ids, : feature_meta["base_count"]], Pfp[ids]))
                Z = residualizer.transform(C[ids], X, remove=remove_nuisance)
                if not add_persistence:
                    Z = Z[:, : feature_meta["base_count"]]
                scores.ravel()[fp_idx[ids]] = model.predict_proba(Z)[:, 1].astype(np.float32)
            pred, selection = select_ridges(scores, val, support=support)
            row = score_mask(pred)
            row["selection"] = selection
            results[arm].append(row)
            print(name, arm, row["dense"]["dti"], row["sparse"]["dti"], flush=True)

        evidence["results"] = {arm: summary(rows) for arm, rows in results.items()}
        evidence["historical_diagnostics"] = {
            tag: summary(rows) for tag, rows in historical_scores.items()
        }
        (ROOT / "evidence/h24_3a_experiment.json").write_text(json.dumps(evidence, indent=2) + "\n")

    candidate = evidence["results"]["physics_persistence_residualized"]
    paired_gates = {}
    for baseline_arm in ("physics_raw", "physics_residualized"):
        gate_result = holdout.gate(candidate, evidence["results"][baseline_arm])
        gate_result["minimum_effect_passed"] = bool(
            gate_result["delta_mean_dense"] > 0.001 and gate_result["delta_mean_sparse"] > 0.001
        )
        paired_gates[baseline_arm] = gate_result
    historical_gates = {
        tag: holdout.gate(candidate, summary(rows)) for tag, rows in historical_scores.items()
    }
    evidence["paired_gate"] = paired_gates
    evidence["historical_diagnostic_gate"] = historical_gates
    paired_pass = all(g["passed"] and g["minimum_effect_passed"] for g in paired_gates.values())
    hist_pass = all(g["passed"] for g in historical_gates.values())
    evidence["decision"] = {
        "candidate_beats_paired_baselines": paired_pass,
        "candidate_beats_historical_diagnostics": hist_pass,
        "original_h19_holdout_reproduced": False,
        "full_accessibility_audit_complete": audit_complete,
        "comparable_current_best_oof_reproduced": False,
        "promoted": False,
        "reason": "No promotion or submission slot without paired improvement, a complete three-family accessibility audit, and a comparable reproduced current-best OOF result. The current official four-block membership is unavailable.",
    }

    # Make an exact experimental raster so the final prediction can be audited;
    # binary output remains a prototype, never a new submission recommendation.
    rng = np.random.default_rng(SEED)
    full_pos = np.flatnonzero(labels.ravel()[fp_idx])
    full_neg = np.flatnonzero((d_labels >= 9).ravel()[fp_idx])
    n_pos, n_neg = min(30000, len(full_pos)), min(90000, len(full_neg))
    fit_ids = np.r_[
        rng.choice(full_pos, n_pos, replace=False),
        rng.choice(full_neg, n_neg, replace=False),
    ]
    y_full = np.r_[np.ones(n_pos, np.int8), np.zeros(n_neg, np.int8)]
    uniform = rng.choice(len(fp_idx), min(50000, len(fp_idx)), replace=False)
    X_uniform = np.column_stack((G[uniform, : feature_meta["base_count"]], Pfp[uniform]))
    full_residualizer = NuisanceResidualizer(distance_columns=2).fit(C[uniform], X_uniform)
    X_full = np.column_stack((G[fit_ids, : feature_meta["base_count"]], Pfp[fit_ids]))
    model = HistGradientBoostingClassifier(**PARAMS).fit(
        full_residualizer.transform(C[fit_ids], X_full, remove=True), y_full
    )
    full_scores = np.zeros(fp.shape, dtype=np.float32)
    for begin in range(0, len(fp_idx), 30000):
        ids = np.arange(begin, min(begin + 30000, len(fp_idx)))
        X = np.column_stack((G[ids, : feature_meta["base_count"]], Pfp[ids]))
        Z = full_residualizer.transform(C[ids], X, remove=True)
        full_scores.ravel()[fp_idx[ids]] = model.predict_proba(Z)[:, 1].astype(np.float32)
    full_mask = np.zeros(fp.shape, dtype=bool)
    for fold_id in range(4):
        fold_valid = (folds == fold_id) & fp
        selected, _ = select_ridges(full_scores, fold_valid, support=fp, catalogue=labels)
        full_mask |= selected

    dest = ROOT / "out/h24-3a-contact-persistence-20261002-experimental.tif"
    dest.parent.mkdir(parents=True, exist_ok=True)
    submission.write_submission(
        full_mask.astype(np.float32),
        ROOT / "data/bridge/sample_submission.tif",
        dest,
    )
    checks = submission.check_variants(dest, ROOT / "data/bridge/sample_submission.tif")
    if not checks["format_valid"]:
        raise SystemExit("Experimental raster failed the official-grid/format checks")
    evidence["experimental_raster"] = {
        "path": str(dest.relative_to(ROOT)),
        "sha256": sha256_file(dest),
        "positive_pixels": int(full_mask.sum()),
        "format_checks": checks,
        "recommended_to_upload": False,
        "note": "Exact full-region binary experimental raster; not a submission candidate unless all independent gates pass.",
    }
    evidence["seconds"] = time.time() - t0
    evidence["complete_run"] = True
    evidence["submission_slot_spent"] = False
    (ROOT / "evidence/h24_3a_experiment.json").write_text(json.dumps(evidence, indent=2) + "\n")
    print("DONE", json.dumps(evidence["decision"]), flush=True)


if __name__ == "__main__":
    with threadpool_limits(limits=2):
        main()
