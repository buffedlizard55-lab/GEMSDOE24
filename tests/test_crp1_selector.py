"""Unit tests for H24-CRP1 transforms and the independent selector."""

from __future__ import annotations

import numpy as np

from gems import crp1, selector


def test_saddle_strength_analytic():
    y, x = np.mgrid[-10:11, -10:11].astype(np.float32)
    valid = np.ones(x.shape, bool)
    # f = x^2 - y^2: Hessian determinant = -4 -> saddle strength 2.
    s = crp1.saddle_strength(x**2 - y**2, valid, 1.0)
    assert abs(float(s[10, 10]) - 2.0) < 1e-4
    # Pure ridge f = -x^2 has determinant 0 -> no saddle response.
    r = crp1.saddle_strength(-(x**2), valid, 1.0)
    assert float(r[10, 10]) == 0.0
    # Bowl f = x^2 + y^2 has positive determinant -> zero saddle response.
    b = crp1.saddle_strength(x**2 + y**2, valid, 1.0)
    assert float(b[10, 10]) == 0.0


def test_saddle_restores_nan_on_invalid():
    field = np.arange(25, dtype=np.float32).reshape(5, 5)
    valid = np.ones((5, 5), bool)
    valid[0, 0] = False
    out = crp1.saddle_strength(field, valid, 1.0)
    assert np.isnan(out[0, 0])
    assert np.isfinite(out[valid]).all()


def test_rank_score_and_footprint_rank():
    score, valid = crp1._rank_score(np.array([[0, 255], [128, 1]], dtype=np.uint8))
    assert np.isnan(score[0, 0]) and not valid[0, 0]
    assert np.isfinite(score[valid]).all()
    rk = crp1.footprint_rank(
        np.array([[3.0, 1.0], [2.0, 9.0]], dtype=np.float32), np.ones((2, 2), bool)
    )
    assert rk[0, 1] == 0.25 and rk[1, 1] == 1.0


def _passing_card(tmp_path, monkeypatch) -> dict:
    artifact = tmp_path / "cand-zeros.tif"
    artifact.write_bytes(b"fake")
    from gems.validator import sha256_file

    monkeypatch.setattr(
        selector.submission,
        "check_variants",
        lambda a, t: {
            "format_valid": True,
            "checks": {
                "variant_strict_whole_array_no_nan_allowed": {"pass": True},
                "footprint_range_0_1": {"pass": True},
                "footprint_all_finite": {"pass": True},
            },
        },
    )
    # Synthetic complete two-entry registry; no claim of actual scientific replay.
    required_hashes = frozenset({"a" * 64, "b" * 64})
    monkeypatch.setattr(selector, "_required_registry_footprints", lambda: required_hashes)

    def stage(name):
        is_final = name == "final_dots"
        return {
            "stage": name,
            "registry_unique_rasters": 2,
            "max_abs_rank_correlation": 0.4,
            "literal_all_entries_passed": True,
            "literal_duplicate_rows": [],
            "rows": [
                {
                    "footprint_sha256": digest,
                    "raw_spearman": 0.4,
                    "kernel_spearman": 0.2,
                    "candidate_dot_overlap_within_3px": 0.5 if is_final else None,
                    "duplicate": False,
                    "correlation_defined": True,
                }
                for digest in sorted(required_hashes)
            ],
            **(
                {
                    "max_dot_overlap": 0.5,
                    "method_lane_max_dot_overlap": 0.5,
                    "method_lane_passed": True,
                }
                if is_final
                else {}
            ),
        }

    return {
        "raster_sha256": sha256_file(artifact),
        "submission_name": "cand-zeros.tif",
        "leakage_canary": {
            "passed": True,
            "two_polarities_checked": True,
            "evaluator_version": selector.RECORDED_BEST_EVALUATOR,
            "n_features_checked": 1,
            "worst_polarity_extremity": 0.71,
            "features": {
                "test_feature": {
                    "pooled_auc": 0.71,
                    "pooled_presence_auc": 0.5,
                    "leakage_suspected": False,
                    "folds": [
                        {
                            "fold": name,
                            "auc": 0.6,
                            "presence_auc": 0.5,
                            "positives": 10,
                            "background": 10,
                        }
                        for name in selector.FOLD_NAMES
                    ],
                }
            },
        },
        "holdout": {
            "label": "HOLDOUT-DTI",
            "evaluator_version": selector.RECORDED_BEST_EVALUATOR,
            "dti": selector.RECORDED_BEST_DTI + 0.01,
            "n_withheld_positive_pixels": 60988,
        },
        "paired_vs_baseline": {"ci95": [0.001, 0.02]},
        "baseline_reproduced": True,
        "paired_vs_current_best": {
            "baseline_dti": selector.RECORDED_BEST_DTI,
            "evaluator_version": selector.RECORDED_BEST_EVALUATOR,
            "n_withheld_positive_pixels": 60988,
            "baseline_replayed": True,
            "ci95": [0.001, 0.02],
        },
        "novelty": {
            "surface": stage("surface_before_placement"),
            "final_dots": stage("final_dots"),
            "peers_final": {"max_dot_overlap_within_3px": 0.5, "passed": True},
        },
        "c2st_exact_file": {"strict_gate_passed": True, "labels_audited_first": True},
        "note": "short note",
        "experiments_run": 1,
        "submission_slots_used": 0,
    }


def test_recorded_gate_screen_never_authorizes_without_independent_replay_and_quota(
    tmp_path, monkeypatch
):
    card = _passing_card(tmp_path, monkeypatch)
    receipt = selector.verify_selector(tmp_path / "cand-zeros.tif", tmp_path / "t.tif", card)
    assert receipt["recorded_scientific_screen_passed"] is True
    assert receipt["ok_to_submit"] is False
    assert receipt["decision"] == "DO_NOT_SUBMIT"
    assert not receipt["gates"]["current_account_quota_independently_verified"]
    assert not receipt["gates"]["complete_independent_replay_certificate"]
    assert receipt["human_inspection_used"] is False
    assert receipt["quota_status"].startswith("unknown")


def test_selector_fails_closed_on_each_broken_gate(tmp_path, monkeypatch):
    base = _passing_card(tmp_path, monkeypatch)
    artifact = tmp_path / "cand-zeros.tif"

    def variant(**changes):
        import copy

        card = copy.deepcopy(base)
        for key, value in changes.items():
            target = card
            parts = key.split(".")
            for part in parts[:-1]:
                target = target[part]
            target[parts[-1]] = value
        return card

    cases = [
        variant(**{"holdout.dti": selector.RECORDED_BEST_DTI - 0.01}),
        variant(**{"paired_vs_baseline.ci95": [-0.001, 0.02]}),
        variant(**{"novelty.final_dots.method_lane_max_dot_overlap": 0.71}),
        variant(**{"novelty.final_dots.max_abs_rank_correlation": 0.91}),
        variant(**{"c2st_exact_file.strict_gate_passed": False}),
        variant(note="x" * 141),
        variant(experiments_run=4),
        variant(submission_slots_used=1),
        variant(raster_sha256="0" * 64),
        variant(
            **{
                "novelty.final_dots.literal_duplicate_rows": [
                    {"file": "docs/downloads/some-method.tif", "registry_id": "registry-001"}
                ]
            }
        ),
    ]
    for card in cases:
        receipt = selector.verify_selector(artifact, tmp_path / "t.tif", card)
        assert receipt["ok_to_submit"] is False, receipt["reasons"]
        assert receipt["decision"] == "DO_NOT_SUBMIT"
        assert receipt["recorded_scientific_screen_passed"] is False


def test_selector_missing_evidence_fails_closed(tmp_path, monkeypatch):
    card = _passing_card(tmp_path, monkeypatch)
    del card["novelty"]
    receipt = selector.verify_selector(tmp_path / "cand-zeros.tif", tmp_path / "t.tif", card)
    assert receipt["ok_to_submit"] is False
    assert any("g4" in r for r in receipt["reasons"])


def test_literal_calibration_duplicates_cannot_be_excluded(tmp_path, monkeypatch):
    card = _passing_card(tmp_path, monkeypatch)
    card["novelty"]["final_dots"]["literal_duplicate_rows"] = [
        {
            "file": "inputs/calibration/13gems_20261001_r13-lattice-s5_v2_nan-outside.tif",
            "registry_id": "registry-039",
        }
    ]
    result = selector.verify_selector(tmp_path / "cand-zeros.tif", tmp_path / "t.tif", card)
    assert result["gates"]["g4_registry_novelty"] is False
    assert result["recorded_scientific_screen_passed"] is False


def test_easy_baseline_win_cannot_replace_current_best_paired_evidence(tmp_path, monkeypatch):
    card = _passing_card(tmp_path, monkeypatch)
    del card["paired_vs_current_best"]
    result = selector.verify_selector(tmp_path / "cand-zeros.tif", tmp_path / "t.tif", card)
    assert result["gates"]["g3_holdout_beats_recorded_best_and_paired_baseline"] is False


def test_quota_flags_and_human_confirmation_never_override_missing_verifier(tmp_path, monkeypatch):
    card = _passing_card(tmp_path, monkeypatch)
    card.update(quota_confirmed=True, human_inspected=True, independent_selector_verified=True)
    result = selector.verify_selector(tmp_path / "cand-zeros.tif", tmp_path / "t.tif", card)
    assert result["recorded_scientific_screen_passed"] is True
    assert not result["gates"]["current_account_quota_independently_verified"]
    assert not result["gates"]["complete_independent_replay_certificate"]
    assert result["ok_to_submit"] is False


def test_unknown_or_false_literal_gate_is_not_vacuously_successful(tmp_path, monkeypatch):
    card = _passing_card(tmp_path, monkeypatch)
    del card["novelty"]["surface"]["literal_all_entries_passed"]
    result = selector.verify_selector(tmp_path / "cand-zeros.tif", tmp_path / "t.tif", card)
    assert result["gates"]["g4_registry_novelty"] is False


def test_historical_gate_compatibility_only_allows_documented_stricter_changes():
    old = {
        "g1_format_strict_0_1": True,
        "g2_leakage_canary": True,
        "g3_holdout_beats_recorded_best_and_paired_baseline": False,
        "g4_registry_novelty": True,
        "g5_exact_file_c2st": True,
    }
    assert selector.recorded_gates_compatible(old, old.copy())
    strict = dict(old, g2_leakage_canary=False, g4_registry_novelty=False)
    assert selector.recorded_gates_compatible(old, strict)
    assert not selector.recorded_gates_compatible(strict, old)
    assert not selector.recorded_gates_compatible(old, dict(old, g5_exact_file_c2st=False))
    assert not selector.recorded_gates_compatible(old, dict(old, g2_leakage_canary=1))
    assert not selector.recorded_gates_compatible(old, {"g2_leakage_canary": False})
    changed_best = dict(old, g3_holdout_beats_recorded_best_and_paired_baseline=True)
    assert not selector.recorded_gates_compatible(old, changed_best)
    assert selector.recorded_gates_compatible(old, changed_best, allow_benchmark_change=True)


def test_canary_gate_requires_actual_value_and_missingness_rows(tmp_path, monkeypatch):
    import copy

    base = _passing_card(tmp_path, monkeypatch)
    assert selector._recorded_canary_passed(base["leakage_canary"])
    for mutate in (
        lambda c: c["leakage_canary"].update(features={}, n_features_checked=0),
        lambda c: c["leakage_canary"].update(n_features_checked=2),
        lambda c: c["leakage_canary"].update(worst_polarity_extremity=0.6),
        lambda c: c["leakage_canary"]["features"]["test_feature"].update(pooled_presence_auc=0.99),
        lambda c: c["leakage_canary"]["features"]["test_feature"]["folds"].pop(),
        lambda c: c["leakage_canary"]["features"]["test_feature"]["folds"][0].update(auc=0.01),
        lambda c: c["leakage_canary"]["features"]["test_feature"]["folds"][0].pop("presence_auc"),
    ):
        bad = copy.deepcopy(base)
        mutate(bad)
        assert not selector._recorded_canary_passed(bad["leakage_canary"])
        result = selector.verify_selector(tmp_path / "cand-zeros.tif", tmp_path / "t.tif", bad)
        assert result["gates"]["g2_leakage_canary"] is False
        assert result["ok_to_submit"] is False


def test_literal_gate_requires_nonvacuous_matching_full_registry_rows(tmp_path, monkeypatch):
    import copy

    base = _passing_card(tmp_path, monkeypatch)
    assert selector._literal_novelty_passed(base)
    for mutate in (
        lambda c: c["novelty"]["surface"].update(rows=[], registry_unique_rasters=0),
        lambda c: c["novelty"]["surface"]["rows"].pop(),
        lambda c: c["novelty"]["final_dots"]["rows"].pop(),
        lambda c: c["novelty"]["final_dots"]["rows"][0].update(duplicate=True),
        lambda c: c["novelty"]["final_dots"]["rows"][0].update(
            candidate_dot_overlap_within_3px=0.71
        ),
        lambda c: c["novelty"]["surface"]["rows"][0].update(raw_spearman=-0.91),
        lambda c: c["novelty"]["surface"]["rows"][0].update(correlation_defined=False),
        lambda c: c["novelty"]["surface"].update(max_abs_rank_correlation=0.1),
        lambda c: c["novelty"]["final_dots"].update(max_dot_overlap=0.1),
        lambda c: c["novelty"]["final_dots"]["rows"][0].update(footprint_sha256="c" * 64),
        lambda c: c["novelty"]["surface"].update(stage="final_dots"),
    ):
        bad = copy.deepcopy(base)
        mutate(bad)
        assert not selector._literal_novelty_passed(bad)
        result = selector.verify_selector(tmp_path / "cand-zeros.tif", tmp_path / "t.tif", bad)
        assert result["gates"]["g4_registry_novelty"] is False
        assert result["ok_to_submit"] is False
    monkeypatch.setattr(selector, "_required_registry_footprints", lambda: None)
    assert not selector._literal_novelty_passed(base)


def test_nonfinite_performance_and_negative_experiment_count_fail_named_gates(
    tmp_path, monkeypatch
):
    for field in (float("nan"), float("inf"), -1, True):
        card = _passing_card(tmp_path, monkeypatch)
        card["holdout"]["dti"] = field
        result = selector.verify_selector(tmp_path / "cand-zeros.tif", tmp_path / "t.tif", card)
        assert result["gates"]["g3_holdout_beats_recorded_best_and_paired_baseline"] is False
    card = _passing_card(tmp_path, monkeypatch)
    card["experiments_run"] = -1
    result = selector.verify_selector(tmp_path / "cand-zeros.tif", tmp_path / "t.tif", card)
    assert result["gates"]["budget_and_no_slot_spent"] is False


def test_malformed_numeric_evidence_cannot_pass_individual_gates(tmp_path, monkeypatch):
    """A negative overall verdict must not conceal an incorrectly green subgate."""
    cases = {
        "g2_leakage_canary": [
            ("leakage_canary.worst_polarity_extremity", v)
            for v in ("0.71", True, float("nan"), float("inf"))
        ],
        "g3_holdout_beats_recorded_best_and_paired_baseline": [
            ("paired_vs_baseline.ci95", v)
            for v in ([0.02, 0.01], [0.01], [0.01, float("nan")], [True, 1], ["0.01", 1])
        ]
        + [("holdout.n_withheld_positive_pixels", 60988.5)],
        "g4_registry_novelty": [
            (f"novelty.{field}", v)
            for field in (
                "surface.max_abs_rank_correlation",
                "final_dots.max_abs_rank_correlation",
                "final_dots.method_lane_max_dot_overlap",
                "peers_final.max_dot_overlap_within_3px",
            )
            for v in (-0.1, float("-inf"), float("nan"), "0.4", False, 10**400)
        ],
        "budget_and_no_slot_spent": [("submission_slots_used", v) for v in (0.5, "0", False)],
    }
    for gate, mutations in cases.items():
        for path, value in mutations:
            card = _passing_card(tmp_path, monkeypatch)
            target = card
            parts = path.split(".")
            for key in parts[:-1]:
                target = target[key]
            target[parts[-1]] = value
            result = selector.verify_selector(tmp_path / "cand-zeros.tif", tmp_path / "t.tif", card)
            assert result["gates"][gate] is False, (path, value)
            assert result["recorded_scientific_screen_passed"] is False
            assert result["ok_to_submit"] is False


def test_non_object_gate_sections_return_negative_instead_of_crashing(tmp_path, monkeypatch):
    for field in (
        "leakage_canary",
        "holdout",
        "paired_vs_current_best",
        "novelty",
        "c2st_exact_file",
    ):
        card = _passing_card(tmp_path, monkeypatch)
        card[field] = []
        result = selector.verify_selector(tmp_path / "cand-zeros.tif", tmp_path / "t.tif", card)
        assert result["recorded_scientific_screen_passed"] is False
        assert result["ok_to_submit"] is False


def test_review_notice_and_no_unjustified_cross_site_superiority():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    for name in (
        "index.html",
        "executive-summary.html",
        "docs/index.html",
        "docs/executive-summary.html",
    ):
        html = (root / name).read_text()
        assert "Current review: no submission-authorized TIFF." in html
        assert "review-20261026.md" in html
        assert "STRONGEST UNSCORED UNIQUE CANDIDATE ACROSS ALL 9 SITES" not in html
        assert "Pixel-level distance forensics proved" not in html
        assert "TNR1 0.12352" not in html
