"""H24-DKRN1: Topological D8 Drainage-Knickpoint Routing & Split-View 300 m DTI-Kernel Allocation.

Implements preregistration ``knowledge/27_preregistered_DKRN1_2026-10-26.md``:
1. Ten label-free physical channels (``DKRN1_NAMES``) solved via exact sparse
   unit-lower-triangular D8 topological flow routing ``(I - P^T) A = 1`` on ``det_elev``,
   1D channel-graph Flint's-law stream-power knickpoint jumps, 4-step thalweg dog-leg
   deflections, 900 m cross-wash knickpoint corridor coherence, drainage trunk asymmetry,
   footwall relief vs catchment residual, concealed sub-alluvial gravity ramps,
   Walker Lane transtensional strain partitioning, and pointwise LiDAR contour-over-bank
   discrimination (zero reuse of EUL1 Euler or PAIR1 graben-pair/dipole stencils).
2. Split-View Dual-Head Fold Estimator (strictly fit on ``train_mask`` & ``visible_mask``):
   - Head A (Gap-Native 47-channel 300 m DTI-Kernel Soft-Label Regressor): excludes the
     15 raw 1 m LiDAR amplitude/lineament channels and regresses exact triangular kernel
     credit ``y_K = max(0, 1 - d_vis / 3.0)`` across core, 0-300 m damage corridor,
     near-flank, and far-field rows, calibrated to fold kernel-credit expectation.
   - Head B (Full-Physics 62-channel Elkan Bayes-Posterior Core Classifier): applies
     selective non-topographic nuisance residualization, 3-tier relief-conditioned
     LiDAR-gap calibration, and exact Elkan (2001) prior-odds Bayes calibration so
     case-control sigmoid saturation does not inflate diffuse hillslopes over thin traces.
3. Three-Regime Net-Tversky Submodular Coverage Allocator (48% Core-Kernel Ridge,
   28% D8 Hydrologic Knickpoint & Deflected-Wash Corridors, 24% Concealed Sub-Alluvial
   & Walker-Lane Hydrothermal Step-Overs) with Minoux lazy-greedy upper-bound queue.
"""

from __future__ import annotations

import gc
import heapq
import json
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from scipy import sparse
from scipy.ndimage import distance_transform_edt, gaussian_filter
from scipy.sparse.linalg import spsolve_triangular
from scipy.special import expit, logit
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from threadpoolctl import threadpool_limits

from . import dprf1, geofeatures, gvc
from .metric import ALPHA, KERNEL_OFFSETS, RADIUS_PX
from .residualize import NuisanceResidualizer
from .validator import sha256_file

DKRN1_NAMES: tuple[str, ...] = (
    "d8_log_acc",
    "d8_stream_power_knick",
    "d8_knick_reach_max3",
    "d8_thalweg_turn",
    "d8_knick_corridor_900m",
    "d8_drainage_asymmetry_1km",
    "d8_incision_vs_catchment",
    "suballuvial_grav_ramp",
    "walker_transtension_index",
    "lidar_contour_over_bank",
)

RAW_LIDAR_AMPLITUDE_NAMES: frozenset[str] = frozenset(
    {
        "lidar_1",
        "lidar_2",
        "lidar_3",
        "lidar_4",
        "lidar_5",
        "lidar_6",
        "lidar_7",
        "lidar_8",
        "lidar_9",
        "lidar_10",
        "lidar_cos2strike",
        "lidar_sin2strike",
        "gvc_lidar_lineament_900m",
        "sahg_g_sat",
        "sahg_h_conduit",
    }
)

DKRN1_SELECTIVE_EXTRA_NAMES: tuple[str, ...] = (
    "suballuvial_grav_ramp",
    "walker_transtension_index",
)

HYDRO_GATE_NAMES: tuple[str, ...] = (
    "d8_knick_corridor_900m",
    "d8_stream_power_knick",
    "d8_knick_reach_max3",
    "d8_thalweg_turn",
    "d8_incision_vs_catchment",
)

CONCEALED_EXTRA_STEP_NAMES: tuple[str, ...] = (
    "suballuvial_grav_ramp",
    "walker_transtension_index",
)

# Sparse-regime Tversky marginal threshold at reference D_0 = 0.2778 (alpha = 0.2)
SPARSE_REF_DTI = 0.2778
SPARSE_TAU_STAR = (ALPHA * SPARSE_REF_DTI) / (1.0 - ALPHA * SPARSE_REF_DTI)
TAU_EFF_BASE = 0.25 * SPARSE_TAU_STAR


def _dequantize_lidar_sqrt(q: np.ndarray, valid_mask: np.ndarray, xmax: float) -> np.ndarray:
    """Dequantize uint8 sqrt-encoded 3DEP LiDAR band (`0=nodata; 1..255 -> [0, xmax]`)."""
    out = np.full(q.shape, np.nan, dtype=np.float32)
    m = valid_mask & (q > 0)
    if np.any(m):
        frac = np.clip((q[m].astype(np.float32) - 1.0) / 254.0, 0.0, 1.0)
        out[m] = np.float32(xmax) * (frac * frac)
    return out


def compute_d8_hydrologic_channels(
    det_elev: np.ndarray,
    det_elev_slope: np.ndarray,
    det_local_relief: np.ndarray,
    footprint: np.ndarray,
) -> dict[str, np.ndarray]:
    """Solve exact sparse unit-lower-triangular D8 routing and compute 7 label-free channels."""
    fp = np.asarray(footprint, dtype=bool)
    h, w = fp.shape
    dem_v = fp & geofeatures._valid(det_elev) & geofeatures._valid(det_elev_slope)
    if not np.any(dem_v):
        raise ValueError("No valid DEM pixels inside footprint")

    dem_fill = gvc._nearest_fill(det_elev, dem_v).astype(np.float64)
    yy, xx = np.indices((h, w), dtype=np.float64)
    # Mild pit-breaching blend + deterministic sub-millimetre coordinate tie-break
    z = (
        0.80 * dem_fill
        + 0.20 * gaussian_filter(dem_fill, sigma=2.5, mode="nearest")
        + 1e-7 * yy
        + 1e-10 * xx
    )
    del dem_fill, yy, xx

    dirs = (
        (-1, 0, 100.0),
        (-1, 1, 141.4213562373095),
        (0, 1, 100.0),
        (1, 1, 141.4213562373095),
        (1, 0, 100.0),
        (1, -1, 141.4213562373095),
        (0, -1, 100.0),
        (-1, -1, 141.4213562373095),
    )
    z_pad = np.pad(z, 1, mode="edge")
    fp_pad = np.pad(fp, 1, mode="constant", constant_values=False)
    best_slope = np.zeros((h, w), dtype=np.float64)
    best_dy = np.zeros((h, w), dtype=np.int8)
    best_dx = np.zeros((h, w), dtype=np.int8)

    for dy, dx, dist in dirs:
        nb_z = z_pad[1 + dy : 1 + dy + h, 1 + dx : 1 + dx + w]
        nb_fp = fp_pad[1 + dy : 1 + dy + h, 1 + dx : 1 + dx + w]
        slp = np.where(fp & nb_fp, (z - nb_z) / dist, -1.0)
        better = slp > best_slope
        best_slope = np.where(better, slp, best_slope)
        best_dy = np.where(better, dy, best_dy)
        best_dx = np.where(better, dx, best_dx)
    del z_pad, fp_pad

    fp_ids = np.flatnonzero(fp.ravel())
    n_fp = len(fp_ids)
    grid_to_fp = np.full(h * w, -1, dtype=np.int32)
    grid_to_fp[fp_ids] = np.arange(n_fp, dtype=np.int32)

    fy, fx = np.unravel_index(fp_ids, (h, w))
    s_fp_f64 = best_slope[fy, fx]
    has_rcv = s_fp_f64 > 0.0
    src_idx = np.flatnonzero(has_rcv)
    ry = fy[src_idx] + best_dy[fy, fx][src_idx]
    rx = fx[src_idx] + best_dx[fy, fx][src_idx]
    dst_idx = grid_to_fp[ry * w + rx]
    if np.any(dst_idx < 0):
        raise RuntimeError("D8 routed outside footprint")

    z_fp = z.ravel()[fp_ids]
    if not np.all(z_fp[src_idx] > z_fp[dst_idx]):
        raise RuntimeError("D8 receiver graph violated strict descent")
    del z, best_slope, best_dy, best_dx, grid_to_fp

    order = np.argsort(-z_fp, kind="mergesort")
    rank_of = np.empty(n_fp, dtype=np.int32)
    rank_of[order] = np.arange(n_fp, dtype=np.int32)
    col_perm = rank_of[src_idx]
    row_perm = rank_of[dst_idx]
    if not np.all(row_perm > col_perm):
        raise RuntimeError("Permuted D8 system is not strictly lower triangular")
    del z_fp, rank_of

    lhs = sparse.eye(n_fp, format="csr", dtype=np.float64) - sparse.csr_matrix(
        (np.ones(len(src_idx), dtype=np.float64), (row_perm, col_perm)),
        shape=(n_fp, n_fp),
    )
    acc_perm = spsolve_triangular(
        lhs, np.ones(n_fp, dtype=np.float64), lower=True, unit_diagonal=True
    )
    acc_fp = np.empty(n_fp, dtype=np.float32)
    acc_fp[order] = np.maximum(acc_perm, 1.0).astype(np.float32)
    del lhs, acc_perm, order, col_perm, row_perm

    rcv_fp = np.arange(n_fp, dtype=np.int32)
    rcv_fp[src_idx] = dst_idx
    in_acc_sum = np.bincount(dst_idx, weights=acc_fp[src_idx], minlength=n_fp).astype(np.float32)

    def dn_step(v: np.ndarray) -> np.ndarray:
        return v[rcv_fp]

    def up_step(v: np.ndarray) -> np.ndarray:
        num = np.bincount(
            dst_idx,
            weights=(acc_fp[src_idx] * v[src_idx]).astype(np.float64),
            minlength=n_fp,
        ).astype(np.float32)
        return np.where(in_acc_sum > 0.0, num / np.maximum(in_acc_sum, 1e-6), v)

    # 1. Log catchment area
    log_acc_fp = np.log1p(acc_fp).astype(np.float32)

    # 2. Flint's-law stream-power knickpoint jump along 1D D8 channel graph
    s_fp = np.maximum(s_fp_f64, 1e-5).astype(np.float32)
    ksn = s_fp * np.power(acc_fp, 0.45).astype(np.float32)
    d1 = dn_step(ksn)
    d2 = dn_step(d1)
    d3 = dn_step(d2)
    u1 = up_step(ksn)
    u2 = up_step(u1)
    u3 = up_step(u2)
    ksn_ref = 0.5 * ((d1 + d2 + d3) / 3.0 + (u1 + u2 + u3) / 3.0)
    knick_fp = (np.maximum(0.0, ksn - ksn_ref) * (acc_fp >= 4.0).astype(np.float32)).astype(
        np.float32
    )
    del s_fp_f64, s_fp, ksn, d1, d2, d3, u1, u2, u3, ksn_ref

    # 3. 3-step channel-reach max of knickpoint intensity
    kd1 = dn_step(knick_fp)
    kd2 = dn_step(kd1)
    ku1 = np.zeros(n_fp, dtype=np.float32)
    np.maximum.at(ku1, dst_idx, knick_fp[src_idx])
    ku2 = np.zeros(n_fp, dtype=np.float32)
    np.maximum.at(ku2, dst_idx, ku1[src_idx])
    knick_reach_fp = np.maximum.reduce([knick_fp, kd1, kd2, ku1, ku2]).astype(np.float32)
    del kd1, kd2, ku1, ku2

    # 4. 4-step downstream vs 4-step upstream thalweg dog-leg turn
    p4 = rcv_fp[rcv_fp[rcv_fp[rcv_fp]]]
    fy_f = fy.astype(np.float32)
    fx_f = fx.astype(np.float32)
    dy_dn = fy_f[p4] - fy_f
    dx_dn = fx_f[p4] - fx_f

    uy = up_step(up_step(up_step(up_step(fy_f))))
    ux = up_step(up_step(up_step(up_step(fx_f))))
    dy_up = fy_f - uy
    dx_up = fx_f - ux

    n_dn = np.hypot(dy_dn, dx_dn)
    n_up = np.hypot(dy_up, dx_up)
    valid_chord = (acc_fp >= 6.0) & (n_dn > 0.5) & (n_up > 0.5)
    cos_psi = np.ones(n_fp, dtype=np.float32)
    cos_psi[valid_chord] = np.clip(
        (dy_dn[valid_chord] * dy_up[valid_chord] + dx_dn[valid_chord] * dx_up[valid_chord])
        / (n_dn[valid_chord] * n_up[valid_chord]),
        -1.0,
        1.0,
    )
    turn_fp = np.where(valid_chord, (1.0 - cos_psi) * log_acc_fp, 0.0).astype(np.float32)
    del p4, fy_f, fx_f, dy_dn, dx_dn, uy, ux, dy_up, dx_up, n_dn, n_up, valid_chord, cos_psi

    def to_2d(vec_fp: np.ndarray) -> np.ndarray:
        arr = np.full((h, w), np.nan, dtype=np.float32)
        arr.ravel()[fp_ids] = vec_fp
        arr[~dem_v] = np.nan
        return arr

    log_acc_2d = to_2d(log_acc_fp)
    knick_2d = to_2d(knick_fp)
    knick_reach_2d = to_2d(knick_reach_fp)
    turn_2d = to_2d(turn_fp)
    del log_acc_fp, knick_fp, knick_reach_fp, turn_fp

    # 5. 900 m 8-azimuth colinear knickpoint + thalweg-turn corridor
    comb = np.maximum(
        gvc._robust_z(knick_2d, dem_v) + 0.50 * gvc._robust_z(turn_2d, dem_v),
        0.0,
    ).astype(np.float32)
    corridor_2d = gvc.oriented_lineament_response(comb, dem_v, half_len_px=4, flank_offset_px=3)
    del comb

    # 6. 1 km transverse drainage trunk asymmetry in low-to-moderate slope basins
    log_acc_fill = gvc._nearest_fill(log_acc_2d, dem_v)
    slope_z = gvc._robust_z(det_elev_slope, dem_v)
    asym_raw = (log_acc_fill - gaussian_filter(log_acc_fill, sigma=10.0, mode="nearest")) * expit(
        -slope_z
    ).astype(np.float32)
    asym_2d = np.where(dem_v, asym_raw, np.nan).astype(np.float32)
    del log_acc_fill, slope_z, asym_raw

    # 7. Footwall local relief residual above catchment-expected fluvial incision
    rel_v = dem_v & np.isfinite(det_local_relief)
    incis_raw = gvc._robust_z(det_local_relief, rel_v) - 0.50 * gvc._robust_z(log_acc_2d, rel_v)
    incis_2d = np.where(rel_v, incis_raw, np.nan).astype(np.float32)
    del incis_raw

    return {
        "d8_log_acc": log_acc_2d,
        "d8_stream_power_knick": knick_2d,
        "d8_knick_reach_max3": knick_reach_2d,
        "d8_thalweg_turn": turn_2d,
        "d8_knick_corridor_900m": corridor_2d,
        "d8_drainage_asymmetry_1km": asym_2d,
        "d8_incision_vs_catchment": incis_2d,
    }


def build_dkrn1_memmap(
    root: Path,
    base_mm: np.ndarray,
    base_names: list[str],
    footprint: np.ndarray,
    out_path: Path,
) -> tuple[np.ndarray, list[str]]:
    """Build or load the 10-channel H24-DKRN1 memmap on ``footprint`` (zero label access)."""
    fp = np.asarray(footprint, dtype=bool)
    fp_ids = np.flatnonzero(fp.ravel())
    n_fp = len(fp_ids)
    meta_path = out_path.with_suffix(".json")
    expected_bytes = n_fp * len(DKRN1_NAMES) * 4

    if out_path.exists() and meta_path.exists() and out_path.stat().st_size == expected_bytes:
        meta = json.loads(meta_path.read_text())
        if meta.get("names") == list(DKRN1_NAMES) and meta.get("n_fp") == n_fp:
            mm = np.memmap(out_path, dtype="float32", mode="r", shape=(n_fp, len(DKRN1_NAMES)))
            return mm, list(DKRN1_NAMES)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    mm = np.memmap(out_path, dtype="float32", mode="w+", shape=(n_fp, len(DKRN1_NAMES)))

    # Assert external CSVs never feed forbidden catalogue-distance columns
    for csv_rel in (
        "data/external/gdr_wellspring_in_footprint.csv",
        "data/external/gdr_volcanic_vents_in_footprint.csv",
    ):
        csv_p = root / csv_rel
        if csv_p.exists():
            hdr = csv_p.open("r", encoding="utf-8").readline().strip().split(",")
            used = [c for c in hdr if c not in gvc.FORBIDDEN_COLUMNS]
            assert "dist_known_fault_px" not in used

    train_tif = root / "data/training_features.tif"
    with rasterio.open(train_tif) as src:

        def read_band(bname: str) -> np.ndarray:
            idx = geofeatures.BAND_ORDER.index(bname) + 1
            a = src.read(idx).astype(np.float32)
            bad = (~geofeatures._valid(a)) | (~fp)
            a[bad] = np.nan
            return a

        det_elev = read_band("det_elev")
        det_elev_slope = read_band("det_elev_slope")
        iso_grav_slope = read_band("iso_grav_anom_slope")
        depth_base = read_band("depth_to_base_surf")
        geod_2ndinv = read_band("geod_2ndinv")
        geod_shear = read_band("geod_shearrate")
        geod_dil = read_band("geod_dilaterate")

    rel_2d = np.full(fp.shape, np.nan, dtype=np.float32)
    rel_2d.ravel()[fp_ids] = np.asarray(
        base_mm[:, base_names.index("det_local_relief")], dtype=np.float32
    )

    d8_ch = compute_d8_hydrologic_channels(det_elev, det_elev_slope, rel_2d, fp)
    del det_elev, det_elev_slope, rel_2d
    for j, nm in enumerate(DKRN1_NAMES[:7]):
        mm[:, j] = d8_ch[nm].ravel()[fp_ids]
    del d8_ch
    gc.collect()

    # 8. Concealed sub-alluvial gravity ramp (depth_to_base_surf centered on 500 m piedmont cover)
    sub_v = fp & np.isfinite(iso_grav_slope) & np.isfinite(depth_base)
    sub_ramp = np.where(
        sub_v,
        iso_grav_slope * np.exp(-(((depth_base - 500.0) / 550.0) ** 2)),
        np.nan,
    ).astype(np.float32)
    mm[:, 7] = sub_ramp.ravel()[fp_ids]
    del iso_grav_slope, depth_base, sub_v, sub_ramp

    # 9. Walker Lane transtensional shear-dilation partitioning
    geod_v = fp & np.isfinite(geod_2ndinv) & np.isfinite(geod_shear) & np.isfinite(geod_dil)
    dil_z = gvc._robust_z(geod_dil, geod_v)
    transt = np.where(
        geod_v,
        geod_shear * (0.5 + 0.5 * expit(dil_z)) / (np.maximum(geod_2ndinv, 0.0) + 1.0),
        np.nan,
    ).astype(np.float32)
    mm[:, 8] = transt.ravel()[fp_ids]
    del geod_2ndinv, geod_shear, geod_dil, geod_v, dil_z, transt

    # 10. Pointwise 1 m LiDAR contour-scarp vs incised-channel-bank discriminator
    lidar_tif = root / "data/external/lidar_scarp_features_u8.tif"
    lidar_meta = json.loads(lidar_tif.with_name("lidar_scarp_features.json").read_text())
    lbands: list[str] = list(lidar_meta["bands"])
    lquant: dict[str, Any] = dict(lidar_meta["quantisation"])
    with rasterio.open(lidar_tif) as dlid:
        valid_u8 = dlid.read(lbands.index("valid") + 1)
        lid_v = fp & (valid_u8 > 0)
        q_down = dlid.read(lbands.index("downface_max") + 1)
        q_up = dlid.read(lbands.index("upface_max") + 1)
        q_cross = dlid.read(lbands.index("cross_max") + 1)

    down = _dequantize_lidar_sqrt(q_down, lid_v, float(lquant["downface_max"][0]))
    up = _dequantize_lidar_sqrt(q_up, lid_v, float(lquant["upface_max"][0]))
    cross = _dequantize_lidar_sqrt(q_cross, lid_v, float(lquant["cross_max"][0]))
    both_v = lid_v & np.isfinite(down) & np.isfinite(up) & np.isfinite(cross)
    cob = np.full(fp.shape, np.nan, dtype=np.float32)
    num = down[both_v] + 1.25 * up[both_v] - cross[both_v]
    den = down[both_v] + 1.25 * up[both_v] + cross[both_v] + 0.02
    cob[both_v] = (num / den).astype(np.float32)
    mm[:, 9] = cob.ravel()[fp_ids]
    del valid_u8, lid_v, q_down, q_up, q_cross, down, up, cross, both_v, cob

    mm.flush()
    del mm
    gc.collect()

    meta_payload = {
        "names": list(DKRN1_NAMES),
        "n_fp": int(n_fp),
        "sha256": sha256_file(out_path),
        "inputs": {
            "data/training_features.tif": sha256_file(train_tif),
            "data/external/lidar_scarp_features_u8.tif": sha256_file(lidar_tif),
        },
        "forbidden_columns_excluded": sorted(gvc.FORBIDDEN_COLUMNS),
        "ambiguous_bands_excluded": ["tc", "ieq_n100a15", "deq_n100a15"],
    }
    meta_path.write_text(json.dumps(meta_payload, indent=2) + "\n")
    mm_ro = np.memmap(out_path, dtype="float32", mode="r", shape=(n_fp, len(DKRN1_NAMES)))
    return mm_ro, list(DKRN1_NAMES)


def sample_kernel_corridor_rows(
    train_mask: np.ndarray,
    visible_mask: np.ndarray,
    fp_ids: np.ndarray,
    *,
    max_core: int = 20_000,
    max_corridor: int = 25_000,
    max_near_neg: int = 25_000,
    max_far_neg: int = 30_000,
    seed: int = 20261026,
) -> tuple[np.ndarray, np.ndarray, float]:
    """Stratified 300 m triangular DTI-kernel soft-label sampler strictly on ``train_mask``."""
    rng = np.random.default_rng(seed)
    dist_vis = distance_transform_edt(~visible_mask)
    y_k_full = np.maximum(0.0, 1.0 - dist_vis / float(RADIUS_PX)).astype(np.float32)

    tr_fp = train_mask.ravel()[fp_ids]
    vis_fp = visible_mask.ravel()[fp_ids]
    d_fp = dist_vis.ravel()[fp_ids]
    yk_fp = y_k_full.ravel()[fp_ids]
    pop_mean_yk = float(np.mean(yk_fp[tr_fp]))

    def pick(mask_1d: np.ndarray, cap: int) -> np.ndarray:
        pool = np.flatnonzero(mask_1d)
        if len(pool) <= cap:
            return pool
        return np.sort(rng.choice(pool, size=cap, replace=False))

    s_core = pick(tr_fp & vis_fp, max_core)
    s_corr = pick(tr_fp & (~vis_fp) & (d_fp > 0.0) & (d_fp < float(RADIUS_PX)), max_corridor)
    s_near = pick(tr_fp & (~vis_fp) & (d_fp >= float(RADIUS_PX)) & (d_fp < 10.0), max_near_neg)
    s_far = pick(tr_fp & (~vis_fp) & (d_fp >= 10.0), max_far_neg)

    rows = np.sort(np.concatenate([s_core, s_corr, s_near, s_far]))
    y_target = yk_fp[rows].astype(np.float32)
    return rows, y_target, pop_mean_yk


class KernelCreditLogitCalibrator:
    """Partial nuisance ridge debiasing + fold-population kernel-credit prior calibration."""

    def __init__(self, alpha: float = 100.0):
        self.alpha = float(alpha)
        self._basis_helper = NuisanceResidualizer(alpha=alpha)
        self.nuis_coef_: np.ndarray | None = None
        self.nuis_offset_: float = 0.0
        self.prior_shift_: float = 0.0
        self.slope_med_: float = 0.0
        self.slope_iqr_: float = 1.0
        self.rel_med_: float = 0.0
        self.rel_iqr_: float = 1.0

    def _rscore(self, slope: np.ndarray, rel: np.ndarray) -> np.ndarray:
        s = np.where(np.isfinite(slope), slope, self.slope_med_)
        r = np.where(np.isfinite(rel), np.abs(rel), self.rel_med_)
        zs = np.clip((s - self.slope_med_) / self.slope_iqr_, -6.0, 6.0)
        zr = np.clip((r - self.rel_med_) / self.rel_iqr_, -6.0, 6.0)
        return (0.5 * zs + 0.5 * zr).astype(np.float32)

    def fit(
        self,
        pred_bg: np.ndarray,
        nuisance_bg: np.ndarray,
        slope_bg: np.ndarray,
        rel_bg: np.ndarray,
        *,
        sample_mean_yk: float,
        pop_mean_yk: float,
    ) -> KernelCreditLogitCalibrator:
        p = np.clip(np.asarray(pred_bg, dtype=np.float64), 1e-4, 1.0 - 1e-4)
        ell = logit(p).astype(np.float32)
        c = np.asarray(nuisance_bg, dtype=np.float32)

        s_obs = slope_bg[np.isfinite(slope_bg)]
        r_obs = np.abs(rel_bg[np.isfinite(rel_bg)])
        self.slope_med_ = float(np.median(s_obs)) if len(s_obs) else 0.0
        s_q25, s_q75 = np.percentile(s_obs, [25.0, 75.0]) if len(s_obs) else (0.0, 1.0)
        self.slope_iqr_ = max(float(s_q75 - s_q25), 1e-4)
        self.rel_med_ = float(np.median(r_obs)) if len(r_obs) else 0.0
        r_q25, r_q75 = np.percentile(r_obs, [25.0, 75.0]) if len(r_obs) else (0.0, 1.0)
        self.rel_iqr_ = max(float(r_q75 - r_q25), 1e-4)

        rscore = self._rscore(slope_bg, rel_bg)
        self._basis_helper.n_nuisance = c.shape[1]
        b_nuis = self._basis_helper._basis(c, fit=True)
        k_nuis = b_nuis.shape[1]
        design = np.column_stack([b_nuis, rscore, rscore * rscore]).astype(np.float32)
        reg = Ridge(alpha=self.alpha).fit(design, ell)
        self.nuis_coef_ = reg.coef_[:k_nuis].astype(np.float32)
        nuis_eff = b_nuis @ self.nuis_coef_
        self.nuis_offset_ = float(np.mean(nuis_eff))

        pi_pop = float(np.clip(pop_mean_yk, 1e-4, 1.0 - 1e-4))
        pi_smp = float(np.clip(sample_mean_yk, 1e-4, 1.0 - 1e-4))
        self.prior_shift_ = float(logit(pi_pop) - logit(pi_smp))
        return self

    def transform(
        self,
        pred: np.ndarray,
        nuisance: np.ndarray,
        slope: np.ndarray,
        rel: np.ndarray,
    ) -> np.ndarray:
        if self.nuis_coef_ is None:
            raise RuntimeError("Call fit before transform")
        p = np.clip(np.asarray(pred, dtype=np.float64), 1e-4, 1.0 - 1e-4)
        ell = logit(p).astype(np.float32)
        b_nuis = self._basis_helper._basis(np.asarray(nuisance, dtype=np.float32), fit=False)
        debiased = ell - ((b_nuis @ self.nuis_coef_) - self.nuis_offset_) + self.prior_shift_
        return np.clip(expit(debiased), 0.0, 1.0).astype(np.float32)


class ThreeRegimeGateScaler:
    """Train-only robust quantile scaler for Hydrologic (Stage 2) and Concealed (Stage 3) gates."""

    def __init__(self, col_indices: dict[str, int]):
        self.col_indices = dict(col_indices)
        self.stats_: dict[str, tuple[float, float]] = {}

    def fit(self, x_train_bg: np.ndarray) -> ThreeRegimeGateScaler:
        self.stats_.clear()
        for name, j in self.col_indices.items():
            v = x_train_bg[:, j]
            obs = v[np.isfinite(v)]
            if len(obs) >= 32:
                med = float(np.median(obs))
                q25, q75 = np.percentile(obs, [25.0, 75.0])
                iqr = max(float(q75 - q25), 1e-5)
            else:
                med, iqr = 0.0, 1.0
            self.stats_[name] = (med, iqr)
        return self

    def _sig(self, x: np.ndarray, name: str, scale: float = 0.85) -> np.ndarray:
        med, iqr = self.stats_[name]
        v = x[:, self.col_indices[name]]
        out = np.full(len(v), 0.5, dtype=np.float32)
        m = np.isfinite(v)
        if np.any(m):
            z = np.clip((v[m] - med) / iqr, -6.0, 6.0)
            out[m] = expit(scale * z).astype(np.float32)
        return out

    def score_hydro_multiplier(self, x: np.ndarray) -> np.ndarray:
        """Stage-2 multiplier emphasizing colinear D8 knickpoint/thalweg corridors & non-bank scarps."""
        corridor = self._sig(x, "d8_knick_corridor_900m", scale=0.95)
        knick = np.maximum(
            self._sig(x, "d8_stream_power_knick", scale=0.90),
            self._sig(x, "d8_knick_reach_max3", scale=0.85),
        )
        turn = self._sig(x, "d8_thalweg_turn", scale=0.85)
        incis = self._sig(x, "d8_incision_vs_catchment", scale=0.70)
        cob = self._sig(x, "lidar_contour_over_bank", scale=0.80)
        drain_core = 0.40 * corridor + 0.30 * knick + 0.20 * turn + 0.10 * incis
        # cob == 0.5 in LiDAR gaps (neutral), >0.5 on contour scarps, <0.5 on incised gully banks
        bank_guard = 0.70 + 0.60 * cob
        return np.clip(drain_core * bank_guard, 0.05, 1.35).astype(np.float32)

    def score_concealed_multiplier(self, x: np.ndarray) -> np.ndarray:
        """Stage-3 multiplier emphasizing concealed intrabasin hydrothermal & Walker-Lane conduits."""
        up = np.zeros(len(x), dtype=np.float32)
        for nm in dprf1.UPFLOW_CONDUIT_NAMES:
            up = np.maximum(up, self._sig(x, nm, scale=0.85))
        step_names = (*dprf1.SUBSURFACE_STEP_NAMES, *CONCEALED_EXTRA_STEP_NAMES)
        st = np.zeros(len(x), dtype=np.float32)
        for nm in step_names:
            st += self._sig(x, nm, scale=0.85)
        st /= float(len(step_names))
        low_slope = 1.0 - 0.55 * self._sig(x, dprf1.STEEP_SLOPE_NAME, scale=0.90)
        return np.clip((0.30 + 0.70 * up) * st * low_slope, 0.05, 1.0).astype(np.float32)


def _apply_elkan_bayes_shift(
    prob_cal: np.ndarray, *, pop_prev: float, sample_prev: float
) -> np.ndarray:
    """Apply exact Elkan (2001) prior-odds log-odds shift from sample to fold population."""
    pi_pop = float(np.clip(pop_prev, 1e-5, 1.0 - 1e-5))
    pi_smp = float(np.clip(sample_prev, 1e-5, 1.0 - 1e-5))
    delta_ell = float(logit(pi_pop) - logit(pi_smp))
    p = np.clip(np.asarray(prob_cal, dtype=np.float64), 1e-6, 1.0 - 1e-6)
    return np.clip(expit(logit(p) + delta_ell), 0.0, 1.0).astype(np.float32)


def fit_and_predict_dkrn1_fold(
    base_mm: np.ndarray,
    gvc_mm: np.ndarray,
    sahg_mm: np.ndarray,
    dkrn1_mm: np.ndarray,
    nuisance_fp: np.ndarray,
    all_names: list[str],
    fp: np.ndarray,
    fp_ids: np.ndarray,
    *,
    train_mask: np.ndarray,
    visible_mask: np.ndarray,
    predict_mask: np.ndarray,
    seed: int,
    chunk_size: int = 200_000,
) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    """Fit Split-View Head A (47-ch kernel regressor) + Head B (62-ch Bayes core) on ``train_mask``.

    Returns both Arm 1 (full Split-View) and Arm 2 (pure Head A 47-ch kernel-only) fold surfaces
    from a single fold pass so Head A is never redundantly refit.
    """
    if len(all_names) != 62:
        raise ValueError(f"Expected 62 DKRN1 channels, got {len(all_names)}")

    head_a_cols = [j for j, nm in enumerate(all_names) if nm not in RAW_LIDAR_AMPLITUDE_NAMES]
    if len(head_a_cols) != 47:
        raise RuntimeError(f"Expected 47 gap-native Head A channels, got {len(head_a_cols)}")

    sel_names = sorted(set(dprf1.SELECTIVE_RESID_NAMES) | set(DKRN1_SELECTIVE_EXTRA_NAMES))
    sel_indices = [all_names.index(nm) for nm in sel_names]

    gate_col_names = sorted(
        {
            *HYDRO_GATE_NAMES,
            "lidar_contour_over_bank",
            *dprf1.UPFLOW_CONDUIT_NAMES,
            *dprf1.SUBSURFACE_STEP_NAMES,
            *CONCEALED_EXTRA_STEP_NAMES,
            dprf1.STEEP_SLOPE_NAME,
        }
    )
    gate_col_map = {nm: all_names.index(nm) for nm in gate_col_names}
    g_sat_idx = all_names.index("sahg_g_sat")
    slope_idx = all_names.index(dprf1.STEEP_SLOPE_NAME)
    rel_idx = all_names.index(dprf1.LOCAL_RELIEF_NAME)

    # 1. Sample Head B (stratified core) and Head A (300 m kernel corridor) strictly on train_mask
    core_rows, y_core = dprf1.sample_fold_training_rows(
        train_mask,
        visible_mask,
        fp_ids,
        mode="stratified_d3",
        max_pos=25_000,
        max_neg=75_000,
        seed=seed,
    )
    kern_rows, y_kern, pop_mean_yk = sample_kernel_corridor_rows(
        train_mask, visible_mask, fp_ids, seed=seed + 17
    )
    pop_core_prev = float(int((train_mask & visible_mask).sum()) / max(int(train_mask.sum()), 1))
    sample_core_prev = float(np.mean(y_core))
    sample_mean_yk = float(np.mean(y_kern))

    # 2. Disjoint 35,000 training background rows for residualizer, gate scaler, and calibrators
    bg_mask = train_mask & (~visible_mask)
    bg_pool_all = np.flatnonzero(bg_mask.ravel()[fp_ids])
    used_train = np.union1d(core_rows, kern_rows)
    bg_disjoint = np.setdiff1d(bg_pool_all, used_train, assume_unique=True)
    if len(bg_disjoint) < 5_000:
        bg_disjoint = bg_pool_all
    rng_bg = np.random.default_rng(seed + 41)
    bg_sel = np.sort(rng_bg.choice(bg_disjoint, size=min(35_000, len(bg_disjoint)), replace=False))

    x_bg = dprf1.read_stack_rows(bg_sel, base_mm, gvc_mm, sahg_mm, dkrn1_mm)
    c_bg = np.asarray(nuisance_fp[bg_sel], dtype=np.float32)

    gate_scaler = ThreeRegimeGateScaler(gate_col_map).fit(x_bg)
    resid = dprf1.SelectiveNonTopographicResidualizer(sel_indices, alpha=100.0).fit(c_bg, x_bg)
    x_bg_res = resid.transform_inplace(c_bg, x_bg.copy())

    # 3. Fit Head A (47-ch Gap-Native 300 m DTI-Kernel Soft-Label Regressor) + Head B (62-ch Core)
    x_kern = dprf1.read_stack_rows(kern_rows, base_mm, gvc_mm, sahg_mm, dkrn1_mm)
    c_kern = np.asarray(nuisance_fp[kern_rows], dtype=np.float32)
    resid.transform_inplace(c_kern, x_kern)
    x_kern_a = np.ascontiguousarray(x_kern[:, head_a_cols], dtype=np.float32)
    del x_kern, c_kern

    reg_models: list[HistGradientBoostingRegressor] = []
    clf_models: list[HistGradientBoostingClassifier] = []

    with threadpool_limits(limits=2):
        for s_off in (110, 210):
            reg = HistGradientBoostingRegressor(
                loss="squared_error",
                max_iter=190,
                learning_rate=0.055,
                max_leaf_nodes=31,
                min_samples_leaf=80,
                l2_regularization=2.5,
                early_stopping=False,
                random_state=seed + s_off,
            )
            reg.fit(x_kern_a, y_kern)
            reg_models.append(reg)
        del x_kern_a
        gc.collect()

        x_core = dprf1.read_stack_rows(core_rows, base_mm, gvc_mm, sahg_mm, dkrn1_mm)
        c_core = np.asarray(nuisance_fp[core_rows], dtype=np.float32)
        resid.transform_inplace(c_core, x_core)
        for s_off in (310, 410):
            clf = HistGradientBoostingClassifier(
                max_iter=190,
                learning_rate=0.055,
                max_leaf_nodes=31,
                min_samples_leaf=80,
                l2_regularization=2.5,
                early_stopping=False,
                random_state=seed + s_off,
            )
            clf.fit(x_core, y_core)
            clf_models.append(clf)
        del x_core, c_core
        gc.collect()

        # Fit Head A & Head B calibrators on training background predictions
        x_bg_a = np.ascontiguousarray(x_bg_res[:, head_a_cols], dtype=np.float32)
        mu_bg_raw = 0.5 * (reg_models[0].predict(x_bg_a) + reg_models[1].predict(x_bg_a))
        del x_bg_a
        kern_cal = KernelCreditLogitCalibrator(alpha=100.0).fit(
            mu_bg_raw,
            c_bg,
            x_bg[:, slope_idx],
            x_bg[:, rel_idx],
            sample_mean_yk=sample_mean_yk,
            pop_mean_yk=pop_mean_yk,
        )

        p_bg_raw = 0.5 * (
            clf_models[0].predict_proba(x_bg_res)[:, 1]
            + clf_models[1].predict_proba(x_bg_res)[:, 1]
        )
        core_cal = dprf1.ReliefConditionedCalibrator(alpha=100.0).fit(
            p_bg_raw,
            has_lidar_bg=np.isfinite(x_bg[:, g_sat_idx]),
            nuisance_bg=c_bg,
            slope_bg=x_bg[:, slope_idx],
            local_relief_bg=x_bg[:, rel_idx],
        )
        del x_bg, x_bg_res, c_bg, mu_bg_raw, p_bg_raw
        gc.collect()

        # 4. Chunked prediction on predict_mask
        pred_rows = np.flatnonzero(predict_mask.ravel()[fp_ids])
        q_core_vec = np.empty(len(pred_rows), dtype=np.float32)
        mu_kern_vec = np.empty(len(pred_rows), dtype=np.float32)
        m_hydro_vec = np.empty(len(pred_rows), dtype=np.float32)
        m_conc_vec = np.empty(len(pred_rows), dtype=np.float32)
        has_lid_vec = np.empty(len(pred_rows), dtype=bool)

        for start in range(0, len(pred_rows), chunk_size):
            sl = pred_rows[start : start + chunk_size]
            x_raw = dprf1.read_stack_rows(sl, base_mm, gvc_mm, sahg_mm, dkrn1_mm)
            m_hydro_vec[start : start + chunk_size] = gate_scaler.score_hydro_multiplier(x_raw)
            m_conc_vec[start : start + chunk_size] = gate_scaler.score_concealed_multiplier(x_raw)

            hl = np.isfinite(x_raw[:, g_sat_idx])
            has_lid_vec[start : start + chunk_size] = hl
            slp = x_raw[:, slope_idx].copy()
            rel = x_raw[:, rel_idx].copy()
            c_sub = np.asarray(nuisance_fp[sl], dtype=np.float32)
            resid.transform_inplace(c_sub, x_raw)

            x_sub_a = np.ascontiguousarray(x_raw[:, head_a_cols], dtype=np.float32)
            mu_raw = 0.5 * (reg_models[0].predict(x_sub_a) + reg_models[1].predict(x_sub_a))
            del x_sub_a
            mu_kern_vec[start : start + chunk_size] = kern_cal.transform(mu_raw, c_sub, slp, rel)

            p_raw = 0.5 * (
                clf_models[0].predict_proba(x_raw)[:, 1] + clf_models[1].predict_proba(x_raw)[:, 1]
            )
            p_cal = core_cal.transform(p_raw, hl, c_sub, slp, rel)
            q_core_vec[start : start + chunk_size] = _apply_elkan_bayes_shift(
                p_cal, pop_prev=pop_core_prev, sample_prev=sample_core_prev
            )
            del x_raw, c_sub, mu_raw, p_raw, p_cal

    def scatter_2d(vec: np.ndarray) -> np.ndarray:
        arr = np.zeros(fp.shape, dtype=np.float32)
        arr.ravel()[fp_ids[pred_rows]] = vec
        return arr

    q_sharp = dprf1.sharpen_ridge_coherence(scatter_2d(q_core_vec), predict_mask, half_len_px=4)
    mu_sharp = dprf1.sharpen_ridge_coherence(scatter_2d(mu_kern_vec), predict_mask, half_len_px=4)

    q_deb = dprf1.debiased_apron_surface(q_sharp, predict_mask, visible_mask)
    mu_deb = dprf1.debiased_apron_surface(mu_sharp, predict_mask, visible_mask)

    has_lid_2d = np.zeros(fp.shape, dtype=bool)
    has_lid_2d.ravel()[fp_ids[pred_rows]] = has_lid_vec

    u_post = np.where(
        has_lid_2d,
        0.52 * q_deb + 0.48 * mu_deb,
        0.35 * q_deb + 0.65 * mu_deb,
    ).astype(np.float32)
    u_post[~predict_mask] = 0.0

    m_hydro_2d = scatter_2d(m_hydro_vec)
    m_conc_2d = scatter_2d(m_conc_vec)

    surfaces = {
        "u_post": u_post,
        "mu_deb": mu_deb,
        "q_deb": q_deb,
        "m_hydro": m_hydro_2d,
        "m_concealed": m_conc_2d,
    }
    meta = {
        "n_head_a_channels": len(head_a_cols),
        "n_head_b_channels": len(all_names),
        "n_core_pos": int((y_core == 1).sum()),
        "n_core_neg": int((y_core == 0).sum()),
        "n_kern_rows": int(len(y_kern)),
        "pop_core_prev": pop_core_prev,
        "pop_mean_yk": pop_mean_yk,
        "elkan_bayes_shift": float(logit(pop_core_prev) - logit(sample_core_prev)),
        "kernel_logit_shift": float(kern_cal.prior_shift_),
    }
    return surfaces, meta


def _net_tversky_submodular_stage(
    weight_2d: np.ndarray,
    mu_kernel_2d: np.ndarray,
    valid_2d: np.ndarray,
    vis_2d: np.ndarray,
    *,
    target_add: int,
    min_spacing_px: float,
    catalogue_clearance_px: float,
    tau_eff: float,
    existing_dots: np.ndarray | None = None,
) -> np.ndarray:
    """Minoux (1978) lazy-greedy 300 m coverage allocator with Net-Tversky FP cost."""
    h, w = weight_2d.shape
    out = (
        np.asarray(existing_dots, dtype=np.float32).copy()
        if existing_dots is not None
        else np.zeros((h, w), dtype=np.float32)
    )
    if target_add <= 0:
        return out

    if vis_2d.any():
        dist_vis = distance_transform_edt(~vis_2d)
        eligible = valid_2d & (~vis_2d) & (dist_vis > catalogue_clearance_px)
    else:
        eligible = valid_2d.copy()
    if existing_dots is not None and np.any(existing_dots > 0.5):
        dist_ex = distance_transform_edt(~(existing_dots > 0.5))
        eligible &= dist_ex >= (min_spacing_px - 1e-9)
    eligible &= np.isfinite(weight_2d) & (weight_2d > 0.0)

    cand_ids = np.flatnonzero(eligible.ravel())
    if not len(cand_ids):
        return out

    pool_cap = min(len(cand_ids), max(target_add * 12, 150_000))
    cand_scores = weight_2d.ravel()[cand_ids]
    if len(cand_ids) > pool_cap:
        part = np.argpartition(-cand_scores, pool_cap - 1)[:pool_cap]
        cand_ids = cand_ids[part]
        cand_scores = cand_scores[part]
    order = np.lexsort((cand_ids, -cand_scores))
    cand_ids = cand_ids[order]

    pad = int(np.ceil(max(RADIUS_PX, min_spacing_px))) + 1
    hp, wp = h + 2 * pad, w + 2 * pad

    active_mass = np.where(
        valid_2d & (~vis_2d) & np.isfinite(weight_2d), np.clip(weight_2d, 0.0, 1.0), 0.0
    ).astype(np.float32)
    p_pad = np.zeros((hp, wp), dtype=np.float32)
    p_pad[pad : pad + h, pad : pad + w] = active_mass

    mu_clean = np.where(np.isfinite(mu_kernel_2d), np.clip(mu_kernel_2d, 0.0, 1.0), 0.0).astype(
        np.float32
    )
    scale_ref = max(float(np.mean(cand_scores)), 1e-4)
    tau_stage = float(tau_eff) * scale_ref

    k_offs_1d = np.array([dy * wp + dx for dy, dx, _ in KERNEL_OFFSETS], dtype=np.int64)
    k_vals = np.array([k for _, _, k in KERNEL_OFFSETS], dtype=np.float32)

    r_excl = int(np.ceil(min_spacing_px))
    excl_offs_1d = np.array(
        [
            dy * wp + dx
            for dy in range(-r_excl, r_excl + 1)
            for dx in range(-r_excl, r_excl + 1)
            if float(np.hypot(dy, dx)) < min_spacing_px - 1e-9
        ],
        dtype=np.int64,
    )

    p_1d = p_pad.ravel()
    cov_1d = np.zeros(hp * wp, dtype=np.float32)
    blocked_1d = np.zeros(hp * wp, dtype=bool)

    if existing_dots is not None and np.any(existing_dots > 0.5):
        ey, ex = np.nonzero(existing_dots > 0.5)
        ex_centers = (ey + pad) * wp + (ex + pad)
        for c0 in ex_centers.tolist():
            idx29 = c0 + k_offs_1d
            cov_1d[idx29] = np.maximum(cov_1d[idx29], k_vals)
            blocked_1d[c0 + excl_offs_1d] = True

    cy, cx = np.unravel_index(cand_ids, (h, w))
    centers = (cy + pad) * wp + (cx + pad)

    heap: list[tuple[float, int, int, int, int, float]] = []
    for i in range(len(cand_ids)):
        c0 = int(centers[i])
        if blocked_1d[c0]:
            continue
        ry_i, rx_i = int(cy[i]), int(cx[i])
        idx29 = c0 + k_offs_1d
        rem = np.maximum(k_vals - cov_1d[idx29], 0.0)
        tp_gain = float(np.dot(p_1d[idx29], rem))
        if tp_gain <= 1e-12:
            continue
        fp_pen = tau_stage * (1.0 - float(mu_clean[ry_i, rx_i]))
        net_u = tp_gain - fp_pen
        heap.append((-net_u, int(i), c0, ry_i, rx_i, fp_pen))
    heapq.heapify(heap)

    added = 0
    while heap and added < target_add:
        neg_ub, rank, center, ry, rx, fp_pen = heapq.heappop(heap)
        if blocked_1d[center]:
            continue
        idx29 = center + k_offs_1d
        rem = k_vals - cov_1d[idx29]
        np.maximum(rem, 0.0, out=rem)
        tp_gain = float(np.dot(p_1d[idx29], rem))
        if tp_gain <= 1e-12:
            continue
        net_gain = tp_gain - fp_pen
        if heap and (-net_gain > heap[0][0] + 1e-12):
            heapq.heappush(heap, (-net_gain, rank, center, ry, rx, fp_pen))
            continue
        out[ry, rx] = 1.0
        cov_1d[idx29] = np.maximum(cov_1d[idx29], k_vals)
        blocked_1d[center + excl_offs_1d] = True
        added += 1

    return out


def three_regime_net_tversky_allocate(
    u_base_2d: np.ndarray,
    mu_kernel_2d: np.ndarray,
    m_hydro_2d: np.ndarray,
    m_concealed_2d: np.ndarray,
    valid_mask: np.ndarray,
    visible_faults: np.ndarray,
    *,
    budget: int,
    shares: tuple[float, float, float] = (0.48, 0.28, 0.24),
    min_spacing_px: float = 2.9,
    catalogue_clearance_px: float = 2.0,
    tau_eff: float = TAU_EFF_BASE,
) -> np.ndarray:
    """Allocate ``budget`` dots across Ridge (48%), D8 Hydrologic (28%), and Concealed (24%)."""
    val = np.asarray(valid_mask, dtype=bool)
    vis = np.asarray(visible_faults, dtype=bool)
    k_total = int(budget)
    if k_total <= 0:
        return np.zeros(u_base_2d.shape, dtype=np.float32)

    s1, s2, _ = shares
    k1 = int(round(k_total * float(s1)))
    k2 = int(round(k_total * float(s2)))

    w1 = np.asarray(u_base_2d, dtype=np.float32)
    w2 = (w1 * np.asarray(m_hydro_2d, dtype=np.float32)).astype(np.float32)
    w3 = (w1 * np.asarray(m_concealed_2d, dtype=np.float32)).astype(np.float32)

    dots = _net_tversky_submodular_stage(
        w1,
        mu_kernel_2d,
        val,
        vis,
        target_add=k1,
        min_spacing_px=min_spacing_px,
        catalogue_clearance_px=catalogue_clearance_px,
        tau_eff=tau_eff,
        existing_dots=None,
    )
    rem_after_1 = k_total - int((dots > 0.5).sum())
    if rem_after_1 > 0:
        add2 = min(k2, rem_after_1)
        dots = _net_tversky_submodular_stage(
            w2,
            mu_kernel_2d,
            val,
            vis,
            target_add=add2,
            min_spacing_px=min_spacing_px,
            catalogue_clearance_px=catalogue_clearance_px,
            tau_eff=tau_eff,
            existing_dots=dots,
        )
    rem_after_2 = k_total - int((dots > 0.5).sum())
    if rem_after_2 > 0:
        dots = _net_tversky_submodular_stage(
            w3,
            mu_kernel_2d,
            val,
            vis,
            target_add=rem_after_2,
            min_spacing_px=min_spacing_px,
            catalogue_clearance_px=catalogue_clearance_px,
            tau_eff=tau_eff,
            existing_dots=dots,
        )
    # Top-up fallback on w1 only if Stages 2/3 exhausted eligible pool before k_total
    rem_final = k_total - int((dots > 0.5).sum())
    if rem_final > 0:
        dots = _net_tversky_submodular_stage(
            w1,
            mu_kernel_2d,
            val,
            vis,
            target_add=rem_final,
            min_spacing_px=min_spacing_px,
            catalogue_clearance_px=catalogue_clearance_px,
            tau_eff=tau_eff,
            existing_dots=dots,
        )
    return dots.astype(np.float32)


def ranking_surface_for_novelty(
    u_base_2d: np.ndarray,
    m_hydro_2d: np.ndarray,
    m_concealed_2d: np.ndarray,
    valid_mask: np.ndarray,
    visible_faults: np.ndarray,
    *,
    catalogue_clearance_px: float = 2.0,
) -> np.ndarray:
    """Combined pre-placement ranking surface aligned with 3-regime weights (48/28/24)."""
    val = np.asarray(valid_mask, dtype=bool)
    vis = np.asarray(visible_faults, dtype=bool)
    comb = (
        0.48 * u_base_2d + 0.28 * (u_base_2d * m_hydro_2d) + 0.24 * (u_base_2d * m_concealed_2d)
    ).astype(np.float32)
    if vis.any():
        d_vis = distance_transform_edt(~vis)
        elig = val & (~vis) & (d_vis > catalogue_clearance_px)
    else:
        elig = val & (~vis)
    return np.where(elig & np.isfinite(comb), np.clip(comb, 0.0, 1.0), 0.0).astype(np.float32)
