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


def require_postprocess_evidence(
    pinned_reference_sha256: str,
    candidate_sha256: str,
    candidate_recomputed_exactly: bool,
    validation: dict,
    audit: dict,
    *,
    relative_auc_tolerance: float = 0.01,
) -> dict:
    """Evidence for a label-free, deterministic subset transform of one pinned scored reference.

    This is NOT the retraining rule (``require_candidate_evidence``): nothing is retrained, so there is no
    out-of-fold model to reproduce. The transform reads no labels or scores, the candidate must be an exact
    recomputation from the pinned reference, the preregistered paired gates must all pass on the same truths,
    and the exact file must be audited with every requested nuisance family, labels first.

    The owner's *strict* accessibility gate (meaningful association => fail) is reported separately and is
    never rewritten. ``slot_recommendation`` is ``eligible`` only if that strict gate passes;
    ``owner_decision_required`` if it fails but the candidate is no more nuisance-associated than its own
    reference (within ``relative_auc_tolerance``, a declared criterion, not the owner's); otherwise
    ``not_recommended``.
    """
    gates = validation.get("selection_and_gates", {})
    cand = validation.get("candidate", {})
    refs = audit.get("references", {})
    cand_audit = refs.get("candidate", {})
    ref_audit = refs.get("h19-5", {})
    rules = {
        "reference_is_the_pinned_scored_raster": validation.get("sources", {})
        .get("h19_5", {})
        .get("sha256")
        == pinned_reference_sha256,
        "candidate_is_exact_deterministic_recomputation": bool(candidate_recomputed_exactly),
        "transform_reads_no_labels_or_scores": validation.get("protocol", {}).get(
            "transform_reads_labels_or_scores"
        )
        is False,
        "preregistered_paired_gates_all_passed": gates.get("eligible") is True,
        "validated_file_is_this_file": cand.get("sha256") == candidate_sha256,
        "audit_complete_run": audit.get("complete_run") is True,
        "all_requested_source_families": audit.get("full_requested_audit_complete") is True,
        "labels_audited_first": audit.get("protocol", {}).get("labels_first") is True,
        "same_exact_candidate_audited": cand_audit.get("sha256") == candidate_sha256,
    }
    failures = [k for k, v in rules.items() if not v]
    if failures:
        raise ValueError("Post-process candidate is NOT eligible: " + ", ".join(failures))
    strict = cand_audit.get("full_requested_audit_gate_passed") is True
    cand_auc = cand_audit["primary"]["observed_auc"]
    ref_auc = ref_audit["primary"]["observed_auc"]
    relative_ok = cand_auc <= ref_auc + relative_auc_tolerance
    if strict:
        recommendation = "eligible"
    elif relative_ok:
        recommendation = "owner_decision_required"
    else:
        recommendation = "not_recommended"
    return {
        "passed": True,
        "rules": rules,
        "strict_owner_audit_gate_passed": strict,
        "relative_audit": {
            "candidate_auc": cand_auc,
            "reference_auc": ref_auc,
            "tolerance": relative_auc_tolerance,
            "not_worse_than_reference": bool(relative_ok),
        },
        "slot_recommendation": recommendation,
        "note": "Local gates are necessary, not sufficient: proxy-vs-live rank correlations measured this session are weak.",
    }
