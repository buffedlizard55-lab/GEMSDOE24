"""H24-GT1: Basement-hinge + shallow thermal DAB co-location detector.

Physical layers:
- depth_to_base_surf gradient magnitude (basement offset)
- iso_grav_anom_hg (gravity horizontal gradient)
- det_elev_slope (alluvial flatness gate)
- F2mDAB thermal anomaly from 2m probe IDW (INGENIOUS, GDR 1391)

Support mask: binary erosion 9x9 ensuring complete 400 m stencil.
No catalogue-derived feature; catalogue only masked at emission/evaluation.
"""

from __future__ import annotations

import numpy as np
from scipy.ndimage import binary_dilation, binary_erosion, distance_transform_edt, gaussian_filter

STENCIL_RADIUS_PX = 4
THERMAL_RADIUS_M = 5000
THERMAL_K = 100  # nearest probes to consider
TAU_THERMAL = 10.0  # clip DAB at 10C, normalize by 10


def verify_support(support: np.ndarray, raw_valid: np.ndarray, radius_px: int = STENCIL_RADIUS_PX) -> bool:
    support, raw_valid = np.asarray(support, bool), np.asarray(raw_valid, bool)
    if support.shape != raw_valid.shape or support.ndim != 2 or radius_px < 0:
        raise ValueError("Aligned 2D masks required")
    if not support.any():
        return False
    size = 2 * int(radius_px) + 1
    dilated = binary_dilation(support, structure=np.ones((size, size), bool), border_value=False)
    if radius_px > 0:
        r = int(radius_px)
        if support[:r, :].any() or support[-r:, :].any() or support[:, :r].any() or support[:, -r:].any():
            return False
    return bool(not np.any(dilated & ~raw_valid))


def _robust_sigmoid(x: np.ndarray, support: np.ndarray) -> np.ndarray:
    vals = x[support]
    if not vals.size or not np.isfinite(vals).all():
        raise ValueError("Finite supported values required")
    med = float(np.median(vals))
    q25, q75 = np.percentile(vals, [25.0, 75.0])
    iqr = max(float(q75 - q25), 1e-6)
    z = np.clip((np.where(np.isfinite(x), x, med) - med) / iqr, -10.0, 10.0)
    out = (1.0 / (1.0 + np.exp(-z))).astype(np.float32)
    out[~support] = 0.0
    return out


def _grad_mag_3x3_filled(a: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """Gradient magnitude on gap-filled array, but only trust where original valid."""
    # Fill NaN via nearest valid (distance_transform_edt indices)
    if not valid.any():
        return np.zeros(a.shape, dtype=np.float32)
    # Fill with nearest valid
    inds = distance_transform_edt(~valid, return_distances=False, return_indices=True)
    filled = a.copy()
    filled[~valid] = a[tuple(inds[:, ~valid])]
    gy, gx = np.gradient(filled, 100.0)  # 100 m pixel
    mag = np.hypot(gx, gy).astype(np.float32)
    mag[~valid] = 0.0
    return mag


def build_thermal_field(
    footprint: np.ndarray,
    probe_xy: np.ndarray,  # (N,2) UTM x,y in EPSG:32611
    probe_dab: np.ndarray,  # (N,) F2mDAB values
    transform,  # rasterio Affine
    radius_m: float = THERMAL_RADIUS_M,
    k_nearest: int = THERMAL_K,
) -> np.ndarray:
    """IDW thermal anomaly field normalized to [0,1]. Vectorized in tiles to avoid O(HW*N)."""
    from scipy.spatial import cKDTree

    fp = np.asarray(footprint, bool)
    H, W = fp.shape
    # Convert probe UTM to pixel coords to build tree in pixel space (approx)
    # Use inverse transform: col,row = ~transform * (x,y)
    inv = ~transform
    probe_cols_rows = np.array([inv * (x, y) for x, y in probe_xy])
    # probe_cols_rows is (N,2) col,row
    # But KDTree should be in UTM meters for true distance; we have UTM, so use UTM
    tree = cKDTree(probe_xy)
    # For each footprint pixel, query nearest probes within radius
    # To avoid per-pixel Python loop overhead, tile processing with vectorization
    ys, xs = np.nonzero(fp)  # footprint pixels only
    # Convert pixel to UTM for querying
    # UTM = transform * (col,row)
    # rasterio transform maps col,row to x,y: x = transform.a*col + transform.c, y = transform.e*row + transform.f? But we have Affine.
    # Use transform * (col,row)
    # Let's compute via affine
    # Affine: |a b c| |col|   |x|
    #         |d e f|*|row| = |y|
    us = transform.c + transform.a * xs + transform.b * ys
    vs = transform.f + transform.d * xs + transform.e * ys
    pts_utm = np.column_stack((us, vs))  # (P,2)

    # Tiled query to avoid huge allocation: process in chunks of 100k pixels
    field = np.zeros(fp.shape, dtype=np.float32)
    chunk = 100000
    for start in range(0, len(ys), chunk):
        end = min(start + chunk, len(ys))
        pts_chunk = pts_utm[start:end]
        dists, idxs = tree.query(pts_chunk, k=k_nearest, distance_upper_bound=radius_m, workers=1)
        if k_nearest == 1:
            dists = dists[:, None]
            idxs = idxs[:, None]
        for pi in range(end - start):
            col_i = idxs[pi]
            d_i = dists[pi]
            mask = np.isfinite(d_i) & (d_i <= radius_m) & (d_i >= 0) & (col_i < len(probe_dab)) & (col_i >= 0)
            if not np.any(mask):
                continue
            valid_d = d_i[mask]
            valid_idx = col_i[mask].astype(int)
            valid_d = np.maximum(valid_d, 50.0)
            w = 1.0 / (valid_d ** 2)
            dab_vals = probe_dab[valid_idx]
            good = np.isfinite(dab_vals)
            if not good.any():
                continue
            w = w[good]
            dab_vals = dab_vals[good]
            t = np.sum(w * dab_vals) / np.sum(w)
            t = np.clip(t, 0.0, TAU_THERMAL) / TAU_THERMAL
            field[ys[start + pi], xs[start + pi]] = t
        # progress
        if (start // chunk) % 10 == 0:
            print(f"Thermal tiling {start}/{len(ys)}", flush=True)
    return field


def build_surfaces(
    footprint: np.ndarray,
    depth_to_base: np.ndarray,
    iso_grav_hg: np.ndarray,
    det_slope: np.ndarray,
    thermal_norm: np.ndarray,
) -> tuple[dict[str, np.ndarray], np.ndarray]:
    fp = np.asarray(footprint, bool)
    if fp.ndim != 2 or not fp.any():
        raise ValueError("Nonempty footprint required")
    for arr in (depth_to_base, iso_grav_hg, det_slope, thermal_norm):
        if np.asarray(arr).shape != fp.shape:
            raise ValueError("Band shape mismatch")

    raw_valid = fp.copy()
    for b in (depth_to_base, iso_grav_hg, det_slope):
        raw_valid &= np.isfinite(np.asarray(b))
    # thermal_norm is allowed to be zero outside radius, so we require finite there (it is all finite)
    raw_valid &= np.isfinite(thermal_norm)

    size = 2 * STENCIL_RADIUS_PX + 1
    support = binary_erosion(raw_valid, structure=np.ones((size, size), bool), border_value=False)
    if not verify_support(support, raw_valid, STENCIL_RADIUS_PX):
        raise AssertionError("Support verification failed")

    # Basement hinge B
    # depth gradient magnitude (filled)
    valid_depth = np.isfinite(depth_to_base) & fp
    grad_depth = _grad_mag_3x3_filled(depth_to_base.astype(np.float32), valid_depth)
    # Robust sigmoids on support
    g_depth_sig = _robust_sigmoid(grad_depth, support)
    g_hg_sig = _robust_sigmoid(iso_grav_hg.astype(np.float32), support)
    B_raw = 0.6 * g_depth_sig + 0.4 * g_hg_sig
    B = np.where(support, B_raw, 0.0).astype(np.float32)

    # Flatness mask F
    slope = np.where(raw_valid, det_slope.astype(np.float32), 0.0)
    F = np.exp(-np.clip(slope, 0, 45) / 5.0).astype(np.float32)
    F = np.where(support, F, 0.0)

    # Candidate S = B * (0.3+0.7*T) * (0.5+0.5*F)
    T = np.where(support, np.clip(thermal_norm, 0, 1), 0.0).astype(np.float32)
    S = np.where(support, B * (0.3 + 0.7 * T) * (0.5 + 0.5 * F), 0.0).astype(np.float32)

    # Ablation B_only = B * (0.5+0.5*F) (no thermal)
    B_only = np.where(support, B * (0.5 + 0.5 * F), 0.0).astype(np.float32)

    surfaces = {
        "thermal_norm": T,
        "basement_B": B,
        "flatness_F": F,
        "B_only": B_only,
        "candidate": S,
    }
    return surfaces, support

