"""Preregistered H24-DPRF1: Dual-Partition OOF Relief-Conditioned Hydrothermal-Structural Fusion.

Implements the locked specification in ``knowledge/19_preregistered_DPRF1_2026-10-26.md``:
1. 52-channel feature stack combining the 30 scale-separated prepared base channels,
   18 label-free OpenEI GDR INGENIOUS hydrothermal / Miller-Singh tilt / 8-azimuth
   lineament channels (``gems.gvc``), and 4 modality-aware ``SAHG1`` conduit channels
   (``sahg_g_sat``, ``sahg_r_alt``, ``sahg_b_step``, ``sahg_h_conduit``) with native
   ``NaN`` sensor-gap routing.
2. Selective Non-Topographic Nuisance Residualization: fits ``NuisanceResidualizer``
   strictly on observed training-fold background pixels for the 9 regional survey /
   access-confounded channels only, leaving local topographic, lineament, and
   point-source hydrothermal residuals uncorrupted.
3. Relief-Conditioned LiDAR-Gap Log-Odds Calibration: partial nuisance debiasing
   controlling for topographic relief, followed by 3-tier relief-conditioned
   quantile alignment between ``~has_lidar`` and ``has_lidar`` domains.
4. 8-Azimuth Out-of-Fold Ridge-Coherence Sharpening & Two-Regime 300 m Submodular
   Kernel Allocation (68% primary ridge + 32% concealed hydrothermal-subsurface conduit).
5. Dual-Partition Stitched Out-of-Fold (Quadrant + 45-degree Rotated Diamond)
   full-footprint inference with Visible-Catalogue Apron Quantile Debiasing.
"""

from __future__ import annotations

import gc
import heapq
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt
from scipy.ndimage import label as ndi_label
from scipy.special import expit, logit
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import Ridge
from threadpoolctl import threadpool_limits

from . import gvc, rshg1, sahg1
from .metric import KERNEL_OFFSETS, RADIUS_PX
from .residualize import NuisanceResidualizer

SAHG4_NAMES: tuple[str, ...] = (
    "sahg_g_sat",
    "sahg_r_alt",
    "sahg_b_step",
    "sahg_h_conduit",
)

SELECTIVE_RESID_NAMES: frozenset[str] = frozenset(
    {
        "rtp",
        "tmi",
        "iso_grav_anom",
        "depth_to_base_surf",
        "cond_surf",
        "gvc_rad_k_thk_alter",
        "gvc_rad_uth_excess",
        "sahg_r_alt",
        "sahg_b_step",
    }
)

UPFLOW_CONDUIT_NAMES: tuple[str, ...] = (
    "gvc_paleo_sinter_logd",
    "gvc_probe2m_anom_1p5km",
    "gvc_spring_hot_logd",
    "gvc_geotherm_halo_2p5km",
    "sahg_h_conduit",
)

SUBSURFACE_STEP_NAMES: tuple[str, ...] = (
    "gvc_tmi_tilt_grad",
    "gvc_grav_tilt_grad",
    "gvc_basement_step_grad",
    "gvc_grav_mag_coalign_2km",
    "sahg_b_step",
)

STEEP_SLOPE_NAME = "det_elev_slope"
LOCAL_RELIEF_NAME = "det_local_relief"


def build_sahg4_memmap(
    root: Path,
    base_mm: np.ndarray,
    base_names: list[str],
    footprint: np.ndarray,
    out_path: Path,
) -> tuple[np.ndarray, list[str]]:
    """Compute or load the 4 modality-aware SAHG1 channels (NaN outside sensor support)."""
    fp = np.asarray(footprint, dtype=bool)
    fp_ids = np.flatnonzero(fp.ravel())
    n_fp = len(fp_ids)
    if out_path.exists():
        mm = np.load(out_path, mmap_mode="r")
        if mm.shape == (n_fp, len(SAHG4_NAMES)) and mm.dtype == np.float32:
            return mm, list(SAHG4_NAMES)

    lidar_path = root / "data/external/lidar_scarp_features_u8.tif"
    lidar_meta = _read_json(lidar_path.with_name("lidar_scarp_features.json"))
    rad_path = root / "data/external/geodawn_rad_u8.tif"
    rad_meta = _read_json(rad_path.with_name("geodawn_rad.json"))
    ext_path = root / "data/external/geodawn_extensions_u8.tif"
    ext_meta = _read_json(ext_path.with_name("geodawn_extensions.json"))

    def unpack_base(col_name: str) -> np.ndarray:
        idx = base_names.index(col_name)
        grid = np.full(fp.shape, np.nan, dtype=np.float32)
        grid.ravel()[fp_ids] = base_mm[:, idx]
        return grid

    det_elev = unpack_base("det_elev")
    lidar_bands: dict[str, np.ndarray] = {}
    with rasterio.open(lidar_path) as ds:
        for bname in sahg1.LIDAR_SPECS:
            lidar_bands[bname] = ds.read(lidar_meta["bands"].index(bname) + 1)
    g_sat = rshg1.compute_modality_sahg1_g_sat(lidar_bands, det_elev, fp)
    del lidar_bands
    gc.collect()

    rad_bands: dict[str, np.ndarray] = {}
    with rasterio.open(rad_path) as ds:
        for bname in sahg1.RAD_BANDS:
            rad_bands[bname] = ds.read(rad_meta["channels"].index(bname) + 1)
    ext_bands: dict[str, np.ndarray] = {}
    with rasterio.open(ext_path) as ds:
        for bname in sahg1.EXT_BANDS:
            ext_bands[bname] = ds.read(ext_meta["channels"].index(bname) + 1)
    r_alt = rshg1.compute_modality_sahg1_r_alt(rad_bands, ext_bands, fp)
    del rad_bands, ext_bands
    gc.collect()

    geophys_bands: dict[str, np.ndarray] = {"det_elev": det_elev}
    for gname in sahg1.GEOPHYS_BANDS:
        if gname != "det_elev":
            geophys_bands[gname] = unpack_base(gname)
    b_step = rshg1.compute_modality_sahg1_b_step(geophys_bands, fp)
    del geophys_bands, det_elev
    gc.collect()

    both_ok = np.isfinite(r_alt) & np.isfinite(b_step)
    h_conduit = np.where(
        both_ok,
        np.sqrt(np.maximum(np.where(both_ok, r_alt * b_step, 0.0), 0.0)),
        np.nan,
    ).astype(np.float32)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    mm_w = np.lib.format.open_memmap(
        out_path, mode="w+", dtype=np.float32, shape=(n_fp, len(SAHG4_NAMES))
    )
    mm_w[:, 0] = g_sat.ravel()[fp_ids]
    mm_w[:, 1] = r_alt.ravel()[fp_ids]
    mm_w[:, 2] = b_step.ravel()[fp_ids]
    mm_w[:, 3] = h_conduit.ravel()[fp_ids]
    mm_w.flush()
    del g_sat, r_alt, b_step, h_conduit, mm_w
    gc.collect()
    return np.load(out_path, mmap_mode="r"), list(SAHG4_NAMES)


def _read_json(path: Path) -> dict[str, Any]:
    import json

    return json.loads(path.read_text())


def read_stack_rows(
    rows: np.ndarray,
    base_mm: np.ndarray,
    gvc_mm: np.ndarray,
    sahg_mm: np.ndarray,
    extra_mm: np.ndarray | None = None,
) -> np.ndarray:
    """Assemble a float32 block from the stack memmaps, optionally with lane extra channels.

    Column order is always ``[base (30), gvc (18), sahg (4), extra...]`` so the
    52-channel DPRF1 layout is a strict prefix; ``extra_mm=None`` reproduces the
    original DPRF1 behaviour byte-for-byte.
    """
    n = len(rows)
    n_extra = 0 if extra_mm is None else int(extra_mm.shape[1])
    out = np.empty((n, 52 + n_extra), dtype=np.float32)
    out[:, :30] = base_mm[rows]
    out[:, 30:48] = gvc_mm[rows]
    out[:, 48:52] = sahg_mm[rows]
    if extra_mm is not None:
        out[:, 52:] = extra_mm[rows]
    return out


def read_52ch_rows(
    rows: np.ndarray,
    base_mm: np.ndarray,
    gvc_mm: np.ndarray,
    sahg_mm: np.ndarray,
) -> np.ndarray:
    """Assemble a ``(len(rows), 52)`` float32 block from the three memmaps."""
    return read_stack_rows(rows, base_mm, gvc_mm, sahg_mm)


class SelectiveNonTopographicResidualizer:
    """Residualize only regional/survey-confounded channels on training background; leave local channels untouched."""

    def __init__(
        self,
        target_indices: list[int] | np.ndarray,
        *,
        alpha: float = 100.0,
        distance_columns: int = 2,
    ):
        self.target_indices = np.asarray(
            sorted(set(int(i) for i in target_indices)), dtype=np.int64
        )
        self.alpha = float(alpha)
        self.distance_columns = int(distance_columns)
        self._basis_helper = NuisanceResidualizer(
            alpha=self.alpha, distance_columns=self.distance_columns
        )
        self.medians_: dict[int, float] = {}
        self.scales_: dict[int, float] = {}
        self.models_: dict[int, Ridge] = {}

    def fit(
        self, nuisance: np.ndarray, features: np.ndarray
    ) -> SelectiveNonTopographicResidualizer:
        c = np.asarray(nuisance, dtype=np.float32)
        x = np.asarray(features, dtype=np.float32)
        if c.ndim != 2 or x.ndim != 2 or len(c) != len(x):
            raise ValueError("Aligned 2D nuisance and feature matrices required")
        if c.shape[1] < self.distance_columns or not np.isfinite(c).all():
            raise ValueError("Finite nuisance matrix with >= distance_columns required")
        self._basis_helper.n_nuisance = c.shape[1]
        basis_all = self._basis_helper._basis(c, fit=True)

        self.medians_.clear()
        self.scales_.clear()
        self.models_.clear()
        for j in self.target_indices.tolist():
            col = x[:, j]
            obs = np.isfinite(col)
            if int(obs.sum()) < 64:
                continue
            vals = col[obs]
            med = float(np.median(vals))
            mad = float(1.4826 * np.median(np.abs(vals - med)))
            std = float(np.std(vals))
            sc = max(mad if mad > 1e-6 else std, 1e-6)
            z_obs = np.clip((vals - med) / sc, -8.0, 8.0).astype(np.float32)
            self.medians_[j] = med
            self.scales_[j] = sc
            self.models_[j] = Ridge(alpha=self.alpha).fit(basis_all[obs], z_obs)
        return self

    def transform_inplace(self, nuisance: np.ndarray, features: np.ndarray) -> np.ndarray:
        """Overwrite only ``self.target_indices`` with nuisance-residualized values, preserving NaNs."""
        if not self.models_:
            return features
        c = np.asarray(nuisance, dtype=np.float32)
        if len(c) != len(features):
            raise ValueError("Nuisance/feature row count mismatch")
        basis = self._basis_helper._basis(c, fit=False)
        for j, model in self.models_.items():
            col = features[:, j]
            obs = np.isfinite(col)
            if not obs.any():
                continue
            med = self.medians_[j]
            sc = self.scales_[j]
            z = np.clip((col[obs] - med) / sc, -8.0, 8.0).astype(np.float32)
            res = (z - model.predict(basis[obs])).astype(np.float32)
            col_new = np.full(len(col), np.nan, dtype=np.float32)
            col_new[obs] = res
            features[:, j] = col_new
        return features


class ReliefConditionedCalibrator:
    """Partial-relief nuisance log-odds debiaser + 3-tier relief-conditioned LiDAR-gap calibrator."""

    def __init__(self, alpha: float = 100.0, distance_columns: int = 2):
        self.alpha = float(alpha)
        self.distance_columns = int(distance_columns)
        self._basis_helper = NuisanceResidualizer(
            alpha=self.alpha, distance_columns=self.distance_columns
        )
        self.slope_med_: float = 0.0
        self.slope_iqr_: float = 1.0
        self.rel_med_: float = 0.0
        self.rel_iqr_: float = 1.0
        self.tier_cuts_: tuple[float, float] = (-0.25, 0.25)
        self.nuis_coef_: np.ndarray | None = None
        self.nuis_offset_: float = 0.0
        self.tier_stats_: dict[int, tuple[float, float, float, float]] = {}

    def _relief_score(self, slope: np.ndarray, local_relief: np.ndarray) -> np.ndarray:
        s_safe = np.where(np.isfinite(slope), np.maximum(slope, 0.0), self.slope_med_)
        r_safe = np.where(np.isfinite(local_relief), np.abs(local_relief), self.rel_med_)
        zs = np.clip((s_safe - self.slope_med_) / self.slope_iqr_, -6.0, 6.0)
        zr = np.clip((r_safe - self.rel_med_) / self.rel_iqr_, -6.0, 6.0)
        return (0.5 * zs + 0.5 * zr).astype(np.float32)

    def _assign_tiers(self, rscore: np.ndarray) -> np.ndarray:
        t0, t1 = self.tier_cuts_
        tiers = np.zeros(len(rscore), dtype=np.int8)
        tiers[rscore >= t0] = 1
        tiers[rscore >= t1] = 2
        return tiers

    def fit(
        self,
        prob_bg: np.ndarray,
        has_lidar_bg: np.ndarray,
        nuisance_bg: np.ndarray,
        slope_bg: np.ndarray,
        local_relief_bg: np.ndarray,
    ) -> ReliefConditionedCalibrator:
        p = np.clip(np.asarray(prob_bg, dtype=np.float64), 1e-5, 1.0 - 1e-5)
        ell = logit(p).astype(np.float32)
        hl = np.asarray(has_lidar_bg, dtype=bool)
        c = np.asarray(nuisance_bg, dtype=np.float32)

        s_obs = slope_bg[np.isfinite(slope_bg)]
        r_obs = np.abs(local_relief_bg[np.isfinite(local_relief_bg)])
        self.slope_med_ = float(np.median(s_obs)) if len(s_obs) else 0.0
        s_q25, s_q75 = np.percentile(s_obs, [25.0, 75.0]) if len(s_obs) else (0.0, 1.0)
        self.slope_iqr_ = max(float(s_q75 - s_q25), 1e-4)

        self.rel_med_ = float(np.median(r_obs)) if len(r_obs) else 0.0
        r_q25, r_q75 = np.percentile(r_obs, [25.0, 75.0]) if len(r_obs) else (0.0, 1.0)
        self.rel_iqr_ = max(float(r_q75 - r_q25), 1e-4)

        rscore = self._relief_score(slope_bg, local_relief_bg)
        q33, q67 = np.percentile(rscore, [33.33, 66.67])
        self.tier_cuts_ = (float(q33), float(q67))

        # Partial ridge regression: ell ~ [nuisance_basis, rscore, rscore^2, has_lidar]
        # Subtract ONLY the partial nuisance component so relief contrast is preserved!
        self._basis_helper.n_nuisance = c.shape[1]
        b_nuis = self._basis_helper._basis(c, fit=True)
        k_nuis = b_nuis.shape[1]
        design = np.column_stack([b_nuis, rscore, rscore * rscore, hl.astype(np.float32)]).astype(
            np.float32
        )
        reg = Ridge(alpha=self.alpha).fit(design, ell)
        self.nuis_coef_ = reg.coef_[:k_nuis].astype(np.float32)
        nuis_eff = b_nuis @ self.nuis_coef_
        self.nuis_offset_ = float(np.mean(nuis_eff))
        debiased = ell - (nuis_eff - self.nuis_offset_)

        # Fit 3-tier relief-conditioned median and (p99 - p50) spread on has_lidar vs ~has_lidar
        tiers = self._assign_tiers(rscore)
        g_med_l = (
            float(np.median(debiased[hl])) if int(hl.sum()) >= 32 else float(np.median(debiased))
        )
        g_spr_l = (
            max(float(np.percentile(debiased[hl], 99.0) - g_med_l), 0.25)
            if int(hl.sum()) >= 32
            else 1.0
        )
        g_med_g = float(np.median(debiased[~hl])) if int((~hl).sum()) >= 32 else g_med_l
        g_spr_g = (
            max(float(np.percentile(debiased[~hl], 99.0) - g_med_g), 0.25)
            if int((~hl).sum()) >= 32
            else g_spr_l
        )

        self.tier_stats_.clear()
        for t in (0, 1, 2):
            m_l = hl & (tiers == t)
            m_g = (~hl) & (tiers == t)
            if int(m_l.sum()) >= 100:
                med_l = float(np.median(debiased[m_l]))
                spr_l = max(float(np.percentile(debiased[m_l], 99.0) - med_l), 0.25)
            else:
                med_l, spr_l = g_med_l, g_spr_l
            if int(m_g.sum()) >= 100:
                med_g = float(np.median(debiased[m_g]))
                spr_g = max(float(np.percentile(debiased[m_g], 99.0) - med_g), 0.25)
            else:
                med_g, spr_g = g_med_g, g_spr_g
            self.tier_stats_[t] = (med_l, spr_l, med_g, spr_g)
        return self

    def transform(
        self,
        prob: np.ndarray,
        has_lidar: np.ndarray,
        nuisance: np.ndarray,
        slope: np.ndarray,
        local_relief: np.ndarray,
    ) -> np.ndarray:
        if self.nuis_coef_ is None:
            raise RuntimeError("Call fit before transform")
        p = np.clip(np.asarray(prob, dtype=np.float64), 1e-5, 1.0 - 1e-5)
        ell = logit(p).astype(np.float32)
        hl = np.asarray(has_lidar, dtype=bool)
        c = np.asarray(nuisance, dtype=np.float32)
        b_nuis = self._basis_helper._basis(c, fit=False)
        debiased = ell - ((b_nuis @ self.nuis_coef_) - self.nuis_offset_)

        if (~hl).any():
            rscore = self._relief_score(slope, local_relief)
            tiers = self._assign_tiers(rscore)
            for t in (0, 1, 2):
                m_g = (~hl) & (tiers == t)
                if not m_g.any():
                    continue
                med_l, spr_l, med_g, spr_g = self.tier_stats_[t]
                z_gap = (debiased[m_g] - med_g) / spr_g
                debiased[m_g] = med_l + spr_l * z_gap
        return np.clip(expit(debiased), 0.0, 1.0).astype(np.float32)


class TrainQuantileGateScaler:
    """Fit robust channel medians/IQRs strictly on training rows for Regime-B conduit gates."""

    def __init__(self, col_indices: dict[str, int]):
        self.col_indices = dict(col_indices)
        self.stats_: dict[str, tuple[float, float]] = {}

    def fit(self, x_train: np.ndarray) -> TrainQuantileGateScaler:
        self.stats_.clear()
        for name, idx in self.col_indices.items():
            col = x_train[:, idx]
            obs = col[np.isfinite(col)]
            if len(obs) >= 32:
                med = float(np.median(obs))
                q25, q75 = np.percentile(obs, [25.0, 75.0])
                iqr = max(float(q75 - q25), 1e-5)
            else:
                med, iqr = 0.0, 1.0
            self.stats_[name] = (med, iqr)
        return self

    def score_regime_b_multiplier(
        self, x_rows: np.ndarray, *, extra_subsurface_names: tuple[str, ...] = ()
    ) -> np.ndarray:
        """Compute ``(0.30 + 0.70*H_upflow) * (0.30 + 0.70*B_sub) * (1.0 - 0.50*S_steep)``.

        ``extra_subsurface_names`` (lane extension, e.g. EUL1 Euler-contact channels)
        are averaged into ``B_sub`` alongside ``SUBSURFACE_STEP_NAMES``; the default
        empty tuple reproduces the original DPRF1 multiplier exactly.
        """
        n = len(x_rows)

        def sig(name: str) -> np.ndarray:
            idx = self.col_indices[name]
            med, iqr = self.stats_[name]
            col = x_rows[:, idx]
            obs = np.isfinite(col)
            out = np.full(n, 0.5, dtype=np.float32)
            if obs.any():
                z = np.clip((col[obs] - med) / iqr, -6.0, 6.0)
                out[obs] = expit(z).astype(np.float32)
            return out

        h_up = np.zeros(n, dtype=np.float32)
        for nm in UPFLOW_CONDUIT_NAMES:
            h_up += sig(nm)
        h_up /= float(len(UPFLOW_CONDUIT_NAMES))

        sub_names = (*SUBSURFACE_STEP_NAMES, *extra_subsurface_names)
        b_sub = np.zeros(n, dtype=np.float32)
        for nm in sub_names:
            b_sub += sig(nm)
        b_sub /= float(len(sub_names))

        s_steep = sig(STEEP_SLOPE_NAME)
        mult = (0.30 + 0.70 * h_up) * (0.30 + 0.70 * b_sub) * (1.0 - 0.50 * s_steep)
        return mult.astype(np.float32)


def sharpen_ridge_coherence(
    prob_2d: np.ndarray, valid_mask: np.ndarray, *, half_len_px: int = 4
) -> np.ndarray:
    """8-azimuth (900 m) ridge-coherence sharpening computed strictly inside ``valid_mask``."""
    v = np.asarray(valid_mask, dtype=bool)
    if not v.any():
        return np.zeros(prob_2d.shape, dtype=np.float32)
    p_in = np.where(v & np.isfinite(prob_2d), np.clip(prob_2d, 0.0, 1.0), 0.0).astype(np.float32)
    filled = gvc._nearest_fill(p_in, v)

    h, w = filled.shape
    pad = int(half_len_px)
    p_pad = np.pad(filled, pad, mode="edge")
    t = np.arange(-half_len_px, half_len_px + 1, dtype=np.float64)
    inv_n = np.float32(1.0 / len(t))

    r_max = np.full((h, w), -np.inf, dtype=np.float32)
    r_sum = np.zeros((h, w), dtype=np.float32)
    for k in range(8):
        theta = k * (np.pi / 8.0)
        dys = np.rint(t * np.sin(theta)).astype(np.int32)
        dxs = np.rint(t * np.cos(theta)).astype(np.int32)
        acc = np.zeros((h, w), dtype=np.float32)
        for dy, dx in zip(dys.tolist(), dxs.tolist()):
            acc += p_pad[pad + dy : pad + dy + h, pad + dx : pad + dx + w]
        resp = acc * inv_n
        np.maximum(r_max, resp, out=r_max)
        r_sum += resp
    r_mean = r_sum * np.float32(0.125)
    delta_r = np.maximum(r_max - r_mean, 0.0)
    p99 = max(float(np.percentile(delta_r[v], 99.0)), 1e-6)
    boost = np.clip(delta_r / np.float32(p99), 0.0, 1.5)
    out = np.where(v, np.clip(0.72 * p_in + 0.28 * p_in * boost, 0.0, 1.0), 0.0)
    return out.astype(np.float32)


def debiased_apron_surface(
    prob_2d: np.ndarray,
    valid_mask: np.ndarray,
    visible_faults: np.ndarray,
    *,
    near_lo_px: float = 2.0,
    near_hi_px: float = 9.0,
    far_ref_px: float = 12.0,
) -> np.ndarray:
    """Map near-catalogue (2-9 px) quantiles onto the out-of-fold far-field (>12 px) distribution.

    On ``SegmentHoldout(buffer_px=15)``, ``min(d_vis) == 16.0 px > 9.0 px`` everywhere inside
    ``fold['valid']``, so ``near_belt`` is naturally empty (exact identity). On full-footprint
    stitched-OOF inference, this prevents residual near-catalogue apron inflation while
    strictly preserving internal spatial rank order inside ``2 < d_cat <= 9 px``.
    """
    out = np.asarray(prob_2d, dtype=np.float32).copy()
    vis = np.asarray(visible_faults, dtype=bool)
    val = np.asarray(valid_mask, dtype=bool)
    if not vis.any() or not val.any():
        return out
    d_vis = distance_transform_edt(~vis)
    near_mask = val & (~vis) & (d_vis > near_lo_px) & (d_vis <= near_hi_px)
    far_mask = val & (~vis) & (d_vis > far_ref_px)
    n_near = int(near_mask.sum())
    n_far = int(far_mask.sum())
    if n_near < 100 or n_far < 500:
        return out

    near_vals = out[near_mask]
    far_vals = out[far_mask]
    q_grid = np.linspace(0.0, 1.0, 2001, dtype=np.float64)
    far_q = np.quantile(far_vals.astype(np.float64), q_grid)
    order = np.argsort(near_vals, kind="mergesort")
    ranks = np.empty(n_near, dtype=np.float64)
    ranks[order] = np.linspace(0.0, 1.0, n_near, dtype=np.float64)
    mapped = np.interp(ranks, q_grid, far_q).astype(np.float32)
    # Apply only downward/distribution-matching cap when near-apron exceeds far-field quantiles
    out[near_mask] = np.minimum(near_vals, mapped)
    return out


def _submodular_stage(
    prob_2d: np.ndarray,
    valid_2d: np.ndarray,
    vis_2d: np.ndarray,
    *,
    target_add: int,
    min_spacing_px: float,
    catalogue_clearance_px: float,
    existing_dots: np.ndarray | None = None,
) -> np.ndarray:
    """Minoux (1978) lazy-greedy 300 m kernel coverage allocator, optionally conditioned on ``existing_dots``."""
    h, w = prob_2d.shape
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
    eligible &= np.isfinite(prob_2d) & (prob_2d > 0.0)

    cand_ids = np.flatnonzero(eligible.ravel())
    if not len(cand_ids):
        return out

    pool_cap = min(len(cand_ids), max(target_add * 10, 140_000))
    cand_scores = prob_2d.ravel()[cand_ids]
    if len(cand_ids) > pool_cap:
        part = np.argpartition(-cand_scores, pool_cap - 1)[:pool_cap]
        cand_ids = cand_ids[part]
        cand_scores = cand_scores[part]
    order = np.lexsort((cand_ids, -cand_scores))
    cand_ids = cand_ids[order]

    pad = int(np.ceil(max(RADIUS_PX, min_spacing_px))) + 1
    hp, wp = h + 2 * pad, w + 2 * pad

    active_mass = np.where(
        valid_2d & (~vis_2d) & np.isfinite(prob_2d), np.clip(prob_2d, 0.0, 1.0), 0.0
    )
    p_pad = np.zeros((hp, wp), dtype=np.float32)
    p_pad[pad : pad + h, pad : pad + w] = active_mass

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

    heap: list[tuple[float, int, int, int, int]] = []
    for i in range(len(cand_ids)):
        c0 = int(centers[i])
        if blocked_1d[c0]:
            continue
        idx29 = c0 + k_offs_1d
        rem = np.maximum(k_vals - cov_1d[idx29], 0.0)
        ub = float(np.dot(p_1d[idx29], rem))
        if ub > 0.0:
            heap.append((-ub, int(i), c0, int(cy[i]), int(cx[i])))
    heapq.heapify(heap)

    added = 0
    while heap and added < target_add:
        neg_ub, rank, center, ry, rx = heapq.heappop(heap)
        if blocked_1d[center]:
            continue
        idx29 = center + k_offs_1d
        rem = k_vals - cov_1d[idx29]
        np.maximum(rem, 0.0, out=rem)
        gain = float(np.dot(p_1d[idx29], rem))
        if gain <= 0.0:
            continue
        if heap and (-gain > heap[0][0] + 1e-12):
            heapq.heappush(heap, (-gain, rank, center, ry, rx))
            continue
        out[ry, rx] = 1.0
        cov_1d[idx29] = np.maximum(cov_1d[idx29], k_vals)
        blocked_1d[center + excl_offs_1d] = True
        added += 1

    return out


def two_regime_submodular_allocate(
    p_sharp_2d: np.ndarray,
    p_conduit_2d: np.ndarray,
    valid_2d: np.ndarray,
    visible_2d: np.ndarray,
    *,
    budget: int,
    primary_share: float = 0.68,
    min_spacing_px: float = 2.8,
    catalogue_clearance_px: float = 2.0,
) -> np.ndarray:
    """Allocate ``primary_share`` on ``p_sharp_2d`` and ``1 - primary_share`` on ``p_conduit_2d``."""
    if budget <= 0:
        return np.zeros(p_sharp_2d.shape, dtype=np.float32)
    b_a = int(round(float(primary_share) * budget))
    b_a = max(0, min(budget, b_a))
    dots_a = _submodular_stage(
        p_sharp_2d,
        valid_2d,
        visible_2d,
        target_add=b_a,
        min_spacing_px=min_spacing_px,
        catalogue_clearance_px=catalogue_clearance_px,
        existing_dots=None,
    )
    b_b = budget - int((dots_a > 0.5).sum())
    if b_b <= 0:
        return dots_a
    return _submodular_stage(
        p_conduit_2d,
        valid_2d,
        visible_2d,
        target_add=b_b,
        min_spacing_px=min_spacing_px,
        catalogue_clearance_px=catalogue_clearance_px,
        existing_dots=dots_a,
    )


def make_rotated45_segment_folds(
    footprint: np.ndarray, labels: np.ndarray, *, buffer_px: int = 15
) -> list[dict[str, Any]]:
    """Construct 45-degree rotated diamond folds with identical whole-component hiding as ``SegmentHoldout``."""
    fp = np.asarray(footprint, dtype=bool)
    lab = np.asarray(labels, dtype=bool)
    ys, xs = np.nonzero(fp)
    ym = float(np.median(ys))
    xm = float(np.median(xs))
    yy, xx = np.indices(fp.shape, dtype=np.float32)
    u = (yy - ym) + (xx - xm)
    v = (yy - ym) - (xx - xm)
    sector_defs = [
        ("North_Diamond", (u < 0) & (v < 0)),
        ("East_Diamond", (u >= 0) & (v < 0)),
        ("West_Diamond", (u < 0) & (v >= 0)),
        ("South_Diamond", (u >= 0) & (v >= 0)),
    ]
    components, _ = ndi_label(lab, structure=np.ones((3, 3), dtype=int))
    folds: list[dict[str, Any]] = []
    for fid, (name, raw_sec) in enumerate(sector_defs):
        valid = fp & raw_sec
        collar = distance_transform_edt(~valid) <= buffer_px
        hidden_ids = np.unique(components[collar & lab])
        hidden_ids = hidden_ids[hidden_ids > 0]
        hidden = lab & np.isin(components, hidden_ids)
        visible = lab & (~hidden)
        truth = hidden & valid
        train = fp & (distance_transform_edt(~(valid | hidden)) > buffer_px)
        folds.append(
            {
                "id": fid,
                "name": name,
                "valid": valid,
                "train": train,
                "visible": visible,
                "truth": truth,
            }
        )
    return folds


def sample_fold_training_rows(
    train_mask: np.ndarray,
    visible_mask: np.ndarray,
    fp_ids: np.ndarray,
    *,
    mode: str,
    max_pos: int = 25_000,
    max_neg: int = 75_000,
    seed: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Sample leak-free training rows from ``fold['train']`` using ``fold['visible']`` ONLY."""
    dist_vis = distance_transform_edt(~visible_mask)
    pos_mask = train_mask & visible_mask
    pos_pool = np.flatnonzero(pos_mask.ravel()[fp_ids])
    rng = np.random.default_rng(seed)
    if len(pos_pool) > max_pos:
        pos_sel = rng.choice(pos_pool, size=max_pos, replace=False)
        pos_sel.sort()
    else:
        pos_sel = pos_pool

    if mode == "stratified_d3":
        near_mask = train_mask & (~visible_mask) & (dist_vis >= 3.0) & (dist_vis < 10.0)
        far_mask = train_mask & (~visible_mask) & (dist_vis >= 10.0)
        near_pool = np.flatnonzero(near_mask.ravel()[fp_ids])
        far_pool = np.flatnonzero(far_mask.ravel()[fp_ids])
        n_near_target = int(round(0.35 * max_neg))
        take_near = min(len(near_pool), n_near_target)
        take_far = min(len(far_pool), max_neg - take_near)
        s_near = (
            rng.choice(near_pool, size=take_near, replace=False)
            if len(near_pool) > take_near
            else near_pool
        )
        s_far = (
            rng.choice(far_pool, size=take_far, replace=False)
            if len(far_pool) > take_far
            else far_pool
        )
        neg_sel = np.sort(np.concatenate([s_near, s_far]))
    elif mode == "deadzone_d9":
        neg_mask = train_mask & (~visible_mask) & (dist_vis >= 9.0)
        neg_pool = np.flatnonzero(neg_mask.ravel()[fp_ids])
        neg_sel = (
            np.sort(rng.choice(neg_pool, size=max_neg, replace=False))
            if len(neg_pool) > max_neg
            else neg_pool
        )
    else:
        raise ValueError(f"Unknown negative sampling mode: {mode!r}")

    if len(pos_sel) < 100 or len(neg_sel) < 500:
        raise RuntimeError("Insufficient training positives or negatives in fold")

    rows = np.concatenate([pos_sel, neg_sel])
    y = np.concatenate(
        [np.ones(len(pos_sel), dtype=np.int8), np.zeros(len(neg_sel), dtype=np.int8)]
    )
    return rows, y


def fit_and_predict_fold(
    base_mm: np.ndarray,
    gvc_mm: np.ndarray,
    sahg_mm: np.ndarray,
    nuisance_fp: np.ndarray,
    all_names: list[str],
    fp: np.ndarray,
    fp_ids: np.ndarray,
    *,
    train_mask: np.ndarray,
    visible_mask: np.ndarray,
    predict_mask: np.ndarray,
    neg_mode: str,
    seed: int,
    chunk_size: int = 200_000,
    extra_mm: np.ndarray | None = None,
    regime_b_extra_names: tuple[str, ...] = (),
    selective_extra_names: tuple[str, ...] = (),
    return_legacy_conduit: bool = False,
) -> (
    tuple[np.ndarray, np.ndarray, dict[str, Any]]
    | tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, Any]]
):
    """Fit selective residualizer, 2-seed HGB, relief-conditioned calibrator, and predict ``(p_sharp, p_conduit)``.

    Lane-extension parameters (defaults reproduce DPRF1 exactly): ``extra_mm`` adds
    trailing physical channels listed at the end of ``all_names``;
    ``regime_b_extra_names`` are averaged into the Regime-B subsurface multiplier;
    ``selective_extra_names`` join the selective-residualization set.
    """
    n_extra = 0 if extra_mm is None else int(extra_mm.shape[1])
    if len(all_names) != 52 + n_extra:
        raise ValueError("all_names must list the 52 DPRF1 channels plus any extra channels")
    sel_names = sorted(set(SELECTIVE_RESID_NAMES) | set(selective_extra_names))
    sel_indices = [all_names.index(nm) for nm in sel_names]
    gate_col_map = {
        nm: all_names.index(nm)
        for nm in (
            *UPFLOW_CONDUIT_NAMES,
            *SUBSURFACE_STEP_NAMES,
            STEEP_SLOPE_NAME,
            *regime_b_extra_names,
        )
    }
    g_sat_idx = all_names.index("sahg_g_sat")
    slope_idx = all_names.index(STEEP_SLOPE_NAME)
    rel_idx = all_names.index(LOCAL_RELIEF_NAME)

    # 1. Sample training positives + negatives first so background calibration rows are 100% disjoint
    tr_rows, y_tr = sample_fold_training_rows(
        train_mask, visible_mask, fp_ids, mode=neg_mode, max_pos=25_000, max_neg=75_000, seed=seed
    )

    # 2. Fit SelectiveNonTopographicResidualizer & TrainQuantileGateScaler on 35,000 disjoint train bg rows
    bg_mask = train_mask & (~visible_mask)
    bg_pool_all = np.flatnonzero(bg_mask.ravel()[fp_ids])
    bg_disjoint = np.setdiff1d(bg_pool_all, tr_rows, assume_unique=False)
    if len(bg_disjoint) < 5_000:
        bg_disjoint = bg_pool_all
    rng_bg = np.random.default_rng(seed + 41)
    bg_sel = np.sort(rng_bg.choice(bg_disjoint, size=min(35_000, len(bg_disjoint)), replace=False))
    x_bg = read_stack_rows(bg_sel, base_mm, gvc_mm, sahg_mm, extra_mm)
    c_bg = np.asarray(nuisance_fp[bg_sel], dtype=np.float32)

    gate_scaler = TrainQuantileGateScaler(gate_col_map).fit(x_bg)
    resid = SelectiveNonTopographicResidualizer(sel_indices, alpha=100.0).fit(c_bg, x_bg)
    x_bg_res = resid.transform_inplace(c_bg, x_bg.copy())

    x_tr = read_stack_rows(tr_rows, base_mm, gvc_mm, sahg_mm, extra_mm)
    c_tr = np.asarray(nuisance_fp[tr_rows], dtype=np.float32)
    resid.transform_inplace(c_tr, x_tr)

    models: list[HistGradientBoostingClassifier] = []
    with threadpool_limits(limits=2):
        for s_off in (100, 200):
            clf = HistGradientBoostingClassifier(
                max_iter=190,
                learning_rate=0.055,
                max_leaf_nodes=31,
                min_samples_leaf=80,
                l2_regularization=2.5,
                early_stopping=False,
                random_state=seed + s_off,
            )
            clf.fit(x_tr, y_tr)
            models.append(clf)

        # 3. Fit ReliefConditionedCalibrator on training background predictions
        p_bg_raw = 0.5 * (
            models[0].predict_proba(x_bg_res)[:, 1] + models[1].predict_proba(x_bg_res)[:, 1]
        )
        calibrator = ReliefConditionedCalibrator(alpha=100.0).fit(
            p_bg_raw,
            has_lidar_bg=np.isfinite(x_bg[:, g_sat_idx]),
            nuisance_bg=c_bg,
            slope_bg=x_bg[:, slope_idx],
            local_relief_bg=x_bg[:, rel_idx],
        )
        del x_tr, c_tr, x_bg, x_bg_res, c_bg, p_bg_raw
        gc.collect()

        # 4. Chunked prediction on predict_mask
        pred_rows = np.flatnonzero(predict_mask.ravel()[fp_ids])
        p_cal_vec = np.empty(len(pred_rows), dtype=np.float32)
        mult_b_vec = np.empty(len(pred_rows), dtype=np.float32)
        mult_b_legacy_vec = (
            np.empty(len(pred_rows), dtype=np.float32) if return_legacy_conduit else None
        )

        for start in range(0, len(pred_rows), chunk_size):
            sl = pred_rows[start : start + chunk_size]
            x_raw = read_stack_rows(sl, base_mm, gvc_mm, sahg_mm, extra_mm)
            mult_b_vec[start : start + chunk_size] = gate_scaler.score_regime_b_multiplier(
                x_raw, extra_subsurface_names=regime_b_extra_names
            )
            if mult_b_legacy_vec is not None:
                mult_b_legacy_vec[start : start + chunk_size] = (
                    gate_scaler.score_regime_b_multiplier(x_raw)
                )
            has_lid = np.isfinite(x_raw[:, g_sat_idx])
            slp = x_raw[:, slope_idx].copy()
            rel = x_raw[:, rel_idx].copy()
            c_sub = np.asarray(nuisance_fp[sl], dtype=np.float32)
            resid.transform_inplace(c_sub, x_raw)
            p_raw = 0.5 * (
                models[0].predict_proba(x_raw)[:, 1] + models[1].predict_proba(x_raw)[:, 1]
            )
            p_cal_vec[start : start + chunk_size] = calibrator.transform(
                p_raw, has_lid, c_sub, slp, rel
            )
            del x_raw, c_sub, p_raw

    p_cal_2d = np.zeros(fp.shape, dtype=np.float32)
    p_cal_2d.ravel()[fp_ids[pred_rows]] = p_cal_vec
    p_sharp_2d = sharpen_ridge_coherence(p_cal_2d, predict_mask, half_len_px=4)

    mult_b_2d = np.zeros(fp.shape, dtype=np.float32)
    mult_b_2d.ravel()[fp_ids[pred_rows]] = mult_b_vec
    p_conduit_2d = (p_sharp_2d * mult_b_2d).astype(np.float32)

    meta = {
        "neg_mode": neg_mode,
        "n_train_pos": int((y_tr == 1).sum()),
        "n_train_neg": int((y_tr == 0).sum()),
        "n_selective_residualized_cols": len(sel_indices),
        "relief_tier_cuts": list(calibrator.tier_cuts_),
    }
    if return_legacy_conduit:
        assert mult_b_legacy_vec is not None
        mult_b_leg_2d = np.zeros(fp.shape, dtype=np.float32)
        mult_b_leg_2d.ravel()[fp_ids[pred_rows]] = mult_b_legacy_vec
        p_conduit_legacy_2d = (p_sharp_2d * mult_b_leg_2d).astype(np.float32)
        return p_sharp_2d, p_conduit_2d, p_conduit_legacy_2d, meta
    return p_sharp_2d, p_conduit_2d, meta
