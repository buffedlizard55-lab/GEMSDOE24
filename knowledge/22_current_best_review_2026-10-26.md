# Current-best continuation review — 2026-10-26

## Executive decision

**DOWNLOAD YES / SUBMIT NO. No new TIFF generated and no new experiment run in this continuation.**
The requested new, literal-gate-unique, submission-ready release remains unachieved.
The existing all-finite DPRF1 research TIFF was reopened, hashed, validated against
the cached template and screened through the shared selector. This is not a
retraining, independent scientific replay or new organizer result.

- Artifact: `gems24-dprf1-stitched-oof-tworegime-20261026-81849d67c8bf-zeros.tif`.
- SHA-256: `c1257c1d4b5ac9cc0a8e29b0120c614fcaa1f38474bc1f6de98c0a1afb0567f1`.
- Recorded **HOLDOUT-DTI 0.16379**, 95% CI **[0.15045, 0.17739]**,
  `gems-segment-pooled-v1`, **60,988 withheld positive pixels**.
- Fresh output: [`current_best_review.json`](../docs/data/current_best_review.json).
- Reproduce: `.venv/bin/python scripts/review_current_best.py`.

The nine-site comparison remains available on the executive page and in
`evidence/nine_site_executive_summary_20261026.json`. It is a frozen source audit,
not a current leaderboard. Its historical ranking and sibling holdouts cannot
establish which unscored artifact would win on organizer hidden labels. Earlier
cross-site superiority language in this JSON is retained as historical evidence;
the current review and visible page explicitly narrow it to a local point-best.

## Why H33-B2 may have improved the owner-reported leaderboard result

Inherited pixel forensics describe H33-B2 as a subset of the D2.8 prediction,
removing near-catalogue pixels. With pixel-exact known-fault masking, a nearby
but not exactly masked prediction can incur false-positive cost without finding
new faults. Pruning redundant dots can therefore improve distance-weighted
Tversky precision without sacrificing equivalent recovery. This is a plausible
metric/geometric explanation, **not proof of the hidden-label causal mechanism**.
It is not evidence that more pruning, more geothermal proxies or a new filename
will improve a leaderboard result. The owner-reported result is not
ORGANIZER-CONFIRMED; no artifact-linked portal receipt was obtained.

Neither that number nor either conflicting overall leader claim establishes an
attainable target from local holdout measurements. We did not copy or modify B2.

## Three prospective hypotheses — deferred, not experiments or score forecasts

No single-method paragraph was supplied. Previously stopped lanes remain stopped.
The following rank is qualitative expected benefit versus cost, not projected DTI.
Source inspection found no implementation of the exact proposed operators below;
this does not establish novelty outside this repository. All need preregistration,
canaries for every actual transform, whole-segment blocked validation, paired
comparison to the current-best and surface/dot registry checks **before placement
or any promotion**. None has been validated in this continuation.

| Rank | Exact layers / operator | Missing-fault rationale and named mimic | Difference / cost / viability |
|---|---|---|---|
| 1 | `dem_elev`, `dem_tpi`, `lidar_step`: extract a directed thalweg graph, then align abrupt channel-azimuth offsets across independent drainage catchments | A buried transverse fault may consistently offset multiple washes without a continuous exposed scarp; Lake Lahontan strandlines and fan avulsion can mimic it | Existing TRSG1 mentions knickpoint breaks but does not implement a directed multi-catchment graph. Moderate expected benefit, high implementation cost; coarse 100 m DEM may be inadequate. Existing cached layers only; no new source availability assumed |
| 2 | `tmi_rtp`, `tmi_up150`, `iso_grav_anom`: azimuthal local semivariogram change across a candidate front, requiring concordant changes in magnetic and gravity fabric | Buried basement displacement may change texture rather than produce a high-amplitude edge already mapped; intrusive contacts or survey mosaics mimic this | Unlike tilt/Hessian/ridge magnitude, test a two-sided texture-distribution discontinuity. Uncertain benefit, medium cost; requires checking real cached raw-band coverage and acquisition confounds before execution |
| 3 | `tmi_rtp`, `tmi_up150`, `dem_elev`: multi-frequency quadrature phase-congruency fronts with cross-modality orientation agreement, excluding amplitude as primary evidence | Low-amplitude buried steps may be missed by amplitude-thresholded detectors; dikes and aligned erosional benches mimic fronts | Cross-depth persistence alone was already tried in CRP1; the proposed new operator is local quadrature phase agreement, not another persistence rerun. Uncertain benefit, medium/high cost; no fresh external data required in principle |

These hypotheses are **not authorization to bypass the lattice veto**. The
retained spacing-5 control lies within 3 pixels of almost the whole footprint.
Under the literal protocol, that can reject even an unrelated detector. No
comparator was removed, no threshold relaxed and no new dot placement attempted.

## Irregularities and limitations

1. Existing first-screen `active_lane.json` identifies the frozen TNR1 packet,
   not the highest recorded local point estimate. Retained for historical lane
   identity; a separate current-best banner and JSON now resolve the local best
   from all declared-comparable run cards rather than rewriting its identity.
2. Generated prose incorrectly quoted the TNR1 holdout result. Corrected to the
   recorded **HOLDOUT-DTI 0.13219**, 95% CI **[0.11791, 0.14546]**,
   `gems-segment-pooled-v1`, **60,988 withheld positives**.
3. DPRF1 passes the competing-method subset but fails literal all-entry novelty.
   It must not be called fully unique or a verified cross-site winner.
4. The current selector compares DPRF1 to the current floor including itself;
   strict superiority therefore fails on equality. This is a conservative screen,
   not evidence of scientific regression. An eventual positive selector needs
   immutable pre-experiment benchmark identity and paired replay, not a weaker
   floor, self-exclusion shortcut or hand-entered promotion flag.
5. The zero-outside TIFF passes finite/range, single-band, CRS, shape and transform
   checks, but its outside-footprint/nodata convention differs from the cached
   NaN-outside sample. Fresh validator output explicitly records this distinction.
   Passing these local format checks is not organizer acceptance certification.
6. Independent positive replay and account-quota verifier adapters are absent.
   The selector is deliberately negative-only; no human-inspection workaround.
7. Raw feature caches are not installed in this clean checkout. Existing raw data
   restore/prepare procedures remain necessary for any newly assigned experiment;
   an earlier session's claim that training is ready is not a fresh data audit.
8. Initial provenance-test failures were caused by shallow Git history, not
   repaired by weakening tests. `git fetch --unshallow origin` restored history.

## Official sources and access scope

- Organizer GitHub reference HEAD was checked through GitHub API during this
  continuation: [`aebe92f7c8a990f0e3443451b7a825d9afd6336b`](https://github.com/drivendataorg/gems-prize-reference-solution/commit/aebe92f7c8a990f0e3443451b7a825d9afd6336b).
  This confirms repository identity, not independent validation of every inherited scientific claim.
- [Competition problem](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/),
  [leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/),
  [official rules](https://docs.nlr.gov/docs/fy26osti/96647.pdf): retained official
  review links; not freshly retrieved. Sandbox network only permits GitHub and
  package registries; project policy also disallows automatic DrivenData access.
- [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and),
  [OpenEI INGENIOUS](https://gdr.openei.org/submissions/1391): inherited official
  layer provenance links, not newly fetched source authentication.

## Three review passes and next work

1. Reviewed standing instructions, owner briefs, current benchmark receipts,
   selector and website. Revalidated DPRF1 without rerunning the stopped lane.
2. Added read-only current-best verification with unsafe-path, failed identity,
   invalid-format and positive-authorization rejection tests; corrected misleading
   generated prose. Full suite: **353 tests pass** after restoring Git history.
3. Rebuilt the site, checked formatting/lint and rechecked exact-file and site
   gates. No training, new raster, registry-policy change or submission slot.

Next: preserve the literal policy unless prospectively revised; design a genuinely
independent replay certificate and legitimate machine-verifiable quota integration
before implementing positive authorization. Harmonize sibling holdouts before
claiming a cross-site winner. Assign one new geological lane only after these
protocol contradictions are resolved. No projected leaderboard score is promised.
