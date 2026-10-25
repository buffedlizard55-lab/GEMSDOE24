# `H24-RSHG1` Findings, Nine-Site Synthesis & 3-Pass Verification — 2026-10-25

- **Date (UTC):** 2026-10-25
- **Branch:** `arena/fa1f8797-gemsdoe24`
- **Preregistration commit (frozen prior to run):** `a019e4e` (`knowledge/17_preregistered_RSHG1_2026-10-25.md`)
- **Primary GeoTIFF (zero-outside, strict `[0, 1]` all-finite):** `docs/downloads/gems24-rshg1-regime-hydro-hgb-20261025-98f69d77e868-zeros.tif`
  - **SHA-256:** `06d28182d9fea06d1d4ac3fc603bada748306e68350ebe432e3ff9f82fd3703e`
- **NaN-outside companion GeoTIFF:** `docs/downloads/gems24-rshg1-regime-hydro-hgb-20261025-98f69d77e868-nan.tif`
  - **SHA-256:** `1b9e6c1ca4278b1bc6d76138c264c7d68d80172b5be2c191a77e12689055290d`
- **JSON run card:** `evidence/rshg1_run_card_20261025.json` (mirrored at `docs/data/rshg1_run_card.json`)
- **Full experiment receipt:** `evidence/rshg1_experiment_20261025.json` (`1` of max `3` experiments used; `663.05 s` wall time; `3,488.8 MiB` peak RSS on 2 CPU cores)
- **Automated decision:** **`DOWNLOAD: YES · SUBMIT: NO` (`verdict: "negative"`, `ok_to_submit: false`, `submission_status: "DO_NOT_SUBMIT"`)** — determined automatically by `gems.preflight` and `scripts/run_rshg1_lane.py` with zero human-inspector fallback.

---

## 1. PhD Synthesis: Why `GEMSDOE32` (`H33-B2`) Scored Highest Among the Nine Priority Sites — and How to Surpass It

### 1.1 Provenance & Epistemic Status of Reported Leaderboard Numbers
Across the nine audited repositories (`GEMSDOE24, 25, 27, 28, 30, 31, 32, 33, 36`, `evidence/priority_review_20261025.json` and `registry/priority_rasters.json` covering 46 distinct footprint rasters plus 84 peer-review blobs):
1. **`0.2778` (`h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros`, published in `GEMSDOE32`):** Classified strictly as **`UNVERIFIED-OWNER-REPORT`**, **not** `ORGANIZER-CONFIRMED`, because no artifact-linked DrivenData submission-page screenshot/JSON receipt has been archived in git.
2. **`0.3195` vs. `0.4413` leader references:** Unverified conflicting task-statement snapshots from earlier user prompts. Under DrivenData Terms of Use, automated scraping of `drivendata.org` is prohibited, so no live leaderboard claim is asserted without an organizer receipt.

### 1.2 Exact Pixel-Level Mechanism of `GEMSDOE32` (`H33-B2`)
Byte-for-byte comparison across the nine sibling sites (`evidence/priority_review_20261025.json`) proves that `GEMSDOE32`'s `H33-B2` (`37,654` positive pixels inside the `5,167,373`-cell active footprint) introduced **zero new geological detections**:
- `GEMSDOE25` / `GEMSDOE30` reference `D2.8` (`44,090` Poisson-thinned dots on the multi-physics `H19-5` ridge surface) $\rightarrow$ `GEMSDOE31` `H27-4` (`40,199` dots after deleting `3,891` dots within $\le 1\text{ px} = 100\text{ m}$ of the public fault catalogue) $\rightarrow$ `GEMSDOE32` `H33-B2` (`37,654` dots after deleting the remaining `2,545` dots at $1 < d_{\text{cat}} \le 2\text{ px} = 200\text{ m}$; `6,436` total dots deleted relative to `D2.8`, **0 dots added**, Jaccard `0.8540` vs. `D2.8` and `0.9367` vs. `H27-4`).
- By contrast, `GEMSDOE36` (`47,764` dots) contains all `37,654` `H33-B2` dots plus `10,110` broader lower-precision dots, while `GEMSDOE27` (`59,075` dots) and `GEMSDOE30` (`80,000`–`85,526` dots) roughly doubled emitted false-positive mass (`F`).

Under the competition Distance-Tolerant IoU (`DTI`) with Asymmetric Tversky weights ($\alpha = 0.2$, $\beta = 0.8$) and $300\text{ m}$ (`3 px`) linear distance decay $K_{300}(d) = \max(0, 1 - d / 300\text{ m})$:
$$\mathrm{DTI} = \frac{\mathrm{TP}_w}{(1 - \beta)\,\mathrm{TP}_w + \alpha\,\mathrm{FP}_w + \beta\,\mathrm{FN}_w} = \frac{\mathrm{TP}_w}{\mathrm{TP}_w + 0.2\,\mathrm{FP}_w + 0.8\,\mathrm{FN}_w}.$$
Two distinct mechanisms explain why `H33-B2` outperformed every sibling variant:
1. **Supervised multi-physics skeleton + spacing-4 Poisson thinning (`D2.8`):** Because any single binary dot illuminates a $7 \times 7$ (`600 m × 600 m`) triangular footprint via $\max_q K_{300}(\|x - q\|)$, thinning dense connected ridges to one dot every $\sim 4\text{ px}$ cuts $\mathrm{FP}_w$ by $\sim 3\times$ while preserving $>92\%$ of weighted recall $\mathrm{TP}_w$. Unsupervised single-physics heuristics (`MTR1` `0.06441`, `CON` `0.06446`, `H-UNIQUE-03` `0.05384`, `ASPC` `0.08553`, `SAHG1` `0.09672`) lose 35%–140% in `HOLDOUT-DTI` relative to supervised multi-physics fusion (`~0.130`) because Basin and Range faults express across complementary regimes (3DEP scarps on range fronts, gravity/magnetic steps beneath alluvial bajadas, Th-normalized K alteration in damage zones).
2. **200 m visible-catalogue flank clearance (`-6,436` dots):** Multi-scale Gaussian/curvature features blur true fault scarps across $100\text{–}200\text{ m}$ flanks around already-mapped USGS/INGENIOUS catalogue traces. Where hidden test segments represent *unmapped blind/range-front structures* rather than parallel strands $100\text{–}200\text{ m}$ off existing lines, dots at $d_{\text{cat}} \le 200\text{ m}$ incur pure $0.2\,\Delta\mathrm{FP}_w$ penalty with negligible $\Delta\mathrm{TP}_w$. Removing `6,436` flank dots saves up to $0.2 \times 6{,}436 \approx 1{,}287$ denominator units.

### 1.3 Exact Code Distinction Between `SegmentHoldout` and Full-Footprint Inference
In `src/gems/holdout.py` (`lines 422–432`), `SegmentHoldout` constructs `collar = binary_dilation(valid, iterations=15)` (`1.5 km`) and hides every connected fault component intersecting `valid | collar`. Consequently, `fold["visible"]` is identically zero everywhere inside `valid`, meaning $\operatorname{dist}(\text{visible}) > 15\text{ px}$ for every cell scored in `SegmentHoldout`. At full-footprint inference, however, all `60,988` public catalogue pixels lie inside the active footprint. Using the **exact same** `emit_rshg1_dots(..., visible_mask=visible, clearance_px=2.0)` operator across both holdout and live inference ensures zero discrepancy in code while clearing `100–200 m` smoothed flanks around known faults in the full-footprint GeoTIFF (`0` emitted dots within $\le 200\text{ m}$ of `labels.tif`).

### 1.4 Can We Beat `GEMSDOE32` (`H33-B2`), and How?
**Yes — in principle — only by adding genuine off-catalogue fault detections in regimes where `H19-5`/`H33-B2` was blind or confounded, not by further pruning `H19-5`.** Specifically, `H19-5` (and `oof_multiphysics_hgb_d3`) suffered two structural blind spots documented in `knowledge/13_SAHG1_findings_2026-10-25.md` and `knowledge/14_data_readiness_and_next_gate_2026-10-25.md`:
1. **31.8% 3DEP LiDAR gap blackout:** `oof_multiphysics_hgb_d3` restricted `eligible` strictly to the `3,522,084` LiDAR-covered cells (`68.16%` of footprint), emitting zero predictions across the `1,645,289` footprint cells (`31.84%`) lacking 3DEP LiDAR tiles.
2. **Severe C2ST accessibility/claim confounding:** Both `H19-5` (`AUC = 0.5630`, `Holm p = 0.030`) and `H24-SAHG1` (`AUC = 0.5826`, `Holm p = 0.020`) failed the `gems.c2s2` spatial-block nuisance audit (`claim_m` single-feature AUC `0.585`), whereas the true fault catalogue sits at chance (`AUC = 0.4958`).

---

## 2. Execution of Prior-Session Next Steps & `H24-RSHG1` Results

Prior to running `H24-RSHG1`, we completed every pending engineering and audit item from PRs #16, #17, #18, and #19:
1. Restored `data/training_features.tif` (`SHA-256: 4371c82ec0b9aaad3be5fbdfba36db13ba6ee1bbeffef6959dc554ebae73fb5a`), `data/prepared/features.npy` (`SHA-256: a4ca25b206923639140dc38910e6a41052b11a5a26d272a571316379557545a5`), `data/access/confounds.npz`, all 46 priority registry rasters (`data/research/priority_registry/`), and all 84 peer-review rasters (`data/research/peer_review/`).
2. Verified frozen `evaluate_holdout.py --verify-recorded` and `run_sahg1_lane.py --verify-recorded` receipts (`verified: true`), and audited `PR #18`'s `H24-CON` raster against the restored 46-raster registry (`method_lane_passed = True`, `max_overlap = 0.3108`, `max_|rho| = 0.0502`, `literal_all_entries_passed = False` on `registry-039`).
3. Audited all 19 bands of `training_features.tif` (stride-sampled with zero label access), discovering that Band 6 (`tc`, `[3.32, 42.72]`) is radiometric **Total Count** exposure rate rather than magnetic tilt angle, and computing true potential-field Miller & Singh (1994) tilt-derivative zero-contour sharpness directly from `rtp_magnetic_anomaly` (`mag_tilt_zero`) and `cba_gravity` (`grav_tilt_zero`) plus isotropic 100 m DEM Hessian ridge strength (`dem_hess_ridge`) across 99.64% of the footprint.
4. Preregistered four ranked hypotheses in `knowledge/17_preregistered_RSHG1_2026-10-25.md` (committed at `a019e4e`) and executed Rank 1 (`H24-RSHG1`: 42-channel `NaN`-routed multi-physics + strike-hydro-geomorph HGB ensemble with fold-local `NanPreservingResidualizer` and `RegimeNuisanceCalibrator`) in a single streaming pass (`663.05 s`, peak RSS `3,488.8 MiB`).

### 2.1 `HOLDOUT-DTI` Results Across All 2026-10-25 Lanes (Not Leaderboard Scores)

All scores below are **`HOLDOUT-DTI`** (`60,988` withheld positive pixels across whole hidden connected fault segments, `1,999` 10 km spatial block-bootstrap draws). **None are `ORGANIZER-CONFIRMED` leaderboard scores.**

| Candidate / Arm | Evaluator | Pooled `HOLDOUT-DTI` | 95% Block-Bootstrap CI | `NW` | `NE_LidarGapHeavy` | `SW` | `SE` | Exact-File C2ST AUC (Holm *p*) |
|---|---|---:|---|---:|---:|---:|---:|---|
| **`H24-RSHG1` Ablation B (`calibrated_pointwise_b0`: 42-ch residualized + calibrated, pointwise Poisson)** | `gems-segment-pooled-v1` | **`0.13137`** | `[0.11870, 0.14504]` | `0.13355` | **`0.17365`** | `0.08296` | **`0.15374`** | diagnostic surface |
| Reconstructed `oof_multiphysics_hgb_d3` baseline (27-ch, LiDAR-only, unresidualized) | `gems-segment-pooled-v1` | `0.13000` | `[0.11565, 0.14396]` | `0.14613` | `0.13464` | `0.10490` | `0.14558` | OOF reference |
| `H24-RSHG1` Ablation A (`uncalibrated_pointwise_b0`: 42-ch `NaN`-routed, no residualizer/calibrator) | `gems-segment-pooled-v1` | `0.12976` | `[0.11720, 0.14265]` | `0.12614` | `0.16000` | `0.10190` | `0.14122` | diagnostic surface |
| **Locked Primary `H24-RSHG1` (`gems24-rshg1-...-zeros.tif`, with $\sqrt{p \cdot (K_{300}*p)}$)** | `gems-segment-pooled-v1` | **`0.12899`** | `[0.11578, 0.14305]` | `0.13427` | **`0.17285`** | `0.07993` | **`0.14902`** | **`0.5088` (*p* = `0.700`, PASS)** |
| `H24-SAHG1` Strike-Hydro-Geomorph (`PR #16`) | `gems-segment-pooled-v1` | `0.09672` | `[0.08657, 0.10703]` | `0.09370` | `0.07725` | `0.08826` | `0.11798` | `0.5826` (*p* = `0.020`, FAIL) |
| `H24-CON` Clay-Cap Conductivity Saddle (`PR #18`) | `gems-segment-pooled-v1` | `0.06446` | `[0.05841, 0.07030]` | — | — | — | — | not run |
| `MTR1` Paired Magnetic Trough (`PR #11`) | `gems-segment-pooled-v1` | `0.06441` | `[0.05830, 0.07112]` | — | — | — | — | not run |
| `H-UNIQUE-03` Fault-Guided K Modulation (`PR #19`) | `gems-segment-pooled-v1` | `0.05384` | `[0.03894, 0.06866]` | — | — | — | — | not run |
| **Locked Primary `H24-RSHG1` on 3.0 km Bridge Protocol** | `segment-hide-recover-pooled-v1` | **`0.13112`** | `[0.11373, 0.14999]` | `0.12358` | **`0.17787`** | `0.09749` | `0.13275` | **`0.5088` (*p* = `0.700`, PASS)** |
| `H24-SAHG1` on 3.0 km Bridge Protocol (`PR #16`) | `segment-hide-recover-pooled-v1` | `0.09655` | `[0.08270, 0.10976]` | — | — | — | — | `0.5826` (FAIL) |
| `ASPC` Antislope Scarp Curvature (`PR #10`) | `segment-hide-recover-pooled-v1` | `0.08553` | `[0.07257, 0.09876]` | — | — | — | — | not run |

### 2.2 Paired Mechanism Attribution (What Worked and What Hurt)
1. **Massive LiDAR-gap recovery (`NE_LidarGapHeavy` `+0.03821` to `+0.03901`):** Unlocking the 31.84% LiDAR gap via native tree `NaN` routing over DEM-Hessian ridge, gravity/magnetic tilt zero-contour sharpness, basement horizontal-gradient step, and Th-normalized K alteration raised `NE_LidarGapHeavy` `HOLDOUT-DTI` from `0.13464` (`oof_multiphysics_hgb_d3`) to **`0.16000`** (`Ablation A`), **`0.17285`** (`Primary H24-RSHG1`), and **`0.17365`** (`Ablation B`) — a **+28.4% to +29.0% relative gain** in the LiDAR-gap-dominated quadrant!
2. **`NaN`-preserving nuisance residualization + regime calibration (`+0.00161` gain in `Ablation B` over `Ablation A`):** Unlike legacy `H24-2A` (which imputed missing values and lost `-0.0163` dense DTI when residualizing), fitting `NanPreservingResidualizer` strictly on finite fold-training rows plus `RegimeNuisanceCalibrator` **increased** pointwise `HOLDOUT-DTI` from `0.12976` (`Ablation A`) to **`0.13137`** (`Ablation B`, the highest `HOLDOUT-DTI` recorded in `GEMSDOE24`, improving 3 of 4 folds: `NW +0.00741`, `NE +0.01365`, `SE +0.01252`), while simultaneously reducing exact-file C2ST AUC to **`0.5088`** (`Holm p = 0.700`, `claim_m` single-feature AUC `0.5071` vs. `0.5850` in `H19-5`).
3. **Why locked `Primary H24-RSHG1` (`0.12899`) statistically tied `oof_multiphysics_hgb_d3` (`0.13000`, paired $\Delta = -0.00100$, 95% CI `[-0.01650, +0.01387]`):**
   - **Finding A — Redundant `7×7` kernel smoothing (`-0.00238`, 95% CI `[-0.00462, -0.00018]`):** Convolving the already multi-scale tree probability surface with $K_{300}$ via $\sqrt{p \cdot (K_{300}*p)}$ slightly broadened fault-zone ridges relative to pointwise `priority_poisson` (`0.13137` $\rightarrow$ `0.12899`). Because `Primary H24-RSHG1` was locked before seeing holdout (`a019e4e`), we **do not** swap the GeoTIFF post-hoc to `Ablation B`.
   - **Finding B — Uniform vs. terrain-conditioned LiDAR-gap tail matching in `SW` (`0.10190` $\rightarrow$ `0.08296`):** In `NE_LidarGapHeavy`, missing 3DEP LiDAR tiles cover steep faulted mountain ranges (`+0.01365` calibration gain). In `SW`, 3DEP LiDAR covers the faulted ranges while `~has_lidar` falls predominantly on flat, aseismic basin-floor/border cells; matching `p99(~has_lidar) == p99(has_lidar)` fold-globally therefore over-allocated dots into `SW`'s flat LiDAR-gap floor. Conditioning the LiDAR-gap tail match on regional topographic relief (`det_local_relief`) will retain the `+0.039` `NE` gain without the `SW` drag.

### 2.3 Two-Polarity Leakage Canary & Exact-File C2ST Nuisance Audit
- **Two-polarity single-feature leakage canary (`gems.holdout.feature_leakage_canary`):** **PASSED (`42/42` features + calibrated OOF surface)**. Every feature's pooled raw AUC lies inside `[0.4007, 0.5993]` (worst single feature: `det_local_relief` raw `AUC = 0.4007`, symmetric `0.5993`, far inside `[0.10, 0.90]`); OOF calibrated surface `AUC = 0.6400` (`< 0.90`).
- **Exact-file C2ST accessibility/acquisition audit (`gems.c2s2.audit_prediction_mask`):** **PASSED (`strict_gate_passed = True`)**.
  - Observed out-of-block AUC distinguishing `H24-RSHG1` (`37,722` emitted dots) from footprint background using `(road_m, claim_m, block_1..block_4)`: **`0.5088`** (`null_mean = 0.4995`, `null_p95 = 0.5223`, `margin_vs_p95 = -0.0135`, raw `p = 0.350`, `Holm p = 0.700`).
  - Single-confound AUCs: `road_m = 0.5200`, `claim_m = 0.5071`, `block_1 = 0.4922`, `block_2 = 0.4863`, `block_3 = 0.5158`, `block_4 = 0.4886` (vs. `labels.tif` joint `AUC = 0.4958`). This completely resolves the nuisance failure identified in `H24-SAHG1` (`0.5826`) and `H19-5` (`0.5630`).

### 2.4 Full-Cache Registry & Peer Novelty Discovery (Independent Physical Convergence)
Compared against all **48** competing method rasters (`46` priority registry method lanes + `CON` + `ASPC`), **83** peer-review blobs, **`H-UNIQUE-03`**, and the **2** retained calibration controls (`registry-039` spacing-5 lattice, `registry-044` zero placeholder):
- **Copied prior submission pixels:** **`0`** (`SHA-256` distinct from every compared raster; pre-placement surface `max |ρ| = 0.4518 ≤ 0.90` **PASS**; vs. `H-UNIQUE-03`: 3-px overlap `0.0885`, `ρ = -0.0031`; vs. `H24-CON`: distinct).
- **Directional `≤ 3 px` (`300 m`) dot overlap:** **`method_lane_passed = False`** (`max_overlap = 0.7269 > 0.70`) and **`literal_all_entries_passed = False`** (`0.9982` against `registry-039` spacing-5 calibration lattice):
  - `0.7269` (`72.69%`) of `H24-RSHG1`'s independently predicted off-catalogue dots fall within `300 m` of `registry-041` (`gems10-h25-ctx-ridge`, a `174,232`-pixel thick supervised ridge map in `inputs/calibration/`), and `0.7233` (`72.33%`) fall within `300 m` of `registry-016` (`gems28-h37-1-probe-union-pool-r1`, `38,545` px).
  - **Scientific interpretation:** Weak unsupervised heuristics (`H-UNIQUE-03` `0.054`, `MTR1` `0.064`, `CON` `0.064`, `SAHG1` `0.097`) stayed below `0.48` method-lane overlap largely because >60% of their dots fired on off-fault noise or alteration halos. Once an independent 42-channel supervised detector reaches `HOLDOUT-DTI ~ 0.13` with `>200 m` public-catalogue flank clearance, >72% of its predicted unmapped range-front scarps naturally co-locate within `300 m` of the same physical Great Basin fault scarps detected by prior supervised ensembles (`gems10` / `gems28`) — even with `max |ρ| = 0.4518` and zero shared prediction inputs. Under Rule 1, we record this convergence faithfully and hold `ok_to_submit = False`.

---

## 3. Verified Official Sources, AI Disclosure & Irregularities Logged

### 3.1 Trusted Sources Inspected / Linked for Manual Review
- **Organizer Reference Solution (verified via GitHub):** <https://github.com/drivendataorg/gems-prize-reference-solution/tree/aebe92f7c8a990f0e3443451b7a825d9afd6336b> — confirms fault-geometry target, Asymmetric Tversky weights (`0.2 / 0.8`), and single-band `EPSG:32611` `3730 × 3292` output template.
- **USGS GeoDAWN (`DOI: 10.5066/P93LGLVQ`):** <https://www.sciencebase.gov/catalog/item/657e1d85d34e23d3533209f7> — cached official ReadMe verified for magnetic/radiometric channel definitions and UTM Zone 11N gridding.
- **USGS 3DEP & SGMC:** <https://www.usgs.gov/3d-elevation-program> and <https://www.usgs.gov/programs/national-cooperative-geologic-mapping-program/science/state-geologic-map-compilation-sgmc> — provenance for cached `lidar_scarp_features_u8.tif` and `derived_sgmc_faults_100m_u8.tif` (used only as an audit/metadata reference; never used as a label-leaking input).
- **DOE GDR INGENIOUS (`Submission 1391`):** <https://gdr.openei.org/submissions/1391> — official Great Basin play-fairway context.
- **DrivenData Competition Pages & Prize Rules (manual review only; never scraped):** <https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/>, <https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/>, and <https://docs.nlr.gov/docs/fy26osti/96647.pdf>.
- **AI Tool Disclosure (Official Rules §3.2):** Maintained in `AI_DISCLOSURE.md`; Arena.ai Agent Mode assisted code authoring, preregistered holdout evaluation, exact-file validation, and documentation; zero automated DrivenData requests or uploads were made.

### 3.2 Irregularities Logged During This Session
1. **`training_features.tif` Band 6 (`tc`) semantics & float32 boundary sentinels:** Direct band inspection showed `tc` spans `[+3.32, +42.72]` (radiometric Total Count exposure rate, not signed magnetic tilt angle), and 5 bands contain `-3.4028235e+38` sentinels on `3,061` footprint-edge cells (`0.06%`). `gems.rshg1` sanitizes `|x| > 1e30` to `NaN` before computing true potential-field tilt derivatives from `rtp_magnetic_anomaly` and `cba_gravity`.
2. **Manual HTML drift in PR #18 (`H24-CON`) and PR #19 (`H-UNIQUE-03`):** Both sibling PRs edited `index.html`, `docs/index.html`, and `docs/executive-summary.html` directly without wiring their packets into `scripts/site_packets.py` / `scripts/build_site.py`. Running `scripts/build_site.py` without fixing `site_packets.py` would have erased both packets. We wired `CON`, `H-UNIQUE-03`, and `RSHG1` deterministically into `scripts/site_packets.py` and `scripts/build_site.py` with SHA-256 verification.
3. **Open stale PR #7 (`arena/01a0fd2e-gemsdoe24`):** Left untouched per governance (`knowledge/08_parallel_session_pr7_2026-10-02.md`).

---

## 4. Mandatory Three-Pass Review & Remaining Work / Next Steps

### 4.1 Three-Pass Verification Summary
1. **Pass 1 — Scientific, Mathematical & Leakage Integrity:** Verified `SegmentHoldout` component hiding (`1.5 km` and `3.0 km` collars), train-only fitting of `NanPreservingResidualizer`, `RegimeNuisanceCalibrator`, and fold-local HGB/ET models, two-polarity single-feature leakage canary (`42/42` PASS), exact-file C2ST (`AUC = 0.5088`, `Holm p = 0.700` PASS), and strict adherence to preregistration `a019e4e` (retaining `Primary H24-RSHG1` `0.12899` rather than post-hoc swapping to `Ablation B` `0.13137`).
2. **Pass 2 — Exact-File GeoTIFF, Checksum & Gate Determinism:** Verified `gems24-rshg1-regime-hydro-hgb-20261025-98f69d77e868-zeros.tif` (`3730 × 3292`, `float32`, `EPSG:32611`, affine `[100, 0, 243350, 0, -100, 4508550]`, `0` NaN/Inf, global min `0.0`, global max `1.0`, `37,722` active footprint dots, `0` outside-footprint positives, `89`-char note), `-nan.tif` companion, `preflight_submission.py` (`SUBMISSION: DO_NOT_SUBMIT`), and `--verify-recorded` across `evaluate_holdout.py`, `run_sahg1_lane.py`, and `run_rshg1_lane.py`.
3. **Pass 3 — Site Build, Link Integrity, Test Suite & Snapshot Hygiene:** Rebuilt all GitHub Pages HTML/JSON/README outputs deterministically via `scripts/build_site.py`, verified zero broken links (`BeautifulSoup` check across all 5 HTML pages), passed `pytest`, `ruff check`, `compileall`, `node --check`, and `git diff --check`, and scheduled cleanup of gitignored bulk caches (`data/training_features.tif`, `data/prepared/`, `data/research/`, `data/access/`) immediately after final PR merge and verification.

### 4.2 Concrete Next Steps for the Next Session
1. **Pointwise + Terrain-Conditioned LiDAR-Gap Calibration (`H24-RSHG2`):** Drop the post-hoc $\sqrt{p \cdot (K_{300}*p)}$ convolution (recovering `Ablation B`'s `+0.00238` advantage at `0.13137`) and condition `RegimeNuisanceCalibrator`'s `~has_lidar` tail match on regional relief (`det_local_relief`) so flat `SW` basin-floor LiDAR gaps are not boosted to mountain-front fault density while retaining `NE_LidarGapHeavy`'s `+0.039` gain.
2. **Explicit Multi-Lane Selector Policy for Supervised Convergence:** Establish an explicit selector rule distinguishing (a) prohibited copying/post-processing of prior submissions from (b) independent physical convergence (`|ρ| ≤ 0.50`, zero shared prediction inputs) onto major range-front scarps already covered by `174k`-pixel historical ridge maps (`registry-041`), alongside the already-separated `registry-039` spacing-5 calibration lattice.
3. **Hypothesis 2 (`H24-DRAIN1` Topographic Drainage-Network Deflection):** Implement multi-scale D8 stream-channel deflection + knickpoint alignment on raw `elevation` (`100%` footprint coverage) as an orthogonal geomorphic channel to pair with `H24-RSHG2`.
