# Repository review and build-precedence fix — 2026-10-25

## Decision

**Review-only: no new detector experiment, no new TIFF, and no competition slot used.** The current owner prompt does not supply the single assigned method paragraph required by its lane protocol; the latest H-UNIQUE run card also records three experiments against the three-experiment limit. Retuning or selecting a parallel lane would breach the stop rule. Existing research TIFs are downloadable for audit, but none is approved for submission.

### Code defect fixed

The checked-in first-screen pages and `docs/data/unique_run_card.json` identify the H-UNIQUE TIF as the current research download. However, before this review, `scripts/build_site.py` selected the older `independent-mtr1-v1` packet first and would replace the current H-UNIQUE landing page during a clean Pages build. This disagreed with the exact-file revalidation recently added on `main`.

The default public build now calls the shared `gems.release_audit.verify_current_download`, verifies the exact H-UNIQUE TIFF against its hash-bound card and template, and checks that the root overview, docs overview, and executive guide all link the same file/hash and display `NOT OK TO SUBMIT`. It writes a `site_build.json` receipt for that exact active file. The previous MTR1/ASPC renderers remain reachable only through `--legacy-research-site`, used by their historical tests; the deployment workflow's no-argument build now fails closed rather than silently publishing an older artifact. The static content itself is preserved and checked rather than rewritten from an unrelated lane.

## Current download: exact status

The current first-screen research file is `24gems-doer-fault-guided-k-20261025T220208Z-dedb860f7e83-zeros.tif`, SHA-256 `800856082214038640ba98796c390ff76cb8583944dbc05505d9787ce7688c9e`. The exact-file receipt in `evidence/current_download_revalidation.json` and run card in `docs/data/unique_run_card.json` identify it as `DOWNLOAD: YES · SUBMIT: NO`.

Its **HOLDOUT-DTI** is `0.0538395` on `gems-segment-pooled-v1` (60,988 withheld positives; 95% CI `[0.0389377, 0.0686555]`). The candidate does not beat the comparable OOF baseline **HOLDOUT-DTI** `0.13000` on the same evaluator (60,988 withheld positives; 95% CI `[0.11565, 0.14396]`). Its raw surface rank correlation is below 0.90, but 99.867% of its final dots are within 3 px of a spacing-5 calibration raster, above the 70% stop threshold. Thus it fails novelty and is not promotable.

The TIFF passes exact-grid, single-band, finite `[0,1]` checks, including the outside pixels (zero-outside); this addresses the reported global-range rejection mode, but **does not prove portal acceptance**. The template's NaN-outside convention is not matched by this zero-outside encoding; the validator marks `official_format_compliant: false`. The negative scientific and novelty gates remain decisive regardless of format.

## H33-B2 result and limits of inference

The supplied H33-B2 `0.2778` remains **OWNER-REPORTED / TEAM-PUBLISHED**, not ORGANIZER-CONFIRMED: no artifact-linked submission-page receipt exists in this checkout. The conflicting 0.3195 and 0.4413 leaderboard claims are likewise not verified here. The latest corrected H33 analysis is `knowledge/14_h33_analysis_2026-10-25.md`.

Local forensics support geometry only: the 37,654-dot H33-B2 positive set is the 44,090-dot D2.8 set after removing 6,436 dots within 200 m of the supplied catalogue; there are no new coordinates in that comparison. This is not hidden truth or causal score evidence. With weighted Tversky components `T=TPw`, `F=FPw`, and truth mass `N`, the denominator is `0.2T + 0.2F + 0.8N`. Removing predictions can improve the ratio only if the loss of weighted TP is sufficiently smaller than the false-positive penalty avoided. Hidden-set `T`, `F`, and the removed dots' credit are unknown. The reported score therefore does not prove that FP reduction caused the improvement or that another detector can beat it.

## Ranked untried hypotheses (qualitative priority, not score forecasts)

These are candidates whose recorded preregistrations say **not run/deferred**; they are not claimed globally novel and were not tested in this review. The local active-code and preregistration scan found no completed validation for these exact operators. No numerical leaderboard or DTI projection is justified.

| Rank | Specific layers/signature | Why it may find an unmapped fault; named non-fault mimic | Difference from completed work / data viability | Expected DTI effect / implementation cost |
|---|---|---|---|---|
| 1 | **Upward-continuation survival of a paired magnetic trough**: cached RTP/TMI and upward-continued TMI (`TMI_up150`); contrast the paired cross-normal trough/shoulders before and after continuation. | A basement-scale concealed corridor may retain paired-trough geometry after upward continuation while short-wavelength cultural or surficial anomalies attenuate. Mimic: a long magnetite-poor lithologic strip. | MTR1 tested one trough plus Th/K; it did not test this preregistered persistence ratio. Recorded cached/GeoDAWN input family; no new external source indicated. See `knowledge/09_preregistration_magnetic_trough_2026-10-25.md`. | Effect unknown; positive increment is plausible only if persistence is independent of MTR1 and acquisition artifacts. Medium cost. |
| 2 | **Basement-topography-decoupled gravity/magnetic analytic-signal ratio**: `iso_grav_anom` horizontal/vertical gradients, `tmi` horizontal/vertical gradients, `depth_to_base_surf`, and `det_elev_slope`. | Concordant potential-field analytic-signal orientation beneath low-relief basin fill could identify buried discontinuities without a scarp. Mimic: pluton margins or paleochannel bedrock ledges. | Distinct from completed H24-3A contact persistence only if the preregistered dimensionless 3-D ratio and low-relief gate are fixed; substantial redundancy risk. Cached channels exist. Preregistered as H24-BTD2; not run. | Effect unknown and likely small at the 100 m potential-field scale; low-medium compute cost. |
| 3 | **Microtopographic curvature doublet with lithology veto**: cached LiDAR `lapneg_max`, `lappos_max`, `cross_max` plus K/Th contrast. | Paired crest/toe curvature within compositionally stable material may distinguish displacement from a primary lithologic edge. Mimic: shoreline terrace within one deposit. | Paired morphology with composition as a veto, unlike ASPC's directional curvature and SAHG1's positive alteration corroboration. Inputs are local; listed as not run in the ASPC preregistration. | Effect unknown; potential precision gain depends on whether the paired signal separates tectonic traces from shoreline forms. Medium cost. |
| 4 | **Repeated channel-crossing displacement consensus**: official 3DEP DEM-derived flow paths; signed lateral displacement at multiple independent crossings along one structural candidate, requiring common sign. | Multiple concordant offsets could indicate a strike-slip splay missed by a scarp catalogue. Mimic: road/terrace edges cannot consistently offset independent channels. | Existing code explores ridges, relief, lineaments and structural tips, not a validated multi-crossing kinematic test. Existing DEM may support a coarse pilot, but raw 3DEP coverage and byte receipts for the needed resolution were not verified. Official source entry point: [USGS 3DEP Data Tools](https://www.usgs.gov/3d-elevation-program/data-tools). Previously deferred in `knowledge/02_preregistered_2026-10-02.md`; untried but not newly conceived. | Potentially larger geological leverage but effect entirely unknown; high cost and not viable at high resolution until full-footprint tile availability is checked. |

Priority is research judgment only: #1 and #2 have local inputs and are cheapest to falsify, while #4 has stronger kinematic specificity but higher data/engineering cost. None can be run until a method paragraph is assigned, budget is authorized, every input has a feature-alone leakage canary, and the prospective registry decision is fixed. The spacing-5 calibration raster must not be removed after observing a candidate.

## Three review passes and verification

1. **Pass 1 — inspect and specify:** read the current README/owner brief, recent main review, H33 correction, current exact-file receipt, active holdout/writer/validator, site builder, source workflow, and H24 preregistrations. Compared current page identity with site-builder routing and found the MTR1-vs-H-UNIQUE precedence defect.
2. **Pass 2 — implement and test:** added a fail-closed default build route using the shared exact-file release audit; retained old MTR1/ASPC paths behind an explicit legacy option for reproduction. Added tests for deployment/current-card agreement and static-page links. No detector code or TIFF bytes changed.
3. **Pass 3 — recheck:** revalidated the exact current file, rebuilt the site receipt, reran recorded MTR1/SAHG1 verifiers without experiment reruns, ran the complete test suite, compilation/JS checks, and `git diff --check`. The whole-repository Ruff check still has 54 findings in three prototype scripts and Ruff format reports seven files needing formatting; those experimental scripts were not run or mechanically rewritten.

The current main's prior exact-download review reported 188 tests. The final count after this change is in the attached review run card and current test output. No new HOLDOUT-DTI is reported for this review.

## Limitations / next work

1. Assign the actual single method paragraph and settle the registry/calibration-control policy prospectively.
2. Confirm the weekly experiment/time budget before any experiment; H-UNIQUE's recorded run card already reports three experiments.
3. Resolve the 54 Ruff findings and five formatting failures before treating the three prototype scripts as supported workflow components.
4. Establish source-level provenance for owner-mirrored competition data; a matching local SHA proves integrity against that mirror receipt, not organizer origin.
5. The top H33 score and current leaderboard values require an artifact-linked organizer receipt; no automated DrivenData checks or uploads are permitted by project policy.

## Manual-review sources

- [DrivenData GEMS problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) — official competition page; not fetched in this review due network/terms policy.
- [DrivenData reference solution](https://github.com/drivendataorg/gems-prize-reference-solution) — organizer-owned repository.
- [USGS GeoDAWN ScienceBase record](https://www.sciencebase.gov/catalog/item/657e1d85d34e23d3533209f7) and [DOI 10.5066/P93LGLVQ](https://doi.org/10.5066/P93LGLVQ) — parent survey provenance, not fault-label evidence.
- [USGS 3DEP Data Tools](https://www.usgs.gov/3d-elevation-program/data-tools) — official elevation-data portal; high-resolution tile availability over the footprint was not checked.
- [GEMSDOE32 page](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html) and the other team pages listed in the owner brief — team-authored comparisons, not organizer score receipts.
