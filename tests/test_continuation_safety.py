"""Fail closed on incomplete canaries and retired, incorrectly described lanes."""

import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from gems.holdout import SegmentHoldout

ROOT = Path(__file__).resolve().parents[1]


def context():
    fp = np.ones((80, 80), bool)
    truth = np.zeros_like(fp)
    truth[15, 5:70] = True
    truth[65, 5:70] = True
    return SegmentHoldout(fp, truth, buffer_px=5)


def test_empty_leakage_screen_is_not_a_pass():
    with pytest.raises(ValueError, match="actual feature"):
        context().canary({})


@pytest.mark.parametrize("limit", [0, -1, True, 2.5])
def test_canary_sample_limit_must_be_positive_integer(limit):
    with pytest.raises(ValueError, match="Positive integer"):
        context().canary({"x": np.ones((80, 80))}, max_per_class=limit)


def test_both_polarities_of_label_leak_are_flagged():
    ctx = context()
    result = ctx.canary({"truth": ctx.labels.astype(float), "inverse": 1 - ctx.labels})
    assert not result["passed"]
    assert result["features"]["truth"]["leakage_suspected"]
    assert result["features"]["inverse"]["leakage_suspected"]


def test_constant_feature_is_a_chance_diagnostic_not_a_leak():
    result = context().canary({"constant": np.ones((80, 80))})
    assert result["passed"]
    assert result["features"]["constant"]["pooled_auc"] == 0.5


def test_stopped_catalogue_proximity_lane_cannot_be_rerun():
    result = subprocess.run(
        [sys.executable, "scripts/build_unique_submission3.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "Retired" in result.stderr and "30 km" in result.stderr


@pytest.mark.parametrize(
    "name",
    [
        "build_unique_submission.py",
        "build_unique_submission2.py",
        "run_con_lane.py",
        "run_fuse_lane.py",
    ],
)
def test_other_frozen_lanes_cannot_restart_experiments(name):
    result = subprocess.run(
        [sys.executable, "scripts/" + name],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0 and "Retired" in result.stderr


def test_nonzero_placeholder_is_not_exempted_from_competing_method_checks():
    from gems.novelty import classify_registry_entry

    row = {
        "file": "inputs/calibration/gemsdoe9-PLACEHOLDER-2314b599.tif",
        "positive_pixels": 147684,
    }
    assert classify_registry_entry(row) == "competing_method_lane"
