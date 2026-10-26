"""Artifact review is exhaustive within its pins, but never a score or authorization."""

import copy
import importlib.util
import itertools
from pathlib import Path

import numpy as np
import pytest
from scipy.ndimage import distance_transform_edt

from gems.github_archive import git_blob_sha
from gems.novelty import classify_space_filling_control

ROOT = Path(__file__).resolve().parents[1]


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


AUDIT = module("audit_priority_portfolio")
CACHE = module("cache_priority_registry")


def tiny_snapshot():
    sources, rows = [], []
    for n in AUDIT.SITES:
        repo, ref, path, blob = f"buffedlizard55-lab/GEMSDOE{n}", "a" * 40, "docs/a.tif", "b" * 40
        sources.append({"repo": repo, "ref": ref, "files": [{"path": path, "blob_sha": blob}]})
        rows.append({"repo": repo, "ref": ref, "file": path, "blob_sha": blob})
    manifest = {
        "sources": [{"repo": s["repo"], "ref": s["ref"]} for s in sources],
        "unique_rasters": rows[:-1],
        "duplicate_content_variants": [],
        "rejected": rows[-1:],
        "footprint_identity": {"policy": "sample-template"},
    }
    return manifest, {"sources": sources}


def test_partial_snapshot_cannot_claim_all_nine_or_drop_invalid_files():
    manifest, snapshot = tiny_snapshot()
    assert len(AUDIT.validate_snapshot(manifest, snapshot)) == 9
    for section in ("unique_rasters", "rejected"):
        bad = copy.deepcopy(manifest)
        bad[section].pop()
        with pytest.raises(ValueError, match="Every discovered"):
            AUDIT.validate_snapshot(bad, snapshot)
    snapshot["sources"].pop()
    with pytest.raises(ValueError, match="All nine"):
        AUDIT.validate_snapshot(manifest, snapshot)


def test_snapshot_cannot_mix_refs_duplicate_rows_or_silently_change_masks():
    manifest, snapshot = tiny_snapshot()
    for mutation in ("ref", "duplicate", "mask"):
        bad = copy.deepcopy(manifest)
        if mutation == "ref":
            bad["unique_rasters"][0]["ref"] = "c" * 40
        elif mutation == "duplicate":
            bad["unique_rasters"].append(bad["unique_rasters"][0])
        else:
            bad["footprint_identity"]["policy"] = "legacy-science"
        with pytest.raises(ValueError):
            AUDIT.validate_snapshot(bad, snapshot)


def test_only_self_encodings_are_excluded_not_cross_site_copies_or_local_lattice():
    candidate = {
        "repo": "own/site",
        "file": "docs/candidate-zeros.tif",
        "footprint_sha256": "1" * 64,
    }
    companion = {**candidate, "file": "docs/candidate-nan.tif"}
    peer_copy = {**candidate, "repo": "other/site"}
    lattice = {
        "repo": "local historic references",
        "file": "inputs/lattice.tif",
        "footprint_sha256": "2" * 64,
    }
    manifest = {
        "unique_rasters": [candidate, lattice],
        "duplicate_content_variants": [companion, peer_copy],
    }
    result = AUDIT.comparator_entries(candidate, manifest)
    assert len(result) == 2
    assert {r["repo"] for r in result} == {"other/site", "local historic references"}
    manifest["duplicate_content_variants"].pop()
    assert len(AUDIT.comparator_entries(candidate, manifest)) == 1
    manifest["duplicate_content_variants"].append(
        {**candidate, "file": "docs/renamed-method-zeros.tif"}
    )
    assert len(AUDIT.comparator_entries(candidate, manifest)) == 2


def test_api_cache_honors_custom_directory_and_immutable_ref(monkeypatch, tmp_path):
    monkeypatch.setattr(CACHE, "ROOT", tmp_path)
    payloads = {"a" * 40: b"old bytes", "b" * 40: b"new bytes"}
    calls = []

    def fetch(endpoint):
        calls.append(endpoint)
        return payloads[endpoint.split("ref=")[-1]]

    monkeypatch.setattr(CACHE, "gh", fetch)
    output = []
    for ref, raw in payloads.items():
        output.append(
            CACHE.cache_one(
                ("owner/repo", ref, {"path": "docs/a.tif", "blob_sha": git_blob_sha(raw)}),
                tmp_path / "custom",
            )
        )
    assert output[0]["cache_path"] != output[1]["cache_path"]
    assert all((tmp_path / r["cache_path"]).is_relative_to(tmp_path / "custom") for r in output)
    assert (tmp_path / output[0]["cache_path"]).read_bytes() == b"old bytes"
    assert (tmp_path / output[1]["cache_path"]).read_bytes() == b"new bytes"
    assert len(calls) == 2


def test_bad_api_bytes_are_not_installed_and_paths_cannot_escape(monkeypatch, tmp_path):
    monkeypatch.setattr(CACHE, "ROOT", tmp_path)
    monkeypatch.setattr(CACHE, "gh", lambda endpoint: b"wrong")
    with pytest.raises(ValueError, match="Git object"):
        CACHE.cache_one(
            ("owner/repo", "a" * 40, {"path": "a.tif", "blob_sha": git_blob_sha(b"right")}),
            tmp_path,
        )
    assert not list(tmp_path.rglob("*.tif"))
    with pytest.raises(ValueError, match="Unsafe"):
        CACHE.cache_one(
            ("owner/repo", "a" * 40, {"path": "../a.tif", "blob_sha": "b" * 40}), tmp_path
        )
    with pytest.raises(ValueError, match="immutable"):
        CACHE.cache_one(("owner/repo", "main", {"path": "a.tif", "blob_sha": "b" * 40}), tmp_path)


def test_pigeonhole_minimum_matches_exhaustive_subset_enumeration():
    fp = np.ones((3, 4), bool)
    ref = np.zeros_like(fp)
    ref[1, 1] = True
    radius, budget = 1.0, 8
    result = classify_space_filling_control(fp, ref, radius_px=radius, candidate_dot_count=budget)
    covered = (distance_transform_edt(~ref) <= radius).ravel()
    minimum = min(
        float(covered[list(ids)].mean()) for ids in itertools.combinations(range(fp.size), budget)
    )
    assert result["pigeonhole_min_overlap_for_candidate_size"] == minimum


@pytest.mark.parametrize(
    "kwargs",
    [
        {"radius_px": float("nan")},
        {"radius_px": -1},
        {"radius_px": True},
        {"coverage_threshold": float("inf")},
        {"coverage_threshold": 1.1},
        {"candidate_dot_count": True},
        {"candidate_dot_count": 2.5},
        {"candidate_dot_count": 0},
        {"candidate_dot_count": 5},
    ],
)
def test_obstruction_rejects_malformed_parameters(kwargs):
    with pytest.raises(ValueError):
        classify_space_filling_control(np.ones((2, 2)), np.eye(2), **kwargs)


def test_obstruction_rejects_broadcastable_or_nonfinite_masks():
    with pytest.raises(ValueError):
        classify_space_filling_control(np.ones((3, 3)), np.ones((1, 3)))
    with pytest.raises(ValueError):
        classify_space_filling_control(np.ones((3, 3)), np.full((3, 3), np.nan))


def test_prepared_cache_reuse_checks_bytes_inputs_and_layout(monkeypatch, tmp_path):
    import json

    from gems.validator import sha256_file

    prepare = module("prepare_data")
    monkeypatch.setattr(prepare, "ROOT", tmp_path)
    source = tmp_path / "source.bin"
    source.write_bytes(b"pinned raw input")
    cache, meta = tmp_path / "features.npy", tmp_path / "features.json"
    np.save(cache, np.ones((4, 2), dtype=np.float32))
    metadata = {
        "names": ["x", "y"],
        "shape": [4, 2],
        "sha256": sha256_file(cache),
        "inputs": {"source.bin": sha256_file(source)},
    }
    meta.write_text(json.dumps(metadata))
    assert prepare.verify_cached_preparation(cache, meta, (source,), (4, 2), ["x", "y"]) == metadata
    with pytest.raises(ValueError, match="layout"):
        prepare.verify_cached_preparation(cache, meta, (source,), (4, 2), ["y", "x"])
    source.write_bytes(b"changed input")
    with pytest.raises(ValueError, match="inputs changed"):
        prepare.verify_cached_preparation(cache, meta, (source,), (4, 2), ["x", "y"])
    source.write_bytes(b"pinned raw input")
    np.save(cache, np.zeros((4, 2), dtype=np.float32))
    with pytest.raises(ValueError, match="checksum"):
        prepare.verify_cached_preparation(cache, meta, (source,), (4, 2), ["x", "y"])
    np.save(cache, np.ones((4, 2), dtype=np.float64))
    metadata["sha256"] = sha256_file(cache)
    meta.write_text(json.dumps(metadata))
    with pytest.raises(ValueError, match="array layout"):
        prepare.verify_cached_preparation(cache, meta, (source,), (4, 2), ["x", "y"])


def test_frozen_manifest_rehydration_preserves_ids_and_history(monkeypatch, tmp_path):
    from gems.validator import sha256_file

    monkeypatch.setattr(CACHE, "ROOT", tmp_path)
    source = tmp_path / "data/research/new/source.tif"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"unchanged pinned bytes")
    row = {
        "repo": "owner/repo",
        "ref": "a" * 40,
        "file": "docs/a.tif",
        "id": "old-id",
        "sha256": sha256_file(source),
        "cache_path": "data/research/old/a.tif",
        "footprint_sha256": "c" * 64,
    }
    original = {
        "sources": [{"repo": "owner/repo", "ref": "a" * 40}],
        "unique_rasters": [row],
        "duplicate_content_variants": [],
        "rejected": [],
        "generated_utc": "frozen",
    }
    restored = copy.deepcopy(original)
    restored["unique_rasters"][0].update(id="new-id", cache_path="data/research/new/source.tif")
    restored["footprint_identity"] = {"policy": "legacy-science"}
    saved = copy.deepcopy(original)
    assert CACHE.preserve_frozen_manifest(original, restored) == saved
    assert (tmp_path / row["cache_path"]).read_bytes() == source.read_bytes()
    assert original == saved
    restored["unique_rasters"][0]["sha256"] = "f" * 64
    with pytest.raises(ValueError, match="identity"):
        CACHE.preserve_frozen_manifest(original, restored)
    restored["unique_rasters"][0]["sha256"] = row["sha256"]
    restored["footprint_identity"]["policy"] = "sample-template"
    with pytest.raises(ValueError, match="policy"):
        CACHE.preserve_frozen_manifest(original, restored)


def portfolio_module(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    return module("portfolio_summary")


def test_completed_portfolio_audit_is_exhaustive_and_negative(monkeypatch):
    import json

    summary = portfolio_module(monkeypatch)
    audit = json.loads((ROOT / summary.AUDIT_PATH).read_text())
    manifest = json.loads((ROOT / "registry/priority_rasters_20261026_portfolio.json").read_text())
    assert summary.validate_audit(audit, manifest) == audit
    assert audit["counts"]["files"] == 326
    assert audit["counts"]["format_rejected"] == 2
    assert audit["footprint"]["symmetric_difference_pixels"] == 0
    assert all(not x["final_dot_novelty"]["passed"] for x in audit["named_artifact_audits"])
    best = next(
        x
        for x in audit["named_artifact_audits"]
        if x["site"] == "GEMSDOE24" and x["role"] == "source_featured_research_not_ranked"
    )
    eul = next(r for r in best["final_dot_novelty"]["rows"] if "gems24-eul1" in r["file"])
    assert eul["duplicate"] is True and eul["candidate_dot_overlap_within_3px"] > 0.86


@pytest.mark.parametrize(
    "mutation",
    [
        "forecast",
        "authorization",
        "missing_file",
        "missing_target",
        "missing_comparator",
        "duplicate_flag",
        "wrong_maximum",
        "invalid_correlation",
        "preplacement",
    ],
)
def test_summary_rejects_optimistic_or_partial_evidence(monkeypatch, mutation):
    import json

    summary = portfolio_module(monkeypatch)
    audit = json.loads((ROOT / summary.AUDIT_PATH).read_text())
    manifest = json.loads((ROOT / "registry/priority_rasters_20261026_portfolio.json").read_text())
    first = audit["named_artifact_audits"][0]
    if mutation == "forecast":
        audit["leaderboard_estimate"] = 0.5
    elif mutation == "authorization":
        audit["submission_authorized"] = True
    elif mutation == "missing_file":
        audit["inventory"].pop()
    elif mutation == "missing_target":
        audit["named_artifact_audits"].pop()
    elif mutation == "missing_comparator":
        first["final_dot_novelty"]["rows"].pop()
        first["final_dot_novelty"]["registry_unique_rasters"] -= 1
    elif mutation == "duplicate_flag":
        row = first["final_dot_novelty"]["rows"][0]
        row["duplicate"] = not row["duplicate"]
    elif mutation == "wrong_maximum":
        first["final_dot_novelty"]["max_dot_overlap"] = 0.1
    elif mutation == "invalid_correlation":
        first["final_dot_novelty"]["rows"][0]["raw_spearman"] = 1.01
    else:
        first["preplacement_surface_novelty"] = {"passed": True}
    with pytest.raises(ValueError):
        summary.validate_audit(audit, manifest)


def test_source_holdout_requires_ci_evaluator_and_withheld_count(monkeypatch):
    summary = portfolio_module(monkeypatch)
    card = {
        "holdout_dti": {
            "pooled_dti": 0.1,
            "ci_95": [0.08, 0.12],
            "evaluator_version": "test-v1",
            "withheld_positives": 10,
        }
    }
    assert summary.source_holdout(25, card)["label"] == "HOLDOUT-DTI"
    card["holdout_dti"]["withheld_positives"] = True
    with pytest.raises(ValueError):
        summary.source_holdout(25, card)
    assert summary.source_holdout(27, {})["dti"] is None
    assert summary.source_holdout(30, {})["dti"] is None
    assert summary.source_holdout(31, {})["dti"] is None
