"""Featured downloads and priority summaries cannot turn claims into approval."""

import copy
import importlib.util
import json
from pathlib import Path

import pytest

from gems.release_audit import verify_featured_downloads

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "priority_summary", ROOT / "scripts/priority_summary.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_featured_exact_bytes_remain_negative():
    result = verify_featured_downloads(ROOT)
    assert [r["lane"] for r in result["files"]] == ["gvc1", "rshg1"]
    assert result["ok_to_download"] is True
    assert result["ok_to_submit"] is False
    for row in result["files"]:
        assert row["validator_output"]["format_valid"]
        assert not row["validator_output"]["submission_authorized"]


@pytest.mark.parametrize(
    "change",
    [
        {"ok_to_submit": True},
        {"verdict": "promote"},
        {"submission_authorized": True},
        {"sha256": "0" * 64},
        {"file": "../escape-zeros.tif"},
        {"note_file": "../escape.txt"},
        {"note": "x" * 141},
    ],
)
def test_featured_metadata_tampering_fails_closed(monkeypatch, change):
    original = Path.read_text

    def read(path, *args, **kwargs):
        text = original(path, *args, **kwargs)
        if path == ROOT / "docs/data/gvc1_download.json":
            data = json.loads(text)
            data.update(change)
            return json.dumps(data)
        return text

    monkeypatch.setattr(Path, "read_text", read)
    with pytest.raises(ValueError):
        verify_featured_downloads(ROOT)


def test_nine_site_summary_labels_claims_and_staleness():
    registry = json.loads((ROOT / "registry/priority_rasters.json").read_text())
    feed = json.loads((ROOT / "docs/data/priority_feed.json").read_text())
    html = module.priority_summary(registry, feed)
    assert html.count("OWNER-REPORTED, UNVERIFIED:") == 9
    assert html.count("SUBMIT: NO") == 9
    assert "Best file to submit under the current gates: NONE" in html
    assert "0.2778" in html
    feed = copy.deepcopy(feed)
    feed["rows"].pop()
    with pytest.raises(ValueError):
        module.priority_summary(registry, feed)
