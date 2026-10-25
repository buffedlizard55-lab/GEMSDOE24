#!/usr/bin/env python3
"""Execute or verify the preregistered H24-RSHG1 streaming multi-physics OOF lane.

Spec locked before execution in ``knowledge/17_preregistered_RSHG1_2026-10-25.md``:
- Streams 42 physical/geomorphic/hydrothermal/tilt-angle/curvature channels into
  ``data/prepared/rshg1_features.npy`` (<1.6 GiB RSS on 3.8 GiB RAM, 0 swap).
- Runs two-polarity single-feature leakage canaries across all 42 channels before
  training or placement.
- Fits training-only ``NanPreservingResidualizer`` + 2-seed regularized
  ``HistGradientBoostingClassifier`` + ``RegimeNuisanceCalibrator`` strictly on
  ``fold["train"]`` across 100% of the competition footprint (routing the 31.8%
  3DEP LiDAR gap via ``NaN`` splits instead of blacking it out).
- Evaluates primary ``HOLDOUT-DTI`` on ``gems-segment-pooled-v1`` (1.5 km collar,
  60,988 withheld positives, 10 km block bootstrap, 1,999 draws) with exact paired
  block-bootstrap CIs against ``oof_multiphysics_hgb_d3`` (0.13000) and diagnostic
  ablations, plus a leak-free 3.0 km ``segment-hide-recover-pooled-v1`` bridge run.
- Audits pre-placement surface & final dots against all competing method lanes
  (priority registry + ASPC + MTR1 + SAHG1 + CON), 83 peer blobs, and literal
  calibration controls, and runs the exact-file C2ST nuisance audit (``gems.c2s2``).
- Never contacts DrivenData and never spends a weekly submission slot.
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import os
import resource
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import struct  # noqa: E402
import zlib  # noqa: E402

import numpy as np  # noqa: E402
import rasterio  # noqa: E402
from scipy.ndimage import binary_erosion, distance_transform_edt  # noqa: E402
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
    preflight,
    rshg1,
    sahg1,
    submission,
)
from gems.validator import sha256_file  # noqa: E402

BUDGET_FRAC = 0.0073
SEED = 20261025
HGB_PARAMS = dict(
    max_iter=140,
    max_leaf_nodes=31,
    min_samples_leaf=80,
    learning_rate=0.06,
    l2_regularization=8.0,
    early_stopping=False,
)
BASELINE_HGB_PARAMS = dict(
    max_iter=80,
    max_leaf_nodes=15,
    learning_rate=0.08,
    l2_regularization=5.0,
    early_stopping=False,
    random_state=SEED,
)

MEMMAP_PATH = ROOT / "data/prepared/rshg1_features.npy"
EXPERIMENT_JSON = ROOT / "evidence/rshg1_experiment_20261025.json"
RUN_CARD_JSON = ROOT / "evidence/rshg1_run_card_20261025.json"
DOCS_RUN_CARD_JSON = ROOT / "docs/data/rshg1_run_card.json"
DOCS_DOWNLOAD_JSON = ROOT / "docs/data/rshg1_download.json"
PREVIEW_PNG = ROOT / "docs/assets/rshg1-preview.png"


def save_json(obj: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n")


def peak_rss_mib() -> float:
    return float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) / 1024.0


def strict_whole_array_ok(check_dict: dict[str, Any]) -> bool:
    return bool(
        check_dict.get("checks", {})
        .get("variant_strict_whole_array_no_nan_allowed", {})
        .get("pass")
    )


def verify_recorded() -> dict[str, Any]:
    """Verify frozen RSHG1 receipts, exact GeoTIFF pair, preflight, and <=140-char note."""
    for p in (EXPERIMENT_JSON, RUN_CARD_JSON, DOCS_RUN_CARD_JSON, DOCS_DOWNLOAD_JSON, PREVIEW_PNG):
        if not p.exists():
            raise SystemExit(f"Missing recorded RSHG1 artifact: {p}")
    exp = json.loads(EXPERIMENT_JSON.read_text())
    card = json.loads(RUN_CARD_JSON.read_text())
    docs_card = json.loads(DOCS_RUN_CARD_JSON.read_text())
    dl = json.loads(DOCS_DOWNLOAD_JSON.read_text())
    if card != docs_card:
        raise SystemExit("Evidence and docs/data RSHG1 run cards disagree")
    if (
        card["verdict"] != "negative"
        or card["ok_to_submit"] is not False
        or dl["ok_to_submit"] is not False
    ):
        raise SystemExit("Recorded RSHG1 packet must remain fail-closed until separate selector")

    template = ROOT / "data/bridge/sample_submission.tif"
    zeros_path = ROOT / "docs/downloads" / card["submission_name"]
    nan_path = ROOT / "docs/downloads" / card["nan_outside_artifact"]
    checks_path = ROOT / "docs/downloads" / dl["checks_file"]
    note_path = ROOT / "docs/downloads" / dl["note_file"]
    preflight_path = zeros_path.with_suffix(".preflight.json")

    if sha256_file(zeros_path) != card["raster_sha256"] or dl["sha256"] != card["raster_sha256"]:
        raise SystemExit("RSHG1 zero-outside GeoTIFF SHA-256 mismatch")
    if (
        sha256_file(nan_path) != card["nan_outside_sha256"]
        or dl["nan_sha256"] != card["nan_outside_sha256"]
    ):
        raise SystemExit("RSHG1 NaN-outside GeoTIFF SHA-256 mismatch")

    fresh_zero = submission.check_variants(zeros_path, template)
    fresh_nan = submission.check_variants(nan_path, template)
    recorded_checks = json.loads(checks_path.read_text())
    if (
        not fresh_zero["format_valid"]
        or not fresh_nan["format_valid"]
        or not strict_whole_array_ok(fresh_zero)
        or recorded_checks["zero_outside"]["sha256"] != card["raster_sha256"]
        or recorded_checks["nan_outside"]["sha256"] != card["nan_outside_sha256"]
    ):
        raise SystemExit("RSHG1 exact-file format/range validator check failed")

    note_text = note_path.read_text().strip()
    if len(note_text) > 140 or note_text != card["note"] or note_text != dl["note"]:
        raise SystemExit("RSHG1 note missing, mismatched, or >140 chars")

    pre = json.loads(preflight_path.read_text())
    if (
        pre.get("artifact", {}).get("sha256") != card["raster_sha256"]
        or pre.get("run_card", {}).get("artifact_sha256_matches") is not True
        or pre.get("run_card", {}).get("artifact_name_matches") is not True
        or pre.get("decision", {}).get("submission_status") != "DO_NOT_SUBMIT"
        or pre.get("decision", {}).get("ready_to_submit") is not False
        or pre.get("portal_range_diagnostic", {}).get("strict_whole_array_values_in_0_1")
        is not True
    ):
        raise SystemExit("RSHG1 preflight receipt missing, stale, or not fail-closed")

    return {
        "verified": True,
        "experiment_rerun": False,
        "submission_name": card["submission_name"],
        "raster_sha256": card["raster_sha256"],
        "holdout_dti": card["holdout"]["dti"],
        "oof_baseline_dti": card["reconstructed_oof_multiphysics_baseline"]["dti"],
        "c2st_auc": card["exact_file_nuisance_audit"]["observed_auc"],
        "technical_promotion_gates_passed": card["technical_promotion_gates_passed"],
        "verdict": card["verdict"],
        "ok_to_submit": card["ok_to_submit"],
        "preregistration": exp["preregistration"],
    }


def _png_chunk(tag: bytes, data: bytes) -> bytes:
    crc = zlib.crc32(tag + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)


def write_preview(dots: np.ndarray, fp: np.ndarray, out_path: Path, step: int = 6) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    h, w = fp.shape
    sh, sw = h // step, w // step
    fp_small = fp[: sh * step, : sw * step].reshape(sh, step, sw, step).any(axis=(1, 3))
    d_small = dots[: sh * step, : sw * step].reshape(sh, step, sw, step).any(axis=(1, 3))
    rgb = np.full((sh, sw, 3), (244, 241, 234), dtype=np.uint8)
    rgb[fp_small] = (224, 232, 226)
    rgb[d_small] = (15, 118, 110)
    raw = b"".join(b"\x00" + rgb[y].tobytes() for y in range(sh))
    ihdr = struct.pack(">IIBBBBB", sw, sh, 8, 2, 0, 0, 0)
    png = (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", ihdr)
        + _png_chunk(b"IDAT", zlib.compress(raw, level=9))
        + _png_chunk(b"IEND", b"")
    )
    out_path.write_bytes(png)


def run_streaming_canary(
    context: holdout.SegmentHoldout, mm: np.memmap, fp: np.ndarray, batch_size: int = 4
) -> dict[str, Any]:
    """Run SegmentHoldout.canary in small 2D batches so RSS stays <250 MiB."""
    fp_ids = np.flatnonzero(fp)
    merged_features: dict[str, Any] = {}
    last_meta: dict[str, Any] = {}
    for start in range(0, len(rshg1.FEATURE_NAMES), batch_size):
        batch_dict: dict[str, np.ndarray] = {}
        for j in range(start, min(start + batch_size, len(rshg1.FEATURE_NAMES))):
            grid = np.full(fp.shape, np.nan, dtype=np.float32)
            grid.ravel()[fp_ids] = mm[:, j]
            batch_dict[rshg1.FEATURE_NAMES[j]] = grid
        rep = context.canary(batch_dict, seed=SEED, max_per_class=15000)
        merged_features.update(rep["features"])
        last_meta = rep
        del batch_dict
        gc.collect()
    passed = not any(v["leakage_suspected"] for v in merged_features.values())
    worst_name = max(
        merged_features,
        key=lambda k: max(merged_features[k]["pooled_auc"], 1.0 - merged_features[k]["pooled_auc"]),
    )
    worst_auc = merged_features[worst_name]["pooled_auc"]
    return {
        "diagnostic": last_meta["diagnostic"],
        "evaluator_version": last_meta["evaluator_version"],
        "threshold": last_meta["threshold"],
        "two_polarities_checked": True,
        "passed": passed,
        "n_features_checked": len(merged_features),
        "worst_feature": worst_name,
        "worst_pooled_auc": worst_auc,
        "worst_polarity_extremity": max(worst_auc, 1.0 - worst_auc),
        "features": merged_features,
        "interpretation": last_meta["interpretation"],
    }


def predict_in_chunks(
    models: list[HistGradientBoostingClassifier],
    resid: rshg1.NanPreservingResidualizer | None,
    calibrator: rshg1.RegimeNuisanceCalibrator | None,
    mm: np.memmap,
    nuisance_fp: np.ndarray,
    fp_row_indices: np.ndarray,
    *,
    chunk_size: int = 200_000,
) -> np.ndarray:
    """Predict calibrated or raw ensemble probabilities in bounded memory chunks."""
    out = np.empty(len(fp_row_indices), dtype=np.float32)
    for start in range(0, len(fp_row_indices), chunk_size):
        sub = fp_row_indices[start : start + chunk_size]
        x_raw = np.asarray(mm[sub], dtype=np.float32)
        c_sub = nuisance_fp[sub]
        x_in = resid.transform(c_sub, x_raw, remove=True) if resid is not None else x_raw
        p_sum = np.zeros(len(sub), dtype=np.float64)
        for m in models:
            p_sum += m.predict_proba(x_in)[:, 1]
        p_mean = (p_sum / float(len(models))).astype(np.float32)
        if calibrator is not None:
            has_lidar = np.isfinite(x_raw[:, rshg1.G_SAT_INDEX])
            p_mean = calibrator.transform(p_mean, has_lidar, c_sub)
        out[start : start + chunk_size] = p_mean
    return out


def fit_fold_models(
    mm: np.memmap,
    nuisance_fp: np.ndarray,
    fp_ids: np.ndarray,
    train_mask: np.ndarray,
    visible_mask: np.ndarray,
    *,
    fold_seed_base: int,
    fit_raw_ablation: bool = False,
) -> tuple[
    list[HistGradientBoostingClassifier],
    rshg1.NanPreservingResidualizer,
    rshg1.RegimeNuisanceCalibrator,
    list[HistGradientBoostingClassifier] | None,
]:
    """Fit training-only residualizer, 2-seed HGB ensemble, and background calibrator."""
    dist_vis = distance_transform_edt(~visible_mask)
    pos_mask = train_mask & visible_mask
    neg_mask = train_mask & (~visible_mask) & (dist_vis >= 9.0)
    bg_mask = train_mask & (~visible_mask)
    del dist_vis

    pos_rows = np.flatnonzero(pos_mask.ravel()[fp_ids])
    neg_rows = np.flatnonzero(neg_mask.ravel()[fp_ids])
    bg_rows = np.flatnonzero(bg_mask.ravel()[fp_ids])
    del pos_mask, neg_mask, bg_mask

    if len(pos_rows) < 200 or len(neg_rows) < 600:
        raise RuntimeError("Insufficient training positives/negatives in fold")

    rng_bg = np.random.default_rng(fold_seed_base + 77)
    bg_sel = rng_bg.choice(bg_rows, min(30_000, len(bg_rows)), replace=False)
    bg_sel.sort()
    x_bg_raw = np.asarray(mm[bg_sel], dtype=np.float32)
    c_bg = nuisance_fp[bg_sel]
    resid = rshg1.NanPreservingResidualizer(alpha=100.0).fit(c_bg, x_bg_raw)

    models_cal: list[HistGradientBoostingClassifier] = []
    models_raw: list[HistGradientBoostingClassifier] | None = [] if fit_raw_ablation else None

    for s_idx in range(2):
        seed_s = fold_seed_base + s_idx
        rng_s = np.random.default_rng(seed_s)
        p_sel = rng_s.choice(pos_rows, min(30_000, len(pos_rows)), replace=False)
        n_sel = rng_s.choice(neg_rows, min(90_000, len(neg_rows)), replace=False)
        tr_rows = np.r_[p_sel, n_sel]
        y_tr = np.r_[np.ones(len(p_sel), dtype=np.int8), np.zeros(len(n_sel), dtype=np.int8)]
        x_tr_raw = np.asarray(mm[tr_rows], dtype=np.float32)
        c_tr = nuisance_fp[tr_rows]
        x_tr_res = resid.transform(c_tr, x_tr_raw, remove=True)

        m_cal = HistGradientBoostingClassifier(**HGB_PARAMS, random_state=seed_s)
        m_cal.fit(x_tr_res, y_tr)
        models_cal.append(m_cal)

        if models_raw is not None:
            m_raw = HistGradientBoostingClassifier(**HGB_PARAMS, random_state=seed_s)
            m_raw.fit(x_tr_raw, y_tr)
            models_raw.append(m_raw)

        del x_tr_raw, x_tr_res, c_tr, tr_rows, y_tr
    gc.collect()

    x_bg_res = resid.transform(c_bg, x_bg_raw, remove=True)
    p_bg = 0.5 * (
        models_cal[0].predict_proba(x_bg_res)[:, 1] + models_cal[1].predict_proba(x_bg_res)[:, 1]
    )
    has_lidar_bg = np.isfinite(x_bg_raw[:, rshg1.G_SAT_INDEX])
    calibrator = rshg1.RegimeNuisanceCalibrator(alpha=100.0).fit(p_bg, has_lidar_bg, c_bg)
    del x_bg_raw, x_bg_res, c_bg, p_bg, pos_rows, neg_rows, bg_rows
    gc.collect()

    return models_cal, resid, calibrator, models_raw


def build_recorded_oof_baseline(
    context: holdout.SegmentHoldout,
    prep_path: Path,
    base_count: int,
    sahg1_support: np.ndarray,
    fp: np.ndarray,
) -> list[np.ndarray]:
    """Reproduce exact oof_multiphysics_hgb_d3 predictions for paired block bootstrap."""
    stack = np.load(prep_path, mmap_mode="r")
    fp_ids = np.flatnonzero(fp)
    preds: list[np.ndarray] = []
    for fold in context.folds:
        fid = int(fold["id"])
        rng = np.random.default_rng(SEED + fid)
        dist_vis = distance_transform_edt(~fold["visible"])
        pos = np.flatnonzero((fold["train"] & fold["visible"]).ravel()[fp_ids])
        neg = np.flatnonzero((fold["train"] & ~fold["visible"] & (dist_vis >= 9)).ravel()[fp_ids])
        del dist_vis
        p_sel = rng.choice(pos, min(20_000, len(pos)), replace=False)
        n_sel = rng.choice(neg, min(60_000, len(neg)), replace=False)
        tr = np.r_[p_sel, n_sel]
        y = np.r_[np.ones(len(p_sel), dtype=np.int8), np.zeros(len(n_sel), dtype=np.int8)]
        X_tr = np.asarray(stack[tr, :base_count], dtype=np.float32)
        params = {**BASELINE_HGB_PARAMS, "random_state": SEED + fid}
        model = HistGradientBoostingClassifier(**params).fit(X_tr, y)
        val_rows = np.flatnonzero(fold["valid"].ravel()[fp_ids])
        score = np.zeros(fp.shape, dtype=np.float32)
        for b in range(0, len(val_rows), 150_000):
            ii = val_rows[b : b + 150_000]
            score.ravel()[fp_ids[ii]] = model.predict_proba(
                np.asarray(stack[ii, :base_count], dtype=np.float32)
            )[:, 1].astype(np.float32)
        eligible = sahg1_support & fold["valid"] & ~fold["visible"]
        k = int(round(BUDGET_FRAC * int(fold["valid"].sum())))
        preds.append(emission.priority_poisson(score, eligible, k, min_dist=3))
        del X_tr, score, model
        gc.collect()
    return preds


def summarize_with_blocks(
    context: holdout.SegmentHoldout, predictions: list[np.ndarray]
) -> tuple[dict[str, Any], np.ndarray]:
    summary = context.summarize(predictions, ci_draws=1999)
    block_rows = []
    for pred, fold in zip(predictions, context.folds):
        _, blocks = context.score_fold(pred, fold)
        block_rows.append(blocks)
    total_blocks = np.sum(block_rows, axis=0)
    yy, xx = np.nonzero(context.footprint)
    nx = (context.footprint.shape[1] + 99) // 100
    active = np.unique((yy // 100) * nx + xx // 100)
    return summary, total_blocks[active]


def paired_delta_summary(
    summary_a: dict[str, Any],
    blocks_a: np.ndarray,
    summary_b: dict[str, Any],
    blocks_b: np.ndarray,
) -> dict[str, Any]:
    ci = holdout.pooled_bootstrap(blocks_a, paired=blocks_b, resamples=1999, seed=SEED)
    return {
        "delta_dti": float(summary_a["dti"] - summary_b["dti"]),
        "ci95": ci,
        "ci95_strictly_positive": bool(ci[0] > 0.0),
    }


def evaluate_bridge_3km(
    mm: np.memmap,
    nuisance_fp: np.ndarray,
    fp: np.ndarray,
    catalogue: np.ndarray,
) -> dict[str, Any]:
    """Run leak-free 3.0 km buffer_px=30 OOF pass on segment-hide-recover-pooled-v1."""
    fp_ids = np.flatnonzero(fp)
    tile_rows_all = []
    fold_details = []
    for fold in holdout.segment_folds(fp, catalogue, buffer_px=30):
        fid = int(fold["fold"])
        models_cal, resid, calibrator, _ = fit_fold_models(
            mm,
            nuisance_fp,
            fp_ids,
            fold["training"],
            fold["visible"],
            fold_seed_base=SEED + 500 + 10 * fid,
            fit_raw_ablation=False,
        )
        test_rows = np.flatnonzero(fold["test"].ravel()[fp_ids])
        p_test = predict_in_chunks(models_cal, resid, calibrator, mm, nuisance_fp, test_rows)
        prob_map = np.zeros(fp.shape, dtype=np.float32)
        prob_map.ravel()[fp_ids[test_rows]] = p_test
        dots = rshg1.emit_rshg1_dots(
            prob_map,
            fold["test"],
            fold["visible"],
            budget_frac=BUDGET_FRAC,
            min_dist=3.0,
            flank_clearance_px=2.0,
            use_kernel_trace=True,
        )
        t_rows, ref = holdout.spatial_components(
            dots, fold["hidden"] & fold["test"], fold["test"], fold["visible"], tile_px=200
        )
        tile_rows_all.append(t_rows)
        fold_details.append({"fold": fold["name"], **ref})
        del models_cal, resid, calibrator, prob_map, dots
        gc.collect()

    summed_tiles = np.sum(tile_rows_all, axis=0)
    yy, xx = np.nonzero(fp)
    nx = (fp.shape[1] + 199) // 200
    active_tiles = np.unique((yy // 200) * nx + xx // 200)
    pooled = holdout.pooled_components(fold_details)
    ci95 = holdout.pooled_bootstrap(summed_tiles[active_tiles], resamples=1000, seed=SEED)
    aspc_report = json.loads((ROOT / "evidence/aspc_run_20261025.json").read_text())
    sahg1_card = json.loads((ROOT / "evidence/sahg1_run_card_20261025.json").read_text())
    rec_aspc = float(aspc_report["holdout"]["value"])
    rec_aspc_ctrl = float(aspc_report["holdout"]["control_value"])
    rec_sahg1_bridge = float(sahg1_card["bridge_protocol_holdout"]["dti"])
    return {
        "label": "HOLDOUT-DTI",
        "evaluator_version": holdout.SEGMENT_EVALUATOR_VERSION,
        "dti": pooled["dti"],
        "ci95": ci95,
        "n_withheld_positives": int(pooled["n_truth"]),
        "n_emitted": int(pooled["n_emitted"]),
        "buffer_m": 3000,
        "recorded_aspc_dti": rec_aspc,
        "recorded_aspc_scarp_control_dti": rec_aspc_ctrl,
        "delta_vs_recorded_aspc": float(pooled["dti"] - rec_aspc),
        "delta_vs_recorded_aspc_control": float(pooled["dti"] - rec_aspc_ctrl),
        "recorded_sahg1_bridge_dti": rec_sahg1_bridge,
        "delta_vs_recorded_sahg1_bridge": float(pooled["dti"] - rec_sahg1_bridge),
        "folds": fold_details,
    }


def extra_20261025_entries(fp: np.ndarray) -> list[dict[str, Any]]:
    """Collect all 4 local 2026-10-25 method lanes (ASPC, MTR1, SAHG1, CON) for novelty check."""
    extras = [
        (
            "local-20261025-aspc",
            "docs/downloads/gems24-aspc-20261025-6393e9d9b0df-RESEARCH-NOT-SUBMISSION-zeros.tif",
        ),
        (
            "local-20261025-mtr1",
            "docs/downloads/gems24-mtr1-negative-paired-trough-20261025-ed7243e6d163-zeros.tif",
        ),
        (
            "local-20261025-sahg1",
            "docs/downloads/gems24-sahg1-strike-hydro-geomorph-20261025-13d01f28d5db-zeros.tif",
        ),
        (
            "local-20261025-con",
            "docs/downloads/gems24-con-claycap-strain-saddle-20261025-ded121060878-zeros.tif",
        ),
    ]
    out: list[dict[str, Any]] = []
    for eid, rel in extras:
        p = ROOT / rel
        if not p.exists():
            raise FileNotFoundError(f"Expected local 2026-10-25 comparator missing: {p}")
        with rasterio.open(p) as ds:
            a = ds.read(1)
        fp_sha = hashlib.sha256(np.asarray(a[fp], dtype="<f4").tobytes()).hexdigest()
        out.append(
            {
                "id": eid,
                "repo": "buffedlizard55-lab/GEMSDOE24",
                "file": rel,
                "cache_path": rel,
                "sha256": sha256_file(p),
                "footprint_sha256": fp_sha,
                "positive_pixels": int((a[fp] > 0).sum()),
            }
        )
    return out


def check_peer_blobs(
    surface: np.ndarray, dots: np.ndarray | None, fp: np.ndarray
) -> dict[str, Any]:
    """Check all 83 competition-grid blobs in registry/peer_rasters_20261025.json."""
    peer_reg = json.loads((ROOT / "registry/peer_rasters_20261025.json").read_text())["entries"]
    blobs: dict[str, dict[str, Any]] = {}
    for row in peer_reg:
        if row.get("role") == "format_demo_not_submission":
            continue
        blobs.setdefault(row["blob"], row)
    surf_ranks = rankdata(surface[fp])
    dot_ranks = rankdata(dots[fp].astype(np.float32)) if dots is not None else None
    max_surf_rho = 0.0
    max_dot_rho = 0.0
    max_overlap = 0.0
    for row in blobs.values():
        p = ROOT / row["cache_path"]
        with rasterio.open(p) as ds:
            a = ds.read(1)
        s_rho = novelty.rank_correlation(surf_ranks, a[fp])
        if s_rho is not None:
            max_surf_rho = max(max_surf_rho, abs(float(s_rho)))
        if dots is not None and dot_ranks is not None:
            d_rho = novelty.rank_correlation(dot_ranks, a[fp])
            ov = novelty.dot_overlap(dots, fp & (a > 0))["candidate_within_3px_of_reference"]
            if d_rho is not None:
                max_dot_rho = max(max_dot_rho, abs(float(d_rho)))
            if ov is not None:
                max_overlap = max(max_overlap, float(ov))
    passed = max_surf_rho <= 0.90 and (
        dots is None or (max_dot_rho <= 0.90 and max_overlap <= 0.70)
    )
    return {
        "peer_unique_blobs_checked": len(blobs),
        "max_abs_surface_spearman": max_surf_rho,
        "max_abs_dot_spearman": max_dot_rho if dots is not None else None,
        "max_dot_overlap_within_3px": max_overlap if dots is not None else None,
        "passed": passed,
    }


def run_exact_file_c2st(zeros_path: Path, fp: np.ndarray, labels: np.ndarray) -> dict[str, Any]:
    """Run exact-file C2ST nuisance audit (labels first, then written candidate raster)."""
    with np.load(confounds.CONF / "confounds.npz") as cache:
        feats = confounds.classifier_features(cache)
    fold_grid, _ = holdout.make_quadrant_folds(fp)
    h, w = fp.shape
    yy, xx = np.ogrid[:h, :w]
    spatial_block = (yy // 100) * ((w + 99) // 100) + xx // 100
    purge = {}
    for fid in range(4):
        collar = distance_transform_edt(fold_grid != fid) <= 15
        purge[fid] = np.unique(spatial_block[collar & fp])

    with rasterio.open(zeros_path) as ds:
        cand_mask = (ds.read(1) > 0.5) & fp

    res_labels = c2s2.c2s2_test(
        "labels",
        labels,
        feats,
        fold_grid,
        fp,
        n_null=199,
        n_per_class=12_000,
        null_mode="grouped",
        seed=20261002,
        purge_groups=purge,
    ).as_dict()
    res_cand = c2s2.c2s2_test(
        "rshg1_candidate",
        cand_mask,
        feats,
        fold_grid,
        fp,
        n_null=199,
        n_per_class=12_000,
        null_mode="grouped",
        seed=20261002,
        purge_groups=purge,
    ).as_dict()
    shift_cand = c2s2.c2s2_test(
        "rshg1_candidate_shift",
        cand_mask,
        feats,
        fold_grid,
        fp,
        n_null=99,
        n_per_class=12_000,
        null_mode="shift",
        seed=20261002,
        purge_groups=purge,
        shift_fn=lambda dy, dx, ref=cand_mask: np.roll(ref, (dy, dx), axis=(0, 1)),
    ).as_dict()

    near, far, _ = c2s2.near_far_masks(cand_mask)
    singles = {}
    for fname in sorted(feats):
        X, y, f, info = c2s2.build_matrix(
            {fname: feats[fname]}, near, far, fold_grid, fp, 12_000, 20261002
        )
        auc_f, _ = c2s2.spatial_cv_auc(
            c2s2.make_model(seed=20261002),
            X,
            y,
            f,
            groups=info["spatial_blocks"],
            purge_groups=purge,
        )
        singles[fname] = float(auc_f)

    holm_l, holm_c = c2s2.holm_adjust([res_labels["p_value"], res_cand["p_value"]])
    res_labels["holm_p_value"] = float(holm_l)
    res_cand["holm_p_value"] = float(holm_c)
    flagged = bool(
        holm_c <= 0.05 and res_cand["observed_auc"] >= 0.55 and res_cand["margin_vs_p95"] >= 0.02
    )
    return {
        "protocol_seed": 20261002,
        "features": sorted(feats),
        "samples_per_class": 12_000,
        "grouped_permutations": 199,
        "shift_diagnostics": 99,
        "labels_first": {
            "observed_auc": res_labels["observed_auc"],
            "null_p95": res_labels["null_auc_p95"],
            "p_value": res_labels["p_value"],
            "holm_p_value": float(holm_l),
        },
        "observed_auc": res_cand["observed_auc"],
        "null_p95": res_cand["null_auc_p95"],
        "margin_vs_p95": res_cand["margin_vs_p95"],
        "p_value": res_cand["p_value"],
        "holm_p_value": float(holm_c),
        "shift_diagnostic_p_value": shift_cand["p_value"],
        "single_feature_auc_descriptive": singles,
        "flagged_association": flagged,
        "strict_gate_passed": not flagged,
        "recorded_sahg1_auc": 0.5825909290437927,
        "delta_auc_vs_sahg1": float(res_cand["observed_auc"] - 0.5825909290437927),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--verify-recorded", action="store_true")
    args = ap.parse_args()

    if args.verify_recorded:
        print(json.dumps(verify_recorded(), indent=2, allow_nan=False))
        return

    if EXPERIMENT_JSON.exists():
        raise SystemExit(
            f"{EXPERIMENT_JSON} already exists; refusing implicit rerun of preregistered experiment. "
            "Use --verify-recorded to validate frozen outputs."
        )

    t0 = time.monotonic()
    with threadpool_limits(limits=2):
        template = ROOT / "data/bridge/sample_submission.tif"
        labels_path = ROOT / "data/bridge/labels.tif"
        training_tif = ROOT / "data/training_features.tif"
        prep_path = ROOT / "data/prepared/features.npy"
        prep_meta = json.loads((ROOT / "data/prepared/features.json").read_text())
        lidar_path = ROOT / "data/external/lidar_scarp_features_u8.tif"
        lidar_meta = json.loads(lidar_path.with_name("lidar_scarp_features.json").read_text())
        rad_path = ROOT / "data/external/geodawn_rad_u8.tif"
        rad_meta = json.loads(rad_path.with_name("geodawn_rad.json").read_text())
        ext_path = ROOT / "data/external/geodawn_extensions_u8.tif"
        ext_meta = json.loads(ext_path.with_name("geodawn_extensions.json").read_text())
        confounds.build_all(force=False)
        conf_path = confounds.CONF / "confounds.npz"

        if sha256_file(prep_path) != prep_meta["sha256"]:
            raise SystemExit("Prepared feature stack SHA-256 mismatch")
        if sha256_file(rad_path) != rad_meta["product_sha256"]:
            raise SystemExit("GeoDAWN radiometrics SHA-256 mismatch")
        if sha256_file(ext_path) != ext_meta["product_sha256"]:
            raise SystemExit("GeoDAWN extensions SHA-256 mismatch")

        input_hashes = {
            str(p.relative_to(ROOT)): sha256_file(p)
            for p in (
                template,
                labels_path,
                training_tif,
                prep_path,
                lidar_path,
                rad_path,
                ext_path,
                conf_path,
            )
        }

        fp = footprint.load_footprint()
        fp_ids = np.flatnonzero(fp)
        with rasterio.open(labels_path) as ds:
            catalogue = (ds.read(1) > 0) & fp

        print(f"[1/7] Building 42-channel float32 memmap ({len(fp_ids):,} rows)...", flush=True)
        mm = rshg1.build_rshg1_feature_memmap(
            out_path=MEMMAP_PATH,
            footprint=fp,
            prepared_path=prep_path,
            prepared_names=prep_meta["names"],
            training_tif_path=training_tif,
            lidar_tif_path=lidar_path,
            lidar_meta=lidar_meta,
            rad_tif_path=rad_path,
            rad_meta=rad_meta,
            ext_tif_path=ext_path,
            ext_meta=ext_meta,
        )
        col_coverage = {
            name: float(np.isfinite(mm[:, idx]).mean())
            for idx, name in enumerate(rshg1.FEATURE_NAMES)
        }
        print(
            f"      Memmap ready; RSS={peak_rss_mib():.1f} MiB; "
            f"G_sat coverage={col_coverage['g_sat']:.4f}, R_alt={col_coverage['r_alt']:.4f}, B_step={col_coverage['b_step']:.4f}",
            flush=True,
        )

        context = holdout.SegmentHoldout(fp, catalogue, buffer_px=15)
        print("[2/7] Running two-polarity leakage canaries across all 42 channels...", flush=True)
        canary_42 = run_streaming_canary(context, mm, fp, batch_size=4)
        print(
            f"      Canary passed={canary_42['passed']}, worst={canary_42['worst_feature']} "
            f"(pooled AUC={canary_42['worst_pooled_auc']:.4f}); RSS={peak_rss_mib():.1f} MiB",
            flush=True,
        )
        if not canary_42["passed"]:
            save_json(
                {
                    "verdict": "negative",
                    "stopped_reason": "leakage_canary_failed",
                    "canary": canary_42,
                },
                EXPERIMENT_JSON,
            )
            raise SystemExit("HALT: Single-feature leakage canary exceeded threshold 0.90")

        with np.load(conf_path) as c_npz:
            cdict = confounds.classifier_features(c_npz)
            nuisance_fp = np.column_stack(
                [
                    cdict[k].ravel()[fp_ids].astype(np.float32, copy=False)
                    for k in rshg1.NUISANCE_KEYS
                ]
            )
        del cdict
        gc.collect()

        print(
            "[3/7] Fitting fold-local H24-RSHG1 & diagnostic ablations on SegmentHoldout...",
            flush=True,
        )
        oof_prob_cal = np.zeros(fp.shape, dtype=np.float32)
        oof_prob_raw = np.zeros(fp.shape, dtype=np.float32)
        dots_primary_folds: list[np.ndarray] = []
        dots_cal_pw_folds: list[np.ndarray] = []
        dots_raw_pw_folds: list[np.ndarray] = []

        for fold in context.folds:
            fid = int(fold["id"])
            models_cal, resid, calibrator, models_raw = fit_fold_models(
                mm,
                nuisance_fp,
                fp_ids,
                fold["train"],
                fold["visible"],
                fold_seed_base=SEED + 10 * fid,
                fit_raw_ablation=True,
            )
            val_rows = np.flatnonzero(fold["valid"].ravel()[fp_ids])
            p_val_cal = predict_in_chunks(models_cal, resid, calibrator, mm, nuisance_fp, val_rows)
            p_val_raw = predict_in_chunks(models_raw or [], None, None, mm, nuisance_fp, val_rows)

            fold_cal_map = np.zeros(fp.shape, dtype=np.float32)
            fold_cal_map.ravel()[fp_ids[val_rows]] = p_val_cal
            oof_prob_cal += fold_cal_map

            fold_raw_map = np.zeros(fp.shape, dtype=np.float32)
            fold_raw_map.ravel()[fp_ids[val_rows]] = p_val_raw
            oof_prob_raw += fold_raw_map

            d_prim = rshg1.emit_rshg1_dots(
                fold_cal_map,
                fold["valid"],
                fold["visible"],
                budget_frac=BUDGET_FRAC,
                min_dist=3.0,
                flank_clearance_px=2.0,
                use_kernel_trace=True,
            )
            d_cal_pw = rshg1.emit_rshg1_dots(
                fold_cal_map,
                fold["valid"],
                fold["visible"],
                budget_frac=BUDGET_FRAC,
                min_dist=3.0,
                flank_clearance_px=0.0,
                use_kernel_trace=False,
            )
            d_raw_pw = rshg1.emit_rshg1_dots(
                fold_raw_map,
                fold["valid"],
                fold["visible"],
                budget_frac=BUDGET_FRAC,
                min_dist=3.0,
                flank_clearance_px=0.0,
                use_kernel_trace=False,
            )
            dots_primary_folds.append(d_prim)
            dots_cal_pw_folds.append(d_cal_pw)
            dots_raw_pw_folds.append(d_raw_pw)
            print(
                f"      Fold {fold['name']:18s}: emitted={int(d_prim.sum()):,} px; RSS={peak_rss_mib():.1f} MiB",
                flush=True,
            )
            del (
                models_cal,
                resid,
                calibrator,
                models_raw,
                fold_cal_map,
                fold_raw_map,
                p_val_cal,
                p_val_raw,
            )
            gc.collect()

        oof_canary = context.canary(
            {"rshg1_oof_calibrated_prob": oof_prob_cal}, seed=SEED, max_per_class=15000
        )
        if not oof_canary["passed"]:
            raise SystemExit("HALT: OOF calibrated surface flagged leakage canary")
        del oof_prob_raw
        gc.collect()

        # Reconstruct exact oof_multiphysics_hgb_d3 baseline for paired 1,999-draw bootstrap
        with (
            rasterio.open(lidar_path) as dlid,
            rasterio.open(rad_path) as drad,
            rasterio.open(ext_path) as dext,
        ):
            rv = fp.copy()
            for bname in sahg1.LIDAR_SPECS:
                rv &= dlid.read(lidar_meta["bands"].index(bname) + 1) > 0
            for bname in sahg1.RAD_BANDS:
                rv &= drad.read(rad_meta["channels"].index(bname) + 1) > 0
            for bname in sahg1.EXT_BANDS:
                rv &= dext.read(ext_meta["channels"].index(bname) + 1) > 0
        prep_mm = np.load(prep_path, mmap_mode="r")
        for gname in sahg1.GEOPHYS_BANDS:
            gcol = prep_mm[:, prep_meta["names"].index(gname)]
            gmask = np.zeros(fp.shape, dtype=bool)
            gmask.ravel()[fp_ids] = np.isfinite(gcol)
            rv &= gmask
        exact_sahg1_support = binary_erosion(
            rv,
            structure=np.ones(
                (2 * sahg1.STENCIL_RADIUS_PX + 1, 2 * sahg1.STENCIL_RADIUS_PX + 1), dtype=bool
            ),
            border_value=False,
        )
        del rv
        oof_base_dots = build_recorded_oof_baseline(
            context, prep_path, int(prep_meta["base_count"]), exact_sahg1_support, fp
        )
        del exact_sahg1_support
        gc.collect()

        sum_primary, blk_primary = summarize_with_blocks(context, dots_primary_folds)
        sum_cal_pw, blk_cal_pw = summarize_with_blocks(context, dots_cal_pw_folds)
        sum_raw_pw, blk_raw_pw = summarize_with_blocks(context, dots_raw_pw_folds)
        sum_oof_base, blk_oof_base = summarize_with_blocks(context, oof_base_dots)

        sahg1_recorded = json.loads((ROOT / "evidence/sahg1_run_card_20261025.json").read_text())
        recorded_oof_dti = float(sahg1_recorded["reconstructed_oof_multiphysics_baseline"]["dti"])
        if abs(sum_oof_base["dti"] - recorded_oof_dti) > 1e-6:
            raise SystemExit(
                f"Baseline reproduction drift: got {sum_oof_base['dti']}, expected {recorded_oof_dti}"
            )

        paired_vs_oof = paired_delta_summary(sum_primary, blk_primary, sum_oof_base, blk_oof_base)
        paired_vs_cal_pw = paired_delta_summary(sum_primary, blk_primary, sum_cal_pw, blk_cal_pw)
        paired_vs_raw_pw = paired_delta_summary(sum_primary, blk_primary, sum_raw_pw, blk_raw_pw)

        print(
            f"      HOLDOUT-DTI (gems-segment-pooled-v1): H24-RSHG1 = {sum_primary['dti']:.5f} "
            f"{sum_primary['ci95']['interval']} vs oof_multiphysics_hgb_d3 = {sum_oof_base['dti']:.5f} "
            f"(paired delta = {paired_vs_oof['delta_dti']:+.5f}, CI={paired_vs_oof['ci95']})",
            flush=True,
        )
        print(
            f"      Ablation B (calibrated pointwise) = {sum_cal_pw['dti']:.5f}; "
            f"Ablation A (uncalibrated pointwise) = {sum_raw_pw['dti']:.5f}",
            flush=True,
        )

        print(
            "[4/7] Running leak-free 3.0 km segment-hide-recover-pooled-v1 bridge evaluation...",
            flush=True,
        )
        bridge_3km = evaluate_bridge_3km(mm, nuisance_fp, fp, catalogue)
        print(
            f"      Bridge HOLDOUT-DTI (3.0 km): H24-RSHG1 = {bridge_3km['dti']:.5f} {bridge_3km['ci95']} "
            f"(vs SAHG1 {bridge_3km['recorded_sahg1_bridge_dti']:.5f}, ASPC {bridge_3km['recorded_aspc_dti']:.5f})",
            flush=True,
        )

        print(
            "[5/7] Fitting full-footprint H24-RSHG1 model & running full registry/peer novelty checks...",
            flush=True,
        )
        models_full, resid_full, cal_full, _ = fit_fold_models(
            mm,
            nuisance_fp,
            fp_ids,
            fp,
            catalogue,
            fold_seed_base=SEED + 900,
            fit_raw_ablation=False,
        )
        all_rows = np.arange(len(fp_ids), dtype=np.int64)
        p_full_rows = predict_in_chunks(
            models_full, resid_full, cal_full, mm, nuisance_fp, all_rows
        )
        p_full_cal = np.zeros(fp.shape, dtype=np.float32)
        p_full_cal.ravel()[fp_ids] = p_full_rows
        del models_full, resid_full, cal_full, p_full_rows, all_rows, nuisance_fp
        gc.collect()

        trace_surface_full = rshg1.kernel_trace_score(p_full_cal, fp, catalogue)
        priority_reg = json.loads((ROOT / "registry/priority_rasters.json").read_text())
        extras = extra_20261025_entries(fp)

        pre_nov_methods = novelty.compare_prospective_registry(
            trace_surface_full,
            fp,
            priority_reg["unique_rasters"],
            ROOT,
            sample_size=200_000,
            extra_entries=extras,
        )
        pre_nov_peers = check_peer_blobs(trace_surface_full, None, fp)
        if not pre_nov_methods["method_lane_passed"] or not pre_nov_peers["passed"]:
            save_json(
                {
                    "verdict": "negative",
                    "stopped_reason": "pre_placement_method_novelty_failed",
                    "pre_nov_methods": pre_nov_methods,
                    "pre_nov_peers": pre_nov_peers,
                },
                EXPERIMENT_JSON,
            )
            raise SystemExit(
                "HALT: Pre-placement surface exceeded method-lane rank correlation 0.90"
            )

        final_dots = rshg1.emit_rshg1_dots(
            p_full_cal,
            fp,
            catalogue,
            budget_frac=BUDGET_FRAC,
            min_dist=3.0,
            flank_clearance_px=2.0,
            use_kernel_trace=True,
        )
        final_nov_methods = novelty.compare_prospective_registry(
            trace_surface_full,
            fp,
            priority_reg["unique_rasters"],
            ROOT,
            dots=final_dots,
            sample_size=200_000,
            extra_entries=extras,
        )
        final_nov_peers = check_peer_blobs(trace_surface_full, final_dots, fp)
        print(
            f"      Novelty: competing_methods={final_nov_methods['competing_method_rasters_count']} "
            f"(passed={final_nov_methods['method_lane_passed']}, max_overlap={final_nov_methods['method_lane_max_dot_overlap']:.4f}, "
            f"max_|rho|={final_nov_methods['method_lane_max_abs_rank_correlation']:.4f}); "
            f"peers={final_nov_peers['peer_unique_blobs_checked']} "
            f"(passed={final_nov_peers['passed']}, max_overlap={final_nov_peers['max_dot_overlap_within_3px']:.4f}); "
            f"literal_all_entries_passed={final_nov_methods['literal_all_entries_passed']}",
            flush=True,
        )
        del trace_surface_full, p_full_cal
        gc.collect()

        print(
            "[6/7] Writing competition GeoTIFF pair & running exact-file format validator...",
            flush=True,
        )
        content_id = submission.scored_content_id(final_dots, fp, catalogue)
        zeros_name = submission.make_filename(
            "gems24", "rshg1-regime-hydro-hgb", "20261025", content_id, "zeros"
        )
        nan_name = zeros_name.replace("-zeros.tif", "-nan.tif")
        downloads = ROOT / "docs/downloads"
        zeros_path = submission.write_submission(
            final_dots.astype(np.float32), template, downloads / zeros_name, outside="zero"
        )
        nan_path = submission.write_submission(
            final_dots.astype(np.float32), template, downloads / nan_name, outside="nan"
        )
        zero_raw_checks = submission.check_variants(zeros_path, template)
        nan_raw_checks = submission.check_variants(nan_path, template)
        checks = {
            "zero_outside": {
                "file": zeros_name,
                "submission_authorized": False,
                **zero_raw_checks,
            },
            "nan_outside": {
                "file": nan_name,
                "submission_authorized": False,
                **nan_raw_checks,
            },
        }
        if (
            not zero_raw_checks["format_valid"]
            or not nan_raw_checks["format_valid"]
            or not strict_whole_array_ok(zero_raw_checks)
        ):
            raise SystemExit("Written GeoTIFF failed format or strict [0,1] range check")

        write_preview(final_dots, fp, PREVIEW_PNG)
        dist_cat_dots = distance_transform_edt(~catalogue)[final_dots]
        min_cat_dist_px = float(dist_cat_dots.min())

        print("[7/7] Running exact-file C2ST nuisance audit on written GeoTIFF...", flush=True)
        c2st_report = run_exact_file_c2st(zeros_path, fp, catalogue)
        print(
            f"      C2ST: labels AUC={c2st_report['labels_first']['observed_auc']:.4f}, "
            f"H24-RSHG1 AUC={c2st_report['observed_auc']:.4f} (null p95={c2st_report['null_p95']:.4f}, "
            f"Holm p={c2st_report['holm_p_value']:.3f}, strict_gate_passed={c2st_report['strict_gate_passed']})",
            flush=True,
        )

        canary_ok = bool(canary_42["passed"] and oof_canary["passed"])
        method_nov_ok = bool(final_nov_methods["method_lane_passed"] and final_nov_peers["passed"])
        literal_nov_ok = bool(final_nov_methods["literal_all_entries_passed"])
        beats_oof_ok = bool(
            sum_primary["dti"] > sum_oof_base["dti"] and paired_vs_oof["ci95_strictly_positive"]
        )
        c2st_ok = bool(c2st_report["strict_gate_passed"])
        format_ok = bool(
            zero_raw_checks["format_valid"]
            and nan_raw_checks["format_valid"]
            and strict_whole_array_ok(zero_raw_checks)
        )
        technical_gates_passed = bool(
            canary_ok and method_nov_ok and beats_oof_ok and c2st_ok and format_ok
        )

        # Fail-closed per AGENTS.md & PARALLEL-RUN PROTOCOL Rules 1 & 6:
        # literal_all_entries_passed is False due to retained registry-039 spacing-5 lattice,
        # lane is provisional, and weekly-slot promotion requires a separate selector step.
        verdict = "negative"
        ok_to_submit = False

        note = (
            f"GEMS24 RSHG1 | 42ch NaN-HGB+res+K300 b2 {content_id} | "
            f"DTI {sum_primary['dti']:.4f}; DO NOT SUBMIT"
        )
        if len(note) > 140:
            raise AssertionError(f"Short note length {len(note)} > 140")

        note_file = f"note-{zeros_name[:-4]}.txt"
        checks_file = f"checks-{zeros_name[:-4]}.json"
        (downloads / note_file).write_text(note + "\n")
        save_json(checks, downloads / checks_file)

        con_card = json.loads((ROOT / "evidence/con_run_card_20261025.json").read_text())
        mtr1_card = json.loads((ROOT / "evidence/mtr1_run_card.json").read_text())

        blockers = []
        if not beats_oof_ok:
            blockers.append(
                f"Did not beat oof_multiphysics_hgb_d3 ({sum_oof_base['dti']:.5f}) with positive 95% paired CI"
            )
        if not c2st_ok:
            blockers.append(
                f"Exact-file C2ST nuisance audit flagged (AUC={c2st_report['observed_auc']:.4f}, Holm p={c2st_report['holm_p_value']:.3f})"
            )
        if not method_nov_ok:
            blockers.append("Method-lane novelty threshold exceeded")
        if not literal_nov_ok:
            blockers.append(
                "Retained synthetic spacing-5 calibration lattice (registry-039) covers 99.87% of footprint within 3 px (literal overlap = 1.0)"
            )
        blockers.append(
            "Provisional parallel lane without single assigned method paragraph; live weekly-slot authorization requires a separate selector step (Protocol Rule 6)"
        )

        elapsed = float(time.monotonic() - t0)
        card = {
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "lane_id": "H24-RSHG1",
            "lane_status": "provisional_unassigned_method_paragraph",
            "preregistration": "knowledge/17_preregistered_RSHG1_2026-10-25.md",
            "hypothesis": (
                "Regime-adaptive 42-channel NaN-routed multi-physics OOF HGB ensemble with "
                "NaN-preserving training-only nuisance residualization, regime/nuisance background "
                "log-odds calibration, 300 m kernel-expected trace scoring, and >200 m visible-catalogue halo clearance"
            ),
            "mechanism": (
                "Combines strike-projected 3DEP LiDAR antislope scarps (G_sat, NaN in LiDAR gaps), "
                "Th-immobile K/U hydrothermal alteration (R_alt), potential-field magnetic/gravity tilt "
                "zero-crossings (cos_tilt_mag, cos_tilt_grav, grad_tilt_mag), shallow upward-continuation "
                "magnetic contrast (tmi vs TMI_up150), multi-scale 100 m DEM Hessian ridges, and 4 omitted "
                "local competition bands across 100% of the footprint while removing (road_m, claim_m, block_1..4) "
                "mountain-bedrock background bias strictly on fold.train"
            ),
            "named_non_fault_mimic": (
                "Shallow buried Neogene basaltic feeder dikes or welded-tuff erosional paleobluffs "
                "flanked by K-feldspar-rich arkosic alluvial fan detritus"
            ),
            "holdout": sum_primary,
            "diagnostic_ablations": {
                "rshg1_calibrated_pointwise_b0": sum_cal_pw,
                "rshg1_uncalibrated_pointwise_b0": sum_raw_pw,
            },
            "reconstructed_oof_multiphysics_baseline": sum_oof_base,
            "paired_comparisons": {
                "rshg1_minus_reconstructed_oof_hgb_d3": paired_vs_oof,
                "rshg1_minus_calibrated_pointwise_ablation": paired_vs_cal_pw,
                "rshg1_minus_uncalibrated_pointwise_ablation": paired_vs_raw_pw,
                "rshg1_minus_recorded_sahg1": {
                    "recorded_sahg1_dti": float(sahg1_recorded["holdout"]["dti"]),
                    "delta_dti": float(
                        sum_primary["dti"] - float(sahg1_recorded["holdout"]["dti"])
                    ),
                },
                "rshg1_minus_recorded_con": {
                    "recorded_con_dti": float(con_card["holdout"]["dti"]),
                    "delta_dti": float(sum_primary["dti"] - float(con_card["holdout"]["dti"])),
                },
                "rshg1_minus_recorded_mtr1": {
                    "recorded_mtr1_dti": float(mtr1_card["holdout"]["dti"]),
                    "delta_dti": float(sum_primary["dti"] - float(mtr1_card["holdout"]["dti"])),
                },
            },
            "bridge_protocol_holdout": bridge_3km,
            "leakage_canary": {
                "passed": canary_ok,
                "n_features_checked": canary_42["n_features_checked"],
                "worst_feature": canary_42["worst_feature"],
                "worst_pooled_auc": canary_42["worst_pooled_auc"],
                "oof_calibrated_prob_pooled_auc": oof_canary["features"][
                    "rshg1_oof_calibrated_prob"
                ]["pooled_auc"],
            },
            "correlation_overlap_vs_registry": {
                "method_lane_passed": method_nov_ok,
                "literal_all_entries_passed": literal_nov_ok,
                "competing_method_rasters_checked": final_nov_methods[
                    "competing_method_rasters_count"
                ],
                "calibration_controls_checked": final_nov_methods[
                    "calibration_control_rasters_count"
                ],
                "peer_blobs_checked": final_nov_peers["peer_unique_blobs_checked"],
                "pre_placement_max_abs_rank_correlation": max(
                    float(pre_nov_methods["method_lane_max_abs_rank_correlation"]),
                    float(pre_nov_peers["max_abs_surface_spearman"]),
                ),
                "surface_max_abs_rank_correlation": float(
                    final_nov_methods["method_lane_max_abs_rank_correlation"]
                ),
                "method_lane_max_overlap_within_3px": float(
                    final_nov_methods["method_lane_max_dot_overlap"]
                ),
                "peer_blobs_max_abs_rank_correlation": max(
                    float(final_nov_peers["max_abs_surface_spearman"]),
                    float(final_nov_peers["max_abs_dot_spearman"] or 0.0),
                ),
                "peer_blobs_max_overlap_within_3px": float(
                    final_nov_peers["max_dot_overlap_within_3px"]
                ),
                "literal_all_entries_max_overlap_within_3px": float(
                    final_nov_methods["max_dot_overlap"]
                ),
            },
            "exact_file_nuisance_audit": c2st_report,
            "raster_sha256": sha256_file(zeros_path),
            "nan_outside_artifact": nan_name,
            "nan_outside_sha256": sha256_file(nan_path),
            "positive_pixels": int(final_dots.sum()),
            "min_distance_to_public_catalogue_px": min_cat_dist_px,
            "validator_output": zero_raw_checks,
            "nan_validator_output": nan_raw_checks,
            "submission_name": zeros_name,
            "note": note,
            "note_length": len(note),
            "technical_gate_breakdown": {
                "format_and_strict_0_1_range": format_ok,
                "two_polarity_leakage_canary": canary_ok,
                "method_and_peer_novelty": method_nov_ok,
                "beats_oof_multiphysics_hgb_d3_with_95ci": beats_oof_ok,
                "exact_file_c2st_nuisance_gate": c2st_ok,
            },
            "technical_promotion_gates_passed": technical_gates_passed,
            "selector_candidate_if_calibration_controls_excluded": technical_gates_passed,
            "verdict": verdict,
            "ok_to_download": True,
            "ok_to_submit": ok_to_submit,
            "submission_authorized": False,
            "submission_slot_spent": False,
            "organizer_confirmed_score": None,
            "blocking_reasons": blockers,
            "budget": {
                "experiments_run_this_session": 1,
                "max_experiments": 3,
                "elapsed_seconds": elapsed,
                "max_hours": 2.0,
                "peak_rss_mib": peak_rss_mib(),
            },
        }
        save_json(card, RUN_CARD_JSON)
        save_json(card, DOCS_RUN_CARD_JSON)

        download_meta = {
            "lane_id": "H24-RSHG1",
            "file": zeros_name,
            "sha256": card["raster_sha256"],
            "nan_file": nan_name,
            "nan_sha256": card["nan_outside_sha256"],
            "pixel_count": int(final_dots.sum()),
            "min_distance_to_catalogue_px": min_cat_dist_px,
            "note": note,
            "note_file": note_file,
            "checks_file": checks_file,
            "preview_png": "assets/rshg1-preview.png",
            "verdict": verdict,
            "technical_promotion_gates_passed": technical_gates_passed,
            "ok_to_download": True,
            "ok_to_submit": False,
            "submission_authorized": False,
        }
        save_json(download_meta, DOCS_DOWNLOAD_JSON)

        pre_receipt = preflight.preflight(
            zeros_path,
            template,
            run_card_path=RUN_CARD_JSON.relative_to(ROOT),
            note=note,
            expected_template_sha256=input_hashes["data/bridge/sample_submission.tif"],
        )
        save_json(pre_receipt, zeros_path.with_suffix(".preflight.json"))

        # Strip huge per-row registry arrays from experiment JSON to keep repo git-friendly (<200 KB)
        slim_final_nov = {k: v for k, v in final_nov_methods.items() if k != "rows"}
        slim_pre_nov = {k: v for k, v in pre_nov_methods.items() if k != "rows"}

        full_exp = {
            "generated_utc": card["generated_utc"],
            "preregistration": card["preregistration"],
            "experiment_number": 1,
            "input_hashes": input_hashes,
            "feature_names": list(rshg1.FEATURE_NAMES),
            "feature_finite_coverage": col_coverage,
            "canary_42": canary_42,
            "oof_canary": oof_canary,
            "holdout_primary": sum_primary,
            "ablation_calibrated_pointwise": sum_cal_pw,
            "ablation_uncalibrated_pointwise": sum_raw_pw,
            "reconstructed_oof_baseline": sum_oof_base,
            "paired_comparisons": card["paired_comparisons"],
            "bridge_3km": bridge_3km,
            "pre_placement_novelty_methods": slim_pre_nov,
            "pre_placement_novelty_peers": pre_nov_peers,
            "final_novelty_methods": slim_final_nov,
            "final_novelty_peers": final_nov_peers,
            "exact_file_c2st": c2st_report,
            "run_card": card,
            "preflight": pre_receipt,
            "ok_to_submit": False,
        }
        save_json(full_exp, EXPERIMENT_JSON)
        print(
            json.dumps(
                {
                    "status": "completed",
                    "submission_name": zeros_name,
                    "sha256": card["raster_sha256"],
                    "holdout_dti": sum_primary["dti"],
                    "holdout_ci95": sum_primary["ci95"]["interval"],
                    "oof_baseline_dti": sum_oof_base["dti"],
                    "paired_delta_vs_oof": paired_vs_oof["delta_dti"],
                    "paired_ci95_vs_oof": paired_vs_oof["ci95"],
                    "bridge_3km_dti": bridge_3km["dti"],
                    "c2st_auc": c2st_report["observed_auc"],
                    "c2st_holm_p": c2st_report["holm_p_value"],
                    "c2st_strict_gate_passed": c2st_ok,
                    "method_lane_novelty_passed": method_nov_ok,
                    "technical_promotion_gates_passed": technical_gates_passed,
                    "verdict": verdict,
                    "ok_to_submit": ok_to_submit,
                    "elapsed_seconds": round(elapsed, 2),
                    "peak_rss_mib": round(peak_rss_mib(), 1),
                },
                indent=2,
            ),
            flush=True,
        )


if __name__ == "__main__":
    main()
