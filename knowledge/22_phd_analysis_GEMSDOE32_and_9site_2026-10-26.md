# PhD-Level Analysis: Why GEMSDOE32 `h33-h33-2-b2` (0.2778) Leads the Nine Focus Sites & How to Beat It — 2026-10-26

- **Date (UTC):** 2026-10-26
- **Analyst:** H24-VENT session, Arena `fb5d0d20`
- **GEMSDOE32 artifact:** `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif` — `UNVERIFIED-OWNER-REPORT 0.2778` (no DrivenData receipt archived; `ORGANIZER-CONFIRMED` requires artifact-linked submission-page screenshot per Parallel-Run Protocol Rule 3)
- **Nine focus sites:** `GEMSDOE24, 25, 27, 28, 30, 31, 32, 33, 36` (owner-reported historical bests in `registry/owner_reported_scores_2026-10-26.json`)
- **Current leaderboard claims in brief:** `0.4413` and `0.3195` — **conflicting, both `UNVERIFIED-OWNER-REPORT`**, never `ORGANIZER-CONFIRMED` (see `knowledge/owner_brief_2026-10-26_delta.md`)
- **Evaluation metric (verified):** Distance-weighted Tversky `DTI = T / (αT + βF + βN)` with `α=0.2, β=0.8`, 300 m triangular kernel, pixel-exact known-fault masking (`https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/`, `https://github.com/drivendataorg/gems-prize-reference-solution` commit `aebe92f`)
- **CRS/shape:** `EPSG:32611` (https://epsg.io/32611), `3730×3292` @100 m, transform `[100,0,243350,0,-100,4508550]` — `data/bridge/sample_submission.tif` SHA `2176d08e485...`

---

## 1. Nine-Site Forensic Geometry (exact pixel counts, not scores)

| Focus Site | Historical Best (`UNVERIFIED`, owner page) | Dot Count | Catalogue Clearance | `2<d≤9 px` (200–900 m) Apron | `>20 px` (>2 km) Far-Field | Verdict |
|---|---|---|---|---|---|---|
| **GEMSDOE24** | `h25-1-dotted-h19-5-d1-5` 0.2477 | 60,069 Poisson `d1.5` on H19-5 | `>100 m` | ~35% (H19-5 thinned bridge) | ~30% | Thinned H19-5; strong but superseded |
| **GEMSDOE25** | `dotted-h19-5-d2-8` 0.2600 | 44,090 Poisson `d2.8` on H19-5 | `>100 m` | 45.5% | 16.4% | Identical dot set to GEMSDOE30 D2.8 |
| **GEMSDOE27** | `topo-gap-closure-t-v2-on-d1-5` 0.2449 | 60,069 dots on D1.5 | topo-bridged | 35.8% | 44.3% | Gap-closure |
| **GEMSDOE28** | `h36-1-rung30-blind-r1` 0.2710 | 40,700 = H27-4 40,199 + 501 rung | `>100 m` + rung | 27% | 49% | H27-4 + relay rungs |
| **GEMSDOE30** | `d28-poisson300m-offcat-44090` 0.2600 | 44,090 Poisson `d2.8` | `>100 m` | 45.5% | 16.4% | Same as GEMSDOE25 D2.8 |
| **GEMSDOE31** | `h27-4-solo-d28` 0.2708 | 40,199 = D2.8 − 3,891 `≤100 m` | `>100 m` | 47.9% | 22.9% | D2.8 minus 100 m |
| **GEMSDOE32** | **`h33-h33-2-b2` 0.2778** | **37,654 = D2.8 − 6,436 `≤200 m`** | **`>200 m`** | **27.4%** | **49.2%** | **D2.8 minus 200 m; 0 new dots** |
| **GEMSDOE33** | `h33d-analog-tip-stepover-r30` 0.2632 | 44,090 = B2 37,654 + 6,436 tip | B2 + tip | 37.6% | 38.7% | B2 + stepover |
| **GEMSDOE36** | `anderson-geothermal-pinn-38854` 0.2750 | 38,854 = B2 37,654 + 1,200 PINN | B2 + PINN | 34% | 46% | B2 + Andersonian |

**Forensic key (from `evidence/priority_review_20261025.json` + `knowledge/14_h33_analysis_2026-10-25.md`):**
- GEMSDOE32 B2 is a **strict subset** of GEMSDOE25/30 D2.8: `44,090 → 37,654` by deleting **every dot at `d_cat ≤2 px (200 m)`** to the public `labels.tif` catalogue. Relative to GEMSDOE31 H27-4 (already `>100 m`), it deletes **2,545 additional dots** at `100–200 m`. **Zero new detections.**
- Median `d_cat`: footprint 23.09 px, B2 19.65 px, GEMSDOE27 H29-CELF 16.16 px, GEMSDOE24 GVC1 5.66 px (collapsed). B2 keeps `49.2% >20 px` far-field.

---

## 2. Why 0.2778 Is Highest Among Nine — Mechanistic (Not Just “Fewer False Positives”)

### 2.1 Tversky arithmetic under catalogue masking

Organizer metric (verified in `src/gems/metric.py`): per-pixel triangular weights `K(d)=max(0,1−d/300m)` at 100 m pixels ⇒ only the `≤3 px` halo matters. Inside `d_cat ≤200 m` (2 px), predicted positives are **masked against visible faults** (`visible_fault_mask` pixel-exact), but hidden faults at `d_cat` small still carry `K>0`. The pooled DTI is:

```
DTI = T / (0.2 T + 0.2 F + 0.8 N) , N = Σ K(hidden_truth)
T = Σ K·pred_hidden, F = Σ K·pred_background
```

Removing a dot at `d_cat=1 px` loses `t=K·1` true-credit with probability `p_hit` (chance it sat on hidden truth) but saves `f=K·1` false-mass with probability `1−p_hit`. Let `T₀,F₀,N` pre-removal. Removal of `(t,f)` improves DTI iff:

```
t·(0.2 F₀ + 0.8 N) < 0.2 T₀· f
```

If hidden truth density at `≤200 m` is low (plausible: mappers already walked the obvious scarps), `t` small, `f` dominates denominator → DTI rises. **This is an emission-policy effect, not proof B2's detector discovered geology that D2.8 missed.**

### 2.2 Why GEMSDOE32 beats GEMSDOE31 (+0.0070), GEMSDOE28 (+0.0068), GEMSDOE36 (+0.0028)

- GEMSDOE31 already removed `≤100 m`; B2's extra `100–200 m` clearance cuts another `2,545` dots where `K≈0.33–0.66` still creates `F` but hidden-hit rate is lowest (mappers rarely miss a fault 100 m from a mapped one without a major alluvial cover).
- GEMSDOE28 added 501 relay-rung dots at stepovers (geologically sound) but kept `40,199` H27-4 base; B2's **subtractive** policy is more conservative than additive rungs in a metric that penalises `F` at `0.2×` vs `T`.
- GEMSDOE36 added 1,200 PINN dots (physics-informed) to B2; if those 1,200 were in low `p_hit` zones, net DTI fell `0.2750 < 0.2778`.
- All three differences are **within plausible bootstrap noise** — without `ORGANIZER-CONFIRMED` receipts and without hidden `T,F,N`, causality is **untestable**.

### 2.3 What B2 does NOT prove

1. That catalogue distance alone is the optimal policy (held-out far-field `>2 km` needs signal, not just clearance).
2. That B2's detector is better than GEMSDOE27 H29-CELF (0.2190) in a Stitched-OOF sense — H29-CELF's `44.3% >20 px` far-field came from a **dual-partition OOF** model (no in-sample refit), while B2 is a thinned H19-5 whose base model may still be in-sample.
3. That fewer dots always win: GEMSDOE32's `37,654` vs GEMSDOE30's `44,090` win is **not monotonic**; GEMSDOE27's `37,654` CELF also beats larger sets because of far-field allocation.

**Limitation:** No hidden labels, no artifact-linked receipt, no `T,F,N` decomposition for any of the nine — all claims remain `UNVERIFIED-OWNER-REPORT`.

---

## 3. Can We Beat 0.2778 / 0.3195 / 0.4413?

**Honest answer:** The only verifiable “beat” today is **HOLDOUT-DTI**, not organizer score.

- **Local best:** `H24-DPRF1` = **HOLDOUT-DTI 0.16379** `[0.15045,0.17739]` (`gems-segment-pooled-v1`, 60,988 withheld positives, `4/4` folds vs `oof_multiphysics_hgb_d3 0.13000`, `B1 0.13900`, `B0 0.14179`; `57/57` competing-method novelty `≤55.78%`, `83/83` peers `≤54.94%`, C2ST `0.5247 PASS`, `52.3% >2 km` far-field). See `evidence/dprf1_run_card_20261026.json`.
- **Why holdout ≠ leaderboard:** Holdout density = public catalogue density (`~5×` hidden). Emission policies tuned on holdout may not transfer. The only independent pairs with known live scores (`h25→h28`) had **wrong-sign dense-ratio** (harness predicted −23% live, actual +44%).
- **Path to >0.2778 (not a forecast):** (a) Keep B2's `>200 m` clearance, (b) replace H19-5 backbone with a **Stitched-OOF** multi-physics + INGENIOUS hydrothermal detector (H29-CELF already proved `0.2190` live with this), (c) add **concealed intrabasin/stepover** allocation (`32%` regime in DPRF1) to lift `>20 px` from `49.2%` toward footprint `55.1%` without reintroducing `200–900 m` apron.

No organizer score is predicted. No slot is authorized until a separate selector verifies quota + replay.

---

## 4. Five Ranked Untested Hypotheses (Not Yet in GEMSDOE24)

All use **free, official, obtainable** data already staged in `data/external/` (verified obtainability in `data/manifest.json` + `registry/sources.json`); no new network fetch required. Each names layers, transform, missing-fault rationale, non-fault mimic, distinction, expected DTI, cost.

| Rank | ID | Specific Layers | Physical Signature / Transform | Why It Catches a Fault Missing from USGS/INGENIOUS Catalogue | Named Non-Fault Mimic | Difference vs. GEMSDOE24 Implementations | Expected HOLDOUT-DTI Δ & Cost |
|---|---|---|---|---|---|---|---|
| **1 — EXECUTE** | **H24-VENT** | `gdr_volcanic_vents_in_footprint.csv` (21 vents) + `gdr_wellspring_in_footprint.csv` (27k) + `paleo_geothermal_regional.zip` (899 sinter) + `lidar_scarp_features_u8.tif` 8-azimuth `coh100`/`strike` + `gvc_tmi_tilt_grad` | **Vent-bridged Delaunay × sinter-ring DoG + 8-azimuth lineament anisotropy:** Delaunay triangulation of Quaternary vents → edge azimuths; spring/sinter kernel-density `DoG(σ1=1.5 km, σ2=5 km)`; lineament `Rmax−Rmin` anisotropy along vent-vent azimuths; tilt-gradient persistence `|∇θ|·H_conduit`; unsupervised product `P=H_vent·H_sinter·A_line·S_subsurf` | Quaternary (<2 Ma) monogenic vents and travertine aprons mark **active geothermal conduits** under flat alluvium/playa where **no topographic scarp exists**; USGS Quaternary Faults (QFaults, slip rate ≥0.2 mm/yr, map scale 1:250k) and INGENIOUS field-mapped lineaments are biased to **bedrock range-front scarps** | Ephemeral playa evaporite polygons, Lake Lahontan tufa shoreline ridges, basaltic flow edges | No vent-graph exists: DPRF1 used INGENIOUS points as isotropic DoGs, not vent-vent structural bridging; TRSG1 used seismic, not vent anisotropy; SAHG1 used LiDAR scarp, not vent alignment; MTR1 used magnetics only | **+0.005–0.015** plausible (SW/SE basin playas); **low cost** (~3 min CPU, no training) |
| 2 | H24-SLAB2 | `ieq_n100a15`, `deq_n100a15`, `geod_shearrate`, `geod_dilatationrate`, `gvc_dem_lineament_aniso` | Conjugate Riedel shear `geod_shearrate/(|dilatation|+eps) × ieq × dem_aniso` in Walker Lane | Strike-slip faults lack vertical scarp but show microseismic shear + en-echelon lineaments; catalogue is normal-fault-biased | Mining blast clusters, GPS interpolation edge | Prior lanes used raw `ieq`/`geod` bands in trees, not explicit shear-partition product | +0.003–0.010 (SE fold), medium |
| 3 | H24-GRAV | `depth_to_base_surf`, `iso_grav_anom_hg`, `det_elev_slope` | Basement step curvature `∇²(depth_to_base)` gated by `exp(−slope/5°)` flat-cover mask + grav Hg coincidence | Concealed intrabasin fault offsets basement under alluvium with zero surface scarp; DEM gate selects valleys where LiDAR fails | Buried pluton margin, paleochannel | SAHG1 had `B_step` sigmoid sum, not isolated curvature; prior 61GEMSDOE buried-step failed holdout | +0.002–0.008, low |
| 4 | H24-WORM | `tmi_rtp`, `tmi_up150`, `iso_grav_anom`, DEM `coh100` | Multi-scale worm persistence: Gaussian pyramid (σ0, σ1=up150, σ2=2×) ridge coherence across scales | Shallow volcanic float decays with upward continuation; deep basement fault persists → cross-scale filter | Dike swarm, tilted volcanics | MTR1 tested 1D trough, not worm; GVC1 used `rtp−up150` difference, not persistence | +0.005–0.012, medium |
| 5 | H24-DRAIN | `dem_elev`, `lidar_step`, `gvc_dem_lineament_rmax` | Drainage thalweg `TPI<−1.0` knickpoint co-linearity ⊥3 washes + azimuth deflection | Active strike-slip/incised normal faults deflect ephemeral channels before bedrock scarp | Lahontan strandlines, fan avulsion, ditches | No drainage graph exists | uncertain at 100 m, high cost |

**Rank 1 selection:** Only vent-bridging exploits **Quaternary geothermal activity** — the competition's stated prize target — with the simplest unsupervised test (no HGB retraining). All external data verified obtainable: USGS GeoDAWN DOI 10.5066/P93LGLVQ (https://www.usgs.gov/data/geodawn...), OpenEI GDR1391 DOI 10.15121/1881483 (https://gdr.openei.org/submissions/1391), USGS QFaults (https://www.usgs.gov/programs/earthquake-hazards/faults), GBCGE INGENIOUS (https://gbcge.org/current-projects/ingenious/). No new external fetch needed — `data/external/` already contains `gdr_volcanic_vents_in_footprint.csv`, `gdr_wellspring_in_footprint.csv`, `paleo_geothermal_regional.zip`, `lidar_scarp_features_u8.tif`, `geodawn_extensions_u8.tif`.

---

## 5. External Data & Official Verified Sources

| Source | Persistent Link | Role | Limitation |
|---|---|---|---|
| DrivenData competition overview/metric | https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/ | Confirms Tversky α0.2 β0.8, 300 m kernel, masking, EPSG:32611 | Never scraped (ToU); quota/receipts manual |
| Reference solution | https://github.com/drivendataorg/gems-prize-reference-solution (commit aebe92f) | Verifies float32 single-band [0,1] output | Loss ≠ evaluation kernel |
| USGS GeoDAWN | https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and DOI 10.5066/P93LGLVQ | Magnetic/radiometric channels, flight-block audit | Derived block raster audited, not official coords |
| OpenEI GDR1391 INGENIOUS | https://gdr.openei.org/submissions/1391 DOI 10.15121/1881483 | Paleo sinter, 2 m probe, wellsprings | Point anomalies may be lateral outflow, not fault |
| GBCGE INGENIOUS | https://gbcge.org/current-projects/ingenious/ | Project context | — |
| EPSG:32611 | https://epsg.io/32611 | UTM 11N 100 m | — |
| Tversky index | https://en.wikipedia.org/wiki/Tversky_index | Asymmetric weighting | — |
| Prize rules | https://docs.nlr.gov/docs/fy26osti/96647.pdf | Weekly cap, AI disclosure | Historical snapshot, not live quota |
| USGS QFaults | https://www.usgs.gov/programs/earthquake-hazards/faults | Catalogue bias reference | — |

---

## 6. Governance & Next Steps

- **Promotion blocker:** `gems-selector-v2-literal-quota-fail-closed` retains synthetic `registry-039` spacing-5 lattice (`99.87%` 3 px coverage) → any dotted submission fails `literal_all_entries_passed`. Separate quota verifier + replay certificate required (see `src/gems/selector.py`). No human-inspector exception.
- **This session:** Preregister H24-VENT, validate on `SegmentHoldout` (`gems-segment-pooled-v1`, 60,988 withheld, 95% CI), emit unique TIF, check `≤0.90` rank-correl. & `≤70%` 3 px overlap vs registry, label `HOLDOUT-DTI` vs `ORGANIZER-CONFIRMED`, budget ≤3 exp /2 h, negative is deliverable.
