"""The generated lattice-hole diagnostic section must stay truthful and fail closed.

Regression for a prior page that prominently called a by-construction lattice-hole
artifact a "Unique GeoTIFF." The section must identify it as non-unique and retain
its explicit research-only / do-not-submit status.
"""

import importlib.util
import json
import re
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CARD = "evidence/24gems-interior-offlattice-geothermal-20261028T164358Z-e5a3c34b27db_run_card.json"
RECEIPT = "evidence/unique_local_overlap_20261028.json"


def _load_build_site():
    spec = importlib.util.spec_from_file_location("build_site", ROOT / "scripts/build_site.py")
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.path.remove(str(ROOT / "scripts"))
    return mod


def _mirror(tmp: Path) -> Path:
    for rel in (CARD, RECEIPT, "docs/downloads", "docs/data"):
        src = ROOT / rel
        dst = tmp / rel
        if src.is_dir():
            shutil.copytree(src, dst, dirs_exist_ok=True)
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(src, dst)
    return tmp


def test_real_section_labels_lattice_hole_diagnostic_not_unique_and_do_not_submit():
    bs = _load_build_site()
    html = bs.render_lattice_hole_diagnostic(ROOT)
    assert 'id="lattice-hole-diagnostic"' in html
    assert "NOT UNIQUE" in html
    assert "NOT protocol-unique" in html
    assert "INVALID AS A UNIQUENESS PASS" in html
    assert "placement by construction" in html
    assert "SUBMIT: NO" in html
    assert "NOT ESTIMABLE" in html
    assert "HOLDOUT-DTI 0.0038" in html
    assert "not a full registry or other-repository comparison" in html
    assert "Unique GeoTIFF" not in html
    assert "SUBMIT: YES" not in html
    assert 'tabindex="0" role="region" aria-label="Lattice-hole diagnostic TIFF details"' in html
    note = re.search(r"Historical note \(≤140 chars, (\d+) used\)", html)
    assert note and int(note.group(1)) <= 140
    for href in re.findall(r'href="(downloads/[^"]+|data/[^"]+)"', html):
        assert (ROOT / "docs" / href).is_file(), href


def test_published_pages_have_no_false_unique_geotiff_label():
    pages = (
        "docs/index.html",
        "docs/executive-summary.html",
        "docs/executive-summary-9sites.html",
        "docs/research.html",
        "docs/sources.html",
    )
    for path in pages:
        html = (ROOT / path).read_text()
        assert "Unique GeoTIFF" not in html, path
    executive = (ROOT / "docs/executive-summary.html").read_text()
    assert 'id="lattice-hole-diagnostic"' in executive
    assert "NOT protocol-unique" in executive
    assert "INVALID AS A UNIQUENESS PASS" in executive
    assert "SUBMIT: NO" in executive


def test_research_card_does_not_displace_current_best_download():
    bs = _load_build_site()
    content = '<section id="current-best-review">best CTA</section><p>more</p>'
    result = bs.place_research_diagnostic_after_current_best(
        content, '<section id="lattice-hole-diagnostic">research</section>'
    )
    assert result.index("best CTA") < result.index("lattice-hole-diagnostic") < result.index("more")


def test_section_placement_fails_closed_without_current_best():
    bs = _load_build_site()
    with pytest.raises(ValueError, match="missing the current point-best"):
        bs.place_research_diagnostic_after_current_best(
            "<main></main>", "<section>research</section>"
        )


def test_parallel_candidate_section_reports_only_supported_negative_claims():
    bs = _load_build_site()
    html = bs.render_parallel_candidate_summary(ROOT)
    assert 'id="parallel-research-candidates"' in html
    assert "VENTRAD — research only; SUBMIT: NO" in html
    assert "H-BLIND-UPWELL — research only; SUBMIT: NO" in html
    assert "0.99817" in html
    assert "Full registry novelty is <strong>not re-verified</strong>" in html
    assert "HOLDOUT-DTI" in html and "NOT ESTIMABLE" in html
    assert "not replayed in this review" in html
    assert "SUBMIT: YES" not in html
    for href in re.findall(
        r'href="(downloads/[^"]+|data/[^"]+|executive-summary-unique\.html)"', html
    ):
        assert (ROOT / "docs" / href).is_file(), href


def test_diagnostic_placement_keeps_point_best_first():
    bs = _load_build_site()
    content = '<section id="current-best-review">best CTA</section><p>more</p>'
    candidate_cards = '<section id="parallel-research-candidates">negative candidates</section>'
    diagnostic = '<section id="lattice-hole-diagnostic">negative diagnostic</section>'
    result = bs.place_research_diagnostic_after_current_best(content, candidate_cards + diagnostic)
    assert result.index("best CTA") < result.index("parallel-research-candidates")
    assert result.index("parallel-research-candidates") < result.index("lattice-hole-diagnostic")
    assert result.index("lattice-hole-diagnostic") < result.index("more")


def test_section_refuses_a_tampered_geotiff(tmp_path):
    bs = _load_build_site()
    tmp = _mirror(tmp_path)
    name = json.loads((ROOT / CARD).read_text())["submission_name"]
    tif = tmp / "docs/downloads" / f"{name}-zeros.tif"
    with tif.open("ab") as f:
        f.write(b"\x00")  # any byte change must break the card's SHA-256 binding
    with pytest.raises(ValueError, match="hash changed"):
        bs.render_lattice_hole_diagnostic(tmp)


def test_section_refuses_a_card_that_authorizes_submission(tmp_path):
    bs = _load_build_site()
    tmp = _mirror(tmp_path)
    card_path = tmp / CARD
    card = json.loads(card_path.read_text())
    card["ok_to_submit"] = True
    card_path.write_text(json.dumps(card))
    with pytest.raises(ValueError, match="must remain DO NOT SUBMIT"):
        bs.render_lattice_hole_diagnostic(tmp)


def test_section_refuses_a_receipt_for_a_different_file(tmp_path):
    bs = _load_build_site()
    tmp = _mirror(tmp_path)
    rp = tmp / RECEIPT
    receipt = json.loads(rp.read_text())
    receipt["candidate_sha256"] = "0" * 64
    rp.write_text(json.dumps(receipt))
    with pytest.raises(ValueError, match="does not describe this diagnostic TIFF"):
        bs.render_lattice_hole_diagnostic(tmp)


def test_geo1_summary_labels_download_as_research_only_not_unique():
    page = ROOT / "docs/executive-summary-9sites.html"
    html = page.read_text()
    assert "GEO1 Research TIFF" in html
    assert "DOWNLOAD: YES — research only" in html
    assert "NOT PROTOCOL-UNIQUE" in html
    assert "NOT UNIQUE — DO NOT SUBMIT" in html
    assert "99.25%" in html and "70%" in html
    assert "NOT ESTABLISHED against current peer heads" in html
    assert "official-format compliant" in html
    assert "HOLDOUT-DTI" in html and "NOT ESTIMABLE" in html
    assert "YES (by bytes)" not in html
    assert "Unique TIF Submission" not in html
    assert "unique, freshly computed TIF" not in html
    assert "Best source-recorded HOLDOUT-DTI" not in html

    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    section = soup.find("section", id="nine-site-table")
    assert section is not None
    table = section.find("table")
    headers = [th.get_text(" ", strip=True) for th in table.select("thead th")]
    assert "Leaderboard estimate / score provenance" in headers
    rows = table.select("tbody tr")
    assert len(rows) == 9
    for row in rows:
        cells = row.find_all(["th", "td"], recursive=False)
        assert len(cells) == 5
        score = cells[2].get_text(" ", strip=True)
        uniqueness = cells[3].get_text(" ", strip=True)
        assert "LEADERBOARD ESTIMATE: NOT ESTIMABLE" in score
        assert "FAIL" in uniqueness
        if "HOLDOUT-DTI" in score:
            assert "gems-segment-pooled-v1" in score
            assert "60,988 withheld positives" in score
            assert "95% CI" in score
        assert cells[4].get_text(" ", strip=True).startswith("NO")

    root_index = (ROOT / "index.html").read_text()
    assert 'href="docs/executive-summary-9sites.html"' in root_index


def test_session_run_card_rejects_duplicate_json_keys():
    path = ROOT / "evidence/session_7b3c8e4b_20261029_run_card.json"

    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    card = json.loads(path.read_text(), object_pairs_hook=unique_object)
    assert card["verdict"] == "negative"
    assert card["submission_authorized"] is False
