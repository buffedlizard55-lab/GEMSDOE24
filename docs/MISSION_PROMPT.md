# GEMS DOE 24 — Current Mission Prompt (normalized summary)

**Current checkout status — follow-up review 2026-10-30, branch `arena/50bd576c-gemsdoe24`:** No new TIFF, scientific experiment, holdout, leaderboard estimate or competition slot was produced. The single-method paragraph required to assign the parallel-run lane is absent; the full competition feature raster/prepared cache is also absent. Do not invent a lane, bypass the stop gates, or label any file safe to submit. See the [GEO1 holdout-integrity correction](geo1-holdout-integrity-review-20261030.md), [nine-site report](nine-site-submission-summary.html), and [negative JSON session card](../evidence/session_50bd576c_20261030_run_card.json). Project dependencies were installed in an ignored local `.venv`; the full test suite passes, but absent competition inputs and the unassigned lane still preclude a scientifically valid fresh raster/holdout. The historical nine-site table and all owner-reported score claims remain historical, and hidden leaderboard scores are **NOT ESTIMABLE**. No file is cleared to submit.

**Parallel GitHub-feed review on this date:** Read the [three-pass review](repo-review-20261030-arena-9b32516e.md) and [run card](../evidence/session_9b32516e_20261030_run_card.json). Its GitHub-only feed found all nine focus repositories' `main` refs advanced since the pinned artifact audit; it did not audit new files or scores. This follow-up preserves that distinction.

**Earlier review on this date:** The [three-pass review](repo-review-20261030-arena-6a29c5b2.md) and [run card](../evidence/session_6a29c5b2_20261030_run_card.json) accurately record the runtime dependencies absent at that earlier point. The follow-up installed dependencies for code/test verification; it did not restore competition data or run a model.

**Source task context:** historical normalized summary, last corrected 2026-10-29; branch references in earlier session notes are historical. Read the actual current request and README as well.

## Objective
Place top of the DrivenData GEMS competition leaderboard (https://www.drivendata.org/competitions/306/competition-doe-gems/) by generating a **unique TIF submission** and publishing an executive summary that makes the best submission obvious and downloadable.

## Focus sites
GEMSDOE24, GEMSDOE25, GEMSDOE27, GEMSDOE28, GEMSDOE30, GEMSDOE31, GEMSDOE32, GEMSDOE33, GEMSDOE36.

## Hard requirements (must all hold)
1. **MUST generate a unique TIF submission.** Do not copy a previous submission. It must be obvious whether the generated TIF is OK to download and submit.
2. Easy-to-download submission TIF (one click). Investigate the reported "Predicted values must be in range [0, 1]" portal rejection. A zero-outside variant passes a strict whole-array range check locally, but its acceptance and the cause of the rejection are not established; it differs from the sample's NaN-outside convention.
3. Unique name + short note (<= 140 characters).
4. Executive summary on every focus site; a table listing: file to download, estimated score, whether unique vs the other GEMSDOE sites.
5. Executive summary subpage explaining exactly how to make a submission.
6. Validation through the project, no human intervention: no NaN inside footprint, values in [0,1], CRS/shape/transform match template (EPSG:32611, 3730x3292 @100 m).
7. Put this prompt into the repo README and re-read it each session.
8. Create a PR and merge onto main.
9. No hallucinations; work line by line; official verified sources; flag irregularities.

## Evidence rules (parallel-run protocol)
- Label every number HOLDOUT-DTI (evaluator version, # withheld positives, 95% CI) or ORGANIZER-CONFIRMED (organizer receipt). A projection is never written as a score.
- Leakage canary: any feature alone with AUC > 0.90 = leakage until proven otherwise.
- Uniqueness: raster rank-correlation <= 0.90 with any registry raster AND <= 70% of dots within 3 px of any one registry raster's dots (surface before placement AND final dots).
- Holdout = hide-and-recover: withhold whole fault segments with buffer, catalogue features from visible faults only, pixel-exact masking, pooled DTI (alpha 0.2, beta 0.8, 300 m triangular kernel).
- End with one JSON run card: hypothesis; mechanism; named non-fault mimic; holdout DTI + CI; correlation/overlap vs registry; raster sha256; validator output; submission name + <=140-char note; verdict promote/negative.
- Budget: stop after 3 experiments or 2 hours. No submission slot spent without a selector step.

## Historical state (2026-10-28; source-recorded; recheck before use)
- Owner-reported historical highs (GEMSDOE32 B2 0.2778, GEMSDOE36 Anderson 0.2750, etc.) are **NOT organizer-confirmed**; no DrivenData auth is available, so live scores are NOT ESTIMABLE.
- The retained spacing-5 lattice covers approximately 99.87% of the footprint within 3 px. The geometric lower bound exceeds the 70% limit for any set of at least 22,164 distinct in-footprint dots; at 37,654 dots it is about 82.34%. Smaller budgets are not ruled out by this bound alone and are not certified unique. Do not evade the gate by targeting lattice holes.
- Research-only VENTRAD candidate: `docs/downloads/24GEMSDOE-ventrad-blind-geothermal-20261028-34b558b554fb-zero.tif` (SHA-256 `603d21db…9626`), 37,722 dots, source-recorded HOLDOUT-DTI 0.1223 [0.1111, 0.1337] (`gems-segment-pooled-v1`, 60,988 withheld positives). A narrow 10-method comparison is not the protocol registry test: the required retained-lattice overlap is 0.99817 (>0.70), so protocol uniqueness FAILS. The candidate is format-valid, `ok_to_download: YES`, `ok_to_submit: NO`; no slot was spent. Its measurement was not independently replayed in the current review.

## Off-limits / do-not
- Do not claim an unverified score is organizer-confirmed.
- Do not restart stopped lanes or retune dots to evade the literal overlap gate.
- Do not spend a weekly submission slot; no organizer auth is available in this environment.
- No new TIFF is "submission-authorized" by a format pass alone.
