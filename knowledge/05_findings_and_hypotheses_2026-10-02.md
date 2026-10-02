# 05 · Findings, ranked hypotheses and what the live board tells us (2026-10-02)

Evidence classes are kept apart. **OFFICIAL** = organizer/USGS text I read at the cited link.
**TEAM** = the owner's own sibling sites/repos (not organizer receipts). **TASK** = numbers present only in
the task statement (agent-transcribed, flagged below). **COMPUTED** = reproducible in this repo.
**INFERENCE** = my reading, assumptions stated. Nothing here is a leaderboard score unless the owner reported it.

## 1. New OFFICIAL facts (all read this session)

| # | Fact (verbatim or tight paraphrase) | Source |
|---|---|---|
| F1 | Known USGS/INGENIOUS pixels "are masked / excluded from evaluation, so they do not count towards penalty terms"; the final re-evaluation also masks them. (DrivenData staff `chrisk-dd`, 2026-09-16) | [forum 11516 #2](https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516/2) |
| F2 | "new fault" means "any fault pixel not already captured by USGS/INGENIOUS" and "can include newly mapped geometry of an existing fault system". (staff, 2026-09-23) | [forum 11536 #2](https://community.drivendata.org/t/where-do-you-draw-the-line/11536/2) |
| F3 | Staff are "not sharing details about the data sources, fault types, or coverage behind the test faults"; the Phase 2 test set "is updated by expert review of all Phase 1 submissions". (2026-09-23) | [forum 11527 #7](https://community.drivendata.org/t/how-were-the-new-test-faults-identified-data-sources-and-fault-types/11527/7) |
| F4 | Public score = "pooling over all pixels in the public subset and computing a single Tversky index"; chunking is undisclosed; private is computed the same way; "the final re-evaluation will be on the entire GeoDAWN area". (2026-10-01) | [forum 11550 #2](https://community.drivendata.org/t/leaderboard-aggregation-pooled-over-public-test-pixels-or-mean-of-per-chunk-scores/11550/2) |
| F5 | Hand-labelling is permitted if the labels are saved and available on request. (2026-10-01) | [forum 11543 #2](https://community.drivendata.org/t/using-a-teammates-geological-interpretation-as-training-labels/11543/2) |
| F6 | The survey was "divide[d] ... into four separate acquisition blocks, each with an independent base of operations"; published line-km: Winnemucca 62,530 · Fallon 43,500 · Hawthorne 21,400 · Tonopah 21,600 (incl. Area 1); total 149,030 km. Flights 1–87 Winnemucca, 88–148 Fallon, 149–161 Hawthorne (fixed-wing); Tonopah = helicopter. Base stations given in UTM 11N. Tie lines extend ≥2 km into the neighbouring block. | [USGS report, Fig. 3 and text](https://www.sciencebase.gov/catalog/item/657e1d85d34e23d3533209f7) (`data/external/audit_sources/…D21_Report.pdf`) |
| F7 | Three aircraft/sensor systems: Cessna 180 and Cessna 206 Turbo (Geometrics G-823A, 0.0002 nT) and a Bell 206 helicopter (Scintrex CS-3, 0.0006 nT). Area 1 (Clayton Valley): 200 m lines, 100/150 m clearance; Area 2: 400 m, 150/200 m. | same item, `GeoDAWN Metadata FINAL.csv` |
| F8 | The spectrometer/magnetometer **profile CSV archives are S3-hosted; anonymous GET returns HTTP 403** and the `file/get?name=` form returns 404 (Manager URLs return an HTML page). They need a browser/Manager or an emailed link. | CI receipt `evidence/ci/profiles.log` |
| F9 | Census TIGER2024 `ROADS/tl_2024_<FIPS>_roads.zip` and `COUNTY/tl_2024_us_county.zip` exist at the paths the script uses. | [directory listing](https://www2.census.gov/geo/tiger/TIGER2024/ROADS/) |

**Irregularity found and fixed.** `scripts/fetch_official_roads.py` compared the TIGER `.prj` CRS to EPSG:4269
with strict `CRS.equals`, which is `False` for the standard ESRI WKT (axis order). Reproduced locally; this is the
probable cause of the earlier 25-second CI failure (the CI log itself was unreadable). With
`ignore_axis_order=True` and an authority-code check the official buffered road run succeeds
(`complete_county_check: true`, 1,141,630 seed pixels).

## 2. Acquisition blocks: a declared, audited derivation (COMPUTED)

`scripts/derive_acquisition_blocks.py` georeferences Figure 3 by fitting the official extent polygon to the figure's
yellow outline (mean boundary residual ≈ 4.9 px ≈ 1.6 km; scale 3.07–3.10 px/km vs the figure's own 200 km bar ≈ 3.03),
reads the four rectangles' edges as fitted lines, assigns Tonopah as the footprint south of the Hawthorne base line,
and **audits against the published line-km** with tolerances fixed beforehand (±8 % per block, ±5 % total):

| Block | Published km | Derived km | Δ |
|---|---|---|---|
| Winnemucca | 62,530 | 63,045 | +0.8 % |
| Fallon | 43,500 | 44,972 | +3.4 % |
| Hawthorne | 21,400 | 20,942 | −2.1 % |
| Tonopah (incl. Area 1, Area-1 priority) | 21,600 | 21,833 | +1.1 % |
| Total | 149,030 | 150,793 | +1.2 % |

The variant that double-counts Area-2 lines inside Area 1 overshoots Tonopah by 62 %, so the audit discriminates.
Status is **derived_audited, official_coordinates = false**: boundaries are read from a figure (few-km uncertainty;
membership within ~2 km of a boundary is inherently ambiguous because tie lines overlap). The official flight-number
mapping (F6) would supersede it but its profile archives are not anonymously downloadable (F8).

## 3. What the live board says (COMPUTED from 24 downloaded scored artifacts; scores are owner-reported)

Artifact hashes match the content IDs in their file names. Score provenance per file is in
`registry/live_scores.json` ("site" = also stated on a team site page I fetched; "task" = only in the task statement).
H28's 0.1839 is **uncorroborated**: an earlier verbatim snapshot of the owner's list (GEMSDOE21 README) shows it blank.

* **Proxy rank correlations with live score are weak.** Exact DTI against SGMC-minus-catalogue (an independent,
  geologist-mapped fault set the catalogue models never saw): Spearman +0.33 (n = 24, p = .11); on the 12 team-corroborated
  scores +0.06. Catalogue-sparse proxy: −0.02 (contaminated: models trained on the catalogue). The team's own
  16GEMSDOE page reports +0.17 for the dense proxy (n = 15). **A holdout win is necessary, not sufficient.**
* **Near-catalogue emission fails.** All 5 files with ≥45 % of non-catalogue emission within 3 px of the catalogue scored ≤ 0.046;
  3 of the other 19 did. Reproducing/hugging the catalogue does not find new faults (consistent with three team pages).
* **Emission count alone does not rank files** (Spearman −0.24, n.s.), but the worst files by far emit most (H19-C 452,798 px → 0.0297).
  Together with F4 this indicates a **sparse, false-positive-dominated regime** (INFERENCE, assumptions: public subset ≈ a
  region fraction; truth ≪ emission).
* **Lidar-coverage concentration is untestable** from existing files: nearly all emit ≈75 % inside lidar coverage (= area share).
* **Emission geometry of the best files.** H19-5/H19-4/H16-1 are blobby segments (39–41 % of pixels have ≥3 emitted neighbours;
  mean component 4.1–4.5 px). H28 and the `nms3` files are pure isolated dots. H25 and H28 share the identical probability
  field (`6452ae1d…`); the owner reports **0.1280 (solid) → 0.1839 (dotted)** for them (the second number: see above).

### Why H19-4 (0.1894) and H19-5 (0.1922) scored best — what can and cannot be said
Supported: they are the same family (91–98 % mutual 1.5-px coverage with H16-1), ≈90 % topographic/scarp, emit ≈121–124k
non-catalogue pixels, 20 % of which lie within 3 px of the catalogue, and none on catalogue pixels. The H16-1 → H19-5 gain
(+0.0067) is far smaller than the H25 → H28 geometry effect. **Not supported:** any claim that a specific physical "line"
or weight caused the gain. **Is > 0.1894 achievable?** Already exceeded by H19-5 (0.1922). Beyond that, the only
lever with direct evidence in the group's own record is emission geometry (§4); the 0.3195 leader needs new information, not re-spending.

## 4. H25-1 — Dotted H19 (generation system) · preregistered, validated, **not a geology hypothesis**

* **Layers:** none new. Transform of the pinned H19-5 emission (`src/gems/thinning.py::dot_thin`, geodesic Poisson-disk subset,
  no label/score read, subset-only, deterministic).
* **Signature targeted:** fault traces are continuous; the metric credits a pixel `1 − d/3`, so a ~3-px dotted trace keeps ≈0.78 of
  on-line credit for ≈⅓ of the false-positive mass.
* **Why it can matter for faults missing from the catalogue:** it cannot *find* them; it lowers the cost of every candidate trace,
  which in an FP-dominated regime raises DTI for the same detections.
* **Difference from the repo:** H19 emissions were never dotted; H28 dotted only the weaker H25 field.
* **Expected DTI / cost:** harness +27 % relative on sparse truths (+18 % on the confirmation quadrant, 48/48 cell wins,
  block-bootstrap 5th percentile +21 %), neutral at full density (Δ −0.0005…+0.0019). If the live regime resembles that, 0.192 → ≈0.23;
  the team's own density-matched holdout gave +23 %, the owner-reported H25 → H28 pair +44 %. **Cost:** minutes of CPU.
* **Honest limits:** the harness did *not* reproduce the H25 → H28 live jump (it shows ≈+1 %), so magnitude is uncalibrated.
  Results: `evidence/dotting_validation.json`. Preregistration: `04_preregistered_dotting_2026-10-02.md`.

## 5. Ranked geological hypotheses not yet implemented (H25-2 … H25-5)

| Rank | Hypothesis | Layers | Physical signature | Why it could catch faults missing from USGS/INGENIOUS | Difference from repo | Expected DTI / cost |
|---|---|---|---|---|---|---|
| 1 | **H25-2 Strike-compatibility prior** | emitted-ridge orientation; local regional strike distribution from *training-region* catalogue only (≈50 km kernel); optional strain axes | Andersonian normal/oblique faults cluster near the local strike family; roads, channels and mine benches do not | Raises precision for compatible lineaments, so the budget reaches unmapped-but-compatible traces; does not need a scarp | no explicit orientation-field prior in the active pipeline (orientation exists only as GBM features) | +0.00–0.01, uncertain; ≈1 day; testable on the same blocked folds with the catalogue used only from other quadrants |
| 2 | **H25-3 Scarp cross-profile template** | 1 m 3DEP DEM (706/716 tiles already processed on CI) | diffusion-degraded step (error-function) with consistent height across a 20–60 m profile vs sharper/symmetric road cuts, terrace risers, shorelines | Short Quaternary scarps in alluvium that are subtle at 10 m and unlisted; this is the evidence experts see on lidar | repo uses per-100 m maxima of slope/curvature (`ex_max`, `step_max`, …), losing profile shape | highest ceiling (+0.01–0.03), high cost: CI re-run over all tiles, ≈2 days |
| 3 | **H25-4 Concealed basin-margin step** | `depth_to_base_surf`, `iso_grav_anom_hg`, `tmi_hg` | co-located steps in basement depth, gravity gradient and magnetic edge with trace continuity | buried range-front/intra-basin faults with no scarp | geophysics enter only as raw GBM channels, not as a joint-step detector | small/uncertain (hidden truth looks topography-driven); ≈2 days |
| 4 | **H25-1b Dotted multi-field union** | dotted H19-5 ∪ dotted independent field (e.g. H28) | complementary detections amortise the fixed FN term | adds recall where H19 is blind, at ~⅓ FP per pixel | unions so far were near-duplicates (Jaccard .95) | positive iff added dots earn ≥ 0.2·DTI in credit share (met by any independent field of similar standalone DTI); proxies cannot rank fields, so **unvalidated**; hours |
| 5 | **H25-5 Microseismic lineations** | USGS ComCat (public domain) epicentres | along-strike hypocentre alignments on active structures | blind/reactivated faults | catalogue `deq/ieq` bands are ambiguous aliases and unused | low: location error (1–5 km) ≫ the 300 m kernel |

Ranking criterion: expected DTI gain × probability the proxy can validate it ÷ cost, with H25-1 ahead of all because it is the only item
with direct live evidence. H25-2 is next because it can be validated on the existing quadrants with no new data.

## 6. Overlooked / contrarian items (verified or flagged)

* Staff F2 says *new geometry of an existing system counts*; the live record says **catalogue-hugging emission fails**. They reconcile only if
  such geometry lies mostly beyond ~300 m of mapped pixels, so continuation priors need *geological* evidence, not proximity (H24-1 and the
  team's `h16-continuation`, 0.0461, agree).
* F5 allows hand-labelled lidar training data. A geologist-labelled scarp set is the most direct way to supervise H25-3 and is not used yet. It needs a
  human (access need, §7).
* Phase 2 re-labels with expert review of **all Phase 1 submissions** (F3): diverse, well-localised predictions have value beyond the Phase 1 rank.
* Multiple accounts: the leaderboard rows for `extradr19`, `SDCF9`, `smashi34`, `smrtdoog5`, `wbg1` appear on team pages as owner-associated, "attribution unverified".
  The official rules limit submissions per week; check that account usage complies with the rules' one-account/team provisions before relying on it.

## 7. Limits and access I need

* Cannot reach DrivenData's submission portal, private leaderboard or hidden labels; cannot verify owner scores (please confirm H28 = 0.1839 and the other **TASK** rows on your submissions page).
* ScienceBase S3-hosted profile CSVs (F8): please download `22103_spec_a1_csv.zip` / `…a2…` in a browser or request the emailed link if you want the *official* flight-number block mapping.
* A geologist for hand-labelled lidar scarps (F5), and a ~3-minute decision from you on whether to spend a slot on the dotted candidate.
