"""Fail-closed promotion checks, independent from GeoTIFF format validation."""

from __future__ import annotations


def require_candidate_evidence(source_sha256: str, experiment: dict, audit: dict) -> dict:
    decision = experiment.get("decision", {})
    ref = experiment.get("experimental_raster", {})
    references = audit.get("references", {})
    candidate = references.get("candidate", {})
    rules = {
        "fresh_experiment_complete": experiment.get("complete_run") is True,
        "paired_retraining_gains": decision.get("candidate_beats_paired_baselines") is True,
        "beats_both_historical_diagnostics": decision.get("candidate_beats_historical_diagnostics")
        is True,
        "comparable_current_best_holdout_reproduced": decision.get(
            "original_h19_holdout_reproduced"
        )
        is True,
        "explicit_promotion_decision": decision.get("promoted") is True,
        "training_only_nuisance_removal": experiment.get("protocol", {}).get(
            "nuisance_training_only"
        )
        is True,
        "same_experimental_file": ref.get("sha256") == source_sha256,
        "audit_complete_run": audit.get("complete_run") is True,
        "all_requested_source_families": audit.get("full_requested_audit_complete") is True,
        "labels_and_each_reference_audited": {"labels", "h19-4", "h19-5", "candidate"}
        <= set(references),
        "same_exact_candidate_audited": candidate.get("sha256") == source_sha256,
        "candidate_bias_gate_passed": candidate.get("full_requested_audit_gate_passed") is True,
        "labels_audited_first": audit.get("protocol", {}).get("labels_first") is True,
    }
    failures = [k for k, v in rules.items() if not v]
    if failures:
        raise ValueError("Candidate is NOT slot-eligible: " + ", ".join(failures))
    # A label/reference association need not disappear after a feature-level
    # intervention. Its detection requires mitigation + the candidate re-audit,
    # not falsely reporting that the catalogue itself has become unbiased.
    return {"passed": True, "rules": rules}
