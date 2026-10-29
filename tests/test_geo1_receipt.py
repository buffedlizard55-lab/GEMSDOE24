"""GEO1 exact-file receipt verification must be read-only and fail closed."""

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]


def test_geo1_receipt_verifier_reopens_exact_tiff_and_reports_negative_decision():
    result = subprocess.run(
        [sys.executable, "scripts/verify_geo1_receipt.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    receipt = json.loads(result.stdout)
    assert receipt["verified"] is True
    assert receipt["format_valid"] is True
    assert receipt["strict_whole_array_0_1"] is True
    assert receipt["holdout_label"] == "HOLDOUT-DTI"
    assert receipt["holdout_evaluator_version"] == "gems-segment-pooled-v1"
    assert receipt["withheld_positive_pixels"] == 60988.0
    assert receipt["verdict"] == "negative"
    assert receipt["ok_to_submit"] is False


def test_geo1_verifier_is_read_only_and_hash_bound():
    run_card = ROOT / "evidence/geo1_run_card.json"
    raster = (
        ROOT
        / "docs/downloads/GEMSDOE24-geo1-concealed-conduit-rad-mag-lidar-20261029-8c9946590ca7-zeros.tif"
    )
    before = {
        path: (hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_mtime_ns)
        for path in (run_card, raster)
    }
    subprocess.run(
        [sys.executable, "scripts/verify_geo1_receipt.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    after = {
        path: (hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_mtime_ns)
        for path in (run_card, raster)
    }
    assert after == before


def test_geo1_verifier_rejects_tampered_run_card(tmp_path):
    for path in (
        "evidence/geo1_experiment.json",
        "evidence/geo1_run_card.json",
        "docs/data/geo1_run_card.json",
        "docs/data/geo1_download.json",
        "docs/downloads",
        "data/bridge/sample_submission.tif",
        "src/gems/holdout.py",
        "src/gems/metric.py",
        "src/gems/emission.py",
        "src/gems/novelty.py",
        "src/gems/submission.py",
        "scripts/build_unique_geothermal_submission.py",
    ):
        source = ROOT / path
        target = tmp_path / path
        if source.is_dir():
            shutil.copytree(source, target)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    card_path = tmp_path / "evidence/geo1_run_card.json"
    card = json.loads(card_path.read_text())
    card["raster_sha256"] = "0" * 64
    card_path.write_text(json.dumps(card))
    other = json.loads((tmp_path / "docs/data/geo1_run_card.json").read_text())
    other["raster_sha256"] = "0" * 64
    (tmp_path / "docs/data/geo1_run_card.json").write_text(json.dumps(other))

    result = subprocess.run(
        [sys.executable, "scripts/verify_geo1_receipt.py", "--root", str(tmp_path)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "SHA-256" in result.stderr


def test_nine_site_executive_page_has_download_links_that_resolve_and_clear_submit_status():
    path = ROOT / "docs/executive-summary-9sites.html"
    soup = BeautifulSoup(path.read_text(), "html.parser")
    text = soup.get_text(" ", strip=True)
    assert "DOWNLOAD: YES · SUBMIT: NO" in text
    assert "NOT submission-authorized" in text
    assert "NOT ESTIMABLE" in text
    assert "GEMSDOE24-geo1-concealed-conduit-rad-mag-lidar-20261029-8c9946590ca7-zeros.tif" in text
    table = soup.find(id="nine-site-table").find("table")
    assert len(table.find("tbody").find_all("tr", recursive=False)) == 9

    missing = []
    for tag in soup.find_all(href=True):
        href = tag["href"]
        if href.startswith(("http://", "https://", "mailto:", "#", "data:", "javascript:")):
            continue
        target = (path.parent / href.split("#")[0].split("?")[0]).resolve()
        if not target.exists():
            missing.append((href, str(target)))
    assert not missing
