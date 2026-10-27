#!/usr/bin/env python3
"""Offline necessary-condition check; never authorizes a submission.

Consumes a frozen exact-file audit, not live data. No third-party dependencies.
"""

import argparse
import hashlib
import json
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def bounds(covered: int, uncovered: int, dots: int, limit: Fraction) -> dict:
    if covered < 0 or uncovered < 0 or dots <= 0 or dots > covered + uncovered:
        raise ValueError("Invalid footprint or candidate size")
    if not 0 <= limit < 1:
        raise ValueError("Overlap limit must be in [0, 1)")
    minimum = Fraction(max(0, dots - uncovered), dots)
    maximum = min(covered + uncovered, int(Fraction(uncovered) / (1 - limit)))
    return {
        "candidate_dots": dots,
        "minimum_possible_directed_overlap": float(minimum),
        "overlap_limit": float(limit),
        "necessarily_fails_literal_gate": minimum > limit,
        "maximum_dots_not_ruled_out_by_this_bound": maximum,
        "interpretation": "Necessary condition only; not evidence of novelty or scientific merit",
    }


def report(path: Path, dots: int) -> dict:
    raw = path.read_bytes()
    audit = json.loads(raw)
    if audit.get("schema") != "current-focus-nine-file-audit-v1":
        raise ValueError("Unsupported audit schema")
    lattice = audit["lattice"]
    result = bounds(
        lattice["footprint_3px_covered_pixels"],
        lattice["footprint_3px_uncovered_pixels"],
        dots,
        Fraction(str(lattice["coverage_threshold"])),
    )
    return {
        "schema": "gems-protocol-feasibility-v1",
        "source_audit": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "source_checked_utc": audit["checked_utc"],
        "scope": "Arithmetic on frozen audit counts; no raster remeasurement or live refresh",
        "lattice_sha256": lattice["sha256"],
        "geometry": result,
        "submission_authorized": False,
        "leaderboard_estimate": None,
        "required_next_step": "Coordinator must assign a method lane and resolve the space-filling registry control policy; do not change gates or evade the lattice by placement",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--audit", type=Path, default=ROOT / "evidence/current_focus_nine_file_audit_20261027.json"
    )
    parser.add_argument("--dots", type=int, default=37654)
    args = parser.parse_args()
    print(json.dumps(report(args.audit.resolve(), args.dots), indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
