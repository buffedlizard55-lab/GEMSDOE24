# Standing project instructions

Read the entire root README, its standing owner charter and the **verbatim owner brief**
(`README.md`, section "Owner brief") at the start of every session. Maximize P(Win) and
Own the Outcome, without promising a score or prize.

- **First command of every session: `git fetch origin` and compare `origin/<session branch>` with
  `HEAD`.** On 2026-10-02 the remote session branch already held 12 commits (dotted-H19 validation,
  official road run, derived blocks, score ledger) that the freshly created checkout did not contain.
  Merge them (never force-push) before doing any work, then read `knowledge/05_*` and `knowledge/06_*`.
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
  exact-file audit, or the owner explicitly accepts a declared exception (recorded in
  `registry/submissions.json`). Format green is not gate green. The agent never uploads.
- Keep owner-reported scores, official snapshots, local diagnostics and hypotheses distinct.
  Preserve unknowns, hashes, negative results and source limitations. Scores that appear only in the
  brief (`registry/live_scores.json`, `task_statement_only`) are unconfirmed.
- Keep the first-screen download clear, uniquely named and [0,1]-validated, with
  separate short comment and executive guide. A renamed reference is not new work.
- The dense-catalogue holdout is a different regime from the hidden set (truth density ~5x lower).
  Judge emission/thinning policies on the density-matched sparse simulation first and report the dense
  regime as non-inferiority; on the one independent pair with known scores (h25 -> h28) the dense
  ratio had the wrong sign (-23 %) while the live score rose 44 %.
- Review three times; preserve source links and blocked acceptance items. Do not
  claim a PR, merge or public deployment without evidence. Never request secrets.
- Keep large regenerable inputs/caches out of Git; retain only the small artifacts
  necessary for auditable scientific results.
