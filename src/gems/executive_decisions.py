"""Conservative nine-site decision packet; never selects a weekly submission slot.

Historical owner claims identify references only. Current-best review certifies
local bytes, not a cross-site winner or a calibrated hidden-label prediction.
"""

from __future__ import annotations

import json
import math
from html import escape
from pathlib import Path

from .validator import sha256_file

SITES = tuple(f"GEMSDOE{n}" for n in (24, 25, 27, 28, 30, 31, 32, 33, 36))
CLAIMS = "registry/owner_reported_scores_2026-10-26.json"


def build_decisions(root: Path, current: dict) -> dict:
    claims = json.loads((root / CLAIMS).read_text())
    if set(claims["sites"]) != set(SITES):
        raise ValueError("Nine-site claim inventory must match the requested sites exactly")
    if current.get("ok_to_submit") is not False or current.get("verdict") != "negative":
        raise ValueError("Review packet cannot authorize submission")
    name = current["submission_name"]
    if Path(name).name != name or not name.endswith("-zeros.tif"):
        raise ValueError("Unsafe research filename")
    artifact = root / "docs/downloads" / name
    if sha256_file(artifact) != current["raster_sha256"]:
        raise ValueError("Research download differs from reviewed bytes")
    rows = []
    for site in SITES:
        entries = claims["sites"][site]
        if not entries:
            raise ValueError("Missing historical claims")
        for entry in entries:
            value = entry["owner_reported"]
            if (
                not isinstance(entry.get("name"), str)
                or not entry["name"]
                or type(value) not in (int, float)
                or not math.isfinite(value)
                or not 0 <= value <= 1
            ):
                raise ValueError("Malformed owner-reported reference")
        best = max(entries, key=lambda entry: entry["owner_reported"])
        rows.append(
            {
                "site": site,
                "source_url": f"https://github.com/buffedlizard55-lab/{site}",
                "historical_reference": best["name"],
                "historical_claim": {
                    "label": "UNVERIFIED-OWNER-REPORT",
                    "value": best["owner_reported"],
                    "source": CLAIMS,
                },
                "research_download": name if site == "GEMSDOE24" else None,
                "holdout": current["holdout"] if site == "GEMSDOE24" else None,
                "leaderboard_estimate": None,
                "organizer_confirmed_score": None,
                "uniqueness": (
                    "FAIL: literal registry overlap"
                    if site == "GEMSDOE24"
                    else "NOT ESTABLISHED: no fresh artifact-level audit in this review"
                ),
                "ok_to_submit": False,
                "decision": "DO_NOT_SUBMIT",
            }
        )
    return {
        "schema_version": "nine-site-decisions-v1",
        "scope": "Local exact-file review plus historical owner claims; no cross-site selection",
        "claims_sha256": sha256_file(root / CLAIMS),
        "leaderboard_estimate_method": "Unavailable: no independently calibrated paired organizer receipts",
        "rows": rows,
        "ok_to_submit": False,
        "verdict": "negative",
    }


def render_decisions(packet: dict) -> str:
    e = lambda value: escape(str(value), quote=True)  # noqa: E731
    rows = []
    for row in packet["rows"]:
        name, holdout = row["research_download"], row["holdout"]
        download = (
            f'<a href="downloads/{e(name)}" download="{e(name)}">{e(name)}</a>'
            "<br>Research only; DO NOT SUBMIT"
            if name
            else "None recommended by this review"
        )
        metric = "Not independently harmonized / replayed"
        if holdout:
            low, high = holdout["ci95"]["interval"]
            metric = (
                f"HOLDOUT-DTI {holdout['dti']:.5f}; 95% CI [{low:.5f}, {high:.5f}]; "
                f"{e(holdout['evaluator_version'])}; "
                f"{holdout['n_withheld_positive_pixels']:,} withheld positives. Recorded, not replayed."
            )
        claim = row["historical_claim"]
        rows.append(
            f'<tr><th scope="row"><a href="{e(row["source_url"])}">{e(row["site"])}</a></th>'
            f"<td><code>{e(row['historical_reference'])}</code><br>"
            f"{e(claim['label'])}: {claim['value']:.4f}</td>"
            f"<td>{download}</td><td>{metric}</td>"
            f"<td>Unknown; no calibrated estimate</td><td>{e(row['uniqueness'])}<br>"
            "<strong>SUBMIT NO</strong></td></tr>"
        )
    return (
        '<section class="card" id="nine-site-download-decisions">'
        "<h2>Nine-site download and submission decisions</h2>"
        "<p>No approved submission exists. Historical best means highest value in the owner's "
        "list, not a verified leaderboard winner. A blank estimate is deliberate: local holdout "
        "cannot be converted into an organizer score without calibration. No new TIFF was "
        "generated by this review. Research download availability is not permission to submit.</p>"
        '<div class="tablewrap" tabindex="0" role="region" aria-label="Nine-site decisions, scroll horizontally">'
        "<table><caption>All nine requested sites; fail-closed submission status</caption>"
        "<thead><tr><th>Site</th><th>Historical reference (not a download recommendation)</th>"
        "<th>File to download</th><th>Local evidence</th><th>Leaderboard estimate</th>"
        "<th>Unique / submit?</th></tr></thead><tbody>"
        + "".join(rows)
        + '</tbody></table></div><p><a href="data/nine_site_download_decisions.json" download>'
        "Download machine-readable nine-site decisions</a></p></section>"
    )
