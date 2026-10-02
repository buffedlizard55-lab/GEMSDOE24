"""Offline tests for the flight-path summariser (synthetic polylines written with pyshp)."""

from __future__ import annotations

import io
import zipfile
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest
import shapefile

ROOT = Path(__file__).resolve().parents[1]
spec = spec_from_file_location("fp_extract", ROOT / "scripts/extract_geodawn_flight_paths.py")
fp = module_from_spec(spec)
spec.loader.exec_module(fp)


def synthetic_zip() -> bytes:
    shp, shx, dbf = io.BytesIO(), io.BytesIO(), io.BytesIO()
    w = shapefile.Writer(shp=shp, shx=shx, dbf=dbf, shapeType=shapefile.POLYLINE)
    w.field("Id", "N", 4)
    w.field("Line", "C", 12)
    w.line([[(float(x), 0.0) for x in range(0, 10001, 50)]])  # 10 km east-west, heading 90 deg
    w.record(0, "L100")
    w.line([[(0.0, 400.0), (0.0, 1400.0)], [(0.0, 3000.0), (0.0, 3500.0)]])  # two parts, 1.5 km
    w.record(0, "L9001")
    w.close()
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as z:
        z.writestr("area2_flight_path.shp", shp.getvalue())
        z.writestr("area2_flight_path.shx", shx.getvalue())
        z.writestr("area2_flight_path.dbf", dbf.getvalue())
    return out.getvalue()


def test_line_lengths_extent_heading_and_sampling():
    df, sample = fp.summarise(fp.read_zip_shapefile(synthetic_zip()), "a2")
    by = df.set_index("line")
    assert by.loc["L100", "km"] == pytest.approx(10.0)
    assert by.loc["L100", "heading_deg"] == pytest.approx(90.0)
    assert by.loc["L100", "xmax"] == pytest.approx(10000.0)
    assert by.loc["L9001", "km"] == pytest.approx(1.5)  # gap between parts is not flown length
    s100 = sample[sample["line"] == "L100"]
    assert 20 <= len(s100) <= 22 and s100["x"].diff().dropna().min() >= 450


def test_line_field_is_required():
    shp, shx, dbf = io.BytesIO(), io.BytesIO(), io.BytesIO()
    w = shapefile.Writer(shp=shp, shx=shx, dbf=dbf, shapeType=shapefile.POLYLINE)
    w.field("Name", "C", 8)
    w.line([[(0.0, 0.0), (1.0, 1.0)]])
    w.record("x")
    w.close()
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as z:
        z.writestr("a.shp", shp.getvalue())
        z.writestr("a.shx", shx.getvalue())
        z.writestr("a.dbf", dbf.getvalue())
    with pytest.raises(ValueError):
        fp.summarise(fp.read_zip_shapefile(out.getvalue()), "a1")
