"""Registry-relative novelty checks. Unique bytes alone are not a unique method.

All registry values are comparison-only. Nothing here returns a modified score
or perturbs a candidate to evade the thresholds.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import rasterio
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
    if (
        ra.shape != b.shape
        or ra.ndim != 1
        or not ra.size
        or not np.isfinite(ra).all()
        or not np.isfinite(b).all()
    ):
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
    if c.shape != r.shape or c.ndim != 2 or not np.isfinite(radius_px) or radius_px < 0:
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
        "radius_px": float(radius_px),
        "candidate_dots": len(cp),
        "reference_dots": len(rp),
    }


def is_duplicate(rho, overlap=None):
    if any(v is not None and not np.isfinite(v) for v in (rho, overlap)):
        raise ValueError("Duplicate checks need finite statistics or explicit None")
    return bool((rho is not None and abs(rho) > 0.90) or (overlap is not None and overlap > 0.70))


def compare_registry(surface, footprint, entries, root, *, dots=None, sample_size=200000):
    """Test surface before placement, or final dots afterward, against every entry.

    Raw rank correlations cover the full footprint; kernel sensitivity uses a
    fixed reproducible uniform sample. Dot overlap is
    exact over ALL candidate dots, directional candidate -> registry, <=3 px.
    """
    surface, footprint = np.asarray(surface), np.asarray(footprint, bool)
    if (
        surface.shape != footprint.shape
        or footprint.ndim != 2
        or not footprint.any()
        or sample_size < 1
        or not np.isfinite(surface[footprint]).all()
    ):
        raise ValueError("Finite footprint-aligned candidate surface required")
    ids = np.flatnonzero(footprint)
    rng = np.random.default_rng(20261025)
    sample = rng.choice(ids, min(sample_size, len(ids)), replace=False)
    h, w = surface.shape
    sample_yx = np.column_stack(np.unravel_index(sample, (h, w)))
    values = surface.ravel()[sample]
    full_ranks = rankdata(surface.ravel()[ids])
    if dots is not None:
        dots = np.asarray(dots, bool)
        if dots.shape != surface.shape or np.any(dots & ~footprint) or not dots.any():
            raise ValueError("Nonempty candidate dots inside footprint required")
        dot_yx = np.argwhere(dots)
        candidate_kernel = np.maximum(1 - cKDTree(dot_yx).query(sample_yx)[0] / 3, 0)
    else:
        dot_yx, candidate_kernel = None, None
    rows = []
    for row in entries:
        path = Path(root) / row["cache_path"]
        with rasterio.open(path) as ds:
            if ds.shape != footprint.shape:
                raise ValueError(f"Registry grid mismatch: {path}")
            a = ds.read(1)
        content = hashlib.sha256(np.asarray(a[footprint], dtype="<f4").tobytes()).hexdigest()
        if content != row["footprint_sha256"]:
            raise ValueError(f"Registry footprint checksum mismatch: {path}")
        registry_dots = footprint & np.isfinite(a) & (a > 0)
        registry_yx = np.argwhere(registry_dots)
        tree = cKDTree(registry_yx) if len(registry_yx) else None
        kernel = (
            np.maximum(1 - tree.query(sample_yx)[0] / 3, 0)
            if tree is not None
            else np.zeros(len(sample))
        )
        raw_rank = rank_correlation(full_ranks, a.ravel()[ids])
        kernel_rank = correlation(candidate_kernel if dots is not None else values, kernel)
        overlap = (
            float(np.mean(tree.query(dot_yx)[0] <= 3.0))
            if dots is not None and tree is not None
            else (0.0 if dots is not None else None)
        )
        duplicate = any(abs(x) > 0.90 for x in (raw_rank, kernel_rank) if x is not None) or (
            overlap is not None and overlap > 0.70
        )
        rows.append(
            {
                "registry_id": row["id"],
                "file": row["file"],
                "footprint_sha256": content,
                "raw_spearman": raw_rank,
                "kernel_spearman": kernel_rank,
                "candidate_dot_overlap_within_3px": overlap,
                "duplicate": bool(duplicate),
            }
        )
    return {
        "stage": "final_dots" if dots is not None else "surface_before_placement",
        "passed": bool(rows) and not any(row["duplicate"] for row in rows),
        "registry_unique_rasters": len(rows),
        "raw_rank_scope": "exact over all footprint pixels",
        "raw_rank_pixels": len(ids),
        "kernel_rank_sample_size": len(sample),
        "rank_sample_seed": 20261025,
        "rank_limit": 0.90,
        "overlap_limit": 0.70,
        "overlap_distance_px": 3,
        "overlap_scope": "ALL candidate dots, not a sample",
        "max_abs_rank_correlation": max(
            (
                abs(r[k])
                for r in rows
                for k in ("raw_spearman", "kernel_spearman")
                if r[k] is not None
            ),
            default=None,
        ),
        "max_dot_overlap": max(
            (
                r["candidate_dot_overlap_within_3px"]
                for r in rows
                if r["candidate_dot_overlap_within_3px"] is not None
            ),
            default=None,
        ),
        "rows": rows,
    }


SYNTHETIC_CALIBRATION_CONTROL_FILES = {
    "inputs/calibration/13gems_20261001_r13-lattice-s5_v2_nan-outside.tif": "synthetic_spacing5_calibration_lattice",
    "inputs/calibration/gemsdoe9-PLACEHOLDER-2314b599.tif": "all_zero_placeholder_control",
}


def classify_registry_entry(row: dict) -> str:
    """Distinguish synthetic calibration lattices/placeholders from competing method lanes."""
    file_path = str(row.get("file", ""))
    if file_path in SYNTHETIC_CALIBRATION_CONTROL_FILES:
        return SYNTHETIC_CALIBRATION_CONTROL_FILES[file_path]
    return "competing_method_lane"


def compare_prospective_registry(
    surface,
    footprint,
    entries,
    root,
    *,
    dots=None,
    sample_size=200000,
    extra_entries=(),
):
    """Prospective registry comparison that separates synthetic calibration lattices from method lanes.

    Every entry in ``entries`` and ``extra_entries`` is still evaluated and retained in ``rows``;
    no comparator is ever deleted. Both ``method_lane_passed`` (excluding synthetic uniform
    calibration lattices/placeholders) and ``literal_all_entries_passed`` (treating the spacing-5
    calibration lattice as a method lane) are reported explicitly.
    """
    combined = list(entries) + list(extra_entries)
    base = compare_registry(surface, footprint, combined, root, dots=dots, sample_size=sample_size)
    method_rows = []
    control_rows = []
    for entry, row in zip(combined, base["rows"]):
        role = classify_registry_entry(entry)
        row["entry_role"] = role
        if role == "competing_method_lane":
            method_rows.append(row)
        else:
            control_rows.append(row)
    method_max_rho = max(
        (
            abs(r[k])
            for r in method_rows
            for k in ("raw_spearman", "kernel_spearman")
            if r[k] is not None
        ),
        default=None,
    )
    method_max_overlap = max(
        (
            r["candidate_dot_overlap_within_3px"]
            for r in method_rows
            if r["candidate_dot_overlap_within_3px"] is not None
        ),
        default=None,
    )
    method_passed = bool(method_rows) and not any(r["duplicate"] for r in method_rows)
    return {
        **base,
        "method_lane_passed": method_passed,
        "literal_all_entries_passed": base["passed"],
        "competing_method_rasters_count": len(method_rows),
        "calibration_control_rasters_count": len(control_rows),
        "method_lane_max_abs_rank_correlation": method_max_rho,
        "method_lane_max_dot_overlap": method_max_overlap,
        "calibration_control_rows": control_rows,
    }
