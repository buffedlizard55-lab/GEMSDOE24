#!/usr/bin/env python3
"""Read-only replay of the nine owner-named historical champions, not a selector.

Downloads only immutable, hash-pinned research artifacts. Reuses the shared
validator and lattice geometry; never writes predictions or estimates scores.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from html import escape
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from check_uniqueness_feasibility import audit as feasibility  # noqa: E402
from restore_data import gh_bytes  # noqa: E402

from gems.submission import check_variants  # noqa: E402
from gems.validator import sha256_file  # noqa: E402

SITES = {f"GEMSDOE{n}" for n in (24, 25, 27, 28, 30, 31, 32, 33, 36)}


def parse_source(row):
    match = re.fullmatch(
        r"https://github.com/(buffedlizard55-lab/GEMSDOE\d+)/blob/([0-9a-f]{40})/(docs/downloads/[^/]+\.tif)",
        row["url"],
    )
    if not match or match[1].split("/")[-1] != row["repo"]:
        raise ValueError("An immutable matching focus-repository TIFF URL is required")
    if not re.fullmatch(r"[0-9a-f]{64}", row["sha256"]):
        raise ValueError("SHA-256 required")
    return match.groups()


def geometry(values, footprint, lattice_distance):
    if any(
        np.ma.isMaskedArray(x) and np.ma.getmaskarray(x).any()
        for x in (values, footprint, lattice_distance)
    ):
        raise ValueError("Geometry inputs must not contain masked pixels")
    if values.shape != footprint.shape or lattice_distance.shape != footprint.shape:
        raise ValueError("Geometry grids differ")
    if not np.isin(footprint, [0, 1]).all():
        raise ValueError("Geometry footprint must be binary")
    footprint = np.asarray(footprint, dtype=bool)
    if not np.isfinite(lattice_distance[footprint]).all() or np.any(
        lattice_distance[footprint] < 0
    ):
        raise ValueError("Geometry distance must be finite and nonnegative inside footprint")
    if not np.isfinite(values[footprint]).all() or not np.isin(values[footprint], [0, 1]).all():
        raise ValueError("Historical champion must be finite binary inside footprint")
    dots = footprint & (values > 0)
    count = int(dots.sum())
    if not count:
        raise ValueError("Empty champion")
    return {
        "dots": count,
        "footprint_content_sha256": hashlib.sha256(
            values[footprint].astype("<f4").tobytes()
        ).hexdigest(),
        "lattice_overlap_within_3px": float(np.count_nonzero(lattice_distance[dots] <= 3) / count),
    }


def build(root=ROOT):
    root = Path(root)
    source = root / "evidence/peer_forensics_20261025.json"
    records = json.loads(source.read_text())["artifacts"]
    if len(records) != 9 or {r["repo"] for r in records} != SITES:
        raise ValueError("Exactly nine distinct focus sites required")
    # Reopen and authenticate the witness with the shared pre-training tool.
    witness = feasibility(root, [37654, 44090])
    with rasterio.open(root / "data/bridge/sample_submission.tif") as ds:
        fp = np.isfinite(ds.read(1))
    with rasterio.open(root / witness["witness"]["path"]) as ds:
        lattice_distance = distance_transform_edt(~(fp & (ds.read(1) > 0)))
    claims = {
        r["site"]: r["historical_best_owner_reported_unverified"]
        for r in json.loads(
            (root / "evidence/current_focus_nine_file_audit_20261027.json").read_text()
        )["rows"]
    }
    rows = []
    for record in records:
        repo, ref, path = parse_source(record)
        cache = root / "data/research/historical_champions" / record["repo"] / Path(path).name
        if not cache.exists():
            gh_bytes(repo, path, ref, cache)
        if sha256_file(cache) != record["sha256"]:
            raise ValueError("Historical artifact checksum changed")
        checked = check_variants(cache, root / "data/bridge/sample_submission.tif")
        if not checked["format_valid"]:
            raise ValueError("Historical artifact failed shared format validator")
        with rasterio.open(cache) as ds:
            geom = geometry(ds.read(1), fp, lattice_distance)
        if geom["dots"] != record["dot_count"]:
            raise ValueError("Historical dot count changed")
        rows.append(
            {
                "site": record["repo"],
                "source_url": record["url"],
                "download_url": record["url"].replace("/blob/", "/raw/"),
                "file": Path(path).name,
                "sha256": record["sha256"],
                "owner_reported_unverified": claims[record["repo"]],
                "leaderboard_estimate": None,
                "holdout_dti": None,
                "validator_output": checked,
                **geom,
                "preplacement_surface": "NOT AVAILABLE; not replayed",
                "full_registry_pass": False,
                "submission_authorized": False,
            }
        )
    for row in rows:
        row["exact_in_footprint_aliases"] = [
            r["site"]
            for r in rows
            if r["site"] != row["site"]
            and r["footprint_content_sha256"] == row["footprint_content_sha256"]
        ]
        row["literal_uniqueness"] = (
            "FAIL" if row["lattice_overlap_within_3px"] > 0.70 else "NOT ESTABLISHED"
        )
    return {
        "schema": "historical-champion-readback-v1",
        "checked_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "Nine owner-named historical champions, not latest heads or all files; no scientific replay",
        "source_record_sha256": sha256_file(source),
        "witness": witness["witness"],
        "score_status": "OWNER-REPORTED / UNVERIFIED; not organizer-confirmed or score estimates",
        "organizer_confirmed_scores": [],
        "rows": rows,
        "new_tiffs": 0,
        "new_experiments": 0,
        "slots_used": 0,
        "submission_authorized": False,
    }


def render(report):
    e = escape
    rows = []
    for r in report["rows"]:
        claim = r["owner_reported_unverified"]["owner_reported"]
        aliases = ", ".join(r["exact_in_footprint_aliases"]) or "None among these nine"
        rows.append(
            f'<tr><th scope="row">{e(r["site"])}</th><td><a href="{e(r["download_url"], quote=True)}">'
            f"{e(r['file'])}</a><br><small>Research only; SHA-256 {r['sha256']}</small></td>"
            f"<td>{claim:.4f} OWNER-REPORTED / UNVERIFIED</td><td>NOT ESTIMABLE</td>"
            f"<td>{e(aliases)}</td><td>{r['lattice_overlap_within_3px']:.2%}; {r['literal_uniqueness']}</td>"
            "<td>Format PASS; <strong>SUBMIT NO</strong></td></tr>"
        )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Nine historical champions — submission decision</title><link rel="stylesheet" href="assets/style.css"></head>
<body><main><p><a href="executive-summary.html">Executive guide</a> · <a href="submission-readiness.html">Uniqueness feasibility</a></p>
<h1>No submission-authorized file</h1><p><strong>DOWNLOAD: research only · SUBMIT: NO.</strong>
The requested new, unique high-scoring TIFF has not been achieved. No experiment or submission slot was used.</p>
<h2>Which historical file performed best?</h2><p>GEMSDOE32 B2 has the highest <em>owner-reported</em> result in this nine-site list (0.2778), not an organizer-confirmed result.
No file below is recommended for a fresh competition submission. All are prior artifacts, not newly generated predictions.
The downloadable variants are exactly identified below; a filename variant does not prove it is the byte-identical artifact scored by the portal.</p>
<p>Read back {e(report["checked_utc"])} at immutable commits. Scope: {e(report["scope"])}.
No new-head, pre-placement-surface or exhaustive registry certification follows. Local format PASS is not organizer acceptance.</p>
<div class="tablewrap" role="region" aria-label="Historical champion download and decision table" tabindex="0"><table>
<caption>Prior champion artifacts — none eligible as a new unique submission</caption><thead><tr><th>Site</th><th>Exact research download</th>
<th>Historical claim (not estimated)</th><th>Leaderboard estimate</th><th>Identical footprint predictions</th><th>3-pixel lattice overlap / uniqueness</th><th>Decision</th></tr></thead>
<tbody>{"".join(rows)}</tbody></table></div>
<h2>Why B2 may have helped — and what is actually known</h2>
<p>The <a href="https://github.com/buffedlizard55-lab/GEMSDOE24/blob/fdd41b075a05e7df5b222e6e3644344cecc65746/evidence/oj1_priority_ancestry_replay.json">recorded geometry replay</a> found B2 is the 44,090-dot GEMSDOE25 pattern after removing 6,436 dots within 200 m of the visible catalogue. It is also GEMSDOE31 minus 2,545 dots. This is pruning, not evidence of a new subsurface model or vent discovery. That prior replay is not rerun by this table.</p>
<p>Sparse emission and removal of redundant predictions near visible faults could reduce false-positive mass under distance-based Tversky scoring. Whether it actually did so on hidden labels, and how much true-positive mass it lost, cannot be established from geometry or one reported result. Predicting a result above 0.2778, 0.3195 or 0.4413 would be unsupported. The two leader values in the request are conflicting snapshots, not verified current standings.</p>
<h2>Next action, without spending a slot</h2><p>The method-lane paragraph is missing. Common fixed dot budgets cannot pass the literal retained-lattice rule; do not remove the comparator, shift dots into its holes or retune a stopped method. Resolve the protocol prospectively before training.
<a href="research-directions-20261027.md">Four ranked research directions, novelty caveats and source availability</a> remain proposals, not validated discoveries. The published site does not include raw training rasters or the prepared feature cache; this audit does not authenticate their provenance.</p>
<p>After a lane is assigned: use the shared buffered whole-segment holdout, visible-only catalogue features, feature canaries, pooled 300 m DTI and paired confidence intervals; check surfaces and final dots against the complete registry. Only a separately authorized selector with verified quota can promote a candidate. A CPU pipeline exists; GPU access is not universally required.</p>
<h2>Format and upload guide</h2><p>The shared validator checked single-band grid alignment and finite in-footprint values in [0,1]. No raster was repaired or rewritten here. A prior portal range error cannot be diagnosed from its text alone; exterior NaNs and out-of-range values must both be checked. Do not assume renaming or clipping establishes scientific eligibility.</p>
<p>When a future candidate passes every gate, download its exact hash-bound TIFF, use its unique submission name and note (at most 140 characters), and upload it on the <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/">competition submission page</a>. Save the artifact-linked organizer receipt. For now, do not upload any file from this table.</p>
<p><a href="data/historical_champions_20261028.json">Full machine-readable validator and overlap receipt</a> ·
<a href="https://github.com/drivendataorg/gems-prize-reference-solution">Official reference solution</a> ·
<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">Official problem description (not fetched here)</a>.</p>
</main></body></html>\n"""


if __name__ == "__main__":
    report = build()
    (ROOT / "docs/data/historical_champions_20261028.json").write_text(
        json.dumps(report, indent=2, allow_nan=False) + "\n"
    )
    (ROOT / "docs/historical-champions.html").write_text(render(report))
    print(json.dumps({"checked": len(report["rows"]), "submission_authorized": False}))
