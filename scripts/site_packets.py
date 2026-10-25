"""Validate and retain concurrent negative packets without selecting a winner."""

from __future__ import annotations

import json
from html import escape

from gems.validator import sha256_file


def concurrent_aspc(root):
    """One compact, independently hash-bound entry; never change its scientific record."""
    report_path = root / "evidence/aspc_run_20261025.json"
    if not report_path.exists():
        return ""
    report = json.loads(report_path.read_text())
    card = json.loads((root / "evidence/aspc_run_card_20261025.json").read_text())
    row = report.get("artifact")
    if not row:
        return "<p>Concurrent ASPC research stopped without a downloadable artifact.</p>"
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
    return f"""<aside class="card concurrent" aria-label="Preserved concurrent experiment">
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
