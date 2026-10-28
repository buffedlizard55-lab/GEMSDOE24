"""The blocked session cannot be mistaken for a scored or eligible candidate."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_negative_session_card_is_explicit_about_absence_of_candidate():
    card = json.loads((ROOT / "evidence/session_c1d3a8b8_run_card_20261028.json").read_text())
    for key in (
        "hypothesis",
        "mechanism",
        "named_non_fault_mimic",
        "holdout",
        "holdout_dti",
        "holdout_ci95",
        "evaluator_version",
        "withheld_positive_pixels",
        "raster_sha256",
        "validator_output",
        "submission_name",
        "leaderboard_estimate",
        "organizer_confirmed_score",
        "remaining_quota",
    ):
        assert card[key] is None
    assert all(
        card["validation"][key] is None
        for key in ("nan_count", "finite_range", "crs", "shape", "transform")
    )
    assert card["verdict"] == "negative" and card["ok_to_submit"] is False
    assert card["ok_to_download_candidate"] is False
    assert card["experiments_executed"] == card["new_geological_tiffs"] == 0
    assert card["competition_slots_used"] == 0
    assert len(card["note"]) == card["note_length"] <= 140
    assert card["peer_research_only"]["scientific_replay"] is False
    assert card["peer_research_only"]["submit_authorized"] is False
    assert len(card["review_passes"]) == 3
