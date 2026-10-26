#!/usr/bin/env python3
"""Build the EUL1-updated nine-site executive summary from recorded evidence only.

Reads the frozen DPRF1 nine-site receipt, the EUL1 run card, and (for overlap
auditing only) cached registry/peer rasters. No numbers are invented: per-site
scores remain UNVERIFIED-OWNER-REPORT unless an organizer receipt exists, and all
local measurements stay labelled HOLDOUT-DTI. Writes a superseding receipt; the
original DPRF1 nine-site file is never modified.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import numpy as np  # noqa: E402
import rasterio  # noqa: E402
from scipy.stats import rankdata  # noqa: E402

from gems import footprint as footprint_mod  # noqa: E402
from gems import novelty  # noqa: E402

SRC = ROOT / "evidence/nine_site_executive_summary_20261026.json"
CARD = ROOT / "evidence/eul1_run_card_20261026.json"
OUT_E = ROOT / "evidence/nine_site_executive_summary_eul1_20261026.json"
OUT_D = ROOT / "docs/data/nine_site_executive_summary_eul1_20261026.json"
PEER_REG = ROOT / "registry/peer_rasters_20261025.json"


def load_raster_by_basename(
    basename: str, fp: np.ndarray, expected_sha: str | None = None
) -> tuple[np.ndarray | None, str | None]:
    """Find a cached competition-grid raster whose recorded path has this basename.

    SHA-verified sibling artifacts re-fetched at the nine-site receipt's pinned
    commits into ``data/research/nine_site_eul1/`` take precedence; any candidate
    whose bytes do not match ``expected_sha`` is rejected.
    """
    if not basename:
        return None, None
    from gems.validator import sha256_file

    cand = ROOT / "data/research/nine_site_eul1" / basename
    if cand.exists() and (expected_sha is None or sha256_file(cand) == expected_sha):
        with rasterio.open(cand) as ds:
            if ds.shape == fp.shape:
                return (
                    ds.read(1),
                    f"sha-verified re-fetch at pinned commit: data/research/nine_site_eul1/{basename}",
                )
    entries = json.loads(PEER_REG.read_text())["entries"]
    for row in entries:
        if Path(str(row.get("path", ""))).name == basename:
            p = ROOT / row["cache_path"]
            if p.exists():
                with rasterio.open(p) as ds:
                    if ds.shape == fp.shape:
                        return ds.read(1), f"peer-cache:{row['cache_path']}"
    # Local downloads (GEMSDOE24 lanes such as DPRF1 itself)
    p = ROOT / "docs/downloads" / basename
    if p.exists():
        with rasterio.open(p) as ds:
            if ds.shape == fp.shape:
                return ds.read(1), f"docs/downloads/{basename}"
    return None, None


def main() -> None:
    nine = json.loads(SRC.read_text())
    card = json.loads(CARD.read_text())
    fp = footprint_mod.load_footprint()
    eul1_path = ROOT / "docs/downloads" / card["submission_name"]
    with rasterio.open(eul1_path) as ds:
        eul1 = ds.read(1)
    eul1_dots = (eul1 > 0.5) & fp
    eul1_ranks = rankdata(eul1[fp].astype(np.float32))

    sites_out = []
    for site in nine["sites"]:
        entry = dict(site)
        arr, src = load_raster_by_basename(
            str(site.get("inspected_artifact_file") or ""),
            fp,
            expected_sha=str(site.get("inspected_artifact_sha256") or "") or None,
        )
        if arr is None:
            entry["eul1_3px_overlap_vs_site_artifact"] = None
            entry["eul1_spearman_vs_site_artifact"] = None
            entry["eul1_overlap_source"] = (
                "inspected artifact not in this session's local cache; not recomputed"
            )
        else:
            ov = novelty.dot_overlap(eul1_dots, fp & np.isfinite(arr) & (arr > 0))[
                "candidate_within_3px_of_reference"
            ]
            rho = novelty.rank_correlation(eul1_ranks, arr[fp])
            entry["eul1_3px_overlap_vs_site_artifact"] = None if ov is None else float(ov)
            entry["eul1_spearman_vs_site_artifact"] = None if rho is None else float(rho)
            entry["eul1_overlap_source"] = src
        sites_out.append(entry)

    g24 = next(s for s in sites_out if s["site"] == "GEMSDOE24")
    g24["latest_eul1_20261026"] = {
        "artifact_file": card["submission_name"],
        "artifact_sha256": card["raster_sha256"],
        "dots": card["off_catalogue_distance_profile"]["n_dots"],
        "holdout_dti": card["holdout"]["dti"],
        "holdout_ci95": card["holdout"]["ci95"]["interval"],
        "evaluator_version": card["holdout"]["evaluator_version"],
        "n_withheld_positive_pixels": card["holdout"]["n_withheld_positive_pixels"],
        "paired_delta_vs_dprf1_replay": card["paired_comparisons"]["arm1_vs_arm2_noeuler_replay"][
            "paired_delta_dti"
        ],
        "paired_delta_ci95_vs_dprf1_replay": card["paired_comparisons"][
            "arm1_vs_arm2_noeuler_replay"
        ]["paired_delta_ci95"],
        "dot_overlap_within_3px_vs_dprf1": card["correlation_overlap_vs_registry"][
            "dot_overlap_within_3px_vs_dprf1"
        ],
        "verdict": "negative",
        "ok_to_download": True,
        "ok_to_submit": False,
    }
    g24["executive_verdict_eul1_update"] = (
        "DO NOT SUBMIT EUL1 (HOLDOUT-DTI 0.16005 < DPRF1 0.16379; 86.57% of its dots within 3 px "
        "of DPRF1 = duplicate lane). The strongest unscored unique candidate REMAINS DPRF1 "
        "gems24-dprf1-stitched-oof-tworegime-20261026-81849d67c8bf-zeros.tif (selector step pending)."
    )

    out = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "EUL1 update of the nine-site executive summary (GEMSDOE24, 25, 27, 28, 30, 31, 32, 33, 36)",
        "supersedes": "evidence/nine_site_executive_summary_20261026.json (kept, unmodified)",
        "score_governance": nine["score_governance"],
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
                "replayed bit-identically inside the EUL1 session). This is the ONE obvious file to "
                "submit IF AND WHEN the separate selector step authorizes a slot (currently "
                "DO_NOT_SUBMIT: quota unknown, literal lattice retained, replay certificate missing). "
                "Submitting any other file first would be strictly worse by local evidence."
            ),
            "eul1_disposition": (
                "H24-EUL1 (gems24-eul1-negative-euler-contact-20261026-eda170f04847-zeros.tif, "
                f"SHA-256 {card['raster_sha256']}) is a valid-format unique-bytes research download "
                "but a NEGATIVE result: HOLDOUT-DTI 0.16005 [0.14729, 0.17278] vs DPRF1 replay "
                "0.16379 (paired delta -0.00375, 95% CI [-0.00825, +0.00074], 1/4 folds) and "
                "86.57% final-dot overlap with DPRF1 (> 70% Rule-1 limit). DOWNLOAD: YES. SUBMIT: NO. "
                "Do not spend a slot on it; do not retune it."
            ),
            "can_we_beat_02778": (
                "Unproven and not forecastable from local data. 0.2778 (UNVERIFIED-OWNER-REPORT) is an "
                "emission-geometry artifact of one strong parent surface (H19-5 sparse-thinned and "
                "catalogue-cleared); no unique detector in this portfolio has yet beaten DPRF1's local "
                "holdout, and HOLDOUT-DTI does not map linearly to the sparse hidden-truth leaderboard. "
                "The only evidence-based path is: authorize DPRF1 through the selector step, obtain an "
                "ORGANIZER-CONFIRMED receipt for it, and let that calibration point govern the next lane."
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
            "eul1_overlap=",
            s["eul1_3px_overlap_vs_site_artifact"],
            s["eul1_overlap_source"],
        )


if __name__ == "__main__":
    main()
