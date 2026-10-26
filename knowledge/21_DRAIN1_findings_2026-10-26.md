# H24-DRAIN1 Findings, PhD Leaderboard Diagnosis & Run-Card Attribution — 2026-10-26

## 1. Executive Summary

This session preregistered and executed **H24-DRAIN1** (knowledge/20_preregistered_DRAIN1_2026-10-26.md, scripts/run_drain_lane.py, evidence/drain1_run_card_20261025.json), a fully label-free drainage-network deflection detector on the 100 m `det_elev` band. It is the first lane in this repository to target **concave valley** Hessian `max(λ_max)` (vs. all prior ridge-convex `max(−λ_min)`), profile-curvature knickpoints, and D8 aspect-deflection — orthogonal to LiDAR scarp, magnetic tilt, and hydrothermal channels used by `MTR1`/`SAHG1`/`RSHG1`/`GVC1`.

**Holdout result (gems-segment-pooled-v1, 60,988 withheld positives, 1.5 km collar, 10 km block bootstrap 1,999 draws, seed 20261025):**
- **H24-DRAIN1 HOLDOUT-DTI 0.06578** (95% CI [0.05847, 0.07322], pooled TPw 3734, FPw 36154, FNw 57253, 37,722 binary dots)
- vs. reconstructed `B1` OOF-Base-Submod **0.13899** (Δ −0.07322) and `GVC1` **0.14876** (Δ −0.08299) — **does not beat current best**
- vs. unsupervised heritage: `MTR1` 0.06441 (+0.00137), `CON` 0.06446 (+0.00132), `H-UNIQUE-03` 0.05384 (+0.01194), `ASPC` 0.08553 on 3 km bridge (not directly comparable). Modest gain over single-feature magnetic/RAD baselines but below supervised multi-physics.

**Gate summary (automated, zero human-inspector fallback):**
- Format/strict [0,1] **PASS** (both `-zeros.tif` and `-nan.tif` pass `check_variants`; zeros variant passes strict whole-array `((a>=0)&(a<=1)).all()`; 0 NaN inside footprint, 37,722 dots ≥300 m)
- Two-polarity leakage canary **PASS** (5/5 features: det_elev_source 0.4872, valley 0.5785, c_prof 0.5400, asp_grad 0.4621, drain_candidate 0.5024; worst 0.5785 ≪0.90)
- Prospective method-lane novelty **PASS** (50 unique rasters checked = 49 competing method + 1 spacing-5 lattice; surface max |ρ| 0.1237 ≤0.90, final-dot max |ρ| 0.1227 ≤0.90, final-dot max competing overlap **0.4518 ≤0.70 PASS**; literal spacing-5 lattice 1.0 >0.70 reported separately, as intended)
- Exact-file C2ST nuisance audit **FAIL** (labels AUC 0.4958 Holm p 0.625 not flagged; **candidate AUC 0.5864, null p95 0.5212, margin +0.0652, Holm p = 0.010 → flagged**; threshold Holm p ≤0.05 & AUC≥0.55 & margin≥0.02)
- Governance (unassigned lane, literal lattice retained, no selector) **BLOCKED**

**Verdict: DOWNLOAD: YES · SUBMIT: NO (DO_NOT_SUBMIT), `verdict: "negative"`**. Zero previous submission pixels copied (SHA distinct, pre-placement max |ρ| 0.1237). No weekly slot spent. Negative is a deliverable.

**Artifact (both variants produced, zeros passes strict portal check):**
- `docs/downloads/gems24-drain1-valley-knick-deflect-20261026-da704869289a-zeros.tif` (SHA-256 `99d884f7d5c258a4633f2eb7d2a522e7d2462ead0a5438b931b7af1ad29d225a`, 825,180 bytes, LZW)
- `docs/downloads/gems24-drain1-valley-knick-deflect-20261026-da704869289a-nan.tif` (SHA-256 `8b07d71835000be114ebcb0393291a44c4d2b9d6ff02c0b834c3fabdb9db6555`)
- `docs/downloads/gems24-drain1-valley-knick-deflect-20261026-da704869289a-nan.zip` (SHA-256 `d724ed83b19b53faecbe31bdd1adea1f5d4ad14802b17e2a49490b442903586f`)
- Note (98 chars, ≤140): `GEMS24 DRAIN1 | valley knick deflect | da704869289a | HOLDOUT-DTI 0.06578 | DO NOT SUBMIT`
- Run card: `evidence/drain1_run_card_20261025.json` + `docs/data/drain1_run_card.json`
- Download receipt: `docs/data/drain1_download.json`
- Preflight: `docs/downloads/gems24-drain1-valley-knick-deflect-20261026-da704869289a-zeros.preflight.json` (DO_NOT_SUBMIT, strict_range True)
- Checks: `docs/downloads/checks-gems24-drain1-valley-knick-deflect-20261026-da704869289a-zeros.json`

## 2. Why H33-B2 0.2778 is the highest among the nine priority sites — forensic & metric diagnosis

Priority-site table (owner-reported, not ORGANIZER-CONFIRMED; sources registry/priority_rasters.json + docs/downloads forensics; see knowledge/14_h33_analysis_2026-10-25.md for byte-level proof):

| Priority repo | Best artifact (owner-reported DTI) | DTI | Dots | Ancestry vs H19-5 group best (e27054cf) |
|---|---|---|---|---|
| GEMSDOE24 | h25-1-dotted-h19-5-d1-5 | 0.2477 | 60,069 | H19-5 Poisson d1.5 = 60k |
| GEMSDOE25 | dotted-h19-5-d2-8 | 0.2600 | 44,090 | H19-5 d2.8 = 44k |
| GEMSDOE27 | topo-gap-closure-t-v2-on-d1-5 | 0.2449 | ~60k? | gap-closure on d1.5 |
| GEMSDOE28 | h36-1-rung30-blind-r1 | 0.2710 | 37,660 | tip relay rung |
| GEMSDOE30 | d28-poisson300m-offcat-44090 | 0.2600 | 44,090 | = D2.8 |
| GEMSDOE31 | h27-4-solo-d28 | 0.2708 | 40,199 | D2.8 minus 3,891 within 1 px of catalogue |
| **GEMSDOE32** | **h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros** | **0.2778** | **37,654** | **D2.8 minus 6,436 within ≤2 px (≤200 m) of catalogue** |
| GEMSDOE33 | h33d-analog-tip-stepover-r30 | 0.2632 | ~? | analog tip stepover |
| GEMSDOE36 | anderson-geothermal-pinn-38854 | 0.2750 | 38,854 | PINN geothermal |

**Why H33 wins (plausible, not proven hidden-score causal):** Competition Tversky DTI denominator = 0.2TPw + 0.2FPw + 0.8N. H19-5 raw supervised probabilities peak within 100-200 m of mapped faults because 100 m DEM/gravity/mag gradients smooth across that scale. Emitting dots at d_cat ≤2 px wastes ~15% of 44k budget on 0.2·FPw while retaining little unique TPw (most hidden truth is >1.5 km from visible components in holdout). H33's catalogue clearance at 200 m plus Poisson d=2.8 (280 m min spacing) maximally reduces FPw clustering while the 300 m triangular kernel still allows 100-300 m near-misses to earn partial credit (TPw decays as 1−d/3 px). H31 (0.2708) at 1 px clearance is weaker; D2.8 (0.2600) with no clearance is weaker; H36 PINN (0.2750) at 0.0028 behind. The ordering is consistent with FPw reduction hypothesis but **byte ancestry alone does not prove hidden TP/FP**, because a removed dot carries unknown hidden truth credit. Also note 0.3195/0.4413 figures in brief conflict and carry no receipt; GEMSDOE32's 0.2778 remains owner-reported, not organizer-confirmed.

**Can we beat 0.2778?** On the frozen public holdout, the current best supervised multi-physics (GVC1 0.14876 vs OOF-Base 0.13899) shows orthogonal geology (vent+tilt+lineament) adds +0.00976 paired gain (CI [0.00075,0.01951], 3/4 folds) with C2ST pass. Holdout absolute DTI (~0.14) cannot be compared to leaderboard DTI (~0.27) because holdout thins to 20% density per quadrant (sparse regime) while leaderboard hidden truth is ~5× sparser; emission policy optimal density differs. What we can beat is **GVC1's holdout best** on same evaluator with same budget and same 60,988 withheld positives. Drainage is orthogonal (basin floors vs range fronts) and should diversify, but this unsupervised valley variant at 0.06578 fails to beat supervised. Next fusion should learn to **re-weight** valley vs ridge via supervised HGB with training-only nuisance residualization and terrain-conditioned LiDAR-gap calibration (RSHG2 idea: condition ~has_lidar tail on det_local_relief to avoid over-allocating flat SW).

## 3. DRAIN1 mechanism attribution vs baselines

Per-fold HOLDOUT-DTI (gems-segment-pooled-v1):

| Fold | DRAIN1 | GVC1 (for reference) | NE gap |
|---|---|---|---|
| NW | 0.06929 | 0.17362 | -0.104 |
| NE_LidarGapHeavy | 0.03966 | 0.16747 | -0.128 (worst) |
| SW | 0.08551 | 0.10867 | -0.023 |
| SE | 0.06037 | 0.16552 | -0.105 |

DRAIN improves only in SW flat valley (+ modest), but collapses in NE_LidarGapHeavy (0.039 vs 0.167) because valley detector fires on flat LiDAR-gap mountain pediments incorrectly while missing range-front scarps. The 96.4% support is near-full, but discriminant power is weak.

## 4. Leakage & C2ST diagnostics

- Two-polarity canary 5/5 PASS; worst valley 0.5785, well below 0.90.
- C2ST labels AUC 0.4958 (clean); candidate AUC 0.5864 flagged. Single-feature descriptives: slope_gate correlates with valley floors where roads/claims cluster (valley floors = infrastructure corridors). This mirrors SAHG1's 0.5826 failure before residualization. Training-only `NuisanceResidualizer` (road_m, claim_m, blocks) would likely reduce AUC below 0.55 as in RSHG1 (0.5088) and FUSE-RESID (0.4928). Unsupervised DRAIN has no residualizer; next supervised fusion should include it.

## 5. Novelty — independent computation confirmed

- Surface max |ρ| 0.1237 ≤0.90 PASS; final-dot max |ρ| 0.1227 PASS; final-dot competing overlap 0.4518 ≤0.70 PASS (low because valley dots are in basin interiors, not range fronts). Zero copied pixels; footprint SHA distinct.
- Literal spacing-5 lattice overlap 1.0 >0.70 flagged (every 37k subset overlaps 99.87% coverage lattice), reported separately via `separate_calibration_controls=True` without deleting comparator.

## 6. Limitations & next steps

1. **Unsupervised = weak discriminant:** Valley alone cannot learn that a 15 cm basin scarp with hydrothermal halo should outrank a 2 m range-front tufa bar. Supervised fusion needed.
2. **C2ST flagged:** Road/claim/block siting bias must be removed training-only, refit, re-audit.
3. **NE gap failure:** Valley fires on steep LiDAR-gap ranges; need relief-conditioned calibration (`det_local_relief`) to avoid flat-floor over-allocation in SW while preserving NE gap recall.
4. **Next:** Implement **H24-DRAIN-GVC fusion**: 30 base + 18 GVC + 2 drain (valley_n, c_prof_n) = 50 channels, 2-seed HGB ensemble (max_iter 220, max_leaf_nodes 31, l2 3.0) with 20 km isotonic calibration, submodular allocation (250 m), training-only `NuisanceResidualizer` (100% as in GVC1-Resid) and regime-conditioned LiDAR-gap tail matching. Expect +0.005–0.015 over GVC1 if drain adds orthogonal basin recall without harming range-front precision.

## 7. Sources, AI disclosure & verification

- DrivenData pages: https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/ and https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/
- GDR 1391: https://gdr.openei.org/submissions/1391
- GeoDAWN DOI: https://doi.org/10.5066/P93LGLVQ
- USGS 3DEP: https://www.usgs.gov/3d-elevation-program/data-tools
- Reference solution: https://github.com/drivendataorg/gems-prize-reference-solution
- EPSG:32611: https://epsg.io/32611
- Tversky: https://en.wikipedia.org/wiki/Tversky_index
- AI disclosure: Arena.ai Agent Mode assisted code, preregistered holdout, exact-file validation, docs; zero DrivenData automation or upload.

Verify:
```
.venv/bin/python scripts/run_drain_lane.py --verify
.venv/bin/python scripts/preflight_submission.py docs/downloads/gems24-drain1-valley-knick-deflect-20261026-da704869289a-zeros.tif --run-card evidence/drain1_run_card_20261025.json
.venv/bin/pytest -q
```

No new weekly slot was spent. All numbers are HOLDOUT-DTI, not ORGANIZER-CONFIRMED.

