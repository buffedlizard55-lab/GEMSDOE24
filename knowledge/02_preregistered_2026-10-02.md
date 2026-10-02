# Preregistered next experiments — 2026-10-02

Written **before new detector implementation or fold scoring**. This extends the
previous session's pending H24-2/3/4 queue rather than claiming those ideas were
never mentioned. Expected gains below are **ordinal scientific judgments, not
predicted leaderboard scores**. The competition predicts faults, not vents.

## Review that informed this register

Read local `src/gems/`, all previous audit/gate reports, 19GEMSDOE's
`src/gems/hypotheses.py` and `scripts/evaluate_h19_and_build_submissions.py`,
16GEMSDOE's hypothesis register, and 13GEMSDOE's R12/R13 registers. Archive the
commit ids in `evidence/group_review.json`. Novelty is relative to the reviewed
code, not a claim about every competitor or unseen session.

Critical corrections: the inherited audit uses geological sites and label-derived
fault distances; its 'four-block' raster is constant; MRDS is not mining claims;
its later gate ranks **binary submissions**, including arbitrary zero ties, rather
than retraining held-out models. Historical scores are not proof of a mechanism.
Use fresh paired retraining, 1.5 km collars, frozen parameters, and nuisance-only
features that do not contain label geometry. Do not infer causation from C2ST.

## Ranked candidates (expected DTI benefit / implementation cost)

| Rank | ID and specific layers | Physical transform/signature | Why it might find omitted faults | Difference from reviewed implementations | Expected gain; cost; feasibility |
|---|---|---|---|---|---|
| 1 | **H24-2A radial-gradient arc coherence**: competition RTP (band 2), TMI (band 14), detrended elevation (band 12); gravity (band 13) as corroboration | normalized radial component of the field gradient integrated over annuli of radius 0.6/1.2/2.4 km; retain an edge only when radial coherence supports the same curvature in a second physical field; no catalogue-defined centers | a curved structural boundary could be fragmented or suppressed by straight-line/ridge continuity filters; a corroborated arcuate segment is a candidate, not automatically a ring fault (intrusions and erosional basins are competing explanations) | implements pending H24-2 with **radial direction**, not scalar ring averaging or a straight worm; H19-3 uses openness/LRM and H16 worms use linear edge strength. No radial-gradient template in reviewed local code | medium **conditional** on genuine arcuate structures; moderate CPU cost; **viable** with the hash-verified local 19-band stack; no external data |
| 2 | **H24-3A common-resolution contact persistence**: RTP, TMI and isostatic gravity; official GeoDAWN Area1/Area2 plus acquisition metadata | upward-continuation transfer exp(-|k|h) at fixed heights, then contact-location persistence rather than amplitude summation; do not downward-continue noise | broad contacts under basin fill can survive continuation when shallow anthropogenic edges and flight artifacts do not | pending H24-3 normalizes ranks; this tests **contact persistence at a common observing scale**, unlike Gaussian worms/TDR contours or emission-only stratum ranks | small–medium; low–moderate cost; viable with local layers; precise flight-height corrections require official line data and are not assumed |
| 3 | **H24-4A directional residual variogram**: RTP and isostatic-gravity high-pass residuals, dilation as optional corroboration | differences at 0.3/0.6/1.2 km in 8 directions; anisotropy of directional semivariance and agreement across fields | buried damage zones may have texture anisotropy without a sharp surface scarp | pending H24-4; variogram **range/phase** is not the structure-tensor/coherence already in the lidar stack and not earthquake density | low–medium; moderate cost; viable with local layers; not yet tested |
| 4 | **H24-6 repeated drainage-offset concordance**: raw 10 m USGS 3DEP DEM and derived flow networks (optionally 1 m validation) | estimate signed lateral displacement of multiple drainage crossings along one candidate line; demand a common displacement sign, reject a single channel-bank step | repeated channel displacement can reveal short strike-slip splays missed by a quaternary scarp catalogue, whereas a road or terrace edge does not consistently offset independent channels | prior anti-piedmont, flow maps and hinge curvature score local relief; this scores **kinematic consistency across multiple channel crossings** | uncertain medium upside; high cost; source is free official USGS 3DEP, but **deferred** until raw DEM coverage and byte receipt verified; a listing/old sibling receipt alone does not make it ready |

Official layer descriptions and licence: [competition problem](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/),
[USGS GeoDAWN / CC0](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and),
[USGS 3DEP downloads](https://www.usgs.gov/3d-elevation-program/data-tools).
Example official 10 m source to probe before H24-6:
<https://prd-tnm.s3.amazonaws.com/StagedProducts/Elevation/13/TIFF/current/n39w119/USGS_13_n39w119.tif>.

## Frozen validation and promotion rule

1. Top candidate H24-2A is tested once, without a public submission. Hyperparameters
   above are fixed here. No search on outer validation outcomes. A negative result
   is kept, not relabelled as a new successful experiment.
2. Refit physics-only detector vs **the same detector plus arc features**, then
   refit both after regressing each feature on road/trail distance, closed-claim
   distance, and acquisition categories **on training-region pixels only**.
   Nuisance regression is a robustness intervention, not a causal correction.
3. Four geographically contiguous quadrants, 1.5 km train/test exclusion collar.
   Exclude any fault component touching validation/collar from supervised
   training anywhere. Negatives are unlabelled, not proven fault absence.
   Use one fixed ridge budget of 2.45%, no zero-score padding.
4. Report exact DTI on all withheld catalogue components (dense), plus a fixed
   20% component subset (sparse; remaining catalogue pixels are pixel-exactly
   masked). The latter is only a **catalogue-gap simulation**, not new-fault truth.
5. Promote only if dense **and** sparse means beat the in-run detector baseline
   **and** both historical H19-4/H19-5 raster diagnostics, at least 3/4 sparse
   folds win, no fold loses >0.01, and dense/sparse deltas exceed 0.001. Historical
   rasters cannot be certified OOF here; this is an additional conservative veto,
   not a clean estimate of their generalization. If baseline reconstruction is
   unavailable, do not claim to beat H19's original 0.21413/0.08667 holdout.
6. A primary audit uses only the required non-geological feature families.
   199 refitted grouped permutations, 99 minimum-distance spatial shifts as a
   sensitivity check; Holm correction across labels and the two individual
   historical predictions. Association flag requires adjusted p<=0.05, AUC>=0.55,
   and margin over the grouped-null 95th percentile >=0.02. Spatial exchangeability
   is an assumption; shifts are a diagnostic on this irregular nonstationary map.
7. Re-audit the exact final raster (not a union of unrelated submissions).
   Missing true four-block membership means **incomplete audit**, not a pass.
   Do not spend a slot, or advertise a new winner, without all applicable gates.

The group-best download remains a clearly labelled H19-5 reference until an
experiment passes; renaming the reference is not a new scientific discovery.

## Dated protocol/status addendum — 2026-10-02

This addendum preserves, rather than overwrites, the original pre-registration.
The initial available-family audit v2 used Area1 as a proxy for missing four-block
membership and a toroidal spatial shift; review found both invalid for the
requested full audit. The corrected v3 audit therefore uses only the
non-wrapping, refitted spatial-shift sensitivity analysis, labels first, then
each individual reference, and reports Holm-adjusted diagnostics. It requires
199 valid shifts, uses no Area1/Area2 or geological proxy, and remains explicitly
provisional because true four-block membership is unavailable. Its shift tail is
not an exact spatial randomization p-value. See the complete v3 receipts for
results and deviations; no result is retroactively represented as confirmatory.

H24-2A's recorded experiment is now historical-only for promotion because it
used Area1 and clipped-road inputs. The remaining-hypothesis register
`knowledge/04_remaining_hypotheses_2026-10-02.md` ranks H24-3A as the next
implementable candidate and documents a pre-implementation 20 km collar
amendment. H24-3A was tested once; it failed the preregistered paired sparse-fold
and historical-H19 gates. No weekly slot was consumed.
