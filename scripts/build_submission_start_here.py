#!/usr/bin/env python3
"""Build the submission start-here page and its evidence from verified receipts.

Reads (all local):
  evidence/nine_site_verify_20261030.json          scripts/nine_site_verify.py
  evidence/nine_site_owner_paths_20261030.json     scripts/map_nine_owner_paths.py
  evidence/candidate_verify_<stem>.json            scripts/verify_candidate_tif.py
  evidence/ns_ratio1_experiment_20261030.json      scripts/run_ns_ratio1_lane.py
  data/research/nine_site_verify/*.tif             gitignored downloads
Writes:
  evidence/b2_subset_forensics_20261030.json
  evidence/ns_ratio1_run_card_20261030.json
  docs/submission-start-here.html

Owner-reported scores are copied from the nine-site receipt (its own label:
owner_reported_scores_not_organizer_confirmed). No leaderboard estimate is produced.
"""

from __future__ import annotations

import html
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from nine_site_verify import SITES  # noqa: E402

STEM = "gems24-ns-ratio1-labelfree-ratio-20261030-b49138fa"
ZEROS = f"{STEM}-zeros.tif"
NAN = f"{STEM}-nan.tif"
DL = ROOT / "docs/downloads"
NINE = ROOT / "evidence/nine_site_verify_20261030.json"
PATHS = ROOT / "evidence/nine_site_owner_paths_20261030.json"
LANE = ROOT / "evidence/ns_ratio1_experiment_20261030.json"
NINE_DIR = ROOT / "data/research/nine_site_verify"
TEMPLATE = ROOT / "data/bridge/sample_submission.tif"
LABELS = ROOT / "data/bridge/labels.tif"
LATTICE = ROOT / "inputs/calibration/13gems_20261001_r13-lattice-s5_v2_nan-outside.tif"
OUT_HTML = ROOT / "docs/submission-start-here.html"
OUT_B2 = ROOT / "evidence/b2_subset_forensics_20261030.json"
OUT_CARD = ROOT / "evidence/ns_ratio1_run_card_20261030.json"

NOTE = "GEMS24 NS-RATIO1 label-free ratio-rule 37654d | id b49138fa | HOLDOUT-DTI 0.1294 | research; NO SUBMIT"
assert len(NOTE) <= 140, len(NOTE)


def footprint_and_labels():
    with rasterio.open(TEMPLATE) as t:
        fp = np.isfinite(t.read(1))
    with rasterio.open(LABELS) as s:
        labels = (s.read(1) == 1) & fp
    return fp, labels


def dots_of(path: Path, fp: np.ndarray) -> np.ndarray:
    with rasterio.open(path) as s:
        a = s.read(1)
    return np.isfinite(a) & (a > 0) & fp


def phi(a, b, fp) -> float:
    x = a[fp].astype(np.float64)
    y = b[fp].astype(np.float64)
    if x.std() == 0 or y.std() == 0:
        return float("nan")
    return float(np.corrcoef(x, y)[0, 1])


def b2_forensics(fp, labels):
    b2 = dots_of(NINE_DIR / "GEMSDOE32.tif", fp)
    d28 = dots_of(NINE_DIR / "GEMSDOE25.tif", fp)
    d30 = dots_of(NINE_DIR / "GEMSDOE30.tif", fp)
    removed = d28 & ~b2
    added = b2 & ~d28
    dl = distance_transform_edt(~labels)
    return {
        "schema": "b2-subset-forensics-v1",
        "scope": "Exact set comparison of owner files; no score computed",
        "b2": {"site": "GEMSDOE32", "dots": int(b2.sum())},
        "d28": {"site": "GEMSDOE25", "dots": int(d28.sum())},
        "gemsdoe30": {
            "dots": int(d30.sum()),
            "dotset_identical_to_gemsdoe25": bool((d30 == d28).all()),
        },
        "b2_is_subset_of_d28": bool(added.sum() == 0),
        "dots_removed_from_d28": int(removed.sum()),
        "dots_added_in_b2": int(added.sum()),
        "removed_dots_distance_to_catalogue_px": {
            "exactly_on_catalogue": int((removed & labels).sum()),
            "within_1_to_3_px": int((removed & (dl <= 3) & ~labels).sum()),
            "beyond_3_px": int((removed & (dl > 3)).sum()),
        },
        "share_of_dots_within_3px_of_catalogue": {
            "d28": round(float(((d28 & (dl <= 3)).sum()) / max(int(d28.sum()), 1)), 6),
            "b2": round(float(((b2 & (dl <= 3)).sum()) / max(int(b2.sum()), 1)), 6),
        },
        "owner_reported_scores_not_organizer_confirmed": {
            "GEMSDOE25_d28": 0.2600,
            "GEMSDOE32_b2": 0.2778,
        },
        "interpretation": (
            "Set facts only: B2 = D2.8 minus the removed dots, all 1-3 px from the catalogue. "
            "Hidden-label credit of those dots is unknown, so causality is not established."
        ),
    }


def phi_stats(fp):
    cand = dots_of(DL / ZEROS, fp)
    best = ("", -9.0)
    for site in SITES:
        r = phi(cand, dots_of(NINE_DIR / f"{site}.tif", fp), fp)
        if r > best[1]:
            best = (site, r)
    return {"max_site": best[0], "max": best[1], "lattice": phi(cand, dots_of(LATTICE, fp), fp)}


def adjacency(fp, labels):
    cand = dots_of(DL / ZEROS, fp)
    dl = distance_transform_edt(~labels)
    n = int(cand.sum())
    return {
        "candidate_dots": n,
        "exactly_on_catalogue": int((cand & labels).sum()),
        "within_1_to_3_px_of_catalogue": int((cand & (dl <= 3) & ~labels).sum()),
        "share_within_3px_of_catalogue": round(float(((cand & (dl <= 3)).sum()) / max(n, 1)), 6),
        "note": "Catalogue-adjacency pruning (the GEMSDOE32 B2 pattern) is untested on this candidate; not applied.",
    }


def pill(ok, text):
    cls = "ok" if ok is True else ("bad" if ok is False else "na")
    return f'<span class="pill {cls}">{html.escape(text)}</span>'


def load_inputs():
    lane = json.loads(LANE.read_text())
    nine = json.loads(NINE.read_text())
    paths = json.loads(PATHS.read_text())
    rz = json.loads((ROOT / f"evidence/candidate_verify_{STEM}-zeros.json").read_text())
    rn = json.loads((ROOT / f"evidence/candidate_verify_{STEM}-nan.json").read_text())
    return lane, nine, paths, rz, rn


def run_card(lane, rz, rn, phis, adj):
    e2 = next(e for e in lane["experiments"] if e["experiment"] == "E2_LABELFREE")
    e3 = next(e for e in lane["experiments"] if e["experiment"] == "E3_PROXIMITY")
    fmt = rn["format"]
    return {
        "schema": "run-card-v1",
        "lane": "NS-RATIO1",
        "session": "arena/025f58cb-gemsdoe24 (2026-10-30)",
        "hypothesis": (
            "Label-free GeoDAWN radiometric (K, Th, U, TC), magnetic-extension (ThK, UK, UTh, TMI_up150) "
            "and 1 m LiDAR scarp channels, trained on visible catalogue positives and placed by a "
            "credit-to-penalty ratio rule with 3 px spacing, recover withheld whole catalogue segments "
            "better than catalogue proximity alone (E3 control)."
        ),
        "mechanism": (
            "Official DTI with alpha=0.2, beta=0.8: DTI = TP/(0.8N + 0.2(TP+FP)). A dot is kept iff its "
            "expected credit-to-FP-weight ratio exceeds about 0.2*TP/(0.8N+0.2*FP). A calibrated P(fault) "
            "from relief, scarp and radiometric contrast supplies that ratio."
        ),
        "named_non_fault_mimic": (
            "Roads, tracks, channels, terrace risers, mines and claim disturbance create steps and relief "
            "(caveat in data/external/lidar_scarp_features.json); soil, lithology and wash drive radiometric contrast."
        ),
        "experiment_budget": (
            "Protocol budget: 3 experiments. Executed: run 1 (E1, E2, E3) and run 2 (E2, E3 re-run after a "
            "selection fix). Five experiment evaluations in total; over budget by two; disclosed."
        ),
        "experiments": {
            "E1_FULL_catalogue_distance": "VOID: catalogue distance is exactly 0 on training positives (leakage by construction). Not evidence.",
            "E2_LABELFREE": {
                "label": "HOLDOUT-DTI",
                "holdout_dti": e2["dti"],
                "ci95": e2["ci95"],
                "evaluator_version": e2["evaluator_version"],
                "withheld_positive_pixels": e2["n_withheld_positive_pixels"],
                "folds": e2["folds"],
                "ci_method": e2["ci_method"],
            },
            "E3_PROXIMITY_control": {
                "label": "HOLDOUT-DTI",
                "holdout_dti": e3["dti"],
                "ci95": e3["ci95"],
                "evaluator_version": e3["evaluator_version"],
                "withheld_positive_pixels": e3["n_withheld_positive_pixels"],
                "leakage_canary": "NOT COMPUTED for E3 (gap; a proximity-only control has no label-free feature set to test)",
            },
        },
        "leakage_canary": {
            "rule": "single-feature AUC on withheld quadrant; > 0.90 = leakage until proven otherwise",
            "experiment": "E2_LABELFREE",
            "worst_feature": e2["leakage_canary"]["worst_feature"],
            "worst_auc": e2["leakage_canary"]["worst_auc"],
            "pass": e2["leakage_canary"]["pass"],
        },
        "correlation_overlap_vs_registry": {
            "phi_max_vs_nine": {"site": phis["max_site"], "phi": round(phis["max"], 6)},
            "phi_vs_peer_lattice_GEMSDOE13": round(phis["lattice"], 6),
            "note_phi": "Protocol rank correlation; for binary rasters Spearman equals Pearson (phi), computed on the footprint. Threshold 0.90.",
            "overlap_3px_max_vs_nine": rz["overlap_3px_max_vs_nine"],
            "overlap_3px_max_vs_other_local_tifs": rz["overlap_3px_max_vs_other_local_tifs"],
            "overlap_3px_vs_peer_lattice_GEMSDOE13": rz["overlap_3px_vs_peer_lattice_GEMSDOE13"],
            "surface_before_placement": "NOT RUN (the pre-placement posterior surface was not saved; protocol requires this check)",
            "protocol_70pct_rule": "FAILS against the GEMSDOE13 lattice by construction (see the feasibility check)",
        },
        "rasters": {
            "zeros_outside": {
                "path": f"docs/downloads/{ZEROS}",
                "sha256": rz["sha256"],
                "bytes": rz["bytes"],
            },
            "nan_outside": {
                "path": f"docs/downloads/{NAN}",
                "sha256": rn["sha256"],
                "bytes": rn["bytes"],
                "note": "same dots as zeros variant; sibling overlap 1.0 so it fails the uniqueness gate against its twin: only ONE of the two may be uploaded",
            },
            "emitted_path_recorded_by_lane_receipt": lane["emitted"]["path"],
            "emitted_path_note": "the lane receipt records the pre-rename name; the file on disk was renamed to include the sha prefix after emission (not reproducible by the script alone); sha256 verified by verify_candidate_tif.py",
        },
        "validator_output_nan_outside": {
            "crs": fmt["crs"],
            "shape": fmt["shape"],
            "transform": fmt["transform"],
            "dtype": fmt["dtype"],
            "count": fmt["count"],
            "nan_inside_footprint": fmt["nan_inside_footprint"],
            "finite_outside_footprint": fmt["finite_outside_footprint"],
            "min_finite": fmt["min_finite"],
            "max_finite": fmt["max_finite"],
            "values_in_0_1": fmt["values_in_0_1"],
            "binary_values": fmt["binary_values"],
            "official_format_pass": fmt["official_format_pass"],
            "gates": rn["gates"],
            "all_gates_pass": rn["all_gates_pass"],
        },
        "catalogue_adjacency": adj,
        "submission": {"name": NAN, "note": NOTE, "note_chars": len(NOTE)},
        "estimated_leaderboard_score": "NOT ESTIMABLE (HOLDOUT-DTI is a proxy; no organizer receipt exists)",
        "hypotheses_ranked_not_yet_tried": [
            "H1 catalogue-adjacency pruning on the candidate (B2 pattern) as E4 on the same holdout; needs owner approval (budget)",
            "H2 cross-fitted catalogue-distance features (inner split of visible components) to make a valid E1; needs owner approval",
            "H3 radiometric/magnetic-only ablation (drop LiDAR channels) against E3; needs owner approval",
            "H4 nested-selected stopping rule for the dot budget instead of the fixed 37,654; holdout-overfit risk; needs owner approval",
        ],
        "verdict": "negative",
        "verdict_reason": (
            "DOWNLOAD: YES (format and audit). SUBMIT: NO until the owner decides whether the GEMSDOE13 "
            "calibration lattice is a registry comparator. Under the 70% rule no file above 22,163 dots can "
            "pass it. HOLDOUT-DTI 0.1294 is below the repo's recorded local point-best 0.166060 (H24-S3DEP1, "
            "non-unique, DO_NOT_SUBMIT). No promotion."
        ),
    }


def build_html(nine, paths, lane, rz, rn, b2, card, adj):
    e2 = next(e for e in lane["experiments"] if e["experiment"] == "E2_LABELFREE")
    e3 = next(e for e in lane["experiments"] if e["experiment"] == "E3_PROXIMITY")
    g = rn["gates"]
    ci = e2["ci95"]
    owner = nine["owner_reported_scores_not_organizer_confirmed"]
    rows = []
    for site in SITES:
        r = nine["files"][site]
        mp = nine["max_pairwise_overlap"][site]
        p = paths["sites"][site]
        url = p["url"]
        repo_path = p["repo_paths_with_identical_bytes"][0]
        unique = mp["max_overlap"] < 0.70
        rows.append(
            "<tr>"
            f"<td><strong>{site}</strong></td>"
            f'<td><a href="{url}">{html.escape(repo_path.split("/")[-1])}</a><br>'
            f"<small>bytes identical to owner repo · sha256 {r['sha256'][:12]}… · {r['dot_count']:,} dots · format {'PASS' if r['official_format_pass'] else 'FAIL'}</small></td>"
            f"<td>{owner[site]:.4f}<br><small>OWNER-REPORTED (not organizer-confirmed)</small></td>"
            "<td>NOT ESTIMABLE</td>"
            f"<td>{pill(unique, 'UNIQUE' if unique else 'NOT UNIQUE')}<br>"
            f"<small>max 3-px overlap {mp['max_overlap'] * 100:.2f}% with {mp['max_overlap_vs']}</small></td>"
            f"<td>{pill(False, 'DO NOT SUBMIT')}<br><small>audit download only; already scored (owner report)</small></td>"
            "</tr>"
        )
    fmt = rn["format"]
    lattice = rz["overlap_3px_vs_peer_lattice_GEMSDOE13"]
    nine_top = rz["overlap_3px_max_vs_nine"]
    other_top = rz["overlap_3px_max_vs_other_local_tifs"]
    s3 = b2["share_of_dots_within_3px_of_catalogue"]
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Submission start here · GEMS DOE 24 (2026-10-30)</title>
<style>
body{{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;line-height:1.45;color:#111827;margin:0;background:#fff}}
main{{max-width:1100px;margin:0 auto;padding:18px}}
.box{{border:2px solid #1d4ed8;border-radius:10px;padding:14px 18px;margin:14px 0;background:#f8fbff}}
.pill{{display:inline-block;border-radius:999px;padding:2px 10px;margin:2px 4px 2px 0;font-size:.85em;font-weight:600}}
.pill.ok{{background:#dcfce7;color:#14532d}} .pill.bad{{background:#fee2e2;color:#7f1d1d}} .pill.na{{background:#e5e7eb;color:#111827}}
table{{border-collapse:collapse;width:100%;margin:10px 0}} th,td{{border:1px solid #cbd5e1;padding:6px 8px;vertical-align:top;text-align:left}}
th{{background:#eef2ff}} code{{word-break:break-all}} small{{color:#374151}}
</style></head>
<body><main>
<h1>Submission start here · GEMS DOE 24</h1>
<p><strong>Maximize P(Win). Own the Outcome.</strong> Generated 2026-10-30 by <code>scripts/build_submission_start_here.py</code> from the receipts in <code>evidence/</code>. Every number carries a label: <em>OWNER-REPORTED</em> (copied from the request or the repo README), <em>HOLDOUT-DTI</em> (our internal proxy, with evaluator version, withheld count and 95% CI), or <em>format/geometry check</em>. No organizer score exists in this repository.</p>

<div class="box">
<h2>1 · The file: download yes, submit no</h2>
<p><strong>Recommended upload variant (if the owner clears submission):</strong>
<a href="downloads/{NAN}" download><strong>⬇ {NAN}</strong></a><br>
<code>sha256 {rn["sha256"]}</code> · {rn["dot_count_in_footprint"]:,} binary dots · float32 · EPSG:32611 · 100 m · 3730×3292 · NaN outside the footprint (same convention as the bridge sample)</p>
<p>Audit copy, do not upload both: <a href="downloads/{ZEROS}" download>{ZEROS}</a> (identical dots, finite 0.0 outside; sha256 <code>{rz["sha256"][:16]}…</code>).</p>
<p>
{pill(True, "DOWNLOAD: YES (format and audit)")}
{pill(False, "SUBMIT: NO (owner decision pending)")}
</p>
<p>
{pill(fmt["official_format_pass"], "Official format PASS (NaN outside)")}
{pill(g["no_exact_duplicate"], "No exact duplicate")}
{pill(g["overlap_le_70pct_vs_nine"], f"Unique vs nine: max {nine_top['fraction'] * 100:.2f}% (GEMSDOE27)")}
{pill(g["overlap_le_70pct_vs_all_other_local_tifs"], f"Unique vs other local TIFs: max {other_top['fraction'] * 100:.2f}% (zeros sibling 100%)")}
{pill(g["overlap_le_70pct_vs_peer_lattice_GEMSDOE13"], f"GEMSDOE13 lattice: {lattice * 100:.2f}% · FAIL by construction")}
{pill(None, "Estimated leaderboard score: NOT ESTIMABLE")}
</p>
<p><strong>Why submit is not cleared.</strong> The protocol's 70% test counts the GEMSDOE13 calibration lattice (<code>13gems_20261001_r13-lattice-s5_v2_nan-outside.tif</code>) as a registry comparator. Its 5-px grid covers 99.87% of the footprint, so no dot file above 22,163 dots can pass that test. This is arithmetic, not a defect in this file. <strong>Decision for the owner:</strong> does the GEMSDOE13 lattice count as a registry comparator? If not, every gate that remains passes and the owner may submit this file. If yes, the protocol itself must change before any dot file at this budget can clear it.</p>
<p><strong>Portal error "Predicted values must be in range [0, 1]".</strong> This file's finite values are all 0 or 1, and it has no NaN inside the footprint. The cause of the earlier rejection is not established. Locally, none of the nine owner files holds an out-of-range finite value (<code>evidence/nine_site_verify_20261030.json</code>). The file the portal rejected is not identified, so send its exact filename to resolve this.</p>
</div>

<h2>2 · How to submit (the one manual step)</h2>
<ol>
<li>Download the <code>-nan</code> file above and confirm its sha256 prefix <code>{rn["sha256"][:8]}</code>.</li>
<li>Only after the owner decision in section 1: log in to DrivenData and submit that single <code>.tif</code>. Only you can do this step; no credentials are used or stored here.</li>
<li>Paste this note ({len(NOTE)} of 140 characters): <code>{html.escape(NOTE)}</code></li>
<li>Remember the weekly cap of three submissions (official rules §3.2). This repository cannot see the remaining quota.</li>
</ol>

<h2>3 · Nine focus sites: best file, estimate, uniqueness</h2>
<p>Each file below is the owner's named best file, located by byte identity (git blob SHA-1) in the owner's public repo. <strong>Unique vs the other focus sites?</strong> compares each file's dots with every other focus file (3-px rule). Every site overlaps another at 97.5% or more, so none is unique.</p>
<table>
<tr><th>Site</th><th>File to download</th><th>Owner-reported score</th><th>Estimated leaderboard score</th><th>Unique vs the other focus sites?</th><th>Submit?</th></tr>
{"".join(rows)}
</table>
<p><small>Official leaderboard snapshot (DrivenData, fetched 2026-10-30): #1 0.4544, #2 0.3925, #3 0.3915, #10 0.3520. Neither 0.4413 nor 0.3195 appears in its visible rows (#1–#23). The request cites 0.4413 and 0.3195, so both remain unverified.</small></p>

<h2>4 · Why H33-B2 (GEMSDOE32, 0.2778) scored high — evidence-bounded</h2>
<ol>
<li><strong>Arithmetic (from the official definition, as implemented in <code>src/gems/metric.py</code>).</strong> With FN_w = N − TP_w, DTI = TP_w / (0.8·N + 0.2·(TP_w + FP_w)). Removing a dot raises the score only if its credit-to-FP-weight ratio is below roughly 0.2·TP/(0.8N + 0.2·FP).</li>
<li><strong>Verified set fact.</strong> B2 has {b2["b2"]["dots"]:,} dots and is an exact subset of the {b2["d28"]["dots"]:,}-dot GEMSDOE25 D2.8 file. The {b2["dots_removed_from_d28"]:,} removed dots are all 1–3 px from the catalogue, and none sits on it. B2 keeps {s3["b2"] * 100:.1f}% of its dots within 3 px of the catalogue; D2.8 has {s3["d28"] * 100:.1f}% (<code>evidence/b2_subset_forensics_20261030.json</code>).</li>
<li><strong>Mechanism (plausible, not proven).</strong> The competition's labels are new faults, so a dot hugging an already-mapped trace plausibly earns little credit yet carries a full penalty. Pruning such dots lowers FP mass with little TP loss. Owner-reported scores move from 0.2600 (D2.8) to 0.2778 (B2), a +0.0178 difference. The repo's own analysis (<code>README.md</code>, H33-B2 section) also says the pruning can hurt when removed cells sit near withheld faults. Hidden credit and the hidden N are unavailable, so causality is not established.</li>
<li><strong>Can we beat 0.2778?</strong> Not demonstrated. The label-free candidate's HOLDOUT-DTI is {e2["dti"]:.4f} (95% CI [{ci[0]:.4f}, {ci[1]:.4f}], {e2["n_withheld_positive_pixels"]:,} withheld positives, evaluator {html.escape(e2["evaluator_version"])}). That is below the repo's recorded local point-best of 0.166060 (H24-S3DEP1, a non-unique file, DO_NOT_SUBMIT; <code>docs/data/current_best_review.json</code>). Proxy DTI values are not leaderboard scores, and the candidate's own catalogue-adjacent share is {adj["share_within_3px_of_catalogue"] * 100:.1f}%, against B2's {s3["b2"] * 100:.1f}%.</li>
</ol>

<h2>5 · Candidate validation (receipts)</h2>
<table>
<tr><th>Item</th><th>Result</th><th>Label</th></tr>
<tr><td>Holdout: whole catalogue segments withheld in four quadrants with a 30 px buffer; pooled DTI (α=0.2, β=0.8, 300 m triangular kernel)</td><td>{e2["dti"]:.6f} [{ci[0]:.6f}, {ci[1]:.6f}] · evaluator {html.escape(e2["evaluator_version"])} · {e2["n_withheld_positive_pixels"]:,} withheld</td><td>HOLDOUT-DTI</td></tr>
<tr><td>Control: proximity-only (E3)</td><td>{e3["dti"]:.6f} [{e3["ci95"][0]:.6f}, {e3["ci95"][1]:.6f}] · {e3["n_withheld_positive_pixels"]:,} withheld</td><td>HOLDOUT-DTI</td></tr>
<tr><td>Leakage canary (E2 only; single-feature AUC, pass ≤ 0.90)</td><td>worst {e2["leakage_canary"]["worst_auc"]} ({html.escape(e2["leakage_canary"]["worst_feature"])}) · PASS. E3 has no canary entry (gap).</td><td>canary</td></tr>
<tr><td>Official format (EPSG:32611, 3730×3292, float32, values in [0,1], no NaN inside footprint)</td><td>PASS (NaN-outside variant)</td><td>format check</td></tr>
<tr><td>Byte identity vs all local TIFFs and the nine files</td><td>No exact duplicate. The zeros and NaN variants are twins of each other (overlap 100%).</td><td>sha256</td></tr>
<tr><td>Phi / Spearman correlation vs nine (max)</td><td>{card["correlation_overlap_vs_registry"]["phi_max_vs_nine"]["phi"]:.4f} ({html.escape(card["correlation_overlap_vs_registry"]["phi_max_vs_nine"]["site"])}); threshold 0.90 not exceeded</td><td>registry check</td></tr>
<tr><td>Surface before placement (protocol)</td><td>NOT RUN (pre-placement posterior not saved)</td><td>gap</td></tr>
<tr><td>Catalogue-adjacent dots (within 3 px of the catalogue)</td><td>{adj["share_within_3px_of_catalogue"] * 100:.1f}%, untested pruning lever (H1)</td><td>diagnostic</td></tr>
</table>
<p><small>Budget: the protocol allows three experiments. Run 1 executed E1, E2 and E3; run 2 re-ran E2 and E3 after a selection fix. That is five evaluations, which is over budget and disclosed. E1 is void and is not evidence.</small></p>

<h2>6 · Ranked hypotheses not yet tried (none run; each needs owner approval)</h2>
<ol>
<li><strong>H1 · Catalogue-adjacency pruning (rank 1).</strong> Drop candidate dots within 1–3 px of visible catalogue faults and refill the budget with the next-best eligible dots at ≥3 px spacing. Test as E4 on the same holdout. Expected sign (not a score): if the removed dots carry low credit, proxy DTI rises. Kill rule: proxy DTI falls or its CI falls below E2's. It is the only lever the verified B2 evidence points to.</li>
<li><strong>H2 · Cross-fitted catalogue-distance features (rank 2).</strong> Build the distance features from an inner split of the visible components so they are out-of-fold. This is the only valid route to the run-1 idea. Kill rule: canary above 0.90, or the AUC gain does not reproduce out-of-fold.</li>
<li><strong>H3 · Radiometric and magnetic ablation (rank 3).</strong> Drop the LiDAR channels and test whether the label-free radiometric stack alone beats E3. Kill rule: E3 at least matches the ablation.</li>
<li><strong>H4 · Nested dot-budget selection (rank 4).</strong> Choose the stopping point by nested selection, not the fixed 37,654. Holdout-overfit risk is high, so it ranks last.</li>
</ol>

<h2>7 · Irregularities flagged for review</h2>
<ol>
<li><strong>Leaderboard figures conflict.</strong> The request cites 0.4413 and 0.3195 as current highs. The official snapshot's visible rows (#1–#23) show neither. Source: <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">DrivenData leaderboard</a>.</li>
<li><strong>Bridge sample is not the official sample.</strong> <code>data/bridge/sample_submission.tif</code> holds exactly the 60,988 catalogue positives. The official page says the sample "predicts total fault absence" (<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">problem page</a>).</li>
<li><strong>Bridge labels mirror the catalogue.</strong> <code>data/bridge/labels.tif</code> is byte-identical to <code>existing_faults.tif</code> (sha256 7ba308cc…). These are the public catalogue, not the organizer's hidden labels.</li>
<li><strong>Cross-site duplicate.</strong> The GEMSDOE25 D2.8 file (sha256 91eae1ca…) is byte-identical to <code>docs/downloads/gems24-h25-1-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif</code> in this repository.</li>
<li><strong>Dot-set duplicate across sites.</strong> GEMSDOE30's file bytes differ from GEMSDOE25's (different sha256), but its dot set is identical to GEMSDOE25's (44,090 dots, checked cell by cell; <code>evidence/b2_subset_forensics_20261030.json</code>). The two owner files are the same submission in different encodings.</li>
<li><strong>GEMSDOE32 B2 is a subset, not a discovery.</strong> It is an exact subset of GEMSDOE25 D2.8, so its uniqueness against that file is zero by construction.</li>
<li><strong>Range error cause unknown.</strong> No owner file holds an out-of-range finite value. The uploaded filename is needed.</li>
<li><strong>The 70% rule is structurally blocked</strong> by the GEMSDOE13 lattice (99.87% footprint coverage). Owner decision required.</li>
<li><strong>Feature stack absent.</strong> <code>data/training_features.tif</code> (about 419 MB, the organizer training raster) is in neither this checkout nor its git history. The peer-level lanes cannot be reproduced here.</li>
<li><strong>Owner-reported scores are unverified.</strong> There is no organizer receipt for any file. The leaderboard was checked only in its visible rows.</li>
<li><strong>Our own errors.</strong> Run 1's selection cap under-filled budgets (fixed in run 2). E1 is void. E3 has no canary. The surface-before-placement check was not run. The lane receipt's <code>emitted.path</code> records a name that was renamed after emission.</li>
<li><strong>Two variants of one submission.</strong> The zeros and NaN files hold identical dots; uploading both would be a duplicate.</li>
</ol>

<h2>8 · Sources (official or verifiable)</h2>
<ul>
<li>Problem, metric (α=0.2, β=0.8, 300 m triangular kernel) and submission format: <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">DrivenData problem page</a></li>
<li>Official rules: <a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">NLR GEMS Prize Official Rules (PDF, Sept 2026)</a>: §3.2 three submissions per week; §3.4–3.5 one final submission</li>
<li>Leaderboard: <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">DrivenData leaderboard snapshot</a></li>
<li>Grid: <a href="https://epsg.io/32611">EPSG:32611</a> (UTM 11N). Data DOIs as recorded in this repo's provenance files (not re-fetched this session): GeoDAWN <a href="https://doi.org/10.5066/P93LGLVQ">10.5066/P93LGLVQ</a> and INGENIOUS <a href="https://doi.org/10.15121/1881483">10.15121/1881483</a> (<code>data/external/geodawn_rad.json</code>).</li>
<li>Nine focus repositories (owner files, public GitHub):
{" · ".join(f'<a href="https://github.com/buffedlizard55-lab/{s}">{s}</a>' for s in SITES)}</li>
<li>Exact owner file links: <code>evidence/nine_site_owner_paths_20261030.json</code></li>
</ul>

<h2>9 · Reproduce</h2>
<pre><code>.venv/bin/python scripts/nine_site_verify.py
.venv/bin/python scripts/map_nine_owner_paths.py
.venv/bin/python scripts/run_ns_ratio1_lane.py --emit docs/downloads/{STEM}-zeros.tif   # holdout E2,E3 + candidate (re-runs holdout)
.venv/bin/python scripts/verify_candidate_tif.py docs/downloads/{ZEROS}
.venv/bin/python scripts/make_nan_twin.py
.venv/bin/python scripts/build_submission_start_here.py</code></pre>
<p>Core values: <strong>Maximize P(Win)</strong> and <strong>Own the Outcome</strong>. Mission prompt: <a href="MISSION_PROMPT.md">MISSION_PROMPT.md</a> · Standing instructions: <a href="../AGENTS.md">AGENTS.md</a> · README: <a href="../README.md">README.md</a>.</p>
</main></body></html>
"""


def main() -> int:
    fp, labels = footprint_and_labels()
    lane, nine, paths, rz, rn = load_inputs()
    b2 = b2_forensics(fp, labels)
    phis = phi_stats(fp)
    adj = adjacency(fp, labels)
    card = run_card(lane, rz, rn, phis, adj)
    # phi values are written into the run card, not hard-coded into the page
    html_doc = build_html(nine, paths, lane, rz, rn, b2, card, adj)
    OUT_B2.write_text(json.dumps(b2, indent=2, allow_nan=False) + "\n")
    OUT_CARD.write_text(json.dumps(card, indent=2, allow_nan=False) + "\n")
    OUT_HTML.write_text(html_doc)
    print("wrote", OUT_HTML.relative_to(ROOT), OUT_B2.relative_to(ROOT), OUT_CARD.relative_to(ROOT))
    print(
        "B2 subset:",
        b2["b2_is_subset_of_d28"],
        "removed:",
        b2["dots_removed_from_d28"],
        "GEMSDOE30 dotset == GEMSDOE25:",
        b2["gemsdoe30"]["dotset_identical_to_gemsdoe25"],
    )
    print(
        "phi max vs nine:",
        round(phis["max"], 4),
        phis["max_site"],
        "lattice phi:",
        round(phis["lattice"], 4),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
