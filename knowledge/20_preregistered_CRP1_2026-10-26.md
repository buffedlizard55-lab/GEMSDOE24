# Preregistration — H24-CRP1 (2026-10-26) — FROZEN BEFORE IMPLEMENTATION

Session branch: `arena/12195834-gemsdoe24`, base `main @ 758af9f` (PR #27 merged).
Budget (Parallel-Run Protocol §6): **1 experiment** planned (max 3 / 2 h), **0 submission slots**.
This file is committed before the lane code is written or run. No parameter below
may be changed after seeing holdout or novelty results; a stop is a deliverable.

## Previous-session next steps executed first (in order)

1. Read README current decision, `AGENTS.md`, `knowledge/19_priority_review_2026-10-26.md`,
   `knowledge/14_h33_analysis_2026-10-25.md`, GVC1/RSHG1/FUSE/SAHG1 run cards. Stopped
   lanes (MTR1, OJ1, ASPC, SAHG1, CON, FUSE, RSHG1, GVC1, H-UNIQUE-03) are **not rerun or retuned**.
2. `scripts/verify_featured_downloads.py` re-run: featured GVC1/RSHG1 research TIFFs
   format-valid, `ok_to_download=true`, `ok_to_submit=false` (unchanged).
3. Data restored with existing tools only: `scripts/restore_data.py` (419 MB bridge,
   sha256 `4371c82e…3bc5`, owner mirror — integrity only, not organizer authentication),
   `scripts/prepare_data.py` (30-column stack, sha256 `a4ca25b2…2dc8`),
   `scripts/cache_priority_registry.py` pinned snapshot (46/46 unique registry rasters
   cached; GitHub REST rate limit hit afterwards — peer blobs fetched via codeload
   tarballs at the same pinned revisions, blob-sha1 asserted per file).
4. README "Remaining next steps" item adopted as this lane's nuisance policy:
   **targeted (selective) residualization of non-topographic bands only**.
   `knowledge/19` items: no lane paragraph was supplied by a coordinator — this
   session's owner brief itself instructs generating and validating the top ranked
   hypothesis; that instruction is recorded here as the lane assignment source.
   The literal spacing-5 comparator is **not** removed; prospective separation
   (`compare_prospective_registry`, already in `src/gems/novelty.py`) is the
   pre-existing policy and both verdicts will be reported.

## Why GEMSDOE32 H33-B2 (0.2778, OWNER-REPORTED, UNVERIFIED) leads the nine-site list

Local forensic identity (recorded, `evidence/priority_review_20261025.json`,
`knowledge/13_GVC1_findings_2026-10-25.md` §1): H33-B2 = the 44,090-dot
H27-4/D2.8 emission with the 6,436 dots within 2 px of `existing_faults.tif`
deleted and **0 dots added** → 37,654 dots. It is an emission-policy change on
H19-5 ancestry, not a new detector. Under DTI `T/(0.2T+0.2F+0.8G)` (α=0.2, β=0.8,
300 m triangular kernel), deleting a batch helps iff its lost TP credit / saved
FP mass `< αD/(1−(1−β)D) ≈ 0.055` at D≈0.26; near-catalogue dots lose most of
their kernel footprint to the pixel-exact catalogue mask, so they are the most
plausible low-credit/high-FP batch. Hidden TP/FP of the deleted dots are unknown,
so causality is **not** established. No organizer receipt exists for 0.2778,
0.3195 or 0.4413; the latter two conflict in the brief. Beating 0.2778 is
therefore a hypothesis to test, never a forecast: it requires new detector
signal at full 100 m resolution **plus** H33-style sparse binary emission
(clearance >2 px, spacing ≥3 px, ≈37–38k dots). Cautionary evidence: the
owner's updated list reports GVC1 (this repo's holdout-best, HOLDOUT-DTI
0.14876) at 0.0859 live — dense-catalogue holdout rank does not guarantee
hidden-set rank (truth density ≈5× lower; `AGENTS.md`).

## Ranked untried geological hypotheses (4) — top one executed

| # | Lane | Layers / physical signature | Why a *missing* fault, not a mapped one | Difference from everything in this repo | Cost / data |
|---|---|---|---|---|---|
| 1 | **H24-CRP1 (EXECUTE)** | GeoDAWN contractor ratio grids UK/UTh/ThK + K/Th/U ranks (`geodawn_extensions_u8`, `geodawn_rad_u8`): compositional-balance fronts \|∇logit(rank)\|, UTh-stability gating, rank-space K-vs-(Th,U) balance; cross-depth magnetic persistence: rank(TMI) vs contractor TMI upward-continued 150 m — residual + gradient-magnitude/direction agreement; DEM/gravity Hessian **saddle** strength √(relu(−λ₁λ₂)) at σ=3,6 px. Fed with the prepared 30-ch stack into fold-local HGB with **selective** nuisance residualization (airborne bands only). | Hydrothermal alteration changes mobile-element (K,U) balance across a concealed fault while Th (immobile) stays stable — a compositional front can cross alluvial cover with no scarp and no catalogue proximity. A basement fault persists between shallow TMI and its 150 m upward continuation; surficial float does not. Step-overs/relay ramps (saddles) are where mapped traces stop but the structure continues. Zero catalogue-distance features. | No prior lane used contractor ratio grids as compositional coordinates (SAHG1 used scalar K/U `R_alt`; MTR1 scalar Th/K), none used the contractor upward-continued TMI for cross-depth gradient agreement (RSHG1 `tmi_shallow_res` is single-source smoothing), none used Hessian saddle sign (RSHG1 used ridge eigenvalue), none residualized selectively by band family. | Low–medium; all layers committed & hash-pinned in this repo; CPU only. |
| 2 | Drainage-deflection graph | DEM D8 stream network: displaced channel continuations, persistent azimuth breaks | Buried cross-valley fault deflects drainage without a scarp | Network topology vs all prior pixel operators | High; 100 m DEM may not resolve channels; finer source = USGS 3DEP https://www.usgs.gov/3d-elevation-program/data-tools — host not allowlisted here, tile obtainability NOT verified → not viable this session |
| 3 | Valley-floor blind-fault gate | Low-relief mask × potential-field persistence only | Catalogue is scarp-biased; valley faults are systematically unmapped | Domain restriction no prior lane used | Medium; dense holdout is biased against it — needs its own sparse-regime primary endpoint; deferred |
| 4 | InSAR LOS gradient | Sentinel-1 OPERA DISP-S1 velocity gradient | Fault-core gouge → hydraulic-head step on flat playas, zero scarp | Independent radar physics | High; source NASA ASF DAAC https://asf.alaska.edu/datasets/daac/opera/ — not obtainable from this sandbox → not viable |

Ranking is expected incremental information per implementation cost. **No numeric
DTI improvement is forecast for any row.**

## H24-CRP1 frozen specification

**Inputs (hash-pinned, committed):** `data/prepared/features.npy` (30 ch),
`data/training_features.tif` (19 ch, band order `gems.geofeatures.BAND_ORDER`),
`data/external/geodawn_extensions_u8.tif` (ThK,UK,UTh,TMI_up150),
`data/external/geodawn_rad_u8.tif` (K,Th,U,TC), `data/bridge/labels.tif`,
`data/bridge/sample_submission.tif`, confounds via `gems.confounds.build_all`
(roads, closed claims, 4 derived acquisition blocks — derived, not official coordinates).

**New label-free channels (10)** — computed from pixel values only; no labels,
no catalogue distances, no prior submission pixels. u8 caches are percentile
ranks (1..255, 0=nodata→NaN); `logit(v/255)` is a **monotonic rank score, not a
physical log-ratio** (disclosed limitation). Gradients σ=1 px after nearest-valid
fill used only inside the transform; source-invalid pixels restored to NaN.
1. `crp_uk_front` = |∇ logit r_UK|
2. `crp_uth_stable_front` = `crp_uk_front` · exp(−σ₅(logit r_UTh)) (σ₅ = 5×5 local std)
3. `crp_thk_front` = |∇ logit r_ThK|
4. `crp_ilr1` = logit r_K − ½(logit r_Th + logit r_U) (rank-space balance proxy)
5. `crp_ilr1_front` = |∇ crp_ilr1|
6. `crp_xdepth_resid` = rank_footprint(TMI) − r_TMIup150
7. `crp_xdepth_persist` = min(|∇rank TMI|, |∇r_up150|) · relu(cos Δθ_grad)
8. `crp_dem_saddle3`, 9. `crp_dem_saddle6` = √(relu(−λ₁λ₂)) of DEM Hessian, σ∈{3,6} px
10. `crp_grav_saddle3` = same on `iso_grav_anom`, σ=3 px

**Selective residualization** (`rshg1.NanPreservingResidualizer`, α=100, fit on
≤30k training-fold background rows, nuisance = log1p road_m, log1p claim_m,
block_1..4): residualize ONLY `rtp, tmi_hg, tmi_vg, tmi, cond_surf,
depth_to_base_surf, iso_grav_anom, iso_grav_anom_hg, iso_grav_anom_vg, arc_rtp`
and CRP channels 1–7. Never residualize DEM/LiDAR/strain/saddle channels.
No regime calibrator (that is RSHG1's mechanism, not reused here).

**Model:** per `SegmentHoldout` fold (buffer 15 px): positives = `train & visible`
(≤30k sampled), negatives = `train & ~visible & EDT(visible)≥9 px` (≤90k),
2× `HistGradientBoostingClassifier(max_iter=140, max_leaf_nodes=31,
min_samples_leaf=80, learning_rate=0.06, l2=8.0)`, seeds `20261026+10·fold+{0,1}`,
probability = seed mean. Deployment: same recipe refit on full footprint
(pos = full catalogue), seeds `20261026+900+{0,1}`.

**Emission (shared `rshg1.emit_rshg1_dots`):** kernel-trace score,
`flank_clearance_px=2.0` (EDT>2 from visible/full catalogue — the H33 mechanism),
`min_dist=3.0`, `budget_frac=0.0073` of domain (≈37.7k dots full footprint).

**Evaluator:** `gems-segment-pooled-v1` via `SegmentHoldout` (whole components
hidden everywhere, 1,500 m buffer, visible-only masks, pooled TPw/FPw/FNw,
α=0.2, β=0.8, 300 m kernel, 1,999-draw 10 km block bootstrap).
Baseline reconstructed in-session with the recorded RSHG1-script recipe
(`oof_multiphysics_hgb_d3`, must reproduce HOLDOUT-DTI 0.13000 ±1e-6 or STOP)
for the paired block-bootstrap Δ. Recorded best on this evaluator:
GVC1 HOLDOUT-DTI 0.14876 (60,988 withheld positives).

## Pre-registered gates — ALL must pass for `promote`; any fail ⇒ `negative`, no retuning

- **G1 format:** shared writer zeros variant: single-band float32, EPSG:32611,
  template shape/transform, finite [0,1] over the **whole array** (strict variant).
- **G2 leakage canary:** every one of the 40 features alone on the holdout,
  both AUC polarities ≤0.90 (`SegmentHoldout.canary`); OOF surface canary too.
- **G3 holdout:** pooled HOLDOUT-DTI point estimate **> 0.14876** (recorded GVC1)
  **and** paired Δ vs in-session OOF baseline 95% CI strictly > 0.
- **G4 novelty (Protocol §1):** surface before placement AND final dots:
  |ρ| ≤0.90 vs every registry entry (controls included); final-dot ≤3 px overlap
  ≤0.70 vs every **competing method** raster (46 priority + local ASPC/MTR1/SAHG1/
  CON/FUSE/RSHG1/GVC1/OJ1) and vs peer blobs. Literal all-entry result reported;
  a literal failure caused solely by the spacing-5 calibration lattice
  (pigeonhole-bound ≥0.70 for any candidate) is reported, not hidden. If the
  pre-placement surface exceeds |ρ|>0.90 vs any entry → STOP before placement.
- **G5 exact-file C2ST:** strict nuisance gate on the written zeros TIFF
  (labels audited first), as in RSHG1/GVC1 packets.
- **G6 independent selector:** new `gems.selector` verifier re-derives the
  decision from artifact bytes + run card (hashes, G1–G5 evidence, note ≤140
  chars, experiments ≤3, slots used = 0) and issues the only `ok_to_submit`
  flag. Quota on the organizer account cannot be read from here (DrivenData
  automation prohibited); selector records `quota_status="unknown_owner_must_confirm_on_submission_page"`
  even on PASS. The agent never uploads.

On any failure after dots exist: export the unchanged dots as a NEGATIVE
research GeoTIFF pair (zeros + NaN twins), `DOWNLOAD: YES · SUBMIT: NO`.

**Named non-fault mimics:** transported arkosic alluvium / lithologic contacts
(compositional fronts), magnetite-poor palaeochannel or remanence
(cross-depth persistence), pluvial shoreline / wind-scoured saddle
(DEM saddle), flight-line levelling seams (all airborne channels).

**Score labelling:** every local number = HOLDOUT-DTI (evaluator, withheld
positives, 95% CI); every competition number in the brief = OWNER-REPORTED,
UNVERIFIED. No ORGANIZER-CONFIRMED score exists in this repo. Fault recovery
is the benchmark target — no geothermal-vent, heat or permeability claim.
