"""Fail-closed recorded-evidence selector screen, never a quota bypass.

Exact bytes and recorded gate values are checked mechanically. This is NOT a
complete independent retraining/leakage/novelty replay certificate. In particular,
no legitimate current-account quota verifier is wired into the project, so this
version can issue negative decisions only. A human inspection/confirmation or a
self-asserted flag cannot override that blocker. Never uploads or contacts a
competition portal. Historical v1 receipts remain immutable research evidence.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import submission
from .benchmarks import EVALUATOR, recorded_point_best
from .validator import sha256_file

SELECTOR_VERSION = "gems-selector-v2-literal-quota-fail-closed"

# Read the highest currently recorded declared-comparable point estimate.
# This is a conservative floor, not certification that its method is promotable.
try:
    RECORDED_BEST_EVIDENCE = recorded_point_best(Path(__file__).resolve().parents[2])
except (OSError, ValueError, KeyError, TypeError):
    RECORDED_BEST_EVIDENCE = None
RECORDED_BEST_DTI = (
    RECORDED_BEST_EVIDENCE["holdout"]["dti"] if RECORDED_BEST_EVIDENCE is not None else float("inf")
)
RECORDED_BEST_EVALUATOR = EVALUATOR

MAX_RANK_CORRELATION = 0.90
MAX_DOT_OVERLAP = 0.70
MAX_NOTE_CHARS = 140
MAX_EXPERIMENTS = 3


def _number(value: Any, lower: float, upper: float) -> bool:
    """JSON numbers only: reject booleans, coercible strings and nonfinite values."""
    return type(value) in (int, float) and lower <= value <= upper and math.isfinite(value)


def _positive_interval(value: Any) -> bool:
    return (
        isinstance(value, list)
        and len(value) == 2
        and all(_number(v, 0, 1) for v in value)
        and 0 < value[0] <= value[1]
    )


def _strict_ok(checks: dict[str, Any]) -> bool:
    try:
        return bool(
            checks["checks"]["variant_strict_whole_array_no_nan_allowed"]["pass"] is True
            and checks["checks"]["footprint_range_0_1"]["pass"] is True
            and checks["checks"]["footprint_all_finite"]["pass"] is True
        )
    except (KeyError, TypeError):
        return False


def _literal_novelty_passed(run_card: dict[str, Any]) -> bool:
    """All entries means ALL entries; no control exception, no vacuous success."""
    try:
        novelty_result = run_card["novelty"]
        surface, final = novelty_result["surface"], novelty_result["final_dots"]
        return (
            surface.get("literal_all_entries_passed") is True
            and final.get("literal_all_entries_passed") is True
            and isinstance(final.get("literal_duplicate_rows"), list)
            and not final["literal_duplicate_rows"]
        )
    except (KeyError, TypeError, AttributeError):
        return False


def verify_selector(
    artifact: Path | str,
    template: Path | str,
    run_card: dict[str, Any],
) -> dict[str, Any]:
    """Re-derive the submit decision for ``artifact`` from bytes + run card."""
    artifact = Path(artifact)
    gates: dict[str, bool] = {}
    reasons: list[str] = []

    def fail(name: str, why: str) -> None:
        gates[name] = False
        reasons.append(f"{name}: {why}")

    # --- identity: exact bytes must be the run card's raster -----------------
    try:
        actual_sha = sha256_file(artifact) if artifact.is_file() else None
    except OSError:
        actual_sha = None
    if actual_sha is not None and actual_sha == run_card.get("raster_sha256"):
        gates["artifact_hash_matches_run_card"] = True
    else:
        fail("artifact_hash_matches_run_card", "sha256 mismatch or file missing")

    if artifact.name == run_card.get("submission_name"):
        gates["artifact_name_matches_run_card"] = True
    else:
        fail("artifact_name_matches_run_card", "filename differs from run card")

    # --- G1: format + strict whole-array [0,1], re-run on the exact bytes ---
    try:
        checks = submission.check_variants(artifact, template)
        if checks.get("format_valid") is True and _strict_ok(checks):
            gates["g1_format_strict_0_1"] = True
        else:
            fail("g1_format_strict_0_1", "shared validator or strict [0,1] variant failed")
    except Exception as exc:  # fail closed on any validator error
        fail("g1_format_strict_0_1", f"validator error: {type(exc).__name__}")

    # --- G2: leakage canaries -------------------------------------------------
    try:
        canary = run_card["leakage_canary"]
        worst = canary["worst_polarity_extremity"]
        if canary.get("passed") is True and _number(worst, 0.5, 0.90):
            gates["g2_leakage_canary"] = True
        else:
            fail("g2_leakage_canary", f"passed={canary.get('passed')}, worst extremity={worst}")
    except (KeyError, TypeError, ValueError, AttributeError):
        fail("g2_leakage_canary", "canary evidence missing or malformed")

    # --- G3: holdout win --------------------------------------------------------
    try:
        holdout = run_card["holdout"]
        paired = run_card["paired_vs_baseline"]
        dti = holdout["dti"]
        ci_lo = paired["ci95"][0]
        n_pos = holdout["n_withheld_positive_pixels"]
        ok = (
            _number(dti, 0, 1)
            and holdout.get("label") == "HOLDOUT-DTI"
            and holdout.get("evaluator_version") == RECORDED_BEST_EVALUATOR
            and math.isfinite(dti)
            and RECORDED_BEST_DTI < dti <= 1
            and _positive_interval(paired["ci95"])
            and type(n_pos) is int
            and n_pos == 60988
            and run_card.get("baseline_reproduced") is True
        )
        current_pair = run_card.get("paired_vs_current_best", {})
        current_ci = current_pair.get("ci95", [])
        ok = ok and (
            _number(current_pair.get("baseline_dti"), 0, 1)
            and current_pair.get("baseline_dti") == RECORDED_BEST_DTI
            and current_pair.get("evaluator_version") == RECORDED_BEST_EVALUATOR
            and type(current_pair.get("n_withheld_positive_pixels")) is int
            and current_pair.get("n_withheld_positive_pixels") == 60988
            and current_pair.get("baseline_replayed") is True
            and _positive_interval(current_ci)
        )
        if ok:
            gates["g3_holdout_beats_recorded_best_and_paired_baseline"] = True
        else:
            fail(
                "g3_holdout_beats_recorded_best_and_paired_baseline",
                f"dti={dti} vs recorded best {RECORDED_BEST_DTI}, paired CI lower={ci_lo}",
            )
    except (KeyError, TypeError, ValueError, IndexError, AttributeError):
        fail("g3_holdout_beats_recorded_best_and_paired_baseline", "holdout evidence malformed")

    # --- G4: registry novelty (surface + final dots) ---------------------------
    try:
        nov = run_card["novelty"]
        surf_rho = nov["surface"]["max_abs_rank_correlation"]
        fin = nov["final_dots"]
        fin_rho = fin["max_abs_rank_correlation"]
        overlap = fin["method_lane_max_dot_overlap"]
        peer_overlap = nov["peers_final"]["max_dot_overlap_within_3px"]
        ok = (
            _number(surf_rho, 0, MAX_RANK_CORRELATION)
            and _number(fin_rho, 0, MAX_RANK_CORRELATION)
            and _number(overlap, 0, MAX_DOT_OVERLAP)
            and _number(peer_overlap, 0, MAX_DOT_OVERLAP)
            and fin.get("method_lane_passed") is True
            and nov["peers_final"].get("passed") is True
            and _literal_novelty_passed(run_card)
        )
        if ok:
            gates["g4_registry_novelty"] = True
        else:
            fail(
                "g4_registry_novelty",
                f"surface|rho|={surf_rho}, final|rho|={fin_rho}, "
                f"method overlap={overlap}, peer overlap={peer_overlap}",
            )
    except (KeyError, TypeError, ValueError, AttributeError):
        fail("g4_registry_novelty", "novelty evidence missing or malformed")

    # --- G5: exact-file C2ST nuisance audit --------------------------------------
    try:
        c2st = run_card["c2st_exact_file"]
        if c2st.get("strict_gate_passed") is True and c2st.get("labels_audited_first") is True:
            gates["g5_exact_file_c2st"] = True
        else:
            fail("g5_exact_file_c2st", "strict C2ST gate not passed on the exact file")
    except (KeyError, TypeError, AttributeError):
        fail("g5_exact_file_c2st", "C2ST evidence missing or malformed")

    # --- note + budget -------------------------------------------------------------
    note = run_card.get("note")
    if isinstance(note, str) and 0 < len(note) <= MAX_NOTE_CHARS:
        gates["note_at_most_140_chars"] = True
    else:
        fail("note_at_most_140_chars", "note missing or longer than 140 characters")

    try:
        if (
            type(run_card["experiments_run"]) is int
            and 1 <= run_card["experiments_run"] <= MAX_EXPERIMENTS
            and type(run_card["submission_slots_used"]) is int
            and run_card["submission_slots_used"] == 0
        ):
            gates["budget_and_no_slot_spent"] = True
        else:
            fail("budget_and_no_slot_spent", "experiment budget exceeded or slot already spent")
    except (KeyError, TypeError, ValueError, AttributeError):
        fail("budget_and_no_slot_spent", "budget evidence missing or malformed")

    recorded_scientific_screen_passed = bool(gates) and all(gates.values())
    # No positive authorization path until legitimate, independently verified
    # current-account allowance AND the complete replay certificate are wired.
    # Merely adding quota_confirmed=true to an arbitrary card is not evidence.
    fail(
        "current_account_quota_independently_verified",
        "unknown; no quota verifier/receipt adapter implemented; no human-confirmation exception",
    )
    fail(
        "complete_independent_replay_certificate",
        "not implemented; recorded flags and numeric summaries are screening evidence, not an independent promotion certificate",
    )
    ok_to_submit = bool(gates) and all(gates.values())
    return {
        "selector_version": SELECTOR_VERSION,
        "decided_utc": datetime.now(timezone.utc).isoformat(),
        "artifact": artifact.name,
        "artifact_sha256": actual_sha,
        "human_inspection_used": False,
        "gates": gates,
        "all_gates_passed": ok_to_submit,
        "ok_to_submit": ok_to_submit,
        "decision": "OK_TO_SUBMIT" if ok_to_submit else "DO_NOT_SUBMIT",
        "quota_status": "unknown_BLOCKED_no_manual_confirmation_exception",
        "recorded_scientific_screen_passed": recorded_scientific_screen_passed,
        "current_point_best_source": RECORDED_BEST_EVIDENCE["source"]
        if RECORDED_BEST_EVIDENCE
        else None,
        "reasons": reasons,
        "scope": (
            "Recorded-evidence screening and exact-file validation only; positive authorization "
            "is not implemented. Not an organizer score, quota record or acceptance guarantee. The agent never uploads."
        ),
    }
