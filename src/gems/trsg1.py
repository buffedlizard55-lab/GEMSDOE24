"""H24-TRSG1: Two-Regime Seismic-Geothermal Step-Over & Terrain-Conditioned Stitched-OOF Detector.

Implements the locked preregistered specification in
``knowledge/19_preregistered_TRSG1_2026-10-26.md``:
- Reuses the 30-channel cached competition stack (``data/prepared/features.npy``),
  restores all 6 omitted ``data/training_features.tif`` physical bands (including
  previously unused seismicity bands ``ieq_n100a15`` and ``deq_n100a15``, with
  ``IR-BAND-PROVENANCE`` disclosed), and computes 8 scale-localized seismic-fabric,
  Faulds & Hinz (2015) hyperbolic relay-ramp saddle, piedmont/drainage breakline,
  Quaternary volcanic-vent demagnetization, Th-normalized K/U alteration, and
  sub-alluvial Euler-like basement-step channels (44 channels total; zero catalogue
  or global radial EDT features).
- ``TerrainReliefRegimeCalibrator`` removes smooth road/claim/block background
  log-odds shifts and aligns ``~has_lidar`` vs. ``has_lidar`` quantiles strictly
  within matching terrain-relief tertiles (fixing ``RSHG1``'s ``SW`` basin
  over-amplification while preserving ``NE_LidarGapHeavy`` mountain recovery).
- ``make_rotated45_folds`` constructs a 45°-rotated whole-component 1.5 km-buffered
  4-sector spatial partition so full-footprint deployment uses a 100% out-of-fold
  Dual-Partition Stitched-OOF surface (``0.5 * P_quad + 0.5 * P_rot45``),
  eliminating ``GVC1``'s in-sample near-catalogue halo collapse.
- ``emit_two_regime_poisson`` allocates binary ``{0, 1}`` fault vertices across
  Concealed Alluvial Basin (``depth_to_base_surf >= 300 m & slope <= 6°``) and
  Range-Front / Step-Over regimes with strict global ``min_dist >= 3.0 px`` and
  ``EDT(~visible) > 2.0 px`` off-catalogue clearance.
"""

from __future__ import annotations

import gc
import io
import warnings
import zipfile
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import rasterio
import shapefile
from pyproj import Transformer
from scipy.ndimage import (
    distance_transform_edt,
    gaussian_filter,
)
from scipy.ndimage import (
    label as ndi_label,
)
from scipy.special import expit, logit
from sklearn.linear_model import Ridge

from . import geofeatures, rshg1
from .emission import priority_poisson
from .residualize import NuisanceResidualizer

FORBIDDEN_COLUMNS: frozenset[str] = frozenset(
    {"dist_known_fault_px", "fault_dist", "qfault_dist", "known_fault"}
)

NUISANCE_KEYS: tuple[str, ...] = rshg1.NUISANCE_KEYS

PREPARED30_NAMES: tuple[str, ...] = (
    rshg1.PREPARED_BASE13 + rshg1.PREPARED_LIDAR12 + rshg1.PREPARED_DERIVED5
)

OMITTED6_NAMES: tuple[str, ...] = (
    "mag_anom",
    "geod_2ndinv",
    "iso_grav_anom_slope",
    "tc",
    "eq_ieq_log",
    "eq_deq_excess",
)

ENGINEERED8_NAMES: tuple[str, ...] = (
    "eq_fabric_aniso",
    "relay_saddle_dem",
    "relay_saddle_pot",
    "piedmont_drainage_break",
    "ing_upflow_dog",
    "qvent_demag_conduit",
    "th_norm_k_u_alt",
    "basement_euler_step",
)

FEATURE_NAMES: tuple[str, ...] = PREPARED30_NAMES + OMITTED6_NAMES + ENGINEERED8_NAMES

SELECTIVE_RESIDUAL_NAMES: frozenset[str] = frozenset(
    {
        "rtp",
        "iso_grav_anom",
        "tmi",
        "cond_surf",
        "depth_to_base_surf",
        "mag_anom",
        "tc",
        "eq_ieq_log",
        "ing_upflow_dog",
        "th_norm_k_u_alt",
    }
)

SELECTIVE_RESIDUAL_INDICES: np.ndarray = np.array(
    [i for i, n in enumerate(FEATURE_NAMES) if n in SELECTIVE_RESIDUAL_NAMES], dtype=np.int64
)

IDX_SLOPE: int = FEATURE_NAMES.index("det_elev_slope")
IDX_DEPTH_BASE: int = FEATURE_NAMES.index("depth_to_base_surf")
IDX_LOCAL_RELIEF: int = FEATURE_NAMES.index("det_local_relief")
IDX_LIDAR1: int = FEATURE_NAMES.index("lidar_1")
SUBSURFACE_CONDUIT_INDICES: np.ndarray = np.array(
    [
        FEATURE_NAMES.index(n)
        for n in (
            "basement_euler_step",
            "relay_saddle_pot",
            "eq_fabric_aniso",
            "ing_upflow_dog",
            "qvent_demag_conduit",
        )
    ],
    dtype=np.int64,
)


def nearest_fill(arr: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """Fill unobserved cells with nearest valid value strictly for local filter stencils."""
    v = np.asarray(valid, dtype=bool) & np.isfinite(arr)
    if not v.any():
        return np.zeros(arr.shape, dtype=np.float32)
    if v.all():
        return np.asarray(arr, dtype=np.float32)
    inds = distance_transform_edt(~v, return_distances=False, return_indices=True)
    return np.asarray(arr, dtype=np.float32)[tuple(inds)]


def robust_z(arr: np.ndarray, valid: np.ndarray, *, clip_val: float = 8.0) -> np.ndarray:
    """Compute IQR-scaled median z-score on valid finite support (`0` outside before masking)."""
    v = np.asarray(valid, dtype=bool) & np.isfinite(arr)
    out = np.zeros(arr.shape, dtype=np.float32)
    if not v.any():
        return out
    vals = np.asarray(arr[v], dtype=np.float64)
    med = float(np.median(vals))
    q25, q75 = np.quantile(vals, [0.25, 0.75])
    iqr = max(float(q75 - q25), float(np.std(vals)) * 0.5, 1e-6)
    out[v] = np.clip((vals - med) / iqr, -clip_val, clip_val).astype(np.float32)
    return out


def hyperbolic_saddle_twist(
    field_2d: np.ndarray, valid: np.ndarray, *, sigma_px: float
) -> np.ndarray:
    """Compute hyperbolic Hessian saddle twist ``sigma^2 * sqrt(max(0, -det H_sigma))``.

    Opposite-sign principal curvatures (``lambda_1 > 0, lambda_2 < 0 => -det H > 0``)
    characterize twisted relay ramps, en-echelon fault step-overs, and transfer zones
    (Faulds & Hinz 2015), whereas pure linear ridges have ``lambda_1 ~ 0 => det H ~ 0``.
    """
    if sigma_px <= 0:
        raise ValueError("sigma_px must be > 0")
    v = np.asarray(valid, dtype=bool) & np.isfinite(field_2d)
    if not v.any():
        return np.full(field_2d.shape, np.nan, dtype=np.float32)
    f = nearest_fill(field_2d, v)
    s = gaussian_filter(f, sigma=float(sigma_px), mode="nearest", truncate=4.0)
    gy, gx = np.gradient(s)
    hyy, hyx = np.gradient(gy)
    hxy_raw, hxx = np.gradient(gx)
    hxy = 0.5 * (hyx + hxy_raw)
    neg_det = np.maximum(-(hxx * hyy - hxy * hxy), 0.0)
    twist = (float(sigma_px * sigma_px) * np.sqrt(neg_det)).astype(np.float32)
    twist[~v] = np.nan
    return twist


def seismic_fabric_anisotropy(
    ieq_log: np.ndarray,
    valid: np.ndarray,
    *,
    grad_sigma_px: float = 1.5,
    tensor_sigma_px: float = 6.0,
) -> np.ndarray:
    """Compute structure-tensor linear coherence ``((mu1 - mu2)/(mu1 + mu2)) * sqrt(mu1)``."""
    v = np.asarray(valid, dtype=bool) & np.isfinite(ieq_log)
    if not v.any():
        return np.full(ieq_log.shape, np.nan, dtype=np.float32)
    f = nearest_fill(ieq_log, v)
    gx = gaussian_filter(f, sigma=float(grad_sigma_px), order=(0, 1), mode="nearest", truncate=3.0)
    gy = gaussian_filter(f, sigma=float(grad_sigma_px), order=(1, 0), mode="nearest", truncate=3.0)
    jxx = gaussian_filter(gx * gx, sigma=float(tensor_sigma_px), mode="nearest", truncate=3.0)
    jyy = gaussian_filter(gy * gy, sigma=float(tensor_sigma_px), mode="nearest", truncate=3.0)
    jxy = gaussian_filter(gx * gy, sigma=float(tensor_sigma_px), mode="nearest", truncate=3.0)
    tr = np.maximum(jxx + jyy, 0.0)
    disc = np.sqrt(np.maximum((jxx - jyy) ** 2 + 4.0 * jxy * jxy, 0.0))
    mu1 = 0.5 * (tr + disc)
    coh = (disc / (tr + 1e-6)) * np.sqrt(np.maximum(mu1, 0.0))
    out = coh.astype(np.float32)
    out[~v] = np.nan
    return out


def local_dog_positive(
    impulse_grid: np.ndarray,
    footprint: np.ndarray,
    *,
    sigma_narrow_px: float,
    sigma_wide_px: float,
    wide_weight: float = 0.65,
) -> np.ndarray:
    """Scale-localized non-negative Difference-of-Gaussians (zero global radial bullseyes)."""
    if sigma_narrow_px <= 0 or sigma_wide_px <= sigma_narrow_px:
        raise ValueError("Require 0 < sigma_narrow_px < sigma_wide_px")
    g = np.asarray(impulse_grid, dtype=np.float32)
    narrow = gaussian_filter(g, sigma=float(sigma_narrow_px), mode="constant", cval=0.0)
    wide = gaussian_filter(g, sigma=float(sigma_wide_px), mode="constant", cval=0.0)
    dog = np.maximum(narrow - float(wide_weight) * wide, 0.0).astype(np.float32)
    dog[~np.asarray(footprint, dtype=bool)] = np.nan
    return dog


def load_localized_upflow_and_vents(
    root: Path,
    shape: tuple[int, int],
    transform: rasterio.Affine,
    footprint: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Build localized INGENIOUS upflow DoG (800m - 3km) and Quaternary vent impulse (1.2km - 3.6km).

    Strictly asserts ``FORBIDDEN_COLUMNS`` are absent from every loaded table and
    never reads ``gdr_qfaults_traces.csv`` or any submission raster.
    """
    h, w = shape
    fp = np.asarray(footprint, dtype=bool)
    inv_tr = ~transform
    to_utm11 = Transformer.from_crs("EPSG:4269", "EPSG:32611", always_xy=True)

    # 1. Paleo-geothermal sinter / travertine / tufa fossil vent sites
    paleo_zip = root / "data/external/paleo_geothermal_regional.zip"
    with zipfile.ZipFile(paleo_zip) as z:
        df_paleo = pd.read_csv(z.open("Paleo_geothermal_final.csv"), encoding="cp1252")
    if set(df_paleo.columns.str.lower()) & FORBIDDEN_COLUMNS:
        raise RuntimeError("Forbidden fault column in Paleo_geothermal_final.csv")
    px_x, px_y = to_utm11.transform(
        df_paleo["Long_deg_NAD83"].to_numpy(dtype=np.float64),
        df_paleo["Lat_deg_NAD83"].to_numpy(dtype=np.float64),
    )
    cf, rf = inv_tr * (px_x, px_y)
    ri, ci = np.floor(rf).astype(np.int64), np.floor(cf).astype(np.int64)
    ok = (ri >= 0) & (ri < h) & (ci >= 0) & (ci < w)
    paleo_imp = np.zeros((h, w), dtype=np.float32)
    np.add.at(paleo_imp, (ri[ok], ci[ok]), 1.0)
    dog_paleo = local_dog_positive(paleo_imp, fp, sigma_narrow_px=8.0, sigma_wide_px=30.0)
    del paleo_imp

    # 2. Shallow 2 m temperature probe positive anomalies (F2mDAB > 0)
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
        fields = [f[0] for f in sf.fields[1:]]
        if {n.lower() for n in fields} & FORBIDDEN_COLUMNS:
            raise RuntimeError("Forbidden fault column in 2m probe shapefile")
        idx_dab = fields.index("F2mDAB")
        idx_lon = fields.index("LongDegree")
        idx_lat = fields.index("LatDegreeN")
        lons, lats, dabs = [], [], []
        for rec in sf.iterRecords():
            try:
                lon_v, lat_v, dab_v = float(rec[idx_lon]), float(rec[idx_lat]), float(rec[idx_dab])
            except (TypeError, ValueError):
                continue
            if np.isfinite(lon_v) and np.isfinite(lat_v) and np.isfinite(dab_v) and dab_v > 0.0:
                lons.append(lon_v)
                lats.append(lat_v)
                dabs.append(min(dab_v, 15.0))
    ux, uy = to_utm11.transform(np.asarray(lons, float), np.asarray(lats, float))
    cf, rf = inv_tr * (ux, uy)
    ri, ci = np.floor(rf).astype(np.int64), np.floor(cf).astype(np.int64)
    ok = (ri >= 0) & (ri < h) & (ci >= 0) & (ci < w)
    probe_imp = np.zeros((h, w), dtype=np.float32)
    np.add.at(probe_imp, (ri[ok], ci[ok]), np.asarray(dabs, dtype=np.float32)[ok])
    dog_probe = local_dog_positive(probe_imp, fp, sigma_narrow_px=8.0, sigma_wide_px=30.0)
    del probe_imp

    # 3. GDR wells & springs: strictly load coordinates + thermal/geothermometer columns only
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
        raise RuntimeError("Forbidden fault column loaded from gdr_wellspring_in_footprint.csv")
    w_cf, w_rf = inv_tr * (
        df_ws["utm_x"].to_numpy(dtype=np.float64),
        df_ws["utm_y"].to_numpy(dtype=np.float64),
    )
    w_ri, w_ci = np.floor(w_rf).astype(np.int64), np.floor(w_cf).astype(np.int64)
    w_ok = (w_ri >= 0) & (w_ri < h) & (w_ci >= 0) & (w_ci < w)
    temp_c = pd.to_numeric(df_ws["temp_c"], errors="coerce").to_numpy(dtype=np.float64)
    gt_cols = np.column_stack(
        [
            pd.to_numeric(df_ws[c], errors="coerce").to_numpy(dtype=np.float64)
            for c in ("geothermquartz_c", "geothermchalc_c", "geothermcat_c")
        ]
    )
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="All-NaN slice encountered")
        gt_max = np.nanmax(gt_cols, axis=1)
    therm_excess = np.maximum(
        np.where(np.isfinite(temp_c), np.clip((temp_c - 35.0) / 40.0, 0.0, 4.0), 0.0),
        np.where(np.isfinite(gt_max), np.clip((gt_max - 70.0) / 60.0, 0.0, 4.0), 0.0),
    )
    hot_sel = w_ok & (therm_excess > 0.0)
    ws_imp = np.zeros((h, w), dtype=np.float32)
    np.add.at(ws_imp, (w_ri[hot_sel], w_ci[hot_sel]), therm_excess[hot_sel].astype(np.float32))
    dog_ws = local_dog_positive(ws_imp, fp, sigma_narrow_px=8.0, sigma_wide_px=30.0)
    del ws_imp

    # Combine localized INGENIOUS upflow signal (zero outside ~6 km of thermal features)
    p99_p = max(float(np.nanpercentile(dog_paleo[fp], 99.5)), 1e-6)
    p99_t = max(float(np.nanpercentile(dog_probe[fp], 99.5)), 1e-6)
    p99_w = max(float(np.nanpercentile(dog_ws[fp], 99.5)), 1e-6)
    ing_upflow_dog = np.where(
        fp,
        np.clip(dog_paleo / p99_p, 0.0, 6.0)
        + np.clip(dog_probe / p99_t, 0.0, 6.0)
        + np.clip(dog_ws / p99_w, 0.0, 6.0),
        np.nan,
    ).astype(np.float32)
    del dog_paleo, dog_probe, dog_ws

    # 4. Quaternary volcanic vents (strictly load row, col only; dist_known_fault_px forbidden)
    vv_csv = root / "data/external/gdr_volcanic_vents_in_footprint.csv"
    df_vv = pd.read_csv(vv_csv, usecols=["row", "col"])
    if set(df_vv.columns.str.lower()) & FORBIDDEN_COLUMNS:
        raise RuntimeError("Forbidden fault column loaded from gdr_volcanic_vents_in_footprint.csv")
    v_ri = pd.to_numeric(df_vv["row"], errors="coerce").to_numpy(dtype=np.float64)
    v_ci = pd.to_numeric(df_vv["col"], errors="coerce").to_numpy(dtype=np.float64)
    v_ok = np.isfinite(v_ri) & np.isfinite(v_ci)
    v_ri_i = np.floor(v_ri[v_ok]).astype(np.int64)
    v_ci_i = np.floor(v_ci[v_ok]).astype(np.int64)
    in_b = (v_ri_i >= 0) & (v_ri_i < h) & (v_ci_i >= 0) & (v_ci_i < w)
    vv_imp = np.zeros((h, w), dtype=np.float32)
    np.add.at(vv_imp, (v_ri_i[in_b], v_ci_i[in_b]), 1.0)
    dog_vv = local_dog_positive(vv_imp, fp, sigma_narrow_px=12.0, sigma_wide_px=36.0)
    del vv_imp

    return ing_upflow_dog, dog_vv


def build_trsg1_feature_memmap(
    *,
    out_path: Path,
    root: Path,
    footprint: np.ndarray,
    prepared_path: Path,
    prepared_names: list[str],
    training_tif_path: Path,
    rad_tif_path: Path,
    rad_meta: dict[str, Any],
    ext_tif_path: Path,
    ext_meta: dict[str, Any],
) -> np.memmap:
    """Stream all 44 float32 TRSG1 channels into ``out_path`` under <1.5 GiB RSS."""
    fp = np.asarray(footprint, dtype=bool)
    fp_ids = np.flatnonzero(fp)
    n_rows = int(len(fp_ids))
    n_cols = len(FEATURE_NAMES)
    shape = fp.shape

    if tuple(prepared_names) != PREPARED30_NAMES:
        raise ValueError("Prepared 30-channel order does not match PREPARED30_NAMES")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    mm = np.lib.format.open_memmap(out_path, mode="w+", dtype=np.float32, shape=(n_rows, n_cols))

    # 1. Copy channels 0..29 from cached data/prepared/features.npy in bounded row chunks
    prep_mm = np.load(prepared_path, mmap_mode="r")
    if prep_mm.shape != (n_rows, 30):
        raise ValueError(f"Unexpected prepared shape {prep_mm.shape}; expected {(n_rows, 30)}")
    for start in range(0, n_rows, 500_000):
        end = min(start + 500_000, n_rows)
        mm[start:end, :30] = prep_mm[start:end, :]
    del prep_mm
    gc.collect()

    def unpack_col(name: str) -> np.ndarray:
        idx = FEATURE_NAMES.index(name)
        arr = np.full(shape, np.nan, dtype=np.float32)
        arr.ravel()[fp_ids] = mm[:, idx]
        return arr

    def write_col(name: str, grid_2d: np.ndarray) -> None:
        idx = FEATURE_NAMES.index(name)
        mm[:, idx] = np.asarray(grid_2d, dtype=np.float32).ravel()[fp_ids]

    # 2. Read the 6 omitted bands from data/training_features.tif (|x| > 1e30 -> NaN)
    with rasterio.open(training_tif_path) as ds:
        grid_transform = ds.transform

        def read_clean_band(bname: str) -> np.ndarray:
            bidx = geofeatures.BAND_ORDER.index(bname) + 1
            raw = ds.read(bidx).astype(np.float32)
            bad = (~np.isfinite(raw)) | (np.abs(raw) > 1e30) | (~fp)
            raw[bad] = np.nan
            return raw

        for bname in ("mag_anom", "geod_2ndinv", "iso_grav_anom_slope", "tc"):
            arr = read_clean_band(bname)
            write_col(bname, arr)
            del arr

        ieq_raw = read_clean_band("ieq_n100a15")
        deq_raw = read_clean_band("deq_n100a15")

    eq_valid = fp & np.isfinite(ieq_raw) & np.isfinite(deq_raw)
    ieq_log = np.where(eq_valid, np.log1p(np.maximum(ieq_raw, 0.0)), np.nan).astype(np.float32)
    deq_log = np.where(eq_valid, np.log1p(np.maximum(deq_raw, 0.0)), np.nan).astype(np.float32)
    del ieq_raw, deq_raw
    deq_excess = np.where(
        eq_valid, robust_z(deq_log, eq_valid) - 0.70 * robust_z(ieq_log, eq_valid), np.nan
    ).astype(np.float32)
    write_col("eq_ieq_log", ieq_log)
    write_col("eq_deq_excess", deq_excess)
    del deq_log, deq_excess

    # 36: Seismic fabric structure-tensor anisotropy
    eq_aniso = seismic_fabric_anisotropy(ieq_log, eq_valid, grad_sigma_px=1.5, tensor_sigma_px=6.0)
    write_col("eq_fabric_aniso", eq_aniso)
    del ieq_log, eq_aniso, eq_valid
    gc.collect()

    # 37 & 39: DEM hyperbolic relay-ramp saddle twist + piedmont concavity / drainage incision break
    det_elev = unpack_col("det_elev")
    slope = unpack_col("det_elev_slope")
    dem_valid = fp & np.isfinite(det_elev) & np.isfinite(slope)
    s3 = hyperbolic_saddle_twist(det_elev, dem_valid, sigma_px=3.0)
    s8 = hyperbolic_saddle_twist(det_elev, dem_valid, sigma_px=8.0)
    relay_dem = np.where(
        dem_valid, robust_z(s3, dem_valid) + 0.50 * robust_z(s8, dem_valid), np.nan
    ).astype(np.float32)
    write_col("relay_saddle_dem", relay_dem)
    del s3, s8, relay_dem

    slope_f = nearest_fill(np.maximum(slope, 0.0), dem_valid)
    elev_f = nearest_fill(det_elev, dem_valid)
    p85_slope = float(np.percentile(slope_f[dem_valid], 85.0))
    piedmont_conc = (
        gaussian_filter(slope_f, sigma=12.0, mode="nearest")
        - gaussian_filter(slope_f, sigma=3.0, mode="nearest")
    ) * (slope_f < p85_slope).astype(np.float32)
    elev_s2 = gaussian_filter(elev_f, sigma=2.0, mode="nearest")
    gy_e, gx_e = np.gradient(elev_s2)
    hyy_e, _ = np.gradient(gy_e)
    _, hxx_e = np.gradient(gx_e)
    lap_valley = np.maximum(hxx_e + hyy_e, 0.0)
    del elev_s2, gy_e, gx_e, hyy_e, hxx_e
    sl_s4 = gaussian_filter(slope_f, sigma=4.0, mode="nearest")
    gy_s, gx_s = np.gradient(sl_s4)
    knick = lap_valley * np.hypot(gx_s, gy_s)
    pd_break = np.where(
        dem_valid, robust_z(piedmont_conc, dem_valid) + robust_z(knick, dem_valid), np.nan
    ).astype(np.float32)
    write_col("piedmont_drainage_break", pd_break)
    del slope, slope_f, elev_f, piedmont_conc, lap_valley, sl_s4, gy_s, gx_s, knick, pd_break
    gc.collect()

    # 38 & 43: Potential-field transfer saddle + tilt contacts + basement Euler-like step
    iso_grav = unpack_col("iso_grav_anom")
    rtp = unpack_col("rtp")
    tmi_hg = unpack_col("tmi_hg")
    tmi_vg = unpack_col("tmi_vg")
    grav_hg = unpack_col("iso_grav_anom_hg")
    grav_vg = unpack_col("iso_grav_anom_vg")

    tilts = rshg1.compute_tilt_and_curvature_channels(
        tmi_hg=tmi_hg,
        tmi_vg=tmi_vg,
        grav_hg=grav_hg,
        grav_vg=grav_vg,
        det_elev=det_elev,
        footprint=fp,
    )
    del det_elev

    pot_valid = (
        fp
        & np.isfinite(iso_grav)
        & np.isfinite(rtp)
        & np.isfinite(tilts["cos_tilt_grav"])
        & np.isfinite(tilts["cos_tilt_mag"])
    )
    gs5 = hyperbolic_saddle_twist(iso_grav, pot_valid, sigma_px=5.0)
    rs4 = hyperbolic_saddle_twist(rtp, pot_valid, sigma_px=4.0)
    relay_pot = np.where(
        pot_valid,
        robust_z(gs5, pot_valid)
        + 0.50 * robust_z(rs4, pot_valid)
        + tilts["cos_tilt_grav"]
        + tilts["cos_tilt_mag"],
        np.nan,
    ).astype(np.float32)
    write_col("relay_saddle_pot", relay_pot)
    del iso_grav, rtp, gs5, rs4, relay_pot, tilts
    gc.collect()

    depth_base = unpack_col("depth_to_base_surf")
    euler_valid = (
        fp
        & np.isfinite(tmi_hg)
        & np.isfinite(tmi_vg)
        & np.isfinite(grav_hg)
        & np.isfinite(depth_base)
    )
    db_f = gaussian_filter(nearest_fill(depth_base, euler_valid), sigma=2.0, mode="nearest")
    gy_b, gx_b = np.gradient(db_f)
    grad_db = np.hypot(gx_b, gy_b)
    vp_ratio = (
        np.abs(np.where(euler_valid, tmi_vg, 0.0))
        / np.sqrt(np.where(euler_valid, tmi_hg, 0.0) ** 2 + 1.0)
    ) * grad_db
    co_hg = np.sqrt(
        np.maximum(robust_z(grav_hg, euler_valid), 0.0)
        * np.maximum(robust_z(tmi_hg, euler_valid), 0.0)
    )
    euler_step = np.where(euler_valid, robust_z(vp_ratio, euler_valid) + co_hg, np.nan).astype(
        np.float32
    )
    write_col("basement_euler_step", euler_step)
    del (
        tmi_hg,
        tmi_vg,
        grav_hg,
        grav_vg,
        depth_base,
        db_f,
        gy_b,
        gx_b,
        grad_db,
        vp_ratio,
        co_hg,
        euler_step,
    )
    gc.collect()

    # 40, 41, 42: Localized INGENIOUS upflow DoG, Quaternary vent + demag + clay-cap, Th-norm K/U alteration
    ing_dog, qvent_dog = load_localized_upflow_and_vents(root, shape, grid_transform, fp)
    write_col("ing_upflow_dog", ing_dog)
    del ing_dog

    with rasterio.open(rad_tif_path) as ds_rad:
        rad_ch = list(rad_meta["channels"])
        rad_bands = {c: ds_rad.read(rad_ch.index(c) + 1) for c in ("K", "Th")}
    with rasterio.open(ext_tif_path) as ds_ext:
        ext_ch = list(ext_meta["channels"])
        ext_bands = {c: ds_ext.read(ext_ch.index(c) + 1) for c in ("ThK", "UTh")}
        tmi_up150_u8 = ds_ext.read(ext_ch.index("TMI_up150") + 1)

    r_alt = rshg1.compute_modality_sahg1_r_alt(rad_bands, ext_bands, fp)
    del rad_bands, ext_bands
    r_valid = fp & np.isfinite(r_alt)
    r_f = nearest_fill(r_alt, r_valid)
    r_hp = np.where(r_valid, r_f - gaussian_filter(r_f, sigma=15.0, mode="nearest"), np.nan).astype(
        np.float32
    )
    write_col("th_norm_k_u_alt", r_hp)
    del r_alt, r_f, r_hp

    tmi = unpack_col("tmi")
    cond = unpack_col("cond_surf")
    demag = rshg1.compute_shallow_magnetic_residual(tmi, tmi_up150_u8, fp)
    del tmi, tmi_up150_u8
    qd_valid = fp & np.isfinite(cond)
    cond_f = gaussian_filter(
        np.log1p(np.maximum(nearest_fill(cond, qd_valid), 0.0)), sigma=2.0, mode="nearest"
    )
    gy_c, gx_c = np.gradient(cond_f)
    cond_grad = np.hypot(gx_c, gy_c)
    demag_safe = np.where(np.isfinite(demag), demag, 0.0)
    p99_v = max(float(np.nanpercentile(qvent_dog[fp], 99.5)), 1e-6)
    qv_conduit = np.where(
        qd_valid,
        np.clip(qvent_dog / p99_v, 0.0, 6.0)
        + np.maximum(robust_z(demag_safe * cond_grad, qd_valid), 0.0),
        np.nan,
    ).astype(np.float32)
    write_col("qvent_demag_conduit", qv_conduit)
    del cond, demag, cond_f, gy_c, gx_c, cond_grad, demag_safe, qvent_dog, qv_conduit

    mm.flush()
    gc.collect()
    return mm


class TerrainReliefRegimeCalibrator:
    """Training-only nuisance debiaser + terrain-relief-stratified LiDAR-gap tail alignment."""

    def __init__(self, alpha: float = 100.0, distance_columns: int = 2):
        self.alpha = float(alpha)
        self.distance_columns = int(distance_columns)
        self._basis_helper = NuisanceResidualizer(
            alpha=alpha, distance_columns=self.distance_columns
        )
        self.ridge_: Ridge | None = None
        self.mean_nuis_: float = 0.0
        self.relief_cuts_: tuple[float, float] = (0.0, 1.0)
        self.strata_stats_: dict[int, tuple[float, float, float, float]] = {}

    def _strata(self, abs_relief: np.ndarray) -> np.ndarray:
        q33, q67 = self.relief_cuts_
        r = np.where(np.isfinite(abs_relief), abs_relief, q33)
        out = np.zeros(len(r), dtype=np.int8)
        out[r >= q33] = 1
        out[r >= q67] = 2
        return out

    def fit(
        self,
        prob_bg: np.ndarray,
        has_lidar_bg: np.ndarray,
        abs_relief_bg: np.ndarray,
        nuisance_bg: np.ndarray,
    ) -> TerrainReliefRegimeCalibrator:
        p = np.clip(np.asarray(prob_bg, dtype=np.float64), 1e-5, 1.0 - 1e-5)
        ell = logit(p).astype(np.float32)
        hl = np.asarray(has_lidar_bg, dtype=bool)
        rel = np.abs(np.asarray(abs_relief_bg, dtype=np.float32))
        c = np.asarray(nuisance_bg, dtype=np.float32)
        if len(p) != len(hl) or len(p) != len(rel) or len(p) != len(c):
            raise ValueError(
                "Aligned 1D prob_bg, has_lidar_bg, abs_relief_bg, 2D nuisance_bg required"
            )
        if c.shape[1] < self.distance_columns or not np.isfinite(c).all():
            raise ValueError("Finite nuisance_bg with >= distance_columns required")

        self._basis_helper.n_nuisance = c.shape[1]
        basis = self._basis_helper._basis(c, fit=True)
        self.ridge_ = Ridge(alpha=self.alpha).fit(basis, ell)
        pred = self.ridge_.predict(basis)
        self.mean_nuis_ = float(np.mean(pred))
        debiased = ell - (pred - self.mean_nuis_)

        fin_rel = rel[np.isfinite(rel)]
        if len(fin_rel) >= 32:
            q33, q67 = np.percentile(fin_rel, [33.33, 66.67])
            self.relief_cuts_ = (float(q33), max(float(q67), float(q33) + 1e-6))
        else:
            self.relief_cuts_ = (0.0, 1.0)

        global_med_l = (
            float(np.median(debiased[hl])) if int(hl.sum()) >= 32 else float(np.median(debiased))
        )
        global_spr_l = (
            max(float(np.percentile(debiased[hl], 99.0) - global_med_l), 0.25)
            if int(hl.sum()) >= 32
            else max(float(np.percentile(debiased, 99.0) - global_med_l), 0.25)
        )
        global_med_g = float(np.median(debiased[~hl])) if int((~hl).sum()) >= 32 else global_med_l
        global_spr_g = (
            max(float(np.percentile(debiased[~hl], 99.0) - global_med_g), 0.25)
            if int((~hl).sum()) >= 32
            else global_spr_l
        )

        st = self._strata(rel)
        self.strata_stats_ = {}
        for s in (0, 1, 2):
            m_l = hl & (st == s)
            m_g = (~hl) & (st == s)
            if int(m_l.sum()) >= 32:
                med_l = float(np.median(debiased[m_l]))
                spr_l = max(float(np.percentile(debiased[m_l], 99.0) - med_l), 0.25)
            else:
                med_l, spr_l = global_med_l, global_spr_l
            if int(m_g.sum()) >= 32:
                med_g = float(np.median(debiased[m_g]))
                spr_g = max(float(np.percentile(debiased[m_g], 99.0) - med_g), 0.25)
            else:
                med_g, spr_g = global_med_g, global_spr_g
            self.strata_stats_[s] = (med_l, spr_l, med_g, spr_g)
        return self

    def transform(
        self,
        prob: np.ndarray,
        has_lidar: np.ndarray,
        abs_relief: np.ndarray,
        nuisance: np.ndarray,
    ) -> np.ndarray:
        if self.ridge_ is None:
            raise RuntimeError("Call fit before transform")
        p = np.clip(np.asarray(prob, dtype=np.float64), 1e-5, 1.0 - 1e-5)
        ell = logit(p)
        hl = np.asarray(has_lidar, dtype=bool)
        rel = np.abs(np.asarray(abs_relief, dtype=np.float32))
        c = np.asarray(nuisance, dtype=np.float32)
        basis = self._basis_helper._basis(c, fit=False)
        debiased = ell - (self.ridge_.predict(basis) - self.mean_nuis_)
        out = debiased.copy()
        gap = ~hl
        if np.any(gap):
            st = self._strata(rel)
            for s in (0, 1, 2):
                mask_s = gap & (st == s)
                if np.any(mask_s):
                    med_l, spr_l, med_g, spr_g = self.strata_stats_[s]
                    out[mask_s] = med_l + (debiased[mask_s] - med_g) * (spr_l / spr_g)
        return expit(np.clip(out, -14.0, 14.0)).astype(np.float32)


def make_rotated45_folds(
    footprint: np.ndarray, labels: np.ndarray, *, buffer_px: int = 15
) -> list[dict[str, Any]]:
    """Construct 45°-rotated 4-sector whole-component buffered holdout partitions.

    Mirrors ``SegmentHoldout``'s exact whole-component hiding and ``buffer_px``
    purging along 45°-rotated axes ``u = (y - y0) + (x - x0)``, ``v = (y - y0) - (x - x0)``
    so blending Quadrant-OOF + Rotated45-OOF yields a 100% out-of-fold deployment surface.
    """
    fp = np.asarray(footprint, dtype=bool)
    lab = np.asarray(labels, dtype=bool)
    if fp.shape != lab.shape or fp.ndim != 2 or buffer_px < 3 or np.any(lab & ~fp) or not lab.any():
        raise ValueError("Aligned nonempty footprint, labels, and >=3 px collar required")

    components, _ = ndi_label(lab, structure=np.ones((3, 3), dtype=int))
    yy, xx = np.nonzero(fp)
    y0 = float(np.median(yy))
    x0 = float(np.median(xx))
    yg, xg = np.indices(fp.shape, dtype=np.float32)
    u = (yg - y0) + (xg - x0)
    v = (yg - y0) - (xg - x0)

    sector_grid = np.full(fp.shape, -1, dtype=np.int8)
    sector_grid[fp & (u < 0) & (v < 0)] = 0
    sector_grid[fp & (u >= 0) & (v < 0)] = 1
    sector_grid[fp & (u >= 0) & (v >= 0)] = 2
    sector_grid[fp & (u < 0) & (v >= 0)] = 3
    names = ("ROT45_N", "ROT45_E", "ROT45_S", "ROT45_W")

    folds: list[dict[str, Any]] = []
    for s_idx, name in enumerate(names):
        valid = fp & (sector_grid == s_idx)
        if not valid.any():
            raise ValueError(f"Empty rotated sector: {name}")
        collar = distance_transform_edt(~valid) <= buffer_px
        hidden_ids = np.unique(components[collar & lab])
        hidden_ids = hidden_ids[hidden_ids > 0]
        hidden = lab & np.isin(components, hidden_ids)
        visible = lab & ~hidden
        truth = hidden & valid
        if not truth.any():
            raise ValueError(f"No withheld positives in rotated sector: {name}")
        train = fp & (distance_transform_edt(~(valid | hidden)) > buffer_px)
        folds.append(
            {
                "id": s_idx,
                "name": name,
                "valid": valid,
                "train": train,
                "visible": visible,
                "truth": truth,
                "hidden_component_ids": hidden_ids,
            }
        )
    return folds


def emit_global_poisson(
    prob_map: np.ndarray,
    domain_mask: np.ndarray,
    visible_mask: np.ndarray,
    *,
    budget_frac: float = 0.0073,
    min_dist: float = 3.0,
    clearance_px: float = 2.0,
) -> np.ndarray:
    """Emit spaced binary vertices globally using visible-only clearance."""
    dom = np.asarray(domain_mask, dtype=bool)
    vis = np.asarray(visible_mask, dtype=bool)
    k = int(round(float(budget_frac) * int(dom.sum())))
    if k <= 0:
        return np.zeros(dom.shape, dtype=bool)
    clear = (
        distance_transform_edt(~vis) > float(clearance_px)
        if (clearance_px > 0 and vis.any())
        else ~vis
    )
    eligible = dom & clear & np.isfinite(prob_map)
    score = np.where(eligible, np.clip(prob_map, 0.0, 1.0), 0.0).astype(np.float32)
    return priority_poisson(score, eligible, k, min_dist=min_dist)


def emit_two_regime_poisson(
    prob_map: np.ndarray,
    domain_mask: np.ndarray,
    visible_mask: np.ndarray,
    depth_to_base: np.ndarray,
    slope_deg: np.ndarray,
    subsurface_conduit_z: np.ndarray,
    *,
    budget_frac: float = 0.0073,
    basin_budget_share: float = 0.26,
    basin_depth_min_m: float = 300.0,
    basin_slope_max_deg: float = 6.0,
    min_dist: float = 3.0,
    clearance_px: float = 2.0,
) -> np.ndarray:
    """Emit spaced binary vertices across Concealed-Basin and Range-Front/Step-Over regimes.

    Enforces ``EDT(~visible_mask) > clearance_px`` and global inter-dot spacing
    ``>= min_dist`` strictly across both regimes and across their shared boundary.
    """
    dom = np.asarray(domain_mask, dtype=bool)
    vis = np.asarray(visible_mask, dtype=bool)
    if (
        prob_map.shape != dom.shape
        or vis.shape != dom.shape
        or depth_to_base.shape != dom.shape
        or slope_deg.shape != dom.shape
        or subsurface_conduit_z.shape != dom.shape
    ):
        raise ValueError("Aligned 2D arrays required for two-regime emission")
    if not (0.0 <= basin_budget_share <= 1.0):
        raise ValueError("basin_budget_share must lie in [0, 1]")

    k_total = int(round(float(budget_frac) * int(dom.sum())))
    if k_total <= 0:
        return np.zeros(dom.shape, dtype=bool)

    clear = (
        distance_transform_edt(~vis) > float(clearance_px)
        if (clearance_px > 0 and vis.any())
        else ~vis
    )
    elig_all = dom & clear & np.isfinite(prob_map) & (prob_map > 0.0)
    basin_regime = (
        np.isfinite(depth_to_base)
        & np.isfinite(slope_deg)
        & (depth_to_base >= float(basin_depth_min_m))
        & (slope_deg <= float(basin_slope_max_deg))
    )

    k_basin = int(round(float(basin_budget_share) * k_total))
    elig_basin = elig_all & basin_regime
    sub_sig = expit(
        np.clip(np.where(np.isfinite(subsurface_conduit_z), subsurface_conduit_z, 0.0), -6.0, 6.0)
    ).astype(np.float32)
    score_basin = np.where(
        elig_basin,
        np.clip(prob_map, 0.0, 1.0) * (0.85 + 0.15 * sub_sig),
        0.0,
    ).astype(np.float32)

    dots_basin = (
        priority_poisson(score_basin, elig_basin, k_basin, min_dist=min_dist)
        if (k_basin > 0 and elig_basin.any())
        else np.zeros(dom.shape, dtype=bool)
    )

    k_rem = k_total - int(dots_basin.sum())
    if k_rem <= 0:
        return dots_basin

    if dots_basin.any():
        not_near_basin_dot = distance_transform_edt(~dots_basin) >= float(min_dist)
    else:
        not_near_basin_dot = np.ones(dom.shape, dtype=bool)

    canyon_taper = np.where(
        np.isfinite(slope_deg) & np.isfinite(depth_to_base) & (depth_to_base < 50.0),
        1.0 - 0.20 * np.clip((slope_deg - 24.0) / 15.0, 0.0, 1.0),
        1.0,
    ).astype(np.float32)
    elig_range = elig_all & (~basin_regime) & not_near_basin_dot
    score_range = np.where(elig_range, np.clip(prob_map, 0.0, 1.0) * canyon_taper, 0.0).astype(
        np.float32
    )
    dots_range = priority_poisson(score_range, elig_range, k_rem, min_dist=min_dist)

    combined = dots_basin | dots_range
    # If Regime A saturated before k_rem (rare on small grids), top up from remaining eligible cells
    shortfall = k_total - int(combined.sum())
    if shortfall > 0:
        elig_extra = elig_all & (
            distance_transform_edt(~combined) >= float(min_dist)
            if combined.any()
            else np.ones(dom.shape, dtype=bool)
        )
        if elig_extra.any():
            score_extra = np.where(elig_extra, np.clip(prob_map, 0.0, 1.0), 0.0).astype(np.float32)
            combined = combined | priority_poisson(
                score_extra, elig_extra, shortfall, min_dist=min_dist
            )
    return combined
