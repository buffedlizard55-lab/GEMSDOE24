# H24-MTR1 preregistration — 2026-10-25

Written and committed before implementing or evaluating this experiment. Budget: **one
experiment with one fixed ablation**, no parameter search; never more than three experiments
or two hours from the session start (2026-10-25 20:00 UTC). No competition upload/slot.

## Lane and scope

The brief refers to a “single method paragraph below”, but contains no actual lane assignment.
Record this as IR-20261025-MISSING-LANE. To proceed autonomously, reserve this provisional,
narrow lane: **paired, signed magnetic troughs with local radiometric corroboration**.
No terrain/scarp features, thermal point locations, prior submission pixels, learned
catalogue-distance habitat, or prune-and-augment operators may enter the detector.
Novelty means unimplemented in the local active pipeline and the reviewed source paths of
the nine priority repositories, not unimplemented by every competitor. A missing explicit
lane assignment and an unavailable independently reconstructed current-best OOF comparator
both veto promotion; negative artifacts are deliverables.

## Ranked geological slate (before implementation)

Expected benefit is qualitative and uncertain, NOT a projected score. All are variants in
the paired-trough lane; only rank 1 is authorized for this experiment.

| Rank | Hypothesis and precise inputs | Physical signature / missing-fault rationale | Difference from reviewed code | Expected benefit / cost | Non-fault mimic |
|---|---|---|---|---|---|
| 1 | H24-MTR1: cached `rtp` in `data/prepared/features.npy`; contractor `ThK` ratio, band 1 of `data/external/geodawn_extensions_u8.tif` | A narrow signed magnetic low bounded by two high shoulders, persistent along strike, with local Th/K depletion. Hypothesis: magnetite destruction and K addition along a concealed alteration conduit could leave no mapped surface scarp. These are hypotheses, not diagnoses. | Repo uses raw bands, annular responses and terrain models; reviewed H33 methods use Hessian line/edge consensus and catalogue-flank pruning, not this two-sided cross-normal signed trough with a ratio residual. No old raster contributes values. | Highest testability per cost; uncertain precision gain, possibly negative; under 30 CPU minutes | Magnetite-poor alluvial paleochannel with K-rich detritus |
| 2 | H24-MTR2: same RTP plus cached TMI and `TMI_up150`, extension band 4 | Require a paired trough to persist after upward continuation while short-wave cultural interference attenuates. Could expose deeper concealed alteration corridors. | A trough survival ratio, not the existing multiscale *edge* persistence or Euler contact depth. | Moderate/uncertain benefit; medium cost; dequantization limitations | A long magnetite-poor lithologic strip |
| 3 | H24-MTR3: RTP paired trough plus contractor `ThK` and `UTh`, extension bands 1 and 3 | Ratio-change asymmetry across both trough shoulders; compare K-related variation with a second radioelement ratio rather than an amplitude-only alteration weight. Could distinguish narrow alteration zones from broad cover. | Cross-normal compositional residuals, not scalar K/Th fusion or a contact-ridge product. | Lower confidence; low implementation cost; quantization may destroy the signature | K-rich sediment sorting or weathering |
| 4 | H24-MTR4: RTP paired trough plus cached `cond_surf` | Conductivity ridge centred *inside* both magnetic shoulders rather than at a single magnetic edge. Candidate blind fluid pathway without a topographic step. | Centred cross-normal offset relationship, not the H32 clay-cap boundary or raw conductivity feature. | Low at the metric's localization scale; low cost | Saline basin-fill channel / clay-rich palaeovalley |

No new external data are needed for rank 1. The actual cached files are readable and their
hashes will be recorded. Official source: USGS GeoDAWN release DOI
[10.5066/P93LGLVQ](https://doi.org/10.5066/P93LGLVQ),
[ScienceBase item](https://www.sciencebase.gov/catalog/item/657e1d85d34e23d3533209f7).
The cached official `GeoDAWN_ReadMe.pdf` explicitly lists `thk_ratio`, magnetic channels,
projection and grid spacing. Current external USGS access is not available from the
sandbox's allowlist; mirror integrity is NOT fresh organizer authentication. No proposal
requiring a new source is called viable without checking availability.

## Frozen operator

1. Reuse `scripts/prepare_data.py`'s memory-mapped feature cache, never reconstruct a
   competing feature stack. Read only its `rtp` column for the detector.
2. RTP: Gaussian sigma 1 px. Regional scale: sigma 8 px, truncate 4. Local residual
   standard deviation from the sigma-8 residual, floor 1e-6. Four cross-normal directions
   at 0, 45, 90, 135 degrees, shoulders exactly 3 px away by bilinear interpolation.
3. Direction response = `max(min(left-centre, right-centre), 0) / local_sd`.
   Along-strike persistence = minimum of the centre response and the mean response at
   +/-4 px along the tangent. Maximum over the four directions. Compress with `1-exp(-x)`.
4. ThK uses the contractor ratio band, NOT a ratio of separately quantized K and Th.
   Zero is nodata. Local depletion = positive `(Gaussian8(q)-Gaussian1(q))/local_sd(q)`;
   compress with `1-exp(-x)`. These are relative quantized units, not physical Th/K values.
5. Candidate surface = `magnetic_trough * (0.5 + 0.5 * ratio_depletion)`.
   Ablation = `magnetic_trough` alone. No tuning of weights/scales/directions after results.
   Erode valid support by 40 px; no toroidal wrapping, no nodata-induced contacts.
6. Shared deterministic positive-only priority Poisson emission, 3 px minimum distance,
   budget `round(0.0073 * evaluation_area)`, no zero-score backfill, no imposed catalogue
   halo. Pixel-exact visible-catalogue exclusion occurs after surface construction.

## Shared evaluator correction (not a private fork)

The repository has `gems.holdout` and `gems.submission`, but not the template filenames
`evaluate_holdout.py` / `submission_writer.py`. Add thin shared command entry points using
those modules. Keep historical evaluator results explicitly legacy, not silently rewritten.

Add a versioned component-blocked protocol to **the shared** `src/gems/holdout.py`:
- Existing four contiguous quadrants. Withhold every complete 8-connected catalogue
  component touching the quadrant or its 1.5 km collar. Remove its pixels everywhere from
  visible faults. No withheld label enters feature generation, imputation, fitted scaling,
  training or masking. The formula has no supervised fit and no catalogue-derived feature.
- Score withheld positives inside the quadrant; visible catalogue is masked pixel-exactly.
  Run on full spatial support so the 300 m kernel is not truncated at an artificial crop.
- Use existing `gems.metric.dti_score_fast` (alpha .2, beta .8, triangular R=300 m).
  **Pool TPw/FPw/FNw across folds before computing DTI**, not the mean of fold ratios.
- 95% percentile CI by 1,999 resamples of 10 km spatial groups, pooling components; report
  the number of withheld positive pixels and components. Correlated geologic structures
  crossing groups mean this is an approximate internal-validation CI, not hidden-score CI.
- Canary: test every actual source/transform channel alone before joint scoring. AUC is
  heldout fault-v-background, with deterministic negative samples at least 900 m from
  withheld truth. Check both polarities (`max(AUC,1-AUC)>0.90` veto), report class counts.
- A paired gain vs the same-run magnetic-only ablation is informative. It is NOT a
  certified win over the unavailable current-best reconstructed OOF model. Historic TIFFs
  may be scored *as-emitted diagnostics only*, never be used as training/candidate inputs.

## Registry / stop rules

Inspect all published submission TIFFs in the nine priority repositories, pinned to the
reviewed commit; include local historic registry TIFFs. Content-deduplicate variants only
after checking their actual footprint values. Record scope and failures.

Before placement: Spearman on a deterministic 200,000-footprint-pixel sample versus each
registry raster; also compare triangular-kernel neighbourhood fields as a disclosed
sensitivity. After placement: repeat rank checks and compute exact directional fraction
of candidate dots within <=3 px of every registry raster's positive pixels. Stop and log
`duplicate` if any rank correlation exceeds .90 or final overlap exceeds .70. No attempt
to add random pixels or change parameters to defeat these gates.

## Outcome and artifact

Write a genuinely independently computed single-band float32 TIFF using shared
`gems.submission.write_submission`; provide a NaN-outside official-text variant and an
all-finite zero-outside troubleshooting variant. Re-read both and verify every requirement;
short note <=140 characters. Primary first-screen download must be the NEW candidate,
with an explicit **DO NOT SUBMIT / negative** state unless all scientific/uniqueness gates
pass. Do not conflate format validity with submission authorization. Keep the exact-file
SHA, scored-content SHA, full validator JSON and a single final JSON run card.

No organizer receipt was supplied for the brief's score claims; do not label any of them
ORGANIZER-CONFIRMED. The brief contains conflicting leader claims (0.4413 vs 0.3195).
No projection is a score. No automatic access to DrivenData and no slot selection/upload.

## Pre-run implementation correction (no experiment result inspected)

Support erosion is **72 px**, not the initially listed 40. Code review shows that
`Gaussian8((Gaussian1(a)-Gaussian8(Gaussian1(a)))**2)` has nested support:
4 + 32 + 32 pixels, plus 4 px tangent displacement = 72. A 40 px mask would
allow nodata fill to affect scores near a survey edge. Scales, weights, spacing
and budget are unchanged. This correction is committed before any experiment.

The registry is pinned to the initial review's commits. A concurrent update to
GEMSDOE25 main during discovery was detected by a Git blob hash mismatch; do not
mix its new README with the earlier snapshot. Refreshes require explicit opt-in.

Raw raster Spearman checks will be **exact over all footprint pixels**, stronger
than the preregistered uniform sample; only the additional kernel-field
sensitivity uses the fixed 200,000-pixel sample. Undefined constant-field
correlations are recorded as null, never invented as zero.
