# PhD Findings, `GEMSDOE32` Mathematical Dissection & Live Nine-Site Executive Synthesis: `H24-S3DEP1` (2026-10-26)

- **Lane ID**: `H24-S3DEP1` (*Seamless 10 m USGS 3DEP Monoclinal-Step × 19-Band Crustal Strain/Seismic × OpenEI GDR #1391 Hydrothermal Conduit Dual-Objective Stitched-OOF*)
- **Preregistration**: [`knowledge/29_preregistered_S3DEP1_2026-10-26.md`](29_preregistered_S3DEP1_2026-10-26.md) locked at commit `7e6db4d428aea6c26a769feed71f4de04f50f613` prior to model execution
- **Primary Artifact (`-zeros.tif`)**: `docs/downloads/gems24-s3dep1-negative-10m-monoclinal-20261026-464fa34b4091-zeros.tif` (`SHA-256: 86516533fb525ebce792152ae4ed852e88ae4feda0bd596710c7319a238b8071`)
- **Single-TIFF ZIP**: `docs/downloads/gems24-s3dep1-negative-10m-monoclinal-20261026-464fa34b4091-zeros.zip` (`SHA-256: ab88bde8b0868ea715b26b25368535638179c34a062c14f57ba57e0576b530c4`)
- **NaN-Outside Twin (`-nan.tif`)**: `docs/downloads/gems24-s3dep1-negative-10m-monoclinal-20261026-464fa34b4091-nan.tif` (`SHA-256: 039678640909e8965582e31833bd785a2b62b4c2a776682ad49c50529b8daa6e`)
- **Submission Note (`108 <= 140` chars)**: `GEMS24 S3DEP1 | 10m 3DEP+crustal OOF 37654d | id 464fa34b4091 | HOLDOUT-DTI 0.1661 | research; DO NOT SUBMIT`
- **Autonomous Verdict**: **`negative` · `DOWNLOAD: YES` (research/audit only) · `SUBMIT: NO` (`DO_NOT_SUBMIT` via `gems-selector-v2-literal-quota-fail-closed`)**
- **Experiment & Slot Budget**: `3 / 3` preregistered experiments spent (`Arm 1`, `Arm 2`, `Arm 3` in `1,271.5 s`, peak RSS `3,658.9 MiB`); `0` weekly DrivenData slots spent; zero post-hoc retuning permitted.

---

## 1. PhD Analysis: Why & How `GEMSDOE32` (`h33-h33-2-b2`, `0.2778` `UNVERIFIED-OWNER-REPORT`) Achieved the Highest Nine-Site Score — and How to Surpass It

### 1.1 Exact Pixel-Set Genealogy (Zero Added Detections)
Every leaderboard figure in the standing prompt (`0.2778`, `0.2750`, `0.2710`, `0.2708`, `0.2632`, `0.2600`, `0.2477`, `0.2449`, plus conflicting global-leader snapshots `0.3195` vs `0.4413` and owner-noted `0.4437`) is strictly labeled **`UNVERIFIED-OWNER-REPORT`** because zero artifact-linked DrivenData submission-page receipts exist in any inspected repository, and automated access to `drivendata.org` is prohibited.

Direct SHA-verified pixel-set comparison (`evidence/priority_review_20261025.json` and `data/research/nine_site_20261026_refresh/GEMSDOE32/.../gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif`, `SHA-256: c55bafc47005...`) proves that the entire progression from `0.1922` to `0.2778` added **zero new geological detections**:

1. **`H19-5` (`161,366` contiguous ridge pixels, `0.1922` `UNVERIFIED-OWNER-REPORT`)**: Supervised 30-band multi-physics + 1 m LiDAR scarp detector trained on the public INGENIOUS/USGS fault raster.
2. **`D1.5` (`GEMSDOE24`, `60,069` pixels, `0.2477` `UNVERIFIED-OWNER-REPORT`)**: Geodesic Poisson-disk dot-thinning (`spacing ~ 150 m`) along the exact `H19-5` skeleton. Because the evaluation kernel is a `300 m` (`3 px`) Euclidean triangle $K(d)=\max(0, 1 - d/300\text{ m})$ (`src/gems/metric.py`), spacing dots every `200–300 m` retains nearly all true-positive kernel coverage $T=\text{TP}_w$ while cutting false-positive mass $F=\text{FP}_w$ by $>62\%$.
3. **`D2.8` (`GEMSDOE25` / `GEMSDOE30`, `44,090` pixels, `0.2600` `UNVERIFIED-OWNER-REPORT`)**: Wider `~280 m` Poisson-disk spacing on `H19-5`.
4. **`H27-4` (`GEMSDOE31`, `40,199` pixels, `0.2708` `UNVERIFIED-OWNER-REPORT`)**: `D2.8` with `3,891` near-catalogue flank dots pruned.
5. **`H33-B2` (`GEMSDOE32`, `37,654` pixels, `0.2778` `UNVERIFIED-OWNER-REPORT`)**: Exact subset of `D2.8` (`B2 ⊂ H27-4 ⊂ D2.8`, zero pixels added) obtained by deleting all **`6,436` dots within $d_{\text{cat}} \le 200\text{ m}$ (`2 px`)** of the public fault catalogue.

### 1.2 Exact Tversky DTI Deletion & Marginal-Addition Calculus
Under pooled Distance-Tolerant Intersection (`alpha = 0.2`, `beta = 0.8`, `src/gems/metric.py`):

$$D = \frac{T}{(1-\beta)T + \alpha F + \beta G} = \frac{T}{0.2\,T + 0.2\,(N - T) + 0.8\,G} = \frac{T}{0.2\,N + 0.8\,G}$$

where $G = T + \text{FN}_w$ is the fixed hidden-fault positive count, $N = T + F$ is total off-catalogue emitted mass, and $T = \sum_{x \in \mathcal{G}_{\text{hid}}} \max_{\hat{x} \in \hat{Y}} K(\|x - \hat{x}\|_2)$ is kernel-weighted true-positive recovery.

1. **Why deleting $6,436$ near-catalogue ($d_{\text{cat}} \le 200\text{ m}$) dots raised `0.2600 -> 0.2778` (`+0.0178`)**: Public fault pixels are masked before scoring, and withheld hidden faults are predominantly distinct unmapped structures rather than parallel traces `100–200 m` beside already-mapped faults. Those `6,436` halo dots carried $\Delta T \approx 0$ while paying full false-positive penalty $0.2\,\Delta F \approx 1,287.2$ denominator units. Removing $\Delta N = 6,436$ zero-credit dots scales $D$ by $(0.2 N_0 + 0.8 G) / (0.2(N_0 - 6,436) + 0.8 G) \approx +6.8\%$, matching $0.2778 / 0.2600 = 1.0685$.
2. **Exact marginal-precision threshold to beat `0.2778` / `0.3195` / `0.4413` genuinely**: Adding $\Delta N$ new dots with expected marginal kernel credit $\bar{\tau} = \Delta T / \Delta N$ strictly increases $D$ over baseline $D_0$ if and only if:

$$\bar{\tau} > \tau^*(D_0) = \frac{\alpha D_0}{1 - (1 - \beta - \alpha) D_0} = \frac{0.2\,D_0}{1 - 0.2\,D_0}$$

| Reference Benchmark | `D_0` (`UNVERIFIED-OWNER-REPORT`) | Break-Even Marginal Credit $\tau^*(D_0)$ per Added Dot | Geological Requirement (Without Copying `H19-5`/`B2`) |
|---|---:|---:|---|
| `GEMSDOE32 H33-B2` | `0.2778` | **`5.88%`** (`0.05883`) | Recover unmapped faults in the **31.8% 1 m LiDAR gap** (`1,641,254` cells) and sub-alluvial basins at zero $d_{\text{cat}} \le 200\text{ m}$ waste |
| Prompt Leader Snapshot A | `0.3195` | **`6.83%`** (`0.06826`) | Seamless `10 m` 3DEP + crustal strain/seismic + blind hydrothermal alteration/MT/InSAR |
| Prompt Leader Snapshot B | `0.4413` | **`9.68%`** (`0.09680`) | High-precision concealed intrabasin & relay-ramp fault localization (likely aided by external remote sensing / 3D MT / manual Quaternary scarp interpretation permitted by rules) |

---

## 2. Four Novel Geological Hypotheses Ranked Prior to Execution

Full specifications are locked in [`knowledge/29_preregistered_S3DEP1_2026-10-26.md`](29_preregistered_S3DEP1_2026-10-26.md):

1. **`H24-S3DEP1` (Rank 1 — Executed in this session)**: *Seamless 10 m USGS 3DEP Sub-Cell Monoclinal Step-Asymmetry × Restored 19-Band Crustal Strain/Seismic × OpenEI GDR #1391 Hydrothermal Conduit Dual-Objective OOF (`61` channels, **zero 1 m LiDAR**).* Uses USGS 3DEP 1/3 arc-second (`~10 m`) seamless DEM tiles ([ScienceBase `4f70aa9fe4b058caae3f8de5`](https://www.sciencebase.gov/catalog/item/4f70aa9fe4b058caae3f8de5)), six previously dropped `training_features.tif` crustal/seismic channels (`mag_anom`, `geod_2ndinv`, `iso_grav_anom_slope`, Bouguer `tc`, `log1p(deq_n100a15)`, `log1p(ieq_n100a15)`), and OpenEI GDR [#1391](https://gdr.openei.org/submissions/1391) hydrothermal upflow tracers while **strictly withholding all 15 1 m LiDAR channels**.
2. **`H24-SENT2-HYDRO` (Rank 2 — Unexecuted, needs external cloud-free composite)**: *Sentinel-2 L2A `20 m` SWIR Clay/Carbonate/Ferric Alteration Lineaments (`B11/B12`, `B04/B02`) × Shallow AEM Conductivity Step (`|\nabla \log(1 + \text{cond\_surf})|`).* Official source: [Copernicus / Element84 Earth Search STAC `sentinel-2-l2a`](https://earth-search.aws.element84.com/v1/collections/sentinel-2-l2a). Targets zero-relief argillic/silicic alteration halos along blind intrabasin faults under playa/bajada cover.
3. **`H24-USARRAY-MT3D` (Rank 3 — Unexecuted, needs external NetCDF fetch)**: *USGS Great Basin 3D Magnetotelluric Mid-Crustal (`2–15 km`) Sub-Playa Conduit Gradients × `geod_2ndinv` + `deq_n100a15`.* Official source: [USGS ScienceBase `5fb70a0ad34eb413d5e14873`](https://www.sciencebase.gov/catalog/item/5fb70a0ad34eb413d5e14873). Penetrates shallow conductive playa smectite caps that blind `<300 m` AEM (`cond_surf`).
4. **`H24-INSAR-OPERA` (Rank 4 — Unexecuted, needs external OPERA fetch)**: *NASA/JPL OPERA Sentinel-1 `DISP-S1` `30 m` Multi-Annual LOS Velocity Steps Across Basin-Margin Gravity Gradients.* Official source: [NASA ASF / Earthdata CMR `OPERA_L3_DISP-S1_V1`](https://cmr.earthdata.nasa.gov/search/collections.json?short_name=OPERA_L3_DISP-S1_V1). Detects sharp differential ground-water/geothermal aquitard compartmentalization across buried zero-scarp faults.

---

## 3. Executed Results for `H24-S3DEP1`: New All-Time Repository `HOLDOUT-DTI` Point-Best (`0.166060`) & Binding Negative Stop

### 3.1 Three-Experiment Preregistered Readout (`gems-segment-pooled-v1`, `60,988` Withheld Positives)

| Arm / Control | 1 m LiDAR Channels Used | `NW` | `NE_LidarGapHeavy` | `SW` | `SE` | Pooled `HOLDOUT-DTI` | 95% Block-Bootstrap CI (`10 km`, `1,999` draws) |
|---|---:|---:|---:|---:|---:|---:|---|
| **`Arm 3`: `H24-S3DEP1` Hybrid Primary (`0.65` Core + `0.35` Kernel300)** | **`0`** | **`0.16392`** | **`0.21972`** | `0.11667` | **`0.18336`** | **`0.166060`** | **`[0.151858, 0.180339]`** |
| `Arm 1`: `S3DEP1` Dual-Negative (`d3+d9`) Core Classifier (`61` ch) | `0` | `0.16288` | **`0.22088`** | `0.11491` | `0.18405` | **`0.165366`** | `[0.150978, 0.179262]` |
| `Arm 2`: `S3DEP1` Pure `300 m` Kernel Soft-Label Regressor (`61` ch) | `0` | `0.15928` | `0.20591` | `0.11417` | `0.17433` | `0.158449` | `[0.144850, 0.172777]` |
| Control: `H24-DPRF1` Exact Replay (`52` ch, includes `15` 1 m LiDAR ch) | `15` | `0.15425` | `0.21227` | **`0.12768`** | `0.17442` | `0.163792` | `[0.150446, 0.177390]` |
| Control: Reconstructed `oof_multiphysics_hgb_d3` (`27` ch) | `10` | `0.14613` | `0.13464` | `0.10490` | `0.14558` | `0.129997` | `[0.115648, 0.143963]` |

- **`3.0 km` Bridge Protocol (`segment-hide-recover-pooled-v1`, `60,988` withheld)**: **`HOLDOUT-DTI = 0.162568`** (`[0.144755, 0.180606]`), statistically tied with `H24-DPRF1` (`0.162902`, $\Delta = -0.000334$) and far ahead of `DKRN1` (`0.154615`), `TRSG1` (`0.146741`), `RSHG1` (`0.131120`), and `FUSE-HCW` (`0.123620`).
- **Paired Block-Bootstrap Deltas (`10 km` blocks, `1,999` resamples)**:
  - `Arm 3 - oof_multiphysics_hgb_d3`: **`+0.036063`** (`[+0.020819, +0.051946]`, **`4 / 4` folds won**, strictly positive 95% CI).
  - `Arm 3 - Arm 2 (Kernel300)`: **`+0.007612`** (`[+0.002611, +0.012555]`, **`4 / 4` folds won**, strictly positive 95% CI).
  - `Arm 3 - H24-DPRF1 (replay)`: **`+0.002268`** (`[-0.006994, +0.011442]`, **`3 / 4` folds won**: `NW +0.00967`, `NE +0.00745`, `SE +0.00894`, `SW -0.01101` where dense 1 m LiDAR scarps dominate; paired 95% CI spans zero).
- **61-Channel Two-Polarity Leakage Canary**: **PASS (`61 / 61`)** — worst raw pooled AUC `gvc_elev_local_resid = 0.6111 <= 0.90` (`s3dep1_quad_oof_hybrid` diagnostic AUC `0.7336 <= 0.90`). Strongest solo new channels: `dem10_hgm200_mean = 0.6053`, `dem10_slope_std = 0.5887`, `dem10_hgm50_max = 0.5802`, `bouguer_tc_mgal` (`0.4270`, extremity `0.5730`), `s3dep_monoclinal_step_index = 0.5687`, `s3dep_scarp_over_incision = 0.5679`.

### 3.2 Novelty, C2ST & Why `H24-S3DEP1` Stopped Honestly at `DO_NOT_SUBMIT`

1. **Parent-Convergence Against `H24-DPRF1` Cured (`64.45% <= 70%`)**: Every previous high-scoring extension in this repository (`CUP1 = 91.2%`, `EUL1 = 86.57%`, `DKRN1 = 75.68%`) exceeded the `70%` 3-px dot-overlap ceiling against `DPRF1` because 1 m LiDAR scarps dominated tree splits inside the `68.2%` LiDAR coverage polygon. Withholding all `15` 1 m LiDAR channels reduced 3-px overlap with `DPRF1` to **`64.45% <= 70.0%` (`PASS`)**, `54.72%` vs `TRSG1`, `46.95%` vs `GEMSDOE32 B2`, `<= 54.33%` across all `83` peer blobs (`PASS`), and `<= 53.17%` across all `32` live `2026-10-26` sibling focus GeoTIFFs (`PASS`).
2. **Binding Overlap Flag vs Local Stopped Lane `DKRN1` (`71.32% > 70%`)**: Against `69` competing method rasters in the combined local + portfolio registry, `S3DEP1` passed `68 / 69` and exceeded `70%` by **`+1.32 pp` (`71.32%`)** against a single raster: local stopped lane `DKRN1` (`gems24-dkrn1-negative-d8-knick-kernel-20261026-7f031285130c-zeros.tif`). Diagnosis: `DKRN1`'s gap-native Head A (`47` channels) and `S3DEP1` (`61` channels) share the exact same `37` non-LiDAR geophysical/hydrothermal channels and `300 m` submodular allocator, causing convergence inside basin margins and the `31.8%` LiDAR gap. In addition, the retained synthetic spacing-5 lattice (`registry-039`, `99.87%` footprint coverage at `3 px`) forces `99.51%` literal overlap by pigeonhole (`>= 82.34%` for any `37,654`-dot set). Per Parallel-Run Protocol Rule 1, we logged the result immediately and performed **zero post-hoc retuning**.
3. **Binding Exact-File C2ST Nuisance Flag (`AUC = 0.6012`, `Holm p = 0.0200`)**: While training labels pass C2ST (`AUC = 0.5040`), `S3DEP1`'s emitted dots recorded `AUC = 0.6012` against `road_m / claim_m / block_1..4`. Diagnosis: our preregistration residualized all `19` non-topographic geophysical/seismic channels (`S3DEP1_RESID_INDICES`) and applied `UnconditionalNuisanceLogitCalibrator`, **but intentionally excluded `dem10_*` sub-cell gradients** under the assumption that seamless `10 m` DEM is purely topographic. At `10 m` resolution (`1/3` arc-sec), paved US/state highways across Great Basin valleys create `15–25 m` road-cut benches and elevated fill embankments (`dem10_onesided3`, `dem10_steep_ratio_max`) directly along `tiger_road_distance_m = 0`, imprinting road-corridor contrast onto the tree splits that post-hoc marginal logit debiasing over `6` coarse basis terms cannot fully erase.
4. **Flagged Metadata Irregularity (`IRR-S3DEP1-TC-BAND`)**: Band 6 (`tc`) of `data/training_features.tif` carries an inherited bridge GDAL description claiming *"Tilt angle or total curvature"*, yet direct inspection of all `5,167,373` in-footprint cells proves strictly positive values `[2.948, 88.573]` (median `13.48`, mean `15.86`), which physically is the USGS/INGENIOUS **Complete Bouguer gravity terrain correction (`tc`, in mGal)** — never a `[-pi/2, +pi/2]` tilt angle or zero-mean curvature. Documented in `data/prepared/s3dep1_stack61.json`.

---

## 4. Live `2026-10-26` Nine-Site `main` HEAD Master Forensic Table

All `8` sibling repositories were freshly pulled at their live `2026-10-26` `main` HEAD commits (`32` GeoTIFFs SHA-verified in `data/research/nine_site_20261026_refresh/manifest_20261026.json`; full machine-readable ledger in [`evidence/nine_site_executive_summary_s3dep1_20261026.json`](../evidence/nine_site_executive_summary_s3dep1_20261026.json)):

| Site & Live `main` HEAD | Historical Reference (`UNVERIFIED-OWNER-REPORT`, Do Not Copy) | Live `2026-10-26` Featured Research `.tif` (`SHA-256` prefix) | Strict `[0,1]` / Dots / Apron / `>2 km` | `S3DEP1` 3-px Overlap | Autonomous Download / Submit Verdict & Flagged Irregularities |
|---|---|---|---|---:|---|
| **[GEMSDOE24](https://buffedlizard55-lab.github.io/GEMSDOE24/)** `5cfab745` + this PR | `h25-1-dotted-h19-5-d1-5` (`0.2477`) | `gems24-s3dep1-negative-10m-monoclinal-20261026-464fa34b4091-zeros.tif` (`86516533fb52`) | **PASS** · `37,654` · `22.2%` / `52.1%` | self (`64.45%` vs `DPRF1`) | **DOWNLOAD: YES · SUBMIT: NO.** New all-time recorded `HOLDOUT-DTI = 0.16606` (`[0.15186, 0.18034]`, zero 1 m LiDAR); stopped on `71.32%` vs local `DKRN1`, `C2ST = 0.6012`, paired CI vs `DPRF1` spanning 0, and `registry-039`. |
| **[GEMSDOE25](https://buffedlizard55-lab.github.io/GEMSDOE25/)** `bc3381fd` | `dotted-h19-5-d2-8` (`0.2600`) | `gems25-h72-3-subsurf-pttg-mths-sapd3-0-k3p0-20261026-88bbebfe79b4-zeros.tif` (`51f6e3cb83d7`) | **PASS** · `41,061` · `46.5%` / `24.0%` | **`27.86%`** (`PASS`) | **DOWNLOAD: YES · SUBMIT: NO.** `H72-3` self-marks `SUBMIT: NO` after confirmation miss. |
| **[GEMSDOE27](https://buffedlizard55-lab.github.io/GEMSDOE27/)** `f1e32af8` | `topo-gap-closure-t-v2` (`0.2449`); `H29-CELF` (`0.2190`) | `gems27-h31-drcg-wl-celf28-20261026-cf8e1bbef244-allfinite.tif` (`2c002b027924`) | **PASS** · `37,654` · `34.4%` / `43.8%` | **`52.62%`** (`PASS`) | **DOWNLOAD: YES · SUBMIT: NO.** Non-comparable `289,180`-px split (`0.04730`); `~0.235` is an unverified `PROJECTION`, not a score; omits `registry-039`. |
| **[GEMSDOE28](https://buffedlizard55-lab.github.io/GEMSDOE28/)** `9c1be21e` | `h36-1-rung30-blind-r1` (`0.2710`) | `gems28-s20-nchc-20261026-d432a1d5d6ee-allfinite.tif` (`1d629d6c953c`) | **PASS** · `40,071` · `53.0%` / `23.8%` | **`28.50%`** (`PASS`) | **DOWNLOAD: YES · SUBMIT: NO.** `HOLDOUT-DTI = 0.13126` (`53.0%` apron); **Irregularity**: `12 / 44` repo downloads un-manifested. |
| **[GEMSDOE30](https://buffedlizard55-lab.github.io/GEMSDOE30/)** `35ce8911` | `d28-poisson300m-offcat` (`0.2600`) | `GEMSDOE30-geothermal-corridor-offcat-d3-20261026T160300Z.tif` (`0ed267020015`) | **FAIL (`7,111,787` outside NaN)** · `40,000` · `24.4%` / `43.4%` | **`13.04%`** (`PASS`) | **DO NOT SUBMIT.** **Irregularity**: outside-footprint `NaN`s fail strict whole-array `[0, 1]` check; `H30-14` (`0.1371`) self-marked `DO NOT SUBMIT`. |
| **[GEMSDOE31](https://buffedlizard55-lab.github.io/GEMSDOE31/docs/)** `78f9bf3a` | `h27-4-solo-d28` (`0.2708`) | `gemsdoe31-h31t-transtension-dinkelbach-20261025-b37654-zeros.tif` (`83fbc267a754`) | **PASS** · `37,654` · `24.5%` / `51.5%` | **`39.87%`** (`PASS`) | **DOWNLOAD: YES · SUBMIT: NO.** `H31-T` (`0.1300` on `gems57`) & `H31-U` (`0.0952`) self-marked `DO NOT SUBMIT`; **Irregularity**: earlier `CSDU` companion had `2,610,312` nonfinite interior cells. |
| **[GEMSDOE32](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html)** `8953b986` | `h33-h33-2-b2` (`0.2778`) | `gemsdoe32-h46-trhv-tworegime-ventconduit-37654-20261026T173000Z-6437b275-zeros.tif` (`9f42346d3ace`) | **PASS** · `37,654` · `45.3%` / `32.9%` | **`35.06%`** (`PASS`) | **DOWNLOAD: YES · SUBMIT: NO.** `H45`/`H46` self-marked `DO NOT SUBMIT`; **Irregularity**: `arena47-perturb-h38-unique` (`f2c238b48468`) is a perturbed derivative prohibited under novelty rules. |
| **[GEMSDOE33](https://buffedlizard55-lab.github.io/GEMSDOE33/)** `a24fb7c5` | `h33d-analog-tip-stepover` (`0.2632`) | `gemsdoe33-a33-r3-llc-37654-20261026-7f91f9f3ced9-zeros.tif` (`76f9e157d01b`) | **PASS** · `37,654` · `38.1%` / `31.2%` | **`31.03%`** (`PASS`) | **DOWNLOAD: YES · SUBMIT: NO.** `A33-R3-LLC` scored `0.13151` and self-marks `DO NOT SUBMIT`. |
| **[GEMSDOE36](https://buffedlizard55-lab.github.io/GEMSDOE36/docs/)** `b90418f8` | `anderson-geothermal-pinn` (`0.2750`) | `gemsdoe36-hvg36-vent-dipole-20261026-b3ee97873192-zeros.tif` (`85d56b03aff1`) | **PASS** · `37,654` · `64.4%` / `9.6%` | **`28.73%`** (`PASS`) | **DOWNLOAD: YES · SUBMIT: NO.** `HVG-36` scored `0.135759` (`64.4%` apron collapse); **Irregularity**: companion `GVSC-36` has `94.6%` internal overlap. |

---

## 5. Remaining Next Steps & Explicit Limitations

### Next Steps for a Future Clean Session
1. **Road-Corridor Masking / Residualization on `10 m` 3DEP Sub-Cell Operators**: Any future `10 m` 3DEP lane must include `dem10_onesided*`, `dem10_hgm50_max`, `dem10_steep_ratio_max`, and `dem10_curv_absmax` inside fold-local `NuisanceResidualizer` (or zero sub-cell step operators within `d_road <= 150 m` of TIGER highways before 900 m lineament integration) so highway cut-and-fill embankments cannot trigger `gems.c2s2` (`AUC < 0.55`).
2. **Orthogonal External Sensing (`H24-SENT2-HYDRO`, `H24-USARRAY-MT3D`, `H24-INSAR-OPERA`)**: Because any two models sharing the same `37` internal non-LiDAR INGENIOUS channels converge near `~70%` 3-px dot overlap at `N = 37,654`, breaking both internal-backbone convergence (`DKRN1` `71.32%`) and pushing `HOLDOUT-DTI` significantly past `0.16606` (paired 95% CI `> 0` vs `S3DEP1` & `DPRF1`) requires genuinely external free official grids (Sentinel-2 SWIR clay/ferric alteration, USArray 3D MT `2–15 km` resistivity, or OPERA `DISP-S1` InSAR velocity steps) in an environment with outbound access to ScienceBase / STAC / Earthdata.
3. **Prospective Selector Governance on `registry-039`**: At standard `37,654`-dot emission, the synthetic spacing-5 calibration lattice (`registry-039`, `99.87%` footprint coverage within `3 px`) forces `>= 82.34%` literal overlap on every possible footprint subset. Any future `OK_TO_SUBMIT` promotion requires either an explicit owner policy update separating `calibration_lattice_control` from `competing_method` inside `selector.py` + verified live DrivenData weekly quota + independent clean-checkout replay certificate, or a smaller ultra-high-precision emission budget evaluated prospectively.

### Limitations
- No organizer-authenticated DrivenData submission-page receipt exists in this repository; all historical leaderboard values remain `UNVERIFIED-OWNER-REPORT`, and no calibrated leaderboard score forecast is claimed for `H24-S3DEP1` or `H24-DPRF1`.
- Outbound network access in this sandbox is restricted to GitHub, PyPI, and npm (`sciencebase.gov`, `openei.org`, `earthdata.nasa.gov`, and `drivendata.org` are unreachable; `10 m` 3DEP vectors were restored from SHA-verified archive `buffedlizard55-lab/GEMSDOE10@91d6566ecc86`).
- Official airborne magnetic acquisition block polygons remain audited vector reconstructions from the published USGS figure (`data/external/audit_sources/acquisition_blocks_receipt.json`), not raw flight-line shapefiles.
