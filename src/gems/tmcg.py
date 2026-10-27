"""H24-TMCG: topographic–magnetic cross-gradient for structurally decoupled faults.

Physical operator (Gallardo & Meju 2003-style structural coupling, inverted):
    |∇z × ∇rtp| = |∂z/∂x · ∂rtp/∂y − ∂z/∂y · ∂rtp/∂x|

High values mean surface topography and reduced-to-pole magnetics are *not*
aligned. Catalogue mapping is scarp- and spring-driven; a buried or young
strand that does not yet control the drainage network can still warp RTP.
This is distinct from EUL1's gravity–magnetic cross-gradient inside a 52-ch
HGB, and from PTAR (tilt × flat-basin gate) / GSD (strain × gravity saddle).
"""

from __future__ import annotations

import numpy as np
from scipy.ndimage import gaussian_filter, sobel


def cross_gradient(z: np.ndarray, mag: np.ndarray, support: np.ndarray) -> np.ndarray:
    z = np.where(support, np.nan_to_num(z, nan=0.0), 0.0).astype(np.float32)
    mag = np.where(support, np.nan_to_num(mag, nan=0.0), 0.0).astype(np.float32)
    zs = gaussian_filter(z, 1.0)
    ms = gaussian_filter(mag, 1.0)
    zx, zy = sobel(zs, axis=1), sobel(zs, axis=0)
    mx, my = sobel(ms, axis=1), sobel(ms, axis=0)
    cg = np.abs(zx * my - zy * mx).astype(np.float32)
    cg[~support] = 0.0
    return cg


def robust01(x: np.ndarray, support: np.ndarray) -> np.ndarray:
    v = x[support]
    if v.size == 0:
        return np.zeros_like(x, dtype=np.float32)
    lo, hi = np.percentile(v, [5, 95])
    span = max(float(hi - lo), 1e-6)
    out = np.clip((x - lo) / span, 0.0, 1.0).astype(np.float32)
    out[~support] = 0.0
    return out
