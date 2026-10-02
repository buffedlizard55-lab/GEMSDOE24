#!/usr/bin/env python
"""Wrapper: rebuild data/confounds/confounds.npz (+ provenance) via gems.confounds.
Run after placing optional d_road_px.tif / d_claim_px.tif in data/confounds/."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from gems import confounds as cf  # noqa: E402

force = "--force" in sys.argv
print(json.dumps(cf.build_all(force=force), indent=2))
