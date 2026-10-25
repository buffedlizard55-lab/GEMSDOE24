"""Exact-file preflight keeps format compatibility and promotion authority separate."""

import json
import subprocess
import sys
from pathlib import Path

from gems.preflight import concise_status, preflight
from gems.validator import sha256_file

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "data/bridge/sample_submission.tif"
CARD = ROOT / "evidence/aspc_run_card_20261025.json"
ZEROS = ROOT / "docs/downloads/gems24-aspc-20261025-6393e9d9b0df-RESEARCH-NOT-SUBMISSION-zeros.tif"
NAN = ROOT / "docs/downloads/gems24-aspc-20261025-6393e9d9b0df-RESEARCH-NOT-SUBMISSION-nan.tif"
MTR_CARD = ROOT / "evidence/mtr1_run_card.json"
MTR_ZEROS = (
    ROOT / "docs/downloads/gems24-mtr1-negative-paired-trough-20261025-ed7243e6d163-zeros.tif"
)
TEMPLATE_SHA = "2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc"


def test_research_artifact_passes_format_and_strict_range_but_is_not_authorized():
    report = preflight(ZEROS, TEMPLATE, run_card_path=CARD, expected_template_sha256=TEMPLATE_SHA)
    assert report["format_validation"]["format_valid"]
    assert report["portal_range_diagnostic"]["strict_whole_array_values_in_0_1"]
    assert report["template"]["pinned_bytes_match"]
    assert report["note"]["within_limit"] and report["note"]["characters"] == 93
    assert not report["run_card"]["scientific_authorization"]
    assert report["decision"]["submission_status"] == "DO_NOT_SUBMIT"
    assert not report["decision"]["ready_to_submit"]
    assert "RUN_CARD_NOT_PROMOTED" in report["decision"]["blockers"]
    assert "SUBMISSION: DO_NOT_SUBMIT" in concise_status(report)


def test_current_mtr_artifact_is_strict_range_compatible_but_has_a_negative_scientific_gate():
    report = preflight(
        MTR_ZEROS, TEMPLATE, run_card_path=MTR_CARD, expected_template_sha256=TEMPLATE_SHA
    )
    assert report["format_validation"]["format_valid"]
    assert report["portal_range_diagnostic"]["strict_whole_array_values_in_0_1"]
    assert report["note"]["characters"] == 104 and report["note"]["within_limit"]
    assert not report["run_card"]["scientific_authorization"]
    assert report["decision"]["submission_status"] == "DO_NOT_SUBMIT"
    assert "RUN_CARD_NOT_PROMOTED" in report["decision"]["blockers"]


def test_nan_outside_twin_is_format_valid_but_not_strict_global_range_compatible():
    report = preflight(NAN, TEMPLATE, run_card_path=CARD, expected_template_sha256=TEMPLATE_SHA)
    assert report["format_validation"]["format_valid"]
    assert not report["portal_range_diagnostic"]["strict_whole_array_values_in_0_1"]
    assert not report["decision"]["ready_to_submit"]
    assert "portal_global_range_compatibility_is_not_demonstrated" in report["decision"]["blockers"]


def test_tampered_or_misbound_run_card_never_grants_authorization(tmp_path):
    card = json.loads(CARD.read_text())
    card.update({"submission_authorized": True, "verdict": "promote"})
    card["raster_sha256"] = "not-the-artifact"
    card["validator_output"]["sha256"] = "not-the-artifact"
    path = tmp_path / "tampered-card.json"
    path.write_text(json.dumps(card))
    report = preflight(ZEROS, TEMPLATE, run_card_path=path, expected_template_sha256=TEMPLATE_SHA)
    assert not report["run_card"]["scientific_authorization"]
    assert "RUN_CARD_HASH_MISMATCH" in report["decision"]["blockers"]
    assert "RUN_CARD_VALIDATOR_HASH_MISMATCH" in report["decision"]["blockers"]


def test_self_asserted_promoted_card_cannot_replace_independent_selector_evidence(tmp_path):
    """This is a unit fixture, not a claim about the active research artifact."""
    digest = sha256_file(ZEROS)
    card = {
        "raster_sha256": digest,
        "submission_name": ZEROS.name,
        "validator_output": {"sha256": digest, "format_valid": True},
        "verdict": "promote",
        "submission_authorized": True,
        "note": "Synthetic unit-test receipt, not a competition result.",
    }
    path = tmp_path / "synthetic-promoted-card.json"
    path.write_text(json.dumps(card))
    report = preflight(ZEROS, TEMPLATE, run_card_path=path, expected_template_sha256=TEMPLATE_SHA)
    assert not report["run_card"]["scientific_authorization"]
    assert not report["decision"]["ready_to_submit"]
    assert report["decision"]["submission_status"] == "DO_NOT_SUBMIT"
    assert "INDEPENDENT_SELECTOR_EVIDENCE_REQUIRED" in report["decision"]["blockers"]


def test_cli_writes_a_reproducible_receipt_and_does_not_turn_negative_gate_into_error(tmp_path):
    output = tmp_path / "receipt.json"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/preflight_submission.py",
            str(ZEROS),
            "--run-card",
            str(CARD),
            "--output",
            str(output),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "SUBMISSION: DO_NOT_SUBMIT" in result.stdout
    receipt = json.loads(output.read_text())
    assert receipt["artifact"]["sha256"] == sha256_file(ZEROS)
    assert not receipt["decision"]["ready_to_submit"]
