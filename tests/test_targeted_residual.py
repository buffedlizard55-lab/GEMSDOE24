import sys
from pathlib import Path

import numpy as np
import pytest

from gems.holdout import SegmentHoldout
from gems.targeted_residual import TargetedResidualizer

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from run_tnr1_lane import batches_canary, sample_training


def matrices():
    rng = np.random.default_rng(72)
    nuisance = np.column_stack([rng.uniform(0, 5, (200, 2)), np.eye(4)[np.arange(200) % 4]]).astype(
        np.float32
    )
    geology = rng.normal(size=(200, 4)).astype(np.float32)
    geology[:, 0] += nuisance[:, 0]
    geology[::7, 3] = np.nan
    return nuisance, geology


def test_targeted_removal_preserves_protected_values_and_nan_bits():
    nuisance, geology = matrices()
    intervention = TargetedResidualizer(["air", "gravity", "terrain", "scarp"], ["air", "gravity"])
    intervention.fit(nuisance[:120], geology[:120])
    source = geology.copy()
    transformed = intervention.transform(nuisance, geology)
    assert transformed[:, 2:].tobytes() == source[:, 2:].tobytes()
    assert np.array_equal(geology, source, equal_nan=True)
    assert not np.allclose(transformed[:, :2], geology[:, :2])
    assert intervention.receipt()["n_training_rows"] == 120
    assert intervention.receipt()["unchanged_columns"] == ["terrain", "scarp"]


def test_heldout_transform_does_not_refit_training_statistics():
    nuisance, geology = matrices()
    intervention = TargetedResidualizer(["a", "b", "c", "d"], ["a"])
    intervention.fit(nuisance[:100], geology[:100])
    coefficients = intervention.residualizer.model.coef_.copy()
    median = intervention.residualizer.median.copy()
    changed = geology[100:].copy()
    changed[:, 0] += 10000
    intervention.transform(nuisance[100:], changed)
    assert np.array_equal(coefficients, intervention.residualizer.model.coef_)
    assert np.array_equal(median, intervention.residualizer.median)


@pytest.mark.parametrize(
    "names, targets",
    [([], ["a"]), (["a", "a"], ["a"]), (["a"], []), (["a"], ["x"]), (["a"], ["a", "a"])],
)
def test_column_policy_cannot_silently_change(names, targets):
    with pytest.raises(ValueError):
        TargetedResidualizer(names, targets)


def test_unfitted_missing_nuisance_and_wrong_shapes_fail_closed():
    nuisance, geology = matrices()
    intervention = TargetedResidualizer(["a", "b", "c", "d"], ["a"])
    with pytest.raises(ValueError, match="Fit"):
        intervention.transform(nuisance, geology)
    intervention.fit(nuisance[:100], geology[:100])
    with pytest.raises(ValueError, match="columns"):
        intervention.transform(nuisance, geology[:, :3])
    nuisance[0, 0] = np.nan
    with pytest.raises(ValueError, match="Missing nuisance"):
        intervention.transform(nuisance, geology)
    geology[0, 0] = np.inf
    with pytest.raises(ValueError, match="Infinity"):
        intervention.transform(nuisance, geology)


def test_training_sampler_never_uses_validation_or_hidden_labels():
    fp_ids = np.arange(100 * 100)
    train = np.ones((100, 100), bool)
    train[:, 60:] = False
    visible = np.zeros_like(train)
    visible[10:14, 10] = True
    visible[80:85, 20] = True
    selected, labels, uniform = sample_training(fp_ids, train, visible, 13)
    assert train.ravel()[selected].all() and train.ravel()[uniform].all()
    assert np.array_equal(visible.ravel()[selected], labels.astype(bool))
    again, y_again, u_again = sample_training(fp_ids, train, visible, 13)
    assert np.array_equal(selected, again)
    assert np.array_equal(labels, y_again)
    assert np.array_equal(uniform, u_again)


def test_batched_canary_uses_shared_two_polarity_failures():
    fp = np.ones((60, 60), bool)
    truth = np.zeros_like(fp)
    for y in (10, 45):
        for x in (10, 45):
            truth[y : y + 3, x] = True
    context = SegmentHoldout(fp, truth, buffer_px=3)
    fp_ids = np.flatnonzero(fp)
    result = batches_canary(
        context,
        [("truth", truth[fp].astype(float)), ("inverse", (~truth)[fp].astype(float))],
        fp_ids,
        group_size=1,
    )
    assert not result["passed"] and result["feature_count"] == 2
    assert all(row["leakage_suspected"] for row in result["features"].values())
    assert result["two_polarities_checked"]
