"""Unit tests for H24-TRSG1 physical operators, relief-stratified calibration, and two-regime emission."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from scipy.spatial.distance import pdist

from gems import trsg1

ROOT = Path(__file__).resolve().parents[1]


def test_feature_schema_and_selective_residual_indices():
    assert len(trsg1.FEATURE_NAMES) == 44
    assert len(set(trsg1.FEATURE_NAMES)) == 44
    # Tectonic strain and local topographic curvature must NOT be residualized away
    for preserved in (
        "geod_dilaterate",
        "geod_shearrate",
        "geod_2ndinv",
        "det_elev_slope",
        "det_local_relief",
        "relay_saddle_dem",
        "lidar_1",
    ):
        idx = trsg1.FEATURE_NAMES.index(preserved)
        assert idx not in set(trsg1.SELECTIVE_RESIDUAL_INDICES.tolist())
    # Survey/siting-sensitive scalars ARE selectively residualized
    for target in ("rtp", "iso_grav_anom", "tc", "eq_ieq_log", "ing_upflow_dog"):
        idx = trsg1.FEATURE_NAMES.index(target)
        assert idx in set(trsg1.SELECTIVE_RESIDUAL_INDICES.tolist())


def test_hyperbolic_saddle_twist_detects_saddle_and_suppresses_pure_ridge():
    yy, xx = np.mgrid[-25:26, -25:26].astype(np.float32)
    valid = np.ones_like(yy, dtype=bool)
    saddle = xx * xx - yy * yy  # det H = (2)(-2) - 0 = -4 < 0 => strong hyperbolic twist
    pure_ridge = -(yy * yy)  # det H = (0)(-2) - 0 = 0 => zero saddle twist
    dome = -(xx * xx + yy * yy)  # det H = (-2)(-2) = +4 > 0 => zero saddle twist

    tw_saddle = trsg1.hyperbolic_saddle_twist(saddle, valid, sigma_px=2.0)
    tw_ridge = trsg1.hyperbolic_saddle_twist(pure_ridge, valid, sigma_px=2.0)
    tw_dome = trsg1.hyperbolic_saddle_twist(dome, valid, sigma_px=2.0)

    assert float(tw_saddle[25, 25]) > 7.8
    assert float(tw_ridge[25, 25]) == pytest.approx(0.0, abs=1e-6)
    assert float(tw_dome[25, 25]) == pytest.approx(0.0, abs=1e-6)


def test_seismic_fabric_anisotropy_distinguishes_lineament_from_isotropic_blob():
    yy, xx = np.mgrid[-30:31, -30:31].astype(np.float32)
    valid = np.ones_like(yy, dtype=bool)
    lineament = np.exp(-0.5 * (yy / 2.0) ** 2)
    blob = np.exp(-0.5 * ((xx * xx + yy * yy) / 9.0))

    coh_line = trsg1.seismic_fabric_anisotropy(
        lineament, valid, grad_sigma_px=1.0, tensor_sigma_px=4.0
    )
    coh_blob = trsg1.seismic_fabric_anisotropy(blob, valid, grad_sigma_px=1.0, tensor_sigma_px=4.0)

    assert float(coh_line[30, 30]) > 4.0 * float(coh_blob[30, 30])


def test_local_dog_has_compact_decay_and_no_global_bullseye():
    fp = np.ones((121, 121), dtype=bool)
    imp = np.zeros((121, 121), dtype=np.float32)
    imp[60, 60] = 10.0
    dog = trsg1.local_dog_positive(imp, fp, sigma_narrow_px=4.0, sigma_wide_px=12.0)
    assert float(dog[60, 60]) > 0.05
    # Far from the impulse (>4*sigma_wide), DoG vanishes to exact 0.0 (no global radial coordinate)
    assert float(dog[0, 0]) == 0.0
    assert float(dog[0, 120]) == 0.0


def test_terrain_relief_calibrator_separates_flat_and_steep_lidar_gaps():
    rng = np.random.default_rng(42)
    n = 2400
    nuisance = np.column_stack(
        [
            rng.uniform(0.0, 5000.0, size=n),
            rng.uniform(0.0, 5000.0, size=n),
            np.tile(np.eye(4, dtype=np.float32), (n // 4, 1)),
        ]
    ).astype(np.float32)
    has_lidar = np.zeros(n, dtype=bool)
    has_lidar[:1200] = True
    relief = np.concatenate(
        [
            np.linspace(1.0, 300.0, 1200, dtype=np.float32),
            np.linspace(1.0, 300.0, 1200, dtype=np.float32),
        ]
    )
    # In LiDAR-covered domain: flat relief has low fault prob (0.05), steep relief has higher prob (0.35)
    # In LiDAR-gap domain: uncalibrated tree outputs compressed ~0.12 everywhere
    prob = np.where(
        has_lidar,
        np.where(relief > 200.0, 0.35, 0.05) + rng.normal(0.0, 0.01, size=n),
        0.12 + rng.normal(0.0, 0.01, size=n),
    )
    prob = np.clip(prob, 1e-4, 0.999).astype(np.float32)

    cal = trsg1.TerrainReliefRegimeCalibrator(alpha=100.0).fit(prob, has_lidar, relief, nuisance)
    out = cal.transform(prob, has_lidar, relief, nuisance)

    gap_flat = (~has_lidar) & (relief < 80.0)
    gap_steep = (~has_lidar) & (relief > 220.0)
    assert float(np.median(out[gap_steep])) > 2.5 * float(np.median(out[gap_flat]))


def test_rotated45_folds_partition_footprint_and_hide_whole_components():
    fp = np.ones((90, 90), dtype=bool)
    labels = np.zeros((90, 90), dtype=bool)
    # Continuous diagonal fault crossing multiple sectors + regional segments
    for k in range(10, 80):
        labels[k, k] = True
    labels[15, 40:75] = True
    labels[75, 15:50] = True
    labels[40:75, 15] = True

    folds = trsg1.make_rotated45_folds(fp, labels, buffer_px=6)
    assert len(folds) == 4
    union_valid = np.zeros_like(fp)
    overlap_valid = np.zeros_like(fp, dtype=int)
    for f in folds:
        union_valid |= f["valid"]
        overlap_valid += f["valid"].astype(int)
        # Train and valid are disjoint and separated by > buffer_px
        assert not np.any(f["train"] & f["valid"])
        assert not np.any(f["visible"] & f["truth"])
    assert np.array_equal(union_valid, fp)
    assert np.all(overlap_valid[fp] == 1)


def test_two_regime_poisson_enforces_global_min_spacing_and_clearance():
    h, w = 80, 80
    dom = np.ones((h, w), dtype=bool)
    vis = np.zeros((h, w), dtype=bool)
    vis[40, 20:60] = True

    yy, xx = np.mgrid[:h, :w].astype(np.float32)
    prob = (0.2 + 0.6 * np.exp(-((yy - 39.0) ** 2) / 50.0)).astype(np.float32)
    # Left half: concealed basin (depth=500m, slope=2 deg); Right half: range-front (depth=80m, slope=12 deg)
    depth = np.where(xx < 40, 500.0, 80.0).astype(np.float32)
    slope = np.where(xx < 40, 2.0, 12.0).astype(np.float32)
    sub_z = np.ones((h, w), dtype=np.float32)

    dots = trsg1.emit_two_regime_poisson(
        prob,
        dom,
        vis,
        depth,
        slope,
        sub_z,
        budget_frac=0.01,
        basin_budget_share=0.30,
        min_dist=3.0,
        clearance_px=2.0,
    )
    k_expected = int(round(0.01 * h * w))
    assert int(dots.sum()) == k_expected
    # No dot on or within <= 2.0 px of visible fault
    from scipy.ndimage import distance_transform_edt

    assert float(distance_transform_edt(~vis)[dots].min()) > 2.0
    # Pairwise Euclidean distance across ALL dots (including across x=40 regime boundary!) >= 3.0 px
    pts = np.argwhere(dots).astype(np.float64)
    assert float(pdist(pts).min()) >= 3.0 - 1e-6


def test_trsg1_verify_recorded_and_refuses_implicit_rerun():
    import json
    import subprocess
    import sys

    res_verify = subprocess.run(
        [sys.executable, "scripts/run_trsg1_lane.py", "--verify-recorded"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert res_verify.returncode == 0, res_verify.stderr
    payload = json.loads(res_verify.stdout)
    assert payload["verified"] is True
    assert payload["experiment_rerun"] is False
    assert payload["technical_promotion_gates_passed"] is True
    assert payload["verdict"] == "negative"
    assert payload["ok_to_submit"] is False

    res_rerun = subprocess.run(
        [sys.executable, "scripts/run_trsg1_lane.py", "--run"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert res_rerun.returncode != 0
    assert "refusing implicit rerun of locked preregistered experiment" in res_rerun.stderr


def test_trsg1_artifacts_are_hash_bound_strict_range_and_fail_closed():
    import json

    import rasterio

    from gems import footprint
    from gems.preflight import concise_status, preflight
    from gems.validator import sha256_file

    card_path = ROOT / "evidence/trsg1_run_card_20261026.json"
    dl_path = ROOT / "docs/data/trsg1_download.json"
    active_path = ROOT / "docs/data/active_lane.json"
    template = ROOT / "data/bridge/sample_submission.tif"
    template_sha = "2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc"

    card = json.loads(card_path.read_text())
    dl = json.loads(dl_path.read_text())
    active = json.loads(active_path.read_text())

    zeros = ROOT / "docs/downloads" / dl["file"]
    nan_p = ROOT / "docs/downloads" / dl["nan_file"]
    zip_p = ROOT / "docs/downloads" / dl["zip_file"]
    assert zeros.exists() and nan_p.exists() and zip_p.exists()
    assert sha256_file(zeros) == dl["sha256"] == card["raster_sha256"]
    assert sha256_file(nan_p) == dl["nan_sha256"] == card["nan_outside_sha256"]
    assert sha256_file(zip_p) == dl["zip_sha256"] == card["zip_sha256"]
    assert active["lane"] == "H24-S3DEP1"
    assert active["semantics"] == "current recorded point-best review; no new lane assignment"
    assert active["ok_to_submit"] is False
    sel = json.loads((ROOT / "evidence/trsg1_selector_20261026.json").read_text())
    assert sel["decision"] == "DO_NOT_SUBMIT" and sel["ok_to_submit"] is False
    assert len(dl["note"]) <= 140 and dl["note"] == card["note"]

    fp = footprint.load_footprint()
    with rasterio.open(zeros) as ds:
        arr = ds.read(1)
        assert ds.count == 1
        assert ds.dtypes == ("float32",)
        assert ds.shape == (3730, 3292)
        assert str(ds.crs) == "EPSG:32611"
        assert np.isfinite(arr).all()
        assert float(arr.min()) >= 0.0 and float(arr.max()) <= 1.0
        assert float(arr[~fp].max()) == 0.0
        assert int((arr[fp] > 0.5).sum()) == 37722

    with rasterio.open(nan_p) as ds_nan:
        arr_nan = ds_nan.read(1)
        assert np.isfinite(arr_nan[fp]).all()
        assert np.isnan(arr_nan[~fp]).all()
        assert np.array_equal(arr_nan[fp], arr[fp])

    report = preflight(
        zeros,
        template,
        run_card_path=card_path,
        expected_template_sha256=template_sha,
    )
    assert report["format_validation"]["format_valid"] is True
    assert report["portal_range_diagnostic"]["strict_whole_array_values_in_0_1"] is True
    assert report["run_card"]["scientific_authorization"] is False
    assert report["decision"]["submission_status"] == "DO_NOT_SUBMIT"
    assert report["decision"]["ready_to_submit"] is False
    assert "SUBMISSION: DO_NOT_SUBMIT" in concise_status(report)
