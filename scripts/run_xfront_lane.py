#!/usr/bin/env python3
"""Execute or verify the preregistered H24-XFRONT lane (2026-10-26).

Spec locked before execution in
``knowledge/25_preregistered_XFRONT_2026-10-26.md`` (commit ``3ebb375``),
amendment #1 ``knowledge/26_XFRONT_prereg_amendment_2026-10-26.md``
(``MIN_TOTAL_WEIGHT = 2.0``) and amendment #2
``knowledge/27_XFRONT_prereg_amendment2_2026-10-26.md`` (two arms, arm+budget
selected by the sparse-simulated DTI).

Label-free detector: cross-modal oriented step corroboration over six
independent layers (RTP magnetics, isostatic gravity, AEM depth-to-basement,
AEM conductivity, DEM, GNSS shear-strain rate), with an excess-orientation-
coherence factor measured against a 19-draw rotation null (arm A) and without
it (arm B, the pre-specified mechanism ablation).

Evaluation: ``SegmentHoldout`` (``gems-segment-pooled-v1``, 1.5 km collar,
60,988 withheld positives, 1,999 10 km block-bootstrap draws) plus a
density-matched sparse-truth simulation (a fixed-seed 20 % subsample of the
withheld components is "newly discovered"; the remaining 80 % are unmapped, so a
prediction beside them is a false positive). Novelty against all 46 pinned
nine-site rasters + every local GEMSDOE24 TIFF + 84 peer blobs; exact-file
Lopez-Paz & Oquab C2ST nuisance audit; shared writer/validator/selector.

Never contacts DrivenData. Never spends a weekly submission slot.
"""

from __future__ import annotations

import argparse
import gc
import hashlib
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
sys.path.insert(0, str(ROOT / "scripts"))

import numpy as np  # noqa: E402
import rasterio  # noqa: E402
import run_dprf1_lane as dprf  # noqa: E402  (reuse frozen peer/distance/C2ST helpers)
from scipy.ndimage import distance_transform_edt  # noqa: E402

from gems import (  # noqa: E402
    emission,
    footprint,
    holdout,
    novelty,
    selector,
    submission,
    xfront,
)
from gems.validator import sha256_file  # noqa: E402

SEED = 20261026
SPARSE_FRACTION = 0.20
SPARSE_FRACTIONS: tuple[float, ...] = (0.20, 0.10, 0.05)  # 0.20 = preregistered selection statistic
MIN_DIST_PX = 2.8
CATALOGUE_CLEARANCE_PX = 2.0
BUDGET_GRID: tuple[int, ...] = (15_000, 20_000, 25_000, 30_000, 37_654, 45_000)
MAX_BUDGET = max(BUDGET_GRID)
ARMS = ("A", "B")
PREREG = "knowledge/25_preregistered_XFRONT_2026-10-26.md"
PREREG_COMMIT = "3ebb375"

WORK = ROOT / "data" / "work_xfront"
EXPERIMENT_JSON = ROOT / "evidence" / "xfront_experiment_20261026.json"
RUN_CARD_JSON = ROOT / "evidence" / "xfront_run_card_20261026.json"
SELECTOR_JSON = ROOT / "evidence" / "xfront_selector_20261026.json"
DOCS_RUN_CARD_JSON = ROOT / "docs" / "data" / "xfront_run_card.json"
DOCS_SELECTOR_JSON = ROOT / "docs" / "data" / "xfront_selector.json"
DOCS_DOWNLOAD_JSON = ROOT / "docs" / "data" / "xfront_download.json"
TEMPLATE_SHA256 = "2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc"


def save_json(obj: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n")


def load_surface(fp: np.ndarray) -> dict[str, Any]:
    """Build (or reload) the frozen two-arm H24-XFRONT surfaces."""
    WORK.mkdir(parents=True, exist_ok=True)
    cache = WORK / "arms.npz"
    meta = WORK / "arms.json"
    prep_meta = json.loads((ROOT / "data/prepared/features.json").read_text())
    prep_path = ROOT / "data" / "prepared" / "features.npy"
    if sha256_file(prep_path) != prep_meta["sha256"]:
        raise SystemExit("Prepared 30-channel feature-stack SHA-256 mismatch")
    if cache.exists() and meta.exists():
        m = json.loads(meta.read_text())
        if m.get("feature_sha256") == prep_meta["sha256"]:
            z = np.load(cache)
            return {
                "A": z["A"],
                "B": z["B"],
                "corroboration": z["corroboration"],
                "excess": z["excess"],
                "coherence": z["coherence"],
                "null_coherence": z["null_coherence"],
                "magnitudes": {k: z[f"mag_{k}"] for k in xfront.MODALITIES},
                "diagnostics": m,
            }
    idx = np.flatnonzero(fp.ravel())
    mm = np.load(prep_path, mmap_mode="r")
    names: list[str] = list(prep_meta["names"])
    layers: dict[str, np.ndarray] = {}
    for name in xfront.MODALITIES:
        if name not in names:
            raise SystemExit(f"Missing preregistered modality in cache: {name}")
        a = np.array(mm[:, names.index(name)], dtype=np.float32)
        grid = np.full(fp.shape, np.nan, dtype=np.float32)
        grid.ravel()[idx] = a
        layers[name] = grid
    del mm
    gc.collect()
    res = xfront.build_xfront(layers, fp)
    del layers
    gc.collect()
    score_a = res["score"]  # C * E_R  (primary arm)
    elig = res["total_weight"] >= res["min_total_weight"]
    score_b = np.where(elig, res["corroboration"], 0.0).astype(np.float32)  # C alone
    np.savez_compressed(
        cache,
        A=score_a,
        B=score_b,
        corroboration=res["corroboration"],
        excess=res["excess_coherence"],
        coherence=res["coherence"],
        null_coherence=res["null_coherence"],
        **{f"mag_{k}": v for k, v in res["magnitudes"].items()},
    )
    save_json(
        {
            "feature_sha256": prep_meta["sha256"],
            "n_eligible": res["n_eligible"],
            "modalities": list(xfront.MODALITIES),
            "sigmas": list(xfront.SIGMAS),
            "weight_floor": xfront.WEIGHT_FLOOR,
            "min_total_weight": res["min_total_weight"],
            "n_perm": res["n_perm"],
            "seed": res["seed"],
        },
        meta,
    )
    return {
        "A": score_a,
        "B": score_b,
        "corroboration": res["corroboration"],
        "excess": res["excess_coherence"],
        "coherence": res["coherence"],
        "null_coherence": res["null_coherence"],
        "magnitudes": res["magnitudes"],
        "diagnostics": json.loads(meta.read_text()),
    }


def local_entries(fp: np.ndarray, existing: set[str]) -> list[dict[str, Any]]:
    """Every competition-grid GeoTIFF this repository has ever published."""
    seen = set(existing)
    out: list[dict[str, Any]] = []
    paths = sorted((ROOT / "docs" / "downloads").glob("*.tif")) + sorted(
        (ROOT / "inputs").rglob("*.tif")
    )
    for p in paths:
        try:
            with rasterio.open(p) as ds:
                if ds.shape != fp.shape or ds.count != 1:
                    continue
                a = ds.read(1)
        except rasterio.errors.RasterioIOError:
            continue
        inside = a[fp]
        if not np.isfinite(inside).all() or np.any((inside < 0) | (inside > 1)):
            continue
        key = hashlib.sha256(np.asarray(inside, dtype="<f4").tobytes()).hexdigest()
        if key in seen:
            continue
        seen.add(key)
        out.append(
            {
                "id": "local-" + p.stem[:52],
                "repo": "buffedlizard55-lab/GEMSDOE24",
                "file": str(p.relative_to(ROOT)),
                "cache_path": str(p.relative_to(ROOT)),
                "sha256": sha256_file(p),
                "footprint_sha256": key,
                "positive_pixels": int((inside > 0).sum()),
            }
        )
    return out


def ordered_dots(score: np.ndarray, eligible: np.ndarray, budget: int) -> np.ndarray:
    """Greedy min-distance dots at ``budget``, returned in placement order."""
    mask = emission.priority_poisson(score, eligible, budget, min_dist=MIN_DIST_PX)
    ids = np.flatnonzero(mask.ravel())
    order = np.lexsort((ids, -score.ravel()[ids]))
    return ids[order]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--verify-recorded", action="store_true")
    args = ap.parse_args()
    if args.verify_recorded:
        if not RUN_CARD_JSON.exists():
            raise SystemExit("No recorded H24-XFRONT run card to verify")
        print(json.dumps(json.loads(RUN_CARD_JSON.read_text()), indent=2, allow_nan=False))
        return
    if EXPERIMENT_JSON.exists():
        raise SystemExit(
            "H24-XFRONT experiment already recorded and frozen. No implicit rerun; use --verify-recorded."
        )

    t0 = time.monotonic()
    fp = footprint.load_footprint()
    template = ROOT / "data" / "bridge" / "sample_submission.tif"
    with rasterio.open(ROOT / "data" / "bridge" / "labels.tif") as l_ds:
        catalogue = (l_ds.read(1) > 0) & fp

    print("[1/7] Building/loading the two H24-XFRONT arms...", flush=True)
    surf = load_surface(fp)
    print(f"      eligible pixels={surf['diagnostics']['n_eligible']:,}", flush=True)

    ctx = holdout.SegmentHoldout(fp, catalogue, buffer_px=15)

    print("[2/7] Two-polarity leakage canary on every preregistered feature...", flush=True)
    canary_features: dict[str, np.ndarray] = {
        "xfront_A_C_times_excess": surf["A"],
        "xfront_B_corroboration": surf["B"],
        "xfront_corroboration_raw": surf["corroboration"],
        "xfront_excess_coherence": surf["excess"],
        "xfront_coherence": surf["coherence"],
        "xfront_null_coherence": surf["null_coherence"],
    }
    for name, mag in surf["magnitudes"].items():
        canary_features[f"edge_mag_{name}"] = np.where(np.isfinite(mag), mag, 0.0).astype(
            np.float32
        )
    canary = ctx.canary(canary_features)
    worst = max(max(v["pooled_auc"], 1 - v["pooled_auc"]) for v in canary["features"].values())
    print(f"      canary passed={canary['passed']} worst extremity={worst:.4f}", flush=True)
    if not canary["passed"]:
        raise SystemExit("HALT: leakage canary exceeded the 0.90 threshold")

    print("[3/7] Four-fold holdout + density-matched sparse simulation...", flush=True)
    total_offcat = int((fp & (~catalogue)).sum())
    results: dict[str, dict[int, dict[str, Any]]] = {a: {} for a in ARMS}
    fold_rows: dict[tuple[str, int], list[dict[str, float]]] = {}
    fold_blocks: dict[tuple[str, int], list[np.ndarray]] = {}
    sparse_rows: dict[tuple[str, int, float], list[dict[str, float]]] = {}
    sparse_blocks: dict[tuple[str, int, float], list[np.ndarray]] = {}
    sparse_info: dict[float, dict[str, int]] = {}
    for fold in ctx.folds:
        fid = int(fold["id"])
        f_offcat = int((fold["valid"] & (~fold["visible"])).sum())
        dist_vis = distance_transform_edt(~fold["visible"])
        base_elig = fold["valid"] & (dist_vis > CATALOGUE_CLEARANCE_PX)
        hidden_ids = np.asarray(fold["hidden_component_ids"], dtype=np.int64)
        sparse_truths: dict[float, np.ndarray] = {}
        sparse_meta: dict[float, dict[str, int]] = {}
        for frac in SPARSE_FRACTIONS:
            rng = np.random.default_rng(SEED + fid + int(frac * 1000))
            n_keep = max(1, int(round(frac * len(hidden_ids))))
            keep = rng.choice(hidden_ids, size=n_keep, replace=False)
            sparse_truths[frac] = np.isin(ctx.components, keep) & fold["valid"]
            sparse_meta[frac] = {
                "components_kept": n_keep,
                "components_unmapped": int(len(hidden_ids) - n_keep),
                "truth_pixels": int(sparse_truths[frac].sum()),
            }
        for arm in ARMS:
            score = surf[arm]
            elig = base_elig & (score > 0)
            k_max = int(round(MAX_BUDGET * f_offcat / total_offcat))
            order = ordered_dots(score, elig, k_max)
            for budget in BUDGET_GRID:
                k = int(round(budget * f_offcat / total_offcat))
                pred = np.zeros(fp.shape, dtype=np.float32)
                if k:
                    pred.ravel()[order[: min(k, len(order))]] = 1.0
                ref, blocks = ctx.score_fold(pred, fold)
                fold_rows.setdefault((arm, budget), []).append(
                    {
                        "fold": fold["name"],
                        **{
                            kk: ref[kk]
                            for kk in ("TP_w", "FP_w", "FN_w", "n_truth", "n_emitted", "dti")
                        },
                    }
                )
                fold_blocks.setdefault((arm, budget), []).append(blocks)
                for frac in SPARSE_FRACTIONS:
                    sblocks, sref = holdout.spatial_components(
                        pred, sparse_truths[frac], fold["valid"], fold["visible"], tile_px=100
                    )
                    sparse_rows.setdefault((arm, budget, frac), []).append(
                        {
                            "fold": fold["name"],
                            **{
                                kk: sref[kk]
                                for kk in ("TP_w", "FP_w", "FN_w", "n_truth", "n_emitted", "dti")
                            },
                        }
                    )
                    sparse_blocks.setdefault((arm, budget, frac), []).append(sblocks)
                    sparse_info.setdefault(frac, {"components": 0, "pixels": 0})
                    sparse_info[frac]["components"] += sparse_meta[frac]["components_kept"]
                    sparse_info[frac]["pixels"] += sparse_meta[frac]["truth_pixels"]
                del pred
        print(f"      fold {fold['name']:18s} done ({time.monotonic() - t0:.0f}s)", flush=True)

    yy, xx = np.nonzero(fp)
    nx = (fp.shape[1] + 99) // 100
    active = np.unique((yy // 100) * nx + xx // 100)
    for arm in ARMS:
        for budget in BUDGET_GRID:
            dense = holdout.pooled_components(fold_rows[(arm, budget)])
            sparse = holdout.pooled_components(sparse_rows[(arm, budget, SPARSE_FRACTION)])
            dblocks = np.sum(fold_blocks[(arm, budget)], axis=0)
            sblocks = np.sum(sparse_blocks[(arm, budget, SPARSE_FRACTION)], axis=0)
            results[arm][budget] = {
                "budget": budget,
                "arm": arm,
                "dense_holdout_dti": float(dense["dti"]),
                "dense_ci95": holdout.spatial_bootstrap_ci(dblocks[active], draws=1999)["interval"],
                "dense_folds": [round(r["dti"], 5) for r in fold_rows[(arm, budget)]],
                "dense_mean_fold_dti": round(
                    float(np.mean([r["dti"] for r in fold_rows[(arm, budget)]])), 5
                ),
                "dense_coverage": float(dense["TP_w"] / max(dense["n_truth"], 1)),
                "dense_tp_w": float(dense["TP_w"]),
                "dense_fp_w": float(dense["FP_w"]),
                "dense_fn_w": float(dense["FN_w"]),
                "n_withheld_positive_pixels": int(dense["n_truth"]),
                "sparse_simulated_dti": float(sparse["dti"]),
                "sparse_ci95": holdout.spatial_bootstrap_ci(sblocks[active], draws=1999)[
                    "interval"
                ],
                "sparse_folds": [
                    round(r["dti"], 5) for r in sparse_rows[(arm, budget, SPARSE_FRACTION)]
                ],
                "sparse_mean_fold_dti": round(
                    float(np.mean([r["dti"] for r in sparse_rows[(arm, budget, SPARSE_FRACTION)]])),
                    5,
                ),
                "sparse_coverage": float(sparse["TP_w"] / max(sparse["n_truth"], 1)),
                "sparse_n_truth": int(sparse["n_truth"]),
                "n_emitted": int(dense["n_emitted"]),
            }
            r = results[arm][budget]
            for frac in SPARSE_FRACTIONS:
                s20 = holdout.pooled_components(sparse_rows[(arm, budget, frac)])
                sb = np.sum(sparse_blocks[(arm, budget, frac)], axis=0)
                r.setdefault("sparse_sensitivity", {})[str(frac)] = {
                    "simulated_dti": float(s20["dti"]),
                    "mean_fold_dti": round(
                        float(np.mean([q["dti"] for q in sparse_rows[(arm, budget, frac)]])), 5
                    ),
                    "ci95": holdout.spatial_bootstrap_ci(sb[active], draws=1999)["interval"],
                    "coverage": float(s20["TP_w"] / max(s20["n_truth"], 1)),
                    "n_truth": int(s20["n_truth"]),
                }
            print(
                f"      arm {arm} B={budget:>6,} | dense {r['dense_holdout_dti']:.5f} "
                f"| sparse20 {r['sparse_simulated_dti']:.5f} "
                f"| sparse10 {r['sparse_sensitivity']['0.1']['simulated_dti']:.5f} "
                f"| sparse05 {r['sparse_sensitivity']['0.05']['simulated_dti']:.5f}",
                flush=True,
            )

    best = max(
        ((arm, budget) for arm in ARMS for budget in BUDGET_GRID),
        key=lambda k: (
            results[k[0]][k[1]]["sparse_mean_fold_dti"],
            -k[1],
            k[0] == "A",
        ),
    )
    sel_arm, sel_budget = best
    print(f"      selected arm={sel_arm} budget={sel_budget:,}", flush=True)

    # ---- paired comparison of the two pre-specified arms at the selected budget ----
    cand = [np.zeros(fp.shape, dtype=np.float32) for _ in range(4)]
    base = [np.zeros(fp.shape, dtype=np.float32) for _ in range(4)]
    for i, fold in enumerate(ctx.folds):
        f_offcat = int((fold["valid"] & (~fold["visible"])).sum())
        k = int(round(sel_budget * f_offcat / total_offcat))
        dist_vis = distance_transform_edt(~fold["visible"])
        base_elig = fold["valid"] & (dist_vis > CATALOGUE_CLEARANCE_PX)
        for arm, store in ((sel_arm, cand[i]), ("B" if sel_arm == "A" else "A", base[i])):
            score = surf[arm]
            order = ordered_dots(score, base_elig & (score > 0), k)
            store.ravel()[order[: min(k, len(order))]] = 1.0
    paired = ctx.compare_paired(cand, base, ci_draws=1999, seed=SEED)

    del cand, base
    gc.collect()

    print("[4/7] Full-footprint allocation and novelty vs registry + peers...", flush=True)
    score_sel = surf[sel_arm]
    dist_cat = distance_transform_edt(~catalogue)
    full_elig = fp & (dist_cat > CATALOGUE_CLEARANCE_PX) & (score_sel > 0)
    final_ids = ordered_dots(score_sel, full_elig, sel_budget)
    final = np.zeros(fp.shape, dtype=np.float32)
    final.ravel()[final_ids] = 1.0

    priority_reg = json.loads((ROOT / "registry" / "priority_rasters.json").read_text())
    existing = {e["footprint_sha256"] for e in priority_reg["unique_rasters"]}
    extras = local_entries(fp, existing)
    entries = priority_reg["unique_rasters"] + extras
    pre_methods = novelty.compare_prospective_registry(
        score_sel, fp, entries, ROOT, sample_size=200_000
    )
    pre_peers = dprf.check_peer_blobs(score_sel, None, fp)
    fin_methods = novelty.compare_prospective_registry(
        score_sel, fp, entries, ROOT, dots=final > 0.5, sample_size=200_000
    )
    fin_peers = dprf.check_peer_blobs(score_sel, final, fp)
    profile = dprf.compute_distance_profile(final > 0.5, catalogue, fp)
    print(
        f"      novelty: methods max|rho|={fin_methods['method_lane_max_abs_rank_correlation']:.4f} "
        f"max3px={fin_methods['method_lane_max_dot_overlap']:.4f} passed={fin_methods['method_lane_passed']}; "
        f"peers max3px={fin_peers['max_dot_overlap_within_3px']:.4f} passed={fin_peers['passed']}",
        flush=True,
    )

    print("[5/7] Writing GeoTIFF pair + ZIP...", flush=True)
    content_id = submission.scored_content_id(final, fp, catalogue)
    slug = f"xfront-{'ce' if sel_arm == 'A' else 'c'}-corrob-{sel_budget}"
    date = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    name = f"gems24-{slug}-{date}-{content_id}-zeros.tif"
    zeros_path = ROOT / "docs" / "downloads" / name
    submission.write_submission(final, template, zeros_path, outside="zero")
    nan_name = name.replace("-zeros.tif", "-nan.tif")
    nan_path = ROOT / "docs" / "downloads" / nan_name
    submission.write_submission(final, template, nan_path, outside="nan")
    zip_path = submission.zip_single(zeros_path)
    validator = submission.check_variants(zeros_path, template)
    validator_nan = submission.check_variants(nan_path, template)
    print(f"      wrote {name} ({zeros_path.stat().st_size:,} bytes)", flush=True)

    print("[6/7] Exact-file C2ST nuisance audit...", flush=True)
    audit = dprf.run_exact_file_c2st(zeros_path, catalogue, fp)

    note = (
        f"GEMS24 XFRONT arm{sel_arm} | cross-modal oriented-step corroboration | "
        f"{sel_budget} dots | id {content_id}"
    )
    if len(note) > 140:
        note = (
            f"GEMS24 XFRONT {sel_arm} | cross-modal step corrob | {sel_budget} dots | {content_id}"
        )

    holdout_block = {
        "label": "HOLDOUT-DTI",
        "evaluator_version": holdout.MTR_EVALUATOR_VERSION,
        "dti": results[sel_arm][sel_budget]["dense_holdout_dti"],
        "ci95": results[sel_arm][sel_budget]["dense_ci95"],
        "n_withheld_positive_pixels": results[sel_arm][sel_budget]["n_withheld_positive_pixels"],
        "protocol": {
            "alpha": 0.2,
            "beta": 0.8,
            "triangular_kernel_radius_m": 300,
            "buffer_m": 1500,
            "whole_components_hidden_everywhere": True,
            "visible_fault_mask": "pixel-exact",
            "catalogue_features": "detector is label-free; no catalogue feature is used",
        },
    }
    run_card: dict[str, Any] = {
        "schema_version": "gems-run-card/2",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "lane_id": "H24-XFRONT",
        "preregistration": PREREG,
        "preregistration_commit": PREREG_COMMIT,
        "amendments": [
            "knowledge/26_XFRONT_prereg_amendment_2026-10-26.md",
            "knowledge/27_XFRONT_prereg_amendment2_2026-10-26.md",
        ],
        "experiments_run": 1,
        "experiment_budget_limit": 3,
        "elapsed_seconds": round(time.monotonic() - t0, 1),
        "hypothesis": (
            "A fault missing from the catalogue is usually buried, so its scarp is gone but the "
            "step it imposes on independent potential-field/AEM layers survives and forces those "
            "layers' across-strike gradient vectors to share one strike."
        ),
        "mechanism": (
            "per-pixel weighted mean-resultant length of doubled across-strike orientations across "
            "six independent layers (RTP, isostatic gravity, AEM depth-to-basement, AEM conductivity, "
            "DEM, GNSS shear rate), scored as corroboration C (=sum of ranked top-30% edge weights) "
            "times excess orientation coherence E_R over a 19-draw translation null (arm A); arm B is "
            "the pre-specified ablation C alone on the identical eligible set."
        ),
        "named_non_fault_mimic": (
            "lithologic/stratigraphic contacts and Lake Lahontan strandlines: buried alluvial-fan "
            "margins and pluvial shorelines also produce co-located, co-oriented steps in AEM depth, "
            "conductivity, gravity and DEM with no fault present"
        ),
        "holdout": holdout_block,
        "holdout_dense_all_arms_and_budgets": results,
        "density_matched_sparse_simulation": {
            "label": "SIMULATED-SPARSE-DTI",
            "design": (
                "per fold, a seeded 20% subsample of withheld COMPONENTS is the newly-discovered truth; "
                "the other 80% stay excluded from visible and from truth so a prediction beside them is "
                "a false positive, as beside an unmapped real fault"
            ),
            "seed": SEED,
            "sparse_fraction": SPARSE_FRACTION,
            "sensitivity_fractions": list(SPARSE_FRACTIONS),
            "sensitivity_note": (
                "reported as a diagnostic only; the locked selection statistic stays the "
                "preregistered 0.20 fraction. Tests whether the owner-reported live pattern "
                "(fewer dots -> higher score) appears at lower simulated truth densities."
            ),
            "simulated_truth_pixels": {str(k): v["pixels"] for k, v in sorted(sparse_info.items())},
            "simulated_truth_components": {
                str(k): v["components"] for k, v in sorted(sparse_info.items())
            },
            "selected": {
                "arm": sel_arm,
                "budget": sel_budget,
                "sparse_simulated_dti": results[sel_arm][sel_budget]["sparse_simulated_dti"],
                "sparse_ci95": results[sel_arm][sel_budget]["sparse_ci95"],
                "sparse_mean_fold_dti": results[sel_arm][sel_budget]["sparse_mean_fold_dti"],
                "sparse_n_truth": results[sel_arm][sel_budget]["sparse_n_truth"],
            },
            "selection_statistic": "mean over the four folds of the sparse-simulated DTI",
            "limitation": "a simulation of the live regime, not the live regime; no organizer label is available",
        },
        "selected_arm": sel_arm,
        "selected_budget": sel_budget,
        "emission": {
            "operator": "gems.emission.priority_poisson",
            "min_spacing_px": MIN_DIST_PX,
            "catalogue_clearance_px": CATALOGUE_CLEARANCE_PX,
            "budget_grid": list(BUDGET_GRID),
        },
        "leakage_canary": {
            **{k: v for k, v in canary.items() if k != "features"},
            "n_features": len(canary["features"]),
            "worst_polarity_extremity": float(worst),
            "per_feature": {
                k: {
                    "pooled_auc": v["pooled_auc"],
                    "leakage_suspected": v["leakage_suspected"],
                }
                for k, v in canary["features"].items()
            },
        },
        "paired_vs_baseline": {
            "candidate_dti": paired["candidate_dti"],
            "baseline_dti": paired["baseline_dti"],
            "paired_delta_dti": paired["paired_delta_dti"],
            "ci95": paired["paired_delta_ci95"],
            "ci95_strictly_positive": paired["ci95_strictly_positive"],
            "fold_wins": paired["fold_wins"],
            "n_folds": paired["n_folds"],
            "evaluator_version": holdout.MTR_EVALUATOR_VERSION,
            "comparator": f"arm {'B' if sel_arm == 'A' else 'A'} (pre-specified mechanism ablation), same budget",
        },
        "paired_vs_current_best": {
            "baseline_dti": None,
            "evaluator_version": holdout.MTR_EVALUATOR_VERSION,
            "n_withheld_positive_pixels": None,
            "baseline_replayed": False,
            "ci95": None,
            "why": (
                "H24-DPRF1 (0.16379) was not retrained this session; a recorded point estimate is not "
                "replayed evidence, so no paired CI is asserted (amendment A8)"
            ),
        },
        "baseline_reproduced": False,
        "novelty": {
            "surface": pre_methods,
            "final_dots": fin_methods,
            "peers_surface": pre_peers,
            "peers_final": fin_peers,
            "registry_entries_checked": len(entries),
            "correlation_overlap_vs_registry": {
                "max_abs_rank_correlation_surface": pre_methods["max_abs_rank_correlation"],
                "max_abs_rank_correlation_final_dots": fin_methods[
                    "method_lane_max_abs_rank_correlation"
                ],
                "max_3px_dot_overlap_method_lanes": fin_methods["method_lane_max_dot_overlap"],
                "max_3px_dot_overlap_peer_blobs": fin_peers["max_dot_overlap_within_3px"],
            },
        },
        "off_catalogue_distance_profile": profile,
        "c2st_exact_file": audit,
        "raster_sha256": sha256_file(zeros_path),
        "nan_outside_artifact": nan_name,
        "nan_outside_sha256": sha256_file(nan_path),
        "zip_artifact": zip_path.name,
        "zip_sha256": sha256_file(zip_path),
        "validator_output": validator,
        "validator_output_nan_twin": validator_nan,
        "submission_name": name,
        "note": note,
        "note_length": len(note),
        "verdict": "negative",
        "ok_to_download": True,
        "ok_to_submit": False,
        "submission_authorized": False,
        "submission_slots_used": 0,
        "organizer_confirmed_score": None,
        "governance_hold_reasons": [],
    }

    print("[7/7] Selector v2 screen + preflight...", flush=True)
    sel = selector.verify_selector(zeros_path, template, run_card)
    save_json(sel, SELECTOR_JSON)
    save_json(sel, DOCS_SELECTOR_JSON)
    run_card["selector_receipt"] = sel
    run_card["governance_hold_reasons"] = sel["reasons"]
    run_card["verdict"] = "negative" if not sel["ok_to_submit"] else "promote"
    run_card["ok_to_submit"] = bool(sel["ok_to_submit"])
    run_card["submission_authorized"] = bool(sel["ok_to_submit"])

    from gems import preflight as preflight_mod

    preflight_mod.preflight(
        zeros_path,
        template,
        run_card_path=RUN_CARD_JSON,
        note=note,
        expected_template_sha256=TEMPLATE_SHA256,
    )
    save_json(run_card, RUN_CARD_JSON)
    save_json(run_card, DOCS_RUN_CARD_JSON)
    pf2 = preflight_mod.preflight(
        zeros_path,
        template,
        run_card_path=RUN_CARD_JSON,
        note=note,
        expected_template_sha256=TEMPLATE_SHA256,
    )
    save_json(pf2, ROOT / "docs" / "downloads" / (name[:-4] + ".preflight.json"))
    save_json(pf2, ROOT / "docs" / "downloads" / (name[:-4] + ".checks.json"))
    save_json(
        {
            "artifact": name,
            "sha256": run_card["raster_sha256"],
            "format_valid": validator["format_valid"],
            "strict_whole_array_0_1": validator["checks"][
                "variant_strict_whole_array_no_nan_allowed"
            ]["pass"],
            "download_status": pf2["decision"]["download_status"],
            "submission_status": pf2["decision"]["submission_status"],
            "blockers": pf2["decision"]["blockers"],
            "selector_decision": sel["decision"],
            "holdout_dti": holdout_block["dti"],
            "note": note,
        },
        DOCS_DOWNLOAD_JSON,
    )
    save_json(
        {
            "lane": "H24-XFRONT",
            "generated_utc": run_card["generated_utc"],
            "canary": canary,
            "all_arms_and_budgets": results,
            "selected": {"arm": sel_arm, "budget": sel_budget},
            "fold_rows_dense": {f"{a}|{b}": fold_rows[(a, b)] for a in ARMS for b in BUDGET_GRID},
            "fold_rows_sparse": {
                f"{a}|{b}|{c}": sparse_rows[(a, b, c)]
                for a in ARMS
                for b in BUDGET_GRID
                for c in SPARSE_FRACTIONS
            },
            "novelty": run_card["novelty"],
            "c2st": audit,
            "distance_profile": profile,
            "validator": validator,
        },
        EXPERIMENT_JSON,
    )
    print(
        f"DONE {name} | HOLDOUT-DTI {holdout_block['dti']:.5f} | "
        f"SIMULATED-SPARSE-DTI {results[sel_arm][sel_budget]['sparse_simulated_dti']:.5f} | "
        f"selector {sel['decision']} | download {pf2['decision']['download_status']} | "
        f"submit {pf2['decision']['submission_status']}"
    )


if __name__ == "__main__":
    main()
