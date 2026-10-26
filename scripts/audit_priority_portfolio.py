#!/usr/bin/env python3
"""Reopen a complete pinned nine-site artifact snapshot; never train or authorize.

Uses the shared validator and novelty implementation. Retains all invalid files,
encoding aliases and literal controls. No leaderboard projection is computed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems.benchmarks import recorded_point_best  # noqa: E402
from gems.footprint import load_footprint  # noqa: E402
from gems.github_archive import git_blob_sha, safe_relative  # noqa: E402
from gems.novelty import classify_space_filling_control, compare_registry  # noqa: E402
from gems.submission import check_variants  # noqa: E402
from gems.validator import sha256_file  # noqa: E402

SITES = (24, 25, 27, 28, 30, 31, 32, 33, 36)
VERSION = "nine-site-artifact-audit-v1"
MANIFEST = ROOT / "registry/priority_rasters_20261026_portfolio.json"
SNAPSHOT = ROOT / "registry/priority_source_snapshot_20261026_portfolio.json"
OUTPUT = ROOT / "evidence/portfolio_artifact_audit_20261026.json"
FEATURED = {
    24: "gems24-dprf1-stitched-oof-tworegime-20261026-81849d67c8bf-zeros.tif",
    25: "gems25-h71-hgpc-blind-b2-sapd3-k3p5-20261026-9eb0c31e5149-zeros.tif",
    27: "gems27-h31-drcg-wl-celf28-20261026-cf8e1bbef244-allfinite.tif",
    28: "gems28-s20-nchc-20261026-d432a1d5d6ee-allfinite.tif",
    30: "GEMSDOE30-geothermal-corridor-offcat-d3-20261026T160300Z.tif",
    31: "gemsdoe31-csdu-stepover-8cf9dc27-allfinite.tif",
    32: "gemsdoe32-h44-spcp-sarpu-curvconduit-37654-20261026T053000Z-38f7995a-zeros.tif",
    33: "gemsdoe33-a33-r3-llc-37654-20261026-7f91f9f3ced9-zeros.tif",
    36: "gemsdoe36-mto36-ortho-contact-20261026-c41282e9da7a-zeros.tif",
}


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".partial")
    temporary.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def all_rows(manifest):
    return [
        row
        for key in ("unique_rasters", "duplicate_content_variants", "rejected")
        for row in manifest[key]
    ]


def validate_snapshot(manifest, snapshot):
    """A partial/mismatched registry must never look like a complete audit."""
    expected_repos = {f"buffedlizard55-lab/GEMSDOE{n}" for n in SITES}
    pins = {row["repo"]: row["ref"] for row in snapshot["sources"]}
    if len(snapshot["sources"]) != len(SITES) or set(pins) != expected_repos:
        raise ValueError("All nine source repositories are required exactly once")
    if any(not re.fullmatch(r"[0-9a-f]{40}", ref) for ref in pins.values()):
        raise ValueError("Immutable commit refs required")
    if manifest["sources"] != [{"repo": s["repo"], "ref": s["ref"]} for s in snapshot["sources"]]:
        raise ValueError("Manifest and discovery snapshot pins differ")
    if manifest.get("footprint_identity", {}).get("policy") != "sample-template":
        raise ValueError("This audit requires an explicit sample-template footprint")
    expected = {}
    for source in snapshot["sources"]:
        for entry in source["files"]:
            path = str(safe_relative(entry["path"]))
            if not path.lower().endswith((".tif", ".tiff")):
                continue
            key = (source["repo"], path)
            if key in expected:
                raise ValueError("Duplicate discovery entry")
            expected[key] = entry["blob_sha"]
    actual = {}
    for row in all_rows(manifest):
        if row["repo"] == "local historic references":
            continue
        key = (row["repo"], row["file"])
        if key in actual or row["ref"] != pins.get(row["repo"]):
            raise ValueError("Duplicate file or unpinned source in manifest")
        actual[key] = row.get("blob_sha")
    if actual != expected:
        raise ValueError("Every discovered TIFF, including rejected files, must be inventoried")
    return pins


def normalized_encoding(path):
    stem = str(Path(path).with_suffix(""))
    return re.sub(r"-(nan|zeros|zero|allfinite|nan-outside)$", "", stem)


def comparator_entries(candidate, manifest):
    """Exclude only this artifact's own encodings, never a cross-site alias/control."""
    groups = defaultdict(list)
    for row in manifest["unique_rasters"] + manifest["duplicate_content_variants"]:
        groups[row["footprint_sha256"]].append(row)
    result = []
    for digest, aliases in groups.items():
        other = [
            row
            for row in aliases
            if not (
                row["repo"] == candidate["repo"]
                and normalized_encoding(row["file"]) == normalized_encoding(candidate["file"])
            )
        ]
        if other:
            representative = min(other, key=lambda row: (row["repo"], row["file"]))
            result.append({**representative, "id": "content-" + digest[:16]})
    return result


def file_inventory(manifest, snapshot, fp, known):
    expected = {
        (s["repo"], entry["path"]): entry["blob_sha"]
        for s in snapshot["sources"]
        for entry in s["files"]
    }
    rows = []
    for i, row in enumerate(all_rows(manifest)):
        path = ROOT / safe_relative(row["cache_path"])
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != row["sha256"]:
            raise ValueError(f"Changed cached TIFF: {row['file']}")
        if (
            row["repo"] != "local historic references"
            and git_blob_sha(raw) != expected[(row["repo"], row["file"])]
        ):
            raise ValueError(f"Git blob mismatch: {row['file']}")
        del raw
        checks = check_variants(path, ROOT / "data/bridge/sample_submission.tif")
        detail = {
            "repo": row["repo"],
            "ref": row["ref"],
            "file": row["file"],
            "sha256": checks["sha256"],
            "bytes": checks["bytes"],
            "source_url": row.get("source_url"),
            "format_valid": checks["format_valid"],
            "strict_all_finite_0_1": checks["checks"]["variant_strict_whole_array_no_nan_allowed"][
                "pass"
            ],
            "template_nan_outside_convention": checks["official_format_compliant"],
            "hard_failures": checks["hard_failures"],
            "footprint_sha256": row.get("footprint_sha256"),
            "positive_pixels": checks["in_footprint_positive_pixels"],
            "scientific_replay": "not performed",
            "submission_authorized": False,
        }
        with rasterio.open(path) as ds:
            a = ds.read(1)
        if a.shape == fp.shape:
            detail["nonfinite_inside_footprint"] = int((~np.isfinite(a[fp])).sum())
            detail["out_of_range_finite_inside"] = int(((a[fp] < 0) | (a[fp] > 1)).sum())
            detail["binary_inside"] = bool(np.isin(a[fp], [0, 1]).all())
            detail["positive_on_catalogue"] = int(((a > 0) & fp & known).sum())
            if checks["format_valid"]:
                digest = hashlib.sha256(np.asarray(a[fp], dtype="<f4").tobytes()).hexdigest()
                if row.get("footprint_sha256") != digest:
                    raise ValueError("Footprint identity changed during revalidation")
                detail["scored_domain_sha256"] = hashlib.sha256(
                    np.asarray(a[fp & ~known], dtype="<f4").tobytes()
                ).hexdigest()
        if not checks["format_valid"]:
            detail["validator_output"] = checks
        rows.append(detail)
        if i % 25 == 0:
            print(f"Shared format validation {i + 1}/{len(all_rows(manifest))}", flush=True)
    return rows


def resolve_named(manifest, site, filename):
    matches = [
        r
        for r in all_rows(manifest)
        if r["repo"] == f"buffedlizard55-lab/GEMSDOE{site}" and Path(r["file"]).name == filename
    ]
    if len(matches) != 1:
        raise ValueError(f"Missing or ambiguous named artifact: GEMSDOE{site}/{filename}")
    return matches[0]


def read_binary(row, fp):
    with rasterio.open(ROOT / safe_relative(row["cache_path"])) as ds:
        a = ds.read(1)
    if a.shape != fp.shape or not np.isin(a[fp], [0, 1]).all():
        raise ValueError("Binary aligned artifact required for ancestry")
    return fp & (a > 0)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--resume",
        action="store_true",
        help="Reuse only hash-bound exact stage receipts, never scores",
    )
    args = ap.parse_args()
    manifest, snapshot = json.loads(MANIFEST.read_text()), json.loads(SNAPSHOT.read_text())
    pins = validate_snapshot(manifest, snapshot)
    template = ROOT / "data/bridge/sample_submission.tif"
    with rasterio.open(template) as ds:
        fp = np.isfinite(ds.read(1))
    with rasterio.open(ROOT / "data/bridge/existing_faults.tif") as ds:
        known = fp & (ds.read(1) > 0)
    identity = {
        "version": VERSION,
        "manifest_sha256": sha256_file(MANIFEST),
        "snapshot_sha256": sha256_file(SNAPSHOT),
        "template_sha256": sha256_file(template),
        "catalogue_sha256": sha256_file(ROOT / "data/bridge/existing_faults.tif"),
        "novelty_source_sha256": sha256_file(ROOT / "src/gems/novelty.py"),
        "validator_source_sha256": sha256_file(ROOT / "src/gems/submission.py"),
        "audit_source_sha256": sha256_file(Path(__file__)),
    }
    stage = ROOT / "data/research/portfolio_20261026T1612Z/audit_stages"
    stage.mkdir(parents=True, exist_ok=True)
    inv_path = stage / "inventory.json"
    saved = json.loads(inv_path.read_text()) if args.resume and inv_path.exists() else {}
    if saved.get("identity") == identity:
        # Even on resume, every named byte must still match the frozen snapshot.
        for row in all_rows(manifest):
            if sha256_file(ROOT / safe_relative(row["cache_path"])) != row["sha256"]:
                raise ValueError("Changed cached artifact during resume")
        inventory = saved["rows"]
    else:
        inventory = file_inventory(manifest, snapshot, fp, known)
        write_json(inv_path, {"identity": identity, "rows": inventory})
    old = json.loads((ROOT / "evidence/peer_forensics_20261025.json").read_text())["artifacts"]
    targets = []
    historic_masks = {}
    for row in old:
        n = int(row["repo"].removeprefix("GEMSDOE"))
        selected = resolve_named(manifest, n, row["file"])
        if selected["sha256"] != row["sha256"]:
            raise ValueError("Historical named file changed; do not reassociate its owner score")
        targets.append((n, "historical_owner_maximum", selected))
        historic_masks[n] = read_binary(selected, fp)
    for n, name in FEATURED.items():
        targets.append((n, "source_featured_research_not_ranked", resolve_named(manifest, n, name)))
    results = []
    for n, role, row in targets:
        target_path = stage / f"{n}-{role}.json"
        receipt = (
            json.loads(target_path.read_text()) if args.resume and target_path.exists() else {}
        )
        if receipt.get("identity") != identity or receipt.get("artifact_sha256") != row["sha256"]:
            print(f"Full final-dot registry audit: GEMSDOE{n} {role}", flush=True)
            pred = read_binary(row, fp)
            entries = comparator_entries(row, manifest)
            novelty = compare_registry(pred, fp, entries, ROOT, dots=pred)
            receipt = {
                "identity": identity,
                "artifact_sha256": row["sha256"],
                "final_dot_novelty": novelty,
            }
            write_json(target_path, receipt)
        result = {
            "site": f"GEMSDOE{n}",
            "role": role,
            "file": row["file"],
            "sha256": row["sha256"],
            "ref": row["ref"],
            "source_url": row["source_url"],
            "download_url": row["source_url"] + "?raw=1",
            "format": next(
                x for x in inventory if x["repo"] == row["repo"] and x["file"] == row["file"]
            ),
            "final_dot_novelty": receipt["final_dot_novelty"],
            "preplacement_surface_novelty": None,
            "preplacement_limitation": "The original continuous surface was not replayed; final dots cannot stand in for it",
            "leaderboard_estimate": None,
            "estimate_status": "NOT_ESTIMABLE: no artifact-linked organizer receipts or validated out-of-sample calibration",
            "organizer_confirmed_score": None,
            "ok_to_submit": False,
            "scientific_holdout_replayed": False,
        }
        results.append(result)
    h33 = historic_masks[32]
    distance = distance_transform_edt(~known)
    lineage = {
        "class": "COMPUTED-ARTIFACT-GEOMETRY, not a score or hidden-label causal finding",
        "GEMSDOE25_equals_GEMSDOE30": bool(np.array_equal(historic_masks[25], historic_masks[30])),
        "GEMSDOE32_equals_GEMSDOE25_with_distance_gt_2px": bool(
            np.array_equal(h33, historic_masks[25] & (distance > 2))
        ),
        "GEMSDOE32_equals_GEMSDOE31_with_distance_gt_2px": bool(
            np.array_equal(h33, historic_masks[31] & (distance > 2))
        ),
        "historical_positive_pixels": {str(k): int(v.sum()) for k, v in historic_masks.items()},
        "difference_from_h33": {
            str(k): {"removed_to_h33": int((v & ~h33).sum()), "added_to_h33": int((h33 & ~v).sum())}
            for k, v in historic_masks.items()
        },
    }
    lattice_path = ROOT / "inputs/calibration/13gems_20261001_r13-lattice-s5_v2_nan-outside.tif"
    with rasterio.open(lattice_path) as ds:
        lattice = fp & (ds.read(1) > 0)
    controls = {
        "file": str(lattice_path.relative_to(ROOT)),
        "sha256": sha256_file(lattice_path),
        "geometry": classify_space_filling_control(fp, lattice, candidate_dot_count=37654),
        "interpretation": "An overlap lower bound above 0.70 is a mathematical obstruction at this budget, not proof of copied science. Control retained; no dot movement or policy exception.",
    }
    science_fp = load_footprint()
    counts = Counter(row["repo"] for row in inventory)
    best = recorded_point_best(ROOT)
    output = {
        "audit_version": VERSION,
        "checked_utc": datetime.now(timezone.utc).isoformat(),
        "identity": identity,
        "scope": manifest["scope"],
        "evidence_class": "COMPUTED-ARTIFACT-AUDIT; no new HOLDOUT-DTI or ORGANIZER-CONFIRMED result",
        "sources": [
            {"repo": repo, "ref": ref, "raster_files_audited": counts[repo]}
            for repo, ref in pins.items()
        ],
        "all_discovered_files_accounted_for": True,
        "counts": {
            "files": len(inventory),
            "distinct_valid_contents": len(manifest["unique_rasters"]),
            "encoding_or_content_aliases": len(manifest["duplicate_content_variants"]),
            "format_rejected": sum(not x["format_valid"] for x in inventory),
            "strict_all_finite_0_1": sum(
                x["strict_all_finite_0_1"] and x["format_valid"] for x in inventory
            ),
        },
        "footprint": {
            "template_pixels": int(fp.sum()),
            "historical_science_pixels": int(science_fp.sum()),
            "symmetric_difference_pixels": int((fp ^ science_fp).sum()),
            "differing_row_col": np.argwhere(fp ^ science_fp).tolist(),
            "past_metrics_rewritten": False,
        },
        "inventory": inventory,
        "named_artifact_audits": results,
        "h33_ancestry": lineage,
        "literal_lattice_obstruction": controls,
        "recorded_local_point_best_not_new_measurement": best,
        "preplacement_surfaces_replayed": False,
        "organizer_confirmed_scores": [],
        "leaderboard_estimate": None,
        "cross_site_performance_ranking": "Not established; different holdout protocols are not interchangeable",
        "submission_authorized": False,
        "new_tiffs_generated": 0,
        "new_experiments": 0,
        "slots_used": 0,
        "verdict": "negative",
    }
    write_json(OUTPUT, output)
    print(
        json.dumps(
            {
                "output": str(OUTPUT.relative_to(ROOT)),
                "counts": output["counts"],
                "lineage": lineage,
                "lattice": controls,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
