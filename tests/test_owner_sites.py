"""All requested sources retained; GitHub text cannot become a score receipt."""

import copy
import csv
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import review_owner_sites as sites  # noqa: E402
from tnr1_site import all_sites_table  # noqa: E402

DATA = json.loads((ROOT / "docs/data/all_owner_sites_20261026.json").read_text())


def test_all_owner_sites_and_each_claim_preserved_without_score_confirmation():
    assert sites.validate(DATA) == DATA
    parsed = sites.owner_sites(sites.BRIEF.read_text())
    assert len(parsed) == 92
    assert DATA["owner_reported_claims"] == 119
    assert all(row["source_status"] == "readme_retrieved" for row in DATA["rows"])
    assert DATA["organizer_confirmed_receipts"] == [] and DATA["leaderboard"] is None
    assert all("UNVERIFIED" in claim["status"] for row in DATA["rows"] for claim in row["claims"])
    rows = list(csv.DictReader((ROOT / "docs/data/all_owner_sites_20261026.csv").open()))
    assert {row["repository"] for row in rows} == {row["repo"] for row in DATA["rows"]}
    assert all(
        "UNVERIFIED" in row["score_status"] or row["score_status"] == "NO SCORE REPORTED"
        for row in rows
    )
    h33 = parsed["GEMSDOE32"]["claims"]
    assert any(
        claim["value_as_reported"] == "0.2778"
        and "h33-h33-2-b2" in claim["submission_name_as_reported"]
        for claim in h33
    )
    row52 = next(row for row in DATA["rows"] if row["repo"].endswith("/GEMSDOE52"))
    assert "recovered and verified" in row52["text_representation_irregularity"]


@pytest.mark.parametrize(
    "change",
    [
        lambda d: d["rows"].pop(),
        lambda d: d["rows"].append(copy.deepcopy(d["rows"][0])),
        lambda d: d.update(site_count=93),
        lambda d: d.update(owner_reported_claims=120),
        lambda d: d.update(leaderboard={"best_score": 0.9}),
        lambda d: d.update(organizer_confirmed_receipts=["invented"]),
        lambda d: d.update(checked_utc="2026-10-26"),
        lambda d: d.update(refresh_status="success-maybe"),
        lambda d: d.update(brief_sha256="0" * 64),
        lambda d: d["rows"][0].update(readme_url="javascript:alert(1)"),
        lambda d: d["rows"][0].update(commit="not-a-commit"),
        lambda d: d["rows"][0]["claims"][0].update(status="ORGANIZER-CONFIRMED"),
    ],
)
def test_missing_sources_fabricated_scores_or_bad_freshness_fail_closed(change):
    data = copy.deepcopy(DATA)
    change(data)
    with pytest.raises(ValueError):
        sites.validate(data)


def test_failed_refresh_retains_real_old_timestamp_and_displays_staleness(monkeypatch, tmp_path):
    path = tmp_path / "docs/data/all_owner_sites_20261026.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(DATA))
    monkeypatch.setattr(sites, "OUTPUT", path)
    after = sites.retain_stale_snapshot(OSError("simulated network failure"))
    assert after["checked_utc"] == DATA["checked_utc"]
    assert after["rows"] == DATA["rows"]
    assert after["refresh_status"] == "error"
    assert "not freshly verified" in after["refresh_error"]
    html = all_sites_table(tmp_path)
    assert "STALE SNAPSHOT" in html
    assert DATA["checked_utc"] in html
    assert "0.2778" in html and "UNVERIFIED" in html


def test_priority_feed_reuses_snapshot_time_without_fake_new_freshness(monkeypatch, tmp_path):
    import refresh_priority_feed as priority

    registry_dir = tmp_path / "registry"
    data_dir = tmp_path / "docs/data"
    registry_dir.mkdir()
    data_dir.mkdir(parents=True)
    registry = json.loads((ROOT / "registry/priority_rasters.json").read_text())
    (registry_dir / "priority_rasters.json").write_text(json.dumps(registry))
    snapshot = data_dir / "all_owner_sites_20261026.json"
    snapshot.write_text(json.dumps(DATA))
    monkeypatch.setattr(priority, "ROOT", tmp_path)
    monkeypatch.setattr(
        sys, "argv", ["refresh_priority_feed.py", "--from-owner-snapshot", str(snapshot)]
    )
    priority.main()
    feed = json.loads((data_dir / "priority_feed.json").read_text())
    assert feed["checked_utc"] == DATA["checked_utc"]
    assert feed["leaderboard"] is None and feed["organizer_score_receipts"] == []
    assert len(feed["rows"]) == 9 and feed["status"] == "checked"
    stale = copy.deepcopy(DATA)
    stale["refresh_status"] = "error"
    snapshot.write_text(json.dumps(stale))
    with pytest.raises(ValueError, match="stale"):
        priority.main()
