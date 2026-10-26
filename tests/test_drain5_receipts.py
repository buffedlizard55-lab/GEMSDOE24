"""Frozen H24-DRAIN5 duplicate-lane receipts: the first paired win over DPRF1 must
never be re-rendered as a unique, submittable candidate."""

import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CARD = json.loads((ROOT / "evidence/drain5_run_card_20261026.json").read_text())
SEL = json.loads((ROOT / "evidence/drain5_selector_20261026.json").read_text())
DL = json.loads((ROOT / "docs/data/drain5_download.json").read_text())
NINE = json.loads((ROOT / "evidence/nine_site_executive_summary_drain5_20261026.json").read_text())
DPRF1_CARD = json.loads((ROOT / "evidence/dprf1_run_card_20261026.json").read_text())


def test_drain5_frozen_head_to_head_is_replayed_and_not_promoted():
    pair = CARD["paired_comparisons"]["arm1_vs_arm2_nodrain_replay"]
    assert CARD["baseline_reproduced"] is True
    assert CARD["verdict"] == "negative"
    assert CARD["ok_to_submit"] is False
    assert CARD["ok_to_download"] is True
    # First strictly positive paired increment over the DPRF1 parent ...
    assert CARD["holdout"]["dti"] > DPRF1_CARD["holdout"]["dti"]
    assert pair["paired_delta_dti"] > 0
    assert pair["paired_delta_ci95"][0] > 0
    assert pair["fold_wins"] == 4
    # ... that is still a duplicate lane under Rule 1 (parent family only).
    nov = CARD["correlation_overlap_vs_registry"]
    assert nov["dot_overlap_within_3px_vs_dprf1"] > 0.70
    top = nov["top_5_competing_comparators"]
    assert [t["registry_id"] for t in top[:2]] == ["local-dprf1", "local-eul1"]
    assert all(
        t["candidate_dot_overlap_within_3px"] <= 0.70 and not t["duplicate"] for t in top[2:]
    )
    assert nov["peer_blobs_max_dot_overlap"] <= 0.70
    assert CARD["exact_file_nuisance_audit"]["candidate"]["strict_gate_passed"] is True
    assert CARD["leakage_canary"]["passed"] is True
    assert (
        CARD["arms_same_evaluator"]["arm2_nodrain_52ch_replay"]["dti"]
        == DPRF1_CARD["holdout"]["dti"]
    )


def test_drain5_selector_and_drainage_receipt_are_consistent():
    assert SEL["decision"] == "DO_NOT_SUBMIT"
    assert SEL["human_inspection_used"] is False
    assert SEL["artifact_sha256"] == CARD["raster_sha256"] == DL["sha256"]
    assert DL["ok_to_submit"] is False and DL["file"] == CARD["submission_name"]
    # The first lane ever to pass G3 against the issuance-time recorded best (DPRF1).
    assert SEL["gates"]["g3_holdout_beats_recorded_best_and_paired_baseline"] is True
    assert SEL["gates"]["g4_registry_novelty"] is False
    diag = CARD["drainage_diagnostics"]
    assert diag["channel_cells_accum_ge_100"] > 0
    assert 0 < diag["sink_cells"] < 0.01 * diag["valid_dem_cells"]
    assert CARD["leakage_canary"]["n_features_checked"] == 59


def test_drain5_exact_download_zip_and_note():
    checks = json.loads((ROOT / "docs/downloads" / DL["checks_file"]).read_text())
    zero = checks["zero_outside"]
    assert zero["format_valid"] is True
    assert zero["submission_authorized"] is False
    assert zero["in_footprint_positive_pixels"] == 37_654
    assert zero["checks"]["footprint_range_0_1"]["pass"] is True
    assert zero["checks"]["variant_strict_whole_array_no_nan_allowed"]["pass"] is True
    assert DL["pixel_count"] == 37_654
    zip_path = ROOT / "docs/downloads" / DL["zip_file"]
    with zipfile.ZipFile(zip_path) as zf:
        assert zf.namelist() == [DL["file"]]
        assert hashlib.sha256(zf.read(DL["file"])).hexdigest() == DL["sha256"]
    note = (ROOT / "docs/downloads" / DL["note_file"]).read_text().strip()
    assert note == DL["note"] == CARD["note"]
    assert 0 < len(note) <= 140


def test_drain5_is_never_rendered_as_current_submit_choice():
    assert len(NINE["sites"]) == 9
    home = next(s for s in NINE["sites"] if s["site"] == "GEMSDOE24")
    block = home["latest_drain5_20261026"]
    assert block["ok_to_download"] is True and block["ok_to_submit"] is False
    assert block["paired_delta_ci95_vs_dprf1_replay"][0] > 0
    assert home["drain5_3px_overlap_vs_site_artifact"] > 0.70
    table = NINE["download_submit_table"]
    assert table[0]["file_to_download"] == DPRF1_CARD["submission_name"]
    assert table[1]["file_to_download"] == DL["file"]
    assert all(row["ok_to_submit"] is False for row in table)
    assert all(
        row["estimated_score"] is None
        or row["estimated_score"]["label"].startswith(("HOLDOUT-DTI", "UNVERIFIED"))
        for row in table
    )
    findings = (
        ROOT / "knowledge/27_DRAIN5_findings_and_executive_summary_2026-10-26.md"
    ).read_text()
    assert "OK TO SUBMIT TODAY: NOTHING" in findings
    assert DL["file"] in findings and DL["sha256"] in findings
    # The recorded run card is embedded verbatim.
    assert json.loads(findings.split("```json", 1)[1].split("```", 1)[0]) == CARD
    # First screen: the #1 unscored unique candidate (DPRF1) is named before DRAIN5.
    for page in (
        "index.html",
        "executive-summary.html",
        "docs/index.html",
        "docs/executive-summary.html",
        "README.md",
    ):
        path = ROOT / page
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        assert 0 <= text.find(DPRF1_CARD["submission_name"]) < text.find(DL["file"]), page


def test_drain5_verify_recorded_independent_receipts():
    result = subprocess.run(
        [sys.executable, "scripts/run_drain5_lane.py", "--verify-recorded"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    receipt = json.loads(result.stdout)
    assert receipt["verified"] is True and receipt["experiment_rerun"] is False
    assert receipt["submission_name"] == DL["file"] and receipt["ok_to_submit"] is False
