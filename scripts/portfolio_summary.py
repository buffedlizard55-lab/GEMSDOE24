"""Evidence-bound nine-site executive view; never select a slot or forecast a score."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
from html import escape
from pathlib import Path

from audit_priority_portfolio import comparator_entries

from gems.novelty import is_duplicate
from gems.validator import sha256_file

SITES = {f"GEMSDOE{n}" for n in (24, 25, 27, 28, 30, 31, 32, 33, 36)}
AUDIT_PATH = "evidence/portfolio_artifact_audit_20261026.json"


def finite_number(value, lo, hi):
    return type(value) in (int, float) and math.isfinite(value) and lo <= value <= hi


def validate_audit(audit, manifest):
    """Verify the recorded audit's scope and recompute its negative gate decisions."""
    if audit.get("audit_version") != "nine-site-artifact-audit-v1":
        raise ValueError("Unknown portfolio audit version")
    if audit.get("submission_authorized") is not False or audit.get("verdict") != "negative":
        raise ValueError("Portfolio review cannot authorize a submission")
    if (
        audit.get("leaderboard_estimate") is not None
        or audit.get("organizer_confirmed_scores") != []
    ):
        raise ValueError("Portfolio artifact audit is not score evidence")
    if audit.get("all_discovered_files_accounted_for") is not True:
        raise ValueError("Incomplete portfolio audit")
    expected_pins = {s["repo"]: s["ref"] for s in manifest["sources"]}
    pins = {s["repo"]: s["ref"] for s in audit["sources"]}
    if len(audit["sources"]) != 9 or pins != expected_pins:
        raise ValueError("Portfolio pins do not match its registry")
    if {s.split("/")[-1] for s in pins} != SITES:
        raise ValueError("All nine portfolio sites are required")
    roster = {
        (r["repo"], r["file"]): r
        for section in ("unique_rasters", "duplicate_content_variants", "rejected")
        for r in manifest[section]
    }
    inventory = {(r["repo"], r["file"]): r for r in audit["inventory"]}
    if len(inventory) != len(audit["inventory"]) or set(inventory) != set(roster):
        raise ValueError("Portfolio inventory must account for every file exactly once")
    if any(row["sha256"] != roster[key]["sha256"] for key, row in inventory.items()):
        raise ValueError("Portfolio inventory identity drift")
    counts = audit["counts"]
    expected_counts = {
        "files": len(inventory),
        "distinct_valid_contents": len(manifest["unique_rasters"]),
        "encoding_or_content_aliases": len(manifest["duplicate_content_variants"]),
        "format_rejected": sum(row["format_valid"] is False for row in inventory.values()),
        "strict_all_finite_0_1": sum(
            row["strict_all_finite_0_1"] is True and row["format_valid"] is True
            for row in inventory.values()
        ),
    }
    if counts != expected_counts:
        raise ValueError("Portfolio counts disagree with its file inventory")
    targets = audit["named_artifact_audits"]
    for role in ("historical_owner_maximum", "source_featured_research_not_ranked"):
        selected = [row for row in targets if row["role"] == role]
        if len(selected) != 9 or {row["site"] for row in selected} != SITES:
            raise ValueError("Each portfolio role must cover all nine sites exactly once")
    if len(targets) != 18:
        raise ValueError("Unexpected portfolio target")
    for target in targets:
        key = ("buffedlizard55-lab/" + target["site"], target["file"])
        if (
            key not in inventory
            or target["format"] != inventory[key]
            or target["sha256"] != inventory[key]["sha256"]
        ):
            raise ValueError("Named artifact identity/format mismatch")
        if (
            target.get("ok_to_submit") is not False
            or target.get("leaderboard_estimate") is not None
        ):
            raise ValueError("Artifact comparison cannot select or project a submission")
        if (
            target.get("preplacement_surface_novelty") is not None
            or target.get("scientific_holdout_replayed") is not False
        ):
            raise ValueError("Saved dots cannot be presented as a pre-placement/scientific replay")
        novelty = target["final_dot_novelty"]
        rows = novelty["rows"]
        expected_comparators = comparator_entries(roster[key], manifest)
        expected = {(r["id"], r["file"], r["footprint_sha256"]) for r in expected_comparators}
        measured = {(r["registry_id"], r["file"], r["footprint_sha256"]) for r in rows}
        if len(measured) != len(rows) or expected != measured:
            raise ValueError("Final-dot audit must retain every comparator, including controls")
        if not rows or novelty["registry_unique_rasters"] != len(rows):
            raise ValueError("Empty or incomplete final-dot audit")
        duplicate = []
        correlations, overlaps = [], []
        for row in rows:
            # Million-element rank dot products can accumulate small roundoff above 1.
            # This is only a mathematical-domain tolerance, not a change to 0.90.
            ranks = [row["raw_spearman"], row["kernel_spearman"]]
            if any(v is not None and not finite_number(v, -1 - 1e-9, 1 + 1e-9) for v in ranks):
                raise ValueError("Invalid rank evidence")
            overlap = row["candidate_dot_overlap_within_3px"]
            if not finite_number(overlap, 0, 1):
                raise ValueError("Invalid overlap evidence")
            flag = any(is_duplicate(v, overlap) for v in ranks)
            if row["duplicate"] is not flag:
                raise ValueError("Duplicate flag contradicts measured statistics")
            duplicate.append(flag)
            correlations.extend(abs(v) for v in ranks if v is not None)
            overlaps.append(overlap)
        if novelty["passed"] is not (not any(duplicate)):
            raise ValueError("Final-dot pass flag contradicts registry evidence")
        if novelty["max_abs_rank_correlation"] != max(correlations, default=None) or novelty[
            "max_dot_overlap"
        ] != max(overlaps):
            raise ValueError("Reported novelty maxima disagree with rows")
    return audit


def source_holdout(n, card):
    """Explicit adapters, not a recursive 'pick the largest number' heuristic."""
    source_status = "SOURCE-RECORDED, NOT INDEPENDENTLY REPLAYED"
    if n == 24:
        h = card["holdout"]
        result = {
            "dti": h["dti"],
            "ci95": h["ci95"]["interval"],
            "evaluator": h["evaluator_version"],
            "withheld": h["n_withheld_positive_pixels"],
        }
    elif n == 25:
        h = card["holdout_dti"]
        result = {
            "dti": h["pooled_dti"],
            "ci95": h["ci_95"],
            "evaluator": h["evaluator_version"],
            "withheld": h["withheld_positives"],
        }
    elif n == 27:
        return {
            "label": "HOLDOUT-DTI",
            "status": "DISPUTED DENOMINATOR; do not rank",
            "dti": None,
            "reason": "Pinned run card states 120,778 withheld positives; pinned README states 289,180 occurrences. Independent reconciliation is absent.",
        }
    elif n == 28:
        h = card["holdout"]
        result = {
            "dti": h["dti"],
            "ci95": h["ci95"],
            "evaluator": h["evaluator_version"],
            "withheld": h["withheld_positives"],
        }
    elif n in (30, 31):
        return {
            "label": "HOLDOUT-DTI",
            "status": "NOT RUN in source record",
            "dti": None,
            "reason": "No buffered hide-and-recover result or complete feature-canary evidence for this file.",
        }
    elif n == 32:
        h = card["holdout_dti"]["primary_hide_and_recover"]
        result = {
            "dti": h["pooled_dti"],
            "ci95": h["ci95"],
            "evaluator": h["evaluator_version"],
            "withheld": h["n_withheld_positives"],
        }
    elif n == 33:
        h = card["holdout_dti"]["confirmation"][card["selected_variant"]]
        result = {
            "dti": h["dti"],
            "ci95": h["ci95"],
            "evaluator": h["evaluator_version"],
            "withheld": h["withheld_positives"],
        }
    elif n == 36:
        h = card["holdout_dti"]
        result = {
            "dti": h["pooled_candidate"],
            "ci95": h["ci95_candidate"],
            "evaluator": h["evaluator_version"],
            "withheld": h["withheld_positives"],
        }
    else:
        raise ValueError("Unknown portfolio site")
    if (
        not finite_number(result["dti"], 0, 1)
        or not isinstance(result["ci95"], list)
        or len(result["ci95"]) != 2
    ):
        raise ValueError("Invalid source holdout measurement")
    lo, hi = result["ci95"]
    if (
        not finite_number(lo, 0, 1)
        or not finite_number(hi, 0, 1)
        or not lo <= result["dti"] <= hi
        or type(result["withheld"]) is not int
        or result["withheld"] < 1
        or not result["evaluator"]
    ):
        raise ValueError("Incomplete source holdout provenance")
    return {"label": "HOLDOUT-DTI", "status": source_status, **result}


def holdout_html(record):
    if record["dti"] is None:
        return escape(record["status"]) + "<br>" + escape(record["reason"])
    lo, hi = record["ci95"]
    return (
        f"<strong>HOLDOUT-DTI {record['dti']:.5f}</strong><br>95% CI [{lo:.5f}, {hi:.5f}]<br>"
        f"<code>{escape(record['evaluator'])}</code><br>{record['withheld']:,} withheld positives<br>"
        '<span class="micro">Source-recorded; not independently replayed. Not a leaderboard estimate.</span>'
    )


def render_late_integrations(root):
    """Keep concurrent artifacts reachable without laundering their scientific claims."""
    path = root / "evidence/portfolio_concurrent_local_files_20261026.json"
    packet = json.loads(path.read_text())
    if packet.get("submission_authorized") is not False or packet.get("verdict") != "negative":
        raise ValueError("Concurrent artifact review cannot authorize a submission")
    items = []
    for row in packet["files"]:
        relative = Path(row["file"])
        if (
            relative.parts[:2] != ("docs", "downloads")
            or len(relative.parts) != 3
            or relative.suffix != ".tif"
        ):
            raise ValueError("Unsafe concurrent download path")
        if (
            sha256_file(root / relative) != row["sha256"]
            or row.get("ok_to_submit") is not False
            or row.get("generated_by_this_session") is not False
        ):
            raise ValueError("Concurrent file identity/negative verdict changed")
        check = row["validator_output"]
        if check["sha256"] != row["sha256"]:
            raise ValueError("Concurrent validator identity mismatch")
        strict = check["checks"]["variant_strict_whole_array_no_nan_allowed"]["pass"]
        status = (
            "allfinite range/grid PASS"
            if strict and check["format_valid"]
            else "interior/grid PASS; NaN-outside variant"
            if check["format_valid"]
            else "FORMAT REJECT"
        )
        items.append(
            f'<li><a href="downloads/{escape(relative.name, quote=True)}" download="{escape(relative.name, quote=True)}"><code class="portfolio-file">{escape(relative.name)}</code></a>'
            f"<br>{status} · SHA-256 {row['sha256'][:16]}… · <strong>SUBMIT NO</strong></li>"
        )
    (root / "docs/data/portfolio_concurrent_local_files_20261026.json").write_bytes(
        path.read_bytes()
    )
    return (
        '<details id="late-concurrent-files"><summary>10 late-merged local research TIFFs — preserved, not submission-approved</summary>'
        "<p>These were generated by parallel lanes and merged after the frozen nine-site pin, not generated by this review. "
        "Exact bytes were checked separately at commit <code>"
        + escape(packet["source_ref"][:12])
        + "</code>. "
        "Their scientific claims and pre-placement surfaces were not independently replayed; none is promoted here. "
        "DPRF1 was compared against these seven additional contents; its already-failed original gates remain binding.</p><ul>"
        + "".join(items)
        + '</ul><a href="data/portfolio_concurrent_local_files_20261026.json">Separate concurrent-file receipt</a></details>'
    )


def build_portfolio(root):
    root = Path(root)
    manifest_path = root / "registry/priority_rasters_20261026_portfolio.json"
    audit = json.loads((root / AUDIT_PATH).read_text())
    manifest = json.loads(manifest_path.read_text())
    if audit["identity"]["manifest_sha256"] != sha256_file(manifest_path):
        raise ValueError("Portfolio registry digest changed")
    snapshot_path = root / "registry/priority_source_snapshot_20261026_portfolio.json"
    if audit["identity"]["snapshot_sha256"] != sha256_file(snapshot_path):
        raise ValueError("Portfolio source snapshot digest changed")
    validate_audit(audit, manifest)
    claims = json.loads((root / "registry/owner_reported_scores_2026-10-26.json").read_text())
    metadata = json.loads((root / "registry/portfolio_metadata_20261026.json").read_text())
    cards = {24: json.loads((root / "evidence/dprf1_run_card_20261026.json").read_text())}
    card_urls = {24: "data/dprf1_run_card.json"}
    for row in metadata["files"]:
        path = root / row["local_evidence_path"]
        if sha256_file(path) != row["sha256"]:
            raise ValueError("Pinned peer source card changed")
        n = int(row["repo"].split("GEMSDOE")[-1])
        cards[n] = json.loads(path.read_text())
        card_urls[n] = row["source_url"]
    historical, featured, csv_rows = [], [], []
    historical_cards, featured_cards = [], []
    source_findings = {
        24: "DPRF1 is only the recorded local point-best. Fresh directed overlap also fails against EUL1 (86.66%), not just the lattice. No replay or slot.",
        25: "H71 loses its source holdout comparator; source format-only 'ok_to_upload' is not authorization.",
        27: "Source claims PROMOTE under a narrower registry. That does not pass this literal full-registry gate; withheld-count conflict unresolved.",
        28: "NCHC loses the matched source holdout baseline. Parallel protocols/seed reuse must not be pooled.",
        30: "Source holdout/canaries not run. NaN-outside encoding fails the strict whole-array finite variant, despite valid interior values.",
        31: "CSDU: 2,101 dots inside the template, 1,899 outside, 32 on catalogue. NaN companion has 2,610,312 nonfinite interior cells; source claims conflict.",
        32: "H44 loses the source control. Alternate SGMC diagnostics cannot replace the mandated primary holdout.",
        33: "LLC confirmation does not beat the source CSHT control. An exact-byte new file is not a passed uniqueness gate.",
        36: "MTO paired CI includes zero and literal novelty fails. The format-demo TIFF is not competition-grid data.",
    }
    for target in audit["named_artifact_audits"]:
        site, role = target["site"], target["role"]
        n = int(site.removeprefix("GEMSDOE"))
        f, nov = target["format"], target["final_dot_novelty"]
        other_sites = sorted(
            {
                r["repo"].split("/")[-1]
                for r in audit["inventory"]
                if r.get("footprint_sha256") == f["footprint_sha256"]
                and r["repo"] != f["repo"]
                and r["repo"].startswith("buffedlizard55-lab/")
            }
        )
        exact = (
            "Exact content also on " + ", ".join(other_sites)
            if other_sites
            else "No exact-content match on another audited focus site"
        )
        novelty = (
            f"<strong>NO — literal gate FAIL</strong><br>Max 3-px overlap {nov['max_dot_overlap']:.2%}; "
            f"max tested |ρ| {nov['max_abs_rank_correlation']:.4f}.<br>{escape(exact)}. "
            "Pre-placement surface not replayed."
        )
        if nov["passed"]:
            # This fixed negative review is not a prospective positive selector.
            novelty = "Final dots not flagged in this snapshot; pre-placement/scientific replay absent. NOT certified unique."
        file_link = (
            f'<a href="{escape(target["download_url"], quote=True)}">'
            f'<code class="portfolio-file">{escape(Path(target["file"]).name)}</code></a>'
            f'<br><span class="micro">Research/reference only · SHA-256 {target["sha256"][:16]}…</span>'
        )
        row = {
            "site": site,
            "role": role,
            "file": Path(target["file"]).name,
            "sha256": target["sha256"],
            "download_url": target["download_url"],
            "leaderboard_estimate": "NOT ESTIMABLE",
            "submission_allowed": "NO",
            "literal_final_dot_novelty": "FAIL"
            if not nov["passed"]
            else "NOT FLAGGED; full protocol unverified",
            "max_3px_overlap": nov["max_dot_overlap"],
            "exact_other_sites": "; ".join(other_sites),
            "holdout_label": "",
            "holdout_dti": "",
            "holdout_ci95": "",
            "holdout_evaluator": "",
            "withheld_positives": "",
        }
        if role == "historical_owner_maximum":
            claim = claims["best_per_site_owner_reported"][site]
            historical.append(
                f'<tr><th scope="row">{site}</th><td>{file_link}</td><td>OWNER-REPORTED / UNVERIFIED<br><strong>{claim:.4f}</strong></td><td>Not estimable</td><td>{novelty}</td><td><strong>NO</strong> — historical; do not copy or resubmit.</td></tr>'
            )
            row["owner_reported_unverified"] = f"{claim:.4f}"
            historical_cards.append(
                f"<article><h3>{site}</h3><p><strong>OWNER-REPORTED / UNVERIFIED: {claim:.4f}</strong></p>"
                f"<p>{file_link}</p><p><strong>SUBMIT: NO</strong> — historical / duplicate.</p>"
                f"<p>Estimated leaderboard score: not estimable.</p><details><summary>Uniqueness evidence</summary>{novelty}</details></article>"
            )
        else:
            card = cards[n]
            digest = card.get("raster_sha256")
            if n == 25:
                digest = card["tif"]["sha256"]
            elif n == 27:
                digest = card["raster"]["sha256"]
            elif n == 31:
                digest = card["raster_sha256"]["allfinite_fallback"]
            if digest != target["sha256"]:
                raise ValueError(f"{site} source card does not identify the reviewed exact file")
            h = source_holdout(n, card)
            status = (
                "PASS: all pixels finite [0,1]"
                if f["strict_all_finite_0_1"]
                else "Interior checks PASS; strict whole-array finite check FAIL"
            )
            if not f["format_valid"]:
                status = "FORMAT FAIL"
            featured.append(
                f'<tr><th scope="row">{site}</th><td>{file_link}<br>{escape(status)}</td><td>{holdout_html(h)}<br><a href="{escape(card_urls[n], quote=True)}">Pinned source record</a></td><td>Not estimable</td><td>{novelty}</td><td><strong>DO NOT SUBMIT</strong><br>{escape(source_findings[n])}</td></tr>'
            )
            featured_cards.append(
                f"<article><h3>{site}</h3><p>{file_link}</p><p>{escape(status)}</p>"
                f"<p><strong>SUBMIT: NO.</strong> {escape(source_findings[n])}</p>"
                f'<p>{holdout_html(h)}</p><p><a href="{escape(card_urls[n], quote=True)}">Pinned source record</a></p>'
                f"<p>Estimated leaderboard score: not estimable.</p><details><summary>Uniqueness evidence</summary>{novelty}</details></article>"
            )
            row.update(
                holdout_label="HOLDOUT-DTI / SOURCE-RECORDED",
                holdout_dti=h["dti"] if h["dti"] is not None else h["status"],
                holdout_ci95=h.get("ci95", ""),
                holdout_evaluator=h.get("evaluator", ""),
                withheld_positives=h.get("withheld", ""),
            )
        csv_rows.append(row)
    table_head = '<div class="tablewrap" tabindex="0" role="region" aria-label="{label}"><table><thead><tr><th>Site</th><th>File to download — research only</th><th>{score}</th><th>Estimated leaderboard score</th><th>Unique under the literal rule?</th><th>Okay to submit?</th></tr></thead><tbody>'
    counts = audit["counts"]
    from refresh_priority_feed import validate_feed

    feed_path = root / "docs/data/portfolio_freshness.json"
    if feed_path.exists():
        feed = validate_feed(json.loads(feed_path.read_text()), manifest["sources"])
        changed = sum(row["changed_since_review"] is True for row in feed["rows"])
        failed = sum(row["status"] == "failed" for row in feed["rows"])
        freshness = f"GitHub refs checked {feed['checked_utc']}: {changed} changed since the artifact audit; {failed} failed checks. New commits have not been raster-audited here."
    else:
        freshness = "Source freshness has not been checked against this artifact snapshot."
    intro = f"""<section id="portfolio-audit"><h2>Nine-Site Executive Summary — refreshed artifact audit</h2>
<p><strong>Best file approved to submit: NONE. NOT OK TO SUBMIT.</strong> No new TIFF was generated in this review.
The download above is an existing research result, not a new submission. We will not make a copy look unique by renaming or perturbing it.</p>
<p>{counts["files"]} TIFF files reopened at nine immutable source refs, including local historical controls;
{counts["distinct_valid_contents"]} distinct valid in-footprint contents, {counts["encoding_or_content_aliases"]} encoding/content aliases,
{counts["format_rejected"]} rejected files. Exact audit: {escape(audit["checked_utc"])}. All pre-placement surfaces and scientific training runs were <strong>not replayed</strong>.</p>
<p class="micro">{escape(freshness)} <a href="data/portfolio_freshness.json">Freshness receipt</a></p>
<p>Source-recorded HOLDOUT-DTI is not an organizer result. Differing evaluators and withheld sets must not be ranked together.
There is no defensible calibrated leaderboard estimate; “not estimable” is not a zero score.</p>
<div class="actions"><a class="button" href="data/portfolio_summary_20261026.csv" download>Download the nine-site table .csv</a>
<a class="button" href="data/portfolio_artifact_audit_20261026.json" download>Full artifact / uniqueness audit .json</a>
<a class="button" href="portfolio-review-20261026.md">Findings, sources &amp; next steps</a>
<a class="button" href="data/portfolio_run_card_20261026.json" download>Session negative run card</a></div></section>"""
    history = (
        '<section id="portfolio-historical"><h2>Highest historical result listed for each site</h2>'
        "<p>These figures are preserved owner claims, <strong>not ORGANIZER-CONFIRMED</strong>, not HOLDOUT-DTI, and not forecasts. "
        "The linked encoding is hash-checked; a score-to-uploaded-byte association has not been authenticated.</p>"
        + table_head.format(
            label="Historical nine-site comparison", score="Historical claim — not verified score"
        )
        + "".join(historical)
        + '</tbody></table></div><div class="portfolio-mobile">'
        + "".join(historical_cards)
        + "</div></section>"
    )
    current = (
        '<section id="portfolio-current"><h2>Current reviewed research files — not performance-ranked</h2>'
        "<p>These are the pinned source-featured files (DPRF1 is GEMSDOE24’s local recorded point-best), not selections for a weekly slot. "
        "The shared final-dot audit retains every control and excludes only each file’s own encodings. No sibling PASS badge overrides this protocol.</p>"
        + table_head.format(
            label="Current nine-site research files",
            score="Source-recorded HOLDOUT-DTI / evidence gap",
        )
        + "".join(featured)
        + '</tbody></table></div><div class="portfolio-mobile">'
        + "".join(featured_cards)
        + "</div></section>"
    )
    lattice = audit["literal_lattice_obstruction"]["geometry"]
    proof = f"""<section id="portfolio-obstruction"><h2>Why another standard-budget run is blocked before placement</h2>
<p>The retained lattice leaves only {lattice["footprint_3px_uncovered_pixels"]:,} template cells farther than 3 px from its dots.
Any {37654:,}-dot set inside that footprint therefore has overlap at least
<strong>{lattice["pigeonhole_min_overlap_for_candidate_size"]:.2%}</strong>, already above the 70% limit.
This is a combinatorial lower bound, not proof of copied geology. It applies at this budget, not every conceivable smaller budget.</p>
<p>No control was dropped, no cutoff relaxed, no points moved into lattice holes, and no stopped lane rerun.
The prompt still lacks its single-method paragraph. The required new gate-passing TIFF remains <strong>unachieved</strong>, not pending a human inspector.</p></section>"""
    guide = """<section id="portfolio-submission-guide"><h2>Exactly how a future approved file would be submitted</h2>
<p><strong>No currently reviewed file is approved.</strong> This is a procedure, not authorization.</p>
<ol class="steplist"><li><h3>Require a complete automated PASS packet</h3><p>It must beat the current comparable holdout best with a paired CI, pass per-feature canaries, pre-placement and final literal registry checks, exact-file validation, independent replay and the separate quota-aware selector. No manual override.</p></li>
<li><h3>Download the exact released TIFF</h3><p>Match filename and SHA-256. Use a single-band GeoTIFF or a ZIP containing exactly that TIFF. Do not upload the feature stack, preview or an old renamed prediction.</p></li>
<li><h3>Open the official competition submission page</h3><p>Use <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">DrivenData GEMS</a> → Submit → Make new submission. The project does not automate that portal.</p></li>
<li><h3>Choose the file and copy its note</h3><p>Use the validated filename and the release packet’s comment under Note (optional), at most 140 characters here. Preserve the artifact-linked result receipt.</p></li></ol>
<p>Current account allowance is unknown. Historical references to three submissions per week are not a live quota check.</p>
<h3>“Predicted values must be in range [0, 1]”</h3><p>The local validator checks finite [0,1] values inside the pinned footprint and separately checks every stored cell. The DPRF1 zero variant is allfinite; its NaN-outside companion follows the inherited sample convention but fails a strict no-NaN test. The earlier portal rejection’s exact cause is unknown. Neither convention guarantees organizer acceptance.</p></section>"""
    buffer = io.StringIO(newline="")
    fields = list(csv_rows[0])
    for row in csv_rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    writer = csv.DictWriter(buffer, fieldnames=fields)
    writer.writeheader()
    writer.writerows(csv_rows)
    docs = root / "docs/data"
    (docs / "portfolio_summary_20261026.csv").write_text(buffer.getvalue())
    # A concise text deliverable is generated from the same identity-bound rows.
    best = next(
        row
        for row in csv_rows
        if row["site"] == "GEMSDOE24" and row["role"] == "source_featured_research_not_ranked"
    )
    lines = [
        "# Nine-site executive decision — 2026-10-26",
        "",
        "**DOWNLOAD existing research: YES. SUBMIT: NO. New TIFFs: 0.**",
        "",
        "The requested new, higher-scoring, genuinely unique submission was not achieved. No old prediction was renamed or copied into a new submission.",
        "",
        f"[Download existing DPRF1 research TIFF](downloads/{best['file']}) · [Full submission guide](executive-summary.html) · [Scientific findings and sources](portfolio-review-20261026.md)",
        "",
        f"**Exact file:** `{best['file']}`  ",
        f"**SHA-256:** `{best['sha256']}`",
        "",
        "DPRF1 is the recorded local point-best, not a verified cross-site winner. Its source-recorded HOLDOUT-DTI is 0.16379, 95% CI [0.15045, 0.17739], `gems-segment-pooled-v1`, 60,988 withheld positives; not replayed here and not a leaderboard forecast.",
        "",
        "## Highest historical owner claim by site",
        "",
        "Every value below is OWNER-REPORTED / UNVERIFIED, not ORGANIZER-CONFIRMED. No file is approved for submission. Encoding identity is verified, not association with an actual uploaded score.",
        "",
        "| Site | Exact historical reference download | Unverified owner claim | New submission? |",
        "|---|---|---:|---|",
    ]
    for row in csv_rows:
        if row["role"] == "historical_owner_maximum":
            lines.append(
                f"| {row['site']} | [`{row['file']}`]({row['download_url']}) | {row['owner_reported_unverified']} | NO — historical / duplicate |"
            )
    lines += [
        "",
        "## Current source-featured research — not a performance ranking",
        "",
        "No defensible leaderboard estimate is available for any file. Different evaluators/withheld sets are not interchangeable. All listed final-dot audits fail the literal rule; pre-placement surfaces were not replayed.",
        "",
        "| Site | Exact research download | Source-recorded evidence, not replayed | Submit? |",
        "|---|---|---|---|",
    ]
    for row in csv_rows:
        if row["role"] != "source_featured_research_not_ranked":
            continue
        h = source_holdout(
            int(row["site"].removeprefix("GEMSDOE")),
            cards[int(row["site"].removeprefix("GEMSDOE"))],
        )
        evidence = (
            h["status"]
            if h["dti"] is None
            else f"HOLDOUT-DTI {h['dti']:.5f}; 95% CI [{h['ci95'][0]:.5f}, {h['ci95'][1]:.5f}]; `{h['evaluator']}`; {h['withheld']:,} withheld positives"
        )
        lines.append(
            f"| {row['site']} | [`{row['file']}`]({row['download_url']}) | {evidence} | NO |"
        )
    lines += [
        "",
        "## Material findings",
        "",
        f"- Reopened {counts['files']} TIFFs: 167 distinct valid contents, 157 aliases, two format rejects. All 18 selected artifacts fail the literal final-dot comparison.",
        "- DPRF1 also fails against the real EUL1 method at **86.66% directed overlap**, not just the lattice (99.56%). Reverse-direction overlap is not interchangeable.",
        "- H33-B2's mask exactly equals D2.8 minus 6,436 dots within 200 m of the catalogue. False-positive cleanup is a plausible explanation for the owner's 0.2778 claim, not proof of hidden-score causality.",
        "- The named GEMSDOE28 and GEMSDOE33 historical files are not the simple B2 supersets described in some older summaries. Exact dot-set differences are in the new audit.",
        "- GEMSDOE31 CSDU has only 2,101 of its 4,000 dots inside the template and 32 on the catalogue; its NaN companion has 2,610,312 invalid interior cells. The GEMSDOE36 format demo is off-grid.",
        "- The retained lattice forces at least **82.34% overlap at 37,654 dots**. No control was removed and no smaller budget chosen to evade it.",
        "- The raw feature raster and 30-channel CPU cache were restored and hash-checked. They remain ignored bulk data, from a pinned owner mirror rather than authenticated organizer access.",
        "- Proposed graben-pair science was found already implemented on GEMSDOE36. The corrected unexecuted queue prioritizes texture discontinuity, radiometric spatial lag and phase congruency; no improvement is claimed.",
        "",
        "**Limitations:** missing assigned lane, no new geological experiment or independent scientific replay, no calibrated hidden-score estimate, no artifact-linked organizer receipt, no verified current quota. Later source commits are not silently included in this pinned audit.",
        "",
        "[Full CSV](data/portfolio_summary_20261026.csv) · [Complete file/uniqueness audit](data/portfolio_artifact_audit_20261026.json) · [Source freshness](data/portfolio_freshness.json)",
    ]
    (root / "docs/portfolio-executive-summary.md").write_text("\n".join(lines) + "\n")
    (root / "docs/portfolio-hypotheses-20261026.md").write_bytes(
        (root / "knowledge/26_portfolio_plan_corrections_2026-10-26.md").read_bytes()
    )
    (docs / "portfolio_artifact_audit_20261026.json").write_bytes((root / AUDIT_PATH).read_bytes())
    run_path = root / "evidence/portfolio_run_card_20261026.json"
    run = json.loads(run_path.read_text())
    if (
        run.get("verdict") != "negative"
        or run.get("ok_to_submit") is not False
        or run.get("goal_achieved") is not False
        or run.get("raster_sha256") is not None
        or run.get("submission_name") is not None
        or run.get("holdout_dti", {}).get("value") is not None
        or run.get("artifact_audit_sha256") != sha256_file(root / AUDIT_PATH)
        or run.get("reviewed_existing_artifact", {}).get("sha256") != best["sha256"]
        or type(run.get("submission_note")) is not str
        or not 0 < len(run["submission_note"]) <= 140
        or run.get("submission_note_chars") != len(run["submission_note"])
    ):
        raise ValueError("Portfolio run card cannot invent an experiment or authorization")
    (docs / "portfolio_run_card_20261026.json").write_bytes(run_path.read_bytes())
    for name in ("portfolio_source_claims_20261026.json",):
        (docs / name).write_bytes((root / "evidence" / name).read_bytes())
    return {
        "intro": intro,
        "late_integrations": render_late_integrations(root),
        "historical": history,
        "current": current,
        "obstruction": proof,
        "guide": guide,
        "audit_sha256": hashlib.sha256((root / AUDIT_PATH).read_bytes()).hexdigest(),
    }
