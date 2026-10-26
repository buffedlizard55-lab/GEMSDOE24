"""Unit tests for H24-CUP1 label-free transforms (support erosion, finiteness)."""

import numpy as np

from gems import cup


def _grid(seed=0, shape=(240, 240)):
    return (np.random.default_rng(seed).random(shape) * 100).astype(np.float32)


def test_support_erodes_interior_only():
    valid = np.ones((50, 50), bool)
    sup = cup._support(valid, 5)
    assert sup[25, 25] and not sup[0, 0] and not sup[4, 25] and sup[6, 25]


def test_grad_and_contrast_are_nan_outside_support_and_finite_inside():
    a, valid = _grid(), np.ones((240, 240), bool)
    g = cup._grad(a, valid, 1.0, 8)
    c = cup._local_contrast(a, valid, 5.0)
    assert np.isnan(g[0, 0]) and np.isfinite(g[120, 120]) and np.all(g[np.isfinite(g)] >= 0)
    assert np.isnan(c[0, 0]) and np.isfinite(c[120, 120])


def test_nodata_hole_cannot_create_a_score_at_its_centre():
    a, valid = _grid(), np.ones((240, 240), bool)
    valid[100:140, 100:140] = False
    g = cup._grad(a, valid, 1.0, 8)
    c = cup._local_contrast(a, valid, 8.0)
    assert np.isnan(g[120, 120]) and np.isnan(c[120, 120])


def test_feature_name_count_matches_preregistration():
    assert len(cup.CUP_FEATURE_NAMES) == 16
    assert len(set(cup.CUP_FEATURE_NAMES)) == 16
    assert all(n.startswith("cup_") for n in cup.CUP_FEATURE_NAMES)
