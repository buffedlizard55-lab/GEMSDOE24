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


# Historical Holdout above remains for reproducing dated experiments only.
# This version fixes the mean-of-ratios / hide-and-recover mismatch in that
# protocol once, in the shared module, instead of creating a private evaluator.
SEGMENT_EVALUATOR_VERSION = "gems-segment-pooled-v1"


def pooled_components(rows):
    """Pool metric components, never average region-level DTI ratios."""
    from .metric import ALPHA, BETA, EPS

    keys = ("TP_w", "FP_w", "FN_w", "n_truth", "n_emitted")
    out = {k: float(sum(r[k] for r in rows)) for k in keys}
    den = out["TP_w"] + ALPHA * out["FP_w"] + BETA * out["FN_w"] + EPS
    out["dti"] = out["TP_w"] / den
    return out


def spatial_bootstrap_ci(blocks, *, draws=1999, seed=20261025):
    """Approximate 95% CI, resampling 10 km blocks and pooling their components."""
    from .metric import ALPHA, BETA, EPS

    x = np.asarray(blocks, np.float64)
    if x.ndim != 2 or x.shape[1] != 3 or not len(x) or not np.isfinite(x).all():
        raise ValueError("Finite nonempty block TP/FP/FN components required")
    if draws < 100 or np.any(x < -1e-9):
        raise ValueError("At least 100 draws and nonnegative components required")
    rng = np.random.default_rng(seed)
    # Small matrix (hundreds of spatial groups); do not store full raster draws.
    sampled = x[rng.integers(len(x), size=(draws, len(x)))].sum(axis=1)
    scores = sampled[:, 0] / (sampled[:, 0] + ALPHA * sampled[:, 1] + BETA * sampled[:, 2] + EPS)
    return {
        "level": 0.95,
        "interval": np.quantile(scores, [0.025, 0.975]).tolist(),
        "method": "percentile spatial-block bootstrap of pooled TPw/FPw/FNw",
        "block_pixels": 100,
        "block_size_m": 10000,
        "n_blocks": len(x),
        "resamples": draws,
        "seed": seed,
        "limitation": "Internal-validation uncertainty; geologic structures may cross blocks. Not a hidden-score interval.",
    }


class SegmentHoldout:
    """Whole-component, buffered, quadrant-blocked hide-and-recover context.

    ``visible`` is the ONLY catalogue a detector may read. Whole connected
    components touching validation or its collar are hidden everywhere, not
    merely clipped at a split line. ``train`` is independently spatially purged.
    The positive class is an imperfect mapped-fault proxy, not hidden new truth.
    """

    def __init__(self, footprint, labels, *, buffer_px=15):
        from scipy.ndimage import distance_transform_edt

        self.footprint = np.asarray(footprint, bool)
        self.labels = np.asarray(labels, bool)
        if (
            self.footprint.shape != self.labels.shape
            or self.footprint.ndim != 2
            or buffer_px < 3
            or np.any(self.labels & ~self.footprint)
            or not self.labels.any()
        ):
            raise ValueError("Aligned nonempty catalogue, footprint and >=3 px collar required")
        self.components, self.n_components = ndi_label(self.labels, structure=np.ones((3, 3), int))
        self.fold_grid, names = make_quadrant_folds(self.footprint)
        self.folds = []
        for f, name in enumerate(names):
            valid = self.footprint & (self.fold_grid == f)
            if not valid.any():
                raise ValueError(f"Empty spatial fold: {name}")
            collar = distance_transform_edt(~valid) <= buffer_px
            hidden_ids = np.unique(self.components[collar & self.labels])
            hidden_ids = hidden_ids[hidden_ids > 0]
            hidden = self.labels & np.isin(self.components, hidden_ids)
            visible = self.labels & ~hidden
            truth = hidden & valid
            if not truth.any():
                raise ValueError(f"No withheld positives: {name}")
            self.folds.append(
                {
                    "id": f,
                    "name": name,
                    "valid": valid,
                    "train": self.footprint & ~collar,
                    "visible": visible,
                    "truth": truth,
                    "hidden_component_ids": hidden_ids,
                }
            )
        self.buffer_px = buffer_px

    def score_fold(self, prediction, fold):
        """Use the common exact metric, then audit bootstrap contributions by KD tree."""
        from scipy.spatial import cKDTree

        from . import metric

        pred = np.asarray(prediction)
        if pred.shape != self.footprint.shape or not np.isin(pred, [0, 1]).all():
            raise ValueError("A finite aligned binary prediction is required")
        valid, visible, truth = fold["valid"], fold["visible"], fold["truth"]
        active_pred = pred.astype(bool) & valid & ~visible
        reference = metric.dti_score_fast(
            active_pred, truth, valid_mask=valid, catalogue_mask=visible
        )
        pyx, tyx = np.argwhere(active_pred), np.argwhere(truth)
        tp = (
            np.maximum(1 - cKDTree(pyx).query(tyx)[0] / metric.RADIUS_PX, 0)
            if len(pyx)
            else np.zeros(len(tyx))
        )
        fp = (
            1 - np.maximum(1 - cKDTree(tyx).query(pyx)[0] / metric.RADIUS_PX, 0)
            if len(tyx)
            else np.ones(len(pyx))
        )
        nx = (self.footprint.shape[1] + 99) // 100
        n = ((self.footprint.shape[0] + 99) // 100) * nx
        ti = (tyx[:, 0] // 100) * nx + tyx[:, 1] // 100
        pi = (pyx[:, 0] // 100) * nx + pyx[:, 1] // 100
        blocks = np.column_stack(
            [
                np.bincount(ti, weights=tp, minlength=n),
                np.bincount(pi, weights=fp, minlength=n),
                np.bincount(ti, weights=1 - tp, minlength=n),
            ]
        )
        if not np.allclose(
            blocks.sum(axis=0),
            [reference[k] for k in ("TP_w", "FP_w", "FN_w")],
            rtol=0,
            atol=1e-8,
        ):
            raise AssertionError("Bootstrap components disagree with shared exact metric")
        return reference, blocks

    def summarize(self, predictions, *, ci_draws=1999):
        if len(predictions) != len(self.folds):
            raise ValueError("One independent prediction per held-out fold required")
        rows, block_rows = [], []
        for pred, fold in zip(predictions, self.folds):
            result, blocks = self.score_fold(pred, fold)
            rows.append({"fold": fold["name"], **result})
            block_rows.append(blocks)
        blocks = np.sum(block_rows, axis=0)
        yy, xx = np.nonzero(self.footprint)
        nx = (self.footprint.shape[1] + 99) // 100
        active_blocks = np.unique((yy // 100) * nx + xx // 100)
        total = pooled_components(rows)
        return {
            "label": "HOLDOUT-DTI",
            "evaluator_version": SEGMENT_EVALUATOR_VERSION,
            **total,
            "n_withheld_positive_pixels": int(total["n_truth"]),
            "n_unique_withheld_components": self.n_components,
            "ci95": spatial_bootstrap_ci(blocks[active_blocks], draws=ci_draws),
            "folds": rows,
            "protocol": {
                "aggregation": "pooled TPw/FPw/FNw, not mean fold DTI",
                "buffer_m": self.buffer_px * 100,
                "whole_components_hidden_everywhere": True,
                "visible_fault_mask": "pixel-exact, applied before credit and FP calculation",
                "catalogue_features": "must be constructed from fold.visible only",
                "alpha": 0.2,
                "beta": 0.8,
                "triangular_kernel_radius_m": 300,
            },
        }

    def canary(self, features, *, seed=20261025, max_per_class=15000):
        """One-feature AUC diagnostics, never silently change a feature after a flag."""
        from scipy.ndimage import distance_transform_edt
        from sklearn.metrics import roc_auc_score

        rng = np.random.default_rng(seed)
        rows, samples = {}, []
        for fold in self.folds:
            truth, valid = fold["truth"], fold["valid"]
            positive = np.flatnonzero(truth)
            negative = np.flatnonzero(
                valid & ~fold["visible"] & (distance_transform_edt(~truth) >= 9)
            )
            positive = rng.choice(positive, min(len(positive), max_per_class), replace=False)
            negative = rng.choice(negative, min(len(negative), max_per_class), replace=False)
            samples.append((np.r_[positive, negative], len(positive), len(negative)))
        for name, surface in features.items():
            surface = np.asarray(surface)
            if surface.shape != self.footprint.shape:
                raise ValueError("Canary feature shape mismatch")
            details, values, labels = [], [], []
            for fold, (ids, n_positive, n_negative) in zip(self.folds, samples):
                x = surface.ravel()[ids]
                # Missingness itself is tested: use the same fixed zero sentinel
                # that the detector uses outside its supported physical domain.
                x = np.where(np.isfinite(x), x, 0)
                y = np.r_[np.ones(n_positive), np.zeros(n_negative)]
                auc = float(roc_auc_score(y, x))
                details.append(
                    {
                        "fold": fold["name"],
                        "auc": auc,
                        "positives": n_positive,
                        "background": n_negative,
                    }
                )
                values.append(x)
                labels.append(y)
            auc = float(roc_auc_score(np.concatenate(labels), np.concatenate(values)))
            suspicious = (
                max([max(auc, 1 - auc)] + [max(x["auc"], 1 - x["auc"]) for x in details]) > 0.90
            )
            rows[name] = {"pooled_auc": auc, "leakage_suspected": suspicious, "folds": details}
        return {
            "diagnostic": "LEAKAGE-CANARY AUC, not a DTI or organizer score",
            "evaluator_version": SEGMENT_EVALUATOR_VERSION,
            "threshold": 0.90,
            "two_polarities_checked": True,
            "passed": not any(x["leakage_suspected"] for x in rows.values()),
            "features": rows,
            "interpretation": "AUC > .90 is leakage until explained; lower AUC does not prove independence or fault discovery.",
        }
