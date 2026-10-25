"""H24-GVC1: Geothermal Vent-Upflow, Oriented Lineament & Tilt-Derivative Discovery.

Implements the preregistered label-free physical & INGENIOUS geothermal feature
operators and the exact Minoux (1978) lazy-greedy 300 m triangular-kernel
submodular dot allocator for ``SegmentHoldout`` (``gems-segment-pooled-v1``).

Anti-leakage invariants enforced in code:
1. ``dist_known_fault_px`` is never read from any INGENIOUS CSV and is asserted
   absent from loaded DataFrames.
2. ``gdr_qfaults_traces.csv`` and all prior submission rasters are never read
   during feature engineering, model fitting, calibration, or dot allocation.
3. Fold-level negative sampling, inner spatial-block isotonic calibration, and
   optional ``NuisanceResidualizer`` fitting operate strictly inside ``fold['train']``
   using ``fold['visible']`` only.
"""

from __future__ import annotations

import gc
import heapq
import io
import zipfile
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import rasterio
import shapefile
from pyproj import Transformer
from scipy.ndimage import distance_transform_edt, gaussian_filter
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.isotonic import IsotonicRegression
from threadpoolctl import threadpool_limits

from .metric import KERNEL_OFFSETS, RADIUS_PX, ridge_nms, select_top_positive
from .residualize import NuisanceResidualizer

GVC1_FEATURE_NAMES: tuple[str, ...] = (
    "gvc_paleo_sinter_logd",
    "gvc_probe2m_anom_1p5km",
    "gvc_spring_hot_logd",
    "gvc_geotherm_halo_2p5km",
    "gvc_rad_k_thk_alter",
    "gvc_rad_uth_excess",
    "gvc_cond_clay_grad",
    "gvc_tmi_tilt",
    "gvc_tmi_tilt_grad",
    "gvc_grav_tilt_grad",
    "gvc_tmi_shallow_demag",
    "gvc_basement_step_grad",
    "gvc_transtension_potency",
    "gvc_piedmont_inflection",
    "gvc_elev_local_resid",
    "gvc_dem_lineament_900m",
    "gvc_lidar_lineament_900m",
    "gvc_grav_mag_coalign_2km",
)

FORBIDDEN_COLUMNS: frozenset[str] = frozenset(
    {"dist_known_fault_px", "fault_dist", "qfault_dist", "known_fault"}
)


def _nearest_fill(arr: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """Fill missing cells with nearest valid value strictly for spatial filtering."""
    v = np.asarray(valid, bool) & np.isfinite(arr)
    if not v.any():
        return np.zeros(arr.shape, dtype=np.float32)
    if v.all():
        return np.asarray(arr, dtype=np.float32)
    inds = distance_transform_edt(~v, return_distances=False, return_indices=True)
    return np.asarray(arr, dtype=np.float32)[tuple(inds)]


def _robust_z(arr: np.ndarray, valid: np.ndarray) -> np.ndarray:
    v = np.asarray(valid, bool) & np.isfinite(arr)
    vals = arr[v]
    med = float(np.median(vals))
    q25, q75 = np.quantile(vals, [0.25, 0.75])
    iqr = max(float(q75 - q25), 1e-6)
    out = np.zeros(arr.shape, dtype=np.float32)
    out[v] = np.clip((arr[v] - med) / iqr, -8.0, 8.0)
    return out


def _grad_mag(arr_filled: np.ndarray) -> np.ndarray:
    gy, gx = np.gradient(arr_filled.astype(np.float32, copy=False))
    return np.hypot(gx, gy).astype(np.float32)


def oriented_lineament_response(
    field_2d: np.ndarray,
    valid: np.ndarray,
    *,
    half_len_px: int = 4,
    flank_offset_px: int | None = 3,
    n_azimuths: int = 8,
) -> np.ndarray:
    """Max over azimuths of along-strike mean minus orthogonal cross-strike flanks."""
    f_fill = _nearest_fill(field_2d, valid)
    pad_w = max(half_len_px, flank_offset_px or 0) + 1
    padded = np.pad(f_fill, pad_w, mode="edge")
    h, w = field_2d.shape
    best = np.full((h, w), -np.inf, dtype=np.float32)

    for m in range(n_azimuths):
        theta = m * np.pi / n_azimuths
        st, ct = float(np.sin(theta)), float(np.cos(theta))
        along_pts = sorted(
            {(int(round(t * st)), int(round(t * ct))) for t in range(-half_len_px, half_len_px + 1)}
        )
        acc = np.zeros((h, w), dtype=np.float32)
        for dy, dx in along_pts:
            acc += padded[pad_w + dy : pad_w + dy + h, pad_w + dx : pad_w + dx + w]
        acc /= float(len(along_pts))

        if flank_offset_px is not None and flank_offset_px > 0:
            fy = int(round(flank_offset_px * ct))
            fx = int(round(-flank_offset_px * st))
            if fy == 0 and fx == 0:
                fy = flank_offset_px
            flank = 0.5 * (
                padded[pad_w + fy : pad_w + fy + h, pad_w + fx : pad_w + fx + w]
                + padded[pad_w - fy : pad_w - fy + h, pad_w - fx : pad_w - fx + w]
            )
            resp = acc - flank
        else:
            resp = acc
        np.maximum(best, resp, out=best)

    best[~valid] = np.nan
    return best


def load_ingenious_geothermal_features(
    root: Path,
    shape: tuple[int, int],
    transform: rasterio.Affine,
    footprint: np.ndarray,
) -> dict[str, np.ndarray]:
    """Build the 4 INGENIOUS geothermal vent, 2m probe, and spring/geothermometer fields."""
    h, w = shape
    inv_tr = ~transform
    to_utm11 = Transformer.from_crs("EPSG:4269", "EPSG:32611", always_xy=True)

    # 1. Paleo-geothermal sinter / travertine / tufa fossil vent deposits
    paleo_zip = root / "data/external/paleo_geothermal_regional.zip"
    with zipfile.ZipFile(paleo_zip) as z:
        df_paleo = pd.read_csv(z.open("Paleo_geothermal_final.csv"), encoding="cp1252")
    bad_paleo = set(df_paleo.columns.str.lower()) & FORBIDDEN_COLUMNS
    if bad_paleo:
        raise RuntimeError(f"Forbidden fault column in paleo CSV: {bad_paleo}")
    px_x, px_y = to_utm11.transform(
        df_paleo["Long_deg_NAD83"].to_numpy(dtype=np.float64),
        df_paleo["Lat_deg_NAD83"].to_numpy(dtype=np.float64),
    )
    cols_f, rows_f = inv_tr * (px_x, px_y)
    rows_i = np.floor(rows_f).astype(np.int64)
    cols_i = np.floor(cols_f).astype(np.int64)
    in_box = (rows_i >= 0) & (rows_i < h) & (cols_i >= 0) & (cols_i < w)
    paleo_mask = np.zeros((h, w), dtype=bool)
    paleo_mask[rows_i[in_box], cols_i[in_box]] = True
    if not paleo_mask.any():
        raise RuntimeError("No INGENIOUS paleo-geothermal deposits mapped onto template grid")
    paleo_logd = (-np.log1p(distance_transform_edt(~paleo_mask))).astype(np.float32)
    paleo_logd[~footprint] = np.nan

    # 2. Shallow 2-meter temperature probe normalized anomalies (F2mDAB > 0)
    probe_zip = root / "data/external/2m_temperature_probe_INGENIOUS_regional_data.zip"
    with zipfile.ZipFile(probe_zip) as z:
        shp_b = io.BytesIO(
            z.read(
                "2m_temperature_probe_INGENIOUS_regional_data/2m_temperature_probe_n83geo/2m_temperature_probe_n83geo.shp"
            )
        )
        dbf_b = io.BytesIO(
            z.read(
                "2m_temperature_probe_INGENIOUS_regional_data/2m_temperature_probe_n83geo/2m_temperature_probe_n83geo.dbf"
            )
        )
        sf = shapefile.Reader(shp=shp_b, dbf=dbf_b, encoding="cp1252")
        field_names = [f[0] for f in sf.fields[1:]]
        if {n.lower() for n in field_names} & FORBIDDEN_COLUMNS:
            raise RuntimeError("Forbidden fault column in 2m probe shapefile")
        idx_dab = field_names.index("F2mDAB")
        idx_lon = field_names.index("LongDegree")
        idx_lat = field_names.index("LatDegreeN")
        lons, lats, dabs = [], [], []
        for rec in sf.iterRecords():
            try:
                lon_v = float(rec[idx_lon])
                lat_v = float(rec[idx_lat])
                dab_v = float(rec[idx_dab])
            except (TypeError, ValueError):
                continue
            if np.isfinite(lon_v) and np.isfinite(lat_v) and np.isfinite(dab_v):
                lons.append(lon_v)
                lats.append(lat_v)
                dabs.append(max(0.0, dab_v))
    ux, uy = to_utm11.transform(np.asarray(lons, float), np.asarray(lats, float))
    cf, rf = inv_tr * (ux, uy)
    ri = np.floor(rf).astype(np.int64)
    ci = np.floor(cf).astype(np.int64)
    ok = (ri >= 0) & (ri < h) & (ci >= 0) & (ci < w)
    val_grid = np.zeros((h, w), dtype=np.float32)
    cnt_grid = np.zeros((h, w), dtype=np.float32)
    np.add.at(val_grid, (ri[ok], ci[ok]), np.asarray(dabs, dtype=np.float32)[ok])
    np.add.at(cnt_grid, (ri[ok], ci[ok]), 1.0)
    num_2m = gaussian_filter(val_grid, sigma=15.0)
    den_2m = gaussian_filter(cnt_grid, sigma=15.0)
    probe2m = (num_2m / (den_2m + 0.02)).astype(np.float32)
    probe2m[~footprint] = np.nan

    # 3 & 4. GDR wells & springs: drop dist_known_fault_px immediately, use only coordinates & temperatures
    ws_csv = root / "data/external/gdr_wellspring_in_footprint.csv"
    allowed_ws = [
        "utm_x",
        "utm_y",
        "temp_c",
        "geothermquartz_c",
        "geothermchalc_c",
        "geothermcat_c",
    ]
    df_ws = pd.read_csv(ws_csv, usecols=allowed_ws)
    if set(df_ws.columns.str.lower()) & FORBIDDEN_COLUMNS:
        raise RuntimeError("Forbidden fault column loaded from wellspring CSV")
    w_cf, w_rf = inv_tr * (
        df_ws["utm_x"].to_numpy(dtype=np.float64),
        df_ws["utm_y"].to_numpy(dtype=np.float64),
    )
    w_ri = np.floor(w_rf).astype(np.int64)
    w_ci = np.floor(w_cf).astype(np.int64)
    w_ok = (w_ri >= 0) & (w_ri < h) & (w_ci >= 0) & (w_ci < w)

    temp_c = pd.to_numeric(df_ws["temp_c"], errors="coerce").to_numpy(dtype=np.float64)
    hot = w_ok & np.isfinite(temp_c) & (temp_c >= 37.0)
    hot_mask = np.zeros((h, w), dtype=bool)
    hot_mask[w_ri[hot], w_ci[hot]] = True
    if not hot_mask.any():
        raise RuntimeError("No hot springs/wells >= 37C found in footprint")
    spring_hot_logd = (-np.log1p(distance_transform_edt(~hot_mask))).astype(np.float32)
    spring_hot_logd[~footprint] = np.nan

    gt_cols = np.column_stack(
        [
            pd.to_numeric(df_ws[c], errors="coerce").to_numpy(dtype=np.float64)
            for c in ("geothermquartz_c", "geothermchalc_c", "geothermcat_c")
        ]
    )
    import warnings

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="All-NaN slice encountered")
        gt_max = np.nanmax(gt_cols, axis=1)
    gt_excess = np.where(np.isfinite(gt_max), np.clip(gt_max - 60.0, 0.0, 220.0), 0.0)
    gt_pos = w_ok & (gt_excess > 0.0)
    gt_val = np.zeros((h, w), dtype=np.float32)
    gt_cnt = np.zeros((h, w), dtype=np.float32)
    np.add.at(gt_val, (w_ri[gt_pos], w_ci[gt_pos]), gt_excess[gt_pos].astype(np.float32))
    np.add.at(gt_cnt, (w_ri[gt_pos], w_ci[gt_pos]), 1.0)
    geotherm_halo = (
        gaussian_filter(gt_val, sigma=25.0) / (gaussian_filter(gt_cnt, sigma=25.0) + 0.02)
    ).astype(np.float32)
    geotherm_halo[~footprint] = np.nan

    return {
        "gvc_paleo_sinter_logd": paleo_logd,
        "gvc_probe2m_anom_1p5km": probe2m,
        "gvc_spring_hot_logd": spring_hot_logd,
        "gvc_geotherm_halo_2p5km": geotherm_halo,
    }


def build_gvc1_features(
    root: Path,
    base_memmap: np.ndarray,
    base_names: list[str],
    footprint: np.ndarray,
    transform: rasterio.Affine,
    out_npy_path: Path,
) -> tuple[np.ndarray, list[str]]:
    """Construct all 18 label-free GVC1 features onto a disk-backed float32 memmap."""
    h, w = footprint.shape
    fp_idx = np.flatnonzero(footprint.ravel())
    if base_memmap.shape != (len(fp_idx), len(base_names)):
        raise ValueError("Base feature memmap shape mismatch")

    out_npy_path.parent.mkdir(parents=True, exist_ok=True)
    gvc_mm = np.lib.format.open_memmap(
        out_npy_path,
        mode="w+",
        dtype=np.float32,
        shape=(len(fp_idx), len(GVC1_FEATURE_NAMES)),
    )

    def unpack_col(name: str) -> np.ndarray:
        col = base_names.index(name)
        grid = np.full((h, w), np.nan, dtype=np.float32)
        grid.ravel()[fp_idx] = base_memmap[:, col]
        return grid

    def write_feature(name: str, grid_2d: np.ndarray) -> None:
        col = GVC1_FEATURE_NAMES.index(name)
        gvc_mm[:, col] = grid_2d.ravel()[fp_idx].astype(np.float32)

    # 1..4: INGENIOUS geothermal vent / shallow 2m probe / spring & geothermometer fields
    geo_fields = load_ingenious_geothermal_features(root, (h, w), transform, footprint)
    for k, v in geo_fields.items():
        write_feature(k, v)
    del geo_fields
    gc.collect()

    # 5, 6, 11: Radiometrics (K, ThK, UTh) and shallow demagnetization (TMI_up150 vs rtp)
    rad_path = root / "data/external/geodawn_rad_u8.tif"
    ext_path = root / "data/external/geodawn_extensions_u8.tif"
    with rasterio.open(rad_path) as ds_rad, rasterio.open(ext_path) as ds_ext:
        k_u8 = ds_rad.read(1).astype(np.float32)
        thk_u8 = ds_ext.read(1).astype(np.float32)
        uth_u8 = ds_ext.read(3).astype(np.float32)
        tmi_up150_u8 = ds_ext.read(4).astype(np.float32)

    k_valid = footprint & (k_u8 > 0)
    thk_valid = footprint & (thk_u8 > 0)
    both_kt = k_valid & thk_valid
    k_fill = _nearest_fill(k_u8, k_valid)
    thk_fill = _nearest_fill(thk_u8, thk_valid)
    k_loc = (k_fill - gaussian_filter(k_fill, sigma=20.0)) / (
        np.sqrt(gaussian_filter((k_fill - gaussian_filter(k_fill, sigma=20.0)) ** 2, sigma=20.0))
        + 1.0
    )
    thk_loc = (thk_fill - gaussian_filter(thk_fill, sigma=20.0)) / (
        np.sqrt(
            gaussian_filter((thk_fill - gaussian_filter(thk_fill, sigma=20.0)) ** 2, sigma=20.0)
        )
        + 1.0
    )
    rad_alter = np.where(both_kt, k_loc - thk_loc, np.nan).astype(np.float32)
    write_feature("gvc_rad_k_thk_alter", rad_alter)
    del k_u8, thk_u8, k_fill, thk_fill, k_loc, thk_loc, rad_alter

    uth_valid = footprint & (uth_u8 > 0)
    uth_fill = _nearest_fill(uth_u8, uth_valid)
    uth_excess = np.where(uth_valid, uth_fill - gaussian_filter(uth_fill, sigma=20.0), np.nan)
    write_feature("gvc_rad_uth_excess", uth_excess.astype(np.float32))
    del uth_u8, uth_fill, uth_excess

    rtp = unpack_col("rtp")
    up_valid = footprint & (tmi_up150_u8 > 0) & np.isfinite(rtp)
    z_up = _robust_z(tmi_up150_u8, up_valid)
    z_rtp = _robust_z(rtp, up_valid)
    diff_mag = _nearest_fill(z_up - z_rtp, up_valid)
    shallow_demag = np.where(
        up_valid, gaussian_filter(diff_mag, sigma=20.0) - diff_mag, np.nan
    ).astype(np.float32)
    write_feature("gvc_tmi_shallow_demag", shallow_demag)
    del tmi_up150_u8, rtp, z_up, z_rtp, diff_mag, shallow_demag
    gc.collect()

    # 7: MT shallow conductivity clay-cap boundary gradient
    cond = unpack_col("cond_surf")
    cond_v = footprint & np.isfinite(cond)
    cond_log = _nearest_fill(np.log1p(np.maximum(cond, 0.0)), cond_v)
    cond_grad = np.where(cond_v, _grad_mag(gaussian_filter(cond_log, sigma=1.5)), np.nan)
    write_feature("gvc_cond_clay_grad", cond_grad.astype(np.float32))
    del cond, cond_log, cond_grad

    # 8 & 9: Miller & Singh (1994) magnetic tilt angle & contact sharpness
    tmi_hg = unpack_col("tmi_hg")
    tmi_vg = unpack_col("tmi_vg")
    mag_v = footprint & np.isfinite(tmi_hg) & np.isfinite(tmi_vg)
    tilt_mag = np.arctan2(tmi_vg, np.sqrt(np.maximum(tmi_hg, 0.0) ** 2 + 1e-6)).astype(np.float32)
    tilt_mag_f = _nearest_fill(tilt_mag, mag_v)
    tilt_mag_grad = np.where(mag_v, _grad_mag(tilt_mag_f), np.nan).astype(np.float32)
    tilt_mag[~mag_v] = np.nan
    write_feature("gvc_tmi_tilt", tilt_mag)
    write_feature("gvc_tmi_tilt_grad", tilt_mag_grad)
    del tmi_vg, tilt_mag, tilt_mag_f, tilt_mag_grad

    # 10 & 18: Gravity tilt contact sharpness & 2.1 km gravity-magnetic horizontal-gradient co-alignment
    grav_hg = unpack_col("iso_grav_anom_hg")
    grav_vg = unpack_col("iso_grav_anom_vg")
    grav_v = footprint & np.isfinite(grav_hg) & np.isfinite(grav_vg)
    tilt_grav_f = _nearest_fill(
        np.arctan2(grav_vg, np.sqrt(np.maximum(grav_hg, 0.0) ** 2 + 1e-6)).astype(np.float32),
        grav_v,
    )
    tilt_grav_grad = np.where(grav_v, _grad_mag(tilt_grav_f), np.nan).astype(np.float32)
    write_feature("gvc_grav_tilt_grad", tilt_grav_grad)
    del grav_vg, tilt_grav_f, tilt_grav_grad

    gm_v = footprint & np.isfinite(grav_hg) & np.isfinite(tmi_hg)
    zg_pos = np.maximum(_robust_z(grav_hg, gm_v), 0.0)
    zm_pos = np.maximum(_robust_z(tmi_hg, gm_v), 0.0)
    gm_prod = np.sqrt(zg_pos * zm_pos).astype(np.float32)
    coalign_2km = oriented_lineament_response(
        gm_prod, gm_v, half_len_px=10, flank_offset_px=None, n_azimuths=8
    )
    write_feature("gvc_grav_mag_coalign_2km", coalign_2km)
    del tmi_hg, grav_hg, zg_pos, zm_pos, gm_prod, coalign_2km
    gc.collect()

    # 12: Concealed basement step gradient
    base_d = unpack_col("depth_to_base_surf")
    bd_v = footprint & np.isfinite(base_d)
    bd_grad = np.where(bd_v, _grad_mag(gaussian_filter(_nearest_fill(base_d, bd_v), 1.5)), np.nan)
    write_feature("gvc_basement_step_grad", bd_grad.astype(np.float32))
    del base_d, bd_grad

    # 13: Geodetic transtensional dilation x shear potency
    dil = unpack_col("geod_dilaterate")
    shr = unpack_col("geod_shearrate")
    geo_v = footprint & np.isfinite(dil) & np.isfinite(shr)
    potency = np.where(geo_v, _robust_z(dil, geo_v) * _robust_z(shr, geo_v), np.nan)
    write_feature("gvc_transtension_potency", potency.astype(np.float32))
    del dil, shr, potency

    # 14, 15, 16: Piedmont break-in-slope, local elevation residual & 900 m DEM lineament persistence
    elev = unpack_col("det_elev")
    slope = unpack_col("det_elev_slope")
    loc_rel = unpack_col("det_local_relief")
    dem_v = footprint & np.isfinite(elev) & np.isfinite(slope)
    elev_f = _nearest_fill(elev, dem_v)
    slope_f = _nearest_fill(np.maximum(slope, 0.0), dem_v)
    elev_resid_12 = elev_f - gaussian_filter(elev_f, sigma=12.0)
    piedmont = (
        gaussian_filter(slope_f, sigma=15.0) - gaussian_filter(slope_f, sigma=3.0)
    ) * np.log1p(np.maximum(elev_f - gaussian_filter(elev_f, sigma=25.0) + 50.0, 0.0))
    piedmont_out = np.where(dem_v, piedmont, np.nan).astype(np.float32)
    elev_resid_out = np.where(dem_v, elev_resid_12, np.nan).astype(np.float32)
    write_feature("gvc_piedmont_inflection", piedmont_out)
    write_feature("gvc_elev_local_resid", elev_resid_out)
    del elev, elev_f, piedmont, piedmont_out, elev_resid_12, elev_resid_out

    dem_break = np.abs(_nearest_fill(loc_rel, dem_v)) * np.log1p(slope_f)
    dem_line_900 = oriented_lineament_response(
        dem_break, dem_v, half_len_px=4, flank_offset_px=3, n_azimuths=8
    )
    write_feature("gvc_dem_lineament_900m", dem_line_900)
    del slope, loc_rel, slope_f, dem_break, dem_line_900
    gc.collect()

    # 17: 900 m oriented lineament persistence on 1 m LiDAR scarp step_max (lidar_3); 0 outside LiDAR coverage
    lidar_step = unpack_col("lidar_3")
    lid_v = footprint & np.isfinite(lidar_step)
    lid_resp = oriented_lineament_response(
        np.where(lid_v, lidar_step, 0.0), lid_v, half_len_px=4, flank_offset_px=3, n_azimuths=8
    )
    lid_out = np.where(footprint, np.where(lid_v, lid_resp, 0.0), np.nan).astype(np.float32)
    write_feature("gvc_lidar_lineament_900m", lid_out)
    del lidar_step, lid_resp, lid_out
    gvc_mm.flush()
    gc.collect()

    return gvc_mm, list(GVC1_FEATURE_NAMES)


def submodular_dti_allocate(
    prob: np.ndarray,
    valid: np.ndarray,
    visible_faults: np.ndarray,
    *,
    budget: int,
    min_spacing_px: float = 2.5,
    catalogue_clearance_px: float = 2.0,
) -> np.ndarray:
    """Exact Minoux (1978) lazy-greedy maximization of expected 300 m kernel coverage.

    Maximizes ``U(S) = sum_y p(y) max_{s in S} k(||y - s||_2)`` over the official
    ``R = 3.0 px`` (300 m) triangular kernel ``KERNEL_OFFSETS`` subject to minimum
    inter-dot spacing ``min_spacing_px`` and off-catalogue mapping-apron clearance
    ``EDT(~visible_faults) > catalogue_clearance_px``.
    """
    prob_2d = np.asarray(prob, dtype=np.float32)
    valid_2d = np.asarray(valid, bool)
    vis_2d = np.asarray(visible_faults, bool)
    if prob_2d.shape != valid_2d.shape or vis_2d.shape != valid_2d.shape:
        raise ValueError("Aligned 2D grids required for submodular allocation")
    if budget <= 0:
        return np.zeros(prob_2d.shape, dtype=np.float32)

    if vis_2d.any():
        dist_vis = distance_transform_edt(~vis_2d)
        eligible = valid_2d & ~vis_2d & (dist_vis > catalogue_clearance_px)
    else:
        eligible = valid_2d.copy()
    eligible &= np.isfinite(prob_2d) & (prob_2d > 0.0)

    cand_ids = np.flatnonzero(eligible.ravel())
    if not len(cand_ids):
        return np.zeros(prob_2d.shape, dtype=np.float32)

    pool_cap = min(len(cand_ids), max(budget * 7, 90_000))
    cand_scores = prob_2d.ravel()[cand_ids]
    if len(cand_ids) > pool_cap:
        part = np.argpartition(-cand_scores, pool_cap - 1)[:pool_cap]
        cand_ids = cand_ids[part]
        cand_scores = cand_scores[part]
    order = np.lexsort((cand_ids, -cand_scores))
    cand_ids = cand_ids[order]

    h, w = prob_2d.shape
    pad = int(np.ceil(max(RADIUS_PX, min_spacing_px))) + 1
    hp, wp = h + 2 * pad, w + 2 * pad

    # Probability mass exists only on active off-visible evaluation domain
    active_mass = np.where(
        valid_2d & ~vis_2d & np.isfinite(prob_2d), np.clip(prob_2d, 0.0, 1.0), 0.0
    )
    p_pad = np.zeros((hp, wp), dtype=np.float32)
    p_pad[pad : pad + h, pad : pad + w] = active_mass

    # Vectorized initial upper bound u_0(x) = sum_{(dy,dx,k)} p(x + d) * k
    ub_grid = np.zeros((h, w), dtype=np.float32)
    for dy, dx, k in KERNEL_OFFSETS:
        ub_grid += p_pad[pad + dy : pad + dy + h, pad + dx : pad + dx + w] * np.float32(k)

    cy, cx = np.unravel_index(cand_ids, (h, w))
    init_ub = ub_grid[cy, cx]

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

    centers = (cy + pad) * wp + (cx + pad)
    heap: list[tuple[float, int, int, int, int]] = [
        (-float(init_ub[i]), int(i), int(centers[i]), int(cy[i]), int(cx[i]))
        for i in range(len(cand_ids))
        if init_ub[i] > 0.0
    ]
    heapq.heapify(heap)

    out = np.zeros((h, w), dtype=np.float32)
    selected = 0
    while heap and selected < budget:
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
        selected += 1

    return out


def _sample_train_indices(
    train_mask: np.ndarray,
    visible_mask: np.ndarray,
    footprint: np.ndarray,
    *,
    max_negatives: int,
    seed: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return footprint-row indices, binary labels, and 20 km block IDs strictly from train & visible."""
    fp_lookup = np.full(footprint.shape, -1, dtype=np.int32)
    fp_lookup.ravel()[np.flatnonzero(footprint.ravel())] = np.arange(
        int(footprint.sum()), dtype=np.int32
    )

    pos_mask = train_mask & visible_mask & footprint
    neg_mask = train_mask & footprint & (distance_transform_edt(~visible_mask) >= 9.0)
    pos_yx = np.argwhere(pos_mask)
    neg_yx = np.argwhere(neg_mask)
    if len(pos_yx) < 50 or len(neg_yx) < 500:
        raise ValueError("Insufficient training positives or >=900m background pixels")

    rng = np.random.default_rng(seed)
    if len(neg_yx) > max_negatives:
        take = rng.choice(len(neg_yx), size=max_negatives, replace=False)
        neg_yx = neg_yx[take]

    yx = np.vstack([pos_yx, neg_yx])
    fp_rows = fp_lookup[yx[:, 0], yx[:, 1]]
    y = np.concatenate([np.ones(len(pos_yx), dtype=np.int8), np.zeros(len(neg_yx), dtype=np.int8)])
    nx_blk = (footprint.shape[1] + 199) // 200
    blocks_20km = (yx[:, 0] // 200) * nx_blk + (yx[:, 1] // 200)
    return fp_rows, y, blocks_20km


def _read_rows_concat(
    rows: np.ndarray, base_mm: np.ndarray, extra_mm: np.ndarray | None
) -> np.ndarray:
    x_base = np.asarray(base_mm[rows], dtype=np.float32)
    if extra_mm is None:
        return x_base
    x_ext = np.asarray(extra_mm[rows], dtype=np.float32)
    return np.hstack([x_base, x_ext])


def fit_predict_calibrated_hgb(
    base_mm: np.ndarray,
    extra_mm: np.ndarray | None,
    nuisance_mm: np.ndarray | None,
    *,
    train_mask: np.ndarray,
    visible_mask: np.ndarray,
    predict_mask: np.ndarray,
    footprint: np.ndarray,
    seed: int,
    max_negatives: int = 220_000,
    residualize: bool = False,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Fit 2-seed spatially calibrated HGB strictly on ``train_mask`` and predict ``predict_mask``."""
    fp_rows, y, blk20 = _sample_train_indices(
        train_mask, visible_mask, footprint, max_negatives=max_negatives, seed=seed
    )
    X = _read_rows_concat(fp_rows, base_mm, extra_mm)

    cal_hold = (blk20 % 6) == 0
    if cal_hold.sum() < 200 or (~cal_hold).sum() < 1000 or len(np.unique(y[cal_hold])) < 2:
        # Deterministic fallback to modulo-5 if modulo-6 lacks positives
        cal_hold = (blk20 % 5) == 0
    fit_sel = ~cal_hold

    resid: NuisanceResidualizer | None = None
    if residualize:
        if nuisance_mm is None:
            raise ValueError("Residualized arm requires aligned nuisance matrix")
        C_all = np.asarray(nuisance_mm[fp_rows], dtype=np.float32)
        rng_r = np.random.default_rng(seed + 31)
        bg_rows = np.flatnonzero(train_mask.ravel()[np.flatnonzero(footprint.ravel())])
        bg_take = rng_r.choice(bg_rows, size=min(120_000, len(bg_rows)), replace=False)
        C_bg = np.asarray(nuisance_mm[bg_take], dtype=np.float32)
        G_bg = _read_rows_concat(bg_take, base_mm, extra_mm)
        resid = NuisanceResidualizer(distance_columns=2, alpha=100.0).fit(C_bg, G_bg)
        X = resid.transform(C_all, X, remove=True)
        del C_all, C_bg, G_bg

    models: list[HistGradientBoostingClassifier] = []
    with threadpool_limits(limits=2):
        for s_off in (100, 200):
            clf = HistGradientBoostingClassifier(
                max_iter=220,
                learning_rate=0.05,
                max_leaf_nodes=31,
                min_samples_leaf=80,
                l2_regularization=3.0,
                early_stopping=False,
                random_state=seed + s_off,
            )
            clf.fit(X[fit_sel], y[fit_sel])
            models.append(clf)

        raw_cal = 0.5 * (
            models[0].predict_proba(X[cal_hold])[:, 1] + models[1].predict_proba(X[cal_hold])[:, 1]
        )
        iso = IsotonicRegression(y_min=0.0, y_max=1.0, out_of_bounds="clip")
        iso.fit(raw_cal, y[cal_hold].astype(np.float64))

        # Chunked prediction over requested footprint subset to keep RAM < 700 MB
        fp_flat_ids = np.flatnonzero(footprint.ravel())
        pred_in_fp = predict_mask.ravel()[fp_flat_ids]
        target_rows = np.flatnonzero(pred_in_fp)
        pred_vals = np.zeros(len(fp_flat_ids), dtype=np.float32)
        chunk = 250_000
        for start in range(0, len(target_rows), chunk):
            sl = target_rows[start : start + chunk]
            X_chunk = _read_rows_concat(sl, base_mm, extra_mm)
            if resid is not None:
                C_chunk = np.asarray(nuisance_mm[sl], dtype=np.float32)
                X_chunk = resid.transform(C_chunk, X_chunk, remove=True)
            raw_p = 0.5 * (
                models[0].predict_proba(X_chunk)[:, 1] + models[1].predict_proba(X_chunk)[:, 1]
            )
            pred_vals[sl] = iso.transform(raw_p).astype(np.float32)

    out_2d = np.zeros(footprint.shape, dtype=np.float32)
    out_2d.ravel()[fp_flat_ids] = pred_vals
    meta = {
        "n_train_pos": int((y == 1).sum()),
        "n_train_neg": int((y == 0).sum()),
        "n_fit_samples": int(fit_sel.sum()),
        "n_cal_samples": int(cal_hold.sum()),
        "n_features": int(X.shape[1]),
        "residualized": bool(residualize),
    }
    del X
    gc.collect()
    return out_2d, meta


def fit_predict_legacy_ridge_baseline(
    base_mm: np.ndarray,
    *,
    train_mask: np.ndarray,
    visible_mask: np.ndarray,
    valid_mask: np.ndarray,
    footprint: np.ndarray,
    seed: int,
    budget_fraction: float = 0.0245,
) -> np.ndarray:
    """Reconstruct GEMSDOE24's legacy h24_2_experiment HGB + ridge_nms arm leak-free on SegmentHoldout."""
    fp_rows, y, _ = _sample_train_indices(
        train_mask, visible_mask, footprint, max_negatives=200_000, seed=seed
    )
    X = np.asarray(base_mm[fp_rows], dtype=np.float32)
    with threadpool_limits(limits=2):
        clf = HistGradientBoostingClassifier(
            max_iter=180,
            learning_rate=0.06,
            max_leaf_nodes=31,
            min_samples_leaf=80,
            l2_regularization=2.0,
            early_stopping=False,
            random_state=seed,
        ).fit(X, y)
        fp_flat_ids = np.flatnonzero(footprint.ravel())
        target_rows = np.flatnonzero(valid_mask.ravel()[fp_flat_ids])
        pred_vals = np.zeros(len(fp_flat_ids), dtype=np.float32)
        chunk = 250_000
        for start in range(0, len(target_rows), chunk):
            sl = target_rows[start : start + chunk]
            pred_vals[sl] = clf.predict_proba(np.asarray(base_mm[sl], dtype=np.float32))[:, 1]
    del X
    gc.collect()

    surf = np.zeros(footprint.shape, dtype=np.float32)
    surf.ravel()[fp_flat_ids] = pred_vals
    active = valid_mask & ~visible_mask
    ridge = ridge_nms(surf, valid_mask, sigma=1.0) & active
    k = int(round(budget_fraction * int(active.sum())))
    return select_top_positive(surf, ridge, k).astype(np.float32)
