# H24-CON findings — 2026-10-25

> Review correction: physical interpretation below is a hypothesis, not verified
> clay-cap or vent detection. Missing registry comparisons are UNKNOWN, never a
> uniqueness pass. The code assumes slope units and computes several global
> normalizations; this run is not promotion evidence.

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

The recorded configurations underperformed the comparable baseline; this does
not establish that every regional operator fails or that FUSE must win. Hidden
truth components and a receipt-linked GEMSDOE32 score are unavailable. The
conductive clay-cap interpretation and its spatial wavelength require independent
physical verification. FUSE's reported memory failure is an engineering blocker,
not a scientific result or evidence of superiority.

## Next steps

1. Implement streaming FUSE training (per-fold fit, OOF predict, immediate dot emission, gc) on 8+ GB instance.
2. Re-run prospective novelty with full `data/research` cache restored via `scripts/cache_priority_registry.py`.
3. Add exact-file C2ST audit and nuisance residualization to reduce C2ST AUC 0.58 → <0.55.

Only explicitly labeled holdout results are HOLDOUT-DTI; AUC, geometry, hashes, and runtime are diagnostics, not scores. No result here is ORGANIZER-CONFIRMED. No weekly slot spent.
