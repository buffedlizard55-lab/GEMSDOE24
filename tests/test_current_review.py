"""A current-best review must validate bytes and never become promotion."""

import json
from pathlib import Path

import pytest

from gems.current_review import review_current_best

ROOT = Path(__file__).resolve().parents[1]


def test_review_finds_current_best_without_relying_on_active_lane():
    result = review_current_best(ROOT)
    assert result["current_recorded_point_best"]["lane"] == "DPRF1"
    assert result["holdout"]["n_withheld_positive_pixels"] == 60988
    assert result["holdout"]["evaluator_version"] == "gems-segment-pooled-v1"
    assert result["validator_output"]["format_valid"] is True
    assert result["validator_output"]["sha256"] == result["raster_sha256"]
    assert result["non_fault_mimic"]
    assert result["ok_to_submit"] is False and result["verdict"] == "negative"
    assert result["new_experiments"] == result["submission_slots_used"] == 0
    assert result["selector"]["gates"]["g4_registry_novelty"] is False
    assert len(result["note"]) <= 140


def test_review_rejects_unsafe_filename(monkeypatch):
    import gems.current_review as module

    monkeypatch.setattr(module, "recorded_point_best", lambda root: {"source": "card.json"})
    original = Path.read_text

    def read(path, *args, **kwargs):
        if path.name == "card.json":
            return json.dumps({"submission_name": "../escape-zeros.tif"})
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", read)
    with pytest.raises(ValueError, match="plain zero-outside"):
        review_current_best(ROOT)


@pytest.mark.parametrize(
    "failed_gate",
    [
        "artifact_hash_matches_run_card",
        "artifact_name_matches_run_card",
        "g1_format_strict_0_1",
        "note_at_most_140_chars",
    ],
)
def test_bad_bytes_or_identity_cannot_produce_download_yes(monkeypatch, failed_gate):
    import gems.current_review as module

    gates = {
        key: True
        for key in (
            "artifact_hash_matches_run_card",
            "artifact_name_matches_run_card",
            "g1_format_strict_0_1",
            "note_at_most_140_chars",
        )
    }
    gates[failed_gate] = False
    monkeypatch.setattr(module, "verify_selector", lambda *args: {"gates": gates})
    with pytest.raises(ValueError, match="exact-file"):
        review_current_best(ROOT)


def test_review_refuses_to_become_a_positive_authorization_path(monkeypatch):
    import gems.current_review as module

    gates = {
        key: True
        for key in (
            "artifact_hash_matches_run_card",
            "artifact_name_matches_run_card",
            "g1_format_strict_0_1",
            "note_at_most_140_chars",
        )
    }
    monkeypatch.setattr(
        module,
        "verify_selector",
        lambda *args: {
            "gates": gates,
            "ok_to_submit": True,
            "decision": "OK_TO_SUBMIT",
        },
    )
    with pytest.raises(ValueError, match="cannot authorize"):
        review_current_best(ROOT)


def test_current_pages_disclaim_cross_site_rank_and_causal_proof():
    for page in (
        "index.html",
        "executive-summary.html",
        "docs/index.html",
        "docs/executive-summary.html",
    ):
        text = (ROOT / page).read_text()
        assert 'id="current-best-review"' in text
        assert "Not a verified cross-site winner" in text
        assert "not unique under the literal all-entry rule" in text
        assert "plausible, unproven explanation" in text
        assert "unscored, genuinely unique GeoTIFFs across all 9 sites" not in text
