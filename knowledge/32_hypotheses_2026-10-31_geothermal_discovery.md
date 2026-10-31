# 3–5 candidate geological hypotheses for geothermal-vent fault discovery (2026-10-31)

Context: the nine focus sites (GEMSDOE24/25/27/28/30/31/32/33/36) share one dot family —
every pair overlaps ≥97.6% within 3 px (evidence/nine_site_verify_20261030.json). The
highest owner-reported value is GEMSDOE32 B2 (0.2778), which is an exact dot subset of
GEMSDOE25 D2.8 with catalogue-adjacent dots removed — not unique, not an organizer score,
and prohibited to copy. All estimates below are planning judgments, not forecasts; every
candidate must pass the SegmentHoldout hide-and-recover gate (pooled DTI, α=0.2, β=0.8,
300 m triangular kernel, 60,988 withheld positives) before any weekly slot is considered.
No slot is spent here; the agent never uploads.

## H1 · Geo1 concealed-conduit propensity (GEOPHYSICS + LiDAR scarp) — TOP CANDIDATE

* **Layers (all committed, free, official):** USGS GeoDAWN radiometrics (K, Th, U, total
  count) and TMI upward-continued to 150 m (DOI 10.5066/P93LGLVQ, ScienceBase item
  657e1d85d34e23d3533209f7), GeoDAWN extensions (Th/K, U/K, U/Th ratios), and USGS
  3DEP 1 m LiDAR scarp derivatives (step/upface/downface/cross/relief) — committed as
  uint8 rank grids in data/external/ (geodawn_rad_u8.tif, geodawn_extensions_u8.tif,
  lidar_scarp_features_u8.tif). Footprint: data/bridge/sample_submission.tif.
* **Physical signature targeted:** edge/magnitude transforms (3×3 Sobel on rank grids,
  100 m Gaussian smoothing) of aeromagnetics + radiometrics — concealed fault-controlled
  fluid pathways produce magnetic step/trough edges and K/Th/U alteration fronts at
  depth; LiDAR scarp expression (step_max, upface/downface, cross-cutting curvature)
  targets the 2 m surface expression of concealed scarps. Combined by weighted sum and
  normalized to [0,1] over the footprint.
* **Why it catches faults missing from USGS/INGENIOUS:** the catalogue maps surface
  traces; concealed geothermal conduits leave no through-going surface trace but do
  alter near-surface geophysics and produce subtle scarps. Targets the concealed
  fraction directly, not catalogue proximity.
* **How it differs from in-repo implementations:** distinct from MTR1 (magnetic trough
  + Th/K only, no LiDAR, no edges), S3DEP1 (3DEP sub-cell gradients + crustal bands,
  no radiometric edges), XVAR1 (semivariogram jumps), DPRF1/EUL1/TRSG1 (crustal stack
  + Euler contacts). Implemented in scripts/build_unique_geothermal_submission.py
  (SegmentHoldout + submission_writer, no labels in the score, no old predictions).
* **Non-fault mimic:** alluvial fan/terrace riser/paleoshoreline steps that sharpen
  K/Th/U and magnetic gradients; road cut/fill corridors (audited via nuisance families).
* **Expected DTI improvement:** medium — moves mass to geophysically plausible pixels
  without changing local order; holdout baseline to beat is S3DEP1 0.166060.
* **Implementation cost:** low — grids already on disk; script exists; ~1 experiment.

## H2 · Surface geothermal feature proximity (vents + hot springs, catalogue-offset band)

* **Layers:** GDR/OpenEI #1391 volcanic vents (gdr_volcanic_vents_in_footprint.csv) and
  hot springs (gdr_wellspring_in_footprint.csv, temp_c) — committed public extracts;
  existing_faults.tif catalogue for the 200–900 m offset band.
* **Physical signature:** triangular-kernel (300 m) proximity to surface geothermal
  features weighted by measured temperature; dots restricted to the 200–900 m band from
  visible catalogue faults (H33-B2 offset insight: hidden truth is offset from, not
  coincident with, mapped traces).
* **Why it catches faults missing from the catalogue:** springs and vents mark where
  geothermal fluid reaches the surface along concealed conduits; the conduit fault at
  depth is commonly absent from line-trace catalogues.
* **Differs from in-repo:** H-UNIQUE-07 was stopped for full-catalogue support leakage;
  this version constructs per-fold eligibility from fold.visible only and never reads
  labels in the score. Not yet executed as a clean lane.
* **Non-fault mimic:** cold springs, non-geothermal seeps, gravel pits, surface water.
* **Expected DTI improvement:** low–medium; **cost:** low (CSVs on disk).

## H3 · INGENIOUS 2 m temperature-probe proximity (direct heat evidence, overlooked)

* **Layers:** 2m_temperature_probe_INGENIOUS_regional_data.zip (committed) — in-situ
  2 m temperature probe measurements (xlsx + shapefile n83geo). Free official INGENIOUS
  data that virtually no lane has used as a detector input.
* **Physical signature:** kernel-weighted proximity to high 2 m temperature readings
  (heat anomalously close to the surface = shallow geothermal plumbing).
* **Why it catches catalogue gaps:** a temperature anomaly requires no mapped fault at
  all; it directly targets the geothermal system, and the fault hosting it may be
  entirely unmapped.
* **Differs from in-repo:** no existing lane uses in-situ temperature probes; all
  existing lanes use remote-sensing proxies or catalogue geometry.
* **Non-fault mimic:** cultural heat, irrigation, shallow groundwater unrelated to
  faults; probe spatial clustering (access bias).
* **Data availability:** verified obtainable (zip committed). **Cost:** medium (point
  → raster conversion, temperature field cleaning).
* **Expected DTI improvement:** medium–high ceiling if probes cluster on concealed
  faults; unverified until holdout run.

## H4 · Qfaults confidence-stratified gap prior (INGENIOUS qfaults map scale)

* **Layers:** gdr_qfaults_traces.csv (committed, 1,126 traces with map_scale, recency,
  slip rate) — INGENIOUS Qfaults; centroids already snapped to footprint rows/cols.
* **Physical signature:** local density / nearest distance to "Inferred" (buried,
  poorly constrained) traces at 1:250k scale — where mappers marked "Inferred", real
  unmapped faults are likelier within a few km.
* **Why it catches gaps:** the catalogue's confidence field is the public trace of
  where the mapping process thinned out; an inferred trace 1–2 km from the nearest
  well-constrained trace marks a gap zone.
* **Differs from in-repo:** existing lanes use the catalogue as labels/negatives only;
  none uses confidence stratification as a spatial mass-re-allocation prior restricted
  to pixels where independent geophysical evidence fires (keeps self-prediction leak
  out of the score).
* **Non-fault mimic:** mapper convenience, access-driven mapping density (roads).
* **Expected DTI improvement:** low (re-allocation multiplier only); **cost:** low
  (CSV on disk).

## H5 · Ring/curvature matched filter (arc faults under-reported by line traces)

* **Layers:** would need the GeoDAWN DEM (22103_dem from ScienceBase 657e1d85…, not
  committed; 45 MB area-1 / 242 MB area-2) or curvature from TMI_up150 gradient
  structure tensor on committed grids.
* **Physical signature:** curvature-selective matched filter (Radon-style, radius
  3–30 cells) for circular/arcuate gradient chains — caldera rings and cryptodome
  annuli around geothermal systems.
* **Why it catches gaps:** every in-repo detector is linearity-biased (worms,
  directional coherence, cross-gradient edges); ring faults are broken into penalized
  segments by linear trackers. Ring faults at Steamboat Hills/Tonopah-springs-type
  systems are geothermal targets under-reported by USGS line-trace convention.
* **Differs from in-repo:** no sibling repo contains any curvature template.
* **Blocker:** DEM not committed and ScienceBase bulk download is large; verify
  obtainability (free DOI 10.5066/P93LGLVQ) before marking viable. Fall back to
  gradient-curvature of committed TMI_up150.
* **Expected DTI improvement:** speculative (highest ceiling); **cost:** high.

Ranking by expected DTI improvement × implementation cost: H1 > H3 > H2 ≈ H4 > H5.
Validation order: run H1 on SegmentHoldout first (grids on disk, script exists). If H1
does not beat the recorded S3DEP1 holdout point-best 0.166060 with a clean uniqueness
gate, do not spend a slot; report negative result.

All source links are public and official: USGS ScienceBase (GDR #1391, DOI above),
INGENIOUS (gbcge.org/current-projects/ingenious/), USGS Qfaults via GDR. No
DrivenData automation; leaderboard access is human-only per competition ToU.
