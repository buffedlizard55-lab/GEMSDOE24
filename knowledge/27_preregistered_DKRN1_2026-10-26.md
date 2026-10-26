# Preregistration — `H24-DKRN1`: Topological D8 Drainage-Knickpoint Routing & Split-View 300 m DTI-Kernel Net-Tversky Allocation (2026-10-26)

- **Lane ID:** `H24-DKRN1` (uniting `AGENTS.md` untried queue items `H24-DRAIN5` topological flow-routing knickpoints + `H24-KERN6` 300 m DTI-kernel soft-label credit estimation)
- **Date (UTC):** `2026-10-26`
- **Branch:** `arena/3c6e51cf-gemsdoe24` (fast-forwarded to `origin/main` `d2368718190e` before preregistration)
- **Assigned-lane status:** Provisional self-selected lane (`AGENTS.md` next-step queue). The standing prompt references an assigned single-method paragraph that is absent from the brief; this disclosure is carried into the JSON run card.
- **Experiment budget (Protocol Rule 6):** Strictly locked to `<= 3` experiments (`Arm 1` primary `H24-DKRN1`, `Arm 2` pure gap-native kernel-only ablation `DKRN1-HeadA-Kernel47`, `Arm 3` same-session head-to-head `H24-DPRF1` replay + `oof_multiphysics_hgb_d3` control) and `<= 2.0` wall-clock hours. Zero competition submission slots will be accessed or spent by the agent.

---

## 1. Motivation & Diagnosis of Prior Stopped Lanes

1. **Parent-convergence ceiling (`EUL1` `86.57%`, `CUP1` `91.20%`):** Appending auxiliary channels onto `H24-DPRF1`'s exact 52-channel binary `1:3` case-control `HistGradientBoostingClassifier` + `68%` primary-ridge allocator forces `>85%` of emitted dots within `3 px` (`300 m`) of `DPRF1`, failing Protocol Rule 1 (`<= 70%`).
2. **Case-control sigmoid tail saturation in submodular integration:** Binary HGB lanes trained on `1:3` case-control samples ($\pi_{\text{sample}} = 0.25$ vs true off-catalogue fold prevalence $\pi_{\text{pop}} \approx 0.0118$, a $28\times$ prior-odds inflation) emit uncalibrated probabilities where a mediocre hillslope ($\text{true } q = 0.076 \to \hat{p}_{\text{cc}} = 0.70$) achieves `74%` of the weight of a sharp tectonic scarp ($\text{true } q = 0.38 \to \hat{p}_{\text{cc}} = 0.94$). Summing uncalibrated $\hat{p}_{\text{cc}}$ over a `29`-pixel `300 m` disk systematically favors wide diffuse hillslope blobs over 1-pixel-thin concealed fault traces.
3. **Discarded `0 < d_vis < 300 m` fault-damage-zone training signal:** Every prior supervised lane in `GEMSDOE24` trained binary classifiers on `d_vis == 0` vs `d_vis >= 3 px`, discarding all training pixels in the `100–283 m` (`1–2.83 px`) fault-damage and digitizing-offset corridor even though the competition metric awards exact triangular kernel credit $K(d) = \max(0, 1 - d / 300\text{ m}) \in (0, 1)$ there.
4. **3DEP LiDAR gap (`31.8%` of footprint, concentrated in `NE_LidarGapHeavy`) and buried piedmont washes (`SW`/`SE`):** Active faults crossing alluvial fans or unflown 3DEP regions often lack preserved interfluve scarps yet leave **colinear stream-power knickpoints and dog-leg thalweg deflections** along ephemeral drainage networks routable across `100%` of `det_elev`.

---

## 2. Four Ranked Untried Candidate Geological Hypotheses (Pre-Implementation)

All four candidates below are untried across all 16 executed `GEMSDOE24` lanes (`MTR1, ASPC, SAHG1, RSHG1, FUSE-HCW, GVC1, OJ1, CRP1, CUP1, TNR1, DPRF1, TRSG1, VENT, EUL1, PAIR1, CON`) and inspected `2026-10-26` sibling focus lanes (`GEMSDOE25, 27, 28, 30, 31, 32, 33, 36`). Expected gains are **qualitative planning judgments, never leaderboard score projections**.

| Rank | Candidate ID & Name | Specific Layers Used | Physical Signature at a Real Fault | Why Missing from USGS Qfaults / INGENIOUS Catalogue | Named Non-Fault Mimic | Distinction from Existing Repo Code | Expected Gain vs Cost & Official Data Availability |
|---:|---|---|---|---|---|---|---|
| **1 (SELECTED)** | **`H24-DKRN1` — Topological D8 Drainage-Knickpoint Routing & Split-View 300 m DTI-Kernel Net-Tversky Allocation** | `det_elev`, `det_elev_slope`, `iso_grav_anom_slope`, `geod_2ndinv`, `geod_shearrate`, `geod_dilaterate`, `depth_to_base_surf` (`data/training_features.tif`), pointwise dequantized `downface_max`, `upface_max`, `cross_max` (`lidar_scarp_features_u8.tif`), plus cached 30-ch base + 18-ch INGENIOUS/lineament + 4-ch SAHG conduit stack (`dist_known_fault_px` strictly excluded). | Exact sparse unit-lower-triangular D8 flow routing $(I - P^\top)A = \mathbf{1}$ reveals **Flint's-law stream-power knickpoint jumps** ($k_{sn} = S_{\text{D8}} A^{0.45}$ above upstream/downstream channel reaches) and **4-step thalweg dog-leg azimuth deflections** aligned colinearly across parallel fan washes (`900 m` 8-azimuth corridor), paired with sub-alluvial gravity ramps (`depth_to_base_surf` `150–1,100 m`), Walker-Lane transtensional strain partitioning, Split-View `300 m` DTI-kernel soft-label regression, and Elkan Bayes-posterior Net-Tversky 3-regime submodular allocation. | Rapid late-Holocene sheetflood aggradation erases interfluve scarps on piedmont fans, and `31.8%` of the footprint lacks 1 m LiDAR; ephemeral washes incising across upthrown blocks or strike-slip splays preserve aligned knickpoints and dog-leg offsets invisible to aerial-photo scarp mapping. | Resistant Tertiary welded ash-flow tuff or basalt caprock ledges creating contour-following lithologic knickpoints across adjacent washes; incised non-tectonic fan-head trench banks (`cross_max` high); Pleistocene Lake Lahontan wave-cut strandlines. | First topological D8 hydrological graph solver (`spsolve_triangular`), first along-channel stream-power knickpoint & thalweg-deflection operator, first continuous `300 m` DTI-kernel soft-label regressor (`H24-KERN6`), first Split-View LiDAR-excluded head + Elkan Bayes prior-odds calibration + 3-regime Net-Tversky FP-penalized submodular allocator. Zero reuse of `EUL1` Euler or `PAIR1` graben-pair/dipole operators. | **Highest expected holdout & sparse-transfer benefit** (targets `SW`/`SE` piedmonts and `NE` LiDAR gap while structurally breaking `DPRF1` parent convergence). Moderate CPU cost (~14–18 min on 2 cores, `<2.6 GiB` RSS). **100% locally staged & SHA-verified inputs.** |
| **2 (Backup — not run)** | **`H24-LSHS2` — Pluvial Strandline & Stratigraphic Contour-Orthogonality Filter** | `det_elev`, `det_gradient`, `lidar_cos2strike`, `lidar_sin2strike`, `iso_grav_anom_hg`, `depth_to_base_surf`. | Normal/oblique faults climb or descend across local topographic contours along strike ($\lvert \nabla z \cdot \hat{t}_{\text{strike}} \rvert > 0$) and coincide with subsurface density gradients, whereas pluvial wave-cut benches remain strictly horizontal along equipotential contours ($\nabla z \cdot \hat{t}_{\text{strike}} \approx 0$). | Subtle Holocene intrabasin faults below `~1,330 m` in Lahontan sub-basins were omitted or conflated with shoreline scarps during 1:100k reconnaissance mapping. | Gently dipping (`2°–5°`) tilted Tertiary lacustrine carbonate hogbacks cutting across modern alluvial fan contours. | Explicit along-strike contour-orthogonality rate $\lvert \sin(\psi_{\text{scarp}} - \psi_{\text{contour}}) \rvert$; untried across all 9 repos. | Moderate expected gain in `NW`/`NE` Lahontan basins; limited because `det_elev` removes regional base elevation and raw USGS 3DEP elevation tiles on `usgs.gov` are unreachable from this sandbox. |
| **3 (Backup — not run)** | **`H24-MTCS3` — Hydrothermal Smectite Clay-Cap Perimeter × Basement-Step Upflow Detector** | `cond_surf`, `iso_grav_anom_hg`, `depth_to_base_surf`, GeoDAWN `K, Th, U, ThK`, INGENIOUS `2 m` temperature probe & well/spring geothermometry. | Fault-controlled geothermal upflow zones form impermeable or brecciated structural boundaries along the **lateral maximum horizontal gradient $\lvert \nabla \log(\text{cond\_surf}) \rvert$** co-aligned with `iso_grav_anom_hg`, rather than at peak smectite clay-cap interiors. | Blind Basin-and-Range geothermal conduits (e.g., Dixie/Gabbs step-overs) capped by intact playa clay exhibit zero surface scarp. | Saline playa evaporite brine perimeters bordering non-tectonic alluvial fan toes. | Replaces raw `cond_surf` magnitude (`SAHG1`/`DPRF1`) with vector co-alignment $\lvert \nabla \log(\text{cond\_surf}) \cdot \nabla \text{iso\_grav} \rvert$. | Low-to-moderate `100 m` localization precision because `cond_surf` has `>1–2 km` interpolation wavelength; low CPU cost; all inputs local. |
| **4 (Backup — not run)** | **`H24-PSAR4` — Sentinel-1 / ARIA InSAR Interseismic & Aquifer-Barrier Phase-Gradient Detector** | External NASA OPERA / ASF Sentinel-1 ascending + descending LOS velocity gradients fused with `geod_shearrate`, `geod_dilaterate`, and `lidar_coh100`. | Shallow aseismic fault creep, postseismic relaxation (e.g., Monte Cristo Range shear zone), and fault-sealed groundwater compartment steps produce sharp `100–300 m` LOS phase gradients across low-relief playas. | Distributed Walker Lane shear splays and blind hydrostratigraphic barrier faults lack cumulative topographic throw. | Agricultural or mining dewatering subsidence bowls and tropospheric phase stratification on steep ranges. | Spaceborne radar phase-gradient edge detection; untried in `GEMSDOE24`. | Potentially strong in `SW`/`SE`, **blocked in this sandbox** (`asf.alaska.edu` / `nasa.gov` outside outbound allowlist; no local InSAR raster staged). |

---

## 3. Exact Mathematical & Algorithmic Specification of `H24-DKRN1`

### 3.1 Label-Free Topological D8 & Tectonic Channel Construction (`10` new channels in `data/prepared/dkrn1_features.dat`)

All 10 channels are computed strictly from geophysical, topographic, and radiometric/LiDAR rasters **without reading `labels.tif` or `existing_faults.tif`**, and asserting `FORBIDDEN_COLUMNS` (`dist_known_fault_px`, etc.) are never accessed:

1. **Exact Sparse Topological D8 Flow Routing on `det_elev` (`100 m` UTM grid):**
   - Nearest-fill boundary NaNs on `det_elev` strictly for routing continuity, apply mild pit-breaching blend $z(y, x) = 0.80\,z_{\text{raw}}(y, x) + 0.20\,(G_{\sigma=2.5} * z_{\text{raw}})(y, x) + 10^{-7} y + 10^{-10} x$ so every interior cell has strict tie-free ordering.
   - Route each footprint cell $i$ to the neighbor $j \in \mathcal{N}_8(i) \cap \text{footprint}$ maximizing positive steepest descent $S_{\text{D8}}(i) = \max_{j} (z(i) - z(j)) / d(i, j)$ (`100 m` cardinal, `141.42 m` diagonal). Because $z(\text{rcv}(i)) < z(i)$ strictly, the receiver graph $P$ is a strict DAG.
   - Permuting by descending $z$ makes $I - P_{\text{perm}}^\top$ unit lower-triangular; solve $(I - P_{\text{perm}}^\top) A_{\text{perm}} = \mathbf{1}$ via `scipy.sparse.linalg.spsolve_triangular` to obtain exact catchment pixel count $A_{\text{D8}}(i) \ge 1$.
   - **`d8_log_acc`**: $\log(1 + A_{\text{D8}}(i))$ (`NaN` outside valid DEM).
2. **`d8_stream_power_knick` (Flint's-law channel steepness jump):**
   - Local stream-power steepness proxy $k_{sn}(i) = S_{\text{D8}}(i)\, A_{\text{D8}}(i)^{0.45}$.
   - Propagate 3 steps downstream along $P$ and 3 steps area-weighted upstream along $P^\top$ (pure 1D channel-graph stencil, zero cross-divide Gaussian blurring) to form $\bar{k}_{sn,\text{dn3}}(i)$ and $\bar{k}_{sn,\text{up3}}(i)$.
   - $\text{knick}(i) = \max\bigl(0,\, k_{sn}(i) - \tfrac{1}{2}(\bar{k}_{sn,\text{up3}}(i) + \bar{k}_{sn,\text{dn3}}(i))\bigr) \cdot \mathbf{1}[A_{\text{D8}}(i) \ge 4]$.
3. **`d8_knick_reach_max3`**: Maximum of `d8_stream_power_knick` across the 3-step upstream/downstream channel reach $\{P^{-2}, P^{-1}, I, P^1, P^2\}$, capturing the `300 m` fault-crossing reach along active washes.
4. **`d8_thalweg_turn` (Shutter-ridge / strike-slip dog-leg deflection):**
   - Compare unit 4-step downstream chord vector $\hat{v}_{\text{dn4}}(i)$ (`i -> P^4(i)`) against area-weighted 4-step upstream inflow chord vector $\hat{v}_{\text{up4}}(i)$ along channels with $A_{\text{D8}}(i) \ge 6$:
   - $\text{turn}(i) = (1 - \hat{v}_{\text{dn4}}(i) \cdot \hat{v}_{\text{up4}}(i)) \log(1 + A_{\text{D8}}(i)) \cdot \mathbf{1}[A_{\text{D8}}(i) \ge 6]$.
5. **`d8_knick_corridor_900m` (Cross-wash colinear knickpoint/deflection alignment):**
   - Apply 8-azimuth `900 m` (`half_len_px = 4`) oriented lineament coherence (`gvc.oriented_lineament_coherence`) to $z_{\text{rob}}(\text{d8\_stream\_power\_knick}) + 0.5\, z_{\text{rob}}(\text{d8\_thalweg\_turn})$. Planar faults align knickpoints across adjacent washes; sinuous lithologic ledges do not.
6. **`d8_drainage_asymmetry_1km` (Tilted half-graben trunk migration):**
   - $(\text{d8\_log\_acc} - G_{\sigma=10}(\text{d8\_log\_acc})) \cdot \mathrm{expit}(-z_{\text{rob}}(\text{det\_elev\_slope}))$.
7. **`d8_incision_vs_catchment` (Footwall uplift vs fluvial canyon relief):**
   - $z_{\text{rob}}(\text{det\_local\_relief}) - 0.50\, z_{\text{rob}}(\text{d8\_log\_acc})$.
8. **`suballuvial_grav_ramp` (Concealed piedmont bedrock step under `150–1,100 m` alluvial cover):**
   - `iso_grav_anom_slope` (`band 5` of `training_features.tif`) $\times \exp\bigl(-((\text{depth\_to\_base\_surf} - 500.0) / 550.0)^2\bigr)$.
9. **`walker_transtension_index` (Walker Lane dextral-oblique transtensional partitioning):**
   - $\text{geod\_shearrate} \cdot (0.5 + 0.5\,\mathrm{expit}(z_{\text{rob}}(\text{geod\_dilaterate}))) / (\text{geod\_2ndinv} + 1.0)$ using clean geodetic bands `4, 7, 8` (`tc`, `ieq_n100a15`, `deq_n100a15` excluded).
10. **`lidar_contour_over_bank` (Pointwise contour-scarp vs incised-channel-bank discriminator):**
    - Dequantize `downface_max`, `upface_max`, `cross_max` from `lidar_scarp_features_u8.tif` via exact `sqrt` lookup (`xmax * ((q - 1)/254)^2`, `NaN` where `valid == 0` or `q == 0`), and compute single-pixel ratio:
      $$\frac{\text{downface\_max} + 1.25\,\text{upface\_max} - \text{cross\_max}}{\text{downface\_max} + 1.25\,\text{upface\_max} + \text{cross\_max} + 0.02}$$
      (`NaN` outside `lidar_valid`). Uses **zero** spatial graben-pair or Laplacian crest-base dipole stencils (`PAIR1` untouched).

### 3.2 Split-View Dual-Head Learning & Elkan Bayes Prior-Odds Calibration (Fold-Local Only)

Within each training fold (`train_mask`, `visible_mask` ONLY — never touching validation/test labels):
- **Selective non-topographic nuisance residualizer (`11` channels):** Fit `SelectiveNonTopographicResidualizer(alpha=100.0)` on `35,000` disjoint training background rows (`train_mask & ~visible_mask`) over `SELECTIVE_RESID_NAMES | {"suballuvial_grav_ramp", "walker_transtension_index"}`, preserving `NaN`s and all topographic/scarp/D8 geometry.
- **Head A — Gap-Native `300 m` DTI-Kernel Soft-Label Regressor (`47` channels, `H24-KERN6`):**
  - Input view excludes all `15` raw 1 m LiDAR amplitude/lineament channels (`lidar_1..10`, `lidar_cos2strike`, `lidar_sin2strike`, `gvc_lidar_lineament_900m`, `sahg_g_sat`, `sahg_h_conduit`), retaining `47` channels (`18` non-LiDAR base + `17` non-LiDAR GVC + `2` non-LiDAR SAHG + `10` new `DKRN1` channels).
  - Target: exact competition `300 m` triangular kernel credit $y_K(x) = \max(0,\, 1 - d_{\text{vis}}(x)/3.0) \in [0, 1]$ computed strictly from `visible_mask`.
  - Stratified kernel-corridor training sample (`max 100,000` rows from `train_mask`): up to `20,000` fault-core (`d_vis == 0`, $y_K = 1$), `25,000` damage-corridor (`0 < d_vis < 3.0`, $y_K \in (0, 1)$), `25,000` near-flank (`3.0 <= d_vis < 10.0`, $y_K = 0$), and `30,000` far-field (`d_vis >= 10.0`, $y_K = 0$).
  - Model: 2-seed `HistGradientBoostingRegressor(loss="squared_error", max_iter=190, learning_rate=0.055, max_leaf_nodes=31, min_samples_leaf=80, l2_regularization=2.5, early_stopping=False)`.
  - Calibration: partial nuisance ridge debiasing on clipped `[1e-4, 1 - 1e-4]` log-odds of $\hat{y}_K$ on the `35,000` disjoint background rows, followed by exact fold-train kernel-prevalence log-odds shift $\Delta \ell_K = \mathrm{logit}(\bar{y}_{K,\text{train}}) - \mathrm{logit}(\bar{y}_{K,\text{sample}})$, yielding calibrated expected 300 m kernel credit $\hat{\mu}_K(x) \in (0, 1)$.
- **Head B — Full-Physics Elkan Bayes-Posterior Core Classifier (`62` channels):**
  - Input view: all `62` channels (`30` base + `18` GVC + `4` SAHG + `10` `DKRN1`).
  - Stratified core sample (`25,000` positives at `d_vis == 0` vs `75,000` negatives at `d_vis >= 3.0`, `50%` near `3–12 px` / `50%` far `>= 12 px`).
  - Model: 2-seed `HistGradientBoostingClassifier(max_iter=190, learning_rate=0.055, max_leaf_nodes=31, min_samples_leaf=80, l2_regularization=2.5, early_stopping=False)`.
  - Calibration: `ReliefConditionedCalibrator` across `has_lidar` vs `~has_lidar` in 3 terrain-relief tiers, followed by **exact Elkan (2001) prior-odds shift** $\Delta \ell_{\text{Bayes}} = \mathrm{logit}(\pi_{\text{train}}) - \mathrm{logit}(\pi_{\text{sample}})$ where $\pi_{\text{train}} = \lvert \text{train} \cap \text{visible}\rvert / \lvert \text{train}\rvert$ and $\pi_{\text{sample}} = N_+ / (N_+ + N_-)$, yielding true non-saturated fault-core posterior $\hat{q}_{\text{core}}(x) \in (0, 1)$.

### 3.3 Split-View Expected-Credit Fusion & 3-Regime Net-Tversky Submodular Allocation

1. Ridge-sharpen (`half_len_px = 4`, 8-azimuth lineament coherence) and visible-catalogue apron-debias (`debiased_apron_surface` on `visible_mask` ONLY) both $\hat{q}_{\text{core}}$ and $\hat{\mu}_K$.
2. Form sensor-aware expected-credit density:
   $$u_{\text{post}}(x) = \begin{cases} 0.52\,\hat{q}_{\text{core,deb}}(x) + 0.48\,\hat{\mu}_{K,\text{deb}}(x), & \text{if } \text{has\_lidar}(x), \\ 0.35\,\hat{q}_{\text{core,deb}}(x) + 0.65\,\hat{\mu}_{K,\text{deb}}(x), & \text{if } \neg\text{has\_lidar}(x). \end{cases}$$
3. **3-Regime Net-Tversky Submodular Coverage (`min_spacing_px = 2.9`, `catalogue_clearance_px = 2.0`, `budget = 37,654` deployment / proportional off-catalogue `k_fold` on holdout):**
   - Marginal Net-Tversky objective at candidate dot $s$ given current coverage $C$:
     $$\Delta U(s \mid C) = \sum_{\Delta \in \mathcal{N}_3} w_{\text{regime}}(s + \Delta)\,\max\bigl(0,\, K(\|\Delta\|) - C(s + \Delta)\bigr) - \tau_{\text{eff}}\bigl(1 - \hat{\mu}_{K,\text{deb}}(s)\bigr),$$
     with sparse-regime Tversky FP penalty weight $\tau^* = \frac{\alpha D_0}{1 - \alpha D_0} = \frac{0.2 \times 0.2778}{1 - 0.2 \times 0.2778} = 0.05882$ scaled to posterior units ($\tau_{\text{eff}} = 0.25\,\tau^*$).
   - **Stage 1 (`48%` share — Split-View Core-Kernel Ridge):** $w_1 = u_{\text{post}}$.
   - **Stage 2 (`28%` share — D8 Hydrologic Knickpoint & Deflected-Thalweg Corridors):** $w_2 = u_{\text{post}} \cdot m_{\text{hydro}}$, where $m_{\text{hydro}}$ is a train-quantile-calibrated sigmoid gate on `d8_knick_corridor_900m`, `d8_stream_power_knick`, `d8_knick_reach_max3`, `d8_thalweg_turn`, `d8_incision_vs_catchment`, and `lidar_contour_over_bank` (neutral `0.5` when `NaN`).
   - **Stage 3 (`24%` share — Concealed Sub-Alluvial & Walker-Lane Hydrothermal Conduits):** $w_3 = u_{\text{post}} \cdot m_{\text{concealed}}$, where $m_{\text{concealed}}$ is a train-quantile-calibrated sigmoid gate on `UPFLOW_CONDUIT_NAMES` $\times$ (`SUBSURFACE_STEP_NAMES` + `suballuvial_grav_ramp` + `walker_transtension_index`) $\times$ low-slope factor.
4. **Deployment raster (`37,654` binary `{0, 1}` dots):** Generated strictly via **100% Dual-Partition Stitched-OOF** (`0.50` axis-aligned 4-quadrant OOF + `0.50` 45°-rotated 4-wedge OOF, both with `1.5 km` whole-component buffers; zero in-sample full-grid refit). Emitted as `-zeros.tif` (strict whole-array `[0, 1]`, `0` NaNs), `-nan.tif` twin, and single-TIFF `.zip` via shared `gems.submission.write_pair`.

---

## 4. Locked 3-Experiment Plan & Fail-Closed Acceptance Gates

1. **Experiment 1 (`Arm 1` — `H24-DKRN1`, Primary Candidate):** 62-channel Split-View (`Head A` 47-ch kernel regressor + `Head B` 62-ch Bayes-posterior core classifier) + 3-Regime Net-Tversky Submodular Allocation (`48% / 28% / 24%`). Also evaluated on the `3.0 km` bridge protocol (`segment-hide-recover-pooled-v1`).
2. **Experiment 2 (`Arm 2` — `DKRN1-HeadA-Kernel47`, Gap-Native Kernel-Only Ablation):** Pure 47-channel `Head A` `300 m` DTI-kernel soft-label regressor + 3-Regime Net-Tversky Submodular Allocation (zero raw LiDAR amplitude channels; isolates `DRAIN5 + KERN6`).
3. **Experiment 3 (`Arm 3` — `DPRF1-Replay`, Exact Same-Session Head-to-Head Control):** Exact 52-channel `H24-DPRF1` replay + `oof_multiphysics_hgb_d3` (`27`-ch OOF baseline) on `gems-segment-pooled-v1` (`60,988` withheld positives, `1,999` 10 km block-bootstrap draws) for exact paired CIs.

### Frozen Gates (Zero Post-Hoc Threshold Changes Permitted)
- **Leakage Canary (Rule 4):** Two-polarity single-feature `HOLDOUT` AUC `<= 0.90` across all `62` channels (run before model fitting; abort if any channel exceeds `0.90`).
- **Format & `[0, 1]` Compliance:** Single-band `float32`, `EPSG:32611`, `3730 x 3292`, exact template geotransform, `0` NaN/Inf anywhere in `-zeros.tif`, values strictly in `[0, 1]`, note `<= 140` chars.
- **Uniqueness (Rule 1):** Pre-placement surface `|Spearman rho| <= 0.90` AND final dots `<= 0.70` within `3 px` against **all** competing method rasters (`priority_rasters.json` minus synthetic `registry-039`/`044`, all local `2026-10-25`/`2026-10-26` lanes including `DPRF1`, `TRSG1`, `EUL1`, `VENT`, `PAIR1`, and all `83` on-grid peer blobs, plus auxiliary `2026-10-26` 8-sibling refresh audit). Literal overlap against `registry-039` (`spacing-5` synthetic lattice) is recorded transparently without exemption.
- **Holdout Superiority:** `HOLDOUT-DTI > 0.1637924246971501` (`H24-DPRF1`) with strictly positive 95% paired block-bootstrap CIs over both `DPRF1` replay and `oof_multiphysics_hgb_d3`.
- **Exact-File Nuisance C2ST:** `observed_auc < 0.55` (or unflagged after Holm adjustment against `labels_first`) on roads, BLM claims, and derived 4-block boundaries (`derived_audited_not_official_coordinates`).
- **Promotion Selector:** Governed exclusively by `gems.selector.verify_selector` (`gems-selector-v2-literal-quota-fail-closed`). Because live DrivenData quota verification, literal `registry-039` separation, and an independent replay certificate remain unimplemented, `ok_to_submit` fails closed (`False` / `DO_NOT_SUBMIT`) even if scientific holdout and competing-method novelty pass; negative or fail-closed outcomes are reported honestly as first-class deliverables.
