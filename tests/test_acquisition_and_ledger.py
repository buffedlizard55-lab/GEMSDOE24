"""Block-derivation helpers, audit tolerance logic and the live-score ledger's integrity."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from gems import acquisition as acq

ROOT = Path(__file__).resolve().parents[1]


def test_published_block_totals_sum_to_the_report_total():
    assert sum(acq.OFFICIAL_LINE_KM.values()) == acq.OFFICIAL_TOTAL_KM == 149_030.0


def test_fit_line_recovers_vertical_and_horizontal_edges_with_outliers():
    rng = np.random.default_rng(1)
    y = np.arange(0, 200.0)
    vert = np.c_[100 + 0.05 * y + rng.normal(0, 0.3, 200), y]
    vert = np.vstack([vert, [[400, 10], [5, 150], [300, 90]]])  # gross outliers
    m, k = acq.fit_line(vert, vertical=True)
    assert m == pytest.approx(0.05, abs=0.01) and k == pytest.approx(100, abs=1.0)
    x = np.arange(0, 300.0)
    horiz = np.c_[x, 50 - 0.01 * x + rng.normal(0, 0.3, 300)]
    m, k = acq.fit_line(horiz, vertical=False)
    assert m == pytest.approx(-0.01, abs=0.005) and k == pytest.approx(50, abs=1.0)
    with pytest.raises(ValueError):
        acq.fit_line(vert[:5], vertical=True)


def test_rect_corners_from_edge_lines():
    corners = acq.rect_corners((0.0, 10.0), (0.0, 110.0), (0.0, 20.0), (0.0, 70.0))
    assert corners == [(10.0, 20.0), (110.0, 20.0), (110.0, 70.0), (10.0, 70.0)]


def test_georef_forward_inverse_round_trip():
    g = acq.Georef(340.0, -345.0, 32000.0, 14100.0, 0.688)
    lon, lat = np.array([-118.0, -117.2]), np.array([39.0, 38.1])
    u, v = g.forward(lon, lat)
    lo2, la2 = g.inverse(u, v)
    assert np.allclose(lo2, lon) and np.allclose(la2, lat)


def test_line_km_audit_tolerances_pass_and_fail():
    ok = {b: v * 1.02 for b, v in acq.OFFICIAL_LINE_KM.items()}
    assert acq.audit_line_km(ok)["passed"] is True
    bad = dict(ok)
    bad[4] = acq.OFFICIAL_LINE_KM[4] * 1.62  # the Area-1 double-counting variant
    audit = acq.audit_line_km(bad)
    assert audit["passed"] is False and audit["blocks"]["Tonopah"]["within_tolerance"] is False
    drift = {b: v * 1.075 for b, v in acq.OFFICIAL_LINE_KM.items()}  # each block ok, total not
    assert acq.audit_line_km(drift)["total"]["within_tolerance"] is False


def test_fill_unassigned_and_apportioning():
    fp = np.ones((10, 10), bool)
    block = np.zeros((10, 10), np.uint8)
    block[:, :4] = 1
    block[:, 6:] = 2
    filled, n = acq.fill_unassigned(block, fp)
    assert n == 20 and set(np.unique(filled)) == {1, 2}
    xy = np.array([[0.5, 0.5], [9.5, 0.5]])
    km = acq.block_line_km(
        [(10.0, xy)], filled, lambda x, y: (np.floor(x).astype(int), np.floor(y).astype(int))
    )
    assert km[1] == pytest.approx(5.0) and km[2] == pytest.approx(5.0)


def test_live_ledger_is_well_formed_and_never_invents_scores():
    led = json.loads((ROOT / "registry/live_scores.json").read_text())
    ids = [a["id"] for a in led["artifacts"]]
    assert len(ids) == len(set(ids)) == 24
    for a in led["artifacts"]:
        assert 0.0 < a["owner_reported_public_score"] < 1.0
        assert len(a["sha256"]) == 64 and len(a["repo_commit"]) == 40
        assert a["corroboration"] in led["corroboration_levels"]
    task_only = {a["id"] for a in led["artifacts"] if a["corroboration"] == "task_statement_only"}
    assert task_only == {"g10_h28dot_1839", "g13_lattice_0904", "g16_h18_3a_0976"}
    assert all(u["owner_reported_public_score"] is None for u in led["unscored_artifacts"])
    assert {"22GEMSDOE", "h18-4", "h20-1", "h20-5"} <= set(led["blank_in_task_statement"])


def test_derived_block_receipt_status_is_never_official_coordinates():
    p = ROOT / "data/external/audit_sources/acquisition_blocks_receipt.json"
    r = json.loads(p.read_text())
    assert r["status"] == "derived_audited" and r["official_coordinates"] is False
    audit = r["line_km_audit"][r["primary_audit_variant"]]["audit"]
    assert audit["passed"] is True
    assert r["audit_tolerances_fixed_before_derivation"] == {"per_block": 0.08, "total": 0.05}
