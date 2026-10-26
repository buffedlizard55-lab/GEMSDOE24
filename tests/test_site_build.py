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
    (tmp / "data/bridge").mkdir(parents=True)
    shutil.copy(
        ROOT / "data/bridge/sample_submission.tif", tmp / "data/bridge/sample_submission.tif"
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


def test_contradictory_hunique_packet_is_quarantined_without_tiff_link(built):
    from bs4 import BeautifulSoup

    row = json.loads((built / "docs/data/unique_gapfill_quarantined_download.json").read_text())
    for page in ("index.html", "docs/index.html", "docs/executive-summary.html"):
        html = (built / page).read_text()
        assert "H-UNIQUE-03 quarantined" in html
        assert "NOT OK TO SUBMIT" in html
        # PR #56 retains a different, historical H-UNIQUE raster in the
        # collapsed portfolio. The artifact quarantined for oracle leakage
        # must not be recommended or linked anywhere in the built pages.
        assert row["file"] not in html
        soup = BeautifulSoup(html, "html.parser")
        quarantine = soup.find("aside", attrs={"aria-label": "Quarantined H-UNIQUE-03 evidence"})
        assert quarantine is not None
        assert not quarantine.find("a", href=lambda href: href and row["file"] in href)


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
        "executive-summary.html",
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


def test_current_negative_lane_has_a_hash_bound_preflight_and_no_legacy_recommendation(built):
    row = json.loads((built / "docs/data/independent_download.json").read_text())
    preflight = json.loads(
        (
            built
            / "docs/downloads/gems24-mtr1-negative-paired-trough-20261025-ed7243e6d163-zeros.preflight.json"
        ).read_text()
    )
    assert preflight["artifact"]["sha256"] == row["sha256"]
    assert preflight["run_card"]["artifact_sha256_matches"]
    assert preflight["run_card"]["artifact_name_matches"]
    assert preflight["decision"]["submission_status"] == "DO_NOT_SUBMIT"
    assert not preflight["decision"]["ready_to_submit"]
    for name in ("index.html", "docs/index.html", "docs/executive-summary.html"):
        text = (built / name).read_text()
        assert "NOT OK TO SUBMIT" in text
        assert "DO NOT SUBMIT" in text
        assert "Automated preflight" in text
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


def test_mtr_download_is_retained_and_parallel_aspc_is_not_erased(built):
    row = json.loads((built / "docs/data/independent_download.json").read_text())
    for page in ("index.html", "docs/index.html", "docs/executive-summary.html"):
        html = (built / page).read_text()
        assert 'download="' + row["file"] + '"' in html
        assert "DOWNLOAD: YES" in html and "NOT OK TO SUBMIT" in html
        assert "DO NOT SUBMIT" in html and "ASPC research TIFF" in html
        assert html.index('id="historical-') < html.index(row["file"])
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


def test_site_rejects_a_stale_or_permissive_mtr_preflight(built):
    path = (
        built
        / "docs/downloads/gems24-mtr1-negative-paired-trough-20261025-ed7243e6d163-zeros.preflight.json"
    )
    original = path.read_text()
    try:
        altered = json.loads(original)
        altered["decision"]["ready_to_submit"] = True
        altered["decision"]["submission_status"] = "OK_TO_SUBMIT"
        path.write_text(json.dumps(altered))
        result = subprocess.run(
            [sys.executable, "scripts/build_site.py"], cwd=built, capture_output=True, text=True
        )
        assert result.returncode != 0 and "preflight" in result.stderr
    finally:
        path.write_text(original)


@pytest.mark.parametrize("encoding", ["primary", "companion"])
def test_site_rejects_upload_permission_in_either_download_receipt(built, encoding):
    report = json.loads((built / "evidence/aspc_run_20261025.json").read_text())
    row = report["artifact" if encoding == "primary" else "template_convention_companion"]
    path = (built / "docs/downloads" / row["file"]).with_suffix(".checks.json")
    original = path.read_text()
    checks = json.loads(original)
    checks["ok_to_upload"] = True
    try:
        path.write_text(json.dumps(checks))
        result = subprocess.run(
            [sys.executable, "scripts/build_site.py"], cwd=built, capture_output=True, text=True
        )
        assert result.returncode != 0
        assert "disagrees" in result.stderr or "cannot grant upload authorization" in result.stderr
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


def test_latest_oj1_download_precedes_preserved_mtr_and_links_exact_file(built):
    card = json.loads((built / "docs/data/oj1_run_card.json").read_text())
    mtr = json.loads((built / "docs/data/independent_download.json").read_text())
    for name in ("index.html", "docs/index.html", "docs/executive-summary.html"):
        html = (built / name).read_text()
        assert 'download="' + card["submission_name"] + '"' in html
        assert html.index(card["submission_name"]) < html.index(mtr["file"])
        assert "DO NOT SUBMIT" in html and "independent selector" in html.lower()
    assert (built / "docs/downloads" / card["submission_name"]).is_file()


def test_site_rejects_permissive_oj1_preflight(built):
    card = json.loads((built / "docs/data/oj1_run_card.json").read_text())
    path = (built / "docs/downloads" / card["submission_name"]).with_suffix(".preflight.json")
    original = path.read_text()
    try:
        altered = json.loads(original)
        altered["decision"]["ready_to_submit"] = True
        path.write_text(json.dumps(altered))
        result = subprocess.run(
            [sys.executable, "scripts/build_site.py"], cwd=built, capture_output=True, text=True
        )
        assert result.returncode != 0 and "OJ1 preflight" in result.stderr
    finally:
        path.write_text(original)


def test_site_rejects_oj1_published_card_drift(built):
    path = built / "docs/data/oj1_run_card.json"
    original = path.read_text()
    try:
        altered = json.loads(original)
        altered["verdict"] = "promote"
        path.write_text(json.dumps(altered))
        result = subprocess.run(
            [sys.executable, "scripts/build_site.py"], cwd=built, capture_output=True, text=True
        )
        assert result.returncode != 0 and "Published OJ1 run card" in result.stderr
    finally:
        path.write_text(original)


def test_trsg1_is_above_historical_lanes_and_9site_executive_is_rendered(built):
    trsg1 = json.loads((built / "docs/data/trsg1_download.json").read_text())
    dprf1 = json.loads((built / "docs/data/dprf1_download.json").read_text())
    rshg1 = json.loads((built / "docs/data/rshg1_download.json").read_text())
    mtr = json.loads((built / "docs/data/independent_download.json").read_text())
    active = json.loads((built / "docs/data/active_lane.json").read_text())
    assert active["lane"] in {"H24-TNR1", "H24-TRSG1"}
    assert active["ok_to_submit"] is False and active["verdict"] == "negative"
    for name in ("index.html", "docs/index.html", "docs/executive-summary.html"):
        html = (built / name).read_text()
        assert 'download="' + trsg1["file"] + '"' in html
        assert (
            html.index(dprf1["file"])
            < html.index(trsg1["file"])
            < html.index(rshg1["file"])
            < html.index(mtr["file"])
        )
        assert "7/7 Technical Gates PASS" in html and "DO_NOT_SUBMIT" in html
    exec_html = (built / "docs/executive-summary.html").read_text()
    for site_needle in ("GEMSDOE32", "0.2778", "GEMSDOE36", "0.2750", "GEMSDOE24", "0.2477"):
        assert site_needle in exec_html


def test_site_rejects_trsg1_checksum_tampering_and_permissive_preflight(built):
    card_path = built / "evidence/trsg1_run_card_20261026.json"
    original_card = card_path.read_text()
    try:
        altered = json.loads(original_card)
        altered["raster_sha256"] = "0" * 64
        card_path.write_text(json.dumps(altered))
        result = subprocess.run(
            [sys.executable, "scripts/build_site.py"], cwd=built, capture_output=True, text=True
        )
        assert result.returncode != 0 and "TRSG1 checksum" in result.stderr
    finally:
        card_path.write_text(original_card)

    dl = json.loads((built / "docs/data/trsg1_download.json").read_text())
    pf_path = (built / "docs/downloads" / dl["file"]).with_suffix(".preflight.json")
    original_pf = pf_path.read_text()
    try:
        altered_pf = json.loads(original_pf)
        altered_pf["decision"]["ready_to_submit"] = True
        altered_pf["decision"]["submission_status"] = "OK_TO_SUBMIT"
        pf_path.write_text(json.dumps(altered_pf))
        result = subprocess.run(
            [sys.executable, "scripts/build_site.py"], cwd=built, capture_output=True, text=True
        )
        assert result.returncode != 0 and "TRSG1 exact-file preflight" in result.stderr
    finally:
        pf_path.write_text(original_pf)


def test_euler_packet_does_not_override_literal_uniqueness_veto(built):
    """A negative incremental lane cannot market its parent as submission-ready."""
    for page in ("docs/index.html", "docs/executive-summary.html", "README.md"):
        text = (built / page).read_text()
        assert "single best unscored unique candidate" not in text
        assert "only file the local evidence supports submitting" not in text
        assert "not a literal-gate-unique or submit-ready candidate" in text


def test_current_portfolio_supersedes_archives_and_binds_the_first_download(built):
    current = json.loads((built / "docs/data/current_best_review.json").read_text())
    receipt = json.loads((built / "evidence/site_build.json").read_text())
    assert receipt["primary_sha256"] == current["raster_sha256"]
    assert receipt["primary_file"] == current["submission_name"]
    assert (built / "docs/data/portfolio_summary_20261026.csv").exists()
    for name in (
        "index.html",
        "docs/index.html",
        "executive-summary.html",
        "docs/executive-summary.html",
    ):
        html = (built / name).read_text()
        assert 'id="portfolio-audit"' in html and 'id="portfolio-current"' in html
        assert "not estimable" in html.lower()
        assert "86.66%" in html and "DISPUTED DENOMINATOR" in html
        assert html.index('id="portfolio-audit"') < html.index('id="historical-all-')
        assert 'id="current-download-details"' in html
        assert 'id="note-current-best"' in html
    assert 'href="docs/portfolio-review-20261026.md"' in (built / "index.html").read_text()


def test_site_refuses_tampered_peer_scientific_source_card(built):
    path = built / "evidence/portfolio_source_cards/GEMSDOE25.json"
    original = path.read_text()
    try:
        altered = json.loads(original)
        altered["verdict"] = "promote"
        path.write_text(json.dumps(altered))
        result = subprocess.run(
            [sys.executable, "scripts/build_site.py"], cwd=built, capture_output=True, text=True
        )
        assert result.returncode != 0 and "Pinned peer source card changed" in result.stderr
    finally:
        path.write_text(original)
