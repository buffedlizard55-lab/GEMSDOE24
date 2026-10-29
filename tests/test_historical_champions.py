import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location(
    "historical_champions", ROOT / "scripts/review_historical_champions.py"
)
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)


def test_fresh_historical_readback_uses_strict_shared_validator(monkeypatch):
    calls = []

    def validator(path, template, *, strict=False):
        calls.append((path, template, strict))
        return {"format_valid": False}

    monkeypatch.setattr(review, "check_variants", validator)
    assert review.validate_historical_artifact("candidate.tif", "template.tif") == {
        "format_valid": False
    }
    assert calls == [("candidate.tif", "template.tif", True)]


def test_sources_require_immutable_matching_focus_repository():
    row = json.loads((ROOT / "evidence/peer_forensics_20261025.json").read_text())["artifacts"][0]
    assert review.parse_source(row)[0] == "buffedlizard55-lab/GEMSDOE24"
    for update in (
        {"url": row["url"].replace("07345ea0604953d7efb858d9cfbc21e20c7aca0b", "main")},
        {"repo": "GEMSDOE25"},
        {"sha256": "bad"},
        {"url": row["url"].replace("github.com", "example.com")},
    ):
        with pytest.raises(ValueError):
            review.parse_source({**row, **update})


def test_geometry_measures_inclusive_three_pixel_overlap_and_ignores_exterior():
    fp = np.array([[True, True, True, False]])
    a = np.array([[1.0, 1.0, 0.0, np.nan]])
    result = review.geometry(a, fp, np.array([[3.0, 3.01, 0.0, 0.0]]))
    assert result["dots"] == 2
    assert result["lattice_overlap_within_3px"] == 0.5
    a[0, 3] = 1
    assert (
        review.geometry(a, fp, np.zeros_like(a))["footprint_content_sha256"]
        == result["footprint_content_sha256"]
    )


@pytest.mark.parametrize(
    "a", [np.array([[np.nan]]), np.array([[2.0]]), np.array([[0.0]]), np.array([[0.5]])]
)
def test_invalid_or_empty_binary_champion_fails_closed(a):
    with pytest.raises(ValueError):
        review.geometry(a, np.ones_like(a, dtype=bool), np.zeros_like(a))


def test_published_readback_has_all_sites_no_estimate_and_no_authorization():
    report = json.loads((ROOT / "docs/data/historical_champions_20261028.json").read_text())
    assert len(report["rows"]) == 9
    assert {r["site"] for r in report["rows"]} == review.SITES
    assert report["organizer_confirmed_scores"] == []
    assert report["submission_authorized"] is False
    assert report["new_tiffs"] == report["new_experiments"] == report["slots_used"] == 0
    for row in report["rows"]:
        assert row["leaderboard_estimate"] is row["holdout_dti"] is None
        assert row["validator_output"]["sha256"] == row["sha256"]
        assert row["validator_output"]["format_valid"] is True
        # Fresh readbacks must include strict-only checks, not merely the
        # legacy fields retained for historical receipt compatibility.
        checks = row["validator_output"]["checks"]
        for name in (
            "template_self_contained",
            "raster_self_contained",
            "template_footprint_unmasked",
            "footprint_unmasked",
            "geotiff_driver",
        ):
            assert checks[name]["pass"] is True
            assert checks[name]["hard_requirement"] is True
        assert row["submission_authorized"] is False
        assert row["literal_uniqueness"] == "FAIL"
    aliases = {r["site"]: r["exact_in_footprint_aliases"] for r in report["rows"]}
    assert aliases["GEMSDOE25"] == ["GEMSDOE30"]
    assert aliases["GEMSDOE30"] == ["GEMSDOE25"]
    html = review.render(report)
    assert "SUBMIT NO" in html and "NOT ESTIMABLE" in html
    assert "../evidence/" not in html
    assert html.count('<th scope="row">GEMSDOE') == 9


def test_render_displays_actual_validator_results_not_unconditional_pass():
    report = json.loads((ROOT / "docs/data/historical_champions_20261028.json").read_text())
    html = review.render(report)
    assert html.count("Local checks: PASS; exterior-NaN check: FAIL / UNKNOWN") == 9
    report["rows"][0]["validator_output"]["format_valid"] = False
    report["rows"][0]["validator_output"]["checks"]["outside_is_nan_official_text"]["pass"] = True
    html = review.render(report)
    assert "Local checks: FAIL / UNKNOWN; exterior-NaN check: PASS" in html
    assert "<td>Format PASS;" not in html
