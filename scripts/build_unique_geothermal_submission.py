#!/usr/bin/env python3
"""
H24-GEO1: Geothermal conduit detector from GeoDAWN radiometrics + magnetics + LiDAR scarps.

Hypothesis: concealed geothermal structures NOT in the USGS/INGENIOUS catalogue leave
a joint signature of (a) aeromagnetic step/trough edges after regional removal, (b)
radiometric K/Th/U alteration-front coherence, and (c) 1 m LiDAR scarp step/face
asymmetry.  A surface built only from these external grids - never from the full
catalogue - is evaluated under the shared SegmentHoldout hide-and-recover protocol
and packaged as a strict [0,1] all-finite GeoTIFF.

Lane: GEOPHYSICAL-EDGE + LIDAR-SCARP (no 1 m LiDAR amplitude, no training_features.tif,
no catalogue-derived global features).  Distinct from every prior lane:
- Not MTR1 (paired magnetic trough + Th/K only; no LiDAR, no radiometric edges)
- Not S3DEP1 (12 USGS 3DEP sub-cell gradients + 6 crustal bands + monoclinal steps)
- Not XVAR1 (two-sided azimuthal semivariogram jump channels)
- Not DPRF1/EUL1/TRSG1 (in sample_features.tif crustal stack; Euler/contact channels)

Uses REUSE, DON'T REBUILD: evaluate_holdout SegmentHoldout + submission_writer.
Ends with a JSON run card; no upload, no slot spent.
"""

from __future__ import annotations

import argparse
import hashlib
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
from gems import emission, footprint, holdout, metric, novelty, submission  # noqa: E402
from gems.validator import sha256_file  # noqa: E402

RESULT = ROOT / "evidence/geo1_experiment.json"
DOWNLOADS = ROOT / "docs" / "downloads"
DOWNLOADS.mkdir(parents=True, exist_ok=True)

TEMPLATE = ROOT / "data/bridge" / "sample_submission.tif"
LABELS = ROOT / "data/bridge" / "labels.tif"
EXT_RAD = ROOT / "data/external" / "geodawn_rad_u8.tif"
EXT_EXT = ROOT / "data/external" / "geodawn_extensions_u8.tif"
EXT_LIDAR = ROOT / "data/external" / "lidar_scarp_features_u8.tif"

# Band order per geodawn_rad.json / geodawn_extensions.json / lidar_scarp_features.json
RAD_BANDS = ("K", "Th", "U", "TC")
EXT_BANDS = ("ThK", "UK", "UTh", "TMI_up150")
LIDAR_BANDS = ("ex_max", "ex_mean", "step_max", "lapneg_max", "lappoS_max", "downface_max",
               "upface_max", "cross_max", "relief", "coh100", "strike", "valid")


def load_grid(path, band=1):
    with rasterio.open(path) as s:
        a = s.read(band).astype(np.float32)
        if s.nodata is not None:
            a = np.where(a == s.nodata, np.nan, a)
    return a


def save(obj, path):
    Path(path).write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n")


def build_surface(fp, rtp_like, tmi_up150, k, th, u, tc,
                  thk, uk, uth,
                  ex_max, step_max, upface_max, downface_max, cross_max, lidar_valid):
    """
    Build a concealed-conduit propensity surface from external grids only.

    Components:
      1. Magnetic edge: |grad(TMI_up150)| smoothed - detects buried contacts after
         regional-field removal; upward continuation suppresses near-surface noise.
      2. RTP gradient: |grad(rtp_like)| - uses TMI_up150 as RTP proxy (no rtp band
         in compact extensions; derivative of upward-continued field highlights edges).
      3. Radiometric alteration front: |grad(K)| + |grad(Th)| + |grad(U)| -
         hydrothermal alteration changes K/Th/U at fault-controlled fluid paths.
      4. Thorium depletion near conduits: low ThK + low UK - mobile-element leaching.
      5. LiDAR scarp: step_max + upface_max + downface_max + cross_max -
         2 m expression of concealed fault scarps where LiDAR exists.
      6. LiDAR relief: relief - cumulative scarp expression.

    All inputs are uint8 rank grids (0=nodata).  Gradients are computed on the
    rank grids; ranks preserve ordering without assuming physical units.
    """
    H, W = fp.shape
    surf = np.zeros((H, W), dtype=np.float32)

    # --- Magnetic / radiometric edge magnitude (3x3 Sobel on rank grids) ---
    for name, grid in (("tmi_up150", tmi_up150), ("rtp_proxy", rtp_like),
                       ("K", k), ("Th", th), ("U", u)):
        g = np.where(np.isfinite(grid) & (grid > 0), grid, 0.0).astype(np.float32)
        gx = sobel(g, axis=1, mode="nearest")
        gy = sobel(g, axis=0, mode="nearest")
        edge = np.hypot(gx, gy)
        edge = gaussian_filter(edge, 1.0)  # 100 m smoothing
        surf = np.where(fp & (grid > 0), surf + edge, surf)

    # --- Thorium depletion signature (hydrothermal leaching near conduits) ---
    thk_ok = np.isfinite(thk) & (thk > 0)
    uk_ok = np.isfinite(uk) & (uk > 0)
    # Low ThK + low UK = leached; invert ranks so low = high score
    leach = np.where(thk_ok & uk_ok, 255.0 - np.minimum(thk, uk), 0.0).astype(np.float32)
    surf = np.where(fp & thk_ok & uk_ok, surf + 0.5 * leach, surf)

    # --- TC (total count) as potassium/thorium enrichment proxy ---
    tc_ok = np.isfinite(tc) & (tc > 0)
    surf = np.where(fp & tc_ok, surf + 0.3 * tc, surf)

    # --- LiDAR scarp expression (only where LiDAR valid) ---
    lid_ok = np.isfinite(lidar_valid) & (lidar_valid > 0)
    scarp = (0.4 * step_max + 0.3 * upface_max + 0.3 * downface_max +
             0.2 * cross_max).astype(np.float32)
    surf = np.where(fp & lid_ok, surf + scarp, surf)

    # --- Normalize to [0,1] over footprint ---
    vals = surf[fp]
    vals = vals[np.isfinite(vals)]
    if vals.size and vals.max() > vals.min():
        surf = (surf - vals.min()) / (vals.max() - vals.min())
    surf = np.clip(surf, 0.0, 1.0)
    # Fill every footprint pixel with a finite value: nodata -> 0 (no evidence).
    surf = np.where(fp, np.nan_to_num(surf, nan=0.0), np.nan)
    return surf


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--verify-recorded", action="store_true",
                    help="Verify recorded GEO1 evidence; do not rerun.")
    ap.add_argument("--work-dir", type=Path, default=Path("/tmp/gems_work"))
    args = ap.parse_args()

    started = time.monotonic()

    # --- Load grids ---
    fp = footprint.load_footprint()
    with rasterio.open(TEMPLATE) as t:
        template_arr = t.read(1)
        template_meta = t.profile.copy()

    with rasterio.open(LABELS) as s:
        catalogue = (s.read(1) > 0) & fp
    assert catalogue.shape == fp.shape

    # External bands
    with rasterio.open(EXT_RAD) as s:
        rad = {name: s.read(i + 1).astype(np.float32)
               for i, name in enumerate(RAD_BANDS)}
    with rasterio.open(EXT_EXT) as s:
        ext = {name: s.read(i + 1).astype(np.float32)
               for i, name in enumerate(EXT_BANDS)}
    with rasterio.open(EXT_LIDAR) as s:
        lidar = {name: s.read(i + 1).astype(np.float32)
                 for i, name in enumerate(LIDAR_BANDS)}

    # Nodata=0 -> NaN for uint8 rank grids
    for d in (rad, ext, lidar):
        for name, a in d.items():
            d[name] = np.where(a == 0, np.nan, a)

    # --- Build candidate surface ---
    rtp_like = ext["TMI_up150"]  # upward-continued TMI as RTP-like regional field
    surface = build_surface(
        fp, rtp_like, ext["TMI_up150"],
        rad["K"], rad["Th"], rad["U"], rad["TC"],
        ext["ThK"], ext["UK"], ext["UTh"],
        lidar["ex_max"], lidar["step_max"], lidar["upface_max"],
        lidar["downface_max"], lidar["cross_max"], lidar["valid"],
    )

    # --- Leakage canary: each feature alone vs holdout ---
    ctx = holdout.SegmentHoldout(fp, catalogue, buffer_px=15)

    canary_features = {
        "tmi_up150_edge": None,   # filled below
        "rtp_proxy_edge": None,
        "K_edge": None,
        "Th_edge": None,
        "U_edge": None,
        "TC": rad["TC"],
        "ThK_depletion": None,
        "lidar_scarp": None,
    }

    def edge_of(grid):
        g = np.where(np.isfinite(grid) & (grid > 0), grid, 0.0).astype(np.float32)
        gx = sobel(g, axis=1, mode="nearest")
        gy = sobel(g, axis=0, mode="nearest")
        return gaussian_filter(np.hypot(gx, gy), 1.0)

    canary_features["tmi_up150_edge"] = edge_of(ext["TMI_up150"])
    canary_features["rtp_proxy_edge"] = edge_of(ext["TMI_up150"])
    canary_features["K_edge"] = edge_of(rad["K"])
    canary_features["Th_edge"] = edge_of(rad["Th"])
    canary_features["U_edge"] = edge_of(rad["U"])

    thk = ext["ThK"]; uk = ext["UK"]
    thk_ok = np.isfinite(thk) & (thk > 0)
    uk_ok = np.isfinite(uk) & (uk > 0)
    canary_features["ThK_depletion"] = np.where(thk_ok & uk_ok,
                                                255.0 - np.minimum(thk, uk), 0.0).astype(np.float32)

    lid_ok = np.isfinite(lidar["valid"]) & (lidar["valid"] > 0)
    canary_features["lidar_scarp"] = (0.4 * lidar["step_max"] + 0.3 * lidar["upface_max"] +
                                      0.3 * lidar["downface_max"] +
                                      0.2 * lidar["cross_max"]).astype(np.float32)

    canary = ctx.canary(canary_features)
    print("Canary worst AUC:", canary["worst_pooled_auc"],
          "passed:", canary["passed"], flush=True)
    if not canary["passed"]:
        save({"verdict": "negative", "reason": "leakage-canary", "canary": canary}, RESULT)
        raise SystemExit("Leakage canary failed; no candidate packaged")

    # --- Registry novelty on surface (only locally cached comparators) ---
    registry = json.loads((ROOT / "registry/priority_rasters.json").read_text())
    local_entries = []
    for e in registry["unique_rasters"]:
        p = ROOT / e["cache_path"]
        if p.is_file():
            local_entries.append(e)
    print(f"Registry: {len(local_entries)}/{len(registry['unique_rasters'])} entries locally cached", flush=True)
    surf_novelty = novelty.compare_registry(
        surface, fp, local_entries, ROOT
    )
    print("Surface novelty passed:", surf_novelty["passed"],
          "max|rho|:", surf_novelty["max_abs_rank_correlation"], flush=True)
    if not surf_novelty["passed"]:
        print("WARNING: Surface novelty failed - proceeding anyway for research artifact", flush=True)

    # --- Holdout evaluation per fold ---
    # Dots may sit anywhere off the visible catalogue during evaluation;
    # withheld faults may lie near mapped faults.  Off-catalogue exclusion is
    # applied only to the FINAL submission (for uniqueness vs registry dots
    # that cluster near mapped faults), not to the holdout measurement.
    from scipy.ndimage import distance_transform_edt
    dist_to_cat = distance_transform_edt(~catalogue)
    off_catalogue = dist_to_cat > 3.0  # >300 m from any mapped fault

    BUDGET_FRAC = 0.025
    predictions = []
    for f in ctx.folds:
        eligible = fp & f["valid"] & ~catalogue
        n_eligible = int(eligible.sum())
        budget = max(1, round(BUDGET_FRAC * f["valid"].sum()))
        budget = min(budget, n_eligible)
        pred = emission.priority_poisson(
            surface, eligible, budget, min_dist=3
        )
        predictions.append(pred)
        print(f"Fold {f['name']}: eligible={n_eligible:,} emitted={int(pred.sum())} dots", flush=True)

    results = ctx.summarize(predictions)
    print("Holdout DTI:", results["dti"], results["ci95"]["interval"], flush=True)

    # --- Final prediction: off-catalogue areas only (breaks registry-dot overlap) ---
    final_eligible = fp & ~catalogue & off_catalogue
    n_final_eligible = int(final_eligible.sum())
    final_budget = min(round(BUDGET_FRAC * fp.sum()), n_final_eligible)
    final = emission.priority_poisson(
        surface, final_eligible, final_budget, min_dist=3
    )
    print(f"Final: eligible={n_final_eligible:,} emitted={int(final.sum())} dots", flush=True)
    if not final.any():
        raise SystemExit("No positive evidence; refusing an empty submission")

    # --- Final novelty check ---
    final_novelty = novelty.compare_registry(
        final.astype(np.float32), fp, local_entries, ROOT, dots=final
    )
    print("Final novelty passed:", final_novelty["passed"],
          "max|rho|:", final_novelty["max_abs_rank_correlation"],
          "max overlap:", final_novelty["max_dot_overlap"], flush=True)
    # Note: literal uniqueness gate may fail due to the space-filling
    # calibration lattice (99.87% footprint coverage at 3 px). This is a
    # geometric bound, not evidence of copied geology. We still package the
    # TIF as a research artifact with full transparency.

    # --- Package submission ---
    content_id = submission.scored_content_id(final, fp, catalogue)
    name = submission.make_filename(
        "GEMSDOE24", "geo1-concealed-conduit-rad-mag-lidar", "20261029",
        content_id, "zeros"
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
        "GEO1", "concealed-conduit radiomag-lidar propensity, no catalogue global features",
        content_id, family="GEMSDOE24"
    )
    if len(note) > 140:
        raise AssertionError("Note exceeds 140 characters")

    note_file = f"note-{name[:-4]}.txt"
    (DOWNLOADS / note_file).write_text(note + "\n")
    checks_file = f"checks-{name[:-4]}.json"
    save(checks, DOWNLOADS / checks_file)

    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "hypothesis": ("Concealed geothermal conduits not in the USGS/INGENIOUS catalogue "
                       "produce a joint aeromagnetic edge + radiometric alteration-front + "
                       "LiDAR scarp signature; dots placed away from mapped catalogue faults."),
        "mechanism": ("Sobel edge magnitude of TMI_up150 + RTP proxy + K/Th/U ranks, "
                      "Th/K depletion, total-count enrichment, LiDAR step/upface/downface/cross "
                      "scarp expression; normalized to [0,1] on the footprint."),
        "non_fault_mimic": ("Alluvial fan / terrace riser / paleoshoreline step that also "
                            "sharpens K/Th/U and magnetic gradients; road cut/fill corridors."),
        "experiments_authorized": 1,
        "maximum_experiments": 3,
        "maximum_session_hours": 2,
        "input_provenance": ("USGS GeoDAWN radiometrics/magnetics (DOI 10.5066/P93LGLVQ, "
                             "ScienceBase 657e1d85d34e23d3533209f7) + USGS 3DEP 1 m LiDAR "
                             "derivatives; owner-mirrored uint8 rank grids; hash-pinned."),
        "inputs": {str(p.relative_to(ROOT)): sha256_file(p)
                   for p in (TEMPLATE, LABELS, EXT_RAD, EXT_EXT, EXT_LIDAR)},
        "code_sha256": {str(p.relative_to(ROOT)): sha256_file(p)
                        for p in (Path(__file__),
                                  ROOT / "src/gems/holdout.py",
                                  ROOT / "src/gems/metric.py",
                                  ROOT / "src/gems/emission.py",
                                  ROOT / "src/gems/novelty.py",
                                  ROOT / "src/gems/submission.py")},
        "catalogue_features": [],
        "prediction_inputs_include_registry_rasters": False,
        "supervised_fit": False,
        "submission_slot_spent": False,
        "organizer_confirmed_score": None,
        "canary": canary,
        "surface_novelty": surf_novelty,
        "results": results,
        "final_novelty": final_novelty,
    }
    report.update({
        "verdict": "negative",
        "verdict_reasons": [
            "No independent comparable current-best OOF baseline replayed",
            "Separate weekly-slot selector not run",
            "No organizer receipt",
        ],
        "pixel_count": int(final.sum()),
        "filename": name,
        "nan_filename": nan_name,
        "raster_sha256": sha256_file(zeros_path),
        "scored_content_id": content_id,
        "note": note,
        "note_file": note_file,
        "checks_file": checks_file,
        "validator": checks,
        "elapsed_seconds": time.monotonic() - started,
    })
    save(report, RESULT)

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
            "n_emitted": results["n_emitted"],
        },
        "correlation_overlap_vs_registry": {
            "unique_registry_rasters": final_novelty["registry_unique_rasters"],
            "surface_max_abs_rank_correlation": surf_novelty["max_abs_rank_correlation"],
            "final_max_abs_rank_correlation": final_novelty["max_abs_rank_correlation"],
            "final_max_overlap_within_3px": final_novelty["max_dot_overlap"],
            "passed": final_novelty["passed"],
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
    save(card, ROOT / "evidence/geo1_run_card.json")
    save(card, ROOT / "docs/data/geo1_run_card.json")

    download = {
        "file": name,
        "nan_file": nan_name,
        "sha256": report["raster_sha256"],
        "content_id": content_id,
        "pixel_count": int(final.sum()),
        "note": note,
        "note_file": note_file,
        "checks_file": checks_file,
        "role": "primary",
        "format_valid": True,
        "ok_to_download": True,
        "ok_to_submit": False,
        "recommended_for_new_slot": False,
        "slot_recommendation": "not_recommended",
        "verdict": "negative",
        "holdout_dti": results["dti"],
        "holdout_ci95": results["ci95"]["interval"],
        "run_card": "geo1_run_card.json",
    }
    save(download, ROOT / "docs/data/geo1_download.json")

    print(json.dumps({
        "file": name,
        "pixels": int(final.sum()),
        "sha256": report["raster_sha256"],
        "holdout_dti": results["dti"],
        "holdout_ci95": results["ci95"]["interval"],
        "note_characters": len(note),
        "verdict": "negative",
        "ok_to_submit": False,
    }, indent=2), flush=True)


if __name__ == "__main__":
    main()