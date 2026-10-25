"""The stopped OJ1 packet is reproducible evidence, never upload permission."""

import importlib.util
import json
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("oj1_runner", ROOT / "scripts/run_oj1_lane.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def test_fixed_negative_has_full_holdout_and_both_registry_stages():
    card = runner.verify_recorded()
    h = card["holdout"]
    assert h["label"] == "HOLDOUT-DTI" and h["n_withheld_positive_pixels"] == 60988
    assert h["evaluator_version"] == "gems-segment-pooled-v1"
    assert h["ci95"]["interval"][0] <= h["dti"] <= h["ci95"]["interval"][1]
    assert h["dti"] < card["recorded_baseline_comparison"]["holdout"]["dti"]
    before = card["correlation_overlap_vs_registry"]["surface"]
    after = card["correlation_overlap_vs_registry"]["final_dots"]
    assert before["passed"] and not after["passed"]
    assert len(before["rows"]) == len(after["rows"]) == 46
    assert after["max_dot_overlap"] > 0.70
    assert card["leakage_canary"]["passed"]
    assert len(card["leakage_canary"]["features"]) == 24
    assert card["stopped_reason"].startswith("duplicate-final-dots")
    assert not card["ok_to_submit"] and not card["submission_authorized"]
    assert len(card["note"]) <= 140 and "DO NOT SUBMIT" in card["note"]


@pytest.mark.parametrize("change", ["hash", "name", "verdict", "metric"])
def test_changed_record_is_not_a_valid_research_packet(tmp_path, change):
    for name in ("evidence/oj1_experiment_20261025.json", "evidence/oj1_run_card_20261025.json"):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / name, path)
    path = tmp_path / "evidence/oj1_run_card_20261025.json"
    card = json.loads(path.read_text())
    if change == "hash":
        card["raster_sha256"] = "0" * 64
    elif change == "name":
        card["submission_name"] = "../escape.tif"
    elif change == "verdict":
        card["verdict"] = "promote"
    else:
        card["holdout"]["dti"] = 0.99
    path.write_text(json.dumps(card))
    with pytest.raises(ValueError):
        runner.verify_recorded(tmp_path)
