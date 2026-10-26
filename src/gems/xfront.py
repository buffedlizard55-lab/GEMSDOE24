"""H24-XFRONT — cross-modal oriented step corroboration under a rotation null.

Preregistration: ``knowledge/25_preregistered_XFRONT_2026-10-26.md`` (commit
``3ebb375``) + amendment ``knowledge/26_XFRONT_prereg_amendment_2026-10-26.md``
(``MIN_TOTAL_WEIGHT = 2.0``, null evaluated on the eligible flat index set).
Every constant below is frozen before any result and must not be retuned.

Physical claim
--------------
A fault that is missing from the public catalogue is usually one whose surface
scarp is buried or subdued. Burial removes the topographic ridge but not the
*step* the structure imposes on independent potential-field and airborne-
electromagnetic layers, and the step forces those layers' across-strike
gradient vectors to share one strike. H24-XFRONT therefore measures, per pixel,
the weighted mean-resultant length of the **doubled** across-strike orientations
of independent layers and keeps only the **excess** of that coherence over a
rotation null that preserves every layer's own edge geometry while destroying
between-layer orientation agreement.

Named non-fault mimic (declared in the preregistration): a lithologic /
stratigraphic contact or a Lake Lahontan strandline also produces co-located,
co-oriented steps in AEM depth, conductivity, gravity and DEM with no fault.

All inputs are label-free; no prior submission pixel is read.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy.ndimage import gaussian_filter

MODALITIES: tuple[str, ...] = (
    "rtp",
    "iso_grav_anom",
    "depth_to_base_surf",
    "cond_surf",
    "det_elev",
    "geod_shearrate",
)
SIGMAS: tuple[float, ...] = (1.2, 3.0)
WEIGHT_FLOOR: float = 0.70  # weights ramp linearly from the 70th percentile to 1
MIN_TOTAL_WEIGHT: float = 2.0  # amendment A1: >= two fully-weighted layers
N_PERM: int = 19
SHIFT_MIN_PX: int = 40
SHIFT_MAX_PX: int = 400
NULL_SEED: int = 20261026
N_ANGLE_BINS: int = 256

# cos/sin tables for the uint8 index of the doubled angle 2*theta.
_INDEX = np.arange(N_ANGLE_BINS, dtype=np.float32) * (2.0 * np.pi / np.float32(N_ANGLE_BINS))
TAB_COS = np.cos(_INDEX).astype(np.float32)
TAB_SIN = np.sin(_INDEX).astype(np.float32)


def _smoothed(field: np.ndarray, valid: np.ndarray, sigma: float) -> np.ndarray:
    """Gaussian smoothing with normalised convolution over the valid support."""
    f0 = np.where(valid, field, 0.0).astype(np.float32, copy=False)
    num = gaussian_filter(f0, sigma, mode="nearest")
    den = gaussian_filter(valid.astype(np.float32), sigma, mode="nearest")
    out = np.full(field.shape, np.nan, dtype=np.float32)
    ok = den > 1e-6
    out[ok] = num[ok] / den[ok]
    return out


def _percentile_rank(values: np.ndarray) -> np.ndarray:
    """Average ranks in [0, 1] over the finite sample; NaN elsewhere."""
    out = np.full(values.shape, np.nan, dtype=np.float32)
    finite = np.isfinite(values)
    if not finite.any():
        return out
    v = values[finite]
    n = len(v)
    order = np.argsort(v, kind="stable")
    sv = v[order]
    ranks = np.arange(1, n + 1, dtype=np.float64)
    # average ranks over exact ties
    change = np.flatnonzero(np.r_[True, sv[1:] != sv[:-1], True])
    for start, stop in zip(change[:-1], change[1:]):
        if stop - start > 1:
            ranks[start:stop] = 0.5 * (start + 1 + stop)
    out_flat = np.empty(n, dtype=np.float64)
    out_flat[order] = ranks
    out[finite] = ((out_flat - 1.0) / max(n - 1, 1)).astype(np.float32)
    return out


def edge_fields(field: np.ndarray, valid: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Multi-scale edge magnitude and uint8 doubled-angle orientation index.

    The returned ``index`` encodes the doubled angle ``2*theta`` of the
    across-strike gradient on ``[0, 360)`` deg into ``0..255`` so that a
    weighted mean resultant length is a well-defined orientation statistic
    (``theta`` and ``theta + 180 deg`` are the same strike).
    """
    field = np.asarray(field, dtype=np.float32)
    valid = np.asarray(valid, bool)
    if field.shape != valid.shape or field.ndim != 2:
        raise ValueError("Aligned 2D field and valid mask required")
    best = np.full(field.shape, -np.inf, dtype=np.float32)
    best_gy = np.zeros(field.shape, dtype=np.float32)
    best_gx = np.zeros(field.shape, dtype=np.float32)
    for sigma in SIGMAS:
        s = _smoothed(field, valid, sigma)
        gy, gx = np.gradient(s)
        mag = np.hypot(gy, gx).astype(np.float32)
        take = mag > best
        best = np.where(take, mag, best)
        best_gy = np.where(take, gy, best_gy)
        best_gx = np.where(take, gx, best_gx)
    mag = np.where(np.isfinite(best), best, np.nan).astype(np.float32)
    with np.errstate(invalid="ignore"):
        theta = np.arctan2(best_gy, best_gx).astype(np.float32)
    idx = np.round((theta % np.pi) * (N_ANGLE_BINS / (2.0 * np.pi))).astype(np.int64)
    idx = (idx % N_ANGLE_BINS).astype(np.uint8)
    idx[~np.isfinite(mag)] = 0
    return mag, idx


def _random_fill(idx: np.ndarray, inside: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Replace the undefined orientation outside ``inside`` by a seeded sample.

    Toroidal wrapping must never inject one fixed orientation into the null.
    """
    pool = idx[inside]
    if pool.size == 0:
        return idx
    out = idx.copy()
    n_out = int((~inside).sum())
    if n_out:
        out[~inside] = rng.choice(pool, size=n_out, replace=True)
    return out


def build_xfront(
    layers: dict[str, np.ndarray],
    footprint: np.ndarray,
    *,
    n_perm: int = N_PERM,
    seed: int = NULL_SEED,
) -> dict[str, Any]:
    """Build the frozen H24-XFRONT surface.

    ``layers`` maps modality name -> full-grid float32 array with NaN where
    undefined. Returns the score plus every diagnostic component. Layers'
    orientations are translated (never their weights) to build the null, and the
    null is evaluated on the flat eligible-pixel index set only.
    """
    fp = np.asarray(footprint, bool)
    h, w = fp.shape
    n_mod = len(MODALITIES)
    weights = np.zeros((n_mod, h, w), dtype=np.uint8)
    index = np.zeros((n_mod, h, w), dtype=np.uint8)
    magnitudes: dict[str, np.ndarray] = {}
    for i, name in enumerate(MODALITIES):
        if name not in layers:
            raise ValueError(f"Missing preregistered modality: {name}")
        field = np.asarray(layers[name], dtype=np.float32)
        if field.shape != fp.shape:
            raise ValueError(f"Modality {name} grid mismatch")
        valid = fp & np.isfinite(field)
        mag, idx = edge_fields(field, valid)
        magnitudes[name] = mag
        pct = _percentile_rank(np.where(fp, mag, np.nan))
        wu = np.clip((pct - WEIGHT_FLOOR) / (1.0 - WEIGHT_FLOOR), 0.0, 1.0)
        wu = np.where(np.isfinite(wu), wu, 0.0)
        weights[i] = np.round(wu * 255.0).astype(np.uint8)
        rng = np.random.default_rng(seed + i)
        index[i] = _random_fill(idx, fp, rng)
        del mag, idx, pct, wu

    total_w_u8 = weights.sum(axis=0, dtype=np.uint16)
    c_norm = (total_w_u8.astype(np.float32) / 255.0) / float(n_mod)
    threshold = int(round(MIN_TOTAL_WEIGHT * 255.0))
    eligible = fp & (total_w_u8 >= threshold)
    sel = np.flatnonzero(eligible.ravel())
    score = np.zeros((h, w), dtype=np.float32)
    r_obs_full = np.zeros((h, w), dtype=np.float32)
    r_null_full = np.zeros((h, w), dtype=np.float32)
    excess_full = np.zeros((h, w), dtype=np.float32)

    if sel.size:
        y_sel = (sel // w).astype(np.int64)
        x_sel = (sel % w).astype(np.int64)
        wflat = [weights[i].ravel()[sel].astype(np.float32) / 255.0 for i in range(n_mod)]
        iflat = [index[i].ravel() for i in range(n_mod)]
        total_sel = total_w_u8.ravel()[sel].astype(np.float32) / 255.0

        ac = np.zeros(sel.size, dtype=np.float32)
        asum = np.zeros(sel.size, dtype=np.float32)
        for i in range(n_mod):
            ac += wflat[i] * TAB_COS[iflat[i][sel]]
            asum += wflat[i] * TAB_SIN[iflat[i][sel]]
        r_obs = np.sqrt(ac * ac + asum * asum) / np.maximum(total_sel, 1e-6)

        rng = np.random.default_rng(seed)
        r_null_sum = np.zeros(sel.size, dtype=np.float32)
        for _ in range(int(n_perm)):
            ac_p = np.zeros(sel.size, dtype=np.float32)
            as_p = np.zeros(sel.size, dtype=np.float32)
            for i in range(n_mod):
                dy = int(rng.integers(SHIFT_MIN_PX, SHIFT_MAX_PX + 1)) * (
                    1 if rng.random() < 0.5 else -1
                )
                dx = int(rng.integers(SHIFT_MIN_PX, SHIFT_MAX_PX + 1)) * (
                    1 if rng.random() < 0.5 else -1
                )
                yy = (y_sel - dy) % h
                xx = (x_sel - dx) % w
                pos = yy * w + xx
                shifted = iflat[i][pos]
                ac_p += wflat[i] * TAB_COS[shifted]
                as_p += wflat[i] * TAB_SIN[shifted]
            r_null_sum += np.sqrt(ac_p * ac_p + as_p * as_p) / np.maximum(total_sel, 1e-6)
        r_null_mean = r_null_sum / float(n_perm)

        excess = np.clip((r_obs - r_null_mean) / (1.0 - r_null_mean + 1e-6), 0.0, 1.0)
        c_sel = c_norm.ravel()[sel]
        score.ravel()[sel] = (c_sel * excess).astype(np.float32)
        r_obs_full.ravel()[sel] = r_obs
        r_null_full.ravel()[sel] = r_null_mean
        excess_full.ravel()[sel] = excess

    return {
        "score": score,
        "corroboration": c_norm.astype(np.float32),
        "coherence": r_obs_full,
        "null_coherence": r_null_full,
        "excess_coherence": excess_full,
        "total_weight": (total_w_u8.astype(np.float32) / 255.0),
        "magnitudes": magnitudes,
        "modalities": list(MODALITIES),
        "n_eligible": int(sel.size),
        "n_perm": int(n_perm),
        "seed": int(seed),
        "min_total_weight": float(MIN_TOTAL_WEIGHT),
    }
