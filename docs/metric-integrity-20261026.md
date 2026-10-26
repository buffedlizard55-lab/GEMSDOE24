# B2 metric explanation — corrected integrity review, 2026-10-26

**DOWNLOAD RESEARCH: YES / SUBMIT: NO. No new TIFF, experiment or slot in this continuation.**

The [executive guide](executive-summary.html) contains the nine-site comparison and the existing local point-best research download. There is **no validated organizer-score estimate** for that file. The requested new, fully unique, submit-ready release remains unachieved. Missing lane assignment, literal registry uniqueness failure, absent independent scientific replay and unknown account quota remain binding; none is a request for a human inspector.

## What was checked now

- Reopened the existing DPRF1 zero-outside TIFF through `scripts/review_current_best.py`, which uses the shared selector and submission validator. Exact SHA-256: `c1257c1d4b5ac9cc0a8e29b0120c614fcaa1f38474bc1f6de98c0a1afb0567f1`.
- Single band, finite values in the template footprint, all-array values in [0,1], and matching CRS/shape/transform pass. The cached sample uses NaN outside; the zero variant does not match that convention. Local strict-range validity is **not organizer acceptance**.
- Recorded **HOLDOUT-DTI 0.16379**, 95% CI **[0.15045, 0.17739]**, `gems-segment-pooled-v1`, **60,988 withheld positive pixels**. These measurements were **not scientifically replayed** here. See [exact-file review](data/current_best_review.json) and [run card](../evidence/dprf1_run_card_20261026.json).
- Queried the official [organizer reference repository](https://github.com/drivendataorg/gems-prize-reference-solution/tree/aebe92f7c8a990f0e3443451b7a825d9afd6336b); its HEAD was still `aebe92f7c8a990f0e3443451b7a825d9afd6336b`. This is source identity, not a fresh review of the competition portal or an organizer receipt.
- Preserved VENT source and receipts. Its fabricated fallback C2ST/novelty values invalidate those gate claims. No independent VENT holdout replay was performed, so its recorded performance is not trusted here either. Its prior narrative is now explicitly quarantined and its README PASS claim withdrawn.

## Correct metric, and what pruning does

This algebra describes the existing shared evaluator in [`src/gems/metric.py`](../src/gems/metric.py), not a newly measured leaderboard result. Let:

- `G` be the count of withheld positive pixels in the evaluation domain.
- `T` be recovered true-positive credit: for each truth pixel, the maximum prediction-weighted triangular kernel credit from nearby predictions, summed over truth pixels.
- `F` be false-positive mass: each predicted value multiplied by `1 - K(distance to nearest hidden-truth pixel)`, summed over the evaluation domain.
- `K(d) = max(1 - d / 300 m, 0)`; the shared grid has 100 m pixels.
- Known visible-fault pixels are neutralized **pixel-exactly**, not with a 200 m mask.

With false-positive penalty `alpha = 0.2` and false-negative penalty `beta = 0.8`, ignoring the implementation's small denominator epsilon:

```text
DTI = T / (T + 0.2 F + 0.8 (G - T))
    = T / (0.2 T + 0.2 F + 0.8 G).
```

The numerator is **T, not 0.2 T**. False-positive mass is **not** `sum(K * prediction on background)`. In particular, the kernel distance for `F` is distance to hidden truth, **not distance to the public catalogue**. A point 100 m from a visible catalogue fault can still incur full false-positive mass when it is far from every hidden truth pixel.

If deleting a dot loses `t` recovered true credit and removes `f` false-positive mass, then, with `G` fixed, deletion improves DTI precisely when:

```text
t * (0.2 F + 0.8 G) < 0.2 T * f.
```

This explains how pruning redundant predictions can help, without claiming all near-catalogue predictions are wrong. A dot can contribute credit to several truth pixels, so `t` cannot in general be treated as a single Bernoulli hit. Compute the actual before/after components on held-out truth. The regression tests exercise beneficial, harmful and score-neutral deletions against the shared exact evaluator, not just an algebraic illustration.

## What can be said about GEMSDOE32 B2

Inherited pixel forensics describe B2 as a subset of the D2.8 dot set, deleting points at public-catalogue distance at most 200 m; they do not describe newly detected faults. See [inherited analysis](../knowledge/14_h33_analysis_2026-10-25.md) and [priority receipt](../evidence/priority_review_20261025.json). Those frozen forensics were not recomputed against refreshed peer rasters in this continuation.

The owner's `0.2778` claim is **UNVERIFIED-OWNER-REPORT**, not ORGANIZER-CONFIRMED. A reduction in redundant false-positive mass is a **plausible, unproven explanation**, not an identified hidden-label causal mechanism. There is no evidence here that the removed pixels have the lowest hidden-hit probability, that their difference is within bootstrap noise, or that field mappers rarely miss faults at a particular distance. Those statements in the quarantined narrative should not be reused.

Could an independent method beat B2? Possibly, but no verified numerical leaderboard forecast is supported. Holdout measures recovery of hidden portions of the public catalogue, not the organizer's unseen fault population. A geothermal vent or spring association is not by itself proof of a fault, useful permeability, heat or a prize-winning score. Existing hypothesis rankings remain prospective only; no new method paragraph was assigned in this prompt.

## Source and access limits

Official links retained for review:

- [Competition problem and metric](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [Submission portal](https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/)
- [Prize document](https://docs.nlr.gov/docs/fy26osti/96647.pdf)
- [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
- [OpenEI INGENIOUS data](https://gdr.openei.org/submissions/1391)

Only the GitHub reference identity was freshly checked remotely here. The other hosts are outside this sandbox's outbound allowlist; current contents, competition status, account quota, and both conflicting overall leaderboard claims in the prompt were not verified. No inaccessible source is described as freshly researched or obtainable. Existing prompt copies remain in the README and linked owner briefs. No raw data, prior submission pixels, comparator exemptions or promotion thresholds were changed.
