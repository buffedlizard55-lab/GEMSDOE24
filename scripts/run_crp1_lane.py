#!/usr/bin/env python3
"""Execute or verify the preregistered H24-CRP1 lane (2026-10-26).

Frozen spec: ``knowledge/20_preregistered_CRP1_2026-10-26.md`` (committed
before this code).  Reuses the shared template tools only: cached prepared
feature stack, ``gems.holdout.SegmentHoldout`` evaluator, ``gems.submission``
writer/validator, ``gems.novelty`` registry checks, ``gems.c2s2`` audit via
the recorded RSHG1 runner helpers, and the independent ``gems.selector``.

One experiment, zero submission slots, no DrivenData access, no uploads.
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import importlib.util
import json
import os
import sys
import time
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
from sklearn.ensemble import HistGradientBoostingClassifier  # noqa: E402
from threadpoolctl import threadpool_limits  # noqa: E402

from gems import confounds, crp1, footprint, holdout, novelty, rshg1, sahg1, selector, submission  # noqa: E402
from gems.validator import sha256_file  # noqa: E402

# Reuse the recorded RSHG1 runner's baseline/C2ST/peer helpers verbatim
# (shared tools, no private fork of evaluator or audit logic).
_spec = importlib.util.spec_from_file_location("run_rshg1_lane", ROOT / "scripts/run_rshg1_lane.py")
_rshg1_runner = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_rshg1_runner)

SEED = 20261026
BUDGET_FRAC = 0.0073
HGB_PARAMS = dict(
    max_iter=140,
    max_leaf_nodes=31,
    min_samples_leaf=80,
    learning_rate=0.06,
    l2_regularization=8.0,
    early_stopping=False,
)
MEMMAP_PATH = ROOT / "data/prepared/crp1_features.npy"
EXPERIMENT_JSON = ROOT / "evidence/crp1_experiment_20261026.json"
RUN_CARD_JSON = ROOT / "evidence/crp1_run_card_20261026.json"
DOCS_RUN_CARD_JSON = ROOT / "docs/data/crp1_run_card.json"
DOCS_DOWNLOAD_JSON = ROOT / "docs/data/crp1_download.json"
SELECTOR_JSON = ROOT / "evidence/crp1_selector_20261026.json"
PREVIEW_PNG = ROOT / "docs/assets/crp1-preview.png"

LOCAL_EXTRA_DOWNLOADS = (
    ("local-fuse-hcw", "docs/downloads/gems24-fuse-fuse-hcw-hgb-20261025-3fd41218a10a-zeros.tif"),
    ("local-rshg1", "docs/downloads/gems24-rshg1-regime-hydro-hgb-20261025-98f69d77e868-zeros.tif"),
    (
        "local-gvc1",
        "docs/downloads/gems24-gvc1-negative-geothermal-lineament-submod-20261025-abe8e51c719d-zeros.tif",
    ),
    ("local-oj1", "docs/downloads/gems24-oj1-3eef450351de-RESEARCH-NOT-SUBMISSION-zeros.tif"),
    ("local-doer", "docs/downloads/24gems-doer-fault-guided-k-20261025T220208Z-dedb860f7e83-zeros.tif"),
)


def save_json(obj: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n")


def extra_entries(fp: np.ndarray) -> list[dict[str, Any]]:
    """Local 2026-10-25 lanes (RSHG1 helper) plus later local method lanes."""
    out = list(_rshg1_runner.extra_20261025_entries(fp))
    for eid, rel in LOCAL_EXTRA_DOWNLOADS:
        p = ROOT / rel
        if not p.exists():
            # The GVC1 filename carries its build date; tolerate the recorded name only.
            raise FileNotFoundError(f"Expected local comparator missing: {p}")
        with rasterio.open(p) as ds:
            a = ds.read(1)
        out.append(
            {
                "id": eid,
                "repo": "buffedlizard55-lab/GEMSDOE24",
                "file": rel,
                "cache_path": rel,
                "sha256": sha256_file(p),
                "footprint_sha256": hashlib.sha256(
                    np.asarray(a[fp], dtype="<f4").tobytes()
                ).hexdigest(),
                "positive_pixels": int((a[fp] > 0).sum()),
            }
        )
    return out


def streaming_canary(context, mm, fp, names, batch_size: int = 4) -> dict[str, Any]:
    """Two-polarity single-feature canary over the memmap via the shared evaluator."""
    fp_ids = np.flatnonzero(fp)
    merged: dict[str, Any] = {}
    last: dict[str, Any] = {}
    for start in range(0, len(names), batch_size):
        batch: dict[str, np.ndarray] = {}
        for j in range(start, min(start + batch_size, len(names))):
            grid = np.full(fp.shape, np.nan, dtype=np.float32)
            grid.ravel()[fp_ids] = mm[:, j]
            batch[names[j]] = grid
        rep = context.canary(batch, seed=SEED, max_per_class=15000)
        merged.update(rep["features"])
        last = rep
        del batch
        gc.collect()
    worst_name = max(
        merged,
        key=lambda k: max(merged[k]["pooled_auc"], 1.0 - merged[k]["pooled_auc"]),
    )
    worst_auc = float(merged[worst_name]["pooled_auc"])
    return {
        "diagnostic": last["diagnostic"],
        "evaluator_version": last["evaluator_version"],
        "threshold": last["threshold"],
        "two_polarities_checked": True,
        "passed": not any(v["leakage_suspected"] for v in merged.values()),
        "n_features_checked": len(merged),
        "worst_feature": worst_name,
        "worst_pooled_auc": worst_auc,
        "worst_polarity_extremity": max(worst_auc, 1.0 - worst_auc),
        "features": merged,
        "interpretation": last["interpretation"],
    }


def fit_models(mm, nuisance_fp, fp_ids, train_mask, visible_mask, *, seed_base, resid_idx):
    """Selective-residualized 2-seed HGB ensemble, fit on training rows only."""
    dist_vis = distance_transform_edt(~visible_mask)
    pos_rows = np.flatnonzero((train_mask & visible_mask).ravel()[fp_ids])
    neg_rows = np.flatnonzero(
        (train_mask & ~visible_mask & (dist_vis >= 9.0)).ravel()[fp_ids]
    )
    bg_rows = np.flatnonzero((train_mask & ~visible_mask).ravel()[fp_ids])
    del dist_vis
    if len(pos_rows) < 200 or len(neg_rows) < 600:
        raise RuntimeError("Insufficient training positives/negatives")

    rng_bg = np.random.default_rng(seed_base + 77)
    bg_sel = np.sort(rng_bg.choice(bg_rows, min(30_000, len(bg_rows)), replace=False))
    resid = rshg1.NanPreservingResidualizer(
        regional_indices=np.asarray(resid_idx, dtype=np.int64), alpha=100.0
    ).fit(nuisance_fp[bg_sel], np.asarray(mm[bg_sel], dtype=np.float32))

    models = []
    for s_idx in range(2):
        seed_s = seed_base + s_idx
        rng = np.random.default_rng(seed_s)
        p_sel = rng.choice(pos_rows, min(30_000, len(pos_rows)), replace=False)
        n_sel = rng.choice(neg_rows, min(90_000, len(neg_rows)), replace=False)
        tr = np.r_[p_sel, n_sel]
        y = np.r_[np.ones(len(p_sel), np.int8), np.zeros(len(n_sel), np.int8)]
        x = resid.transform(
            nuisance_fp[tr], np.asarray(mm[tr], dtype=np.float32), remove=True
        )
        model = HistGradientBoostingClassifier(**HGB_PARAMS, random_state=seed_s)
        model.fit(x, y)
        models.append(model)
        del x, tr, y
        gc.collect()
    del pos_rows, neg_rows, bg_rows
    gc.collect()
    return models, resid


def sahg1_support(fp, fp_ids, prep_path, prep_names, lidar_meta, rad_meta, ext_meta):
    """Exact SAHG1 support mask used by the recorded OOF baseline recipe."""
    lidar_path = ROOT / "data/external/lidar_scarp_features_u8.tif"
    rad_path = ROOT / "data/external/geodawn_rad_u8.tif"
    ext_path = ROOT / "data/external/geodawn_extensions_u8.tif"
    with rasterio.open(lidar_path) as dlid, rasterio.open(rad_path) as drad, rasterio.open(
        ext_path
    ) as dext:
        rv = fp.copy()
        for bname in sahg1.LIDAR_SPECS:
            rv &= dlid.read(lidar_meta["bands"].index(bname) + 1) > 0
        for bname in sahg1.RAD_BANDS:
            rv &= drad.read(rad_meta["channels"].index(bname) + 1) > 0
        for bname in sahg1.EXT_BANDS:
            rv &= dext.read(ext_meta["channels"].index(bname) + 1) > 0
    prep_mm = np.load(prep_path, mmap_mode="r")
    for gname in sahg1.GEOPHYS_BANDS:
        gmask = np.zeros(fp.shape, dtype=bool)
        gmask.ravel()[fp_ids] = np.isfinite(prep_mm[:, prep_names.index(gname)])
        rv &= gmask
        del gmask
    support = binary_erosion(
        rv,
        structure=np.ones(
            (2 * sahg1.STENCIL_RADIUS_PX + 1, 2 * sahg1.STENCIL_RADIUS_PX + 1), dtype=bool
        ),
        border_value=False,
    )
    del rv
    gc.collect()
    return support


def novelty_card_section(surface_rep, final_rep, peers_surface, peers_final):
    literal_rows = [
        {
            "registry_id": r["registry_id"],
            "file": r["file"],
            "entry_role": r.get("entry_role"),
            "candidate_dot_overlap_within_3px": r["candidate_dot_overlap_within_3px"],
            "raw_spearman": r["raw_spearman"],
            "kernel_spearman": r["kernel_spearman"],
        }
        for r in final_rep["rows"]
        if r["duplicate"]
    ]
    return {
        "surface": {
            "max_abs_rank_correlation": surface_rep["max_abs_rank_correlation"],
            "method_lane_passed": surface_rep["method_lane_passed"],
            "literal_all_entries_passed": surface_rep["literal_all_entries_passed"],
            "registry_unique_rasters": surface_rep["registry_unique_rasters"],
        },
        "final_dots": {
            "max_abs_rank_correlation": final_rep["max_abs_rank_correlation"],
            "method_lane_max_dot_overlap": final_rep["method_lane_max_dot_overlap"],
            "method_lane_passed": final_rep["method_lane_passed"],
            "literal_all_entries_passed": final_rep["literal_all_entries_passed"],
            "competing_method_rasters_count": final_rep["competing_method_rasters_count"],
            "calibration_control_rasters_count": final_rep[
                "calibration_control_rasters_count"
            ],
            "literal_duplicate_rows": literal_rows,
        },
        "peers_surface": peers_surface,
        "peers_final": peers_final,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--verify-recorded", action="store_true")
    args = ap.parse_args()

    template = ROOT / "data/bridge/sample_submission.tif"
    if args.verify_recorded:
        card = json.loads(RUN_CARD_JSON.read_text())
        zeros = ROOT / "docs/downloads" / card["submission_name"]
        receipt = selector.verify_selector(zeros, template, card)
        recorded = json.loads(SELECTOR_JSON.read_text())
        ok = (
            sha256_file(zeros) == card["raster_sha256"]
            and receipt["decision"] == recorded["decision"]
            and receipt["gates"] == recorded["gates"]
        )
        print(json.dumps({"verify_recorded": ok, "selector": receipt}, indent=2))
        if not ok:
            raise SystemExit("Recorded CRP1 verification FAILED")
        return

    if EXPERIMENT_JSON.exists():
        raise SystemExit(
            f"{EXPERIMENT_JSON} already exists; refusing implicit rerun. "
            "Use --verify-recorded."
        )

    t0 = time.monotonic()
    with threadpool_limits(limits=2):
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
        if sha256_file(prep_path) != prep_meta["sha256"]:
            raise SystemExit("Prepared feature stack SHA-256 mismatch")
        if sha256_file(rad_path) != rad_meta["product_sha256"]:
            raise SystemExit("GeoDAWN radiometrics SHA-256 mismatch")
        if sha256_file(ext_path) != ext_meta["product_sha256"]:
            raise SystemExit("GeoDAWN extensions SHA-256 mismatch")

        confounds.build_all(force=False)
        conf_path = confounds.CONF / "confounds.npz"

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

        print(f"[1/7] Building CRP1 40-channel memmap ({len(fp_ids):,} rows)...", flush=True)
        mm, names, resid_idx = crp1.build_crp1_memmap(
            out_path=MEMMAP_PATH,
            footprint=fp,
            prepared_path=prep_path,
            prepared_names=prep_meta["names"],
            training_tif=training_tif,
            ext_tif=ext_path,
            rad_tif=rad_path,
            ext_channels=ext_meta["channels"],
            rad_channels=rad_meta["channels"],
        )
        coverage = {
            n: float(np.isfinite(mm[:, names.index(n)]).mean()) for n in crp1.NEW_FEATURE_NAMES
        }
        print(f"      new-channel finite coverage: {coverage}", flush=True)

        context = holdout.SegmentHoldout(fp, catalogue, buffer_px=15)
        print("[2/7] Two-polarity leakage canaries (40 features)...", flush=True)
        canary = streaming_canary(context, mm, fp, names)
        print(
            f"      passed={canary['passed']} worst={canary['worst_feature']} "
            f"extremity={canary['worst_polarity_extremity']:.4f}",
            flush=True,
        )
        if not canary["passed"]:
            save_json(
                {"verdict": "negative", "stopped_reason": "leakage_canary_failed", "canary": canary},
                EXPERIMENT_JSON,
            )
            raise SystemExit("HALT: leakage canary exceeded 0.90")

        with np.load(conf_path) as c_npz:
            cdict = confounds.classifier_features(c_npz)
            nuisance_fp = np.column_stack(
                [cdict[k].ravel()[fp_ids].astype(np.float32, copy=False) for k in rshg1.NUISANCE_KEYS]
            )
        del cdict
        gc.collect()

        print("[3/7] Fold-local CRP1 fits + emission...", flush=True)
        oof_prob = np.zeros(fp.shape, dtype=np.float32)
        fold_dots: list[np.ndarray] = []
        for fold in context.folds:
            fid = int(fold["id"])
            models, resid = fit_models(
                mm,
                nuisance_fp,
                fp_ids,
                fold["train"],
                fold["visible"],
                seed_base=SEED + 10 * fid,
                resid_idx=resid_idx,
            )
            val_rows = np.flatnonzero(fold["valid"].ravel()[fp_ids])
            p_val = _rshg1_runner.predict_in_chunks(models, resid, None, mm, nuisance_fp, val_rows)
            fold_map = np.zeros(fp.shape, dtype=np.float32)
            fold_map.ravel()[fp_ids[val_rows]] = p_val
            oof_prob += fold_map
            dots = rshg1.emit_rshg1_dots(
                fold_map,
                fold["valid"],
                fold["visible"],
                budget_frac=BUDGET_FRAC,
                min_dist=3.0,
                flank_clearance_px=2.0,
                use_kernel_trace=True,
            )
            fold_dots.append(dots)
            print(f"      fold {fold['name']}: dots={int(dots.sum()):,}", flush=True)
            del models, resid, fold_map, p_val
            gc.collect()

        oof_canary = context.canary({"crp1_oof_prob": oof_prob}, seed=SEED, max_per_class=15000)
        if not oof_canary["passed"]:
            save_json(
                {"verdict": "negative", "stopped_reason": "oof_canary_failed", "canary": canary, "oof_canary": oof_canary},
                EXPERIMENT_JSON,
            )
            raise SystemExit("HALT: OOF surface canary flagged leakage")

        print("[4/7] Reconstructing recorded OOF baseline for paired comparison...", flush=True)
        support = sahg1_support(
            fp, fp_ids, prep_path, prep_meta["names"], lidar_meta, rad_meta, ext_meta
        )
        base_dots = _rshg1_runner.build_recorded_oof_baseline(
            context, prep_path, int(prep_meta["base_count"]), support, fp
        )
        del support
        gc.collect()
        sum_crp1, blk_crp1 = _rshg1_runner.summarize_with_blocks(context, fold_dots)
        sum_base, blk_base = _rshg1_runner.summarize_with_blocks(context, base_dots)
        sahg1_recorded = json.loads((ROOT / "evidence/sahg1_run_card_20261025.json").read_text())
        recorded_oof = float(sahg1_recorded["reconstructed_oof_multiphysics_baseline"]["dti"])
        baseline_reproduced = abs(sum_base["dti"] - recorded_oof) <= 1e-6
        if not baseline_reproduced:
            save_json(
                {
                    "verdict": "negative",
                    "stopped_reason": "baseline_reproduction_drift",
                    "got": sum_base["dti"],
                    "expected": recorded_oof,
                },
                EXPERIMENT_JSON,
            )
            raise SystemExit(f"Baseline drift: got {sum_base['dti']}, expected {recorded_oof}")
        paired = _rshg1_runner.paired_delta_summary(sum_crp1, blk_crp1, sum_base, blk_base)
        # paired_delta_summary uses the RSHG1 runner's SEED for the bootstrap;
        # recompute the CI under this lane's frozen seed for exact reproducibility.
        paired_ci = holdout.pooled_bootstrap(blk_crp1, paired=blk_base, resamples=1999, seed=SEED)
        paired = {
            "delta_dti": float(sum_crp1["dti"] - sum_base["dti"]),
            "ci95": paired_ci,
            "ci95_strictly_positive": bool(paired_ci[0] > 0.0),
            "bootstrap_seed": SEED,
        }
        print(
            f"      HOLDOUT-DTI CRP1={sum_crp1['dti']:.5f} {sum_crp1['ci95']['interval']} "
            f"vs baseline={sum_base['dti']:.5f} (paired delta {paired['delta_dti']:+.5f}, CI {paired['ci95']})",
            flush=True,
        )

        print("[5/7] Full-footprint fit + registry novelty (surface, then dots)...", flush=True)
        models_full, resid_full = fit_models(
            mm, nuisance_fp, fp_ids, fp, catalogue, seed_base=SEED + 900, resid_idx=resid_idx
        )
        all_rows = np.arange(len(fp_ids), dtype=np.int64)
        p_rows = _rshg1_runner.predict_in_chunks(models_full, resid_full, None, mm, nuisance_fp, all_rows)
        p_full = np.zeros(fp.shape, dtype=np.float32)
        p_full.ravel()[fp_ids] = p_rows
        del models_full, resid_full, p_rows, all_rows, nuisance_fp
        gc.collect()

        trace = rshg1.kernel_trace_score(p_full, fp, catalogue)
        priority_reg = json.loads((ROOT / "registry/priority_rasters.json").read_text())
        extras = extra_entries(fp)
        surface_rep = novelty.compare_prospective_registry(
            trace, fp, priority_reg["unique_rasters"], ROOT, sample_size=200_000, extra_entries=extras
        )
        peers_surface = _rshg1_runner.check_peer_blobs(trace, None, fp)
        if (surface_rep["max_abs_rank_correlation"] or 0) > 0.90 or not peers_surface["passed"]:
            save_json(
                {
                    "verdict": "negative",
                    "stopped_reason": "pre_placement_surface_duplicate",
                    "surface": surface_rep,
                    "peers_surface": peers_surface,
                },
                EXPERIMENT_JSON,
            )
            raise SystemExit("HALT: pre-placement surface is a registry duplicate (Protocol §1)")

        final_dots = rshg1.emit_rshg1_dots(
            p_full,
            fp,
            catalogue,
            budget_frac=BUDGET_FRAC,
            min_dist=3.0,
            flank_clearance_px=2.0,
            use_kernel_trace=True,
        )
        final_rep = novelty.compare_prospective_registry(
            trace,
            fp,
            priority_reg["unique_rasters"],
            ROOT,
            dots=final_dots,
            sample_size=200_000,
            extra_entries=extras,
        )
        peers_final = _rshg1_runner.check_peer_blobs(trace, final_dots, fp)
        print(
            f"      novelty: method_passed={final_rep['method_lane_passed']} "
            f"max_overlap={final_rep['method_lane_max_dot_overlap']} "
            f"max|rho|={final_rep['max_abs_rank_correlation']} "
            f"peers_passed={peers_final['passed']} peer_overlap={peers_final['max_dot_overlap_within_3px']} "
            f"literal={final_rep['literal_all_entries_passed']}",
            flush=True,
        )
        del trace, p_full
        gc.collect()

        print("[6/7] Writing GeoTIFF pair + shared validator...", flush=True)
        content_id = submission.scored_content_id(final_dots, fp, catalogue)
        zeros_name = submission.make_filename(
            "gems24", "crp1-compfront-xdepth-saddle", "20261026", content_id, "zeros"
        )
        nan_name = zeros_name.replace("-zeros.tif", "-nan.tif")
        downloads = ROOT / "docs/downloads"
        zeros_path = submission.write_submission(
            final_dots.astype(np.float32), template, downloads / zeros_name, outside="zero"
        )
        nan_path = submission.write_submission(
            final_dots.astype(np.float32), template, downloads / nan_name, outside="nan"
        )
        zero_checks = submission.check_variants(zeros_path, template)
        nan_checks = submission.check_variants(nan_path, template)
        if (
            not zero_checks["format_valid"]
            or not nan_checks["format_valid"]
            or not _rshg1_runner.strict_whole_array_ok(zero_checks)
        ):
            raise SystemExit("Written GeoTIFF failed format or strict [0,1] check")
        _rshg1_runner.write_preview(final_dots, fp, PREVIEW_PNG)
        min_cat_dist = float(distance_transform_edt(~catalogue)[final_dots].min())
        n_dots = int(final_dots.sum())

        print("[7/7] Exact-file C2ST nuisance audit...", flush=True)
        c2st_report = _rshg1_runner.run_exact_file_c2st(zeros_path, fp, catalogue)
        print(
            f"      C2ST candidate AUC={c2st_report['observed_auc']:.4f} "
            f"strict_gate_passed={c2st_report['strict_gate_passed']}",
            flush=True,
        )

        nov_section = novelty_card_section(surface_rep, final_rep, peers_surface, peers_final)
        experiment = {
            "lane": "H24-CRP1",
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "preregistration": "knowledge/20_preregistered_CRP1_2026-10-26.md",
            "input_hashes": input_hashes,
            "feature_names": names,
            "residualized_indices": resid_idx,
            "new_channel_finite_coverage": coverage,
            "canary": canary,
            "oof_canary": oof_canary,
            "holdout": sum_crp1,
            "baseline": sum_base,
            "baseline_recorded_dti": recorded_oof,
            "baseline_reproduced": baseline_reproduced,
            "paired_vs_baseline": paired,
            "novelty_surface_rows": surface_rep["rows"],
            "novelty_final_rows": final_rep["rows"],
            "novelty": nov_section,
            "c2st_exact_file": c2st_report,
            "validator_zero": zero_checks,
            "validator_nan": nan_checks,
            "n_dots": n_dots,
            "min_catalogue_distance_px": min_cat_dist,
            "elapsed_s": time.monotonic() - t0,
        }
        save_json(experiment, EXPERIMENT_JSON)

        note = (
            f"GEMS24 CRP1 | comp-front+xdepth+saddle sel-resid HGB | "
            f"HOLDOUT-DTI {sum_crp1['dti']:.5f} | id {content_id}"
        )
        assert len(note) <= 140, len(note)

        card = {
            "hypothesis": (
                "H24-CRP1: compositional radiometric fronts (contractor UK/UTh/ThK + K/Th/U "
                "rank balances) + cross-depth TMI/up150 persistence + DEM/gravity Hessian "
                "saddles, with selective nuisance residualization of airborne bands only"
            ),
            "mechanism": (
                "Concealed faults juxtapose/alter mobile-element (K,U) balance against stable "
                "Th, persist between shallow TMI and its 150 m upward continuation, and "
                "concentrate at step-over saddles; emitted as sparse binary dots with >2 px "
                "catalogue clearance, >=3 px spacing, 300 m kernel-trace ranking"
            ),
            "named_non_fault_mimic": (
                "Transported arkosic alluvium / lithologic contacts (compositional fronts); "
                "magnetite-poor palaeochannel or remanence (cross-depth persistence); pluvial "
                "shoreline saddle; flight-line levelling seams"
            ),
            "holdout": sum_crp1,
            "paired_vs_baseline": {
                **paired,
                "baseline_name": "oof_multiphysics_hgb_d3 (reconstructed in-session)",
                "baseline_dti": sum_base["dti"],
            },
            "baseline_reproduced": baseline_reproduced,
            "recorded_best_same_evaluator": {
                "lane": "H24-GVC1",
                "dti": selector.RECORDED_BEST_DTI,
                "source": "evidence/gvc1_run_card_20261025.json",
            },
            "leakage_canary": canary,
            "novelty": nov_section,
            "correlation_overlap_vs_registry": {
                "surface_max_abs_rank_correlation": surface_rep["max_abs_rank_correlation"],
                "final_max_abs_rank_correlation": final_rep["max_abs_rank_correlation"],
                "final_max_method_overlap_within_3px": final_rep["method_lane_max_dot_overlap"],
                "final_max_peer_overlap_within_3px": peers_final["max_dot_overlap_within_3px"],
                "method_lane_passed": final_rep["method_lane_passed"],
                "literal_all_entries_passed": final_rep["literal_all_entries_passed"],
            },
            "c2st_exact_file": {"labels_audited_first": True, **c2st_report},
            "raster_sha256": sha256_file(zeros_path),
            "nan_companion_sha256": sha256_file(nan_path),
            "validator_output": zero_checks,
            "nan_validator_output": nan_checks,
            "submission_name": zeros_name,
            "nan_submission_name": nan_name,
            "pixel_count": n_dots,
            "note": note,
            "note_length": len(note),
            "experiments_run": 1,
            "submission_slots_used": 0,
            "organizer_confirmed_score": None,
            "input_hashes": input_hashes,
            "preregistration": "knowledge/20_preregistered_CRP1_2026-10-26.md",
        }

        receipt = selector.verify_selector(zeros_path, template, card)
        if not receipt["ok_to_submit"]:
            neg_note = (
                f"GEMS24 CRP1 | comp-front+xdepth+saddle | NEGATIVE gate stop; "
                f"DO NOT SUBMIT | id {content_id}"
            )
            assert len(neg_note) <= 140, len(neg_note)
            card["note"] = neg_note
            card["note_length"] = len(neg_note)
            receipt = selector.verify_selector(zeros_path, template, card)

        promote = bool(receipt["ok_to_submit"])
        card.update(
            {
                "selector_receipt": receipt,
                "verdict": "promote" if promote else "negative",
                "ok_to_download": True,
                "ok_to_submit": promote,
                "reasons": receipt["reasons"],
            }
        )
        save_json(card, RUN_CARD_JSON)
        save_json(card, DOCS_RUN_CARD_JSON)
        save_json(receipt, SELECTOR_JSON)
        save_json(receipt, downloads / zeros_name.replace(".tif", ".selector.json"))
        (downloads / f"note-{zeros_name.replace('.tif', '.txt')}").write_text(card["note"] + "\n")
        save_json(
            {"zero_outside": {"file": zeros_name, "submission_authorized": promote, **zero_checks}},
            downloads / f"checks-{zeros_name.replace('.tif', '.json')}",
        )
        save_json(
            {
                "file": zeros_name,
                "nan_file": nan_name,
                "note": card["note"],
                "note_file": f"note-{zeros_name.replace('.tif', '.txt')}",
                "sha256": card["raster_sha256"],
                "nan_sha256": card["nan_companion_sha256"],
                "pixel_count": n_dots,
                "ok_to_download": True,
                "ok_to_submit": promote,
                "selector_decision": receipt["decision"],
                "holdout_dti": sum_crp1["dti"],
                "holdout_ci95": sum_crp1["ci95"]["interval"],
            },
            DOCS_DOWNLOAD_JSON,
        )
        print(
            f"DONE verdict={card['verdict']} ok_to_submit={promote} "
            f"file={zeros_name} sha256={card['raster_sha256']} dots={n_dots}",
            flush=True,
        )


if __name__ == "__main__":
    main()
