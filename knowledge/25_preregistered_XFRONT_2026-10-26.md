# Preregistration — H24-XFRONT (cross-modal oriented step corroboration under a rotation null) — 2026-10-26

- **Session branch:** `arena/5741170c-gemsdoe24` (base `fb9e230`)
- **Parallel-run lane declaration (self-assigned).** The owner prompt's
  "single method paragraph below" is **absent** for the seventh consecutive
  session (same irregularity recorded in `AGENTS.md`, PRs #28/#35). To avoid
  colliding with sibling sessions from the same base commit, this session
  declares its own lane **before** any code is written:

  > **Lane paragraph (H24-XFRONT).** *A fault that is missing from the public
  > catalogue is, in this basin-and-range setting, most often a structure whose
  > surface scarp is buried or subdued, so it is not expressed as a topographic
  > ridge. What survives burial is the **step** it imposes on independent
  > potential-field and airbone-electromagnetic fields. H24-XFRONT therefore does
  > not detect ridges: it detects, at every pixel, the **coincidence of
  > co-oriented gradient (step) vectors** across six physically independent
  > layers, and converts that coincidence into an **excess-orientation-coherence
  > statistic measured against a rotation null** that preserves every layer's own
  > edge geometry while destroying between-layer orientation agreement. The
  > emitted GeoTIFF is produced by one label-free operator, evaluated
  > identically on every spatial fold, at a dot budget selected **in advance** by
  > a density-matched sparse-truth simulation rather than by the dense
  > catalogue holdout.*

- **Budget:** 1 preregistered experiment inside one lane (limit 3 / 2 h).
- **Promotion:** none. A separate selector step (`gems.selector.v2`) and the
  weekly cap govern any real slot; this document cannot authorize one.

---

## 1. Ranked candidate hypotheses (all untried in `GEMSDOE24`)

Every candidate names the layers, the transform, the missing-fault mechanism,
the non-fault mimic, and the difference from everything already in this repo.

| Rank | ID | Layers | Physical signature / transform | Why it catches a fault **missing** from the catalogue | Named non-fault mimic | Difference vs. implemented lanes | Expected HOLDOUT-DTI Δ · cost |
|---|---|---|---|---|---|---|---|
| **1 — EXECUTE** | **H24-XFRONT** | `rtp`, `iso_grav_anom`, `depth_to_base_surf`, `cond_surf`, `det_elev`, `geod_shearrate` | Multi-scale (σ = 1.2, 3.0 px) gradient of each layer → **edge magnitude** (ranked) + **across-strike orientation**; per-pixel weighted mean-resultant length `R` of *doubled* orientations over layers in the top 30 % of edge strength; excess coherence `E_R = (R_obs − R_null_mean)/(1 − R_null_mean)` under a **19-draw rotation null** (each layer's orientation field translated by an independent random offset of 40–400 px, weights held fixed); corroboration `C = Σw/6`; score `= C · E_R` | Burial removes the scarp but **not** the step in basement depth, fill conductivity, gravity and magnetics. A buried fault forces **all four** of those steps to share one strike; unrelated edges do not. Every catalogue-based lane is fitted to *visible* scarps, so it is blind exactly where the catalogue is blind. | **Lithologic / stratigraphic contact and Lake Lahontan strandlines** — a buried alluvial-fan margin or a pluvial shoreline also produces co-located, co-oriented steps in AEM depth, conductivity, gravity and DEM without any fault. This is the lane's declared confound, not an afterthought. | All 16 prior lanes (MTR1, ASPC, SAHG1, GVC1, CON, FUSE, OJ1, RSHG1, HCW, CRP1, CUP1, DPRF1, EUL1, TNR1, VENT, TRSG1) feed **magnitude-only** channels (gradients, DoG, Euler, openness, arcs) into a per-fold learner or multiply isotropic surfaces. **None** computes an orientation-resolved between-layer statistic, **none** uses a rotation-null significance, and **none** uses `depth_to_base_surf`/`cond_surf` as a *step*, only as raw tree inputs. | unknown (honest: a label-free detector has historically scored 0.02–0.10 vs. 0.16 for the supervised point-best); **low cost** — no training, one deterministic operator |
| 2 | H24-DENS | any surface (diagnostic) | Emit budget `B` chosen by maximising **sparse-simulated** DTI over `B ∈ {15k, 20k, 25k, 30k, 37 654, 45k}`; sparse truth = a fixed-seed 20 % subsample of withheld *components*, the remaining 80 % unmapped (so predictions beside them are false positives) | The only leaderboard gain ever observed in this portfolio was **subtractive emission** (GEMSDOE32 `B2` = D2.8 minus ≤200 m, 0.2778 > D2.8 0.2600), and the owner-reported score is monotone in dot count from 60 069 → 37 654. The dense holdout **cannot** answer this (its marginal-inclusion threshold is ~1.6× looser), so it needs a density-matched simulation. | none (policy, not geology) | No lane in this repo has swept the emission budget on a sparse-regime proxy; budgets are inherited from `B2` (37 654) by convention. | policy finding, not a DTI claim · very low cost |
| 3 | H24-DRAIN | `det_elev`, `lidar_*` | Flow-routing knickpoints / channel deflection | Active faults deflect ephemeral wash channels before a scarp is visible | fan avulsion, ditches, strandlines | no drainage graph exists here | uncertain at 100 m · high cost |
| 4 | H24-SLAB2 | `ieq_n100a15`, `deq_n100a15`, `geod_shearrate`, `geod_dilaterate` | Conjugate Riedel shear partitioning | strike-slip faults lack scarps; catalogue is normal-fault biased | mining blast clusters, GPS interpolation edge | raw bands only in trees today | +0.003–0.010 · medium |
| 5 | H24-KERN6 | any surface | Marginal-DTI-optimal (`marginal_inclusion_threshold`) emission instead of a fixed top-k | FP is weighted only 0.2×, so the optimal rule is a threshold on expected credit, not a budget | none | no lane uses the metric's own marginal rule for emission | unknown · low cost |

**Selection:** Rank 1 (`H24-XFRONT`) is executed as the lane; Rank 2
(`H24-DENS`) is executed **inside the same lane** as the preregistered
*emission decision rule* (§3.4), so no second detector is built. Ranks 3–5 are
left for future sessions with a fresh preregistration.

---

## 2. Frozen detector specification (`src/gems/xfront.py`)

Inputs are the cached, hash-pinned 30-channel stack
(`data/prepared/features.npy`, sha `a4ca25b2…`, `scripts/prepare_data.py`) and
the pinned template/labels — no new network fetch, no new external source.

1. **Modalities (6):** `rtp` (RTP magnetics), `iso_grav_anom` (isostatic
   residual gravity), `depth_to_base_surf` (AEM depth to conductive basement),
   `cond_surf` (AEM near-surface conductivity), `det_elev` (DEM),
   `geod_shearrate` (GNSS shear-strain rate). `tmi` is deliberately excluded
   (ρ = 0.9965 with `rtp`, recorded in `AGENTS.md` under `IRR-EUL1-VG-BANDS`).
2. **NaN handling:** normalised convolution — smooth `f·v` and `v` with the
   same Gaussian and divide; no label-based imputation.
3. **Scales:** σ ∈ {1.2 px, 3.0 px}. Magnitude = elementwise max over scales;
   orientation is taken from the scale achieving that max.
4. **Edge magnitude → weight:** per-modality footprint-wide percentile rank
   `p_m`; `w_m = clip((p_m − 0.70)/0.30, 0, 1)` (only the top 30 % of each
   layer's edges can corroborate; graded, not binary).
5. **Orientation:** θ = atan2(∂_y s, ∂_x s) (across-strike); stored as a
   `uint8` index of the **doubled** angle 2θ so that the mean resultant length
   is orientation-valued on [0°, 180°).
6. **Corroboration:** `C(x) = Σ_m w_m(x)/6`; `R(x) = |Σ_m w_m e^{2iθ_m}| / Σ_m w_m`.
7. **Rotation null (19 draws, seed 20261026):** per draw, each modality's
   orientation index field is translated by an independent random integer
   offset with each component uniform on ±[40, 400] px; weights **held fixed**;
   outside-footprint orientation indices are replaced by a seeded sample from
   the inside-footprint distribution so border wrapping cannot create a fixed
   orientation. `R_null_mean` = mean over draws.
8. **Score:** `E_R = clip((R − R_null_mean)/(1 − R_null_mean + 1e-6), 0, 1)`;
   `score = C · E_R`; zero where `Σ w_m < 1.0`.
9. **Emission:** `gems.emission.priority_poisson(score, eligible, B, min_dist = 2.8 px)`;
   `eligible = footprint & (EDT(~catalogue) > 2.0 px) & (score > 0)` — the
   GEMSDOE32 `B2` clearance convention, preregistered, never tuned.
10. **Label-free:** the operator reads no labels and no prior submission
    pixels, so the identical operator is applied per fold and on the full
    footprint for the emitted file.

## 3. Frozen evaluation

### 3.1 Primary (comparable) endpoint
`gems-segment-pooled-v1` on `scripts/evaluate_holdout.py`'s
`SegmentHoldout(fp, catalogue, buffer_px=15)`: whole components hidden
everywhere, 1.5 km purge, pixel-exact visible-fault mask, pooled
TP_w/FP_w/FN_w, α = 0.2, β = 0.8, 300 m triangular kernel, **60 988**
withheld positive pixels, 95 % CI by 10 km spatial-block bootstrap
(1 999 draws). Reported as **HOLDOUT-DTI**, never as a leaderboard score.

### 3.2 Leakage canary
`SegmentHoldout.canary` on `{score, C, E_R, and each modality's edge
magnitude}` — two polarities, threshold 0.90. Any feature above 0.90 halts the
lane (it is leakage until explained).

### 3.3 Novelty (Rule 1)
`gems.novelty.compare_prospective_registry` for the pre-placement surface and
the final dots against all 46 pinned nine-site rasters **plus** every local
2026-10-25/26 TIFF, and `check_peer_blobs` against the 84 pinned peer blobs.
Gates: |ρ| ≤ 0.90 everywhere, final-dot 3-px overlap ≤ 0.70 vs. competing
method lanes and peers. The literal all-entry result (which retains the
synthetic `registry-039` spacing-5 calibration lattice) is recorded **and
reported separately**, never retro-fitted.

### 3.4 Emission budget decision rule (Rank 2, executed)
Budgets `B ∈ {15 000, 20 000, 25 000, 30 000, 37 654, 45 000}`. Per fold the
budget is `k_fold = round(B · offcatalogue_valid_fold / offcatalogue_total)`.
**Selection statistic = mean over the four folds of the sparse-simulated DTI**
(§3.5). `B*` = argmax; ties → the smaller budget. The **dense** HOLDOUT-DTI is
then reported at `B*` for comparability and is *not* used for selection. No
budget is changed after the fact.

### 3.5 Density-matched sparse simulation (secondary, declared)
The live hidden set is ~5× sparser than the public catalogue
(`AGENTS.md`, "truth density ~5x lower"). Simulation: for each fold, a
fixed-seed (20261026) 20 % subsample of the **withheld components** is the
"newly discovered" truth; the remaining 80 % of withheld components stay
excluded from `visible` and from truth, so a prediction beside them is a false
positive exactly as it would be beside an unmapped real fault. Predicted
truth density ≈ 0.24 % of the footprint vs. 1.18 % dense.
**This is a simulation of the live regime, not the live regime.** All numbers
from it are labelled `SIMULATED-SPARSE-DTI`.

### 3.6 Exact-file nuisance audit
`c2s2` classifier two-sample test on the **emitted bytes** against road /
mining-claim / four-acquisition-block confounds, labels audited first, Holm
adjusted; flag at AUC ≥ 0.55 with p ≤ 0.05.

## 4. Stop / no-retune rules
- One execution. If the canary exceeds 0.90, the lane halts.
- No retuning of σ, weights, modality set, clearance, spacing, seed or budget
  after any result is seen. A second run requires a new preregistration.
- Negative results are deliverables. New bytes are not scientific uniqueness.
- No submission slot is spent; the agent never uploads.

## 5. Deliverables
`src/gems/xfront.py`, `scripts/run_xfront_lane.py`,
`evidence/xfront_run_card_20261026.json`,
`evidence/xfront_experiment_20261026.json`,
`evidence/xfront_selector_20261026.json`,
`docs/downloads/gems24-xfront-*-zeros.tif` (+ NaN twin + ZIP),
`knowledge/26_XFRONT_findings_and_9site_executive_summary_2026-10-26.md`,
README + site update, this preregistration, and a merged PR.
