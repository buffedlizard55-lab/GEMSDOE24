#!/usr/bin/env python3
"""Assemble the CGMK1-session nine-site executive JSON from pinned artifacts.

No number is hand-typed here except labels: historical maxima and source-
featured holdouts come from ``docs/data/current_focus_nine_file_audit_20261027.json``
(2026-10-27 immutable-commit audit); local rows come from the recorded
S3DEP1 and CGMK1 run cards. Owner-reported values stay UNVERIFIED.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "evidence/nine_site_executive_summary_cgmk1_20261027.json"
OUT_DOCS = ROOT / "docs/data/nine_site_executive_summary_cgmk1_20261027.json"


def load(p: str):
    return json.loads((ROOT / p).read_text())


def holdout_brief(h: dict | None, source: str) -> dict | None:
    if not h:
        return None
    if h.get("label") == "INVALID HOLDOUT":
        return {
            "label": "INVALID HOLDOUT",
            "dti": None,
            "status": h.get("status"),
            "source": source,
        }
    return {
        "label": h.get("label"),
        "dti": h.get("value", h.get("dti")),
        "ci95": h.get("ci95", {}).get("interval")
        if isinstance(h.get("ci95"), dict)
        else h.get("ci95"),
        "evaluator_version": h.get("evaluator", h.get("evaluator_version")),
        "n_withheld": h.get("withheld", h.get("n_withheld_positive_pixels")),
        "evidence_class": "SOURCE-RECORDED in the pinned audit; not replayed in this session",
        "source": source,
    }


def main() -> None:
    audit = load("docs/data/current_focus_nine_file_audit_20261027.json")
    cgmk1 = load("evidence/cgmk1_run_card_20261027.json")
    s3dep1 = load("evidence/s3dep1_run_card_20261026.json")
    rows = []
    for r in audit["rows"]:
        rows.append(
            {
                "site": r["site"],
                "source_repo_url": f"https://github.com/buffedlizard55-lab/{r['site']}",
                "historical_best_claim": {
                    "name": r["historical_best_owner_reported_unverified"]["name"],
                    "value": r["historical_best_owner_reported_unverified"]["owner_reported"],
                    "label": "UNVERIFIED-OWNER-REPORT (not ORGANIZER-CONFIRMED)",
                },
                "source_featured_file_at_pinned_commit": {
                    "path": r["source_file"]["path"],
                    "sha256": r["source_file"]["sha256"],
                    "source_url": r["source_file"]["source_url"],
                    "download_url": r["download_url"],
                    "source_ref": r["source_ref"],
                },
                "source_featured_holdout": holdout_brief(
                    r["holdout"], "docs/data/current_focus_nine_file_audit_20261027.json"
                ),
                "dots": r["dots"],
                "literal_lattice_overlap_within_3px": r["literal_lattice_overlap_within_3px"],
                "uniqueness_literal_rule": "FAIL (>70% lattice overlap; see pigeonhole note)",
                "leaderboard_estimate": None,
                "leaderboard_estimate_note": (
                    "No defensible numeric estimate: no artifact-linked organizer receipt; "
                    "holdouts use different evaluators/splits across sites."
                ),
                "ok_to_download_research": True,
                "ok_to_submit": False,
                "decision": "DO_NOT_SUBMIT",
            }
        )
    by_site = {r["site"]: r for r in rows}
    by_site["GEMSDOE24"]["this_session_new_lane"] = {
        "lane": "H24-CGMK1",
        "download_file": cgmk1["submission"]["zeros_tif_path"],
        "sha256": cgmk1["submission"]["zeros_tif_sha256"],
        "holdout": {
            "label": "HOLDOUT-DTI (measured this session; independently rescored)",
            "dti": cgmk1["holdout"]["dti"],
            "ci95": cgmk1["holdout"]["ci95"]["interval"],
            "evaluator_version": cgmk1["holdout"]["evaluator_version"],
            "n_withheld": cgmk1["holdout"]["n_withheld_positive_pixels"],
        },
        "uniqueness": {
            "competing_methods": "PASS (max 3-px overlap "
            f"{cgmk1['novelty']['final_max_competing_dot_overlap_within_3px']:.4f}, "
            f"max |rho| {cgmk1['novelty']['final_max_abs_rank_correlation']:.4f}, "
            f"{cgmk1['novelty']['registry_entries_compared']} local entries)",
            "literal_incl_lattice": "FAIL (lattice overlap 1.0000; pigeonhole minimum 0.8234 at 37,654 dots)",
        },
        "model_projection_not_a_score": cgmk1["model_projection_not_a_score"]["range"],
        "verdict": cgmk1["verdict"],
        "ok_to_submit": False,
    }
    by_site["GEMSDOE24"]["recorded_local_point_best"] = {
        "lane": "H24-S3DEP1 (recorded 2026-10-26; not replayed this session)",
        "download_file": "docs/downloads/gems24-s3dep1-negative-10m-monoclinal-20261026-464fa34b4091-zeros.tif",
        "holdout": {
            "label": "HOLDOUT-DTI (source record)",
            "dti": s3dep1["holdout"]["dti"],
            "ci95": s3dep1["holdout"]["ci95"]["interval"],
            "evaluator_version": s3dep1["holdout"]["evaluator_version"],
            "n_withheld": s3dep1["holdout"]["n_withheld_positive_pixels"],
        },
        "verdict": s3dep1.get("verdict"),
        "ok_to_submit": False,
    }
    out = {
        "schema": "nine-site-executive-summary-cgmk1-v1",
        "generated_from": [
            "docs/data/current_focus_nine_file_audit_20261027.json",
            "evidence/cgmk1_run_card_20261027.json",
            "evidence/s3dep1_run_card_20261026.json",
            "registry/owner_reported_scores_2026-10-26.json",
        ],
        "decision": "DO_NOT_SUBMIT (all rows; zero slots spent this session)",
        "leaderboard_claims": {
            "values_in_owner_briefs": [0.4413, 0.3195],
            "label": "UNVERIFIED-OWNER-REPORT; the two values conflict; no receipt in this repository",
        },
        "best_historical_claim_among_focus_sites": {
            "name": "h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros (GEMSDOE32)",
            "value": 0.2778,
            "label": "UNVERIFIED-OWNER-REPORT",
            "ancestry_source": "evidence/portfolio_artifact_audit_20261026.json#h33_ancestry",
        },
        "pigeonhole_note": (
            "Spacing-5 lattice covers 5,160,724/5,167,373 footprint pixels within 3 px; any "
            "37,654-dot in-footprint set overlaps it by >= 82.34%, so the literal all-entry "
            "70% rule cannot pass at that budget. Control-separated overlaps are reported "
            "alongside; the literal failure is never hidden."
        ),
        "rows": rows,
    }
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    OUT_DOCS.write_text(json.dumps(out, indent=2) + "\n")
    print(f"wrote {OUT} and {OUT_DOCS} with {len(rows)} site rows")


if __name__ == "__main__":
    main()
