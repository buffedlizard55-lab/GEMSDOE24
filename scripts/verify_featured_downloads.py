#!/usr/bin/env python3
"""Revalidate featured GVC1/RSHG1 research downloads; never grant authorization."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems.release_audit import verify_featured_downloads  # noqa: E402

if __name__ == "__main__":
    print(json.dumps(verify_featured_downloads(ROOT), indent=2, allow_nan=False))
