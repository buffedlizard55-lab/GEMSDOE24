"""Full-footprint registry comparisons; no sampled uniqueness certificates."""

from __future__ import annotations

import numpy as np
from scipy.spatial import cKDTree
from scipy.stats import rankdata


def correlation(a, b):
    """Spearman rho with explicit undefined status for constant arrays."""
    a, b = np.asarray(a), np.asarray(b)
    if a.shape != b.shape or a.ndim != 1 or not len(a):
        raise ValueError("Nonempty aligned vectors required")
    if not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError("Finite vectors required")
    if np.ptp(a) == 0 or np.ptp(b) == 0:
        return None
    return rank_correlation(rankdata(a), b)


def rank_correlation(ranks_a, b):
    """Spearman given precomputed average ranks for the first vector."""
    ra = np.asarray(ranks_a, dtype=np.float64)
    b = np.asarray(b)
    if ra.shape != b.shape or not np.isfinite(ra).all() or not np.isfinite(b).all():
        raise ValueError("Aligned finite vectors required")
    if np.ptp(b) == 0 or np.ptp(ra) == 0:
        return None
    # Binary references are overwhelmingly common; a binary vector is affine
    # to its average ranks, so avoid ranking millions of tied values again.
    if np.isin(b, [0, 1]).all():
        rb = b.astype(np.float64)
    else:
        rb = rankdata(b)
    da, db = ra - ra.mean(), rb - rb.mean()
    return float(np.dot(da, db) / np.sqrt(np.dot(da, da) * np.dot(db, db)))


def dot_overlap(candidate, reference, radius_px=3.0):
    """Directional inclusive-radius coverage, not a symmetric similarity score."""
    c, r = np.asarray(candidate, bool), np.asarray(reference, bool)
    if c.shape != r.shape or c.ndim != 2 or radius_px < 0:
        raise ValueError("Aligned masks and nonnegative radius required")
    cp, rp = np.argwhere(c), np.argwhere(r)
    forward = None if not len(cp) else 0.0
    reverse = None if not len(rp) else 0.0
    if len(cp) and len(rp):
        forward = float(np.mean(cKDTree(rp).query(cp)[0] <= radius_px))
        reverse = float(np.mean(cKDTree(cp).query(rp)[0] <= radius_px))
    return {
        "candidate_within_3px_of_reference": forward,
        "reference_within_3px_of_candidate": reverse,
        "candidate_dots": len(cp),
        "reference_dots": len(rp),
    }


def is_duplicate(rho, overlap=None):
    return bool((rho is not None and rho > 0.90) or (overlap is not None and overlap > 0.70))
