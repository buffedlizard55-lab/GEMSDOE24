#!/usr/bin/env python3
"""Execute or verify the preregistered H24-DPRF1 Dual-Partition OOF lane.

Spec locked prior to execution in ``knowledge/19_preregistered_DPRF1_2026-10-26.md``:
- Combines 30 scale-separated prepared base channels + 18 label-free OpenEI GDR
  INGENIOUS hydrothermal/tilt/lineament channels (``gems.gvc``) + 4 modality-aware
  ``SAHG1`` conduit channels (``sahg_g_sat``, ``sahg_r_alt``, ``sahg_b_step``,
  ``sahg_h_conduit``) = 52 channels, keeping ``NaN`` on sensor gaps.
- Runs 52-channel two-polarity single-feature leakage canaries prior to model fit.
- Evaluates 3 locked arms on ``SegmentHoldout`` (``gems-segment-pooled-v1``,
  1.5 km collar, 60,988 withheld positives, 1,999 10 km block-bootstrap draws):
  1. ``Arm 1 (H24-DPRF1)``: Stratified near+far negatives (``d_vis >= 3.0 px``),
     selective 9-channel non-topographic nuisance residualization, relief-conditioned
     LiDAR-gap calibration, 8-azimuth ridge sharpening, and Two-Regime submodular
     300 m allocation (68% primary ridge + 32% concealed hydrothermal conduit).
  2. ``Arm 2 (DPRF1-SingleRegime)``: Same 52-ch model + Single-Regime submodular
     300 m allocation (100% primary ridge).
  3. ``Arm 3 (DPRF1-DeadZone9)``: Legacy ``d_vis >= 9.0 px`` negative dead zone +
     Two-Regime submodular 300 m allocation.
- Evaluates paired 10 km block-bootstrap CIs against ``oof_multiphysics_hgb_d3``
  (0.13000), ``B1: OOF-Base-Submod`` (0.13900), and ``B0: OOF-H24-Ridge`` (0.14179),
  plus 3.0 km ``segment-hide-recover-pooled-v1`` bridge evaluation.
- Exports the full-footprint GeoTIFF strictly from Dual-Partition Stitched-OOF
  (Quadrant OOF + 45-degree Rotated Diamond OOF) + Visible-Catalogue Apron Quantile
  Debiasing so zero pixels are ever predicted in-sample on ``catalogue``.
- Audits pre-placement surface & final dots against all 46 priority registry rasters,
  all 9 local 2026-10-25 method lanes (55 unique registry rasters), and 83 peer blobs,
  and runs the exact-file Lopez-Paz & Oquab C2ST nuisance audit (``gems.c2s2``).
- Never contacts DrivenData and never spends a weekly submission slot.
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import os
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

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import numpy as np  # noqa: E402
import rasterio  # noqa: E402
from scipy.ndimage import binary_erosion, distance_transform_edt  # noqa: E402
from scipy.stats import rankdata  # noqa: E402
from sklearn.ensemble import HistGradientBoostingClassifier  # noqa: E402
from threadpoolctl import threadpool_limits  # noqa: E402

from gems import (  # noqa: E402
    c2s2,
    confounds,
    dprf1,
    emission,
    footprint,
    gvc,
    holdout,
    novelty,
    sahg1,
    selector,
    submission,
)
from gems.validator import sha256_file  # noqa: E402

SEED = 20261026
GVC_BASE_SEED = 20261025
FULL_DOT_BUDGET = 37654
PREREG_PATH = "knowledge/19_preregistered_DPRF1_2026-10-26.md"
PREREG_COMMIT = "0c190e8ef9f4e6e7f1436d56ee0ddbf8a79627ca"

GVC_MEMMAP = ROOT / "data/prepared/gvc1_features.npy"
SAHG4_MEMMAP = ROOT / "data/prepared/sahg4_features.npy"
EXPERIMENT_JSON = ROOT / "evidence/dprf1_experiment_20261026.json"
RUN_CARD_JSON = ROOT / "evidence/dprf1_run_card_20261026.json"
SELECTOR_JSON = ROOT / "evidence/dprf1_selector_20261026.json"
DOCS_RUN_CARD_JSON = ROOT / "docs/data/dprf1_run_card.json"
DOCS_SELECTOR_JSON = ROOT / "docs/data/dprf1_selector.json"
DOCS_DOWNLOAD_JSON = ROOT / "docs/data/dprf1_download.json"
PREVIEW_PNG = ROOT / "docs/assets/dprf1-preview.png"

BASELINE_D3_PARAMS = dict(
    max_iter=80,
    max_leaf_nodes=15,
    learning_rate=0.08,
    l2_regularization=5.0,
    early_stopping=False,
)


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


def run_batched_52ch_canary(
    context: holdout.SegmentHoldout,
    fp: np.ndarray,
    base_mm: np.ndarray,
    base_names: list[str],
    gvc_mm: np.ndarray,
    gvc_names: list[str],
    sahg_mm: np.ndarray,
    sahg_names: list[str],
    *,
    batch_size: int = 4,
) -> dict[str, Any]:
    fp_ids = np.flatnonzero(fp.ravel())
    specs = (
        [(n, "base", i) for i, n in enumerate(base_names)]
        + [(n, "gvc", i) for i, n in enumerate(gvc_names)]
        + [(n, "sahg", i) for i, n in enumerate(sahg_names)]
    )
    merged: dict[str, Any] = {}
    last_meta: dict[str, Any] = {}
    for start in range(0, len(specs), batch_size):
        batch = specs[start : start + batch_size]
        fdict: dict[str, np.ndarray] = {}
        for name, src, col in batch:
            grid = np.full(fp.shape, np.nan, dtype=np.float32)
            if src == "base":
                grid.ravel()[fp_ids] = base_mm[:, col]
            elif src == "gvc":
                grid.ravel()[fp_ids] = gvc_mm[:, col]
            else:
                grid.ravel()[fp_ids] = sahg_mm[:, col]
            fdict[name] = grid
        rep = context.canary(fdict, seed=GVC_BASE_SEED, max_per_class=15000)
        merged.update(rep["features"])
        last_meta = rep
        del fdict
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


def build_oof_multiphysics_hgb_d3(
    context: holdout.SegmentHoldout,
    base_mm: np.ndarray,
    base_names: list[str],
    base_nc: int,
    fp: np.ndarray,
) -> list[np.ndarray]:
    """Reproduce exact oof_multiphysics_hgb_d3 (0.13000) on SegmentHoldout for paired bootstrap."""
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
                emission.priority_poisson(f_surf, elig, budget, min_dist=3).astype(np.float32)
            )
            del f_surf, x_tr, clf
            gc.collect()
    return preds


def evaluate_bridge_3km(
    base_mm: np.ndarray,
    gvc_mm: np.ndarray,
    sahg_mm: np.ndarray,
    nuisance_fp: np.ndarray,
    all_names: list[str],
    fp: np.ndarray,
    catalogue: np.ndarray,
) -> dict[str, Any]:
    """Evaluate Arm 1 (H24-DPRF1) on the 3.0 km / 20 km tile bridge protocol."""
    fp_ids = np.flatnonzero(fp.ravel())
    total_offcat = int((fp & (~catalogue)).sum())
    tile_rows_all = []
    fold_details = []
    for fid, fold in enumerate(holdout.segment_folds(fp, catalogue, buffer_px=30)):
        p_sharp, p_cond, _ = dprf1.fit_and_predict_fold(
            base_mm,
            gvc_mm,
            sahg_mm,
            nuisance_fp,
            all_names,
            fp,
            fp_ids,
            train_mask=fold["training"],
            visible_mask=fold["visible"],
            predict_mask=fold["test"],
            neg_mode="stratified_d3",
            seed=SEED + 300 + 13 * fid,
        )
        f_offcat = int((fold["test"] & (~fold["visible"])).sum())
        k_fold = int(round(FULL_DOT_BUDGET * f_offcat / total_offcat))
        dots = dprf1.two_regime_submodular_allocate(
            p_sharp,
            p_cond,
            fold["test"],
            fold["visible"],
            budget=k_fold,
            primary_share=0.68,
            min_spacing_px=2.8,
            catalogue_clearance_px=2.0,
        )
        t_rows, ref = holdout.spatial_components(
            dots > 0.5, fold["hidden"] & fold["test"], fold["test"], fold["visible"], tile_px=200
        )
        tile_rows_all.append(t_rows)
        fold_details.append({"fold": fold["name"], **ref})
        del p_sharp, p_cond, dots
        gc.collect()

    summed_tiles = np.sum(tile_rows_all, axis=0)
    yy, xx = np.nonzero(fp)
    nx = (fp.shape[1] + 199) // 200
    active_tiles = np.unique((yy // 200) * nx + xx // 200)
    pooled = holdout.pooled_components(fold_details)
    ci95 = holdout.pooled_bootstrap(summed_tiles[active_tiles], resamples=1000, seed=SEED)
    aspc_report = json.loads((ROOT / "evidence/aspc_run_20261025.json").read_text())
    sahg1_card = json.loads((ROOT / "evidence/sahg1_run_card_20261025.json").read_text())
    hcw_card = json.loads((ROOT / "evidence/hcw_run_card_20261025.json").read_text())
    rshg1_card = json.loads((ROOT / "evidence/rshg1_run_card_20261025.json").read_text())
    return {
        "label": "HOLDOUT-DTI",
        "evaluator_version": holdout.SEGMENT_EVALUATOR_VERSION,
        "dti": pooled["dti"],
        "ci95": ci95,
        "n_withheld_positives": int(pooled["n_truth"]),
        "n_emitted": int(pooled["n_emitted"]),
        "buffer_m": 3000,
        "recorded_aspc_dti": float(aspc_report["holdout"]["value"]),
        "recorded_sahg1_bridge_dti": float(sahg1_card["bridge_protocol_holdout"]["dti"]),
        "recorded_fuse_hcw_bridge_dti": float(hcw_card["bridge_protocol_holdout"]["dti"]),
        "recorded_rshg1_bridge_dti": float(rshg1_card["bridge_protocol_holdout"]["dti"]),
        "delta_vs_aspc": float(pooled["dti"] - float(aspc_report["holdout"]["value"])),
        "delta_vs_sahg1_bridge": float(
            pooled["dti"] - float(sahg1_card["bridge_protocol_holdout"]["dti"])
        ),
        "delta_vs_fuse_hcw_bridge": float(
            pooled["dti"] - float(hcw_card["bridge_protocol_holdout"]["dti"])
        ),
        "delta_vs_rshg1_bridge": float(
            pooled["dti"] - float(rshg1_card["bridge_protocol_holdout"]["dti"])
        ),
        "folds": fold_details,
    }


def all_local_20261025_entries(fp: np.ndarray, existing_shas: set[str]) -> list[dict[str, Any]]:
    """Collect all 9 local 2026-10-25 GEMSDOE24 method-lane GeoTIFFs for exhaustive novelty checks."""
    candidates = [
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
    seen = set(existing_shas)
    out: list[dict[str, Any]] = []
    for eid, rel in candidates:
        p = ROOT / rel
        if not p.exists():
            continue
        with rasterio.open(p) as ds:
            a = ds.read(1)
        fp_sha = hashlib.sha256(np.asarray(a[fp], dtype="<f4").tobytes()).hexdigest()
        if fp_sha in seen:
            continue
        seen.add(fp_sha)
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
    """Check all competition-grid blobs in registry/peer_rasters_20261025.json."""
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
    for row in blobs.values():
        p = ROOT / row["cache_path"]
        if not p.exists():
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
        and max_surf_rho <= 0.90
        and (dots is None or (max_dot_rho <= 0.90 and max_overlap <= 0.70))
    )
    return {
        "peer_unique_blobs_checked": checked,
        "max_abs_surface_spearman": max_surf_rho,
        "max_abs_dot_spearman": max_dot_rho if dots is not None else None,
        "max_dot_overlap_within_3px": max_overlap if dots is not None else None,
        "max_overlap_peer_artifact": max_overlap_file,
        "passed": passed,
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
        "h24_dprf1_exact_file",
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
    """Verify frozen DPRF1 receipts, GeoTIFF variants, ZIP, selector, preflight, and <=140-char note."""
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
            raise SystemExit(f"Missing recorded DPRF1 artifact: {p}")
    exp = json.loads(EXPERIMENT_JSON.read_text())
    card = json.loads(RUN_CARD_JSON.read_text())
    docs_card = json.loads(DOCS_RUN_CARD_JSON.read_text())
    saved_sel = json.loads(SELECTOR_JSON.read_text())
    docs_sel = json.loads(DOCS_SELECTOR_JSON.read_text())
    dl = json.loads(DOCS_DOWNLOAD_JSON.read_text())
    if card != docs_card or saved_sel != docs_sel:
        raise SystemExit("Evidence and docs/data DPRF1 run cards or selector receipts disagree")

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
    if (
        saved_sel.get("gates") != fresh_sel.get("gates")
        or saved_sel.get("decision") != fresh_sel.get("decision")
        or json.loads(dl_sel_path.read_text()) != saved_sel
        or card.get("ok_to_submit") is not ok_sel
        or dl.get("ok_to_submit") is not ok_sel
        or (card.get("verdict") == "promote") is not ok_sel
    ):
        raise SystemExit("DPRF1 run card/download disagrees with independent gems.selector receipt")

    if sha256_file(zeros_path) != card["raster_sha256"] or dl["sha256"] != card["raster_sha256"]:
        raise SystemExit("DPRF1 zero-outside GeoTIFF SHA-256 mismatch")
    if (
        sha256_file(nan_path) != card["nan_outside_sha256"]
        or dl["nan_sha256"] != card["nan_outside_sha256"]
    ):
        raise SystemExit("DPRF1 NaN-outside GeoTIFF SHA-256 mismatch")
    if sha256_file(zip_path) != card["zip_sha256"] or dl["zip_sha256"] != card["zip_sha256"]:
        raise SystemExit("DPRF1 ZIP SHA-256 mismatch")
    with zipfile.ZipFile(zip_path) as zf:
        if zf.namelist() != [zeros_path.name]:
            raise SystemExit("DPRF1 ZIP entry list invalid")
        if hashlib.sha256(zf.read(zeros_path.name)).hexdigest() != card["raster_sha256"]:
            raise SystemExit("DPRF1 ZIP inner GeoTIFF hash mismatch")

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
        raise SystemExit("DPRF1 exact-file format/range validator check failed")

    note_text = note_path.read_text().strip()
    if len(note_text) > 140 or note_text != card["note"] or note_text != dl["note"]:
        raise SystemExit("DPRF1 note missing, mismatched, or >140 chars")

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
        raise SystemExit("DPRF1 preflight receipt missing, stale, or not fail-closed")

    return {
        "verified": True,
        "experiment_rerun": False,
        "submission_name": card["submission_name"],
        "raster_sha256": card["raster_sha256"],
        "holdout_dti": card["holdout"]["dti"],
        "single_regime_dti": exp["arms"]["arm2_single_regime"]["holdout"]["dti"],
        "deadzone9_dti": exp["arms"]["arm3_deadzone9"]["holdout"]["dti"],
        "c2st_auc": card["exact_file_nuisance_audit"]["candidate"]["observed_auc"],
        "competing_method_novelty_passed": card["correlation_overlap_vs_registry"][
            "method_lane_passed"
        ],
        "competing_method_max_3px_overlap": card["correlation_overlap_vs_registry"][
            "method_lane_max_dot_overlap"
        ],
        "farfield_gt20px_fraction": card["off_catalogue_distance_profile"]["frac_gt_20px_farfield"],
        "verdict": card["verdict"],
        "ok_to_submit": card["ok_to_submit"],
        "selector_decision": fresh_sel["decision"],
        "selector_version": fresh_sel["selector_version"],
        "preregistration": exp["preregistration"],
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
            "H24-DPRF1 experiment already recorded and frozen. No implicit rerun; use --verify-recorded."
        )

    t0 = time.monotonic()
    fp = footprint.load_footprint()
    fp_ids = np.flatnonzero(fp.ravel())
    template = ROOT / "data/bridge/sample_submission.tif"
    with rasterio.open(template) as t_ds:
        transform = t_ds.transform
    with rasterio.open(ROOT / "data/bridge/labels.tif") as l_ds:
        catalogue = (l_ds.read(1) > 0) & fp

    prep_meta = json.loads((ROOT / "data/prepared/features.json").read_text())
    prep_path = ROOT / "data/prepared/features.npy"
    if sha256_file(prep_path) != prep_meta["sha256"]:
        raise SystemExit("Prepared 30-channel feature-stack SHA-256 mismatch")
    base_mm = np.load(prep_path, mmap_mode="r")
    base_names: list[str] = list(prep_meta["names"])
    base_nc = int(prep_meta["base_count"])

    print("[1/7] Building/loading 52-channel disk-backed feature stack...", flush=True)
    if GVC_MEMMAP.exists():
        gvc_mm = np.load(GVC_MEMMAP, mmap_mode="r")
        if gvc_mm.shape != (len(fp_ids), len(gvc.GVC1_FEATURE_NAMES)):
            gvc_mm, gvc_names = gvc.build_gvc1_features(
                ROOT, base_mm, base_names, fp, transform, GVC_MEMMAP
            )
            gvc_mm = np.load(GVC_MEMMAP, mmap_mode="r")
        else:
            gvc_names = list(gvc.GVC1_FEATURE_NAMES)
    else:
        _, gvc_names = gvc.build_gvc1_features(ROOT, base_mm, base_names, fp, transform, GVC_MEMMAP)
        gvc_mm = np.load(GVC_MEMMAP, mmap_mode="r")

    sahg_mm, sahg_names = dprf1.build_sahg4_memmap(ROOT, base_mm, base_names, fp, SAHG4_MEMMAP)
    all_names = base_names + gvc_names + sahg_names
    assert len(all_names) == 52
    print(f"      52-channel stack ready; RSS={peak_rss_mib():.1f} MiB", flush=True)

    context = holdout.SegmentHoldout(fp, catalogue, buffer_px=15)
    print("[2/7] Running two-polarity Leakage Canary across all 52 channels...", flush=True)
    canary = run_batched_52ch_canary(
        context, fp, base_mm, base_names, gvc_mm, gvc_names, sahg_mm, sahg_names, batch_size=4
    )
    print(
        f"      Canary passed={canary['passed']} | worst={canary['worst_feature']} "
        f"(pooled AUC={canary['worst_pooled_auc']:.4f}); RSS={peak_rss_mib():.1f} MiB",
        flush=True,
    )
    if not canary["passed"]:
        raise SystemExit("HALT: Single-feature leakage canary exceeded threshold 0.90")

    conf_prov = confounds.build_all(force=False)
    with np.load(confounds.CONF / "confounds.npz") as c_npz:
        cdict = confounds.classifier_features(c_npz)
        nuis_keys = ["road_m", "claim_m", "block_1", "block_2", "block_3", "block_4"]
        nuisance_fp = np.column_stack(
            [cdict[k].ravel()[fp_ids].astype(np.float32, copy=False) for k in nuis_keys]
        )
    del cdict
    gc.collect()

    print(
        "[3/7] Running 4-fold SegmentHoldout (Arm 1: DPRF1, Arm 2: SingleRegime, Arm 3: DeadZone9 + Baselines)...",
        flush=True,
    )
    total_offcat = int((fp & (~catalogue)).sum())
    oof_quad_sharp = np.zeros(fp.shape, dtype=np.float32)
    oof_quad_cond = np.zeros(fp.shape, dtype=np.float32)
    oof_quad_dz9_sharp = np.zeros(fp.shape, dtype=np.float32)
    oof_quad_dz9_cond = np.zeros(fp.shape, dtype=np.float32)

    preds_arm1: list[np.ndarray] = []
    preds_arm2: list[np.ndarray] = []
    preds_arm3: list[np.ndarray] = []
    preds_b0: list[np.ndarray] = []
    preds_b1: list[np.ndarray] = []
    fold_meta: list[dict[str, Any]] = []

    for fold in context.folds:
        fid = int(fold["id"])
        fname = fold["name"]
        tf0 = time.monotonic()
        f_offcat = int((fold["valid"] & (~fold["visible"])).sum())
        k_fold = int(round(FULL_DOT_BUDGET * f_offcat / total_offcat))

        # Arm 1 & Arm 2 share the exact same 52-ch stratified_d3 model & surface
        p_s1, p_c1, m_a1 = dprf1.fit_and_predict_fold(
            base_mm,
            gvc_mm,
            sahg_mm,
            nuisance_fp,
            all_names,
            fp,
            fp_ids,
            train_mask=fold["train"],
            visible_mask=fold["visible"],
            predict_mask=fold["valid"],
            neg_mode="stratified_d3",
            seed=SEED + 10 * fid,
        )
        p_s1 = dprf1.debiased_apron_surface(p_s1, fold["valid"], fold["visible"])
        p_c1 = dprf1.debiased_apron_surface(p_c1, fold["valid"], fold["visible"])
        oof_quad_sharp += p_s1
        oof_quad_cond += p_c1

        d_arm1 = dprf1.two_regime_submodular_allocate(
            p_s1,
            p_c1,
            fold["valid"],
            fold["visible"],
            budget=k_fold,
            primary_share=0.68,
            min_spacing_px=2.8,
            catalogue_clearance_px=2.0,
        )
        d_arm2 = gvc.submodular_dti_allocate(
            p_s1,
            fold["valid"],
            fold["visible"],
            budget=k_fold,
            min_spacing_px=2.8,
            catalogue_clearance_px=2.0,
        )
        preds_arm1.append(d_arm1)
        preds_arm2.append(d_arm2)
        del p_s1, p_c1

        # Arm 3: DeadZone9 (dist_vis >= 9.0) ablation
        p_s3, p_c3, m_a3 = dprf1.fit_and_predict_fold(
            base_mm,
            gvc_mm,
            sahg_mm,
            nuisance_fp,
            all_names,
            fp,
            fp_ids,
            train_mask=fold["train"],
            visible_mask=fold["visible"],
            predict_mask=fold["valid"],
            neg_mode="deadzone_d9",
            seed=SEED + 10 * fid,
        )
        oof_quad_dz9_sharp += p_s3
        oof_quad_dz9_cond += p_c3
        d_arm3 = dprf1.two_regime_submodular_allocate(
            p_s3,
            p_c3,
            fold["valid"],
            fold["visible"],
            budget=k_fold,
            primary_share=0.68,
            min_spacing_px=2.8,
            catalogue_clearance_px=2.0,
        )
        preds_arm3.append(d_arm3)
        del p_s3, p_c3

        # Reconstruct exact B0 (OOF-H24-Ridge) and B1 (OOF-Base-Submod) for paired bootstrap CIs
        p_b0 = gvc.fit_predict_legacy_ridge_baseline(
            base_mm,
            train_mask=fold["train"],
            visible_mask=fold["visible"],
            valid_mask=fold["valid"],
            footprint=fp,
            seed=GVC_BASE_SEED + fid,
        )
        preds_b0.append(p_b0)

        surf_b1, _ = gvc.fit_predict_calibrated_hgb(
            base_mm,
            None,
            None,
            train_mask=fold["train"],
            visible_mask=fold["visible"],
            predict_mask=fold["valid"],
            footprint=fp,
            seed=GVC_BASE_SEED + fid,
            residualize=False,
        )
        p_b1 = gvc.submodular_dti_allocate(
            surf_b1,
            fold["valid"],
            fold["visible"],
            budget=k_fold,
            min_spacing_px=2.5,
            catalogue_clearance_px=2.0,
        )
        preds_b1.append(p_b1)
        del surf_b1
        gc.collect()

        r1, _ = context.score_fold(d_arm1, fold)
        r2, _ = context.score_fold(d_arm2, fold)
        r3, _ = context.score_fold(d_arm3, fold)
        rb1, _ = context.score_fold(p_b1, fold)
        print(
            f"      Fold {fname:18s} | k={k_fold:,} | DPRF1={r1['dti']:.5f} | "
            f"SingleReg={r2['dti']:.5f} | DZ9={r3['dti']:.5f} | B1={rb1['dti']:.5f} "
            f"({time.monotonic() - tf0:.1f}s, RSS={peak_rss_mib():.1f} MiB)",
            flush=True,
        )
        fold_meta.append({"fold": fname, "k_fold_budget": k_fold, "arm1": m_a1, "arm3": m_a3})

    preds_d3 = build_oof_multiphysics_hgb_d3(context, base_mm, base_names, base_nc, fp)

    sum_arm1 = context.summarize(preds_arm1, ci_draws=1999)
    sum_arm2 = context.summarize(preds_arm2, ci_draws=1999)
    sum_arm3 = context.summarize(preds_arm3, ci_draws=1999)
    sum_b0 = context.summarize(preds_b0, ci_draws=1999)
    sum_b1 = context.summarize(preds_b1, ci_draws=1999)
    sum_d3 = context.summarize(preds_d3, ci_draws=1999)

    paired = {
        "arm1_vs_oof_multiphysics_hgb_d3": context.compare_paired(
            preds_arm1, preds_d3, ci_draws=1999, seed=SEED
        ),
        "arm1_vs_B1_oof_base_submod": context.compare_paired(
            preds_arm1, preds_b1, ci_draws=1999, seed=SEED
        ),
        "arm1_vs_B0_oof_h24_ridge": context.compare_paired(
            preds_arm1, preds_b0, ci_draws=1999, seed=SEED
        ),
        "arm1_vs_arm2_two_regime_effect": context.compare_paired(
            preds_arm1, preds_arm2, ci_draws=1999, seed=SEED
        ),
        "arm1_vs_arm3_stratified_d3_vs_deadzone9": context.compare_paired(
            preds_arm1, preds_arm3, ci_draws=1999, seed=SEED
        ),
        "arm2_vs_B1_oof_base_submod": context.compare_paired(
            preds_arm2, preds_b1, ci_draws=1999, seed=SEED
        ),
        "arm3_vs_B1_oof_base_submod": context.compare_paired(
            preds_arm3, preds_b1, ci_draws=1999, seed=SEED
        ),
    }
    print(
        f"      POOLED HOLDOUT-DTI | Arm1(DPRF1)={sum_arm1['dti']:.5f} {sum_arm1['ci95']['interval']} | "
        f"Arm2(SingleReg)={sum_arm2['dti']:.5f} | Arm3(DZ9)={sum_arm3['dti']:.5f} | "
        f"B1={sum_b1['dti']:.5f} | B0={sum_b0['dti']:.5f} | d3={sum_d3['dti']:.5f}",
        flush=True,
    )
    del preds_arm1, preds_arm2, preds_arm3, preds_b0, preds_b1, preds_d3
    gc.collect()

    oof_canary = context.canary(
        {"dprf1_quad_oof_sharp": oof_quad_sharp}, seed=GVC_BASE_SEED, max_per_class=15000
    )
    if not oof_canary["passed"]:
        raise SystemExit("HALT: Quadrant OOF surface flagged leakage canary")

    print("[4/7] Running 3.0 km segment-hide-recover-pooled-v1 bridge evaluation...", flush=True)
    bridge_3km = evaluate_bridge_3km(
        base_mm, gvc_mm, sahg_mm, nuisance_fp, all_names, fp, catalogue
    )
    print(
        f"      Bridge HOLDOUT-DTI (3.0 km): DPRF1={bridge_3km['dti']:.5f} {bridge_3km['ci95']} "
        f"(vs RSHG1 {bridge_3km['recorded_rshg1_bridge_dti']:.5f}, FUSE-HCW {bridge_3km['recorded_fuse_hcw_bridge_dti']:.5f})",
        flush=True,
    )

    print(
        "[5/7] Running Partition 2 (Rotated45_Diamond_OOF) & Stitched-OOF Apron Debiasing...",
        flush=True,
    )
    rot45_folds = dprf1.make_rotated45_segment_folds(fp, catalogue, buffer_px=15)
    oof_rot45_sharp = np.zeros(fp.shape, dtype=np.float32)
    oof_rot45_cond = np.zeros(fp.shape, dtype=np.float32)
    for rfold in rot45_folds:
        rfid = int(rfold["id"])
        ps_r, pc_r, _ = dprf1.fit_and_predict_fold(
            base_mm,
            gvc_mm,
            sahg_mm,
            nuisance_fp,
            all_names,
            fp,
            fp_ids,
            train_mask=rfold["train"],
            visible_mask=rfold["visible"],
            predict_mask=rfold["valid"],
            neg_mode="stratified_d3",
            seed=SEED + 500 + 17 * rfid,
        )
        oof_rot45_sharp += ps_r
        oof_rot45_cond += pc_r
        del ps_r, pc_r
        gc.collect()

    stitched_sharp_raw = (0.50 * oof_quad_sharp + 0.50 * oof_rot45_sharp).astype(np.float32)
    stitched_cond_raw = (0.50 * oof_quad_cond + 0.50 * oof_rot45_cond).astype(np.float32)
    del oof_rot45_sharp, oof_rot45_cond, oof_quad_dz9_sharp, oof_quad_dz9_cond
    gc.collect()

    # Apply locked Visible-Catalogue Apron Quantile Debiasing (2 < d_cat <= 9 px -> d_cat > 12 px)
    stitched_sharp = dprf1.debiased_apron_surface(stitched_sharp_raw, fp, catalogue)
    stitched_cond = dprf1.debiased_apron_surface(stitched_cond_raw, fp, catalogue)
    pre_placement_surface = (0.68 * stitched_sharp + 0.32 * stitched_cond).astype(np.float32)

    priority_reg = json.loads((ROOT / "registry/priority_rasters.json").read_text())
    existing_shas = {e["footprint_sha256"] for e in priority_reg["unique_rasters"]}
    extra_locals = all_local_20261025_entries(fp, existing_shas)

    print(
        f"[6/7] Checking pre-placement & final-dot novelty across {len(priority_reg['unique_rasters']) + len(extra_locals)} registry rasters + 83 peer blobs...",
        flush=True,
    )
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
        f"      Pre-placement surface: method_lane_passed={pre_nov_methods['method_lane_passed']} "
        f"(max |rho|={pre_nov_methods['method_lane_max_abs_rank_correlation']:.4f}), "
        f"peers_passed={pre_nov_peers['passed']} (max |rho|={pre_nov_peers['max_abs_surface_spearman']:.4f})",
        flush=True,
    )
    if not pre_nov_methods["method_lane_passed"] or not pre_nov_peers["passed"]:
        raise SystemExit("HALT: Pre-placement surface exceeded 0.90 rank-correlation limit")

    final_dots = dprf1.two_regime_submodular_allocate(
        stitched_sharp,
        stitched_cond,
        fp,
        catalogue,
        budget=FULL_DOT_BUDGET,
        primary_share=0.68,
        min_spacing_px=2.8,
        catalogue_clearance_px=2.0,
    )
    # Also compute un-debiased stitched-OOF dots purely as an internal diagnostic of apron debiasing
    dots_undebiased_diag = dprf1.two_regime_submodular_allocate(
        stitched_sharp_raw,
        stitched_cond_raw,
        fp,
        catalogue,
        budget=FULL_DOT_BUDGET,
        primary_share=0.68,
        min_spacing_px=2.8,
        catalogue_clearance_px=2.0,
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
    comp_nov_ok = bool(final_nov_methods["method_lane_passed"] and final_nov_peers["passed"])
    print(
        f"      Final dots ({dist_profile['n_dots']:,}): competing_methods={final_nov_methods['competing_method_rasters_count']} "
        f"(passed={final_nov_methods['method_lane_passed']}, max_3px_overlap={final_nov_methods['method_lane_max_dot_overlap']:.4f}, "
        f"max_|rho|={final_nov_methods['method_lane_max_abs_rank_correlation']:.4f}); "
        f"peers={final_nov_peers['peer_unique_blobs_checked']} "
        f"(passed={final_nov_peers['passed']}, max_3px_overlap={final_nov_peers['max_dot_overlap_within_3px']:.4f}); "
        f"apron_2_9px={100 * dist_profile['frac_2_to_9px_apron']:.1f}%, farfield_gt20px={100 * dist_profile['frac_gt_20px_farfield']:.1f}%",
        flush=True,
    )

    print(
        "[7/7] Writing GeoTIFF pair + ZIP, running exact-file C2ST nuisance audit & preflight...",
        flush=True,
    )
    slug = (
        "dprf1-stitched-oof-tworegime" if comp_nov_ok else "dprf1-negative-stitched-oof-tworegime"
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

    zero_raw_checks = submission.check_variants(zeros_path, template)
    nan_raw_checks = submission.check_variants(nan_path, template)
    if (
        not zero_raw_checks["format_valid"]
        or not nan_raw_checks["format_valid"]
        or not strict_whole_array_ok(zero_raw_checks)
    ):
        raise SystemExit("Exact-file format/strict-range validator failed")

    checks_payload = {
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
        "zeros_zip_file": zip_name,
        "zeros_zip_sha256": sha256_file(zip_path),
    }
    checks_file = f"checks-{zeros_name[:-4]}.json"
    save_json(checks_payload, downloads / checks_file)

    c2st_report = run_exact_file_c2st(zeros_path, catalogue, fp)
    print(
        f"      C2ST strict pass={c2st_report['candidate']['strict_gate_passed']} "
        f"(AUC={c2st_report['candidate']['observed_auc']:.4f}, Holm p={c2st_report['candidate']['holm_p_value']:.3f})",
        flush=True,
    )

    write_preview(final_dots > 0.5, fp, PREVIEW_PNG)

    note = (
        f"GEMS24 DPRF1 | 52ch stitched-OOF 2-regime submod | id {content_id} | "
        f"HOLDOUT-DTI {sum_arm1['dti']:.5f} | research; selector gated"
    )
    if len(note) > 140:
        raise AssertionError(f"Note length {len(note)} exceeds 140 characters")
    note_file = f"note-{zeros_name[:-4]}.txt"
    (downloads / note_file).write_text(note + "\n")

    # Sort top competing comparators by 3-px dot overlap for transparent reporting
    comp_rows_sorted = sorted(
        [
            r
            for r in final_nov_methods["rows"]
            if r.get("entry_role") == "competing_method_lane"
            and r.get("candidate_dot_overlap_within_3px") is not None
        ],
        key=lambda r: float(r["candidate_dot_overlap_within_3px"]),
        reverse=True,
    )

    recorded_gvc1 = json.loads((ROOT / "evidence/gvc1_run_card_20261025.json").read_text())
    recorded_rshg1 = json.loads((ROOT / "evidence/rshg1_run_card_20261025.json").read_text())
    recorded_hcw = json.loads((ROOT / "evidence/hcw_run_card_20261025.json").read_text())
    recorded_sahg1 = json.loads((ROOT / "evidence/sahg1_run_card_20261025.json").read_text())

    technical_gates = {
        "format_and_strict_0_1_range_passed": True,
        "leakage_canary_52ch_passed": bool(canary["passed"]),
        "beats_oof_multiphysics_hgb_d3_ci95_gt_0": bool(
            paired["arm1_vs_oof_multiphysics_hgb_d3"]["ci95_strictly_positive"]
        ),
        "beats_matched_oof_base_B1_ci95_gt_0": bool(
            paired["arm1_vs_B1_oof_base_submod"]["ci95_strictly_positive"]
        ),
        "beats_legacy_oof_h24_ridge_B0": bool(sum_arm1["dti"] > sum_b0["dti"]),
        "beats_all_prior_method_unique_lanes_in_repo": bool(
            sum_arm1["dti"] > float(recorded_hcw["holdout"]["dti"])
            and sum_arm1["dti"] > float(recorded_sahg1["holdout"]["dti"])
        ),
        "competing_method_novelty_54_rasters_passed": bool(final_nov_methods["method_lane_passed"]),
        "peer_blobs_83_novelty_passed": bool(final_nov_peers["passed"]),
        "exact_file_c2st_nuisance_passed": bool(c2st_report["candidate"]["strict_gate_passed"]),
        "stitched_oof_apron_debiasing_verified": bool(
            dist_profile["frac_gt_20px_farfield"] >= 0.35 and dist_profile["frac_le_2px"] == 0.0
        ),
    }
    all_technical_passed = all(technical_gates.values())

    elapsed = round(time.monotonic() - t0, 2)
    run_card = {
        "schema_version": 2,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "lane_id": "H24-DPRF1",
        "preregistration": PREREG_PATH,
        "preregistration_commit": PREREG_COMMIT,
        "experiments_run": 3,
        "experiment_budget_limit": 3,
        "elapsed_seconds": elapsed,
        "peak_rss_mib": round(peak_rss_mib(), 1),
        "hypothesis": (
            "52-channel Dual-Partition Stitched-OOF hydrothermal-structural fusion "
            "(30 scale-separated base + 18 OpenEI GDR INGENIOUS paleo-sinter/2m-probe/geothermometry/"
            "Miller-Singh tilt/8-azimuth lineaments + 4 modality-aware SAHG1 conduit channels) "
            "with selective 9-channel non-topographic nuisance residualization, relief-conditioned "
            "LiDAR-gap log-odds calibration, 8-azimuth ridge sharpening, visible-catalogue apron "
            "quantile debiasing, and Two-Regime 300 m submodular allocation (68% primary ridge + "
            "32% low-relief intrabasin/step-over hydrothermal-subsurface conduit)."
        ),
        "mechanism": (
            "Eliminates the Stage-5 in-sample 200-900 m catalogue-apron memorization bug that caused "
            "GVC1 (0.14876 holdout -> 0.0859 owner-reported live, 70.4% dots in 2-9 px, 76.82% range-front "
            "overlap) to collapse, while preserving multi-physics + INGENIOUS hydrothermal recall across "
            "both 3DEP LiDAR gaps (via relief-conditioned tail matching) and concealed intrabasin/step-over "
            "geothermal conduits (via Two-Regime submodular 300 m coverage allocation)."
        ),
        "named_non_fault_mimic": (
            "Coincidence of a Tertiary welded ash-flow tuff cooling-joint hogback or diabase dike swarm "
            "with lateral hot-spring travertine apron outflow or arkosic K-feldspar alluvial fan detritus, "
            "plus Pleistocene Lake Lahontan shorezone tufa benches."
        ),
        "holdout": sum_arm1,
        "bridge_protocol_holdout": bridge_3km,
        "baselines_and_siblings_same_evaluator": {
            "oof_multiphysics_hgb_d3": {
                "dti": sum_d3["dti"],
                "ci95": sum_d3["ci95"]["interval"],
            },
            "B1_oof_base_submod": {
                "dti": sum_b1["dti"],
                "ci95": sum_b1["ci95"]["interval"],
            },
            "B0_oof_h24_ridge": {
                "dti": sum_b0["dti"],
                "ci95": sum_b0["ci95"]["interval"],
            },
            "H24_SAHG1_recorded": {
                "dti": float(recorded_sahg1["holdout"]["dti"]),
                "ci95": recorded_sahg1["holdout"]["ci95"]["interval"],
            },
            "H24_FUSE_HCW_recorded": {
                "dti": float(recorded_hcw["holdout"]["dti"]),
                "ci95": recorded_hcw["holdout"]["ci95"]["interval"],
            },
            "H24_RSHG1_recorded": {
                "dti": float(recorded_rshg1["holdout"]["dti"]),
                "ci95": recorded_rshg1["holdout"]["ci95"]["interval"],
            },
            "H24_GVC1_recorded_overlap_failed": {
                "dti": float(recorded_gvc1["holdout"]["dti"]),
                "ci95": recorded_gvc1["holdout"]["ci95"]["interval"],
                "competing_3px_overlap": float(
                    recorded_gvc1["correlation_overlap_vs_registry"][
                        "final_max_competing_overlap_within_3px"
                    ]
                ),
            },
        },
        "paired_comparisons": paired,
        "leakage_canary": {
            "passed": canary["passed"],
            "n_features_checked": canary["n_features_checked"],
            "worst_feature": canary["worst_feature"],
            "worst_pooled_auc": canary["worst_pooled_auc"],
            "worst_polarity_extremity": canary["worst_polarity_extremity"],
            "oof_surface_auc": oof_canary["features"]["dprf1_quad_oof_sharp"]["pooled_auc"],
        },
        "correlation_overlap_vs_registry": {
            "total_registry_entries_checked": final_nov_methods["registry_unique_rasters"],
            "competing_method_rasters_checked": final_nov_methods["competing_method_rasters_count"],
            "calibration_control_rasters_checked": final_nov_methods[
                "calibration_control_rasters_count"
            ],
            "peer_blobs_checked": final_nov_peers["peer_unique_blobs_checked"],
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
            "peer_blobs_passed": final_nov_peers["passed"],
            "peer_blobs_max_dot_overlap": final_nov_peers["max_dot_overlap_within_3px"],
            "peer_blobs_max_overlap_artifact": final_nov_peers["max_overlap_peer_artifact"],
            "literal_all_entries_passed": final_nov_methods["literal_all_entries_passed"],
            "literal_all_entries_max_dot_overlap": final_nov_methods["max_dot_overlap"],
            "calibration_control_rows": final_nov_methods["calibration_control_rows"],
            "top_5_competing_comparators": comp_rows_sorted[:5],
        },
        "off_catalogue_distance_profile": dist_profile,
        "off_catalogue_distance_profile_before_apron_debiasing": dist_profile_undebiased,
        "exact_file_nuisance_audit": c2st_report,
        "technical_gates": technical_gates,
        "technical_promotion_gates_passed": all_technical_passed,
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
            "crs": "EPSG:32611",
            "shape": [3730, 3292],
            "transform": [100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0],
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
            "Retained synthetic spacing-5 calibration lattice (registry-039) covers 99.87% of footprint within 3 px under literal unseparated check",
            "No coordinator-assigned single-method lane paragraph or live account weekly-quota receipt in sandbox",
        ],
    }

    save_json(run_card, RUN_CARD_JSON)
    save_json(run_card, DOCS_RUN_CARD_JSON)

    # Run shared exact-file preflight_submission.py to write the hash-bound preflight receipt
    preflight_out = downloads / f"{zeros_name[:-4]}.preflight.json"
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/preflight_submission.py"),
            str(zeros_path),
            "--run-card",
            str(RUN_CARD_JSON),
            "--output",
            str(preflight_out),
        ],
        cwd=ROOT,
        check=True,
    )

    download_record = {
        "lane_id": "H24-DPRF1",
        "file": zeros_name,
        "sha256": zero_raw_checks["sha256"],
        "nan_file": nan_name,
        "nan_sha256": nan_raw_checks["sha256"],
        "zip_file": zip_name,
        "zip_sha256": checks_payload["zeros_zip_sha256"],
        "checks_file": checks_file,
        "preflight_file": preflight_out.name,
        "note_file": note_file,
        "note": note,
        "pixel_count": int((final_dots[fp] > 0.5).sum()),
        "holdout_dti": sum_arm1["dti"],
        "holdout_ci95": sum_arm1["ci95"]["interval"],
        "bridge_dti": bridge_3km["dti"],
        "c2st_auc": c2st_report["candidate"]["observed_auc"],
        "c2st_holm_p": c2st_report["candidate"]["holm_p_value"],
        "competing_method_novelty_passed": final_nov_methods["method_lane_passed"],
        "competing_method_max_3px_overlap": final_nov_methods["method_lane_max_dot_overlap"],
        "peer_blobs_novelty_passed": final_nov_peers["passed"],
        "peer_blobs_max_3px_overlap": final_nov_peers["max_dot_overlap_within_3px"],
        "farfield_gt20px_fraction": dist_profile["frac_gt_20px_farfield"],
        "technical_promotion_gates_passed": all_technical_passed,
        "ok_to_download": True,
        "ok_to_submit": False,
        "submission_authorized": False,
        "verdict": "negative",
    }
    save_json(download_record, DOCS_DOWNLOAD_JSON)

    experiment_record = {
        "generated_utc": run_card["generated_utc"],
        "lane_id": "H24-DPRF1",
        "preregistration": PREREG_PATH,
        "preregistration_commit": PREREG_COMMIT,
        "elapsed_seconds": elapsed,
        "peak_rss_mib": run_card["peak_rss_mib"],
        "feature_names_52": all_names,
        "selective_residualized_9": sorted(dprf1.SELECTIVE_RESID_NAMES),
        "canary": canary,
        "fold_fit_metadata": fold_meta,
        "arms": {
            "arm1_dprf1_primary": {"holdout": sum_arm1},
            "arm2_single_regime": {"holdout": sum_arm2},
            "arm3_deadzone9": {"holdout": sum_arm3},
        },
        "baselines": {
            "oof_multiphysics_hgb_d3": sum_d3,
            "B1_oof_base_submod": sum_b1,
            "B0_oof_h24_ridge": sum_b0,
        },
        "paired_comparisons": paired,
        "bridge_3km": bridge_3km,
        "novelty": {
            "pre_placement_methods": {k: v for k, v in pre_nov_methods.items() if k != "rows"},
            "pre_placement_peers": pre_nov_peers,
            "final_dots_methods": final_nov_methods,
            "final_dots_peers": final_nov_peers,
        },
        "off_catalogue_distance_profile": dist_profile,
        "off_catalogue_distance_profile_before_apron_debiasing": dist_profile_undebiased,
        "c2st_audit": c2st_report,
        "nuisance_provenance": conf_prov,
        "ok_to_submit": False,
        "run_card": run_card,
    }
    save_json(experiment_record, EXPERIMENT_JSON)
    print(
        f"Done in {elapsed:.1f}s (peak RSS {run_card['peak_rss_mib']:.1f} MiB). "
        f"Technical gates all passed={all_technical_passed}; verdict={run_card['verdict']}.",
        flush=True,
    )


if __name__ == "__main__":
    main()
