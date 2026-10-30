# Repository review — 2026-10-30 — `arena/6a29c5b2-gemsdoe24`

## Decision first

**No new TIFF, no new geological experiment, no score estimate, and no submission slot. SUBMIT: NO.**
The requested “single method paragraph” is not present in the current task, and the repository's standing instructions require that paragraph to assign the one permitted lane. I will not invent a lane, restart a stopped one, or use a private runner. The prescribed holdout cannot be run in this checkout because the full training raster and prepared feature cache are absent; the Python runtime also lacks NumPy, Rasterio, scikit-learn, pytest and Ruff. This is a deliberate negative result, not a claim that the requested high-scoring unique candidate was achieved.

The README already links the normalized mission prompt and nine-site executive guide. The historical nine-site page says the highest *owner-reported* claim is the GEMSDOE32 B2 artifact; it is not an organizer-confirmed score, a current leaderboard result, or evidence that the file is a suitable submission. Its geometry is a pruning of a predecessor raster, not a new geologic detection. A prediction for hidden leaderboard performance is **NOT ESTIMABLE**.

## What the existing evidence says about GEMSDOE32 B2

The immutable historical readback in [`docs/data/historical_champions_20261028.json`](data/historical_champions_20261028.json), the overlap receipts, and [`knowledge/14_h33_analysis_2026-10-25.md`](../knowledge/14_h33_analysis_2026-10-25.md) support a narrow geometric finding: B2's positive pixels are a subset of the GEMSDOE25/30 D2.8 pattern after removing predictions within 200 m of the public catalogue; the recorded comparison added no prediction locations. The source-reported B2 value has no artifact-linked organizer receipt in this checkout.

A plausible explanation for its reported ordering is a **precision–recall trade-off** under the distance-weighted Tversky metric: deleting predictions can reduce weighted false-positive mass, while losing any nearby hidden-fault credit can reduce true-positive mass. The 300 m triangular kernel means spatial proximity matters, and the asymmetric penalties do not imply that fewer dots always score better. But hidden truth and its weighted TP/FP/FN decomposition are unavailable; therefore the causal explanation is **not established**. The observed geometry cannot show that B2 found a concealed fault, geothermal vent, or permeability conduit. Nor can a source-reported point score establish it beats other submissions or the current leaderboard.

The user-provided leaderboard snapshots conflict. Neither snapshot was authenticated from an artifact-linked organizer receipt in this review. We did not access DrivenData, refresh a live leaderboard, authenticate, or upload anything. Consequently, we cannot responsibly claim a new method beats B2 or estimate a leaderboard score.

## Nine-site executive decision

Use the existing [nine-site historical champion table](historical-champions.html) as the file-by-file record. It includes exact downloadable TIFF names and immutable source links, source-reported values with their provenance labels, `NOT ESTIMABLE` leaderboard estimates, format checks and per-file decisions. Its scope is a frozen set of one historical champion per site, **not** each site's latest head or every submission. It is not a live refresh.

| Focus site | Historical file/method represented in the pinned table | Leaderboard estimate | Unique vs the focus set / literal registry gate | Action |
|---|---|---|---|---|
| GEMSDOE24 | H25-1 dotted H19-5, D1.5 | NOT ESTIMABLE | No; fails literal lattice overlap gate | Research/audit only; do not submit |
| GEMSDOE25 | Dotted H19-5, D2.8 | NOT ESTIMABLE | No; same in-footprint predictions as GEMSDOE30; fails literal lattice gate | Research/audit only; do not submit |
| GEMSDOE27 | Topographic gap-closure, D1.5 | NOT ESTIMABLE | No; fails literal lattice overlap gate | Research/audit only; do not submit |
| GEMSDOE28 | H36 blind rung-30 | NOT ESTIMABLE | No; fails literal lattice overlap gate | Research/audit only; do not submit |
| GEMSDOE30 | D28 Poisson 300 m off-catalogue | NOT ESTIMABLE | No; same in-footprint predictions as GEMSDOE25; fails literal lattice gate | Research/audit only; do not submit |
| GEMSDOE31 | H27-4 solo D28 | NOT ESTIMABLE | No; fails literal lattice overlap gate | Research/audit only; do not submit |
| GEMSDOE32 | H33 B2 | NOT ESTIMABLE | No; fails literal lattice overlap gate | Historical reported high only; do not submit |
| GEMSDOE33 | H33D analogue tip/stepover | NOT ESTIMABLE | No; fails literal lattice overlap gate | Research/audit only; do not submit |
| GEMSDOE36 | Anderson geothermal PINN | NOT ESTIMABLE | No; fails literal lattice overlap gate | Research/audit only; do not submit |

“Fails literal lattice gate” refers to the retained spacing-5 calibration witness in the frozen audit—not proof of copying and not a full current registry census. The historical audit reports near-total 3-pixel overlap with that witness for the nine selected artifacts. Pairwise near-identity among these rasters is a separate observation; shared output geometry does not prove their underlying methods or source files were copied. Do not download any of these for submission.

## Candidate hypotheses — ranked research queue, not lane assignments

These are qualitative expected-information-per-cost rankings, **not numeric DTI forecasts**. “Unexecuted” here means no completed matching experiment was found in the local repository search; it does not certify the idea is globally novel or reconcile every parallel PR. The first two ideas resemble proposals already recorded in [`docs/research-directions-20261027.md`](research-directions-20261027.md), and the repository notes overlap with open parallel work. Reconcile that history before calling either new. No candidate can be run until a lane is explicitly assigned.

| Rank | Candidate layers and physical signature | Why it could reveal a catalogue-missing fault | Named non-fault mimic | Difference from implemented methods | Expected DTI value / cost / viability |
|---|---|---|---|---|---|
| 1 | Cached `rtp` and `iso_grav_anom`: scale-fixed signed cross-gradient, testing a polarity reversal across a locally estimated `det_elev` line tangent | A buried splay or oblique structure could juxtapose magnetic and density contrasts without a sharp mapped scarp; signed reversal tests an interface relation rather than another single-layer ridge | Intrusive contact, remanent magnetization, flight-line or gridding seam | Existing work includes unsigned cross-gradient/co-alignment, magnitude and structure-tensor approaches; the signed gravity–magnetic reversal is a different preregistered transform, but its prospective form is already documented | **Potential:** moderate, unquantified. **Cost:** medium if exact cached stack restored. **Not viable now:** `data/training_features.tif` and `data/prepared/features.npy`/metadata are absent; source-band meaning is not independently authenticated. |
| 2 | Cached GeoDAWN `K`, `Th`, `U`: fold-fitted conditional K-rank residual given Th/U ranks, then a robust cross-front gradient | A localized compositional alteration front might trace fluid flow along a buried structure not represented by mapped surface faults | Lithologic sorting/weathering, moisture, vegetation, or acquisition-block effects | Differs from fixed radiometric ratios/contrasts by fitting conditional ranks on training folds only; related radiometric rank work exists and overlap with the historic proposal/parallel PR must be reconciled | **Potential:** low-to-moderate, unquantified. **Cost:** medium. **Data:** a local contractor-derived uint8 grid is present, but that alone does not prove its source identity, units or full-stack readiness. Not testable with current runtime/cache. |
| 3 | Official USGS ASTER hydrothermal-alteration mineral-group maps plus `rtp`/gravity: signed lateral offset between an elongated mineral transition and an independently derived geophysical front | A fluid-alteration halo displaced from a buried structure may persist where no mapped scarp exists | Volcanic/lithologic boundary, older mineralization, mine disturbance, vegetation or atmospheric artifact | Targets mineral-group transitions and signed displacement rather than the repository's radiometric/thermal proxies | **Potential:** moderate but highly uncertain. **Cost:** high (download, spatial coverage, registration, cloud/vegetation masks, provenance). **Not viable now:** no ASTER files are present and this sandbox cannot verify current coverage or obtainability from the official source. Do not treat the source page as proof that a usable raster is obtainable for this footprint. |
| 4 | NASA OPERA Sentinel-1 displacement time series, if exact footprint coverage can be verified: coherent cross-fault velocity gradient and temporal persistence, intersected with existing subsurface lineaments | Persistent differential deformation may reveal active structure beneath alluvium without relying on surface relief | Groundwater/seasonal hydrology, subsidence, vegetation decorrelation, atmospheric delay, processing seams | Adds an independent time-series deformation modality rather than another static geophysical/DEM transform | **Potential:** uncertain. **Cost:** very high (access, stack processing, temporal QA, alignment). **Not viable now:** no OPERA raster or verified collection/coverage receipt exists locally, and obtainability could not be checked. Source pointer in prior repo notes: [NASA Earthdata CMR OPERA DISP-S1](https://cmr.earthdata.nasa.gov/search/collections.json?short_name=OPERA_L3_DISP-S1_V1); not freshly retrieved here. No score claim. |

For any future authorized experiment: withhold whole fault segments plus buffer; build every catalogue feature from visible faults only; mask those visible pixels exactly; run each feature alone as a leakage canary; test surface novelty before placement and dot overlap afterward against the current registry; use the shared pooled DTI evaluator and writer; stop at the three-experiment/two-hour limit. A feature-only AUC over the specified threshold is leakage until disproved. A candidate must beat the comparable holdout best with paired uncertainty and pass the separate selector; holdout is not an organizer score or a leaderboard forecast.

## Verified checkout facts and blockers

- Branch is `arena/6a29c5b2-gemsdoe24`, initially at the same base commit as `main`; no unrelated pre-existing work was present in the working tree.
- Present: `data/bridge/labels.tif`, `existing_faults.tif`, and `sample_submission.tif`; selected external files include GeoDAWN radiometric/extension caches and GDR/INGENIOUS resources.
- Absent: `data/training_features.tif`, `data/prepared/features.npy`, and `data/prepared/features.json`. This means the request to reuse the prepared cached stack cannot be fulfilled from the current checkout.
- The runtime has no NumPy, Rasterio, scikit-learn, pytest or Ruff. Consequently, no GeoTIFF was reopened with the current validator, no pipeline or holdout was executed, and no project test suite was run. Do not mistake historical validation receipts for a fresh pass.
- `python scripts/check_protocol_feasibility.py --dots 37654` was run. It returned exit code 2 from a pure-Python arithmetic check over the frozen nine-site audit (checked 2026-10-27; no raster remeasurement or live refresh): the lower-bound overlap is 0.823418…, above the literal 0.70 limit. This proves that this fixed dot budget cannot pass that one necessary gate; it does not prove the calibration raster is a valid competitor, certify a smaller budget, or establish scientific merit. The more rigorous raster-opening preflight could not run because NumPy/Rasterio are absent. Do not change a stopped method's budget or target lattice holes to evade the gate.
- README and the normalized [mission prompt](MISSION_PROMPT.md) already direct each session to the core values **Maximize P(Win)** and **Own the Outcome**. This review added no prediction TIFF and therefore has no raster SHA-256 or submission note.

## Sources for manual review

These are relevant official/reference links already recorded in the repository; this session did not freshly retrieve their pages. They are source pointers, not fresh coverage, license, portal or account checks.

- [DrivenData problem and metric](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) and [competition data page](https://www.drivendata.org/competitions/306/competition-doe-gems/data/) (repository records the data page as login-restricted; no automated access attempted).
- [DrivenData reference solution](https://github.com/drivendataorg/gems-prize-reference-solution).
- [USGS GeoDAWN release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and), DOI `10.5066/P93LGLVQ`.
- [OpenEI GDR #1391 / INGENIOUS](https://gdr.openei.org/submissions/1391).
- [USGS ASTER alteration/mineral-group release](https://www.usgs.gov/data/digital-maps-hydrothermal-alteration-type-key-mineral-groups-and-green-vegetation-western), DOI `10.5066/F7CR5RK7`.
- [USGS 3DEP products](https://www.usgs.gov/3d-elevation-program/about-3dep-products-services).
- [Submission rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf) (the user-provided URL; not freshly opened in this review).

## Three-pass review record

1. **Inventory:** read README, mission prompt, AGENTS and current historical review; checked repository state, current data placement, scripts, nine-site table and saved run cards. No live competition page or other GEMSDOE site was refreshed.
2. **Challenge:** independently checked presence/absence of inputs and Python modules, inspected the DTI implementation and B2 forensic note, and ran the frozen arithmetic feasibility checker. Confirmed the score explanation is only plausible, not causal; the high reported value has no organizer receipt.
3. **Close-out:** wrote a negative run card with null holdout/overlap/hash/validator fields because no candidate was emitted; did not create or rename any raster. Corrected a broken README markdown link to the existing blind-upwell run card, parsed the new JSON and asserted negative/null fields, checked local links in README/mission/review, and ran `git diff --check`; all passed. Full tests, lint, TIFF validation and Pages build remain unverified due missing dependencies.

## Remaining work / limitations

1. Obtain the missing official competition inputs and restore the cache through an authorized route, preserving hashes and provenance; then install the pinned requirements and run `prepare_data.py`.
2. Have the coordinator assign the single paragraph/lane and resolve the prospective calibration-lattice policy. Reconcile the relevant parallel PR and exact implemented methods before choosing any hypothesis.
3. Only then preregister and run a source-available candidate with feature-wise leakage canaries, shared segment holdout, both novelty checks and a strict output validator; stop at the configured budget.
4. Refresh immutable GitHub source pins under the permitted GitHub channel and audit every new artifact. Do not use GitHub Pages result text as organizer confirmation.
5. A separate selector must confirm scientific promotion and current registry uniqueness; the owner must handle any authenticated submission and provide an artifact-linked organizer receipt. No submission slot is approved by this review.
6. Investigate the reported `[0,1]` portal error only against the exact rejected bytes and an organizer response. The cause remains unknown; a local validator is not portal acceptance.
7. Preserve the existing executive guide's one-click research download and clear `SUBMIT: NO` labels; do not replace them with an unvalidated TIFF. Refresh its nine-site snapshot only when sources are permitted and changes are audited.

**Bottom line:** GEMSDOE32 B2 is the highest historical owner-reported entry in the pinned nine-site snapshot, but it is not an evidence-backed submission recommendation. There is no basis here for a higher-scoring unique submission, no valid current score estimate, and no generated file safe to submit. The correct outcome is to stop, record the blockers, and continue only after inputs and lane authorization are resolved.
