"""OJ1: label-free circular dispersion of locally coherent terrain scarps.

Quantized, 100 m cell maxima are proxies, not resolved intersecting fault traces.
The deliberately fixed operator is specified in knowledge/17_preregistered_OJ1*.
"""

from __future__ import annotations

import numpy as np
from scipy.ndimage import uniform_filter

from .aspc import decode

BANDS = {
    "step_max": (3, 1.0, "sqrt"),
    "lapneg_max": (4, 0.05, "sqrt"),
    "lappos_max": (5, 0.05, "sqrt"),
    "coh100": (10, 1.0, "linear"),
    "strike": (11, 180.0, "linear"),
    "valid": (12, 1.0, "linear"),
}


def factors(encoded, footprint):
    """Return fixed surface, all raw/transformed canaries, and support mask."""
    fp = np.asarray(footprint)
    if fp.ndim != 2 or fp.dtype != bool or not fp.any():
        raise ValueError("Nonempty 2D boolean footprint required")
    decoded = {}
    support = fp.copy()
    for name, (_, maximum, kind) in BANDS.items():
        q = np.asarray(encoded[name])
        if q.shape != fp.shape or q.dtype != np.uint8:
            raise ValueError(f"Aligned uint8 source required: {name}")
        support &= q > 0
        decoded[name] = decode(q, maximum, kind).astype(np.float32)
    support &= decoded["valid"] > 0.5
    # Missing strike has zero *weight*: it must not act like a northward scarp.
    weight = np.where(support, decoded["coh100"], 0).astype(np.float32)
    angle = 2 * np.deg2rad(decoded["strike"])
    c = (weight * np.cos(angle)).astype(np.float32)
    s = (weight * np.sin(angle)).astype(np.float32)
    mean = lambda a: uniform_filter(a, size=5, mode="constant", cval=0)  # noqa: E731
    mean_weight = mean(weight)
    mean_c, mean_s = mean(c), mean(s)
    resultant = np.divide(
        np.hypot(mean_c, mean_s),
        mean_weight,
        out=np.ones_like(weight),
        where=mean_weight > 0,
    )
    neighborhood_support = mean(support.astype(np.float32))
    dispersion = np.where(
        support & (neighborhood_support >= 0.5), np.clip(1 - resultant, 0, 1), 0
    ).astype(np.float32)
    n, p = decoded["lapneg_max"], decoded["lappos_max"]
    balance = np.clip(2 * np.sqrt(n * p) / (n + p + 1e-8), 0, 1)
    root_step = np.sqrt(decoded["step_max"])
    surface = np.where(support, dispersion * weight * balance * root_step, 0).astype(np.float32)
    # Raw sources, their decodings, and every transform entering the operator.
    canaries = {f"raw_{name}": np.where(fp, encoded[name], 0) for name in BANDS}
    canaries.update({f"decoded_{name}": value for name, value in decoded.items()})
    canaries.update(
        support=support.astype(np.float32),
        weighted_cos2=c,
        weighted_sin2=s,
        mean_weight=mean_weight,
        mean_cos2=mean_c,
        mean_sin2=mean_s,
        neighborhood_support=neighborhood_support,
        resultant=resultant,
        dispersion=dispersion,
        curvature_balance=balance,
        root_step=root_step,
        candidate=surface,
    )
    return surface, canaries, support
