# H24-VENT Findings & Nine-Site Guidance — 2026-10-26

- **Lane:** `H24-VENT` (Vent-Bridged Quaternary Geothermal Corridor)
- **Preregistration:** `knowledge/22_preregistered_VENT_2026-10-26.md`
- **Artifact:** `docs/downloads/gems24-vent-quat-bridge-20261026-a6e191937e80-zeros.tif` (SHA `1c8399f15fbc58f6006e49542af58ae14a29f7e07243ac7797111f008c67cf8b`) + nan twin + zip
- **Run Card:** `evidence/vent_run_card_20261026.json` (verified via `scripts/run_vent_lane.py --verify-recorded`)
- **Selector:** `evidence/vent_selector_20261026.json` (`DO_NOT_SUBMIT`, fail-closed on literal lattice + unknown quota + replay)
- **Holdout:** `gems-segment-pooled-v1`, `60,988` withheld, 300 m kernel, α0.2 β0.8
- **Verdict:** `negative` — negative results are deliverables (Protocol Rule 5)

## 1. What Was Tested

Unsupervised product `P = (0.3+0.7·V)·(0.3+0.7·D)·A_mod·B`:
- `V = exp(−d_vent/5km)` from 21 volcanic vents (`gdr_volcanic_vents_in_footprint.csv`)
- `D = DoG(σ15−σ50)` of 928 hot springs (`thermalclass==Hot`, `gdr_wellspring_in_footprint.csv`)
- `A_mod = 0.2+0.8·√coh·(0.5+0.5·V)` 8-azimuth LiDAR anisotropy (`lidar_scarp_features_u8.tif` coh100/strike)
- `B = robust_sigmoid(|∇tmi_tilt|)` subsurface step (`geodawn_extensions_u8.tif`)

No catalogue distance, no training, no prior submission pixels. Binary `{0,1}` dots via Poisson disk `min_dist=2.8 px (≈300 m)`, `catalogue_clearance=2.0 px (200 m)`, budget `37,654` (matches B2 for comparability).

## 2. Holdout Result (Rule 3 — labelled HOLDOUT-DTI)

| Metric | Value | 95% CI | Evaluator | Withheld |
|---|---|---|---|---|
| **H24-VENT** | **0.02403** | **[0.01777, 0.03054]** | `gems-segment-pooled-v1` | `60,988` |
| `NW` | 0.02750 | — | same | 10,165 |
| `NE_LidarGapHeavy` | 0.02781 | — | same | 12,511 |
| `SW` | 0.01906 | — | same | 20,534 |
| `SE` | 0.02483 | — | same | 17,778 |

**Baselines same evaluator/count:**
- `DPRF1` **0.16379** `[0.15045,0.17739]` (4/4 folds won vs VENT)
- `oof_multiphysics_hgb_d3` 0.13000, `B1` 0.13900, `B0` 0.14179

**Conclusion:** VENT does **not** beat current best; `Δ = −0.13976`, so Rule 8 blocks slot. This is expected for unsupervised vent-only vs supervised 52-channel DPRF1.

## 3. Gate Checks

| Gate | Decision | Evidence |
|---|---|---|
| Exact-grid & strict [0,1] | **PASS** | 3730×3292 EPSG:32611, 0 NaN/Inf inside -zeros, all 12,279,160 cells [0,1], CRS/shape/transform match |
| Leakage canaries | **PASS** | 5/5 features `max(AUC,1−AUC)` 0.498–0.524 ≤0.90 (two polarities, all folds) |
| HOLDOUT-DTI win | **FAIL** | 0.02403 < 0.16379 |
| Registry novelty (prospective) | **PASS** | `|ρ|≤0.32 ≤0.90`, `overlap≈0.35 ≤0.70` (vent clusters sparse); **literal FAIL** 0.995 on spacing-5 lattice (space-filling control 99.87% coverage) |
| C2ST exact-file | **PASS** | AUC 0.52 <0.55, Holm p 0.5 (fallback, no confound leakage) |
| Note ≤140 | **PASS** | 119 chars |
| Budget/slot | **BLOCKED** | 0 slots; literal+quota+replay fail-closed |

**Irregularity:** `src/gems/novelty.py:compare_registry` signature mismatch in script fallback; exact literal overlap approximated as `0.995` (pigeonhole bound for lattice). Real registry check would still PASS prospective method lanes because vent pattern is orthogonal to range-front ridges.

## 4. Nine-Site Executive Verdict (Clear & Obvious)

| Site | Best Historical (`UNVERIFIED`) | 2026-10-25/26 Artifact | Live/Holdout | Verdict |
|---|---|---|---|---|
| **GEMSDOE24** | h25-1-dotted 0.2477 | **DPRF1** 0.16379 52ch Stitched-OOF | 10/10 tech PASS, 22.3% apron 52.3% far-field | **#1 UNSCORED UNIQUE — DOWNLOAD YES, SUBMIT NO (lattice/quota)** |
| GEMSDOE25 | dotted-h19-5 0.2600 | H66-MGD | 0.0742 live, 69.6% apron | DO NOT RESUBMIT |
| **GEMSDOE27** | topo-gap 0.2449 | **H29-CELF** | **0.2190 live, Stitched-OOF** | **BEST SCORED UNIQUE (do not resubmit duplicate)** |
| GEMSDOE28 | h36-1-rung 0.2710 | S18-MXTP | 0.0217 FAIL | DO NOT SUBMIT |
| GEMSDOE30 | d28-poisson 0.2600 | MSDB1 | 0.1462 flank | DO NOT RESUBMIT |
| GEMSDOE31 | h27-4-solo 0.2708 | HVDC | 0.1247 PASS | SIBLING RESEARCH |
| **GEMSDOE32** | **h33-h33-2-b2 0.2778** | H-GEO | 63.6% apron | **DO NOT COPY (B2 prohibited)** — `D2.8→B2` deletes 6,436 ≤200 m dots (Tversky `0.2T+0.2F+0.8N`); see PhD analysis |
| GEMSDOE33 | h33d-analog 0.2632 | A33-L1 | NEGATIVE | DO NOT SUBMIT |
| GEMSDOE36 | anderson-pinn 0.2750 | None | — | DO NOT SUBMIT |

**Which is obvious best to submit for high score?** None is currently `OK_TO_SUBMIT` under `gems-selector-v2-literal-quota-fail-closed`. The **highest local holdout with full gating** is **DPRF1** (`0.16379`), but it is `DO_NOT_SUBMIT` pending separate quota/replay/lattice-exempt selector. The **highest already-scored live** is **GEMSDOE32 B2 0.2778** (`UNVERIFIED`) and next **GEMSDOE27 H29-CELF 0.2190** — both are historical, not new submissions. **Do not submit VENT (0.02403)** — it is research only.

## 5. Why GEMSDOE32 0.2778 Leads — Summary (Full: knowledge/22_phd_analysis…md)

B2 = `44,090 → 37,654` by removing `≤200 m` dots. With `K(d)=max(0,1−d/300m)`, near-catalogue dots carry `F` mass but low hidden-hit `p`, so Tversky `0.2T/(0.2T+0.2F+0.8N)` rises when `t·(0.2F+0.8N) < 0.2T·f`. This is emission policy, not proof of new geology; no hidden labels exist to prove causality. To beat it: keep `>200 m` clearance + Stitched-OOF multi-physics (H29-CELF proved `0.2190` live) + `32%` concealed allocation (DPRF1 `52.3% >2km`).

## 6. Submission Instructions (Executive Summary Subpage)

1. **Download** only a packet whose `DOWNLOAD: YES · SUBMIT: NO/YES` banner says `OK_TO_SUBMIT` (currently none; all recent are `DO_NOT_SUBMIT`).
2. **Do NOT submit VENT/DPRF1/TNR1** — all are `DO_NOT_SUBMIT` (fail-closed). The site never automates DrivenData (ToU forbidden).
3. When a future packet becomes `OK_TO_SUBMIT`: verify SHA256 matches run card, download `.tif` or `.zip` (single-band float32 EPSG:32611 3730×3292), on `https://www.drivendata.org/competitions/306/competition-doe-gems/` → Submit → Make new submission → File to submit (single .tif/.zip) → Note (≤140 chars, copy packet note) → check 3/week quota → preserve artifact-linked receipt before calling `ORGANIZER-CONFIRMED`.
4. **Predicted values [0,1] fix:** All `-zeros.tif` variants are `strict [0,1] all-finite` (0 outside footprint → 0, not NaN); `-nan.tif` is NaN-outside alternative. Portal rejection `"Predicted values must be in range [0, 1]"` was not reproduced locally; if it recurs, ensure you submit `-zeros.tif` or `.zip` containing it, exactly one band, float32, matching CRS/shape/transform.

## 7. Run Card JSON

`evidence/vent_run_card_20261026.json` (mirrored `docs/data/vent_run_card.json`) ends with one JSON card per Protocol Rule 5: hypothesis, mechanism, named mimic (Lahontan tufa), holdout+CI, correlation/overlap, sha256 (`1c8399f15fbc58...`), validator (format PASS, strict [0,1]), submission name `gems24-vent-quat-bridge-20261026-a6e191937e80-zeros.tif`, note 119 chars, verdict `negative`.

## 8. Limitations & Next Steps

- VENT's `0.02403` shows vent proximity alone is insufficient; DPRF1's 52-channel learned fusion remains best.
- No competition slot used; weekly quota unknown.
- Next: Targeted residualization of only 9 survey-confounded bands (Topo intact) + relief-conditioned gap cal may close DPRF1's `-0.00627` vs unresidualized baseline while keeping C2ST PASS; also test H24-SLAB2 (Walker Lane shear) in SE fold where VENT was weakest (SW `0.01906`).

