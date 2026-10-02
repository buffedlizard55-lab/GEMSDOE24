#!/usr/bin/env python3
"""Generate the evidence-led static Pages site from current verified receipts.

The only downloadable prediction is the pinned H19-5 reference. Experimental
rasters stay out of the site unless every promotion and exact-file gate passes.
This script does not contact DrivenData or infer scores from participant rows.
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


def load(path: str, default=None):
    p = ROOT / path
    if not p.exists():
        return {} if default is None else default
    return json.loads(p.read_text())


def e(value) -> str:
    return escape(str(value), quote=True)


def fmt(value, n: int = 5) -> str:
    return "not available" if value is None else f"{value:.{n}f}"


def page(title: str, active: str, body: str, prefix: str = "") -> str:
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
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="Evidence-led DOE GEMS fault prediction, accessibility auditing, official data provenance, and a validated reference GeoTIFF."><meta name="source-feed" content="{prefix}data/source_health.json"><title>{e(title)} · GEMS DOE 24</title><link rel="stylesheet" href="{prefix}assets/style.css"></head>
<body><header><div class="nav"><a class="brand" href="{prefix}index.html"><span class="mark" aria-hidden="true">∿</span><span>GEMS DOE 24<small>Geologic mapping · evidence first</small></span></a><nav class="navlinks" aria-label="Main navigation">{"".join(nav)}</nav></div></header>
<main>{body}</main><footer class="footer"><p><strong>Maximize P(Win). Own the Outcome.</strong><br>Local validation is not hidden-fault truth. Association is not causation. A reference download is not a new prediction. No new weekly submission is recommended.</p><p>AI-assisted development disclosed.<br><a href="{prefix}sources.html">Sources, limitations & review</a><br>Public deployment is not claimed by a local build.</p></footer><script src="{prefix}assets/app.js" defer></script></body></html>'''


def main() -> None:
    download = load("docs/data/download.json")
    if not download:
        raise SystemExit("Missing validated reference bundle metadata")
    primary = DOCS / "downloads" / download["file"]
    if not primary.is_file() or sha256_file(primary) != download["sha256"]:
        raise SystemExit("Website reference is missing or differs from its pinned SHA-256")

    experiment = load("evidence/h24_3a_experiment.json")
    audit = load("evidence/accessibility_audit_v3.json")
    inputs = load("evidence/access_inputs.json")
    group = load("evidence/group_review.json")
    sources = load("docs/data/sources.json")
    review = load("evidence/review_passes.json")
    source_health = load("docs/data/source_health.json")
    results = experiment.get("results", {})
    history = experiment.get("historical_diagnostics", {})
    candidate = results.get("physics_persistence_residualized", {})
    baseline = results.get("physics_raw", {})
    residual_baseline = results.get("physics_residualized", {})
    h19_4 = history.get("h19-4", {})
    h19_5 = history.get("h19-5", {})
    paired_gate = experiment.get("paired_gate", {}).get("physics_residualized", {})
    refs = audit.get("references", {})
    candidate_c2st = refs.get("candidate", {})
    candidate_primary = candidate_c2st.get("primary", {})
    label_primary = refs.get("labels", {}).get("primary", {})
    leader = source_health.get("leaderboard", {})
    leader_score = leader.get("best_score")
    checked = source_health.get("checked_utc", "2026-10-02")

    file_name = e(download["file"])
    fallback = e(download["fallback"])
    checks_file = e(download["checks_file"])
    zip_file = e(download["zip"])
    note_file = e(download["note_file"])
    size_mib = primary.stat().st_size / (1024 * 1024)
    note = e(download["note"])
    download_button = (
        f'<a class="button primary" href="downloads/{file_name}" '
        f'download="{file_name}">↓ Download reference .tif '
        f"<span>({size_mib:.2f} MiB)</span></a>"
    )
    guide_button = (
        '<a class="button" href="executive-summary.html">Submission / executive guide ↗</a>'
    )
    full_audit = bool(audit.get("full_requested_audit_complete"))
    warning = (
        '<div class="status"><strong>No new slot-eligible candidate; no slot consumed.</strong> '
        "The 2024 TIGER buffered road bridge now passes source-window and completeness checks, "
        "but true membership in all four GeoDAWN acquisition blocks is still unavailable. "
        "H24-3A has higher mean DTI than the residualized baseline but fails its "
        "preregistered sparse-fold gate and trails H19 as-emitted diagnostics. The only one-click file below is the pinned H19-5 reference, "
        "not a new prediction.</div>"
    )

    leader_html = (
        f'<a href="{e(leader.get("url", "https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/"))}" '
        f'target="_blank" rel="noopener noreferrer">{fmt(leader_score, 4)}</a>'
        if leader_score is not None
        else "not verified"
    )
    # Shared leaderboard, artifact and promotion caveat.
    overview = f"""<div class="hero"><div><div class="eyebrow">DOE GEMS Prize · auditable fault prediction</div><h1>Evidence before<br>another slot.</h1><p class="lead">An official road-data bridge, a corrected available-family accessibility audit, and a spatially held-out physics hypothesis. The evidence says to hold—not to spend a weekly slot.</p><div class="actions">{download_button}{guide_button}</div><p class="micro"><span class="badge blue">Pinned H19-5 reference</span> Owner-reported original public DTI <strong>0.1922</strong>; not a newly scored file.</p></div><aside class="card visual"><div class="cardtop"><h3>LOCAL DENSE / SPARSE DTI</h3><span class="badge amber">Not promoted</span></div><div class="chartrow"><span>Physics raw</span><div class="track"><div class="bar" style="width:70%"></div></div><strong>{fmt(baseline.get("mean_dense_dti"), 4)} / {fmt(baseline.get("mean_sparse_dti"), 4)}</strong></div><div class="chartrow"><span>H24-3A residualized</span><div class="track"><div class="bar candidate" style="width:80%"></div></div><strong>{fmt(candidate.get("mean_dense_dti"), 4)} / {fmt(candidate.get("mean_sparse_dti"), 4)}</strong></div><div class="chartrow"><span>H19-5 as emitted</span><div class="track"><div class="bar" style="width:100%"></div></div><strong>{fmt(h19_5.get("mean_dense_dti"), 4)} / {fmt(h19_5.get("mean_sparse_dti"), 4)}</strong></div><p class="legend">Four-quadrant research holdout; these are local catalogue diagnostics, not public leaderboard scores or hidden-test predictions.</p><div class="note small">Official public leader snapshot: <strong>{leader_html}</strong> · checked {e(checked)}. No file/account score mapping inferred.</div></aside></div>
{warning}
<div class="metrics"><div class="card metric"><div class="number">32 counties</div><div class="label">Official TIGER 2024 source coverage</div><div class="sub">20 km buffered · 32 complete</div></div><div class="card metric"><div class="number">2 / 3</div><div class="label">Required nuisance families available</div><div class="sub">Roads + claims; four blocks missing</div></div><div class="card metric"><div class="number">{fmt(candidate_primary.get("observed_auc"), 4)}</div><div class="label">Exact candidate C2ST AUC</div><div class="sub">Two-family diagnostic; no flag</div></div><div class="card metric"><div class="number">No slot</div><div class="label">Promotion decision</div><div class="sub">Paired and historical gates fail</div></div></div>
<section><div class="sectionhead"><h2>What the evidence says</h2><a href="research.html" class="small">Read methods and results →</a></div><div class="grid3"><article class="card"><div class="tagline">01 · Source bridge</div><h3>Road coverage fixed</h3><p>Complete official Census county sources cover the 20 km padded seed-grid window. An explicit 2024 MTFCC Road/Path allowlist excludes 183 internal-use S1750 features.</p><p>The result is a road/path distance, not a full hiking-network or travel-time model.</p></article><article class="card"><div class="tagline">02 · Mapping-process audit</div><h3>Available families tested</h3><p>Labels were tested first, then H19-4, H19-5 and the exact experimental raster against road/trail and closed-claim distances.</p><p>No measured association met the declared effect rule; the mandatory four-block feature is absent, so the full audit remains blocked.</p></article><article class="card"><div class="tagline">03 · Protect the slot</div><h3>H24-3A stopped</h3><p>The new contact-persistence detector loses to H19 as-emitted diagnostics and fails one paired residualized-baseline gate.</p><p>A passing format check cannot replace missing acquisition membership, comparable OOF evidence or scientific promotion.</p></article></div></section>
<section><div class="grid2"><article class="card"><h2>Official source links</h2><ul class="prose"><li><a href="https://www2.census.gov/geo/tiger/TIGER2024/ROADS/" target="_blank" rel="noopener noreferrer">U.S. Census TIGER/Line 2024 roads</a> and <a href="https://www2.census.gov/geo/pdfs/maps-data/data/tiger/tgrshp2024/TGRSHP2024_TechDoc_E.pdf" target="_blank" rel="noopener noreferrer">MTFCC technical documentation</a>.</li><li><a href="https://www.sciencebase.gov/catalog/item/657e1d85d34e23d3533209f7" target="_blank" rel="noopener noreferrer">USGS GeoDAWN release</a>: four operational areas are named, but no independently verified four-block GIS membership was available.</li><li><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/" target="_blank" rel="noopener noreferrer">Official public leaderboard</a>: account standings are not linked to an artifact checksum here.</li></ul></article><article class="card"><h2>Next evidence—not another slot</h2><p>Obtain verified four-block polygons or pixel membership, rebuild the C2ST on all three required nuisance families, and reconstruct a comparable current-best OOF baseline. The exact candidate is archived for review and is not recommended for upload.</p><div class="actions"><a class="button" href="data/audit.json" download>Audit receipt JSON</a><a class="button" href="data/experiment.json" download>H24-3A receipt JSON</a></div></article></div></section>
<section><div class="callout"><div><h3>One file. One verifiable identity.</h3><p>Format-checked reference, SHA-256, separate short note, and plain-language instructions.</p></div>{guide_button}</div></section>"""

    hypotheses = [
        (
            "1 · H24-3A · tested",
            "RTP, TMI and gravity; upward continuation at 100/200/400 m; bounded edge-amplitude persistence and unoriented-gradient stability.",
            "Broader buried contacts may persist when shallow artifacts fade; distinct from simply summing Gaussian worms. Expected small–medium benefit; low–moderate CPU. Available layers; flight-height corrections not assumed.",
            "Held-out test completed; not promoted.",
        ),
        (
            "2 · H24-4A · untested",
            "High-pass RTP/gravity differences at 0.3/0.6/1.2 km in eight directions; directional residual variograms and cross-field agreement.",
            "Could capture damage-zone texture without a sharp scarp; differs from existing structure-tensor coherence. Expected low–medium benefit; moderate CPU. Available layers.",
            "Not implemented; no score.",
        ),
        (
            "3 · H24-2A · exploratory only",
            "RTP and detrended elevation; fixed annular radial gradients at 0.6/1.2/2.4 km with edge backprojection.",
            "May recover arcuate contacts; differs from label-centered buffers and scalar ring averaging. Earlier run used Area1 as a forbidden proxy and clipped roads, so its gains are historical only.",
            "Superseded; not a valid promotion result.",
        ),
        (
            "4 · H24-6 · deferred",
            "USGS 3DEP 10 m terrain; repeated signed drainage offsets at independent crossings.",
            "Potential strike-slip evidence distinct from one terrace/road step. Expected uncertain medium; high cost; full raw coverage unverified.",
            "Deferred pending verified official tile coverage.",
        ),
    ]
    hyp_rows = "".join(
        f"<tr><td><strong>{e(rank)}</strong></td><td>{e(layers)}</td><td>{e(rationale)}</td><td>{e(status)}</td></tr>"
        for rank, layers, rationale, status in hypotheses
    )

    result_rows = []
    arm_labels = (
        ("physics_raw", "Physics baseline · raw"),
        ("physics_persistence_raw", "Physics + H24-3A · raw"),
        ("physics_residualized", "Physics baseline · residualized"),
        ("physics_persistence_residualized", "Physics + H24-3A · residualized"),
    )
    for key, label in arm_labels:
        row = results.get(key, {})
        gate_text = (
            "selected challenger; paired gate failed"
            if key.endswith("residualized") and "persistence" in key
            else "paired reference"
        )
        result_rows.append(
            f'<tr><td>{e(label)}</td><td class="num">{fmt(row.get("mean_dense_dti"))}</td><td class="num">{fmt(row.get("mean_sparse_dti"))}</td><td>{e(gate_text)}</td></tr>'
        )
    for tag, row in (("H19-4", h19_4), ("H19-5", h19_5)):
        result_rows.append(
            f'<tr><td>{tag} as emitted</td><td class="num">{fmt(row.get("mean_dense_dti"))}</td><td class="num">{fmt(row.get("mean_sparse_dti"))}</td><td>Historical diagnostic; not original OOF reproduction</td></tr>'
        )
    research = f"""<div class="pagehead"><div class="eyebrow">Preregistered physics · spatial test · honest result</div><h1>One new hypothesis.<br>One measured outcome.</h1><p>H24-3A adds multi-scale persistence of potential-field contacts. Four spatial quadrants, a predeclared 20 km training collar, identical model settings and training-only nuisance transforms were used across all arms.</p></div>{warning}
<section><h2>Ranked hypotheses</h2><div class="tablewrap"><table><thead><tr><th>Rank / status</th><th>Named layers and physical signature</th><th>Why a fault may be missing / distinction / expected benefit and cost</th><th>Evidence state</th></tr></thead><tbody>{hyp_rows}</tbody></table></div><p class="micro">Expected benefits are ordinal hypotheses, not score promises. Novelty is relative to reviewed repository methods, not unseen competitors.</p></section>
<section><h2>H24-3A paired holdout</h2><div class="tablewrap"><table><thead><tr><th>Arm / reference</th><th>Dense DTI</th><th>Sparse DTI</th><th>Interpretation</th></tr></thead><tbody>{"".join(result_rows)}</tbody></table></div><div class="card"><p>Contact persistence vs residualized physics: <strong>Δ dense {fmt(candidate.get("mean_dense_dti", 0) - residual_baseline.get("mean_dense_dti", 0))}, Δ sparse {fmt(candidate.get("mean_sparse_dti", 0) - residual_baseline.get("mean_sparse_dti", 0))}</strong>. Dense improved in 4/4 quadrants, but sparse improved in only {paired_gate.get("sparse_fold_wins", "not available")}/4; one sparse fold lost {fmt(paired_gate.get("worst_fold_delta_sparse"))}. The preregistered paired gate therefore fails.</p><p>Against H19-4/5 as-emitted local diagnostics, candidate means are {fmt(candidate.get("mean_dense_dti"))}/{fmt(candidate.get("mean_sparse_dti"))}, versus {fmt(h19_4.get("mean_dense_dti"))}/{fmt(h19_4.get("mean_sparse_dti"))} and {fmt(h19_5.get("mean_dense_dti"))}/{fmt(h19_5.get("mean_sparse_dti"))}. These local scores do not equal public leaderboard results.</p><p><strong>No slot was spent; the experimental raster is not promoted.</strong></p></div></section>
<section><h2>Exact raster & accessibility audit</h2><div class="grid2"><article class="card"><h3>Format gate</h3><p>Experimental SHA-256: <code>{e(experiment.get("experimental_raster", {}).get("sha256", "not available"))}</code></p><p>Full template shape/CRS/transform, one float32 band, 5,167,373 finite in-footprint values in [0,1], and NaN outside all pass. That is a format result only.</p><p>Output remains under ignored <code>out/</code>, not a download or submission recommendation.</p></article><article class="card"><h3>Spatial / model caveats</h3><ul class="prose"><li>Positives are catalogue trace pixels, not verified fault-absence labels.</li><li>Full-scene unlabeled potential-field continuation is transductive; the 20 km collar leaves residual long-range dependence.</li><li>Whole components touching held-out quadrants/collars were excluded from supervised training; each fold used 20,000 positive and 60,000 unlabelled negatives.</li><li>Historical H19 maps are scored as emitted only; the original training/OOF caches are unavailable.</li></ul></article></div></section>
<section><h2>Why the owner’s H19 results remain interesting</h2><div class="card"><p>Owner-reported H19-4 = <strong>0.1894</strong>; H19-5 = <strong>0.1922</strong>. The local H19-5 output is format validated and remains a reference. No artifact-linked organizer receipt proves either exact raster's score.</p><p>The official public leaderboard currently shows a top score of <strong>{fmt(leader_score, 4)}</strong> ({e(leader.get("participant", "unknown"))} checked {e(checked)}). Public rows at 0.1922 and 0.1894 are not linked to the H19 files; the .0028 owner-reported difference cannot identify a winning mechanism.</p><p>H19-4 and H19-5 share some structure but are not statistically independent submissions. Their local as-emitted DTI is a conservative diagnostic, not an OOF reproduction or score mapping.</p></div></section>
<section><h2>Interpretation limits</h2><ul class="prose"><li>C2ST association is not causal proof; non-rejection does not establish absence of accessibility-related bias.</li><li>Road/claim residualization is an observational conditional-mean adjustment, not causal identification.</li><li>The official report names Winnemucca, Fallon, Hawthorne and Tonopah, but Figure 3 is unreferenced and does not supply true pixel-to-block membership.</li><li>The strict 20 km feature collar is conservative but the upward-continuation kernel has infinite support.</li><li>The old H24-2 experiment used Area1 as a forbidden block proxy and clipped road mirrors; its gain is superseded for confirmation/promotion.</li></ul></section>"""

    audit_rows = []
    for name in ("labels", "h19-4", "h19-5", "candidate"):
        record = refs.get(name)
        if not record:
            continue
        primary_result = record.get("primary", {})
        flag = record.get("meaningful_access_association_available_features", False)
        effect = (
            "Meets available-family effect rule" if flag else "No effect flag on measured families"
        )
        audit_rows.append(
            f'<tr><td>{e(name)}</td><td class="num">{fmt(primary_result.get("observed_auc"), 4)}</td><td class="num">{fmt(primary_result.get("null_auc_p95"), 4)}</td><td class="num">{fmt(primary_result.get("margin_vs_p95"), 4)}</td><td class="num">{fmt(primary_result.get("holm_p_value"), 3)}</td><td>{e(effect)}</td></tr>'
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
    road_entry = inputs.get("features", {}).get("road_m", {})
    road_counts = road_entry.get("mtfcc_counts", {})
    excluded_s1750 = road_entry.get("mtfcc_excluded_counts", {}).get("S1750", 0)
    source_page = f"""<div class="pagehead"><div class="eyebrow">Manual-review links · acquisition receipts · uncertainty kept visible</div><h1>Separate source facts from conclusions.</h1><p>Official data and computed diagnostics are linked to their receipts. The complete audit remains blocked by one specific missing nuisance family: true four-block acquisition membership.</p></div><div class="status"><strong>Full requested audit: {"COMPLETE" if full_audit else "BLOCKED"}.</strong> The official 2024 Census road bridge covers all 32 intersecting counties and a 20 km source-grid buffer; 183 S1750 internal-use features were excluded. Closed BLM claim distances are present. True pixel membership in all four operational acquisition blocks is still unavailable; Area1/Area2 are not substitutes.</div>
<section><h2>Available-family C2ST diagnostics</h2><div class="tablewrap"><table><thead><tr><th>Raster (labels first)</th><th>AUC</th><th>Shift-null p95</th><th>Margin vs p95</th><th>Holm diagnostic</th><th>Interpretation</th></tr></thead><tbody>{"".join(audit_rows)}</tbody></table></div><p class="micro">AUC is the held-out two-sample statistic. Nulls refit the detector on non-wrapping translated masks; 199 valid shifts. The declared effect flag requires Holm-adjusted shift-tail diagnostic ≤.05, AUC ≥.55 and margin ≥.02. The labels-first AUC was {fmt(label_primary.get("observed_auc"), 4)}. Values do not meet that rule for available families. They are provisional, not a full three-family audit.</p><p class="micro">Measured features: official TIGER Road/Path distance and quality-filtered BLM closed-claim distance. No geology, label-derived seam, MRDS, well, vent, probe or Area1 feature entered. Association is not causation; shift-tail values are approximate stationarity diagnostics, not exact randomization p-values.</p></section>
<section><h2>Official inputs and exclusions</h2><div class="tablewrap"><table><thead><tr><th>Source / review link</th><th>Computed receipt</th><th>Limit / scope</th></tr></thead><tbody><tr><td><a href="https://www2.census.gov/geo/tiger/TIGER2024/ROADS/" target="_blank" rel="noopener noreferrer">Census TIGER/Line 2024 Roads ↗</a></td><td>32 complete CA/NV counties; 20 km buffer; EPSG:4269 source counties. Accepted road/path counts: {e(json.dumps(road_counts, sort_keys=True))}. Excluded S1750: {e(excluded_s1750)}.</td><td>Selected roads, vehicular trails and path/access classes; not a complete hiking-network or travel-time model.</td></tr><tr><td><a href="https://www2.census.gov/geo/pdfs/maps-data/data/tiger/tgrshp2024/TGRSHP2024_TechDoc_E.pdf" target="_blank" rel="noopener noreferrer">2024 TIGER technical documentation ↗</a></td><td>Explicit Road/Path MTFCC allowlist; internal-use S1750 and unknown/non-road classes excluded.</td><td>Source classification is not a guarantee every path is traversable or public.</td></tr><tr><td><a href="https://gis.blm.gov/nlsdb/rest/services/Mining_Claims/MiningClaims/MapServer/2" target="_blank" rel="noopener noreferrer">BLM National Land Status Database, closed claims ↗</a></td><td>{e(inputs.get("features", {}).get("claim_m", {}).get("n_source_cases", "unknown"))} source cases, quality-filtered; exact raster/hash in receipt.</td><td>PLSS legal-land approximations; not exact stakes or historic workings.</td></tr><tr><td><a href="https://www.sciencebase.gov/catalog/item/657e1d85d34e23d3533209f7" target="_blank" rel="noopener noreferrer">USGS GeoDAWN data release ↗</a></td><td>Names Winnemucca, Fallon, Hawthorne and Tonopah; two survey-area regimes.</td><td>Published Figure 3 is unreferenced; no verified four-block pixel membership.</td></tr><tr><td><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/" target="_blank" rel="noopener noreferrer">Official DrivenData leaderboard ↗</a></td><td>Top public row {fmt(leader_score, 4)} ({e(leader.get("participant", "unknown"))}), checked {e(checked)}.</td><td>Public account standings are not tied to this repository's exact H19 file hashes.</td></tr></tbody></table></div><p class="micro">The current missing-input list is: {e(missing)}. Full county ZIP and per-county hashes, accepted/excluded MTFCC counts, exact raster checksum and source-window checks are in <code>data/external/audit_sources/tiger_road_receipt.json</code>.</p></section>
<section><h2>Official leaderboard vs owner-reported H19 claims</h2><div class="card"><p>Owner report: H19-4 <strong>0.1894</strong>; H19-5 <strong>0.1922</strong>. Current public leaderboard snapshot: DARD <strong>{fmt(leader_score, 4)}</strong> at rank #1. Rows with 0.1922 and 0.1894 appear at ranks #26 and #28, respectively, but no receipt links those accounts' submissions to these exact files; do not infer artifact scores from the row matches.</p><p>Review the <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/" target="_blank" rel="noopener noreferrer">official leaderboard</a>. These are public score rows only, not new scores for this project.</p></div></section>
<section><h2>All 21 supplied project sources</h2><p class="small muted">Repository review links and pinned commits are listed for manual review. This does not independently certify unseen implementations, current public deployment or scores without artifact-linked receipts.</p><div class="tablewrap"><table><thead><tr><th>Project / site</th><th>Pinned source / commit</th><th>Review status</th><th>Scope</th></tr></thead><tbody>{"".join(group_rows)}</tbody></table></div></section>
<section><div class="grid2"><article class="card"><h3>What was repaired</h3><ul class="prose"><li>Strict nuisance allowlist: only roads/trails, closed mining claims and all four real acquisition blocks; no Area1/Area2 substitution.</li><li>Official buffered Census road bridge; Road/Path MTFCC filter excludes S1750 and records source CRS.</li><li>Labels-first then individual predictions; 199 non-wrapping shifts, four spatial folds, Holm adjustment and an explicit effect threshold.</li><li>Training-only nuisance transforms; no post-emission score reweighting.</li><li>Old v2 audit, which used Area1 and a toroidal/group null, is historical and non-confirmatory.</li></ul></article><article class="card"><h3>Remaining blockers and oddities</h3><p>{e(missing)}</p><p>H24-3A loses to H19 diagnostics and fails the residualized paired sparse gate. The exact raster passes format checks but is not recommended for upload. No new weekly slot was consumed.</p><p>Current best comparable OOF, original H19 caches and verified four-block membership are unavailable. No live leaderboard score is inferred for an artifact.</p><p>Review state: {e(review.get("summary", "pending final review"))}</p><p>Three review passes are recorded in <a href="data/review_passes.json">the review receipt</a>.</p></article></div></section>
<section><h2>Source and experiment receipts</h2><div class="actions"><a class="button" href="data/audit.json" download>C2ST audit JSON</a><a class="button" href="data/experiment.json" download>H24-3A experiment JSON</a><a class="button" href="data/access_inputs.json" download>Access-input receipt</a><a class="button" href="data/source_health.json" download>Leaderboard/source snapshot</a><a class="button" href="data/review_passes.json" download>Three-pass review</a></div></section>"""

    executive = f'''<div class="pagehead"><div class="eyebrow">Executive summary · submission guide</div><h1>Reference file.<br>No duplicate slot.</h1><p>H19-5 is the pinned, format-checked reference; the owner reported its original public DTI as 0.1922. It is not a new prediction and must not be resubmitted as one. The new H24-3A experiment is not promoted.</p><div class="actions">{download_button}{guide_button}</div></div>{warning}
<section><div class="grid2"><article class="card"><h3>One-click reference download</h3><span class="badge blue">Owner-reported original DTI 0.1922</span><p class="fileline">{file_name}</p><ul class="checks"><li>Single band · float32 · EPSG:32611</li><li>3730 × 3292 · exact pinned template transform</li><li>All 5,167,373 footprint values finite and in [0,1]</li><li>NaN outside the official footprint</li><li>Content matches pinned H19-5 reference; not a new score</li></ul><p class="micro">SHA-256: <code>{e(download["sha256"])}</code>. Format validity is checked locally; the file has not been uploaded or rescored in this session.</p></article><article class="card"><h3>Separate note and optional checks</h3><p class="note" id="submission-note">{note}</p><div class="actions"><button class="button" data-copy="#submission-note" data-feedback="#copy-feedback">Copy short comment</button><a class="button" href="downloads/{note_file}" download>Comment .txt</a></div><p id="copy-feedback" class="copyfeedback" aria-live="polite"></p><div class="actions"><a class="button" href="downloads/{checks_file}" download>Format checks JSON</a><a class="button" href="downloads/{zip_file}" download>Single-TIFF ZIP</a><a class="button" href="downloads/{fallback}" download>All-finite fallback</a></div><p class="micro">The zeros-outside fallback differs from the official NaN convention; use only if the organizer explicitly permits it. The note is separate, never a second ZIP member.</p></article></div></section>
<section class="narrow"><h2>Exactly how to submit—only if a future candidate is eligible</h2><ol class="steplist"><li><h3>Check the promotion gates first</h3><p>This H19 reference has no new score. Do not spend a repeat slot. A future candidate must beat a comparable same-protocol holdout, pass the full road/claim/four-block audit, and have its exact final file independently checked.</p></li><li><h3>Use a single-band GeoTIFF</h3><p>Select the uniquely named <code>.tif</code> above only when appropriate. Do not submit the feature stack, a preview, model weights, ZIP folders or a renamed experimental raster. Check SHA-256 and format JSON.</p></li><li><h3>Use the official DrivenData portal</h3><p>Open the <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/" target="_blank" rel="noopener noreferrer">GEMS competition page</a>, choose the submission area and upload the one TIFF (or permitted single-file ZIP). Paste the separate short text comment. This repository never uploads automatically.</p></li><li><h3>For “Predicted values must be in range [0, 1]”</h3><p>Stop and inspect in-footprint finite values, min/max, band count, dtype, CRS, shape and geotransform. Never rescale after seeing a score. The fallback is not silently interchangeable with the official NaN-outside raster.</p></li><li><h3>Record only the organizer’s returned result</h3><p>Save upload time, exact SHA-256, returned score and artifact receipt. Without that link, an account leaderboard score does not establish the score of this file.</p></li></ol></section>
<section><h2>Leaderboard comparison, cautiously</h2><div class="card"><p>At the {e(checked)} check, the official public leaderboard top row was DARD at <strong>{fmt(leader_score, 4)}</strong>. Rows at 0.1922 and 0.1894 appeared at #26/#28, but no artifact-linked evidence identifies either as the H19-5/H19-4 file. The owner-reported H19 scores remain owner reports; no score is inferred from account standings.</p><p>The official page is <a href="{e(leader.get("url", "https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/"))}" target="_blank" rel="noopener noreferrer">reviewable here</a>. The research holdout values elsewhere on this site are not leaderboard scores.</p></div></section>'''

    bodies = {
        "index.html": ("Overview", "Overview", overview),
        "research.html": ("Research and results", "Research", research),
        "sources.html": ("Sources and audit", "Sources & audit", source_page),
        "executive-summary.html": ("Executive submission guide", "Submission guide", executive),
    }
    for name, (title, active, body) in bodies.items():
        (DOCS / name).write_text(page(title, active, body))

    root_overview = overview
    for path in ("data/", "downloads/", "executive-summary.html", "research.html", "sources.html"):
        root_overview = root_overview.replace(f'href="{path}', f'href="docs/{path}')
    (ROOT / "index.html").write_text(page("Overview", "Overview", root_overview, prefix="docs/"))
    (ROOT / "executive-summary.html").write_text(
        '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="refresh" content="0;url=docs/executive-summary.html"><title>Executive guide</title></head><body><a href="docs/executive-summary.html">Open the executive guide</a></body></html>'
    )
    for source, target in (
        ("evidence/h24_3a_experiment.json", "docs/data/experiment.json"),
        ("evidence/accessibility_audit_v3.json", "docs/data/audit.json"),
        ("evidence/access_inputs.json", "docs/data/access_inputs.json"),
        ("docs/data/source_health.json", "docs/data/source_health.json"),
        ("evidence/review_passes.json", "docs/data/review_passes.json"),
    ):
        content = load(source)
        (ROOT / target).write_text(json.dumps(content, indent=2) + "\n")
    (DOCS / "data/group_review.json").write_text(json.dumps(group, indent=2) + "\n")

    status = f"""**No new slot-eligible candidate; no slot consumed.** H19-5 remains a format-validated reference with owner-reported original public DTI **0.1922**. The official leaderboard snapshot on {checked} showed DARD at **{fmt(leader_score, 4)}** (#1); rows at **0.1922** and **0.1894** were present but are not linked to these raster hashes.

H24-3A paired residualized holdout: **{fmt(candidate.get("mean_dense_dti"))} / {fmt(candidate.get("mean_sparse_dti"))}** vs residualized physics **{fmt(residual_baseline.get("mean_dense_dti"))} / {fmt(residual_baseline.get("mean_sparse_dti"))}**. It fails the preregistered sparse-fold gate and trails H19-4/5 as-emitted local diagnostics. These local DTI values do not forecast a public score.

The official 2024 Census road/path bridge now passes complete county/window checks: 32 counties, 20 km buffer, explicit Road/Path MTFCC allowlist, S1750 excluded. The full three-family C2ST is still **BLOCKED** because verified four-block pixel membership is missing. Labels first, then H19-4, H19-5 and exact H24-3A were tested using the two available families only; no available-family association met the declared effect rule. No causality or absence of bias is inferred.

Reference: [`{download["file"]}`](docs/downloads/{download["file"]}). New experimental exact raster is format valid but **not recommended to upload**. PR/merge/public deployment are recorded separately; this local build is not publication proof.
"""
    readme = ROOT / "README.md"
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
        "pages": [str((DOCS / name).relative_to(ROOT)) for name in bodies],
        "root": "index.html",
        "full_audit_complete": full_audit,
        "new_slot_eligible": False,
        "publication_verified": False,
        "no_scores_inferred": True,
    }
    (ROOT / "evidence/site_build.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
