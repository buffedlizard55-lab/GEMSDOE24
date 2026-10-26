#!/usr/bin/env python3
"""Execute or verify H24-S3DEP1 (Seamless 10 m 3DEP Monoclinal-Step x Crustal-Seismic x Conduit OOF).

Preregistration: ``knowledge/29_preregistered_S3DEP1_2026-10-26.md`` (commit ``7e6db4d428ae``).
Budget: <= 3 experiments, <= 2 hours. Refuses implicit reruns once frozen receipts exist.
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import resource
import struct
import subprocess
import sys
import time
import zipfile
import zlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from scipy.ndimage import binary_erosion, distance_transform_edt
from scipy.stats import rankdata
from sklearn.ensemble import HistGradientBoostingClassifier
from threadpoolctl import threadpool_limits

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems import (  # noqa: E402
    c2s2,
    confounds,
    dprf1,
    emission,
    footprint,
    gvc,
    holdout,
    novelty,
    s3dep1,
    sahg1,
    selector,
    submission,
)
from gems.validator import sha256_file  # noqa: E402

LANE_ID = "H24-S3DEP1"
PREREG_PATH = "knowledge/29_preregistered_S3DEP1_2026-10-26.md"
PREREG_COMMIT = "7e6db4d428aea6c26a769feed71f4de04f50f613"

SEED = 20261026
GVC_BASE_SEED = 20261025
FULL_DOT_BUDGET = 37654
PRIMARY_SHARE = 0.72
MIN_SPACING_PX = 2.8
CATALOGUE_CLEARANCE_PX = 2.0
RECORDED_DPRF1_DTI = 0.1637924246971501

BASELINE_D3_PARAMS: dict[str, Any] = {
    "max_iter": 80,
    "max_leaf_nodes": 15,
    "learning_rate": 0.08,
    "l2_regularization": 5.0,
    "early_stopping": False,
}

STACK61_PATH = ROOT / "data/prepared/s3dep1_stack61.dat"
WORK_DIR = ROOT / "data/prepared/s3dep1_work"
STAGE0_JSON = WORK_DIR / "stage0_canary.json"
STAGE1_JSON = WORK_DIR / "stage1_summary.json"
STAGE1_ARRAYS = WORK_DIR / "stage1_oof_quad.npz"
STAGE2_JSON = WORK_DIR / "stage2_bridge.json"
STAGE2_ARRAYS = WORK_DIR / "stage2_stitched.npz"

EXPERIMENT_JSON = ROOT / "evidence/s3dep1_experiment_20261026.json"
RUN_CARD_JSON = ROOT / "evidence/s3dep1_run_card_20261026.json"
SELECTOR_JSON = ROOT / "evidence/s3dep1_selector_20261026.json"
DOCS_RUN_CARD_JSON = ROOT / "docs/data/s3dep1_run_card.json"
DOCS_SELECTOR_JSON = ROOT / "docs/data/s3dep1_selector.json"
DOCS_DOWNLOAD_JSON = ROOT / "docs/data/s3dep1_download.json"
PREVIEW_PNG = ROOT / "docs/assets/s3dep1-preview.png"


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
    rgb[fp_small] = (221, 233, 229)
    rgb[d_small] = (18, 92, 148)
    raw = b"".join(b"\x00" + rgb[y].tobytes() for y in range(sh))
    ihdr = struct.pack(">IIBBBBB", sw, sh, 8, 2, 0, 0, 0)
    png = (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", ihdr)
        + _png_chunk(b"IDAT", zlib.compress(raw, level=9))
        + _png_chunk(b"IEND", b"")
    )
    out_path.write_bytes(png)


def run_batched_canary(
    context: holdout.SegmentHoldout,
    fp: np.ndarray,
    stack_mm: np.ndarray,
    names: list[str],
    *,
    batch_size: int = 4,
) -> dict[str, Any]:
    """Two-polarity single-feature leakage canary over all 61 S3DEP1 channels."""
    fp_ids = np.flatnonzero(fp.ravel())
    merged: dict[str, Any] = {}
    last_meta: dict[str, Any] = {}
    for start in range(0, len(names), batch_size):
        batch_names = names[start : start + batch_size]
        fdict: dict[str, np.ndarray] = {}
        for off, name in enumerate(batch_names):
            grid = np.full(fp.shape, np.nan, dtype=np.float32)
            grid.ravel()[fp_ids] = stack_mm[:, start + off]
            fdict[name] = grid
        rep = context.canary(fdict, seed=GVC_BASE_SEED, max_per_class=15000)
        merged.update(rep["features"])
        last_meta = rep
        del fdict
        gc.collect()
    passed = not any(v["leakage_suspected"] for v in merged.values())
    worst_name = max(
        merged, key=lambda k: max(merged[k]["pooled_auc"], 1.0 - merged[k]["pooled_auc"])
    )
    worst_auc = float(merged[worst_name]["pooled_auc"])
    dem10_aucs = {
        k: float(merged[k]["pooled_auc"])
        for k in (*s3dep1.DEM10_12_NAMES, *s3dep1.S3DEP1_DERIVED6_NAMES)
        if k in merged
    }
    restored6_aucs = {
        k: float(merged[k]["pooled_auc"]) for k in s3dep1.RESTORED_TRAIN6_NAMES if k in merged
    }
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
        "dem10_and_derived_pooled_aucs": dem10_aucs,
        "restored_train6_pooled_aucs": restored6_aucs,
        "features": merged,
        "interpretation": last_meta["interpretation"],
    }


def build_oof_multiphysics_hgb_d3(
    context: holdout.SegmentHoldout,
    base_mm: np.ndarray,
    base_names: list[str],
    base_nc: int,
    fp: np.ndarray,
) -> list[np.ndarray]:
    """Reproduce exact 27-channel oof_multiphysics_hgb_d3 (0.13000) on SegmentHoldout."""
    fp_ids = np.flatnonzero(fp.ravel())
    lidar_path = ROOT / "data/external/lidar_scarp_features_u8.tif"
    lidar_meta = json.loads(lidar_path.with_name("lidar_scarp_features.json").read_text())
    rad_path = ROOT / "data/external/geodawn_rad_u8.tif"
    rad_meta = json.loads(rad_path.with_name("geodawn_rad.json").read_text())
    ext_path = ROOT / "data/external/geodawn_extensions_u8.tif"
    ext_meta = json.loads(ext_path.with_name("geodawn_extensions.json").read_text())

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
    for gname in sahg1.GEOPHYS_BANDS:
        gcol = base_mm[:, base_names.index(gname)]
        gmask = np.zeros(fp.shape, dtype=bool)
        gmask.ravel()[fp_ids] = np.isfinite(gcol)
        rv &= gmask
    support = binary_erosion(
        rv,
        structure=np.ones(
            (2 * sahg1.STENCIL_RADIUS_PX + 1, 2 * sahg1.STENCIL_RADIUS_PX + 1), dtype=bool
        ),
        border_value=False,
    )
    del rv
    preds: list[np.ndarray] = []
    with threadpool_limits(limits=2):
        for fold in context.folds:
            fid = int(fold["id"])
            rng = np.random.default_rng(GVC_BASE_SEED + fid)
            dist_vis = distance_transform_edt(~fold["visible"])
            pos_mask = fold["train"] & fold["visible"]
            neg_mask = fold["train"] & (~fold["visible"]) & (dist_vis >= 9)
            pos_ids = np.flatnonzero(pos_mask.ravel()[fp_ids])
            neg_ids = np.flatnonzero(neg_mask.ravel()[fp_ids])
            pos_sel = rng.choice(pos_ids, min(20000, len(pos_ids)), replace=False)
            neg_sel = rng.choice(neg_ids, min(60000, len(neg_ids)), replace=False)
            tr_sel = np.r_[pos_sel, neg_sel]
            y_tr = np.r_[np.ones(len(pos_sel), np.int8), np.zeros(len(neg_sel), np.int8)]
            x_tr = np.asarray(base_mm[tr_sel, :base_nc], dtype=np.float32)
            clf = HistGradientBoostingClassifier(
                **BASELINE_D3_PARAMS, random_state=GVC_BASE_SEED
            ).fit(x_tr, y_tr)
            val_ids = np.flatnonzero(fold["valid"].ravel()[fp_ids])
            f_surf = np.zeros(fp.shape, dtype=np.float32)
            for s in range(0, len(val_ids), 150_000):
                ch = val_ids[s : s + 150_000]
                f_surf.ravel()[fp_ids[ch]] = clf.predict_proba(
                    np.asarray(base_mm[ch, :base_nc], dtype=np.float32)
                )[:, 1].astype(np.float32)
            budget = int(round(0.0073 * int(fold["valid"].sum())))
            elig = support & fold["valid"] & (~fold["visible"])
            preds.append(
                emission.priority_poisson(f_surf, elig, budget, min_dist=3).astype(np.uint8)
            )
            del f_surf, x_tr, clf
            gc.collect()
    return preds


def build_dprf1_replay_preds(
    context: holdout.SegmentHoldout,
    nuisance_fp: np.ndarray,
    fp: np.ndarray,
    catalogue: np.ndarray,
) -> list[np.ndarray]:
    """Reproduce exact H24-DPRF1 fold dot arrays for paired bootstrap comparison."""
    fp_ids = np.flatnonzero(fp.ravel())
    prep_meta = json.loads((ROOT / "data/prepared/features.json").read_text())
    base_names = list(prep_meta["names"])
    base_mm = np.load(ROOT / "data/prepared/features.npy", mmap_mode="r")
    gvc_mm = np.load(ROOT / "data/prepared/gvc1_features.npy", mmap_mode="r")
    gvc_names = list(gvc.GVC1_FEATURE_NAMES)
    sahg_mm = np.load(ROOT / "data/prepared/sahg4_features.npy", mmap_mode="r")
    sahg_names = list(dprf1.SAHG4_NAMES)
    names52 = base_names + gvc_names + sahg_names

    total_offcat = int((fp & (~catalogue)).sum())
    preds: list[np.ndarray] = []
    for fold in context.folds:
        fid = int(fold["id"])
        f_offcat = int((fold["valid"] & (~fold["visible"])).sum())
        k_fold = int(round(FULL_DOT_BUDGET * f_offcat / total_offcat))
        p_s3, p_c3, _ = dprf1.fit_and_predict_fold(
            base_mm,
            gvc_mm,
            sahg_mm,
            nuisance_fp,
            names52,
            fp,
            fp_ids,
            train_mask=fold["train"],
            visible_mask=fold["visible"],
            predict_mask=fold["valid"],
            neg_mode="stratified_d3",
            seed=SEED + 10 * fid,
        )
        p_s3 = dprf1.debiased_apron_surface(p_s3, fold["valid"], fold["visible"])
        p_c3 = dprf1.debiased_apron_surface(p_c3, fold["valid"], fold["visible"])
        d_dprf = dprf1.two_regime_submodular_allocate(
            p_s3,
            p_c3,
            fold["valid"],
            fold["visible"],
            budget=k_fold,
            primary_share=0.68,
            min_spacing_px=2.8,
            catalogue_clearance_px=2.0,
        )
        preds.append((d_dprf > 0.5).astype(np.uint8))
        del p_s3, p_c3, d_dprf
        gc.collect()
    del base_mm, gvc_mm, sahg_mm
    gc.collect()
    return preds


def evaluate_bridge_3km(
    stack_mm: np.ndarray,
    nuisance_fp: np.ndarray,
    all_names: list[str],
    fp: np.ndarray,
    catalogue: np.ndarray,
) -> dict[str, Any]:
    """Evaluate Arm 3 (H24-S3DEP1 primary) on the 3.0 km / 20 km tile bridge protocol."""
    fp_ids = np.flatnonzero(fp.ravel())
    total_offcat = int((fp & (~catalogue)).sum())
    tile_rows_all = []
    fold_details = []
    for fid, fold in enumerate(holdout.segment_folds(fp, catalogue, buffer_px=30)):
        surfs, _ = s3dep1.fit_and_predict_s3dep1_fold(
            stack_mm,
            nuisance_fp,
            all_names,
            fp,
            fp_ids,
            train_mask=fold["training"],
            visible_mask=fold["visible"],
            predict_mask=fold["test"],
            seed=SEED + 300 + 13 * fid,
            return_all_arms=False,
        )
        f_offcat = int((fold["test"] & (~fold["visible"])).sum())
        k_fold = int(round(FULL_DOT_BUDGET * f_offcat / total_offcat))
        p_s = dprf1.debiased_apron_surface(surfs["arm3_sharp"], fold["test"], fold["visible"])
        p_c = dprf1.debiased_apron_surface(surfs["arm3_conduit"], fold["test"], fold["visible"])
        dots = dprf1.two_regime_submodular_allocate(
            p_s,
            p_c,
            fold["test"],
            fold["visible"],
            budget=k_fold,
            primary_share=PRIMARY_SHARE,
            min_spacing_px=MIN_SPACING_PX,
            catalogue_clearance_px=CATALOGUE_CLEARANCE_PX,
        )
        t_rows, ref = holdout.spatial_components(
            dots > 0.5, fold["hidden"] & fold["test"], fold["test"], fold["visible"], tile_px=200
        )
        tile_rows_all.append(t_rows)
        fold_details.append({"fold": fold["name"], **ref})
        del surfs, p_s, p_c, dots
        gc.collect()

    summed_tiles = np.sum(tile_rows_all, axis=0)
    yy, xx = np.nonzero(fp)
    nx = (fp.shape[1] + 199) // 200
    active_tiles = np.unique((yy // 200) * nx + xx // 200)
    pooled = holdout.pooled_components(fold_details)
    ci95 = holdout.pooled_bootstrap(summed_tiles[active_tiles], resamples=1000, seed=SEED)
    dprf1_card = json.loads((ROOT / "evidence/dprf1_run_card_20261026.json").read_text())
    rec_dprf1_br = float(dprf1_card["bridge_protocol_holdout"]["dti"])
    return {
        "label": "HOLDOUT-DTI",
        "evaluator_version": holdout.SEGMENT_EVALUATOR_VERSION,
        "dti": pooled["dti"],
        "ci95": ci95,
        "n_withheld_positives": int(pooled["n_truth"]),
        "n_emitted": int(pooled["n_emitted"]),
        "buffer_m": 3000,
        "recorded_dprf1_bridge_dti": rec_dprf1_br,
        "delta_vs_dprf1_bridge": float(pooled["dti"] - rec_dprf1_br),
        "folds": fold_details,
    }


def local_lane_entries(fp: np.ndarray, existing_shas: set[str]) -> list[dict[str, Any]]:
    """Discover all existing local GEMSDOE24 method-lane GeoTIFFs in docs/downloads/."""
    seen = set(existing_shas)
    out: list[dict[str, Any]] = []
    for p in sorted((ROOT / "docs/downloads").glob("*.tif")):
        if "s3dep1" in p.name.lower():
            continue
        with rasterio.open(p) as ds:
            if ds.shape != fp.shape or ds.count != 1:
                continue
            a = ds.read(1)
        if not np.isfinite(a[fp]).all():
            continue
        fp_sha = hashlib.sha256(np.asarray(a[fp], dtype="<f4").tobytes()).hexdigest()
        if fp_sha in seen:
            continue
        seen.add(fp_sha)
        rel = str(p.relative_to(ROOT))
        out.append(
            {
                "id": f"local-{p.stem[:36]}",
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
    """Check all on-grid blobs in registry/peer_rasters_20261025.json."""
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
    max_overlap_file = None
    checked = 0
    missing = 0
    for row in blobs.values():
        p = ROOT / row["cache_path"]
        if not p.exists():
            missing += 1
            continue
        with rasterio.open(p) as ds:
            if ds.shape != fp.shape:
                continue
            a = ds.read(1)
        checked += 1
        s_rho = novelty.rank_correlation(surf_ranks, a[fp])
        if s_rho is not None:
            max_surf_rho = max(max_surf_rho, abs(float(s_rho)))
        if dots is not None and dot_ranks is not None:
            d_rho = novelty.rank_correlation(dot_ranks, a[fp])
            if d_rho is not None:
                max_dot_rho = max(max_dot_rho, abs(float(d_rho)))
            ov = novelty.dot_overlap(dots > 0.5, fp & np.isfinite(a) & (a > 0))[
                "candidate_within_3px_of_reference"
            ]
            if ov is not None and float(ov) > max_overlap:
                max_overlap = float(ov)
                max_overlap_file = f"{row['repo']}:{row['path']}"
    passed = (
        checked > 0
        and missing == 0
        and max_surf_rho <= 0.90
        and (dots is None or (max_dot_rho <= 0.90 and max_overlap <= 0.70))
    )
    return {
        "peer_unique_blobs_checked": checked,
        "peer_blobs_missing_from_cache": missing,
        "max_abs_surface_spearman": max_surf_rho,
        "max_abs_dot_spearman": max_dot_rho if dots is not None else None,
        "max_dot_overlap_within_3px": max_overlap if dots is not None else None,
        "max_overlap_peer_artifact": max_overlap_file,
        "passed": passed,
    }


def check_nine_site_20261026_refresh(
    surface: np.ndarray, dots: np.ndarray, fp: np.ndarray
) -> dict[str, Any]:
    """Cross-site novelty check against all live-cached 2026-10-26 sibling focus TIFs."""
    manifest_p = ROOT / "data/research/nine_site_20261026_refresh/manifest_20261026.json"
    if not manifest_p.exists():
        return {"checked": 0, "rows": [], "max_dot_overlap_within_3px": None, "passed": None}
    manifest = json.loads(manifest_p.read_text())
    surf_ranks = rankdata(surface[fp])
    rows = []
    max_ov = 0.0
    max_rho = 0.0
    for item in manifest:
        p = ROOT / item["cache_path"]
        if not p.exists():
            continue
        with rasterio.open(p) as ds:
            if ds.shape != fp.shape:
                continue
            a = ds.read(1)
        s_rho = float(abs(novelty.rank_correlation(surf_ranks, a[fp]) or 0.0))
        ov = float(
            novelty.dot_overlap(dots > 0.5, fp & np.isfinite(a) & (a > 0))[
                "candidate_within_3px_of_reference"
            ]
            or 0.0
        )
        max_ov = max(max_ov, ov)
        max_rho = max(max_rho, s_rho)
        rows.append(
            {
                "repo": item["repo"],
                "head_commit": item["head_commit"],
                "path": item["path"],
                "sha256": item["sha256"],
                "surface_abs_spearman": s_rho,
                "candidate_dot_overlap_within_3px": ov,
            }
        )
    return {
        "checked": len(rows),
        "max_surface_abs_spearman": max_rho,
        "max_dot_overlap_within_3px": max_ov,
        "passed": bool(len(rows) > 0 and max_rho <= 0.90 and max_ov <= 0.70),
        "rows": rows,
    }


def compute_distance_profile(
    dots_bool: np.ndarray, catalogue: np.ndarray, fp: np.ndarray
) -> dict[str, Any]:
    dist_cat = distance_transform_edt(~catalogue)
    d = dist_cat[dots_bool & fp]
    return {
        "n_dots": int(len(d)),
        "min_dist_px": float(d.min()) if len(d) else None,
        "median_dist_px": float(np.median(d)) if len(d) else None,
        "frac_le_2px": float(np.mean(d <= 2.0)) if len(d) else 0.0,
        "frac_2_to_5px": float(np.mean((d > 2.0) & (d <= 5.0))) if len(d) else 0.0,
        "frac_5_to_9px": float(np.mean((d > 5.0) & (d <= 9.0))) if len(d) else 0.0,
        "frac_2_to_9px_apron": float(np.mean((d > 2.0) & (d <= 9.0))) if len(d) else 0.0,
        "frac_9_to_20px": float(np.mean((d > 9.0) & (d <= 20.0))) if len(d) else 0.0,
        "frac_gt_20px_farfield": float(np.mean(d > 20.0)) if len(d) else 0.0,
    }


def run_exact_file_c2st(
    zeros_tif_path: Path, catalogue: np.ndarray, fp: np.ndarray
) -> dict[str, Any]:
    """Audit labels first, then the exact emitted GeoTIFF on road/claim/4-block confounds."""
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
        seed=GVC_BASE_SEED,
    )
    with rasterio.open(zeros_tif_path) as ds:
        cand_mask = (ds.read(1) > 0.5) & fp
    cand_res = c2s2.c2s2_test(
        "h24_s3dep1_exact_file",
        cand_mask,
        cfeat,
        fold_grid,
        fp,
        n_per_class=8000,
        n_null=99,
        seed=GVC_BASE_SEED,
    )
    adj_p = c2s2.holm_adjust([label_res.p_value, cand_res.p_value])
    flagged = bool(
        adj_p[1] <= 0.05 and cand_res.observed_auc >= 0.55 and cand_res.margin_vs_p95 >= 0.02
    )
    return {
        "method": "Classifier two-sample test (Lopez-Paz & Oquab, ICLR 2017) with 10 km block label swaps",
        "labels_audited_first": True,
        "nuisance_families_only": sorted(cfeat.keys()),
        "block_boundary_status": "derived_audited_not_official_coordinates",
        "labels_first": {
            "observed_auc": float(label_res.observed_auc),
            "fold_aucs": [float(x) for x in label_res.fold_aucs],
            "null_p95": float(label_res.null_auc_p95),
            "margin_vs_p95": float(label_res.margin_vs_p95),
            "raw_p_value": float(label_res.p_value),
            "holm_p_value": float(adj_p[0]),
        },
        "candidate": {
            "file": zeros_tif_path.name,
            "sha256": sha256_file(zeros_tif_path),
            "positive_pixels": int(cand_mask.sum()),
            "observed_auc": float(cand_res.observed_auc),
            "fold_aucs": [float(x) for x in cand_res.fold_aucs],
            "null_p95": float(cand_res.null_auc_p95),
            "margin_vs_p95": float(cand_res.margin_vs_p95),
            "raw_p_value": float(cand_res.p_value),
            "holm_p_value": float(adj_p[1]),
            "strict_gate_flagged": flagged,
            "strict_gate_passed": not flagged,
        },
    }


def verify_recorded() -> dict[str, Any]:
    """Verify frozen S3DEP1 receipts, GeoTIFF variants, ZIP, selector, preflight, and <=140-char note."""
    for p in (
        EXPERIMENT_JSON,
        RUN_CARD_JSON,
        SELECTOR_JSON,
        DOCS_RUN_CARD_JSON,
        DOCS_SELECTOR_JSON,
        DOCS_DOWNLOAD_JSON,
        PREVIEW_PNG,
    ):
        if not p.exists():
            raise SystemExit(f"Missing recorded S3DEP1 artifact: {p}")
    card = json.loads(RUN_CARD_JSON.read_text())
    docs_card = json.loads(DOCS_RUN_CARD_JSON.read_text())
    saved_sel = json.loads(SELECTOR_JSON.read_text())
    docs_sel = json.loads(DOCS_SELECTOR_JSON.read_text())
    dl = json.loads(DOCS_DOWNLOAD_JSON.read_text())
    if card != docs_card or saved_sel != docs_sel:
        raise SystemExit("Evidence and docs/data S3DEP1 run cards or selector receipts disagree")
    if card.get("selector_receipt") != saved_sel:
        raise SystemExit("S3DEP1 run card embedded selector receipt disagrees with selector file")
    prereg_path = ROOT / card.get("preregistration", "")
    prereg_commit = card.get("preregistration_commit", "")
    if not prereg_path.is_file() or not prereg_commit or prereg_commit == "uncommitted":
        raise SystemExit("S3DEP1 preregistration file or commit hash missing")
    anc = subprocess.run(
        ["git", "merge-base", "--is-ancestor", prereg_commit, "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if anc.returncode != 0:
        raise SystemExit(
            f"S3DEP1 preregistration commit {prereg_commit} is not an ancestor of HEAD"
        )

    template = ROOT / "data/bridge/sample_submission.tif"
    zeros_path = ROOT / "docs/downloads" / card["submission_name"]
    nan_path = ROOT / "docs/downloads" / card["nan_outside_artifact"]
    zip_path = ROOT / "docs/downloads" / card["zip_artifact"]
    checks_path = ROOT / "docs/downloads" / dl["checks_file"]
    note_path = ROOT / "docs/downloads" / dl["note_file"]
    preflight_path = zeros_path.with_suffix(".preflight.json")
    dl_sel_path = zeros_path.with_suffix(".selector.json")

    fresh_sel = selector.verify_selector(zeros_path, template, card)
    ok_sel = bool(fresh_sel["ok_to_submit"]) and fresh_sel["decision"] == "OK_TO_SUBMIT"
    saved_gates = dict(saved_sel.get("gates") or {})
    fresh_gates = dict(fresh_sel.get("gates") or {})
    g3 = "g3_holdout_beats_recorded_best_and_paired_baseline"
    saved_gates.pop(g3, None)
    fresh_gates.pop(g3, None)
    if (
        saved_gates != fresh_gates
        or saved_sel.get("decision") != fresh_sel.get("decision")
        or json.loads(dl_sel_path.read_text()) != saved_sel
        or card.get("ok_to_submit") is not ok_sel
        or dl.get("ok_to_submit") is not ok_sel
        or (card.get("verdict") == "promote") is not ok_sel
    ):
        raise SystemExit(
            "S3DEP1 run card/download disagrees with independent gems.selector receipt"
        )

    if sha256_file(zeros_path) != card["raster_sha256"] or dl["sha256"] != card["raster_sha256"]:
        raise SystemExit("S3DEP1 zero-outside GeoTIFF SHA-256 mismatch")
    if (
        sha256_file(nan_path) != card["nan_outside_sha256"]
        or dl["nan_sha256"] != card["nan_outside_sha256"]
    ):
        raise SystemExit("S3DEP1 NaN-outside GeoTIFF SHA-256 mismatch")
    if sha256_file(zip_path) != card["zip_sha256"] or dl["zip_sha256"] != card["zip_sha256"]:
        raise SystemExit("S3DEP1 ZIP SHA-256 mismatch")
    with zipfile.ZipFile(zip_path) as zf:
        if zf.namelist() != [zeros_path.name]:
            raise SystemExit("S3DEP1 ZIP entry list invalid")
        if hashlib.sha256(zf.read(zeros_path.name)).hexdigest() != card["raster_sha256"]:
            raise SystemExit("S3DEP1 ZIP inner GeoTIFF hash mismatch")

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
        raise SystemExit("S3DEP1 exact-file format/range validator check failed")

    note_text = note_path.read_text().strip()
    if len(note_text) > 140 or note_text != card["note"] or note_text != dl["note"]:
        raise SystemExit("S3DEP1 note missing, mismatched, or >140 chars")

    pre = json.loads(preflight_path.read_text())
    exp_sub_status = "OK_TO_SUBMIT" if ok_sel else "DO_NOT_SUBMIT"
    if (
        pre.get("artifact", {}).get("sha256") != card["raster_sha256"]
        or pre.get("run_card", {}).get("artifact_sha256_matches") is not True
        or pre.get("run_card", {}).get("artifact_name_matches") is not True
        or pre.get("decision", {}).get("submission_status") != exp_sub_status
        or pre.get("decision", {}).get("ready_to_submit") is not ok_sel
    ):
        raise SystemExit("S3DEP1 preflight receipt failed closed check")

    summary = {
        "verified": True,
        "lane_id": card["lane_id"],
        "submission_name": card["submission_name"],
        "raster_sha256": card["raster_sha256"],
        "holdout_dti": card["holdout"]["dti"],
        "selector_decision": fresh_sel["decision"],
        "ok_to_submit": ok_sel,
        "verdict": card["verdict"],
    }
    print(json.dumps(summary, indent=2))
    return summary


def ensure_stack61(
    fp: np.ndarray, transform: rasterio.Affine
) -> tuple[np.ndarray, list[str], dict[str, Any]]:
    """Build or load the 61-channel 1m-LiDAR-free S3DEP1 memmap."""
    prep_meta = json.loads((ROOT / "data/prepared/features.json").read_text())
    prep_path = ROOT / "data/prepared/features.npy"
    if sha256_file(prep_path) != prep_meta["sha256"]:
        raise SystemExit("Prepared 30-channel feature-stack SHA-256 mismatch")
    base_names: list[str] = list(prep_meta["names"])
    base_mm = np.load(prep_path, mmap_mode="r")

    gvc_memmap = ROOT / "data/prepared/gvc1_features.npy"
    if not gvc_memmap.exists():
        _, gvc_names = gvc.build_gvc1_features(ROOT, base_mm, base_names, fp, transform, gvc_memmap)
    gvc_mm = np.load(gvc_memmap, mmap_mode="r")
    gvc_names = list(gvc.GVC1_FEATURE_NAMES)

    sahg_mm, sahg_names = dprf1.build_sahg4_memmap(
        ROOT, base_mm, base_names, fp, ROOT / "data/prepared/sahg4_features.npy"
    )
    stack_mm, names61, stack_meta = s3dep1.build_s3dep1_memmap(
        ROOT, base_mm, base_names, gvc_mm, gvc_names, sahg_mm, sahg_names, fp, STACK61_PATH
    )
    del base_mm, gvc_mm, sahg_mm
    gc.collect()
    return stack_mm, names61, stack_meta


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-recorded", action="store_true")
    parser.add_argument("--stage", choices=("0", "1", "2", "3", "all"), default="all")
    args = parser.parse_args()
    if args.verify_recorded:
        verify_recorded()
        return
    if RUN_CARD_JSON.exists():
        raise SystemExit(
            f"{RUN_CARD_JSON} already exists; refusing implicit rerun of frozen lane {LANE_ID}. "
            "Use --verify-recorded."
        )

    t0 = time.monotonic()
    fp = footprint.load_footprint()
    fp_ids = np.flatnonzero(fp.ravel())
    template = ROOT / "data/bridge/sample_submission.tif"
    with rasterio.open(template) as ds_t:
        transform = ds_t.transform
        tmpl_crs = str(ds_t.crs)
        tmpl_shape = ds_t.shape
    with rasterio.open(ROOT / "data/bridge/labels.tif") as ds_l:
        catalogue = (ds_l.read(1) > 0) & fp

    print(
        f"[1/8] Loading/building {LANE_ID} 61-channel 1m-LiDAR-free seamless memmap...",
        flush=True,
    )
    stack_mm, names61, stack_meta = ensure_stack61(fp, transform)
    print(
        f"      Stack ready: shape={stack_mm.shape}, sha256={stack_meta['sha256'][:12]}, "
        f"RSS={peak_rss_mib():.1f} MiB",
        flush=True,
    )

    context = holdout.SegmentHoldout(fp, catalogue, buffer_px=15)

    # ---- STAGE 0: Two-polarity single-feature leakage canary ----
    if args.stage in ("0", "all"):
        print(
            "[2/8] Running two-polarity single-feature leakage canary over all 61 channels...",
            flush=True,
        )
        canary = run_batched_canary(context, fp, stack_mm, names61)
        print(
            f"      Canary passed={canary['passed']} (n={canary['n_features_checked']}, "
            f"worst={canary['worst_feature']} extremity={canary['worst_polarity_extremity']:.4f}, "
            f"RSS={peak_rss_mib():.1f} MiB)",
            flush=True,
        )
        if not canary["passed"]:
            raise SystemExit("HALT: Single-feature leakage canary exceeded 0.90 threshold!")
        WORK_DIR.mkdir(parents=True, exist_ok=True)
        save_json(
            {
                "stage0_elapsed": round(time.monotonic() - t0, 2),
                "stage0_peak_rss_mib": round(peak_rss_mib(), 1),
                "stack_meta": stack_meta,
                "canary": canary,
            },
            STAGE0_JSON,
        )
        if args.stage == "0":
            return
    else:
        if not STAGE0_JSON.exists():
            raise SystemExit("Run --stage 0 before later stages")
        s0 = json.loads(STAGE0_JSON.read_text())
        canary = s0["canary"]

    conf_prov = confounds.build_all(force=False)
    with np.load(confounds.CONF / "confounds.npz") as c_npz:
        cdict = confounds.classifier_features(c_npz)
        nuis_keys = ["road_m", "claim_m", "block_1", "block_2", "block_3", "block_4"]
        nuisance_fp = np.column_stack(
            [cdict[k].ravel()[fp_ids].astype(np.float32, copy=False) for k in nuis_keys]
        )
    del cdict
    gc.collect()

    # ---- STAGE 1: SegmentHoldout (60,988 withheld) across 3 Preregistered Arms + Paired Baselines ----
    if args.stage in ("1", "all"):
        s0_t = (
            float(json.loads(STAGE0_JSON.read_text())["stage0_elapsed"])
            if STAGE0_JSON.exists()
            else 0.0
        )
        t_s1 = time.monotonic()
        print(
            "[3/8] Partition 1 (SegmentHoldout, 60,988 withheld): "
            "Arm 1 (Core d3+d9) vs Arm 2 (300m Kernel Reg) vs Arm 3 (Log-Odds Hybrid Primary)...",
            flush=True,
        )
        total_offcat = int((fp & (~catalogue)).sum())
        preds_arm1: list[np.ndarray] = []
        preds_arm2: list[np.ndarray] = []
        preds_arm3: list[np.ndarray] = []
        oof_quad_sharp = np.zeros(fp.shape, dtype=np.float32)
        oof_quad_cond = np.zeros(fp.shape, dtype=np.float32)
        fold_meta: list[dict[str, Any]] = []

        for fold in context.folds:
            tf0 = time.monotonic()
            fid = int(fold["id"])
            fname = str(fold["name"])
            f_offcat = int((fold["valid"] & (~fold["visible"])).sum())
            k_fold = int(round(FULL_DOT_BUDGET * f_offcat / total_offcat))

            surfs, m_fold = s3dep1.fit_and_predict_s3dep1_fold(
                stack_mm,
                nuisance_fp,
                names61,
                fp,
                fp_ids,
                train_mask=fold["train"],
                visible_mask=fold["visible"],
                predict_mask=fold["valid"],
                seed=SEED + 10 * fid,
                return_all_arms=True,
            )
            oof_quad_sharp += surfs["arm3_sharp"]
            oof_quad_cond += surfs["arm3_conduit"]

            for arm_key, dest_list in (
                ("arm1", preds_arm1),
                ("arm2", preds_arm2),
                ("arm3", preds_arm3),
            ):
                p_s = dprf1.debiased_apron_surface(
                    surfs[f"{arm_key}_sharp"], fold["valid"], fold["visible"]
                )
                p_c = dprf1.debiased_apron_surface(
                    surfs[f"{arm_key}_conduit"], fold["valid"], fold["visible"]
                )
                d_alloc = dprf1.two_regime_submodular_allocate(
                    p_s,
                    p_c,
                    fold["valid"],
                    fold["visible"],
                    budget=k_fold,
                    primary_share=PRIMARY_SHARE,
                    min_spacing_px=MIN_SPACING_PX,
                    catalogue_clearance_px=CATALOGUE_CLEARANCE_PX,
                )
                dest_list.append((d_alloc > 0.5).astype(np.uint8))
                del p_s, p_c, d_alloc
            del surfs
            gc.collect()

            r1, _ = context.score_fold(preds_arm1[-1], fold)
            r2, _ = context.score_fold(preds_arm2[-1], fold)
            r3, _ = context.score_fold(preds_arm3[-1], fold)
            print(
                f"      Fold {fname:18s} | k={k_fold:,} | Arm1(Core)={r1['dti']:.5f} | "
                f"Arm2(Kern300)={r2['dti']:.5f} | Arm3(Hybrid)={r3['dti']:.5f} "
                f"({time.monotonic() - tf0:.1f}s, RSS={peak_rss_mib():.1f} MiB)",
                flush=True,
            )
            fold_meta.append({"fold": fname, "k_fold_budget": k_fold, "s3dep1": m_fold})

        print(
            "      Running exact paired controls (DPRF1 replay + oof_multiphysics_hgb_d3)...",
            flush=True,
        )
        preds_dprf1 = build_dprf1_replay_preds(context, nuisance_fp, fp, catalogue)
        prep_meta = json.loads((ROOT / "data/prepared/features.json").read_text())
        base_mm_tmp = np.load(ROOT / "data/prepared/features.npy", mmap_mode="r")
        preds_oof_d3 = build_oof_multiphysics_hgb_d3(
            context, base_mm_tmp, list(prep_meta["names"]), int(prep_meta["base_count"]), fp
        )
        del base_mm_tmp
        gc.collect()

        sum_arm1 = context.summarize(preds_arm1, ci_draws=1999)
        sum_arm2 = context.summarize(preds_arm2, ci_draws=1999)
        sum_arm3 = context.summarize(preds_arm3, ci_draws=1999)
        sum_dprf1 = context.summarize(preds_dprf1, ci_draws=1999)
        sum_oof_d3 = context.summarize(preds_oof_d3, ci_draws=1999)

        paired = {
            "arm3_vs_dprf1_replay": context.compare_paired(
                preds_arm3, preds_dprf1, ci_draws=1999, seed=GVC_BASE_SEED
            ),
            "arm3_vs_oof_multiphysics_hgb_d3": context.compare_paired(
                preds_arm3, preds_oof_d3, ci_draws=1999, seed=GVC_BASE_SEED
            ),
            "arm3_vs_arm1_core_dualneg": context.compare_paired(
                preds_arm3, preds_arm1, ci_draws=1999, seed=GVC_BASE_SEED
            ),
            "arm3_vs_arm2_kernel300_reg": context.compare_paired(
                preds_arm3, preds_arm2, ci_draws=1999, seed=GVC_BASE_SEED
            ),
        }
        print(
            f"      POOLED HOLDOUT-DTI | Arm3(S3DEP1 Hybrid)={sum_arm3['dti']:.5f} {sum_arm3['ci95']['interval']} | "
            f"Arm1(Core)={sum_arm1['dti']:.5f} | Arm2(Kern300)={sum_arm2['dti']:.5f} | "
            f"DPRF1(replay)={sum_dprf1['dti']:.5f} | OOF-d3={sum_oof_d3['dti']:.5f}",
            flush=True,
        )
        del preds_arm1, preds_arm2, preds_arm3, preds_dprf1, preds_oof_d3
        gc.collect()

        oof_canary = context.canary(
            {"s3dep1_quad_oof_hybrid": oof_quad_sharp}, seed=GVC_BASE_SEED, max_per_class=15000
        )
        if not oof_canary["passed"]:
            raise SystemExit("HALT: Quadrant OOF surface flagged leakage canary")

        stage1_elapsed = round(s0_t + (time.monotonic() - t_s1), 2)
        stage1_rss = round(peak_rss_mib(), 1)
        WORK_DIR.mkdir(parents=True, exist_ok=True)
        np.savez(
            STAGE1_ARRAYS,
            oof_quad_sharp=oof_quad_sharp,
            oof_quad_cond=oof_quad_cond,
        )
        save_json(
            {
                "stage1_elapsed": stage1_elapsed,
                "stage1_peak_rss_mib": stage1_rss,
                "oof_canary": oof_canary,
                "fold_meta": fold_meta,
                "sum_arm1": sum_arm1,
                "sum_arm2": sum_arm2,
                "sum_arm3": sum_arm3,
                "sum_dprf1": sum_dprf1,
                "sum_oof_d3": sum_oof_d3,
                "paired": paired,
            },
            STAGE1_JSON,
        )
        if args.stage == "1":
            print(f"Stage 1 checkpoint saved in {stage1_elapsed:.1f}s -> {STAGE1_JSON}", flush=True)
            return
    else:
        if not STAGE1_JSON.exists() or not STAGE1_ARRAYS.exists():
            raise SystemExit("Run --stage 1 before later stages")
        s1 = json.loads(STAGE1_JSON.read_text())
        stage1_elapsed = float(s1["stage1_elapsed"])
        stage1_rss = float(s1["stage1_peak_rss_mib"])
        oof_canary = s1["oof_canary"]
        fold_meta = s1["fold_meta"]
        sum_arm1 = s1["sum_arm1"]
        sum_arm2 = s1["sum_arm2"]
        sum_arm3 = s1["sum_arm3"]
        sum_dprf1 = s1["sum_dprf1"]
        sum_oof_d3 = s1["sum_oof_d3"]
        paired = s1["paired"]
        with np.load(STAGE1_ARRAYS) as z1:
            oof_quad_sharp = z1["oof_quad_sharp"].astype(np.float32)
            oof_quad_cond = z1["oof_quad_cond"].astype(np.float32)

    # ---- STAGE 2: 3.0 km Bridge Protocol + Rotated-45° OOF Partition ----
    if args.stage in ("2", "all"):
        t_s2 = time.monotonic()
        print(
            "[4/8] Evaluating 3.0 km Bridge Protocol + Partition 2 (Rotated45 OOF) for deployment...",
            flush=True,
        )
        bridge_3km = evaluate_bridge_3km(stack_mm, nuisance_fp, names61, fp, catalogue)
        print(
            f"      3.0 km Bridge HOLDOUT-DTI={bridge_3km['dti']:.5f} "
            f"(vs DPRF1 bridge {bridge_3km['recorded_dprf1_bridge_dti']:.5f})",
            flush=True,
        )

        rot45_folds = dprf1.make_rotated45_segment_folds(fp, catalogue, buffer_px=15)
        oof_rot_sharp = np.zeros(fp.shape, dtype=np.float32)
        oof_rot_cond = np.zeros(fp.shape, dtype=np.float32)
        for rfold in rot45_folds:
            rfid = int(rfold["id"])
            rsurfs, _ = s3dep1.fit_and_predict_s3dep1_fold(
                stack_mm,
                nuisance_fp,
                names61,
                fp,
                fp_ids,
                train_mask=rfold["train"],
                visible_mask=rfold["visible"],
                predict_mask=rfold["valid"],
                seed=SEED + 500 + 17 * rfid,
                return_all_arms=False,
            )
            oof_rot_sharp += rsurfs["arm3_sharp"]
            oof_rot_cond += rsurfs["arm3_conduit"]
            del rsurfs
            gc.collect()

        stitched_sharp_raw = (0.50 * oof_quad_sharp + 0.50 * oof_rot_sharp).astype(np.float32)
        stitched_cond_raw = (0.50 * oof_quad_cond + 0.50 * oof_rot_cond).astype(np.float32)
        del oof_quad_sharp, oof_quad_cond, oof_rot_sharp, oof_rot_cond
        gc.collect()

        stage2_elapsed = round(stage1_elapsed + (time.monotonic() - t_s2), 2)
        stage2_rss = max(stage1_rss, round(peak_rss_mib(), 1))
        np.savez(
            STAGE2_ARRAYS,
            stitched_sharp_raw=stitched_sharp_raw,
            stitched_cond_raw=stitched_cond_raw,
        )
        save_json(
            {
                "stage2_elapsed": stage2_elapsed,
                "stage2_peak_rss_mib": stage2_rss,
                "bridge_3km": bridge_3km,
            },
            STAGE2_JSON,
        )
        if args.stage == "2":
            print(f"Stage 2 checkpoint saved in {stage2_elapsed:.1f}s -> {STAGE2_JSON}", flush=True)
            return
    else:
        if not STAGE2_JSON.exists() or not STAGE2_ARRAYS.exists():
            raise SystemExit("Run --stage 2 before --stage 3")
        s2 = json.loads(STAGE2_JSON.read_text())
        stage2_elapsed = float(s2["stage2_elapsed"])
        stage2_rss = max(stage1_rss, float(s2["stage2_peak_rss_mib"]))
        bridge_3km = s2["bridge_3km"]
        del oof_quad_sharp, oof_quad_cond
        gc.collect()
        with np.load(STAGE2_ARRAYS) as z2:
            stitched_sharp_raw = z2["stitched_sharp_raw"].astype(np.float32)
            stitched_cond_raw = z2["stitched_cond_raw"].astype(np.float32)

    # ---- STAGE 3: Novelty Audit + GeoTIFF/ZIP Emission + Exact-File C2ST + Selector v2 ----
    t_s3 = time.monotonic()
    del stack_mm, nuisance_fp
    gc.collect()

    stitched_sharp = dprf1.debiased_apron_surface(stitched_sharp_raw, fp, catalogue)
    stitched_cond = dprf1.debiased_apron_surface(stitched_cond_raw, fp, catalogue)
    pre_placement_surface = s3dep1.ranking_surface_for_novelty(
        stitched_sharp,
        stitched_cond,
        fp,
        catalogue,
        primary_share=PRIMARY_SHARE,
        catalogue_clearance_px=CATALOGUE_CLEARANCE_PX,
    )

    print(
        "[5/8] Pre-placement novelty audit (surface) vs pinned registry + all local lanes + peers...",
        flush=True,
    )
    priority_reg = json.loads((ROOT / "registry/priority_rasters.json").read_text())
    existing_shas = {e["footprint_sha256"] for e in priority_reg["unique_rasters"]}
    extra_locals = local_lane_entries(fp, existing_shas)
    pre_nov_methods = novelty.compare_prospective_registry(
        pre_placement_surface,
        fp,
        priority_reg["unique_rasters"],
        ROOT,
        sample_size=200_000,
        extra_entries=extra_locals,
    )
    pre_nov_peers = check_peer_blobs(pre_placement_surface, None, fp)
    print(
        f"      Surface: method_passed={pre_nov_methods['method_lane_passed']} "
        f"(max |rho|={pre_nov_methods['method_lane_max_abs_rank_correlation']}), "
        f"peers checked={pre_nov_peers['peer_unique_blobs_checked']} passed={pre_nov_peers['passed']} "
        f"(max |rho|={pre_nov_peers['max_abs_surface_spearman']:.4f})",
        flush=True,
    )

    print(
        "[6/8] Final 37,654-dot Two-Regime 300 m Submodular allocation + final-dot novelty audit...",
        flush=True,
    )
    final_dots = dprf1.two_regime_submodular_allocate(
        stitched_sharp,
        stitched_cond,
        fp,
        catalogue,
        budget=FULL_DOT_BUDGET,
        primary_share=PRIMARY_SHARE,
        min_spacing_px=MIN_SPACING_PX,
        catalogue_clearance_px=CATALOGUE_CLEARANCE_PX,
    )
    dots_undebiased_diag = dprf1.two_regime_submodular_allocate(
        stitched_sharp_raw,
        stitched_cond_raw,
        fp,
        catalogue,
        budget=FULL_DOT_BUDGET,
        primary_share=PRIMARY_SHARE,
        min_spacing_px=MIN_SPACING_PX,
        catalogue_clearance_px=CATALOGUE_CLEARANCE_PX,
    )
    dist_profile = compute_distance_profile(final_dots > 0.5, catalogue, fp)
    dist_profile_undebiased = compute_distance_profile(dots_undebiased_diag > 0.5, catalogue, fp)
    del dots_undebiased_diag, stitched_sharp_raw, stitched_cond_raw
    gc.collect()

    final_nov_methods = novelty.compare_prospective_registry(
        pre_placement_surface,
        fp,
        priority_reg["unique_rasters"],
        ROOT,
        dots=final_dots > 0.5,
        sample_size=200_000,
        extra_entries=extra_locals,
    )
    final_nov_peers = check_peer_blobs(pre_placement_surface, final_dots, fp)
    nine_site_refresh = check_nine_site_20261026_refresh(pre_placement_surface, final_dots, fp)

    comp_nov_ok = bool(
        pre_nov_methods["method_lane_passed"]
        and pre_nov_peers["passed"]
        and final_nov_methods["method_lane_passed"]
        and final_nov_peers["passed"]
        and bool(nine_site_refresh["passed"])
    )
    dprf1_overlap = None
    dkrn1_overlap = None
    trsg1_overlap = None
    b2_overlap = None
    for row in final_nov_methods["rows"]:
        fstr = str(row.get("file", ""))
        if "dprf1-stitched-oof" in fstr:
            dprf1_overlap = row.get("candidate_dot_overlap_within_3px")
        if "dkrn1-" in fstr:
            dkrn1_overlap = row.get("candidate_dot_overlap_within_3px")
        if "trsg1-" in fstr:
            trsg1_overlap = row.get("candidate_dot_overlap_within_3px")
        if "h33-h33-2-b2" in fstr:
            b2_overlap = row.get("candidate_dot_overlap_within_3px")
    print(
        f"      Final dots ({dist_profile['n_dots']:,}): competing={final_nov_methods['competing_method_rasters_count']} "
        f"passed={final_nov_methods['method_lane_passed']} max_overlap={final_nov_methods['method_lane_max_dot_overlap']} "
        f"(vs DPRF1={dprf1_overlap}, vs DKRN1={dkrn1_overlap}, vs TRSG1={trsg1_overlap}, vs B2={b2_overlap}); "
        f"peers passed={final_nov_peers['passed']} max_ov={final_nov_peers['max_dot_overlap_within_3px']}; "
        f"9-site-20261026 ({nine_site_refresh['checked']}) passed={nine_site_refresh['passed']} "
        f"max_ov={nine_site_refresh['max_dot_overlap_within_3px']}",
        flush=True,
    )

    print("[7/8] Writing GeoTIFF pair + ZIP + preview PNG + exact-file C2ST audit...", flush=True)
    p_vs_dprf1 = paired["arm3_vs_dprf1_replay"]
    p_vs_oof = paired["arm3_vs_oof_multiphysics_hgb_d3"]
    beats_point_best = bool(sum_arm3["dti"] > RECORDED_DPRF1_DTI)
    paired_dprf1_ci = list(p_vs_dprf1["paired_delta_ci95"])
    paired_oof_ci = list(p_vs_oof["paired_delta_ci95"])
    beats_dprf1_ci = bool(paired_dprf1_ci[0] > 0.0)
    beats_oof_ci = bool(paired_oof_ci[0] > 0.0)

    slug = (
        "s3dep1-10m-monoclinal-crustal-oof"
        if (comp_nov_ok and beats_point_best and beats_dprf1_ci)
        else "s3dep1-negative-10m-monoclinal"
    )
    content_id = submission.scored_content_id(final_dots, fp, catalogue)
    downloads = ROOT / "docs/downloads"
    zeros_name = submission.make_filename("gems24", slug, "20261026", content_id, "zeros")
    nan_name = submission.make_filename("gems24", slug, "20261026", content_id, "nan")
    zeros_path = submission.write_submission(
        final_dots.astype(np.float32), template, downloads / zeros_name, outside="zero"
    )
    nan_path = submission.write_submission(
        final_dots.astype(np.float32), template, downloads / nan_name, outside="nan"
    )
    zip_name = zeros_name.replace(".tif", ".zip")
    zip_path = submission.zip_single(zeros_path, downloads / zip_name)
    write_preview(final_dots > 0.5, fp, PREVIEW_PNG)

    zero_raw_checks = submission.check_variants(zeros_path, template)
    nan_raw_checks = submission.check_variants(nan_path, template)
    if (
        not zero_raw_checks["format_valid"]
        or not nan_raw_checks["format_valid"]
        or not strict_whole_array_ok(zero_raw_checks)
    ):
        raise SystemExit("Exact-file format/strict-range validator failed")

    checks_file = f"checks-{zeros_name[:-4]}.json"
    checks_payload = {
        "zero_outside": zero_raw_checks,
        "nan_outside": nan_raw_checks,
        "zeros_zip": zip_name,
        "zeros_zip_sha256": sha256_file(zip_path),
    }
    save_json(checks_payload, downloads / checks_file)

    c2st_report = run_exact_file_c2st(zeros_path, catalogue, fp)
    print(
        f"      C2ST: labels_auc={c2st_report['labels_first']['observed_auc']:.4f}, "
        f"cand_auc={c2st_report['candidate']['observed_auc']:.4f} "
        f"(holm_p={c2st_report['candidate']['holm_p_value']:.4f}, passed={c2st_report['candidate']['strict_gate_passed']})",
        flush=True,
    )

    comp_rows_sorted = sorted(
        [
            r
            for r in final_nov_methods["rows"]
            if r.get("comparator_class") != "space_filling_calibration_control"
        ],
        key=lambda r: float(r.get("candidate_dot_overlap_within_3px") or 0.0),
        reverse=True,
    )
    literal_dup_rows = [
        {
            "registry_id": r["registry_id"],
            "file": r["file"],
            "comparator_class": r.get("comparator_class"),
            "candidate_dot_overlap_within_3px": r.get("candidate_dot_overlap_within_3px"),
        }
        for r in final_nov_methods["rows"]
        if (r.get("candidate_dot_overlap_within_3px") or 0.0) > 0.70
    ]

    technical_gates = {
        "g1_format_strict_0_1": True,
        "g2_leakage_canary": bool(canary["passed"] and oof_canary["passed"]),
        "g3_beats_recorded_dprf1_point": beats_point_best,
        "g3_paired_ci95_positive_vs_dprf1_replay": beats_dprf1_ci,
        "g3_paired_ci95_positive_vs_oof_d3": beats_oof_ci,
        "g4_prospective_method_and_peer_novelty": comp_nov_ok,
        "g4_literal_all_entries_including_s5_lattice": bool(
            final_nov_methods["literal_all_entries_passed"]
        ),
        "g5_exact_file_c2st": bool(c2st_report["candidate"]["strict_gate_passed"]),
    }
    all_scientific_passed = bool(
        technical_gates["g1_format_strict_0_1"]
        and technical_gates["g2_leakage_canary"]
        and technical_gates["g3_beats_recorded_dprf1_point"]
        and technical_gates["g3_paired_ci95_positive_vs_dprf1_replay"]
        and technical_gates["g3_paired_ci95_positive_vs_oof_d3"]
        and technical_gates["g4_prospective_method_and_peer_novelty"]
        and technical_gates["g5_exact_file_c2st"]
    )
    elapsed = round(stage2_elapsed + (time.monotonic() - t_s3), 2)
    final_rss = max(stage2_rss, round(peak_rss_mib(), 1))

    # Build provisional run_card, run independent selector.verify_selector, and align status fail-closed
    note = (
        f"GEMS24 S3DEP1 | 10m 3DEP+crustal OOF 37654d | id {content_id} | "
        f"HOLDOUT-DTI {sum_arm3['dti']:.4f} | research; DO NOT SUBMIT"
    )
    if len(note) > 140:
        raise RuntimeError(f"Note exceeded 140 chars: {len(note)}")
    note_file = f"note-{zeros_name[:-4]}.txt"
    (downloads / note_file).write_text(note + "\n")

    run_card: dict[str, Any] = {
        "schema_version": 2,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "lane_id": LANE_ID,
        "assigned_lane_status": (
            "preregistered_10m_3dep_monoclinal_crustal_lane; "
            "assigned single-method paragraph absent in standing prompt"
        ),
        "preregistration": PREREG_PATH,
        "preregistration_commit": PREREG_COMMIT,
        "experiments_run": 3,
        "experiment_budget_limit": 3,
        "elapsed_seconds": elapsed,
        "peak_rss_mib": final_rss,
        "external_official_sources": [
            {
                "name": "USGS 3DEP 1/3 arc-second (~10 m) Seamless DEM (12 1x1 deg tiles n38w118..n41w120)",
                "catalog_url": "https://www.sciencebase.gov/catalog/item/4f70aa9fe4b058caae3f8de5",
                "immutable_archive_ref": "buffedlizard55-lab/GEMSDOE10@91d6566ecc86141eca9e81c259057678930e596f",
                "manifest_sha256": stack_meta["inputs"]["data/dem10/manifest.json"],
                "footprint_finite_coverage": 1.0,
            }
        ],
        "hypothesis": (
            "61-channel 100% 1m-LiDAR-free Seamless 10 m USGS 3DEP Monoclinal Step-Asymmetry x "
            "19-band Crustal Strain/Seismic x GDR #1391 Hydrothermal Conduit Dual-Objective OOF "
            "Detector: unidirectional 30-50 m monoclinal step index (dem10_onesided3 * log1p(hgm50_max) "
            "* steep_ratio) and 900 m 8-azimuth monoclinal lineament coherence resolve degraded "
            "Pleistocene piedmont scarps and all 1,641,254 cells of the 31.8% 1 m LiDAR gap without "
            "1 m LiDAR parent-convergence, fused via log-odds geometric blending of a dual-negative "
            "(d3+d9) core classifier and a 300 m triangular-kernel soft-label regressor with "
            "unconditional nuisance logit debiasing and Two-Regime 300 m submodular coverage."
        ),
        "mechanism": (
            "Monoclinal normal and transtensional fault scarps create monotonic 30 m elevation steps "
            "(dem10_onesided3 -> 1) laterally coherent over >=900 m above basin-margin gravity slopes "
            "(iso_grav_anom_slope) and active GPS/microseismic strain zones (geod_2ndinv, deq_n100a15), "
            "whereas symmetric desert washes, gullies, and highway borrow ditches reverse slope within "
            "30 m (dem10_onesided -> 0, curv_absmax high). Withholding all 15 1 m LiDAR channels "
            "eliminates the 68.2% block-seam and breaks >75% 3-px dot convergence onto DPRF1."
        ),
        "named_non_fault_mimic": (
            "Pleistocene Lake Lahontan / Bonneville pluvial wave-cut shoreline benches (unidirectional "
            "10-30 m steps along equipotential contours), resistant Tertiary welded ash-flow tuff "
            "hogback dip-slopes, and highway cut-and-fill embankments along valley corridors."
        ),
        "holdout": sum_arm3,
        "bridge_protocol_holdout": bridge_3km,
        "arms_same_evaluator": {
            "arm1_s3dep1_core_dualneg_61ch": {
                "dti": sum_arm1["dti"],
                "ci95": sum_arm1["ci95"]["interval"],
            },
            "arm2_s3dep1_kernel300_reg_61ch": {
                "dti": sum_arm2["dti"],
                "ci95": sum_arm2["ci95"]["interval"],
            },
            "arm3_s3dep1_hybrid_primary_61ch": {
                "dti": sum_arm3["dti"],
                "ci95": sum_arm3["ci95"]["interval"],
            },
            "control_dprf1_52ch_replay": {
                "dti": sum_dprf1["dti"],
                "ci95": sum_dprf1["ci95"]["interval"],
                "recorded_best_dti": RECORDED_DPRF1_DTI,
            },
            "control_oof_multiphysics_hgb_d3": {
                "dti": sum_oof_d3["dti"],
                "ci95": sum_oof_d3["ci95"]["interval"],
            },
        },
        "paired_vs_dprf1_replay": p_vs_dprf1,
        "paired_vs_oof_multiphysics_hgb_d3": p_vs_oof,
        "paired_vs_arm1_core": paired["arm3_vs_arm1_core_dualneg"],
        "paired_vs_arm2_kernel300": paired["arm3_vs_arm2_kernel300_reg"],
        "baseline_reproduced": abs(float(sum_oof_d3["dti"]) - 0.129996798011798) < 1e-9,
        "paired_vs_baseline": {
            "baseline_name": "oof_multiphysics_hgb_d3",
            "evaluator_version": holdout.SEGMENT_EVALUATOR_VERSION,
            "n_withheld_positive_pixels": 60988,
            "baseline_dti": float(sum_oof_d3["dti"]),
            "delta_dti": float(p_vs_oof["paired_delta_dti"]),
            "ci95": paired_oof_ci,
        },
        "paired_vs_current_best": {
            "baseline_name": "H24-DPRF1",
            "evaluator_version": holdout.SEGMENT_EVALUATOR_VERSION,
            "n_withheld_positive_pixels": 60988,
            "baseline_replayed": abs(float(sum_dprf1["dti"]) - RECORDED_DPRF1_DTI) < 1e-12,
            "baseline_dti": float(sum_dprf1["dti"]),
            "delta_dti": float(p_vs_dprf1["paired_delta_dti"]),
            "ci95": paired_dprf1_ci,
        },
        "leakage_canary": {
            "passed": bool(canary["passed"] and oof_canary["passed"]),
            "n_features_checked": canary["n_features_checked"],
            "worst_feature": canary["worst_feature"],
            "worst_pooled_auc": canary["worst_pooled_auc"],
            "worst_polarity_extremity": canary["worst_polarity_extremity"],
            "quad_oof_hybrid_auc": oof_canary["features"]["s3dep1_quad_oof_hybrid"]["pooled_auc"],
        },
        "leakage_canary_summary": {
            "passed": bool(canary["passed"] and oof_canary["passed"]),
            "n_features_checked": canary["n_features_checked"],
            "worst_feature": canary["worst_feature"],
            "worst_pooled_auc": canary["worst_pooled_auc"],
            "worst_polarity_extremity": canary["worst_polarity_extremity"],
            "quad_oof_hybrid_auc": oof_canary["features"]["s3dep1_quad_oof_hybrid"]["pooled_auc"],
        },
        "correlation_overlap_vs_registry": {
            "pre_placement_surface_max_abs_spearman": pre_nov_methods[
                "method_lane_max_abs_rank_correlation"
            ],
            "final_dots_max_abs_spearman": final_nov_methods[
                "method_lane_max_abs_rank_correlation"
            ],
            "competing_method_max_3px_dot_overlap": final_nov_methods[
                "method_lane_max_dot_overlap"
            ],
            "competing_method_passed": bool(final_nov_methods["method_lane_passed"]),
            "dot_overlap_within_3px_vs_dprf1": dprf1_overlap,
            "dot_overlap_within_3px_vs_dkrn1": dkrn1_overlap,
            "dot_overlap_within_3px_vs_trsg1": trsg1_overlap,
            "dot_overlap_within_3px_vs_gemsdoe32_b2": b2_overlap,
            "peer_blobs_max_3px_dot_overlap": final_nov_peers["max_dot_overlap_within_3px"],
            "peer_blobs_passed": bool(final_nov_peers["passed"]),
            "nine_site_20261026_max_3px_dot_overlap": nine_site_refresh[
                "max_dot_overlap_within_3px"
            ],
            "nine_site_20261026_passed": bool(nine_site_refresh["passed"]),
            "literal_all_entries_max_3px_dot_overlap": final_nov_methods["max_dot_overlap"],
            "literal_all_entries_passed": bool(final_nov_methods["literal_all_entries_passed"]),
        },
        "novelty_vs_registry": {
            "competing_method_rasters_checked": final_nov_methods["competing_method_rasters_count"],
            "local_lanes_added": [e["id"] for e in extra_locals],
            "peer_blobs_checked": final_nov_peers["peer_unique_blobs_checked"],
            "peer_blobs_missing_from_cache": final_nov_peers["peer_blobs_missing_from_cache"],
            "nine_site_20261026_refresh_checked": nine_site_refresh["checked"],
            "nine_site_20261026_refresh_passed": nine_site_refresh["passed"],
            "nine_site_20261026_refresh_max_dot_overlap": nine_site_refresh[
                "max_dot_overlap_within_3px"
            ],
            "pre_placement_surface_max_abs_rank_correlation": pre_nov_methods[
                "method_lane_max_abs_rank_correlation"
            ],
            "pre_placement_peers_max_abs_rank_correlation": pre_nov_peers[
                "max_abs_surface_spearman"
            ],
            "method_lane_passed": final_nov_methods["method_lane_passed"],
            "method_lane_max_abs_rank_correlation": final_nov_methods[
                "method_lane_max_abs_rank_correlation"
            ],
            "method_lane_max_dot_overlap": final_nov_methods["method_lane_max_dot_overlap"],
            "dot_overlap_within_3px_vs_dprf1": dprf1_overlap,
            "dot_overlap_within_3px_vs_dkrn1": dkrn1_overlap,
            "dot_overlap_within_3px_vs_trsg1": trsg1_overlap,
            "dot_overlap_within_3px_vs_b2": b2_overlap,
            "peer_blobs_passed": final_nov_peers["passed"],
            "peer_blobs_max_dot_overlap": final_nov_peers["max_dot_overlap_within_3px"],
            "peer_blobs_max_overlap_artifact": final_nov_peers["max_overlap_peer_artifact"],
            "literal_all_entries_passed": final_nov_methods["literal_all_entries_passed"],
            "literal_all_entries_max_dot_overlap": final_nov_methods["max_dot_overlap"],
            "calibration_control_rows": final_nov_methods["calibration_control_rows"],
            "top_5_competing_comparators": comp_rows_sorted[:5],
        },
        "novelty": {
            "surface": {
                "max_abs_rank_correlation": pre_nov_methods["method_lane_max_abs_rank_correlation"],
                "literal_all_entries_passed": bool(pre_nov_methods["literal_all_entries_passed"]),
            },
            "final_dots": {
                "max_abs_rank_correlation": final_nov_methods[
                    "method_lane_max_abs_rank_correlation"
                ],
                "method_lane_max_dot_overlap": final_nov_methods["method_lane_max_dot_overlap"],
                "method_lane_passed": bool(final_nov_methods["method_lane_passed"]),
                "literal_all_entries_passed": bool(final_nov_methods["literal_all_entries_passed"]),
                "literal_duplicate_rows": literal_dup_rows,
            },
            "peers_final": {
                "max_dot_overlap_within_3px": final_nov_peers["max_dot_overlap_within_3px"],
                "passed": bool(final_nov_peers["passed"]),
            },
            "nine_site_20261026_refresh": nine_site_refresh,
        },
        "off_catalogue_distance_profile": dist_profile,
        "off_catalogue_distance_profile_before_apron_debiasing": dist_profile_undebiased,
        "exact_file_nuisance_audit": c2st_report,
        "c2st_exact_file": {
            "labels_audited_first": True,
            "strict_gate_passed": bool(c2st_report["candidate"]["strict_gate_passed"]),
            "observed_auc": c2st_report["candidate"]["observed_auc"],
            "holm_p_value": c2st_report["candidate"]["holm_p_value"],
        },
        "technical_gates": technical_gates,
        "scientific_screen_all_passed": all_scientific_passed,
        "raster_sha256": zero_raw_checks["sha256"],
        "nan_outside_artifact": nan_name,
        "nan_outside_sha256": nan_raw_checks["sha256"],
        "zip_artifact": zip_name,
        "zip_sha256": checks_payload["zeros_zip_sha256"],
        "validator_output": {
            "sha256": zero_raw_checks["sha256"],
            "format_valid": zero_raw_checks["format_valid"],
            "format_acceptable": zero_raw_checks["format_acceptable"],
            "strict_whole_array_values_in_0_1": strict_whole_array_ok(zero_raw_checks),
            "no_nan_in_footprint": zero_raw_checks["checks"]["footprint_all_finite"]["pass"],
            "footprint_range_0_1": zero_raw_checks["checks"]["footprint_range_0_1"]["pass"],
            "crs": tmpl_crs,
            "shape": list(tmpl_shape),
            "positive_pixels": int((final_dots[fp] > 0.5).sum()),
        },
        "submission_name": zeros_name,
        "note": note,
        "note_length": len(note),
        "verdict": "negative",
        "ok_to_download": True,
        "ok_to_submit": False,
        "submission_authorized": False,
        "submission_slots_used": 0,
        "organizer_confirmed_score": None,
        "governance_hold_reasons": [
            "Parallel-Run Protocol Rule 6: promotion to a real weekly slot is a separate selector step",
            "gems-selector-v2-literal-quota-fail-closed: literal registry-039 spacing-5 lattice retained, live DrivenData quota unknown, independent positive replay certificate not implemented",
            "HOLDOUT-DTI is a local hide-and-recover measurement, not a leaderboard score or forecast",
        ],
    }

    print("[8/8] Selector v2 receipt on exact bytes + preflight + records...", flush=True)
    sel_receipt = selector.verify_selector(zeros_path, template, run_card)
    ok_sel = bool(sel_receipt["ok_to_submit"]) and sel_receipt["decision"] == "OK_TO_SUBMIT"
    run_card["ok_to_submit"] = ok_sel
    run_card["submission_authorized"] = ok_sel
    run_card["verdict"] = "promote" if ok_sel else "negative"
    run_card["selector_receipt"] = sel_receipt
    print(
        f"      Selector: {sel_receipt['decision']} | gates={sel_receipt['gates']}",
        flush=True,
    )
    save_json(sel_receipt, SELECTOR_JSON)
    save_json(sel_receipt, DOCS_SELECTOR_JSON)
    save_json(sel_receipt, zeros_path.with_suffix(".selector.json"))
    save_json(run_card, RUN_CARD_JSON)
    save_json(run_card, DOCS_RUN_CARD_JSON)

    preflight_out = downloads / f"{zeros_name[:-4]}.preflight.json"
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/preflight_submission.py"),
            str(zeros_path),
            "--run-card",
            str(RUN_CARD_JSON),
            "--note-file",
            str(downloads / note_file),
            "--output",
            str(preflight_out),
        ],
        cwd=ROOT,
        check=True,
    )

    download_record = {
        "lane_id": LANE_ID,
        "file": zeros_name,
        "sha256": zero_raw_checks["sha256"],
        "nan_file": nan_name,
        "nan_sha256": nan_raw_checks["sha256"],
        "zip_file": zip_name,
        "zip_sha256": checks_payload["zeros_zip_sha256"],
        "checks_file": checks_file,
        "preflight_file": preflight_out.name,
        "selector_file": zeros_path.with_suffix(".selector.json").name,
        "note_file": note_file,
        "note": note,
        "pixel_count": int((final_dots[fp] > 0.5).sum()),
        "holdout_dti": sum_arm3["dti"],
        "holdout_ci95": sum_arm3["ci95"]["interval"],
        "bridge_3km_dti": bridge_3km["dti"],
        "bridge_3km_ci95": bridge_3km["ci95"],
        "arm1_core_dualneg_dti": float(sum_arm1["dti"]),
        "arm2_kernel300_reg_dti": float(sum_arm2["dti"]),
        "control_dprf1_replay_dti": float(sum_dprf1["dti"]),
        "oof_multiphysics_hgb_d3_dti": float(sum_oof_d3["dti"]),
        "recorded_dprf1_dti": RECORDED_DPRF1_DTI,
        "beats_recorded_dprf1_point": beats_point_best,
        "paired_delta_vs_dprf1_replay": float(p_vs_dprf1["paired_delta_dti"]),
        "paired_delta_ci95_vs_dprf1_replay": paired_dprf1_ci,
        "paired_delta_vs_oof_d3": float(p_vs_oof["paired_delta_dti"]),
        "paired_delta_ci95_vs_oof_d3": paired_oof_ci,
        "c2st_auc": c2st_report["candidate"]["observed_auc"],
        "c2st_holm_p": c2st_report["candidate"]["holm_p_value"],
        "competing_method_novelty_passed": comp_nov_ok,
        "competing_method_max_3px_overlap": final_nov_methods["method_lane_max_dot_overlap"],
        "dot_overlap_within_3px_vs_dprf1": dprf1_overlap,
        "dot_overlap_within_3px_vs_dkrn1": dkrn1_overlap,
        "dot_overlap_within_3px_vs_trsg1": trsg1_overlap,
        "dot_overlap_within_3px_vs_b2": b2_overlap,
        "peer_blobs_novelty_passed": final_nov_peers["passed"],
        "peer_blobs_max_3px_overlap": final_nov_peers["max_dot_overlap_within_3px"],
        "nine_site_20261026_refresh_passed": nine_site_refresh["passed"],
        "nine_site_20261026_refresh_max_3px_overlap": nine_site_refresh[
            "max_dot_overlap_within_3px"
        ],
        "apron_2_to_9px_fraction": dist_profile["frac_2_to_9px_apron"],
        "farfield_gt20px_fraction": dist_profile["frac_gt_20px_farfield"],
        "scientific_screen_all_passed": all_scientific_passed,
        "ok_to_download": True,
        "ok_to_submit": ok_sel,
        "submission_authorized": ok_sel,
        "verdict": run_card["verdict"],
        "selector_decision": sel_receipt["decision"],
        "competing_method_rasters_checked": final_nov_methods["competing_method_rasters_count"],
    }
    save_json(download_record, DOCS_DOWNLOAD_JSON)

    experiment_record = {
        "generated_utc": run_card["generated_utc"],
        "lane_id": LANE_ID,
        "preregistration": PREREG_PATH,
        "preregistration_commit": PREREG_COMMIT,
        "elapsed_seconds": elapsed,
        "peak_rss_mib": final_rss,
        "feature_names_61": names61,
        "zero_1m_lidar_channels": True,
        "excluded_1m_lidar_15": sorted(s3dep1.FORBIDDEN_1M_LIDAR_NAMES),
        "selective_residualized_19": sorted(s3dep1.S3DEP1_SELECTIVE_RESID_NAMES),
        "stack_meta": stack_meta,
        "canary": canary,
        "fold_fit_metadata": fold_meta,
        "arms": {
            "arm1_s3dep1_core_dualneg_61ch": {"holdout": sum_arm1},
            "arm2_s3dep1_kernel300_reg_61ch": {"holdout": sum_arm2},
            "arm3_s3dep1_hybrid_primary_61ch": {"holdout": sum_arm3, "bridge_3km": bridge_3km},
            "control_dprf1_52ch_replay": {"holdout": sum_dprf1},
            "control_oof_multiphysics_hgb_d3": {"holdout": sum_oof_d3},
        },
        "paired_comparisons": paired,
        "novelty": {
            "pre_placement_methods": {k: v for k, v in pre_nov_methods.items() if k != "rows"},
            "pre_placement_peers": pre_nov_peers,
            "final_dots_methods": final_nov_methods,
            "final_dots_peers": final_nov_peers,
            "nine_site_20261026_refresh": nine_site_refresh,
        },
        "off_catalogue_distance_profile": dist_profile,
        "off_catalogue_distance_profile_before_apron_debiasing": dist_profile_undebiased,
        "c2st_audit": c2st_report,
        "nuisance_provenance": conf_prov,
        "ok_to_submit": ok_sel,
        "run_card": run_card,
    }
    save_json(experiment_record, EXPERIMENT_JSON)
    print(
        f"Done in {elapsed:.1f}s (peak RSS {final_rss:.1f} MiB). "
        f"S3DEP1 Arm3 HOLDOUT-DTI={sum_arm3['dti']:.5f} (Arm1={sum_arm1['dti']:.5f}, Arm2={sum_arm2['dti']:.5f}) "
        f"vs DPRF1={sum_dprf1['dti']:.5f}, OOF-d3={sum_oof_d3['dti']:.5f}; "
        f"comp_novelty={comp_nov_ok} (vs DPRF1 {dprf1_overlap}, vs DKRN1 {dkrn1_overlap}, vs B2 {b2_overlap}); "
        f"C2ST={c2st_report['candidate']['observed_auc']:.4f} (passed={c2st_report['candidate']['strict_gate_passed']}); "
        f"selector={sel_receipt['decision']}; verdict={run_card['verdict']}.",
        flush=True,
    )


if __name__ == "__main__":
    main()
