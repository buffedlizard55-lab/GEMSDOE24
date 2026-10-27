# Preregistration — H24-CGMK1 (2026-10-27, session arena/5ef84d43)

**Status: written BEFORE any CGMK1 feature, model, holdout score, or TIFF was
computed in this session.** Data restoration and band inventory (counts,
valid-pixel counts, min/max) preceded this file; no label-derived statistic
other than the already-published catalogue total (60,988 px) was inspected.

Core values: **Maximize P(Win)** · **Own the Outcome**. Automated gates only;
no human-inspector fallback.

## Irregularities flagged before implementation (do not silently resolve)

1. **No assigned lane paragraph.** The parallel-run protocol says "Your lane
   is the single method paragraph below", but no method paragraph is present
   in the operative prompt (same absence recorded 2026-10-26/27). This
   session therefore **self-assigns one narrow lane** (below), discloses the
   collision risk with parallel sessions, and enforces the same duplicate
   gates. This is a deviation forced by the owner's explicit instruction to
   generate a unique TIFF in this session; it is logged, not hidden.
2. **Conflicting leaderboard claims.** The brief states both `0.4413` and
   `0.3195` as "current leaderboard high". Neither has an artifact-linked
   organizer receipt in this repo. Both are **UNVERIFIED-OWNER-REPORT**.
3. **Lattice pigeonhole.** The retained spacing-5 calibration lattice
   (registry control, 206,895 in-footprint dots) covers 5,160,724 of
   5,167,373 footprint pixels within 3 px, so *any* 37,654-dot in-footprint
   set overlaps it by >= 82.34% (see `knowledge/31_...`). The literal
   "any registry raster > 70% => duplicate" rule is therefore mathematically
   unsatisfiable at the standard budget if the lattice is treated as a
   method raster. This session reports **both**: (a) the literal all-entry
   result including the lattice (fail-closed for SUBMIT), and (b) the
   control-separated result using `novelty.classify_space_filling_control`
   (the informative scientific comparison, with Spearman |rho| <= 0.90 still
   enforced against every entry including the lattice). No dots will be
   moved, and no registry entry will be deleted, to defeat either check.
4. **Portal "[0, 1]" rejection cause unproven.** The shipped candidate will
   be the all-finite zeros-outside variant (strict whole-array [0,1] PASS).
   Official text describes NaN outside bounds; the sample itself is
   NaN-outside. Neither variant is proven portal-accepted. A NaN twin is
   produced only as a labelled compatibility artifact, never as the
   recommended upload.
5. **Band 6 `tc` provenance** is not established as gravity terrain
   correction (see `evidence/band6_provenance_review_20261027.json`).
   CGMK1 **excludes `tc`** rather than using it under an unsupported name.
6. **All owner-listed leaderboard scores** (including GEMSDOE32 B2
   `0.2778`) are UNVERIFIED-OWNER-REPORT until an artifact-linked
   submission-page receipt is recorded. HOLDOUT-DTI numbers are internal
   measurements, never leaderboard scores. Any leaderboard figure for a new
   file is a **MODEL PROJECTION (not a score)** under stated assumptions.

## Five candidate hypotheses considered (ranked before implementation)

| Rank | Hypothesis (layers → signature) | Why it could catch a catalogue-missing fault | Difference from implemented lanes | Non-fault mimic | Expected DTI value / cost |
|---|---|---|---|---|---|
| 1 | **CGMK1 — signed gravity–magnetic cross-gradient reversal + lithology-conditioned K-residual front, geophysics-only supervised.** Layers: `rtp`, `iso_grav_anom` gradients at sigma 1 and 2.5 px → signed sin/cos of inter-field gradient angle and \|∇ sin\| reversal; GeoDAWN ordinal `K,Th,U` → fold-fit linear conditional `K ~ Th + U + Th·U`, residual and its gated gradient front; supervised HGB over raw magnetic/gravity/AEM/strain/seismic bands only. | An oblique buried splay can rotate magnetic-basement vs gravity-basement edge orientations relative to each other and can channel K-metasomatic fluids under cover — signals that need no surface scarp, so they can be present exactly where DEM/LiDAR mapping (the source of most catalogue traces) is blind. | GVC1/EUL1 used unsigned co-alignment/magnitude; TMCG unsigned topo–magnetic cross-gradient; SAHG1 fixed Th-controlled scalar contrasts; CRP1 rank-space fronts. None used the *signed* gravity–magnetic reversal or a *fold-fit conditional* K residual. CGMK1 also drops the whole 100 m DEM slope/relief trunk and all LiDAR channels that drove DPRF1/DKRN1/S3DEP1/XVAR1 dot convergence (71–87% mutual overlaps). | Intrusive contact geometry, remanent magnetization, GeoDAWN survey seams; arkosic sediment sorting. | Highest qualitative information per cost; **unknown DTI** (no number promised). Cost: low–medium (all inputs cached/committed; CPU only). |
| 2 | Signed terrain-flexure dipole + basement step (`det_elev`, `det_local_relief`, `depth_to_base_surf`, strain rates): opposite-signed separated cross-normal curvature lobes around a narrow basement-depth gradient. | Broad bending above a buried fault where no crisp scarp survives. | RSHG1 used pointwise Hessian curvature; CON a conductivity saddle; neither a separated signed pair. | Terrace–valley pairs, alluvial-fan curvature. | Unknown DTI; medium cost; carries DEM-trunk convergence risk (the documented cause of prior >70% overlaps), hence ranked below CGMK1. Viable with cached data. |
| 3 | NASA OPERA DISP-S1 InSAR line-of-sight velocity step across candidate traces. Official free source: NASA Earthdata / ASF DAAC OPERA DISP-S1. | Actively creeping/loading blind faults produce a velocity discontinuity with no topographic scarp. | No lane in this repo uses InSAR time series. | Aquifer compaction, landslide motion. | **Not viable in this sandbox**: outbound network is restricted to github.com / npm / PyPI hosts and Earthdata requires authenticated download; obtainability of footprint frames was therefore **not** established. Named for a future session with Earthdata access; do not propose as current. |
| 4 | Sentinel-2 SWIR clay/ferric alteration fronts (Copernicus Data Space, official free). | Hydrothermal argillic/iron-oxide alteration along concealed conduits. | Radiometric K/Th/U is used here; optical SWIR mineral indices are not in any implemented lane. | Playa evaporites, burn scars, lithologic soil changes. | **Not viable in this sandbox** (Copernicus egress not in the allowlist; tile obtainability unchecked). Future only. |
| 5 | EarthScope/USArray MT 3-D conductivity conduits at 2–15 km (IRIS EMC, official free model repository). | A deep conductive fault-zone conduit can exist under non-conductive cover with no surface trace. | AEM `cond_surf` is a near-surface apparent conductivity; no lane uses depth-resolved MT. | Graphitic metasediments, saline aquifers. | **Not viable in this sandbox** (IRIS EMC egress not in allowlist; coarse model resolution vs 100 m grid also unverified for this footprint). Future only. |

External layers actually used by CGMK1 are already committed with provenance
JSONs: USGS GeoDAWN radiometrics and contractor ratio/extension grids
(`data/external/geodawn_rad_u8.tif`, `geodawn_extensions_u8.tif`; USGS data
release DOI 10.5066/P93LGLVQ, ScienceBase item in the JSONs). No new external
download is required, so Rank 1 is viable now; Ranks 3–5 are explicitly not
claimed viable until their official downloads are obtainable and checked.

## Preregistered method (single lane — exact)

Inputs (hash-pinned owner mirror, **not organizer-authenticated**):
`data/training_features.tif` SHA-256
`4371c82e3b8339b807bdffcf4ef59a225520fe2988d521be208ae33743123bc5`
(restored this session via `scripts/restore_data.py`); bridge
`labels.tif` / `sample_submission.tif` per `data/manifest.json`; committed
GeoDAWN u8 grids per their JSON sidecars. Band semantics from
`src/gems/geofeatures.BAND_ORDER`; valid = finite and > -1e30.

Feature stack (all label-free transforms; the only fitted transform, the
conditional-K linear model, is fit **per fold on that fold's train pixels
only** for holdout, and on all supported footprint pixels — still label-free —
for the final full-fit surface):

- Raw geophysics (16): `mag_anom, rtp, tmi_hg, tmi_vg, tmi, iso_grav_anom,
  iso_grav_anom_hg, iso_grav_anom_vg, iso_grav_anom_slope, cond_surf,
  depth_to_base_surf, geod_2ndinv, geod_shearrate, geod_dilaterate,
  deq_n100a15, ieq_n100a15`; plus deterministic
  `log_deq_ieq = log1p(deq) - log1p(ieq)`.
  Excluded by design: `det_elev`, `det_elev_slope` (DEM trunk), `tc`
  (provenance), all LiDAR channels, all catalogue-distance features.
- Radiometric ordinals (8): `K, Th, U, TC` and `ThK, UK, UTh, TMI_up150`
  bytes scaled /255, 0 → NaN. Bytes are percentile ranks, not concentrations.
- Signed cross-gradient (8): for smoothed `rtp` (m) and `iso_grav_anom` (g)
  at sigma ∈ {1, 2.5} px (nearest-valid fill used only inside derivative
  stencils; support eroded so filled pixels never score):
  `sinθ = (gx·my − gy·mx)/(|g||m|+eps)`, `cosθ = (g·m)/(|g||m|+eps)`,
  eps = 1e-6 × median(|g||m|) over support (computed per full grid,
  label-free); `rev = |∇(sinθ smoothed sigma 1)|`;
  `magprod = log1p(|g|·|m|)`.
  Channels: sin/cos/rev/magprod × 2 scales.
- Conditional-K (4): fold-fit OLS on ordinal ranks
  `rK ~ 1 + rTh + rU + rTh·rU` (train-fold supported sample, deterministic
  stride sample ≤ 200k); `kres = rK − pred`; `kres_grad = |∇ kres|` (sigma 1);
  `kres_grad3` (sigma 2.5); `kfront = kres_grad / (1 + |∇rTh| + |∇rU|)`.

Support: every derivative channel finite after eroding the joint raw-valid
mask by the maximum stencil radius (sigma 2.5 Gaussian truncated at 4 sigma
+ gradient + smoothing of sinθ ⇒ erosion radius 14 px, applied once). Pixels
outside support are ineligible for training negatives/positives and for
emission; they are **not** silently imputed for scoring.

Model: `HistGradientBoostingClassifier(max_iter=80, max_leaf_nodes=15,
learning_rate=0.08, l2_regularization=5.0, early_stopping=False)` — the
repo's recorded baseline-D3 hyperparameters, unchanged (no tuning).
NaN handled natively by HGB; no label-based imputation.

Holdout (shared evaluator, unmodified): `holdout.SegmentHoldout(fp,
catalogue, buffer_px=15)`, `gems-segment-pooled-v1`, pooled DTI
α=0.2, β=0.8, 300 m triangular kernel, visible faults masked pixel-exactly,
catalogue-based features: none. Per fold: positives = train ∩ visible
(sample ≤ 20,000, seed 20261027+fold), negatives = train, ≥9 px from visible
(sample ≤ 60,000). Emission per fold: `emission.priority_poisson(surface,
support ∩ valid ∩ ~visible, budget = round(37654 × fold off-catalogue /
total off-catalogue), min_dist=3)`. Report pooled HOLDOUT-DTI + 95% CI +
withheld count, per-fold rows.

Baseline in the same run (same folds/samples/emission): raw-16 + log-ratio +
8 rad ordinals **without** the 12 new channels (25 ch). Paired comparison via
`SegmentHoldout.compare_paired`. Leakage canary: `SegmentHoldout.canary` on
every source and derived channel + the OOF surface; any two-polarity
extremity > 0.90 ⇒ stop, verdict negative.

**Exactly 2 priced experiments** (within the ≤3 / ≤2 h budget):
- EXP-1: CGMK1 full stack (37 ch) holdout.
- EXP-2: matched 25-ch control holdout (same code path with the new channels
  withheld). This is an ablation control, not a tuning search.
No third arm, no hyperparameter search, no threshold/seed retuning after
seeing EXP-1/EXP-2. Whichever of EXP-1/EXP-2 is the preregistered primary
(**EXP-1**) defines the candidate, regardless of which scores higher; EXP-2
is reported as the control.

Full-fit candidate: retrain EXP-1 spec on the full catalogue
(positives = catalogue ∩ support sample ≤ 40,000; negatives ≥9 px from
catalogue sample ≤ 120,000; seed 20261027), predict the full footprint,
emit exactly **37,654** dots by `priority_poisson(..., min_dist=3)` over
`support ∩ footprint ∩ ~catalogue ∩ (distance-to-catalogue > 2.0 px)`.
The >2 px clearance is preregistered from the B2 ancestry finding (B2 =
D2.8 minus 6,436 dots within 2 px of catalogue, zero added): near-catalogue
halo mass is the one emission change with an owner-reported leaderboard
gain; it is a fixed rule here, not tuned on the holdout (holdout folds use
the same clearance against fold-visible faults).

Novelty gates (before placement on the OOF/full surface and again on final
dots): Spearman rank correlation |rho| ≤ 0.90 vs every computable registry
entry available locally (priority registry entries whose rasters are
present under docs/downloads + inputs + calibration, content-deduped) and
directed 3-px dot overlap ≤ 70% vs every non-control entry; lattice and any
other space-filling control reported separately per Irregularity 3.
Exceeding a threshold ⇒ log duplicate, verdict negative, no dot moving.

Promotion rule (all required for verdict `promote`; otherwise `negative`):
(i) format PASS (single-band float32, EPSG:32611, template shape/transform,
no NaN/Inf in footprint, values in {0,1} ⊂ [0,1], strict whole-array [0,1]
for the zeros variant); (ii) canary PASS; (iii) EXP-1 pooled HOLDOUT-DTI
point estimate **strictly greater** than the conservative selection floor
from `benchmarks.selection_floor` (recorded: KPL-36 0.17010, unreplayed) —
beating only the same-session control is insufficient; (iv) novelty PASS
under the control-separated rule **and** lattice literal result disclosed
(literal failure alone ⇒ at most "promote-to-selector-review", still
SUBMIT: NO from this session; per protocol, slot selection is a separate
selector step and this session spends **zero** slots); (v) paired
EXP-1 − EXP-2 delta reported with CI (not required positive, but a negative
primary-vs-control result ⇒ verdict negative: the new geology must not hurt).

Score reporting: HOLDOUT-DTI (evaluator, withheld n, 95% CI) is the only
measured performance. A leaderboard **MODEL PROJECTION (not a score)** may
be reported using `emission.model_dti` with the lattice-calibrated truth
density τ = 0.0024445 (12631.65 px equivalent, `evidence/emission_calibration.json`),
φ swept {0, 0.05, 0.10}, τ swept ±20%, and candidate coverage taken from the
holdout — with the explicit assumption (likely false in detail) that hidden
new faults are credited at the same rate as withheld catalogue faults.

Run card: one JSON at `evidence/cgmk1_run_card_20261027.json` with
hypothesis, mechanism, named mimic, HOLDOUT-DTI + CI, registry
correlation/overlap (both lattice treatments), raster SHA-256, validator
output, submission name + ≤140-char note, verdict promote/negative.
Negative results are deliverables and will be published as-is.

Builder note (≤140 chars, exact string decided after content-ID exists;
template): `GEMS24 CGMK1 | signed grav-mag reversal + cond-K front, geophys-only | id <content_id> | not yet live-scored`
