# Preregistration — H24-PAIR1 (2026-10-26, this session)

**Lane (single method, Parallel-Run Protocol Rule 1):** object-level
**paired opposite-facing scarp + crest/base dipole operators** computed from the
committed 100 m LiDAR scarp cache, fused by one HistGradientBoosting model over the
cached physical stack. No prior submission pixels are read. No catalogue-distance
feature is used (catalogue enters only as labels, pixel-exact masking, and the
emission clearance — exactly as in every prior lane).

## Why this is not a rerun of a stopped lane
- SAHG1/OJ1 used *pointwise* LiDAR channels / orientation junctions. PAIR1 uses
  *two-sided spatial pairing*: `min(upface(x), downface(x+o·d))` over 8 azimuths ×
  offsets {1,2,3} px (and the mirror), plus a crest→base dipole
  `min(lapneg(x), lappos(x+o·d))`, o∈{1,2}. This exact operator family is listed as
  prospective Rank 1 in `docs/review-20261026.md` and is not implemented in any
  `src/gems/*.py` module (verified by source inspection this session).
- Mechanism: narrow intrabasin **grabens** preserve paired low-relief scarps facing
  each other; the USGS/INGENIOUS catalogue is biased to single range-front scarps,
  so paired-scarp structures under thin alluvium are plausibly under-mapped.
- **Named non-fault mimics:** fluvial terrace pairs, irrigation banks/levees,
  road cuts, Lake Lahontan shoreline ridges.

## Data (all committed, no new fetch; sandbox cannot reach other hosts)
- `data/external/lidar_scarp_features_u8.tif` (12 bands, USGS 3DEP-derived)
- `data/external/geodawn_rad_u8.tif` (K, Th, U, TC; USGS GeoDAWN DOI 10.5066/P93LGLVQ)
- `data/external/geodawn_extensions_u8.tif` (ThK, UK, UTh, TMI_up150)
- Labels/footprint: `data/bridge/existing_faults.tif`, `data/bridge/sample_submission.tif`
- **Known limitation:** the 419 MB competition `training_features.tif` (DPRF1's 30
  base channels) is gitignored and absent in this checkout; DPRF1's recorded
  0.16379 therefore cannot be replayed here. PAIR1's stack is the 20 cached bands
  + 4 new operators. This is disclosed, not hidden.

## Locked protocol
- Evaluator: shared `gems.holdout.SegmentHoldout(buffer_px=15)`,
  `gems-segment-pooled-v1`, pooled DTI α=0.2 β=0.8, 300 m triangular kernel,
  whole components hidden, visible-only catalogue, pixel-exact masking.
- Exp 1 (BASE): HGB on 21 base channels. Exp 2 (PAIR1): + 4 pair/dipole operators.
  Exp 3 (emission ablation): PAIR1 surface, catalogue clearance >3 px vs >2 px.
  All three reported; selection bias from Exp 3 disclosed.
- Emission (Exp 1/2): `gems.emission.priority_poisson(min_dist=3.0)`,
  eligible = valid & dist(visible) > 2 px, per-fold budget
  `round(37654 · fold_offcat / total_offcat)` (identical rule to DPRF1).
- HGB: `max_iter=190, learning_rate=0.055, max_leaf_nodes=31, min_samples_leaf=80,
  l2_regularization=2.5` (same as DPRF1); pos = train∩visible, neg = train pixels
  ≥9 px from visible, sampled ≤3× pos, seed 20261026.
- Canary (Rule 4): every feature alone via `SegmentHoldout.canary`; AUC>0.90 ⇒ stop.
- Novelty (Rule 1): surface Spearman |ρ|≤0.90 and final-dot 3-px overlap ≤0.70 vs
  every locally available registry raster (incl. DPRF1, H19-5, dotted D1.5/D2.8,
  calibration lattice reported separately per prospective policy).
- Final raster: quadrant-stitched OOF surface → 37,654 dots, clearance >2 px from
  full catalogue (or Exp-3 winner), via `gems.submission.write_submission`
  (zeros + nan twins), validated by `gems.submission.check_variants`.
- Verdict rule: `promote` requires PAIR1 paired-Δ CI > 0 vs BASE **and** pooled
  HOLDOUT-DTI > recorded DPRF1 0.16379 **and** novelty/format pass. Otherwise
  `negative` (a deliverable). Promotion to a real slot remains a separate
  selector step (Rule 6) — this session spends **no slot**.
- Budget: ≤3 experiments (this preregistration defines all three).
