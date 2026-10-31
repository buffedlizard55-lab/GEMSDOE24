#!/usr/bin/env python3
"""Generate a *unique* research GeoTIFF by construction.

Method: score the geophysical concealed-conduit surface (GeoDAWN radiometrics +
magnetics + LiDAR scarp; the H1 hypothesis in knowledge/32_hypotheses_2026-10-31.md)
only inside pixels that lie OUTSIDE the 3 px neighborhood of every one of the nine
focus-site dots (GEMSDOE24/25/27/28/30/31/32/33/36).  Every emitted dot therefore has
directed 3-px overlap 0.0000 with each focus site - unique by construction, not by
post-hoc tuning.  Dots are placed with the shared deterministic priority_poisson over
the holdout-visible (catalogue-excluded) surface; no labels, no old predictions, no
registry rasters enter the score.

Packaged as a strict all-finite [0,1] single-band float32 GeoTIFF on the exact
template grid (EPSG:32611, 3730x3292 @100 m), zeros outside the footprint.

This is a RESEARCH artifact.  Verdict: SUBMIT: NO.  Reasons: (a) holdout DTI is not
expected to beat the recorded S3DEP1 point-best 0.166060 because dots are confined to
areas far from catalogue fault structure where the withheld positives live; (b) no
weekly-slot selector/quota is verified; (c) no organizer receipt exists.  The estimate
is NOT ESTIMABLE.  No submission slot is spent; the agent never uploads.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems import emission, footprint, holdout, submission  # noqa: E402
from gems.validator import sha256_file  # noqa: E402

TEMPLATE = ROOT / "data/bridge" / "sample_submission.tif"
LABELS = ROOT / "data/bridge" / "labels.tif"
EXT_RAD = ROOT / "data/external" / "geodawn_rad_u8.tif"
EXT_EXT = ROOT / "data/external" / "geodawn_extensions_u8.tif"
EXT_LIDAR = ROOT / "data/external" / "lidar_scarp_features_u8.tif"
NINE_DIR = ROOT / "data" / "research" / "nine_site_verify"
SITES = [
    "GEMSDOE24",
    "GEMSDOE25",
    "GEMSDOE27",
    "GEMSDOE28",
    "GEMSDOE30",
    "GEMSDOE31",
    "GEMSDOE32",
    "GEMSDOE33",
    "GEMSDOE36",
]
DOWNLOADS = ROOT / "docs" / "downloads"
DOWNLOADS.mkdir(parents=True, exist_ok=True)

RAD_BANDS = ("K", "Th", "U", "TC")
EXT_BANDS = ("ThK", "UK", "UTh", "TMI_up150")
LIDAR_BANDS = ("ex_max", "ex_mean", "step_max", "lapneg_max", "lappoS_max", "downface_max",
               "upface_max", "cross_max", "relief", "coh100", "strike", "valid")
BUDGET_DOTS = 10000
MIN_DIST_PX = 3.0
RADIUS_PX = 3.0


def load_u8(path):
    with rasterio.open(path) as s:
        a = s.read(1).astype(np.float32)
        if s.nodata is not None:
            a = np.where(a == s.nodata, np.nan, a)
    return a


def edge_of(grid):
    from scipy.ndimage import gaussian_filter, sobel
    g = np.where(np.isfinite(grid) & (grid > 0), grid, 0.0).astype(np.float32)
    gx = sobel(g, axis=1, mode="nearest")
    gy = sobel(g, axis=0, mode="nearest")
    return gaussian_filter(np.hypot(gx, gy), 1.0)


def build_surface(fp, tmi_up150, k, th, u, tc, thk, uk, uth,
                  step_max, upface_max, downface_max, cross_max, lidar_valid):
    surf = np.zeros(fp.shape, dtype=np.float32)
    for name, grid in (("tmi", tmi_up150), ("K", k), ("Th", th), ("U", u)):
        surf = np.where(fp & np.isfinite(grid), surf + edge_of(grid), surf)
    ok = np.isfinite(thk) & np.isfinite(uk)
    surf = np.where(fp & ok, surf + 0.5 * (255.0 - np.minimum(thk, uk)), surf)
    surf = np.where(fp & np.isfinite(tc) & (tc > 0), surf + 0.3 * tc, surf)
    lid_ok = np.isfinite(lidar_valid) & (lidar_valid > 0)
    scarp = (0.4 * step_max + 0.3 * upface_max + 0.3 * downface_max + 0.2 * cross_max)
    surf = np.where(fp & lid_ok, surf + scarp, surf)
    vals = surf[fp][np.isfinite(surf[fp])]
    if vals.size and vals.max() > vals.min():
        surf = (surf - vals.min()) / (vals.max() - vals.min())
    surf = np.clip(surf, 0.0, 1.0)
    surf = np.where(fp, np.nan_to_num(surf, nan=0.0), np.nan)
    return surf


def save(obj, path):
    Path(path).write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--budget", type=int, default=BUDGET_DOTS)
    args = ap.parse_args()
    started = time.monotonic()

    fp = footprint.load_footprint()
    with rasterio.open(LABELS) as s:
        catalogue = (s.read(1) > 0) & fp

    # --- Uniqueness mask: outside the 3 px neighborhood of every focus-site dot ---
    union = np.zeros(fp.shape, bool)
    dot_counts = {}
    for s in SITES:
        with rasterio.open(NINE_DIR / f"{s}.tif") as ds:
            a = ds.read(1)
        m = np.isfinite(a) & (a > 0) & fp
        dot_counts[s] = int(m.sum())
        union |= m
    dist = distance_transform_edt(~union)
    uncovered = fp & (dist > RADIUS_PX)
    print("footprint px", int(fp.sum()), "union dots", int(union.sum()),
          "uncovered px", int(uncovered.sum()), flush=True)
    if not uncovered.any() or args.budget > int(uncovered.sum()):
        raise SystemExit("Uncovered area too small for the requested budget")

    # --- Surface from committed external grids ---
    with rasterio.open(EXT_RAD) as s:
        rad = {name: s.read(i + 1).astype(np.float32)
               for i, name in enumerate(RAD_BANDS)}
    with rasterio.open(EXT_EXT) as s:
        ext = {name: s.read(i + 1).astype(np.float32)
               for i, name in enumerate(EXT_BANDS)}
    with rasterio.open(EXT_LIDAR) as s:
        lidar = {name: s.read(i + 1).astype(np.float32)
                 for i, name in enumerate(LIDAR_BANDS)}
    for d in (rad, ext, lidar):
        for name, a in d.items():
            d[name] = np.where(a == 0, np.nan, a)
    surface = build_surface(
        fp, ext["TMI_up150"], rad["K"], rad["Th"], rad["U"], rad["TC"],
        ext["ThK"], ext["UK"], ext["UTh"],
        lidar["step_max"], lidar["upface_max"], lidar["downface_max"],
        lidar["cross_max"], lidar["valid"],
    )
    surface = np.where(uncovered, surface, 0.0)

    # --- Leakage canary on component surfaces ---
    ctx = holdout.SegmentHoldout(fp, catalogue, buffer_px=15)
    canary_features = {
        "tmi_edge": np.where(fp, edge_of(ext["TMI_up150"]), 0.0).astype(np.float32),
        "K_edge": np.where(fp, edge_of(rad["K"]), 0.0).astype(np.float32),
        "Th_edge": np.where(fp, edge_of(rad["Th"]), 0.0).astype(np.float32),
        "U_edge": np.where(fp, edge_of(rad["U"]), 0.0).astype(np.float32),
        "TC": np.where(fp, rad["TC"], 0.0).astype(np.float32),
        "lidar_scarp": np.where(
            fp,
            (0.4 * lidar["step_max"] + 0.3 * lidar["upface_max"] +
             0.3 * lidar["downface_max"] + 0.2 * lidar["cross_max"]).astype(np.float32),
            0.0,
        ),
    }
    canary = ctx.canary(canary_features)
    print("Canary worst AUC:", canary["worst_pooled_auc"], "passed:", canary["passed"], flush=True)
    if not canary["passed"]:
        raise SystemExit("Leakage canary failed")

    # --- Holdout: dots restricted to uncovered, off-catalogue pixels ---
    predictions = []
    for f in ctx.folds:
        eligible = fp & f["valid"] & ~catalogue & uncovered
        n_eligible = int(eligible.sum())
        budget = min(args.budget // len(ctx.folds), n_eligible)
        pred = emission.priority_poisson(surface, eligible, budget, min_dist=MIN_DIST_PX)
        predictions.append(pred)
        print(f"Fold {f['name']}: eligible={n_eligible:,} emitted={int(pred.sum())} dots", flush=True)
    results = ctx.summarize(predictions)
    print("Holdout DTI:", results["dti"], results["ci95"]["interval"], flush=True)

    # --- Final dots ---
    final_eligible = fp & ~catalogue & uncovered
    final_budget = min(args.budget, int(final_eligible.sum()))
    final = emission.priority_poisson(surface, final_eligible, final_budget,
                                      min_dist=MIN_DIST_PX)
    if not final.any():
        raise SystemExit("No dots placed; refusing empty submission")

    # --- Verify uniqueness vs each focus site ---
    from gems.novelty import dot_overlap
    overlaps = {}
    for s in SITES:
        with rasterio.open(NINE_DIR / f"{s}.tif") as ds:
            a = ds.read(1)
        ref = np.isfinite(a) & (a > 0) & fp
        overlaps[s] = dot_overlap(final, ref)["candidate_within_3px_of_reference"]

    # --- Package ---
    content_id = submission.scored_content_id(final, fp, catalogue)
    name = submission.make_filename(
        "GEMSDOE24", f"unique-complement-{args.budget}dots", "20261031",
        content_id, "zeros",
    )
    zeros_path = submission.write_submission(final, TEMPLATE, DOWNLOADS / name,
                                             outside="zero")
    nan_name = name.replace("-zeros.tif", "-nan.tif")
    nan_path = submission.write_submission(final, TEMPLATE, DOWNLOADS / nan_name,
                                           outside="nan")
    checks = {
        "zero_outside": submission.check_variants(zeros_path, TEMPLATE, strict=True),
        "nan_outside": submission.check_variants(nan_path, TEMPLATE, strict=True),
    }
    if not all(c["format_valid"] for c in checks.values()):
        raise SystemExit("Format checks failed; do not publish")

    note = submission.make_note(
        "UNIQUE-COMPLEMENT",
        f"{args.budget} dots outside all nine focus-site 3px neighborhoods; geophysics-scored",
        content_id, family="GEMSDOE24",
    )
    if len(note) > 140:
        raise AssertionError("Note exceeds 140 characters")
    (DOWNLOADS / f"note-{name[:-4]}.txt").write_text(note + "\n")
    save(checks, DOWNLOADS / f"checks-{name[:-4]}.json")

    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "hypothesis": ("A dot set confined to the complement of the 3 px neighborhoods of "
                       "all nine focus-site submissions is unique by construction; scored by "
                       "concealed-conduit geophysical propensity."),
        "mechanism": ("GeoDAWN TMI/K/Th/U/TC edges + Th/K depletion + LiDAR scarp score, "
                      "restricted to uncovered footprint pixels; deterministic priority-Poisson dots."),
        "non_fault_mimic": "Alluvial/terrace steps and road cut/fill corridors in geophysically quiet areas.",
        "inputs": {str(p.relative_to(ROOT)): sha256_file(p)
                   for p in (TEMPLATE, LABELS, EXT_RAD, EXT_EXT, EXT_LIDAR)}
        | {str(NINE_DIR / f"{s}.tif"): sha256_file(NINE_DIR / f"{s}.tif") for s in SITES},
        "code_sha256": {str(p.relative_to(ROOT)): sha256_file(p)
                        for p in (Path(__file__), ROOT / "src/gems/holdout.py",
                                  ROOT / "src/gems/metric.py", ROOT / "src/gems/emission.py",
                                  ROOT / "src/gems/submission.py")},
        "catalogue_features": [],
        "prediction_inputs_include_registry_rasters": False,
        "supervised_fit": False,
        "submission_slot_spent": False,
        "organizer_confirmed_score": None,
        "canary": canary,
        "results": results,
        "uncovered_pixels": int(uncovered.sum()),
        "budget": args.budget,
        "focus_site_overlaps": overlaps,
    }
    report.update({
        "verdict": "negative",
        "verdict_reasons": [
            "Holdout DTI not expected to beat recorded S3DEP1 point-best 0.166060",
            "No separate weekly-slot selector or quota verification",
            "No organizer receipt; estimate NOT ESTIMABLE",
        ],
        "pixel_count": int(final.sum()),
        "filename": name,
        "nan_filename": nan_name,
        "raster_sha256": sha256_file(zeros_path),
        "scored_content_id": content_id,
        "note": note,
        "note_file": f"note-{name[:-4]}.txt",
        "checks_file": f"checks-{name[:-4]}.json",
        "validator": checks,
        "elapsed_seconds": time.monotonic() - started,
    })
    save(report, ROOT / "evidence/unique_complement_experiment.json")
    save(report, ROOT / "docs/data/unique_complement_experiment.json")

    card = {
        "hypothesis": report["hypothesis"],
        "mechanism": report["mechanism"],
        "non_fault_mimic": report["non_fault_mimic"],
        "holdout": {
            "label": "HOLDOUT-DTI",
            "evaluator_version": holdout.MTR_EVALUATOR_VERSION,
            "dti": results["dti"],
            "ci95": results["ci95"]["interval"],
            "n_withheld_positive_pixels": results["n_truth"],
            "n_emitted": int(final.sum()),
        },
        "correlation_overlap_vs_registry": {
            "unique_registry_rasters": 0,
            "note": "Uniqueness by construction: 0.0000 directed 3-px overlap with each of the nine focus sites",
            "focus_site_overlaps": overlaps,
            "all_zero": all(v == 0.0 for v in overlaps.values()),
        },
        "raster_sha256": report["raster_sha256"],
        "validator_output": checks["zero_outside"],
        "submission_name": name,
        "note": note,
        "verdict": "negative",
        "ok_to_download": True,
        "ok_to_submit": False,
        "organizer_confirmed_score": None,
        "experiments_run": 1,
        "submission_slots_used": 0,
    }
    save(card, ROOT / "evidence/unique_complement_run_card.json")
    save(card, ROOT / "docs/data/unique_complement_run_card.json")

    download = {
        "file": name,
        "nan_file": nan_name,
        "sha256": report["raster_sha256"],
        "content_id": content_id,
        "pixel_count": int(final.sum()),
        "note": note,
        "note_file": f"note-{name[:-4]}.txt",
        "checks_file": f"checks-{name[:-4]}.json",
        "role": "unique-research",
        "format_valid": True,
        "ok_to_download": True,
        "ok_to_submit": False,
        "recommended_for_new_slot": False,
        "slot_recommendation": "not_recommended",
        "verdict": "negative",
        "holdout_dti": results["dti"],
        "holdout_ci95": results["ci95"]["interval"],
        "run_card": "unique_complement_run_card.json",
    }
    save(download, ROOT / "docs/data/unique_complement_download.json")

    print(json.dumps({
        "file": name,
        "pixels": int(final.sum()),
        "sha256": report["raster_sha256"],
        "holdout_dti": results["dti"],
        "holdout_ci95": results["ci95"]["interval"],
        "overlaps_vs_nine": overlaps,
        "note_characters": len(note),
        "verdict": "negative",
        "ok_to_submit": False,
    }, indent=2), flush=True)


if __name__ == "__main__":
    main()
