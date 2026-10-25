"""Both download encodings must fail closed on inconsistent safety evidence."""

import json
import shutil
from pathlib import Path

import pytest

from gems.receipts import research_receipt

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(params=["artifact", "template_convention_companion"])
def receipt(request, tmp_path):
    row = json.loads((ROOT / "evidence/aspc_run_20261025.json").read_text())[request.param]
    source = ROOT / "docs/downloads" / row["file"]
    shutil.copy(source, tmp_path / source.name)
    shutil.copy(
        source.with_suffix(".checks.json"), tmp_path / source.with_suffix(".checks.json").name
    )
    return tmp_path, row


def test_fresh_checks_match_recorded_bytes(receipt):
    folder, row = receipt
    result = research_receipt(folder, row, template=ROOT / "data/bridge/sample_submission.tif")
    assert result["format_valid"] and not result["submission_authorized"]


@pytest.mark.parametrize(
    "fault",
    [
        "authorization",
        "missing_authorization",
        "filename",
        "hard_failure",
        "contradiction",
        "bytes",
        "embedded",
        "path",
    ],
)
def test_tampered_evidence_is_rejected(receipt, fault):
    folder, row = receipt
    path = folder / Path(row["file"]).with_suffix(".checks.json")
    checks = json.loads(path.read_text())
    if fault == "authorization":
        checks["ok_to_upload"] = True
    elif fault == "missing_authorization":
        del row["submission_authorized"]
    elif fault == "filename":
        checks["file"] = "different.tif"
    elif fault == "hard_failure":
        checks["hard_failures"] = ["range"]
    elif fault == "contradiction":
        checks["checks"]["footprint_range_0_1"]["pass"] = False
    elif fault == "bytes":
        with (folder / row["file"]).open("ab") as stream:
            stream.write(b"changed")
    elif fault == "embedded":
        row["validator_output"] = {"format_valid": True}
    elif fault == "path":
        row["file"] = "../escape.tif"
    path.write_text(json.dumps(checks))
    with pytest.raises(ValueError):
        research_receipt(folder, row)
