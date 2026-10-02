"""Potential-field scale-space transforms for preregistered H24-3A.

The Fourier multiplier exp(-2*pi*h*|k|) is the exact flat-earth spectral
upward-continuation operator at height ``h``. Invalid cells are nearest-filled
only for convolution, then restored to NaN; callers must mask an edge guard.
"""

from __future__ import annotations

import math

import numpy as np
from scipy.fft import fftfreq, irfft2, rfft2, rfftfreq
from scipy.ndimage import distance_transform_edt, maximum_filter


def upward_continue(
    field: np.ndarray,
    height_m: float,
    *,
    cell_size_m: float = 100.0,
    padding_factor: float = 4.0,
) -> np.ndarray:
    """Upward-continue a 2-D potential field using its Fourier transfer kernel.

    Missing cells are filled from the nearest finite cell for the transform,
    but are returned as NaN. A caller should ignore an edge guard around all
    invalid cells because the continuation operator is non-local.
    """
    a = np.asarray(field, dtype=np.float32)
    if a.ndim != 2 or min(a.shape, default=0) < 2:
        raise ValueError("field must be a 2-D array at least 2 by 2")
    if not math.isfinite(height_m) or height_m < 0:
        raise ValueError("height_m must be finite and non-negative")
    if not math.isfinite(cell_size_m) or cell_size_m <= 0:
        raise ValueError("cell_size_m must be finite and positive")
    if not math.isfinite(padding_factor) or padding_factor < 0:
        raise ValueError("padding_factor must be finite and non-negative")

    valid = np.isfinite(a)
    if not valid.any():
        raise ValueError("field contains no finite cells")
    if height_m == 0:
        return a.copy()

    if valid.all():
        filled = a
    else:
        nearest = distance_transform_edt(~valid, return_distances=False, return_indices=True)
        filled = a[tuple(nearest)]

    pad = max(1, int(math.ceil(padding_factor * height_m / cell_size_m)))
    padded = np.pad(filled, ((pad, pad), (pad, pad)), mode="reflect")
    fy = fftfreq(padded.shape[0], d=cell_size_m)
    fx = rfftfreq(padded.shape[1], d=cell_size_m)
    wavenumber = np.hypot(fy[:, None], fx[None, :])
    transfer = np.exp(-2.0 * np.pi * height_m * wavenumber).astype(np.float32)
    spectrum = rfft2(padded, workers=1)
    continued = irfft2(spectrum * transfer, s=padded.shape, workers=1)
    result = np.asarray(continued[pad:-pad, pad:-pad], dtype=np.float32).copy()
    result[~valid] = np.nan
    return result


def contact_persistence(
    field: np.ndarray,
    *,
    heights_m: tuple[float, float, float] = (100.0, 200.0, 400.0),
    cell_size_m: float = 100.0,
    edge_guard_m: float | None = None,
) -> np.ndarray:
    """Return neighbourhood-tolerant, orientation-weighted edge persistence.

    Gradient magnitudes are calculated after upward continuation at three
    heights. The 3x3 neighbourhood maximum allows a one-cell ridge displacement;
    the minimum 200/400 m response relative to the 100 m response measures
    amplitude persistence. An unoriented-gradient agreement term penalizes
    contact directions that rotate between 100 and 400 m. The result is bounded
    to [0, 1] and is NaN wherever convolution support is unsafe.
    """
    if len(heights_m) != 3:
        raise ValueError("exactly three continuation heights are required")
    hs = tuple(float(h) for h in heights_m)
    if any(not math.isfinite(h) or h <= 0 for h in hs) or tuple(sorted(hs)) != hs:
        raise ValueError("heights_m must contain three increasing positive heights")
    if not math.isfinite(cell_size_m) or cell_size_m <= 0:
        raise ValueError("cell_size_m must be finite and positive")
    guard_m = 4.0 * hs[-1] if edge_guard_m is None else float(edge_guard_m)
    if not math.isfinite(guard_m) or guard_m < 0:
        raise ValueError("edge_guard_m must be finite and non-negative")

    a = np.asarray(field, dtype=np.float32)
    if a.ndim != 2:
        raise ValueError("field must be two-dimensional")
    valid = np.isfinite(a)
    if not valid.any():
        raise ValueError("field contains no finite cells")
    safe = valid & (distance_transform_edt(valid) * cell_size_m >= guard_m)

    magnitude_near: list[np.ndarray] = []
    orientation: list[np.ndarray] = []
    for height in hs:
        continued = upward_continue(a, height, cell_size_m=cell_size_m)
        gy, gx = np.gradient(continued, cell_size_m)
        magnitude = np.hypot(gx, gy).astype(np.float32)
        magnitude_near.append(maximum_filter(magnitude, size=3, mode="nearest").astype(np.float32))
        if height in (hs[0], hs[-1]):
            orientation.append(np.arctan2(gy, gx).astype(np.float32))
        del continued, gy, gx, magnitude

    denominator = magnitude_near[0]
    numerator = np.minimum(magnitude_near[1], magnitude_near[2])
    persistence = np.divide(
        numerator,
        denominator,
        out=np.zeros_like(numerator, dtype=np.float32),
        where=denominator > np.finfo(np.float32).eps,
    )
    np.clip(persistence, 0.0, 1.0, out=persistence)
    orientation_agreement = 0.5 * (1.0 + np.cos(2.0 * (orientation[0] - orientation[1])))
    result = (persistence * orientation_agreement).astype(np.float32)
    result[~safe] = np.nan
    return result
