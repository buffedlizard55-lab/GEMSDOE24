#!/usr/bin/env python3
"""Execute or verify H24-CGMK1 exactly as preregistered (knowledge/32_...).

Budget: 2 priced experiments (EXP-1 primary 37ch, EXP-2 matched 25ch
control), zero submission slots. Shared tools only: SegmentHoldout,
priority_poisson, submission_writer functions, novelty.compare_registry.
Refuses to rerun once the run card exists.
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt
from sklearn.ensemble import HistGradientBoostingClassifier
from threadpoolctl import threadpool_limits

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems import benchmarks, cgmk1, emission, holdout, novelty, submission  # noqa: E402
from gems.validator import sha256_file  # noqa: E402

LANE = "H24-CGMK1"
SEED = 20261027
FULL_DOT_BUDGET = 37654
HGB = {
    "max_iter": 80,
    "max_leaf_nodes": 15,
    "learning_rate": 0.08,
    "l2_regularization": 5.0,
    "early_stopping": False,
}
WORK = ROOT / "data/prepared/cgmk1_work"
EXPERIMENT_JSON = ROOT / "evidence/cgmk1_experiment_20261027.json"
RUN_CARD_JSON = ROOT / "evidence/cgmk1_run_card_20261027.json"
DOWNLOADS = ROOT / "docs/downloads"
TEMPLATE = ROOT / "data/bridge/sample_submission.tif"
LABELS = ROOT / "data/bridge/labels.tif"
TAU_LATTICE = 0.002444501885533123  # evidence/emission_calibration.json


def save(obj: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, allow_nan=False, default=float) + "\n")


def stage(name: str) -> Path:
    WORK.mkdir(parents=True, exist_ok=True)
    return WORK / f"{name}.json"


def done(name: str) -> dict | None:
    p = stage(name)
    return json.loads(p.read_text()) if p.exists() else None


def grid_from_vec(vec: np.ndarray, fp_ids: np.ndarray, shape) -> np.ndarray:
    g = np.zeros(shape, np.float32)
    g.ravel()[fp_ids] = vec
    return g


def assemble(stack, condk, idx: np.ndarray, mode: str) -> np.ndarray:
    if mode == "control25":
        return np.asarray(stack[idx, :25], dtype=np.float32)
    return np.hstack(
        [np.asarray(stack[idx, :], dtype=np.float32), np.asarray(condk[idx, :], dtype=np.float32)]
    ).astype(np.float32)


def predict_surface(clf, stack, condk, idx_all, fp_ids, shape, mode) -> np.ndarray:
    surf = np.zeros(shape, np.float32)
    for s in range(0, len(idx_all), 150_000):
        ch = idx_all[s : s + 150_000]
        surf.ravel()[fp_ids[ch]] = clf.predict_proba(assemble(stack, condk, ch, mode))[:, 1]
    return surf


def fit_hgb(x: np.ndarray, y: np.ndarray, seed: int):
    return HistGradientBoostingClassifier(**HGB, random_state=seed).fit(x, y)


def local_registry_entries(fp: np.ndarray) -> tuple[list[dict], list[dict]]:
    """Content-deduped registry from locally present, footprint-finite rasters."""
    candidates = (
        sorted(DOWNLOADS.glob("*-zeros.tif"))
        + sorted(DOWNLOADS.glob("*-allfinite.tif"))
        + sorted((ROOT / "inputs").glob("*-allfinite.tif"))
        + sorted((ROOT / "inputs/calibration").glob("*.tif"))
    )
    seen: set[str] = set()
    entries, skipped = [], []
    for p in candidates:
        if "cgmk1" in p.name.lower():
            continue
        try:
            with rasterio.open(p) as ds:
                if ds.count != 1 or ds.shape != fp.shape or str(ds.crs) != "EPSG:32611":
                    skipped.append({"file": str(p.relative_to(ROOT)), "reason": "grid/count/crs"})
                    continue
                a = ds.read(1)
        except Exception as exc:  # unreadable comparator is recorded, never silently dropped
            skipped.append({"file": str(p.relative_to(ROOT)), "reason": f"read error: {exc}"})
            continue
        inside = a[fp]
        if not np.isfinite(inside).all() or np.any((inside < 0) | (inside > 1)):
            skipped.append(
                {
                    "file": str(p.relative_to(ROOT)),
                    "reason": "non-finite or out of [0,1] in footprint",
                }
            )
            continue
        fp_sha = hashlib.sha256(np.asarray(inside, dtype="<f4").tobytes()).hexdigest()
        del a, inside
        if fp_sha in seen:
            skipped.append(
                {"file": str(p.relative_to(ROOT)), "reason": "duplicate footprint content"}
            )
            continue
        seen.add(fp_sha)
        rel = str(p.relative_to(ROOT))
        entries.append(
            {
                "id": f"local-{len(entries) + 1:03d}",
                "repo": "buffedlizard55-lab/GEMSDOE24 (local checkout)",
                "file": rel,
                "cache_path": rel,
                "sha256": sha256_file(p),
                "footprint_sha256": fp_sha,
            }
        )
    return entries, skipped


def projection(holdout_result: dict, n_dots: int, area: int) -> dict:
    """MODEL PROJECTION (not a score) under preregistered stated assumptions."""
    coverage = float(holdout_result["TP_w"] / holdout_result["n_truth"])
    rows = []
    for tau_f in (0.8, 1.0, 1.2):
        for phi in (0.0, 0.05, 0.10):
            tau = TAU_LATTICE * tau_f
            rows.append(
                {
                    "tau_factor": tau_f,
                    "phi": phi,
                    "model_dti": float(
                        emission.model_dti(coverage * tau, n_dots / area, tau, phi=phi)
                    ),
                }
            )
    vals = [r["model_dti"] for r in rows]
    return {
        "label": "MODEL PROJECTION - NOT A SCORE, NOT ORGANIZER-CONFIRMED",
        "method": "emission.model_dti, credit rate = holdout coverage, lattice-calibrated tau",
        "assumptions": [
            "hidden new faults are credited at the same rate as withheld catalogue faults (likely false in detail)",
            "tau from the blind spacing-5 lattice owner-reported score 0.0904 (evidence/emission_calibration.json)",
            "FP mass ~ N(1-phi); phi and tau swept, never fitted to a desired answer",
        ],
        "holdout_coverage_used": coverage,
        "tau_central": TAU_LATTICE,
        "sweep": rows,
        "range": [min(vals), max(vals)],
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--verify-recorded", action="store_true")
    ap.add_argument("--force-stack", action="store_true")
    args = ap.parse_args()
    if args.verify_recorded:
        card = json.loads(RUN_CARD_JSON.read_text())
        tif = ROOT / card["submission"]["zeros_tif_path"]
        checks = submission.check_variants(tif, TEMPLATE)
        ok = (
            checks["format_valid"]
            and checks["sha256"] == card["submission"]["zeros_tif_sha256"]
            and checks["in_footprint_positive_pixels"] == card["submission"]["positive_pixels"]
        )
        print(
            json.dumps(
                {"verified": bool(ok), "experiment_rerun": False, "checks_sha": checks["sha256"]},
                indent=2,
            )
        )
        if not ok:
            raise SystemExit("Recorded CGMK1 artifact failed verification")
        return
    if RUN_CARD_JSON.exists():
        raise SystemExit("CGMK1 already recorded; use --verify-recorded (no silent rerun/retune)")

    t0 = time.monotonic()
    report: dict[str, Any] = {
        "lane": LANE,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "preregistration": "knowledge/32_preregistered_CGMK1_2026-10-27.md",
        "preregistration_commits": ["9b280a3", "8dafdc5"],
        "experiments_priced": ["EXP-1 primary 37ch", "EXP-2 matched 25ch control"],
        "submission_slots_spent": 0,
        "organizer_confirmed_score": None,
    }
    # Selection floor BEFORE this lane's card exists (cannot include itself).
    report["selection_floor_before_run"] = benchmarks.selection_floor(ROOT)
    floor_dti = float(report["selection_floor_before_run"]["holdout"]["dti"])
    report["selection_floor_dti"] = floor_dti
    print(
        f"[cgmk1] selection floor (pre-run) = {floor_dti:.5f} "
        f"({report['selection_floor_before_run']['lane']})",
        flush=True,
    )

    with rasterio.open(TEMPLATE) as t:
        fp = np.isfinite(t.read(1))
    with rasterio.open(LABELS) as s:
        catalogue = (s.read(1) > 0) & fp
    assert int(catalogue.sum()) == 60988
    fp_ids = np.flatnonzero(fp.ravel())
    shape = fp.shape

    # ---- Stage 0: stack + support -------------------------------------------------
    if done("stage0") is None:
        meta = cgmk1.build_stack33(ROOT, WORK, fp, force=args.force_stack)
        save({"stack_meta": meta}, stage("stage0"))
    else:
        meta = done("stage0")["stack_meta"]
    stack = np.load(WORK / "cgmk1_stack33.npy", mmap_mode="r")
    support = np.load(WORK / "cgmk1_support.npy")
    sup_vec = support.ravel()[fp_ids]
    names = list(meta["names"])
    report["stack"] = meta
    print(f"[cgmk1] stack {stack.shape} support {int(support.sum())}", flush=True)

    # Global (label-free) conditional-K fit: canary grids + final full fit only.
    condk_global_path = WORK / "condk_global.npy"
    if not (WORK / "condk_global coeffs.json").exists():
        sup_idx = np.flatnonzero(sup_vec)
        stride = max(1, len(sup_idx) // 200_000)
        sample = sup_idx[::stride][:200_000]
        coeffs_global = cgmk1.fit_condk_coeffs(
            np.asarray(stack[sample, names.index("rad_K")]),
            np.asarray(stack[sample, names.index("rad_Th")]),
            np.asarray(stack[sample, names.index("rad_U")]),
        )
        save(
            {
                "coeffs": [float(c) for c in coeffs_global],
                "fit_rows": int(len(sample)),
                "fit_scope": "all supported footprint rows (label-free); used for canary + final full fit only",
            },
            WORK / "condk_global coeffs.json",
        )
    coeffs_global = np.array(json.loads((WORK / "condk_global coeffs.json").read_text())["coeffs"])
    if not condk_global_path.exists():
        cgmk1.build_condk_matrix(stack, names, fp, support, coeffs_global, condk_global_path)
    condk_global = np.load(condk_global_path, mmap_mode="r")

    context = holdout.SegmentHoldout(fp, catalogue, buffer_px=15)
    report["fold_integrity"] = [
        {
            "fold": f["name"],
            "withheld_positive_pixels": int(f["truth"].sum()),
            "hidden_whole_components": int(len(f["hidden_component_ids"])),
            "visible_fault_pixels": int(f["visible"].sum()),
            "train_valid_overlap": bool((f["train"] & f["valid"]).any()),
            "hidden_component_in_visible": bool(
                np.isin(context.components[f["visible"]], f["hidden_component_ids"]).any()
            ),
        }
        for f in context.folds
    ]
    assert sum(r["withheld_positive_pixels"] for r in report["fold_integrity"]) == 60988

    # ---- Stage 1: leakage canary on every channel ----------------------------------
    if done("stage1_canary") is None:
        merged: dict[str, Any] = {}
        all_names = names + list(cgmk1.CONDK4)
        for s in range(0, len(all_names), 6):
            batch = {}
            for nm in all_names[s : s + 6]:
                if nm in names:
                    vec = np.asarray(stack[:, names.index(nm)], dtype=np.float32)
                else:
                    vec = np.asarray(condk_global[:, cgmk1.CONDK4.index(nm)], dtype=np.float32)
                batch[nm] = grid_from_vec(
                    np.where(np.isfinite(vec), vec, 0.0).astype(np.float32), fp_ids, shape
                )
                del vec
            res = context.canary(batch)
            merged.update(res["features"])
            del batch, res
            gc.collect()
            print(
                f"[cgmk1] canary batch to {min(s + 6, len(all_names))}/{len(all_names)}", flush=True
            )
        canary = {
            "diagnostic": "LEAKAGE-CANARY AUC, not a DTI or organizer score",
            "evaluator_version": holdout.MTR_EVALUATOR_VERSION,
            "threshold_two_polarity_extremity": 0.90,
            "passed": not any(v["leakage_suspected"] for v in merged.values()),
            "worst_feature": max(
                merged, key=lambda k: max(merged[k]["pooled_auc"], 1 - merged[k]["pooled_auc"])
            ),
            "features": merged,
        }
        canary["worst_extremity"] = max(
            max(v["pooled_auc"], 1 - v["pooled_auc"]) for v in merged.values()
        )
        save(canary, stage("stage1_canary"))
    report["canary"] = done("stage1_canary")
    print(
        f"[cgmk1] canary passed={report['canary']['passed']} worst={report['canary']['worst_feature']} "
        f"extremity={report['canary']['worst_extremity']:.4f}",
        flush=True,
    )
    if not report["canary"]["passed"]:
        report.update(
            verdict="negative", stop_reason="leakage canary failed (AUC extremity > 0.90)"
        )
        save(report, EXPERIMENT_JSON)
        raise SystemExit("Canary failed; stopping before modelling (run card not written)")

    total_offcat = int((fp & ~catalogue).sum())

    # ---- Stage 2: EXP-1 + EXP-2 fold holdout ---------------------------------------
    dots1_paths, dots2_paths = [], []
    oof_surface_path = WORK / "oof_surface_exp1.npy"
    fold_meta = []
    if done("stage2") is None:
        oof = np.zeros(shape, np.float32)
        with threadpool_limits(limits=2):
            for fold in context.folds:
                fid = int(fold["id"])
                fname = fold["name"]
                t_fold = time.monotonic()
                dist_vis = distance_transform_edt(~fold["visible"])
                tr_vec = fold["train"].ravel()[fp_ids]
                vis_vec = fold["visible"].ravel()[fp_ids]
                dist_vec = dist_vis.ravel()[fp_ids]
                pos_idx = np.flatnonzero(sup_vec & tr_vec & vis_vec)
                neg_idx = np.flatnonzero(sup_vec & tr_vec & ~vis_vec & (dist_vec >= 9))
                rng = np.random.default_rng(SEED + fid)
                pos_sel = rng.choice(pos_idx, min(20_000, len(pos_idx)), replace=False)
                neg_sel = rng.choice(neg_idx, min(60_000, len(neg_idx)), replace=False)
                tr_sel = np.r_[pos_sel, neg_sel]
                y_tr = np.r_[np.ones(len(pos_sel), np.int8), np.zeros(len(neg_sel), np.int8)]

                # Fold-fit conditional-K (train-fold supported rows only; label-free).
                fit_idx = np.flatnonzero(sup_vec & tr_vec)
                stride = max(1, len(fit_idx) // 200_000)
                fit_sample = fit_idx[::stride][:200_000]
                coeffs = cgmk1.fit_condk_coeffs(
                    np.asarray(stack[fit_sample, names.index("rad_K")]),
                    np.asarray(stack[fit_sample, names.index("rad_Th")]),
                    np.asarray(stack[fit_sample, names.index("rad_U")]),
                )
                condk_path = WORK / f"condk_fold{fid}.npy"
                condk = cgmk1.build_condk_matrix(stack, names, fp, support, coeffs, condk_path)

                val_idx = np.flatnonzero(fold["valid"].ravel()[fp_ids])
                eligible = support & fold["valid"] & ~fold["visible"] & (dist_vis > 2.0)
                budget = int(
                    round(
                        FULL_DOT_BUDGET
                        * int((fold["valid"] & ~fold["visible"]).sum())
                        / total_offcat
                    )
                )

                fold_entry: dict[str, Any] = {
                    "fold": fname,
                    "budget": budget,
                    "n_pos_train": int(len(pos_sel)),
                    "n_neg_train": int(len(neg_sel)),
                    "condk_coeffs_fold_fit": [float(c) for c in coeffs],
                }
                for arm, mode, paths_list in (
                    ("exp1", "full37", dots1_paths),
                    ("exp2", "control25", dots2_paths),
                ):
                    clf = fit_hgb(
                        assemble(stack, condk, tr_sel, mode),
                        y_tr,
                        SEED + 100 * fid + (0 if arm == "exp1" else 1),
                    )
                    surf = predict_surface(clf, stack, condk, val_idx, fp_ids, shape, mode)
                    dots = emission.priority_poisson(surf, eligible, budget, min_dist=3.0)
                    p = WORK / f"dots_{arm}_fold{fid}.npy"
                    np.save(p, dots.astype(np.uint8))
                    paths_list.append(str(p.name))
                    if arm == "exp1":
                        oof[fold["valid"]] = surf[fold["valid"]]
                    fold_entry[f"{arm}_dots_emitted"] = int(dots.sum())
                    del clf, surf, dots
                    gc.collect()
                fold_meta.append(fold_entry)
                del condk, dist_vis, tr_vec, vis_vec, dist_vec, pos_idx, neg_idx, fit_idx
                gc.collect()
                print(
                    f"[cgmk1] fold {fname} done in {time.monotonic() - t_fold:.0f}s "
                    f"budget={budget}",
                    flush=True,
                )
        np.save(oof_surface_path, oof)
        del oof
        save(
            {"fold_meta": fold_meta, "dots_exp1": dots1_paths, "dots_exp2": dots2_paths},
            stage("stage2"),
        )
    s2 = done("stage2")
    fold_meta = s2["fold_meta"]
    dots1 = [np.load(WORK / p) for p in s2["dots_exp1"]]
    dots2 = [np.load(WORK / p) for p in s2["dots_exp2"]]
    if done("stage2_scores") is None:
        h1 = context.summarize(dots1)
        h2 = context.summarize(dots2)
        paired = context.compare_paired(dots1, dots2)
        oof_canary = context.canary({"oof_surface_exp1": np.load(oof_surface_path)})
        save(
            {
                "exp1_holdout": h1,
                "exp2_holdout_control": h2,
                "paired_exp1_minus_exp2": paired,
                "oof_surface_canary": oof_canary,
            },
            stage("stage2_scores"),
        )
    sc = done("stage2_scores")
    report["arms"] = {"fold_meta": fold_meta, **sc}
    report["canary_oof_surface"] = sc["oof_surface_canary"]
    print(
        f"[cgmk1] EXP-1 HOLDOUT-DTI {sc['exp1_holdout']['dti']:.5f} "
        f"CI {sc['exp1_holdout']['ci95']['interval']} | EXP-2 control "
        f"{sc['exp2_holdout_control']['dti']:.5f} | floor {floor_dti:.5f}",
        flush=True,
    )
    if not sc["oof_surface_canary"]["passed"]:
        report.update(verdict="negative", stop_reason="OOF surface canary failed")
        save(report, EXPERIMENT_JSON)
        raise SystemExit("OOF canary failed; stopping before placement")

    # ---- Stage 3: pre-placement novelty on the OOF surface -------------------------
    entries, skipped = local_registry_entries(fp)
    report["registry_scope"] = {
        "entries_used": len(entries),
        "skipped": skipped,
        "scope_limit": "Locally present footprint-finite rasters only; pinned cross-repo registry "
        "rasters under data/research are not present in this sandbox checkout.",
    }
    if done("stage3_novelty_surface") is None:
        oof = np.load(oof_surface_path)
        oof = np.where(fp & np.isfinite(oof), oof, 0.0).astype(np.float32)
        nov_surface = novelty.compare_registry(
            oof,
            fp,
            entries,
            ROOT,
            dots=None,
            sample_size=100_000,
            separate_calibration_controls=True,
        )
        save(nov_surface, stage("stage3_novelty_surface"))
        del oof
    nov_surface = done("stage3_novelty_surface")
    report["novelty_surface_before_placement"] = nov_surface
    print(
        f"[cgmk1] surface novelty: literal_pass={nov_surface['passed']} "
        f"competing_pass={nov_surface.get('competing_method_passed')} "
        f"max|rho|={nov_surface['max_abs_rank_correlation']}",
        flush=True,
    )
    rank_duplicate = any(
        (r["raw_spearman"] is not None and abs(r["raw_spearman"]) > 0.90)
        or (r["kernel_spearman"] is not None and abs(r["kernel_spearman"]) > 0.90)
        for r in nov_surface["rows"]
    )
    if rank_duplicate:
        report.update(
            verdict="negative", stop_reason="pre-placement rank-correlation duplicate (>0.90)"
        )
        save(report, EXPERIMENT_JSON)
        raise SystemExit("Duplicate on surface before placement; stopping")

    # ---- Stage 4: full fit, emission, final novelty, validation --------------------
    if done("stage4") is None:
        rng = np.random.default_rng(SEED)
        dist_cat = distance_transform_edt(~catalogue)
        cat_vec = catalogue.ravel()[fp_ids]
        dist_vec = dist_cat.ravel()[fp_ids]
        pos_idx = np.flatnonzero(sup_vec & cat_vec)
        neg_idx = np.flatnonzero(sup_vec & ~cat_vec & (dist_vec >= 9))
        pos_sel = rng.choice(pos_idx, min(40_000, len(pos_idx)), replace=False)
        neg_sel = rng.choice(neg_idx, min(120_000, len(neg_idx)), replace=False)
        tr_sel = np.r_[pos_sel, neg_sel]
        y_tr = np.r_[np.ones(len(pos_sel), np.int8), np.zeros(len(neg_sel), np.int8)]
        with threadpool_limits(limits=2):
            clf = fit_hgb(assemble(stack, condk_global, tr_sel, "full37"), y_tr, SEED)
            surface = predict_surface(
                clf, stack, condk_global, np.arange(len(fp_ids)), fp_ids, shape, "full37"
            )
        del clf
        eligible = support & fp & ~catalogue & (dist_cat > 2.0)
        dots = emission.priority_poisson(surface, eligible, FULL_DOT_BUDGET, min_dist=3.0)
        np.save(WORK / "full_surface.npy", surface)
        np.save(WORK / "full_dots.npy", dots.astype(np.uint8))
        save(
            {
                "full_dots": int(dots.sum()),
                "n_pos_train": int(len(pos_sel)),
                "n_neg_train": int(len(neg_sel)),
                "eligible_pixels": int(eligible.sum()),
            },
            stage("stage4"),
        )
        del surface, dots, dist_cat
        gc.collect()
    s4 = done("stage4")
    surface = np.load(WORK / "full_surface.npy")
    dots = np.load(WORK / "full_dots.npy").astype(bool)
    if int(dots.sum()) != FULL_DOT_BUDGET:
        report["dot_budget_warning"] = f"emitted {int(dots.sum())} != budget {FULL_DOT_BUDGET}"
    if done("stage5_novelty_dots") is None:
        surf_finite = np.where(fp & np.isfinite(surface), surface, 0.0).astype(np.float32)
        nov_dots = novelty.compare_registry(
            surf_finite,
            fp,
            entries,
            ROOT,
            dots=dots.astype(np.uint8),
            sample_size=100_000,
            separate_calibration_controls=True,
        )
        save(nov_dots, stage("stage5_novelty_dots"))
        del surf_finite
    nov_dots = done("stage5_novelty_dots")
    report["novelty_final_dots"] = nov_dots
    print(
        f"[cgmk1] final dots novelty: literal_pass={nov_dots['passed']} "
        f"competing_pass={nov_dots.get('competing_method_passed')} "
        f"max_competing_overlap={nov_dots.get('max_competing_dot_overlap')} "
        f"max|rho|={nov_dots['max_abs_rank_correlation']}",
        flush=True,
    )

    h1 = sc["exp1_holdout"]
    holds_floor = float(h1["dti"]) > floor_dti
    primary_not_harmful = float(h1["dti"]) >= float(sc["exp2_holdout_control"]["dti"])
    novelty_competing_pass = bool(nov_dots.get("competing_method_passed"))
    gate = {
        "format_placeholder_pending_write": True,
        "canary_all_channels": bool(report["canary"]["passed"]),
        "canary_oof_surface": bool(sc["oof_surface_canary"]["passed"]),
        "holdout_point_beats_selection_floor": bool(holds_floor),
        "primary_not_worse_than_control_point": bool(primary_not_harmful),
        "novelty_rank_and_competing_overlap": novelty_competing_pass,
        "novelty_literal_including_space_filling_controls": bool(nov_dots["passed"]),
        "dot_budget_exact": int(dots.sum()) == FULL_DOT_BUDGET,
    }
    promote = all(
        gate[k]
        for k in (
            "canary_all_channels",
            "canary_oof_surface",
            "holdout_point_beats_selection_floor",
            "primary_not_worse_than_control_point",
            "novelty_rank_and_competing_overlap",
            "dot_budget_exact",
        )
    )
    verdict = "promote" if promote else "negative"
    tag = "selector-review" if promote else "negative"

    pred = np.where(dots, 1.0, 0.0).astype(np.float32)
    content_id = submission.scored_content_id(pred, fp, catalogue)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    base = f"gems24-cgmk1-{tag}-signed-gravmag-condk-{stamp}-{content_id}"
    zeros_path = DOWNLOADS / f"{base}-zeros.tif"
    nan_path = DOWNLOADS / f"{base}-nan.tif"
    submission.write_submission(pred, TEMPLATE, zeros_path, outside="zero")
    submission.write_submission(pred, TEMPLATE, nan_path, outside="nan")
    zip_path = submission.zip_single(zeros_path)
    checks_zeros = submission.check_variants(zeros_path, TEMPLATE)
    checks_nan = submission.check_variants(nan_path, TEMPLATE)
    gate["format_zeros"] = bool(checks_zeros["format_valid"])
    gate.pop("format_placeholder_pending_write")
    strict_ok = bool(checks_zeros["checks"]["variant_strict_whole_array_no_nan_allowed"]["pass"])
    note = f"GEMS24 CGMK1 | signed grav-mag reversal + cond-K front, geophys-only | id {content_id} | not yet live-scored"
    assert len(note) <= 140, len(note)
    (DOWNLOADS / f"note-{base}-zeros.txt").write_text(note + "\n")
    save(checks_zeros, DOWNLOADS / f"checks-{base}-zeros.json")
    save(checks_nan, DOWNLOADS / f"checks-{base}-nan.json")

    if not checks_zeros["format_valid"]:
        verdict = "negative"
    proj = projection(h1, int(dots.sum()), int(fp.sum()))
    report.update(
        verdict=verdict,
        promotion_substatus=(
            "promote_to_selector_review_only; literal lattice rule fails by pigeonhole; "
            "this session authorizes no slot"
            if verdict == "promote"
            else "negative result; research download only"
        ),
        gates=gate,
        strict_whole_array_0_1_zeros_variant=strict_ok,
        model_projection=proj,
        elapsed_seconds=time.monotonic() - t0,
        code_sha256={
            "src/gems/cgmk1.py": sha256_file(ROOT / "src/gems/cgmk1.py"),
            "scripts/run_cgmk1_lane.py": sha256_file(ROOT / "scripts/run_cgmk1_lane.py"),
            "src/gems/holdout.py": sha256_file(ROOT / "src/gems/holdout.py"),
            "src/gems/metric.py": sha256_file(ROOT / "src/gems/metric.py"),
            "src/gems/emission.py": sha256_file(ROOT / "src/gems/emission.py"),
            "src/gems/novelty.py": sha256_file(ROOT / "src/gems/novelty.py"),
            "src/gems/submission.py": sha256_file(ROOT / "src/gems/submission.py"),
        },
        full_fit=s4,
    )
    save(report, EXPERIMENT_JSON)

    run_card = {
        "lane": LANE,
        "session_branch": "arena/5ef84d43-gemsdoe24",
        "preregistration": report["preregistration"],
        "preregistration_commits": report["preregistration_commits"],
        "hypothesis": (
            "Oblique buried splays rotate magnetic- vs gravity-basement gradient fields "
            "relative to each other and channel K-metasomatic fluids under cover; a "
            "signed cross-gradient reversal + lithology-conditioned K-residual front, "
            "supervised on geophysics only, can find catalogue-missing faults where "
            "DEM/LiDAR mapping is blind."
        ),
        "mechanism": (
            "sin/cos of the inter-field gradient angle (rtp vs iso_grav_anom, sigma "
            "1 and 2.5 px), |grad sin| reversal, log gradient-energy product; "
            "fold-fit OLS K ~ Th + U + Th*U residual and gated gradient front; HGB "
            "(baseline-D3 hyperparameters) on 37 geophysics+radiometric channels; "
            "no DEM trunk, no LiDAR, no tc, no catalogue-distance features; "
            "37,654 priority-Poisson dots (min_dist 3 px, >2 px catalogue clearance)."
        ),
        "named_non_fault_mimic": (
            "Intrusive contact geometry / remanent magnetization / GeoDAWN survey "
            "seams (cross-gradient reversal); arkosic sediment sorting and moisture "
            "(conditional-K residual)."
        ),
        "holdout": h1,
        "control_exp2_holdout": sc["exp2_holdout_control"],
        "paired_exp1_minus_exp2": sc["paired_exp1_minus_exp2"],
        "selection_floor_before_run": report["selection_floor_before_run"],
        "canary": {
            "passed": report["canary"]["passed"],
            "worst_feature": report["canary"]["worst_feature"],
            "worst_two_polarity_extremity": report["canary"]["worst_extremity"],
            "oof_surface_passed": sc["oof_surface_canary"]["passed"],
        },
        "novelty": {
            "surface_before_placement_max_abs_rank_correlation": nov_surface[
                "max_abs_rank_correlation"
            ],
            "final_max_abs_rank_correlation": nov_dots["max_abs_rank_correlation"],
            "final_max_competing_dot_overlap_within_3px": nov_dots.get("max_competing_dot_overlap"),
            "final_competing_method_passed": nov_dots.get("competing_method_passed"),
            "final_literal_passed_incl_space_filling_controls": nov_dots["passed"],
            "calibration_control_summary": nov_dots.get("calibration_control_summary"),
            "registry_entries_compared": len(entries),
            "registry_scope_limit": report["registry_scope"]["scope_limit"],
        },
        "validator_output": {
            "zeros_variant": checks_zeros,
            "nan_twin": checks_nan,
            "strict_whole_array_0_1_zeros_variant": strict_ok,
        },
        "submission": {
            "name": zeros_path.name,
            "zeros_tif_path": str(zeros_path.relative_to(ROOT)),
            "zeros_tif_sha256": sha256_file(zeros_path),
            "zeros_tif_bytes": zeros_path.stat().st_size,
            "zip_path": str(zip_path.relative_to(ROOT)),
            "zip_sha256": sha256_file(zip_path),
            "nan_twin_path": str(nan_path.relative_to(ROOT)),
            "nan_twin_sha256": sha256_file(nan_path),
            "content_id": content_id,
            "positive_pixels": int(dots.sum()),
            "note": note,
            "note_characters": len(note),
        },
        "model_projection_not_a_score": proj,
        "organizer_confirmed_score": None,
        "submission_slots_spent": 0,
        "ok_to_download": True,
        "ok_to_submit": False,
        "submit_decision": "DO_NOT_SUBMIT from this session (separate selector step + literal lattice issue)",
        "gates": gate,
        "verdict": verdict,
    }
    save(run_card, RUN_CARD_JSON)
    save(run_card, ROOT / "docs/data/cgmk1_run_card.json")
    print(
        json.dumps(
            {
                "verdict": verdict,
                "holdout_dti": h1["dti"],
                "holdout_ci95": h1["ci95"]["interval"],
                "control_dti": sc["exp2_holdout_control"]["dti"],
                "floor_dti": floor_dti,
                "submission_name": zeros_path.name,
                "sha256": run_card["submission"]["zeros_tif_sha256"],
                "gates": gate,
                "elapsed_seconds": report["elapsed_seconds"],
            },
            indent=2,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
