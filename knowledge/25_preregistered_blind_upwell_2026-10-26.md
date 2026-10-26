# Preregistration — H24-BLIND-UPWELL (2026-10-26)

**Session lane:** single method — concealed-fault geothermal upwelling detector. One experiment this session (budget: max 3 experiments / 2 hours). No DrivenData access; the agent never uploads. ORGANIZER-CONFIRMED requires an artifact-linked submission-page receipt.

## 3–5 candidate hypotheses (ranked by expected DTI improvement vs implementation cost)

### H1 — Blind upwelling: LiDAR short-wavelength steepness × radiometric K × low Th/K × shallow thermal (catalogue-independent scoring, kernel-cover sparse emission)

**Layers:**
- `data/external/lidar_scarp_features_u8.tif` band 2 `ex_mean` — mean short-wavelength slope excess (subtle fault flexure/curvature; no surface scarp required). Quantisation: sqrt, xmax 0.3 m/m (per lidar_scarp_features.json).
- `data/external/geodawn_rad_u8.tif` band 1 `K` — potassium, illite/adularia alteration halo proxy (USGS GeoDAWN, DOI 10.5066/P93LGLVQ; ScienceBase 657e1d85d34e23d3533209f7).
- `data/external/geodawn_extensions_u8.tif` band 1 `ThK` — contractor Th/Potassium ratio; low Th/K = argillic overprint proxy.
- `data/external/gdr_volcanic_vents_in_footprint.csv` + `data/external/gdr_wellspring_in_footprint.csv` — 21 volcanic vents and 8,718 springs with temperature (INGENIOUS/OpenEI GDR submission 1391), rasterized and triangular-kernel-convolved (R=300 m) to a shallow-thermal anomaly surface. Vents sit mean 3.2 km from known faults → candidate blind systems.

**Physical signature:** Blind faults hosting geothermal upwelling express subtle curvature flexure (ex_mean), K enrichment, low Th/K (argillic), and shallow thermal anomalies WITHOUT a mappable surface trace. These are therefore MISSING from the USGS/INGENIOUS catalogue (which maps only well-expressed traces). Scoring surface is fully catalogue-independent; catalogue faults are used ONLY for holdout masking/evaluation.

**Named non-fault mimic:** K-rich alluvial fans / paleochannels with shallow warm groundwater produce steep + K + warm coincidence without a fault.

**Difference from everything in this repo:** H-UNIQUE-01 used scarps (ex_max/step_max = surface expression) and dotted near catalogue faults → 99.85% final-dot overlap failure. DPRF1/GVC1 condition heavily on catalogue-proximal aprons + submodular allocation. MTR1 used magnetic trough + ThK. No lane combines curvature flexure + thermal (vent/spring) + K + ThK with catalogue-independent scoring and emission excluded from catalogue pixels. The 2m temperature/vent/spring layers are not used as a raster layer in any existing lane.

**Expected DTI improvement:** targets far-field blind faults that catalogue-conditioned surfaces (DPRF1, 0.16379) under-sample; kernel-cover emission retains more TP credit per FP pixel than rank Poisson. Cost: LOW (all data present; no new external download).

### H2 — Radiometric front × curvature hinge (catalogue-independent)

**Layers:** `geodawn_rad` K/Th/U gradient magnitude (edge detection) × `lidar_scarp_features` band 4 `lapneg_max` (crest convexity) × band 5 `lappos_max` (base concavity).

**Physical signature:** alteration fronts and fault-related curvature hinges at concealed faults; edge transforms highlight discontinuities not trace-mapped in the catalogue.

**Named non-fault mimic:** lithological contacts and terrace edges.

**Difference from repo:** no existing lane uses radiometric edge × curvature hinge. Cost: LOW (data present; gradient computed on committed grids).

**Expected DTI improvement:** moderate; front/hinge signal is weaker than direct thermal upwelling. Ranked #2.

### H3 — Spring/vent density kernel × LiDAR step (catalogue-independent)

**Layers:** triangular-kernel density of vents/springs (R=300 m) × `lidar_scarp_features` band 3 `step_max`.

**Physical signature:** spring/vent clusters mark concealed fault-controlled upwelling; slope steps mark subtle displacement.

**Named non-fault mimic:** spring-fed channels and terrace risers.

**Difference from repo:** spring/vent density not yet used as a scoring layer. Cost: LOW. Ranked #3 (vents are sparse: 21 points).

### H4 — TMI_up150 magnetic low × K alteration (catalogue-independent)

**Layers:** `geodawn_extensions` band 4 `TMI_up150` (upward-continued magnetic) × `geodawn_rad` band 1 `K`.

**Physical signature:** blind faults destroy magnetite (magnetic low) with K alteration halo — concealed systems.

**Named non-fault mimic:** lithological magnetic lows unrelated to geothermal flow.

**Difference from repo:** MTR1 used RTP trough + ThK (different magnetic channel, different ratio). Cost: LOW. Ranked #4 (magnetic lows are a weaker, broader geothermal proxy than direct thermal).

### H5 — INSAR/InSAR deformation (DEFERRED — external data not obtainable from this sandbox)

**Layers:** line-of-sight deformation rate × coherence.

**Physical signature:** fault creep / geothermal inflation at concealed faults.

**Named non-fault mimic:** groundwater-level change, aquifer compaction.

**Why deferred:** NASA OPERA / InSAR products are not reachable from this sandbox (only github.com and pypi.org allowlisted). No specific free official source verified obtainable within budget. Explicitly NOT implemented this session.

## Top candidate: H1 (blind upwelling)

Selected for implementation because it (a) targets faults missing from the catalogue via concealed-signature layers no lane combines, (b) uses only committed, hash-pinned, grid-aligned data (no external download), (c) is cheap to run and validate on SegmentHoldout, and (d) its emission policy (exclude catalogue pixels from dots) directly addresses the novelty failure mode that stopped H-UNIQUE-01 (99.85% overlap with H19-5 mirror).

## Protocol

- SegmentHoldout (whole-component hide-and-recover, buffer 15 px = 1.5 km, four spatial quadrants, pooled DTI, alpha 0.2, beta 0.8, 300 m triangular kernel, 100 m tiles, 1 999 bootstrap draws).
- Every channel AND the combined surface tested alone on the holdout (leakage canary); AUC > 0.90 (either polarity) = leakage until proven otherwise.
- Pre-placement surface novelty and final-dot novelty vs the priority registry: |Spearman rho| <= 0.90 AND candidate-dots-within-3-px overlap <= 0.70 versus every competing method lane; synthetic calibration controls reported separately, never removed.
- Exact-grid TIF, zeros outside the footprint (finite [0,1] everywhere — portal-range compatible), single band float32, CRS EPSG:32611, shape (3730, 3292), geotransform matching the template.
- Promotion to `ok_to_submit=True` only if ALL of: format valid; strict whole-array [0,1]; novelty passes; canary passes; holdout DTI beats the current comparable best (0.13000 OOF multiphysics baseline, `gems-segment-pooled-v1`, or current recorded best if higher).
- Otherwise verdict = `negative`, which is a deliverable. No DrivenData slot is spent.

## Outputs

- `docs/downloads/24gems-blind-upwelling-<date>-<content_id>-zeros.tif` (zeros outside, finite [0,1])
- `docs/downloads/checks-*.json`, `preflight-*.json`, `note-*.txt` (<= 140 chars)
- `evidence/blind_upwell_experiment.json` + `docs/data/blind_upwell_run_card.json` (run card)
- `docs/data/blind_upwell_download.json` (download entry)

## Inputs (hash-pinned)

- data/bridge/sample_submission.tif (template)
- data/bridge/labels.tif (catalogue, holdout only)
- data/external/lidar_scarp_features_u8.tif
- data/external/geodawn_rad_u8.tif
- data/external/geodawn_extensions_u8.tif
- data/external/gdr_volcanic_vents_in_footprint.csv
- data/external/gdr_wellspring_in_footprint.csv

## Official sources

- USGS GeoDAWN: https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and (DOI 10.5066/P93LGLVQ; ScienceBase item 657e1d85d34e23d3533209f7)
- INGENIOUS/OpenEI GDR: https://gdr.openei.org/submissions/1391
- USGS 3DEP LiDAR DEM: USGS National Geospatial Program (3DEP products without use restrictions)
- EPSG:32611: https://epsg.io/32611
- Tversky/DTI: https://en.wikipedia.org/wiki/Tversky_index ; competition metric page https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/#performance-metric
- Competition rules: https://docs.nlr.gov/docs/fy26osti/96647.pdf
