"""The current audit is evidence-bound and cannot turn stopped lanes into uploads."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from audit_current_focus_files import validate_audit  # noqa: E402

from gems import selector  # noqa: E402
from gems.validator import sha256_file  # noqa: E402


def test_nine_current_files_have_hash_bound_negative_lattice_witnesses():
    report = validate_audit(
        json.loads((ROOT / "evidence/current_focus_nine_file_audit_20261027.json").read_text())
    )
    assert len(report["rows"]) == 9
    assert all(r["format_valid"] and r["strict_whole_array_finite_0_1"] for r in report["rows"])
    assert all(
        r["literal_lattice_duplicate"] and r["literal_lattice_overlap_within_3px"] > 0.70
        for r in report["rows"]
    )
    assert all(
        r["preplacement_surface_novelty"] is None and not r["ok_to_submit"] for r in report["rows"]
    )
    assert report["new_tiffs_generated_by_this_session"] == 0
    assert report["competition_slots_used"] == 0
    assert report["rows"][0]["holdout"]["label"] == "INVALID HOLDOUT"


def test_tampered_focus_report_cannot_certify_novelty_or_lose_a_site():
    original = json.loads(
        (ROOT / "evidence/current_focus_nine_file_audit_20261027.json").read_text()
    )
    for mutate in (
        lambda v: v["rows"].pop(),
        lambda v: v["rows"][0].update(ok_to_submit=True),
        lambda v: v["rows"][0].update(literal_lattice_duplicate=False),
        lambda v: v["rows"][0]["source_file"].update(sha256="0" * 64),
        lambda v: v["rows"][0]["source_file"].update(git_blob="0" * 40),
        lambda v: v["rows"][1]["holdout"].update(value=0.04),
        lambda v: v["rows"][1].update(literal_lattice_overlap_within_3px=0.8),
        lambda v: v.update(organizer_confirmed_scores=[0.2778]),
    ):
        invalid = copy.deepcopy(original)
        mutate(invalid)
        with pytest.raises(ValueError):
            validate_audit(invalid)


def test_concurrent_lanes_are_stopped_without_touching_their_original_tiffs():
    cards = (
        ("scripts/run_tmcg_lane.py", "evidence/tmcg_integrity_review_20261027.json"),
        ("scripts/build_unique_submission7.py", "evidence/unique07_integrity_review_20261027.json"),
    )
    for script, card_path in cards:
        card = json.loads((ROOT / card_path).read_text())
        raster = ROOT / "docs/downloads" / card["submission_name"]
        before = sha256_file(raster)
        blocked = subprocess.run([sys.executable, script], cwd=ROOT, capture_output=True, text=True)
        assert blocked.returncode != 0
        assert "stopped" in blocked.stderr.lower()
        assert sha256_file(raster) == before == card["raster_sha256"]
    retired = subprocess.run(
        [sys.executable, "scripts/patch_h24_07_reports.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert retired.returncode != 0 and "retired" in retired.stderr.lower()


def test_unique07_read_only_review_reproduces_leak_and_exact_duplicate():
    proc = subprocess.run(
        [sys.executable, "scripts/build_unique_submission7.py", "--verify-recorded"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    card = json.loads(proc.stdout)
    assert card["fold_leakage"]["detected"] is True
    assert card["recorded_holdout"]["status"].startswith("INVALID")
    assert card["correlation_overlap_vs_registry"]["rows"][0][
        "candidate_dot_overlap_within_3px"
    ] == pytest.approx(0.9977949283351709)
    assert card["ok_to_submit"] is False
    assert card["validator_output"]["format_valid"] is True


def test_selector_uses_pinned_external_point_floor_but_never_authorizes_it():
    assert selector.RECORDED_BEST_EVIDENCE["lane"] == "KPL-36"
    assert selector.RECORDED_BEST_DTI == pytest.approx(0.17010000946379217)
    assert selector.RECORDED_BEST_EVIDENCE["ok_to_submit"] is False
    assert "not independently replayed" in selector.RECORDED_BEST_EVIDENCE["scope"]


def test_pages_surface_current_review_and_quarantine():
    pages = (
        "index.html",
        "executive-summary.html",
        "docs/index.html",
        "docs/executive-summary.html",
    )
    for path in pages:
        html = (ROOT / path).read_text()
        assert "fold eligibility" in html and "withheld segments" in html
        assert "not a scientifically replayed or proven comparable winner" in html
        assert "Band-6 correction" in html
        if path == "docs/executive-summary.html":
            assert 'id="unique-submission"' in html
            assert 'href="executive-summary-unique.html#nine-site"' in html
        else:
            assert 'id="current-focus-files"' in html
            assert "all nine fail the literal 70% overlap rule" in html
