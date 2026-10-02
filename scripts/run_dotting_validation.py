#!/usr/bin/env python3
"""Frozen validation of H25-1 'Dotted H19' (knowledge/04_preregistered_dotting_2026-10-02.md).

Paired comparison of an emission mask with and without geodesic dot thinning, scored with the exact
DTI formulas on identical truths. The transform reads no label, truth or score, so any difference is
due to emission geometry only. Never consumes a submission slot.

Truth families (known catalogue masked everywhere, evaluation inside each spatial quadrant):
sparse  = catalogue components at 1/2 and 1/4 (3 draws) and independent SGMC-minus-catalogue traces
          >10 px from the catalogue at 1/2 and 1/4 (3 draws);
full    = repo dense protocol and full SGMC-far10 (non-inferiority check only).
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
from gems import footprint, holdout, submission  # noqa: E402
from gems.thinning import dot_thin, neighbour_profile  # noqa: E402
from gems.validator import sha256_file  # noqa: E402

D_GRID = [1.0, 1.5, 2.0, 2.4, 2.8, 3.2, 3.6, 4.2, 5.0]
SPARSE = ("cat_half", "cat_quarter", "sgmc_half", "sgmc_quarter")
FULL = ("catdense", "sgmc_full")
FRACTION = {"cat_half": 0.5, "cat_quarter": 0.25, "sgmc_half": 0.5, "sgmc_quarter": 0.25}
DRAWS = 3
DEV_FOLDS = (0, 1, 2)
CONFIRM_FOLD = 3
SEED = 20261002
BOOTSTRAP = 2000
R = 3.0


def read(path):
    with rasterio.open(path) as d:
        return d.read(1)


def emission(path, fp, known):
    a = read(path)
    return np.isfinite(a) & (a > 0) & fp & ~known


def dist_to(mask):
    if not mask.any():
        return np.full(mask.shape, 1e6, np.float32)
    return distance_transform_edt(~mask).astype(np.float32)


def cell_score(dist_p, p, g, dist_g):
    n = int(g.sum())
    tp = float(np.maximum(1.0 - dist_p[g] / R, 0.0).sum())
    fp = float((1.0 - np.maximum(1.0 - dist_g[p] / R, 0.0)).sum())
    fn = n - tp
    return {
        "dti": tp / (tp + 0.2 * fp + 0.8 * fn + 1e-7),
        "coverage": tp / max(n, 1),
        "fp_per_truth": fp / max(n, 1),
        "emitted": int(p.sum()),
        "truth": n,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=ROOT / "evidence/dotting_validation.json")
    ap.add_argument("--extra", action="append", default=[], help="NAME=PATH no-thinning arm")
    ap.add_argument("--write-candidate", type=Path, default=ROOT / "out/h25-1-dotted-h19-5.tif")
    args = ap.parse_args()
    t0 = time.time()
    fp = footprint.load_footprint()
    labels = (read(ROOT / "data/bridge/labels.tif") > 0) & fp
    sgmc = (read(ROOT / "data/external/derived_sgmc_faults_100m_u8.tif") > 0) & fp
    sgmc_far10 = sgmc & ~labels & (distance_transform_edt(~labels) > 10)
    folds, names = holdout.make_quadrant_folds(fp)
    bases = {
        "h19_5": next((ROOT / "inputs").glob("*h19-5*-nan.tif")),
        "h19_4": next((ROOT / "inputs").glob("*h19-4*-nan.tif")),
        "h16_1": next((ROOT / "inputs").glob("*h16-1*-nan.tif")),
    }
    arms: dict[str, np.ndarray] = {}
    profiles, sources = {}, {}
    for key, path in bases.items():
        E = emission(path, fp, labels)
        sources[key] = {"path": str(path.relative_to(ROOT)), "sha256": sha256_file(path)}
        profiles[key] = neighbour_profile(E)
        for d in D_GRID:
            arms[f"{key}@{d:g}"] = E if d <= 1.0 else dot_thin(E, d)
        print(
            key, "thinned", {f"{d:g}": int(arms[f"{key}@{d:g}"].sum()) for d in D_GRID}, flush=True
        )
    for spec in args.extra:
        name, path = spec.split("=", 1)
        E = emission(Path(path), fp, labels)
        arms[f"retro:{name}"] = E
        sources[f"retro:{name}"] = {"path": path, "sha256": sha256_file(Path(path))}
        profiles[f"retro:{name}"] = neighbour_profile(E)
    cells: dict[str, dict[tuple, dict]] = {a: {} for a in arms}
    for f_id, fold_name in enumerate(names):
        val = (folds == f_id) & fp
        yy, xx = np.nonzero(val)
        sl = (slice(yy.min(), yy.max() + 1), slice(xx.min(), xx.max() + 1))
        v = val[sl]
        dist_p = {a: dist_to(m[sl] & v) for a, m in arms.items()}
        p_crop = {a: (m[sl] & v) for a, m in arms.items()}
        td = labels[sl] & v
        sg = sgmc_far10[sl] & v
        truths: dict[tuple, np.ndarray] = {("catdense", 0): td, ("sgmc_full", 0): sg}
        for fam in SPARSE:
            base_truth = td if fam.startswith("cat") else sg
            for k in range(DRAWS):
                seed = SEED + 1000 * f_id + 100 * SPARSE.index(fam) + k
                truths[(fam, k)] = holdout.thin_components(base_truth, FRACTION[fam], seed)
        for (fam, k), g in truths.items():
            if g.sum() < 30:
                continue
            dist_g = dist_to(g)
            for a in arms:
                cells[a][(f_id, fam, k)] = cell_score(dist_p[a], p_crop[a], g, dist_g)
        print("fold", fold_name, "done", f"{time.time() - t0:.0f}s", flush=True)

    def mean_rel(base, d, folds_, fams):
        solid, dotted = f"{base}@1", f"{base}@{d:g}"
        vals = []
        for (f_id, fam, k), s in cells[solid].items():
            if f_id in folds_ and fam in fams and (f_id, fam, k) in cells[dotted]:
                vals.append((cells[dotted][(f_id, fam, k)]["dti"] - s["dti"]) / max(s["dti"], 1e-9))
        return float(np.mean(vals)) if vals else float("nan"), len(vals)

    def mean_abs(base, d, folds_, fams):
        solid, dotted = f"{base}@1", f"{base}@{d:g}"
        vals = [
            cells[dotted][key]["dti"] - s["dti"]
            for key, s in cells[solid].items()
            if key[0] in folds_ and key[1] in fams and key in cells[dotted]
        ]
        return float(np.mean(vals)) if vals else float("nan")

    result = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "preregistration": "knowledge/04_preregistered_dotting_2026-10-02.md",
        "protocol": {
            "d_grid": D_GRID,
            "folds": names,
            "dev_folds": [names[i] for i in DEV_FOLDS],
            "confirmation_fold": names[CONFIRM_FOLD],
            "sparse_families": SPARSE,
            "full_families": FULL,
            "draws": DRAWS,
            "seed": SEED,
            "catalogue_pixels_removed_from_emission_before_thinning": True,
            "transform_reads_labels_or_scores": False,
        },
        "sources": sources,
        "neighbour_profile": profiles,
        "per_arm": {},
        "submission_slot_spent": False,
    }
    all_folds = tuple(range(4))
    for base in bases:
        rows = {}
        for d in D_GRID:
            rel_dev, n_dev = mean_rel(base, d, DEV_FOLDS, SPARSE)
            rows[f"{d:g}"] = {
                "emitted_total": int(arms[f"{base}@{d:g}"].sum()),
                "dev_sparse_mean_relative_gain": rel_dev,
                "dev_sparse_cells": n_dev,
                "confirm_sparse_mean_relative_gain": mean_rel(base, d, (CONFIRM_FOLD,), SPARSE)[0],
                "all_sparse_mean_relative_gain": mean_rel(base, d, all_folds, SPARSE)[0],
                "dev_full_mean_abs_delta": mean_abs(base, d, DEV_FOLDS, FULL),
                "all_full_mean_abs_delta": mean_abs(base, d, all_folds, FULL),
                "mean_dti_by_family": {
                    fam: float(
                        np.mean(
                            [
                                c["dti"]
                                for (f, fm, k), c in cells[f"{base}@{d:g}"].items()
                                if fm == fam
                            ]
                        )
                    )
                    for fam in SPARSE + FULL
                },
            }
        result["per_arm"][base] = rows
    # selection on the primary emission, dev folds only
    cand = [d for d in D_GRID if d > 1.0]
    best = max(
        cand,
        key=lambda d: (
            round(result["per_arm"]["h19_5"][f"{d:g}"]["dev_sparse_mean_relative_gain"], 9),
            d,
        ),
    )
    primary = f"h19_5@{best:g}"
    solid = "h19_5@1"
    wins, total = 0, 0
    block = {}
    for key, s in cells[solid].items():
        if key[1] in SPARSE and key in cells[primary]:
            rel = (cells[primary][key]["dti"] - s["dti"]) / max(s["dti"], 1e-9)
            wins += rel > 0
            total += 1
            block.setdefault((key[0], key[1]), []).append(rel)
    block_means = np.array([np.mean(v) for v in block.values()])
    rng = np.random.default_rng(SEED)
    boots = [
        float(block_means[rng.integers(0, len(block_means), len(block_means))].mean())
        for _ in range(BOOTSTRAP)
    ]
    gates = {
        "selected_d": best,
        "G1_confirm_mean_relative_gain": result["per_arm"]["h19_5"][f"{best:g}"][
            "confirm_sparse_mean_relative_gain"
        ],
        "G1_pass": result["per_arm"]["h19_5"][f"{best:g}"]["confirm_sparse_mean_relative_gain"]
        >= 0.05,
        "G2_win_rate": wins / max(total, 1),
        "G2_cells": total,
        "G2_pass": wins / max(total, 1) >= 0.75,
        "G3_bootstrap_p05_mean_relative_gain": float(np.percentile(boots, 5)),
        "G3_pass": float(np.percentile(boots, 5)) > 0,
        "G4_dev_full_mean_abs_delta": result["per_arm"]["h19_5"][f"{best:g}"][
            "dev_full_mean_abs_delta"
        ],
        "G4_pass": result["per_arm"]["h19_5"][f"{best:g}"]["dev_full_mean_abs_delta"] >= -0.010,
    }
    for rep in ("h19_4", "h16_1"):
        g_rep = result["per_arm"][rep][f"{best:g}"]["all_sparse_mean_relative_gain"]
        gates[f"G5_{rep}_mean_sparse_relative_gain"] = g_rep
    gates["G5_pass"] = all(
        gates[f"G5_{r}_mean_sparse_relative_gain"] > 0 for r in ("h19_4", "h16_1")
    )
    gates["eligible"] = all(
        gates[k] for k in ("G1_pass", "G2_pass", "G3_pass", "G4_pass", "G5_pass")
    )
    result["selection_and_gates"] = gates
    # retrodiction: owner-reported H25 (solid) -> H28 (dotted) on the same probability field
    retro = [a for a in arms if a.startswith("retro:")]
    if len(retro) == 2:
        names_r = sorted(retro)
        rr = {}
        for fam_group, fams in (("sparse", SPARSE), ("full", FULL), ("all", SPARSE + FULL)):
            out = {}
            for a in names_r:
                out[a] = float(
                    np.mean([c["dti"] for (f, fm, k), c in cells[a].items() if fm in fams])
                )
            rr[fam_group] = out
        result["retrodiction_h25_to_h28"] = {
            "mean_dti": rr,
            "note": "Owner-reported live: H25 0.1280 -> H28 0.1839 (H28 value uncorroborated in repo).",
        }
    # candidate raster (never auto-submitted)
    E = arms[f"h19_5@{best:g}"]
    args.write_candidate.parent.mkdir(exist_ok=True)
    submission.write_submission(
        E.astype(np.float32), ROOT / "data/bridge/sample_submission.tif", args.write_candidate
    )
    checks = submission.check_variants(
        args.write_candidate, ROOT / "data/bridge/sample_submission.tif"
    )
    result["candidate"] = {
        "path": str(args.write_candidate.relative_to(ROOT)),
        "sha256": sha256_file(args.write_candidate),
        "positive_pixels": int(E.sum()),
        "solid_positive_pixels": int(arms["h19_5@1"].sum()),
        "format_checks": checks,
        "recommended_to_upload": False,
        "note": "Experimental. Needs exact-file accessibility audit + promotion gate before packaging.",
    }
    result["seconds"] = time.time() - t0
    args.out.write_text(json.dumps(result, indent=2, default=float) + "\n")
    print(json.dumps({"gates": gates, "seconds": result["seconds"]}, indent=2, default=float))


if __name__ == "__main__":
    main()
