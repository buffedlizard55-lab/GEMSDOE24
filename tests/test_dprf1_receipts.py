"""Unit, exact-file receipt, 9-site executive-summary, and tamper tests for H24-DPRF1."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

from gems import dprf1, footprint, selector
from gems.preflight import concise_status, preflight
from gems.validator import sha256_file

ROOT = Path(__file__).resolve().parents[1]
CARD_PATH = ROOT / "evidence/dprf1_run_card_20261026.json"
EXP_PATH = ROOT / "evidence/dprf1_experiment_20261026.json"
SEL_PATH = ROOT / "evidence/dprf1_selector_20261026.json"
DL_PATH = ROOT / "docs/data/dprf1_download.json"
NINE_SITE_PATH = ROOT / "evidence/nine_site_executive_summary_20261026.json"
TEMPLATE = ROOT / "data/bridge/sample_submission.tif"
TEMPLATE_SHA = "2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc"


def test_dprf1_operators_preserve_nan_and_cure_apron_inflation():
    rng = np.random.default_rng(123)
    h, w = 80, 80
    fp = np.ones((h, w), dtype=bool)
    vis = np.zeros((h, w), dtype=bool)
    vis[20:60, 20] = True

    p = rng.uniform(0.05, 0.25, size=(h, w)).astype(np.float32)
    p[15:65, 55] = 0.85
    ps = dprf1.sharpen_ridge_coherence(p, fp)
    assert ps.shape == (h, w) and np.isfinite(ps).all()
    assert float(ps[40, 55]) > float(p[40, 55])

    # Inflate 3-7 px apron around vis and verify debiased_apron_surface caps it
    p_inf = p.copy()
    p_inf[20:60, 23:28] = 0.99
    deb = dprf1.debiased_apron_surface(p_inf, fp, vis)
    assert float(deb[40, 25]) < 0.99

    dots = dprf1.two_regime_submodular_allocate(
        ps,
        (ps * 0.7).astype(np.float32),
        fp,
        vis,
        budget=40,
        primary_share=0.68,
        min_spacing_px=2.8,
        catalogue_clearance_px=2.0,
    )
    assert int((dots > 0.5).sum()) == 40
    assert set(np.unique(dots)).issubset({0.0, 1.0})
    d_vis = distance_transform_edt(~vis)
    assert float(d_vis[dots > 0.5].min()) > 2.0

    # Selective residualizer leaves non-selected columns untouched and preserves NaN
    x = rng.normal(size=(600, 12)).astype(np.float32)
    x[:100, 0] = np.nan
    x[:80, 5] = np.nan
    c = np.column_stack(
        [rng.uniform(0, 8, size=(600, 2)), np.eye(4)[rng.integers(0, 4, size=600)]]
    ).astype(np.float32)
    res = dprf1.SelectiveNonTopographicResidualizer([0, 2]).fit(c, x)
    x_out = res.transform_inplace(c, x.copy())
    assert np.isnan(x_out[:100, 0]).all()
    assert np.array_equal(x_out[:, 1], x[:, 1])
    assert np.isnan(x_out[:80, 5]).all()


def test_dprf1_recorded_artifacts_verify_and_refuse_implicit_rerun():
    res = subprocess.run(
        [sys.executable, "scripts/run_dprf1_lane.py", "--verify-recorded"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(res.stdout)
    assert payload["verified"] is True
    assert payload["experiment_rerun"] is False
    assert payload["verdict"] == "negative"
    assert payload["ok_to_submit"] is False
    assert payload["selector_decision"] == "DO_NOT_SUBMIT"
    assert payload["competing_method_novelty_passed"] is True
    assert payload["competing_method_max_3px_overlap"] <= 0.70
    assert payload["c2st_auc"] < 0.55
    assert payload["farfield_gt20px_fraction"] >= 0.45
    assert payload["holdout_dti"] > payload["single_regime_dti"] > payload["deadzone9_dti"] > 0.15

    # Refuses implicit rerun
    rerun = subprocess.run(
        [sys.executable, "scripts/run_dprf1_lane.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert rerun.returncode != 0 and "already recorded" in rerun.stderr

    card = json.loads(CARD_PATH.read_text())
    exp = json.loads(EXP_PATH.read_text())
    saved_sel = json.loads(SEL_PATH.read_text())
    dl = json.loads(DL_PATH.read_text())
    assert card["technical_promotion_gates_passed"] is True
    assert all(card["technical_gates"].values())
    assert card["submission_slots_used"] == 0
    assert card["organizer_confirmed_score"] is None
    assert 0 < len(card["note"]) <= 140
    assert card["correlation_overlap_vs_registry"]["competing_method_rasters_checked"] == 57

    zeros = ROOT / "docs/downloads" / card["submission_name"]
    nan_p = ROOT / "docs/downloads" / card["nan_outside_artifact"]
    zip_p = ROOT / "docs/downloads" / card["zip_artifact"]
    assert sha256_file(zeros) == card["raster_sha256"] == dl["sha256"]
    assert sha256_file(nan_p) == card["nan_outside_sha256"] == dl["nan_sha256"]
    assert sha256_file(zip_p) == card["zip_sha256"] == dl["zip_sha256"]

    fresh_sel = selector.verify_selector(zeros, TEMPLATE, card)
    assert fresh_sel["ok_to_submit"] is False
    assert fresh_sel["decision"] == "DO_NOT_SUBMIT"
    assert fresh_sel["human_inspection_used"] is False
    assert fresh_sel["gates"] == saved_sel["gates"]

    fp = footprint.load_footprint()
    with rasterio.open(zeros) as dz, rasterio.open(nan_p) as dn:
        az, an = dz.read(1), dn.read(1)
        assert dz.count == 1 and dz.dtypes == ("float32",)
        assert dz.shape == (3730, 3292) and str(dz.crs) == "EPSG:32611"
        assert np.isfinite(az).all()
        assert float(az.min()) >= 0.0 and float(az.max()) <= 1.0
        assert float(az[~fp].max()) == 0.0
        assert int((az[fp] > 0.5).sum()) == 37654
        assert np.isnan(an[~fp]).all()
        assert np.array_equal(az[fp], an[fp])

    with zipfile.ZipFile(zip_p) as zf:
        assert zf.namelist() == [zeros.name]
        assert hashlib.sha256(zf.read(zeros.name)).hexdigest() == card["raster_sha256"]

    pf = preflight(zeros, TEMPLATE, run_card_path=CARD_PATH, expected_template_sha256=TEMPLATE_SHA)
    assert pf["format_validation"]["format_valid"] is True
    assert pf["portal_range_diagnostic"]["strict_whole_array_values_in_0_1"] is True
    assert pf["decision"]["submission_status"] == "DO_NOT_SUBMIT"
    assert pf["decision"]["ready_to_submit"] is False
    assert "SUBMISSION: DO_NOT_SUBMIT" in concise_status(pf)
    assert exp["run_card"]["raster_sha256"] == card["raster_sha256"]


def test_nine_site_executive_summary_and_first_screen_order(tmp_path):
    nine = json.loads(NINE_SITE_PATH.read_text())
    expected_sites = [
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
    assert [r["site"] for r in nine["sites"]] == expected_sites
    for r in nine["sites"]:
        assert len(r["inspected_main_commit"]) == 40
        assert len(r["inspected_artifact_sha256"]) == 64
        if r["site"] != "GEMSDOE24":
            assert r["dprf1_3px_overlap_vs_site_artifact"] <= 0.70

    dl = json.loads(DL_PATH.read_text())
    gvc_dl = json.loads((ROOT / "docs/data/gvc1_download.json").read_text())
    rshg_dl = json.loads((ROOT / "docs/data/rshg1_download.json").read_text())

    for rel in (
        "index.html",
        "executive-summary.html",
        "docs/index.html",
        "docs/executive-summary.html",
    ):
        html = (ROOT / rel).read_text()
        assert f'download="{dl["file"]}"' in html
        assert html.index(dl["file"]) < html.index(gvc_dl["file"]) < html.index(rshg_dl["file"])
        for s in expected_sites:
            assert s in html
        assert "Nine-Site Executive Summary" in html

    readme = (ROOT / "README.md").read_text()
    assert dl["file"] in readme
    for s in expected_sites:
        assert s in readme

    # Verify tampering with DPRF1 run card fails site build closed
    site = tmp_path / "repo"
    for rel in ("scripts", "src", "docs", "evidence", "registry", "data/bridge", "README.md"):
        src = ROOT / rel
        dst = site / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)
    card_p = site / "evidence/dprf1_run_card_20261026.json"
    bad = json.loads(card_p.read_text())
    bad["raster_sha256"] = "0" * 64
    card_p.write_text(json.dumps(bad))
    proc = subprocess.run(
        [sys.executable, str(site / "scripts/build_site.py")],
        cwd=site,
        capture_output=True,
        text=True,
    )
    assert proc.returncode != 0
    assert "DPRF1 checksum" in proc.stderr
