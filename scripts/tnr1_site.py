"""Render the latest exact-file-verified negative packet, without a slot selector."""

from __future__ import annotations

import json
from html import escape

from run_tnr1_lane import verify_recorded

from gems.benchmarks import recorded_point_best
from gems.novelty import SYNTHETIC_CALIBRATION_CONTROL_FILES


def render(root):
    card_path = root / "evidence/tnr1_run_card_20261026.json"
    if not card_path.exists():
        active = root / "docs/data/active_lane.json"
        if active.exists() and json.loads(active.read_text()).get("lane") == "H24-TNR1":
            raise ValueError("Current TNR1 receipt missing; no silent historical fallback")
        return None
    card = verify_recorded(root, source_history=False)
    if not card.get("submission_name"):
        raise ValueError("TNR1 has no releasable file; do not silently feature an old candidate")
    report = json.loads((root / "evidence/tnr1_experiment_20261026.json").read_text())
    holdout = card["holdout"]
    low, high = holdout["ci95"]["interval"]
    before = card["correlation_overlap_vs_registry"]["surface_before_placement"]
    after = card["correlation_overlap_vs_registry"]["final_dots"]
    method_rows = [
        row for row in after["rows"] if row["file"] not in SYNTHETIC_CALIBRATION_CONTROL_FILES
    ]
    method_overlap = max(row["candidate_dot_overlap_within_3px"] for row in method_rows)
    audit = card["exact_file_nuisance_audit"]["candidate"]
    raw = card["matched_control_holdout"]
    raw_low, raw_high = raw["ci95"]["interval"]
    paired = card["paired_comparison"]
    delta_low, delta_high = paired["paired_delta_ci95"]
    best = card["recorded_baseline_comparisons"]["recorded_current_highest_gvc1"]["holdout"]
    best_low, best_high = best["ci95"]["interval"]
    current = recorded_point_best(root)
    current_score = current["holdout"]
    current_low, current_high = current_score["ci95"]["interval"]
    count = sum(
        len(card[key]["features"]) for key in ("raw_feature_canary", "oof_transform_canary")
    )
    name = escape(card["submission_name"], quote=True)
    twin = escape(card["nan_outside_companion"]["file"], quote=True)
    note = escape(card["note"])
    digest = escape(card["raster_sha256"])
    info = (
        f'<p class="fileline">{name}</p><p class="hash">SHA-256 {digest}</p>'
        '<p class="micro">Newly computed prediction content, not a copied submission. '
        "Distinct bytes do not mean the scientific uniqueness gate passed.</p>"
    )
    status = (
        '<div class="status stopped" role="status"><strong>DOWNLOAD: YES · SUBMIT: NO. '
        "NOT OK TO SUBMIT.</strong><br>Automated NEGATIVE verdict: no current-best holdout win "
        "and the final-dot novelty gate failed. No human-inspector fallback, no retuning, no slot used.</div>"
    )
    buttons = (
        f'<a class="button primary" href="downloads/{name}" download="{name}">'
        "↓ Download new research .tif — DO NOT SUBMIT</a>"
        f'<a class="button" href="downloads/{name[:-4]}.preflight.json">Automated preflight</a>'
    )
    score_label = (
        f"HOLDOUT-DTI · <code>{escape(holdout['evaluator_version'])}</code> · "
        f"{holdout['n_withheld_positive_pixels']:,} withheld positives · "
        f"95% spatial-bootstrap CI [{low:.5f}, {high:.5f}]"
    )
    hero = f"""<div class="hero" id="current-packet"><div>
<div class="eyebrow">Featured session file · H24-TNR1 · 2026-10-26</div>
<h1>Download the evidence.<br>Protect the slot.</h1>
<p class="lead">A new, independently computed fault-prediction GeoTIFF is ready to download.
The project evaluated it automatically and says <strong>do not submit</strong>—not “inspection pending”.</p>
{status}<div class="actions">{buttons}<a class="button" href="executive-summary.html">Submission guide →</a></div>{info}
</div><aside class="card visual"><div class="cardtop"><h2 class="metric-label">HOLDOUT-DTI</h2>
<span class="badge amber">Not a leaderboard score</span></div><div class="result-number">{holdout["dti"]:.5f}</div>
<p class="micro">{score_label}</p><img class="raster-preview" src="assets/tnr1-preview.png"
alt="Downsampled map of frozen TNR1 research dots; not verified faults or geothermal vents">
<p class="micro">{card["validator_output"]["in_footprint_positive_pixels"]:,} experimental dots · not yet scored by the organizer · all-finite [0,1] zero-outside encoding</p></aside></div>"""
    rows = [
        (
            "Exact file / range",
            "PASS",
            "Single-band float32; no NaN/Inf anywhere in the zero variant; every value [0,1]; template CRS/shape/transform match. The official NaN-outside convention differs; the companion matches it, but is also not authorized.",
        ),
        (
            "Leakage canaries",
            "PASS",
            f"{count} raw-input, missingness, physical-factor and OOF-transform checks; both AUC polarities, every spatial fold. This is a diagnostic, not proof of independent discovery.",
        ),
        (
            "Matched control",
            "NO GAIN",
            f"Paired HOLDOUT-DTI delta {paired['paired_delta_dti']:+.5f}, 95% CI [{delta_low:+.5f}, {delta_high:+.5f}]; {paired['fold_wins']}/{paired['n_folds']} folds won.",
        ),
        (
            "Current recorded point-best",
            "FAIL",
            f"TNR1 HOLDOUT-DTI {holdout['dti']:.5f} is below later {current['lane']} {current_score['dti']:.5f} (95% CI [{current_low:.5f}, {current_high:.5f}]); same declared evaluator/count. A point-best is not a certified paired win; no independent best-model replay is claimed.",
        ),
        (
            "Exact-file nuisance audit",
            "NOT FLAGGED",
            f"C2ST diagnostic AUC {audit['observed_auc']:.4f}; null p95 {audit['null_auc_p95']:.4f}; Holm p {audit['holm_p_value']:.3f}. Non-rejection is not proof of unbiased geology.",
        ),
        (
            "Pre-placement surface",
            "PASS",
            f"Maximum tested raw/kernel |Spearman| {before['max_abs_rank_correlation']:.5f} across {before['registry_unique_rasters']} frozen contents; limit 0.90.",
        ),
        (
            "Final-dot uniqueness",
            "FAIL / STOP",
            f"Directional 3-px overlap {100 * method_overlap:.2f}% against a competing method, above 70%; {100 * after['max_dot_overlap']:.2f}% against the retained lattice. Failure is not only the calibration control.",
        ),
        (
            "Slot authorization",
            "BLOCKED",
            "No assigned method paragraph, independently verified selector certificate, current account allowance or organizer receipt. Zero slots spent.",
        ),
    ]
    gates = (
        '<section id="tnr1-gates"><h2>Automated decision gates</h2><div class="tablewrap" tabindex="0" role="region" aria-label="TNR1 decision gates"><table><thead><tr><th>Gate</th><th>Decision</th><th>Evidence / limitation</th></tr></thead><tbody>'
        + "".join(
            f"<tr><td>{escape(title)}</td><td><strong>{escape(decision)}</strong></td><td>{escape(detail)}</td></tr>"
            for title, decision, detail in rows
        )
        + '</tbody></table></div><p class="micro">A format PASS never authorizes a weekly slot. All performance values are HOLDOUT-DTI; AUC/overlap are explicitly different diagnostics.</p></section>'
    )
    note_block = f'''<section class="grid2"><article class="card"><h3>Unique filename and short note</h3>
<div class="note" id="note-tnr1">{note}</div><div class="actions"><button class="button"
data-copy="#note-tnr1" data-feedback="#tnr1-feedback">Copy research note</button>
<a class="button" href="downloads/{name[:-4]}.note.txt" download>Note .txt</a></div>
<p id="tnr1-feedback" class="copyfeedback" aria-live="polite"></p><p class="micro">{len(card["note"])} characters · maximum 140 · not an authorization</p></article>
<article class="card"><h3>Download the complete decision</h3><div class="actions">
<a class="button" href="data/tnr1_run_card.json" download>JSON run card</a>
<a class="button" href="downloads/{twin}" download="{twin}">NaN-outside companion</a></div>
<p class="micro">Same interior predictions in both encodings. The companion is research-only too and fails a strict whole-array no-NaN test by design.</p></article></section>'''
    howto = """<section id="submission-steps"><h2>How a future authorized file would be submitted</h2>
<p><strong>Do not submit TNR1.</strong> The static site serves generated files; it does not train in the browser or automate the competition portal.
A separate automated selector must first verify a current-best paired holdout win, complete canaries, exact-file audit,
all-entry novelty and current account allowance. No human inspection exception replaces these checks.</p>
<ol class="steplist"><li><h3>Download only a released PASS packet</h3><p>Match its filename and SHA-256 to its hash-bound validation receipt. Never rename an old submission to make it look new.</p></li>
<li><h3>Open the official competition</h3><p>Sign in at <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">DrivenData GEMS</a>, then Submit → Make new submission. The project never automates DrivenData access.</p></li>
<li><h3>File to submit</h3><p>Select the released single-band .tif, or a ZIP containing exactly one such file. CRS, shape and geotransform must match the template.</p></li>
<li><h3>Note (optional)</h3><p>Copy the released packet’s note, at most 140 characters under this project’s stricter policy.</p></li>
<li><h3>Check allowance and preserve the result</h3><p>Historical rules mention three submissions per week; the current remaining allowance is unknown. A selector must refuse release without a current legitimate quota record. Preserve an artifact-linked submission-page receipt before any score is called ORGANIZER-CONFIRMED.</p></li></ol></section>
<section><h2>About “Predicted values must be in range [0, 1]”</h2><p>The primary <code>-zeros.tif</code> is allfinite: every stored cell is finite and in [0,1], with zeros outside the footprint. The NaN companion has NaN only outside. Both match the pinned grid. This rules out those local file defects; it does not prove what caused the earlier portal rejection or guarantee organizer acceptance.</p></section>"""
    explanation = f"""<section><h2>What the experiment actually tested</h2><p>TNR1 keeps {len(report["model_columns"]) - 12} terrain/strain inputs unchanged while removing training-region nuisance responses from 12 non-topographic/composite channels in a 31-channel HGB model. It reuses cached physical features, not old prediction pixels. A matched raw control used the same sampled rows and model settings.</p>
<p>Whole fault components touching each held-out quadrant or its collar are hidden everywhere. Training is purged by 1.5 km; catalogue-dependent sampling uses visible faults only. Visible faults are masked pixel-exactly; TPw/FPw/FNw are pooled before DTI, with alpha 0.2, beta 0.8 and a 300 m triangular kernel.</p>
<div class="tablewrap" tabindex="0" role="region" aria-label="Comparable holdout results"><table><thead><tr><th>Arm / record</th><th>HOLDOUT-DTI</th><th>95% CI</th><th>Status</th></tr></thead><tbody>
<tr><td>TNR1 fixed candidate</td><td>{holdout["dti"]:.5f}</td><td>[{low:.5f}, {high:.5f}]</td><td>New measurement; negative</td></tr>
<tr><td>Matched raw 31-channel control</td><td>{raw["dti"]:.5f}</td><td>[{raw_low:.5f}, {raw_high:.5f}]</td><td>New control measurement; not a submission choice</td></tr>
<tr><td>GVC1 execution-time comparator</td><td>{best["dti"]:.5f}</td><td>[{best_low:.5f}, {best_high:.5f}]</td><td>Recorded, not retrained here; novelty failed</td></tr>
<tr><td>{current["lane"]} later recorded point-best</td><td>{current_score["dti"]:.5f}</td><td>[{current_low:.5f}, {current_high:.5f}]</td><td>Parallel record, not a certified paired win or submit authorization</td></tr></tbody></table></div>
<p class="micro">All rows: {escape(holdout["evaluator_version"])} · {holdout["n_withheld_positive_pixels"]:,} withheld positives. CIs are internal spatial-bootstrap uncertainty, not hidden-score estimates. Repeated use of this public holdout can itself overfit research decisions.</p>
<p><strong>Named alternative:</strong> {escape(card["named_non_fault_mimic"])}. A fault-proxy raster is not proof of a vent, heat, fluid supply or permeability. Frozen SAHG1 physical preprocessing uses survey-wide statistics; the new nuisance fit alone is training-only. The complete support mask covers {100 * report["support_pixels"] / 5167373:.2f}% of the footprint, limiting recall.</p>
<p><a href="https://github.com/buffedlizard55-lab/GEMSDOE24/blob/main/knowledge/20_preregistered_TNR1_2026-10-26.md">Four ranked preregistered hypotheses</a> · <a href="https://github.com/buffedlizard55-lab/GEMSDOE24/blob/main/knowledge/21_TNR1_findings_2026-10-26.md">Findings and next work</a> · <a href="data/tnr1_run_card.json">Full numerical evidence</a></p></section>"""
    h33 = """<section><h2>Why GEMSDOE32 may have improved—and what is not known</h2>
<p>Its reported <strong>0.2778 is OWNER-REPORTED / UNVERIFIED</strong>, not ORGANIZER-CONFIRMED. Frozen pixel forensics show 40,199 predecessor dots became 37,654 by deleting 2,545 dots within 200 m of the catalogue; none were added. That is emission-policy refinement, not proof of a new geological detector.</p>
<p>For D = T/(0.2T + 0.2F + 0.8N), removing true-positive credit L and false-positive mass S helps only when L(0.2F + 0.8N) &lt; 0.2TS. Hidden T/F/L/S are unavailable, so fewer dots do not prove better accuracy or identify the hidden-score cause. A higher new score is possible, but this experiment does not establish one. The conflicting reported leaderboard highs 0.3195 and 0.4413 remain unverified.</p>
<p><a href="data/priority_review_20261025.json">Frozen geometry evidence</a> · <a href="https://github.com/buffedlizard55-lab/GEMSDOE24/blob/main/knowledge/14_h33_analysis_2026-10-25.md">Derivation and limitations</a></p></section>"""
    overview = (
        hero
        + gates
        + note_block
        + h33
        + '<section><h2>Full source inventory</h2><p>All 92 owner-listed repository READMEs have been retrieved at immutable commits and checked for byte identity. That is a source audit—not organizer score verification or a novelty certificate against every current TIFF.</p><div class="actions"><a class="button" href="sources.html#all-owner-sites">Browse all 92 sites</a><a class="button" href="data/all_owner_sites_20261026.csv" download>Download audit table .csv</a><a class="button" href="research.html#tnr1-research">Method and limitations</a></div></section>'
    )
    executive = (
        '<div class="pagehead"><div class="eyebrow">Executive submission summary</div><h1>New file available.<br>Not cleared to submit.</h1></div>'
        + status
        + '<div class="actions">'
        + buttons
        + "</div>"
        + info
        + gates
        + note_block
        + howto
    )
    artifact = {
        "file": card["submission_name"],
        "sha256": card["raster_sha256"],
        "note": card["note"],
        "note_file": card["submission_name"][:-4] + ".note.txt",
        "ok_to_download": True,
        "ok_to_submit": False,
        "submission_authorized": False,
        "verdict": "negative",
    }
    return {
        "overview": overview,
        "executive": executive,
        "research": '<section id="tnr1-research"><div class="pagehead"><div class="eyebrow">This session’s preregistered test · stopped without retuning</div><h1>Keep the negative result.</h1></div>'
        + status
        + "</section>"
        + explanation
        + gates
        + h33,
        "active": {
            "lane": "H24-TNR1",
            "generated_utc": report["generated_utc"],
            "preregistration": report["preregistration"],
            "evaluator_version": holdout["evaluator_version"],
            "holdout": holdout,
            "artifact": artifact,
            "verdict": "negative",
            "ok_to_submit": False,
            "submission_authorized": False,
        },
        "status_md": f"Latest **H24-TNR1**: [`{card['submission_name']}`](docs/downloads/{card['submission_name']}). **DOWNLOAD YES / SUBMIT NO — NOT OK TO SUBMIT**. HOLDOUT-DTI **{holdout['dti']:.5f}**, 95% CI **[{low:.5f}, {high:.5f}]**, `{holdout['evaluator_version']}`, **{holdout['n_withheld_positive_pixels']:,} withheld positives**. Matched raw control **HOLDOUT-DTI {raw['dti']:.5f}** (95% CI [{raw_low:.5f}, {raw_high:.5f}]); paired delta {paired['paired_delta_dti']:+.5f} (95% CI [{delta_low:+.5f}, {delta_high:+.5f}]). Execution-time GVC1 comparator **HOLDOUT-DTI {best['dti']:.5f}** (95% CI [{best_low:.5f}, {best_high:.5f}], same evaluator/positives; not retrained). Later recorded {current['lane']} point-best **HOLDOUT-DTI {current_score['dti']:.5f}** (95% CI [{current_low:.5f}, {current_high:.5f}], same evaluator/positives) changes nothing about this frozen lane's paired and duplicate verdicts. Exact file [0,1]/grid and {count} leakage-canary checks pass; C2ST diagnostic AUC {audit['observed_auc']:.4f}, Holm p {audit['holm_p_value']:.3f}, not flagged. Final competing-method 3-px overlap **{100 * method_overlap:.2f}%** exceeds 70%; retained lattice overlap **100%**. Stopped as duplicate; no retuning. New bytes, not gate-passing scientific uniqueness, and not a leaderboard result. No weekly slot has been spent. [JSON run card](evidence/tnr1_run_card_20261026.json) · [Executive guide](docs/executive-summary.html) · [Current owner brief](knowledge/owner_brief_2026-10-26.md).\n\nEarlier packets below are historical, not current submission authority.\n\n",
    }


def all_sites_table(root):
    path = root / "docs/data/all_owner_sites_20261026.json"
    if not path.exists():
        return ""
    from review_owner_sites import validate

    data = validate(json.loads(path.read_text()))
    rows = []
    for row in data["rows"]:
        claims = (
            "<br>".join(
                f"<code>{escape(claim['submission_name_as_reported'])}</code>: {escape(claim['value_as_reported'])}"
                for claim in row["claims"]
            )
            or "No score reported"
        )
        rows.append(
            f'<tr><td><a href="{escape(row["readme_url"], quote=True)}">{escape(row["repo"].split("/")[-1])}</a></td><td>{claims}<br><strong>OWNER-REPORTED / UNVERIFIED</strong></td><td>{escape(row["source_status"])}<br><code>{escape(row["commit"][:12])}</code></td></tr>'
        )
    stale = ""
    if data.get("refresh_status") == "error":
        stale = (
            '<p class="status stopped"><strong>STALE SNAPSHOT:</strong> '
            + escape(data["refresh_error"])
            + "</p>"
        )
    return stale + (
        f'<section id="all-owner-sites"><h2>All {data["site_count"]} owner-listed sites</h2><p>Source snapshot {escape(data["checked_utc"])}. Full READMEs retrieved at immutable commits, byte-identity verified, and programmatically inventoried. Score rows are historical owner claims from the preserved brief, not a fresh scoring feed. This does not verify every scientific sentence, any organizer score, or every published TIFF. TNR1 novelty remains scoped to its separately frozen 117-raster union.</p><div class="actions"><a class="button" href="data/all_owner_sites_20261026.csv" download>Audit table .csv</a><a class="button" href="data/all_owner_sites_20261026.json" download>Full source pins / hashes .json</a><a class="button" href="data/tnr1_source_review_20261026.json" download>Official-source claim evidence</a></div><details><summary>Show the complete source / owner-claim table</summary><div class="tablewrap" tabindex="0" role="region" aria-label="All owner-listed source claims"><table><thead><tr><th>Source</th><th>Owner claims, not verified scores</th><th>Source status / pin</th></tr></thead><tbody>'
        + "".join(rows)
        + "</tbody></table></div></details></section>"
    )
