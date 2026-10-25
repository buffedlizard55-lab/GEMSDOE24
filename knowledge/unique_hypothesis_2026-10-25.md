# Preregistration — H-UNIQUE-01 (2026-10-25)

## Hypothesis

**Blind hydrothermal-conduit detection via LiDAR scarp × radiometric potassium concordance.**

Geothermal systems localise at blind faults where hydrothermal K-enrichment
(illite/adularia alteration) coincides with subtle fault scarps expressible in
2 m LiDAR derivatives. The USGS / INGENIOUS catalogue maps only well-expressed,
catalogued traces. This detector does NOT condition on any catalogue fault to
build its score surface, so it can detect concealed / blind conduits absent
from the catalogue. Catalogue faults are used ONLY for holdout masking and
evaluation, never for feature construction.

## Layers

| Source | File | Channels used |
|---|---|---|
| LiDAR scarp derivatives (3DEP-derived) | `data/external/lidar_scarp_features_u8.tif` | band 1 `ex_max` (max slope excess), band 3 `step_max` (max step), band 9 `relief` |
| GeoDAWN radiometrics (USGS, DOI 10.5066/P93LGLVQ) | `data/external/geodawn_rad_u8.tif` | band 1 `K` (potassium, alteration halo proxy) |
| GeoDAWN extensions (contractor ratios) | `data/external/geodawn_extensions_u8.tif` | channel 1 `ThK` (low Th/K = argillic overprint proxy) |

All three rasters are hash-pinned and grid-aligned to the competition template
(EPSG:32611, 3730 × 3292, 100 m, origin 243350 / 4508550).

## Score surface

`score = norm01(ex_max) × norm01(step_max) × (0.5 + 0.5 × norm01(relief)) × norm01(K) × (1 − norm01(ThK))`

Each channel is normalised to [0,1] over its 2nd–98th percentile range on its
valid pixels; invalid pixels are zeroed. The surface is zeroed outside the
footprint. Support = footprint ∩ LiDAR-valid ∩ K>0 ∩ ThK>0.

## Non-fault mimic (named)

K-rich alluvial-fan toes with steep slopes can produce a false scarp + K
coincidence. This is the named alternative process that could mimic the signal.

## Evaluation

* SegmentHoldout (whole-component hide-and-recover, buffer 15 px = 1.5 km,
  four spatial quadrants, pooled DTI, alpha 0.2, beta 0.8, 300 m triangular
  kernel, 100 m tiles, 1 999 bootstrap draws).
* Budget fraction 0.0073 of valid fold pixels, min_dist 3 px, priority_poisson
  dots from support ∩ fold-valid ∩ ~visible.
* Final dots: support ∩ ~catalogue, same budget and spacing.

## Leakage canary

Each channel (scarps_ex_max, k_anomaly, alteration_thk) and the combined score
surface tested alone on the holdout. AUC > 0.90 (either polarity) = leakage
until proven otherwise.

## Novelty gate

Pre-placement and final-dot comparison against the 46-entry priority registry:
absolute Spearman rank < 0.90 AND candidate-dots-within-3-px overlap < 0.70
versus every competing method lane. Synthetic calibration controls reported
separately, never removed.

## Promotion rule

Promote to `ok_to_submit=True` only if ALL of:
1. Exact-grid format validation passes (CRS/shape/transform, float32, single band).
2. Strict whole-array [0,1] diagnostic passes (finite everywhere, zeros outside).
3. Novelty gate passes (< 0.90 rank, < 70% overlap vs all registry rasters).
4. Leakage canary passes (no channel AUC > 0.90).
5. Holdout DTI beats the current comparable best (0.13000 OOF multiphysics
   baseline, `gems-segment-pooled-v1`).

Otherwise verdict = `negative`, which is a deliverable.

## Outputs

* `docs/downloads/24gems-doer-blind-conduit-<date>-<content_id>-zeros.tif`
  (zeros outside, finite [0,1] everywhere — portal-range compatible)
* `docs/downloads/checks-*.json` (exact-file validator)
* `docs/downloads/preflight-*.json` (fail-closed preflight)
* `docs/downloads/note-*.txt` (<= 140 characters)
* `evidence/unique_experiment.json` + `docs/data/unique_run_card.json` (run card)

## Budget

Experiment 1 of 3; session cap 2 hours. No DrivenData access; the agent never
uploads. ORGANIZER-CONFIRMED requires an artifact-linked submission-page receipt.
