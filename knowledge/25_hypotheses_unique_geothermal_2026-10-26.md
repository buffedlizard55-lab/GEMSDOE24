# Candidate Geological Hypotheses — H-UNIQUE-04/05/06 (2026-10-26)

**Protocol constraint:** Validate the top candidate on the spatially-blocked holdout
(`SegmentHoldout`, pooled DTI alpha 0.2, beta 0.8, 300 m triangular kernel,
60,988 withheld positives) before any weekly submission slot. Negative results
are deliverables. Do not spend a slot on an idea that has not beaten the current
comparable holdout best (OOF multi-physics HGB: HOLDOUT-DTI 0.13000;
DPRF1 point-best: HOLDOUT-DTI 0.16379).

All hypotheses below are catalogue-independent: the USGS/INGENIOUS fault
catalogue is used ONLY for holdout masking and evaluation, never to build the
score surface. This targets faults MISSING from the catalogue — concealed,
blind, or stepover structures without a mapped surface trace.

---

## H-UNIQUE-04 · Concealed basin-margin step (rank 1 · tested · NEGATIVE)

**Layers:** `iso_grav_anom_hg` (gravity horizontal gradient),
`depth_to_base_surf` (basement depth), `lidar_scarp_features_u8.tif` band 9
(relief, for terrain suppression).

**Physical signature:** Basin-margin faults offset the basement surface.
A co-located gravity-gradient lineament + depth-to-basement step marks a
concealed fault. Terrain suppression downweights high-relief areas where
surface scarps would already be catalogued.

**Why it catches missing faults:** Concealed range-front faults have no
surface rupture and therefore no LiDAR scarp; they are absent from the
USGS/INGENIOUS catalogue. The basement step and gravity gradient remain
detectable under cover.

**Difference from repo:** Not terrain-scarp based (differs from SAHG1/RSHG1),
not catalogue-guided (differs from dotted-ridge/h28/h33), not magnetic-trough
based (differs from MTR1/CRP1).

**Expected DTI improvement:** Low-to-moderate (concealed structures are
sparse; kernel credit is diffuse). **Cost:** Low — all layers already in the
pinned feature stack.

**Result:** HOLDOUT-DTI 0.0594 [0.0434, 0.0761]. Novelty gate FAILED:
final-dot overlap 100% vs registry (gravity/basement features co-locate with
catalogued faults). **Verdict: negative.** (evidence/unique_experiment4.json)

**Non-fault mimic:** Lithologic or intrusive contacts with gravity / basement
contrast produce the same signature without a fault.

---

## H-UNIQUE-05/06 · Geothermal surface-feature proximity (rank 2 · tested · NEGATIVE)

**Layers:** `gdr_volcanic_vents_in_footprint.csv` (vent row/col),
`gdr_wellspring_in_footprint.csv` (spring row/col + temperature °C).

**Physical signature:** Hot springs and volcanic vents mark where geothermal
fluid reaches the surface. The fault is the conduit. Kernel-smoothed proximity
to these features (300 m triangular kernel, temperature-weighted for springs)
targets fault conduits without ever conditioning on fault traces.

**Why it catches missing faults:** Vents and springs are geothermal surface
features, not faults. They are independent of fault mapping and orthogonal to
every registry raster derived from fault traces or geophysical fault proxies.
Faults that host geothermal convection but lack surface expression are
missing from the catalogue.

**Difference from repo:** No LiDAR, gravity, magnetics, or DEM scarps.
Orthogonal detection geometry to all reviewed methods.

**Expected DTI improvement:** Low (geothermal features are sparse; many
are cold/non-geothermal mimics). **Cost:** Low — public GDR/INGENIOUS CSVs.

**Result:** HOLDOUT-DTI 0.0223 [0.0180, 0.0272]. Novelty gate FAILED:
final-dot overlap 99.7% vs registry (geothermal features co-locate with
faults at the surface). Canary PASSED (AUC ~0.50 for all channels — no
leakage). **Verdict: negative.** (evidence/unique_experiment6.json,
packaged TIF: `24gems-geothermal-surface-proximity-20261026T163058Z-dd2fff044fc1-zeros.tif`)

**Non-fault mimic:** Cold springs, non-geothermal seeps, surface water.

---

## H-UNIQUE-A · Strike-compatibility prior (UNTRIED · rank 3)

**Layers:** LiDAR strike orientation (`lidar_scarp_features_u8.tif` band 11),
training-region catalogue strike field (derived from visible faults only).

**Physical signature:** Faults in an Andersonian strike-slip regime prefer a
narrow strike range. Emitted dots weighted by strike compatibility with the
local structural grain reject randomly oriented false positives.

**Why it catches missing faults:** Blind faults that match the regional
strike family but are unmapped; rejects cross-strike noise from lithologic
contacts or geomorphic artifacts.

**Difference from repo:** No reviewed method uses orientation priors on
emitted dots.

**Expected DTI improvement:** +0.00–0.01 (precision filter, not a detector).
**Cost:** Low — uses existing LiDAR bands and visible catalogue.

**External data needed:** None (all local). **Status:** Not yet tested.

---

## H-UNIQUE-B · Scarp cross-profile template (UNTRIED · rank 4)

**Layers:** 1 m 3DEP DEM tiles (706/716 processed on CI), scarp cross-profile
template (concave-up free face + colluvial apron).

**Physical signature:** Quaternary scarps have a distinctive cross-profile:
steep bedrock face, colluvial wedge, symmetric/asymmetric apron. A matched
filter along cross-strip transects detects scarps that per-100-m maxima
smooth over.

**Why it catches missing faults:** Short, subtle Quaternary scarps are
unlisted in the catalogue (mapping threshold too high). Template matching
is sensitive to low-relief scarps.

**Difference from repo:** Uses profile shape, not per-pixel relief maxima.

**Expected DTI improvement:** +0.01–0.03. **Cost:** Medium — needs 3DEP tile
availability receipts from USGS 3DEP (free, official:
https://www.usgs.gov/3d-elevation-program/data-tools).

**External data needed:** 3DEP 1 m DEM tiles (free, public). **Status:** Not
yet tested; CI tile processing already validated.

---

## H-UNIQUE-C · Map-scale correction corridor (UNTRIED · rank 5)

**Layers:** INGENIOUS `MAPSCALE` per trace (82% of catalogue length at
1:250k), LiDAR scarps.

**Physical signature:** Qfaults can be ~400 m off true location (Hermant 2025).
Staff note: new truth may lie within 300 m of a known trace. A corridor
around catalogue traces weighted by map-scale uncertainty targets this
positional-uncertainty band.

**Why it catches missing faults:** Maps positional uncertainty explicitly
rather than treating catalogue traces as exact. Catches faults whose mapped
location is off but whose true position is nearby.

**Difference from repo:** Catalogue used as positional-uncertainty prior,
not a halo (halos fail the overlap gate).

**Expected DTI improvement:** Unknown. **Cost:** Medium — needs per-pixel
map-scale raster from GDR 1391 (free: https://gdr.openei.org/submissions/1391).

**External data needed:** GDR 1391 MAPSCALE raster. **Status:** Not yet tested;
source obtainability not yet verified from this sandbox (only github/pypi
respond).

---

## Ranking summary (expected DTI × P(validatable) ÷ cost)

| Rank | Hypothesis | Layers | Expected ΔDTI | Cost | Status |
|------|-----------|--------|---------------|------|--------|
| 1 | Concealed basin-margin step | gravity-hg, depth-base, relief | Low-mod | Low | Tested, NEGATIVE |
| 2 | Geothermal surface proximity | vents, springs + temp | Low | Low | Tested, NEGATIVE |
| 3 | Strike-compatibility prior | lidar strike, visible catalogue strike | 0.00–0.01 | Low | Untried |
| 4 | Scarp cross-profile template | 3DEP 1 m DEM | 0.01–0.03 | Medium | Untried |
| 5 | Map-scale correction corridor | MAPSCALE + LiDAR scarps | Unknown | Medium | Untried, data TBD |

**Recommendation:** The two tested hypotheses both failed the novelty gate
because geological features co-locate with catalogue faults at the surface.
The next untried candidate (H-UNIQUE-A, strike compatibility) is a precision
filter rather than a detector and is unlikely to clear novelty alone. The
most promising untried path is H-UNIQUE-B (scarp cross-profile template),
which changes detection geometry from amplitude-based to profile-shape-based,
potentially avoiding registry overlap. It requires 3DEP 1 m DEM tiles
(official, free, from USGS 3DEP).
