#!/usr/bin/env python3
"""Build a UNIQUE GEMS submission GeoTIFF — catalogue-blind upwelling conduit.

Hypothesis (H-BLIND-UPWELL-01): Blind hydrothermal upwelling conduits.
Geothermal fluids leach mobile Uranium relative to immobile Thorium (low U/Th),
demagnetise host rock (TMI upward-continuation gradient halo), and express as
subtle base-concave scarps (LiDAR lapneg_max). The USGS/INGENIOUS catalogue
maps only well-expressed surface traces; concealed conduits below the mapping
threshold are absent. This detector does NOT condition on any catalogue fault
to build its score surface, so it can score blind conduits missing from the
catalogue.

Layers:
  * geodawn_rad_u8.tif        -> U, Th  (U/Th depletion = hydrothermal leaching)
  * geodawn_extensions_u8.tif -> TMI_up150 (demagnetisation halo via gradient)
  * lidar_scarp_features_u8.tif -> lapneg_max (crest convexity / base concavity)
  * labels / existing_faults  -> catalogue mask (holdout masking only; never used
    to build the score surface)

Mechanism: low U/Th x demagnetisation x scarp-convexity emits sparse dots via
priority_poisson, restricted to catalogue-blind support.

Non-fault mimic: K-rich alluvial-fan toes, gravel pits and road cut/fill can
produce low-U/Th + steep-slope coincidences.

Protocol: SegmentHoldout hide-and-recover (buffer 15 px), pooled DTI
(alpha 0.2, beta 0.8, 300 m triangular kernel), per-channel leakage canary,
local dot-overlap novelty vs downloaded sibling TIFFs, exact-grid float32
GeoTIFF with zeros outside the footprint (finite [0,1] everywhere — addresses
the "[0, 1]" portal rejection).

Outputs:
  docs/downloads/24gems-blind-upwell-conduit-<date>-<content_id>-zeros.tif
  docs/downloads/checks-*.json, note-*.txt, preflight-*.json
  evidence/blind_upwell_experiment.json
  docs/data/blind_upwell_run_card.json, blind_upwell_download.json

Verdict set by gates. No upload occurs.
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
from scipy.ndimage import distance_transform_edt, gaussian_filter, sobel

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems import emission, footprint, holdout, submission  # noqa: E402
from gems.preflight import preflight  # noqa: E402
from gems.validator import sha256_file  # noqa: E402

TEMPLATE = ROOT / "data/bridge/sample_submission.tif"
LABELS = ROOT / "data/bridge/labels.tif"
EXISTING = ROOT / "data/bridge/existing_faults.tif"
LIDAR = ROOT / "data/external/lidar_scarp_features_u8.tif"
RAD = ROOT / "data/external/geodawn_rad_u8.tif"
EXT = ROOT / "data/external/geodawn_extensions_u8.tif"

BUDGET_FRACTION = 0.0073  # ~0.73% of footprint pixels as dots
MIN_DIST_PX = 3.0
RESULT = ROOT / "evidence/blind_upwell_experiment.json"
DOWNLOADS = ROOT / "docs/downloads"
DATA_OUT = ROOT / "docs/data"
LOCAL_COMPARATORS = ROOT / "docs/downloads"


def save(obj, path):
    Path(path).write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n")


def read_u8(path, band):
    with rasterio.open(path) as ds:
        return ds.read(band).astype(np.float32)


def norm01(a, mask):
    v = np.where(mask & np.isfinite(a), a, np.nan)
    lo, hi = np.nanpercentile(v, 2), np.nanpercentile(v, 98)
    if not (np.isfinite(lo) and np.isfinite(hi)) or hi <= lo:
        return np.zeros_like(a)
    out = np.clip((a - lo) / (hi - lo), 0.0, 1.0)
    out[~mask] = 0.0
    return out


def build_score_surface(fp):
    """Catalogue-blind score surface: U/Th depletion x demagnetisation x scarp."""
    with rasterio.open(TEMPLATE) as t:
        t_shape = t.shape
        t_fp = np.isfinite(t.read(1))

    lidar_valid = read_u8(LIDAR, 12) > 0
    lapneg = read_u8(LIDAR, 5)  # lapneg_max
    u_band = read_u8(RAD, 3)  # U
    th_band = read_u8(RAD, 2)  # Th
    tmi_up = read_u8(EXT, 4)  # TMI_up150

    for name, arr in (("lapneg", lapneg), ("u", u_band), ("th", th_band), ("tmi_up", tmi_up)):
        if arr.shape != t_shape:
            raise SystemExit(f"{name} shape {arr.shape} != template {t_shape}")

    # U/Th depletion: low U/Th = mobile U leached by hydrothermal fluids.
    with np.errstate(divide="ignore", invalid="ignore"):
        uth = np.where((th_band > 0) & lidar_valid, u_band / np.maximum(th_band, 1), np.nan)
    uth_valid = lidar_valid & np.isfinite(uth)
    uth_depletion = 1.0 - norm01(uth, uth_valid)  # low ratio -> high score

    # Demagnetisation halo: gradient of upward-continued TMI.
    tmi_fill = tmi_up.astype(np.float64)
    valid_tmi = lidar_valid & (tmi_up > 0)
    if not valid_tmi.any():
        tmi_grad = np.zeros_like(tmi_up)
    else:
        inds = distance_transform_edt(~valid_tmi, return_distances=False, return_indices=True)
        tmi_filled = tmi_fill[tuple(inds)]
        gx = sobel(gaussian_filter(tmi_filled, 2), axis=1)
        gy = sobel(gaussian_filter(tmi_filled, 2), axis=0)
        tmi_grad = np.hypot(gx, gy)
        tmi_grad[~valid_tmi] = np.nan
    tmi_grad_n = norm01(tmi_grad, valid_tmi)

    # Scarp base concavity / crest convexity.
    lapneg_n = norm01(lapneg, lidar_valid)

    score = uth_depletion * tmi_grad_n * lapneg_n
    support = fp & lidar_valid & uth_valid & valid_tmi & t_fp
    score = np.where(support, score, 0.0).astype(np.float32)
    return (
        score,
        support,
        {"uth_depletion": uth_depletion, "tmi_grad": tmi_grad_n, "lapneg": lapneg_n},
    )


def novelty_vs_local(comparator_tifs, fp, dots):
    """Local novelty: 3px dot overlap vs sibling TIFFs (candidate -> comparator)."""
    from scipy.spatial import cKDTree

    results = []
    cp = np.argwhere(dots)
    for path in comparator_tifs:
        try:
            with rasterio.open(path) as ds:
                ref = ds.read(1).astype(np.float32)
                ref_fp = np.isfinite(ref)
        except Exception as exc:  # noqa: BLE001
            results.append({"file": path.name, "error": str(exc), "duplicate": None})
            continue
        if ref.shape != fp.shape or not np.array_equal(ref_fp, fp):
            results.append({"file": path.name, "skipped": "grid/footprint mismatch"})
            continue
        ref_dots = np.isfinite(ref) & (ref > 0) & fp
        rp = np.argwhere(ref_dots)
        if len(cp) and len(rp):
            forward = float(np.mean(cKDTree(rp).query(cp)[0] <= 3.0))
        else:
            forward = 0.0
        results.append(
            {
                "file": path.name,
                "comparator_dots": int(rp.sum()),
                "dots_within_3px": forward,
                "overlap_gt_70": forward > 0.70,
            }
        )
    return results


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--verify-recorded",
        action="store_true",
        help="Inspect recorded evidence; do not run a new experiment",
    )
    args = ap.parse_args()

    if args.verify_recorded:
        if RESULT.exists():
            print(RESULT.read_text())
        else:
            print(json.dumps({"status": "no_recorded_experiment"}))
        return

    started = time.monotonic()
    fp = footprint.load_footprint()
    with rasterio.open(LABELS) as s:
        catalogue = (s.read(1) > 0) & fp
    score, support, channels = build_score_surface(fp)
    print(f"Support pixels: {int(support.sum()):,}", flush=True)
    print(f"Score>0 pixels: {int((score > 0).sum()):,}", flush=True)

    # ---- Holdout context ----
    context = holdout.SegmentHoldout(fp, catalogue, buffer_px=15)

    # ---- Leakage canary: each channel alone ----
    canary_features = {
        "uth_depletion": channels["uth_depletion"],
        "tmi_gradient": channels["tmi_grad"],
        "lapneg_scarp": channels["lapneg"],
        "score_surface": score,
    }
    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "hypothesis": (
            "H-BLIND-UPWELL-01 blind hydrothermal upwelling: U/Th depletion x "
            "TMI-up150 demagnetisation gradient x LiDAR lapneg scarp convexity"
        ),
        "mechanism": (
            "Mobile-U leaching (low U/Th), demagnetisation halo and subtle "
            "base-concave scarps mark concealed conduits absent from the "
            "USGS/INGENIOUS catalogue; score is catalogue-blind"
        ),
        "non_fault_mimic": "K-rich alluvial-fan toes, gravel pits and road cut/fill",
        "experiment_number": 1,
        "maximum_experiments": 3,
        "maximum_session_hours": 2,
        "input_provenance": (
            "Committed external mirrors (USGS GeoDAWN DOI 10.5066/P93LGLVQ, 3DEP LiDAR derivatives)"
        ),
        "inputs": {
            str(p.relative_to(ROOT)): sha256_file(p)
            for p in (TEMPLATE, LABELS, EXISTING, LIDAR, RAD, EXT)
        },
        "code_sha256": {
            str(p.relative_to(ROOT)): sha256_file(p)
            for p in (
                Path(__file__),
                ROOT / "src/gems/holdout.py",
                ROOT / "src/gems/metric.py",
                ROOT / "src/gems/emission.py",
                ROOT / "src/gems/novelty.py",
                ROOT / "src/gems/submission.py",
            )
        },
        "supported_pixels": int(support.sum()),
        "catalogue_features": [],
        "prediction_inputs_include_registry_rasters": False,
        "supervised_fit": False,
        "submission_slot_spent": False,
        "organizer_confirmed_score": None,
        "lane_status": "new lane: catalogue-blind upwelling conduit detector",
    }

    report["fold_integrity"] = [
        {
            "name": f["name"],
            "withheld_positive_pixels": int(f["truth"].sum()),
            "hidden_whole_components": len(f["hidden_component_ids"]),
            "visible_fault_pixels": int(f["visible"].sum()),
            "train_validation_overlap": bool((f["train"] & f["valid"]).any()),
        }
        for f in context.folds
    ]

    report["canary"] = context.canary(canary_features)
    if not report["canary"]["passed"]:
        report.update(
            verdict="negative",
            stopped_reason="leakage-canary",
            elapsed_seconds=time.monotonic() - started,
        )
        save(report, RESULT)
        raise SystemExit("Leakage canary failed; no candidate packaged")
    print("Canaries passed", flush=True)

    # ---- Per-fold holdout predictions (catalogue-blind dots) ----
    predictions = []
    for f in context.folds:
        eligible = support & f["valid"] & ~f["visible"]
        budget = round(BUDGET_FRACTION * f["valid"].sum())
        pred = emission.priority_poisson(score, eligible, budget, min_dist=MIN_DIST_PX)
        predictions.append(pred)

    results = context.summarize(predictions)
    report["holdout"] = results
    print(f"HOLDOUT-DTI {results['dti']} CI {results['ci95']['interval']}", flush=True)

    # ---- Final dots on full support, excluding catalogue ----
    final = emission.priority_poisson(
        score, support & ~catalogue, round(BUDGET_FRACTION * fp.sum()), min_dist=MIN_DIST_PX
    )
    if not final.any():
        raise SystemExit("No positive evidence; refusing an empty submission")

    # ---- Local novelty on final dots vs sibling TIFFs ----
    comparators = sorted(LOCAL_COMPARATORS.glob("*.tif"))
    dot_novelty = novelty_vs_local(comparators, fp, final)
    max_overlap = max(
        (
            r.get("dots_within_3px", 0.0)
            for r in dot_novelty
            if isinstance(r.get("dots_within_3px"), (int, float))
        ),
        default=0.0,
    )
    report["final_novelty_local"] = {
        "n_comparators": len(comparators),
        "max_dot_overlap": max_overlap,
        "comparators": dot_novelty,
    }
    novelty_pass = max_overlap <= 0.70
    print(
        f"Final dots novelty (max local dot overlap): {max_overlap:.4f} pass={novelty_pass}",
        flush=True,
    )

    # ---- Package TIF (zeros outside = finite [0,1] everywhere) ----
    content_id = submission.scored_content_id(final, fp, catalogue)
    date_str = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    name = submission.make_filename("24gems", "blind-upwell-conduit", date_str, content_id, "zeros")

    zeros_path = DOWNLOADS / name
    zeros = submission.write_submission(final, TEMPLATE, zeros_path, outside="zero")
    checks = submission.check_variants(zeros, TEMPLATE)
    if not checks["format_valid"]:
        raise SystemExit("Exact-file format checks failed; do not publish")

    note = (
        f"24GEMS blind-upwell U/Thxdemagxscarp | catalogue-blind | "
        f"research; HOLDOUT-DTI {results['dti']:.5f} | id {content_id}"
    )
    if len(note) > 140:
        note = note[:137] + "..."
    note_file = f"note-{name[:-4]}.txt"
    (DOWNLOADS / note_file).write_text(note + "\n")

    checks_file = f"checks-{name[:-4]}.json"
    save(checks, DOWNLOADS / checks_file)
    raster_sha256 = sha256_file(zeros)

    preflight_report = preflight(
        zeros,
        TEMPLATE,
        run_card_path=None,
        note=note,
        expected_template_sha256=sha256_file(TEMPLATE),
    )
    preflight_file = f"preflight-{name[:-4]}.json"
    save(preflight_report, DOWNLOADS / preflight_file)

    # ---- Zip twin ----
    zip_path = submission.zip_single(zeros, DOWNLOADS / (name[:-4] + ".zip"))

    beats_current_best = results["dti"] > 0.13000
    ok_to_submit = (
        checks["format_valid"]
        and checks["checks"]["variant_strict_whole_array_no_nan_allowed"]["pass"]
        and novelty_pass
        and report["canary"]["passed"]
        and beats_current_best
    )
    verdict = "promote" if ok_to_submit else "negative"

    card = {
        "hypothesis": report["hypothesis"],
        "mechanism": report["mechanism"],
        "non_fault_mimic": report["non_fault_mimic"],
        "holdout": {
            "evaluator_version": results["evaluator_version"],
            "dti": results["dti"],
            "ci95": results["ci95"]["interval"],
            "n_withheld_positive_pixels": results["n_withheld_positive_pixels"],
            "protocol": results["protocol"],
        },
        "novelty_local": report["final_novelty_local"],
        "leakage_canary": {
            "passed": report["canary"]["passed"],
            "threshold": report["canary"]["threshold"],
            "features": {k: v["pooled_auc"] for k, v in report["canary"]["features"].items()},
        },
        "raster_sha256": raster_sha256,
        "validator_output": checks,
        "preflight": preflight_report["decision"],
        "submission_name": name,
        "note": note,
        "note_characters": len(note),
        "note_limit": 140,
        "verdict": verdict,
        "ok_to_download": checks["format_valid"],
        "ok_to_submit": ok_to_submit,
        "reasons": (
            []
            if ok_to_submit
            else (
                ["holdout DTI does not beat current comparable best 0.13000"]
                if not beats_current_best
                else []
            )
            + (["format or range check failed"] if not checks["format_valid"] else [])
            + (["novelty gate failed"] if not novelty_pass else [])
            + (["canary failed"] if not report["canary"]["passed"] else [])
        ),
        "organizer_confirmed_score": None,
        "experiments_run": 1,
        "submission_slots_used": 0,
        "elapsed_seconds": time.monotonic() - started,
    }
    save(card, RESULT)
    save(card, DATA_OUT / "blind_upwell_run_card.json")

    download_entry = {
        "file": name,
        "sha256": raster_sha256,
        "content_id": content_id,
        "pixel_count": int(final.sum()),
        "note": note,
        "note_file": note_file,
        "checks_file": checks_file,
        "preflight_file": preflight_file,
        "zip_file": zip_path.name,
        "role": "primary",
        "format_valid": checks["format_valid"],
        "strict_range_ok": checks["checks"]["variant_strict_whole_array_no_nan_allowed"]["pass"],
        "ok_to_download": checks["format_valid"],
        "ok_to_submit": ok_to_submit,
        "verdict": verdict,
        "holdout_dti": results["dti"],
        "run_card": "blind_upwell_run_card.json",
    }
    save(download_entry, DATA_OUT / "blind_upwell_download.json")
    print(
        json.dumps(
            {
                "file": name,
                "pixels": int(final.sum()),
                "sha256": raster_sha256,
                "holdout_dti": results["dti"],
                "ci95": results["ci95"]["interval"],
                "max_dot_overlap": max_overlap,
                "novelty_pass": novelty_pass,
                "note_characters": len(note),
                "verdict": verdict,
                "ok_to_submit": ok_to_submit,
            },
            indent=2,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
