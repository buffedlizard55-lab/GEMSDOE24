"""H24-CUP1: compositional radiometric fronts + upward-continuation trough persistence.

Label-free channels for the preregistered 2026-10-26 lane
(``knowledge/20_preregistered_CUP1_2026-10-26.md``). Inputs are the hash-pinned
GeoDAWN U8 rank grids (contractor K/Th/U/TC and ThK/UK/UTh/TMI_up150 products;
bytes are ranks, not physical concentrations) and the prepared RTP column.
No catalogue-derived quantity is read here. Every channel is masked to a
support eroded by its own receptive field so nodata fill can never create a
score; outside support the value is NaN (the shared HGB treats NaN as missing).
"""

from __future__ import annotations

import gc
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt, gaussian_filter

from .gvc import _grad_mag, _nearest_fill, _robust_z
from .magnetic_trough import paired_trough

CUP_FEATURE_NAMES: tuple[str, ...] = (
    "cup_thk_grad",
    "cup_uk_grad",
    "cup_uth_grad",
    "cup_comp_front",
    "cup_k_loc5",
    "cup_th_loc5",
    "cup_u_loc5",
    "cup_thk_loc8",
    "cup_uk_loc8",
    "cup_tc_grad",
    "cup_up150_grad",
    "cup_up150_loc8",
    "cup_trough_up",
    "cup_trough_rtp",
    "cup_trough_persist",
    "cup_deep_resid_grad",
)


def _support(valid: np.ndarray, margin_px: int) -> np.ndarray:
    """Pixels whose full ``margin_px`` neighbourhood is valid (EDT, no wrapping)."""
    padded = np.pad(np.asarray(valid, bool), 1, constant_values=False)
    return distance_transform_edt(padded)[1:-1, 1:-1] > margin_px


def _grad(a: np.ndarray, valid: np.ndarray, sigma: float, margin_px: int) -> np.ndarray:
    filled = gaussian_filter(_nearest_fill(a, valid), sigma, truncate=4)
    out = np.full(a.shape, np.nan, dtype=np.float32)
    sup = _support(valid, margin_px)
    out[sup] = _grad_mag(filled)[sup]
    return out


def _local_contrast(a: np.ndarray, valid: np.ndarray, sigma: float) -> np.ndarray:
    """(x - G_sigma x) / local SD at the same scale; support eroded by nested RF."""
    filled = gaussian_filter(_nearest_fill(a, valid), 1, truncate=4)
    resid = filled - gaussian_filter(filled, sigma, truncate=4)
    sd = np.sqrt(gaussian_filter(resid * resid, sigma, truncate=4)) + 1e-6
    margin = int(np.ceil(4 * 1 + 4 * sigma + 4 * sigma)) + 4
    out = np.full(a.shape, np.nan, dtype=np.float32)
    sup = _support(valid, margin)
    out[sup] = (resid / sd)[sup].astype(np.float32)
    return out


def build_cup_features(
    root: Path,
    base_memmap: np.ndarray,
    base_names: list[str],
    footprint: np.ndarray,
    out_npy_path: Path,
) -> tuple[np.ndarray, list[str]]:
    """Construct all CUP channels onto a disk-backed float32 memmap (footprint rows)."""
    fp = np.asarray(footprint, bool)
    h, w = fp.shape
    fp_idx = np.flatnonzero(fp.ravel())
    if base_memmap.shape != (len(fp_idx), len(base_names)):
        raise ValueError("Base feature memmap shape mismatch")
    out_npy_path.parent.mkdir(parents=True, exist_ok=True)
    mm = np.lib.format.open_memmap(
        out_npy_path, mode="w+", dtype=np.float32, shape=(len(fp_idx), len(CUP_FEATURE_NAMES))
    )

    def write(name: str, grid: np.ndarray) -> None:
        mm[:, CUP_FEATURE_NAMES.index(name)] = grid.ravel()[fp_idx].astype(np.float32)

    rad_path = root / "data/external/geodawn_rad_u8.tif"
    ext_path = root / "data/external/geodawn_extensions_u8.tif"
    with rasterio.open(rad_path) as ds:
        rad = {n: ds.read(i + 1).astype(np.float32) for i, n in enumerate(("K", "Th", "U", "TC"))}
    with rasterio.open(ext_path) as ds:
        ext = {
            n: ds.read(i + 1).astype(np.float32)
            for i, n in enumerate(("ThK", "UK", "UTh", "TMI_up150"))
        }
    grids = {**rad, **ext}
    valid = {n: fp & (g > 0) for n, g in grids.items()}

    # 100-300 m compositional fronts (gradient of sigma-1 ratio grids).
    grads: dict[str, np.ndarray] = {}
    for src, name in (("ThK", "cup_thk_grad"), ("UK", "cup_uk_grad"), ("UTh", "cup_uth_grad")):
        g = _grad(grids[src], valid[src], 1.0, 8)
        grads[src] = g
        write(name, g)
    write("cup_tc_grad", _grad(grids["TC"], valid["TC"], 1.0, 8))
    write("cup_up150_grad", _grad(grids["TMI_up150"], valid["TMI_up150"], 1.5, 10))

    # Stability-gated front: a ThK front counts most where UTh is locally quiet.
    uth = grads["UTh"]
    scale = float(np.nanmedian(uth[fp])) if np.isfinite(uth[fp]).any() else 1.0
    scale = scale if scale > 0 else 1.0
    front = grads["ThK"] / (1.0 + np.where(np.isfinite(uth), uth, np.nan) / scale)
    write("cup_comp_front", front.astype(np.float32))
    del grads, uth, front
    gc.collect()

    # 500-800 m local contrasts (different scale from GVC1's sigma-20 scalars).
    for src, name, sigma in (
        ("K", "cup_k_loc5", 5.0),
        ("Th", "cup_th_loc5", 5.0),
        ("U", "cup_u_loc5", 5.0),
        ("ThK", "cup_thk_loc8", 8.0),
        ("UK", "cup_uk_loc8", 8.0),
        ("TMI_up150", "cup_up150_loc8", 8.0),
    ):
        write(name, _local_contrast(grids[src], valid[src], sigma))
    gc.collect()

    # Paired troughs on shallow RTP (prepared physical column) and deep TMI_up150.
    rtp_grid = np.full((h, w), np.nan, dtype=np.float32)
    rtp_grid.ravel()[fp_idx] = base_memmap[:, base_names.index("rtp")]
    rtp_valid = fp & np.isfinite(rtp_grid)
    up_valid = valid["TMI_up150"]
    trough_rtp = paired_trough(rtp_grid, rtp_valid)
    trough_up = paired_trough(grids["TMI_up150"], up_valid)
    sup_r = _support(rtp_valid, 72)
    sup_u = _support(up_valid, 72)
    tr = np.full((h, w), np.nan, dtype=np.float32)
    tu = np.full((h, w), np.nan, dtype=np.float32)
    tr[sup_r] = trough_rtp[sup_r]
    tu[sup_u] = trough_up[sup_u]
    write("cup_trough_rtp", tr)
    write("cup_trough_up", tu)
    both = sup_r & sup_u
    persist = np.full((h, w), np.nan, dtype=np.float32)
    persist[both] = (tu[both] / (tr[both] + tu[both] + 1e-6)).astype(np.float32)
    write("cup_trough_persist", persist)
    del trough_rtp, trough_up, tr, tu, persist
    gc.collect()

    # Deep-shallow residual gradient at 300 m (GVC1 used a sigma-20 scalar level).
    joint = rtp_valid & up_valid
    resid = _robust_z(grids["TMI_up150"], joint) - _robust_z(rtp_grid, joint)
    resid_fill = gaussian_filter(_nearest_fill(resid, joint), 3.0, truncate=4)
    out = np.full((h, w), np.nan, dtype=np.float32)
    sup = _support(joint, 20)
    out[sup] = _grad_mag(resid_fill)[sup]
    write("cup_deep_resid_grad", out)
    del rtp_grid, resid, resid_fill, out, grids, valid
    mm.flush()
    gc.collect()
    return mm, list(CUP_FEATURE_NAMES)
