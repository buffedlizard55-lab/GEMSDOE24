#!/usr/bin/env python3
"""Fail early if historical preregistration checks cannot trust a shallow checkout.

Full history is necessary, not sufficient: individual verification scripts must
still check that their exact pinned commits exist and satisfy ancestry rules.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def check_history(root: Path) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--is-shallow-repository"],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        return False, f"Cannot check git history: {exc}"
    if result.returncode != 0:
        return False, f"Cannot check git history: {result.stderr.strip() or 'git failed'}"
    state = result.stdout.strip()
    if state == "true":
        return False, (
            "Shallow checkout: historical preregistration verification requires full history. "
            "Run 'git fetch --unshallow origin' or use checkout fetch-depth: 0."
        )
    if state != "false":
        return False, f"Cannot determine git history depth: unexpected git output {state!r}"
    return True, "Full history detected; pinned commits and ancestry still require verification."


def main() -> int:
    ok, message = check_history(ROOT)
    print(message, file=sys.stdout if ok else sys.stderr)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
