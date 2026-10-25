"""Preregistered H24-SAHG1: Strike-Aligned Hydrothermal-Geomorphic Conduit Detector.

Combines:
1. Strike-projected 3DEP LiDAR antislope scarp tensor (G_strike) with contour-obliquity
   attenuation of equipotential pluvial lake shorelines, mapped through a saturating
   structural gate G_sat = G_strike / (G_strike + 0.015).
2. Stable-Thorium-controlled mobile-K and mobile-U alteration contrast (R_alt) from
   cached GeoDAWN radiometric and contractor ratio grids.
3. Subsurface gravity/magnetic/basement-step and geodetic transtensional strain
   corroboration (B_step) from prepared competition bridge channels.
4. Complete discrete receptive-field validity mask: binary erosion of raw channel
   validity over the exact 9x9 (radius 4 px = 400 m) maximum stencil footprint so
   no boundary/nodata fill value ever influences a supported pixel.
"""

from __future__ import annotations

import gc

import numpy as np
from scipy.ndimage import binary_dilation, binary_erosion, convolve, uniform_filter

from .aspc import BANDS as ASPC_BANDS
from .aspc import decode

LIDAR_SPECS = {
    **ASPC_BANDS,
    "strike": (180.0, "linear"),
}
RAD_BANDS = ("K", "Th", "U")
EXT_BANDS = ("ThK", "UTh")
GEOPHYS_BANDS = (
    "det_elev",
    "det_elev_slope",
    "iso_grav_anom_hg",
    "tmi_hg",
    "depth_to_base_surf",
    "geod_dilaterate",
    "geod_shearrate",
)
STENCIL_RADIUS_PX = 4
TAU_G = 0.015


def verify_receptive_field_support(
    support: np.ndarray, raw_valid: np.ndarray, radius_px: int = STENCIL_RADIUS_PX
) -> bool:
    """Prove every stencil neighbour within +-radius_px of ``support`` lies inside ``raw_valid``."""
    support, raw_valid = np.asarray(support, bool), np.asarray(raw_valid, bool)
    if support.shape != raw_valid.shape or support.ndim != 2 or radius_px < 0:
        raise ValueError("Aligned 2D boolean masks and nonnegative radius required")
    if not support.any():
        return False
    size = 2 * int(radius_px) + 1
    dilated = binary_dilation(
        support, structure=np.ones((size, size), dtype=bool), border_value=False
    )
    if radius_px > 0:
        r = int(radius_px)
        if (
            support[:r, :].any()
            or support[-r:, :].any()
            or support[:, :r].any()
            or support[:, -r:].any()
        ):
            return False
    return bool(not np.any(dilated & ~raw_valid))


def _directional_line_kernels() -> list[tuple[float, np.ndarray]]:
    """Four 5x5 directional line kernels at 0, 45, 90, 135 degrees (radius 2 px = 200 m)."""
    w0, w1, w2 = 0.30, 0.22, 0.13
    k_ew = np.zeros((5, 5), dtype=np.float32)
    k_ew[2, :] = [w2, w1, w0, w1, w2]

    k_diag1 = np.zeros((5, 5), dtype=np.float32)
    for i, w in enumerate((w2, w1, w0, w1, w2)):
        k_diag1[4 - i, i] = w

    k_ns = k_ew.T.copy()

    k_diag2 = np.zeros((5, 5), dtype=np.float32)
    for i, w in enumerate((w2, w1, w0, w1, w2)):
        k_diag2[i, i] = w

    return [
        (0.0, k_ew),
        (np.pi / 4.0, k_diag1),
        (np.pi / 2.0, k_ns),
        (3.0 * np.pi / 4.0, k_diag2),
    ]


def _robust_sigmoid(x: np.ndarray, support: np.ndarray) -> np.ndarray:
    vals = x[support]
    if not vals.size or not np.isfinite(vals).all():
        raise ValueError("Finite supported values required for robust sigmoid")
    med = float(np.median(vals))
    q25, q75 = np.percentile(vals, [25.0, 75.0])
    iqr = max(float(q75 - q25), 1e-6)
    z = np.clip((np.where(np.isfinite(x), x, med) - med) / iqr, -10.0, 10.0)
    out = (1.0 / (1.0 + np.exp(-z))).astype(np.float32)
    out[~support] = 0.0
    return out


def _grad_mag_3x3(a: np.ndarray) -> np.ndarray:
    """Central-difference gradient magnitude using a strictly 3x3 stencil (radius 1 px)."""
    safe = np.where(np.isfinite(a), a, 0.0).astype(np.float32)
    gy, gx = np.gradient(safe)
    return np.hypot(gx, gy).astype(np.float32)


def build_surfaces(
    lidar_bands: dict[str, np.ndarray],
    rad_bands: dict[str, np.ndarray],
    ext_bands: dict[str, np.ndarray],
    geophys_bands: dict[str, np.ndarray],
    footprint: np.ndarray,
) -> tuple[dict[str, np.ndarray], np.ndarray]:
    """Compute SAHG1 surface, intermediate factors, and verified support mask (memory-frugal)."""
    fp = np.asarray(footprint, bool)
    if fp.ndim != 2 or not fp.any():
        raise ValueError("Nonempty 2D footprint required")
    if set(lidar_bands) != set(LIDAR_SPECS):
        raise ValueError("Missing required 3DEP LiDAR bands")
    if set(rad_bands) != set(RAD_BANDS) or set(ext_bands) != set(EXT_BANDS):
        raise ValueError("Missing required GeoDAWN radiometric or ratio bands")
    if set(geophys_bands) != set(GEOPHYS_BANDS):
        raise ValueError("Missing required geophysical/DEM bridge bands")

    raw_valid = fp.copy()
    for b in (*lidar_bands.values(), *rad_bands.values(), *ext_bands.values()):
        arr = np.asarray(b)
        if arr.shape != fp.shape:
            raise ValueError("Band shape mismatch")
        raw_valid &= np.isfinite(arr) & (arr > 0)
    for b in geophys_bands.values():
        arr = np.asarray(b)
        if arr.shape != fp.shape:
            raise ValueError("Geophysical band shape mismatch")
        raw_valid &= np.isfinite(arr)

    size = 2 * STENCIL_RADIUS_PX + 1
    support = binary_erosion(
        raw_valid, structure=np.ones((size, size), dtype=bool), border_value=False
    )
    if not verify_receptive_field_support(support, raw_valid, STENCIL_RADIUS_PX):
        raise AssertionError("Discrete receptive-field support verification failed")

    # 1. Decode LiDAR descriptors and compute strike-aligned geomorphic scarp core
    up = decode(lidar_bands["upface_max"], *LIDAR_SPECS["upface_max"])
    down = decode(lidar_bands["downface_max"], *LIDAR_SPECS["downface_max"])
    cross = decode(lidar_bands["cross_max"], *LIDAR_SPECS["cross_max"])
    total = up + down + cross + 1e-3
    anti = up / total
    veto = 1.0 - cross / total
    del up, down, cross, total
    ln = decode(lidar_bands["lapneg_max"], *LIDAR_SPECS["lapneg_max"])
    lp = decode(lidar_bands["lappos_max"], *LIDAR_SPECS["lappos_max"])
    balance = 2.0 * np.sqrt(ln * lp) / (ln + lp + 1e-6)
    del ln, lp
    step_raw = decode(lidar_bands["step_max"], *LIDAR_SPECS["step_max"])
    step = step_raw / (step_raw + 0.05)
    del step_raw
    coh = np.sqrt(np.clip(decode(lidar_bands["coh100"], *LIDAR_SPECS["coh100"]), 0.0, 1.0))
    g0 = np.where(raw_valid, anti * veto * balance * step * coh, 0.0).astype(np.float32)
    del anti, veto, balance, step, coh

    strike_deg = decode(lidar_bands["strike"], *LIDAR_SPECS["strike"])
    theta = np.deg2rad(np.where(raw_valid, strike_deg, 0.0)).astype(np.float32)
    del strike_deg
    g_along = np.zeros(fp.shape, dtype=np.float32)
    for phi, kern in _directional_line_kernels():
        weight = 0.5 * (np.cos(theta - phi) ** 2)
        resp = convolve(g0, kern, mode="nearest")
        g_along += (weight * np.maximum(resp, 0.0)).astype(np.float32)
        del weight, resp

    dem_safe = np.where(raw_valid, geophys_bands["det_elev"], 0.0).astype(np.float32)
    gy, gx = np.gradient(dem_safe, 100.0)
    del dem_safe
    theta_contour = np.arctan2(gx, -gy)
    del gx, gy
    sin2_diff = 0.5 * (1.0 - np.cos(2.0 * (theta - theta_contour)))
    del theta, theta_contour
    w_oblique = (0.65 + 0.35 * np.clip(sin2_diff, 0.0, 1.0)).astype(np.float32)
    del sin2_diff

    g_strike = np.where(support, np.sqrt(np.maximum(g0 * g_along, 0.0)) * w_oblique, 0.0).astype(
        np.float32
    )
    del g_along, w_oblique
    g_sat = np.where(support, g_strike / (g_strike + TAU_G), 0.0).astype(np.float32)

    # 2. Stable-Thorium-controlled mobile-K and mobile-U alteration contrast
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
    grad_th = _grad_mag_3x3(uth_elem)
    del uth_elem
    v_th = np.exp(-4.0 * grad_th).astype(np.float32)
    del grad_th
    r_raw = np.where(support, v_th * (0.6 * ek + 0.4 * eu), 0.0).astype(np.float32)
    del v_th, ek, eu
    r_p95 = max(float(np.percentile(r_raw[support], 95.0)), 1e-6)
    r_alt = np.where(support, np.clip(r_raw / r_p95, 0.0, 1.0), 0.0).astype(np.float32)
    del r_raw

    # 3. Subsurface basement-step & geodetic transtensional strain corroboration
    g_hg = _robust_sigmoid(np.asarray(geophys_bands["iso_grav_anom_hg"], np.float32), support)
    m_hg = _robust_sigmoid(np.asarray(geophys_bands["tmi_hg"], np.float32), support)
    db_grad = _grad_mag_3x3(
        np.where(raw_valid, geophys_bands["depth_to_base_surf"], 0.0).astype(np.float32)
    )
    d_bg = _robust_sigmoid(db_grad, support)
    del db_grad
    strain_sum = np.asarray(geophys_bands["geod_dilaterate"], np.float32) + np.asarray(
        geophys_bands["geod_shearrate"], np.float32
    )
    s_geod = _robust_sigmoid(strain_sum, support)
    del strain_sum
    b_step = np.where(support, 0.35 * g_hg + 0.25 * m_hg + 0.25 * d_bg + 0.15 * s_geod, 0.0).astype(
        np.float32
    )
    del g_hg, m_hg, d_bg, s_geod, raw_valid

    # 4. Combined SAHG1 conduit score
    h_conduit = np.where(support, np.sqrt(np.maximum(r_alt * b_step, 0.0)), 0.0).astype(np.float32)
    candidate = np.where(
        support,
        np.clip(g_sat * (0.15 + 0.85 * h_conduit) * np.sqrt(np.maximum(b_step, 0.0)), 0.0, 1.0),
        0.0,
    ).astype(np.float32)
    geomorphic_only = np.where(support, g0, 0.0).astype(np.float32)
    del g0
    gc.collect()

    surfaces = {
        "geomorphic_core_g0": geomorphic_only,
        "strike_scarp_g_strike": g_strike,
        "saturating_scarp_g_sat": g_sat,
        "radiometric_alteration_r_alt": r_alt,
        "basement_step_b_step": b_step,
        "hydrothermal_conduit_h": h_conduit,
        "candidate": candidate,
    }
    return surfaces, support
