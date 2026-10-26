"""No historical claim, valid TIFF or local point-best may imply submission approval."""

import copy
import json
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from gems.executive_decisions import CLAIMS, SITES, build_decisions, render_decisions

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def current():
    return json.loads((ROOT / "docs/data/current_best_review.json").read_text())


def test_complete_nine_site_download_and_estimate_table(current):
    packet = build_decisions(ROOT, current)
    assert tuple(row["site"] for row in packet["rows"]) == SITES
    assert all(row["ok_to_submit"] is False for row in packet["rows"])
    assert all(row["leaderboard_estimate"] is None for row in packet["rows"])
    assert all(row["organizer_confirmed_score"] is None for row in packet["rows"])
    assert packet["rows"][0]["uniqueness"].startswith("FAIL")
    assert packet["rows"][6]["historical_claim"]["value"] == 0.2778
    soup = BeautifulSoup(render_decisions(packet), "html.parser")
    assert len(soup.select("tbody tr")) == 9
    assert len(soup.select("a[download$='.tif']")) == 1
    assert soup.select_one("caption")
    assert "60,988 withheld positives" in soup.get_text()
    assert soup.get_text().count("SUBMIT NO") == 9


@pytest.mark.parametrize("name", ["../escape-zeros.tif", "x-nan.tif", "/x-zeros.tif"])
def test_unsafe_downloads_are_rejected(current, name):
    current["submission_name"] = name
    with pytest.raises(ValueError, match="filename"):
        build_decisions(ROOT, current)


def test_modified_download_cannot_be_recommended(current):
    current["raster_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="reviewed bytes"):
        build_decisions(ROOT, current)


def test_positive_card_cannot_authorize_via_table(current):
    current["ok_to_submit"] = True
    with pytest.raises(ValueError, match="authorize"):
        build_decisions(ROOT, current)


@pytest.mark.parametrize("value", [True, float("nan"), -0.1, 1.1, "0.9"])
def test_bad_reference_values_fail_closed(tmp_path, current, value):
    claims = json.loads((ROOT / CLAIMS).read_text())
    claims["sites"]["GEMSDOE24"][0]["owner_reported"] = value
    path = tmp_path / CLAIMS
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(claims))
    # Reuse immutable local bytes; this test is about claim validation, not raster IO.
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/downloads").symlink_to(ROOT / "docs/downloads", target_is_directory=True)
    with pytest.raises(ValueError, match="Malformed"):
        build_decisions(tmp_path, current)


def test_missing_site_cannot_silently_drop_a_requested_site(tmp_path, current):
    claims = json.loads((ROOT / CLAIMS).read_text())
    del claims["sites"]["GEMSDOE36"]
    path = tmp_path / CLAIMS
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(claims))
    with pytest.raises(ValueError, match="exactly"):
        build_decisions(tmp_path, current)


def test_renderer_escapes_reference_text(current):
    packet = copy.deepcopy(build_decisions(ROOT, current))
    packet["rows"][0]["historical_reference"] = "<script>alert(1)</script>"
    assert "<script>" not in render_decisions(packet)


def test_generated_pages_keep_decisions_above_historical_packets():
    for page in (
        "index.html",
        "executive-summary.html",
        "docs/index.html",
        "docs/executive-summary.html",
    ):
        soup = BeautifulSoup((ROOT / page).read_text(), "html.parser")
        table = soup.select_one("#nine-site-download-decisions")
        assert table is not None
        assert len(table.select("tbody tr")) == 9
        assert "no calibrated estimate" in table.get_text()
