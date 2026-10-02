"""Classifier two-sample test (C2S2) for distribution shift between pixel sets.

Formalism follows Lopez-Paz & Oquab, "The Classifier Two-Sample Test", ICLR 2017
(arXiv:1610.06539, https://arxiv.org/abs/1610.06539): draw two samples P and Q,
train a probabilistic classifier to discriminate them, and use its held-out
accuracy (here: cross-validated AUC) as the test statistic. P = Q iff the
classifier cannot beat the null distribution obtained by relabelling a sample
drawn from a single distribution. We obtain the null by two mechanisms:

  * ``perm``  — i.i.d. relabelling of the sampled pixels (permutation test);
  * ``shift`` — torus-shift the *fault mask* itself by a random offset and
    re-derive near/far sets, preserving spatial autocorrelation of both classes
    while breaking the true P/Q alignment (a stricter null for spatial data;
    cf. Dutkiewicz et al. 2023 permutation schemes for spatial point patterns,
    https://doi.org/10.1111/ecog.06258 - methods framing only).

In this project the test answers one question: can *non-geological* covariates
(acquisition window/block, lidar coverage, distance to field-work points,
optionally roads and mining claims) tell "near mapped fault" pixels apart from
"far" ones? If yes on the training labels, the catalogue's shape is confounded
by field accessibility; if yes on a *predicted* raster, that raster's gain is
partly mapping-process overfitting, which a same-catalogue spatial holdout
cannot catch.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import numpy as np
from scipy.ndimage import distance_transform_edt
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import StandardScaler


# --------------------------------------------------------------------------- datasets
def near_far_masks(reference: np.ndarray, near_px: int = 3, far_px: int = 9) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (near, far, dist) for a binary or continuous reference raster.

    near = distance to positive reference pixels <= near_px (the metric kernel R
    at 100 m: a prediction there could earn TP credit from a catalogue-class
    trace); far = distance >= far_px (>=300 m off every mapped trace).
    """
    pos = np.asarray(reference) > 0
    if not pos.any():
        raise ValueError("reference raster has no positive pixels")
    d = distance_transform_edt(~pos)
    near = d <= near_px
    far = d >= far_px
    return near, far, d


def build_matrix(feats: dict[str, np.ndarray], near: np.ndarray, far_pool: np.ndarray, fold: np.ndarray,
                 footprint: np.ndarray, n_per_class: int, seed: int) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict]:
    """Sub-sample balanced near/far pixels; return X, y, fold-id, info."""
    rng = np.random.default_rng(seed)
    ys, xs = np.nonzero(near & footprint)
    n_near = min(n_per_class, len(ys))
    sel = rng.choice(len(ys), size=n_near, replace=False) if len(ys) > n_near else np.arange(len(ys))
    rows_n, cols_n = ys[sel], xs[sel]
    ys, xs = np.nonzero(far_pool & footprint)
    n_far = min(n_per_class, len(ys))
    sel = rng.choice(len(ys), size=n_far, replace=False) if len(ys) > n_far else np.arange(len(ys))
    rows_f, cols_f = ys[sel], xs[sel]
    rows = np.concatenate([rows_n, rows_f])
    cols = np.concatenate([cols_n, cols_f])
    y = np.concatenate([np.ones(len(rows_n), dtype=np.int8), np.zeros(len(rows_f), dtype=np.int8)])
    f = fold[rows, cols].astype(np.int8)
    X = np.stack([np.asarray(feats[k], dtype=np.float32)[rows, cols] for k in sorted(feats)], axis=1)
    info = {"feature_names": sorted(feats), "n_near": int(len(rows_n)), "n_far": int(len(rows_f)),
            "n_near_total": int((near & footprint).sum()), "n_far_total": int((far_pool & footprint).sum())}
    return X, y, f, info


# --------------------------------------------------------------------------- models
def make_model(kind: str, seed: int = 0) -> Callable[[np.ndarray, np.ndarray], object]:
    if kind == "logit":
        def fit(X, y):
            sc = StandardScaler().fit(X)
            m = LogisticRegression(max_iter=400, C=0.5)
            m.fit(sc.transform(X), y)
            return ("sc", sc, m)
        return fit
    if kind == "hgb":
        def fit(X, y):
            m = HistGradientBoostingClassifier(
                max_iter=60, learning_rate=0.1, max_leaf_nodes=15,
                l2_regularization=1.0, early_stopping=False, random_state=seed,
            )
            m.fit(X, y)
            return ("m", m)
        return fit
    raise ValueError(kind)


def _predict(model, X, kind):
    if kind == "logit":
        _, sc, m = model
        return m.predict_proba(sc.transform(X))[:, 1]
    return model[1].predict_proba(X)[:, 1]


def spatial_cv_auc(fit, X, y, fold, kind) -> tuple[float, list[float]]:
    aucs = []
    for f in np.unique(fold[fold >= 0]):
        tr, te = (fold != f) & (fold >= 0), fold == f
        if te.sum() < 50 or len(np.unique(y[tr])) < 2:
            aucs.append(float("nan"))
            continue
        m = fit(X[tr], y[tr])
        p = _predict(m, X[te], kind)
        aucs.append(float(roc_auc_score(y[te], p)))
    mean = float(np.nanmean(aucs)) if len(aucs) else float("nan")
    return mean, [round(a, 5) for a in aucs]


# --------------------------------------------------------------------------- the test
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
        return {k: (round(v, 5) if isinstance(v, float) else v) for k, v in self.__dict__.items()}


def c2s2_test(
    surface_name: str,
    reference: np.ndarray,
    feats: dict[str, np.ndarray],
    fold: np.ndarray,
    footprint: np.ndarray,
    *,
    model_kind: str = "hgb",
    n_per_class: int = 120_000,
    n_null: int = 41,
    seed: int = 20261001,
    null_mode: str = "perm",
    shift_fn: Callable[[int, int], np.ndarray] | None = None,
) -> C2S2Result:
    """Run the C2S2 statistic + permutation null.

    ``shift_fn(dy,dx)`` must return the reference *class mask* translated on the
    grid (torus). When provided with ``null_mode='shift'``, the null is built by
    re-deriving the near set from shifted masks (spatially structured null).
    """
    rng = np.random.default_rng(seed)
    near, far, _d = near_far_masks(reference)
    fit = make_model(model_kind, seed)
    X, y, f, info = build_matrix(feats, near, far, fold, footprint, n_per_class, seed)
    obs, folds = spatial_cv_auc(fit, X, y, f, model_kind)

    nulls: list[float] = []
    if null_mode == "perm":
        for b in range(n_null):
            yp = y.copy()
            rng.shuffle(yp)
            a, _ = spatial_cv_auc(fit, X, yp, f, model_kind)
            nulls.append(a)
    elif null_mode == "shift":
        if shift_fn is None:
            raise ValueError("shift null needs shift_fn")
        for b in range(n_null):
            dy = int(rng.integers(-(footprint.shape[0] // 4), footprint.shape[0] // 4 + 1))
            dx = int(rng.integers(-(footprint.shape[1] // 4), footprint.shape[1] // 4 + 1))
            ref_s = shift_fn(dy, dx)
            near_s, far_s, _ = near_far_masks(ref_s)
            Xs, ys_, fs_, _ = build_matrix(feats, near_s, far_s, fold, footprint, n_per_class, seed + 1000 + b)
            a, _ = spatial_cv_auc(fit, Xs, ys_, fs_, model_kind)
            nulls.append(a)
    else:
        raise ValueError(null_mode)

    nulls_arr = np.asarray(nulls, dtype=np.float64)
    p95 = float(np.quantile(nulls_arr, 0.95))
    p = (1.0 + float(np.sum(nulls_arr >= obs))) / (1.0 + len(nulls_arr))
    return C2S2Result(
        surface=surface_name, model=model_kind, observed_auc=obs, fold_aucs=folds,
        null_kind=null_mode, n_null=len(nulls_arr),
        null_auc_mean=float(nulls_arr.mean()), null_auc_p95=p95, null_auc_max=float(nulls_arr.max()),
        margin_vs_p95=obs - p95, p_value=p, info={**info, "null_aucs": [round(a, 5) for a in nulls]},
    )


def drop_one_feature_auc(surface_name: str, reference: np.ndarray, feats: dict[str, np.ndarray], fold: np.ndarray,
                         footprint: np.ndarray, model_kind: str, n_per_class: int, seed: int) -> dict:
    """Univariate AUC per feature and leave-one-out ΔAUC of the full test."""
    out: dict = {"single_feature_auc": {}, "leave_one_out_delta_auc": {}}
    near, far, _ = near_far_masks(reference)
    fit = make_model(model_kind, seed)
    full_auc, _ = spatial_cv_auc(fit, *build_matrix(feats, near, far, fold, footprint, n_per_class, seed)[:3], model_kind)
    for k in sorted(feats):
        sub = {k: feats[k]}
        X, y, f, _ = build_matrix(sub, near, far, fold, footprint, n_per_class, seed)
        a, _ = spatial_cv_auc(fit, X, y, f, model_kind)
        out["single_feature_auc"][k] = round(a, 5)
    for k in sorted(feats):
        sub = {kk: v for kk, v in feats.items() if kk != k}
        X, y, f, _ = build_matrix(sub, near, far, fold, footprint, n_per_class, seed)
        a, _ = spatial_cv_auc(fit, X, y, f, model_kind)
        out["leave_one_out_delta_auc"][k] = round(full_auc - a, 5)
    return out
