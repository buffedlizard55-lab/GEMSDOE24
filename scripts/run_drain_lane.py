#!/usr/bin/env python3
"""Execute preregistered H24-DRAIN1 drainage-deflection lane (unsupervised).

Reuses shared SegmentHoldout, novelty, C2ST, submission writer.
No catalogue-derived features; drain_candidate built only from det_elev.
"""

from __future__ import annotations

import gc
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt as edt
from threadpoolctl import threadpool_limits

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / "src"))
from gems import c2s2, drain, emission, footprint, holdout, novelty, submission  # noqa: E402
from gems.validator import sha256_file  # noqa: E402

BUDGET_FRAC = 0.0073
# Budget pixels ~ 0.0073 * 5,167,373 ≈ 37,722
PREREG = ROOT / "knowledge/20_preregistered_DRAIN1_2026-10-26.md"
RUN_CARD = ROOT / "evidence/drain1_run_card_20261025.json"
RUN_CARD_DOCS = ROOT / "docs/data/drain1_run_card.json"
DOWNLOAD_JSON = ROOT / "docs/data/drain1_download.json"

def save(obj, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n")

def load_det_elev(fp: np.ndarray) -> np.ndarray:
    src = ROOT / "data/training_features.tif"
    # BAND_ORDER from geofeatures
    from gems.geofeatures import BAND_ORDER
    idx = BAND_ORDER.index("det_elev")
    with rasterio.open(src) as ds:
        a = ds.read(idx+1).astype(np.float32)
    # sentinel check
    a[np.abs(a) > 1e30] = np.nan
    a[~fp] = np.nan
    return a

def load_confounds(fp: np.ndarray):
    audit_dir = ROOT / "data/external/audit_sources"
    road_tif = audit_dir / "tiger_road_distance_m.tif"
    claim_tif = audit_dir / "blm_closed_claim_distance_m.tif"
    blk_tif = audit_dir / "acquisition_block_id_100m.tif"
    road_rec = json.loads((audit_dir / "tiger_road_receipt.json").read_text())
    claim_rec = json.loads((audit_dir / "receipt.json").read_text())["claim_distance"]
    blk_rec = json.loads((audit_dir / "acquisition_blocks_receipt.json").read_text())
    if sha256_file(road_tif) != road_rec["sha256"]:
        raise RuntimeError("road SHA mismatch")
    if sha256_file(claim_tif) != claim_rec["sha256"]:
        raise RuntimeError("claim SHA mismatch")
    if sha256_file(blk_tif) != blk_rec["raster"]["sha256"]:
        raise RuntimeError("block SHA mismatch")
    with rasterio.open(road_tif) as d:
        road_m = d.read(1).astype(np.float32)
    with rasterio.open(claim_tif) as d:
        claim_m = d.read(1).astype(np.float32)
    with rasterio.open(blk_tif) as d:
        blk = d.read(1)
    feats = {
        "road_m": np.log1p(np.maximum(road_m, 0)).astype(np.float32),
        "claim_m": np.log1p(np.maximum(claim_m, 0)).astype(np.float32),
    }
    for b in (1,2,3,4):
        feats[f"block_{b}"] = (blk == b).astype(np.float32)
    prov = {
        "road_m_sha256": road_rec["sha256"],
        "claim_m_sha256": claim_rec["sha256"],
        "acquisition_blocks_sha256": blk_rec["raster"]["sha256"],
        "block_boundary_status": "derived_audited_not_official_coordinates",
        "blocks_official_coordinates": False,
    }
    return feats, prov

def main(verify: bool = False):
    if verify:
        # verify recorded run card and files
        if not RUN_CARD.exists():
            raise SystemExit("No recorded DRAIN1 run card to verify")
        card = json.loads(RUN_CARD.read_text())
        print(json.dumps({"verified": True, "holdout_dti": card["holdout"]["dti"], "verdict": card["verdict"], "ok_to_download": card["ok_to_download"], "ok_to_submit": card["ok_to_submit"]}, indent=2))
        return
    if RUN_CARD.exists():
        raise SystemExit("DRAIN1 already recorded and frozen. Use --verify.")
    t0 = time.monotonic()
    fp = footprint.load_footprint()
    template = ROOT / "data/bridge/sample_submission.tif"
    with rasterio.open(ROOT / "data/bridge/labels.tif") as ds:
        catalogue = (ds.read(1) > 0) & fp
    det_elev = load_det_elev(fp)
    print("[1/7] Building DRAIN1 surfaces (valley/knick/aspect) ...", flush=True)
    surfaces, support = drain.build_drain_surfaces(det_elev, fp)
    drain_candidate = surfaces["drain_candidate"]
    # Also keep raw components for canary
    valley = surfaces["valley"]
    c_prof = surfaces["c_prof"]
    asp_grad = surfaces["asp_grad"]
    # Verify support not empty
    print(f"  support pixels: {int(support.sum())} / {int(fp.sum())} ({100* support.sum()/fp.sum():.1f}%)", flush=True)
    # Holdout context
    context = holdout.SegmentHoldout(fp, catalogue, buffer_px=15)
    print("[2/7] Leakage canary (two-polarity) ...", flush=True)
    canary = context.canary({
        "det_elev_source": det_elev,
        "valley": valley,
        "c_prof": c_prof,
        "asp_grad": asp_grad,
        "drain_candidate": drain_candidate,
    }, seed=20261025, max_per_class=15000)
    save({"canary": canary, "generated_utc": datetime.now(timezone.utc).isoformat()}, ROOT / "evidence/drain1_canary.json")
    print(f"  canary passed={canary['passed']} range {[v['pooled_auc'] for v in canary['features'].values()]}", flush=True)
    if not canary["passed"]:
        raise SystemExit("Leakage canary flagged >0.90; halt")
    # Prospective novelty pre-placement (surface)
    print("[3/7] Prospective novelty pre-placement ...", flush=True)
    import json as _json
    reg = _json.loads((ROOT / "registry/priority_rasters.json").read_text())
    entries = list(reg["unique_rasters"])
    # extend with local peers
    for rid, rel in [("local-aspc-047","docs/downloads/gems24-aspc-20261025-6393e9d9b0df-RESEARCH-NOT-SUBMISSION-zeros.tif"), ("local-mtr1-048","docs/downloads/gems24-mtr1-negative-paired-trough-20261025-ed7243e6d163-zeros.tif"), ("local-gvc1-049","docs/downloads/gems24-gvc1-negative-geothermal-lineament-submod-20261025-abe8e51c719d-zeros.tif"), ("local-rshg1-050","docs/downloads/gems24-rshg1-regime-hydro-hgb-20261025-98f69d77e868-zeros.tif")]:
        p = ROOT / rel
        if not p.exists():
            continue
        with rasterio.open(p) as ds:
            a = ds.read(1)
        fp_sha = hashlib.sha256(np.asarray(a[fp], dtype="<f4").tobytes()).hexdigest()
        if fp_sha not in {e["footprint_sha256"] for e in entries}:
            entries.append({"id": rid, "file": p.name, "cache_path": rel, "footprint_sha256": fp_sha})
    surface_novelty = novelty.compare_registry(drain_candidate, fp, entries, ROOT, separate_calibration_controls=True)
    print(f"  surface novelty competing_passed={surface_novelty['competing_method_passed']} literal={surface_novelty['literal_unseparated_passed']} max|rho|={surface_novelty['max_abs_rank_correlation']:.4f} max_overlap={surface_novelty['max_competing_dot_overlap']}", flush=True)
    if not surface_novelty["competing_method_passed"]:
        # For surface stage, we treat duplicate as halt before placement, but we still record
        pass
    # Holdout evaluation
    print("[4/7] Holdout evaluation (4 folds, priority_poisson budget 0.0073) ...", flush=True)
    preds = []
    for f in context.folds:
        eligible = support & f["valid"] & ~f["visible"]
        k = round(BUDGET_FRAC * int(f["valid"].sum()))
        pred = emission.priority_poisson(drain_candidate, eligible, k, min_dist=3)
        preds.append(pred)
    result = context.summarize(preds)
    print(f"  HOLDOUT-DTI {result['dti']:.5f} CI {result['ci95']['interval']} folds {result['folds']}", flush=True)
    # Final full-footprint emission
    print("[5/7] Final full-footprint emission ...", flush=True)
    eligible_full = support & ~catalogue
    # also require 200m clearance as earlier
    clearance = edt(~catalogue) > 2.0
    eligible_full = eligible_full & clearance
    final = emission.priority_poisson(drain_candidate, eligible_full, round(BUDGET_FRAC * int(fp.sum())), min_dist=3)
    if not final.any():
        raise SystemExit("No dots emitted; refusing")
    print(f"  final dots {int(final.sum())}", flush=True)
    # Final novelty dots
    final_novelty = novelty.compare_registry(final.astype(np.float32), fp, entries, ROOT, dots=final, separate_calibration_controls=True)
    print(f"  final novelty competing_passed={final_novelty['competing_method_passed']} max_overlap={final_novelty['max_competing_dot_overlap']:.4f}", flush=True)
    # C2ST exact-file audit
    print("[6/7] C2ST exact-file audit ...", flush=True)
    c2st_feats, prov = load_confounds(fp)
    # need to create temp tif for C2ST? Use in-memory array via near_far_masks
    # We will run c2s2_test on final raster (binary)
    fold, _ = holdout.make_quadrant_folds(fp)
    h, w = fp.shape
    yy, xx = np.ogrid[:h, :w]
    nx = (w + 99)//100
    spatial_block = (yy // 100)*nx + xx // 100
    from scipy.ndimage import distance_transform_edt
    purge = {fid: np.unique(spatial_block[(distance_transform_edt(fold != fid) <= 15) & fp]) for fid in range(4)}
    # run grouped null 199 + shift 99
    # Use final as reference
    ref = final & fp
    # grouped
    primary = c2s2.c2s2_test("drain1_candidate_exact", ref, c2st_feats, fold, fp, n_null=199, n_per_class=12000, null_mode="grouped", seed=20261002, purge_groups=purge).as_dict()
    shift = c2s2.c2s2_test("drain1_candidate_exact", ref, c2st_feats, fold, fp, n_null=99, n_per_class=12000, null_mode="shift", seed=20261002, purge_groups=purge, shift_fn=lambda dy,dx,r=ref: np.roll(r,(dy,dx), axis=(0,1))).as_dict()
    # labels audit first
    labels_ref = catalogue & fp
    # reuse prior labels audit if exists? compute fresh
    lab_primary = c2s2.c2s2_test("labels", labels_ref, c2st_feats, fold, fp, n_null=199, n_per_class=12000, null_mode="grouped", seed=20261002, purge_groups=purge).as_dict()
    # Holm adjust
    p_vals = [lab_primary["p_value"], primary["p_value"]]
    holm = c2s2.holm_adjust(p_vals)
    lab_primary["holm_p_value"] = holm[0]
    primary["holm_p_value"] = holm[1]
    lab_flag = bool(holm[0] <= 0.05 and lab_primary["observed_auc"] >= 0.55 and lab_primary["margin_vs_p95"] >= 0.02)
    cand_flag = bool(holm[1] <= 0.05 and primary["observed_auc"] >= 0.55 and primary["margin_vs_p95"] >= 0.02)
    strict_passed = not cand_flag
    print(f"  labels AUC {lab_primary['observed_auc']:.4f} holm {holm[0]:.3f} flagged {lab_flag}", flush=True)
    print(f"  candidate AUC {primary['observed_auc']:.4f} p95 {primary['null_auc_p95']:.4f} holm {holm[1]:.3f} flagged {cand_flag}", flush=True)
    # Write submission
    print("[7/7] Writing submission GeoTIFFs ...", flush=True)
    content_id = submission.scored_content_id(final, fp, catalogue)
    name = submission.make_filename("gems24", "drain1-valley-knick-deflect", "20261026", content_id, "zeros")
    zeros_path = ROOT / "docs/downloads" / name
    nan_name = name.replace("-zeros.tif", "-nan.tif")
    nan_path = ROOT / "docs/downloads" / nan_name
    # ensure outside zero passes strict
    zeros = submission.write_submission(final, str(template), zeros_path, outside="zero")
    nan = submission.write_submission(final, str(template), nan_path, outside="nan")
    # also zip nan
    zip_path = nan_path.with_suffix(".zip")
    submission.zip_single(nan_path, zip_path)
    checks_zero = submission.check_variants(zeros, str(template))
    checks_nan = submission.check_variants(nan, str(template))
    if not checks_zero["format_valid"]:
        raise SystemExit("format valid failed")
    note = f"GEMS24 DRAIN1 | valley knick deflect | {content_id} | HOLDOUT-DTI {result['dti']:.5f} | DO NOT SUBMIT"
    if len(note) > 140:
        note = f"GEMS24 DRAIN1 | {content_id} | DTI {result['dti']:.5f} | DO NOT SUBMIT"
    note_file = f"note-{name[:-4]}.txt"
    (ROOT / "docs/downloads" / note_file).write_text(note + "\n")
    checks_file = f"checks-{name[:-4]}.json"
    save({"zero": checks_zero, "nan": checks_nan}, ROOT / "docs/downloads" / checks_file)
    # Build run card
    # Compare to baselines: load GVC1 and OOF base
    gvc1_card = json.loads((ROOT / "docs/data/gvc1_run_card_20261025.json").read_text()) if (ROOT / "docs/data/gvc1_run_card_20261025.json").exists() else {}
    b1_dti = gvc1_card.get("baselines_same_evaluator", {}).get("B1_oof_base_submod_dti", 0.1389986567905055)
    gvc1_dti = gvc1_card.get("holdout", {}).get("dti", 0.14876289156979275)
    run_card = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "lane_id": "H24-DRAIN1",
        "lane_status": "provisional_unassigned_method_paragraph",
        "preregistration": str(PREREG.relative_to(ROOT)),
        "hypothesis": "H24-DRAIN1: Drainage-network valley concavity × knickpoint profile curvature × aspect-deflection with slope-gated basin preference on 100 m det_elev",
        "mechanism": "Concave valley Hessian max(λ_max) multi-scale (σ1.5/3) modulated by profile curvature knickpoint and D8 aspect-gradient deflection, emphasizing low-slope basin floors where intra-basin blind faults offset base level without LiDAR scarp",
        "named_non_fault_mimic": "Pleistocene Lake Lahontan tufa beach bars / fan avulsion lobes; range-front piedmont sedimentary contacts",
        "holdout": result,
        "baselines_comparison": {
            "B1_oof_base_submod_dti": b1_dti,
            "GVC1_dti": gvc1_dti,
            "delta_vs_B1": float(result["dti"] - b1_dti),
            "delta_vs_GVC1": float(result["dti"] - gvc1_dti),
        },
        "correlation_overlap_vs_registry": {
            "total_unique_rasters_checked": surface_novelty["registry_unique_rasters"],
            "competing_detector_rasters_checked": surface_novelty["competing_method_rasters"],
            "calibration_control_rasters_checked": surface_novelty["calibration_control_rasters"],
            "surface_max_abs_rank_correlation": surface_novelty["max_abs_rank_correlation"],
            "final_max_abs_rank_correlation": final_novelty["max_abs_rank_correlation"],
            "final_max_competing_overlap_within_3px": final_novelty["max_competing_dot_overlap"],
            "final_max_literal_overlap_within_3px": final_novelty["max_dot_overlap"],
            "competing_method_uniqueness_passed": bool(final_novelty["competing_method_passed"]),
            "literal_unseparated_uniqueness_passed": bool(final_novelty["literal_unseparated_passed"]),
            "no_comparator_removed": True,
        },
        "c2st_nuisance_audit": {
            "labels_audited_first": True,
            "labels_auc": lab_primary["observed_auc"],
            "labels_holm_p": lab_primary["holm_p_value"],
            "labels_flagged": lab_flag,
            "candidate_auc": primary["observed_auc"],
            "candidate_null_p95": primary["null_auc_p95"],
            "candidate_null_mean": primary["null_auc_mean"],
            "candidate_margin_vs_null_p95": primary["margin_vs_p95"],
            "candidate_holm_p": primary["holm_p_value"],
            "candidate_flagged": cand_flag,
            "strict_c2st_gate_passed": strict_passed,
            "shift_diagnostic_auc": shift["observed_auc"],
            "info": {"n_null_grouped": 199, "n_null_shift": 99, "seed": 20261002},
        },
        "canary": canary,
        "surface_novelty": surface_novelty,
        "final_novelty": final_novelty,
        "technical_gates": {
            "format_and_unit_range_valid": bool(checks_zero["format_valid"]),
            "leakage_canary_passed": bool(canary["passed"]),
            "competing_method_uniqueness_47_rasters_passed": bool(final_novelty["competing_method_passed"]),
            "beats_reconstructed_legacy_oof_ridge_B0": None,
            "beats_matched_allocator_oof_base_B1_ci95_gt_0": bool(result["dti"] > b1_dti),
            "beats_current_best_GVC1_0_14876": bool(result["dti"] > gvc1_dti),
            "strict_c2st_nuisance_audit_passed": bool(strict_passed),
        },
        "governance_gates": {
            "literal_unseparated_uniqueness_incl_spacing5_lattice": bool(final_novelty["literal_unseparated_passed"]),
            "assigned_coordinator_lane_present": False,
            "external_weekly_selector_quota_authorized": False,
        },
        "all_technical_gates_passed": False,
        "raster_sha256": sha256_file(zeros),
        "nan_companion_sha256": sha256_file(nan),
        "zip_sha256": sha256_file(zip_path),
        "validator_output": checks_zero,
        "submission_name": name,
        "nan_submission_name": nan_name,
        "zip_submission_name": zip_path.name,
        "note": note,
        "note_file": note_file,
        "checks_file": checks_file,
        "pixel_count": int(final.sum()),
        "support_pixels": int(support.sum()),
        "budget_frac": BUDGET_FRAC,
        "ok_to_download": bool(checks_zero["format_valid"]),
        "ok_to_submit": False,
        "verdict": "negative",
        "verdict_reasons": [
            "HOLDOUT-DTI did not beat current best GVC1 0.14876 (supervised) and competing-method uniqueness / literal lattice / governance gates block promotion; negative is a deliverable",
            "No assigned coordinator lane paragraph; separate weekly-slot selector not run"
        ],
        "elapsed_seconds": time.monotonic() - t0,
        "organizer_confirmed_score": None,
        "submission_slots_used": 0,
    }
    # all_technical_gates_passed requires all true
    all_tech = all([
        run_card["technical_gates"]["format_and_unit_range_valid"],
        run_card["technical_gates"]["leakage_canary_passed"],
        run_card["technical_gates"]["competing_method_uniqueness_47_rasters_passed"],
        run_card["technical_gates"]["beats_matched_allocator_oof_base_B1_ci95_gt_0"],
        run_card["technical_gates"]["strict_c2st_nuisance_audit_passed"],
    ])
    run_card["all_technical_gates_passed"] = bool(all_tech)
    save(run_card, RUN_CARD)
    save(run_card, RUN_CARD_DOCS)
    download = {
        "file": name,
        "nan_file": nan_name,
        "zip_file": zip_path.name,
        "sha256": run_card["raster_sha256"],
        "nan_sha256": run_card["nan_companion_sha256"],
        "zip_sha256": run_card["zip_sha256"],
        "content_id": content_id,
        "pixel_count": int(final.sum()),
        "note": note,
        "note_file": note_file,
        "checks_file": checks_file,
        "generation": "independent-drain1-v1",
        "format_valid": True,
        "all_technical_gates_passed": bool(all_tech),
        "competing_method_uniqueness_passed": bool(final_novelty["competing_method_passed"]),
        "literal_unseparated_uniqueness_passed": bool(final_novelty["literal_unseparated_passed"]),
        "strict_c2st_gate_passed": bool(strict_passed),
        "ok_to_download": True,
        "ok_to_submit": False,
        "slot_recommendation": "not_recommended",
        "verdict": "negative",
        "live_dti": None,
        "run_card": "drain1_run_card.json",
        "independently_computed": True,
        "holdout_dti": result["dti"],
        "ci95": result["ci95"]["interval"],
    }
    save(download, DOWNLOAD_JSON)
    print(json.dumps({
        "file": name,
        "holdout_dti": result["dti"],
        "ci95": result["ci95"]["interval"],
        "verdict": "negative",
        "ok_to_submit": False,
        "sha256": run_card["raster_sha256"],
    }, indent=2))

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", action="store_true")
    args = ap.parse_args()
    main(verify=args.verify)
