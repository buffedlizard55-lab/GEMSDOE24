#!/usr/bin/env python3
"""Execute or verify the preregistered H24-GVC1 experiment via shared protocol tools.

Invoked through ``scripts/evaluate_holdout.py --run-gvc1`` or ``--verify-gvc1``.
Reuses ``SegmentHoldout`` (``gems-segment-pooled-v1``), ``novelty.compare_registry``,
``c2s2.c2s2_test``, and ``scripts/submission_writer.py``. Leaves all frozen MTR1
and ASPC receipts untouched.
"""

from __future__ import annotations

import gc
import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt
from threadpoolctl import threadpool_limits

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems import c2s2, footprint, gvc, holdout, novelty, submission  # noqa: E402
from gems.validator import sha256_file  # noqa: E402

EXPERIMENT_JSON = ROOT / "evidence/gvc1_experiment_20261025.json"
RUN_CARD_JSON = ROOT / "evidence/gvc1_run_card_20261025.json"
C2ST_JSON = ROOT / "evidence/gvc1_c2st_audit_20261025.json"
DOWNLOAD_JSON = ROOT / "docs/data/gvc1_download.json"
PREREG_PATH = ROOT / "knowledge/12_preregistration_GVC1_2026-10-25.md"
PREREG_COMMIT = "1bc8ace0b726555ab27d13905ed389e7f44301ec"
FULL_DOT_BUDGET = 37654


def _save_json(obj: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n")


def _load_verified_nuisance(
    root: Path, fp: np.ndarray, work_dir: Path
) -> tuple[dict[str, np.ndarray], np.ndarray, dict[str, Any]]:
    """Load verified road, claim, and derived 4-block audit grids without touching frozen receipts."""
    audit_dir = root / "data/external/audit_sources"
    road_tif = audit_dir / "tiger_road_distance_m.tif"
    road_rec = json.loads((audit_dir / "tiger_road_receipt.json").read_text())
    if sha256_file(road_tif) != road_rec["sha256"]:
        raise RuntimeError("Road distance TIFF SHA-256 mismatch")

    claim_tif = audit_dir / "blm_closed_claim_distance_m.tif"
    claim_rec = json.loads((audit_dir / "receipt.json").read_text())["claim_distance"]
    if sha256_file(claim_tif) != claim_rec["sha256"]:
        raise RuntimeError("BLM closed-claim distance TIFF SHA-256 mismatch")

    blk_tif = audit_dir / "acquisition_block_id_100m.tif"
    blk_rec = json.loads((audit_dir / "acquisition_blocks_receipt.json").read_text())
    if sha256_file(blk_tif) != blk_rec["raster"]["sha256"]:
        raise RuntimeError("Derived acquisition-block TIFF SHA-256 mismatch")

    with rasterio.open(road_tif) as d:
        road_m = d.read(1).astype(np.float32)
    with rasterio.open(claim_tif) as d:
        claim_m = d.read(1).astype(np.float32)
    with rasterio.open(blk_tif) as d:
        blk = d.read(1)

    c2st_feats: dict[str, np.ndarray] = {
        "road_m": np.log1p(np.maximum(road_m, 0.0)).astype(np.float32),
        "claim_m": np.log1p(np.maximum(claim_m, 0.0)).astype(np.float32),
    }
    for b in (1, 2, 3, 4):
        c2st_feats[f"block_{b}"] = (blk == b).astype(np.float32)

    fp_ids = np.flatnonzero(fp.ravel())
    nuis_path = work_dir / "nuisance_fp.npy"
    if not nuis_path.exists():
        nuis_mm = np.lib.format.open_memmap(
            nuis_path, mode="w+", dtype=np.float32, shape=(len(fp_ids), 6)
        )
        nuis_mm[:, 0] = c2st_feats["road_m"].ravel()[fp_ids]
        nuis_mm[:, 1] = c2st_feats["claim_m"].ravel()[fp_ids]
        for i, b in enumerate((1, 2, 3, 4), start=2):
            nuis_mm[:, i] = c2st_feats[f"block_{b}"].ravel()[fp_ids]
        nuis_mm.flush()

    prov = {
        "road_m_sha256": road_rec["sha256"],
        "claim_m_sha256": claim_rec["sha256"],
        "acquisition_blocks_sha256": blk_rec["raster"]["sha256"],
        "block_boundary_status": "derived_audited_not_official_coordinates",
        "blocks_official_coordinates": False,
        "full_requested_audit_available": True,
    }
    return c2st_feats, np.load(nuis_path, mmap_mode="r"), prov


def _extended_registry_entries(root: Path, fp: np.ndarray) -> list[dict[str, Any]]:
    reg = json.loads((root / "registry/priority_rasters.json").read_text())
    entries = list(reg["unique_rasters"])
    seen = {e["footprint_sha256"] for e in entries}
    local_peers = [
        (
            "local-aspc-047",
            "docs/downloads/gems24-aspc-20261025-6393e9d9b0df-RESEARCH-NOT-SUBMISSION-zeros.tif",
        ),
        (
            "local-mtr1-048",
            "docs/downloads/gems24-mtr1-negative-paired-trough-20261025-ed7243e6d163-zeros.tif",
        ),
    ]
    for rid, rel_path in local_peers:
        p = root / rel_path
        if not p.exists():
            continue
        with rasterio.open(p) as ds:
            a = ds.read(1)
        fp_sha = hashlib.sha256(np.asarray(a[fp], dtype="<f4").tobytes()).hexdigest()
        if fp_sha not in seen:
            seen.add(fp_sha)
            entries.append(
                {
                    "id": rid,
                    "file": p.name,
                    "cache_path": rel_path,
                    "footprint_sha256": fp_sha,
                }
            )
    return entries


def _run_batched_canary(
    context: holdout.SegmentHoldout,
    fp: np.ndarray,
    base_mm: np.ndarray,
    base_names: list[str],
    gvc_mm: np.ndarray,
    gvc_names: list[str],
    *,
    batch_size: int = 8,
) -> dict[str, Any]:
    fp_ids = np.flatnonzero(fp.ravel())
    all_specs = [(n, "base", i) for i, n in enumerate(base_names)] + [
        (n, "gvc", i) for i, n in enumerate(gvc_names)
    ]
    merged_features: dict[str, Any] = {}
    meta_template: dict[str, Any] = {}
    for start in range(0, len(all_specs), batch_size):
        batch = all_specs[start : start + batch_size]
        fdict: dict[str, np.ndarray] = {}
        for name, src, col in batch:
            grid = np.full(fp.shape, np.nan, dtype=np.float32)
            grid.ravel()[fp_ids] = base_mm[:, col] if src == "base" else gvc_mm[:, col]
            fdict[name] = grid
        res = context.canary(fdict, seed=20261025, max_per_class=15000)
        if not meta_template:
            meta_template = {k: v for k, v in res.items() if k != "features"}
        merged_features.update(res["features"])
        del fdict
        gc.collect()
    meta_template["passed"] = not any(v["leakage_suspected"] for v in merged_features.values())
    meta_template["features"] = merged_features
    return meta_template


def _write_via_shared_cli(
    pred_2d: np.ndarray, out_tif: Path, template: Path, outside: str, tmp_npy: Path
) -> dict[str, Any]:
    tmp_npy.parent.mkdir(parents=True, exist_ok=True)
    np.save(tmp_npy, pred_2d.astype(np.float32))
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/submission_writer.py"),
            str(tmp_npy),
            str(out_tif),
            "--template",
            str(template),
            "--outside",
            outside,
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    tmp_npy.unlink(missing_ok=True)
    return json.loads(proc.stdout)


def _run_c2st_family(
    fp: np.ndarray,
    c2st_feats: dict[str, np.ndarray],
    prov: dict[str, Any],
    surfaces: list[tuple[str, Path]],
) -> dict[str, Any]:
    fold, names = holdout.make_quadrant_folds(fp)
    h, w = fp.shape
    yy, xx = np.ogrid[:h, :w]
    spatial_block = (yy // 100) * ((w + 99) // 100) + xx // 100
    purge = {
        f_id: np.unique(spatial_block[(distance_transform_edt(fold != f_id) <= 15) & fp])
        for f_id in range(4)
    }
    refs_out: dict[str, Any] = {}
    p_vals: list[float] = []
    ordered_labels: list[str] = []

    prior_audit_path = ROOT / "evidence/accessibility_audit_v2.json"
    prior_labels_rec = None
    if prior_audit_path.exists():
        prior_doc = json.loads(prior_audit_path.read_text())
        cand_lab = prior_doc.get("references", {}).get("labels")
        if (
            cand_lab
            and cand_lab.get("sha256") == sha256_file(ROOT / "data/bridge/labels.tif")
            and prior_doc.get("protocol", {}).get("permutations") == 199
            and prior_doc.get("protocol", {}).get("shifts") == 99
            and prior_doc.get("protocol", {}).get("seed") == 20261002
        ):
            prior_labels_rec = cand_lab

    for label, tif_path in surfaces:
        if label == "labels" and prior_labels_rec is not None:
            p_slim = dict(prior_labels_rec["primary"])
            p_inf = dict(p_slim.get("info", {}))
            p_inf.pop("null_aucs", None)
            p_slim["info"] = p_inf
            s_slim = dict(prior_labels_rec["shift_diagnostic"])
            s_inf = dict(s_slim.get("info", {}))
            s_inf.pop("null_aucs", None)
            s_inf.pop("shift_draws", None)
            s_slim["info"] = s_inf
            refs_out[label] = {
                "file": tif_path.name,
                "sha256": prior_labels_rec["sha256"],
                "positive_pixels": int(prior_labels_rec["positive_pixels"]),
                "primary": p_slim,
                "shift_diagnostic": s_slim,
                "single_feature_auc_descriptive": dict(
                    prior_labels_rec.get("single_feature_auc_descriptive", {})
                ),
                "reused_verified_labels_receipt": "evidence/accessibility_audit_v2.json",
            }
            ordered_labels.append(label)
            p_vals.append(float(p_slim["p_value"]))
            continue
        with rasterio.open(tif_path) as ds:
            vals = ds.read(1)
        ref = (vals > (0.0 if label == "labels" else 0.5)) & fp
        primary = c2s2.c2s2_test(
            label,
            ref,
            c2st_feats,
            fold,
            fp,
            n_null=199,
            n_per_class=12000,
            null_mode="grouped",
            seed=20261002,
            purge_groups=purge,
        ).as_dict()
        shift = c2s2.c2s2_test(
            label,
            ref,
            c2st_feats,
            fold,
            fp,
            n_null=99,
            n_per_class=12000,
            null_mode="shift",
            seed=20261002,
            purge_groups=purge,
            shift_fn=lambda dy, dx, r=ref: np.roll(r, (dy, dx), axis=(0, 1)),
        ).as_dict()
        # Descriptive single-feature AUCs
        near, far, _ = c2s2.near_far_masks(ref)
        singles: dict[str, float] = {}
        fit_fn = c2s2.make_model("hgb", 20261002)
        with threadpool_limits(limits=2):
            for fname in sorted(c2st_feats):
                X1, y1, f1, inf1 = c2s2.build_matrix(
                    {fname: c2st_feats[fname]}, near, far, fold, fp, 12000, 20261002
                )
                auc1, _ = c2s2.spatial_cv_auc(
                    fit_fn,
                    X1,
                    y1,
                    f1,
                    "hgb",
                    groups=inf1["spatial_blocks"],
                    purge_groups=purge,
                )
                singles[fname] = float(auc1)
        # Drop verbose 199-element null array into summary quantiles to keep JSON compact
        primary_slim = dict(primary)
        primary_info = dict(primary_slim.get("info", {}))
        primary_info.pop("null_aucs", None)
        primary_slim["info"] = primary_info

        shift_slim = dict(shift)
        shift_info = dict(shift_slim.get("info", {}))
        shift_info.pop("null_aucs", None)
        shift_info.pop("shift_draws", None)
        shift_slim["info"] = shift_info

        refs_out[label] = {
            "file": tif_path.name,
            "sha256": sha256_file(tif_path),
            "positive_pixels": int(ref.sum()),
            "primary": primary_slim,
            "shift_diagnostic": shift_slim,
            "single_feature_auc_descriptive": singles,
        }
        ordered_labels.append(label)
        p_vals.append(float(primary["p_value"]))

    holm = c2s2.holm_adjust(p_vals)
    for label, hp in zip(ordered_labels, holm):
        r = refs_out[label]
        p = r["primary"]
        p["holm_p_value"] = float(hp)
        flagged = bool(hp <= 0.05 and p["observed_auc"] >= 0.55 and p["margin_vs_p95"] >= 0.02)
        r["meaningful_access_association_flagged"] = flagged
        r["strict_c2st_gate_passed"] = not flagged

    return {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "protocol": {
            "method": "Lopez-Paz & Oquab (ICLR 2017) spatial C2ST, https://arxiv.org/abs/1610.06545",
            "labels_first": ordered_labels[0] == "labels",
            "feature_names": sorted(c2st_feats),
            "samples_per_class": 12000,
            "grouped_permutations": 199,
            "spatial_shifts": 99,
            "seed": 20261002,
            "folds": names,
            "effect_rule": "Holm p<=.05 AND AUC>=.55 AND margin over grouped-null p95>=.02",
        },
        "source_provenance": prov,
        "references": refs_out,
    }


def run_gvc1(*, work_dir: Path, stop_after_stage5: bool = False) -> dict[str, Any]:
    if EXPERIMENT_JSON.exists():
        raise SystemExit(
            "H24-GVC1 experiment already recorded and frozen. No implicit rerun; use --verify-gvc1."
        )
    t_start = time.monotonic()
    work_dir.mkdir(parents=True, exist_ok=True)

    fp = footprint.load_footprint()
    template = ROOT / "data/bridge/sample_submission.tif"
    with rasterio.open(template) as t_ds:
        transform = t_ds.transform
    with rasterio.open(ROOT / "data/bridge/labels.tif") as l_ds:
        catalogue = (l_ds.read(1) > 0) & fp

    prep_dir = work_dir / "prepared"
    if not (prep_dir / "features.npy").exists():
        prep_dir = ROOT / "data/prepared"
    meta = json.loads((prep_dir / "features.json").read_text())
    base_npy = prep_dir / "features.npy"
    if sha256_file(base_npy) != meta["sha256"]:
        raise SystemExit("Prepared feature-stack SHA-256 mismatch")
    base_mm = np.load(base_npy, mmap_mode="r")
    base_names: list[str] = list(meta["names"])

    print(
        "[1/7] Building/verifying 18 label-free GVC1 geothermal/lineament/tilt features...",
        flush=True,
    )
    gvc_npy = work_dir / "gvc1_features.npy"
    if gvc_npy.exists():
        gvc_mm = np.load(gvc_npy, mmap_mode="r")
        if gvc_mm.shape != (int(fp.sum()), len(gvc.GVC1_FEATURE_NAMES)):
            _, gvc_names = gvc.build_gvc1_features(
                ROOT, base_mm, base_names, fp, transform, gvc_npy
            )
            gvc_mm = np.load(gvc_npy, mmap_mode="r")
        else:
            gvc_names = list(gvc.GVC1_FEATURE_NAMES)
    else:
        _, gvc_names = gvc.build_gvc1_features(ROOT, base_mm, base_names, fp, transform, gvc_npy)
        gvc_mm = np.load(gvc_npy, mmap_mode="r")

    print("[2/7] Loading verified road/claim/4-block nuisance grids...", flush=True)
    c2st_feats, nuis_mm, nuis_prov = _load_verified_nuisance(ROOT, fp, work_dir)

    stage5_ckpt = work_dir / "stage5_checkpoint.json"
    cand_tmp = work_dir / "candidates"
    cand_tmp.mkdir(parents=True, exist_ok=True)
    e1_dots_npy = cand_tmp / "full_dots_e1.npy"
    e2_dots_npy = cand_tmp / "full_dots_e2.npy"

    if stage5_ckpt.exists() and e1_dots_npy.exists() and e2_dots_npy.exists():
        print("[3-5/7] Loading verified deterministic Stage-5 checkpoint...", flush=True)
        ck = json.loads(stage5_ckpt.read_text())
        canary = ck["canary"]
        fold_fit_meta = ck["fold_fit_metadata"]
        sum_b0 = ck["sum_b0"]
        sum_b1 = ck["sum_b1"]
        sum_e1 = ck["sum_e1"]
        sum_e2 = ck["sum_e2"]
        paired = ck["paired"]
        full_meta_e1 = ck["full_meta_e1"]
        full_meta_e2 = ck["full_meta_e2"]
        nov_e1_surf = ck["nov_e1_surf"]
        nov_e1_dots = ck["nov_e1_dots"]
        nov_e2_surf = ck["nov_e2_surf"]
        nov_e2_dots = ck["nov_e2_dots"]
        stage15_elapsed = float(ck["elapsed_stage15"])
        full_dots_e1 = np.load(e1_dots_npy)
        full_dots_e2 = np.load(e2_dots_npy)
    else:
        context = holdout.SegmentHoldout(fp, catalogue, buffer_px=15)
        print("[3/7] Running two-polarity Leakage Canary across all 48 features...", flush=True)
        canary = _run_batched_canary(context, fp, base_mm, base_names, gvc_mm, gvc_names)
        max_canary = max(v["pooled_auc"] for v in canary["features"].values())
        min_canary = min(v["pooled_auc"] for v in canary["features"].values())
        print(
            f"      Canary passed={canary['passed']} | pooled AUC range=[{min_canary:.4f}, {max_canary:.4f}]",
            flush=True,
        )
        if not canary["passed"]:
            raise SystemExit("Leakage canary flagged >0.90; halting immediately without fitting")

        print(
            "[4/7] Running 4-fold SegmentHoldout (B0, B1, E1: H24-GVC1, E2: H24-GVC1-Resid)...",
            flush=True,
        )
        total_offcat = int((fp & ~catalogue).sum())
        preds_b0, preds_b1, preds_e1, preds_e2 = [], [], [], []
        fold_fit_meta = []

        for f in context.folds:
            fid = int(f["id"])
            fname = f["name"]
            f_offcat = int((f["valid"] & ~f["visible"]).sum())
            k_fold = int(round(FULL_DOT_BUDGET * f_offcat / total_offcat))
            t_f = time.monotonic()

            p_b0 = gvc.fit_predict_legacy_ridge_baseline(
                base_mm,
                train_mask=f["train"],
                visible_mask=f["visible"],
                valid_mask=f["valid"],
                footprint=fp,
                seed=20261025 + fid,
            )
            preds_b0.append(p_b0)

            surf_b1, m_b1 = gvc.fit_predict_calibrated_hgb(
                base_mm,
                None,
                None,
                train_mask=f["train"],
                visible_mask=f["visible"],
                predict_mask=f["valid"],
                footprint=fp,
                seed=20261025 + fid,
                residualize=False,
            )
            p_b1 = gvc.submodular_dti_allocate(
                surf_b1,
                f["valid"],
                f["visible"],
                budget=k_fold,
                min_spacing_px=2.5,
                catalogue_clearance_px=2.0,
            )
            preds_b1.append(p_b1)
            del surf_b1

            surf_e1, m_e1 = gvc.fit_predict_calibrated_hgb(
                base_mm,
                gvc_mm,
                None,
                train_mask=f["train"],
                visible_mask=f["visible"],
                predict_mask=f["valid"],
                footprint=fp,
                seed=20261025 + fid,
                residualize=False,
            )
            p_e1 = gvc.submodular_dti_allocate(
                surf_e1,
                f["valid"],
                f["visible"],
                budget=k_fold,
                min_spacing_px=2.5,
                catalogue_clearance_px=2.0,
            )
            preds_e1.append(p_e1)
            del surf_e1

            surf_e2, m_e2 = gvc.fit_predict_calibrated_hgb(
                base_mm,
                gvc_mm,
                nuis_mm,
                train_mask=f["train"],
                visible_mask=f["visible"],
                predict_mask=f["valid"],
                footprint=fp,
                seed=20261025 + fid,
                residualize=True,
            )
            p_e2 = gvc.submodular_dti_allocate(
                surf_e2,
                f["valid"],
                f["visible"],
                budget=k_fold,
                min_spacing_px=2.5,
                catalogue_clearance_px=2.0,
            )
            preds_e2.append(p_e2)
            del surf_e2
            gc.collect()

            s0, _ = context.score_fold(p_b0, f)
            s1, _ = context.score_fold(p_b1, f)
            se1, _ = context.score_fold(p_e1, f)
            se2, _ = context.score_fold(p_e2, f)
            print(
                f"      Fold {fname:<18} | k={k_fold:,} | B0={s0['dti']:.5f} | B1={s1['dti']:.5f} | E1={se1['dti']:.5f} | E2={se2['dti']:.5f} ({time.monotonic() - t_f:.1f}s)",
                flush=True,
            )
            fold_fit_meta.append(
                {"fold": fname, "k_fold_budget": k_fold, "b1": m_b1, "e1": m_e1, "e2": m_e2}
            )

        sum_b0 = context.summarize(preds_b0, ci_draws=1999)
        sum_b1 = context.summarize(preds_b1, ci_draws=1999)
        sum_e1 = context.summarize(preds_e1, ci_draws=1999)
        sum_e2 = context.summarize(preds_e2, ci_draws=1999)

        paired = {
            "B1_vs_B0_allocator_effect": context.compare_paired(preds_b1, preds_b0, ci_draws=1999),
            "E1_vs_B0_total_gain": context.compare_paired(preds_e1, preds_b0, ci_draws=1999),
            "E1_vs_B1_physics_geothermal_gain": context.compare_paired(
                preds_e1, preds_b1, ci_draws=1999
            ),
            "E2_vs_B0_total_gain": context.compare_paired(preds_e2, preds_b0, ci_draws=1999),
            "E2_vs_B1_physics_geothermal_gain": context.compare_paired(
                preds_e2, preds_b1, ci_draws=1999
            ),
            "E2_vs_E1_residualization_delta": context.compare_paired(
                preds_e2, preds_e1, ci_draws=1999
            ),
        }
        print(
            f"      POOLED HOLDOUT-DTI | B0={sum_b0['dti']:.5f} | B1={sum_b1['dti']:.5f} | E1={sum_e1['dti']:.5f} | E2={sum_e2['dti']:.5f}",
            flush=True,
        )
        print(
            f"      PAIRED E1-B1 = {paired['E1_vs_B1_physics_geothermal_gain']['paired_delta_dti']:+.5f} CI95={paired['E1_vs_B1_physics_geothermal_gain']['paired_delta_ci95']}",
            flush=True,
        )
        print(
            f"      PAIRED E2-B1 = {paired['E2_vs_B1_physics_geothermal_gain']['paired_delta_dti']:+.5f} CI95={paired['E2_vs_B1_physics_geothermal_gain']['paired_delta_ci95']}",
            flush=True,
        )
        del preds_b0, preds_b1, preds_e1, preds_e2
        gc.collect()

        print(
            "[5/7] Fitting full-footprint surfaces & checking 48-raster novelty gate...", flush=True
        )
        full_surf_e1, full_meta_e1 = gvc.fit_predict_calibrated_hgb(
            base_mm,
            gvc_mm,
            None,
            train_mask=fp,
            visible_mask=catalogue,
            predict_mask=fp,
            footprint=fp,
            seed=20261025 + 99,
            residualize=False,
        )
        full_dots_e1 = gvc.submodular_dti_allocate(
            full_surf_e1,
            fp,
            catalogue,
            budget=FULL_DOT_BUDGET,
            min_spacing_px=2.5,
            catalogue_clearance_px=2.0,
        )

        full_surf_e2, full_meta_e2 = gvc.fit_predict_calibrated_hgb(
            base_mm,
            gvc_mm,
            nuis_mm,
            train_mask=fp,
            visible_mask=catalogue,
            predict_mask=fp,
            footprint=fp,
            seed=20261025 + 99,
            residualize=True,
        )
        full_dots_e2 = gvc.submodular_dti_allocate(
            full_surf_e2,
            fp,
            catalogue,
            budget=FULL_DOT_BUDGET,
            min_spacing_px=2.5,
            catalogue_clearance_px=2.0,
        )

        entries_48 = _extended_registry_entries(ROOT, fp)
        nov_e1_surf = novelty.compare_registry(
            full_surf_e1, fp, entries_48, ROOT, separate_calibration_controls=True
        )
        nov_e1_dots = novelty.compare_registry(
            full_dots_e1,
            fp,
            entries_48,
            ROOT,
            dots=(full_dots_e1 > 0.5),
            separate_calibration_controls=True,
        )
        nov_e2_surf = novelty.compare_registry(
            full_surf_e2, fp, entries_48, ROOT, separate_calibration_controls=True
        )
        nov_e2_dots = novelty.compare_registry(
            full_dots_e2,
            fp,
            entries_48,
            ROOT,
            dots=(full_dots_e2 > 0.5),
            separate_calibration_controls=True,
        )
        print(
            f"      E1 novelty (47 competing): surf_pass={nov_e1_surf['competing_method_passed']} max|rho|={nov_e1_surf['max_abs_rank_correlation']:.4f} | dots_pass={nov_e1_dots['competing_method_passed']} max_comp_ov={nov_e1_dots['max_competing_dot_overlap']:.4f}",
            flush=True,
        )
        print(
            f"      E2 novelty (47 competing): surf_pass={nov_e2_surf['competing_method_passed']} max|rho|={nov_e2_surf['max_abs_rank_correlation']:.4f} | dots_pass={nov_e2_dots['competing_method_passed']} max_comp_ov={nov_e2_dots['max_competing_dot_overlap']:.4f}",
            flush=True,
        )
        np.save(e1_dots_npy, full_dots_e1)
        np.save(e2_dots_npy, full_dots_e2)
        stage15_elapsed = time.monotonic() - t_start
        _save_json(
            {
                "canary": canary,
                "fold_fit_metadata": fold_fit_meta,
                "sum_b0": sum_b0,
                "sum_b1": sum_b1,
                "sum_e1": sum_e1,
                "sum_e2": sum_e2,
                "paired": paired,
                "full_meta_e1": full_meta_e1,
                "full_meta_e2": full_meta_e2,
                "nov_e1_surf": nov_e1_surf,
                "nov_e1_dots": nov_e1_dots,
                "nov_e2_surf": nov_e2_surf,
                "nov_e2_dots": nov_e2_dots,
                "elapsed_stage15": stage15_elapsed,
            },
            stage5_ckpt,
        )
    if stop_after_stage5:
        return {"stage5_complete": True, "elapsed_stage15": round(stage15_elapsed, 2)}

    t_s6 = time.monotonic()
    print(
        "[6/7] Running exact-file Lopez-Paz & Oquab C2ST Nuisance Audit (labels first)...",
        flush=True,
    )
    e1_tmp_tif = cand_tmp / "e1_gvc1_zeros.tif"
    e2_tmp_tif = cand_tmp / "e2_gvc1_resid_zeros.tif"
    _write_via_shared_cli(full_dots_e1, e1_tmp_tif, template, "zero", cand_tmp / "e1.npy")
    _write_via_shared_cli(full_dots_e2, e2_tmp_tif, template, "zero", cand_tmp / "e2.npy")

    c2st_report = _run_c2st_family(
        fp,
        c2st_feats,
        nuis_prov,
        [
            ("labels", ROOT / "data/bridge/labels.tif"),
            ("e1_gvc1", e1_tmp_tif),
            ("e2_gvc1_resid", e2_tmp_tif),
        ],
    )
    _save_json(c2st_report, C2ST_JSON)
    e1_c2st_ok = bool(c2st_report["references"]["e1_gvc1"]["strict_c2st_gate_passed"])
    e2_c2st_ok = bool(c2st_report["references"]["e2_gvc1_resid"]["strict_c2st_gate_passed"])
    print(
        f"      C2ST strict pass: labels={c2st_report['references']['labels']['strict_c2st_gate_passed']} (AUC={c2st_report['references']['labels']['primary']['observed_auc']:.4f}) | E1={e1_c2st_ok} (AUC={c2st_report['references']['e1_gvc1']['primary']['observed_auc']:.4f}, Holm p={c2st_report['references']['e1_gvc1']['primary']['holm_p_value']:.3f}) | E2={e2_c2st_ok} (AUC={c2st_report['references']['e2_gvc1_resid']['primary']['observed_auc']:.4f}, Holm p={c2st_report['references']['e2_gvc1_resid']['primary']['holm_p_value']:.3f})",
        flush=True,
    )

    # Preregistered deterministic selection rule (§3.4 of 12_preregistration_GVC1_2026-10-25.md)
    if e1_c2st_ok:
        selected_arm = "e1_gvc1" if sum_e1["dti"] >= sum_e2["dti"] else "e2_gvc1_resid"
        selection_reason = "E1 passed strict C2ST; selected higher HOLDOUT-DTI arm"
    elif (not e1_c2st_ok) and e2_c2st_ok and (sum_e2["dti"] > sum_b1["dti"]):
        selected_arm = "e2_gvc1_resid"
        selection_reason = "E1 flagged by strict C2ST while training-only residualized E2 passed strict C2ST and beat OOF-Base-Submod (B1)"
    else:
        selected_arm = "e1_gvc1" if sum_e1["dti"] >= sum_e2["dti"] else "e2_gvc1_resid"
        selection_reason = "Selected higher HOLDOUT-DTI arm under preregistered fallback; C2ST status recorded in blockers"

    if selected_arm == "e1_gvc1":
        sel_dots = full_dots_e1
        sel_holdout = sum_e1
        sel_vs_b0 = paired["E1_vs_B0_total_gain"]
        sel_vs_b1 = paired["E1_vs_B1_physics_geothermal_gain"]
        sel_nov_surf = nov_e1_surf
        sel_nov_dots = nov_e1_dots
        sel_c2st = c2st_report["references"]["e1_gvc1"]
        base_slug = "gvc1-geothermal-lineament-submod"
        arm_tag = "GVC1"
    else:
        sel_dots = full_dots_e2
        sel_holdout = sum_e2
        sel_vs_b0 = paired["E2_vs_B0_total_gain"]
        sel_vs_b1 = paired["E2_vs_B1_physics_geothermal_gain"]
        sel_nov_surf = nov_e2_surf
        sel_nov_dots = nov_e2_dots
        sel_c2st = c2st_report["references"]["e2_gvc1_resid"]
        base_slug = "gvc1-resid-geothermal-lineament-submod"
        arm_tag = "GVC1-R"

    comp_nov_ok = bool(
        sel_nov_surf["competing_method_passed"] and sel_nov_dots["competing_method_passed"]
    )
    slug = base_slug if comp_nov_ok else base_slug.replace("gvc1-", "gvc1-negative-", 1)

    print(
        f"[7/7] Packaging selected arm {selected_arm} (competing_novelty_ok={comp_nov_ok}) via shared submission_writer.py...",
        flush=True,
    )
    content_id = submission.scored_content_id(sel_dots, fp, catalogue)
    downloads = ROOT / "docs/downloads"
    zeros_name = submission.make_filename("gems24", slug, "20261025", content_id, "zeros")
    nan_name = submission.make_filename("gems24", slug, "20261025", content_id, "nan")
    zeros_path = downloads / zeros_name
    nan_path = downloads / nan_name

    chk_zeros = _write_via_shared_cli(
        sel_dots, zeros_path, template, "zero", cand_tmp / "final_z.npy"
    )
    chk_nan = _write_via_shared_cli(sel_dots, nan_path, template, "nan", cand_tmp / "final_n.npy")
    if not (chk_zeros["format_valid"] and chk_nan["format_valid"]):
        raise SystemExit("Exact-file format validator failed")
    zip_path = submission.zip_single(nan_path, downloads / nan_name.replace(".tif", ".zip"))

    if not comp_nov_ok:
        max_ov_pct = sel_nov_dots["max_competing_dot_overlap"] * 100.0
        note = (
            f"GEMS24 {arm_tag} | vent+2m+tilt+lineament | "
            f"NEGATIVE: {max_ov_pct:.1f}% 3px overlap stop; DO NOT SUBMIT | id {content_id}"
        )
    else:
        note = (
            f"GEMS24 {arm_tag} | INGENIOUS vent+2m+tilt+lineament submod | "
            f"NOT FOR LIVE SLOT: selector/lattice gate | id {content_id}"
        )
    if len(note) > 140:
        raise AssertionError(f"Submission note length {len(note)} > 140")
    note_file = f"note-{zeros_name[:-4]}.txt"
    checks_file = f"checks-{zeros_name[:-4]}.json"
    (downloads / note_file).write_text(note + "\n")
    _save_json(
        {
            "zero_outside": chk_zeros,
            "nan_outside": chk_nan,
            "nan_zip_file": zip_path.name,
            "nan_zip_sha256": sha256_file(zip_path),
        },
        downloads / checks_file,
    )

    # Evaluate automatic technical vs governance gates (fail-closed, zero human inspector)
    technical_gates = {
        "format_and_unit_range_valid": bool(chk_zeros["format_valid"] and chk_nan["format_valid"]),
        "leakage_canary_passed": bool(canary["passed"]),
        "competing_method_uniqueness_47_rasters_passed": bool(comp_nov_ok),
        "beats_reconstructed_legacy_oof_ridge_B0_pooled": bool(sel_holdout["dti"] > sum_b0["dti"]),
        "beats_matched_allocator_oof_base_B1_ci95_gt_0": bool(
            sel_vs_b1["ci95_strictly_positive"] and sel_vs_b1["fold_wins"] >= 3
        ),
        "strict_c2st_nuisance_audit_passed": bool(sel_c2st["strict_c2st_gate_passed"]),
    }
    governance_gates = {
        "literal_unseparated_uniqueness_incl_spacing5_lattice": bool(
            sel_nov_dots["literal_unseparated_passed"]
        ),
        "assigned_coordinator_lane_present": False,
        "external_weekly_selector_quota_authorized": False,
    }
    ok_to_submit = all(technical_gates.values()) and all(governance_gates.values())
    verdict = "promote" if ok_to_submit else "negative"

    blockers: list[str] = []
    if not comp_nov_ok:
        top_c = sel_nov_dots["rows"]
        top_comp_row = max(
            (r for r in top_c if r["comparator_class"] == "competing_method"),
            key=lambda r: r["candidate_dot_overlap_within_3px"] or 0.0,
        )
        blockers.append(
            f"Duplicate-overlap stop (Rule 1): {top_comp_row['candidate_dot_overlap_within_3px'] * 100:.2f}% (>70%) of emitted dots lie <=3 px from competing supervised range-front detector {top_comp_row['registry_id']} ({top_comp_row['file']}, raw Spearman rho={top_comp_row['raw_spearman']:.4f})"
        )
    for k, v in technical_gates.items():
        if not v and k != "competing_method_uniqueness_47_rasters_passed":
            blockers.append(f"Technical gate failed: {k}")
    if not governance_gates["literal_unseparated_uniqueness_incl_spacing5_lattice"]:
        ctrl = sel_nov_dots["calibration_control_summary"][0]
        blockers.append(
            f"Retained spacing-5 calibration lattice ({ctrl['registry_id']}) covers "
            f"{ctrl['footprint_3px_coverage'] * 100:.2f}% of footprint at 3 px "
            f"(pigeonhole lower bound >= {ctrl['pigeonhole_min_overlap'] * 100:.2f}% > 70%)"
        )
    if not governance_gates["assigned_coordinator_lane_present"]:
        blockers.append(
            "No coordinator-assigned single method paragraph in brief (IR-20261025-MISSING-LANE)"
        )
    if not governance_gates[
        "external_weekly_selector_quota_verified"
        if "external_weekly_selector_quota_verified" in governance_gates
        else "external_weekly_selector_quota_authorized"
    ]:
        blockers.append(
            "Parallel-Run Protocol Rule 6: live weekly-slot selection requires separate cross-lane selector and verified DrivenData weekly cap"
        )

    elapsed = round(stage15_elapsed + (time.monotonic() - t_s6), 2)

    def _slim_nov(n: dict[str, Any]) -> dict[str, Any]:
        top_comp = sorted(
            [r for r in n["rows"] if r["comparator_class"] == "competing_method"],
            key=lambda r: (
                r["candidate_dot_overlap_within_3px"]
                if r["candidate_dot_overlap_within_3px"] is not None
                else abs(r["raw_spearman"] or 0.0)
            ),
            reverse=True,
        )[:8]
        out = {k: v for k, v in n.items() if k != "rows"}
        out["top_competing_comparators"] = top_comp
        return out

    experiment_payload = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "hypothesis_selected": selected_arm,
        "selection_reason": selection_reason,
        "preregistration": str(PREREG_PATH.relative_to(ROOT)),
        "preregistration_commit": PREREG_COMMIT,
        "preregistration_sha256": sha256_file(PREREG_PATH),
        "experiments_executed": 2,
        "maximum_experiments_budget": 3,
        "elapsed_seconds": elapsed,
        "maximum_session_seconds": 7200,
        "environment": {k: version(k) for k in ("numpy", "scipy", "scikit-learn", "rasterio")},
        "code_sha256": {
            str(p.relative_to(ROOT)): sha256_file(p)
            for p in (
                ROOT / "src/gems/gvc.py",
                ROOT / "src/gems/holdout.py",
                ROOT / "src/gems/metric.py",
                ROOT / "src/gems/novelty.py",
                ROOT / "src/gems/c2s2.py",
                ROOT / "src/gems/residualize.py",
                ROOT / "src/gems/submission.py",
                ROOT / "scripts/submission_writer.py",
                Path(__file__),
            )
        },
        "forbidden_columns_verified_unread": sorted(gvc.FORBIDDEN_COLUMNS),
        "prediction_inputs_include_registry_rasters": False,
        "feature_names_base_30": base_names,
        "feature_names_gvc1_18": gvc_names,
        "canary": canary,
        "fold_fit_metadata": fold_fit_meta,
        "full_fit_metadata": {"e1_gvc1": full_meta_e1, "e2_gvc1_resid": full_meta_e2},
        "holdout_results": {
            "B0_oof_h24_ridge": sum_b0,
            "B1_oof_base_submod": sum_b1,
            "E1_h24_gvc1": sum_e1,
            "E2_h24_gvc1_resid": sum_e2,
        },
        "paired_comparisons": paired,
        "novelty_48_rasters": {
            "e1_surface": _slim_nov(nov_e1_surf),
            "e1_final_dots": _slim_nov(nov_e1_dots),
            "e2_surface": _slim_nov(nov_e2_surf),
            "e2_final_dots": _slim_nov(nov_e2_dots),
        },
        "c2st_audit_file": str(C2ST_JSON.relative_to(ROOT)),
        "technical_gates": technical_gates,
        "governance_gates": governance_gates,
        "all_technical_gates_passed": all(technical_gates.values()),
        "ok_to_download": True,
        "ok_to_submit": ok_to_submit,
        "verdict": verdict,
        "blockers": blockers,
        "artifact": {
            "selected_arm": selected_arm,
            "zeros_file": zeros_name,
            "zeros_sha256": chk_zeros["sha256"],
            "nan_file": nan_name,
            "nan_sha256": chk_nan["sha256"],
            "nan_zip_file": zip_path.name,
            "nan_zip_sha256": sha256_file(zip_path),
            "content_id": content_id,
            "pixel_count": int(chk_zeros["in_footprint_positive_pixels"]),
            "note": note,
            "note_length": len(note),
            "note_file": note_file,
            "checks_file": checks_file,
        },
        "submission_slots_used": 0,
        "organizer_confirmed_score": None,
    }
    _save_json(experiment_payload, EXPERIMENT_JSON)

    run_card = {
        "hypothesis": (
            f"H24-{arm_tag}: Geothermal vent/2m-probe/geothermometer upflow + "
            "8-azimuth lineament persistence + Miller-Singh tilt-derivative OOF ensemble "
            "with exact Minoux lazy-greedy 300 m submodular allocation"
        ),
        "mechanism": (
            "Permeable Great Basin fault conduits localize hydrothermal vents (INGENIOUS paleo-sinter/tufa, "
            "shallow 2m F2mDAB thermal plumes, >=37C springs & quartz/chalcedony geothermometers, local K/ThK "
            "& UTh alteration, MT clay-cap edges) along zero-crossing potential-field tilt contacts, piedmont "
            "inflections, and 0.9-2.1 km directional breaklines; allocated via 300 m triangular-kernel submodular coverage"
        ),
        "named_non_fault_mimic": (
            "Perched lateral thermal-groundwater outflow plumes in permeable alluvial-fan paleochannels "
            "and Pleistocene Lake Lahontan shoreline tufa terraces; range-front mining-claim clustering"
        ),
        "holdout": sel_holdout,
        "baselines_same_evaluator": {
            "B0_oof_h24_ridge_dti": sum_b0["dti"],
            "B0_ci95": sum_b0["ci95"]["interval"],
            "B1_oof_base_submod_dti": sum_b1["dti"],
            "B1_ci95": sum_b1["ci95"]["interval"],
            "paired_gain_vs_B0": sel_vs_b0,
            "paired_gain_vs_B1": sel_vs_b1,
        },
        "correlation_overlap_vs_registry": {
            "total_unique_rasters_checked": sel_nov_dots["registry_unique_rasters"],
            "competing_detector_rasters_checked": sel_nov_dots["competing_method_rasters"],
            "calibration_control_rasters_checked": sel_nov_dots["calibration_control_rasters"],
            "surface_max_abs_rank_correlation": sel_nov_surf["max_abs_rank_correlation"],
            "final_max_abs_rank_correlation": sel_nov_dots["max_abs_rank_correlation"],
            "final_max_competing_overlap_within_3px": sel_nov_dots["max_competing_dot_overlap"],
            "final_max_literal_overlap_within_3px": sel_nov_dots["max_dot_overlap"],
            "competing_method_uniqueness_passed": bool(
                sel_nov_surf["competing_method_passed"] and sel_nov_dots["competing_method_passed"]
            ),
            "literal_unseparated_uniqueness_passed": bool(
                sel_nov_dots["literal_unseparated_passed"]
            ),
            "calibration_control_summary": sel_nov_dots["calibration_control_summary"],
            "no_comparator_removed": True,
        },
        "c2st_nuisance_audit": {
            "labels_audited_first": c2st_report["protocol"]["labels_first"],
            "labels_auc": c2st_report["references"]["labels"]["primary"]["observed_auc"],
            "candidate_auc": sel_c2st["primary"]["observed_auc"],
            "candidate_holm_p": sel_c2st["primary"]["holm_p_value"],
            "candidate_margin_vs_null_p95": sel_c2st["primary"]["margin_vs_p95"],
            "strict_c2st_gate_passed": sel_c2st["strict_c2st_gate_passed"],
        },
        "technical_gates": technical_gates,
        "governance_gates": governance_gates,
        "all_technical_gates_passed": all(technical_gates.values()),
        "raster_sha256": chk_zeros["sha256"],
        "nan_companion_sha256": chk_nan["sha256"],
        "validator_output": chk_zeros,
        "nan_validator_output": chk_nan,
        "submission_name": zeros_name,
        "nan_submission_name": nan_name,
        "zip_submission_name": zip_path.name,
        "pixel_count": int(chk_zeros["in_footprint_positive_pixels"]),
        "note": note,
        "note_length": len(note),
        "verdict": verdict,
        "ok_to_download": True,
        "ok_to_submit": ok_to_submit,
        "reasons": blockers,
        "experiments_run": 2,
        "submission_slots_used": 0,
        "organizer_confirmed_score": None,
        "packaging_deviation": (
            "After duplicate-overlap stop (>70% within 3 px of competing range-front detector), exported the unchanged already-computed negative artifact solely for reproducible audit. Zero retuning, zero comparator removal, zero slot spent."
            if not comp_nov_ok
            else None
        ),
    }
    _save_json(run_card, RUN_CARD_JSON)
    _save_json(run_card, ROOT / "docs/data/gvc1_run_card_20261025.json")

    dl_packet = {
        "file": zeros_name,
        "nan_file": nan_name,
        "zip_file": zip_path.name,
        "sha256": chk_zeros["sha256"],
        "nan_sha256": chk_nan["sha256"],
        "zip_sha256": sha256_file(zip_path),
        "content_id": content_id,
        "pixel_count": int(chk_zeros["in_footprint_positive_pixels"]),
        "note": note,
        "note_length": len(note),
        "note_file": note_file,
        "checks_file": checks_file,
        "generation": "independent-gvc1-v1",
        "selected_arm": selected_arm,
        "format_valid": True,
        "all_technical_gates_passed": all(technical_gates.values()),
        "competing_method_uniqueness_passed": bool(
            sel_nov_surf["competing_method_passed"] and sel_nov_dots["competing_method_passed"]
        ),
        "literal_unseparated_uniqueness_passed": bool(sel_nov_dots["literal_unseparated_passed"]),
        "strict_c2st_gate_passed": bool(sel_c2st["strict_c2st_gate_passed"]),
        "ok_to_download": True,
        "ok_to_submit": ok_to_submit,
        "slot_recommendation": "not_recommended" if not ok_to_submit else "selector_eligible",
        "verdict": verdict,
        "live_dti": None,
        "run_card": "gvc1_run_card_20261025.json",
        "independently_computed": True,
    }
    _save_json(dl_packet, DOWNLOAD_JSON)
    return run_card


def verify_gvc1() -> dict[str, Any]:
    exp = json.loads(EXPERIMENT_JSON.read_text())
    card = json.loads(RUN_CARD_JSON.read_text())
    c2st_rep = json.loads(C2ST_JSON.read_text())
    dl = json.loads(DOWNLOAD_JSON.read_text())
    template = ROOT / "data/bridge/sample_submission.tif"
    downloads = ROOT / "docs/downloads"

    z_path = downloads / card["submission_name"]
    n_path = downloads / card["nan_submission_name"]
    zip_path = downloads / card["zip_submission_name"]
    if sha256_file(z_path) != card["raster_sha256"]:
        raise AssertionError("GVC1 zero-outside TIFF SHA-256 mismatch")
    if sha256_file(n_path) != card["nan_companion_sha256"]:
        raise AssertionError("GVC1 NaN-outside TIFF SHA-256 mismatch")
    if sha256_file(zip_path) != dl["zip_sha256"]:
        raise AssertionError("GVC1 single-TIFF ZIP SHA-256 mismatch")

    cz = submission.check_variants(z_path, template)
    cn = submission.check_variants(n_path, template)
    if not (cz["format_valid"] and cn["format_valid"] and cn["official_format_compliant"]):
        raise AssertionError("GVC1 GeoTIFF format check failed")
    if len(card["note"]) > 140:
        raise AssertionError("GVC1 note exceeds 140 chars")
    if not exp["canary"]["passed"]:
        raise AssertionError("GVC1 canary failed")
    if not c2st_rep["protocol"]["labels_first"]:
        raise AssertionError("C2ST labels_first violated")
    if card["organizer_confirmed_score"] is not None or card["submission_slots_used"] != 0:
        raise AssertionError("Live score or slot count misreported")

    return {
        "verified": True,
        "selected_arm": exp["hypothesis_selected"],
        "submission_name": card["submission_name"],
        "raster_sha256": card["raster_sha256"],
        "holdout_dti": card["holdout"]["dti"],
        "b0_dti": card["baselines_same_evaluator"]["B0_oof_h24_ridge_dti"],
        "b1_dti": card["baselines_same_evaluator"]["B1_oof_base_submod_dti"],
        "all_technical_gates_passed": card["all_technical_gates_passed"],
        "ok_to_download": card["ok_to_download"],
        "ok_to_submit": card["ok_to_submit"],
        "verdict": card["verdict"],
    }


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--work-dir", type=Path, default=Path("/tmp/gems_work"))
    ap.add_argument("--stop-after-stage5", action="store_true")
    ap.add_argument("--verify", action="store_true")
    args = ap.parse_args()
    out = (
        verify_gvc1()
        if args.verify
        else run_gvc1(work_dir=args.work_dir, stop_after_stage5=args.stop_after_stage5)
    )
    print(json.dumps(out, indent=2))
