# H24-XFRONT Findings & Updated Executive Summary (2026-10-26) — cross-modal oriented-step corroboration is negative; DPRF1 remains the one obvious candidate

- **Lane:** `H24-XFRONT` — label-free *cross-modal oriented-step corroboration* (six independent layers)
- **Preregistration:** [`25_preregistered_XFRONT_2026-10-26.md`](25_preregistered_XFRONT_2026-10-26.md) @ `3ebb375`, plus
  amendments [`26_XFRONT_prereg_amendment_2026-10-26.md`](26_XFRONT_prereg_amendment_2026-10-26.md) (≥2-layer
  corroboration floor, filed after the smoke test showed coherence is undefined for a single layer) and
  [`27_XFRONT_prereg_amendment2_2026-10-26.md`](27_XFRONT_prereg_amendment2_2026-10-26.md) (pre-specified
  mechanism-ablation arm B + arm-selection rule, filed before the run)
- **New unique TIF generated this session:**
  `docs/downloads/gems24-xfront-c-corrob-45000-20261026T162655Z-921f4f037290-zeros.tif`
  SHA-256 `04d2359a58ab85d1e66076d0543e1fbb1cd89a22312d4474f8dd8c30bb523edf` · 39,456 dots (budget cap 45,000) ·
  828,786 bytes · strict whole-array `[0,1]` PASS · CRS/shape/geotransform PASS
- **Verdict: NEGATIVE — DOWNLOAD: YES · SUBMIT: NO.** One experiment of the 3-experiment budget used.
  Zero slots spent. Zero human-inspector fallback.
- **Run card (Rule 5):** [`evidence/xfront_run_card_20261026.json`](../evidence/xfront_run_card_20261026.json)
  · selector [`evidence/xfront_selector_20261026.json`](../evidence/xfront_selector_20261026.json)

---

## 0. The obvious answer first (what to submit, per site)

**The highest-scoring recorded local artifact across all nine focus sites remains DPRF1** (HOLDOUT-DTI 0.16379),
generated 2026-10-26 in this repo — and it is **not a literal-gate-unique or submit-ready candidate**:

> **File:** `gems24-dprf1-stitched-oof-tworegime-20261026-81849d67c8bf-zeros.tif`
> **SHA-256:** `c1257c1d4b5ac9cc0a8e29b0120c614fcaa1f38474bc1f6de98c0a1afb0567f1`
> **Note (≤140 chars):** `GEMS24 DPRF1 | 52ch stitched-OOF 2-regime submod | id 81849d67c8bf | HOLDOUT-DTI 0.16379 | research; DO NOT SUBMIT`
> **Status today: DOWNLOAD YES · SUBMIT NO** — not because of any science gate (its competing-method technical
> gates PASS), but because the separate selector step has not authorized a slot: live DrivenData weekly quota is
> unknown from the sandbox, the literal registry retains the synthetic spacing-5 lattice (`registry-039`), and no
> independent replay certificate exists. **No manual override of that hold is requested or supported here: every
> file in this portfolio stays at `DO_NOT_SUBMIT` until the selector step is complete.

**XFRONT (today's new file) must not be submitted.** HOLDOUT-DTI `0.06584` is **2.5× worse** than DPRF1's
`0.16379`, and it is also worse than every serious lane in the portfolio (EUL1 0.16005, CUP1 0.15038,
TRSG1 0.14644, GVC1 0.14876, CRP1 0.13747, TNR1 0.13219). It is a valid-format, registry-unique research
download and a clean negative measurement. It spent **no submission slot**.

The download is on the first screen of `index.html` (`Download XFRONT research GeoTIFF (-zeros)`), with the
verdict written next to it: **DOWNLOAD: YES · SUBMIT: NO**. The `executive-summary.html#xfront` section states
the same verdict and points back to DPRF1 as the only candidate.

## 1. Why did `GEMSDOE32 h33-h33-2-b2` get 0.2778, and can we beat it?

*(Fuller treatments: [`24_EUL1_findings_and_executive_summary_2026-10-26.md`](24_EUL1_findings_and_executive_summary_2026-10-26.md) §1
and [`20_DPRF1_findings_and_9site_executive_summary_2026-10-26.md`](20_DPRF1_findings_and_9site_executive_summary_2026-10-26.md).
Condensed, evidence-bounded version:)*

`h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` is the owner-reported maximum at **0.2778**
(`UNVERIFIED-OWNER-REPORT` — no organizer receipt exists for any file in this repo). Its score is not evidence of
a better *detector*; it is evidence of a better **emission geometry** under the competition metric. The metric is
R=3 px tolerance-tolerant and rewards *presence near* a hidden fault, not accuracy: with only 1.18% of the
footprint labelled and a ~2–9 px "apron" of near-catalogue pixels carrying most of the recoverable mass, a raster
that (a) emits a sparse, well-spaced dot field, (b) sits in the apron rather than on the catalogue, and (c) does
not waste dots on far-field noise, wins. `B2` is exactly that: a hand-tuned dot budget with 2.0 px catalogue
clearance and 2.8 px minimum spacing — the same emission convention this repo now uses
(`gems.emission.priority_poisson(min_dist=2.8)` + 2.0 px clearance).

**Can >0.2778 be achieved?** Two things must both be true, and today neither is:

1. **Holdout truth.** Every local number is HOLDOUT-DTI, a *local* hide-and-recover proxy, not the leaderboard
   metric. DPRF1's 0.16379 is not "worse than 0.2778" — they are different estimators on different withheld
   sets. No organizer-confirmed score exists, so no local-to-leaderboard calibration is honest.
2. **Emission budget.** XFRONT's sweep is *monotone increasing* in budget across the whole preregistered grid
   (15k→45k), i.e. this detector is **under**-emitting at every budget tested, whereas the owner-reported
   live winners cluster near 37–45k dots. That is a hint that the 0.2778-class files are winning on budget
   placement, not on physics — and it is the one lever that does not require a better detector.

**Copying `h33-h33-2-b2` is prohibited by charter** (B2 is a reference, never a resubmission), and it would
waste a slot re-measuring a known number.

## 2. What XFRONT did (one lane, two locked arms, six layers)

Hypothesis: *a buried fault displaces the layer interfaces it offsets, so the **across-strike step** it imposes
should appear **at the same place** in physically independent layers — RTP magnetics (`rtp`), isostatic gravity
(`iso_grav_anom`), AEM depth-to-basement (`depth_to_base_surf`), AEM conductivity (`cond_surf`), DEM
(`det_elev`), and GNSS shear-strain rate (`geod_shearrate`) — while the layers' **orientations** should agree
more than a rotation null predicts.*

Operator (frozen in `src/gems/xfront.py`):

- Per layer *m*, at two scales σ∈{1.2, 3.0}: `p_m` = within-scale percentile of the across-strike derivative
  magnitude; weight `w_m = clip((p_m − 0.70)/0.30, 0, 1)`; orientation θ_m.
- **Corroboration** `C = Σ w_m / 6` (how many independent layers step here).
- **Orientation coherence** `R = |Σ w_m·e^{2iθ_m}| / Σ w_m` (do they step in the same direction?).
- `E_R = clip((R − mean of a 19-draw translation null) / (1 − mean), 0, 1)` (null seed 20261026).
- **Arm A** `score = C · E_R` (the preregistered mechanism). **Arm B** `score = C` alone (pre-specified
  mechanism ablation, identical eligible set) — arm selection by the preregistered rule.
- Zero outside the eligible set (`Σ w_m ≥ 2.0`, 363,026 px = 7.0% of the footprint) — amendment A1 was filed
  after the smoke test proved `R ≡ 1` when only one layer contributes, i.e. coherence is *undefined* as
  corroboration for a single layer.

Emission: `priority_poisson(min_dist=2.8)` with 2.0 px catalogue clearance over a preregistered budget grid
{15k, 20k, 25k, 30k, 37,654, 45k}, selection statistic = **20% sparse-simulated DTI** (the pre-specified
density-matched estimator), reported together with the dense statistic.

## 3. Results (HOLDOUT-DTI, `gems-segment-pooled-v1`, 60,988 withheld positives)

| Arm | Budget | Dense HOLDOUT-DTI | Sparse 20% | Sparse 10% | Sparse 5% |
|---|---:|---:|---:|---:|---:|
| A | 15,000 | 0.02880 | 0.02373 | — | — |
| A | 20,000 | 0.03649 | 0.02892 | — | — |
| A | 25,000 | 0.04228 | 0.03206 | — | — |
| A | 30,000 | 0.04757 | 0.03515 | — | — |
| A | 37,654 | 0.05383 | 0.03863 | — | — |
| A | 45,000 | 0.05940 | 0.04174 | — | — |
| B | 15,000 | 0.03230 | 0.02826 | — | — |
| B | 20,000 | 0.03975 | 0.03233 | — | — |
| B | 25,000 | 0.04516 | 0.03823 | 0.02343 | 0.02303 |
| B | 30,000 | 0.05211 | 0.04269 | 0.02443 | 0.02284 |
| B | 37,654 | 0.05983 | 0.04858 | 0.02676 | 0.02308 |
| **B (selected)** | **45,000** | **0.06584** | **0.05283** | **0.02931** | **0.02302** |

- **Selected:** arm **B**, budget **45,000** — a **boundary** optimum. The selection statistic rises monotonically
  across the entire grid: there is no interior optimum, and the lane is under-emitting everywhere in 15k–45k.
- **Mechanism ablation (pre-specified, paired, 4/4 folds):** arm B 0.06584 vs arm A 0.05940, paired Δ
  **+0.00644** (95% CI [+0.00132, +0.01243]). The rotation-null orientation factor is **actively harmful**.
- **Leakage canary:** PASS, worst extremity 0.59617 (from `edge_mag_det_elev`) over 12 features (threshold 0.90).
  Pooled diagnostic AUC: raw corroboration **0.5439**, arm B 0.5137, arm A 0.5052, **excess coherence 0.5052**,
  coherence 0.5132, translation-null coherence 0.5133.
- **Novelty vs registry (62 entries):** surface max |rho| **0.1245**, final-dot max |rho| **0.1304**,
  max 3-px dot overlap over 61 competing-method rasters **0.4532** (limit 0.70), 83/83 peer blobs **0.4532** —
  both method and peer lanes **PASS**. Overlap with this repo's own lanes: DPRF1 0.2483, EUL1 0.2502,
  TRSG1 0.2219, TNR1 0.2178, SAHG1 0.2874, CRP1 0.1961, CUP1 0.1806, GVC1 0.1874.
- **Distance profile:** 39,456 dots, median 21.26 px from the catalogue, 23.7% in the 2–9 px apron, 52.3% beyond
  2 km — i.e. this detector is *not* an apron-collapsed copy of the catalogue.
- **Exact-file C2ST (nuisance families only): FAILED.** Candidate AUC **0.5835** (Holm p 0.02, null p95 0.52463)
  vs labels-first reference AUC 0.50401 — the emitted dots are predictable from road / mining-claim /
  acquisition-block features alone, i.e. partly accessibility and cultural structure, not fault structure.
- Format: strict whole-array `[0,1]` PASS, CRS/shape/geotransform PASS, single band, `ok_to_upload=false`
  (a format validator cannot authorize an upload).

## 4. Interpretation — the useful part of a negative

**The label-free corroboration geometry is the part that works; the orientation refinement is not.** Raw
corroboration is the most label-associated of the six candidates (pooled diagnostic AUC 0.5439 vs 0.5052 for the
excess-coherence factor, i.e. essentially chance), and dropping the coherence factor — arm B — is what makes the
ablation win. All are far below the 0.90 leakage threshold, so none of this is leakage; it is a weak detector. The physical reason is now documented rather than guessed:
all six orientation fields are dominated by the **same regional structural grain** (Basin-and-Range NNE strike), so
translating the layers cannot break their agreement — translation is the wrong null for an orientation statistic.
A rotation or strike-permutation null would be the correct test, and it is a cheap, preregistered follow-up if a
future lane wants the orientation idea back.

**The C2ST flag is a real confound, not a nuisance to explain away.** Roads and mining claims follow valley floors
and basin margins; DEM steps, gravity gradients, AEM depth-to-basement changes and magnetic gradients all live in
exactly those places. Part of what this detector calls "corroboration" is *human access*. That is a genuine
scientific finding about label-free multi-physics stacking, and it is recorded as a gate failure.

**Divergence from the parent is not sufficient.** XFRONT is the least parent-convergent lane this repo has run
(max 3-px overlap 0.4532; only 0.2483 with DPRF1) — i.e. the "parent convergence blocks uniqueness" diagnosis is
*not* the binding constraint here. It is simply a weaker detector. Uniqueness is necessary but nowhere near
sufficient.

**Sparse-simulated DTI is sampling-density dependent, not a stable estimator.** At a fixed raster the statistic
decays 0.05283 → 0.02931 → 0.02302 as truth sampling goes 20% → 10% → 5%. Any future use must state the
fraction; comparisons across fractions are meaningless.

**Lane budget:** 1 experiment of 3, 413 s wall-clock, ~2.1 GiB peak. Lane is now **stopped** — no rerun, no retune.

## 5. Nine-site executive summary (updated; scores UNVERIFIED-OWNER-REPORT unless stated)

Receipt: [`evidence/nine_site_executive_summary_20261026.json`](../evidence/nine_site_executive_summary_20261026.json)
and the EUL1 update. XFRONT does not change any per-site verdict; the "XFRONT 3-px overlap" column is the new
evidence that today's file is unique against every one of them.

| Site | Historical best (owner-reported) | Latest unique artifact examined | Status | XFRONT 3-px overlap | Obvious verdict |
|---|---|---|---|---:|---|
| **GEMSDOE24** | `h25-1-dotted-h19-5-d1-5` 0.2477 | **DPRF1** `…81849d67c8bf-zeros` HOLDOUT-DTI **0.16379**; XFRONT 0.06584 (negative) | DPRF1 unscored; XFRONT unscored | 0.2996 | **Highest recorded local artifact = DPRF1 file above, still held at `DO_NOT_SUBMIT`. DO NOT SUBMIT XFRONT.** |
| GEMSDOE25 | `dotted-h19-5-d2-8` 0.2600 | `h66-mgd…da617550a0e9` scored 0.0742 | already scored | ≤0.3230 | DO NOT RESUBMIT (apron collapse) |
| GEMSDOE27 | `topo-gap-closure…d1-5` 0.2449 | `h29-…celf…511898747886` scored **0.2190** | already scored | 0.2656 | Best already-scored 2026-10-25 unique method; do not duplicate |
| GEMSDOE28 | `h36-1-rung30-blind-r1` 0.2710 | `s18-mxtp…3e95505c011a` scored 0.0217 | already scored, holdout FAIL | 0.2642 | DO NOT SUBMIT |
| GEMSDOE30 | `d28-poisson300m…44090` 0.2600 | `MSDB1…e7856ec3f14a` scored 0.1462 | already scored | 0.4532 (vs `gemsdoe30-sgmc-hedge-d10`) | DO NOT RESUBMIT |
| GEMSDOE31 | `h27-4-solo-d28` 0.2708 | `h31-hvdc…43714168` unscored, own holdout PASS | unscored sibling | 0.2567 | Secondary unscored sibling; locally weaker apron profile than DPRF1 |
| GEMSDOE32 | **`h33-h33-2-b2` 0.2778** | `h-geo-conduit…2d0d0c5e` unscored, repo says DO NOT SUBMIT | B2 prohibited copy | 0.2451 | DO NOT SUBMIT; B2 is a reference, never a resubmission |
| GEMSDOE33 | `h33d-analog…r30` 0.2632 | `a33-l1…85c94a805a34` unscored, own holdout FAIL | negative | 0.2534 | DO NOT SUBMIT |
| GEMSDOE36 | `anderson…pinn-38854` 0.2750 | none valid (legacy copied/leaky retired) | no candidate | 0.2101 | DO NOT SUBMIT |

Overlap column = maximum 3-px dot overlap between XFRONT and any registry entry whose filename carries that
site prefix, excluding the synthetic spacing-5 calibration lattice `registry-039` (0.9991 against any candidate).
All values are far below the 0.70 Rule-1 ceiling: XFRONT is unique against every one of the nine sites.

**Bottom line unchanged across all nine sites: no site today has a submit-authorized unique artifact.**
GEMSDOE24/DPRF1 is the highest-scoring recorded local artifact (still not literal-gate-unique); GEMSDOE32's 0.2778 is the highest owner-reported score and is
prohibited to copy; the gaps among the top owner-reported scores (31 +0.0070, 28 +0.0068, 36 +0.0028 vs 0.2778)
are inside bootstrap noise.

## 6. Next steps (ranked by P(Win); no further experiments this session — lane budget spent)

1. **Selector step for DPRF1** (separate from any lane): record the live DrivenData weekly-quota state from the
   submission page into a dated receipt, prospectively separate the synthetic spacing-5 calibration lattice from
   competing methods in the selector policy, and implement the independent replay certificate. Until then every
   file in the portfolio is correctly `SUBMIT: NO`.
2. **Budget-placement lane, not another detector**: XFRONT's monotone sweep is the strongest signal this session
   produced. A preregistered lane that holds the DPRF1 detector fixed and sweeps *budget × spacing × clearance*
   (e.g. 45k–120k dots) under the sparse-simulated statistic is cheap and directly targets the lever the
   owner-reported winners appear to be pulling.
3. **Rotation null for the orientation idea** (if it is ever revived): replace the 19-draw translation null with a
   strike-permutation / rotation null, and re-run the A-vs-B ablation. Cheap; requires a new preregistration.
4. **On an unrestricted machine:** `H24-INSAR4` (NASA ASF OPERA DISP-S1, free/official) remains the only wholly
   independent sensor physics not yet tested; unreachable from this sandbox.

## 7. Limitations, irregularities, framing integrity

- No ORGANIZER-CONFIRMED score exists for any file discussed; the `0.3195` vs `0.4413` leader claims conflict and
  are unverified. Fault recovery is a structural proxy, not geothermal-vent discovery.
- `paired_vs_current_best` is deliberately **null**: DPRF1 (0.16379) was not retrained this session, and a recorded
  point estimate is not replayed evidence, so no paired CI is asserted (amendment A8). The comparison in §0 is a
  difference of recorded point estimates, not a paired bootstrap.
- **Novelty asymmetry (recorded, not smoothed over):** the *surface* comparison reports
  `literal_all_entries_passed: true` while the *final-dots* comparison reports `false`. The scientific comparators
  (61 competing-method rasters, 83 peer blobs) PASS at 0.4532; the failing entry is the synthetic spacing-5
  calibration lattice `registry-039`, whose dots are within 3 px of 99.91% of any candidate's dots (a 5-px lattice
  is within √8 px of every interior cell). This is the same structural blocker as every other lane and is not
  fixable inside a lane.
- Sandbox limits: DrivenData, NLR, USGS, OpenEI and NASA hosts unreachable (only GitHub/PyPI respond); competition
  data are the hash-pinned owner bridge, integrity-verified but not organizer-authenticated. 3.9 GiB RAM / 2 CPU.
- The six layers are the same feature stack the supervised lanes already use; XFRONT's contribution is the
  *combination rule* and the *null*, not new data. It cannot exceed what those layers contain.

## 8. JSON run card (Rule 5 — canonical copy in `evidence/xfront_run_card_20261026.json`)

```json
{
  "lane_id": "H24-XFRONT",
  "hypothesis": "A buried fault imposes a step on every layer it offsets, so across-strike steps in independent physics coincide; corroboration across layers plus orientation agreement above a rotation null locates faults absent from the catalogue.",
  "mechanism": "Per-layer across-strike derivative percentile weights and structure-tensor orientations at sigma in {1.2, 3.0}; C = sum(w)/6, R = |sum(w*e^{2i theta})|/sum(w); E_R = excess over a 19-draw translation null; arm A = C*E_R, arm B = C; zero where sum(w) < 2.0.",
  "named_non_fault_mimic": "Unfaulted lithologic contact gradients, basin-margin gravity/magnetic gradients, and cultural corridors (roads, claims) that follow valleys and produce co-located steps in every layer",
  "holdout": {"label": "HOLDOUT-DTI", "evaluator_version": "gems-segment-pooled-v1", "dti": 0.06584109933014508, "ci95": [0.05496516536426873, 0.07904208065066184], "n_withheld_positive_pixels": 60988},
  "selected_arm": "B",
  "selected_budget": 45000,
  "paired_vs_baseline": {"comparator": "arm A (pre-specified mechanism ablation), same budget", "candidate_dti": 0.06584109933014508, "baseline_dti": 0.05939811824651516, "paired_delta_dti": 0.006442981083629916, "ci95": [0.0013214304026682587, 0.012426835263258773], "fold_wins": "4/4"},
  "c2st_exact_file": {"candidate_auc": 0.5835293469094295, "holm_p_value": 0.02, "labels_first_auc": 0.5040084703386403, "strict_gate_passed": false},
  "novelty": {"registry_entries_checked": 62, "competing_method_rasters": 61, "max_abs_rank_correlation_surface": 0.12451287495195174, "max_abs_rank_correlation_final_dots": 0.13039102427111587, "max_3px_dot_overlap_method_lanes": 0.45321370640713704, "max_3px_dot_overlap_peer_blobs": 0.45321370640713704, "method_lane_passed": true, "peers_passed": true, "literal_all_entries_passed_final_dots": false},
  "raster_sha256": "04d2359a58ab85d1e66076d0543e1fbb1cd89a22312d4474f8dd8c30bb523edf",
  "validator": {"format_valid": true, "strict_whole_array_0_1": true, "in_footprint_positive_pixels": 39456, "submission_authorized": false},
  "submission_name": "gems24-xfront-c-corrob-45000-20261026T162655Z-921f4f037290-zeros.tif",
  "note": "GEMS24 XFRONT armB | cross-modal oriented-step corroboration | 45000 dots | id 921f4f037290",
  "verdict": "negative",
  "ok_to_download": true,
  "ok_to_submit": false,
  "submission_slots_used": 0,
  "organizer_confirmed_score": null
}
```
