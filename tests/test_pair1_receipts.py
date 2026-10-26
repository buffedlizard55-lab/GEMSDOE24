"""PAIR1 receipt integrity: run card must match the exact downloadable file."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import rasterio

ROOT = Path(__file__).resolve().parents[1]
CARD = json.loads((ROOT / "evidence/pair1_run_card_20261026.json").read_text())
EXP = json.loads((ROOT / "evidence/pair1_experiment_20261026.json").read_text())


def test_pair1_file_hash_and_strict_range():
    p = ROOT / "docs/downloads" / CARD["submission_name"]
    assert p.is_file()
    assert hashlib.sha256(p.read_bytes()).hexdigest() == CARD["raster_sha256"]
    with rasterio.open(p) as ds:
        a = ds.read(1)
        assert ds.count == 1 and ds.dtypes == ("float32",)
        assert ds.shape == (3730, 3292) and ds.crs.to_epsg() == 32611
    assert bool(((a >= 0) & (a <= 1)).all())  # strict whole-array: no NaN anywhere
    assert int((a > 0).sum()) == CARD["validator_output"]["dots"] == 37654


def test_pair1_verdict_is_negative_and_no_slot():
    assert CARD["verdict"] == "negative"
    assert CARD["slot_spent"] is False
    assert CARD["organizer_confirmed_score"] is None
    assert len(CARD["submission_note_le_140"]) <= 140
    h = CARD["holdout"]
    assert h["evaluator_version"] == "gems-segment-pooled-v1"
    assert h["n_withheld_positives"] == 60988
    # negative means: did not beat its own BASE, CI straddles/below zero
    assert h["exp2_pair1_26ch"]["dti"] < h["exp1_base_22ch"]["dti"]
    assert h["paired_delta_ci95"][0] < 0


def test_pair1_method_novelty_pass_but_literal_registry_gate_fails():
    n = CARD["correlation_overlap_vs_registry"]
    assert n["max_abs_spearman_rho"] <= 0.90
    assert n["max_candidate_dots_within_3px"] <= 0.70  # competing methods only
    assert n["spacing5_lattice_control_overlap"] > 0.70
    assert "Literal all-entry gate therefore still fails" in n["lattice_note"]
    assert CARD["leakage_canary"]["passed"] is True
    assert CARD["leakage_canary"]["worst_two_polarity_auc"] <= 0.90


def test_pair1_executive_summary_applies_literal_rule_to_lattice():
    page = (ROOT / "docs/pair1-executive-summary-20261026.html").read_text()
    assert "NO under literal Rule 1" in page
    assert "99.4% within 3 px of registry-039" in page
    assert "Zero copied pixels does not override this proximity gate" in page


def test_pair1_experiment_matches_card():
    assert EXP["final"]["sha256_zeros"] == CARD["raster_sha256"]
    assert (
        abs(EXP["experiments"]["exp2_pair1"]["dti"] - CARD["holdout"]["exp2_pair1_26ch"]["dti"])
        < 1e-12
    )
    assert EXP["final"]["validator_zeros"]["format_valid"] is True
