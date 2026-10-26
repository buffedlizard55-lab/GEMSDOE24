#!/usr/bin/env python3
"""Build the DRAIN5-updated nine-site executive summary from recorded evidence only.

Reads the EUL1-updated nine-site receipt, the DRAIN5/DPRF1/EUL1 run cards, and
(for overlap auditing only) sibling artifacts re-fetched from GitHub at the
receipt's pinned ``inspected_main_commit`` values and verified byte-identical
against the recorded SHA-256 hashes before any overlap is computed. No numbers
are invented: per-site scores remain UNVERIFIED-OWNER-REPORT unless an organizer
receipt exists, and all local measurements stay labelled HOLDOUT-DTI with
evaluator version, withheld-positive count and 95% CI. Writes a superseding
receipt; earlier nine-site files are never modified.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import numpy as np  # noqa: E402
import rasterio  # noqa: E402
from restore_data import gh_bytes  # noqa: E402
from scipy.stats import rankdata  # noqa: E402

from gems import footprint as footprint_mod  # noqa: E402
from gems import novelty  # noqa: E402
from gems.validator import sha256_file  # noqa: E402

SRC = ROOT / "evidence/nine_site_executive_summary_eul1_20261026.json"
CARD = ROOT / "evidence/drain5_run_card_20261026.json"
DPRF1_CARD = ROOT / "evidence/dprf1_run_card_20261026.json"
EUL1_CARD = ROOT / "evidence/eul1_run_card_20261026.json"
OUT_E = ROOT / "evidence/nine_site_executive_summary_drain5_20261026.json"
OUT_D = ROOT / "docs/data/nine_site_executive_summary_drain5_20261026.json"
FETCH_DIR = ROOT / "data/research/nine_site_drain5"


def fetch_pinned_artifact(site: dict) -> tuple[np.ndarray | None, str]:
    """Return the site's inspected raster, byte-verified, or (None, reason)."""
    basename = str(site.get("inspected_artifact_file") or "")
    expected_sha = str(site.get("inspected_artifact_sha256") or "")
    if not basename or not expected_sha:
        return None, "no inspected artifact recorded"
    local = ROOT / "docs/downloads" / basename
    if local.exists() and sha256_file(local) == expected_sha:
        with rasterio.open(local) as ds:
            return ds.read(1), f"sha-verified local file: docs/downloads/{basename}"
    cached = FETCH_DIR / basename
    if cached.exists() and sha256_file(cached) == expected_sha:
        with rasterio.open(cached) as ds:
            return ds.read(1), f"sha-verified re-fetch cache: {cached.relative_to(ROOT)}"
    repo = str(site["repo"])
    commit = str(site["inspected_main_commit"])
    try:
        tree = json.loads(
            subprocess.check_output(
                ["gh", "api", f"repos/{repo}/git/trees/{commit}?recursive=1"],
                stderr=subprocess.DEVNULL,
            )
        )
        matches = [
            x["path"]
            for x in tree.get("tree", [])
            if str(x.get("path", "")).endswith("/" + basename)
        ]
        if len(matches) != 1:
            return None, f"pinned tree has {len(matches)} paths ending {basename}; not recomputed"
        gh_bytes(repo, matches[0], commit, cached)
    except Exception as exc:  # network/host failure is reported, never papered over
        return None, f"re-fetch at pinned commit failed ({type(exc).__name__}); not recomputed"
    if sha256_file(cached) != expected_sha:
        return None, "re-fetched bytes do not match recorded SHA-256; rejected, not recomputed"
    with rasterio.open(cached) as ds:
        return ds.read(1), f"sha-verified re-fetch at pinned commit: {cached.relative_to(ROOT)}"


def holdout_block(card: dict) -> dict:
    h = card["holdout"]
    return {
        "label": "HOLDOUT-DTI",
        "value": h["dti"],
        "ci95": h["ci95"]["interval"],
        "evaluator_version": h["evaluator_version"],
        "n_withheld_positive_pixels": h["n_withheld_positive_pixels"],
        "is_leaderboard_score": False,
    }


def main() -> None:
    nine = json.loads(SRC.read_text())
    card = json.loads(CARD.read_text())
    dprf1 = json.loads(DPRF1_CARD.read_text())
    eul1 = json.loads(EUL1_CARD.read_text())
    fp = footprint_mod.load_footprint()
    drain_path = ROOT / "docs/downloads" / card["submission_name"]
    if sha256_file(drain_path) != card["raster_sha256"]:
        raise SystemExit("DRAIN5 artifact hash disagrees with run card")
    with rasterio.open(drain_path) as ds:
        drain = ds.read(1)
    drain_dots = (drain > 0.5) & fp
    drain_ranks = rankdata(drain[fp].astype(np.float32))

    sites_out = []
    for site in nine["sites"]:
        entry = dict(site)
        arr, src = fetch_pinned_artifact(site)
        if arr is None or arr.shape != fp.shape:
            entry["drain5_3px_overlap_vs_site_artifact"] = None
            entry["drain5_spearman_vs_site_artifact"] = None
            entry["drain5_overlap_source"] = src
        else:
            ov = novelty.dot_overlap(drain_dots, fp & np.isfinite(arr) & (arr > 0))[
                "candidate_within_3px_of_reference"
            ]
            rho = novelty.rank_correlation(drain_ranks, arr[fp])
            entry["drain5_3px_overlap_vs_site_artifact"] = None if ov is None else float(ov)
            entry["drain5_spearman_vs_site_artifact"] = None if rho is None else float(rho)
            entry["drain5_overlap_source"] = src
        sites_out.append(entry)

    nov = card["correlation_overlap_vs_registry"]
    g24 = next(s for s in sites_out if s["site"] == "GEMSDOE24")
    g24["latest_drain5_20261026"] = {
        "artifact_file": card["submission_name"],
        "artifact_sha256": card["raster_sha256"],
        "dots": card["off_catalogue_distance_profile"]["n_dots"],
        "holdout_dti": card["holdout"]["dti"],
        "holdout_ci95": card["holdout"]["ci95"]["interval"],
        "evaluator_version": card["holdout"]["evaluator_version"],
        "n_withheld_positive_pixels": card["holdout"]["n_withheld_positive_pixels"],
        "paired_delta_vs_dprf1_replay": card["paired_comparisons"]["arm1_vs_arm2_nodrain_replay"][
            "paired_delta_dti"
        ],
        "paired_delta_ci95_vs_dprf1_replay": card["paired_comparisons"][
            "arm1_vs_arm2_nodrain_replay"
        ]["paired_delta_ci95"],
        "paired_fold_wins_vs_dprf1_replay": card["paired_comparisons"][
            "arm1_vs_arm2_nodrain_replay"
        ]["fold_wins"],
        "dot_overlap_within_3px_vs_dprf1": nov["dot_overlap_within_3px_vs_dprf1"],
        "verdict": "negative",
        "ok_to_download": True,
        "ok_to_submit": False,
    }
    g24["executive_verdict_drain5_update"] = (
        "DO NOT SUBMIT DRAIN5: HOLDOUT-DTI 0.16950 beats DPRF1 paired (+0.00571, 95% CI "
        "[+0.00136, +0.01003], 4/4 folds), but 83.55% of its dots lie within 3 px of DPRF1 "
        "(> 70% Rule-1 limit = duplicate lane). The strongest unscored UNIQUE-LANE candidate "
        "REMAINS DPRF1 gems24-dprf1-stitched-oof-tworegime-20261026-81849d67c8bf-zeros.tif "
        "(competing-method novelty PASS; selector step pending). DRAIN5 is the best local "
        "detector measurement and a research download; do not submit both files."
    )

    table = [
        {
            "rank": 1,
            "file_to_download": dprf1["submission_name"],
            "site": "GEMSDOE24 (this repo)",
            "estimated_score": holdout_block(dprf1),
            "organizer_confirmed_score": None,
            "unique_bytes": True,
            "unique_lane_vs_all_competing_methods": True,
            "literal_all_entry_uniqueness_including_synthetic_lattice": False,
            "ok_to_download": True,
            "ok_to_submit": False,
            "obvious_action": (
                "FIRST FILE IF the separate selector step ever authorizes a slot "
                "(currently DO_NOT_SUBMIT: quota unknown, replay certificate missing, "
                "literal lattice retained). Do not submit today."
            ),
        },
        {
            "rank": 2,
            "file_to_download": card["submission_name"],
            "site": "GEMSDOE24 (this repo)",
            "estimated_score": holdout_block(card),
            "organizer_confirmed_score": None,
            "unique_bytes": True,
            "unique_lane_vs_all_competing_methods": False,
            "literal_all_entry_uniqueness_including_synthetic_lattice": False,
            "ok_to_download": True,
            "ok_to_submit": False,
            "obvious_action": (
                "RESEARCH DOWNLOAD ONLY. Best local measurement (paired +0.00571 over DPRF1) "
                "but a duplicate lane of DPRF1 (83.55% dot overlap). Never submit both; "
                "never present as the unique submission."
            ),
        },
        {
            "rank": 3,
            "file_to_download": eul1["submission_name"],
            "site": "GEMSDOE24 (this repo)",
            "estimated_score": holdout_block(eul1),
            "organizer_confirmed_score": None,
            "unique_bytes": True,
            "unique_lane_vs_all_competing_methods": False,
            "literal_all_entry_uniqueness_including_synthetic_lattice": False,
            "ok_to_download": True,
            "ok_to_submit": False,
            "obvious_action": "DO NOT SUBMIT (negative: loses to DPRF1 and 86.57% dot overlap).",
        },
    ]
    for site in sites_out:
        if site["site"] == "GEMSDOE24":
            continue
        scored = site.get("latest_20261025_owner_reported_score")
        table.append(
            {
                "rank": None,
                "file_to_download": site.get("inspected_artifact_file"),
                "site": site["site"],
                "estimated_score": None,
                "owner_reported_score_unverified": scored,
                "organizer_confirmed_score": None,
                "unique_bytes": True,
                "unique_lane_vs_all_competing_methods": None,
                "ok_to_download": True,
                "ok_to_submit": False,
                "obvious_action": site.get("executive_verdict"),
                "drain5_3px_overlap_vs_this_artifact": site.get(
                    "drain5_3px_overlap_vs_site_artifact"
                ),
            }
        )

    out = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "DRAIN5 update of the nine-site executive summary (GEMSDOE24, 25, 27, 28, 30, 31, 32, 33, 36)",
        "supersedes": "evidence/nine_site_executive_summary_eul1_20261026.json (kept, unmodified)",
        "score_governance": nine["score_governance"],
        "download_submit_table": table,
        "cross_site_executive_conclusion": {
            "best_historical_reference_not_for_resubmission": nine[
                "cross_site_executive_conclusion"
            ]["best_historical_reference_not_for_resubmission"],
            "best_already_scored_unique_20261025_submission": nine[
                "cross_site_executive_conclusion"
            ]["best_already_scored_unique_20261025_submission"],
            "best_unscored_unique_candidate": (
                "GEMSDOE24 DPRF1 gems24-dprf1-stitched-oof-tworegime-20261026-81849d67c8bf-zeros.tif "
                "(SHA-256 c1257c1d4b5ac9cc0a8e29b0120c614fcaa1f38474bc1f6de98c0a1afb0567f1; "
                "HOLDOUT-DTI 0.16379 [0.15045, 0.17739], gems-segment-pooled-v1, 60,988 withheld; "
                "replayed bit-identically in both the EUL1 and DRAIN5 sessions; competing-method "
                "novelty PASS at 55.78% max 3-px overlap). This remains the ONE obvious file for a "
                "first authorized slot. Status today: DO_NOT_SUBMIT under selector v2 (live quota "
                "unknown, independent replay certificate missing, literal spacing-5 lattice retained)."
            ),
            "drain5_disposition": (
                "H24-DRAIN5 (gems24-drain5-negative-drainage-knickpoint-20261026-ff95d6fb3205-zeros.tif, "
                f"SHA-256 {card['raster_sha256']}) is the best local detector measurement in the "
                "portfolio — HOLDOUT-DTI 0.16950 [0.15627, 0.18343], paired +0.00571 "
                "[+0.00136, +0.01003] over the bit-identical DPRF1 replay, 4/4 folds, selector gate "
                "G3 TRUE for the first time — but it is a NEGATIVE lane verdict: 83.55% of its dots "
                "lie within 3 px of DPRF1 (82.87% of EUL1), so it is not a unique lane. "
                "DOWNLOAD: YES (research). SUBMIT: NO. Do not retune it; carry its drainage "
                "channels into a fresh preregistration that changes target/allocator geometry."
            ),
            "can_we_beat_02778": (
                "Still unproven and not forecastable from local data. DRAIN5 proves a real, paired, "
                "4/4-fold detector improvement exists beyond the saturated H19-5/B2 emission "
                "geometry, which is the necessary direction; but HOLDOUT-DTI (dense mapped-fault "
                "recovery) does not map linearly onto the sparse hidden-truth leaderboard, and "
                "0.2778 remains UNVERIFIED-OWNER-REPORT. The evidence-based path is unchanged: "
                "authorize DPRF1 through the separate selector step, obtain one "
                "ORGANIZER-CONFIRMED calibration receipt, and let it govern the next lane."
            ),
        },
        "sites": sites_out,
    }
    payload = json.dumps(out, indent=2, allow_nan=False) + "\n"
    OUT_E.write_text(payload)
    OUT_D.parent.mkdir(parents=True, exist_ok=True)
    OUT_D.write_text(payload)
    print(f"Wrote {OUT_E.relative_to(ROOT)} and {OUT_D.relative_to(ROOT)}")
    for s in sites_out:
        print(
            s["site"],
            "drain5_overlap=",
            s["drain5_3px_overlap_vs_site_artifact"],
            s["drain5_overlap_source"],
        )


if __name__ == "__main__":
    main()
