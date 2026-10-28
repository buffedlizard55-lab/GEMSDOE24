"""Format checks cannot silently become an upload/scientific promotion gate."""

import hashlib
import zipfile

import numpy as np
import pytest
import rasterio
from rasterio.transform import Affine

from gems import submission
from gems.promotion import require_candidate_evidence


def template(tmp_path):
    p = tmp_path / "template.tif"
    a = np.zeros((16, 20), np.float32)
    a[:2] = np.nan
    with rasterio.open(
        p,
        "w",
        driver="GTiff",
        height=16,
        width=20,
        count=1,
        dtype="float32",
        crs="EPSG:32611",
        transform=Affine(100, 0, 243350, 0, -100, 4508550),
        nodata=np.nan,
    ) as s:
        s.write(a, 1)
    return p, np.isfinite(a)


def test_writer_defaults_to_all_finite_zero_outside_and_preserves_source(tmp_path):
    t, fp = template(tmp_path)
    a = np.full(fp.shape, 0.7, np.float32)
    old = a.copy()
    p = submission.write_submission(a, t, tmp_path / "out.tif")
    with rasterio.open(p) as d:
        b = d.read(1)
        assert d.count == 1 and d.dtypes == ("float32",) and d.crs.to_epsg() == 32611
        assert np.isfinite(b).all() and np.all(b[~fp] == 0)
        assert d.nodata is None
    checks = submission.check_variants(p, t)
    assert checks["checks"]["variant_strict_whole_array_no_nan_allowed"]["pass"]
    assert np.array_equal(a, old)


def test_writer_nan_outside_is_explicit_compatibility_twin(tmp_path):
    t, fp = template(tmp_path)
    p = submission.write_submission(
        np.full(fp.shape, 0.7, np.float32), t, tmp_path / "nan-twin.tif", outside="nan"
    )
    with rasterio.open(p) as d:
        b = d.read(1)
        assert np.isfinite(b[fp]).all() and np.isnan(b[~fp]).all()
        assert np.isnan(d.nodata)
    checks = submission.check_variants(p, t)
    assert not checks["checks"]["variant_strict_whole_array_no_nan_allowed"]["pass"]


@pytest.mark.parametrize("value", [np.nan, np.inf, -np.inf, -0.01, 1.01])
def test_invalid_inside_probabilities_are_not_silently_clipped(tmp_path, value):
    t, fp = template(tmp_path)
    a = np.full(fp.shape, value)
    with pytest.raises(ValueError, match="finite and in"):
        submission.write_submission(a, t, tmp_path / "bad.tif")
    assert not (tmp_path / "bad.tif").exists()


def test_same_wrong_template_and_prediction_cannot_certify_organizer_grid(tmp_path):
    t, fp = template(tmp_path)
    p = submission.write_submission(np.ones(fp.shape), t, tmp_path / "out.tif")
    checks = submission.check_variants(p, t)
    assert checks["checks"]["shape_matches_template"]["pass"]
    assert not checks["checks"]["official_template_grid_and_footprint"]["pass"]
    assert not checks["format_valid"] and not checks["ok_to_upload"]


def test_all_finite_fallback_is_in_range_even_under_strict_whole_array_reader(tmp_path):
    t, fp = template(tmp_path)
    p = submission.write_submission(np.ones(fp.shape), t, tmp_path / "out.tif", outside="zero")
    checks = submission.check_variants(p, t)
    assert checks["checks"]["variant_strict_whole_array_no_nan_allowed"]["pass"]
    assert not checks["official_format_compliant"]


def test_sanitizer_is_an_explicit_operation_not_an_implicit_training_fix():
    a = submission.sanitize(np.array([np.nan, np.inf, -np.inf, -1, 0.5, 2]))
    assert list(a) == [0, 1, 0, 0, 0.5, 1] and a.dtype == np.float32


def test_soft_scored_content_id_avoids_binary_threshold_collision_and_ignores_masked_pixels():
    fp = np.ones((6, 6), bool)
    fp[0] = False
    cat = np.zeros_like(fp)
    cat[3, 3] = True
    a = np.full(fp.shape, 0.2)
    b = np.full(fp.shape, 0.4)
    assert submission.scored_content_id(a, fp, cat) != submission.scored_content_id(b, fp, cat)
    b = a.copy()
    b[~fp] = np.nan
    b[cat] = 1
    assert submission.scored_content_id(a, fp, cat) == submission.scored_content_id(b, fp, cat)
    b[2, 2] = np.inf
    with pytest.raises(ValueError):
        submission.scored_content_id(b, fp, cat)


def test_zip_has_one_flat_tif_with_identical_bytes_and_note_is_not_inside(tmp_path):
    t, fp = template(tmp_path)
    p = submission.write_submission(np.ones(fp.shape), t, tmp_path / "prediction.tif")
    z = submission.zip_single(p)
    with zipfile.ZipFile(z) as archive:
        assert archive.namelist() == [p.name]
        assert (
            hashlib.sha256(archive.read(p.name)).digest() == hashlib.sha256(p.read_bytes()).digest()
        )


def test_note_names_reference_and_never_falsely_calls_it_a_new_score():
    note = submission.make_note("reference-h19-5", "x" * 500, "123456789abc", reference=True)
    assert len(note) <= 140 and "reference, no new score" in note
    assert "not yet live-scored" not in note


def test_note_helper_enforces_the_project_140_character_limit():
    note = submission.make_note("h24-safe", "x" * 500, "123456789abc")
    assert len(note) == 140
    with pytest.raises(ValueError, match="140-character"):
        submission.make_note("x" * 200, "summary", "y" * 64)


def complete_evidence():
    exp = {
        "complete_run": True,
        "decision": {
            "candidate_beats_paired_baselines": True,
            "candidate_beats_historical_diagnostics": True,
            "original_h19_holdout_reproduced": True,
            "promoted": True,
        },
        "protocol": {"nuisance_training_only": True},
        "experimental_raster": {"sha256": "abc"},
    }
    audit = {
        "complete_run": True,
        "full_requested_audit_complete": True,
        "protocol": {"labels_first": True},
        "references": {
            "labels": {},
            "h19-4": {},
            "h19-5": {},
            "candidate": {"sha256": "abc", "full_requested_audit_gate_passed": True},
        },
    }
    return exp, audit


def test_promotion_fails_closed_for_missing_blocks_or_unreproduced_current_best():
    exp, audit = complete_evidence()
    assert require_candidate_evidence("abc", exp, audit)["passed"]
    for key in list(exp["decision"]):
        exp, audit = complete_evidence()
        exp["decision"][key] = False
        with pytest.raises(ValueError):
            require_candidate_evidence("abc", exp, audit)
    exp, audit = complete_evidence()
    audit["full_requested_audit_complete"] = False
    with pytest.raises(ValueError, match="all_requested"):
        require_candidate_evidence("abc", exp, audit)


def test_audit_of_different_file_or_no_training_mitigation_cannot_authorize_new_slot():
    exp, audit = complete_evidence()
    with pytest.raises(ValueError, match="same_exact_candidate"):
        require_candidate_evidence("wrong-file", exp, audit)
    exp["protocol"]["nuisance_training_only"] = False
    with pytest.raises(ValueError, match="training_only"):
        require_candidate_evidence("abc", exp, audit)
    with pytest.raises(ValueError):
        require_candidate_evidence("abc", {}, {})


def _post_inputs(strict=False, cand_auc=0.55, ref_auc=0.556, gates_ok=True):
    validation = {
        "sources": {"h19_5": {"sha256": "ref"}},
        "protocol": {"transform_reads_labels_or_scores": False},
        "selection_and_gates": {"eligible": gates_ok},
        "candidate": {"sha256": "cand"},
    }
    audit = {
        "complete_run": True,
        "full_requested_audit_complete": True,
        "protocol": {"labels_first": True},
        "references": {
            "candidate": {
                "sha256": "cand",
                "primary": {"observed_auc": cand_auc},
                "full_requested_audit_gate_passed": strict,
            },
            "h19-5": {"primary": {"observed_auc": ref_auc}},
        },
    }
    return validation, audit


def test_postprocess_requires_exact_recomputation_and_all_gates():
    from gems.promotion import require_postprocess_evidence

    v, a = _post_inputs()
    with pytest.raises(ValueError, match="exact_deterministic_recomputation"):
        require_postprocess_evidence("ref", "cand", False, v, a)
    v, a = _post_inputs(gates_ok=False)
    with pytest.raises(ValueError, match="paired_gates"):
        require_postprocess_evidence("ref", "cand", True, v, a)
    v, a = _post_inputs()
    with pytest.raises(ValueError, match="reference_is_the_pinned"):
        require_postprocess_evidence("other", "cand", True, v, a)
    a["references"]["candidate"]["sha256"] = "different"
    with pytest.raises(ValueError, match="same_exact_candidate_audited"):
        require_postprocess_evidence("ref", "cand", True, v, a)


def test_postprocess_never_rewrites_the_owner_strict_gate():
    from gems.promotion import require_postprocess_evidence

    v, a = _post_inputs(strict=False, cand_auc=0.553, ref_auc=0.556)
    out = require_postprocess_evidence("ref", "cand", True, v, a)
    assert out["strict_owner_audit_gate_passed"] is False
    assert out["slot_recommendation"] == "owner_decision_required"
    v, a = _post_inputs(strict=False, cand_auc=0.60, ref_auc=0.556)
    assert (
        require_postprocess_evidence("ref", "cand", True, v, a)["slot_recommendation"]
        == "not_recommended"
    )
    v, a = _post_inputs(strict=True, cand_auc=0.52, ref_auc=0.556)
    assert (
        require_postprocess_evidence("ref", "cand", True, v, a)["slot_recommendation"] == "eligible"
    )


def test_postprocess_audit_label_selects_the_right_reference_entry():
    from gems.promotion import require_postprocess_evidence

    v, a = _post_inputs(strict=False, cand_auc=0.553, ref_auc=0.556)
    a["references"]["candidate_alt"] = {
        "sha256": "alt",
        "primary": {"observed_auc": 0.60},
        "full_requested_audit_gate_passed": False,
    }
    v["candidate"]["sha256"] = "alt"
    out = require_postprocess_evidence("ref", "alt", True, v, a, candidate_label="candidate_alt")
    assert out["slot_recommendation"] == "not_recommended"  # judged on ITS audit, not the primary's
    with pytest.raises(ValueError, match="same_exact_candidate_audited"):
        require_postprocess_evidence("ref", "alt", True, v, a)  # default label points at "cand"


def _pin_test_template(monkeypatch, fp):
    # Use a miniature grid so these tests exercise the complete format decision.
    monkeypatch.setitem(submission.EXPECTED, "shape", fp.shape)
    monkeypatch.setitem(submission.EXPECTED, "footprint_pixels", int(fp.sum()))
    monkeypatch.setitem(submission.EXPECTED, "footprint_sha256", submission.footprint_sha256(fp))


def test_nodata_masks_inside_are_not_accepted_as_valid_probabilities(tmp_path, monkeypatch):
    t, fp = template(tmp_path)
    _pin_test_template(monkeypatch, fp)
    p = submission.write_submission(np.full(fp.shape, 0.7), t, tmp_path / "out.tif")
    with rasterio.open(p, "r+") as dataset:
        a = dataset.read(1)
        a[3, 3] = 0
        dataset.write(a, 1)
        dataset.nodata = 0
    checks = submission.check_variants(p, t, strict=True)
    assert checks["checks"]["footprint_all_finite"]["pass"]
    assert checks["checks"]["variant_strict_whole_array_no_nan_allowed"]["pass"]
    assert not checks["checks"]["footprint_unmasked"]["pass"]
    assert not checks["format_valid"] and "footprint_unmasked" in checks["hard_failures"]


def test_internal_mask_inside_is_rejected_even_without_nodata(tmp_path, monkeypatch):
    t, fp = template(tmp_path)
    _pin_test_template(monkeypatch, fp)
    p = submission.write_submission(np.full(fp.shape, 0.7), t, tmp_path / "out.tif")
    mask = np.full(fp.shape, 255, dtype=np.uint8)
    mask[4, 4] = 0
    with rasterio.Env(GDAL_TIFF_INTERNAL_MASK=True), rasterio.open(p, "r+") as dataset:
        dataset.write_mask(mask)
    checks = submission.check_variants(p, t, strict=True)
    assert checks["checks"]["variant_masked_read"]["pass"]
    assert not checks["checks"]["footprint_unmasked"]["pass"]
    assert not checks["format_valid"]


def test_geotiff_extension_cannot_disguise_a_vrt(tmp_path, monkeypatch):
    from rasterio.shutil import copy as rio_copy

    t, fp = template(tmp_path)
    _pin_test_template(monkeypatch, fp)
    source = submission.write_submission(np.full(fp.shape, 0.7), t, tmp_path / "source.tif")
    disguised = tmp_path / "not-a-geotiff.tif"
    rio_copy(source, disguised, driver="VRT")
    checks = submission.check_variants(disguised, t, strict=True)
    assert checks["checks"]["single_band"]["pass"]
    assert checks["checks"]["footprint_unmasked"]["pass"]
    assert not checks["checks"]["geotiff_driver"]["pass"]
    assert not checks["format_valid"] and "geotiff_driver" in checks["hard_failures"]


def test_masking_only_exterior_does_not_fail_interior_gate(tmp_path, monkeypatch):
    t, fp = template(tmp_path)
    _pin_test_template(monkeypatch, fp)
    p = submission.write_submission(np.full(fp.shape, 0.7), t, tmp_path / "out.tif")
    with rasterio.open(p, "r+") as dataset:
        dataset.nodata = 0
    checks = submission.check_variants(p, t, strict=True)
    assert checks["checks"]["footprint_unmasked"]["pass"]
    assert checks["format_valid"]


def test_preflight_applies_strict_mask_and_driver_checks(tmp_path, monkeypatch):
    from gems.preflight import preflight

    t, fp = template(tmp_path)
    _pin_test_template(monkeypatch, fp)
    p = submission.write_submission(np.full(fp.shape, 0.7), t, tmp_path / "out.tif")
    with rasterio.open(p, "r+") as dataset:
        a = dataset.read(1)
        a[3, 3] = 0
        dataset.write(a, 1)
        dataset.nodata = 0
    report = preflight(p, t)
    checks = report["format_validation"]["checks"]
    assert checks["geotiff_driver"]["pass"]
    assert not checks["footprint_unmasked"]["pass"]
    assert not report["requirements"]["single_tif_and_footprint_format"]
    assert not report["decision"]["ready_to_submit"]


def test_strict_check_rejects_external_mask_even_when_all_pixels_valid(tmp_path, monkeypatch):
    t, fp = template(tmp_path)
    _pin_test_template(monkeypatch, fp)
    p = submission.write_submission(np.full(fp.shape, 0.7), t, tmp_path / "out.tif")
    with rasterio.Env(GDAL_TIFF_INTERNAL_MASK=False), rasterio.open(p, "r+") as dataset:
        dataset.write_mask(np.full(fp.shape, 255, np.uint8))
    assert (tmp_path / "out.tif.msk").exists()
    checks = submission.check_variants(p, t, strict=True)
    assert checks["checks"]["footprint_unmasked"]["pass"]
    assert not checks["checks"]["raster_self_contained"]["pass"]
    assert not checks["format_valid"]


def test_writer_refuses_stale_sidecar_and_masked_input(tmp_path):
    t, fp = template(tmp_path)
    output = tmp_path / "out.tif"
    sidecar = tmp_path / "out.tif.msk"
    sidecar.write_bytes(b"do not remove")
    with pytest.raises(ValueError, match="sidecar"):
        submission.write_submission(np.ones(fp.shape), t, output)
    assert sidecar.read_bytes() == b"do not remove" and not output.exists()
    sidecar.unlink()
    masked = np.ma.array(np.ones(fp.shape), mask=np.zeros(fp.shape, dtype=bool))
    masked.mask[3, 3] = True
    with pytest.raises(ValueError, match="must not be masked"):
        submission.write_submission(masked, t, output)
    assert not output.exists()


def test_masked_template_is_rejected_by_writer_and_strict_validator(tmp_path, monkeypatch):
    t, fp = template(tmp_path)
    _pin_test_template(monkeypatch, fp)
    p = submission.write_submission(np.full(fp.shape, 0.7), t, tmp_path / "out.tif")
    mask = np.full(fp.shape, 255, dtype=np.uint8)
    mask[3, 3] = 0
    with rasterio.Env(GDAL_TIFF_INTERNAL_MASK=True), rasterio.open(t, "r+") as dataset:
        dataset.write_mask(mask)
    checks = submission.check_variants(p, t, strict=True)
    assert not checks["checks"]["template_footprint_unmasked"]["pass"]
    with pytest.raises(ValueError, match="Template contains masked"):
        submission.write_submission(np.ones(fp.shape), t, tmp_path / "new.tif")
