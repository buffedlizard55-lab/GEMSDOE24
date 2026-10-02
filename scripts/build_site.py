#!/usr/bin/env python3
"""Generate the small, honest Pages site from verified local evidence.

No binary submission re-ranking, network requests, invented live scores, or
publication claims. The source feed is refreshed separately on hosted CI.
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
from gems.validator import sha256_file  # noqa: E402

DOCS = ROOT / "docs"


def load(path, default=None):
    p = ROOT / path
    if not p.exists():
        return {} if default is None else default
    return json.loads(p.read_text())


def fmt(value, n=5):
    return "pending" if value is None else f"{value:.{n}f}"


def e(value):
    return escape(str(value), quote=True)


def page(title, active, body, prefix=""):
    nav = []
    for name, path in (
        ("Overview", "index.html"),
        ("Research", "research.html"),
        ("Sources & audit", "sources.html"),
        ("Submission guide", "executive-summary.html"),
    ):
        nav.append(
            f'<a class="{"active" if name == active else ""}" href="{prefix}{path}">{name}</a>'
        )
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="Evidence-led DOE GEMS fault prediction: preregistered physical hypotheses, spatial retraining, source audits and validated GeoTIFF reference downloads."><meta name="source-feed" content="{prefix}data/source_health.json"><title>{e(title)} · GEMS DOE 24</title><link rel="stylesheet" href="{prefix}assets/style.css"></head>
<body><header><div class="nav"><a class="brand" href="{prefix}index.html"><span class="mark" aria-hidden="true">∿</span><span>GEMS DOE 24<small>Geologic mapping · evidence first</small></span></a><nav class="navlinks" aria-label="Main navigation">{"".join(nav)}</nav></div></header>
<main>{body}</main><footer class="footer"><p><strong>Maximize P(Win). Own the Outcome.</strong><br>Local validation is not hidden-fault truth. Association is not causation. Reference downloads do not create new leaderboard results. No new weekly submission is recommended.</p><p>AI-assisted development disclosed.<br><a href="{prefix}sources.html">Sources, limitations & review</a><br>Public deployment not verified; GitHub reconnection required.</p></footer><script src="{prefix}assets/app.js" defer></script></body></html>'''


def main():
    download = load("docs/data/download.json")
    if not download:
        raise SystemExit("Create the validated reference bundle first")
    primary = DOCS / "downloads" / download["file"]
    if not primary.exists() or sha256_file(primary) != download["sha256"]:
        raise SystemExit("Website download is missing or differs from its validated checksum")
    experiment = load("evidence/h24_2_experiment.json")
    audit = load("evidence/accessibility_audit_v2.json")
    inputs = load("evidence/access_inputs.json")
    group = load("evidence/group_review.json")
    sources = load("docs/data/sources.json")
    review = load("evidence/review_passes.json")
    results = experiment.get("results", {}) if experiment.get("complete_run") else {}
    history = experiment.get("historical_diagnostics", {}) if experiment.get("complete_run") else {}
    candidate = results.get("physics_arc_residualized", {})
    baseline = results.get("physics_raw", {})
    ds = (
        candidate.get("mean_sparse_dti", 0) - baseline.get("mean_sparse_dti", 0)
        if candidate and baseline
        else None
    )
    dd = (
        candidate.get("mean_dense_dti", 0) - baseline.get("mean_dense_dti", 0)
        if candidate and baseline
        else None
    )
    ref_file = e(download["file"])
    fallback = e(download["fallback"])
    checks_file = e(download["checks_file"])
    note_file = e(download["note_file"])
    size = primary.stat().st_size / (1024**2)
    actions = f'''<div class="actions"><a class="button primary" href="downloads/{ref_file}" download="{ref_file}">↓ Download reference .tif <span>({size:.2f} MiB)</span></a><a class="button" href="executive-summary.html">Submission / executive guide ↗</a></div>'''
    warning = """<div class="status"><strong>No new slot-eligible candidate.</strong> The trained arc candidate improved the matched learning baseline, but did not beat H19 diagnostics. Four-block coordinates and fully buffered road-source coverage remain unresolved. The download is the known H19-5 reference, not a new prediction; do not waste a repeat slot.</div>"""
    local_chart = []
    maxscore = (
        max([v.get("mean_sparse_dti", 0) for v in (*results.values(), *history.values())] or [0.1])
        * 1.15
    )
    for label, row, kind in (
        ("Physics baseline", baseline, ""),
        ("Arc + residualization", candidate, "candidate"),
        ("H19-5 diagnostic", history.get("h19-5", {}), ""),
    ):
        score = row.get("mean_sparse_dti")
        width = 100 * score / maxscore if score is not None and maxscore else 0
        local_chart.append(
            f'<div class="chartrow"><span>{label}</span><div class="track"><div class="bar {kind}" style="width:{width:.3f}%"></div></div><strong>{fmt(score, 4)}</strong></div>'
        )
    hero = f"""<div class="hero"><div><div class="eyebrow">DOE GEMS Prize · auditable fault prediction</div><h1>Better evidence.<br>Before another slot.</h1><p class="lead">A reproducible physical detector, a spatial nuisance audit, and a transparent decision to hold the next submission. Inspect the format-validated group reference in one click.</p>{actions}<p class="micro"><span class="badge blue">H19-5 reference</span> Original <strong>0.1922</strong> reported by the owner · not a new score · float32 / [0,1]</p></div><aside class="card visual"><div class="cardtop"><h3>LOCAL SPARSE-HOLDOUT DTI</h3><span class="badge amber">Not promoted</span></div>{"".join(local_chart)}<p class="legend">Same emitted-raster diagnostic protocol, not a reconstruction of H19’s original OOF fit and <strong>not public leaderboard scores</strong>. New candidate: 16 paired refits across four spatial folds.</p><div class="note small">Paired sparse gain: <strong>{fmt(ds)}</strong><br>Current-best diagnostic veto: <strong>failed</strong></div></aside></div>"""
    overview = (
        hero
        + warning
        + f"""<div class="metrics"><div class="card metric"><div class="number">5.17M × 30</div><div class="label">Prepared footprint descriptors</div><div class="sub">Hash-verified matrix · CPU pipeline</div></div><div class="card metric"><div class="number">16 refits</div><div class="label">Four arms × four regions</div><div class="sub">Whole-component supervised exclusion</div></div><div class="card metric"><div class="number">{fmt(ds, 4)}</div><div class="label">Paired local sparse DTI gain</div><div class="sub">Insufficient to beat current reference</div></div><div class="card metric"><div class="number" data-leader-score>0.3195</div><div class="label">Official leader snapshot</div><div class="sub"><span data-leader-name>DARD</span> · <span data-source-time>2026-10-02</span></div></div></div>
<section><div class="sectionhead"><h2>A complete experiment. An honest stop.</h2><a href="research.html" class="small">Read the methods and results →</a></div><div class="grid3"><article class="card"><div class="tagline">01 · Physical hypothesis</div><h3>Direction-aware contact support</h3><p>Fixed 0.6 / 1.2 / 2.4 km annular gradient descriptors from RTP and detrended elevation, back-projected to edges rather than basin centers. No catalogue-defined centers.</p><p>Contacts and intrusion rims are competing explanations; the descriptor is not a ring-fault proof.</p></article><article class="card"><div class="tagline">02 · Measured nuisances</div><h3>Audit the mapping process</h3><p>Road proximity, real closed-claim distance and the available survey-area indicator only. 199 grouped refitted randomizations and 99 spatial shifts per raster.</p><p>The required four operational block categories are missing; tightly clipped legacy roads also limit boundary certification.</p></article><article class="card"><div class="tagline">03 · Protect the slot</div><h3>Promotion fails closed</h3><p>True refitting, matched holdout gains and an exact-file re-audit precede packaging. Missing current-best OOF reconstruction or required sources cannot become a green gate.</p><p>A correct GeoTIFF format does not make a candidate scientifically eligible.</p></article></div></section>
<section><div class="grid2"><article class="card"><div class="sectionhead"><h2>What ran</h2><span class="badge">Verified locally</span></div><ol class="steplist"><li><h3>Restore and prepare</h3><p>419 MB owner feature bridge verified; 592 MiB label-free descriptor matrix completed.</p></li><li><h3>Preregister, then implement</h3><p>Four distinct physical strategies ranked before new detector implementation.</p></li><li><h3>Audit labels first</h3><p>Available-family label AUC 0.5283: below the .55 meaningful-effect threshold. It is not a full-audit pass.</p></li><li><h3>Refit all four arms</h3><p>Physics / physics+arc, each raw and training-only nuisance-residualized. No outer-fold hyperparameter search.</p></li><li><h3>Inspect the exact prediction</h3><p>126,600 binary-confidence pixels; [0,1] verified; kept experimental and not promoted.</p></li></ol></article><article class="card"><div class="sectionhead"><h2>Source updates</h2><span class="badge gray">Timestamped</span></div><ul class="feed" id="source-feed-list"><li><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">Official leader: 0.3195, DARD</a><small>Official page read · 2026-10-02</small></li><li><a href="sources.html">Two GeoDAWN resolution areas ≠ four operational blocks</a><small>Official USGS report · preserved byte receipt</small></li><li><a href="sources.html">MRDS is not mining claims; BLM closed claims are used</a><small>Official BLM source · quality-filtered geometry</small></li></ul><p class="micro" data-source-state>Latest verified snapshot, not a live scoring API</p><p class="micro">Scheduled feed refresh is implemented, but requires authenticated publication. Public deployment is not currently verified.</p></article></div></section>
<section><div class="callout"><div><h3>One file. One verifiable identity.</h3><p>Exact grid, range and checksum checks, a separate short comment, and no ambiguity about whether the file is new.</p></div><a class="button" href="executive-summary.html">Open the executive guide →</a></div></section>"""
    )
    names = {
        "physics_raw": "Physics · raw",
        "physics_arc_raw": "Physics + arc · raw",
        "physics_residualized": "Physics · residualized",
        "physics_arc_residualized": "Physics + arc · residualized",
    }
    result_rows = []
    for key, row in results.items():
        result_rows.append(
            f'<tr class="{"highlight" if key == "physics_arc_residualized" else ""}"><td>{names[key]}<br><span class="sourcekind">Fresh matched retraining</span></td><td class="num">{fmt(row["mean_dense_dti"])}</td><td class="num">{fmt(row["mean_sparse_dti"])}</td><td>{"Selected in advance, not promoted" if key == "physics_arc_residualized" else "Controlled comparison"}</td></tr>'
        )
    for key, row in history.items():
        result_rows.append(
            f'<tr><td>{key.upper()} as emitted<br><span class="sourcekind">Diagnostic, NOT reconstructed OOF</span></td><td class="num">{fmt(row["mean_dense_dti"])}</td><td class="num">{fmt(row["mean_sparse_dti"])}</td><td>Additional conservative veto</td></tr>'
        )
    research = f"""<div class="pagehead"><div class="eyebrow">Methods · frozen experiment · limitations</div><h1>Physical leverage, not a renamed raster.</h1><p>Four ranked strategies were written before implementation. The first was tested with fresh paired spatial retraining; the outcome was retained even though the current-best veto failed.</p></div>{warning}
<section><h2>Four preregistered hypotheses</h2><div class="tablewrap"><table><thead><tr><th>Rank / hypothesis</th><th>Layers and physical signature</th><th>Missing-fault rationale / distinction</th><th>Expected benefit / cost / readiness</th></tr></thead><tbody><tr><td><strong>1 · H24-2A</strong><br>Annular radial-gradient coherence</td><td>RTP and detrended elevation; 0.6/1.2/2.4 km directional templates and rim backprojection.</td><td>Candidate arcuate contacts that straight continuity filters may fragment; not scalar ring averaging or label-centered buffers.</td><td>Conditional medium / moderate CPU.<br><span class="badge blue">Tested, not promoted</span></td></tr><tr><td><strong>2 · H24-3A</strong><br>Common-resolution contact persistence</td><td>RTP, TMI and gravity; fixed upward-continuation scales, location persistence, no noise-amplifying downward continuation.</td><td>Broader buried contacts may persist when shallow artifacts do not; different from simply summing Gaussian worms.</td><td>Small–medium / low–moderate.<br>Layers staged; flight-height corrections not assumed.</td></tr><tr><td><strong>3 · H24-4A</strong><br>Directional residual variograms</td><td>High-pass RTP/gravity differences at .3/.6/1.2 km in eight directions; anisotropy and cross-field agreement.</td><td>Damage-zone texture without a sharp scarp; variogram range/phase differs from existing structure-tensor coherence.</td><td>Low–medium / moderate.<br>Available layers; not tested.</td></tr><tr><td><strong>4 · H24-6</strong><br>Repeated drainage offsets</td><td>Raw USGS 10 m 3DEP flow networks; repeated signed displacement at independent crossings.</td><td>Kinematic concordance for short strike-slip splays, not a single terrace/road step.</td><td>Uncertain medium / high.<br><span class="badge amber">Deferred: raw coverage unverified</span></td></tr></tbody></table></div><p class="micro">Expected benefits are ordinal judgments, not predicted scores. Novelty is relative to reviewed sources, not unseen competitors.</p></section>
<section><h2>Actual local results</h2><div class="tablewrap"><table><thead><tr><th>Arm / reference</th><th>Dense DTI</th><th>Sparse DTI</th><th>Interpretation</th></tr></thead><tbody>{"".join(result_rows)}</tbody></table></div><p class="micro">Dense = withheld provided traces; sparse = fixed 20% component subset with remaining known pixels masked. This is a catalogue-gap simulation, not private test truth. The legacy road input is tightly clipped; these remain provisional available-input experiments.</p></section>
<section><div class="grid2"><article class="card"><h3>Frozen, paired protocol</h3><ul class="prose"><li>Four geographic quadrants, 1.5 km exclusion collar, entire touching fault components removed from supervised training.</li><li>Same positives/unlabelled negatives, 80-iteration HGB settings and training-only scaler for all four arms.</li><li>Quadratic nuisance splines/interactions fitted on a uniform training-region sample; Ridge alpha 100.</li><li>2.45% maximum ridge budget; positive finite candidates only; deterministic ties, no zero padding.</li><li>Complete predicted halos before NMS; catalogue masking only after NMS, never catalogue-shaped zero-padding artifacts.</li></ul></article><article class="card"><h3>Why the decision is a stop</h3><p>Paired dense/sparse gains are {fmt(dd)} / {fmt(ds)} over physics raw. They satisfy the in-run paired rule, but both H19 diagnostics remain stronger.</p><p>Original H19 OOF caches are absent. Neither diagnostic can certify a same-protocol current-best reconstruction. Acquisition categories and road-source boundary completeness are also unresolved.</p><p><strong>No weekly slot has been spent. No better leaderboard score is claimed.</strong></p></article></div></section>
<section><h2>What explains H19’s strong owner-reported results?</h2><div class="card"><p>The reviewed implementation is heavily topographic: H19-4 gives 92% of its covered-area mixture to the L3/L4 scarp-family terms; H19-5 gives 90%, with altered openness/thermal/tip mixtures, gap CDF matching and a slightly smaller budget. Those coefficients are not measured causal contributions.</p><p>Both outputs are zero on all 60,988 known pixels. Their measured Jaccard is .777234: related but distinct, not statistically independent lines. The .0028 reported score difference cannot tell us which mechanism caused it. Current source comments/register wording and older artifact filenames are not a full source-version reconstruction.</p><p>Thin, accurately localized candidates and restrained false-positive allocation plausibly help the 300 m DTI. The predicted-raster access association and the incomplete source audit prevent a stronger claim of discovery.</p></div></section>
<section><h2>Keep the scientific caveats</h2><ul class="prose"><li>C2ST association does not establish that accessibility caused mapping; roads/claims can correlate with true geology.</li><li>A conditional-mean residualizer can leave nonlinear/variance dependence. AUC below threshold is not proof of no bias.</li><li>Annular support is not unique to ring faults: intrusions, erosion and locally tangent sharp edges can respond.</li><li>Image context can extend about 4.8 km; the 1.5 km collar does not make all physical context independent. Global unlabelled descriptor normalization is transductive.</li><li>Numeric detector settings were fixed in implementation before first fit, but not all were enumerated in the initial preregistration. No hindsight search or silent amendment is claimed.</li><li>Core bridge hashes establish owner-mirror integrity, not independent organizer band authentication.</li></ul></section>"""
    audit_rows = []
    for key, value in audit.get("references", {}).items():
        p = value.get("primary", {})
        adjusted = p.get("holm_p_value") if audit.get("complete_run") else None
        association = (
            value.get("meaningful_access_association_available_features")
            if audit.get("complete_run")
            else None
        )
        status = (
            "Flagged association"
            if association
            else "Below effect rule"
            if association is False
            else "Final adjustment pending"
        )
        audit_rows.append(
            f'<tr><td>{e(key.upper())}</td><td class="num">{fmt(p.get("observed_auc"), 4)}</td><td class="num">{fmt(adjusted, 3)}</td><td class="num">{fmt(p.get("margin_vs_p95"), 4)}</td><td><span class="badge {"amber" if association else "gray"}">{status}</span></td></tr>'
        )
    fact_rows = []
    for fact in sources.get("facts", []):
        fact_rows.append(
            f'<tr><td><a href="{e(fact["url"])}" target="_blank" rel="noopener noreferrer">{e(fact["name"])} ↗</a><br><span class="sourcekind">{e(fact["kind"])}</span></td><td>{e(fact["verified"])}</td><td>{e(fact["limit"])}</td></tr>'
        )
    group_rows = []
    for row in group.get("rows", []):
        group_rows.append(
            f'<tr><td><a href="{e(row["site_url"])}" target="_blank" rel="noopener noreferrer">{e(row["repo"])} ↗</a></td><td><a href="{e(row["source_url"])}" target="_blank" rel="noopener noreferrer">{e(row["source_path"])}</a><br><code>{e(row.get("commit", "")[:12])}</code></td><td>{e(row.get("status", "unknown"))}</td><td>{len(row.get("consulted_files", []))} selected method/registry files</td></tr>'
        )
    missing = "; ".join(inputs.get("missing_required", []) or ["No unresolved families recorded"])
    source_page = f"""<div class="pagehead"><div class="eyebrow">Manual-review links · auditable receipts</div><h1>Separate facts from conclusions.</h1><p>Official sources, measured diagnostics, owner-reported scores and hypotheses are distinct evidence classes. Missing data stay missing; no geological proxy is substituted for a nuisance input.</p></div><div class="status"><strong>Full requested audit: BLOCKED.</strong> Operational block membership is unverified, and the legacy road mirror is tightly clipped. A 20 km seed grid alone cannot repair the missing outside-window road geometries. The buffered official road acquisition workflow is implemented but could not be run after GitHub authentication failed.</div>
<section><h2>Available-input classifier two-sample diagnostics</h2><div class="tablewrap"><table><thead><tr><th>Raster</th><th>Held-out AUC</th><th>Holm p</th><th>Margin vs null p95</th><th>Available-family effect rule</th></tr></thead><tbody>{"".join(audit_rows)}</tbody></table></div><p class="micro">Only road proximity (clipped-source provisional), closed-claim distance and Area1 membership. 199 grouped refits, 99 shift diagnostics, four spatial folds and purged 10 km groups. Flag requires Holm p≤.05, AUC≥.55 and margin≥.02. None of these rows is a full-audit pass without the required sources.</p><p class="micro">AUC adapts the paper’s accuracy-based C2ST. Group exchangeability is an assumption; shifts on this irregular nonstationary footprint are diagnostic, not an exact null. Single-feature ablations are descriptive.</p></section>
<section><h2>Verified source/data table</h2><div class="tablewrap"><table><thead><tr><th>Source / review link</th><th>Checked fact or receipt</th><th>Limitation / irregularity</th></tr></thead><tbody>{"".join(fact_rows)}</tbody></table></div></section>
<section><h2>All 21 supplied project sources</h2><p class="small muted">Pinned HTML/source code was read for every supplied URL. This does not independently prove each current public deployment, score receipt or every unseen method. Unreported scores remain unknown.</p><div class="tablewrap"><table><thead><tr><th>Project / site</th><th>Pinned source / commit</th><th>Review status</th><th>Scope</th></tr></thead><tbody>{"".join(group_rows)}</tbody></table></div></section>
<section><div class="grid2"><article class="card"><h3>What was repaired</h3><ul class="prose"><li>Wrong arXiv id corrected; geometric/geothermal proxies removed from nuisance tests.</li><li>MRDS “claims” substitution retired; complete-ID checked BLM closed claims used.</li><li>Area1/Area2 overwrite fixed; false four-block constants never accepted.</li><li>Known predictions and truth masked in both DTI implementations; adjacent-new-truth regression tests added.</li><li>Empty components, zero budgets, binary re-thinning, arbitrary zero backfill and soft-score hash collisions addressed.</li><li>Training-only refitting replaces post-emission rank reweighting; exact artifact identity gates packaging.</li></ul></article><article class="card"><h3>What remains genuinely unresolved</h3><p>{e(missing)}</p><p>Original H19 OOF reconstruction, source-to-artifact version linkage and independent original-band authentication are not fabricated. Archived legacy reports do not authorize a slot.</p><p>GitHub REST/GraphQL authentication and push failed. Local work is saved, but no PR, merge, buffered-road acquisition or public deployment is claimed.</p><p class="small">The full uncondensed original chat was unavailable; the README preserves the inherited quoted charter and all active requirements available in context.</p></article></div></section>
<section><h2>Three-pass reliability review</h2><div class="card"><p>Pass 1 implements the data→features→audit→paired retraining→prediction pipeline. Pass 2 tests masks, halos, geometry orientation, source windows, empty sets, range checks and gates. Pass 3 rechecks the owner’s acceptance scope and explicitly retains blocked items.</p><p>Current review state: {e(review.get("summary", "Final source/format/reliability checks are being completed."))}</p><div class="actions"><a class="button" href="data/experiment.json" download>Download experiment receipt</a><a class="button" href="data/audit.json" download>Download audit receipt</a><a class="button" href="data/source_health.json" download>Timestamped source feed</a></div></div></section>"""
    note = e(download["note"])
    executive = f"""<div class="pagehead"><div class="eyebrow">Executive summary · exact submission instructions</div><h1>The right file.<br>The right expectation.</h1><p>H19-5 is already above the owner’s .1894 reference. The newly trained arc experiment did not beat the current-best diagnostics, so the visible download remains the old group reference—not a new leaderboard entry.</p>{actions}</div>{warning}
<section><div class="grid2"><article class="card"><h3>Reference download</h3><span class="badge blue">Owner-reported original DTI 0.1922</span><p class="fileline">{ref_file}</p><ul class="checks"><li>Single band · float32 · EPSG:32611</li><li>3730 × 3292 · 100 m grid · exact template transform</li><li>All 5,167,373 in-footprint values finite and in [0,1]</li><li>NaN outside the official footprint</li><li>Scored content unchanged from pinned H19-5</li></ul><p class="micro">The primary is byte-identical to the pinned H19-5 input. The new float32-v2 content id replaces the old binary-v1 id; it does not mean a new prediction.</p></article><article class="card"><h3>Integrity, comment and fallback</h3><p class="small">Full file SHA-256:</p><div id="file-sha" class="note hash">{e(download["sha256"])}</div><p class="micro">Format is verified locally, not portal-upload tested. A green format check does not authorize a slot.</p><div class="actions"><a class="button" href="downloads/{checks_file}" download>Checks JSON</a><a class="button" href="downloads/{e(download["zip"])}" download>Single-TIFF ZIP</a><a class="button" href="downloads/{fallback}" download>Zeros-outside fallback</a></div><p class="micro">Fallback is [0,1] even under strict whole-array readers, but differs from the official NaN convention outside the footprint. Use only if the portal explicitly rejects that convention and organizer guidance permits it.</p></article></div></section>
<section class="narrow"><h2>Do not spend a duplicate weekly slot</h2><ol class="steplist"><li><h3>Check scientific eligibility before opening the portal</h3><p>This reference has no new score. The experimental raster is not promoted. A future candidate must beat the reproduced current-best same-protocol spatial holdout and pass a complete exact-file nuisance audit.</p></li><li><h3>Download the prediction, not a training raster</h3><p>Use the single-band .tif above. Do not submit the 19-band feature stack, raw terrain values, classifier log-odds, a folder or a renamed experimental raster. Confirm the basename and checksum against its receipt.</p></li><li><h3>When an eligible candidate exists, use the official competition portal</h3><p>Sign in to DrivenData, navigate to the GEMS competition’s submissions area, select the .tif (or the permitted single-file ZIP), and paste the matching plain-text note. This repository does not sign in or upload automatically.</p></li><li><h3>If the portal reports “Predicted values must be in range [0, 1]”</h3><p>Stop. Inspect the checks JSON for in-footprint finite values, min/max, one band, float32, CRS and transform. Never repair the upload by arbitrary rescaling after seeing a score. The official NaN-outside primary and separately labelled allfinite fallback are both locally checked.</p></li><li><h3>Record only the organizer’s actual response</h3><p>Associate returned score, upload time and exact SHA-256 in the registry. Unknown or failed uploads stay unknown—not zero and not an invented improvement.</p></li><li><h3>Before final prize selection</h3><p>Follow current limits, final-selection rules, licensed-data obligations and AI/code/narrative disclosure. Confirm deadline ambiguities with the organizer. Another repo/account is not a quota reset.</p></li></ol><a class="button" href="https://www.drivendata.org/competitions/306/competition-doe-gems/" target="_blank" rel="noopener noreferrer">Official competition →</a></section>
<section><h2>Short reference comment</h2><div class="note" id="submission-note">{note}</div><div class="actions" style="margin-top:12px"><button class="button" data-copy="#submission-note" data-feedback="#copy-feedback">Copy plain-text comment</button><a class="button" href="downloads/{note_file}" download>Download comment .txt</a></div><p class="copyfeedback" id="copy-feedback" aria-live="polite"></p><p class="micro">{len(download["note"])} characters; note is separate, never a second ZIP member. Copying it is not a recommendation to upload the reference again.</p></section>
<section><h2>What the result actually says</h2><div class="card"><p>Matched fresh retraining gains are real local computations: {fmt(dd)} dense and {fmt(ds)} sparse over the physics-only learning baseline. The candidate still loses to H19 as-emitted diagnostics, and neither historical raster reconstructs its original OOF model.</p><p>Prediction access association is a robustness warning, not causal proof. Missing four-block geography and buffered road coverage prevent the full requested audit from passing. No new weekly slot has been consumed.</p><p>Next: reconnect GitHub, run the official buffered-road workflow, verify the operational blocks, audit labels first again, refit all arms on corrected sources and reconstruct the current-best OOF reference before reconsidering promotion.</p></div></section>"""
    bodies = {
        "index.html": ("Overview", "Overview", overview),
        "research.html": ("Research and results", "Research", research),
        "sources.html": ("Sources and audit", "Sources & audit", source_page),
        "executive-summary.html": ("Executive submission guide", "Submission guide", executive),
    }
    for name, (title, active, body) in bodies.items():
        (DOCS / name).write_text(page(title, active, body))
    root_overview = overview
    # Root landing and /docs landing both work under a project Pages base path.
    for path in ("downloads/", "executive-summary.html", "research.html", "sources.html"):
        root_overview = root_overview.replace(f'href="{path}', f'href="docs/{path}')
    (ROOT / "index.html").write_text(page("Overview", "Overview", root_overview, prefix="docs/"))
    (ROOT / "executive-summary.html").write_text(
        '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="refresh" content="0;url=docs/executive-summary.html"><title>Executive guide</title></head><body><a href="docs/executive-summary.html">Open the executive guide</a></body></html>'
    )
    (DOCS / "data/experiment.json").write_text(json.dumps(experiment, indent=2) + "\n")
    (DOCS / "data/audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    (DOCS / "data/group_review.json").write_text(json.dumps(group, indent=2) + "\n")
    (DOCS / "data/access_inputs.json").write_text(json.dumps(inputs, indent=2) + "\n")
    (DOCS / "data/review_passes.json").write_text(json.dumps(review, indent=2) + "\n")
    status = f"""**No new slot-eligible candidate; no slot consumed.** H19-5 remains a
format-validated reference with owner-reported original public DTI **0.1922**.
The official leader snapshot is **0.3195** (2026-10-02; not an artifact-linked
score for this repo).

Fresh physics → arc+residualized local dense/sparse DTI:
**{fmt(baseline.get("mean_dense_dti"))} / {fmt(baseline.get("mean_sparse_dti"))} →
{fmt(candidate.get("mean_dense_dti"))} / {fmt(candidate.get("mean_sparse_dti"))}**.
These gains are below H19-4/H19-5 as-emitted diagnostics; original current-best
OOF reconstruction is absent. They do not predict a new leaderboard score.

The full requested audit is **BLOCKED**: four-block geography is unverified and
legacy road clipping leaves boundary coverage uncertified. Official buffered
road acquisition is implemented but its workflow could not run after GitHub
authentication/push failed. Claim distances are official, quality-filtered and
buffered. Exact experimental-raster audit complete: **{audit.get("complete_run", False)}**
(provisional available inputs, never a full-source pass).

Reference: [`{download["file"]}`](docs/downloads/{download["file"]}).
Public PR/merge/deployment are **not claimed**; GitHub reconnection is required.
"""
    readme = ROOT / "README.md"
    if readme.exists():
        text = readme.read_text()
        text = re.sub(
            r"<!-- STATUS:START -->.*?<!-- STATUS:END -->",
            f"<!-- STATUS:START -->\n{status}<!-- STATUS:END -->",
            text,
            flags=re.S,
        )
        readme.write_text(text)
    receipt = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "reference_sha256": download["sha256"],
        "pages": [str((DOCS / p).relative_to(ROOT)) for p in bodies],
        "root": "index.html",
        "publication_verified": False,
        "new_slot_eligible": False,
        "no_scores_fabricated": True,
    }
    (ROOT / "evidence/site_build.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
