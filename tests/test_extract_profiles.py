"""Offline tests for the GeoDAWN profile extractor (synthetic archive, no network)."""

from __future__ import annotations

import io
import zipfile
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = spec_from_file_location(
    "extract_geodawn_profiles", ROOT / "scripts/extract_geodawn_profiles.py"
)
ext = module_from_spec(spec)
spec.loader.exec_module(ext)

HEADER = "Line,flight,heading,fid,date,time,lat,lon,x,y,dem,drape,gps_elev,radar,calc_radar,k_raw"


def synthetic_csv() -> bytes:
    rows = ["/ Geosoft-style preamble line", "// another comment", HEADER]
    fid = 0

    def add(line, flight, date, xs, y, clearance=150.0):
        nonlocal fid
        for x in xs:
            fid += 1
            rows.append(
                f"{line},{flight},90,{fid},{date},00:00:00.0,39,-117,{x},{y},1500,{1500 + clearance},"
                f"{1500 + clearance},{clearance},{clearance},12"
            )

    add("L100", 1, "2021/11/01", np.arange(0, 10001, 50), 0)
    add("L105", 1, "2021/11/01", np.arange(10000, -1, -50), 400)
    # 2 km gap (jump 2000 -> 4500 m) must not count as flown length
    add(
        "L110",
        2,
        "2021/11/02",
        list(range(0, 2001, 100)) + list(range(4500, 6001, 100)),
        800,
        100.0,
    )
    return ("\n".join(rows) + "\n").encode()


def archive(tmp_path: Path) -> Path:
    path = tmp_path / "spec.zip"
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("22103_spec_a2.csv", synthetic_csv())
    return path


def run(tmp_path, chunk_rows):
    p = archive(tmp_path)
    with zipfile.ZipFile(p) as z:
        return ext.parse_stream(lambda: z.open("22103_spec_a2.csv"), "a2", chunk_rows=chunk_rows)


def test_header_sniff_skips_comments_and_finds_required_columns():
    text = synthetic_csv().decode().splitlines()
    row, names = ext.sniff_header(text)
    assert row == 2 and {"line", "flight", "x", "y", "date"} <= set(names)
    with pytest.raises(ValueError):
        ext.sniff_header(["a,b,c", "1,2,3"])


def test_line_km_gap_exclusion_and_groups(tmp_path):
    summary, sample, info = run(tmp_path, 10_000)
    by = summary.set_index("line")
    assert by.loc["L100", "km"] == pytest.approx(10.0)
    assert by.loc["L105", "km"] == pytest.approx(10.0)
    assert by.loc["L110", "km"] == pytest.approx(3.5)  # 2000 m + 1500 m, gap excluded
    assert by.loc["L110", "gaps_over_2km"] == 1
    assert set(summary["flight"]) == {1, 2}
    assert by.loc["L100", "runs"] == 1
    assert by.loc["L100", "clearance_mean_m"] == pytest.approx(150.0)
    assert by.loc["L110", "drape_height_mean_m"] == pytest.approx(100.0)
    assert info["rows"] == len(summary.index) * 0 + 201 + 201 + 21 + 16


def test_chunk_boundaries_do_not_change_results(tmp_path):
    big_s, big_p, _ = run(tmp_path, 100_000)
    small_s, small_p, _ = run(tmp_path, 37)  # splits lines mid-run
    key = ["line", "flight", "date"]
    a = big_s.sort_values(key).reset_index(drop=True)
    b = small_s.sort_values(key).reset_index(drop=True)
    for col in ("n_fiducials", "km", "xmin", "xmax", "runs", "gaps_over_2km"):
        np.testing.assert_allclose(a[col].to_numpy(float), b[col].to_numpy(float))
    sort = ["line", "x", "y"]
    pd_a = big_p.sort_values(sort).reset_index(drop=True)
    pd_b = small_p.sort_values(sort).reset_index(drop=True)
    assert len(pd_a) == len(pd_b)
    np.testing.assert_allclose(pd_a["x"].to_numpy(), pd_b["x"].to_numpy())


def test_sample_is_thinned_to_about_the_step(tmp_path):
    _, sample, _ = run(tmp_path, 10_000)
    l100 = sample[sample["line"] == "L100"].sort_values("x")
    # 10 km at one point per 500 m bin, including both ends of the run
    assert 20 <= len(l100) <= 22
    assert np.diff(l100["x"].to_numpy()).min() >= 450


def test_unsorted_input_is_visible_in_runs(tmp_path):
    rows = [HEADER]
    for i, line in enumerate(["L1", "L2", "L1", "L2"]):
        rows.append(f"{line},1,90,{i},2021/11/01,0,39,-117,{i * 100},0,1500,1650,1650,150,150,1")
    p = tmp_path / "u.zip"
    with zipfile.ZipFile(p, "w") as z:
        z.writestr("u.csv", "\n".join(rows) + "\n")
    with zipfile.ZipFile(p) as z:
        summary, _, _ = ext.parse_stream(lambda: z.open("u.csv"), "a1", chunk_rows=10)
    assert (summary["runs"] == 2).all()  # interleaved rows are flagged, not silently merged


def test_md5_helper_matches_hashlib(tmp_path):
    import hashlib

    path = archive(tmp_path)
    m, s = ext.md5_sha256(path)
    raw = path.read_bytes()
    assert m == hashlib.md5(raw).hexdigest()  # noqa: S324
    assert s == hashlib.sha256(raw).hexdigest()


def test_main_runs_offline_with_local_zip(tmp_path, monkeypatch):
    out = tmp_path / "out"
    monkeypatch.setattr(
        "sys.argv",
        [
            "x",
            "--out",
            str(out),
            "--workdir",
            str(tmp_path / "w"),
            "--local-zip",
            "a2",
            str(archive(tmp_path)),
        ],
    )
    ext.main()
    assert (out / "geodawn_line_flight_summary.csv").exists()
    assert (out / "geodawn_fiducial_sample.csv.gz").exists()
    receipt = (out / "geodawn_profile_receipt.json").read_text()
    assert '"label_free": true' in receipt and "total_km_by_area" in receipt
    assert io.StringIO  # keep import used
