# GEMS DOE 24 — evidence before a leaderboard slot

**Goal: maximize the chance of winning DOE GEMS / DrivenData #306 through sound
geological inference, reproducible experiments and honest validation.** A goal
is not a score forecast or a guarantee of winning.

> **Maximize P(Win).** Prefer verified scientific leverage over cosmetic model
> changes, submission fishing or comfortable busywork.
>
> **Own the Outcome.** Resolve data placement and engineering blockers
> autonomously; report negative results and genuine remaining constraints rather
> than passing an unavailable source off as a completed experiment.

**Start here every session, in this order:** (1) this README — status, charter and
the owner's brief at the bottom; (2) [`knowledge/owner_brief_verbatim.md`](knowledge/owner_brief_verbatim.md);
(3) [`AGENTS.md`](AGENTS.md) (and [`AI_DISCLOSURE.md`](AI_DISCLOSURE.md) for the prize narrative); (4) `git fetch origin`, compare with the session branch, **and list open PRs / `arena/*` branches** (`gh pr list --state open`) — a sibling session may be working from the same base (see [`knowledge/08_parallel_session_pr7_2026-10-02.md`](knowledge/08_parallel_session_pr7_2026-10-02.md));
(5) [`knowledge/06_synthesis_2026-10-02_session2.md`](knowledge/06_synthesis_2026-10-02_session2.md) and
[`knowledge/05_findings_and_hypotheses_2026-10-02.md`](knowledge/05_findings_and_hypotheses_2026-10-02.md);
(6) `python -m pytest -q`.

[Live site](https://buffedlizard55-lab.github.io/GEMSDOE24/) ·
[Submission guide](https://buffedlizard55-lab.github.io/GEMSDOE24/docs/executive-summary.html) ·
[Research synthesis](knowledge/06_synthesis_2026-10-02_session2.md) ·
[Emission preregistration](knowledge/04_preregistered_emission_2026-10-02.md) ·
[Dotting preregistration](knowledge/04_preregistered_dotting_2026-10-02.md) ·
[Source review](knowledge/03_verified_sources_2026-10-02.md)


## Follow-up release review (2026-10-25)

**Still NOT OK TO SUBMIT.** The unique ASPC research TIFF below has now been
reopened and revalidated independently of its stored format receipts. Site builds
fail closed if bytes, validator receipts, run card or authorization flags disagree.
This is verification of the frozen result, **not a new geological experiment**.
See the [three-pass review and prioritized next steps](knowledge/11_release_review_2026-10-25.md)
and [fresh exact-file audit](evidence/release_revalidation_20261025.json).

```bash
python -m pip install -e '.[dev]'
python scripts/verify_research_release.py  # offline; does not rerun confirmation folds
python -m pytest -q
```

## Current reproducibility entry point (2026-10-25)

```bash
.venv/bin/python scripts/review_peer_registry.py
# run_aspc_lane.py is frozen and refuses to overwrite its recorded experiment.
.venv/bin/python scripts/package_aspc_companion.py  # same predictions, template NaN convention
.venv/bin/python scripts/build_site.py
.venv/bin/python -m pytest -q
```

The shared evaluator correction is in `src/gems/holdout.py`; no private evaluator
or writer was introduced. Historical fold-averaged/postprocessed DTI is not the
new pooled hide-and-recover benchmark. Full input/factor AUC tests and exact-file
checks are in the JSON run card. The scientific comparison is favorable against
a fixed scarp control but **not certified against the current best**.

## Active owner prompt — read before every session

The [2026-10-25 owner requirements](knowledge/owner_brief_2026-10-25.md) supersede
historical promotion recommendations below. They are reproduced in the current-brief
appendix (repetitions consolidated, not a verbatim chat transcript). Read them with
[the ASPC findings](knowledge/10_ASPC_findings_2026-10-25.md). **No file is authorized
merely because it passes format checks.**

## Current decision

<!-- STATUS:START -->
**NOT OK TO SUBMIT.** ASPC has a negative promotion verdict, not a leaderboard result.

Unique [research TIFF](docs/downloads/gems24-aspc-20261025-6393e9d9b0df-RESEARCH-NOT-SUBMISSION-zeros.tif) — format-valid, do not upload.
[Run card](evidence/aspc_run_card_20261025.json) · [Executive guide](docs/executive-summary.html) · [Preregistered hypotheses](knowledge/09_preregistered_ASPC_2026-10-25.md).

No weekly slot has been spent. No organizer-confirmed score, current-best OOF certification,
assigned parallel lane or selector authorization. Historical results below are not current promotion authority.

**HOLDOUT-DTI** (segment-hide-recover-pooled-v1, 60,988 withheld positives):
0.08553, 95% CI [0.07440, 0.09648].
Fixed scarp control 0.06836; paired Δ +0.01717,
95% CI [+0.00897, +0.02466]. These are not leaderboard scores.
<!-- STATUS:END -->

## Standing session charter — read this at the start of every session

This section preserves **all active requirements available in the session
context**, including corrections and scope decisions. The owner's brief itself is
reproduced **verbatim at the bottom of this file** and in
[`knowledge/owner_brief_verbatim.md`](knowledge/owner_brief_verbatim.md) (see that
file's provenance note: the 24GEMSDOE-specific opening is the wording preserved by
earlier sessions; the shared brief is the owner's text as stored by sibling session
22GEMSDOE).

1. Review this repository and the group's websites/source code; resume genuine
   next steps from earlier sessions before proposing duplicate work. Work
   autonomously without asking for data placement, feature preparation or
   routine design decisions. Download/restore into `data/`, prepare, train,
   predict and validate as far as verified inputs and permissions permit.
2. Aim to finish at the top of the leaderboard using PhD-level scientific
   judgment. Verify factual assertions against **official, trusted sources**,
   link them for manual review, collect auditable data/source/knowledge tables
   for subsequent projects, and flag irregularities. Never fabricate scores,
   access, causal discovery, source availability or completion.
3. Study why H19-4 and H19-5 are the group's highest **owner-reported** results:
   `gems19-h19-4-multi-line-physical-corroboration-20261001-691e4dfa-nan`
   **0.1894**, and
   `gems19-h19-5-openness-thermal-corroboration-20261001-e27054cf-nan`
   **0.1922**. H19-5 already exceeds 0.1894. The owner's leader snapshot 0.3049
   and the inherited site snapshot 0.3168 are historical, not current facts.
   Do not infer the score of a particular file from a public account's score
   without an artifact-linked organizer receipt.
4. Before implementing a new detector, write **3–5 genuinely unimplemented
   hypotheses relative to the reviewed work**. Each must name the precise
   layers, physical transform/signature, missing-fault rationale, distinction
   from reviewed methods, expected DTI benefit and implementation cost. Rank
   them. If external data are needed, name a free official source and verify
   practical availability; otherwise explicitly defer that hypothesis. Novelty
   is not a claim about unseen competitors' work.
5. Run a classifier two-sample audit motivated by **Lopez-Paz & Oquab, ICLR
   2017**. Distinguish pixels near mapped faults from far pixels using **only**
   road/trail distance, historic mining-claim distance and categorical membership
   of the **four GeoDAWN operational acquisition blocks**. No geothermal wells,
   sinter, vents, probes, mineral-occurrence substitutions, fault-distance
   features, mapped-fault confidence, or label-derived seams may enter this
   nuisance-only test.
6. Audit **training labels first**, then each relevant prediction raster, and
   the **exact final candidate** before any slot. Refit classifiers for null
   replicates and use spatial separation, effect-size safeguards and declared
   multiplicity control. If meaningful association appears, remove/residualize
   measured confounds on **training-region pixels only**, refit the detector and
   re-evaluate. A spatial holdout from the same catalogue is not sufficient by
   itself to certify robustness to the mapping process.
7. Scientific correction to the owner's premise: C2ST detects **distributional
   association**, not its cause. Roads/claims can themselves correlate with
   geology; non-rejection does not prove absence of bias. This implementation
   explicitly adapts the paper's held-out accuracy statistic to a prespecified
   AUC with refitted spatial randomizations. Block exchangeability is assumed;
   torus shifts on a nonstationary, irregular footprint are sensitivity
   diagnostics, not an exact spatial null.
8. **Never spend a weekly slot unless the candidate beats the CURRENT comparable
   spatially blocked holdout best.** Validate the top hypothesis on the frozen
   protocol, require paired true retraining gains and the exact-raster bias
   audit, and never treat re-ranking an already-binary submission as retraining.
   Missing original H19 OOF reconstruction or a required source blocks
   certification; an arbitrary easier baseline is not enough. A label-free
   *subset* transform of an already-scored raster uses the separate post-process
   path (`gems.promotion.require_postprocess_evidence`): frozen paired gates plus
   exact-file audit; if only the strict accessibility gate fails and the file is no
   more associated than its reference, the result is `owner_decision_required` —
   the owner may accept a declared exception, recorded in `registry/submissions.json`.
9. Submission: a **single-band float32 GeoTIFF**, matching the template's CRS,
   shape and geotransform, with **finite [0,1] values inside** and NaN outside the
   official footprint. Fix the owner's rejection, “Predicted values must be in
   range [0, 1]”. Give every artifact a unique name/content identifier, an
   obvious **one-click `.tif` download at the beginning of the site**, a separate
   short submission comment and a dedicated executive-summary/instructions
   subpage. Format validity does not authorize a scientific promotion. A
   zeros-outside fallback is separately labelled, not silently substituted for
   the official NaN convention.
10. Clean up GitHub Pages and implement a timestamped automated source feed.
    Distinguish owner reports, team-authored claims, official snapshots, computed
    diagnostics and hypotheses. Unknown scores, including unreported 22/23
    results, remain unknown. Never republish a renamed reference as a new win.
11. Review in **three passes**: (i) implement and verify against sources;
    (ii) find and fix bugs, assumptions and edge cases;
    (iii) recheck this original acceptance scope, reliability and code. Keep the
    review record and limitations. Open a PR from the session branch and merge
    through GitHub if the configured connection permits it; never silently claim
    a merge or a public deployment that did not occur.
12. Arena's **Maximize P(Win)** and **Own the Outcome** remain focal. Follow the
    session's fixed Arena branch, never create/write an orphan data branch, never
    ask for GitHub credentials, and preserve large regenerable datasets outside
    Git. If GitHub authentication fails, the platform connection needs
    reconnection; this is not permission to forge a merge or bypass authentication.
13. **First command of every session: `git fetch origin` and compare
    `origin/<session branch>` with `HEAD`.** On 2026-10-02 the remote session
    branch already held 12 commits that the fresh checkout lacked; merge, never
    force-push.
14. Scores that appear only in the brief (H28 0.1839, lattice 0.0904, …) are
    unconfirmed (`registry/live_scores.json`, `task_statement_only`). The dense
    catalogue holdout is a different regime from the hidden set; judge emission
    policies on the density-matched sparse simulation first.

## Reproduce the active pipeline

Python 3.11; CPU-only (2 cores, 4 GB RAM are enough). Install the recorded versions:

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/pip install --no-deps -e .
.venv/bin/python -m pytest -q
.venv/bin/ruff check src scripts tests
```

Data placement is autonomous and hash-pinned (needs only GitHub access; the 419 MB raster
and 592 MiB matrix stay ignored):

```bash
.venv/bin/python scripts/restore_data.py --roads
.venv/bin/python scripts/prepare_data.py
.venv/bin/python scripts/build_confounds.py --force      # roads + claims + derived four blocks
```

The headline experiment (all frozen in `knowledge/04_preregistered_emission_2026-10-02.md`):

```bash
.venv/bin/python scripts/run_emission_experiment.py --draws 30   # lattice calibration, K-grid, h25->h28 check
.venv/bin/python scripts/run_operator_comparison.py              # equal-N head-to-head + frozen selection
.venv/bin/python scripts/make_dot_thinned_sources.py --spacing 1.5 --spacing 2.4
.venv/bin/python scripts/write_postprocess_validation.py
```

Exact-file classifier two-sample audit, labels first (≈13 min on 2 CPUs), then package through the
fail-closed post-process path and rebuild the site:

```bash
.venv/bin/python scripts/run_geology_audit.py --force \
  --candidate out/h25-1-dotthin-d1.5-h19-5.tif --candidate-alt out/h25-1-dotthin-d2.4-h19-5.tif
.venv/bin/python scripts/build_submission24.py out/h25-1-dotthin-d1.5-h19-5.tif --postprocess-of h19-5 \
  --validation evidence/h24_e1_validation_primary.json --spacing 1.5 --role primary --summary "<<=126 chars>>"
.venv/bin/python scripts/build_submission24.py out/h25-1-dotthin-d2.4-h19-5.tif --postprocess-of h19-5 \
  --validation evidence/dotting_validation.json --spacing 2.8 --candidate-label candidate_alt --role alternate \
  --summary "<<=126 chars>>"
.venv/bin/python scripts/build_site.py
```

The owner records a score read from the portal (never automated; DrivenData forbids bots):

```bash
.venv/bin/python scripts/record_live_score.py --file <downloaded-file-name-or-sha-prefix> --score 0.2xxx
```

`scripts/analyze_group_rasters.py --sibling-root <folder of shallow clones of the owner's repos>` regenerates the
format forensics and leaderboard-geometry evidence. The reference-only bypass (`--mirror-of h19-5`) still verifies the
full pinned H19-5 hash. Nothing in these commands uploads to DrivenData or spends a slot.

## What is verified, and what is not

- **Integrity:** the restored owner bridge is pinned to its original hashes (training raster `4371c82e…`, labels
  `7ba308cc…`, template `2176d08e…`). This proves mirror consistency, **not independent organizer authentication**. The
  owner's `sample_submission.tif`/`example_submission.tif` has 60,988 pixels equal to 1.0 exactly on the labelled fault
  pixels, whereas the organizers' page says the sample "predicts total fault absence" (staff said they may change the
  description) — it is used only as a grid/footprint template.
- **Calibration and emission (COMPUTED):** hidden truth density τ≈0.24 % of cells from the owner's blind-lattice score
  (brief-only, unconfirmed); dotted H19-5 candidates improve the density-matched sparse simulation by +36 % (primary) /
  +42 % (alternate) with a positive/slightly negative dense effect. The model score (≈0.25, plausible 0.22–0.28) is **not**
  a leaderboard result; on the one independent pair with known scores the harness under-predicted the live effect and its
  dense ratio had the wrong sign.
- **Format:** strict writer; none of 148 owner rasters has an in-footprint value outside [0,1]; the cause of the original
  portal message is **not established**.
- **Audit:** full required families (6 rasters, Holm over 6 tests). Labels AUC 0.496 (no association); H19-4/H19-5/candidates
  0.555–0.563 (flagged, mostly claim proximity; not robust to spatial shifts). **Residualizing** (H24-2A, refit on the corrected
  sources) brings the detector's raster to AUC 0.525 (not flagged) but costs 0.016 dense DTI and does not beat the raw physics
  baseline — the strict audit and the holdout pull in opposite directions. Four blocks are **derived from an official figure and
  audited against published line-km, not official coordinates** (they are latitude bands, so removing them also removes regional
  geology); roads are the official buffered Census run.
- **Not verified:** the hidden labels, the private leaderboard, any score for the new files, account↔artifact mapping, the
  portal's note-length limit, the competition's exact deadline convention, the official flight-number→block mapping.

## Evidence and repository map

| Path | Role |
|---|---|
| `src/gems/emission.py`, `emission_eval.py`, `thinning.py` | calibration, kernel-cover control, exact fast paired evaluator, deterministic `dot_thin` |
| `src/gems/` (other) | exact/binary DTI, ridge selection, descriptors, strict nuisance inputs, spatial C2ST, residualization, packaging, promotion |
| `scripts/run_emission_experiment.py`, `run_operator_comparison.py`, `run_dotting_validation.py` | frozen experiments (this session / earlier session) |
| `scripts/run_geology_audit.py`, `build_confounds.py`, `derive_acquisition_blocks.py` | labels-first audit, nuisance rasters, audited block derivation |
| `scripts/build_submission24.py`, `record_live_score.py`, `build_site.py` | fail-closed packaging, score ledger, site + README status |
| `scripts/analyze_group_rasters.py` | format forensics and score-vs-geometry analysis of the owner's rasters |
| `evidence/h24_e1_*.json`, `emission_calibration.json`, `dotting_validation.json` | all experiment receipts |
| `evidence/accessibility_audit_v2.json`, `access_inputs.json` | audit receipts and source provenance |
| `evidence/format_forensics.json`, `group_raster_profiles.csv`, `lb_geometry_analysis.json` | portal-error forensics, per-raster profiles, score geometry |
| `registry/live_scores.json`, `submissions.json`, `irregularities.json` | owner-reported scores (with confirmation level), packaged files, irregularities |
| `inputs/`, `inputs/calibration/` | pinned scored reference rasters; calibration rasters copied unchanged from the owner's repos |
| `data/external/audit_sources/` | official USGS documents/figure, buffered road raster + receipt, claim-distance bridge, derived block raster + receipt |
| `docs/` | Pages site, one-click download, executive guide, timestamped feed |
| `knowledge/` | brief, preregistrations, findings, verified sources, synthesis, parallel-session (PR #7) reconciliation |

## Publication and automation

- GitHub Pages is enabled for `main` and the live site is served at <https://buffedlizard55-lab.github.io/GEMSDOE24/>.
  `website.yml` rebuilds the site from `main` on every push and on a 6-hourly schedule (no scheduled run had been
  observed when this was written; only the push-triggered run). The feed is a timestamped snapshot, not a live API.
  **It never requests drivendata.org** (its Terms of Use forbid automatic access): the leaderboard/forum entries are
  human-read snapshots, and only the USGS ScienceBase API is checked automatically (`scripts/refresh_source_feed.py`).
- `official-inputs-ci.yml` runs the anonymous official-source derivations the sandbox cannot reach (Census, USGS) on any
  `arena/**` branch and commits only small derived files back to that branch.
- The agent never uploads to DrivenData and never requests credentials. Follow organizer limits (3 submissions/week, one final
  submission, AI disclosure in the narrative); confirm the rules/page deadline discrepancy with the organizers.

## Historical next actions (2026-10-02; superseded for slot decisions)

1. **Owner decision + upload (the only step that produces new information):** primary first, alternate in the same week if
   the exception is accepted; record both with `scripts/record_live_score.py`. Re-fit τ and the retention model from the two scores.
2. **Reconcile open PR #7** (a parallel session's H24-3A / road-source work, opened from the pre-merge base; conflicts in 20
   files; first screen would regress to the reference file). Do not merge it as is; rebase onto `main`, port only its new
   work, re-run the audit with an S1750-free road raster — plan and cross-checks in
   [`knowledge/08_parallel_session_pr7_2026-10-02.md`](knowledge/08_parallel_session_pr7_2026-10-02.md).
3. Test **H25-2** (strike-compatibility prior; no new data) next, then **H25-3** (scarp profile template on the processed 1 m
   tiles) and **H25-6** (map-scale correction corridor; needs a per-pixel map-scale raster from GDR 1391 via CI). H24-3A has
   a reported negative result in PR #7 (not reproduced here); H24-4A is untested.
4. Combine dotting with a *retrained, nuisance-residualized* detector only if it first beats the matched baseline.
5. If the owner supplies the S3-hosted GeoDAWN profile archives, replace the derived block raster with the official
   flight-number mapping.
6. A geologist-labelled scarp set (allowed if labels are saved) is the most direct supervised signal not yet used.
7. Keep brief-only scores flagged until the owner re-checks the submissions page.

## Owner brief (verbatim) — standing starting point, read every session

<details><summary><strong>Full owner brief (see provenance note inside)</strong></summary>

**Provenance and honesty note.** The exact message text of the 24GEMSDOE session was not available to the
agent that wrote this file. It is reconstructed from two sources, both stored verbatim by earlier work:

* **Part A** — the 24GEMSDOE-specific opening (classifier two-sample audit, H19 study, hypotheses, prompt-in-README
  rule, [0,1] error, executive summary, data placement, three passes, PR/merge). Taken unchanged from
  `knowledge/inherited_owner_charter.md`, which the earlier sessions of this repository preserved.
* **Part B** — the shared brief (score table, goal, leaderboard, Core Values, submission-form text, links,
  Site creation, passes, "create a pull request and merge") exactly as stored verbatim in
  `buffedlizard55-lab/GEMSDOE22` `README.md` (commit `96481093a7f73e5c13669e45574213d70c204ba0`), **minus** that session's own first paragraph
  (a fractal-clustering instruction that belongs to 22GEMSDOE, not to this repository).

Differences from the original message that cannot be ruled out: whitespace/link markup (the original used nested
markdown links), the order of Part A relative to Part B, and any 24GEMSDOE-specific wording not preserved in Part A.
Dated facts inside (scores, leaderboard 0.3049) reflect the moment the brief was written; `registry/live_scores.json` and the
README status block supersede stale values.

## Part A — 24GEMSDOE-specific opening (preserved wording)

```text
Review the repo; ensure an easy one-click downloadable submission tif exists
as the prompt describes; read the entire prompt. Formally test whether the
"geology" signal is actually encoding field accessibility, then remove it:
train a classifier two-sample test (the ML literature's distribution-shift
detector, Lopez-Paz & Oquab, ICLR 2017) to distinguish pixels near a mapped
fault from far pixels using ONLY non-geological confound features: distance to
nearest road/trail, distance to historic mining claims, and which of GeoDAWN's
four acquisition blocks (each with different line spacing and flight height) a
pixel falls in. If it beats its own null distribution by a meaningful margin,
that confirms the catalogue's shape is confounded by where geologists could
physically get to (strengthens the scientific case, and identifies exactly
what to residualize before training the real detector). Run on training labels
first to validate the premise, then again on our own predicted raster before
spending a submission slot; if predictions are equally explained by
road/acquisition-block proximity, the gain is mapping-process overfitting, not
discovery. A spatially-blocked holdout alone won't catch it since holdout
faults come from the same biased catalogue. Study/analyze why 19GEMSDOE got the
group's best live scores (h19-4 …691e4dfa-nan = 0.1894, h19-5 …e27054cf-nan =
0.1922) and whether we can beat 0.1894 (leader 0.3049 per user; site says
0.3168). Before implementing, produce 3–5 candidate geological hypotheses not
yet tried, each naming: specific layer(s), the physical signature targeted
(e.g. edge-detection/curvature transform), why it should catch a fault missing
from the USGS/INGENIOUS catalogue, and how it differs from everything already
in the repo; rank by expected DTI improvement and implementation cost;
validate the top one on the spatially-blocked holdout; if new external data is
needed, name the specific free official source and verify it is obtainable.
Put this prompt into the repo README and treat it as the standing starting
point each session; keep Arena Core Values ("Maximize P(Win)", "Own the
Outcome") as a focal point. Fix the submission error the user hit — "Predicted
values must be in range [0, 1]" — and give each tif a unique name plus a short
DrivenData note; create an executive-summary subpage explaining exactly how to
submit, obvious on the site's first screen. Autonomously complete the "data
placement" blocker (download into data/, then prepare_data) with no manual
input. Verify line by line against official sources with links for manual
review; flag irregularities; no hallucinations; 3 passes; finish by opening
and merging a PR to main, stating remaining work and limitations.
```

## Part B — shared brief (verbatim from GEMSDOE22 @ 96481093a7f7)

```text
Review the repo.

There should be an easy to download submission tif file as described by the prompt. Read the entire prompt.

Here are the results from submissions into the competition, separated by ....:
https://buffedlizard55-lab.github.io/GEMSDOE/docs/index.html
gems-submission-20260925T001403Z-7f00890a: 0.1563
....
https://buffedlizard55-lab.github.io/6GEMSDOE/
gems6_hgb88-topk03_33cec71ff0: 0.0286
....
https://buffedlizard55-lab.github.io/GEMSDOE3/docs/index.html
pindrop-v4-nodes-20260925T152420Z-f347b70daa: 0.1193
pindrop-v4-discovery-20260925T152423Z-37f9d5b855: 0.0830
pindrop-v4-ridge-20260925T152422Z-4e03fc9705: 0.1152
....
https://buffedlizard55-lab.github.io/GEMSDOE2/docs/index.html
gemsdoe2-dual-family-union-20260925T160406Z-f68e590f: 0.1560
....
https://buffedlizard55-lab.github.io/GEMSDOE4/
gems-submission-20260926T163915Z-237f0063: 0.0343
....
https://buffedlizard55-lab.github.io/5GEMSDOE/docs/index.html
gems-submission-20260926T175114Z-7f00890a: 0.1563
....
https://buffedlizard55-lab.github.io/7GEMSDOE/
lidarscarp-ridge-top2pct-36c3a3f341c8: 0.1461
....
https://buffedlizard55-lab.github.io/8GEMSDOE/
Hedge-v2_submission: 0.1563
....
https://buffedlizard55-lab.github.io/GEMSDOE9/docs/index.html
2314b599: 0.0107
....
https://buffedlizard55-lab.github.io/11GEMSDOE/docs/index.html
gems-structural-area06-v1: 0.0202
....
https://buffedlizard55-lab.github.io/12GEMSDOE/docs/index.html
r7-nms3-dem10-scarp_0c9199f14e62:0.1294
r7-nms3-dem10-scarp_0c9199f14e62_allfinite:0.1294
....
https://buffedlizard55-lab.github.io/15GEMSDOE/docs/index.html
gems-tso1-20260929T005627Z-conj_alteration_mag: 0.0782
....
https://buffedlizard55-lab.github.io/14GEMSDOE/docs/index.html
GEMS_r5-geom-horse-ensemble_20260929T154852Z_ccbe1de0_site_e96e942f: 0.0020
....
https://buffedlizard55-lab.github.io/17GEMSDOE/
17GEMSDOE_F-ensemble-2pct_20260930T050626Z:0.0187
....
https://buffedlizard55-lab.github.io/18GEMSDOE/
H19-C_20260930T212401Z_c11e495e: 0.0297
....
https://buffedlizard55-lab.github.io/19GEMSDOE/docs/index.html
h19-4-multiline-corroborated-openness-thermal-pop-20260930-691e4dfa-nan: 0.1894
h19-5-powerlaw-budget-multiline-corroborated-20260930-e27054cf-nan: 0.1922
....
https://buffedlizard55-lab.github.io/GEMSDOE10/
h16-continuation-20260927T065521077735Z-3431b83c7c: 0.0461
h20-dem10-scarp-thin-20260927T155223039488Z-ffc91a1686: 0.0921
H25-ctx-ridge-20260927T232947704150Z-6452ae1d00: 0.1280
h28-dotted-ridge-20260928T020256236880Z-6452ae1d00: 0.1839
....
https://buffedlizard55-lab.github.io/13GEMSDOE/
20261001_r13-lattice-s5_v2_nan-outside:0.0904
....
https://buffedlizard55-lab.github.io/16GEMSDOE/docs/index.html
h16-1-topo-geophys-baseline-ridges-20260930-df20f65e-nan: 0.1855
h18-3a-topo-geophys-x-complexity-prior-20260930-c502dfab-nan: 0.0976
h18-4-usgs-geologic-map-faults-gap-20260930-aef8f42c-nan:
....
https://buffedlizard55-lab.github.io/20GEMSDOE/docs/index.html
h20-1-sarnnpu-powerlaw-pi0363-tilt-wingcrack-20260930-be0e8f6b-nan:
h20-5-continuous-pu-proxy-unverified-20260930-824ce73a-nan:
....
https://buffedlizard55-lab.github.io/GEMSDOE21/
h19-4-reference-20260930-691e4dfa: 0.1894
....
22GEMSDOE SCORE:
....
23GEMSDOE SCORE:
....
24GEMSDOE SCORE:
....
25GEMSDOE SCORE:
....
26GEMSDOE SCORE:
....
27GEMSDOE SCORE:
....

WE NEED TO STUDY, ANALYZE, AND UNDERSTAND THE HIGHEST SCORE FROM THE GEMDOE SITE WHERE THE SUBMISSION TIF IS DOWNLOADED FROM WHICH IS THE FOLLOWING:
https://buffedlizard55-lab.github.io/19GEMSDOE/docs/index.html
h19-4-multiline-corroborated-openness-thermal-pop-20260930-691e4dfa-nan: 0.1894
h19-5-powerlaw-budget-multiline-corroborated-20260930-e27054cf-nan: 0.1922

Why and how did this get the highest score and are we able to generate a submission that scores higher than 0.1894?
Answer the question using Phd level experience, knowledge, and judgement.

The following is the leaderboard for the competition:
https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/

We need to quickly look at the results and results from the GEMSDOE websites above.

Before implementing, generate 3–5 candidate geological hypotheses we haven't tried yet, each naming: the specific layer(s) involved, the physical signature being targeted (e.g., an edge-detection or curvature transform), why it should catch a fault missing from the USGS/INGENIOUS catalogue rather than one already in it, and how it differs from anything already implemented in this repo. Rank them by expected DTI improvement and implementation cost. Validate the top candidate on our spatially-blocked holdout set before touching a weekly submission slot — do not spend a submission slot on an idea that hasn't beaten the current holdout best. If a candidate can't be validated without new external data, name the specific free, official source needed and check it's obtainable before proposing the idea as viable.
Work line by line verifying from official verified trusted sources, provide links for manual review. There should be no manual input, work on your own to complete tasks. Flag any irregularities for review. No hallucinations.
Verify no hallucinations.

The goal of this project is to get a full list that follow our requirements. No hallucinations. Verify line by line.

We have a good understanding of how our hypothesis, methodology, calculations, analysis are done so we should be able to figure out a way to score higher on the leaderboard using previous results and scoring that we have across the sites listed above. We need to come up with distinct and unique strategies to score higher in this competition leaderboard. We need to start doing heavy and deep research into the part of the project that matters the most, which is the scientific discovery of geothermal vents. We should store all of our information and knowledge that we can gather from official verified sources. This will serve as a starting point for other projects as well. We need to think outside the box but still be grounded in proper scientific research, we are ultimately aiming for a top prize that many others are competing for. So it's important to be contrarian but be smart about it. We need to find sources of data that others are over looking or areas of the project when it comes to geothermal vents. We need to do deep research and critical thinking and come up with new hypothesis to test.

The following sites should serve as a starting point for understanding how to generate TIF submissions. These websites are researched, and tested and have generated TIF submissions. But we need to generate high scoring submissions.

https://buffedlizard55-lab.github.io/GEMSDOE/docs/index.html
gems-submission-20260925T001403Z-7f00890a: 0.1563
https://buffedlizard55-lab.github.io/6GEMSDOE/
gems6_hgb88-topk03_33cec71ff0: 0.0286
https://buffedlizard55-lab.github.io/GEMSDOE3/docs/index.html
pindrop-v4-nodes-20260925T152420Z-f347b70daa: 0.1193
pindrop-v4-discovery-20260925T152423Z-37f9d5b855: 0.0830
pindrop-v4-ridge-20260925T152422Z-4e03fc9705: 0.1152
https://buffedlizard55-lab.github.io/GEMSDOE2/docs/index.html
gemsdoe2-dual-family-union-20260925T160406Z-f68e590f: 0.1560
https://buffedlizard55-lab.github.io/GEMSDOE4/
gems-submission-20260926T163915Z-237f0063: 0.0343
https://buffedlizard55-lab.github.io/5GEMSDOE/docs/index.html
gems-submission-20260926T175114Z-7f00890a: 0.1563
https://buffedlizard55-lab.github.io/7GEMSDOE/
lidarscarp-ridge-top2pct-36c3a3f341c8: 0.1461
https://buffedlizard55-lab.github.io/8GEMSDOE/
Hedge-v2_submission: 0.1563
https://buffedlizard55-lab.github.io/GEMSDOE9/docs/index.html
2314b599: 0.0107
https://buffedlizard55-lab.github.io/11GEMSDOE/docs/index.html
gems-structural-area06-v1: 0.0202
https://buffedlizard55-lab.github.io/12GEMSDOE/docs/index.html
r7-nms3-dem10-scarp_0c9199f14e62:0.1294
r7-nms3-dem10-scarp_0c9199f14e62_allfinite:0.1294
https://buffedlizard55-lab.github.io/15GEMSDOE/docs/index.html
gems-tso1-20260929T005627Z-conj_alteration_mag: 0.0782
https://buffedlizard55-lab.github.io/14GEMSDOE/docs/index.html
GEMS_r5-geom-horse-ensemble_20260929T154852Z_ccbe1de0_site_e96e942f: 0.0020
https://buffedlizard55-lab.github.io/17GEMSDOE/
17GEMSDOE_F-ensemble-2pct_20260930T050626Z:0.0187
https://buffedlizard55-lab.github.io/18GEMSDOE/
H19-C_20260930T212401Z_c11e495e: 0.0297
https://buffedlizard55-lab.github.io/19GEMSDOE/docs/index.html
h19-4-multiline-corroborated-openness-thermal-pop-20260930-691e4dfa-nan: 0.1894
h19-5-powerlaw-budget-multiline-corroborated-20260930-e27054cf-nan: 0.1922
https://buffedlizard55-lab.github.io/GEMSDOE10/
h16-continuation-20260927T065521077735Z-3431b83c7c: 0.0461
h20-dem10-scarp-thin-20260927T155223039488Z-ffc91a1686: 0.0921
H25-ctx-ridge-20260927T232947704150Z-6452ae1d00: 0.1280
h28-dotted-ridge-20260928T020256236880Z-6452ae1d00: 0.1839
https://buffedlizard55-lab.github.io/13GEMSDOE/
20261001_r13-lattice-s5_v2_nan-outside:0.0904
https://buffedlizard55-lab.github.io/16GEMSDOE/docs/index.html
h16-1-topo-geophys-baseline-ridges-20260930-df20f65e-nan: 0.1855
h18-3a-topo-geophys-x-complexity-prior-20260930-c502dfab-nan: 0.0976
h18-4-usgs-geologic-map-faults-gap-20260930-aef8f42c-nan:
https://buffedlizard55-lab.github.io/20GEMSDOE/docs/index.html
h20-1-sarnnpu-powerlaw-pi0363-tilt-wingcrack-20260930-be0e8f6b-nan:
h20-5-continuous-pu-proxy-unverified-20260930-824ce73a-nan:
https://buffedlizard55-lab.github.io/GEMSDOE21/
h19-4-reference-20260930-691e4dfa: 0.1894
22GEMSDOE SCORE:
23GEMSDOE SCORE:
24GEMSDOE SCORE:
25GEMSDOE SCORE:
26GEMSDOE SCORE:
27GEMSDOE SCORE:

WE NEED TO STUDY, ANALYZE, AND UNDERSTAND THE HIGHEST SCORE FROM THE GEMDOE SITE WHERE THE SUBMISSION TIF IS DOWNLOADED FROM WHICH IS THE FOLLOWING:
https://buffedlizard55-lab.github.io/19GEMSDOE/docs/index.html
h19-4-multiline-corroborated-openness-thermal-pop-20260930-691e4dfa-nan: 0.1894
h19-5-powerlaw-budget-multiline-corroborated-20260930-e27054cf-nan: 0.1922

Why and how did this get the highest score and are we able to generate a submission that scores higher than 0.1894?
Answer the question using Phd level experience, knowledge, and judgement.

The following is the leaderboard for the competition:
https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/

0.3049 is the highest score right now so we need to design a new strategy, research, testing, analyzing, and generating submission system than the current website. It should be unique, take unique approaches to generating a submission that can score higher than .3049.

Put this prompt into the repo readme and read it everytime we work on the project as a starting point to make sure we are building what we are aiming for and have a strong base to continue building and improving on making something useful for everyday use. It should solve the problem of having to manually check everything ourselves and have an up to date current feed.

Review the repo.

The following is taken from the Arena AI team and I think it makes a good point on building a successful project, so let's keep the Core Values and Own the Outcome as a focal point when building, developing, researching, suggesting upgrades, and implementing the work.

Our Core Values
Maximize P(Win)
"Maximize the Probability of Winning": our decision making framework. In every decision, we weigh tradeoffs, assess risk, and choose the path that maximizes the probability that Arena succeeds. We set aside our emotions and make tough decisions in order to maximize P(Win). "Maximize P(Win)" frees us from constraints and clarifies that we must put Arena first.

Own the Outcome
We own results end to end — not just our individual slice of the work. When problems arise and we have the means to act, we do so without waiting for permission or assignment. We treat failure and success as signals and use them to improve. At Arena, we stay accountable to the final outcome.

Work line by line verifying from official verified trusted sources, provide links for manual review. There should be no manual input, work on your own to complete tasks. Flag any irregularities for review. No hallucinations.
Verify no hallucinations.
The goal of this project is to get a full list that follow our requirements. No hallucinations. Verify line by line.

We need to focus on being able to generate a submission into the competition.

The site should be able to generate a TIF file that is required for submission. It should be as easy as download to click a File to submit into the competition. This needs to be in the executive summary or the very beginning of the site. it should be obvious when you visit the site.

I tried to submit the document that i downloaded from the site but it returned this error on the submission form:
"Predicted values must be in range [0, 1]"

Also we need to give it a unique name and A short comment to help you or your team tell submissions apart later e.g. clustering with k=25

Here is the submission page when i click submit file
New submission

File to submitNo file chosen
You can submit a single-band GeoTIFF (.tif) file, or a .zip file containing a single GeoTIFF, with your predictions. It must match the submission format's CRS, shape, and geotransform. You may wish to review the competition rules first.
Note (optional)
A short comment to help you or your team tell submissions apart later e.g. clustering with k=25

Create a executive summary subpage that explains exactly how to make a submission into the contest.

Work on the next steps from the previous sessions first.

The goal of this project is to place top of the leaderboard in this competition. The following is the competition:
https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/

We need to create a project that can compete and place top of the leaderboard. We need to understand the problem, collect all the data and organize it into a clean easily auditable table with official verified links for manual verification.

This is the guidelines we need to follow.https://www.drivendata.org/competitions/306/competition-doe-gems/
Get familiar with the problem through the overview and problem description,https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/. You might also want to reference additional resources available on the about page,https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/.
Download the data from the data,https://www.drivendata.org/competitions/306/competition-doe-gems/data/, tab.
Create and train your own model. This reference solution,https://github.com/drivendataorg/gems-prize-reference-solution implements a simple approach.
Use your model to generate predictions that match the submission format.
Tell me what are you limitations and what you need access to during this project. We will need to find free publicly available sources and data from official and verified sources if we are to use 3rd party or external data.

this pdf outlines how submissions must be entered into the competition.
https://docs.nlr.gov/docs/fy26osti/96647.pdf

You must be able to do your own research, deep research, scientific literature research and organize the knowledge so that we can critically think through the problem and generate a solution through scientific and free publicly available information. this must be done autonomously and must be constantly reviewed and improved upon. Provide suggestions and improvements and implement them.

No DrivenData auth -> cannot auto-download training_features.tif, labels.tif, sample_submission.tif, 1m_DEM_links.csv from https://www.drivendata.org/competitions/306/competition-doe-gems/data/ (verified redirect to login)
See below for links from the above site. See attached files for links from the above site.
https://gdr.openei.org/submissions/1391

Download competition data from https://www.drivendata.org/competitions/306/competition-doe-gems/data/ (requires login) to data/
See links below for competition data:
https://www.dropbox.com/scl/fi/aemhtutjgcp6tr3tint94/GEMS_96647.pdf?rlkey=rek210cj2smnmzb8n0sla1vmd&st=wz4kofki&dl=0
https://www.dropbox.com/scl/fi/6rgvnuady818ol8yqgis4/example_submission.tif?rlkey=kbykilvau066xuogoosbf4cq8&st=8junzdyw&dl=0
https://www.dropbox.com/scl/fi/t7fyt03qdh9egyme0itwo/existing_faults.tif?rlkey=yiao96uluqdkipf0h5vju71jf&st=rnino7ya&dl=0
https://www.dropbox.com/scl/fi/3vz9o0wwavi26xaeoxlwr/gems-geodawn-numerical-features.tif?rlkey=je8d8fepqfbst9lnwsq9rkplu&st=zj1lag1r&dl=0
https://www.dropbox.com/scl/fi/ig0mban712ns1atphgphe/Digital-elevation-model-links-JSON.pdf?rlkey=zm77f1vbtt2if8hlruymptnu3&st=srhhir10&dl=0

Work line by line verifying from official verified trusted sources, provide links for manual review. There should be no manual input, work on your own to complete tasks. Flag any irregularities for review. No hallucinations.
Verify no hallucinations.
The goal of this project is to get a full list that follow our requirements. No hallucinations. Verify line by line.

Site creation
Create a github page for this repo that has clean ui, user friendly, simple and easy to use. It should be organized and clean.

It should include all relevant information in an easy to read format with official verified links as sources for review. Work line by line verify everything no hallucinations.

The single remaining blocker to training is data placement: run bash scripts/download_competition_data.sh on any unrestricted machine into data/, then python scripts/prepare_data.py — after that the full train->inference->validate pipeline is ready to run (GPU needed for training; metric/losses/validation all verified working here on CPU).

you need to complete the above task by yourself. Work line by line verifying from official verified trusted sources, provide links for manual review. There should be no manual input, work on your own to complete tasks. Flag any irregularities for review. No hallucinations.

Verify no hallucinations.

The goal of this project is to get a full list that follow our requirements. No hallucinations. Verify line by line.

Run this task through multiple passes.
Pass 1: Implement the task completely and verify the result.
Pass 2: Review your work for bugs, missing requirements, incorrect assumptions, and edge cases. Fix everything you find.
Pass 3: Re-check the entire implementation against the original request. Improve accuracy, reliability, completeness, and code quality. Fix any remaining issues.
Do not stop after the first pass. Each pass must build on the previous one. Before finishing, verify that the final result fully satisfies the original request. Work line by line verify everything no hallucinations.

Go ahead and create a pull request and then merge the pull request onto the main. Make suggestions for what work still needs to be done and any limitations that is in the way of a successful project. It should be worked on in this next session or the next session. Work line by line verify everything no hallucinations.
```

</details>


---

## Current-brief appendix — received 2026-10-25

<details>
<summary>Current owner prompt / standing requirements (read every session)</summary>

# Owner prompt — active requirements received 2026-10-25

This is an operational transcription with repetitions consolidated, not a claim of a byte-for-byte transcript of the chat. It supplements the older verbatim brief. Read this and the README at the beginning of every session. Historical numbers are owner assertions, not verified organizer receipts.

## Highest urgency

> MUST GENERATE A UNIQUE TIF SUBMISSION FOR THE COMPETITION. DO NOT COPY A PREVIOUS SUBMISSION UNLESS IT'S FOR LEARNING AND EDUCATION. BUT WE MUST GENERATE A UNIQUE TIF SUBMISSION. IT MUST BE OBVIOUS WHETHER IT IS OK TO DOWNLOAD AND SUBMIT THE GENERATED TIF SUBMISSION.

Review the repo and work on real next steps from previous sessions first. Focus on the best submissions named by the owner from **GEMSDOE24, GEMSDOE25, GEMSDOE27, GEMSDOE28, GEMSDOE30, GEMSDOE31, GEMSDOE32, GEMSDOE33 and GEMSDOE36**. Study source code and actual emitted rasters, not just method names. Generate a genuinely new prediction, not a renamed or repackaged prior prediction. A failed scientific test is still a deliverable; do not falsely mark it ready to submit.

## Parallel-run protocol (priority)

1. **LANE:** The session is one of several. Stay in the assigned single-method lane. Surface rank correlation above 0.90 with any registry raster, or more than 70% of candidate dots within 3 px of one registry raster, means duplicate: log and stop. Check before placement and on final dots. No single method paragraph was actually supplied in this message; do not silently assert an assignment.
2. **REUSE, DON'T REBUILD:** Use the template's cached feature stack and shared holdout evaluator/submission writer. Hide-and-recover must withhold whole fault segments with a buffer; derive every catalogue feature from visible faults only; mask visible faults pixel-exactly; score pooled DTI, alpha 0.2, beta 0.8, 300 m triangular kernel. Fix shared defects once in the template and report them; no private evaluator forks.
3. **NUMBER PROVENANCE:** A score is HOLDOUT-DTI (version, withheld-positive count, 95% CI) or ORGANIZER-CONFIRMED (artifact-linked submission-page receipt). A projection is never a score. Unverified owner assertions must not be forced into either verified category.
4. **LEAKAGE CANARY:** Test each feature alone on the holdout before trusting it; AUC above 0.90 means leakage until disproved. Preserve failed tests.
5. **RUN CARD:** End with one JSON card: hypothesis; mechanism; named non-fault mimic; holdout DTI and CI; registry correlation/overlap; raster SHA256; validator results (no NaN inside footprint, [0,1], CRS/shape/transform match); unique submission name and <=140-character note; verdict promote/negative. Negative results count.
6. **BUDGET:** Stop after 3 experiments or 2 hours. Do not select actual submissions: promotion to a real slot belongs to a separate selector, within the current submission-page weekly cap.

## Specific research question and evidence handling

The owner names `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` from [GEMSDOE32](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html) and reports **0.2778**. Explain what is actually known about why/how that artifact improved, and whether a higher result can be supported, with PhD-level scientific judgment. The same brief calls **0.4413** a current high score and later calls **0.3195** the current high score. These conflict; neither is a verified current leaderboard result here. Never infer an exact-file score from a team-account leaderboard row.

The owner's named nine-site results (all **UNVERIFIED-OWNER-REPORT**, no organizer receipt supplied):

| Site | Owner-named artifact | Owner assertion, not a verified score |
|---|---|---|
| [GEMSDOE24](https://buffedlizard55-lab.github.io/GEMSDOE24/) | h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan | 0.2477 |
| [GEMSDOE25](https://buffedlizard55-lab.github.io/GEMSDOE25/) | dotted-h19-5-d2-8-20261002-e56ea318af89-nan | 0.2600 |
| [GEMSDOE27](https://buffedlizard55-lab.github.io/GEMSDOE27/) | topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan | 0.2449 |
| [GEMSDOE28](https://buffedlizard55-lab.github.io/GEMSDOE28/) | h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan | 0.2710 |
| [GEMSDOE30](https://buffedlizard55-lab.github.io/GEMSDOE30/) | d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca | 0.2600 |
| [GEMSDOE31](https://buffedlizard55-lab.github.io/GEMSDOE31/docs/) | h27-4-solo-d28-20261004-8acb75e1-nan | 0.2708 |
| [GEMSDOE32](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html) | h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros | 0.2778 |
| [GEMSDOE33](https://buffedlizard55-lab.github.io/GEMSDOE33/) | h33d-analog-tip-stepover-r30-20261004-cb490425926e | 0.2632 |
| [GEMSDOE36](https://buffedlizard55-lab.github.io/GEMSDOE36/docs/) | anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros | 0.2750 |

The wider historical list is context, not authorization to reproduce those emissions or a requirement to run every past method. Evaluate the named best artifacts first. Keep unverified submissions and score claims distinct from measured local results.

## Geological discovery, hypotheses and data

Before implementation, produce 3–5 genuinely unimplemented geological hypotheses. Each names precise layers, physical transform/signature, why it might find a fault missing from USGS/INGENIOUS rather than merely repeat the catalogue, how it differs from existing work, and the non-fault mechanism that can mimic it. Rank by expected DTI benefit and implementation cost; do not fabricate numerical forecasts. Validate the top candidate on spatially blocked holdout before any weekly slot; do not spend a slot unless it beats the current comparable holdout best. If a new source is needed, identify a free official source and check obtainability before calling the idea viable.

Deep research, literature analysis and auditable source/knowledge tables should support geothermal science and reusable future projects. Be contrarian but physically grounded. Fault geometry, geothermal vents, permeability and commercially viable resources are different claims: do not conflate them. Keep official trusted links, factual verification boundaries, current feed timestamps and irregularities. Verify implementation line by line with tests; do not promise absence of every possible hallucination or pretend unread sources were read.

Resolve routine data placement and engineering autonomously. The historical instruction about GPU training being ready after data placement is a premise to audit, not proof it remains true. Use available cached official-derived inputs; do not claim downloads/training that did not happen. State network, authentication, provenance and current-best reconstruction limits. Never ask for GitHub credentials.

## Submission generation and user interface

A single-band GeoTIFF `.tif` (or `.zip` containing one GeoTIFF) must match the submission template's CRS, shape and geotransform. Values inside the footprint must be finite and in [0,1]. Preserve explicit outside-footprint encoding. Reopen the exact generated bytes, hash them and attach validator output. Address the prior portal error **“Predicted values must be in range [0, 1]”** without asserting an unverified cause. Give the artifact a unique name/content identity and a short **Note (optional)**, <=140 characters for this lane.

Make one-click TIFF download and a conspicuous download/submit status the first thing on the site and executive summary. Clean, simple GitHub Pages UI; organized research and official-source links. Create a dedicated executive-summary/submission-guide subpage. Scientific inspection/gates must be automated through the project; an opaque “ask a human inspector” must not stand in for validation. A failed gate must visibly block authorization, not hide behind a format-green badge. Actual weekly selection is separate, and the project does not auto-upload.

## Official and data links to retain for review

- [Competition](https://www.drivendata.org/competitions/306/competition-doe-gems/), [problem/metric](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/), [about/resources](https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/), [data](https://www.drivendata.org/competitions/306/competition-doe-gems/data/), [leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/).
- [Organizer reference solution](https://github.com/drivendataorg/gems-prize-reference-solution).
- [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and), [INGENIOUS](https://gbcge.org/current-projects/ingenious/), [GDR 1391](https://gdr.openei.org/submissions/1391).
- [Prize rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf); [EPSG:32611](https://epsg.io/32611); [Tversky background](https://en.wikipedia.org/wiki/Tversky_index) (background, not organizer authority).
- Owner-supplied Dropbox mirrors: [rules](https://www.dropbox.com/scl/fi/aemhtutjgcp6tr3tint94/GEMS_96647.pdf?rlkey=rek210cj2smnmzb8n0sla1vmd&st=wz4kofki&dl=0), [template](https://www.dropbox.com/scl/fi/6rgvnuady818ol8yqgis4/example_submission.tif?rlkey=kbykilvau066xuogoosbf4cq8&st=8junzdyw&dl=0), [existing faults](https://www.dropbox.com/scl/fi/t7fyt03qdh9egyme0itwo/existing_faults.tif?rlkey=yiao96uluqdkipf0h5vju71jf&st=rnino7ya&dl=0), [features](https://www.dropbox.com/scl/fi/3vz9o0wwavi26xaeoxlwr/gems-geodawn-numerical-features.tif?rlkey=je8d8fepqfbst9lnwsq9rkplu&st=zj1lag1r&dl=0), [DEM links PDF](https://www.dropbox.com/scl/fi/ig0mban712ns1atphgphe/Digital-elevation-model-links-JSON.pdf?rlkey=zm77f1vbtt2if8hlruymptnu3&st=srhhir10&dl=0). Mirrors are not independent organizer provenance.

Existing repository policy prohibits automated DrivenData access, including leaderboard scraping. Do not bypass it or silently claim a continuously updated leaderboard. An automated official-source health snapshot is not a live competition feed.

## Core values and delivery

**Maximize P(Win):** weigh risk, tradeoffs and evidence, not comfortable busywork or cosmetic submission fishing. **Own the Outcome:** resolve problems within available authority, retain failures, preserve reproducibility and report genuine limitations.

Work autonomously, through **three passes**: implement/verify; review bugs, edge cases and assumptions and fix them; recheck against original acceptance criteria and improve quality. Do not stop after the first pass. Provide the full requirement status and future work. Open a pull request from the session branch and merge it onto main if checks and permissions permit. Never claim a PR, merge or deployment without evidence. Do not change another parallel session's branch or merge its conflicting work by overwrite.

</details>
