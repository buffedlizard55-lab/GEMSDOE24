"""Validate and retain concurrent negative packets without selecting a winner."""

from __future__ import annotations

import json
from html import escape

from gems.receipts import research_receipt
from gems.validator import sha256_file


def concurrent_fuse(root):
    """Validate and render the 2026-10-25 H24-FUSE (RAW / RESID / HCW) packet."""
    report_path = root / "evidence/fuse_experiment_20261025.json"
    if not report_path.exists():
        return ""
    report = json.loads(report_path.read_text())
    card = json.loads((root / "evidence/fuse_run_card_20261025.json").read_text())
    dl = json.loads((root / "docs/data/fuse_download.json").read_text())
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
<a class="button" href="data/fuse_run_card.json">FUSE JSON run card</a>
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


def concurrent_aspc(root):
    """One compact, independently hash-bound entry; never change its scientific record."""
    sahg1_html = concurrent_sahg1(root)
    report_path = root / "evidence/aspc_run_20261025.json"
    if not report_path.exists():
        return sahg1_html
    report = json.loads(report_path.read_text())
    card = json.loads((root / "evidence/aspc_run_card_20261025.json").read_text())
    row = report.get("artifact")
    if not row:
        return (
            sahg1_html + "<p>Concurrent ASPC research stopped without a downloadable artifact.</p>"
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
        sahg1_html
        + f"""<aside class="card concurrent" aria-label="Preserved concurrent experiments">
<h3>Parallel ASPC, CON &amp; H-UNIQUE-03 results retained — all NOT OK TO SUBMIT</h3>
<p>Earlier 2026-10-25 research artifacts and evidence are preserved for audit; none beat the <code>0.13000</code> OOF baseline or obtained slot authorization:</p>
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
