#!/usr/bin/env python3
"""H24-E1: calibrated kernel-cover emission, paired holdout test (no submission slot is spent).

Follows ``knowledge/04_preregistered_emission_2026-10-02.md``.  Frozen grid and
decision rule are not tuned here.  Outputs ``evidence/emission_calibration.json``
and ``evidence/h24_e1_emission_experiment.json``.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems import emission, footprint, holdout  # noqa: E402
from gems.emission_eval import FoldCache, verify_against_reference  # noqa: E402
from gems.validator import sha256_file  # noqa: E402

FRACTIONS = (0.60, 0.45, 0.35, 0.25)
N_DRAWS = 30
LATTICE = "13gems_20261001_r13-lattice-s5_v2_nan-outside.tif"
LATTICE_SCORE = 0.0904  # owner-reported, 13GEMSDOE
PAIR = (
    ("gems10-h25-ctx-ridge-20260927T232947704150Z-6452ae1d00.tif", 0.1280),
    ("gems10-h28-dotted-ridge-20260928T020256236880Z-6452ae1d00.tif", 0.1839),
)
MASKING_PAIR = (
    ("gemsdoe-ens12-adopted-7f00890a.tif", 0.1563),
    ("8GEMSDOE_Hedge-v2_submission.tif", 0.1563),
)
BASES = {"h19-5": ("inputs/*h19-5*-nan.tif", 0.1922), "h19-4": ("inputs/*h19-4*-nan.tif", 0.1894)}
SEED = 20261002


def read_mask(path, fp):
    with rasterio.open(path) as d:
        a = d.read(1)
    return (np.nan_to_num(a, nan=0.0) > 0.5) & fp


def calibration(fp, labels):
    cal = ROOT / "inputs/calibration"
    lat = read_mask(cal / LATTICE, fp)
    est = emission.lattice_truth_density(lat, fp, labels, LATTICE_SCORE)
    sens = {}
    for s in (LATTICE_SCORE - 0.00005, LATTICE_SCORE + 0.00005):
        sens[f"{s:.5f}"] = emission.lattice_truth_density(lat, fp, labels, s)["tau"]
    area = int(fp.sum())
    # natural experiment (same probability-surface id 6452ae1d00): ridge vs dotted
    (n25, s25), (n28, s28) = PAIR
    m25, m28 = read_mask(cal / n25, fp) & ~labels, read_mask(cal / n28, fp) & ~labels
    k25, k28 = emission.kernel_credit(m25), emission.kernel_credit(m28)
    near = (distance_transform_edt(~m25) <= 1) & fp & ~labels
    geo_ret = float(k28[near].mean() / k25[near].mean())
    tp25 = emission.implied_credit(s25, m25.sum() / area, est["tau"])
    tp28 = emission.implied_credit(s28, m28.sum() / area, est["tau"])
    pred28 = {
        f"{r:.2f}": emission.extrapolate_variant(
            s25, int(m25.sum()), int(m28.sum()), r, area, est["tau"]
        )
        for r in (0.70, 0.75, 0.80, 0.85)
    }
    # masking check: Hedge-v2 = ens12 off-catalogue pixels + all catalogue pixels, same reported score
    (a_name, a_s), (b_name, b_s) = MASKING_PAIR
    A, B = read_mask(cal / a_name, fp), read_mask(cal / b_name, fp)
    masking = {
        "ens12_reported": a_s,
        "hedge_v2_reported": b_s,
        "identical_off_catalogue_pixels": bool(np.array_equal(A & ~labels, B & ~labels)),
        "hedge_pixels_on_catalogue": int((B & labels).sum()),
        "ens12_pixels_on_catalogue": int((A & labels).sum()),
        "inference": "Adding every catalogue pixel as a prediction left the reported score unchanged, "
        "consistent with known-pixel masking of predictions (owner-reported scores; not an organizer receipt).",
    }
    return {
        "lattice": {
            "file": LATTICE,
            "sha256": sha256_file(cal / LATTICE),
            "reported_score_owner": LATTICE_SCORE,
            **est,
            "tau_sensitivity_to_score_rounding": sens,
            "synthetic_estimator_error": "mean +2.5 %, sd 7.6 %, range -9 %..+18 % over 24 synthetic truth layouts (tests/test_emission.py world)",
            "catalogue_px": int(labels.sum()),
            "truth_to_catalogue_ratio": est["truth_px_equivalent"] / int(labels.sum()),
        },
        "natural_experiment_same_surface_6452ae1d00": {
            "ridge": {
                "file": n25,
                "reported": s25,
                "off_catalogue_px": int(m25.sum()),
                "implied_credit_over_truth": tp25 / est["tau"],
            },
            "dotted": {
                "file": n28,
                "reported": s28,
                "off_catalogue_px": int(m28.sum()),
                "implied_credit_over_truth": tp28 / est["tau"],
            },
            "pixel_ratio": float(m28.sum() / m25.sum()),
            "geometric_credit_retention_truth_within_1px_of_ridge": geo_ret,
            "implied_credit_retention_from_reported_scores": float(tp28 / tp25),
            "model_predicted_dotted_score_by_retention": pred28,
            "score_change": s28 / s25 - 1.0,
        },
        "known_pixel_masking_check": masking,
        "assumptions": [
            "lattice is a blind sampler: expected credit at a truth pixel is independent of truth layout",
            "false-positive mass ~ N(1-phi), phi = mean kernel proximity of emitted pixels to truth (0.05; swept 0-0.10)",
            "public-subset truth density transfers to the private subset; Phase 2 truth is denser",
            "owner-reported scores are correctly attributed to these exact files (content ids = sha256 prefixes)",
        ],
    }


def stats(x):
    x = np.asarray(x, float)
    return {"mean": float(x.mean()), "sd": float(x.std(ddof=1)) if len(x) > 1 else 0.0}


def boot_ci(diff, n=4000, seed=1):
    rng = np.random.default_rng(seed)
    d = np.asarray(diff, float)
    m = d[rng.integers(0, len(d), (n, len(d)))].mean(axis=1)
    return [float(np.quantile(m, 0.025)), float(np.quantile(m, 0.975))]


def validate_extrapolation_on_pair(cache, fp, labels, tau, area):
    """Out-of-sample check of the extrapolation method on h25 -> h28 (known owner-reported scores).

    Retention is measured with the SAME harness used for H19 (30 sparse draws), the base score
    is h25's reported 0.1280, and the prediction is compared with h28's reported 0.1839.
    The method never saw h28's score; tau comes from the lattice only.
    """
    cal = ROOT / "inputs/calibration"
    (n25, s25), (n28, s28) = PAIR
    m25 = read_mask(cal / n25, fp) & ~labels
    m28 = read_mask(cal / n28, fp) & ~labels
    tp = {}
    for tag, m in (("h25", m25), ("h28", m28)):
        prep = cache.prep(m)
        tp[tag] = {
            "sparse": float(
                sum(r["tp"] for d in range(cache.n_draws) for r in cache.sparse_scores(prep, d))
            ),
            "dense": float(sum(r["tp"] for r in cache.dense_scores(prep))),
        }
    dti = {}
    for tag, m in (("h25", m25), ("h28", m28)):
        prep = cache.prep(m)
        dti[tag] = {
            "sparse": float(
                np.mean(
                    [[r["dti"] for r in cache.sparse_scores(prep, d)] for d in range(cache.n_draws)]
                )
            ),
            "dense": float(np.mean([r["dti"] for r in cache.dense_scores(prep)])),
        }
    ret_sparse = tp["h28"]["sparse"] / tp["h25"]["sparse"]
    ret_dense = tp["h28"]["dense"] / tp["h25"]["dense"]
    out = {
        "pair": [n25, n28],
        "reported": [s25, s28],
        "n_off_catalogue": [int(m25.sum()), int(m28.sum())],
        "harness_sparse_retention": ret_sparse,
        "harness_dense_retention": ret_dense,
        "harness_dti": dti,
        "harness_sparse_dti_ratio_h28_over_h25": dti["h28"]["sparse"] / dti["h25"]["sparse"],
        "harness_dense_dti_ratio_h28_over_h25": dti["h28"]["dense"] / dti["h25"]["dense"],
        "predictions": {},
    }
    for phi in (0.0, 0.05, 0.10):
        out["predictions"][f"phi{phi:.2f}"] = emission.extrapolate_variant(
            s25, int(m25.sum()), int(m28.sum()), min(ret_sparse, 1.0), area, tau, phi=phi
        )
    out["observed"] = s28
    out["abs_error_phi0.05"] = out["predictions"]["phi0.05"] - s28
    out["relative_gain_predicted_phi0.05"] = out["predictions"]["phi0.05"] / s25 - 1.0
    out["relative_gain_observed"] = s28 / s25 - 1.0
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--draws", type=int, default=N_DRAWS)
    args = ap.parse_args()
    t0 = time.time()
    fp = footprint.load_footprint()
    with rasterio.open(ROOT / "data/bridge/labels.tif") as d:
        labels = (d.read(1) > 0) & fp
    area = int(fp.sum())
    cal = calibration(fp, labels)
    (ROOT / "evidence/emission_calibration.json").write_text(json.dumps(cal, indent=2) + "\n")
    tau = cal["lattice"]["tau"]
    print(
        "tau",
        tau,
        "natural-experiment retention",
        cal["natural_experiment_same_surface_6452ae1d00"][
            "implied_credit_retention_from_reported_scores"
        ],
        flush=True,
    )

    cache = FoldCache(fp, labels, range(args.draws))
    validation = validate_extrapolation_on_pair(cache, fp, labels, tau, area)
    print(
        "pair validation:",
        json.dumps(
            {
                k: validation[k]
                for k in ("harness_sparse_retention", "observed", "abs_error_phi0.05")
            }
        ),
        flush=True,
    )
    candidates = {}
    meta = {}
    for tag, (pat, lb) in BASES.items():
        base = read_mask(next(ROOT.glob(pat)), fp)
        assert not (base & labels).any(), "baseline must not emit on catalogue cells"
        candidates[tag] = base
        meta[tag] = {"kind": "baseline", "base": tag, "lb_owner": lb, "n": int(base.sum())}
        for f in FRACTIONS:
            t1 = time.time()
            cov = emission.kernel_cover_thin(base, f)
            rnd = emission.random_thin(base, f, SEED)
            candidates[f"{tag}|K{f:.2f}"] = cov
            candidates[f"{tag}|R{f:.2f}"] = rnd
            meta[f"{tag}|K{f:.2f}"] = {
                "kind": "kernel_cover",
                "base": tag,
                "keep": f,
                "n": int(cov.sum()),
            }
            meta[f"{tag}|R{f:.2f}"] = {
                "kind": "random_control",
                "base": tag,
                "keep": f,
                "n": int(rnd.sum()),
            }
            print(f"built {tag} f={f} cover n={cov.sum()} in {time.time() - t1:.1f}s", flush=True)
    worst = verify_against_reference(cache, fp, labels, candidates["h19-5|K0.45"])
    print("cached evaluator exact; worst abs diff", worst, flush=True)

    res = {}
    for key, mask in candidates.items():
        prep = cache.prep(mask)
        dense = cache.dense_scores(prep)
        sparse = [cache.sparse_scores(prep, d) for d in range(args.draws)]
        res[key] = {
            "dense_fold": [r["dti"] for r in dense],
            "dense_tp": [r["tp"] for r in dense],
            "sparse_fold": [[r["dti"] for r in s] for s in sparse],
            "sparse_tp": [[r["tp"] for r in s] for s in sparse],
        }
    out = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "preregistration": "knowledge/04_preregistered_emission_2026-10-02.md",
        "n_draws": args.draws,
        "fractions": list(FRACTIONS),
        "evaluator_max_abs_diff_vs_gems_metric": worst,
        "footprint_px": area,
        "calibration": cal,
        "extrapolation_validation_h25_to_h28": validation,
        "candidates": {},
        "slot_spent": False,
    }
    for key in candidates:
        r = res[key]
        base_key = meta[key]["base"]
        b = res[base_key]
        dense_mean = float(np.mean(r["dense_fold"]))
        sp = np.array(r["sparse_fold"])  # draws x folds
        sp_mean_draw = sp.mean(axis=1)
        bsp = np.array(b["sparse_fold"])
        diff_draw = sp_mean_draw - bsp.mean(axis=1)
        fold_wins = int((sp > bsp).sum())
        ret_sparse = float(np.sum(r["sparse_tp"]) / np.sum(b["sparse_tp"]))
        ret_dense = float(np.sum(r["dense_tp"]) / np.sum(b["dense_tp"]))
        n_var, n_base = meta[key]["n"], meta[base_key]["n"]
        lb_base = meta[base_key]["lb_owner"]
        ext = {}
        if key != base_key:
            for phi in (0.0, 0.05, 0.10):
                ext[f"phi{phi:.2f}"] = {
                    "sparse_retention": emission.extrapolate_variant(
                        lb_base, n_base, n_var, min(ret_sparse, 1.0), area, tau, phi=phi
                    ),
                    "dense_retention": emission.extrapolate_variant(
                        lb_base, n_base, n_var, min(ret_dense, 1.0), area, tau, phi=phi
                    ),
                }
            tau_hi, tau_lo = tau * 1.15, tau * 0.85
            ext["tau_plus15pct"] = emission.extrapolate_variant(
                lb_base, n_base, n_var, min(ret_sparse, 1.0), area, tau_hi
            )
            ext["tau_minus15pct"] = emission.extrapolate_variant(
                lb_base, n_base, n_var, min(ret_sparse, 1.0), area, tau_lo
            )
            ext["tau_x2_if_calibration_wrong_by_2x"] = emission.extrapolate_variant(
                lb_base, n_base, n_var, min(ret_sparse, 1.0), area, tau * 2.0
            )
        out["candidates"][key] = {
            **meta[key],
            "pixel_fraction_of_base": n_var / n_base,
            "dense_mean": dense_mean,
            "dense_fold": r["dense_fold"],
            "sparse_mean_over_draws": stats(sp_mean_draw),
            "sparse_fold_mean_over_draws": [float(x) for x in sp.mean(axis=0)],
            "paired_sparse_diff_vs_base": {**stats(diff_draw), "bootstrap95": boot_ci(diff_draw)},
            "paired_dense_diff_vs_base": dense_mean - float(np.mean(b["dense_fold"])),
            "sparse_fold_draw_wins_vs_base": fold_wins,
            "sparse_fold_draw_total": int(sp.size),
            "sparse_credit_retention": ret_sparse,
            "dense_credit_retention": ret_dense,
            "model_extrapolated_public_score": ext,
        }
        print(
            f"{key:14s} N={n_var:7d} dense={dense_mean:.5f} sparse={np.mean(sp_mean_draw):.5f}"
            f" d_sparse={np.mean(diff_draw):+.5f} wins={fold_wins}/{sp.size} ret_s={ret_sparse:.3f}",
            flush=True,
        )
    # legacy gate, reported without modification (mean-over-draws fold scores)
    legacy = {}
    for tag in BASES:
        b = res[tag]
        base_sum = {
            "fold_dense": [round(float(x), 5) for x in b["dense_fold"]],
            "fold_sparse": [round(float(x), 5) for x in np.array(b["sparse_fold"]).mean(axis=0)],
        }
        base_sum["mean_dense_dti"] = round(float(np.mean(base_sum["fold_dense"])), 5)
        base_sum["mean_sparse_dti"] = round(float(np.mean(base_sum["fold_sparse"])), 5)
        for f in FRACTIONS:
            key = f"{tag}|K{f:.2f}"
            c = res[key]
            cs = {
                "fold_dense": [round(float(x), 5) for x in c["dense_fold"]],
                "fold_sparse": [
                    round(float(x), 5) for x in np.array(c["sparse_fold"]).mean(axis=0)
                ],
            }
            cs["mean_dense_dti"] = round(float(np.mean(cs["fold_dense"])), 5)
            cs["mean_sparse_dti"] = round(float(np.mean(cs["fold_sparse"])), 5)
            legacy[key] = holdout.gate(cs, base_sum)
    out["legacy_gate_vs_base"] = legacy
    out["seconds"] = time.time() - t0
    (ROOT / "out").mkdir(exist_ok=True)
    np.savez_compressed(
        ROOT / "out/h24_e1_candidates.npz",
        **{k.replace("|", "__"): np.packbits(v) for k, v in candidates.items()},
    )
    (ROOT / "evidence/h24_e1_emission_experiment.json").write_text(json.dumps(out, indent=2) + "\n")
    print("done", out["seconds"], flush=True)


if __name__ == "__main__":
    main()
