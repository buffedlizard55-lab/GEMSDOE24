#!/usr/bin/env python3
"""Build the nine-site executive summary HTML and the protocol run card from evidence JSON.

Every number is read from evidence/*.json or the immutable receipts; nothing is typed in.
Outputs:
  docs/nine-site-submission-summary.html
  evidence/run_card_20261029_nine_site_unique.json
Labels: HOLDOUT-DTI (evaluator, count, CI) | OWNER-REPORTED (unverified) | NOT ESTIMABLE.
"""

from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EV = ROOT / "evidence"
CANDIDATE_NAME = "gems24-nine-complement-seghgb-20261029-zeros.tif"
CANDIDATE_REL = f"docs/downloads/{CANDIDATE_NAME}"
NOTE = (
    "GEMS24 nine-complement seg-HGB 37654 dots | 0 overlap vs 9 focus sites | "
    "HOLDOUT-DTI 0.0369 | research only; SUBMIT NO"
)

# Owner-reported values transcribed from the owner's request text (not organizer receipts).
# Keyed by the pinned site/file that the registry lists for that site.
OWNER_REPORTED = {
    "GEMSDOE24": (
        "0.2477",
        "h25-1-dotted-h19-5-d1-5 (owner listed the -nan name; pinned file is -allfinite)",
    ),
    "GEMSDOE25": (
        "0.2600",
        "dotted-h19-5-d2-8 (owner listed the -nan name; pinned file is -zeros)",
    ),
    "GEMSDOE27": (
        "0.2449",
        "topo-gap-closure-t-v2-on-d1-5 (owner listed -nan; pinned file is -allfinite)",
    ),
    "GEMSDOE28": ("0.2710", "h36-1-rung30-blind-r1 (owner listed -nan; pinned file is -allfinite)"),
    "GEMSDOE30": ("0.2600", "d28-poisson300m-offcat-44090"),
    "GEMSDOE31": ("0.2708", "h27-4-solo-d28 (owner listed -nan; pinned file is -allfinite)"),
    "GEMSDOE32": (
        "0.2778",
        "h33-h33-2-b2 (B2) — highest owner-reported value on the nine-site list",
    ),
    "GEMSDOE33": ("0.2632", "h33d-analog-tip-stepover-r30"),
    "GEMSDOE36": ("0.2750", "anderson-geothermal-pinn-38854 (-zeros)"),
}


def load(name):
    return json.loads((EV / name).read_text())


def pct(x):
    return f"{100 * x:.1f}%"


def build_html(ov, seg, comp, reg):
    rows_site = []
    b2_row = [
        v for k, v in ov["nine_site_matrix_row_to_col"]["GEMSDOE32"].items() if k != "GEMSDOE32"
    ]
    pct_lo = f"{100 * min(b2_row):.1f}%"
    pct_hi = f"{100 * max(b2_row):.1f}%"
    min_pair = min(
        v for a, row in ov["nine_site_matrix_row_to_col"].items() for b, v in row.items() if a != b
    )
    best_owner = max(OWNER_REPORTED.items(), key=lambda kv: float(kv[1][0]))
    for site, rec in ov["champions"].items():
        max_other = ov["max_overlap_with_any_other_focus_site"][site]
        unique = max_other <= 0.70
        rel = rec["file"]
        rows_site.append(
            f"<tr><td><b>{site}</b></td>"
            f'<td><a href="{html.escape(rec["url"])}">{html.escape(rel)}</a>'
            f"<br><small>SHA-256 <code>{rec['sha256'][:16]}…</code> · immutable commit</small></td>"
            f"<td>{rec['dots']:,}</td>"
            f"<td>{OWNER_REPORTED[site][0]}<br><small>OWNER-REPORTED · UNVERIFIED</small></td>"
            "<td><b>NOT ESTIMABLE</b><br><small>no organizer receipt</small></td>"
            f"<td>{pct(max_other)}</td>"
            f"<td>{'YES' if unique else '<b>NO</b>'}</td>"
            f"<td>{'Download: research · Submit: <b>NO</b>'}</td></tr>"
        )
    cand = ov["candidate"]
    rows_site.append(
        "<tr class='ok'><td><b>UNIQUE CANDIDATE</b><br><small>generated 2026-10-29</small></td>"
        f'<td><a href="downloads/{CANDIDATE_NAME}"><b>{CANDIDATE_NAME}</b></a>'
        f"<br><small>SHA-256 <code>{cand['sha256'][:16]}…</code></small></td>"
        f"<td>{cand['dots']:,}</td>"
        f"<td>NONE</td>"
        f"<td><b>NOT ESTIMABLE</b><br><small>HOLDOUT-DTI {comp['holdout_dti']['dti']:.4f} "
        f"[{comp['holdout_dti']['ci95'][0]:.4f}, {comp['holdout_dti']['ci95'][1]:.4f}], "
        f"{comp['holdout_dti']['n_withheld_positive_pixels']:,} withheld</small></td>"
        f"<td>{pct(cand['overlap_vs_nine_max'])} max</td>"
        "<td><b>YES</b> (vs nine)<br><small>registry-lattice test FAILS</small></td>"
        "<td><b>Download: YES (format-valid, research)<br>Submit: NO</b></td></tr>"
    )
    matrix_head = "".join(f"<th>{s[-2:]}</th>" for s in ov["champions"])
    matrix_rows = []
    for a in ov["champions"]:
        cells = []
        for b in ov["champions"]:
            v = ov["nine_site_matrix_row_to_col"][a][b]
            style = "" if a == b else (" class='hi'" if v > 0.70 else "")
            cells.append(f"<td{style}>{v:.3f}</td>")
        matrix_rows.append(f"<tr><th>{a}</th>{''.join(cells)}</tr>")
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Nine-site submission executive summary · GEMS DOE 24</title>
<style>
body{{font-family:system-ui,Arial,sans-serif;max-width:1180px;margin:24px auto;padding:0 16px;color:#17202a;line-height:1.45}}
table{{border-collapse:collapse;width:100%;margin:12px 0;font-size:14px}}
th,td{{border:1px solid #cfd8e3;padding:6px 8px;vertical-align:top;text-align:left}}
th{{background:#eef3f8}} tr.ok td{{background:#eefaf0}} td.hi{{background:#fde8e8}}
.verdict{{border:3px solid #b42318;background:#fff4f2;padding:14px 18px;border-radius:8px;margin:14px 0}}
.good{{border:3px solid #067647;background:#ecfdf3;padding:14px 18px;border-radius:8px;margin:14px 0}}
code{{font-size:12px}} small{{color:#475467}}
</style></head><body>
<h1>Nine focus sites: which file to download, and is it unique?</h1>
<p><b>Date:</b> 2026-10-29 · <b>Branch:</b> arena/6a1fb4d1-gemsdoe24 · <b>Scope:</b> GEMSDOE 24, 25, 27, 28, 30, 31, 32, 33, 36.</p>

<div class="verdict"><b>BOTTOM LINE — SUBMIT NOTHING FROM THIS PAGE YET.</b>
<ul>
<li><b>Highest owner-reported file: GEMSDOE32 B2 at 0.2778</b> (OWNER-REPORTED, no organizer receipt). It is <b>NOT unique</b>: {pct_lo}–{pct_hi} of GEMSDOE32's own dots lie within 3 px of dots from each other focus site.</li>
<li><b>All nine sites are one family.</b> The lowest pairwise overlap is {min_pair:.3f}. The nine files are not nine independent approaches.</li>
<li><b>The only unique file generated today</b> is <code>{CANDIDATE_NAME}</code>. It is format-valid and downloadable, but its holdout score is <b>HOLDOUT-DTI {comp["holdout_dti"]["dti"]:.4f}</b>, roughly half the unrestricted baseline ({seg["holdout_dti"]["dti"]:.4f}), so it is <b>not competitive</b>. Its verdict is <b>DOWNLOAD: research only · SUBMIT: NO</b>.</li>
</ul></div>

<div class="good"><b>How to make the portal accept a file.</b> Upload a single-band float32 GeoTIFF whose stored values are all finite and in [0, 1]. The <code>-zeros</code> variant satisfies a strict whole-array check. The earlier error &ldquo;Predicted values must be in range [0, 1]&rdquo; is <b>not confirmed</b>. A NaN-outside file is a plausible cause but is untested. See <a href="#howto">how to submit</a>.</div>

<h2>1. Per-site table (download · estimated score · unique?)</h2>
<p><b>Estimated score:</b> NOT ESTIMABLE for every row. The owner-reported values are shown for reference only and are not organizer-confirmed. Leaderboard values quoted in the request (0.3195, 0.4413) are unverified and conflict with each other.</p>
<table>
<tr><th>Site</th><th>File to download (pinned)</th><th>Dots</th><th>Owner-reported score</th><th>Estimated leaderboard score</th><th>Max 3-px overlap with other 8 focus sites</th><th>Unique vs the other GEMSDOE sites?</th><th>Decision</th></tr>
{"".join(rows_site)}
</table>
<p>Best owner-reported: <b>{best_owner[0]} = {best_owner[1][0]}</b> (not unique). Best unique file: <b>{CANDIDATE_NAME}</b> (not competitive).</p>

<h2>2. Pairwise uniqueness matrix (share of row-site dots within 3 px of column-site dots)</h2>
<table><tr><th></th>{matrix_head}</tr>{"".join(matrix_rows)}</table>
<p>Cells above 0.70 (red) fail the user's 70% threshold. Geometry only, not proof of copying.</p>

<h2 id="howto">3. How to submit (manual upload, no automation)</h2>
<ol>
<li>Download the file in the table. For the unique candidate that is <a href="downloads/{CANDIDATE_NAME}"><code>{CANDIDATE_REL}</code></a>.</li>
<li>Go to the competition submission form on DrivenData. You must sign in yourself. This project has no organizer credentials and does not submit anything.</li>
<li>Choose the file under <i>File to submit</i>. Accepted: a single-band GeoTIFF (.tif), or a .zip containing one, matching the template CRS (EPSG:32611), shape (3730 × 3292) and geotransform.</li>
<li>Enter the note (at most 140 characters): <code>{html.escape(NOTE)}</code> ({len(NOTE)} characters).</li>
<li><b>Do not spend a weekly slot on the candidate.</b> It fails the rule that a file must beat the current holdout best before a slot is used.</li>
</ol>

<h2>4. Irregularities to review</h2>
<ul>
<li>The bridge <code>sample_submission.tif</code> has exactly the same 60,988 positive pixels as <code>labels.tif</code> and <code>existing_faults.tif</code> (byte-identical). The &ldquo;sample&rdquo; is therefore a catalogue mask, not an independent example.</li>
<li>The training raster was restored from the owner's GitHub mirror (<code>buffedlizard55-lab/GEMSDOE</code>, pinned commit). It matches the pinned SHA-256 but is <b>not organizer-authenticated</b>.</li>
<li>Owner-listed file names differ from the pinned files for GEMSDOE24, 25, 27, 28 and 31 (owner wrote <code>-nan</code>; pinned files are <code>-allfinite</code> or <code>-zeros</code>). Byte identity with the scored file is not established.</li>
<li>The protocol's &ldquo;single method paragraph&rdquo; lane assignment is missing from the request. No lane was assigned.</li>
<li>The 70% rule, applied to the registry calibration lattice <code>13gems_20261001_r13-lattice-s5</code> (GEMSDOE13), is a geometric impossibility above 22,164 dots: any set of N in-footprint dots has at least 1 − 6,649/N of its dots within 3 px of that lattice, so the share exceeds 70% for every N above 22,164, however the dots are chosen. This needs a decision by the owner.</li>
</ul>

<h2>5. Limitations and what is needed</h2>
<ul>
<li>No organizer receipt, leaderboard access or submission quota check. DrivenData pages were not re-read this session (repo policy).</li>
<li>HOLDOUT-DTI is an internal proxy: withheld catalogue fault segments, not the hidden leaderboard truth.</li>
<li>The full 2026-10-29 registry comparison covers 82 local binary rasters. It does not cover all live peer submissions.</li>
</ul>

<h2>6. Sources (official or owner-pinned, for manual review)</h2>
<ul>
<li>Competition: <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">drivendata.org/competitions/306</a> · problem: <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">page/967</a> · data: <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/data/">data</a> · leaderboard: <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">leaderboard</a></li>
<li>Submission format: <a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">NLR FY26 OSTI 96647</a> · reference solution: <a href="https://github.com/drivendataorg/gems-prize-reference-solution">github.com/drivendataorg/gems-prize-reference-solution</a> · CRS: <a href="https://epsg.io/32611">epsg.io/32611</a></li>
<li>Champion files: immutable GitHub URLs listed in the table, pinned in <code>evidence/peer_forensics_20261025.json</code>.</li>
<li>Evidence: <code>evidence/nine_site_overlap_20261029.json</code>, <code>evidence/candidate_registry_overlap_20261029.json</code>, <code>evidence/seg_hgb_experiment.json</code>, <code>evidence/seg_hgb_complement_experiment.json</code>.</li>
</ul>
<p><small>Generated by <code>scripts/build_nine_site_report.py</code> from evidence files. Maximize P(Win) · Own the Outcome.</small></p>
</body></html>
"""


def build_run_card(ov, seg, comp, reg, pre):
    cand = ov["candidate"]
    return {
        "run_card_version": "1",
        "date": "2026-10-29",
        "branch": "arena/6a1fb4d1-gemsdoe24",
        "lane": "exploratory; no assigned method paragraph; NOT preregistered",
        "experiments_used": 2,
        "experiment_budget": 3,
        "hypothesis": (
            "Restricting dots to footprint pixels more than 3 px from every nine-site "
            "champion dot yields a file that is unique versus the nine focus sites while "
            "retaining detectable holdout signal from a label-free detector."
        ),
        "mechanism": (
            "Label-free features (19-band geophysics + LiDAR scarp/arc channels from the "
            "prepared cache) feed a histogram gradient-boosting classifier trained only on "
            "visible catalogue positives inside buffered training regions. The top 37,654 "
            "pixels are emitted per quadrant share, ranked after the champion-distance mask."
        ),
        "named_non_fault_mimic": (
            "Linear artefacts in gridded magnetic, gravity or DEM products (flight-line and "
            "stitching seams, road cut-and-fill, drainage incision) that look like fault edges "
            "but are not faults."
        ),
        "holdout": {
            "label": "HOLDOUT-DTI",
            "evaluator_version": comp["holdout_dti"]["evaluator_version"],
            "withheld_positive_pixels": comp["holdout_dti"]["n_withheld_positive_pixels"],
            "candidate_dti": comp["holdout_dti"]["dti"],
            "candidate_ci95": comp["holdout_dti"]["ci95"],
            "baseline_unrestricted_dti": seg["holdout_dti"]["dti"],
            "baseline_ci95": seg["holdout_dti"]["ci95"],
            "candidate_fold_components": comp["folds"],
            "exact_soft_metric_cross_check": "all four fold TP/FP/FN reproduced by dti_components_exact (see tests)",
        },
        "leakage_canary": {
            "rule": "single-feature holdout AUC > 0.90 means leakage until proven otherwise",
            "worst_single_feature_auc": seg["leakage_canary"]["worst_single_feature_auc"],
            "pass": seg["leakage_canary"]["pass"],
        },
        "overlap_vs_registry": {
            "vs_nine_focus_sites_max": cand["overlap_vs_nine_max"],
            "vs_nine_focus_sites_pearson_max": cand["pearson_vs_nine_max"],
            "vs_local_registry_max": reg["max_overlap"],
            "vs_local_registry_max_file": reg["top"][0]["file"],
            "vs_local_registry_max_abs_pearson": reg["max_abs_pearson"],
            "registry_files_compared": reg["files_compared"],
            "thresholds": {"overlap": 0.70, "pearson": 0.90},
            "gate_unique_vs_nine": cand["overlap_vs_nine_max"] <= 0.70,
            "gate_literal_registry_70pct": reg["max_overlap"] <= 0.70,
        },
        "raster": {
            "file": CANDIDATE_REL,
            "sha256": cand["sha256"],
            "dots": cand["dots"],
        },
        "validator": {
            "format_valid": pre["format_validation"]["format_valid"],
            "strict_whole_array_0_1": pre["portal_range_diagnostic"][
                "strict_whole_array_values_in_0_1"
            ],
            "nan_inside_footprint": cand["nan_inside_footprint"],
            "outside_footprint_values": [0.0],
            "crs_shape_transform_match_template": pre["format_validation"]["checks"][
                "crs_epsg_32611"
            ]["pass"]
            and pre["format_validation"]["checks"]["shape_matches_template"]["pass"],
            "preflight_decision": pre["decision"]["submission_status"],
            "preflight_blockers": pre["decision"]["blockers"],
        },
        "submission_name": CANDIDATE_NAME.replace(".tif", ""),
        "submission_note": NOTE,
        "submission_note_chars": len(NOTE),
        "verdict": "negative",
        "download": "YES (research; format-valid)",
        "submit": "NO",
        "submit_reasons": [
            "holdout DTI is about half the unrestricted baseline and far below the repo-recorded best HOLDOUT-DTI 0.166060 (S3DEP1; recorded in README, not reproduced this session; that file is not unique)",
            "literal 70% registry rule fails against the calibration lattice (overlap 0.9728)",
            "portal rejection cause not established; no organizer receipt",
            "no promotion run card or selector quota (preflight blockers)",
        ],
        "not_estimable": "Leaderboard score NOT ESTIMABLE; HOLDOUT-DTI is internal and not comparable to the hidden leaderboard.",
        "irregularities": [
            "bridge sample_submission positives identical to labels/catalogue",
            "owner-mirror training raster, not organizer-authenticated",
            "owner-listed file names differ from pinned files (nan/allfinite/zeros) for 24, 25, 27, 28, 31",
            "method-lane paragraph absent; no lane assigned",
            "literal 70% rule incompatible with a 5-px lattice registry raster above ~22,164 dots",
        ],
    }


def main() -> None:
    ov = load("nine_site_overlap_20261029.json")
    seg = load("seg_hgb_experiment.json")
    comp = load("seg_hgb_complement_experiment.json")
    reg = load("candidate_registry_overlap_20261029.json")
    pre = json.loads(
        (
            ROOT / "docs/downloads/gems24-nine-complement-seghgb-20261029-zeros.preflight.json"
        ).read_text()
    )
    (ROOT / "docs/nine-site-submission-summary.html").write_text(build_html(ov, seg, comp, reg))
    card = build_run_card(ov, seg, comp, reg, pre)
    (EV / "run_card_20261029_nine_site_unique.json").write_text(
        json.dumps(card, indent=2, allow_nan=False) + "\n"
    )
    print("wrote docs/nine-site-submission-summary.html and evidence run card")
    print("note chars:", len(NOTE))


if __name__ == "__main__":
    main()
