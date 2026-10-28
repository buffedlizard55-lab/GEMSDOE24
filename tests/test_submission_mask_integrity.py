"""Finite pixels can still be NoData; a single TIFF must carry its own validity mask."""

import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import Affine

from gems import submission

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def tiny_grid(tmp_path, monkeypatch):
    template = tmp_path / "template.tif"
    values = np.zeros((6, 7), dtype="float32")
    values[0, :] = np.nan
    transform = Affine(100, 0, 243350, 0, -100, 4508550)
    profile = {
        "driver": "GTiff",
        "height": values.shape[0],
        "width": values.shape[1],
        "count": 1,
        "dtype": "float32",
        "crs": "EPSG:32611",
        "transform": transform,
        "nodata": np.nan,
    }
    with rasterio.open(template, "w", **profile) as dataset:
        dataset.write(values, 1)
    footprint = np.isfinite(values)
    expected = dict(submission.EXPECTED)
    expected.update(
        shape=values.shape,
        transform=tuple(transform)[:6],
        footprint_pixels=int(footprint.sum()),
        footprint_sha256=submission.footprint_sha256(footprint),
    )
    monkeypatch.setattr(submission, "EXPECTED", expected)
    return template, footprint, profile


def test_in_range_nodata_inside_footprint_is_not_format_valid(tmp_path, tiny_grid):
    template, footprint, profile = tiny_grid
    values = np.zeros(footprint.shape, dtype="float32")
    values[2, 2] = 0.5  # Keep at least one value visible in a masked read.
    path = tmp_path / "finite-but-nodata.tif"
    with rasterio.open(path, "w", **(profile | {"nodata": 0})) as dataset:
        dataset.write(values, 1)
    report = submission.check_variants(path, template)
    assert report["checks"]["variant_strict_whole_array_no_nan_allowed"]["pass"]
    assert not report["format_valid"]
    assert not report["checks"]["footprint_unmasked"]["pass"]
    assert "footprint_unmasked" in report["hard_failures"]


def test_internal_mask_hiding_a_finite_prediction_is_rejected(tmp_path, tiny_grid):
    template, footprint, profile = tiny_grid
    path = tmp_path / "internal-mask.tif"
    mask = np.full(footprint.shape, 255, dtype="uint8")
    mask[2, 3] = 0
    with rasterio.Env(GDAL_TIFF_INTERNAL_MASK=True):
        with rasterio.open(path, "w", **(profile | {"nodata": None})) as dataset:
            dataset.write(np.full(footprint.shape, 0.25, dtype="float32"), 1)
            dataset.write_mask(mask)
    report = submission.check_variants(path, template)
    assert report["checks"]["variant_strict_whole_array_no_nan_allowed"]["pass"]
    assert not report["checks"]["footprint_unmasked"]["pass"]
    assert not report["format_valid"]


def test_external_mask_is_rejected_even_if_only_exterior_is_masked(tmp_path, tiny_grid):
    template, footprint, profile = tiny_grid
    path = tmp_path / "external-mask.tif"
    with rasterio.Env(GDAL_TIFF_INTERNAL_MASK=False):
        with rasterio.open(path, "w", **(profile | {"nodata": None})) as dataset:
            dataset.write(np.full(footprint.shape, 0.25, dtype="float32"), 1)
            dataset.write_mask(footprint.astype("uint8") * 255)
    assert path.with_suffix(".tif.msk").exists()
    report = submission.check_variants(path, template)
    assert report["checks"]["footprint_unmasked"]["pass"]
    assert not report["checks"]["self_contained_single_tiff"]["pass"]
    assert not report["format_valid"]


def test_standard_nan_exterior_and_zero_exterior_remain_valid(tmp_path, tiny_grid):
    template, footprint, _ = tiny_grid
    values = np.full(footprint.shape, 0.25, dtype="float32")
    for exterior in ("zero", "nan"):
        path = submission.write_submission(
            values, template, tmp_path / f"{exterior}.tif", outside=exterior
        )
        report = submission.check_variants(path, template)
        assert report["format_valid"]
        assert report["checks"]["footprint_unmasked"]["pass"]
        assert report["checks"]["self_contained_single_tiff"]["pass"]
        assert report["template_grid_and_footprint_match_pinned_mirror"]
        assert report["template_origin_authenticated"] is False
        assert "not authenticate" in report["template_provenance_limit"]
        assert not report["submission_authorized"]


def test_writer_does_not_silently_discard_interior_array_mask(tmp_path, tiny_grid):
    template, footprint, _ = tiny_grid
    masked = np.ma.array(np.full(footprint.shape, 0.25), mask=np.zeros(footprint.shape, bool))
    masked.mask[2, 3] = True
    out = tmp_path / "output.tif"
    with pytest.raises(ValueError, match="masked|NoData"):
        submission.write_submission(masked, template, out)
    assert not out.exists()


def test_writer_may_replace_a_masked_exterior_with_selected_encoding(tmp_path, tiny_grid):
    template, footprint, _ = tiny_grid
    masked = np.ma.array(np.full(footprint.shape, 0.25), mask=~footprint)
    out = submission.write_submission(masked, template, tmp_path / "outside.tif")
    report = submission.check_variants(out, template)
    assert report["format_valid"]


def test_cli_does_not_erase_input_tiff_mask(tmp_path, tiny_grid):
    template, footprint, profile = tiny_grid
    path = tmp_path / "prediction.tif"
    mask = np.full(footprint.shape, 255, dtype="uint8")
    mask[2, 3] = 0
    with rasterio.Env(GDAL_TIFF_INTERNAL_MASK=True):
        with rasterio.open(path, "w", **(profile | {"nodata": None})) as dataset:
            dataset.write(np.full(footprint.shape, 0.25, dtype="float32"), 1)
            dataset.write_mask(mask)
    out = tmp_path / "output.tif"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/submission_writer.py",
            str(path),
            str(out),
            "--template",
            str(template),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "masked" in result.stderr.lower() or "nodata" in result.stderr.lower()
    assert not out.exists()


def test_writer_preserves_preexisting_external_sidecar(tmp_path, tiny_grid):
    template, footprint, _ = tiny_grid
    output = tmp_path / "out.tif"
    sidecar = tmp_path / "out.tif.msk"
    sidecar.write_bytes(b"do not delete")
    with pytest.raises(ValueError, match="sidecar"):
        submission.write_submission(np.ones(footprint.shape), template, output)
    assert not output.exists() and sidecar.read_bytes() == b"do not delete"


def test_zip_rejects_external_mask_dependency(tmp_path, tiny_grid):
    _, footprint, profile = tiny_grid
    path = tmp_path / "masked.tif"
    with rasterio.Env(GDAL_TIFF_INTERNAL_MASK=False):
        with rasterio.open(path, "w", **(profile | {"nodata": None})) as dataset:
            dataset.write(np.full(footprint.shape, 0.25, dtype="float32"), 1)
            dataset.write_mask(footprint.astype("uint8") * 255)
    with pytest.raises(ValueError, match="self-contained"):
        submission.zip_single(path)
    assert not path.with_suffix(".zip").exists()


def test_frozen_receipt_allows_added_passing_checks_but_not_a_changed_or_failed_check(
    tmp_path, tiny_grid
):
    import copy

    template, footprint, _ = tiny_grid
    path = submission.write_submission(np.ones(footprint.shape), template, tmp_path / "valid.tif")
    fresh = submission.check_variants(path, template)
    old = copy.deepcopy(fresh)
    del old["checks"]["footprint_unmasked"]
    del old["checks"]["self_contained_single_tiff"]
    assert submission.recorded_validation_matches(fresh, old)

    changed = copy.deepcopy(old)
    changed["checks"]["single_band"]["pass"] = False
    assert not submission.recorded_validation_matches(fresh, changed)
    changed = copy.deepcopy(old)
    changed["sha256"] = "other"
    assert not submission.recorded_validation_matches(fresh, changed)
    changed = copy.deepcopy(fresh)
    changed["checks"]["footprint_unmasked"]["pass"] = False
    # Reject even if a malformed result falsely claims format_valid is true.
    assert not submission.recorded_validation_matches(changed, old)
    changed = copy.deepcopy(fresh)
    del changed["checks"]["self_contained_single_tiff"]
    assert not submission.recorded_validation_matches(changed, old)
    assert not submission.recorded_validation_matches(fresh, old, ignore_fields=("sha256",))


@pytest.mark.parametrize("changed_input", ["artifact", "template"])
def test_preflight_rejects_inputs_changed_during_validation(
    tmp_path, tiny_grid, monkeypatch, changed_input
):
    from gems.preflight import preflight

    template, footprint, _ = tiny_grid
    artifact = submission.write_submission(
        np.ones(footprint.shape), template, tmp_path / "valid.tif"
    )
    real = submission.check_variants

    def mutate_after_read(path, sample):
        report = real(path, sample)
        target = artifact if changed_input == "artifact" else template
        with target.open("ab") as stream:
            stream.write(b"changed")
        return report

    monkeypatch.setattr(submission, "check_variants", mutate_after_read)
    with pytest.raises(ValueError, match="changed during preflight"):
        preflight(artifact, template)


def test_writer_rejects_masked_finite_template_footprint(tiny_grid, tmp_path):
    template, footprint, _ = tiny_grid
    with rasterio.open(template, "r+") as ds:
        ds.nodata = 0
    with pytest.raises(ValueError, match="template.*masked|template.*NoData"):
        submission.write_submission(np.ones(footprint.shape), template, tmp_path / "unsafe.tif")


def test_writer_rejects_template_external_mask_sidecar(tiny_grid, tmp_path):
    template, footprint, _ = tiny_grid
    with rasterio.Env(GDAL_TIFF_INTERNAL_MASK=False):
        with rasterio.open(template, "r+") as ds:
            ds.write_mask(np.full(footprint.shape, 255, dtype="uint8"))
    with pytest.raises(ValueError, match="template.*sidecar|template.*self-contained"):
        submission.write_submission(np.ones(footprint.shape), template, tmp_path / "unsafe.tif")


@pytest.mark.parametrize("damage", ["nodata", "sidecar"])
def test_validator_refuses_untrustworthy_template_masks(tmp_path, tiny_grid, damage):
    template, footprint, _ = tiny_grid
    path = submission.write_submission(np.ones(footprint.shape), template, tmp_path / "valid.tif")
    if damage == "nodata":
        with rasterio.open(template, "r+") as ds:
            ds.nodata = 0
    else:
        with rasterio.Env(GDAL_TIFF_INTERNAL_MASK=False):
            with rasterio.open(template, "r+") as ds:
                ds.write_mask(np.full(footprint.shape, 255, dtype="uint8"))
    report = submission.check_variants(path, template)
    assert report["checks"]["official_template_grid_and_footprint"]["pass"]
    assert not report["checks"]["template_unmasked_and_self_contained"]["pass"]
    assert not report["format_valid"]


def test_footprint_hash_cannot_ignore_masked_pixels():
    masked = np.ma.array([[1, 1], [1, 0]], mask=[[False, True], [False, False]])
    with pytest.raises(ValueError, match="masked"):
        submission.footprint_sha256(masked)
