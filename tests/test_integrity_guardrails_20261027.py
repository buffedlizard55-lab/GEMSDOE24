"""Regressions for mask integrity, feature canaries and non-destructive output."""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import Affine

from gems import holdout, metric, selector, submission

ROOT = Path(__file__).resolve().parents[1]


def scene():
    footprint = np.ones((80, 80), dtype=bool)
    labels = np.zeros_like(footprint)
    labels[15, 5:70] = True
    labels[65, 5:70] = True
    return footprint, labels


def template(tmp_path):
    path = tmp_path / "template.tif"
    data = np.zeros((16, 20), dtype=np.float32)
    data[:2] = np.nan
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=data.shape[0],
        width=data.shape[1],
        count=1,
        dtype="float32",
        crs="EPSG:32611",
        transform=Affine(100, 0, 243350, 0, -100, 4508550),
        nodata=np.nan,
    ) as ds:
        ds.write(data, 1)
    return path, data


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -9999, 0.5, 2])
@pytest.mark.parametrize("input_name", ["footprint", "labels"])
def test_segment_evaluators_reject_nonbinary_or_nodata_masks(bad, input_name):
    fp, labels = scene()
    values = {"footprint": fp.astype(float), "labels": labels.astype(float)}
    values[input_name][30, 30] = bad
    with pytest.raises(ValueError, match="finite two-dimensional binary"):
        holdout.SegmentHoldout(values["footprint"], values["labels"], buffer_px=5)
    with pytest.raises(ValueError, match="finite two-dimensional binary"):
        list(holdout.segment_folds(values["footprint"], values["labels"], buffer_px=5))
    with pytest.raises(ValueError, match="finite two-dimensional binary"):
        holdout.Holdout(values["footprint"], values["labels"])


def test_segment_folds_reject_an_unbuffered_evaluation():
    fp, labels = scene()
    with pytest.raises(ValueError, match="buffer >=3"):
        list(holdout.segment_folds(fp, labels, buffer_px=0))


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -9999, 0.5, 2])
def test_metric_rejects_invalid_truth_in_active_domain_but_ignores_outside(bad):
    truth = np.zeros((10, 10), dtype=float)
    pred = np.zeros_like(truth)
    valid = np.ones_like(truth, dtype=bool)
    truth[2, 2] = bad
    with pytest.raises(ValueError, match="finite binary"):
        metric.dti_components_exact(pred, truth, valid_mask=valid)
    with pytest.raises(ValueError, match="finite binary"):
        metric.dti_score_fast(pred, truth, valid_mask=valid)
    valid[2, 2] = False
    assert metric.dti_score_fast(pred, truth, valid_mask=valid)["dti"] == 0


@pytest.mark.parametrize("alpha,beta", [(float("nan"), 0.8), (0.2, float("inf"))])
def test_metric_rejects_nonfinite_penalties(alpha, beta):
    with pytest.raises(ValueError, match="finite"):
        metric.dti_components_exact(np.zeros((5, 5)), np.zeros((5, 5)), alpha=alpha, beta=beta)


def test_canary_detects_missingness_when_zero_imputation_hides_it():
    fp, labels = scene()
    ctx = holdout.SegmentHoldout(fp, labels, buffer_px=5)
    feature = np.zeros(fp.shape, dtype=float)
    feature[labels] = np.nan
    report = ctx.canary({"missing_on_positives": feature})
    result = report["features"]["missing_on_positives"]
    assert result["pooled_auc"] == 0.5  # all finite and imputed values are zero
    assert result["pooled_presence_auc"] == 0.0
    assert result["leakage_suspected"] is True
    assert not report["passed"] and report["missingness_tested_separately"]


def test_canary_accepts_independently_constructed_fold_local_features():
    fp, labels = scene()
    ctx = holdout.SegmentHoldout(fp, labels, buffer_px=5)
    grids = [np.zeros(fp.shape) for _ in ctx.folds]
    grids[0][ctx.folds[0]["truth"]] = 1
    report = ctx.canary({"folds": grids})
    assert report["features"]["folds"]["folds"][0]["auc"] == 1.0
    assert report["features"]["folds"]["leakage_suspected"]
    with pytest.raises(ValueError, match="one per fold"):
        ctx.canary({"wrong_count": grids[:-1]})
    ordinary_nested_list = np.zeros(fp.shape).tolist()
    actual_canary = ctx.canary({"nested": ordinary_nested_list})
    assert actual_canary["passed"] and selector._recorded_canary_passed(actual_canary)


def test_equal_population_wrong_footprint_no_longer_passes_grid_validation(tmp_path, monkeypatch):
    sample, data = template(tmp_path)
    footprint = np.isfinite(data)
    # Use a small synthetic template while retaining the production validation logic.
    expected = dict(submission.EXPECTED)
    expected.update(
        shape=data.shape,
        footprint_pixels=int(footprint.sum()),
        footprint_sha256=submission.footprint_sha256(footprint),
    )
    monkeypatch.setattr(submission, "EXPECTED", expected)
    prediction = submission.write_submission(np.ones(data.shape), sample, tmp_path / "out.tif")
    assert submission.check_variants(prediction, sample)["format_valid"]
    # Swap a valid and an invalid pixel: same shape, CRS, transform and count.
    altered = data.copy()
    altered[0, 0], altered[2, 0] = 0, np.nan
    assert int(np.isfinite(altered).sum()) == int(footprint.sum())
    with rasterio.open(sample, "r+") as ds:
        ds.write(altered, 1)
    result = submission.check_variants(prediction, sample)
    assert not result["checks"]["official_template_grid_and_footprint"]["pass"]
    assert not result["format_valid"]


def test_pinned_portfolio_registry_is_nonempty_and_includes_the_lattice():
    required = selector._required_registry_footprints()
    assert required is not None and len(required) == 167
    assert "15bc7e7d4e21d284c42e4183bb7c63d087f67635818bd7b963d58f6beed44817" in required


def test_writer_and_zip_never_overwrite_their_inputs(tmp_path):
    sample, data = template(tmp_path)
    original = sample.read_bytes()
    for alias in (sample, tmp_path / "sample-symlink.tif", tmp_path / "sample-hardlink.tif"):
        if alias.name == "sample-symlink.tif":
            alias.symlink_to(sample)
        if alias.name == "sample-hardlink.tif":
            alias.hardlink_to(sample)
        with pytest.raises(ValueError, match="overwrite the template"):
            submission.write_submission(np.ones(data.shape), sample, alias)
        assert sample.read_bytes() == original
    with pytest.raises(ValueError, match="overwrite the source TIFF"):
        submission.zip_single(sample, sample)
    assert sample.read_bytes() == original


def test_cli_refuses_to_replace_prediction_input(tmp_path):
    sample, data = template(tmp_path)
    source = tmp_path / "prediction.npy"
    np.save(source, np.ones(data.shape))
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    result = subprocess.run(
        [
            sys.executable,
            "scripts/submission_writer.py",
            str(source),
            str(source),
            "--template",
            str(sample),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0 and "overwrite the prediction" in result.stderr
    assert hashlib.sha256(source.read_bytes()).hexdigest() == digest
