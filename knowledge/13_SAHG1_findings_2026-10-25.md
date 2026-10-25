# H24-SAHG1 findings, unified OOF benchmark, and three-pass review — 2026-10-25

## 1. Executive decision and deliverable summary

**DOWNLOAD: YES (for research/audit). SUBMIT: NO — automated NEGATIVE verdict, no human-inspector fallback.**

This session executed the explicit **Next steps** left by the two preceding 2026-10-25 parallel sessions (`PR #10` ASPC and `PR #11` MTR1) while preserving 100% of their frozen receipts, code, tests, and downloadable artifacts:

1. **Unique GeoTIFF generated from physical feature layers (no copied submission pixels):**
   - Primary zero-outside GeoTIFF: [`gems24-sahg1-strike-hydro-geomorph-20261025-13d01f28d5db-zeros.tif`](../docs/downloads/gems24-sahg1-strike-hydro-geomorph-20261025-13d01f28d5db-zeros.tif) (`SHA-256: 8d5a5f99245fecf11cea72c33c41bad800cd0e41215744d7dd5d9ac6df673f11`).
   - Template-convention NaN-outside twin: [`gems24-sahg1-strike-hydro-geomorph-20261025-13d01f28d5db-nan.tif`](../docs/downloads/gems24-sahg1-strike-hydro-geomorph-20261025-13d01f28d5db-nan.tif) (`SHA-256: 80f893de18ac9a83696a572e7d0e92e93d33057dd68491807d487acfb7a7cd25`).
   - Format validation (`scripts/submission_writer.py` / `gems.submission.check_variants`): single-band `float32`, `EPSG:32611`, shape `3730 × 3292`, affine `(100, 0, 243350, 0, -100, 4508550)`, **0 NaN/Inf inside the 5,167,373-pixel footprint**, values strictly in `[0.0, 1.0]`, **37,722** positive dots (`ok_to_upload: false`, `submission_authorized: false`).
   - Short submission note (**117 characters**, $\le 140$ cap):
     `GEMS24 SAHG1 | strike LiDAR scarp x stable-Th K/U + basement step | research only; DO NOT SUBMIT | id 13d01f28d5db`
   - Complete frozen receipts: [`evidence/sahg1_experiment_20261025.json`](../evidence/sahg1_experiment_20261025.json) and [`evidence/sahg1_run_card_20261025.json`](../evidence/sahg1_run_card_20261025.json).

2. **Why `H24-SAHG1` is a scientific step forward on `HOLDOUT-DTI` yet remains `SUBMIT: NO`:**
   - **Beats both prior 2026-10-25 physical operators and its own geomorphic ablation on both segment-pooled evaluators:**
     - On `gems-segment-pooled-v1` (60,988 withheld positives, 1.5 km collar, 10 km block bootstrap, 1,999 resamples): `H24-SAHG1` achieves **HOLDOUT-DTI `0.09672`** (95% CI **`[0.08657, 0.10703]`**), outperforming its geomorphic-only ablation `G_0` (**`0.08659`**, 95% CI `[0.07757, 0.09514]`, paired gain **`+0.01012`**, 95% CI **`[+0.00372, +0.01711]`**) and outperforming recorded `MTR1` (**`0.06441`**, 95% CI `[0.05830, 0.07112]`, gain **`+0.03230`** / `+50.2%`).
     - On `segment-hide-recover-pooled-v1` (60,988 withheld positives, 3.0 km buffer, 20 km tile bootstrap, 1,000 resamples, 37,654 dots): `H24-SAHG1` achieves **HOLDOUT-DTI `0.09655`** (95% CI **`[0.08270, 0.10976]`**), outperforming recorded `ASPC` (**`0.08553`**, 95% CI `[0.07440, 0.09648]`, gain **`+0.01102`** / `+12.9%`) and recorded `ASPC` control (**`0.06836`**, 95% CI `[0.05679, 0.08039]`, gain **`+0.02819`** / `+41.2%`).
   - **Does NOT beat the newly reconstructed same-protocol OOF multi-physics baseline (`oof_multiphysics_hgb_d3`):**
     - Reconstructing a leakage-free out-of-fold `HistGradientBoostingClassifier` across the 27 prepared physical/LiDAR/DEM channels (`data/prepared/features.npy`) trained strictly on `fold["train"]` of `SegmentHoldout` and emitted with identical `priority_poisson(..., min_dist=3)` budget yields **HOLDOUT-DTI `0.13000`** (95% CI **`[0.11565, 0.14396]`**). Because `H24-SAHG1` (`0.09672`) trails `oof_multiphysics_hgb_d3` (`0.13000`, paired delta **`-0.03328`**, 95% CI **`[-0.04658, -0.02062]`**), it does not beat the current holdout best and must not consume a weekly submission slot.
   - **Prospective novelty gate vs. literal calibration-lattice veto:**
     - Using `novelty.compare_prospective_registry`, `H24-SAHG1` passes against **all 46 competing method rasters** (44 method rasters in `priority_rasters.json` plus `ASPC` and `MTR1`: max surface $|\rho| = 0.38159 \le 0.90$, max dot $|\rho| = 0.30210 \le 0.90$, max 3-px dot overlap **`0.47683` $\le 0.70$**) and against **all 83 competition-grid blobs** in `peer_rasters_20261025.json` (max 3-px dot overlap **`0.45936` $\le 0.70$**).
     - When the synthetic uniform spacing-5 calibration lattice (`registry-039`, `13gems_20261001_r13-lattice-s5_v2_nan-outside.tif`, which covers 99.87% of the footprint within 3 px) is included as a literal method comparator, overlap is `1.0` (`literal_all_entries_passed: false`). Both flags are reported transparently without deleting `registry-039`.
   - **Exact-file C2ST nuisance audit (`gems.c2s2`):**
     - Training labels audit at held-out AUC **`0.49119`** (Holm $p = 0.620$, unassociated with roads/claims/blocks), whereas `H24-SAHG1` audits at held-out AUC **`0.58259`** (null p95 `0.53204`, margin `+0.05054`, Holm $p = 0.020$, `strict_gate_passed: false`), reflecting range-front correlation with roads, historic mining claims, and latitude-band acquisition blocks.

---

## 2. Unified cross-protocol holdout comparison table

All values below are **HOLDOUT-DTI** computed on the 60,988 withheld positive catalogue pixels across the four spatial quadrants (`NW`, `NE_LidarGapHeavy`, `SW`, `SE`) with whole 8-connected components withheld globally, visible catalogue pixels masked exactly (`~fold["visible"]`), and pooled Tversky components ($\alpha = 0.2$, $\beta = 0.8$, 300 m triangular kernel). None is an `ORGANIZER-CONFIRMED` leaderboard score.

| Candidate / Arm | Evaluator version | Training buffer / CI design | Emitted dots (full / pooled) | Pooled HOLDOUT-DTI | 95% Bootstrap CI | Status / comparison note |
|---|---|---|---:|---:|---|---|
| **Reconstructed OOF Multi-Physics Baseline (`oof_multiphysics_hgb_d3`)** | `gems-segment-pooled-v1` | 1.5 km collar; 10 km block bootstrap (1,999 draws) | 37,722 | **0.13000** | `[0.11565, 0.14396]` | Leakage-free fold-local HGB on 27 prepared physical/LiDAR/DEM channels (Next Step 2 benchmark) |
| **`H24-SAHG1` Candidate (this session)** | `gems-segment-pooled-v1` | 1.5 km collar; 10 km block bootstrap (1,999 draws) | 37,722 | **0.09672** | `[0.08657, 0.10703]` | Beats `G_0` ablation by `+0.01012` (`[+0.00372, +0.01711]`) and `MTR1` by `+0.03230`; trails `oof_multiphysics_hgb_d3` by `-0.03328` |
| **`H24-SAHG1` Geomorphic-Only Ablation (`geomorphic_core_g0`)** | `gems-segment-pooled-v1` | 1.5 km collar; 10 km block bootstrap (1,999 draws) | 37,722 | **0.08659** | `[0.07757, 0.09514]` | Pointwise antislope paired-curvature scarp on `SAHG1`'s eroded 9×9 support mask |
| **Recorded `MTR1` Candidate (PR #11)** | `gems-segment-pooled-v1` | 1.5 km collar; 10 km block bootstrap (1,999 draws) | 37,722 | **0.06441** | `[0.05830, 0.07112]` | Paired signed RTP magnetic trough + contractor Th/K depletion (terrain-free) |
| **Recorded `MTR1` Magnetic-Only Ablation (PR #11)** | `gems-segment-pooled-v1` | 1.5 km collar; 10 km block bootstrap (1,999 draws) | 37,722 | **0.06166** | `[0.05571, 0.06827]` | Paired signed RTP magnetic trough only |
| **`H24-SAHG1` Candidate (bridge evaluation)** | `segment-hide-recover-pooled-v1` | 3.0 km buffer; 20 km tile bootstrap (1,000 draws) | 37,654 | **0.09655** | `[0.08270, 0.10976]` | Beats recorded `ASPC` (`0.08553`) by `+0.01102` and `ASPC` control (`0.06836`) by `+0.02819` |
| **Recorded `ASPC` Candidate (PR #10)** | `segment-hide-recover-pooled-v1` | 3.0 km buffer; 20 km tile bootstrap (1,000 draws) | 37,654 | **0.08553** | `[0.07440, 0.09648]` | Pointwise LiDAR antislope paired-curvature scarp (provisional negative lane) |
| **Recorded `ASPC` Scarp Control (PR #10)** | `segment-hide-recover-pooled-v1` | 3.0 km buffer; 20 km tile bootstrap (1,000 draws) | 37,654 | **0.06836** | `[0.05679, 0.08039]` | Fixed LiDAR `step_max / (step_max + 0.05)` control |

---

## 3. Leakage canaries, novelty diagnostics, and exact-file C2ST nuisance audit

### Leakage canaries (`SegmentHoldout.canary`, threshold `0.90` / `0.10`)
All **29** raw input channels and derived surfaces (`lidar_upface_max`, `lidar_downface_max`, `lidar_cross_max`, `lidar_step_max`, `lidar_lapneg_max`, `lidar_lappos_max`, `lidar_coh100`, `lidar_valid`, `lidar_strike`, `rad_K`, `rad_Th`, `rad_U`, `ext_ThK`, `ext_UTh`, `geophys_det_elev`, `geophys_det_elev_slope`, `geophys_iso_grav_anom_hg`, `geophys_tmi_hg`, `geophys_depth_to_base_surf`, `geophys_geod_dilaterate`, `geophys_geod_shearrate`, `support_mask`, `geomorphic_core_g0`, `strike_scarp_g_strike`, `saturating_scarp_g_sat`, `radiometric_alteration_r_alt`, `basement_step_b_step`, `hydrothermal_conduit_h`, and `candidate`) were tested independently across all 4 folds (116 fold-feature tests). Pooled diagnostic AUCs ranged from **`0.48394`** (`rad_U`) to **`0.59496`** (`geophys_det_elev_slope`), with `candidate` at **`0.57983`** — well inside `[0.10, 0.90]`.

### Prospective novelty vs. registry (`src/gems/novelty.py`)
- **46 competing method rasters** (`44` method rasters in `registry/priority_rasters.json` + `ASPC` + `MTR1`):
  - Pre-placement surface max $|\rho|$: **`0.38159`** (vs. `ASPC`, well below `0.90`).
  - Final-dot max $|\rho|$: **`0.30210`** (well below `0.90`).
  - Final-dot max 3-px directional overlap: **`0.47683`** (`47.68%` vs. `ASPC`, well below `0.70` — **`method_lane_passed: true`**).
- **83 competition-grid blobs** in `registry/peer_rasters_20261025.json`:
  - Max surface $|\rho|$: **`0.09725`**; max dot $|\rho|$: **`0.04457`**; max 3-px directional overlap: **`0.45936`** (`45.94%` $\le 0.70$ — **`passed: true`**).
- **2 synthetic calibration controls** in `registry/priority_rasters.json`:
  - `registry-039` (`inputs/calibration/13gems_20261001_r13-lattice-s5_v2_nan-outside.tif`, spacing-5 uniform lattice): 3-px overlap is **`1.0`** (`literal_all_entries_passed: false`) because every interior pixel of the 100 m grid lies within $\sqrt{8} \approx 2.83 \le 3\text{ px}$ of a spacing-5 lattice node.
  - `registry-044` (`inputs/calibration/gemsdoe9-PLACEHOLDER-2314b599.tif`, all-zero placeholder): correlation `null`, overlap `0.0`.

### Exact-file C2ST nuisance audit (`gems.c2s2`, Lopez-Paz & Oquab ICLR 2017)
- Using only buffered Census road/trail distance (`road_m`), BLM closed mining-claim distance (`claim_m`), and the four derived GeoDAWN acquisition blocks (`block_1..4`, labeled `derived_audited_not_official_coordinates`), 199 grouped 10 km block label swaps (99 per test, 4 spatial folds):
  - **Training labels (`labels_first`):** Held-out AUC **`0.49119`**, null p95 `0.53139`, margin `-0.04020`, Holm $p = 0.620$ (unassociated).
  - **Exact `H24-SAHG1` candidate (`sahg1_candidate_exact`):** Held-out AUC **`0.58259`**, null p95 `0.53204`, margin `+0.05054`, Holm $p = 0.020$ (`strict_gate_flagged: true`).

---

## 4. Limitations and next-session work order

1. **Limitations:**
   - No outbound access or automated requests to `drivendata.org` (prohibited by standing compliance policy and competition Terms of Use); no private labels, live leaderboard verification, or submission-page receipts are available.
   - `data/training_features.tif` (419 MB) and `data/prepared/features.npy` (620 MB) are restored from hash-pinned mirrors and remain gitignored to obey the repository's artifact cap.
   - While `oof_multiphysics_hgb_d3` (`0.13000` HOLDOUT-DTI) provides a genuine, leakage-free same-protocol OOF multi-physics baseline in this repository, the external `19GEMSDOE` repository's original `H19-5` fold probability arrays were never published in Git.
2. **Next-session recommendations:**
   - **Integrate `H24-SAHG1`'s strike-projected LiDAR scarp and stable-Th-controlled K/U alteration features as fold-local input columns inside the out-of-fold `HistGradientBoostingClassifier` (`oof_multiphysics_hgb_d3`)** with training-only nuisance residualization (`gems.residualize.NuisanceResidualizer`), testing whether adding `G_strike` and `R_alt` improves OOF HOLDOUT-DTI above `0.13000` while reducing the C2ST nuisance AUC below `0.55`.
   - Maintain strict separation between `HOLDOUT-DTI` and `ORGANIZER-CONFIRMED` scores; never promote a candidate to a weekly slot without beating the `0.13000` OOF benchmark, passing the exact-file C2ST audit, and obtaining separate selector authorization.
