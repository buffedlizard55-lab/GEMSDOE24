# Repository review — 2026-10-30 (`arena/9b32516e-gemsdoe24`)

**Decision: NO NEW TIFF · NO NEW GEOLOGICAL EXPERIMENT · NO SCORE ESTIMATE · SUBMIT: NO.**
This review refreshed the GitHub commit-freshness feed and revalidated the nine *pinned historical champion files*. It did not inspect the changed heads' new TIFFs or infer current site winners. No submission slot was used.

## Executive answer

- The strongest supplied nine-site claim is GEMSDOE32 H33-B2, **0.2778 OWNER-REPORTED / UNVERIFIED**, not ORGANIZER-CONFIRMED. It is not evidence that the current leaderboard score is 0.2778, and it is not an estimate of a new prediction's score.
- A plausible explanation for the B2-vs-D2.8 reported difference is pruning predictions near the public catalogue, which may remove false-positive mass. Pixel forensics in the repository identify B2 as a deletion-only subset of D2.8: 6,436 dots removed and no new coordinates. Under the shared DTI, removal helps only when the false-positive mass removed is large enough relative to any lost true-positive credit. Hidden labels are unavailable, so that causal balance is unknown. Proximity to a public fault is not proof that a prediction is false.
- A result above 0.2778 is possible in principle, but **no defensible probability or leaderboard score estimate is available**. The reported overall highs 0.3195 and 0.4413 conflict and have no submission-page receipts in this checkout.
- The requested new TIF was **not generated**. The session-specific method paragraph is absent; `data/training_features.tif` and its prepared stack are absent; and both customary fixed dot counts fail the literal 70% 3-pixel lattice gate before any candidate can be considered. Inventing a different lane, tuning a stopped budget or creating a renamed/perturbed old prediction would violate the parallel-run rules rather than produce a defensible unique submission.

## Nine-site decision table — historical artifacts only

Exact immutable files were read back by the shared historical-champion audit. Scores below are the owner's historical claims from the preserved site records, **not organizer receipts**. The “estimated leaderboard score” field remains **NOT ESTIMABLE** for every row. The 3-pixel values are directed overlap against the retained spacing-5 calibration-lattice witness; these fail the stated uniqueness threshold but do not imply copying. Max peer-overlap values are from the repository's earlier nine-file pairwise audit, not a refreshed audit of the new HEADs.

| Site | Exact historical file (research/audit download) | Historical score evidence | Max peer 3-px overlap | Lattice overlap (3 px) | Unique vs focus sites? | Score estimate / submit decision |
|---|---|---:|---:|---:|---|---|
| GEMSDOE24 | [gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-allfinite.tif](https://github.com/buffedlizard55-lab/GEMSDOE24/raw/07345ea0604953d7efb858d9cfbc21e20c7aca0b/docs/downloads/gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-allfinite.tif) | 0.2477 OWNER-REPORTED / UNVERIFIED | 1.000 | 99.9218% | **No** under literal gate | NOT ESTIMABLE · DO NOT SUBMIT |
| GEMSDOE25 | [gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-zeros.tif](https://github.com/buffedlizard55-lab/GEMSDOE25/raw/04333cc3fbf7486c56e0324fd07aee684be614dc/docs/downloads/gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-zeros.tif) | 0.2600 OWNER-REPORTED / UNVERIFIED | 1.000 | 99.9161% | **No**; exact positive-set duplicate of GEMSDOE30 D28 | NOT ESTIMABLE · DO NOT SUBMIT |
| GEMSDOE27 | [gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-allfinite.tif](https://github.com/buffedlizard55-lab/GEMSDOE27/raw/b8dd298e10884afffa05436673ac73aeaf850b8c/docs/downloads/gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-allfinite.tif) | 0.2449 OWNER-REPORTED / UNVERIFIED | 0.980 | 99.9234% | **No** under literal gate | NOT ESTIMABLE · DO NOT SUBMIT |
| GEMSDOE28 | [gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-allfinite.tif](https://github.com/buffedlizard55-lab/GEMSDOE28/raw/78e724f95337a6528b1248be5c113c6d6d502891/docs/downloads/gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-allfinite.tif) | 0.2710 OWNER-REPORTED / UNVERIFIED | 1.000 | 99.9097% | **No** under literal gate | NOT ESTIMABLE · DO NOT SUBMIT |
| GEMSDOE30 | [gemsdoe30-d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca.tif](https://github.com/buffedlizard55-lab/GEMSDOE30/raw/3d5bec2af5f29291617f97c9e2dfe443be6f55c3/docs/downloads/gemsdoe30-d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca.tif) | 0.2600 OWNER-REPORTED / UNVERIFIED | 1.000 | 99.9161% | **No**; exact positive-set duplicate of GEMSDOE25 D2.8 | NOT ESTIMABLE · DO NOT SUBMIT |
| GEMSDOE31 | [gemsdoe31-h27-4-solo-d28-20261004-8acb75e1-allfinite.tif](https://github.com/buffedlizard55-lab/GEMSDOE31/raw/cf13282fcd86290f1539f0a86446c8ba7205a79b/docs/downloads/gemsdoe31-h27-4-solo-d28-20261004-8acb75e1-allfinite.tif) | 0.2708 OWNER-REPORTED / UNVERIFIED | 1.000 | 99.9179% | **No** under literal gate | NOT ESTIMABLE · DO NOT SUBMIT |
| GEMSDOE32 | [gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif](https://github.com/buffedlizard55-lab/GEMSDOE32/raw/012e17b2a115c3c0d5e7885bea625bf9657c99fc/docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif) | **0.2778 OWNER-REPORTED / UNVERIFIED** | 1.000 | 99.9150% | **No** under literal gate | NOT ESTIMABLE · DO NOT SUBMIT |
| GEMSDOE33 | [GEMSDOE33-h33d-analog-tip-stepover-r30-20261004-cb490425926e.tif](https://github.com/buffedlizard55-lab/GEMSDOE33/raw/f52533110fe62cd03e77f1228e9e5ecac412c463/docs/downloads/GEMSDOE33-h33d-analog-tip-stepover-r30-20261004-cb490425926e.tif) | 0.2632 OWNER-REPORTED / UNVERIFIED | 0.997 | 99.9140% | **No** under literal gate | NOT ESTIMABLE · DO NOT SUBMIT |
| GEMSDOE36 | [gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif](https://github.com/buffedlizard55-lab/GEMSDOE36/raw/c9ad59ec6f969ed931d089a03044c1567a633e84/docs/downloads/gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif) | 0.2750 OWNER-REPORTED / UNVERIFIED | 0.976 | 99.9176% | **No** under literal gate | NOT ESTIMABLE · DO NOT SUBMIT |

The downloads above are immutable historical artifacts for research/audit. **None is recommended or authorized for upload.** The current site repositories may contain later files; those have not been reviewed in this session. The shared rendered nine-site page is [here](nine-site-submission-summary.html), and the verified historical download/audit table is [here](historical-champions.html).

## Current-feed result and scope

At `2026-10-30T22:48:16Z`, the GitHub-only priority feed successfully checked all 9 priority repositories: **9/9 `main` refs differ from their pinned artifact-audit refs**. See [`docs/data/priority_feed.json`](data/priority_feed.json). This is only a commit-reference freshness check. It did not read those newer READMEs, inspect their new TIFFs, verify new score claims, or access DrivenData. The static nine-site matrix above remains an explicitly historical snapshot until those newer heads are audited.

## Why no new candidate was tested

The parallel-run protocol requires the method paragraph itself to assign one lane. None is present in this request or in the active run card. In addition:

- The full `data/training_features.tif` and prepared cache are absent. Existing bridge/external derivatives are not the requested cached feature stack.
- A fresh necessary-condition check of the fixed 37,654- and 44,090-dot budgets returned `STOP_IMPOSSIBLE_BUDGET` for both against the retained lattice witness: witness coverage is 99.8713%; minimum directed overlap bounds are 82.3418% and 84.9195%, respectively. This proves only those budgets cannot meet the literal gate. It does **not** establish that every smaller budget fails and is not evidence of copied geology.
- Because no candidate surface was generated, neither pre-placement rank-correlation nor final-dot overlap was measured. No feature-level leakage canary, spatially blocked hide-and-recover, validation of a candidate TIFF, or selector run occurred.

### Ranked hypotheses for a future formally assigned lane

These are qualitative research priorities, not score predictions. The current GitHub feed shows changed peer heads, and the prior repo already discusses related proposals; therefore **none is certified untried across all nine current site heads**. First audit current implementations and source semantics before declaring novelty. No experiment is authorized by this ranking.

| Rank | Specific layers and targeted signature | Why it may mark an unmapped structure | Distinction from locally documented methods; main mimic | Expected DTI / cost |
|---|---|---|---|---|
| 1 | `rtp` × `iso_grav_anom` (and terrain-derived tangent only as an independently defined orientation reference): signed normalized cross-gradient and cross-strike sign reversal at fixed physical scales. | A buried oblique contact/splay can change the relative orientation of magnetic and gravity gradients without a crisp surface scarp. | Existing local work emphasizes gradient magnitudes, unsigned cross-alignment and topographic/magnetic coupling; a signed gravity–magnetic reversal is a distinct operator, but the earlier research queue and a prior concurrent proposal overlap it. **Mimics:** intrusive contacts, remanent magnetization, survey seams. | Highest qualitative information-per-cost priority; **unknown DTI**; medium compute. |
| 2 | GeoDAWN `K`, `Th`, `U` ordinal/rank layers: fit a fold-local conditional K-rank response to Th/U ranks, then detect a residual cross-front where Th/U ranks are stable. | Localized alteration/transport along a concealed discontinuity may depart from parent-lithology background. | Differs from fixed K/Th contrasts and unconditional radiometric-front features already explored locally; conditional ranks must be trained separately inside each visible-only fold. **Mimics:** sediment sorting, weathering, moisture, vegetation and lithologic contacts. | Moderate-to-high potential; **unknown DTI**; medium cost. |
| 3 | `det_elev`, `det_local_relief`, `depth_to_base_surf`, `geod_dilaterate`, `geod_shearrate`: separated, oppositely signed cross-normal terrain-flexure lobes around a basement-depth step, corroborated by broad strain. | A buried fault may generate broad flexure after a sharp scarp has been erased. | More specific than pointwise Hessian/curvature and conductivity-saddle features in local work; requires fold-safe orientation and support. **Mimics:** terrace–valley pairs, dunes, alluvial fans, road cuts. | Moderate potential; **unknown DTI**; medium/high memory and scale-selection cost. |
| 4 | Official USGS ASTER hydrothermal-alteration mineral-group maps: elongated mineral-transition front and signed offset from a separately derived magnetic/gravity lineament. | A fluid-alteration halo could preserve evidence of a buried conduit where relief is muted. | Targets transition geometry/offset rather than simply radiometric intensity. **Mimics:** volcanic lithologic contacts, mineralization unrelated to active structures, mines, vegetation and atmospheric artifacts. | Lower prior pending coverage; **unknown DTI**; high data/alignment cost. Official source pointer: [USGS ASTER hydrothermal alteration maps](https://www.usgs.gov/data/digital-maps-hydrothermal-alteration-type-key-mineral-groups-and-green-vegetation-western), DOI `10.5066/F7CR5RK7`. Its footprint coverage, exact downloadable files and access could not be checked from this runtime, so it is **not data-ready or viable yet**. |

For hypotheses 1–3, the relevant cached channels are referred to in prior project records, but the full training raster/cache is missing here; their available status must not be inferred from channel names alone. Feature-only AUC canaries and whole-segment buffered holdout scores are **not available for these proposed transforms**. Do not attach any numeric DTI or leaderboard estimate to the ranking.

## Protocol and submission integrity

The shared metric uses `DTI = T / (T + 0.2F + 0.8(G-T))`, with the 300 m triangular credit kernel and exact visible-fault masking. Here `T` is recovered weighted truth credit, `F` is weighted false-positive mass and `G` is withheld truth mass. Deleting predictions helps only if the FP mass removed compensates for lost recovered truth credit; public-catalogue distance alone cannot establish this on hidden faults. See [`src/gems/metric.py`](../src/gems/metric.py) and the corrected [B2 metric note](metric-integrity-20261026.md).

No TIF can be marked “OK to submit” from this review: there is no candidate hash or candidate validator output, no surface/final-dot registry comparison, no independent promotion selector receipt, no current account quota, and no organizer receipt. The reported portal error “Predicted values must be in range [0, 1]” remains unexplained. An all-finite local check can address NaNs/range but cannot establish portal acceptance; do not upload a historical reference merely because its local format checks pass.

## Official references for manual review

These links are source pointers, not sources freshly fetched in this review except GitHub-hosted repository data. The runtime only permits outbound access to GitHub and package registries; no DrivenData, USGS, NLR or OpenEI page was accessed during this review.

- [DrivenData GEMS overview/problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) · [submission rules page](https://www.drivendata.org/competitions/306/competition-doe-gems/)
- [DrivenData reference solution (GitHub)](https://github.com/drivendataorg/gems-prize-reference-solution)
- [NLR GEMS competition rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf)
- [USGS GeoDAWN release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and), DOI `10.5066/P93LGLVQ`
- [OpenEI INGENIOUS data submission](https://gdr.openei.org/submissions/1391)
- [USGS 3DEP products/services](https://www.usgs.gov/3d-elevation-program/about-3dep-products-services)
- [EPSG:32611](https://epsg.io/32611)

## Three review passes and verification

1. **Review/implementation:** read the standing `README.md`, `AGENTS.md`, normalized `docs/MISSION_PROMPT.md`, submission/uniqueness code, pinned historical champion artifacts, B2 metric analysis and ranked research notes. Refreshed the GitHub-only nine-repository commit feed; all 9 current `main` refs changed from the pinned audit refs. Made the stale scope visible in the README and nine-site page. No geological experiment or TIFF generation.
2. **Adversarial review:** separated owner claims from organizer receipts; verified that B2 is not established as a newly detected fault surface; treated the 70% lattice threshold as an actual geometric stop, not a reason to hide predictions in uncovered cells; checked that the data stack is absent; rejected a numeric score projection and any current-head claim. Revalidated all nine pinned historical champion files with the shared historical artifact review; all fail the literal lattice gate.
3. **Final check:** full test suite **667 passed, 1 skipped**; Ruff lint and format checks pass; priority feed offline schema check passes; fixed-budget checker returns exit 2 for the documented 37,654 and 44,090 cases; `git diff --check` passes. No TIFF, score estimate, holdout, slot, or positive submission authorization was produced.

## Next work / blockers

1. Inspect all nine changed GitHub heads and newly named artifact/score claims before updating a “current” ranking; do not equate a freshness feed with an audit or score confirmation.
2. Restore the full training raster/cache from an authorized source and hash/provenance-verify it. DrivenData data/login and all non-GitHub official hosts were inaccessible in this session.
3. Obtain an explicit coordinator-provided single-method paragraph. Compare any candidate idea with both this repo's prior methods and the freshly changed peer heads before calling it untried.
4. Resolve the retained-lattice comparator policy prospectively; do not change thresholds, budgets or registry to evade the existing stop.
5. Only then, within the three-experiment/two-hour cap, run the shared fold-safe hide-and-recover, per-feature leakage canaries, surface/final-dot uniqueness checks, writer and validator. Promote only via the separate hash-bound selector and verified quota step.
6. Obtain a submission-page receipt to diagnose the range rejection and establish an organizer score. Do not claim the current overall leaderboard score from conflicting prompt snapshots.
