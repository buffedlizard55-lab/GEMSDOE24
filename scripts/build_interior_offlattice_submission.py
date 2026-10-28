#!/usr/bin/env python3
"""
Generate a UNIQUE, research-only GEMS submission: geothermal-prioritized
interior off-lattice binary dots.

Design (deterministic; no ML training lane required):
  * Lattice holes: footprint cells whose nearest spacing-5 lattice dot is
    strictly > 3 px away (the "interior off-lattice" support, 6,649 cells).
    Every dot lives in a lattice hole, so directed overlap vs the retained
    spacing-5 lattice is exactly 0.0 (<= 0.70 Rule-1 ceiling).
  * Geothermal favorability on the interior support: potassium anomaly
    (GeoDAWN K), low Th/K argillic overprint (GeoDAWN extensions ThK),
    vent/spring proximity (triangular kernel credit, R=300 m), and LiDAR
    short-wavelength scarp flexure (ex_mean). Multiplicative score, in [0,1].
  * Dots = top-N interior cells by favorability, binary {0,1} surface.
  * Segment holdout (gems-segment-pooled-v1, buffer 30 px) against the
    restored bridge labels (60,988 positives) gives HOLDOUT-DTI + 95% CI.
  * Strict whole-array [0,1] finite GeoTIFF (zeros outside footprint) to avoid
    the portal "Predicted values must be in range [0, 1]" rejection mode.

This is a RESEARCH construction, not an assigned parallel-run method lane.
HOLDOUT-DTI is an internal validation measurement, not an organizer score or
a leaderboard projection. SUBMIT: NO pending a coordinator-assigned lane,
complete selector/quota evidence, and an artifact-linked organizer receipt.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems import emission, holdout, novelty, submission  # noqa: E402
from gems.metric import ALPHA, BETA, RADIUS_PX  # noqa: E402
from gems.validator import sha256_file  # noqa: E402

TEMPLATE = ROOT / "data/bridge/sample_submission.tif"
LABELS = ROOT / "data/bridge/labels.tif"
LATTICE = ROOT / "inputs/calibration/13gems_20261001_r13-lattice-s5_v2_nan-outside.tif"
LIDAR = ROOT / "data/external/lidar_scarp_features_u8.tif"
RAD = ROOT / "data/external/geodawn_rad_u8.tif"
EXT = ROOT / "data/external/geodawn_extensions_u8.tif"
VENTS_CSV = ROOT / "data/external/gdr_volcanic_vents_in_footprint.csv"
SPRINGS_CSV = ROOT / "data/external/gdr_wellspring_in_footprint.csv"

DOWNLOADS = ROOT / "docs/downloads"
DATA_OUT = ROOT / "docs/data"
EVIDENCE = ROOT / "evidence"

SEED = 20261028
BUFFER_PX = 30  # 3 km segment buffer
MAX_DOTS = 6649  # all interior off-lattice cells
NOTE_PREFIX = "24GEMS interior-offlattice geothermal dots"


def save_json(obj, path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n")


def read_u8_band(path, band):
    with rasterio.open(path) as ds:
        return ds.read(band).astype(np.float32)


def norm01(a, valid_mask):
    v = np.where(valid_mask & np.isfinite(a), a, np.nan)
    if v.size and np.isfinite(v).any():
        lo, hi = np.nanpercentile(v, 2), np.nanpercentile(v, 98)
        if np.isfinite(lo) and np.isfinite(hi) and hi > lo:
            out = np.clip((a - lo) / (hi - lo), 0.0, 1.0)
        else:
            out = np.zeros_like(a)
    else:
        out = np.zeros_like(a)
    out[~valid_mask] = 0.0
    return out.astype(np.float32)


def thermal_surface(fp):
    mask = np.zeros(fp.shape, bool)
    n_vents = 0
    with open(VENTS_CSV, newline="") as f:
        for row in csv.DictReader(f):
            r = int(float(row["row"]))
            c = int(float(row["col"]))
            if 0 <= r < fp.shape[0] and 0 <= c < fp.shape[1] and fp[r, c]:
                mask[r, c] = True
                n_vents += 1
    n_springs = 0
    with open(SPRINGS_CSV, newline="") as f:
        for row in csv.DictReader(f):
            r = int(float(row["row"]))
            c = int(float(row["col"]))
            gq = row.get("geothermquartz_c", "")
            if gq in (None, "", "nan", "NaN"):
                continue
            if 0 <= r < fp.shape[0] and 0 <= c < fp.shape[1] and fp[r, c]:
                mask[r, c] = True
                n_springs += 1
    credit = emission.kernel_credit(mask, radius=3.0)
    valid = fp & (credit > 0)
    thermal = norm01(credit, valid)
    return thermal, int(mask.sum()), n_vents, n_springs


def build_interior_mask(fp, lattice_dots):
    """Interior footprint cells strictly > 3 px from any lattice dot.

    Computes distance to the nearest lattice dot *within the footprint only*,
    so the polygon boundary is not mistaken for a nearby lattice vertex.
    """
    ref = lattice_dots & fp
    dist = distance_transform_edt(~ref)
    return fp & (dist > 3.0), dist


def build_favorability(fp, interior):
    lidar_valid = read_u8_band(LIDAR, 12) > 0
    ex_mean = read_u8_band(LIDAR, 2)  # short-wavelength steepness / flexure
    k_band = read_u8_band(RAD, 1)  # potassium alteration halo
    thk_band = read_u8_band(EXT, 1)  # Th/K; low = argillic overprint
    for name, arr in (("ex_mean", ex_mean), ("k_band", k_band), ("thk_band", thk_band)):
        if arr.shape != fp.shape:
            raise SystemExit(f"{name} shape {arr.shape} != template {fp.shape}")
    thermal, n_thermal_px, n_vents, n_springs = thermal_surface(fp)
    curvature = norm01(ex_mean, lidar_valid)
    k_anom = norm01(k_band, lidar_valid & (k_band > 0))
    alteration = 1.0 - norm01(thk_band, lidar_valid & (thk_band > 0))
    favor = curvature * k_anom * alteration * (1.0 + thermal)
    favor = np.where(interior, favor, 0.0).astype(np.float32)
    return favor, dict(
        n_thermal_px=n_thermal_px,
        n_vents=n_vents,
        n_springs=n_springs,
    )


def choose_dots(favor, interior, max_dots):
    ys, xs = np.nonzero(interior & (favor > 0))
    scores = favor[ys, xs]
    order = np.argsort(-scores, kind="stable")
    n = min(max_dots, len(order))
    sel = order[:n]
    dots = np.zeros(interior.shape, bool)
    dots[ys[sel], xs[sel]] = True
    return dots, int(n), int(len(ys)), float(scores[sel].min()) if n else 0.0


def run_holdout(surface, fp, labels):
    """Score a fixed binary surface under the segment hide-and-recover protocol.

    The same global surface is scored once per held-out fold; each fold scores
    predictions in its valid quadrant against withheld truth there, masking
    known/visible faults pixel-exactly from the false-positive domain.
    Catalogue-dependent inputs are never used to build ``surface``.
    """
    ctx = holdout.SegmentHoldout(fp, labels, buffer_px=BUFFER_PX)
    summary = ctx.summarize([surface] * len(ctx.folds), ci_draws=1999)
    folds = []
    for row in summary["folds"]:
        folds.append(
            {
                "fold": row["fold"],
                "tp_w": float(row["TP_w"]),
                "fp_w": float(row["FP_w"]),
                "fn_w": float(row["FN_w"]),
                "n_truth": int(row["n_truth"]),
                "n_emitted": int(row["n_emitted"]),
                "dti": float(row["dti"]),
                "coverage": float(row["coverage"]),
            }
        )
    return ctx, folds, summary


def pooled_ci(folds, resamples=1999, seed=SEED):
    rows = np.asarray([[f["tp_w"], f["fp_w"], f["fn_w"]] for f in folds], dtype=np.float64)
    pooled = holdout.pooled_dti(rows)
    rng = np.random.default_rng(seed)
    scores = []
    for _ in range(resamples):
        ids = rng.integers(0, len(rows), len(rows))
        scores.append(holdout.pooled_dti(rows[ids]))
    lo, hi = float(np.quantile(scores, 0.025)), float(np.quantile(scores, 0.975))
    return pooled, [lo, hi]


def novelty_checks(surface, dots, fp):
    """Novelty vs the retained lattice (cached) and local dots."""
    with rasterio.open(LATTICE) as ds:
        lat = (ds.read(1) > 0) & fp
    lat_dist = distance_transform_edt(~(lat))
    lattice_overlap = float(np.mean(lat_dist[dots & fp] <= 3.0)) if (dots & fp).any() else 0.0
    surface_ranks = None
    from scipy.stats import rankdata

    surface_ranks = rankdata(surface[fp])
    with rasterio.open(LATTICE) as ds:
        lat_a = ds.read(1)
    raw_rho = novelty.rank_correlation(surface_ranks, lat_a[fp])
    return {
        "lattice_dots": int(lat.sum()),
        "lattice_overlap_within_3px": lattice_overlap,
        "lattice_duplicate_stop": lattice_overlap > 0.70,
        "surface_abs_spearman_vs_lattice": None if raw_rho is None else abs(float(raw_rho)),
        "surface_spearman_defined": raw_rho is not None,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--max-dots", type=int, default=MAX_DOTS)
    ap.add_argument(
        "--emit",
        action="store_true",
        help="write TIFF/ZIP/artifacts (default: dry-run validation only)",
    )
    args = ap.parse_args()

    with rasterio.open(TEMPLATE) as ds:
        fp = np.isfinite(ds.read(1))
    with rasterio.open(LATTICE) as ds:
        lattice_dots = ds.read(1) > 0
    with rasterio.open(LABELS) as ds:
        labels_raw = ds.read(1)
    # Restrict catalogue truth to the finite footprint; outside -> 0.
    labels = np.where(fp, labels_raw, 0).astype(np.float32)
    if not np.isin(labels[fp], (0, 1)).all() or not np.isfinite(labels[fp]).all():
        raise ValueError("labels.tif must be finite binary inside the footprint")

    interior, lattice_distance = build_interior_mask(fp, lattice_dots)
    n_interior = int(interior.sum())
    print(f"Interior off-lattice cells (>3px from lattice): {n_interior:,}")

    favor, thermal_info = build_favorability(fp, interior)
    dots, n_dots, n_favor_positive, min_score = choose_dots(favor, interior, args.max_dots)
    print(f"Favorability-positive interior cells: {n_favor_positive:,}; dots emitted: {n_dots:,}")

    surface = np.zeros(fp.shape, dtype=np.float32)
    surface[dots] = 1.0

    # ---- Holdout ----
    ctx, folds, summary = run_holdout(surface, fp, labels)
    pooled = float(summary["dti"])
    ci = [float(summary["ci95"]["interval"][0]), float(summary["ci95"]["interval"][1])]
    n_withheld = int(summary["n_withheld_positive_pixels"])
    print(
        f"Holdout: pooled DTI={pooled:.6f} 95% CI=[{ci[0]:.6f},{ci[1]:.6f}] "
        f"withheld={n_withheld:,} emitted={n_dots:,}"
    )

    # ---- Novelty vs lattice ----
    nov = novelty_checks(surface, dots, fp)
    print(
        f"Novelty vs lattice: overlap={nov['lattice_overlap_within_3px']:.6f} "
        f"stop={nov['lattice_duplicate_stop']}"
    )

    # ---- Format validation (strict whole-array [0,1]) ----
    content_id = hashlib.sha256(np.asarray(surface[fp], dtype="<f4").tobytes()).hexdigest()[:12]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    base = f"24gems-interior-offlattice-geothermal-{stamp}-{content_id}"
    tif_path = DOWNLOADS / f"{base}-zeros.tif"
    nan_path = DOWNLOADS / f"{base}-nan.tif"
    zip_path = DOWNLOADS / f"{base}-zeros.zip"
    checks_path = DOWNLOADS / f"{base}-checks.json"
    note_path = DOWNLOADS / f"{base}-note.txt"
    card_path = EVIDENCE / f"{base}_run_card.json"
    note = (
        f"24GEMS interior-offlattice geothermal dots | HOLDOUT-DTI {pooled:.4f} "
        f"| id {content_id} | research; DO NOT SUBMIT"
    )
    if len(note) > 140:
        note = note[:137] + "..."

    result = {
        "schema": "interior-offlattice-submission-v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "hypothesis": "Geothermal feeder faults missed by the catalogue lie in spacing-5 lattice "
        "3-px coverage holes; prioritizing those holes by public geothermal favorability "
        "recovers unmapped faults without touching any catalogue-adjacent dot.",
        "mechanism": "Binary dots at interior cells >3 px from the retained lattice, ranked by "
        "potassium anomaly, low Th/K, vent/spring proximity and LiDAR flexure.",
        "named_non_fault_mimic": "Erosional scarps, paleo-shoreline risers, lithologic contacts, "
        "dike edges, survey seams.",
        "interior_cells": n_interior,
        "dots_emitted": n_dots,
        "favorability_positive_cells": n_favor_positive,
        "min_dot_favorability": min_score,
        "thermal": thermal_info,
        "holdout": {
            "label": "HOLDOUT-DTI",
            "evaluator_version": summary.get("evaluator_version"),
            "n_withheld_positive_pixels": int(n_withheld),
            "n_unique_withheld_components": int(summary.get("n_unique_withheld_components", 0)),
            "pooled_dti": float(pooled),
            "ci95": ci,
            "folds": folds,
            "protocol": summary.get("protocol"),
            "alpha": ALPHA,
            "beta": BETA,
            "radius_m": int(RADIUS_PX * 100),
            "buffer_px": BUFFER_PX,
        },
        "novelty_vs_lattice": nov,
        "raster_sha256": None,
        "submission_name": base,
        "note": note,
        "note_chars": len(note),
        "verdict": "negative",
        "ok_to_download": True,
        "ok_to_submit": False,
        "submission_authorized": False,
        "slots_used": 0,
        "experiments_run": 1,
        "organizer_confirmed_score": None,
        "leaderboard_estimate": None,
        "score_status": "NOT ESTIMABLE; internal holdout only, not an organizer score",
    }

    if args.emit:
        # Write strict whole-array [0,1] zeros-outside GeoTIFF.
        submission.write_submission(surface, TEMPLATE, tif_path, outside="zero")
        submission.zip_single(tif_path, zip_path)
        # NaN-outside compatibility twin (never the recommended upload artifact).
        submission.write_submission(surface, TEMPLATE, nan_path, outside="nan")
        checks = submission.check_variants(tif_path, TEMPLATE)
        checks["exterior_encoding"] = "zero_outside_whole_array_finite"
        save_json(checks, checks_path)
        note_path.write_text(note + "\n")
        result["raster_sha256"] = sha256_file(tif_path)
        result["validator_output"] = checks
        result["note_file"] = note_path.name
        result["zip_sha256"] = sha256_file(zip_path)
        save_json(result, card_path)
        save_json(result, DATA_OUT / f"{base}_run_card.json")
        save_json(
            {
                "file": f"{base}-zeros.tif",
                "sha256": result["raster_sha256"],
                "bytes": tif_path.stat().st_size,
                "verdict": result["verdict"],
                "ok_to_submit": result["ok_to_submit"],
            },
            DATA_OUT / f"{base}_download.json",
        )
        print(f"Wrote {tif_path} ({tif_path.stat().st_size / 1e6:.1f} MB)")
        print(f"SHA-256: {result['raster_sha256']}")
    else:
        print("DRY-RUN: pass --emit to write TIFF/ZIP/artifacts.")

    save_json(result, card_path if not args.emit else card_path)
    save_json(result, EVIDENCE / f"{base}_dryrun.json" if not args.emit else card_path)
    print(
        json.dumps(
            {
                k: result[k]
                for k in (
                    "verdict",
                    "ok_to_submit",
                    "pooled_dti",
                    "lattice_overlap_within_3px",
                    "raster_sha256",
                )
                if k in result
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
