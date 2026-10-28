#!/usr/bin/env python3
"""Compare one candidate raster with the nine pinned historical focus-site champions.

This is a narrowly scoped final-dot overlap audit, not a geological experiment,
pre-placement surface-correlation test, current-head audit, full-registry census,
or submission selector. It reuses the pinned historical readback report, exact
SHA-256 checks, the shared directed ``dot_overlap`` metric, and GitHub-only artifact
retrieval. Downloaded comparison inputs are cached under ignored ``data/research``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from restore_data import gh_bytes  # noqa: E402

from gems.novelty import dot_overlap  # noqa: E402
from gems.submission import check_variants  # noqa: E402

EXPECTED_SITES = {f"GEMSDOE{number}" for number in (24, 25, 27, 28, 30, 31, 32, 33, 36)}
URL_RE = re.compile(
    r"https://github\.com/(buffedlizard55-lab/GEMSDOE\d+)/blob/([0-9a-f]{40})/(docs/downloads/[^/]+\.tif)"
)
RADIUS_PX = 3.0
LIMIT = 0.70


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def pinned_source(row: dict) -> tuple[str, str, str]:
    match = URL_RE.fullmatch(row.get("source_url", ""))
    if not match or match.group(1).rsplit("/", 1)[-1] != row.get("site"):
        raise ValueError("Each comparator needs an immutable matching focus-site TIFF URL")
    expected = row.get("sha256", "")
    if not re.fullmatch(r"[0-9a-f]{64}", expected):
        raise ValueError("Every historical comparator requires a pinned SHA-256")
    return match.groups()


def read_dot_mask(path: Path) -> tuple[np.ndarray, dict]:
    with rasterio.open(path) as dataset:
        if dataset.count != 1:
            raise ValueError(f"Expected a single-band GeoTIFF: {path}")
        values = dataset.read(1)
        metadata = {
            "crs": dataset.crs.to_string() if dataset.crs else None,
            "transform": list(dataset.transform)[:6],
            "shape": list(dataset.shape),
            "dtype": dataset.dtypes[0],
        }
    if not np.isfinite(values).any():
        raise ValueError(f"Raster has no finite values: {path}")
    return np.isfinite(values) & (values > 0.5), metadata


def audit(
    candidate: Path,
    historical_report: Path,
    template: Path,
    cache_root: Path,
    *,
    fetch=gh_bytes,
) -> dict:
    candidate = Path(candidate)
    historical_report = Path(historical_report)
    template = Path(template)
    cache_root = Path(cache_root)
    report = json.loads(historical_report.read_text())
    rows = report.get("rows")
    if (
        not isinstance(rows, list)
        or len(rows) != 9
        or {r.get("site") for r in rows} != EXPECTED_SITES
    ):
        raise ValueError("Historical readback must contain exactly the nine named focus sites")
    candidate_validation = check_variants(candidate, template)
    candidate_sha = sha256(candidate)
    if (
        not candidate_validation.get("format_valid")
        or candidate_validation.get("sha256") != candidate_sha
    ):
        raise ValueError("Candidate failed shared exact-file format validation")
    candidate_dots, candidate_grid = read_dot_mask(candidate)
    if not candidate_dots.any():
        raise ValueError("Candidate has no positive prediction pixels")

    comparisons = []
    for row in rows:
        repository, ref, relative_path = pinned_source(row)
        cache = cache_root / row["site"] / Path(relative_path).name
        if not cache.is_file():
            fetch(repository, relative_path, ref, cache)
        observed_sha = sha256(cache)
        if observed_sha != row["sha256"]:
            raise ValueError(f"Historical artifact hash mismatch for {row['site']}")
        reference_dots, reference_grid = read_dot_mask(cache)
        if reference_grid != candidate_grid:
            raise ValueError(f"Candidate and {row['site']} comparator grids differ")
        overlap = dot_overlap(candidate_dots, reference_dots, radius_px=RADIUS_PX)
        comparisons.append(
            {
                "site": row["site"],
                "source_url": row["source_url"],
                "reference_sha256": observed_sha,
                "candidate_dot_count": overlap["candidate_dots"],
                "reference_dot_count": overlap["reference_dots"],
                "candidate_within_3px_of_reference": overlap["candidate_within_3px_of_reference"],
                "reference_within_3px_of_candidate": overlap["reference_within_3px_of_candidate"],
                "exact_dot_mask_alias": bool(np.array_equal(candidate_dots, reference_dots)),
                "owner_reported_score": row.get("owner_reported_unverified", {}).get(
                    "owner_reported"
                ),
                "score_status": "OWNER-REPORTED / UNVERIFIED",
            }
        )

    comparisons.sort(key=lambda item: item["candidate_within_3px_of_reference"], reverse=True)
    maximum = comparisons[0]["candidate_within_3px_of_reference"]
    return {
        "schema": "historical-focus-champion-overlap-v1",
        "checked_utc": datetime.now(UTC).isoformat(),
        "candidate": candidate.relative_to(ROOT).as_posix(),
        "candidate_sha256": candidate_sha,
        "candidate_dot_count": int(candidate_dots.sum()),
        "candidate_format_valid": True,
        "rule": "duplicate stop if more than 70% of candidate dots fall within 3 px of one reference raster",
        "radius_px": RADIUS_PX,
        "overlap_limit": LIMIT,
        "reference_scope": "Exactly the nine pinned owner-named historical champion TIFFs; not current repository heads, all files, all 167 registry aliases, or all competitors.",
        "references_compared": len(comparisons),
        "max_candidate_dot_overlap": maximum,
        "max_overlap_site": comparisons[0]["site"],
        "passes_nine_historical_file_overlap_threshold": maximum <= LIMIT,
        "exact_dot_mask_aliases": [
            row["site"] for row in comparisons if row["exact_dot_mask_alias"]
        ],
        "preplacement_surface_correlation": "NOT TESTED: these source artifacts provide final TIFFs, not the candidate's continuous surface at pre-placement time.",
        "full_registry_uniqueness": "NOT ESTABLISHED",
        "submission_authorized": False,
        "comparisons": comparisons,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--candidate",
        type=Path,
        default=Path(
            "docs/downloads/24gems-interior-offlattice-geothermal-20261028T164358Z-"
            "e5a3c34b27db-zeros.tif"
        ),
    )
    parser.add_argument(
        "--historical-report",
        type=Path,
        default=Path("docs/data/historical_champions_20261028.json"),
    )
    parser.add_argument("--template", type=Path, default=Path("data/bridge/sample_submission.tif"))
    parser.add_argument(
        "--cache-root", type=Path, default=Path("data/research/focus_champion_overlap")
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("evidence/historical_champion_overlap_20261028.json"),
    )
    args = parser.parse_args()
    paths = [args.candidate, args.historical_report, args.template, args.cache_root, args.out]
    resolved = [path if path.is_absolute() else ROOT / path for path in paths]
    result = audit(*resolved[:4])
    resolved[4].parent.mkdir(parents=True, exist_ok=True)
    resolved[4].write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "references_compared": result["references_compared"],
                "max_candidate_dot_overlap": result["max_candidate_dot_overlap"],
                "max_overlap_site": result["max_overlap_site"],
                "passes_nine_historical_file_overlap_threshold": result[
                    "passes_nine_historical_file_overlap_threshold"
                ],
                "full_registry_uniqueness": result["full_registry_uniqueness"],
                "submission_authorized": result["submission_authorized"],
            },
            indent=2,
        )
    )
    return 0 if result["passes_nine_historical_file_overlap_threshold"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
