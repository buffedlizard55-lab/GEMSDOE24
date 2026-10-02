#!/usr/bin/env python
"""Build the 24GEMSDOE submission bundle from a chosen (gate-passed) raster.

Emits into docs/downloads/ (served by GitHub Pages):
  gems24-<hyp>-<date>-<cid>-nan.tif        primary upload (NaN outside footprint)
  gems24-<hyp>-<date>-<cid>-allfinite.tif  fallback if the portal rejects NaN
  <same>.zip                                single-file zip, tif + note
  note-<stem>.txt                           short DrivenData note (<=200 chars)
  checks-<stem>.json                        check_variants() output, both files
Appends a registry/submissions.json entry with the DTI *holdout gate* result
from evidence/geoaudit.json when present (never invents live scores).
Usage: build_submission24.py <source.tif> --hyp h24-1-access-residualized [--mirror-of gems19-h19-5...]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems import footprint, paths, submission  # noqa: E402

TEMPLATE = paths.DATA_DIR / "bridge" / "sample_submission.tif"


def content_id(arr: np.ndarray, fp: np.ndarray, known: np.ndarray) -> str:
    # group convention (identical to 19GEMSDOE): content + mask hash, 8 hex
    return submission.scored_content_id(arr, fp, known.astype(np.uint8))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("source")
    ap.add_argument("--hyp", default="h24-1-access-residualized")
    ap.add_argument("--mirror-of", default="")
    args = ap.parse_args()
    src = Path(args.source)
    if not src.is_absolute():
        src = ROOT / src
    with rasterio.open(src) as d:
        arr = d.read(1).astype(np.float32)
        crs_ok = d.crs is None or str(d.crs).upper().replace("EPSG::", "EPSG:") == "EPSG:32611"
    if not crs_ok:
        raise SystemExit(f"refusing to build: unexpected CRS {d.crs}")
    fp = footprint.load_footprint()
    known = footprint.load_band(paths.DATA_DIR / "bridge" / "existing_faults.tif") > 0
    cid = content_id(np.nan_to_num(arr), fp, known)
    date = datetime.now(timezone.utc).strftime("%Y%m%d")
    dl = paths.DOWNLOADS_DIR
    dl.mkdir(parents=True, exist_ok=True)
    out_nan = dl / submission.make_filename("gems24", args.hyp, date, cid, "nan")
    out_all = dl / submission.make_filename("gems24", args.hyp, date, cid, "allfinite")
    submission.write_submission(np.nan_to_num(arr, nan=0.0), TEMPLATE, out_nan, outside="nan")
    submission.write_submission(np.nan_to_num(arr, nan=0.0), TEMPLATE, out_all, outside="zero")
    checks = {"nan": submission.check_variants(out_nan, TEMPLATE),
              "allfinite": submission.check_variants(out_all, TEMPLATE)}
    for v in checks.values():
        if not v.get("ok_to_upload", False):
            raise SystemExit(f"variant check failed: {v['hard_failures']}")
    note = submission.make_note(args.hyp,
                                f"{args.hyp}: accessibility-residualized emission "
                                f"({src.name[:40]})" + (f"; mirrors {args.mirror_of}" if args.mirror_of else ""),
                                cid)
    (dl / f"note-{out_nan.stem}.txt").write_text(note + "\n")
    zp = submission.zip_single(out_nan, dl / (out_nan.stem + ".zip"))
    j = dl / f"checks-{out_nan.stem}.json"
    j.write_text(json.dumps({"checks": checks, "note": note, "source": str(src),
                               "mirror_of": args.mirror_of}, indent=2))
    gate = {}
    ga = paths.EVIDENCE_DIR / "geoaudit.json"
    if ga.exists():
        g = json.loads(ga.read_text()).get("gate", {})
        gate = {k: v.get("dti") for k, v in g.items() if isinstance(v, dict)}
    reg_p = paths.REGISTRY_PATH
    reg = json.loads(reg_p.read_text()) if reg_p.exists() else {"submissions": []}
    reg["submissions"].append({
        "family": "gems24", "hypothesis": args.hyp, "content_id": cid, "date": date,
        "file": out_nan.name, "zip": zp.name, "sha256": hashlib.sha256(out_nan.read_bytes()).hexdigest()[:16],
        "holdout_gate_dti": gate, "mirror_of": args.mirror_of,
        "live_dti": None, "slot_spent": False,
        "note": note,
    })
    reg_p.parent.mkdir(parents=True, exist_ok=True)
    reg_p.write_text(json.dumps(reg, indent=2) + "\n")
    print(json.dumps({"tif": str(out_nan.relative_to(ROOT)), "zip": str(zp.relative_to(ROOT)),
                       "note": note, "gate": gate, "checks_ok": all(c.get("ok_to_upload") for c in checks.values())}, indent=2))


if __name__ == "__main__":
    main()
