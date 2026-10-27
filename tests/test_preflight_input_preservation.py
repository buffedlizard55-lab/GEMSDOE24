"""A read-only preflight receipt must not destroy its own evidence."""

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "preflight_cli_preservation", ROOT / "scripts/preflight_submission.py"
)
CLI = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CLI)


@pytest.mark.parametrize("role", ["artifact", "template", "run-card", "note-file"])
@pytest.mark.parametrize("alias", ["direct", "symlink", "hardlink"])
def test_cli_preserves_each_input_before_evaluation(tmp_path, role, alias):
    source = tmp_path / "source"
    source.write_bytes(b"immutable evidence, deliberately not a TIFF")
    output = source if alias == "direct" else tmp_path / "receipt.json"
    if alias == "symlink":
        output.symlink_to(source)
    elif alias == "hardlink":
        output.hardlink_to(source)
    command = [sys.executable, str(ROOT / "scripts/preflight_submission.py")]
    command += [str(source if role == "artifact" else tmp_path / "missing.tif")]
    if role != "artifact":
        command += [f"--{role}", str(source)]
    command += ["--output", str(output)]
    result = subprocess.run(command, capture_output=True, text=True, cwd=ROOT)
    assert result.returncode != 0
    assert "Receipt output must not overwrite" in result.stderr
    assert source.read_bytes() == b"immutable evidence, deliberately not a TIFF"


def test_distinct_receipt_and_stdout_are_allowed(tmp_path):
    source = tmp_path / "artifact.tif"
    source.write_bytes(b"source")
    CLI.protect_inputs(tmp_path / "receipt.json", source, None)
    CLI.protect_inputs(None, source)
    assert source.read_bytes() == b"source"
    assert not (tmp_path / "receipt.json").exists()
