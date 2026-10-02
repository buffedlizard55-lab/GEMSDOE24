import json
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = spec_from_file_location("record_live_score", ROOT / "scripts/record_live_score.py")
mod = module_from_spec(spec)
spec.loader.exec_module(mod)


def _tree(tmp_path):
    (tmp_path / "registry").mkdir()
    (tmp_path / "registry/submissions.json").write_text(
        json.dumps(
            {
                "submissions": [
                    {
                        "family": "gems24",
                        "hypothesis": "h25-1",
                        "content_id": "abc123",
                        "file": "gems24-x-nan.tif",
                        "sha256": "deadbeef" * 8,
                        "live_dti": None,
                    }
                ]
            }
        )
    )
    (tmp_path / "registry/live_scores.json").write_text(json.dumps({"artifacts": []}))
    return tmp_path


def test_records_score_with_history_and_never_overwrites_silently(tmp_path):
    root = _tree(tmp_path)
    mod.record("gems24-x-nan.tif", 0.2134, "2026-10-03T14:05Z", "first", root)
    mod.record("deadbeef", 0.2201, "2026-10-04T09:00Z", "recheck", root)
    reg = json.loads((root / "registry/submissions.json").read_text())["submissions"][0]
    assert reg["live_dti"] == 0.2201 and [h["score"] for h in reg["score_history"]] == [
        0.2134,
        0.2201,
    ]
    art = json.loads((root / "registry/live_scores.json").read_text())["artifacts"]
    assert len(art) == 1 and art[0]["owner_reported_public_score"] == 0.2201
    assert art[0]["corroboration"] == "owner_report_recorded_by_script"


@pytest.mark.parametrize("bad", [0.0, 1.0, -0.1, 1.5])
def test_rejects_non_probability_scores(tmp_path, bad):
    with pytest.raises(ValueError):
        mod.record("gems24-x-nan.tif", bad, None, "", _tree(tmp_path))


def test_unknown_or_ambiguous_file_is_rejected(tmp_path):
    root = _tree(tmp_path)
    with pytest.raises(ValueError):
        mod.record("nope.tif", 0.2, None, "", root)
    with pytest.raises(ValueError):
        mod.record("de", 0.2, None, "", root)  # prefix too short to identify a file
