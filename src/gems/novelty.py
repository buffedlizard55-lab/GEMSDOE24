"""Registry-relative novelty checks. Unique bytes alone are not a unique method.

All registry values are comparison-only. Nothing here returns a modified score
or perturbs a candidate to evade the thresholds.
"""

from __future__ import annotations

import hashlib
from fractions import Fraction
from pathlib import Path

import numpy as np
import rasterio
from scipy.spatial import cKDTree
from scipy.stats import rankdata

from gems.uniqueness_budget import bounds as exact_budget_bounds


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


def classify_space_filling_control(
    footprint: np.ndarray,
    reference_dots: np.ndarray,
    *,
    radius_px: float = 3.0,
    coverage_threshold: float = 0.70,
    candidate_dot_count: int | None = None,
) -> dict[str, float | int | bool | None]:
    """Identify blind space-filling calibration controls by 3-px footprint coverage.

    If a reference raster's radius-``radius_px`` union covers ``M = N - U`` of ``N``
    footprint pixels (leaving ``U`` uncovered pixels), then by the Pigeonhole Principle
    EVERY subset ``C`` of size ``|C| = K`` inside the footprint has directional overlap
    ``>= max(0, 1 - U / K)``. When ``coverage >= coverage_threshold`` (0.70), directional
    overlap at radius ``radius_px`` cannot distinguish an unrelated detector from a copy,
    whereas full-footprint Spearman rank correlation (``|rho| <= 0.90``) remains informative.
    """
    fp_raw, ref_raw = np.asarray(footprint), np.asarray(reference_dots)
    if (
        fp_raw.ndim != 2
        or fp_raw.shape != ref_raw.shape
        or not np.isin(fp_raw, [0, 1]).all()
        or not np.isin(ref_raw, [0, 1]).all()
        or not fp_raw.any()
    ):
        raise ValueError("Aligned nonempty finite binary footprint and reference masks required")
    if (
        type(radius_px) not in (int, float)
        or not np.isfinite(radius_px)
        or radius_px < 0
        or type(coverage_threshold) not in (int, float)
        or not np.isfinite(coverage_threshold)
        or not 0 <= coverage_threshold <= 1
    ):
        raise ValueError("Finite nonnegative radius and [0,1] coverage threshold required")
    fp = fp_raw.astype(bool)
    ref = ref_raw.astype(bool) & fp
    if candidate_dot_count is not None and (
        type(candidate_dot_count) is not int or not 1 <= candidate_dot_count <= int(fp.sum())
    ):
        raise ValueError("Candidate count must be a positive integer no larger than the footprint")
    n_fp = int(fp.sum())
    if not ref.any():
        cov_px = 0
    else:
        from scipy.ndimage import distance_transform_edt

        cov_px = int((distance_transform_edt(~ref)[fp] <= float(radius_px)).sum())
    uncovered = n_fp - cov_px
    coverage = cov_px / n_fp
    pigeonhole_lb = (
        max(0, candidate_dot_count - uncovered) / candidate_dot_count
        if candidate_dot_count is not None
        else None
    )
    return {
        "is_space_filling_calibration_control": bool(coverage >= coverage_threshold),
        "footprint_3px_covered_pixels": cov_px,
        "footprint_3px_uncovered_pixels": uncovered,
        "footprint_3px_coverage": float(coverage),
        "coverage_threshold": float(coverage_threshold),
        "pigeonhole_min_overlap_for_candidate_size": pigeonhole_lb,
    }


def dot_budget_feasibility(
    footprint_pixels: int, uncovered_pixels: int, candidate_dot_count: int
) -> dict:
    """Necessary-only pre-training bound for the literal >70% overlap stop rule.

    For K distinct in-footprint dots and U pixels outside a reference's 3-px
    union, at least max(0, K-U) dots must overlap it. Compare integers so a
    bound of exactly 70% is NOT stopped by floating-point rounding. This says
    nothing about surface correlation, geological skill, or smaller budgets'
    actual overlap. Never use it to retune dots around a registry comparator.
    """
    if (
        any(type(v) is not int for v in (footprint_pixels, uncovered_pixels, candidate_dot_count))
        or footprint_pixels < 1
        or not 0 <= uncovered_pixels <= footprint_pixels
        or not 1 <= candidate_dot_count <= footprint_pixels
    ):
        raise ValueError(
            "Integer footprint, uncovered count and distinct in-footprint budget required"
        )
    exact = exact_budget_bounds(
        footprint_pixels - uncovered_pixels, uncovered_pixels, candidate_dot_count, Fraction(7, 10)
    )
    impossible = exact["necessarily_fails_literal_gate"]
    return {
        "candidate_dot_count": candidate_dot_count,
        "minimum_overlapping_dots": max(0, candidate_dot_count - uncovered_pixels),
        "minimum_overlap_fraction": exact["minimum_possible_directed_overlap"],
        "overlap_limit_fraction": exact["overlap_limit"],
        "strictly_exceeds_limit": impossible,
        "status": "STOP_IMPOSSIBLE_BUDGET" if impossible else "NOT_RULED_OUT_NOT_A_PASS",
        "maximum_budget_not_ruled_out_by_this_bound": exact[
            "maximum_dots_not_ruled_out_by_this_bound"
        ],
        "submission_authorized": False,
    }


def compare_registry(
    surface,
    footprint,
    entries,
    root,
    *,
    dots=None,
    sample_size=200000,
    separate_calibration_controls: bool = False,
    template_path: Path | str | None = None,
):
    """Test surface before placement, or final dots afterward, against every entry.

    Raw rank correlations cover the full footprint; kernel sensitivity uses a
    fixed reproducible uniform sample. Dot overlap is
    exact over ALL candidate dots, directional candidate -> registry, <=3 px.

    The top-level ``passed`` and each row's ``duplicate`` always enforce the
    literal all-entry rule. Separating controls adds an informational diagnostic
    only; it cannot exempt any comparator. Undefined rank correlations cannot
    certify a pass. Every reference must match the trusted template's grid and
    its registered footprint hash.
    """
    surface, raw_footprint = np.asarray(surface), np.asarray(footprint)
    if (
        raw_footprint.ndim != 2
        or not np.isfinite(raw_footprint).all()
        or not np.isin(raw_footprint, (0, 1)).all()
    ):
        raise ValueError("Footprint must be a finite two-dimensional binary mask")
    footprint = raw_footprint.astype(bool)
    if (
        surface.shape != footprint.shape
        or not footprint.any()
        or type(sample_size) is not int
        or sample_size < 1
        or not np.isfinite(surface[footprint]).all()
    ):
        raise ValueError("Finite footprint-aligned candidate surface required")
    template = (
        Path(template_path)
        if template_path is not None
        else Path(root) / "data/bridge/sample_submission.tif"
    )
    if not template.is_file():
        raise ValueError("A template is required to validate comparator CRS and transform")
    with rasterio.open(template) as ds:
        if (
            ds.count != 1
            or ds.crs is None
            or ds.shape != footprint.shape
            or not np.array_equal(np.isfinite(ds.read(1)), footprint)
        ):
            raise ValueError("Template grid or finite footprint does not match the candidate")
        template_crs, template_transform = ds.crs, ds.transform
    ids = np.flatnonzero(footprint)
    rng = np.random.default_rng(20261025)
    sample = rng.choice(ids, min(sample_size, len(ids)), replace=False)
    h, w = surface.shape
    sample_yx = np.column_stack(np.unravel_index(sample, (h, w)))
    values = surface.ravel()[sample]
    full_ranks = rankdata(surface.ravel()[ids])
    if dots is not None:
        dots = np.asarray(dots)
        if (
            dots.shape != surface.shape
            or not np.isfinite(dots).all()
            or not np.isin(dots, (0, 1)).all()
        ):
            raise ValueError("Candidate dots must be a finite binary mask")
        dots = dots.astype(bool)
        if np.any(dots & ~footprint) or not dots.any():
            raise ValueError("Nonempty candidate dots inside footprint required")
        dot_yx = np.argwhere(dots)
        candidate_kernel = np.maximum(1 - cKDTree(dot_yx).query(sample_yx)[0] / 3, 0)
    else:
        dot_yx, candidate_kernel = None, None
    rows = []
    n_cand_dots = len(dot_yx) if dot_yx is not None else None
    for row in entries:
        path = Path(root) / row["cache_path"]
        with rasterio.open(path) as ds:
            if (
                ds.count != 1
                or ds.shape != footprint.shape
                or ds.crs != template_crs
                or ds.transform != template_transform
            ):
                raise ValueError(f"Registry grid mismatch: {path}")
            a = ds.read(1)
        if not np.isfinite(a[footprint]).all() or np.any((a[footprint] < 0) | (a[footprint] > 1)):
            raise ValueError(f"Registry footprint has invalid values: {path}")
        content = hashlib.sha256(np.asarray(a[footprint], dtype="<f4").tobytes()).hexdigest()
        if content != row.get("footprint_sha256"):
            raise ValueError(f"Registry footprint checksum missing or mismatched: {path}")
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
        rank_dup = any(abs(x) > 0.90 for x in (raw_rank, kernel_rank) if x is not None)
        literal_duplicate = rank_dup or (overlap is not None and overlap > 0.70)
        correlation_defined = raw_rank is not None and kernel_rank is not None
        entry_dict = {
            "registry_id": row["id"],
            "file": row["file"],
            "footprint_sha256": content,
            "raw_spearman": raw_rank,
            "kernel_spearman": kernel_rank,
            "candidate_dot_overlap_within_3px": overlap,
            "duplicate": bool(literal_duplicate),
            "correlation_defined": correlation_defined,
        }
        if separate_calibration_controls:
            ctrl = classify_space_filling_control(
                footprint,
                registry_dots,
                radius_px=3.0,
                coverage_threshold=0.70,
                candidate_dot_count=n_cand_dots,
            )
            is_ctrl = bool(ctrl["is_space_filling_calibration_control"])
            competing_dup = rank_dup or (not is_ctrl and overlap is not None and overlap > 0.70)
            entry_dict.update(
                comparator_class=(
                    "space_filling_calibration_control" if is_ctrl else "competing_method"
                ),
                footprint_3px_coverage=ctrl["footprint_3px_coverage"],
                footprint_3px_uncovered_pixels=ctrl["footprint_3px_uncovered_pixels"],
                pigeonhole_min_overlap=ctrl["pigeonhole_min_overlap_for_candidate_size"],
                literal_duplicate=bool(literal_duplicate),
                competing_method_duplicate=bool(competing_dup),
            )
        rows.append(entry_dict)
    out = {
        "stage": "final_dots" if dots is not None else "surface_before_placement",
        "passed": bool(rows)
        and all(row["correlation_defined"] and not row["duplicate"] for row in rows),
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
    if separate_calibration_controls:
        comp_rows = [r for r in rows if r["comparator_class"] == "competing_method"]
        ctrl_rows = [
            r for r in rows if r["comparator_class"] == "space_filling_calibration_control"
        ]
        out.update(
            separate_calibration_controls=True,
            competing_method_rasters=len(comp_rows),
            calibration_control_rasters=len(ctrl_rows),
            competing_method_passed=bool(comp_rows)
            and all(r["correlation_defined"] and not r["competing_method_duplicate"] for r in rows),
            literal_unseparated_passed=out["passed"],
            max_competing_dot_overlap=max(
                (
                    r["candidate_dot_overlap_within_3px"]
                    for r in comp_rows
                    if r["candidate_dot_overlap_within_3px"] is not None
                ),
                default=None,
            ),
            calibration_control_summary=[
                {
                    "registry_id": r["registry_id"],
                    "file": r["file"],
                    "raw_spearman": r["raw_spearman"],
                    "kernel_spearman": r["kernel_spearman"],
                    "candidate_dot_overlap_within_3px": r["candidate_dot_overlap_within_3px"],
                    "footprint_3px_coverage": r["footprint_3px_coverage"],
                    "footprint_3px_uncovered_pixels": r["footprint_3px_uncovered_pixels"],
                    "pigeonhole_min_overlap": r["pigeonhole_min_overlap"],
                }
                for r in ctrl_rows
            ],
        )
    return out


SYNTHETIC_CALIBRATION_CONTROL_FILES = {
    "inputs/calibration/13gems_20261001_r13-lattice-s5_v2_nan-outside.tif": "synthetic_spacing5_calibration_lattice",
}


def classify_registry_entry(row: dict) -> str:
    """Classify only established controls, never infer empty content from a filename.

    The historical GEMSDOE9 PLACEHOLDER actually has 147,684 positive pixels in
    the pinned registry; its former all-zero classification was incorrect.
    This prospective correction does not rewrite frozen comparisons or exempt
    any comparator from the literal all-entry gate.
    """
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
    method_passed = bool(method_rows) and all(
        r["correlation_defined"] and not r["duplicate"] for r in method_rows
    )
    return {
        **base,
        "method_lane_passed": method_passed,
        "literal_all_entries_passed": base["passed"],
        "literal_duplicate_rows": [row for row in base["rows"] if row["duplicate"]],
        "competing_method_rasters_count": len(method_rows),
        "calibration_control_rasters_count": len(control_rows),
        "method_lane_max_abs_rank_correlation": method_max_rho,
        "method_lane_max_dot_overlap": method_max_overlap,
        "calibration_control_rows": control_rows,
    }
