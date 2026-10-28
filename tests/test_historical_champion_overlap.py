"""The nine-site overlap audit stays pinned, directed, and explicitly incomplete."""

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "audit_historical_champion_overlap", ROOT / "scripts/audit_historical_champion_overlap.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

SITES = [24, 25, 27, 28, 30, 31, 32, 33, 36]


def _fixture(tmp_path, monkeypatch, overlap_bad=False):
    monkeypatch.setattr(MODULE, "ROOT", tmp_path)
    candidate = tmp_path / "candidate.tif"
    candidate.write_bytes(b"candidate")
    report_path = tmp_path / "historical.json"
    cache_root = tmp_path / "cache"
    template = tmp_path / "template.tif"
    template.write_bytes(b"template")
    rows = []
    source_bytes = {}
    for number in SITES:
        site = f"GEMSDOE{number}"
        rel = f"docs/downloads/{site}.tif"
        body = f"pinned-{site}".encode()
        source_bytes[site] = body
        rows.append(
            {
                "site": site,
                "source_url": (
                    f"https://github.com/buffedlizard55-lab/{site}/blob/{'a' * 40}/{rel}"
                ),
                "sha256": hashlib.sha256(body).hexdigest(),
                "owner_reported_unverified": {"owner_reported": None},
            }
        )
    report_path.write_text(json.dumps({"rows": rows}))
    candidate_mask = np.zeros((20, 20), dtype=bool)
    candidate_mask[2:8, 2] = True
    reference_masks = {}
    for number in SITES:
        site = f"GEMSDOE{number}"
        reference = np.zeros_like(candidate_mask)
        if overlap_bad and number == 24:
            reference[2:8, 2] = True
        else:
            reference[15:18, 15] = True
        reference_masks[site] = reference

    def fetch(repository, rel, ref, dest):
        site = repository.rsplit("/", 1)[-1]
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(source_bytes[site])

    def fake_validation(path, _template):
        return {"format_valid": True, "sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest()}

    def fake_read_mask(path):
        path = Path(path)
        if path == candidate:
            mask = candidate_mask
        else:
            mask = reference_masks[path.parent.name]
        return mask, {"crs": "EPSG:32611", "transform": [1, 0, 0, 0, -1, 0], "shape": [20, 20]}

    monkeypatch.setattr(MODULE, "check_variants", fake_validation)
    monkeypatch.setattr(MODULE, "read_dot_mask", fake_read_mask)
    return candidate, report_path, template, cache_root, fetch


def test_audit_checks_all_nine_hash_pinned_historical_files(tmp_path, monkeypatch):
    args = _fixture(tmp_path, monkeypatch)
    result = MODULE.audit(*args[:4], fetch=args[4])
    assert result["references_compared"] == 9
    assert result["passes_nine_historical_file_overlap_threshold"] is True
    assert result["exact_dot_mask_aliases"] == []
    assert result["full_registry_uniqueness"] == "NOT ESTABLISHED"
    assert result["submission_authorized"] is False
    assert result["comparisons"][0]["candidate_within_3px_of_reference"] == 0.0


def test_audit_fails_the_threshold_when_one_reference_is_too_close(tmp_path, monkeypatch):
    args = _fixture(tmp_path, monkeypatch, overlap_bad=True)
    result = MODULE.audit(*args[:4], fetch=args[4])
    assert result["max_overlap_site"] == "GEMSDOE24"
    assert result["max_candidate_dot_overlap"] == 1.0
    assert result["passes_nine_historical_file_overlap_threshold"] is False


def test_audit_rejects_incomplete_or_mismatched_site_sets(tmp_path, monkeypatch):
    args = _fixture(tmp_path, monkeypatch)
    args[1].write_text(json.dumps({"rows": []}))
    with pytest.raises(ValueError, match="exactly the nine named focus sites"):
        MODULE.audit(*args[:4], fetch=args[4])


def test_source_parser_rejects_mutable_refs_or_nonfocus_hosts():
    with pytest.raises(ValueError, match="immutable matching focus-site"):
        MODULE.pinned_source(
            {
                "site": "GEMSDOE24",
                "source_url": "https://github.com/buffedlizard55-lab/GEMSDOE24/blob/main/docs/downloads/x.tif",
                "sha256": "a" * 64,
            }
        )
