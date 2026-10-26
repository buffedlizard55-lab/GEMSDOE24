# Repository review — Arena branch `arena/b7b2f1b6-gemsdoe24` — 2026-10-26

## Executive decision

**No new TIFF or geological experiment was produced in this review. Nothing is authorized to submit.** The required single-method lane paragraph is not present in the active request, so no experiment was assigned or run. The retained spacing-5 calibration lattice also imposes a documented minimum 3-pixel overlap of **82.34%** for a 37,654-dot candidate, above the 70% stop rule. This is a geometric feasibility obstruction at that budget, not a reason to remove controls, move dots, or lower the budget to evade a gate.

**Do not submit the historical H-UNIQUE-03 gapfill TIFF.** Its persisted download/run-card metadata says `promote` and `ok_to_submit=true`, while the same packet's format validator says `ok_to_upload=false` and `submission_authorized=false`, its hash-bound preflight says `DO_NOT_SUBMIT` / `ready_to_submit=false`, and there is no independent selector receipt. The reported `0.601827` value in this contradictory packet is quarantined and is not accepted here as a valid HOLDOUT-DTI result or a leaderboard estimate. Historical input files and their claims were not rewritten.

The documented local point-best is still DPRF1: source-recorded **HOLDOUT-DTI 0.16379**, 95% CI `[0.15045, 0.17739]`, evaluator `gems-segment-pooled-v1`, 60,988 withheld positives. This is not organizer-confirmed, was not independently replayed during this review, and remains `DO_NOT_SUBMIT` under the stored selector. The 0.2778 H33-B2 value and the supplied 0.3195 / 0.4413 leaderboard statements remain unverified owner claims; no defensible hidden-score projection is available.

## Work performed

1. Read the standing project instructions, current README/owner brief, prior portfolio review, corrected research queue, submission validator, site builder and existing tests. The original requested prompt and normalized requirements are already preserved in the README.
2. Inspected the open sibling PR #50 before doing experiments. Its description reports H24-DRAIN5 at **HOLDOUT-DTI 0.16950** (95% CI `[0.15627, 0.18343]`, `gems-segment-pooled-v1`, 60,988 withheld positives), but reports **83.55% 3-pixel overlap with DPRF1**, above the 70% rule. The PR is open, not part of this branch, and is a negative duplicate result—not a downloadable submission recommendation. See [PR #50](https://github.com/buffedlizard55-lab/GEMSDOE24/pull/50); those measurements were not independently replayed here.
3. Corrected two integrity defects without changing historical scientific receipts:
   - The site builder no longer aborts when H-UNIQUE-03's packet contains contradictory promotion records. It renders an explicit quarantine alert and does not link the disputed TIFF as a recommended download.
   - `verify_current_download()` now binds to the documented DPRF1 exact-file metadata, run card and selector, instead of treating the contradictory H-UNIQUE-03 run card as the current download authority. It reopens the TIFF and verifies its hash, format, strict `[0,1]`, grid, count, note and negative selector decision.
   - Updated regression tests to lock the quarantine and DPRF1 identity. Added a narrowly documented Ruff exclusion for the frozen, source-hashed H-UNIQUE-03 runner so formatting cannot silently rewrite historical experiment code; the runner itself was not changed.
4. Kept all research TIFFs, holdout scores, registry contents and historical run cards unchanged. No slot was spent and no DrivenData page was contacted.

## H33-B2: what is and is not known

The pinned artifact audit records a precise mask relationship: H33-B2's 37,654 dots equal the GEMSDOE25/GEMSDOE30 44,090-dot D2.8 set after removing 6,436 dots within 200 m of the public fault catalogue. This supports a *plausible* mechanism: removing catalogue-proximal dots can reduce weighted false-positive cost if the deleted dots contribute little held-out truth credit. It does **not** establish that this deletion caused the owner-reported 0.2778 score. The hidden truth and organizer score decomposition are unavailable. The score-to-file receipt is not authenticated, and copying or further pruning this pattern would not constitute an independent discovery. See the evidence-bounded [metric-integrity review](metric-integrity-20261026.md) and [nine-site executive comparison](portfolio-executive-summary.md).

## Site and submission status

| Item | Evidence-backed status |
|---|---|
| Nine focus sites | Existing portfolio table covers GEMSDOE24/25/27/28/30/31/32/33/36. Historical scores are explicitly unverified owner claims; estimated leaderboard scores are not estimable. |
| DPRF1 download | Exact file is format-valid and finite in `[0,1]`, SHA-256 `c1257c1d4b5ac9cc0a8e29b0120c614fcaa1f38474bc1f6de98c0a1afb0567f1`; research download only, selector `DO_NOT_SUBMIT`. |
| H-UNIQUE-03 gapfill | **Quarantined.** Conflicting positive metadata; missing selector; its preflight is a negative decision. Do not download for competition submission. |
| Organizer score / live quota | None authenticated. No upload or automated DrivenData access was attempted. |
| External-source validation | The research leads remain official references, but this sandbox can only reach GitHub/codeload and package registries; no new USGS/NLR/DrivenData source fetch was performed. |

## Verification — three passes

- **Pass 1 — inventory and baseline:** reviewed the repo and open PR context, traced the contradictory H-UNIQUE-03 receipts, confirmed no method paragraph was assigned, and did not run a geological experiment.
- **Pass 2 — correction and edge cases:** quarantined contradictory site metadata instead of allowing a TIFF link or breaking site generation; made exact-file verification point at DPRF1's recorded metadata/card/selector; added regression checks for mismatch and unsafe statuses.
- **Pass 3 — recheck:** full suite **451 passed**; `ruff check src scripts tests` passed; `ruff format --check src scripts tests` passed (**180 files**); compileall and `git diff --check` passed; the site-build tests successfully generated a scratch copy and confirmed the H-UNIQUE-03 TIFF is absent from the recommended page output. `scripts/verify_current_download.py` returned format valid, `ok_to_download=true`, `ok_to_submit=false`, `submission_authorized=false`, verdict `negative` for the exact DPRF1 research file.

The tests establish repository behavior, not scientific replay, novelty against every newly changed peer artifact, competition portal acceptance, or leaderboard performance.

## Next actions and blockers

1. Reconcile PR #50 and other open sibling work through the repository owner; do not cherry-pick or merge a sibling branch from this session. Rebase/review against updated `main` before opening or merging a follow-up.
2. Obtain an explicit, single-method lane paragraph before another experiment. Preregister one untried, cache-ready hypothesis from the corrected queue in `knowledge/26_portfolio_plan_corrections_2026-10-26.md`; run its feature-alone leakage canaries and surface-level novelty tests before dot placement, then apply the literal registry stop to final dots.
3. Resolve the standard-budget lattice obstruction through a prospectively approved policy change—not by deleting controls or evading the limit. Until then, no standard-budget unique candidate can pass.
4. Keep all score claims separate: HOLDOUT-DTI with evaluator, withheld count and CI; organizer-confirmed only with an artifact-linked receipt. No numeric hidden-score estimate is supportable.
5. A real submission still requires an independently replayed scientific selector and current account allowance, followed by the user's own portal action. A local format pass is not organizer acceptance.

### Official/manual-review links

- [DrivenData competition and rules](https://www.drivendata.org/competitions/306/competition-doe-gems/)
- [DrivenData problem and metric page](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [DrivenData about/resources](https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/)
- [DrivenData data page (login required)](https://www.drivendata.org/competitions/306/competition-doe-gems/data/)
- [Official reference solution](https://github.com/drivendataorg/gems-prize-reference-solution)
- [DOE/NLR competition rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf)
- [USGS GeoDAWN survey record](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
- [USGS 3DEP data tools](https://www.usgs.gov/3d-elevation-program/data-tools)
- [INGENIOUS project](https://gbcge.org/current-projects/ingenious/)
- [EPSG:32611](https://epsg.io/32611)
