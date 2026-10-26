"""Exact-file, preflight, and site-ordering invariants for H24-RSHG1."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import rasterio

from gems import footprint
from gems.preflight import concise_status, preflight
from gems.validator import sha256_file

ROOT = Path(__file__).resolve().parents[1]
CARD_PATH = ROOT / "evidence/rshg1_run_card_20261025.json"
EXP_PATH = ROOT / "evidence/rshg1_experiment_20261025.json"
DL_PATH = ROOT / "docs/data/rshg1_download.json"
TEMPLATE = ROOT / "data/bridge/sample_submission.tif"
TEMPLATE_SHA = "2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc"


def test_rshg1_artifacts_are_hash_bound_strict_range_and_fail_closed():
    card = json.loads(CARD_PATH.read_text())
    exp = json.loads(EXP_PATH.read_text())
    dl = json.loads(DL_PATH.read_text())

    zeros = ROOT / "docs/downloads" / dl["file"]
    nan = ROOT / "docs/downloads" / dl["nan_file"]
    assert zeros.exists() and nan.exists()
    assert sha256_file(zeros) == dl["sha256"] == card["raster_sha256"]
    assert sha256_file(nan) == dl["nan_sha256"] == card["nan_outside_sha256"]
    published_rshg1 = json.loads((ROOT / "docs/data/rshg1_run_card.json").read_text())
    active = json.loads((ROOT / "docs/data/active_lane.json").read_text())
    assert published_rshg1["submission_name"] == dl["file"]
    assert published_rshg1["raster_sha256"] == dl["sha256"]
    assert active["ok_to_submit"] is False
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

    with rasterio.open(nan) as ds_nan:
        arr_nan = ds_nan.read(1)
        assert np.isfinite(arr_nan[fp]).all()
        assert np.isnan(arr_nan[~fp]).all()
        assert np.array_equal(arr_nan[fp], arr[fp])

    assert card["verdict"] == exp["run_card"]["verdict"] == "negative"
    assert exp["ok_to_submit"] is False
    assert card["ok_to_submit"] is False and card["ok_to_download"] is True
    assert card["leakage_canary"]["passed"] is True
    assert card["exact_file_nuisance_audit"]["strict_gate_passed"] is True
    assert card["exact_file_nuisance_audit"]["observed_auc"] < 0.5223
    assert card["min_distance_to_public_catalogue_px"] > 2.0

    report = preflight(
        zeros,
        TEMPLATE,
        run_card_path=CARD_PATH,
        expected_template_sha256=TEMPLATE_SHA,
    )
    assert report["format_validation"]["format_valid"] is True
    assert report["portal_range_diagnostic"]["strict_whole_array_values_in_0_1"] is True
    assert report["run_card"]["scientific_authorization"] is False
    assert report["decision"]["submission_status"] == "DO_NOT_SUBMIT"
    assert report["decision"]["ready_to_submit"] is False
    assert "SUBMISSION: DO_NOT_SUBMIT" in concise_status(report)


def test_rshg1_verify_recorded_succeeds_without_rerun():
    res = subprocess.run(
        [sys.executable, "scripts/run_rshg1_lane.py", "--verify-recorded"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, res.stderr
    payload = json.loads(res.stdout)
    assert payload["verified"] is True
    assert payload["experiment_rerun"] is False
    assert payload["ok_to_submit"] is False


def test_rshg1_is_retained_and_preserves_all_sibling_packets():
    dl = json.loads(DL_PATH.read_text())
    mtr = json.loads((ROOT / "docs/data/independent_download.json").read_text())
    sahg = json.loads((ROOT / "docs/data/sahg1_download.json").read_text())
    con = json.loads((ROOT / "evidence/con_run_card_20261025.json").read_text())

    for rel in ("index.html", "docs/index.html", "docs/executive-summary.html"):
        html = (ROOT / rel).read_text()
        assert f'download="{dl["file"]}"' in html
        assert "NOT OK TO SUBMIT" in html and "DO_NOT_SUBMIT" in html
        assert html.index(dl["file"]) < html.index(mtr["file"])
        assert html.index(dl["file"]) < html.index(sahg["file"])
        assert con["submission_name"] in html
        assert html.index('id="historical-') < html.index(dl["file"])


def test_site_build_rejects_rshg1_checksum_or_preflight_tampering(tmp_path):
    for name in ("docs", "evidence", "registry", "scripts", "src", "knowledge"):
        shutil.copytree(
            ROOT / name,
            tmp_path / name,
            ignore=shutil.ignore_patterns("__pycache__", "archive", "*.pyc"),
        )
    (tmp_path / "data/external/audit_sources").mkdir(parents=True)
    shutil.copy(
        ROOT / "data/external/audit_sources/acquisition_blocks_receipt.json",
        tmp_path / "data/external/audit_sources/acquisition_blocks_receipt.json",
    )
    (tmp_path / "data/bridge").mkdir(parents=True)
    shutil.copy(TEMPLATE, tmp_path / "data/bridge/sample_submission.tif")
    shutil.copy(ROOT / "README.md", tmp_path / "README.md")

    card_p = tmp_path / "evidence/rshg1_run_card_20261025.json"
    orig_card = card_p.read_text()
    try:
        bad = json.loads(orig_card)
        bad["raster_sha256"] = "f" * 64
        card_p.write_text(json.dumps(bad))
        res = subprocess.run(
            [sys.executable, "scripts/build_site.py"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
        )
        assert res.returncode != 0 and "RSHG1 checksum" in res.stderr
    finally:
        card_p.write_text(orig_card)

    dl = json.loads(DL_PATH.read_text())
    pf_p = (tmp_path / "docs/downloads" / dl["file"]).with_suffix(".preflight.json")
    orig_pf = pf_p.read_text()
    try:
        bad_pf = json.loads(orig_pf)
        bad_pf["decision"]["ready_to_submit"] = True
        bad_pf["decision"]["submission_status"] = "OK_TO_SUBMIT"
        pf_p.write_text(json.dumps(bad_pf))
        res = subprocess.run(
            [sys.executable, "scripts/build_site.py"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
        )
        assert res.returncode != 0 and "RSHG1 exact-file preflight" in res.stderr
    finally:
        pf_p.write_text(orig_pf)
