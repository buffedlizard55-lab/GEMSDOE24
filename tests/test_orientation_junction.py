"""OJ1's circular geometry and strict input/missingness contracts."""

import numpy as np
import pytest

from gems.orientation_junction import BANDS, factors


def sources(shape=(30, 30)):
    return {name: np.full(shape, 255, np.uint8) for name in BANDS}


def test_parallel_scarps_have_no_junction_response():
    q = sources()
    surface, canaries, support = factors(q, np.ones((30, 30), bool))
    assert support.all()
    assert np.max(surface) < 1e-6
    assert set(canaries) >= {f"raw_{name}" for name in BANDS}
    assert np.isfinite(surface).all() and ((surface >= 0) & (surface <= 1)).all()


def test_coherent_crossing_families_respond_but_isolated_orientation_does_not():
    q = sources()
    q["strike"][:, :15] = 1  # zero degrees
    q["strike"][:, 15:] = 128  # ninety degrees
    surface, _, _ = factors(q, np.ones((30, 30), bool))
    assert surface[15, 14] > 0.79
    assert surface[15, 2] < 1e-6


def test_axial_zero_and_180_are_the_same_orientation():
    q = sources()
    q["strike"][:, :15] = 1
    assert factors(q, np.ones((30, 30), bool))[0].max() < 1e-6


def test_no_lidar_does_not_create_a_spurious_junction():
    q = sources()
    q["strike"][:, :15] = 0
    surface, _, support = factors(q, np.ones((30, 30), bool))
    assert not support[:, :15].any()
    assert surface.max() < 1e-6
    q["valid"][:] = 1  # encoded sample present, but decoded fraction zero
    surface, _, support = factors(q, np.ones((30, 30), bool))
    assert not support.any() and not surface.any()


@pytest.mark.parametrize("fault", ["float", "shape", "footprint"])
def test_bad_inputs_fail_closed(fault):
    q, fp = sources(), np.ones((30, 30), bool)
    if fault == "float":
        q["strike"] = q["strike"].astype(float)
    elif fault == "shape":
        q["strike"] = q["strike"][:2]
    else:
        fp = fp.astype(float)
    with pytest.raises(ValueError):
        factors(q, fp)
