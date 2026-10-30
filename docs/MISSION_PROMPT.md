# GEMSDOE24 — active mission prompt (normalized, 2026-10-30)

**Read this file, the complete root `README.md`, and `AGENTS.md` at the start of every session.** This is the operative summary of the current task and its corrections; it does not replace the user's actual request. Start with this branch's [three-pass review](repo-review-20261030-arena-5b3e6982.md) and [negative JSON run card](../evidence/session_5b3e6982_20261030_run_card.json); also read the [latest merged nine-site review](repo-review-20261030-arena-9b32516e.md) and [run card](../evidence/session_9b32516e_20261030_run_card.json), the [merged companion review](repo-review-20261030-arena-6a29c5b2.md) and [run card](../evidence/session_6a29c5b2_20261030_run_card.json), and the [current-source snapshot](current-source-snapshot-20261030.md). Earlier branch references are historical.

## Objective and scope

Review GEMSDOE24, GEMSDOE25, GEMSDOE27, GEMSDOE28, GEMSDOE30, GEMSDOE31, GEMSDOE32, GEMSDOE33, and GEMSDOE36. Keep a clear per-site executive table of exact historical downloads, evidence class, uniqueness status, and explicit download/submit decisions. The goal is a genuinely novel, scientifically defensible high-performing GeoTIFF, but **generation is conditional on the assigned method lane and every prospective gate passing**. A forced output, copied raster, or weakened comparator is not success. Keep the site's downloadable research/review guide easy to use and describe the safe submission workflow.

## Evidence and score language

- A scientific result is labeled **HOLDOUT-DTI** only with its evaluator/version, withheld-positive count, and 95% confidence interval. State whether it is a recorded artifact verification or a fresh replay.
- A competition result is **ORGANIZER-CONFIRMED** only when an artifact-linked submission receipt from the organizer is present.
- Owner-reported standings, source README text, internal projections, holdout values, and file-format checks are **not** organizer scores. If no admissible estimate exists, write **NOT ESTIMABLE**.
- Preserve source links, immutable refs, hashes, limitations, and negative decisions. Do not infer current score or artifact status from a changed GitHub commit.

## Lane, validation, and novelty gates

- Stay within the single assigned method paragraph. If it is absent, do not invent a lane or restart stopped work.
- Reuse the shared feature stack, `scripts/evaluate_holdout.py`, and `scripts/submission_writer.py`. Hold out buffered whole fault segments; derive catalogue features only from visible faults; apply the visible-fault mask exactly; pool DTI with α=0.2, β=0.8, and the 300 m triangular kernel.
- Test each actual feature and transform alone for leakage. Treat AUC >0.90 as suspected leakage until disproven.
- Check the pre-placement surface and final dots against the complete comparable registry. Stop if absolute rank correlation >0.90 or >70% of candidate dots are within 3 px of any registry raster. Do not tune a stopped budget, move dots to evade the rule, or alter/remove the registry or comparator.
- Limit work to three experiments or two hours. Preserve negative results. A weekly slot requires a separate selector, independently verified quota, and a comparable current-best improvement meeting the requested 2–3% threshold; no slot or upload is authorized by this prompt.
- Rank 3–5 hypotheses before implementation. For each, name the exact data layers and transform, fault-recovery mechanism, distinction from prior methods, non-fault mimics, qualitative expected benefit/cost, and verified free-data availability. If source access is not verified, mark the idea blocked—not viable.

## Artifact requirements (only after all science and novelty gates pass)

- Produce a genuinely new single-band GeoTIFF, never a copied earlier prediction. Validate finite, in-footprint values in [0,1], and exact template CRS, shape, and transform (expected template: EPSG:32611, 3730×3292, 100 m). Record a unique filename, exact SHA-256, and a note of at most 140 characters.
- State **DOWNLOAD: research only** or **DOWNLOAD: submission candidate** and **SUBMIT: YES/NO** separately. A local validator does not guarantee organizer acceptance; explain exterior-footprint encoding uncertainty rather than guessing the cause of a portal error.
- Do not use human inspection as a fallback. The project agent never automates DrivenData access or uploads; keep portal steps user-controlled and require an artifact-linked receipt for any claimed score.

## Current evidence snapshot — 2026-10-30

- The refreshed owner-site scan retrieved 92/92 GitHub READMEs at immutable refs. The 118 historical owner-reported claims carried in the inventory are parsed from the preserved 2026-10-26 brief, not extracted from those refreshed README bodies; zero organizer-confirmed receipts were recorded. This is not an artifact audit or score verification.
- A GitHub API commit-ref check at `2026-10-30T23:30:42Z` found all nine focus `main` refs changed since their pinned artifact-review refs; GEMSDOE24 and GEMSDOE30 advanced again after the 23:11 README snapshot. The changed heads and files were not audited here. This is source freshness only, not a current artifact, score, or submission check; see [`docs/data/priority_feed.json`](data/priority_feed.json).
- The nine pinned historical champions were reopened and locally checked. None is authorized for submission; their per-site filenames, raw download links, owner-claim labels, hashes, format limits, and lattice overlaps are in [`docs/historical-champions.html`](historical-champions.html) and [`docs/data/historical_champions_20261028.json`](data/historical_champions_20261028.json). These are historical artifacts, not latest-head endorsements.
- The fixed retained-lattice necessary bound returns `STOP_IMPOSSIBLE_BUDGET` at 37,654 and 44,090 dots. This is a stop, not a target for budget tuning. No candidate TIFF, experiment, or submission slot was created/used in this review.
- Recorded `H24-S3DEP1` HOLDOUT-DTI is 0.1660601364 [0.1518583912, 0.1803388646], evaluator `gems-segment-pooled-v1`, 60,988 withheld positives. `--verify-recorded` verifies its pinned artifact and selector receipt, not a fresh scientific replay; its decision remains `DO_NOT_SUBMIT`.
- No artifact-linked organizer receipt or current official leaderboard snapshot was obtained. Leaderboard estimates remain **NOT ESTIMABLE**. No TIFF is approved to submit.

## Current branch audit addendum — 2026-10-30

- GEO1's archived HOLDOUT-DTI is **INVALID_HOLDOUT_CLAIM** because fold eligibility uses the full catalogue, including hidden labels; the nonzero recorded TP count is inconsistent with that path. Its DTI/CI cannot be used for ranking or promotion. The exact source/evidence hashes are pinned in `../evidence/geo1_holdout_leakage_audit_20261030.json`.
- The 37,654- and 44,090-dot budgets are stopped by the spacing-5 retained-lattice necessary bound (82.3418% and 84.9195% minimum overlap, respectively). The complement research raster's 97.2752% local-lattice overlap independently makes it `DO_NOT_SUBMIT`, despite 0% overlap against the nine historical focus files.
- B2's 0.2778 is only OWNER-REPORTED / UNVERIFIED. The pinned 6,436- and 2,545-dot deletions are geometric ancestry comparisons, not evidence of hidden positives or score causality.
- The session run card is negative: 0 experiments, no new candidate TIFF, no portal upload, holdout and final-dot tests `NOT RUN`, 0 slots. Its historical complement HOLDOUT-DTI is reported separately and was not rerun. No hypothesis was selected or executed because the assigned method lane remains absent.
- The report labels all leaderboard estimates NOT ESTIMABLE, distinguishes research downloads from submit authorization, and preserves the exact historical filenames and hashes. The source-freshness check did not audit current files or scores.

## Session-start and closeout

Read the README, this prompt, `AGENTS.md`, the latest review, and its run card before work. Inspect `git status` before editing. Run three adversarial review passes (implementation/evidence review, bug-and-assumption review, then original-request audit); test and lint relevant changes. Open and merge a PR only after checks pass. Core values: **Maximize P(Win)** and **Own the Outcome**.
