# Preregistration: `H24-DRAIN5` — D8 Drainage-Network Knickpoint & Deflection Channels in Dual-Partition Stitched-OOF (2026-10-26)

**Status:** Locked prior to implementation of `src/gems/drainage.py`, prior to any
holdout fit, and prior to exporting any raster in this session. Branch
`arena/30f63db6-gemsdoe24`, base commit `46f663dad1a1c3d8231e5de5dbad4ee4d19e8d56`
(PR #38 merged into `main` and merged into this branch before any science).
**Seeds (locked, identical to DPRF1/EUL1):** master `SEED = 20261026`, GVC base seed
`20261025`, fold seeds `SEED + 10*fid`, rotated-diamond seeds `SEED + 500 + 17*rfid`.
**Budget:** this is experiment 1 of at most 3 this session (3 locked arms of one lane,
as in EUL1); zero weekly submission slots; no DrivenData contact (its Terms of Use
forbid automated access — see `AGENTS.md`).

---

## 1. Why this lane, and what beating 0.2778 would actually require

The prompt's `0.2778` for `GEMSDOE32 h33-h33-2-b2` — like the conflicting `0.3195` /
`0.4413` "current leader" figures — is **UNVERIFIED-OWNER-REPORT**: no artifact-linked
DrivenData receipt exists in git, so nothing here may be labelled ORGANIZER-CONFIRMED
(Parallel-Run Protocol Rule 3). What *is* geometrically proven
(`knowledge/14_h33_analysis_2026-10-25.md`, restated in
`knowledge/24_EUL1_findings_and_executive_summary_2026-10-26.md` §1): B2 = the 44,090-dot
Poisson-thinned `H19-5` surface (`D2.8`) with all 6,436 dots at catalogue distance
≤200 m deleted and **zero dots added** (37,654 dots; 49.2% at >2 km). Under the
distance-weighted Tversky metric `DTI = T/(T + 0.2F + 0.8N)` (300 m triangular credit),
deleting near-catalogue dots that mostly duplicate neighbours' credit while adding FP
mass next to already-masked known faults raises the score; sparse, catalogue-cleared,
far-field-tilted emission is the transferable lesson, and DPRF1 already embodies it
(37,654 dots, 0% ≤2 px, 52.3% >2 km). **That emission geometry is saturated.** Every
further gain must come from a better *detector surface* — ranking fault pixels highly
that `H19-5`-descended surfaces never ranked — proven on a paired, spatially blocked
hide-and-recover holdout, never asserted as a leaderboard forecast. HOLDOUT-DTI hides
*mapped* segments (dense regime); the leaderboard hides *unmapped* faults (sparse
regime); the two are correlated through detector quality but not interchangeable, so
no local number licenses a ">0.2778" claim.

The current recorded local point-best is **H24-DPRF1: HOLDOUT-DTI 0.16379**
(95% CI [0.15045, 0.17739], `gems-segment-pooled-v1`, 60,988 withheld positives;
re-verified this session by `scripts/run_dprf1_lane.py --verify-recorded`). It remains
`SUBMIT: NO` under `gems.selector` v2 (literal `registry-039` lattice retained, live
quota unknown, independent positive replay certificate unimplemented). Yesterday's
EUL1 lane taught the binding constraint: appending correlated channels to DPRF1
re-selects its dot lattice (EUL1: 86.57% of dots within 3 px of DPRF1 → duplicate,
paired Δ −0.00375). The documented next-step queue (`AGENTS.md`, EUL1 findings §6)
names exactly two fresh lanes that change *evidence or target geometry* rather than
appending another view of the same fields: **H24-DRAIN5** (flow-routing knickpoint
graph — new evidence geometry) and **H24-KERN6** (DTI-kernel soft-label regression —
new target geometry). This session locks **DRAIN5** (rank 1 below).

## 2. Candidate hypotheses, ranked (prompt requirement; 5 candidates)

| Rank | Candidate (lane id) | Layer(s) involved | Physical signature targeted | Why it should catch a fault *missing* from the USGS/INGENIOUS catalogue | Named non-fault mimic | How it differs from everything implemented in this repo | Expected DTI value / cost / external-data viability |
|---|---|---|---|---|---|---|---|
| **1 (SELECTED)** | **H24-DRAIN5** drainage-network knickpoints & deflections | Competition `det_elev` (100 m DEM, already cached as prepared-stack column) only | D8 single-flow-direction routing: upslope contributing area `A(x)`, normalised channel steepness `k_sn = slope·A^0.45`, downstream knickpoint jump `Δk_sn`, 8-azimuth co-linearity of channel-gated knickpoints, height-above-nearest-channel (HAND), distance-to-channel, flow-azimuth bend | Oblique/strike-slip and rapidly eroded piedmont normal faults lose their interfluve scarp to sheetwash in 10³–10⁴ yr while ephemeral washes keep aligned knickpoints and bayonet deflections where they cross the buried trace; mappers working from imagery/scarps systematically miss exactly these | Resistant lithologic hogbacks (welded tuff/dike ribs) making lithologic knickpoints across parallel gullies; alluvial fan-lobe avulsion channels; Lake Lahontan strandlines; road borrow ditches | **No flow routing exists anywhere in this repo.** All geomorphology is local filters (≤9×9 stencils, Gaussian/Hessian). TRSG1's `piedmont_drainage_break` is a local slope-Laplacian sum (`src/gems/trsg1.py:449-478`), not network topology: it has no contributing area, no downstream ordering, no cross-catchment alignment | Uncertain at 100 m (+0.000…+0.010 hoped, concentrated on piedmont/range-front folds; no score forecast). Cost medium (one label-free routing build, minutes; reuse DPRF1/EUL1 machinery). **No external data needed** — fully viable in-sandbox. The finer 10 m variant (USGS 3DEP 1/3 arc-sec, free/official: https://apps.nationalmap.gov/downloader/) is **not obtainable here**: host unreachable from sandbox (checked 2026-10-26T16:18Z, HTTPS code 000; `github.com` returns 200) — coarse 100 m variant only, disclosed |
| 2 | **H24-KERN6** DTI-kernel soft-label regression | DPRF1 52-channel stack; target derived from `fold.visible` only | `HistGradientBoostingRegressor` on kernel-credit target `y(x)=max_g(1−d(x,g)/3px)` instead of binary labels | Centres predicted mass on fault cores in the metric's own credit geometry; may recover segments whose binary-classifier response is smeared along-strike | Smears credit onto parallel non-fault lineaments 100–300 m away | Every supervised lane here is binary classification; none regresses the metric kernel | Cheap, but it is an objective change, not new geological evidence; the submodular allocator already optimises kernel cover on the classifier surface. Deferred behind rank 1; first choice next session if DRAIN5 is negative |
| 3 | **H24-SEGBAL7** per-component-balanced training weights | DPRF1 52-channel stack; `fold.visible` components only | Sample weights `w ∝ 1/len(component)` so short concealed segments count equally with long mapped range-fronts during HGB fitting | Hidden faults are plausibly the *short, low-throw* segments that pixel-uniform training under-weights by construction | Short cultural lineaments (fence lines, short road cuts) get up-weighted too | All lanes sample pixels uniformly (25k pos cap); none balances by segment | Cheap. Risk: pooled HOLDOUT-DTI is pixel-weighted, so this can *hurt* the primary endpoint while helping the hidden regime — an endpoint conflict that needs its own preregistration. Deferred |
| 4 | **H24-INSAR4** Sentinel-1 LOS velocity steps | NASA ASF DAAC `OPERA_L3_DISP-S1_V1` (free, official: https://asf.alaska.edu/datasets/daac/opera/) | Cross-strike `|∇⊥ v_LOS|` (mm/yr) at fault-gouge groundwater barriers in flat playas | Poroelastic subsidence steps occur where DEM/LiDAR show literally nothing (Carson/Humboldt sinks) | Aquifer pinch-outs, evaporite heave | No radar data anywhere in the portfolio | Potentially high in playas but **not viable this session**: `asf.alaska.edu` unreachable from sandbox (checked 2026-10-26T16:18Z, HTTPS code 000). Named source is free/official for an unrestricted machine; not proposed as runnable here |
| 5 | **H24-3DEP8** raw 1 m gully-offset graph | USGS 3DEP 1 m DEM tiles (706 tiles inventoried in `data/external/lidar_scarp_features.json`; official bucket `https://prd-tnm.s3.amazonaws.com`) | Metre-scale lateral gully offsets + synchronous knickpoints across ≥3 adjacent 1 m channels | Strike-slip offsets of 2–15 m survive in gullies long after the scarp is gone | Lithologic ash-bed knickpoints, OHV ruts | `lidar_scarp_features_u8.tif` keeps only per-100 m summary amplitudes, never a channel graph | Potentially high, **not viable here**: >200 GB staging, host outside sandbox allowlist, 19 GB free disk. Deferred to external high-storage compute |

## 3. Locked DRAIN5 channel definitions (label-free; computed once from `det_elev`)

All seven channels derive **only** from the prepared-stack `det_elev` column
(competition band 12; finite on 5,164,312 of 5,167,373 footprint pixels, verified
2026-10-26). No label, catalogue, registry or prior-submission pixel is read.
Routing domain = footprint pixels with finite `det_elev` ("valid cells"). The DEM is
nearest-filled **only** to evaluate the Gaussian smoothing stencil, then smoothed at
σ = 2 px (200 m) to suppress 100 m sampling pits; channels are `NaN` wherever the
original DEM is invalid (native HGB missing-value routing). **No depression filling:**
a cell whose 8 neighbours are all ≥ its smoothed elevation (or invalid) is a *sink*
(self-receiver; accumulation terminates) — the physically correct endorheic behaviour
for Great Basin playas, disclosed as a limitation for through-flowing reaches that
cross DEM pits. Receivers: D8 steepest descent, drop/distance (diagonals ÷√2), fixed
neighbour order `[(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]`, first-max
tie-break. Accumulation `A` (upslope cell count, self excluded) by processing valid
cells in strictly descending smoothed-elevation order (exact for D8 DAGs whose every
edge descends). Slope `S` = gradient magnitude of the same smoothed DEM (m/m, pixel
size 100 m). Channel mask `C100: A ≥ 100` cells (≈1 km² contributing area).

1. `drn_log_accum` = `log10(1 + A)`.
2. `drn_ksn` = `S · (max(A,1))^0.45` (normalised channel steepness proxy, θ_ref = 0.45).
3. `drn_knick` = `k_sn(x) − k_sn(recv(x))` (downstream steepness drop; >0 at a
   knickpoint lip), gated to `A ≥ 20`, `NaN` at sinks and below the gate.
4. `drn_knick_lineament` = `gems.gvc.oriented_lineament_response` (8-azimuth, the
   shared operator) of `max(drn_knick, 0)` on `A ≥ 20` cells after Gaussian σ = 1.5 px
   smoothing — co-linear knickpoints across adjacent washes respond as a line across
   strike. (Exact call parameters fixed in code before any fit; defaults of the
   shared operator.)
5. `drn_chan_dist` = `log1p(EDT distance in px to nearest C100 cell)`.
6. `drn_hand` = `z(x) − z(nearest C100 cell)` from the same EDT indices (metres,
   clipped to [−50, 500]).
7. `drn_bend` = `1 − cos(Δ azimuth)` between `x→recv(x)` and `recv(x)→recv²(x)`,
   gated to `A ≥ 20`, `NaN` where either link is a sink.

Regime-B gating names (Arm 1): `(drn_knick, drn_knick_lineament, drn_ksn)` averaged
into `B_sub` via the existing `TrainQuantileGateScaler.score_regime_b_multiplier`
`extra_subsurface_names` mechanism. **Selective residualization: drainage channels
are NOT added** — they are terrain-derived like the protected topographic channels,
not regional-survey/access fields (`selective_extra_names = ()`).

Diagnostics recorded with the build (label-free census, reported verbatim): valid
cell count, sink count/fraction, channel-cell count at `A ≥ 100`, max/median `A`,
per-channel finite fraction on the footprint.

## 4. Locked protocol (reuse, don't rebuild — Rule 2)

Shared machinery, unchanged semantics: `gems.holdout.SegmentHoldout`
(`gems-segment-pooled-v1`, buffer 15 px, whole components hidden everywhere, visible
faults masked pixel-exactly, pooled α=0.2/β=0.8/300 m triangular kernel),
`gems.dprf1.fit_and_predict_fold` (stratified `d_vis ≥ 3 px` negatives, selective
9-channel residualization, relief-conditioned calibration, 8-azimuth sharpening,
two-regime submodular allocation) extended only through its existing
`extra_mm`/`regime_b_extra_names`/`return_legacy_conduit` parameters, stitched-OOF
(quadrant + 45° diamond) + apron debiasing, `gems.submission` writer, `gems.novelty`,
`gems.c2s2`, `gems.selector` v2. **No shared-code changes** are permitted except a
new additive module `src/gems/drainage.py`; `scripts/run_dprf1_lane.py
--verify-recorded` and `scripts/run_eul1_lane.py --verify-recorded` must still pass.
No prior submission pixels enter the detector (registry rasters are read *only* by
the novelty audit).

**Three locked arms** (budget 37,654 dots full-footprint; per-fold
`k = round(37654 · fold_offcat_valid / total_offcat)`; spacing 2.8 px; clearance >2 px):
1. `Arm 1 DRAIN-primary`: 59-channel model (52 + 7 drainage); Regime-B multiplier adds
   the three drainage gate channels.
2. `Arm 2 noDRAIN replay`: exact 52-channel DPRF1 configuration through the same code
   path (`extra_mm=None`). Expected to reproduce the recorded DPRF1 HOLDOUT-DTI
   0.1637924246971501 (EUL1's identical replay was bit-identical); any deviation is
   reported as an irregularity, never silently absorbed.
3. `Arm 3 channels-only`: 59-channel model; Regime-B multiplier = DPRF1 legacy set.
   Attribution: Arm3−Arm2 = channel effect; Arm1−Arm3 = Regime-B drainage-gating effect.

**Full-footprint export:** Arm 1 only, Dual-Partition Stitched-OOF + apron quantile
debiasing; 0% in-sample pixels; budget fixed at 37,654 *in advance* (B2-matched).

## 5. Mandatory gates (all automated; zero human-inspector fallback)

1. **Canary (Rule 4):** every one of 59 channels solo on `SegmentHoldout.canary`, both
   polarities; `max(AUC, 1−AUC) ≤ 0.90` or halt. Drainage-channel solo AUCs reported.
2. **Holdout (Rule 3):** pooled HOLDOUT-DTI + 95% CI (1,999 10 km block-bootstrap
   draws; 60,988 withheld positives) for all arms; paired CIs Arm1 vs Arm2, Arm3 vs
   Arm2, Arm1 vs Arm3; explicit statement vs recorded point-best 0.16379. No number
   may be written as a leaderboard score or projection.
3. **Novelty (Rule 1):** pre-placement surface **and** final dots vs the pinned
   registry (`registry/priority_rasters.json`, 46 unique rasters) + all local
   GEMSDOE24 method lanes incl. DPRF1/EUL1/TRSG1/CUP1/CRP1/TNR1 (restored and
   hash-verified this session: 46/46 priority, 98/98 peer references = 84 unique
   blobs) + peer blobs: `|ρ| ≤ 0.90`, 3-px dot overlap `≤ 0.70` per competing-method
   raster. Literal all-entry result (incl. `registry-039` spacing-5 lattice) reported
   transparently. Exceeding a limit = duplicate lane: log and stop, no retuning, no
   dot-jittering to escape.
4. **C2ST:** exact-file spatial-block nuisance audit, labels first; strict gate
   AUC < 0.55 (with Holm-adjusted p and p95 margin as implemented).
5. **Format:** shared validator on exact bytes — single-band float32, template
   CRS/shape/transform, whole-array finite `[0,1]` for `-zeros.tif` (the portal's
   "Predicted values must be in range [0, 1]" failure mode), NaN-outside twin,
   single-TIFF ZIP.
6. **Run card (Rule 5):** one JSON card (hypothesis; mechanism; named mimic;
   HOLDOUT-DTI + CI; registry correlation/overlap; raster sha256; validator output;
   submission name + ≤140-character note; verdict promote/negative) plus the
   `gems.selector` v2 receipt computed on the exact bytes.

## 6. Decision ceiling, declared in advance

`gems.selector` v2 is a *negative-only* screen (literal lattice retained, live quota
unknown from the sandbox, positive replay certificate unimplemented). The best honest
outcome of this session is therefore **"strongest unscored unique candidate —
DOWNLOAD: YES · SUBMIT: NO (`DO_NOT_SUBMIT`), selector step pending"**. If DRAIN5 beats
0.16379 with paired CI > 0 *and* passes novelty/C2ST/format, it becomes the #1
unscored candidate and the executive summary must say so with its file name, SHA-256
and ≤140-char note up front; if it fails any of those, verdict is `negative`, DPRF1
remains #1, and the negative result is the deliverable. No retuning after seeing
results (no channel subsetting, no new gates, no threshold/θ changes, no seed or
budget changes). Claiming `SUBMIT: YES` would require the separate selector step:
(i) prospective policy separation of synthetic calibration controls, (ii) an
owner-recorded live weekly-quota receipt from the submission page (the agent may not
automate DrivenData), (iii) an independent replay certificate. This lane cannot grant
any of those to itself.

## 7. Official sources for manual review

- Competition/problem/metric: https://www.drivendata.org/competitions/306/competition-doe-gems/ · https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/ · leaderboard https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/ (never scraped; login-gated data not bypassed)
- Rules PDF: https://docs.nlr.gov/docs/fy26osti/96647.pdf
- Reference solution: https://github.com/drivendataorg/gems-prize-reference-solution
- USGS GeoDAWN survey: https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and · DOI 10.5066/P93LGLVQ
- OpenEI GDR INGENIOUS #1391: https://gdr.openei.org/submissions/1391 · https://gbcge.org/current-projects/ingenious/
- USGS 3DEP (deferred finer DEM): https://www.usgs.gov/3d-elevation-program · https://apps.nationalmap.gov/downloader/
- NASA ASF OPERA (rank-4 source, deferred): https://asf.alaska.edu/datasets/daac/opera/
- CRS EPSG:32611: https://epsg.io/32611 · Tversky index: https://en.wikipedia.org/wiki/Tversky_index
- Method citations (no external data taken): O'Callaghan & Mark (1984) D8 flow
  direction; Flint (1974) / Wobus et al. (2006) stream-power steepness `k_sn` with
  θ_ref = 0.45; Rennó et al. (2008) HAND.

*Core values applied: Maximize P(Win) — spend the session on the only remaining
evidence geometry (drainage-network topology) that no lane in the 92-repo portfolio
has computed; Own the Outcome — the paired holdout and the gates decide, end-to-end,
with no manual inspection step and no invented score.*
