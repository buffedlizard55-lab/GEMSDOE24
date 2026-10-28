"""Prospective novelty must not certify missing, malformed or unaligned evidence."""

import hashlib
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import Affine

from gems import novelty


def _grid(path: Path, data, *, crs="EPSG:32611", transform=None, count=1):
    if transform is None:
        transform = Affine(100, 0, 243350, 0, -100, 4508550)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=data.shape[1],
        height=data.shape[0],
        count=count,
        dtype="float32",
        crs=crs,
        transform=transform,
    ) as dst:
        for i in range(1, count + 1):
            dst.write(data.astype("float32"), i)


@pytest.fixture
def fixture(tmp_path):
    fp = np.ones((20, 30), dtype=bool)
    a = np.zeros(fp.shape, dtype=np.float32)
    a[2:18:4, 3:27:5] = 1
    template, reference = tmp_path / "template.tif", tmp_path / "ref.tif"
    _grid(template, np.zeros_like(a))
    _grid(reference, a)
    row = {
        "id": "ref",
        "file": reference.name,
        "cache_path": reference.name,
        "footprint_sha256": hashlib.sha256(a[fp].astype("<f4").tobytes()).hexdigest(),
    }
    surface = np.random.default_rng(12).random(fp.shape)
    return tmp_path, fp, a, surface, template, reference, row


def _compare(data, **kwargs):
    root, fp, _a, surface, template, _ref, row = data
    return novelty.compare_registry(surface, fp, [row], root, template_path=template, **kwargs)


def test_aligned_nonconstant_reference_has_a_defined_comparison(fixture):
    result = _compare(fixture)
    assert result["passed"] is True
    assert result["rows"][0]["correlation_defined"] is True


@pytest.mark.parametrize("damage", ["crs", "transform", "count"])
def test_same_shape_same_values_do_not_hide_bad_georeferencing(fixture, damage):
    root, _fp, a, _surface, _template, ref, _row = fixture
    opts = {
        "crs": {"crs": "EPSG:4326"},
        "transform": {"transform": Affine(100, 0, 243450, 0, -100, 4508550)},
        "count": {"count": 2},
    }[damage]
    _grid(ref, a, **opts)
    with pytest.raises(ValueError, match="Registry grid mismatch"):
        _compare(fixture)


def test_missing_template_or_footprint_hash_fails_closed(fixture):
    root, fp, _a, surface, _template, _ref, row = fixture
    with pytest.raises(ValueError, match="template is required"):
        novelty.compare_registry(surface, fp, [row], root)
    del row["footprint_sha256"]
    with pytest.raises(ValueError, match="checksum"):
        _compare(fixture)


def test_undefined_rank_comparison_does_not_certify_novelty(fixture):
    root, fp, _a, _surface, template, _ref, row = fixture
    result = novelty.compare_registry(np.zeros(fp.shape), fp, [row], root, template_path=template)
    assert result["rows"][0]["raw_spearman"] is None
    assert result["rows"][0]["correlation_defined"] is False
    assert result["passed"] is False


def test_nonbinary_or_nan_dot_masks_are_rejected_not_coerced(fixture):
    root, fp, _a, surface, template, _ref, row = fixture
    for invalid in (np.nan, -1.0, 0.5):
        dots = np.zeros(fp.shape)
        dots[2, 3] = invalid
        with pytest.raises(ValueError, match="finite binary"):
            novelty.compare_registry(surface, fp, [row], root, template_path=template, dots=dots)


def test_finite_in_range_nodata_pixels_in_a_registry_raster_are_rejected(fixture):
    root, fp, a, surface, template, ref, row = fixture
    # All raw bytes and the registered value hash still match; but zero-valued
    # cells (including almost the whole footprint) are marked NoData.
    with rasterio.open(ref, "r+") as ds:
        ds.nodata = 0.0
    with pytest.raises(ValueError, match="masked|NoData"):
        novelty.compare_registry(surface, fp, [row], root, template_path=template)


def test_candidate_arrays_cannot_silently_discard_masks(fixture):
    root, fp, _a, surface, template, _ref, row = fixture
    masked = np.ma.array(surface, mask=np.zeros(fp.shape, dtype=bool))
    masked.mask[3, 4] = True
    with pytest.raises(ValueError, match="masked"):
        novelty.compare_registry(masked, fp, [row], root, template_path=template)
    dots = np.ma.array(np.zeros(fp.shape), mask=np.zeros(fp.shape, dtype=bool))
    dots[1, 1] = 1
    dots.mask[3, 4] = True
    with pytest.raises(ValueError, match="masked"):
        novelty.compare_registry(surface, fp, [row], root, template_path=template, dots=dots)


def test_template_with_masked_footprint_is_rejected(fixture):
    root, fp, _a, surface, template, _ref, row = fixture
    with rasterio.open(template, "r+") as ds:
        ds.nodata = 0.0
    with pytest.raises(ValueError, match="Template.*masked|Template.*NoData"):
        novelty.compare_registry(surface, fp, [row], root, template_path=template)


def test_registry_sidecar_not_covered_by_raster_hash_is_rejected(fixture):
    root, fp, _a, surface, template, ref, row = fixture
    with rasterio.Env(GDAL_TIFF_INTERNAL_MASK=False):
        with rasterio.open(ref, "r+") as ds:
            ds.write_mask(np.full(fp.shape, 255, dtype="uint8"))
    assert ref.with_suffix(".tif.msk").exists()
    with pytest.raises(ValueError, match="sidecar|self-contained"):
        novelty.compare_registry(surface, fp, [row], root, template_path=template)


def test_dot_overlap_cannot_count_nan_or_masked_pixels_as_dots():
    candidate = np.array([[1.0, 0.0]])
    for invalid in (
        np.array([[float("nan"), 1.0]]),
        np.array([[0.2, 1.0]]),
        np.ma.array([[0.0, 1.0]], mask=[[True, False]]),
    ):
        with pytest.raises(ValueError, match="binary|masked"):
            novelty.dot_overlap(candidate, invalid)


def test_control_coverage_does_not_discard_input_masks():
    footprint = np.ones((2, 2), dtype=bool)
    reference = np.ma.array(np.eye(2, dtype=bool), mask=[[True, False], [False, False]])
    with pytest.raises(ValueError, match="masked"):
        novelty.classify_space_filling_control(footprint, reference)


@pytest.mark.parametrize("fn", [novelty.correlation, novelty.rank_correlation])
def test_correlations_do_not_discard_masks(fn):
    masked = np.ma.array([1.0, 2.0, 3.0], mask=[False, True, False])
    with pytest.raises(ValueError, match="masked"):
        fn(masked, np.array([1.0, 2.0, 3.0]))
    with pytest.raises(ValueError, match="masked"):
        fn(np.array([1.0, 2.0, 3.0]), masked)
