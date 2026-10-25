#!/usr/bin/env python3
"""One preregistered ASPC experiment; fails closed, never selects/uploads a slot."""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Avoid thread oversubscription on the small research worker.
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import numpy as np  # noqa: E402
import rasterio  # noqa: E402
from scipy.stats import rankdata  # noqa: E402
from sklearn.metrics import roc_auc_score  # noqa: E402

from gems import aspc, holdout, novelty, submission  # noqa: E402
from gems.validator import sha256_file  # noqa: E402

BUDGET = 37654
REPORT = ROOT / "evidence/aspc_run_20261025.json"
CARD = ROOT / "evidence/aspc_run_card_20261025.json"
TEMPLATE = ROOT / "data/bridge/sample_submission.tif"


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")


def main():
    start = time.monotonic()
    if REPORT.exists():
        raise SystemExit(
            "Experiment already recorded. No implicit rerun/tuning on confirmation folds."
        )
    with rasterio.open(TEMPLATE) as ds:
        fp = np.isfinite(ds.read(1))
        grid = (ds.shape, ds.crs, ds.transform)
    manifest = json.loads((ROOT / "data/manifest.json").read_text())["files"]
    hashes = {}
    for rel in [
        "bridge/sample_submission.tif",
        "bridge/labels.tif",
        "external/lidar_scarp_features_u8.tif",
    ]:
        p = ROOT / "data" / rel
        digest = sha256_file(p)
        if digest != manifest[rel]["sha256"]:
            raise ValueError(f"Input checksum mismatch: {rel}")
        hashes[rel] = digest
    with rasterio.open(ROOT / "data/bridge/labels.tif") as ds:
        if (ds.shape, ds.crs, ds.transform) != grid:
            raise ValueError("Label grid mismatch")
        labels = ds.read(1) > 0
    metadata = json.loads((ROOT / "data/external/lidar_scarp_features.json").read_text())
    with rasterio.open(ROOT / "data/external/lidar_scarp_features_u8.tif") as ds:
        if (ds.shape, ds.crs, ds.transform) != grid or list(ds.descriptions) != metadata["bands"]:
            raise ValueError("Cached descriptor grid or band semantics mismatch")
        bands = {}
        for name, spec in aspc.BANDS.items():
            if metadata["quantisation"][name] != list(spec):
                raise ValueError(f"Quantization mismatch: {name}")
            bands[name] = ds.read(metadata["bands"].index(name) + 1)
    surface, canaries, support, control = aspc.factors(bands, fp)
    del bands
    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "experiment_count": 1,
        "experiment_limit": 3,
        "runtime_limit_seconds": 7200,
        "preregistration": "knowledge/09_preregistered_ASPC_2026-10-25.md",
        "preregistration_sha256": sha256_file(
            ROOT / "knowledge/09_preregistered_ASPC_2026-10-25.md"
        ),
        "lane": "ASPC-provisional-unassigned",
        "input_sha256": hashes,
        "evaluator_version": holdout.SEGMENT_EVALUATOR_VERSION,
        "surface_sha256": __import__("hashlib").sha256(surface.astype("<f4").tobytes()).hexdigest(),
        "support_pixels": int(support.sum()),
        "surface_reads_catalogue": False,
        "registry_scope": json.loads((ROOT / "registry/peer_rasters_20261025.json").read_text())[
            "scope"
        ],
        "score_provenance": "HOLDOUT-DTI only. No organizer receipt and no projected leaderboard score.",
        "canaries": [],
        "surface_registry": [],
        "final_registry": [],
        "folds": [],
        "submission_authorized": False,
        "slot_spent": False,
        "verdict": "negative",
        "blockers": [
            "No assigned parallel-run method lane",
            "Current-best comparable OOF reconstruction unavailable",
            "Exact-file nuisance audit not run; negative screening candidate",
            "Weekly selector authorization and current portal cap unverified",
        ],
    }
    card = {
        "hypothesis": "ASPC antislope paired-curvature scarp (provisional research lane)",
        "mechanism": "Uphill-facing fraction * paired-curvature balance * channel-bank veto * step response * sqrt(coherence)",
        "named_non_fault_mimic": "rotational landslide headscarps and terrace risers",
        "holdout_dti": None,
        "correlation_overlap_vs_registry": None,
        "raster_sha256": None,
        "validator_output": None,
        "submission_name": None,
        "note": "ASPC antislope/curvature with channel veto; research-only. No organizer score; do not submit.",
        "verdict": "negative",
        "submission_authorized": False,
    }

    def finish(reason=None):
        if reason:
            report["blockers"].append(reason)
        report["elapsed_seconds"] = round(time.monotonic() - start, 3)
        card["blockers"] = report["blockers"]
        write_json(REPORT, report)
        write_json(CARD, card)
        print(json.dumps(card, indent=2, allow_nan=False))

    def budget_check():
        if time.monotonic() - start > 7200:
            finish("Runtime budget exceeded; stopped without promotion")
            raise SystemExit(1)

    refs = json.loads((ROOT / "registry/peer_rasters_20261025.json").read_text())["entries"]
    blobs = {}
    report["excluded_non_submission_references"] = []
    for row in refs:
        if row.get("role") == "format_demo_not_submission":
            report["excluded_non_submission_references"].append(row)
            continue
        blobs.setdefault(row["blob"], row)

    # Every registry raster is verified before trusting surface/final comparisons.
    def reference(row):
        p = ROOT / row["cache_path"]
        if sha256_file(p) != row["sha256"]:
            raise ValueError("Registry file checksum mismatch")
        with rasterio.open(p) as ds:
            if (ds.shape, ds.crs, ds.transform) != grid or ds.count != 1:
                raise ValueError(f"Registry grid/count mismatch: {row['url']}")
            a = ds.read(1)
        if not np.isfinite(a[fp]).all() or np.any((a[fp] < 0) | (a[fp] > 1)):
            raise ValueError("Registry has invalid inside-footprint values; comparison incomplete")
        return a

    ranks = rankdata(surface[fp])
    for row in blobs.values():
        a = reference(row)
        rho = novelty.rank_correlation(ranks, a[fp])
        report["surface_registry"].append(
            {
                "blob": row["blob"],
                "url": row["url"],
                "rho": rho,
                "status": "constant reference" if rho is None else "computed",
            }
        )
        budget_check()
        if novelty.is_duplicate(rho):
            finish("Duplicate surface exceeds rank-correlation threshold; stopped before placement")
            return
    del ranks, a
    print("Surface uniqueness screen passed", flush=True)

    # Leakage screen happens before any trusting of results or placement.
    for fold in holdout.segment_folds(fp, labels):
        active = fold["test"] & ~fold["visible"]
        y = fold["hidden"][active]
        if not y.any() or y.all():
            finish("Single-class holdout: leakage screen unavailable")
            return
        for name, a in canaries.items():
            auc = float(roc_auc_score(y, a[active]))
            report["canaries"].append(
                {
                    "fold": fold["name"],
                    "feature": name,
                    "evidence_class": "DIAGNOSTIC-AUC",
                    "auc": auc,
                    "n_withheld_positives": int(y.sum()),
                    "flagged": auc > 0.90 or auc < 0.10,
                }
            )
            if auc > 0.90 or auc < 0.10:
                finish(f"Leakage canary quarantined feature {name} in {fold['name']}")
                return
        budget_check()
    del canaries
    print("All input/factor canaries passed", flush=True)

    # Final all-visible-catalogue file is NOT used to score held-out positives.
    dots = aspc.place_dots(surface, support & ~labels, BUDGET)
    final_values = dots[fp].astype(np.float32)
    ranks = rankdata(final_values)
    for row in blobs.values():
        a = reference(row)
        rho = novelty.rank_correlation(ranks, a[fp])
        overlap = novelty.dot_overlap(dots, fp & (a > 0))
        report["final_registry"].append(
            {"blob": row["blob"], "url": row["url"], "rho": rho, **overlap}
        )
        budget_check()
        if novelty.is_duplicate(rho, overlap["candidate_within_3px_of_reference"]):
            card["correlation_overlap_vs_registry"] = report["final_registry"][-1]
            finish(
                "Duplicate final dots exceed correlation/overlap threshold; stopped, no submission artifact"
            )
            return
    del ranks, final_values, a
    card["correlation_overlap_vs_registry"] = {
        "references": len(refs),
        "unique_blobs": len(blobs),
        "all_full_footprint": True,
        "maximum_surface_rho": max(
            r["rho"] for r in report["surface_registry"] if r["rho"] is not None
        ),
        "maximum_dot_rho": max(r["rho"] for r in report["final_registry"] if r["rho"] is not None),
        "maximum_candidate_within_3px": max(
            r["candidate_within_3px_of_reference"] for r in report["final_registry"]
        ),
        "distinct_in_reviewed_registry": True,
        "global_uniqueness_proven": False,
    }
    print("Final dot uniqueness screen passed", flush=True)

    candidate_tiles, control_tiles = [], []
    global_tile_grid = None
    for fold in holdout.segment_folds(fp, labels):
        budget = int(round(BUDGET * fold["test"].sum() / fp.sum()))
        eligible = support & fold["test"] & ~fold["visible"]
        pred = aspc.place_dots(surface, eligible, budget)
        baseline = aspc.place_dots(control, eligible, budget)
        rows, metric = holdout.spatial_components(
            pred, fold["hidden"], fold["test"], fold["visible"]
        )
        base_rows, base_metric = holdout.spatial_components(
            baseline, fold["hidden"], fold["test"], fold["visible"]
        )
        # Include all footprint-intersecting tiles, even zero-contribution tiles.
        tile_grid = np.zeros(len(rows), bool)
        yy, xx = np.nonzero(fold["test"])
        ncols = (fp.shape[1] + 199) // 200
        tile_grid[(yy // 200) * ncols + xx // 200] = True
        global_tile_grid = tile_grid if global_tile_grid is None else global_tile_grid | tile_grid
        candidate_tiles.append(rows)
        control_tiles.append(base_rows)
        counts = {k: v for k, v in fold.items() if not isinstance(v, np.ndarray)}
        report["folds"].append(
            {
                **counts,
                "training_pixels": int(fold["training"].sum()),
                "visible_fault_pixels": int(fold["visible"].sum()),
                "emitted_dots": int(pred.sum()),
                "candidate_components": metric,
                "control_components": base_metric,
            }
        )
        print(f"Completed fold {fold['name']}", flush=True)
        budget_check()
    # A tile crossing a quadrant boundary is ONE spatial cluster, not two.
    rows = np.sum(candidate_tiles, axis=0)[global_tile_grid]
    base_rows = np.sum(control_tiles, axis=0)[global_tile_grid]
    n_positive = sum(x["n_withheld_positives"] for x in report["folds"])
    result = {
        "evidence_class": "HOLDOUT-DTI",
        "evaluator_version": holdout.SEGMENT_EVALUATOR_VERSION,
        "n_withheld_positives": n_positive,
        "value": holdout.pooled_dti(rows),
        "ci95": holdout.pooled_bootstrap(rows),
        "control_value": holdout.pooled_dti(base_rows),
        "control_ci95": holdout.pooled_bootstrap(base_rows),
        "paired_delta": holdout.pooled_dti(rows) - holdout.pooled_dti(base_rows),
        "paired_delta_ci95": holdout.pooled_bootstrap(rows, paired=base_rows),
        "ci_method": "20 km spatial tile cluster bootstrap, 1000 resamples; conditional on frozen quadrants/catalogue",
        "ci_limitations": "Not hidden-set uncertainty; quadrant portions of the same global tile are aggregated",
        "cluster_count": len(rows),
        "current_best_oof_comparison": None,
        "alpha": 0.2,
        "beta": 0.8,
        "triangular_kernel_m": 300,
    }
    report["holdout"] = result
    card["holdout_dti"] = result
    report["beats_fixed_control"] = result["paired_delta_ci95"][0] > 0
    cid = submission.scored_content_id(dots.astype(np.float32), fp, labels)
    name = f"gems24-aspc-20261025-{cid}-RESEARCH-NOT-SUBMISSION-zeros.tif"
    dest = ROOT / "docs/downloads" / name
    submission.write_submission(dots.astype(np.float32), TEMPLATE, dest, outside="zero")
    checks = submission.check_variants(dest, TEMPLATE)
    if not checks["format_valid"]:
        raise AssertionError("Final exact-file format check failed")
    if checks["in_footprint_positive_pixels"] != BUDGET:
        raise AssertionError("Emitted dot count changed during writing")
    write_json(dest.with_suffix(".checks.json"), checks)
    note = card["note"]
    if len(note) > 140:
        raise AssertionError("Note exceeds preregistered 140-character cap")
    dest.with_suffix(".note.txt").write_text(note + "\n")
    card.update(
        {"raster_sha256": checks["sha256"], "validator_output": checks, "submission_name": name}
    )
    report["artifact"] = {
        "file": name,
        "sha256": checks["sha256"],
        "note": note,
        "format_valid": True,
        "research_only": True,
        "submission_authorized": False,
        "content_id": cid,
    }
    finish("Promotion not established; research-only file, do not upload")


if __name__ == "__main__":
    main()
