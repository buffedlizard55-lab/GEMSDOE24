#!/usr/bin/env python3
"""Package a slot-eligible candidate OR the exact known H19-5 reference.

Format validation never replaces scientific gates. ZIP contains ONE .tif; the
<=200-character comment is a separate file. No portal uploads are performed.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems import footprint, paths, submission  # noqa: E402
from gems.promotion import require_candidate_evidence  # noqa: E402
from gems.validator import sha256_file  # noqa: E402

TEMPLATE = ROOT / "data/bridge/sample_submission.tif"
H19_5_SHA = "ec1f9b56b83ce33cad781ceb9f104b18fb4f2ff785263a4e89616af4aabdee8d"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source", type=Path)
    ap.add_argument("--hyp", default="h24-2a")
    ap.add_argument("--mirror-of", choices=["h19-5"], default=None)
    ap.add_argument("--summary", default="")
    ap.add_argument("--gate-file", type=Path, default=ROOT / "evidence/h24_2_experiment.json")
    ap.add_argument(
        "--audit-file", type=Path, default=ROOT / "evidence/accessibility_audit_v2.json"
    )
    args = ap.parse_args()
    source = args.source.resolve()
    digest = sha256_file(source)
    if args.mirror_of:
        if digest != H19_5_SHA:
            raise SystemExit(
                "Reference bypass is allowed ONLY for the pinned H19-5 artifact, not an arbitrary raster"
            )
        gate = {
            "passed": False,
            "reason": "Reference only; renaming does not create a new prediction or justify another slot",
        }
    else:
        try:
            gate = require_candidate_evidence(
                digest,
                json.loads(args.gate_file.read_text()),
                json.loads(args.audit_file.read_text()),
            )
        except (OSError, ValueError, KeyError) as exc:
            raise SystemExit(str(exc)) from exc
    source_checks = submission.check_variants(source, TEMPLATE)
    if not source_checks["format_valid"]:
        raise SystemExit(
            "Source raster format failed: " + ", ".join(source_checks["hard_failures"])
        )
    with rasterio.open(source) as d:
        arr = d.read(1)
    fp = footprint.load_footprint()
    known = footprint.load_band(ROOT / "data/bridge/existing_faults.tif") > 0
    cid = submission.scored_content_id(arr, fp, known)
    date = datetime.now(timezone.utc).strftime("%Y%m%d")
    hyp = "reference-h19-5" if args.mirror_of else args.hyp
    dl = paths.DOWNLOADS_DIR
    dl.mkdir(parents=True, exist_ok=True)
    primary = dl / submission.make_filename("gems24", hyp, date, cid, "nan")
    fallback = dl / submission.make_filename("gems24", hyp, date, cid, "allfinite")
    submission.write_submission(arr, TEMPLATE, primary, outside="nan")
    submission.write_submission(arr, TEMPLATE, fallback, outside="zero")
    checks = {
        "nan": submission.check_variants(primary, TEMPLATE),
        "allfinite": submission.check_variants(fallback, TEMPLATE),
    }
    if not all(c["format_valid"] for c in checks.values()):
        raise SystemExit("Packaged raster failed range/grid/band validation")
    with rasterio.open(primary) as d:
        if submission.scored_content_id(d.read(1), fp, known) != cid:
            raise SystemExit("Packaging changed scored predictions")
    summary = args.summary or (
        "H19-5 reference; original DTI 0.1922 reported by owner. Not a new prediction; do not spend a repeat slot."
        if args.mirror_of
        else "Held-out candidate with matched training-only nuisance removal and exact-raster re-audit"
    )
    note = submission.make_note(hyp, summary, cid, reference=bool(args.mirror_of))
    note_path = dl / ("note-" + primary.stem + ".txt")
    note_path.write_text(note + "\n")
    archive = submission.zip_single(primary)
    receipt = {
        "checks": checks,
        "note": note,
        "source": str(source.relative_to(ROOT)),
        "source_sha256": digest,
        "mirror_of": args.mirror_of,
        "promotion_gate": gate,
        "same_scored_content_verified": True,
    }
    checks_path = dl / ("checks-" + primary.stem + ".json")
    checks_path.write_text(json.dumps(receipt, indent=2) + "\n")
    reg = (
        json.loads(paths.REGISTRY_PATH.read_text())
        if paths.REGISTRY_PATH.exists()
        else {"submissions": []}
    )
    reg["submissions"] = [s for s in reg.get("submissions", []) if s.get("file") != primary.name]
    row = {
        "family": "gems24",
        "hypothesis": hyp,
        "date": date,
        "content_id": cid,
        "content_id_algorithm": "scored-float32-v2",
        "file": primary.name,
        "fallback": fallback.name,
        "zip": archive.name,
        "note_file": note_path.name,
        "checks_file": checks_path.name,
        "sha256": sha256_file(primary),
        "mirror_of": args.mirror_of,
        "live_dti": None,
        "original_reported_dti": 0.1922 if args.mirror_of else None,
        "score_evidence": "owner report" if args.mirror_of else None,
        "recommended_for_new_slot": not bool(args.mirror_of),
        "slot_spent": False,
        "note": note,
    }
    reg["submissions"].append(row)
    paths.REGISTRY_PATH.write_text(json.dumps(reg, indent=2) + "\n")
    (ROOT / "docs/data/download.json").write_text(json.dumps(row, indent=2) + "\n")
    print(json.dumps(row, indent=2))


if __name__ == "__main__":
    main()
