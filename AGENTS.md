# Standing project instructions

**CUP1 continuation (2026-10-26):** Read `knowledge/20_preregistered_CUP1_2026-10-26.md`,
`knowledge/21_CUP1_findings_2026-10-26.md` and `evidence/cup1_run_card_20261026.json` first.
CUP1 (HOLDOUT-DTI 0.15038, new point best) is DOWNLOAD YES / SUBMIT NO: paired CI vs matched
B-GVC crosses 0 and 91.2% of dots sit within 3 px of parent GVC1. Do not rerun/retune CUP1,
and do not propose another GVC18+HGB increment — it will converge to the same dots. Next lane
must be an orthogonal surface family, judged on SegmentHoldout **and** SGMC-sparse; the
independent selector/quota certificate is still missing and blocks any SUBMIT YES.

**OJ1 continuation (2026-10-25):** Read `knowledge/17_preregistered_OJ1_2026-10-25.md`,
`knowledge/18_OJ1_findings_2026-10-25.md`, and `evidence/oj1_run_card_20261025.json` first.
OJ1 stopped as duplicate-final-dots (spacing-5 control retained), loses the recorded
OOF baseline, and is DOWNLOAD YES / SUBMIT NO. Do not rerun or retune it.
Historical UNIQUE01/02/03, CON and FUSE entrypoints are retired; source/evidence
remain for education. UNIQUE03 executed a 30 km decay, not its advertised 300 m;
its proximity/composite canaries were not run. Never present it as catalogue-independent.
Shared preflight schema v2 refuses to authorize from promote booleans alone;
independent selector verification is missing, not a human-inspection pending state.


**Current precedence (2026-10-25):** read `knowledge/owner_brief_2026-10-25.md`
and the current README decision first. It is also embedded in README. The
current brief supersedes historic requests to submit reference subsets or seek
an owner/human inspection exception. Read
`knowledge/09_preregistration_magnetic_trough_2026-10-25.md` and
`evidence/mtr1_run_card.json`. The lane STOPPED as duplicate under the literal
overlap rule: a registered spacing-5 lattice covers the supported domain at
radius 3. Do not remove it after the fact, retune this lane or label the negative
TIFF submit-ready. No old submission pixels may enter a new detector.

- Current shared evaluator: `gems.holdout.SegmentHoldout` /
  `scripts/evaluate_holdout.py`: whole components hidden everywhere, buffered
  spatial quadrants, visible-only catalogue features/masks, POOLED metric
  components, versioned HOLDOUT-DTI with positive count and 95% CI.
- Current shared writer: `gems.submission` / `scripts/submission_writer.py`.
  File validity never sets `ok_to_upload=true`. Separate selector required.
- Test every actual source/transform alone for leakage, both AUC polarities.
- Pre-placement and final registry checks; exact raw rank correlations and
  all-dot directional overlap. Exceed .90 rank or .70 overlap at <=3 px => STOP.
- At most 3 experiments or 2 hours/session. Current stopped session ran 1.
  Negative results are deliverables, not a reason to keep searching.
- No ORGANIZER-CONFIRMED result without an artifact-linked submission-page
  receipt. Current leaderboard claims conflict and remain unverified.

The older instructions below remain for historical reproduction where they do
not conflict with that current protocol.


**Concurrent main work preserved:** PRs #9/#10 landed during this lane. Read
`knowledge/09_preregistered_ASPC_2026-10-25.md` and
`knowledge/10_ASPC_findings_2026-10-25.md` as well. ASPC's negative run, code,
receipts and downloads remain intact; it is not a substitute for a comparable
current-best OOF baseline. Do not rerun either recorded lane. Both share the
central evaluator/novelty/writer implementation; their declared fold/buffer/CI
policies and pinned registry scopes differ. Keep those differences explicit.

**2026-10-25 H24-SAHG1 and OOF baseline packet (`knowledge/12_preregistered_SAHG1_2026-10-25.md`, `knowledge/13_SAHG1_findings_2026-10-25.md`):**
Executes the Next-work items from PRs #10 and #11 (`src/gems/sahg1.py`, `scripts/run_sahg1_lane.py`,
`evidence/sahg1_run_card_20261025.json`):
- Prospective novelty check `gems.novelty.compare_prospective_registry(...)` separates synthetic
  calibration controls (`registry-039` spacing-5 lattice, `registry-044` zero placeholder) from
  competing method lanes while preserving `compare_registry(...)` and literal all-entry flags.
- Reconstructed same-protocol out-of-fold multi-physics baseline (`oof_multiphysics_hgb_d3`,
  `gems-segment-pooled-v1` HOLDOUT-DTI `0.13000`, 95% CI `[0.11565, 0.14396]`).
- `H24-SAHG1` achieves HOLDOUT-DTI `0.09672` (`[0.08657, 0.10703]`) on `gems-segment-pooled-v1`
  and `0.09655` (`[0.08270, 0.10976]`) on `segment-hide-recover-pooled-v1`, beating `MTR1`,
  `ASPC`, and its own geomorphic ablation `G_0` (`+0.01012`), passing prospective method-lane
  novelty (`46/46` method lanes, `83/83` peer blobs), and running the exact-file C2ST audit
  (`AUC 0.5826`). Remains `DOWNLOAD: YES · SUBMIT: NO` (`verdict: "negative"`). Verify with
  `.venv/bin/python scripts/run_sahg1_lane.py --verify-recorded`.

**2026-10-25 H24-FUSE residualized conduit OOF-HGB packet (`knowledge/17_preregistered_FUSE_2026-10-25.md`, `knowledge/18_FUSE_findings_2026-10-25.md`):**
Executes documented Next Step #4 (`scripts/run_fuse_lane.py`, `evidence/fuse_run_card_20261025.json`):
- Evaluates three preregistered 31-channel fold-local `HistGradientBoostingClassifier` arms (`FUSE-RAW`,
  `FUSE-RESID`, `FUSE-HCW`) fusing the 27 prepared physical/LiDAR/DEM channels with `SAHG1`'s `G_sat`,
  `R_alt`, `B_step`, and `H_conduit` inside a verified 9×9 support mask.
- Shows that unresidualized `FUSE-RAW` matches `0.13000` (`0.12995`) but fails prospective method-lane
  novelty (`0.7399 > 0.70` vs. `registry-006`).
- Shows that training-only `NuisanceResidualizer` (`FUSE-RESID` `0.12210`, `FUSE-HCW` `0.12372`) reduces
  exact-file C2ST AUC from `0.5826` down to `0.4928` / `0.5108` (`< 0.55`, Holm `p = 0.870`), passes
  prospective novelty across all 49 competing method rasters (`0.6315 <= 0.70`) and 83 peer blobs
  (`0.6025 <= 0.70`), and beats `SAHG1` (`+0.02701`), `ASPC` (`+0.02798`), `CON` (`+0.05926`), `MTR1`
  (`+0.05931`), and `H-UNIQUE-03` (`+0.06988`). Remains `DOWNLOAD: YES · SUBMIT: NO` (`verdict: "negative"`).
  Verify with `.venv/bin/python scripts/run_fuse_lane.py --verify-recorded`.

Read the entire root README, its standing owner charter and the **verbatim owner brief**
(`README.md`, section "Owner brief") at the start of every session. Maximize P(Win) and
Own the Outcome, without promising a score or prize.

- **First command of every session: `git fetch origin` and compare `origin/<session branch>` with
  `HEAD`.** On 2026-10-02 the remote session branch already held 12 commits (dotted-H19 validation,
  official road run, derived blocks, score ledger) that the freshly created checkout did not contain.
  Merge them (never force-push) before doing any work, then read `knowledge/05_*` and `knowledge/06_*`.
- **Second command: `gh pr list --state open` and `git ls-remote --heads origin 'arena/*'`.** A sibling Arena session of the same
  account can run in parallel from the same base commit: on 2026-10-02 branch `arena/01a0fd2e-gemsdoe24` opened PR #7 minutes after
  this repository's PRs #5/#6 merged, and it conflicts in 20 files. Read any open PR before starting, do not duplicate its
  experiments, never push to a sibling's branch, and re-fetch `origin/main` before opening your own PR. If a sibling PR conflicts
  with `main`, report it (`knowledge/08_parallel_session_pr7_2026-10-02.md`); never resolve it by overwriting `main`'s README, site,
  audit or compliance files, and never merge a PR whose base predates `main`'s compliance fix without rebasing it first.
- Use the active pipeline and evidence; legacy scripts/reports are historical,
  not promotion authority.
- Preregister hypotheses before implementation (commit the preregistration *before* the run). Do not
  silently tune outer folds, change a negative result into a new success, or select among operators
  on the same draws that confirm them.
- Audit labels first using only the required nuisance families (roads, claims, four acquisition
  blocks). The block raster is **derived from an official figure and audited against published
  line-km; it is not official coordinates** - keep that label wherever it is used.
- Fit nuisance removal/scaling on training-region data only; refit and re-audit
  the exact emitted candidate. Association is not causation.
- No weekly slot unless the candidate beats the CURRENT comparable holdout best and passes the
  exact-file audit, uniqueness gates and separate selector. The current charter does not permit
  the historical human/owner-exception shortcut. Format green is not gate green. The agent never uploads.
- Keep owner-reported scores, official snapshots, local diagnostics and hypotheses distinct.
  Preserve unknowns, hashes, negative results and source limitations. Scores that appear only in the
  brief (`registry/live_scores.json`, `task_statement_only`) are unconfirmed.
- Keep the first-screen download clear, uniquely named and [0,1]-validated, with
  separate short comment and executive guide. A renamed reference is not new work.
- The dense-catalogue holdout is a different regime from the hidden set (truth density ~5x lower).
  Judge emission/thinning policies on the density-matched sparse simulation first and report the dense
  regime as non-inferiority; on the one independent pair with known scores (h25 -> h28) the dense
  ratio had the wrong sign (-23 %) while the live score rose 44 %.
- **Never automate access to drivendata.org** (leaderboard, forum, data, submission pages): its Terms of Use forbid any robot/automatic device
  "for any purpose, including monitoring", and the prize rules bind competitors to them. Leaderboard rows are human-read snapshots
  (`scripts/refresh_source_feed.py --leaderboard-file`); tests enforce this. The agent never uploads submissions.
- Review three times; preserve source links and blocked acceptance items. Do not
  claim a PR, merge or public deployment without evidence. Never request secrets.
- Keep large regenerable inputs/caches out of Git; retain only the small artifacts
  necessary for auditable scientific results.
