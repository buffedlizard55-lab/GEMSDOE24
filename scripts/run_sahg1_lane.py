#!/usr/bin/env python3
"""Execute the preregistered H24-SAHG1 lane and same-protocol OOF baseline reconstruction.

Strictly preserves recorded MTR1 and ASPC experiments/files. Runs at most one
preregistered SAHG1 experiment plus the leakage-free OOF multi-physics baseline
from Next Step 2, audits the exact emitted candidate with C2ST, and writes a
uniquely named GeoTIFF pair (-zeros.tif and -nan.tif) and JSON run card.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import struct
import sys
import time
import zlib
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import numpy as np  # noqa: E402
import rasterio  # noqa: E402
from scipy.ndimage import distance_transform_edt  # noqa: E402
from scipy.stats import rankdata  # noqa: E402
from sklearn.ensemble import HistGradientBoostingClassifier  # noqa: E402
from threadpoolctl import threadpool_limits  # noqa: E402

from gems import (  # noqa: E402
    c2s2,
    confounds,
    emission,
    footprint,
    holdout,
    novelty,
    sahg1,
    submission,
)
from gems.validator import sha256_file  # noqa: E402

BUDGET_FRACTION = 0.0073
ASPC_BUDGET = 37654
SEED = 20261025
HGB_PARAMS = dict(
    max_iter=80,
    max_leaf_nodes=15,
    learning_rate=0.08,
    l2_regularization=5.0,
    early_stopping=False,
    random_state=SEED,
)

EXPERIMENT_PATH = ROOT / "evidence/sahg1_experiment_20261025.json"
RUN_CARD_PATH = ROOT / "evidence/sahg1_run_card_20261025.json"
DOCS_CARD_PATH = ROOT / "docs/data/sahg1_run_card.json"
DOCS_DOWNLOAD_PATH = ROOT / "docs/data/sahg1_download.json"
PREVIEW_PATH = ROOT / "docs/assets/sahg1-preview.png"


def save_json(obj: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n")


def write_preview_png(dots: np.ndarray, fp: np.ndarray, dest: Path, step: int = 8) -> None:
    """Write a dependency-free RGB PNG preview of footprint and emitted dots."""
    h, w = fp.shape
    oh, ow = (h + step - 1) // step, (w + step - 1) // step
    rgb = np.zeros((oh, ow, 3), dtype=np.uint8)
    rgb[:] = (15, 23, 42)  # dark slate outside footprint
    fp_sub = fp[: oh * step, : ow * step]
    for dy in range(step):
        for dx in range(step):
            sub = fp_sub[dy::step, dx::step]
            rgb[: sub.shape[0], : sub.shape[1]][sub] = (30, 41, 59)
    for dy in range(step):
        for dx in range(step):
            sub = dots[dy::step, dx::step]
            rgb[: sub.shape[0], : sub.shape[1]][sub] = (56, 189, 248)

    raw_rows = b"".join(b"\x00" + rgb[y].tobytes() for y in range(oh))

    def chunk(tag: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)

    ihdr = struct.pack(">IIBBBBB", ow, oh, 8, 2, 0, 0, 0)
    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(raw_rows, level=9))
        + chunk(b"IEND", b"")
    )
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(png)


def load_inputs(fp: np.ndarray) -> tuple[dict, dict, dict, dict, dict]:
    template = ROOT / "data/bridge/sample_submission.tif"
    prep_meta = json.loads((ROOT / "data/prepared/features.json").read_text())
    prep_path = ROOT / "data/prepared/features.npy"
    if sha256_file(prep_path) != prep_meta["sha256"]:
        raise SystemExit("Prepared feature-stack checksum mismatch")

    lidar_path = ROOT / "data/external/lidar_scarp_features_u8.tif"
    lidar_meta = json.loads(lidar_path.with_name("lidar_scarp_features.json").read_text())
    rad_path = ROOT / "data/external/geodawn_rad_u8.tif"
    rad_meta = json.loads(rad_path.with_name("geodawn_rad.json").read_text())
    ext_path = ROOT / "data/external/geodawn_extensions_u8.tif"
    ext_meta = json.loads(ext_path.with_name("geodawn_extensions.json").read_text())

    if sha256_file(rad_path) != rad_meta["product_sha256"]:
        raise SystemExit("Radiometric cache checksum mismatch")
    if sha256_file(ext_path) != ext_meta["product_sha256"]:
        raise SystemExit("Extension ratio cache checksum mismatch")

    with rasterio.open(template) as t:
        grid = (t.shape, t.crs, t.transform)

    lidar_bands = {}
    with rasterio.open(lidar_path) as ds:
        if (ds.shape, ds.crs, ds.transform) != grid:
            raise SystemExit("LiDAR grid mismatch")
        for name in sahg1.LIDAR_SPECS:
            idx = lidar_meta["bands"].index(name) + 1
            lidar_bands[name] = ds.read(idx)

    rad_bands = {}
    with rasterio.open(rad_path) as ds:
        if (ds.shape, ds.crs, ds.transform) != grid:
            raise SystemExit("Radiometric grid mismatch")
        for name in sahg1.RAD_BANDS:
            idx = rad_meta["channels"].index(name) + 1
            rad_bands[name] = ds.read(idx)

    ext_bands = {}
    with rasterio.open(ext_path) as ds:
        if (ds.shape, ds.crs, ds.transform) != grid:
            raise SystemExit("Extension ratio grid mismatch")
        for name in sahg1.EXT_BANDS:
            idx = ext_meta["channels"].index(name) + 1
            ext_bands[name] = ds.read(idx)

    stack = np.load(prep_path, mmap_mode="r")
    fp_ids = np.flatnonzero(fp)
    geophys_bands = {}
    for name in sahg1.GEOPHYS_BANDS:
        arr = np.full(fp.shape, np.nan, dtype=np.float32)
        arr.ravel()[fp_ids] = stack[:, prep_meta["names"].index(name)]
        geophys_bands[name] = arr
    del stack

    hashes = {
        str(p.relative_to(ROOT)): sha256_file(p)
        for p in (
            template,
            ROOT / "data/bridge/labels.tif",
            prep_path,
            lidar_path,
            rad_path,
            ext_path,
        )
    }
    return lidar_bands, rad_bands, ext_bands, geophys_bands, hashes


def build_oof_baseline_predictions(
    context: holdout.SegmentHoldout, fp: np.ndarray, support: np.ndarray
) -> tuple[list[np.ndarray], np.ndarray]:
    """Reconstruct a leakage-free OOF multi-physics HGB detector under SegmentHoldout."""
    prep_meta = json.loads((ROOT / "data/prepared/features.json").read_text())
    stack = np.load(ROOT / "data/prepared/features.npy", mmap_mode="r")
    base_nc = int(prep_meta["base_count"])
    fp_ids = np.flatnonzero(fp)
    oof_surface = np.zeros(fp.shape, dtype=np.float32)
    predictions = []

    with threadpool_limits(limits=2):
        for fold in context.folds:
            rng = np.random.default_rng(SEED + int(fold["id"]))
            # Visible catalogue only! Never read hidden components for negative distance buffer.
            dist_visible = distance_transform_edt(~fold["visible"])
            pos_mask = fold["train"] & fold["visible"]
            neg_mask = fold["train"] & ~fold["visible"] & (dist_visible >= 9)
            pos_ids = np.flatnonzero(pos_mask.ravel()[fp_ids])
            neg_ids = np.flatnonzero(neg_mask.ravel()[fp_ids])
            pos_sel = rng.choice(pos_ids, min(20000, len(pos_ids)), replace=False)
            neg_sel = rng.choice(neg_ids, min(60000, len(neg_ids)), replace=False)
            train_sel = np.r_[pos_sel, neg_sel]
            y_train = np.r_[np.ones(len(pos_sel), np.int8), np.zeros(len(neg_sel), np.int8)]
            X_train = np.asarray(stack[train_sel, :base_nc], dtype=np.float32)
            model = HistGradientBoostingClassifier(**HGB_PARAMS).fit(X_train, y_train)

            val_ids = np.flatnonzero(fold["valid"].ravel()[fp_ids])
            fold_score = np.zeros(fp.shape, dtype=np.float32)
            for begin in range(0, len(val_ids), 75000):
                chunk = val_ids[begin : begin + 75000]
                X_val = np.asarray(stack[chunk, :base_nc], dtype=np.float32)
                probs = model.predict_proba(X_val)[:, 1].astype(np.float32)
                fold_score.ravel()[fp_ids[chunk]] = probs
                oof_surface.ravel()[fp_ids[chunk]] = probs

            eligible = support & fold["valid"] & ~fold["visible"]
            budget = round(BUDGET_FRACTION * int(fold["valid"].sum()))
            pred = emission.priority_poisson(fold_score, eligible, budget, min_dist=3)
            predictions.append(pred)
    del stack
    return predictions, oof_surface


def evaluate_bridge_protocol(
    surface: np.ndarray,
    fp: np.ndarray,
    catalogue: np.ndarray,
    support: np.ndarray,
) -> dict:
    """Evaluate SAHG1 on the 3 km / 20 km tile protocol used by ASPC for apples-to-apples bridging."""
    aspc_report = json.loads((ROOT / "evidence/aspc_run_20261025.json").read_text())
    cand_tiles = []
    global_tile_grid = None
    ncols = (fp.shape[1] + 199) // 200
    for fold in holdout.segment_folds(fp, catalogue, buffer_px=30):
        budget = int(round(ASPC_BUDGET * fold["test"].sum() / fp.sum()))
        eligible = support & fold["test"] & ~fold["visible"]
        pred = emission.priority_poisson(surface, eligible, budget, min_dist=3)
        rows, _ = holdout.spatial_components(
            pred, fold["hidden"], fold["test"], fold["visible"], tile_px=200
        )
        tile_grid = np.zeros(len(rows), bool)
        yy, xx = np.nonzero(fold["test"])
        tile_grid[(yy // 200) * ncols + xx // 200] = True
        global_tile_grid = tile_grid if global_tile_grid is None else (global_tile_grid | tile_grid)
        cand_tiles.append(rows)
    rows_pooled = np.sum(cand_tiles, axis=0)[global_tile_grid]
    val = holdout.pooled_dti(rows_pooled)
    ci = holdout.pooled_bootstrap(rows_pooled, resamples=1000, seed=SEED)
    return {
        "label": "HOLDOUT-DTI",
        "evaluator_version": holdout.SEGMENT_EVALUATOR_VERSION,
        "n_withheld_positives": int(aspc_report["holdout"]["n_withheld_positives"]),
        "dti": val,
        "ci95": ci,
        "recorded_aspc_dti": float(aspc_report["holdout"]["value"]),
        "recorded_aspc_ci95": list(aspc_report["holdout"]["ci95"]),
        "recorded_aspc_scarp_control_dti": float(aspc_report["holdout"]["control_value"]),
        "recorded_aspc_scarp_control_ci95": list(aspc_report["holdout"]["control_ci95"]),
        "delta_vs_recorded_aspc": val - float(aspc_report["holdout"]["value"]),
        "delta_vs_recorded_aspc_control": val - float(aspc_report["holdout"]["control_value"]),
    }


def check_peer_blobs(surface: np.ndarray, dots: np.ndarray, fp: np.ndarray) -> dict:
    """Also check all 83 competition-grid blobs in registry/peer_rasters_20261025.json."""
    peer_reg = json.loads((ROOT / "registry/peer_rasters_20261025.json").read_text())["entries"]
    blobs = {}
    for row in peer_reg:
        if row.get("role") == "format_demo_not_submission":
            continue
        blobs.setdefault(row["blob"], row)
    surf_ranks = rankdata(surface[fp])
    dot_ranks = rankdata(dots[fp].astype(np.float32))
    max_surf_rho = 0.0
    max_dot_rho = 0.0
    max_overlap = 0.0
    for row in blobs.values():
        p = ROOT / row["cache_path"]
        with rasterio.open(p) as ds:
            a = ds.read(1)
        s_rho = novelty.rank_correlation(surf_ranks, a[fp])
        d_rho = novelty.rank_correlation(dot_ranks, a[fp])
        ov = novelty.dot_overlap(dots, fp & (a > 0))["candidate_within_3px_of_reference"]
        if s_rho is not None:
            max_surf_rho = max(max_surf_rho, abs(s_rho))
        if d_rho is not None:
            max_dot_rho = max(max_dot_rho, abs(d_rho))
        if ov is not None:
            max_overlap = max(max_overlap, float(ov))
    return {
        "peer_unique_blobs_checked": len(blobs),
        "max_abs_surface_spearman": max_surf_rho,
        "max_abs_dot_spearman": max_dot_rho,
        "max_dot_overlap_within_3px": max_overlap,
        "passed": max_surf_rho <= 0.90 and max_dot_rho <= 0.90 and max_overlap <= 0.70,
    }


def run_exact_file_nuisance_audit(dots: np.ndarray, catalogue: np.ndarray, fp: np.ndarray) -> dict:
    """Run C2ST nuisance audit (labels first, then SAHG1 candidate) on road/claim/4-block confounds."""
    confounds.build_all(force=False)
    with np.load(confounds.CONF / "confounds.npz") as npz:
        cfeat = confounds.classifier_features(npz)
    fold_grid, _ = holdout.make_quadrant_folds(fp)
    label_res = c2s2.c2s2_test(
        "training_labels_first",
        catalogue,
        cfeat,
        fold_grid,
        fp,
        n_per_class=8000,
        n_null=99,
        seed=SEED,
    )
    cand_res = c2s2.c2s2_test(
        "sahg1_candidate_exact",
        dots,
        cfeat,
        fold_grid,
        fp,
        n_per_class=8000,
        n_null=99,
        seed=SEED,
    )
    adj_p = c2s2.holm_adjust([label_res.p_value, cand_res.p_value])
    flagged = bool(
        adj_p[1] <= 0.05 and cand_res.observed_auc >= 0.55 and cand_res.margin_vs_p95 >= 0.02
    )
    return {
        "method": "Classifier two-sample test (Lopez-Paz & Oquab, ICLR 2017) with 10 km block label swaps",
        "nuisance_families_only": sorted(cfeat.keys()),
        "block_boundary_status": "derived_audited_not_official_coordinates (audited against published line-km, not official coordinates)",
        "labels_first": {
            "observed_auc": label_res.observed_auc,
            "fold_aucs": label_res.fold_aucs,
            "null_p95": label_res.null_auc_p95,
            "margin_vs_p95": label_res.margin_vs_p95,
            "raw_p_value": label_res.p_value,
            "holm_p_value": adj_p[0],
        },
        "sahg1_candidate": {
            "observed_auc": cand_res.observed_auc,
            "fold_aucs": cand_res.fold_aucs,
            "null_p95": cand_res.null_auc_p95,
            "margin_vs_p95": cand_res.margin_vs_p95,
            "raw_p_value": cand_res.p_value,
            "holm_p_value": adj_p[1],
            "strict_gate_flagged": flagged,
            "strict_gate_passed": not flagged,
        },
        "interpretation": "Association is not causation; roads and historic mining claims correlate with range-front relief and geology.",
    }


def extra_20261025_entries(fp: np.ndarray) -> list[dict]:
    """Include earlier 2026-10-25 research rasters (ASPC and MTR1) in registry novelty checks."""
    extras = []
    for idx, rel in enumerate(
        (
            "docs/downloads/gems24-aspc-20261025-6393e9d9b0df-RESEARCH-NOT-SUBMISSION-zeros.tif",
            "docs/downloads/gems24-mtr1-negative-paired-trough-20261025-ed7243e6d163-zeros.tif",
        ),
        start=1,
    ):
        p = ROOT / rel
        with rasterio.open(p) as ds:
            a = ds.read(1)
        fp_sha = hashlib.sha256(np.asarray(a[fp], dtype="<f4").tobytes()).hexdigest()
        extras.append(
            {
                "id": f"session20261025-{idx:02d}",
                "repo": "buffedlizard55-lab/GEMSDOE24",
                "file": rel,
                "cache_path": rel,
                "sha256": sha256_file(p),
                "footprint_sha256": fp_sha,
                "positive_pixels": int((a[fp] > 0).sum()),
            }
        )
    return extras


def verify_recorded() -> dict:
    exp = json.loads(EXPERIMENT_PATH.read_text())
    card = json.loads(RUN_CARD_PATH.read_text())
    dl = json.loads(DOCS_DOWNLOAD_PATH.read_text())
    template = ROOT / "data/bridge/sample_submission.tif"
    z_path = ROOT / "docs/downloads" / card["submission_name"]
    n_path = ROOT / "docs/downloads" / card["nan_outside_artifact"]
    if sha256_file(z_path) != card["raster_sha256"] or dl["sha256"] != card["raster_sha256"]:
        raise ValueError("SAHG1 primary TIFF checksum mismatch")
    checks = json.loads((ROOT / "docs/downloads" / dl["checks_file"]).read_text())
    if (
        sha256_file(z_path) != checks["zero_outside"]["sha256"]
        or sha256_file(n_path) != checks["nan_outside"]["sha256"]
    ):
        raise ValueError("SAHG1 variant checksum mismatch")
    for k in ("zero_outside", "nan_outside"):
        c = submission.check_variants(ROOT / "docs/downloads" / checks[k]["file"], template)
        if not c["format_valid"] or c["ok_to_upload"] or c["submission_authorized"]:
            raise ValueError(f"SAHG1 validator check failed for {k}")
    if card["verdict"] != "negative" or card["ok_to_submit"] or dl["ok_to_submit"]:
        raise ValueError("SAHG1 fail-closed verdict was weakened")
    return {
        "verified": True,
        "experiment_rerun": False,
        "submission_name": card["submission_name"],
        "raster_sha256": card["raster_sha256"],
        "holdout_dti": card["holdout"]["dti"],
        "ci95": card["holdout"]["ci95"]["interval"],
        "method_lane_novelty_passed": card["correlation_overlap_vs_registry"]["method_lane_passed"],
        "literal_all_entries_passed": card["correlation_overlap_vs_registry"][
            "literal_all_entries_passed"
        ],
        "verdict": card["verdict"],
        "ok_to_submit": card["ok_to_submit"],
        "experiments_run": exp["experiment_number"],
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--verify-recorded", action="store_true")
    args = ap.parse_args()
    if args.verify_recorded:
        print(json.dumps(verify_recorded(), indent=2, allow_nan=False))
        return
    if EXPERIMENT_PATH.exists():
        raise SystemExit(
            "SAHG1 experiment already recorded. No implicit rerun/tuning; use --verify-recorded."
        )

    t0 = time.monotonic()
    fp = footprint.load_footprint()
    template = ROOT / "data/bridge/sample_submission.tif"
    with rasterio.open(ROOT / "data/bridge/labels.tif") as ds:
        catalogue = (ds.read(1) > 0) & fp

    context = holdout.SegmentHoldout(fp, catalogue, buffer_px=15)
    lidar_b, rad_b, ext_b, geophys_b, input_hashes = load_inputs(fp)
    surfaces, support = sahg1.build_surfaces(lidar_b, rad_b, ext_b, geophys_b, fp)

    # Run leakage canaries in memory-bounded batches (no 28-array simultaneous allocation)
    canary_features = {}
    for batch in (
        {f"lidar_{k}": v for k, v in lidar_b.items()},
        {
            **{f"rad_{k}": v for k, v in rad_b.items()},
            **{f"ext_{k}": v for k, v in ext_b.items()},
            "support_mask": support.astype(np.uint8),
        },
        {f"geophys_{k}": v for k, v in geophys_b.items()},
        surfaces,
    ):
        part = context.canary(batch)
        canary_features.update(part["features"])
    del lidar_b, rad_b, ext_b, geophys_b
    __import__("gc").collect()
    canary_report = {
        "diagnostic": "LEAKAGE-CANARY AUC, not a DTI or organizer score",
        "evaluator_version": holdout.MTR_EVALUATOR_VERSION,
        "threshold": 0.90,
        "two_polarities_checked": True,
        "passed": not any(x["leakage_suspected"] for x in canary_features.values()),
        "features": canary_features,
        "interpretation": "AUC > .90 is leakage until explained; lower AUC does not prove independence or fault discovery.",
    }
    if not canary_report["passed"]:
        raise SystemExit("Leakage canary failed on SAHG1 input/factor")
    print("SAHG1 leakage canaries passed:", len(canary_features), "features", flush=True)

    priority_reg = json.loads((ROOT / "registry/priority_rasters.json").read_text())
    extras = extra_20261025_entries(fp)
    surface_novelty = novelty.compare_prospective_registry(
        surfaces["candidate"],
        fp,
        priority_reg["unique_rasters"],
        ROOT,
        extra_entries=extras,
    )
    if not surface_novelty["method_lane_passed"]:
        raise SystemExit("Duplicate surface against a competing method lane; halted")
    print(
        "Pre-placement surface novelty passed:",
        surface_novelty["method_lane_max_abs_rank_correlation"],
        flush=True,
    )

    # Evaluate SAHG1 and Geomorphic-only ablation on SegmentHoldout (gems-segment-pooled-v1)
    arm_preds = {}
    arm_results = {}
    arm_blocks = {}
    yy, xx = np.nonzero(fp)
    nx = (fp.shape[1] + 99) // 100
    active_blocks = np.unique((yy // 100) * nx + xx // 100)

    for arm_name, surf_key in (
        ("geomorphic_core_g0", "geomorphic_core_g0"),
        ("sahg1_candidate", "candidate"),
    ):
        preds = []
        blocks_list = []
        for f in context.folds:
            eligible = support & f["valid"] & ~f["visible"]
            budget = round(BUDGET_FRACTION * int(f["valid"].sum()))
            p = emission.priority_poisson(surfaces[surf_key], eligible, budget, min_dist=3)
            preds.append(p)
            _, blk = context.score_fold(p, f)
            blocks_list.append(blk)
        arm_preds[arm_name] = preds
        arm_results[arm_name] = context.summarize(preds)
        arm_blocks[arm_name] = np.sum(blocks_list, axis=0)[active_blocks]
        print(
            arm_name,
            "HOLDOUT-DTI",
            arm_results[arm_name]["dti"],
            arm_results[arm_name]["ci95"]["interval"],
            flush=True,
        )

    # Next Step 2: Reconstruct same-protocol OOF multi-physics HGB baseline
    print("Reconstructing leakage-free OOF multi-physics baseline...", flush=True)
    oof_preds, _ = build_oof_baseline_predictions(context, fp, support)
    oof_blocks_list = [context.score_fold(p, f)[1] for p, f in zip(oof_preds, context.folds)]
    arm_results["oof_multiphysics_hgb_d3"] = context.summarize(oof_preds)
    arm_blocks["oof_multiphysics_hgb_d3"] = np.sum(oof_blocks_list, axis=0)[active_blocks]
    print(
        "oof_multiphysics_hgb_d3 HOLDOUT-DTI",
        arm_results["oof_multiphysics_hgb_d3"]["dti"],
        arm_results["oof_multiphysics_hgb_d3"]["ci95"]["interval"],
        flush=True,
    )

    paired_vs_g0_ci = holdout.pooled_bootstrap(
        arm_blocks["sahg1_candidate"],
        paired=arm_blocks["geomorphic_core_g0"],
        resamples=1999,
        seed=SEED,
    )
    paired_vs_oof_ci = holdout.pooled_bootstrap(
        arm_blocks["sahg1_candidate"],
        paired=arm_blocks["oof_multiphysics_hgb_d3"],
        resamples=1999,
        seed=SEED,
    )

    # Also evaluate on the 3 km / 20 km ASPC bridge protocol
    bridge_eval = evaluate_bridge_protocol(surfaces["candidate"], fp, catalogue, support)
    print(
        "Bridge protocol (segment-hide-recover-pooled-v1) HOLDOUT-DTI:",
        bridge_eval["dti"],
        bridge_eval["ci95"],
        flush=True,
    )

    # Full-footprint dot placement for SAHG1
    full_budget = round(BUDGET_FRACTION * int(fp.sum()))
    final_dots = emission.priority_poisson(
        surfaces["candidate"], support & ~catalogue, full_budget, min_dist=3
    )
    final_novelty = novelty.compare_prospective_registry(
        final_dots.astype(np.float32),
        fp,
        priority_reg["unique_rasters"],
        ROOT,
        dots=final_dots,
        extra_entries=extras,
    )
    peer_check = check_peer_blobs(surfaces["candidate"], final_dots, fp)
    del surfaces
    __import__("gc").collect()
    if not final_novelty["method_lane_passed"] or not peer_check["passed"]:
        raise SystemExit("Duplicate final dots against a competing method lane; halted")
    print(
        "Final-dot method-lane novelty passed; max overlap vs competing method lanes:",
        final_novelty["method_lane_max_dot_overlap"],
        "peer blobs max overlap:",
        peer_check["max_dot_overlap_within_3px"],
        flush=True,
    )

    # Exact-file C2ST nuisance audit (labels first, then SAHG1 exact dots)
    print("Running exact-file C2ST nuisance audit...", flush=True)
    nuisance_audit = run_exact_file_nuisance_audit(final_dots, catalogue, fp)

    content_id = submission.scored_content_id(final_dots, fp, catalogue)
    sub_name = submission.make_filename(
        "gems24", "sahg1-strike-hydro-geomorph", "20261025", content_id, "zeros"
    )
    nan_name = sub_name.replace("-zeros.tif", "-nan.tif")
    downloads = ROOT / "docs/downloads"
    z_path = submission.write_submission(
        final_dots.astype(np.float32), template, downloads / sub_name, outside="zero"
    )
    n_path = submission.write_submission(
        final_dots.astype(np.float32), template, downloads / nan_name, outside="nan"
    )
    checks = {
        "zero_outside": submission.check_variants(z_path, template),
        "nan_outside": submission.check_variants(n_path, template),
    }
    if not all(c["format_valid"] for c in checks.values()):
        raise SystemExit("Exact-file format validation failed")

    note = f"GEMS24 SAHG1 | strike LiDAR scarp x stable-Th K/U + basement step | research only; DO NOT SUBMIT | id {content_id}"
    if len(note) > 140:
        raise AssertionError(f"Note length {len(note)} exceeds 140 characters")
    note_file = f"note-{sub_name[:-4]}.txt"
    checks_file = f"checks-{sub_name[:-4]}.json"
    (downloads / note_file).write_text(note + "\n")
    save_json(checks, downloads / checks_file)
    write_preview_png(final_dots, fp, PREVIEW_PATH)

    mtr_card = json.loads((ROOT / "evidence/mtr1_run_card.json").read_text())
    beats_oof = (
        arm_results["sahg1_candidate"]["dti"] > arm_results["oof_multiphysics_hgb_d3"]["dti"]
        and paired_vs_oof_ci[0] > 0
    )
    verdict_reasons = [
        "No single assigned method-lane paragraph was supplied in the prompt (provisional lane)",
        "Literal all-entry overlap rule still flags synthetic spacing-5 calibration lattice registry-039 (1.0 overlap within 3 px), though all 46 competing method lanes and 83 peer blobs pass (max overlap <= 0.70)",
        "Promotion to a weekly competition slot requires a separate selector step within verified portal quota",
    ]
    if not beats_oof:
        verdict_reasons.insert(
            0,
            f"Did not beat reconstructed same-protocol OOF multi-physics HGB baseline ({arm_results['sahg1_candidate']['dti']:.5f} vs {arm_results['oof_multiphysics_hgb_d3']['dti']:.5f})",
        )
    if not nuisance_audit["sahg1_candidate"]["strict_gate_passed"]:
        verdict_reasons.append(
            f"Exact-file C2ST nuisance audit flagged accessibility/block association (AUC {nuisance_audit['sahg1_candidate']['observed_auc']:.4f}, Holm p={nuisance_audit['sahg1_candidate']['holm_p_value']:.3f})"
        )

    experiment = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "hypothesis": "H24-SAHG1 strike-aligned hydrothermal-geomorphic conduit detector (saturating strike-projected 3DEP LiDAR scarp x stable-Th K/U alteration x basement/strain step)",
        "preregistration": "knowledge/12_preregistered_SAHG1_2026-10-25.md",
        "preregistration_commit": "8ea2d46",
        "experiment_number": 1,
        "experiments_authorized": 1,
        "maximum_experiments": 3,
        "maximum_session_hours": 2,
        "input_provenance": "hash-pinned local/owner caches verified before execution; no automated DrivenData access",
        "inputs": input_hashes,
        "receptive_field_support": {
            "stencil_radius_px": sahg1.STENCIL_RADIUS_PX,
            "stencil_window_m": (2 * sahg1.STENCIL_RADIUS_PX + 1) * 100,
            "supported_pixels": int(support.sum()),
            "complete_discrete_support_verified": True,
        },
        "catalogue_features": [],
        "prediction_inputs_include_registry_rasters": False,
        "canary": canary_report,
        "surface_novelty": surface_novelty,
        "final_novelty": final_novelty,
        "peer_blob_novelty": peer_check,
        "results": arm_results,
        "paired_comparisons": {
            "sahg1_minus_geomorphic_core_g0": {
                "delta_dti": arm_results["sahg1_candidate"]["dti"]
                - arm_results["geomorphic_core_g0"]["dti"],
                "ci95": paired_vs_g0_ci,
            },
            "sahg1_minus_reconstructed_oof_hgb_d3": {
                "delta_dti": arm_results["sahg1_candidate"]["dti"]
                - arm_results["oof_multiphysics_hgb_d3"]["dti"],
                "ci95": paired_vs_oof_ci,
            },
            "sahg1_minus_recorded_mtr1": {
                "delta_dti": arm_results["sahg1_candidate"]["dti"]
                - float(mtr_card["holdout"]["dti"]),
                "recorded_mtr1_dti": float(mtr_card["holdout"]["dti"]),
                "recorded_mtr1_ci95": list(mtr_card["holdout"]["ci95"]["interval"]),
            },
        },
        "bridge_protocol_evaluation": bridge_eval,
        "exact_file_nuisance_audit": nuisance_audit,
        "artifact": {
            "file": sub_name,
            "nan_file": nan_name,
            "sha256": sha256_file(z_path),
            "nan_sha256": sha256_file(n_path),
            "content_id": content_id,
            "pixel_count": int(final_dots.sum()),
            "note": note,
            "note_file": note_file,
            "checks_file": checks_file,
        },
        "verdict": "negative",
        "ok_to_download": True,
        "ok_to_submit": False,
        "submission_slot_spent": False,
        "organizer_confirmed_score": None,
        "verdict_reasons": verdict_reasons,
        "elapsed_seconds": round(time.monotonic() - t0, 3),
    }
    save_json(experiment, EXPERIMENT_PATH)

    run_card = {
        "hypothesis": experiment["hypothesis"],
        "mechanism": "Saturating strike-projected 3DEP LiDAR antislope scarp (G_sat) with pluvial-shoreline contour-obliquity filter, multiplied by immobile-Th-controlled mobile K/U alteration (R_alt) and subsurface gravity/magnetic/basement-step + strain corroboration (B_step) inside a complete 9x9 discrete receptive-field support mask",
        "named_non_fault_mimic": "Pleistocene pluvial Lake Lahontan tufa-cemented beach bars or welded-tuff stratigraphic ledges cutting across alluvial fan lobes",
        "holdout": arm_results["sahg1_candidate"],
        "geomorphic_only_ablation": arm_results["geomorphic_core_g0"],
        "reconstructed_oof_multiphysics_baseline": arm_results["oof_multiphysics_hgb_d3"],
        "bridge_protocol_holdout": bridge_eval,
        "paired_comparisons": experiment["paired_comparisons"],
        "correlation_overlap_vs_registry": {
            "total_unique_rasters_checked": final_novelty["registry_unique_rasters"],
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
            "method_lane_passed": bool(
                final_novelty["method_lane_passed"] and peer_check["passed"]
            ),
            "literal_all_entries_passed": bool(final_novelty["literal_all_entries_passed"]),
            "passed": bool(final_novelty["literal_all_entries_passed"]),
            "scope": priority_reg["scope"] + " + 2026-10-25 ASPC and MTR1 research rasters",
        },
        "exact_file_nuisance_audit": nuisance_audit["sahg1_candidate"],
        "raster_sha256": checks["zero_outside"]["sha256"],
        "nan_outside_artifact": nan_name,
        "nan_outside_sha256": checks["nan_outside"]["sha256"],
        "validator_output": checks["zero_outside"],
        "submission_name": sub_name,
        "note": note,
        "verdict": "negative",
        "ok_to_download": True,
        "ok_to_submit": False,
        "reasons": verdict_reasons,
        "organizer_confirmed_score": None,
        "experiments_run": 1,
        "submission_slots_used": 0,
    }
    save_json(run_card, RUN_CARD_PATH)
    save_json(run_card, DOCS_CARD_PATH)
    save_json(experiment, ROOT / "docs/data/sahg1_experiment_20261025.json")

    dl_packet = {
        "file": sub_name,
        "nan_file": nan_name,
        "sha256": checks["zero_outside"]["sha256"],
        "nan_sha256": checks["nan_outside"]["sha256"],
        "content_id": content_id,
        "pixel_count": int(final_dots.sum()),
        "note": note,
        "note_file": note_file,
        "checks_file": checks_file,
        "generation": "independent-sahg1-v1",
        "format_valid": True,
        "ok_to_download": True,
        "ok_to_submit": False,
        "slot_recommendation": "not_recommended",
        "verdict": "negative",
        "live_dti": None,
        "run_card": "sahg1_run_card.json",
        "independently_computed": True,
        "method_lane_uniqueness_passed": bool(
            final_novelty["method_lane_passed"] and peer_check["passed"]
        ),
        "literal_lattice_uniqueness_passed": bool(final_novelty["literal_all_entries_passed"]),
    }
    save_json(dl_packet, DOCS_DOWNLOAD_PATH)
    print(json.dumps(verify_recorded(), indent=2, allow_nan=False), flush=True)


if __name__ == "__main__":
    main()
