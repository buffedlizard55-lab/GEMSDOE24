"""Exact-file and evidence-completeness checks; never promote a format-green file."""

import hashlib
import json
from pathlib import Path

import numpy as np
import rasterio

from gems import aspc, holdout, submission

ROOT = Path(__file__).resolve().parents[1]


def load(path):
    return json.loads((ROOT / path).read_text())


def test_current_lane_counts_and_canaries_cover_every_input_and_factor():
    report = load("evidence/aspc_run_20261025.json")
    result = report["holdout"]
    assert result["evaluator_version"] == holdout.SEGMENT_EVALUATOR_VERSION
    assert result["evidence_class"] == "HOLDOUT-DTI"
    assert result["n_withheld_positives"] == sum(f["n_withheld_positives"] for f in report["folds"])
    features = set(aspc.BANDS) | {
        "antislope_fraction",
        "channel_veto",
        "curvature_balance",
        "step_response",
        "coherence_sqrt",
        "combined_surface",
    }
    assert len(report["canaries"]) == len(features) * 4
    for f in report["folds"]:
        tests = [r for r in report["canaries"] if r["fold"] == f["name"]]
        assert {r["feature"] for r in tests} == features
        assert all(0.10 <= r["auc"] <= 0.90 and not r["flagged"] for r in tests)
        assert f["n_withheld_whole_segment_pixels"] >= f["n_withheld_positives"]
        assert f["buffer_px"] == 30
    rows = [
        [f["candidate_components"][k] for k in ("TP_w", "FP_w", "FN_w")] for f in report["folds"]
    ]
    assert abs(holdout.pooled_dti(rows) - result["value"]) < 1e-12
    assert result["ci95"][0] < result["value"] < result["ci95"][1]
    assert result["current_best_oof_comparison"] is None
    assert not report["submission_authorized"] and not report["slot_spent"]


def test_every_valid_registry_blob_was_checked_without_sampling_or_silent_omission():
    report = load("evidence/aspc_run_20261025.json")
    registry = load("registry/peer_rasters_20261025.json")["entries"]
    expected = {r["blob"] for r in registry if r.get("role") != "format_demo_not_submission"}
    for key in ("surface_registry", "final_registry"):
        assert {r["blob"] for r in report[key]} == expected
        assert len(report[key]) == len(expected)
    excluded = report["excluded_non_submission_references"]
    assert len(excluded) == 1 and "FORMAT_TEST_NOT_SUBMISSION" in excluded[0]["path"]
    assert max(r["rho"] for r in report["surface_registry"] if r["rho"] is not None) <= 0.90
    assert max(r["candidate_within_3px_of_reference"] for r in report["final_registry"]) <= 0.70


def test_exact_primary_and_template_convention_twin_match_predictions_but_not_authorization():
    report = load("evidence/aspc_run_20261025.json")
    card = load("evidence/aspc_run_card_20261025.json")
    row = report["artifact"]
    twin = report["template_convention_companion"]
    assert len(row["note"]) <= 140 and "do not submit" in row["note"].lower()
    template = ROOT / "data/bridge/sample_submission.tif"
    with rasterio.open(template) as ds:
        fp = np.isfinite(ds.read(1))
    arrays = []
    for r in (row, twin):
        p = ROOT / "docs/downloads" / r["file"]
        assert hashlib.sha256(p.read_bytes()).hexdigest() == r["sha256"]
        checks = submission.check_variants(p, template)
        assert checks["format_valid"] and checks["format_acceptable"]
        assert not checks["ok_to_upload"] and not checks["submission_authorized"]
        with rasterio.open(p) as ds:
            arrays.append(ds.read(1))
    assert np.array_equal(arrays[0][fp], arrays[1][fp])
    assert np.isfinite(arrays[0]).all() and np.isnan(arrays[1][~fp]).all()
    assert int(arrays[0][fp].sum()) == 37654
    assert card["raster_sha256"] == row["sha256"]
    assert card["verdict"] == "negative" and not card["submission_authorized"]


def test_promotion_blockers_and_no_unverified_scores_disguised_as_organizer_receipts():
    report = load("evidence/aspc_run_20261025.json")
    assert not report["surface_reads_catalogue"]
    assert report["experiment_count"] == 1 and report["elapsed_seconds"] < 7200
    assert any("Current-best" in s for s in report["blockers"])
    forensic = load("evidence/peer_forensics_20261025.json")
    assert len(forensic["artifacts"]) == 9 and not forensic["organizer_confirmed_scores"]
    assert all(
        r["score_status"].startswith("UNVERIFIED-OWNER-REPORT") for r in forensic["artifacts"]
    )
