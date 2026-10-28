"""The generated PR #85 review must disclose the local audit's limited scope.

Regression for the misleading "unique submission" block: a local raster subset
and a comparator-hole construction are not a full-registry novelty pass.
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


def test_pr85_local_receipt_is_not_presented_as_full_registry_uniqueness():
    bs = _load_build_site()
    html = bs.render_pr85_research_review(ROOT)
    assert 'id="pr85-posthoc-overlap"' in html
    assert "DOWNLOAD: YES (research only) · SUBMIT: NO." in html
    assert "literal uniqueness NOT ESTABLISHED" in html
    assert "max directed overlap 0.4686" in html
    assert "across 69 same-grid rasters" in html
    assert "excludes the full 167-alias registry and other repositories" in html
    assert "complete-registry or pre-placement check" in html
    assert "no-evasion rule" in html
    assert "0.003802043" in html and "3,000 m buffer" in html
    assert "NOT ESTIMABLE" in html
    assert "Unique GeoTIFF" not in html and "Unique submission" not in html
    assert "SUBMIT: YES" not in html.upper().replace("SUBMIT: NO", "")
    note = re.search(r"Research note</td><td><code>(.*?)</code>", html)
    assert note and len(note.group(1)) <= 140
    assert 'tabindex="0"' in html and 'role="region"' in html
    for href in re.findall(r'href="(downloads/[^"]+|data/[^"]+)"', html):
        assert (ROOT / "docs" / href).is_file(), href


def test_review_refuses_a_tampered_geotiff(tmp_path):
    bs = _load_build_site()
    tmp = _mirror(tmp_path)
    name = json.loads((ROOT / CARD).read_text())["submission_name"]
    tif = tmp / "docs/downloads" / f"{name}-zeros.tif"
    with tif.open("ab") as f:
        f.write(b"\x00")
    with pytest.raises(ValueError, match="does not match its run card"):
        bs.render_pr85_research_review(tmp)


def test_review_refuses_a_card_that_authorizes_submission(tmp_path):
    bs = _load_build_site()
    tmp = _mirror(tmp_path)
    card_path = tmp / CARD
    card = json.loads(card_path.read_text())
    card["ok_to_submit"] = True
    card_path.write_text(json.dumps(card))
    with pytest.raises(ValueError, match="must remain DO NOT SUBMIT"):
        bs.render_pr85_research_review(tmp)


def test_review_refuses_a_receipt_for_a_different_file(tmp_path):
    bs = _load_build_site()
    tmp = _mirror(tmp_path)
    rp = tmp / RECEIPT
    receipt = json.loads(rp.read_text())
    receipt["candidate_sha256"] = "0" * 64
    rp.write_text(json.dumps(receipt))
    with pytest.raises(ValueError, match="identity or scope changed"):
        bs.render_pr85_research_review(tmp)
