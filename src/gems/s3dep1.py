"""Preregistered H24-S3DEP1: Seamless 10 m 3DEP Monoclinal-Step x Crustal-Seismic x Conduit OOF.

Implements the locked specification in ``knowledge/29_preregistered_S3DEP1_2026-10-26.md``:
1. 61-channel 100% 1m-LiDAR-free seamless physical stack combining:
   - 18 non-LiDAR prepared geophysical/100m-DEM channels,
   - 17 non-LiDAR OpenEI GDR #1391 INGENIOUS hydrothermal & 900 m geophysical lineament channels,
   - 2 non-LiDAR GeoDAWN/basement SAHG1 channels (``sahg_r_alt``, ``sahg_b_step``),
   - 6 restored ``training_features.tif`` crustal/geodetic/seismic channels omitted by
     ``prepare_data.py`` (``mag_anom``, ``geod_2ndinv``, ``iso_grav_anom_slope``,
     ``bouguer_tc_mgal``, ``eq_deq_log1p``, ``eq_ieq_log1p``),
   - 12 seamless USGS 3DEP 1/3 arc-sec (~10 m) DEM sub-cell scarp & monoclinal-step
     asymmetry channels (``data/dem10/*.f32.npy``, 100.00% footprint coverage), and
   - 6 new S3DEP1 tectonic-geomorphic & sub-alluvial crustal coupling channels.
2. Fold-strict ``SelectiveNonTopographicResidualizer`` across all 19 regional potential-field,
   gravity-gradient, geodetic, seismic, radiometric, and crustal-coupling channels, with Stage-2
   subsurface/conduit gate multipliers evaluated strictly AFTER residualization.
3. Fold-strict ``UnconditionalNuisanceLogitCalibrator`` removing marginal ``road_m / claim_m /
   block_1..4`` log-odds drift on both Stage-1 and Stage-2 surfaces without slope conditioning.
4. Dual-Objective Log-Odds Geometric Fusion (``0.65 * logit(p_core_dualneg) + 0.35 * logit(p_kern300)``),
   8-azimuth 900 m ridge-coherence sharpening, visible-catalogue apron quantile debiasing, and
   Two-Regime 300 m triangular-kernel submodular allocation (72% primary scarp/seismic ridge +
   28% concealed hydrothermal-crustal conduit).
"""

from __future__ import annotations

import gc
import json
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from scipy.special import expit, logit
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from threadpoolctl import threadpool_limits

from . import dkrn1, dprf1, geofeatures, gvc
from .residualize import NuisanceResidualizer
from .validator import sha256_file

FORBIDDEN_1M_LIDAR_NAMES: frozenset[str] = frozenset(
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

NON_LIDAR_BASE18_NAMES: tuple[str, ...] = (
    "rtp",
    "tmi_hg",
    "tmi_vg",
    "iso_grav_anom",
    "iso_grav_anom_hg",
    "iso_grav_anom_vg",
    "det_elev",
    "det_elev_slope",
    "tmi",
    "cond_surf",
    "depth_to_base_surf",
    "geod_dilaterate",
    "geod_shearrate",
    "det_local_relief",
    "det_gradient",
    "arc_rtp",
    "arc_det_elev",
    "arc_agreement",
)

NON_LIDAR_GVC17_NAMES: tuple[str, ...] = tuple(
    nm for nm in gvc.GVC1_FEATURE_NAMES if nm != "gvc_lidar_lineament_900m"
)

NON_LIDAR_SAHG2_NAMES: tuple[str, ...] = (
    "sahg_r_alt",
    "sahg_b_step",
)

RESTORED_TRAIN6_NAMES: tuple[str, ...] = (
    "mag_anom",
    "geod_2ndinv",
    "iso_grav_anom_slope",
    "bouguer_tc_mgal",
    "eq_deq_log1p",
    "eq_ieq_log1p",
)

DEM10_12_NAMES: tuple[str, ...] = (
    "dem10_slope_max",
    "dem10_slope_mean",
    "dem10_slope_std",
    "dem10_hgm20_max",
    "dem10_hgm50_max",
    "dem10_hgm200_mean",
    "dem10_steep_ratio_max",
    "dem10_resid_std",
    "dem10_resid_range",
    "dem10_curv_absmax",
    "dem10_onesided",
    "dem10_onesided3",
)

S3DEP1_DERIVED6_NAMES: tuple[str, ...] = (
    "s3dep_monoclinal_step_index",
    "s3dep_monoclinal_lineament_900m",
    "s3dep_scarp_over_incision",
    "s3dep_piedmont_inflection_50_200",
    "s3dep_suballuvial_grav_monocline",
    "crustal_strain_eq_coupling",
)

S3DEP1_NAMES: tuple[str, ...] = (
    *NON_LIDAR_BASE18_NAMES,
    *NON_LIDAR_GVC17_NAMES,
    *NON_LIDAR_SAHG2_NAMES,
    *RESTORED_TRAIN6_NAMES,
    *DEM10_12_NAMES,
    *S3DEP1_DERIVED6_NAMES,
)

S3DEP1_SELECTIVE_RESID_NAMES: frozenset[str] = frozenset(
    {
        "rtp",
        "tmi",
        "mag_anom",
        "iso_grav_anom",
        "iso_grav_anom_slope",
        "bouguer_tc_mgal",
        "depth_to_base_surf",
        "cond_surf",
        "geod_2ndinv",
        "geod_shearrate",
        "geod_dilaterate",
        "eq_deq_log1p",
        "eq_ieq_log1p",
        "gvc_rad_k_thk_alter",
        "gvc_rad_uth_excess",
        "sahg_r_alt",
        "sahg_b_step",
        "s3dep_suballuvial_grav_monocline",
        "crustal_strain_eq_coupling",
    }
)

NON_LIDAR_UPFLOW_NAMES: tuple[str, ...] = (
    "gvc_paleo_sinter_logd",
    "gvc_probe2m_anom_1p5km",
    "gvc_spring_hot_logd",
    "gvc_geotherm_halo_2p5km",
)

S3DEP1_SUBSURFACE_NAMES: tuple[str, ...] = (
    "gvc_tmi_tilt_grad",
    "gvc_grav_tilt_grad",
    "gvc_basement_step_grad",
    "gvc_grav_mag_coalign_2km",
    "sahg_b_step",
    "s3dep_suballuvial_grav_monocline",
    "crustal_strain_eq_coupling",
)

DEM10_SLOPE_MEAN_NAME = "dem10_slope_mean"

if len(S3DEP1_NAMES) != 61:
    raise AssertionError(f"Expected 61 S3DEP1 channels, got {len(S3DEP1_NAMES)}")
if set(S3DEP1_NAMES) & FORBIDDEN_1M_LIDAR_NAMES:
    raise AssertionError("Forbidden 1 m LiDAR channel leaked into S3DEP1_NAMES")


def compute_s3dep1_derived_channels(
    *,
    dem10_onesided: np.ndarray,
    dem10_onesided3: np.ndarray,
    dem10_hgm50_max: np.ndarray,
    dem10_hgm200_mean: np.ndarray,
    dem10_steep_ratio_max: np.ndarray,
    dem10_slope_mean: np.ndarray,
    dem10_curv_absmax: np.ndarray,
    iso_grav_anom_slope: np.ndarray,
    depth_to_base_surf: np.ndarray,
    geod_2ndinv: np.ndarray,
    geod_shearrate: np.ndarray,
    eq_deq_log1p: np.ndarray,
    eq_ieq_log1p: np.ndarray,
    footprint: np.ndarray,
) -> dict[str, np.ndarray]:
    """Compute the 6 preregistered label-free S3DEP1 tectonic-geomorphic & crustal operators."""
    fp = np.asarray(footprint, dtype=bool)
    dem_v = (
        fp
        & np.isfinite(dem10_onesided)
        & np.isfinite(dem10_onesided3)
        & np.isfinite(dem10_hgm50_max)
        & np.isfinite(dem10_hgm200_mean)
        & np.isfinite(dem10_steep_ratio_max)
        & np.isfinite(dem10_slope_mean)
        & np.isfinite(dem10_curv_absmax)
    )

    o1 = np.clip(dem10_onesided, 0.0, 1.0)
    o3 = np.clip(dem10_onesided3, 0.0, 1.0)
    hgm50 = np.maximum(dem10_hgm50_max, 0.0)
    steep_r = np.maximum(dem10_steep_ratio_max, 0.0)
    curv = np.maximum(dem10_curv_absmax, 0.0)

    # 1. Unidirectional 30-50 m monoclinal step index localized inside 100 m cells
    msi = np.where(
        dem_v,
        o3 * np.log1p(hgm50) * (steep_r / (steep_r + 2.0)),
        np.nan,
    ).astype(np.float32)

    # 2. 8-azimuth 900 m strike-minus-flank monoclinal lineament response (100% seamless)
    msi_lin900 = gvc.oriented_lineament_response(msi, dem_v, half_len_px=4, flank_offset_px=3)

    # 3. Monoclinal scarp vs symmetric channel/road-cut curvature discriminator
    num_sc = o3 * hgm50
    den_sc = num_sc + (1.0 - o1) * 20.0 * curv + 0.01
    scarp_over_inc = np.where(dem_v, num_sc / den_sc, np.nan).astype(np.float32)

    # 4. Degraded Pleistocene piedmont scarp inflection (50 m break over gentle 200 m fan slope)
    z_h50 = gvc._robust_z(hgm50, dem_v)
    z_h200 = gvc._robust_z(np.maximum(dem10_hgm200_mean, 0.0), dem_v)
    z_slp = gvc._robust_z(np.maximum(dem10_slope_mean, 0.0), dem_v)
    pied_inf = np.where(
        dem_v,
        o3 * np.maximum(0.0, z_h50 - 0.65 * z_h200) * expit(-z_slp).astype(np.float32),
        np.nan,
    ).astype(np.float32)
    del z_h50, z_h200, z_slp

    # 5. Sub-alluvial gravity ramp x surface 10 m monoclinal warp coupling (150-1050 m fill)
    sub_v = dem_v & np.isfinite(iso_grav_anom_slope) & np.isfinite(depth_to_base_surf)
    z_msi = gvc._robust_z(msi, dem_v)
    sub_grav_mono = np.where(
        sub_v,
        expit(z_msi).astype(np.float32)
        * np.maximum(iso_grav_anom_slope, 0.0)
        * np.exp(-(((depth_to_base_surf - 450.0) / 500.0) ** 2)),
        np.nan,
    ).astype(np.float32)
    del z_msi

    # 6. Crustal GPS 2nd-invariant strain x declustered microseismic damage-zone localization
    eq_v = (
        fp
        & np.isfinite(geod_2ndinv)
        & np.isfinite(geod_shearrate)
        & np.isfinite(eq_deq_log1p)
        & np.isfinite(eq_ieq_log1p)
    )
    z_deq = gvc._robust_z(eq_deq_log1p, eq_v)
    z_ieq = gvc._robust_z(eq_ieq_log1p, eq_v)
    z_shr = gvc._robust_z(geod_shearrate, eq_v)
    strain_eq = np.where(
        eq_v,
        np.log1p(np.maximum(geod_2ndinv, 0.0))
        * (0.5 + 0.5 * expit(z_deq - 0.5 * z_ieq).astype(np.float32))
        * (0.5 + 0.5 * expit(z_shr).astype(np.float32)),
        np.nan,
    ).astype(np.float32)

    return {
        "s3dep_monoclinal_step_index": msi,
        "s3dep_monoclinal_lineament_900m": msi_lin900.astype(np.float32),
        "s3dep_scarp_over_incision": scarp_over_inc,
        "s3dep_piedmont_inflection_50_200": pied_inf,
        "s3dep_suballuvial_grav_monocline": sub_grav_mono,
        "crustal_strain_eq_coupling": strain_eq,
    }


def verify_dem10_archive(dem10_dir: Path, n_fp: int) -> dict[str, str]:
    """Verify SHA-256 digests and exact footprint length of all 12 USGS 3DEP 10 m channels."""
    manifest_path = dem10_dir / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(
            f"Missing {manifest_path}; restore immutable USGS 3DEP 10 m archive first"
        )
    manifest = json.loads(manifest_path.read_text())
    if int(manifest.get("footprint_pixels", -1)) != int(n_fp):
        raise ValueError("dem10 manifest footprint_pixels mismatch")
    stats = manifest.get("channel_stats") or {}
    verified_hashes: dict[str, str] = {}
    for ch in DEM10_12_NAMES:
        fpath = dem10_dir / f"{ch}.f32.npy"
        if not fpath.exists():
            raise FileNotFoundError(f"Missing 10 m 3DEP channel file: {fpath}")
        sha = sha256_file(fpath)
        exp = (stats.get(ch) or {}).get("sha256")
        if exp and sha != exp:
            raise ValueError(f"SHA-256 mismatch on {fpath}: {sha} != {exp}")
        arr = np.load(fpath, mmap_mode="r")
        if arr.shape != (n_fp,) or arr.dtype != np.float32:
            raise ValueError(f"Unexpected shape/dtype on {fpath}: {arr.shape} {arr.dtype}")
        verified_hashes[ch] = sha
    return verified_hashes


def build_s3dep1_memmap(
    root: Path,
    base_mm: np.ndarray,
    base_names: list[str],
    gvc_mm: np.ndarray,
    gvc_names: list[str],
    sahg_mm: np.ndarray,
    sahg_names: list[str],
    footprint: np.ndarray,
    out_path: Path,
) -> tuple[np.ndarray, list[str], dict[str, Any]]:
    """Build or open the 61-channel 1m-LiDAR-free S3DEP1 float32 memmap under <1.5 GiB RSS."""
    fp = np.asarray(footprint, dtype=bool)
    fp_ids = np.flatnonzero(fp.ravel())
    n_fp = len(fp_ids)
    n_cols = len(S3DEP1_NAMES)
    meta_path = out_path.with_suffix(".json")
    expected_bytes = n_fp * n_cols * 4

    if out_path.exists() and meta_path.exists() and out_path.stat().st_size == expected_bytes:
        meta = json.loads(meta_path.read_text())
        if meta.get("names") == list(S3DEP1_NAMES) and int(meta.get("n_fp", -1)) == n_fp:
            mm_ro = np.memmap(out_path, dtype="float32", mode="r", shape=(n_fp, n_cols))
            return mm_ro, list(S3DEP1_NAMES), meta

    # Verify external CSV headers never expose forbidden fault-distance columns
    for csv_rel in (
        "data/external/gdr_wellspring_in_footprint.csv",
        "data/external/gdr_volcanic_vents_in_footprint.csv",
    ):
        csv_p = root / csv_rel
        if csv_p.exists():
            hdr = csv_p.open("r", encoding="utf-8").readline().strip().split(",")
            allowed = [c for c in hdr if c.lower() not in gvc.FORBIDDEN_COLUMNS]
            if "dist_known_fault_px" in allowed:
                raise RuntimeError("Forbidden column leaked into allowed external columns")

    dem10_dir = root / "data/dem10"
    dem10_hashes = verify_dem10_archive(dem10_dir, n_fp)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    mm = np.memmap(out_path, dtype="float32", mode="w+", shape=(n_fp, n_cols))

    # 1. Copy 18 non-LiDAR prepared base channels + 17 non-LiDAR GVC + 2 non-LiDAR SAHG in chunks
    base_idx = [base_names.index(nm) for nm in NON_LIDAR_BASE18_NAMES]
    gvc_idx = [gvc_names.index(nm) for nm in NON_LIDAR_GVC17_NAMES]
    sahg_idx = [sahg_names.index(nm) for nm in NON_LIDAR_SAHG2_NAMES]
    for s in range(0, n_fp, 400_000):
        e = min(s + 400_000, n_fp)
        mm[s:e, 0:18] = base_mm[s:e, base_idx]
        mm[s:e, 18:35] = gvc_mm[s:e, gvc_idx]
        mm[s:e, 35:37] = sahg_mm[s:e, sahg_idx]
    mm.flush()
    gc.collect()

    def to_2d(vec_fp: np.ndarray) -> np.ndarray:
        grid = np.full(fp.shape, np.nan, dtype=np.float32)
        grid.ravel()[fp_ids] = vec_fp
        return grid

    # 2. Read the 6 restored training_features.tif bands (cols 37..42)
    train_tif = root / "data/training_features.tif"
    with rasterio.open(train_tif) as src:

        def read_clean(bname: str) -> np.ndarray:
            bidx = geofeatures.BAND_ORDER.index(bname) + 1
            raw = src.read(bidx).astype(np.float32)
            bad = (~np.isfinite(raw)) | (np.abs(raw) > 1e30) | (~fp)
            raw[bad] = np.nan
            return raw

        mag_anom = read_clean("mag_anom")
        mm[:, 37] = mag_anom.ravel()[fp_ids]
        del mag_anom

        geod_2ndinv = read_clean("geod_2ndinv")
        mm[:, 38] = geod_2ndinv.ravel()[fp_ids]

        iso_grav_slope = read_clean("iso_grav_anom_slope")
        mm[:, 39] = iso_grav_slope.ravel()[fp_ids]

        tc_mgal = read_clean("tc")
        mm[:, 40] = tc_mgal.ravel()[fp_ids]
        del tc_mgal

        deq_raw = read_clean("deq_n100a15")
        eq_deq_log1p = np.where(
            fp & np.isfinite(deq_raw), np.log1p(np.maximum(deq_raw, 0.0)), np.nan
        ).astype(np.float32)
        del deq_raw
        mm[:, 41] = eq_deq_log1p.ravel()[fp_ids]

        ieq_raw = read_clean("ieq_n100a15")
        eq_ieq_log1p = np.where(
            fp & np.isfinite(ieq_raw), np.log1p(np.maximum(ieq_raw, 0.0)), np.nan
        ).astype(np.float32)
        del ieq_raw
        mm[:, 42] = eq_ieq_log1p.ravel()[fp_ids]

    mm.flush()
    gc.collect()

    # 3. Copy all 12 seamless 10 m 3DEP DEM channels (cols 43..54)
    dem10_2d_keep: dict[str, np.ndarray] = {}
    need_for_derived = {
        "dem10_onesided",
        "dem10_onesided3",
        "dem10_hgm50_max",
        "dem10_hgm200_mean",
        "dem10_steep_ratio_max",
        "dem10_slope_mean",
        "dem10_curv_absmax",
    }
    for j, ch in enumerate(DEM10_12_NAMES):
        vec = np.asarray(np.load(dem10_dir / f"{ch}.f32.npy", mmap_mode="r"), dtype=np.float32)
        mm[:, 43 + j] = vec
        if ch in need_for_derived:
            dem10_2d_keep[ch] = to_2d(vec)
        del vec
    mm.flush()

    # 4. Compute 6 derived S3DEP1 operators (cols 55..60)
    depth_base_2d = to_2d(np.asarray(mm[:, S3DEP1_NAMES.index("depth_to_base_surf")], np.float32))
    geod_shear_2d = to_2d(np.asarray(mm[:, S3DEP1_NAMES.index("geod_shearrate")], np.float32))

    derived = compute_s3dep1_derived_channels(
        dem10_onesided=dem10_2d_keep["dem10_onesided"],
        dem10_onesided3=dem10_2d_keep["dem10_onesided3"],
        dem10_hgm50_max=dem10_2d_keep["dem10_hgm50_max"],
        dem10_hgm200_mean=dem10_2d_keep["dem10_hgm200_mean"],
        dem10_steep_ratio_max=dem10_2d_keep["dem10_steep_ratio_max"],
        dem10_slope_mean=dem10_2d_keep["dem10_slope_mean"],
        dem10_curv_absmax=dem10_2d_keep["dem10_curv_absmax"],
        iso_grav_anom_slope=iso_grav_slope,
        depth_to_base_surf=depth_base_2d,
        geod_2ndinv=geod_2ndinv,
        geod_shearrate=geod_shear_2d,
        eq_deq_log1p=eq_deq_log1p,
        eq_ieq_log1p=eq_ieq_log1p,
        footprint=fp,
    )
    del (
        dem10_2d_keep,
        iso_grav_slope,
        depth_base_2d,
        geod_2ndinv,
        geod_shear_2d,
        eq_deq_log1p,
        eq_ieq_log1p,
    )
    for k, dname in enumerate(S3DEP1_DERIVED6_NAMES):
        mm[:, 55 + k] = derived[dname].ravel()[fp_ids]
    del derived
    mm.flush()
    del mm
    gc.collect()

    meta_payload = {
        "names": list(S3DEP1_NAMES),
        "n_fp": int(n_fp),
        "n_cols": int(n_cols),
        "sha256": sha256_file(out_path),
        "zero_1m_lidar_channels": True,
        "forbidden_1m_lidar_excluded": sorted(FORBIDDEN_1M_LIDAR_NAMES),
        "forbidden_csv_columns_excluded": sorted(gvc.FORBIDDEN_COLUMNS),
        "inputs": {
            "data/training_features.tif": sha256_file(train_tif),
            "data/dem10/manifest.json": sha256_file(dem10_dir / "manifest.json"),
            "dem10_channels": dem10_hashes,
        },
        "band_provenance_notes": {
            "bouguer_tc_mgal": (
                "Historic feature alias retained unchanged for reproducibility; it does not "
                "establish gravity, terrain correction or mGal units. Band 6 ('tc') is "
                "strongly rank-correlated with cached GeoDAWN radiometric total count; the "
                "mirror tag instead says magnetic tilt/curvature. Source and units remain "
                "unverified; see evidence/band6_provenance_review_20261027.json."
            )
        },
    }
    meta_path.write_text(json.dumps(meta_payload, indent=2) + "\n")
    mm_ro = np.memmap(out_path, dtype="float32", mode="r", shape=(n_fp, n_cols))
    return mm_ro, list(S3DEP1_NAMES), meta_payload


class UnconditionalNuisanceLogitCalibrator:
    """Fold-only unconditional marginal nuisance log-odds debiaser (zero slope conditioning)."""

    def __init__(self, alpha: float = 100.0):
        self.alpha = float(alpha)
        self._basis_helper = NuisanceResidualizer(alpha=alpha)
        self.ridge_: Ridge | None = None
        self.mean_nuis_: float = 0.0

    def fit(
        self, prob_bg: np.ndarray, nuisance_bg: np.ndarray
    ) -> UnconditionalNuisanceLogitCalibrator:
        p = np.clip(np.asarray(prob_bg, dtype=np.float64), 1e-4, 1.0 - 1e-4)
        ell = logit(p).astype(np.float32)
        c = np.asarray(nuisance_bg, dtype=np.float32)
        self._basis_helper.n_nuisance = c.shape[1]
        basis = self._basis_helper._basis(c, fit=True)
        self.ridge_ = Ridge(alpha=self.alpha).fit(basis, ell)
        eff = self.ridge_.predict(basis)
        self.mean_nuis_ = float(np.mean(eff))
        return self

    def transform(self, prob: np.ndarray, nuisance: np.ndarray) -> np.ndarray:
        if self.ridge_ is None:
            raise RuntimeError("Call fit before transform")
        p = np.clip(np.asarray(prob, dtype=np.float64), 1e-4, 1.0 - 1e-4)
        ell = logit(p).astype(np.float32)
        basis = self._basis_helper._basis(np.asarray(nuisance, dtype=np.float32), fit=False)
        debiased = ell - (self.ridge_.predict(basis) - self.mean_nuis_)
        return np.clip(expit(np.clip(debiased, -14.0, 14.0)), 0.0, 1.0).astype(np.float32)


class S3depConduitGateScaler:
    """Train-only robust quantile scaler for Stage-2 concealed hydrothermal-crustal conduits."""

    def __init__(self, col_indices: dict[str, int]):
        self.col_indices = dict(col_indices)
        self.stats_: dict[str, tuple[float, float]] = {}

    def fit(self, x_train_bg_residualized: np.ndarray) -> S3depConduitGateScaler:
        self.stats_.clear()
        for name, idx in self.col_indices.items():
            col = x_train_bg_residualized[:, idx]
            obs = col[np.isfinite(col)]
            if len(obs) >= 32:
                med = float(np.median(obs))
                q25, q75 = np.percentile(obs, [25.0, 75.0])
                iqr = max(float(q75 - q25), 1e-5)
            else:
                med, iqr = 0.0, 1.0
            self.stats_[name] = (med, iqr)
        return self

    def _sig(self, x_res: np.ndarray, name: str) -> np.ndarray:
        idx = self.col_indices[name]
        med, iqr = self.stats_[name]
        col = x_res[:, idx]
        out = np.full(len(x_res), 0.5, dtype=np.float32)
        obs = np.isfinite(col)
        if np.any(obs):
            z = np.clip((col[obs] - med) / iqr, -6.0, 6.0)
            out[obs] = expit(z).astype(np.float32)
        return out

    def score_multiplier(self, x_residualized: np.ndarray) -> np.ndarray:
        """Compute Stage-2 conduit multiplier strictly on residualized features."""
        n = len(x_residualized)
        h_up = np.zeros(n, dtype=np.float32)
        for nm in NON_LIDAR_UPFLOW_NAMES:
            h_up += self._sig(x_residualized, nm)
        h_up /= float(len(NON_LIDAR_UPFLOW_NAMES))

        b_sub = np.zeros(n, dtype=np.float32)
        for nm in S3DEP1_SUBSURFACE_NAMES:
            b_sub += self._sig(x_residualized, nm)
        b_sub /= float(len(S3DEP1_SUBSURFACE_NAMES))

        s_steep = self._sig(x_residualized, DEM10_SLOPE_MEAN_NAME)
        mult = (0.30 + 0.70 * h_up) * (0.30 + 0.70 * b_sub) * (1.0 - 0.50 * s_steep)
        return np.clip(mult, 0.05, 1.0).astype(np.float32)


def log_odds_geometric_blend(
    p_core: np.ndarray, p_kern: np.ndarray, *, w_core: float = 0.65
) -> np.ndarray:
    """Compute ``expit(w_core * logit(p_core) + (1 - w_core) * logit(p_kern))`` safely."""
    w_a = float(w_core)
    w_b = 1.0 - w_a
    a = np.clip(np.asarray(p_core, dtype=np.float64), 1e-5, 1.0 - 1e-5)
    b = np.clip(np.asarray(p_kern, dtype=np.float64), 1e-5, 1.0 - 1e-5)
    ell = w_a * logit(a) + w_b * logit(b)
    return np.clip(expit(np.clip(ell, -14.0, 14.0)), 0.0, 1.0).astype(np.float32)


def fit_and_predict_s3dep1_fold(
    stack_mm: np.ndarray,
    nuisance_fp: np.ndarray,
    all_names: list[str],
    fp: np.ndarray,
    fp_ids: np.ndarray,
    *,
    train_mask: np.ndarray,
    visible_mask: np.ndarray,
    predict_mask: np.ndarray,
    seed: int,
    chunk_size: int = 150_000,
    max_iter: int = 200,
    return_all_arms: bool = True,
) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    """Fit Arm 1 (core d3+d9), Arm 2 (300m kernel reg), and Arm 3 (log-odds hybrid) on one fold."""
    if tuple(all_names) != S3DEP1_NAMES:
        raise ValueError("all_names must match S3DEP1_NAMES (61 non-1m-LiDAR channels)")

    sel_names = sorted(S3DEP1_SELECTIVE_RESID_NAMES)
    sel_indices = [all_names.index(nm) for nm in sel_names]
    gate_names = (*NON_LIDAR_UPFLOW_NAMES, *S3DEP1_SUBSURFACE_NAMES, DEM10_SLOPE_MEAN_NAME)
    gate_col_map = {nm: all_names.index(nm) for nm in gate_names}

    # 1. Sample d3 core, d9 deadzone, and 300m kernel training rows strictly inside train_mask
    rows_d3, y_d3 = dprf1.sample_fold_training_rows(
        train_mask,
        visible_mask,
        fp_ids,
        mode="stratified_d3",
        max_pos=25_000,
        max_neg=75_000,
        seed=seed,
    )
    rows_d9, y_d9 = dprf1.sample_fold_training_rows(
        train_mask,
        visible_mask,
        fp_ids,
        mode="deadzone_d9",
        max_pos=25_000,
        max_neg=75_000,
        seed=seed + 7,
    )
    rows_kern, y_kern, pop_mean_yk = dkrn1.sample_kernel_corridor_rows(
        train_mask, visible_mask, fp_ids, seed=seed + 19
    )

    # 2. Disjoint 35,000 training background rows for residualizer, gate scaler, and calibrators
    bg_mask = train_mask & (~visible_mask)
    bg_pool_all = np.flatnonzero(bg_mask.ravel()[fp_ids])
    used_all = np.union1d(np.union1d(rows_d3, rows_d9), rows_kern)
    bg_disjoint = np.setdiff1d(bg_pool_all, used_all, assume_unique=True)
    if len(bg_disjoint) < 5_000:
        bg_disjoint = bg_pool_all
    rng_bg = np.random.default_rng(seed + 41)
    bg_sel = np.sort(rng_bg.choice(bg_disjoint, size=min(35_000, len(bg_disjoint)), replace=False))

    x_bg_res = np.asarray(stack_mm[bg_sel], dtype=np.float32).copy()
    c_bg = np.asarray(nuisance_fp[bg_sel], dtype=np.float32)

    resid = dprf1.SelectiveNonTopographicResidualizer(sel_indices, alpha=100.0).fit(c_bg, x_bg_res)
    resid.transform_inplace(c_bg, x_bg_res)
    gate_scaler = S3depConduitGateScaler(gate_col_map).fit(x_bg_res)
    mult_bg = gate_scaler.score_multiplier(x_bg_res)

    clf_d3_models: list[HistGradientBoostingClassifier] = []
    clf_d9_models: list[HistGradientBoostingClassifier] = []
    reg_k_models: list[HistGradientBoostingRegressor] = []

    with threadpool_limits(limits=2):
        # Fit Core Stratified-d3 Classifiers
        x_d3 = np.asarray(stack_mm[rows_d3], dtype=np.float32).copy()
        resid.transform_inplace(np.asarray(nuisance_fp[rows_d3], dtype=np.float32), x_d3)
        for s_off in (100, 200):
            clf = HistGradientBoostingClassifier(
                max_iter=max_iter,
                learning_rate=0.055,
                max_leaf_nodes=31,
                min_samples_leaf=80,
                l2_regularization=2.5,
                early_stopping=False,
                random_state=seed + s_off,
            )
            clf.fit(x_d3, y_d3)
            clf_d3_models.append(clf)
        del x_d3
        gc.collect()

        # Fit Core Deadzone-d9 Classifiers
        x_d9 = np.asarray(stack_mm[rows_d9], dtype=np.float32).copy()
        resid.transform_inplace(np.asarray(nuisance_fp[rows_d9], dtype=np.float32), x_d9)
        for s_off in (300, 400):
            clf = HistGradientBoostingClassifier(
                max_iter=max_iter,
                learning_rate=0.055,
                max_leaf_nodes=31,
                min_samples_leaf=80,
                l2_regularization=2.5,
                early_stopping=False,
                random_state=seed + s_off,
            )
            clf.fit(x_d9, y_d9)
            clf_d9_models.append(clf)
        del x_d9
        gc.collect()

        # Fit 300 m Triangular-Kernel Corridor Regressors
        x_kr = np.asarray(stack_mm[rows_kern], dtype=np.float32).copy()
        resid.transform_inplace(np.asarray(nuisance_fp[rows_kern], dtype=np.float32), x_kr)
        for s_off in (500, 600):
            reg = HistGradientBoostingRegressor(
                loss="squared_error",
                max_iter=max_iter,
                learning_rate=0.055,
                max_leaf_nodes=31,
                min_samples_leaf=80,
                l2_regularization=2.5,
                early_stopping=False,
                random_state=seed + s_off,
            )
            reg.fit(x_kr, y_kern)
            reg_k_models.append(reg)
        del x_kr
        gc.collect()

        # Fit UnconditionalNuisanceLogitCalibrators on disjoint background rows
        p_d3_bg = 0.5 * (
            clf_d3_models[0].predict_proba(x_bg_res)[:, 1]
            + clf_d3_models[1].predict_proba(x_bg_res)[:, 1]
        )
        p_d9_bg = 0.5 * (
            clf_d9_models[0].predict_proba(x_bg_res)[:, 1]
            + clf_d9_models[1].predict_proba(x_bg_res)[:, 1]
        )
        p_k_bg = np.clip(
            0.5 * (reg_k_models[0].predict(x_bg_res) + reg_k_models[1].predict(x_bg_res)),
            1e-4,
            1.0 - 1e-4,
        )

        cal_d3 = UnconditionalNuisanceLogitCalibrator(alpha=100.0).fit(p_d3_bg, c_bg)
        cal_d9 = UnconditionalNuisanceLogitCalibrator(alpha=100.0).fit(p_d9_bg, c_bg)
        cal_k = UnconditionalNuisanceLogitCalibrator(alpha=100.0).fit(p_k_bg, c_bg)

        p_core_bg = (
            0.55 * cal_d3.transform(p_d3_bg, c_bg) + 0.45 * cal_d9.transform(p_d9_bg, c_bg)
        ).astype(np.float32)
        p_kern_bg = cal_k.transform(p_k_bg, c_bg)
        p_hyb_bg = log_odds_geometric_blend(p_core_bg, p_kern_bg, w_core=0.65)

        cal_cond_hyb = UnconditionalNuisanceLogitCalibrator(alpha=100.0).fit(
            p_hyb_bg * mult_bg, c_bg
        )
        cal_cond_core = (
            UnconditionalNuisanceLogitCalibrator(alpha=100.0).fit(p_core_bg * mult_bg, c_bg)
            if return_all_arms
            else None
        )
        cal_cond_kern = (
            UnconditionalNuisanceLogitCalibrator(alpha=100.0).fit(p_kern_bg * mult_bg, c_bg)
            if return_all_arms
            else None
        )
        del x_bg_res, c_bg, mult_bg, p_d3_bg, p_d9_bg, p_k_bg, p_core_bg, p_kern_bg, p_hyb_bg
        gc.collect()

        # 3. Chunked prediction over predict_mask
        pred_rows = np.flatnonzero(predict_mask.ravel()[fp_ids])
        n_pred = len(pred_rows)
        hyb_vec = np.empty(n_pred, dtype=np.float32)
        hyb_cond_vec = np.empty(n_pred, dtype=np.float32)
        core_vec = np.empty(n_pred, dtype=np.float32) if return_all_arms else None
        core_cond_vec = np.empty(n_pred, dtype=np.float32) if return_all_arms else None
        kern_vec = np.empty(n_pred, dtype=np.float32) if return_all_arms else None
        kern_cond_vec = np.empty(n_pred, dtype=np.float32) if return_all_arms else None

        for start in range(0, n_pred, chunk_size):
            sl = pred_rows[start : start + chunk_size]
            end = start + len(sl)
            x_sub = np.asarray(stack_mm[sl], dtype=np.float32).copy()
            c_sub = np.asarray(nuisance_fp[sl], dtype=np.float32)
            resid.transform_inplace(c_sub, x_sub)
            m_sub = gate_scaler.score_multiplier(x_sub)

            p3_raw = 0.5 * (
                clf_d3_models[0].predict_proba(x_sub)[:, 1]
                + clf_d3_models[1].predict_proba(x_sub)[:, 1]
            )
            p9_raw = 0.5 * (
                clf_d9_models[0].predict_proba(x_sub)[:, 1]
                + clf_d9_models[1].predict_proba(x_sub)[:, 1]
            )
            pk_raw = np.clip(
                0.5 * (reg_k_models[0].predict(x_sub) + reg_k_models[1].predict(x_sub)),
                1e-4,
                1.0 - 1e-4,
            )
            del x_sub

            p_core = (
                0.55 * cal_d3.transform(p3_raw, c_sub) + 0.45 * cal_d9.transform(p9_raw, c_sub)
            ).astype(np.float32)
            p_kern = cal_k.transform(pk_raw, c_sub)
            p_hyb = log_odds_geometric_blend(p_core, p_kern, w_core=0.65)

            hyb_vec[start:end] = p_hyb
            hyb_cond_vec[start:end] = cal_cond_hyb.transform(p_hyb * m_sub, c_sub)
            if return_all_arms:
                assert (
                    core_vec is not None
                    and core_cond_vec is not None
                    and kern_vec is not None
                    and kern_cond_vec is not None
                    and cal_cond_core is not None
                    and cal_cond_kern is not None
                )
                core_vec[start:end] = p_core
                core_cond_vec[start:end] = cal_cond_core.transform(p_core * m_sub, c_sub)
                kern_vec[start:end] = p_kern
                kern_cond_vec[start:end] = cal_cond_kern.transform(p_kern * m_sub, c_sub)
            del c_sub, m_sub, p3_raw, p9_raw, pk_raw, p_core, p_kern, p_hyb

    def scatter_sharp(vec: np.ndarray) -> np.ndarray:
        arr = np.zeros(fp.shape, dtype=np.float32)
        arr.ravel()[fp_ids[pred_rows]] = vec
        return dprf1.sharpen_ridge_coherence(arr, predict_mask, half_len_px=4)

    def scatter_plain(vec: np.ndarray) -> np.ndarray:
        arr = np.zeros(fp.shape, dtype=np.float32)
        arr.ravel()[fp_ids[pred_rows]] = vec
        return arr

    hyb_sharp = scatter_sharp(hyb_vec)
    hyb_cond_raw = scatter_plain(hyb_cond_vec)
    # Preserve ridge sharpening along Stage-2 conduits while retaining nuisance debiasing
    hyb_cond = dprf1.sharpen_ridge_coherence(hyb_cond_raw, predict_mask, half_len_px=4)
    del hyb_vec, hyb_cond_vec, hyb_cond_raw

    surfaces: dict[str, np.ndarray] = {
        "arm3_sharp": hyb_sharp,
        "arm3_conduit": hyb_cond,
    }
    if return_all_arms:
        assert (
            core_vec is not None
            and core_cond_vec is not None
            and kern_vec is not None
            and kern_cond_vec is not None
        )
        surfaces["arm1_sharp"] = scatter_sharp(core_vec)
        surfaces["arm1_conduit"] = scatter_sharp(core_cond_vec)
        surfaces["arm2_sharp"] = scatter_sharp(kern_vec)
        surfaces["arm2_conduit"] = scatter_sharp(kern_cond_vec)

    meta = {
        "n_channels": len(all_names),
        "zero_1m_lidar": True,
        "n_selective_residualized_cols": len(sel_indices),
        "n_d3_pos": int((y_d3 == 1).sum()),
        "n_d3_neg": int((y_d3 == 0).sum()),
        "n_d9_pos": int((y_d9 == 1).sum()),
        "n_d9_neg": int((y_d9 == 0).sum()),
        "n_kern_rows": int(len(y_kern)),
        "pop_mean_yk": float(pop_mean_yk),
    }
    return surfaces, meta


def ranking_surface_for_novelty(
    p_sharp: np.ndarray,
    p_conduit: np.ndarray,
    footprint: np.ndarray,
    catalogue: np.ndarray,
    *,
    primary_share: float = 0.72,
    catalogue_clearance_px: float = 2.0,
) -> np.ndarray:
    """Combined off-catalogue pre-placement ranking surface audited by Protocol Rule 1."""
    from scipy.ndimage import distance_transform_edt

    fp = np.asarray(footprint, dtype=bool)
    cat = np.asarray(catalogue, dtype=bool)
    elig = fp & (~cat) & (distance_transform_edt(~cat) > float(catalogue_clearance_px))
    w = float(primary_share)
    comb = np.where(elig, np.clip(w * p_sharp + (1.0 - w) * p_conduit, 0.0, 1.0), 0.0)
    return comb.astype(np.float32)
