"""Tests for H24-GVC1 geothermal/tilt/lineament operators, paired holdout CIs,
prospective calibration-control separation, exact-file receipts, and site fail-closed gates."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import numpy as np
import pytest
import rasterio
from scipy.ndimage import distance_transform_edt

from gems import gvc, holdout, novelty, submission

ROOT = Path(__file__).resolve().parents[1]


def test_classify_space_filling_control_and_pigeonhole_bound(tmp_path):
    H, W = 60, 60
    fp = np.ones((H, W), dtype=bool)
    yy, xx = np.meshgrid(np.arange(H), np.arange(W), indexing="ij")
    lattice = ((yy % 5) == 2) & ((xx % 5) == 2)
    ctrl = novelty.classify_space_filling_control(fp, lattice, candidate_dot_count=40)
    assert ctrl["is_space_filling_calibration_control"] is True
    assert ctrl["footprint_3px_coverage"] > 0.98
    assert ctrl["pigeonhole_min_overlap_for_candidate_size"] > 0.70

    corridor = np.zeros((H, W), dtype=bool)
    corridor[:, 30] = True
    comp = novelty.classify_space_filling_control(fp, corridor, candidate_dot_count=40)
    assert comp["is_space_filling_calibration_control"] is False
    assert comp["footprint_3px_coverage"] < 0.20

    lat_path = tmp_path / "lattice.tif"
    cor_path = tmp_path / "corridor.tif"
    transform = rasterio.Affine(100.0, 0.0, 0.0, 0.0, -100.0, 6000.0)
    profile = {
        "driver": "GTiff",
        "height": H,
        "width": W,
        "count": 1,
        "dtype": "float32",
        "crs": "EPSG:32611",
        "transform": transform,
    }
    for path, arr in (
        (lat_path, lattice.astype(np.float32)),
        (cor_path, corridor.astype(np.float32)),
    ):
        with rasterio.open(path, "w", **profile) as ds:
            ds.write(arr, 1)

    import hashlib

    lat_sha = hashlib.sha256(
        np.asarray(lattice.astype(np.float32)[fp], dtype="<f4").tobytes()
    ).hexdigest()
    cor_sha = hashlib.sha256(
        np.asarray(corridor.astype(np.float32)[fp], dtype="<f4").tobytes()
    ).hexdigest()
    entries = [
        {
            "id": "reg-lat",
            "cache_path": "lattice.tif",
            "file": "lattice.tif",
            "footprint_sha256": lat_sha,
        },
        {
            "id": "reg-cor",
            "cache_path": "corridor.tif",
            "file": "corridor.tif",
            "footprint_sha256": cor_sha,
        },
    ]

    cand = np.zeros((H, W), dtype=np.float32)
    cand[5:55:4, 10] = 1.0
    rep = novelty.compare_registry(
        cand,
        fp,
        entries,
        tmp_path,
        dots=cand > 0.5,
        separate_calibration_controls=True,
    )
    assert rep["registry_unique_rasters"] == 2
    assert rep["competing_method_rasters"] == 1
    assert rep["calibration_control_rasters"] == 1
    assert rep["competing_method_passed"] is True
    assert rep["literal_unseparated_passed"] is False
    assert rep["passed"] is True
    assert len(rep["rows"]) == 2


def test_paired_segment_holdout_zero_and_positive_gain():
    H, W = 240, 240
    fp = np.ones((H, W), dtype=bool)
    labels = np.zeros((H, W), dtype=bool)
    labels[20:80, 40] = True
    labels[20:80, 180] = True
    labels[150:210, 40] = True
    labels[150:210, 180] = True
    ev = holdout.SegmentHoldout(fp, labels, buffer_px=5)

    base = np.zeros((H, W), dtype=np.float32)
    base[25:75:4, 40] = 1.0
    better = base.copy()
    better[25:75:4, 180] = 1.0
    better[155:205:4, 40] = 1.0
    better[155:205:4, 180] = 1.0

    same = ev.compare_paired([base] * 4, [base] * 4, ci_draws=99, seed=7)
    assert same["paired_delta_dti"] == pytest.approx(0.0, abs=1e-12)
    assert same["paired_delta_ci95"] == [0.0, 0.0]

    gain = ev.compare_paired([better] * 4, [base] * 4, ci_draws=99, seed=7)
    assert gain["paired_delta_dti"] > 0.10
    assert gain["ci95_strictly_positive"] is True
    assert gain["fold_wins"] >= 3


def test_oriented_lineament_and_submodular_allocator():
    H, W = 64, 64
    fp = np.ones((H, W), dtype=bool)
    _, xx = np.meshgrid(
        np.arange(H, dtype=np.float32), np.arange(W, dtype=np.float32), indexing="ij"
    )
    ridge = np.exp(-0.5 * ((xx - 32.0) / 1.5) ** 2).astype(np.float32)
    rmax = gvc.oriented_lineament_response(ridge, fp)
    assert rmax.shape == (H, W) and np.isfinite(rmax).all()
    assert float(rmax[:, 32].mean()) > float(rmax[:, 10].mean())

    vis = np.zeros((H, W), dtype=bool)
    vis[30:35, 32] = True
    dots = gvc.submodular_dti_allocate(
        ridge,
        fp,
        vis,
        budget=12,
        min_spacing_px=3.0,
        catalogue_clearance_px=3.0,
    )
    assert dots.dtype == np.float32
    assert set(np.unique(dots)).issubset({0.0, 1.0})
    assert int((dots > 0.5).sum()) <= 12
    edt = distance_transform_edt(~vis)
    assert float(edt[dots > 0.5].min()) >= 3.0 - 1e-5


def test_gvc1_recorded_artifacts_and_fail_closed_verdict():
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/evaluate_holdout.py"), "--verify-gvc1"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    summary = json.loads(proc.stdout)
    assert summary["verified"] is True
    assert summary["verdict"] == "negative"
    assert summary["ok_to_download"] is True
    assert summary["ok_to_submit"] is False
    assert summary["all_technical_gates_passed"] is False
    assert summary["holdout_dti"] > summary["b0_dti"] > summary["b1_dti"]

    card = json.loads((ROOT / "evidence/gvc1_run_card_20261025.json").read_text())
    assert 0 < len(card["note"]) <= 140
    assert card["submission_slots_used"] == 0
    assert card["organizer_confirmed_score"] is None
    assert card["c2st_nuisance_audit"]["labels_audited_first"] is True
    assert card["c2st_nuisance_audit"]["strict_c2st_gate_passed"] is True
    assert card["technical_gates"]["leakage_canary_passed"] is True
    assert card["technical_gates"]["beats_matched_allocator_oof_base_B1_ci95_gt_0"] is True
    assert card["technical_gates"]["competing_method_uniqueness_47_rasters_passed"] is False

    template = ROOT / "data/bridge/sample_submission.tif"
    z_path = ROOT / "docs/downloads" / card["submission_name"]
    n_path = ROOT / "docs/downloads" / card["nan_submission_name"]
    zip_path = ROOT / "docs/downloads" / card["zip_submission_name"]
    z_chk = submission.check_variants(z_path, template)
    n_chk = submission.check_variants(n_path, template)
    assert z_chk["format_valid"] is True and z_chk["format_acceptable"] is True
    assert n_chk["format_valid"] is True and n_chk["format_acceptable"] is True
    with rasterio.open(template) as ds:
        fp = np.isfinite(ds.read(1))
    with rasterio.open(z_path) as dz, rasterio.open(n_path) as dn:
        az, an = dz.read(1), dn.read(1)
    assert np.isfinite(az).all()
    assert np.all(az[~fp] == 0.0)
    assert np.isnan(an[~fp]).all()
    assert float(az.min()) >= 0.0 and float(az.max()) <= 1.0
    assert np.array_equal(az[fp], an[fp])
    with zipfile.ZipFile(zip_path) as zf:
        assert zf.namelist() == [card["nan_submission_name"]]


def test_historical_packet_retains_gvc1_and_tamper_fails_site_build(tmp_path):
    dl = json.loads((ROOT / "docs/data/gvc1_download.json").read_text())
    for rel in ("index.html", "docs/index.html", "docs/executive-summary.html"):
        html = (ROOT / rel).read_text()
        first_screen = html.split('id="historical-', 1)[1]
        assert dl["file"] in first_screen
        assert "NOT OK TO SUBMIT" in first_screen
        assert "DO NOT SUBMIT" in first_screen

    readme = (ROOT / "README.md").read_text()
    assert dl["file"] in readme
    assert "knowledge/owner_brief_2026-10-25.md" in readme
    assert "GEMSDOE32" in readme and "PARALLEL-RUN PROTOCOL" in readme

    for item in ("docs", "evidence", "registry", "scripts", "src", "knowledge"):
        shutil.copytree(ROOT / item, tmp_path / item)
    (tmp_path / "data/bridge").mkdir(parents=True)
    shutil.copy2(
        ROOT / "data/bridge/sample_submission.tif",
        tmp_path / "data/bridge/sample_submission.tif",
    )
    shutil.copy2(ROOT / "README.md", tmp_path / "README.md")
    target = tmp_path / "docs/downloads" / dl["file"]
    raw = bytearray(target.read_bytes())
    raw[-1] ^= 0xFF
    target.write_bytes(bytes(raw))
    proc = subprocess.run(
        [sys.executable, str(tmp_path / "scripts/build_site.py")],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert proc.returncode != 0
