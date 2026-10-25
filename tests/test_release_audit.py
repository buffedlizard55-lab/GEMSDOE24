"""Fail-closed checks against stale, tampered or inconsistent release evidence."""

import json
import shutil
from pathlib import Path

import pytest

from gems.release_audit import verify_research_release

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def release(tmp_path):
    for directory in ("evidence", "docs/downloads", "data/bridge"):
        shutil.copytree(ROOT / directory, tmp_path / directory)
    return tmp_path


def mutate(root, path, action):
    target = root / path
    data = json.loads(target.read_text())
    action(data)
    target.write_text(json.dumps(data))


def test_exact_downloads_revalidate_without_promoting():
    audit = verify_research_release(ROOT)
    assert audit["verdict"] == "negative"
    assert audit["same_in_footprint_predictions"]
    assert not audit["submission_authorized"]
    assert len(audit["files"]) == 2


@pytest.mark.parametrize(
    "field,value",
    [
        ("submission_authorized", True),
        ("verdict", "promote"),
        ("blockers", []),
        ("raster_sha256", "0" * 64),
        ("holdout_dti", {}),
        ("note", "other note"),
    ],
)
def test_card_disagreement_stops_release(release, field, value):
    mutate(release, "evidence/aspc_run_card_20261025.json", lambda d: d.update({field: value}))
    with pytest.raises(ValueError):
        verify_research_release(release)


def test_stale_receipt_stops_release(release):
    card = json.loads((release / "evidence/aspc_run_card_20261025.json").read_text())
    receipt = "docs/downloads/" + card["submission_name"].replace(".tif", ".checks.json")
    mutate(release, receipt, lambda d: d.update({"in_footprint_positive_pixels": 0}))
    with pytest.raises(ValueError, match="stored receipts"):
        verify_research_release(release)


def test_corrupted_bytes_stop_release(release):
    card = json.loads((release / "evidence/aspc_run_card_20261025.json").read_text())
    path = release / "docs/downloads" / card["submission_name"]
    with path.open("ab") as stream:
        stream.write(b"changed bytes")
    with pytest.raises(ValueError, match="hash or format"):
        verify_research_release(release)
