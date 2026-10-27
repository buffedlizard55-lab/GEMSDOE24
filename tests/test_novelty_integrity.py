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
