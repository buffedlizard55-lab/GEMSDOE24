import numpy as np
import pytest

from gems import emission, metric


def _line_mask(shape=(40, 120), row=20):
    m = np.zeros(shape, bool)
    m[row, 5:-5] = True
    return m


def test_cover_is_deterministic_subset_with_exact_count():
    m = _line_mask()
    a = emission.kernel_cover_thin(m, 0.34)
    b = emission.kernel_cover_thin(m, 0.34)
    assert np.array_equal(a, b)
    assert (a & ~m).sum() == 0
    assert a.sum() == round(0.34 * m.sum())


def test_cover_edges_and_validation():
    m = _line_mask()
    assert np.array_equal(emission.kernel_cover_thin(m, 1.0), m)
    empty = np.zeros_like(m)
    assert not emission.kernel_cover_thin(empty, 0.5).any()
    with pytest.raises(ValueError):
        emission.kernel_cover_thin(m, 0.0)
    with pytest.raises(ValueError):
        emission.kernel_cover_thin(m, 1.2)
    with pytest.raises(ValueError):
        emission.kernel_cover_thin(m.ravel(), 0.5)
    with pytest.raises(ValueError):
        emission.kernel_cover_thin(m, 0.5, weights=np.full(m.shape, np.nan))


def test_cover_spreads_pixels_and_beats_random_thinning():
    m = _line_mask()
    keep = 1 / 3
    cover = emission.kernel_cover_thin(m, keep)
    cols = np.sort(np.nonzero(cover)[1])
    gaps = np.diff(cols)
    assert gaps.max() <= 6  # no unnecessary hole along the line
    cover_credit = emission.kernel_credit(cover)[m].mean()
    rand_credit = np.mean(
        [emission.kernel_credit(emission.random_thin(m, keep, s))[m].mean() for s in range(20)]
    )
    assert cover_credit > rand_credit + 0.05


def test_random_thin_is_reproducible_and_same_size():
    m = _line_mask()
    r1, r2 = emission.random_thin(m, 0.4, 7), emission.random_thin(m, 0.4, 7)
    assert np.array_equal(r1, r2) and r1.sum() == round(0.4 * m.sum())
    assert not emission.random_thin(np.zeros_like(m), 0.4, 1).any()


def _synthetic_world(seed=0, size=600, n_lines=12, length=60):
    rng = np.random.default_rng(seed)
    truth = np.zeros((size, size), bool)
    for _ in range(n_lines):
        r, c = rng.integers(40, size - 40, 2)
        if rng.random() < 0.5:
            truth[r, max(c - length // 2, 0) : c + length // 2] = True
        else:
            truth[max(r - length // 2, 0) : r + length // 2, c] = True
    return truth


def test_lattice_calibration_recovers_known_truth_density():
    truth = _synthetic_world()
    fp = np.ones(truth.shape, bool)
    known = np.zeros_like(fp)
    lattice = np.zeros_like(fp)
    lattice[2::5, 2::5] = True
    score = metric.dti_score_fast(lattice, truth, valid_mask=fp)["dti"]
    got = emission.lattice_truth_density(lattice, fp, known, score)
    true_tau = truth.sum() / fp.sum()
    assert got["tau"] == pytest.approx(true_tau, rel=0.25)


def test_lattice_calibration_rejects_impossible_score():
    fp = np.ones((60, 60), bool)
    lattice = np.zeros_like(fp)
    lattice[::5, ::5] = True
    with pytest.raises(ValueError):
        emission.lattice_truth_density(lattice, fp, np.zeros_like(fp), 0.9)
    with pytest.raises(ValueError):
        emission.lattice_truth_density(lattice, fp, np.zeros_like(fp), 0.0)


def test_model_round_trip_and_identity_extrapolation():
    tp = emission.implied_credit(0.19, 0.023, 0.00244, phi=0.05)
    assert emission.model_dti(tp, 0.023, 0.00244, phi=0.05) == pytest.approx(0.19, rel=1e-9)
    area = 5_000_000
    same = emission.extrapolate_variant(0.19, 115_000, 115_000, 1.0, area, 0.00244)
    assert same == pytest.approx(0.19, rel=1e-9)
    assert emission.extrapolate_variant(0.19, 115_000, 40_000, 0.8, area, 0.00244) > 0.19
    with pytest.raises(ValueError):
        emission.extrapolate_variant(0.19, 1, 1, 1.5, area, 0.002)


def test_thinning_helps_only_when_false_positive_mass_dominates():
    """Exact metric on synthetic truth: noisy dense ridge mask, sparse vs dense truth."""
    rng = np.random.default_rng(1)
    size = 500
    fp = np.ones((size, size), bool)
    sparse_truth = np.zeros((size, size), bool)
    sparse_truth[250, 100:160] = True
    sparse_truth[100:140, 400] = True
    dense_truth = np.zeros_like(sparse_truth)
    for r in range(20, size, 12):
        dense_truth[r, 20:-20] = True
    ridge = np.zeros_like(sparse_truth)
    for r in rng.choice(np.arange(10, size - 10), 60, replace=False):
        ridge[r, 20:-20] = True  # long lines, almost all wrong
    ridge[250, 90:170] = True  # one correct line
    ridge[90:150, 400] = True
    cover = emission.kernel_cover_thin(ridge, 0.34)
    base = metric.dti_score_fast(ridge, sparse_truth, valid_mask=fp)["dti"]
    thin = metric.dti_score_fast(cover, sparse_truth, valid_mask=fp)["dti"]
    assert thin > base  # FP-dominated regime: fewer pixels win
    dense_base = metric.dti_score_fast(ridge, dense_truth, valid_mask=fp)["dti"]
    dense_thin = metric.dti_score_fast(cover, dense_truth, valid_mask=fp)["dti"]
    assert dense_thin < dense_base * 1.0 + 1e-9  # dense truth rewards coverage, not thinning
