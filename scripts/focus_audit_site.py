"""Render the separately audited nine current source files and concurrent stops."""

from __future__ import annotations

import json
from html import escape
from pathlib import Path

from audit_current_focus_files import validate_audit
from refresh_priority_feed import validate_feed

from gems.benchmarks import selection_floor
from gems.validator import sha256_file


def _holdout(h):
    if h["value"] is None:
        return f"<strong>INVALID HOLDOUT</strong><br>{escape(h['status'])}"
    lo, hi = h["ci95"]
    return (
        f"<strong>HOLDOUT-DTI {h['value']:.5f}</strong> "
        f"<br>95% CI [{lo:.5f}, {hi:.5f}]<br><code>{escape(h['evaluator'])}</code>"
        f'<br>{h["withheld"]:,} withheld<br><span class="micro">{escape(h["status"])}</span>'
    )


def _verify_concurrent(root: Path, relative: str, *, leaked: bool) -> dict:
    p = root / relative
    card = json.loads(p.read_text())
    raster = root / "docs/downloads" / card["submission_name"]
    rows = card["correlation_overlap_vs_registry"]["rows"]
    if (
        not raster.is_file()
        or sha256_file(raster) != card["raster_sha256"]
        or card["validator_output"]["sha256"] != card["raster_sha256"]
        or card["ok_to_submit"] is not False
        or card["generated_by_this_session"] is not False
        or card["verdict"] != "negative"
        or len(rows) != 1
        or rows[0]["duplicate"] is not True
        or rows[0]["candidate_dot_overlap_within_3px"] <= 0.70
        or card.get("preplacement_surface_novelty") is not None
        or (leaked and card.get("fold_leakage", {}).get("detected") is not True)
    ):
        raise ValueError("Concurrent audit evidence or negative decision changed")
    return card


def render(root: Path) -> dict[str, str]:
    root = Path(root)
    path = root / "evidence/current_focus_nine_file_audit_20261027.json"
    audit = validate_audit(json.loads(path.read_text()), root)
    if any(row["literal_lattice_duplicate"] is not True for row in audit["rows"]):
        raise ValueError("Fixed nine-file negative summary requires nine duplicate witnesses")
    manifest = json.loads((root / "registry/priority_rasters_20261026_portfolio.json").read_text())
    feed = validate_feed(
        json.loads((root / "docs/data/portfolio_freshness.json").read_text()), manifest["sources"]
    )
    latest = {row["repo"].split("/")[-1]: row for row in feed["rows"]}
    moved = sum(
        latest[row["site"]]["status"] == "checked"
        and latest[row["site"]]["latest_main_ref"] != row["source_ref"]
        for row in audit["rows"]
    )
    unknown = sum(latest[row["site"]]["status"] != "checked" for row in audit["rows"])
    tmcg = _verify_concurrent(root, "evidence/tmcg_integrity_review_20261027.json", leaked=False)
    unique = _verify_concurrent(
        root, "evidence/unique07_integrity_review_20261027.json", leaked=True
    )
    band = json.loads((root / "evidence/band6_provenance_review_20261027.json").read_text())
    floor = selection_floor(root)
    peer = json.loads((root / "evidence/peer_s2d36_audit_20261028.json").read_text())
    if (
        peer.get("schema") != "peer-s2d36-research-audit-v1"
        or peer.get("verdict") != "negative"
        or peer.get("submission_authorized") is not False
        or peer["source_identities"]["card"]["sha256"] != floor["source_sha256"]
        or peer["recorded_holdout"]["value"] != floor["holdout"]["dti"]
        or peer["local_format_validation"]["sha256"]
        != peer["source_identities"]["raster"]["sha256"]
        or peer["local_format_validation"]["format_valid"] is not True
        or peer["literal_lattice_overlap"]["candidate_within_3px_of_reference"] <= 0.70
        or peer.get("literal_uniqueness_pass") is not False
    ):
        raise ValueError("Peer research audit or negative decision changed")
    if (
        band["schema"] != "band6-provenance-audit-v1"
        or band["organizer_authentication"] != "not established"
    ):
        raise ValueError("Band-6 provenance audit is malformed")
    if floor["lane"] != "S2D-36" or floor["ok_to_submit"] is not False:
        raise ValueError("External comparison floor or fail-closed status changed")
    e = escape
    tr, mobile = [], []
    for row in audit["rows"]:
        name = Path(row["source_file"]["path"]).name
        href = e(row["download_url"], quote=True)
        overlap = row["literal_lattice_overlap_within_3px"]
        novelty = (
            f"<strong>FAIL — {overlap:.2%}</strong> of dots within 3 px of the registered lattice. "
            "Full registry and pre-placement surface not replayed."
            if row["literal_lattice_duplicate"]
            else "Lattice alone not flagged; full registry and pre-placement surface NOT audited."
        )
        owner = row["historical_best_owner_reported_unverified"]
        history = f"{owner['owner_reported']:.4f} OWNER-REPORTED / UNVERIFIED"
        historical_file = f"<code>{e(owner['name'])}</code>"
        source = f'<a href="{e(row["source_card"]["source_url"], quote=True)}">Source run card</a>'
        file_link = (
            f'<a href="{href}"><code class="portfolio-file">{e(name)}</code></a>'
            f'<br><span class="micro">SHA-256 {row["source_file"]["sha256"][:16]}…; exact file format and strict [0,1] '
            f"{'PASS' if row['format_valid'] and row['strict_whole_array_finite_0_1'] else 'NOT PASS'}</span>"
        )
        score = _holdout(row["holdout"]) + "<br>" + source
        site_feed = latest[row["site"]]
        if site_feed["status"] != "checked":
            source_state = "UNKNOWN — GitHub check failed"
        elif site_feed["latest_main_ref"] != row["source_ref"]:
            source_state = "CHANGED — latest commit not re-audited"
        else:
            source_state = "UNCHANGED since audited commit"
        tr.append(
            f'<tr><th scope="row">{e(row["site"])}</th><td>{file_link}</td><td>{score}</td>'
            f"<td>NOT ESTIMABLE</td><td>{historical_file}<br>{e(history)}<br>"
            f'<span class="micro">Claimed filename/score; no organizer receipt.</span></td>'
            f"<td>{novelty}</td><td>{e(source_state)}</td><td><strong>NO</strong></td></tr>"
        )
        mobile.append(
            f"<article><h3>{e(row['site'])}</h3><p>{file_link}</p><p>{score}</p>"
            f"<p>Leaderboard estimate: NOT ESTIMABLE</p><p>{historical_file}<br>{e(history)}</p><p>{novelty}</p>"
            f"<p>Source: {e(source_state)}</p><p><strong>SUBMIT: NO</strong></p></article>"
        )
    research = f"""<section id="current-focus-files"><h2>Current nine-site research file review</h2>
<p><strong>Before another experiment:</strong> the frozen lattice counts force at least 82.34% overlap for any 37,654-dot in-footprint candidate. This is a geometric bound, not a score. No method lane is assigned and no exception was made. <a href="protocol-feasibility-20261027.md">Reproducible feasibility check and next steps</a> · <a href="research-directions-20261027.md">Four ranked unexecuted hypotheses and data availability</a>.</p>
<p><strong>Nothing is approved to submit.</strong> On {e(audit["checked_utc"])} one explicitly named TIFF and its run card from each site were fetched at immutable commits and rechecked. All nine exact files passed the local grid/range checks and <strong>all nine fail the literal 70% overlap rule</strong> against the retained calibration lattice. This is one decisive comparator, not a complete current registry; no score surface or model was replayed. Click a filename to download for research only.</p>
<p>The “best” historical number is an unverified owner claim, not a verified score. Featured source files are not ranked against one another: their evaluators and withheld sets differ. No leaderboard score estimate is defensible. Source feed checked {e(feed["checked_utc"])}: {moved} sites moved beyond these nine-file audit refs and {unknown} checks failed. These states describe only that timestamp; they are not a live source check. A changed source has not been re-audited.</p>
<div class="tablewrap" tabindex="0" role="region" aria-label="Current nine-site research audit"><table><thead><tr><th>Site</th><th>Research download / file check</th><th>Source holdout evidence</th><th>Leaderboard estimate</th><th>Best historical claim</th><th>Literal uniqueness</th><th>Source freshness</th><th>Submit?</th></tr></thead><tbody>{"".join(tr)}</tbody></table></div>
<div class="portfolio-mobile">{"".join(mobile)}</div><p><a href="data/current_focus_nine_file_audit_20261027.json">Machine-readable nine-file audit</a> · <a href="data/current_focus_source_pins_20261027.json">Pinned source identities</a> · <a href="data/portfolio_freshness.json">Source feed</a></p></section>"""
    tmcg_name = e(tmcg["submission_name"], quote=True)
    unique_name = e(unique["submission_name"], quote=True)
    peer_url = peer["source_identities"]["raster"]["source_url"].replace("/blob/", "/raw/", 1)
    alert = f"""<section class="card" id="oct27-integrity"><h2>New integrity review: download for research; do not submit</h2>
<p><strong>No new TIFF or experiment was produced by this review; no slot was spent.</strong> Two files from concurrent merged sessions remain research artifacts. Both fail literal uniqueness. H-UNIQUE-07 also used the full fault catalogue in fold eligibility, including withheld segments; its reported holdout is invalid. Its raw-feature canary did not test that mask.</p>
<div class="actions"><a class="button" href="{e(peer_url, quote=True)}">Download pinned S2D-36 TIFF — research only, SUBMIT: NO</a><a class="button" href="downloads/{tmcg_name}" download>Download TMCG — research only</a><a class="button" href="downloads/{unique_name}" download>Download quarantined H-UNIQUE-07 — research only</a></div>
<p>S2D-36 exact-file recheck: SHA-256 <code class="hash">{peer["source_identities"]["raster"]["sha256"]}</code>; local float32/grid/range and strict whole-array [0,1] checks pass, but <strong>{peer["literal_lattice_overlap"]["candidate_within_3px_of_reference"]:.2%}</strong> of its dots are within 3 pixels of the retained lattice (limit 70%). Neither template organizer origin nor portal acceptance is established. <a href="data/peer_s2d36_audit_20261028.json">Read the independent research audit</a>.</p>
<p>TMCG: {tmcg["correlation_overlap_vs_registry"]["rows"][0]["candidate_dot_overlap_within_3px"]:.2%} final-dot overlap with the lattice; source-recorded HOLDOUT-DTI {tmcg["holdout"]["dti"]:.5f} [0.06271, 0.08168], <code>gems-segment-pooled-v1</code>, 60,988 withheld, not replayed. H-UNIQUE-07: {unique["correlation_overlap_vs_registry"]["rows"][0]["candidate_dot_overlap_within_3px"]:.2%} lattice overlap and leaked holdout. Neither original pre-placement check is established.</p>
<p>The highest local main-branch point record remains S3DEP1 (0.16606, not replayed). A pinned GEMSDOE36 S2D-36 source reports <strong>HOLDOUT-DTI {floor["holdout"]["dti"]:.6f}</strong> [{floor["holdout"]["ci95"]["interval"][0]:.6f}, {floor["holdout"]["ci95"]["interval"][1]:.6f}], <code>gems-segment-pooled-v1</code>, 60,988 withheld. We conservatively use this as a prospective comparison floor; it is not a scientifically replayed or proven comparable winner. Its exact TIFF also fails the literal lattice gate; the source reports a historical feature-value canary, not an independently verified full missingness screen. <a href="https://github.com/buffedlizard55-lab/GEMSDOE36/blob/4b717aaff6eaf5de9b53030e637f8e1cf0d56e43/evidence/s2d36_run_card_20261027.json">Pinned source run card</a>. KPL-36 reports 0.17010; open PR #50 separately reports DRAIN5 0.16950. Neither is a submit authorization.</p>
<p>Band-6 correction: the legacy name <code>bouguer_tc_mgal</code> does not establish gravity or mGal units. In a fixed 250,000-pixel sample it has Spearman {band["correlations"]["TC"]["spearman"]:.5f} with cached GeoDAWN radiometric total count, while the mirror tag says magnetic tilt/curvature. Identity and source authentication remain unverified.</p>
<p><strong>Official-text distinction:</strong> the public format text calls for single-band float32 in [0,1], the supplied grid, and null/NaN outside bounds. Our allfinite variant instead writes zero outside the sample footprint. The earlier portal rejection cause is unknown; neither variant has an organizer acceptance receipt. <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">Official format</a> · <a href="https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516/4">Pixel-exact mask clarification</a>.</p>
<p><a href="data/tmcg_integrity_review_20261027.json">TMCG exact-file audit</a> · <a href="data/unique07_integrity_review_20261027.json">H-UNIQUE-07 leakage audit</a> · <a href="data/band6_provenance_review_20261027.json">Band-6 provenance audit</a> · <a href="data/official_public_review_20261027.json">Official-source review and access-policy incident</a> · <a href="data/site_browser_integrity_review_20261027.json">Browser accessibility review</a></p></section>"""
    return {"alert": alert, "current": research}
