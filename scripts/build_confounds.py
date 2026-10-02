#!/usr/bin/env python3
"""Build strict data/access nuisance rasters; never substitute geological proxies."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from gems import confounds

if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--force", action="store_true")
    args = p.parse_args()
    print(json.dumps(confounds.build_all(force=args.force), indent=2))
