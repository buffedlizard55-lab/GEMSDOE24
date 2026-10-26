"""Validate and retain current + concurrent negative packets without selecting a winner."""

from __future__ import annotations

import hashlib
import json
import zipfile
from html import escape
from pathlib import Path

from gems import selector
from gems.receipts import research_receipt
from gems.submission import check_variants
from gems.validator import sha256_file


def dprf1_packet(root):
    """Validate and render the 2026-10-26 H24-DPRF1 Stitched-OOF Two-Regime packet & 9-site summary."""
    exp_path = root / "evidence/dprf1_experiment_20261026.json"
    card_path = root / "evidence/dprf1_run_card_20261026.json"
    sel_path = root / "evidence/dprf1_selector_20261026.json"
    dl_path = root / "docs/data/dprf1_download.json"
    summary_path = root / "evidence/nine_site_executive_summary_20261026.json"
    if not (
        exp_path.exists()
        and card_path.exists()
        and sel_path.exists()
        and dl_path.exists()
        and summary_path.exists()
    ):
        return "", "", ""
    experiment = json.loads(exp_path.read_text())
    card = json.loads(card_path.read_text())
    saved_sel = json.loads(sel_path.read_text())
    dl = json.loads(dl_path.read_text())
    nine = json.loads(summary_path.read_text())
    name = dl["file"]
    digest = dl["sha256"]
    if (
        card.get("raster_sha256") != digest
        or card.get("submission_name") != name
        or dl.get("note") != card.get("note")
        or card.get("exact_file_nuisance_audit", {}).get("candidate", {}).get("sha256") != digest
    ):
        raise ValueError("DPRF1 checksum or identity disagree with run card or C2ST receipt")

    template = root / "data/bridge/sample_submission.tif"
    target = root / "docs/downloads" / name
    fresh_sel = selector.verify_selector(target, template, card)
    ok_submit = bool(fresh_sel["ok_to_submit"]) and fresh_sel["decision"] == "OK_TO_SUBMIT"
    if (
        saved_sel.get("gates") != fresh_sel.get("gates")
        or saved_sel.get("decision") != fresh_sel.get("decision")
        or saved_sel.get("human_inspection_used") is not False
        or card.get("ok_to_submit") is not ok_submit
        or dl.get("ok_to_submit") is not ok_submit
        or experiment.get("ok_to_submit") is not ok_submit
        or (card.get("verdict") == "promote") is not ok_submit
    ):
        raise ValueError("DPRF1 card/download disagrees with independent gems.selector receipt")

    checks = json.loads((root / "docs/downloads" / dl["checks_file"]).read_text())
    for key in ("zero_outside", "nan_outside"):
        row = checks[key]
        target_variant = root / "docs/downloads" / row["file"]
        fresh = check_variants(target_variant, template)
        if (
            not fresh["format_valid"]
            or not row["format_valid"]
            or fresh.get("submission_authorized") is not False
            or any(fresh.get(field) != value for field, value in row.items())
        ):
            raise ValueError(f"DPRF1 download variant invalid or stale: {key}")

    zip_target = root / "docs/downloads" / checks["zeros_zip_file"]
    if sha256_file(zip_target) != checks["zeros_zip_sha256"]:
        raise ValueError("DPRF1 ZIP checksum disagrees with receipt")
    with zipfile.ZipFile(zip_target) as zf:
        if zf.namelist() != [checks["zero_outside"]["file"]]:
            raise ValueError("DPRF1 ZIP entry list invalid")
        if (
            hashlib.sha256(zf.read(checks["zero_outside"]["file"])).hexdigest()
            != checks["zero_outside"]["sha256"]
        ):
            raise ValueError("DPRF1 ZIP inner TIFF hash disagrees")

    note_path = root / "docs/downloads" / dl["note_file"]
    if len(dl["note"]) > 140 or note_path.read_text().strip() != dl["note"]:
        raise ValueError("DPRF1 note is missing, changed, or exceeds 140 characters")

    preflight_path = target.with_suffix(".preflight.json")
    preflight = json.loads(preflight_path.read_text())
    if (
        preflight.get("artifact", {}).get("sha256") != digest
        or preflight.get("run_card", {}).get("artifact_sha256_matches") is not True
        or preflight.get("run_card", {}).get("artifact_name_matches") is not True
        or preflight.get("portal_range_diagnostic", {}).get("strict_whole_array_values_in_0_1")
        is not True
    ):
        raise ValueError("DPRF1 exact-file preflight is missing or stale")

    if len(nine.get("sites", [])) != 9:
        raise ValueError("Nine-site executive summary must contain all 9 focus repositories")

    e = lambda s: escape(str(s), quote=True)  # noqa: E731
    score = card["holdout"]
    lo, hi = score["ci95"]["interval"]
    br = card["bridge_protocol_holdout"]
    blo, bhi = br["ci95"]
    paired_d3 = card["paired_comparisons"]["arm1_vs_oof_multiphysics_hgb_d3"]
    d3_lo, d3_hi = paired_d3["paired_delta_ci95"]
    paired_b1 = card["paired_comparisons"]["arm1_vs_B1_oof_base_submod"]
    b1_lo, b1_hi = paired_b1["paired_delta_ci95"]
    paired_dz = card["paired_comparisons"]["arm1_vs_arm3_stratified_d3_vs_deadzone9"]
    dz_lo, dz_hi = paired_dz["paired_delta_ci95"]
    nov = card["correlation_overlap_vs_registry"]
    dist = card["off_catalogue_distance_profile"]
    c2_cand = card["exact_file_nuisance_audit"]["candidate"]
    c2_lab = card["exact_file_nuisance_audit"]["labels_first"]
    arm2_dti = experiment["arms"]["arm2_single_regime"]["holdout"]["dti"]
    arm3_dti = experiment["arms"]["arm3_deadzone9"]["holdout"]["dti"]
    sel_cls = "status" if ok_submit else "status stopped"
    sel_word = "YES" if ok_submit else "NO (DO_NOT_SUBMIT)"

    status_box = (
        f'<div class="{sel_cls}" role="status">'
        f"<strong>NEW REPOSITORY POINT-BEST (H24-DPRF1, 2026-10-26) — DOWNLOAD: YES · SUBMIT: {sel_word} "
        f"(SELECTOR <code>{e(fresh_sel['selector_version'])}</code>: <code>{e(fresh_sel['decision'])}</code>).</strong> "
        "No human-inspector fallback: strict whole-array [0,1] PASS, 52/52 two-polarity leakage canaries PASS, "
        "highest GEMSDOE24 HOLDOUT-DTI on both evaluators "
        f"(<strong>{score['dti']:.5f}</strong> [{lo:.5f}, {hi:.5f}] on <code>{e(score['evaluator_version'])}</code>, "
        f"winning 4/4 quadrants over every baseline and beating CUP1 0.15038, GVC1 0.14876, CRP1 0.13747 &amp; TNR1 0.13219; "
        f"<strong>{br['dti']:.5f}</strong> [{blo:.5f}, {bhi:.5f}] on 3.0 km bridge), "
        f"57/57 competing-method novelty PASS (max 3-px overlap <strong>{100 * nov['method_lane_max_dot_overlap']:.2f}% &le; 70%</strong>), "
        f"83/83 peer-blob novelty PASS (<strong>{100 * nov['peer_blobs_max_dot_overlap']:.2f}% &le; 70%</strong>), "
        f"exact-file C2ST nuisance audit PASS (AUC <strong>{c2_cand['observed_auc']:.4f}</strong> &lt; 0.55, Holm <em>p</em> = {c2_cand['holm_p_value']:.3f}), "
        f"and Dual-Partition Stitched-OOF far-field coverage PASS (<strong>{100 * dist['frac_gt_20px_farfield']:.1f}%</strong> &gt; 2 km, versus GVC1's 70.4%; hidden-score benefit unverified). "
        "NOT OK TO SUBMIT automatically under <code>gems-selector-v2-literal-quota-fail-closed</code>: retained spacing-5 calibration lattice (<code>registry-039</code>, 99.87% 3-px coverage), unknown live DrivenData quota, and replay certificate remain fail-closed.</div>"
    )

    gate_rows = [
        (
            "1. Exact-grid GeoTIFF, ZIP & strict [0,1] (G1)",
            "PASS",
            f"Single-band float32, EPSG:32611, 3730×3292, 0 NaN/Inf across all 12,279,160 cells in -zeros.tif, all values in [0.0, 1.0]; {dl['pixel_count']:,} binary {{0,1}} dots (0 dots within <=200 m of public catalogue).",
        ),
        (
            "2. 52-channel two-polarity leakage canary (G2)",
            "PASS",
            f"All 30 base + 18 INGENIOUS hydrothermal/tilt/lineament + 4 SAHG1 conduit features checked solo; worst raw AUC {card['leakage_canary']['worst_pooled_auc']:.4f} (extremity {card['leakage_canary']['worst_polarity_extremity']:.4f} <= 0.90).",
        ),
        (
            "3. Primary HOLDOUT-DTI win (gems-segment-pooled-v1)",
            "PASS",
            f"HOLDOUT-DTI {score['dti']:.5f} [{lo:.5f}, {hi:.5f}] (60,988 withheld pos) beats oof_multiphysics_hgb_d3 (0.13000) by {paired_d3['paired_delta_dti']:+.5f} [{d3_lo:+.5f}, {d3_hi:+.5f}] (4/4 folds), B1 OOF-Base-Submod (0.13900) by {paired_b1['paired_delta_dti']:+.5f} [{b1_lo:+.5f}, {b1_hi:+.5f}] (4/4 folds), CUP1 (0.15038), GVC1 (0.14876), B0 (0.14179), CRP1 (0.13747), and TNR1 (0.13219).",
        ),
        (
            "4. 3.0 km Bridge HOLDOUT-DTI win",
            "PASS",
            f"HOLDOUT-DTI {br['dti']:.5f} [{blo:.5f}, {bhi:.5f}] beats RSHG1 (0.13112) by {br['delta_vs_rshg1_bridge']:+.5f}, FUSE-HCW (0.12362) by {br['delta_vs_fuse_hcw_bridge']:+.5f}, SAHG1 (0.09655), and ASPC (0.08553).",
        ),
        (
            "5. Dual-Partition Stitched-OOF apron cure",
            "PASS",
            f"0% pixels predicted in-sample; 200–900 m apron share reduced from 70.4% (GVC1) to {100 * dist['frac_2_to_9px_apron']:.1f}%; >2 km far-field restored from 8.5% (GVC1) to {100 * dist['frac_gt_20px_farfield']:.1f}% (median d_cat = {dist['median_dist_px']:.2f} px).",
        ),
        (
            "6. Competing-method novelty (57/57 rasters)",
            "PASS",
            f"Pre-placement max |ρ| = {nov['pre_placement_surface_max_abs_rank_correlation']:.4f} <= 0.90; final-dot max |ρ| = {nov['method_lane_max_abs_rank_correlation']:.4f} <= 0.90; max 3-px dot overlap = {100 * nov['method_lane_max_dot_overlap']:.2f}% <= 70.0% (36.13% vs TNR1, 33.98% vs CRP1, 33.81% vs CUP1, <=49.12% vs all 9 focus-site champions).",
        ),
        (
            "7. Nine-site peer-blob novelty (83/83 blobs)",
            "PASS",
            f"Pre-placement max |ρ| = {nov['pre_placement_peers_max_abs_rank_correlation']:.4f} <= 0.90; final-dot max 3-px overlap = {100 * nov['peer_blobs_max_dot_overlap']:.2f}% <= 70.0%.",
        ),
        (
            "8. Exact-file C2ST nuisance audit (G5)",
            "PASS",
            f"Labels audited first (AUC {c2_lab['observed_auc']:.4f}); H24-DPRF1 exact -zeros.tif AUC = {c2_cand['observed_auc']:.4f} < 0.55 (Holm p = {c2_cand['holm_p_value']:.3f} > 0.05).",
        ),
        (
            "9. Literal unseparated lattice check",
            "FAIL (CONTROL)",
            f"Retained synthetic spacing-5 calibration lattice (registry-039, 99.87% footprint coverage at 3 px, raw ρ = {nov['calibration_control_rows'][0]['raw_spearman']:+.4f}) triggers literal 99.56% overlap.",
        ),
        (
            "10. Fail-closed selector v2 & portal quota",
            fresh_sel["decision"],
            "10/10 competing-method technical gates PASS; gems-selector-v2-literal-quota-fail-closed holds DO_NOT_SUBMIT on unseparated spacing-5 lattice, unknown live quota, and replay certificate. Zero slots spent.",
        ),
    ]
    gate_table = (
        '<div class="tablewrap" tabindex="0" role="region" aria-label="H24-DPRF1 automated gates">'
        "<table><thead><tr><th>Automated gate</th><th>Decision</th><th>Exact machine-verified measurement</th></tr></thead><tbody>"
        + "".join(
            f"<tr><td>{e(a)}</td><td><strong>{e(b)}</strong></td><td>{e(c)}</td></tr>"
            for a, b, c in gate_rows
        )
        + "</tbody></table></div>"
    )

    site_rows_html = []
    for s in nine["sites"]:
        hist_str = f"{s['historical_best_submission']} ({s['historical_best_owner_reported_score']:.4f} owner-reported)"
        if s["latest_20261025_scored_submission"]:
            sc_str = f"{s['latest_20261025_scored_submission']} ({s['latest_20261025_owner_reported_score']:.4f} owner-reported)"
        else:
            sc_str = "None newly scored in prompt"
        ov_str = (
            "Self (#1 tech gates)"
            if s["site"] == "GEMSDOE24"
            else f"{100 * s['dprf1_3px_overlap_vs_site_artifact']:.2f}% (ρ={s['dprf1_spearman_vs_site_artifact']:+.3f})"
        )
        site_rows_html.append(
            f"<tr>"
            f'<td><strong><a href="{e(s["pages_url"])}" target="_blank" rel="noopener noreferrer">{e(s["site"])} ↗</a></strong><br><small><code>{e(s["inspected_main_commit"][:8])}</code></small></td>'
            f"<td><code>{e(hist_str)}</code><br><small>{e(s['historical_ancestry'])}</small></td>"
            f"<td><code>{e(s['inspected_artifact_file'])}</code><br><small>Recent prompt score: {e(sc_str)} · Apron 2–9 px: {100 * s['inspected_frac_2_to_9px']:.1f}% · &gt;2 km: {100 * s['inspected_frac_gt_20px']:.1f}%</small></td>"
            f"<td>{e(s['current_holdout_and_gate_summary'])}</td>"
            f"<td><code>{e(ov_str)}</code></td>"
            f"<td><strong>{e(s['executive_verdict'])}</strong></td>"
            f"</tr>"
        )
    nine_site_table = (
        '<section id="nine-site-executive-summary" aria-label="Executive summary across all 9 focus sites">'
        "<h2>Nine-Site Executive Summary (GEMSDOE24, 25, 27, 28, 30, 31, 32, 33, 36): Best Unique Candidate Analysis</h2>"
        "<p>All leaderboard figures from the prompt (including <code>GEMSDOE32</code> <code>0.2778</code>, <code>GEMSDOE27</code> <code>H29-CELF</code> <code>0.2190</code>, and conflicting leader snapshots <code>0.3195</code> vs <code>0.4413</code>) are <strong>UNVERIFIED-OWNER-REPORT</strong> (not <code>ORGANIZER-CONFIRMED</code>). "
        "Historical <code>H19-5</code> derivatives (<code>D1.5</code>, <code>D2.8</code>, <code>H27-4</code>, <code>H33-B2</code>, <code>GEMSDOE36 PINN</code>) cannot be copied or resubmitted. "
        "Among <strong>already-scored 2026-10-25 unique submissions</strong>, <code>GEMSDOE27</code> <code>H29-CELF</code> (<code>0.2190</code>) has the highest owner-reported result in this recent scored subset. A plausible, unproven explanation is that Dual-Partition Stitched-OOF preserved <code>44.3%</code> far-field (&gt;2 km) discovery whereas in-sample Stage-5 refits (<code>GVC1</code> <code>0.0859</code>, <code>H66-MGD</code> <code>0.0742</code>) dumped ~70% of dots into 200–900 m catalogue aprons. "
        "Among <strong>recorded local research GeoTIFFs</strong>, <strong><code>H24-DPRF1</code> (<code>GEMSDOE24</code>, HOLDOUT-DTI <code>0.16379</code>, 57/57 competing-method novelty PASS, <code>52.3%</code> &gt;2 km far-field, &le;49.12% 3-px overlap vs every focus site)</strong> is the local recorded point-best, not a harmonized cross-site winner and not unique under the literal all-entry rule; held at <code>DO_NOT_SUBMIT</code> under <code>gems-selector-v2-literal-quota-fail-closed</code> because literal novelty, independently verified quota and independent replay requirements are unmet.</p>"
        '<div class="tablewrap" tabindex="0" role="region" aria-label="Nine-site executive comparison table">'
        "<table><thead><tr><th>Focus Site</th><th>Historical Best (Do Not Copy)</th><th>Inspected Unique Artifact &amp; Spatial Profile</th><th>Holdout &amp; Gate Audit</th><th>H24-DPRF1 3-px Overlap</th><th>Executive Verdict</th></tr></thead><tbody>"
        + "".join(site_rows_html)
        + "</tbody></table></div>"
        '<p class="micro">Full SHA-256 &amp; commit-pinned cross-site receipt: <a href="data/nine_site_executive_summary_20261026.json" download>nine_site_executive_summary_20261026.json</a>.</p></section>'
    )

    note_block = (
        f'<div class="note" id="note-dprf1">{e(dl["note"])}</div>'
        '<div class="actions"><button class="button" data-copy="#note-dprf1" data-feedback="#copy-feedback-dprf1">'
        "Copy DPRF1 short note (&le;140 chars)</button>"
        f'<a class="button" href="downloads/{e(dl["note_file"])}" download>DPRF1 Note .txt</a></div>'
        '<p id="copy-feedback-dprf1" class="copyfeedback" aria-live="polite"></p>'
        f'<p class="micro">{len(dl["note"])} characters · maximum 140</p>'
    )

    hero_html = f"""<section id="dprf1-overview" class="hero" aria-label="Latest 2026-10-26 H24-DPRF1 Stitched-OOF Two-Regime GeoTIFF">
<div>
<div class="eyebrow">New 2026-10-26 Point-Best · H24-DPRF1 · 57/57 Competing-Method Novelty PASS</div>
<h2>Highest HOLDOUT-DTI (0.16379) &amp; Apron Cure.<br>Fail-closed selector v2: DO NOT SUBMIT.</h2>
<p class="lead"><strong><code>H24-DPRF1</code></strong> fuses 52 physical &amp; OpenEI GDR INGENIOUS hydrothermal channels (paleo-sinter, 2 m thermal probes, geothermometry, Miller–Singh tilt, 8-azimuth lineaments, and modality-aware <code>SAHG1</code> conduits) using <strong>Stratified <code>d_vis &ge; 300 m</code> negative sampling</strong>, <strong>3-tier Relief-Conditioned LiDAR-gap calibration</strong>, <strong>Dual-Partition Stitched-OOF</strong> (Quadrant + 45&deg; Diamond, zero in-sample predictions), and <strong>Two-Regime 300 m Submodular Allocation</strong>. <strong>Zero previous submission pixels were copied.</strong> It is <strong>not yet scored</strong> on DrivenData, cures <code>GVC1</code>'s 70.4% near-catalogue apron collapse (restoring <strong>52.3% &gt;2 km far-field</strong> dots), passes <strong>all 57 competing method rasters</strong> (max 3-px overlap <strong>55.78% &le; 70%</strong>) and <strong>83 peer blobs</strong> (<strong>54.94%</strong>), passes strict exact-file C2ST (AUC <code>{c2_cand["observed_auc"]:.4f}</code>), and remains <strong>NOT OK TO SUBMIT (<code>DO_NOT_SUBMIT</code>)</strong> under <code>gems-selector-v2-literal-quota-fail-closed</code>.</p>
{status_box}
<div class="actions">
<a class="button primary" href="downloads/{e(name)}" download="{e(name)}">↓ Download H24-DPRF1 .tif (strict [0,1]) — DO NOT SUBMIT</a>
<a class="button" href="downloads/{e(dl["zip_file"])}" download="{e(dl["zip_file"])}">↓ Single-GeoTIFF .zip (zeros outside)</a>
<a class="button" href="downloads/{e(dl["nan_file"])}" download="{e(dl["nan_file"])}">↓ NaN-outside twin .tif</a>
<a class="button" href="downloads/{e(dl["selector_file"])}">Selector v2 JSON — DO_NOT_SUBMIT</a>
<a class="button" href="downloads/{e(preflight_path.name)}">Automated preflight — DO_NOT_SUBMIT</a>
<a class="button" href="data/dprf1_run_card.json" download>DPRF1 JSON run card</a>
<a class="button" href="executive-summary.html">9-Site Executive Summary &amp; Guide →</a>
</div>
<p class="fileline">{e(name)}</p>
<p class="hash">SHA-256 {e(digest)} · ZIP SHA-256 {e(dl["zip_sha256"])} · NaN-twin SHA-256 {e(dl["nan_sha256"])}</p>
{note_block}
</div>
<aside class="card visual">
<div class="cardtop"><h2 class="metric-label">H24-DPRF1 HOLDOUT-DTI</h2><span class="badge amber">Not leaderboard scores</span></div>
<div class="result-number">{score["dti"]:.5f}</div>
<p class="micro">HOLDOUT-DTI · <code>{e(score["evaluator_version"])}</code> · {score["n_withheld_positive_pixels"]:,} withheld positives · 95% CI [{lo:.5f}, {hi:.5f}] · Paired Δ vs <code>oof_multiphysics_hgb_d3</code>: <strong>{paired_d3["paired_delta_dti"]:+.5f}</strong> [{d3_lo:+.5f}, {d3_hi:+.5f}] (4/4 folds) · Bridge 3.0 km: <strong>{br["dti"]:.5f}</strong></p>
<img class="raster-preview" src="assets/dprf1-preview.png" alt="Downsampled preview of H24-DPRF1 Dual-Partition Stitched-OOF fault dots (37,654 positive cells)">
<p class="micro">37,654 binary {{0,1}} dots · NE_LidarGapHeavy DTI <strong>{score["folds"][1]["dti"]:.5f}</strong> · SE DTI <strong>{score["folds"][3]["dti"]:.5f}</strong> · 52.3% &gt;2 km far-field</p>
</aside>
</section>
<section aria-label="H24-DPRF1 10-gate automated verification"><h2>H24-DPRF1 automated 10-gate &amp; selector v2 verification (no human-inspector fallback)</h2>{gate_table}</section>
{nine_site_table}"""

    exec_html = f"""<section id="dprf1-exec" class="card concurrent" aria-label="H24-DPRF1 executive status">
<h2>2026-10-26 Point-Best Candidate (<code>H24-DPRF1</code>) — DOWNLOAD: YES · SUBMIT: NO (<code>DO_NOT_SUBMIT</code>)</h2>
{status_box}
<div class="actions">
<a class="button primary" href="downloads/{e(name)}" download="{e(name)}">↓ Download H24-DPRF1 .tif (strict [0,1]) — DO NOT SUBMIT</a>
<a class="button" href="downloads/{e(dl["zip_file"])}" download="{e(dl["zip_file"])}">↓ Download Single-GeoTIFF .zip</a>
<a class="button" href="downloads/{e(dl["nan_file"])}" download="{e(dl["nan_file"])}">↓ Download NaN-outside twin .tif</a>
<a class="button" href="downloads/{e(dl["selector_file"])}">Selector v2 JSON</a>
<a class="button" href="downloads/{e(preflight_path.name)}">Automated preflight JSON</a>
<a class="button" href="downloads/{e(dl["checks_file"])}">Exact-file Validator JSON</a>
<a class="button" href="data/dprf1_run_card.json" download>DPRF1 JSON Run Card</a>
</div>
<p class="fileline">{e(name)}</p>
<p class="hash">SHA-256 {e(digest)}</p>
{note_block}
{gate_table}
</section>
{nine_site_table}"""

    research_html = f"""<section id="dprf1-research"><h2>2026-10-26 Breakthrough: H24-DPRF1 Dual-Partition Stitched-OOF &amp; Apron Redistribution Analysis (0.0859 owner-reported)</h2>
<div class="grid2"><article class="card"><h3>Three-Arm Preregistered Factorial on <code>SegmentHoldout</code> (not leaderboard scores)</h3>
<div class="tablewrap" tabindex="0" role="region" aria-label="H24-DPRF1 three-arm holdout comparison"><table><thead><tr><th>Arm / Baseline</th><th>Pooled <code>HOLDOUT-DTI</code></th><th>95% Bootstrap CI</th><th>NW</th><th>NE_LidarGap</th><th>SW</th><th>SE</th></tr></thead><tbody>
<tr><td><strong>Arm 1: <code>H24-DPRF1</code> (Stratified d&ge;3 + Two-Regime, packaged)</strong></td><td><strong>{score["dti"]:.5f}</strong></td><td>[{lo:.5f}, {hi:.5f}]</td><td><strong>{score["folds"][0]["dti"]:.5f}</strong></td><td><strong>{score["folds"][1]["dti"]:.5f}</strong></td><td><strong>{score["folds"][2]["dti"]:.5f}</strong></td><td><strong>{score["folds"][3]["dti"]:.5f}</strong></td></tr>
<tr><td>Arm 2: <code>DPRF1-SingleRegime</code> (100% primary ridge)</td><td>{arm2_dti:.5f}</td><td>[{experiment["arms"]["arm2_single_regime"]["holdout"]["ci95"]["interval"][0]:.5f}, {experiment["arms"]["arm2_single_regime"]["holdout"]["ci95"]["interval"][1]:.5f}]</td><td>{experiment["arms"]["arm2_single_regime"]["holdout"]["folds"][0]["dti"]:.5f}</td><td>{experiment["arms"]["arm2_single_regime"]["holdout"]["folds"][1]["dti"]:.5f}</td><td>{experiment["arms"]["arm2_single_regime"]["holdout"]["folds"][2]["dti"]:.5f}</td><td>{experiment["arms"]["arm2_single_regime"]["holdout"]["folds"][3]["dti"]:.5f}</td></tr>
<tr><td>Arm 3: <code>DPRF1-DeadZone9</code> (legacy d&ge;9 negative dead zone)</td><td>{arm3_dti:.5f}</td><td>[{experiment["arms"]["arm3_deadzone9"]["holdout"]["ci95"]["interval"][0]:.5f}, {experiment["arms"]["arm3_deadzone9"]["holdout"]["ci95"]["interval"][1]:.5f}]</td><td>{experiment["arms"]["arm3_deadzone9"]["holdout"]["folds"][0]["dti"]:.5f}</td><td>{experiment["arms"]["arm3_deadzone9"]["holdout"]["folds"][1]["dti"]:.5f}</td><td>{experiment["arms"]["arm3_deadzone9"]["holdout"]["folds"][2]["dti"]:.5f}</td><td>{experiment["arms"]["arm3_deadzone9"]["holdout"]["folds"][3]["dti"]:.5f}</td></tr>
<tr><td><code>B0: OOF-H24-Ridge</code> (30-ch ridge baseline)</td><td>{card["baselines_and_siblings_same_evaluator"]["B0_oof_h24_ridge"]["dti"]:.5f}</td><td>[{card["baselines_and_siblings_same_evaluator"]["B0_oof_h24_ridge"]["ci95"][0]:.5f}, {card["baselines_and_siblings_same_evaluator"]["B0_oof_h24_ridge"]["ci95"][1]:.5f}]</td><td>0.13426</td><td>0.17339</td><td>0.11339</td><td>0.15357</td></tr>
<tr><td><code>B1: OOF-Base-Submod</code> (30-ch matched submod baseline)</td><td>{card["baselines_and_siblings_same_evaluator"]["B1_oof_base_submod"]["dti"]:.5f}</td><td>[{card["baselines_and_siblings_same_evaluator"]["B1_oof_base_submod"]["ci95"][0]:.5f}, {card["baselines_and_siblings_same_evaluator"]["B1_oof_base_submod"]["ci95"][1]:.5f}]</td><td>0.14975</td><td>0.16713</td><td>0.11172</td><td>0.14253</td></tr>
<tr><td><code>oof_multiphysics_hgb_d3</code> (27-ch LiDAR-only baseline)</td><td>{card["baselines_and_siblings_same_evaluator"]["oof_multiphysics_hgb_d3"]["dti"]:.5f}</td><td>[{card["baselines_and_siblings_same_evaluator"]["oof_multiphysics_hgb_d3"]["ci95"][0]:.5f}, {card["baselines_and_siblings_same_evaluator"]["oof_multiphysics_hgb_d3"]["ci95"][1]:.5f}]</td><td>0.14613</td><td>0.13464</td><td>0.10490</td><td>0.14558</td></tr>
</tbody></table></div>
<p class="micro">Stratified <code>d_vis &ge; 300 m</code> negatives beat the legacy <code>d_vis &ge; 900 m</code> dead zone by <strong>{paired_dz["paired_delta_dti"]:+.5f}</strong> (95% CI [{dz_lo:+.5f}, {dz_hi:+.5f}], 4/4 folds won), while 3-tier relief-conditioned LiDAR-gap calibration lifts <code>SW</code> from <code>0.07993</code> (<code>RSHG1</code>) to <strong><code>0.12768</code></strong> and <code>NE_LidarGapHeavy</code> to <strong><code>0.21227</code></strong>.</p></article>
<article class="card"><h3>Possible explanation for owner-reported GVC1 0.0859 vs H29-CELF 0.2190 — not causal proof</h3>
<img class="raster-preview" src="assets/dprf1-preview.png" alt="Downsampled preview of H24-DPRF1 fault dots (37,654 positive cells)">
<p class="micro">Recorded distance forensics found near-catalogue clustering in <code>GVC1</code> (<code>0.0859</code> owner-reported) and <code>GEMSDOE25 H66-MGD</code> (<code>0.0742</code>) with <strong>70.4%</strong> and <strong>69.6%</strong> of their dots into 200–900 m halos around already-mapped faults (leaving only 8.5% and 3.0% &gt;2 km). DPRF1 combines multiple changes and records 200–900 m apron dots to <strong>{100 * dist["frac_2_to_9px_apron"]:.1f}%</strong>, restores <strong>{100 * dist["frac_gt_20px_farfield"]:.1f}%</strong> &gt;2 km far-field dot allocation, and passes all 57 competing method rasters (max 3-px overlap <strong>{100 * nov["method_lane_max_dot_overlap"]:.2f}%</strong> &le; 70%). <a href="https://github.com/buffedlizard55-lab/GEMSDOE24/blob/main/knowledge/19_preregistered_DPRF1_2026-10-26.md">DPRF1 preregistration →</a> · <a href="https://github.com/buffedlizard55-lab/GEMSDOE24/blob/main/knowledge/20_DPRF1_findings_and_9site_executive_summary_2026-10-26.md">DPRF1 PhD synthesis &amp; 9-site review →</a></p></article></div></section>"""
    return hero_html, exec_html, research_html


def cup1_packet(root):
    """Validate and render the 2026-10-26 H24-CUP1 packet from its exact receipts."""
    exp_path = root / "evidence/cup1_experiment_20261026.json"
    card_path = root / "evidence/cup1_run_card_20261026.json"
    if not (exp_path.exists() and card_path.exists()):
        return "", "", ""
    experiment = json.loads(exp_path.read_text())
    card = json.loads(card_path.read_text())
    name = card["submission_name"]
    target = root / "docs/downloads" / name
    if not target.exists() or sha256_file(target) != card["raster_sha256"]:
        raise ValueError("CUP1 exact-file SHA-256 disagrees with run card")
    if (
        card.get("ok_to_submit") is not False
        or card.get("ok_to_download") is not True
        or card.get("verdict") != "negative"
    ):
        raise ValueError("CUP1 packet must stay fail-closed (selector is a separate step)")
    note_path = root / "docs/downloads" / f"note-{name[:-4]}.txt"
    if len(card["note"]) > 140 or note_path.read_text().strip() != card["note"]:
        raise ValueError("CUP1 note missing, changed, or >140 characters")
    checks = json.loads((root / "docs/downloads" / f"checks-{name[:-4]}.json").read_text())
    template = root / "data/bridge/sample_submission.tif"
    for key in ("zero_outside", "nan_outside"):
        row = checks[key]
        fresh = check_variants(root / "docs/downloads" / row["file"], template)
        if (
            not fresh["format_valid"]
            or not row["format_valid"]
            or fresh.get("sha256") != row.get("sha256")
        ):
            raise ValueError(f"CUP1 download variant invalid or stale: {key}")
    preflight_path = target.with_suffix(".preflight.json")
    preflight = json.loads(preflight_path.read_text())
    if (
        preflight.get("artifact", {}).get("sha256") != card["raster_sha256"]
        or preflight.get("decision", {}).get("ready_to_submit") is not False
        or preflight.get("portal_range_diagnostic", {}).get("strict_whole_array_values_in_0_1")
        is not True
    ):
        raise ValueError("CUP1 exact-file preflight missing, stale, or does not fail closed")

    e = lambda s: escape(str(s), quote=True)  # noqa: E731
    h = card["holdout_dti"]
    ci = h["ci95"]
    lo, hi = ci["interval"] if isinstance(ci, dict) else ci
    gates = card["technical_gates"]
    nov = card["correlation_overlap_vs_registry"]
    c2 = card["c2st_nuisance_audit"]
    eligible = card["verdict"] == "promote"
    verdict_word = "SELECTOR-ELIGIBLE" if eligible else "DO_NOT_SUBMIT"
    status_box = (
        '<div class="status stopped" role="status"><strong>'
        f"RETAINED NEGATIVE RESEARCH (H24-CUP1, 2026-10-26) — DOWNLOAD: YES · SUBMIT: "
        f"{'SELECTOR STEP REQUIRED' if eligible else 'NO'} ({verdict_word}).</strong> "
        f"{e(card['submit_state'])}. Automated validation only — zero human-inspector fallback. "
        "No organizer-confirmed score exists; HOLDOUT-DTI below is a local measurement, not a leaderboard result or projection.</div>"
    )
    gate_rows = "".join(
        f"<tr><td>{e(k)}</td><td><strong>{'PASS' if v else 'FAIL'}</strong></td></tr>"
        for k, v in gates.items()
    )
    reasons = "".join(f"<li>{e(r)}</li>" for r in card["reasons"])
    hero = f"""<section class="hero" aria-label="H24-CUP1 unique GeoTIFF and automated gate">
<div>
<div class="eyebrow">Retained parallel research · H24-CUP1 compositional fronts + upward-continuation persistence</div>
<h1>Download the new .tif.<br>Read the gate before submitting.</h1>
<p class="lead"><strong><code>{e(name)}</code></strong> was generated in this repository on 2026-10-26 from physical layers only —
GeoDAWN K/Th/U ratio-grid compositional fronts plus RTP→TMI-150 m paired-trough persistence, fused with the shared
multi-physics stack and emitted as 37,654 sparse off-catalogue dots. <strong>Zero previous submission pixels were copied;</strong>
novelty was checked against the pinned registry before and after placement and failed. New content does not mean lane uniqueness passed.</p>
{status_box}
<div class="actions">
<a class="button primary" href="downloads/{e(name)}" download="{e(name)}">↓ Download CUP1 GeoTIFF (zeros outside, strict [0,1])</a>
<a class="button" href="downloads/{e(card["nan_submission_name"])}" download>↓ NaN-outside official-text .tif</a>
<a class="button" href="downloads/{e(card["zip_submission_name"])}" download>↓ Zeros .zip (single GeoTIFF)</a>
<a class="button" href="downloads/{e(preflight_path.name)}">Automated preflight receipt</a>
<a class="button" href="executive-summary.html">Executive summary &amp; how to submit →</a>
</div>
<p class="fileline">{e(name)}</p><p class="hash">SHA-256 {e(card["raster_sha256"])}</p>
<p class="micro"><strong>Portal note (≤140 chars):</strong></p>
<div class="note" id="note-cup1">{e(card["note"])}</div>
<div class="actions"><button class="button" data-copy="#note-cup1" data-feedback="#copy-feedback-cup1">Copy short note</button>
<a class="button" href="downloads/note-{e(name[:-4])}.txt" download>Note .txt</a></div>
<p id="copy-feedback-cup1" class="copyfeedback" aria-live="polite"></p>
</div>
<aside class="card visual"><div class="cardtop"><h3>HOLDOUT-DTI</h3><span class="badge amber">Local only — not a leaderboard score</span></div>
<div class="result-number">{h["dti"]:.5f}</div>
<p>HOLDOUT-DTI · {e(h["evaluator_version"])} · {h["n_withheld_positive_pixels"]:,} withheld positives · 95% CI [{lo:.5f}, {hi:.5f}]<br>
Matched B-GVC baseline {h["matched_baseline_bgvc_dti"]:.5f} · paired Δ {h["paired_delta"]:+.5f} (95% CI [{h["paired_delta_ci95"][0]:+.5f}, {h["paired_delta_ci95"][1]:+.5f}]) · recorded prior best (GVC1) 0.14876</p>
<p class="micro">Max competing 3-px dot overlap {nov["final_max_competing_overlap_within_3px"]:.4f} (gate ≤0.70) · max |ρ| {nov["final_method_lane_max_abs_rho"]:.4f} (gate ≤0.90) · C2ST AUC {c2["candidate_auc"]:.4f}</p>
</aside></section>"""
    exec_html = f"""<section aria-label="H24-CUP1 executive gate report"><h2>Parallel negative result: H24-CUP1 (2026-10-26)</h2>
{status_box}
<div class="actions"><a class="button primary" href="downloads/{e(name)}" download="{e(name)}">↓ Download CUP1 .tif</a>
<a class="button" href="downloads/checks-{e(name[:-4])}.json" download>Exact-file validator JSON</a>
<a class="button" href="data/cup1_download.json" download>Run-card download JSON</a></div>
<p class="fileline">{e(name)}</p><p class="hash">SHA-256 {e(card["raster_sha256"])}</p>
<div class="tablewrap"><table><thead><tr><th>Automated technical gate</th><th>Decision</th></tr></thead><tbody>{gate_rows}</tbody></table></div>
<p><strong>Why this state:</strong></p><ul>{reasons}</ul>
<p class="micro">Hypothesis: {e(card["hypothesis"])}<br>Named non-fault mimic: {e(card["named_non_fault_mimic"])}.
SGMC sparse off-catalogue diagnostic (not a gate, not a score): CUP1 {card["sgmc_sparse_diagnostic"]["cup1"]:.5f} vs matched B-GVC {card["sgmc_sparse_diagnostic"]["bgvc_matched"]:.5f}.</p>
</section>"""
    aucs = [v["pooled_auc"] for v in experiment["canary"]["features"].values()]
    research = f"""<section><h2>2026-10-26 H24-CUP1 — compositional fronts + upward-continuation persistence</h2>
<p>Preregistered before implementation (<code>knowledge/20_preregistered_CUP1_2026-10-26.md</code>, commit {e(experiment["preregistration_commit"])}).
Channels: 16 CUP + 18 GVC + 30 prepared base; fold-local calibrated HGB; shared submodular allocator
(37,654 dots, 2.5 px spacing, 2 px catalogue clearance). Leakage canary over {len(aucs)} features:
pooled AUC [{min(aucs):.4f}, {max(aucs):.4f}] (both polarities, gate 0.90).</p>
{exec_html}
<p><a href="https://github.com/buffedlizard55-lab/GEMSDOE24/blob/main/knowledge/20_preregistered_CUP1_2026-10-26.md">CUP1 preregistration →</a> ·
<a href="https://github.com/buffedlizard55-lab/GEMSDOE24/blob/main/evidence/cup1_run_card_20261026.json">CUP1 JSON run card →</a></p></section>"""
    return hero, exec_html, research


def gvc1_packet(root):
    """Validate and render the 2026-10-25 H24-GVC1 hydrothermal+tilt+lineament packet."""
    exp_path = root / "evidence/gvc1_experiment_20261025.json"
    card_path = root / "evidence/gvc1_run_card_20261025.json"
    c2st_path = root / "evidence/gvc1_c2st_audit_20261025.json"
    dl_path = root / "docs/data/gvc1_download.json"
    if not (exp_path.exists() and card_path.exists() and c2st_path.exists() and dl_path.exists()):
        return "", "", ""
    experiment = json.loads(exp_path.read_text())
    card = json.loads(card_path.read_text())
    c2st = json.loads(c2st_path.read_text())
    dl = json.loads(dl_path.read_text())
    name = dl["file"]
    digest = dl["sha256"]
    if (
        card.get("raster_sha256") != digest
        or card.get("submission_name") != name
        or dl.get("note") != card.get("note")
        or c2st.get("references", {}).get("e1_gvc1", {}).get("sha256") != digest
    ):
        raise ValueError("GVC1 checksum or identity disagree with run card or C2ST receipt")
    if (
        experiment.get("ok_to_submit") is not False
        or dl.get("ok_to_submit") is not False
        or card.get("ok_to_submit") is not False
        or card.get("verdict") != "negative"
    ):
        raise ValueError("A negative research page cannot grant GVC1 slot authorization")

    template = root / "data/bridge/sample_submission.tif"
    checks = json.loads((root / "docs/downloads" / dl["checks_file"]).read_text())
    for key in ("zero_outside", "nan_outside"):
        row = checks[key]
        target_variant = root / "docs/downloads" / row["file"]
        fresh = check_variants(target_variant, template)
        if (
            not fresh["format_valid"]
            or not row["format_valid"]
            or fresh.get("submission_authorized") is not False
            or any(fresh.get(field) != value for field, value in row.items())
        ):
            raise ValueError(f"GVC1 download variant invalid or stale: {key}")
    zip_target = root / "docs/downloads" / checks["nan_zip_file"]
    if sha256_file(zip_target) != checks["nan_zip_sha256"]:
        raise ValueError("GVC1 ZIP checksum disagrees with receipt")
    with zipfile.ZipFile(zip_target) as zf:
        if zf.namelist() != [checks["nan_outside"]["file"]]:
            raise ValueError("GVC1 ZIP entry list invalid")
        if (
            hashlib.sha256(zf.read(checks["nan_outside"]["file"])).hexdigest()
            != checks["nan_outside"]["sha256"]
        ):
            raise ValueError("GVC1 ZIP inner TIFF hash disagrees")

    note_path = root / "docs/downloads" / dl["note_file"]
    if len(dl["note"]) > 140 or note_path.read_text().strip() != dl["note"]:
        raise ValueError("GVC1 note is missing, changed, or exceeds 140 characters")

    target = root / "docs/downloads" / name
    preflight_path = target.with_suffix(".preflight.json")
    preflight = json.loads(preflight_path.read_text())
    if (
        preflight.get("artifact", {}).get("sha256") != digest
        or preflight.get("run_card", {}).get("artifact_sha256_matches") is not True
        or preflight.get("run_card", {}).get("artifact_name_matches") is not True
        or preflight.get("decision", {}).get("submission_status") != "DO_NOT_SUBMIT"
        or preflight.get("decision", {}).get("ready_to_submit") is not False
        or preflight.get("portal_range_diagnostic", {}).get("strict_whole_array_values_in_0_1")
        is not True
    ):
        raise ValueError("GVC1 exact-file preflight is missing, stale, or does not fail closed")

    e = lambda s: escape(str(s), quote=True)  # noqa: E731
    score = card["holdout"]
    lo, hi = score["ci95"]["interval"]
    base = card["baselines_same_evaluator"]
    b0_lo, b0_hi = base["B0_ci95"]
    b1_lo, b1_hi = base["B1_ci95"]
    paired = experiment["paired_comparisons"]["E1_vs_B1_physics_geothermal_gain"]
    d_lo, d_hi = paired["paired_delta_ci95"]
    e2 = experiment["holdout_results"]["E2_h24_gvc1_resid"]
    e2_lo, e2_hi = e2["ci95"]["interval"]
    nov = card["correlation_overlap_vs_registry"]
    cal_row = nov["calibration_control_summary"][0]
    top_comp = experiment["novelty_48_rasters"]["e1_final_dots"]["top_competing_comparators"][0]
    c2_aud = card["c2st_nuisance_audit"]
    canary_aucs = [v["pooled_auc"] for v in experiment["canary"]["features"].values()]
    canary_min, canary_max = min(canary_aucs), max(canary_aucs)

    status_box = (
        '<div class="status stopped" role="status">'
        "<strong>HIGHEST HOLDOUT ARTIFACT (H24-GVC1) — DOWNLOAD: YES · SUBMIT: NO. NOT OK TO SUBMIT (DO_NOT_SUBMIT).</strong> "
        "Automated gates ran end-to-end with zero human-inspector fallback: format/strict-[0,1] PASS, "
        f"48/48 two-polarity leakage canaries PASS ([{canary_min:.4f}, {canary_max:.4f}]), "
        f"matched OOF-Base gain PASS (HOLDOUT-DTI {score['dti']:.5f} vs {base['B1_oof_base_submod_dti']:.5f}, "
        f"paired Δ {paired['paired_delta_dti']:+.5f}, 95% CI [{d_lo:+.5f}, {d_hi:+.5f}], {paired['fold_wins']}/4 folds), "
        f"and exact-file C2ST nuisance audit PASS (AUC {c2_aud['candidate_auc']:.4f}, Holm p = {c2_aud['candidate_holm_p']:.3f}), "
        f"but 3-px dot overlap reaches {100 * nov['final_max_competing_overlap_within_3px']:.2f}% (&gt; 70%) against "
        f"prior 161k-px range-front ridges ({e(top_comp['registry_id'])}) plus {100 * cal_row['candidate_dot_overlap_within_3px']:.2f}% "
        f"on the retained spacing-5 lattice ({e(cal_row['registry_id'])}). Stopped immediately per Rule 1 "
        "(subsequently reported in sibling ledgers at 0.0859 OWNER-REPORTED due to in-sample train_mask=fp + neg>=9px halo collapse; diagnosed and resolved in 2026-10-26 H24-TRSG1 above).</div>"
    )
    gate_rows = [
        (
            "1. Exact-grid GeoTIFF & strict [0,1]",
            "PASS",
            f"Single-band float32, EPSG:32611, 3730×3292, 0 NaN/Inf inside footprint, all 12,279,160 cells in [0.0, 1.0]; {dl['pixel_count']:,} binary {{0,1}} dots (&ge;300 m clearance).",
        ),
        (
            "2. 48-feature two-polarity leakage canary",
            "PASS",
            f"All 30 scale-separated base + 18 label-free INGENIOUS hydrothermal/tilt/lineament features in [{canary_min:.4f}, {canary_max:.4f}] (well inside [0.10, 0.90]).",
        ),
        (
            "3. Reconstructed OOF HOLDOUT-DTI win",
            "PASS",
            f"HOLDOUT-DTI {score['dti']:.5f} [{lo:.5f}, {hi:.5f}] beats matched B1 OOF-Base-Submod ({base['B1_oof_base_submod_dti']:.5f}) by {paired['paired_delta_dti']:+.5f} (95% CI [{d_lo:+.5f}, {d_hi:+.5f}], 3/4 folds), B0 OOF-H24-Ridge ({base['B0_oof_h24_ridge_dti']:.5f}), and RSHG1 (0.12900).",
        ),
        (
            "4. Exact-file C2ST nuisance audit",
            "PASS",
            f"Labels audited first (AUC {c2_aud['labels_auc']:.4f}); H24-GVC1 AUC {c2_aud['candidate_auc']:.4f} (margin vs null p95 {c2_aud['candidate_margin_vs_null_p95']:+.4f}, Holm p = {c2_aud['candidate_holm_p']:.3f}).",
        ),
        (
            "5. Registry 3-px dot-overlap uniqueness",
            "FAIL",
            f"Surface max |ρ| = {nov['surface_max_abs_rank_correlation']:.4f} &le; 0.90 PASS and non-duplicate vs all 2026-10-25 GEMSDOE24 lanes (&le;60.7%), but 3-px overlap = {100 * nov['final_max_competing_overlap_within_3px']:.2f}% (&gt;70%) on {top_comp['registry_id']} ({Path(top_comp['file']).name}).",
        ),
        (
            "6. Separate weekly-slot selector",
            "BLOCKED",
            "Stopped automatically on Rule 1 overlap + unassigned coordinator lane + external weekly-quota selector. Zero competition slots spent.",
        ),
    ]
    gate_table = (
        '<div class="tablewrap"><table><thead><tr><th>Automated gate</th><th>Decision</th><th>Exact measurement / interpretation</th></tr></thead><tbody>'
        + "".join(
            f"<tr><td>{e(a)}</td><td><strong>{e(b)}</strong></td><td>{e(c)}</td></tr>"
            for a, b, c in gate_rows
        )
        + "</tbody></table></div>"
    )
    note_block = (
        f'<div class="note" id="note-gvc1">{e(dl["note"])}</div>'
        '<div class="actions"><button class="button" data-copy="#note-gvc1" data-feedback="#copy-feedback-gvc1">'
        "Copy GVC1 note (&le;140 chars)</button>"
        f'<a class="button" href="downloads/{e(dl["note_file"])}" download>GVC1 Note .txt</a></div>'
        '<p id="copy-feedback-gvc1" class="copyfeedback" aria-live="polite"></p>'
        f'<p class="micro">{len(dl["note"])} characters · maximum 140</p>'
    )
    hero_html = f"""<section class="hero" aria-label="Latest H24-GVC1 hydrothermal + lineament GeoTIFF and automated gate">
<div>
<div class="eyebrow">Highest GEMSDOE24 Holdout · H24-GVC1 INGENIOUS Hydrothermal + Tilt + 8-Azimuth Lineaments</div>
<h1>Genuine hydrothermal OOF win.<br>Automatic overlap stop: DO NOT SUBMIT.</h1>
<p class="lead"><strong><code>{e(name)}</code></strong> was computed independently from OpenEI GDR INGENIOUS paleo-sinter/travertine (899 pts), 2 m shallow temperature probes (599 pts), and geothermometry (2,331 pts) fused with Miller–Singh magnetic tilt derivatives, 8-azimuth DEM/gravity/magnetic lineaments, and a 300 m submodular kernel allocator. <strong>Zero previous submission pixels were copied.</strong> It is <strong>not yet scored</strong> on the competition portal, achieved a historical <code>HOLDOUT-DTI</code> result in GEMSDOE24 (<strong><code>{score["dti"]:.5f}</code></strong>, paired Δ <strong><code>{paired["paired_delta_dti"]:+.5f}</code></strong> with 95% CI <code>[{d_lo:+.5f}, {d_hi:+.5f}]</code> over matched <code>OOF-Base</code>) while passing strict C2ST (AUC <code>{c2_aud["candidate_auc"]:.4f}</code>, Holm <em>p</em> = <code>{c2_aud["candidate_holm_p"]:.3f}</code>), and is automatically marked <strong>NOT OK TO SUBMIT</strong> because 76.82% of its dots fall within 300 m of dense range-front ridges (<code>{e(top_comp["registry_id"])}</code>).</p>
{status_box}
<div class="actions">
<a class="button primary" href="downloads/{e(name)}" download="{e(name)}">↓ Download H24-GVC1 GeoTIFF (zeros outside, [0,1]) — DO NOT SUBMIT</a>
<a class="button" href="downloads/{e(dl["nan_file"])}" download="{e(dl["nan_file"])}">↓ NaN-outside .tif — DO NOT SUBMIT</a>
<a class="button" href="downloads/{e(dl["zip_file"])}" download="{e(dl["zip_file"])}">↓ NaN-outside .zip — DO NOT SUBMIT</a>
<a class="button" href="downloads/{e(preflight_path.name)}">Automated preflight — DO_NOT_SUBMIT</a>
<a class="button" href="data/gvc1_run_card_20261025.json" download>GVC1 JSON run card</a>
<a class="button" href="executive-summary.html">Executive submission guide →</a>
</div>
<p class="fileline">{e(name)}</p>
<p class="hash">SHA-256 {e(digest)} · NaN-twin SHA-256 {e(dl["nan_sha256"])}</p>
<p class="micro"><span class="badge blue">Format &amp; [0,1] PASS</span> <span class="badge blue">OOF Δ {paired["paired_delta_dti"]:+.5f} PASS</span> <span class="badge blue">C2ST {c2_aud["candidate_auc"]:.4f} PASS</span> <span class="badge danger">3-px Overlap 76.8% FAIL</span> <span class="badge gray">0 slots used</span></p>
{note_block}
</div>
<aside class="card visual">
<div class="cardtop"><h3>H24-GVC1 HOLDOUT-DTI</h3><span class="badge amber">Not leaderboard scores</span></div>
<div class="result-number">{score["dti"]:.5f}</div>
<p>HOLDOUT-DTI · <code>{e(score["evaluator_version"])}</code> · {score["n_withheld_positive_pixels"]:,} withheld positives · 95% CI [{lo:.5f}, {hi:.5f}] · Paired Δ vs matched OOF-Base: <strong>{paired["paired_delta_dti"]:+.5f}</strong> [{d_lo:+.5f}, {d_hi:+.5f}] ({paired["fold_wins"]}/4 folds)</p>
<img class="raster-preview" src="assets/gvc1-preview.png" alt="Downsampled preview of H24-GVC1 independently computed fault dots (37,654 positive cells)">
<p class="micro">37,654 binary {{0,1}} dots · NW fold DTI {score["folds"][0]["dti"]:.5f} (+0.02387 vs OOF-Base) · SE fold DTI {score["folds"][3]["dti"]:.5f} (+0.02299)</p>
</aside>
</section>
<section aria-label="H24-GVC1 automated gate breakdown"><h2>H24-GVC1 automated validation gates (zero human-inspector fallback)</h2>{gate_table}</section>"""

    exec_html = f"""<section class="card concurrent" aria-label="H24-GVC1 submission status">
<h2>Highest Holdout Artifact: <code>{e(name)}</code> — DOWNLOAD: YES · SUBMIT: NO</h2>
{status_box}
<div class="actions">
<a class="button primary" href="downloads/{e(name)}" download="{e(name)}">↓ Download H24-GVC1 GeoTIFF (zeros outside) — DO NOT SUBMIT</a>
<a class="button" href="downloads/{e(dl["nan_file"])}" download="{e(dl["nan_file"])}">↓ GVC1 NaN-outside twin — DO NOT SUBMIT</a>
<a class="button" href="downloads/{e(dl["zip_file"])}" download="{e(dl["zip_file"])}">↓ GVC1 NaN-outside .zip — DO NOT SUBMIT</a>
<a class="button" href="downloads/{e(preflight_path.name)}">GVC1 Automated preflight JSON</a>
<a class="button" href="downloads/{e(dl["checks_file"])}">GVC1 Exact-file validator JSON</a>
<a class="button" href="data/gvc1_run_card_20261025.json" download>GVC1 JSON run card</a>
</div>
<p class="fileline">{e(name)} · SHA-256 <code>{e(digest)}</code></p>
{note_block}
{gate_table}
</section>"""

    b0_folds = {r["fold"]: r for r in experiment["holdout_results"]["B0_oof_h24_ridge"]["folds"]}
    b1_folds = {r["fold"]: r for r in experiment["holdout_results"]["B1_oof_base_submod"]["folds"]}
    e2_folds = {r["fold"]: r for r in experiment["holdout_results"]["E2_h24_gvc1_resid"]["folds"]}
    e1_folds = {r["fold"]: r for r in experiment["holdout_results"]["E1_h24_gvc1"]["folds"]}
    fold_rows = "".join(
        f"<tr><td><code>{e(fn)}</code></td><td><strong>{e1_folds[fn]['dti']:.5f}</strong></td><td>{e2_folds[fn]['dti']:.5f}</td><td>{b1_folds[fn]['dti']:.5f}</td><td>{b0_folds[fn]['dti']:.5f}</td><td>{e1_folds[fn]['n_emitted']:,}</td></tr>"
        for fn in ("NW", "NE_LidarGapHeavy", "SW", "SE")
    )
    research_html = f"""<section><h2>2026-10-25 Continuation Breakthrough &amp; Overlap Stop: H24-GVC1 Geothermal-Vent Upflow + Tilt + Lineament Submodular Detector</h2>
<div class="grid2"><article class="card"><h3>HOLDOUT-DTI vs Reconstructed OOF Baselines (not leaderboard scores)</h3>
<div class="tablewrap"><table><thead><tr><th>Fold / Summary</th><th>E1: H24-GVC1</th><th>E2: GVC1-Resid</th><th>B1: OOF-Base-Submod</th><th>B0: OOF-H24-Ridge</th><th>GVC1 Dots</th></tr></thead><tbody>
{fold_rows}
<tr><td><strong>Pooled <code>gems-segment-pooled-v1</code></strong></td><td><strong>{score["dti"]:.5f}</strong> [{lo:.5f}, {hi:.5f}]</td><td>{e2["dti"]:.5f} [{e2_lo:.5f}, {e2_hi:.5f}]</td><td>{base["B1_oof_base_submod_dti"]:.5f} [{b1_lo:.5f}, {b1_hi:.5f}]</td><td>{base["B0_oof_h24_ridge_dti"]:.5f} [{b0_lo:.5f}, {b0_hi:.5f}]</td><td>{dl["pixel_count"]:,}</td></tr>
</tbody></table></div>
<p class="micro">Adding 18 label-free OpenEI GDR INGENIOUS hydrothermal-upflow (paleo-sinter/travertine, 2 m shallow temperature probes, wells/springs geothermometry), Miller–Singh TMI tilt, and 8-azimuth DEM/gravity/magnetic lineament features to the matched 30-feature submodular baseline lifts pooled <code>HOLDOUT-DTI</code> by <strong>{paired["paired_delta_dti"]:+.5f}</strong> (10 km block-bootstrap 95% CI <strong>[{d_lo:+.5f}, {d_hi:+.5f}]</strong>, winning 3/4 quadrants: NW <code>+0.02387</code>, SE <code>+0.02299</code>, NE <code>+0.00034</code>). Linear road/claim/block residualization (<code>E2</code>) erases the gain (<code>{e2["dti"]:.5f}</code>) because Great Basin roads and historic mining claims follow range-bounding valleys — while <code>E1</code> already passes strict exact-file C2ST without residualization (AUC <strong><code>{c2_aud["candidate_auc"]:.4f}</code></strong>, Holm <em>p</em> = <code>{c2_aud["candidate_holm_p"]:.3f}</code>).</p></article>
<article class="card"><h3>4 Ranked Hypotheses, Mimics &amp; Supervised Range-Front Convergence</h3>
<img class="raster-preview" src="assets/gvc1-preview.png" alt="Downsampled preview of H24-GVC1 fault dots (37,654 positive cells)">
<p class="micro">Ranked pre-run in commit <code>1bc8ace0</code>: (1) <code>H24-GVC1</code> hydrothermal+tilt+lineaments (executed), (2) <code>H24-CSB2</code> tensor curvature step-over saddles, (3) <code>H24-MDE3</code> multi-depth potential-field persistence, (4) <code>H24-INSAR4</code> NASA OPERA Sentinel-1 InSAR deformation (deferred, network-blocked). Named mimics: welded ash-flow tuff hogbacks/caldera margins, lateral fan thermal outflow plumes, and Pleistocene Lahontan shorezone tufa. Although non-duplicate (&le;60.7%) against every 2026-10-25 GEMSDOE24 lane, 76.82% of <code>H24-GVC1</code> dots fall within 300 m of 161,366-px <code>gems10-h25-ctx-ridge</code> (<code>registry-041</code>, raw &rho; = 0.0445), triggering an immediate Rule 1 stop. <a href="https://github.com/buffedlizard55-lab/GEMSDOE24/blob/main/knowledge/12_preregistration_GVC1_2026-10-25.md">GVC1 preregistration →</a> · <a href="https://github.com/buffedlizard55-lab/GEMSDOE24/blob/main/knowledge/13_GVC1_findings_2026-10-25.md">GVC1 findings &amp; source ledger →</a></p></article></div></section>"""
    return hero_html, exec_html, research_html


def rshg1_packet(root):
    """Validate and render the latest 2026-10-25 H24-RSHG1 packet (hero, executive, research)."""
    report_path = root / "evidence/rshg1_experiment_20261025.json"
    card_path = root / "evidence/rshg1_run_card_20261025.json"
    dl_path = root / "docs/data/rshg1_download.json"
    if not (report_path.exists() and card_path.exists() and dl_path.exists()):
        return "", "", ""
    report = json.loads(report_path.read_text())
    card = json.loads(card_path.read_text())
    dl = json.loads(dl_path.read_text())
    name = dl["file"]
    digest = dl["sha256"]
    if (
        card.get("raster_sha256") != digest
        or card.get("submission_name") != name
        or dl.get("note") != card.get("note")
    ):
        raise ValueError("RSHG1 checksum or identity disagree with run card")
    target = root / "docs/downloads" / name
    checks = json.loads((root / "docs/downloads" / dl["checks_file"]).read_text())
    if (
        sha256_file(target) != digest
        or checks["zero_outside"].get("sha256") != digest
        or checks["zero_outside"].get("format_valid") is not True
        or checks["zero_outside"].get("submission_authorized") is not False
    ):
        raise ValueError("RSHG1 checksum or exact-file validator disagrees")
    nan_target = root / "docs/downloads" / dl["nan_file"]
    if (
        sha256_file(nan_target) != dl["nan_sha256"]
        or checks["nan_outside"].get("sha256") != dl["nan_sha256"]
        or checks["nan_outside"].get("format_valid") is not True
        or checks["nan_outside"].get("submission_authorized") is not False
    ):
        raise ValueError("RSHG1 NaN-outside companion checksum or validator disagrees")
    if (
        report.get("ok_to_submit") is not False
        or dl.get("ok_to_submit") is not False
        or card.get("ok_to_submit") is not False
        or card.get("verdict") != "negative"
    ):
        raise ValueError("A negative research page cannot grant RSHG1 slot authorization")
    note_path = root / "docs/downloads" / dl["note_file"]
    if len(dl["note"]) > 140 or note_path.read_text().strip() != dl["note"]:
        raise ValueError("RSHG1 note is missing, changed, or exceeds 140 characters")
    preflight_path = target.with_suffix(".preflight.json")
    preflight = json.loads(preflight_path.read_text())
    if (
        preflight.get("artifact", {}).get("sha256") != digest
        or preflight.get("run_card", {}).get("artifact_sha256_matches") is not True
        or preflight.get("run_card", {}).get("artifact_name_matches") is not True
        or preflight.get("decision", {}).get("submission_status") != "DO_NOT_SUBMIT"
        or preflight.get("decision", {}).get("ready_to_submit") is not False
        or preflight.get("portal_range_diagnostic", {}).get("strict_whole_array_values_in_0_1")
        is not True
    ):
        raise ValueError("RSHG1 exact-file preflight is missing, stale, or does not fail closed")
    e = lambda s: escape(str(s), quote=True)  # noqa: E731
    h_main = card["holdout"]
    lo, hi = h_main["ci95"]["interval"]
    h_oof = card["reconstructed_oof_multiphysics_baseline"]
    olo, ohi = h_oof["ci95"]["interval"]
    h_ab_b = report["ablation_calibrated_pointwise"]
    blo, bhi = h_ab_b["ci95"]["interval"]
    h_ab_a = report["ablation_uncalibrated_pointwise"]
    alo, ahi = h_ab_a["ci95"]["interval"]
    h_br = card["bridge_protocol_holdout"]
    brlo, brhi = h_br["ci95"]
    nov = card["correlation_overlap_vs_registry"]
    c2st = card["exact_file_nuisance_audit"]
    canary = card["leakage_canary"]
    p_oof = card["paired_comparisons"]["rshg1_minus_reconstructed_oof_hgb_d3"]

    status_box = (
        '<div class="status stopped" role="status">'
        "<strong>LATEST ARTIFACT (H24-RSHG1) — DOWNLOAD: YES · SUBMIT: NO. NOT OK TO SUBMIT (DO_NOT_SUBMIT).</strong> "
        "Automated gates ran end-to-end with zero human-inspector fallback: format/strict-[0,1] PASS, "
        f"42-feature leakage canary PASS, and exact-file C2ST nuisance audit PASS (AUC {c2st['observed_auc']:.4f}, Holm p = {c2st['holm_p_value']:.3f}), "
        f"but locked primary HOLDOUT-DTI ({h_main['dti']:.5f}) statistically ties the OOF multi-physics baseline ({h_oof['dti']:.5f}, Δ {p_oof['delta_dti']:+.5f}) "
        f"and 3-px dot overlap reaches {nov['method_lane_max_overlap_within_3px']:.4f} (&gt; 0.70) against prior supervised ridges.</div>"
    )
    gate_rows = [
        (
            "1. Exact-grid GeoTIFF & strict [0,1]",
            "PASS",
            f"Single-band float32, EPSG:32611, 3730×3292, 0 NaN/Inf, all 12,279,160 cells in [0.0, 1.0]; {dl['pixel_count']:,} off-catalogue dots (>200 m from public catalogue).",
        ),
        (
            "2. Two-polarity leakage canary",
            "PASS",
            f"42/42 channels checked on SegmentHoldout (worst feature {canary['worst_feature']} pooled AUC {canary['worst_pooled_auc']:.4f}, within [0.10, 0.90]; OOF prob AUC {canary['oof_calibrated_prob_pooled_auc']:.4f}).",
        ),
        (
            "3. Exact-file C2ST nuisance audit",
            "PASS",
            f"Spatial-block C2ST AUC {c2st['observed_auc']:.4f} ≤ null p95 {c2st['null_p95']:.4f} (Holm p = {c2st['holm_p_value']:.3f}; claim_m AUC {c2st['single_feature_auc_descriptive']['claim_m']:.4f} vs SAHG1 0.5826 FAIL).",
        ),
        (
            "4. Comparable OOF HOLDOUT-DTI win",
            "FAIL (TIE)",
            f"Primary H24-RSHG1 HOLDOUT-DTI {h_main['dti']:.5f} [{lo:.5f}, {hi:.5f}] ties oof_multiphysics_hgb_d3 {h_oof['dti']:.5f} (Δ {p_oof['delta_dti']:+.5f}; calibrated pointwise ablation {h_ab_b['dti']:.5f}; 3 km bridge {h_br['dti']:.5f}).",
        ),
        (
            "5. Registry & peer 3-px dot novelty",
            "FAIL",
            f"Zero copied pixels & surface max |ρ| = {nov['surface_max_abs_rank_correlation']:.4f} ≤ 0.90 PASS, but 3-px dot overlap = {nov['method_lane_max_overlap_within_3px']:.4f} (> 0.70) on gems10-h25-ctx-ridge & {nov['peer_blobs_max_overlap_within_3px']:.4f} on gems28 (plus {nov['literal_all_entries_max_overlap_within_3px']:.4f} on registry-039 lattice).",
        ),
        (
            "6. Separate weekly-slot selector",
            "DO_NOT_SUBMIT",
            "Automatic fail-closed decision (preflight: DO_NOT_SUBMIT). Zero DrivenData uploads or live competition slots spent.",
        ),
    ]
    gate_table = (
        '<div class="tablewrap"><table><thead><tr><th>H24-RSHG1 automated gate</th><th>Decision</th><th>Measured evidence (not leaderboard scores)</th></tr></thead><tbody>'
        + "".join(
            f"<tr><td>{e(a)}</td><td><strong>{e(b)}</strong></td><td>{e(c)}</td></tr>"
            for a, b, c in gate_rows
        )
        + "</tbody></table></div>"
    )
    note_block = (
        f'<div class="note" id="note-rshg1">{e(dl["note"])}</div>'
        '<div class="actions">'
        '<button class="button" data-copy="#note-rshg1" data-feedback="#copy-feedback-rshg1">Copy RSHG1 short note</button>'
        f'<a class="button" href="downloads/{e(dl["note_file"])}" download>RSHG1 note .txt</a>'
        "</div>"
        '<p id="copy-feedback-rshg1" class="copyfeedback" aria-live="polite"></p>'
        f'<p class="micro">{len(dl["note"])} characters · maximum 140</p>'
    )
    hero_html = f"""<section class="hero" aria-label="Latest H24-RSHG1 unique GeoTIFF and automated gate">
<div>
<div class="eyebrow">Latest 2026-10-25 experiment · H24-RSHG1 42-channel regime-calibrated HGB</div>
<h1>Unique multi-physics GeoTIFF.<br>Automated gate: DO NOT SUBMIT.</h1>
<p class="lead"><strong><code>{e(name)}</code></strong> was generated from scratch across 100% of the active footprint (including the 31.8% 3DEP LiDAR gap) using 42 physical channels, fold-local <code>NaN</code>-preserving nuisance residualization, and training-only regime log-odds calibration. <strong>Zero prior submission pixels were read or copied.</strong> It is <strong>not yet scored</strong> by the organizer, solves the C2ST nuisance audit (AUC <code>{c2st["observed_auc"]:.4f}</code>, Holm <em>p</em> = <code>{c2st["holm_p_value"]:.3f}</code>), and doubles prior unsupervised <code>HOLDOUT-DTI</code> (<code>{h_main["dti"]:.5f}</code> primary; <code>{h_ab_b["dti"]:.5f}</code> calibrated pointwise), but is automatically marked <strong>NOT OK TO SUBMIT</strong> because its locked primary arm ties <code>oof_multiphysics_hgb_d3</code> (<code>{h_oof["dti"]:.5f}</code>) and exceeds the 70% 3-px overlap cap against convergent supervised ridges.</p>
{status_box}
<div class="actions">
<a class="button primary" href="downloads/{e(name)}" download="{e(name)}">↓ Download H24-RSHG1 GeoTIFF (zeros outside, [0,1]) — DO NOT SUBMIT</a>
<a class="button" href="downloads/{e(dl["nan_file"])}" download="{e(dl["nan_file"])}">↓ NaN-outside twin — DO NOT SUBMIT</a>
<a class="button" href="downloads/{e(preflight_path.name)}">Automated preflight — DO_NOT_SUBMIT</a>
<a class="button" href="data/rshg1_run_card.json" download>RSHG1 JSON run card</a>
<a class="button" href="executive-summary.html">Executive submission guide →</a>
</div>
<p class="fileline">{e(name)}</p>
<p class="hash">SHA-256 {e(digest)} · NaN-twin SHA-256 {e(dl["nan_sha256"])}</p>
<p class="micro"><span class="badge blue">Format &amp; [0,1] PASS</span> <span class="badge blue">C2ST {c2st["observed_auc"]:.4f} PASS</span> <span class="badge danger">OOF Tie / Overlap 0.727 FAIL</span> <span class="badge gray">0 slots used</span></p>
{note_block}
</div>
<aside class="card visual">
<div class="cardtop"><h3>H24-RSHG1 HOLDOUT-DTI</h3><span class="badge amber">Not leaderboard scores</span></div>
<div class="result-number">{h_main["dti"]:.5f}</div>
<p>HOLDOUT-DTI · <code>{e(h_main["evaluator_version"])}</code> · {h_main["n_withheld_positive_pixels"]:,} withheld positives · 95% CI [{lo:.5f}, {hi:.5f}] · Calibrated pointwise diagnostic: <strong>{h_ab_b["dti"]:.5f}</strong> · 3.0 km bridge: <strong>{h_br["dti"]:.5f}</strong></p>
<img class="raster-preview" src="assets/rshg1-preview.png" alt="Downsampled preview of H24-RSHG1 independently computed fault dots (37,722 positive cells)">
<p class="micro">37,722 off-catalogue fault dots · NE_LidarGapHeavy fold DTI {h_main["folds"][1]["dti"]:.5f} (+0.03821 vs OOF baseline)</p>
</aside>
</section>
<section aria-label="H24-RSHG1 automated gate breakdown"><h2>H24-RSHG1 automated validation gates (zero human-inspector fallback)</h2>{gate_table}</section>"""

    exec_html = f"""<section class="card concurrent" aria-label="Latest H24-RSHG1 submission status">
<h2>Latest 2026-10-25 Artifact: <code>{e(name)}</code> — DOWNLOAD: YES · SUBMIT: NO</h2>
{status_box}
<div class="actions">
<a class="button primary" href="downloads/{e(name)}" download="{e(name)}">↓ Download H24-RSHG1 GeoTIFF (zeros outside) — DO NOT SUBMIT</a>
<a class="button" href="downloads/{e(dl["nan_file"])}" download="{e(dl["nan_file"])}">↓ RSHG1 NaN-outside twin — DO NOT SUBMIT</a>
<a class="button" href="downloads/{e(preflight_path.name)}">RSHG1 Automated preflight JSON</a>
<a class="button" href="downloads/{e(dl["checks_file"])}">RSHG1 Exact-file validator JSON</a>
<a class="button" href="data/rshg1_run_card.json" download>RSHG1 JSON run card</a>
</div>
<p class="fileline">{e(name)} · SHA-256 <code>{e(digest)}</code></p>
{note_block}
{gate_table}
</section>"""

    fold_rows = "".join(
        f"<tr><td><code>{e(f['fold'])}</code></td><td><strong>{f['dti']:.5f}</strong></td><td>{b['dti']:.5f}</td><td>{u['dti']:.5f}</td><td>{o['dti']:.5f}</td><td>{f['n_emitted']:,}</td></tr>"
        for f, b, u, o in zip(
            h_main["folds"],
            h_ab_b["folds"],
            h_ab_a["folds"],
            h_oof["folds"],
            strict=True,
        )
    )
    research_html = f"""<section><h2>Latest 2026-10-25 Execution: H24-RSHG1 Regime-Calibrated 42-Channel Multi-Physics + Strike-Hydro-Geomorph</h2>
<div class="grid2"><article class="card"><h3>HOLDOUT-DTI &amp; Per-Fold Mechanism Attribution (not leaderboard scores)</h3>
<div class="tablewrap"><table><thead><tr><th>Fold / Summary</th><th>Primary RSHG1</th><th>Ablation B (Pointwise Cal.)</th><th>Ablation A (Uncal.)</th><th>OOF HGB Baseline</th><th>RSHG1 Dots</th></tr></thead><tbody>
{fold_rows}
<tr><td><strong>Pooled <code>gems-segment-pooled-v1</code></strong></td><td><strong>{h_main["dti"]:.5f}</strong> [{lo:.5f}, {hi:.5f}]</td><td><strong>{h_ab_b["dti"]:.5f}</strong> [{blo:.5f}, {bhi:.5f}]</td><td>{h_ab_a["dti"]:.5f} [{alo:.5f}, {ahi:.5f}]</td><td>{h_oof["dti"]:.5f} [{olo:.5f}, {ohi:.5f}]</td><td>{dl["pixel_count"]:,}</td></tr>
</tbody></table></div>
<p class="micro">Unlocking the 31.8% 3DEP LiDAR gap via tree <code>NaN</code> routing + Miller &amp; Singh tilt-zero sharpness + DEM-Hessian ridge + Th-normalized K alteration jumped <code>NE_LidarGapHeavy</code> from <code>0.13464</code> to <strong><code>0.17285</code></strong> (<code>0.17365</code> pointwise). <code>Ablation B</code> (<code>0.13137</code>) was a historical <code>HOLDOUT-DTI</code> point-best at execution; post-hoc <code>K_300</code> kernel smoothing cost <code>-0.00238</code>, and uniform LiDAR-gap tail matching over-allocated dots in flat <code>SW</code> valley gaps.</p></article>
<article class="card"><h3>C2ST Nuisance Breakthrough &amp; Supervised Convergence</h3>
<img class="raster-preview" src="assets/rshg1-preview.png" alt="Downsampled preview of H24-RSHG1 fault dots (37,722 positive cells)">
<p class="micro">Exact-file C2ST AUC dropped from <code>0.5826</code> (SAHG1 FAIL) to <strong><code>{c2st["observed_auc"]:.4f}</code></strong> (null p95 <code>{c2st["null_p95"]:.4f}</code>, Holm <em>p</em> = <code>{c2st["holm_p_value"]:.3f}</code>, <code>claim_m</code> AUC <code>{c2st["single_feature_auc_descriptive"]["claim_m"]:.4f}</code> — <strong>PASS</strong>). Surface max |ρ| = <code>{nov["surface_max_abs_rank_correlation"]:.4f}</code> ≤ 0.90 with zero copied pixels, while 72.69% of predicted off-catalogue dots independently converge within 300 m of <code>gems10-h25-ctx-ridge</code> (<code>0.7233</code> on <code>gems28</code>). <a href="https://github.com/buffedlizard55-lab/GEMSDOE24/blob/main/knowledge/17_preregistered_RSHG1_2026-10-25.md">RSHG1 preregistration →</a> · <a href="https://github.com/buffedlizard55-lab/GEMSDOE24/blob/main/knowledge/18_RSHG1_findings_2026-10-25.md">RSHG1 PhD synthesis &amp; findings →</a></p></article></div></section>"""
    return hero_html, exec_html, research_html


def concurrent_fuse(root):
    """Validate and render the 2026-10-25 H24-FUSE (RAW / RESID / HCW) packet."""
    report_path = root / "evidence/hcw_experiment_20261025.json"
    if not report_path.exists():
        return ""
    report = json.loads(report_path.read_text())
    card = json.loads((root / "evidence/hcw_run_card_20261025.json").read_text())
    dl = json.loads((root / "docs/data/hcw_download.json").read_text())
    name = dl["file"]
    digest = dl["sha256"]
    if (
        card.get("raster_sha256") != digest
        or card.get("submission_name") != name
        or dl.get("note") != card.get("note")
    ):
        raise ValueError("FUSE checksum or identity disagree with run card")
    target = root / "docs/downloads" / name
    checks = json.loads((root / "docs/downloads" / dl["checks_file"]).read_text())
    if (
        sha256_file(target) != digest
        or checks["zero_outside"].get("sha256") != digest
        or checks["zero_outside"].get("format_valid") is not True
        or checks["zero_outside"].get("submission_authorized") is not False
        or checks["zero_outside"].get("ok_to_upload") is not False
    ):
        raise ValueError("FUSE checksum or exact-file validator disagrees")
    nan_target = root / "docs/downloads" / dl["nan_file"]
    if (
        sha256_file(nan_target) != dl["nan_sha256"]
        or checks["nan_outside"].get("sha256") != dl["nan_sha256"]
        or checks["nan_outside"].get("format_valid") is not True
        or checks["nan_outside"].get("submission_authorized") is not False
        or checks["nan_outside"].get("ok_to_upload") is not False
    ):
        raise ValueError("FUSE NaN-outside companion checksum or validator disagrees")
    if (
        report.get("ok_to_submit") is not False
        or dl.get("ok_to_submit") is not False
        or card.get("ok_to_submit") is not False
        or card.get("verdict") != "negative"
    ):
        raise ValueError("A negative research page cannot grant FUSE slot authorization")
    note_path = root / "docs/downloads" / dl["note_file"]
    if len(dl["note"]) > 140 or note_path.read_text().strip() != dl["note"]:
        raise ValueError("FUSE note is missing, changed, or exceeds 140 characters")
    preflight_path = target.with_suffix(".preflight.json")
    preflight = json.loads(preflight_path.read_text())
    if (
        preflight.get("artifact", {}).get("sha256") != digest
        or preflight.get("run_card", {}).get("artifact_sha256_matches") is not True
        or preflight.get("run_card", {}).get("artifact_name_matches") is not True
        or preflight.get("decision", {}).get("submission_status") != "DO_NOT_SUBMIT"
        or preflight.get("decision", {}).get("ready_to_submit") is not False
        or preflight.get("portal_range_diagnostic", {}).get("strict_whole_array_values_in_0_1")
        is not True
    ):
        raise ValueError("FUSE exact-file preflight is missing, stale, or does not fail closed")
    e = lambda s: escape(str(s), quote=True)  # noqa: E731
    h_main = card["holdout"]
    lo, hi = h_main["ci95"]["interval"]
    arms = card["arms_holdout_summary"]
    h_bridge = card["bridge_protocol_holdout"]
    blo, bhi = h_bridge["ci95"]
    nov = card["correlation_overlap_vs_registry"]
    c2st = card["exact_file_nuisance_audit"]
    return f"""<aside class="card concurrent" aria-label="H24-FUSE residualized conduit OOF-HGB experiment">
<h3>Latest 2026-10-25 Unique Submission GeoTIFF: H24-FUSE-HCW — DOWNLOAD: YES · SUBMIT: NO (NOT OK TO SUBMIT)</h3>
<p>Executes the documented Next Step #4: fold-local 31-channel <code>HistGradientBoostingClassifier</code> fusing 27 prepared geophysical/LiDAR/DEM channels with <code>SAHG1</code> strike-projected scarp (<code>G_sat</code>), stable-Th K/U alteration (<code>R_alt</code>), basement/strain step (<code>B_step</code>), and hydrothermal conduit interaction (<code>H_conduit</code>) inside a verified 9×9 discrete support mask, with training-only nuisance residualization (<code>NuisanceResidualizer</code> on <code>road_m</code>, <code>claim_m</code>, <code>block_1..4</code>) and hydrothermal-conduit priority weighting (<strong>no copied submission pixels</strong>).</p>
<p><strong>Key scientific findings across the 3 preregistered arms:</strong>
(1) Unresidualized <code>FUSE-RAW</code> matches the OOF baseline (<strong>HOLDOUT-DTI {arms["fuse_raw"]["dti"]:.5f}</strong> vs. <code>0.13000</code>), but <strong>fails prospective method-lane novelty</strong> (max 3-px dot overlap <code>{arms["fuse_raw"]["method_lane_max_overlap_within_3px"]:.4f}</code> &gt; 0.70 against <code>registry-006</code> topographic scarp ridges).
(2) Training-only nuisance residualization (<code>FUSE-RESID</code>, <strong>HOLDOUT-DTI {arms["fuse_resid"]["dti"]:.5f}</strong>) eliminates accessibility/block confounding — reducing exact-file C2ST AUC from <code>0.5826</code> (SAHG1) to <strong><code>{arms["fuse_resid"]["c2st_auc"]:.4f}</code></strong> (Holm <em>p</em> = <code>{arms["fuse_resid"]["c2st_holm_p"]:.3f}</code>, <strong>PASS</strong>) — and passes prospective method-lane novelty (overlap <code>{arms["fuse_resid"]["method_lane_max_overlap_within_3px"]:.4f}</code> ≤ 0.70).
(3) Hydrothermal-conduit weighting (<code>FUSE-HCW</code>, packaged below) achieves <strong>HOLDOUT-DTI {h_main["dti"]:.5f}</strong> (95% CI [{lo:.5f}, {hi:.5f}]), beating every prior method-lane-unique detector in this repository (<code>SAHG1</code> <code>0.09672</code> by <strong>+0.02701</strong>, <code>ASPC</code> <code>0.08553</code> by <strong>+0.02798</strong>, <code>CON</code> <code>0.06446</code> by <strong>+0.05926</strong>, <code>MTR1</code> <code>0.06441</code> by <strong>+0.05931</strong>, <code>H-UNIQUE-03</code> <code>0.05384</code> by <strong>+0.06988</strong>), passing prospective novelty across all <strong>{nov["competing_method_rasters_checked"]}</strong> competing method rasters (max overlap <code>{nov["method_lane_max_overlap_within_3px"]:.4f}</code> ≤ 0.70) and <strong>{nov["peer_blobs_checked"]}</strong> peer blobs (<code>{nov["peer_blobs_max_overlap_within_3px"]:.4f}</code> ≤ 0.70), and passing the exact-file C2ST nuisance audit (AUC <code>{c2st["observed_auc"]:.4f}</code> &lt; 0.55, Holm <em>p</em> = <code>{c2st["holm_p_value"]:.3f}</code>).
<strong>Why it remains DO NOT SUBMIT:</strong> removing latitude-band block/access confounds costs <code>-0.00627</code> HOLDOUT-DTI relative to the unresidualized <code>0.13000</code> baseline, the literal all-entry overlap rule still flags the synthetic spacing-5 calibration lattice (<code>1.0</code>), and weekly-slot promotion requires a separate selector step.</p>
<div class="actions">
<a class="button primary" href="downloads/{e(name)}" download="{e(name)}">↓ Download FUSE-HCW .tif (zeros outside, [0,1]-safe) — DO NOT SUBMIT</a>
<a class="button" href="downloads/{e(dl["nan_file"])}" download="{e(dl["nan_file"])}">↓ FUSE-HCW NaN-outside twin — DO NOT SUBMIT</a>
<a class="button" href="data/hcw_run_card.json">FUSE JSON run card</a>
<a class="button" href="downloads/{e(dl["checks_file"])}">FUSE validator JSON</a>
<a class="button" href="downloads/{e(preflight_path.name)}">FUSE preflight JSON</a>
</div>
<details open><summary>FUSE-HCW HOLDOUT-DTI, C2ST audit, short note, and SHA-256 (not leaderboard scores)</summary>
<p><strong>Primary evaluator <code>{e(h_main["evaluator_version"])}</code></strong> ({h_main["n_withheld_positive_pixels"]:,} withheld positives, 1.5 km collar, 10 km block bootstrap, 1,999 draws):
<code>FUSE-HCW</code> <strong>HOLDOUT-DTI {h_main["dti"]:.5f}</strong> (95% CI [{lo:.5f}, {hi:.5f}]) ·
<code>FUSE-RESID</code> <strong>{arms["fuse_resid"]["dti"]:.5f}</strong> ([{arms["fuse_resid"]["ci95"][0]:.5f}, {arms["fuse_resid"]["ci95"][1]:.5f}]) ·
<code>FUSE-RAW</code> <strong>{arms["fuse_raw"]["dti"]:.5f}</strong> ([{arms["fuse_raw"]["ci95"][0]:.5f}, {arms["fuse_raw"]["ci95"][1]:.5f}]) ·
<code>oof_multiphysics_hgb_d3</code> <strong>{arms["oof_multiphysics_hgb_d3_baseline"]["dti"]:.5f}</strong> ([{arms["oof_multiphysics_hgb_d3_baseline"]["ci95"][0]:.5f}, {arms["oof_multiphysics_hgb_d3_baseline"]["ci95"][1]:.5f}]).
<strong>Bridge evaluator <code>{e(h_bridge["evaluator_version"])}</code>:</strong> <strong>{h_bridge["dti"]:.5f}</strong> (95% CI [{blo:.5f}, {bhi:.5f}], Δ <strong>+{h_bridge["delta_vs_recorded_aspc"]:.5f}</strong> vs. ASPC).</p>
<p class="note" id="note-fuse">{e(dl["note"])}</p>
<div class="actions"><button class="button" data-copy="#note-fuse" data-feedback="#fb-fuse">Copy FUSE note</button><a class="button" href="downloads/{e(dl["note_file"])}" download>FUSE Note .txt</a></div>
<p id="fb-fuse" class="copyfeedback" aria-live="polite"></p>
<p class="hash">SHA-256 {e(digest)} · NaN-twin SHA-256 {e(dl["nan_sha256"])}</p></details></aside>"""


def concurrent_sahg1(root):
    """Validate and render the 2026-10-25 H24-SAHG1 packet and reconstructed OOF baseline."""
    fuse_html = concurrent_fuse(root)
    report_path = root / "evidence/sahg1_experiment_20261025.json"
    if not report_path.exists():
        return fuse_html
    report = json.loads(report_path.read_text())
    card = json.loads((root / "evidence/sahg1_run_card_20261025.json").read_text())
    dl = json.loads((root / "docs/data/sahg1_download.json").read_text())
    name = dl["file"]
    digest = dl["sha256"]
    if (
        card.get("raster_sha256") != digest
        or card.get("submission_name") != name
        or dl.get("note") != card.get("note")
    ):
        raise ValueError("SAHG1 checksum or identity disagree with run card")
    target = root / "docs/downloads" / name
    checks = json.loads((root / "docs/downloads" / dl["checks_file"]).read_text())
    if (
        sha256_file(target) != digest
        or checks["zero_outside"].get("sha256") != digest
        or checks["zero_outside"].get("format_valid") is not True
        or checks["zero_outside"].get("submission_authorized") is not False
    ):
        raise ValueError("SAHG1 checksum or exact-file validator disagrees")
    nan_target = root / "docs/downloads" / dl["nan_file"]
    if (
        sha256_file(nan_target) != dl["nan_sha256"]
        or checks["nan_outside"].get("sha256") != dl["nan_sha256"]
        or checks["nan_outside"].get("format_valid") is not True
        or checks["nan_outside"].get("submission_authorized") is not False
    ):
        raise ValueError("SAHG1 NaN-outside companion checksum or validator disagrees")
    if (
        report.get("ok_to_submit") is not False
        or dl.get("ok_to_submit") is not False
        or card.get("ok_to_submit") is not False
        or card.get("verdict") != "negative"
    ):
        raise ValueError("A negative research page cannot grant SAHG1 slot authorization")
    note_path = root / "docs/downloads" / dl["note_file"]
    if len(dl["note"]) > 140 or note_path.read_text().strip() != dl["note"]:
        raise ValueError("SAHG1 note is missing, changed, or exceeds 140 characters")
    preflight_path = target.with_suffix(".preflight.json")
    preflight = json.loads(preflight_path.read_text())
    if (
        preflight.get("artifact", {}).get("sha256") != digest
        or preflight.get("run_card", {}).get("artifact_sha256_matches") is not True
        or preflight.get("run_card", {}).get("artifact_name_matches") is not True
        or preflight.get("decision", {}).get("submission_status") != "DO_NOT_SUBMIT"
        or preflight.get("decision", {}).get("ready_to_submit") is not False
        or preflight.get("portal_range_diagnostic", {}).get("strict_whole_array_values_in_0_1")
        is not True
    ):
        raise ValueError("SAHG1 exact-file preflight is missing, stale, or does not fail closed")
    e = lambda s: escape(str(s), quote=True)  # noqa: E731
    h_main = card["holdout"]
    lo, hi = h_main["ci95"]["interval"]
    h_ablation = card["geomorphic_only_ablation"]
    alo, ahi = h_ablation["ci95"]["interval"]
    h_oof = card["reconstructed_oof_multiphysics_baseline"]
    olo, ohi = h_oof["ci95"]["interval"]
    h_bridge = card["bridge_protocol_holdout"]
    blo, bhi = h_bridge["ci95"]
    nov = card["correlation_overlap_vs_registry"]
    c2st = card["exact_file_nuisance_audit"]
    return (
        fuse_html
        + f"""<aside class="card concurrent" aria-label="H24-SAHG1 experiment and OOF benchmark">
<h3>Preserved H24-SAHG1 Strike-Hydro-Geomorph GeoTIFF — DOWNLOAD: YES · SUBMIT: NO (NOT OK TO SUBMIT)</h3>
<p>Independently computed from strike-projected 3DEP LiDAR antislope scarps (<code>G_sat</code>),
immobile-Thorium-controlled mobile K/U alteration (<code>R_alt</code>), and subsurface basement/strain steps
(<code>B_step</code>) inside a verified 9×9 discrete receptive-field support mask (<strong>no copied submission pixels</strong>).
Passes exact-grid/<code>[0,1]</code> format checks and prospective novelty against all <strong>{nov["competing_method_rasters_checked"]}</strong>
competing method lanes (max 3-px overlap <code>{nov["method_lane_max_overlap_within_3px"]:.4f}</code> ≤ 0.70) and
<strong>{nov["peer_blobs_checked"]}</strong> peer blobs (<code>{nov["peer_blobs_max_overlap_within_3px"]:.4f}</code> ≤ 0.70), and beats
both prior 2026-10-25 physical operators (<code>MTR1</code> and <code>ASPC</code>) plus its own geomorphic ablation on
<code>HOLDOUT-DTI</code> — but remains <strong>DO NOT SUBMIT</strong> because it does not beat the reconstructed
same-protocol out-of-fold multi-physics HGB baseline (<code>{h_oof["dti"]:.5f}</code>), flags the C2ST nuisance gate
(AUC <code>{c2st["observed_auc"]:.4f}</code>, Holm <em>p</em> = <code>{c2st["holm_p_value"]:.3f}</code>), and triggers the literal
spacing-5 calibration lattice overlap if calibration controls are not separated.</p>
<div class="actions">
<a class="button" href="downloads/{e(name)}" download="{e(name)}">↓ SAHG1 audit TIFF (zeros outside) — DO NOT SUBMIT</a>
<a class="button" href="downloads/{e(dl["nan_file"])}" download="{e(dl["nan_file"])}">↓ SAHG1 NaN-outside twin — DO NOT SUBMIT</a>
<a class="button" href="data/sahg1_run_card.json">SAHG1 JSON run card</a>
<a class="button" href="downloads/{e(dl["checks_file"])}">SAHG1 validator JSON</a>
<a class="button" href="downloads/{e(preflight_path.name)}">SAHG1 preflight JSON</a>
</div>
<details><summary>SAHG1 HOLDOUT-DTI comparison, short note, and SHA-256 (not leaderboard scores)</summary>
<p><strong>Primary evaluator <code>{e(h_main["evaluator_version"])}</code></strong> ({h_main["n_withheld_positive_pixels"]:,} withheld positives, 1.5 km collar, 10 km block bootstrap, 1,999 draws):
SAHG1 <strong>HOLDOUT-DTI {h_main["dti"]:.5f}</strong> (95% CI [{lo:.5f}, {hi:.5f}]) vs. geomorphic-only ablation <code>G_0</code>
<strong>{h_ablation["dti"]:.5f}</strong> ([{alo:.5f}, {ahi:.5f}], paired Δ <strong>+{card["paired_comparisons"]["sahg1_minus_geomorphic_core_g0"]["delta_dti"]:.5f}</strong>)
and recorded <code>MTR1</code> <strong>{card["paired_comparisons"]["sahg1_minus_recorded_mtr1"]["recorded_mtr1_dti"]:.5f}</strong>
(Δ <strong>+{card["paired_comparisons"]["sahg1_minus_recorded_mtr1"]["delta_dti"]:.5f}</strong>); reconstructed same-protocol OOF multi-physics baseline
<code>oof_multiphysics_hgb_d3</code> = <strong>{h_oof["dti"]:.5f}</strong> ([{olo:.5f}, {ohi:.5f}], paired Δ <strong>{card["paired_comparisons"]["sahg1_minus_reconstructed_oof_hgb_d3"]["delta_dti"]:.5f}</strong>).</p>
<p><strong>Bridge evaluator <code>{e(h_bridge["evaluator_version"])}</code></strong> ({h_bridge["n_withheld_positives"]:,} withheld positives, 3.0 km buffer, 20 km tile bootstrap, 1,000 draws):
SAHG1 <strong>HOLDOUT-DTI {h_bridge["dti"]:.5f}</strong> (95% CI [{blo:.5f}, {bhi:.5f}]) vs. recorded <code>ASPC</code>
<strong>{h_bridge["recorded_aspc_dti"]:.5f}</strong> (Δ <strong>+{h_bridge["delta_vs_recorded_aspc"]:.5f}</strong>) and <code>ASPC</code> control
<strong>{h_bridge["recorded_aspc_scarp_control_dti"]:.5f}</strong> (Δ <strong>+{h_bridge["delta_vs_recorded_aspc_control"]:.5f}</strong>).</p>
<p class="note">{e(dl["note"])}</p><p class="hash">SHA-256 {e(digest)} · NaN-twin SHA-256 {e(dl["nan_sha256"])}</p></details></aside>"""
    )


def concurrent_con(root):
    """Validate and retain PR #18's H24-CON clay-cap conductivity saddle packet."""
    card_path = root / "evidence/con_run_card_20261025.json"
    if not card_path.exists():
        return ""
    card = json.loads(card_path.read_text())
    name = card["submission_name"]
    nan_name = card["nan_submission_name"]
    digest = card["raster_sha256"]
    target = root / "docs/downloads" / name
    if (
        not target.exists()
        or sha256_file(target) != digest
        or card.get("ok_to_submit") is not False
        or card.get("verdict") != "negative"
        or len(card["note"]) > 140
    ):
        raise ValueError("Concurrent CON run-card or checksum disagrees")
    e = lambda s: escape(str(s), quote=True)  # noqa: E731
    h = card["holdout"]
    lo, hi = h["ci95"]["interval"]
    return f"""<aside class="card concurrent" aria-label="Preserved H24-CON experiment">
<h3>Parallel H24-CON Clay-Cap Saddle GeoTIFF retained — DOWNLOAD: YES · SUBMIT: NO</h3>
<p>PR #18 evaluated unsupervised surface-conductivity saddle × geodetic strain (<strong>HOLDOUT-DTI {h["dti"]:.5f}</strong>, 95% CI [{lo:.5f}, {hi:.5f}], <code>{e(h["evaluator_version"])}</code>). Format-valid, negative verdict retained.</p>
<div class="actions">
<a class="button" href="downloads/{e(name)}" download="{e(name)}">↓ CON audit TIFF (zeros outside) — DO NOT SUBMIT</a>
<a class="button" href="downloads/{e(nan_name)}" download="{e(nan_name)}">↓ CON NaN-outside twin — DO NOT SUBMIT</a>
<a class="button" href="data/con_run_card.json">CON JSON run card</a>
</div>
<details><summary>CON short note and SHA-256</summary>
<p class="note">{e(card["note"])}</p><p class="hash">SHA-256 {e(digest)}</p></details></aside>"""


def concurrent_unique(root):
    """Validate and retain PR #19's H-UNIQUE-03 fault-guided K modulation packet."""
    dl_path = root / "docs/data/unique_download.json"
    card_path = root / "docs/data/unique_run_card.json"
    if not (dl_path.exists() and card_path.exists()):
        return ""
    dl = json.loads(dl_path.read_text())
    card = json.loads(card_path.read_text())
    name = dl["file"]
    digest = dl["sha256"]
    target = root / "docs/downloads" / name
    if (
        not target.exists()
        or sha256_file(target) != digest
        or card.get("raster_sha256") != digest
        or dl.get("ok_to_submit") is not False
        or card.get("verdict") != "negative"
        or len(dl["note"]) > 140
    ):
        raise ValueError("Concurrent H-UNIQUE-03 run-card or checksum disagrees")
    e = lambda s: escape(str(s), quote=True)  # noqa: E731
    lo, hi = dl["holdout_ci95"]
    return f"""<aside class="card concurrent" aria-label="Preserved H-UNIQUE-03 experiment">
<h3>Parallel H-UNIQUE-03 Fault-Guided K GeoTIFF retained — DOWNLOAD: YES · SUBMIT: NO</h3>
<p>PR #19 evaluated visible-fault-guided potassium modulation (<strong>HOLDOUT-DTI {dl["holdout_dti"]:.5f}</strong>, 95% CI [{lo:.5f}, {hi:.5f}]). Format-valid, negative verdict retained.</p>
<div class="actions">
<a class="button" href="downloads/{e(name)}" download="{e(name)}">↓ H-UNIQUE-03 audit TIFF — DO NOT SUBMIT</a>
<a class="button" href="data/unique_run_card.json">H-UNIQUE-03 JSON run card</a>
</div>
<details><summary>H-UNIQUE-03 short note and SHA-256</summary>
<p class="note">{e(dl["note"])}</p><p class="hash">SHA-256 {e(digest)}</p></details></aside>"""


def concurrent_aspc(root):
    """Validate and render preserved 2026-10-25 sibling negative packets."""
    prefix_html = concurrent_sahg1(root) + concurrent_con(root) + concurrent_unique(root)
    report_path = root / "evidence/aspc_run_20261025.json"
    if not report_path.exists():
        return prefix_html
    report = json.loads(report_path.read_text())
    card = json.loads((root / "evidence/aspc_run_card_20261025.json").read_text())
    row = report.get("artifact")
    if not row:
        return (
            prefix_html + "<p>Concurrent ASPC research stopped without a downloadable artifact.</p>"
        )
    name = row["file"]
    digest = row["sha256"]
    if card.get("raster_sha256") != digest or card.get("submission_name") != name:
        raise ValueError("Concurrent ASPC run-card and artifact identity disagree")
    checks = research_receipt(root / "docs/downloads", row)
    if card.get("validator_output") != checks:
        raise ValueError("Concurrent ASPC validator output disagrees")
    if (
        report.get("submission_authorized") is not False
        or row.get("submission_authorized") is not False
        or card.get("submission_authorized") is not False
        or card.get("verdict") != "negative"
    ):
        raise ValueError("A negative research page cannot grant ASPC slot authorization")
    twin = report.get("template_convention_companion")
    if twin:
        research_receipt(root / "docs/downloads", twin)
        if card.get("template_convention_companion") != twin:
            raise ValueError("Concurrent ASPC companion identity disagrees")
    if len(row["note"]) > 140:
        raise ValueError("Concurrent lane note exceeds current limit")
    e = lambda s: escape(str(s), quote=True)  # noqa: E731
    result = report["holdout"]
    lo, hi = result["ci95"]
    return (
        prefix_html
        + f"""<aside class="card concurrent" aria-label="Preserved concurrent experiments">
<h3>Parallel ASPC, CON &amp; H-UNIQUE-03 results retained — all NOT OK TO SUBMIT</h3>
<p>PR #10 landed earlier on 2026-10-25. Its separate research artifact and evidence are preserved;
no current-best OOF certificate or slot authorization was obtained. Different component/collar and
bootstrap policies mean its point score is <strong>not a comparable current-best ranking</strong>.</p>
<div class="actions"><a class="button" href="downloads/{e(name)}" download="{e(name)}">↓ ASPC research TIFF — DO NOT SUBMIT</a>
<a class="button" href="data/aspc_run_card.json">ASPC evidence</a>
<a class="button" href="downloads/gems24-con-claycap-strain-saddle-20261025-ded121060878-zeros.tif" download="gems24-con-claycap-strain-saddle-20261025-ded121060878-zeros.tif">↓ CON audit TIFF — DO NOT SUBMIT</a>
<a class="button" href="data/con_run_card.json">CON run card</a>
<a class="button" href="downloads/24gems-doer-fault-guided-k-20261025T220208Z-dedb860f7e83-zeros.tif" download="24gems-doer-fault-guided-k-20261025T220208Z-dedb860f7e83-zeros.tif">↓ H-UNIQUE-03 TIFF — DO NOT SUBMIT</a>
<a class="button" href="data/unique_run_card.json">H-UNIQUE-03 run card</a></div>
<details><summary>Parallel ASPC, CON &amp; H-UNIQUE-03 details and short notes</summary>
<p><strong>ASPC:</strong> HOLDOUT-DTI {result["value"]:.5f}; 95% CI [{lo:.5f}, {hi:.5f}];
{result["n_withheld_positives"]:,} withheld positives; evaluator <code>{e(result["evaluator_version"])}</code>.
Not a leaderboard score.</p>
<p><strong>H24-CON (PR #18):</strong> Conductive clay-cap Laplacian saddle × transtensional strain; HOLDOUT-DTI <code>0.06446</code> (95% CI [0.05841, 0.07030]) on <code>gems-segment-pooled-v1</code>; prospective method-lane max 3-px overlap <code>0.3108</code> ≤ 0.70 (PASS), literal spacing-5 lattice overlap <code>1.0</code> (FAIL).</p>
<p><strong>H-UNIQUE-03 (PR #19):</strong> Visible-fault-guided K-modulation; HOLDOUT-DTI <code>0.05384</code> (95% CI [0.03894, 0.06866]) on <code>gems-segment-pooled-v1</code>; flagged for unit-conversion irregularity (<code>DIST_DECAY_PX=300.0</code> = 30 km instead of 300 m) and omitted proximity channel in leakage canary.</p>
<p class="note">{e(row["note"])}</p><p class="hash">ASPC SHA-256 {e(digest)}</p></details></aside>"""
    )


def concurrent_oj1(root):
    """Reopen the latest fixed negative packet before showing any download."""
    if not (root / "evidence/oj1_run_card_20261025.json").exists():
        return ""
    from run_oj1_lane import verify_recorded

    card = verify_recorded(root)
    e = lambda value: escape(str(value), quote=True)  # noqa: E731
    if not card["submission_name"]:
        return f'<aside class="card"><h2>OJ1 stopped without a TIFF</h2><p>{e(card["stopped_reason"])}</p></aside>'
    name = card["submission_name"]
    published = json.loads((root / "docs/data/oj1_run_card.json").read_text())
    if published != card:
        raise ValueError("Published OJ1 run card disagrees with experiment")
    preflight_name = name[:-4] + ".preflight.json"
    receipt = json.loads((root / "docs/downloads" / preflight_name).read_text())
    if (
        receipt.get("artifact", {}).get("sha256") != card["raster_sha256"]
        or receipt.get("decision", {}).get("ready_to_submit") is not False
        or receipt.get("decision", {}).get("submission_status") != "DO_NOT_SUBMIT"
        or receipt.get("portal_range_diagnostic", {}).get("strict_whole_array_values_in_0_1")
        is not True
    ):
        raise ValueError("OJ1 preflight changed or does not fail closed")
    result = card["holdout"]
    lo, hi = result["ci95"]["interval"]
    comparison = card["recorded_baseline_comparison"]["holdout"]
    blo, bhi = comparison["ci95"]["interval"]
    before = card["correlation_overlap_vs_registry"]["surface"]
    after = card["correlation_overlap_vs_registry"]["final_dots"]
    return f'''<section class="card" aria-label="Latest OJ1 research GeoTIFF">
<div class="eyebrow">Latest fixed experiment · OJ1 · negative result</div>
<h2>New GeoTIFF: download for research, NOT OK TO SUBMIT</h2>
<p><strong>DOWNLOAD: YES · SUBMIT: NO. DO NOT SUBMIT.</strong>
Computed independently from LiDAR scarp orientations, coherence, curvature and step response;
no old submission pixels used. Different bytes do not establish scientific uniqueness:
the literal final-dot registry gate failed. The lane stopped, with no retuning or weekly slot.</p>
<div class="actions"><a class="button primary" href="downloads/{e(name)}" download="{e(name)}">↓ Download OJ1 research .tif — DO NOT SUBMIT</a>
<a class="button" href="data/oj1_run_card.json">Full JSON run card</a>
<a class="button" href="downloads/{e(preflight_name)}">Automated preflight</a></div>
<p class="fileline">{e(name)}</p><p class="hash">SHA-256 {e(card["raster_sha256"])}</p>
<p><strong>HOLDOUT-DTI {result["dti"]:.5f}</strong>, 95% CI [{lo:.5f}, {hi:.5f}];
evaluator <code>{e(result["evaluator_version"])}</code>; {result["n_withheld_positive_pixels"]:,} withheld positive pixels.
Recorded same-protocol OOF baseline: <strong>HOLDOUT-DTI {comparison["dti"]:.5f}</strong>,
95% CI [{blo:.5f}, {bhi:.5f}], same evaluator and positive count; not replayed in this session.
OJ1 did not beat it. These are <strong>not leaderboard scores</strong>; OJ1 is not yet scored by the organizer.</p>
<p>Format: single float32 band, exact template CRS/shape/transform; finite [0,1] everywhere,
zeros outside. No local check guarantees portal acceptance.
Source/transform canaries passed; this is not proof of geological specificity.
Registry: {after["registry_unique_rasters"]} pinned rasters (including controls), pre-placement max absolute rank statistic
{before["max_abs_rank_correlation"]:.4f}; final {after["max_abs_rank_correlation"]:.4f};
maximum directional overlap within 3 px <strong>{100 * after["max_dot_overlap"]:.2f}%</strong> (limit 70%).
Spacing-5 control retained; no exemption. No claim of global uniqueness or a vent discovery.</p>
<div class="note" id="note-oj1">{e(card["note"])}</div>
<button class="button" data-copy="#note-oj1" data-feedback="#fb-oj1">Copy short research note</button>
<p id="fb-oj1" aria-live="polite"></p><p class="micro">{len(card["note"])} characters; maximum 140.
Independent selector/quota verification is not implemented, so preflight cannot authorize any slot from card flags alone.</p></section>'''


def trsg1_packet(root: Path) -> tuple[str, str, str]:
    """Validate and render the 2026-10-26 H24-TRSG1 Two-Regime Stitched-OOF packet + 9-site portfolio executive."""
    exp_path = root / "evidence/trsg1_experiment_20261026.json"
    card_path = root / "evidence/trsg1_run_card_20261026.json"
    dl_path = root / "docs/data/trsg1_download.json"
    if not (exp_path.exists() and card_path.exists() and dl_path.exists()):
        return "", "", ""

    experiment = json.loads(exp_path.read_text())
    card = json.loads(card_path.read_text())
    dl = json.loads(dl_path.read_text())
    name = dl["file"]
    digest = dl["sha256"]
    if (
        card.get("raster_sha256") != digest
        or card.get("submission_name") != name
        or dl.get("note") != card.get("note")
    ):
        raise ValueError("TRSG1 checksum or identity disagree with run card")
    if (
        experiment.get("ok_to_submit") is not False
        or dl.get("ok_to_submit") is not False
        or card.get("ok_to_submit") is not False
        or card.get("verdict") != "negative"
    ):
        raise ValueError("A fail-closed negative page cannot grant TRSG1 slot authorization")

    template = root / "data/bridge/sample_submission.tif"
    checks = json.loads((root / "docs/downloads" / dl["checks_file"]).read_text())
    for key in ("zero_outside", "nan_outside"):
        row = checks[key]
        target_variant = root / "docs/downloads" / row["file"]
        fresh = check_variants(target_variant, template)
        if (
            not fresh["format_valid"]
            or not row["format_valid"]
            or fresh.get("submission_authorized") is not False
            or any(fresh.get(field) != value for field, value in row.items())
        ):
            raise ValueError(f"TRSG1 download variant invalid or stale: {key}")

    zip_target = root / "docs/downloads" / dl["zip_file"]
    if (
        sha256_file(zip_target) != dl["zip_sha256"]
        or card.get("zip_sha256") != dl["zip_sha256"]
        or card.get("zip_artifact") != dl["zip_file"]
    ):
        raise ValueError("TRSG1 ZIP checksum disagrees with receipt")
    with zipfile.ZipFile(zip_target) as zf:
        if zf.namelist() != [name]:
            raise ValueError("TRSG1 ZIP entry list invalid")
        if hashlib.sha256(zf.read(name)).hexdigest() != digest:
            raise ValueError("TRSG1 ZIP inner TIFF hash disagrees")

    note_path = root / "docs/downloads" / dl["note_file"]
    if len(dl["note"]) > 140 or note_path.read_text().strip() != dl["note"]:
        raise ValueError("TRSG1 note is missing, changed, or exceeds 140 characters")

    target = root / "docs/downloads" / name
    sel_path = root / "evidence/trsg1_selector_20261026.json"
    if sel_path.exists():
        saved_sel = json.loads(sel_path.read_text())
        fresh_sel = selector.verify_selector(target, template, card)
        if (
            saved_sel.get("gates") != fresh_sel.get("gates")
            or saved_sel.get("decision") != fresh_sel.get("decision")
            or saved_sel.get("decision") != "DO_NOT_SUBMIT"
            or saved_sel.get("human_inspection_used") is not False
        ):
            raise ValueError("TRSG1 selector v2 receipt disagrees with fresh gems.selector check")
    preflight_path = target.with_suffix(".preflight.json")
    preflight = json.loads(preflight_path.read_text())
    if (
        preflight.get("artifact", {}).get("sha256") != digest
        or preflight.get("run_card", {}).get("artifact_sha256_matches") is not True
        or preflight.get("run_card", {}).get("artifact_name_matches") is not True
        or preflight.get("decision", {}).get("submission_status") != "DO_NOT_SUBMIT"
        or preflight.get("decision", {}).get("ready_to_submit") is not False
        or preflight.get("portal_range_diagnostic", {}).get("strict_whole_array_values_in_0_1")
        is not True
    ):
        raise ValueError("TRSG1 exact-file preflight is missing, stale, or does not fail closed")

    e = lambda s: escape(str(s), quote=True)  # noqa: E731
    h_main = card["holdout"]
    lo, hi = h_main["ci95"]["interval"]
    h_a1 = experiment["arm1_raw44"]
    a1_lo, a1_hi = h_a1["ci95"]["interval"]
    h_a2 = experiment["arm2_selres_terraincal"]
    a2_lo, a2_hi = h_a2["ci95"]["interval"]
    h_oof = card["reconstructed_oof_multiphysics_baseline"]
    oof_lo, oof_hi = h_oof["ci95"]["interval"]
    p_oof = card["paired_comparisons"]["arm3_minus_reconstructed_oof_hgb_d3"]
    d_lo, d_hi = p_oof["ci95"]
    h_br = card["bridge_protocol_holdout"]
    br_lo, br_hi = h_br["ci95"]
    canary = card["leakage_canary"]
    nov = card["correlation_overlap_vs_registry"]
    cal_ctrl_id = experiment["final_novelty_methods"]["calibration_control_rows"][0]["registry_id"]
    c2st = card["exact_file_nuisance_audit"]
    halo = card["deployment_halo_and_regime_diagnostics"]

    status_box = (
        '<div class="status stopped" role="status">'
        "<strong>LATEST 2026-10-26 ARTIFACT (H24-TRSG1) — DOWNLOAD: YES · SUBMIT: NO. NOT OK TO SUBMIT (DO_NOT_SUBMIT).</strong> "
        "Automated gates ran end-to-end with zero human-inspector fallback: <strong>7 / 7 technical &amp; scientific gates PASS</strong> "
        f"(exact template grid &amp; strict whole-array [0,1] PASS · 44/44 two-polarity canaries PASS [worst {e(canary['worst_feature'])} AUC {canary['worst_pooled_auc']:.4f}] · "
        f"comparable OOF HOLDOUT-DTI win PASS [{h_main['dti']:.5f} vs {h_oof['dti']:.5f}, paired Δ {p_oof['delta_dti']:+.5f}, 95% CI [{d_lo:+.5f}, {d_hi:+.5f}]] · "
        f"competing-method + peer uniqueness across 137 rasters PASS [max 3-px overlap {nov['method_lane_max_overlap_within_3px']:.4f} ≤ 0.70, max |ρ| {nov['pre_placement_max_abs_rank_correlation']:.4f} ≤ 0.90] · "
        f"exact-file C2ST nuisance audit PASS [AUC {c2st['observed_auc']:.4f} &lt; 0.55, Holm p = {c2st['holm_p_value']:.3f}] · "
        f"Stitched-OOF Halo Sanity PASS [2&lt;d_cat≤5 px = {100 * halo['frac_2_to_5px_halo']:.1f}% vs GVC1 45.8%; d_cat&gt;30 px = {100 * halo['frac_gt_30px_deep_concealed']:.1f}% vs GVC1 4.1%]). "
        f"Fail-closed governance stays <code>DO_NOT_SUBMIT</code> because the retained spacing-5 calibration lattice ({e(cal_ctrl_id)}) triggers literal {nov['literal_all_entries_max_overlap_within_3px']:.4f} overlap and weekly-slot promotion requires an external selector (Rule 6).</div>"
    )

    gate_rows = [
        (
            "1. Exact-grid GeoTIFF & strict [0,1]",
            "PASS",
            f"Single-band float32, EPSG:32611, shape 3730×3292, 37,722 binary {{0,1}} dots (min d_cat = {halo['min_dist_to_catalogue_px']:.2f} px > 2.0 px); zero NaN/Inf across all 12,279,160 cells in -zeros.tif; ZIP & -nan.tif verified.",
        ),
        (
            "2. Two-polarity leakage canaries (44 ch)",
            "PASS",
            f"44/44 channels checked on SegmentHoldout (worst feature {canary['worst_feature']} pooled AUC {canary['worst_pooled_auc']:.4f}, within [0.10, 0.90]; OOF surface AUC {canary['oof_calibrated_prob_pooled_auc']:.4f}).",
        ),
        (
            "3. Comparable OOF HOLDOUT-DTI win",
            "PASS",
            f"Primary Arm 3 HOLDOUT-DTI {h_main['dti']:.5f} [{lo:.5f}, {hi:.5f}] beats oof_multiphysics_hgb_d3 ({h_oof['dti']:.5f}) by {p_oof['delta_dti']:+.5f} with strictly positive 95% paired CI [{d_lo:+.5f}, {d_hi:+.5f}] (Arm 2: {h_a2['dti']:.5f}; 3 km bridge: {h_br['dti']:.5f} [{br_lo:.5f}, {br_hi:.5f}]).",
        ),
        (
            "4. Competing-method & peer novelty (137 rasters)",
            "PASS",
            f"Zero copied pixels; max |ρ| = {nov['pre_placement_max_abs_rank_correlation']:.4f} (pre-placement) / {nov['surface_max_abs_rank_correlation']:.4f} (final) ≤ 0.90; max 3-px dot overlap = {nov['method_lane_max_overlap_within_3px']:.4f} ≤ 0.70 across 54 competing methods & 83 peer blobs (H33-2-B2 overlap 0.5140; GVC1 0.3586).",
        ),
        (
            "5. Exact-file C2ST nuisance audit",
            "PASS",
            f"Spatial-block C2ST AUC {c2st['observed_auc']:.4f} ≤ null p95 {c2st['null_p95']:.4f} (Holm p = {c2st['holm_p_value']:.3f}, labels control {c2st['labels_first']['observed_auc']:.4f}).",
        ),
        (
            "6. Stitched-OOF Halo & LiDAR-Gap Sanity",
            "PASS",
            f"100% Dual-Partition Stitched-OOF deployment cuts 2<d_cat≤5 px halo from 45.8% (GVC1 0.0859 collapse) to {100 * halo['frac_2_to_5px_halo']:.1f}%, boosts deep concealed d_cat>30 px from 4.1% to {100 * halo['frac_gt_30px_deep_concealed']:.1f}%, and allocates {100 * halo['frac_in_lidar_gap']:.1f}% in the 3DEP LiDAR gap (26.0% concealed basin).",
        ),
        (
            "7. Literal calibration control & separate selector",
            "DO_NOT_SUBMIT",
            f"Retained spacing-5 calibration lattice ({cal_ctrl_id}) flags literal {nov['literal_all_entries_max_overlap_within_3px']:.4f} 3-px overlap; external weekly-slot selector required before any DrivenData upload (0 slots spent).",
        ),
    ]
    gate_table = (
        '<div class="tablewrap" tabindex="0" role="region" aria-label="H24-TRSG1 automated gates"><table><thead><tr><th>H24-TRSG1 automated gate</th><th>Decision</th><th>Measured evidence (not leaderboard scores)</th></tr></thead><tbody>'
        + "".join(
            f"<tr><td>{e(a)}</td><td><strong>{e(b)}</strong></td><td>{e(c)}</td></tr>"
            for a, b, c in gate_rows
        )
        + "</tbody></table></div>"
    )

    note_block = (
        f'<div class="note" id="note-trsg1">{e(dl["note"])}</div>'
        '<div class="actions">'
        '<button class="button" data-copy="#note-trsg1" data-feedback="#copy-feedback-trsg1">Copy TRSG1 short note</button>'
        f'<a class="button" href="downloads/{e(dl["note_file"])}" download>TRSG1 note .txt</a>'
        "</div>"
        '<p id="copy-feedback-trsg1" class="copyfeedback" aria-live="polite"></p>'
        f'<p class="micro">{len(dl["note"])} characters · maximum 140</p>'
    )

    hero_html = f"""<section id="trsg1-overview" class="hero" aria-label="Latest 2026-10-26 H24-TRSG1 unique GeoTIFF and automated gate">
<div>
<div class="eyebrow">2026-10-26 Orthogonal Seismic-Geothermal Lane · H24-TRSG1 · 7/7 Technical Gates PASS</div>
<h2>Seismic-Geothermal Step-Over Stitched-OOF.<br>Fail-closed selector v2: DO NOT SUBMIT.</h2>
<p class="lead"><strong><code>{e(name)}</code></strong> was generated independently from 44 physical channels (restored <code>ieq_n100a15</code>/<code>deq_n100a15</code> microseismic anisotropy, hyperbolic step-over saddle twist, scale-localized INGENIOUS sinter/2 m-probe/geothermometry DoGs, Quaternary vent corridors, selective nuisance residualization, terrain-relief LiDAR-gap calibration, and <strong>100% Dual-Partition Stitched-OOF</strong> Two-Regime allocation). <strong>Zero prior submission pixels were read or copied.</strong> It is <strong>not yet scored</strong> by the organizer, achieves <strong><code>HOLDOUT-DTI {h_main["dti"]:.5f}</code></strong> (strictly positive paired 95% CI <code>[{d_lo:+.5f}, {d_hi:+.5f}]</code> over <code>oof_multiphysics_hgb_d3</code>), passes 137-raster novelty (<code>{nov["method_lane_max_overlap_within_3px"]:.4f} ≤ 0.70</code>; <code>≤0.6622</code> vs <code>DPRF1</code>/<code>TNR1</code>/<code>CRP1</code>/<code>CUP1</code>) and C2ST (<code>{c2st["observed_auc"]:.4f}</code>), and resolves <code>GVC1</code>'s in-sample halo collapse (<code>32.0%</code> deep concealed discovery vs <code>4.1%</code>), while staying <strong>NOT OK TO SUBMIT</strong> under <code>gems-selector-v2-literal-quota-fail-closed</code>.</p>
{status_box}
<div class="actions">
<a class="button primary" href="downloads/{e(name)}" download="{e(name)}">↓ Download H24-TRSG1 GeoTIFF (zeros outside, [0,1]) — DO NOT SUBMIT</a>
<a class="button" href="downloads/{e(dl["zip_file"])}" download="{e(dl["zip_file"])}">↓ Download Single-TIFF .zip — DO NOT SUBMIT</a>
<a class="button" href="downloads/{e(dl["nan_file"])}" download="{e(dl["nan_file"])}">↓ NaN-outside twin — DO NOT SUBMIT</a>
<a class="button" href="downloads/{e(preflight_path.name)}">Automated preflight — DO_NOT_SUBMIT</a>
<a class="button" href="data/trsg1_selector.json" download>Selector v2 JSON — DO_NOT_SUBMIT</a>
<a class="button" href="data/trsg1_run_card_20261026.json" download>TRSG1 JSON run card</a>
<a class="button" href="executive-summary.html">9-site executive &amp; submission guide →</a>
</div>
<p class="fileline">{e(name)}</p>
<p class="hash">SHA-256 {e(digest)} · ZIP SHA-256 {e(dl["zip_sha256"])}</p>
{note_block}
</div>
<aside class="card visual">
<div class="cardtop"><h2 class="metric-label">H24-TRSG1 HOLDOUT-DTI</h2><span class="badge amber">Not leaderboard scores</span></div>
<div class="result-number">{h_main["dti"]:.5f}</div>
<p class="micro">HOLDOUT-DTI · <code>{e(h_main["evaluator_version"])}</code> · {h_main["n_withheld_positive_pixels"]:,} withheld positives · 95% CI [{lo:.5f}, {hi:.5f}] · Arm 2 Global: <strong>{h_a2["dti"]:.5f}</strong> · 3.0 km bridge: <strong>{h_br["dti"]:.5f}</strong></p>
<img class="raster-preview" src="assets/trsg1-preview.png" alt="Downsampled preview of H24-TRSG1 Stitched-OOF Two-Regime fault dots (37,722 positive cells)">
<p class="micro">37,722 binary dots · 26.0% concealed basin · 32.0% deep off-catalogue (&gt;3 km) · NE_LidarGapHeavy {h_main["folds"][1]["dti"]:.5f}</p>
</aside>
</section>
<section aria-label="H24-TRSG1 automated gate breakdown"><h2>H24-TRSG1 automated validation gates (zero human-inspector fallback)</h2>{gate_table}</section>"""

    portfolio_table = """<div class="tablewrap" tabindex="0" role="region" aria-label="TRSG1 nine-site scoreboard"><table><thead><tr><th>Rank</th><th>Priority Site</th><th>Pinned <code>main</code></th><th>Best Submission on Site (<code>OWNER-REPORTED</code>)</th><th>Dots</th><th>Best Score</th><th>2026-10-25/26 Independent Detector Note</th></tr></thead><tbody>
<tr><td><strong>1</strong></td><td><a href="https://github.com/buffedlizard55-lab/GEMSDOE32"><strong>GEMSDOE32</strong></a></td><td><code>7a97c5a889</code></td><td><code>h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros</code></td><td>37,654</td><td><strong>0.2778</strong></td><td><strong>#1 overall across the 9 priority sites</strong> (<code>D2.8</code> + 200 m zero-credit apron prune)</td></tr>
<tr><td>2</td><td><a href="https://github.com/buffedlizard55-lab/GEMSDOE36">GEMSDOE36</a></td><td><code>d519364018</code></td><td><code>h35-1-pinn-b2-p1200-20261004T193800Z-f7a8dae1</code></td><td>38,854</td><td><strong>0.2750</strong></td><td><code>gied</code> / <code>sbrf</code> (unscored)</td></tr>
<tr><td>3</td><td><a href="https://github.com/buffedlizard55-lab/GEMSDOE28">GEMSDOE28</a></td><td><code>10c26af3dc</code></td><td><code>h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan</code></td><td>39,964</td><td><strong>0.2710</strong></td><td><code>s18-mxtp</code>: <code>0.0217</code> (<code>OWNER-REPORTED</code>)</td></tr>
<tr><td>4</td><td><a href="https://github.com/buffedlizard55-lab/GEMSDOE31">GEMSDOE31</a></td><td><code>3c1be4993a</code></td><td><code>h27-4-20261003T081907Z-7f95c1c9</code></td><td>40,199</td><td><strong>0.2708</strong></td><td><code>scgp-submod-37654</code> (unscored)</td></tr>
<tr><td>5</td><td><a href="https://github.com/buffedlizard55-lab/GEMSDOE33">GEMSDOE33</a></td><td><code>b542e5ce41</code></td><td><code>h38-3-b2-matched44090-20261004T093000Z-6930b98e</code></td><td>44,090</td><td><strong>0.2632</strong></td><td><code>tcf</code> / <code>gied</code> (unscored)</td></tr>
<tr><td>6 (tie)</td><td><a href="https://github.com/buffedlizard55-lab/GEMSDOE25">GEMSDOE25</a></td><td><code>0a45b3ca64</code></td><td><code>dotted-h19-5-d2-8-20261002-e56ea318af89-nan</code></td><td>44,090</td><td><strong>0.2600</strong></td><td><code>h66-mgd-flank</code>: <code>0.0742</code> (<code>OWNER-REPORTED</code>)</td></tr>
<tr><td>6 (tie)</td><td><a href="https://github.com/buffedlizard55-lab/GEMSDOE30">GEMSDOE30</a></td><td><code>78ae70817a</code></td><td><code>d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca</code></td><td>44,090</td><td><strong>0.2600</strong></td><td><code>MSDB1-edge44090</code>: <code>0.1462</code> (<code>18.2%</code> wasted at <code>d_cat≤2 px</code>)</td></tr>
<tr><td>8</td><td><a href="https://github.com/buffedlizard55-lab/GEMSDOE24"><strong>GEMSDOE24</strong></a></td><td><code>fc2bc6f350</code></td><td><code>gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan</code></td><td>60,069</td><td><strong>0.2477</strong></td><td><code>GVC1</code>: <code>0.0859</code> (in-sample halo); <strong><code>H24-DPRF1</code> (<code>0.16379</code>) &amp; <code>H24-TRSG1</code> (<code>0.14644</code>, C2ST <code>0.4727</code>)</strong></td></tr>
<tr><td>9</td><td><a href="https://github.com/buffedlizard55-lab/GEMSDOE27">GEMSDOE27</a></td><td><code>927322eadb</code></td><td><code>topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan</code></td><td>59,075</td><td><strong>0.2449</strong></td><td><strong><code>H29-HPVC</code>: <code>0.2190</code></strong> (stitched OOF + CELF cover)</td></tr>
</tbody></table></div>"""

    exec_html = f"""<section id="trsg1-exec" class="card concurrent" aria-label="Latest 2026-10-26 H24-TRSG1 submission status &amp; 9-site executive review">
<h2>2026-10-26 Orthogonal Seismic-Geothermal Candidate (<code>H24-TRSG1</code>) — DOWNLOAD: YES · SUBMIT: NO (7/7 Technical Gates PASS)</h2>
{status_box}
<div class="actions">
<a class="button primary" href="downloads/{e(name)}" download="{e(name)}">↓ Download H24-TRSG1 GeoTIFF (zeros outside) — DO NOT SUBMIT</a>
<a class="button" href="downloads/{e(dl["zip_file"])}" download="{e(dl["zip_file"])}">↓ Download Single-TIFF .zip — DO NOT SUBMIT</a>
<a class="button" href="downloads/{e(dl["nan_file"])}" download="{e(dl["nan_file"])}">↓ TRSG1 NaN-outside twin — DO NOT SUBMIT</a>
<a class="button" href="downloads/{e(preflight_path.name)}">TRSG1 Automated preflight JSON</a>
<a class="button" href="data/trsg1_selector.json" download>TRSG1 Selector v2 JSON</a>
<a class="button" href="downloads/{e(dl["checks_file"])}">TRSG1 Exact-file validator JSON</a>
<a class="button" href="data/trsg1_run_card_20261026.json" download>TRSG1 JSON run card</a>
</div>
<p class="fileline">{e(name)} · SHA-256 <code>{e(digest)}</code></p>
{note_block}
{gate_table}
<h3>Verified 9-Priority-Site Scoreboard (<code>OWNER-REPORTED</code>, unverified without organizer receipts)</h3>
{portfolio_table}
<p class="micro">Broader sibling benchmarks disclosed in repository ledgers (<code>OWNER-REPORTED</code>): <code>GEMSDOE84</code> <code>0.3195</code>, <code>GEMSDOE87</code> <code>0.3037</code>, <code>GEMSDOE83</code> <code>0.2966</code>; top independent non-<code>H19-5</code> detectors on 2026-10-25: <code>GEMSDOE70 P8-OOF38k</code> <strong><code>0.2478</code></strong>, <code>GEMSDOE76 ptcf</code> <strong><code>0.2343</code></strong>, <code>GEMSDOE63 cvarlw</code> <strong><code>0.2303</code></strong>, and <code>GEMSDOE27 H29</code> <strong><code>0.2190</code></strong>. Competition top score claims (<code>0.3195</code> snapshot vs <code>0.4413</code> prompt text) remain unverified without live DrivenData scraping (prohibited by Terms of Use). <a href="https://github.com/buffedlizard55-lab/GEMSDOE24/blob/main/knowledge/20_TRSG1_findings_and_portfolio_executive_2026-10-26.md">Full PhD monograph &amp; 9-site audit →</a></p>
</section>"""

    fold_rows = "".join(
        f"<tr><td><code>{e(f3['fold'])}</code></td><td><strong>{f3['dti']:.5f}</strong></td><td>{f2['dti']:.5f}</td><td>{f1['dti']:.5f}</td><td>{fo['dti']:.5f}</td><td>{f3['n_emitted']:,}</td></tr>"
        for f3, f2, f1, fo in zip(
            h_main["folds"],
            h_a2["folds"],
            h_a1["folds"],
            h_oof["folds"],
            strict=True,
        )
    )
    research_html = f"""<section id="trsg1-research"><h2>2026-10-26 Orthogonal Execution: H24-TRSG1 Two-Regime Seismic-Geothermal Stitched-OOF Detector</h2>
<div class="grid2"><article class="card"><h3>3-Arm HOLDOUT-DTI &amp; Per-Fold Attribution (not leaderboard scores)</h3>
<div class="tablewrap" tabindex="0" role="region" aria-label="H24-TRSG1 three-arm holdout comparison"><table><thead><tr><th>Fold / Summary</th><th>Arm 3: TRSG1 (2-Regime, Primary)</th><th>Arm 2: SelRes + TerrainCal</th><th>Arm 1: Raw 44-ch</th><th>OOF HGB Baseline</th><th>TRSG1 Dots</th></tr></thead><tbody>
{fold_rows}
<tr><td><strong>Pooled <code>gems-segment-pooled-v1</code></strong></td><td><strong>{h_main["dti"]:.5f}</strong> [{lo:.5f}, {hi:.5f}]</td><td><strong>{h_a2["dti"]:.5f}</strong> [{a2_lo:.5f}, {a2_hi:.5f}]</td><td>{h_a1["dti"]:.5f} [{a1_lo:.5f}, {a1_hi:.5f}]</td><td>{h_oof["dti"]:.5f} [{oof_lo:.5f}, {oof_hi:.5f}]</td><td>{dl["pixel_count"]:,}</td></tr>
</tbody></table></div>
<p class="micro">Selective nuisance residualization + terrain-relief LiDAR-gap calibration (<code>Arm 2</code>) lifts <code>NE_LidarGapHeavy</code> from <code>0.17781</code> to <strong><code>0.18908</code></strong> without hurting <code>SW</code> (<code>0.10035</code> vs RSHG1 <code>0.07993</code>). Two-Regime allocation (<code>Arm 3</code>) achieves paired gain <strong><code>{p_oof["delta_dti"]:+.5f}</code></strong> (<code>[{d_lo:+.5f}, {d_hi:+.5f}]</code>) over <code>oof_multiphysics_hgb_d3</code> and <strong><code>{h_br["dti"]:.5f}</code></strong> on the 3.0 km bridge.</p></article>
<article class="card"><h3>Post-GVC1 Halo Cure, Uniqueness &amp; PhD Synthesis</h3>
<img class="raster-preview" src="assets/trsg1-preview.png" alt="Downsampled preview of H24-TRSG1 Stitched-OOF Two-Regime fault dots (37,722 positive cells)">
<p class="micro">Why <code>GEMSDOE32 H33-2-B2</code> scored <code>0.2778</code> while <code>GVC1</code> scored <code>0.0859</code>: <code>H33-2-B2</code> applies Dinkelbach <code>{{0,1}}</code> vertex emission + 2.8 px geodesic spacing + exact <code>d_cat &gt; 2.0 px</code> pruning with <strong>35.8%</strong> deep off-catalogue dots (<code>d_cat &gt; 30 px</code>) and only <strong>15.0%</strong> in <code>2&lt;d_cat≤5 px</code>, whereas <code>GVC1</code> fitted in-sample with <code>neg ≥ 9 px</code> + global thermal EDT, dumping <strong>45.8%</strong> in <code>2&lt;d_cat≤5 px</code> and <strong>4.1%</strong> at <code>d_cat &gt; 30 px</code>. <code>H24-TRSG1</code>'s close-flank negatives + compact DoGs + 100% Stitched-OOF restores <strong>18.4%</strong> halo and <strong>32.0%</strong> deep concealed discovery while passing 137-raster novelty (<code>{nov["method_lane_max_overlap_within_3px"]:.4f} ≤ 0.70</code>) and C2ST (<code>{c2st["observed_auc"]:.4f}</code>). <a href="https://github.com/buffedlizard55-lab/GEMSDOE24/blob/main/knowledge/19_preregistered_TRSG1_2026-10-26.md">TRSG1 preregistration →</a> · <a href="https://github.com/buffedlizard55-lab/GEMSDOE24/blob/main/knowledge/20_TRSG1_findings_and_portfolio_executive_2026-10-26.md">Full PhD synthesis &amp; roadmap to 0.4413 →</a></p></article></div></section>"""
    return hero_html, exec_html, research_html


def crp1_packet(root):
    """Validate and render the 2026-10-26 H24-CRP1 packet (hero, executive, research).

    Decision text is generated from the independent selector receipt only;
    this renderer never upgrades a decision.  Returns empty strings when the
    CRP1 evidence is absent (site builds before the experiment remain valid).
    """
    card_path = root / "evidence/crp1_run_card_20261026.json"
    dl_path = root / "docs/data/crp1_download.json"
    sel_path = root / "evidence/crp1_selector_20261026.json"
    if not (card_path.exists() and dl_path.exists() and sel_path.exists()):
        return "", "", ""
    card = json.loads(card_path.read_text())
    dl = json.loads(dl_path.read_text())
    receipt = json.loads(sel_path.read_text())
    name = dl["file"]
    digest = dl["sha256"]
    published = json.loads((root / "docs/data/crp1_run_card.json").read_text())
    target = root / "docs/downloads" / name
    checks = json.loads((root / "docs/downloads" / f"checks-{name[:-4]}.json").read_text())
    if (
        published != card
        or card.get("raster_sha256") != digest
        or card.get("submission_name") != name
        or dl.get("note") != card.get("note")
        or sha256_file(target) != digest
        or checks["zero_outside"].get("sha256") != digest
        or checks["zero_outside"].get("format_valid") is not True
        or receipt.get("artifact_sha256") != digest
        or receipt.get("artifact") != name
        or receipt.get("human_inspection_used") is not False
    ):
        raise ValueError("CRP1 packet identity, checksum or selector receipt disagrees")
    from gems.selector import verify_selector

    current_screen = verify_selector(target, root / "data/bridge/sample_submission.tif", card)
    if (
        receipt.get("ok_to_submit") is not False
        or current_screen["ok_to_submit"] is not False
        or receipt.get("decision") != current_screen["decision"]
    ):
        raise ValueError("Frozen negative CRP1 cannot be promoted by edited card/selector flags")
    (root / "docs/data/crp1_current_policy_screen.json").write_text(
        json.dumps(current_screen, indent=2, allow_nan=False) + "\n"
    )
    ok_submit = False
    if card.get("ok_to_submit") is not ok_submit or dl.get("ok_to_submit") is not ok_submit:
        raise ValueError("CRP1 card/download disagree with the independent selector")
    if (card.get("verdict") == "promote") is not ok_submit:
        raise ValueError("CRP1 verdict disagrees with the independent selector")
    note_path = root / "docs/downloads" / dl["note_file"]
    if len(dl["note"]) > 140 or note_path.read_text().strip() != dl["note"]:
        raise ValueError("CRP1 note is missing, changed, or exceeds 140 characters")

    e = lambda s: escape(str(s), quote=True)  # noqa: E731
    h = card["holdout"]
    lo, hi = h["ci95"]["interval"]
    paired = card["paired_vs_baseline"]
    plo, phi = paired["ci95"]
    nov = card["correlation_overlap_vs_registry"]
    c2st = card["c2st_exact_file"]
    canary = card["leakage_canary"]
    best = card["recorded_best_same_evaluator"]["dti"]
    size = target.stat().st_size / (1024**2)
    decision_word = "YES" if ok_submit else "NO"
    decision_label = "OK_TO_SUBMIT" if ok_submit else "DO_NOT_SUBMIT"
    status_cls = "status" if ok_submit else "status stopped"
    verdict_sentence = "Frozen negative result; no retuning or slot. Current policy retains all literal comparators and blocks unknown quota and the missing independent positive replay certificate. The v1 JSON remains historical, not a release permission."
    reasons = (
        "".join(f"<li>{e(r)}</li>" for r in current_screen.get("reasons", []))
        or "<li>None — all gates passed.</li>"
    )
    gate_rows = "".join(
        f"<tr><td>{e(k)}</td><td><strong>{'PASS' if v else 'FAIL'}</strong></td></tr>"
        for k, v in current_screen["gates"].items()
    )
    status_box = (
        f'<div class="{status_cls}" role="status"><strong>NEWLY COMPUTED RESEARCH (H24-CRP1, 2026-10-26) — '
        f"DOWNLOAD: YES · SUBMIT: {decision_word} ({decision_label}).</strong> "
        f"{e(verdict_sentence)} Validated end-to-end by project automation — shared "
        f"format validator, leakage canaries, SegmentHoldout, registry novelty, exact-file "
        f"C2ST and the independent selector — with <strong>no human-inspector fallback</strong>. "
        f"HOLDOUT-DTI is a local measurement, not a leaderboard score or forecast.</div>"
    )
    hero_html = f"""<div class="hero"><div><div class="eyebrow">DOE GEMS · retained parallel GeoTIFF generated 2026-10-26</div>
<h1>One new file.<br>One automatic decision.</h1>
<p class="lead">H24-CRP1 computed its own predictions from physical layers (compositional radiometric
fronts, cross-depth magnetic persistence, curvature saddles) with selective nuisance
residualization. <strong>No previous submission pixels were copied.</strong> Download it with one
click; the independent selector receipt below states whether it may be submitted.</p>
{status_box}
<div class="actions"><a class="button primary" href="downloads/{e(name)}" download="{e(name)}">↓ Download CRP1 research .tif — DO NOT SUBMIT <span>({size:.2f} MiB)</span></a>
<a class="button" href="executive-summary.html#crp1">Executive summary &amp; gates →</a>
<a class="button" href="downloads/{e(name[:-4])}.selector.json">Archived v1 selector (JSON)</a><a class="button" href="data/crp1_current_policy_screen.json">Current negative-only policy</a></div>
<p class="fileline">{e(name)}</p><p class="hash">SHA-256 {e(digest)}</p>
<p class="micro"><span class="badge blue">Single-band float32 · EPSG:32611 · values in [0,1]</span>
<span class="badge {"blue" if ok_submit else "danger"}">{decision_label}</span> <span class="badge gray">0 slots used by this repository session</span></p></div>
<aside class="card visual"><div class="cardtop"><h3>HOLDOUT-DTI</h3><span class="badge amber">Not a leaderboard score</span></div>
<div class="result-number">{h["dti"]:.5f}</div>
<p>95% CI [{lo:.5f}, {hi:.5f}] · evaluator <code>{e(h["evaluator_version"])}</code> ·
{h["n_withheld_positive_pixels"]:,} withheld positives · paired Δ vs reconstructed OOF baseline
{paired["delta_dti"]:+.5f} (95% CI [{plo:+.5f}, {phi:+.5f}]) · execution-time GVC1 comparator {best:.5f}; see current point-best in the featured gate table.</p>
<img class="raster-preview" src="assets/crp1-preview.png" alt="Downsampled map of CRP1 experimental fault dots, not verified faults or geothermal vents">
<p class="micro">Experiment preview · downsampled 100 m grid · not verified faults or vents</p></aside></div>"""

    exec_html = f"""<section id="crp1" class="card" aria-label="H24-CRP1 executive summary">
<div class="eyebrow">Executive summary · unique file generated this session</div>
<h2>H24-CRP1 — is this exact file OK to download and submit?</h2>
{status_box}
<div class="actions"><a class="button primary" href="downloads/{e(name)}" download="{e(name)}">↓ Download {e(name)} ({size:.2f} MiB)</a>
<a class="button" href="downloads/{e(dl["nan_file"])}" download>NaN-outside twin</a>
<a class="button" href="data/crp1_run_card.json">Full JSON run card</a>
<a class="button" href="downloads/checks-{e(name[:-4])}.json">Exact-file validator JSON</a></div>
<p class="hash">SHA-256 {e(digest)}</p>
<h3>Unique name and short comment (paste into the submission Note field if — and only if — the selector says OK)</h3>
<div class="note" id="note-crp1">{e(dl["note"])}</div>
<div class="actions" style="margin-top:10px"><button class="button" data-copy="#note-crp1" data-feedback="#fb-crp1">Copy note</button>
<a class="button" href="downloads/{e(dl["note_file"])}" download>Note .txt</a></div>
<p class="copyfeedback" id="fb-crp1" aria-live="polite"></p>
<p class="micro">{len(dl["note"])} characters · maximum 140</p>
<h3>Current negative-only policy screen (archived v1 receipt kept separately)</h3>
<div class="tablewrap"><table><thead><tr><th>Gate</th><th>Decision</th></tr></thead><tbody>{gate_rows}</tbody></table></div>
<ul>{reasons}</ul>
<p>Measured evidence: leakage canary worst polarity extremity {canary["worst_polarity_extremity"]:.4f} (limit 0.90);
surface max |ρ| {nov["surface_max_abs_rank_correlation"]:.4f} and final-dot max |ρ| {nov["final_max_abs_rank_correlation"]:.4f} (limit 0.90);
max competing-method 3-px dot overlap {nov["final_max_method_overlap_within_3px"]:.4f} and peer overlap
{nov["final_max_peer_overlap_within_3px"]:.4f} (limit 0.70); literal all-entry novelty
{"passed" if nov["literal_all_entries_passed"] else "FAIL — literal controls and/or competing methods retained; no exceptions"};
exact-file C2ST AUC {c2st["observed_auc"]:.4f} (strict gate {"PASS" if c2st["strict_gate_passed"] else "FAIL"});
{dl["pixel_count"]:,} binary dots. Every competition score quoted on this site remains
<strong>OWNER-REPORTED, UNVERIFIED</strong> unless an organizer receipt is published; CRP1 has
<strong>no organizer score</strong>. Local validation cannot guarantee portal acceptance or a score
above 0.2778.</p></section>"""

    fold_rows = "".join(
        f"<tr><td>{e(f['fold'])}</td><td>{f['dti']:.5f}</td><td>{int(f['n_truth']):,}</td><td>{int(f['n_emitted']):,}</td></tr>"
        for f in h["folds"]
    )
    research_html = f"""<section><h2>H24-CRP1 (2026-10-26) — preregistered method and result</h2>
<p><strong>Hypothesis:</strong> {e(card["hypothesis"])}</p>
<p><strong>Mechanism:</strong> {e(card["mechanism"])}</p>
<p><strong>Named non-fault mimic:</strong> {e(card["named_non_fault_mimic"])}</p>
<div class="tablewrap"><table><thead><tr><th>Fold</th><th>HOLDOUT-DTI</th><th>Withheld positives</th><th>Emitted dots</th></tr></thead>
<tbody>{fold_rows}</tbody></table></div>
<p>Pooled HOLDOUT-DTI <strong>{h["dti"]:.5f}</strong> (95% CI [{lo:.5f}, {hi:.5f}]) on
<code>{e(h["evaluator_version"])}</code>. Spec frozen before implementation in
<code>knowledge/20_preregistered_CRP1_2026-10-26.md</code>; verdict
<code>{e(card["verdict"])}</code> from the independent selector. Fault recovery is the benchmark
target — this raster is not evidence of a geothermal vent, heat or permeability.</p></section>"""
    return hero_html, exec_html, research_html
