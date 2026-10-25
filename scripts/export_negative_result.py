#!/usr/bin/env python3
"""Export the stopped, fixed negative experiment for audit, NOT a submission slot.

This is an explicit packaging deviation from the preregistration's no-package-on-
duplicate policy, to satisfy the owner's negative-artifact deliverable request.
No parameter, dot, score, threshold or registry membership is changed. A failed
novelty gate stays failed, and no second experiment is run.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems import emission, footprint, magnetic_trough, submission  # noqa: E402
from gems.validator import sha256_file  # noqa: E402


def save(obj, path):
    Path(path).write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n")


def main():
    experiment_path = ROOT / "evidence/mtr1_experiment.json"
    r = json.loads(experiment_path.read_text())
    if r.get("stopped_reason") != "duplicate-final-dots" or r.get("verdict") != "negative":
        raise SystemExit("Only the recorded stopped negative experiment can be exported here")
    for group in ("inputs", "code_sha256"):
        for name, digest in r[group].items():
            if sha256_file(ROOT / name) != digest:
                raise SystemExit(f"Experiment provenance changed: {name}")
    fp = footprint.load_footprint()
    ids = np.flatnonzero(fp)
    meta = json.loads((ROOT / "data/prepared/features.json").read_text())
    stack = np.load(ROOT / "data/prepared/features.npy", mmap_mode="r")
    rtp = np.full(fp.shape, np.nan, np.float32)
    rtp.ravel()[ids] = stack[:, meta["names"].index("rtp")]
    del stack
    with rasterio.open(ROOT / "data/external/geodawn_extensions_u8.tif") as s:
        thk = s.read(1).astype(np.float32)
    with rasterio.open(ROOT / "data/bridge/labels.tif") as s:
        catalogue = (s.read(1) > 0) & fp
    surfaces, support = magnetic_trough.build_surfaces(rtp, thk, fp)
    cached = np.load(ROOT / "data/prepared/mtr1/candidate.npy", mmap_mode="r")
    if not np.array_equal(surfaces["candidate"], cached):
        raise SystemExit("Reconstructed fixed candidate differs from the tested surface")
    final = emission.priority_poisson(
        surfaces["candidate"], support & ~catalogue, round(0.0073 * fp.sum()), min_dist=3
    )
    content = submission.scored_content_id(final, fp, catalogue)
    name = submission.make_filename(
        "gems24", "mtr1-negative-paired-trough", "20261025", content, "zeros"
    )
    download = ROOT / "docs/downloads"
    template = ROOT / "data/bridge/sample_submission.tif"
    zero = submission.write_submission(final, template, download / name, outside="zero")
    nan_name = name.replace("-zeros.tif", "-nan.tif")
    nan = submission.write_submission(final, template, download / nan_name, outside="nan")
    checks = {
        "zero_outside": submission.check_variants(zero, template),
        "nan_outside": submission.check_variants(nan, template),
    }
    if not all(x["format_valid"] for x in checks.values()):
        raise SystemExit("Negative artifact failed file-format validation")
    registry = json.loads((ROOT / "registry/priority_rasters.json").read_text())
    independent_content = all(
        hashlib_footprint(final, fp) != row["footprint_sha256"]
        for row in registry["unique_rasters"]
    )
    if not independent_content:
        raise SystemExit("Unexpected identical old raster: do not package a reference copy")
    note = f"GEMS24 MTR1 | paired RTP trough + Th/K | NEGATIVE: lattice overlap veto; DO NOT SUBMIT | id {content}"
    if len(note) > 140:
        raise AssertionError("Note too long")
    checks_file, note_file = f"checks-{name[:-4]}.json", f"note-{name[:-4]}.txt"
    save(checks, download / checks_file)
    (download / note_file).write_text(note + "\n")
    # Audit geometry of the vetoing lattice; it remains IN the decision registry.
    from scipy.ndimage import distance_transform_edt

    veto = next(x for x in registry["unique_rasters"] if "lattice-s5" in x["file"])
    with rasterio.open(ROOT / veto["cache_path"]) as s:
        lattice = (s.read(1) > 0) & fp
    covered = distance_transform_edt(~lattice) <= 3
    scope = {
        "registry_id": veto["id"],
        "lattice_file": veto["file"],
        "footprint_fraction_within_3px_of_lattice": float(covered[fp].mean()),
        "supported_candidate_domain_fraction_within_3px": float(covered[support].mean()),
        "interpretation": "Spacing-5 lattice covers the supported domain at radius 3: overlap alone cannot distinguish ANY detector in that domain. Gate nevertheless remains failed.",
        "no_comparator_removed": True,
    }
    reasons = [
        "Duplicate-overlap stop: every candidate dot is <=3 px from the registered spacing-5 calibration lattice",
        "No independently reconstructed comparable current-best OOF baseline",
        "No explicit assigned lane paragraph in the brief; provisional lane only",
        "Separate weekly-slot selector not run",
    ]
    card = {
        "hypothesis": r["hypothesis"],
        "mechanism": "Paired signed RTP trough + tangent persistence, weighted by local contractor Th/K depletion; no terrain, label-derived feature or old prediction input",
        "non_fault_mimic": "Magnetite-poor alluvial paleochannel with K-rich detritus",
        "holdout": r["results"]["candidate"],
        "magnetic_only_ablation": r["results"]["magnetic_trough"],
        "paired_gain_dti": r["paired_gain_vs_magnetic_only"],
        "correlation_overlap_vs_registry": {
            "unique_registry_rasters": len(registry["unique_rasters"]),
            "surface_max_abs_rank_correlation": r["surface_novelty"]["max_abs_rank_correlation"],
            "final_max_abs_rank_correlation": r["final_novelty"]["max_abs_rank_correlation"],
            "final_max_overlap_within_3px": r["final_novelty"]["max_dot_overlap"],
            "passed": False,
            "scope": registry["scope"],
            "raw_rank_scope": "exact over all footprint pixels",
            "kernel_sensitivity_sample_pixels": 200000,
            "veto_geometry": scope,
        },
        "raster_sha256": sha256_file(zero),
        "validator_output": checks["zero_outside"],
        "submission_name": name,
        "nan_outside_artifact": nan_name,
        "pixel_count": int(final.sum()),
        "note": note,
        "verdict": "negative",
        "content_identical_to_registry": False,
        "independently_computed": True,
        "lane_uniqueness_gate_passed": False,
        "ok_to_download": True,
        "ok_to_submit": False,
        "reasons": reasons,
        "organizer_confirmed_score": None,
        "experiments_run": 1,
        "submission_slots_used": 0,
        "packaging_deviation": "After duplicate stop, exported the unchanged already-tested negative artifact solely for audit. No retuning, comparator removal, new experiment or promotion.",
    }
    save(card, ROOT / "evidence/mtr1_run_card.json")
    save(card, ROOT / "docs/data/mtr1_run_card.json")
    save(scope, ROOT / "evidence/lattice_overlap_irregularity.json")
    d = {
        "file": name,
        "nan_file": nan_name,
        "sha256": sha256_file(zero),
        "content_id": content,
        "pixel_count": int(final.sum()),
        "note": note,
        "note_file": note_file,
        "checks_file": checks_file,
        "generation": "independent-mtr1-v1",
        "format_valid": True,
        "ok_to_download": True,
        "ok_to_submit": False,
        "slot_recommendation": "not_recommended",
        "verdict": "negative",
        "live_dti": None,
        "run_card": "mtr1_run_card.json",
        "independently_computed": True,
        "lane_uniqueness_gate_passed": False,
    }
    old = ROOT / "docs/data/download.json"
    if not (ROOT / "evidence/archive/download_20261002.json").exists():
        (ROOT / "evidence/archive/download_20261002.json").write_text(old.read_text())
    save(d, old)
    save(d, ROOT / "docs/data/independent_download.json")
    print(
        json.dumps(
            {
                "file": name,
                "sha256": card["raster_sha256"],
                "pixels": int(final.sum()),
                "note_length": len(note),
                "format_valid": True,
                "ok_to_submit": False,
                "verdict": "negative",
                "veto_geometry": scope,
            },
            indent=2,
        )
    )


def hashlib_footprint(a, fp):
    import hashlib

    return hashlib.sha256(np.asarray(a[fp], dtype="<f4").tobytes()).hexdigest()


if __name__ == "__main__":
    main()
