"""CLI must not publish or overwrite an artifact until strict validation passes."""

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import Affine

from gems import submission

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "writer_transaction", ROOT / "scripts/submission_writer.py"
)
CLI = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CLI)


def make_template(tmp_path):
    path = tmp_path / "template.tif"
    values = np.full((8, 10), 0.5, dtype="float32")
    values[0] = np.nan
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=8,
        width=10,
        count=1,
        dtype="float32",
        crs="EPSG:32611",
        transform=Affine(100, 0, 243350, 0, -100, 4508550),
        nodata=np.nan,
    ) as dst:
        dst.write(values, 1)
    return path, np.isfinite(values)


def pin_template(monkeypatch, template, footprint):
    # Synthetic grid is a test fixture, not the organizer template.
    with rasterio.open(template) as src:
        monkeypatch.setitem(submission.EXPECTED, "shape", src.shape)
        monkeypatch.setitem(submission.EXPECTED, "transform", tuple(src.transform)[:6])
    monkeypatch.setitem(submission.EXPECTED, "footprint_pixels", int(footprint.sum()))
    monkeypatch.setitem(
        submission.EXPECTED, "footprint_sha256", submission.footprint_sha256(footprint)
    )


def run(monkeypatch, prediction, output, template):
    monkeypatch.setattr(
        sys,
        "argv",
        ["submission_writer.py", str(prediction), str(output), "--template", str(template)],
    )
    CLI.main()


@pytest.mark.parametrize("already_exists", [False, True])
def test_invalid_template_never_publishes_or_overwrites(tmp_path, monkeypatch, already_exists):
    template, fp = make_template(tmp_path)
    prediction = tmp_path / "pred.npy"
    np.save(prediction, np.full(fp.shape, 0.5))
    output = tmp_path / "out.tif"
    if already_exists:
        output.write_bytes(b"previous artifact")
    with pytest.raises(SystemExit, match="failed pinned-grid"):
        run(monkeypatch, prediction, output, template)
    if already_exists:
        assert output.read_bytes() == b"previous artifact"
    else:
        assert not output.exists()
    assert not list(tmp_path.glob(".submission-*"))


def test_validated_file_atomically_replaces_output(tmp_path, monkeypatch, capsys):
    template, fp = make_template(tmp_path)
    pin_template(monkeypatch, template, fp)
    prediction = tmp_path / "pred.npy"
    np.save(prediction, np.full(fp.shape, 0.5))
    output = tmp_path / "out.tif"
    output.write_bytes(b"previous artifact")
    run(monkeypatch, prediction, output, template)
    report = json.loads(capsys.readouterr().out)
    assert report["format_valid"] and not report["submission_authorized"]
    assert report["sha256"] == submission.sha256_file(output)
    assert str(output) in report["checks"]["raster_self_contained"]["detail"]
    assert ".submission-" not in report["checks"]["raster_self_contained"]["detail"]
    with rasterio.open(output) as src:
        assert np.all(src.read(1)[fp] == 0.5)
        assert np.all(src.read(1)[~fp] == 0)
    assert not list(tmp_path.glob(".submission-*"))


def test_validator_exception_preserves_existing_output(tmp_path, monkeypatch):
    template, fp = make_template(tmp_path)
    prediction = tmp_path / "pred.npy"
    np.save(prediction, np.full(fp.shape, 0.5))
    output = tmp_path / "out.tif"
    output.write_bytes(b"previous artifact")

    def fail(*args, **kwargs):
        raise RuntimeError("validator failed")

    monkeypatch.setattr(CLI, "check_variants", fail)
    with pytest.raises(RuntimeError, match="validator failed"):
        run(monkeypatch, prediction, output, template)
    assert output.read_bytes() == b"previous artifact"
    assert not list(tmp_path.glob(".submission-*"))


def test_destination_sidecar_rejected_without_modification(tmp_path, monkeypatch):
    template, fp = make_template(tmp_path)
    prediction = tmp_path / "pred.npy"
    np.save(prediction, np.full(fp.shape, 0.5))
    output = tmp_path / "out.tif"
    output.write_bytes(b"previous artifact")
    sidecar = tmp_path / "out.tif.msk"
    sidecar.write_bytes(b"sidecar")
    with pytest.raises(ValueError, match="existing external sidecar"):
        run(monkeypatch, prediction, output, template)
    assert output.read_bytes() == b"previous artifact"
    assert sidecar.read_bytes() == b"sidecar"


@pytest.mark.parametrize("source", ["template", "prediction"])
@pytest.mark.parametrize("alias", ["direct", "symlink", "hardlink"])
def test_cli_never_overwrites_input_aliases(tmp_path, monkeypatch, source, alias):
    template, fp = make_template(tmp_path)
    prediction = tmp_path / "pred.npy"
    np.save(prediction, np.full(fp.shape, 0.5))
    target = template if source == "template" else prediction
    before = target.read_bytes()
    output = target if alias == "direct" else tmp_path / "alias.tif"
    if alias == "symlink":
        output.symlink_to(target)
    elif alias == "hardlink":
        output.hardlink_to(target)
    with pytest.raises(SystemExit, match="must not overwrite"):
        run(monkeypatch, prediction, output, template)
    assert target.read_bytes() == before
