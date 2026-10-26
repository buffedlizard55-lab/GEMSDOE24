"""H24-DRAIN1: Drainage-network deflection & knickpoint surfaces from det_elev.

Computes valley concavity, profile curvature knickpoint, and aspect-deflection
on the 100 m det_elev band (training_features.tif). All operations are
label-free; no catalogue, no registry raster, no INGENIOUS CSV is read.

Formulas stated explicitly for auditability; support mask eroded 21x21 so
9x9 stencil never leaks over invalid boundaries.
"""

from __future__ import annotations

import numpy as np
from scipy.ndimage import binary_erosion, gaussian_filter
from scipy.ndimage import distance_transform_edt as edt

from .sahg1 import verify_receptive_field_support


def build_drain_surfaces(det_elev: np.ndarray, footprint: np.ndarray) -> tuple[dict[str, np.ndarray], np.ndarray]:
    """Build DRAIN1 candidate and intermediate surfaces.

    Inputs:
        det_elev: float32 DEM band (det_elev from training_features), shape (H,W)
        footprint: bool mask of scored footprint (5,167,373 px)

    Returns:
        surfaces dict with keys: valley, c_prof, asp_grad, drain_candidate
        support: bool mask where every 21x21 neighbour is valid (9 px stencil radius)
    """
    fp = np.asarray(footprint, bool)
    de = np.asarray(det_elev, np.float32)
    if fp.shape != de.shape or fp.ndim != 2 or not fp.any():
        raise ValueError("Aligned nonempty footprint and det_elev required")
    # valid is footprint + finite + not sentinel
    valid = fp & np.isfinite(de) & (np.abs(de) < 1e30)
    if not valid.any():
        raise ValueError("No valid DEM pixels inside footprint")
    # support: 21x21 erosion guarantees radius 10 > max sigma truncation 9
    support = binary_erosion(valid, structure=np.ones((21, 21), dtype=bool), border_value=False)
    if not verify_receptive_field_support(support, valid, 10):
        raise AssertionError("DRAIN support receptive-field verification failed")
    # nearest-valid fill for derivative neighborhoods; isolated invalids stay via support erosion
    # distance_transform_edt with return_indices is memory heavy but okay for 12M
    _, (rr, cc) = edt(~valid, return_indices=True, return_distances=True)  # type: ignore
    dem_fill = de[rr, cc].astype(np.float32)
    # dem_fill outside support may be fill values, but final candidate masked to support
    # multi-scale valley (concave) Hessian response
    valley = np.zeros(fp.shape, dtype=np.float32)
    # also compute profile curvature intermediate
    # need gradients for aspect/profile
    # smooth with sigma=1 for gradient
    sm1 = gaussian_filter(dem_fill, sigma=1.0, mode="nearest", truncate=3.0)
    gy, gx = np.gradient(sm1, 100.0)  # gy = d/drow, gx = d/dcol
    # preserve for later
    grad_mag = np.hypot(gx, gy).astype(np.float32)
    slope_deg = np.degrees(np.arctan(grad_mag)).astype(np.float32)
    theta = np.arctan2(gy, gx).astype(np.float32)  # aspect (-pi, pi)
    del sm1

    # Hessian multi-scale
    for sigma in (1.5, 3.0):
        hxx = gaussian_filter(dem_fill, sigma=sigma, order=(0, 2), mode="nearest", truncate=3.0)
        hyy = gaussian_filter(dem_fill, sigma=sigma, order=(2, 0), mode="nearest", truncate=3.0)
        hxy = gaussian_filter(dem_fill, sigma=sigma, order=(1, 1), mode="nearest", truncate=3.0)
        trace = hxx + hyy
        disc = np.sqrt(np.maximum((hxx - hyy) ** 2 + 4.0 * hxy * hxy, 0.0))
        lmax = 0.5 * (trace + disc)  # most positive curvature (valley)
        # scale by sigma^2 as scale-normalized
        valley += (sigma * sigma) * np.maximum(lmax, 0.0).astype(np.float32)
        # we don't need ridge separately now
        del hxx, hyy, hxy, trace, disc, lmax

    # profile curvature: second derivative along slope direction
    # recompute Hessian at sigma=1.5 for curvature (choose single scale for stability)
    hxx1 = gaussian_filter(dem_fill, sigma=1.5, order=(0, 2), mode="nearest", truncate=3.0)
    hyy1 = gaussian_filter(dem_fill, sigma=1.5, order=(2, 0), mode="nearest", truncate=3.0)
    hxy1 = gaussian_filter(dem_fill, sigma=1.5, order=(1, 1), mode="nearest", truncate=3.0)
    # unit slope vector
    eps = 1e-6
    cx = gx / np.maximum(grad_mag, eps)
    cy = gy / np.maximum(grad_mag, eps)
    # profile curvature absolute
    c_prof = np.abs(hxx1 * cx * cx + 2.0 * hxy1 * cx * cy + hyy1 * cy * cy).astype(np.float32)
    del hxx1, hyy1, hxy1, cx, cy

    # aspect deflection gradient magnitude: circular gradient of theta
    # unwrap circular difference: wrap to [-pi, pi] then gradient
    # compute small finite differences of theta with wrapping
    # Use approach: compute cos/sin components gradient magnitude
    cos_t = np.cos(theta).astype(np.float32)
    sin_t = np.sin(theta).astype(np.float32)
    # gradients of cos and sin
    gy_c, gx_c = np.gradient(cos_t, 100.0)
    gy_s, gx_s = np.gradient(sin_t, 100.0)
    # aspect gradient magnitude approx hypot of both
    asp_grad = np.hypot(np.hypot(gx_c, gy_c), np.hypot(gx_s, gy_s)).astype(np.float32)
    del cos_t, sin_t, gx_c, gy_c, gx_s, gy_s, theta, gx, gy

    # normalization per support p99
    def p99_norm(a: np.ndarray) -> np.ndarray:
        v = a[support]
        if not v.size:
            return np.zeros_like(a)
        p99 = float(np.percentile(v, 99.0))
        if not np.isfinite(p99) or p99 <= 1e-9:
            p99 = float(np.percentile(v, 95.0)) if np.isfinite(np.percentile(v, 95.0)) else 1.0
            if p99 <= 1e-9:
                p99 = 1.0
        out = np.clip(a / p99, 0.0, 1.0).astype(np.float32)
        out[~support] = 0.0
        return out

    valley_n = p99_norm(valley)
    c_prof_n = p99_norm(c_prof)
    asp_grad_n = p99_norm(asp_grad)
    # slope gate: flat basin preference
    slope_gate = np.exp(-slope_deg / 5.0).astype(np.float32)
    slope_gate[~support] = 0.0

    # combined drain score
    # D = sigma_valley * (0.5+0.5σ(C)) * (0.6+0.4σ(|∇θ|)) * slope_gate
    drain = (valley_n * (0.5 + 0.5 * c_prof_n) * (0.6 + 0.4 * asp_grad_n) * slope_gate).astype(np.float32)
    drain[~support] = 0.0
    # also mask outside support already, but ensure footprint outside support is 0 not NaN for canary
    # surfaces masked to support for interpretability; canary uses zeros outside support

    surfaces = {
        "valley": np.where(support, valley, 0.0).astype(np.float32),
        "c_prof": np.where(support, c_prof, 0.0).astype(np.float32),
        "asp_grad": np.where(support, asp_grad, 0.0).astype(np.float32),
        "drain_candidate": drain,
    }
    # also include normalized versions for diagnostics if needed
    surfaces["_valley_n"] = valley_n
    surfaces["_c_prof_n"] = c_prof_n
    surfaces["_asp_grad_n"] = asp_grad_n
    surfaces["_slope_gate"] = slope_gate

    return surfaces, support
