"""H24-PAIR1 lane runner (preregistration: knowledge/25_preregistered_PAIR1_2026-10-26.md).

Reuses shared tools only: gems.holdout.SegmentHoldout, gems.emission.priority_poisson,
gems.submission (writer + check_variants), gems.novelty. No prior submission pixels
are read as features; registry rasters are opened only for the novelty audit.
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt
from sklearn.ensemble import HistGradientBoostingClassifier

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems import emission, holdout, novelty, submission  # noqa: E402

SEED = 20261026
FULL_BUDGET = 37654
DIRS8 = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


def unpack(q: np.ndarray) -> np.ndarray:
    """uint8 cache convention: 0 = nodata, else 1 + round(254*t(x)) -> t(x) in [0,1]."""
    out = np.full(q.shape, np.nan, dtype=np.float32)
    ok = q > 0
    out[ok] = (q[ok].astype(np.float32) - 1.0) / 254.0
    return out


def shift(a: np.ndarray, dy: int, dx: int) -> np.ndarray:
    out = np.full_like(a, np.nan)
    ys = slice(max(dy, 0), a.shape[0] + min(dy, 0))
    xs = slice(max(dx, 0), a.shape[1] + min(dx, 0))
    yt = slice(max(-dy, 0), a.shape[0] + min(-dy, 0))
    xt = slice(max(-dx, 0), a.shape[1] + min(-dx, 0))
    out[ys, xs] = a[yt, xt]
    return out


def pair_offset(a: np.ndarray, b: np.ndarray, offsets: tuple[int, ...]) -> np.ndarray:
    best = np.full(a.shape, -1.0, dtype=np.float32)
    for dy, dx in DIRS8:
        for o in offsets:
            cand = np.fmin(a, shift(b, dy * o, dx * o))
            best = np.fmax(best, np.where(np.isnan(cand), -1.0, cand))
    return np.where(best < 0, np.nan, best).astype(np.float32)


def load_features(fp: np.ndarray) -> tuple[np.ndarray, list[str], list[str]]:
    """Return (X on footprint pixels, base_names, new_operator_names)."""
    cols: dict[str, np.ndarray] = {}
    lidar_names = json.loads((ROOT / "data/external/lidar_scarp_features.json").read_text())[
        "bands"
    ]
    with rasterio.open(ROOT / "data/external/lidar_scarp_features_u8.tif") as ds:
        for i, name in enumerate(lidar_names, start=1):
            cols[f"lidar_{name}"] = unpack(ds.read(i))
    with rasterio.open(ROOT / "data/external/geodawn_rad_u8.tif") as ds:
        for i, name in enumerate(["K", "Th", "U", "TC"], start=1):
            cols[f"rad_{name}"] = unpack(ds.read(i))
    with rasterio.open(ROOT / "data/external/geodawn_extensions_u8.tif") as ds:
        for i, name in enumerate(["ThK", "UK", "UTh", "TMI_up150"], start=1):
            cols[f"ext_{name}"] = unpack(ds.read(i))

    strike = cols.pop("lidar_strike")  # quantized angle/180 in [0,1]
    theta = strike * np.pi  # strike is axial: use doubled-angle encoding
    cols["strike_sin2"] = np.sin(2 * theta).astype(np.float32)
    cols["strike_cos2"] = np.cos(2 * theta).astype(np.float32)
    cols["has_lidar"] = np.where(np.isnan(cols["lidar_valid"]), 0.0, 1.0).astype(np.float32)
    base_names = list(cols.keys())

    up, down = cols["lidar_upface_max"], cols["lidar_downface_max"]
    new: dict[str, np.ndarray] = {
        "pair_same": np.fmin(up, down).astype(np.float32),
        "pair_offset": np.fmax(pair_offset(up, down, (1, 2, 3)), pair_offset(down, up, (1, 2, 3))),
        "dipole_crest_base": pair_offset(
            cols["lidar_lapneg_max"], cols["lidar_lappos_max"], (1, 2)
        ),
    }
    new["pair_x_coh"] = (new["pair_offset"] * cols["lidar_coh100"]).astype(np.float32)
    cols.update(new)
    names = list(cols.keys())
    X = np.column_stack([cols[n][fp] for n in names]).astype(np.float32)
    return X, base_names, list(new.keys()), names


def fit_predict(X, fp_ids, fold, feat_idx, rng):
    labels_visible = fold["visible"]
    dist_vis = distance_transform_edt(~labels_visible)
    pos_mask = fold["train"] & labels_visible
    neg_mask = fold["train"] & (~labels_visible) & (dist_vis >= 9)
    pos_ids = np.flatnonzero(pos_mask.ravel())
    neg_ids = np.flatnonzero(neg_mask.ravel())
    neg_take = rng.choice(neg_ids, size=min(len(neg_ids), 3 * len(pos_ids)), replace=False)
    train_flat = np.r_[pos_ids, neg_take]
    y = np.r_[np.ones(len(pos_ids)), np.zeros(len(neg_take))].astype(np.int8)
    pos_in_fp = np.searchsorted(fp_ids, train_flat)
    clf = HistGradientBoostingClassifier(
        max_iter=190,
        learning_rate=0.055,
        max_leaf_nodes=31,
        min_samples_leaf=80,
        l2_regularization=2.5,
        early_stopping=False,
        random_state=SEED,
    )
    clf.fit(X[pos_in_fp][:, feat_idx], y)
    val_flat = np.flatnonzero(fold["valid"].ravel())
    val_in_fp = np.searchsorted(fp_ids, val_flat)
    surf = np.zeros(fp_shape_global, dtype=np.float32)
    for s in range(0, len(val_in_fp), 250_000):
        ch = val_in_fp[s : s + 250_000]
        surf.ravel()[fp_ids[ch]] = clf.predict_proba(X[ch][:, feat_idx])[:, 1]
    return surf, clf


fp_shape_global = (3730, 3292)


def emit_fold(surf, fold, k_fold, clearance):
    elig = fold["valid"] & (distance_transform_edt(~fold["visible"]) > clearance)
    return emission.priority_poisson(surf, elig, int(k_fold), min_dist=3.0)


def main() -> None:
    t0 = time.time()
    with rasterio.open(ROOT / "data/bridge/sample_submission.tif") as ds:
        fp = np.isfinite(ds.read(1))
    with rasterio.open(ROOT / "data/bridge/existing_faults.tif") as ds:
        catalogue = ds.read(1) == 1
    fp_ids = np.flatnonzero(fp.ravel())
    print("[1/6] loading features …", flush=True)
    X, base_names, new_names, all_names = load_features(fp)
    print(
        f"      X={X.shape} base={len(base_names)} new={new_names} ({time.time() - t0:.0f}s)",
        flush=True,
    )

    ctx = holdout.SegmentHoldout(fp, catalogue, buffer_px=15)

    print("[2/6] leakage canaries (every feature alone) …", flush=True)
    feat2d = {}
    for j, n in enumerate(all_names):
        g = np.zeros(fp.shape, dtype=np.float32)
        g.ravel()[fp_ids] = np.where(np.isnan(X[:, j]), 0, X[:, j])
        feat2d[n] = g
    canary = ctx.canary(feat2d)
    worst = max(
        ((max(v["pooled_auc"], 1 - v["pooled_auc"]), k) for k, v in canary["features"].items())
    )
    print(
        f"      canary passed={canary['passed']} worst={worst} ({time.time() - t0:.0f}s)",
        flush=True,
    )
    if not canary["passed"]:
        raise SystemExit("LEAKAGE CANARY FAILED — stopping per protocol Rule 4")

    total_offcat = int((fp & ~catalogue).sum())
    base_idx = [all_names.index(n) for n in base_names]
    pair_idx = list(range(len(all_names)))

    results: dict = {}
    stitched: dict[str, np.ndarray] = {}
    for exp, feat_idx, clearance in (
        ("exp1_base", base_idx, 2.0),
        ("exp2_pair1", pair_idx, 2.0),
        ("exp3_pair1_clear3", pair_idx, 3.0),
    ):
        print(f"[3/6] {exp}: 4-fold OOF …", flush=True)
        preds, surf_full = [], np.zeros(fp.shape, dtype=np.float32)
        fold_rng = np.random.default_rng(SEED)
        for fold in ctx.folds:
            surf, _ = fit_predict(X, fp_ids, fold, feat_idx, fold_rng)
            surf_full[fold["valid"]] = surf[fold["valid"]]
            f_offcat = int((fold["valid"] & (~fold["visible"])).sum())
            k_fold = int(round(FULL_BUDGET * f_offcat / total_offcat))
            preds.append(emit_fold(surf, fold, k_fold, clearance).astype(np.float32))
        summ = ctx.summarize(preds, ci_draws=999)
        results[exp] = {
            "dti": summ["dti"],
            "ci95": summ["ci95"]["interval"],
            "n_truth": summ["n_withheld_positive_pixels"],
            "folds": summ["folds"],
            "evaluator": summ["evaluator_version"],
        }
        stitched[exp] = surf_full
        results[exp]["preds"] = preds
        print(
            f"      {exp} HOLDOUT-DTI={summ['dti']:.5f} CI={summ['ci95']['interval']} "
            f"n_truth={summ['n_withheld_positive_pixels']} ({time.time() - t0:.0f}s)",
            flush=True,
        )

    paired = ctx.compare_paired(
        results["exp2_pair1"].pop("preds"), results["exp1_base"].pop("preds"), ci_draws=999
    )
    results["exp3_pair1_clear3"].pop("preds")
    print(
        f"[4/6] paired PAIR1-BASE delta={paired['paired_delta_dti']:.5f} "
        f"CI={paired['paired_delta_ci95']} wins={paired['fold_wins']}/4",
        flush=True,
    )

    # ---- final deployment surface: stitched OOF of the better PAIR1 arm ----
    best_exp = (
        "exp2_pair1"
        if results["exp2_pair1"]["dti"] >= results["exp3_pair1_clear3"]["dti"]
        else "exp3_pair1_clear3"
    )
    clearance = 2.0 if best_exp == "exp2_pair1" else 3.0
    surf = stitched["exp2_pair1"]  # exp2/exp3 share the same surface; only emission differs
    elig = fp & (distance_transform_edt(~catalogue) > clearance)
    dots = emission.priority_poisson(surf, elig, FULL_BUDGET, min_dist=3.0)
    pred2d = np.where(fp, dots.astype(np.float32), 0.0).astype(np.float32)
    cid = submission.scored_content_id(pred2d, fp, catalogue)
    fname = submission.make_filename("gems24", "pair1-graben-dipole-oof", "20261026", cid, "zeros")
    out_dir = ROOT / "docs/downloads"
    zeros_path = out_dir / fname
    nan_path = out_dir / fname.replace("-zeros.tif", "-nan.tif")
    tmpl = ROOT / "data/bridge/sample_submission.tif"
    submission.write_submission(pred2d, tmpl, zeros_path, outside="zero")
    submission.write_submission(pred2d, tmpl, nan_path, outside="nan")
    zip_path = submission.zip_single(zeros_path)
    v_zeros = submission.check_variants(zeros_path, tmpl)
    v_nan = submission.check_variants(nan_path, tmpl)
    print(
        f"[5/6] wrote {fname} dots={int(dots.sum())} sha={v_zeros['sha256'][:16]}… "
        f"format_valid={v_zeros['format_valid']} strict="
        f"{v_zeros['checks']['variant_strict_whole_array_no_nan_allowed']['pass']}",
        flush=True,
    )

    # ---- novelty vs every locally available registry raster ----
    print("[6/6] novelty audit …", flush=True)
    refs = (
        sorted((ROOT / "docs/downloads").glob("*.tif"))
        + sorted((ROOT / "inputs").glob("*.tif"))
        + sorted((ROOT / "inputs/calibration").glob("*.tif"))
    )
    surf_fp = surf[fp].astype(np.float64)
    novelty_rows = []
    for p in refs:
        if p.name in (fname, nan_path.name):
            continue
        with rasterio.open(p) as ds:
            a = ds.read(1)
        ref_dots = np.isfinite(a) & (a > 0) & fp
        if not ref_dots.any():
            continue
        ov = novelty.dot_overlap(dots, ref_dots, radius_px=3.0)
        rho = novelty.correlation(surf_fp, ref_dots[fp].astype(np.float64))
        novelty_rows.append(
            {
                "reference": str(p.relative_to(ROOT)),
                "spearman_rho_surface_vs_refdots": rho,
                "candidate_within_3px_of_reference": ov["candidate_within_3px_of_reference"],
                "reference_dots": ov["reference_dots"],
                "is_duplicate": novelty.is_duplicate(rho, ov["candidate_within_3px_of_reference"]),
            }
        )
    lattice = [r for r in novelty_rows if "lattice" in r["reference"]]
    competing = [r for r in novelty_rows if "lattice" not in r["reference"]]
    max_rho = max((abs(r["spearman_rho_surface_vs_refdots"] or 0) for r in competing), default=None)
    max_ov = max((r["candidate_within_3px_of_reference"] or 0) for r in competing)
    print(
        f"      competing refs={len(competing)} max|rho|={max_rho:.4f} max_overlap={max_ov:.4f} "
        f"lattice_overlap={[r['candidate_within_3px_of_reference'] for r in lattice]}",
        flush=True,
    )

    dcat = distance_transform_edt(~catalogue)[dots]
    dist_profile = {
        "frac_le_2px": float((dcat <= 2).mean()),
        "frac_2_to_9px": float(((dcat > 2) & (dcat <= 9)).mean()),
        "frac_gt_20px": float((dcat > 20).mean()),
        "min_px": float(dcat.min()),
        "median_px": float(np.median(dcat)),
    }
    card = {
        "lane": "H24-PAIR1",
        "date": "2026-10-26",
        "preregistration": "knowledge/25_preregistered_PAIR1_2026-10-26.md",
        "features": {"base": base_names, "new_operators": new_names, "all": all_names},
        "canary": {
            "passed": canary["passed"],
            "worst_two_polarity_auc": worst[0],
            "worst_feature": worst[1],
            "features": {k: v["pooled_auc"] for k, v in canary["features"].items()},
        },
        "experiments": {
            k: {kk: vv for kk, vv in v.items() if kk != "folds"} | {"folds": v["folds"]}
            for k, v in results.items()
        },
        "paired_pair1_vs_base": paired,
        "final": {
            "source_experiment": best_exp,
            "clearance_px": clearance,
            "file_zeros": fname,
            "file_nan": nan_path.name,
            "zip": zip_path.name,
            "content_id": cid,
            "dots": int(dots.sum()),
            "sha256_zeros": v_zeros["sha256"],
            "sha256_zip": hashlib.sha256(zip_path.read_bytes()).hexdigest(),
            "validator_zeros": v_zeros,
            "validator_nan_format_valid": v_nan["format_valid"],
            "distance_to_catalogue_profile": dist_profile,
        },
        "novelty": {
            "n_competing_references": len(competing),
            "max_abs_spearman_competing": max_rho,
            "max_dot_overlap_3px_competing": max_ov,
            "lattice_control_rows": lattice,
            "rows": novelty_rows,
        },
        "runtime_s": round(time.time() - t0, 1),
    }
    (ROOT / "evidence/pair1_experiment_20261026.json").write_text(
        json.dumps(card, indent=2, default=float) + "\n"
    )
    print(f"DONE in {time.time() - t0:.0f}s -> evidence/pair1_experiment_20261026.json", flush=True)


if __name__ == "__main__":
    main()
