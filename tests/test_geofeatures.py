"""Tests for the feature-stack module: sentinel handling, rank quantization,
and the memmap assembly contract. Kept light (no full-raster IO in CI)."""

import numpy as np

from gems import geofeatures as gf


def test_band_list_matches_official_order():
    assert len(gf.BAND_ORDER) == 19
    assert gf.BAND_ORDER[0] == "mag_anom"
    assert gf.BAND_ORDER[11] == "det_elev"  # the DEM band derivatives use
    assert gf.BAND_ORDER[18] == "det_elev_slope"
    assert len(set(gf.BAND_ORDER)) == 19


def test_valid_masks_sentinels():
    a = np.array([0.0, -3.4e38, np.nan, 5.0, -1e31], dtype=np.float32)
    v = gf._valid(a)
    assert list(v) == [True, False, False, True, False]


def test_impute_preserves_valid_and_fills_isolated_invalid():
    a = np.arange(25, dtype=np.float32).reshape(5, 5)
    a[2, 2] = -3.4e38  # sentinel inside the valid grid
    v = gf._valid(a)
    out = gf._impute(a, v)
    assert np.isfinite(out[2, 2]) and out[2, 2] > gf.SENTINEL  # filled from neighbours
    assert out[0, 0] == a[0, 0]  # valid pixels untouched


def test_impute_keeps_unfillable_nan():
    a = np.zeros((7, 7), np.float32)
    a[:] = np.nan
    v = gf._valid(a)
    out = gf._impute(a, v)
    assert np.isnan(out).all()


def test_rank_monotone_and_bounded():
    rng = np.random.default_rng(0)
    col = rng.normal(size=1000).astype(np.float32)
    col[7] = np.nan
    r = gf._rank_u16(col)
    assert r.dtype == np.uint16 and r.max() <= 65534
    assert r[7] == 0  # non-finite -> 0
    fin = np.isfinite(col)
    vals = col[fin]
    ranks = r[fin]
    order = np.argsort(vals, kind="stable")
    assert np.all(np.diff(ranks[order]) >= 0)  # monotone in value


def test_semantics_documented():
    s = gf.band_semantics()
    for key in ("openness", "asmag", "slope", "quantization", "imputation"):
        assert key in s and len(s[key]) > 20
