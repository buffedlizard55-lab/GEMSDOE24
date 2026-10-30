#!/usr/bin/env python3
"""Build the nine-site research/decision summary from pinned evidence JSON.

The default command updates only the HTML. An archival experiment card is never
rewritten implicitly; use --refresh-archival-run-card only when intentionally
reconstructing that historical card.

Labels: HOLDOUT-DTI (evaluator, count, CI) | OWNER-REPORTED (unverified) |
NOT ESTIMABLE. A format pass is never submission authorization.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EV = ROOT / "evidence"
CANDIDATE_NAME = "gems24-nine-complement-seghgb-20261029-zeros.tif"
CANDIDATE_REL = f"docs/downloads/{CANDIDATE_NAME}"
NOTE = (
    "GEMS24 nine-complement seg-HGB 37654 dots | 0 overlap vs 9 focus sites | "
    "HOLDOUT-DTI 0.0369 | research only; SUBMIT NO"
)

# Owner-reported values transcribed from the owner's request text (not organizer receipts).
# Keyed by the pinned site/file that the registry lists for that site.
OWNER_REPORTED = {
    "GEMSDOE24": (
        "0.2477",
        "h25-1-dotted-h19-5-d1-5 (owner listed the -nan name; pinned file is -allfinite)",
    ),
    "GEMSDOE25": (
        "0.2600",
        "dotted-h19-5-d2-8 (owner listed the -nan name; pinned file is -zeros)",
    ),
    "GEMSDOE27": (
        "0.2449",
        "topo-gap-closure-t-v2-on-d1-5 (owner listed -nan; pinned file is -allfinite)",
    ),
    "GEMSDOE28": ("0.2710", "h36-1-rung30-blind-r1 (owner listed -nan; pinned file is -allfinite)"),
    "GEMSDOE30": ("0.2600", "d28-poisson300m-offcat-44090"),
    "GEMSDOE31": ("0.2708", "h27-4-solo-d28 (owner listed -nan; pinned file is -allfinite)"),
    "GEMSDOE32": (
        "0.2778",
        "h33-h33-2-b2 (B2) — highest owner-reported value on the nine-site list",
    ),
    "GEMSDOE33": ("0.2632", "h33d-analog-tip-stepover-r30"),
    "GEMSDOE36": ("0.2750", "anderson-geothermal-pinn-38854 (-zeros)"),
}


GEO1_REL = (
    "downloads/GEMSDOE24-geo1-concealed-conduit-rad-mag-lidar-20261029-8c9946590ca7-zeros.tif"
)
GEO1_CARD = "geo1_run_card.json"


def geo1_facts():
    """Read geometry, but fail closed unless the source-level holdout audit is intact."""
    card = load(GEO1_CARD)
    overlap = load("geo1_registry_overlap_20261029.json")
    audit = load("geo1_holdout_leakage_audit_20261030.json")
    for rel, expected in audit["sha256"].items():
        actual = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
        if actual != expected:
            raise RuntimeError(f"GEO1 audit source changed: {rel}")

    nine = [r for r in overlap["all"] if "data/research/nine_site/" in r["file"]]
    lattice = [r for r in overlap["all"] if "lattice" in r["file"]]
    other = [
        r for r in overlap["all"]
        if "data/research/nine_site/" not in r["file"] and "lattice" not in r["file"]
    ]
    if not nine or not lattice or not other:
        raise RuntimeError("GEO1 overlap receipt is incomplete; report fails closed")
    max_nine = max(nine, key=lambda r: r["overlap_candidate_within_3px"])
    max_other = max(other, key=lambda r: r["overlap_candidate_within_3px"])
    return {
        "file": card["submission_name"],
        "sha256": card["validator_output"]["sha256"],
        "dots": int(card["validator_output"]["in_footprint_positive_pixels"]),
        "holdout_status": audit["disposition"],
        "holdout_finding": audit["finding"],
        "max_nine": max_nine["overlap_candidate_within_3px"],
        "max_nine_file": max_nine["file"],
        "lattice": max(lattice, key=lambda r: r["overlap_candidate_within_3px"])[
            "overlap_candidate_within_3px"
        ],
        "max_other_nonlattice": max_other["overlap_candidate_within_3px"],
        "max_other_file": max_other["file"],
        "verdict": card["verdict"],
        "ok_to_submit": card["ok_to_submit"],
        "note": card["note"],
    }


def load(name):
    return json.loads((EV / name).read_text())


def pct(x):
    return f"{100 * x:.1f}%"


def raw_download_url(url: str) -> str:
    """Convert a pinned GitHub blob page to its direct immutable raw URL."""
    return url.replace("github.com/", "raw.githubusercontent.com/").replace("/blob/", "/", 1)


def build_html(ov, seg, comp, reg, feasibility, preflight, b2, b2_ancestry, restore, preparation, priority_feed):
    g = geo1_facts()
    site_rows = []
    b2_row = [
        value
        for site, value in ov["nine_site_matrix_row_to_col"]["GEMSDOE32"].items()
        if site != "GEMSDOE32"
    ]
    pct_lo = f"{100 * min(b2_row):.1f}%"
    pct_hi = f"{100 * max(b2_row):.1f}%"
    min_pair = min(
        value
        for site, row in ov["nine_site_matrix_row_to_col"].items()
        for other, value in row.items()
        if site != other
    )
    best_owner = max(OWNER_REPORTED.items(), key=lambda item: float(item[1][0]))

    for site, rec in ov["champions"].items():
        max_other = ov["max_overlap_with_any_other_focus_site"][site]
        download = raw_download_url(rec["url"])
        site_rows.append(
            f"<tr><th scope='row'>{html.escape(site)}</th>"
            f'<td><a class="download" href="{html.escape(download, quote=True)}" '
            f'download="{html.escape(rec["file"], quote=True)}">Download GeoTIFF</a>'
            f"<br><code>{html.escape(rec['file'])}</code>"
            f"<br><small>SHA-256 <code>{rec['sha256'][:16]}…</code> · pinned owner-repository commit</small></td>"
            f"<td>{rec['dots']:,}</td>"
            f"<td><b>{OWNER_REPORTED[site][0]}</b>"
            f"<br><small>OWNER-REPORTED · UNVERIFIED</small></td>"
            "<td><b>NOT ESTIMABLE</b><br><small>no organizer receipt</small></td>"
            f"<td>{pct(max_other)}</td>"
            f"<td><b>{'YES' if max_other <= 0.70 else 'NO'}</b>"
            f"<br><small>vs the other eight; 70% gate</small></td>"
            "<td>Download: research snapshot<br><b>Submit: NO</b></td></tr>"
        )

    cand = ov["candidate"]
    comp_score = comp["holdout_dti"]
    comp_ci = comp_score["ci95"]
    comp_protocol = (
        f"HOLDOUT-DTI · {html.escape(comp_score['evaluator_version'])} · "
        f"{comp_score['n_withheld_positive_pixels']:,} withheld positives · "
        f"95% CI [{comp_ci[0]:.4f}, {comp_ci[1]:.4f}]"
    )
    site_rows.append(
        "<tr><th scope='row'>Prior research candidate<br><small>2026-10-29 · not a focus-site champion</small></th>"
        f'<td><a class="download" href="downloads/{CANDIDATE_NAME}" '
        f'download="{CANDIDATE_NAME}">Download research GeoTIFF</a>'
        f"<br><code>{CANDIDATE_NAME}</code>"
        f"<br><small>SHA-256 <code>{cand['sha256'][:16]}…</code></small></td>"
        f"<td>{cand['dots']:,}</td><td>—</td>"
        f"<td><b>NOT ESTIMABLE</b><br><small>{comp_protocol}</small></td>"
        f"<td>{pct(cand['overlap_vs_nine_max'])}</td>"
        f"<td><b>YES vs nine</b><br><small>not vs full local registry</small></td>"
        "<td>Download: research only<br><b>Submit: NO</b></td></tr>"
    )
    site_rows.append(
        "<tr><th scope='row'>Prior GEO1 research artifact<br><small>holdout integrity FAIL</small></th>"
        f'<td><a class="download" href="{html.escape(GEO1_REL, quote=True)}" '
        f'download="{html.escape(g["file"], quote=True)}">Download research GeoTIFF</a>'
        f"<br><code>{html.escape(g['file'])}</code>"
        f"<br><small>SHA-256 <code>{g['sha256'][:16]}…</code></small></td>"
        f"<td>{g['dots']:,}</td><td>—</td>"
        "<td><b>NOT ESTIMABLE</b><br><small>recorded HOLDOUT-DTI invalid; full-catalogue eligibility leakage</small></td>"
        f"<td>{pct(g['max_nine'])}</td>"
        f"<td><b>YES vs nine</b><br><small>NO vs local registry: lattice {pct(g['lattice'])}</small></td>"
        "<td>Download: research only<br><b>Submit: NO</b></td></tr>"
    )

    matrix_head = "".join(f"<th scope='col'>{html.escape(site[-2:])}</th>" for site in ov["champions"])
    matrix_rows = []
    for site in ov["champions"]:
        cells = []
        for other in ov["champions"]:
            value = ov["nine_site_matrix_row_to_col"][site][other]
            style = "" if site == other else (" class='hi'" if value > 0.70 else "")
            cells.append(f"<td{style}>{value:.3f}</td>")
        matrix_rows.append(f"<tr><th scope='row'>{html.escape(site)}</th>{''.join(cells)}</tr>")

    budget_lines = []
    for item in feasibility["budgets"]:
        budget_lines.append(
            f"<li><b>{item['candidate_dot_count']:,} dots:</b> at least "
            f"{item['minimum_overlapping_dots']:,} ({pct(item['minimum_overlap_fraction'])}) "
            f"must fall within 3 px of the retained lattice, above the 70% limit. "
            "Status: STOP_IMPOSSIBLE_BUDGET.</li>"
        )
    comp_format = preflight["format_validation"]
    comp_decision = preflight["decision"]
    training = next(row for row in restore["files"] if row["file"] == "training_features.tif")
    prepared_sha = preparation["sha256"]
    prepared_shape = preparation["shape"]
    feed_rows = priority_feed.get("rows", [])
    changed_refs = sum(bool(row.get("changed_since_review")) for row in feed_rows)
    feed_checked = html.escape(priority_feed.get("checked_utc", "unknown"))
    advanced_after_snapshot = priority_feed.get("ref_check_note", {}).get(
        "advanced_since_2026_10_30T23_11_snapshot", []
    )
    advanced_sites = ", ".join(
        html.escape(repo.rsplit("/", 1)[-1]) for repo in advanced_after_snapshot
    )
    freshness_detail = (
        f" The later ref-only check found {advanced_sites} advanced after the 23:11 "
        "owner-README snapshot; no updated README bodies or repository files were fetched."
        if advanced_sites
        else ""
    )

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="Evidence-led GEMS DOE 24 nine-site review: pinned research downloads, score provenance, geometric uniqueness and submission gates.">
<title>GEMS DOE 24 · Nine-site decision brief</title>
<style>
:root{{--ink:#17202a;--muted:#52606d;--line:#d6dee7;--paper:#fff;--wash:#f4f7fa;--red:#9b1c1c;--redbg:#fff2f0;--green:#12643a;--greenbg:#edf9f1;--blue:#174ea6}}
*{{box-sizing:border-box}} body{{font-family:system-ui,-apple-system,Segoe UI,Arial,sans-serif;max-width:1220px;margin:0 auto;padding:24px 18px 56px;color:var(--ink);line-height:1.55;background:var(--paper)}}
h1{{font-size:clamp(2rem,4vw,3rem);line-height:1.1;margin:.35em 0}} h2{{margin-top:2.1rem;line-height:1.2}} h3{{margin:1rem 0 .3rem}} p{{max-width:100ch}} a{{color:var(--blue)}} code{{font-size:.9em;overflow-wrap:anywhere}} small{{color:var(--muted)}}
.kicker{{text-transform:uppercase;letter-spacing:.09em;font-weight:750;color:#3b5369;font-size:.82rem}} .meta{{color:var(--muted)}}
.panel{{padding:16px 20px;border:2px solid var(--red);background:var(--redbg);border-radius:12px;margin:18px 0}} .panel strong{{color:var(--red)}} .soft{{padding:14px 18px;border:1px solid var(--line);background:var(--wash);border-radius:10px;margin:14px 0}}
.tablewrap{{overflow-x:auto;border:1px solid var(--line);border-radius:8px;margin:12px 0}} table{{border-collapse:collapse;width:100%;min-width:960px;font-size:14px}} th,td{{border:1px solid var(--line);padding:9px 10px;vertical-align:top;text-align:left}} thead th{{background:#edf2f7;position:sticky;top:0}} tbody tr:nth-child(even){{background:#fafbfd}} td.hi{{background:#ffe4e0;font-weight:700}} .download{{font-weight:750;white-space:nowrap}} .pill{{display:inline-block;border:1px solid var(--line);border-radius:100px;padding:2px 9px;font-size:.85em}}
footer{{border-top:1px solid var(--line);margin-top:36px;padding-top:16px;color:var(--muted)}}
</style></head><body>
<p class="kicker">Evidence first · no portal access · no slot used</p>
<h1>Nine-site research and submission decision</h1>
<p class="meta"><b>Reviewed:</b> 2026-10-30 · <b>Branch:</b> arena/5b3e6982-gemsdoe24 · <b>Focus:</b> GEMSDOE 24, 25, 27, 28, 30, 31, 32, 33 and 36.</p>

<section class="panel" aria-label="Current decision">
<strong>DECISION: NO FILE IS AUTHORIZED TO SUBMIT.</strong> The page contains downloadable research artifacts, not approved entries. No new experiment, prediction surface, candidate dot set, TIFF, organizer upload or submission slot was created in this review.
<ul>
<li><b>Highest owner-reported claim:</b> GEMSDOE32 B2 at 0.2778 — <b>OWNER-REPORTED / UNVERIFIED</b>, not an organizer receipt. It is not unique: {pct_lo}–{pct_hi} of its dots are within 3 px of each other focus site's dots.</li>
<li><b>All nine pinned champions fail the 70% nine-site comparison.</b> Pairwise overlap ranges from {min_pair:.3f} to 1.000; this is geometry, not proof of copying.</li>
<li>The 2026-10-29 complement research artifact clears the nine-site comparison (0.0% overlap) but overlaps the retained local lattice at {pct(reg['max_overlap'])}; its format receipt is not a selector. GEO1's recorded holdout is invalid, and its lattice overlap is {pct(g['lattice'])}.</li>
<li><b>Estimated leaderboard score: NOT ESTIMABLE</b> for every file. No current leaderboard or organizer receipt was checked.</li>
</ul></section>

<div class="soft"><b>Important distinction.</b> “Download” means only that a local research artifact is available. “Submit” requires a separate hash-bound scientific promotion/selector decision. Local GeoTIFF format validity cannot grant that decision.</div>

<h2>1. Per-site summary: exact file, reported value, score estimate and uniqueness</h2>
<p>Owner-reported numbers are preserved as claims, not verified scores. Estimated leaderboard score is <b>NOT ESTIMABLE</b> in every row. “Unique vs other eight” means no more than 70% of that site's positive dots fall within 3 pixels of any one of the other eight pinned site rasters; it does not mean unique in the entire registry.</p>
<div class="tablewrap"><table><thead><tr><th>Site / artifact</th><th>One-click pinned download</th><th>Positive dots</th><th>Owner-reported score</th><th>Estimated leaderboard score</th><th>Maximum 3-px overlap vs other eight</th><th>Unique vs other eight?</th><th>Decision</th></tr></thead><tbody>
{"".join(site_rows)}
</tbody></table></div>
<div class="soft"><b>Historical snapshot notice.</b> The GitHub-only source feed checked {feed_checked} reports {changed_refs}/{len(feed_rows)} priority-repository main refs changed since their pinned artifact audits.{freshness_detail} The changed heads and files have not been audited here; this table is not a current-site winner list. <a href="data/priority_feed.json">Open the commit-freshness receipt</a> (not a score API).</div>
<p><b>Best owner-reported value:</b> {best_owner[0]} = {best_owner[1][0]} (unverified; not unique). No score forecast is derived from this rank.</p>

<h2>2. GEMSDOE32 B2 at 0.2778: what the local evidence does and does not show</h2>
<p>The 0.2778 value remains <b>OWNER-REPORTED / UNVERIFIED</b>. Pinned pixel-forensics receipts record two deletion-only comparisons: B2 is the exact 37,654-dot subset of a 44,090-dot GEMSDOE25/GEMSDOE30 D2.8 pattern after removing {b2_ancestry['removed_from_GEMSDOE25']:,} cells within 200 m of the public catalogue; separately, the 40,199-dot D2.8-family comparison in the priority-review receipt removes {b2['removed_dots']:,} catalogue-adjacent cells. Neither comparison adds a new B2 detection. This is emission/pruning geometry, not a new detector. Hidden true-positive credit and false-positive mass are unknown, so these receipts cannot establish why the reported score changed or predict another raster's score. See the <a href="../evidence/oj1_priority_ancestry_replay.json">cross-site ancestry replay</a> and <a href="../evidence/priority_review_20261025.json">40,199-dot comparison receipt</a>.</p>

<h2>3. Prior research artifacts: not submission recommendations</h2>
<div class="tablewrap"><table><thead><tr><th>Artifact</th><th>Internal HOLDOUT-DTI (not a leaderboard score)</th><th>Nine-site geometry</th><th>Broader local registry / decision</th></tr></thead><tbody>
<tr><th scope="row">Nine-complement seg-HGB<br><small>2026-10-29 · SHA-256 {cand['sha256']}</small></th>
<td><b>HOLDOUT-DTI {comp_score['dti']:.6f}</b><br>{comp_protocol}<br><small>Source-recorded historical measurement; not rerun in this review.</small></td>
<td>0.0% max overlap vs nine champions</td>
<td>{reg['files_compared']} local registry rasters in the 2026-10-29 receipt; max dot overlap {pct(reg['max_overlap'])} vs <code>{html.escape(reg['top'][0]['file'])}</code>. Local preflight: <b>format-valid research download</b>; official-format compliance is not certified; submission status <b>{html.escape(comp_decision['submission_status'])}</b>.</td></tr>
<tr><th scope="row">GEO1 concealed-conduit<br><small>2026-10-29 · SHA-256 {g['sha256']}</small></th>
<td><b>NOT A VALID HOLDOUT RESULT.</b> Its archived DTI/CI are rejected because fold eligibility masks the full catalogue, including withheld labels, instead of using only the fold-visible catalogue. The pinned code and result are not scientifically reproducible as a holdout claim; no numeric DTI is displayed.</td>
<td>{pct(g['max_nine'])} max vs nine champions</td>
<td>83 local rasters in the 2026-10-29 overlap receipt; lattice overlap {pct(g['lattice'])}; submission status <b>DO NOT SUBMIT</b>. See <a href="repo-review-20261030-arena-5b3e6982.md">source-level audit</a>.</td></tr>
</tbody></table></div>
<p><b>Download policy:</b> both files may be downloaded for research, but neither is OK to submit. The candidate preflight recorded {comp_format['in_footprint_positive_pixels']:,} in-footprint positive cells, no NaN/Inf inside the footprint, and a whole-array [0,1] pass. It also recorded <code>official_format_compliant=false</code>, and scientific-promotion / run-card blockers remain. These local checks do not explain the historical portal rejection.</p>

<h2>4. GEO1 holdout-integrity finding</h2>
<p>The experiment card records a code SHA that matches the current source; that does not establish which bytes were actually executed. The source audit shows that in <code>scripts/build_unique_geothermal_submission.py</code>, the fold loop sets <code>eligible = fp &amp; f["valid"] &amp; ~catalogue</code>, where <code>catalogue</code> is loaded once from the full label raster. The shared <code>SegmentHoldout</code> contract requires fold-visible catalogue masking. Since the hidden fold positives are a subset of that full catalogue, this eligibility rule uses withheld labels in deciding which pixels may be predicted. Therefore the recorded GEO1 HOLDOUT-DTI, CI and canary pass cannot support method ranking or promotion. The original experiment files remain unchanged; the audit records source hashes and the invalid disposition in <a href="../evidence/geo1_holdout_leakage_audit_20261030.json">the machine-readable audit</a>.</p>

<h2>5. Uniqueness feasibility stop</h2>
<p>The 2026-10-30 necessary-bound check used the pinned spacing-5 calibration lattice as a witness; it is not a full current peer census. Within 3 px the witness covers {feasibility['coverage']['footprint_3px_covered_pixels']:,} of {feasibility['interior_coverage']['footprint_pixels']:,} footprint pixels ({pct(feasibility['coverage']['footprint_3px_coverage'])}), leaving {feasibility['coverage']['footprint_3px_uncovered_pixels']:,} uncovered. A dot budget above the bound is stopped before building any surface or placing dots.</p>
<ul>{''.join(budget_lines)}<li>The universal bound does not rule out budgets up to {feasibility['budgets'][0]['maximum_budget_not_ruled_out_by_this_bound']:,}; those budgets are <b>NOT RULED OUT</b>, not proven unique or scientifically useful.</li></ul>
<p>No surface rank-correlation or final-dot test was run this session because no candidate surface or dots were generated. Do not target uncovered lattice holes or alter the comparator set to evade this stop.</p>

<h2>6. Data provenance and known irregularities</h2>
<ul>
<li><code>data/training_features.tif</code> was restored from the owner-supplied mirror at commit <code>{html.escape(training['mirror_ref'])}</code>, SHA-256 <code>{training['sha256']}</code>. It is hash-pinned but <b>not organizer-authenticated</b>.</li>
<li>The prepared cache has {prepared_shape[0]:,} × {prepared_shape[1]} values, SHA-256 <code>{prepared_sha}</code>. Its inputs include the owner-mirror raster and previously staged bridge/derived data; this is preparation, not scientific validation.</li>
<li>Bridge <code>labels.tif</code> and <code>existing_faults.tif</code> have identical hashes; <code>sample_submission.tif</code> is a catalogue-mask-like bridge artifact, not an independent labelled example.</li>
<li>The method paragraph assigning a single lane is still missing. No geological hypothesis was selected or run.</li>
<li>No official DrivenData page, live leaderboard or portal was freshly checked in this review. The 0.3195 and 0.4413 claims remain unresolved and unverified.</li>
</ul>

<h2>7. How to submit a future authorized GeoTIFF</h2>
<div class="panel"><strong>Stop here for the current files.</strong> There is no submission-authorized artifact. The instructions below describe the mechanics for a future file only after its assigned method lane, scientific holdout, leakage canaries, pre/post uniqueness gates, and separate selector all pass.</div>
<ol>
<li>Use the shared writer, not a private export script: <code>.venv/bin/python scripts/submission_writer.py prediction.npy output.tif --template data/bridge/sample_submission.tif --outside nan</code>. Choose the exterior convention only after confirming the current official instructions; the zero-outside compatibility experiment is not organizer-accepted.</li>
<li>Run exact-file preflight against the final TIFF and its authorized run card: <code>.venv/bin/python scripts/preflight_submission.py output.tif --run-card evidence/&lt;authorized-run-card.json&gt; --note "&lt;unique name and short note&gt;" --output evidence/&lt;preflight.json&gt;</code>. The note must be at most 140 characters. A format pass alone still means <b>SUBMIT: NO</b>.</li>
<li>Confirm the final SHA-256 in the preflight matches the promoted TIFF and the independent selector's authorization. If any hash or gate differs, stop.</li>
<li>Only after that, the owner signs in to the official competition portal, chooses the authorized GeoTIFF, enters the exact note, and saves the organizer's receipt. No credentials, automated upload, or organizer receipt are available in this checkout.</li>
<li>Record the receipt as <b>ORGANIZER-CONFIRMED</b>; until then, any leaderboard score is <b>NOT ESTIMABLE</b>.</li>
</ol>

<h2>8. Pairwise overlap matrix</h2>
<p>Each cell is the share of row-site dots within 3 px of column-site dots. Red cells exceed the 70% research threshold. Similar geometry does not prove copying.</p>
<div class="tablewrap"><table><thead><tr><th scope="col">Row ↓ / Column →</th>{matrix_head}</tr></thead><tbody>{''.join(matrix_rows)}</tbody></table></div>

<h2>9. Evidence and sources</h2>
<ul>
<li>Current three-pass review: <a href="repo-review-20261030-arena-5b3e6982.md">repo-review-20261030-arena-5b3e6982.md</a> · mission: <a href="MISSION_PROMPT.md">MISSION_PROMPT.md</a> · end-of-session run card: <a href="../evidence/session_5b3e6982_20261030_run_card.json">JSON run card</a>.</li>
<li>Nine-site overlaps: <code>evidence/nine_site_overlap_20261029.json</code> · candidate registry: <code>evidence/candidate_registry_overlap_20261029.json</code> · feasibility: <code>evidence/session_5b3e6982_feasibility_20261030.json</code>.</li>
<li>Experiment cards: <code>evidence/seg_hgb_complement_experiment.json</code> · <code>evidence/geo1_run_card.json</code> · GEO1 integrity audit above.</li>
<li>Competition and rules references retained in the repository: <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">DrivenData competition</a> · <a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">NLR format/rules PDF</a>. These pages were <b>not freshly fetched</b> during this review.</li>
</ul>
<footer><b>Maximize P(Win) · Own the Outcome.</b><br>Generated from pinned local evidence by <code>scripts/build_nine_site_report.py</code>. Historical artifacts and owner claims are not current leaderboard evidence; download does not imply permission to submit.</footer>
</body></html>
"""

def build_run_card(ov, seg, comp, reg, pre):
    cand = ov["candidate"]
    return {
        "run_card_version": "1",
        "date": "2026-10-29",
        "branch": "arena/6a1fb4d1-gemsdoe24",
        "lane": "exploratory; no assigned method paragraph; NOT preregistered",
        "experiments_used": 2,
        "experiment_budget": 3,
        "hypothesis": (
            "Restricting dots to footprint pixels more than 3 px from every nine-site "
            "champion dot yields a file that is unique versus the nine focus sites while "
            "retaining detectable holdout signal from a label-free detector."
        ),
        "mechanism": (
            "Label-free features (19-band geophysics + LiDAR scarp/arc channels from the "
            "prepared cache) feed a histogram gradient-boosting classifier trained only on "
            "visible catalogue positives inside buffered training regions. The top 37,654 "
            "pixels are emitted per quadrant share, ranked after the champion-distance mask."
        ),
        "named_non_fault_mimic": (
            "Linear artefacts in gridded magnetic, gravity or DEM products (flight-line and "
            "stitching seams, road cut-and-fill, drainage incision) that look like fault edges "
            "but are not faults."
        ),
        "holdout": {
            "label": "HOLDOUT-DTI",
            "evaluator_version": comp["holdout_dti"]["evaluator_version"],
            "withheld_positive_pixels": comp["holdout_dti"]["n_withheld_positive_pixels"],
            "candidate_dti": comp["holdout_dti"]["dti"],
            "candidate_ci95": comp["holdout_dti"]["ci95"],
            "baseline_unrestricted_dti": seg["holdout_dti"]["dti"],
            "baseline_ci95": seg["holdout_dti"]["ci95"],
            "candidate_fold_components": comp["folds"],
            "exact_soft_metric_cross_check": "all four fold TP/FP/FN reproduced by dti_components_exact (see tests)",
        },
        "leakage_canary": {
            "rule": "single-feature holdout AUC > 0.90 means leakage until proven otherwise",
            "worst_single_feature_auc": seg["leakage_canary"]["worst_single_feature_auc"],
            "pass": seg["leakage_canary"]["pass"],
        },
        "overlap_vs_registry": {
            "vs_nine_focus_sites_max": cand["overlap_vs_nine_max"],
            "vs_nine_focus_sites_pearson_max": cand["pearson_vs_nine_max"],
            "vs_local_registry_max": reg["max_overlap"],
            "vs_local_registry_max_file": reg["top"][0]["file"],
            "vs_local_registry_max_abs_pearson": reg["max_abs_pearson"],
            "registry_files_compared": reg["files_compared"],
            "thresholds": {"overlap": 0.70, "pearson": 0.90},
            "gate_unique_vs_nine": cand["overlap_vs_nine_max"] <= 0.70,
            "gate_literal_registry_70pct": reg["max_overlap"] <= 0.70,
        },
        "raster": {
            "file": CANDIDATE_REL,
            "sha256": cand["sha256"],
            "dots": cand["dots"],
        },
        "validator": {
            "format_valid": pre["format_validation"]["format_valid"],
            "strict_whole_array_0_1": pre["portal_range_diagnostic"][
                "strict_whole_array_values_in_0_1"
            ],
            "nan_inside_footprint": cand["nan_inside_footprint"],
            "outside_footprint_values": [0.0],
            "crs_shape_transform_match_template": pre["format_validation"]["checks"][
                "crs_epsg_32611"
            ]["pass"]
            and pre["format_validation"]["checks"]["shape_matches_template"]["pass"],
            "preflight_decision": pre["decision"]["submission_status"],
            "preflight_blockers": pre["decision"]["blockers"],
        },
        "alternate_unique_candidate_geo1": geo1_facts(),
        "submission_name": CANDIDATE_NAME.replace(".tif", ""),
        "submission_note": NOTE,
        "submission_note_chars": len(NOTE),
        "verdict": "negative",
        "download": "YES (research; format-valid)",
        "submit": "NO",
        "submit_reasons": [
            "source-recorded HOLDOUT-DTI 0.036939 is below the matched unrestricted seg-HGB baseline 0.068516; both are internal measurements, not leaderboard scores, and neither was rerun in this review",
            "literal 70% registry rule fails against the calibration lattice (overlap 0.9728)",
            "portal rejection cause not established; no organizer receipt",
            "no promotion run card or selector quota (preflight blockers)",
        ],
        "not_estimable": "Leaderboard score NOT ESTIMABLE; HOLDOUT-DTI is internal and not comparable to the hidden leaderboard.",
        "irregularities": [
            "bridge sample_submission positives identical to labels/catalogue",
            "owner-mirror training raster, not organizer-authenticated",
            "owner-listed file names differ from pinned files (nan/allfinite/zeros) for 24, 25, 27, 28, 31",
            "method-lane paragraph absent; no lane assigned",
            "literal 70% rule incompatible with a 5-px lattice registry raster above ~22,164 dots",
        ],
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--refresh-archival-run-card",
        action="store_true",
        help="also rewrite the 2026-10-29 historical run card (normally left immutable)",
    )
    args = parser.parse_args(argv)

    ov = load("nine_site_overlap_20261029.json")
    seg = load("seg_hgb_experiment.json")
    comp = load("seg_hgb_complement_experiment.json")
    reg = load("candidate_registry_overlap_20261029.json")
    feasibility = load("session_5b3e6982_feasibility_20261030.json")
    preflight = load("session_5b3e6982_complement_preflight_20261030.json")
    b2 = load("priority_review_20261025.json")
    b2_ancestry = load("oj1_priority_ancestry_replay.json")
    restore = load("data_restore_20261025.json")
    preparation = load("data_preparation.json")
    priority_feed = json.loads((ROOT / "docs/data/priority_feed.json").read_text())
    out = ROOT / "docs/nine-site-submission-summary.html"
    out.write_text(
        build_html(
            ov, seg, comp, reg, feasibility, preflight, b2, b2_ancestry,
            restore, preparation, priority_feed
        )
    )
    print(f"wrote {out.relative_to(ROOT)}")

    if args.refresh_archival_run_card:
        archival_pre = json.loads(
            (ROOT / "docs/downloads/gems24-nine-complement-seghgb-20261029-zeros.preflight.json")
            .read_text()
        )
        card = build_run_card(ov, seg, comp, reg, archival_pre)
        (EV / "run_card_20261029_nine_site_unique.json").write_text(
            json.dumps(card, indent=2, allow_nan=False) + "\n"
        )
        print("also refreshed the archival 2026-10-29 run card")


if __name__ == "__main__":
    main()
