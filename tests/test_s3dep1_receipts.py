"""Unit, exact-file receipt, preregistration-ancestry, 9-site, and tamper tests for H24-S3DEP1."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

from gems import s3dep1, selector
from gems.benchmarks import recorded_point_best, recorded_points

ROOT = Path(__file__).resolve().parents[1]
CARD_PATH = ROOT / "evidence/s3dep1_run_card_20261026.json"
EXP_PATH = ROOT / "evidence/s3dep1_experiment_20261026.json"
SEL_PATH = ROOT / "evidence/s3dep1_selector_20261026.json"
DL_PATH = ROOT / "docs/data/s3dep1_download.json"
NINE_PATH = ROOT / "evidence/nine_site_executive_summary_s3dep1_20261026.json"


def test_s3dep1_zero_1m_lidar_and_operators_preserve_footprint_nan():
    assert len(s3dep1.S3DEP1_NAMES) == 61
    assert not (set(s3dep1.S3DEP1_NAMES) & s3dep1.FORBIDDEN_1M_LIDAR_NAMES)
    assert len(s3dep1.FORBIDDEN_1M_LIDAR_NAMES) == 15

    rng = np.random.default_rng(20261026)
    shape = (40, 44)
    fp = np.zeros(shape, dtype=bool)
    fp[4:36, 4:40] = True

    def mk(lo: float = 0.0, hi: float = 1.0) -> np.ndarray:
        arr = rng.uniform(lo, hi, size=shape).astype(np.float32)
        arr[~fp] = np.nan
        return arr

    # Synthetic monoclinal scarp across row 20 vs symmetric ditch across row 10
    o1 = mk(0.2, 0.8)
    o3 = mk(0.2, 0.8)
    hgm50 = mk(0.05, 0.5)
    curv = mk(0.001, 0.02)
    o1[20, 8:36] = 0.98
    o3[20, 8:36] = 0.98
    hgm50[20, 8:36] = 2.5
    curv[20, 8:36] = 0.002

    o1[10, 8:36] = 0.05
    o3[10, 8:36] = 0.05
    hgm50[10, 8:36] = 2.5
    curv[10, 8:36] = 0.25

    derived = s3dep1.compute_s3dep1_derived_channels(
        dem10_onesided=o1,
        dem10_onesided3=o3,
        dem10_hgm50_max=hgm50,
        dem10_hgm200_mean=mk(0.02, 0.3),
        dem10_steep_ratio_max=mk(0.5, 4.0),
        dem10_slope_mean=mk(0.01, 0.2),
        dem10_curv_absmax=curv,
        iso_grav_anom_slope=mk(0.1, 2.0),
        depth_to_base_surf=mk(100.0, 900.0),
        geod_2ndinv=mk(10.0, 80.0),
        geod_shearrate=mk(5.0, 60.0),
        eq_deq_log1p=mk(0.0, 2.5),
        eq_ieq_log1p=mk(0.0, 2.0),
        footprint=fp,
    )
    assert set(derived) == set(s3dep1.S3DEP1_DERIVED6_NAMES)
    for arr in derived.values():
        assert arr.shape == shape and arr.dtype == np.float32
        assert np.isnan(arr[~fp]).all()
        assert np.isfinite(arr[fp]).all()
    assert float(np.mean(derived["s3dep_scarp_over_incision"][20, 10:34])) > float(
        np.mean(derived["s3dep_scarp_over_incision"][10, 10:34])
    )

    # Unconditional nuisance logit calibrator removes marginal nuisance drift
    n_rows = 400
    nuis = rng.uniform(0.0, 5000.0, size=(n_rows, 6)).astype(np.float32)
    nuis[:, 2:] = (nuis[:, 2:] > 2500.0).astype(np.float32)
    raw_p = 1.0 / (1.0 + np.exp(-(0.8 * (nuis[:, 0] / 5000.0) - 1.5)))
    cal = s3dep1.UnconditionalNuisanceLogitCalibrator(alpha=10.0).fit(raw_p, nuis)
    deb_p = cal.transform(raw_p, nuis)
    assert deb_p.dtype == np.float32
    assert np.all((deb_p >= 0.0) & (deb_p <= 1.0))
    corr_before = abs(np.corrcoef(raw_p, nuis[:, 0])[0, 1])
    corr_after = abs(np.corrcoef(deb_p, nuis[:, 0])[0, 1])
    assert corr_after < corr_before


def test_s3dep1_recorded_artifacts_verify_and_refuse_implicit_rerun():
    proc = subprocess.run(
        [sys.executable, "scripts/run_s3dep1_lane.py", "--verify-recorded"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    receipt = json.loads(proc.stdout)
    assert receipt["verified"] is True
    assert receipt["lane_id"] == "H24-S3DEP1"
    assert receipt["selector_decision"] == "DO_NOT_SUBMIT"
    assert receipt["ok_to_submit"] is False
    assert receipt["verdict"] == "negative"

    refuse = subprocess.run(
        [sys.executable, "scripts/run_s3dep1_lane.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert refuse.returncode != 0
    assert "refusing implicit rerun" in refuse.stderr.lower()


def test_s3dep1_preregistration_ancestry_and_new_point_best_benchmark():
    card = json.loads(CARD_PATH.read_text())
    exp = json.loads(EXP_PATH.read_text())
    sel = json.loads(SEL_PATH.read_text())
    dl = json.loads(DL_PATH.read_text())

    prereg_sha = card["preregistration_commit"]
    assert prereg_sha == "7e6db4d428aea6c26a769feed71f4de04f50f613"
    assert (ROOT / card["preregistration"]).is_file()
    subprocess.run(
        ["git", "merge-base", "--is-ancestor", prereg_sha, "HEAD"],
        cwd=ROOT,
        check=True,
    )

    assert card["experiments_run"] == card["experiment_budget_limit"] == 3
    assert card["verdict"] == "negative"
    assert card["ok_to_download"] is True
    assert card["ok_to_submit"] is False
    assert sel["decision"] == "DO_NOT_SUBMIT"
    assert sel["gates"]["g1_format_strict_0_1"] is True
    assert sel["gates"]["g2_leakage_canary"] is True
    assert sel["gates"]["g4_registry_novelty"] is False
    assert sel["gates"]["g5_exact_file_c2st"] is False

    # S3DEP1 achieves a new all-time recorded HOLDOUT-DTI point-best (> DPRF1 0.16379)
    assert card["holdout"]["dti"] > 0.1660
    assert card["holdout"]["dti"] > card["arms_same_evaluator"]["control_dprf1_52ch_replay"]["dti"]
    assert card["paired_vs_oof_multiphysics_hgb_d3"]["ci95_strictly_positive"] is True
    assert card["paired_vs_oof_multiphysics_hgb_d3"]["fold_wins"] == 4

    # Breaks DPRF1 parent convergence (<=70%) and all 8 sibling sites, flagged vs DKRN1 (>70%)
    nov = card["correlation_overlap_vs_registry"]
    assert nov["dot_overlap_within_3px_vs_dprf1"] <= 0.70
    assert nov["dot_overlap_within_3px_vs_gemsdoe32_b2"] <= 0.70
    assert nov["peer_blobs_passed"] is True
    assert nov["nine_site_20261026_passed"] is True
    assert nov["dot_overlap_within_3px_vs_dkrn1"] > 0.70

    best = recorded_point_best(ROOT)
    assert best["lane"] == "S3DEP1"
    assert best["holdout"]["dti"] == card["holdout"]["dti"]
    assert {"S3DEP1", "DPRF1", "DKRN1", "TRSG1"} <= {r["lane"] for r in recorded_points(ROOT)}
    assert len(dl["note"]) <= 140
    assert exp["ok_to_submit"] is False


def test_s3dep1_nine_site_20261026_forensics_and_site_tamper_guard(tmp_path):
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
    for sname in expected[1:]:
        assert by_site[sname]["s3dep1_3px_overlap_vs_site_artifact"] <= 0.70

    s3_dl = json.loads(DL_PATH.read_text())
    dprf_dl = json.loads((ROOT / "docs/data/dprf1_download.json").read_text())
    dkrn_dl = json.loads((ROOT / "docs/data/dkrn1_download.json").read_text())
    for page in (
        "index.html",
        "docs/index.html",
        "executive-summary.html",
        "docs/executive-summary.html",
    ):
        html = (ROOT / page).read_text()
        assert html.index(s3_dl["file"]) < html.index(dprf_dl["file"]) < html.index(dkrn_dl["file"])

    readme = (ROOT / "README.md").read_text()
    assert readme.index("H24-S3DEP1") < readme.index("H24-DPRF1") < readme.index(dkrn_dl["file"])

    # Independent selector confirms DO_NOT_SUBMIT on exact GeoTIFF bytes
    fresh_sel = selector.verify_selector(
        ROOT / "docs/downloads" / s3_dl["file"],
        ROOT / "data/bridge/sample_submission.tif",
        json.loads(CARD_PATH.read_text()),
    )
    assert fresh_sel["decision"] == "DO_NOT_SUBMIT" and fresh_sel["ok_to_submit"] is False

    # Tampering with S3DEP1 run card SHA-256 fails build_site.py closed
    site = tmp_path / "repo"
    site.mkdir()
    for rel in ("scripts", "src", "registry", "evidence", "docs", "knowledge"):
        shutil.copytree(ROOT / rel, site / rel)
    (site / "data/bridge").mkdir(parents=True)
    shutil.copy2(
        ROOT / "data/bridge/sample_submission.tif",
        site / "data/bridge/sample_submission.tif",
    )
    shutil.copy2(ROOT / "README.md", site / "README.md")
    card_copy = site / "evidence/s3dep1_run_card_20261026.json"
    tampered = json.loads(card_copy.read_text())
    tampered["raster_sha256"] = "f" * 64
    card_copy.write_text(json.dumps(tampered))
    proc = subprocess.run(
        [sys.executable, "scripts/build_site.py"],
        cwd=site,
        capture_output=True,
        text=True,
    )
    assert proc.returncode != 0
    assert "S3DEP1 checksum" in proc.stderr or "Current-best raster checksum" in proc.stderr
