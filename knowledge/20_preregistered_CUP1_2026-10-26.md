# Preregistration: H24-CUP1 — compositional radiometric fronts + upward-continuation
# trough persistence (2026-10-26)

Written before implementing or evaluating this experiment. Budget: **at most 3 experiments
or 2 hours** from session start (2026-10-26). This document preregisters **one** fixed
primary experiment (Rank 1) and one preregistered fallback (Rank 2, only if Rank 1 fails
a gate and budget remains). No competition upload; promotion to a weekly slot is a
separate selector step outside this session.

## Lane and scope (IR retained, not hidden)

The brief's "single method paragraph" is absent, as in prior sessions
(IR-20261025-MISSING-LANE). Provisional narrow lane reserved here, before any result:
**label-free compositional (log-ratio-style contractor K/Th/U ratio-grid) fronts at
100–800 m scales, plus paired magnetic-trough persistence between the shallow RTP field
and the contractor TMI upward-continued to 150 m, supplied as channels to the shared
fold-local calibrated HGB and emitted with the shared allocator.** No prior submission
pixels, catalogue-distance habitat features, fault tips, or prune-and-augment operators
enter the detector. Stopped lanes (MTR1, ASPC, SAHG1, CON, OJ1, FUSE, GVC1, RSHG1,
UNIQUE01–03) are not rerun or retuned; their shared tools are reused unchanged.

## Why GEMSDOE32 H33-B2 (0.2778, OWNER-REPORTED, UNVERIFIED) leads the group — forensic basis

Local artifact geometry (`evidence/priority_review_20261025.json`,
`knowledge/14_h33_analysis_2026-10-25.md`): H33-B2's 37,654 dots are exactly the
40,199-dot GEMSDOE28/31 H27-4 set minus the 2,545 dots within 2 px (200 m) of the
supplied catalogue — **zero new coordinates, no new detector**. The owner-reported
ladder on the same ancestry (continuous ridge 0.1922 → dotted 0.2477/0.2600 →
solo-d28 0.2708 → catalogue-clearance 0.2778) is therefore an **emission-policy**
result: under DTI = TPw/(TPw + 0.2·FPw + 0.8·FNw) with a 300 m triangular kernel,
sparse dots keep most kernel credit per truth pixel while emitting far less FP mass,
and dots on the catalogued apron earn no hidden-truth credit (organizer masks known
faults) yet still risk FP mass. Hidden TP/FP of the removed dots are unknown, so
"pure FP savings" is a testable explanation, not a proven cause. **Implication:** to
beat 0.2778 a candidate needs (a) the same class of emission (sparse, ≈37.7k dots,
≥200 m off-catalogue — already the shared `submodular_dti_allocate` defaults:
budget 37,654, spacing 2.5 px, clearance 2.0 px), applied to (b) a **better ranking
surface** than the H19-5/H27-4 ridge family, and (c) surface mass where the catalogue
is incomplete. This preregistration tests (b)/(c) with new physical channels; it
forecasts no score.

## Ranked geological hypotheses (before implementation)

Expected benefit is qualitative and uncertain, NOT a projected score.

| Rank | Layers & physical signature | Why an omitted (not catalogued) fault? | Difference from implemented repo methods | Non-fault mimic | Cost / new data |
|---|---|---|---|---|---|
| **1 — SELECTED (H24-CUP1)** | GeoDAWN contractor ratio grids ThK, UK, UTh + K/Th/U/TC (`geodawn_extensions_u8.tif`, `geodawn_rad_u8.tif`); RTP vs TMI_up150. Transforms: 100–300 m gradient fronts of each ratio grid; stability-gated front `|∇ThK|/(1+|∇UTh|/s)`; 500–800 m local contrasts; paired-trough response on TMI_up150 and the **persistence ratio** `T_up/(T_rtp+T_up+ε)`; deep–shallow residual gradient. Given as channels to shared fold-local HGB on base27+GVC18. | Hydrothermal K-metasomatism / U remobilisation along a **blind** fault changes the K–Th–U balance, producing a narrow compositional front that cross-cuts lithology; a deep-seated demagnetised fault zone survives 150 m upward continuation while surficial/cultural short-wave noise attenuates. Neither signature needs a scarp or a catalogue tip, so both can flag intra-basin faults photogeology missed. | GVC1 used two 2 km-scale (σ20) scalar contrasts (`k_loc−thk_loc`, UTh excess) and a σ20 shallow-demag scalar; SAHG1 one isotropic 9×9 alteration product; MTR1 a fixed unsupervised RTP-trough × ThK-depletion product (stopped — not rerun). CUP1 supplies **multi-scale ratio-grid fronts + a cross-scale persistence ratio as learned channels**, not a fixed product. | Transported arkosic sediment front / lithologic contact (radiometrics); magnetite-poor palaeochannel persisting with depth (magnetics). | Low–medium CPU; **no new data** — all layers already cached and hash-pinned. |
| 2 — fallback only | Relief-regime-stratified allocation: same CUP1 surface, budget split between high-/low-relief regimes by a fold-local visible-label density ratio fixed before seeing candidate results. | Catalogue completeness is relief-dependent; global top-k concentrates on already-mapped range fronts. | GVC1/RSHG1 allocate globally; RSHG1 calibrated by regime but did not stratify the dot budget. | Basin dots may simply be fan distributaries. | Low; judged first on SGMC sparse simulation (per AGENTS), dense pooled as non-inferiority. |
| 3 | LiDAR tip-damage: along-strike `d(coh100)/ds` drop × balanced curvature sign-flip (`lidar_scarp_features_u8.tif`). | Catalogue truncates at fan burial; tip damage extends beyond the mapped tip without using the tip as input. | Proposed in `knowledge/15` rank 3, never executed; distinct from SAHG1 amplitude/persistence. | Road-cut terminus, avulsion-lobe edge. | Low; cached. |
| 4 | Pure MTR2 operator: unsupervised paired-trough survival ratio RTP→TMI_up150. | Deep concealed alteration corridor. | CUP1 uses persistence only as HGB channels; pure operator is a different (weaker) claim. MTR1 remains stopped. | Long magnetite-poor lithologic strip. | Medium; cached. |
| 5 | DEM drainage-deflection network (100 m `det_elev` D8 bearings). | Buried cross-valley fault deflects drainage without a preserved scarp. | Network topology, not scarps/Hessians (SAHG1/RSHG1/OJ1). | Stream capture, lithologic boundary, ditch. | High; 100 m DEM limits channels. Finer DEM would need USGS 3DEP (https://www.usgs.gov/3d-elevation-program/data-tools) — host not allowlisted here, obtainability **not verified**, so not proposed as viable this session. |

## Fixed experiment spec (Rank 1; no tuning after results)

1. **Inputs (hash-verified before use):** `data/prepared/features.npy` (30 ch, from
   `scripts/prepare_data.py`), GVC1 18 ch rebuilt by shared `gems.gvc.build_gvc1_features`,
   `geodawn_rad_u8.tif`, `geodawn_extensions_u8.tif`, bridge labels/template.
   Detector feature matrix = the full 30-column prepared base memmap exactly as the
   GVC1 pipeline passes it to `fit_predict_calibrated_hgb` (its 48-channel canary =
   30 base + 18 GVC; `features.json`'s legacy `base_count: 27` field is not used to
   slice columns) + GVC18 + CUP channels below.
   Matched baseline **B-GVC** = same base + GVC18, same HGB, same allocator — isolates
   the CUP increment with a paired comparison. (B-GVC is a fresh same-protocol
   reconstruction for pairing; the frozen GVC1 receipt HOLDOUT-DTI 0.14876 stays the
   recorded current best and is not rewritten.)
2. **CUP channels** (label-free; U8 rank grids dequantised as q/255, 0=nodata;
   nearest-fill only inside transform neighbourhoods; values NaN outside valid support,
   eroded by each transform's receptive field):
   ratio fronts `cup_thk_grad`, `cup_uk_grad`, `cup_uth_grad` (|∇| of σ1 grid);
   `cup_comp_front = cup_thk_grad / (1 + cup_uth_grad / median_fp(cup_uth_grad))`;
   local contrasts at σ5/σ8 normalised by local SD: `cup_k_loc5`, `cup_th_loc5`,
   `cup_u_loc5`, `cup_thk_loc8`, `cup_uk_loc8`; `cup_tc_grad`;
   `cup_up150_grad` (|∇| σ1.5 of TMI_up150); `cup_up150_loc8`;
   paired troughs `cup_trough_up`, and `cup_trough_rtp` via shared
   `gems.magnetic_trough.paired_trough`; `cup_trough_persist = T_up/(T_rtp+T_up+1e-6)`;
   `cup_deep_resid_grad = |∇(robust_z(TMI_up150) − robust_z(RTP))|` at σ3.
3. **Holdout:** shared `SegmentHoldout(buffer_px=15)` (`gems-segment-pooled-v1`):
   whole 8-connected components hidden everywhere, visible masked pixel-exactly,
   pooled TPw/FPw/FNw (α0.2 β0.8, 300 m), 95% CI 1,999-draw 10 km block bootstrap,
   report withheld positives. HGB identical to `gems.gvc.fit_predict_calibrated_hgb`
   (2 seeds, 220 iter, isotonic calibration on spatial blocks), negatives ≥900 m from
   **visible** faults only.
4. **Canaries:** every raw/derived channel alone (base+GVC+CUP), both polarities,
   shared `SegmentHoldout.canary`; AUC >0.90 (either polarity) = halt as leakage.
5. **Emission:** shared `gems.gvc.submodular_dti_allocate`, budget 37,654 full-grid
   (fold budgets pro-rated by off-catalogue area exactly as GVC1), spacing 2.5 px,
   catalogue clearance 2.0 px from **fold-visible** faults (full model: full catalogue).
6. **Novelty (stop rule):** shared `novelty.compare_prospective_registry` on the OOF
   surface before placement and on final dots, against all pinned registry entries
   (`registry/priority_rasters.json` + local peer downloads incl. GVC1). Exceeding
   |ρ|>0.90 on any entry, or >70% of dots within 3 px of any **competing method**
   raster, = duplicate → log and stop. Literal all-entry result (incl. spacing-5
   calibration lattice) reported separately and never used to delete a comparator.
7. **Secondary live-proxy (diagnostic, not a gate):** SGMC off-catalogue sparse truth
   (`derived_sgmc_faults_100m_u8.tif`, >10 px from catalogue) DTI for candidate dots,
   B-GVC dots and the frozen GVC1 file, as-emitted. Reported as SGMC-SPARSE-DTI,
   never as a leaderboard estimate.
8. **Writer/validator:** shared `scripts/submission_writer.py`, both outside variants;
   primary download = zeros-outside (strict whole-array finite [0,1], answering the
   portal "Predicted values must be in range [0, 1]" rejection — NaN-outside twin is
   the official-text variant). Values clipped to [0,1] before writing; re-read and
   verify CRS/shape/transform vs pinned template.
9. **Nuisance audit:** exact-file spatial C2ST (roads, closed claims, 4 derived
   acquisition blocks — derived, not official coordinates) via shared `gems.c2s2`,
   labels first, same effect rule as GVC1 (Holm p≤.05 AND AUC≥.55 AND margin≥.02 flags).
10. **Promotion gates (all required for SUBMIT YES):** canary pass; paired
    CUP1−B-GVC 95% CI strictly >0 **and** CUP1 pooled HOLDOUT-DTI > recorded 0.14876;
    novelty pass both stages; C2ST pass; format pass. Even then the run card records
    `verdict: promote` only as *selector-eligible*: an independent selector/quota
    certificate is not implemented and weekly quota is unknown, so site wording will
    say "OK TO SUBMIT" only if every technical gate passes, with the selector caveat
    printed next to the download. Otherwise DOWNLOAD YES / SUBMIT NO, verdict negative.
11. **Run card:** one JSON with hypothesis, mechanism, named mimic, HOLDOUT-DTI+CI
    (evaluator, withheld positives), paired delta, correlation/overlap vs registry,
    raster SHA-256, validator output, unique filename + ≤140-char note, verdict.

No DrivenData automation, no credentials, no human-inspector fallback. Fault recovery
is the benchmark target; no geothermal-vent discovery is claimed from a fault raster.
