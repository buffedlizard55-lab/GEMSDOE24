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
    return {
        "raster_sha256": sha256_file(artifact),
        "submission_name": "cand-zeros.tif",
        "leakage_canary": {"passed": True, "worst_polarity_extremity": 0.71},
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
            "surface": {"max_abs_rank_correlation": 0.4, "literal_all_entries_passed": True},
            "final_dots": {
                "max_abs_rank_correlation": 0.4,
                "method_lane_max_dot_overlap": 0.5,
                "method_lane_passed": True,
                "literal_all_entries_passed": True,
                "literal_duplicate_rows": [],
            },
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
