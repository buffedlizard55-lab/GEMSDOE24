"""Synthetic unit tests for H24-CGMK1 label-free channels (no bulk data)."""

import numpy as np
import pytest

from gems.cgmk1 import (
    BASE25,
    CONDK4,
    CROSS8,
    FULL37,
    STACK33,
    cross_gradient_channels,
    fit_condk_coeffs,
)


def test_channel_inventory_is_preregistered():
    assert len(BASE25) == 25
    assert len(CROSS8) == 8
    assert len(CONDK4) == 4
    assert len(STACK33) == 33
    assert len(FULL37) == 37
    assert len(set(FULL37)) == 37
    # Preregistered exclusions.
    for banned in ("det_elev", "det_elev_slope", "tc"):
        assert banned not in FULL37


def test_cross_gradient_parallel_fields_have_zero_signed_sin():
    y, x = np.mgrid[0:60, 0:60]
    mag = (x + 2 * y).astype(np.float32)
    grav = (3 * x + 6 * y).astype(np.float32)  # gradients exactly parallel to mag
    support = np.zeros((60, 60), bool)
    support[15:-15, 15:-15] = True
    sin_t, cos_t, rev, _ = cross_gradient_channels(mag, grav, support, 1.0)
    assert np.abs(sin_t[support]).max() < 1e-4
    assert np.abs(cos_t[support] - 1.0).max() < 1e-3
    assert np.abs(rev[support]).max() < 1e-4


def test_cross_gradient_perpendicular_fields_have_unit_signed_sin():
    y, x = np.mgrid[0:60, 0:60]
    mag = y.astype(np.float32)  # gradient (0, 1) in (x, y) components
    grav = x.astype(np.float32)  # gradient (1, 0)
    support = np.zeros((60, 60), bool)
    support[15:-15, 15:-15] = True
    sin_t, cos_t, _, _ = cross_gradient_channels(mag, grav, support, 1.0)
    # (gx*my - gy*mx) / (|g||m|) = (1*1 - 0*0) / 1 = +1 exactly.
    assert np.abs(sin_t[support] - 1.0).max() < 1e-3
    assert np.abs(cos_t[support]).max() < 1e-3
    # Swapping the fields flips the sign: this is the signed reversal channel.
    sin_swap, _, _, _ = cross_gradient_channels(grav, mag, support, 1.0)
    assert np.abs(sin_swap[support] + 1.0).max() < 1e-3


def test_fit_condk_recovers_known_coefficients():
    rng = np.random.default_rng(7)
    rth, ru = rng.random(5000), rng.random(5000)
    true = np.array([0.10, 0.40, -0.20, 0.30])
    rk = true[0] + true[1] * rth + true[2] * ru + true[3] * rth * ru
    rk[:25] = np.nan  # missing rows must be dropped, not imputed
    est = fit_condk_coeffs(rk, rth, ru)
    np.testing.assert_allclose(est, true, atol=1e-8)


def test_fit_condk_rejects_too_few_rows():
    with pytest.raises(ValueError):
        fit_condk_coeffs(np.ones(10), np.ones(10), np.ones(10))
