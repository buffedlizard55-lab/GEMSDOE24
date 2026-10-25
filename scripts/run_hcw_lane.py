#!/usr/bin/env python3
"""Execute the preregistered H24-FUSE lane (RAW, RESID, HCW arms) under SegmentHoldout.

Implements the documented Next Step #4 from README.md and knowledge/17_preregistered_FUSE_2026-10-25.md:
1. Fold-local 31-channel HistGradientBoostingClassifier (27 prepared base channels +
   4 SAHG1 physical conduit channels: G_sat, R_alt, B_step, H_conduit) inside the
   verified 9x9 discrete receptive-field support mask.
2. Three preregistered arms evaluated on SegmentHoldout (gems-segment-pooled-v1,
   60,988 withheld positives, 3,199 components, 1.5 km collar, 1,999 block-bootstrap draws):
   - H24-FUSE-RAW: unresidualized 31-channel OOF-HGB + Poisson-disk d=3 emission
   - H24-FUSE-RESID: training-only NuisanceResidualizer (road_m, claim_m, block_1..4)
     fitted strictly on a uniform 30,000-pixel fold-train sample + 31-channel OOF-HGB
   - H24-FUSE-HCW: residualized OOF-HGB probability weighted by hydrothermal-basement
     conduit factor (0.25 + 0.75*H_conduit)*(0.30 + 0.70*G_sat) to prioritize
     hydrothermally corroborated fault segments and decorrelate from pure scarp ridges.
3. Memory-frugal 75,000-row chunked inference (<1.8 GB RSS on 3.8 GB CPU instances).
4. Leakage canaries (both polarities), prospective + literal registry novelty checks
   (46 priority rasters + 5 session rasters + 84 peer blobs), exact-file C2ST nuisance
   audit, and fail-closed exact-file preflight receipt.
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import os
import struct
import subprocess
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
from gems.residualize import NuisanceResidualizer  # noqa: E402
from gems.validator import sha256_file  # noqa: E402

BUDGET_FRACTION = 0.0073
ASPC_BUDGET = 37654
SEED = 20261025
CHUNK_SIZE = 75000
HGB_PARAMS = dict(
    max_iter=80,
    max_leaf_nodes=15,
    learning_rate=0.08,
    l2_regularization=5.0,
    early_stopping=False,
    random_state=SEED,
)

EXPERIMENT_JSON = ROOT / "evidence/hcw_experiment_20261025.json"
RUN_CARD_JSON = ROOT / "evidence/hcw_run_card_20261025.json"
DOCS_RUN_CARD = ROOT / "docs/data/hcw_run_card.json"
DOCS_DOWNLOAD_JSON = ROOT / "docs/data/hcw_download.json"
PREVIEW_PATH = ROOT / "docs/assets/fuse-preview.png"


def save_json(obj: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n")


def write_preview_png(dots: np.ndarray, fp: np.ndarray, dest: Path, step: int = 8) -> None:
    """Write a dependency-free RGB PNG preview of footprint and emitted dots."""
    h, w = fp.shape
    oh, ow = (h + step - 1) // step, (w + step - 1) // step
    rgb = np.zeros((oh, ow, 3), dtype=np.uint8)
    rgb[:] = (15, 23, 42)
    fp_sub = fp[: oh * step, : ow * step]
    for dy in range(step):
        for dx in range(step):
            sub = fp_sub[dy::step, dx::step]
            rgb[: sub.shape[0], : sub.shape[1]][sub] = (30, 41, 59)
    for dy in range(step):
        for dx in range(step):
            sub = dots[dy::step, dx::step]
            rgb[: sub.shape[0], : sub.shape[1]][sub] = (52, 211, 153)

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


def build_engineered_features(fp: np.ndarray) -> tuple[dict[str, np.ndarray], np.ndarray, dict]:
    """Load verified physical rasters, compute SAHG1 surfaces, and free intermediate 2D arrays."""
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

    surfaces, support = sahg1.build_surfaces(
        lidar_bands, rad_bands, ext_bands, geophys_bands, fp
    )
    del lidar_bands, rad_bands, ext_bands, geophys_bands
    gc.collect()

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
    return surfaces, support, hashes


def load_nuisance_matrix(fp: np.ndarray) -> tuple[np.ndarray, list[str], dict]:
    """Load strict non-geological nuisance features (road_m, claim_m, block_1..4) on footprint."""
    prov = confounds.build_all(force=False)
    with np.load(confounds.CONF / "confounds.npz") as npz:
        cfeat = confounds.classifier_features(npz)
    if "road_m" not in cfeat or "claim_m" not in cfeat:
        raise SystemExit("Strict road_m and claim_m nuisance distances required")
    ckeys = ["road_m", "claim_m"] + sorted(set(cfeat) - {"road_m", "claim_m"})
    fp_ids = np.flatnonzero(fp)
    C = np.column_stack([cfeat[k].ravel()[fp_ids] for k in ckeys]).astype(np.float32)
    del cfeat
    gc.collect()
    if not np.isfinite(C).all():
        raise SystemExit("Non-finite nuisance values inside footprint")
    return C, ckeys, prov


def extra_session_entries(fp: np.ndarray) -> list[dict]:
    """Include earlier 2026-10-25 GEMSDOE24 rasters in registry novelty checks."""
    extras = []
    candidates = (
        "docs/downloads/gems24-aspc-20261025-6393e9d9b0df-RESEARCH-NOT-SUBMISSION-zeros.tif",
        "docs/downloads/gems24-mtr1-negative-paired-trough-20261025-ed7243e6d163-zeros.tif",
        "docs/downloads/gems24-sahg1-strike-hydro-geomorph-20261025-13d01f28d5db-zeros.tif",
        "docs/downloads/gems24-con-claycap-strain-saddle-20261025-ded121060878-zeros.tif",
        "docs/downloads/24gems-doer-fault-guided-k-20261025T220208Z-dedb860f7e83-zeros.tif",
    )
    for idx, rel in enumerate(candidates, start=1):
        p = ROOT / rel
        if not p.exists():
            continue
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


def check_peer_blobs(surface: np.ndarray, dots: np.ndarray, fp: np.ndarray) -> dict:
    """Check all competition-grid blobs in registry/peer_rasters_20261025.json."""
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
        d_rho = novelty.rank_correlation(dot_ranks, a[fp])
        ov = novelty.dot_overlap(dots, fp & np.isfinite(a) & (a > 0))[
            "candidate_within_3px_of_reference"
        ]
        if s_rho is not None:
            max_surf_rho = max(max_surf_rho, abs(s_rho))
        if d_rho is not None:
            max_dot_rho = max(max_dot_rho, abs(d_rho))
        if ov is not None and float(ov) > max_overlap:
            max_overlap = float(ov)
            max_overlap_file = f"{row['repo']}:{row['path']}"
    return {
        "peer_unique_blobs_checked": checked,
        "max_abs_surface_spearman": max_surf_rho,
        "max_abs_dot_spearman": max_dot_rho,
        "max_dot_overlap_within_3px": max_overlap,
        "max_overlap_peer_artifact": max_overlap_file,
        "passed": checked > 0
        and max_surf_rho <= 0.90
        and max_dot_rho <= 0.90
        and max_overlap <= 0.70,
    }


def evaluate_bridge_protocol(
    surface: np.ndarray,
    fp: np.ndarray,
    catalogue: np.ndarray,
    support: np.ndarray,
) -> dict:
    """Evaluate candidate surface on the 3 km / 20 km tile protocol used by ASPC."""
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
        "delta_vs_recorded_aspc": val - float(aspc_report["holdout"]["value"]),
    }


def run_c2st_audit(
    dots_map: dict[str, np.ndarray], catalogue: np.ndarray, fp: np.ndarray
) -> dict:
    """Run C2ST nuisance audit (labels first, then emitted candidates) on road/claim/4-block confounds."""
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
    cand_results = {}
    p_list = [label_res.p_value]
    keys = list(dots_map.keys())
    for k in keys:
        res = c2s2.c2s2_test(
            k,
            dots_map[k],
            cfeat,
            fold_grid,
            fp,
            n_per_class=8000,
            n_null=99,
            seed=SEED,
        )
        cand_results[k] = res
        p_list.append(res.p_value)
    adj_p = c2s2.holm_adjust(p_list)
    out = {
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
        "candidates": {},
    }
    for idx, k in enumerate(keys, start=1):
        r = cand_results[k]
        hp = adj_p[idx]
        flagged = bool(hp <= 0.05 and r.observed_auc >= 0.55 and r.margin_vs_p95 >= 0.02)
        out["candidates"][k] = {
            "observed_auc": r.observed_auc,
            "fold_aucs": r.fold_aucs,
            "null_p95": r.null_auc_p95,
            "margin_vs_p95": r.margin_vs_p95,
            "raw_p_value": r.p_value,
            "holm_p_value": hp,
            "strict_gate_flagged": flagged,
            "strict_gate_passed": not flagged,
        }
    return out


def verify_recorded() -> dict:
    exp = json.loads(EXPERIMENT_JSON.read_text())
    card = json.loads(RUN_CARD_JSON.read_text())
    dl = json.loads(DOCS_DOWNLOAD_JSON.read_text())
    template = ROOT / "data/bridge/sample_submission.tif"
    z_path = ROOT / "docs/downloads" / card["submission_name"]
    n_path = ROOT / "docs/downloads" / card["nan_outside_artifact"]
    if sha256_file(z_path) != card["raster_sha256"] or dl["sha256"] != card["raster_sha256"]:
        raise ValueError("FUSE primary TIFF checksum mismatch")
    checks = json.loads((ROOT / "docs/downloads" / dl["checks_file"]).read_text())
    if (
        sha256_file(z_path) != checks["zero_outside"]["sha256"]
        or sha256_file(n_path) != checks["nan_outside"]["sha256"]
    ):
        raise ValueError("FUSE variant checksum mismatch")
    for k in ("zero_outside", "nan_outside"):
        c = submission.check_variants(ROOT / "docs/downloads" / checks[k]["file"], template)
        if not c["format_valid"] or c["ok_to_upload"] or c["submission_authorized"]:
            raise ValueError(f"FUSE validator check failed for {k}")
    if card["verdict"] != "negative" or card["ok_to_submit"] or dl["ok_to_submit"]:
        raise ValueError("FUSE fail-closed verdict was weakened")
    return {
        "verified": True,
        "experiment_rerun": False,
        "submission_name": card["submission_name"],
        "raster_sha256": card["raster_sha256"],
        "holdout_dti": card["holdout"]["dti"],
        "ci95": card["holdout"]["ci95"]["interval"],
        "fuse_raw_dti": exp["arms"]["fuse_raw"]["holdout"]["dti"],
        "fuse_resid_dti": exp["arms"]["fuse_resid"]["holdout"]["dti"],
        "fuse_hcw_dti": exp["arms"]["fuse_hcw"]["holdout"]["dti"],
        "method_lane_novelty_passed": card["correlation_overlap_vs_registry"]["method_lane_passed"],
        "literal_all_entries_passed": card["correlation_overlap_vs_registry"][
            "literal_all_entries_passed"
        ],
        "verdict": card["verdict"],
        "ok_to_submit": card["ok_to_submit"],
        "experiments_run": card["experiments_run"],
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
            "H24-FUSE experiment already recorded. No implicit rerun/tuning; use --verify-recorded."
        )

    started = time.monotonic()
    fp = footprint.load_footprint()
    fp_ids = np.flatnonzero(fp)
    template = ROOT / "data/bridge/sample_submission.tif"
    with rasterio.open(ROOT / "data/bridge/labels.tif") as ds:
        catalogue = (ds.read(1) > 0) & fp

    print("1. Building SAHG1 engineered physical surfaces and verifying 9x9 support...", flush=True)
    surfaces, support, input_hashes = build_engineered_features(fp)
    g_strike = surfaces["strike_scarp_g_strike"]
    g_sat = surfaces["saturating_scarp_g_sat"]
    r_alt = surfaces["radiometric_alteration_r_alt"]
    b_step = surfaces["basement_step_b_step"]
    h_conduit = surfaces["hydrothermal_conduit_h"]

    # Extract compact footprint vectors (5167373 x 4 float32 = 82 MB)
    eng_names = ["G_sat", "R_alt", "B_step", "H_conduit"]
    X_eng_fp = np.column_stack(
        [
            np.nan_to_num(g_sat.ravel()[fp_ids], nan=0.0),
            np.nan_to_num(r_alt.ravel()[fp_ids], nan=0.0),
            np.nan_to_num(b_step.ravel()[fp_ids], nan=0.0),
            np.nan_to_num(h_conduit.ravel()[fp_ids], nan=0.0),
        ]
    ).astype(np.float32)

    # Conduit weighting factor for Arm 3 (FUSE-HCW):
    hcw_weight_2d = np.where(
        support,
        (0.25 + 0.75 * h_conduit) * (0.30 + 0.70 * g_sat),
        0.0,
    ).astype(np.float32)

    print("2. Setting up SegmentHoldout and running leakage canaries...", flush=True)
    context = holdout.SegmentHoldout(fp, catalogue, buffer_px=15)
    canary_features = {
        "strike_scarp_g_strike": g_strike,
        "saturating_scarp_g_sat": g_sat,
        "radiometric_alteration_r_alt": r_alt,
        "basement_step_b_step": b_step,
        "hydrothermal_conduit_h": h_conduit,
        "hcw_conduit_weight": hcw_weight_2d,
    }
    canary_report = context.canary(canary_features, seed=SEED)
    del surfaces, g_strike, g_sat, r_alt, b_step, h_conduit
    gc.collect()
    if not canary_report["passed"]:
        raise SystemExit(f"Leakage canary failed: {json.dumps(canary_report, indent=2)}")
    print("   Leakage canary PASSED (all features within [0.10, 0.90]).", flush=True)

    print("3. Loading nuisance matrix and prepared 27-channel stack...", flush=True)
    C_fp, nuisance_keys, nuisance_prov = load_nuisance_matrix(fp)
    prep_meta = json.loads((ROOT / "data/prepared/features.json").read_text())
    base_nc = int(prep_meta["base_count"])
    stack = np.load(ROOT / "data/prepared/features.npy", mmap_mode="r")

    oof_raw = np.zeros(fp.shape, dtype=np.float32)
    oof_resid = np.zeros(fp.shape, dtype=np.float32)
    oof_hcw = np.zeros(fp.shape, dtype=np.float32)
    preds_raw, preds_resid, preds_hcw, preds_base = [], [], [], []

    print("4. Running fold-local OOF training & chunked inference across 4 quadrants...", flush=True)
    with threadpool_limits(limits=2):
        for fold in context.folds:
            fid = int(fold["id"])
            fname = str(fold["name"])
            rng = np.random.default_rng(SEED + fid)
            # Visible catalogue only! Never read hidden components for negative distance buffer.
            dist_visible = distance_transform_edt(~fold["visible"])
            pos_mask = fold["train"] & fold["visible"]
            neg_mask = fold["train"] & ~fold["visible"] & (dist_visible >= 9)
            del dist_visible

            pos_ids = np.flatnonzero(pos_mask.ravel()[fp_ids])
            neg_ids = np.flatnonzero(neg_mask.ravel()[fp_ids])
            pos_sel = rng.choice(pos_ids, min(20000, len(pos_ids)), replace=False)
            neg_sel = rng.choice(neg_ids, min(60000, len(neg_ids)), replace=False)
            train_sel = np.r_[pos_sel, neg_sel]
            y_train = np.r_[np.ones(len(pos_sel), np.int8), np.zeros(len(neg_sel), np.int8)]

            # Baseline 27-channel model (reproducing oof_multiphysics_hgb_d3 for paired bootstrap)
            X_train_base = np.asarray(stack[train_sel, :base_nc], dtype=np.float32)
            model_base = HistGradientBoostingClassifier(**HGB_PARAMS).fit(X_train_base, y_train)

            # Arm 1: FUSE-RAW (31 channels)
            X_train_31 = np.hstack([X_train_base, X_eng_fp[train_sel]])
            del X_train_base
            model_raw = HistGradientBoostingClassifier(**HGB_PARAMS).fit(X_train_31, y_train)

            # Arm 2: FUSE-RESID (training-only NuisanceResidualizer on uniform 30,000 train sample)
            train_fp_pool = np.flatnonzero(fold["train"].ravel()[fp_ids])
            u_rng = np.random.default_rng(SEED + 100 + fid)
            u_sel = u_rng.choice(train_fp_pool, min(30000, len(train_fp_pool)), replace=False)
            X_u_31 = np.hstack([np.asarray(stack[u_sel, :base_nc], dtype=np.float32), X_eng_fp[u_sel]])
            resid = NuisanceResidualizer(distance_columns=2, alpha=100.0).fit(C_fp[u_sel], X_u_31)
            del X_u_31
            X_train_resid = resid.transform(C_fp[train_sel], X_train_31, remove=True)
            del X_train_31
            model_resid = HistGradientBoostingClassifier(**HGB_PARAMS).fit(X_train_resid, y_train)
            del X_train_resid

            # Predict on fold["valid"] in 75k chunks
            val_ids = np.flatnonzero(fold["valid"].ravel()[fp_ids])
            f_base = np.zeros(fp.shape, dtype=np.float32)
            f_raw = np.zeros(fp.shape, dtype=np.float32)
            f_resid = np.zeros(fp.shape, dtype=np.float32)

            for begin in range(0, len(val_ids), CHUNK_SIZE):
                ch = val_ids[begin : begin + CHUNK_SIZE]
                X_ch_base = np.asarray(stack[ch, :base_nc], dtype=np.float32)
                p_b = model_base.predict_proba(X_ch_base)[:, 1].astype(np.float32)
                X_ch_31 = np.hstack([X_ch_base, X_eng_fp[ch]])
                del X_ch_base
                p_r = model_raw.predict_proba(X_ch_31)[:, 1].astype(np.float32)
                X_ch_res = resid.transform(C_fp[ch], X_ch_31, remove=True)
                del X_ch_31
                p_res = model_resid.predict_proba(X_ch_res)[:, 1].astype(np.float32)
                del X_ch_res

                grid_ch = fp_ids[ch]
                f_base.ravel()[grid_ch] = p_b
                f_raw.ravel()[grid_ch] = p_r
                f_resid.ravel()[grid_ch] = p_res
                oof_raw.ravel()[grid_ch] = p_r
                oof_resid.ravel()[grid_ch] = p_res

            f_hcw = (f_resid * hcw_weight_2d).astype(np.float32)
            oof_hcw += np.where(fold["valid"], f_hcw, 0.0)

            eligible = support & fold["valid"] & ~fold["visible"]
            budget = round(BUDGET_FRACTION * int(fold["valid"].sum()))
            preds_base.append(emission.priority_poisson(f_base, eligible, budget, min_dist=3))
            preds_raw.append(emission.priority_poisson(f_raw, eligible, budget, min_dist=3))
            preds_resid.append(emission.priority_poisson(f_resid, eligible, budget, min_dist=3))
            preds_hcw.append(emission.priority_poisson(f_hcw, eligible, budget, min_dist=3))
            del f_base, f_raw, f_resid, f_hcw
            gc.collect()
            print(f"   Completed fold {fname} (budget={budget})", flush=True)

    print("5. Summarizing HOLDOUT-DTI and paired block-bootstrap comparisons...", flush=True)
    sum_base = context.summarize(preds_base)
    sum_raw = context.summarize(preds_raw)
    sum_resid = context.summarize(preds_resid)
    sum_hcw = context.summarize(preds_hcw)

    yy, xx = np.nonzero(fp)
    nx = (fp.shape[1] + 99) // 100
    active_blocks = np.unique((yy // 100) * nx + xx // 100)

    def active_block_matrix(preds: list[np.ndarray]) -> np.ndarray:
        return np.sum(
            [context.score_fold(p, f)[1] for p, f in zip(preds, context.folds)], axis=0
        )[active_blocks]

    tiles_base = active_block_matrix(preds_base)
    tiles_raw = active_block_matrix(preds_raw)
    tiles_resid = active_block_matrix(preds_resid)
    tiles_hcw = active_block_matrix(preds_hcw)

    def paired_ci(tiles_a: np.ndarray, dti_a: float, tiles_b: np.ndarray, dti_b: float) -> dict:
        return {
            "delta_dti": float(dti_a - dti_b),
            "ci95": holdout.pooled_bootstrap(tiles_a, paired=tiles_b, resamples=1999, seed=SEED),
        }

    paired_comparisons = {
        "fuse_raw_minus_oof_base": paired_ci(tiles_raw, sum_raw["dti"], tiles_base, sum_base["dti"]),
        "fuse_resid_minus_oof_base": paired_ci(
            tiles_resid, sum_resid["dti"], tiles_base, sum_base["dti"]
        ),
        "fuse_hcw_minus_oof_base": paired_ci(tiles_hcw, sum_hcw["dti"], tiles_base, sum_base["dti"]),
        "fuse_resid_minus_fuse_raw": paired_ci(
            tiles_resid, sum_resid["dti"], tiles_raw, sum_raw["dti"]
        ),
    }
    print(
        f"   OOF-Base:   {sum_base['dti']:.5f} {sum_base['ci95']['interval']}\n"
        f"   FUSE-RAW:   {sum_raw['dti']:.5f} {sum_raw['ci95']['interval']} (delta={paired_comparisons['fuse_raw_minus_oof_base']['delta_dti']:+.5f})\n"
        f"   FUSE-RESID: {sum_resid['dti']:.5f} {sum_resid['ci95']['interval']} (delta={paired_comparisons['fuse_resid_minus_oof_base']['delta_dti']:+.5f})\n"
        f"   FUSE-HCW:   {sum_hcw['dti']:.5f} {sum_hcw['ci95']['interval']} (delta={paired_comparisons['fuse_hcw_minus_oof_base']['delta_dti']:+.5f})",
        flush=True,
    )

    print("6. Fitting full-footprint models to emit final candidate dot sets...", flush=True)
    with threadpool_limits(limits=2):
        rng_full = np.random.default_rng(SEED + 99)
        dist_cat = distance_transform_edt(~catalogue)
        pos_full = np.flatnonzero((catalogue & fp).ravel()[fp_ids])
        neg_full = np.flatnonzero((fp & ~catalogue & (dist_cat >= 9) & support).ravel()[fp_ids])
        del dist_cat
        pos_sel = rng_full.choice(pos_full, min(25000, len(pos_full)), replace=False)
        neg_sel = rng_full.choice(neg_full, min(75000, len(neg_full)), replace=False)
        train_sel = np.r_[pos_sel, neg_sel]
        y_full = np.r_[np.ones(len(pos_sel), np.int8), np.zeros(len(neg_sel), np.int8)]

        X_full_31 = np.hstack(
            [np.asarray(stack[train_sel, :base_nc], dtype=np.float32), X_eng_fp[train_sel]]
        )
        model_full_raw = HistGradientBoostingClassifier(**HGB_PARAMS).fit(X_full_31, y_full)

        u_full_rng = np.random.default_rng(SEED + 199)
        u_full_sel = u_full_rng.choice(len(fp_ids), min(40000, len(fp_ids)), replace=False)
        X_u_full = np.hstack(
            [np.asarray(stack[u_full_sel, :base_nc], dtype=np.float32), X_eng_fp[u_full_sel]]
        )
        resid_full = NuisanceResidualizer(distance_columns=2, alpha=100.0).fit(
            C_fp[u_full_sel], X_u_full
        )
        del X_u_full
        X_full_resid = resid_full.transform(C_fp[train_sel], X_full_31, remove=True)
        del X_full_31
        model_full_resid = HistGradientBoostingClassifier(**HGB_PARAMS).fit(X_full_resid, y_full)
        del X_full_resid

        sup_in_fp = np.flatnonzero(support.ravel()[fp_ids])
        p_full_raw = np.zeros(fp.shape, dtype=np.float32)
        p_full_resid = np.zeros(fp.shape, dtype=np.float32)
        for begin in range(0, len(sup_in_fp), CHUNK_SIZE):
            ch = sup_in_fp[begin : begin + CHUNK_SIZE]
            X_ch_31 = np.hstack(
                [np.asarray(stack[ch, :base_nc], dtype=np.float32), X_eng_fp[ch]]
            )
            pr = model_full_raw.predict_proba(X_ch_31)[:, 1].astype(np.float32)
            X_ch_res = resid_full.transform(C_fp[ch], X_ch_31, remove=True)
            del X_ch_31
            pres = model_full_resid.predict_proba(X_ch_res)[:, 1].astype(np.float32)
            del X_ch_res
            grid_ch = fp_ids[ch]
            p_full_raw.ravel()[grid_ch] = pr
            p_full_resid.ravel()[grid_ch] = pres

    del stack, X_eng_fp, C_fp
    gc.collect()

    p_full_hcw = np.clip(p_full_resid * hcw_weight_2d, 0.0, 1.0).astype(np.float32)
    full_budget = round(BUDGET_FRACTION * int(fp.sum()))
    eligible_final = support & ~catalogue

    dots_raw = emission.priority_poisson(p_full_raw, eligible_final, full_budget, min_dist=3)
    dots_resid = emission.priority_poisson(p_full_resid, eligible_final, full_budget, min_dist=3)
    dots_hcw = emission.priority_poisson(p_full_hcw, eligible_final, full_budget, min_dist=3)

    print("7. Running prospective + literal registry novelty checks on all 3 arms...", flush=True)
    registry_entries = json.loads((ROOT / "registry/priority_rasters.json").read_text())[
        "unique_rasters"
    ]
    extras = extra_session_entries(fp)

    nov_arms = {}
    for arm_key, surf, dts in (
        ("fuse_raw", p_full_raw, dots_raw),
        ("fuse_resid", p_full_resid, dots_resid),
        ("fuse_hcw", p_full_hcw, dots_hcw),
    ):
        surf_nov = novelty.compare_prospective_registry(
            surf, fp, registry_entries, ROOT, extra_entries=extras
        )
        dot_nov = novelty.compare_prospective_registry(
            surf, fp, registry_entries, ROOT, dots=dts, extra_entries=extras
        )
        peer_nov = check_peer_blobs(surf, dts, fp)
        nov_arms[arm_key] = {
            "surface": surf_nov,
            "dots": dot_nov,
            "peer": peer_nov,
            "method_lane_passed": bool(
                surf_nov["method_lane_passed"]
                and dot_nov["method_lane_passed"]
                and peer_nov["passed"]
            ),
            "literal_all_entries_passed": bool(
                surf_nov["literal_all_entries_passed"]
                and dot_nov["literal_all_entries_passed"]
                and peer_nov["passed"]
            ),
        }
        print(
            f"   Novelty [{arm_key}]: method_lane_passed={nov_arms[arm_key]['method_lane_passed']} "
            f"(max_method_overlap={dot_nov['method_lane_max_dot_overlap']:.4f}, "
            f"peer_max_overlap={peer_nov['max_dot_overlap_within_3px']:.4f}, "
            f"max_surf_rho={surf_nov['method_lane_max_abs_rank_correlation']:.4f})",
            flush=True,
        )

    print("8. Running exact-file C2ST nuisance audit across all 3 arms...", flush=True)
    c2st_report = run_c2st_audit(
        {"fuse_raw": dots_raw, "fuse_resid": dots_resid, "fuse_hcw": dots_hcw},
        catalogue,
        fp,
    )
    for k, v in c2st_report["candidates"].items():
        print(
            f"   C2ST [{k}]: AUC={v['observed_auc']:.4f}, null_p95={v['null_p95']:.4f}, "
            f"Holm_p={v['holm_p_value']:.3f}, passed={v['strict_gate_passed']}",
            flush=True,
        )

    # Select the packaged primary artifact according to preregistered rule:
    # Prefer the highest-HOLDOUT-DTI arm that passes prospective method-lane novelty;
    # if none passes, package fuse_hcw (lowest overlap) with negative verdict.
    arm_order = [
        ("fuse_raw", sum_raw, p_full_raw, dots_raw, oof_raw),
        ("fuse_resid", sum_resid, p_full_resid, dots_resid, oof_resid),
        ("fuse_hcw", sum_hcw, p_full_hcw, dots_hcw, oof_hcw),
    ]
    passing_method = [a for a in arm_order if nov_arms[a[0]]["method_lane_passed"]]
    if passing_method:
        selected_key, selected_sum, selected_surf, selected_dots, selected_oof = max(
            passing_method, key=lambda x: x[1]["dti"]
        )
    else:
        selected_key, selected_sum, selected_surf, selected_dots, selected_oof = min(
            arm_order, key=lambda x: nov_arms[x[0]]["dots"]["method_lane_max_dot_overlap"]
        )
    print(f"9. Packaging selected arm: {selected_key}...", flush=True)

    bridge_eval = evaluate_bridge_protocol(selected_oof, fp, catalogue, support)

    content_id = submission.scored_content_id(selected_dots, fp, catalogue)
    slug = f"fuse-{selected_key.replace('_', '-')}-hgb"
    z_name = submission.make_filename("gems24", slug, "20261025", content_id, "zeros")
    n_name = submission.make_filename("gems24", slug, "20261025", content_id, "nan")
    downloads = ROOT / "docs/downloads"
    z_path = submission.write_submission(
        selected_dots.astype(np.float32), template, downloads / z_name, outside="zero"
    )
    n_path = submission.write_submission(
        selected_dots.astype(np.float32), template, downloads / n_name, outside="nan"
    )
    checks = {
        "zero_outside": submission.check_variants(z_path, template),
        "nan_outside": submission.check_variants(n_path, template),
    }
    if not all(c["format_valid"] for c in checks.values()):
        raise SystemExit("FUSE submission variant failed exact-grid format check")

    checks_name = f"checks-{z_name[:-4]}.json"
    save_json(checks, downloads / checks_name)

    note = (
        f"GEMS24 FUSE ({selected_key.upper()}) | OOF-HGB + SAHG1 conduit | "
        f"research only; DO NOT SUBMIT | id {content_id}"
    )
    if len(note) > 140:
        note = note[:140]
    note_name = f"note-{z_name[:-4]}.txt"
    (downloads / note_name).write_text(note + "\n")
    write_preview_png(selected_dots, fp, PREVIEW_PATH)

    sel_nov = nov_arms[selected_key]
    sel_c2st = c2st_report["candidates"][selected_key]
    reasons = []
    if selected_sum["dti"] <= sum_base["dti"]:
        reasons.append(
            f"Selected arm {selected_key} did not beat reconstructed same-protocol OOF multi-physics baseline ({selected_sum['dti']:.5f} vs {sum_base['dti']:.5f})"
        )
    if not sel_nov["method_lane_passed"]:
        reasons.append(
            f"Prospective method-lane novelty failed (max 3-px dot overlap {sel_nov['dots']['method_lane_max_dot_overlap']:.4f} > 0.70)"
        )
    if not sel_nov["literal_all_entries_passed"]:
        reasons.append(
            "Literal all-entry overlap rule still flags synthetic spacing-5 calibration lattice registry-039 (1.0 overlap within 3 px), though competing method lanes and peer blobs are reported separately"
        )
    if not sel_c2st["strict_gate_passed"]:
        reasons.append(
            f"Exact-file C2ST nuisance audit flagged accessibility/block association (AUC {sel_c2st['observed_auc']:.4f}, Holm p={sel_c2st['holm_p_value']:.3f})"
        )
    reasons.append(
        "No single assigned method-lane paragraph was supplied in the prompt (provisional lane)"
    )
    reasons.append(
        "Promotion to a weekly competition slot requires a separate selector step within verified portal quota"
    )

    run_card = {
        "hypothesis": (
            "H24-FUSE fold-local 31-channel OOF-HGB fusing 27 multi-physics/LiDAR base channels with "
            "SAHG1 strike-projected scarp (G_sat), stable-Th K/U alteration (R_alt), basement/strain step "
            "(B_step), and hydrothermal conduit interaction (H_conduit), tested with and without training-only "
            "nuisance residualization (NuisanceResidualizer) and hydrothermal-conduit priority weighting"
        ),
        "mechanism": (
            "Per-fold HistGradientBoostingClassifier trained strictly on visible faults inside fold['train'] "
            "with >=900 m negative buffer, evaluated across three preregistered arms (FUSE-RAW, FUSE-RESID, "
            "FUSE-HCW) inside a verified 9x9 discrete receptive-field support mask"
        ),
        "named_non_fault_mimic": (
            "Pleistocene Lake Lahontan tufa-cemented beach ridges or welded-tuff stratigraphic ledges "
            "overlying buried intrusive contacts; road/mining access corridors along range fronts"
        ),
        "selected_arm": selected_key,
        "holdout": selected_sum,
        "arms_holdout_summary": {
            "oof_multiphysics_hgb_d3_baseline": {
                "dti": sum_base["dti"],
                "ci95": sum_base["ci95"]["interval"],
                "TP_w": sum_base["TP_w"],
                "FP_w": sum_base["FP_w"],
            },
            "fuse_raw": {
                "dti": sum_raw["dti"],
                "ci95": sum_raw["ci95"]["interval"],
                "TP_w": sum_raw["TP_w"],
                "FP_w": sum_raw["FP_w"],
                "method_lane_novelty_passed": nov_arms["fuse_raw"]["method_lane_passed"],
                "method_lane_max_overlap_within_3px": nov_arms["fuse_raw"]["dots"][
                    "method_lane_max_dot_overlap"
                ],
                "peer_blobs_max_overlap_within_3px": nov_arms["fuse_raw"]["peer"][
                    "max_dot_overlap_within_3px"
                ],
                "c2st_auc": c2st_report["candidates"]["fuse_raw"]["observed_auc"],
                "c2st_holm_p": c2st_report["candidates"]["fuse_raw"]["holm_p_value"],
                "c2st_passed": c2st_report["candidates"]["fuse_raw"]["strict_gate_passed"],
            },
            "fuse_resid": {
                "dti": sum_resid["dti"],
                "ci95": sum_resid["ci95"]["interval"],
                "TP_w": sum_resid["TP_w"],
                "FP_w": sum_resid["FP_w"],
                "method_lane_novelty_passed": nov_arms["fuse_resid"]["method_lane_passed"],
                "method_lane_max_overlap_within_3px": nov_arms["fuse_resid"]["dots"][
                    "method_lane_max_dot_overlap"
                ],
                "peer_blobs_max_overlap_within_3px": nov_arms["fuse_resid"]["peer"][
                    "max_dot_overlap_within_3px"
                ],
                "c2st_auc": c2st_report["candidates"]["fuse_resid"]["observed_auc"],
                "c2st_holm_p": c2st_report["candidates"]["fuse_resid"]["holm_p_value"],
                "c2st_passed": c2st_report["candidates"]["fuse_resid"]["strict_gate_passed"],
            },
            "fuse_hcw": {
                "dti": sum_hcw["dti"],
                "ci95": sum_hcw["ci95"]["interval"],
                "TP_w": sum_hcw["TP_w"],
                "FP_w": sum_hcw["FP_w"],
                "method_lane_novelty_passed": nov_arms["fuse_hcw"]["method_lane_passed"],
                "method_lane_max_overlap_within_3px": nov_arms["fuse_hcw"]["dots"][
                    "method_lane_max_dot_overlap"
                ],
                "peer_blobs_max_overlap_within_3px": nov_arms["fuse_hcw"]["peer"][
                    "max_dot_overlap_within_3px"
                ],
                "c2st_auc": c2st_report["candidates"]["fuse_hcw"]["observed_auc"],
                "c2st_holm_p": c2st_report["candidates"]["fuse_hcw"]["holm_p_value"],
                "c2st_passed": c2st_report["candidates"]["fuse_hcw"]["strict_gate_passed"],
            },
        },
        "bridge_protocol_holdout": bridge_eval,
        "paired_comparisons": paired_comparisons,
        "correlation_overlap_vs_registry": {
            "total_unique_rasters_checked": sel_nov["dots"]["registry_unique_rasters"],
            "competing_method_rasters_checked": sel_nov["dots"]["competing_method_rasters_count"],
            "calibration_control_rasters_checked": sel_nov["dots"][
                "calibration_control_rasters_count"
            ],
            "peer_blobs_checked": sel_nov["peer"]["peer_unique_blobs_checked"],
            "surface_max_abs_rank_correlation": sel_nov["surface"][
                "method_lane_max_abs_rank_correlation"
            ],
            "final_max_abs_rank_correlation": sel_nov["dots"][
                "method_lane_max_abs_rank_correlation"
            ],
            "method_lane_max_overlap_within_3px": sel_nov["dots"]["method_lane_max_dot_overlap"],
            "peer_blobs_max_overlap_within_3px": sel_nov["peer"]["max_dot_overlap_within_3px"],
            "literal_all_entries_max_overlap_within_3px": sel_nov["dots"]["max_dot_overlap"],
            "method_lane_passed": sel_nov["method_lane_passed"],
            "literal_all_entries_passed": sel_nov["literal_all_entries_passed"],
            "passed": False,
            "scope": (
                "All 46 unique rasters in registry/priority_rasters.json + 5 prior 2026-10-25 "
                "GEMSDOE24 session rasters + 84 unique peer blobs in registry/peer_rasters_20261025.json"
            ),
        },
        "exact_file_nuisance_audit": sel_c2st,
        "all_arms_c2st_audit": c2st_report,
        "raster_sha256": checks["zero_outside"]["sha256"],
        "nan_outside_artifact": n_name,
        "nan_outside_sha256": checks["nan_outside"]["sha256"],
        "validator_output": checks["zero_outside"],
        "submission_name": z_name,
        "note": note,
        "verdict": "negative",
        "ok_to_download": True,
        "ok_to_submit": False,
        "reasons": reasons,
        "organizer_confirmed_score": None,
        "experiments_run": 3,
        "submission_slots_used": 0,
    }

    experiment_record = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "hypothesis": run_card["hypothesis"],
        "mechanism": run_card["mechanism"],
        "named_non_fault_mimic": run_card["named_non_fault_mimic"],
        "preregistration": "knowledge/17_preregistered_FUSE_2026-10-25.md",
        "experiment_number": 3,
        "maximum_experiments": 3,
        "maximum_session_hours": 2,
        "elapsed_seconds": time.monotonic() - started,
        "inputs": input_hashes,
        "nuisance_keys": nuisance_keys,
        "nuisance_provenance": nuisance_prov,
        "support_Verification": {
            "stencil_radius_px": sahg1.STENCIL_RADIUS_PX,
            "supported_pixels": int(support.sum()),
            "footprint_pixels": int(fp.sum()),
            "verified_9x9": True,
        },
        "canary": canary_report,
        "arms": {
            "oof_base": {"holdout": sum_base},
            "fuse_raw": {
                "holdout": sum_raw,
                "novelty_method_lane_passed": nov_arms["fuse_raw"]["method_lane_passed"],
                "novelty_max_method_overlap": nov_arms["fuse_raw"]["dots"][
                    "method_lane_max_dot_overlap"
                ],
                "novelty_peer": nov_arms["fuse_raw"]["peer"],
                "c2st": c2st_report["candidates"]["fuse_raw"],
            },
            "fuse_resid": {
                "holdout": sum_resid,
                "novelty_method_lane_passed": nov_arms["fuse_resid"]["method_lane_passed"],
                "novelty_max_method_overlap": nov_arms["fuse_resid"]["dots"][
                    "method_lane_max_dot_overlap"
                ],
                "novelty_peer": nov_arms["fuse_resid"]["peer"],
                "c2st": c2st_report["candidates"]["fuse_resid"],
            },
            "fuse_hcw": {
                "holdout": sum_hcw,
                "novelty_method_lane_passed": nov_arms["fuse_hcw"]["method_lane_passed"],
                "novelty_max_method_overlap": nov_arms["fuse_hcw"]["dots"][
                    "method_lane_max_dot_overlap"
                ],
                "novelty_peer": nov_arms["fuse_hcw"]["peer"],
                "c2st": c2st_report["candidates"]["fuse_hcw"],
            },
        },
        "selected_arm": selected_key,
        "paired_comparisons": paired_comparisons,
        "bridge_protocol_holdout": bridge_eval,
        "c2st_full": c2st_report,
        "selected_novelty_surface": sel_nov["surface"],
        "selected_novelty_dots": sel_nov["dots"],
        "selected_novelty_peer": sel_nov["peer"],
        "submission": {
            "file": z_name,
            "sha256": checks["zero_outside"]["sha256"],
            "nan_file": n_name,
            "nan_sha256": checks["nan_outside"]["sha256"],
            "checks_file": checks_name,
            "note_file": note_name,
            "note": note,
            "content_id": content_id,
            "pixel_count": int(selected_dots.sum()),
        },
        "verdict": "negative",
        "ok_to_submit": False,
        "submission_authorized": False,
    }

    download_manifest = {
        "status": "audit_only_do_not_submit",
        "ok_to_download": True,
        "ok_to_submit": False,
        "submission_authorized": False,
        "verdict": "negative",
        "generation": "fuse-hcw-resid-hgb-v1",
        "selected_arm": selected_key,
        "file": z_name,
        "sha256": checks["zero_outside"]["sha256"],
        "nan_file": n_name,
        "nan_sha256": checks["nan_outside"]["sha256"],
        "checks_file": checks_name,
        "note_file": note_name,
        "note": note,
        "content_id": content_id,
        "pixel_count": int(selected_dots.sum()),
        "method_lane_novelty_passed": sel_nov["method_lane_passed"],
        "literal_all_entries_passed": sel_nov["literal_all_entries_passed"],
        "holdout_dti": selected_sum["dti"],
        "holdout_ci95": selected_sum["ci95"]["interval"],
        "fuse_raw_dti": sum_raw["dti"],
        "fuse_raw_ci95": sum_raw["ci95"]["interval"],
        "fuse_resid_dti": sum_resid["dti"],
        "fuse_resid_ci95": sum_resid["ci95"]["interval"],
        "fuse_hcw_dti": sum_hcw["dti"],
        "fuse_hcw_ci95": sum_hcw["ci95"]["interval"],
        "oof_baseline_dti": sum_base["dti"],
        "oof_baseline_ci95": sum_base["ci95"]["interval"],
    }

    save_json(experiment_record, EXPERIMENT_JSON)
    save_json(run_card, RUN_CARD_JSON)
    save_json(run_card, DOCS_RUN_CARD)
    save_json(download_manifest, DOCS_DOWNLOAD_JSON)

    # Generate exact-file preflight receipt via shared CLI
    preflight_out = downloads / f"{z_name[:-4]}.preflight.json"
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/preflight_submission.py"),
            str(z_path),
            "--run-card",
            str(RUN_CARD_JSON),
            "--output",
            str(preflight_out),
        ],
        cwd=ROOT,
        check=True,
    )
    print(f"10. Completed H24-FUSE run and preflight: {z_name}", flush=True)
    print(json.dumps(verify_recorded(), indent=2), flush=True)


if __name__ == "__main__":
    main()
