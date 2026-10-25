"""Spatially blocked holdout used to gate hypotheses *before* any weekly submission slot is spent."""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy.ndimage import label as ndi_label

from .metric import dti_score_fast, ridge_nms, select_top_positive

BUDGET_FRAC = 0.025
FOLD_NAMES = ["NW", "NE_LidarGapHeavy", "SW", "SE"]


def make_quadrant_folds(footprint: np.ndarray) -> tuple[np.ndarray, list[str]]:
    footprint = np.asarray(footprint, bool)
    if footprint.ndim != 2 or not footprint.any():
        raise ValueError("A nonempty 2D footprint is required")
    yy, xx = np.nonzero(footprint)
    y_med, x_med = int(np.median(yy)), int(np.median(xx))
    H, W = footprint.shape
    gy, gx = np.ogrid[:H, :W]
    fold = np.full((H, W), -1, dtype=np.int8)
    fold[(gy < y_med) & (gx < x_med) & footprint] = 0
    fold[(gy < y_med) & (gx >= x_med) & footprint] = 1
    fold[(gy >= y_med) & (gx < x_med) & footprint] = 2
    fold[(gy >= y_med) & (gx >= x_med) & footprint] = 3
    return fold, list(FOLD_NAMES)


def thin_components(truth_2d: np.ndarray, keep_frac: float, seed: int) -> np.ndarray:
    if not 0 <= keep_frac <= 1:
        raise ValueError("Component fraction must be in [0,1]")
    comp, n = ndi_label(truth_2d, structure=np.ones((3, 3), dtype=int))
    if n == 0 or keep_frac == 0:
        return np.zeros_like(truth_2d, dtype=bool)
    rng = np.random.default_rng(seed)
    keep = rng.choice(np.arange(1, n + 1), size=max(1, int(round(keep_frac * n))), replace=False)
    return np.isin(comp, keep)


class Holdout:
    def __init__(
        self,
        footprint: np.ndarray,
        labels: np.ndarray,
        budget: float = BUDGET_FRAC,
        sparse_seed_offset: int = 0,
    ):
        footprint, labels = np.asarray(footprint, bool), np.asarray(labels, bool)
        if footprint.shape != labels.shape or not 0 <= budget <= 1:
            raise ValueError("Aligned grids and budget in [0,1] required")
        self.footprint = footprint
        self.labels = labels
        self.budget = budget
        self.fp_idx = np.flatnonzero(footprint.ravel())
        self.fold_2d, self.fold_names = make_quadrant_folds(footprint)
        self.quads = []
        for f_id, name in enumerate(self.fold_names):
            f_mask = (self.fold_2d == f_id) & footprint
            if not f_mask.any():
                raise ValueError(
                    f"Spatial quadrant {name} is empty; cannot claim a four-fold holdout"
                )
            r0, r1 = np.nonzero(f_mask.any(axis=1))[0][[0, -1]]
            c0, c1 = np.nonzero(f_mask.any(axis=0))[0][[0, -1]]
            sl = (slice(r0, r1 + 1), slice(c0, c1 + 1))
            t_dense = labels & f_mask
            t_sparse = thin_components(
                t_dense, keep_frac=0.20, seed=4242 + f_id + sparse_seed_offset
            )
            known = t_dense & ~t_sparse
            self.quads.append(
                (f_id, name, f_mask, sl, t_dense[sl], t_sparse[sl], known[sl], f_mask[sl])
            )

    def to_2d(self, p_fp: np.ndarray) -> np.ndarray:
        if np.asarray(p_fp).shape != (len(self.fp_idx),):
            raise ValueError("Footprint score vector length mismatch")
        a = np.zeros(self.footprint.shape, dtype=np.float32)
        a.ravel()[self.fp_idx] = p_fp
        return a

    def emit(
        self, p_fp: np.ndarray, *, ridge: bool = True, budget_per_quad: list[int] | None = None
    ) -> np.ndarray:
        """Per-quadrant top-budget binary mask over the full grid (ridge-thinned unless ``ridge=False``)."""
        score = self.to_2d(p_fp)
        if ridge:
            r = ridge_nms(score, self.footprint, sigma=1.0)
            boosted = np.where(r, score, 0)
        else:
            boosted = score
        out = np.zeros(self.footprint.shape, dtype=bool)
        for f_id, _n, f_mask, _sl, _td, _ts, _kc, fm in self.quads:
            k = (
                int(budget_per_quad[f_id])
                if budget_per_quad is not None
                else int(round(self.budget * fm.sum()))
            )
            out |= select_top_positive(boosted, f_mask, k)
        return out

    def score_mask(self, pred: np.ndarray) -> dict[str, Any]:
        dense, sparse, detail = [], [], {}
        for _f, name, _m, sl, td, ts, kc, fm in self.quads:
            rd = dti_score_fast(pred[sl], td, valid_mask=fm)
            rs = dti_score_fast(pred[sl], ts, valid_mask=fm, catalogue_mask=kc)
            dense.append(rd["dti"])
            sparse.append(rs["dti"])
            detail[name] = {
                "dense_dti": round(rd["dti"], 5),
                "sparse_dti": round(rs["dti"], 5),
                "dense_coverage": round(rd["coverage"], 4),
                "sparse_coverage": round(rs["coverage"], 4),
                "emitted_px": int(pred[sl].sum()),
            }
        return {
            "mean_dense_dti": round(float(np.mean(dense)), 5),
            "mean_sparse_dti": round(float(np.mean(sparse)), 5),
            "fold_dense": [round(x, 5) for x in dense],
            "fold_sparse": [round(x, 5) for x in sparse],
            "folds": detail,
        }

    def evaluate(self, p_fp: np.ndarray, *, ridge: bool = True) -> dict[str, Any]:
        return self.score_mask(self.emit(p_fp, ridge=ridge))

    def emit_quadrant(
        self, p_fp: np.ndarray, f_id: int, *, ridge: bool = True, k_override: int | None = None
    ) -> np.ndarray:
        score = self.to_2d(p_fp)
        boosted = (
            np.where(ridge_nms(score, self.footprint, sigma=1.0), score, 0) if ridge else score
        )
        _f, _n, f_mask, _sl, _td, _ts, _kc, fm = self.quads[f_id]
        k = int(k_override) if k_override is not None else int(round(self.budget * fm.sum()))
        return select_top_positive(boosted, f_mask, k)

    def score_quadrant(
        self, pred: np.ndarray, f_id: int, mode: str, mask_predictions: bool = False
    ) -> float:
        _f, _n, _m, sl, td, ts, kc, fm = self.quads[f_id]
        if mode == "dense":
            return dti_score_fast(pred[sl], td, valid_mask=fm)["dti"]
        return dti_score_fast(
            pred[sl], ts, valid_mask=fm, catalogue_mask=kc, mask_predictions=mask_predictions
        )["dti"]

    def known_for(self, f_id: int, mode: str) -> np.ndarray:
        _f, _n, f_mask, sl, _td, _ts, kc, _fm = self.quads[f_id]
        known = self.labels & ~f_mask
        if mode == "sparse":
            known = known.copy()
            known[sl] |= kc
        return known

    def evaluate_by_quadrant(self, surface_fn) -> dict[str, Any]:
        dense, sparse = [], []
        for f_id in range(len(self.quads)):
            dense.append(
                self.score_quadrant(
                    self.emit_quadrant(surface_fn(f_id, "dense"), f_id), f_id, "dense"
                )
            )
            sparse.append(
                self.score_quadrant(
                    self.emit_quadrant(surface_fn(f_id, "sparse"), f_id), f_id, "sparse"
                )
            )
        return {
            "mean_dense_dti": round(float(np.mean(dense)), 5),
            "mean_sparse_dti": round(float(np.mean(sparse)), 5),
            "fold_dense": [round(x, 5) for x in dense],
            "fold_sparse": [round(x, 5) for x in sparse],
        }


def gate(
    candidate: dict[str, Any],
    baseline: dict[str, Any],
    *,
    max_fold_loss: float = 0.01,
    min_mean_gain: float = 0.001,
) -> dict[str, Any]:
    """Pre-registered promotion rule.

    PASS requires: higher mean dense AND mean sparse DTI than the baseline; higher sparse DTI in >= 3 of 4 folds;
    and no fold losing more than ``max_fold_loss`` DTI (dense or sparse) relative to the baseline.
    """
    cd, cs = candidate["fold_dense"], candidate["fold_sparse"]
    bd, bs = baseline["fold_dense"], baseline["fold_sparse"]
    arrays = [np.asarray(a, float) for a in (cd, cs, bd, bs)]
    if any(a.shape != (4,) or np.any(~np.isfinite(a)) or np.any((a < 0) | (a > 1)) for a in arrays):
        raise ValueError("Gate requires four finite [0,1] fold scores for both candidates")
    if max_fold_loss < 0 or min_mean_gain < 0:
        raise ValueError("Gate tolerances must be nonnegative")
    means_consistent = all(
        abs(d[k] - float(np.mean(a))) <= 1e-4
        for d, a, k in (
            (candidate, arrays[0], "mean_dense_dti"),
            (candidate, arrays[1], "mean_sparse_dti"),
            (baseline, arrays[2], "mean_dense_dti"),
            (baseline, arrays[3], "mean_sparse_dti"),
        )
    )
    sparse_wins = int(sum(c > b for c, b in zip(cs, bs)))
    dense_wins = int(sum(c > b for c, b in zip(cd, bd)))
    worst_dense = round(min(c - b for c, b in zip(cd, bd)), 5)
    worst_sparse = round(min(c - b for c, b in zip(cs, bs)), 5)
    rules = {
        "reported_means_match_four_fold_scores": means_consistent,
        "mean_dense_improves": candidate["mean_dense_dti"] - baseline["mean_dense_dti"]
        > min_mean_gain,
        "mean_sparse_improves": candidate["mean_sparse_dti"] - baseline["mean_sparse_dti"]
        > min_mean_gain,
        "sparse_fold_wins_ge_3_of_4": sparse_wins >= 3,
        "no_fold_loses_more_than_0_01": worst_dense >= -max_fold_loss
        and worst_sparse >= -max_fold_loss,
    }
    return {
        "passed": all(rules.values()),
        "rules": rules,
        "sparse_fold_wins": sparse_wins,
        "dense_fold_wins": dense_wins,
        "worst_fold_delta_dense": worst_dense,
        "worst_fold_delta_sparse": worst_sparse,
        "delta_mean_dense": round(candidate["mean_dense_dti"] - baseline["mean_dense_dti"], 5),
        "delta_mean_sparse": round(candidate["mean_sparse_dti"] - baseline["mean_sparse_dti"], 5),
    }


# Legacy Holdout above remains for reproduction of historical evidence. It is NOT
# the authority for the parallel-run segment protocol below.
SEGMENT_EVALUATOR_VERSION = "segment-hide-recover-pooled-v1"


def segment_folds(footprint, labels, buffer_px=30):
    """Hide whole 8-connected components touching each quadrant.

    Components are a conservative raster proxy for segments, not expert trace IDs.
    Components that cross quadrant boundaries can be withheld in multiple folds,
    but each scored positive pixel belongs to only one quadrant.
    All catalogue-based features MUST consume only the yielded visible grid.
    """
    from scipy.ndimage import distance_transform_edt

    fp, truth = np.asarray(footprint, bool), np.asarray(labels, bool)
    if fp.shape != truth.shape or np.any(truth & ~fp) or buffer_px < 0:
        raise ValueError("Aligned footprint/truth, truth inside footprint and buffer >=0 required")
    components, count = ndi_label(truth, structure=np.ones((3, 3), int))
    if not count:
        raise ValueError("No fault components to withhold")
    fold_grid, names = make_quadrant_folds(fp)
    for fold, name in enumerate(names):
        test = fp & (fold_grid == fold)
        ids = np.unique(components[test & truth])
        if not len(ids):
            raise ValueError(f"No withheld positive components in {name}")
        selected = np.zeros(count + 1, bool)
        selected[ids] = True
        hidden = selected[components]
        visible = truth & ~hidden
        # Exclude the entire test region and a buffer from every hidden segment
        # and test boundary when deriving/fitting any train-dependent features.
        training = fp & (distance_transform_edt(~(test | hidden)) > buffer_px)
        yield {
            "name": name,
            "fold": fold,
            "test": test,
            "hidden": hidden,
            "visible": visible,
            "training": training,
            "n_withheld_components": int(len(ids)),
            "n_withheld_whole_segment_pixels": int(hidden.sum()),
            "n_withheld_positives": int((hidden & test).sum()),
            "buffer_px": buffer_px,
        }


def pooled_dti(components):
    """Ratio of SUMMED TP/FP/FN, never an average of fold scores."""
    from .metric import ALPHA, BETA, EPS

    a = np.asarray(components, dtype=np.float64)
    if a.ndim != 2 or a.shape[1] != 3 or not np.isfinite(a).all() or np.any(a < -1e-8):
        raise ValueError("Finite nonnegative [TP,FP,FN] rows required")
    tp, false_positive, fn = a.sum(axis=0)
    return float(tp / (tp + ALPHA * false_positive + BETA * fn + EPS))


def spatial_components(prediction, truth, valid, visible, tile_px=200):
    """Exact binary DTI decomposed by spatial tile for cluster bootstrap.

    Distances are computed on the full evaluation domain BEFORE tile attribution;
    there are no artificial tile-edge penalties. Known pixels are masked exactly.
    Contributions are assigned to the truth pixel for TP/FN, prediction pixel for FP.
    """
    from scipy.spatial import cKDTree

    from .metric import RADIUS_PX, dti_score_fast

    if tile_px < 1:
        raise ValueError("Positive spatial tile size required")
    # Reference call validates inputs, masks visible faults and supplies exact
    # components. KD-trees only attribute these same components to spatial tiles.
    reference = dti_score_fast(prediction, truth, valid_mask=valid, catalogue_mask=visible)
    active = np.asarray(valid, bool) & ~np.asarray(visible, bool)
    pp = np.argwhere(active & (np.asarray(prediction) > 0))
    gg = np.argwhere(active & np.asarray(truth, bool))
    ncols = (active.shape[1] + tile_px - 1) // tile_px
    nrows = (active.shape[0] + tile_px - 1) // tile_px
    rows = np.zeros((ncols * nrows, 3), dtype=np.float64)

    def tile_ids(points):
        return (points[:, 0] // tile_px) * ncols + points[:, 1] // tile_px

    credit = np.zeros(len(gg))
    if len(pp) and len(gg):
        credit = np.maximum(1 - cKDTree(pp).query(gg)[0] / RADIUS_PX, 0)
    if len(gg):
        np.add.at(rows[:, 0], tile_ids(gg), credit)
        np.add.at(rows[:, 2], tile_ids(gg), 1 - credit)
    penalty = np.ones(len(pp))
    if len(gg) and len(pp):
        penalty = 1 - np.maximum(1 - cKDTree(gg).query(pp)[0] / RADIUS_PX, 0)
    if len(pp):
        np.add.at(rows[:, 1], tile_ids(pp), penalty)
    expected = [reference[k] for k in ("TP_w", "FP_w", "FN_w")]
    if not np.allclose(rows.sum(axis=0), expected, rtol=1e-10, atol=1e-7):
        raise AssertionError("Spatial components disagree with shared exact metric")
    return rows, reference


def pooled_bootstrap(rows, *, paired=None, resamples=1000, seed=20261025):
    """Conditional spatial cluster-bootstrap CI; paired rows must use identical tiles."""
    a = np.asarray(rows, dtype=np.float64)
    pooled_dti(a)  # validates even when all tiles have zero contribution
    if len(a) < 2 or resamples < 2:
        raise ValueError("At least two clusters and two resamples required")
    b = None if paired is None else np.asarray(paired, dtype=np.float64)
    if b is not None:
        pooled_dti(b)
        if b.shape != a.shape:
            raise ValueError("Paired cluster grids must match")
    rng = np.random.default_rng(seed)
    scores = []
    for _ in range(resamples):
        ids = rng.integers(0, len(a), len(a))
        value = pooled_dti(a[ids])
        if b is not None:
            value -= pooled_dti(b[ids])
        scores.append(value)
    return [float(x) for x in np.quantile(scores, [0.025, 0.975])]
