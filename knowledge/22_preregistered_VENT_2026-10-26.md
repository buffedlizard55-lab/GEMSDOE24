# Preregistration: `H24-VENT` — Volcanic Vent-Bridged Quaternary Geothermal Corridor (2026-10-26)

**Status:** Locked prior to execution on `2026-10-26` (branch `arena/fb5d0d20-gemsdoe24`)
**Session Budget:** Maximum 3 experimental arms (V1 primary + 2 ablation controls) — this doc preregisters 1 primary + 2 ablation diagnostics within a single locked script `scripts/run_vent_lane.py`; hard wall-clock `<2 h`; zero DrivenData slots spent (selector separation per Rule 6).
**Reuse:** Template cached stack not required; uses `data/bridge/sample_submission.tif`, `data/bridge/labels.tif`, `data/external/gdr_volcanic_vents_in_footprint.csv` (21 vents), `data/external/gdr_wellspring_in_footprint.csv` (27k springs), `data/external/lidar_scarp_features_u8.tif` (8 bands), `data/external/geodawn_extensions_u8.tif` (mag/grav), and `src/gems/holdout.py:SegmentHoldout`, `src/gems/submission.py`, `src/gems/novelty.py`, `src/gems/metric.py`. No private fork.
**Governance:** All numbers `HOLDOUT-DTI` (evaluator, withheld count, 95% CI) or `ORGANIZER-CONFIRMED` (receipt only). Leakage canary `AUC>0.90` = flag. LANE check `|ρ|≤0.90` & `≤70%` 3 px overlap pre-placement + final. Budget ≤3/2 h.

---

## 1. Ranked Hypotheses (5 untried, distinct from GEMSDOE24)

| Rank | ID | Layers | Physical Signature | Missing-Fault Rationale | Non-Fault Mimic | Difference vs Repo | Expected Δ / Cost / New Data |
|---|---|---|---|---|---|---|---|
| **1 EXECUTE** | **H24-VENT** | 21 Quaternary vents (row/col) + 27k springs (row/col) + 8-azimuth LiDAR `coh100`/`strike`/`step_max`/`valid` + `tmi_tilt_grad` from `geodawn_extensions_u8.tif` | Delaunay vent-vent edge azimuths → lineament anisotropy `A=|cos(2(θ_vent−θ_line))|`; spring kernel DoG `D=Gauss1.5km−Gauss5km`; subsurface `B=|∇tmi_tilt|`; unsupervised product `P = (0.3+0.7·V)·(0.3+0.7·D)·(0.2+0.8·A)·B` | Active Quaternary vents & hot-spring travertine mark **concealed geothermal conduits under flat alluvium/playa** where USGS QFaults (1:250k bedrock scarps) and INGENIOUS field lineaments are blind | Lahontan tufa benches, playa evaporite cracks, basalt flow edges | No vent-graph exists; DPRF1 used isotropic sinter DoGs, TRSG1 used seismic, SAHG1 used scarp product, not vent alignment | +0.005–0.015, low (~3 min), data staged |
| 2 | H24-SLAB2 | `ieq_n100a15`, `deq_n100a15`, `geod_shearrate` | `shear/(|dilat|+eps)·ieq·aniso` | Walker Lane strike-slip lacks scarp but has shear + microseismic | Mining blasts | Prior used raw bands, not shear partition | +0.003–0.010, medium |
| 3 | H24-GRAV | `depth_to_base_surf`, `iso_grav_hg`, `det_elev_slope` | `∇²(depth)·exp(−slope/5°)·gravHg` | Buried rangefront under alluvium | Pluton margin | SAHG1 had B_step sigmoid, not curvature | +0.002–0.008, low |
| 4 | H24-WORM | `tmi_rtp`, `tmi_up150`, `iso_grav` | Worm persistence across Gaussian pyramid | Deep basement persists vs shallow volcanics that decay | Dikes | MTR1 1D trough ≠ worm | +0.005–0.012, medium |
| 5 | H24-DRAIN | `dem_elev`, `lidar_step` | Drainage TPI knickpoint collinearity | Channel deflection before scarp | Strandlines/fans | No drainage graph | uncertain, high |

---

## 2. Fixed Protocol for H24-VENT Primary

### 2.1 Input fingerprints (verify before run)
- `data/bridge/sample_submission.tif` sha `2176d08e...` (3730×3292, EPSG:32611)
- `data/bridge/labels.tif` sha `7ba308cc...` (60,988 positives)
- `data/external/gdr_volcanic_vents_in_footprint.csv` 21 rows
- `data/external/lidar_scarp_features_u8.tif` sha `d580bb8b...`
- `data/external/geodawn_extensions_u8.tif` sha `a35a9c6d...` (for `tmi_tilt_hgrad`)

### 2.2 Surface construction (label-free, no catalogue distance)
1. Rasterize vents to `H×W` binary `V_bin` via row/col; compute Euclidean distance `d_vent` (EDT); `V = exp(−d_vent / 50)` (50 px = 5 km, range `≈[0,1]`).
2. Rasterize springs with `thermalclass==Hot` (filter) to `S_bin`; Gaussian blur `σ15=15 px` & `σ50=50 px` via 2D separable uniform approx; `D = clip(G15−G50,0,1)` normalized to 95th.
3. Decode LiDAR: `coh100`, `strike`, `step_max`, `valid` from u8 via `aspc.decode`; support `fp & valid>0`; `A = sqrt(coh100)` (coherence) modulated by vent azimuth coherence: for each pixel, `θ_line = strike`; `θ_vent` = azimuth to nearest vent edge (Delaunay); `A_mod = 0.2+0.8·|cos(2·(θ_vent−θ_line))|`.
4. Decode `tmi_tilt_hgrad` from extensions u8 (u8→float via `c224..`? Actually `geodawn_extensions_u8.tif` band 3? Use placeholder `tmi_tilt_grad` as grav-tilt proxy); `B = robust_sigmoid(|∇B|, support)`.
5. Combined unsupervised surface `P = V·D·A_mod·B` on support, `0` elsewhere; clip `[0,1]`.

No catalogue `dist_known_fault_px` or `labels.tif` enters surface; only external label-free geodata.

### 2.3 Holdout evaluation (Rule 2: hide-and-recover)
- `SegmentHoldout(fp, catalogue, buffer_px=15)` → 4 folds NW/NE/SW/SE, `60,988` withheld, `n_unique_withheld_components` via `holdout.py`.
- For each fold, supply `P` as prediction (unsupervised, same for all folds; whole-component visibility matters only for masking, not for training).
- Score via `holdout.summarize([P_fold...])` → `HOLDOUT-DTI` pooled `α0.2 β0.8 300 m` + `ci95` (1,999 10 km block bootstrap). Compare vs `oof_multiphysics_hgb_d3 0.13000`, `B1 0.13900`, `B0 0.14179`, `DPRF1 0.16379` (same evaluator/count). `Rule 8: do not spend slot unless beats current best`.
- Leakage canaries: test `V,D,A_mod,B,P` individually via `holdout.canary({name:surf})`; `worst max(AUC,1−AUC) ≤0.90` PASS else flag.

### 2.4 Dot emission (unique, format-valid)
- Budget `37,654` dots (footprint-scaled, matches B2 for comparability) with `catalogue_clearance_px=2.0` (`200 m`) and `min_spacing_px=2.8` (~300 m submodular kernel via Poisson disk `aspc.place_dots(P, eligible, 37654, 2.8)`).
- `eligible = support & ~catalogue & (dist_cat>2)` (catalogue exactly masked).
- Binary `{0.0,1.0}` dots; outside footprint handled via `submission.write_submission(..., outside="zero"/"nan")` → strict `[0,1]` all-finite for `-zeros`, NaN outside for `-nan`, plus `.zip`.

### 2.5 Novelty & audit gates (Rule 1)
- Pre-placement: rank-correlation `|ρ|≤0.90` vs all `registry/priority_rasters.json` (46 rasters) + `registry/peer_rasters_20261025.json` (83 blobs) + 9 local method lanes; sample 200k rank pixels.
- Final dots: directional `3 px` overlap `≤70%` vs same registry sets; retain literal all-entry `registry-039` lattice on record (fail-closed).
- Exact-file C2ST nuisance audit via `gems.c2s2.c2s2_test(P_dots_raster, ...)` with spatial-block swaps, Holm `p`.
- Validator: `submission.check_variants(artifact, template)` → `format_valid`, `footprint_range_0_1`, `footprint_all_finite`, CRS/shape/transform match.

### 2.6 Ablation diagnostics (within 3-exp budget)
- **A1 V-only:** `P=V·B` (no spring/lineament) — isolates vent proximity.
- **A2 No-vent:** `P=D·A_mod·B` — isolates hydrothermal + structural without vents.

### 2.7 Run card (Rule 5)
One JSON `evidence/vent_run_card_20261026.json`: hypothesis, mechanism, named mimic, holdout+CI vs baselines, correlation/overlap vs registry, sha256, validator, submission name (`gems24-vent-quat-bridge-20261026-{id}-zeros.tif`) + note `≤140 chars`, verdict `promote`/`negative`. Negative is deliverable.

---

## 3. Expected Outcome & Stop Condition
- **Expect:** `HOLDOUT-DTI ≈0.08–0.12` (unsupervised < DPRF1 `0.16379`), likely `NEGATIVE` vs current best, but **passes** format, canary, C2ST, competing-method novelty (`<50%` because vent clusters sparse), literal lattice **FAIL** (inevitable for dotted submissions).
- **Stop:** Log duplicate if `>70%` overlap vs any registry raster on surface OR final dots; no retuning; no slot; publish negative card and `DOWNLOAD: YES · SUBMIT: NO` site update with 9-site executive summary.

