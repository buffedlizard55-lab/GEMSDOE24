"""Regression and receipt-integrity tests for the 2026-10-25 H24-FUSE packet."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

from gems.validator import sha256_file

ROOT = Path(__file__).resolve().parents[1]


def test_recorded_fuse_receipts_and_exact_files_verify() -> None:
    res = subprocess.run(
        [sys.executable, str(ROOT / "scripts/run_hcw_lane.py"), "--verify-recorded"],
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
    assert payload["method_lane_novelty_passed"] is True
    assert payload["literal_all_entries_passed"] is False
    assert payload["experiments_run"] == 3
    assert 0.120 < payload["holdout_dti"] < 0.128
    assert 0.128 < payload["fuse_raw_dti"] < 0.132
    assert 0.120 < payload["fuse_resid_dti"] < 0.126

    card = json.loads((ROOT / "evidence/hcw_run_card_20261025.json").read_text())
    dl = json.loads((ROOT / "docs/data/hcw_download.json").read_text())
    zero_path = ROOT / "docs/downloads" / card["submission_name"]
    nan_path = ROOT / "docs/downloads" / card["nan_outside_artifact"]

    assert sha256_file(zero_path) == card["raster_sha256"] == dl["sha256"]
    assert sha256_file(nan_path) == card["nan_outside_sha256"] == dl["nan_sha256"]
    assert len(card["note"]) <= 140
    assert card["ok_to_submit"] is False
    assert card["verdict"] == "negative"

    # Verify C2ST passed (< 0.55) on both residualized arms
    arms = card["arms_holdout_summary"]
    assert arms["fuse_resid"]["c2st_passed"] is True
    assert arms["fuse_resid"]["c2st_auc"] < 0.55
    assert arms["fuse_hcw"]["c2st_passed"] is True
    assert arms["fuse_hcw"]["c2st_auc"] < 0.55
    # And verify FUSE-RAW failed prospective method-lane novelty (> 0.70) while FUSE-RESID & FUSE-HCW passed
    assert arms["fuse_raw"]["method_lane_novelty_passed"] is False
    assert arms["fuse_raw"]["method_lane_max_overlap_within_3px"] > 0.70
    assert arms["fuse_resid"]["method_lane_novelty_passed"] is True
    assert arms["fuse_resid"]["method_lane_max_overlap_within_3px"] <= 0.70
    assert arms["fuse_hcw"]["method_lane_novelty_passed"] is True
    assert arms["fuse_hcw"]["method_lane_max_overlap_within_3px"] <= 0.70


def test_fuse_refuses_implicit_rerun() -> None:
    res = subprocess.run(
        [sys.executable, str(ROOT / "scripts/run_hcw_lane.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert res.returncode != 0
    assert "already recorded" in res.stderr


def test_fuse_is_on_first_screen_and_rejects_checksum_tampering(tmp_path: Path) -> None:
    dl = json.loads((ROOT / "docs/data/hcw_download.json").read_text())
    for page in (
        "index.html",
        "docs/index.html",
        "docs/executive-summary.html",
        "executive-summary.html",
    ):
        html = (ROOT / page).read_text()
        assert f'download="{dl["file"]}"' in html
        assert f'download="{dl["nan_file"]}"' in html
        assert "H24-FUSE-HCW" in html
        assert "DOWNLOAD: YES" in html and "SUBMIT: NO" in html
        if 'class="metrics"' in html:
            assert html.index(dl["file"]) < html.index('class="metrics"')

    # Verify tampering with FUSE run card fails site build
    site = tmp_path / "repo"
    for rel in ("scripts", "src", "docs", "evidence", "registry", "data/bridge", "README.md"):
        src = ROOT / rel
        dst = site / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)
    card_p = site / "evidence/hcw_run_card_20261025.json"
    card = json.loads(card_p.read_text())
    card["raster_sha256"] = "0" * 64
    card_p.write_text(json.dumps(card))
    proc = subprocess.run(
        [sys.executable, "scripts/build_site.py"],
        cwd=site,
        capture_output=True,
        text=True,
    )
    assert proc.returncode != 0
    assert "FUSE checksum" in proc.stderr


def test_con_novelty_backfilled() -> None:
    card = json.loads((ROOT / "evidence/con_run_card_20261025.json").read_text())
    nov = card["correlation_overlap_vs_registry"]
    assert nov["total_entries_checked"] >= 46
    assert nov["method_lane_passed"] is True
    assert nov["method_lane_max_dot_overlap"] <= 0.70
