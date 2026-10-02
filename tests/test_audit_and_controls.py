"""Regression tests for the repaired spatial audit, geometry and interventions."""

import numpy as np
import pytest
from shapely.geometry import shape

from gems import arcs, c2s2, confounds, holdout, metric
from gems.residualize import NuisanceResidualizer


def test_known_pixel_cannot_credit_adjacent_new_truth_in_either_scorer():
    known = np.zeros((15, 15), bool)
    known[7, 7] = True
    truth = np.zeros_like(known)
    truth[7, 8] = True
    for f in (metric.dti_score_fast, metric.dti_components_exact):
        assert f(known, truth, catalogue_mask=known)["TP_w"] == 0
        assert f(known, truth, catalogue_mask=known, mask_predictions=False)["dti"] == 0


def test_catalogue_truth_is_excluded_and_exact_fast_masking_agree():
    rng = np.random.default_rng(7)
    truth = rng.random((30, 30)) < 0.05
    p = rng.random((30, 30)) < 0.08
    known = rng.random((30, 30)) < 0.10
    valid = rng.random((30, 30)) > 0.2
    fast = metric.dti_score_fast(p, truth, valid, known)
    exact = metric.dti_components_exact(p, truth, valid, known)
    for k in ("dti", "TP_w", "FP_w", "FN_w"):
        assert fast[k] == pytest.approx(exact[k], abs=1e-10)
    assert fast["n_truth"] == np.count_nonzero(truth & valid & ~known)


def test_soft_scores_cannot_silently_use_binary_dti():
    with pytest.raises(ValueError, match="binary-only"):
        metric.dti_score_fast(np.full((10, 10), 0.3), np.ones((10, 10), bool))


def test_invalid_dti_grid_and_range_fail_closed():
    for pred in (
        np.ones((2, 3)),
        np.full((3, 3), 1.1),
        np.full((3, 3), np.inf),
        np.full((3, 3), np.nan),
    ):
        with pytest.raises(ValueError):
            metric.dti_components_exact(pred, np.ones((3, 3)))


def test_boundary_or_invalid_padding_is_not_a_ridge():
    s = np.ones((70, 70), np.float32)
    valid = np.ones_like(s, bool)
    valid[:, 30:34] = False
    assert not metric.ridge_nms(s, valid).any()


def test_zero_budget_empty_candidates_and_ties_are_deterministic():
    s = np.zeros((8, 8))
    valid = np.ones_like(s, bool)
    assert not metric.select_top_positive(s, valid, 12).any()
    s[2, 1:4] = 1
    assert not metric.select_top_positive(s, valid, 0).any()
    p = metric.select_top_positive(s, valid, 2)
    assert list(np.flatnonzero(p)) == [17, 18]
    assert metric.select_top_positive(s, valid, 100).sum() == 3


def test_component_thinning_handles_no_components_or_zero_fraction():
    t = np.zeros((12, 12), bool)
    assert not holdout.thin_components(t, 0.2, 1).any()
    t[5, 5] = True
    assert not holdout.thin_components(t, 0, 1).any()
    assert holdout.thin_components(t, 0.2, 1).sum() == 1
    with pytest.raises(ValueError):
        holdout.thin_components(t, 1.1, 1)


def test_empty_footprint_and_empty_spatial_quadrant_are_not_four_fold_cv():
    with pytest.raises(ValueError):
        holdout.make_quadrant_folds(np.zeros((10, 10), bool))
    t = np.ones((1, 20), bool)
    with pytest.raises(ValueError, match="empty"):
        holdout.Holdout(t, np.zeros_like(t))


def scores(values):
    return {
        "fold_dense": values,
        "fold_sparse": values,
        "mean_dense_dti": float(np.mean(values)),
        "mean_sparse_dti": float(np.mean(values)),
    }


def test_gate_checks_fold_counts_reported_means_and_minimum_gain():
    base = scores([0.1] * 4)
    assert holdout.gate(scores([0.102] * 4), base)["passed"]
    assert not holdout.gate(scores([0.1005] * 4), base)["passed"]
    incorrect = scores([0.102] * 4)
    incorrect["mean_dense_dti"] = 0.8
    assert not holdout.gate(incorrect, base)["passed"]
    for values in ([0.2, 0.2], [0.2, 0.2, 0.2, np.nan]):
        with pytest.raises(ValueError):
            holdout.gate(scores(values), base)


def test_radial_template_is_directional_not_a_scalar_ring_average():
    yy, xx = np.mgrid[-50:51, -50:51]
    valid = np.ones_like(xx, bool)
    linear, _ = arcs.radial_coherence(xx.astype(float), valid, 12)
    radial, _ = arcs.radial_coherence((xx * xx + yy * yy).astype(float), valid, 12)
    assert linear[50, 50] < 1e-5
    assert radial[50, 50] > 0.98


def test_arc_support_is_on_rim_not_basin_center_and_requires_valid_halo():
    yy, xx = np.mgrid[-60:61, -60:61]
    r = np.hypot(yy, xx)
    field = 1 / (1 + np.exp(-(r - 12)))
    valid = np.ones_like(r, bool)
    support = arcs.arc_rim_support(field, valid, radii=(12,))
    assert support[60, 72] > support[60, 60] * 5
    valid[60, 75] = False
    coherence, good = arcs.radial_coherence(field, valid, 12)
    assert not good[60, 60] and coherence[60, 60] == 0


def test_distance_source_is_real_and_outside_footprint_sources_are_retained():
    fp = np.zeros((5, 5), bool)
    fp[2, 2] = True
    with pytest.raises(ValueError):
        confounds.distance_to_seeds(np.zeros_like(fp), fp)
    seeds = np.zeros_like(fp)
    seeds[0, 0] = True
    d = confounds.distance_to_seeds(seeds, fp)
    assert d[2, 2] == pytest.approx(np.sqrt(8) * 100, abs=0.001)
    assert np.isnan(d[0, 0])
    padded = np.zeros((9, 9), bool)
    padded[1, 4] = True
    with pytest.raises(ValueError, match="too short"):
        confounds.distance_to_seeds(padded, np.ones((5, 5), bool), padding=2)
    wide = np.zeros((25, 25), bool)
    wide[9, 12] = True
    d = confounds.distance_to_seeds(wide, np.ones((5, 5), bool), padding=10)
    assert d[0, 2] == 100  # nearest claim/road is outside the output rectangle


def test_esri_multiple_shells_and_holes_do_not_become_one_wrong_polygon():
    shell1 = [[0, 0], [0, 10], [10, 10], [10, 0], [0, 0]]  # Esri clockwise
    hole = [[2, 2], [8, 2], [8, 8], [2, 8], [2, 2]]  # counterclockwise
    shell2 = [[20, 0], [20, 5], [25, 5], [25, 0], [20, 0]]
    g = shape(confounds.esri_polygon([shell1, hole, shell2]))
    assert g.geom_type == "MultiPolygon"
    assert g.area == pytest.approx(89)
    assert g.is_valid


def test_claim_quality_parser_handles_verbose_codes_not_just_literal_25():
    assert confounds.quality_code("25: county-only, no PLSS match") == 25
    assert confounds.quality_code("8; only section in LLD") == 8
    assert confounds.quality_code("4.1: intersecting parts") == 4.1
    assert confounds.quality_code(None) is None


def test_only_requested_nuisance_families_and_categories_enter_primary_test(tmp_path):
    a = np.ones((2, 2), np.float32)
    p = tmp_path / "good.npz"
    np.savez(p, road_m=a, claim_m=a, **{f"block_{b}": a for b in range(1, 5)})
    with np.load(p) as z:
        feats = confounds.classifier_features(z)
        assert len(feats) == 6 and "area1" not in feats
    np.savez(p, road_m=a, claim_m=a, area1=a)
    with np.load(p) as z:
        with pytest.raises(ValueError, match="Forbidden"):
            confounds.classifier_features(z)
    np.savez(p, road_m=a, claim_m=a, block_1=a)
    with np.load(p) as z:
        with pytest.raises(ValueError, match="Partial operational-block"):
            confounds.classifier_features(z)
    np.savez(p, road_m=a, claim_m=a)
    with np.load(p) as z:
        # Partial diagnostics may use measured distances, but never an Area1/2 proxy.
        assert set(confounds.classifier_features(z)) == {"road_m", "claim_m"}
    np.savez(p, road_m=a, mrds_m=a)
    with np.load(p) as z:
        with pytest.raises(ValueError, match="Forbidden"):
            confounds.classifier_features(z)


def test_holm_preserves_order_and_controls_declared_family():
    assert c2s2.holm_adjust([0.04, 0.01, 0.03]) == pytest.approx([0.06, 0.03, 0.06])
    assert c2s2.holm_adjust([]) == []
    with pytest.raises(ValueError):
        c2s2.holm_adjust([np.nan])


def test_near_far_ignore_nan_outside_and_have_disjoint_populations():
    ref = np.full((30, 30), np.nan)
    ref[15, 15] = 1
    near, far, d = c2s2.near_far_masks(ref)
    assert near[15, 15] and not far[15, 15]
    assert not (near & far).any() and d[15, 15] == 0
    with pytest.raises(ValueError):
        c2s2.near_far_masks(np.zeros_like(ref))


def test_nonwrapping_shift_never_moves_reference_pixels_across_opposite_edges():
    ref = np.zeros((4, 5), np.uint8)
    ref[0, 0] = 1
    ref[3, 4] = 1
    moved = c2s2.translate_no_wrap(ref, 1, 2)
    assert moved[1, 2] == 1
    assert moved[3, 4] == 0
    assert moved.sum() == 1
    assert c2s2.translate_no_wrap(ref, 20, 0).sum() == 0
    with pytest.raises(ValueError, match="2D"):
        c2s2.translate_no_wrap(np.ones(4), 0, 1)


def test_permutation_pipeline_refits_every_fold_for_every_replicate(monkeypatch):
    yy, xx = np.mgrid[:60, :60]
    fp = np.ones((60, 60), bool)
    ref = np.zeros_like(fp)
    ref[30, :] = True
    fold = np.where(xx < 30, 0, 1)
    fits = []

    class Constant:
        def predict_proba(self, X):
            return np.full((len(X), 2), 0.5)

    def make(*args):
        def fit(X, y):
            fits.append(len(X))
            return Constant()

        return fit

    monkeypatch.setattr(c2s2, "make_model", make)
    with pytest.raises(ValueError, match="Only spatial-shift"):
        c2s2.c2s2_test(
            "synthetic",
            ref,
            {"road_m": xx.astype(float)},
            fold,
            fp,
            n_per_class=200,
            n_null=3,
            null_mode="grouped",
        )
    r = c2s2.c2s2_test(
        "synthetic",
        ref,
        {"road_m": xx.astype(float)},
        fold,
        fp,
        n_per_class=200,
        n_null=3,
        null_mode="perm",
    )
    assert len(fits) == 8 and r.observed_auc == 0.5 and r.p_value == 1
    assert r.info["refit_every_null"]


def test_residualizer_uses_training_scaling_and_removes_measured_mean_signal():
    rng = np.random.default_rng(5)
    c = rng.uniform(0, 5, (10000, 3)).astype(np.float32)
    c[:, 2] = c[:, 2] > 2.5
    g = np.column_stack(
        [
            2 * c[:, 0] + c[:, 1] + 2 * c[:, 2] + 0.2 * rng.normal(size=len(c)),
            rng.normal(size=len(c)),
        ]
    ).astype(np.float32)
    resid = NuisanceResidualizer(alpha=0.01).fit(c, g)
    med = resid.median.copy()
    scale = resid.scale.copy()
    z = resid.transform(c, g)
    assert abs(np.corrcoef(c[:, 0], z[:, 0])[0, 1]) < 0.02
    resid.transform(c[:5] * 100, g[:5] * 100)
    assert np.array_equal(med, resid.median) and np.array_equal(scale, resid.scale)
    with pytest.raises(ValueError):
        resid.transform(np.full((5, 3), np.nan), g[:5])


def test_nonbinary_or_nan_evaluation_masks_are_rejected():
    for mask in (np.full((8, 8), 2), np.full((8, 8), np.nan)):
        with pytest.raises(ValueError, match="binary"):
            metric.dti_components_exact(np.ones((8, 8)), np.ones((8, 8)), valid_mask=mask)


def test_area1_has_priority_over_overlapping_area2(monkeypatch):
    fp = np.ones((8, 8), bool)

    def outline(path, fp):
        a = np.ones_like(fp)
        if "area1" in str(path):
            a[:] = False
            a[:2, :2] = True
        return a

    monkeypatch.setattr(confounds, "_outline", outline)
    a = confounds.acquisition_areas(fp)
    assert np.all(a[:2, :2] == 1) and a[7, 7] == 2


def test_arc_descriptor_is_not_unique_evidence_of_a_ring_fault():
    # A straight sharp contact tangent to a test annulus can align its local
    # gradient radially. Preserve and disclose this limitation; do not claim
    # that the first, frozen feature uniquely isolates ring faults.
    yy, xx = np.mgrid[-60:61, -60:61]
    field = 1 / (1 + np.exp(-xx.astype(float)))
    c, good = arcs.radial_coherence(field, np.ones_like(field, bool), 12)
    assert good[60, 71] and c[60, 71] > 0.8
