#!/usr/bin/env python3
"""Directed 3-px dot-overlap scan of one candidate against every LOCAL same-grid raster.

Scope (stated in the receipt): this covers only the GeoTIFFs present in this
checkout (docs/downloads, inputs, evidence) that share the candidate's exact grid.
It is NOT a scan of the full 167-alias registry or of the other GEMSDOE repositories,
whose rasters are not all local. A pass here is therefore not a registry-wide pass.

Rule (owner brief): fail if more than 70% of the candidate's dots lie within 3 px of
one reference raster's dots. Reported as the forward direction (candidate -> reference),
which is the rule's direction; the reverse direction is recorded for transparency.
A reference whose dot mask is identical to the candidate's is an encoding alias
(e.g. -zeros vs -nan twin of the same prediction) and is reported separately, not as
a peer.

Writes evidence/unique_local_overlap_<stamp>.json. Read-only with respect to rasters.
"""

from __future__ import annotations

import argparse
import glob
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems.novelty import dot_overlap  # noqa: E402

LIMIT = 0.70
RADIUS_PX = 3.0


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dot_mask(path: Path) -> tuple[np.ndarray, tuple[int, int]]:
    with rasterio.open(path) as src:
        if src.count != 1:
            raise ValueError(f"{path} is not single-band")
        arr = src.read(1).astype(np.float64)
        shape = src.shape
    return np.isfinite(arr) & (arr > 0.5), shape


def scan(candidate: Path, stamp: str, out: Path) -> dict:
    cand, shape = dot_mask(candidate)
    if int(cand.sum()) == 0:
        raise ValueError("candidate has no dots; nothing to compare")
    candidate_sha = sha256(candidate)
    paths = sorted(
        {
            p
            for pattern in ("docs/downloads/*.tif", "inputs/**/*.tif", "evidence/**/*.tif")
            for p in glob.glob(str(ROOT / pattern), recursive=True)
        }
    )
    rows, aliases, skipped = [], [], []
    for p in map(Path, paths):
        if p.resolve() == candidate.resolve():
            continue
        try:
            ref, ref_shape = dot_mask(p)
        except Exception as exc:  # unreadable or multi-band: recorded, never silently dropped
            skipped.append({"file": p.relative_to(ROOT).as_posix(), "reason": str(exc)[:120]})
            continue
        if ref_shape != shape or int(ref.sum()) == 0:
            continue
        if np.array_equal(ref, cand):
            aliases.append(p.relative_to(ROOT).as_posix())
            continue
        ov = dot_overlap(cand, ref, radius_px=RADIUS_PX)
        rows.append(
            {
                "file": p.relative_to(ROOT).as_posix(),
                "sha256": sha256(p),
                "reference_dots": ov["reference_dots"],
                "candidate_within_3px_of_reference": ov["candidate_within_3px_of_reference"],
                "reference_within_3px_of_candidate": ov["reference_within_3px_of_candidate"],
            }
        )
    rows.sort(key=lambda r: r["candidate_within_3px_of_reference"], reverse=True)
    worst = rows[0] if rows else None
    receipt = {
        "schema": "unique-local-overlap-v1",
        "generated_utc": datetime.now(UTC).isoformat(),
        "candidate": candidate.relative_to(ROOT).as_posix(),
        "candidate_sha256": candidate_sha,
        "candidate_dots": int(cand.sum()),
        "rule": f"fail if candidate-within-3px-of-reference > {LIMIT} (directed, inclusive radius)",
        "scope": (
            "Local same-grid GeoTIFFs in this checkout only (docs/downloads, inputs, evidence). "
            "NOT the full 167-alias registry and NOT other GEMSDOE repositories."
        ),
        "references_compared": len(rows),
        "encoding_aliases_same_dots": aliases,
        "unreadable_skipped": skipped,
        "max_forward_overlap": worst["candidate_within_3px_of_reference"] if worst else None,
        "max_forward_reference": worst["file"] if worst else None,
        "passes_local_rule": bool(
            worst is None or worst["candidate_within_3px_of_reference"] <= LIMIT
        ),
        "top_references": rows[:12],
        "submission_authorized": False,
    }
    out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    return receipt


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("candidate", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    cand = args.candidate if args.candidate.is_absolute() else ROOT / args.candidate
    stamp = datetime.now(UTC).strftime("%Y%m%d")
    receipt = scan(cand, stamp, args.out if args.out.is_absolute() else ROOT / args.out)
    print(
        json.dumps(
            {
                k: receipt[k]
                for k in ("references_compared", "max_forward_overlap", "passes_local_rule")
            },
            indent=2,
        )
    )
    return 0 if receipt["passes_local_rule"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
