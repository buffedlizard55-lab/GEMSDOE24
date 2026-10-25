"""Unit tests for H24-RSHG1 multi-physics operators, NaN-preserving residualization, and emission."""

from __future__ import annotations

import numpy as np
from scipy.ndimage import distance_transform_edt

from gems import rshg1


def test_feature_spec_dimensions():
    assert len(rshg1.FEATURE_NAMES) == 42
    assert len(set(rshg1.FEATURE_NAMES)) == 42
    assert len(rshg1.REGIONAL_INDICES) == 11
    assert rshg1.FEATURE_NAMES[rshg1.G_SAT_INDEX] == "g_sat"


def test_kernel_trace_score_boosts_linear_ridges_and_masks_visible():
    dom = np.ones((21, 21), dtype=bool)
    vis = np.zeros((21, 21), dtype=bool)
    vis[3, 3] = True
    prob = np.zeros((21, 21), dtype=np.float32)
    # Isolated 1-pixel spike at (5, 15) vs continuous horizontal ridge at row 14
    prob[5, 15] = 0.40
    prob[14, 4:16] = 0.40
    prob[3, 3] = 0.99  # visible pixel must be zeroed BEFORE convolution
    prob[3, 4] = 0.20

    s = rshg1.kernel_trace_score(prob, dom, vis)
    assert s[3, 3] == 0.0
    # Off-ridge zero probability stays strictly zero (no off-ridge drift!)
    assert s[12, 10] == 0.0
    # Continuous ridge receives higher kernel-integrated score than equal-amplitude 1-px spike
    assert s[14, 10] > s[5, 15] * 1.4


def test_emit_rshg1_dots_enforces_200m_visible_clearance_and_min_dist():
    dom = np.ones((30, 30), dtype=bool)
    vis = np.zeros((30, 30), dtype=bool)
    vis[15, 5:25] = True  # known fault trace
    prob = np.full((30, 30), 0.1, dtype=np.float32)
    # Put very strong halo within 1..2 px of visible fault, and moderate ridge far away
    prob[13:18, 5:25] = 0.95
    prob[4, 4:26] = 0.50

    dots = rshg1.emit_rshg1_dots(
        prob, dom, vis, budget_frac=0.02, min_dist=3.0, flank_clearance_px=2.0
    )
    assert dots.any()
    dist_vis = distance_transform_edt(~vis)
    # Every emitted dot must sit strictly > 2.0 px (>200 m) from visible fault
    assert np.all(dist_vis[dots] > 2.0)


def test_nan_preserving_residualizer_never_injects_nuisance_into_missing_tiles():
    rng = np.random.default_rng(42)
    n = 1200
    nuisance = np.column_stack(
        [
            rng.uniform(0, 3000, size=n).astype(np.float32),
            rng.uniform(0, 5000, size=n).astype(np.float32),
            (np.arange(n) < 300).astype(np.float32),
            ((np.arange(n) >= 300) & (np.arange(n) < 600)).astype(np.float32),
            ((np.arange(n) >= 600) & (np.arange(n) < 900)).astype(np.float32),
            (np.arange(n) >= 900).astype(np.float32),
        ]
    )
    # 3 columns: col 0 = regional scalar strongly correlated with claim_m + block,
    # col 1 = local scarp feature with 30% missing LiDAR gap, col 2 = regional with NaNs
    x = rng.normal(0.0, 1.0, size=(n, 3)).astype(np.float32)
    x[:, 0] += 0.002 * nuisance[:, 1] + 3.0 * nuisance[:, 2]
    x[:, 2] += -0.0015 * nuisance[:, 0]
    gap = np.arange(n) % 3 == 0
    x[gap, 1] = np.nan
    x[np.flatnonzero(gap)[:100], 2] = np.nan

    res = rshg1.NanPreservingResidualizer(regional_indices=np.array([0, 2]), alpha=10.0)
    res.fit(nuisance, x)
    xt = res.transform(nuisance, x, remove=True)

    # Exact NaN pattern preserved!
    assert np.array_equal(np.isnan(xt), np.isnan(x))
    # Regional column correlation with nuisance is strongly suppressed on observed rows
    raw_corr = abs(np.corrcoef(x[:, 0], nuisance[:, 1])[0, 1])
    res_corr = abs(np.corrcoef(xt[:, 0], nuisance[:, 1])[0, 1])
    assert res_corr < 0.25 * raw_corr


def test_regime_nuisance_calibrator_matches_gap_tail_and_stays_in_unit_interval():
    rng = np.random.default_rng(7)
    n = 2000
    has_lidar = np.arange(n) >= 700
    nuisance = np.column_stack(
        [
            rng.uniform(10.0, 5000.0, size=n).astype(np.float32),
            rng.uniform(10.0, 8000.0, size=n).astype(np.float32),
            (np.arange(n) < 1000).astype(np.float32),
            (np.arange(n) >= 1000).astype(np.float32),
        ]
    )
    # Simulate compressed upper tail in LiDAR gap + strong nuisance drift
    raw_logit = rng.normal(-2.5, 1.2, size=n)
    raw_logit[~has_lidar] = -2.8 + 0.45 * rng.normal(0.0, 1.0, size=(~has_lidar).sum())
    raw_logit += -0.00025 * nuisance[:, 1]
    prob = 1.0 / (1.0 + np.exp(-raw_logit))

    cal = rshg1.RegimeNuisanceCalibrator(alpha=20.0).fit(prob, has_lidar, nuisance)
    out = cal.transform(prob, has_lidar, nuisance)
    assert out.dtype == np.float32
    assert np.isfinite(out).all()
    assert float(out.min()) >= 0.0 and float(out.max()) <= 1.0

    # Upper-tail p99 rates between gap and lidar domains become closely aligned
    p99_lidar = np.percentile(out[has_lidar], 99.0)
    p99_gap = np.percentile(out[~has_lidar], 99.0)
    assert abs(p99_lidar - p99_gap) < 0.06


def test_tilt_and_curvature_channels_respect_boundary_erosion():
    shape = (45, 45)
    fp = np.ones(shape, dtype=bool)
    fp[:2, :] = False
    yy, xx = np.indices(shape, dtype=np.float32)
    # Vertical magnetic fault contact along xx == 22 -> tmi_vg crosses 0 at xx == 22, tmi_hg peaks
    tmi_vg = (xx - 22.0).astype(np.float32)
    tmi_hg = np.exp(-0.1 * (xx - 22.0) ** 2).astype(np.float32) + 0.2
    grav_vg = (yy - 22.0).astype(np.float32)
    grav_hg = np.exp(-0.1 * (yy - 22.0) ** 2).astype(np.float32) + 0.2
    # Positive topographic ridge along yy == 22
    det_elev = (10.0 * np.exp(-0.25 * (yy - 22.0) ** 2)).astype(np.float32)

    ch = rshg1.compute_tilt_and_curvature_channels(tmi_hg, tmi_vg, grav_hg, grav_vg, det_elev, fp)
    assert np.isnan(ch["cos_tilt_mag"][0, 10])
    assert ch["cos_tilt_mag"][22, 22] > 0.99
    assert ch["cos_tilt_mag"][22, 22] > ch["cos_tilt_mag"][22, 30]
    assert ch["cos_tilt_grav"][22, 22] > 0.99
    # DEM Hessian ridge eroded by 10 px from top invalid rows 0..1 -> rows 0..11 must be NaN
    assert np.all(np.isnan(ch["dem_hess_ridge"][:12, :]))
    assert ch["dem_hess_ridge"][22, 22] > ch["dem_hess_ridge"][30, 22] * 3.0
