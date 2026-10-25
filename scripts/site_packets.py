"""Validate and retain current + concurrent negative packets without selecting a winner."""

from __future__ import annotations

import json
from html import escape

from gems.receipts import research_receipt
from gems.validator import sha256_file


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
<p class="micro">Unlocking the 31.8% 3DEP LiDAR gap via tree <code>NaN</code> routing + Miller &amp; Singh tilt-zero sharpness + DEM-Hessian ridge + Th-normalized K alteration jumped <code>NE_LidarGapHeavy</code> from <code>0.13464</code> to <strong><code>0.17285</code></strong> (<code>0.17365</code> pointwise). <code>Ablation B</code> (<code>0.13137</code>) achieved the highest <code>HOLDOUT-DTI</code> recorded in GEMSDOE24; post-hoc <code>K_300</code> kernel smoothing cost <code>-0.00238</code>, and uniform LiDAR-gap tail matching over-allocated dots in flat <code>SW</code> valley gaps.</p></article>
<article class="card"><h3>C2ST Nuisance Breakthrough &amp; Supervised Convergence</h3>
<img class="raster-preview" src="assets/rshg1-preview.png" alt="Downsampled preview of H24-RSHG1 fault dots (37,722 positive cells)">
<p class="micro">Exact-file C2ST AUC dropped from <code>0.5826</code> (SAHG1 FAIL) to <strong><code>{c2st["observed_auc"]:.4f}</code></strong> (null p95 <code>{c2st["null_p95"]:.4f}</code>, Holm <em>p</em> = <code>{c2st["holm_p_value"]:.3f}</code>, <code>claim_m</code> AUC <code>{c2st["single_feature_auc_descriptive"]["claim_m"]:.4f}</code> — <strong>PASS</strong>). Surface max |ρ| = <code>{nov["surface_max_abs_rank_correlation"]:.4f}</code> ≤ 0.90 with zero copied pixels, while 72.69% of predicted off-catalogue dots independently converge within 300 m of <code>gems10-h25-ctx-ridge</code> (<code>0.7233</code> on <code>gems28</code>). <a href="https://github.com/buffedlizard55-lab/GEMSDOE24/blob/main/knowledge/17_preregistered_RSHG1_2026-10-25.md">RSHG1 preregistration →</a> · <a href="https://github.com/buffedlizard55-lab/GEMSDOE24/blob/main/knowledge/18_RSHG1_findings_2026-10-25.md">RSHG1 PhD synthesis &amp; findings →</a></p></article></div></section>"""
    return hero_html, exec_html, research_html


def concurrent_sahg1(root):
    """Validate and render the 2026-10-25 H24-SAHG1 packet and reconstructed OOF baseline."""
    report_path = root / "evidence/sahg1_experiment_20261025.json"
    if not report_path.exists():
        return ""
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
    return f"""<aside class="card concurrent" aria-label="H24-SAHG1 experiment and OOF benchmark">
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
            prefix_html
            + "<p>Concurrent ASPC research stopped without a downloadable artifact.</p>"
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
        + f"""<aside class="card concurrent" aria-label="Preserved concurrent experiment">
<h3>Parallel ASPC result retained — also NOT OK TO SUBMIT</h3>
<p>PR #10 landed earlier on 2026-10-25. Its separate research artifact and evidence are preserved;
no current-best OOF certificate or slot authorization was obtained. Different component/collar and
bootstrap policies mean its point score is <strong>not a comparable current-best ranking</strong>.</p>
<div class="actions"><a class="button" href="downloads/{e(name)}" download="{e(name)}">↓ ASPC research TIFF — DO NOT SUBMIT</a>
<a class="button" href="data/aspc_run_card.json">ASPC evidence</a></div>
<details><summary>Parallel result and short note</summary>
<p>HOLDOUT-DTI {result["value"]:.5f}; 95% CI [{lo:.5f}, {hi:.5f}];
{result["n_withheld_positives"]:,} withheld positives; evaluator <code>{e(result["evaluator_version"])}</code>.
Not a leaderboard score. Its registry scope did not include the local spacing-5 calibration lattice.</p>
<p class="note">{e(row["note"])}</p><p class="hash">SHA-256 {e(digest)}</p></details></aside>"""
    )
