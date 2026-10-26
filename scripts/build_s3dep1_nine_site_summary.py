#!/usr/bin/env python3
"""Build the frozen 2026-10-26 nine-site S3DEP1 forensic receipt.

The input refs were main HEAD when the original audit ran; they are immutable
snapshot pins, not current HEAD.  The receipt computes exact distance profiles
and 3-px dot overlaps against S3DEP1, DPRF1, DKRN1 and historical B2.  It does
not verify owner-reported scores or infer hidden-label credit.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from gems import footprint  # noqa: E402
from gems.novelty import dot_overlap  # noqa: E402

FEATURED_20261026 = {
    "GEMSDOE25": (
        "bc3381fd82d8dca5c75721366ad90b2af8019548",
        "gems25-h72-3-subsurf-pttg-mths-sapd3-0-k3p0-20261026-88bbebfe79b4-zeros.tif",
        (
            "DO NOT SUBMIT — GEMSDOE25 HEAD (bc3381fd, H72-3 PTTG-MTHS, 41,061 dots) "
            "self-marks SUBMIT: NO after confirmation miss; historical D2.8 (0.2600 "
            "UNVERIFIED-OWNER-REPORT) is prohibited to copy."
        ),
    ),
    "GEMSDOE27": (
        "f1e32af867d9cf0081af20866c8241ec8678a432",
        "gems27-h31-drcg-wl-celf28-20261026-cf8e1bbef244-allfinite.tif",
        (
            "DO NOT SUBMIT — H31-DRCG evaluated on non-comparable 289,180-px split "
            "(0.04730 HOLDOUT-DTI; ~0.235 text is an unverified PROJECTION, not a score) "
            "and omits registry-039 literal lattice check; H29-CELF (0.2190 "
            "UNVERIFIED-OWNER-REPORT) already scored."
        ),
    ),
    "GEMSDOE28": (
        "9c1be21e8f1be707347f737e42abf62ea669c819",
        "gems28-s20-nchc-20261026-d432a1d5d6ee-allfinite.tif",
        (
            "DO NOT SUBMIT — S20-NCHC scored HOLDOUT-DTI 0.13126 (53.0% apron clustering; "
            "trails S3DEP1 0.16606 by -0.03480 and DPRF1 0.16379 by -0.03253); 12/44 "
            "repo downloads un-manifested (flagged irregularity)."
        ),
    ),
    "GEMSDOE30": (
        "35ce8911e2c3287eed973eacd12c252e8cb3f34c",
        "GEMSDOE30-geothermal-corridor-offcat-d3-20261026T160300Z.tif",
        (
            "DO NOT SUBMIT — FAILS strict whole-array [0,1] (7,111,787 NaN cells outside "
            "footprint; risks DrivenData '[0, 1]' range rejection) and H30-14 (0.1371) "
            "is self-marked DO NOT SUBMIT."
        ),
    ),
    "GEMSDOE31": (
        "78f9bf3ae82e5c78ca348aa37c0660c339e72f0e",
        "gemsdoe31-h31t-transtension-dinkelbach-20261025-b37654-zeros.tif",
        (
            "DO NOT SUBMIT — H31-T scored 0.1300 on gems57 protocol and subsequent H31-U "
            "strain-seismic corroboration (e9befc53, 0.0952) is self-marked DO NOT SUBMIT; "
            "earlier CSDU companion had 2,610,312 nonfinite interior cells (irregularity)."
        ),
    ),
    "GEMSDOE32": (
        "8953b986b2ce6eb5ee8b7eda23fe3ad529720986",
        "gemsdoe32-h46-trhv-tworegime-ventconduit-37654-20261026T173000Z-6437b275-zeros.tif",
        (
            "DO NOT SUBMIT — Historical H33-B2 (0.2778 UNVERIFIED-OWNER-REPORT) is an "
            "exact 37,654-dot halo-deletion subset of D2.8 prohibited to copy; 2026-10-26 "
            "lanes H45/H46 self-mark DO NOT SUBMIT and 'arena47-perturb-h38-unique' "
            "(f2c238b48468) is flagged as a perturbed derivative irregularity."
        ),
    ),
    "GEMSDOE33": (
        "a24fb7c5031ee08b12440af4593057858fecef8e",
        "gemsdoe33-a33-r3-llc-37654-20261026-7f91f9f3ced9-zeros.tif",
        (
            "DO NOT SUBMIT — A33-R3-LLC scored HOLDOUT-DTI 0.13151 (trails S3DEP1 0.16606 "
            "and DPRF1 0.16379) and GEMSDOE33 HEAD (a24fb7c5) explicitly marks DO NOT SUBMIT."
        ),
    ),
    "GEMSDOE36": (
        "b90418f852615aa0974cf9a53b92fa569ed133fc",
        "gemsdoe36-hvg36-vent-dipole-20261026-b3ee97873192-zeros.tif",
        (
            "DO NOT SUBMIT — HVG-36 scored HOLDOUT-DTI 0.135759 (paired CI spans zero), "
            "companion GVSC-36 has 94.6% internal overlap, and GEMSDOE36 HEAD (b90418f8) "
            "explicitly marks DO NOT SUBMIT."
        ),
    ),
}


def read_mask(path: Path, fp: np.ndarray) -> np.ndarray:
    with rasterio.open(path) as src:
        arr = src.read(1)
    return fp & np.isfinite(arr) & (arr > 0.5)


def main() -> int:
    fp = footprint.load_footprint()
    with rasterio.open(ROOT / "data/bridge/existing_faults.tif") as src:
        lab = src.read(1)
        cat = fp & np.isfinite(lab) & (lab > 0.5)
    dist_cat = distance_transform_edt(~cat).astype(np.float32)

    s3_card = json.loads((ROOT / "evidence/s3dep1_run_card_20261026.json").read_text())
    dprf_card = json.loads((ROOT / "evidence/dprf1_run_card_20261026.json").read_text())
    prev_nine = json.loads(
        (ROOT / "evidence/nine_site_executive_summary_dkrn1_20261026.json").read_text()
    )
    manifest = json.loads(
        (ROOT / "data/research/nine_site_20261026_refresh/manifest_20261026.json").read_text()
    )
    by_repo_file = {(r["repo"], Path(r["path"]).name): r for r in manifest}

    s3_dots = read_mask(ROOT / "docs/downloads" / s3_card["submission_name"], fp)
    dprf_dots = read_mask(ROOT / "docs/downloads" / dprf_card["submission_name"], fp)
    dkrn_card = json.loads((ROOT / "evidence/dkrn1_run_card_20261026.json").read_text())
    dkrn_dots = read_mask(ROOT / "docs/downloads" / dkrn_card["submission_name"], fp)
    b2_row = by_repo_file[
        (
            "buffedlizard55-lab/GEMSDOE32",
            "gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif",
        )
    ]
    b2_dots = read_mask(ROOT / b2_row["cache_path"], fp)

    prev_by_site = {r["site"]: r for r in prev_nine["sites"]}
    sites_out = []

    # Site 24 (this repo)
    s3_dist = s3_card["off_catalogue_distance_profile"]
    sites_out.append(
        {
            "site": "GEMSDOE24",
            "repo": "buffedlizard55-lab/GEMSDOE24",
            "inspected_main_commit": "5cfab74597cd1d0a271e4640b4cc34511e56ca59",
            "pages_url": "https://buffedlizard55-lab.github.io/GEMSDOE24/",
            "executive_summary_url": "https://buffedlizard55-lab.github.io/GEMSDOE24/executive-summary.html",
            "historical_best_submission": "h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan",
            "historical_best_owner_reported_score": 0.2477,
            "score_provenance_label": "UNVERIFIED-OWNER-REPORT",
            "recorded_point_best_artifact": s3_card["submission_name"],
            "recorded_point_best_sha256": s3_card["raster_sha256"],
            "recorded_point_best_holdout_dti": s3_card["holdout"]["dti"],
            "recorded_point_best_ci95": s3_card["holdout"]["ci95"]["interval"],
            "previous_point_best_dprf1": {
                "artifact_file": dprf_card["submission_name"],
                "artifact_sha256": dprf_card["raster_sha256"],
                "holdout_dti": dprf_card["holdout"]["dti"],
                "holdout_ci95": dprf_card["holdout"]["ci95"]["interval"],
                "c2st_auc": dprf_card["exact_file_nuisance_audit"]["candidate"]["observed_auc"],
            },
            "latest_s3dep1_20261026": {
                "artifact_file": s3_card["submission_name"],
                "artifact_sha256": s3_card["raster_sha256"],
                "dots": 37654,
                "whole_array_strict_0_1": True,
                "holdout_dti": s3_card["holdout"]["dti"],
                "holdout_ci95": s3_card["holdout"]["ci95"]["interval"],
                "arm1_core_dti": s3_card["arms_same_evaluator"]["arm1_s3dep1_core_dualneg_61ch"][
                    "dti"
                ],
                "arm2_kernel300_dti": s3_card["arms_same_evaluator"][
                    "arm2_s3dep1_kernel300_reg_61ch"
                ]["dti"],
                "bridge_3km_dti": s3_card["bridge_protocol_holdout"]["dti"],
                "ne_lidar_gap_heavy_dti": s3_card["holdout"]["folds"][1]["dti"],
                "apron_2_to_9px": round(float(s3_dist["frac_2_to_9px_apron"]), 4),
                "farfield_gt_20px": round(float(s3_dist["frac_gt_20px_farfield"]), 4),
                "overlap_3px_vs_DPRF1": round(
                    float(
                        s3_card["correlation_overlap_vs_registry"][
                            "dot_overlap_within_3px_vs_dprf1"
                        ]
                    ),
                    4,
                ),
                "overlap_3px_vs_DKRN1": round(
                    float(
                        s3_card["correlation_overlap_vs_registry"][
                            "dot_overlap_within_3px_vs_dkrn1"
                        ]
                    ),
                    4,
                ),
                "overlap_3px_vs_B2": round(
                    float(
                        s3_card["correlation_overlap_vs_registry"][
                            "dot_overlap_within_3px_vs_gemsdoe32_b2"
                        ]
                    ),
                    4,
                ),
                "c2st_auc": round(
                    float(s3_card["exact_file_nuisance_audit"]["candidate"]["observed_auc"]), 4
                ),
                "verdict": "negative",
                "ok_to_download": True,
                "ok_to_submit": False,
            },
            "inspected_20261026_artifact": s3_card["submission_name"],
            "inspected_20261026_sha256": s3_card["raster_sha256"],
            "inspected_20261026_dots": 37654,
            "whole_array_strict_0_1": True,
            "apron_2_to_9px": round(float(s3_dist["frac_2_to_9px_apron"]), 4),
            "farfield_gt_20px": round(float(s3_dist["frac_gt_20px_farfield"]), 4),
            "s3dep1_3px_overlap_vs_site_artifact": 1.0,
            "executive_verdict": (
                "DOWNLOAD: YES (research audit) · SUBMIT: NO. H24-S3DEP1 is GEMSDOE24's "
                "current recorded local HOLDOUT-DTI point-best (0.16606 [0.15186, 0.18034], "
                "NE_LidarGapHeavy 0.21972, zero 1 m LiDAR, 64.45% <= 70% vs DPRF1, "
                "<=53.17% vs all 8 sibling sites in this frozen audit), but stops on 71.32% "
                "overlap vs local DKRN1, road-associated C2ST 0.6012 (highway cut/fill is a "
                "plausible mimic), paired CI spanning 0 vs DPRF1, and registry-039."
            ),
        }
    )

    for site_name in (
        "GEMSDOE25",
        "GEMSDOE27",
        "GEMSDOE28",
        "GEMSDOE30",
        "GEMSDOE31",
        "GEMSDOE32",
        "GEMSDOE33",
        "GEMSDOE36",
    ):
        head_commit, fname, verdict_str = FEATURED_20261026[site_name]
        repo = f"buffedlizard55-lab/{site_name}"
        mrow = by_repo_file[(repo, fname)]
        dots = read_mask(ROOT / mrow["cache_path"], fp)
        dvals = dist_cat[dots]
        apron = float(np.mean((dvals > 2.0) & (dvals <= 9.0))) if dvals.size else 0.0
        farf = float(np.mean(dvals > 20.0)) if dvals.size else 0.0
        ov_s3 = float(
            dot_overlap(s3_dots, dots, radius_px=3.0)["candidate_within_3px_of_reference"]
        )
        ov_dprf = float(
            dot_overlap(dprf_dots, dots, radius_px=3.0)["candidate_within_3px_of_reference"]
        )
        ov_dkrn = float(
            dot_overlap(dkrn_dots, dots, radius_px=3.0)["candidate_within_3px_of_reference"]
        )
        ov_b2 = float(
            dot_overlap(dots, b2_dots, radius_px=3.0)["candidate_within_3px_of_reference"]
        )
        prev = prev_by_site[site_name]
        entry = {
            "site": site_name,
            "repo": repo,
            "inspected_main_commit": head_commit,
            "pages_url": prev["pages_url"],
            "executive_summary_url": prev["executive_summary_url"],
            "historical_best_submission": prev["historical_best_submission"],
            "historical_best_owner_reported_score": prev["historical_best_owner_reported_score"],
            "score_provenance_label": "UNVERIFIED-OWNER-REPORT",
            "inspected_20261026_artifact": fname,
            "inspected_20261026_sha256": mrow["sha256"],
            "inspected_20261026_dots": int(mrow["positive_pixels"]),
            "whole_array_strict_0_1": bool(mrow["strict_whole_array_0_1"]),
            "apron_2_to_9px": round(apron, 4),
            "farfield_gt_20px": round(farf, 4),
            "overlap_3px_vs_B2": round(ov_b2, 4),
            "overlap_3px_vs_DPRF1": round(ov_dprf, 4),
            "overlap_3px_vs_DKRN1": round(ov_dkrn, 4),
            "s3dep1_3px_overlap_vs_site_artifact": round(ov_s3, 4),
            "executive_verdict": verdict_str,
        }
        if site_name == "GEMSDOE27":
            entry["latest_20261025_scored_submission"] = prev["latest_20261025_scored_submission"]
        sites_out.append(entry)

    out = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "scope": (
            "H24-S3DEP1 recorded results plus a frozen 2026-10-26 nine-site forensic "
            "snapshot at listed immutable commits; not current HEAD or score verification"
        ),
        "supersedes": "evidence/nine_site_executive_summary_dkrn1_20261026.json (kept, unmodified)",
        "score_governance": prev_nine["score_governance"],
        "cross_site_executive_conclusion": {
            "best_historical_reference_not_for_resubmission": (
                "GEMSDOE32 H33-B2 (0.2778 UNVERIFIED-OWNER-REPORT) is a pixel-exact "
                "37,654-dot deletion-only subset of D2.8 with 6,436 <=200 m catalogue-halo "
                "dots removed. Hidden credit and causal score effect are unobserved; do not "
                "copy or perturb it."
            ),
            "best_already_scored_unique_20261025_submission": prev_nine[
                "cross_site_executive_conclusion"
            ]["best_already_scored_unique_20261025_submission"],
            "recorded_local_point_best_research_only": (
                f"GEMSDOE24 H24-S3DEP1 {s3_card['submission_name']} (SHA-256 "
                f"{s3_card['raster_sha256']}; HOLDOUT-DTI 0.16606 [0.15186, 0.18034], "
                "gems-segment-pooled-v1, 60,988 withheld, zero 1 m LiDAR, NE_LidarGapHeavy "
                "0.21972, 3.0 km Bridge 0.16257, 64.45% 3-px overlap vs DPRF1 <= 70%, "
                "<=53.17% vs all 32 sibling focus TIFFs in the frozen audit, <=54.33% vs all "
                "83 peer blobs). DOWNLOAD: YES (audit only) · SUBMIT: NO (not a literal-gate-"
                "unique or submit-ready candidate: 71.32% 3-px overlap vs local stopped lane "
                "DKRN1, exact-file C2ST AUC 0.6012 holm_p=0.0200, paired CI vs DPRF1 "
                "[-0.00699, +0.01144] spans zero, and retained spacing-5 lattice registry-039)."
            ),
            "previous_point_best_dprf1_disposition": (
                f"GEMSDOE24 H24-DPRF1 {dprf_card['submission_name']} (HOLDOUT-DTI 0.16379 "
                "[0.15045, 0.17739], C2ST 0.5247 PASS, 55.78% original competing-method "
                "novelty PASS, 86.66% overlap vs subsequent EUL1) remains not a literal-gate-"
                "unique or submit-ready candidate under gems-selector-v2-literal-quota-fail-closed."
            ),
            "all_eight_20261026_sibling_tifs_audited": (
                "Frozen audit: 32 GeoTIFFs across GEMSDOE25@bc3381fd, 27@f1e32af8, "
                "28@9c1be21e, 30@35ce8911, 31@78f9bf3a, 32@8953b986, 33@a24fb7c5, and "
                "36@b90418f8 were SHA-verified and audited pixel-by-pixel. These refs are no "
                "longer presented as live HEAD; newer commits need a new artifact audit."
            ),
            "can_we_beat_02778_03195_04413": (
                "Unproven and unforecastable without organizer receipts and hidden labels. "
                "Pixel algebra proves B2 is a deletion-only subset, not that its deleted dots "
                "had zero hidden-fault credit. Break-even credit per added mass is alpha*D: "
                "5.56%, 6.39%, and 8.83% at D=0.2778, 0.3195, and 0.4413; corresponding "
                "true-credit/false-mass ratios are 5.88%, 6.83%, and 9.68%."
            ),
        },
        "sites": sites_out,
        "correction_20261026": {
            "irregularity_id": "IRR-S3DEP1-MARGINAL-THRESHOLD-UNOBSERVED-CAUSAL",
            "status": "corrected narrative; recorded raster measurements unchanged",
            "detail": (
                "Earlier prose mislabeled the delta-TP/delta-FP threshold as delta-TP/delta-N "
                "and treated zero hidden credit as observed."
            ),
            "source_refresh": "evidence/focus_source_refresh_20261026.json",
        },
    }

    out_path = ROOT / "evidence/nine_site_executive_summary_s3dep1_20261026.json"
    out_path.write_text(json.dumps(out, indent=2, allow_nan=False) + "\n")
    print(f"Wrote {out_path} ({len(sites_out)} sites).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
