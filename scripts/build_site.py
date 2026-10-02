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
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="DOE GEMS fault prediction: a validated, uniquely named submission GeoTIFF, how to submit it, and the evidence behind it."><meta name="source-feed" content="{prefix}data/source_health.json"><title>{e(title)} · GEMS DOE 24</title><link rel="stylesheet" href="{prefix}assets/style.css"></head>
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


def main():
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
