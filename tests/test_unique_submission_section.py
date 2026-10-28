"""The generated unique-GeoTIFF section on the submission guide must stay truthful and fail closed.

Regression for: a hand-edited featured block was silently erased by the next site rebuild.
The section is now generated from its run card, file, note and overlap receipt.
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


def test_real_section_is_do_not_submit_and_links_resolve():
    bs = _load_build_site()
    html = bs.render_unique_submission(ROOT)
    assert 'id="unique-submission"' in html
    assert "SUBMIT: NO" in html
    assert "NOT ESTIMABLE" in html
    assert 'tabindex="0" role="region" aria-label="Unique research TIFF validation details"' in html
    assert "SUBMIT: YES" not in html.upper().replace("SUBMIT: NO", "")
    note = re.search(r"Note \(≤140 chars, (\d+) used\)", html)
    assert note and int(note.group(1)) <= 140
    for href in re.findall(r'href="(downloads/[^"]+|data/[^"]+)"', html):
        assert (ROOT / "docs" / href).is_file(), href


def test_research_card_does_not_displace_current_best_download():
    bs = _load_build_site()
    content = '<section id="current-best-review">best CTA</section><p>more</p>'
    result = bs.place_unique_section_after_current_best(
        content, '<section id="unique-submission">research</section>'
    )
    assert result.index("best CTA") < result.index("unique-submission") < result.index("more")


def test_section_placement_fails_closed_without_current_best():
    bs = _load_build_site()
    with pytest.raises(ValueError, match="missing the current point-best"):
        bs.place_unique_section_after_current_best("<main></main>", "<section>research</section>")


def test_section_refuses_a_tampered_geotiff(tmp_path):
    bs = _load_build_site()
    tmp = _mirror(tmp_path)
    name = json.loads((ROOT / CARD).read_text())["submission_name"]
    tif = tmp / "docs/downloads" / f"{name}-zeros.tif"
    with tif.open("ab") as f:
        f.write(b"\x00")  # any byte change must break the card's SHA-256 binding
    with pytest.raises(ValueError, match="does not match its run card"):
        bs.render_unique_submission(tmp)


def test_section_refuses_a_card_that_authorizes_submission(tmp_path):
    bs = _load_build_site()
    tmp = _mirror(tmp_path)
    card_path = tmp / CARD
    card = json.loads(card_path.read_text())
    card["ok_to_submit"] = True
    card_path.write_text(json.dumps(card))
    with pytest.raises(ValueError, match="must remain DO NOT SUBMIT"):
        bs.render_unique_submission(tmp)


def test_section_refuses_a_receipt_for_a_different_file(tmp_path):
    bs = _load_build_site()
    tmp = _mirror(tmp_path)
    rp = tmp / RECEIPT
    receipt = json.loads(rp.read_text())
    receipt["candidate_sha256"] = "0" * 64
    rp.write_text(json.dumps(receipt))
    with pytest.raises(ValueError, match="does not describe this GeoTIFF"):
        bs.render_unique_submission(tmp)
