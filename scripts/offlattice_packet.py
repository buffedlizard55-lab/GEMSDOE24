"""Render the merged PR #85 research raster without implying uniqueness or approval.

The TIFF and scientific run card are immutable inputs. This module only checks
that the local file still matches its recorded hash/format and renders the
recorded result with its protocol limitations; it never recomputes the surface
or holdout and never authorizes a submission.
"""

from __future__ import annotations

import json
import math
from html import escape
from pathlib import Path

from gems.submission import check_variants
from gems.validator import sha256_file

CARD = "24gems-interior-offlattice-geothermal-20261028T164358Z-e5a3c34b27db_run_card.json"
CARD_SHA256 = "d3e11253d6ed17087be6602ee4084abbd57da873e0f561607fdfd672f60c3dd7"
DOWNLOAD = "24gems-interior-offlattice-geothermal-20261028T164358Z-e5a3c34b27db_download.json"


def _check_card(root: Path) -> tuple[dict, dict, str, str, list[float]]:
    card_path = root / "evidence" / CARD
    if not card_path.is_file() or sha256_file(card_path) != CARD_SHA256:
        raise ValueError("PR #85 scientific run card differs from the frozen source")
    card = json.loads(card_path.read_text())
    holdout = card.get("holdout")
    if not isinstance(holdout, dict):
        raise ValueError("PR #85 research card is missing its HOLDOUT-DTI record")

    filename = card.get("validator_output", {}).get("file")
    if (
        card.get("schema") != "interior-offlattice-submission-v1"
        or not isinstance(filename, str)
        or Path(filename).name != filename
        or not filename.endswith("-zeros.tif")
        or filename != f"{card.get('submission_name')}-zeros.tif"
        or card.get("verdict") != "negative"
        or card.get("ok_to_download") is not True
        or card.get("ok_to_submit") is not False
        or card.get("submission_authorized") is not False
        or card.get("slots_used") != 0
        or card.get("organizer_confirmed_score") is not None
        or card.get("leaderboard_estimate") is not None
    ):
        raise ValueError("PR #85 research card identity or negative decision changed")

    score = holdout.get("pooled_dti")
    ci = holdout.get("ci95")
    if (
        holdout.get("label") != "HOLDOUT-DTI"
        or holdout.get("evaluator_version") != "gems-segment-pooled-v1"
        or holdout.get("n_withheld_positive_pixels") != 60988
        or (holdout.get("protocol") or {}).get("buffer_m") != 3000
        or type(score) not in (float, int)
        or not math.isfinite(score)
        or not 0 <= score <= 1
        or not isinstance(ci, list)
        or len(ci) != 2
        or any(type(value) not in (float, int) or not math.isfinite(value) for value in ci)
        or not 0 <= ci[0] <= score <= ci[1] <= 1
    ):
        raise ValueError("PR #85 HOLDOUT-DTI record is malformed or changed protocol")

    # The novelty record is intentionally treated as a single-lattice diagnostic,
    # never as a complete registry decision or submission gate.
    lattice = card.get("novelty_vs_lattice", {})
    if (
        lattice.get("lattice_overlap_within_3px") != 0.0
        or lattice.get("lattice_duplicate_stop") is not False
        or card.get("experiments_run") != 1
    ):
        raise ValueError("PR #85's frozen lattice-only diagnostic or run identity changed")

    raster = root / "docs" / "downloads" / filename
    if not raster.is_file() or sha256_file(raster) != card.get("raster_sha256"):
        raise ValueError("PR #85 research raster is missing or differs from its run card")
    validator = check_variants(raster, root / "data/bridge/sample_submission.tif")
    recorded = card["validator_output"]
    if (
        validator.get("sha256") != card.get("raster_sha256")
        or validator.get("format_valid") is not True
        or validator.get("submission_authorized") is not False
        or validator.get("in_footprint_positive_pixels") != card.get("dots_emitted")
        or recorded.get("sha256") != card.get("raster_sha256")
        or recorded.get("template_origin_authenticated") is not False
    ):
        raise ValueError("PR #85 research raster no longer passes its recorded local format checks")

    checks_name = filename.removesuffix("-zeros.tif") + "-checks.json"
    checks_path = root / "docs" / "downloads" / checks_name
    download_path = root / "docs" / "data" / DOWNLOAD
    run_card_copy = root / "docs" / "data" / CARD
    if not checks_path.is_file() or not download_path.is_file() or not run_card_copy.is_file():
        raise ValueError("PR #85 download evidence is incomplete")
    checks = json.loads(checks_path.read_text())
    download = json.loads(download_path.read_text())
    if (
        checks.get("sha256") != card["raster_sha256"]
        or checks.get("format_valid") is not True
        or checks.get("submission_authorized") is not False
        or download.get("file") != filename
        or download.get("sha256") != card["raster_sha256"]
        or download.get("verdict") != "negative"
        or download.get("ok_to_submit") is not False
        or run_card_copy.read_bytes() != card_path.read_bytes()
    ):
        raise ValueError("PR #85 download receipts disagree with the frozen run card")
    return card, validator, filename, checks_name, ci


def render(root: Path) -> dict[str, str]:
    """Return a prominently negative HTML card and README status paragraph."""
    root = Path(root)
    card, validator, filename, checks_name, ci = _check_card(root)
    holdout = card["holdout"]
    score = holdout["pooled_dti"]
    lo, hi = ci
    escaped_name = escape(filename, quote=True)
    escaped_hash = escape(card["raster_sha256"], quote=True)
    card_link = escape(CARD, quote=True)
    checks_link = escape(checks_name, quote=True)
    dti_text = f"{score:.9f}"
    ci_text = f"[{lo:.9f}, {hi:.9f}]"
    n_withheld = holdout["n_withheld_positive_pixels"]
    buffer_m = holdout["protocol"]["buffer_m"]

    html = f"""<section class=\"card research-warning\" id=\"pr85-research-raster\" aria-label=\"PR 85 research raster status\">
<h2>PR #85 research TIFF — literal uniqueness NOT ESTABLISHED</h2>
<p><strong>DOWNLOAD: YES (research only) · SUBMIT: NO.</strong> This file is not cleared as a unique submission. The merged PR #85 artifact remains available for audit, but its run card does not establish protocol-compliant uniqueness or submission eligibility.</p>
<p><a class=\"button primary\" href=\"downloads/{escaped_name}\" download=\"{escaped_name}\">Download exact PR #85 research GeoTIFF — DO NOT SUBMIT</a> · <a href=\"data/{card_link}\" download>Run-card JSON</a> · <a href=\"downloads/{checks_link}\" download>Local format-check JSON</a></p>
<p class=\"fileline\">{escaped_name}</p><p class=\"hash\">SHA-256 {escaped_hash}</p>
<div class=\"tablewrap\" tabindex=\"0\" role=\"region\" aria-label=\"PR #85 research TIFF evidence details\"><table><tbody>
<tr><th>Run-card result</th><td><strong>HOLDOUT-DTI {dti_text}</strong>; reported 95% CI {ci_text}; <code>gems-segment-pooled-v1</code>; {n_withheld:,} withheld positives; {buffer_m:,} m buffer. Internal result only, not replayed here or organizer-confirmed.</td></tr>
<tr><th>Comparable score / leaderboard</th><td>The 3,000 m collar differs from the 1,500 m comparison cards; treat this estimate as a different protocol, not a directly comparable score. Leaderboard estimate: <strong>NOT ESTIMABLE</strong>.</td></tr>
<tr><th>Uniqueness</th><td><strong>NOT ESTABLISHED.</strong> The reported 0.0000 dot overlap is against the retained spacing-5 lattice only; the generator deliberately selects cells more than 3 px from that lattice. The pre-placement surface and complete registry were not checked. Selecting lattice holes conflicts with the no-evasion rule; do not use this as a uniqueness pass.</td></tr>
<tr><th>Local file checks</th><td>SHA-256 and {validator.get("in_footprint_positive_pixels", 0):,} in-footprint dots rechecked. Local format validation passed; organizer template origin and portal acceptance are not established.</td></tr>
<tr><th>Decision</th><td><strong>DO NOT SUBMIT.</strong> Frozen card: negative, submission_authorized=false, slots_used=0.</td></tr>
</tbody></table></div>
<p><a href=\"session-review-2dd70faf-20261028.md\">Three-pass review and evidence limits</a></p>
<p class=\"micro\">The scientific run card and score were not modified. This review created no TIFF, experiment, holdout result or competition slot.</p>
</section>"""

    markdown = (
        f"**PR #85 research TIFF: DOWNLOAD YES (research only) / SUBMIT NO.** "
        f"[`{filename}`](docs/downloads/{filename}) · SHA-256 `{card['raster_sha256']}`. "
        f"Run-card-reported HOLDOUT-DTI {dti_text}, 95% CI {ci_text}, "
        f"`{holdout['evaluator_version']}`, {n_withheld:,} withheld positives, "
        f"{buffer_m:,} m buffer. Its reported 0.0000 overlap checks only one retained lattice "
        "which the generator deliberately avoids; no full-registry/pre-placement test exists. "
        "Literal uniqueness is not established and this hole-targeting conflicts with the "
        "no-evasion rule. The 3 km holdout differs from the 1.5 km comparator protocol; "
        "not a leaderboard estimate or organizer-confirmed score. No slot authorized. "
        "This review ran no new experiment, holdout or TIFF because the assigned method paragraph is absent. "
        f"[run card](evidence/{CARD}) · [format checks](docs/downloads/{checks_name})."
    )
    return {"html": html, "markdown": markdown}
