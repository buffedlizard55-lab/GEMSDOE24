"""Immutable TNR1 diagnostics, exact files, fail-closed release, current UI."""

from __future__ import annotations

import copy
import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
import rasterio

from gems.submission import check_variants
from gems.validator import sha256_file

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from run_tnr1_lane import verify_recorded  # noqa: E402

CARD_PATH = Path("evidence/tnr1_run_card_20261026.json")
REPORT_PATH = Path("evidence/tnr1_experiment_20261026.json")
PUBLISHED_PATH = Path("docs/data/tnr1_run_card.json")
CARD = json.loads((ROOT / CARD_PATH).read_text())


@pytest.fixture
def packet(tmp_path):
    files = [
        CARD_PATH,
        REPORT_PATH,
        PUBLISHED_PATH,
        Path("registry/tnr1_union_20261026.json"),
        Path("evidence/gvc1_run_card_20261025.json"),
        Path("evidence/sahg1_run_card_20261025.json"),
        Path("data/bridge/sample_submission.tif"),
    ]
    name = CARD["submission_name"]
    files += [
        Path("docs/downloads") / item
        for item in (
            name,
            CARD["nan_outside_companion"]["file"],
            name[:-4] + ".note.txt",
            name[:-4] + ".preflight.json",
        )
    ]
    for relative in files:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
    return tmp_path


def update_card(root, mutate):
    card = copy.deepcopy(CARD)
    mutate(card)
    report = json.loads((root / REPORT_PATH).read_text())
    report["run_card"] = card
    for relative, data in ((CARD_PATH, card), (PUBLISHED_PATH, card), (REPORT_PATH, report)):
        (root / relative).write_text(json.dumps(data, allow_nan=False))


def test_original_execution_source_and_recorded_diagnostics_verify():
    assert verify_recorded(ROOT, source_history=True) == CARD
    assert CARD["experiments_run"] == CARD["candidate_arms"] == CARD["matched_controls"] == 1
    assert CARD["verdict"] == "negative"
    assert CARD["submission_slots_used"] == 0
    assert CARD["ok_to_submit"] is CARD["submission_authorized"] is False
    assert "duplicate-final-dots" in CARD["stopped_reason"]
    assert CARD["raw_feature_canary"]["feature_count"] == 66
    assert CARD["oof_transform_canary"]["feature_count"] == 13


def test_packet_verification_needs_no_training_cache_or_registry_rasters(packet):
    assert not (packet / "data/prepared").exists()
    assert not (packet / "data/research").exists()
    assert verify_recorded(packet, source_history=False) == CARD


@pytest.mark.parametrize(
    "change",
    [
        lambda c: c.update(verdict="promote"),
        lambda c: c.update(ok_to_submit=True),
        lambda c: c.update(submission_authorized=True),
        lambda c: c.update(organizer_confirmed_score=0.9),
        lambda c: c.update(note="x" * 141),
        lambda c: c.update(submission_name="../escape-zeros.tif"),
        lambda c: c.update(raster_sha256="0" * 64),
        lambda c: c["nan_outside_companion"].update(file="../escape-nan.tif"),
        lambda c: c["holdout"].update(dti=0.9),
        lambda c: c["paired_comparison"].update(paired_delta_dti=0.1),
        lambda c: c["paired_comparison"].update(ci95_strictly_positive=True),
        lambda c: c["raw_feature_canary"].update(two_polarities_checked=False),
        lambda c: c["raw_feature_canary"]["features"]["input/rtp"].update(pooled_auc=0.01),
        lambda c: c["correlation_overlap_vs_registry"]["final_dots"].update(passed=True),
        lambda c: c["correlation_overlap_vs_registry"]["final_dots"].update(overlap_limit=0.8),
        lambda c: c["correlation_overlap_vs_registry"]["final_dots"]["rows"].pop(),
        lambda c: c["correlation_overlap_vs_registry"]["final_dots"]["rows"][-1].update(
            footprint_sha256="0" * 64
        ),
        lambda c: c["exact_file_nuisance_audit"].update(candidate_sha256="0" * 64),
        lambda c: c["exact_file_nuisance_audit"]["candidate"].update(holm_p_value=0.01),
        lambda c: c["recorded_baseline_comparisons"]["recorded_current_highest_gvc1"].update(
            candidate_point_estimate_higher=True
        ),
    ],
)
def test_even_consistently_edited_copies_cannot_change_the_negative_receipt(packet, change):
    update_card(packet, change)
    with pytest.raises(ValueError):
        verify_recorded(packet, source_history=False)


def test_binary_or_preflight_or_note_tampering_fails(packet):
    path = packet / "docs/downloads" / CARD["submission_name"]
    note = path.with_suffix(".note.txt")
    note.write_text("A different note")
    with pytest.raises(ValueError, match="note"):
        verify_recorded(packet, source_history=False)
    note.write_text(CARD["note"] + "\n")
    pre_path = path.with_suffix(".preflight.json")
    original = pre_path.read_text()
    pre = json.loads(original)
    pre["requirements"]["hash_bound_scientific_promotion"] = True
    pre_path.write_text(json.dumps(pre))
    with pytest.raises(ValueError, match="preflight"):
        verify_recorded(packet, source_history=False)
    pre_path.write_text(original)
    raw = bytearray(path.read_bytes())
    raw[-1] ^= 1
    path.write_bytes(raw)
    with pytest.raises(ValueError, match="hash"):
        verify_recorded(packet, source_history=False)


def test_exact_arrays_and_two_explicit_outside_conventions():
    template = ROOT / "data/bridge/sample_submission.tif"
    primary = ROOT / "docs/downloads" / CARD["submission_name"]
    twin = primary.with_name(CARD["nan_outside_companion"]["file"])
    with rasterio.open(template) as ds:
        fp = np.isfinite(ds.read(1))
    with rasterio.open(primary) as ds, rasterio.open(twin) as twin_ds:
        values, companion = ds.read(1), twin_ds.read(1)
        assert ds.dtypes == ("float32",) and ds.count == 1
        assert ds.shape == (3730, 3292) and ds.crs.to_epsg() == 32611
        assert np.isfinite(values).all() and set(np.unique(values)) == {0, 1}
        assert not values[~fp].any()
        assert np.isnan(companion[~fp]).all()
        assert np.array_equal(values[fp], companion[fp])
    with rasterio.open(ROOT / "data/bridge/existing_faults.tif") as ds:
        assert not values[np.nan_to_num(ds.read(1)) > 0].any()
    assert int((values > 0).sum()) == 37722
    assert sha256_file(primary) == CARD["raster_sha256"]
    assert check_variants(primary, template)["official_format_compliant"] is False
    assert check_variants(twin, template)["official_format_compliant"] is True
    registry = json.loads((ROOT / "registry/tnr1_union_20261026.json").read_text())
    import hashlib

    content = hashlib.sha256(values[fp].astype("<f4").tobytes()).hexdigest()
    assert all(row["footprint_sha256"] != content for row in registry["unique_rasters"])
    # Content inequality is not enough: real-method and literal novelty fail.
    assert not CARD["correlation_overlap_vs_registry"]["final_dots"]["passed"]


def test_current_best_leads_and_tnr1_is_historical():
    active = json.loads((ROOT / "docs/data/active_lane.json").read_text())
    assert active["lane"] == "H24-TNR1"  # active lane identity, not point-best selector
    assert active["artifact"]["sha256"] == CARD["raster_sha256"]
    assert active["artifact"]["file"] == CARD["submission_name"]
    assert active["ok_to_submit"] is active["submission_authorized"] is False
    current = json.loads((ROOT / "docs/data/current_best_review.json").read_text())
    old = json.loads((ROOT / "docs/data/rshg1_download.json").read_text())
    for relative in (
        "index.html",
        "docs/index.html",
        "executive-summary.html",
        "docs/executive-summary.html",
    ):
        html = (ROOT / relative).read_text()
        historical = html.index('id="historical-tnr1')
        current_section = html[:historical]
        historical_section = html[historical:]
        assert 'download="' + current["submission_name"] + '"' in current_section
        assert "DOWNLOAD: YES" in current_section and "SUBMIT: NO" in current_section
        assert "NOT OK TO SUBMIT" in current_section and "DO NOT SUBMIT" in current_section
        assert "No human-inspector fallback" in current_section
        assert CARD["submission_name"] not in current_section
        assert old["file"] not in current_section and old["file"] in historical_section
        assert current["raster_sha256"] in current_section
        assert 'data-copy="#note-tnr1"' not in current_section
        assert 'data-copy="#note-tnr1"' in historical_section


def test_tnr1_render_does_not_claim_to_be_latest():
    from tnr1_site import render

    result = render(ROOT)
    assert "Historical negative experiment · H24-TNR1" in result["overview"]
    assert "Historical TNR1 result" in result["executive"]
    assert "Historical **H24-TNR1** result" in result["status_md"]
    assert "Latest **H24-TNR1**" not in result["status_md"]


def test_current_receipt_missing_never_silently_falls_back(packet):
    from tnr1_site import render

    (packet / "docs/data/active_lane.json").write_text(json.dumps({"lane": "H24-TNR1"}))
    (packet / CARD_PATH).unlink()
    with pytest.raises(ValueError, match="no silent"):
        render(packet)


def test_already_run_guard_refuses_before_training():
    before = (ROOT / CARD_PATH).read_bytes()
    result = subprocess.run(
        [sys.executable, "scripts/run_tnr1_lane.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode != 0
    assert "already" in result.stderr.lower() or "frozen" in result.stderr.lower()
    assert (ROOT / CARD_PATH).read_bytes() == before


def test_full_current_request_is_embedded_in_readme():
    brief = (ROOT / "knowledge/owner_brief_2026-10-26.md").read_text()
    readme = (ROOT / "README.md").read_text()
    assert brief in readme
    assert "PARALLEL-RUN PROTOCOL" in brief and "GEMSDOE92" in brief
    assert "fully unique" in readme or "gate-passing unique" in readme
    assert "not been achieved" in readme or "not** been achieved" in readme
