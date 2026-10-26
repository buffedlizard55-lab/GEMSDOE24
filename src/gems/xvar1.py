"""H24-XVAR1: Two-Sided Azimuthal Semivariogram Texture-Jump & LiDAR-Free Subsurface Discovery.

Implements the preregistered Rank #1 prospective portfolio hypothesis from
``knowledge/29_preregistered_XVAR1_2026-10-26.md``:

1. Eight label-free azimuthal semivariogram & split-domain roughness-jump channels
   (``xvar_rtp_twosided_jump``, ``xvar_grav_twosided_jump``, ``xvar_mag_grav_concordance``,
   ``xvar_spectral_roughness_step``, ``xvar_up150_persistence``, ``xvar_anisotropy_corridor``,
   ``xvar_cond_basement_step``, ``xvar_strain_textured_conduit``) using parity-symmetric
   centered lag differences so split-half-plane log-semivariogram steps peak pixel-exactly
   on concealed fault planes without half-lag shift.
2. Strictly 100% LiDAR-amplitude-free 45-channel feature view (37 non-LiDAR base/GVC/SAHG
   channels + 8 XVAR1 channels; all 15 1 m 3DEP LiDAR channels excluded) so LiDAR-covered
   and LiDAR-gap domains are modeled symmetrically without DPRF1 scarp template convergence.
3. Full fold-safe nuisance residualization across all 8 XVAR1 channels, 9 regional survey
   channels, model logits (``nuisance_weight=1.0``), and the secondary concealed-texture /
   hydrothermal gate against ``[area1, block_1..4, claim_m, road_m]`` to prevent road,
   mining-claim, acquisition-block, and Area1/Area2 resolution-mosaic leakage.
4. Dual subsurface estimator (300 m DTI-kernel soft-label regressor + Elkan prior-odds
   fault-core classifier) and two-regime lazy-greedy 300 m submodular dot allocation.
"""

from __future__ import annotations

import gc
import json
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt, gaussian_filter
from scipy.special import expit
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from threadpoolctl import threadpool_limits

from . import dkrn1, dprf1, gvc
from .validator import sha256_file

XVAR1_NAMES: tuple[str, ...] = (
    "xvar_rtp_twosided_jump",
    "xvar_grav_twosided_jump",
    "xvar_mag_grav_concordance",
    "xvar_spectral_roughness_step",
    "xvar_up150_persistence",
    "xvar_anisotropy_corridor",
    "xvar_cond_basement_step",
    "xvar_strain_textured_conduit",
)

RAW_LIDAR_AMPLITUDE_NAMES: frozenset[str] = dkrn1.RAW_LIDAR_AMPLITUDE_NAMES

XVAR1_HGB_REG_PARAMS: dict[str, Any] = {
    "loss": "squared_error",
    "max_iter": 190,
    "learning_rate": 0.055,
    "max_leaf_nodes": 31,
    "min_samples_leaf": 80,
    "l2_regularization": 2.5,
    "early_stopping": False,
}

XVAR1_HGB_CLF_PARAMS: dict[str, Any] = {
    "max_iter": 190,
    "learning_rate": 0.055,
    "max_leaf_nodes": 31,
    "min_samples_leaf": 80,
    "l2_regularization": 2.5,
    "early_stopping": False,
}

# 4 strike azimuths: m=0 (E-W strike -> N-S normal), m=1 (NE-SW), m=2 (N-S -> E-W normal), m=3 (NW-SE)
_STRIKE_UNIT_STEPS: tuple[tuple[int, int], ...] = (
    (0, 1),
    (1, 1),
    (1, 0),
    (-1, 1),
)
_NORMAL_UNIT_STEPS: tuple[tuple[int, int], ...] = (
    (1, 0),
    (-1, 1),
    (0, -1),
    (1, 1),
)


def _step_for_lag(unit_dy: int, unit_dx: int, lag_px: int) -> tuple[int, int, float]:
    """Scale discrete step so Euclidean distance matches lag_px in 100 m grid units."""
    if unit_dy != 0 and unit_dx != 0:
        d = max(1, int(round(lag_px / np.sqrt(2.0))))
        dy, dx = unit_dy * d, unit_dx * d
    else:
        dy, dx = unit_dy * lag_px, unit_dx * lag_px
    dist_sq = float(dy * dy + dx * dx)
    scale = float(lag_px * lag_px) / max(dist_sq, 1.0)
    return dy, dx, scale


def _shift2d(padded: np.ndarray, pad: int, dy: int, dx: int, h: int, w: int) -> np.ndarray:
    return padded[pad + dy : pad + dy + h, pad + dx : pad + dx + w]


def _centered_directional_semivariances(
    z_filled: np.ndarray,
    lag_px: int,
    *,
    sigma_px: float = 3.0,
) -> tuple[list[np.ndarray], np.ndarray]:
    """Parity-symmetric directional semivariances gamma_m(x; lag) and isotropic mean."""
    h, w = z_filled.shape
    pad = lag_px + 1
    padded = np.pad(z_filled.astype(np.float32, copy=False), pad, mode="edge")
    dir_gammas: list[np.ndarray] = []
    iso = np.zeros((h, w), dtype=np.float32)
    for u_dy, u_dx in _STRIKE_UNIT_STEPS:
        dy, dx, scale = _step_for_lag(u_dy, u_dx, lag_px)
        fwd = _shift2d(padded, pad, dy, dx, h, w) - z_filled
        bwd = _shift2d(padded, pad, -dy, -dx, h, w) - z_filled
        raw_sq = (0.25 * scale) * (fwd * fwd + bwd * bwd)
        gm = gaussian_filter(raw_sq.astype(np.float32, copy=False), sigma=sigma_px).astype(
            np.float32, copy=False
        )
        dir_gammas.append(gm)
        iso += 0.25 * gm
    return dir_gammas, iso


def _twosided_log_jumps(
    gamma_iso: np.ndarray,
    *,
    offset_px: int = 5,
    eps: float = 1e-3,
) -> list[np.ndarray]:
    """Signed log-semivariogram jumps J_m(x) across strike normals at +/- offset_px."""
    h, w = gamma_iso.shape
    pad = offset_px + 1
    log_g = np.log(np.maximum(gamma_iso, 0.0) + eps).astype(np.float32, copy=False)
    padded = np.pad(log_g, pad, mode="edge")
    jumps: list[np.ndarray] = []
    for n_dy, n_dx in _NORMAL_UNIT_STEPS:
        dy, dx, _ = _step_for_lag(n_dy, n_dx, offset_px)
        pos_half = _shift2d(padded, pad, dy, dx, h, w)
        neg_half = _shift2d(padded, pad, -dy, -dx, h, w)
        jumps.append((pos_half - neg_half).astype(np.float32, copy=False))
    return jumps


def _twosided_scalar_diffs(field_2d: np.ndarray, *, offset_px: int = 5) -> list[np.ndarray]:
    """Signed split-half-plane differences across strike normals at +/- offset_px."""
    h, w = field_2d.shape
    pad = offset_px + 1
    padded = np.pad(field_2d.astype(np.float32, copy=False), pad, mode="edge")
    diffs: list[np.ndarray] = []
    for n_dy, n_dx in _NORMAL_UNIT_STEPS:
        dy, dx, _ = _step_for_lag(n_dy, n_dx, offset_px)
        pos_half = _shift2d(padded, pad, dy, dx, h, w)
        neg_half = _shift2d(padded, pad, -dy, -dx, h, w)
        diffs.append((pos_half - neg_half).astype(np.float32, copy=False))
    return diffs


def build_xvar1_memmap(
    root: Path,
    base_mm: np.ndarray,
    base_names: list[str],
    fp: np.ndarray,
    cache_path: Path,
    *,
    force: bool = False,
) -> tuple[np.memmap, list[str]]:
    """Build or verify the 8-channel label-free XVAR1 semivariogram memmap."""
    h, w = fp.shape
    fp_ids = np.flatnonzero(fp.ravel())
    n_fp = len(fp_ids)
    meta_path = cache_path.with_suffix(".json")

    src_tf = root / "data/training_features.tif"
    src_ext = root / "data/external/geodawn_extensions_u8.tif"
    prep_path = root / "data/prepared/features.npy"
    expected_inputs = {
        "data/prepared/features.npy": sha256_file(prep_path),
        "data/training_features.tif": sha256_file(src_tf),
        "data/external/geodawn_extensions_u8.tif": sha256_file(src_ext),
    }

    if cache_path.exists() and meta_path.exists() and not force:
        meta = json.loads(meta_path.read_text())
        if (
            meta.get("names") == list(XVAR1_NAMES)
            and meta.get("shape") == [n_fp, len(XVAR1_NAMES)]
            and meta.get("inputs") == expected_inputs
            and meta.get("sha256") == sha256_file(cache_path)
        ):
            mm = np.memmap(cache_path, dtype="float32", mode="r", shape=(n_fp, len(XVAR1_NAMES)))
            return mm, list(XVAR1_NAMES)

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = cache_path.with_suffix(".partial.dat")
    mm_w = np.memmap(tmp_path, dtype="float32", mode="w+", shape=(n_fp, len(XVAR1_NAMES)))

    def _base_grid(name: str) -> tuple[np.ndarray, np.ndarray]:
        col = base_names.index(name)
        g = np.full((h, w), np.nan, dtype=np.float32)
        g.ravel()[fp_ids] = base_mm[:, col]
        v = fp & np.isfinite(g)
        return g, v

    def _std_filled(g: np.ndarray, v: np.ndarray) -> np.ndarray:
        rz = gvc._robust_z(g, v)
        return gvc._nearest_fill(rz, v)

    # Read base float32 geophysical grids
    rtp_raw, v_rtp = _base_grid("rtp")
    grav_raw, v_grav = _base_grid("iso_grav_anom")
    tmi_raw, v_tmi = _base_grid("tmi")
    cond_raw, v_cond = _base_grid("cond_surf")
    dtb_raw, v_dtb = _base_grid("depth_to_base_surf")
    shear_raw, v_shear = _base_grid("geod_shearrate")
    dil_raw, v_dil = _base_grid("geod_dilaterate")

    z_rtp = _std_filled(rtp_raw, v_rtp)
    z_grav = _std_filled(grav_raw, v_grav)
    z_tmi = _std_filled(tmi_raw, v_tmi)
    del rtp_raw, grav_raw, tmi_raw

    # Semivariances on RTP and gravity at lags h=2 (200 m), h=3 (300 m), h=6 (600 m)
    _, rtp_iso2 = _centered_directional_semivariances(z_rtp, 2, sigma_px=3.0)
    rtp_dir3, rtp_iso3 = _centered_directional_semivariances(z_rtp, 3, sigma_px=3.0)
    _, rtp_iso6 = _centered_directional_semivariances(z_rtp, 6, sigma_px=3.0)
    del z_rtp, rtp_iso3

    _, grav_iso2 = _centered_directional_semivariances(z_grav, 2, sigma_px=3.0)
    grav_dir3, grav_iso3 = _centered_directional_semivariances(z_grav, 3, sigma_px=3.0)
    _, grav_iso6 = _centered_directional_semivariances(z_grav, 6, sigma_px=3.0)
    del z_grav, grav_iso3

    j_rtp2 = _twosided_log_jumps(rtp_iso2, offset_px=5)
    j_rtp6 = _twosided_log_jumps(rtp_iso6, offset_px=5)
    j_grav2 = _twosided_log_jumps(grav_iso2, offset_px=5)
    j_grav6 = _twosided_log_jumps(grav_iso6, offset_px=5)

    # 1. xvar_rtp_twosided_jump: persistent across lags 200 m & 600 m with matching polarity
    c_rtp_jump = np.zeros((h, w), dtype=np.float32)
    for m in range(4):
        same_sign = (j_rtp2[m] * j_rtp6[m]) > 0.0
        val = np.sqrt(np.maximum(0.0, np.abs(j_rtp2[m]) * np.abs(j_rtp6[m]))).astype(
            np.float32, copy=False
        )
        c_rtp_jump = np.maximum(c_rtp_jump, np.where(same_sign, val, 0.0))
    c_rtp_jump[~v_rtp] = np.nan
    mm_w[:, 0] = c_rtp_jump.ravel()[fp_ids]
    del c_rtp_jump, j_rtp6

    # 2. xvar_grav_twosided_jump: persistent across lags 200 m & 600 m with matching polarity
    c_grav_jump = np.zeros((h, w), dtype=np.float32)
    for m in range(4):
        same_sign = (j_grav2[m] * j_grav6[m]) > 0.0
        val = np.sqrt(np.maximum(0.0, np.abs(j_grav2[m]) * np.abs(j_grav6[m]))).astype(
            np.float32, copy=False
        )
        c_grav_jump = np.maximum(c_grav_jump, np.where(same_sign, val, 0.0))
    c_grav_jump[~v_grav] = np.nan
    mm_w[:, 1] = c_grav_jump.ravel()[fp_ids]
    del c_grav_jump, j_grav6, grav_iso2, grav_iso6

    # 3. xvar_mag_grav_concordance: azimuth- and polarity-locked RTP + gravity texture step
    c_concord = np.zeros((h, w), dtype=np.float32)
    for m in range(4):
        prod = np.maximum(0.0, j_rtp2[m] * j_grav2[m])
        c_concord = np.maximum(c_concord, np.sqrt(prod).astype(np.float32, copy=False))
    v_mg = v_rtp & v_grav
    c_concord_filled = c_concord.copy()
    c_concord[~v_mg] = np.nan
    mm_w[:, 2] = c_concord.ravel()[fp_ids]
    del c_concord, j_rtp2, j_grav2

    # 4. xvar_spectral_roughness_step: Spector-Grant depth-proxy log(gamma_200 / gamma_600) jump
    rho_sg = np.log((np.maximum(rtp_iso2, 0.0) + 1e-3) / (np.maximum(rtp_iso6, 0.0) + 1e-3)).astype(
        np.float32, copy=False
    )
    del rtp_iso2, rtp_iso6
    sg_diffs = _twosided_scalar_diffs(rho_sg, offset_px=5)
    c_sg_step = np.zeros((h, w), dtype=np.float32)
    for d_m in sg_diffs:
        c_sg_step = np.maximum(c_sg_step, np.abs(d_m))
    c_sg_step[~v_rtp] = np.nan
    mm_w[:, 3] = c_sg_step.ravel()[fp_ids]
    del rho_sg, sg_diffs, c_sg_step

    # 5. xvar_up150_persistence: TMI vs TMI_up150 (quantized rank 1..255) semivariogram persistence
    ext_meta = json.loads((root / "data/external/geodawn_extensions.json").read_text())
    up150_band = ext_meta["channels"].index("TMI_up150") + 1
    with rasterio.open(src_ext) as ds_ext:
        up150_u8 = ds_ext.read(up150_band)
    v_up150 = fp & (up150_u8 > 0)
    up150_f = np.where(v_up150, up150_u8.astype(np.float32), np.nan)
    del up150_u8
    z_up150 = _std_filled(up150_f, v_up150)
    del up150_f
    _, tmi_iso3 = _centered_directional_semivariances(z_tmi, 3, sigma_px=3.0)
    _, up150_iso3 = _centered_directional_semivariances(z_up150, 3, sigma_px=3.0)
    del z_tmi, z_up150
    j_tmi3 = _twosided_log_jumps(tmi_iso3, offset_px=5)
    j_up3 = _twosided_log_jumps(up150_iso3, offset_px=5)
    del tmi_iso3, up150_iso3
    c_up_persist = np.zeros((h, w), dtype=np.float32)
    for m in range(4):
        prod = np.maximum(0.0, j_tmi3[m] * j_up3[m])
        c_up_persist = np.maximum(c_up_persist, np.sqrt(prod).astype(np.float32, copy=False))
    c_up_persist[~(v_tmi & v_up150)] = np.nan
    mm_w[:, 4] = c_up_persist.ravel()[fp_ids]
    del j_tmi3, j_up3, c_up_persist

    # 6. xvar_anisotropy_corridor: cross-strike vs along-strike directional semivariance log-ratio
    c_aniso = np.zeros((h, w), dtype=np.float32)
    for m in range(4):
        perp_m = (m + 2) % 4
        lr_rtp = np.log(
            (np.maximum(rtp_dir3[perp_m], 0.0) + 1e-3) / (np.maximum(rtp_dir3[m], 0.0) + 1e-3)
        )
        lr_grav = np.log(
            (np.maximum(grav_dir3[perp_m], 0.0) + 1e-3) / (np.maximum(grav_dir3[m], 0.0) + 1e-3)
        )
        c_aniso = np.maximum(c_aniso, np.maximum(0.0, 0.5 * (lr_rtp + lr_grav)).astype(np.float32))
    c_aniso[~v_mg] = np.nan
    mm_w[:, 5] = c_aniso.ravel()[fp_ids]
    del rtp_dir3, grav_dir3, c_aniso

    # 7. xvar_cond_basement_step: split-domain step across cond_surf x depth_to_base_surf
    z_cond = gaussian_filter(_std_filled(cond_raw, v_cond), sigma=2.0).astype(np.float32)
    z_dtb = gaussian_filter(_std_filled(dtb_raw, v_dtb), sigma=2.0).astype(np.float32)
    del cond_raw, dtb_raw
    d_cond = _twosided_scalar_diffs(z_cond, offset_px=5)
    d_dtb = _twosided_scalar_diffs(z_dtb, offset_px=5)
    del z_cond, z_dtb
    c_cb_step = np.zeros((h, w), dtype=np.float32)
    for m in range(4):
        c_cb_step = np.maximum(
            c_cb_step,
            np.sqrt(np.abs(d_cond[m]) * np.abs(d_dtb[m])).astype(np.float32, copy=False),
        )
    c_cb_step[~(v_cond & v_dtb)] = np.nan
    mm_w[:, 6] = c_cb_step.ravel()[fp_ids]
    del d_cond, d_dtb, c_cb_step

    # 8. xvar_strain_textured_conduit: active shear/dilation strain-partitioned texture conduit
    z_sh = gvc._robust_z(shear_raw, v_shear)
    z_dl = gvc._robust_z(dil_raw, v_dil)
    del shear_raw, dil_raw
    strain_mod = (0.5 + 0.5 * expit(z_sh)) * (0.5 + 0.5 * expit(z_dl))
    c_strain_tex = (c_concord_filled * strain_mod).astype(np.float32)
    c_strain_tex[~(v_mg & v_shear & v_dil)] = np.nan
    mm_w[:, 7] = c_strain_tex.ravel()[fp_ids]
    del c_concord_filled, z_sh, z_dl, strain_mod, c_strain_tex

    mm_w.flush()
    del mm_w
    tmp_path.replace(cache_path)
    gc.collect()

    meta_out = {
        "names": list(XVAR1_NAMES),
        "shape": [n_fp, len(XVAR1_NAMES)],
        "sha256": sha256_file(cache_path),
        "inputs": expected_inputs,
        "excluded_forbidden_columns": sorted(gvc.FORBIDDEN_COLUMNS),
        "excluded_raw_lidar_channels": sorted(RAW_LIDAR_AMPLITUDE_NAMES),
        "d8_hydrology_used": False,
        "note": (
            "Parity-symmetric centered azimuthal semivariograms (lags 200m, 300m, 600m) and "
            "two-sided +/-500m split-half-plane log-semivariogram jumps across RTP, TMI, "
            "TMI_up150 ranks, isostatic gravity, conductivity, depth-to-basement, and geodetic strain."
        ),
    }
    meta_path.write_text(json.dumps(meta_out, indent=2) + "\n")
    mm_r = np.memmap(cache_path, dtype="float32", mode="r", shape=(n_fp, len(XVAR1_NAMES)))
    return mm_r, list(XVAR1_NAMES)


def _residualized_rank01(
    col_vals: np.ndarray,
    nuisance_fp: np.ndarray,
    bg_rows: np.ndarray,
    *,
    alpha: float = 60.0,
) -> np.ndarray:
    """Residualize a 1D footprint feature on disjoint training background rows, then rank to [0, 1]."""
    out = np.zeros(len(col_vals), dtype=np.float32)
    fin = np.isfinite(col_vals) & np.all(np.isfinite(nuisance_fp), axis=1)
    fit_rows = bg_rows[fin[bg_rows]]
    if len(fit_rows) < 64:
        return out
    xb_raw = nuisance_fp[fit_rows].astype(np.float64)
    xb = xb_raw.copy()
    xb[:, :2] = np.log1p(np.maximum(xb[:, :2], 0.0))
    mu_n = xb.mean(axis=0)
    sd_n = np.where(xb.std(axis=0) > 1e-6, xb.std(axis=0), 1.0)
    xz = (xb - mu_n) / sd_n
    yb = col_vals[fit_rows].astype(np.float64)
    mu_y = float(yb.mean())
    yc = yb - mu_y
    gram = xz.T @ xz + alpha * np.eye(xz.shape[1], dtype=np.float64)
    beta = np.linalg.solve(gram, xz.T @ yc)

    fin_idx = np.flatnonzero(fin)
    resid = np.empty(len(fin_idx), dtype=np.float32)
    for start in range(0, len(fin_idx), 250_000):
        sl = fin_idx[start : start + 250_000]
        sl_n = nuisance_fp[sl].astype(np.float64).copy()
        sl_n[:, :2] = np.log1p(np.maximum(sl_n[:, :2], 0.0))
        zn = (sl_n - mu_n) / sd_n
        resid[start : start + len(sl)] = (
            col_vals[sl].astype(np.float64) - (mu_y + zn @ beta)
        ).astype(np.float32)
    order = np.argsort(resid, kind="mergesort")
    ranks = np.empty(len(resid), dtype=np.float32)
    ranks[order] = (np.arange(len(resid), dtype=np.float32) + 0.5) / float(len(resid))
    out[fin_idx] = ranks
    return out


def _assemble_subsurface_rows(
    row_ids: np.ndarray,
    base_mm: np.ndarray,
    gvc_mm: np.ndarray,
    sahg_mm: np.ndarray,
    xvar_mm: np.ndarray | None,
    sub_cols_52: np.ndarray,
) -> np.ndarray:
    """Gather selected footprint rows for the 37-ch or 45-ch LiDAR-free stack."""
    n_base = base_mm.shape[1]
    n_gvc = gvc_mm.shape[1]
    n_52 = len(sub_cols_52)
    n_xvar = xvar_mm.shape[1] if xvar_mm is not None else 0
    out = np.empty((len(row_ids), n_52 + n_xvar), dtype=np.float32)
    for j, c52 in enumerate(sub_cols_52):
        c = int(c52)
        if c < n_base:
            out[:, j] = base_mm[row_ids, c]
        elif c < n_base + n_gvc:
            out[:, j] = gvc_mm[row_ids, c - n_base]
        else:
            out[:, j] = sahg_mm[row_ids, c - n_base - n_gvc]
    if xvar_mm is not None and n_xvar > 0:
        out[:, n_52:] = xvar_mm[row_ids]
    return out


def fit_and_predict_xvar1_fold(
    base_mm: np.ndarray,
    gvc_mm: np.ndarray,
    sahg_mm: np.ndarray,
    xvar_mm: np.ndarray | None,
    nuisance_fp: np.ndarray,
    names52: list[str],
    xvar_names: list[str],
    fp: np.ndarray,
    fp_ids: np.ndarray,
    *,
    train_mask: np.ndarray,
    visible_mask: np.ndarray,
    predict_mask: np.ndarray,
    include_xvar1: bool = True,
    seed: int = 20261026,
    chunk_rows: int = 160_000,
) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    """Fit LiDAR-free Dual Subsurface Estimator strictly inside train_mask & visible_mask."""
    rng = np.random.default_rng(seed)
    dist_vis = distance_transform_edt(~visible_mask).astype(np.float32)
    slope_fp = base_mm[:, names52.index("det_elev_slope")]
    relief_fp = base_mm[:, names52.index("det_local_relief")]

    sub_cols_52 = np.asarray(
        [i for i, n in enumerate(names52) if n not in RAW_LIDAR_AMPLITUDE_NAMES],
        dtype=np.int32,
    )
    sub_names_52 = [names52[int(i)] for i in sub_cols_52]
    active_xvar = xvar_mm if include_xvar1 else None
    feat_names = sub_names_52 + (list(xvar_names) if include_xvar1 else [])

    # Disjoint training background rows for fold-safe nuisance residualization & logit calibration
    bg_all = np.flatnonzero((train_mask & (~visible_mask) & (dist_vis >= 3.0)).ravel()[fp_ids])
    bg_cal = (
        np.sort(rng.choice(bg_all, size=min(35_000, len(bg_all)), replace=False))
        if len(bg_all) > 35_000
        else bg_all
    )

    extra_resid = frozenset(xvar_names) if include_xvar1 else frozenset()
    target_names = set(dprf1.SELECTIVE_RESID_NAMES) | set(extra_resid)
    target_indices = [j for j, nm in enumerate(feat_names) if nm in target_names]
    resid = dprf1.SelectiveNonTopographicResidualizer(
        target_indices=target_indices,
        alpha=60.0,
        distance_columns=2,
    )
    x_bg = _assemble_subsurface_rows(bg_cal, base_mm, gvc_mm, sahg_mm, active_xvar, sub_cols_52)
    resid.fit(nuisance_fp[bg_cal], x_bg)

    # Estimator 1: 300 m DTI-kernel soft-label regressor
    reg_rows, y_reg, pop_mean_kernel = dkrn1.sample_kernel_corridor_rows(
        train_mask, visible_mask, fp_ids, seed=seed + 11
    )
    x_reg = _assemble_subsurface_rows(reg_rows, base_mm, gvc_mm, sahg_mm, active_xvar, sub_cols_52)
    resid.transform_inplace(nuisance_fp[reg_rows], x_reg)
    with threadpool_limits(limits=2):
        reg0 = HistGradientBoostingRegressor(**XVAR1_HGB_REG_PARAMS, random_state=seed + 101).fit(
            x_reg, y_reg
        )
        reg1 = HistGradientBoostingRegressor(**XVAR1_HGB_REG_PARAMS, random_state=seed + 202).fit(
            x_reg, y_reg
        )
    del x_reg

    sample_mean_kernel = float(y_reg.mean())
    x_bg_res = x_bg.copy()
    resid.transform_inplace(nuisance_fp[bg_cal], x_bg_res)
    with threadpool_limits(limits=2):
        bg_pred_k = 0.5 * (
            reg0.predict(x_bg_res).astype(np.float64) + reg1.predict(x_bg_res).astype(np.float64)
        )
    cal_reg = dkrn1.KernelCreditLogitCalibrator(alpha=60.0).fit(
        bg_pred_k,
        nuisance_fp[bg_cal],
        slope_fp[bg_cal],
        relief_fp[bg_cal],
        sample_mean_yk=sample_mean_kernel,
        pop_mean_yk=pop_mean_kernel,
    )

    # Estimator 2: Subsurface Elkan prior-odds fault-core classifier (d_vis == 0 vs d_vis >= 3.0)
    clf_rows, y_clf = dprf1.sample_fold_training_rows(
        train_mask,
        visible_mask,
        fp_ids,
        mode="stratified_d3",
        max_pos=25_000,
        max_neg=75_000,
        seed=seed + 33,
    )
    n_pos_clf = int((y_clf == 1).sum())
    n_neg_clf = int((y_clf == 0).sum())
    x_clf = _assemble_subsurface_rows(clf_rows, base_mm, gvc_mm, sahg_mm, active_xvar, sub_cols_52)
    resid.transform_inplace(nuisance_fp[clf_rows], x_clf)
    with threadpool_limits(limits=2):
        clf0 = HistGradientBoostingClassifier(**XVAR1_HGB_CLF_PARAMS, random_state=seed + 303).fit(
            x_clf, y_clf
        )
        clf1 = HistGradientBoostingClassifier(**XVAR1_HGB_CLF_PARAMS, random_state=seed + 404).fit(
            x_clf, y_clf
        )
    del x_clf

    pi_train = float(max((train_mask & visible_mask).sum(), 1) / max(int(train_mask.sum()), 1))
    pi_sample = float(n_pos_clf / max(len(clf_rows), 1))
    with threadpool_limits(limits=2):
        bg_pred_c = 0.5 * (
            clf0.predict_proba(x_bg_res)[:, 1].astype(np.float64)
            + clf1.predict_proba(x_bg_res)[:, 1].astype(np.float64)
        )
    cal_clf = dkrn1.KernelCreditLogitCalibrator(alpha=60.0).fit(
        bg_pred_c,
        nuisance_fp[bg_cal],
        slope_fp[bg_cal],
        relief_fp[bg_cal],
        sample_mean_yk=pi_sample,
        pop_mean_yk=pi_train,
    )
    del x_bg, x_bg_res, bg_pred_k, bg_pred_c

    # Stream fold predictions in bounded memory chunks
    pred_rows = np.flatnonzero(predict_mask.ravel()[fp_ids])
    mu_grid = np.zeros(fp.shape, dtype=np.float32)
    q_grid = np.zeros(fp.shape, dtype=np.float32)
    with threadpool_limits(limits=2):
        for s in range(0, len(pred_rows), chunk_rows):
            ch = pred_rows[s : s + chunk_rows]
            x_ch = _assemble_subsurface_rows(ch, base_mm, gvc_mm, sahg_mm, active_xvar, sub_cols_52)
            resid.transform_inplace(nuisance_fp[ch], x_ch)
            raw_k = 0.5 * (
                reg0.predict(x_ch).astype(np.float64) + reg1.predict(x_ch).astype(np.float64)
            )
            raw_c = 0.5 * (
                clf0.predict_proba(x_ch)[:, 1].astype(np.float64)
                + clf1.predict_proba(x_ch)[:, 1].astype(np.float64)
            )
            mu_grid.ravel()[fp_ids[ch]] = cal_reg.transform(
                raw_k, nuisance_fp[ch], slope_fp[ch], relief_fp[ch]
            )
            q_grid.ravel()[fp_ids[ch]] = cal_clf.transform(
                raw_c, nuisance_fp[ch], slope_fp[ch], relief_fp[ch]
            )
            del x_ch, raw_k, raw_c

    del reg0, reg1, clf0, clf1
    gc.collect()

    # 8-azimuth ridge-coherence sharpening + visible-only apron quantile debiasing
    mu_sharp = dprf1.sharpen_ridge_coherence(mu_grid, predict_mask, half_len_px=4)
    q_sharp = dprf1.sharpen_ridge_coherence(q_grid, predict_mask, half_len_px=4)
    del mu_grid, q_grid
    mu_deb = dprf1.debiased_apron_surface(mu_sharp, predict_mask, visible_mask)
    q_deb = dprf1.debiased_apron_surface(q_sharp, predict_mask, visible_mask)
    del mu_sharp, q_sharp

    u_xvar = np.zeros(fp.shape, dtype=np.float32)
    u_xvar[predict_mask] = (0.55 * mu_deb[predict_mask] + 0.45 * q_deb[predict_mask]).astype(
        np.float32
    )
    del mu_deb, q_deb

    # Nuisance-residualized secondary concealed-texture / hydrothermal conduit gate
    n_base = base_mm.shape[1]
    n_gvc = gvc_mm.shape[1]
    r_halo = _residualized_rank01(
        gvc_mm[:, names52.index("gvc_geotherm_halo_2p5km") - n_base], nuisance_fp, bg_cal
    )
    r_alt = _residualized_rank01(
        sahg_mm[:, names52.index("sahg_r_alt") - n_base - n_gvc], nuisance_fp, bg_cal
    )
    if include_xvar1 and xvar_mm is not None:
        r_conc = _residualized_rank01(
            xvar_mm[:, xvar_names.index("xvar_mag_grav_concordance")], nuisance_fp, bg_cal
        )
        r_sg = _residualized_rank01(
            xvar_mm[:, xvar_names.index("xvar_spectral_roughness_step")], nuisance_fp, bg_cal
        )
        r_cb = _residualized_rank01(
            xvar_mm[:, xvar_names.index("xvar_cond_basement_step")], nuisance_fp, bg_cal
        )
        gate_fp = 0.25 + 0.75 * (
            0.30 * r_conc + 0.25 * r_sg + 0.20 * r_cb + 0.15 * r_alt + 0.10 * r_halo
        )
    else:
        r_bstep = _residualized_rank01(
            sahg_mm[:, names52.index("sahg_b_step") - n_base - n_gvc], nuisance_fp, bg_cal
        )
        gate_fp = 0.25 + 0.75 * (0.40 * r_bstep + 0.35 * r_alt + 0.25 * r_halo)

    m_tex = np.zeros(fp.shape, dtype=np.float32)
    m_tex.ravel()[fp_ids] = gate_fp.astype(np.float32)
    m_tex[~predict_mask] = 0.0
    u_tex = (u_xvar * m_tex).astype(np.float32)

    meta = {
        "include_xvar1": include_xvar1,
        "n_features": len(feat_names),
        "n_residualized_features": len(resid.models_),
        "n_reg_rows": int(len(reg_rows)),
        "n_clf_pos": int(n_pos_clf),
        "n_clf_neg": int(n_neg_clf),
        "pop_mean_kernel_credit": pop_mean_kernel,
        "sample_mean_kernel_credit": sample_mean_kernel,
        "pi_train": pi_train,
        "pi_sample": pi_sample,
    }
    return {"u_xvar": u_xvar, "u_tex": u_tex, "m_tex": m_tex}, meta


def ranking_surface_for_novelty(
    u_xvar: np.ndarray,
    u_tex: np.ndarray,
    fp: np.ndarray,
    catalogue: np.ndarray,
    *,
    primary_share: float = 0.65,
    catalogue_clearance_px: float = 2.0,
) -> np.ndarray:
    """Continuous pre-placement ranking surface gated strictly outside catalogue clearance."""
    dist_cat = distance_transform_edt(~catalogue)
    elig = fp & (~catalogue) & (dist_cat > catalogue_clearance_px)
    surf = np.zeros(fp.shape, dtype=np.float32)
    surf[elig] = (primary_share * u_xvar[elig] + (1.0 - primary_share) * u_tex[elig]).astype(
        np.float32
    )
    return surf
