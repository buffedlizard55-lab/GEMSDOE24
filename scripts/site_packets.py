"""Validate and retain concurrent negative packets without selecting a winner."""

from __future__ import annotations

import hashlib
import json
import zipfile
from html import escape

from gems.receipts import research_receipt
from gems.submission import check_variants


def _sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_mtr1_packet(root, primary: dict) -> dict:
    """Re-verify the frozen MTR1 negative packet and return its run card."""
    docs = root / "docs"
    card = json.loads((root / "evidence/mtr1_run_card.json").read_text())
    checks_path = docs / "downloads" / primary["checks_file"]
    checks = json.loads(checks_path.read_text())
    p = docs / "downloads" / primary["file"]
    if _sha256_file(p) != card["raster_sha256"] or _sha256_file(p) != primary["sha256"]:
        raise ValueError("MTR1 download checksum does not match the run card")
    if primary["ok_to_submit"] or card["verdict"] != "negative" or card["ok_to_submit"]:
        raise ValueError("Stopped MTR1 artifact cannot be presented as submit-ready")
    template = root / "data/bridge/sample_submission.tif"
    for key, row in checks.items():
        target = docs / "downloads" / row["file"]
        fresh = check_variants(target, template)
        if (
            not fresh["format_valid"]
            or not row["format_valid"]
            or any(fresh.get(field) != value for field, value in row.items())
        ):
            raise ValueError(f"Invalid, changed or stale MTR1 download variant: {key}")
    if primary["file"] != card["submission_name"] or primary["note"] != card["note"]:
        raise ValueError("MTR1 metadata and exact run-card identity disagree")
    if (
        len(primary["note"]) > 140
        or (docs / "downloads" / primary["note_file"]).read_text().strip() != primary["note"]
    ):
        raise ValueError("MTR1 note is missing, changed or over the 140-character limit")
    return card


def concurrent_mtr1(root, primary: dict) -> str:
    """Compact, hash-verified card retaining the earlier unsupervised MTR1 negative packet."""
    card = verify_mtr1_packet(root, primary)
    e = lambda s: escape(str(s), quote=True)  # noqa: E731
    score = card["holdout"]
    lo, hi = score["ci95"]["interval"]
    name = primary["file"]
    return f"""<aside class="card concurrent" aria-label="Preserved MTR1 unsupervised experiment">
<h3>Retained MTR1 unsupervised packet — also NOT OK TO SUBMIT</h3>
<p>Earlier unsupervised paired-magnetic-trough × contractor Th/K run preserved intact for audit.
Evaluated on the same <code>{e(score["evaluator_version"])}</code> protocol ({score["n_withheld_positive_pixels"]:,} withheld positives):
<strong>HOLDOUT-DTI {score["dti"]:.5f}</strong> (95% CI [{lo:.5f}, {hi:.5f}]); stopped automatically on spacing-5 calibration lattice overlap.</p>
<div class="actions"><a class="button" href="downloads/{e(name)}" download="{e(name)}">↓ MTR1 audit TIFF — DO NOT SUBMIT</a>
<a class="button" href="data/mtr1_run_card.json" download>MTR1 run card</a></div>
<details><summary>MTR1 checksum and short note</summary>
<p class="note">{e(primary["note"])}</p><p class="hash">SHA-256 {e(primary["sha256"])}</p></details></aside>"""


def verify_gvc1_packet(root) -> tuple[dict, dict, dict, dict]:
    """Re-verify the GVC1 negative audit packet, run card, experiment receipt, and C2ST receipt."""
    docs = root / "docs"
    primary = json.loads((docs / "data/gvc1_download.json").read_text())
    card = json.loads((root / "evidence/gvc1_run_card_20261025.json").read_text())
    experiment = json.loads((root / "evidence/gvc1_experiment_20261025.json").read_text())
    c2st = json.loads((root / "evidence/gvc1_c2st_audit_20261025.json").read_text())

    if primary["ok_to_submit"] or card["verdict"] != "negative" or card["ok_to_submit"]:
        raise ValueError("Stopped GVC1 negative artifact cannot be presented as submit-ready")
    p = docs / "downloads" / primary["file"]
    if _sha256_file(p) != card["raster_sha256"] or _sha256_file(p) != primary["sha256"]:
        raise ValueError("GVC1 download checksum does not match the run card")
    checks = json.loads((docs / "downloads" / primary["checks_file"]).read_text())
    template = root / "data/bridge/sample_submission.tif"
    for key in ("zero_outside", "nan_outside"):
        row = checks[key]
        target = docs / "downloads" / row["file"]
        fresh = check_variants(target, template)
        if (
            not fresh["format_valid"]
            or not row["format_valid"]
            or any(fresh.get(field) != value for field, value in row.items())
        ):
            raise ValueError(f"Invalid, changed or stale GVC1 download variant: {key}")
    zip_target = docs / "downloads" / checks["nan_zip_file"]
    if _sha256_file(zip_target) != checks["nan_zip_sha256"]:
        raise ValueError("Invalid, changed or stale GVC1 ZIP variant")
    with zipfile.ZipFile(zip_target) as zf:
        names = zf.namelist()
        if names != [checks["nan_outside"]["file"]]:
            raise ValueError(f"GVC1 ZIP must contain exactly nan_outside .tif, got {names}")
        inner_sha = hashlib.sha256(zf.read(names[0])).hexdigest()
        if inner_sha != checks["nan_outside"]["sha256"]:
            raise ValueError("GVC1 ZIP inner TIFF hash disagrees with nan_outside receipt")
    if primary["file"] != card["submission_name"] or primary["note"] != card["note"]:
        raise ValueError("GVC1 metadata and exact run-card identity disagree")
    if (
        len(primary["note"]) > 140
        or (docs / "downloads" / primary["note_file"]).read_text().strip() != primary["note"]
    ):
        raise ValueError("GVC1 note is missing, changed or over the 140-character limit")
    return primary, card, experiment, c2st


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
