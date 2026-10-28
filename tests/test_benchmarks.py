"""A later declared point-best cannot be hidden behind an easier old floor."""

import json
import shutil
from pathlib import Path

import pytest

from gems.benchmarks import RECORDS, recorded_point_best, recorded_points
from gems.validator import sha256_file

ROOT = Path(__file__).resolve().parents[1]


def _seed(root):
    evidence = root / "evidence"
    evidence.mkdir()
    for _, source, _ in RECORDS:
        shutil.copyfile(ROOT / source, root / source)
    return evidence


def test_later_cup_point_best_is_recorded_but_never_mistaken_for_promotion():
    result = recorded_point_best(ROOT)
    assert result["lane"] == "S3DEP1"
    assert result["holdout"]["dti"] == 0.16606013635163805
    assert result["source_sha256"] == sha256_file(ROOT / result["source"])
    assert result["ok_to_submit"] is False
    assert "no independent" in result["scope"]
    rows = recorded_points(ROOT)
    assert {"GVC1", "TNR1", "CRP1", "CUP1", "DPRF1", "S3DEP1"} <= {row["lane"] for row in rows}
    assert [row["holdout"]["dti"] for row in rows] == sorted(
        (row["holdout"]["dti"] for row in rows), reverse=True
    )


def test_new_records_are_discovered_without_changing_a_hardcoded_floor(tmp_path):
    evidence = _seed(tmp_path)
    card = json.loads((ROOT / "evidence/tnr1_run_card_20261026.json").read_text())
    # Synthetic metadata fixture; the inventory deliberately is not a score replay.
    card["holdout"]["dti"] = 0.17
    card["holdout"]["ci95"]["interval"] = [0.16, 0.18]
    (evidence / "future_run_card_fixture.json").write_text(json.dumps(card))
    result = recorded_point_best(tmp_path)
    assert result["lane"] == "FUTURE" and result["holdout"]["dti"] == 0.17
    assert result["ok_to_submit"] is False
    card["holdout"]["evaluator_version"] = "different-protocol"
    (evidence / "future_run_card_fixture.json").write_text(json.dumps(card))
    assert recorded_point_best(tmp_path)["lane"] == "S3DEP1"


def test_new_record_with_explicit_pooled_dti_alias_is_normalized(tmp_path):
    evidence = _seed(tmp_path)
    card = json.loads((ROOT / "evidence/tnr1_run_card_20261026.json").read_text())
    card["holdout"]["pooled_dti"] = card["holdout"].pop("dti")
    (evidence / "future_pooled_run_card.json").write_text(json.dumps(card))
    row = next(row for row in recorded_points(tmp_path) if row["lane"] == "FUTURE_POOLED")
    assert row["holdout"]["dti"] == 0.13219180093505795


def test_conflicting_dti_aliases_fail_closed(tmp_path):
    evidence = _seed(tmp_path)
    card = json.loads((ROOT / "evidence/tnr1_run_card_20261026.json").read_text())
    card["holdout"]["pooled_dti"] = 0.9
    (evidence / "future_conflicting_run_card.json").write_text(json.dumps(card))
    with pytest.raises(ValueError, match="Conflicting benchmark"):
        recorded_points(tmp_path)


def test_bad_known_benchmark_cannot_silently_lower_the_current_best(tmp_path):
    evidence = _seed(tmp_path)
    card = json.loads((ROOT / "evidence/gvc1_run_card_20261025.json").read_text())
    card["holdout"]["n_withheld_positive_pixels"] = 1
    (evidence / "gvc1_run_card_20261025.json").write_text(json.dumps(card))
    with pytest.raises(ValueError, match="Known benchmark"):
        recorded_points(tmp_path)


@pytest.mark.parametrize("damage", ["missing_file", "missing_primary_result"])
def test_losing_the_highest_known_receipt_is_fail_closed(tmp_path, damage):
    _seed(tmp_path)
    path = tmp_path / "evidence/cup1_run_card_20261026.json"
    if damage == "missing_file":
        path.unlink()
    else:
        card = json.loads(path.read_text())
        del card["holdout_dti"]
        path.write_text(json.dumps(card))
    with pytest.raises(ValueError, match="Known benchmark"):
        recorded_points(tmp_path)


def test_legacy_ci_list_is_normalized_without_claiming_replay(tmp_path):
    evidence = _seed(tmp_path)
    card = json.loads((ROOT / "evidence/tnr1_run_card_20261026.json").read_text())
    card["holdout"]["ci95"] = card["holdout"]["ci95"]["interval"]
    (evidence / "legacy_run_card_fixture.json").write_text(json.dumps(card))
    legacy = next(row for row in recorded_points(tmp_path) if row["lane"] == "LEGACY")
    assert legacy["holdout"]["ci95"]["level"] == 0.95
    assert "no bootstrap replay" in legacy["holdout"]["ci95"]["scope"]
    assert "no independent" in legacy["scope"]


def test_pinned_concurrent_results_raise_the_conservative_selection_floor(tmp_path):
    from gems.benchmarks import EXTERNAL_RECORDS, selection_floor

    _seed(tmp_path)
    for row in EXTERNAL_RECORDS:
        external = tmp_path / row["source"]
        external.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / row["source"], external)
    assert recorded_point_best(tmp_path)["lane"] == "S3DEP1"  # local main remains unchanged
    result = selection_floor(tmp_path)
    assert result["lane"] == "KPL-36"
    assert result["holdout"]["dti"] == 0.17010000946379217
    assert result["ok_to_submit"] is False
    assert "not independently replayed" in result["scope"]
    for row in EXTERNAL_RECORDS:
        external = tmp_path / row["source"]
        original = external.read_bytes()
        external.write_bytes(original + b" ")
        with pytest.raises(ValueError, match="missing or changed"):
            selection_floor(tmp_path)
        external.unlink()
        with pytest.raises(ValueError, match="missing or changed"):
            selection_floor(tmp_path)
        external.write_bytes(original)
