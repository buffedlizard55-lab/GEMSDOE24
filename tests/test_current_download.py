"""Current first-screen download must fail closed on stale/tampered evidence."""
import json
import shutil
from pathlib import Path

import pytest

from gems.release_audit import verify_current_download

ROOT = Path(__file__).resolve().parents[1]


def test_current_download_is_format_valid_not_submit_ready():
    result = verify_current_download(ROOT)
    assert result["validator_output"]["format_valid"]
    assert result["ok_to_download"]
    assert not result["ok_to_submit"]


@pytest.mark.parametrize("change", [
    {"ok_to_submit": True}, {"verdict": "promote"},
    {"raster_sha256": "0" * 64}, {"submission_name": "../escape.tif"},
    {"note": "x" * 141}, {"validator_output": {}},
])
def test_current_download_rejects_inconsistent_card(tmp_path, change):
    for directory in ("docs/data", "docs/downloads", "data/bridge"):
        shutil.copytree(ROOT / directory, tmp_path / directory)
    path = tmp_path / "docs/data/unique_run_card.json"
    card = json.loads(path.read_text())
    card.update(change)
    path.write_text(json.dumps(card))
    with pytest.raises(ValueError):
        verify_current_download(tmp_path)
