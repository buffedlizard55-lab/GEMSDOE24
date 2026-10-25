"""Fail-closed, exact-file submission preflight.

A syntactically valid GeoTIFF is not evidence that a competition submission is
scientifically eligible.  This module deliberately reports those two questions
separately and reserves ``OK_TO_SUBMIT`` for an independently verified selector release.
Hash-bound run-card booleans alone cannot authorize a competition slot. The
selector receipt verifier is not implemented; current releases fail closed.

The strict whole-array range diagnostic is intentionally stricter than the
competition-template footprint convention: it is useful after a portal reports
``Predicted values must be in range [0, 1]``, but it does not establish why a
portal previously rejected a file or guarantee that a portal will accept it.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import submission
from .validator import sha256_file

SCHEMA_VERSION = 2
NOTE_LIMIT = 140


def _read_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    """Read a JSON object without turning a malformed receipt into a pass."""
    try:
        value = json.loads(path.read_text())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return None, f"unreadable JSON: {exc}"
    if not isinstance(value, dict):
        return None, "JSON root must be an object"
    return value, None


def _card_evidence(artifact: Path, artifact_sha256: str, run_card: Path | None) -> dict[str, Any]:
    """Check that promotion authority is bound to this file, not its name."""
    base: dict[str, Any] = {
        "provided": run_card is not None,
        "path": str(run_card) if run_card is not None else None,
        "readable": False,
        "artifact_sha256_matches": False,
        "artifact_name_matches": False,
        "validator_sha256_matches": False,
        "validator_format_valid": False,
        "verdict_promote": False,
        "submission_authorized": False,
        "scientific_authorization": False,
        "independent_selector_verified": False,
        "reason_codes": [],
        "note": None,
    }
    if run_card is None:
        base["reason_codes"].append("RUN_CARD_REQUIRED")
        return base
    card, error = _read_json(run_card)
    if error:
        base["reason_codes"].append("RUN_CARD_INVALID")
        base["error"] = error
        return base
    base["readable"] = True
    base["artifact_sha256_matches"] = card.get("raster_sha256") == artifact_sha256
    base["artifact_name_matches"] = card.get("submission_name") == artifact.name
    validator = card.get("validator_output")
    if isinstance(validator, dict):
        base["validator_sha256_matches"] = validator.get("sha256") == artifact_sha256
        base["validator_format_valid"] = validator.get("format_valid") is True
    base["verdict_promote"] = card.get("verdict") == "promote"
    base["submission_authorized"] = card.get("submission_authorized") is True
    base["note"] = card.get("note") if isinstance(card.get("note"), str) else None

    for field, code in (
        ("artifact_sha256_matches", "RUN_CARD_HASH_MISMATCH"),
        ("artifact_name_matches", "RUN_CARD_NAME_MISMATCH"),
        ("validator_sha256_matches", "RUN_CARD_VALIDATOR_HASH_MISMATCH"),
        ("validator_format_valid", "RUN_CARD_VALIDATOR_NOT_FORMAT_VALID"),
        ("verdict_promote", "RUN_CARD_NOT_PROMOTED"),
        ("submission_authorized", "RUN_CARD_NOT_AUTHORIZED"),
    ):
        if not base[field]:
            base["reason_codes"].append(code)
    # Card booleans are assertions, not evidence of the underlying holdout,
    # canary, novelty, nuisance-audit and live-quota gates. No independent
    # selector receipt verifier exists yet. Reserve positive authorization for
    # that implementation; never grant it from a fabricated promote flag.
    base["reason_codes"].append("INDEPENDENT_SELECTOR_EVIDENCE_REQUIRED")
    base["scientific_authorization"] = False
    return base


def _note_evidence(note: str | None) -> dict[str, Any]:
    present = isinstance(note, str) and bool(note.strip())
    length = len(note) if isinstance(note, str) else None
    return {
        "present": present,
        "characters": length,
        "limit": NOTE_LIMIT,
        "within_limit": bool(present and length is not None and length <= NOTE_LIMIT),
    }


def preflight(
    artifact_path: Path | str,
    template_path: Path | str,
    *,
    run_card_path: Path | str | None = None,
    note: str | None = None,
    expected_template_sha256: str | None = None,
) -> dict[str, Any]:
    """Inspect exact bytes and return a hash-bound, machine-readable decision.

    ``expected_template_sha256`` is optional for generic use.  Without it, the
    report refuses to label the template as pinned and consequently cannot emit
    ``OK_TO_SUBMIT``.  This prevents a self-consistent arbitrary template from
    being mistaken for the competition template.
    """
    artifact, template = Path(artifact_path), Path(template_path)
    run_card = Path(run_card_path) if run_card_path is not None else None
    if not artifact.is_file():
        raise FileNotFoundError(f"Artifact does not exist: {artifact}")
    if not template.is_file():
        raise FileNotFoundError(f"Template does not exist: {template}")

    artifact_sha256 = sha256_file(artifact)
    template_sha256 = sha256_file(template)
    checks = submission.check_variants(artifact, template)
    strict_range = checks["checks"]["variant_strict_whole_array_no_nan_allowed"]["pass"]
    template_pinned = (
        expected_template_sha256 is not None and template_sha256 == expected_template_sha256
    )
    card = _card_evidence(artifact, artifact_sha256, run_card)
    chosen_note = note if note is not None else card["note"]
    note_check = _note_evidence(chosen_note)

    format_ok = checks["format_valid"] is True and artifact.suffix.lower() == ".tif"
    requirements = {
        "single_tif_and_footprint_format": format_ok,
        "strict_whole_array_values_in_0_1": bool(strict_range),
        "pinned_template_bytes": template_pinned,
        "short_note_present_and_at_most_140_characters": note_check["within_limit"],
        "hash_bound_scientific_promotion": card["scientific_authorization"],
    }
    blockers = [name for name, passed in requirements.items() if not passed]
    if not requirements["strict_whole_array_values_in_0_1"]:
        blockers.append("portal_global_range_compatibility_is_not_demonstrated")
    if not card["scientific_authorization"]:
        blockers.extend(card["reason_codes"])
    # Preserve a deterministic order while not repeating codes.
    blockers = list(dict.fromkeys(blockers))
    ready = not blockers
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact": {
            "file": artifact.name,
            "sha256": artifact_sha256,
            "bytes": artifact.stat().st_size,
            "is_tif": artifact.suffix.lower() == ".tif",
        },
        "template": {
            "file": template.name,
            "sha256": template_sha256,
            "expected_sha256": expected_template_sha256,
            "pinned_bytes_match": template_pinned,
            "provenance_limit": (
                "A pinned mirror verifies local byte identity, not independent organizer authentication."
            ),
        },
        "format_validation": checks,
        "portal_range_diagnostic": {
            "strict_whole_array_values_in_0_1": bool(strict_range),
            "meaning": (
                "Passes ((array >= 0) & (array <= 1)).all() over every stored value; "
                "a NaN-outside template encoding does not pass this stricter diagnostic."
            ),
            "limit": (
                "This is a compatibility diagnostic after the reported range error, not a claim "
                "that the organizer portal will accept the file or an explanation of past rejection."
            ),
        },
        "run_card": card,
        "note": {**note_check, "value": chosen_note},
        "requirements": requirements,
        "decision": {
            "download_status": "FORMAT_VALID_RESEARCH_DOWNLOAD"
            if checks["format_valid"]
            else "FORMAT_INVALID_DO_NOT_USE",
            "submission_status": "OK_TO_SUBMIT" if ready else "DO_NOT_SUBMIT",
            "ready_to_submit": ready,
            "blockers": blockers,
            "scope": (
                "No portal upload occurs. OK_TO_SUBMIT is a local evidence decision, not an "
                "organizer receipt or a leaderboard score."
            ),
        },
    }


def concise_status(report: dict[str, Any]) -> str:
    """Return a terminal-safe status line that cannot be confused with a score."""
    decision = report["decision"]
    return (
        f"FORMAT: {report['format_validation']['format_valid']} | "
        f"STRICT_RANGE: {report['portal_range_diagnostic']['strict_whole_array_values_in_0_1']} | "
        f"SCIENTIFIC_AUTHORIZATION: {report['run_card']['scientific_authorization']} | "
        f"SUBMISSION: {decision['submission_status']}"
    )
