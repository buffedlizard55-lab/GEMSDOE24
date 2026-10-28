#!/usr/bin/env python3
"""Fail clearly before provenance verification if the Git checkout is shallow.

Full history is necessary, not sufficient, for verifying historical source commits.
This check does not fetch anything or verify a particular experiment.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def check_history(root: Path) -> None:
    try:
        output = subprocess.check_output(
            ["git", "rev-parse", "--is-shallow-repository"],
            cwd=root,
            text=True,
            stderr=subprocess.PIPE,
            timeout=30,
        ).strip()
    except (OSError, subprocess.SubprocessError) as exc:
        raise ValueError(
            "Cannot determine Git history state; provenance remains unverified"
        ) from exc
    if output == "true":
        raise ValueError("Shallow checkout: fetch full Git history before provenance checks")
    if output != "false":
        raise ValueError("Unexpected Git history state; provenance remains unverified")


def main() -> int:
    try:
        check_history(ROOT)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print("Git history is not shallow; individual provenance checks are still required")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
