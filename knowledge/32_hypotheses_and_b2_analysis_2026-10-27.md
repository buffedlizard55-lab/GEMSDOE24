# Nine-Site GEMS DOE 24/25/27/28/30/31/32/33/36 — Hypotheses, B2 Forensics, and 2026-10-27 New Unique Lanes
*Generated 2026-10-27 · Branch arena/363f4b81 · Data-Restore + Holdout-Gated Experiments*

## Executive Verdict (automated gates)

- **DOWNLOAD: YES — SUBMIT: NO** (all files fail the literal 70% lattice gate; no file is authorized).
- Highest **OWNER-REPORTED / UNVERIFIED** historical peak across the nine focus sites: **GEMSDOE32 B2 0.2778** (submitted 2026-10-04). Zero organizer receipt in repo; do not resubmit.
- Highest **local HOLDOUT-DTI (gems-segment-pooled-v1, 60,988 withheld)** produced in this program: **GEMSDOE24 S3DEP1 0.16606 [0.15186, 0.18034]** (2026-10-26, 61-ch, 37,654 dots, zero 1 m LiDAR). Paired Δ vs prior best DPRF1 0.16379 is +0.00227 [−0.00699, +0.01144]. S3DEP1 fails novelty vs DKRN1 (71.32% >70%) and C2ST road-corridor flag — **not submit-ready**.
- **New unique lanes (this session, 2026-10-27, 2/3 budget spent):**
  - **H24-NEW-UNIQUE (30-ch HGB, K=37654):** HOLDOUT-DTI **0.14034 [0.12677, 0.15394]**, SHA `53603c4744442a464abb03b887101b2377f033238b43b7a4a5c8dfb728a25bd3`, **competing-method novelty PASS (64.40% ≤70%)**, literal lattice FAIL (99.79% vs `registry-039`), median far-field 14.8 px (52.3% >2 km). DOWNLOAD YES, SUBMIT NO.
  - **H24-SIGNED-CGMAG (35-ch with signed cross-gradient reversal, K=37654):** HOLDOUT-DTI **0.13582 [0.12219, 0.14898]**, SHA `793ec5c67f06d9a6baea9b6145301bc893f5cc7ea27b8dba0d318233054f14be`, competing-method PASS (63.89% ≤70%), literal FAIL (99.68%).
- **Lattice obstruction (combinatorial bound):** Calibration lattice `13gems_20261001_r13-lattice-s5_v2_nan-outside.tif` (3730×3292, 206,895 dots, 99.87% 3-px coverage of the 5,167,373-cell footprint; 6,649 uncovered cells = isolated 5×5 hole centers) imposes pigeonhole minima: **K=37654 → 82.34%**, **K=15000 → 55.67%**. No standard-budget (37,654-dot) file can pass 70% under the literal all-entry definition without trivial evasion. Any submission must either negotiate the calibration scope or use K≤22,163 (and accept the associated DTI penalty). This bound was recomputed via `distance_transform_edt` on `sample_submission.tif` / external rasters (EPSG:32611, 100 m, transform `100,0,243350,0,-100,4508550`) and reconfirmed in this session.

All scores are **HOLDOUT-DTI** (local evaluator + withheld count + CI) — *never* written as leaderboard scores. `ORGANIZER-CONFIRMED` requires a DrivenData submission-page receipt; none exists for any figure in this document.

---

## 1. Nine-Site Summary (concise per-site table)

| Site | Highest historical peak (OWNER-REPORTED / UNVERIFIED, prohibited to copy) | Latest source-recorded holdout (gems-segment-pooled-v1 unless noted) | File to download (research only) | Overlap vs lattice (3 px) | Verdict |
|------|--------------------------------|--------------------------------|-----------------|---|---|
| GEMSDOE24 | H25-1 / D1.5 0.2477 (`989f59505db1`) | S3DEP1 0.16606 [0.15186,0.18034] (60,988 w/h, paired Δ +0.00227) — current local point-best | `gems24-s3dep1-negative-10m-monoclinal-20261026-464fa34b4091-zeros.tif` (SHA 86516533…) | 99.87% | DOWNLOAD YES / SUBMIT NO |
| GEMSDOE25 | D2.8 0.2600 (`e56ea318af89`) | H71 HOLDOUT-DTI 0.05058 [0.03726,0.06389] (21,835 w/h, `gems25.holdout.v1.2-buffered-4quad`) | `gems25-h71-hgpc-blind-b2-sapd3-k3p5-20261026-9eb0c31e5149-zeros.tif` | 100% | RESEARCH ONLY / NO |
| GEMSDOE27 | GAP-CLOSURE T-V2 0.2449 (`5512495c6bd1`) | H31-DRCG 0.04730 [0.04453,0.04962] (120,778 w/h, disputed vs 289,180 in README) | `gems27-h31-drcg-wl-celf28-20261026-cf8e1bbef244-allfinite.tif` | 99.61% | RESEARCH ONLY / NO |
| GEMSDOE28 | H36-1 Rung-30 Blind 0.2710 (`b531dae0a36f`) | S22-CTXHGB 0.12018 [0.10471,0.13649] (36,596 w/h, `gems27.metric.dti_binary`) | `gems28-s22-ctxhgb-20261026-e23dabcec6e2-allfinite.tif` | 99.62% | RESEARCH ONLY / NO |
| GEMSDOE30 | D28 Poisson 0.2600 (`91eae1ca`) | CSR1 0.15816 [0.14499,0.17147] (60,988 w/h, `component-holdout-v3-blockstats-20261025`) | `gems30-CSR1-44090-20261026-502fb5948335-zeros.tif` | 99.99% | RESEARCH ONLY / NO |
| GEMSDOE31 | H27-4 Solo 0.2708 (`8acb75e1`) | H31Y Regime-Mosaic 0.15496 [0.14011,0.17012] (60,988, `gems57-pooled-hide-v2`) | `gemsdoe31-h31y-regime-mosaic-37654-20261026-66162f1f-zeros.tif` | 99.05% | RESEARCH ONLY / NO |
| **GEMSDOE32** | **H33-B2 0.2778 (`e5eb6e7e`) — program peak** | H47-LDGI 0.11976 [0.10573,0.13290] (22,232, HIDE-RECOVER-v3) | `gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif` | 99.92% | HISTORICAL DUPLICATE (see §2) — NO |
| GEMSDOE33 | H33D Analog Tip-Stepover 0.2632 (`cb49042592…`) | FSML2-CC 0.10308 [0.09414,0.11294] (60,988, confirm split) | `gemsdoe33-fsml2-cc-37654-20261026-6fd4410bbaee-zeros.tif` | 100% | RESEARCH ONLY / NO |
| GEMSDOE36 | Anderson Geothermal PINN 0.2750 (`9b9ea4e6`) | KPL-36 0.17010 [0.15509,0.18614] (60,988, `gems-segment-pooled-v1`) — highest comparable pooled-DTI outside S3DEP1 | `gemsdoe36-kpl36-exp3-20261026-fc869911e88c-zeros.tif` | 99.17% | RESEARCH ONLY / NO |

All source-recorded holdouts are *source-recorded*, not independently replayed; none is an organizer score. The table preserves the original submission filenames/SHAs for reference — downloading them does not make them submit-ready.

---

## 2. B2 Forensics — Why 0.2778 Beat Everything (and why 0.3195/0.4413 are not comparable)

### Pixel-exact mechanism (established)

Byte-level diffing (registry/priority_rasters.json + evidence/priority_review_20261025.json, reconfirmed 2026-10-27) shows:

- **B2 (`h33-h33-2-b2 … e5eb6e7e-zeros.tif`, 37,654 dots) is exactly D2.8 (`dotted-h19-5-d2-8 … e56ea318af89`, 44,090 dots = 0.2600) minus the 6,436 dots with `d_cat ≤ 200 m`** of public training faults. **Zero dots added.**

Under DTI = T / (T + 0.2·F + 0.8·G) with R=3 px (300 m) and 3-px triangular smoothing, those 6,436 dots sit in the already-mapped halo where the marginal blind-hit rate is negligible. Removing them deletes **0.2·ΔF = 1,287.2** of denominator penalty while T is barely affected — a pure false-positive prune.

Threshold: at D0=0.2600, a removed subset raises DTI iff its hit-to-false-positive ratio satisfies **t/f < D0/(5−4·D0) = 0.0549** (≈5.2% blind precision outside the halo). The 6,436-dot halo trivially meets it (t≈0), so DTI must rise — which it did, to 0.2778.

### Why that matters geologically

D2.8 is the ancestral H19-5 Poisson300m OffCat file replicated across GEMSDOE24/25/30/31/32/33 (SHA `3e78737f0…`/`8cf893ea…` etc.). Its 0.2600 already encoded a strong prior: faults are not uniformly scattered, they step within 300 m of known segments. B2 is the *same* geology with a catalogue-apron handicap removed — not a new structural discovery.

### Reconciling 0.2778 vs 0.3195 vs 0.4413

- **0.2778** — highest *artifact-attached* value in the nine-site focus brief (GEMSDOE32 B2, 2026-10-04). This is the correct program peak to cite when comparing historical submissions.
- **0.3195** — older overall leaderboard #1 *snapshot* (all sites, not nine-focus) preserved in an earlier standing-prompt paragraph; no artifact link survives in this repo.
- **0.4413** — 2026-10-25 overall leaderboard #1 *snapshot* (newer prompt header), cross-checked vs GEMSDOE32's live snapshot 0.4437 (2026-10-26). This is cross-project (all GEMS DOE groups), not a nine-focus artifact score.

None has an organizer receipt in this checkout. Treating them as comparable is a category error: B2's DTI is evaluated on undisclosed blind faults; the live leaderboard uses a strictly masked scoring set (catalogue faults hidden per community https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516/4 — pixel-exact mask, known USGS ingenious faults hidden when scoring). The only honest path past 0.2778 is marginal blind precision >5.82% outside the apron — i.e., 3DEP scarp + pure geophysical step detection in the 31.8% LiDAR gap, not halo pruning.

---

## 3. Five Hypotheses for Genuinely New Fault Mass (ranked)

All assume the current frozen training stack (418,912,844 B, SHA `4371c82e7…`, 19 bands; prepared `features.npy` 5,167,373×30 float32, 592 MB, SHA `a4ca25b…`) plus any *public* DEM-derived relief — no catalogue leakage.

| Rank | Hypothesis | Observable Signature | Why It Catches What the Catalogue Missed | What Must Change from Prior Lanes |
|------|------------|-------------------|----------------------------------------|----------------------------------|
| **1** | **SIGNED-CGMAG: signed gravity–magnetic cross-gradient reversal across terrain tangent** | RTP vs `iso_grav_anom` (`band6`) horizontal gradients go from subparallel (over intact basement) to orthogonal/antiparallel; the *signed* cross-product c = (∇RTP × ∇g)·ẑ flips sign along a 3DEP-defined monocline/scarp | Catalogue is dominated by surface breaks; an oblique buried splay under thin alluvium rotates the basement susceptibility edge away from the density edge without a surface offset. Previous lanes used unsigned gravity/mag channels or scalar curvature. | New channels: `c_σ` at σ=1.2,3.0 + `∂c/∂t` along terrain tangent (see §4). Validated on `gems-segment-pooled-v1` (60,988). |
| 2 | ORTHO-K-COND: Curie–conductivity orthogonality conditioned on lithology | High K (magnetic Curie-proxy) rank *within* each `Th/U`/rad channel, orthogonal to `cond_surf` trend | Catalogue under-samples blind faults in conductive basin fill where resistivity masks magnetics. Conditioning removes lithology contrast mimics. | Rank-transform K and `cond_surf` per lithology bin; train conditioned residual. |
| 3 | FLEXURE-DIPOLE: monoclinal flexure dipole in 3DEP 10 m DEM | Paired 300 m/800 m downslope–upslope tilt dipole straddling a 1.5 km wavelength warp, with `det_local_relief` null | Blind reverse faults under alluvium produce broad warps, not sharp scarps; S3DEP1's single-scale operators miss the dipole. | Dual-scale second-difference of `det_elev`; cross-validated against road/claim C2ST (AUC<0.55). |
| 4 | MAG-GRAV-TEXTURE: cross-strike anisotropy of potential-field texture | Azimuthal semivariogram jump 2× stronger cross-strike than along-strike on RTP/gravity, decoupled from `arc_*` lidar flags | Alluvial basins hide faults in lidar; field texture anisotropy survives under cover. Prior lanes coupled `arc_*` radii too tightly to photolineaments. | Isotropic vs anisotropic texture at 300 m/800 m; exclude any channel with leakage AUC>0.90. |
| 5 | MULTI-CATCHMENT-OFFSET: watershed divide offset | Systematic 200–600 m divide migration across a linear trend, with upstream area asymmetry | Long-term fault slip deflects divides; catalogue short circuits on young scarps miss maturity signal. Requires 10 m D8 routing (not attempted this session). | Deferred — needs absolute 10 m DEM tiles outside this checkout (data/dem10 absent). |

Ranking criterion: expected **Δ HOLDOUT-DTI** per engineering cost under blind evaluation (60,988 positives, R=3 px). H1 was implemented this session as H24-SIGNED-CGMAG (§4); it did not beat S3DEP1 but validated the mechanistic channel construction.

---

## 4. H1 Implementation (2026-10-27) — What Was Built and What Scored

**Mechanism code (run_new_unique_lane_v3.py):** From 100 m footprints (`footprint.py` WIDTH 3292 HEIGHT 3730, EPSG:32611, transform `100,0,243350,0,-100,4508550`), filled `rtp`, `iso_grav_anom`, `det_elev` via nearest-neighbor inpainting inside footprint, Gaussian σ 1.2/3.0, gradients in meters (100 m/px), signed normalized cross-product `c = (∇RTP × ∇g)/|∇RTP||∇g|`, terrain tangent from `det_elev` tilt, and along-tangent derivative magnitude `|∂c/∂t|`. Five new channels: `c1,c3,d1,d3,slope` → 35-ch stack `data/prepared/new_unique_v3.npy` (SHA `5fa882d4…`). Training: `HistGradientBoostingClassifier(max_iter=80, max_leaf=15, lr=0.08, l2=5.0)`, per-quad hide-and-recover (buffer 15 px, negatives ≥9 px from withheld), budget K=37654, `priority_poisson` min-dist 3 px (mirroring `run_s3dep1_lane.py` pattern, prereg `7e6db4d428ae`, SEED 20261026/20261027, FULL_DOT_BUDGET 37654, PRIMARY_SHARE 0.72, 61-ch, SegmentHoldout, canary ≤0.90, paired DPRF1/OOF-d3, bridge 3 km, C2ST, selector v2).

- **Leakage canary:** PASS (worst pooled AUC 0.658 on OOF surface; raw-feature AUCs ≤0.402).
- **Holdout:** 0.13582 [0.12219, 0.14898] (SIGNED-CGMAG) — below S3DEP1 0.16606; 0.14034 [0.12677, 0.15394] for the 30-ch baseline re-run.
- **Novelty:** Competing-method lane (prospective registry, 167 unique contents at `data/research/portfolio_20261026T1612Z/cache/…`) — **PASS** (max 3-px dot overlap 63.89% / 64.40% ≤70%; lattice excluded from competing lane). Literal gate (all 167 + registry-039 calibration lattice 206,895 dots) — **FAIL** (99.68–99.79% lattice overlap).
- **Format:** single-band float32 [0,1], EPSG:32611, zero outside (strict whole-array finite PASS); NaN-outside twin + ZIP per `submission.write_submission`/`check_variants`.

**Interpretation:** H1 adds orthogonal information (signed reversal is not in S3DEP1/XVAR1's unsigned channels), but on this withheld geometry it underfits the dominant apron signal that S3DEP1's 10 m 3DEP monocline operators capture. Its value is as a *diversifier*, not a replacement — stackable, not dominant.

---

## 5. “Predicted values must be in range [0,1]” — Handling

- All `_zeros.tif` outputs in this session are **strict-whole-array finite**: every stored cell (including outside-footprint zeros) is finite ∈[0,1]; validator `variant_strict_whole_array_no_nan_allowed` PASS.
- Legacy `_allfinite.tif` / `_nan.tif` companions are also generated for compatibility; the competition's official page (https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) and mask clarification (https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516/4) define the grid but do not document this rejection cause.
- **No portal upload was attempted**; no receipt exists. Either encoding passes the *local* validator; organizer acceptance is untested.

---

## 6. How to Use This (download ≠ submit)

All TIFs below are **research-only**. To submit, the project requires (per `gems-selector-v2-literal-quota-fail-closed`): paired holdout win vs recorded best, per-feature leakage canary, literal novelty (≤70%), exact-file C2ST, valid weekly quota, and independent replay certificate — none is satisfied.

```text
docs/downloads/gems24-new-unique-hydro-gravity-hgb-20261027-df63489defe3-zeros.tif
  SHA-256 53603c4744442a464abb03b887101b2377f033238b43b7a4a5c8dfb728a25bd3  37,654 dots  HOLDOUT-DTI 0.14034  DOWNLOAD YES / SUBMIT NO

docs/downloads/gems24-signed-cgmag-reversal-hgb-20261027-52c0189a911b-zeros.tif
  SHA-256 793ec5c67f06d9a6baea9b6145301bc893f5cc7ea27b8dba0d318233054f14be  37,654 dots  HOLDOUT-DTI 0.13582  DOWNLOAD YES / SUBMIT NO

docs/downloads/gems24-s3dep1-negative-10m-monoclinal-20261026-464fa34b4091-zeros.tif
  SHA-256 86516533fb525ebce792152ae4ed852e88ae4feda0bd596710c7319a238b8071  37,654 dots  HOLDOUT-DTI 0.16606  DOWNLOAD YES / SUBMIT NO (prior local best)
```

*Generated TIFs are new byte-unique contents (SHA not in `registry/priority_rasters.json` priority set nor in `data/research/portfolio_20261026T1612Z` audit). Distinct bytes ≠ literal-gate pass.*

---
*Method sources: competition page & mask thread (see §5), `src/gems/{footprint,holdout,novelty,submission,validator,c2s2,confounds}.py`, `scripts/{restore_data,prepare_data,run_s3dep1_lane}.py` (read 2026-10-27), `data/bridge/sample_submission.tif` (3730×3292, EPSG:32611), `inputs/calibration/13gems_20261001_r13-lattice-s5_v2_nan-outside.tif` (206,895 dots).*
