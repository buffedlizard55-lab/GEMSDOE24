#!/usr/bin/env python3
"""Execute or verify the preregistered H24-TRSG1 Two-Regime Stitched-OOF lane.

Spec locked before execution in ``knowledge/19_preregistered_TRSG1_2026-10-26.md``:
- Streams 44 physical, seismic-fabric, Faulds-Hinz relay-ramp hyperbolic saddle,
  piedmont/drainage breakline, Quaternary volcanic-vent demagnetization, and
  scale-localized INGENIOUS upflow channels into ``data/prepared/trsg1_features.npy``
  (<1.8 GiB RSS on 3.8 GiB RAM, 0 swap; zero catalogue or global radial EDT features).
- Runs two-polarity single-feature leakage canaries across all 44 channels before
  model fitting.
- Evaluates the 3 preregistered arms on ``SegmentHoldout`` (``gems-segment-pooled-v1``,
  1.5 km collar, 60,988 withheld positives, 1,999 10 km block-bootstrap draws) with
  exact paired block-bootstrap CIs against ``oof_multiphysics_hgb_d3`` (0.13000) and
  across arms, plus leak-free 3.0 km ``segment-hide-recover-pooled-v1`` bridge scores:
    * Arm 1: ``TRSG1-Raw44`` (unresidualized 44ch + close-flank/far negatives + global Poisson)
    * Arm 2: ``TRSG1-SelRes-TerrainCal`` (selective survey residualizer + terrain-relief-stratified LiDAR-gap calibrator + global Poisson)
    * Arm 3: ``TRSG1-TwoRegime-StitchedOOF`` (Two-Regime Concealed-Basin 26% + Range-Front 74% Poisson allocation + Dual-Partition 0°+45° Stitched-OOF full-footprint deployment)
- Exports ``-zeros.tif``, ``-nan.tif``, and ``-zeros.zip`` via ``submission_writer.py`` /
  ``gems.submission``, checks novelty against all 46 priority rasters + all 9 local
  2026-10-25 GEMSDOE24 rasters + all 83 peer blobs, runs exact-file C2ST nuisance
  audit (``gems.c2s2``), and writes schema-v2 fail-closed preflight receipts.
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import os
import resource
import subprocess
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
    trsg1,
)
from gems.validator import sha256_file  # noqa: E402

SEED = 20261026
BASELINE_SEED = 20261025
BUDGET_FRAC = 0.0073
BASIN_SHARE = 0.26
BASIN_DEPTH_MIN_M = 300.0
BASIN_SLOPE_MAX_DEG = 6.0

HGB_PARAMS = dict(
    max_iter=150,
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
    random_state=BASELINE_SEED,
)

MEMMAP_PATH = ROOT / "data/prepared/trsg1_features.npy"
EXPERIMENT_JSON = ROOT / "evidence/trsg1_experiment_20261026.json"
RUN_CARD_JSON = ROOT / "evidence/trsg1_run_card_20261026.json"
DOCS_RUN_CARD_JSON = ROOT / "docs/data/trsg1_run_card.json"
DOCS_DOWNLOAD_JSON = ROOT / "docs/data/trsg1_download.json"
PREVIEW_PNG = ROOT / "docs/assets/trsg1-preview.png"


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
    """Verify frozen TRSG1 receipts, exact GeoTIFF pair, ZIP, preflight, and <=140-char note."""
    for p in (EXPERIMENT_JSON, RUN_CARD_JSON, DOCS_RUN_CARD_JSON, DOCS_DOWNLOAD_JSON, PREVIEW_PNG):
        if not p.exists():
            raise SystemExit(f"Missing recorded TRSG1 artifact: {p}")
    exp = json.loads(EXPERIMENT_JSON.read_text())
    card = json.loads(RUN_CARD_JSON.read_text())
    docs_card = json.loads(DOCS_RUN_CARD_JSON.read_text())
    dl = json.loads(DOCS_DOWNLOAD_JSON.read_text())
    if card != docs_card:
        raise SystemExit("Evidence and docs/data TRSG1 run cards disagree")
    if (
        card["verdict"] != "negative"
        or card["ok_to_submit"] is not False
        or dl["ok_to_submit"] is not False
    ):
        raise SystemExit("Recorded TRSG1 packet must remain fail-closed until separate selector")

    template = ROOT / "data/bridge/sample_submission.tif"
    zeros_path = ROOT / "docs/downloads" / card["submission_name"]
    nan_path = ROOT / "docs/downloads" / card["nan_outside_artifact"]
    zip_path = zeros_path.with_suffix(".zip")
    checks_path = ROOT / "docs/downloads" / dl["checks_file"]
    note_path = ROOT / "docs/downloads" / dl["note_file"]
    preflight_path = zeros_path.with_suffix(".preflight.json")

    if not zip_path.is_file():
        raise SystemExit(f"Missing TRSG1 single-file ZIP companion: {zip_path}")
    if (
        sha256_file(zip_path) != card["zip_sha256"]
        or dl["zip_sha256"] != card["zip_sha256"]
        or dl["zip_file"] != card["zip_artifact"]
    ):
        raise SystemExit("TRSG1 single-file ZIP SHA-256 mismatch")
    with trsg1.zipfile.ZipFile(zip_path) as zf:
        if zf.namelist() != [card["submission_name"]]:
            raise SystemExit("TRSG1 ZIP inner file list invalid")
        if hashlib.sha256(zf.read(card["submission_name"])).hexdigest() != card["raster_sha256"]:
            raise SystemExit("TRSG1 ZIP inner GeoTIFF SHA-256 mismatch")
    if not (ROOT / exp["preregistration"]).is_file():
        raise SystemExit(f"Missing TRSG1 preregistration file: {exp['preregistration']}")
    if sha256_file(zeros_path) != card["raster_sha256"] or dl["sha256"] != card["raster_sha256"]:
        raise SystemExit("TRSG1 zero-outside GeoTIFF SHA-256 mismatch")
    if (
        sha256_file(nan_path) != card["nan_outside_sha256"]
        or dl["nan_sha256"] != card["nan_outside_sha256"]
    ):
        raise SystemExit("TRSG1 NaN-outside GeoTIFF SHA-256 mismatch")

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
        raise SystemExit("TRSG1 exact-file format/range validator check failed")

    note_text = note_path.read_text().strip()
    if len(note_text) > 140 or note_text != card["note"] or note_text != dl["note"]:
        raise SystemExit("TRSG1 note missing, mismatched, or >140 chars")

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
        raise SystemExit("TRSG1 preflight receipt missing, stale, or not fail-closed")

    return {
        "verified": True,
        "experiment_rerun": False,
        "submission_name": card["submission_name"],
        "raster_sha256": card["raster_sha256"],
        "holdout_dti": card["holdout"]["dti"],
        "oof_baseline_dti": card["reconstructed_oof_multiphysics_baseline"]["dti"],
        "c2st_auc": card["exact_file_nuisance_audit"]["observed_auc"],
        "method_lane_max_overlap": card["correlation_overlap_vs_registry"][
            "method_lane_max_overlap_within_3px"
        ],
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
    rgb[fp_small] = (223, 233, 229)
    rgb[d_small] = (13, 92, 99)
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
    """Run SegmentHoldout.canary across all 44 TRSG1 channels in bounded memory batches."""
    fp_ids = np.flatnonzero(fp)
    merged: dict[str, Any] = {}
    last_meta: dict[str, Any] = {}
    for start in range(0, len(trsg1.FEATURE_NAMES), batch_size):
        batch: dict[str, np.ndarray] = {}
        for j in range(start, min(start + batch_size, len(trsg1.FEATURE_NAMES))):
            grid = np.full(fp.shape, np.nan, dtype=np.float32)
            grid.ravel()[fp_ids] = mm[:, j]
            batch[trsg1.FEATURE_NAMES[j]] = grid
        rep = context.canary(batch, seed=SEED, max_per_class=15000)
        merged.update(rep["features"])
        last_meta = rep
        del batch
        gc.collect()
    passed = not any(v["leakage_suspected"] for v in merged.values())
    worst_name = max(
        merged,
        key=lambda k: max(merged[k]["pooled_auc"], 1.0 - merged[k]["pooled_auc"]),
    )
    worst_auc = merged[worst_name]["pooled_auc"]
    return {
        "diagnostic": last_meta["diagnostic"],
        "evaluator_version": last_meta["evaluator_version"],
        "threshold": last_meta["threshold"],
        "two_polarities_checked": True,
        "passed": passed,
        "n_features_checked": len(merged),
        "worst_feature": worst_name,
        "worst_pooled_auc": worst_auc,
        "worst_polarity_extremity": max(worst_auc, 1.0 - worst_auc),
        "features": merged,
        "interpretation": last_meta["interpretation"],
    }


def predict_in_chunks(
    models: list[HistGradientBoostingClassifier],
    resid: rshg1.NanPreservingResidualizer | None,
    calibrator: trsg1.TerrainReliefRegimeCalibrator | None,
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
            has_lidar = np.isfinite(x_raw[:, trsg1.IDX_LIDAR1])
            abs_relief = np.abs(x_raw[:, trsg1.IDX_LOCAL_RELIEF])
            p_mean = calibrator.transform(p_mean, has_lidar, abs_relief, c_sub)
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
    fit_raw_arm: bool = False,
) -> tuple[
    list[HistGradientBoostingClassifier],
    rshg1.NanPreservingResidualizer,
    trsg1.TerrainReliefRegimeCalibrator,
    list[HistGradientBoostingClassifier] | None,
]:
    """Fit selective residualizer, close-flank+far HGB ensemble, and relief-stratified calibrator."""
    dist_vis = distance_transform_edt(~visible_mask)
    pos_mask = train_mask & visible_mask
    neg_far_mask = train_mask & (~visible_mask) & (dist_vis >= 9.0)
    neg_flank_mask = train_mask & (~visible_mask) & (dist_vis >= 4.0) & (dist_vis < 9.0)
    bg_mask = train_mask & (~visible_mask) & (dist_vis >= 4.0)
    del dist_vis

    pos_rows = np.flatnonzero(pos_mask.ravel()[fp_ids])
    neg_far_rows = np.flatnonzero(neg_far_mask.ravel()[fp_ids])
    neg_flank_rows = np.flatnonzero(neg_flank_mask.ravel()[fp_ids])
    bg_rows = np.flatnonzero(bg_mask.ravel()[fp_ids])
    del pos_mask, neg_far_mask, neg_flank_mask, bg_mask

    if len(pos_rows) < 200 or len(neg_far_rows) < 600:
        raise RuntimeError("Insufficient training positives/negatives in fold")

    rng_bg = np.random.default_rng(fold_seed_base + 77)
    bg_sel = rng_bg.choice(bg_rows, min(36_000, len(bg_rows)), replace=False)
    bg_sel.sort()
    x_bg_raw = np.asarray(mm[bg_sel], dtype=np.float32)
    c_bg = nuisance_fp[bg_sel]
    resid = rshg1.NanPreservingResidualizer(
        regional_indices=trsg1.SELECTIVE_RESIDUAL_INDICES, alpha=100.0
    ).fit(c_bg, x_bg_raw)

    models_cal: list[HistGradientBoostingClassifier] = []
    models_raw: list[HistGradientBoostingClassifier] | None = [] if fit_raw_arm else None

    for s_idx in range(2):
        seed_s = fold_seed_base + s_idx
        rng_s = np.random.default_rng(seed_s)
        p_sel = rng_s.choice(pos_rows, min(30_000, len(pos_rows)), replace=False)
        nf_sel = rng_s.choice(neg_far_rows, min(72_000, len(neg_far_rows)), replace=False)
        nk_sel = (
            rng_s.choice(neg_flank_rows, min(18_000, len(neg_flank_rows)), replace=False)
            if len(neg_flank_rows) > 0
            else np.empty(0, dtype=np.int64)
        )
        n_sel = np.r_[nf_sel, nk_sel]
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
    has_lidar_bg = np.isfinite(x_bg_raw[:, trsg1.IDX_LIDAR1])
    abs_relief_bg = np.abs(x_bg_raw[:, trsg1.IDX_LOCAL_RELIEF])
    calibrator = trsg1.TerrainReliefRegimeCalibrator(alpha=100.0).fit(
        p_bg, has_lidar_bg, abs_relief_bg, c_bg
    )
    del x_bg_raw, x_bg_res, c_bg, p_bg, pos_rows, neg_far_rows, neg_flank_rows, bg_rows
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
        rng = np.random.default_rng(BASELINE_SEED + fid)
        dist_vis = distance_transform_edt(~fold["visible"])
        pos = np.flatnonzero((fold["train"] & fold["visible"]).ravel()[fp_ids])
        neg = np.flatnonzero((fold["train"] & ~fold["visible"] & (dist_vis >= 9)).ravel()[fp_ids])
        del dist_vis
        p_sel = rng.choice(pos, min(20_000, len(pos)), replace=False)
        n_sel = rng.choice(neg, min(60_000, len(neg)), replace=False)
        tr = np.r_[p_sel, n_sel]
        y = np.r_[np.ones(len(p_sel), dtype=np.int8), np.zeros(len(n_sel), dtype=np.int8)]
        x_tr = np.asarray(stack[tr, :base_count], dtype=np.float32)
        params = {**BASELINE_HGB_PARAMS, "random_state": BASELINE_SEED + fid}
        model = HistGradientBoostingClassifier(**params).fit(x_tr, y)
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
        del x_tr, score, model
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
    ci = holdout.pooled_bootstrap(blocks_a, paired=blocks_b, resamples=1999, seed=BASELINE_SEED)
    return {
        "delta_dti": float(summary_a["dti"] - summary_b["dti"]),
        "ci95": ci,
        "ci95_strictly_positive": bool(ci[0] > 0.0),
    }


def compute_subsurface_conduit_z(
    mm: np.memmap, fp: np.ndarray, fp_ids: np.ndarray, ref_mask: np.ndarray
) -> np.ndarray:
    """Compute standardized subsurface conduit z-score strictly using statistics on ref_mask."""
    ref_rows = np.flatnonzero(ref_mask.ravel()[fp_ids])
    acc = np.zeros(len(fp_ids), dtype=np.float32)
    for col_idx in trsg1.SUBSURFACE_CONDUIT_INDICES:
        col_all = np.asarray(mm[:, int(col_idx)], dtype=np.float32)
        ref_vals = col_all[ref_rows]
        ref_fin = ref_vals[np.isfinite(ref_vals)]
        if len(ref_fin) >= 32:
            med = float(np.median(ref_fin))
            q25, q75 = np.quantile(ref_fin, [0.25, 0.75])
            iqr = max(float(q75 - q25), float(np.std(ref_fin)) * 0.5, 1e-6)
        else:
            med, iqr = 0.0, 1.0
        z_col = np.where(np.isfinite(col_all), np.clip((col_all - med) / iqr, -6.0, 6.0), 0.0)
        acc += z_col.astype(np.float32)
    acc /= float(len(trsg1.SUBSURFACE_CONDUIT_INDICES))
    grid = np.zeros(fp.shape, dtype=np.float32)
    grid.ravel()[fp_ids] = acc
    return grid


def evaluate_bridge_3km(
    mm: np.memmap,
    nuisance_fp: np.ndarray,
    fp: np.ndarray,
    catalogue: np.ndarray,
    depth_2d: np.ndarray,
    slope_2d: np.ndarray,
) -> dict[str, Any]:
    """Run leak-free 3.0 km buffer_px=30 OOF pass on segment-hide-recover-pooled-v1."""
    fp_ids = np.flatnonzero(fp)
    tile_rows_arm3 = []
    tile_rows_arm2 = []
    fold_details = []
    fold_details_arm2 = []
    for fold in holdout.segment_folds(fp, catalogue, buffer_px=30):
        fid = int(fold["fold"])
        models_cal, resid, calibrator, _ = fit_fold_models(
            mm,
            nuisance_fp,
            fp_ids,
            fold["training"],
            fold["visible"],
            fold_seed_base=SEED + 200 + 10 * fid,
            fit_raw_arm=False,
        )
        test_rows = np.flatnonzero(fold["test"].ravel()[fp_ids])
        p_test = predict_in_chunks(models_cal, resid, calibrator, mm, nuisance_fp, test_rows)
        prob_map = np.zeros(fp.shape, dtype=np.float32)
        prob_map.ravel()[fp_ids[test_rows]] = p_test
        sub_z = compute_subsurface_conduit_z(mm, fp, fp_ids, fold["training"] & ~fold["visible"])
        dots_arm3 = trsg1.emit_two_regime_poisson(
            prob_map,
            fold["test"],
            fold["visible"],
            depth_2d,
            slope_2d,
            sub_z,
            budget_frac=BUDGET_FRAC,
            basin_budget_share=BASIN_SHARE,
            basin_depth_min_m=BASIN_DEPTH_MIN_M,
            basin_slope_max_deg=BASIN_SLOPE_MAX_DEG,
            min_dist=3.0,
            clearance_px=2.0,
        )
        dots_arm2 = trsg1.emit_global_poisson(
            prob_map, fold["test"], fold["visible"], budget_frac=BUDGET_FRAC
        )
        truth_test = fold["hidden"] & fold["test"]
        tiles3, ref3 = holdout.spatial_components(
            dots_arm3, truth_test, fold["test"], fold["visible"], tile_px=200
        )
        tiles2, ref2 = holdout.spatial_components(
            dots_arm2, truth_test, fold["test"], fold["visible"], tile_px=200
        )
        tile_rows_arm3.append(tiles3)
        tile_rows_arm2.append(tiles2)
        fold_details.append({"fold": fold["name"], **ref3})
        fold_details_arm2.append({"fold": fold["name"], **ref2})
        del models_cal, resid, calibrator, p_test, prob_map, sub_z, dots_arm3, dots_arm2
        gc.collect()

    summed_t3 = np.sum(tile_rows_arm3, axis=0)
    yy, xx = np.nonzero(fp)
    nx = (fp.shape[1] + 199) // 200
    active_tiles = np.unique((yy // 200) * nx + xx // 200)
    pooled3 = holdout.pooled_components(fold_details)
    pooled2 = holdout.pooled_components(fold_details_arm2)
    ci3 = holdout.pooled_bootstrap(summed_t3[active_tiles], resamples=1000, seed=BASELINE_SEED)
    sahg1_card = json.loads((ROOT / "evidence/sahg1_run_card_20261025.json").read_text())
    rshg1_card = json.loads((ROOT / "evidence/rshg1_run_card_20261025.json").read_text())
    return {
        "label": "HOLDOUT-DTI",
        "evaluator_version": holdout.SEGMENT_EVALUATOR_VERSION,
        "buffer_m": 3000,
        "dti": pooled3["dti"],
        "ci95": ci3,
        "n_withheld_positives": int(pooled3["n_truth"]),
        "n_emitted": int(pooled3["n_emitted"]),
        "arm2_global_dti": pooled2["dti"],
        "recorded_rshg1_bridge_dti": float(rshg1_card["bridge_protocol_holdout"]["dti"]),
        "recorded_sahg1_bridge_dti": float(sahg1_card["bridge_protocol_holdout"]["dti"]),
        "recorded_aspc_dti": float(sahg1_card["bridge_protocol_holdout"]["recorded_aspc_dti"]),
        "folds": fold_details,
    }


def extra_all_local_20261025_entries(fp: np.ndarray) -> list[dict[str, Any]]:
    """Collect ALL 9 local 2026-10-25 GEMSDOE24 method rasters for full novelty auditing."""
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
        (
            "local-20261025-unique03",
            "docs/downloads/24gems-doer-fault-guided-k-20261025T220208Z-dedb860f7e83-zeros.tif",
        ),
        (
            "local-20261025-oj1",
            "docs/downloads/gems24-oj1-3eef450351de-RESEARCH-NOT-SUBMISSION-zeros.tif",
        ),
        (
            "local-20261025-fuse-hcw",
            "docs/downloads/gems24-fuse-fuse-hcw-hgb-20261025-3fd41218a10a-zeros.tif",
        ),
        (
            "local-20261025-rshg1",
            "docs/downloads/gems24-rshg1-regime-hydro-hgb-20261025-98f69d77e868-zeros.tif",
        ),
        (
            "local-20261025-gvc1",
            "docs/downloads/gems24-gvc1-negative-geothermal-lineament-submod-20261025-abe8e51c719d-zeros.tif",
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
    max_overlap_blob = None
    for bsha, row in blobs.items():
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
            if ov is not None and float(ov) > max_overlap:
                max_overlap = float(ov)
                max_overlap_blob = f"{row['repo']}:{row['path']} ({bsha[:10]})"
    passed = max_surf_rho <= 0.90 and (
        dots is None or (max_dot_rho <= 0.90 and max_overlap <= 0.70)
    )
    return {
        "peer_unique_blobs_checked": len(blobs),
        "max_abs_surface_spearman": max_surf_rho,
        "max_abs_dot_spearman": max_dot_rho if dots is not None else None,
        "max_dot_overlap_within_3px": max_overlap if dots is not None else None,
        "max_overlap_peer": max_overlap_blob,
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
        "trsg1_candidate",
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
        "trsg1_candidate_shift",
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
        x_f, y_f, f_f, info = c2s2.build_matrix(
            {fname: feats[fname]}, near, far, fold_grid, fp, 12_000, 20261002
        )
        auc_f, _ = c2s2.spatial_cv_auc(
            c2s2.make_model(seed=20261002),
            x_f,
            y_f,
            f_f,
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
    strict_auc_under_055 = bool(res_cand["observed_auc"] < 0.55 and not flagged)
    return {
        "protocol_seed": 20261002,
        "features": sorted(feats),
        "samples_per_class": 12_000,
        "grouped_permutations": 199,
        "shift_diagnostics": 99,
        "labels_first": {
            "observed_auc": float(res_labels["observed_auc"]),
            "null_p95": float(res_labels["null_auc_p95"]),
            "p_value": float(res_labels["p_value"]),
            "holm_p_value": float(holm_l),
        },
        "observed_auc": float(res_cand["observed_auc"]),
        "fold_aucs": res_cand["fold_aucs"],
        "null_mean": float(res_cand["null_auc_mean"]),
        "null_p95": float(res_cand["null_auc_p95"]),
        "margin_vs_p95": float(res_cand["margin_vs_p95"]),
        "p_value": float(res_cand["p_value"]),
        "holm_p_value": float(holm_c),
        "shift_diagnostic_null_p95": float(shift_cand["null_auc_p95"]),
        "shift_diagnostic_p_value": float(shift_cand["p_value"]),
        "single_feature_aucs": singles,
        "flagged_by_audit_rule": flagged,
        "strict_gate_passed": strict_auc_under_055,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--verify-recorded",
        action="store_true",
        help="Verify frozen TRSG1 artifacts, SHA-256 hashes, ZIP, preflight, and <=140-char note.",
    )
    ap.add_argument(
        "--run",
        action="store_true",
        help="Execute the single locked 3-arm preregistered H24-TRSG1 experiment.",
    )
    args = ap.parse_args()

    if args.verify_recorded:
        print(json.dumps(verify_recorded(), indent=2))
        return
    if not args.run:
        ap.error("Specify --verify-recorded or --run")
    if EXPERIMENT_JSON.exists():
        raise SystemExit(
            f"{EXPERIMENT_JSON} already exists; refusing implicit rerun of locked preregistered experiment. "
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
        rad_path = ROOT / "data/external/geodawn_rad_u8.tif"
        rad_meta = json.loads((ROOT / "data/external/geodawn_rad.json").read_text())
        ext_path = ROOT / "data/external/geodawn_extensions_u8.tif"
        ext_meta = json.loads((ROOT / "data/external/geodawn_extensions.json").read_text())
        confounds.build_all(force=False)
        conf_path = confounds.CONF / "confounds.npz"

        for req in (
            template,
            labels_path,
            training_tif,
            prep_path,
            lidar_path,
            rad_path,
            ext_path,
            conf_path,
        ):
            if not req.exists():
                raise SystemExit(f"Missing required staged input: {req}")

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

        if MEMMAP_PATH.exists():
            mm_check = np.load(MEMMAP_PATH, mmap_mode="r")
            if (
                mm_check.shape == (len(fp_ids), len(trsg1.FEATURE_NAMES))
                and mm_check.dtype == np.float32
            ):
                print(
                    f"[1/8] Reusing verified 44-channel TRSG1 memmap ({len(fp_ids):,} rows)...",
                    flush=True,
                )
                mm = mm_check
            else:
                del mm_check
                mm = trsg1.build_trsg1_feature_memmap(
                    out_path=MEMMAP_PATH,
                    root=ROOT,
                    footprint=fp,
                    prepared_path=prep_path,
                    prepared_names=prep_meta["names"],
                    training_tif_path=training_tif,
                    rad_tif_path=rad_path,
                    rad_meta=rad_meta,
                    ext_tif_path=ext_path,
                    ext_meta=ext_meta,
                )
        else:
            print(
                f"[1/8] Streaming 44-channel TRSG1 float32 memmap ({len(fp_ids):,} rows)...",
                flush=True,
            )
            mm = trsg1.build_trsg1_feature_memmap(
                out_path=MEMMAP_PATH,
                root=ROOT,
                footprint=fp,
                prepared_path=prep_path,
                prepared_names=prep_meta["names"],
                training_tif_path=training_tif,
                rad_tif_path=rad_path,
                rad_meta=rad_meta,
                ext_tif_path=ext_path,
                ext_meta=ext_meta,
            )
            del mm
            gc.collect()
            mm = np.load(MEMMAP_PATH, mmap_mode="r")
        col_coverage = {
            name: float(np.isfinite(mm[:, idx]).mean())
            for idx, name in enumerate(trsg1.FEATURE_NAMES)
        }
        print(
            f"      Memmap ready; RSS={peak_rss_mib():.1f} MiB; "
            f"eq_fabric_aniso={col_coverage['eq_fabric_aniso']:.4f}, "
            f"relay_saddle_dem={col_coverage['relay_saddle_dem']:.4f}, "
            f"lidar_1={col_coverage['lidar_1']:.4f}",
            flush=True,
        )

        context = holdout.SegmentHoldout(fp, catalogue, buffer_px=15)
        print("[2/8] Running two-polarity leakage canaries across all 44 channels...", flush=True)
        canary_44 = run_streaming_canary(context, mm, fp, batch_size=4)
        print(
            f"      Canary passed={canary_44['passed']}, worst={canary_44['worst_feature']} "
            f"(pooled AUC={canary_44['worst_pooled_auc']:.4f}); RSS={peak_rss_mib():.1f} MiB",
            flush=True,
        )
        if not canary_44["passed"]:
            save_json(
                {
                    "verdict": "negative",
                    "stopped_reason": "leakage_canary_failed",
                    "canary": canary_44,
                },
                EXPERIMENT_JSON,
            )
            raise SystemExit("HALT: Single-feature leakage canary exceeded threshold 0.90")

        with np.load(conf_path) as c_npz:
            cdict = confounds.classifier_features(c_npz)
            nuisance_fp = np.column_stack(
                [
                    cdict[k].ravel()[fp_ids].astype(np.float32, copy=False)
                    for k in trsg1.NUISANCE_KEYS
                ]
            )
        del cdict
        gc.collect()

        depth_2d = np.full(fp.shape, np.nan, dtype=np.float32)
        depth_2d.ravel()[fp_ids] = mm[:, trsg1.IDX_DEPTH_BASE]
        slope_2d = np.full(fp.shape, np.nan, dtype=np.float32)
        slope_2d.ravel()[fp_ids] = mm[:, trsg1.IDX_SLOPE]
        has_lidar_2d = np.zeros(fp.shape, dtype=bool)
        has_lidar_2d.ravel()[fp_ids] = np.isfinite(mm[:, trsg1.IDX_LIDAR1])

        print(
            "[3/8] Evaluating the 3 preregistered arms on SegmentHoldout (gems-segment-pooled-v1)...",
            flush=True,
        )
        oof_prob_cal = np.zeros(fp.shape, dtype=np.float32)
        oof_prob_raw = np.zeros(fp.shape, dtype=np.float32)
        dots_arm1_folds: list[np.ndarray] = []
        dots_arm2_folds: list[np.ndarray] = []
        dots_arm3_folds: list[np.ndarray] = []

        for fold in context.folds:
            fid = int(fold["id"])
            models_cal, resid, calibrator, models_raw = fit_fold_models(
                mm,
                nuisance_fp,
                fp_ids,
                fold["train"],
                fold["visible"],
                fold_seed_base=SEED + 10 * fid,
                fit_raw_arm=True,
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

            sub_z_fold = compute_subsurface_conduit_z(
                mm, fp, fp_ids, fold["train"] & ~fold["visible"]
            )

            d_arm1 = trsg1.emit_global_poisson(
                fold_raw_map, fold["valid"], fold["visible"], budget_frac=BUDGET_FRAC
            )
            d_arm2 = trsg1.emit_global_poisson(
                fold_cal_map, fold["valid"], fold["visible"], budget_frac=BUDGET_FRAC
            )
            d_arm3 = trsg1.emit_two_regime_poisson(
                fold_cal_map,
                fold["valid"],
                fold["visible"],
                depth_2d,
                slope_2d,
                sub_z_fold,
                budget_frac=BUDGET_FRAC,
                basin_budget_share=BASIN_SHARE,
                basin_depth_min_m=BASIN_DEPTH_MIN_M,
                basin_slope_max_deg=BASIN_SLOPE_MAX_DEG,
                min_dist=3.0,
                clearance_px=2.0,
            )
            dots_arm1_folds.append(d_arm1)
            dots_arm2_folds.append(d_arm2)
            dots_arm3_folds.append(d_arm3)

            del (
                models_cal,
                resid,
                calibrator,
                models_raw,
                p_val_cal,
                p_val_raw,
                fold_cal_map,
                fold_raw_map,
                sub_z_fold,
            )
            gc.collect()

        oof_canary = context.canary({"trsg1_oof_calibrated_prob": oof_prob_cal}, seed=SEED)
        if not oof_canary["passed"]:
            raise SystemExit("HALT: OOF calibrated probability canary failed")

        # Exact SAHG1 eroded support for identical baseline reproduction (0.13000)
        with rasterio.open(lidar_path) as dsl:
            rv = fp.copy()
            for bi in range(1, dsl.count + 1):
                a = dsl.read(bi)
                rv &= np.isfinite(a) & (a > 0)
        with rasterio.open(rad_path) as dsr:
            for bi in range(1, dsr.count + 1):
                a = dsr.read(bi)
                rv &= np.isfinite(a) & (a > 0)
        with rasterio.open(ext_path) as dse:
            for bi in range(1, dse.count + 1):
                a = dse.read(bi)
                rv &= np.isfinite(a) & (a > 0)
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

        sum_arm1, blk_arm1 = summarize_with_blocks(context, dots_arm1_folds)
        sum_arm2, blk_arm2 = summarize_with_blocks(context, dots_arm2_folds)
        sum_arm3, blk_arm3 = summarize_with_blocks(context, dots_arm3_folds)
        sum_oof_base, blk_oof_base = summarize_with_blocks(context, oof_base_dots)

        sahg1_recorded = json.loads((ROOT / "evidence/sahg1_run_card_20261025.json").read_text())
        rshg1_recorded = json.loads((ROOT / "evidence/rshg1_run_card_20261025.json").read_text())
        hcw_recorded = json.loads((ROOT / "evidence/hcw_run_card_20261025.json").read_text())
        gvc1_recorded = json.loads((ROOT / "evidence/gvc1_run_card_20261025.json").read_text())
        recorded_oof_dti = float(sahg1_recorded["reconstructed_oof_multiphysics_baseline"]["dti"])
        if abs(sum_oof_base["dti"] - recorded_oof_dti) > 1e-6:
            raise SystemExit(
                f"Baseline reproduction drift: got {sum_oof_base['dti']}, expected {recorded_oof_dti}"
            )

        paired_arm3_vs_oof = paired_delta_summary(sum_arm3, blk_arm3, sum_oof_base, blk_oof_base)
        paired_arm2_vs_oof = paired_delta_summary(sum_arm2, blk_arm2, sum_oof_base, blk_oof_base)
        paired_arm1_vs_oof = paired_delta_summary(sum_arm1, blk_arm1, sum_oof_base, blk_oof_base)
        paired_arm2_vs_arm1 = paired_delta_summary(sum_arm2, blk_arm2, sum_arm1, blk_arm1)
        paired_arm3_vs_arm2 = paired_delta_summary(sum_arm3, blk_arm3, sum_arm2, blk_arm2)

        print(
            f"      Arm 1 (TRSG1-Raw44):              DTI = {sum_arm1['dti']:.5f} {sum_arm1['ci95']['interval']}\n"
            f"      Arm 2 (TRSG1-SelRes-TerrainCal):  DTI = {sum_arm2['dti']:.5f} {sum_arm2['ci95']['interval']}\n"
            f"      Arm 3 (TRSG1-TwoRegime-Primary):  DTI = {sum_arm3['dti']:.5f} {sum_arm3['ci95']['interval']}\n"
            f"      vs oof_multiphysics_hgb_d3 ({sum_oof_base['dti']:.5f}): "
            f"Arm3 delta={paired_arm3_vs_oof['delta_dti']:+.5f} CI={paired_arm3_vs_oof['ci95']}; "
            f"Arm2 delta={paired_arm2_vs_oof['delta_dti']:+.5f} CI={paired_arm2_vs_oof['ci95']}",
            flush=True,
        )

        print(
            "[4/8] Running leak-free 3.0 km segment-hide-recover-pooled-v1 bridge evaluation...",
            flush=True,
        )
        bridge_3km = evaluate_bridge_3km(mm, nuisance_fp, fp, catalogue, depth_2d, slope_2d)
        print(
            f"      Bridge HOLDOUT-DTI (3.0 km): Arm3 = {bridge_3km['dti']:.5f} {bridge_3km['ci95']} "
            f"(Arm2 = {bridge_3km['arm2_global_dti']:.5f}; RSHG1 = {bridge_3km['recorded_rshg1_bridge_dti']:.5f})",
            flush=True,
        )

        print(
            "[5/8] Fitting 45°-rotated 4-sector OOF models for 100% out-of-fold Stitched-OOF deployment...",
            flush=True,
        )
        rot45_folds = trsg1.make_rotated45_folds(fp, catalogue, buffer_px=15)
        rot45_prob_cal = np.zeros(fp.shape, dtype=np.float32)
        for rfold in rot45_folds:
            sid = int(rfold["id"])
            m_rot, res_rot, cal_rot, _ = fit_fold_models(
                mm,
                nuisance_fp,
                fp_ids,
                rfold["train"],
                rfold["visible"],
                fold_seed_base=SEED + 500 + 10 * sid,
                fit_raw_arm=False,
            )
            sec_rows = np.flatnonzero(rfold["valid"].ravel()[fp_ids])
            p_sec = predict_in_chunks(m_rot, res_rot, cal_rot, mm, nuisance_fp, sec_rows)
            rot45_prob_cal.ravel()[fp_ids[sec_rows]] = p_sec
            del m_rot, res_rot, cal_rot, p_sec
            gc.collect()

        stitched_oof_prob = (0.5 * oof_prob_cal + 0.5 * rot45_prob_cal).astype(np.float32)
        sub_z_full = compute_subsurface_conduit_z(mm, fp, fp_ids, fp & ~catalogue)
        del rot45_prob_cal, oof_prob_raw, nuisance_fp
        gc.collect()

        print(
            "[6/8] Auditing pre-placement surface & Two-Regime Stitched-OOF dots against all 138 registry/local/peer rasters...",
            flush=True,
        )
        priority_reg = json.loads((ROOT / "registry/priority_rasters.json").read_text())
        extras = extra_all_local_20261025_entries(fp)

        pre_nov_methods = novelty.compare_prospective_registry(
            stitched_oof_prob,
            fp,
            priority_reg["unique_rasters"],
            ROOT,
            sample_size=200_000,
            extra_entries=extras,
        )
        pre_nov_peers = check_peer_blobs(stitched_oof_prob, None, fp)
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

        final_dots = trsg1.emit_two_regime_poisson(
            stitched_oof_prob,
            fp,
            catalogue,
            depth_2d,
            slope_2d,
            sub_z_full,
            budget_frac=BUDGET_FRAC,
            basin_budget_share=BASIN_SHARE,
            basin_depth_min_m=BASIN_DEPTH_MIN_M,
            basin_slope_max_deg=BASIN_SLOPE_MAX_DEG,
            min_dist=3.0,
            clearance_px=2.0,
        )
        final_nov_methods = novelty.compare_prospective_registry(
            stitched_oof_prob,
            fp,
            priority_reg["unique_rasters"],
            ROOT,
            dots=final_dots,
            sample_size=200_000,
            extra_entries=extras,
        )
        final_nov_peers = check_peer_blobs(stitched_oof_prob, final_dots, fp)

        # Compute Post-GVC1 Out-of-Fold Halo, Basin & LiDAR-Gap Sanity Diagnostics
        dist_cat_all = distance_transform_edt(~catalogue)
        d_on_dots = dist_cat_all[final_dots]
        slope_q75 = float(np.nanpercentile(slope_2d[fp], 75.0))
        basin_mask_fp = fp & (depth_2d >= BASIN_DEPTH_MIN_M) & (slope_2d <= BASIN_SLOPE_MAX_DEG)
        deployment_diagnostics = {
            "n_dots": int(final_dots.sum()),
            "min_dist_to_catalogue_px": float(d_on_dots.min()),
            "frac_d_le_2px": float(np.mean(d_on_dots <= 2.0)),
            "frac_2_to_5px_halo": float(np.mean((d_on_dots > 2.0) & (d_on_dots <= 5.0))),
            "frac_5_to_15px": float(np.mean((d_on_dots > 5.0) & (d_on_dots <= 15.0))),
            "frac_15_to_30px": float(np.mean((d_on_dots > 15.0) & (d_on_dots <= 30.0))),
            "frac_gt_30px_deep_concealed": float(np.mean(d_on_dots > 30.0)),
            "frac_concealed_basin_regime": float(np.mean(basin_mask_fp[final_dots])),
            "frac_top_quartile_steep_slope": float(np.mean(slope_2d[final_dots] > slope_q75)),
            "frac_in_lidar_gap": float(np.mean(~has_lidar_2d[final_dots])),
            "stitched_oof_zero_insample_pixels": True,
        }
        halo_sanity_ok = bool(
            deployment_diagnostics["frac_d_le_2px"] == 0.0
            and deployment_diagnostics["frac_2_to_5px_halo"] <= 0.25
            and deployment_diagnostics["frac_gt_30px_deep_concealed"] >= 0.22
            and 0.15 <= deployment_diagnostics["frac_in_lidar_gap"] <= 0.35
        )
        print(
            f"      Novelty: competing_methods={final_nov_methods['competing_method_rasters_count']} "
            f"(passed={final_nov_methods['method_lane_passed']}, max_overlap={final_nov_methods['method_lane_max_dot_overlap']:.4f}, "
            f"max_|rho|={final_nov_methods['method_lane_max_abs_rank_correlation']:.4f}); "
            f"peers={final_nov_peers['peer_unique_blobs_checked']} "
            f"(passed={final_nov_peers['passed']}, max_overlap={final_nov_peers['max_dot_overlap_within_3px']:.4f})\n"
            f"      Halo sanity: d<=2px={100 * deployment_diagnostics['frac_d_le_2px']:.1f}%, "
            f"2<d<=5px={100 * deployment_diagnostics['frac_2_to_5px_halo']:.1f}% (vs GVC1 45.8%), "
            f"d>30px={100 * deployment_diagnostics['frac_gt_30px_deep_concealed']:.1f}% (vs GVC1 4.1%), "
            f"basin={100 * deployment_diagnostics['frac_concealed_basin_regime']:.1f}%, "
            f"NoLid={100 * deployment_diagnostics['frac_in_lidar_gap']:.1f}%",
            flush=True,
        )
        del stitched_oof_prob, sub_z_full, depth_2d, slope_2d, dist_cat_all
        gc.collect()

        print(
            "[7/8] Writing competition GeoTIFF pair via submission_writer.py & running exact-file C2ST...",
            flush=True,
        )
        content_id = submission.scored_content_id(final_dots, fp, catalogue)
        zeros_name = submission.make_filename(
            "gems24", "trsg1-tworegime-seismic-geo-oof", "20261026", content_id, "zeros"
        )
        nan_name = zeros_name.replace("-zeros.tif", "-nan.tif")
        downloads = ROOT / "docs/downloads"
        downloads.mkdir(parents=True, exist_ok=True)
        tmp_npy = ROOT / "data/prepared/trsg1_pred_tmp.npy"
        np.save(tmp_npy, final_dots.astype(np.float32))
        try:
            res_w_zero = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/submission_writer.py"),
                    str(tmp_npy),
                    str(downloads / zeros_name),
                    "--template",
                    str(template),
                    "--outside",
                    "zero",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=True,
            )
            res_w_nan = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/submission_writer.py"),
                    str(tmp_npy),
                    str(downloads / nan_name),
                    "--template",
                    str(template),
                    "--outside",
                    "nan",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=True,
            )
        finally:
            tmp_npy.unlink(missing_ok=True)

        zeros_path = downloads / zeros_name
        nan_path = downloads / nan_name
        zip_path = submission.zip_single(zeros_path)
        zero_raw_checks = json.loads(res_w_zero.stdout)
        nan_raw_checks = json.loads(res_w_nan.stdout)
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

        c2st_report = run_exact_file_c2st(zeros_path, fp, catalogue)
        print(
            f"      C2ST: labels AUC={c2st_report['labels_first']['observed_auc']:.4f}, "
            f"H24-TRSG1 AUC={c2st_report['observed_auc']:.4f} (null p95={c2st_report['null_p95']:.4f}, "
            f"Holm p={c2st_report['holm_p_value']:.3f}, strict_gate_passed={c2st_report['strict_gate_passed']})",
            flush=True,
        )

        print(
            "[8/8] Writing run card, schema-v2 preflight receipt, and verifying recorded artifacts...",
            flush=True,
        )
        canary_ok = bool(canary_44["passed"] and oof_canary["passed"])
        method_nov_ok = bool(final_nov_methods["method_lane_passed"] and final_nov_peers["passed"])
        literal_nov_ok = bool(final_nov_methods["literal_all_entries_passed"])
        hcw_dti = float(hcw_recorded["holdout"]["dti"])
        beats_hcw_ok = bool(sum_arm3["dti"] > hcw_dti)
        beats_oof_ok = bool(
            sum_arm3["dti"] > sum_oof_base["dti"] and paired_arm3_vs_oof["ci95_strictly_positive"]
        )
        c2st_ok = bool(c2st_report["strict_gate_passed"])
        format_ok = bool(
            zero_raw_checks["format_valid"]
            and nan_raw_checks["format_valid"]
            and strict_whole_array_ok(zero_raw_checks)
        )
        technical_gates_passed = bool(
            canary_ok
            and method_nov_ok
            and beats_hcw_ok
            and beats_oof_ok
            and c2st_ok
            and halo_sanity_ok
            and format_ok
        )

        # Fail-closed per AGENTS.md & PARALLEL-RUN PROTOCOL Rules 1 & 6:
        # literal_all_entries_passed is False due to retained registry-039 spacing-5 lattice,
        # lane is provisional, and weekly-slot promotion requires a separate selector step.
        verdict = "negative"
        ok_to_submit = False

        note = (
            f"GEMS24 TRSG1 | 44ch 2reg-StOOF {content_id} | "
            f"DTI {sum_arm3['dti']:.4f}; DO NOT SUBMIT"
        )
        if len(note) > 140:
            raise AssertionError(f"Short note length {len(note)} > 140")

        note_file = f"note-{zeros_name[:-4]}.txt"
        checks_file = f"checks-{zeros_name[:-4]}.json"
        (downloads / note_file).write_text(note + "\n")
        save_json(checks, downloads / checks_file)

        blockers = []
        if not beats_hcw_ok:
            blockers.append(
                f"Did not beat current best gate-passing GEMSDOE24 detector H24-FUSE-HCW ({hcw_dti:.5f})"
            )
        if not beats_oof_ok:
            blockers.append(
                f"Did not beat oof_multiphysics_hgb_d3 ({sum_oof_base['dti']:.5f}) with strictly positive 95% paired CI"
            )
        if not c2st_ok:
            blockers.append(
                f"Exact-file C2ST nuisance audit >= 0.55 or flagged (AUC={c2st_report['observed_auc']:.4f}, Holm p={c2st_report['holm_p_value']:.3f})"
            )
        if not method_nov_ok:
            blockers.append(
                "Competing-method or peer 3-px dot overlap (>0.70) / Spearman (|rho|>0.90) exceeded"
            )
        if not halo_sanity_ok:
            blockers.append("Failed post-GVC1 deployment halo / basin / LiDAR-gap sanity gate")
        if not literal_nov_ok:
            blockers.append(
                "Retained synthetic spacing-5 calibration lattice (registry-039) covers 99.87% of footprint within 3 px (literal overlap = 1.0)"
            )
        blockers.append(
            "Provisional parallel lane without single assigned method paragraph; live weekly-slot authorization requires a separate selector step (Protocol Rule 6)"
        )

        # Identify closest competing method comparator for transparent audit
        comp_rows = [
            r for r in final_nov_methods["rows"] if r.get("entry_role") == "competing_method_lane"
        ]
        worst_comp_row = max(
            comp_rows, key=lambda r: float(r.get("candidate_dot_overlap_within_3px") or 0.0)
        )

        elapsed = float(time.monotonic() - t0)
        card = {
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "lane_id": "H24-TRSG1",
            "lane_status": "provisional_unassigned_method_paragraph",
            "preregistration": "knowledge/19_preregistered_TRSG1_2026-10-26.md",
            "hypothesis": (
                "Two-Regime 44-channel Seismic-Geothermal Step-Over Saddle, Drainage-Incision & "
                "Terrain-Conditioned Dual-Partition Stitched-OOF HGB Detector (resolving GVC1's "
                "0.0859 in-sample halo collapse and RSHG1's SW basin / >70% ridge-overlap bottlenecks)"
            ),
            "mechanism": (
                "Integrates previously unused competition earthquake seismicity bands (ieq_n100a15, "
                "deq_n100a15 structure-tensor anisotropy & swarm excess), Quaternary volcanic vents "
                "(gdr_volcanic_vents_in_footprint.csv), Faulds & Hinz (2015) hyperbolic Hessian saddle "
                "twists (-det H > 0 on DEM & gravity/RTP), piedmont/drainage knickpoint breaks, and "
                "scale-localized (800 m - 3 km DoG, zero global EDT) INGENIOUS sinter/2m-probe/spring "
                "upflow; applies selective survey/siting nuisance residualization + terrain-relief-stratified "
                "LiDAR-gap calibration strictly on fold.train; and deploys a 100% out-of-fold "
                "0.5*Quadrant_OOF + 0.5*Rotated45_OOF surface via Two-Regime Concealed-Basin (26%) + "
                "Range-Front/Step-Over (74%) Poisson allocation (min_dist=3, d_cat>2 px)"
            ),
            "named_non_fault_mimic": (
                "Erosional hogbacks on tilted Oligocene-Miocene welded tuffs / caldera ring dikes, "
                "Pleistocene Lake Lahontan (~1,335 m) wave-cut shorelines & tufa mounds, mining-blast "
                "seismicity, and lateral thermal outflow plumes in permeable fanglomerates"
            ),
            "holdout": sum_arm3,
            "diagnostic_ablations": {
                "arm1_trsg1_raw44_global_poisson": sum_arm1,
                "arm2_trsg1_selres_terraincal_global_poisson": sum_arm2,
            },
            "reconstructed_oof_multiphysics_baseline": sum_oof_base,
            "paired_comparisons": {
                "arm3_minus_reconstructed_oof_hgb_d3": paired_arm3_vs_oof,
                "arm2_minus_reconstructed_oof_hgb_d3": paired_arm2_vs_oof,
                "arm1_minus_reconstructed_oof_hgb_d3": paired_arm1_vs_oof,
                "arm2_minus_arm1_selective_res_and_terrain_cal": paired_arm2_vs_arm1,
                "arm3_minus_arm2_two_regime_allocation": paired_arm3_vs_arm2,
                "arm3_minus_recorded_fuse_hcw": {
                    "recorded_fuse_hcw_dti": hcw_dti,
                    "delta_dti": float(sum_arm3["dti"] - hcw_dti),
                },
                "arm3_minus_recorded_rshg1": {
                    "recorded_rshg1_dti": float(rshg1_recorded["holdout"]["dti"]),
                    "delta_dti": float(sum_arm3["dti"] - float(rshg1_recorded["holdout"]["dti"])),
                },
                "arm3_minus_recorded_gvc1_insample_failed_novelty": {
                    "recorded_gvc1_holdout_dti": float(gvc1_recorded["holdout"]["dti"]),
                    "owner_reported_gvc1_live_score": 0.0859,
                    "delta_holdout_dti": float(
                        sum_arm3["dti"] - float(gvc1_recorded["holdout"]["dti"])
                    ),
                },
            },
            "bridge_protocol_holdout": bridge_3km,
            "leakage_canary": {
                "passed": canary_ok,
                "n_features_checked": canary_44["n_features_checked"],
                "worst_feature": canary_44["worst_feature"],
                "worst_pooled_auc": canary_44["worst_pooled_auc"],
                "oof_calibrated_prob_pooled_auc": oof_canary["features"][
                    "trsg1_oof_calibrated_prob"
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
                "closest_competing_method_raster": {
                    "id": worst_comp_row["registry_id"],
                    "file": worst_comp_row["file"],
                    "dot_overlap_within_3px": float(
                        worst_comp_row["candidate_dot_overlap_within_3px"]
                    ),
                },
                "peer_blobs_max_abs_rank_correlation": max(
                    float(final_nov_peers["max_abs_surface_spearman"]),
                    float(final_nov_peers["max_abs_dot_spearman"] or 0.0),
                ),
                "peer_blobs_max_overlap_within_3px": float(
                    final_nov_peers["max_dot_overlap_within_3px"]
                ),
                "closest_peer_blob": final_nov_peers["max_overlap_peer"],
                "literal_all_entries_max_overlap_within_3px": float(
                    final_nov_methods["max_dot_overlap"]
                ),
            },
            "deployment_halo_and_regime_diagnostics": deployment_diagnostics,
            "exact_file_nuisance_audit": c2st_report,
            "band_provenance_disclosure": (
                "IR-BAND-PROVENANCE disclosed: tc, ieq_n100a15, and deq_n100a15 band aliases "
                "follow shared geofeatures.BAND_ORDER on verified owner mirror training_features.tif "
                f"(SHA-256 {input_hashes['data/training_features.tif']}); "
                "all 44 channels passed two-polarity leakage canaries before training."
            ),
            "raster_sha256": sha256_file(zeros_path),
            "nan_outside_artifact": nan_name,
            "nan_outside_sha256": sha256_file(nan_path),
            "zip_artifact": zip_path.name,
            "zip_sha256": sha256_file(zip_path),
            "positive_pixels": int(final_dots.sum()),
            "min_distance_to_public_catalogue_px": deployment_diagnostics[
                "min_dist_to_catalogue_px"
            ],
            "validator_output": zero_raw_checks,
            "nan_validator_output": nan_raw_checks,
            "submission_name": zeros_name,
            "note": note,
            "note_length": len(note),
            "technical_gate_breakdown": {
                "format_and_strict_0_1_range": format_ok,
                "two_polarity_leakage_canary": canary_ok,
                "method_and_peer_novelty": method_nov_ok,
                "beats_fuse_hcw_best_gate_passing_lane": beats_hcw_ok,
                "beats_oof_multiphysics_hgb_d3_with_95ci": beats_oof_ok,
                "exact_file_c2st_nuisance_gate": c2st_ok,
                "stitched_oof_halo_and_lidar_gap_sanity": halo_sanity_ok,
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
                "experiments_run_this_session": 3,
                "arms_evaluated": [
                    "Arm 1: TRSG1-Raw44",
                    "Arm 2: TRSG1-SelRes-TerrainCal",
                    "Arm 3: TRSG1-TwoRegime-StitchedOOF",
                ],
                "max_experiments": 3,
                "elapsed_seconds": elapsed,
                "max_hours": 2.0,
                "peak_rss_mib": peak_rss_mib(),
            },
        }
        save_json(card, RUN_CARD_JSON)
        save_json(card, DOCS_RUN_CARD_JSON)

        download_meta = {
            "lane_id": "H24-TRSG1",
            "file": zeros_name,
            "sha256": card["raster_sha256"],
            "nan_file": nan_name,
            "nan_sha256": card["nan_outside_sha256"],
            "zip_file": zip_path.name,
            "zip_sha256": card["zip_sha256"],
            "pixel_count": int(final_dots.sum()),
            "min_distance_to_catalogue_px": deployment_diagnostics["min_dist_to_catalogue_px"],
            "note": note,
            "note_file": note_file,
            "checks_file": checks_file,
            "preview_png": "assets/trsg1-preview.png",
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

        slim_final_nov = {k: v for k, v in final_nov_methods.items() if k != "rows"}
        slim_pre_nov = {k: v for k, v in pre_nov_methods.items() if k != "rows"}

        full_exp = {
            "generated_utc": card["generated_utc"],
            "preregistration": card["preregistration"],
            "experiments_evaluated": 3,
            "input_hashes": input_hashes,
            "feature_names": list(trsg1.FEATURE_NAMES),
            "feature_finite_coverage": col_coverage,
            "canary_44": canary_44,
            "oof_canary": oof_canary,
            "arm1_raw44": sum_arm1,
            "arm2_selres_terraincal": sum_arm2,
            "arm3_tworegime_primary": sum_arm3,
            "reconstructed_oof_baseline": sum_oof_base,
            "paired_comparisons": card["paired_comparisons"],
            "bridge_3km": bridge_3km,
            "deployment_halo_and_regime_diagnostics": deployment_diagnostics,
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

        verified = verify_recorded()
        print(
            json.dumps(
                {
                    "status": "completed",
                    "verified_recorded": verified["verified"],
                    "submission_name": zeros_name,
                    "sha256": card["raster_sha256"],
                    "arm1_dti": sum_arm1["dti"],
                    "arm2_dti": sum_arm2["dti"],
                    "arm3_dti": sum_arm3["dti"],
                    "arm3_ci95": sum_arm3["ci95"]["interval"],
                    "oof_baseline_dti": sum_oof_base["dti"],
                    "paired_delta_arm3_vs_oof": paired_arm3_vs_oof["delta_dti"],
                    "paired_ci95_arm3_vs_oof": paired_arm3_vs_oof["ci95"],
                    "bridge_3km_dti": bridge_3km["dti"],
                    "method_max_overlap_3px": final_nov_methods["method_lane_max_dot_overlap"],
                    "peer_max_overlap_3px": final_nov_peers["max_dot_overlap_within_3px"],
                    "c2st_auc": c2st_report["observed_auc"],
                    "c2st_holm_p": c2st_report["holm_p_value"],
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
