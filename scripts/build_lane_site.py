"""Render the current, fail-closed lane result using the existing Pages shell."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from html import escape


def build(root, page):
    docs = root / "docs"
    report = json.loads((root / "evidence/aspc_run_20261025.json").read_text())
    card = json.loads((root / "evidence/aspc_run_card_20261025.json").read_text())
    forensic = json.loads((root / "evidence/peer_forensics_20261025.json").read_text())
    artifact = report.get("artifact")
    e = lambda s: escape(str(s), quote=True)  # noqa: E731
    download = "<p>No TIFF released: the experiment stopped at a required gate.</p>"
    name = None
    if artifact:
        from gems.validator import sha256_file

        name = artifact["file"]
        target = docs / "downloads" / name
        if sha256_file(target) != artifact["sha256"]:
            raise ValueError("Active research artifact differs from its exact-file receipt")
        if card.get("raster_sha256") != artifact["sha256"] or card.get("submission_name") != name:
            raise ValueError("Run card and active artifact identity disagree")
        checks = json.loads(target.with_suffix(".checks.json").read_text())
        if checks.get("sha256") != artifact["sha256"] or checks.get("format_valid") is not True:
            raise ValueError("Active artifact does not have a hash-bound passing format receipt")
        if card["submission_authorized"] or artifact["submission_authorized"]:
            raise ValueError("A research lane cannot grant selector authorization")
        download = f'''<div class="actions"><a class="button primary" href="downloads/{e(name)}" download="{e(name)}">↓ Download unique research .tif — DO NOT SUBMIT</a><a class="button" href="downloads/{e(name.replace(".tif", ".checks.json"))}">Exact-file validator</a></div><p class="fileline">{e(name)}</p><p class="micro">SHA-256: {e(artifact["sha256"])}</p>'''
    twin = report.get("template_convention_companion")
    if twin:
        if sha256_file(docs / "downloads" / twin["file"]) != twin["sha256"]:
            raise ValueError("Template-convention companion checksum mismatch")
        download += f'<p><a href="downloads/{e(twin["file"])}" download="{e(twin["file"])}">Same research predictions, NaN-outside template convention — also DO NOT SUBMIT</a></p>'
    blockers = "".join(f"<li>{e(x)}</li>" for x in report["blockers"])
    status = f"""<div class="status"><strong>NOT OK TO SUBMIT — negative promotion decision.</strong> Automated gates do not authorize a competition slot. Downloading is safe; uploading this file is not recommended.<ul>{blockers}</ul></div>"""
    result = report.get("holdout")
    metrics = "<p>No HOLDOUT-DTI result: stopped before scoring. This is not a zero score.</p>"
    if result:
        ci = result["ci95"]
        delta = result["paired_delta_ci95"]
        metrics = f"""<section class="card"><h2>HOLDOUT-DTI — not leaderboard scores</h2><table><thead><tr><th>Frozen protocol</th><th>Pooled result</th><th>95% spatial-cluster CI</th></tr></thead><tbody><tr><td>ASPC candidate</td><td>{result["value"]:.5f}</td><td>[{ci[0]:.5f}, {ci[1]:.5f}]</td></tr><tr><td>Fixed scarp-amplitude control</td><td>{result["control_value"]:.5f}</td><td>[{result["control_ci95"][0]:.5f}, {result["control_ci95"][1]:.5f}]</td></tr><tr><td>Paired candidate minus control</td><td>{result["paired_delta"]:+.5f}</td><td>[{delta[0]:+.5f}, {delta[1]:+.5f}]</td></tr></tbody></table><p>Evaluator <code>{e(result["evaluator_version"])}</code>; {result["n_withheld_positives"]:,} scored withheld positives. {e(result["ci_method"])}. {e(result["ci_limitations"])}.</p><p>Whole connected fault components hidden with a buffered training exclusion. Catalogue-based features: none. Visible faults masked pixel-exactly. Components pooled before computing DTI; no fold-score average.</p></section>"""
    novelty = card.get("correlation_overlap_vs_registry") or {}
    novelty_text = "No complete uniqueness result; consult run card."
    if novelty.get("distinct_in_reviewed_registry"):
        novelty_text = f"""Distinct in reviewed registry: {novelty["unique_blobs"]} prediction blobs, full-footprint comparisons. Maximum surface Spearman {novelty["maximum_surface_rho"]:.4f}; final-dot Spearman {novelty["maximum_dot_rho"]:.4f}; candidate dots within 3 px of one reference at most {100 * novelty["maximum_candidate_within_3px"]:.2f}%. Thresholds: rho &gt; 0.90 or overlap &gt; 70% stop the run. Not proof of global uniqueness or an assigned parallel lane."""
    overview = f"""<div class="pagehead"><div class="eyebrow">Executive decision · automated evidence gates · 2026-10-25</div><h1>A new TIFF.<br>An honest stop/go decision.</h1><p class="lead">ASPC is a newly generated, label-free antislope/curvature prediction—not a copied submission. It is <strong>not yet scored</strong> by the organizer. The project made the scientific decision automatically: <strong>do not submit</strong>.</p>{download}<p><a href="executive-summary.html">Executive submission guide →</a> · <a href="data/aspc_run_card.json">JSON run card</a> · <a href="data/active_lane.json">Full experiment</a></p></div>{status}{metrics}<section class="card"><h2>Uniqueness is a separate gate</h2><p>{novelty_text}</p><p>No weekly submission slot was spent. Promotion and selection are separate; this lane cannot choose or upload a submission.</p></section><section class="card"><h2>Why the reported GEMSDOE32 result matters</h2><p>The reported 0.2778 is <strong>UNVERIFIED-OWNER-REPORT</strong>, not ORGANIZER-CONFIRMED. Byte-level forensics show its 37,654 dots equal the 44,090-dot D2.8 reference after removing every dot within 200 m of known faults. This is emission pruning, not proof of new geothermal physics. It can improve DTI if the removed false-positive penalty exceeds the cost of lost weighted recall. Hidden labels are unavailable, so the causal explanation and a higher future score are not established.</p><p>The nine-site comparison, four ranked hypotheses and source limits are on <a href="research.html">Research</a>. Geothermal vents are not this competition's label target: fault geometry is. No vent discovery is claimed.</p></section>"""
    guide = f"""<div class="pagehead"><div class="eyebrow">Executive summary · submission procedure</div><h1>Download does not mean submit.</h1><p>The unique ASPC GeoTIFF has a negative promotion verdict. No human inspection is required to decide its current status: the automated decision is <strong>NOT AUTHORIZED</strong>.</p>{download}</div>{status}<section class="card"><h2>What the file checks establish</h2><p>One float32 band, exact template CRS/shape/geotransform, finite values in [0,1] inside the footprint. This allfinite / zeros-outside research file also contains no NaN anywhere. Zero outside is a conservative encoding variant, not independent confirmation of current portal rules. The existing writer was reused and the exact bytes reopened and validated. SHA-256 identifies the downloaded file.</p><p><strong>“Predicted values must be in range [0, 1]”</strong>: this file has no such out-of-range values. The prior portal rejection's cause is unknown; do not invent an explanation or silently clamp a broken model.</p></section><section class="card"><h2>Future eligible-file procedure — blocked for this artifact</h2><ol><li>Generate a fresh candidate on its assigned lane using the cached stack and shared evaluator/writer.</li><li>Pass every feature leakage canary, pre-placement correlation check, final-dot overlap test, matched current-best OOF gate and exact-file scientific audit.</li><li>The separate selector checks the current submission-page weekly cap. Historical rules mention <strong>three submissions</strong>; that is not a verified current cap.</li><li>Only after selector authorization, use <strong>Make new submission</strong> on the organizer portal and choose the exact single-band GeoTIFF (or a ZIP with exactly that TIFF). The project never uploads.</li><li>Use the unique filename and the short comment in <strong>Note (optional)</strong>. Never rename an old raster to claim novelty.</li><li>Record the artifact SHA-256 and an artifact-linked submission-page receipt as ORGANIZER-CONFIRMED. An account leaderboard row alone is not a file receipt.</li></ol></section>"""
    if artifact:
        guide += f"""<section class="card"><h2>Research identifier and short comment</h2><p><code>{e(name)}</code></p><div class="note" id="note-aspc">{e(artifact["note"])}</div><div class="actions"><button class="button" data-copy="#note-aspc" data-feedback="#fb-aspc">Copy research note</button></div><p id="fb-aspc" class="copyfeedback" aria-live="polite"></p><p>{len(artifact["note"])} characters; capped at 140. This note explicitly says not to submit.</p></section>"""
    table_rows = "".join(
        f'''<tr><td><a href="{e(r["url"])}">{e(r["repo"])}</a></td><td>{r["dot_count"]:,}</td><td>{r["within_200m_catalogue"]:,}</td><td>{r["jaccard_h33"]:.4f}</td></tr>'''
        for r in forensic["artifacts"]
    )
    research = f"""<div class="pagehead"><div class="eyebrow">Research · negative results retained</div><h1>One mechanism, one preregistered test.</h1></div>{status}{metrics}<section class="card"><h2>ASPC physical hypothesis</h2><p>Decoded uphill-facing scarp fraction × balanced crest/toe curvature × a channel-bank veto × step response × square-root coherence. All factors come from cached, quantized USGS 3DEP-derived descriptors. No mapped fault location or scored raster enters the ranking. A rotational landslide headscarp or terrace riser can mimic it. The 100 m maxima only co-occur: they do not prove a resolved crest/toe pair.</p><p>Every input and intermediate factor was screened independently for unusually strong holdout AUC; see the full experiment. The raster is an uncalibrated ranking emitted as binary dots, not a calibrated geothermal probability.</p><p><a href="https://github.com/buffedlizard55-lab/GEMSDOE24/blob/main/knowledge/09_preregistered_ASPC_2026-10-25.md">Four ranked hypotheses and preregistration</a> · <a href="data/active_lane.json">Exact canaries, fold counts and registry tests</a></p></section><section class="card"><h2>Nine-site artifact review</h2><p>COMPUTED-ARTIFACT-FORENSICS; these are counts and geometric similarity, not scores. Links point to pinned GitHub revisions. Highest-scoring identity follows the owner's list; no organizer receipts were recovered.</p><table><thead><tr><th>Repository</th><th>Dots</th><th>Within 200 m of catalogue</th><th>Jaccard vs H33-B2</th></tr></thead><tbody>{table_rows}</tbody></table><p>GEMSDOE25 and GEMSDOE30's named references are the same emitted geometry. H33-B2 is exactly the GEMSDOE31 reference after its next 200 m clearance. GEMSDOE36 contains every H33-B2 dot plus additional dots. Those are byte-derived statements—not evidence for thermal conductivity, effective permeability, or hidden-label accuracy.</p></section><section class="card"><h2>Why a better result is possible, but not promised</h2><p>For DTI=T/(T+αF+β(N−T)), pruning loses weighted recall L and removes FP penalty M. It helps only if αTM &gt; L(αF+βN). Catalogue proximity alone does not prove L=0: adjacent hidden fault geometry may be real. New fault evidence must improve held-out precision/recall, not merely reproduce or rename the successful dot family. This lane's fixed hypothesis was tested once; negative evidence is not discarded or tuned into a win.</p><p>Leaderboard figures in the supplied brief conflict. Neither a model projection nor an unverified reported score is a current organizer-confirmed result.</p></section>"""
    sources = f"""<div class="pagehead"><div class="eyebrow">Sources · verification boundaries</div><h1>Traceable claims, explicit unknowns.</h1></div>{status}<section class="card"><table><thead><tr><th>Source</th><th>What was actually verified</th><th>Limitation</th></tr></thead><tbody><tr><td><a href="https://github.com/drivendataorg/gems-prize-reference-solution">Organizer-owned reference solution</a></td><td>Repository/notebook fetched via GitHub: fault target, Tversky training weights, CPU option.</td><td>Does not independently establish the distance-weighted scoring formula.</td></tr><tr><td><a href="https://doi.org/10.5066/P93LGLVQ">USGS GeoDAWN</a> · <a href="https://www.sciencebase.gov/catalog/item/657e1d85d34e23d3533209f7">ScienceBase item</a></td><td>Cached official report/metadata reviewed; cached derived input hashes match repository manifest.</td><td>Official origin of parent survey is not independent authentication of every derived pixel. Direct host outside current network allowlist.</td></tr><tr><td><a href="https://www.usgs.gov/3d-elevation-program">USGS 3DEP</a> · <a href="https://github.com/buffedlizard55-lab/7GEMSDOE/actions/runs/36266555805">Team derivation record</a></td><td>Cached LiDAR band descriptions, quantization, grid and SHA-256 checked.</td><td>Team-derived scarp descriptors, not an official fault inventory; coverage incomplete.</td></tr><tr><td><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">Competition problem/metric</a> · <a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">Prize rules</a> · <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">Leaderboard</a></td><td>Manual-review links retained, not fetched this session. No receipt supplied.</td><td>Project policy forbids automated DrivenData access. Current cap, leaderboard and portal acceptance are unverified.</td></tr></tbody></table></section><section class="card"><h2>Audit files and three-pass review</h2><ul><li><a href="data/aspc_run_card.json">JSON run card</a></li><li><a href="data/active_lane.json">Experiment, leakage canaries and novelty registry results</a></li><li><a href="data/peer_forensics.json">Nine-site byte-level forensics</a></li><li><a href="data/review_20261025.json">Three-pass review record</a></li><li><a href="data/source_health.json">Historical automated source snapshot (check timestamp, not a current leaderboard feed)</a></li></ul><p>No claim of line-by-line scientific certainty, causality, organizer score, discovered vent, or global novelty is made. PR #7 remains unresolved and was not merged into this work. Next useful work: assigned lane, a current-best OOF reconstruction, independent official input provenance and a negative-result-informed new preregistration—not another submission slot.</p></section>"""
    for filename, title, active, body in [
        ("index.html", "Overview", "Overview", overview),
        ("executive-summary.html", "Submission guide", "Submission guide", guide),
        ("research.html", "Research and results", "Research", research),
        ("sources.html", "Sources and audit", "Sources & audit", sources),
    ]:
        body = body.replace(
            "<table>",
            '<div class="tablewrap" role="region" aria-label="Evidence table" tabindex="0"><table>',
        ).replace("</table>", "</table></div>")
        (docs / filename).write_text(page(title, active, body))
    root_body = overview.replace(
        "<table>",
        '<div class="tablewrap" role="region" aria-label="Evidence table" tabindex="0"><table>',
    ).replace("</table>", "</table></div>")
    for path in ("downloads/", "data/", "executive-summary.html", "research.html", "sources.html"):
        root_body = root_body.replace(f'href="{path}', f'href="docs/{path}')
    (root / "index.html").write_text(page("Overview", "Overview", root_body, prefix="docs/"))
    (root / "executive-summary.html").write_text(
        '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta http-equiv="refresh" content="0;url=docs/executive-summary.html"><title>Executive guide</title></head><body><a href="docs/executive-summary.html">Open the executive guide</a></body></html>'
    )
    for obj, dest in [
        (report, "active_lane.json"),
        (card, "aspc_run_card.json"),
        (forensic, "peer_forensics.json"),
    ]:
        (docs / "data" / dest).write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n")
    review = root / "evidence/review_20261025.json"
    (docs / "data/review_20261025.json").write_text(
        review.read_text() if review.exists() else '{"status":"review in progress"}\n'
    )
    md = f"""**NOT OK TO SUBMIT.** ASPC has a negative promotion verdict, not a leaderboard result.

{f"Unique [research TIFF](docs/downloads/{name}) — format-valid, do not upload." if name else "No TIFF released: required gate stopped the experiment."}
[Run card](evidence/aspc_run_card_20261025.json) · [Executive guide](docs/executive-summary.html) · [Preregistered hypotheses](knowledge/09_preregistered_ASPC_2026-10-25.md).

No weekly slot has been spent. No organizer-confirmed score, current-best OOF certification,
assigned parallel lane or selector authorization. Historical results below are not current promotion authority.
"""
    if result:
        md += f"""\n**HOLDOUT-DTI** ({result["evaluator_version"]}, {result["n_withheld_positives"]:,} withheld positives):
{result["value"]:.5f}, 95% CI [{result["ci95"][0]:.5f}, {result["ci95"][1]:.5f}].
Fixed scarp control {result["control_value"]:.5f}; paired Δ {result["paired_delta"]:+.5f},
95% CI [{result["paired_delta_ci95"][0]:+.5f}, {result["paired_delta_ci95"][1]:+.5f}]. These are not leaderboard scores.
"""
    readme = root / "README.md"
    text = re.sub(
        r"<!-- STATUS:START -->.*?<!-- STATUS:END -->",
        "<!-- STATUS:START -->\n" + md + "<!-- STATUS:END -->",
        readme.read_text(),
        flags=re.S,
    )
    readme.write_text(text)
    receipt = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "active_file": name,
        "primary_sha256": artifact["sha256"] if artifact else None,
        "slot_recommendation": "not_recommended",
        "new_slot_eligible": False,
        "submission_authorized": False,
        "no_scores_fabricated": True,
        "root": "index.html",
        "pages": [
            "docs/index.html",
            "docs/executive-summary.html",
            "docs/research.html",
            "docs/sources.html",
        ],
    }
    (root / "evidence/site_build.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))
