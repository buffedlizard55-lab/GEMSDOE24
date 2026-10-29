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


@pytest.mark.parametrize("role", ["artifact", "template"])
@pytest.mark.parametrize("suffix", [".msk", ".aux.xml", ".ovr"])
def test_receipt_does_not_create_or_overwrite_a_tiff_sidecar(tmp_path, role, suffix):
    source = tmp_path / "source.tif"
    source.write_bytes(b"source")
    output = tmp_path / (source.name + suffix)
    command = [sys.executable, str(ROOT / "scripts/preflight_submission.py")]
    command += [str(source if role == "artifact" else tmp_path / "missing.tif")]
    if role == "template":
        command += ["--template", str(source)]
    result = subprocess.run(command + ["--output", str(output)], capture_output=True, text=True)
    assert result.returncode != 0
    assert "must not overwrite or create a TIFF sidecar" in result.stderr
    assert not output.exists() and source.read_bytes() == b"source"


def test_sidecar_path_is_checked_against_symlink_target(tmp_path):
    source = tmp_path / "source.tif"
    source.write_bytes(b"source")
    alias = tmp_path / "alias.tif"
    alias.symlink_to(source)
    with pytest.raises(ValueError, match="TIFF sidecar"):
        CLI.protect_inputs(tmp_path / "source.tif.msk", alias)
    assert source.read_bytes() == b"source"


def test_distinct_receipt_and_stdout_are_allowed(tmp_path):
    source = tmp_path / "artifact.tif"
    source.write_bytes(b"source")
    CLI.protect_inputs(tmp_path / "receipt.json", source, None)
    CLI.protect_inputs(None, source)
    assert source.read_bytes() == b"source"
    assert not (tmp_path / "receipt.json").exists()
