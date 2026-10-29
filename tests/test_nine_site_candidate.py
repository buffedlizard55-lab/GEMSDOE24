"""Regression checks for the 2026-10-29 nine-site unique candidate (SUBMIT NO by design).

These tests never call a portal, never submit, and never write a score. They pin the
candidate bytes, its grid/range validity, its note length, the negative verdict, and
(when the pinned champion bytes are present locally) its zero overlap with the nine sites.
"""

import json
from pathlib import Path

import numpy as np
import pytest
import rasterio

ROOT = Path(__file__).resolve().parents[1]
CAND = ROOT / "docs/downloads/gems24-nine-complement-seghgb-20261029-zeros.tif"
CARD = ROOT / "evidence/run_card_20261029_nine_site_unique.json"
TEMPLATE = ROOT / "data/bridge/sample_submission.tif"
RECEIPT = ROOT / "data/research/nine_site/fetch_receipt.json"


def _sha(path):
    import hashlib

    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _card():
    return json.loads(CARD.read_text())


def test_candidate_bytes_match_run_card():
    assert CAND.exists()
    assert _sha(CAND) == _card()["raster"]["sha256"]


def test_candidate_grid_matches_template_and_is_strict_0_1():
    with rasterio.open(TEMPLATE) as t, rasterio.open(CAND) as c:
        assert c.count == 1 and c.dtypes[0] == "float32"
        assert c.crs.to_epsg() == 32611
        assert c.shape == t.shape == (3730, 3292)
        assert c.transform == t.transform
        a = c.read(1)
    assert np.all((a >= 0) & (a <= 1))
    assert not np.isnan(a).any()
    with rasterio.open(TEMPLATE) as t:
        fp = np.isfinite(t.read(1))
    assert int(((a > 0) & fp).sum()) == _card()["raster"]["dots"] == 37654


def test_note_within_limit_and_verdict_is_negative_submit_no():
    card = _card()
    assert len(card["submission_note"]) <= 140
    assert card["submission_note_chars"] == len(card["submission_note"])
    assert card["verdict"] == "negative"
    assert card["submit"] == "NO"
    assert card["holdout"]["label"] == "HOLDOUT-DTI"


@pytest.mark.skipif(not RECEIPT.exists(), reason="pinned champion bytes not restored locally")
def test_zero_overlap_with_nine_focus_sites_and_registry_gate_recorded_as_fail():
    from scipy.ndimage import distance_transform_edt

    with rasterio.open(TEMPLATE) as t:
        fp = np.isfinite(t.read(1))
    with rasterio.open(CAND) as c:
        cd = fp & (c.read(1) > 0)
    for row in json.loads(RECEIPT.read_text()):
        assert _sha(ROOT / row["local"]) == row["sha256_expected"]
        with rasterio.open(ROOT / row["local"]) as ds:
            bd = fp & (ds.read(1) > 0)
        ov = float(((distance_transform_edt(~bd) <= 3.0) & cd).sum() / cd.sum())
        assert ov <= 0.70, row["site"]
    # The literal registry (lattice) gate is recorded as FAILED, not hidden.
    assert _card()["overlap_vs_registry"]["gate_literal_registry_70pct"] is False


def test_exact_soft_metric_reproduces_recorded_fold_components():
    import sys

    sys.path.insert(0, str(ROOT / "src"))
    from gems import holdout
    from gems.metric import dti_components_exact

    with rasterio.open(TEMPLATE) as t:
        fp = np.isfinite(t.read(1))
    labels = (rasterio.open(ROOT / "data/bridge/labels.tif").read(1) == 1) & fp
    with rasterio.open(CAND) as c:
        cand = c.read(1).astype(np.float64)
    sh = holdout.SegmentHoldout(fp, labels, buffer_px=30)
    rec = json.loads((ROOT / "evidence/seg_hgb_complement_experiment.json").read_text())["folds"]
    for fold, r in zip(sh.folds, rec):
        comp = dti_components_exact(
            cand,
            fold["truth"].astype(np.uint8),
            valid_mask=fold["valid"],
            catalogue_mask=fold["visible"],
        )
        assert abs(comp["TP_w"] - r["TP_w"]) < 1e-2
        assert abs(comp["FP_w"] - r["FP_w"]) < 1e-2
        assert abs(comp["FN_w"] - r["FN_w"]) < 1e-2
