"""An external point record is a source claim, not a promotion or score replay."""

import copy
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import audit_peer_s2d36 as peer  # noqa: E402


def _source_cards():
    return {
        key: json.loads((ROOT / peer.SOURCES[key]["local"]).read_text())
        for key in ("card", "holdout", "canary", "preregistration")
    }


def test_pinned_peer_evidence_has_correct_ci_and_explicit_scope():
    row = peer.check_reported_evidence(**_source_cards())
    assert row["value"] == pytest.approx(0.2007657135656901)
    assert row["ci95"] == [0.18648773519590356, 0.21533340056778932]
    assert row["withheld_positive_pixels"] == 60988
    assert "no model/fold/bootstrap replay" in row["scope"]
    assert row["source_ci_resamples"] == 1999
    assert "1,000" in row["source_document_discrepancy"]
    assert "missingness" in row["canary_scope"]


@pytest.mark.parametrize("damage", ["arm", "ci", "pooled", "negative", "hash", "canary"])
def test_changed_peer_claims_fail_closed(damage):
    source = copy.deepcopy(_source_cards())
    if damage == "arm":
        source["card"]["best_arm"] = "EXP-1"
    elif damage == "ci":
        source["card"]["holdout"]["arms"]["EXP-2"]["ci95"][0] = 0
    elif damage == "pooled":
        source["holdout"]["summaries"]["EXP-2"]["TP_w"] += 1
    elif damage == "negative":
        source["card"]["slot_approved"] = True
    elif damage == "hash":
        source["card"]["submission"]["sha256"] = "0" * 64
    else:
        source["canary"]["passed"] = False
    with pytest.raises(ValueError, match="inconsistent"):
        peer.check_reported_evidence(**source)


def test_recorded_exact_file_audit_never_authorizes_submission():
    report = json.loads((ROOT / "evidence/peer_s2d36_audit_20261028.json").read_text())
    assert report["source_commit"] == peer.REF
    assert report["source_identities"]["raster"]["sha256"] == peer.SOURCES["raster"]["sha256"]
    assert report["local_format_validation"]["format_valid"] is True
    assert report["local_format_validation"]["template_origin_authenticated"] is False
    assert report["literal_lattice_overlap"]["candidate_within_3px_of_reference"] == pytest.approx(
        0.9947947097253944
    )
    assert report["literal_uniqueness_pass"] is False
    assert report["submission_authorized"] is False and report["verdict"] == "negative"
    assert report["leaderboard_score"] is report["organizer_receipt"] is None
    assert report["new_experiments"] == report["new_geological_tiffs"] == 0
    assert report["competition_slots_used"] == 0


def test_pinned_card_cannot_be_silently_changed(tmp_path, monkeypatch):
    row = peer.SOURCES["card"]
    destination = tmp_path / row["local"]
    destination.parent.mkdir(parents=True)
    destination.write_bytes((ROOT / row["local"]).read_bytes())
    monkeypatch.setattr(peer, "SOURCES", {"card": row})
    assert peer.verify_source_bytes(tmp_path)["card"]["git_blob"] == row["blob"]
    destination.write_bytes(destination.read_bytes() + b" ")
    with pytest.raises(ValueError, match="bytes changed"):
        peer.verify_source_bytes(tmp_path)
    destination.unlink()
    with pytest.raises(ValueError, match="missing"):
        peer.verify_source_bytes(tmp_path)
