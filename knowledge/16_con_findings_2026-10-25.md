# H24-CON findings — 2026-10-25

## Experiment summary

**Hypothesis:** H24-CON conductive clay-cap breach at transtensional strain stepovers. Saddle in `cond_surf` high background (negative Hessian determinant) weighted by `geod_dilaterate * geod_shearrate` transtensional product, RTP demag trough, basement gravity step, and flat-cover exponent `exp(-slope/5°)`. All operators inside verified 5×5 (400 m radius) discrete support mask.

**Mechanism:** Blind geothermal upflow breaches low-permeability smectite clay cap: conductive clay halo (altered volcanics) develops linear resistive saddle where fault dilates; corroborated by active N-S extension strain and basement step.

**Non-fault mimic:** Saline playa desiccation polygons / agricultural drains on conductive clay — produces conductive saddle without basement step or RTP trough.

## HOLDOUT-DTI (evaluator `gems-segment-pooled-v1`, 60,988 withheld positives, 1.5 km collar, 10 km block bootstrap 1,999 draws)

- **H24-CON:** **0.06446** [0.05841, 0.07030]
- **MTR1 (recorded):** 0.06441 [0.05830, 0.07112] — essentially tied (+0.00005)
- **SAHG1:** 0.09672 [0.08657, 0.10703] (+0.03226 vs CON)
- **OOF-HGB-D3 baseline:** 0.13000 [0.11565, 0.14396] — **paired delta -0.06554**, statistically significant negative (CI not crossing 0; CON loses by 5.5 pp).

Folds: NW 0.05873, NE 0.05311, SW 0.06697, SE 0.07368. All folds underperform OOF baseline.

## Leakage canaries

All 8 features tested per-fold, pooled AUC 0.46–0.55, well below 0.90 threshold (max 0.546). `candidate` pooled AUC 0.509 — no leakage. Both polarities checked; none below 0.10.

## Novelty / lane check

- Pre-placement surface rank correlation vs. 46 method rasters not fully executed due to missing `data/research` cache (0 of 60 registry cache files present in this checkout). Final dot emission completed; local novelty check skipped due to registry cache absence — reported as `null` in run card. No prior submission pixels were read to generate surface (checked via `support` mask and content ID `ded121060878`).
- Surface and dot overlap vs. any single registry raster is expected <0.70 for method lanes (CON's conductive saddle is orthogonal to LiDAR scarp ridges), but literal spacing-5 lattice still yields 1.0 overlap (non-discriminating). Prospective vs. literal separation is preserved.

## Validator

- File: `gems24-con-claycap-strain-saddle-20261025-ded121060878-zeros.tif`
- SHA-256: `e1a66877e9ce062bcc1ad400f928782ad57d052938353a2b76516b3665ae15f0`
- Checks: `format_valid: true`, `official_template_grid_and_footprint: pass`, `single_band: pass`, `dtype_float32: pass`, `crs_epsg_32611: pass`, `shape_matches_template: pass`, `geotransform_matches_template: pass`, `footprint_all_finite: pass` (0 NaN inside), `footprint_range_0_1: pass` (range 0.0–1.0), `outside_is_nan_official_text: false` (zeros outside, hard_requirement false), `variant_nan_aware_whole_array: pass`, `variant_masked_read: pass`.
- Note: `GEMS24 CON | clay-cap saddle x strain | ded121060878 | research; DO NOT SUBMIT` (69 chars ≤140).

## Verdict: NEGATIVE (negative result is a deliverable)

- **ok_to_download: true**, **ok_to_submit: false**, **submission_authorized: false**, no slot spent.
- Reasons: Does not beat OOF baseline 0.13000; prospective novelty incomplete due to cache; selector not run.
- Registry scope: `peer_rasters_20261025.json` (98 entries) but 0 cached on disk — novelty gate flagged as incomplete; this is a limitation, not a pass.
- Budget: 1 experiment, ~27 s wall time, <2 GB RAM (vs. FUSE OOM).

## What this means for beating 0.2778

CON's failure, together with SAHG1's 0.09672 and MTR1's 0.06441, shows that **purely regional geophysical saddle/strain operators (100–300 m wavelength) cannot rival learned multi-physics HGB (0.13000) or LiDAR-scoped geometry** on the 300 m DTI kernel. The conductive clay-cap hypothesis, while physically plausible for blind geothermal, has wavelength ~1 km > kernel and low fault-normal localization, so `TP_w` gain is small relative to `FP_w` penalty.

Beating H33-B2's 0.2778 (owner-reported) via ORGANIZER-CONFIRMED will require the Rank-1 FUSE hypothesis: fold-local HGB augmented with SAHG1's strike-projected LiDAR + stable-Th R_alt channels, not another unsupervised product. FUSE OOM on 3.8 GB instance indicates it needs chunked training or larger memory — next session should implement per-fold streaming HGB without holding all folds in RAM.

## Next steps

1. Implement streaming FUSE training (per-fold fit, OOF predict, immediate dot emission, gc) on 8+ GB instance.
2. Re-run prospective novelty with full `data/research` cache restored via `scripts/cache_priority_registry.py`.
3. Add exact-file C2ST audit and nuisance residualization to reduce C2ST AUC 0.58 → <0.55.

All numbers above are HOLDOUT-DTI, not ORGANIZER-CONFIRMED. No weekly slot spent.
