# H24-TNR1 — preregistration, 2026-10-26

**Read the owner brief in README first. Maximize P(Win); Own the Outcome.**

## Governance and hard limits

The current message still omits the promised assigned single-method paragraph.
This is an **autonomously selected, unassigned RESEARCH lane**, not a claim of
coordinator assignment or permission to use a slot. This explicitly departs from
the previous review's recommendation to wait for assignment, in order to carry
out the renewed request for autonomous generation. This governance gap alone
prevents promotion. No historic negative lane is rerun, retuned, or relabelled.

One fixed new hypothesis, one candidate arm, one matched raw control, at most
three experiment arms / two hours in this session. The control is a prospective
baseline replay, not another candidate search. No tuning after a result. Stop at
the first failed canary or surface/final-dot duplicate gate. Keep the literal
all-entry rule, including the spacing-5 control. Do not move dots to evade it.
The unchanged candidate may be written once **before** its final-dot check for a
format/audit deliverable; a duplicate must remain DOWNLOAD YES / SUBMIT NO.

## Four not-yet-executed candidate tests, ranked before implementation

Priority is qualitative expected incremental information per cost, **not a DTI
forecast**. Novelty means the named operator was not found in the reviewed local
Python implementation, not global novelty or absence from unseen parallel work.
Existing physical layers are explicitly reused; a new statistical test does not
make those layers new geological discoveries.

| Rank | Geological/inference hypothesis and exact layers | Signature and missing-fault rationale | Distinction from implemented code | Named non-fault mimic; cost; availability |
|---|---|---|---|---|
| 1 | **TNR1: preserve tectonic deformation while removing survey/access response only from non-topographic channels.** The cached 27 model columns plus SAHG1 `G_sat`, `R_alt`, `B_step`, `H_conduit`. | The anti-slope scarp/paired curvature/strike-persistence signal may contain deformation information lost when FUSE residualizes *every* channel. Conditional magnetic/gravity/conductivity/alteration evidence could recover short fault splays rather than repeat catalogue-distance geometry. This is a test of the information-bearing geology, not a new field observation. | FUSE-RESID removes nuisance means from all 31 channels; FUSE-HCW additionally reweights by a fixed conduit gate; RSHG1 changes features/regimes. TNR1 selectively residualizes 12 prespecified non-topographic/composite channels and leaves the other 19 unchanged, with no HCW postweight. This executes the unfinished targeted-residualization next step in README. | Tilted volcanic tuff cuestas and pluvial shorelines intersecting access/mining corridors; moderate CPU cost; all inputs locally hash-verified. Selected once. |
| 2 | **Signed cross-gradient chirality reversal**, cached `rtp`, `iso_grav_anom`, `det_elev`. | A localized change in the sign of the normalized 2-D cross product of magnetic and gravity gradients along a persistent terrain break could indicate an oblique fault cutting a lithologic boundary. May highlight an omitted cross-fault rather than the mapped range-front. | Existing GVC1 uses lineament maxima/tilt and SAHG1 magnitude corroboration; this would test the *signed* along-strike reversal of the cross-gradient, not larger gradient amplitude or generic edge co-location. | Intrusive contact geometry and remanent magnetization; medium implementation cost; cached fields available. Not run. |
| 3 | **Lithology-conditioned ordinal K front**, cached GeoDAWN K, Th, U and contractor Th/K, U/Th. | A sharp cross-normal gradient in the training-only conditional K residual given Th and U, with little Th/U ordinal change, might isolate an alteration front crossing parent lithology and a missing branch under cover. | Earlier OJ1 proposed log(K/sqrt(Th U)), but the cache lacks concentration-reconstruction endpoints. Do **not** take physical ratios of independently scaled bytes. This new proposal is explicitly an ordinal conditional-response test, not a quantitative compositional balance or SAHG1's fixed K/U contrasts. | Arkosic sediment sorting, moisture, lithologic contacts; medium cost; quantized caches present, absolute geochemical claim not viable without original official grids. Not run. |
| 4 | **Signed terrain-flexure dipoles corroborated by basement steps**, cached `det_elev`, `det_local_relief`, `depth_to_base_surf`, geodetic dilatation/shear. | Opposite-sign broad curvature lobes on either side of a narrow basement edge could indicate a concealed flexural fault where a crisp mapped scarp is absent. Test a paired cross-normal profile with a complete finite-stencil support mask. | RSHG1 uses pointwise Hessian curvature and CON a conductivity saddle; this would require a separated signed-lobe pair and broad strain corroboration. It cannot recover subpixel crest/toe locations from LiDAR maxima. | Erosional terrace/valley pair or dune/alluvial-fan curvature; medium cost; cached descriptors present, 100 m resolution and broad strain are serious limitations. Not run. |

No new external source is required by the selected test. Finer DEM or original
radiometric-concentration followups are **deferred**, not advertised as available:
USGS 3DEP https://www.usgs.gov/3d-elevation-program/data-tools and USGS GeoDAWN
https://doi.org/10.5066/P93LGLVQ are the specific official sources; their hosts are
outside this environment's allowlist, so new tile/archive obtainability is not
verified here.

## Fixed TNR1 method paragraph

Use exactly the prepared 27 base physical/DEM/LiDAR columns, with the four frozen
SAHG1 feature definitions `saturating_scarp_g_sat`, `radiometric_alteration_r_alt`,
`basement_step_b_step`, `hydrothermal_conduit_h`. Use SAHG1's verified complete
9x9 support mask. Reuse its definitions as a fixed label-free physical feature
product, **not** its old prediction pixels. Its survey-wide robust sigmoid is
transductive preprocessing, not a fresh training-only calibration; retain that
limitation explicitly.

Residualize **only** these 12 named columns:
`rtp`, `tmi_hg`, `tmi_vg`, `iso_grav_anom`, `iso_grav_anom_hg`,
`iso_grav_anom_vg`, `tmi`, `cond_surf`, `depth_to_base_surf`,
`radiometric_alteration_r_alt`, `basement_step_b_step`, `hydrothermal_conduit_h`.
Keep the remaining 19 columns (DEM, geodetic strain, LiDAR and `G_sat`) bitwise
unchanged, including their missingness. Nuisance basis uses only log-distance to
roads/claims and four one-hot acquisition blocks via shared `confounds` and
`NuisanceResidualizer(alpha=100)`. Blocks remain **derived, line-km audited, not
official coordinates**. No nuisance column is fed directly to the fault model.

- Shared `SegmentHoldout(buffer_px=15)`, evaluator `gems-segment-pooled-v1`:
  hide whole components touching each quadrant or collar everywhere, purge
  training by 1.5 km from the validation region and entire hidden components;
  derive all catalogue-dependent sampling distances from `fold.visible` only.
  Pixel-exact visible-fault mask. Pooled TPw/FPw/FNw, alpha .2, beta .8,
  300 m triangular kernel; 1,999 spatial 10 km bootstrap resamples.
- RNG seed `20261026`; training positives up to 20,000 and negatives up to
  60,000, negatives at least 9 px from visible faults; uniform **training-only**
  30,000-row sample for nuisance imputation/scaling/spline fitting.
- One 31-column TNR1 HGB and one 31-column raw control per fold. Both use
  `max_iter=80`, `max_leaf_nodes=15`, `learning_rate=.08`,
  `l2_regularization=5`, `early_stopping=False`, seed above. Chunk inference in
  75,000 rows, no whole-footprint dense feature copy. No HCW weighting.
- Screen every actual raw model input alone (two AUC polarities, all folds),
  support/missingness, each OOF residualized input and the candidate surface.
  Use shared canaries, **not** in-sample predictions or fitted full-catalogue
  features for the OOF canary. AUC > .90 => stop, no feature rescue.
- Registry: retain original priority and peer pins, append a versioned current
  nine-site snapshot plus all existing local research TIFFs **before the run**;
  checksum every entry, deduplicate identical footprint content only (retain
  provenance aliases). Check continuous TNR1 surface before any dot placement
  and exact final dots; never silently skip missing comparisons. All-entry
  rank > .90 or directional 3-px overlap > .70 => duplicate and stop.
- Emit fixed priority-Poisson `min_dist=3`, budget
  `round(.0073 * fold.valid.sum())`, eligibility support AND fold.valid AND NOT
  fold.visible. Same emission for the matched control. No tuning K from scores.
- Compare paired TNR1 vs raw control using shared evaluator/bootstrap. Also
  compare to the **recorded current highest** GVC1 HOLDOUT-DTI .1487628916
  (95% CI [.1341347155,.1637034539], 60,988 positives, same evaluator) and the
  old reconstructed .13000 baseline, without pretending a recorded comparison
  is a new independent best-model replay or hidden-score conversion.
- Fit one full-visible-catalogue TNR1 model with the same sampling/parameters
  for the final surface. It is distinct from the OOF predictions; gate that
  exact final surface before final placement too.
- Shared writer exports a uniquely named `RESEARCH-NOT-SUBMISSION-zeros.tif`
  (whole array finite [0,1]) and NaN-outside companion. Validate both, equal
  interior predictions, grid/CRS/transform/hash; no automatic clipping of bad
  predictions. Note <=140 characters; shared preflight must say DO_NOT_SUBMIT.
- Audit labels first using shared C2ST, then reopen the exact emitted zero TIFF
  for its nuisance-only audit (99 refitted grouped null draws; Holm over the
  two tests). Audit **before** final-dot duplicate check, never continue science
  after a duplicate. Non-rejection is not proof of unbiased geology.
- Verdict remains `negative`: lane not externally assigned, literal novelty
  rule cannot be waived, independent selector/current quota absent. No portal
  automation, no slot use, no forecast or organizer score. A positive point
  comparison alone cannot authorize submission.

## Source/claim boundaries

Freshly confirmed organizer code pin:
https://github.com/drivendataorg/gems-prize-reference-solution/tree/aebe92f7c8a990f0e3443451b7a825d9afd6336b .
Inspect the README/notebook for target, training loss and output examples; do
not present it as independent verification of the complete evaluation service.

Cached official `GeoDAWN_ReadMe.pdf.txt` supports WGS84/UTM11, 50/100 m source
grids and channel semantics. Its local PDF/text hashes will be retained; the
source was **not freshly fetched from USGS**. Team mirrors certify byte
integrity, not original organizer authentication. Official problem/rules links:
https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/ and
https://docs.nlr.gov/docs/fy26osti/96647.pdf . No automated DrivenData requests.

The task is recovery of unmapped fault pixels, **not directly geothermal vents**.
Tuff cuestas, shorelines, lithology, cover and survey/access patterns are real
competing explanations. Reported .2778/.3195/.4413 values are owner claims, not
ORGANIZER-CONFIRMED. Scientific efficacy remains an experiment, not a fact.
