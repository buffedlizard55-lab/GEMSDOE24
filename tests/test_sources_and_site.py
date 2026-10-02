"""Bounded source parsing, explicit failures and source-window regression tests."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import numpy as np
import pytest

from gems import c2s2

ROOT = Path(__file__).resolve().parents[1]


def script(name):
    spec = spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_leaderboard_parser_verifies_rank_score_and_never_infers_artifact_identity():
    module = script("refresh_source_feed")
    html = """<table><tr><th>Header</th></tr><tr><td>#1</td><td></td>
      <td><a href='/users/DARD/'>DARD</a><br>12 submissions</td><td>0.3195</td><td></td></tr>
      <tr><td>#2</td><td></td><td><a href='/users/Other/'>Other</a> 3 submissions</td>
      <td>0.3042</td><td></td></tr></table>"""
    leader, rows = module.parse_leaderboard(html)
    assert leader == {"rank": 1, "participant": "DARD", "best_score": 0.3195, "submissions": 12}
    assert len(rows) == 2
    for invalid in ("<html>Please log in</html>", html.replace("0.3042", "0.4000")):
        with pytest.raises(ValueError):
            module.parse_leaderboard(invalid)


def test_geometry_only_invalid_shift_is_recorded_and_retried_not_given_chance_auc(monkeypatch):
    yy, xx = np.mgrid[:60, :60]
    ref = np.zeros((60, 60), bool)
    ref[30] = True
    fp = np.ones_like(ref)
    fold = np.where(xx < 30, 0, 1)
    calls = []

    class Constant:
        def predict_proba(self, X):
            return np.full((len(X), 2), 0.5)

    monkeypatch.setattr(c2s2, "make_model", lambda *args: lambda X, y: Constant())

    def shift(dy, dx):
        calls.append((dy, dx))
        if len(calls) == 1:
            invalid = np.zeros_like(ref)
            invalid[10, 10] = True
            return invalid  # no near samples in the other spatial fold
        return ref

    r = c2s2.c2s2_test(
        "synthetic",
        ref,
        {"road_m": xx.astype(float)},
        fold,
        fp,
        n_per_class=200,
        n_null=2,
        null_mode="shift",
        shift_fn=shift,
    )
    assert r.n_null == 2 and r.p_value == 1
    assert len(r.info["shift_draws"]) == 3
    assert sum(r.info["rejected_single_class_shifts"].values()) == 1
    assert r.info["valid_shift_count"] == 2
    assert not r.info["shift_draws"][0]["valid"]
    assert "never AUC" in r.info["conditional_geometry_design"]


def test_impossible_shift_design_fails_closed_after_a_bounded_geometry_retry(monkeypatch):
    yy, xx = np.mgrid[:60, :60]
    ref = np.zeros((60, 60), bool)
    ref[30] = True
    fp = np.ones_like(ref)
    fold = np.where(xx < 30, 0, 1)

    class Constant:
        def predict_proba(self, X):
            return np.full((len(X), 2), 0.5)

    monkeypatch.setattr(c2s2, "make_model", lambda *args: lambda X, y: Constant())
    invalid = np.zeros_like(ref)
    invalid[10, 10] = True
    with pytest.raises(ValueError, match="20 geometry-only"):
        c2s2.c2s2_test(
            "bad",
            ref,
            {"road_m": xx.astype(float)},
            fold,
            fp,
            n_per_class=200,
            n_null=1,
            null_mode="shift",
            shift_fn=lambda dy, dx: invalid,
        )


def test_official_roads_select_a_buffer_not_the_legacy_tight_bbox():
    module = script("fetch_official_roads")
    assert module.BOX == (-120.5, 37.0, -115.9, 41.0)
    assert module.intersects([-120.1, 40.73, -119.9, 40.9])
    assert not module.intersects([0, 0, 1, 1])
    assert module.PAD == 200


def test_archive_commands_cannot_execute_historical_branch_or_invalid_audit_work():
    import subprocess
    import sys

    for name in ("ci_fetch_external.py", "run_gate24.py", "build_access_layers.py"):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / name)], capture_output=True, text=True
        )
        assert result.returncode != 0 and "Retired" in result.stderr


def test_feed_never_requests_drivendata_hosts(monkeypatch, tmp_path):
    """DrivenData's Terms of Use forbid automatic access; the scheduled feed must not touch it."""
    module = script("refresh_source_feed")
    import json as _json

    seen = []

    class Resp:
        content = b'{"id": "657e1d85d34e23d3533209f7", "title": "GeoDAWN: x", "provenance": {"lastUpdated": "2025-02-28"}}'

        def raise_for_status(self):
            return None

        def json(self):
            return _json.loads(self.content)

    class Session:
        headers = {}

        def get(self, url, timeout=0):
            seen.append(url)
            return Resp()

    monkeypatch.setattr(module.requests, "Session", Session)
    feed = tmp_path / "docs/data"
    feed.mkdir(parents=True)
    src = module.ROOT / "docs/data/source_health.json"
    (feed / "source_health.json").write_text(src.read_text())
    monkeypatch.setattr(module, "ROOT", tmp_path)
    module.main.__globals__["ROOT"] = tmp_path
    monkeypatch.setattr("sys.argv", ["refresh_source_feed.py"])
    module.main()
    assert seen and all("drivendata.org" not in u for u in seen)
    with pytest.raises(ValueError, match="Terms of Use"):
        module.assert_allowed("https://community.drivendata.org/t/x.json")
    with pytest.raises(ValueError, match="Terms of Use"):
        module.assert_allowed("https://www.drivendata.org/competitions/306/")
    assert module.assert_allowed("https://www.sciencebase.gov/catalog/item/x?format=json")


def test_no_script_or_workflow_fetches_drivendata_automatically():
    import re

    offenders = []
    for path in list((ROOT / "scripts").glob("*.py")) + list(
        (ROOT / ".github/workflows").glob("*.yml")
    ):
        text = path.read_text()
        for m in re.finditer(
            r"(requests\.(get|post)|session\.get|urlopen|curl|wget)[^\n]*drivendata", text
        ):
            offenders.append((path.name, m.group(0)[:80]))
    assert not offenders, offenders
