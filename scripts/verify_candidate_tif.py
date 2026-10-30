#!/usr/bin/env python3
"""Pre-upload gate for a candidate GeoTIFF (read-only; writes a JSON receipt).

Checks, in order, and reports every failure instead of stopping at the first:
  1. Official format (DrivenData submission-format text, page 967):
     EPSG:32611, 100 m grid identical to data/bridge/sample_submission.tif,
     single band float32, all finite values in [0, 1], NaN/null only outside
     the footprint (this candidate uses finite 0.0 outside; see README).
  2. Byte identity: sha256 equal to any TIFF in the repo or the nine focus repos.
  3. Uniqueness, two measures, both reported:
     a. max fraction of this file's dots within 3 px of any other file's dots,
        against the nine focus files and every local TIFF (exact-duplicate and
        near-duplicate test). Limit used by the repo protocol: 70%.
     b. the same measure against the registered peer lattice witness
        inputs/calibration/13gems_20261001_r13-lattice-s5_v2_nan-outside.tif
        (GEMSDOE13). Reported separately because its 5-px lattice covers
        99.87% of the footprint, so the 70% test is unsatisfiable above
        22,163 dots (scripts/check_uniqueness_feasibility.py).
Output: evidence/candidate_verify_<stem>.json. Verdict is never "submit";
a PASS here is a format/uniqueness receipt, not authorization or a score.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from nine_site_verify import SITES, format_check, overlap_3px, sha256  # noqa: E402

TEMPLATE = ROOT / "data/bridge/sample_submission.tif"
LATTICE = ROOT / "inputs/calibration/13gems_20261001_r13-lattice-s5_v2_nan-outside.tif"
NINE_DIR = ROOT / "data/research/nine_site_verify"
LIMIT = 0.70


def _dots(path: Path, footprint: np.ndarray) -> np.ndarray:
    with rasterio.open(path) as ds:
        a = ds.read(1)
    return np.isfinite(a) & (a > 0) & footprint


def local_tifs():
    seen = set()
    for pat in ("docs/downloads/**/*.tif", "inputs/**/*.tif"):
        for p in sorted(ROOT.glob(pat)):
            if p.is_file() and p not in seen:
                seen.add(p)
                yield p


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("candidate", type=Path)
    ap.add_argument("--receipt", type=Path, default=None)
    args = ap.parse_args()
    cand = args.candidate if args.candidate.is_absolute() else ROOT / args.candidate

    with rasterio.open(TEMPLATE) as t:
        template_profile = {"shape": t.shape, "transform": t.transform}
        footprint = np.isfinite(t.read(1))
    fmt, _ = format_check(cand, template_profile, footprint)
    cand_sha = sha256(cand)
    cand_dots = _dots(cand, footprint)
    n_dots = int(cand_dots.sum())

    # 2. byte identity against every local TIFF and the nine focus files
    exact = []
    comparators = {}
    for p in local_tifs():
        if p.resolve() in (cand.resolve(), LATTICE.resolve()):
            continue  # the lattice is reported once, as peer-lattice:GEMSDOE13
        comparators[str(p.relative_to(ROOT))] = p
    for site in SITES:
        p = NINE_DIR / f"{site}.tif"
        if p.exists():
            comparators[f"nine:{site}"] = p
    comparators["peer-lattice:GEMSDOE13"] = LATTICE

    hashes = {}
    for name, p in comparators.items():
        h = sha256(p)
        if h == cand_sha:
            exact.append(name)
        hashes[name] = h

    # 3a. overlap against every comparator (dots of candidate within 3 px of comparator dots)
    overlaps = {}
    for name, p in comparators.items():
        other = _dots(p, footprint)
        if other.sum() == 0:
            continue
        overlaps[name] = overlap_3px(cand_dots, other)
    ranked = sorted(overlaps.items(), key=lambda kv: kv[1], reverse=True)
    nine_max = max(((k, v) for k, v in overlaps.items() if k.startswith("nine:")), key=lambda kv: kv[1])
    lattice = overlaps.get("peer-lattice:GEMSDOE13")
    lattice_rel = str(LATTICE.relative_to(ROOT))
    other_max = max(
        ((k, v) for k, v in overlaps.items()
         if not k.startswith("nine:") and k not in ("peer-lattice:GEMSDOE13", lattice_rel)),
        key=lambda kv: kv[1], default=(None, None),
    )

    gate_format = bool(fmt["official_format_pass"])
    gate_exact = len(exact) == 0
    gate_nine = nine_max[1] <= LIMIT
    gate_all_other = bool(other_max[1] is None or other_max[1] <= LIMIT)
    gate_lattice = lattice is not None and lattice <= LIMIT

    receipt = {
        "schema": "candidate-tif-verify-v1",
        "candidate": str(cand.relative_to(ROOT)),
        "sha256": cand_sha,
        "bytes": cand.stat().st_size,
        "dot_count_in_footprint": n_dots,
        "format": fmt,
        "exact_duplicate_of": exact,
        "overlap_3px_max_vs_nine": {"site": nine_max[0], "fraction": round(nine_max[1], 6)},
        "overlap_3px_max_vs_other_local_tifs": {"file": other_max[0],
                                                "fraction": None if other_max[1] is None else round(other_max[1], 6)},
        "overlap_3px_vs_peer_lattice_GEMSDOE13": None if lattice is None else round(lattice, 6),
        "comparators_checked": len(comparators),
        "top5_overlaps": [[k, round(v, 6)] for k, v in ranked[:5]],
        "gates": {
            "official_format": gate_format,
            "no_exact_duplicate": gate_exact,
            "overlap_le_70pct_vs_nine": gate_nine,
            "overlap_le_70pct_vs_all_other_local_tifs": gate_all_other,
            "overlap_le_70pct_vs_peer_lattice_GEMSDOE13": gate_lattice,
        },
        "verdict_scope": "format and uniqueness receipt only; NOT an organizer score, NOT upload authorization",
    }
    receipt["all_gates_pass"] = all(receipt["gates"].values())
    out = args.receipt or ROOT / f"evidence/candidate_verify_{cand.stem}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, indent=2, allow_nan=False) + "\n")
    print(json.dumps({k: receipt[k] for k in ("sha256", "dot_count_in_footprint", "gates",
                                              "overlap_3px_max_vs_nine",
                                              "overlap_3px_max_vs_other_local_tifs",
                                              "overlap_3px_vs_peer_lattice_GEMSDOE13",
                                              "exact_duplicate_of", "comparators_checked")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
