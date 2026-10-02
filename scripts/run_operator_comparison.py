#!/usr/bin/env python3
"""Operator head-to-head and frozen selection of the thinned-H19-5 deliverables.

Design, selection rule and confirmation are frozen in
``knowledge/04_preregistered_emission_2026-10-02.md`` (sections 5-6) before this runs.
No weekly slot is spent. Output: ``evidence/h24_e1_operator_comparison.json``.
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems import emission, footprint, holdout, thinning  # noqa: E402
from gems.emission_eval import FoldCache, verify_against_reference  # noqa: E402

SELECTION = range(0, 30)
CONFIRMATION = range(30, 60)
D_GRID = (1.5, 2.4, 3.2)
K_GRID = (0.45, 0.50, 0.55, 0.60)
BASES = {"h19-5": ("inputs/*h19-5*-nan.tif", 0.1922), "h19-4": ("inputs/*h19-4*-nan.tif", 0.1894)}
PHI = 0.05


def read_mask(path, fp):
    with rasterio.open(path) as d:
        a = d.read(1)
    return (np.nan_to_num(a, nan=0.0) > 0.5) & fp


def evaluate(cache, mask):
    prep = cache.prep(mask)
    dense = cache.dense_scores(prep)
    sparse = [cache.sparse_scores(prep, d) for d in range(cache.n_draws)]
    return {
        "dense_fold": [r["dti"] for r in dense],
        "dense_tp": [r["tp"] for r in dense],
        "sparse": np.array([[r["dti"] for r in s] for s in sparse]),  # draws x folds
        "sparse_tp": np.array([[r["tp"] for r in s] for s in sparse]),
    }


def summary(res):
    fs = res["sparse"].mean(axis=0)
    return {
        "fold_dense": [round(float(x), 5) for x in res["dense_fold"]],
        "fold_sparse": [round(float(x), 5) for x in fs],
        "mean_dense_dti": round(float(np.mean(res["dense_fold"])), 5),
        "mean_sparse_dti": round(float(np.mean(fs)), 5),
    }


def main():
    t0 = time.time()
    (ROOT / "out").mkdir(exist_ok=True)
    fp = footprint.load_footprint()
    with rasterio.open(ROOT / "data/bridge/labels.tif") as d:
        labels = (d.read(1) > 0) & fp
    area = int(fp.sum())
    tau = json.loads((ROOT / "evidence/emission_calibration.json").read_text())["lattice"]["tau"]
    caches = {
        "selection": FoldCache(fp, labels, SELECTION),
        "confirmation": FoldCache(fp, labels, CONFIRMATION),
    }
    out = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "preregistration": "knowledge/04_preregistered_emission_2026-10-02.md (sections 5-6)",
        "tau": tau,
        "phi": PHI,
        "selection_draw_offsets": [SELECTION.start, SELECTION.stop - 1],
        "confirmation_draw_offsets": [CONFIRMATION.start, CONFIRMATION.stop - 1],
        "bases": {},
        "slot_spent": False,
    }
    for tag, (pat, lb) in BASES.items():
        base = read_mask(next(ROOT.glob(pat)), fp)
        assert not (base & labels).any()
        cands = {"solid": (base, "baseline", None)}
        for d in D_GRID:
            m = thinning.dot_thin(base, d)
            cands[f"D{d:g}"] = (m, "dot_thin", d)
        n_base = int(base.sum())
        fs = {round(cands[f"D{d:g}"][0].sum() / n_base, 3) for d in D_GRID} | set(K_GRID)
        for f in sorted(fs):
            cands[f"K{f:.3f}"] = (emission.kernel_cover_thin(base, f), "kernel_cover", f)
        # equal-N pairing information
        results = {}
        for name, (mask, kind, par) in cands.items():
            results[name] = {
                "kind": kind,
                "param": par,
                "n": int(mask.sum()),
                "pixel_fraction": float(mask.sum() / n_base),
                "mask": mask,
            }
        if tag == "h19-5":
            worst = verify_against_reference(caches["selection"], fp, labels, cands["D2.4"][0])
            out["evaluator_max_abs_diff_vs_gems_metric"] = worst
        for split, cache in caches.items():
            for name in cands:
                results[name][split] = evaluate(cache, results[name]["mask"])
        base_sum = {split: summary(results["solid"][split]) for split in caches}
        rows = {}
        for name, r in results.items():
            row = {k: r[k] for k in ("kind", "param", "n", "pixel_fraction")}
            for split in caches:
                res = r[split]
                b = results["solid"][split]
                ret_s = float(res["sparse_tp"].sum() / b["sparse_tp"].sum())
                ret_d = float(np.sum(res["dense_tp"]) / np.sum(b["dense_tp"]))
                s = summary(res)
                row[split] = {
                    **s,
                    "sparse_mean_over_draws": float(res["sparse"].mean()),
                    "paired_sparse_gain_abs": float(res["sparse"].mean() - b["sparse"].mean()),
                    "paired_sparse_gain_rel": float(
                        res["sparse"].mean() / b["sparse"].mean() - 1.0
                    ),
                    "paired_dense_gain_abs": float(
                        np.mean(res["dense_fold"]) - np.mean(b["dense_fold"])
                    ),
                    "sparse_retention": ret_s,
                    "dense_retention": ret_d,
                    "model_public_score": emission.extrapolate_variant(
                        lb, n_base, r["n"], min(ret_s, 1.0), area, tau, phi=PHI
                    ),
                    "draw_fold_wins": int((res["sparse"] > b["sparse"]).sum()),
                    "draw_fold_cells": int(res["sparse"].size),
                }
                if name != "solid":
                    row[split]["legacy_gate"] = holdout.gate(s, base_sum[split])
            rows[name] = row
        out["bases"][tag] = {"lb_owner": lb, "n_base": n_base, "candidates": rows}
        for name, r in results.items():
            r.pop("mask", None)
        print(f"-- {tag}", flush=True)
        for name, row in rows.items():
            s, c = row["selection"], row["confirmation"]
            print(
                f"{name:9s} N={row['n']:6d} ({row['pixel_fraction']:.3f})"
                f" sel: dense {s['mean_dense_dti']:.4f} sparse {s['mean_sparse_dti']:.4f}"
                f" gate={s.get('legacy_gate', {}).get('passed')} model={s['model_public_score']:.4f}"
                f" | conf: dense {c['mean_dense_dti']:.4f} sparse {c['mean_sparse_dti']:.4f}"
                f" gate={c.get('legacy_gate', {}).get('passed')}",
                flush=True,
            )
        if tag == "h19-5":
            np.savez_compressed(
                ROOT / "out/h24_e1_operator_candidates.npz",
                **{n.replace(".", "_"): np.packbits(m) for n, (m, _k, _p) in cands.items()},
            )

    # ---- frozen selection on H19-5 -------------------------------------------------
    rows = out["bases"]["h19-5"]["candidates"]
    eligible = [
        n for n, r in rows.items() if n != "solid" and r["selection"]["legacy_gate"]["passed"]
    ]
    eligible.sort(key=lambda n: (-rows[n]["selection"]["model_public_score"], -rows[n]["n"]))
    primary = None
    for n in eligible:
        if rows[n]["confirmation"]["legacy_gate"]["passed"]:
            primary = n
            break
    sparse_opt = max(
        (n for n in rows if n != "solid"),
        key=lambda n: (rows[n]["selection"]["mean_sparse_dti"], rows[n]["n"]),
    )
    out["frozen_selection"] = {
        "eligible_on_selection_draws_ranked_by_model_score": eligible,
        "primary": primary,
        "primary_passes_confirmation": bool(primary),
        "alternate_sparse_optimal": sparse_opt,
        "alternate_selection_gate_passed": rows[sparse_opt]["selection"]["legacy_gate"]["passed"],
        "alternate_confirmation_gate_passed": rows[sparse_opt]["confirmation"]["legacy_gate"][
            "passed"
        ],
    }
    out["seconds"] = time.time() - t0
    (ROOT / "evidence/h24_e1_operator_comparison.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out["frozen_selection"], indent=1))
    print("done", out["seconds"])


if __name__ == "__main__":
    main()
