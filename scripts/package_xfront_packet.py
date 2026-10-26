#!/usr/bin/env python3
"""Package the frozen H24-XFRONT artifacts for the Pages site (no science rerun).

Reopens the exact emitted GeoTIFFs and ZIP with the shared validator, writes the
short-note text file, the selector receipt, a downsampled preview and the
``docs/data/xfront_download.json`` packet the site renderer validates against.
Nothing here can change a gate decision, the raster bytes or the verdict.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import rasterio  # noqa: E402
import run_dprf1_lane as dprf  # noqa: E402

from gems import footprint as footprint_mod  # noqa: E402
from gems import selector, submission  # noqa: E402
from gems.validator import sha256_file  # noqa: E402

CARD = ROOT / "evidence" / "xfront_run_card_20261026.json"
TEMPLATE = ROOT / "data" / "bridge" / "sample_submission.tif"
DOWNLOADS = ROOT / "docs" / "downloads"


def main() -> None:
    card = json.loads(CARD.read_text())
    name = card["submission_name"]
    nan_name = card["nan_outside_artifact"]
    zip_name = card["zip_artifact"]
    zeros = DOWNLOADS / name
    nan_tif = DOWNLOADS / nan_name
    zip_path = DOWNLOADS / zip_name
    if sha256_file(zeros) != card["raster_sha256"]:
        raise SystemExit("XFRONT zeros artifact does not match its run-card hash")
    if sha256_file(nan_tif) != card["nan_outside_sha256"]:
        raise SystemExit("XFRONT NaN-outside twin does not match its run-card hash")
    if sha256_file(zip_path) != card["zip_sha256"]:
        raise SystemExit("XFRONT ZIP does not match its run-card hash")

    zero_checks = submission.check_variants(zeros, TEMPLATE)
    nan_checks = submission.check_variants(nan_tif, TEMPLATE)
    if not zero_checks["format_valid"] or not nan_checks["format_valid"]:
        raise SystemExit("XFRONT artifact failed the shared format validator")
    if zero_checks["submission_authorized"] or nan_checks["submission_authorized"]:
        raise SystemExit("A format validator cannot authorize a submission")

    stem = name[:-4]
    checks = {
        "zero_outside": zero_checks,
        "nan_outside": nan_checks,
        "zeros_zip_file": zip_name,
        "zeros_zip_sha256": card["zip_sha256"],
    }
    with __import__("zipfile").ZipFile(zip_path) as zf:
        if zf.namelist() != [name]:
            raise SystemExit("XFRONT ZIP must contain exactly the single GeoTIFF")
        if sha256_file(zeros) != card["raster_sha256"]:
            raise SystemExit("XFRONT ZIP contents disagree with the artifact hash")
    (DOWNLOADS / f"checks-{stem}.json").write_text(
        json.dumps(checks, indent=2, allow_nan=False) + "\n"
    )

    note_file = f"note-{stem}.txt"
    (DOWNLOADS / note_file).write_text(card["note"] + "\n")
    if len(card["note"]) > 140:
        raise SystemExit("XFRONT note exceeds the 140-character limit")

    fresh = selector.verify_selector(zeros, TEMPLATE, card)
    (DOWNLOADS / f"{stem}.selector.json").write_text(
        json.dumps(fresh, indent=2, allow_nan=False) + "\n"
    )
    if fresh["decision"] != "DO_NOT_SUBMIT" or card["ok_to_submit"]:
        raise SystemExit("XFRONT selector must remain fail-closed for this artifact")

    fp = footprint_mod.load_footprint()
    with rasterio.open(zeros) as ds:
        dots = (ds.read(1) > 0.5) & fp
    preview = ROOT / "docs" / "assets" / "xfront-preview.png"
    dprf.write_preview(dots, fp, preview)

    holdout = card["holdout"]
    nov = card["novelty"]
    c2 = card["c2st_exact_file"]["candidate"]
    prof = card["off_catalogue_distance_profile"]
    sel = card["density_matched_sparse_simulation"]["selected"]
    packet = {
        "lane_id": "H24-XFRONT",
        "file": name,
        "sha256": card["raster_sha256"],
        "nan_file": nan_name,
        "nan_sha256": card["nan_outside_sha256"],
        "zip_file": zip_name,
        "zip_sha256": card["zip_sha256"],
        "checks_file": f"checks-{stem}.json",
        "preflight_file": f"{stem}.preflight.json",
        "selector_file": f"{stem}.selector.json",
        "note_file": note_file,
        "note": card["note"],
        "pixel_count": int(prof["n_dots"]),
        "requested_budget": int(card["selected_budget"]),
        "selected_arm": card["selected_arm"],
        "holdout_dti": holdout["dti"],
        "holdout_ci95": holdout["ci95"],
        "holdout_evaluator": holdout["evaluator_version"],
        "n_withheld_positive_pixels": holdout["n_withheld_positive_pixels"],
        "simulated_sparse_dti": sel["sparse_simulated_dti"],
        "simulated_sparse_ci95": sel["sparse_ci95"],
        "simulated_sparse_fraction": 0.20,
        "paired_delta_vs_ablation": card["paired_vs_baseline"]["paired_delta_dti"],
        "paired_delta_ci95_vs_ablation": card["paired_vs_baseline"]["ci95"],
        "ablation_arm_dti": card["paired_vs_baseline"]["baseline_dti"],
        "c2st_auc": c2["observed_auc"],
        "c2st_holm_p": c2["holm_p_value"],
        "c2st_strict_gate_passed": c2["strict_gate_passed"],
        "competing_method_novelty_passed": bool(nov["final_dots"]["method_lane_passed"]),
        "competing_method_max_3px_overlap": nov["final_dots"]["method_lane_max_dot_overlap"],
        "competing_method_max_abs_rho": nov["final_dots"]["method_lane_max_abs_rank_correlation"],
        "peer_blobs_novelty_passed": bool(nov["peers_final"]["passed"]),
        "peer_blobs_max_3px_overlap": nov["peers_final"]["max_dot_overlap_within_3px"],
        "registry_entries_checked": nov["registry_entries_checked"],
        "competing_method_rasters_checked": nov["final_dots"]["competing_method_rasters_count"],
        "apron_2_to_9px_fraction": prof["frac_2_to_9px_apron"],
        "farfield_gt20px_fraction": prof["frac_gt_20px_farfield"],
        "median_distance_px": prof["median_dist_px"],
        "technical_promotion_gates_passed": False,
        "ok_to_download": True,
        "ok_to_submit": False,
        "submission_authorized": False,
        "verdict": card["verdict"],
        "selector_decision": fresh["decision"],
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "slots_used": 0,
    }
    (ROOT / "docs" / "data" / "xfront_download.json").write_text(
        json.dumps(packet, indent=2, allow_nan=False) + "\n"
    )
    print(json.dumps(packet, indent=2))


if __name__ == "__main__":
    main()
