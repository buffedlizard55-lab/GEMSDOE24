#!/usr/bin/env python3
"""Read-only, necessary-only uniqueness gate BEFORE allocating training time.

No prediction surface, placement, TIFF, training, score estimate or upload is
created. One pinned registry witness can prove failure, never a registry pass.
Exit 2 means at least one requested budget is mathematically impossible under
the literal >70% / <=3 px gate; exit 0 means only NOT RULED OUT, not approval.
Missing/tampered evidence is an error, not a passing or skipped comparator.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from html import escape
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems.novelty import classify_space_filling_control, dot_budget_feasibility  # noqa: E402
from gems.validator import sha256_file  # noqa: E402

REGISTRY = "registry/priority_rasters_20261026_portfolio.json"
TEMPLATE = "data/bridge/sample_submission.tif"
WITNESS = "inputs/calibration/13gems_20261001_r13-lattice-s5_v2_nan-outside.tif"


def audit(root: Path, budgets: list[int]) -> dict:
    root = Path(root)
    if not budgets:
        raise ValueError("At least one prospectively specified dot budget is required")
    registry_path = root / REGISTRY
    registry = json.loads(registry_path.read_text())
    matches = [r for r in registry["unique_rasters"] if r["file"] == WITNESS]
    if len(matches) != 1:
        raise ValueError("Pinned registry witness must occur exactly once")
    row = matches[0]
    # Do not accept arbitrary cache paths, even if a modified registry names one.
    if row["cache_path"] != WITNESS:
        raise ValueError("Unexpected lattice cache path")
    template_sha = json.loads((root / "data/manifest.json").read_text())["files"][
        "bridge/sample_submission.tif"
    ]["sha256"]
    if sha256_file(root / TEMPLATE) != template_sha:
        raise ValueError("Pinned template checksum mismatch")
    if sha256_file(root / WITNESS) != row["sha256"]:
        raise ValueError("Registry witness checksum mismatch")
    with rasterio.open(root / TEMPLATE) as t, rasterio.open(root / WITNESS) as r:
        if any(
            len(ds.files) != 1 or Path(ds.files[0]).resolve() != (root / path).resolve()
            for ds, path in ((t, TEMPLATE), (r, WITNESS))
        ):
            raise ValueError("Template and witness must be self-contained without sidecars")
        if (
            t.count != 1
            or t.crs is None
            or (t.count, t.shape, t.crs, t.transform) != (r.count, r.shape, r.crs, r.transform)
        ):
            raise ValueError("Single-band template and witness must share CRS/shape/transform")
        fp = np.isfinite(t.read(1))
        if (
            np.ma.getmaskarray(t.read(1, masked=True))[fp].any()
            or np.ma.getmaskarray(r.read(1, masked=True))[fp].any()
        ):
            raise ValueError("Template or witness has masked or NoData pixels inside footprint")
        values = r.read(1)
    if not fp.any() or not np.isfinite(values[fp]).all():
        raise ValueError("Nonempty footprint and finite witness values required")
    if np.any((values[fp] < 0) | (values[fp] > 1)):
        raise ValueError("Registry witness values outside [0,1]")
    content_sha = hashlib.sha256(values[fp].astype("<f4").tobytes()).hexdigest()
    if content_sha != row["footprint_sha256"]:
        raise ValueError("Witness footprint content hash mismatch")
    coverage = classify_space_filling_control(fp, fp & (values > 0), radius_px=3.0)
    results = [
        dot_budget_feasibility(int(fp.sum()), coverage["footprint_3px_uncovered_pixels"], k)
        for k in budgets
    ]
    return {
        "schema": "uniqueness-budget-feasibility-v1",
        "checked_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "One necessary geometric gate; NOT a complete registry audit or scientific experiment",
        "registry": {"path": REGISTRY, "sha256": sha256_file(registry_path)},
        "template": {"path": TEMPLATE, "sha256": template_sha},
        "witness": {"path": WITNESS, "sha256": row["sha256"], "footprint_sha256": content_sha},
        "coverage": coverage,
        "budgets": results,
        "impossible_budget_found": any(r["strictly_exceeds_limit"] for r in results),
        "preplacement_surface_test": "NOT RUN: no surface generated",
        "final_dot_test": "NOT RUN: no dots generated; universal lower bound only",
        "leaderboard_estimate": None,
        "holdout_dti": None,
        "submission_authorized": False,
        "new_tiffs": 0,
        "new_experiments": 0,
        "competition_slots_used": 0,
        "warning": "Do not change a stopped lane's budget or registry to evade this gate.",
    }


def render(report: dict) -> str:
    e = escape
    rows = "".join(
        f"<tr><td>{r['candidate_dot_count']:,}</td><td>{r['minimum_overlapping_dots']:,}</td>"
        f"<td>{r['minimum_overlap_fraction']:.4%}</td><td>{e(r['status'])}</td></tr>"
        for r in report["budgets"]
    )
    uncovered = report["coverage"]["footprint_3px_uncovered_pixels"]
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Pre-training uniqueness gate · GEMS DOE 24</title><link rel="stylesheet" href="assets/style.css"></head>
<body><main><p><a href="index.html">Overview</a> · <a href="executive-summary.html#current-focus-files">Nine-site executive table and research downloads</a></p>
<h1>No submission-authorized TIFF</h1><p><strong>DOWNLOAD: research only. SUBMIT: NO.</strong>
No new TIFF or geological experiment was generated by this check.</p>
<h2>Check feasibility before spending training time</h2>
<p>Checked {e(report["checked_utc"])}. This is a mathematical bound, not HOLDOUT-DTI,
not an organizer score, and not evidence that a geological method copied another.</p>
<p>The retained lattice leaves only <strong>{uncovered:,}</strong> footprint pixels outside
its inclusive 3-pixel union. Any K distinct in-footprint dots must have at least
max(0, K − {uncovered:,}) overlapping dots. A strict integer comparison enforces the
<strong>greater than 70%</strong> stop rule, including its exact boundary.</p>
<div class="tablewrap" role="region" aria-label="Diagnostic budget bounds" tabindex="0"><table><caption>Necessary-only overlap bounds for diagnostic budgets; not a budget search or submission selection</caption>
<thead><tr><th scope="col">Dot budget K</th><th scope="col">Minimum overlapping dots</th>
<th scope="col">Minimum overlap</th><th scope="col">Decision</th></tr></thead><tbody>{rows}</tbody></table></div>
<p><strong>NOT_RULED_OUT is not PASS.</strong> Smaller budgets may also fail in practice.
No surface correlation, full registry, leakage, comparative holdout, bias, replay, or live quota
pass follows from this calculation. Do not shift dots, alter a stopped budget or remove the
lattice to force uniqueness. A protocol change requires a prospective coordination decision.</p>
<h2>Reproduce without training or human inspection</h2>
<pre role="region" aria-label="Read-only reproduction command" tabindex="0">python scripts/check_uniqueness_feasibility.py --dot-budget 37654 --dot-budget 44090</pre>
<p>Exit 2: impossible requested budget. Exit 0: only not ruled out. Missing or changed evidence fails;
the program never writes a TIFF or uploads anything. <a href="data/uniqueness_feasibility_20261027.json">Hash-bound JSON receipt</a>.</p>
<h2>Evidence and next action</h2><p class="note">The exact witness is <code>{e(report["witness"]["path"])}</code>,
SHA-256 <code>{e(report["witness"]["sha256"])}</code>. This is one decisive comparator,
not a complete fresh census of the registry.</p>
<p>The operative prompt still lacks its single-method lane paragraph. Preserve stopped lanes.
The <a href="https://github.com/buffedlizard55-lab/GEMSDOE24/blob/main/knowledge/31_current_integrity_review_2026-10-27.md">ranked geological hypotheses and integrity review</a>
remain prospective. Catalogue-hide-and-recover tests measure fault recovery, not geothermal vent confirmation.
The <a href="executive-summary.html">submission guide</a> distinguishes numeric/grid validity from eligibility.</p>
</main></body></html>\n"""


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dot-budget", type=int, action="append", required=True)
    p.add_argument("--output", type=Path)
    p.add_argument("--html", type=Path)
    args = p.parse_args()
    report = audit(ROOT, args.dot_budget)
    text = json.dumps(report, indent=2, allow_nan=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text)
    if args.html:
        args.html.parent.mkdir(parents=True, exist_ok=True)
        args.html.write_text(render(report))
    print(text, end="")
    return 2 if report["impossible_budget_found"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
