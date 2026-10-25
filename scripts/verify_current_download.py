#!/usr/bin/env python3
"""Print a fresh fail-closed receipt for the historical UNIQUE03 research-only download."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems.release_audit import verify_current_download  # noqa: E402

if __name__ == "__main__":
    print(json.dumps(verify_current_download(ROOT), indent=2, allow_nan=False))
