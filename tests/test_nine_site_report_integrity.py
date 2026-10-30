"""Regression tests for the nine-site report's GEO1 holdout-integrity warning.

These checks read pinned JSON evidence only. They do not run an experiment,
open a portal, generate a TIFF, or authorize a submission.
"""

import json
from pathlib import Path

import pytest

from scripts import build_nine_site_report as report

ROOT = Path(__file__).resolve().parents[1]


def _json(path: str) -> dict:
    return json.loads((ROOT / path).read_text())


def _report_html() -> str:
    return report.build_html(
        _json("evidence/nine_site_overlap_20261029.json"),
        _json("evidence/seg_hgb_experiment.json"),
        _json("evidence/seg_hgb_complement_experiment.json"),
        _json("evidence/candidate_registry_overlap_20261029.json"),
    )


def test_geo1_holdout_is_explicitly_invalid_and_not_rankable():
    facts = report.geo1_facts()
    holdout = facts["holdout"]

    assert holdout["label"] == "INVALID SOURCE-RECORDED HOLDOUT-DTI"
    assert holdout["valid_for_comparison"] is False
    assert "COMPROMISED" in holdout["status"]
    assert "complete labels grid" in holdout["status"]
    assert holdout["evaluator_version"] == "gems-segment-pooled-v1"
    assert holdout["withheld_positives"] == 60_988
    assert facts["lattice"] > 0.70
    assert facts["max_nine"] < 0.70
    assert facts["ok_to_submit"] is False


def test_report_disclaims_geo1_score_and_separates_focus_nine_from_full_registry():
    content = _report_html()

    assert "No protocol-unique, validated candidate is identified" in content
    assert "INVALID SOURCE-RECORDED HOLDOUT-DTI" in content
    assert "95% CI [0.1323, 0.1524]" in content
    assert "95% CI [0.0308, 0.0439]" in content
    assert "compromised by full-catalogue eligibility leakage" in content
    assert "full-registry gate FAIL" in content
    assert "Best protocol-unique submission:</b> none identified" in content
    assert "Best unique file by holdout" not in content
    assert "GEO1 (on main, concurrent session) has the stronger holdout" not in content
    assert "Do not upload either research raster from this page" in content
    assert "no file here is approved to upload" in content
    assert "at 22,164 or more dots" in content
    assert "largest budget not ruled out by this bound is 22,163" in content


def test_geo1_integrity_disagreement_fails_closed(monkeypatch):
    original_load = report.load

    def altered_load(name: str) -> dict:
        result = original_load(name)
        if name == "session_1ec38571_20261029_run_card.json":
            result["reviewed_parallel_artifact"]["recorded_holdout_dti"]["review_status"] = (
                "SOURCE-RECORDED; NOT REVIEWED"
            )
        return result

    monkeypatch.setattr(report, "load", altered_load)
    with pytest.raises(ValueError, match="not marked invalid"):
        report.geo1_facts()


def test_geo1_positive_selector_receipt_fails_closed(monkeypatch):
    original_load = report.load

    def altered_load(name: str) -> dict:
        result = original_load(name)
        if name == "geo1_run_card.json":
            result["verdict"] = "promote"
            result["ok_to_submit"] = True
        return result

    monkeypatch.setattr(report, "load", altered_load)
    with pytest.raises(ValueError, match="selector receipt is not negative"):
        report.geo1_facts()


def test_geo1_source_hash_disagreement_fails_closed(monkeypatch):
    original_load = report.load

    def altered_load(name: str) -> dict:
        result = original_load(name)
        if name == "geo1_experiment.json":
            result["code_sha256"]["scripts/build_unique_geothermal_submission.py"] = "0" * 64
        return result

    monkeypatch.setattr(report, "load", altered_load)
    with pytest.raises(ValueError, match="source-hashed runner changed"):
        report.geo1_facts()
