"""Regression tests for the shared current protocol, not private evaluator copies."""

import hashlib

import numpy as np
import pytest
import rasterio
from rasterio.transform import Affine
from scipy.ndimage import distance_transform_edt
from scipy.spatial import cKDTree

from gems import emission, holdout, magnetic_trough, novelty, submission


def context():
    fp = np.ones((260, 260), bool)
    labels = np.zeros_like(fp)
    labels[30, 20:240] = True  # one WHOLE component crosses the north split
    labels[200, 20:90] = True
    labels[200, 190:240] = True
    return holdout.SegmentHoldout(fp, labels)


def test_whole_fault_component_is_removed_everywhere_and_train_is_buffered():
    h = context()
    for f in h.folds:
        hidden = f["hidden_component_ids"]
        assert not np.isin(h.components[f["visible"]], hidden).any()
        assert not (f["train"] & f["valid"]).any()
        assert not (f["visible"] & f["truth"]).any()
        whole_hidden = np.isin(h.components, hidden) & h.labels
        protected = f["valid"] | whole_hidden
        assert not (f["train"] & (distance_transform_edt(~protected) <= h.buffer_px)).any()
    assert not h.folds[0]["visible"][30, 200]  # far across the split, not a clipped fragment


def test_pooled_dti_is_not_mean_of_fold_ratios():
    rows = [
        {"TP_w": 1, "FP_w": 0, "FN_w": 0, "n_truth": 1, "n_emitted": 1},
        {"TP_w": 0, "FP_w": 100, "FN_w": 10, "n_truth": 10, "n_emitted": 100},
    ]
    p = holdout.pooled_components(rows)
    assert p["dti"] == pytest.approx(1 / (1 + 0.2 * 100 + 0.8 * 10 + 1e-7))
    assert p["dti"] != pytest.approx(0.5)


def test_exact_shared_metric_and_bootstrap_components_agree_with_visible_masking():
    h = context()
    predictions = [h.labels | f["visible"] for f in h.folds]
    result = h.summarize(predictions, ci_draws=100)
    assert result["label"] == "HOLDOUT-DTI"
    assert result["dti"] == pytest.approx(1)
    assert result["n_withheld_positive_pixels"] == h.labels.sum()
    assert result["n_unique_withheld_components"] == 3
    assert result["ci95"]["level"] == 0.95


def test_canary_flags_a_label_feature_in_either_polarity_and_test_counts_are_explicit():
    h = context()
    r = h.canary({"leak": h.labels.astype(float), "inverse_leak": 1 - h.labels.astype(float)})
    assert not r["passed"]
    assert all(x["leakage_suspected"] for x in r["features"].values())
    assert r["features"]["leak"]["pooled_auc"] == 1
    assert r["features"]["inverse_leak"]["pooled_auc"] == 0


def test_priority_poisson_is_positive_only_deterministic_and_respects_spacing():
    score = np.random.default_rng(0).random((50, 50))
    score[:10] = 0
    score[12] = np.nan
    eligible = np.ones(score.shape, bool)
    p = emission.priority_poisson(score, eligible, 100)
    assert p.sum() == 100 and not p[:10].any() and not p[12].any()
    assert np.array_equal(p, emission.priority_poisson(score, eligible, 100))
    assert cKDTree(np.argwhere(p)).query(np.argwhere(p), k=2)[0][:, 1].min() >= 3
    assert not emission.priority_poisson(score, eligible, 0).any()
    assert not emission.priority_poisson(np.zeros_like(score), eligible, 20).any()


def test_paired_trough_targets_a_two_sided_low_not_a_monotonic_contact():
    yy, xx = np.mgrid[:260, :260]
    valid = np.ones(xx.shape, bool)
    trough = -np.exp(-(((xx - 130) / 3) ** 2)).astype(np.float32)
    response = magnetic_trough.paired_trough(trough, valid)
    assert response[130, 130] > response[130, 110]
    monotone = xx.astype(np.float32)
    assert magnetic_trough.paired_trough(monotone, valid)[100:160, 100:160].max() < 1e-5
    surfaces, support = magnetic_trough.build_surfaces(trough, 100 + 50 * trough, valid)
    assert not support[:72].any() and not support[:, :72].any()
    assert surfaces["candidate"][130, 130] > 0
    assert np.isfinite(surfaces["candidate"]).all()
    assert not surfaces["candidate"][~support].any()


def test_novelty_stops_an_exact_or_spatially_redundant_candidate(tmp_path):
    fp = np.ones((40, 40), bool)
    a = np.zeros(fp.shape, np.float32)
    a[10:30:4, 10:30:4] = 1
    p = tmp_path / "registry.tif"
    with rasterio.open(
        p,
        "w",
        driver="GTiff",
        height=40,
        width=40,
        count=1,
        dtype="float32",
        crs="EPSG:32611",
        transform=Affine(100, 0, 243350, 0, -100, 4508550),
    ) as s:
        s.write(a, 1)
    rows = [
        {
            "cache_path": p.name,
            "footprint_sha256": hashlib.sha256(a[fp].astype("<f4").tobytes()).hexdigest(),
            "id": "test",
            "file": p.name,
        }
    ]
    surface = novelty.compare_registry(a, fp, rows, tmp_path, template_path=p)
    final = novelty.compare_registry(a, fp, rows, tmp_path, dots=a > 0, template_path=p)
    assert not surface["passed"] and not final["passed"]
    assert final["max_dot_overlap"] == 1
    assert surface["max_abs_rank_correlation"] == pytest.approx(1)


def test_format_validator_never_authorizes_an_upload(tmp_path, monkeypatch):
    fp = np.ones((16, 20), bool)
    fp[:2] = False
    template = tmp_path / "t.tif"
    with rasterio.open(
        template,
        "w",
        driver="GTiff",
        height=16,
        width=20,
        count=1,
        dtype="float32",
        crs="EPSG:32611",
        transform=Affine(100, 0, 243350, 0, -100, 4508550),
        nodata=np.nan,
    ) as s:
        s.write(np.where(fp, 0, np.nan).astype(np.float32), 1)
    monkeypatch.setitem(submission.EXPECTED, "shape", fp.shape)
    monkeypatch.setitem(submission.EXPECTED, "footprint_pixels", int(fp.sum()))
    monkeypatch.setitem(submission.EXPECTED, "footprint_sha256", submission.footprint_sha256(fp))
    p = submission.write_submission(np.ones(fp.shape), template, tmp_path / "new.tif")
    checks = submission.check_variants(p, template)
    assert checks["format_valid"]
    assert checks["ok_to_upload"] is False
    assert "selector" in checks["upload_authorization"]


def test_shared_emitter_rejects_fractional_budget_and_nonfinite_spacing():
    score = np.ones((12, 12), np.float32)
    eligible = np.ones_like(score, bool)
    for budget in (2.5, np.nan, np.inf):
        with pytest.raises(ValueError):
            emission.priority_poisson(score, eligible, budget)
    for distance in (np.nan, np.inf):
        with pytest.raises(ValueError):
            emission.priority_poisson(score, eligible, 2, min_dist=distance)
