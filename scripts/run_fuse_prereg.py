#!/usr/bin/env python3
"""Execute the preregistered H24-FUSE experiment (knowledge/15_preregistered_next_gen_2026-10-25.md, Rank 1).

H24-FUSE = the same fold-local HistGradientBoosting learner as the reconstructed
OOF multi-physics baseline (``oof_multiphysics_hgb_d3``), with the four SAHG1-engineered
channels (G_sat, R_alt, B_step, H_conduit) appended to the 27 prepared base channels.

Design rules enforced here (see the preregistration):
- One fixed run. A recorded experiment is never overwritten; use ``--verify-recorded``.
- No tuning: HGB parameters, sampling sizes, seeds and budget are the SAHG1/OOF constants.
- Shared code only: ``gems.holdout.SegmentHoldout``, ``gems.novelty``, ``gems.submission`` and
  the SAHG1 runner helpers (baseline reconstruction, peer-blob check, exact-file C2ST audit).
- The full-footprint model (trained on ALL catalogue pixels) is used ONLY to place dots and for
  novelty comparison against registry rasters. It is never scored on the holdout, so no
  holdout truth leaks into any reported DTI, and the SAHG1 bridge-protocol evaluation is skipped
  for this arm for the same reason.
- Verdict fails closed. File validity never sets ``ok_to_submit``; a separate selector step is
  required, and the agent never uploads.
"""

from __future__ import annotations

import argparse
import gc
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import numpy as np  # noqa: E402
import rasterio  # noqa: E402
import run_sahg1_lane as s1  # noqa: E402  (shared SAHG1 helpers; not re-implemented)
from scipy.ndimage import distance_transform_edt  # noqa: E402
from sklearn.ensemble import HistGradientBoostingClassifier  # noqa: E402
from threadpoolctl import threadpool_limits  # noqa: E402

from gems import emission, footprint, holdout, novelty, sahg1, submission  # noqa: E402
from gems.validator import sha256_file  # noqa: E402

BUDGET_FRACTION = s1.BUDGET_FRACTION
SEED = s1.SEED
HGB_PARAMS = dict(s1.HGB_PARAMS)
AUG_KEYS = (
    "saturating_scarp_g_sat",
    "radiometric_alteration_r_alt",
    "basement_step_b_step",
    "hydrothermal_conduit_h",
)
AUG_NAMES = ("G_sat", "R_alt", "B_step", "H_conduit")
ATTEMPT_NOTE = (
    "Attempt 1 printed the holdout arms, then crashed at the peer-blob cache step (missing "
    "data/research/peer_review; no record written). The peer cache was restored from pinned GitHub "
    "blobs. Attempt 2 (full run, fixed final-dot novelty call without dots=, which had passed "
    "literal overlap as None) was discarded before any conclusion was drawn from it. No HGB, sampling or "
    "budget parameter was changed in any attempt."
)
N_POS, N_NEG = 20000, 60000
BASELINE_RECORDED = ROOT / "evidence/sahg1_experiment_20261025.json"

EXPERIMENT_PATH = ROOT / "evidence/fuse_experiment_20261025.json"
RUN_CARD_PATH = ROOT / "evidence/fuse_run_card_20261025.json"
DOCS_CARD_PATH = ROOT / "docs/data/fuse_run_card.json"
DOCS_DOWNLOAD_PATH = ROOT / "docs/data/fuse_download.json"


def save_json(obj: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n")


def augmented_block(stack, base_nc: int, aug_flat: np.ndarray, ids: np.ndarray) -> np.ndarray:
    """Rows = footprint-order indices ``ids``; columns = 27 base + 4 SAHG1 channels."""
    X = np.empty((len(ids), base_nc + len(AUG_KEYS)), dtype=np.float32)
    X[:, :base_nc] = stack[ids, :base_nc]
    X[:, base_nc:] = aug_flat[ids]
    return X


def fuse_oof_predictions(context, fp, support, stack, base_nc, aug_flat, fp_ids):
    """Per-fold FUSE learner, identical sampling/emission protocol to the OOF baseline."""
    predictions = []
    oof_surface = np.zeros(fp.shape, dtype=np.float32)
    with threadpool_limits(limits=2):
        for fold in context.folds:
            rng = np.random.default_rng(SEED + int(fold["id"]))
            # Visible catalogue only for the negative buffer; never hidden components.
            dist_visible = distance_transform_edt(~fold["visible"])
            pos_ids = np.flatnonzero((fold["train"] & fold["visible"]).ravel()[fp_ids])
            neg_ids = np.flatnonzero(
                (fold["train"] & ~fold["visible"] & (dist_visible >= 9)).ravel()[fp_ids]
            )
            pos_sel = rng.choice(pos_ids, min(N_POS, len(pos_ids)), replace=False)
            neg_sel = rng.choice(neg_ids, min(N_NEG, len(neg_ids)), replace=False)
            train_sel = np.r_[pos_sel, neg_sel]
            y_train = np.r_[np.ones(len(pos_sel), np.int8), np.zeros(len(neg_sel), np.int8)]
            model = HistGradientBoostingClassifier(**HGB_PARAMS).fit(
                augmented_block(stack, base_nc, aug_flat, train_sel), y_train
            )

            val_ids = np.flatnonzero(fold["valid"].ravel()[fp_ids])
            fold_score = np.zeros(fp.shape, dtype=np.float32)
            for begin in range(0, len(val_ids), 75000):
                chunk = val_ids[begin : begin + 75000]
                probs = model.predict_proba(augmented_block(stack, base_nc, aug_flat, chunk))[
                    :, 1
                ].astype(np.float32)
                fold_score.ravel()[fp_ids[chunk]] = probs
                oof_surface.ravel()[fp_ids[chunk]] = probs
            eligible = support & fold["valid"] & ~fold["visible"]
            budget = round(BUDGET_FRACTION * int(fold["valid"].sum()))
            predictions.append(emission.priority_poisson(fold_score, eligible, budget, min_dist=3))
            del model, fold_score
            gc.collect()
    return predictions, oof_surface


def full_footprint_surface(fp, catalogue, support, stack, base_nc, aug_flat, fp_ids) -> np.ndarray:
    """Placement model: trained on every catalogue pixel. NEVER used for holdout scoring."""
    rng = np.random.default_rng(SEED + 99)
    dist_cat = distance_transform_edt(~catalogue)
    pos_ids = np.flatnonzero(catalogue.ravel()[fp_ids])
    neg_ids = np.flatnonzero((fp & ~catalogue & (dist_cat >= 9)).ravel()[fp_ids])
    pos_sel = rng.choice(pos_ids, min(N_POS, len(pos_ids)), replace=False)
    neg_sel = rng.choice(neg_ids, min(N_NEG, len(neg_ids)), replace=False)
    y = np.r_[np.ones(len(pos_sel), np.int8), np.zeros(len(neg_sel), np.int8)]
    with threadpool_limits(limits=2):
        model = HistGradientBoostingClassifier(**HGB_PARAMS).fit(
            augmented_block(stack, base_nc, aug_flat, np.r_[pos_sel, neg_sel]), y
        )
        surface = np.zeros(fp.shape, dtype=np.float32)
        ids = np.flatnonzero((support & fp).ravel()[fp_ids])
        for begin in range(0, len(ids), 75000):
            chunk = ids[begin : begin + 75000]
            probs = model.predict_proba(augmented_block(stack, base_nc, aug_flat, chunk))[
                :, 1
            ].astype(np.float32)
            surface.ravel()[fp_ids[chunk]] = probs
    return surface


def verify_recorded() -> dict:
    exp = json.loads(EXPERIMENT_PATH.read_text())
    card = json.loads(RUN_CARD_PATH.read_text())
    template = ROOT / "data/bridge/sample_submission.tif"
    z_path = ROOT / "docs/downloads" / card["submission_name"]
    n_path = ROOT / "docs/downloads" / card["nan_outside_artifact"]
    if sha256_file(z_path) != card["raster_sha256"]:
        raise ValueError("FUSE primary TIFF checksum mismatch")
    if sha256_file(n_path) != card["nan_outside_sha256"]:
        raise ValueError("FUSE NaN-outside TIFF checksum mismatch")
    for path in (z_path, n_path):
        c = submission.check_variants(path, template)
        if not c["format_valid"] or c["ok_to_upload"] or c["submission_authorized"]:
            raise ValueError(f"FUSE validator check failed for {path.name}")
    if card["ok_to_submit"] or card["verdict"] not in ("negative", "promote"):
        raise ValueError("FUSE verdict weakened or malformed")
    return {
        "verified": True,
        "experiment_rerun": False,
        "submission_name": card["submission_name"],
        "raster_sha256": card["raster_sha256"],
        "holdout_dti": card["holdout"]["dti"],
        "ci95": card["holdout"]["ci95"]["interval"],
        "verdict": card["verdict"],
        "ok_to_submit": card["ok_to_submit"],
        "experiments_run": exp["experiment_number"],
    }


def build_card_from_record(record: dict) -> dict:
    """Deterministic run card from the recorded stop (no recomputation, no new numbers)."""
    final = record["final_novelty"]
    arm = record["results"]["h24_fuse_hgb_sahg1_channels"]
    base = record["results"]["oof_multiphysics_hgb_d3"]
    dups = [
        {
            "registry_id": r["registry_id"],
            "file": r["file"],
            "dot_overlap_within_3px": r["candidate_dot_overlap_within_3px"],
            "raw_spearman": r["raw_spearman"],
        }
        for r in final["rows"]
        if r["duplicate"]
    ]
    return {
        "hypothesis": "H24-FUSE: 27 prepared base channels + 4 SAHG1 channels (G_sat, R_alt, B_step, H_conduit) in a fold-local HistGradientBoosting learner",
        "mechanism": "Learned fusion of strike-projected LiDAR scarp, stable-Th-normalised K/U alteration, gravity/magnetic/basement/strain step and their conjunction, with fold-local training on visible faults only",
        "named_non_fault_mimic": "Pleistocene Lake Lahontan shoreline/tufa bars or welded-tuff ledges that co-register with alteration and basement-step signals",
        "holdout": {
            "label": "HOLDOUT-DTI",
            "evaluator": arm["evaluator_version"],
            "dti": arm["dti"],
            "ci95": arm["ci95"]["interval"],
            "withheld_positives": arm["n_withheld_positive_pixels"],
        },
        "reconstructed_oof_baseline": {
            "label": "HOLDOUT-DTI",
            "dti": base["dti"],
            "ci95": base["ci95"]["interval"],
            "withheld_positives": base["n_withheld_positive_pixels"],
        },
        "paired_fuse_minus_baseline": {
            "delta_dti": record["paired_fuse_minus_oof_baseline"]["delta_dti"],
            "ci95": record["paired_fuse_minus_oof_baseline"]["ci95"],
        },
        "correlation_overlap_vs_registry": {
            "surface_max_abs_rank_correlation": record["surface_novelty"][
                "max_abs_rank_correlation"
            ],
            "surface_method_lane_passed": record["surface_novelty"]["method_lane_passed"],
            "final_max_abs_rank_correlation": final["max_abs_rank_correlation"],
            "final_method_lane_max_dot_overlap_within_3px": final["method_lane_max_dot_overlap"],
            "final_literal_all_entries_max_overlap_within_3px": final["max_dot_overlap"],
            "final_duplicates_over_0_70_or_rho_0_90": dups,
            "peer_blob_max_dot_overlap_within_3px": record["peer_blob_novelty"][
                "max_dot_overlap_within_3px"
            ],
            "method_lane_passed": bool(
                final["method_lane_passed"] and record["peer_blob_novelty"]["passed"]
            ),
        },
        "leakage_canary": {
            "passed": record["canary"]["passed"],
            "max_pooled_auc": max(v["pooled_auc"] for v in record["canary"]["features"].values()),
            "threshold": 0.90,
        },
        "raster_sha256": None,
        "validator_output": "not run: stopped at the duplicate gate before packaging",
        "submission_name": None,
        "note": None,
        "verdict": "negative",
        "stopped_reason": record["stopped_reason"],
        "ok_to_download": False,
        "ok_to_submit": False,
        "organizer_confirmed_score": None,
        "submission_slots_used": 0,
        "experiments_run": 3,
        "attempt_note": record["attempt_note"],
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--verify-recorded", action="store_true")
    ap.add_argument(
        "--write-card", action="store_true", help="derive the JSON run card from the recorded stop"
    )
    args = ap.parse_args()
    if args.write_card:
        record = json.loads(EXPERIMENT_PATH.read_text())
        if record.get("artifact") is not None or record.get("stopped_reason") is None:
            raise SystemExit("Only a recorded STOP can be carded here")
        card = build_card_from_record(record)
        save_json(card, RUN_CARD_PATH)
        save_json(card, DOCS_CARD_PATH)
        print(json.dumps(card, indent=2, allow_nan=False))
        return
    if args.verify_recorded:
        print(json.dumps(verify_recorded(), indent=2, allow_nan=False))
        return
    if EXPERIMENT_PATH.exists():
        raise SystemExit(
            "FUSE experiment already recorded. No implicit rerun; use --verify-recorded."
        )

    t0 = time.monotonic()
    fp = footprint.load_footprint()
    template = ROOT / "data/bridge/sample_submission.tif"
    with rasterio.open(ROOT / "data/bridge/labels.tif") as ds:
        catalogue = (ds.read(1) > 0) & fp

    # 1. SAHG1 engineered surfaces (uses no catalogue) and the verified 27-channel stack.
    context = holdout.SegmentHoldout(fp, catalogue, buffer_px=15)
    lidar_b, rad_b, ext_b, geophys_b, input_hashes = s1.load_inputs(fp)
    surfaces, support = sahg1.build_surfaces(lidar_b, rad_b, ext_b, geophys_b, fp)
    prep_meta = json.loads((ROOT / "data/prepared/features.json").read_text())
    base_nc = int(prep_meta["base_count"])
    stack = np.load(ROOT / "data/prepared/features.npy", mmap_mode="r")
    fp_ids = np.flatnonzero(fp)
    aug_flat = np.stack([surfaces[k].ravel()[fp_ids] for k in AUG_KEYS], axis=1).astype(np.float32)
    if not np.isfinite(aug_flat).all():
        raise SystemExit("Non-finite SAHG1 channel inside footprint; halted")
    del lidar_b, rad_b, ext_b, geophys_b
    gc.collect()

    # 2. Leakage canaries: each engineered channel and each of the 27 base channels alone.
    # Batched (memory-bounded) canaries: one 2-D surface at a time inside each batch.
    pending = [(name, surfaces[k]) for k, name in zip(AUG_KEYS, AUG_NAMES)]
    for i, name in enumerate(prep_meta["names"][:base_nc]):
        arr = np.full(fp.shape, np.nan, dtype=np.float32)
        arr.ravel()[fp_ids] = stack[:, i]
        pending.append((f"base_{name}", arr))
    canary_features: dict = {}
    canary_passed = True
    for begin in range(0, len(pending), 6):
        part = context.canary(dict(pending[begin : begin + 6]), seed=SEED)
        canary_features.update(part["features"])
        canary_passed = canary_passed and part["passed"]
        del part
        gc.collect()
    del pending
    canary_report = {
        "diagnostic": "LEAKAGE-CANARY AUC, not a DTI or organizer score",
        "evaluator_version": holdout.MTR_EVALUATOR_VERSION,
        "threshold": 0.90,
        "two_polarities_checked": True,
        "passed": canary_passed,
        "features": canary_features,
    }
    if not canary_report["passed"]:
        save_json(
            {"stopped_reason": "leakage-canary", "canary": canary_report},
            EXPERIMENT_PATH,
        )
        raise SystemExit("Leakage canary failed on FUSE input; stopped")
    print("FUSE leakage canaries passed:", len(canary_report["features"]), flush=True)

    # 3. Same-protocol holdout arms.
    priority_reg = json.loads((ROOT / "registry/priority_rasters.json").read_text())
    extras = s1.extra_20261025_entries(fp)
    arm_results = {}
    arm_blocks = {}
    yy, xx = np.nonzero(fp)
    nx = (fp.shape[1] + 99) // 100
    active_blocks = np.unique((yy // 100) * nx + xx // 100)

    print("Running reconstructed OOF multi-physics HGB baseline (27 channels)...", flush=True)
    base_preds, _ = s1.build_oof_baseline_predictions(context, fp, support)
    base_scored = [context.score_fold(p, f)[1] for p, f in zip(base_preds, context.folds)]
    arm_results["oof_multiphysics_hgb_d3"] = context.summarize(base_preds)
    arm_blocks["oof_multiphysics_hgb_d3"] = np.sum(base_scored, axis=0)[active_blocks]
    del base_preds, base_scored
    gc.collect()

    print("Running H24-FUSE OOF learner (27 + 4 SAHG1 channels)...", flush=True)
    fuse_preds, fuse_oof_surface = fuse_oof_predictions(
        context, fp, support, stack, base_nc, aug_flat, fp_ids
    )
    fuse_scored = [context.score_fold(p, f)[1] for p, f in zip(fuse_preds, context.folds)]
    arm_results["h24_fuse_hgb_sahg1_channels"] = context.summarize(fuse_preds)
    arm_blocks["h24_fuse_hgb_sahg1_channels"] = np.sum(fuse_scored, axis=0)[active_blocks]
    del fuse_preds, fuse_scored
    gc.collect()
    for name in ("oof_multiphysics_hgb_d3", "h24_fuse_hgb_sahg1_channels"):
        r = arm_results[name]
        print(name, "HOLDOUT-DTI", r["dti"], r["ci95"]["interval"], flush=True)

    recorded = json.loads(BASELINE_RECORDED.read_text())["results"]["oof_multiphysics_hgb_d3"]
    baseline_repro_delta = arm_results["oof_multiphysics_hgb_d3"]["dti"] - recorded["dti"]

    paired = holdout.pooled_bootstrap(
        arm_blocks["h24_fuse_hgb_sahg1_channels"],
        paired=arm_blocks["oof_multiphysics_hgb_d3"],
        resamples=1999,
        seed=SEED,
    )
    fuse_dti = arm_results["h24_fuse_hgb_sahg1_channels"]["dti"]
    beats_baseline = fuse_dti > recorded["dti"] and paired[0] > 0

    # 4. Full-footprint placement model (never scored on holdout).
    print("Training full-footprint placement model (no holdout scoring)...", flush=True)
    p_full = full_footprint_surface(fp, catalogue, support, stack, base_nc, aug_flat, fp_ids)
    full_budget = round(BUDGET_FRACTION * int(fp.sum()))
    eligible = support & ~catalogue
    final_dots = emission.priority_poisson(p_full, eligible, full_budget, min_dist=3)
    final_dots = final_dots.astype(np.float32)
    pixel_count = int((final_dots > 0).sum())

    # 5. Prospective novelty: pre-placement surface, then final dots.
    surface_novelty = novelty.compare_prospective_registry(
        p_full, fp, priority_reg["unique_rasters"], ROOT, extra_entries=extras
    )
    if not surface_novelty["method_lane_passed"]:
        save_json(
            {
                "stopped_reason": "duplicate-surface-vs-method-lane",
                "surface_novelty": surface_novelty,
            },
            EXPERIMENT_PATH,
        )
        raise SystemExit("Duplicate surface against a competing method lane; halted")
    # Final-dot check: dots=final_dots is REQUIRED so the all-dot directional overlap is computed.
    final_novelty = novelty.compare_prospective_registry(
        final_dots, fp, priority_reg["unique_rasters"], ROOT, dots=final_dots, extra_entries=extras
    )
    peer_check = s1.check_peer_blobs(p_full, final_dots, fp)
    if final_novelty["method_lane_max_dot_overlap"] is None:
        raise SystemExit("Final-dot overlap not computed; refusing to certify novelty")
    final_gate_ok = bool(final_novelty["method_lane_passed"] and peer_check["passed"])
    if not final_gate_ok:
        # Protocol: log the duplicate and STOP. No C2ST, no downloadable TIF is packaged.
        stop_record = {
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "hypothesis": "H24-FUSE: 27 prepared base channels + 4 SAHG1 channels in a fold-local HistGradientBoosting learner",
            "preregistration": "knowledge/15_preregistered_next_gen_2026-10-25.md (Rank 1)",
            "experiment_number": 1,
            "attempt_note": ATTEMPT_NOTE,
            "stopped_reason": "duplicate-final-dots-vs-registry (lane rule: >0.70 within 3 px or rho>0.90)",
            "canary": canary_report,
            "results": arm_results,
            "paired_fuse_minus_oof_baseline": {
                "delta_dti": fuse_dti - arm_results["oof_multiphysics_hgb_d3"]["dti"],
                "ci95": paired,
            },
            "surface_novelty": surface_novelty,
            "final_novelty": final_novelty,
            "peer_blob_novelty": peer_check,
            "artifact": None,
            "verdict": "negative",
            "ok_to_download": False,
            "ok_to_submit": False,
            "submission_slot_spent": False,
            "organizer_confirmed_score": None,
            "elapsed_seconds": round(time.monotonic() - t0, 3),
        }
        save_json(stop_record, EXPERIMENT_PATH)
        print(
            "STOP: final dots are a duplicate of a registry raster; see evidence/fuse_experiment_20261025.json",
            flush=True,
        )
        raise SystemExit(0)

    # 6. Exact-file C2ST nuisance audit on the emitted dots.
    print("Running exact-file C2ST nuisance audit...", flush=True)
    nuisance = s1.run_exact_file_nuisance_audit(final_dots, catalogue, fp)

    # 7. Writer + validator (both NaN-outside and zero-outside variants).
    content_id = submission.scored_content_id(final_dots, fp, catalogue)
    sub_name = submission.make_filename("gems24", "fuse-sahg1-hgb", "20261025", content_id, "zeros")
    nan_name = sub_name.replace("-zeros.tif", "-nan.tif")
    downloads = ROOT / "docs/downloads"
    z_path = submission.write_submission(final_dots, template, downloads / sub_name, outside="zero")
    n_path = submission.write_submission(final_dots, template, downloads / nan_name, outside="nan")
    checks = {
        "zero_outside": submission.check_variants(z_path, template),
        "nan_outside": submission.check_variants(n_path, template),
    }
    if not all(c["format_valid"] for c in checks.values()):
        raise SystemExit("Exact-file format validation failed")

    note = f"GEMS24 H24-FUSE | SAHG1 channels in fold-local HGB | research only; DO NOT SUBMIT | id {content_id}"
    if len(note) > 140:
        raise AssertionError(f"Note length {len(note)} exceeds 140 characters")

    method_lane_ok = bool(final_novelty["method_lane_passed"] and peer_check["passed"])
    literal_ok = bool(final_novelty["literal_all_entries_passed"])
    c2st_ok = bool(nuisance["sahg1_candidate"]["strict_gate_passed"])
    all_gates = bool(beats_baseline and c2st_ok and method_lane_ok and literal_ok)
    reasons = []
    if not beats_baseline:
        reasons.append(
            f"Did not beat reconstructed OOF multi-physics HGB baseline ({fuse_dti:.5f} vs {recorded['dti']:.5f}; paired delta CI low {paired[0]:+.5f})"
        )
    if not literal_ok:
        reasons.append(
            "Literal all-entry overlap rule flags the synthetic spacing-5 calibration lattice (registry-039) at the reported overlap"
        )
    if not c2st_ok:
        reasons.append(
            f"Exact-file C2ST nuisance audit flagged association (AUC {nuisance['sahg1_candidate']['observed_auc']:.4f}, Holm p={nuisance['sahg1_candidate']['holm_p_value']:.3f})"
        )
    reasons.append(
        "Promotion to a weekly slot needs a separate selector step; the agent never uploads"
    )
    verdict = "promote" if all_gates else "negative"

    experiment = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "hypothesis": "H24-FUSE: 27 prepared base channels + 4 SAHG1 channels (G_sat, R_alt, B_step, H_conduit) in a fold-local HistGradientBoosting learner",
        "preregistration": "knowledge/15_preregistered_next_gen_2026-10-25.md (Rank 1)",
        "experiment_number": 1,
        "attempt_note": ATTEMPT_NOTE,
        "maximum_experiments": 3,
        "maximum_session_hours": 2,
        "inputs": input_hashes,
        "prepared_features_sha256": prep_meta["sha256"],
        "base_channels": base_nc,
        "augmented_channels": list(AUG_NAMES),
        "catalogue_used_for_features": False,
        "canary": canary_report,
        "results": arm_results,
        "baseline_reproduction": {
            "recorded_dti": recorded["dti"],
            "recorded_source": "evidence/sahg1_experiment_20261025.json",
            "reproduced_delta": baseline_repro_delta,
        },
        "paired_fuse_minus_oof_baseline": {
            "delta_dti": fuse_dti - arm_results["oof_multiphysics_hgb_d3"]["dti"],
            "ci95": paired,
        },
        "surface_novelty": surface_novelty,
        "final_novelty": final_novelty,
        "peer_blob_novelty": peer_check,
        "exact_file_nuisance_audit": nuisance,
        "bridge_protocol_evaluation": "skipped: placement model trained on all catalogue pixels would be in-sample",
        "artifact": {
            "file": sub_name,
            "nan_file": nan_name,
            "sha256": sha256_file(z_path),
            "nan_sha256": sha256_file(n_path),
            "content_id": content_id,
            "pixel_count": pixel_count,
            "note": note,
        },
        "verdict": verdict,
        "verdict_reasons": reasons,
        "ok_to_download": bool(all(c["format_valid"] for c in checks.values())),
        "ok_to_submit": False,
        "submission_slot_spent": False,
        "organizer_confirmed_score": None,
        "elapsed_seconds": round(time.monotonic() - t0, 3),
    }
    save_json(experiment, EXPERIMENT_PATH)

    run_card = {
        "hypothesis": experiment["hypothesis"],
        "mechanism": "Fold-local learned fusion: LiDAR strike-projected scarp (G_sat), stable-Th-normalised K/U alteration (R_alt), gravity/magnetic/basement/strain step (B_step) and their geometric conjunction (H_conduit) as extra channels next to the 27 prepared base channels",
        "named_non_fault_mimic": "Pleistocene Lake Lahontan shoreline/tufa bars or welded-tuff ledges that co-register with alteration and basement-step signals",
        "holdout": {
            "evaluator": holdout.MTR_EVALUATOR_VERSION,
            "dti": fuse_dti,
            "ci95": arm_results["h24_fuse_hgb_sahg1_channels"]["ci95"],
            "withheld_positives": arm_results["h24_fuse_hgb_sahg1_channels"][
                "n_withheld_positive_pixels"
            ],
            "label": "HOLDOUT-DTI",
        },
        "reconstructed_oof_baseline": arm_results["oof_multiphysics_hgb_d3"],
        "paired_vs_oof_baseline": experiment["paired_fuse_minus_oof_baseline"],
        "correlation_overlap_vs_registry": {
            "competing_method_rasters_checked": final_novelty["competing_method_rasters_count"],
            "calibration_control_rasters_checked": final_novelty[
                "calibration_control_rasters_count"
            ],
            "peer_blobs_checked": peer_check["peer_unique_blobs_checked"],
            "surface_max_abs_rank_correlation": surface_novelty["max_abs_rank_correlation"],
            "final_max_abs_rank_correlation": final_novelty["max_abs_rank_correlation"],
            "method_lane_max_overlap_within_3px": final_novelty["method_lane_max_dot_overlap"],
            "peer_blobs_max_overlap_within_3px": peer_check["max_dot_overlap_within_3px"],
            "literal_all_entries_max_overlap_within_3px": final_novelty["max_dot_overlap"],
            "method_lane_passed": method_lane_ok,
            "literal_all_entries_passed": literal_ok,
        },
        "exact_file_nuisance_audit": nuisance["sahg1_candidate"],
        "raster_sha256": experiment["artifact"]["sha256"],
        "nan_outside_artifact": nan_name,
        "nan_outside_sha256": experiment["artifact"]["nan_sha256"],
        "validator_output": checks["zero_outside"],
        "submission_name": sub_name,
        "note": note,
        "verdict": verdict,
        "ok_to_download": experiment["ok_to_download"],
        "ok_to_submit": False,
        "reasons": reasons,
        "organizer_confirmed_score": None,
        "experiments_run": 1,
        "submission_slots_used": 0,
    }
    save_json(run_card, RUN_CARD_PATH)
    save_json(run_card, DOCS_CARD_PATH)
    save_json(
        {
            "file": sub_name,
            "nan_file": nan_name,
            "sha256": experiment["artifact"]["sha256"],
            "nan_sha256": experiment["artifact"]["nan_sha256"],
            "content_id": content_id,
            "pixel_count": pixel_count,
            "note": note,
            "format_valid": True,
            "ok_to_download": experiment["ok_to_download"],
            "ok_to_submit": False,
            "verdict": verdict,
            "live_dti": None,
            "run_card": "fuse_run_card.json",
        },
        DOCS_DOWNLOAD_PATH,
    )
    print(json.dumps(verify_recorded(), indent=2, allow_nan=False), flush=True)


if __name__ == "__main__":
    main()
