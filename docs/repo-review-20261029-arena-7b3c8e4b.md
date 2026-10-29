# Three-pass repository review — 29 October 2026

**Decision: no submission-authorized file · SUBMIT: NO.** This review branch generated no new TIFF, geological experiment, holdout evaluation, score estimate, competition slot, selector approval, or organizer receipt. The requested unique, validated, high-scoring submission remains unmet. The review rejects the prominent label “Unique GeoTIFF” for a 3,165-dot lattice-hole artifact whose zero overlap is by construction. It also re-reviewed the separately merged GEO1 research TIFF on current `origin/main`; that new artifact fails protocol uniqueness (99.25% lattice overlap) and is not authorized to submit.

[Submission guide](executive-summary.html) · [Historical nine-site exact-file table](historical-champions.html) · [GitHub source freshness record](data/priority_feed.json) · [Machine-readable run card](../evidence/session_7b3c8e4b_20261029_run_card.json) · [Standing method and submission rules](MISSION_PROMPT.md).

## Nine-site table — pinned historical artifacts, not current-head reviews

The exact downloads below come from the pinned 2026-10-28 audit. The score column is a site-level owner claim; it is not proven to be the organizer score for the adjacent exact file. The claims are owner-reported and unverified; leaderboard estimates are **NOT ESTIMABLE**. The recorded lattice overlaps fail the project’s 70% threshold. They are not a re-audit of current HEADs: the GitHub freshness check later found that all nine focus repositories had advanced beyond the review pins. See the linked historical page for immutable source links, full SHA-256 hashes and format caveats.

| Site | Exact historical research TIFF | Historical claim (owner-reported / unverified) | Leaderboard estimate | Recorded 3-px lattice result | Decision |
|---|---|---:|---|---|---|
| GEMSDOE24 | `gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-allfinite.tif` | 0.2477 | **NOT ESTIMABLE** | 99.92% · FAIL | Research only · SUBMIT NO |
| GEMSDOE25 | `gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-zeros.tif` | 0.2600 | **NOT ESTIMABLE** | 99.92% · FAIL; same footprint prediction as GEMSDOE30 | Research only · SUBMIT NO |
| GEMSDOE27 | `gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-allfinite.tif` | 0.2449 | **NOT ESTIMABLE** | 99.92% · FAIL | Research only · SUBMIT NO |
| GEMSDOE28 | `gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-allfinite.tif` | 0.2710 | **NOT ESTIMABLE** | 99.91% · FAIL | Research only · SUBMIT NO |
| GEMSDOE30 | `gemsdoe30-d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca.tif` | 0.2600 | **NOT ESTIMABLE** | 99.92% · FAIL; same footprint prediction as GEMSDOE25 | Research only · SUBMIT NO |
| GEMSDOE31 | `gemsdoe31-h27-4-solo-d28-20261004-8acb75e1-allfinite.tif` | 0.2708 | **NOT ESTIMABLE** | 99.92% · FAIL | Research only · SUBMIT NO |
| GEMSDOE32 | `gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif` | 0.2778 | **NOT ESTIMABLE** | 99.92% · FAIL | Research only · SUBMIT NO |
| GEMSDOE33 | `GEMSDOE33-h33d-analog-tip-stepover-r30-20261004-cb490425926e.tif` | 0.2632 | **NOT ESTIMABLE** | 99.91% · FAIL | Research only · SUBMIT NO |
| GEMSDOE36 | `gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif` | 0.2750 | **NOT ESTIMABLE** | 99.92% · FAIL | Research only · SUBMIT NO |

No value in the “historical claim” column is an organizer-confirmed score. No score is projected from a holdout metric.

## GEO1 on current main — a research negative, not a unique submission

During this review `origin/main` advanced from `6284a52` to `946e381` through PRs #105–#107. PR #107 added a separate GEO1 run and TIFF from branch `arena/06c9bde0`; this branch did not generate or retune it. The merged run card records:

- Exact zero-outside file: `GEMSDOE24-geo1-concealed-conduit-rad-mag-lidar-20261029-8c9946590ca7-zeros.tif`; SHA-256 `ee37d94deb3545af1f814df61ec5acd7addafe01a4833384c2e25d1a5e6b384d`; 129,184 in-footprint binary dots.
- **HOLDOUT-DTI 0.1426949**, 95% CI [0.1322931, 0.1523671], `gems-segment-pooled-v1`, 60,988 withheld positives. This is a source-recorded internal result, not independently replayed here, not an organizer score, and not a leaderboard estimate.
- Pre-placement max |Spearman ρ| 0.210739 versus 8 locally cached registry rasters; final-dot max overlap **0.9925378** versus the retained spacing-5 lattice (threshold 0.70). The source run is a negative result: the exact file is not protocol-unique, and the current peer-head registry was not completely audited. **DOWNLOAD: research only · SUBMIT: NO.**
- The zero-outside variant’s receipt says `format_valid: true` but `official_format_compliant: false`; the NaN-outside twin has the opposite local whole-array NaN result. This does not diagnose portal acceptance. No slot was spent and no organizer receipt exists.
- Implementation irregularity: `scripts/build_unique_geothermal_submission.py` passes the same `TMI_up150` grid as both `rtp_like` and `tmi_up150`. The run’s `tmi_up150_edge` and `rtp_proxy_edge` canaries are numerically identical. The “RTP proxy” is therefore not an independent channel. This is disclosed, not repaired by retuning the stopped experiment.

The current [`executive-summary-9sites.html`](executive-summary-9sites.html) now describes GEO1 as a research TIFF, labels it **NOT UNIQUE · SUBMIT: NO**, limits the uniqueness claim to the available comparison scope, and discloses the format limitation. The older lattice-hole diagnostic is separately labelled **NOT UNIQUE** in the submission guide.

## GEMSDOE32 B2: what the 0.2778 report does and does not establish

The 0.2778 is an **OWNER-REPORTED / UNVERIFIED** claim, not an organizer receipt. The saved artifact-forensics record says the B2 pattern is a deletion-only subset of the GEMSDOE25 pattern after removing 6,436 catalogue-adjacent dots within 200 m; it is also the GEMSDOE31 pattern after removing 2,545 dots. That record is geometry/count evidence, not a replay in this review. Pruning could improve a distance-weighted Tversky score if false-positive mass removed exceeds lost hidden-fault credit. Hidden labels and an organizer receipt are unavailable here, so the cause and score remain unknown. Do not present 0.2778 as a verified current score, a leaderboard estimate, or proof of geothermal causation. See [`evidence/oj1_priority_ancestry_replay.json`](../evidence/oj1_priority_ancestry_replay.json) and the [corrected metric explanation](metric-integrity-20261026.md).

## Pass 1 — establish the current review boundary

- Confirmed the session branch is `arena/7b3c8e4b-gemsdoe24`, based on merged PR #103 at `6284a525a9425ed442f8e3fc0e04dfbd6fce537d`. Restored full Git history; no checkout or branch change was made.
- Refreshed `docs/data/priority_feed.json` from GitHub at 2026-10-29 17:11 UTC: 9/9 main refs checked, 9/9 changed since their older pins, 0 failures. GEMSDOE24 points to `946e381`; PRs #105–#107 had advanced `origin/main`. This is **source-ref freshness only**; it is not a new-raster audit of all peer heads, score check, live leaderboard, or receipt.
- The required `data/training_features.tif`, `data/prepared/features.npy`, and `data/geofeat/` cache are absent. A small bridge template and selected bridge rasters do not replace the prepared feature stack. No scientific rerun is possible from the staged data, and no user/portal credential or data-download exception was requested.
- Read the official competition reference solution README from GitHub at commit [`aebe92f7c8a990f0e3443451b7a825d9afd6336b`](https://github.com/drivendataorg/gems-prize-reference-solution/blob/aebe92f7c8a990f0e3443451b7a825d9afd6336b/README.md). It instructs users to download competition data into `data/` and provides a CPU-only setup; the README digest and scope are recorded in [`session_fc014f14_official_reference.json`](../evidence/session_fc014f14_official_reference.json). This does not establish that the missing data are obtainable in this checkout. DrivenData’s portal, leaderboard, quota, hidden labels and submission receipts were not accessed; automated portal access and uploads remain prohibited by `AGENTS.md`.

## Pass 2 — reproduce the gate and repair the misleading label

Reran the shared necessary-only lattice feasibility check for the already recorded 37,654- and 44,090-dot diagnostic budgets. The 3-px neighborhood covers 5,160,724 of 5,167,373 footprint cells; 6,649 cells are uncovered. The resulting lower bounds are:

| Diagnostic budget | Minimum overlap with retained lattice | Result |
|---:|---:|---|
| 37,654 | 82.3418% | `STOP_IMPOSSIBLE_BUDGET` |
| 44,090 | 84.9195% | `STOP_IMPOSSIBLE_BUDGET` |

These are **necessary-condition geometric bounds**, not measured candidate overlap, model quality, leaderboard scores, or evidence of copied geology. The check exited 2 as designed and authorized no submission. There was no candidate surface, so pre-placement rank correlation was **not run**; no final dots existed for a final-overlap test. The retained comparator was not removed, weakened, or evaded.

The executive page had called an old lattice-hole diagnostic “Unique GeoTIFF.” Its own run card says 3,165 dots were selected from the lattice’s 3-px coverage holes, giving zero lattice overlap **by construction**. A separate stored receipt covers only 69 local same-grid rasters and explicitly excludes the full 167-alias registry and other repositories. That partial comparison cannot cure the prohibited placement strategy. The site generator now labels the artifact **“Lattice-hole diagnostic — research only · NOT UNIQUE · SUBMIT: NO,”** explains why the lattice result is invalid as a uniqueness pass, and identifies the local comparison as incomplete. The merged GEO1 page now labels that separate artifact **research only / NOT PROTOCOL-UNIQUE / SUBMIT: NO**, limits the scope of the registry comparison, discloses the zero-outside format limitation, and fixes its previously broken relative links; generated site navigation now links to the nine-site page. The old lattice-hole download and its negative, source-recorded holdout were not modified or replayed.

## Ranked hypotheses — proposals only, not lane assignments or forecasts

These are carried-forward research proposals, not newly validated methods. Their ranking is a qualitative information-per-cost judgment; expected DTI gain is **unknown**. The scoped local source search did not find these exact operators implemented, but related ideas already occur in project notes, and all nine focus repositories have changed since their pinned reviews. **No global untried/unique claim is made.** No new external source is assumed; all proposed layers are existing competition feature channels. The required local training/cache stack is absent, so none is presently executable or validated.

| Rank / relative cost | Layers and physical signature | Why a catalogue gap is plausible; named non-fault mimic | Difference from existing local operators |
|---|---|---|---|
| 1 · medium–high | `rtp` + `iso_grav_anom`: third-order, directional cross-bicoherence at preregistered wavelengths; look for reproducible phase coupling of a fundamental and harmonic across the independent fields. | A concealed sharp offset could retain cross-field phase coupling despite weak surface expression. **Mimics:** intrusive contacts, volcanic boundaries, or survey leveling. This signature is a hypothesis, not a diagnostic already established for faults. | Third-order phase coupling differs from XVAR1’s second-order semivariogram increments and EUL1 gradients. QPC3 is a prior second-order phase proposal; cross-bicoherence is related but not the same transform. |
| 2 · medium–high | `cond_surf` + `depth_to_base_surf`: contour-component merge persistence under a fixed threshold filtration, evaluated where a conductive corridor crosses a basement step. | A buried discontinuity might connect conductive patches across structural relief without a mapped surface scarp. **Mimics:** clay-rich basin fill and saline groundwater. | Tests connectivity across thresholds rather than CON’s pointwise saddle/Hessian response or a single-amplitude edge. Conductivity alone is non-unique evidence. |
| 3 · high | `rtp` + `iso_grav_anom`, with `depth_to_base_surf` used only in fold-fitted conditioning: partial wavelet coherence and a prespecified signed cross-front phase lag. | A scale-stable residual boundary may survive broad basement-trend removal where a fault is concealed. **Mimics:** igneous contacts, volcanic structures, and survey artifacts. | Scale-specific conditioned cross-spectra differ from unsigned TMCG cross-gradients and QPC3 quadrature phase congruency, but overlaps the project’s earlier phase-family proposals; incremental value is unproven. |

Before any implementation: obtain the missing single-method assignment; compare current sibling source heads before making a novelty claim; preregister only within the three-experiment/two-hour budget; use the shared whole-segment buffered holdout, visible-only catalogue features, pixel-exact visible mask, per-feature leakage canaries, pooled DTI (α=0.2, β=0.8; 300 m triangular kernel), paired 95% intervals and the complete registry gate. A single-feature AUC above 0.90 remains leakage until resolved. The retained-lattice protocol issue must be resolved prospectively, not bypassed by targeting holes. No slot may be used without the separate selector.

## Pass 3 — regression, site build and verification

- Added regression coverage for the lattice-hole label, GEO1 research-only/not-unique wording, the current-peer comparison scope, the format caveat, generated nine-site navigation, working local links, and strict duplicate-key rejection in this review's JSON card. The older hash-bound diagnostic card, TIFF, ≤140-character note, overlap-receipt binding, and DO_NOT_SUBMIT guard remain fail-closed.
- Rebuilt the site successfully at 2026-10-29 17:15:54 UTC. The generated executive guide links to this review; the builder refreshed the recorded S3DEP1/current-selector negative review timestamps without changing its fail-closed decision, generating a new prediction, or spending a slot.
- Final full suite: **667 passed in 229.50 seconds**. Focused site + diagnostic tests: **37 passed in 106.38 seconds**. Repository-wide Ruff check passed; Ruff format check passed (**345 files**); `git diff --check` passed. `scripts/check_git_history.py` reported a non-shallow repository; as its output cautions, pinned commits and ancestry still require individual verification. Both 37,654- and 44,090-dot feasibility checks returned the expected exit 2 and `STOP_IMPOSSIBLE_BUDGET`; no surface or candidate dots were generated.
- Resolved the conflicts from merging the current mainline through PRs #105–#107, including the run-card/README status; no conflict markers remain. Opened PR #110 from this active branch to `main`; its check and merge outcome are tracked on GitHub. The earlier PR #103 was already merged before this session. No file is submission-authorized.

## Close-out / limitations

The review improves documentation integrity but does **not** satisfy the request for a new unique or high-scoring GeoTIFF. The stale nine-site artifact table is clearly labeled historical; all nine current peer heads were not raster-audited and no current scores were verified. The separately merged GEO1 file was reviewed only from its source-recorded evidence and code, not regenerated or independently re-evaluated. The B2 explanation remains a plausible pruning mechanism, not a causal result. No external geology dataset is needed for the listed proposals, but their required feature stack is absent. No external-source availability beyond the official GitHub reference README was verified.

[Machine-readable review run card](../evidence/session_7b3c8e4b_20261029_run_card.json). Final verification results are recorded there.
