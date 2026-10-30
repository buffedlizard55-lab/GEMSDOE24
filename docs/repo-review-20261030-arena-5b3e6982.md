# Three-pass repository review — GEMS DOE 24

**Date:** 2026-10-30 · **Branch:** `arena/5b3e6982-gemsdoe24` · **Base:** `63d5885b68f73c19a7746052ccb3e5690f3271b5`

## Executive disposition

**NO NEW TIFF · NO EXPERIMENT · NO SLOT · SUBMIT: NO.** This review corrected the nine-site report and its generator, added regression coverage, and documented integrity and feasibility stops. No geological hypothesis was selected, no surface or dots were generated, no holdout was rerun, and no upload or organizer contact occurred. The requested unique, high-scoring submission remains unachieved.

Current links: [README mission and status](../README.md) · [nine-site download / score / uniqueness / submission guide](nine-site-submission-summary.html) · [normalized mission prompt](MISSION_PROMPT.md) · [JSON run card](../evidence/session_5b3e6982_20261030_run_card.json).

## Pass 1 — task scope, evidence and acceptance criteria

- Re-read `README.md`, `AGENTS.md`, `docs/MISSION_PROMPT.md`, the nine-site report and its input receipts. The user's primary constraints remain: Maximize P(Win), Own the Outcome, no fabricated score or provenance, exact downloads, no human fallback, three review passes, and no upload/slot from this session.
- The report now lists all nine focus sites with their exact immutable TIFF links, pinned hashes, owner-reported values, NOT ESTIMABLE leaderboard estimates, and measured maximum 3-px overlap against the other eight. Each focus champion fails the specified 70% uniqueness comparison. Geometry does not establish copying.
- Each focus-site value is explicitly **OWNER-REPORTED / UNVERIFIED**; all leaderboard estimates are **NOT ESTIMABLE**. No live leaderboard, DrivenData portal, organizer page or submission receipt was freshly checked.
- A GitHub-only freshness receipt checked at 2026-10-30T22:48:16Z reports all 9 priority repositories' `main` refs advanced since the pinned champion audit. Those new heads and their TIFFs were not inspected; the page explicitly labels its table historical. Receipt: `docs/data/priority_feed.json`.
- The summary no longer calls GEO1's recorded holdout a valid result and no longer publishes its DTI/CI as comparable evidence. It distinguishes nine-site uniqueness from the larger local-registry gate, and labels both prior TIFFs **DOWNLOAD: research only · SUBMIT: NO**.
- The B2 analysis retains 0.2778 as an unverified owner claim. Pinned pixel receipts show B2 is a deletion-only 37,654-dot subset of the 44,090-dot GEMSDOE25/GEMSDOE30 D2.8 pattern after removing 6,436 catalogue-adjacent dots; a separate 40,199-dot D2.8-family comparison removes 2,545. Neither adds B2 dots. This supports emission/pruning geometry, not a new detector or a causal explanation of hidden TP/FP mass. See `evidence/oj1_priority_ancestry_replay.json` and `evidence/priority_review_20261025.json`.

## Pass 2 — source, data and metric integrity

### GEO1 holdout is invalid and internally inconsistent

Compared the `code_sha256` values in `evidence/geo1_experiment.json` with the exact current runner and shared evaluator/emitter. The three code hashes match. The source-level trace is:

1. `scripts/build_unique_geothermal_submission.py:149` reads the full catalogue into `catalogue`.
2. At line 250, the fold loop uses `eligible = fp & f["valid"] & ~catalogue` rather than excluding only `f["visible"]`.
3. `src/gems/holdout.py` constructs fold truth as `hidden & valid`; `hidden` is a subset of the full labels. Its `SegmentHoldout` contract says fold-visible catalogue is the only catalogue a detector may read.
4. `src/gems/emission.py` selects emitted cells from the supplied eligibility mask. Under the pinned code path, no hidden label pixel can be emitted; the archived result nevertheless records `TP_w = 10,817.975` and DTI `0.142694916...`.

Thus the source-recorded `HOLDOUT-DTI` `0.142694916...` (claimed evaluator `gems-segment-pooled-v1`, 60,988 withheld positives, claimed 95% CI `[0.132293..., 0.152367...]`) is **REJECTED / INVALID / NOT REPRODUCIBLE FROM THE PINNED ELIGIBILITY PATH**. The exact cause of the result/source discrepancy is not established; the card hash does not prove which bytes were executed. The feature-only canary passing does not repair an eligibility leak. No replay or fix to the historical GEO1 runner was performed. Audit and source hashes: [`evidence/geo1_holdout_leakage_audit_20261030.json`](../evidence/geo1_holdout_leakage_audit_20261030.json).

### Data and uniqueness stops

- Restored `data/training_features.tif` from owner mirror ref `c0c06ac82178f26b94fce3397036ef8f12a2f3a0`, SHA-256 `4371c82e3b8339b807bdffcf4ef59a225520fe2988d521be208ae33743123bc5` (418,912,844 bytes). **Integrity verified; not organizer-authenticated.**
- Rebuilt prepared feature cache: shape `[5167373, 30]`, SHA-256 `a4ca25b2a18f6f6637f0247367cc6235a1366eb8475f77b18cd0285e62232dc8`. Cache inputs and hashes are recorded in `evidence/data_preparation.json`. These checks establish file integrity, not calibrated fault probabilities or organizer provenance.
- The restored bridge `labels.tif` and `existing_faults.tif` hashes are identical (`7ba308cc...`); `sample_submission.tif` is not an independent labeled example.
- The 2026-10-30 necessary-bound receipt covers 5,160,724 / 5,167,373 footprint pixels within 3 px of the retained lattice (99.8713%). For 37,654 dots, the minimum overlap is 31,005 / 37,654 = 82.3418%; for 44,090, it is 37,441 / 44,090 = 84.9195%. Both fail the 70% gate. `22,163` is only the largest budget not ruled out by this bound, not an approved or measured-unique budget. No surface or dots were made. Full receipt: [`evidence/session_5b3e6982_feasibility_20261030.json`](../evidence/session_5b3e6982_feasibility_20261030.json).
- The existing 2026-10-29 complement TIFF has zero overlap against the nine focus files, but its source-recorded local registry audit finds 97.2752% 3-px dot overlap with the retained lattice. The 2026-10-30 preflight found local format/range valid, `official_format_compliant=false`, and `DO_NOT_SUBMIT`. Its HOLDOUT-DTI `0.036939` (evaluator `gems-segment-pooled-v1`, 60,988 withheld positives, 95% CI `[0.030813, 0.043882]`) is a historical internal measurement, not a leaderboard score; it was not rerun.
- Current source records are pinned historical snapshots; this is not a fresh census of all repositories, current peer submissions or live scores.

## Three ranked geological hypotheses — proposals, not a lane assignment

Exact operators below were not found in the inspected executable implementations, but related methods/proposals exist. Novelty is relative to that inspection only—not certified across every branch or external repository. No external source is needed for these three; all listed bands are staged locally. No scores are projected.

| Rank | Specific layers and signature | Why faults may be missed; difference from repository work | Qualitative benefit / cost | Principal mimic |
|---|---|---|---|---|
| 1 | `cond_surf`, `depth_to_base_surf`, `det_elev`, locally derived acquisition-block nuisance proxy (not official flight-block coordinates; source receipt reports ~4.9 px mean figure-boundary residual): fold-local robust null for conductivity conditional on sediment depth, elevation and acquisition block; score a persistent elongated positive residual corridor crossing a basement-depth step. | Blind permeable faults may channel fluids under basin fill with no surface scarp. Existing work includes conductivity Hessian/saddle tests and a documented contour-component-merge proposal; this tests a conditioned basin-fill background residual, not a generic conductivity edge or contour merge. | Medium–high qualitative potential to suppress playa-clay false positives; medium fit, validation and audit cost. | Saline groundwater, playa/lacustrine clay, survey seam. |
| 2 | `iso_grav_anom`, `depth_to_base_surf`, `iso_grav_anom_hg`, optional `det_elev_slope`: remove a depth-conditioned basin-fill gravity null, then detect a signed cross-normal residual edge pair persistent across scales and intersecting a basement step. | Buried basement offsets may be hidden by broad basin-fill mass. Existing work includes potential gradients, Euler solutions, Hessian invariants, cross-gradients and directional variograms; the proposed contrast is an explicit gravity-compensation residual. | Medium qualitative potential; medium–high cost for physical null fitting, stability tests and leakage audit. | Lithologic density contrast, intrusive body, survey leveling seam. |
| 3 | GeoDAWN `K`, `Th`, `U` plus `ThK`/`UTh`: centered-log-ratio coordinates and a multiscale joint compositional covariance/orientation change point, corroborated by an independent basement step. | Blind alteration may leave a multielement transition without a scarp. CRP1/MTR1/SAHG1 use scalar ratios, depletion or individual fronts; this tests the multivariate covariance change itself. Related radiometric work means the novelty claim is deliberately narrow. | Low–medium qualitative potential; medium–high statistical/compute cost and high confounding risk. | Lithologic contact, soil sorting, moisture/vegetation, radiometric survey seam. |

The user's required paragraph assigning one method lane is still absent. None of these is selected. Any future new-data-dependent idea must identify a free official source and verify exact footprint coverage and obtainable bytes before being called viable; no such external-data candidate was promoted here.

## Pass 3 — implementation, tests, documentation and final diff

- `scripts/build_nine_site_report.py` now fail-closes on changed GEO1 audit source hashes, removes the invalid numeric holdout from the page, uses direct immutable `raw.githubusercontent.com` download links, and incorporates the current feasibility/preflight receipts. `--help` now uses `argparse` safely; default generation updates only the HTML and leaves the 2026-10-29 archival run card untouched.
- Regenerated `docs/nine-site-submission-summary.html`. It contains the nine-site table, B2 analysis, prior-artifact decisions, GEO1 integrity explanation, exact feasibility stop, data provenance and a guarded future-submission walkthrough. Its download buttons do not imply submission authorization.
- Updated the README mission/status and `docs/MISSION_PROMPT.md`; added current-session instructions to `AGENTS.md`.
- Added `tests/test_nine_site_report.py` for all nine rows, direct download URLs, score labels, B2 provenance, GEO1 score redaction/source hashes, safe help and preservation of the archival run card.
- **Tests:** after the initial full-suite run exposed 6 historical Git-object lookup failures in this one-commit shallow checkout, `git fetch --unshallow origin main` hydrated history without changing the working branch. The six affected tests then passed; final full suite: **674 passed, 1 skipped**. Focused report tests: **7 passed**. Ruff: **All checks passed**; `git diff --check`: passed.
- **No official external webpages were fetched.** The preserved GitHub-only freshness feed is not a competition/leaderboard/portal check.

## Merge/PR gate

The current branch must stay `arena/5b3e6982-gemsdoe24`. A PR may be opened from this branch after tests and final diff review. Merge only if all checks pass and the change does not weaken any scientific or selector gate. No experiment or submission is authorized by this documentation/code review.
