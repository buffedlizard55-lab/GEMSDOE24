"""Exact synthetic-field tests for the H24-EUL1 Euler solver.

A direction-cosine field F = X / sqrt(X^2 + Y^2 + Z^2), with (X, Y) offsets from a
source axis at depth z0 and Z = z - z0, is homogeneous of degree 0 about the source,
so on the observation plane z=0 its analytic derivatives satisfy the N=0 Euler
equation exactly with the true (x0, y0, z0). The windowed solver must recover depth
and plan position at window centres near the source.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gems import euler  # noqa: E402


def _synthetic_degree0(shape=(61, 61), centre=(30, 30), depth_px=6.0):
    yy, xx = np.mgrid[0 : shape[0], 0 : shape[1]].astype(np.float64)
    x = xx - centre[1]
    y = yy - centre[0]
    z = np.full_like(x, -depth_px)  # observation plane z=0, source depth z0=depth_px: Z = z - z0
    r2 = x * x + y * y + depth_px * depth_px
    r = np.sqrt(r2)
    field = (x / r).astype(np.float32)
    # Analytic d/dz of X/R at z=0:  X * (-1/2) R^-3 * 2Z = -X*Z / R^3, Z = -depth
    fz = (-x * z / r**3).astype(np.float32)
    valid = np.ones(shape, dtype=bool)
    return field, fz, valid, centre, depth_px


def test_euler_recovers_known_depth_and_position():
    field, fz, valid, (cy, cx), depth_px = _synthetic_degree0()
    sol = euler.euler_solutions(field, fz, valid, window=7)
    # Central window: plan offset ~0, depth ~ true depth, tiny residual, accepted.
    assert abs(float(sol["x0"][cy, cx])) < 0.75
    assert abs(float(sol["y0"][cy, cx])) < 0.75
    assert abs(float(sol["depth"][cy, cx]) - depth_px) < 1.5
    assert float(sol["rel_resid"][cy, cx]) < euler.REL_RESID_MAX
    assert bool(sol["accepted"][cy, cx])
    # Solved plan positions of accepted centres cluster near the true source axis.
    acc = sol["accepted"]
    rows, cols = np.nonzero(acc)
    # Plan-acceptance (|offset| <= 3.5 px) limits accepted centres to ~the 7x7 block
    # whose windows contain the source axis: 49 centres for this geometry.
    assert len(rows) >= 40
    med_r = float(np.median(rows + sol["y0"][acc]))
    med_c = float(np.median(cols + sol["x0"][acc]))
    assert abs(med_r - cy) < 2.0
    assert abs(med_c - cx) < 2.0
    assert abs(float(np.median(sol["depth"][acc])) - depth_px) < 2.0


def test_fft_vertical_derivative_matches_analytic():
    # F = X / R^3 is harmonic away from its source (it is -d/dX of 1/R), so the FFT
    # |k| operator must reproduce its analytic vertical derivative in the interior
    # (up to the z-down/z-up sign). NOTE: the direction-cosine field used for the
    # Euler-solver test is homogeneous degree 0 but NOT harmonic, so it cannot be
    # reused here.
    shape, (cy, cx), depth = (201, 201), (100, 100), 8.0
    yy, xx = np.mgrid[0 : shape[0], 0 : shape[1]].astype(np.float64)
    x, y = xx - cx, yy - cy
    r2 = x * x + y * y + depth * depth
    field = (x / r2**1.5).astype(np.float32)
    fz_analytic = (-3.0 * x * depth / r2**2.5).astype(np.float32)  # d/dZ at Z=depth
    valid = np.ones(shape, dtype=bool)
    fz_fft = euler.fft_vertical_derivative(field, valid)
    interior = np.zeros_like(valid)
    interior[40:-40, 40:-40] = True
    m = interior & valid
    x = fz_fft[m].astype(np.float64)
    y = fz_analytic[m].astype(np.float64)
    corr = float(np.corrcoef(x, y)[0, 1])
    assert abs(corr) > 0.95, corr
    slope = float((x * y).sum() / (x * x).sum())
    assert 0.6 < abs(slope) < 1.6, slope  # per-pixel units agree to taper/edge error


def test_euler_rejects_flat_field():
    field = np.ones((31, 31), dtype=np.float32)
    fz = np.zeros((31, 31), dtype=np.float32)
    valid = np.ones((31, 31), dtype=bool)
    sol = euler.euler_solutions(field, fz, valid, window=7)
    assert not sol["accepted"].any()


def test_euler_channels_shapes_and_nan_support():
    field, fz, valid, _centre, _d = _synthetic_degree0(shape=(41, 41), centre=(20, 20))
    sol = euler.euler_solutions(field, fz, valid, window=7)
    density, depth, quality, diag = euler._smoothed_solution_channels(sol, valid)
    assert density.shape == depth.shape == quality.shape == (41, 41)
    assert np.isfinite(density[valid]).all()
    assert diag["n_solutions_accepted"] > 0
    assert np.isfinite(depth[20, 20]) and np.isfinite(quality[20, 20])
