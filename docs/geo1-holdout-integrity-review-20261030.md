# GEO1 holdout-integrity correction and nine-site review — 2026-10-30

## Decision

**No file in this report is cleared to submit. No new TIFF, geological experiment, holdout, leaderboard estimate, or competition slot was produced by this review.** This is a reporting-integrity correction, not a new scientific lane. The required single method paragraph is absent, and the complete competition feature raster/prepared stack is not present in this checkout.

The [nine-site executive summary](nine-site-submission-summary.html) now labels the GEO1 result as compromised, distinguishes uniqueness versus the nine pinned focus artifacts from the full registry gate, and says **NOT ESTIMABLE** for every leaderboard prediction. The GEO1 TIFF remains a research artifact only; the original raster and run receipts are preserved.

## Why the executive summary needed correction

The prior summary called GEO1 the “stronger holdout” and “best unique file by holdout.” That ranking was not supported. A source-level review in [`evidence/session_1ec38571_20261029_run_card.json`](../evidence/session_1ec38571_20261029_run_card.json) found that the frozen runner used the complete catalogue to decide which cells could be emitted in each holdout fold:

- [`scripts/build_unique_geothermal_submission.py`](../scripts/build_unique_geothermal_submission.py) loads the entire labels/catalogue grid before folds are scored.
- Its fold eligibility is `fp & f["valid"] & ~catalogue`, not a mask formed from `f["visible"]`. Thus withheld target locations influence which predictions can be placed. This violates the requested visible-only hide-and-recover protocol.
- The feature-only AUC canary does not test leakage through this placement mask. The source-recorded `HOLDOUT-DTI = 0.1426949` (evaluator `gems-segment-pooled-v1`, 60,988 withheld positives, 95% CI `[0.1322931, 0.1523671]`) is therefore **COMPROMISED / NOT A VALID COMPARABLE HOLDOUT**. It is retained as historical evidence but excluded from candidate ranking.
- A second source issue is that `rtp_like` and `TMI_up150` reference the same raster and are both passed through the same edge operator. This is duplicate input, not independent RTP corroboration. The exact executed-run source hashes are retained in [`evidence/geo1_experiment.json`](../evidence/geo1_experiment.json); the report builder checks the GEO1 runner hash and the review's raster/holdout identity before displaying the warning.

The relevant source-level evidence is also summarized in the [2026-10-29 repository review](repo-review-20261029-arena-1ec38571.md). This correction does not patch or rerun the frozen GEO1 experiment.

## Nine focus sites: historical leaders, not current recommendations

The pinned historical table covers one owner-named champion per site, not every current site head or every submission. Its score column is **OWNER-REPORTED / UNVERIFIED**; all leaderboard estimates remain **NOT ESTIMABLE** without artifact-linked organizer receipts and hidden labels.

| Site | Pinned historical champion | Owner-reported claim | Leaderboard estimate | Unique under the project protocol? | Action |
|---|---|---:|---|---|---|
| GEMSDOE24 | H25-1 dotted H19-5, D1.5 | 0.2477 | NOT ESTIMABLE | No; fails the retained-lattice gate | Research/audit only; submit NO |
| GEMSDOE25 | Dotted H19-5, D2.8 | 0.2600 | NOT ESTIMABLE | No; exact in-footprint alias of GEMSDOE30 and fails the lattice gate | Research/audit only; submit NO |
| GEMSDOE27 | Topographic gap-closure, D1.5 | 0.2449 | NOT ESTIMABLE | No; fails the retained-lattice gate | Research/audit only; submit NO |
| GEMSDOE28 | H36 blind rung-30 | 0.2710 | NOT ESTIMABLE | No; fails the retained-lattice gate | Research/audit only; submit NO |
| GEMSDOE30 | D28 Poisson, 300 m off-catalogue | 0.2600 | NOT ESTIMABLE | No; exact in-footprint alias of GEMSDOE25 and fails the lattice gate | Research/audit only; submit NO |
| GEMSDOE31 | H27-4 solo, D2.8 | 0.2708 | NOT ESTIMABLE | No; fails the retained-lattice gate | Research/audit only; submit NO |
| GEMSDOE32 | H33-H33-2-B2 | **0.2778** | NOT ESTIMABLE | No; highly overlaps the other focus artifacts and fails the lattice gate | Research/audit only; submit NO |
| GEMSDOE33 | H33D analog tip-stepover, R30 | 0.2632 | NOT ESTIMABLE | No; fails the retained-lattice gate | Research/audit only; submit NO |
| GEMSDOE36 | Anderson geothermal PINN | 0.2750 | NOT ESTIMABLE | No; fails the retained-lattice gate | Research/audit only; submit NO |

The exact filenames, immutable links, hashes, local checks and overlap measures are in the [historical champion table](historical-champions.html) and [`docs/data/historical_champions_20261028.json`](data/historical_champions_20261028.json). These are pinned historical artifacts; the checked nine-site source heads later changed. The report must not describe this snapshot as a current exhaustive registry census.

## What the H33-B2 record can—and cannot—explain

The supplied `0.2778` is the highest owner-reported value among these nine entries, but it is **not ORGANIZER-CONFIRMED** here. The recorded artifact geometry is a deletion-only subset of the GEMSDOE25/30 D2.8 pattern: it removes 6,436 dots within 200 m of the public catalogue and adds no new locations. This is a geometric ancestry result, not proof of hidden-fault recovery, fault permeability, geothermal vents, or the cause of the reported score.

The shared evaluator uses a distance-weighted Tversky score. With weighted true positives `T`, false positives `F`, hidden truth mass `N`, `alpha = 0.2`, and `beta = 0.8`,

`D = T / (T + alpha*F + beta*(N - T))`.

Removing emitted predictions can improve this ratio if the reduction in weighted false-positive mass outweighs the lost weighted true-positive credit. It can also hurt by removing predictions near withheld faults. The hidden-label TP/FP/FN decomposition for the reported leaderboard score is unavailable, so “pruning reduced false positives” is a plausible hypothesis, not an established causal explanation. Fewer dots alone do not imply a higher score.

The user-provided overall leaderboard snapshots `0.3195` and `0.4413` conflict and no artifact-linked organizer receipt was accessed in this review. We did not query DrivenData. It is possible in principle to beat an owner-reported result, but this repository does not establish that any file will score above `0.2778`. The hidden leaderboard estimate is **NOT ESTIMABLE**. The repository's historical local holdout point-best is a separate evidence class and cannot be translated into a leaderboard projection.

## Candidate hypotheses ranked qualitatively — not certified “untried”

The repository already records four prospective directions in [`docs/research-directions-20261027.md`](research-directions-20261027.md). They are not assignments, results, or numerical score predictions. Their order is qualitative expected information per implementation cost; the present review does not certify that any is globally untried because parallel work and newer site heads are not fully reconciled.

| Rank | Inputs and targeted physical signature | Why it could find a missing fault; named non-fault mimic | Difference / cost / source status |
|---|---|---|---|
| 1 | Cached `rtp` + `iso_grav_anom`; signed cross-gradient reversal along an independently estimated `det_elev` tangent | Tests buried oblique intersections/splays not necessarily expressed as a surface scarp; intrusive contacts, remanent magnetization and survey seams can mimic it | Signed reversal rather than unsigned co-alignment; medium cost. Not certified untried: open PR #70 overlaps the signed magnetic–gravity concepts. Full prepared stack is absent. |
| 2 | GeoDAWN `K`, `Th`, `U`; training-fold-only conditional K-rank residual and cross-front gradient | Tests a localized compositional overprint not explained by broad parent-lithology ranks; arkosic sorting, moisture, vegetation and weathering can mimic it | Conditional residual rather than fixed radiometric contrast; medium cost. Related methods exist. Local quantized caches are not absolute concentrations or proof of alteration; full prepared stack is absent. |
| 3 | `det_elev`, local relief, basement depth, dilation and shear; separated opposite-signed terrain-curvature lobes around a basement step | Tests broad flexure after erosion obscures a sharp scarp; terrace/valley pairs, shorelines, fans, dunes and road cuts can mimic it | Separated signed dipole rather than pointwise Hessian; medium cost. Full prepared stack is absent. |
| 4 | Official USGS ASTER hydrothermal mineral-group maps and a potential-field or conductivity front; signed offset of an elongated alteration transition | Tests an alteration halo displaced along a concealed structure; volcanic contacts, older mineralization, mine waste, vegetation and atmospheric artifacts can mimic it | Mineral-type transition/offset, not a direct radiometric or thermal proxy; high acquisition/alignment cost. USGS release DOI `10.5066/F7CR5RK7` is linked below, but exact product coverage, overlap, license of the needed files and automated obtainability were not checked. **Not data-ready or viable for this session.** |

**No top candidate was selected or validated.** The parallel-run protocol assigns one method paragraph, but the active request contains none. The cached feature stack and full training raster are absent in this checkout. The literal 70%/3-pixel rule also proves that the fixed historical 37,654- and 44,090-dot budgets cannot pass against the one retained spacing-5 lattice witness; that necessary bound is not a full-registry pass/fail for other budgets and must not be evaded by moving dots to lattice holes. No weekly slot was used.

## Validation and usability status

- The GEO1 summary correction uses the hash-pinned source review and source-code hash; it does not alter the frozen experiment or raster.
- The nine-site table's highest owner-reported claim and local geometric uniqueness status are separated from the hidden leaderboard estimate.
- A local range/grid check is not portal acceptance. The reported `Predicted values must be in range [0, 1]` error is unresolved; the exact rejected bytes and artifact-linked organizer response are unavailable in this audit.
- Historical research TIFFs and prior reports remain downloadable for audit. Their download links do **not** mean “OK to submit.” No current artifact is authorized; the summary says **SUBMIT: NO**.

## Official references for manual review

These are source links, not claims that their pages or new data products were fetched in this session:

- [DrivenData problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) and [competition data page](https://www.drivendata.org/competitions/306/competition-doe-gems/data/) (login-restricted according to repository records; no access attempted).
- [DrivenData reference solution](https://github.com/drivendataorg/gems-prize-reference-solution).
- [NLR submission/rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf).
- [USGS GeoDAWN release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and), DOI `10.5066/P93LGLVQ`.
- [OpenEI INGENIOUS GDR #1391](https://gdr.openei.org/submissions/1391).
- [USGS ASTER western hydrothermal-alteration/mineral-group release](https://www.usgs.gov/data/digital-maps-hydrothermal-alteration-type-key-mineral-groups-and-green-vegetation-western), DOI `10.5066/F7CR5RK7`.
- [USGS 3DEP products and services](https://www.usgs.gov/3d-elevation-program/about-3dep-products-services).
- [EPSG:32611](https://epsg.io/32611).

## Three review passes

1. **Inventory and evidence:** read the mission, README, standing instructions, historical report and the GEO1 source-level review. Confirmed this task can be completed without training only as a reporting correction; the current project inputs/prepared feature stack are absent and the branch has no new scientific lane.
2. **Adversarial implementation review:** traced the full-catalogue mask in the frozen, hash-recorded GEO1 runner; made the report builder check raster identity, holdout values, review status and executed-runner hash before display. Corrected language that ranked the compromised GEO1 value, added regression tests, and kept both candidate rows visibly research-only.
3. **Original-request recheck:** confirmed the page states the exact historical downloads, keeps all nine leaderboard estimates `NOT ESTIMABLE`, explains why B2's reported value cannot establish causality, distinguishes focus-nine overlap from the literal lattice gate, keeps a generic submission procedure while warning that no file is approved, and creates no TIFF or slot.

## Verification executed in this review

- `python scripts/build_nine_site_report.py`: passed; regenerated the executive-summary HTML and its linked report run card from pinned evidence. It produced no TIFF.
- `pytest -q`: **672 passed, 1 skipped** (including five new GEO1/report-integrity regression tests).
- `ruff check .`, `ruff format --check .` (**353 files already formatted**), and `git diff --check`: passed.
- `.venv/bin/python scripts/build_site.py`: passed. Its generated site metadata/pages were restored afterward because they were unrelated to this focused correction.
- `python scripts/check_git_history.py`: passed after fetching full history.
- `python scripts/check_uniqueness_feasibility.py --dot-budget 37654 --dot-budget 44090`: returned its expected stop code **2**. Against the one retained spacing-5 lattice witness, the necessary overlap lower bounds are **82.34%** and **84.92%** respectively; the largest integer budget not ruled out by this bound is **22,163**. This is a necessary geometric bound only: no candidate surface or dots were generated, and it is not a full-registry or scientific pass.

**Next blockers:** obtain the actual assigned method paragraph and prospective policy for the retained lattice; restore the official competition inputs and prepared cache through an authorized channel; reconcile parallel method work; then preregister and run a candidate only through the shared evaluator/writer, leakage canaries, full registry checks and independent selector. No submission slot is spent until those checks pass.
