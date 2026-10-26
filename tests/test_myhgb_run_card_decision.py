import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_json(relative_path: str) -> dict:
    return json.loads((ROOT / relative_path).read_text())


def test_myhgb_recorded_decision_fails_closed_on_missing_gates() -> None:
    card = _load_json("evidence/myhgb_run_card_20261025.json")
    novelty = card["correlation_overlap_vs_registry"]
    gates = card["technical_gate_breakdown"]

    assert card["verdict"] == "negative"
    assert card["ok_to_submit"] is False
    assert card["submission_authorized"] is False
    assert card["technical_promotion_gates_passed"] is False
    assert card["holdout"]["label"] == "HOLDOUT-DTI"
    assert card["holdout"]["evaluator_version"] == "gems-segment-pooled-v1"
    assert card["holdout"]["n_withheld_positive_pixels"] == 60_988
    assert gates["beats_oof_multiphysics_hgb_d3_with_95ci"] is False
    assert gates["complete_literal_registry_coverage"] is False
    assert novelty["calibration_controls_checked"] == 0
    assert novelty["peer_blobs_checked"] == 0
    assert novelty["literal_all_entries_passed"] is False
    assert novelty["literal_all_entries_max_overlap_within_3px"] is None
    assert "research; DO NOT SUBMIT" in card["note"]
    assert len(card["note"]) <= 140


def test_myhgb_download_and_preflight_never_override_negative_card() -> None:
    download = _load_json("docs/data/myhgb_download.json")
    preflight = _load_json(
        "docs/downloads/gems24-myhgb-regime-hydro-hgb-20261026-3e38453a8fb9-zeros.preflight.json"
    )

    assert download["verdict"] == "negative"
    assert download["ok_to_download"] is True
    assert download["ok_to_submit"] is False
    assert download["submission_authorized"] is False
    assert download["note"].endswith("research; DO NOT SUBMIT")
    assert preflight["decision"]["submission_status"] == "DO_NOT_SUBMIT"
    assert preflight["decision"]["ready_to_submit"] is False
    assert preflight["run_card"]["verdict_promote"] is False


def test_myhgb_runner_does_not_hardcode_positive_gate_or_submission() -> None:
    tree = ast.parse((ROOT / "scripts/run_my_hgb_lane.py").read_text())
    forbidden_targets = {"technical_gates_passed", "ok_to_submit"}

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant):
            if node.value.value is True:
                names = {target.id for target in node.targets if isinstance(target, ast.Name)}
                assert names.isdisjoint(forbidden_targets)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.value, ast.Constant):
            if node.value.value is True and isinstance(node.target, ast.Name):
                assert node.target.id not in forbidden_targets
