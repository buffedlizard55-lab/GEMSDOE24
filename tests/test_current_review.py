"""A current-best review must validate bytes and never become promotion."""

import json
from pathlib import Path

import pytest

from gems.current_review import review_current_best

ROOT = Path(__file__).resolve().parents[1]


def test_review_finds_current_best_without_relying_on_active_lane():
    result = review_current_best(ROOT)
    # H24-DRAIN5 superseded DPRF1 as recorded point-best on 2026-10-26; the live
    # review must find it from evidence, not from any hard-coded lane identity.
    assert result["current_recorded_point_best"]["lane"] == "DRAIN5"
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


def test_concurrent_vent_packet_survives_generated_site():
    card = json.loads((ROOT / "evidence/vent_run_card_20261026.json").read_text())
    for page in ("index.html", "docs/index.html", "docs/executive-summary.html"):
        text = (ROOT / page).read_text()
        assert 'id="vent-packet"' in text
        assert f'download="{card["submission_name"]}"' in text
        assert "not generated or scientifically replayed by this review" in text


def test_vent_quarantine_refuses_execution_and_disclaims_dummy_audits():
    import subprocess
    import sys

    blocked = subprocess.run(
        [sys.executable, "scripts/run_vent_lane.py"], cwd=ROOT, capture_output=True, text=True
    )
    assert blocked.returncode != 0 and "quarantined" in blocked.stderr
    verified = subprocess.run(
        [sys.executable, "scripts/run_vent_lane.py", "--verify-recorded"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    packet = json.loads(verified.stdout)
    assert packet["scientific_gate_claims_trusted"] is False
    assert packet["ok_to_submit"] is False
    assert packet["validator_output"]["format_valid"] is True
    for page in ("docs/index.html", "docs/executive-summary.html"):
        assert "Scientific gate claims untrusted" in (ROOT / page).read_text()
