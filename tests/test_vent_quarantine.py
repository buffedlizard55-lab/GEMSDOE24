"""Quarantined concurrent lane cannot train or advertise fabricated gates."""

import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run_vent_lane.py"


def test_vent_runner_refuses_reexecution():
    result = subprocess.run([sys.executable, str(SCRIPT)], capture_output=True, text=True)
    assert result.returncode != 0
    assert "quarantined" in result.stderr


def test_vent_verification_checks_hash_and_never_trusts_science(monkeypatch):
    spec = importlib.util.spec_from_file_location("vent_quarantine", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = module.verify_recorded()
    assert result["verification_passed"] is True
    assert result["recorded_scientific_claims_trusted"] is False
    assert result["ok_to_submit"] is False
    monkeypatch.setattr(module, "sha256_file", lambda _: "0" * 64)
    assert module.verify_recorded()["verification_passed"] is False


def test_historical_vent_source_preserved_for_audit():
    text = (ROOT / "archive/legacy/vent/run_vent_lane.py.txt").read_text()
    assert "Dummy pass" in text
    assert "Dummy but plausible" in text
    assert "Dummy pass" not in SCRIPT.read_text()
