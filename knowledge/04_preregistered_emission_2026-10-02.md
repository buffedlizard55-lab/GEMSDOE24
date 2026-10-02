# Preregistered hypothesis H24-E1 — calibrated kernel-cover emission

Written **before any holdout score of a thinned raster was computed**. The
calibration inputs below are measurements on the owner's own submissions and
leaderboard reports (not outcomes of this experiment). Everything under
"Frozen protocol" is fixed here and may not be tuned on the outcome.

## 1. Why this is ranked first

The official metric (DrivenData problem page, "Performance metric") is
`DTI = TPw / (TPw + 0.2·FPw + 0.8·FNw)`, with `TPw + FNw = |G|` for binary or
soft predictions because each truth pixel contributes `credit` to TP and
`1-credit` to FN. Hence

```
DTI = TPw / (0.2·(TPw + FPw) + 0.8·|G|)
```

where `FPw = Σ_x p(x)·(1 − max_g k(d(x,g)))` is **linear in the emitted mass**
and `|G|` is the (unknown, small) number of new-fault pixels. The pooled
public score is one Tversky index over the public subset (DrivenData staff,
2026-10-01: "pooled over all pixels in the public subset … single Tversky
index"). Known-fault pixels are pixel-exactly masked.

Whether this is **FP-mass dominated** depends on `|G|`. We can measure it from
a *blind* prediction. 13GEMSDOE submitted a perfectly regular spacing-5 lattice
(`13gems_20261001_r13-lattice-s5_v2_nan-outside.tif`, owner-reported score
**0.0904**). A uniform lattice earns the same expected credit at every truth
pixel regardless of how truth is arranged, so its score pins down the truth
density `τ = |G| / |footprint|` of the public subset.

Measured inputs (from the raster itself, `evidence/emission_calibration.json`):
`N_off-known/|F| = 0.03958`, mean kernel credit over the footprint `m = 0.3718`.
Solving `S = mτ / (0.2(mτ + a) + 0.8τ)` for τ gives **τ ≈ 0.00244**
(≈12.6 k footprint-equivalent truth pixels, ≈20.7 % of the 60,988-pixel
catalogue). Rounding of the reported score moves τ by <1 %.

Natural experiment on the same surface content id (`6452ae1d00`):
`gems10-h25-ctx-ridge` (161,366 off-known px, LB 0.1280) versus
`gems10-h28-dotted-ridge` (65,236 off-known px, LB **0.1839**). Emission density
fell 60 % and the owner-reported score rose 44 %. The calibrated model with
geometric credit retention 0.70 predicts 0.164; the retention implied by the
observation is 0.785. This is one pair, so it is supporting evidence, not proof.

At τ ≈ 0.00244 the best owner files (≈2.3 % of footprint) emit ~10× the truth
density; `0.2·N` is ≈70 % of the DTI denominator. A cheaper emission that keeps
most of the kernel credit is therefore worth more than a marginal detector
improvement, and **none of H16-1/H19-4/H19-5 was ever thinned this way** (the
only dotted file, h28, used a weaker surface).

## 2. Hypothesis, layers, signature, difference from the repository

* **Layers:** none new. Operates on an existing binary ridge raster (H19-5, LB
  0.1922; H19-4, LB 0.1894) and its off-catalogue pixels only.
* **Physical signature used:** fault scarps and gradient ridges are *continuous
  line features*, so a pixel's evidence is spatially redundant with its
  neighbours. The metric's 300 m triangular kernel (3 px) means a pixel at
  distance `d` from a truth pixel already earns `1 − d/3`; adjacent ridge
  pixels share almost all of their credit.
* **Why it can catch faults the catalogue misses:** it does not change what is
  detected; it re-allocates the same evidence to the cheapest covering subset so
  the false-positive mass no longer swamps true corrections/continuations.
* **Difference from reviewed code:** earlier sessions raised the budget
  (22GEMSDOE `h23-a/b`, 6 %/10 %, unscored), or applied NMS at 2.45–2.5 %
  (H16-1/H19). h28 dotting predates and was never combined with the H19
  surface. Here thinning is a **greedy facility-location cover with the exact
  metric kernel**, compared to a random-thinning control with identical N.

## 3. Frozen protocol

1. Baselines (paired, same harness): `inputs/*h19-5*-nan.tif` and
   `inputs/*h19-4*-nan.tif` as emitted. Candidate family `K(f)` = greedy
   facility-location cover of the raster's own off-catalogue pixels with the
   kernel `k(d) = max(1 − d/3, 0)`, stopping at `f` of the original pixel
   count, `f ∈ {0.60, 0.45, 0.35, 0.25}`. Deterministic: ties by flat index.
   Control `R(f)`: uniform random subset, same count, seed 20261002.
2. Harness: `gems.holdout.Holdout` (four contiguous quadrants, 20 % component
   sparse truth, exact masked DTI). **Truth draws:** sparse seed offsets 0–29.
   Dense DTI has no draw.
3. Primary decision statistic: paired difference of mean **sparse** DTI
   (candidate − H19-5 as emitted), averaged over 30 draws, with a paired
   bootstrap over draws and quadrant folds. Rationale: sparse truth has density
   ≈0.24 % of the footprint, matching the lattice-calibrated τ; dense truth is
   ≈1.18 %, a different regime.
4. Selection of `f`: the grid point with the highest mean sparse DTI, provided
   it is not at the grid edge (otherwise report the edge and do not extrapolate).
5. Legacy gate (reported unchanged): `gems.holdout.gate(candidate, baseline)`
   — dense and sparse means each improve > 0.001, ≥3/4 sparse fold wins, no
   fold loses > 0.01. **Both outcomes are reported.** Because the legacy gate
   requires dense improvement in a regime ~5× denser than the hidden set, a
   candidate that passes the sparse criterion but fails only the dense
   criterion is labelled **"owner decision required"**, never auto-promoted.
6. No weekly slot is spent or recommended unless (a) the legacy gate passes, or
   the owner explicitly accepts the regime argument above, **and** (b) the exact
   emitted file passes `gems.submission.check_variants` and the nuisance audit
   on the sources that exist. This is recorded in `registry/submissions.json`.
7. Pre-declared limitations: the as-emitted harness is leaky for H19 (its mask
   excluded *all* catalogue pixels including held-out ones), so absolute DTI is
   inflated and not comparable with the original OOF numbers (dense 0.21413,
   sparse 0.08667); the paired comparison cancels the shared leak but may
   *understate* dotting because the leak places truth exactly 1 px from ridge
   pixels. The calibration assumes the lattice is a blind sampler, that the
   owner-reported 0.0904 belongs to this exact file, FP≈N, and a stable truth
   density across phases. Phase 2 labels are expected to be denser (`|G|`
   grows after expert review), which favours less aggressive thinning; the
   final file must be chosen with that asymmetry in mind.

## 4. Predictions registered in advance (to be scored, not tuned)

Under the calibrated model and retention 0.70–0.85, a cover thinned to
35–45 % of H19-5's pixels should raise the public score to roughly 0.23–0.28.
This is a model-based extrapolation with real uncertainty; a bad outcome (no
sparse gain, or random thinning matching the cover) falsifies the credit-retention
argument and is recorded as such.

## 5. Addendum (written before any thinned-raster holdout score) — provenance

After the sections above were committed (`ce3e89b`), reading GEMSDOE10's
`README.md`/`HYPOTHESES.md` (Session 5, 2026-09-28) showed that **the group had
already established this mechanism**: a leaderboard probe bounded hidden truth
density at ~0.13–0.6 % of the scored area, a density-matched "protocol v5"
simulation was adopted, and the dotted emission `ridge20_d3`
(`placement.dot_nms`, probability-ordered radius-3 suppression along a ridge)
was released as H28 (owner-reported LB 0.1839 vs 0.1280 for the un-dotted H25 on
the same probability surface). The later H16-1/H19 line returned to un-thinned
NMS at 2.45–2.5 % and to the legacy dense-weighted gate, so **the best surface
(H19-5) has never been thinned.** H24-E1 is therefore *not* a new discovery; it
is the application of an existing, LB-supported technique to the best available
content, plus (i) an independent lattice calibration of τ that lands inside
GEMSDOE10's 0.13–0.6 % bound, (ii) an exact-kernel greedy cover with a random-
thinning control, and (iii) a paired test under the current harness.

GEMSDOE10's v5 rule (density-matched primary, full-density non-inferiority with
loss ≤ 0.01) is recorded here as the precedent for how a dense-regime regression
is treated. It is **not** used to relax any criterion above: section 3, item 5
already says a sparse-pass/dense-fail result is reported as "owner decision
required". No thinned-raster score had been computed when this addendum was
written.

## 6. Addendum 2 (frozen before the operator head-to-head is run) — merge with H25-1

While integrating, I found that the earlier work on this session branch had already
preregistered and run an independent version of this idea: **H25-1 "Dotted H19"**
(`knowledge/04_preregistered_dotting_2026-10-02.md`, `src/gems/thinning.py::dot_thin`,
`evidence/dotting_validation.json`; frozen d* = 2.8 -> 44,090 px, all of its gates
passed, no slot spent). Two operators and two truth constructions now agree on the sign
and on the optimum region (about 35-50 % of H19-5's pixels). To choose *one* deliverable
without tuning on the outcome, the following is frozen here, before any run:

* **Operators compared at equal pixel count:** `D(d)` = `thinning.dot_thin` with
  d in {1.5, 2.4, 3.2} (60,069 / 44,090 / 34,817 px on H19-5) and `K(f)` with
  f = N_D / N_base (0.496 / 0.364 / 0.287) plus the grid f in {0.45, 0.50, 0.55, 0.60}
  from section 3. Bases: H19-5 (primary), H19-4 (replicate).
* **Truth draws:** selection = sparse seed offsets 0-29, confirmation = offsets 30-59
  (disjoint truth subsets of the same catalogue; not independent geology).
* **Selection rule for the primary download:** among candidates that pass the legacy
  gate (`holdout.gate`: dense and sparse means each improve by > 0.001, >=3/4 sparse
  fold wins, no fold loses > 0.01) on the **selection** draws, take the one with the
  highest model-extrapolated public score (phi = 0.05, harness sparse retention,
  `emission.extrapolate_variant`); ties go to the larger pixel count. It must pass the
  same gate on the **confirmation** draws, otherwise the next one is used.
* **Alternate download:** the sparse-optimal candidate (highest mean sparse DTI on the
  selection draws), labelled "owner decision required" if it fails the legacy gate.
* Neither file is a reference: both are subsets of H19-5 with new content ids, and no
  weekly slot is spent or recommended unless the exact file also passes the nuisance
  audit on the available sources.
