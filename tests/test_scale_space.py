import numpy as np
import pytest

from gems.scale_space import contact_persistence, upward_continue


def test_upward_continuation_preserves_constant_field_and_zero_height():
    field = np.full((32, 40), 7.5, dtype=np.float32)
    assert np.array_equal(upward_continue(field, 0), field)
    continued = upward_continue(field, 300, cell_size_m=100)
    assert np.allclose(continued, field, atol=2e-6)


def test_upward_continuation_attenuates_high_frequency_and_restores_missing():
    y, x = np.indices((96, 96))
    field = ((x + y) % 2).astype(np.float32)
    field[0, 0] = np.nan
    continued = upward_continue(field, 300, cell_size_m=100)
    assert np.isnan(continued[0, 0])
    assert np.nanstd(continued[8:-8, 8:-8]) < np.nanstd(field[8:-8, 8:-8])


def test_contact_persistence_is_bounded_and_masks_unsafe_edges():
    y, x = np.indices((96, 96))
    field = np.exp(-(((x - 48.0) / 7.0) ** 2)).astype(np.float32)
    field[:2, :] = np.nan
    result = contact_persistence(
        field,
        heights_m=(20, 40, 60),
        cell_size_m=10,
        edge_guard_m=30,
    )
    assert np.isnan(result[0, 40])
    finite = result[np.isfinite(result)]
    assert finite.size
    assert finite.min() >= 0
    assert finite.max() <= 1


def test_scale_space_rejects_invalid_parameters():
    with pytest.raises(ValueError, match="height_m"):
        upward_continue(np.ones((8, 8)), -1)
    with pytest.raises(ValueError, match="increasing"):
        contact_persistence(np.ones((8, 8)), heights_m=(200, 100, 400))
