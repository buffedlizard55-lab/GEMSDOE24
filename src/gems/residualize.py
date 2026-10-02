"""Training-only conditional-mean removal of measured nuisance features.

This is an observational robustness intervention, not causal identification.
Residuals may retain variance/nonlinear dependence; the emitted raster must be
re-audited. No coordinates, fault distances or labels enter the nuisance model.
"""

from __future__ import annotations

import numpy as np
from sklearn.linear_model import Ridge
from sklearn.preprocessing import SplineTransformer


class NuisanceResidualizer:
    def __init__(self, distance_columns: int = 2, alpha: float = 100.0):
        self.distance_columns = distance_columns
        self.alpha = alpha

    def _basis(self, c: np.ndarray, *, fit=False) -> np.ndarray:
        d = c[:, : self.distance_columns]
        cats = c[:, self.distance_columns :]
        if fit:
            self.spline = SplineTransformer(
                n_knots=5, degree=2, knots="uniform", include_bias=False, extrapolation="constant"
            ).fit(d)
        b = self.spline.transform(d).astype(np.float32)
        # Pairwise road/claim interactions plus acquisition-by-access interactions.
        pieces = [b, cats]
        if self.distance_columns == 2:
            half = b.shape[1] // 2
            pieces.append((b[:, :half, None] * b[:, None, half:]).reshape(len(c), -1))
        if cats.shape[1]:
            pieces.append((b[:, :, None] * cats[:, None, :]).reshape(len(c), -1))
        return np.column_stack(pieces).astype(np.float32)

    def fit(self, nuisance_train: np.ndarray, geology_train: np.ndarray):
        c, g = np.asarray(nuisance_train, np.float32), np.asarray(geology_train, np.float32)
        if c.ndim != 2 or g.ndim != 2 or len(c) != len(g) or self.distance_columns < 1:
            raise ValueError("Aligned 2D training matrices and at least one distance required")
        if np.any(~np.isfinite(c)):
            raise ValueError("Nuisance distances cannot be missing/imputed from geology")
        if self.distance_columns > c.shape[1]:
            raise ValueError("distance_columns exceeds nuisance dimensionality")
        # Fit both imputation and scaling solely on the unsupervised training sample.
        self.median = np.nanmedian(g, axis=0)
        self.median = np.where(np.isfinite(self.median), self.median, 0).astype(np.float32)
        lo, hi = np.nanquantile(g, [0.25, 0.75], axis=0)
        self.scale = np.where(np.isfinite(hi - lo) & ((hi - lo) > 1e-6), hi - lo, 1).astype(
            np.float32
        )
        z = self.standardize(g)
        self.model = Ridge(alpha=self.alpha).fit(self._basis(c, fit=True), z)
        self.n_train = len(c)
        return self

    def standardize(self, geology: np.ndarray) -> np.ndarray:
        g = np.asarray(geology, np.float32)
        return np.clip(
            (np.where(np.isfinite(g), g, self.median) - self.median) / self.scale, -8, 8
        ).astype(np.float32)

    def transform(self, nuisance: np.ndarray, geology: np.ndarray, *, remove=True) -> np.ndarray:
        z = self.standardize(geology)
        if not remove:
            return z
        c = np.asarray(nuisance, np.float32)
        if np.any(~np.isfinite(c)):
            raise ValueError("Missing nuisance feature at inference")
        return np.clip(z - self.model.predict(self._basis(c)), -8, 8).astype(np.float32)
