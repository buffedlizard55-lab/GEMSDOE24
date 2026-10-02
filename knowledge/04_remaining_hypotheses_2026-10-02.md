# Remaining untested geology hypotheses — 2026-10-02

This register is ordered after the completed H24-2A experiment (which did **not**
beat the recorded historical H19 as-emitted diagnostics). It was written before
implementing another detector. Scores below are ordinal hypotheses, not promised
DTI gains, and no idea is a submission candidate until it beats a comparable
spatial holdout baseline and passes the exact-raster/accessibility gates.

## Ranked candidates

| Rank | Specific layers | Physical signature and omitted-fault rationale | Difference from reviewed work | Expected DTI / implementation cost / availability |
|---|---|---|---|---|
| 1 — H24-3A: common-resolution contact persistence | Owner bridge RTP (band 2), TMI (band 14), isostatic gravity anomaly (band 13), with the GeoDAWN report's two acquisition specifications used only to interpret resolution limitations | Upward-continue each potential-field grid with the potential-field transfer `exp(-2πh|k|)` at fixed added heights; measure whether co-located contact ridges persist at the same position across heights and across independent magnetic/gravity fields. A broad/buried fault-related contact may remain coherent after short-wavelength noise attenuates, while an isolated processing or near-surface edge may not. Contacts are not uniquely faults. | Tests cross-scale **edge-location stability**, not raw gradient magnitude, sinusoidal/ring filtering or drainage curvature; no new fault labels or fault distances enter. | **Low–medium, conditional** expected DTI; **moderate** implementation/CPU. Required fields are present in the restored owner-supplied stack, but not organizer-authenticated. No new external dataset is required. |
| 2 — H24-4A: directional residual variogram | High-pass RTP/TMI and isostatic-gravity residuals; dilation as independent corroboration only | Estimate semivariance at 0.3/0.6/1.2 km along eight fixed azimuths; encode scale-dependent anisotropy and cross-field orientation agreement. A fractured or damage-zone fabric may produce directional texture even where relief and a sharp contact are weak. | Variogram range/phase is different from the existing LiDAR structure-tensor/coherence layers, line/ridge scores, and earthquake-density bands. | **Low–medium** expected DTI; **moderate** cost. Local stack only (same owner-provenance caveat); no external data required. |
| 3 — H24-6: repeated drainage-offset concordance | USGS 3DEP 1/3-arc-second DEM (about 10 m), derived channel crossings; use 1 m DEM only where available for a predeclared local validation | Along a proposed line, require a consistent signed lateral offset at at least three independent drainage crossings; reject a single scarp or bank step. Repeated channel displacement could reveal short strike-slip splays absent from a Quaternary scarp catalogue. | Scores kinematic consistency across multiple channel crossings, rather than the existing single-pixel relief, anti-piedmont or hinge-curvature descriptors. | **Uncertain medium** expected DTI; **high** data/compute cost. The official USGS TNM Access API returned public GeoTIFF records for the 1/3-arc-second DEM around `(-120.0, 38.5)`; the official catalog describes national coverage/public-domain terms. The previous guessed `/current/n39w119/` URL is stale (HTTP 500 in this environment). The study-wide tiles have **not** been byte-downloaded or coverage-validated, so this stays deferred until the exact TNM API results and file hashes are recorded. |

## Pre-implementation spatial-support amendment for H24-3A

The exact upward-continuation kernel is nonlocal. Before coding/scoring, H24-3A
will use the same four quadrants but a **20 km training exclusion collar** around
each held-out quadrant for every arm, not the older 1.5 km collar. For an ideal
infinite-plane Poisson kernel at the maximum added height of 400 m, the integrated
kernel mass outside 20 km is about 2%; the residual nonlocal dependence remains
and will be disclosed. If that stricter design leaves insufficient positives in
any fold, the experiment fails closed rather than shrinking the collar after
seeing results. This amendment changes no label, feature, model, metric or
submission decision.

## Source and interpretation checks

- [GeoDAWN official release](https://www.sciencebase.gov/catalog/item/657e1d85d34e23d3533209f7) and the preserved contractor report identify four operational blocks, but available GIS gives one combined extent plus Area 1/Area 2 outlines and flight-line inventories with `Id`/`Line`, not block membership. The report's Figure 3 is a non-georeferenced image; no pixel is assigned a “true” block from a nearest base station, a latitude seam, Area 1/2, or label-derived geometry.
- The report specifies **two** acquisition regimes: Area 1 traverse/tie spacing 200 m/2 km and nominal drape 100–150 m; Area 2 400 m/4 km and 150–200 m. Area 1 is within the Tonopah block; Tonopah was flown by helicopter using the same planned layout/drape regime as the other blocks. Therefore, “each of four blocks has a different spacing/height” is not supported by the source.
- [USGS 3DEP 1/3-arc-second collection](https://data.usgs.gov/datacatalog/data/USGS:3a81321b-c153-416f-98b7-cc8e5f0e17c3) and [The National Map download/API](https://www.usgs.gov/tools/download-data-maps-national-map) are the official free-source route. A catalog/API listing confirms a product exists, not that complete footprint coverage or all required bytes have been acquired.
- C2ST association is not causation; conditioning/residualization is a robustness intervention and does not establish a geological or economic mechanism.

## Preregistration clarification and result status

The earlier H24-2 preregistration described upward continuation as `exp(-|k|h)`.
The H24-3A implementation uses spatial frequency in cycles per metre, so its
standard potential-field transfer is `exp(-2*pi*h*|f|)`; this is algebraically
equivalent when angular wavenumber `k = 2*pi*f`. It is a unit convention, not an
outcome-tuned filter. The 20 km collar amendment above replaces the older 1.5 km
collar for H24-3A only; all arms use the same four quadrants and 20 km collar.

H24-3A was run once on 2026-10-02. The official buffered road source is now
verified, but four-block pixel membership remains missing. The candidate gained
mean dense/sparse DTI over the residualized physics baseline yet failed the
sparse-fold win rule (2/4) and trailed both H19 rasters scored as emitted. Its
exact format-valid raster was re-audited with the available road/claim families;
no available-family association flag appeared, but the three-family audit remains
incomplete. No slot was spent and the candidate was not promoted. Full values,
fold details, null results and file hashes are in
`evidence/h24_3a_experiment.json` and `evidence/accessibility_audit_v3.json`.

The next candidate, H24-4A, is untested. H24-6 remains deferred until exact
official 3DEP tiles are downloaded and coverage/hash verified. No partial run may
substitute Area 1/2 or map-digitized seams for block membership, and no score may
be called a leader-beater without a reproduced comparable H19 holdout.
