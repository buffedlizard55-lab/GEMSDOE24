"""Receipt tests for the 2026-10-25 H24-FUSE stop (knowledge/17_FUSE_findings_2026-10-25.md).

These tests never rerun the experiment. They check that the recorded STOP is internally
consistent (no packaged TIFF, final all-dot overlap computed and over the limit) and that
its run card is a deterministic function of the record.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

EXPERIMENT = ROOT / "evidence/fuse_experiment_20261025.json"
CARD = ROOT / "evidence/fuse_run_card_20261025.json"


@pytest.mark.skipif(not EXPERIMENT.exists(), reason="FUSE experiment not recorded in this checkout")
def test_recorded_fuse_stop_is_fail_closed():
    rec = json.loads(EXPERIMENT.read_text())
    assert rec["stopped_reason"].startswith("duplicate-final-dots")
    assert rec["artifact"] is None, "a stopped duplicate must not package a downloadable TIF"
    assert rec["ok_to_submit"] is False and rec["ok_to_download"] is False
    assert rec["organizer_confirmed_score"] is None
    final = rec["final_novelty"]
    assert final["method_lane_passed"] is False
    assert final["method_lane_max_dot_overlap"] is not None, "final overlap must be computed"
    assert final["method_lane_max_dot_overlap"] > 0.70
    assert rec["peer_blob_novelty"]["passed"] is False


@pytest.mark.skipif(not EXPERIMENT.exists(), reason="FUSE experiment not recorded in this checkout")
def test_fuse_run_card_is_deterministic_function_of_record():
    import run_fuse_prereg as fuse

    rec = json.loads(EXPERIMENT.read_text())
    expected = fuse.build_card_from_record(rec)
    assert CARD.exists()
    assert json.loads(CARD.read_text()) == expected
    assert expected["verdict"] == "negative"
    assert expected["holdout"]["label"] == "HOLDOUT-DTI"
    assert expected["holdout"]["withheld_positives"] == 60988
    assert expected["raster_sha256"] is None and expected["submission_name"] is None


@pytest.mark.skipif(not EXPERIMENT.exists(), reason="FUSE experiment not recorded in this checkout")
def test_prereg_runner_refuses_to_rerun_a_recorded_experiment():
    import subprocess

    result = subprocess.run(
        [sys.executable, "scripts/run_fuse_prereg.py"], cwd=ROOT, capture_output=True, text=True
    )
    assert result.returncode != 0
    assert "already recorded" in result.stderr
