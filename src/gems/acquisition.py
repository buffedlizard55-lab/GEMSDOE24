"""Derive GeoDAWN acquisition-block membership from the official report's Figure 3, then audit it.

Official facts used (USGS Data Series report, ScienceBase item 657e1d85d34e23d3533209f7):

* "the survey [was divided] into four separate acquisition blocks, each with an independent base of
  operations at the towns which became the name for each block" (Figure 3), with published line-km
  Winnemucca 62,530, Fallon 43,500, Hawthorne 21,400, Tonopah 21,600 (including Area 1); the report
  states a total of 149,030 km, which is also the sum of the four figures.
* The official extent polygon (``GeoDAWN_data_extent.zip``) is the yellow outline drawn in Figure 3.

Derivation (declared, label-free): fit an affine map from the extent polygon to the yellow outline by
chamfer matching, locate each coloured rectangle's edges as straight lines in the figure, and assign
every footprint pixel to a block. The result is **not official coordinates**. It is accepted for the
nuisance audit only if the line-km it implies reproduces the four published totals within the
tolerances below. These tolerances were fixed before the derivation was run.
"""

from __future__ import annotations

import numpy as np
from scipy.ndimage import distance_transform_edt, label
from scipy.optimize import minimize

BLOCK_NAMES = {1: "Winnemucca", 2: "Fallon", 3: "Hawthorne", 4: "Tonopah"}
OFFICIAL_LINE_KM = {1: 62_530.0, 2: 43_500.0, 3: 21_400.0, 4: 21_600.0}
OFFICIAL_TOTAL_KM = 149_030.0
TOLERANCE_PER_BLOCK = 0.08
TOLERANCE_TOTAL = 0.05


def densify(ring: np.ndarray, step: float = 2000.0) -> np.ndarray:
    ring = np.asarray(ring, float)
    closed = np.vstack([ring, ring[:1]]) if not np.allclose(ring[0], ring[-1]) else ring
    out = []
    for a, b in zip(closed[:-1], closed[1:]):
        n = max(int(np.hypot(*(b - a)) // step), 1)
        out.extend(a + (b - a) * t for t in np.linspace(0.0, 1.0, n, endpoint=False))
    return np.array(out)


class Georef:
    """u = a * (lon * cos(lat0)) + c ;  v = b * lat + d   (no rotation)."""

    def __init__(self, a: float, b: float, c: float, d: float, lat0_rad: float):
        self.a, self.b, self.c, self.d, self.lat0 = a, b, c, d, lat0_rad

    def forward(self, lon, lat):
        return self.a * (np.asarray(lon) * np.cos(self.lat0)) + self.c, self.b * np.asarray(
            lat
        ) + self.d

    def inverse(self, u, v):
        return (np.asarray(u) - self.c) / (self.a * np.cos(self.lat0)), (
            np.asarray(v) - self.d
        ) / self.b

    def as_dict(self) -> dict:
        return {"a": self.a, "b": self.b, "c": self.c, "d": self.d, "lat0_rad": self.lat0}


def fit_georef(lon, lat, yellow_mask: np.ndarray) -> tuple[Georef, float]:
    """Chamfer-match the projected extent ring to the yellow outline mask."""
    H, W = yellow_mask.shape
    dt = distance_transform_edt(~yellow_mask)
    lat0 = float(np.radians(np.mean(lat)))
    X, Y = np.asarray(lon) * np.cos(lat0), np.asarray(lat)
    ys, xs = np.nonzero(yellow_mask)
    a0 = (xs.max() - xs.min()) / (X.max() - X.min())
    b0 = -(ys.max() - ys.min()) / (Y.max() - Y.min())
    base = [a0, b0, xs.min() - a0 * X.min(), ys.min() - b0 * Y.max()]

    def loss(p):
        u, v = p[0] * X + p[2], p[1] * Y + p[3]
        ok = (u >= 0) & (u < W - 1) & (v >= 0) & (v < H - 1)
        if ok.sum() < 0.9 * len(u):
            return 1e3
        return float(
            np.mean(np.minimum(dt[np.round(v[ok]).astype(int), np.round(u[ok]).astype(int)], 40.0))
        )

    best = None
    for s in (0.9, 0.95, 1.0, 1.05, 1.1):
        for dx in (-60, 0, 60):
            for dy in (-60, 0, 60):
                p0 = [base[0] * s, base[1] * s, base[2] + dx, base[3] + dy]
                r = minimize(
                    loss,
                    p0,
                    method="Nelder-Mead",
                    options={"xatol": 1e-3, "fatol": 1e-4, "maxiter": 4000},
                )
                if best is None or r.fun < best.fun:
                    best = r
    a, b, c, d = best.x
    return Georef(float(a), float(b), float(c), float(d), lat0), float(best.fun)


def fit_line(points_xy: np.ndarray, vertical: bool, iterations: int = 3) -> tuple[float, float]:
    """Robust least-squares line. vertical: x = m*y + k ; else y = m*x + k."""
    p = np.asarray(points_xy, float)
    if len(p) < 10:
        raise ValueError("too few edge pixels for a line fit")
    t, s = (p[:, 1], p[:, 0]) if vertical else (p[:, 0], p[:, 1])
    keep = np.ones(len(p), bool)
    m = k = 0.0
    for _ in range(iterations):
        m, k = np.polyfit(t[keep], s[keep], 1)
        res = np.abs(s - (m * t + k))
        thresh = max(2.0, 2.5 * float(np.median(res[keep])))
        keep = res <= thresh
        if keep.sum() < 10:
            break
    return float(m), float(k)


def intersect(vert: tuple[float, float], horiz: tuple[float, float]) -> tuple[float, float]:
    """Intersection of x = mv*y + kv with y = mh*x + kh."""
    mv, kv = vert
    mh, kh = horiz
    y = (mh * kv + kh) / (1.0 - mh * mv)
    return mv * y + kv, y


def rect_corners(left, right, top, bottom):
    return [
        intersect(left, top),
        intersect(right, top),
        intersect(right, bottom),
        intersect(left, bottom),
    ]


def edge_pixels(mask, *, vertical: bool, expected: float, span: tuple[int, int], width: int = 9):
    """Mask pixels within ``width`` of an expected edge coordinate, over [span) of the other axis."""
    lo, hi = span
    if vertical:
        sub = mask[lo:hi, max(int(expected) - width, 0) : int(expected) + width + 1]
        ys, xs = np.nonzero(sub)
        return np.c_[xs + max(int(expected) - width, 0), ys + lo]
    sub = mask[max(int(expected) - width, 0) : int(expected) + width + 1, lo:hi]
    ys, xs = np.nonzero(sub)
    return np.c_[xs + lo, ys + max(int(expected) - width, 0)]


def block_line_km(
    sample_xy_by_line: list[tuple[float, np.ndarray]], block_raster, transform_inv
) -> dict:
    """Apportion each line's length by the share of its sampled vertices in each block."""
    km = {b: 0.0 for b in BLOCK_NAMES}
    for length_km, xy in sample_xy_by_line:
        if len(xy) == 0:
            continue
        cols, rows = transform_inv(xy[:, 0], xy[:, 1])
        ok = (
            (rows >= 0)
            & (rows < block_raster.shape[0])
            & (cols >= 0)
            & (cols < block_raster.shape[1])
        )
        if not ok.any():
            continue
        ids = block_raster[rows[ok].astype(int), cols[ok].astype(int)]
        for b in km:
            km[b] += length_km * float(np.mean(ids == b))
    return km


def audit_line_km(
    derived: dict, *, total_tolerance=TOLERANCE_TOTAL, block_tolerance=TOLERANCE_PER_BLOCK
):
    rows, ok = {}, True
    for b, official in OFFICIAL_LINE_KM.items():
        rel = derived[b] / official - 1.0
        rows[BLOCK_NAMES[b]] = {
            "official_km": official,
            "derived_km": float(derived[b]),
            "relative_difference": float(rel),
            "within_tolerance": bool(abs(rel) <= block_tolerance),
        }
        ok &= abs(rel) <= block_tolerance
    total = float(sum(derived.values()))
    rel_total = total / OFFICIAL_TOTAL_KM - 1.0
    ok &= abs(rel_total) <= total_tolerance
    return {
        "blocks": rows,
        "total": {
            "official_km": OFFICIAL_TOTAL_KM,
            "derived_km": total,
            "relative_difference": float(rel_total),
            "within_tolerance": bool(abs(rel_total) <= total_tolerance),
        },
        "tolerance_per_block": block_tolerance,
        "tolerance_total": total_tolerance,
        "passed": bool(ok),
    }


def fill_unassigned(block: np.ndarray, footprint: np.ndarray) -> tuple[np.ndarray, int]:
    """Assign footprint pixels left at 0 to the nearest assigned block; return count filled."""
    out = block.copy()
    missing = footprint & (out == 0)
    n = int(missing.sum())
    if n and (out > 0).any():
        idx = distance_transform_edt(out == 0, return_distances=False, return_indices=True)
        out[missing] = out[tuple(i[missing] for i in idx)]
    return out, n


def connected_components_per_block(block: np.ndarray) -> dict[int, int]:
    return {b: int(label(block == b, structure=np.ones((3, 3), int))[1]) for b in BLOCK_NAMES}
