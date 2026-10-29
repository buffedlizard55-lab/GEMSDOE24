# Repository review — 2026-10-29 (`arena/1ec38571-gemsdoe24`)

## Decision

**NO SUBMISSION-AUTHORIZED TIFF · DO NOT SUBMIT.** This review created no prediction raster, ran no geological experiment or holdout, estimated no leaderboard score, and used no competition slot. The request's unique, higher-scoring submission is **not yet achieved**. A format-valid historic TIFF is not a new, protocol-unique or submit-authorized prediction.

The existing [nine-site historical champions table](historical-champions.html) is the right starting point for exact download names and local file checks. It is a pinned historical audit, not a fresh scan of every file on the nine sites, not a current leaderboard, and not a recommendation to submit.

## Findings that change the decision

1. **The protocol has no assigned lane.** The request says to stay in one method paragraph, but provides no single method paragraph to execute. Existing hypotheses are proposals, and some overlap open PR work. Selecting one or starting any would violate the standing parallel-run rule. The historical `docs/data/active_lane.json` calls S3DEP1 the local recorded point-best; its own `lane_assignment` field says no new experiment is authorized. It is not a new assignment.
2. **Required training inputs are not in this checkout.** `data/training_features.tif`, the complete prepared feature stack and `data/labels.tif` are absent. The small bridge rasters and external mirrors do not authenticate or replace the organizer's complete inputs. The official DrivenData data page requires account access; this environment cannot access that host. No data, quota, portal, receipt or current leaderboard was downloaded or queried.
3. **The uniqueness constraint makes ordinary dot counts impossible before modeling.** The shared checker freshly verified the pinned bridge template and lattice witness: 5,160,724 of 5,167,373 footprint cells are within 3 px; 6,649 are uncovered. A candidate with 37,654 distinct in-footprint dots must therefore overlap by at least 31,005 dots (**82.3418%**); at 44,090 dots, at least 37,441 (**84.9195%**). Both exceed the literal 70% stop rule. This is a necessary geometric bound against one witness, not a full registry audit, a measured candidate overlap, proof of copying, or a score. It does not prove all smaller budgets fail. Do not evade it by targeting holes, shrinking a stopped lane, or removing a registry comparator.
4. **No hidden-score forecast is supported.** Among the nine claims provided, GEMSDOE32 B2's **0.2778 is owner-reported / unverified**, not an organizer receipt. The prompt's 0.3195 and 0.4413 leaderboard snapshots conflict and are not verified here. The table therefore reports leaderboard estimates as **NOT ESTIMABLE**. A spatial holdout is not an estimate of the hidden competition score.
5. **B2's plausible mechanism is pruning, not a demonstrated new discovery.** A prior geometry replay recorded B2 as a deletion-only subset of the D2.8-family pattern, removing catalogue-proximal dots. Under asymmetric, distance-tolerant Tversky scoring, pruning can improve precision if the removed predictions have more false-positive than true-positive contribution; it can also remove useful recall. Without hidden labels and an organizer receipt, the replay does not establish causality or explain the 0.2778 claim. See the [metric-integrity review](metric-integrity-20261026.md) and the [pinned nine-site audit](../docs/data/historical_champions_20261028.json).
6. **The local comparison floor is not the reported leaderboard.** The repository records `HOLDOUT-DTI = 0.166060` for S3DEP1 (`gems-segment-pooled-v1`, 60,988 withheld positives, 95% CI `[0.151858, 0.180339]`); this measurement was not replayed in this review and its selector is negative. A separate pinned peer receipt for KPL-36 records `HOLDOUT-DTI = 0.170100` (same declared evaluator and withheld-positive count, 95% CI `[0.155089, 0.186138]`), but it is not independently replayed or certified as protocol-equivalent. Do not describe S3DEP1 as the global point-best or KPL-36 as a competition winner. The available evidence is neither organizer-confirmed score.
7. **The reported `[0,1]` portal error remains undiagnosed.** Local strict whole-array range checks can confirm the bytes tested locally, but the exact rejected artifact and artifact-linked portal receipt are absent. The sample has NaN outside the footprint while some downloadable historic variants are all-finite; local format/range success does not establish the portal's interpretation or acceptance.

## Nine-site executive snapshot

All historical numbers below are the owner's supplied claims and remain **unverified**. “Estimate” means a forecast of the hidden competition result; none is supported. The downloadable artifact names and immutable source links are in the linked table. The table's pinned local review reports the historical files as research-only and checks them against a retained lattice witness; no listed file is authorized to submit.

| Site | Highest supplied historical claim | Leaderboard estimate | Local uniqueness / action |
|---|---:|---|---|
| GEMSDOE24 | 0.2477 | NOT ESTIMABLE | Historical research file only; do not submit |
| GEMSDOE25 | 0.2600 | NOT ESTIMABLE | Historical research file only; identical in-footprint predictions to GEMSDOE30 |
| GEMSDOE27 | 0.2449 | NOT ESTIMABLE | Historical research file only; do not submit |
| GEMSDOE28 | 0.2710 | NOT ESTIMABLE | Historical research file only; do not submit |
| GEMSDOE30 | 0.2600 | NOT ESTIMABLE | Historical research file only; identical in-footprint predictions to GEMSDOE25 |
| GEMSDOE31 | 0.2708 | NOT ESTIMABLE | Historical research file only; do not submit |
| GEMSDOE32 | **0.2778** | NOT ESTIMABLE | Highest supplied claim among these nine; not a fresh submission; do not submit |
| GEMSDOE33 | 0.2632 | NOT ESTIMABLE | Historical research file only; do not submit |
| GEMSDOE36 | 0.2750 | NOT ESTIMABLE | Historical research file only; do not submit |

Source for the exact per-file download, hash, local validator details and overlap: [historical champion table](historical-champions.html) and [machine-readable readback](../docs/data/historical_champions_20261028.json). The snapshot checked immutable historical commits, not the latest heads or every raster on each repository. Its lattice overlaps are not evidence that geological methods copied one another.

## Hypotheses already proposed, not certified as untried or viable

The repository's [four prospective directions](research-directions-20261027.md) are hypotheses, not results. They are included here so the review doesn't invent a new method or mistake a suggestion for the missing assigned lane. Their historical rank was qualitative expected information per implementation cost, **not a score forecast**. Existing parallel work has not been exhaustively reconciled, so no item is certified “not tried.”

| Historical proposal rank | Layers / target signature | Why it might recover an unmapped structure; important mimic | Difference / cost / availability status |
|---|---|---|---|
| 1 | Cached `rtp` + `iso_grav_anom` signed cross-gradient and reversal along `det_elev` tangent | Tests buried oblique structures/splays; intrusive contacts, magnetic remanence and survey seams can mimic it | Signed reversal differs from unsigned gradient/magnitude work; medium cost. The full feature stack is absent; overlaps open PR #70 research, so not certified untried. |
| 2 | GeoDAWN radiometric K, Th, U; fold-fitted conditional K-rank residual and cross-front gradient | Tests a localized compositional overprint; sediment sorting, moisture, vegetation, weathering/lithologic contacts mimic it | Conditional residual differs from fixed contrasts but relates to previous rank-space work; medium cost. Cached grids are present but source identity and full organizer inputs are not authenticated; overlaps open PR #70 research. |
| 3 | `det_elev`, local relief, basement depth, dilation and shear; separated signed curvature dipole aligned with basement step | Could capture broad flexure where a scarp is eroded; shorelines, terraces, fans, dunes and cuts mimic it | Separated paired lobes differ from pointwise Hessian tests; medium cost. Required full feature stack is absent; no holdout available. |
| 4 | USGS ASTER mineral-group maps aligned with geophysical fronts; signed transition offset | A fault-related fluid pathway could produce an offset alteration halo; volcanic contacts, older mineralization, mine waste, vegetation and atmospheric artifacts mimic it | Mineral transition/offset differs from direct radiometric or thermal proxying; high acquisition/alignment cost. Official USGS release is identified in the existing direction note ([USGS release, DOI 10.5066/F7CR5RK7](https://www.usgs.gov/data/digital-maps-hydrothermal-alteration-type-key-mineral-groups-and-green-vegetation-western)), but footprint overlap, file-level coverage, licensing details and automated retrieval have **not** been verified here. It is not data-ready or viable for this run. |

**No proposal was implemented.** The missing lane paragraph and unresolved geometric gate take precedence over the request to pick one. Resolving those constraints prospectively is required; don't reinterpret this list as authorization.

## Automated checks and three review passes

- **Pass 1 — inventory and protocol:** read the README/mission/standing instructions and prior reviews; checked branch/base and open PR metadata; confirmed absent training stack; reviewed the existing nine-site and current-best records. No sibling repo was edited.
- **Pass 2 — reproduce and challenge:** installed the pinned project/dev dependencies in ignored `.venv`; ran `scripts/check_uniqueness_feasibility.py --dot-budget 37654 --dot-budget 44090`. It returned exit **2** and `STOP_IMPOSSIBLE_BUDGET` for both budgets. Ran strict local preflight on the S3DEP1 research TIFF: `FORMAT: True | STRICT_RANGE: True | SCIENTIFIC_AUTHORIZATION: False | SUBMISSION: DO_NOT_SUBMIT`. This only revalidates bytes against the local bridge template and is not portal acceptance.
- **Pass 3 — test and close:** the first full test run had **6 failures / 657 passes** because this checkout had shallow Git history and receipt tests could not resolve pinned source commits. `git fetch --unshallow origin` restored history without changing tracked files. The six affected receipt/integrity tests then passed (**52 passed**), and the complete suite passed (**663 passed**). `ruff check .` and `git diff --check` passed. No experiment, new TIFF or slot was used.

Run details: [machine-readable negative run card](../evidence/session_1ec38571_20261029_run_card.json). The required null holdout fields are intentional: this was a repository/protocol review, not a geological experiment.

## Blocking next steps and official-source limits

1. Resolve the single method-lane assignment and the lattice-gate policy prospectively; don't change thresholds or comparators unilaterally.
2. Restore the complete competition `training_features.tif`, official labels/sample submission, provenance and cached feature stack through an authorized channel. The repository documents the [DrivenData data page](https://www.drivendata.org/competitions/306/competition-doe-gems/data/) as login-restricted; it was not accessed in this session.
3. Reconcile open PR #70 and other parallel work before any proposed method is called new. The current runner must use the shared visible-only buffered segment holdout and feature-by-feature leakage canaries, then surface and final-dot tests against the full registry.
4. Replay the current best using the same protocol, compare paired uncertainty, and implement a truly independent selector/replay certificate. Obtain quota/receipt only through allowed organizer workflow. The agent did not upload anything.
5. Diagnose the range rejection only against the exact rejected bytes and any artifact-linked organizer response. Do not infer the cause from a sample or a different TIFF.
6. Refresh every named site and the competition leaderboard from permitted sources before reporting current results. This review reused the existing pinned snapshot; it did not inspect current `github.io` site contents or scrape DrivenData.

Official references for manual review (links are references, not claims of fresh access): [DrivenData problem](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/), [DrivenData data page](https://www.drivendata.org/competitions/306/competition-doe-gems/data/), [NLR prize/rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf), [Drivendata reference solution on GitHub](https://github.com/drivendataorg/gems-prize-reference-solution), [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and), and [OpenEI/INGENIOUS GDR #1391](https://gdr.openei.org/submissions/1391).
