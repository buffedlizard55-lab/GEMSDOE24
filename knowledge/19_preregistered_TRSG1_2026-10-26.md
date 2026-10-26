# Preregistration — `H24-TRSG1` (Two-Regime Seismic-Geothermal Step-Over & Terrain-Conditioned Stitched-OOF Detector)

- **Date (UTC):** `2026-10-26`
- **Repository / Branch:** `buffedlizard55-lab/GEMSDOE24` / `arena/6a7c2974-gemsdoe24`
- **Base `main` Commit:** `fc2bc6f350bf5c6ce8da5d7a2ab03578ea1259d1`
- **Status:** **LOCKED BEFORE IMPLEMENTATION AND BEFORE ANY HOLDOUT FIT OR EVALUATION** (committed prior to writing `src/gems/trsg1.py` or `scripts/run_trsg1_lane.py`, satisfying `AGENTS.md` and resolving `IR-PRE-REG-DETAIL` by enumerating all numeric hyperparameters up front).
- **Experiment Budget (`PARALLEL-RUN PROTOCOL` Rule 6):** Strictly `3` preregistered arms (`Arm 1: TRSG1-Raw44`, `Arm 2: TRSG1-SelRes-TerrainCal`, `Arm 3: TRSG1-TwoRegime-StitchedOOF`, `<= 3` experiments, `< 2` hours, `< 2.0 GiB` RSS). Zero DrivenData network access; zero weekly submission slots spent (`ok_to_submit: false` / `DO_NOT_SUBMIT` pending separate independent selector review).

---

## 1. Forensic Motivation from Previous Sessions (`GVC1` `0.0859` Live Collapse & Unfinished Next Steps)

Before proposing new features, pixel-level diagnostics on all scored portfolio rasters established why `GEMSDOE24`'s `H24-GVC1` (`HOLDOUT-DTI = 0.14876`) dropped to `0.0859` (`OWNER-REPORTED`, unverified without organizer receipt) on the live leaderboard while `GEMSDOE32 H33-2-B2` (`0.2778`), `GEMSDOE70 P8-OOF38k` (`0.2478`), and `GEMSDOE27 H29-HPVC` (`0.2190`) generalized:

1. **In-Sample Near-Catalogue Halo Collapse (`IR-GVC1-INSAMPLE-HALO-COLLAPSE`):** Both `run_gvc1_pipeline.py` and `run_rshg1_lane.py` fitted their deployed full-footprint models in-sample on `train_mask = fp` with `neg_mask = (EDT(~catalogue) >= 9 px)`. Leaving `0 < d_cat < 9 px` (`100–900 m`) unpenalized by negatives while feeding multi-kilometer kernels (`1.5–2.5 km`) and global radial distance fields (`-log1p(EDT(paleo))`, `-log1p(EDT(hot_springs))`) caused the full-map classifier to memorize `200–1,500 m` haloes around `labels.tif`: `GVC1` placed **`45.8%`** of all `37,654` dots in `2 < d_cat <= 5 px`, **`86.0%`** within `d_cat <= 15 px`, and only **`4.1%`** in concealed basins/interiors (`d_cat > 30 px`, vs **`35.8%`** in `H33-2-B2` and **`32.6%`** in `H29-HPVC`). `SegmentHoldout` (`15 px` collar) could not observe this failure because `d_vis > 15 px` holds everywhere inside `fold["valid"]`.
2. **`SW` / Southern `SE` Transtensional Walker Lane Deficit:** Every prior `GEMSDOE24` detector (`RSHG1` `SW = 0.07993`, `GVC1` `SW = 0.10867`) underperformed severely in the `SW` Walker Lane belt because (a) none ingested the competition's earthquake seismicity bands (`ieq_n100a15`, `deq_n100a15`) or Quaternary volcanic vent alignments (`gdr_volcanic_vents_in_footprint.csv`), and (b) `RSHG1`'s unstratified `~has_lidar` calibration matched flat `SW` basin gaps to steep mountain-front `has_lidar` quantiles (`-0.0189` `SW` loss documented in `knowledge/18_RSHG1_findings_2026-10-25.md` §2.2).
3. **Previous-Session Priority Next Steps Executed Here:**
   - `README.md` Next Step #5: Selective non-topographic nuisance residualization preserving tectonic strain and local curvature while residualizing survey/access-sensitive regional scalars.
   - `knowledge/18_RSHG1_findings_2026-10-25.md` §4.2: Pointwise `priority_poisson(..., min_dist=3)` allocation (avoiding the `-0.00994` 2D kernel-blur penalty), terrain-relief-conditioned `~has_lidar` calibration (`H24-RSHG2`), and drainage-incision / relay-ramp curvature channels.
   - `knowledge/13_GVC1_findings_2026-10-25.md` §2 & §7: Hyperbolic relay-ramp saddle curvature (`H24-CSB2`) + two-regime concealed-basin / range-front allocation + strictly cross-fitted stitched-OOF deployment.

---

## 2. Four Ranked Untried Geological & Geothermal-Vent Hypotheses

| Rank | ID & Name | Specific Official Layer(s) | Targeted Physical Signature & Transform | Why It Catches *Missing* Faults vs. Mapped USGS/INGENIOUS Traces | Named Non-Fault Mimic Process(es) & Mitigation | How It Differs from All Prior `GEMSDOE24` Lanes | Expected DTI Gain / Cost / External Data Check |
|---:|---|---|---|---|---|---|---|
| **1** *(Selected)* | **`H24-TRSG1`** — Two-Regime Seismic-Geothermal Step-Over Saddle, Drainage-Break & Terrain-Conditioned Stitched-OOF Detector | Cached `features.npy` (`30` ch) + `training_features.tif` Bands `1,4,5,6,10,16` (`mag_anom`, `geod_2ndinv`, `iso_grav_anom_slope`, `tc`, **`deq_n100a15`**, **`ieq_n100a15`**) + OpenEI GDR #1391 (`gdr_volcanic_vents_in_footprint.csv`, `paleo_geothermal_regional.zip`, `2m_temperature_probe_INGENIOUS_regional_data.zip`, `gdr_wellspring_in_footprint.csv`) + GeoDAWN (`geodawn_rad_u8.tif`, `geodawn_extensions_u8.tif`) | (i) Structure-tensor anisotropy $(\mu_1-\mu_2)/(\mu_1+\mu_2)\sqrt{\mu_1}$ of $\nabla\log(1+\text{ieq})$ & moment excess $\log(1+\text{deq}) - 0.7\log(1+\text{ieq})$; (ii) Faulds & Hinz (2015) hyperbolic Hessian saddle twist $\sqrt{\max(0,-\det H_\sigma)}$ on DEM (`300/800 m`) & gravity/RTP (`400/500 m`); (iii) local DoG (`800 m - 3 km`, zero global radial EDT!) sinter/`2 m`-probe/geothermometer upflow + Quaternary vent demagnetization; (iv) valley-incision × piedmont concavity breakline; (v) relief-conditioned LiDAR-gap calibration + selective survey residualization + Dual-Partition Stitched-OOF Two-Regime allocation | Public Qfaults mapping favors continuous accessible range-front cliffs (`>1.8 km`) and misses: (a) Walker Lane strike-slip microseismic fracture corridors with small vertical throw; (b) diffuse relay-ramp twist saddles hosting `~79%` of Great Basin geothermal upflow (Faulds & Hinz 2015); (c) blind intrabasin faults beneath thick alluvial fill (`depth_to_base_surf >= 300 m, slope <= 6°`); (d) faults inside the `31.8%` 3DEP LiDAR gap | **Mimics:** Oligocene–Miocene welded-tuff hogbacks/caldera ring dikes; Lake Lahontan (`~1,335 m`) wave-cut shorelines & tufa; mining-blast seismicity; lateral outflow plumes in permeable fanglomerates. **Mitigation:** Multi-sensor co-alignment, deep-mountain (`slope > 24° & depth < 50 m`) canyon-wall taper, local DoG kernels (no radial GPS triangulation), training-only road/claim/block residualization + `gems.c2s2` audit | First lane in `GEMSDOE24` to ingest `ieq_n100a15`, `deq_n100a15`, and Quaternary volcanic vents; replaces `GVC1`'s global `-log1p(EDT)` bullseyes & in-sample `train_mask=fp` fit with local DoGs, close-flank negatives (`4<=d<9 px`), relief-stratified LiDAR-gap calibration, Dual-Partition Stitched-OOF deployment, and Two-Regime (`28%` concealed basin / `72%` range-front) `priority_poisson` allocation | **High** (`+0.008` to `+0.018` over `FUSE-HCW` `0.12372` and beating `oof_multiphysics_hgb_d3` `0.13000`, while passing `<=0.70` overlap & `C2ST < 0.55`). **Cost:** Low-Medium (`~15 min`, `<1.9 GiB` RAM, **100% staged local official data**). |
| **2** | **`H24-EULER2`** — Multi-Scale 3D Potential-Field Euler Deconvolution ($N=0.5$) & Gravity–Magnetic Cross-Gradient Basement Tensor | `rtp`, `tmi_hg`, `tmi_vg`, `TMI_up150`, `iso_grav_anom`, `iso_grav_anom_hg`, `iso_grav_anom_vg`, `depth_to_base_surf` | Moving-window Thompson (1982) / Reid et al. (1990) 3D Euler homogeneity solutions $(x-x_0)T_x+(y-y_0)T_y+(z-z_0)T_z=N(B-T)$ at fault-contact index $N=0.5$ weighted by Gallardo & Meju (2004) cross-gradient $|\nabla g \times \nabla M|$ alignment | Detects sub-alluvial intrabasin horst/graben basement offsets (`200–1,500 m` depth) completely buried by Holocene playa silt with zero surface scarp | **Mimic:** Unfaulted pluton intrusive contacts and detrital-magnetite paleochannels | `MTR1` used 1D RTP troughs; `RSHG1`/`GVC1` used scalar tilt angles; no repo lane solves 3D Euler depth-clustering + Gallardo–Meju vector cross-gradients | **Medium** (`+0.004` to `+0.008` in alluvial basins). **Cost:** Medium (`4×4` sliding-window SVD). **100% staged local data.** |
| **3** | **`H24-DRAIN3`** — Hydrological Upslope Area, Stream-Power Knickpoint ($k_{sn}$) & Bayonet Drainage-Deflection Graph | `det_elev`, `det_local_relief`, `lidar_3` (`step_max`), `lidar_9` (`relief`), `geod_shearrate` (+ optional USGS 3DEP `10 m` DEM) | Priority-flood D8/D$\infty$ contributing area $A(x)$, channel steepness jump $\Delta(A^{0.45}|\nabla z|)$, and orthogonal stream-azimuth deflection across strike | Active strike-slip and rapidly eroding piedmont fan faults erase scarps within $10^3\text{–}10^4$ yr while preserving aligned channel knickpoints and bayonet stream offsets | **Mimic:** Resistant lithologic hogbacks, alluvial fan-lobe avulsions, and highway borrow ditches | Prior geomorphic lanes (`ASPC`, `SAHG1`, `OJ1`) used local `9×9` filters without hydrological flow routing or $A(x)^{0.45}|\nabla z|$ knickpoints | **Medium** (`+0.003` to `+0.007`). **Cost:** Medium-High (`5.17M`-cell priority-flood). Testable on 100 m `det_elev`; finer channels obtainable from free official [USGS 3DEP 1/3 arc-sec National Map](https://apps.nationalmap.gov/downloader/) (outside sandbox allowlist; fetchable via CI). |
| **4** | **`H24-INSAR4`** — Spaceborne Sentinel-1 OPERA InSAR LOS Velocity Gradient & Phreatic Fault-Barrier Step | NASA JPL / ASF DAAC `OPERA_L3_DISP-S1_V1` ascending/descending LOS velocity & coherence + `cond_surf` + `depth_to_base_surf` | Cross-strike horizontal gradient $|\nabla_\perp v_{\text{LOS}}|$ (`1–5 mm/yr`) and seasonal InSAR coherence step across clay-sealed phreatic fault cores in flat playas | Flat playas (Carson Sink, Humboldt Sink, Dixie Valley floor) lack topographic scarps and 1 m LiDAR, yet impermeable fault gouge creates sharp poroelastic subsidence/groundwater steps | **Mimic:** Unfaulted clay–gravel aquifer pinch-outs and playa evaporite heave | Completely orthogonal C-band radar interferometric geodesy vs. static potential fields and airborne radiometrics | **High in flat playas**, **Deferred:** Free official NASA/ASF Open Data (<https://asf.alaska.edu/datasets/daac/opera/>), unreachable inside current sandbox allowlist (`github.com`/`pypi.org`/`npmjs.org` only); requires unrestricted runner/workflow staging. |

---

## 3. Exact Locked Specification of Top Candidate `H24-TRSG1`

### 3.1 Feature Stack (`44` Float32 Channels on Full `5,167,373`-Pixel Footprint, `0` Catalogue Inputs)

Stored in gitignored `data/prepared/trsg1_features.npy` (`shape = (5_167_373, 44)`, `float32`, `~910 MB`):

1. **Channels `0..29` (`30` ch — Reused Cached Template Stack `data/prepared/features.npy`, SHA-256 `a4ca25b2...`):**
   - `0..12`: `rtp`, `tmi_hg`, `tmi_vg`, `iso_grav_anom`, `iso_grav_anom_hg`, `iso_grav_anom_vg`, `det_elev`, `det_elev_slope`, `tmi`, `cond_surf`, `depth_to_base_surf`, `geod_dilaterate`, `geod_shearrate`.
   - `13..17`: `det_local_relief`, `det_gradient`, `arc_rtp`, `arc_det_elev`, `arc_agreement`.
   - `18..29`: `lidar_1..10`, `lidar_cos2strike`, `lidar_sin2strike` (`np.nan` preserved across the `31.8%` 3DEP LiDAR gap for native HGB missing-value routing).
2. **Channels `30..35` (`6` ch — Restored `data/training_features.tif` Bands, with `|x| > 1e30 -> NaN`; `IR-BAND-PROVENANCE` disclosed for `tc`, `ieq_n100a15`, `deq_n100a15`):**
   - `30`: `mag_anom` (Band 1)
   - `31`: `geod_2ndinv` (Band 4)
   - `32`: `iso_grav_anom_slope` (Band 5)
   - `33`: `tc` (Band 6, radiometric Total Count)
   - `34`: `eq_ieq_log` = $\log(1 + \max(\text{ieq\_n100a15}, 0))$ (Band 16)
   - `35`: `eq_deq_excess` = $\text{robust\_z}(\log(1 + \max(\text{deq\_n100a15}, 0))) - 0.70\,\text{robust\_z}(\log(1 + \max(\text{ieq\_n100a15}, 0)))$ (Band 10 vs. Band 16)
3. **Channels `36..43` (`8` ch — Engineered Seismic-Fabric, Relay-Ramp Saddle, Drainage-Break & Scale-Localized Geothermal Conduit Operators, `1 px = 100 m`):**
   - `36` (`eq_fabric_aniso`): Structure-tensor linear coherence $\frac{\mu_1 - \mu_2}{\mu_1 + \mu_2 + 10^{-6}}\sqrt{\mu_1}$ of $\nabla_{\sigma=1.5}\log(1 + \text{ieq\_n100a15})$ smoothed at $\sigma_T = 6.0\text{ px}$ (`600 m`).
   - `37` (`relay_saddle_dem`): Hyperbolic DEM saddle twist $\sqrt{\max(0, -\det H_{\sigma=3}(\text{det\_elev}))} + 0.5\sqrt{\max(0, -\det H_{\sigma=8}(\text{det\_elev}))}$ (`300 m` + `800 m` scales).
   - `38` (`relay_saddle_pot`): Potential-field transfer saddle & tilt contact $\text{robust\_z}\!\left(\sqrt{\max(0, -\det H_{\sigma=5}(\text{iso\_grav\_anom}))}\right) + 0.5\,\text{robust\_z}\!\left(\sqrt{\max(0, -\det H_{\sigma=4}(\text{rtp}))}\right) + \cos(\text{tilt}_{\text{grav}}) + \cos(\text{tilt}_{\text{mag}})$.
   - `39` (`piedmont_drainage_break`): $\text{robust\_z}\!\left((\mathcal{G}_{12}(\text{slope}) - \mathcal{G}_3(\text{slope}))\cdot\mathbb{I}(\text{slope} < P_{85})\right) + \text{robust\_z}\!\left(\max(0, \nabla^2_{\sigma=2}\text{det\_elev})\cdot |\nabla \mathcal{G}_4(\text{slope})|\right)$.
   - `40` (`ing_upflow_dog`): Scale-localized Difference-of-Gaussians ($\mathcal{G}_{\sigma=8} - 0.65\,\mathcal{G}_{\sigma=30}$, i.e., `800 m` vs `3,000 m`, clamped $\ge 0$, **zero global EDT!**) over standardized OpenEI GDR #1391 sinter/travertine (`Paleo_geothermal_final.csv`), positive `2 m` probe anomaly (`F2mDAB > 0`), and thermal/geothermometer spring excess (`temp_c >= 35°C` or `Qtz/Chalc/Cat >= 70°C`, strictly asserting `FORBIDDEN_COLUMNS` absent).
   - `41` (`qvent_demag_conduit`): Local DoG ($\mathcal{G}_{\sigma=12} - 0.65\,\mathcal{G}_{\sigma=36}$, `1.2 km` vs `3.6 km`) of Quaternary volcanic vents (`gdr_volcanic_vents_in_footprint.csv`, `row/col` only, `dist_known_fault_px` explicitly dropped & verified unused) + shallow demagnetization (`TMI_up150 - RTP` local residual) × $|\nabla_{\sigma=2}\log(1 + \max(\text{cond\_surf}, 0))|$.
   - `42` (`th_norm_k_u_alt`): GeoDAWN local (`\sigma=15 px` high-pass) Th-normalized K + U hydrothermal alteration residual (`geodawn_rad_u8.tif`, `geodawn_extensions_u8.tif`).
   - `43` (`basement_euler_step`): $\text{robust\_z}\!\left(\frac{|\text{tmi\_vg}|}{\sqrt{\text{tmi\_hg}^2 + 1}}\cdot |\nabla_{\sigma=2}\text{depth\_to\_base\_surf}|\right) + \sqrt{\max(\text{robust\_z}(\text{iso\_grav\_anom\_hg}), 0)\cdot\max(\text{robust\_z}(\text{tmi\_hg}), 0)}$.

### 3.2 Locked Numeric Hyperparameters, Negative Sampling, Residualization & Calibration

- `SEED = 20261026`
- `BUDGET_FRAC = 0.0073` (`37,654` dots on the `5,167,373`-pixel footprint; `round(0.0073 * fold_valid_pixels)` per validation fold)
- `HGB_PARAMS`:
  - `max_iter = 150`, `max_leaf_nodes = 31`, `min_samples_leaf = 80`, `learning_rate = 0.06`, `l2_regularization = 8.0`, `early_stopping = False`, `2` seeds per fold (`fold_seed_base + {0, 1}`).
- **Close-Flank + Far Negative Sampling (strictly on `fold["train"] & ~fold["visible"]`):**
  - Positives: `fold["train"] & fold["visible"]`, capped at `30,000` without replacement.
  - Far-background negatives (`80%`): `fold["train"] & ~fold["visible"] & (EDT(~fold["visible"]) >= 9.0)`, capped at `72,000`.
  - Flank-sharpening negatives (`20%`): `fold["train"] & ~fold["visible"] & (EDT(~fold["visible"]) >= 4.0) & (EDT(~fold["visible"]) < 9.0)`, capped at `18,000` (strictly `>= 400 m > 300 m` DTI kernel radius so adjacent splays inside `300 m` are never mislabeled negative, while penalizing `400–900 m` halo blur).
- **Selective Survey/Siting Nuisance Residualizer (`Arm 2` & `Arm 3`, fitted strictly on `36,000` `fold["train"]` background pixels, `Ridge(alpha=100.0)`):**
  - Residualizes ONLY the `10` survey/access-sensitive channels against `[road_m, claim_m, block_1, block_2, block_3, block_4]`:
    `("rtp", "iso_grav_anom", "tmi", "cond_surf", "depth_to_base_surf", "mag_anom", "tc", "eq_ieq_log", "ing_upflow_dog", "th_norm_k_u_alt")`.
  - Leaves tectonic strain (`geod_dilaterate`, `geod_shearrate`, `geod_2ndinv`), local topographic slope/relief/curvature, 1 m LiDAR scarps, and hyperbolic saddle twists unresidualized (`README.md` Next Step #5).
- **Terrain-Relief-Conditioned LiDAR-Gap Calibrator (`Arm 2` & `Arm 3`, fitted strictly on `fold["train"]` background, `Ridge(alpha=100.0)`):**
  - Partitions `|det_local_relief|` into `3` tertiles (`q33`, `q67` learned on `fold["train"]` background).
  - Within each relief stratum $s \in \{0, 1, 2\}$, affine-aligns `(p50, p99)` log-odds of `~has_lidar` (`!isfinite(lidar_1)`) to `has_lidar` (`isfinite(lidar_1)`) of the **same** relief stratum $s$, then subtracts `Ridge(alpha=100.0)` nuisance log-odds offset on `[road_m, claim_m, block_1..4]`.

### 3.3 The Three Preregistered Experimental Arms (`<= 3` Budget)

1. **`Arm 1` (`TRSG1-Raw44`):** Unresidualized 44-channel HGB ensemble (`2` seeds/fold, close-flank + far negatives) + global `emission.priority_poisson(prob, valid & ~visible & (EDT(~visible) > 2.0), k, min_dist=3)`.
2. **`Arm 2` (`TRSG1-SelRes-TerrainCal`):** Selective Survey/Siting Residualizer + Terrain-Relief-Conditioned LiDAR-Gap Calibrator + global `emission.priority_poisson(prob_cal, valid & ~visible & (EDT(~visible) > 2.0), k, min_dist=3)`.
3. **`Arm 3` (`TRSG1-TwoRegime-StitchedOOF` — Primary Candidate Exported via `submission_writer.py`):**
   - Uses `Arm 2`'s calibrated OOF surface $P_{\text{cal}}(x)$ (zero extra HGB fitting on `SegmentHoldout`).
   - **Two-Regime Concealed-Basin + Range-Front Pointwise Allocation (`min_dist = 3`, `d_vis > 2.0 px`):**
     - **Regime B (`Concealed Alluvial Basin & Low-Slope Apron`):** `basin_mask = (depth_to_base_surf >= 300.0) & (det_elev_slope <= 6.0)` (`38.7%` of footprint). Allocates `k_basin = round(0.26 * k)` dots via `priority_poisson(..., min_dist=3)` ranked by $P_{\text{cal}}(x)\cdot\bigl(0.85 + 0.15\,\sigma(Z_{\text{sub}}(x))\bigr)$, where $Z_{\text{sub}}$ is the robust-standardized mean of `(basement_euler_step, relay_saddle_pot, eq_fabric_aniso, ing_upflow_dog, qvent_demag_conduit)`.
     - **Regime A (`Range-Front, Piedmont Break & Step-Over Terrain`):** Remaining `k - n_emitted_basin` dots allocated in `~basin_mask` (with `EDT(~dots_basin) >= 3.0` enforced so global `min_dist >= 3.0 px` holds strictly across the regime boundary!) via `priority_poisson(..., min_dist=3)` ranked by $P_{\text{cal}}(x)\cdot\bigl(1 - 0.20\,\text{clip}((\text{slope}-24.0)/15.0, 0, 1)\cdot\mathbb{I}(\text{depth\_to\_base\_surf} < 50.0)\bigr)$.
   - **Full-Footprint Stitched-OOF Deployment:** Blends `0.5 * P_quad_OOF + 0.5 * P_rot45_OOF` (`0°` quadrant `SegmentHoldout` OOF + `45°`-rotated 4-sector whole-component `15 px`-buffered OOF), guaranteeing that **100% of pixels in the exported competition `.tif` are predicted strictly out-of-fold** (`0%` in-sample predictions).

---

## 4. Preregistered Validation, Uniqueness, Nuisance & Submission Gates

1. **Gate 1 — Two-Polarity Single-Feature Leakage Canary (`SegmentHoldout.canary`):** Every one of the `44` channels must satisfy `0.10 <= pooled_auc <= 0.90` (`max(auc, 1 - auc) <= 0.90`) before any model training proceeds.
2. **Gate 2 — Primary Spatially-Blocked Holdout (`gems-segment-pooled-v1`, `1.5 km` collar, `60,988` withheld positives, `1,999` 10 km block-bootstrap draws) + `3.0 km` Bridge (`segment-hide-recover-pooled-v1`):**
   - Must beat `H24-FUSE-HCW` (`0.12372`, current best method-lane-unique & C2ST-passing detector in `GEMSDOE24`) AND `oof_multiphysics_hgb_d3` (`0.13000`, reconstructed OOF multi-physics baseline) on `gems-segment-pooled-v1`, with paired 10 km block-bootstrap CIs reported against `FUSE-HCW`, `oof_multiphysics_hgb_d3`, and `RSHG1` (`0.12899`).
3. **Gate 3 — Pre-Placement Surface & Final-Dot Competing-Method Uniqueness (`PARALLEL-RUN PROTOCOL` Rule 1):**
   - Checked across **all** competing method rasters in `registry/priority_rasters.json`, **all 9** prior `GEMSDOE24` 2026-10-25 rasters (`ASPC`, `MTR1`, `SAHG1`, `CON`, `UNIQUE03`, `OJ1`, `RSHG1`, `FUSE-HCW`, `GVC1`), and **all 83** competition-grid peer blobs in `registry/peer_rasters_20261025.json`:
     - `max |Spearman rho|` (surface & final dots) `<= 0.90`
     - `max candidate_within_3px_of_reference` (final dots vs. all competing method lanes) `<= 0.70`
   - Literal `13gems` spacing-5 calibration lattice (`registry-039`, `99.9%` 3-px footprint coverage) remains unseparated in `priority_rasters.json` and is reported transparently as a governance blocker rather than silently deleted.
4. **Gate 4 — Exact-File C2ST Nuisance Audit (`gems.c2s2`):** Written `-zeros.tif` must achieve grouped spatial-CV `observed_auc < 0.55` (`not flagged` after Holm adjustment across `[road_m, claim_m, block_1..4]`).
5. **Gate 5 — Out-of-Fold Halo & Terrain Sanity Gate (New Post-`GVC1` Live-Transfer Safeguard):**
   - `d_cat <= 2.0 px`: `0.0%`
   - `2.0 < d_cat <= 5.0 px`: `<= 25.0%` (preventing `GVC1`'s `45.8%` and `RSHG1`'s `38.3%` halo collapse)
   - `d_cat > 30.0 px` (deep concealed basin/interior discovery): `>= 22.0%` (vs `GVC1`'s `4.1%`)
   - `NoLid%` (coverage of the `31.8%` 3DEP LiDAR gap): `15.0% <= NoLid% <= 35.0%`
6. **Gate 6 — Exact GeoTIFF Validator & Schema-v2 Automated Preflight (`submission_writer.py` + `preflight_submission.py`):**
   - Single-band `float32` `EPSG:32611` `(3465, 2232)`, strict whole-array values in `[0.0, 1.0]` (`0.0` outside footprint in primary `-zeros.tif`, companion `-nan.tif` + `.zip`), unique filename, `<= 140`-character note, and fail-closed schema-v2 `.preflight.json` (`DO_NOT_SUBMIT` until independent external selector approval).
