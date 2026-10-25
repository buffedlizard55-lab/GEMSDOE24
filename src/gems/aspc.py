"""Preregistered, label-free antislope paired-curvature ranking (ASPC).

Inputs are team-derived, quantized USGS 3DEP descriptors, not fault probabilities.
Maxima co-occur within 100 m cells; they do not resolve a crest/toe doublet.
"""

from __future__ import annotations

import numpy as np

BANDS = {
    "upface_max": (1.0, "sqrt"),
    "downface_max": (1.0, "sqrt"),
    "cross_max": (1.0, "sqrt"),
    "step_max": (1.0, "sqrt"),
    "lapneg_max": (0.05, "sqrt"),
    "lappos_max": (0.05, "sqrt"),
    "coh100": (1.0, "linear"),
    "valid": (1.0, "linear"),
}


def decode(q: np.ndarray, maximum: float, encoding: str) -> np.ndarray:
    q = np.asarray(q)
    if maximum <= 0 or encoding not in {"sqrt", "linear"}:
        raise ValueError("Invalid quantization specification")
    if not np.isfinite(q).all() or np.any((q < 0) | (q > 255)):
        raise ValueError("Expected finite uint8-range quantized samples")
    t = np.maximum(q.astype(np.float32) - 1, 0) / 254
    return maximum * (t * t if encoding == "sqrt" else t)


def factors(bands: dict[str, np.ndarray], footprint: np.ndarray):
    """Return surface, univariate canaries, support and a fixed scarp control."""
    fp = np.asarray(footprint, bool)
    if set(bands) != set(BANDS) or any(np.shape(b) != fp.shape for b in bands.values()):
        raise ValueError("All eight named descriptor grids must match the footprint")
    x = {k: decode(bands[k], *spec) for k, spec in BANDS.items()}
    support = fp & (x["valid"] > 0)
    for b in bands.values():
        support &= b > 0
    total = x["upface_max"] + x["downface_max"] + x["cross_max"] + 0.001
    anti = x["upface_max"] / total
    veto = 1 - x["cross_max"] / total
    n, p = x["lapneg_max"], x["lappos_max"]
    balance = 2 * np.sqrt(n * p) / (n + p + 1e-6)
    step = x["step_max"] / (x["step_max"] + 0.05)
    coherence = np.sqrt(np.clip(x["coh100"], 0, 1))
    surface = np.where(support, anti * veto * balance * step * coherence, 0).astype(np.float32)
    canaries = {
        **x,
        "antislope_fraction": anti,
        "channel_veto": veto,
        "curvature_balance": balance,
        "step_response": step,
        "coherence_sqrt": coherence,
        "combined_surface": surface,
    }
    return surface, canaries, support, np.where(support, step, 0).astype(np.float32)


def place_dots(surface, eligible, budget: int, min_distance: float = 3.0):
    """Deterministic descending-rank Poisson placement, no wraparound or random fill."""
    surface, eligible = np.asarray(surface), np.asarray(eligible, bool)
    if surface.ndim != 2 or surface.shape != eligible.shape:
        raise ValueError("Aligned 2D surface and eligibility required")
    if budget < 1 or min_distance < 1 or not np.isfinite(surface[eligible]).all():
        raise ValueError("Positive budget, distance >=1 and finite eligible scores required")
    ids = np.flatnonzero(eligible & (surface > 0))
    order = ids[np.argsort(-surface.ravel()[ids], kind="stable")]
    h, w = surface.shape
    radius = int(np.ceil(min_distance))
    offsets = [
        (dy, dx)
        for dy in range(-radius, radius + 1)
        for dx in range(-radius, radius + 1)
        if dy * dy + dx * dx < min_distance**2
    ]
    blocked = np.zeros(surface.shape, bool)
    result = np.zeros_like(blocked)
    count = 0
    for idx in order:
        y, x = divmod(int(idx), w)
        if blocked[y, x]:
            continue
        result[y, x] = True
        count += 1
        for dy, dx in offsets:
            yy, xx = y + dy, x + dx
            if 0 <= yy < h and 0 <= xx < w:
                blocked[yy, xx] = True
        if count == budget:
            return result
    raise ValueError(f"Only {count} supported separated dots available, need {budget}")
