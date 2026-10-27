"""Necessary-only overlap bound: exact boundary, malformed evidence and CLI status."""

import itertools
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from gems.novelty import dot_budget_feasibility

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from check_uniqueness_feasibility import REGISTRY, TEMPLATE, WITNESS, audit, render  # noqa: E402


def test_bound_is_attainable_and_never_overstates_overlap_exhaustively():
    # Exhaust all covered sets and candidate sets of a six-pixel footprint.
    # No spatial assumption is needed once the reference's radius union is known.
    n = 6
    for covered_flags in itertools.product((0, 1), repeat=n):
        covered = {i for i, flag in enumerate(covered_flags) if flag}
        for k in range(1, n + 1):
            report = dot_budget_feasibility(n, n - len(covered), k)
            realized = [len(set(c) & covered) for c in itertools.combinations(range(n), k)]
            assert report["minimum_overlapping_dots"] == min(realized)
            assert report["strictly_exceeds_limit"] == all(10 * v > 7 * k for v in realized)
            assert report["submission_authorized"] is False


def test_strict_threshold_and_real_footprint_boundary():
    exact = dot_budget_feasibility(100, 3, 10)
    assert exact["minimum_overlap_fraction"] == 0.70
    assert exact["strictly_exceeds_limit"] is False
    assert dot_budget_feasibility(100, 3, 11)["strictly_exceeds_limit"] is True
    assert not dot_budget_feasibility(5167373, 6649, 22163)["strictly_exceeds_limit"]
    assert dot_budget_feasibility(5167373, 6649, 22164)["strictly_exceeds_limit"]
    assert dot_budget_feasibility(100, 100, 100)["minimum_overlap_fraction"] == 0
    assert dot_budget_feasibility(100, 0, 1)["strictly_exceeds_limit"] is True


@pytest.mark.parametrize(
    "args",
    [
        (0, 0, 1),
        (10, -1, 1),
        (10, 11, 1),
        (10, 2, 0),
        (10, 2, 11),
        (True, 0, 1),
        (10, 2.0, 1),
        (10, 2, False),
        (10, 2, float("nan")),
    ],
)
def test_bad_counts_cannot_certify_a_bound(args):
    with pytest.raises(ValueError):
        dot_budget_feasibility(*args)


@pytest.fixture
def packet(tmp_path):
    for relative in (REGISTRY, TEMPLATE, WITNESS, "data/manifest.json"):
        dest = tmp_path / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, dest)
    return tmp_path


def test_fresh_readback_matches_recorded_receipt_and_no_positive_claim(packet):
    recorded = json.loads((ROOT / "docs/data/uniqueness_feasibility_20261027.json").read_text())
    fresh = audit(packet, [r["candidate_dot_count"] for r in recorded["budgets"]])
    for key in ("witness", "template", "registry", "coverage", "budgets"):
        assert fresh[key] == recorded[key]
    assert fresh["impossible_budget_found"] and not fresh["submission_authorized"]
    assert fresh["new_tiffs"] == fresh["new_experiments"] == fresh["competition_slots_used"] == 0
    assert fresh["holdout_dti"] is fresh["leaderboard_estimate"] is None
    html = render(fresh)
    assert "SUBMIT: NO" in html and "NOT_RULED_OUT is not PASS" in html
    assert "Catalogue-hide-and-recover" in html
    fresh["checked_utc"] = '<script>alert("unsafe")</script>'
    assert "<script>" not in render(fresh)


@pytest.mark.parametrize("damage", ["template", "witness", "content_hash", "missing", "cache_path"])
def test_changed_or_missing_comparator_fails_closed(packet, damage):
    registry_path = packet / REGISTRY
    registry = json.loads(registry_path.read_text())
    row = next(r for r in registry["unique_rasters"] if r["file"] == WITNESS)
    if damage in ("template", "witness"):
        path = packet / (TEMPLATE if damage == "template" else WITNESS)
        path.write_bytes(path.read_bytes() + b"tampered")
    elif damage == "content_hash":
        row["footprint_sha256"] = "0" * 64
    elif damage == "cache_path":
        row["cache_path"] = "../other.tif"
    else:
        registry["unique_rasters"].remove(row)
    registry_path.write_text(json.dumps(registry))
    with pytest.raises(ValueError):
        audit(packet, [37654])


def test_no_budget_is_an_error(packet):
    with pytest.raises(ValueError):
        audit(packet, [])


@pytest.mark.parametrize("k,exit_code", [(37654, 2), (20000, 0)])
def test_cli_exit_zero_does_not_mean_authorized(tmp_path, k, exit_code):
    output = tmp_path / "receipt.json"
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/check_uniqueness_feasibility.py"),
            "--dot-budget",
            str(k),
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    assert result.returncode == exit_code, result.stderr
    report = json.loads(output.read_text())
    assert report["submission_authorized"] is False
    assert report["new_tiffs"] == 0
    assert not list(tmp_path.glob("*.tif"))
