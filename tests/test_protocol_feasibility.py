"""These tests also run without scientific dependencies via unittest."""

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/check_protocol_feasibility.py"
SPEC = importlib.util.spec_from_file_location("protocol_feasibility", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class FeasibilityTests(unittest.TestCase):
    def test_current_bound(self):
        result = MODULE.bounds(5160724, 6649, 37654, Fraction(7, 10))
        self.assertTrue(result["necessarily_fails_literal_gate"])
        self.assertEqual(result["maximum_dots_not_ruled_out_by_this_bound"], 22163)

    def test_exact_threshold_is_not_failure(self):
        result = MODULE.bounds(7, 3, 10, Fraction(7, 10))
        self.assertFalse(result["necessarily_fails_literal_gate"])

    def test_no_uncovered_pixels(self):
        self.assertTrue(MODULE.bounds(100, 0, 1, Fraction(7, 10))["necessarily_fails_literal_gate"])

    def test_empty_overlap(self):
        self.assertEqual(
            MODULE.bounds(10, 10, 5, Fraction(7, 10))["minimum_possible_directed_overlap"], 0
        )

    def test_invalid_inputs(self):
        for args in [
            (-1, 2, 1, Fraction(1, 2)),
            (1, 2, 0, Fraction(1, 2)),
            (1, 2, 4, Fraction(1, 2)),
            (1, 2, 1, Fraction(1)),
        ]:
            with self.assertRaises(ValueError):
                MODULE.bounds(*args)

    def test_modified_threshold_is_rejected(self):
        source = SCRIPT.parents[1] / "evidence/current_focus_nine_file_audit_20261027.json"
        audit = json.loads(source.read_text())
        audit["lattice"]["coverage_threshold"] = 0.99
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audit.json"
            path.write_text(json.dumps(audit))
            with self.assertRaises(ValueError):
                MODULE.report(path, 37654)

    def test_cli_exit_codes(self):
        for dots, expected in [(37654, 2), (20000, 0)]:
            completed = subprocess.run(
                [sys.executable, str(SCRIPT), "--dots", str(dots)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, expected, completed.stderr)
            self.assertFalse(json.loads(completed.stdout)["submission_authorized"])

    def test_frozen_receipt_never_authorizes(self):
        result = MODULE.report(
            SCRIPT.parents[1] / "evidence/current_focus_nine_file_audit_20261027.json", 37654
        )
        self.assertFalse(result["submission_authorized"])
        self.assertIsNone(result["leaderboard_estimate"])


if __name__ == "__main__":
    unittest.main()
