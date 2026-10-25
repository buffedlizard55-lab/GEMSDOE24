"""Streaming multi-physics conduit feature construction, NaN-safe residualization, and emission for H24-RSHG1.

Implements the fixed preregistered specification in
``knowledge/17_preregistered_RSHG1_2026-10-25.md``:
- Zero copied submission pixels; all features derive strictly from official
  competition bands and audited auxiliary USGS 3DEP / GeoDAWN rasters.
- Missing sensor tiles (e.g. 3DEP 1 m LiDAR gaps covering 24.7% of footprint)
  remain ``np.nan`` rather than zero-filled or blacked out, enabling native
  missing-value tree routing across 100% of the competition footprint.
- ``NanPreservingResidualizer`` fits ``NuisanceResidualizer`` strictly on
  observed training-fold pixels for long-wavelength regional scalars while
  preserving ``np.nan`` on unobserved cells so nuisance predictions are never
  injected into sensor gaps.
- ``RegimeNuisanceCalibrator`` aligns background log-odds quantiles between
  LiDAR-covered and LiDAR-gap domains and removes smooth nuisance background
  offsets using training-fold unlabeled background pixels only.
"""

from __future__ import annotations

import gc
from pathlib import Path
from typing import Any

import numpy as np
from scipy.ndimage import (
    binary_erosion,
    convolve,
    distance_transform_edt,
    gaussian_filter,
    uniform_filter,
)
from scipy.special import expit, logit
from sklearn.linear_model import Ridge

from . import sahg1
from .aspc import decode
from .emission import priority_poisson
from .metric import RADIUS_PX
from .residualize import NuisanceResidualizer

# Nuisance column order MUST place the 2 continuous distance columns first
# ("road_m", "claim_m") followed by the 4 categorical block indicators, matching
# NuisanceResidualizer.distance_columns == 2.
NUISANCE_KEYS: tuple[str, ...] = (
    "road_m",
    "claim_m",
    "block_1",
    "block_2",
    "block_3",
    "block_4",
)

PREPARED_BASE13: tuple[str, ...] = (
    "rtp",
    "tmi_hg",
    "tmi_vg",
    "iso_grav_anom",
    "iso_grav_anom_hg",
    "iso_grav_anom_vg",
    "det_elev",
    "det_elev_slope",
    "tmi",
    "cond_surf",
    "depth_to_base_surf",
    "geod_dilaterate",
    "geod_shearrate",
)

OMITTED_LOCAL4: tuple[tuple[str, int], ...] = (
    ("mag_anom", 1),
    ("geod_2ndinv", 4),
    ("iso_grav_anom_slope", 5),
    ("tc", 6),
)

PREPARED_DERIVED5: tuple[str, ...] = (
    "det_local_relief",
    "det_gradient",
    "arc_rtp",
    "arc_det_elev",
    "arc_agreement",
)

PREPARED_LIDAR12: tuple[str, ...] = (
    "lidar_1",
    "lidar_2",
    "lidar_3",
    "lidar_4",
    "lidar_5",
    "lidar_6",
    "lidar_7",
    "lidar_8",
    "lidar_9",
    "lidar_10",
    "lidar_cos2strike",
    "lidar_sin2strike",
)

ENGINEERED8: tuple[str, ...] = (
    "g_sat",
    "r_alt",
    "b_step",
    "tmi_shallow_res",
    "cos_tilt_mag",
    "grad_tilt_mag",
    "cos_tilt_grav",
    "dem_hess_ridge",
)

FEATURE_NAMES: tuple[str, ...] = (
    PREPARED_BASE13
    + tuple(name for name, _ in OMITTED_LOCAL4)
    + PREPARED_DERIVED5
    + PREPARED_LIDAR12
    + ENGINEERED8
)

REGIONAL_SCALAR_NAMES: frozenset[str] = frozenset(
    {
        "rtp",
        "iso_grav_anom",
        "det_elev",
        "tmi",
        "cond_surf",
        "depth_to_base_surf",
        "geod_dilaterate",
        "geod_shearrate",
        "mag_anom",
        "geod_2ndinv",
        "tc",
    }
)

REGIONAL_INDICES: np.ndarray = np.array(
    [i for i, n in enumerate(FEATURE_NAMES) if n in REGIONAL_SCALAR_NAMES], dtype=np.int64
)
G_SAT_INDEX: int = FEATURE_NAMES.index("g_sat")


def triangular_kernel_2d(radius_px: int = RADIUS_PX) -> np.ndarray:
    """Exact discrete 300 m triangular scoring kernel K(d) = max(0, 1 - d / R)."""
    if radius_px < 1:
        raise ValueError("radius_px must be >= 1")
    offs = np.arange(-radius_px, radius_px + 1, dtype=np.float64)
    yy, xx = np.meshgrid(offs, offs, indexing="ij")
    dist = np.hypot(yy, xx)
    return np.maximum(0.0, 1.0 - dist / float(radius_px)).astype(np.float32)


def kernel_trace_score(
    prob_map: np.ndarray,
    domain_mask: np.ndarray,
    visible_mask: np.ndarray,
    *,
    radius_px: int = RADIUS_PX,
) -> np.ndarray:
    """Compute ridge-preserving 300 m kernel-expected trace score sqrt(p0 * (K * p0)).

    Zeroes known visible fault pixels before kernel integration so known fault
    traces cannot contribute synthetic credit to adjacent pixels. Peaks remain
    strictly on non-zero probability ridges because p0(u) multiplies (K * p0)(u).
    """
    p = np.asarray(prob_map, dtype=np.float32)
    dom = np.asarray(domain_mask, dtype=bool)
    vis = np.asarray(visible_mask, dtype=bool)
    if p.shape != dom.shape or p.shape != vis.shape or p.ndim != 2:
        raise ValueError("prob_map, domain_mask, and visible_mask must share 2D shape")
    active = dom & ~vis
    p0 = np.where(active & np.isfinite(p), np.clip(p, 0.0, 1.0), 0.0).astype(np.float32)
    kern = triangular_kernel_2d(radius_px)
    expected_tp = convolve(p0, kern, mode="constant", cval=0.0)
    score = np.sqrt(np.maximum(p0 * np.maximum(expected_tp, 0.0), 0.0))
    return np.where(active, score, 0.0).astype(np.float32)


def emit_rshg1_dots(
    prob_map: np.ndarray,
    domain_mask: np.ndarray,
    visible_mask: np.ndarray,
    *,
    budget_frac: float = 0.0073,
    min_dist: float = 3.0,
    flank_clearance_px: float = 2.0,
    use_kernel_trace: bool = True,
) -> np.ndarray:
    """Emit spaced binary fault detections using visible-only clearance and trace integration."""
    dom = np.asarray(domain_mask, dtype=bool)
    vis = np.asarray(visible_mask, dtype=bool)
    if prob_map.shape != dom.shape or dom.shape != vis.shape:
        raise ValueError("Aligned 2D arrays required")
    if flank_clearance_px < 0 or budget_frac <= 0:
        raise ValueError("Non-negative clearance and positive budget_frac required")
    k = int(round(budget_frac * int(dom.sum())))
    if k <= 0:
        return np.zeros(dom.shape, dtype=bool)
    if flank_clearance_px > 0:
        clear = distance_transform_edt(~vis) > float(flank_clearance_px)
    else:
        clear = ~vis
    eligible = dom & clear
    if use_kernel_trace:
        score = kernel_trace_score(prob_map, dom, vis)
    else:
        score = np.where(
            dom & ~vis & np.isfinite(prob_map), np.clip(prob_map, 0.0, 1.0), 0.0
        ).astype(np.float32)
    return priority_poisson(score, eligible, k, min_dist=min_dist)


def compute_tilt_and_curvature_channels(
    tmi_hg: np.ndarray,
    tmi_vg: np.ndarray,
    grav_hg: np.ndarray,
    grav_vg: np.ndarray,
    det_elev: np.ndarray,
    footprint: np.ndarray,
) -> dict[str, np.ndarray]:
    """Compute potential-field tilt zero-crossing proximity, tilt-depth gradient, and DEM Hessian ridges."""
    fp = np.asarray(footprint, dtype=bool)
    shape = fp.shape
    for arr in (tmi_hg, tmi_vg, grav_hg, grav_vg, det_elev):
        if arr.shape != shape:
            raise ValueError("All input grids must match footprint shape")

    # 1. Magnetic tilt angle zero-crossing proximity & horizontal gradient magnitude
    mag_valid = fp & np.isfinite(tmi_hg) & np.isfinite(tmi_vg)
    med_m = float(np.median(np.abs(tmi_hg[mag_valid]))) if mag_valid.any() else 1.0
    eps_m = max((0.1 * med_m) ** 2, 1e-12)
    denom_m = np.sqrt(np.where(mag_valid, tmi_hg, 0.0) ** 2 + eps_m)
    ratio_m = np.where(mag_valid, tmi_vg, 0.0) / denom_m
    cos_tilt_mag = np.where(mag_valid, 1.0 / np.sqrt(1.0 + ratio_m * ratio_m), np.nan).astype(
        np.float32
    )
    theta_m = np.arctan(ratio_m).astype(np.float32)
    mag_inner = binary_erosion(mag_valid, structure=np.ones((3, 3), dtype=bool), border_value=False)
    grad_tm = sahg1._grad_mag_3x3(np.where(mag_valid, theta_m, 0.0))
    grad_tilt_mag = np.where(mag_inner, grad_tm, np.nan).astype(np.float32)

    # 2. Isostatic gravity tilt angle zero-crossing proximity
    grav_valid = fp & np.isfinite(grav_hg) & np.isfinite(grav_vg)
    med_g = float(np.median(np.abs(grav_hg[grav_valid]))) if grav_valid.any() else 1.0
    eps_g = max((0.1 * med_g) ** 2, 1e-12)
    denom_g = np.sqrt(np.where(grav_valid, grav_hg, 0.0) ** 2 + eps_g)
    ratio_g = np.where(grav_valid, grav_vg, 0.0) / denom_g
    cos_tilt_grav = np.where(grav_valid, 1.0 / np.sqrt(1.0 + ratio_g * ratio_g), np.nan).astype(
        np.float32
    )

    # 3. Multi-scale 100 m DEM Hessian minimum-curvature ridge/scarp convexity
    # Truncated Gaussian radius at sigma=3.0, truncate=3.0 is int(3*3 + 0.5) = 9 px;
    # erode valid mask by radius 10 px (21x21) so boundary fill never leaks inward.
    dem_valid = fp & np.isfinite(det_elev)
    dem_inner = binary_erosion(
        dem_valid, structure=np.ones((21, 21), dtype=bool), border_value=False
    )
    fill_val = float(np.median(det_elev[dem_valid])) if dem_valid.any() else 0.0
    dem_fill = np.where(dem_valid, det_elev, fill_val).astype(np.float32)
    ridge_sum = np.zeros(shape, dtype=np.float32)
    for sigma in (1.5, 3.0):
        hxx = gaussian_filter(dem_fill, sigma=sigma, order=(0, 2), mode="nearest", truncate=3.0)
        hyy = gaussian_filter(dem_fill, sigma=sigma, order=(2, 0), mode="nearest", truncate=3.0)
        hxy = gaussian_filter(dem_fill, sigma=sigma, order=(1, 1), mode="nearest", truncate=3.0)
        trace = hxx + hyy
        disc = np.sqrt(np.maximum((hxx - hyy) ** 2 + 4.0 * hxy * hxy, 0.0))
        lambda_min = 0.5 * (trace - disc)
        ridge_sum += (sigma * sigma) * np.maximum(-lambda_min, 0.0).astype(np.float32)
    dem_hess_ridge = np.where(dem_inner, ridge_sum, np.nan).astype(np.float32)

    return {
        "cos_tilt_mag": cos_tilt_mag,
        "grad_tilt_mag": grad_tilt_mag,
        "cos_tilt_grav": cos_tilt_grav,
        "dem_hess_ridge": dem_hess_ridge,
    }


def compute_shallow_magnetic_residual(
    tmi: np.ndarray, tmi_up150_u8: np.ndarray, footprint: np.ndarray
) -> np.ndarray:
    """Compute shallow-vs-150m upward-continued magnetic persistence inside eroded valid support."""
    fp = np.asarray(footprint, dtype=bool)
    valid = fp & np.isfinite(tmi) & (tmi_up150_u8 > 0)
    inner = binary_erosion(valid, structure=np.ones((5, 5), dtype=bool), border_value=False)
    if not inner.any():
        return np.full(fp.shape, np.nan, dtype=np.float32)
    p01, p99 = np.percentile(tmi[valid], [1.0, 99.0])
    span = max(float(p99 - p01), 1e-6)
    tmi_scaled = np.clip((np.where(valid, tmi, p01) - float(p01)) / span, 0.0, 1.0).astype(
        np.float32
    )
    up150_scaled = np.where(
        valid, np.maximum(tmi_up150_u8.astype(np.float32) - 1.0, 0.0) / 254.0, 0.0
    ).astype(np.float32)
    diff = np.abs(tmi_scaled - up150_scaled)
    return np.where(inner, diff, np.nan).astype(np.float32)


def compute_modality_sahg1_g_sat(
    lidar_bands: dict[str, np.ndarray], det_elev: np.ndarray, footprint: np.ndarray
) -> np.ndarray:
    """Compute strike-projected LiDAR scarp G_sat on eroded LiDAR support (NaN outside)."""
    fp = np.asarray(footprint, dtype=bool)
    raw_valid = fp & np.isfinite(det_elev)
    for b in lidar_bands.values():
        raw_valid &= np.isfinite(b) & (b > 0)
    size = 2 * sahg1.STENCIL_RADIUS_PX + 1
    support = binary_erosion(
        raw_valid, structure=np.ones((size, size), dtype=bool), border_value=False
    )
    if not sahg1.verify_receptive_field_support(support, raw_valid, sahg1.STENCIL_RADIUS_PX):
        raise AssertionError("LiDAR G_sat receptive-field verification failed")

    up = decode(lidar_bands["upface_max"], *sahg1.LIDAR_SPECS["upface_max"])
    down = decode(lidar_bands["downface_max"], *sahg1.LIDAR_SPECS["downface_max"])
    cross = decode(lidar_bands["cross_max"], *sahg1.LIDAR_SPECS["cross_max"])
    total = up + down + cross + 1e-3
    anti = up / total
    veto = 1.0 - cross / total
    del up, down, cross, total
    ln = decode(lidar_bands["lapneg_max"], *sahg1.LIDAR_SPECS["lapneg_max"])
    lp = decode(lidar_bands["lappos_max"], *sahg1.LIDAR_SPECS["lappos_max"])
    balance = 2.0 * np.sqrt(ln * lp) / (ln + lp + 1e-6)
    del ln, lp
    step_raw = decode(lidar_bands["step_max"], *sahg1.LIDAR_SPECS["step_max"])
    step = step_raw / (step_raw + 0.05)
    del step_raw
    coh = np.sqrt(np.clip(decode(lidar_bands["coh100"], *sahg1.LIDAR_SPECS["coh100"]), 0.0, 1.0))
    g0 = np.where(raw_valid, anti * veto * balance * step * coh, 0.0).astype(np.float32)
    del anti, veto, balance, step, coh

    strike_deg = decode(lidar_bands["strike"], *sahg1.LIDAR_SPECS["strike"])
    theta = np.deg2rad(np.where(raw_valid, strike_deg, 0.0)).astype(np.float32)
    del strike_deg
    g_along = np.zeros(fp.shape, dtype=np.float32)
    for phi, kern in sahg1._directional_line_kernels():
        weight = 0.5 * (np.cos(theta - phi) ** 2)
        resp = convolve(g0, kern, mode="nearest")
        g_along += (weight * np.maximum(resp, 0.0)).astype(np.float32)
        del weight, resp

    dem_safe = np.where(raw_valid, det_elev, 0.0).astype(np.float32)
    gy, gx = np.gradient(dem_safe, 100.0)
    del dem_safe
    theta_contour = np.arctan2(gx, -gy)
    del gx, gy
    sin2_diff = 0.5 * (1.0 - np.cos(2.0 * (theta - theta_contour)))
    del theta, theta_contour
    w_oblique = (0.65 + 0.35 * np.clip(sin2_diff, 0.0, 1.0)).astype(np.float32)
    del sin2_diff

    g_strike = np.sqrt(np.maximum(g0 * g_along, 0.0)) * w_oblique
    del g0, g_along, w_oblique
    return np.where(support, g_strike / (g_strike + sahg1.TAU_G), np.nan).astype(np.float32)


def compute_modality_sahg1_r_alt(
    rad_bands: dict[str, np.ndarray], ext_bands: dict[str, np.ndarray], footprint: np.ndarray
) -> np.ndarray:
    """Compute Th-controlled K/U alteration R_alt across full GeoDAWN support (including LiDAR gaps)."""
    fp = np.asarray(footprint, dtype=bool)
    raw_valid = fp.copy()
    for b in (*rad_bands.values(), *ext_bands.values()):
        raw_valid &= np.isfinite(b) & (b > 0)
    size = 2 * sahg1.STENCIL_RADIUS_PX + 1
    support = binary_erosion(
        raw_valid, structure=np.ones((size, size), dtype=bool), border_value=False
    )
    if not sahg1.verify_receptive_field_support(support, raw_valid, sahg1.STENCIL_RADIUS_PX):
        raise AssertionError("Radiometric R_alt receptive-field verification failed")

    uk = np.where(raw_valid, np.maximum(rad_bands["K"].astype(np.float32) - 1.0, 0.0) / 254.0, 0.0)
    uth_elem = np.where(
        raw_valid, np.maximum(rad_bands["Th"].astype(np.float32) - 1.0, 0.0) / 254.0, 0.0
    )
    uthk_ratio = np.where(
        raw_valid, np.maximum(ext_bands["ThK"].astype(np.float32) - 1.0, 0.0) / 254.0, 0.0
    )
    uuth_ratio = np.where(
        raw_valid, np.maximum(ext_bands["UTh"].astype(np.float32) - 1.0, 0.0) / 254.0, 0.0
    )

    ik = (uk - uth_elem) + (1.0 - uthk_ratio)
    del uk, uthk_ratio
    ek = np.clip(ik - uniform_filter(ik, size=9, mode="nearest"), 0.0, 1.0)
    del ik
    eu = np.clip(uuth_ratio - uniform_filter(uuth_ratio, size=9, mode="nearest"), 0.0, 1.0)
    del uuth_ratio
    grad_th = sahg1._grad_mag_3x3(uth_elem)
    del uth_elem
    v_th = np.exp(-4.0 * grad_th).astype(np.float32)
    del grad_th
    r_raw = np.where(support, v_th * (0.6 * ek + 0.4 * eu), 0.0).astype(np.float32)
    del v_th, ek, eu
    r_p95 = max(float(np.percentile(r_raw[support], 95.0)), 1e-6)
    return np.where(support, np.clip(r_raw / r_p95, 0.0, 1.0), np.nan).astype(np.float32)


def compute_modality_sahg1_b_step(
    geophys_bands: dict[str, np.ndarray], footprint: np.ndarray
) -> np.ndarray:
    """Compute subsurface basement/strain step B_step across full geophysical support (including LiDAR gaps)."""
    fp = np.asarray(footprint, dtype=bool)
    raw_valid = fp.copy()
    for b in geophys_bands.values():
        raw_valid &= np.isfinite(b)
    support = binary_erosion(raw_valid, structure=np.ones((5, 5), dtype=bool), border_value=False)
    if not sahg1.verify_receptive_field_support(support, raw_valid, 2):
        raise AssertionError("Geophysical B_step receptive-field verification failed")

    g_hg = sahg1._robust_sigmoid(np.asarray(geophys_bands["iso_grav_anom_hg"], np.float32), support)
    m_hg = sahg1._robust_sigmoid(np.asarray(geophys_bands["tmi_hg"], np.float32), support)
    db_grad = sahg1._grad_mag_3x3(
        np.where(raw_valid, geophys_bands["depth_to_base_surf"], 0.0).astype(np.float32)
    )
    d_bg = sahg1._robust_sigmoid(db_grad, support)
    del db_grad
    strain_sum = np.asarray(geophys_bands["geod_dilaterate"], np.float32) + np.asarray(
        geophys_bands["geod_shearrate"], np.float32
    )
    s_geod = sahg1._robust_sigmoid(strain_sum, support)
    del strain_sum
    return np.where(
        support, 0.35 * g_hg + 0.25 * m_hg + 0.25 * d_bg + 0.15 * s_geod, np.nan
    ).astype(np.float32)


class NanPreservingResidualizer:
    """Training-only nuisance residualizer that preserves NaN on unobserved sensor cells."""

    def __init__(
        self,
        regional_indices: np.ndarray = REGIONAL_INDICES,
        *,
        alpha: float = 100.0,
        distance_columns: int = 2,
    ):
        self.regional_indices = np.asarray(regional_indices, dtype=np.int64)
        self.alpha = float(alpha)
        self.distance_columns = int(distance_columns)
        self._basis_helper = NuisanceResidualizer(
            alpha=alpha, distance_columns=self.distance_columns
        )
        self.medians_: np.ndarray | None = None
        self.scales_: np.ndarray | None = None
        self.models_: dict[int, Ridge] = {}

    def fit(self, nuisance: np.ndarray, features: np.ndarray) -> NanPreservingResidualizer:
        c = np.asarray(nuisance, dtype=np.float32)
        x = np.asarray(features, dtype=np.float32)
        if c.ndim != 2 or x.ndim != 2 or len(c) != len(x):
            raise ValueError("Aligned 2D nuisance and feature matrices required")
        if c.shape[1] < self.distance_columns or not np.isfinite(c).all():
            raise ValueError("Finite nuisance matrix with >= distance_columns required")
        self._basis_helper.n_nuisance = c.shape[1]
        basis_all = self._basis_helper._basis(c, fit=True)

        n_cols = x.shape[1]
        medians = np.zeros(n_cols, dtype=np.float32)
        scales = np.ones(n_cols, dtype=np.float32)
        models: dict[int, Ridge] = {}
        reg_set = set(int(i) for i in self.regional_indices)

        for j in range(n_cols):
            col = x[:, j]
            obs = np.isfinite(col)
            if int(obs.sum()) < 32:
                medians[j] = 0.0
                scales[j] = 1.0
                continue
            vals = col[obs]
            med = float(np.median(vals))
            mad = float(1.4826 * np.median(np.abs(vals - med)))
            std = float(np.std(vals))
            sc = max(mad if mad > 1e-6 else std, 1e-6)
            medians[j] = med
            scales[j] = sc
            if j in reg_set:
                z_obs = np.clip((vals - med) / sc, -8.0, 8.0).astype(np.float32)
                models[j] = Ridge(alpha=self.alpha).fit(basis_all[obs], z_obs)

        self.medians_ = medians
        self.scales_ = scales
        self.models_ = models
        return self

    def transform(
        self, nuisance: np.ndarray, features: np.ndarray, *, remove: bool = True
    ) -> np.ndarray:
        if self.medians_ is None or self.scales_ is None:
            raise RuntimeError("Call fit before transform")
        c = np.asarray(nuisance, dtype=np.float32)
        x = np.asarray(features, dtype=np.float32)
        if len(c) != len(x) or x.shape[1] != len(self.medians_):
            raise ValueError("Feature/nuisance shape mismatch in transform")
        nan_mask = ~np.isfinite(x)
        safe = np.where(nan_mask, self.medians_[None, :], x)
        out = np.clip((safe - self.medians_[None, :]) / self.scales_[None, :], -8.0, 8.0).astype(
            np.float32
        )
        if remove and self.models_:
            basis = self._basis_helper._basis(c, fit=False)
            for j, model in self.models_.items():
                out[:, j] = (out[:, j] - model.predict(basis)).astype(np.float32)
        out[nan_mask] = np.nan
        return out


class RegimeNuisanceCalibrator:
    """Training-only smooth nuisance debiaser followed by LiDAR-gap tail matching."""

    def __init__(self, alpha: float = 100.0, distance_columns: int = 2):
        self.alpha = float(alpha)
        self.distance_columns = int(distance_columns)
        self._basis_helper = NuisanceResidualizer(
            alpha=alpha, distance_columns=self.distance_columns
        )
        self.med_lidar_: float = 0.0
        self.spread_lidar_: float = 1.0
        self.med_gap_: float = 0.0
        self.spread_gap_: float = 1.0
        self.ridge_: Ridge | None = None
        self.mean_nuis_: float = 0.0

    def fit(
        self, prob_bg: np.ndarray, has_lidar_bg: np.ndarray, nuisance_bg: np.ndarray
    ) -> RegimeNuisanceCalibrator:
        p = np.clip(np.asarray(prob_bg, dtype=np.float64), 1e-5, 1.0 - 1e-5)
        ell = logit(p).astype(np.float32)
        hl = np.asarray(has_lidar_bg, dtype=bool)
        c = np.asarray(nuisance_bg, dtype=np.float32)
        if len(p) != len(hl) or len(p) != len(c):
            raise ValueError("Aligned 1D prob_bg, has_lidar_bg and 2D nuisance_bg required")
        if c.shape[1] < self.distance_columns or not np.isfinite(c).all():
            raise ValueError("Finite nuisance_bg with >= distance_columns required")

        # 1. Remove smooth background nuisance shift (road_m, claim_m, block_1..4) on training bg
        self._basis_helper.n_nuisance = c.shape[1]
        basis = self._basis_helper._basis(c, fit=True)
        self.ridge_ = Ridge(alpha=self.alpha).fit(basis, ell)
        pred = self.ridge_.predict(basis)
        self.mean_nuis_ = float(np.mean(pred))
        debiased = ell - (pred - self.mean_nuis_)

        # 2. Match LiDAR-gap background median and (p99 - p50) tail spread to LiDAR-covered domain
        if int(hl.sum()) >= 32:
            self.med_lidar_ = float(np.median(debiased[hl]))
            self.spread_lidar_ = max(
                float(np.percentile(debiased[hl], 99.0) - self.med_lidar_), 0.25
            )
        else:
            self.med_lidar_ = float(np.median(debiased))
            self.spread_lidar_ = max(float(np.percentile(debiased, 99.0) - self.med_lidar_), 0.25)

        if int((~hl).sum()) >= 32:
            self.med_gap_ = float(np.median(debiased[~hl]))
            self.spread_gap_ = max(float(np.percentile(debiased[~hl], 99.0) - self.med_gap_), 0.25)
        else:
            self.med_gap_ = self.med_lidar_
            self.spread_gap_ = self.spread_lidar_
        return self

    def transform(
        self, prob: np.ndarray, has_lidar: np.ndarray, nuisance: np.ndarray
    ) -> np.ndarray:
        if self.ridge_ is None:
            raise RuntimeError("Call fit before transform")
        p = np.clip(np.asarray(prob, dtype=np.float64), 1e-5, 1.0 - 1e-5)
        ell = logit(p)
        hl = np.asarray(has_lidar, dtype=bool)
        c = np.asarray(nuisance, dtype=np.float32)
        basis = self._basis_helper._basis(c, fit=False)
        debiased = ell - (self.ridge_.predict(basis) - self.mean_nuis_)
        if (~hl).any():
            z_gap = (debiased[~hl] - self.med_gap_) / self.spread_gap_
            debiased[~hl] = self.med_lidar_ + self.spread_lidar_ * z_gap
        return np.clip(expit(debiased), 0.0, 1.0).astype(np.float32)


def build_rshg1_feature_memmap(
    *,
    out_path: Path,
    footprint: np.ndarray,
    prepared_path: Path,
    prepared_names: list[str],
    training_tif_path: Path,
    lidar_tif_path: Path,
    lidar_meta: dict[str, Any],
    rad_tif_path: Path,
    rad_meta: dict[str, Any],
    ext_tif_path: Path,
    ext_meta: dict[str, Any],
) -> np.memmap:
    """Stream all 42 preregistered channels into a disk-backed float32 memmap (<1.5 GiB RSS)."""
    import rasterio

    fp = np.asarray(footprint, dtype=bool)
    fp_ids = np.flatnonzero(fp)
    n_fp = len(fp_ids)
    n_cols = len(FEATURE_NAMES)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    mm = np.lib.format.open_memmap(out_path, mode="w+", dtype=np.float32, shape=(n_fp, n_cols))

    prep = np.load(prepared_path, mmap_mode="r")
    if prep.shape[0] != n_fp:
        raise ValueError(f"Prepared row count {prep.shape[0]} != footprint count {n_fp}")

    # 1. Cols 0..12: 13 prepared physical competition bands
    for col_idx, name in enumerate(PREPARED_BASE13):
        src_idx = prepared_names.index(name)
        mm[:, col_idx] = prep[:, src_idx]

    # 2. Cols 13..16: 4 omitted local competition bands from training_features.tif
    with rasterio.open(training_tif_path) as ds:
        for offset, (_, band_idx) in enumerate(OMITTED_LOCAL4):
            raw = ds.read(band_idx).astype(np.float32)
            bad = (~fp) | (~np.isfinite(raw)) | (np.abs(raw) > 1e20)
            raw[bad] = np.nan
            mm[:, 13 + offset] = raw.ravel()[fp_ids]
            del raw, bad
    gc.collect()

    # 3. Cols 17..21: 5 local DEM + radial-gradient arc channels
    for offset, name in enumerate(PREPARED_DERIVED5):
        src_idx = prepared_names.index(name)
        mm[:, 17 + offset] = prep[:, src_idx]

    # 4. Read LiDAR valid mask + bands once for Cols 22..33 and G_sat (Col 34)
    lidar_bands: dict[str, np.ndarray] = {}
    with rasterio.open(lidar_tif_path) as ds:
        lidar_valid_u8 = ds.read(lidar_meta["bands"].index("valid") + 1)
        for bname in sahg1.LIDAR_SPECS:
            idx = lidar_meta["bands"].index(bname) + 1
            lidar_bands[bname] = ds.read(idx)
    lidar_valid_fp = (lidar_valid_u8 > 0).ravel()[fp_ids]
    del lidar_valid_u8
    for offset, name in enumerate(PREPARED_LIDAR12):
        src_idx = prepared_names.index(name)
        vals = np.array(prep[:, src_idx], dtype=np.float32, copy=True)
        vals[~lidar_valid_fp] = np.nan
        mm[:, 22 + offset] = vals
        del vals
    del lidar_valid_fp
    gc.collect()

    def _unpack_prep(col_name: str) -> np.ndarray:
        grid = np.full(fp.shape, np.nan, dtype=np.float32)
        grid.ravel()[fp_ids] = prep[:, prepared_names.index(col_name)]
        return grid

    det_elev = _unpack_prep("det_elev")

    # Col 34: G_sat on eroded LiDAR + DEM support (NaN outside LiDAR support!)
    g_sat_grid = compute_modality_sahg1_g_sat(lidar_bands, det_elev, fp)
    mm[:, 34] = g_sat_grid.ravel()[fp_ids]
    del lidar_bands, g_sat_grid
    gc.collect()

    # Col 35: R_alt on eroded GeoDAWN radiometric support (covers ~98%+ of footprint including LiDAR gaps!)
    rad_bands: dict[str, np.ndarray] = {}
    with rasterio.open(rad_tif_path) as ds:
        for bname in sahg1.RAD_BANDS:
            idx = rad_meta["channels"].index(bname) + 1
            rad_bands[bname] = ds.read(idx)
    ext_bands: dict[str, np.ndarray] = {}
    with rasterio.open(ext_tif_path) as ds:
        for bname in sahg1.EXT_BANDS:
            idx = ext_meta["channels"].index(bname) + 1
            ext_bands[bname] = ds.read(idx)
        tmi_up150_u8 = ds.read(ext_meta["channels"].index("TMI_up150") + 1)

    r_alt_grid = compute_modality_sahg1_r_alt(rad_bands, ext_bands, fp)
    mm[:, 35] = r_alt_grid.ravel()[fp_ids]
    del rad_bands, ext_bands, r_alt_grid
    gc.collect()

    # Col 36: B_step on eroded geophysical support (covers ~99% of footprint including LiDAR gaps!)
    geophys_bands = {
        name: _unpack_prep(name)
        for name in (
            "iso_grav_anom_hg",
            "tmi_hg",
            "depth_to_base_surf",
            "geod_dilaterate",
            "geod_shearrate",
        )
    }
    b_step_grid = compute_modality_sahg1_b_step(geophys_bands, fp)
    mm[:, 36] = b_step_grid.ravel()[fp_ids]
    del geophys_bands, b_step_grid
    gc.collect()

    # Col 37: tmi_shallow_res (surface tmi vs 150 m upward-continued TMI_up150)
    tmi_grid = _unpack_prep("tmi")
    tmi_res = compute_shallow_magnetic_residual(tmi_grid, tmi_up150_u8, fp)
    mm[:, 37] = tmi_res.ravel()[fp_ids]
    del tmi_grid, tmi_up150_u8, tmi_res
    gc.collect()

    # Cols 38..41: potential-field tilt zero-crossings & multi-scale DEM Hessian ridge
    tmi_hg = _unpack_prep("tmi_hg")
    tmi_vg = _unpack_prep("tmi_vg")
    grav_hg = _unpack_prep("iso_grav_anom_hg")
    grav_vg = _unpack_prep("iso_grav_anom_vg")
    tc_dict = compute_tilt_and_curvature_channels(tmi_hg, tmi_vg, grav_hg, grav_vg, det_elev, fp)
    mm[:, 38] = tc_dict["cos_tilt_mag"].ravel()[fp_ids]
    mm[:, 39] = tc_dict["grad_tilt_mag"].ravel()[fp_ids]
    mm[:, 40] = tc_dict["cos_tilt_grav"].ravel()[fp_ids]
    mm[:, 41] = tc_dict["dem_hess_ridge"].ravel()[fp_ids]
    del tmi_hg, tmi_vg, grav_hg, grav_vg, det_elev, tc_dict
    mm.flush()
    gc.collect()

    return np.load(out_path, mmap_mode="r")
