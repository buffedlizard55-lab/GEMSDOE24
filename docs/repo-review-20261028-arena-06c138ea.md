# Repository review — 2026-10-28 (`arena/06c138ea-gemsdoe24`)

## Executive decision

**NO NEW TIFF · NO NEW EXPERIMENT · NO COMPETITION SLOT · NO SUBMISSION AUTHORIZATION.** The requested higher-scoring, unique competition submission is not achieved. This review ends negative rather than presenting an untested artifact as ready to submit.

The repository has a substantial research and delivery framework: a nine-site executive guide, documented historical artifacts, shared holdout/novelty/format tooling, an automated site builder, data provenance records, and test coverage. None of these alone demonstrates organizer acceptance or leaderboard performance. I did not upload a file, spend a slot, run a geological experiment, or create a TIFF.

## Current checkout and project data

- The active branch is `arena/06c138ea-gemsdoe24` at `9e185929eeaa6244f96c3022cf3462faa8ca4de0`; it initially matched `origin/main` and had a clean worktree. Git initially reported a shallow checkout. I fetched the full history from `origin` because historical-receipt tests require referenced commits. This did not switch branches or alter tracked files.
- The organizer-mirrored bridge rasters are present: `data/bridge/sample_submission.tif`, `existing_faults.tif`, and `labels.tif`. Additional compact external/derived layers are present under `data/external/`.
- **`data/training_features.tif` and the prepared `data/geofeat/` cache are absent.** Consequently the cached-feature holdout and per-feature leakage canaries could not be rerun. The presence of smaller bridge or owner-mirrored layers does not supply the missing full training stack or independently authenticate source provenance.
- `docs/downloads/` contains 62 existing TIFFs. Their presence is not a current audit, a fresh scientific result, or permission to submit. Existing research-only/negative artifacts remain governed by their run cards and selectors.
- The exact shared-user request is already embedded in the long historical section of `README.md`; `docs/MISSION_PROMPT.md` is its normalized summary. The README is roughly 3,585 lines, with repeated historical prompts and branch-specific notes. Preserve that archive, but use a short current-status link at the top (updated in this review) rather than appending another duplicate prompt.

## Protocol gates and uniqueness feasibility

The parallel-run protocol restricts this session to a single assigned method paragraph. No such assigned paragraph is present in the active instructions. The existing four-item research queue is explicitly prospective and not a lane assignment; two ideas are also marked as overlapping open/concurrent work. I therefore did not select a hypothesis, generate a surface, or run a holdout.

I ran the read-only shared feasibility checker against the pinned lattice witness and the standard diagnostic budgets. The result is a **geometric feasibility bound, not a score, candidate measurement, proof of copied geology, or full-registry novelty audit**:

| Diagnostic | Result |
|---|---|
| 3-pixel lattice neighborhood coverage | 99.8713% of the template footprint |
| K = 37,654 distinct in-footprint dots | At least 31,005 overlap; minimum 82.3418%, above the literal 70% ceiling; checker exit 2 / `STOP_IMPOSSIBLE_BUDGET` |
| K = 44,090 distinct in-footprint dots | At least 37,441 overlap; minimum 84.9195%, above the literal 70% ceiling; checker exit 2 / `STOP_IMPOSSIBLE_BUDGET` |

The machine report itself states that only one necessary condition was checked: no pre-placement surface correlation and no candidate final-dot test ran. Do not remove this comparator, change the gate, reduce or reshape a stopped lane's budget, or exploit its uncovered cells to get around the rule. A change to that policy must be prospective and made by the responsible coordinator.

## Nine focus sites and H33-B2

The repository includes a nine-site historical champion table and source-pinned artifact/format metadata. It distinguishes owner-reported historical values from organizer-receipt-confirmed scores, and it does not support a numeric leaderboard estimate. The claimed `0.2778` for GEMSDOE32 H33-B2, as well as the conflicting `0.3195` / `0.4413` leaderboard snapshots in the supplied prompt, is **OWNER-REPORTED / UNVERIFIED here**. I did not obtain a DrivenData receipt, live leaderboard record, or account quota. “NOT ESTIMABLE” is the justified estimate; the owner-reported values must not be relabeled as confirmed.

Prior repository forensics describe H33-B2 as a deletion-only mask relative to an earlier dot pattern, with catalogue-proximal dots removed. Under a distance-weighted asymmetric Tversky objective, pruning low-value false-positive mass could improve a score if the removed cells carry sufficiently little hidden true-positive credit. But hidden organizer labels and the removed cells' TP/FP contributions are unavailable. That geometric ancestry is a plausible explanation to investigate, **not evidence that deletion caused `0.2778`**, not proof of the method's geology, and not a basis to promise a larger future score. See [metric-integrity notes](metric-integrity-20261026.md), [historical champions](historical-champions.html), and the linked hash-bound report in `docs/data/`.

Every file shown in the historical table is a previously existing artifact, not a new candidate. The table's uniqueness field is evaluated against its stated/pinned registry snapshot; it is not evidence that a fresh new candidate passes the whole live registry. The right action is not to pick the highest owner-reported entry for a slot; all remain research/audit only under current gates.

## Candidate hypotheses already documented (not new discoveries or lane assignments)

`docs/research-directions-20261027.md` has four hypotheses already on file. They are not certified as globally untried, and no DTI gain is known. Qualitative ordering is research priority only:

| Rank | Inputs and target signature | Why potentially complementary; main non-fault mimic | Readiness / difference |
|---|---|---|---|
| 1 | Cached `rtp` and `iso_grav_anom`, conditioned on an independent `det_elev` tangent: signed magnetic–gravity cross-gradient reversal | Could reflect a buried structural splay absent from surface mapping. Intrusive contacts, magnetic remanence, and acquisition seams can mimic it. | Cache-only concept, but full feature cache absent and source-channel provenance is not organizer-authenticated. Unlike earlier unsigned co-alignment/magnitude features. |
| 2 | Cached GeoDAWN K/Th/U ordinal grids: training-fold conditional K-rank residual and cross-front gradient where Th/U ranks are stable | Could mark a localized compositional overprint away from mapped traces. Sediment sorting, moisture, vegetation, and weathering can mimic it. | Cache-only concept; rasters exist but no cache holdout possible. Related to prior radiometric fronts, but adds fold-fitted conditional residualization. |
| 3 | `det_elev`, `det_local_relief`, `depth_to_base_surf`, `geod_dilaterate`, `geod_shearrate`: separated, signed terrain-flexure lobes around basement-depth change | Broad flexure could persist where a sharp scarp is eroded. Terraces, alluvial fans, dunes, and road cuts can mimic it. | Cache-only concept, medium computational cost; full cache absent. Differs from pointwise Hessian curvature and conductivity-saddle tests. |
| 4 | USGS ASTER mineral-group maps paired with `rtp`, gravity, or `cond_surf`: signed offset between an alteration transition and independent geophysical edge | A fluid-related halo may be offset from a concealed structure. Lithologic contacts, pre-existing mineralization, mining, atmosphere, or vegetation can mimic it. | **Not data-ready:** cited USGS releases are publicly described, but exact footprint coverage, downloadable source files, alignment, and local acquisition were not verified here. Do not claim it is obtainable/validated for this footprint. |

Any future assigned experiment must keep the requested whole-segment buffered hide/recover split; build catalogue-dependent features from visible faults only; mask visible faults pixel-exactly; test each actual feature alone for leakage; report evaluator/version, withheld positives and 95% CI; and use pooled DTI with α=0.2, β=0.8 and the 300 m triangular kernel. It must then pass surface rank-correlation and final-dot overlap gates against the full current registry, followed by format validation and the independent selector. The fixed budget remains at most three experiments or two hours. No holdout was run in this review.

## Submission format and H33 portal error

No new raster was generated, so there is no candidate SHA-256 or candidate validator result to claim. Existing docs describe a single-band GeoTIFF, template grid alignment, finite values, and the [0,1] prediction range. The portal's earlier `Predicted values must be in range [0, 1]` rejection cause is not proven by this review: do not attribute it solely to NaNs without the exact rejected file and organizer validation detail. A local format pass would not establish scientific eligibility, novelty, organizer acceptance, or authorization to use a weekly slot.

**Validator-integrity caveat surfaced by the concurrently integrated `origin/main` review:** `docs/session-review-20261028-mask.md` documents a synthetic finite, in-range pixel masked by GDAL that the shared validator reportedly accepts. I inspected this report but did not independently rerun its synthetic reproduction in this review. The report links concurrent PR #84 as a proposed shared fix; that PR's fix and integration are not yet established here. Until the shared fix is reviewed and integrated, a format PASS must not be treated as a complete validity decision. Historical champion files also have a recorded mismatch between local hard checks and the separate exterior-NaN check; the updated historical table labels these checks separately rather than diagnosing the portal error.

## Verification passes

1. **Pass 1 — baseline:** read the README/current instructions, active mission summary, current branch state, latest repository reviews, experiment and artifact inventory, and existing nine-site/metric documentation. Confirmed that no new method paragraph is assigned and that the full training-feature stack is absent.
2. **Pass 2 — adversarial:** attempted the full test suite. It initially produced **6 failures and 572 passes**, all six failures requiring Git commits missing from the shallow checkout. Fetched full history without changing branches; the dedicated history guard then passed. This checkout dependency is real: users or CI using shallow history need full fetch depth before provenance/ancestry checks.
3. **Pass 3 — final verification:** after restoring history, the full suite passed **578 tests** on this branch's original base. I then integrated the newly advanced `origin/main` to resolve the PR conflict; the integrated suite passed **579 tests**. Ruff formatting caught one style issue in the incoming historical-champion reviewer, which I formatted; its focused tests then passed (**8 tests**). Final Ruff check/format passed (**332 files formatted**). Python compileall, JavaScript syntax, `git diff --check`, and the full-history guard passed. The feasibility checker was reproduced and correctly returned exit 2 for both stated standard diagnostic budgets. No current browser run, fresh peer-site artifact census, source download, holdout, live quota/leaderboard query, TIFF generation, or submission was performed.

## Priorities and remaining limitations

1. Obtain the exact prospective method-paragraph assignment and a written decision on the retained lattice's role in the literal novelty registry. Do not infer the lane from the idea queue.
2. Restore the authorized full feature raster/cache through an allowed source, verify hashes/grid/channel semantics, and document provenance separately from checksums. The training inputs are not in this checkout, and no DrivenData login is available in this runtime.
3. Reconcile open/concurrent lanes and re-audit exact artifacts from current heads; commit freshness alone is not TIFF or score freshness.
4. Only then preregister and run the assigned hypothesis with the shared holdout/evaluator/writer, feature-level leakage canaries, paired uncertainty, and full-registry pre-placement/final novelty. Stop honestly on any gate failure.
5. Keep the separate selector fail-closed. Verify current account allowance only after all scientific and artifact gates; no slot was checked or used here.
6. Continue the executive site from its source artifacts and ensure every site row states an exact file, evidence class, NOT ESTIMABLE score when no receipt supports an estimate, novelty scope, and explicit download/submission decision. No high-scoring submit-ready TIFF is available from this review.

**Run card:** [`evidence/repo_review_20261028_arena_06c138ea_run_card.json`](../evidence/repo_review_20261028_arena_06c138ea_run_card.json). The active mission and full historical request remain linked from the top of `README.md`.
