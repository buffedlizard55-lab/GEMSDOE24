# Preregistered DRAIN1: Drainage-Network Deflection & Knickpoint Alignment — 2026-10-26

**Session branch:** `arena/212d95ff-gemsdoe24` (branched from `fc2bc6f`, active)
**Preregistration committed before any code execution.** No tuning after seeing holdout. Budget: max 3 experiments or 2 hours; this file preregisters one fixed experiment (Rank 1). Negative is a deliverable.

**Reuse, don't rebuild:** `data/prepared/features.npy` (30 channels, SHA a4ca25b2…), `data/bridge/sample_submission.tif` (EPSG:32611, 3730×3292), `src/gems/holdout.py` `SegmentHoldout(buffer_px=15, gems-segment-pooled-v1, 1.5 km collar, 60,988 withheld positives, 10 km block bootstrap 1,999 draws)`, `src/gems/emission.py` `priority_poisson(min_dist=3)`, `src/gems/novelty.py` `compare_registry` (pre-placement + final dots, 200k rank sample, |ρ|>0.90 or overlap>0.70 = duplicate), `src/gems/c2s2.py` (grouped 10 km block C2ST, Holm p≤0.05 & AUC≥0.55 & margin≥0.02 = flagged), `src/gems/submission.py` `write_submission`/`check_variants`, `src/gems/preflight.py`.

**Label rule:** every number HOLDOUT-DTI (evaluator_version, n_withheld_positive_pixels, 95% CI) or ORGANIZER-CONFIRMED (submission-page receipt). Projection never written as score.

---

## 1. Why GEMSDOE32 H33-B2 scored 0.2778 (owner-reported) and how to beat it — PhD synthesis

**Forensic geometry (verified, not scored):** `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` = 37,654 positive pixels. It is `GEMSDOE25/GEMSDOE30` D2.8 (44,090 Poisson-thinned dots from `H19-5` `e27054cf`) with all 6,436 dots within ≤2 px (≤200 m) of the public catalogue deleted (equivalently `GEMSDOE31` `H27-4` 40,199 dots minus 2,545 at 1<d_cat≤2 px). Zero new coordinates added. Source: `evidence/priority_review_20261025.json`, `registry/priority_rasters.json`, byte-level comparison in `knowledge/14_h33_analysis_2026-10-25.md`.

**Metric mechanism (distance-weighted Tversky, α=0.2, β=0.8, 300 m triangular kernel K(d)=max(0,1−d/3 px)):** Score = T / (0.2 T + 0.2 F + 0.8 N) where T=TP_w, F=FP_w, N=truth mass. Removing t (weighted TP) and f (weighted FP) improves ratio iff t·(0.2F+0.8N) < 0.2·T·f. Because K decays linearly over 300 m, dots within 200 m of known faults waste ~15% of budget on 0.2·FP_w flank penalties while contributing little unique TP_w (most hidden truth lies >1.5 km from visible components in `SegmentHoldout`). Poisson thinning at d=2.8 px (280 m min spacing) already reduces FP clustering; catalogue clearance >200 m removes residual flank over-prediction. This explains owner-reported ordering 0.2778 > 0.2708 (H27-4) > 0.2600 (D2.8) without invoking new geology. The 0.3195 / 0.4413 figures in the brief have no artifact-linked receipt and are UNVERIFIED.

**Why it is not optimal and can be beaten:** H33 adds no complementary geology beyond H19-5's learned multi-physics (LiDAR antislope, RTP, gravity, geodetic strain). It still misses blind intra-basin faults with no 10 m LiDAR scarp (31.8% of footprint is LiDAR-gap, especially `NE_LidarGapHeavy`) and concealed piedmont stepovers where surface relief is muted by alluvial-fan aggradation. Holdout evidence: `NE_LidarGapHeavy` truth = 12,511 pixels, but SAHG1 support covers only 68.2% of footprint; RSHG1 recovered only after NaN-aware full-footprint coverage (+0.039 gain in NE). GVC1 later beat OOF-Base by +0.00976 (HOLDOUT-DTI 0.14876 vs 0.13899) by adding geothermal vent/tilt/lineament orthogonal signals. Therefore beating H33 after de-duplication requires (a) full-footprint coverage, (b) orthogonal blind-fault signal (hydrothermal, magnetic tilt-depth, or drainage), and (c) paired holdout gain over current best `GVC1 0.14876` (not over dense-legacy absolute numbers) with strict C2ST pass (AUC<0.55) and prospective novelty pass (|ρ|≤0.90, overlap≤0.70 on 47 competing rasters, calibration lattice reported separately).

**Can we score higher than 0.2778 on the leaderboard?** Holdout DTI values here are ~0.13-0.15 on sparse 20% component-thinned quadrants (3199 components, 60,988 withheld positives). The leaderboard hidden set is density ~5× lower, so absolute DTI scales differently; no linear projection is valid. The only falsifiable claim is HOLDOUT-DTI improvement on the frozen `gems-segment-pooled-v1` protocol. The remaining headroom is real: GVC1 showed +0.00976 gain with 18 new channels; drainage deflection is orthogonal (covers basin interiors where LiDAR/mag are weak) and should add complementary recall without increasing FP in range fronts, plausibly pushing pooled DTI to 0.155-0.165 if well calibrated. No score forecast is offered; we will test on the holdout before spending a slot.

Official sources for manual review (no new fetch, just pointers):
- Competition overview / metric: https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/
- Reference solution (Tversky implementation): https://github.com/drivendataorg/gems-prize-reference-solution
- GeoDAWN DOI: https://doi.org/10.5066/P93LGLVQ  (ScienceBase https://www.sciencebase.gov/catalog/item/657e1d85d34e23d3533209f7)
- USGS 3DEP: https://www.usgs.gov/3d-elevation-program/data-tools  (DEM 1 m & 10 m)
- GDR INGENIOUS 1391: https://gdr.openei.org/submissions/1391  (2 m probe, paleo sinter, springs)
- EPSG:32611: https://epsg.io/32611
- Tversky index: https://en.wikipedia.org/wiki/Tversky_index
- DriveData rules PDF: https://docs.nlr.gov/docs/fy26osti/96647.pdf

---

## 2. Five untried hypotheses (ranked by expected pooled HOLDOUT-DTI gain vs cost, before implementation)

| Rank | Hypothesis · specific layers · physical signature (edge/curvature) | Why it catches fault missing from USGS/INGENIOUS catalogue | Named non-fault mimic | How it differs from everything in this repo | Expected HOLDOUT-DTI leverage · implementation cost · external data |
|---|---|---|---|---|---|
| **1 — SELECTED** | **H24-DRAIN1: Drainage-network deflection + knickpoint alignment.** Layers: `det_elev` (100 m DEM band, prepared stack col 7), `det_elev_slope`, `det_local_relief`, `geod_dilaterate` (shear-dilation context). Signature: (a) **Valley Hessian** `V = max(λ_max,0)` multi-scale (σ=1.5,3 px, truncate 3, 21×21 erode) on det_elev → concave valley axes; (b) **Profile curvature knickpoint** `C_prof = |Hxx·cx²+2Hxy·cx·sy+Hyy·sy²|` along slope azimuth (cx, sy = grad/slope) → abrupt base-level steps; (c) **Aspect-deflection gradient** `|∇θ|` where θ=atan2(gy,gx) circular gradient → beheaded channels, wind gaps. Combined `D = σ(V)·(0.5+0.5·σ(C_prof))·(0.6+0.4·σ(|∇θ|))·exp(−slope/5°)` gated on DEM support, no LiDAR. | USGS/INGENIOUS mapped 1:250k range-front bedrock scarps, but intra-basin faults buried under 10-100 m Quaternary alluvium have **zero 10 m LiDAR scarp** because active fan aggradation erases decimetre offsets. Yet the fault still offsets the piedmont base-level, deflecting ephemeral streams, creating wind gaps and knickpoints preserved in 100 m DEM (100% footprint, vs 68% LiDAR). Drainage is an **integrator** over 10⁴ yr, not a snapshot scarp. | Pleistocene Lake Lahontan tufa beach bars / wave-cut terraces, distributive fan avulsion lobes, road/ditch cuts, or lithologic contacts of welded-tuff caldera rims. | `SAHG1`/`ASPC` used **ridge** convexity (`max(−λ_min,0)`); `MTR1` used magnetic trough; `GVC1` used dem_lineament on openness·slope but not valley/concave nor knickpoint/profile curvature nor aspect deflection. No lane uses D8-channel or knickpoint. | **Highest orthogonality** (basin interior vs range front). Expected pooled DTI +0.008–0.015 over GVC1 0.14876 if flat-basin recall outweighs FP, but uncertainty high because channel signal is diffuse (>500 m). Cost **low** (pure numpy/scipy, <2 min CPU, <1.5 GB). No new external data — det_elev already hash-pinned in `training_features.tif` (SHA 4371c82e…), det_local_relief/gradient already cached. |
| 2 | **H24-THERM-HINGE: Shallow 2 m thermal probe × basement hinge.** Layers: `F2mDAB` (positive 2 m ΔT, `2m_temperature_probe_INGENIOUS_regional_data.zip`), `depth_to_base_surf`, `iso_grav_anom_hg`, `det_elev_slope`. Signature: hinge curvature `∇²⊥ D_base` (Laplacian perpendicular to gravity gradient) gated on `exp(−slope/4°)` and corroborated by Gaussian-smoothed `max(0,F2mDAB)` (σ=15 px). | Concealed basin-interior faults host convective upflow with no surface scarp, but create shallow conductive plume detectable 2 m below surface above sub-alluvial hinge. | Lateral warm-groundwater outflow plumes in permeable paleochannels down-gradient from range-front springs, not directly over fault. | Zero prior lane ingests `2m_temperature_probe` (staged but unused). GVC1 used 2 m probe as one of 18 channels but not hinge-gated. | **Moderate** where probes exist, but probe coverage sparse (~10.6% footprint within 5 km, GDR 1391). Expected DTI +0.003–0.007 pooled. Cost low. Data staged at `data/external/2m_temperature_probe_INGENIOUS_regional_data.zip` (verified inventory). |
| 3 | **H24-SINTER-BRIDGE: Paleo-sinter azimuthal corridor × strain stepover.** Layers: paleo sinter/travertine/tufa points (`paleo_geothermal_regional.zip`), `geod_dilaterate`, `geod_shearrate`, `iso_grav_anom_hg`, `rtp`. Signature: anisotropic axial kernel (L=30 px, 8 azimuths) connecting sinter pairs within 3 km along local dilaterate/shearrate principal axis, × gravity HG magnitude and RTP demag trough. | Fault-valve behaviour seals active conduits with silica sinter during interseismic, leaving linear paleo chains along blind stepovers with no continuous scarp. | Lake Lahontan tufa mounds on wave-cut shorelines unrelated to tectonics. | No GEMSDOE24 lane uses `paleo_geothermal_regional.zip` (GVC1 uses it as point distance among 18, not as azimuthal corridor). | Moderate precision near sinter chains, but recall low (paleo points <200, sparse). Expected DTI +0.002–0.005. Cost low, data staged. |
| 4 | **H24-TILT-CROSS: Multi-scale tilt-derivative zero-cross concordance.** Layers: `rtp`, `tmi_hg`, `tmi_vg`, `iso_grav_anom`, `iso_grav_anom_hg/vg`. Signature: tilt `θ_M = atan(tmi_vg / sqrt(tmi_hg²+ε))`, `θ_G` similarly, zero-cross proximity `exp(−|θ|/0.25)`, gradient survival across σ=1,3 px upward continuation, product `exp(−|θ_M|)·exp(−|θ_G|)`. Tilt normalizes amplitude by depth. | Sub-alluvial basement fault contacts produce sharp susceptibility/density edges smeared in raw HGM; tilt places edge directly over contact independent of magnetization/density magnitude. | Dipping basalt/rhyolite stratigraphic contacts, caldera ring-fracture margins, GeoDAWN flight-line leveling seams. | MTR1 used signed RTP trough; SAHG1 used raw HGM sigmoid, not tilt zero-cross. No lane computes magnetic-gravity tilt concordance. | Low-moderate (100-300 m localization broad). Cost medium (gradient). No new data. |
| 5 | **H24-STRAIN-WORM: Geodetic strain worm persistence (Frangi).** Layers: `geod_dilaterate`, `geod_shearrate`, `det_elev`, `lidar_coh`. Signature: Frangi vesselness on second invariant of strain-rate tensor `√(dilat²+shear²)` multi-scale (σ=1,2,4) → worm-like transtensional corridors, × coherence. | Active Basin-and-Range extension (~10 nstrain/yr) opens permeability before scarp forms; strain worms mark corridors where future scarps will nucleate. | Anthropogenic subsidence (pumping) worm artifacts, DEM noise. | GVC1 used `dilat·shear` product scalar, not multi-scale worm/Frangi. | Small (+0.001–0.003), low cost. |

**Why Rank 1 first:** Only drainage integrates 10⁴ yr base-level history and covers 100% footprint including 31.8% LiDAR gap where prior supervised ensembles blindly concentrate dots. It is orthogonal in feature space (det_elev valley/knick vs LiDAR ridge/mag) and in geography (basin floors vs range fronts), so it should reduce 76.8% ridge overlap toward <70% while potentially lifting pooled DTI if at least 15-20% of hidden truth is intra-basin. If Rank 1 fails to beat `GVC1 0.14876` with C2ST pass, Ranks 2-5 remain as next-session candidates without spending a slot.

---

## 3. Fixed experiment spec (Rank 1, no tuning)

**Inputs (hash-verified before use):**
- `footprint` from `data/bridge/sample_submission.tif` (finite mask = 5,167,373 px, SHA 2176d08e…)
- `labels` from `data/bridge/labels.tif` (SHA 7ba308cc…, 60,988 positives, 3,199 components)
- `det_elev` band extracted from `data/training_features.tif` (SHA 4371c82e…, float32, band index `geofeatures.BAND_ORDER` = `det_elev`) via rasterio, with `geofeatures._valid` sentinel check (|x|>1e30 → NaN)
- `det_elev_slope`, `det_local_relief`, `det_gradient` from `data/prepared/features.npy` (SHA a4ca25b2…)
- `lidar_valid`, `raster profile` from template

**Support mask:** `dem_valid = footprint & isfinite(det_elev)`; inner support `support = binary_erosion(dem_valid, 21×21)` (radius 10 px > max σ=3 truncate 9) so boundary fill never leaks; `verify_receptive_field_support(support, dem_valid, 10)` must pass.

**Derived surfaces (100% formula-stated, no catalogue read):**
1. `dem_fill = det_elev[inds]` where `inds = distance_transform_edt(~dem_valid, return_indices=True)` (nearest valid, no label imputation)
2. Multi-scale Hessian (σ=1.5,3.0, truncate 3):
   - `hxx = gaussian_filter(dem_fill, sigma, order=(0,2))`, `hyy = (2,0)`, `hxy = (1,1)` (mode nearest)
   - `trace = hxx+hyy`, `disc = sqrt(max((hxx−hyy)²+4hxy²,0))`, `λ_max = 0.5*(trace+disc)`, `λ_min = 0.5*(trace−disc)`
   - `valley_σ = σ²·max(λ_max,0)` (concave), `ridge_σ = σ²·max(−λ_min,0)` (for audit)
   - `valley = valley_1.5 + valley_3.0` (sum), clipped to p99
3. `grad = hypot(gx,gy)` where `gx,gy = gradient(gaussian_filter(dem_fill,1),100)`, `slope = degrees(atan(grad))`
4. Profile curvature `C_prof = |hxx·cx²+2hxy·cx·sy+hyy·sy²|` with `(cx,sy)=(gx,gy)/max(grad,1e-6)`, normalized by p99
5. Aspect `θ=atan2(gy,gx)` (circular), `asp_grad = hypot(gradient(circular_diff(θ)))` where circular diff wraps to [−π,π], normalized
6. `D = σ_valley·(0.5+0.5·σ(C_prof))·(0.6+0.4·σ(|∇θ|))·exp(−slope/5°)` where σ(x)=x/p99 clipped [0,1]; then `drain_candidate = where(support, D, 0)`; outside support 0 (not NaN) for canary consistency

**Holdout:** `SegmentHoldout(footprint, labels, buffer_px=15)` — 4 folds NW/NE_LidarGapHeavy/SW/SE, whole components hidden globally, pixel-exact visible mask, pooled DTI (α0.2 β0.8 300 m triangle), 10 km block bootstrap 1,999 draws seed 20261025.

**Leakage canary:** `context.canary({det_elev, dem_valid, valley, C_prof, asp_grad, drain_candidate})` with max_per_class 15000, threshold 0.90 both polarities; halt if flagged.

**Prospective novelty:** `novelty.compare_registry(drain_candidate, fp, registry/priority_rasters.json + local GVC1/RSHG1/SAHG1/MTR1/ASPC/CON, sample 200k, radius 3 px)` pre-placement surface and `novelty.compare_registry(..., dots=final)` final dots; require `|ρ|≤0.90` and `3-px overlap≤0.70` on 47 competing method rasters; calibration lattice `registry-039` reported separately via `separate_calibration_controls=True`.

**C2ST exact-file audit:** `road_m, claim_m, block_1..4` from `data/access/confounds.npz` provenance `data/access/provenance.json` (derived_audited_not_official_coordinates), 12k per class, 199 grouped 10 km block flips + 99 torus shifts, Holm.

**Allocation:** `eligible = support & ~catalogue & (EDT(~catalogue)>2)` (200 m flank clearance) for final; per-fold `eligible = support & valid & ~visible` for holdout. `final = emission.priority_poisson(drain_candidate, eligible, round(0.0073*fp.sum()), min_dist=3)` = 37,722 dots (same budget as RSHG1 for comparability). Binary {0,1} dots, Dinkelbach-valid.

**Baselines & paired comparison:** Reconstruct legacy `B0` (single HGB ridge) and `B1` (30-feat submodular, DTI 0.13899) on identical folds if not already cached; report `compare_paired` with CI.

**Writer & validator:** `submission.write_submission(final, template, docs/downloads/gems24-drain1-...-zeros.tif, outside="zero")` + nan twin + `.zip`; `submission.check_variants` must be format_valid, strict [0,1] on zeros variant, CRS/shape/transform match.

**Run card:** JSON at `evidence/drain1_run_card_20261025.json` + `docs/data/drain1_run_card.json` with hypothesis, mechanism, non-fault mimic, holdout DTI+CI, correlation/overlap, raster sha256, validator output, submission name + note ≤140, verdict promote/negative.

**Governance:** No DrivenData automation, no slot spent; `ok_to_submit` True only if all technical gates AND `literal_unseparated_passed` AND `assigned_coordinator_lane_present` AND `separate_selector_quota_verified` — all false here, so artefact will be `DOWNLOAD: YES · SUBMIT: NO` (DO_NOT_SUBMIT) unless every gate passes, which is logged transparently.

