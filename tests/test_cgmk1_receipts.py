"""Frozen CGMK1 receipt integrity: hashes, format, labels, no-slot verdict.

Reads only committed artifacts (run card, TIFFs, template) — never reruns the
lane and never requires the bulk training raster.
"""

import hashlib
import json
import zipfile
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
CARD = json.loads((ROOT / "evidence/cgmk1_run_card_20261027.json").read_text())
SUB = CARD["submission"]
TIF = ROOT / SUB["zeros_tif_path"]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_run_card_is_negative_and_spends_no_slot():
    assert CARD["lane"] == "H24-CGMK1"
    assert CARD["verdict"] == "negative"
    assert CARD["ok_to_submit"] is False
    assert CARD["ok_to_download"] is True
    assert CARD["submission_slots_spent"] == 0
    assert CARD["organizer_confirmed_score"] is None
    assert len(SUB["note"]) <= 140
    assert SUB["note_characters"] == len(SUB["note"])


def test_holdout_components_recompute_the_recorded_dti():
    h = CARD["holdout"]
    assert h["label"] == "HOLDOUT-DTI"
    assert h["evaluator_version"] == "gems-segment-pooled-v1"
    assert h["n_withheld_positive_pixels"] == 60988
    lo, hi = h["ci95"]["interval"]
    assert 0 <= lo <= h["dti"] <= hi <= 1
    recomputed = h["TP_w"] / (h["TP_w"] + 0.2 * h["FP_w"] + 0.8 * h["FN_w"] + 1e-7)
    assert abs(recomputed - h["dti"]) < 1e-12
    # The recorded result must stay below the pre-run floor it failed.
    assert h["dti"] < CARD["selection_floor_before_run"]["holdout"]["dti"]
    assert CARD["gates"]["holdout_point_beats_selection_floor"] is False
    assert CARD["gates"]["canary_all_channels"] is True


def test_tif_hashes_format_and_strict_range():
    assert sha256(TIF) == SUB["zeros_tif_sha256"]
    assert TIF.stat().st_size == SUB["zeros_tif_bytes"]
    with rasterio.open(ROOT / "data/bridge/sample_submission.tif") as t:
        template_shape, template_crs, template_tr = t.shape, t.crs, t.transform
        footprint = np.isfinite(t.read(1))
    with rasterio.open(TIF) as ds:
        assert ds.count == 1 and ds.dtypes == ("float32",)
        assert ds.shape == template_shape and ds.crs == template_crs
        assert ds.transform == template_tr
        a = ds.read(1)
    assert np.isfinite(a).all(), "zeros variant must have no NaN anywhere"
    assert float(a.min()) >= 0.0 and float(a.max()) <= 1.0
    assert set(np.unique(a).tolist()) == {0.0, 1.0}
    assert int((a[footprint] > 0).sum()) == SUB["positive_pixels"] == 37654
    assert int((a[~footprint] > 0).sum()) == 0
    with rasterio.open(ROOT / "data/bridge/labels.tif") as ds:
        catalogue = (ds.read(1) > 0) & footprint
    assert int(((a > 0) & catalogue).sum()) == 0
    v = CARD["validator_output"]["zeros_variant"]
    assert v["format_valid"] is True and v["hard_failures"] == []
    assert v["checks"]["variant_strict_whole_array_no_nan_allowed"]["pass"] is True
    assert CARD["validator_output"]["strict_whole_array_0_1_zeros_variant"] is True


def test_zip_contains_exactly_the_recorded_tif():
    zp = ROOT / SUB["zip_path"]
    assert sha256(zp) == SUB["zip_sha256"]
    with zipfile.ZipFile(zp) as z:
        assert z.namelist() == [TIF.name]
        assert hashlib.sha256(z.read(TIF.name)).hexdigest() == SUB["zeros_tif_sha256"]


def test_frozen_code_hashes_match_run_card():
    exp = json.loads((ROOT / "evidence/cgmk1_experiment_20261027.json").read_text())
    for rel, digest in exp["code_sha256"].items():
        assert sha256(ROOT / rel) == digest, f"frozen code changed after run: {rel}"


def test_nine_site_json_rows_all_do_not_submit():
    doc = json.loads(
        (ROOT / "evidence/nine_site_executive_summary_cgmk1_20261027.json").read_text()
    )
    sites = [r["site"] for r in doc["rows"]]
    assert sites == [
        "GEMSDOE24",
        "GEMSDOE25",
        "GEMSDOE27",
        "GEMSDOE28",
        "GEMSDOE30",
        "GEMSDOE31",
        "GEMSDOE32",
        "GEMSDOE33",
        "GEMSDOE36",
    ]
    for row in doc["rows"]:
        assert row["ok_to_submit"] is False
        assert row["leaderboard_estimate"] is None
        assert "UNVERIFIED" in row["historical_best_claim"]["label"]
    g32 = next(r for r in doc["rows"] if r["site"] == "GEMSDOE32")
    assert g32["historical_best_claim"]["value"] == 0.2778
    g24 = next(r for r in doc["rows"] if r["site"] == "GEMSDOE24")
    assert g24["this_session_new_lane"]["sha256"] == SUB["zeros_tif_sha256"]
    assert g24["this_session_new_lane"]["holdout"]["dti"] == CARD["holdout"]["dti"]
