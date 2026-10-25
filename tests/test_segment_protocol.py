"""Regression tests for the shared parallel-run evaluator, novelty and ASPC."""

import numpy as np
import pytest
from scipy.ndimage import label
from scipy.spatial import cKDTree
from scipy.stats import spearmanr

from gems import aspc, holdout, novelty
from gems.metric import dti_score_fast


def scene():
    fp = np.ones((80, 80), bool)
    truth = np.zeros_like(fp)
    truth[15, 5:70] = True  # crosses quadrant boundary: must hide whole component
    truth[65, 5:20] = True
    truth[65, 55:70] = True
    return fp, truth


def test_whole_components_hidden_with_buffer_and_no_shared_visible_pixels():
    fp, truth = scene()
    comps, _ = label(truth, np.ones((3, 3)))
    folds = list(holdout.segment_folds(fp, truth, buffer_px=5))
    for f in folds:
        hidden_ids = np.unique(comps[f["hidden"]])
        assert not np.isin(comps[f["visible"]], hidden_ids).any()
        assert not (f["visible"] & f["hidden"]).any()
        assert np.array_equal(f["visible"] | f["hidden"], truth)
        assert not (f["training"] & (f["test"] | f["hidden"])).any()
        if f["training"].any():
            d = cKDTree(np.argwhere(f["test"] | f["hidden"])).query(np.argwhere(f["training"]))[0]
            assert d.min() > 5
    assert sum(f["n_withheld_positives"] for f in folds) == truth.sum()
    assert folds[0]["hidden"][15, 65]


def test_pooled_is_not_fold_average():
    rows = np.array([[1, 0, 0], [1, 100, 9]], float)
    pooled = holdout.pooled_dti(rows)
    assert pooled == pytest.approx(2 / (2 + 20 + 7.2 + 1e-7))
    assert abs(pooled - np.mean([holdout.pooled_dti(r[None]) for r in rows])) > 0.2


def test_tile_metric_is_exact_across_tile_edges_and_visible_is_pixel_exact():
    fp = np.ones((30, 30), bool)
    truth = np.zeros_like(fp)
    truth[10, 10] = truth[14, 20] = True
    pred = np.zeros_like(fp)
    pred[9, 10] = pred[14, 19] = pred[29, 29] = True
    visible = np.zeros_like(fp)
    visible[29, 29] = True
    rows, metric = holdout.spatial_components(pred, truth, fp, visible, tile_px=10)
    expected = dti_score_fast(pred, truth, valid_mask=fp, catalogue_mask=visible)
    assert np.allclose(rows.sum(0), [expected[k] for k in ("TP_w", "FP_w", "FN_w")])
    assert holdout.pooled_dti(rows) == pytest.approx(metric["dti"])
    assert expected["n_emitted"] == 2  # visible prediction masked, adjacent one retained
    assert holdout.pooled_bootstrap(rows, paired=rows, resamples=20) == [0.0, 0.0]


def test_no_truth_or_no_predictions_has_exact_components():
    a = np.zeros((10, 10), bool)
    b = a.copy()
    b[5, 5] = True
    for p, g in ((a, b), (b, a), (a, a)):
        rows, _ = holdout.spatial_components(p, g, np.ones_like(a), a, tile_px=5)
        assert np.allclose(rows.sum(0), [0, p.sum(), g.sum()])


def test_novelty_matches_scipy_and_thresholds_are_strict_inclusive_radius():
    rng = np.random.default_rng(24)
    a = rng.random(500)
    b = (rng.random(500) > 0.8).astype(int)
    assert novelty.correlation(a, b) == pytest.approx(spearmanr(a, b).statistic)
    assert novelty.correlation(a, np.zeros(500)) is None
    assert not novelty.is_duplicate(0.90, 0.70)
    assert novelty.is_duplicate(0.90001) and novelty.is_duplicate(None, 0.70001)
    p, r = np.zeros((10, 10), bool), np.zeros((10, 10), bool)
    p[2, 2] = r[2, 5] = True
    assert novelty.dot_overlap(p, r)["candidate_within_3px_of_reference"] == 1
    r[2, 5] = False
    r[2, 6] = True
    assert novelty.dot_overlap(p, r)["candidate_within_3px_of_reference"] == 0


def test_decode_zero_missing_and_endpoints_and_formula_without_labels():
    assert np.allclose(aspc.decode(np.array([0, 1, 128, 255]), 1, "sqrt"), [0, 0, 0.25, 1])
    bands = {name: np.full((20, 20), 128, np.uint8) for name in aspc.BANDS}
    surface, canaries, support, control = aspc.factors(bands, np.ones((20, 20), bool))
    assert np.isfinite(surface).all() and ((surface >= 0) & (surface <= 1)).all()
    assert set(canaries) >= set(aspc.BANDS) and support.all() and (control > 0).all()
    bands["valid"][:] = 1  # decoded valid fraction zero even though encoded sample is nonzero
    assert not aspc.factors(bands, np.ones((20, 20), bool))[2].any()


def test_dot_placement_deterministic_separated_no_wrap_and_no_random_fill():
    s = np.ones((20, 20), np.float32)
    p = aspc.place_dots(s, np.ones_like(s, bool), 20)
    assert np.array_equal(p, aspc.place_dots(s, np.ones_like(s, bool), 20))
    assert p.sum() == 20
    assert cKDTree(np.argwhere(p)).query(np.argwhere(p), k=2)[0][:, 1].min() >= 3
    with pytest.raises(ValueError, match="available"):
        aspc.place_dots(s, np.zeros_like(s, bool), 20)


def test_reject_nonbinary_probabilities_and_invalid_pool_components():
    with pytest.raises(ValueError):
        holdout.pooled_dti(np.array([[1, -2, 3]]))
    with pytest.raises(ValueError, match="binary"):
        holdout.spatial_components(
            np.full((10, 10), 0.5),
            np.zeros((10, 10), bool),
            np.ones((10, 10), bool),
            np.zeros((10, 10), bool),
        )
