"""Fixed TNR1 nuisance intervention; no labels or catalogue geometry enter it.

Only the prespecified non-topographic channels are transformed. Leaving terrain
unchanged is a testable inference hypothesis, not a claim of geological causality.
"""

from __future__ import annotations

import numpy as np

from .residualize import NuisanceResidualizer

ENGINEERED_NAMES = (
    "saturating_scarp_g_sat",
    "radiometric_alteration_r_alt",
    "basement_step_b_step",
    "hydrothermal_conduit_h",
)
TARGET_NAMES = (
    "rtp",
    "tmi_hg",
    "tmi_vg",
    "iso_grav_anom",
    "iso_grav_anom_hg",
    "iso_grav_anom_vg",
    "tmi",
    "cond_surf",
    "depth_to_base_surf",
    "radiometric_alteration_r_alt",
    "basement_step_b_step",
    "hydrothermal_conduit_h",
)
HGB_PARAMS = {
    "max_iter": 80,
    "max_leaf_nodes": 15,
    "learning_rate": 0.08,
    "l2_regularization": 5.0,
    "early_stopping": False,
    "random_state": 20261026,
}


class TargetedResidualizer:
    def __init__(self, names, targets=TARGET_NAMES):
        self.names, self.targets = tuple(names), tuple(targets)
        if (
            not self.names
            or len(set(self.names)) != len(self.names)
            or not self.targets
            or len(set(self.targets)) != len(self.targets)
            or not set(self.targets).issubset(self.names)
        ):
            raise ValueError("Unique named columns and a nonempty known target subset required")
        self.indices = np.asarray([self.names.index(name) for name in self.targets])
        self.unchanged_indices = np.asarray(
            [i for i, name in enumerate(self.names) if name not in self.targets], dtype=int
        )
        self.residualizer = NuisanceResidualizer(distance_columns=2, alpha=100.0)
        self.fitted = False

    def _matrix(self, geology):
        values = np.asarray(geology, dtype=np.float32)
        if values.ndim != 2 or values.shape[1] != len(self.names):
            raise ValueError("Geological matrix does not match the declared feature columns")
        if np.isinf(values).any():
            raise ValueError("Infinity is not a missing geological observation")
        return values

    def fit(self, nuisance_train, geology_train):
        values = self._matrix(geology_train)
        self.residualizer.fit(nuisance_train, values[:, self.indices])
        self.fitted = True
        return self

    def transform(self, nuisance, geology):
        if not self.fitted:
            raise ValueError("Fit only on a declared training sample before transforming")
        values = self._matrix(geology).copy()
        values[:, self.indices] = self.residualizer.transform(
            nuisance, values[:, self.indices], remove=True
        )
        return values

    def receipt(self):
        if not self.fitted:
            raise ValueError("No fitted intervention exists")
        return {
            "target_columns": list(self.targets),
            "unchanged_columns": [self.names[i] for i in self.unchanged_indices],
            "n_training_rows": self.residualizer.n_train,
            "fit_scope": "uniform sample from the explicitly supplied training mask only",
            "nuisance_model": "shared NuisanceResidualizer: spline interactions + Ridge(alpha=100)",
            "geological_claim": "observational robustness test, not causal identification",
        }
