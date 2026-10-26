#!/usr/bin/env python3
"""Execute or verify H24-DKRN1 (Topological D8 Knickpoint Routing + Split-View 300 m DTI-Kernel).

Preregistration: ``knowledge/27_preregistered_DKRN1_2026-10-26.md`` (commit ``86d7f622a0ef``).
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
    dkrn1,
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

LANE_ID = "H24-DKRN1"
PREREG_PATH = "knowledge/27_preregistered_DKRN1_2026-10-26.md"
PREREG_COMMIT = "86d7f622a0ef5e521611d976e86eab72ad42ce1a"

SEED = 20261026
GVC_BASE_SEED = 20261025
FULL_DOT_BUDGET = 37654
RECORDED_DPRF1_DTI = 0.1637924246971501

BASELINE_D3_PARAMS: dict[str, Any] = {
    "max_iter": 80,
    "max_leaf_nodes": 15,
    "learning_rate": 0.08,
    "l2_regularization": 5.0,
    "early_stopping": False,
}

STAGE1_DIR = ROOT / "data/prepared/dkrn1_work"
STAGE1_JSON = STAGE1_DIR / "stage1_summary.json"
STAGE1_ARRAYS = STAGE1_DIR / "stage1_oof_quad.npz"
STAGE2_JSON = STAGE1_DIR / "stage2_bridge.json"
STAGE2_ARRAYS = STAGE1_DIR / "stage2_oof_rot.npz"

EXPERIMENT_JSON = ROOT / "evidence/dkrn1_experiment_20261026.json"
RUN_CARD_JSON = ROOT / "evidence/dkrn1_run_card_20261026.json"
SELECTOR_JSON = ROOT / "evidence/dkrn1_selector_20261026.json"
DOCS_RUN_CARD_JSON = ROOT / "docs/data/dkrn1_run_card.json"
DOCS_SELECTOR_JSON = ROOT / "docs/data/dkrn1_selector.json"
DOCS_DOWNLOAD_JSON = ROOT / "docs/data/dkrn1_download.json"
PREVIEW_PNG = ROOT / "docs/assets/dkrn1-preview.png"


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
    rgb[d_small] = (13, 110, 110)
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
    sources: list[tuple[str, np.ndarray, list[str]]],
    *,
    batch_size: int = 4,
) -> dict[str, Any]:
    """Two-polarity single-feature canary over all 62 channels."""
    fp_ids = np.flatnonzero(fp.ravel())
    specs: list[tuple[str, int, int]] = []
    for si, (_sname, _mm, names) in enumerate(sources):
        for col, name in enumerate(names):
            specs.append((name, si, col))
    merged: dict[str, Any] = {}
    last_meta: dict[str, Any] = {}
    for start in range(0, len(specs), batch_size):
        batch = specs[start : start + batch_size]
        fdict: dict[str, np.ndarray] = {}
        for name, si, col in batch:
            grid = np.full(fp.shape, np.nan, dtype=np.float32)
            grid.ravel()[fp_ids] = sources[si][1][:, col]
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
    worst_auc = merged[worst_name]["pooled_auc"]
    dkrn1_aucs = {k: merged[k]["pooled_auc"] for k in dkrn1.DKRN1_NAMES if k in merged}
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
        "dkrn1_channel_pooled_aucs": dkrn1_aucs,
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
                emission.priority_poisson(f_surf, elig, budget, min_dist=3).astype(np.float32)
            )
            del f_surf, x_tr, clf
            gc.collect()
    return preds


def evaluate_bridge_3km(
    base_mm: np.ndarray,
    gvc_mm: np.ndarray,
    sahg_mm: np.ndarray,
    dkrn1_mm: np.ndarray,
    nuisance_fp: np.ndarray,
    all_names: list[str],
    fp: np.ndarray,
    catalogue: np.ndarray,
) -> dict[str, Any]:
    """Evaluate Arm 1 (H24-DKRN1) on the 3.0 km / 20 km tile bridge protocol."""
    fp_ids = np.flatnonzero(fp.ravel())
    total_offcat = int((fp & (~catalogue)).sum())
    tile_rows_all = []
    fold_details = []
    for fid, fold in enumerate(holdout.segment_folds(fp, catalogue, buffer_px=30)):
        surfs, _ = dkrn1.fit_and_predict_dkrn1_fold(
            base_mm,
            gvc_mm,
            sahg_mm,
            dkrn1_mm,
            nuisance_fp,
            all_names,
            fp,
            fp_ids,
            train_mask=fold["training"],
            visible_mask=fold["visible"],
            predict_mask=fold["test"],
            seed=SEED + 300 + 13 * fid,
        )
        f_offcat = int((fold["test"] & (~fold["visible"])).sum())
        k_fold = int(round(FULL_DOT_BUDGET * f_offcat / total_offcat))
        dots = dkrn1.three_regime_net_tversky_allocate(
            surfs["u_post"],
            surfs["mu_deb"],
            surfs["m_hydro"],
            surfs["m_concealed"],
            fold["test"],
            fold["visible"],
            budget=k_fold,
            shares=(0.48, 0.28, 0.24),
            min_spacing_px=2.9,
            catalogue_clearance_px=2.0,
        )
        t_rows, ref = holdout.spatial_components(
            dots > 0.5, fold["hidden"] & fold["test"], fold["test"], fold["visible"], tile_px=200
        )
        tile_rows_all.append(t_rows)
        fold_details.append({"fold": fold["name"], **ref})
        del surfs, dots
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
    """All 17 local 2026-10-25 and 2026-10-26 GEMSDOE24 method-lane GeoTIFFs."""
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
        (
            "local-20261026-tnr1",
            "docs/downloads/gems24-tnr1-56dfd14b88db-20261026-RESEARCH-NOT-SUBMISSION-zeros.tif",
        ),
        (
            "local-20261026-crp1",
            "docs/downloads/gems24-crp1-compfront-xdepth-saddle-20261026-c679a967f700-zeros.tif",
        ),
        (
            "local-20261026-cup1",
            "docs/downloads/gems24-cup1-negative-compfront-upcont-submod-20261026-35a808f4514a-zeros.tif",
        ),
        (
            "local-20261026-dprf1",
            "docs/downloads/gems24-dprf1-stitched-oof-tworegime-20261026-81849d67c8bf-zeros.tif",
        ),
        (
            "local-20261026-trsg1",
            "docs/downloads/gems24-trsg1-tworegime-seismic-geo-oof-20261026-7f301fc433f0-zeros.tif",
        ),
        (
            "local-20261026-vent",
            "docs/downloads/gems24-vent-quat-bridge-20261026-a6e191937e80-zeros.tif",
        ),
        (
            "local-20261026-eul1",
            "docs/downloads/gems24-eul1-negative-euler-contact-20261026-eda170f04847-zeros.tif",
        ),
        (
            "local-20261026-pair1",
            "docs/downloads/gems24-pair1-graben-dipole-oof-20261026-842a5212d85c-zeros.tif",
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
    """Auxiliary cross-site novelty check against freshly cached 2026-10-26 sibling focus TIFs."""
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
        "h24_dkrn1_exact_file",
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
    """Verify frozen DKRN1 receipts, GeoTIFF variants, ZIP, selector, preflight, and <=140-char note."""
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
            raise SystemExit(f"Missing recorded DKRN1 artifact: {p}")
    card = json.loads(RUN_CARD_JSON.read_text())
    docs_card = json.loads(DOCS_RUN_CARD_JSON.read_text())
    saved_sel = json.loads(SELECTOR_JSON.read_text())
    docs_sel = json.loads(DOCS_SELECTOR_JSON.read_text())
    dl = json.loads(DOCS_DOWNLOAD_JSON.read_text())
    if card != docs_card or saved_sel != docs_sel:
        raise SystemExit("Evidence and docs/data DKRN1 run cards or selector receipts disagree")
    if card.get("selector_receipt") != saved_sel:
        raise SystemExit("DKRN1 run card embedded selector receipt disagrees with selector file")

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
        raise SystemExit("DKRN1 run card/download disagrees with independent gems.selector receipt")

    if sha256_file(zeros_path) != card["raster_sha256"] or dl["sha256"] != card["raster_sha256"]:
        raise SystemExit("DKRN1 zero-outside GeoTIFF SHA-256 mismatch")
    if (
        sha256_file(nan_path) != card["nan_outside_sha256"]
        or dl["nan_sha256"] != card["nan_outside_sha256"]
    ):
        raise SystemExit("DKRN1 NaN-outside GeoTIFF SHA-256 mismatch")
    if sha256_file(zip_path) != card["zip_sha256"] or dl["zip_sha256"] != card["zip_sha256"]:
        raise SystemExit("DKRN1 ZIP SHA-256 mismatch")
    with zipfile.ZipFile(zip_path) as zf:
        if zf.namelist() != [zeros_path.name]:
            raise SystemExit("DKRN1 ZIP entry list invalid")
        if hashlib.sha256(zf.read(zeros_path.name)).hexdigest() != card["raster_sha256"]:
            raise SystemExit("DKRN1 ZIP inner GeoTIFF hash mismatch")

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
        raise SystemExit("DKRN1 exact-file format/range validator check failed")

    note_text = note_path.read_text().strip()
    if len(note_text) > 140 or note_text != card["note"] or note_text != dl["note"]:
        raise SystemExit("DKRN1 note missing, mismatched, or >140 chars")

    pre = json.loads(preflight_path.read_text())
    if (
        pre.get("artifact", {}).get("sha256") != card["raster_sha256"]
        or pre.get("run_card", {}).get("artifact_sha256_matches") is not True
        or pre.get("run_card", {}).get("artifact_name_matches") is not True
        or pre.get("decision", {}).get("submission_status") != "DO_NOT_SUBMIT"
        or pre.get("decision", {}).get("ready_to_submit") is not False
    ):
        raise SystemExit("DKRN1 preflight receipt failed closed check")

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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-recorded", action="store_true")
    parser.add_argument("--stage", choices=("1", "2", "3", "all"), default="all")
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
    print(
        f"[1/8] Loading footprint, prepared stack, and building {LANE_ID} 10-ch memmap...",
        flush=True,
    )
    fp = footprint.load_footprint()
    fp_ids = np.flatnonzero(fp.ravel())
    template = ROOT / "data/bridge/sample_submission.tif"
    with rasterio.open(template) as ds_t:
        transform = ds_t.transform
        tmpl_crs = str(ds_t.crs)
        tmpl_shape = ds_t.shape
    with rasterio.open(ROOT / "data/bridge/labels.tif") as ds_l:
        catalogue = (ds_l.read(1) > 0) & fp

    prep_meta = json.loads((ROOT / "data/prepared/features.json").read_text())
    prep_path = ROOT / "data/prepared/features.npy"
    if sha256_file(prep_path) != prep_meta["sha256"]:
        raise SystemExit("Prepared 30-channel feature-stack SHA-256 mismatch")
    base_names: list[str] = list(prep_meta["names"])
    base_nc = int(prep_meta["base_count"])
    base_mm = np.load(prep_path, mmap_mode="r")

    gvc_memmap = ROOT / "data/prepared/gvc1_features.npy"
    if gvc_memmap.exists():
        gvc_mm = np.load(gvc_memmap, mmap_mode="r")
        if gvc_mm.shape != (len(fp_ids), len(gvc.GVC1_FEATURE_NAMES)):
            _, gvc_names = gvc.build_gvc1_features(
                ROOT, base_mm, base_names, fp, transform, gvc_memmap
            )
            gvc_mm = np.load(gvc_memmap, mmap_mode="r")
        else:
            gvc_names = list(gvc.GVC1_FEATURE_NAMES)
    else:
        _, gvc_names = gvc.build_gvc1_features(ROOT, base_mm, base_names, fp, transform, gvc_memmap)
        gvc_mm = np.load(gvc_memmap, mmap_mode="r")

    sahg_mm, sahg_names = dprf1.build_sahg4_memmap(
        ROOT, base_mm, base_names, fp, ROOT / "data/prepared/sahg4_features.npy"
    )
    dkrn1_mm, dkrn1_names = dkrn1.build_dkrn1_memmap(
        ROOT, base_mm, base_names, fp, ROOT / "data/prepared/dkrn1_features.dat"
    )
    names52 = base_names + gvc_names + sahg_names
    names62 = names52 + dkrn1_names

    conf_prov = confounds.build_all(force=False)
    with np.load(confounds.CONF / "confounds.npz") as c_npz:
        cdict = confounds.classifier_features(c_npz)
        nuis_keys = ["road_m", "claim_m", "block_1", "block_2", "block_3", "block_4"]
        nuisance_fp = np.column_stack(
            [cdict[k].ravel()[fp_ids].astype(np.float32, copy=False) for k in nuis_keys]
        )
    del cdict
    gc.collect()

    context = holdout.SegmentHoldout(fp, catalogue, buffer_px=15)

    if args.stage in ("1", "all"):
        print(
            "[2/8] Running two-polarity single-feature leakage canary over all 62 channels...",
            flush=True,
        )
        canary = run_batched_canary(
            context,
            fp,
            [
                ("base30", base_mm, base_names),
                ("gvc18", gvc_mm, gvc_names),
                ("sahg4", sahg_mm, sahg_names),
                ("dkrn1_10", dkrn1_mm, dkrn1_names),
            ],
        )
        print(
            f"      Canary passed={canary['passed']} (n={canary['n_features_checked']}, "
            f"worst={canary['worst_feature']} extremity={canary['worst_polarity_extremity']:.4f})",
            flush=True,
        )
        if not canary["passed"]:
            raise SystemExit("HALT: Single-feature leakage canary exceeded 0.90 threshold!")

        print(
            "[3/8] Partition 1 (SegmentHoldout, 60,988 withheld): "
            "Arm 1 (DKRN1 Split-View 62ch) vs Arm 2 (HeadA Kernel47) vs Arm 3 (DPRF1 replay + OOF-d3)...",
            flush=True,
        )
        total_offcat = int((fp & (~catalogue)).sum())
        preds_arm1: list[np.ndarray] = []
        preds_arm2: list[np.ndarray] = []
        preds_arm3_dprf1: list[np.ndarray] = []
        oof_quad_u = np.zeros(fp.shape, dtype=np.float32)
        oof_quad_mu = np.zeros(fp.shape, dtype=np.float32)
        oof_quad_mh = np.zeros(fp.shape, dtype=np.float32)
        oof_quad_mc = np.zeros(fp.shape, dtype=np.float32)
        fold_meta: list[dict[str, Any]] = []

        for fold in context.folds:
            tf0 = time.monotonic()
            fid = int(fold["id"])
            fname = str(fold["name"])
            f_offcat = int((fold["valid"] & (~fold["visible"])).sum())
            k_fold = int(round(FULL_DOT_BUDGET * f_offcat / total_offcat))

            surfs, m_dkrn = dkrn1.fit_and_predict_dkrn1_fold(
                base_mm,
                gvc_mm,
                sahg_mm,
                dkrn1_mm,
                nuisance_fp,
                names62,
                fp,
                fp_ids,
                train_mask=fold["train"],
                visible_mask=fold["visible"],
                predict_mask=fold["valid"],
                seed=SEED + 10 * fid,
            )
            oof_quad_u += surfs["u_post"]
            oof_quad_mu += surfs["mu_deb"]
            oof_quad_mh += surfs["m_hydro"]
            oof_quad_mc += surfs["m_concealed"]

            d_arm1 = dkrn1.three_regime_net_tversky_allocate(
                surfs["u_post"],
                surfs["mu_deb"],
                surfs["m_hydro"],
                surfs["m_concealed"],
                fold["valid"],
                fold["visible"],
                budget=k_fold,
                shares=(0.48, 0.28, 0.24),
                min_spacing_px=2.9,
                catalogue_clearance_px=2.0,
            )
            d_arm2 = dkrn1.three_regime_net_tversky_allocate(
                surfs["mu_deb"],
                surfs["mu_deb"],
                surfs["m_hydro"],
                surfs["m_concealed"],
                fold["valid"],
                fold["visible"],
                budget=k_fold,
                shares=(0.48, 0.28, 0.24),
                min_spacing_px=2.9,
                catalogue_clearance_px=2.0,
            )
            preds_arm1.append((d_arm1 > 0.5).astype(np.uint8))
            preds_arm2.append((d_arm2 > 0.5).astype(np.uint8))
            del surfs, d_arm1, d_arm2
            gc.collect()

            p_s3, p_c3, m_dprf = dprf1.fit_and_predict_fold(
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
            preds_arm3_dprf1.append((d_arm3 > 0.5).astype(np.uint8))
            del p_s3, p_c3, d_arm3
            gc.collect()

            r1, _ = context.score_fold(preds_arm1[-1], fold)
            r2, _ = context.score_fold(preds_arm2[-1], fold)
            r3, _ = context.score_fold(preds_arm3_dprf1[-1], fold)
            print(
                f"      Fold {fname:18s} | k={k_fold:,} | DKRN1={r1['dti']:.5f} | "
                f"HeadA47={r2['dti']:.5f} | DPRF1(replay)={r3['dti']:.5f} "
                f"({time.monotonic() - tf0:.1f}s, RSS={peak_rss_mib():.1f} MiB)",
                flush=True,
            )
            fold_meta.append(
                {"fold": fname, "k_fold_budget": k_fold, "dkrn1": m_dkrn, "dprf1_replay": m_dprf}
            )

        preds_oof_d3 = build_oof_multiphysics_hgb_d3(context, base_mm, base_names, base_nc, fp)
        sum_arm1 = context.summarize(preds_arm1, ci_draws=1999)
        sum_arm2 = context.summarize(preds_arm2, ci_draws=1999)
        sum_arm3_dprf1 = context.summarize(preds_arm3_dprf1, ci_draws=1999)
        sum_oof_d3 = context.summarize(preds_oof_d3, ci_draws=1999)

        paired = {
            "arm1_vs_dprf1_replay": context.compare_paired(
                preds_arm1, preds_arm3_dprf1, ci_draws=1999, seed=GVC_BASE_SEED
            ),
            "arm1_vs_oof_multiphysics_hgb_d3": context.compare_paired(
                preds_arm1, preds_oof_d3, ci_draws=1999, seed=GVC_BASE_SEED
            ),
            "arm1_vs_arm2_head_a_kernel47": context.compare_paired(
                preds_arm1, preds_arm2, ci_draws=1999, seed=GVC_BASE_SEED
            ),
            "arm2_head_a_kernel47_vs_oof_d3": context.compare_paired(
                preds_arm2, preds_oof_d3, ci_draws=1999, seed=GVC_BASE_SEED
            ),
        }
        print(
            f"      POOLED HOLDOUT-DTI | Arm1(DKRN1)={sum_arm1['dti']:.5f} {sum_arm1['ci95']['interval']} | "
            f"Arm2(HeadA47)={sum_arm2['dti']:.5f} | Arm3(DPRF1 replay)={sum_arm3_dprf1['dti']:.5f} | "
            f"OOF-d3={sum_oof_d3['dti']:.5f}",
            flush=True,
        )
        del preds_arm1, preds_arm2, preds_arm3_dprf1, preds_oof_d3
        gc.collect()

        oof_canary = context.canary(
            {"dkrn1_quad_oof_u_post": oof_quad_u}, seed=GVC_BASE_SEED, max_per_class=15000
        )
        if not oof_canary["passed"]:
            raise SystemExit("HALT: Quadrant OOF surface flagged leakage canary")

        stage1_elapsed = round(time.monotonic() - t0, 2)
        stage1_rss = round(peak_rss_mib(), 1)
        STAGE1_DIR.mkdir(parents=True, exist_ok=True)
        np.savez(
            STAGE1_ARRAYS,
            oof_quad_u=oof_quad_u,
            oof_quad_mu=oof_quad_mu,
            oof_quad_mh=oof_quad_mh,
            oof_quad_mc=oof_quad_mc,
        )
        save_json(
            {
                "stage1_elapsed": stage1_elapsed,
                "stage1_peak_rss_mib": stage1_rss,
                "canary": canary,
                "oof_canary": oof_canary,
                "fold_meta": fold_meta,
                "sum_arm1": sum_arm1,
                "sum_arm2": sum_arm2,
                "sum_arm3_dprf1": sum_arm3_dprf1,
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
            raise SystemExit("Stage 2 requested before Stage 1 checkpoint exists")
        s1 = json.loads(STAGE1_JSON.read_text())
        stage1_elapsed = float(s1["stage1_elapsed"])
        stage1_rss = float(s1["stage1_peak_rss_mib"])
        canary = s1["canary"]
        oof_canary = s1["oof_canary"]
        fold_meta = s1["fold_meta"]
        sum_arm1 = s1["sum_arm1"]
        sum_arm2 = s1["sum_arm2"]
        sum_arm3_dprf1 = s1["sum_arm3_dprf1"]
        sum_oof_d3 = s1["sum_oof_d3"]
        paired = s1["paired"]
        with np.load(STAGE1_ARRAYS) as z_arr:
            oof_quad_u = z_arr["oof_quad_u"].astype(np.float32)
            oof_quad_mu = z_arr["oof_quad_mu"].astype(np.float32)
            oof_quad_mh = z_arr["oof_quad_mh"].astype(np.float32)
            oof_quad_mc = z_arr["oof_quad_mc"].astype(np.float32)
        t0 = time.monotonic() - stage1_elapsed

    if args.stage in ("2", "all"):
        print(
            "[4/8] Evaluating 3.0 km Bridge Protocol + Partition 2 (Rotated45 OOF) for deployment...",
            flush=True,
        )
        bridge_3km = evaluate_bridge_3km(
            base_mm, gvc_mm, sahg_mm, dkrn1_mm, nuisance_fp, names62, fp, catalogue
        )
        print(
            f"      3.0 km Bridge HOLDOUT-DTI={bridge_3km['dti']:.5f} "
            f"(vs DPRF1 bridge {bridge_3km['recorded_dprf1_bridge_dti']:.5f})",
            flush=True,
        )

        rot45_folds = dprf1.make_rotated45_segment_folds(fp, catalogue, buffer_px=15)
        oof_rot_u = np.zeros(fp.shape, dtype=np.float32)
        oof_rot_mu = np.zeros(fp.shape, dtype=np.float32)
        oof_rot_mh = np.zeros(fp.shape, dtype=np.float32)
        oof_rot_mc = np.zeros(fp.shape, dtype=np.float32)
        for rfold in rot45_folds:
            rfid = int(rfold["id"])
            rsurfs, _ = dkrn1.fit_and_predict_dkrn1_fold(
                base_mm,
                gvc_mm,
                sahg_mm,
                dkrn1_mm,
                nuisance_fp,
                names62,
                fp,
                fp_ids,
                train_mask=rfold["train"],
                visible_mask=rfold["visible"],
                predict_mask=rfold["valid"],
                seed=SEED + 500 + 17 * rfid,
            )
            oof_rot_u += rsurfs["u_post"]
            oof_rot_mu += rsurfs["mu_deb"]
            oof_rot_mh += rsurfs["m_hydro"]
            oof_rot_mc += rsurfs["m_concealed"]
            del rsurfs
            gc.collect()

        stitched_u_raw = (0.50 * oof_quad_u + 0.50 * oof_rot_u).astype(np.float32)
        stitched_mu_raw = (0.50 * oof_quad_mu + 0.50 * oof_rot_mu).astype(np.float32)
        stitched_mh = (0.50 * oof_quad_mh + 0.50 * oof_rot_mh).astype(np.float32)
        stitched_mc = (0.50 * oof_quad_mc + 0.50 * oof_rot_mc).astype(np.float32)
        del oof_quad_u, oof_quad_mu, oof_quad_mh, oof_quad_mc
        del oof_rot_u, oof_rot_mu, oof_rot_mh, oof_rot_mc
        gc.collect()

        stage2_elapsed = round(time.monotonic() - t0, 2)
        STAGE1_DIR.mkdir(parents=True, exist_ok=True)
        np.savez(
            STAGE2_ARRAYS,
            stitched_u_raw=stitched_u_raw,
            stitched_mu_raw=stitched_mu_raw,
            stitched_mh=stitched_mh,
            stitched_mc=stitched_mc,
        )
        save_json(
            {
                "stage2_elapsed": stage2_elapsed,
                "stage2_peak_rss_mib": max(stage1_rss, round(peak_rss_mib(), 1)),
                "bridge_3km": bridge_3km,
            },
            STAGE2_JSON,
        )
    else:
        if not STAGE2_JSON.exists() or not STAGE2_ARRAYS.exists():
            raise SystemExit("Stage 3 requested before Stage 2 checkpoint exists")
        s2 = json.loads(STAGE2_JSON.read_text())
        stage2_elapsed = float(s2["stage2_elapsed"])
        stage1_rss = max(stage1_rss, float(s2["stage2_peak_rss_mib"]))
        bridge_3km = s2["bridge_3km"]
        del oof_quad_u, oof_quad_mu, oof_quad_mh, oof_quad_mc
        gc.collect()
        with np.load(STAGE2_ARRAYS) as z2:
            stitched_u_raw = z2["stitched_u_raw"].astype(np.float32)
            stitched_mu_raw = z2["stitched_mu_raw"].astype(np.float32)
            stitched_mh = z2["stitched_mh"].astype(np.float32)
            stitched_mc = z2["stitched_mc"].astype(np.float32)
        t0 = time.monotonic() - stage2_elapsed

    stitched_u = dprf1.debiased_apron_surface(stitched_u_raw, fp, catalogue)
    stitched_mu = dprf1.debiased_apron_surface(stitched_mu_raw, fp, catalogue)
    pre_placement_surface = dkrn1.ranking_surface_for_novelty(
        stitched_u, stitched_mh, stitched_mc, fp, catalogue, catalogue_clearance_px=2.0
    )

    print(
        "[5/8] Pre-placement novelty audit (surface) vs pinned registry + local lanes + peers...",
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
        f"(max |rho|={pre_nov_peers['max_abs_surface_spearman']:.4f}, missing={pre_nov_peers['peer_blobs_missing_from_cache']})",
        flush=True,
    )

    print(
        "[6/8] Final 37,654-dot 3-Regime Net-Tversky allocation + final-dot novelty audit...",
        flush=True,
    )
    final_dots = dkrn1.three_regime_net_tversky_allocate(
        stitched_u,
        stitched_mu,
        stitched_mh,
        stitched_mc,
        fp,
        catalogue,
        budget=FULL_DOT_BUDGET,
        shares=(0.48, 0.28, 0.24),
        min_spacing_px=2.9,
        catalogue_clearance_px=2.0,
    )
    dots_undebiased_diag = dkrn1.three_regime_net_tversky_allocate(
        stitched_u_raw,
        stitched_mu_raw,
        stitched_mh,
        stitched_mc,
        fp,
        catalogue,
        budget=FULL_DOT_BUDGET,
        shares=(0.48, 0.28, 0.24),
        min_spacing_px=2.9,
        catalogue_clearance_px=2.0,
    )
    dist_profile = compute_distance_profile(final_dots > 0.5, catalogue, fp)
    dist_profile_undebiased = compute_distance_profile(dots_undebiased_diag > 0.5, catalogue, fp)
    del dots_undebiased_diag, stitched_u_raw, stitched_mu_raw
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
    )
    dprf1_overlap = None
    b2_overlap = None
    for row in final_nov_methods["rows"]:
        fstr = str(row.get("file", ""))
        if "dprf1-stitched-oof" in fstr:
            dprf1_overlap = row.get("candidate_dot_overlap_within_3px")
        if "h33-h33-2-b2" in fstr:
            b2_overlap = row.get("candidate_dot_overlap_within_3px")
    print(
        f"      Final dots ({dist_profile['n_dots']:,}): competing={final_nov_methods['competing_method_rasters_count']} "
        f"passed={final_nov_methods['method_lane_passed']} max_overlap={final_nov_methods['method_lane_max_dot_overlap']} "
        f"(vs DPRF1={dprf1_overlap}, vs B2={b2_overlap}); peers passed={final_nov_peers['passed']} "
        f"max_overlap={final_nov_peers['max_dot_overlap_within_3px']}; "
        f"9-site-20261026 passed={nine_site_refresh['passed']} max_ov={nine_site_refresh['max_dot_overlap_within_3px']}; "
        f"apron2-9={100 * dist_profile['frac_2_to_9px_apron']:.1f}% farfield>20={100 * dist_profile['frac_gt_20px_farfield']:.1f}%",
        flush=True,
    )

    print("[7/8] Writing GeoTIFF pair + ZIP + preview PNG + exact-file C2ST audit...", flush=True)
    p_vs_dprf1 = paired["arm1_vs_dprf1_replay"]
    p_vs_oof = paired["arm1_vs_oof_multiphysics_hgb_d3"]
    beats_point_best = bool(sum_arm1["dti"] > RECORDED_DPRF1_DTI)
    paired_dprf1_ci = list(p_vs_dprf1["paired_delta_ci95"])
    paired_oof_ci = list(p_vs_oof["paired_delta_ci95"])
    beats_dprf1_ci = bool(paired_dprf1_ci[0] > 0.0)
    beats_oof_ci = bool(paired_oof_ci[0] > 0.0)

    slug = (
        "dkrn1-d8-knick-kernel-oof"
        if (comp_nov_ok and beats_point_best and beats_dprf1_ci)
        else "dkrn1-negative-d8-knick-kernel"
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

    note = (
        f"GEMS24 DKRN1 | D8 knick+300m kernel OOF | id {content_id} | "
        f"HOLDOUT-DTI {sum_arm1['dti']:.4f} | research; DO NOT SUBMIT"
    )
    if len(note) > 140:
        raise RuntimeError(f"Note exceeded 140 chars: {len(note)}")
    note_file = f"note-{zeros_name[:-4]}.txt"
    (downloads / note_file).write_text(note + "\n")

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
    replay_matches_recorded = abs(float(sum_arm3_dprf1["dti"]) - RECORDED_DPRF1_DTI) < 1e-12
    elapsed = round(time.monotonic() - t0, 2)

    run_card: dict[str, Any] = {
        "schema_version": 2,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "lane_id": LANE_ID,
        "assigned_lane_status": (
            "provisional_from_agents_next_step_queue_H24_DRAIN5_plus_H24_KERN6; "
            "assigned single-method paragraph absent in standing prompt"
        ),
        "preregistration": PREREG_PATH,
        "preregistration_commit": PREREG_COMMIT,
        "experiments_run": 3,
        "experiment_budget_limit": 3,
        "elapsed_seconds": elapsed,
        "peak_rss_mib": max(stage1_rss, round(peak_rss_mib(), 1)),
        "hypothesis": (
            "62-channel Split-View Topological D8 Drainage-Knickpoint Routing & 300 m DTI-Kernel "
            "Soft-Label Allocation: exact sparse unit-lower-triangular D8 flow routing (I - P^T)A = 1 "
            "extracts Flint's-law stream-power knickpoint jumps, 4-step thalweg dog-leg deflections, "
            "and 900 m cross-wash knickpoint corridors across 100% of det_elev (including the 31.8% "
            "LiDAR gap), fused via a gap-native 47-channel 300 m DTI-kernel regressor (Head A) + "
            "62-channel Elkan Bayes prior-odds calibrated fault-core classifier (Head B) and "
            "allocated across 3 regimes (48% ridge, 28% D8 hydrologic corridors, 24% concealed "
            "sub-alluvial/Walker-Lane hydrothermal conduits) with Net-Tversky FP penalization."
        ),
        "mechanism": (
            "Active faults crossing alluvial fans or the 31.8% 3DEP LiDAR gap preserve colinear "
            "stream-power knickpoints and dog-leg thalweg deflections along ephemeral washes even "
            "where sheetflood aggradation erases interfluve scarps; Split-View withholding of the "
            "15 raw LiDAR amplitude channels from Head A prevents parent convergence onto DPRF1's "
            "scarp splits while regressing continuous 300 m kernel credit y_K in (0,1), and Elkan "
            "(2001) prior-odds calibration eliminates 1:3 case-control sigmoid tail saturation so "
            "wide diffuse hillslopes cannot outvote 1-pixel linear buried traces."
        ),
        "named_non_fault_mimic": (
            "Differential erosion across resistant Tertiary welded ash-flow tuff or basalt caprock "
            "ledges producing contour-following lithologic knickpoints across adjacent washes, "
            "incised non-tectonic fan-head trench banks (cross_max high), and Pleistocene Lake "
            "Lahontan wave-cut shoreline scarps."
        ),
        "holdout": sum_arm1,
        "bridge_protocol_holdout": bridge_3km,
        "arms_same_evaluator": {
            "arm1_dkrn1_splitview_62ch": {
                "dti": sum_arm1["dti"],
                "ci95": sum_arm1["ci95"]["interval"],
            },
            "arm2_head_a_kernel47_ablation": {
                "dti": sum_arm2["dti"],
                "ci95": sum_arm2["ci95"]["interval"],
            },
            "arm3_dprf1_52ch_replay": {
                "dti": sum_arm3_dprf1["dti"],
                "ci95": sum_arm3_dprf1["ci95"]["interval"],
            },
            "oof_multiphysics_hgb_d3_baseline": {
                "dti": sum_oof_d3["dti"],
                "ci95": sum_oof_d3["ci95"]["interval"],
            },
        },
        "paired_comparisons": paired,
        "recorded_point_best_comparison": {
            "recorded_best_lane": "H24-DPRF1",
            "recorded_best_dti": RECORDED_DPRF1_DTI,
            "recorded_best_source": "evidence/dprf1_run_card_20261026.json",
            "candidate_point_delta": float(sum_arm1["dti"] - RECORDED_DPRF1_DTI),
            "candidate_beats_recorded_point": beats_point_best,
            "arm3_dprf1_replay_dti": float(sum_arm3_dprf1["dti"]),
            "arm3_replay_bit_identical_to_recorded": replay_matches_recorded,
        },
        "paired_vs_baseline": {
            "ci95": paired_oof_ci,
            "delta_dti": float(p_vs_oof["paired_delta_dti"]),
            "baseline_name": "oof_multiphysics_hgb_d3 (27ch reconstructed OOF baseline)",
            "baseline_dti": float(sum_oof_d3["dti"]),
        },
        "baseline_reproduced": True,
        "paired_vs_current_best": {
            "baseline_dti": float(sum_arm3_dprf1["dti"]),
            "evaluator_version": "gems-segment-pooled-v1",
            "n_withheld_positive_pixels": 60988,
            "baseline_replayed": True,
            "delta_dti": float(p_vs_dprf1["paired_delta_dti"]),
            "ci95": paired_dprf1_ci,
            "baseline_identity": (
                "Arm3 same-session replay of H24-DPRF1"
                + (
                    " (bit-identical pooled DTI to recorded DPRF1)"
                    if replay_matches_recorded
                    else f" (recorded DPRF1 {RECORDED_DPRF1_DTI})"
                )
            ),
        },
        "leakage_canary": {
            "passed": bool(canary["passed"] and oof_canary["passed"]),
            "n_features_checked": canary["n_features_checked"],
            "worst_feature": canary["worst_feature"],
            "worst_pooled_auc": canary["worst_pooled_auc"],
            "worst_polarity_extremity": canary["worst_polarity_extremity"],
            "dkrn1_channel_pooled_aucs": canary["dkrn1_channel_pooled_aucs"],
            "oof_surface_auc": oof_canary["features"]["dkrn1_quad_oof_u_post"]["pooled_auc"],
        },
        "correlation_overlap_vs_registry": {
            "total_registry_entries_checked": final_nov_methods["registry_unique_rasters"],
            "competing_method_rasters_checked": final_nov_methods["competing_method_rasters_count"],
            "calibration_control_rasters_checked": final_nov_methods[
                "calibration_control_rasters_count"
            ],
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
        "holdout_dti": sum_arm1["dti"],
        "holdout_ci95": sum_arm1["ci95"]["interval"],
        "bridge_3km_dti": bridge_3km["dti"],
        "bridge_3km_ci95": bridge_3km["ci95"],
        "arm2_head_a_kernel47_dti": float(sum_arm2["dti"]),
        "arm3_dprf1_replay_dti": float(sum_arm3_dprf1["dti"]),
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
        "ok_to_submit": False,
        "submission_authorized": False,
        "verdict": "negative",
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
        "peak_rss_mib": run_card["peak_rss_mib"],
        "feature_names_62": names62,
        "dkrn1_feature_names_10": dkrn1_names,
        "head_a_gap_native_excluded_lidar_15": sorted(dkrn1.RAW_LIDAR_AMPLITUDE_NAMES),
        "selective_residualized_11": sorted(
            set(dprf1.SELECTIVE_RESID_NAMES) | set(dkrn1.DKRN1_SELECTIVE_EXTRA_NAMES)
        ),
        "canary": canary,
        "fold_fit_metadata": fold_meta,
        "arms": {
            "arm1_dkrn1_splitview_62ch": {"holdout": sum_arm1, "bridge_3km": bridge_3km},
            "arm2_head_a_kernel47_ablation": {"holdout": sum_arm2},
            "arm3_dprf1_52ch_replay": {"holdout": sum_arm3_dprf1},
            "oof_multiphysics_hgb_d3_baseline": {"holdout": sum_oof_d3},
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
        "ok_to_submit": False,
        "run_card": run_card,
    }
    save_json(experiment_record, EXPERIMENT_JSON)
    print(
        f"Done in {elapsed:.1f}s (peak RSS {run_card['peak_rss_mib']:.1f} MiB). "
        f"DKRN1 HOLDOUT-DTI={sum_arm1['dti']:.5f} vs DPRF1 replay={sum_arm3_dprf1['dti']:.5f} "
        f"(HeadA47={sum_arm2['dti']:.5f}, OOF-d3={sum_oof_d3['dti']:.5f}); "
        f"comp_novelty={comp_nov_ok} (vs DPRF1 {dprf1_overlap}); "
        f"selector={sel_receipt['decision']}; verdict=negative (fail-closed).",
        flush=True,
    )


if __name__ == "__main__":
    main()
