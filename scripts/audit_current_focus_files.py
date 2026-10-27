#!/usr/bin/env python3
"""Reopen one named current research TIFF and run card from each focus site.

Immutable GitHub refs were captured from the validated portfolio freshness feed
and are bound in a fixed source-pin manifest. Git blob identity, the shared
exact-file format validator and one decisive literal lattice
comparison are checked. This is not an exhaustive registry, a pre-placement
surface, a scientific replay, a leaderboard query, or a submission selector.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems import novelty, submission  # noqa: E402
from gems.github_archive import git_blob_sha, safe_relative  # noqa: E402
from gems.validator import sha256_file  # noqa: E402

LATTICE = "inputs/calibration/13gems_20261001_r13-lattice-s5_v2_nan-outside.tif"
PINS = "registry/current_focus_source_pins_20261027.json"
PINS_SHA256 = "1bbf6e13cf0fccdc3acbbeee669b49e738f58e01496280a1d424e7aa510b42b3"
# These are named source-featured artifacts at the feed refs, not a claim that
# every later experiment was inventoried or that any holdout ranks globally.
SELECTED = {
    24: (
        "24gems-catalogue-offset-geothermal-proximity-20261027T114303Z-578c30176163-zeros.tif",
        "evidence/unique_experiment7.json",
    ),
    25: (
        "gems25-h74-rmps-subsurf-catfree-b2-37654-20261026-3751606e1ce5-zeros.tif",
        "registry/run_card_h74_2026-10-26.json",
    ),
    27: (
        "gems27-h31-drcg-wl-celf28-20261026-cf8e1bbef244-allfinite.tif",
        "evidence/h31_s10_run_card_2026-10-26.json",
    ),
    28: ("gems28-s22-ctxhgb-20261026-e23dabcec6e2-allfinite.tif", "evidence/s22c_run_card.json"),
    30: (
        "gems30-CSR1-44090-20261026-502fb5948335-zeros.tif",
        "docs/research/2026-10-26-csr/run-card.json",
    ),
    31: (
        "gemsdoe31-h31y-regime-mosaic-37654-20261026-66162f1f-zeros.tif",
        "evidence/h31ym/run_card.json",
    ),
    32: (
        "gemsdoe32-h47-ldgi-dualhorizon-corridor-37654-20261026T230609Z-0eb8a25c-zeros.tif",
        "evidence/h47_ldgi_run_card.json",
    ),
    33: (
        "gemsdoe33-fsml2-cc-37654-20261026-6fd4410bbaee-zeros.tif",
        "evidence/fsml2_run_card_20261026.json",
    ),
    36: (
        "gemsdoe36-kpl36-exp3-20261026-fc869911e88c-zeros.tif",
        "evidence/kpl36_run_card_20261026.json",
    ),
}


def load_pins(root: Path) -> dict:
    """Load the immutable nine-file snapshot; freshness is a separate live feed."""
    path = Path(root) / PINS
    if not path.is_file() or sha256_file(path) != PINS_SHA256:
        raise ValueError("Current-focus source pin manifest missing or changed")
    pins = json.loads(path.read_text())
    rows = pins.get("rows", [])
    if pins.get("schema") != "current-focus-source-pins-v1" or len(rows) != len(SELECTED):
        raise ValueError("Current-focus source pin manifest is incomplete")
    by_site = {row["site"]: row for row in rows}
    if set(by_site) != {f"GEMSDOE{n}" for n in SELECTED}:
        raise ValueError("Current-focus source pin sites are not unique")
    return {**pins, "by_site": by_site}


def fetch(repo: str, ref: str, relative: str, target: Path) -> dict:
    relative = str(safe_relative(relative))
    endpoint = f"repos/{repo}/contents/{relative}?ref={ref}"
    blob = subprocess.check_output(
        ["gh", "api", endpoint, "--jq", ".sha"], text=True, timeout=90
    ).strip()
    raw = subprocess.check_output(
        ["gh", "api", "-H", "Accept: application/vnd.github.raw+json", endpoint], timeout=90
    )
    if len(blob) != 40 or git_blob_sha(raw) != blob:
        raise ValueError(f"Pinned source bytes do not match Git blob: {repo}/{relative}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
    return {
        "path": relative,
        "git_blob": blob,
        "sha256": sha256_file(target),
        "bytes": len(raw),
        "source_url": f"https://github.com/{repo}/blob/{ref}/{relative}",
    }


def source_measurement(site: int, card: dict) -> dict:
    """Explicit adapters for each source schema; never mine numbers heuristically."""
    status = "SOURCE-RECORDED; not scientifically replayed; not an organizer score"
    if site == 24:
        return {
            "label": "INVALID HOLDOUT",
            "value": None,
            "ci95": None,
            "evaluator": None,
            "withheld": None,
            "status": "Full-catalogue support was used in fold placement; recorded 0.0011238 is not a valid comparison.",
        }
    if site == 25:
        h = card["holdout_dti"]
        r = h["experiment_3_subsurf_block25km_shipped_family"]
        return {
            "label": "HOLDOUT-DTI",
            "value": r["h74_subsurf_pooled"],
            "ci95": r["h74_subsurf_ci95"],
            "evaluator": h["evaluator"],
            "withheld": r["withheld_positive_occurrences"],
            "status": status + "; positive occurrences, not necessarily unique pixels",
        }
    if site == 27:
        h = card["holdout"]
        return {
            "label": "HOLDOUT-DTI",
            "value": h["pooled_dti_H31S_candidate"],
            "ci95": h["pooled_dti_H31S_ci95"],
            "evaluator": h["evaluator"],
            "withheld": h["n_withheld_positives_total"],
            "status": status
            + "; earlier pinned README/card denominator disagreement not independently reconciled",
        }
    if site == 28:
        h = card["holdout"]
        return {
            "label": "HOLDOUT-DTI",
            "value": h["dti"],
            "ci95": h["ci95"],
            "evaluator": h["evaluator_version"],
            "withheld": h["withheld_positives"],
            "status": status
            + "; source card says buffered=false, so not the requested buffered protocol",
        }
    if site == 30:
        h = card["holdout"]
        return {
            "label": "HOLDOUT-DTI",
            "value": h["value"],
            "ci95": h["ci95"],
            "evaluator": h["evaluator_version"],
            "withheld": h["withheld_positives"],
            "status": status,
        }
    if site == 31:
        h = card["holdout_dti"]["candidate"]
        return {
            "label": "HOLDOUT-DTI",
            "value": h["dti"],
            "ci95": h["ci95"],
            "evaluator": h["evaluator_version"],
            "withheld": h["withheld_positive_pixels"],
            "status": status,
        }
    if site == 32:
        h = card["holdout_dti"]["primary_hide_and_recover"]
        return {
            "label": "HOLDOUT-DTI",
            "value": h["pooled_dti"],
            "ci95": h["ci95"],
            "evaluator": h["evaluator_version"],
            "withheld": h["n_withheld_positives"],
            "status": status,
        }
    if site == 33:
        h = card["holdout_dti"]["confirmation"]["V1_cc6@37654"]
        return {
            "label": "HOLDOUT-DTI",
            "value": h["dti"],
            "ci95": h["ci95"],
            "evaluator": h["evaluator_version"],
            "withheld": h["withheld_positives"],
            "status": status + "; confirmation split",
        }
    if site == 36:
        h, arm = card["holdout"], card["holdout"]["arms"]["EXP-3"]
        return {
            "label": "HOLDOUT-DTI",
            "value": arm["dti"],
            "ci95": arm["ci95"],
            "evaluator": h["evaluator_version"],
            "withheld": h["n_withheld_positive_pixels"],
            "status": status + "; peer promote claim conflicts with literal lattice gate",
        }
    raise ValueError("Unexpected focus site")


def audit() -> dict:
    registry_path = ROOT / "registry/priority_rasters_20261026_portfolio.json"
    manifest = json.loads(registry_path.read_text())
    pins = load_pins(ROOT)
    # This audit is replayed at the immutable pinned refs, never silently at a
    # later HEAD. A separate freshness feed reports movement after these refs.
    sources = [
        {
            "repo": f"buffedlizard55-lab/{row['site']}",
            "latest_main_ref": row["source_ref"],
        }
        for row in pins["rows"]
    ]
    claims = json.loads((ROOT / "registry/owner_reported_scores_2026-10-26.json").read_text())[
        "sites"
    ]
    template = ROOT / "data/bridge/sample_submission.tif"
    with rasterio.open(template) as ds:
        fp = np.isfinite(ds.read(1))
        grid = (ds.shape, ds.crs, ds.transform)
    rows = [r for r in manifest["unique_rasters"] if r["file"] == LATTICE]
    if len(rows) != 1 or sha256_file(ROOT / LATTICE) != rows[0]["sha256"]:
        raise ValueError("Retained lattice is missing, ambiguous or changed")
    with rasterio.open(ROOT / LATTICE) as ds:
        if (ds.shape, ds.crs, ds.transform, ds.count) != (*grid, 1):
            raise ValueError("Retained lattice grid changed")
        lattice_data = ds.read(1)
    lattice = fp & np.isfinite(lattice_data) & (lattice_data > 0)
    control = novelty.classify_space_filling_control(fp, lattice, candidate_dot_count=37654)

    def retrieve(row):
        site = int(row["repo"].split("GEMSDOE")[-1])
        name, card_path = SELECTED[site]
        cache = ROOT / "data/research/focus_current_audit" / str(site) / row["latest_main_ref"]
        tif = cache / name
        card_file = cache / Path(card_path).name
        file_meta = fetch(row["repo"], row["latest_main_ref"], "docs/downloads/" + name, tif)
        card_meta = fetch(row["repo"], row["latest_main_ref"], card_path, card_file)
        text = card_file.read_text()
        if name not in text or file_meta["sha256"] not in text:
            raise ValueError(
                f"Source card does not identify the exact TIFF by name and SHA: {site}"
            )
        return site, row, tif, file_meta, card_meta, json.loads(text)

    with ThreadPoolExecutor(max_workers=3) as pool:
        fetched = list(pool.map(retrieve, sources))
    result_rows = []
    for site, source, tif, file_meta, card_meta, card in sorted(fetched):
        check = submission.check_variants(tif, template)
        with rasterio.open(tif) as ds:
            arr = ds.read(1)
        if arr.shape != fp.shape or not np.isin(arr[fp], (0, 1)).all():
            raise ValueError(f"Binary aligned focus artifact required for dot comparison: {site}")
        dots = fp & (arr > 0)
        overlap = novelty.dot_overlap(dots, lattice)["candidate_within_3px_of_reference"]
        duplicate = overlap is not None and overlap > 0.70
        historical = max(claims[f"GEMSDOE{site}"], key=lambda v: v["owner_reported"])
        result_rows.append(
            {
                "site": f"GEMSDOE{site}",
                "source_ref": source["latest_main_ref"],
                "source_file": file_meta,
                "source_card": card_meta,
                "download_url": f"https://github.com/{source['repo']}/raw/{source['latest_main_ref']}/{file_meta['path']}",
                "historical_best_owner_reported_unverified": historical,
                "holdout": source_measurement(site, card),
                "format_valid": check["format_valid"],
                "strict_whole_array_finite_0_1": check["checks"][
                    "variant_strict_whole_array_no_nan_allowed"
                ]["pass"],
                "validator_output": check,
                "dots": int(dots.sum()),
                "literal_lattice_overlap_within_3px": overlap,
                "literal_lattice_duplicate": duplicate,
                "preplacement_surface_novelty": None,
                "full_registry_novelty_replayed": False,
                "ok_to_download": check["format_valid"],
                "ok_to_submit": False,
            }
        )
    return {
        "schema": "current-focus-nine-file-audit-v1",
        "checked_utc": datetime.now(timezone.utc).isoformat(),
        "feed_checked_utc": pins["source_feed_checked_utc"],
        "scope": "One selected source-featured TIFF per focus site at immutable feed refs; not every current TIFF, no scientific replay, no pre-placement surfaces, no leaderboard access",
        "source_score_status": "Source holdouts are not organizer-confirmed and different evaluators/splits are not ranked together",
        "lattice": {
            "file": LATTICE,
            "sha256": rows[0]["sha256"],
            "footprint_sha256": rows[0]["footprint_sha256"],
            **control,
        },
        "rows": result_rows,
        "new_experiments": 0,
        "new_tiffs_generated_by_this_session": 0,
        "competition_slots_used": 0,
        "organizer_confirmed_scores": [],
        "submission_authorized": False,
        "verdict": "negative",
    }


def validate_audit(result: dict, root: Path = ROOT) -> dict:
    """Validate saved provenance and decisions without claiming a fresh replay."""
    root = Path(root)
    if (
        result.get("schema") != "current-focus-nine-file-audit-v1"
        or result.get("new_experiments") != 0
        or result.get("new_tiffs_generated_by_this_session") != 0
        or result.get("competition_slots_used") != 0
        or result.get("organizer_confirmed_scores") != []
        or result.get("submission_authorized") is not False
        or result.get("verdict") != "negative"
    ):
        raise ValueError("Focus-file audit cannot certify experiments or submission")
    if datetime.fromisoformat(result["checked_utc"]).tzinfo is None:
        raise ValueError("Audit timestamp must include timezone")
    manifest = json.loads((root / "registry/priority_rasters_20261026_portfolio.json").read_text())
    lattice_rows = [r for r in manifest["unique_rasters"] if r["file"] == LATTICE]
    lattice = result["lattice"]
    if (
        len(lattice_rows) != 1
        or lattice.get("file") != LATTICE
        or lattice.get("sha256") != lattice_rows[0]["sha256"]
        or lattice.get("footprint_sha256") != lattice_rows[0]["footprint_sha256"]
        or sha256_file(root / LATTICE) != lattice_rows[0]["sha256"]
    ):
        raise ValueError("Focus audit is not bound to the retained registry lattice")
    pins = load_pins(root)
    if result.get("feed_checked_utc") != pins["source_feed_checked_utc"]:
        raise ValueError("Focus audit is not bound to the original source feed")
    claims = json.loads((root / "registry/owner_reported_scores_2026-10-26.json").read_text())[
        "sites"
    ]
    rows = result.get("rows", [])
    if len(rows) != len(SELECTED) or {r.get("site") for r in rows} != {
        f"GEMSDOE{n}" for n in SELECTED
    }:
        raise ValueError("One and only one named artifact per focus site is required")
    for row in rows:
        site = int(row["site"].removeprefix("GEMSDOE"))
        name, card_path = SELECTED[site]
        ref = row["source_ref"]
        repo = f"buffedlizard55-lab/GEMSDOE{site}"
        f, c, check, holdout = (
            row["source_file"],
            row["source_card"],
            row["validator_output"],
            row["holdout"],
        )
        pin = pins["by_site"][row["site"]]
        if (
            not re.fullmatch(r"[a-f0-9]{40}", ref)
            or ref != pin["source_ref"]
            or f != pin["source_file"]
            or c != pin["source_card"]
        ):
            raise ValueError("Focus source ref, hashes or Git blobs differ from immutable pins")
        card_file = root / safe_relative(pin["local_card"])
        raw_card = card_file.read_bytes()
        if (
            len(raw_card) != c["bytes"]
            or sha256_file(card_file) != c["sha256"]
            or git_blob_sha(raw_card) != c["git_blob"]
            or name not in raw_card.decode("utf-8")
            or f["sha256"] not in raw_card.decode("utf-8")
            or source_measurement(site, json.loads(raw_card)) != holdout
        ):
            raise ValueError("Focus source card bytes or displayed holdout changed")
        for meta, expected in ((f, "docs/downloads/" + name), (c, card_path)):
            if (
                meta.get("path") != expected
                or not re.fullmatch(r"[a-f0-9]{64}", meta.get("sha256", ""))
                or not re.fullmatch(r"[a-f0-9]{40}", meta.get("git_blob", ""))
                or meta.get("source_url") != f"https://github.com/{repo}/blob/{ref}/{expected}"
            ):
                raise ValueError("Focus source identity or immutable URL changed")
        check_digest = hashlib.sha256(
            json.dumps(check, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        ).hexdigest()
        if (
            row.get("download_url") != f"https://github.com/{repo}/raw/{ref}/{f['path']}"
            or check_digest != pin["validator_sha256"]
            or row.get("dots") != pin["dots"]
            or check.get("sha256") != f["sha256"]
            or check.get("format_valid") is not row.get("format_valid")
            or check["checks"]["variant_strict_whole_array_no_nan_allowed"]["pass"]
            is not row.get("strict_whole_array_finite_0_1")
            or check.get("in_footprint_positive_pixels") != row.get("dots")
            or row.get("ok_to_download") is not row.get("format_valid")
        ):
            raise ValueError("Focus raster identity or exact-file format evidence changed")
        overlap = row.get("literal_lattice_overlap_within_3px")
        if (
            type(overlap) not in (int, float)
            or not math.isfinite(overlap)
            or not 0 <= overlap <= 1
            or overlap != pin["literal_lattice_overlap_within_3px"]
            or row.get("literal_lattice_duplicate") is not (overlap > 0.70)
            or row.get("preplacement_surface_novelty") is not None
            or row.get("full_registry_novelty_replayed") is not False
            or row.get("ok_to_submit") is not False
        ):
            raise ValueError("Focus novelty or negative decision is inconsistent")
        if row.get("historical_best_owner_reported_unverified") != max(
            claims[row["site"]], key=lambda value: value["owner_reported"]
        ):
            raise ValueError("Historical owner claim changed")
        if holdout.get("value") is None:
            if site != 24 or holdout.get("label") != "INVALID HOLDOUT":
                raise ValueError("Unexpected missing source holdout")
        else:
            val, ci, count = holdout["value"], holdout["ci95"], holdout["withheld"]
            if (
                holdout.get("label") != "HOLDOUT-DTI"
                or type(val) not in (int, float)
                or not math.isfinite(val)
                or not isinstance(ci, list)
                or len(ci) != 2
                or any(type(x) not in (int, float) or not math.isfinite(x) for x in ci)
                or not 0 <= ci[0] <= val <= ci[1] <= 1
                or type(count) is not int
                or count < 1
                or not holdout.get("evaluator")
            ):
                raise ValueError("Incomplete source-recorded holdout")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Optional JSON evidence path inside evidence/")
    args = parser.parse_args()
    text = json.dumps(validate_audit(audit()), indent=2, allow_nan=False) + "\n"
    if args.output:
        target = args.output.resolve()
        if not target.is_relative_to(ROOT / "evidence"):
            raise ValueError("Audit output must be inside evidence/")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
    print(text)


if __name__ == "__main__":
    main()
