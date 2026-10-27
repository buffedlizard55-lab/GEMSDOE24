"""Unit and receipt-verification tests for the 2026-10-25 H24-SAHG1 lane and OOF benchmark."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import binary_erosion

from gems import novelty, sahg1, submission
from gems.validator import sha256_file

ROOT = Path(__file__).resolve().parents[1]


def test_verify_receptive_field_support_catches_boundary_and_interior_holes():
    raw_valid = np.ones((25, 25), dtype=bool)
    raw_valid[12, 12] = False
    # Un-eroded mask touches outer boundary and interior hole -> must fail
    assert not sahg1.verify_receptive_field_support(raw_valid, raw_valid, radius_px=4)

    # Eroded by 7x7 (radius 3) is still within 4 px of the hole -> must fail
    eroded_r3 = binary_erosion(raw_valid, structure=np.ones((7, 7), dtype=bool), border_value=False)
    assert not sahg1.verify_receptive_field_support(eroded_r3, raw_valid, radius_px=4)

    # Eroded by 9x9 (radius 4) satisfies exact 9x9 stencil support -> must pass
    eroded_r4 = binary_erosion(raw_valid, structure=np.ones((9, 9), dtype=bool), border_value=False)
    assert sahg1.verify_receptive_field_support(eroded_r4, raw_valid, radius_px=4)


def test_sahg1_build_surfaces_synthetic_grid():
    rng = np.random.default_rng(20261025)
    shape = (32, 32)
    fp = np.ones(shape, dtype=bool)
    fp[0, :] = False
    lidar_b = {k: rng.integers(5, 240, size=shape, dtype=np.uint8) for k in sahg1.LIDAR_SPECS}
    lidar_b["valid"] = np.where(fp, 255, 0).astype(np.uint8)
    rad_b = {k: rng.integers(5, 240, size=shape, dtype=np.uint8) for k in sahg1.RAD_BANDS}
    ext_b = {k: rng.integers(5, 240, size=shape, dtype=np.uint8) for k in sahg1.EXT_BANDS}
    geophys_b = {
        k: rng.normal(0.0, 1.0, size=shape).astype(np.float32) for k in sahg1.GEOPHYS_BANDS
    }
    surfaces, support = sahg1.build_surfaces(lidar_b, rad_b, ext_b, geophys_b, fp)
    assert support.any()
    assert not support[:4, :].any() and not support[-4:, :].any()
    cand = surfaces["candidate"]
    assert cand.shape == shape and cand.dtype == np.float32
    assert np.isfinite(cand).all()
    assert float(cand.min()) >= 0.0 and float(cand.max()) <= 1.0
    assert float(np.abs(cand[~support]).max()) == 0.0


def test_prospective_novelty_separates_calibration_controls(tmp_path):
    fp = np.ones((20, 20), dtype=bool)
    cand_dots = np.zeros((20, 20), dtype=np.float32)
    cand_dots[5, 5] = 1.0
    cand_dots[14, 14] = 1.0

    # Create one distinct method raster and one spacing-5 lattice control raster
    method_tif = tmp_path / "method_a.tif"
    lattice_tif = tmp_path / "13gems_20261001_r13-lattice-s5_v2_nan-outside.tif"
    profile = {
        "driver": "GTiff",
        "height": 20,
        "width": 20,
        "count": 1,
        "dtype": "float32",
        "crs": "EPSG:32611",
        "transform": rasterio.Affine(100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0),
    }
    template = tmp_path / "data/bridge/sample_submission.tif"
    template.parent.mkdir(parents=True)
    with rasterio.open(template, "w", **profile) as dst:
        dst.write(np.ones((20, 20), dtype=np.float32), 1)
    method_arr = np.zeros((20, 20), dtype=np.float32)
    method_arr[18, 2] = 1.0
    lattice_arr = np.zeros((20, 20), dtype=np.float32)
    lattice_arr[::5, ::5] = 1.0
    with rasterio.open(method_tif, "w", **profile) as dst:
        dst.write(method_arr, 1)
    with rasterio.open(lattice_tif, "w", **profile) as dst:
        dst.write(lattice_arr, 1)

    def fp_sha(a: np.ndarray) -> str:
        return __import__("hashlib").sha256(np.asarray(a[fp], dtype="<f4").tobytes()).hexdigest()

    items = [
        {
            "id": "registry-001",
            "repo": "buffedlizard55-lab/GEMSDOE32",
            "file": "docs/downloads/method_a.tif",
            "cache_path": "method_a.tif",
            "footprint_sha256": fp_sha(method_arr),
        },
        {
            "id": "registry-039",
            "repo": "local/inputs/calibration",
            "file": "inputs/calibration/13gems_20261001_r13-lattice-s5_v2_nan-outside.tif",
            "cache_path": "13gems_20261001_r13-lattice-s5_v2_nan-outside.tif",
            "footprint_sha256": fp_sha(lattice_arr),
        },
    ]
    res = novelty.compare_prospective_registry(cand_dots, fp, items, tmp_path, dots=(cand_dots > 0))
    assert res["competing_method_rasters_count"] == 1
    assert res["calibration_control_rasters_count"] == 1
    assert res["method_lane_passed"] is True
    assert res["literal_all_entries_passed"] is False
    assert res["passed"] is False


def test_sahg1_recorded_receipt_and_artifacts():
    proc = subprocess.run(
        [sys.executable, "scripts/run_sahg1_lane.py", "--verify-recorded"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    summary = json.loads(proc.stdout)
    assert summary["verified"] is True
    assert summary["experiment_rerun"] is False
    assert summary["method_lane_novelty_passed"] is True
    assert summary["literal_all_entries_passed"] is False
    assert summary["verdict"] == "negative"
    assert summary["ok_to_submit"] is False

    card = json.loads((ROOT / "evidence/sahg1_run_card_20261025.json").read_text())
    exp = json.loads((ROOT / "evidence/sahg1_experiment_20261025.json").read_text())
    dl = json.loads((ROOT / "docs/data/sahg1_download.json").read_text())

    # Check holdout labelling and comparison invariants
    assert card["holdout"]["label"] == "HOLDOUT-DTI"
    assert card["holdout"]["evaluator_version"] == "gems-segment-pooled-v1"
    assert card["holdout"]["n_withheld_positive_pixels"] == 60988
    assert card["holdout"]["dti"] > card["geomorphic_only_ablation"]["dti"]
    assert card["paired_comparisons"]["sahg1_minus_geomorphic_core_g0"]["ci95"][0] > 0.0
    assert card["reconstructed_oof_multiphysics_baseline"]["dti"] > card["holdout"]["dti"]
    assert (
        card["bridge_protocol_holdout"]["dti"]
        > card["bridge_protocol_holdout"]["recorded_aspc_dti"]
    )
    assert exp["canary"]["passed"] is True

    # Check exact GeoTIFF files and note
    z_tif = ROOT / "docs/downloads" / dl["file"]
    n_tif = ROOT / "docs/downloads" / dl["nan_file"]
    assert z_tif.exists() and n_tif.exists()
    assert sha256_file(z_tif) == card["raster_sha256"] == dl["sha256"]
    assert sha256_file(n_tif) == card["nan_outside_sha256"] == dl["nan_sha256"]
    assert len(card["note"]) <= 140
    assert "DO NOT SUBMIT" in card["note"]
    template = ROOT / "data/bridge/sample_submission.tif"
    v_z = submission.check_variants(z_tif, template)
    v_n = submission.check_variants(n_tif, template)
    assert v_z["format_valid"] and not v_z["ok_to_upload"] and not v_z["submission_authorized"]
    assert v_n["format_valid"] and not v_n["ok_to_upload"] and not v_n["submission_authorized"]


def test_sahg1_is_retained_and_rejects_checksum_tampering(tmp_path):
    dl = json.loads((ROOT / "docs/data/sahg1_download.json").read_text())
    for page in ("index.html", "docs/index.html", "docs/executive-summary.html"):
        html = (ROOT / page).read_text()
        assert f'download="{dl["file"]}"' in html
        assert f'download="{dl["nan_file"]}"' in html
        assert "H24-SAHG1" in html and "oof_multiphysics_hgb_d3" in html
        assert html.index('id="historical-') < html.index(dl["file"])
