"""H24-DRAIN5 drainage-routing unit tests on synthetic label-free surfaces."""

from __future__ import annotations

import numpy as np

from gems import drainage


def _plane(h: int = 40, w: int = 30) -> tuple[np.ndarray, np.ndarray]:
    z = np.repeat((-2.0 * np.arange(h, dtype=np.float32))[:, None], w, axis=1)
    return z, np.ones((h, w), dtype=bool)


def test_d8_plane_flows_south_and_accumulates_exactly() -> None:
    z, valid = _plane()
    receiver, direction, is_sink = drainage.d8_receivers(z, valid)
    south = drainage.NEIGHBORS.index((1, 0, 1.0))
    assert (direction[:-1] == south).all()
    assert is_sink[-1].all() and not is_sink[:-1].any()
    flat = np.arange(z.size).reshape(z.shape)
    assert (receiver[:-1] == flat[:-1] + z.shape[1]).all()
    accum = drainage.flow_accumulation(z, valid, receiver)
    expected = np.repeat(np.arange(z.shape[0], dtype=np.float32)[:, None], z.shape[1], axis=1)
    np.testing.assert_array_equal(accum, expected)


def test_flow_accumulation_conserves_cells_on_random_dem() -> None:
    rng = np.random.default_rng(7)
    z = rng.random((60, 55), dtype=np.float32) * 100.0
    valid = np.ones(z.shape, dtype=bool)
    receiver, _direction, is_sink = drainage.d8_receivers(z, valid)
    accum = drainage.flow_accumulation(z, valid, receiver)
    # Forest rooted at sinks: every valid cell's unit count ends at exactly one sink.
    assert float((accum[is_sink] + 1.0).sum()) == float(valid.sum())
    assert np.isfinite(accum[valid]).all()
    assert (accum[valid] >= 0).all()


def test_pit_is_sink_and_collects_neighbours() -> None:
    z = np.full((9, 9), 10.0, dtype=np.float32)
    z[4, 4] = 0.0
    z[0, :] = z[-1, :] = 20.0
    z[:, 0] = z[:, -1] = 20.0
    valid = np.ones(z.shape, dtype=bool)
    receiver, _direction, is_sink = drainage.d8_receivers(z, valid)
    assert is_sink[4, 4]
    accum = drainage.flow_accumulation(z, valid, receiver)
    assert accum[4, 4] >= 8.0  # at least the 8 neighbours drain into the pit


def test_invalid_cells_never_receive_or_route() -> None:
    z, valid = _plane(20, 20)
    valid[10, :] = False
    receiver, direction, _is_sink = drainage.d8_receivers(z, valid)
    assert (receiver[~valid] == -1).all()
    routed_targets = receiver[valid & (direction >= 0)]
    assert valid.ravel()[routed_targets].all()


def test_channels_keys_nan_policy_and_straight_bend() -> None:
    # 150 rows so straight-south plane flow accumulates >= 100 cells (channel gate).
    z, valid = _plane(150, 40)
    dem = z.copy()
    dem[~valid] = np.nan
    channels, diag = drainage.compute_drainage_channels(dem, valid)
    assert tuple(channels) == drainage.DRAIN5_FEATURE_NAMES
    for grid in channels.values():
        assert np.isnan(grid[~valid]).all()
    bend = channels["drn_bend"]
    finite_bend = bend[np.isfinite(bend)]
    assert len(finite_bend) > 0
    # Plane flow is everywhere due south: zero azimuth bend on gated cells.
    assert np.allclose(finite_bend, 0.0, atol=1e-6)
    assert diag["labels_read"] is False
    assert diag["valid_dem_cells"] == 150 * 40
    assert diag["channel_cells_accum_ge_100"] == 50 * 40  # rows 100..149 in every column


def test_knickpoint_positive_at_slope_break() -> None:
    h, w = 100, 21
    profile = np.empty(h, dtype=np.float32)
    profile[:50] = -2.0 * np.arange(50)
    profile[50:] = profile[49] - 0.2 * np.arange(1, 51)
    dem = np.repeat(profile[:, None], w, axis=1)
    # Slight cross-slope so flow concentrates in the central column.
    dem = dem + (0.05 * np.abs(np.arange(w)[None, :] - w // 2)).astype(np.float32)
    fp = np.ones((h, w), dtype=bool)
    channels, _diag = drainage.compute_drainage_channels(dem, fp)
    knick = channels["drn_knick"][:, w // 2]
    near_break = np.nanmax(knick[45:56])
    upstream = np.nanmax(knick[25:40])
    assert near_break > upstream
    assert near_break > 0
