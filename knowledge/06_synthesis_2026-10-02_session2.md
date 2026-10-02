# 06 · Synthesis — the metric, the owner's scores, the audit and the dotted H19-5 candidates (2026-10-02, second session on this branch)

Evidence classes: **OFFICIAL** = organizer/USGS text I read at the cited link on 2026-10-02 ·
**OWNER** = scores/files reported by the owner (not organizer receipts) · **COMPUTED** = reproducible in this
repo (script and JSON named) · **INFERENCE** = my reading with assumptions stated.
This document extends `05_findings_and_hypotheses_2026-10-02.md` (the earlier session's work on this branch,
merged here); it does not replace it. Where the two overlap, both agree.

## 1. Official facts read this session (full table with links: `docs/data/sources.json`, site "Sources")

| Fact | Source |
|---|---|
| Submission = one float32 layer, values in [0,1], same grid, "data outside the bounds is null or nan" | [problem page](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) |
| DTI = TPw / (TPw + α·FPw + β·FNw + ε), α = 0.2, β = 0.8, triangular kernel R = 300 m | same |
| Known-fault mask is pixel-exact; near-known pixels far from NEW truth are fully penalized; new truth **can** lie within 300 m of a known trace ("corrections or modifications"); same masking in the final round | [staff, thread 11516](https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516/4) |
| "New fault" = any fault pixel not already captured by USGS/INGENIOUS, including newly mapped geometry of an existing system | [thread 11536](https://community.drivendata.org/t/where-do-you-draw-the-line/11536/2) |
| Public and private scores each pool all pixels of the subset into ONE Tversky index; final re-evaluation is on the entire GeoDAWN area | [thread 11550](https://community.drivendata.org/t/leaderboard-aggregation-pooled-over-public-test-pixels-or-mean-of-per-chunk-scores/11550) |
| Hand-labelling is allowed if labels are saved and available on request | [thread 11543](https://community.drivendata.org/t/using-a-teammates-geological-interpretation-as-training-labels/11543) |
| Three submissions per week; one final submission; generative-AI use must be disclosed | [rules PDF §3.2/3.4](https://docs.nlr.gov/docs/fy26osti/96647.pdf) |
| Competition end "Dec. 3, 2026, 11:59 p.m. UTC" (page) vs "5:00 p.m. ET on the deadline date" (rules A.1) | [page](https://www.drivendata.org/competitions/306/competition-doe-gems/) · rules |
| Four acquisition blocks (N→S Winnemucca, Fallon, Hawthorne, Tonopah); boundaries only in Figure 1 | [ScienceBase](https://www.sciencebase.gov/catalog/item/657e1d85d34e23d3533209f7) |
| Leaderboard 2026-10-02: #1 DARD 0.3195 … #5 0.2919, #26 smrtdoog5 0.1922, #28 SDCF9 0.1894. The 0.3049 in the brief is stale | [leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) |
| USGS Qfaults vs expert/lidar labels can differ by up to 400 m (north-central Nevada) | [Hermant et al. 2025](https://pangea.stanford.edu/ERE/db/GeoConf/papers/SGW/2025/Hermant.pdf), cited on the organizers' About page |

GitHub state (COMPUTED via API): Pages is enabled (`status: built`) for `main`; the live site returned the
deployed overview page; the earlier "deployment not verified / GitHub auth blocked" statements were stale.

## 2. The portal message "Predicted values must be in range [0, 1]" — forensics (COMPUTED)

`scripts/analyze_group_rasters.py` → `evidence/format_forensics.json`, `evidence/group_raster_profiles.csv`.

* 167 unique rasters in the owner's 22 sibling repos; 148 are single-band float32 EPSG:32611 submission-grid rasters.
* **No** raster has a value outside [0,1] or ±Inf inside the footprint. Three early `5GEMSDOE/submission.tif` files have
  3,061 NaN **inside** the footprint and 1,540 finite pixels outside it. Nothing else is anomalous.
* The three blank-score files (h18-4, h20-1, h20-5) are format-identical to files that scored, so their blanks cannot be attributed
  to a format failure (they may simply not have been submitted).
* Both outside-footprint conventions were accepted: 12GEMSDOE's NaN-outside and zeros-outside variants both report 0.1294 (OWNER).
* **Conclusion:** the cause of the original portal message is **not established**. The strict writer
  (`submission.write_submission`: finite and in [0,1] inside, NaN or zero outside, template profile) cannot produce any of the
  observed anomalies. The guide tells the owner what to check if it recurs.

## 3. What the metric implies at the measured truth density

Identity: `TPw + FNw = |G|`, so `DTI = TPw / (0.2·(TPw + FPw) + 0.8·|G|)`; `FPw` is linear in emitted mass.

**Blind-lattice calibration (COMPUTED, `evidence/emission_calibration.json`).** 13GEMSDOE's spacing-5 lattice
(`13gems_20261001_r13-lattice-s5_v2_nan-outside.tif`, OWNER 0.0904; 206,895 px, 204,504 of them off-catalogue; mean kernel credit 0.372) earns the same expected
credit at any truth pixel regardless of how truth is arranged, so `S = mτ / (0.2(mτ + a) + 0.8τ)` gives
**τ = 0.00244** of footprint cells (≈12.6 k pixels ≈ 20.7 % of the 60,988-pixel catalogue). Rounding of 0.0904 moves τ <1 %;
on 24 synthetic truth layouts the estimator's error was +2.5 % (SD 7.6 %). It lies inside GEMSDOE10's independent 0.13–0.6 % bound.
**Caveat:** 0.0904 appears only in the 2026-10-02 brief (the older GEMSDOE21 snapshot shows it blank); treat as unconfirmed.

**Consequence (INFERENCE).** For H19-5 (121,131 px, 2.34 % of the footprint, OWNER 0.1922) the first-order model gives credit/truth ≈ 0.52,
`0.2·N` ≈ 70 % and the false-positive term ≈ 67 % of the DTI denominator. The best files emit ~10× the truth density; **efficiency of
emission is a first-order lever**, comparable to detector skill.

**Independent natural experiment (OWNER).** Same probability surface (`6452ae1d00`): solid H25 (161,366 off-catalogue px) 0.1280 →
dotted H28 (65,236 px) 0.1839, **+44 %**. H28's value is brief-only (older snapshot blank). The calibrated model with the geometric credit
retention 0.70 predicts 0.164; the retention implied by the reported scores is 0.80.

**Known-pixel masking is real (OWNER, consistent with staff).** 8GEMSDOE Hedge-v2 = GEMSDOE ens12's off-catalogue pixels **plus all 60,988
catalogue pixels**; both report 0.1563.

## 4. Why H19-4 (0.1894) and H19-5 (0.1922) scored best — and can it go higher?

**Supported.** Same family (Jaccard 0.777; ≈90 % topographic/scarp coefficients; OOF-expert blend with ridge thinning); no pixel on a catalogue cell;
≈22–23 % of emitted pixels (22.7 % H19-5, 22.5 % H19-4) within 300 m of the catalogue; ≈3.2× enrichment at exactly 100 m (consequence of masking the catalogue after a surface that peaks
on known scarps). Catalogue-hugging does **not** pay: the five files with ≥45 % of off-catalogue pixels within 300 m (6GEMSDOE, 11GEMSDOE, 14GEMSDOE,
17GEMSDOE, h16-continuation) all scored ≤ 0.0461 (`evidence/lb_geometry_analysis.json`; the earlier session found the same). Distance-to-catalogue alone does not
explain the 26 scores (a per-bin shared-hit-rate model gives Pearson 0.256: rejected), so detector skill matters.
**Not supported:** attributing the +0.0028 H19-4→H19-5 difference to any named physical line.

**Higher?** Already exceeded 0.1894. Beyond 0.1922 the only lever with direct evidence is emission efficiency (§5); a materially higher score like the
0.3195 leader's needs new information or a much better detector. The best files were never dotted: H28's dotting predates and used a weaker surface.

## 5. Dotted H19-5: results (COMPUTED; nothing here is a leaderboard score)

Two independent implementations agree.

**(a) Earlier session, frozen before its run** (`04_preregistered_dotting…`, `evidence/dotting_validation.json`, `thinning.dot_thin`): d* = 2.8 → 44,090 px;
dev sparse gain +30.7 %, confirmation +18.1 %, 48/48 cell wins, bootstrap p5 +21 %, full-density Δ −0.0005…+0.0019; all gates passed.

**(b) This session** (`04_preregistered_emission…`; the K(f) grid was frozen before its run; the operator head-to-head and selection rule — Addendum 2 — were frozen after the K grid had been seen but before any `D(d)` score): four sparse-truth quadrants × 30 selection draws (0–29) and 30 disjoint confirmation draws (30–59),
evaluator bit-exact against `gems.metric.dti_score_fast` (max abs diff 0.0).

| H19-5 variant (equal-N pairs) | px | dense | sparse | sparse gain | legacy gate sel/conf | model score |
|---|---|---|---|---|---|---|
| solid (as emitted) | 121,131 | 0.1694 | 0.0710 | — | — | 0.1922 |
| **D1.5 = primary** | 60,069 | 0.1764 | 0.0962 | **+35.6 %** | pass / pass | 0.2548 |
| K (greedy cover) same N | 60,081 | 0.1684 | 0.0915 | +28.9 % | fail / fail | 0.2432 |
| **D2.4 ≡ d\*=2.8 = alternate** | 44,090 | 0.1665 | 0.1008 | **+41.9 %** | fail / fail | 0.2643 |
| K same N | 44,092 | 0.1524 | 0.0919 | +29.4 % | fail / fail | 0.2418 |
| D3.2 | 34,817 | 0.1517 | 0.0986 | +38.9 % | fail / fail | 0.2574 |
| K same N | 34,765 | 0.1333 | 0.0854 | +20.3 % | fail / fail | 0.2231 |

* **My greedy kernel-cover operator is inferior to `dot_thin` at equal pixel count in both regimes.** In the first frozen run (30 draws) random thinning of H19-5 to 45–60 % of its pixels gained only
  +0.009 sparse DTI (greedy cover +0.023 at 45 %) and *lost* at 25 % (−0.0015).
* Frozen selection: primary **D1.5** (only candidate family member passing the legacy gate on selection and confirmation with the highest model score);
  alternate **D2.4/d\*=2.8** (highest sparse DTI; fails the dense-improvement criterion by 0.0029). H19-4 replicates the DTI values to within ±0.002 (model scores within 0.004).
* The alternate raster is **byte-identical** (SHA-256 `91eae1ca…`) to the earlier session's separately frozen candidate: exact reproduction in a fresh environment.
* **Model score** = first-order extrapolation from the harness's sparse credit retention (D1.5: 0.873, D2.4: 0.779): parameter sensitivity (φ 0–0.10, τ ±15 %) 0.247–0.263 and
  0.253–0.277. **Out-of-sample check on h25→h28** (OWNER pair): the same method under-predicts (0.138 vs 0.1839) because the harness retention (0.595) is lower than the
  retention implied by the reported scores (0.80). The harness' sparse DTI ratio h28/h25 is 1.079 (right sign, small), the dense ratio 0.768 (**wrong sign**) while the reported score rose 44 %.
  Hence: sign supported, magnitude uncertain — I state the plausible range as 0.22–0.28, centred ≈0.25, and **no leaderboard result**.
* Phase 2 re-scores on a denser label set (expert-verified additions). That moves the optimum toward less thinning; the primary (50 % of pixels, dense gain positive) is therefore the primary.

## 6. Exact-file classifier two-sample audit (labels first; COMPUTED, `evidence/accessibility_audit_v2.json`)

Features: Census road/trail distance (official buffered run: 32 whole counties, 1,141,630 seed px, raster SHA matches receipt), BLM closed-claim distance, four acquisition blocks
(derived from the official figure and audited against published line-km, **not official coordinates**; my independent digitization of the figure's dashed seams from its latitude ticks —
40.00°, 38.99°, 38.08° N — agrees with the derived raster's 40.03–40.04°, 38.996–39.003°, 38.075–38.096° within ~5 km at the northern seam and ~1–2 km at the two southern seams). 199 grouped refitted nulls, 99 shifts.

| Raster | AUC | null p95 | Holm p (6-test family) | strongest single family | flag |
|---|---|---|---|---|---|
| training labels (first) | 0.496 | 0.520 | 0.625 | road 0.522 | no |
| H19-4 | 0.556 | 0.519 | 0.030 | claims 0.580 | yes |
| H19-5 | 0.563 | 0.519 | 0.030 | claims 0.585 | yes |
| primary (D1.5) | 0.555 | 0.524 | 0.030 | claims 0.574 | yes |
| alternate (D2.4) | 0.558 | 0.517 | 0.030 | claims 0.582 | yes |
| residualized detector (H24-2A arc+resid, 126,600 px) | 0.525 | 0.522 | 0.090 | claims 0.553 | no |

* The catalogue itself shows **no** association with road/claim/block features (the premise "the catalogue is shaped by accessibility" is not supported by this test); the **detectors' outputs do**,
  mostly through claim proximity (mining districts sit in ranges, so this is not independent of geology). Spatial-shift diagnostics are not significant (p 0.25–0.31): the association is not robust to a
  nonstationary shift. Association is not causation.
* Both candidates are slightly **less** associated than their reference (AUC −0.008, −0.005). The strict owner gate fails for the whole H19 family including the reference; the declared relative criterion
  (not worse than the reference +0.01) passes ⇒ `slot_recommendation = owner_decision_required` for both. Residualization applies to retrained detectors (H24-2A did it and did not beat H19); a fixed H19 mask has no model to refit.

### 6b. "Then residualize": refit of all four arms on the corrected sources (COMPUTED, `evidence/h24_2_experiment.json`)

The earlier H24-2A run had only the provisional Area-1 indicator and clipped roads. Re-run with the full families (buffered Census roads, closed claims, four derived blocks; frozen protocol, one truth draw, four quadrants, 1.5 km collar, training-only residualization):

| arm | dense | sparse |
|---|---|---|
| physics, raw | 0.1517 | 0.0584 |
| physics + arc, raw | 0.1531 | 0.0596 |
| physics, residualized | 0.1354 | 0.0555 |
| physics + arc, residualized | 0.1429 | 0.0582 |
| H19-4 / H19-5 as emitted (diagnostic) | 0.1704 / 0.1694 | 0.0685 / 0.0681 |

* With the corrected sources **"arc + residualized beats the baseline" no longer holds** (vs raw physics: Δdense −0.0088, Δsparse −0.0002; it still beats its own residualized baseline by +0.0075 / +0.0027). The earlier positive was an artefact of the provisional inputs.
* Residualizing costs 0.016 dense DTI. Likely reason (INFERENCE): the four blocks are **latitude bands**, so removing block membership removes regional geology (Walker Lane vs Basin and Range, north vs south), and the labels themselves show no accessibility association (AUC 0.496) — there is little catalogue confound for it to remove.
* The residualized detector's emitted raster (`out/h24-2a-residualized-experimental.tif`, 126,600 px) audits at AUC 0.525 (flag: no — AUC below .55, margin +0.002, Holm p 0.09; H19-5: 0.563). Residualization therefore removes most of the detector's association with claim proximity (single-family claim AUC 0.553 vs 0.58–0.59 for H19), but it costs 0.016 dense / 0.003 sparse DTI against the raw physics arm and the raster stays below H19-5 on the holdout (0.143 vs 0.169 dense): **the strict audit and the holdout pull in opposite directions**.
* Not done: reconstruction of the H19 OOF reference (the original OOF surfaces are unavailable), and the preregistered H24-3A/H24-4A tests; both remain open.

## 7. Hypotheses (3–5, ranked) — status

1. **H25-1 / H24-E1 calibrated dotted H19** — not geological; validated above.
2. **H25-2 strike-compatibility prior** (emitted-ridge orientation vs training-region catalogue strike field) — top *geological* item; testable on existing quadrants; **not yet run**.
3. **H25-3 scarp cross-profile template** on 1 m 3DEP (706/716 tiles already processed on CI) — highest ceiling, ≈2 days.
4. **H25-6 map-scale correction corridor (new).** Layers: INGENIOUS `MAPSCALE` per trace (this repo's `gdr_qfaults_traces.csv`: 82 % of length at 1:250,000, 18 % at 1:100,000; the 0.5 mm-at-map-scale convention gives 125 m and 50 m — a nominal figure, not a measured error) with lidar scarps.
   Signature: uncertainty-weighted relocation of known traces to the nearest scarp within the corridor. Rationale: staff say new truth may lie within 300 m of known traces and Qfaults can be ≈400 m off. Difference: uses catalogue geometry as a positional-uncertainty prior, **not a halo**
   (halos fail, §4). Needs a per-pixel map-scale raster from the free GDR 1391 shapefile (CI). **Not yet tested; unvalidated.**
5. **H25-4 concealed basin-margin step** (depth-to-base, gravity gradient, magnetic edge joint step) — small, uncertain.
Free official source check: GDR 1391 (`gdr.openei.org/submissions/1391`) is obtainable via GitHub Actions (the sandbox cannot reach it); USGS 3DEP via the public S3 bucket (CI).

## 8. Limits, access and recommended order

* I cannot reach the DrivenData portal/private leaderboard/hidden labels, upload, or verify scores. Brief-only scores (H28 0.1839, lattice 0.0904) are unconfirmed.
* The as-emitted harness is leaky for H19 (it masked all catalogue pixels, including held-out ones); paired comparisons cancel the shared leak, absolute DTI is inflated.
* Needs from the owner: a decision on the exception (§6); confirmation of the two brief-only scores; the S3-hosted GeoDAWN profile archives for the official flight-number → block mapping; a geologist for hand-labelled lidar scarps.
* **Order (suggestion).** (1) Upload the primary once; the alternate in the same week if the exception is accepted — they differ only in emission, so the two scores measure the emission curve at fixed detections. Record both with `scripts/record_live_score.py`.
  (2) Re-fit τ from the new scores (the model has two unknowns now observed). (3) Test H25-2, then H25-3. (4) Choose the final emission with Phase 2 in mind.
