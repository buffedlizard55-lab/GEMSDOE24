"""These tests also run without scientific dependencies via unittest."""

import importlib.util
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

    def test_frozen_receipt_never_authorizes(self):
        result = MODULE.report(
            SCRIPT.parents[1] / "evidence/current_focus_nine_file_audit_20261027.json", 37654
        )
        self.assertFalse(result["submission_authorized"])
        self.assertIsNone(result["leaderboard_estimate"])


if __name__ == "__main__":
    unittest.main()
