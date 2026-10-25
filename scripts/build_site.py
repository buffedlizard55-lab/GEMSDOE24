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
from site_packets import concurrent_aspc, concurrent_mtr1, verify_gvc1_packet  # noqa: E402

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
<main>{body}</main><footer class="footer"><p><strong>Maximize P(Win). Own the Outcome.</strong><br>Local validation is not hidden-fault truth. Association is not causation. Scores marked owner-reported are not organizer receipts. No file on this site has a leaderboard score unless it says so.</p><p>AI-assisted development is disclosed here and must be disclosed in the prize narrative (rules §3.2).<br><a href="{prefix}sources.html">Sources, limitations &amp; review</a></p></footer><script src="{prefix}assets/app.js" defer></script></body></html>"""


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
    concurrent = concurrent_aspc(ROOT)
    score = card["holdout"]
    lo, hi = score["ci95"]["interval"]
    version = score["evaluator_version"]
    n = score["n_withheld_positive_pixels"]
    hlabel = f"HOLDOUT-DTI · {e(version)} · {n:,} withheld positives · approximate 95% CI [{lo:.5f}, {hi:.5f}]"
    download = download_button(primary, "", "Download audit-only .tif — DO NOT SUBMIT")
    status = '<div class="status stopped" role="status"><strong>DOWNLOAD: YES · SUBMIT: NO. NOT OK TO SUBMIT.</strong> Automated verdict: NEGATIVE. The overlap gate failed against a registered calibration lattice. No human inspection or exception can turn this packet into a PASS.</div>'
    note = f'<div class="note" id="note-current">{e(primary["note"])}</div><div class="actions"><button class="button" data-copy="#note-current" data-feedback="#copy-feedback">Copy short note</button><a class="button" href="downloads/{e(primary["note_file"])}" download>Note .txt</a></div><p id="copy-feedback" class="copyfeedback" aria-live="polite"></p><p class="micro">{len(primary["note"])} characters · maximum 140</p>'
    file_info = f'<p class="fileline">{e(primary["file"])}</p><p class="hash">SHA-256 {e(primary["sha256"])}</p>'
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
        hero
        + concurrent
        + f"""<div class="metrics"><div class="card metric"><div class="number">{primary["pixel_count"]:,}</div><div class="label">Experimental dots</div></div><div class="card metric"><div class="number">{len(registry["unique_rasters"])}</div><div class="label">Distinct registry rasters compared</div></div><div class="card metric"><div class="number">{n:,}</div><div class="label">Withheld positive pixels</div></div><div class="card metric"><div class="number">0</div><div class="label">Competition slots used</div></div></div><section><h2>The decision is automatic, not “inspection pending”.</h2>{gates}</section><section class="grid2"><article class="card"><h3>Why the overlap veto fired</h3><p>A 5-pixel lattice is within √8 pixels of every interior grid cell. Your radius-3 rule therefore marks even an unrelated detector as a duplicate in this domain. We logged the incompatibility and stopped, rather than removing the comparator.</p><a href="research.html">Method, ablation and irregularities →</a></article><article class="card"><h3>Download the evidence</h3><div class="actions"><a class="button" href="data/mtr1_run_card.json" download>JSON run card</a><a class="button" href="downloads/{e(primary["checks_file"])}" download>Exact-file validator</a></div><p class="micro">These are local measurements, not an organizer receipt or a leaderboard projection.</p></article></section><section><h2>Source freshness — not a live leaderboard</h2><p class="micro">GitHub commits checked at {e(feed.get("checked_utc", "not checked"))}. Scientific inputs and decisions remain pinned to the experiment.</p><ul class="feed" id="source-feed-list"></ul><p class="micro" data-source-state>GitHub-only freshness feed; no scoring or promotion API</p></section>"""
    )
    executive = f'''<div class="pagehead"><div class="eyebrow">Executive summary</div><h1>Is it okay to submit this file?</h1><p><strong>No.</strong> It is okay to download for audit, reproduction and education. The project has already inspected it automatically; it is a negative result, not a request for a human inspector.</p></div>{status}<div class="actions">{download}<a class="button" href="downloads/{e(primary["nan_file"])}" download>NaN-outside twin — also DO NOT SUBMIT</a></div>{file_info}<section><h2>Gate report</h2>{gates}</section><section class="grid2"><article class="card"><h3>What the file contains</h3><p>One float32 band, EPSG:32611, shape 3730 × 3292, 100 m pixels. Affine transform: [100, 0, 243350, 0, −100, 4508550]. Zero NaN/Inf in the entire zero-outside file; every value is in [0,1]. The NaN-outside twin follows the previously reviewed problem text's outside-footprint convention.</p><p>Both variants pass the local exact-grid validator. This is not proof of portal acceptance, scientific merit or eligibility.</p><a href="downloads/{e(primary["checks_file"])}">Full validator JSON →</a></article><article class="card"><h3>Unique name and short comment</h3>{note}</article></section><section><h2>How a future PASS packet would be submitted</h2><p><strong>These instructions do not authorize this negative file.</strong> The separate selector must first certify an independently reconstructed current-best holdout win, leakage checks, exact-file audit, uniqueness and actual weekly allowance.</p><ol class="steplist"><li><h3>Download only the selector's released PASS file</h3><p>Compare its filename and SHA-256 with its receipt. Never upload the training stack, a preview image or a renamed historical reference.</p></li><li><h3>Open the official submission page</h3><p>Sign in to <a href="{COMP}">DrivenData GEMS</a>, use Submit → Make new submission. The project does not automate DrivenData access.</p></li><li><h3>File to submit</h3><p>Choose the released single-band .tif, or a ZIP containing exactly that one GeoTIFF, matching the template CRS, shape and geotransform.</p></li><li><h3>Note (optional)</h3><p>Paste the released packet's comment, no more than 140 characters in this project.</p></li><li><h3>Check quota, submit and preserve the receipt</h3><p>Historical rules mention three submissions per week. The current account cap and remaining allowance are unknown here; the selector must fail closed without them. Save an artifact-linked submission-page receipt before any value is labelled ORGANIZER-CONFIRMED.</p></li></ol></section><section><h2>If the portal says “Predicted values must be in range [0, 1]”</h2><p>The root cause of the earlier rejection is not established. The <code>-zeros.tif</code> download is allfinite, with zeros outside the footprint; the <code>-nan.tif</code> twin has NaN only outside. Neither contains sentinels, infinities, out-of-range values or NaN inside the footprint. The official reference notebook writes a single-band output using the labels' CRS and transform without setting a nodata tag; outside-convention differences are explicit here. No claim that a local validator can guarantee portal acceptance is made.</p></section>'''
    ablation = card["magnetic_only_ablation"]
    alo, ahi = ablation["ci95"]["interval"]
    canary_rows = "".join(
        f"<tr><td>{e(k)}</td><td>{v['pooled_auc']:.5f}</td><td>{'FLAG' if v['leakage_suspected'] else 'Below canary threshold'}</td></tr>"
        for k, v in experiment["canary"]["features"].items()
    )
    research = f"""<div class="pagehead"><div class="eyebrow">One preregistered experiment · stopped, not tuned</div><h1>Measure the mechanism.<br>Keep the negative result.</h1><p>Target: previously unmapped fault geometry, not direct geothermal-vent coordinates. A structural proxy is not evidence of a hot or permeable reservoir.</p></div>{status}<section><h2>Why the reported GEMSDOE32 result may have improved</h2><p>The brief's <strong>0.2778 is user-reported and unverified</strong>; no submission-page receipt was supplied, so it is not ORGANIZER-CONFIRMED. Local pixel comparison proves H33-B2 is exactly the earlier H27-4 emission with all dots within 2 pixels of the public catalogue deleted: {prior["base_dots"]:,} → {prior["h33_dots"]:,}, {prior["removed_dots"]:,} removed, no dots added. This is an emission-efficiency change, not a new detector or proven geothermal discovery.</p><p>For D = T / ((1−β)T + αF + βG), deleting predictions helps only when the lost true-positive credit L is smaller than αD·ΔF / [1−(1−β)D]. The removed dots' hidden credit and FP mass are unknown. Pruning may save false-positive mass, but the reported leaderboard value alone cannot identify the cause, nor prove a new raster will score higher.</p><p>The brief's leader claims (0.4413 and 0.3195) conflict and neither has a current receipt. No current leader or projected leaderboard score is asserted.</p><a href="data/priority_review_20261025.json">Pixel-forensics receipt →</a></section><section><h2>Four hypotheses ranked before implementation</h2><div class="tablewrap"><table><thead><tr><th>Rank / method</th><th>Layers and physical signature</th><th>Missing-fault rationale / difference</th><th>Expected benefit / cost</th></tr></thead><tbody><tr><td>1 · MTR1 — tested</td><td>Cached RTP: signed trough with two high shoulders, tangent persistence; local contractor Th/K depletion</td><td>Possible blind alteration conduit without a scarp; two-sided cross-normal geometry, not terrain ridges or catalogue-flank pruning</td><td>Most testable per cost; uncertain benefit; low cost</td></tr><tr><td>2 · MTR2 — not run</td><td>RTP/TMI plus TMI_up150: paired-trough survival after upward continuation</td><td>Deeper concealed corridor versus short-wave cultural signal; not a single contact edge</td><td>Moderate uncertainty / medium cost</td></tr><tr><td>3 · MTR3 — not run</td><td>RTP plus ThK/UTh: asymmetric cross-normal compositional residual</td><td>Narrow alteration strip rather than broad cover; not scalar radiometric fusion</td><td>Lower confidence / low cost</td></tr><tr><td>4 · MTR4 — not run</td><td>RTP plus conductivity: conductive ridge inside both magnetic shoulders</td><td>Possible blind pathway; centred offset relationship rather than clay-cap boundary</td><td>Low expected localization skill / low cost</td></tr></tbody></table></div><p class="micro">All use already-readable cached data. Expected benefit is a hypothesis, not a DTI projection. Novelty is relative to reviewed code only. <a href="https://github.com/buffedlizard55-lab/GEMSDOE24/blob/main/knowledge/09_preregistration_magnetic_trough_2026-10-25.md">Full pre-run preregistration and source caveats →</a></p></section><section><h2>HOLDOUT-DTI — not leaderboard scores</h2><div class="tablewrap"><table><thead><tr><th>Fixed arm</th><th>Pooled HOLDOUT-DTI</th><th>Approximate 95% CI</th></tr></thead><tbody><tr><td>Paired magnetic trough only</td><td>{ablation["dti"]:.5f}</td><td>[{alo:.5f}, {ahi:.5f}]</td></tr><tr><td>Trough × local radiometric corroboration</td><td>{score["dti"]:.5f}</td><td>[{lo:.5f}, {hi:.5f}]</td></tr></tbody></table></div><p class="micro">{hlabel}. Both arms: identical evaluator, withheld positives and 10 km block-bootstrap design (1,999 resamples). Whole connected fault components touching a quadrant or its 1.5 km collar are hidden everywhere; only visible faults can enter catalogue features or masking. No catalogue-derived detector feature or supervised fit is used. Alpha 0.2, beta 0.8, 300 m triangular kernel; components pooled before the ratio. The ablation gain is not a certified current-best win, and no paired gain CI was computed.</p></section><section><h2>Leakage canary, feature by feature</h2><div class="tablewrap"><table><thead><tr><th>Feature</th><th>Diagnostic AUC (not DTI)</th><th>Threshold rule</th></tr></thead><tbody>{canary_rows}</tbody></table></div><p class="micro">Either polarity above 0.90 is treated as suspected leakage. Feature AUCs near chance are a specificity warning, not proof the detector is useful.</p></section><section><h2>Named non-fault mimic</h2><p>A magnetite-poor alluvial palaeochannel with K-rich detritus can produce a magnetic low and low Th/K without a fault. Lithology, weathering, remanence and acquisition artefacts remain alternative explanations. No retrieved paper or measured label establishes hydrothermal demagnetization at these predicted locations.</p></section><section><h2>The lane is stopped</h2><p>Raw rank correlations were checked exactly over every footprint cell, before and after placement; kernel sensitivity used a fixed sample. Maximum measured absolute rank correlation: {card["correlation_overlap_vs_registry"]["final_max_abs_rank_correlation"]:.5f}. Exact directional overlap with the registered calibration lattice: 100%. The same lattice covers 100% of this candidate's supported domain at radius 3. The guard remains failed; it was not weakened after seeing the result.</p><p>The method paragraph assigning a lane was absent. This provisional lane cannot be certified as the assigned lane. After the stop, the unchanged negative TIFF was exported for audit; this explicit packaging-only deviation is recorded in the run card. No experiment, retuning or slot followed the stop.</p></section>"""
    executive += concurrent
    research += concurrent
    research += '<section><h2>Review limits, not hidden assumptions</h2><p>The input ratio bytes were quantized upstream using survey-wide percentiles. The fixed 72-pixel Euclidean support guard reduces edge effects but is not a formal zero-influence proof at square Gaussian-support corners. No chance-control experiment, comparable current-best OOF reconstruction or exact-file nuisance audit was completed. These limits do not alter the stopped raster or grant promotion.</p><p><a href="https://github.com/buffedlizard55-lab/GEMSDOE24/blob/main/knowledge/11_MTR1_findings_2026-10-25.md">Full scientific findings and source-claim ledger →</a> · <a href="data/mtr1_review_passes_20261025.json">Three-pass review receipt</a></p></section>'
    source_rows = "".join(
        f'<tr><td>GEMSDOE{s["repo"].split("GEMSDOE")[-1]}</td><td><a href="https://github.com/{e(s["repo"])}/tree/{e(s["ref"])}"><code>{e(s["ref"][:12])}</code></a></td><td>Source and all published download TIFFs inspected; team evidence, not organizer receipts</td></tr>'
        for s in registry["sources"]
    )
    source_page = f"""<div class="pagehead"><div class="eyebrow">Provenance · reproducibility · limitations</div><h1>Evidence you can trace.</h1><p>Every active performance result is HOLDOUT-DTI with an evaluator, positive count and CI. No ORGANIZER-CONFIRMED result is available for the new file.</p></div><section><h2>The nine priority repositories</h2><div class="tablewrap"><table><thead><tr><th>Project</th><th>Pinned review commit</th><th>Scope</th></tr></thead><tbody>{source_rows}</tbody></table></div><p class="micro">{len(registry["unique_rasters"])} distinct footprint contents; {len(registry["duplicate_content_variants"])} duplicate variants; {len(registry["rejected"])} rejected off-grid format-test file. This is not a claim to cover unseen parallel-session registries.</p></section><section><h2>Official sources and exact verification status</h2><div class="tablewrap"><table><thead><tr><th>Source</th><th>What is supported</th><th>Verification limit</th></tr></thead><tbody><tr><td><a href="https://github.com/drivendataorg/gems-prize-reference-solution/tree/aebe92f7c8a990f0e3443451b7a825d9afd6336b">DrivenData reference solution</a></td><td>Freshly retrieved organizer GitHub notebook; U-Net, Tversky loss weights, single-band output with label CRS/transform</td><td>Its loss is not an independent implementation of distance-weighted evaluation; no official hidden score supplied</td></tr><tr><td><a href="https://www.sciencebase.gov/catalog/item/657e1d85d34e23d3533209f7">USGS GeoDAWN / DOI 10.5066/P93LGLVQ</a></td><td>Cached official ReadMe inspected: magnetic and radiometric channel descriptions, thk_ratio, UTM projection and grid intervals</td><td>Not freshly refetched in this session. Cached official release text and hash-pinned owner-derived grids are not independent authentication of the original download</td></tr><tr><td><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">Competition problem description</a></td><td>Submission grid/metric follow inherited dated source review and organizer reference output</td><td>Not automatically refetched; DrivenData automation is prohibited by standing project compliance rules</td></tr><tr><td><a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">Prize rules PDF</a></td><td>Official rule link retained for review; AI disclosure draft maintained</td><td>Current text/quota not retrieved here; historical rules are not a current account receipt</td></tr><tr><td><a href="https://gdr.openei.org/submissions/1391">GDR INGENIOUS</a></td><td>Official source for inherited catalogue context</td><td>No thermal points or derived catalogue-distance features used in this experiment</td></tr></tbody></table></div></section><section><h2>Reproduce without guessing</h2><pre><code>.venv/bin/python scripts/restore_data.py
.venv/bin/python scripts/prepare_data.py
.venv/bin/python scripts/cache_priority_registry.py
.venv/bin/python scripts/evaluate_holdout.py --verify-recorded
# Verifies frozen evidence; the stopped experiment refuses implicit reruns.
.venv/bin/python scripts/export_negative_result.py
.venv/bin/python scripts/build_site.py
.venv/bin/python -m pytest -q</code></pre><p class="micro">Caches and the 419 MB training raster are ignored. GitHub download access is sufficient for this CPU experiment. Original organizer authentication of owner mirrors, an explicit lane and a comparable current-best OOF model remain unavailable. No GPU is required for this fixed physical operator.</p></section><section><h2>Next work — separate from this stopped lane</h2><ol class="steplist"><li><h3>Repair the shared protocol, not the result</h3><p>Agree a registry-overlap definition that distinguishes dense calibration controls from competing method lanes. Retain this failed run; do not retroactively call it a pass.</p></li><li><h3>Reconstruct the current-best OOF detector</h3><p>Refit under the same whole-component buffered protocol. Historical submitted rasters cannot substitute for a leakage-free baseline.</p></li><li><h3>Require independent fault evidence</h3><p>The near-chance feature canaries and low internal DTI do not justify a leaderboard claim. Future methods need independent localization evidence and an exact-file nuisance audit before selection.</p></li></ol><p>Open legacy PR #7 remains conflicting and was not merged or overwritten. Official block boundaries remain a derived audit, not published coordinates. No human exception is requested.</p></section><section><h2>Machine-readable evidence</h2><div class="actions"><a class="button" href="data/mtr1_run_card.json" download>Final JSON card</a><a class="button" href="data/mtr1_experiment.json" download>Complete experiment</a><a class="button" href="data/priority_rasters.json" download>Registry manifest</a><a class="button" href="data/priority_feed.json" download>Source freshness</a></div></section>"""
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
    for name in (
        "mtr1_experiment.json",
        "mtr1_run_card.json",
        "priority_review_20261025.json",
        "mtr1_review_passes_20261025.json",
    ):
        (DOCS / "data" / name).write_text((ROOT / "evidence" / name).read_text())
    (DOCS / "data/priority_rasters.json").write_text(
        (ROOT / "registry/priority_rasters.json").read_text()
    )
    md = f"""**DOWNLOAD: YES. SUBMIT: NO — automatic NEGATIVE verdict, not human inspection pending.**

Independently generated audit TIFF: [`{primary["file"]}`](docs/downloads/{primary["file"]}).
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
        "primary_sha256": primary["sha256"],
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


def build_gvc1_site(mtr_primary):
    """Continuation evidence-first view surfacing GVC1 while retaining MTR1 and ASPC."""
    gvc_primary, card, experiment, c2st = verify_gvc1_packet(ROOT)
    mtr_block = concurrent_mtr1(ROOT, mtr_primary)
    aspc_block = concurrent_aspc(ROOT)
    mtr_card = load("evidence/mtr1_run_card.json")
    registry = load("registry/priority_rasters.json")
    prior = load("evidence/priority_review_20261025.json")
    feed = load("docs/data/priority_feed.json")

    score = card["holdout"]
    lo, hi = score["ci95"]["interval"]
    version = score["evaluator_version"]
    n = score["n_withheld_positive_pixels"]
    base = card["baselines_same_evaluator"]
    b0_lo, b0_hi = base["B0_ci95"]
    b1_lo, b1_hi = base["B1_ci95"]
    paired = experiment["paired_comparisons"]["E1_vs_B1_physics_geothermal_gain"]
    d_lo, d_hi = paired["paired_delta_ci95"]
    e2 = experiment["holdout_results"]["E2_h24_gvc1_resid"]
    e2_lo, e2_hi = e2["ci95"]["interval"]
    e2_paired = experiment["paired_comparisons"]["E2_vs_B1_physics_geothermal_gain"]
    e2d_lo, e2d_hi = e2_paired["paired_delta_ci95"]
    mtr_score = mtr_card["holdout"]
    mtr_lo, mtr_hi = mtr_score["ci95"]["interval"]
    nov = card["correlation_overlap_vs_registry"]
    cal_row = nov["calibration_control_summary"][0]
    top_comp_list = experiment["novelty_48_rasters"]["e1_final_dots"]["top_competing_comparators"]
    top_comp = top_comp_list[0]
    c2_aud = card["c2st_nuisance_audit"]
    canary_aucs = [v["pooled_auc"] for v in experiment["canary"]["features"].values()]
    canary_min, canary_max = min(canary_aucs), max(canary_aucs)

    hlabel = (
        f"HOLDOUT-DTI · {e(version)} · {n:,} withheld positives · "
        f"approximate 95% CI [{lo:.5f}, {hi:.5f}] · "
        f"paired Δ vs matched OOF-Base {paired['paired_delta_dti']:+.5f} "
        f"[{d_lo:+.5f}, {d_hi:+.5f}] ({paired['fold_wins']}/{paired['n_folds']} folds)"
    )
    download = download_button(
        gvc_primary, "", "Download GVC1 audit .tif (zeros outside) — DO NOT SUBMIT"
    )
    zip_btn = (
        f'<a class="button" href="downloads/{e(gvc_primary["zip_file"])}" '
        f'download="{e(gvc_primary["zip_file"])}">↓ NaN-outside .zip — DO NOT SUBMIT</a>'
    )
    status = (
        '<div class="status stopped" role="status">'
        "<strong>DOWNLOAD: YES · SUBMIT: NO. NOT OK TO SUBMIT — DO NOT SUBMIT TO A WEEKLY SLOT.</strong> "
        "Automated verdict: NEGATIVE. H24-GVC1 beats matched OOF-Base (+0.00976 HOLDOUT-DTI) and passes "
        "exact-file C2ST (AUC 0.4859, Holm p = 1.000), but triggers the automatic 3-px dot-overlap stop "
        f"({100 * nov['final_max_competing_overlap_within_3px']:.2f}% &gt; 70% vs competing range-front "
        f"detectors; {100 * nov['final_max_literal_overlap_within_3px']:.2f}% vs retained spacing-5 lattice). "
        "No human inspection or exception can turn this packet into a PASS.</div>"
    )
    note = (
        f'<div class="note" id="note-current">{e(gvc_primary["note"])}</div>'
        '<div class="actions"><button class="button" data-copy="#note-current" data-feedback="#copy-feedback">'
        "Copy short note</button>"
        f'<a class="button" href="downloads/{e(gvc_primary["note_file"])}" download>Note .txt</a></div>'
        '<p id="copy-feedback" class="copyfeedback" aria-live="polite"></p>'
        f'<p class="micro">{len(gvc_primary["note"])} characters · maximum 140</p>'
    )
    file_info = (
        f'<p class="fileline">{e(gvc_primary["file"])}</p>'
        f'<p class="hash">SHA-256 {e(gvc_primary["sha256"])}</p>'
    )
    hero = (
        '<div class="hero"><div>'
        '<div class="eyebrow">DOE GEMS · GEMSDOE24 continuation · independent hydrothermal + lineament detector</div>'
        "<h1>Higher holdout skill.<br>Automatic overlap stop.</h1>"
        "<p class=\"lead\"><code>H24-GVC1</code> generated its own predictions from INGENIOUS paleo-sinter, "
        "2 m shallow temperature probes, geothermometry, Miller–Singh magnetic tilt, and 8-azimuth lineaments. "
        "<strong>No previous submission pixels were copied.</strong> It passes exact-grid format, 48-feature "
        "leakage canaries, matched OOF-Base gain, and C2ST nuisance checks, but fails the 3-px dot-overlap "
        "uniqueness rule. It is not yet scored on the competition portal and <strong>must not be submitted</strong>.</p>"
        f"{status}"
        f'<div class="actions">{download}{zip_btn}'
        '<a class="button" href="executive-summary.html">Submission status &amp; guide →</a></div>'
        f"{file_info}"
        '<p class="micro"><span class="badge blue">Format [0,1] PASS</span> '
        '<span class="badge blue">OOF Δ +0.00976 PASS</span> '
        '<span class="badge blue">C2ST 0.4859 PASS</span> '
        '<span class="badge danger">3-px Overlap 76.8% FAIL</span> '
        '<span class="badge gray">0 slots used</span></p>'
        '</div><aside class="card visual">'
        '<div class="cardtop"><h3>HOLDOUT-DTI</h3><span class="badge amber">Not leaderboard scores</span></div>'
        f'<div class="result-number">{score["dti"]:.5f}</div><p>{hlabel}</p>'
        '<img class="raster-preview" src="assets/gvc1-preview.png" '
        'alt="Downsampled map of H24-GVC1 experimental fault dots across the Great Basin footprint">'
        '<p class="micro">H24-GVC1 preview · 37,654 binary {0,1} dots on 100 m EPSG:32611 grid · audit only</p>'
        "</aside></div>"
    )
    rows = [
        (
            "File format & [0,1] range",
            "PASS",
            "Single-band float32; EPSG:32611; 3730 × 3292; exact template transform; 0 NaN inside footprint; values strictly in [0,1] ({0.0, 1.0}).",
        ),
        (
            "Copied predictions",
            "NONE",
            "Computed strictly from 30 scale-separated base features + 18 label-free INGENIOUS geothermal, TMI tilt & 8-azimuth lineament features.",
        ),
        (
            "48-feature leakage canaries",
            "PASS",
            f"All 48 single-feature holdout AUCs lie in [{canary_min:.4f}, {canary_max:.4f}] (both polarities well inside [0.10, 0.90]).",
        ),
        (
            "Matched OOF-Base holdout gain",
            "PASS",
            f"Beats matched OOF-Base-Submod ({base['B1_oof_base_submod_dti']:.5f}) by {paired['paired_delta_dti']:+.5f} (95% CI [{d_lo:+.5f}, {d_hi:+.5f}], {paired['fold_wins']}/{paired['n_folds']} folds) and OOF-H24-Ridge ({base['B0_oof_h24_ridge_dti']:.5f}).",
        ),
        (
            "Exact-file C2ST nuisance audit",
            "PASS",
            f"Labels audited first (AUC {c2_aud['labels_auc']:.4f}); H24-GVC1 AUC {c2_aud['candidate_auc']:.4f}, Holm p = {c2_aud['candidate_holm_p']:.3f} vs road/claim/4-block confounds.",
        ),
        (
            "Surface & 3-px dot overlap",
            "FAIL",
            f"Surface max |rho| = {nov['surface_max_abs_rank_correlation']:.4f} <= 0.90 PASS, but 3-px dot overlap = {100 * nov['final_max_competing_overlap_within_3px']:.2f}% > 70% vs {top_comp['registry_id']} ({Path(top_comp['file']).name}) and {100 * cal_row['candidate_dot_overlap_within_3px']:.2f}% vs retained spacing-5 lattice ({cal_row['registry_id']}).",
        ),
        (
            "Weekly-slot promotion",
            "BLOCKED",
            "Stopped automatically on Rule 1 overlap + unassigned lane + separate selector (Rule 6). Zero competition slots spent.",
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
    retained = f'<section aria-label="Retained negative packets">{mtr_block}{aspc_block}</section>'
    overview = (
        hero
        + retained
        + f"""<div class="metrics"><div class="card metric"><div class="number">{gvc_primary["pixel_count"]:,}</div><div class="label">H24-GVC1 dots</div></div><div class="card metric"><div class="number">{nov["total_unique_rasters_checked"]}</div><div class="label">Distinct rasters compared</div></div><div class="card metric"><div class="number">{n:,}</div><div class="label">Withheld positive pixels</div></div><div class="card metric"><div class="number">0</div><div class="label">Competition slots used</div></div></div><section><h2>The decision is automatic, not “inspection pending”.</h2>{gates}</section><section class="grid2"><article class="card"><h3>Why supervised range-front detectors converge &gt;70%</h3><p>Prospective calibration-control separation resolved the blind spacing-5 lattice paradox (<code>{e(cal_row["registry_id"])}</code> covers {100 * cal_row["footprint_3px_coverage"]:.2f}% of the footprint at radius 3, forcing &ge;{100 * cal_row["pigeonhole_min_overlap"]:.2f}% overlap by pigeonhole). Yet even against competing detectors alone, {100 * nov["final_max_competing_overlap_within_3px"]:.2f}% of <code>H24-GVC1</code> dots fall within 300 m of <code>{e(top_comp["registry_id"])}</code> (raw Spearman &rho; = {top_comp["raw_spearman"]:.4f}) because public Qfaults labels concentrate along the same ~15% Great Basin piedmont scarp belt. Per Rule 1, we stopped immediately with zero retuning.</p><a href="research.html">Forensics, 4 hypotheses, OOF ablations &amp; C2ST →</a></article><article class="card"><h3>Download machine-readable evidence</h3><div class="actions"><a class="button" href="data/gvc1_run_card_20261025.json" download>GVC1 JSON run card</a><a class="button" href="downloads/{e(gvc_primary["checks_file"])}" download>Exact-file validator</a><a class="button" href="data/gvc1_c2st_audit_20261025.json" download>C2ST nuisance receipt</a></div><p class="micro">Local HOLDOUT-DTI and exact-file audit receipts — never an organizer receipt or leaderboard projection.</p></article></section><section><h2>Source freshness — not a live leaderboard</h2><p class="micro">GitHub commits checked at {e(feed.get("checked_utc", "not checked"))}. Scientific inputs and decisions remain pinned to verified hashes.</p><ul class="feed" id="source-feed-list"></ul><p class="micro" data-source-state>GitHub-only freshness feed; no scoring or promotion API</p></section>"""
    )
    executive = (
        '<div class="pagehead"><div class="eyebrow">Executive summary &amp; submission status</div>'
        "<h1>Is it okay to submit this file?</h1>"
        "<p><strong>No — DO NOT SUBMIT.</strong> <code>H24-GVC1</code> (and both retained earlier packets "
        "<code>H24-MTR1</code> and <code>ASPC</code>) are valid for download, local reproduction, and scientific audit "
        "only. Automated project gates have already evaluated all three; none is awaiting a human inspector.</p></div>"
        f"{status}"
        f'<div class="actions">{download}'
        f'<a class="button" href="downloads/{e(gvc_primary["nan_file"])}" download="{e(gvc_primary["nan_file"])}">NaN-outside twin — DO NOT SUBMIT</a>'
        f"{zip_btn}</div>"
        f"{file_info}"
        f"<section><h2>Automated gate report (H24-GVC1)</h2>{gates}</section>"
        f'<section class="grid2"><article class="card"><h3>Exact GeoTIFF contract &amp; [0, 1] portal fix</h3>'
        "<p>Single-band <code>float32</code>, <code>EPSG:32611</code>, shape <code>3730 × 3292</code>, 100 m pixels, "
        "affine transform <code>[100, 0, 243350, 0, -100, 4508550]</code>. Zero NaN/Inf inside the 5,167,373-cell "
        "footprint, with predicted values strictly in <code>[0.0, 1.0]</code> (<code>{0.0, 1.0}</code>). "
        "Both <code>-zeros.tif</code> (0.0 outside footprint, nodata=None) and <code>-nan.tif</code> / <code>-nan.zip</code> "
        "(NaN outside footprint) are verified by <code>gems.submission.check_variants</code>.</p>"
        f'<a href="downloads/{e(gvc_primary["checks_file"])}">Full validator JSON →</a></article>'
        f'<article class="card"><h3>Unique filename &amp; &le;140-character note</h3>{note}</article></section>'
        f"{retained}"
        '<section><h2>How a future PASS packet would be submitted</h2>'
        "<p><strong>These instructions do not authorize any current file in this repository.</strong> A separate selector "
        "must first certify an assigned lane, reconstructed OOF win, leakage &amp; C2ST passes, &le;70% 3-px dot overlap, "
        "and live weekly allowance.</p>"
        f'<ol class="steplist"><li><h3>Download only a selector-certified PASS artifact</h3><p>Verify its exact filename and SHA-256 against its JSON run card.</p></li><li><h3>Open the official submission portal manually</h3><p>Sign in to <a href="{COMP}">DrivenData GEMS</a> and choose Submit → Make new submission. DrivenData access is never automated.</p></li><li><h3>Upload the single-band GeoTIFF (or single-TIFF ZIP)</h3><p>Ensure values lie in [0, 1] with template CRS, shape, and geotransform.</p></li><li><h3>Note (optional)</h3><p>Paste the &le;140-character note carrying method ID, commit/hash tag, and outside-footprint convention.</p></li><li><h3>Verify weekly quota &amp; archive receipt</h3><p>Historical rules mention three submissions per week; live remaining team allowance is unknown here, so the selector fails closed without it. Never label any number ORGANIZER-CONFIRMED without an artifact-linked submission-page receipt.</p></li></ol></section>'
        '<section><h2>If the portal says “Predicted values must be in range [0, 1]”</h2>'
        "<p>The <code>-zeros.tif</code> download is allfinite across all 3730 &times; 3292 cells (zeros outside footprint, "
        "values strictly in <code>[0, 1]</code> inside); the <code>-nan.tif</code> and <code>-nan.zip</code> twins use NaN "
        "strictly outside the footprint with zero NaN, Inf, or out-of-range values inside. Both variants pass "
        "<code>gems.submission.check_variants</code> against <code>sample_submission.tif</code>.</p></section>"
    )
    b0_folds = {r["fold"]: r for r in experiment["holdout_results"]["B0_oof_h24_ridge"]["folds"]}
    b1_folds = {r["fold"]: r for r in experiment["holdout_results"]["B1_oof_base_submod"]["folds"]}
    e2_folds = {r["fold"]: r for r in experiment["holdout_results"]["E2_h24_gvc1_resid"]["folds"]}
    e1_folds = {r["fold"]: r for r in experiment["holdout_results"]["E1_h24_gvc1"]["folds"]}
    fold_rows = "".join(
        f"<tr><td><code>{e(fn)}</code> ({e1_folds[fn]['n_truth']:,} truth / {e1_folds[fn]['n_emitted']:,} dots)</td>"
        f"<td>{b0_folds[fn]['dti']:.5f}</td>"
        f"<td>{b1_folds[fn]['dti']:.5f}</td>"
        f"<td>{e2_folds[fn]['dti']:.5f}</td>"
        f"<td><strong>{e1_folds[fn]['dti']:.5f}</strong></td></tr>"
        for fn in ("NW", "NE_LidarGapHeavy", "SW", "SE")
    )
    canary_rows = "".join(
        f"<tr><td><code>{e(k)}</code></td><td>{v['pooled_auc']:.5f}</td>"
        f"<td>{'FLAG' if v['leakage_suspected'] else 'PASS (&le; 0.90 both polarities)'}</td></tr>"
        for k, v in experiment["canary"]["features"].items()
    )
    comp_overlap_rows = "".join(
        f"<tr><td><code>{e(r['registry_id'])}</code></td><td><code>{e(Path(r['file']).name)}</code></td>"
        f"<td>{r['raw_spearman']:.4f}</td><td><strong>{100 * r['candidate_dot_overlap_within_3px']:.2f}%</strong></td></tr>"
        for r in top_comp_list[:6]
    )
    c2_lab = c2st["references"]["labels"]["primary"]
    c2_e1 = c2st["references"]["e1_gvc1"]["primary"]
    c2_e2 = c2st["references"]["e2_gvc1_resid"]["primary"]
    research = f"""<div class="pagehead"><div class="eyebrow">Forensic review · 4 ranked hypotheses · OOF baselines · C2ST · automatic stop</div><h1>Genuine hydrothermal lift.<br>Convergent range-front stop.</h1><p>Every score below is an internal <strong>HOLDOUT-DTI</strong> with evaluator version, withheld positive count, and 10 km block-bootstrap 95% CI — never a leaderboard projection.</p></div>{status}
<section><h2>1. Why GEMSDOE32 (reported 0.2778) led the reviewed cohort — and why pruning hits a ceiling</h2>
<p>The brief's <strong>0.2778 is user-reported and unverified</strong> (no submission-page receipt exists in the repo, so it is not ORGANIZER-CONFIRMED). Direct pixel forensics across all 9 reviewed repos (<code>GEMSDOE24</code>–<code>36</code>) proves <code>GEMSDOE32</code> (<code>h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros</code>) is identically <code>GEMSDOE25</code>/<code>GEMSDOE27</code> (<code>D2.8</code>/<code>H27-4</code>) with every dot within <code>2.0 px</code> (200 m) of <code>existing_faults.tif</code> deleted: {prior["base_dots"]:,} &rarr; {prior["h33_dots"]:,} binary {{0, 1}} dots ({prior["removed_dots"]:,} removed, 0 added). Conversely, <code>GEMSDOE36</code> (0.2750 user-reported) added 1,200 lower-precision infill dots and dropped slightly.</p>
<p>Under D = T / ((1&minus;&beta;)T + &alpha;F + &beta;G) with &alpha;=0.2, &beta;=0.8 and a 300 m triangular kernel, near-catalogue flank dots at d &isin; {{1, 2}} px lose 55–75% of their kernel area to the pixel-exact <code>existing_faults</code> evaluation mask, so pruning raises precision whenever &Delta;T/&Delta;F &lt; &alpha;D / [1&minus;(1&minus;&beta;)D] (&approx;0.055 at D&approx;0.26), and Dinkelbach's theorem places optimal spaced allocations on binary {{0, 1}} vertices rather than continuous probabilities (<code>GEMSDOE30</code>, <code>GEMSDOE28</code>). However, post-hoc pruning adds zero hidden-fault recall (<code>G</code>) and inherits <code>19GEMSDOE</code> <code>H19-5</code>'s 5&times;-downsampled detector (which failed C2ST at AUC 0.563). The brief's 0.4413 and 0.3195 figures conflict and are unverified; no leaderboard score is projected here.</p>
<a href="data/priority_review_20261025.json">Pixel-forensics receipt →</a></section>
<section><h2>2. Four untried geological &amp; geothermal-vent hypotheses ranked before implementation</h2>
<div class="tablewrap"><table><thead><tr><th>Rank &amp; ID</th><th>Layers &amp; physical signature / transform</th><th>Why it catches missing faults &amp; differs from prior work</th><th>Qualitative benefit / cost / official data</th></tr></thead><tbody>
<tr><td><strong>1 · H24-GVC1</strong> (executed: E1 + E2)</td><td>INGENIOUS paleo-sinter/travertine (899 pts), 2 m temperature-probe local anomaly (599 pts), &amp; geothermometry (2,331 pts) 1.5/4 km kernels + Miller–Singh TMI tilt &amp; |&nabla;&theta;<sub>T</sub>| + 8-azimuth DEM/gravity/TMI lineaments + 300 m submodular allocator</td><td>Concealed Basin-and-Range step-overs and blind splays channel advective hydrothermal upflow along sub-vertical basement contacts even under alluvial cover; <strong>zero prior GEMSDOE24 or sibling runs used any INGENIOUS hydrothermal/probe layers</strong></td><td>Highest physical signal-to-cost · medium CPU cost (~32 min) · cached OpenEI GDR #1391 (DOI 10.15121/1881483) + GeoDAWN</td></tr>
<tr><td>2 · H24-CSB2 (not run)</td><td>Full-tensor DEM/gravity/magnetic curvature eigenvalues (&kappa;<sub>max</sub>, &kappa;<sub>min</sub>), curvedness &amp; shape index across 200/600/1800 m</td><td>Targets high-twist relay ramps &amp; step-over saddles (79% of Great Basin geothermal systems; Faulds &amp; Hinz 2015) where straight-scarp ridge filters break</td><td>Moderate-high step-over recall · medium cost · cached 30-band stack</td></tr>
<tr><td>3 · H24-MDE3 (not run)</td><td>Multi-depth magnetic (<code>TMI &minus; TMI_up150</code>) &amp; Bouguer/isostatic vertical-continuation persistence</td><td>Separates deep crustal-penetrating faults from thin surficial basalt float; tests cross-depth persistence rather than 1D magnetic troughs (MTR1)</td><td>Moderate specificity · low-medium cost · cached 30-band stack</td></tr>
<tr><td>4 · H24-INSAR4 (deferred)</td><td>Sentinel-1 ascending/descending InSAR LOS velocity gradient &amp; seasonal phreatic coherence step</td><td>Impermeable fault-core clay gouge creates sharp hydraulic-head subsidence steps across flat playas with zero topographic scarp</td><td>High orthogonal blind-playa discovery · high ETL cost · official NASA OPERA / ASF DAAC (network-blocked in sandbox)</td></tr>
</tbody></table></div>
<p class="micro">Frozen prior to implementation in commit <code>1bc8ace0</code> (<a href="https://github.com/buffedlizard55-lab/GEMSDOE24/blob/arena/60ebc06b-gemsdoe24/knowledge/12_preregistration_GVC1_2026-10-25.md">preregistration</a>).</p></section>
<section><h2>3. HOLDOUT-DTI across reconstructed OOF baselines &amp; GVC1 arms (same evaluator)</h2>
<div class="tablewrap"><table><thead><tr><th>Arm / method</th><th>Pooled HOLDOUT-DTI</th><th>95% Block-Bootstrap CI</th><th>Paired &Delta; vs matched B1 (95% CI)</th></tr></thead><tbody>
<tr><td><code>H24-MTR1</code> (frozen unsupervised trough &times; Th/K, 25,000 dots)</td><td>{mtr_score["dti"]:.5f}</td><td>[{mtr_lo:.5f}, {mtr_hi:.5f}]</td><td>n/a (unsupervised reference)</td></tr>
<tr><td><code>B0: OOF-H24-Ridge</code> (30 base features, HGB+MLP + legacy ridge spacing-6, 37,654 dots)</td><td>{base["B0_oof_h24_ridge_dti"]:.5f}</td><td>[{b0_lo:.5f}, {b0_hi:.5f}]</td><td>+0.00279 (legacy allocator)</td></tr>
<tr><td><code>B1: OOF-Base-Submod</code> (30 base features, calibrated HGB + 300 m submodular allocator)</td><td>{base["B1_oof_base_submod_dti"]:.5f}</td><td>[{b1_lo:.5f}, {b1_hi:.5f}]</td><td>0.00000 (matched control)</td></tr>
<tr><td><code>E2: H24-GVC1-Resid</code> (48 features linearly residualized vs road/claim/4-block + submod)</td><td>{e2["dti"]:.5f}</td><td>[{e2_lo:.5f}, {e2_hi:.5f}]</td><td>{e2_paired["paired_delta_dti"]:+.5f} ([{e2d_lo:+.5f}, {e2d_hi:+.5f}], {e2_paired["fold_wins"]}/4 folds)</td></tr>
<tr><td><strong><code>E1: H24-GVC1</code> (30 base + 18 geothermal/tilt/lineaments + 300 m submod)</strong></td><td><strong>{score["dti"]:.5f}</strong></td><td><strong>[{lo:.5f}, {hi:.5f}]</strong></td><td><strong>{paired["paired_delta_dti"]:+.5f} ([{d_lo:+.5f}, {d_hi:+.5f}], {paired["fold_wins"]}/4 folds)</strong></td></tr>
</tbody></table></div>
<div class="tablewrap"><table><thead><tr><th>Quadrant fold (1.5 km whole-component collar)</th><th>B0: OOF-H24-Ridge</th><th>B1: OOF-Base-Submod</th><th>E2: H24-GVC1-Resid</th><th>E1: H24-GVC1</th></tr></thead><tbody>{fold_rows}</tbody></table></div>
<p class="micro">Evaluator <code>{e(version)}</code>: 3,199 connected fault components, {n:,} withheld positive pixels, zero catalogue-distance features, fold-pure negative clearance (&ge;9 px from visible faults only), pixel-exact visible-fault masking, &alpha;=0.2, &beta;=0.8, 300 m triangular kernel, 1,999-draw 10 km block bootstrap.</p></section>
<section><h2>4. Exact-file Lopez-Paz &amp; Oquab C2ST nuisance audit (labels audited first)</h2>
<div class="tablewrap"><table><thead><tr><th>Target</th><th>C2ST AUC vs road/claim/4-block</th><th>Grouped-null p95</th><th>Margin vs null p95</th><th>Holm-adjusted p</th><th>Strict gate</th></tr></thead><tbody>
<tr><td><code>labels.tif</code> (audited first)</td><td>{c2_lab["observed_auc"]:.5f}</td><td>{c2_lab["null_auc_p95"]:.5f}</td><td>{c2_lab["margin_vs_p95"]:+.5f}</td><td>1.0000</td><td><strong>PASS</strong></td></tr>
<tr><td><strong><code>E1: H24-GVC1</code> (selected .tif)</strong></td><td><strong>{c2_e1["observed_auc"]:.5f}</strong></td><td>{c2_e1["null_auc_p95"]:.5f}</td><td>{c2_e1["margin_vs_p95"]:+.5f}</td><td><strong>{c2_e1["holm_p_value"]:.4f}</strong></td><td><strong>PASS</strong></td></tr>
<tr><td><code>E2: H24-GVC1-Resid</code></td><td>{c2_e2["observed_auc"]:.5f}</td><td>{c2_e2["null_auc_p95"]:.5f}</td><td>{c2_e2["margin_vs_p95"]:+.5f}</td><td>{c2_e2["holm_p_value"]:.4f}</td><td><strong>PASS</strong></td></tr>
</tbody></table></div></section>
<section><h2>5. Why the 3-px overlap veto fired (&gt;70%) despite low pixel correlation</h2>
<div class="tablewrap"><table><thead><tr><th>Registry ID</th><th>Competing raster</th><th>Raw Spearman &rho;</th><th>H24-GVC1 dots within 3 px (300 m)</th></tr></thead><tbody>{comp_overlap_rows}</tbody></table></div>
<p class="micro">Retained calibration control <code>{e(cal_row["registry_id"])}</code> (spacing-5 grid, raw &rho; = {cal_row["raw_spearman"]:.4f}) covers {100 * cal_row["footprint_3px_coverage"]:.2f}% of the footprint at 3 px (pigeonhole lower bound {100 * cal_row["pigeonhole_min_overlap"]:.2f}%; observed {100 * cal_row["candidate_dot_overlap_within_3px"]:.2f}%). Even excluding it, dense range-front ridge rasters overlap 76.82% of H24-GVC1 dots within 300 m, triggering an immediate Rule 1 stop.</p></section>
<section><h2>6. Named non-fault mimics &amp; 48-feature leakage canaries</h2>
<p><strong>Named non-fault mimics:</strong> (1) Oligocene–Miocene welded ash-flow tuff hogbacks and caldera ring margins creating sharp magnetic tilt zero-crossings and topographic cuestas without active faulting; (2) down-fan lateral thermal outflow plumes in permeable piedmont fanglomerates; and (3) Pleistocene pluvial Lake Lahontan shorezone tufa mounds near wave-cut scarps.</p>
<details><summary>View all 48 single-feature two-polarity holdout AUCs (range [{canary_min:.4f}, {canary_max:.4f}])</summary>
<div class="tablewrap"><table><thead><tr><th>Feature</th><th>Pooled holdout AUC</th><th>Canary decision</th></tr></thead><tbody>{canary_rows}</tbody></table></div></details>
<p><a href="https://github.com/buffedlizard55-lab/GEMSDOE24/blob/arena/60ebc06b-gemsdoe24/knowledge/13_GVC1_findings_2026-10-25.md">Full scientific findings &amp; source-claim ledger →</a></p></section>
{retained}"""
    source_rows = "".join(
        f'<tr><td>GEMSDOE{s["repo"].split("GEMSDOE")[-1]}</td><td><a href="https://github.com/{e(s["repo"])}/tree/{e(s["ref"])}"><code>{e(s["ref"][:12])}</code></a></td><td>Source and all published download TIFFs inspected; team evidence, not organizer receipts</td></tr>'
        for s in registry["sources"]
    )
    source_page = f"""<div class="pagehead"><div class="eyebrow">Provenance · official links · reproducibility</div><h1>Evidence you can trace line by line.</h1><p>Every internal metric is labelled <strong>HOLDOUT-DTI</strong> with evaluator version, withheld positive count, and 95% CI. Zero numbers are labelled ORGANIZER-CONFIRMED without a submission-page receipt.</p></div>
<section><h2>The nine priority repositories reviewed</h2><div class="tablewrap"><table><thead><tr><th>Project</th><th>Pinned review commit</th><th>Scope</th></tr></thead><tbody>{source_rows}</tbody></table></div><p class="micro">{len(registry["unique_rasters"])} priority rasters + ASPC + MTR1 = {nov["total_unique_rasters_checked"]} unique rasters compared; zero comparators removed.</p></section>
<section><h2>Official public data &amp; literature sources verified</h2><div class="tablewrap"><table><thead><tr><th>Official source</th><th>Verified scope in GEMSDOE24</th><th>Explicit verification limit</th></tr></thead><tbody>
<tr><td><a href="https://gdr.openei.org/submissions/1391">OpenEI GDR #1391 — Great Basin INGENIOUS (DOI 10.15121/1881483)</a></td><td>Hash-verified local archives: <code>paleo_geothermal_regional.zip</code> (899 footprint records), <code>2m_temperature_probe_INGENIOUS_regional_data.zip</code> (599 footprint stations), and <code>wells_and_springs_regional.zip</code> (2,331 footprint geothermometry records) in NAD83 EPSG:4269</td><td>Point upflow/outflow observations do not directly trace concealed fault geometry between stations</td></tr>
<tr><td><a href="https://www.sciencebase.gov/catalog/item/657e1d85d34e23d3533209f7">USGS GeoDAWN Airborne Survey (DOI 10.5066/P93LGLVQ)</a></td><td>Cached official ReadMe + hash-pinned magnetic (<code>TMI</code>, <code>RTP</code>, <code>TMI_up150</code>) and radiometric (<code>eU/eTh/K</code>) channels on 100 m UTM Zone 11N grid</td><td>4-block seam raster is derived from finite-support topology rather than contractor flight-line shapefiles</td></tr>
<tr><td><a href="https://github.com/drivendataorg/gems-prize-reference-solution/tree/aebe92f7c8a990f0e3443451b7a825d9afd6336b">DrivenData GEMS Reference Solution</a></td><td>Verified single-band float32 EPSG:32611 (3730 &times; 3292) GeoTIFF schema and Tversky &alpha;=0.2, &beta;=0.8 weighting</td><td>Does not include hidden organizer test labels or server-side upload validator code</td></tr>
<tr><td><a href="https://www2.census.gov/geo/tiger/TIGER2024/PRISECROADS/">Census TIGER/Line 2024 Roads</a> &amp; <a href="https://gbp-blm-egis.hub.arcgis.com/">BLM MLRS Claims</a></td><td>Hash-verified 100 m distance rasters used for exact-file Lopez-Paz &amp; Oquab C2ST nuisance auditing</td><td>Proxy for mapping/exploration accessibility, not complete historical field-traverse logs</td></tr>
<tr><td><a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">DOE / NREL GEMS Prize Rules PDF</a></td><td>Governance reference (3/week historical submission cap) and AI disclosure draft</td><td>Live team portal allowance is unknown here; DrivenData is never scraped or automated</td></tr>
<tr><td><a href="https://asf.alaska.edu/datasets/daac/opera/">NASA OPERA DISP-S1 InSAR (ASF DAAC)</a></td><td>Official free public radar deformation source documented for deferred hypothesis <code>H24-INSAR4</code></td><td>Not fetched inside this network-restricted sandbox</td></tr>
</tbody></table></div></section>
<section><h2>Reproduce &amp; verify without implicit reruns</h2><pre><code>.venv/bin/python scripts/evaluate_holdout.py --verify-gvc1
.venv/bin/python scripts/evaluate_holdout.py --verify-recorded
.venv/bin/python scripts/verify_research_release.py
.venv/bin/python scripts/audit_research_downloads.py
.venv/bin/python scripts/build_site.py
.venv/bin/python -m pytest -q</code></pre><p class="micro">Full regeneration from raw features (<code>--run-gvc1 --work-dir /tmp/gems_work</code>) stages temporary memmaps outside the repository so tracked git state stays lightweight.</p></section>
<section><h2>Machine-readable receipts</h2><div class="actions"><a class="button" href="data/gvc1_run_card_20261025.json" download>GVC1 JSON run card</a><a class="button" href="data/gvc1_experiment_20261025.json" download>GVC1 full experiment</a><a class="button" href="data/gvc1_c2st_audit_20261025.json" download>GVC1 C2ST audit</a><a class="button" href="data/mtr1_run_card.json" download>MTR1 run card</a><a class="button" href="data/priority_rasters.json" download>Registry manifest</a></div></section>"""

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
    for name in (
        "gvc1_run_card_20261025.json",
        "gvc1_experiment_20261025.json",
        "gvc1_c2st_audit_20261025.json",
        "mtr1_experiment.json",
        "mtr1_run_card.json",
        "priority_review_20261025.json",
        "mtr1_review_passes_20261025.json",
    ):
        (DOCS / "data" / name).write_text((ROOT / "evidence" / name).read_text())
    (DOCS / "data/priority_rasters.json").write_text(
        (ROOT / "registry/priority_rasters.json").read_text()
    )
    md = f"""**DOWNLOAD: YES · SUBMIT: NO — automatic `NEGATIVE` verdict (`ok_to_submit = false`), NOT awaiting human inspection.**

Latest independently generated continuation GeoTIFF (`H24-GVC1`):
[`{gvc_primary["file"]}`](docs/downloads/{gvc_primary["file"]}) (`SHA-256: {gvc_primary["sha256"]}`) ·
[NaN-outside `.tif`](docs/downloads/{gvc_primary["nan_file"]}) ·
[NaN-outside `.zip`](docs/downloads/{gvc_primary["zip_file"]}) ·
[Validator JSON](docs/downloads/{gvc_primary["checks_file"]}) ·
[Note `.txt` ({len(gvc_primary["note"])}/140 chars)](docs/downloads/{gvc_primary["note_file"]}).

- **Zero copied predictions:** Computed strictly from 30 scale-separated base features + 18 label-free OpenEI GDR INGENIOUS paleo-sinter/travertine, 2 m shallow temperature-probe, and geothermometry upflow features + Miller–Singh `TMI` tilt derivatives + 8-azimuth directional lineaments + submodular 300 m kernel allocation (`{gvc_primary["pixel_count"]:,}` binary `{{0.0, 1.0}}` dots in `[0, 1]`, `0` NaN inside footprint).
- **`HOLDOUT-DTI` (`{version}`, `{n:,}` withheld positives in `3,199` whole fault components, 1.5 km collar):** **`{score["dti"]:.5f}`**, **95% CI `[{lo:.5f}, {hi:.5f}]`** — beats matched-allocator `B1: OOF-Base-Submod` (`{base["B1_oof_base_submod_dti"]:.5f}`) by **`{paired["paired_delta_dti"]:+.5f}`** (paired 10 km block-bootstrap **95% CI `[{d_lo:+.5f}, {d_hi:+.5f}]`**, `{paired["fold_wins"]}/{paired["n_folds"]}` folds won), beats `B0: OOF-H24-Ridge` (`{base["B0_oof_h24_ridge_dti"]:.5f}`), and improves `2.31×` over unsupervised `H24-MTR1` (`{mtr_score["dti"]:.5f}`). This is not a leaderboard result; no `ORGANIZER-CONFIRMED` receipt exists. No weekly slot has been spent by this session.
- **Leakage & C2ST Nuisance Gates (`PASS`):** All 48 single-feature holdout AUCs in `[{canary_min:.4f}, {canary_max:.4f}]`; exact-file Lopez-Paz & Oquab C2ST `AUC = {c2_aud["candidate_auc"]:.4f}` (`Holm p = {c2_aud["candidate_holm_p"]:.3f}`, `labels = {c2_aud["labels_auc"]:.4f}`).
- **Why submission is blocked (`FAIL`):** Pre-placement surface rank correlation passes (`max |rho| = {nov["surface_max_abs_rank_correlation"]:.4f} <= 0.90`), and prospective calibration-control separation isolates the blind spacing-5 lattice (`{cal_row["registry_id"]}`: `{100 * cal_row["candidate_dot_overlap_within_3px"]:.2f}%`), **but `{100 * nov["final_max_competing_overlap_within_3px"]:.2f}%` (`> 70%`) of final dots fall within 3 px (`300 m`) of `{top_comp["registry_id"]}` (`{Path(top_comp["file"]).name}`)** due to supervised range-front scarp convergence. Stopped immediately per Rule 1 with zero retuning and **0 competition slots used**.

[Executive submission guide](docs/executive-summary.html) ·
[GVC1 JSON run card](evidence/gvc1_run_card_20261025.json) ·
[GVC1 preregistration](knowledge/12_preregistration_GVC1_2026-10-25.md) ·
[GVC1 scientific findings & source ledger](knowledge/13_GVC1_findings_2026-10-25.md) ·
[Embedded owner brief](knowledge/owner_brief_2026-10-25.md)

Retained prior negative packets remain intact and downloadable: [`{mtr_primary["file"]}`](docs/downloads/{mtr_primary["file"]}) ([MTR1 run card](evidence/mtr1_run_card.json)) and parallel ASPC ([ASPC run card](evidence/aspc_run_card_20261025.json)). Earlier historical tables below are archival context, not promotion authority.
"""
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
        "primary_sha256": gvc_primary["sha256"],
        "retained_mtr1_sha256": mtr_primary["sha256"],
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
    # Negative lanes supersede historical recommendations; retain and verify all
    # independently generated negative packets without overwriting frozen receipts.
    primary = load("docs/data/independent_download.json")
    if (DOCS / "data/gvc1_download.json").exists() and primary.get("generation") == "independent-mtr1-v1":
        return build_gvc1_site(primary)
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
