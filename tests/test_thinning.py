"""Geodesic dot-thinning invariants: subset, minimum spacing, maximality, determinism."""

from __future__ import annotations

import numpy as np
import pytest
from scipy.ndimage import distance_transform_edt, label

from gems.metric import dti_score_fast
from gems.thinning import dot_thin, neighbour_profile


def line_mask(n=60, shape=(5, 70)):
    m = np.zeros(shape, bool)
    m[2, 3 : 3 + n] = True
    return m


def test_min_dist_one_or_less_is_identity_copy():
    m = line_mask()
    out = dot_thin(m, 1.0)
    assert np.array_equal(out, m) and out is not m


def test_horizontal_line_spacing_is_exactly_three_at_2p8():
    out = dot_thin(line_mask(), 2.8)
    xs = np.flatnonzero(out[2])
    assert set(np.diff(xs)) == {3}
    assert xs[0] == 3  # seed is the lowest raster index of the component


def test_diagonal_line_uses_the_shorter_lattice_step():
    m = np.zeros((70, 70), bool)
    for i in range(60):
        m[i + 2, i + 2] = True
    out = dot_thin(m, 2.8)
    ys, xs = np.nonzero(out)
    steps = np.hypot(np.diff(ys), np.diff(xs))
    assert np.allclose(steps, 2 * np.sqrt(2))  # two diagonal steps = 2.83 px >= 2.8


def test_subset_min_spacing_and_maximality_on_random_blobs():
    rng = np.random.default_rng(0)
    m = rng.random((120, 140)) < 0.12
    m[40:60, 30:90] = True
    for d in (1.5, 2.0, 2.8, 4.2):
        out = dot_thin(m, d)
        assert not (out & ~m).any()  # never adds a pixel
        ys, xs = np.nonzero(out)
        if len(ys) > 1:
            from scipy.spatial import cKDTree

            dist, _ = cKDTree(np.c_[ys, xs]).query(np.c_[ys, xs], k=2)
            assert dist[:, 1].min() >= d - 1e-9
        # maximal: every original pixel is within min_dist of a kept pixel
        near = distance_transform_edt(~out)
        assert (near[m] < d + 1e-9).all()
        # a component is dropped only if it is entirely within min_dist of another kept pixel
        comp, n = label(m, structure=np.ones((3, 3), int))
        kept_ids = set(np.unique(comp[out]).tolist())
        for cid in set(range(1, n + 1)) - kept_ids:
            assert (near[comp == cid] < d).all()


def test_deterministic_bytes():
    rng = np.random.default_rng(3)
    m = rng.random((80, 90)) < 0.2
    assert np.array_equal(dot_thin(m, 2.8), dot_thin(m.copy(), 2.8))


def test_isolated_pixels_are_preserved():
    m = np.zeros((40, 40), bool)
    m[5, 5] = m[5, 20] = m[30, 30] = True
    assert np.array_equal(dot_thin(m, 3.2), m)


def test_rejects_non_2d_and_handles_empty():
    with pytest.raises(ValueError):
        dot_thin(np.zeros((3, 3, 3), bool), 2.0)
    assert not dot_thin(np.zeros((10, 10), bool), 2.0).any()


def test_profile_counts_neighbours_and_components():
    m = line_mask(10)
    p = neighbour_profile(m)
    assert p["pixels"] == 10 and p["components"] == 1
    assert p["one_neighbour"] == pytest.approx(0.2) and p["two_neighbours"] == pytest.approx(0.8)


def test_dotting_a_true_trace_keeps_most_credit_for_a_third_of_the_pixels():
    """The kernel arithmetic the module rests on, checked with the repo's exact metric."""
    truth = np.zeros((9, 200), bool)
    truth[4, 10:190] = True
    solid = truth.copy()
    dotted = dot_thin(solid, 2.8)
    s = dti_score_fast(solid, truth)
    d = dti_score_fast(dotted, truth)
    assert dotted.sum() / solid.sum() == pytest.approx(1 / 3, abs=0.02)
    assert d["coverage"] == pytest.approx(0.78, abs=0.03)
    assert s["coverage"] == pytest.approx(1.0, abs=1e-9)


def test_dotting_a_false_trace_cuts_false_positive_mass_proportionally():
    truth = np.zeros((40, 200), bool)
    truth[4, 10:190] = True
    false_line = np.zeros_like(truth)
    false_line[30, 10:190] = True  # 26 px from the truth: all false positive
    dotted = dot_thin(false_line, 2.8)
    s = dti_score_fast(false_line, truth)
    d = dti_score_fast(dotted, truth)
    assert d["FP_w"] / s["FP_w"] == pytest.approx(1 / 3, abs=0.02)
