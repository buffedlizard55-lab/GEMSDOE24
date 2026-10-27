#!/usr/bin/env python3
"""Stopped H24-TMCG lane; retained only for historical code review.

The original local-download-only novelty helper omitted the registered calibration
lattice and the surface-before-placement gate. The exact final TIFF was later
measured at 100% overlap with that lattice. This lane cannot be restarted or used
to select a file; use ``scripts/audit_tmcg_integrity.py`` for read-only checks.
"""

from __future__ import annotations

import json
import os
import time

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")

import sys  # noqa: E402
from pathlib import Path  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import numpy as np  # noqa: E402
import rasterio  # noqa: E402

from gems import emission, holdout, novelty, submission, tmcg  # noqa: E402
from gems.validator import sha256_file  # noqa: E402

BUDGET_FRAC = 0.0073
SEED = 20261027
BASELINE = 0.16370


def save_json(o, p):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(o, indent=2, allow_nan=False) + "\n")


def load_ch(name, fp, stack, meta):
    idx = meta["names"].index(name)
    arr = np.full(fp.shape, np.nan, dtype=np.float32)
    arr.ravel()[np.flatnonzero(fp.ravel())] = stack[:, idx]
    return arr


def registry_overlap(dots, fp, catalogue, template):
    """Legacy incomplete proxy; never use it to certify uniqueness."""
    raise RuntimeError("Stopped: local download TIFFs are not the full pinned registry")
    out = []
    dl = ROOT / "docs/downloads"
    cand = dots.astype(bool)
    for p in sorted(dl.glob("*.tif"))[:120]:
        try:
            with rasterio.open(p) as s:
                if s.shape != dots.shape:
                    continue
                a = s.read(1)
            ref = np.isfinite(a) & (a > 0.5)
            if not ref.any():
                continue
            ov = novelty.dot_overlap(cand, ref)
            rho = novelty.correlation(
                cand[fp].astype(np.float64),
                np.clip(np.nan_to_num(a[fp], nan=0.0), 0, 1).astype(np.float64),
            )
            dup = novelty.is_duplicate(rho, ov["candidate_within_3px_of_reference"])
            if dup or (ov["candidate_within_3px_of_reference"] or 0) > 0.4:
                out.append(
                    {
                        "file": p.name,
                        "rho": rho,
                        "overlap3": ov["candidate_within_3px_of_reference"],
                        "duplicate": dup,
                    }
                )
        except Exception as e:
            out.append({"file": p.name, "error": str(e)})
    out.sort(key=lambda r: -(r.get("overlap3") or 0))
    worst = out[0] if out else {}
    drifted = any(r.get("duplicate") for r in out)
    return {
        "n_compared": min(120, len(list(dl.glob("*.tif")))),
        "drifted": drifted,
        "worst": worst,
        "flags": out[:12],
    }


def emit_folds(score, support, context):
    dots = []
    for fold in context.folds:
        eligible = support & fold["valid"] & ~fold["visible"]
        k = round(BUDGET_FRAC * int(fold["valid"].sum()))
        dots.append(emission.priority_poisson(score, eligible, k, min_dist=3))
    return dots


def main():
    raise SystemExit(
        "H24-TMCG is stopped: 100% final-dot overlap with a registered lattice; "
        "no rerun, new TIFF or competition slot is permitted. "
        "Use scripts/audit_tmcg_integrity.py for a read-only audit."
    )
    started = time.monotonic()
    template = ROOT / "data/bridge/sample_submission.tif"
    labels_path = ROOT / "data/bridge/labels.tif"
    with rasterio.open(template) as t:
        arr = t.read(1)
        fp = np.isfinite(arr)
    with rasterio.open(labels_path) as ds:
        catalogue = ds.read(1) > 0
    print(f"Footprint {int(fp.sum())} catalogue {int(catalogue.sum())}")

    prep_meta = json.loads((ROOT / "data/prepared/features.json").read_text())
    stack = np.load(ROOT / "data/prepared/features.npy", mmap_mode="r")

    needed = ["det_elev", "rtp", "det_local_relief", "geod_shearrate"]
    support = fp.copy()
    chans = {}
    for n in needed:
        a = load_ch(n, fp, stack, prep_meta)
        support &= np.isfinite(a)
        chans[n] = a

    from scipy.ndimage import binary_erosion

    support = binary_erosion(support, structure=np.ones((5, 5), bool), border_value=False)

    cg = tmcg.cross_gradient(chans["det_elev"], chans["rtp"], support)
    cg01 = tmcg.robust01(cg, support)
    relief = tmcg.robust01(chans["det_local_relief"], support)
    shear = tmcg.robust01(chans["geod_shearrate"], support)
    flat = (1.0 - relief).astype(np.float32)

    arms = {
        "A_raw": cg01,
        "B_decoupled_basin": (cg01 * (0.35 + 0.65 * flat)).astype(np.float32),
        "C_transtension": (cg01 * (0.35 + 0.65 * shear)).astype(np.float32),
    }
    for k, v in arms.items():
        v[~support] = 0.0
        arms[k] = v

    context = holdout.SegmentHoldout(fp, catalogue, buffer_px=15)
    print(f"Folds {len(context.folds)}")

    canary = context.canary(arms, seed=SEED, max_per_class=15000)
    print(f"Canary passed {canary['passed']}")
    if not canary["passed"]:
        save_json(
            {"canary": canary, "verdict": "negative", "stopped": "leakage"},
            ROOT / "evidence/tmcg_experiment_20261027.json",
        )
        raise SystemExit("Canary failed")

    experiments = []
    best = None
    for name, surface in arms.items():
        per = emit_folds(surface, support, context)
        results = context.summarize(per, ci_draws=399)
        rec = {
            "arm": name,
            "holdout_dti": results["dti"],
            "ci95": results["ci95"],
            "n_withheld_positive_pixels": results["n_withheld_positive_pixels"],
            "evaluator_version": results["evaluator_version"],
            "folds": results["folds"],
            "delta_vs_baseline_0_16370": results["dti"] - BASELINE,
        }
        print(f"ARM {name} HOLDOUT-DTI {results['dti']:.5f} CI {results['ci95']['interval']}")
        experiments.append(rec)
        if best is None or results["dti"] > best["holdout_dti"]:
            best = rec
            best_surface = surface
            best_name = name

    eligible_final = support & ~catalogue
    full_budget = round(BUDGET_FRAC * int(fp.sum()))
    final_dots = emission.priority_poisson(best_surface, eligible_final, full_budget, min_dist=3)
    n_dots = int(final_dots.sum())
    print(f"final dots {n_dots}")

    nov = registry_overlap(final_dots, fp, catalogue, template)
    print("novelty drifted", nov["drifted"], "worst", nov.get("worst"))

    content_id = submission.scored_content_id(final_dots, fp, catalogue)
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    fname = submission.make_filename(
        "gems24", f"tmcg-{best_name.lower()}", stamp, content_id, "zeros"
    )
    out_dir = ROOT / "docs/downloads"
    zeros = submission.write_submission(
        final_dots.astype(np.float32), template, out_dir / fname, outside="zero"
    )
    checks = submission.check_variants(zeros, template)

    delta = best["holdout_dti"] - BASELINE
    promote = bool(delta > 0 and not nov["drifted"] and checks.get("format_valid"))
    # Selector, not this lane, spends a weekly slot.
    ok_submit = False
    card = {
        "hypothesis": "H24-TMCG: topographic–magnetic cross-gradient |∇z × ∇rtp| targets catalogue-missing faults that warp RTP without controlling modern drainage.",
        "mechanism": "Sobel gradients of Gaussian-smoothed det_elev and rtp; magnitude of 2-D cross product; three arms (raw / basin-decoupled / shear-weighted).",
        "named_non_fault_mimic": "Irrigation canals, playa edges, and volcanic flow contacts that also misalign topography vs magnetics.",
        "holdout": {
            "label": "HOLDOUT-DTI",
            "evaluator_version": best["evaluator_version"],
            "dti": best["holdout_dti"],
            "ci95": best["ci95"],
            "n_withheld_positive_pixels": best["n_withheld_positive_pixels"],
            "winning_arm": best_name,
            "delta_vs_oof_baseline_0_16370": delta,
        },
        "experiments": experiments,
        "canary": {"passed": canary["passed"], "threshold": 0.90},
        "correlation_overlap_vs_registry": nov,
        "raster_sha256": sha256_file(zeros),
        "n_dots": n_dots,
        "validator_output": checks,
        "submission_name": fname,
        "note": "GEMS24 TMCG |∇z×∇rtp| unique; HOLDOUT only; selector spends slots",
        "verdict": "promote" if promote else "negative",
        "ok_to_download": True,
        "ok_to_submit": ok_submit,
        "experiments_run": 3,
        "elapsed_seconds": time.monotonic() - started,
        "lane": "H24-TMCG",
    }
    save_json(card, ROOT / "evidence/tmcg_run_card_20261027.json")
    save_json(
        {"canary": canary, "experiments": experiments, "novelty": nov},
        ROOT / "evidence/tmcg_experiment_20261027.json",
    )
    print(
        json.dumps(
            {"file": fname, "dti": best["holdout_dti"], "verdict": card["verdict"]}, indent=2
        )
    )


if __name__ == "__main__":
    main()
