"""Classifier two-sample testing (C2ST), adapted to a spatial pixel population.

Lopez-Paz & Oquab, *Revisiting Classifier Two-Sample Tests*, ICLR 2017:
https://arxiv.org/abs/1610.06545 . The previous arXiv id 1610.06539 was wrong.
The paper uses held-out accuracy. We use a prespecified held-out AUC statistic
and refit the identical classifier for every randomization.

A classifier detecting a distributional association does NOT establish its
cause; geological, economic and topographic selection remain alternatives.
A non-rejection is NOT proof of equal distributions or absence of bias.
A torus shift on an irregular, nonstationary footprint is not an exact spatial
randomization. The primary null uses non-wrapping translations of the entire
reference mask; its tail probability is a stationarity-based sensitivity
diagnostic, not a classical exact p-value. IID label shuffles are diagnostic only.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Callable

import numpy as np
from scipy.ndimage import distance_transform_edt
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score
from threadpoolctl import threadpool_limits


class MissingClassError(ValueError):
    """A spatial cohort is not evaluable; never substitute chance AUC."""


@dataclass
class C2S2Result:
    surface: str
    model: str
    observed_auc: float
    fold_aucs: list[float]
    null_kind: str
    n_null: int
    null_auc_mean: float
    null_auc_p95: float
    null_auc_max: float
    margin_vs_p95: float
    p_value: float
    info: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        # Keep unrounded values in evidence; rounding is presentation-only.
        return dict(self.__dict__)


def near_far_masks(reference: np.ndarray, near_px: float = 3, far_px: float = 9):
    """NEAR <=300 m, FAR >=900 m on the 100 m grid; intermediate pixels excluded."""
    ref = np.asarray(reference)
    if ref.ndim != 2 or not (0 <= near_px < far_px):
        raise ValueError("2D reference and 0<=near<far required")
    pos = np.isfinite(ref) & (ref > 0)
    if not pos.any():
        raise ValueError("reference raster has no positive pixels")
    d = distance_transform_edt(~pos)
    return d <= near_px, d >= far_px, d


def translate_no_wrap(reference: np.ndarray, dy: int, dx: int) -> np.ndarray:
    """Translate a 2D reference without toroidal wraparound or label padding."""
    a = np.asarray(reference)
    if a.ndim != 2:
        raise ValueError("A spatial translation requires a 2D reference")
    out = np.zeros_like(a)
    h, w = a.shape
    src_y0, src_y1 = max(0, -dy), min(h, h - dy)
    src_x0, src_x1 = max(0, -dx), min(w, w - dx)
    if src_y0 >= src_y1 or src_x0 >= src_x1:
        return out
    dst_y0, dst_y1 = max(0, dy), min(h, h + dy)
    dst_x0, dst_x1 = max(0, dx), min(w, w + dx)
    out[dst_y0:dst_y1, dst_x0:dst_x1] = a[src_y0:src_y1, src_x0:src_x1]
    return out


def build_matrix(feats, near, far_pool, fold, footprint, n_per_class, seed):
    if not feats or n_per_class < 10:
        raise ValueError("Features and at least 10 pixels per class are required")
    shape = footprint.shape
    if any(np.asarray(a).shape != shape for a in (near, far_pool, fold, *feats.values())):
        raise ValueError("All feature/reference/fold grids must match")
    valid = footprint & (fold >= 0)
    for a in feats.values():
        valid &= np.isfinite(a)
    pools = [np.flatnonzero(near & valid), np.flatnonzero(far_pool & valid)]
    n = min(n_per_class, *(len(p) for p in pools))
    if n < 10:
        raise ValueError("Insufficient finite near/far samples; no proxy/padding used")
    rng = np.random.default_rng(seed)
    rows = np.concatenate([rng.choice(p, size=n, replace=False) for p in pools])
    y = np.repeat([1, 0], n).astype(np.int8)
    X = np.column_stack([np.asarray(feats[k]).ravel()[rows] for k in sorted(feats)]).astype(
        np.float32
    )
    f = fold.ravel()[rows].astype(np.int8)
    yy, xx = np.unravel_index(rows, shape)
    block = (yy // 100) * ((shape[1] + 99) // 100) + xx // 100
    info = {
        "feature_names": sorted(feats),
        "n_near": n,
        "n_far": n,
        "n_near_total": len(pools[0]),
        "n_far_total": len(pools[1]),
        "rows": rows,
        "spatial_blocks": block,
    }
    return X, y, f, info


def make_model(kind: str = "hgb", seed: int = 0):
    if kind != "hgb":
        raise ValueError("Audited implementation fixes model_kind=hgb; no post-hoc model selection")

    def fit(X, y):
        return HistGradientBoostingClassifier(
            max_iter=25,
            learning_rate=0.1,
            max_leaf_nodes=7,
            l2_regularization=5.0,
            early_stopping=False,
            random_state=seed,
        ).fit(X, y)

    return fit


def spatial_cv_auc(fit, X, y, fold, kind="hgb", *, groups=None, purge_groups=None):
    aucs = []
    for f_id in np.unique(fold[fold >= 0]):
        tr, te = (fold != f_id) & (fold >= 0), fold == f_id
        if purge_groups is not None:
            tr &= ~np.isin(groups, purge_groups[int(f_id)])
        if tr.sum() < 10 or te.sum() < 10 or len(np.unique(y[tr])) < 2 or len(np.unique(y[te])) < 2:
            raise MissingClassError(f"Fold {f_id} lacks both classes after spatial purging")
        m = fit(X[tr], y[tr])
        aucs.append(float(roc_auc_score(y[te], m.predict_proba(X[te])[:, 1])))
    if len(aucs) < 2:
        raise ValueError("At least two held-out spatial folds required")
    return float(np.mean(aucs)), aucs


def holm_adjust(p_values: list[float]) -> list[float]:
    """Holm family-wise adjustment, preserving original hypothesis order."""
    p = np.asarray(p_values, float)
    if p.ndim != 1 or np.any(~np.isfinite(p)) or np.any((p < 0) | (p > 1)):
        raise ValueError("Invalid p values")
    order = np.argsort(p)
    adj = np.minimum(1, np.maximum.accumulate((len(p) - np.arange(len(p))) * p[order]))
    out = np.empty(len(p))
    out[order] = adj
    return out.tolist()


def c2s2_test(
    surface_name,
    reference,
    feats,
    fold,
    footprint,
    *,
    model_kind="hgb",
    n_per_class=12000,
    n_null=199,
    seed=20261002,
    null_mode="shift",
    shift_fn: Callable | None = None,
    purge_groups=None,
):
    if n_null < 1:
        raise ValueError("At least one refitted null replicate required")
    if null_mode not in {"shift", "perm"}:
        raise ValueError("Only spatial-shift and explicit iid-diagnostic nulls are supported")
    if null_mode == "shift" and shift_fn is None:
        raise ValueError("shift null requires an explicit non-wrapping geometry function")
    rng = np.random.default_rng(seed)
    near, far, _ = near_far_masks(reference)
    fit = make_model(model_kind, seed)
    X, y, f, info = build_matrix(feats, near, far, fold, footprint, n_per_class, seed)
    groups = info.pop("spatial_blocks")
    info.pop("rows")
    unique_groups = np.unique(groups)
    info.update(
        seed=seed,
        block_size_m=10000,
        n_spatial_blocks=len(unique_groups),
        near_m=300,
        far_m=900,
        statistic="unweighted mean of per-fold ROC AUC",
        null_resolution=1 / (n_null + 1),
        refit_every_null=True,
        model_params={"max_iter": 25, "max_leaf_nodes": 7, "l2_regularization": 5.0},
        null_assumption="non-wrapping spatial-shift stationarity diagnostic; not an exact randomization p-value"
        if null_mode == "shift"
        else "iid pixel exchangeability; diagnostic only and not spatially valid",
    )
    kwargs = {"groups": groups, "purge_groups": purge_groups}
    nulls = []
    rejected_shifts = Counter()
    shift_draws = []
    with threadpool_limits(limits=2):
        observed, folds = spatial_cv_auc(fit, X, y, f, model_kind, **kwargs)
        for b in range(n_null):
            if null_mode == "perm":
                a, _ = spatial_cv_auc(fit, X, rng.permutation(y), f, model_kind, **kwargs)
            elif null_mode == "shift":
                if shift_fn is None:
                    raise ValueError("shift null requires an explicit geometry shift function")
                # A shift with a single-class held-out cohort has no AUC. Use
                # geometry/cohort support ONLY (never score) to condition this
                # diagnostic. Record every rejected draw and cap retries.
                for attempt in range(20):
                    while True:
                        dy = int(
                            rng.integers(
                                -max(10, footprint.shape[0] // 4),
                                max(10, footprint.shape[0] // 4) + 1,
                            )
                        )
                        dx = int(
                            rng.integers(
                                -max(10, footprint.shape[1] // 4),
                                max(10, footprint.shape[1] // 4) + 1,
                            )
                        )
                        if np.hypot(dy, dx) >= 10:
                            break
                    draw = {"dy_px": dy, "dx_px": dx, "replicate": b, "valid": False}
                    shift_draws.append(draw)
                    try:
                        ns, fs, _ = near_far_masks(shift_fn(dy, dx))
                        Xs, ys, ff, inf = build_matrix(
                            feats,
                            ns,
                            fs,
                            fold,
                            footprint,
                            n_per_class,
                            seed + 1000 + len(shift_draws) - 1,
                        )
                        a, _ = spatial_cv_auc(
                            fit,
                            Xs,
                            ys,
                            ff,
                            model_kind,
                            groups=inf["spatial_blocks"],
                            purge_groups=purge_groups,
                        )
                    except MissingClassError as exc:
                        rejected_shifts[str(exc)] += 1
                        draw["reason"] = str(exc)
                        continue
                    draw["valid"] = True
                    break
                else:
                    raise ValueError(
                        "Could not obtain evaluable shift cohorts in 20 geometry-only attempts; diagnostic incomplete"
                    )
            else:
                raise ValueError(null_mode)
            nulls.append(a)
    na = np.asarray(nulls)
    p95 = float(np.quantile(na, 0.95))
    p_value = float((1 + np.count_nonzero(na >= observed)) / (len(na) + 1))
    info["null_aucs"] = nulls
    if null_mode == "shift":
        info["shift_draws"] = shift_draws
        info["rejected_single_class_shifts"] = dict(rejected_shifts)
        info["conditional_geometry_design"] = (
            "requested number of valid non-wrapping shifts; single-class fold draws excluded on support only, never AUC; diagnostic not an exact spatial test"
        )
        info["p_value_interpretation"] = (
            "Empirical upper-tail proportion among valid shifted references; relies on approximate spatial stationarity and must not be reported as an exact randomization p-value."
        )
        info["valid_shift_count"] = len(nulls)
    return C2S2Result(
        surface_name,
        model_kind,
        observed,
        folds,
        null_mode,
        len(na),
        float(na.mean()),
        p95,
        float(na.max()),
        observed - p95,
        p_value,
        info,
    )
