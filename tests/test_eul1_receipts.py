"""Exact-file receipt, replay, nine-site, and fail-closed tests for H24-EUL1 (negative)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CARD = ROOT / "evidence/eul1_run_card_20261026.json"
DL = ROOT / "docs/data/eul1_download.json"
NINE = ROOT / "evidence/nine_site_executive_summary_eul1_20261026.json"
NINE_OLD = ROOT / "evidence/nine_site_executive_summary_20261026.json"


def test_eul1_verify_recorded_passes():
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/run_eul1_lane.py"), "--verify-recorded"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    out = json.loads(proc.stdout)
    assert out["verified"] is True
    assert out["verdict"] == "negative"
    assert out["ok_to_submit"] is False
    assert out["selector_decision"] == "DO_NOT_SUBMIT"


def test_eul1_implicit_rerun_refused():
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/run_eul1_lane.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode != 0
    assert "already recorded and frozen" in proc.stdout + proc.stderr


def test_eul1_negative_head_to_head_against_bit_identical_dprf1_replay():
    card = json.loads(CARD.read_text())
    dl = json.loads(DL.read_text())
    assert card["verdict"] == "negative"
    assert card["ok_to_submit"] is False and dl["ok_to_submit"] is False
    assert card["holdout"]["evaluator_version"] == "gems-segment-pooled-v1"
    assert card["holdout"]["n_withheld_positive_pixels"] == 60988
    cmp_rec = card["recorded_point_best_comparison"]
    # The no-Euler arm reproduced recorded DPRF1 exactly: this is a true head-to-head.
    assert cmp_rec["arm2_replay_bit_identical_to_recorded"] is True
    assert cmp_rec["arm2_replay_dti"] == cmp_rec["recorded_best_dti"] == 0.1637924246971501
    assert cmp_rec["candidate_beats_recorded_point"] is False
    pr = card["paired_comparisons"]["arm1_vs_arm2_noeuler_replay"]
    assert pr["ci95_strictly_positive"] is False
    assert pr["fold_wins"] <= 1
    assert card["paired_comparisons"]["arm3_vs_arm2_channel_effect"]["fold_wins"] == 0
    # Rule-1 duplicate against the DPRF1 parent (>70% of dots within 3 px).
    nov = card["correlation_overlap_vs_registry"]
    assert nov["dot_overlap_within_3px_vs_dprf1"] > 0.70
    assert nov["method_lane_passed"] is False
    # Format strictness held even though the lane is negative.
    v = card["validator_output"]
    assert v["no_nan_in_footprint"] is True
    assert v["footprint_range_0_1"] is True
    assert v["positive_pixels"] == 37654
    assert len(card["note"]) <= 140
    assert card["organizer_confirmed_score"] is None


def test_eul1_nine_site_update_and_first_screen_order():
    nine = json.loads(NINE.read_text())
    old = json.loads(NINE_OLD.read_text())
    expected = [
        "GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30",
        "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36",
    ]
    assert [r["site"] for r in nine["sites"]] == expected
    # Every site artifact was re-fetched and SHA-verified against the earlier receipt.
    old_by_site = {r["site"]: r for r in old["sites"]}
    for r in nine["sites"]:
        assert r["inspected_artifact_sha256"] == old_by_site[r["site"]]["inspected_artifact_sha256"]
        assert r["eul1_3px_overlap_vs_site_artifact"] is not None
        if r["site"] != "GEMSDOE24":
            assert r["eul1_3px_overlap_vs_site_artifact"] <= 0.70
    g24 = nine["sites"][0]
    assert g24["latest_eul1_20261026"]["verdict"] == "negative"
    assert "DPRF1" in nine["cross_site_executive_conclusion"]["best_unscored_unique_candidate"]
    # The superseded receipt is untouched by the EUL1 session.
    assert "latest_eul1_20261026" not in json.dumps(old)

    card = json.loads(CARD.read_text())
    eul1_file = card["submission_name"]
    dprf1_dl = json.loads((ROOT / "docs/data/dprf1_download.json").read_text())
    for rel in ("index.html", "executive-summary.html", "docs/index.html", "docs/executive-summary.html"):
        html = (ROOT / rel).read_text()
        assert eul1_file in html
        # DPRF1 remains ahead of EUL1: it is still the best candidate.
        assert html.index(dprf1_dl["file"]) < html.index(eul1_file)
    readme = (ROOT / "README.md").read_text()
    assert eul1_file in readme
    assert readme.index("H24-DPRF1") < readme.index(eul1_file)
