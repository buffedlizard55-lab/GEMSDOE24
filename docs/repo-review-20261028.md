# Repository review — 2026-10-28

**Decision: research-only downloads; no TIFF is authorized to submit.** This was a read-only review at `a73f9ff` on the fixed branch `arena/23763912-gemsdoe24`. No experiment, raster, score estimate, upload, or slot was created/used. The operative single-method paragraph is still missing, so selecting a geological lane would violate the parallel-run protocol.

## Executive findings

1. **No actionable “best submission” is established.** The nine-site audit at `evidence/current_focus_nine_file_audit_20261027.json` explicitly says it covers one selected source-featured TIFF per site at pinned feed refs, not every current TIFF; it did no scientific replay, pre-placement surface comparison, or leaderboard access. Its nine rows all say `ok_to_submit: false`; their recorded 3-pixel lattice overlaps range from 99.0466% to 100%. Those are specific duplicate-gate failures against the retained lattice, not proof that every possible submission is duplicate.
2. **The current comparison cannot be refreshed from this checkout.** `docs/data/portfolio_freshness.json` is timestamped `2026-10-27T19:18:47Z` and reports all nine focus repositories changed since their pinned review refs. Consequently, it cannot support claims about each site's newest artifacts today. The freshness feed is GitHub-source freshness only, not a scoring/leaderboard feed.
3. **Scores are correctly not projected.** The nine-site audit labels its local measurements `SOURCE-RECORDED`, not replayed and not organizer-confirmed. For example, GEMSDOE36's recorded HOLDOUT-DTI is `0.170100...` with CI `[0.155089..., 0.186138...]`, but the audit itself says the protocol is not independently validated and its artifact fails the lattice gate. H33-B2 `0.2778` and the prompt's `0.3195` / `0.4413` leaderboard claims remain unverified; the repository has no defensible hidden-score estimate.
4. **Data/training are not currently executable here.** `data/bridge/sample_submission.tif` and small bridge labels are present, but `data/training_features.tif` and prepared feature cache are absent (also stated in `knowledge/owner_brief_2026-10-27_active.md`). The runtime has Python 3.11.2 but neither NumPy nor pytest. The owner-supplied GitHub mirror is not organizer authentication. Do not claim training or scientific holdout replay in this environment.
5. **The protocol feasibility receipt is reproducible and conservative.** `python scripts/check_protocol_feasibility.py --dots 37654` yields a necessary-only minimum lattice overlap of 82.3418% and `submission_authorized: false`; this is arithmetic on a frozen audit, not a new raster measurement or a score. The companion raster-backed uniqueness checker cannot run here because NumPy/rasterio are missing. A 18,000-dot budget is merely not ruled out by this one bound, not approved and must not be chosen just to evade the lattice.
6. **No confirmed code defect was demonstrated in this pass.** Python `compileall`, `git diff --check`, and Node syntax check for `docs/assets/app.js` passed. The focused protocol feasibility unittest module passed 6/6. `pytest` tests and scientific suites were not run: pytest/NumPy/rasterio are unavailable. The attempted unittest import of the pytest-dependent uniqueness tests failed for that missing dependency; this is an environment limitation, not a passing test.

## Review passes

### Pass 1 — map the project and reproduce the principal guardrail

Read the root README, `AGENTS.md`, current owner brief, current integrity review, executive page, freshness feed, the nine-site audit, and both feasibility scripts. Confirmed working tree clean at start and fixed branch `arena/23763912-gemsdoe24`; `git fetch origin` completed. GitHub PR listing showed overlapping open work, including PR #70 (CGMK1 / signed geophysics and potassium ideas) and PR #61 (B2 investigation). This review therefore adds no parallel experiment and does not alter/merge another lane.

Ran:

- `python scripts/check_protocol_feasibility.py --dots 37654` — emitted the frozen-receipt result above.
- `python -m unittest discover -s tests -p 'test_protocol_feasibility.py' -v` — 6 tests passed.
- `python -m compileall -q src scripts` — passed.
- `git diff --check` and `node --check docs/assets/app.js` — passed.

### Pass 2 — challenge stale, misleading, and edge-case claims

- The freshness timestamp predates this review date, and all nine rows already report newer source heads than the pinned artifact reviews. Do not render these rows as “latest submission” or use their historical best entries as current winners until a fresh repository audit is done.
- The current exact-file table is deliberately a *selected-file* audit, not an exhaustive registry census. A lattice failure suffices for a negative verdict; a lattice pass alone would not prove uniqueness.
- `check_protocol_feasibility.py` explicitly uses frozen audit counts and exact rational comparison. Its output is bounded to necessary geometry. `check_uniqueness_feasibility.py` additionally reopens pinned rasters and is the stronger check, but currently cannot be executed in this runtime.
- `scripts/refresh_source_feed.py` documents a policy that excludes automatic DrivenData requests; its leaderboard input is human-saved. No DrivenData page or score was accessed in this review. Outbound hosts are constrained by the execution environment; no new USGS/NLR/OpenEI dataset access was attempted.
- The pytest invocation failed because pytest is not installed; NumPy is also absent. No test failure should be re-described as a scientific result.

### Pass 3 — original-request acceptance check

The repository already contains the prominent executive summary and machine-readable nine-site table, exact download links, automated `[0,1]`/grid validation artifacts, and a detailed submission guide. But there is **no current authorized unique TIFF**, no current all-nine source-head artifact audit, no valid current leaderboard projection, and no successful science replay in this runtime. Those are blockers, not work completed by this review. The review leaves them visible and does not manufacture a TIFF or a numerical score estimate.

## Recommended next work

1. Resolve coordination first: supply the exact assigned one-paragraph method and prospectively settle how the literal 70%/3-pixel gate treats the known space-filling lattice. Do not change the gate, budget, or comparator after seeing a candidate.
2. Reconcile the open PRs and evaluate their test/merge status before repeating any ideas they contain. Keep the fixed Arena branch; do not work on their branches.
3. Restore the permitted feature stack from its pinned source, record source hashes and provenance, and install the locked project/test dependencies. Authentication-gated competition data must remain clearly distinguished from an owner mirror.
4. Refresh GitHub source heads, then audit the exact current artifact and its receipts for all nine sites before updating the executive table. Continue to label historical scores and local holdouts by evidence type.
5. Only after lane assignment and a valid data environment: preregister, reuse the shared holdout/writer, run feature-alone leakage canaries, compare pre-placement surface and final dots against the complete registry, and stop at the stated budget. Promote only through the separate selector; a format-valid TIFF is not upload authorization.

## Reproduction and source links

- [Current executive summary](executive-summary.html#current-focus-files)
- [Pinned nine-site exact-file receipt](../evidence/current_focus_nine_file_audit_20261027.json)
- [GitHub-only freshness snapshot](data/portfolio_freshness.json)
- [Current normalized owner brief](../knowledge/owner_brief_2026-10-27_active.md)
- [Current integrity and protocol review](../knowledge/31_current_integrity_review_2026-10-27.md)
- [Protocol feasibility page](protocol-feasibility-20261027.md)
- Competition official problem/format references supplied in README: <https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/> and organizer reference code: <https://github.com/drivendataorg/gems-prize-reference-solution>. Links are references only; this session did not fetch DrivenData.
