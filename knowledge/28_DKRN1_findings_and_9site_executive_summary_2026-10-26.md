# H24-DKRN1 Findings, PhD Metric Analysis (`0.2778` vs `0.3195` / `0.4413`), and Fresh `2026-10-26` Nine-Site Forensic Executive Summary

- **Date:** `2026-10-26`
- **Repository / Branch:** `buffedlizard55-lab/GEMSDOE24` (`arena/3c6e51cf-gemsdoe24`)
- **Preregistration (frozen prior to code & execution):** [`knowledge/27_preregistered_DKRN1_2026-10-26.md`](27_preregistered_DKRN1_2026-10-26.md) @ commit `86d7f622a0ef5e521611d976e86eab72ad42ce1a`
- **Newly Generated Unique GeoTIFF (`-zeros`, all-finite `[0, 1]`):** [`docs/downloads/gems24-dkrn1-negative-d8-knick-kernel-20261026-7f031285130c-zeros.tif`](../docs/downloads/gems24-dkrn1-negative-d8-knick-kernel-20261026-7f031285130c-zeros.tif)
  - **SHA-256:** `0b114a75d5a905ded84450fe55df386f9361ff39139a2e4452476563ac0fa65d`
  - **Single-GeoTIFF ZIP:** [`docs/downloads/gems24-dkrn1-negative-d8-knick-kernel-20261026-7f031285130c-zeros.zip`](../docs/downloads/gems24-dkrn1-negative-d8-knick-kernel-20261026-7f031285130c-zeros.zip) (`SHA-256: 497b1664c9d651b141f30f4a8240bef4e9a2ae816ba338cd4c01eeaefd5e44f0`)
  - **NaN-outside twin:** [`docs/downloads/gems24-dkrn1-negative-d8-knick-kernel-20261026-7f031285130c-nan.tif`](../docs/downloads/gems24-dkrn1-negative-d8-knick-kernel-20261026-7f031285130c-nan.tif) (`SHA-256: 551c8fb4d7bd80ad2b18cfc5e3d903fd693627beec269374ed8ae10df7ed2530`)
  - **Short Note (`104 <= 140` chars):** `GEMS24 DKRN1 | D8 knick+300m kernel OOF | id 7f031285130c | HOLDOUT-DTI 0.1553 | research; DO NOT SUBMIT`
  - **JSON Run Card:** [`evidence/dkrn1_run_card_20261026.json`](../evidence/dkrn1_run_card_20261026.json)
  - **Independent Selector Receipt (`gems-selector-v2-literal-quota-fail-closed`):** [`evidence/dkrn1_selector_20261026.json`](../evidence/dkrn1_selector_20261026.json)

---

## 1. Unmistakable Automated Decision Banner (Zero Human-Inspector Fallback)

| Artifact | Role | `OK TO DOWNLOAD?` | `OK TO SUBMIT TO DRIVENDATA?` | Automated Selector Decision | Primary Local `HOLDOUT-DTI` (`gems-segment-pooled-v1`, `60,988` withheld) |
|---|---|---|---|---|---|
| **[`gems24-dprf1-stitched-oof-tworegime-20261026-81849d67c8bf-zeros.tif`](../docs/downloads/gems24-dprf1-stitched-oof-tworegime-20261026-81849d67c8bf-zeros.tif)** (`H24-DPRF1`) | **Recorded Local Point-Best** (audit/research reference) | **YES** | **NO (`DO_NOT_SUBMIT`)** | `DO_NOT_SUBMIT` (literal `registry-039` spacing-5 lattice `99.87%` coverage, unknown live quota, no replay certificate) | **`0.16379`** (`95% CI [0.15045, 0.17739]`) |
| **[`gems24-dkrn1-negative-d8-knick-kernel-20261026-7f031285130c-zeros.tif`](../docs/downloads/gems24-dkrn1-negative-d8-knick-kernel-20261026-7f031285130c-zeros.tif)** (`H24-DKRN1`, **this session**) | **New Preregistered Split-View D8-Knickpoint + 300 m Kernel Research GeoTIFF** (`0` copied pixels; wins `NE_LidarGapHeavy` `0.21308`) | **YES** | **NO (`DO_NOT_SUBMIT`)** | `DO_NOT_SUBMIT` (`verdict = "negative"`: `-0.00854` vs `DPRF1`, `75.68% > 70%` 3-px overlap vs `DPRF1`, C2ST `0.5773`) | **`0.15525`** (`95% CI [0.14205, 0.16874]`; `HeadA47 = 0.15072`) |
| **All other local & sibling `.tif` files across `GEMSDOE24..36`** | Historical / negative / unscored research files | **Audit only** | **NO (`DO_NOT_SUBMIT`)** | `DO_NOT_SUBMIT` | Trail `DPRF1` or fail `[0,1]` / apron / holdout gates |

---

## 2. Fresh `2026-10-26` Nine-Site Forensic Executive Summary (`GEMSDOE24, 25, 27, 28, 30, 31, 32, 33, 36`)

Every public leaderboard number quoted in inherited prompts is strictly labeled **`UNVERIFIED-OWNER-REPORT`** (zero DrivenData portal submission-page receipts exist in any inspected checkout). Local holdout measurements are strictly labeled **`HOLDOUT-DTI`**; no leaderboard score projection is made. All 8 sibling `2026-10-26` HEAD `.tif` files were fetched by git blob SHA and audited pixel-by-pixel against `EPSG:32611` (`3730 × 3292`), strict whole-array `[0, 1]` finiteness, public-catalogue distance profiles, `GEMSDOE32 B2`, and `H24-DPRF1` / `H24-DKRN1` ([`evidence/nine_site_executive_summary_dkrn1_20261026.json`](../evidence/nine_site_executive_summary_dkrn1_20261026.json)):

| Focus Site & `2026-10-26` HEAD | Historical Reference (`UNVERIFIED-OWNER-REPORT`, prohibited to copy) | Latest `2026-10-26` Inspected `.tif` & SHA-256 Prefix | Dots & Strict Whole-Array `[0,1]` | `2–9 px` Apron / `>2 km` Far-Field | Local Evidence (`HOLDOUT-DTI`) | 3-px Overlap vs `B2` / `DPRF1` / `DKRN1` | Automated Executive Verdict |
|---|---|---|---|---|---|---|---|
| **[GEMSDOE24](https://buffedlizard55-lab.github.io/GEMSDOE24/)** (`d2368718` + `H24-DKRN1`) | `h25-1-dotted-h19-5-d1-5` (`0.2477`) | **Point-best:** `gems24-dprf1-...-zeros.tif` (`c1257c1d4b5a…`)<br>**New:** `gems24-dkrn1-...-zeros.tif` (`0b114a75d5a9…`) | `37,654` · **PASS** (`0` NaN anywhere) | `DPRF1`: `22.3% / 52.3%`<br>`DKRN1`: `23.8% / 52.2%` | `DPRF1`: **`0.16379`** `[0.15045, 0.17739]`<br>`DKRN1`: **`0.15525`** `[0.14205, 0.16874]` (`NE` **`0.21308`**) | `DKRN1`: `44.1%` / `75.7%` / *self* | **DOWNLOAD: YES · SUBMIT: NO** (`DPRF1` remains local point-best; `DKRN1` negative) |
| **[GEMSDOE25](https://buffedlizard55-lab.github.io/GEMSDOE25/)** (`8774b615`) | `dotted-h19-5-d2-8` (`0.2600`) | `gems25-h71-hgpc-blind-b2-sapd3-k3p5-20261026-9eb0c31e5149-zeros.tif` (`44ee60289f21…`) | `59,472` · **PASS** | `19.3% / 57.1%` | Confirmation miss (`+0.00085` on OLIC; self-marked `SUBMIT: NO`) | `15.4%` / `18.5%` / `25.1%` | **DO NOT SUBMIT** (excessive `59,472` FP dot count & failed confirmation gate) |
| **[GEMSDOE27](https://buffedlizard55-lab.github.io/GEMSDOE27/)** (`cf8b4c20`) | `topo-gap-closure-t-v2-on-d1-5` (`0.2449`); `2026-10-25` `H29-CELF` (`0.2190`) | `gems27-h31-drcg-wl-celf28-20261026-cf8e1bbef244-allfinite.tif` (`2c002b027924…`) | `37,654` · **PASS** | `34.4% / 43.8%` | Non-comparable `0.04730` (`289,180`-px split; lacks `registry-039`) | `50.2%` / `62.2%` / `55.9%` | **DO NOT SUBMIT** (non-harmonized split; `H29-CELF` `0.2190` already scored) |
| **[GEMSDOE28](https://buffedlizard55-lab.github.io/GEMSDOE28/)** (`12ec4fea`) | `h36-1-rung30-blind-r1` (`0.2710`) | `gems28-s20-nchc-20261026-d432a1d5d6ee-allfinite.tif` (`1d629d6c953c…`) | `40,071` · **PASS** | `53.0% / 23.8%` | `HOLDOUT-DTI 0.13126` | `31.1%` / `32.6%` / `29.5%` | **DO NOT SUBMIT** (`53.0%` apron clustering; trails `DPRF1` by `-0.03253`) |
| **[GEMSDOE30](https://buffedlizard55-lab.github.io/GEMSDOE30/)** (`35ce8911`) | `d28-poisson300m-offcat-44090` (`0.2600`) | `GEMSDOE30-geothermal-corridor-offcat-d3-20261026T160300Z.tif` (`0ed267020015…`) | `40,000` · **FAIL (`NaN` outside footprint!)** | `24.4% / 43.4%` | Unscored; self-marked `DO NOT SUBMIT` | `14.5%` / `27.6%` / `12.4%` | **DO NOT SUBMIT** (**portal `[0,1]` rejection hazard**: `7,111,787` `NaN` cells outside footprint!) |
| **[GEMSDOE31](https://buffedlizard55-lab.github.io/GEMSDOE31/docs/)** (`8e91d82a` / `70fd6538`) | `h27-4-solo-d28` (`0.2708`) | `gemsdoe31-pgr31-poisson-pseudograv-37654-20261026-zeros.tif` (`9dcc2e0c4da3…`) | `37,654` · **PASS** | **`69.2% / 7.5%`** | `PGR31` & `H31-N` self-marked `DO NOT SUBMIT` | `33.2%` / `35.8%` / `24.4%` | **DO NOT SUBMIT** (**severe `69.2%` apron collapse** — identical pathology to `GVC1` `0.0859`) |
| **[GEMSDOE32](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html)** (`8b00ee91`) | **`h33-h33-2-b2-...-zeros` (`0.2778`)** | `gemsdoe32-h38g1-lidar-geodawn-gdr-celf37654-20261026T013500Z-35859e28-zeros.tif` (`6efe140229c4…`) | `37,654` · **PASS** | `43.2% / 33.6%` | `0.11696` (`HIDE-RECOVER-v3.0`); self-marked `DO NOT SUBMIT` | `58.8%` / `59.8%` / `38.0%` | **DO NOT SUBMIT** (`B2` prohibited to copy; `H38G1` trails local point-best) |
| **[GEMSDOE33](https://buffedlizard55-lab.github.io/GEMSDOE33/)** (`0384d793`) | `h33d-analog-tip-stepover-r30` (`0.2632`) | `gemsdoe33-a33-r3-llc-37654-20261026-7f91f9f3ced9-zeros.tif` (`76f9e157d01b…`) | `37,654` · **PASS** | `38.1% / 31.2%` | `HOLDOUT-DTI 0.13151`; self-marked `DO NOT SUBMIT` | `37.5%` / `37.3%` / `32.2%` | **DO NOT SUBMIT** (trails `DPRF1` by `-0.03228`; self-marked negative) |
| **[GEMSDOE36](https://buffedlizard55-lab.github.io/GEMSDOE36/docs/)** (`2c78770e`) | `anderson-geothermal-pinn-38854` (`0.2750`) | `gemsdoe36-atvr36-20261026.tif` (`54f493f4fa5c…`) | `37,654` · **PASS** | `44.3% / 24.2%` | `ATVR-36`/`MTO-36`/`WDP-36`/`MOE36` (`0.0676–0.1249`) | `35.9%` / `44.2%` / `17.5%` | **DO NOT SUBMIT** (all 4 `2026-10-26` `GEMSDOE36` lanes self-marked `DO NOT SUBMIT`) |

---

## 3. Evidence-bounded analysis of `GEMSDOE32 B2`'s reported `0.2778` (`UNVERIFIED-OWNER-REPORT`)

### 3.1 Exact pixel genealogy of `B2` — geometry, not hidden-label truth

SHA-verified pixel comparison in `evidence/priority_review_20261025.json` and [`docs/metric-integrity-20261026.md`](../docs/metric-integrity-20261026.md) establishes a deterministic subset relationship among the stored masks:

1. `D2.8` is recorded as 44,090 dots.
2. `H33-B2` is recorded as 37,654 dots.
3. The B2 mask contains no dots outside D2.8; 6,436 D2.8 dots are absent from B2, and the removed cells fall in the repository's public-catalogue distance band.

The historical values associated with those files (`0.2600` and `0.2778`) are **UNVERIFIED-OWNER-REPORT** values. The mask relationship does not reveal the organizer's hidden labels and does not establish that the removed dots were false positives, zero-credit cells, or newly absent faults.

### 3.2 A bounded DTI mechanism hypothesis, not a causal explanation

For the shared local evaluator, the metric is a distance-weighted Tversky-style quantity with `alpha = 0.2`, `beta = 0.8`, and a 300 m triangular kernel. In abstract terms, deleting a prediction can raise the metric when the hidden true-positive mass lost is smaller than the false-positive mass removed; it can also lower the metric when the removed cells are near withheld positives. That conditional algebra is useful for experiment design, but it cannot be evaluated for the organizer's hidden labels from this checkout.

The hidden contributions `T`, `F` and `N` for the reported live result are unavailable. We therefore do **not** claim that B2 removed zero-credit cells, that `0.2 × 6,436` is a live denominator change, that B2 discovered zero new faults, or that deletion caused `0.2600 → 0.2778`. The evidence-bounded conclusion is: **plausible emission-policy effect; hidden-label causality unproven**. The conflicting `0.3195` and `0.4413` snapshots also have no artifact-linked organizer receipts.

### 3.3 Consequence for prospective work

B2 is a historical reference and is prohibited from copying or perturbing. A future method must be genuinely independent, must hide whole fault segments with a buffer, derive catalogue features from visible faults only, and must report a local **HOLDOUT-DTI** with evaluator, withheld-positive count and 95% CI. No local holdout is a leaderboard estimate. Any prospective raster also needs the strict finite-array writer, two-polarity feature canaries, pre-placement/final registry checks and a separate selector decision.

---

## 4. Four Untried Geological Hypotheses Ranked Before Implementation

Frozen in [`knowledge/27_preregistered_DKRN1_2026-10-26.md`](27_preregistered_DKRN1_2026-10-26.md) at commit `86d7f622a0ef` before writing a single line of experiment code:

| Rank | Candidate ID & Physical Mechanism | Specific Layers Used | Why It Catches Faults Missing from USGS/INGENIOUS Catalogue | Named Non-Fault Mimic | How It Differs from All 15 Stopped Lanes | Cost & Data Availability |
|---|---|---|---|---|---|---|
| **1 (Tested here -> `H24-DKRN1`)** | **Split-View Topological D8 Drainage-Knickpoint Routing + `300 m` DTI-Kernel Soft-Label Regression + 3-Regime Net-Tversky Allocation** | `det_elev`, `terr_slope`, `iso_grav_anom_hg`, `tmi_hg`, `gb_conduits`, `thk_ratio`, `lidar_dem_slope_max_100m`, plus `52`-ch base/GVC/SAHG stack | Ephemeral washes crossing active faults or the `31.8%` LiDAR gap preserve Flint's-law stream-power knickpoint steps ($\Omega = A^{0.45} S_{\text{D8}}$) and 4-step thalweg dog-legs even where interfluve scarps are buried by sheetfloods | Differential erosion across resistant Tertiary welded tuff / basalt caprock ledges, non-tectonic fan-head trench banks, and Lake Lahontan wave-cut shorelines | First exact global sparse triangular D8 flow-routing solve $(I - P^\top)A = \mathbf{1}$ (`12.28M` cells), first continuous `300 m` DTI-kernel regressor (`Head A`, withholding all 15 LiDAR amplitude channels), first Elkan (2001) prior-odds calibration + 3-regime (`48/28/24%`) Net-Tversky allocator | `~34 min` on 2-core CPU (`3.26 GiB` RSS); 100% local staged data |
| **2 (Next Recommended -> `H24-DRAIN5R-PURE`)** | **Fully Nuisance-Residualized Pure Gap-Native Kernel Regressor (Zero-DPRF1-Head Architecture)** | `47` LiDAR-amplitude-free channels (`det_elev` D8 routing + potential-field tilt/HGM + INGENIOUS hydrothermal DoGs), **all** hydrologic & regime channels residualized against `road_m`/`claim_m`/blocks | Captures `DKRN1` Arm 2's `0.15072` LiDAR-gap & piedmont recovery while eliminating both Head B's `75.68%` `DPRF1` dot convergence and `m_hydro`'s valley wash-road C2ST correlation | Valley-axis axial trunk streams and welded-tuff hogback ledges | Drops Head B (`DPRF1` 62-ch classifier) completely so 3-px overlap vs `DPRF1` falls well below `70%` and residualizes all D8 wash features to pass C2ST `< 0.55` | `~18 min` CPU; 100% local staged data |
| **3 (Untried)** | **`H24-FLEX3` — Elastic-Plate Flexural Curvature × Bouguer Basement-Bench Decoupling** | `det_elev` 2–8 km flexural curvature, `depth_to_base_surf`, `iso_grav_anom`, `tmi_rtp` | Blind antithetic accommodation faults and intra-basin horst blocks flex basin floors over $2\text{–}6\text{ km}$ wavelengths above basement gravity benches without a `100 m` scarp | Compactional differential subsidence over buried paleo-valleys or Miocene caldera ring margins | Long-wavelength elastic plate flexure vs basement-depth decoupling (distinct from `CRP1` short-wave saddles and `PAIR1` `300–600 m` graben pairs) | `~25 min` CPU; 100% local staged data |
| **4 (Untried — external network host required)** | **`H24-INSAR4` — Sentinel-1 ARIA Unwrapped Interseismic Phase-Gradient Discontinuity** | NASA ASF / JPL ARIA Sentinel-1 L2 GUNW unwrapped phase & coherence + `gb_strain_rate` | Directly images aseismic creep, geothermal-fluid-coupled subsidence boundaries, and blind Walker Lane shear steps across zero-relief playas | Valley-fill aquifer seasonal poroelastic drawdown bowls and atmospheric stratified-troposphere ramps | Direct active displacement-field measurement (zero reliance on fossil topography or static potential fields) | Free official NASA Earthdata / ASF (`search.asf.alaska.edu`), blocked only inside this sandbox's host allowlist |

---

## 5. `H24-DKRN1` Experimental Results & Three Durable Post-Mortem Discoveries

### 5.1 Three-Arm Same-Evaluator Readout (`gems-segment-pooled-v1`, `60,988` Withheld Positives)

| Arm / Comparator | NW (`k=8,515`) | `NE_LidarGapHeavy` (`k=10,528`) | SW (`k=10,535`) | SE (`k=8,526`) | Pooled `HOLDOUT-DTI` | `95%` Block-Bootstrap CI | `3.0 km` Bridge `HOLDOUT-DTI` |
|---|---|---|---|---|---|---|---|
| **Arm 1: `H24-DKRN1` (62-ch Split-View + 3-Regime Net-Tversky)** | `0.14986` | **`0.21308`** *(wins!)* | `0.12107` | `0.15390` | **`0.15525`** | `[0.14205, 0.16874]` | **`0.15462`** `[0.13653, 0.17280]` |
| **Arm 2: `HeadA47` Pure Gap-Native `300 m` Kernel Regressor (0 raw LiDAR ch.)** | `0.14933` | `0.20792` | **`0.12168`** | `0.14144` | **`0.15072`** | `[0.13730, 0.16425]` | — |
| **Arm 3: Same-Session `H24-DPRF1` 52-ch Replay** *(recorded `DPRF1`: `0.16379`)* | `0.15639` | `0.21227` | `0.12768` | `0.17442` | **`0.16416`** | `[0.15076, 0.17773]` | `0.16290` (recorded) |
| **Reconstructed `oof_multiphysics_hgb_d3` (27-ch OOF baseline)** | `0.14613` | `0.13464` | `0.10490` | `0.14558` | **`0.13000`** | `[0.11565, 0.14396]` | — |

- **Paired bootstrap Δ (`Arm 1` vs `oof_multiphysics_hgb_d3`):** **`+0.02525`** (`95% CI [+0.01006, +0.04022]`, **`4/4` folds won**, `NE_LidarGapHeavy` gain **`+0.07845`**!).
- **Paired bootstrap Δ (`Arm 2 HeadA47` vs `oof_multiphysics_hgb_d3`):** **`+0.02072`** (`95% CI [+0.00493, +0.03593]`) — **using ZERO raw 1 m LiDAR amplitude channels**, outperforming every prior non-`DPRF1`/`EUL1` lane in `GEMSDOE24` history (`GVC1` `0.14876`, `TRSG1` `0.14644`, `CRP1` `0.14494`, `CUP1` `0.14366`, `TNR1` `0.13219`, `RSHG1` `0.12899`, `PAIR1` `0.12711`).
- **Paired bootstrap Δ (`Arm 1` vs `Arm 2`):** **`+0.00453`** (`95% CI [+0.00173, +0.00768]`, `3/4` folds won).
- **Paired bootstrap Δ (`Arm 1` vs `Arm 3 DPRF1 replay`):** **`-0.00891`** (`95% CI [-0.01530, -0.00224]`, `1/4` folds won — `NE_LidarGapHeavy` `+0.00081`; primary deficit in `SE` `-0.02053` where `DPRF1`'s 68% LiDAR scarp concentration dominates).

### 5.2 Three Quantitative Lessons Recorded for Future Sessions
1. **Topological D8 flow-routing genuinely unlocks the `31.8%` LiDAR gap:** Solving $(I - P^\top)A = \mathbf{1}$ in `5.3s` across `12.28M` cells lifted `NE_LidarGapHeavy` to **`0.21308`** (the highest `NE_LidarGapHeavy` score recorded in `GEMSDOE24`, surpassing `DPRF1` `0.21227`, `TRSG1` `0.18760`, `RSHG1` `0.17285`, and `oof_multiphysics_hgb_d3` `0.13464`).
2. **Exact quantification of parent convergence across three architectures:**
   - `CUP1` vs `GVC1`: `91.20%` 3-px dot overlap (`+21.20` pp over the `70%` Rule-1 ceiling)
   - `EUL1` vs `DPRF1` (`52`-ch binary HGB + `68%` primary share): `86.57%` (`+16.57` pp over ceiling)
   - `DKRN1` vs `DPRF1` (LiDAR-free `47`-ch Kernel Head A + `62`-ch Elkan Core Head B + `48/28/24%` 3-Regime Net-Tversky): **`75.68%`** (`-10.89` pp lower than `EUL1`, passing all `83/83` peer blobs `<=53.37%`, all `8/8` `2026-10-26` sibling `.tif`s `<=55.89%`, and `B2` `44.05%`, yet still `+5.68` pp above `70%` vs `DPRF1`/`EUL1`!).
   - **Theorem-in-practice:** Any detector retaining a $\ge 50\%$-weighted full-stack `DPRF1` Head B inside the `68.2%` LiDAR zone will exceed `70%` 3-px overlap with `DPRF1`. Clearing `70%` requires **100% exclusion of the `DPRF1` head** (`HeadA47`-style architecture).
3. **Why exact-file C2ST flagged `DKRN1` (`AUC = 0.5773`, `holm_p = 0.0200`):**
   Per-fold C2ST AUCs are `[0.5906 (NW), 0.6632 (NE_LidarGapHeavy), 0.5143 (SW), 0.5413 (SE)]`. In the Great Basin, graded valley-floor wash roads (`road_m`), placer/lode claims (`claim_m`), and `block_2` survey boundaries follow major ephemeral D8 washes (`A \ge 10^5\text{ m}^2`). Residualizing only 2 of the 10 `DKRN1` channels while allocating `28%` (`10,543` dots) directly via unresidualized `m_hydro` concentrated dots along road-bearing bajada washes in `NE`. Future hydrologic lanes (`H24-DRAIN5R-PURE`) **must** apply fold-safe `NuisanceResidualizer` to **all** D8 channel-routing features and `m_hydro` before allocation.

---

## 6. Step-by-Step DrivenData Submission Guide & `[0, 1]` Range Error Fix

> **Current Authorization Status:** **`DO_NOT_SUBMIT`** across all files in this repository under `gems-selector-v2-literal-quota-fail-closed`. Follow the steps below **if and only if** the separate selector step explicitly authorizes a release after human verification of live DrivenData weekly quota and calibration-lattice policy.

1. **Always select the `-zeros.tif` file (or its single-GeoTIFF `-zeros.zip`), NEVER `-nan.tif` or an unchecked sibling `.tif`:**
   - Why `"Predicted values must be in range [0, 1]"` happened historically (and why `GEMSDOE30`'s `2026-10-26` file would trigger it again): IEEE-754 `NaN <= 1.0` evaluates to `False`, so any portal validator running whole-array `(arr >= 0.0) & (arr <= 1.0)` without masking `NaN` outside the active footprint rejects files with outside-footprint `NaN`s.
   - Every `-zeros.tif` written by `gems.submission.write_submission(..., outside="zero")` is verified across all `12,279,160` cells (`3730 × 3292`, single-band `float32`, `EPSG:32611`, affine `[100, 0, 243350, 0, -100, 4508550]`, `nodata = None`, `min = 0.0`, `max = 1.0`, `0` `NaN`/`Inf`).
2. **Verify exact SHA-256 and preflight JSON locally before touching the browser:**
   ```bash
   .venv/bin/python scripts/run_dprf1_lane.py --verify-recorded
   .venv/bin/python scripts/run_dkrn1_lane.py --verify-recorded
   ```
3. **Open the official portal manually (never automated):**
   - Sign in to [DrivenData DOE GEMS Competition](https://www.drivendata.org/competitions/306/competition-doe-gems/) -> **Submit**.
   - Check remaining weekly submission quota manually on the page (historical rules specify 3 submissions per rolling 7-day window).
4. **Upload the exact `.tif` (or single-file `.zip`) and paste its `<= 140`-character Note:**
   - Example recorded point-best note (`115` chars, if authorized by selector):
     `GEMS24 DPRF1 | 52ch stitched-OOF 2-regime submod | id 81849d67c8bf | HOLDOUT-DTI 0.16379 | research; DO NOT SUBMIT`
5. **Save an artifact-linked submission-page screenshot/receipt** before labeling any score `ORGANIZER-CONFIRMED`.

---

## 7. Trusted Source Verification & Irregularity Register

### 7.1 Trusted Primary Sources
- **Competition Reference Solution (DrivenData GitHub):** <https://github.com/drivendataorg/gems-prize-reference-solution/tree/aebe92f7c8a990f0e3443451b7a825d9afd6336b> — verifies `EPSG:32611` grid/transform conventions, single-band float32 GeoTIFF output without `nodata` sentinel, and Tversky $(\alpha=0.2, \beta=0.8)$ weighting.
- **Official Prize Rules PDF (DOE / NREL):** <https://docs.nlr.gov/docs/fy26osti/96647.pdf> — governs eligibility, weekly submission limits, and mandatory AI-assistance disclosure (§3.2).
- **USGS GeoDAWN Airborne Geophysics & Radiometrics (DOI `10.5066/P93LGLVQ`):** <https://www.sciencebase.gov/catalog/item/657e1d85d34e23d3533209f7> — documents magnetic (`tmi`, `tmi_rtp`, `tmi_up150`) and radiometric (`thk_ratio`, `uth_ratio`, `uk_ratio`) channels.
- **OpenEI GDR Submission 1391 (Great Basin INGENIOUS Project):** <https://gdr.openei.org/submissions/1391> — official public source for Quaternary fault attributes, sinter/travertine occurrences, 2 m temperature probes, and geothermometry points (used strictly via label-free `src/gems/gvc.py` / `data/external/gdr1391_points.npz`, never the forbidden `dist_known_fault_px` CSVs).
- **USGS 3D Elevation Program (3DEP):** <https://www.usgs.gov/3d-elevation-program/data-tools> — documents 1 m bare-earth LiDAR tile coverage and the `31.8%` acquisition gap across the Great Basin study footprint.
- **Methodological Foundations:**
  - Flint, J. J. (1974), *Stream gradient as a function of order, magnitude, and discharge*, Water Resources Research, 10(5), 969–973, <https://doi.org/10.1029/WR010i005p00969> (stream-power concavity scaling $\Omega \propto A^\theta S$).
  - Elkan, C. (2001), *The Foundations of Cost-Sensitive Learning*, IJCAI-01, pp. 973–978 (exact prior-odds Bayes posterior calibration under case-control subsampling).
  - Minoux, M. (1978), *Accelerated greedy algorithms for maximizing submodular set functions*, Lecture Notes in Control and Information Sciences, 7, 234–243, <https://doi.org/10.1007/BFb0006528> (lazy-greedy submodular maximization).
  - Lopez-Paz, D. & Oquab, M. (2017), *Revisiting Classifier Two-Sample Tests*, ICLR 2017, <https://arxiv.org/abs/1610.06545> (exact-file C2ST nuisance audit).

### 7.2 Irregularities Flagged & Resolved
1. **`IR-MISSING-ASSIGNED-PARAGRAPH`:** The standing prompt references *"the single method lane assigned to this repo below"* without attaching the lane paragraph; resolved transparently by executing the top `AGENTS.md` next-step queue (`H24-DRAIN5` + `H24-KERN6` -> `H24-DKRN1`).
2. **`IR-PROMPT-TOP-CONFLICT`:** Prompt text cites both `0.3195` and `0.4413` as top leaderboard scores without portal receipts; both are flagged `UNVERIFIED-OWNER-REPORT` and never treated as ground truth.
3. **`IR-GEMSDOE30-NAN-OUTSIDE`:** Fresh `2026-10-26` pixel audit caught `7,111,787` `NaN` values outside the footprint in `GEMSDOE30-geothermal-corridor-offcat-d3-20261026T160300Z.tif` (`whole_array_strict_0_1 = False`), flagging a portal range-error hazard.
4. **`IR-GEMSDOE31-APRON-COLLAPSE`:** Fresh `2026-10-26` pixel audit caught `69.19%` near-catalogue apron concentration (`only 7.52% > 2 km`) in `GEMSDOE31` `PGR31`, matching `GVC1`'s `0.0859` failure mode.
5. **`IR-VENT-QUARANTINE-PRESERVED`:** Concurrent `H24-VENT` remains quarantined (`DO NOT SUBMIT`) due to historical dummy C2ST/novelty fallbacks documented in `docs/review-20261026.md`.
6. **`IR-DKRN1-WASH-ROAD-C2ST`:** `H24-DKRN1`'s `28%` `m_hydro` D8 wash allocation flagged exact-file C2ST (`AUC = 0.5773`, Fold 2 `NE_LidarGapHeavy` `0.6632`) due to Great Basin valley-floor roads following major ephemeral washes; recorded honestly without retuning.
