"""H24-CGMK1: signed gravity-magnetic cross-gradient reversal + conditional-K front.

Preregistration: ``knowledge/32_preregistered_CGMK1_2026-10-27.md`` (commits
``9b280a3`` + amendment ``8dafdc5``, both before any result). This module only
builds label-free feature channels. All scoring uses the shared
``holdout.SegmentHoldout`` / ``metric`` / ``emission`` / ``submission`` tools;
nothing here reads labels, registry rasters, or prior predictions.

Design exclusions (preregistered): no ``det_elev``/``det_elev_slope`` DEM
trunk, no LiDAR channels, no band-6 ``tc`` (provenance unestablished), no
catalogue-distance features anywhere in the model (catalogue distance is
used only as the fixed >2 px emission clearance applied by the runner).
"""

from __future__ import annotations

import gc
import json
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import binary_erosion, distance_transform_edt, gaussian_filter

from .geofeatures import BAND_ORDER, _valid
from .validator import sha256_file

RAW16 = (
    "mag_anom",
    "rtp",
    "tmi_hg",
    "tmi_vg",
    "tmi",
    "iso_grav_anom",
    "iso_grav_anom_hg",
    "iso_grav_anom_vg",
    "iso_grav_anom_slope",
    "cond_surf",
    "depth_to_base_surf",
    "geod_2ndinv",
    "geod_shearrate",
    "geod_dilaterate",
    "deq_n100a15",
    "ieq_n100a15",
)
RAD8 = ("rad_K", "rad_Th", "rad_U", "rad_TC", "ext_ThK", "ext_UK", "ext_UTh", "ext_TMI_up150")
BASE25 = RAW16 + ("log_deq_ieq",) + RAD8
CROSS8 = (
    "cg_sin_s1",
    "cg_cos_s1",
    "cg_rev_s1",
    "cg_magprod_s1",
    "cg_sin_s25",
    "cg_cos_s25",
    "cg_rev_s25",
    "cg_magprod_s25",
)
CONDK4 = ("kres", "kres_grad_s1", "kres_grad_s25", "kfront")
STACK33 = BASE25 + CROSS8
FULL37 = STACK33 + CONDK4
CONTROL25 = BASE25

EROSION_PX = 14  # covers the 12 px maximum stencil radius, see preregistration
SIGMAS = (1.0, 2.5)


def _nearest_fill(grid: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """Fill invalid cells by nearest valid value (stencil neighbourhood only).

    Support erosion in the caller guarantees filled values never influence a
    scored pixel: every scored pixel's full stencil lies inside ``valid``.
    """
    if valid.all():
        return grid.astype(np.float32, copy=True)
    inds = distance_transform_edt(~valid, return_distances=False, return_indices=True)
    filled = grid[tuple(inds)].astype(np.float32, copy=False)
    del inds
    return filled


def _grad_mag(grid: np.ndarray) -> np.ndarray:
    gy, gx = np.gradient(grid)
    out = np.hypot(gx, gy).astype(np.float32)
    del gy, gx
    return out


def cross_gradient_channels(
    mag: np.ndarray, grav: np.ndarray, support: np.ndarray, sigma: float
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Signed/unsigned inter-field gradient geometry at one smoothing scale.

    ``mag``/``grav`` must already be nearest-valid filled. Returns
    (sin theta, cos theta, |grad sin theta|, log1p(|g|*|m|)) as float32 grids.
    Raises on non-finite results inside ``support`` so stencil mistakes fail
    loudly instead of silently scoring filled values.
    """
    gs = gaussian_filter(grav, sigma, mode="nearest")
    ms = gaussian_filter(mag, sigma, mode="nearest")
    ggy, ggx = np.gradient(gs)
    del gs
    mgy, mgx = np.gradient(ms)
    del ms
    gn = np.hypot(ggx, ggy)
    mn = np.hypot(mgx, mgy)
    prod = gn * mn
    del gn, mn
    if not np.isfinite(prod[support]).all():
        raise ValueError("cross-gradient magnitude non-finite inside support")
    eps = 1e-6 * float(np.median(prod[support]))
    if not np.isfinite(eps) or eps <= 0:
        raise ValueError("cross-gradient epsilon is not positive/finite")
    denom = prod + eps
    sin_t = ((ggx * mgy - ggy * mgx) / denom).astype(np.float32)
    cos_t = ((ggx * mgx + ggy * mgy) / denom).astype(np.float32)
    del ggx, ggy, mgx, mgy, denom
    magprod = np.log1p(prod).astype(np.float32)
    del prod
    rev = _grad_mag(sin_t)
    for name, ch in (("sin", sin_t), ("cos", cos_t), ("rev", rev), ("magprod", magprod)):
        if not np.isfinite(ch[support]).all():
            raise ValueError(f"cross-gradient channel {name} non-finite inside support")
    if float(np.abs(sin_t[support]).max()) > 1.0 + 1e-5:
        raise ValueError("signed cross-gradient sin escaped [-1, 1]")
    return sin_t, cos_t, rev, magprod


def build_stack33(root: Path, out_dir: Path, footprint: np.ndarray, *, force: bool = False) -> dict:
    """Build (or verify) the 33-channel footprint-vector memmap + support mask."""
    out_dir.mkdir(parents=True, exist_ok=True)
    stack_path = out_dir / "cgmk1_stack33.npy"
    meta_path = out_dir / "cgmk1_stack33.json"
    support_path = out_dir / "cgmk1_support.npy"
    inputs = {
        "training_features": root / "data/training_features.tif",
        "geodawn_rad": root / "data/external/geodawn_rad_u8.tif",
        "geodawn_extensions": root / "data/external/geodawn_extensions_u8.tif",
    }
    expected_hashes = {k: sha256_file(p) for k, p in inputs.items()}
    fp_ids = np.flatnonzero(footprint.ravel())
    shape = (len(fp_ids), len(STACK33))
    if stack_path.exists() and meta_path.exists() and support_path.exists() and not force:
        meta = json.loads(meta_path.read_text())
        if (
            meta.get("names") != list(STACK33)
            or meta.get("shape") != list(shape)
            or meta.get("inputs_sha256") != expected_hashes
            or meta.get("sha256") != sha256_file(stack_path)
        ):
            raise ValueError("CGMK1 cached stack failed verification; explicit force required")
        return meta
    if not force and (stack_path.exists() or meta_path.exists()):
        raise ValueError("Incomplete CGMK1 stack cache; explicit force required")

    tmp = out_dir / "cgmk1_stack33.partial.npy"
    mm = np.lib.format.open_memmap(tmp, mode="w+", dtype=np.float32, shape=shape)
    joint_valid = footprint.copy()
    raw_grids: dict[str, np.ndarray] = {}
    col = 0
    with rasterio.open(inputs["training_features"]) as ds:
        if ds.shape != footprint.shape or ds.count != 19:
            raise ValueError("training_features grid/band mismatch")
        for name in RAW16:
            a = ds.read(BAND_ORDER.index(name) + 1).astype(np.float32)
            v = _valid(a)
            joint_valid &= v
            vec = a.ravel()[fp_ids].astype(np.float32)
            vec[~v.ravel()[fp_ids]] = np.nan
            mm[:, col] = vec
            if name in ("rtp", "iso_grav_anom", "deq_n100a15", "ieq_n100a15"):
                raw_grids[name] = (a, v)
            else:
                del a
            del vec
            col += 1
            print(f"[cgmk1] raw {name} col {col - 1}", flush=True)
    deq, deq_v = raw_grids.pop("deq_n100a15")
    ieq, ieq_v = raw_grids.pop("ieq_n100a15")
    ratio = np.full(footprint.shape, np.nan, np.float32)
    both = deq_v & ieq_v
    ratio[both] = (
        np.log1p(np.clip(deq[both], 0, None)) - np.log1p(np.clip(ieq[both], 0, None))
    ).astype(np.float32)
    mm[:, col] = ratio.ravel()[fp_ids]
    col += 1
    del deq, ieq, ratio, both
    gc.collect()

    rad_names = ["K", "Th", "U", "TC"]
    ext_names = ["ThK", "UK", "UTh", "TMI_up150"]
    for product, names in (("geodawn_rad", rad_names), ("geodawn_extensions", ext_names)):
        with rasterio.open(inputs[product]) as ds:
            if ds.shape != footprint.shape or ds.count != 4:
                raise ValueError(f"{product} grid/band mismatch")
            for b, _nm in enumerate(names, start=1):
                u = ds.read(b)
                ok = u > 0
                joint_valid &= ok | ~footprint
                vec = np.full(len(fp_ids), np.nan, np.float32)
                sel = ok.ravel()[fp_ids]
                vec[sel] = u.ravel()[fp_ids][sel].astype(np.float32) / 255.0
                mm[:, col] = vec
                col += 1
                del u, ok, vec, sel
        print(f"[cgmk1] {product} done at col {col}", flush=True)
    # joint_valid above: rad/ext validity is only required inside the footprint.
    joint_valid &= footprint

    support = binary_erosion(
        joint_valid, structure=np.ones((3, 3), bool), iterations=EROSION_PX, border_value=0
    )
    np.save(support_path, support)
    print(f"[cgmk1] support pixels {int(support.sum())} of {int(footprint.sum())}", flush=True)

    rtp, rtp_v = raw_grids.pop("rtp")
    grav, grav_v = raw_grids.pop("iso_grav_anom")
    mag_f = _nearest_fill(np.where(rtp_v, rtp, 0.0).astype(np.float32), rtp_v)
    grav_f = _nearest_fill(np.where(grav_v, grav, 0.0).astype(np.float32), grav_v)
    del rtp, grav, raw_grids
    gc.collect()
    for sigma in SIGMAS:
        for ch in cross_gradient_channels(mag_f, grav_f, support, sigma):
            vec = ch.ravel()[fp_ids].astype(np.float32)
            vec[~support.ravel()[fp_ids]] = np.nan
            mm[:, col] = vec
            col += 1
            del ch, vec
        gc.collect()
        print(f"[cgmk1] cross-gradient sigma {sigma} done at col {col}", flush=True)
    del mag_f, grav_f
    if col != len(STACK33):
        raise AssertionError(f"stack column count {col} != {len(STACK33)}")
    mm.flush()
    del mm
    tmp.replace(stack_path)
    meta = {
        "names": list(STACK33),
        "shape": list(shape),
        "dtype": "float32",
        "inputs_sha256": expected_hashes,
        "sha256": sha256_file(stack_path),
        "support_pixels": int(support.sum()),
        "footprint_pixels": int(footprint.sum()),
        "erosion_px": EROSION_PX,
        "excluded_by_design": [
            "det_elev",
            "det_elev_slope",
            "tc",
            "all LiDAR channels",
            "all catalogue-distance features",
        ],
        "provenance": "owner-supplied mirror verified by hash only; not organizer-authenticated",
    }
    meta_path.write_text(json.dumps(meta, indent=2) + "\n")
    return meta


def fit_condk_coeffs(rk: np.ndarray, rth: np.ndarray, ru: np.ndarray) -> np.ndarray:
    """OLS ``rK ~ 1 + rTh + rU + rTh*rU`` on clean ordinal-rank rows (label-free)."""
    rk, rth, ru = (np.asarray(x, dtype=np.float64) for x in (rk, rth, ru))
    ok = np.isfinite(rk) & np.isfinite(rth) & np.isfinite(ru)
    if ok.sum() < 1000:
        raise ValueError("Too few finite radiometric rows for conditional-K fit")
    design = np.column_stack([np.ones(int(ok.sum())), rth[ok], ru[ok], rth[ok] * ru[ok]])
    coeffs, *_ = np.linalg.lstsq(design, rk[ok], rcond=None)
    if not np.isfinite(coeffs).all():
        raise ValueError("Conditional-K fit is not finite")
    return coeffs


def condk_design(rk, rth, ru, coeffs):
    b0, b1, b2, b3 = (float(c) for c in coeffs)
    return b0 + b1 * rth + b2 * ru + b3 * (rth * ru)


def build_condk_matrix(
    stack: np.ndarray,
    names: list[str],
    footprint: np.ndarray,
    support: np.ndarray,
    coeffs: np.ndarray,
    out_path: Path,
) -> np.ndarray:
    """Materialize the 4 conditional-K channels as an (n_fp, 4) float32 .npy.

    Grids are reconstructed from the footprint-vector stack columns. Zeros are
    used as stencil fill only; ``support`` erosion guarantees no scored pixel
    touches a filled cell. Values outside support are set to NaN.
    """
    fp_ids = np.flatnonzero(footprint.ravel())
    sup_vec = support.ravel()[fp_ids]
    cols = {
        n: np.asarray(stack[:, names.index(n)], dtype=np.float32)
        for n in ("rad_K", "rad_Th", "rad_U")
    }

    def to_grid(vec: np.ndarray) -> np.ndarray:
        g = np.zeros(footprint.shape, np.float32)
        finite = np.isfinite(vec)
        g.ravel()[fp_ids[finite]] = vec[finite]
        return g

    rk_g, rth_g, ru_g = (to_grid(cols[n]) for n in ("rad_K", "rad_Th", "rad_U"))
    b0, b1, b2, b3 = (float(c) for c in coeffs)
    kres_g = (rk_g - (b0 + b1 * rth_g + b2 * ru_g + b3 * (rth_g * ru_g))).astype(np.float32)
    del rk_g

    partial = out_path.with_name(out_path.stem + ".partial.npy")
    mm_out = np.lib.format.open_memmap(partial, mode="w+", dtype=np.float32, shape=(len(fp_ids), 4))

    def write(col: int, grid: np.ndarray) -> None:
        vec = grid.ravel()[fp_ids].astype(np.float32)
        vec[~sup_vec] = np.nan
        mm_out[:, col] = vec

    write(0, kres_g)
    grad_s1 = _grad_mag(gaussian_filter(kres_g, 1.0, mode="nearest"))
    write(1, grad_s1)
    write(2, _grad_mag(gaussian_filter(kres_g, 2.5, mode="nearest")))
    del kres_g
    th_mag = _grad_mag(gaussian_filter(rth_g, 1.0, mode="nearest"))
    del rth_g
    u_mag = _grad_mag(gaussian_filter(ru_g, 1.0, mode="nearest"))
    del ru_g
    front = (grad_s1 / (1.0 + th_mag + u_mag)).astype(np.float32)
    del grad_s1, th_mag, u_mag
    write(3, front)
    del front
    mm_out.flush()
    del cols  # mm_out itself is a closure cell for write(); drop via gc below
    gc.collect()
    partial.replace(out_path)
    arr = np.load(out_path, mmap_mode="r")
    if not np.isfinite(np.asarray(arr[sup_vec])).all():
        raise ValueError("conditional-K channels non-finite inside support")
    return arr
