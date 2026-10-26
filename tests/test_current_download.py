"""Current first-screen download must fail closed on stale/tampered evidence."""

import json
import shutil
from pathlib import Path

import pytest

from gems.release_audit import verify_current_download

ROOT = Path(__file__).resolve().parents[1]


def test_current_download_is_format_valid_but_not_submit_ready():
    result = verify_current_download(ROOT)
    assert result["validator_output"]["format_valid"]
    assert result["ok_to_download"]
    assert not result["ok_to_submit"]
    assert result["run_card"] == "evidence/dprf1_run_card_20261026.json"
    assert not result["submission_authorized"]


def test_conflicting_hunique_promotion_claim_cannot_replace_current_download():
    result = verify_current_download(ROOT)
    assert result["run_card"].startswith("evidence/dprf1_")
    assert result["verdict"] == "negative"
    assert result["ok_to_submit"] is False


@pytest.mark.parametrize(
    "change",
    [
        {"ok_to_submit": True},
        {"verdict": "promote"},
        {"raster_sha256": "0" * 64},
        {"submission_name": "../escape.tif"},
        {"note": "x" * 141},
        {"validator_output": {}},
    ],
)
def test_current_download_rejects_inconsistent_card(tmp_path, change):
    for directory in ("docs/data", "docs/downloads", "data/bridge", "evidence"):
        shutil.copytree(ROOT / directory, tmp_path / directory)
    path = tmp_path / "evidence/dprf1_run_card_20261026.json"
    card = json.loads(path.read_text())
    card.update(change)
    path.write_text(json.dumps(card))
    with pytest.raises(ValueError):
        verify_current_download(tmp_path)
