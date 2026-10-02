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

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems import footprint, paths, submission  # noqa: E402
from gems.promotion import require_candidate_evidence, require_postprocess_evidence  # noqa: E402
from gems.thinning import dot_thin  # noqa: E402
from gems.validator import sha256_file  # noqa: E402

TEMPLATE = ROOT / "data/bridge/sample_submission.tif"
H19_5_SHA = "ec1f9b56b83ce33cad781ceb9f104b18fb4f2ff785263a4e89616af4aabdee8d"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source", type=Path)
    ap.add_argument("--hyp", default="h24-2a")
    ap.add_argument("--mirror-of", choices=["h19-5"], default=None)
    ap.add_argument(
        "--postprocess-of",
        choices=["h19-5"],
        default=None,
        help="label-free dot-thinning of the pinned H19-5 reference (new evidence rule)",
    )
    ap.add_argument("--validation", type=Path, default=ROOT / "evidence/dotting_validation.json")
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
    elif args.postprocess_of:
        validation = json.loads(args.validation.read_text())
        ref_path = next((ROOT / "inputs").glob("*h19-5*-nan.tif"))
        if sha256_file(ref_path) != H19_5_SHA:
            raise SystemExit("Pinned H19-5 reference differs from its recorded SHA-256")
        fp0 = footprint.load_footprint()
        known0 = footprint.load_band(ROOT / "data/bridge/existing_faults.tif") > 0
        with rasterio.open(ref_path) as d:
            ref_arr = d.read(1)
        with rasterio.open(source) as d:
            cand_arr = d.read(1)
        spacing = validation["selection_and_gates"]["selected_d"]
        expected = dot_thin((ref_arr > 0) & fp0 & ~known0, spacing)
        recomputed = bool(
            np.array_equal((cand_arr > 0) & fp0, expected) and np.isin(cand_arr[fp0], [0, 1]).all()
        )
        try:
            gate = require_postprocess_evidence(
                H19_5_SHA,
                digest,
                recomputed,
                validation,
                json.loads(args.audit_file.read_text()),
            )
        except (OSError, ValueError, KeyError) as exc:
            raise SystemExit(str(exc)) from exc
        gate["transform"] = {"name": "dot_thin", "min_dist_px": spacing, "reference": "h19-5"}
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
    if args.postprocess_of and args.hyp == "h24-2a":
        hyp = "h25-1-dotted-h19-5"
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
    default_summary = (
        "H19-5 dot-thinned to 44k px (label-free). Blocked holdout +27% rel on sparse truths; neutral at full density; unscored"
        if args.postprocess_of
        else "Held-out candidate with matched training-only nuisance removal and exact-raster re-audit"
    )
    summary = args.summary or (
        "H19-5 reference; original DTI 0.1922 reported by owner. Not a new prediction; do not spend a repeat slot."
        if args.mirror_of
        else default_summary
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
        "recommended_for_new_slot": (
            gate.get("slot_recommendation") == "eligible"
            if args.postprocess_of
            else not bool(args.mirror_of)
        ),
        "slot_recommendation": gate.get("slot_recommendation") if args.postprocess_of else None,
        "postprocess_of": args.postprocess_of,
        "strict_owner_audit_gate_passed": gate.get("strict_owner_audit_gate_passed"),
        "validation_file": str(args.validation.relative_to(ROOT)) if args.postprocess_of else None,
        "slot_spent": False,
        "note": note,
    }
    reg["submissions"].append(row)
    paths.REGISTRY_PATH.write_text(json.dumps(reg, indent=2) + "\n")
    target = "reference_download.json" if args.mirror_of else "download.json"
    (ROOT / "docs/data" / target).write_text(json.dumps(row, indent=2) + "\n")
    print(json.dumps(row, indent=2))


if __name__ == "__main__":
    main()
