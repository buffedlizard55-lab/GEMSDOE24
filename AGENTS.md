# Standing project instructions

## H24-CGMK1 session — 2026-10-27 arena/5ef84d43 (executed; negative; do not retune)

Read `knowledge/32_preregistered_CGMK1_2026-10-27.md` (commits `9b280a3`+`8dafdc5`),
`knowledge/33_CGMK1_findings_and_9site_executive_summary_2026-10-27.md`, and
`evidence/cgmk1_run_card_20261027.json` first.
- No lane paragraph was supplied again; this session **disclosed a self-assignment** and
  preregistered one narrow lane before running: signed gravity–magnetic cross-gradient
  reversal + fold-fit conditional-K residual front, geophysics-only HGB (37 ch; no DEM
  trunk, no LiDAR, no `tc`, no catalogue-distance features). EXP-1 **HOLDOUT-DTI 0.08868**
  [0.07565, 0.10234] (`gems-segment-pooled-v1`, 60,988 withheld) vs EXP-2 control 0.08589
  (paired +0.00279 [−0.00222, +0.00768]); both independently rescored exact.
- Verdict **negative / DO_NOT_SUBMIT** (`gems24-cgmk1-negative-signed-gravmag-condk-20261027T173413Z-62ca1c4977c5-zeros.tif`,
  SHA-256 `3258f3290390b92470e0eb9d92886f0ab1289df1abe46397fcfaf08f56b43070`): format and canary PASS,
  competing-method novelty PASS (max overlap 62.05%, ~26% vs DPRF1/S3DEP1/DKRN1 over **39 local entries
  only** — cross-repo registry rasters absent in that sandbox), literal lattice FAIL (100%, pigeonhole),
  holdout far below the 0.17010 floor. **Do not rerun, retune, or re-emit CGMK1**; verify with
  `.venv/bin/python scripts/run_cgmk1_lane.py --verify-recorded`. Never edit
  `src/gems/cgmk1.py`/`scripts/run_cgmk1_lane.py` — their SHA-256s are inside the run card.
- Next (require fresh preregistration / coordinator decisions): obtain ONE artifact-linked organizer
  receipt; resolve the lattice comparator class; only then consider trunk-plus-new-channel or
  OPERA/Sentinel-2/MT lanes from an environment where those official downloads are obtainable.

## Pre-training feasibility continuation — 2026-10-27

Read `knowledge/owner_brief_2026-10-27_feasibility.md` and
`docs/feasibility-review-20261027.md` with README at session start.
Before allocating time to a newly assigned experiment, run
`python scripts/check_uniqueness_feasibility.py --dot-budget K` for its
prospectively fixed budget. Exit 2 proves the literal uniqueness gate cannot
pass; exit 0 means only NOT RULED OUT, never approval. Errors fail closed.
Do not restart old lanes, tune K or exclude comparators to force a pass.
Use `gems.novelty.dot_budget_feasibility` in new shared runners, not a private
metric. This continuation creates no TIFF, experiment, holdout or slot.

## 2026-10-27 integrity override — read before dated notes below

- This review produced **no new TIFF, scientific run or slot**; the assigned
  method paragraph remains absent. No selected focus file is authorized.
- TMCG overlaps the registered lattice at 100%; H-UNIQUE-07 overlaps at 99.7795%
  and its full-catalogue pre-fold support leaks withheld-fault information. Both
  lanes are stopped; their historical narratives cannot establish uniqueness.
- KPL-36 is an unreplayed external recorded HOLDOUT-DTI point of 0.17010 (not a
  confirmed winner). Compare prospectively before promotion; it too fails the
  literal lattice rule. S3DEP1 remains the local point-best, not global best.
- Band 6 `tc` is **not established** as gravity terrain correction or mGal:
  strong correlation to cached radiometric total count is not source proof.
- Current source, limit, portal and hypothesis details are in
  `knowledge/31_current_integrity_review_2026-10-27.md`. Dated claims below are
  historical; where inconsistent with the current evidence, this override wins.


## H24-XVAR1 session — 2026-10-26 (executed `H24-XVAR1`; solved `DPRF1` overlap & exact-file C2ST; negative; do not retune)

Read `knowledge/29_preregistered_XVAR1_2026-10-26.md` (@ `4f251952ee71`), `knowledge/30_XVAR1_findings_and_9site_executive_summary_2026-10-26.md`, `evidence/xvar1_run_card_20261026.json`, and `evidence/nine_site_executive_summary_xvar1_20261026.json` first.
- `H24-XVAR1` (`src/gems/xvar1.py`, `scripts/run_xvar1_lane.py`) executed Rank #1 of `knowledge/26_portfolio_plan_corrections_2026-10-26.md` (8 parity-symmetric centered two-sided azimuthal semivariogram jump & cross-strike anisotropy channels on float32 `rtp`, `iso_grav_anom`, `depth_to_base_surf`, `cond_surf` at lags `h in {300 m, 800 m}` across 4 strikes, 7-column fold-safe `NuisanceResidualizer` incl. `area1`, zero 1 m LiDAR channels, zero D8 wash routing, Dual-Partition Stitched-OOF) across 3 preregistered arms:
  - **Arm 1 (`H24-XVAR1` 45-ch 2-Regime `65% / 35%`):** `HOLDOUT-DTI = 0.14627` (`[0.13345, 0.15997]`, `gems-segment-pooled-v1`, `60,988` withheld), beating `oof_multiphysics_hgb_d3` (`0.13000`) by `+0.01627` (`[+0.00856, +0.02397]`, `4/4` folds), improving on matched 37-ch `B_SUB37` (`0.14533`) in `SW` (`+0.00708`) & `SE` (`+0.00291`) (`Arm 2` winning `3/4` folds incl. `NW +0.00214`), and **beating full 52-ch LiDAR-equipped `DPRF1` on `NW` (`0.15669` / `0.16081` 1R vs `0.15639`)**.
  - **Arm 2 (`XVAR1-1R` Single-Regime `100%`):** `HOLDOUT-DTI = 0.14680` (`[0.13426, 0.16027]`).
  - **Arm 3 (`B_SUB37` matched 37-ch LiDAR-free control without `XVAR1`):** `HOLDOUT-DTI = 0.14533` (`[0.13222, 0.15916]`).
- **Solved Both Prior `DKRN1` Defects — Independently Confirmed Second Convergence Theorem (`DO_NOT_SUBMIT`, `verdict: "negative"`):** `gems24-xvar1-duplicate-semivariogram-20261026-7d909c75458c-zeros.tif` (`SHA-256: 9c7d4ff1d49e322134e6b06e4ec304b98ea03d31420ac58c3803d9f2f57ba4b1`, `37,654` binary `{0,1}` dots, `21.8%` apron / `52.8%` `>2 km` far-field) is **DOWNLOAD: YES (research) · SUBMIT: NO**:
  1. Dropping all 15 1 m LiDAR channels cut 3-px dot overlap with `DPRF1` to **`65.64% <= 70%`** (`44.30%` vs `B2`, `<=53.92%` vs 83 peers, `<=52.41%` vs all 111 live 9-site GeoTIFFs), and 7-confound residualization with zero D8 routing restored exact-file C2ST **PASS** (`AUC = 0.5437 < 0.55`; 60/60 leakage canaries PASS `<=0.6111`).
  2. However, retaining the shared 37-channel `100 m` DEM geomorphic trunk (`det_local_relief`, `det_gradient`, `det_elev_slope`, `gvc_dem_lineament_900m`, `gvc_piedmont_inflection`) produced `75.36% > 70%` 3-px overlap against unsubmitted local `DKRN1` (just as parallel `H24-S3DEP1` hit `71.32% > 70%` against `DKRN1`!). **Do not rerun, retune, or nudge `XVAR1`**; verify frozen receipts via `.venv/bin/python scripts/run_xvar1_lane.py --verify-recorded`.

## H24-S3DEP1 session — 2026-10-26 (new all-time recorded HOLDOUT-DTI point-best `0.166060`; zero 1 m LiDAR; negative; do not retune)

Read `knowledge/29_preregistered_S3DEP1_2026-10-26.md` (@ `7e6db4d428ae`), `knowledge/30_S3DEP1_findings_and_9site_executive_summary_2026-10-26.md`, `evidence/s3dep1_run_card_20261026.json`, and `evidence/nine_site_executive_summary_s3dep1_20261026.json` first.
- `H24-S3DEP1` (`src/gems/s3dep1.py`, `scripts/run_s3dep1_lane.py`) executed a 100% 1 m-LiDAR-free 61-channel seamless detector combining 12 USGS 10 m 3DEP sub-cell gradients (`ScienceBase 4f70aa9fe4b058caae3f8de5`), 6 restored `training_features.tif` crustal/seismic channels (`mag_anom`, `geod_2ndinv`, `iso_grav_anom_slope`, Bouguer `tc` `[2.95, 88.57]` mGal, `log1p(deq/ieq)`), 6 monoclinal step/incision operators, and 37 non-LiDAR base + OpenEI GDR #1391 hydrothermal + SAHG channels across 3 preregistered experiments (`3/3` budget spent, `0` slots spent):
  - **Arm 3 (`H24-S3DEP1` Hybrid Primary `0.65` Core + `0.35` Kernel300):** **`HOLDOUT-DTI = 0.166060`** (`[0.151858, 0.180339]`, `gems-segment-pooled-v1`, `60,988` withheld — **new all-time recorded point-best across all 9 focus repositories**; `NE_LidarGapHeavy = 0.21972`, `SE = 0.18336`; `3.0 km` Bridge `0.16257`), beating `oof_multiphysics_hgb_d3` (`0.13000`) by `+0.03606` (`[+0.02082, +0.05195]`, `4/4` folds) and surpassing recorded `DPRF1` (`0.16379`) by `+0.00227` (`[-0.00699, +0.01144]`, `3/4` folds).
  - **Arm 1 (`S3DEP1` Dual-Negative `d3+d9` Core Classifier):** `HOLDOUT-DTI = 0.165366` (`NE_LidarGapHeavy = 0.22088`).
  - **Arm 2 (`S3DEP1` Pure `300 m` Kernel Soft-Label Regressor):** `HOLDOUT-DTI = 0.158449` (`Arm 3 - Arm 2 = +0.00761` `[+0.00261, +0.01256]`, `4/4` folds).
- **Automated Verdict (`DO_NOT_SUBMIT`, `verdict: "negative"`):** `gems24-s3dep1-negative-10m-monoclinal-20261026-464fa34b4091-zeros.tif` (`SHA-256: 86516533fb525ebce792152ae4ed852e88ae4feda0bd596710c7319a238b8071`) is **DOWNLOAD: YES (audit) · SUBMIT: NO** — broke parent convergence against `DPRF1` (`64.45% <= 70%`), `B2` (`46.95%`), all 83 peers (`<=54.33%`), and all 32 live `2026-10-26` sibling focus TIFFs (`<=53.17%`), but stopped honestly on `71.32%` (`>70%`) 3-px overlap vs local stopped lane `DKRN1`, exact-file C2ST `AUC = 0.6012` (`holm_p = 0.0200` via unresidualized 10 m highway cut/fill gradients), paired CI vs `DPRF1` spanning zero, and retained `registry-039`. **Do not rerun or retune `S3DEP1`**; verify frozen receipts via `.venv/bin/python scripts/run_s3dep1_lane.py --verify-recorded` (new `benchmarks.recorded_point_best` floor = `0.166060`).
- **Next Recommended Geological Lanes (require fresh preregistration & outbound ScienceBase/STAC/CMR access):** (1) residualize or `<=150 m` road-mask `dem10_*` sub-cell gradients to cure highway cut/fill C2ST; (2) add genuinely external orthogonal grids (`H24-SENT2-HYDRO` Sentinel-2 SWIR clay/ferric alteration, `H24-USARRAY-MT3D` 3D MT `2-15 km` conduits, or `H24-INSAR-OPERA` `DISP-S1` velocity steps) or exclude `100 m` DEM slope/relief/lineament channels (`H24-QPC3` / `H24-RLAG2`) so shared-backbone overlap clears `<= 70%` against `DKRN1`/`DPRF1`/`S3DEP1`/`XVAR1`.

## H24-DKRN1 session — 2026-10-26 (executed `H24-DRAIN5` + `H24-KERN6`; negative; do not retune)

Read `knowledge/27_preregistered_DKRN1_2026-10-26.md` (@ `86d7f622a0ef`), `knowledge/28_DKRN1_findings_and_9site_executive_summary_2026-10-26.md`, `evidence/dkrn1_run_card_20261026.json`, and `evidence/nine_site_executive_summary_dkrn1_20261026.json` first.
- `H24-DKRN1` (`src/gems/dkrn1.py`, `scripts/run_dkrn1_lane.py`) executed the top `AGENTS.md` next-step queue (`H24-DRAIN5` exact sparse triangular D8 flow-routing `(I - P^T)A = 1` + `H24-KERN6` Split-View 47-ch LiDAR-free 300 m DTI-kernel regressor + 62-ch Elkan Bayes core classifier + 48%/28%/24% 3-regime Net-Tversky allocation) across 3 preregistered arms:
  - **Arm 1 (`H24-DKRN1` 62-ch Split-View):** `HOLDOUT-DTI = 0.15525` (`[0.14205, 0.16874]`, `gems-segment-pooled-v1`, `60,988` withheld; `3.0 km` bridge `0.15462`), beating `oof_multiphysics_hgb_d3` (`0.13000`) by `+0.02525` (`[+0.01006, +0.04022]`, `4/4` folds) and **winning `NE_LidarGapHeavy` (`0.21308 > 0.21227`) over `DPRF1`**.
  - **Arm 2 (`HeadA47` pure LiDAR-free 47-ch kernel regressor):** `HOLDOUT-DTI = 0.15072` (`[0.13730, 0.16425]`), outperforming `GVC1` (`0.14876`), `TRSG1` (`0.14644`), `CRP1` (`0.14494`), `CUP1` (`0.14366`), `TNR1` (`0.13219`), `RSHG1` (`0.12899`), and `PAIR1` (`0.12711`) with zero raw 1 m LiDAR amplitude channels.
  - **Arm 3 (`DPRF1` same-session replay):** `0.16416` (`recorded DPRF1 = 0.16379`).
- **Automated Verdict (`DO_NOT_SUBMIT`, `verdict: "negative"`):** `gems24-dkrn1-negative-d8-knick-kernel-20261026-7f031285130c-zeros.tif` (`SHA-256: 0b114a75d5a905ded84450fe55df386f9361ff39139a2e4452476563ac0fa65d`) is **DOWNLOAD: YES (audit) · SUBMIT: NO** — trailed `DPRF1` pooled (`-0.00854`), retained `75.68%` 3-px dot overlap with `DPRF1` (`>70%` Rule-1 limit despite `-10.89` pp reduction vs `EUL1`'s `86.57%`), and flagged exact-file C2ST (`AUC = 0.5773`, `holm_p = 0.0200` via unresidualized `m_hydro` valley wash-road correlation). **Do not rerun or retune `DKRN1`**; verify frozen receipts via `.venv/bin/python scripts/run_dkrn1_lane.py --verify-recorded`.
- **Next Recommended Geological Lane (requires fresh preregistration):** `H24-DRAIN5R-PURE` — pure `HeadA` LiDAR-free 47-channel 300 m DTI-kernel regressor (dropping Head B completely so 3-px overlap vs `DPRF1` clears `<= 70%`) with fold-safe `NuisanceResidualizer` applied to **all** D8 channel-routing operators and `m_hydro` so exact-file C2ST clears `< 0.55`. `H24-DPRF1` (`0.16379`) remains the recorded local point-best (`DO_NOT_SUBMIT` pending selector v2 quota/lattice/replay resolution).

## Latest portfolio continuation — 2026-10-26 e78615fb (read first)

Read the README and `knowledge/owner_brief_2026-10-26_portfolio.md` first.
The new immutable artifact audit is `evidence/portfolio_artifact_audit_20261026.json`;
findings/limits are `docs/portfolio-review-20261026.md`. It reopens 326 TIFFs,
retains all rejects/controls and checks 18 named artifacts against 166/167
comparators. All final-dot gates fail. **DPRF1 additionally overlaps EUL1 by
86.66% in the DPRF1→EUL1 direction**, so a lattice exception would not fix it.
No new TIFF or experiment was run; no submission is authorized. Original
pre-placement surfaces and scientific training runs were not independently
replayed. Do not reinterpret geometric audit numbers as HOLDOUT-DTI.

The raw source and 30-channel cache were restored and hash-checked here; bulk
caches are ignored and can be absent in a fresh sandbox. The current committed
footprint and sample mask are identical (5,167,373 cells), not five cells apart.
GEMSDOE36 already implemented graben-pair features; read the corrected queue in
`knowledge/26_portfolio_plan_corrections_2026-10-26.md`. No lane assignment exists.
Never retune stopped methods or remove controls to pass novelty.

Use new versioned snapshot/registry paths for new source pins. The shared API
cache now honors `--cache-dir` and immutable refs; restoring a frozen registry
must not rewrite its IDs/content. Cached feature reuse must verify checksums
and layout. Run site generation/tests against preserved source-card bytes.
Old review sections below remain historical; newer negative gates take precedence.


## Concurrent records preserved below

The dated snapshot above remains the audited scope; subsequent concurrent files are not silently included.

# Latest c6ea4bb7 continuation — 2026-10-26

Read `docs/review-c6ea4bb7.md` first, then the standing instructions below.
Git-object inventory found 311 added TIFF/ZIP paths and one repaired H33-B2 archive.
This is NOT a pixel novelty audit or a new experiment. Registry pins are unchanged.
No lane was supplied; no new TIFF or slot. Next: content-audit the versioned inventory,
coordinate a distinct lane, retain literal overlap stops and independent selector requirements.

# Standing project instructions

## PAIR1 session — 2026-10-26 (executed lane; negative; do not retune)

Read `knowledge/25_preregistered_PAIR1_2026-10-26.md`, `knowledge/26_PAIR1_findings_and_9site_executive_2026-10-26.md`, `evidence/pair1_run_card_20261026.json` first.
H24-PAIR1 (graben pair/dipole operators on the 20 cached uint8 bands; DPRF1's 419 MB training raster absent in clean checkouts) ran its 3 preregistered experiments: BASE 0.12858, PAIR1 0.12711 (paired Δ −0.00147 [−0.00353,+0.00069], 0/4 folds), clearance-3 identical (non-discriminating, disclosed). New unique research TIFF `docs/downloads/gems24-pair1-graben-dipole-oof-20261026-842a5212d85c-zeros.tif` (SHA `ecf16ef6…5d0f93`) is DOWNLOAD YES / SUBMIT NO. Do not rerun or retune PAIR1 (offsets/weights/seed/budget frozen). DPRF1 remains recorded point-best; selector v2 still `DO_NOT_SUBMIT`. Next cache-ready queued hypothesis: radiometric front phase-lag (knowledge/26 §2 rank 2).
Read `docs/metric-integrity-20261026.md` and `evidence/metric_integrity_review_20261026.json` at session start. The VENT narrative is quarantined; never reuse its metric equations, geological generalizations or projected improvements as verified evidence. No new method lane or submission-ready TIFF was established in that integrity continuation.

## Latest continuation safety review — 2026-10-26

Read `docs/review-20261026.md` and `evidence/review_continuation_20261026.json` first.
No new lane or TIFF was run. Literal DPRF1 overlap fails; no cross-site superiority
or hidden-score causal benefit is established. Shared selector now rejects malformed
numeric evidence without making individual screening gates falsely green. All nine
source refs changed since registry pins; source freshness is not an artifact audit.
The exact-file zero variant passes strict range/grid checks, but inherited official
NaN-outside convention differs. Sample/science footprint discrepancy is recorded,
not repaired by changing frozen evidence. No human-inspection override.

Read `knowledge/22_current_best_review_2026-10-26.md` and the README current continuation review first. `scripts/review_current_best.py` revalidates the recorded local point-best without retraining or promotion. No new lane was assigned or experiment run in that continuation. The literal uniqueness failure remains binding; current-best/cross-site superiority and scientific replay are distinct. Historical `active_lane.json` is lane identity, not the current-best selector.

## Latest 2026-10-26 point-best continuation: H24-DPRF1 & Nine-Site Executive Summary

Read `knowledge/owner_brief_2026-10-26.md`, `knowledge/owner_brief_2026-10-25.md`, and the current README decision first.
- `H24-DPRF1` (`src/gems/dprf1.py`, `scripts/run_dprf1_lane.py`, `knowledge/19_preregistered_DPRF1_2026-10-26.md`, `knowledge/20_DPRF1_findings_and_9site_executive_summary_2026-10-26.md`, `evidence/dprf1_run_card_20261026.json`, `evidence/dprf1_selector_20261026.json`) achieves the repository point-best **`HOLDOUT-DTI 0.16379`** (`[0.15045, 0.17739]` on `gems-segment-pooled-v1`, winning `4/4` spatial folds over `oof_multiphysics_hgb_d3` `0.13000`, `B1` `0.13900`, `B0` `0.14179`, and exceeding `CUP1` `0.15038`, `GVC1` `0.14876`, `CRP1` `0.13747`, and `TNR1` `0.13219`) and **`0.16290`** (`[0.14449, 0.18118]`) on `3.0 km` `segment-hide-recover-pooled-v1`.
- Passes **57/57** competing method rasters (`max 3-px overlap = 0.5578 <= 0.70`, incl. `0.3613` vs `TNR1`, `0.3398` vs `CRP1`, `0.3381` vs `CUP1`), **83/83** peer blobs (`0.5494 <= 0.70`), **52/52** two-polarity leakage canaries (`<= 0.6111 <= 0.90`), strict exact-file C2ST (`AUC = 0.5247 < 0.55`, Holm `p = 0.100`), and Dual-Partition Stitched-OOF far-field coverage (`52.3%` `>2 km` vs `22.3%` in `2-9 px`).
- Remains **`DOWNLOAD: YES · SUBMIT: NO` (`DO_NOT_SUBMIT`, `verdict: "negative"`)** under `gems-selector-v2-literal-quota-fail-closed` (retained `registry-039` spacing-5 calibration lattice, unknown live DrivenData quota, and missing independent replay certificate). Verify without rerunning via `.venv/bin/python scripts/run_dprf1_lane.py --verify-recorded`.

## Concurrent continuation decision (2026-10-26): TNR1 stopped; verification only

Read the README current decision and full `knowledge/owner_brief_2026-10-26.md`
**every session**. Latest preregistration/findings: `knowledge/20_preregistered_TNR1_2026-10-26.md`
and `knowledge/21_TNR1_findings_2026-10-26.md`.

- TNR1 already ran once with its fixed matched raw control. It is negative and
  stopped as duplicate. Do not rerun, reweight, move dots, remove controls or
  change the seed/budget/threshold to escape the result.
- Newly generated exact research TIFF: `docs/downloads/gems24-tnr1-56dfd14b88db-20261026-RESEARCH-NOT-SUBMISSION-zeros.tif`.
  SHA-256 `c8cb320c2c776e64c2d198bfc2e28338e7e354b6d827550f09464b413f0a8a90`.
  **DOWNLOAD YES / SUBMIT NO**, not human inspection pending. The requested
  fully unique, submit-ready prediction remains unachieved.
- TNR1 HOLDOUT-DTI 0.13219, 95% CI [0.11791,0.14546],
  `gems-segment-pooled-v1`, 60,988 withheld positives. No detected paired benefit
  over its matched control and below GVC1 at execution. Later CUP1 (`0.15038`) and DPRF1 (`0.16379`)
  recorded point-bests on the same evaluator/count remain negative under v2;
  do not use an outdated/easier best for future screening.
- Protected 19 deformation/terrain channels; residualized exactly 12. Fixed
  HGB; no HCW weights. Do not recast another residualization rerun as untested.
- Final 3-px overlap fails against real competing methods (74.89% maximum) as
  well as the retained lattice (100%). Changing only the control policy cannot
  authorize this file. New bytes are not scientific lane uniqueness.
- Verification only: `.venv/bin/python scripts/evaluate_holdout.py --verify-tnr1`
  or `scripts/run_tnr1_lane.py --verify-recorded`; exact-file preflight remains
  negative. No assigned single-method paragraph/verified replay-and-quota
  authorization receipt exists. No slot was used.
- All 92 owner-listed READMEs were retrieved at immutable commits, byte-identity
  checked and inventoried (118 historical artifact claims). This does not verify every claim,
  organizer score or every current raster. The frozen TNR1 raster union covers
  117 contents / 167 aliases, not all current TIFFs in 92 repositories.
- A single-output broadcast bug was fixed centrally in `gems.residualize` and
  regression-tested before science. Old stopped lanes remain untouched.

The older dated continuation notes below are historical, not newer authority.


**CUP1 continuation (2026-10-26):** Read `knowledge/20_preregistered_CUP1_2026-10-26.md`,
`knowledge/21_CUP1_findings_2026-10-26.md` and `evidence/cup1_run_card_20261026.json` first.
CUP1 (HOLDOUT-DTI 0.15038) is DOWNLOAD YES / SUBMIT NO: paired CI vs matched
B-GVC crosses 0 and 91.2% of dots sit within 3 px of parent GVC1. Do not rerun/retune CUP1,
and do not treat a minor increment as a fresh assigned lane. One negative result does
not prove inevitable convergence of every future model. Prospectively prioritize
orthogonal hypotheses; SGMC-sparse is an additional diagnostic, not a replacement
for the mandated spatially blocked primary endpoint. The current selector is
negative-only: positive replay certification and actual account quota remain
unverified, so no slot can be authorized from card booleans.

**CRP1 continuation (2026-10-26):** Read `knowledge/20_preregistered_CRP1_2026-10-26.md`,
`knowledge/21_CRP1_findings_2026-10-26.md` and `evidence/crp1_run_card_20261026.json` first.
H24-CRP1 (compositional radiometric fronts + cross-depth TMI/up150 persistence +
Hessian saddles, selective residualization) is STOPPED as duplicate/negative:
HOLDOUT-DTI 0.13747 [0.12400, 0.15152] (`gems-segment-pooled-v1`, 60,988 withheld),
paired Δ vs reconstructed OOF baseline +0.00747 [-0.00242, +0.01793], final-dot
overlap 0.8070 > 0.70 (max |ρ| 0.5878), canary/C2ST/format PASS. DOWNLOAD YES /
SUBMIT NO. Do not rerun or retune it (including residualization strength).
The parallel PR #29 selector v1 is preserved historically. Current `gems.selector`
v2 is a negative-only recorded-evidence screen: literal controls are retained,
unknown quota blocks, and complete independent positive replay is not implemented. Preflight schema v2 still requires its own selector receipt
format — wiring the two is future work, do not change preflight semantics silently.
Owner-reported nine-site list updated in `registry/owner_reported_scores_2026-10-26.json`
(includes an unverified 0.0859 claim from the 2026-10-26 brief; no artifact-linked
organizer receipt establishes a live score; pixel-distance forensics on GVC1's
Stage-5 in-sample apron clustering are recorded in `knowledge/20_DPRF1_findings_and_9site_executive_summary_2026-10-26.md`). Parallel PR #28 (`knowledge/20_repo_review_2026-10-26.md`)
shares the `knowledge/20_` prefix with the CRP1 preregistration by coincidence;
both files remain.

**OJ1 continuation (2026-10-25):** Read `knowledge/17_preregistered_OJ1_2026-10-25.md`,
`knowledge/18_OJ1_findings_2026-10-25.md`, and `evidence/oj1_run_card_20261025.json` first.
OJ1 stopped as duplicate-final-dots (spacing-5 control retained), loses the recorded
OOF baseline, and is DOWNLOAD YES / SUBMIT NO. Do not rerun or retune it.
Historical UNIQUE01/02/03, CON and FUSE entrypoints are retired; source/evidence
remain for education. UNIQUE03 executed a 30 km decay, not its advertised 300 m;
its proximity/composite canaries were not run. Never present it as catalogue-independent.
Shared preflight schema v2 refuses to authorize from promote booleans alone;
complete independent selector/quota verification is missing, not a human-inspection pending state.


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

## Continuation — 2026-10-26 H24-EUL1 (Euler N=0 contact): NEGATIVE, DPRF1 still point-best

- EUL1 (prereg `knowledge/22_…` @ `b841bf4`, amendment `knowledge/23_…`, findings
  `knowledge/24_…`) added 7 label-free Euler-deconvolution channels + Euler-gated
  Regime B to DPRF1's exact 52-ch stack: HOLDOUT-DTI **0.16005** [0.14729, 0.17278]
  vs same-session DPRF1 replay **0.16379** (bit-identical DTI+CI; paired Δ −0.00375,
  1/4 folds; channels alone 0/4). Final-dot overlap with DPRF1 **86.57%** → duplicate
  lane; selector v2 `DO_NOT_SUBMIT`; zero slots spent. **Do not rerun or retune EUL1**
  (no looser Euler acceptance, no channel subsetting, no new gating) without a new
  preregistration and a genuinely different detection geometry.
- `IRR-EUL1-VG-BANDS`: bridge `*_vg` bands are NOT certified derivatives
  (`tmi_vg`=∂(`tmi`)×0.00990/px corr 0.9965; `iso_grav_anom_vg` vs ∂(`iso_grav_anom`)
  corr −0.19; `tmi_hg`=2.0000×|∇`tmi`|). Multi-derivative operators must derive their
  derivatives self-consistently (see `gems.euler.fft_vertical_derivative`).
- Parent-convergence is the binding constraint now (CUP1 91.2%, EUL1 86.6% dot
  overlap with their parents): appending channels to DPRF1 cannot clear the 70%
  Rule-1 ceiling. Next lane candidates (fresh prereg required): `H24-DRAIN5`
  flow-routing knickpoints, `H24-KERN6` DTI-kernel soft labels, `H24-INSAR4`
  NASA OPERA (unreachable from this sandbox — only github/pypi respond).
- Immediate next step remains the DPRF1 selector/quota authorization step
  (live-quota receipt, lattice policy separation, independent replay certificate).
  DPRF1 stays the strongest unscored unique candidate; everything else SUBMIT: NO.
- Verify: `.venv/bin/python scripts/run_eul1_lane.py --verify-recorded` and
  `.venv/bin/python scripts/run_dprf1_lane.py --verify-recorded`.

## Continuation — 2026-10-26 H24-XFRONT (cross-modal oriented-step corroboration): NEGATIVE

- XFRONT (prereg `knowledge/25_…` @ `3ebb375`, amendments `knowledge/26_…` ≥2-layer
  corroboration and `knowledge/27_…` pre-specified ablation arm, findings
  `knowledge/28_…`) is a label-free six-layer detector: across-strike step percentile
  weights and structure-tensor orientations for `rtp`, `iso_grav_anom`,
  `depth_to_base_surf`, `cond_surf`, `det_elev`, `geod_shearrate` at σ ∈ {1.2, 3.0};
  C = Σw/6; R = |Σw·e^{2iθ}|/Σw; E_R = excess over a 19-draw translation null
  (seed 20261026); arm A = C·E_R, arm B = C alone; zero where Σw < 2.0.
- Result: **HOLDOUT-DTI 0.06584** [0.05497, 0.07904] at the selected arm **B** /
  budget **45,000** (`gems-segment-pooled-v1`, 60,988 withheld positives, 39,456 dots)
  — far below DPRF1's 0.16379. Pre-specified ablation: arm B beats arm A by
  **+0.00644** [+0.00132, +0.01243] (4/4 folds), i.e. the rotation-null orientation
  factor is actively harmful. Arm×budget sweep is monotone in budget over
  15k–45k: a boundary optimum, so the detector is under-emitting throughout.
- Novelty **PASS** (max |ρ| 0.1304; max 3-px dot overlap 0.4532 over 61 competing
  method rasters and 83 peer blobs; only 0.2483 vs DPRF1) — the least
  parent-convergent lane run to date and still 2.5× worse than DPRF1. Divergence
  from the parent is therefore necessary but nowhere near sufficient.
- Exact-file C2ST **FAILED** (AUC 0.5835, Holm p 0.02, nuisance families only;
  labels-first 0.5040): part of the "corroboration" is road/claim/access structure.
  Do not reframe this flag as noise.
- **Do not rerun or retune XFRONT** (no new null, no new σ, no reweighting, no budget
  extension) without a new preregistration. A rotation/strike-permutation null — not
  translation — would be the correct test of the orientation idea.
- Sparse-simulated DTI is sampling-density dependent (0.05283 / 0.02931 / 0.02302 at
  20% / 10% / 5% truth sampling): always state the fraction.
- Verify: `.venv/bin/python scripts/run_xfront_lane.py --verify-recorded` (frozen
  experiment file `evidence/xfront_experiment_20261026.json` + card + selector).
