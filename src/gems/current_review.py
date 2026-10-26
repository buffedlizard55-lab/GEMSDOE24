"""Read-only current-best audit. Rechecks bytes, not scientific replay or quota."""

from __future__ import annotations

import json
from pathlib import Path

from .benchmarks import recorded_point_best
from .selector import verify_selector
from .submission import check_variants


def review_current_best(root: Path) -> dict:
    root = Path(root)
    best = recorded_point_best(root)
    card = json.loads((root / best["source"]).read_text())
    name = card.get("submission_name", "")
    if not name or Path(name).name != name or not name.endswith("-zeros.tif"):
        raise ValueError("Current best must identify a plain zero-outside TIFF filename")
    receipt = verify_selector(
        root / "docs/downloads" / name,
        root / "data/bridge/sample_submission.tif",
        card,
    )
    identity_format = (
        "artifact_hash_matches_run_card",
        "artifact_name_matches_run_card",
        "g1_format_strict_0_1",
        "note_at_most_140_chars",
    )
    if not all(receipt["gates"].get(key) is True for key in identity_format):
        raise ValueError("Current-best exact-file identity, format or note check failed")
    # This endpoint cannot become an authorization path if the selector changes.
    if receipt["ok_to_submit"] is not False or receipt["decision"] != "DO_NOT_SUBMIT":
        raise ValueError("Review-only endpoint cannot authorize promotion")
    return {
        "audit_version": "current-best-read-only-v1",
        "scope": "Fresh exact-file validation; recorded scientific measurements, not replayed",
        "current_recorded_point_best": best,
        "hypothesis": card.get("hypothesis"),
        "mechanism": (
            "Recorded fault-recovery hypothesis only; this review validates artifact identity "
            "and format, not the causal mechanism or any hidden-leaderboard improvement. "
            "See the original run card for its unverified mechanistic interpretation."
        ),
        "mechanism_source": best["source"],
        "mechanism_causally_verified": False,
        "non_fault_mimic": card.get("non_fault_mimic", card.get("named_non_fault_mimic")),
        "submission_name": name,
        "raster_sha256": card["raster_sha256"],
        "note": card["note"],
        "holdout": best["holdout"],
        "correlation_overlap_vs_registry": card.get("correlation_overlap_vs_registry"),
        "validator_output": check_variants(
            root / "docs/downloads" / name, root / "data/bridge/sample_submission.tif"
        ),
        "selector": receipt,
        "ok_to_download": True,
        "ok_to_submit": False,
        "verdict": "negative",
        "new_experiments": 0,
        "submission_slots_used": 0,
        "organizer_confirmed_score": None,
        "cross_site_ranking": "Not established: sibling holdouts are not independently harmonized",
        "lane_assignment": "No single-method paragraph supplied; no new experiment authorized",
    }
