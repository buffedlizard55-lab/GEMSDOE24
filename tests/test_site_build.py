"""The Pages deployment depends on scripts/build_site.py: build it in a scratch copy and check the result."""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
COPY = ["docs", "evidence", "registry", "scripts", "src", "knowledge"]


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("site")
    for name in COPY:
        shutil.copytree(
            ROOT / name,
            tmp / name,
            ignore=shutil.ignore_patterns("__pycache__", "archive", "*.pyc"),
        )
    (tmp / "data/external/audit_sources").mkdir(parents=True)
    shutil.copy(
        ROOT / "data/external/audit_sources/acquisition_blocks_receipt.json",
        tmp / "data/external/audit_sources/acquisition_blocks_receipt.json",
    )
    shutil.copy(ROOT / "README.md", tmp / "README.md")
    result = subprocess.run(
        [sys.executable, "scripts/build_site.py"], cwd=tmp, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr[-2000:]
    return tmp


def active_artifact(built):
    lane = built / "docs/data/active_lane.json"
    if lane.exists():
        return json.loads(lane.read_text())["artifact"]
    return json.loads((built / "docs/data/download.json").read_text())


def test_download_is_on_the_first_screen_and_the_file_is_the_registered_one(built):
    row = active_artifact(built)
    for page in ("index.html", "docs/index.html", "docs/executive-summary.html"):
        html = (built / page).read_text()
        assert row["file"] in html and 'download="' + row["file"] + '"' in html
        # the download button precedes any metrics/sections: it sits in the hero
        assert (
            html.index(row["file"]) < html.index('class="metrics"')
            if 'class="metrics"' in html
            else True
        )
    assert (built / "docs/downloads" / row["file"]).exists()


def test_pages_state_the_unscored_status_and_never_invent_a_score(built):
    text = (built / "docs/index.html").read_text()
    assert "not yet scored" in text.lower() and "not leaderboard scores" in text.lower()
    receipt = json.loads((built / "evidence/site_build.json").read_text())
    assert receipt["no_scores_fabricated"] is True
    status = (
        (built / "README.md")
        .read_text()
        .split("<!-- STATUS:START -->")[1]
        .split("<!-- STATUS:END -->")[0]
    )
    assert "not a leaderboard result" in status and "No weekly slot has been spent" in status


def test_guide_has_the_portal_steps_note_and_the_range_error_advice(built):
    html = (built / "docs/executive-summary.html").read_text()
    for needle in (
        "Make new submission",
        "Note (optional)",
        "Predicted values must be in range [0, 1]",
        "allfinite",
        "three submissions",
        "SHA-256",
    ):
        assert needle in html
    row = active_artifact(built)
    assert row["note"] in html and len(row["note"]) <= 140


def test_site_never_links_a_missing_local_file(built):
    from bs4 import BeautifulSoup

    for page in (
        "index.html",
        "docs/index.html",
        "docs/executive-summary.html",
        "docs/research.html",
        "docs/sources.html",
    ):
        soup = BeautifulSoup((built / page).read_text(), "html.parser")
        for tag, attr in (("a", "href"), ("link", "href"), ("script", "src"), ("img", "src")):
            for t in soup.find_all(tag):
                v = t.get(attr)
                if not v or v.startswith(("http://", "https://", "mailto:", "#")):
                    continue
                assert (built / page).parent.joinpath(v.split("#")[0].split("?")[0]).exists(), (
                    page,
                    v,
                )


def test_current_negative_lane_is_not_a_legacy_recommendation(built):
    report = json.loads((built / "docs/data/active_lane.json").read_text())
    assert not report["submission_authorized"]
    for name in ("index.html", "docs/index.html", "docs/executive-summary.html"):
        text = (built / name).read_text()
        assert "NOT OK TO SUBMIT" in text
        assert "DO NOT SUBMIT" in text
        assert "One click gets the recommended submission" not in text
    historical = json.loads((built / "docs/data/download.json").read_text())
    assert historical["status"] == "historical_superseded"
    assert not historical["submission_authorized"]


def test_site_rejects_a_run_card_that_disagrees_with_the_exact_download(built):
    path = built / "evidence/aspc_run_card_20261025.json"
    original = path.read_text()
    altered = json.loads(original)
    altered["raster_sha256"] = "tampered-not-a-real-digest"
    try:
        path.write_text(json.dumps(altered))
        result = subprocess.run(
            [sys.executable, "scripts/build_site.py"], cwd=built, capture_output=True, text=True
        )
        assert result.returncode != 0 and "identity disagree" in result.stderr
    finally:
        path.write_text(original)


def test_mtr_download_is_first_screen_and_parallel_aspc_is_not_erased(built):
    row = json.loads((built / "docs/data/independent_download.json").read_text())
    for page in ("index.html", "docs/index.html", "docs/executive-summary.html"):
        html = (built / page).read_text()
        assert 'download="' + row["file"] + '"' in html
        assert "DOWNLOAD: YES" in html and "NOT OK TO SUBMIT" in html
        assert "DO NOT SUBMIT" in html and "ASPC research TIFF" in html
        if 'class="metrics"' in html:
            assert html.index(row["file"]) < html.index('class="metrics"')
    assert not row["ok_to_submit"] and not row["lane_uniqueness_gate_passed"]


def test_site_rejects_mtr_card_checksum_tampering_without_falling_back_to_old_files(built):
    path = built / "evidence/mtr1_run_card.json"
    original = path.read_text()
    try:
        altered = json.loads(original)
        altered["raster_sha256"] = "0" * 64
        path.write_text(json.dumps(altered))
        result = subprocess.run(
            [sys.executable, "scripts/build_site.py"], cwd=built, capture_output=True, text=True
        )
        assert result.returncode != 0 and "checksum" in result.stderr
    finally:
        path.write_text(original)


def test_site_rejects_sahg1_card_checksum_tampering(built):
    path = built / "evidence/sahg1_run_card_20261025.json"
    original = path.read_text()
    try:
        altered = json.loads(original)
        altered["raster_sha256"] = "0" * 64
        path.write_text(json.dumps(altered))
        result = subprocess.run(
            [sys.executable, "scripts/build_site.py"], cwd=built, capture_output=True, text=True
        )
        assert result.returncode != 0 and "SAHG1 checksum" in result.stderr
    finally:
        path.write_text(original)
