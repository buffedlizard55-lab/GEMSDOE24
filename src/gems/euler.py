"""H24-EUL1: Euler-deconvolution basement-contact channels (preregistered 2026-10-26).

Implements the locked specification in ``knowledge/22_preregistered_EUL1_2026-10-26.md``:
moving-window (7x7 px) least-squares Euler homogeneity solutions at structural index
N=0 (vertical contact / step) for the GeoDAWN RTP magnetic and isostatic gravity
fields, plus a 300 m gravity x magnetic cross-gradient co-alignment channel and an
8-azimuth lineament response of the magnetic solution-density field.

Euler homogeneity (Thompson 1982; Reid et al. 1990): for a potential field ``F``
homogeneous of degree ``-N`` about a source at ``(x0, y0, z0)`` observed on ``z=0``,

    (x - x0) Fx + (y - y0) Fy + (0 - z0) Fz = N (B - F).

At ``N = 0`` the background ``B`` drops out and, in window-local pixel offsets
``(u, v)`` (columns, rows) relative to the window centre, every window pixel gives
one linear equation in the unknowns ``(x0, y0, z0)``:

    x0 Fx + y0 Fy + z0 Fz = u Fx + v Fy.

The 49 equations per window are solved in the least-squares sense for every pixel
simultaneously: the normal-equation sums are offset-weighted correlations of the
derivative-product fields (``scipy.ndimage.correlate`` with 7x7 offset kernels), and
the 3x3 systems are solved with the explicit adjugate. Horizontal derivatives are
central differences of the field itself (pixel units).

**Vertical-derivative amendment (label-free metrology, fixed before any fit; see
``knowledge/23_EUL1_prereg_amendment_2026-10-26.md``).** The preregistration planned
to use the survey ``*_vg`` bands as ``Fz``. Pre-fit band forensics showed the stack's
derivative conventions are inconsistent: ``tmi_hg`` is exactly ``2.0 x`` the
per-pixel ``np.gradient`` magnitude of ``tmi`` (corr 0.9906); ``tmi_vg`` is the
vertical derivative of ``tmi`` (corr 0.973 vs an FFT ``|k|`` derivative) but scaled
by ``~0.00937`` relative to per-pixel units; and ``iso_grav_anom_vg`` is **not** the
vertical derivative of ``iso_grav_anom`` at all (corr -0.008 vs FFT ``|k|``). Euler
homogeneity is meaningless with dimensionally mismatched derivatives, so ``Fz`` is
instead computed self-consistently from each field itself with the exact harmonic
identity ``Fz_down = IFFT( |k| * FFT(F) )`` (per-pixel units), validated against the
analytic derivative on a synthetic harmonic field in ``tests/test_euler.py``. The
survey ``*_vg`` bands are used only for the recorded forensics. Source *depth* is
recorded as ``|z0|`` so the result is invariant to the remaining overall ``Fz`` sign
convention; the signed-depth fraction is reported as a diagnostic.

Acceptance is label-free and fixed in the preregistration: depth 0.5-15 px
(50-1500 m), plan offset inside the window (|x0|, |y0| <= 3.5 px), relative
least-squares residual < 0.15, and a non-degenerate normal matrix. Accepted
solutions are accumulated at their solved plan position; density / depth / quality
channels are Gaussian-smoothed (sigma 1.5 px) accumulations, with ``NaN`` where no
accepted solution supports a depth/quality estimate (native HGB missing-value
routing, exactly as in ``gems.dprf1`` SAHG channels).

Anti-leakage invariants: no labels, catalogue distances, registry rasters or prior
submission pixels are read here. Inputs are physical survey bands only.
"""

from __future__ import annotations

import gc
from pathlib import Path
from typing import Any

import numpy as np
from scipy.ndimage import correlate, gaussian_filter

from . import gvc

EUL1_FEATURE_NAMES: tuple[str, ...] = (
    "eul_rtp_density",
    "eul_rtp_depth",
    "eul_rtp_quality",
    "eul_grav_density",
    "eul_grav_depth",
    "eul_xgrad_coalign",
    "eul_rtp_density_lineament",
)

# Euler density/quality channels that gate the concealed Regime-B allocation in Arm 1.
EUL1_REGIME_B_NAMES: tuple[str, ...] = (
    "eul_rtp_density",
    "eul_rtp_quality",
    "eul_grav_density",
)

WINDOW_PX = 7
DEPTH_MIN_PX = 0.5
DEPTH_MAX_PX = 15.0
PLAN_MAX_PX = 3.5
REL_RESID_MAX = 0.15
SMOOTH_SIGMA_PX = 1.5
SUPPORT_MIN = 1e-3


def fft_vertical_derivative(
    field: np.ndarray, valid: np.ndarray, *, pad_px: int = 64, taper_px: int = 48
) -> np.ndarray:
    """Self-consistent vertical derivative (per pixel) of a harmonic potential field.

    For a field satisfying Laplace's equation above its sources and measured on the
    plane ``z=0``, ``dF/dz_down`` has Fourier multiplier ``|k|`` (rad/px). Missing
    pixels are nearest-filled first; the grid is mirror-padded and the pad zone is
    cosine-tapered to the valid mean so edge ringing stays outside the returned
    domain. The overall sign corresponds to the ``z``-down convention; downstream
    Euler depth uses ``|z0|`` and is sign-invariant.
    """
    valid = np.asarray(valid, bool) & np.isfinite(field)
    filled = gvc._nearest_fill(field, valid).astype(np.float64)
    mean = float(np.mean(filled[valid])) if valid.any() else 0.0
    a = filled - mean
    if pad_px > 0:
        a = np.pad(a, pad_px, mode="reflect")
        if taper_px > 0:
            ramp = 0.5 - 0.5 * np.cos(np.linspace(0.0, np.pi, taper_px))
            t = min(taper_px, pad_px)
            for axis in (0, 1):
                sl_lo = [slice(None), slice(None)]
                sl_hi = [slice(None), slice(None)]
                sl_lo[axis] = slice(pad_px - t, pad_px)
                sl_hi[axis] = slice(a.shape[axis] - pad_px, a.shape[axis] - pad_px + t)
                shape = [1, 1]
                shape[axis] = t
                a[tuple(sl_lo)] *= ramp[-t:].reshape(shape)
                a[tuple(sl_hi)] *= ramp[::-1][-t:].reshape(shape)
                edge_lo = [slice(None), slice(None)]
                edge_hi = [slice(None), slice(None)]
                edge_lo[axis] = slice(0, pad_px - t)
                edge_hi[axis] = slice(a.shape[axis] - pad_px + t, a.shape[axis])
                a[tuple(edge_lo)] = 0.0
                a[tuple(edge_hi)] = 0.0
    h, w = a.shape
    kh = (np.fft.fftfreq(h) * 2.0 * np.pi)[:, None]
    kw = (np.fft.rfftfreq(w) * 2.0 * np.pi)[None, :]
    k_mag = np.sqrt(kh * kh + kw * kw)
    fz = np.fft.irfft2(np.fft.rfft2(a) * k_mag, s=(h, w))
    if pad_px > 0:
        fz = fz[pad_px:-pad_px, pad_px:-pad_px]
    return fz.astype(np.float32)


def _offset_kernels(window: int = WINDOW_PX) -> dict[str, np.ndarray]:
    """7x7 offset kernels (rows = v, cols = u) for windowed normal-equation sums."""
    half = window // 2
    vv, uu = np.mgrid[-half : half + 1, -half : half + 1].astype(np.float32)
    return {
        "1": np.ones((window, window), dtype=np.float32),
        "u": uu,
        "v": vv,
        "uu": uu * uu,
        "vv": vv * vv,
        "uv": uu * vv,
    }


def euler_solutions(
    field: np.ndarray,
    fz: np.ndarray,
    valid: np.ndarray,
    *,
    window: int = WINDOW_PX,
) -> dict[str, np.ndarray]:
    """Solve N=0 Euler homogeneity in every ``window`` x ``window`` neighbourhood.

    ``field`` / ``fz`` are the potential field and its vertical derivative on the
    observation plane (pixel units); non-``valid`` pixels are nearest-filled strictly
    for derivative/filter support and are invalid in the outputs. Returns per-centre
    arrays ``x0``, ``y0`` (plan offsets in px, cols/rows), ``depth`` (``|z0|`` px),
    ``z0_signed``, ``rel_resid`` and boolean ``accepted`` under the preregistered
    label-free acceptance rule.
    """
    valid = np.asarray(valid, bool) & np.isfinite(field) & np.isfinite(fz)
    f_fill = gvc._nearest_fill(field, valid)
    z_fill = gvc._nearest_fill(fz, valid)
    fy, fx = np.gradient(f_fill)  # axis0 = rows (y), axis1 = cols (x)
    fx = fx.astype(np.float32, copy=False)
    fy = fy.astype(np.float32, copy=False)
    fz_a = z_fill.astype(np.float32, copy=False)
    del f_fill, z_fill
    gc.collect()

    products = {
        "xx": fx * fx,
        "xy": fx * fy,
        "xz": fx * fz_a,
        "yy": fy * fy,
        "yz": fy * fz_a,
        "zz": fz_a * fz_a,
    }
    del fx, fy, fz_a
    gc.collect()

    kern = _offset_kernels(window)

    def corr(name: str, kname: str) -> np.ndarray:
        return correlate(products[name], kern[kname], mode="nearest")

    sxx, sxy, sxz = corr("xx", "1"), corr("xy", "1"), corr("xz", "1")
    syy, syz, szz = corr("yy", "1"), corr("yz", "1"), corr("zz", "1")
    # rhs r = sum a_i * b_i with b = u*Fx + v*Fy
    rx = corr("xx", "u") + corr("xy", "v")
    ry = corr("xy", "u") + corr("yy", "v")
    rz = corr("xz", "u") + corr("yz", "v")
    # bb = sum b_i^2
    bb = corr("xx", "uu") + 2.0 * corr("xy", "uv") + corr("yy", "vv")
    products.clear()
    gc.collect()

    # Explicit adjugate solve of S theta = r for symmetric 3x3 S.
    # cofactors of [[sxx, sxy, sxz], [sxy, syy, syz], [sxz, syz, szz]]
    c00 = syy * szz - syz * syz
    c01 = sxz * syz - sxy * szz
    c02 = sxy * syz - sxz * syy
    c11 = sxx * szz - sxz * sxz
    c12 = sxz * sxy - sxx * syz
    c22 = sxx * syy - sxy * sxy
    det = sxx * c00 + sxy * c01 + sxz * c02
    trace = sxx + syy + szz
    scale = (np.maximum(trace, 0.0) / 3.0) ** 3
    solvable = valid & (trace > 0.0) & (np.abs(det) > 1e-10 * np.maximum(scale, 1e-30)) & (bb > 0.0)

    inv_det = np.where(solvable, 1.0 / np.where(solvable, det, 1.0), 0.0).astype(np.float32)
    x0 = ((c00 * rx + c01 * ry + c02 * rz) * inv_det).astype(np.float32)
    y0 = ((c01 * rx + c11 * ry + c12 * rz) * inv_det).astype(np.float32)
    z0 = ((c02 * rx + c12 * ry + c22 * rz) * inv_det).astype(np.float32)
    del c00, c01, c02, c11, c12, c22, det, trace, scale, inv_det
    del sxx, sxy, sxz, syy, syz, szz
    gc.collect()

    # Least-squares residual: ||b - A theta||^2 = bb - theta . r  (at the solution)
    resid2 = np.maximum(bb - (x0 * rx + y0 * ry + z0 * rz), 0.0)
    rel_resid = np.sqrt(resid2 / np.maximum(bb, 1e-30)).astype(np.float32)
    del rx, ry, rz, bb, resid2
    gc.collect()

    depth = np.abs(z0)
    accepted = (
        solvable
        & (depth >= DEPTH_MIN_PX)
        & (depth <= DEPTH_MAX_PX)
        & (np.abs(x0) <= PLAN_MAX_PX)
        & (np.abs(y0) <= PLAN_MAX_PX)
        & (rel_resid < REL_RESID_MAX)
    )
    return {
        "x0": x0,
        "y0": y0,
        "z0_signed": z0,
        "depth": depth.astype(np.float32),
        "rel_resid": rel_resid,
        "accepted": accepted,
        "valid": valid,
    }


def _smoothed_solution_channels(
    sol: dict[str, np.ndarray], footprint: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, Any]]:
    """Accumulate accepted solutions at solved plan positions -> density/depth/quality."""
    h, w = footprint.shape
    acc = sol["accepted"]
    rows, cols = np.nonzero(acc)
    diag: dict[str, Any] = {
        "n_windows_valid": int(sol["valid"].sum()),
        "n_solutions_accepted": int(len(rows)),
        "accepted_fraction_of_valid": float(len(rows) / max(int(sol["valid"].sum()), 1)),
    }
    if len(rows):
        diag["signed_depth_positive_fraction"] = float(np.mean(sol["z0_signed"][acc] > 0))
        diag["median_depth_px"] = float(np.median(sol["depth"][acc]))
        diag["median_rel_resid"] = float(np.median(sol["rel_resid"][acc]))
    tgt_r = np.clip(np.rint(rows + sol["y0"][acc]).astype(np.int64), 0, h - 1)
    tgt_c = np.clip(np.rint(cols + sol["x0"][acc]).astype(np.int64), 0, w - 1)
    flat = tgt_r * w + tgt_c

    count = np.zeros(h * w, dtype=np.float32)
    dsum = np.zeros(h * w, dtype=np.float32)
    qsum = np.zeros(h * w, dtype=np.float32)
    np.add.at(count, flat, 1.0)
    np.add.at(dsum, flat, sol["depth"][acc])
    np.add.at(qsum, flat, (1.0 - sol["rel_resid"][acc]).astype(np.float32))
    del flat, tgt_r, tgt_c, rows, cols
    gc.collect()

    density = gaussian_filter(count.reshape(h, w), SMOOTH_SIGMA_PX, mode="nearest")
    dsm = gaussian_filter(dsum.reshape(h, w), SMOOTH_SIGMA_PX, mode="nearest")
    qsm = gaussian_filter(qsum.reshape(h, w), SMOOTH_SIGMA_PX, mode="nearest")
    del count, dsum, qsum
    gc.collect()

    supported = footprint & (density > SUPPORT_MIN)
    depth = np.full((h, w), np.nan, dtype=np.float32)
    quality = np.full((h, w), np.nan, dtype=np.float32)
    depth[supported] = dsm[supported] / density[supported]
    quality[supported] = qsm[supported] / density[supported]
    density_out = np.where(footprint, density, np.nan).astype(np.float32)
    del dsm, qsm, density
    gc.collect()
    return density_out, depth, quality, diag


def cross_gradient_coalign(
    mag_field: np.ndarray,
    grav_field: np.ndarray,
    valid: np.ndarray,
) -> np.ndarray:
    """(1 - |sin angle|) * sqrt(|grad mag| * |grad grav|), robust-z scored.

    High where magnetic and gravity gradients are strong *and* parallel - the
    signature of one basement boundary sourcing both fields (Gallardo & Meju 2004
    cross-gradient, here at native 100 m scale, unlike GVC1's 2 km scalar).
    """
    valid = np.asarray(valid, bool) & np.isfinite(mag_field) & np.isfinite(grav_field)
    m_fill = gvc._nearest_fill(mag_field, valid)
    g_fill = gvc._nearest_fill(grav_field, valid)
    my, mx = np.gradient(m_fill)
    gy, gx = np.gradient(g_fill)
    del m_fill, g_fill
    gc.collect()
    cross = np.abs(gx * my - gy * mx).astype(np.float32)
    gmag = np.hypot(gx, gy).astype(np.float32)
    mmag = np.hypot(mx, my).astype(np.float32)
    del mx, my, gx, gy
    gc.collect()
    denom = gmag * mmag
    sinang = np.clip(cross / np.maximum(denom, 1e-20), 0.0, 1.0)
    strength = np.sqrt(np.maximum(denom, 0.0))
    del cross, denom, gmag, mmag
    gc.collect()
    raw = ((1.0 - sinang) * strength).astype(np.float32)
    del sinang, strength
    out = gvc._robust_z(raw, valid)
    out[~valid] = np.nan
    return out.astype(np.float32)


def build_euler_memmap(
    root: Path,
    base_mm: np.ndarray,
    base_names: list[str],
    footprint: np.ndarray,
    out_path: Path,
) -> tuple[np.ndarray, list[str], dict[str, Any]]:
    """Compute or load the 7 EUL1 channels as a footprint-row float32 memmap."""
    fp = np.asarray(footprint, dtype=bool)
    fp_ids = np.flatnonzero(fp.ravel())
    n_fp = len(fp_ids)
    diag_path = out_path.with_suffix(".diag.json")
    if out_path.exists() and diag_path.exists():
        mm = np.load(out_path, mmap_mode="r")
        if mm.shape == (n_fp, len(EUL1_FEATURE_NAMES)) and mm.dtype == np.float32:
            import json

            return mm, list(EUL1_FEATURE_NAMES), json.loads(diag_path.read_text())

    def unpack(col: str) -> np.ndarray:
        grid = np.full(fp.shape, np.nan, dtype=np.float32)
        grid.ravel()[fp_ids] = base_mm[:, base_names.index(col)]
        return grid

    def vg_forensics(field_col: str, vg_col: str) -> dict[str, Any]:
        """Label-free check: is the survey *_vg band the vertical derivative of its field?"""
        f_full = unpack(field_col)
        vg_full = unpack(vg_col)
        h0, w0 = fp.shape
        sl = (slice(h0 // 2 - 600, h0 // 2 + 600), slice(w0 // 2 - 600, w0 // 2 + 600))
        f_cr, vg_cr = f_full[sl], vg_full[sl]
        v_cr = fp[sl] & np.isfinite(f_cr) & np.isfinite(vg_cr)
        fz_fft = fft_vertical_derivative(f_cr, v_cr)
        interior = np.zeros_like(v_cr)
        interior[150:-150, 150:-150] = True
        m = v_cr & interior
        x = fz_fft[m].astype(np.float64)
        y = vg_cr[m].astype(np.float64)
        slope = float((x * y).sum() / max((x * x).sum(), 1e-30))
        out = {
            "field": field_col,
            "vg_band": vg_col,
            "corr_vg_vs_fft_fz": float(np.corrcoef(x, y)[0, 1]) if m.sum() > 100 else None,
            "slope_vg_equals_slope_times_fft_fz_per_px": slope,
            "n_pixels": int(m.sum()),
        }
        del f_full, vg_full, f_cr, vg_cr, fz_fft
        gc.collect()
        return out

    forensics = {
        "tmi_vg_vs_tmi": vg_forensics("tmi", "tmi_vg"),
        "iso_grav_anom_vg_vs_iso_grav_anom": vg_forensics("iso_grav_anom", "iso_grav_anom_vg"),
    }

    rtp = unpack("rtp")
    field_valid = fp & np.isfinite(rtp)
    fz_rtp = fft_vertical_derivative(rtp, field_valid)
    sol_rtp = euler_solutions(rtp, fz_rtp, field_valid)
    dens_r, depth_r, qual_r, diag_r = _smoothed_solution_channels(sol_rtp, fp)
    del sol_rtp, fz_rtp
    gc.collect()

    grav = unpack("iso_grav_anom")
    field_valid_g = fp & np.isfinite(grav)
    fz_grav = fft_vertical_derivative(grav, field_valid_g)
    sol_grav = euler_solutions(grav, fz_grav, field_valid_g)
    dens_g, depth_g, _qual_g, diag_g = _smoothed_solution_channels(sol_grav, fp)
    del sol_grav, fz_grav, _qual_g
    gc.collect()

    xgrad = cross_gradient_coalign(rtp, grav, fp)
    del grav
    gc.collect()

    dens_valid = fp & np.isfinite(dens_r)
    lineament = gvc.oriented_lineament_response(
        np.where(dens_valid, dens_r, 0.0).astype(np.float32),
        dens_valid,
        half_len_px=4,
        flank_offset_px=3,
    )
    del rtp
    gc.collect()

    grids = [dens_r, depth_r, qual_r, dens_g, depth_g, xgrad, lineament]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    mm_w = np.lib.format.open_memmap(
        out_path, mode="w+", dtype=np.float32, shape=(n_fp, len(EUL1_FEATURE_NAMES))
    )
    for j, grid in enumerate(grids):
        mm_w[:, j] = np.asarray(grid, dtype=np.float32).ravel()[fp_ids]
    mm_w.flush()
    del grids, mm_w
    gc.collect()

    import json

    diagnostics = {
        "rtp": diag_r,
        "grav": diag_g,
        "window_px": WINDOW_PX,
        "structural_index_N": 0,
        "depth_acceptance_px": [DEPTH_MIN_PX, DEPTH_MAX_PX],
        "rel_resid_max": REL_RESID_MAX,
        "smooth_sigma_px": SMOOTH_SIGMA_PX,
        "channels": list(EUL1_FEATURE_NAMES),
        "inputs": ["rtp", "iso_grav_anom"],
        "fz_source": "self-consistent FFT |k| vertical derivative of each field (per-px); survey *_vg bands used only for forensics (amendment A1)",
        "vg_band_forensics": forensics,
        "labels_read": False,
    }
    diag_path.write_text(json.dumps(diagnostics, indent=2) + "\n")
    return np.load(out_path, mmap_mode="r"), list(EUL1_FEATURE_NAMES), diagnostics
