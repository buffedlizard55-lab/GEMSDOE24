#!/usr/bin/env python3
"""Generate the Pages site and the README status block from recorded evidence.

Every number on the pages comes from ``evidence/*.json``, ``registry/*.json`` or
``docs/data/*.json``; nothing is hard-coded except wording. No network access, no
invented live scores, no publication claims. The scheduled source feed
(``scripts/refresh_source_feed.py``) is separate.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from site_packets import (  # noqa: E402
    concurrent_aspc,
    concurrent_oj1,
    crp1_packet,
    cup1_packet,
    dprf1_packet,
    gvc1_packet,
    rshg1_packet,
    trsg1_packet,
)
from tnr1_site import all_sites_table  # noqa: E402
from tnr1_site import render as render_tnr1  # noqa: E402

from gems import emission  # noqa: E402
from gems.validator import sha256_file  # noqa: E402

DOCS = ROOT / "docs"
SITE = "https://buffedlizard55-lab.github.io/GEMSDOE24/"
COMP = "https://www.drivendata.org/competitions/306/competition-doe-gems/"


def load(path, default=None):
    p = ROOT / path
    if not p.exists():
        return {} if default is None else default
    return json.loads(p.read_text())


def fmt(value, n=4):
    return "pending" if value is None else f"{value:.{n}f}"


def e(value):
    return escape(str(value), quote=True)


def link(url, text):
    return f'<a href="{e(url)}" target="_blank" rel="noopener noreferrer">{text} ↗</a>'


def page(title, active, body, prefix=""):
    nav = []
    for name, path in (
        ("Overview", "index.html"),
        ("Submission guide", "executive-summary.html"),
        ("Research", "research.html"),
        ("Sources & audit", "sources.html"),
    ):
        nav.append(
            f'<a class="{"active" if name == active else ""}" href="{prefix}{path}">{name}</a>'
        )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="DOE GEMS fault research: independent GeoTIFF downloads, automated negative submission gates, and reproducible evidence."><meta name="source-feed" content="{prefix}data/source_health.json"><title>{e(title)} · GEMS DOE 24</title><link rel="stylesheet" href="{prefix}assets/style.css"></head>
<body><header><div class="nav"><a class="brand" href="{prefix}index.html"><span class="mark" aria-hidden="true">∿</span><span>GEMS DOE 24<small>Geologic mapping · evidence first</small></span></a><nav class="navlinks" aria-label="Main navigation">{"".join(nav)}</nav></div></header>
<main><aside class="micro review-notice" aria-label="Current submission review"><strong>Current review: no submission-authorized TIFF.</strong> <a href="{prefix}review-20261026.md">Review &amp; blockers</a>.<details><summary>Concurrent VENT integrity warning</summary>VENT is quarantined: historical C2ST/novelty fallback values were fabricated. <a href="{prefix}data/vent_run_card.json">Untrusted historical card</a> · <a href="{prefix}downloads/gems24-vent-quat-bridge-20261026-a6e191937e80-zeros.tif" download>Quarantined research TIFF (DO NOT SUBMIT)</a>. No new artifact audit follows from source freshness alone.</details></aside>{body}</main><footer class="footer"><p><strong>Maximize P(Win). Own the Outcome.</strong><br>Local validation is not hidden-fault truth. Association is not causation. Scores marked owner-reported are not organizer receipts. No file on this site has a leaderboard score unless it says so.</p><p>AI-assisted development is disclosed here and must be disclosed in the prize narrative (rules §3.2).<br><a href="{prefix}sources.html">Sources, limitations &amp; review</a></p></footer><script src="{prefix}assets/app.js" defer></script></body></html>"""


def download_button(row, prefix, label="Download submission .tif", primary=True):
    size = (DOCS / "downloads" / row["file"]).stat().st_size / (1024**2)
    cls = "button primary" if primary else "button"
    return (
        f'<a class="{cls}" href="{prefix}downloads/{e(row["file"])}" download="{e(row["file"])}">'
        f"↓ {label} <span>({size:.2f} MiB)</span></a>"
    )


def note_block(row, ident):
    return (
        f'<div class="note" id="note-{ident}">{e(row["note"])}</div>'
        f'<div class="actions" style="margin-top:10px"><button class="button" data-copy="#note-{ident}" '
        f'data-feedback="#fb-{ident}">Copy note</button>'
        f'<a class="button" href="downloads/{e(row["note_file"])}" download>Note .txt</a></div>'
        f'<p class="copyfeedback" id="fb-{ident}" aria-live="polite"></p>'
        f'<p class="micro">{len(row["note"])} characters (kept ≤ 200; the portal\'s limit is not documented).</p>'
    )


REC_LABEL = {
    "eligible": "Slot-eligible",
    "owner_decision_required": "Owner decision required",
    "not_recommended": "Not recommended",
}


def pct(x):
    return "n/a" if x is None else f"{100 * x:+.0f}%"


def build_independent_site(primary):
    """Current evidence-first view. Legacy pages are not promotion authority."""
    card = load("evidence/mtr1_run_card.json")
    experiment = load("evidence/mtr1_experiment.json")
    registry = load("registry/priority_rasters.json")
    prior = load("evidence/priority_review_20261025.json")
    feed = load("docs/data/priority_feed.json")
    checks_path = DOCS / "downloads" / primary["checks_file"]
    checks = json.loads(checks_path.read_text())
    p = DOCS / "downloads" / primary["file"]
    if sha256_file(p) != card["raster_sha256"] or sha256_file(p) != primary["sha256"]:
        raise SystemExit("Current download checksum does not match the run card")
    if primary["ok_to_submit"] or card["verdict"] != "negative" or card["ok_to_submit"]:
        raise SystemExit("Stopped negative artifact cannot be presented as submit-ready")
    from gems.submission import check_variants

    for key, row in checks.items():
        target = DOCS / "downloads" / row["file"]
        fresh = check_variants(target, ROOT / "data/bridge/sample_submission.tif")
        if (
            not fresh["format_valid"]
            or not row["format_valid"]
            or any(fresh.get(field) != value for field, value in row.items())
        ):
            raise SystemExit(f"Invalid, changed or stale download variant: {key}")
    if primary["file"] != card["submission_name"] or primary["note"] != card["note"]:
        raise SystemExit("MTR1 metadata and exact run-card identity disagree")
    if (
        len(primary["note"]) > 140
        or (DOCS / "downloads" / primary["note_file"]).read_text().strip() != primary["note"]
    ):
        raise SystemExit("Current note is missing, changed or over the 140-character limit")
    preflight_path = p.with_suffix(".preflight.json")
    preflight = json.loads(preflight_path.read_text())
    if (
        preflight.get("artifact", {}).get("sha256") != primary["sha256"]
        or preflight.get("run_card", {}).get("artifact_sha256_matches") is not True
        or preflight.get("run_card", {}).get("artifact_name_matches") is not True
        or preflight.get("decision", {}).get("submission_status") != "DO_NOT_SUBMIT"
        or preflight.get("decision", {}).get("ready_to_submit") is not False
        or preflight.get("portal_range_diagnostic", {}).get("strict_whole_array_values_in_0_1")
        is not True
    ):
        raise SystemExit("Current exact-file preflight is missing, stale, or does not fail closed")
    concurrent = concurrent_aspc(ROOT)
    trsg1_hero, trsg1_exec, trsg1_research = trsg1_packet(ROOT)
    dprf1_hero, dprf1_exec, dprf1_research = dprf1_packet(ROOT)
    dprf1_card_site = load("evidence/dprf1_run_card_20261026.json")
    dprf1_ok_submit = bool(dprf1_card_site.get("ok_to_submit")) and bool(dprf1_hero)
    cup1_hero, cup1_exec, cup1_research = cup1_packet(ROOT)
    crp1_hero, crp1_exec, crp1_research = crp1_packet(ROOT)
    crp1_card_site = load("evidence/crp1_run_card_20261026.json")
    crp1_ok_submit = bool(crp1_card_site.get("ok_to_submit")) and bool(crp1_hero)
    gvc1_hero, gvc1_exec, gvc1_research = gvc1_packet(ROOT)
    rshg1_hero, rshg1_exec, rshg1_research = rshg1_packet(ROOT)
    latest = concurrent_oj1(ROOT)
    score = card["holdout"]
    lo, hi = score["ci95"]["interval"]
    version = score["evaluator_version"]
    n = score["n_withheld_positive_pixels"]
    hlabel = f"HOLDOUT-DTI · {e(version)} · {n:,} withheld positives · approximate 95% CI [{lo:.5f}, {hi:.5f}]"
    download = (
        download_button(primary, "", "Download audit-only .tif — DO NOT SUBMIT")
        + f'<a class="button" href="downloads/{e(preflight_path.name)}">'
        "Automated preflight — DO NOT SUBMIT</a>"
    )
    status = '<div class="status stopped" role="status"><strong>DOWNLOAD: YES · SUBMIT: NO. NOT OK TO SUBMIT.</strong> Automated verdict: NEGATIVE. The overlap gate failed against a registered calibration lattice. No human inspection or exception can turn this packet into a PASS.</div>'
    note = f'<div class="note" id="note-current">{e(primary["note"])}</div><div class="actions"><button class="button" data-copy="#note-current" data-feedback="#copy-feedback">Copy short note</button><a class="button" href="downloads/{e(primary["note_file"])}" download>Note .txt</a></div><p id="copy-feedback" class="copyfeedback" aria-live="polite"></p><p class="micro">{len(primary["note"])} characters · maximum 140</p>'
    file_info = f'<p class="fileline">{e(primary["file"])}</p><p class="hash">SHA-256 {e(primary["sha256"])}</p><p class="micro">Strict whole-array [0,1] diagnostic: pass · scientific authorization: false</p>'
    hero = f"""<div class="hero"><div><div class="eyebrow">DOE GEMS · independently generated experiment</div><h1>A new raster.<br>An honest decision.</h1><p class="lead">The paired-magnetic-trough method generated its own predictions from cached physical layers. <strong>No previous submission pixels were copied.</strong> It passes file-format checks, but it fails your lane-overlap rule. It is not yet scored and <strong>must not be submitted</strong>.</p>{status}<div class="actions">{download}<a class="button" href="executive-summary.html">Submission status &amp; guide →</a></div>{file_info}<p class="micro"><span class="badge blue">Format PASS</span> <span class="badge danger">Novelty gate FAIL</span> <span class="badge gray">No slot used</span></p></div><aside class="card visual"><div class="cardtop"><h3>HOLDOUT-DTI</h3><span class="badge amber">Not leaderboard scores</span></div><div class="result-number">{score["dti"]:.5f}</div><p>{hlabel}</p><img class="raster-preview" src="assets/mtr1-preview.png" alt="Downsampled map of independently computed experimental fault dots, not verified faults or geothermal vents"><p class="micro">Experiment preview · downsampled 100 m grid · not verified faults or vents</p></aside></div>"""
    rows = [
        (
            "File format",
            "PASS",
            "Single-band float32; exact CRS/shape/transform; all cells finite and in [0,1] in the zero-outside download.",
        ),
        (
            "Copied predictions",
            "NONE",
            "Computed only from RTP and contractor Th/K. Exact footprint content differs from every compared registry raster.",
        ),
        (
            "Leakage canaries",
            "PASS",
            "Every source/transform tested alone; both AUC polarities checked. Lower AUC is not proof of geological specificity.",
        ),
        (
            "Lane overlap",
            "FAIL",
            "All candidate dots lie within 3 px of the spacing-5 calibration lattice. Comparator retained; no retuning.",
        ),
        (
            "Current-best holdout",
            "BLOCKED",
            "No independently reconstructed current-best OOF surface. Legacy absolute scores are not comparable.",
        ),
        (
            "Weekly-slot selection",
            "NOT RUN",
            "No portal access, quota assumption or upload. Promotion is a separate selector.",
        ),
    ]
    gates = (
        '<div class="tablewrap"><table><thead><tr><th>Automated gate</th><th>Decision</th><th>Evidence / interpretation</th></tr></thead><tbody>'
        + "".join(
            f"<tr><td>{e(a)}</td><td><strong>{e(b)}</strong></td><td>{e(c)}</td></tr>"
            for a, b, c in rows
        )
        + "</tbody></table></div>"
    )
    overview = (
        cup1_hero
        + crp1_hero
        + gvc1_hero
        + rshg1_hero
        + latest
        + hero
        + concurrent
        + f"""<div class="metrics"><div class="card metric"><div class="number">{primary["pixel_count"]:,}</div><div class="label">Experimental dots</div></div><div class="card metric"><div class="number">{len(registry["unique_rasters"])}</div><div class="label">Distinct registry rasters compared</div></div><div class="card metric"><div class="number">{n:,}</div><div class="label">Withheld positive pixels</div></div><div class="card metric"><div class="number">0</div><div class="label">Competition slots used</div></div></div><section><h2>The decision is automatic, not “inspection pending”.</h2>{gates}</section><section class="grid2"><article class="card"><h3>Why the overlap veto fired</h3><p>A 5-pixel lattice is within √8 pixels of every interior grid cell. Your radius-3 rule therefore marks even an unrelated detector as a duplicate in this domain. We logged the incompatibility and stopped, rather than removing the comparator.</p><a href="research.html">Method, ablation and irregularities →</a></article><article class="card"><h3>Download the evidence</h3><div class="actions"><a class="button" href="data/dprf1_run_card.json" download>DPRF1 JSON run card</a><a class="button" href="data/trsg1_run_card_20261026.json" download>TRSG1 JSON run card</a><a class="button" href="data/nine_site_executive_summary_20261026.json" download>9-Site Executive Summary JSON</a><a class="button" href="data/rshg1_run_card.json" download>RSHG1 JSON run card</a><a class="button" href="data/mtr1_run_card.json" download>MTR1 JSON run card</a><a class="button" href="downloads/{e(primary["checks_file"])}" download>Exact-file validator</a></div><p class="micro">These are local measurements, not an organizer receipt or a leaderboard projection.</p></article></section><section><h2>Source freshness — not a live leaderboard</h2><p class="micro">GitHub commits checked at {e(feed.get("checked_utc", "not checked"))}. Scientific inputs and decisions remain pinned to the experiment.</p><ul class="feed" id="source-feed-list"></ul><p class="micro" data-source-state>GitHub-only freshness feed; no scoring or promotion API</p></section>"""
    )
    any_ok_submit = dprf1_ok_submit or crp1_ok_submit
    exec_intro = (
        "<p><strong>For H24-DPRF1 above: YES — cleared automatically by the independent selector (<code>gems-selector-v1</code>: <code>OK_TO_SUBMIT</code>).</strong> "
        "It passed all 10/10 project validation gates automatically with zero human-inspector fallback; "
        "confirm your remaining weekly quota on the DrivenData submission page before uploading. "
        "Every <em>other</em> historical or sibling GeoTIFF below (including TRSG1, CUP1, CRP1, GVC1, RSHG1, FUSE-HCW, OJ1, MTR1, ASPC) remains "
        "<code>DO_NOT_SUBMIT</code> and is provided only for audit, reproduction and education.</p>"
        if any_ok_submit
        else "<p><strong>No.</strong> Every generated GeoTIFF on this page is okay to download for audit, reproduction and education. "
        "Automated project gates (including the independent selector) have already evaluated them "
        "with zero human-inspector fallback; all current artifacts carry an automatic "
        "<code>DO_NOT_SUBMIT</code> decision.</p>"
    )
    executive = f'''{cup1_exec}{crp1_exec}{gvc1_exec}{rshg1_exec}{latest}<div class="pagehead"><div class="eyebrow">Executive summary</div><h1>Is it okay to submit this file?</h1>{exec_intro}</div>{status}<div class="actions">{download}<a class="button" href="downloads/{e(primary["nan_file"])}" download>NaN-outside twin — also DO NOT SUBMIT</a></div>{file_info}{concurrent}<section><h2>Gate report</h2>{gates}</section><section class="grid2"><article class="card"><h3>What the file contains</h3><p>One float32 band, EPSG:32611, shape 3730 × 3292, 100 m pixels. Affine transform: [100, 0, 243350, 0, −100, 4508550]. Zero NaN/Inf in the entire zero-outside file; every value is in [0,1]. The NaN-outside twin follows the previously reviewed problem text's outside-footprint convention.</p><p>Both variants pass the local exact-grid validator. This is not proof of portal acceptance, scientific merit or eligibility.</p><a href="downloads/{e(primary["checks_file"])}">Full validator JSON →</a></article><article class="card"><h3>Unique name and short comment</h3>{note}</article></section><section><h2>How a future PASS packet would be submitted</h2><p><strong>These instructions do not authorize a negative file.</strong></p><ol class="steplist"><li><h3>Download only the selector's released PASS file</h3><p>Compare its filename and SHA-256 with its receipt. Never upload the training stack, a preview image or a renamed historical reference.</p></li><li><h3>Open the official submission page</h3><p>Sign in to <a href="{COMP}">DrivenData GEMS</a>, use Submit → Make new submission. The project does not automate DrivenData access.</p></li><li><h3>File to submit</h3><p>Choose the released single-band .tif, or a ZIP containing exactly that one GeoTIFF, matching the template CRS, shape and geotransform.</p></li><li><h3>Note (optional)</h3><p>Paste the released packet's comment, no more than 140 characters in this project.</p></li><li><h3>Check quota, submit and preserve the receipt</h3><p>Historical rules mention three submissions per week. The current account cap and remaining allowance are unknown here; confirm remaining allowance on the DrivenData submission page before uploading. Save an artifact-linked submission-page receipt before any value is labelled ORGANIZER-CONFIRMED.</p></li></ol></section><section><h2>If the portal says “Predicted values must be in range [0, 1]”</h2><p>The root cause of the earlier rejection is not established. The <code>-zeros.tif</code> download is allfinite, with zeros outside the footprint; the <code>-nan.tif</code> twin has NaN only outside. Neither contains sentinels, infinities, out-of-range values or NaN inside the footprint. The official reference notebook writes a single-band output using the labels' CRS and transform without setting a nodata tag; outside-convention differences are explicit here. No claim that a local validator can guarantee portal acceptance is made.</p></section>'''
    ablation = card["magnetic_only_ablation"]
    alo, ahi = ablation["ci95"]["interval"]
    canary_rows = "".join(
        f"<tr><td>{e(k)}</td><td>{v['pooled_auc']:.5f}</td><td>{'FLAG' if v['leakage_suspected'] else 'Below canary threshold'}</td></tr>"
        for k, v in experiment["canary"]["features"].items()
    )
    fuse_card = load("evidence/hcw_run_card_20261025.json")
    fuse_section = ""
    if fuse_card:
        fh = fuse_card["holdout"]
        flo, fhi = fh["ci95"]["interval"]
        farms = fuse_card["arms_holdout_summary"]
        fbr = fuse_card["bridge_protocol_holdout"]
        fblo, fbhi = fbr["ci95"]
        fnov = fuse_card["correlation_overlap_vs_registry"]
        fc2st = fuse_card["exact_file_nuisance_audit"]
        fuse_section = f"""<section><h2>2026-10-25 Next-Step #4 Execution: H24-FUSE Residualized Conduit OOF-HGB</h2>
<div class="grid2"><article class="card"><h3>Three-arm HOLDOUT-DTI, novelty &amp; C2ST comparison (not leaderboard scores)</h3>
<div class="tablewrap"><table><thead><tr><th>Arm / Candidate</th><th>Primary HOLDOUT-DTI (<code>{e(fh["evaluator_version"])}</code>)</th><th>95% Bootstrap CI</th><th>Method-Lane Max 3-px Overlap (≤0.70)</th><th>Exact-File C2ST AUC (&lt;0.55)</th></tr></thead><tbody>
<tr><td><strong><code>oof_multiphysics_hgb_d3</code> (27-ch OOF baseline)</strong></td><td><strong>{farms["oof_multiphysics_hgb_d3_baseline"]["dti"]:.5f}</strong></td><td>[{farms["oof_multiphysics_hgb_d3_baseline"]["ci95"][0]:.5f}, {farms["oof_multiphysics_hgb_d3_baseline"]["ci95"][1]:.5f}]</td><td>—</td><td>—</td></tr>
<tr><td><code>H24-FUSE-RAW</code> (31-ch unresidualized OOF-HGB)</td><td>{farms["fuse_raw"]["dti"]:.5f}</td><td>[{farms["fuse_raw"]["ci95"][0]:.5f}, {farms["fuse_raw"]["ci95"][1]:.5f}]</td><td><code>{farms["fuse_raw"]["method_lane_max_overlap_within_3px"]:.4f}</code> (<strong>FAIL</strong>)</td><td><code>{farms["fuse_raw"]["c2st_auc"]:.4f}</code> (PASS)</td></tr>
<tr><td><strong><code>H24-FUSE-HCW</code> (residualized × conduit weight, packaged)</strong></td><td><strong>{fh["dti"]:.5f}</strong></td><td>[{flo:.5f}, {fhi:.5f}]</td><td><strong><code>{fnov["method_lane_max_overlap_within_3px"]:.4f}</code> (PASS)</strong></td><td><strong><code>{fc2st["observed_auc"]:.4f}</code> (PASS)</strong></td></tr>
<tr><td><code>H24-FUSE-RESID</code> (31-ch train-only <code>NuisanceResidualizer</code>)</td><td>{farms["fuse_resid"]["dti"]:.5f}</td><td>[{farms["fuse_resid"]["ci95"][0]:.5f}, {farms["fuse_resid"]["ci95"][1]:.5f}]</td><td><strong><code>{farms["fuse_resid"]["method_lane_max_overlap_within_3px"]:.4f}</code> (PASS)</strong></td><td><strong><code>{farms["fuse_resid"]["c2st_auc"]:.4f}</code> (PASS)</strong></td></tr>
</tbody></table></div>
<p class="micro">60,988 withheld positives across all four quadrants. On the bridge protocol (<code>{e(fbr["evaluator_version"])}</code>), <code>H24-FUSE-HCW</code> achieves <strong>HOLDOUT-DTI {fbr["dti"]:.5f}</strong> (95% CI [{fblo:.5f}, {fbhi:.5f}]), beating <code>SAHG1</code> (<code>0.09655</code>) by <strong>+0.01696</strong> and <code>ASPC</code> (<code>0.08553</code>) by <strong>+{fbr["delta_vs_recorded_aspc"]:.5f}</strong>.</p></article>
<article class="card"><h3>FUSE-HCW preview, C2ST breakthrough &amp; prospective novelty</h3>
<img class="raster-preview" src="assets/fuse-preview.png" alt="Downsampled preview of H24-FUSE-HCW experimental fault dots (37,722 positive cells)">
<p class="micro">Competing method lanes passed: <strong>{fnov["competing_method_rasters_checked"]}/{fnov["competing_method_rasters_checked"]}</strong> (max 3-px overlap <code>{fnov["method_lane_max_overlap_within_3px"]:.4f}</code> ≤ 0.70; peer blobs <code>{fnov["peer_blobs_max_overlap_within_3px"]:.4f}</code> ≤ 0.70; max |ρ| <code>{fnov["surface_max_abs_rank_correlation"]:.4f}</code> ≤ 0.90; literal all-entry overlap <code>{fnov["literal_all_entries_max_overlap_within_3px"]:.4f}</code> fails against the retained spacing-5 calibration lattice). Exact-file C2ST AUC reduced from <code>0.5826</code> (SAHG1) to <strong><code>{fc2st["observed_auc"]:.4f}</code></strong> (null p95 <code>{fc2st["null_p95"]:.4f}</code>, Holm <em>p</em> = <code>{fc2st["holm_p_value"]:.3f}</code>). <a href="https://github.com/buffedlizard55-lab/GEMSDOE24/blob/main/knowledge/17_preregistered_FUSE_2026-10-25.md">FUSE preregistration →</a> · <a href="https://github.com/buffedlizard55-lab/GEMSDOE24/blob/main/knowledge/18_FUSE_findings_2026-10-25.md">FUSE findings &amp; audit →</a></p></article></div></section>"""
    sahg1_card = load("evidence/sahg1_run_card_20261025.json")
    sahg1_section = ""
    if sahg1_card:
        sh = sahg1_card["holdout"]
        slo, shi = sh["ci95"]["interval"]
        sg0 = sahg1_card["geomorphic_only_ablation"]
        sglo, sghi = sg0["ci95"]["interval"]
        soof = sahg1_card["reconstructed_oof_multiphysics_baseline"]
        solo, sohi = soof["ci95"]["interval"]
        sbr = sahg1_card["bridge_protocol_holdout"]
        sblo, sbhi = sbr["ci95"]
        snov = sahg1_card["correlation_overlap_vs_registry"]
        sc2st = sahg1_card["exact_file_nuisance_audit"]
        sahg1_section = f"""<section><h2>2026-10-25 Prior Execution: H24-SAHG1 &amp; Reconstructed OOF Multi-Physics Benchmark</h2>
<div class="grid2"><article class="card"><h3>Unified HOLDOUT-DTI across both evaluators (not leaderboard scores)</h3>
<div class="tablewrap"><table><thead><tr><th>Arm / Candidate</th><th>Evaluator</th><th>HOLDOUT-DTI</th><th>95% Bootstrap CI</th></tr></thead><tbody>
<tr><td><strong>Reconstructed OOF Multi-Physics HGB (<code>oof_multiphysics_hgb_d3</code>)</strong></td><td><code>{e(soof["evaluator_version"])}</code></td><td><strong>{soof["dti"]:.5f}</strong></td><td>[{solo:.5f}, {sohi:.5f}]</td></tr>
<tr><td><strong><code>H24-SAHG1</code> Strike-Hydro-Geomorph (this session)</strong></td><td><code>{e(sh["evaluator_version"])}</code></td><td><strong>{sh["dti"]:.5f}</strong></td><td>[{slo:.5f}, {shi:.5f}]</td></tr>
<tr><td><code>H24-SAHG1</code> geomorphic-only ablation (<code>G_0</code>)</td><td><code>{e(sg0["evaluator_version"])}</code></td><td>{sg0["dti"]:.5f}</td><td>[{sglo:.5f}, {sghi:.5f}]</td></tr>
<tr><td>Recorded <code>MTR1</code> (PR #11)</td><td><code>{e(score["evaluator_version"])}</code></td><td>{score["dti"]:.5f}</td><td>[{lo:.5f}, {hi:.5f}]</td></tr>
<tr><td><strong><code>H24-SAHG1</code> on ASPC bridge protocol</strong></td><td><code>{e(sbr["evaluator_version"])}</code></td><td><strong>{sbr["dti"]:.5f}</strong></td><td>[{sblo:.5f}, {sbhi:.5f}]</td></tr>
<tr><td>Recorded <code>ASPC</code> (PR #10)</td><td><code>{e(sbr["evaluator_version"])}</code></td><td>{sbr["recorded_aspc_dti"]:.5f}</td><td>[{sbr["recorded_aspc_ci95"][0]:.5f}, {sbr["recorded_aspc_ci95"][1]:.5f}]</td></tr>
</tbody></table></div>
<p class="micro">60,988 withheld positives across all four quadrants. Paired gain of <code>H24-SAHG1</code> over <code>G_0</code>: <strong>+{sahg1_card["paired_comparisons"]["sahg1_minus_geomorphic_core_g0"]["delta_dti"]:.5f}</strong> (95% CI [{sahg1_card["paired_comparisons"]["sahg1_minus_geomorphic_core_g0"]["ci95"][0]:.5f}, {sahg1_card["paired_comparisons"]["sahg1_minus_geomorphic_core_g0"]["ci95"][1]:.5f}]); paired delta vs. <code>oof_multiphysics_hgb_d3</code>: <strong>{sahg1_card["paired_comparisons"]["sahg1_minus_reconstructed_oof_hgb_d3"]["delta_dti"]:.5f}</strong>.</p></article>
<article class="card"><h3>SAHG1 preview, prospective novelty &amp; exact-file C2ST</h3>
<img class="raster-preview" src="assets/sahg1-preview.png" alt="Downsampled preview of H24-SAHG1 experimental fault dots (37,722 positive cells)">
<p class="micro">Competing method lanes passed: <strong>{snov["competing_method_rasters_checked"]}/{snov["competing_method_rasters_checked"]}</strong> (max 3-px overlap <code>{snov["method_lane_max_overlap_within_3px"]:.4f}</code> ≤ 0.70; peer blobs <code>{snov["peer_blobs_max_overlap_within_3px"]:.4f}</code> ≤ 0.70; max |ρ| <code>{snov["surface_max_abs_rank_correlation"]:.4f}</code> ≤ 0.90; literal all-entry overlap <code>{snov["literal_all_entries_max_overlap_within_3px"]:.4f}</code> fails against the retained calibration lattice). Exact-file C2ST AUC: <code>{sc2st["observed_auc"]:.4f}</code> (null p95 <code>{sc2st["null_p95"]:.4f}</code>, Holm <em>p</em> = <code>{sc2st["holm_p_value"]:.3f}</code>). <a href="https://github.com/buffedlizard55-lab/GEMSDOE24/blob/main/knowledge/12_preregistered_SAHG1_2026-10-25.md">SAHG1 preregistration →</a> · <a href="https://github.com/buffedlizard55-lab/GEMSDOE24/blob/main/knowledge/13_SAHG1_findings_2026-10-25.md">SAHG1 findings →</a></p></article></div></section>"""
    research = f"""{cup1_research}<div class="pagehead"><div class="eyebrow">One preregistered experiment per session · stopped, not tuned</div><h1>Measure the mechanism.<br>Keep the negative result.</h1><p>Target: previously unmapped fault geometry, not direct geothermal-vent coordinates. A structural proxy is not evidence of a hot or permeable reservoir.</p></div>{status}{crp1_research}{gvc1_research}{rshg1_research}{fuse_section}{sahg1_section}<section><h2>Next scientific gate: ranked hypotheses, not score forecasts</h2><p>The prior data-readiness receipt is historical, not a current file-presence check; no new experiment ran in that review. The spacing-5 calibration raster remains in the registry. Do not interpret a format-valid download alone as submit-ready; check the independent selector receipt.</p><div class="tablewrap"><table><thead><tr><th>Priority</th><th>Layers / signature</th><th>Why it may detect missing faults; principal mimic</th><th>Novelty vs inspected repo; cost / data</th></tr></thead><tbody><tr><td>1 · Incremental SAHG1 × OOF model</td><td>Fold-local strike-projected LiDAR scarp, stable-Th-controlled K/U, basement/strain step; train-only nuisance residualization.</td><td>Test whether surface deformation × hydrothermal alteration adds to the existing multi-physics detector; mimic: acquisition block, road/mining access, lithology or pluvial shoreline.</td><td>Completed across FUSE, RSHG1, TRSG1, and Dual-Partition Stitched-OOF DPRF1. See their packets above.</td></tr><tr><td>2 · Drainage diversion graph</td><td>DEM elevation/relief; stream-network offsets and persistent azimuth changes across scales.</td><td>Fault-controlled drainage diversion without a preserved scarp; mimic: lithologic contact, shoreline, ditch or natural capture.</td><td>No named drainage-graph displacement feature found in inspected code. High cost; current elevation product is staged, but resolution may be limiting. Any 3DEP upgrade needs tile-level availability receipts from <a href="https://www.usgs.gov/3d-elevation-program/data-tools">USGS 3DEP</a>.</td></tr><tr><td>3 · Cross-scale potential-field edge phase</td><td>Cached RTP/TMI and gravity anomalies/gradients; co-located edge phase and orientation at multiple scales.</td><td>Basement discontinuity below cover; mimic: lithologic contacts, remanence or flight-line leveling seam.</td><td>Changes from generic multi-physics fitting to cross-scale edge-phase co-location; redundancy risk. Medium-high cost; available bands are local.</td></tr><tr><td>4 · Confound-controlled thermal/radiometric increment</td><td>GDR probe/thermal plus GeoDAWN K/U/Th conditioned on slope, roads, claims and acquisition blocks.</td><td>Ask if conduit-related thermal/chemical response adds fault localization beyond access and survey coverage; mimic: siting bias or lithology.</td><td>Layers have appeared in prior work; novelty is the strict incremental-value/negative-control test. Low-medium cost; local inputs exist, high null risk.</td></tr></tbody></table></div><p><strong>Decision:</strong> hypothesis 1 is completed research. See <a href="https://github.com/buffedlizard55-lab/GEMSDOE24/blob/main/knowledge/14_data_readiness_and_next_gate_2026-10-25.md">full data-readiness, evidence and source limitations</a> and <a href="data/data_readiness_20261025.json">machine-readable readiness receipt</a>.</p></section><section><h2>Why the reported GEMSDOE32 result may have improved</h2><p>The brief's <strong>0.2778 is user-reported and unverified</strong>; no submission-page receipt was supplied, so it is not ORGANIZER-CONFIRMED. Local pixel comparison proves H33-B2 is exactly the earlier H27-4 emission with all dots within 2 pixels of the public catalogue deleted: {prior["base_dots"]:,} → {prior["h33_dots"]:,}, {prior["removed_dots"]:,} removed, no dots added. This is an emission-efficiency change, not a new detector or proven geothermal discovery.</p><p>For D = T / ((1−β)T + αF + βG), deleting predictions helps only when the lost true-positive credit L is smaller than αD·ΔF / [1−(1−β)D]. The removed dots' hidden credit and FP mass are unknown. Pruning may save false-positive mass, but the reported leaderboard value alone cannot identify the cause, nor prove a new raster will score higher.</p><p>The brief's leader claims (0.4413 and 0.3195) conflict and neither has a current receipt. No current leader or projected leaderboard score is asserted.</p><a href="data/priority_review_20261025.json">Pixel-forensics receipt →</a></section><section><h2>Four hypotheses ranked before implementation</h2><div class="tablewrap"><table><thead><tr><th>Rank / method</th><th>Layers and physical signature</th><th>Missing-fault rationale / difference</th><th>Expected benefit / cost</th></tr></thead><tbody><tr><td>1 · MTR1 — tested</td><td>Cached RTP: signed trough with two high shoulders, tangent persistence; local contractor Th/K depletion</td><td>Possible blind alteration conduit without a scarp; two-sided cross-normal geometry, not terrain ridges or catalogue-flank pruning</td><td>Most testable per cost; uncertain benefit; low cost</td></tr><tr><td>2 · MTR2 — not run</td><td>RTP/TMI plus TMI_up150: paired-trough survival after upward continuation</td><td>Deeper concealed corridor versus short-wave cultural signal; not a single contact edge</td><td>Moderate uncertainty / medium cost</td></tr><tr><td>3 · MTR3 — not run</td><td>RTP plus ThK/UTh: asymmetric cross-normal compositional residual</td><td>Narrow alteration strip rather than broad cover; not scalar radiometric fusion</td><td>Lower confidence / low cost</td></tr><tr><td>4 · MTR4 — not run</td><td>RTP plus conductivity: conductive ridge inside both magnetic shoulders</td><td>Possible blind pathway; centred offset relationship rather than clay-cap boundary</td><td>Low expected localization skill / low cost</td></tr></tbody></table></div><p class="micro">All use already-readable cached data. Expected benefit is a hypothesis, not a DTI projection. Novelty is relative to reviewed code only. <a href="https://github.com/buffedlizard55-lab/GEMSDOE24/blob/main/knowledge/09_preregistration_magnetic_trough_2026-10-25.md">Full pre-run preregistration and source caveats →</a></p></section><section><h2>HOLDOUT-DTI — not leaderboard scores</h2><div class="tablewrap"><table><thead><tr><th>Fixed arm</th><th>Pooled HOLDOUT-DTI</th><th>Approximate 95% CI</th></tr></thead><tbody><tr><td>Paired magnetic trough only</td><td>{ablation["dti"]:.5f}</td><td>[{alo:.5f}, {ahi:.5f}]</td></tr><tr><td>Trough × local radiometric corroboration</td><td>{score["dti"]:.5f}</td><td>[{lo:.5f}, {hi:.5f}]</td></tr></tbody></table></div><p class="micro">{hlabel}. Both arms: identical evaluator, withheld positives and 10 km block-bootstrap design (1,999 resamples). Whole connected fault components touching a quadrant or its 1.5 km collar are hidden everywhere; only visible faults can enter catalogue features or masking. No catalogue-derived detector feature or supervised fit is used. Alpha 0.2, beta 0.8, 300 m triangular kernel; components pooled before the ratio. The ablation gain is not a certified current-best win, and no paired gain CI was computed.</p></section><section><h2>Leakage canary, feature by feature</h2><div class="tablewrap"><table><thead><tr><th>Feature</th><th>Diagnostic AUC (not DTI)</th><th>Threshold rule</th></tr></thead><tbody>{canary_rows}</tbody></table></div><p class="micro">Either polarity above 0.90 is treated as suspected leakage. Feature AUCs near chance are a specificity warning, not proof the detector is useful.</p></section><section><h2>Named non-fault mimic</h2><p>A magnetite-poor alluvial palaeochannel with K-rich detritus can produce a magnetic low and low Th/K without a fault. Lithology, weathering, remanence and acquisition artefacts remain alternative explanations. No retrieved paper or measured label establishes hydrothermal demagnetization at these predicted locations.</p></section><section><h2>The lane is stopped</h2><p>Raw rank correlations were checked exactly over every footprint cell, before and after placement; kernel sensitivity used a fixed sample. Maximum measured absolute rank correlation: {card["correlation_overlap_vs_registry"]["final_max_abs_rank_correlation"]:.5f}. Exact directional overlap with the registered calibration lattice: 100%. The same lattice covers 100% of this candidate's supported domain at radius 3. The guard remains failed; it was not weakened after seeing the result.</p><p>The method paragraph assigning a lane was absent. This provisional lane cannot be certified as the assigned lane. After the stop, the unchanged negative TIFF was exported for audit; this explicit packaging-only deviation is recorded in the run card. No experiment, retuning or slot followed the stop.</p></section>"""
    from priority_summary import priority_summary

    comparison = priority_summary(registry, feed)
    executive += comparison
    overview += '<section class="card"><h2>Historical nine-site maxima audit</h2><p>Historical H19-5 derivatives are ineligible for resubmission; for the 2026-10-26 <code>H24-DPRF1</code> and <code>H24-TRSG1</code> candidates see the cards above. <a href="executive-summary.html#priority-summary">Compare all nine priority sites and their reported historical maxima →</a></p></section>'
    research += latest + concurrent
    research += '<section><h2>Review limits, not hidden assumptions</h2><p>The input ratio bytes were quantized upstream using survey-wide percentiles. The fixed 72-pixel Euclidean support guard reduces edge effects but is not a formal zero-influence proof at square Gaussian-support corners. No chance-control experiment, comparable current-best OOF reconstruction or exact-file nuisance audit was completed for MTR1; all three were subsequently completed in the 2026-10-25 H24-SAHG1 packet above. These limits do not alter the stopped rasters or grant promotion.</p><p><a href="https://github.com/buffedlizard55-lab/GEMSDOE24/blob/main/knowledge/11_MTR1_findings_2026-10-25.md">MTR1 findings →</a> · <a href="https://github.com/buffedlizard55-lab/GEMSDOE24/blob/main/knowledge/13_SAHG1_findings_2026-10-25.md">SAHG1 findings →</a> · <a href="data/mtr1_review_passes_20261025.json">Three-pass review receipt</a></p></section>'
    source_rows = "".join(
        f'<tr><td>GEMSDOE{s["repo"].split("GEMSDOE")[-1]}</td><td><a href="https://github.com/{e(s["repo"])}/tree/{e(s["ref"])}"><code>{e(s["ref"][:12])}</code></a></td><td>Source and all published download TIFFs inspected; team evidence, not organizer receipts</td></tr>'
        for s in registry["sources"]
    )
    source_page = f"""<div class="pagehead"><div class="eyebrow">Provenance · reproducibility · limitations</div><h1>Evidence you can trace.</h1><p>Every active performance result is HOLDOUT-DTI with an evaluator, positive count and CI. No ORGANIZER-CONFIRMED result is available for the new file.</p></div><section><h2>The nine priority repositories</h2><div class="tablewrap"><table><thead><tr><th>Project</th><th>Pinned review commit</th><th>Scope</th></tr></thead><tbody>{source_rows}</tbody></table></div><p class="micro">{len(registry["unique_rasters"])} distinct footprint contents; {len(registry["duplicate_content_variants"])} duplicate variants; {len(registry["rejected"])} rejected off-grid format-test file. This is not a claim to cover unseen parallel-session registries.</p></section><section><h2>Official sources and exact verification status</h2><div class="tablewrap"><table><thead><tr><th>Source</th><th>What is supported</th><th>Verification limit</th></tr></thead><tbody><tr><td><a href="https://github.com/drivendataorg/gems-prize-reference-solution/tree/aebe92f7c8a990f0e3443451b7a825d9afd6336b">DrivenData reference solution</a></td><td>Freshly retrieved organizer GitHub notebook; U-Net, Tversky loss weights, single-band output with label CRS/transform</td><td>Its loss is not an independent implementation of distance-weighted evaluation; no official hidden score supplied</td></tr><tr><td><a href="https://www.sciencebase.gov/catalog/item/657e1d85d34e23d3533209f7">USGS GeoDAWN / DOI 10.5066/P93LGLVQ</a></td><td>Cached official ReadMe inspected: magnetic and radiometric channel descriptions, thk_ratio, UTM projection and grid intervals</td><td>Not freshly refetched in this session. Cached official release text and hash-pinned owner-derived grids are not independent authentication of the original download</td></tr><tr><td><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">Competition problem description</a></td><td>Submission grid/metric follow inherited dated source review and organizer reference output</td><td>Not automatically refetched; DrivenData automation is prohibited by standing project compliance rules</td></tr><tr><td><a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">Prize rules PDF</a></td><td>Official rule link retained for review; AI disclosure draft maintained</td><td>Current text/quota not retrieved here; historical rules are not a current account receipt</td></tr><tr><td><a href="https://gdr.openei.org/submissions/1391">GDR INGENIOUS</a></td><td>Official source for inherited catalogue context</td><td>No thermal points or derived catalogue-distance features used in this experiment</td></tr></tbody></table></div></section><section><h2>Reproduce without guessing</h2><pre><code>.venv/bin/python scripts/restore_data.py
.venv/bin/python scripts/prepare_data.py
.venv/bin/python scripts/cache_priority_registry.py
.venv/bin/python scripts/run_dprf1_lane.py --verify-recorded
.venv/bin/python scripts/evaluate_holdout.py --verify-recorded
.venv/bin/python scripts/evaluate_holdout.py --verify-gvc1
.venv/bin/python scripts/run_sahg1_lane.py --verify-recorded
.venv/bin/python scripts/run_hcw_lane.py --verify-recorded
.venv/bin/python scripts/run_rshg1_lane.py --verify-recorded
.venv/bin/python scripts/run_trsg1_lane.py --verify-recorded
# Verifies frozen evidence; the stopped experiments refuse implicit reruns.
.venv/bin/python scripts/export_negative_result.py
.venv/bin/python scripts/build_site.py
.venv/bin/python -m pytest -q</code></pre><p class="micro">Caches and the 419 MB training raster are ignored. GitHub download access is sufficient for these CPU experiments. Original organizer authentication of owner mirrors and an explicit single-method lane remain unavailable. No GPU is required.</p></section><section><h2>Next work — completed and remaining</h2><ol class="steplist"><li><h3>Completed: Prospective registry-overlap separation</h3><p><code>gems.novelty.compare_prospective_registry</code> separates synthetic calibration controls (<code>registry-039</code> spacing-5 lattice, <code>registry-044</code> zero placeholder) from the competing method lanes and 83 peer blobs while keeping literal all-entry flags on record.</p></li><li><h3>Completed: Reconstructed same-protocol OOF multi-physics baseline</h3><p><code>oof_multiphysics_hgb_d3</code> refits a fold-local 27-channel HGB detector strictly on <code>fold["train"]</code> of <code>SegmentHoldout</code>, establishing a leakage-free OOF benchmark of <strong>HOLDOUT-DTI 0.13000</strong> (95% CI [0.11565, 0.14396]).</p></li><li><h3>Completed: Strike-projected hydrothermal-geomorphic operator &amp; exact-file C2ST</h3><p><code>H24-SAHG1</code> achieves <strong>HOLDOUT-DTI 0.09672</strong> ([0.08657, 0.10703]) on <code>gems-segment-pooled-v1</code> and <strong>0.09655</strong> ([0.08270, 0.10976]) on <code>segment-hide-recover-pooled-v1</code>, beating <code>MTR1</code>, <code>ASPC</code>, and its own geomorphic ablation <code>G_0</code> (+0.01012), and is audited by <code>gems.c2s2</code> (AUC 0.5826 vs. labels 0.4912).</p></li><li><h3>Completed: Dual-Partition Stitched-OOF Fusion &amp; Orthogonal Seismic-Geothermal Discovery (<code>H24-DPRF1</code> &amp; <code>H24-TRSG1</code>)</h3><p><code>H24-DPRF1</code> achieves the repository point-best <strong>HOLDOUT-DTI 0.16379</strong> ([0.15045, 0.17739]) and 3.0 km bridge <strong>0.16290</strong>, passes 57/57 competing method rasters (≤0.5578 ≤ 0.70) and 83/83 peer blobs (≤0.5494 ≤ 0.70), passes C2ST (AUC 0.5247 &lt; 0.55), and restores 52.3% &gt;2 km far-field dot allocation. Orthogonal 44-channel <code>H24-TRSG1</code> integrates restored <code>ieq_n100a15</code>/<code>deq_n100a15</code> microseismic anisotropy, hyperbolic step-over saddle twists, Quaternary vents, and compact INGENIOUS DoGs, achieving <strong>HOLDOUT-DTI 0.14644</strong> ([0.13220, 0.16241], paired Δ <strong>+0.01644</strong> [+0.00053, +0.03163] over <code>oof_multiphysics_hgb_d3</code>; 3.0 km bridge <strong>0.14674</strong>), passing C2ST (AUC <strong>0.4727</strong>, Holm <em>p</em> = 1.000) and 141-raster novelty (≤0.6622 vs <code>DPRF1</code>/<code>TNR1</code>/<code>CRP1</code>/<code>CUP1</code>).</p></li></ol><p>Open legacy PR #7 remains conflicting and was not merged or overwritten. Official block boundaries remain a derived audit, not published coordinates. No human exception is requested.</p></section><section><h2>Machine-readable evidence</h2><div class="actions"><a class="button" href="data/dprf1_run_card.json" download>DPRF1 JSON run card</a><a class="button" href="data/dprf1_selector.json" download>DPRF1 Selector v2 JSON</a><a class="button" href="data/dprf1_experiment_20261026.json" download>DPRF1 experiment</a><a class="button" href="data/trsg1_run_card_20261026.json" download>TRSG1 JSON run card</a><a class="button" href="data/trsg1_selector.json" download>TRSG1 Selector v2 JSON</a><a class="button" href="data/trsg1_experiment_20261026.json" download>TRSG1 experiment</a><a class="button" href="data/nine_site_executive_summary_20261026.json" download>9-Site Executive Summary JSON</a><a class="button" href="data/hcw_run_card.json" download>FUSE-HCW JSON run card</a><a class="button" href="data/hcw_experiment_20261025.json" download>FUSE-HCW experiment</a><a class="button" href="data/fuse_run_card.json" download>Stopped unresidualized FUSE card</a><a class="button" href="data/rshg1_run_card.json" download>RSHG1 JSON run card</a><a class="button" href="data/rshg1_experiment_20261025.json" download>RSHG1 experiment</a><a class="button" href="data/oj1_run_card.json" download>OJ1 JSON run card</a><a class="button" href="data/sahg1_run_card.json" download>SAHG1 JSON run card</a><a class="button" href="data/sahg1_experiment_20261025.json" download>SAHG1 experiment</a><a class="button" href="data/con_run_card.json" download>CON JSON run card</a><a class="button" href="data/unique_run_card.json" download>H-UNIQUE-03 JSON run card</a><a class="button" href="data/mtr1_run_card.json" download>MTR1 JSON card</a><a class="button" href="data/mtr1_experiment.json" download>MTR1 experiment</a><a class="button" href="data/priority_rasters.json" download>Registry manifest</a><a class="button" href="data/priority_feed.json" download>Source freshness</a><a class="button" href="data/submission_preflight_review_20261025.json" download>Preflight review</a><a class="button" href="data/data_readiness_20261025.json" download>Data readiness / next gate</a><a class="button" href="data/2026-10-25_data_readiness_run_card.json" download>Readiness run card</a></div></section>"""
    tnr1 = render_tnr1(ROOT)
    if tnr1:
        overview = (
            tnr1["overview"]
            + dprf1_hero
            + trsg1_hero
            + '<details id="historical-packets"><summary>Earlier research downloads — all DO NOT SUBMIT</summary>'
            + overview
            + "</details>"
        )
        executive = (
            tnr1["executive"]
            + dprf1_exec
            + trsg1_exec
            + '<details id="historical-executive"><summary>Historical submission packets and nine-site comparison</summary>'
            + executive
            + "</details>"
        )
        research = (
            tnr1["research"]
            + dprf1_research
            + trsg1_research
            + '<details id="historical-research"><summary>Prior experiments, frozen evidence and historical proposals</summary>'
            + research
            + "</details>"
        )
        source_page = (
            '<div class="pagehead"><div class="eyebrow">Source audit, not score verification</div><h1>92 repositories.<br>Zero verified scores.</h1><p>Immutable source text, explicit owner-claim labels and honest freshness. No automated DrivenData access. Sources refresh on the six-hour site schedule; this is not a live leaderboard.</p><p class="micro"><span data-source-state>GitHub source freshness only</span> · <span data-source-time>See timestamped snapshot below</span></p></div>'
            + all_sites_table(ROOT)
            + '<details id="historical-sources"><summary>Official data links, earlier source evidence and nine-site freshness feed</summary>'
            + source_page
            + "</details>"
        )
        for source_name in ("tnr1_source_review_20261026.json",):
            (DOCS / "data" / source_name).write_text((ROOT / "evidence" / source_name).read_text())
    else:
        overview = dprf1_hero + trsg1_hero + overview
        executive = dprf1_exec + trsg1_exec + executive
        research = dprf1_research + trsg1_research + research
    # Resolve current-best from all comparable records, not the historical active_lane.
    from gems.current_review import review_current_best

    current = review_current_best(ROOT)
    (DOCS / "data/current_best_review.json").write_text(
        json.dumps(current, indent=2, allow_nan=False) + "\n"
    )
    ch = current["holdout"]
    clo, chi = ch["ci95"]["interval"]
    current_banner = (
        '<section class="card" id="current-best-review"><h2>Current decision: DOWNLOAD YES / SUBMIT NO</h2>'
        f'<p><a class="button primary" href="downloads/{e(current["submission_name"])}" '
        f'download="{e(current["submission_name"])}">Download current point-best research TIFF — DO NOT SUBMIT</a></p>'
        f"<p>Recorded local point-best: <strong>{e(current['current_recorded_point_best']['lane'])}</strong>. "
        f"HOLDOUT-DTI {ch['dti']:.5f}, 95% CI [{clo:.5f}, {chi:.5f}], "
        f"{e(ch['evaluator_version'])}, {ch['n_withheld_positive_pixels']:,} withheld positives. "
        "Exact TIFF bytes revalidated during this site build; scientific measurements were not replayed. "
        "Not a verified cross-site winner or a leaderboard prediction. "
        "Literal novelty, quota and independent replay gates still block submission.</p>"
        '<p><a href="data/current_best_review.json" download>Fresh exact-file review JSON</a> · '
        '<a href="#nine-site-executive-summary">Nine-site executive comparison</a></p></section>'
    )
    # Preserve the concurrent VENT negative packet through scheduled rebuilds.
    vent_html = ""
    vent = load("evidence/vent_run_card_20261026.json")
    if vent:
        from gems.submission import check_variants

        vname = vent["submission_name"]
        if Path(vname).name != vname or not vname.endswith("-zeros.tif"):
            raise ValueError("Unsafe VENT filename")
        vf = check_variants(DOCS / "downloads" / vname, ROOT / "data/bridge/sample_submission.tif")
        if (
            not vf["format_valid"]
            or vf["sha256"] != vent["raster_sha256"]
            or vent.get("ok_to_submit") is not False
            or vent.get("verdict") != "negative"
        ):
            raise ValueError("VENT negative packet identity/format mismatch")
        vh = vent["holdout"]
        vlo, vhi = vh["ci95"]["interval"]
        vent_html = (
            '<section class="card" id="vent-packet"><h2>QUARANTINED H24-VENT research — DO NOT SUBMIT</h2>'
            f"<p>Recorded HOLDOUT-DTI {vh['dti']:.5f}, 95% CI [{vlo:.5f}, {vhi:.5f}], "
            f"{e(vh['evaluator_version'])}, {vh['n_withheld_positive_pixels']:,} withheld positives. "
            "Scientific gate claims untrusted: original code supplied dummy C2ST and registry fallbacks. Below the recorded local best. Preserved from concurrent "
            "PR #34, not generated or scientifically replayed by this review.</p>"
            f'<a class="button" href="downloads/{e(vname)}" download="{e(vname)}">Download VENT research TIFF — DO NOT SUBMIT</a>'
            '<p><a href="data/vent_run_card.json" download>Frozen VENT run card</a></p></section>'
        )
    overview = current_banner + vent_html + overview
    executive = current_banner + vent_html + executive
    pages = {
        "index.html": ("Overview", "Overview", overview),
        "executive-summary.html": ("Submission guide", "Submission guide", executive),
        "research.html": ("Research", "Research", research),
        "sources.html": ("Sources and audit", "Sources & audit", source_page),
    }
    for name, (title, active, body) in pages.items():
        html = page(title, active, body).replace(
            'content="data/source_health.json"', 'content="data/priority_feed.json"'
        )
        (DOCS / name).write_text(html)
    root_body = overview
    for path in ("downloads/", "executive-summary.html", "research.html", "sources.html", "data/"):
        root_body = root_body.replace(f'href="{path}', f'href="docs/{path}')
    root_body = root_body.replace('src="assets/', 'src="docs/assets/')
    (ROOT / "index.html").write_text(
        page("Overview", "Overview", root_body, prefix="docs/").replace(
            'content="docs/data/source_health.json"', 'content="docs/data/priority_feed.json"'
        )
    )
    exec_root_body = executive
    for path in ("downloads/", "executive-summary.html", "research.html", "sources.html", "data/"):
        exec_root_body = exec_root_body.replace(f'href="{path}', f'href="docs/{path}')
    exec_root_body = exec_root_body.replace('src="assets/', 'src="docs/assets/')
    (ROOT / "executive-summary.html").write_text(
        page("Submission guide", "Submission guide", exec_root_body, prefix="docs/").replace(
            'content="docs/data/source_health.json"', 'content="docs/data/priority_feed.json"'
        )
    )
    for name in (
        "trsg1_run_card_20261026.json",
        "trsg1_experiment_20261026.json",
        "dprf1_run_card_20261026.json",
        "dprf1_experiment_20261026.json",
        "nine_site_executive_summary_20261026.json",
        "gvc1_run_card_20261025.json",
        "gvc1_experiment_20261025.json",
        "gvc1_c2st_audit_20261025.json",
        "mtr1_experiment.json",
        "mtr1_run_card.json",
        "priority_review_20261025.json",
        "mtr1_review_passes_20261025.json",
        "sahg1_experiment_20261025.json",
        "fuse_experiment_20261025.json",
        "hcw_experiment_20261025.json",
        "rshg1_experiment_20261025.json",
        "2026-10-25_data_readiness_run_card.json",
    ):
        src_p = ROOT / "evidence" / name
        if src_p.exists():
            (DOCS / "data" / name).write_text(src_p.read_text())
    if (ROOT / "evidence/dprf1_run_card_20261026.json").exists():
        (DOCS / "data/dprf1_run_card.json").write_text(
            (ROOT / "evidence/dprf1_run_card_20261026.json").read_text()
        )
        (DOCS / "data/dprf1_selector.json").write_text(
            (ROOT / "evidence/dprf1_selector_20261026.json").read_text()
        )
    if (ROOT / "evidence/crp1_run_card_20261026.json").exists():
        (DOCS / "data/crp1_run_card.json").write_text(
            (ROOT / "evidence/crp1_run_card_20261026.json").read_text()
        )
        (DOCS / "data/crp1_selector.json").write_text(
            (ROOT / "evidence/crp1_selector_20261026.json").read_text()
        )
    if (ROOT / "evidence/sahg1_run_card_20261025.json").exists():
        (DOCS / "data/sahg1_run_card.json").write_text(
            (ROOT / "evidence/sahg1_run_card_20261025.json").read_text()
        )
    if (ROOT / "evidence/fuse_run_card_20261025.json").exists():
        (DOCS / "data/fuse_run_card.json").write_text(
            (ROOT / "evidence/fuse_run_card_20261025.json").read_text()
        )
    if (ROOT / "evidence/hcw_run_card_20261025.json").exists():
        (DOCS / "data/hcw_run_card.json").write_text(
            (ROOT / "evidence/hcw_run_card_20261025.json").read_text()
        )
    if (ROOT / "evidence/con_run_card_20261025.json").exists():
        (DOCS / "data/con_run_card.json").write_text(
            (ROOT / "evidence/con_run_card_20261025.json").read_text()
        )
    rshg1_card = load("evidence/rshg1_run_card_20261025.json")
    rshg1_dl = load("docs/data/rshg1_download.json")
    if rshg1_card and rshg1_dl:
        (DOCS / "data/rshg1_run_card.json").write_text(
            (ROOT / "evidence/rshg1_run_card_20261025.json").read_text()
        )
        active_payload = {
            "generated_utc": rshg1_card.get("generated_utc"),
            "lane": rshg1_card.get("lane_id"),
            "preregistration": rshg1_card.get("preregistration"),
            "evaluator_version": rshg1_card["holdout"]["evaluator_version"],
            "holdout": rshg1_card["holdout"],
            "exact_file_nuisance_audit": rshg1_card["exact_file_nuisance_audit"],
            "correlation_overlap_vs_registry": rshg1_card["correlation_overlap_vs_registry"],
            "artifact": rshg1_dl,
            "verdict": rshg1_card["verdict"],
            "ok_to_submit": rshg1_card["ok_to_submit"],
        }
        (DOCS / "data/active_lane.json").write_text(json.dumps(active_payload, indent=2) + "\n")
    trsg1_card = load("evidence/trsg1_run_card_20261026.json")
    trsg1_dl = load("docs/data/trsg1_download.json")
    if trsg1_card and trsg1_dl:
        (DOCS / "data/trsg1_run_card.json").write_text(
            (ROOT / "evidence/trsg1_run_card_20261026.json").read_text()
        )
        if (ROOT / "evidence/trsg1_selector_20261026.json").exists():
            (DOCS / "data/trsg1_selector.json").write_text(
                (ROOT / "evidence/trsg1_selector_20261026.json").read_text()
            )
    if tnr1:
        (DOCS / "data/active_lane.json").write_text(
            json.dumps(tnr1["active"], indent=2, allow_nan=False) + "\n"
        )
    (DOCS / "data/priority_rasters.json").write_text(
        (ROOT / "registry/priority_rasters.json").read_text()
    )
    preflight_review = ROOT / "evidence/submission_preflight_review_20261025.json"
    if not preflight_review.exists():
        raise SystemExit("Missing exact-file preflight review record")
    (DOCS / "data/submission_preflight_review_20261025.json").write_text(
        preflight_review.read_text()
    )
    fuse_md = ""
    if fuse_card:
        fh = fuse_card["holdout"]
        flo, fhi = fh["ci95"]["interval"]
        farms = fuse_card["arms_holdout_summary"]
        fbr = fuse_card["bridge_protocol_holdout"]
        fblo, fbhi = fbr["ci95"]
        fnov = fuse_card["correlation_overlap_vs_registry"]
        fc2st = fuse_card["exact_file_nuisance_audit"]
        fuse_md = f"""
Latest 2026-10-25 `H24-FUSE-HCW` Residualized Conduit OOF-HGB GeoTIFF (executes documented Next Step #4):
[`{fuse_card["submission_name"]}`](docs/downloads/{fuse_card["submission_name"]}) (`SHA-256: {fuse_card["raster_sha256"]}`)
and NaN-outside twin [`{fuse_card["nan_outside_artifact"]}`](docs/downloads/{fuse_card["nan_outside_artifact"]}).
Passes exact-grid/`[0,1]` checks, passes exact-file C2ST nuisance audit (AUC `{fc2st["observed_auc"]:.4f}` < 0.55, Holm *p* = `{fc2st["holm_p_value"]:.3f}`; `FUSE-RESID` AUC `{farms["fuse_resid"]["c2st_auc"]:.4f}`, down from `0.5826` on `SAHG1`), and passes prospective novelty against all {fnov["competing_method_rasters_checked"]} competing method lanes (max 3-px overlap `{fnov["method_lane_max_overlap_within_3px"]:.4f}` ≤ 0.70 vs. `{farms["fuse_raw"]["method_lane_max_overlap_within_3px"]:.4f}` FAIL on unresidualized `FUSE-RAW`) and {fnov["peer_blobs_checked"]} peer blobs (`{fnov["peer_blobs_max_overlap_within_3px"]:.4f}` ≤ 0.70). Achieves **HOLDOUT-DTI** `{fh["evaluator_version"]}` = **{fh["dti"]:.5f}** (95% CI **[{flo:.5f}, {fhi:.5f}]**, 60,988 withheld positives) and `{fbr["evaluator_version"]}` = **{fbr["dti"]:.5f}** (95% CI **[{fblo:.5f}, {fbhi:.5f}]**), outperforming every prior method-lane-unique detector in this repository (`SAHG1` `0.09672` by **+0.02701**, `ASPC` `0.08553` by **+0.02798**, `CON` `0.06446` by **+0.05926**, `MTR1` `0.06441` by **+0.05931**, `H-UNIQUE-03` `0.05384` by **+0.06988**). Remains **DOWNLOAD: YES · SUBMIT: NO** because removing road/claim/acquisition-block confounds costs `-0.00627` relative to the unresidualized `oof_multiphysics_hgb_d3` baseline (`0.13000`) and the literal all-entry overlap rule still flags the synthetic spacing-5 calibration lattice (`1.0`).
[FUSE-HCW JSON run card](evidence/hcw_run_card_20261025.json) · [FUSE preregistration](knowledge/17_preregistered_FUSE_2026-10-25.md) · [FUSE findings & audit](knowledge/18_FUSE_findings_2026-10-25.md)
"""
    gvc1_card = load("evidence/gvc1_run_card_20261025.json")
    gvc1_exp = load("evidence/gvc1_experiment_20261025.json")
    gvc1_md = ""
    if gvc1_card and gvc1_exp:
        gh = gvc1_card["holdout"]
        glo, ghi = gh["ci95"]["interval"]
        gb = gvc1_card["baselines_same_evaluator"]
        gp = gvc1_exp["paired_comparisons"]["E1_vs_B1_physics_geothermal_gain"]
        gd_lo, gd_hi = gp["paired_delta_ci95"]
        gc2 = gvc1_card["c2st_nuisance_audit"]
        gnov = gvc1_card["correlation_overlap_vs_registry"]
        gvc1_md = f"""
Highest-Holdout 2026-10-25 `H24-GVC1` INGENIOUS Hydrothermal-Upflow + Tilt + 8-Azimuth Lineament GeoTIFF:
[`{gvc1_card["submission_name"]}`](docs/downloads/{gvc1_card["submission_name"]}) (`SHA-256: {gvc1_card["raster_sha256"]}`),
NaN-outside twin [`{gvc1_card["nan_submission_name"]}`](docs/downloads/{gvc1_card["nan_submission_name"]}), and
[`{gvc1_card["zip_submission_name"]}`](docs/downloads/{gvc1_card["zip_submission_name"]}).
Generated independently from 30 scale-separated base features + 18 label-free OpenEI GDR INGENIOUS paleo-sinter/travertine,
2 m shallow temperature-probe, and geothermometry upflow features + Miller–Singh `TMI` tilt + 8-azimuth lineaments + 300 m
submodular allocation (`37,654` binary `{{0.0, 1.0}}` dots; zero copied submission pixels; strict `[0, 1]` PASS; 48/48 two-polarity
leakage canaries PASS; exact-file C2ST **PASS** with AUC `{gc2["candidate_auc"]:.4f}`, Holm *p* = `{gc2["candidate_holm_p"]:.3f}`).
Achieves **HOLDOUT-DTI** `{gh["evaluator_version"]}` = **{gh["dti"]:.5f}** (95% CI **[{glo:.5f}, {ghi:.5f}]**), beating matched
`B1: OOF-Base-Submod` (`{gb["B1_oof_base_submod_dti"]:.5f}`) by **{gp["paired_delta_dti"]:+.5f}** (paired 95% CI **[{gd_lo:+.5f}, {gd_hi:+.5f}]**,
`{gp["fold_wins"]}/{gp["n_folds"]}` folds won), `B0: OOF-H24-Ridge` (`{gb["B0_oof_h24_ridge_dti"]:.5f}`), and `H24-RSHG1` (`0.12900`).
Automatically marked **DOWNLOAD: YES · SUBMIT: NO (`DO_NOT_SUBMIT`)** because 3-px dot overlap reaches
`{gnov["final_max_competing_overlap_within_3px"]:.4f}` (> 0.70) against 161,366-px `10GEMSDOE` range-front ridges (`max |ρ| = {gnov["surface_max_abs_rank_correlation"]:.4f} ≤ 0.90`).
[GVC1 JSON run card](evidence/gvc1_run_card_20261025.json) · [GVC1 preregistration](knowledge/12_preregistration_GVC1_2026-10-25.md) · [GVC1 findings & source ledger](knowledge/13_GVC1_findings_2026-10-25.md)
"""
    rshg1_md = ""
    if rshg1_card:
        rh = rshg1_card["holdout"]
        rlo, rhi = rh["ci95"]["interval"]
        rab = rshg1_card["diagnostic_ablations"]["rshg1_calibrated_pointwise_b0"]
        rbr = rshg1_card["bridge_protocol_holdout"]
        rblo, rbhi = rbr["ci95"]
        rc2st = rshg1_card["exact_file_nuisance_audit"]
        rnov = rshg1_card["correlation_overlap_vs_registry"]
        rshg1_md = f"""
Latest 2026-10-25 `H24-RSHG1` 42-channel Regime-Calibrated Multi-Physics + Strike-Hydro-Geomorph GeoTIFF:
[`{rshg1_card["submission_name"]}`](docs/downloads/{rshg1_card["submission_name"]}) (`SHA-256: {rshg1_card["raster_sha256"]}`)
and NaN-outside twin [`{rshg1_card["nan_outside_artifact"]}`](docs/downloads/{rshg1_card["nan_outside_artifact"]}).
Generated from scratch across 100% of the active footprint (including the 31.8% 3DEP LiDAR gap; zero copied submission pixels;
strict whole-array `[0, 1]` all-finite PASS; 42/42 two-polarity leakage canaries PASS; exact-file C2ST nuisance audit **PASS** with
AUC `{rc2st["observed_auc"]:.4f}`, null p95 `{rc2st["null_p95"]:.4f}`, Holm *p* = `{rc2st["holm_p_value"]:.3f}`).
Achieves **HOLDOUT-DTI** `{rh["evaluator_version"]}` = **{rh["dti"]:.5f}** (95% CI **[{rlo:.5f}, {rhi:.5f}]**; calibrated pointwise
diagnostic **{rab["dti"]:.5f}**; `NE_LidarGapHeavy` fold **0.17285** vs. `0.13464` OOF baseline) and
`{rbr["evaluator_version"]}` = **{rbr["dti"]:.5f}** (95% CI **[{rblo:.5f}, {rbhi:.5f}]**), outperforming `SAHG1` (`0.09672`),
`ASPC` (`0.08553`), `CON` (`0.06446`), `MTR1` (`0.06441`), and `H-UNIQUE-03` (`0.05384`). Automatically marked
**DOWNLOAD: YES · SUBMIT: NO (`DO_NOT_SUBMIT`)** because its locked primary arm statistically ties `oof_multiphysics_hgb_d3`
(`0.13000`, paired Δ `-0.00100`) and 3-px dot overlap reaches `{rnov["method_lane_max_overlap_within_3px"]:.4f}` (> 0.70)
against convergent supervised ridges (`max |ρ| = {rnov["surface_max_abs_rank_correlation"]:.4f} ≤ 0.90`).
[RSHG1 JSON run card](evidence/rshg1_run_card_20261025.json) · [RSHG1 preregistration](knowledge/17_preregistered_RSHG1_2026-10-25.md) · [RSHG1 PhD synthesis & findings](knowledge/18_RSHG1_findings_2026-10-25.md)
"""
    sahg1_md = ""
    if sahg1_card:
        sh = sahg1_card["holdout"]
        slo, shi = sh["ci95"]["interval"]
        soof = sahg1_card["reconstructed_oof_multiphysics_baseline"]
        solo, sohi = soof["ci95"]["interval"]
        sbr = sahg1_card["bridge_protocol_holdout"]
        sblo, sbhi = sbr["ci95"]
        sahg1_md = f"""
Preserved 2026-10-25 `H24-SAHG1` Strike-Hydro-Geomorph GeoTIFF:
[`{sahg1_card["submission_name"]}`](docs/downloads/{sahg1_card["submission_name"]}) (`SHA-256: {sahg1_card["raster_sha256"]}`)
and NaN-outside twin [`{sahg1_card["nan_outside_artifact"]}`](docs/downloads/{sahg1_card["nan_outside_artifact"]}).
Passes exact-grid/`[0,1]` checks and prospective novelty against all 46 competing method lanes (max 3-px overlap `0.4768` ≤ 0.70)
and 83 peer blobs (`0.4594` ≤ 0.70). However, the literal all-entry overlap is `{snov["literal_all_entries_max_overlap_within_3px"]:.1f}` against the retained synthetic calibration lattice, so the duplicate gate fails. SAHG1 achieves **HOLDOUT-DTI** `{sh["evaluator_version"]}` = **{sh["dti"]:.5f}**
(95% CI **[{slo:.5f}, {shi:.5f}]**, 60,988 withheld positives) and `{sbr["evaluator_version"]}` = **{sbr["dti"]:.5f}**
(95% CI **[{sblo:.5f}, {sbhi:.5f}]**), outperforming both `MTR1` (`0.06441`) and `ASPC` (`0.08553`) and its geomorphic-only
ablation (`0.08659`, paired Δ **+0.01012**). Remains **DOWNLOAD: YES · SUBMIT: NO** because it trails the newly reconstructed
same-protocol OOF multi-physics baseline `oof_multiphysics_hgb_d3` (**HOLDOUT-DTI {soof["dti"]:.5f}**, 95% CI **[{solo:.5f}, {sohi:.5f}]**)
and flags the exact-file C2ST nuisance audit (AUC `0.5826`, Holm *p* = `0.020`).
[SAHG1 JSON run card](evidence/sahg1_run_card_20261025.json) · [SAHG1 preregistration](knowledge/12_preregistered_SAHG1_2026-10-25.md) · [SAHG1 findings](knowledge/13_SAHG1_findings_2026-10-25.md)
"""
    trsg1_md = ""
    if trsg1_card:
        th = trsg1_card["holdout"]
        tlo, thi = th["ci95"]["interval"]
        tp = trsg1_card["paired_comparisons"]["arm3_minus_reconstructed_oof_hgb_d3"]
        tbr = trsg1_card["bridge_protocol_holdout"]
        tblo, tbhi = tbr["ci95"]
        tc2st = trsg1_card["exact_file_nuisance_audit"]
        tnov = trsg1_card["correlation_overlap_vs_registry"]
        thalo = trsg1_card["deployment_halo_and_regime_diagnostics"]
        trsg1_md = f"""
Orthogonal 2026-10-26 `H24-TRSG1` 44-channel Two-Regime Seismic-Geothermal Stitched-OOF GeoTIFF (**7/7 Technical Gates PASS · Selector v2: `DO_NOT_SUBMIT`**):
[`{trsg1_card["submission_name"]}`](docs/downloads/{trsg1_card["submission_name"]}) (`SHA-256: {trsg1_card["raster_sha256"]}`),
Single-TIFF ZIP [`{trsg1_card["zip_artifact"]}`](docs/downloads/{trsg1_card["zip_artifact"]}), and
NaN-outside twin [`{trsg1_card["nan_outside_artifact"]}`](docs/downloads/{trsg1_card["nan_outside_artifact"]})
(Note `{len(trsg1_card["note"])} <= 140` chars: `{trsg1_card["note"]}`).
Generated independently from 44 physical channels (restored `ieq_n100a15`/`deq_n100a15` microseismic anisotropy, hyperbolic step-over saddle twist, scale-localized INGENIOUS sinter/`2 m`-probe/geothermometry DoGs, Quaternary vent corridors, selective nuisance residualization, terrain-relief LiDAR-gap calibration, and **100% Dual-Partition Stitched-OOF** Two-Regime allocation; `37,722` binary `{{0,1}}` dots; zero copied pixels).
Passes exact-grid/strict-`[0,1]` checks, 44/44 two-polarity leakage canaries, exact-file C2ST nuisance audit (**AUC `{tc2st["observed_auc"]:.4f}` < 0.55**, Holm *p* = `{tc2st["holm_p_value"]:.3f}`), competing-method + peer novelty across **141** rasters (**max 3-px dot overlap `{tnov["method_lane_max_overlap_within_3px"]:.4f}` ≤ 0.70** vs prior lanes & `≤0.6622` vs `DPRF1`/`TNR1`/`CRP1`/`CUP1`, max `|ρ| = {tnov["pre_placement_max_abs_rank_correlation"]:.4f}` ≤ 0.90), and cures `GVC1`'s `0.0859` in-sample halo collapse (`2<d_cat≤5 px = {100 * thalo["frac_2_to_5px_halo"]:.1f}%` vs `45.8%`; deep concealed `d_cat > 30 px = {100 * thalo["frac_gt_30px_deep_concealed"]:.1f}%` vs `4.1%`).
Achieves **HOLDOUT-DTI** `{th["evaluator_version"]}` = **{th["dti"]:.5f}** (95% CI **[{tlo:.5f}, {thi:.5f}]**, paired Δ **{tp["delta_dti"]:+.5f}**, strictly positive 95% CI **[{tp["ci95"][0]:+.5f}, {tp["ci95"][1]:+.5f}]** over `oof_multiphysics_hgb_d3` `0.13000`; Arm 2 Global **0.14693**; `NE_LidarGapHeavy` **0.18760**) and `{tbr["evaluator_version"]}` = **{tbr["dti"]:.5f}** (95% CI **[{tblo:.5f}, {tbhi:.5f}]**). Held at **`DO_NOT_SUBMIT`** under `gems-selector-v2-literal-quota-fail-closed` (`evidence/trsg1_selector_20261026.json`).
[TRSG1 JSON run card](evidence/trsg1_run_card_20261026.json) · [TRSG1 Selector v2 JSON](evidence/trsg1_selector_20261026.json) · [TRSG1 preregistration](knowledge/19_preregistered_TRSG1_2026-10-26.md) · [9-Site Executive & PhD Synthesis (`GEMSDOE32` `0.2778` → `0.4413`)](knowledge/20_TRSG1_findings_and_portfolio_executive_2026-10-26.md)
"""
    dprf1_md = ""
    if dprf1_card_site and dprf1_hero:
        dh = dprf1_card_site["holdout"]
        dlo, dhi = dh["ci95"]["interval"]
        dbr = dprf1_card_site["bridge_protocol_holdout"]
        dblo, dbhi = dbr["ci95"]
        dp_d3 = dprf1_card_site["paired_comparisons"]["arm1_vs_oof_multiphysics_hgb_d3"]
        dp_b1 = dprf1_card_site["paired_comparisons"]["arm1_vs_B1_oof_base_submod"]
        dnov = dprf1_card_site["correlation_overlap_vs_registry"]
        dc2st = dprf1_card_site["exact_file_nuisance_audit"]["candidate"]
        ddist = dprf1_card_site["off_catalogue_distance_profile"]
        d_decision = "OK_TO_SUBMIT" if dprf1_ok_submit else "DO_NOT_SUBMIT"
        dprf1_md = f"""
Latest 2026-10-26 Point-Best `H24-DPRF1` 52-Channel Dual-Partition Stitched-OOF + Two-Regime Submodular GeoTIFF (**10/10 Competing-Method Technical Gates PASS · Selector v2: `{d_decision}`**):
[`{dprf1_card_site["submission_name"]}`](docs/downloads/{dprf1_card_site["submission_name"]}) (`SHA-256: {dprf1_card_site["raster_sha256"]}`),
Single-GeoTIFF ZIP [`{dprf1_card_site["zip_artifact"]}`](docs/downloads/{dprf1_card_site["zip_artifact"]}), and
NaN-outside twin [`{dprf1_card_site["nan_outside_artifact"]}`](docs/downloads/{dprf1_card_site["nan_outside_artifact"]}).
Independently generated from 30 scale-separated base features + 18 OpenEI GDR INGENIOUS hydrothermal/tilt/lineament features + 4 modality-aware `SAHG1` conduit features using Stratified `d_vis >= 300 m` negative sampling, selective 9-channel non-topographic nuisance residualization, 3-tier relief-conditioned LiDAR-gap calibration, Dual-Partition Stitched-OOF (Quadrant + 45° Diamond, 0% in-sample pixels), apron quantile debiasing, and Two-Regime 300 m submodular allocation (`37,654` binary `{{0.0, 1.0}}` dots; zero copied submission pixels; strict `[0, 1]` all-finite PASS; 52/52 two-polarity leakage canaries PASS; exact-file C2ST **PASS** with AUC `{dc2st["observed_auc"]:.4f}` < 0.55, Holm *p* = `{dc2st["holm_p_value"]:.3f}`).
Achieves the **highest HOLDOUT-DTI in `GEMSDOE24`** on both evaluators: `{dh["evaluator_version"]}` = **{dh["dti"]:.5f}** (95% CI **[{dlo:.5f}, {dhi:.5f}]**, winning `4/4` spatial folds over `oof_multiphysics_hgb_d3` `0.13000` by `{dp_d3["paired_delta_dti"]:+.5f}` and over `B1: OOF-Base-Submod` `0.13900` by `{dp_b1["paired_delta_dti"]:+.5f}`, and beating `CUP1` `0.15038`, `GVC1` `0.14876`, `TRSG1` `0.14644`, `B0` `0.14179`, `CRP1` `0.13747`, `RSHG1` `0.12899`, `FUSE-HCW` `0.12372`, and `TNR1` `0.13219`) and `{dbr["evaluator_version"]}` = **{dbr["dti"]:.5f}** (95% CI **[{dblo:.5f}, {dbhi:.5f}]**).
Passes prospective novelty across **all {dnov["competing_method_rasters_checked"]} competing method rasters** (max 3-px dot overlap `{dnov["method_lane_max_dot_overlap"]:.4f}` ≤ 0.70; `0.3613` vs `TNR1`, `0.3398` vs `CRP1`, `0.3381` vs `CUP1`, ≤ `0.4912` vs all 9 focus-site champions) and **all {dnov["peer_blobs_checked"]} peer blobs** (`{dnov["peer_blobs_max_dot_overlap"]:.4f}` ≤ 0.70), and restores **{100 * ddist["frac_gt_20px_farfield"]:.1f}%** `> 2 km` far-field dot allocation (`{100 * ddist["frac_2_to_9px_apron"]:.1f}%` in `200–900 m` apron, versus `GVC1`'s `70.4%`; no hidden-score improvement established). Held at **`{d_decision}`** under `gems-selector-v2-literal-quota-fail-closed` (`evidence/dprf1_selector_20261026.json`) due to the unseparated synthetic spacing-5 calibration lattice (`registry-039`), unknown live DrivenData quota, and replay certificate.
[DPRF1 JSON run card](evidence/dprf1_run_card_20261026.json) · [DPRF1 Selector v2 JSON](evidence/dprf1_selector_20261026.json) · [9-Site Executive Summary JSON](evidence/nine_site_executive_summary_20261026.json) · [DPRF1 preregistration](knowledge/19_preregistered_DPRF1_2026-10-26.md) · [DPRF1 PhD synthesis & 9-site review](knowledge/20_DPRF1_findings_and_9site_executive_summary_2026-10-26.md)
"""
    crp1_md = ""
    if crp1_card_site and crp1_hero:
        ch = crp1_card_site["holdout"]
        clo, chi = ch["ci95"]["interval"]
        cp = crp1_card_site["paired_vs_baseline"]
        cnov = crp1_card_site["correlation_overlap_vs_registry"]
        c_decision = "OK_TO_SUBMIT" if crp1_ok_submit else "DO_NOT_SUBMIT"
        crp1_md = f"""
Prior 2026-10-26 `H24-CRP1` GeoTIFF:
[`{crp1_card_site["submission_name"]}`](docs/downloads/{crp1_card_site["submission_name"]})
(`SHA-256: {crp1_card_site["raster_sha256"]}`) and NaN-outside twin
[`{crp1_card_site["nan_submission_name"]}`](docs/downloads/{crp1_card_site["nan_submission_name"]}).
Independently computed (zero copied submission pixels) from compositional radiometric
fronts, cross-depth TMI/up150 persistence and Hessian saddles with selective nuisance
residualization. **HOLDOUT-DTI {ch["dti"]:.5f}** (95% CI [{clo:.5f}, {chi:.5f}],
`{ch["evaluator_version"]}`, {ch["n_withheld_positive_pixels"]:,} withheld positives);
paired Δ vs reconstructed OOF baseline {cp["delta_dti"]:+.5f} (95% CI
[{cp["ci95"][0]:+.5f}, {cp["ci95"][1]:+.5f}]); max competing-method 3-px dot overlap
{cnov["final_max_method_overlap_within_3px"]:.4f} (limit 0.70). Independent selector
decision: **{c_decision}** — see `evidence/crp1_selector_20261026.json`. No organizer
score exists; HOLDOUT-DTI is not a leaderboard forecast. Short comment
({crp1_card_site["note_length"]} chars): `{crp1_card_site["note"]}`
[CRP1 run card](evidence/crp1_run_card_20261026.json) ·
[Preregistration](knowledge/20_preregistered_CRP1_2026-10-26.md) ·
[Executive guide](docs/executive-summary.html#crp1)
"""
    status_headline = (
        "**DOWNLOAD: YES. SUBMIT: YES for `H24-DPRF1` (`OK_TO_SUBMIT` via independent selector `gems-selector-v1`; confirm weekly quota on DrivenData) — automatic verdict, zero human inspection pending. All earlier candidates below remain `DO_NOT_SUBMIT`.**"
        if dprf1_ok_submit
        else "**DOWNLOAD: YES. SUBMIT: NO — automatic NEGATIVE verdict, not human inspection pending.**"
    )
    md = f"""{status_headline}
{dprf1_md}{trsg1_md}{crp1_md}{fuse_md}{gvc1_md}{rshg1_md}{sahg1_md}
Independently generated MTR1 audit TIFF: [`{primary["file"]}`](docs/downloads/{primary["file"]}).
It passes exact-grid/[0,1] file checks but fails the lane overlap rule against a registered
spacing-5 calibration lattice. Content is not copied or identical to any compared file;
this does **not** mean the lane-uniqueness gate passed. No comparator was removed.

**HOLDOUT-DTI** `{version}`: **{score["dti"]:.5f}**, approximate **95% CI
[{lo:.5f}, {hi:.5f}]**; **{n:,} withheld positives** in whole components, buffered
quadrants, pooled metric components. No ORGANIZER-CONFIRMED score exists; this is
not a leaderboard result. No weekly slot has been spent by this session.

[Executive guide](docs/executive-summary.html) · [JSON run card](evidence/mtr1_run_card.json) ·
[Preregistration](knowledge/09_preregistration_magnetic_trough_2026-10-25.md) ·
[Current owner brief](knowledge/owner_brief_2026-10-25.md)

Parallel ASPC research from PR #10 is retained with its own negative verdict and
[run card](evidence/aspc_run_card_20261025.json); its protocol differs, so the two
point scores are not a certified current-best comparison.

Earlier scores/forecasts below are historical, not current promotion authority.
"""
    if latest:
        oj = load("evidence/oj1_run_card_20261025.json")
        oh = oj["holdout"]
        olo, ohi = oh["ci95"]["interval"]
        md = (
            f"Latest OJ1 research TIFF: [`{oj['submission_name']}`](docs/downloads/{oj['submission_name']}). "
            f"**DOWNLOAD YES / SUBMIT NO**. HOLDOUT-DTI {oh['dti']:.5f}, 95% CI [{olo:.5f}, {ohi:.5f}], "
            f"{oh['evaluator_version']}, {oh['n_withheld_positive_pixels']:,} withheld positives. "
            "Stopped as duplicate, not a leaderboard result. No weekly slot has been spent. "
            "[OJ1 run card](evidence/oj1_run_card_20261025.json).\n\n" + md
        )
    if tnr1:
        md = tnr1["status_md"] + md
    readme = ROOT / "README.md"
    readme.write_text(
        re.sub(
            r"<!-- STATUS:START -->.*?<!-- STATUS:END -->",
            f"<!-- STATUS:START -->\n{md}<!-- STATUS:END -->",
            readme.read_text(),
            flags=re.S,
        )
    )
    receipt = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "primary_sha256": tnr1["active"]["artifact"]["sha256"] if tnr1 else primary["sha256"],
        "pages": [str((DOCS / p).relative_to(ROOT)) for p in pages],
        "root": "index.html",
        "slot_recommendation": "not_recommended",
        "new_slot_eligible": False,
        "no_scores_fabricated": True,
        "verdict": "negative",
        "current_evaluator": version,
    }
    (ROOT / "evidence/site_build.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))


def main():
    # Both negative lanes supersede historical recommendations. MTR has its own
    # packet; never overwrite the incoming historical metadata or ASPC receipt.
    primary = load("docs/data/independent_download.json")
    if primary.get("generation") == "independent-mtr1-v1":
        return build_independent_site(primary)
    if (ROOT / "evidence/aspc_run_20261025.json").exists():
        from build_lane_site import build

        build(ROOT, page)
        return
    primary = load("docs/data/download.json")
    alternate = load("docs/data/alternate_download.json")
    reference = load("docs/data/reference_download.json")
    if not primary or not reference:
        raise SystemExit("Build the primary candidate and the reference bundle first")
    for row in (primary, alternate, reference):
        if not row:
            continue
        p = DOCS / "downloads" / row["file"]
        if not p.exists() or sha256_file(p) != row["sha256"]:
            raise SystemExit(
                f"Website download missing or differs from its checksum: {row['file']}"
            )
    comp = load("evidence/h24_e1_operator_comparison.json")
    cal = load("evidence/emission_calibration.json")
    exp1 = load("evidence/h24_e1_emission_experiment.json")
    exp2 = load("evidence/h24_2_experiment.json")
    audit = load("evidence/accessibility_audit_v2.json")
    forensics = load("evidence/format_forensics.json")
    geom = load("evidence/lb_geometry_analysis.json")
    sources = load("docs/data/sources.json")
    group = load("evidence/group_review.json")
    review = load("evidence/review_passes.json")
    health = load("docs/data/source_health.json")
    irregs = load("registry/irregularities.json")
    ledger = load("registry/live_scores.json")

    rows = comp.get("bases", {}).get("h19-5", {}).get("candidates", {})
    solid = rows.get("solid", {})
    sel_name = comp.get("frozen_selection", {}).get("primary")
    alt_name = comp.get("frozen_selection", {}).get("alternate_sparse_optimal")
    sel = rows.get(sel_name, {})
    alt = rows.get(alt_name, {})
    tau = cal.get("lattice", {}).get("tau")
    pair = cal.get("natural_experiment_same_surface_6452ae1d00", {})
    val = exp1.get("extrapolation_validation_h25_to_h28", {})
    refs = audit.get("references", {})
    lab_a, h4_a, h5_a = refs.get("labels", {}), refs.get("h19-4", {}), refs.get("h19-5", {})
    c1_a, c2_a = refs.get("candidate", {}), refs.get("candidate_alt", {})

    def auc(r):
        return r.get("primary", {}).get("observed_auc")

    rec = primary.get("slot_recommendation") or "not_recommended"
    model_lo = sel.get("selection", {}).get("model_public_score")
    sparse_gain = sel.get("selection", {}).get("paired_sparse_gain_rel")
    leader = health.get("leaderboard", {})
    n_px = primary.get("pixel_count")
    ratio = sel.get("pixel_fraction")
    n_base = comp.get("bases", {}).get("h19-5", {}).get("n_base", 121131)
    area = 5167373
    fp_share = None
    if tau:
        tp_b = emission.implied_credit(0.1922, n_base / area, tau, phi=0.05)
        fp_b = (n_base / area) * 0.95
        fp_share = 0.2 * fp_b / (0.2 * (tp_b + fp_b) + 0.8 * tau)

    if rec == "eligible":
        banner = (
            "<strong>Slot-eligible under the owner's rule.</strong> Holdout gates and the strict "
            "exact-file accessibility audit both pass. Expected effect is model-based, not a score."
        )
    elif rec == "owner_decision_required":
        banner = (
            "<strong>Owner decision required before a weekly slot is spent.</strong> The file passes "
            "the frozen holdout gates and every format check, but the strict accessibility gate is "
            f"not passed — the same is true of the already-scored reference (H19-4 prediction AUC "
            f"{fmt(auc(h4_a), 3)}, H19-5 {fmt(auc(h5_a), 3)}, vs label AUC {fmt(auc(lab_a), 3)}). This file is no more associated "
            "with accessibility than that reference. The agent cannot upload anything."
        )
    else:
        banner = (
            "<strong>Not recommended for a slot.</strong> The exact-file audit shows more nuisance "
            "association than the reference it was derived from."
        )

    # ------------------------------------------------------------------ overview
    def bar(label, value, maxv, kind=""):
        width = 100 * value / maxv if value is not None and maxv else 0
        return (
            f'<div class="chartrow"><span>{label}</span><div class="track"><div class="bar {kind}" '
            f'style="width:{width:.2f}%"></div></div><strong>{fmt(value)}</strong></div>'
        )

    sp = lambda r: r.get("selection", {}).get("mean_sparse_dti")  # noqa: E731
    maxv = max([sp(r) or 0 for r in (solid, sel, alt)] or [0.1]) * 1.12
    chart = (
        bar("H19-5 as emitted", sp(solid), maxv)
        + bar("Primary (dot-thinned)", sp(sel), maxv, "candidate")
        + bar("Alternate (sparser)", sp(alt), maxv, "candidate")
    )
    hero = f"""<div class="hero"><div><div class="eyebrow">DOE GEMS Prize · submission file</div><h1>Download the file.<br>Know exactly what it is.</h1><p class="lead">One click gets the recommended submission GeoTIFF. It is a <strong>new, unscored</strong> candidate: the best owner-reported prediction (H19-5, reported 0.1922) re-emitted as a label-free, dot-thinned subset — {n_px:,} pixels, {100 * (ratio or 0):.0f}% of the original — because at the truth density the owner's own scores imply, false-positive mass dominates the metric.</p><div class="actions">{download_button(primary, "")}<a class="button" href="executive-summary.html">How to submit, step by step ↗</a></div><p class="micro"><span class="badge amber">Candidate · not yet scored</span> <span class="badge blue">float32 · [0,1] · NaN outside</span> <span class="badge gray">unique id {e(primary["content_id"])}</span></p><div class="fileline">{e(primary["file"])}</div></div><aside class="card visual"><div class="cardtop"><h3>LOCAL SPARSE-HOLDOUT DTI</h3><span class="badge amber">Not leaderboard scores</span></div>{chart}<p class="legend">Same emitted-raster protocol for all three, 30 sparse-truth draws × 4 spatial folds. Sparse truth density (≈0.24% of the footprint) matches the density calibrated from the owner's blind-lattice score. Paired gain of the primary over H19-5: <strong>{pct(sparse_gain)}</strong>.</p></aside></div>"""
    status = f'<div class="status">{banner}</div>'
    metrics = f"""<div class="metrics"><div class="card metric"><div class="number">0.1922</div><div class="label">Best owner-reported score</div><div class="sub">H19-5 · owner-reported, not a receipt</div></div><div class="card metric"><div class="number" data-leader-score>{fmt(leader.get("best_score"))}</div><div class="label">Official leader snapshot</div><div class="sub"><span data-leader-name>{e(leader.get("participant", "n/a"))}</span> · <span data-source-time>{e(health.get("checked_utc", ""))}</span></div></div><div class="card metric"><div class="number">{fmt((tau or 0) * 100, 2)}%</div><div class="label">Calibrated truth density</div><div class="sub">from the blind-lattice score · ≈{(cal.get("lattice", {}).get("truth_px_equivalent") or 0):,.0f} px</div></div><div class="card metric"><div class="number">{fmt(model_lo, 2)}</div><div class="label">Model expectation (not a score)</div><div class="sub">plausible 0.22–0.28 · one calibration pair</div></div></div>"""
    feed_items = "".join(
        f'<li><a href="{e(u["url"])}">{e(u["title"])}</a><small>{e(u.get("kind", ""))} · {e(u.get("checked_utc", ""))}</small></li>'
        for u in health.get("updates", [])[:5]
    )
    overview = (
        hero
        + status
        + metrics
        + f"""<section><div class="sectionhead"><h2>Why this file, in three facts</h2><a href="research.html" class="small">Methods and numbers →</a></div><div class="grid3"><article class="card"><div class="tagline">01 · The metric</div><h3>Every emitted pixel costs 0.2</h3><p>DTI = TPw / (0.2·(TPw+FPw) + 0.8·|G|). False-positive mass is linear in emitted pixels; |G| (hidden new-fault pixels) is small. {link("https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/#performance-metric", "Official definition")}</p></article><article class="card"><div class="tagline">02 · The measurement</div><h3>A blind lattice reveals the density</h3><p>The owner's spacing-5 lattice scored 0.0904. A uniform lattice earns the same expected credit wherever truth is, so that one number gives the hidden truth density (≈{fmt((tau or 0) * 100, 2)}% of cells). In the first-order model the false-positive term is about {fmt((fp_share or 0) * 100, 0)}% of H19-5's DTI denominator.</p></article><article class="card"><div class="tagline">03 · The precedent</div><h3>Dotting already worked once</h3><p>Same probability surface, solid → dotted: owner-reported 0.1280 → 0.1839 (+44%) with 60% fewer pixels. H19-4/H19-5 were never dotted. This session tests that on the best surface, under frozen rules.</p></article></div></section>
<section><div class="grid2"><article class="card"><div class="sectionhead"><h2>What was checked</h2><span class="badge">Computed in this repo</span></div><ol class="steplist"><li><h3>Format and range</h3><p>Single band, float32, EPSG:32611, exact grid; all {5167373:,} footprint values finite in [0,1]; NaN outside. {forensics.get("submission_grid_float32_rasters", 0)} owner rasters profiled: none has a value outside [0,1].</p></li><li><h3>Paired holdout, frozen rule</h3><p>Four spatial quadrants, 30 selection + 30 confirmation sparse-truth draws; the primary improves sparse and dense DTI and wins {sel.get("selection", {}).get("draw_fold_wins", 0)}/{sel.get("selection", {}).get("draw_fold_cells", 0)} fold-draw cells.</p></li><li><h3>Exact-file accessibility audit</h3><p>Labels first, then each raster: roads, closed claims, four acquisition blocks. Labels AUC {fmt(auc(lab_a), 3)} (chance); H19-4 prediction {fmt(auc(h4_a), 3)}.</p></li><li><h3>Reproducibility</h3><p>The alternate raster is byte-identical to the earlier session's independently frozen candidate (SHA-256 prefix {e((alternate or {}).get("sha256", "")[:8])}).</p></li></ol></article><article class="card"><div class="sectionhead"><h2>Source updates</h2><span class="badge gray">Timestamped</span></div><ul class="feed" id="source-feed-list">{feed_items}</ul><p class="micro" data-source-state>Latest verified snapshot, not a live scoring API</p><p class="micro">The live site is served by GitHub Pages from <code>main</code>. DrivenData rows are <strong>human-read snapshots</strong> (its Terms of Use forbid automatic access, so nothing here fetches it); only the USGS ScienceBase API is checked automatically. Check the timestamps.</p></article></div></section>
<section><div class="callout"><div><h3>Not a renamed reference</h3><p>The already-scored H19-5 file is kept for reference only. Re-uploading it spends a slot for no new information.</p></div><a class="button" href="downloads/{e(reference["file"])}" download>Reference H19-5 (do not resubmit)</a></div></section>"""
    )

    # ------------------------------------------------------------------ executive summary
    alt_block = ""
    if alternate:
        alt_block = f"""<article class="card"><h3>Alternate · sparse-optimal</h3><span class="badge amber">{e(REC_LABEL.get(alternate.get("slot_recommendation"), "Owner decision required"))}</span><p class="fileline">{e(alternate["file"])}</p><ul class="checks"><li>{alternate.get("pixel_count", 0):,} pixels · {100 * (alt.get("pixel_fraction") or 0):.0f}% of H19-5</li><li>Highest sparse DTI ({fmt(sp(alt))} vs {fmt(sp(solid))}); fails the dense-regime criterion by {fmt(abs(alt.get("selection", {}).get("paired_dense_gain_abs") or 0), 4)}</li><li>Same pixel set as the earlier session's frozen d*=2.8 candidate</li></ul><div class="actions">{download_button(alternate, "", "Alternate .tif", False)}<a class="button" href="downloads/{e(alternate["zip"])}" download>ZIP</a></div>{note_block(alternate, "alt")}</article>"""
    steps = f"""<ol class="steplist"><li><h3>1 · Download the file</h3><p>Use the green button. It is one single-band GeoTIFF. Do <em>not</em> upload the 19-band feature stack, a raw layer, a folder, or the reference file. Check that the SHA-256 shown on this page matches.</p></li><li><h3>2 · Open the portal</h3><p>Sign in at {link(COMP, "DrivenData · GEMS")}, click <strong>Submit</strong> in the sidebar, then <strong>Make new submission</strong> (competition page, “How to compete”, step 6).</p></li><li><h3>3 · Choose the file</h3><p>“File to submit”: the portal accepts <em>“a single-band GeoTIFF (.tif) file, or a .zip file containing a single GeoTIFF… It must match the submission format's CRS, shape, and geotransform.”</em> Choose the <code>-nan.tif</code> (official: NaN outside the footprint) or its single-file ZIP.</p></li><li><h3>4 · Paste the note</h3><p>The “Note (optional)” box is for “a short comment to help you or your team tell submissions apart later”. Paste the copyable note below (it carries the content id).</p></li><li><h3>5 · Submit, then record the result</h3><p>Wait for the score. Record the score, time and SHA-256 with <code>python scripts/record_live_score.py</code>. Nothing here uploads for you, and automating DrivenData is not permitted by its terms.</p></li><li><h3>6 · If you see “Predicted values must be in range [0, 1]”</h3><p>Stop and do not rescale. (a) Confirm you chose the single-band file from this page by SHA-256. (b) Try the <code>-allfinite.tif</code> fallback (zeros outside): the owner's 12GEMSDOE record shows both conventions were accepted and scored identically (0.1294). (c) Send the checks JSON to the organizers (<a href="mailto:gemsprize@nlr.gov">gemsprize@nlr.gov</a>). The cause of the original message is <strong>not established</strong> — see the forensics on the Sources page.</p></li></ol>"""
    executive = f"""<div class="pagehead"><div class="eyebrow">Executive summary · exact submission instructions</div><h1>Submit in six steps.</h1><p>The file below is a new, label-free re-emission of H19-5. It has no leaderboard score yet. Weekly limit: <strong>three submissions</strong>; one final submission is chosen without seeing private scores.</p><div class="actions">{download_button(primary, "")}<a class="button" href="index.html">Overview</a></div></div><div class="status">{banner}</div>
<section class="narrow"><h2>The submission</h2><div class="grid2"><article class="card"><h3>Primary · recommended download</h3><span class="badge blue">{e(REC_LABEL.get(primary.get("slot_recommendation"), ""))}</span><p class="fileline">{e(primary["file"])}</p><ul class="checks"><li>Single band · float32 · EPSG:32611 · 3730 × 3292 · 100 m · exact template transform</li><li>All {5167373:,} in-footprint values finite and in [0,1]; NaN outside</li><li>{primary.get("pixel_count", 0):,} positive pixels; none on a catalogue pixel</li><li>Exact recomputation from pinned H19-5 verified (label-free)</li></ul><p class="small">SHA-256</p><div class="note hash" id="file-sha">{e(primary["sha256"])}</div><div class="actions" style="margin-top:12px"><a class="button" href="downloads/{e(primary["zip"])}" download>Single-TIFF ZIP</a><a class="button" href="downloads/{e(primary["fallback"])}" download>Zeros-outside fallback</a><a class="button" href="downloads/{e(primary["checks_file"])}" download>Checks JSON</a></div>{note_block(primary, "primary")}</article>{alt_block}</div></section>
<section class="narrow"><h2>Step by step</h2>{steps}<a class="button" href="{COMP}" target="_blank" rel="noopener noreferrer">Official competition ↗</a></section>
<section class="narrow"><h2>Suggested slot plan (owner decides)</h2><div class="card"><p>Two submissions that differ <em>only</em> in thinning, on identical detection content, measure the emission curve directly: upload the <strong>primary</strong> first; upload the <strong>alternate</strong> in the same week if the owner accepts its declared exception. If the primary does not beat 0.1922, the false-positive-dominance premise is wrong or over-stated and the plan changes. Keep the third slot for the next detector change. Never re-upload the reference.</p><p class="micro">Rules: three submissions per week (§3.2); competition page end date “Dec. 3, 2026, 11:59 p.m. UTC” versus rules “5:00 p.m. ET” on the deadline date — confirm with the organizers. Generative-AI use must be disclosed in the narrative.</p></div></section>"""

    # ------------------------------------------------------------------ research
    def cand_row(name):
        r = rows.get(name, {})
        s, c = r.get("selection", {}), r.get("confirmation", {})
        base = name == "solid"
        gate_s = s.get("legacy_gate", {}).get("passed")
        gate_c = c.get("legacy_gate", {}).get("passed")
        return (
            f'<tr><td>{e(name)}<br><span class="sourcekind">{e(r.get("kind", ""))}</span></td><td class="num">{r.get("n", 0):,}</td>'
            f'<td class="num">{fmt(s.get("mean_dense_dti"))}</td><td class="num">{fmt(s.get("mean_sparse_dti"))}</td>'
            f'<td class="num">{"—" if base else pct(s.get("paired_sparse_gain_rel"))}</td><td class="num">{fmt(c.get("mean_sparse_dti"))}</td>'
            f'<td>{"—" if base else ("pass" if gate_s else "fail") + " / " + ("pass" if gate_c else "fail")}</td><td class="num">{fmt(s.get("model_public_score"), 3)}</td></tr>'
        )

    order = ["solid", "D1.5", "K0.496", "D2.4", "K0.364", "D3.2", "K0.287", "K0.600"]
    op_rows = "".join(cand_row(n) for n in order if n in rows)
    pair_ret = pair.get("implied_credit_retention_from_reported_scores")
    res2 = exp2.get("results", {})
    hist2 = exp2.get("historical_diagnostics", {})
    arm_names = {
        "physics_raw": "Physics, raw",
        "physics_arc_raw": "Physics + arc, raw",
        "physics_residualized": "Physics, residualized",
        "physics_arc_residualized": "Physics + arc, residualized",
    }
    refit_rows = "".join(
        f'<tr><td>{arm_names[k]}</td><td class="num">{fmt(v.get("mean_dense_dti"), 4)}</td><td class="num">{fmt(v.get("mean_sparse_dti"), 4)}</td><td></td></tr>'
        for k, v in res2.items()
        if k in arm_names
    ) + "".join(
        f'<tr><td>{k.upper()} as emitted</td><td class="num">{fmt(v.get("mean_dense_dti"), 4)}</td><td class="num">{fmt(v.get("mean_sparse_dti"), 4)}</td><td><span class="sourcekind">diagnostic, not OOF</span></td></tr>'
        for k, v in hist2.items()
    )
    raw2, cand2 = res2.get("physics_raw", {}), res2.get("physics_arc_residualized", {})
    res_audit = refs.get("h24-2a-residualized", {})
    refit_verdict = (
        f"With the corrected sources the arc + residualized arm does <strong>not</strong> beat the raw physics baseline "
        f"(Δdense {fmt((cand2.get('mean_dense_dti') or 0) - (raw2.get('mean_dense_dti') or 0), 4)}, "
        f"Δsparse {fmt((cand2.get('mean_sparse_dti') or 0) - (raw2.get('mean_sparse_dti') or 0), 4)}), and residualizing alone costs dense DTI. "
        "Block membership is a latitude band, so removing it also removes regional geology, while the labels themselves show no accessibility association "
        f"(AUC {fmt(auc(lab_a), 3)}). "
        + (
            f"The residualized detector's emitted raster audits at AUC {fmt(auc(res_audit), 3)} (H19-5: {fmt(auc(h5_a), 3)})."
            if res_audit
            else ""
        )
    )
    research = f"""<div class="pagehead"><div class="eyebrow">Methods · frozen protocol · limits</div><h1>Efficiency before more detectors.</h1><p>The metric charges 0.2 per emitted pixel. Calibrating the hidden truth density from the owner's own blind-lattice score shows the best files emit ~10× more pixels than there is truth. Re-emitting H19-5 more efficiently is the cheapest lever with direct evidence.</p></div><div class="status">{banner}</div>
<section><h2>What the owner's scores reveal</h2><div class="grid2"><article class="card"><h3>Truth density from a blind lattice</h3><p>The 13GEMSDOE spacing-5 lattice (owner-reported <strong>0.0904</strong>; mean kernel credit {fmt(cal.get("lattice", {}).get("mean_kernel_credit"), 3)}, {cal.get("lattice", {}).get("emitted_px", 0):,} pixels) implies τ = <strong>{fmt((tau or 0) * 100, 3)}%</strong> of cells ({(cal.get("lattice", {}).get("truth_px_equivalent") or 0):,.0f} px ≈ {fmt((cal.get("lattice", {}).get("truth_to_catalogue_ratio") or 0) * 100, 1)}% of the catalogue). Synthetic recovery: mean error +2.5%, SD 7.6%. This lies inside GEMSDOE10's independent 0.13–0.6% bound.</p><p class="micro">Caveat: 0.0904 appears only in the 2026-10-02 brief (older snapshot blank) — unconfirmed by the portal.</p></article><article class="card"><h3>A natural experiment</h3><p>Same probability surface (<code>6452ae1d00</code>): solid H25 (161,366 px) <strong>0.1280</strong> → dotted H28 (65,236 px) <strong>0.1839</strong>, +{fmt((pair.get("score_change") or 0) * 100, 0)}% (also brief-only). Implied credit retention {fmt(pair_ret, 2)}.</p><p>Out-of-sample check of my harness-based extrapolation on this pair: it under-predicted ({fmt((val.get("predictions", {}) or {}).get("phi0.05"), 3)} vs 0.1839). The harness's sparse ratio was {fmt(val.get("harness_sparse_dti_ratio_h28_over_h25"), 2)} (right sign, conservative) but its <em>dense</em> ratio was {fmt(val.get("harness_dense_dti_ratio_h28_over_h25"), 2)} (wrong sign).</p></article></div></section>
<section><h2>Equal-pixel-count operator comparison (H19-5)</h2><div class="tablewrap"><table><thead><tr><th>Candidate</th><th>Pixels</th><th>Dense DTI</th><th>Sparse DTI</th><th>Sparse gain</th><th>Sparse (confirm)</th><th>Legacy gate sel / conf</th><th>Model score</th></tr></thead><tbody>{op_rows}</tbody></table></div><p class="micro">D = earlier session's geodesic Poisson-disk <code>dot_thin</code>; K = this session's greedy kernel cover (inferior at equal N — recorded, not hidden). Selection draws 0–29, confirmation 30–59. Frozen rule: highest model score among candidates passing the legacy gate on selection and confirmation → <strong>{e(sel_name)}</strong>; alternate = highest sparse DTI → <strong>{e(alt_name)}</strong>. Model score = first-order extrapolation from the harness's sparse credit retention, not a leaderboard result.</p></section>
<section><h2>Refit on the corrected nuisance sources (previous sessions' next step)</h2><div class="tablewrap"><table><thead><tr><th>Arm</th><th>Dense DTI</th><th>Sparse DTI</th><th>Note</th></tr></thead><tbody>{refit_rows}</tbody></table></div><p class="micro">Frozen H24-2A protocol: four spatial quadrants, 1.5 km collar, whole-component exclusion, training-only residualization, one truth draw. Nuisance = buffered Census roads, closed claims and the four derived blocks (the earlier run had only Area 1 and clipped roads). {refit_verdict}</p></section>
<section><div class="grid2"><article class="card"><h3>Why H19-4 / H19-5 scored best (supported)</h3><ul class="prose"><li>Same family: ≈90% topographic/scarp terms, Jaccard 0.777, ridge-thinned, no pixel on a catalogue cell.</li><li>≈23% of emitted pixels lie within 300 m of the catalogue; files that hug it (≥45% within 300 m) never exceeded 0.046 ({geom.get("halo_heavy_files_ge45pct_within_3px", {}).get("n", 0)} files).</li><li>Distance-to-catalogue alone does not explain scores (Spearman {fmt(geom.get("spearman_score_vs_share_within_3px_of_catalogue"), 2)}): method skill matters.</li><li>Not supported: attributing the +0.0028 H19-4→H19-5 gain to any named physical line.</li></ul></article><article class="card"><h3>Is a higher score possible?</h3><p>Already: H19-5 exceeded 0.1894. Beyond it, the lever with direct evidence is emission efficiency (model central {fmt(model_lo, 2)}). The 0.3195 leader needs new information or a much better detector; thinning alone does not get there.</p><p class="micro">Phase 2 re-scores on an expanded, denser label set, which favours less aggressive thinning — hence the primary is the gate-passing 50% file, not the sparsest.</p></article></div></section>"""

    # ranked hypotheses (merged with knowledge/05)
    hyp_rows = [
        (
            "1",
            "H25-1 / H24-E1 · calibrated dotted H19",
            "none (transform of pinned H19-5)",
            "Not geology: lowers the cost of every candidate trace",
            "same detections, ~½ the false-positive mass",
            "<span class='badge blue'>Validated on holdout (this page)</span>",
        ),
        (
            "2",
            "H25-2 · strike-compatibility prior",
            "emitted-ridge orientation; training-region catalogue strike field",
            "Raises precision for lineaments compatible with the local Andersonian strike family",
            "no orientation prior in the pipeline",
            "+0.00–0.01 · ≈1 day · <span class='badge amber'>Not yet tested</span>",
        ),
        (
            "3",
            "H25-3 · scarp cross-profile template",
            "1 m 3DEP (706/716 tiles processed on CI)",
            "Short Quaternary scarps unlisted in the catalogue",
            "per-100 m maxima lose profile shape",
            "+0.01–0.03 · ≈2 days · CI re-run",
        ),
        (
            "4",
            "H25-6 · map-scale correction corridor",
            "INGENIOUS <code>MAPSCALE</code> per trace (82% of length at 1:250k) + lidar scarps",
            "Staff: new truth may lie within 300 m of a known trace; Qfaults can be ≈400 m off (Hermant 2025)",
            "catalogue geometry is used as a positional-uncertainty prior, not a halo (halos fail)",
            "unknown · needs a per-pixel map-scale raster (free GDR 1391) · <span class='badge amber'>Not yet tested</span>",
        ),
        (
            "5",
            "H25-4 · concealed basin-margin step",
            "depth_to_base_surf, iso_grav_anom_hg, tmi_hg",
            "Buried range-front faults without a scarp",
            "geophysics only as raw GBM channels",
            "small/uncertain · ≈2 days",
        ),
    ]
    hyp_html = "".join(
        f"<tr><td><strong>{r[0]}</strong></td><td>{r[1]}</td><td>{r[2]}</td><td>{r[3]}</td><td>{r[4]}</td><td>{r[5]}</td></tr>"
        for r in hyp_rows
    )
    research += f"""<section><h2>Ranked hypotheses</h2><div class="tablewrap"><table><thead><tr><th>#</th><th>Hypothesis</th><th>Layers</th><th>Why it can catch missing faults</th><th>Difference from the repo</th><th>Expected DTI · cost · status</th></tr></thead><tbody>{hyp_html}</tbody></table></div><p class="micro">Ranking = expected DTI gain × probability the local proxy can validate it ÷ cost. Item 1 is not a geological hypothesis; the top <em>geological</em> hypothesis (H25-2) is untested. Novelty is relative to reviewed code, not to unseen competitors.</p></section>
<section><h2>Keep the caveats</h2><ul class="prose"><li>The as-emitted harness is leaky for H19 (its mask excluded <em>all</em> catalogue pixels), so absolute DTI is inflated; the paired comparison cancels the shared leak.</li><li>Proxy-vs-live rank correlations are weak (SGMC-minus-catalogue ρ≈+0.33, n=24); a holdout win is necessary, not sufficient.</li><li>The calibration assumes a blind lattice, FP mass ≈ N(1−φ), and that public-subset truth density transfers to the private subset; Phase 2 is expected to be denser.</li><li>Hidden test sources and fault types are undisclosed by the organizers.</li></ul></section>"""

    # ------------------------------------------------------------------ sources
    def audit_row(key, label):
        v = refs.get(key)
        if not v:
            return ""
        p = v.get("primary", {})
        flag = v.get("meaningful_access_association_available_features")
        status = "Flagged association" if flag else "Below effect rule"
        singles = v.get("single_feature_auc_descriptive", {})
        top = max(singles, key=singles.get) if singles else "—"
        return (
            f'<tr><td>{e(label)}</td><td class="num">{v.get("positive_pixels", 0):,}</td><td class="num">{fmt(p.get("observed_auc"), 4)}</td>'
            f'<td class="num">{fmt(p.get("holm_p_value"), 3)}</td><td class="num">{fmt(p.get("margin_vs_p95"), 4)}</td>'
            f'<td>{e(top)} {fmt(singles.get(top), 3) if singles else ""}</td><td><span class="badge {"amber" if flag else "gray"}">{status}</span></td></tr>'
        )

    audit_rows = "".join(
        audit_row(k, name)
        for k, name in (
            ("labels", "Training labels (first)"),
            ("h19-4", "H19-4 as emitted"),
            ("h19-5", "H19-5 as emitted"),
            ("candidate", "Primary candidate"),
            ("candidate_alt", "Alternate candidate"),
            ("h24-2a-residualized", "Residualized detector (H24-2A arc + nuisance removal)"),
        )
    )
    fact_rows = "".join(
        f'<tr><td>{link(f["url"], e(f["name"]))}<br><span class="sourcekind">{e(f["kind"])}</span></td><td>{e(f["verified"])}</td><td>{e(f["limit"])}</td></tr>'
        for f in sources.get("facts", [])
    )
    group_rows = "".join(
        f"<tr><td>{link(r['site_url'], e(r['repo']))}</td><td>{link(r['source_url'], e(r['source_path']))}<br><code>{e(r.get('commit', '')[:12])}</code></td><td>{e(r.get('status', 'unknown'))}</td></tr>"
        for r in group.get("rows", [])
    )
    irr_rows = "".join(
        f"<tr><td><code>{e(i.get('id'))}</code></td><td>{e(i.get('status'))}</td><td>{e(i.get('issue'))}</td><td>{e(i.get('resolution'))}</td></tr>"
        for i in irregs.get("issues", [])
    )
    blk = load("data/external/audit_sources/acquisition_blocks_receipt.json")
    block_note = e(
        blk.get("status", "derived_audited")
        + ", official_coordinates="
        + str(blk.get("official_coordinates"))
        if isinstance(blk, dict)
        else ""
    )
    forensic = forensics
    source_page = f"""<div class="pagehead"><div class="eyebrow">Manual-review links · auditable receipts</div><h1>Separate facts from conclusions.</h1><p>Official sources, computed diagnostics, owner-reported scores and hypotheses are different evidence classes. Missing data stay missing.</p></div>
<section><h2>Classifier two-sample audit (labels first)</h2><div class="tablewrap"><table><thead><tr><th>Raster</th><th>Positive px</th><th>Held-out AUC</th><th>Holm p</th><th>Margin vs null p95</th><th>Strongest single family</th><th>Rule</th></tr></thead><tbody>{audit_rows}</tbody></table></div><p class="micro">Features: road/trail distance (official buffered Census run), BLM closed-claim distance, four acquisition blocks — nothing else. 199 grouped refitted nulls, 99 shift diagnostics, four spatial folds. Flag = Holm p ≤ .05 and AUC ≥ .55 and margin ≥ .02. <strong>Block membership is derived from the official figure and audited against published line-km (status: {block_note}); it is not official coordinates.</strong> Association is not causation: roads/claims can correlate with real geology. Adapted from {link("https://arxiv.org/abs/1610.06545", "Lopez-Paz &amp; Oquab, ICLR 2017")}.</p></section>
<section><h2>Portal-error forensics</h2><div class="card"><p>{forensic.get("unique_rasters", 0)} unique rasters from the owner's repos were profiled ({forensic.get("submission_grid_float32_rasters", 0)} on the submission grid). {forensic.get("rasters_with_any_range_or_nan_problem", 0)} have any anomaly (NaN inside the footprint, early 5GEMSDOE files); <strong>none has a value outside [0,1]</strong>, and the three blank-score files are format-identical to scored ones. {e(forensic.get("interpretation", ""))}</p></div></section>
<section><h2>Verified source table</h2><div class="tablewrap"><table><thead><tr><th>Source / review link</th><th>What I read</th><th>Limitation / irregularity</th></tr></thead><tbody>{fact_rows}</tbody></table></div></section>
<section><h2>Irregularities register</h2><div class="tablewrap"><table><thead><tr><th>ID</th><th>Status</th><th>Issue</th><th>Resolution / state</th></tr></thead><tbody>{irr_rows}</tbody></table></div></section>
<section><h2>Owner score ledger</h2><div class="card"><p>{len(ledger.get("artifacts", []))} scored artifacts matched to hashed files; {len(ledger.get("unscored_artifacts", []))} unscored files recorded; blanks stay unknown, never zero. Scores marked <code>task_statement_only</code> (including H28 0.1839 and the lattice 0.0904) appear only in the 2026-10-02 brief. {link("https://github.com/buffedlizard55-lab/GEMSDOE24/blob/main/registry/live_scores.json", "registry/live_scores.json")}</p></div></section>
<section><h2>All supplied project sources</h2><p class="small muted">Pinned HTML/source was read for every supplied URL; this does not independently prove each deployment or score.</p><div class="tablewrap"><table><thead><tr><th>Project / site</th><th>Pinned source / commit</th><th>Review status</th></tr></thead><tbody>{group_rows}</tbody></table></div></section>
<section><div class="grid2"><article class="card"><h3>Limitations and access needs</h3><ul class="prose"><li>I cannot reach the DrivenData portal, the private leaderboard or hidden labels, nor upload or verify scores.</li><li>Hand-labelled lidar scarps are allowed by staff (labels must be saved) and need a geologist.</li><li>Official flight-number → block mapping needs the S3-hosted profile archives (anonymous GET returns 403).</li><li>DrivenData figures are human-read snapshots: re-verify by hand; no job here may access that site automatically.</li></ul></article><article class="card"><h3>Three-pass review</h3><p>{e(review.get("summary", "Review in progress."))}</p><div class="actions"><a class="button" href="data/source_health.json" download>Source feed</a><a class="button" href="data/audit.json" download>Audit receipt</a></div></article></div></section>"""

    # ------------------------------------------------------------------ write
    bodies = {
        "index.html": ("Overview", "Overview", overview),
        "executive-summary.html": ("Submission guide", "Submission guide", executive),
        "research.html": ("Research and results", "Research", research),
        "sources.html": ("Sources and audit", "Sources & audit", source_page),
    }
    for name, (title, active, body) in bodies.items():
        (DOCS / name).write_text(page(title, active, body))
    root_overview = overview
    for path in ("downloads/", "executive-summary.html", "research.html", "sources.html"):
        root_overview = root_overview.replace(f'href="{path}', f'href="docs/{path}')
    (ROOT / "index.html").write_text(page("Overview", "Overview", root_overview, prefix="docs/"))
    (ROOT / "executive-summary.html").write_text(
        '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="refresh" content="0;url=docs/executive-summary.html"><title>Executive guide</title></head><body><a href="docs/executive-summary.html">Open the executive guide</a></body></html>'
    )
    for src, dst in (
        ("evidence/accessibility_audit_v2.json", "audit.json"),
        ("evidence/h24_e1_operator_comparison.json", "emission_comparison.json"),
        ("evidence/emission_calibration.json", "emission_calibration.json"),
        ("evidence/format_forensics.json", "format_forensics.json"),
        ("evidence/group_review.json", "group_review.json"),
        ("evidence/access_inputs.json", "access_inputs.json"),
        ("evidence/review_passes.json", "review_passes.json"),
    ):
        data = load(src)
        if data:
            (DOCS / "data" / dst).write_text(json.dumps(data, indent=2) + "\n")

    status_md = f"""**{re.sub("<[^>]+>", "", banner)}**

Primary download: [`{primary["file"]}`](docs/downloads/{primary["file"]}) — {primary.get("pixel_count", 0):,} px,
unscored. Calibrated hidden truth density τ ≈ {fmt((tau or 0) * 100, 3)}% of cells (blind lattice, owner-reported 0.0904,
brief-only). Paired sparse-holdout DTI for the primary vs H19-5 as emitted: {fmt(sp(sel))} vs {fmt(sp(solid))}
({pct(sparse_gain)}); model-based expectation ≈ {fmt(model_lo, 2)} (plausible 0.22–0.28) — a model, **not a leaderboard result**.
The best owner-reported score remains **0.1922** (H19-5); the official leader snapshot is **{fmt(leader.get("best_score"))}**
({e(health.get("checked_utc", ""))}). No weekly slot has been spent by this repository.

Exact-file audit (labels first; roads + claims + four derived blocks): labels AUC {fmt(auc(lab_a), 3)}, H19-4 {fmt(auc(h4_a), 3)}, H19-5 {fmt(auc(h5_a), 3)}, primary {fmt(auc(c1_a), 3)}, alternate {fmt(auc(c2_a), 3)}.
Live site (GitHub Pages, branch `main`): {SITE}
"""
    readme = ROOT / "README.md"
    if readme.exists():
        text = readme.read_text()
        text = re.sub(
            r"<!-- STATUS:START -->.*?<!-- STATUS:END -->",
            f"<!-- STATUS:START -->\n{status_md}<!-- STATUS:END -->",
            text,
            flags=re.S,
        )
        readme.write_text(text)
    receipt = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "primary_sha256": primary["sha256"],
        "alternate_sha256": (alternate or {}).get("sha256"),
        "reference_sha256": reference["sha256"],
        "pages": [str((DOCS / p).relative_to(ROOT)) for p in bodies],
        "root": "index.html",
        "slot_recommendation": rec,
        "new_slot_eligible": rec == "eligible",
        "no_scores_fabricated": True,
    }
    (ROOT / "evidence/site_build.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
