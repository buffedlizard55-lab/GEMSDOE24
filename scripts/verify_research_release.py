#!/usr/bin/env python3
"""Verify the frozen release without downloading data or rerunning confirmation folds."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems.release_audit import verify_research_release  # noqa: E402

if __name__ == "__main__":
    print(json.dumps(verify_research_release(ROOT), indent=2, allow_nan=False))
