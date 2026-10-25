"""Validate and retain concurrent negative packets without selecting a winner."""

from __future__ import annotations

import json
from html import escape

from gems.validator import sha256_file


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
<h3>New H24-SAHG1 Strike-Hydro-Geomorph GeoTIFF — DOWNLOAD: YES · SUBMIT: NO (NOT OK TO SUBMIT)</h3>
<p>Independently computed from strike-projected 3DEP LiDAR antislope scarps (<code>G_sat</code>),
immobile-Thorium-controlled mobile K/U alteration (<code>R_alt</code>), and subsurface basement/strain steps
(<code>B_step</code>) inside a verified 9×9 discrete receptive-field support mask (<strong>no copied submission pixels</strong>).
Passes exact-grid/<code>[0,1]</code> format checks and prospective novelty against all <strong>{nov["competing_method_rasters_checked"]}</strong>
competing method lanes (max 3-px overlap <code>{nov["method_lane_max_overlap_within_3px"]:.4f}</code> ≤ 0.70) and
<strong>{nov["peer_blobs_checked"]}</strong> peer blobs (<code>{nov["peer_blobs_max_overlap_within_3px"]:.4f}</code> ≤ 0.70), and beats
both prior 2026-10-25 physical operators (<code>MTR1</code> and <code>ASPC</code>) plus its own geomorphic ablation on
<code>HOLDOUT-DTI</code> — but remains <strong>DO NOT SUBMIT</strong> because it does not beat the newly reconstructed
same-protocol out-of-fold multi-physics HGB baseline (<code>{h_oof["dti"]:.5f}</code>), flags the C2ST nuisance gate
(AUC <code>{c2st["observed_auc"]:.4f}</code>, Holm <em>p</em> = <code>{c2st["holm_p_value"]:.3f}</code>), and triggers the literal
spacing-5 calibration lattice overlap if calibration controls are not separated.</p>
<div class="actions">
<a class="button primary" href="downloads/{e(name)}" download="{e(name)}">↓ SAHG1 audit TIFF (zeros outside) — DO NOT SUBMIT</a>
<a class="button" href="downloads/{e(dl["nan_file"])}" download="{e(dl["nan_file"])}">↓ SAHG1 NaN-outside twin — DO NOT SUBMIT</a>
<a class="button" href="data/sahg1_run_card.json">SAHG1 JSON run card</a>
<a class="button" href="downloads/{e(dl["checks_file"])}">SAHG1 validator JSON</a>
</div>
<details open><summary>SAHG1 HOLDOUT-DTI comparison, short note, and SHA-256 (not leaderboard scores)</summary>
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
    target = root / "docs/downloads" / name
    checks = json.loads(target.with_suffix(".checks.json").read_text())
    if (
        sha256_file(target) != digest
        or checks.get("sha256") != digest
        or checks.get("format_valid") is not True
        or checks.get("submission_authorized") is not False
    ):
        raise ValueError("Concurrent ASPC file or exact-file validator disagrees")
    if (
        report.get("submission_authorized") is not False
        or row.get("submission_authorized") is not False
        or card.get("submission_authorized") is not False
        or card.get("verdict") != "negative"
    ):
        raise ValueError("A negative research page cannot grant ASPC slot authorization")
    twin = report.get("template_convention_companion")
    if twin:
        p = root / "docs/downloads" / twin["file"]
        sidecar = json.loads(p.with_suffix(".checks.json").read_text())
        if (
            sha256_file(p) != twin["sha256"]
            or sidecar.get("sha256") != twin["sha256"]
            or sidecar.get("format_valid") is not True
            or sidecar.get("submission_authorized") is not False
        ):
            raise ValueError("Concurrent ASPC template-convention companion changed")
    if len(row["note"]) > 140:
        raise ValueError("Concurrent lane note exceeds current limit")
    e = lambda s: escape(str(s), quote=True)  # noqa: E731
    result = report["holdout"]
    lo, hi = result["ci95"]
    return (
        sahg1_html
        + f"""<aside class="card concurrent" aria-label="Preserved concurrent experiment">
<h3>Parallel ASPC result retained — also NOT OK TO SUBMIT</h3>
<p>PR #10 landed during this session. Its separate research artifact and evidence are preserved;
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
