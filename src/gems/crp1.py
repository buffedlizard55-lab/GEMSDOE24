"""Label-free feature construction for the preregistered H24-CRP1 lane.

Implements the frozen specification in
``knowledge/20_preregistered_CRP1_2026-10-26.md``:

- compositional radiometric fronts from the contractor GeoDAWN ratio grids
  (UK, UTh, ThK) and K/Th/U channels, encoded in the committed uint8 caches
  as percentile ranks (1..255, 0 = nodata).  ``logit(rank)`` is a monotonic
  rank score, **not** a physical log-ratio; the transform only assumes that
  a physical compositional front remains a front under monotone encoding.
- cross-depth magnetic persistence between the competition TMI band and the
  contractor TMI upward-continued to 150 m (gradient magnitude/direction
  agreement plus a rank residual).
- Hessian saddle strength ``sqrt(relu(-lambda1 * lambda2))`` of the DEM and
  isostatic gravity anomaly (step-over / relay-ramp geometry).

Every channel is a function of pixel values only.  No labels, no catalogue
distance, and no prior submission pixels are read.  Nearest-valid fill is
used only inside spatial transforms; source-invalid pixels are restored to
``NaN`` so tree models can route missingness natively.
"""

from __future__ import annotations

import gc
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt, gaussian_filter, uniform_filter

from .geofeatures import BAND_ORDER, _valid

NEW_FEATURE_NAMES: tuple[str, ...] = (
    "crp_uk_front",
    "crp_uth_stable_front",
    "crp_thk_front",
    "crp_ilr1",
    "crp_ilr1_front",
    "crp_xdepth_resid",
    "crp_xdepth_persist",
    "crp_dem_saddle3",
    "crp_dem_saddle6",
    "crp_grav_saddle3",
)

# Prepared-stack columns that receive training-fold nuisance residualization
# (selective policy preregistered for CRP1: airborne/non-topographic only).
RESIDUALIZED_PREPARED: tuple[str, ...] = (
    "rtp",
    "tmi_hg",
    "tmi_vg",
    "tmi",
    "cond_surf",
    "depth_to_base_surf",
    "iso_grav_anom",
    "iso_grav_anom_hg",
    "iso_grav_anom_vg",
    "arc_rtp",
)
RESIDUALIZED_NEW: tuple[str, ...] = NEW_FEATURE_NAMES[:7]


def _fill_nearest(a: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """Nearest-valid fill for transform neighbourhoods only (label-free)."""
    if valid.all():
        return a.astype(np.float32, copy=True)
    inds = distance_transform_edt(~valid, return_distances=False, return_indices=True)
    out = a[tuple(inds)].astype(np.float32, copy=False)
    del inds
    return out


def _grad_mag(filled: np.ndarray) -> np.ndarray:
    gy, gx = np.gradient(gaussian_filter(filled, 1.0))
    out = np.hypot(gx, gy).astype(np.float32)
    del gy, gx
    return out


def _rank_score(u8_band: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """uint8 percentile-rank cache -> (logit rank score, valid mask)."""
    valid = u8_band > 0
    r = np.clip(u8_band.astype(np.float32) / 255.0, 1.0 / 512.0, 1.0 - 1.0 / 512.0)
    score = np.log(r / (1.0 - r)).astype(np.float32)
    score[~valid] = np.nan
    return score, valid


def _front(score: np.ndarray, valid: np.ndarray) -> np.ndarray:
    filled = _fill_nearest(np.where(valid, score, 0.0).astype(np.float32), valid)
    out = _grad_mag(filled)
    out[~valid] = np.nan
    del filled
    return out


def _local_std(score: np.ndarray, valid: np.ndarray, size: int = 5) -> np.ndarray:
    filled = _fill_nearest(np.where(valid, score, 0.0).astype(np.float32), valid)
    mean = uniform_filter(filled, size=size)
    mean2 = uniform_filter(filled * filled, size=size)
    out = np.sqrt(np.maximum(mean2 - mean * mean, 0.0)).astype(np.float32)
    out[~valid] = np.nan
    del filled, mean, mean2
    return out


def saddle_strength(field: np.ndarray, valid: np.ndarray, sigma: float) -> np.ndarray:
    """sqrt(relu(-lambda1*lambda2)) of the Hessian of ``field`` at ``sigma`` px.

    Positive exactly where the two principal curvatures have opposite signs
    (a saddle); zero on ridges, valleys and planes.  Source-invalid pixels
    are restored to NaN.
    """
    filled = _fill_nearest(np.where(valid, field, 0.0).astype(np.float32), valid)
    f = gaussian_filter(filled, sigma)
    del filled
    gy, gx = np.gradient(f, axis=0), np.gradient(f, axis=1)
    fyy = np.gradient(gy, axis=0)
    fxy = np.gradient(gy, axis=1)
    fxx = np.gradient(gx, axis=1)
    del f, gy, gx
    det = (fxx.astype(np.float64) * fyy - fxy.astype(np.float64) ** 2).astype(np.float32)
    del fxx, fyy, fxy
    out = np.sqrt(np.maximum(-det, 0.0)).astype(np.float32)
    del det
    out[~valid] = np.nan
    return out


def footprint_rank(field: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """Empirical CDF rank in [0,1] over valid pixels; NaN where invalid."""
    out = np.full(field.shape, np.nan, dtype=np.float32)
    vals = field[valid]
    order = np.argsort(vals, kind="stable")
    ranks = np.empty(len(vals), dtype=np.float64)
    ranks[order] = np.arange(1, len(vals) + 1, dtype=np.float64)
    out[valid] = (ranks / float(len(vals))).astype(np.float32)
    del vals, order, ranks
    return out


def build_new_channels(
    *,
    footprint: np.ndarray,
    training_tif: Path,
    ext_tif: Path,
    rad_tif: Path,
    ext_channels: list[str],
    rad_channels: list[str],
) -> dict[str, np.ndarray]:
    """Compute the 10 preregistered CRP1 channels as full float32 grids."""
    fp = np.asarray(footprint, bool)
    out: dict[str, np.ndarray] = {}

    with rasterio.open(ext_tif) as ds:
        uk, uk_v = _rank_score(ds.read(ext_channels.index("UK") + 1))
        uth, uth_v = _rank_score(ds.read(ext_channels.index("UTh") + 1))
        thk, thk_v = _rank_score(ds.read(ext_channels.index("ThK") + 1))
        up_raw = ds.read(ext_channels.index("TMI_up150") + 1)
    uk_v &= fp
    uth_v &= fp
    thk_v &= fp
    out["crp_uk_front"] = _front(uk, uk_v)
    uth_std = _local_std(uth, uth_v)
    stable = (out["crp_uk_front"] * np.exp(-np.nan_to_num(uth_std, nan=0.0))).astype(np.float32)
    stable[~(uk_v & uth_v)] = np.nan
    out["crp_uth_stable_front"] = stable
    del uth_std, stable, uth, uk
    out["crp_thk_front"] = _front(thk, thk_v)
    del thk
    gc.collect()

    with rasterio.open(rad_tif) as ds:
        k_s, k_v = _rank_score(ds.read(rad_channels.index("K") + 1))
        th_s, th_v = _rank_score(ds.read(rad_channels.index("Th") + 1))
        u_s, u_v = _rank_score(ds.read(rad_channels.index("U") + 1))
    ilr_v = k_v & th_v & u_v & fp
    ilr1 = (k_s - 0.5 * (th_s + u_s)).astype(np.float32)
    ilr1[~ilr_v] = np.nan
    del k_s, th_s, u_s
    out["crp_ilr1"] = ilr1
    out["crp_ilr1_front"] = _front(ilr1, ilr_v)
    del ilr1
    gc.collect()

    up_valid = (up_raw > 0) & fp
    up_rank = (up_raw.astype(np.float32) / 255.0).astype(np.float32)
    del up_raw

    with rasterio.open(training_tif) as ds:
        tmi = ds.read(BAND_ORDER.index("tmi") + 1)
    tmi_v = _valid(tmi) & fp
    tmi_rank = footprint_rank(np.where(tmi_v, tmi, 0.0).astype(np.float32), tmi_v)
    del tmi
    both = tmi_v & up_valid
    resid = (tmi_rank - up_rank).astype(np.float32)
    resid[~both] = np.nan
    out["crp_xdepth_resid"] = resid

    a_fill = _fill_nearest(np.where(tmi_v, tmi_rank, 0.0), tmi_v)
    b_fill = _fill_nearest(np.where(up_valid, up_rank, 0.0), up_valid)
    del tmi_rank, up_rank
    gay, gax = np.gradient(gaussian_filter(a_fill, 1.0))
    gby, gbx = np.gradient(gaussian_filter(b_fill, 1.0))
    del a_fill, b_fill
    mag_a = np.hypot(gax, gay)
    mag_b = np.hypot(gbx, gby)
    cos_d = (gax * gbx + gay * gby) / np.maximum(mag_a * mag_b, 1e-12)
    del gay, gax, gby, gbx
    persist = (np.minimum(mag_a, mag_b) * np.maximum(cos_d, 0.0)).astype(np.float32)
    del mag_a, mag_b, cos_d
    persist[~both] = np.nan
    out["crp_xdepth_persist"] = persist
    del persist, both
    gc.collect()

    with rasterio.open(training_tif) as ds:
        dem = ds.read(BAND_ORDER.index("det_elev") + 1)
    dem_v = _valid(dem) & fp
    out["crp_dem_saddle3"] = saddle_strength(dem, dem_v, 3.0)
    out["crp_dem_saddle6"] = saddle_strength(dem, dem_v, 6.0)
    del dem, dem_v
    gc.collect()

    with rasterio.open(training_tif) as ds:
        grav = ds.read(BAND_ORDER.index("iso_grav_anom") + 1)
    grav_v = _valid(grav) & fp
    out["crp_grav_saddle3"] = saddle_strength(grav, grav_v, 3.0)
    del grav, grav_v
    gc.collect()

    missing = [n for n in NEW_FEATURE_NAMES if n not in out]
    if missing:
        raise RuntimeError(f"CRP1 channel accounting error: missing {missing}")
    return out


def build_crp1_memmap(
    *,
    out_path: Path,
    footprint: np.ndarray,
    prepared_path: Path,
    prepared_names: list[str],
    training_tif: Path,
    ext_tif: Path,
    rad_tif: Path,
    ext_channels: list[str],
    rad_channels: list[str],
) -> tuple[np.memmap, list[str], list[int]]:
    """Assemble prepared-30 + CRP1-10 footprint memmap; return names + resid idx."""
    fp_ids = np.flatnonzero(np.asarray(footprint, bool))
    names = list(prepared_names) + list(NEW_FEATURE_NAMES)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    mm = np.lib.format.open_memmap(
        out_path, mode="w+", dtype=np.float32, shape=(len(fp_ids), len(names))
    )
    prep = np.load(prepared_path, mmap_mode="r")
    if prep.shape != (len(fp_ids), len(prepared_names)):
        raise SystemExit("Prepared stack shape does not match footprint/name manifest")
    for start in range(0, len(fp_ids), 250_000):
        mm[start : start + 250_000, : len(prepared_names)] = prep[start : start + 250_000]
    del prep
    mm.flush()

    channels = build_new_channels(
        footprint=footprint,
        training_tif=training_tif,
        ext_tif=ext_tif,
        rad_tif=rad_tif,
        ext_channels=ext_channels,
        rad_channels=rad_channels,
    )
    for j, name in enumerate(NEW_FEATURE_NAMES):
        mm[:, len(prepared_names) + j] = channels[name].ravel()[fp_ids]
        del channels[name]
        gc.collect()
    mm.flush()

    resid_names = set(RESIDUALIZED_PREPARED) | set(RESIDUALIZED_NEW)
    resid_idx = sorted(names.index(n) for n in resid_names)
    return mm, names, resid_idx
