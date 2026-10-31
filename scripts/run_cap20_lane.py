#!/usr/bin/env python3
"""CAP20: catalogue-adjacency-pruned band geometry at the lattice-feasible 20,000-dot budget.

Pre-registered in this file before the first run (see SETTINGS). Every score is
HOLDOUT-DTI (evaluator `gems-segment-pooled-v1`, withheld-positive count and 95% CI
recorded) or a geometry/format check. Nothing here uploads or projects a leaderboard
score.

Lane identity (single method paragraph). Reuse, don't rebuild: the feature stack,
hide-and-recover holdout and writer are the shared template ones
(`run_ns_ratio1_lane.static_features`, `gems.holdout.SegmentHoldout`,
`gems.metric`, `gems.novelty`, `gems.submission`). The three deltas from the
recorded NS-RATIO1 lane are, in the order they were fixed:
  1. Budget K = 20,000, chosen PROSPECTIVELY from
     `scripts/check_uniqueness_feasibility.py`: the retained GEMSDOE13 lattice
     witness leaves 6,649 lattice-free footprint pixels, so any K above 22,163
     necessarily overlaps the lattice by more than 70 percent. 20,000 leaves a
     1.0-point margin with a 6,200-dot lattice-free obligation.
  2. Catalogue-adjacency pruning: eligibility excludes every cell within 3 px of
     the (visible) catalogue, not only catalogue cells themselves. This is the
     repo's queued hypothesis H1, the GEMSDOE32 B2 pattern (B2 removed exactly
     its 1-3 px dots and improved 0.2600 -> 0.2778, owner-reported).
  3. Lattice-free obligation: 6,200 dots are placed on lattice-free pixels
     (clean ones ranked by the science surface first, catalogue-adjacent free
     pixels backfill deterministically; shares start proportional to fold size
     and deficits move to folds with spare free pixels) so the final dot set
     provably satisfies the 70 percent rule against the witness; the remaining
     13,800 dots follow the credit-to-penalty ratio rule on a label-free
     HistGradientBoosting surface with 3 px minimum spacing.

Experiments (session budget 3; two holdout evaluations + one emission):
  E1  CAP20-HGB   label-free channels, halo-excluded eligibility, obligation.
  E2  CAP20-PROX  no-model proximity control under identical constraints.
  E3  EMIT        E1 configuration trained on all catalogue positives; exact
                  20,000 dots; gates: format, range, registry overlap,
                  surface rank correlation, catalogue adjacency.

The hide-and-recover holdout measures recovery of withheld catalogue segments;
it cannot measure the live value of near-catalogue geometry and is not a
leaderboard estimate.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt
from scipy.spatial import cKDTree
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import run_ns_ratio1_lane as ns  # noqa: E402  (shared template feature stack)

from gems import holdout, novelty, submission  # noqa: E402
from gems.validator import sha256_file  # noqa: E402

TEMPLATE = ROOT / "data/bridge/sample_submission.tif"
LABELS = ROOT / "data/bridge/labels.tif"
WITNESS = ROOT / "inputs/calibration/13gems_20261001_r13-lattice-s5_v2_nan-outside.tif"
CACHE = ROOT / "data/research/session20261031/cache"
RESULT = ROOT / "evidence/cap20_experiment_20261031.json"
EMIT_RESULT = ROOT / "evidence/cap20_emit_20261031.json"

SETTINGS = {
    "lane": "CAP20",
    "seed": 20261031,
    "k_total": 20000,
    "obligation_dots": 6200,
    "obligation_margin_note": (
        "6200/20000 => worst-case witness overlap 69.0% < 70% with 449 spare lattice-free pixels"
    ),
    "halo_px": 3.0,
    "min_spacing_px": 3.0,
    "buffer_px": 30,
    "neg_per_pos": 6,
    "hgb": {"max_iter": 200, "learning_rate": 0.08, "max_leaf_nodes": 31},
    "budget_basis": (
        "scripts/check_uniqueness_feasibility.py 2026-10-31: 6,649 lattice-free px; "
        "K>22,163 necessarily exceeds the 70% witness rule"
    ),
}


def allocate(total: int, weights: list[int]) -> list[int]:
    """Largest-remainder split of ``total`` proportional to ``weights``; sums exactly."""
    w = [int(x) for x in weights]
    s = sum(w)
    if total < 0 or s <= 0 or any(x < 0 for x in w):
        raise ValueError("Nonnegative weights with positive sum and nonnegative total required")
    raw = [total * x / s for x in w]
    out = [int(x) for x in raw]
    order = sorted(range(len(w)), key=lambda i: raw[i] - out[i], reverse=True)
    for i in range(total - sum(out)):
        out[order[i % len(order)]] += 1
    return out


def quadrant_views(fp):
    """Fold-name/valid views used for the global obligation allocation."""
    fold_grid, names = holdout.make_quadrant_folds(fp)
    return [{"name": n, "valid": fp & (fold_grid == i)} for i, n in enumerate(names)]


def free_pixels(fp):
    """Footprint pixels farther than 3 px from every retained lattice-witness dot."""
    with rasterio.open(WITNESS) as r:
        lat = (r.read(1) > 0) & fp
    ly, lx = np.nonzero(lat)
    tree = cKDTree(np.column_stack([ly, lx]))
    fy, fx = np.nonzero(fp)
    d, _ = tree.query(np.column_stack([fy, fx]))
    free = np.zeros(fp.shape, bool)
    free.ravel()[np.flatnonzero(fp)] = d > 3.0
    return free


def obligation_plan(folds, target, clean_masks, backfill_masks, surfaces):
    """Place exactly ``target`` obligation dots on lattice-free pixels across all folds.

    ``clean_masks[i]``/``backfill_masks[i]`` are precomputed per fold from the
    catalogue that fold's detector may read (visible faults in the holdout; the
    full catalogue for emission). Clean pixels are ranked by the matching fold
    surface; backfill is deterministic. Shares start proportional to fold size
    and any fold too small to carry its share hands the deficit to folds with
    spare free pixels. Returns (claim mask, per-fold plan, shortfall); shortfall
    is nonzero only if all folds together cannot carry the target.
    """
    avail = [
        int((c & f["valid"]).sum() + (b & f["valid"]).sum())
        for c, b, f in zip(clean_masks, backfill_masks, folds)
    ]
    shares = allocate(target, [int(f["valid"].sum()) for f in folds])
    quota = [min(s, a) for s, a in zip(shares, avail)]
    deficit = target - sum(quota)
    while deficit > 0:
        spare = [a - q for a, q in zip(avail, quota)]
        order = sorted(range(len(folds)), key=lambda i: (-spare[i], i))
        i = order[0]
        if spare[i] <= 0:
            break
        add = min(deficit, spare[i])
        quota[i] += add
        deficit -= add
    claim = np.zeros(folds[0]["valid"].shape, bool)
    per_fold = []
    for i, (q_l, fold) in enumerate(zip(quota, folds)):
        clean = clean_masks[i] & fold["valid"]
        backfill = backfill_masks[i] & fold["valid"]
        need_clean = min(q_l, int(clean.sum()))
        if need_clean:
            ids = np.flatnonzero(clean.ravel())
            vals = np.nan_to_num(surfaces[i].ravel()[ids], nan=0.0)
            order = ids[np.lexsort((ids, -vals))]
            claim.ravel()[order[:need_clean]] = True
        rest = q_l - need_clean
        if rest:
            ids2 = np.flatnonzero(backfill.ravel())
            ids2 = ids2[np.lexsort((ids2,))]  # deterministic: smallest flat index first
            claim.ravel()[ids2[:rest]] = True
        per_fold.append({"fold": fold["name"], "proportional_share": shares[i], "claimed": q_l})
    return claim, per_fold, target - int(claim.sum())


def score_surface(q_grid, eligible, claim, k_total, spacing):
    """Obligation dots first, then ratio_select with spacing on the remaining budget."""
    science_eligible = eligible & ~claim
    k_science = max(0, k_total - int(claim.sum()))
    return claim | ns.ratio_select(q_grid, science_eligible, k_science, spacing)


def subset_channels(static_fp, static_names, keep):
    """Restrict the shared template stack to a preregistered channel family."""
    idx = [i for i, n in enumerate(static_names) if n.split("_", 1)[0] in keep]
    if not idx:
        raise SystemExit("Channel subset is empty")
    return static_fp[idx], [static_names[i] for i in idx]


def fold_surfaces(fp, labels, static_fp, static_names, use_model):
    """Per-fold probability surfaces, eligibility masks and leakage canaries."""
    sh = holdout.SegmentHoldout(fp, labels, buffer_px=SETTINGS["buffer_px"])
    fp_flat = np.flatnonzero(fp.ravel())
    row_of = np.full(fp.size, -1, np.int64)
    row_of[fp_flat] = np.arange(len(fp_flat))
    out = []
    canary: dict[str, list[float]] = {}
    for fold in sh.folds:
        valid, visible, truth, train = fold["valid"], fold["visible"], fold["truth"], fold["train"]
        dist_vis = distance_transform_edt(~visible)
        eligible = valid & ~visible & (dist_vis > SETTINGS["halo_px"]) & fp
        if use_model:
            names = list(static_names)
            X = static_fp.T.astype(np.float32)
            tr = np.flatnonzero((train & fp).ravel())
            tr_rows = row_of[tr]
            is_pos = visible.ravel()[tr]
            pos_rows = tr_rows[is_pos]
            neg_pool = tr_rows[~is_pos]
            rng = np.random.default_rng(SETTINGS["seed"])
            neg_rows = rng.choice(
                neg_pool,
                size=min(len(neg_pool), SETTINGS["neg_per_pos"] * max(len(pos_rows), 1)),
                replace=False,
            )
            rows = np.concatenate([pos_rows, neg_rows])
            y = np.concatenate([np.ones(len(pos_rows)), np.zeros(len(neg_rows))])
            el_rows = row_of[np.flatnonzero(eligible.ravel())]
            q_rows = ns.fit_predict(X[rows], y, X[el_rows], SETTINGS["seed"])
            q = np.zeros(fp.shape, np.float32)
            q.ravel()[np.flatnonzero(eligible.ravel())] = q_rows
            test_rows = row_of[np.flatnonzero((valid & ~visible & fp).ravel())]
            lab = truth.ravel()[np.flatnonzero((valid & ~visible & fp).ravel())].astype(int)
            for j, n in enumerate(names):
                col = X[test_rows, j]
                ok = np.isfinite(col)
                if ok.sum() > 1 and 0 < lab[ok].sum() < ok.sum():
                    auc = roc_auc_score(lab[ok], col[ok])
                    canary.setdefault(n, []).append(float(max(auc, 1 - auc)))
        else:
            q = np.where(eligible, np.exp(-dist_vis / 20.0), 0.0).astype(np.float32)
        out.append({"name": fold["name"], "q": q, "eligible": eligible, "k_share": valid.sum()})
    return sh, out, canary


def run_holdout(experiment, fp, labels, static_fp, static_names, use_model):
    """One hide-and-recover evaluation: obligation + ratio-rule dots per fold."""
    sh, folds, canary = fold_surfaces(fp, labels, static_fp, static_names, use_model)
    surfaces = [f["q"] for f in folds]
    fold_views = [{"name": f["name"], "valid": f["eligible"].shape and sh.folds[i]["valid"]}
                  for i, f in enumerate(folds)]
    clean_masks, backfill_masks = [], []
    free = free_pixels(fp)
    for fold in sh.folds:
        dist_vis = distance_transform_edt(~fold["visible"])
        clean = free & fold["valid"] & ~fold["visible"] & (dist_vis > SETTINGS["halo_px"])
        clean_masks.append(clean)
        backfill_masks.append(free & fold["valid"] & ~clean)
    claim, plan, shortfall = obligation_plan(
        fold_views, SETTINGS["obligation_dots"], clean_masks, backfill_masks, surfaces
    )
    fold_preds = []
    k_exact = allocate(
        SETTINGS["k_total"], [int(f["k_share"]) for f in folds]
    )
    for i, f in enumerate(folds):
        valid = fold_views[i]["valid"]
        pred = score_surface(f["q"], f["eligible"], claim & valid, k_exact[i], SETTINGS["min_spacing_px"])
        fold_preds.append(pred.astype(np.uint8))
    summary = sh.summarize(fold_preds)
    worst = max((max(v) for v in canary.values()), default=None)
    worst_name = max(canary, key=lambda n: max(canary[n])) if canary else None
    out = {
        "experiment": experiment,
        "label": "HOLDOUT-DTI",
        "evaluator_version": summary["evaluator_version"],
        "dti": round(summary["dti"], 6),
        "tp_w": round(summary["TP_w"], 3),
        "fp_w": round(summary["FP_w"], 3),
        "fn_w": round(summary["FN_w"], 3),
        "n_withheld_positive_pixels": summary["n_withheld_positive_pixels"],
        "ci95": [round(x, 6) for x in summary["ci95"]["interval"]],
        "ci_method": summary["ci95"]["method"],
        "folds": [
            {"fold": r["fold"], "dti": round(r["dti"], 6), "dots": int(p.sum())}
            for r, p in zip(summary["folds"], fold_preds)
        ],
        "obligation_plan": plan,
        "obligation_shortfall": int(shortfall),
        "dots_emitted_total": int(sum(p.sum() for p in fold_preds)),
    }
    if canary:
        out["leakage_canary"] = {
            "rule": "single-feature AUC on withheld quadrant; > 0.90 = leakage until proven otherwise",
            "worst_feature": worst_name,
            "worst_auc": round(float(worst), 4),
            "pass": bool(worst is not None and worst <= 0.90),
            "per_feature_max_auc": {k: round(max(v), 4) for k, v in canary.items()},
        }
    for p in fold_preds:
        print(f"[{experiment}] emitted {int(p.sum())} fold dots", flush=True)
    return out


def emit(path: Path, fp, labels, static_fp, static_names, profile):
    """E3: E1 configuration trained on ALL catalogue positives; exact 20,000 dots."""
    X = static_fp.T.astype(np.float32)
    fp_flat = np.flatnonzero(fp.ravel())
    row_of = np.full(fp.size, -1, np.int64)
    row_of[fp_flat] = np.arange(len(fp_flat))
    dist_lab = distance_transform_edt(~labels)
    free = free_pixels(fp)
    eligible = fp & ~labels & (dist_lab > SETTINGS["halo_px"])
    rng = np.random.default_rng(SETTINGS["seed"])
    pos_rows = row_of[np.flatnonzero((labels & fp).ravel())]
    neg_pool = row_of[np.flatnonzero((fp & ~labels).ravel())]
    neg_rows = rng.choice(neg_pool, size=SETTINGS["neg_per_pos"] * len(pos_rows), replace=False)
    rows = np.concatenate([pos_rows, neg_rows])
    y = np.concatenate([np.ones(len(pos_rows)), np.zeros(len(neg_rows))])
    el_rows = row_of[np.flatnonzero(eligible.ravel())]
    q_rows = ns.fit_predict(X[rows], y, X[el_rows], SETTINGS["seed"])
    q = np.zeros(fp.shape, np.float32)
    q.ravel()[np.flatnonzero(eligible.ravel())] = q_rows
    clean = free & ~labels & (dist_lab > SETTINGS["halo_px"])
    backfill = free & ~clean
    claim, plan, shortfall = obligation_plan(
        quadrant_views(fp),
        SETTINGS["obligation_dots"],
        [clean] * 4,
        [backfill] * 4,
        [q] * 4,
    )
    if shortfall:
        raise SystemExit(
            f"Obligation shortfall {shortfall}: witness overlap margin cannot be guaranteed"
        )
    dots = score_surface(q, eligible, claim, SETTINGS["k_total"], SETTINGS["min_spacing_px"])
    if int(dots.sum()) != SETTINGS["k_total"]:
        raise SystemExit(f"Emitted {int(dots.sum())} dots, expected {SETTINGS['k_total']}")
    out = dots.astype(np.float32)
    out[~fp] = 0.0
    path = path if path.is_absolute() else ROOT / path
    path.parent.mkdir(parents=True, exist_ok=True)
    prof = dict(profile)
    prof.update(dtype="float32", count=1, nodata=None, compress="deflate")
    with rasterio.open(path, "w", **prof) as dst:
        dst.write(out, 1)
    surface = q.copy()
    surface[~eligible] = 0.0
    return {
        "path": str(path),
        "path_relative_to_repo": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else None,
        "dots": int(dots.sum()),
        "obligation_dots": int((dots & free).sum()),
        "obligation_plan": plan,
        "features": list(static_names),
        "n_train_pos": int(len(pos_rows)),
        "surface": surface,
        "dots_mask": dots,
    }


def audit_dots(dots, fp, comparators):
    """Directional 3-px overlap and footprint rank correlation vs every comparator."""
    rows = []
    cy, cx = np.nonzero(dots)
    del cy, cx
    for name, path in comparators:
        with rasterio.open(path) as s:
            ref_vals = s.read(1)
        nonfinite = int((~np.isfinite(ref_vals[fp])).sum())
        ref = (ref_vals > 0) & fp
        ov = novelty.dot_overlap(dots, ref, radius_px=3.0)
        rv = ref_vals[fp].astype(np.float64)
        if nonfinite:
            rv = np.where(np.isfinite(rv), rv, 0.0)
        ours = dots[fp].astype(np.float64)
        rho = novelty.correlation(ours, rv)
        rows.append(
            {
                "comparator": name,
                "path": str(path),
                "forward_3px_overlap": round(ov["candidate_within_3px_of_reference"], 6)
                if ov["candidate_within_3px_of_reference"] is not None
                else None,
                "spearman_rho": round(rho, 6) if rho is not None else None,
                "nonfinite_footprint_values_treated_as_zero": nonfinite,
            }
        )
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--emit", type=Path, default=None)
    ap.add_argument("--skip-holdout", action="store_true")
    ap.add_argument(
        "--channels",
        choices=("all", "radmag"),
        default="all",
        help=(
            "all = full template stack (18 ch, E1); radmag = radiometric+magnetic only "
            "(8 ch, zero LiDAR/DEM; README-queued hypothesis H3 ablation)"
        ),
    )
    ap.add_argument("--experiments", default="E1,E2", help="comma list from {E1,E2}")
    args = ap.parse_args()
    t0 = time.time()
    with rasterio.open(TEMPLATE) as t:
        profile = t.profile.copy()
        fp = np.isfinite(t.read(1))
    with rasterio.open(LABELS) as lab:
        labels = (lab.read(1) == 1) & fp
    static_names, static_fp = ns.static_features(fp, profile["transform"], fp.shape)
    if args.channels == "radmag":
        static_fp, static_names = subset_channels(static_fp, static_names, ("rad", "ext"))
    free = free_pixels(fp)
    dist_lab = distance_transform_edt(~labels)
    results = {
        "settings": {**SETTINGS, "channels": args.channels, "experiments_run": args.experiments},
        "inputs": {
            "template_sha256": sha256_file(TEMPLATE),
            "labels_sha256": sha256_file(LABELS),
            "lidar_sha256": sha256_file(ns.LIDAR),
            "rad_sha256": sha256_file(ns.RAD),
            "ext_sha256": sha256_file(ns.EXT),
            "witness_sha256": sha256_file(WITNESS),
        },
        "footprint_cells": int(fp.sum()),
        "catalogue_positive_pixels": int(labels.sum()),
        "lattice_free_pixels": int(free.sum()),
        "lattice_free_clean_off_catalogue": int((free & ~labels & (dist_lab > 3.0)).sum()),
        "static_features": static_names,
        "note": (
            "HOLDOUT-DTI only; not a leaderboard estimate; label-free channels; catalogue "
            "used only through the pixel-exact visible mask"
        ),
    }
    if not args.skip_holdout:
        wanted = {x.strip() for x in args.experiments.split(",") if x.strip()}
        results["experiments"] = []
        if "E1" in wanted:
            e1 = run_holdout(
                f"E1_CAP20_HGB_{args.channels}", fp, labels, static_fp, static_names, True
            )
            results["experiments"].append(e1)
        if "E2" in wanted:
            e2 = run_holdout("E2_CAP20_PROX_control", fp, labels, None, None, False)
            results["experiments"].append(e2)
        if "E1" in wanted and "E2" in wanted:
            results["paired_delta"] = {
                "delta_dti": round(e1["dti"] - e2["dti"], 6),
                "note": "same budget, eligibility, spacing and obligation; only the surface differs",
            }
        for e in results["experiments"]:
            print(
                f"{e['experiment']}: HOLDOUT-DTI={e['dti']} CI={e['ci95']} "
                f"withheld={e['n_withheld_positive_pixels']}",
                flush=True,
            )
    if args.emit is not None:
        emitted = emit(args.emit, fp, labels, static_fp, static_names, profile)
        surface = emitted.pop("surface")
        dots = emitted.pop("dots_mask")
        seen: set[str] = set()
        comparators = []
        for p in [
            WITNESS,
            *sorted((ROOT / "inputs").glob("*.tif")),
            *sorted((ROOT / "inputs/calibration").glob("*.tif")),
            *sorted((ROOT / "docs/downloads").glob("*.tif")),
            *sorted(CACHE.glob("*.tif")),
        ]:
            key = str(p)
            if key not in seen and p != args.emit.resolve():
                seen.add(key)
                comparators.append((p.name[:80], p))
        audits = audit_dots(dots, fp, comparators)
        worst_overlap = max(a["forward_3px_overlap"] for a in audits)
        worst_rho = max(abs(a["spearman_rho"]) for a in audits)
        worst_ov_name = max(audits, key=lambda a: a["forward_3px_overlap"])["comparator"]
        results["emitted"] = emitted
        results["uniqueness_audit"] = {
            "n_comparators": len(audits),
            "rule": (
                "|Spearman| <= 0.90 on the footprint surface AND <= 70% of dots within 3 px "
                "of any one raster"
            ),
            "worst_forward_3px_overlap": worst_overlap,
            "worst_overlap_comparator": worst_ov_name,
            "worst_abs_spearman": worst_rho,
            "pass": bool(worst_overlap <= 0.70 and worst_rho <= 0.90),
            "per_comparator": audits,
        }
        cid = submission.scored_content_id(surface, fp, labels)
        results["emitted"]["scored_content_id"] = cid
        print(
            "audit: worst overlap %.4f (%s) worst |rho| %.4f pass=%s"
            % (worst_overlap, worst_ov_name, worst_rho, results["uniqueness_audit"]["pass"]),
            flush=True,
        )
        print("content_id", cid, flush=True)
    if args.skip_holdout:
        result_path = EMIT_RESULT.with_name(
            EMIT_RESULT.stem
            + ("" if args.channels == "all" else f"-{args.channels}")
            + EMIT_RESULT.suffix
        )
    else:
        result_path = RESULT.with_name(
            RESULT.stem
            + ("" if args.channels == "all" else f"-{args.channels}")
            + RESULT.suffix
        )
    results["seconds"] = round(time.time() - t0, 1)
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(results, indent=2, allow_nan=False, default=str) + "\n")
    print("wrote", result_path.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
