#!/usr/bin/env python
"""Build derived layers + quantized feature stack (see src/gems/geofeatures.py)."""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from gems import geofeatures as gf

t0 = time.time()
force = "--force" in sys.argv
man = gf.build_layers(force=force)
print(f"layers done {time.time() - t0:.0f}s; {len(man['layers'])} layers")
p = gf.build_stack(force=force)
print(f"stack done {time.time() - t0:.0f}s -> {p} ({p.stat().st_size / 1e9:.2f} GB)")
