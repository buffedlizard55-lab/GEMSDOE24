"""Regression coverage for the evidence-led nine-site summary and GEO1 correction."""

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs/nine-site-submission-summary.html"
RUN_CARD = ROOT / "evidence/run_card_20261029_nine_site_unique.json"
AUDIT = ROOT / "evidence/geo1_holdout_leakage_audit_20261030.json"
SITES = [
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


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _report_module():
    spec = importlib.util.spec_from_file_location(
        "build_nine_site_report", ROOT / "scripts/build_nine_site_report.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_all_nine_sites_have_downloads_and_no_leaderboard_estimate():
    text = REPORT.read_text()
    for site in SITES:
        assert f"<th scope='row'>{site}</th>" in text
    assert text.count("NOT ESTIMABLE</b><br><small>no organizer receipt") == len(SITES)
    assert "OWNER-REPORTED · UNVERIFIED" in text
    assert "Estimated leaderboard score: NOT ESTIMABLE" in text
    assert "Submit: NO" in text
    assert "Historical snapshot notice" in text
    assert "data/priority_feed.json" in text


def test_champion_downloads_are_immutable_raw_urls_not_blob_pages():
    evidence = json.loads((ROOT / "evidence/nine_site_overlap_20261029.json").read_text())
    text = REPORT.read_text()
    for rec in evidence["champions"].values():
        expected = _report_module().raw_download_url(rec["url"])
        assert expected in text
    assert "github.com/buffedlizard55-lab/" not in text
    assert "raw.githubusercontent.com/buffedlizard55-lab/" in text


def test_geo1_invalid_holdout_number_is_not_promoted_or_displayed():
    text = REPORT.read_text()
    audit = json.loads(AUDIT.read_text())
    assert audit["disposition"] == "INVALID_HOLDOUT_CLAIM"
    assert audit["experiment_card_code_hashes_match_current_sources"] == {
        "scripts/build_unique_geothermal_submission.py": True,
        "src/gems/holdout.py": True,
        "src/gems/emission.py": True,
    }
    assert "GEO1 holdout-integrity finding" in text
    assert "full-catalogue eligibility leakage" in text
    assert "NOT A VALID HOLDOUT RESULT" in text
    assert "0.14269491602190398" not in text
    assert "HOLDOUT-DTI 0.1427" not in text
    assert "0.1323, 0.1524" not in text


def test_internal_holdout_report_includes_evaluator_count_and_ci():
    text = REPORT.read_text()
    assert "HOLDOUT-DTI · gems-segment-pooled-v1" in text
    assert "60,988 withheld positives" in text
    assert "95% CI [0.0308, 0.0439]" in text
    assert "This is not an organizer score" in text or "not a leaderboard score" in text.lower()


def test_b2_claim_and_geometry_analysis_remain_separated():
    text = REPORT.read_text()
    assert "0.2778 — <b>OWNER-REPORTED / UNVERIFIED</b>" in text
    assert "exact 37,654-dot subset of a 44,090-dot GEMSDOE25/GEMSDOE30 D2.8 pattern" in text
    assert "6,436 cells within 200 m" in text
    assert "40,199-dot D2.8-family comparison" in text
    assert "2,545 catalogue-adjacent cells" in text
    assert "Hidden true-positive credit and false-positive mass are unknown" in text


def test_report_generator_help_is_safe_and_archival_card_is_not_overwritten():
    module = _report_module()
    card_before = _sha(RUN_CARD)
    with pytest.raises(SystemExit) as exc:
        module.main(["--help"])
    assert exc.value.code == 0
    assert _sha(RUN_CARD) == card_before


def test_default_report_build_does_not_rewrite_archival_run_card():
    module = _report_module()
    card_before = _sha(RUN_CARD)
    module.main([])
    assert _sha(RUN_CARD) == card_before
    assert "GEO1 holdout-integrity finding" in REPORT.read_text()
