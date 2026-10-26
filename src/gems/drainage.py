"""H24-DRAIN5: D8 drainage-network knickpoint & deflection channels (preregistered 2026-10-26).

Implements the locked specification in
``knowledge/26_preregistered_DRAIN5_2026-10-26.md``: single-flow-direction (D8,
O'Callaghan & Mark 1984) routing on the competition ``det_elev`` 100 m DEM,
producing upslope contributing area ``A``, normalised channel steepness
``k_sn = S * A**0.45`` (Flint 1974 stream-power form; reference concavity
``theta_ref = 0.45`` as in Wobus et al. 2006), the downstream knickpoint jump
``k_sn(x) - k_sn(recv(x))``, an 8-azimuth co-linearity response of channel-gated
positive knickpoints (shared ``gems.gvc.oriented_lineament_response``),
distance-to-channel, height-above-nearest-channel (HAND; Renno et al. 2008),
and the flow-azimuth bend ``1 - cos(delta azimuth)`` over two downstream links.

Routing policy (locked, disclosed): the DEM is nearest-filled only to evaluate
the Gaussian smoothing stencil (sigma 2 px = 200 m, suppressing 100 m sampling
pits); **no depression filling** is applied. A valid cell with no strictly-lower
valid neighbour is a sink (self-receiver; accumulation terminates there) — the
physically correct endorheic behaviour for Great Basin playas, and a disclosed
limitation for through-flowing reaches crossing residual DEM pits. Receivers
require strictly positive drop/distance (diagonals / sqrt(2)), with the fixed
neighbour order below and first-max tie-breaking, so every routed edge strictly
descends and the flow graph is a DAG: processing cells in descending smoothed
elevation order therefore yields exact D8 accumulation. Channels are ``NaN``
wherever the original DEM is invalid (native HGB missing-value routing, as in
``gems.dprf1`` SAHG channels).

Anti-leakage invariants: the only input is the physical ``det_elev`` band. No
labels, catalogue distances, registry rasters or prior submission pixels are
read here.
"""

from __future__ import annotations

import gc
import json
from pathlib import Path
from typing import Any

import numpy as np
from scipy.ndimage import distance_transform_edt, gaussian_filter

from . import gvc

DRAIN5_FEATURE_NAMES: tuple[str, ...] = (
    "drn_log_accum",
    "drn_ksn",
    "drn_knick",
    "drn_knick_lineament",
    "drn_chan_dist",
    "drn_hand",
    "drn_bend",
)

# Drainage gate channels averaged into the concealed Regime-B multiplier in Arm 1.
DRAIN5_REGIME_B_NAMES: tuple[str, ...] = (
    "drn_knick",
    "drn_knick_lineament",
    "drn_ksn",
)

DEM_COLUMN = "det_elev"
PIXEL_M = 100.0
SMOOTH_SIGMA_PX = 2.0
THETA_REF = 0.45
CHANNEL_MIN_ACCUM = 100.0  # cells; 1 cell = 1 ha at 100 m -> ~1 km^2 contributing area
KNICK_GATE_ACCUM = 20.0  # cells
KNICK_LINEAMENT_SIGMA_PX = 1.5

# Fixed D8 neighbour order (first-max tie-break): (dy, dx, distance in px).
NEIGHBORS: tuple[tuple[int, int, float], ...] = (
    (-1, -1, float(np.sqrt(2.0))),
    (-1, 0, 1.0),
    (-1, 1, float(np.sqrt(2.0))),
    (0, -1, 1.0),
    (0, 1, 1.0),
    (1, -1, float(np.sqrt(2.0))),
    (1, 0, 1.0),
    (1, 1, float(np.sqrt(2.0))),
)


def d8_receivers(
    z_smooth: np.ndarray, valid: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """D8 steepest-descent receivers on the grid.

    Returns ``(receiver_flat, direction_index, is_sink)`` where
    ``receiver_flat`` holds grid-flat indices (self for sinks, -1 where
    invalid), ``direction_index`` indexes ``NEIGHBORS`` (-1 for sinks/invalid),
    and ``is_sink`` marks valid cells with no strictly-lower valid neighbour.
    """
    z = np.asarray(z_smooth, dtype=np.float32)
    v = np.asarray(valid, dtype=bool)
    h, w = z.shape
    z_pad = np.pad(z, 1, mode="edge")
    v_pad = np.pad(v, 1, mode="constant", constant_values=False)
    best_drop = np.zeros((h, w), dtype=np.float32)
    direction = np.full((h, w), -1, dtype=np.int8)
    for k, (dy, dx, dist) in enumerate(NEIGHBORS):
        z_n = z_pad[1 + dy : 1 + dy + h, 1 + dx : 1 + dx + w]
        v_n = v_pad[1 + dy : 1 + dy + h, 1 + dx : 1 + dx + w]
        drop = np.where(v_n, (z - z_n) / np.float32(dist), np.float32(-np.inf))
        better = drop > best_drop
        best_drop = np.where(better, drop, best_drop)
        direction = np.where(better, np.int8(k), direction)
        del z_n, v_n, drop, better
    del z_pad, v_pad
    is_sink = v & (direction < 0)
    flat = np.arange(h * w, dtype=np.int64).reshape(h, w)
    receiver = flat.copy()
    routed = v & ~is_sink
    if routed.any():
        offs = np.array([dy * w + dx for dy, dx, _ in NEIGHBORS], dtype=np.int64)
        receiver[routed] = flat[routed] + offs[direction[routed].astype(np.int64)]
    receiver[~v] = -1
    direction[~v] = -1
    return receiver, direction, is_sink


def flow_accumulation(
    z_smooth: np.ndarray, valid: np.ndarray, receiver_flat: np.ndarray
) -> np.ndarray:
    """Exact D8 upslope cell count ``A`` (self excluded) via descending-elevation order.

    Every routed edge strictly descends, so processing valid cells in descending
    smoothed-elevation order propagates each cell's accumulated count to its
    receiver exactly once. The sequential pass runs over Python lists (the only
    non-vectorised step); ties in elevation never carry an edge, so tie order
    cannot affect the result.
    """
    z = np.asarray(z_smooth, dtype=np.float32)
    v = np.asarray(valid, dtype=bool)
    valid_flat = np.flatnonzero(v.ravel())
    n_valid = len(valid_flat)
    compact_of_flat = np.full(z.size, -1, dtype=np.int64)
    compact_of_flat[valid_flat] = np.arange(n_valid, dtype=np.int64)
    recv_flat_valid = np.asarray(receiver_flat, dtype=np.int64).ravel()[valid_flat]
    recv_compact = compact_of_flat[recv_flat_valid]
    if (recv_compact < 0).any():
        raise ValueError("A valid cell routes to an invalid cell; receiver map is inconsistent")
    del compact_of_flat, recv_flat_valid
    z_valid = z.ravel()[valid_flat].astype(np.float64)
    order = np.argsort(-z_valid, kind="stable")
    del z_valid
    accum = [1.0] * n_valid
    recv_list = recv_compact.tolist()
    del recv_compact
    for c in order.tolist():
        r = recv_list[c]
        if r != c:
            accum[r] += accum[c]
    del recv_list, order
    a_grid = np.full(z.shape, np.nan, dtype=np.float32)
    a_grid.ravel()[valid_flat] = (np.asarray(accum, dtype=np.float64) - 1.0).astype(np.float32)
    del accum
    return a_grid


def compute_drainage_channels(
    dem: np.ndarray, footprint: np.ndarray
) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    """Compute the 7 locked DRAIN5 channels from a ``det_elev`` grid (NaN = invalid)."""
    fp = np.asarray(footprint, dtype=bool)
    z_raw = np.asarray(dem, dtype=np.float32)
    valid = fp & np.isfinite(z_raw)
    if int(valid.sum()) < 1000:
        raise ValueError("DEM has too few valid footprint cells for drainage routing")

    z_fill = gvc._nearest_fill(np.where(valid, z_raw, 0.0).astype(np.float32), valid)
    z_smooth = gaussian_filter(z_fill, sigma=SMOOTH_SIGMA_PX, mode="nearest").astype(np.float32)
    del z_fill
    gc.collect()

    receiver, direction, is_sink = d8_receivers(z_smooth, valid)
    accum = flow_accumulation(z_smooth, valid, receiver)

    gy, gx = np.gradient(z_smooth, PIXEL_M)
    slope = np.hypot(gx, gy).astype(np.float32)
    del gy, gx
    gc.collect()

    def at_receiver(grid: np.ndarray, receiver_grid: np.ndarray) -> np.ndarray:
        """grid values sampled at each cell's receiver (NaN where invalid)."""
        out = np.full(grid.shape, np.nan, dtype=np.float32)
        ok = receiver_grid >= 0
        out.ravel()[np.flatnonzero(ok.ravel())] = grid.ravel()[receiver_grid.ravel()[ok.ravel()]]
        return out

    log_accum = np.where(valid, np.log10(1.0 + accum), np.nan).astype(np.float32)
    ksn = np.where(valid, slope * np.power(np.maximum(accum, 1.0), THETA_REF), np.nan).astype(
        np.float32
    )

    gate = valid & ~is_sink & (accum >= KNICK_GATE_ACCUM)
    knick = np.full(z_smooth.shape, np.nan, dtype=np.float32)
    knick[gate] = (ksn - at_receiver(ksn, receiver))[gate]

    knick_pos = np.zeros(z_smooth.shape, dtype=np.float32)
    knick_pos[gate] = np.maximum(knick[gate], 0.0)
    knick_smooth = gaussian_filter(
        knick_pos, sigma=KNICK_LINEAMENT_SIGMA_PX, mode="nearest"
    ).astype(np.float32)
    del knick_pos
    knick_lineament = gvc.oriented_lineament_response(
        knick_smooth, valid, half_len_px=4, flank_offset_px=3
    )
    del knick_smooth
    gc.collect()

    channel = valid & (accum >= CHANNEL_MIN_ACCUM)
    if not channel.any():
        raise ValueError("No channel cells at the locked accumulation threshold")
    chan_dist_px, chan_idx = distance_transform_edt(~channel, return_indices=True)
    chan_dist = np.where(valid, np.log1p(chan_dist_px.astype(np.float32)), np.nan).astype(
        np.float32
    )
    z_chan = z_smooth[tuple(chan_idx)]
    hand = np.where(valid, np.clip(z_smooth - z_chan, -50.0, 500.0), np.nan).astype(np.float32)
    del chan_dist_px, chan_idx, z_chan
    gc.collect()

    # Flow-azimuth bend over two downstream links: 1 - cos(angle) in [0, 2].
    unit = np.zeros((len(NEIGHBORS), 2), dtype=np.float64)
    for k, (dy, dx, dist) in enumerate(NEIGHBORS):
        unit[k] = (dy / dist, dx / dist)
    dir2 = np.full(direction.shape, -1, dtype=np.int8)
    ok = receiver >= 0
    dir2.ravel()[np.flatnonzero(ok.ravel())] = direction.ravel()[receiver.ravel()[ok.ravel()]]
    bend = np.full(z_smooth.shape, np.nan, dtype=np.float32)
    bend_gate = gate & (direction >= 0) & (dir2 >= 0)
    if bend_gate.any():
        u1 = unit[direction[bend_gate].astype(np.int64)]
        u2 = unit[dir2[bend_gate].astype(np.int64)]
        bend[bend_gate] = (1.0 - np.einsum("ij,ij->i", u1, u2)).astype(np.float32)
        del u1, u2
    del dir2, direction, receiver
    gc.collect()

    channels: dict[str, np.ndarray] = {
        "drn_log_accum": log_accum,
        "drn_ksn": ksn,
        "drn_knick": knick,
        "drn_knick_lineament": np.asarray(knick_lineament, dtype=np.float32),
        "drn_chan_dist": chan_dist,
        "drn_hand": hand,
        "drn_bend": bend,
    }
    for name, grid in channels.items():
        if name not in DRAIN5_FEATURE_NAMES:
            raise AssertionError(f"Unexpected drainage channel {name}")
        grid[~valid] = np.nan

    a_valid = accum[valid]
    diagnostics: dict[str, Any] = {
        "valid_dem_cells": int(valid.sum()),
        "footprint_cells": int(fp.sum()),
        "sink_cells": int(is_sink.sum()),
        "sink_fraction_of_valid": float(is_sink.sum() / valid.sum()),
        "channel_cells_accum_ge_100": int(channel.sum()),
        "accum_max_cells": float(np.nanmax(a_valid)),
        "accum_median_cells": float(np.nanmedian(a_valid)),
        "channel_finite_fraction_on_footprint": {
            name: float(np.isfinite(grid[fp]).mean()) for name, grid in channels.items()
        },
        "labels_read": False,
    }
    del accum, slope, z_smooth, is_sink, gate, channel
    gc.collect()
    return channels, diagnostics


def build_drainage_memmap(
    root: Path,
    base_mm: np.ndarray,
    base_names: list[str],
    footprint: np.ndarray,
    out_path: Path,
) -> tuple[np.ndarray, list[str], dict[str, Any]]:
    """Compute or load the 7 DRAIN5 channels as a footprint-row float32 memmap."""
    fp = np.asarray(footprint, dtype=bool)
    fp_ids = np.flatnonzero(fp.ravel())
    n_fp = len(fp_ids)
    diag_path = out_path.with_suffix(".diag.json")
    if out_path.exists() and diag_path.exists():
        mm = np.load(out_path, mmap_mode="r")
        if mm.shape == (n_fp, len(DRAIN5_FEATURE_NAMES)) and mm.dtype == np.float32:
            return mm, list(DRAIN5_FEATURE_NAMES), json.loads(diag_path.read_text())

    dem = np.full(fp.shape, np.nan, dtype=np.float32)
    dem.ravel()[fp_ids] = base_mm[:, base_names.index(DEM_COLUMN)]
    channels, census = compute_drainage_channels(dem, fp)
    del dem
    gc.collect()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    mm_w = np.lib.format.open_memmap(
        out_path, mode="w+", dtype=np.float32, shape=(n_fp, len(DRAIN5_FEATURE_NAMES))
    )
    for j, name in enumerate(DRAIN5_FEATURE_NAMES):
        mm_w[:, j] = np.asarray(channels[name], dtype=np.float32).ravel()[fp_ids]
    mm_w.flush()
    del channels, mm_w
    gc.collect()

    diagnostics = {
        **census,
        "channels": list(DRAIN5_FEATURE_NAMES),
        "regime_b_gate_names": list(DRAIN5_REGIME_B_NAMES),
        "inputs": [DEM_COLUMN],
        "routing": "D8 steepest descent (drop/distance), first-max tie-break, fixed neighbour order",
        "depression_policy": "no pit filling; Gaussian sigma=2 px smoothing; sinks terminate accumulation (endorheic)",
        "smooth_sigma_px": SMOOTH_SIGMA_PX,
        "theta_ref": THETA_REF,
        "channel_min_accum_cells": CHANNEL_MIN_ACCUM,
        "knick_gate_accum_cells": KNICK_GATE_ACCUM,
    }
    diag_path.write_text(json.dumps(diagnostics, indent=2) + "\n")
    return np.load(out_path, mmap_mode="r"), list(DRAIN5_FEATURE_NAMES), diagnostics
