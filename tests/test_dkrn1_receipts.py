"""Exact-file receipt, D8 operator, three-arm holdout, and nine-site tests for H24-DKRN1."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path

import numpy as np
import rasterio

from gems import dkrn1
from gems.benchmarks import recorded_point_best, recorded_points

ROOT = Path(__file__).resolve().parents[1]
CARD_PATH = ROOT / "evidence/dkrn1_run_card_20261026.json"
EXP_PATH = ROOT / "evidence/dkrn1_experiment_20261026.json"
SEL_PATH = ROOT / "evidence/dkrn1_selector_20261026.json"
DL_PATH = ROOT / "docs/data/dkrn1_download.json"
NINE_PATH = ROOT / "evidence/nine_site_executive_summary_dkrn1_20261026.json"


def test_dkrn1_verify_recorded_passes():
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/run_dkrn1_lane.py"), "--verify-recorded"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    out = json.loads(proc.stdout)
    assert out["verified"] is True
    assert out["lane_id"] == "H24-DKRN1"
    assert out["verdict"] == "negative"
    assert out["ok_to_submit"] is False
    assert out["selector_decision"] == "DO_NOT_SUBMIT"


def test_dkrn1_implicit_rerun_refused():
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/run_dkrn1_lane.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode != 0
    assert "refusing implicit rerun" in proc.stdout + proc.stderr


def test_dkrn1_exact_geotiff_and_three_arm_integrity():
    card = json.loads(CARD_PATH.read_text())
    exp = json.loads(EXP_PATH.read_text())
    sel = json.loads(SEL_PATH.read_text())
    dl = json.loads(DL_PATH.read_text())

    assert card["verdict"] == "negative"
    assert card["ok_to_download"] is True
    assert card["ok_to_submit"] is False
    assert card["submission_authorized"] is False
    assert card["submission_slots_used"] == 0
    assert card["organizer_confirmed_score"] is None
    assert sel["decision"] == "DO_NOT_SUBMIT"
    assert sel["ok_to_submit"] is False
    assert sel["human_inspection_used"] is False
    assert len(card["note"]) <= 140

    zeros_path = ROOT / "docs/downloads" / card["submission_name"]
    nan_path = ROOT / "docs/downloads" / card["nan_outside_artifact"]
    zip_path = ROOT / "docs/downloads" / card["zip_artifact"]
    assert zeros_path.is_file() and nan_path.is_file() and zip_path.is_file()
    assert hashlib.sha256(zeros_path.read_bytes()).hexdigest() == card["raster_sha256"]
    assert hashlib.sha256(nan_path.read_bytes()).hexdigest() == card["nan_outside_sha256"]
    assert hashlib.sha256(zip_path.read_bytes()).hexdigest() == card["zip_sha256"]

    with zipfile.ZipFile(zip_path) as zf:
        assert zf.namelist() == [card["submission_name"]]
        assert hashlib.sha256(zf.read(card["submission_name"])).hexdigest() == card["raster_sha256"]

    with (
        rasterio.open(zeros_path) as ds,
        rasterio.open(ROOT / "data/bridge/sample_submission.tif") as tmpl,
    ):
        arr = ds.read(1)
        assert ds.count == 1 and ds.dtypes == ("float32",)
        assert ds.shape == (3730, 3292) == tmpl.shape
        assert ds.crs == tmpl.crs and ds.crs.to_epsg() == 32611
        assert ds.transform == tmpl.transform
    assert bool(np.isfinite(arr).all())
    assert bool(((arr >= 0.0) & (arr <= 1.0)).all())
    assert int((arr > 0.5).sum()) == 37654 == dl["pixel_count"]

    # Leakage canary: all 62 channels checked and <= 0.90
    lc = card["leakage_canary"]
    assert lc["passed"] is True
    assert lc["n_features_checked"] == 62
    assert lc["worst_polarity_extremity"] <= 0.90
    assert len(lc["dkrn1_channel_pooled_aucs"]) == 10
    assert all(0.10 <= v <= 0.90 for v in lc["dkrn1_channel_pooled_aucs"].values())

    # Three-arm holdout & NE_LidarGapHeavy breakthrough
    h = card["holdout"]
    assert h["evaluator_version"] == "gems-segment-pooled-v1"
    assert h["n_withheld_positive_pixels"] == 60988
    arms = card["arms_same_evaluator"]
    assert 0.155 < arms["arm1_dkrn1_splitview_62ch"]["dti"] < 0.156
    assert 0.150 < arms["arm2_head_a_kernel47_ablation"]["dti"] < 0.151
    assert abs(arms["oof_multiphysics_hgb_d3_baseline"]["dti"] - 0.129996798011798) < 1e-9

    p_oof = card["paired_comparisons"]["arm1_vs_oof_multiphysics_hgb_d3"]
    assert p_oof["ci95_strictly_positive"] is True
    assert p_oof["fold_wins"] == 4

    p_dprf = card["paired_comparisons"]["arm1_vs_dprf1_replay"]
    ne_fold = next(f for f in p_dprf["folds"] if f["fold"] == "NE_LidarGapHeavy")
    assert ne_fold["candidate_wins"] is True
    assert ne_fold["candidate_dti"] > ne_fold["baseline_dti"]
    assert card["recorded_point_best_comparison"]["candidate_beats_recorded_point"] is False

    # Split-View Head A explicitly excluded all 15 raw LiDAR amplitude channels
    assert len(exp["head_a_gap_native_excluded_lidar_15"]) == 15

    # Benchmark inventory discovers DKRN1 while preserving DPRF1 as point-best
    assert recorded_point_best(ROOT)["lane"] == "DPRF1"
    lanes = {r["lane"] for r in recorded_points(ROOT)}
    assert "DKRN1" in lanes


def test_dkrn1_nine_site_20261026_forensics_and_site_ordering():
    nine = json.loads(NINE_PATH.read_text())
    expected = [
        "GEMSDOE24",
        "GEMSDOE25",
        "GEMSDOE27",
        "GEMSDOE28",
        "GEMSDOE30",
        "GEMSDOE31",
        "GEMSDOE32",
        "GEMSDOE33",
        "GEMSDOE36",
    ]
    assert [r["site"] for r in nine["sites"]] == expected
    by_site = {r["site"]: r for r in nine["sites"]}
    assert by_site["GEMSDOE30"]["whole_array_strict_0_1"] is False
    assert by_site["GEMSDOE31"]["apron_2_to_9px"] > 0.65
    for s, r in by_site.items():
        if s != "GEMSDOE24":
            assert r["dkrn1_3px_overlap_vs_site_artifact"] <= 0.70

    card = json.loads(CARD_PATH.read_text())
    dkrn1_file = card["submission_name"]
    dprf1_dl = json.loads((ROOT / "docs/data/dprf1_download.json").read_text())
    eul1_card = json.loads((ROOT / "evidence/eul1_run_card_20261026.json").read_text())
    for rel in (
        "index.html",
        "executive-summary.html",
        "docs/index.html",
        "docs/executive-summary.html",
    ):
        html = (ROOT / rel).read_text()
        assert dkrn1_file in html
        assert html.index(dprf1_dl["file"]) < html.index(dkrn1_file) < html.index(
            eul1_card["submission_name"]
        )
    readme = (ROOT / "README.md").read_text()
    assert dkrn1_file in readme
    assert readme.index("H24-DPRF1") < readme.index(dkrn1_file)


def test_dkrn1_synthetic_d8_routing_unit():
    yy, xx = np.mgrid[0:48, 0:48].astype(np.float32)
    # Tilted piedmont plane with a mid-slope fault scarp step at y = 24
    elev = (1500.0 - 8.0 * yy - 1.5 * xx + np.where(yy < 24, 18.0, 0.0)).astype(np.float32)
    slope = np.hypot(np.gradient(elev, axis=0), np.gradient(elev, axis=1)).astype(np.float32)
    relief = (elev - elev.mean()).astype(np.float32)
    fp = np.ones((48, 48), dtype=bool)
    ch = dkrn1.compute_d8_hydrologic_channels(elev, slope, relief, fp)
    assert set(ch) == {
        "d8_log_acc",
        "d8_stream_power_knick",
        "d8_knick_reach_max3",
        "d8_thalweg_turn",
        "d8_knick_corridor_900m",
        "d8_drainage_asymmetry_1km",
        "d8_incision_vs_catchment",
    }
    for arr in ch.values():
        assert arr.shape == (48, 48) and arr.dtype == np.float32
        assert np.isfinite(arr).all()
    # Every cell accumulates at least 1 cell -> log1p(acc) >= log(2)
    assert float(ch["d8_log_acc"].min()) >= np.log(2.0) - 1e-5
    assert float(ch["d8_log_acc"][-1, -1]) > float(ch["d8_log_acc"][0, 0])
    # Knickpoint response peaks along the synthetic y=22..26 scarp step
    scarp_band = float(ch["d8_stream_power_knick"][22:26, 8:40].mean())
    far_band = float(ch["d8_stream_power_knick"][4:10, 8:40].mean())
    assert scarp_band > far_band
