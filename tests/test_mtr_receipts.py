"""Frozen negative artifacts are deliverables, not a new scoring experiment."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from gems import novelty

ROOT = Path(__file__).resolve().parents[1]


def script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load(name):
    return json.loads((ROOT / name).read_text())


def test_frozen_evidence_and_both_exact_files_verify_without_an_experiment():
    result = script("verify_mtr_receipt").verify()
    assert result["verified"] and not result["experiment_rerun"]
    assert result["source_files_verified"] == 7 and result["variant_files_verified"] == 2
    assert result["verdict"] == "negative" and not result["ok_to_submit"]
    assert not result["lane_uniqueness_passed"] and not result["content_identical_to_registry"]


def test_recorded_runner_refuses_implicit_rerun_without_overwriting_evidence():
    path = ROOT / "evidence/mtr1_experiment.json"
    before = path.read_bytes()
    result = subprocess.run(
        [sys.executable, "scripts/evaluate_holdout.py"], cwd=ROOT, capture_output=True, text=True
    )
    assert result.returncode != 0 and "No implicit rerun" in result.stderr
    assert path.read_bytes() == before


def test_canaries_cover_sources_support_and_every_nontrivial_factor():
    report = load("evidence/mtr1_experiment.json")
    canary = report["canary"]
    assert set(canary["features"]) == {
        "rtp_source",
        "ThK_source",
        "valid_support",
        "magnetic_trough",
        "ratio_depletion",
    }
    assert canary["two_polarities_checked"] and canary["passed"]
    assert not report["supervised_fit"] and not report["catalogue_features"]
    assert not report["prediction_inputs_include_registry_rasters"]
    for feature in canary["features"].values():
        assert len(feature["folds"]) == 4 and not feature["leakage_suspected"]
        for fold in feature["folds"]:
            assert 0.1 <= fold["auc"] <= 0.9 and fold["positives"] > 0 and fold["background"] > 0


def test_every_pinned_unique_raster_was_compared_and_lattice_veto_remains():
    report = load("evidence/mtr1_experiment.json")
    expected = {r["id"] for r in load("registry/priority_rasters.json")["unique_rasters"]}
    assert len(expected) == 46
    for stage in ("surface_novelty", "final_novelty"):
        result = report[stage]
        assert {r["registry_id"] for r in result["rows"]} == expected
        assert result["raw_rank_pixels"] == 5167373
        assert result["raw_rank_scope"] == "exact over all footprint pixels"
    assert report["surface_novelty"]["passed"] and not report["final_novelty"]["passed"]
    veto = [r for r in report["final_novelty"]["rows"] if r["duplicate"]]
    assert len(veto) == 1 and veto[0]["registry_id"] == "registry-039"
    assert veto[0]["candidate_dot_overlap_within_3px"] == 1.0
    geometry = load("evidence/lattice_overlap_irregularity.json")
    assert geometry["supported_candidate_domain_fraction_within_3px"] == 1
    assert geometry["no_comparator_removed"]


def test_source_freshness_schema_cannot_disguise_a_leaderboard_or_omission():
    module = script("refresh_priority_feed")
    data = load("docs/data/priority_feed.json")
    sources = load("registry/priority_rasters.json")["sources"]
    module.validate_feed(data, sources)
    for change in ({"leaderboard": {"best_score": 0.99}}, {"rows": data["rows"][:-1]}):
        with pytest.raises(ValueError):
            module.validate_feed({**data, **change}, sources)
    row = {**data["rows"][0], "changed_since_review": not data["rows"][0]["changed_since_review"]}
    with pytest.raises(ValueError, match="change marker"):
        module.validate_feed({**data, "rows": [row, *data["rows"][1:]]}, sources)


def test_missing_gh_is_a_recorded_failed_check_not_a_crashed_website(monkeypatch):
    module = script("refresh_priority_feed")

    def missing(*args, **kwargs):
        raise FileNotFoundError("gh unavailable")

    monkeypatch.setattr(module.subprocess, "check_output", missing)
    row = module.check({"repo": "owner/repository", "ref": "a" * 40})
    assert row["status"] == "failed" and row["changed_since_review"] is None
    assert row["latest_main_ref"] is None and "unavailable" in row["error"]


def test_duplicate_primitives_reject_unknown_numbers_and_honor_both_polarities():
    assert novelty.is_duplicate(-0.90001)
    assert not novelty.is_duplicate(-0.90, 0.70)
    with pytest.raises(ValueError):
        novelty.is_duplicate(np.nan, 0.5)
    with pytest.raises(ValueError):
        novelty.dot_overlap(np.eye(3), np.eye(3), radius_px=np.nan)
    with pytest.raises(ValueError):
        novelty.rank_correlation(np.empty(0), np.empty(0))


def test_full_current_owner_brief_is_embedded_not_replaced_by_the_parallel_summary():
    brief = (ROOT / "knowledge/owner_brief_2026-10-25.md").read_text()
    body = brief.split("\n---\n", 1)[1].strip()
    assert body in (ROOT / "README.md").read_text()
    assert len(brief) > len((ROOT / "knowledge/owner_brief_2026-10-25_summary.md").read_text())
