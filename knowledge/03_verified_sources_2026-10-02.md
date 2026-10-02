# Source review and scientific interpretation — 2026-10-02

## Evidence classes

1. **Official source read / official byte receipt:** organizer specification,
   staff clarification, USGS/BLM/Census publication, or cited paper. This verifies
   the stated fact, not every interpretation one could attach to it.
2. **Computed locally:** counts, checksums, Jaccard, held-out metrics and null
   replicates. Inputs, code/protocol and limitations must be identified.
3. **Owner report:** artifact-associated scores supplied by the owner. A public
   account's equal score does not independently authenticate a particular file.
4. **Team-authored source claim:** sibling pages and registers. Useful for review
   and novelty, not an organizer score receipt or causal proof.
5. **Hypothesis / unavailable:** conditional physical reasoning or an unresolved
   source. Neither may be presented as a measured result.

## Official and research sources

| Source | Fact checked | What it does NOT establish | Evidence |
|---|---|---|---|
| [DrivenData problem](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) | incomplete provided catalogue; probability/confidence GeoTIFF; float32, UTM11N, 100 m; triangular 300 m DTI, alpha=.2/beta=.8 | identity/type/coverage of every hidden fault; a local catalogue score is not the leaderboard | page read; `gems.metric` worked-example and masking tests |
| [Staff exact-pixel masking clarification](https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516/4) | known pixels themselves are excluded; predictions beside them can still be penalized; new truth may be within 300 m of known traces | a 300 m exclusion buffer around all known faults | both exact/binary scorers repaired; adjacent-new-truth regression test |
| [Staff test-source clarification](https://community.drivendata.org/t/how-were-the-new-test-faults-identified-data-sources-and-fault-types/11527/7) | hidden sources/types/coverage are not disclosed; Phase 2 expert review matters | assuming all test faults are quaternary scarps, blind conduits or ring faults | interpretation guard |
| [Official leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) | 2026-10-02 page read: DARD #1 .3195; rows #26 .1922 and #28 .1894 | which file generated any account score; permanence of this snapshot | page text read; no artifact-to-account checksum/receipt, so no H19 file score inferred |
| [Lopez-Paz & Oquab paper](https://arxiv.org/abs/1610.06545), [full PDF](https://arxiv.org/pdf/1610.06545) | two samples labelled by origin; classifier trained separately from held-out evaluation; original statistic is accuracy, with an iid null | a causal access explanation from classification alone; applying an iid binomial null to autocorrelated pixels | Sections 2–3 read; implementation declares AUC/spatial adaptation and refits each randomization |
| [USGS GeoDAWN release](https://www.sciencebase.gov/catalog/item/657e1d85d34e23d3533209f7), [DOI](https://doi.org/10.5066/P93LGLVQ) | official report, ReadMe, metadata, combined data extent, Area1/Area2 outlines and flight paths are downloadable | that Area1/Area2 are the four operational blocks or that a report figure / metadata title is a georeferenced block polygon | direct CI receipts, preserved official documents, one combined extent and inventories; flight-line fields are `Id`/`Line` only |
| [Official contractor report](https://www.sciencebase.gov/catalog/file/get/657e1d85d34e23d3533209f7?f=__disk__2b%2F67%2Fb4%2F2b67b4e0d88525acc1ae32cf17b8fd001395bf52) | Fig.3 / pp.5–6: four operational block names; only two acquisition regimes—Area1 200 m traverses/2 km ties and 100/150 m drape, Area2 400 m/4 km and 150/200 m; Area1 is in Tonopah, flown by helicopter with the other blocks' planned layout/drape | numeric four-block polygons; a distinct line-spacing/height for each block; nearest base town means ownership of a pixel | `data/external/audit_sources/*Report.pdf(.txt)`; Figure 3's block outlines are not georeferenced; report lines confirm ≥2 km tie-line overlap |
| [BLM closed claims layer](https://gis.blm.gov/nlsdb/rest/services/Mining_Claims/MiningClaims/MapServer/2?f=pjson) | closed mining-claim legal-land polygons, native NAD83, queryable without login | exact stakes, workings, ore bodies, complete historic field accessibility or causation | 702,794-ID checked snapshot; 197,346 unique accepted geometries; full raw and derived hashes; 20 km buffer; explicit quality policy |
| [Census TIGER 2024 roads](https://www2.census.gov/geo/tiger/TIGER2024/ROADS/), [2024 MTFCC definitions](https://www2.census.gov/geo/pdfs/maps-data/data/tiger/tgrshp2024/TGRSHP2024_TechDoc_E.pdf) | Census 2024 Road/Path classes include S1400 local roads, S1500 vehicular trails, S1710 pedestrian trails, S1820 bike paths and S1830 bridle paths; official buffered acquisition includes 32 complete counties and excludes internal-use S1750 | every informal hiking route is present; an accessibility association is causal | county ZIP URLs, bytes and SHA-256s in `data/external/audit_sources/tiger_road_receipt.json`; 20 km raster-source buffer; no outside-window clipping |
| [USGS MRDS](https://mrdata.usgs.gov/mrds/) | mineral-occurrence inventory, with updates ceased in 2011 | mining-claim polygons/history | explicitly excluded from nuisance inputs; old claim substitution retired |
| [INGENIOUS/GDR](https://gdr.openei.org/submissions/1391) | TC refers to thermal conductivity; earthquake-density definitions depend on source conventions | every inherited band alias is correct; TC is automatically a heat-flow measurement | ambiguous tc/earthquake aliases deliberately excluded; bridge band order caveat remains |
| [Faulds & Hinz 2015](https://www.osti.gov/servlets/purl/1724082) | among characterized geothermal systems, stepovers/terminations/intersections are important; 39% of the 426 known ≥37°C systems were blind | those percentages are pixel-fault prevalence or a ring-fault leaderboard prior | physical motivation only; target is faults, not known geothermal sites |
| [Great Basin play-fairway study](https://www.osti.gov/servlets/purl/1724109) | integrated structure/thermal evidence; surface thermal outflow can be displaced from upflow; confirmation requires field/drilling evidence | a thermal blob uniquely identifies the missing conduit or fault | competing-explanation warning |
| [USGS 3DEP 1/3-arc-second collection](https://data.usgs.gov/datacatalog/data/USGS:3a81321b-c153-416f-98b7-cc8e5f0e17c3), [The National Map/API](https://www.usgs.gov/tools/download-data-maps-national-map) | official free/public-domain approximately 10 m product; TNM API query for bbox `(-120.0,38.5,-119.9,38.6)` returned 13 catalog records including downloadable GeoTIFFs | study-wide tiles have not been byte-downloaded, mosaicked or coverage-checked | H24-6 remains deferred; the prior guessed `.../13/TIFF/current/n39w119/...` URL returned HTTP 500 and is retired |
| [Prize rules](https://docs.nlr.gov/docs/fy26osti/96647.pdf) | weekly limits, final selection, licensed external-data obligations and AI/code/narrative disclosure | permission to circumvent quotas across repos/accounts; an assumed deadline conversion | rules/platform time discrepancy flagged, not guessed |

## What H19-4 and H19-5 actually do

Pinned source and consulted-file hashes are in `evidence/group_review.json`.
For direct review use the H19 `src/gems/hypotheses.py` source link in that receipt,
lines 301–395, and its evaluation script. All 21 supplied project source pages
were read successfully; this is a **source-code review**, not proof that every
public deployment matches the pinned commit or that every page's score is official.

- H19-4 builds L1 tip/population, L2 thermal, L3 openness/scarp and L4 anti-piedmont
  combinations. In LiDAR-covered pixels, the final mixture is **.57 L3 + .35 L4 +
  .04 L1 + .04 L2**: **92% topographic/scarp-family terms**. In gaps it is
  .506/.35/.072/.072. These are coefficients, not measured causal contributions.
- H19-5 changes both within-line mixtures and final weights: **.55 L3 + .35 L4 +
  .05 L1 + .05 L2** in covered pixels (90% L3/L4), .48/.35/.085/.085 in gaps.
  It increases the H19 openness/LRM contribution and thermal/tip emphasis.
- Both perform per-quadrant CDF matching in LiDAR gaps and attenuate a pixel
  using the second-largest line score. That is an engineered corroboration
  heuristic, **not a statistical independence test**; L3/L4 share terrain inputs
  and other components share geological/label-derived context.
- Requested ridge budgets are **2.50% versus 2.45%**; H19-5 is not simply H19-4
  with a new filename or only a new budget. Proper ablations would hold all but
  one of the weights, gap calibration and budget fixed.
- Local byte inspection finds **123,779 / 121,131 positive pixels**, respectively,
  both zero on all **60,988 provided catalogue pixels**. Intersection 107,106;
  union 137,804; **Jaccard 0.777234**. This confirms similar but distinct outputs;
  it does not explain the hidden test score causally.

A plausible performance explanation is that well-localized thin scarp/relative-
relief candidates, restrained anti-piedmont filtering and gap treatment improve
alignment and false-positive allocation under the 300 m DTI. Physical context
can be useful for buried structures. **The .0028 owner-reported score difference
cannot identify which mechanism caused it**, and neither score proves geological
or mapping-process independence. H19-5 already beats .1894; no new leaderboard
improvement is claimed for this project.

## C2ST method correction and audit status

`evidence/accessibility_audit_v2.json` is retained only as history and is now
**superseded / not confirmatory**. Its feature set included Area1 membership
when the requested four operational blocks were missing, violating the explicit
no-substitution rule. Its primary 10 km whole-group label flips assumed
exchangeability not established for this design, and its spatial shifts used
`np.roll`, which wraps an irregular footprint across opposite edges. Its archived
AUCs (labels .528330; H19-4 .565964; H19-5 .564592; candidate .534765) are not
a valid full-nuisance audit result and must not be used to pass a gate or make an
accessibility conclusion.

The corrected implementation excludes Area1/Area2 from the classifier,
requires all four block categories to be present together, and uses a
non-wrapping translation of the full reference mask as the spatial null
sensitivity. It preserves/refits the same classifier and fold protocol for each
evaluable shift; shift draws that lack both classes after purging are rejected on
geometry/support only, never on the AUC. Its empirical upper-tail area assumes
approximate spatial stationarity and is **not an exact randomization p-value**.
Holm correction and the AUC/effect-margin thresholds are reported as cautious
diagnostics, not causal evidence.

Until machine-readable true four-block membership is available, labels and
predictions may be compared only with the available official road/trail and BLM
closed-claim distances and the result must be marked **incomplete**. A
non-rejection is not proof of equal distributions. Residualization removes only
a fitted conditional mean; remaining nonlinear/variance dependence requires
re-auditing the exact final raster.

## Limitations to keep visible

- Historical emitted-raster diagnostics do not reconstruct original H19 OOF
  training/evaluation. Their leakage/comparability cannot be certified.
- Dense and sparse truth reuse an incomplete mapping catalogue. Sparse is a
  20%-component **gap simulation**, not true hidden discoveries or an unbiased
  estimate of leaderboard DTI.
- The 1.5 km collar does not make all physical image context independent:
  annular backprojection can use context out to approximately 4.8 km, and global
  unlabelled descriptor normalization is transductive. No validation **label**
  enters the fitted features/nuisance model, but spatial dependence remains.
- An annular coherence feature is not a ring-fault classifier. Intrusion rims,
  erosion, generic contacts and some locally tangent sharp edges can respond.
  Geophysical/topographic agreement is not independent evidence by itself.
- Detector numeric settings were fixed in the implementation before first fit;
  the initial preregistration explicitly fixes transforms, splits, budget and
  decision gates, but does not separately enumerate every HGB/residualizer
  numeric setting. Do not overstate its completeness or silently amend it after
  seeing folds. No outer-fold hyperparameter search was performed.
- Claim geometries have PLSS resolution; TIGER is not a complete walking-access
  model. Their association with true geology is an alternative explanation.
- Owner-mirror feature hashes do not independently authenticate organizer band
  semantics. No input names or score identities are invented to fill gaps.
- Official metadata itself has placeholders (`<class 'str'>`), a Winnemucca title
  despite a full-survey extent, and 151,799 final line-km versus 149,030 acquired
  in the contractor report. Different accounting is possible but **unverified**;
  do not use those discrepancies to infer block boundaries.


## Pass-2 correction, v3 audit and latest holdout (2026-10-02)

### Official road/trail distance bridge

The original tight-box road mirror was not valid for nearest-road distances at
all output pixels. That defect is **resolved for the current source raster** by
the GitHub Actions buffered-road workflow `37028471805`; artifact commit
`205ff15` records the regenerated raster and receipts. Source county CRS is
EPSG:4269 (NAD83 geographic). All 32 intersecting California/Nevada counties
were checked; the bounding box `[-120.5, 37.0, -115.9, 41.0]` has a 20 km buffer
around the seed grid and no outside-window clipping. Current distance-raster
SHA-256 is
`459af5cf2247d07580af42f737533863749166cd42027a0d340745ceb3ed21b8`.

The 2024 Census technical document's Road/Path MTFCC allowlist was applied.
It admits selected Road/Path classes (including local roads, vehicular trails,
pedestrian paths, bike paths and bridle paths); **183 S1750 internal-use
features were excluded**, as were unknown/non-road codes. Per-county ZIP URLs,
byte sizes, hashes, CRS metadata and code counts are in
`data/external/audit_sources/tiger_road_receipt.json`. This is not a complete
hiking network or travel-time model. Initial CRS failure evidence is retained as
superseded in `evidence/official_roads_initial_crs_failure.json`.

### Corrected available-family classifier two-sample audit

`evidence/accessibility_audit_v3.json` tests the training labels first, then
H19-4, H19-5, and the exact H24-3A experimental raster, using only the two
available permitted families: road/trail distance and historic closed-claim
distance. It uses 12,000 samples per class, four spatial folds, the 10 km
spatial-group purge plus 1.5 km collar, 199 valid non-wrapping mask translations,
classifier refits, and Holm adjustment. The primary shift-tail probability is a
stationarity sensitivity diagnostic, not an exact spatial randomization p-value.
True four-block membership remains unavailable, so this is explicitly **not a
full requested audit**; Area1/Area2, label seams and geological proxies do not
enter.

| Reference | C2ST AUC | Shift-null p95 | AUC − p95 | Raw shift tail | Holm shift diagnostic |
|---|---:|---:|---:|---:|---:|
| Training labels | 0.53021 | 0.57133 | -0.04111 | 0.175 | 0.280 |
| H19-4 | 0.56264 | 0.56978 | -0.00714 | 0.080 | 0.280 |
| H19-5 | 0.56697 | 0.57265 | -0.00568 | 0.070 | 0.280 |
| H24-3A exact experimental raster | 0.54388 | 0.58023 | -0.03635 | 0.115 | 0.280 |

No raster meets the declared available-family flag (`Holm <= .05`, AUC >= .55,
margin >= .02). This is **not evidence of no accessibility bias** because the
four-block feature is missing and the stationarity null is approximate. Single-
feature diagnostics are descriptive; mining-claim proximity is more predictive
than road proximity for the H19 rasters, but this is not a causal explanation.

The exact experimental raster at
`out/h24-3a-contact-persistence-20261002-experimental.tif` has SHA-256
`3555997c584fb79777c5380fc9c0937c88afc02703be067eb3e487006a565c3f` and passes
the organizer-grid/format checks. It is not recommended for upload.

### H24-3A contact-persistence holdout

The preregistered challenger upward-continues RTP, TMI and gravity using the
spectral transfer `exp(-2*pi*h*|k|)` at 100/200/400 m, then scores
neighbourhood-tolerant gradient persistence and orientation stability. Because
the exact kernel is nonlocal, a 20 km training exclusion collar was declared
before fitting. The experiment used the same four contiguous quadrants, 80-step
HGB settings, 2.45% ridge budget, training-only nuisance/residual transforms,
and no held-out labels in supervised class sampling. Only official road and
closed-claim distances were available; true blocks remain missing.

| Arm | Mean dense DTI | Mean sparse DTI |
|---|---:|---:|
| Physics raw | 0.13109 | 0.04564 |
| Physics + H24-3A raw | 0.13824 | 0.05214 |
| Physics residualized | 0.14305 | 0.05306 |
| Physics + H24-3A residualized | 0.14980 | 0.05523 |
| H19-4, emitted raster | 0.17043 | 0.06850 |
| H19-5, emitted raster | 0.16944 | 0.06813 |

Against the residualized baseline the challenger gains 0.00675 dense and 0.00217
sparse on average, but sparse DTI improves in only 2/4 folds and one fold loses
0.00256; the paired gate fails. It also loses to both historical H19 rasters as
emitted. Original H19 OOF training is not reproducible from available caches.
No slot was consumed, no new leaderboard score exists, and no candidate is
promoted. The archived H24-2A experiment is separately marked historical only:
it used Area1 as a forbidden acquisition proxy and legacy clipped-road inputs.

The v2 audit remains non-confirmatory for the earlier documented reasons
(Area1 substitution, toroidal shifts and invalid grouped exchangeability). The
latest v3 values above supersede its AUCs; neither report demonstrates causal
access bias or its absence.
