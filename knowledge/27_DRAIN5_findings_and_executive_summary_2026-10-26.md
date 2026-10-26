# H24-DRAIN5 findings and executive summary update (2026-10-26)

> **DOWNLOAD: YES (research) · SUBMIT: NO — automatic verdict, zero human-inspector
> fallback. OK TO SUBMIT TODAY: NOTHING.** H24-DRAIN5 is the first lane to beat the
> bit-identical DPRF1 replay in a paired holdout comparison, and it is simultaneously
> a **duplicate lane** of DPRF1 under Rule 1. Both facts are the deliverable.
> **DPRF1 remains the #1 unscored unique-lane candidate.** Do not submit DRAIN5,
> do not submit both files, and do not retune DRAIN5 — the hypothesis budget for
> this session is spent (3 arms) and the result is frozen.
>
> Panel order everywhere (site, README, this document): **DPRF1 first** (#1
> unscored unique-lane candidate), **DRAIN5 second** (best local detector
> measurement, duplicate dots), then EUL1 and the historical lanes. Every score
> below is labelled **HOLDOUT-DTI** or **UNVERIFIED-OWNER-REPORT**; there is still
> **no ORGANIZER-CONFIRMED score** attached to any file in this repository, and
> a projection is never written as a score.
>
> Preregistration: `knowledge/26_preregistered_DRAIN5_2026-10-26.md` (committed
> `3739d7d` before implementation `a8a4801` and the single full run). No amendment
> was required; the design was executed exactly as frozen (verified by
> `tests/test_drainage.py`, 6 deterministic analytic-DEM tests, and a full diff of
> the runner against the EUL1 precedent before launch).
> Prior portfolio context: `knowledge/25_portfolio_escalation_and_final_executive_summary_2026-10-26.md`.
> Supporting analysis retained verbatim: `knowledge/14_h33_analysis_2026-10-25.md`
> (B2/H33 geometry) and the EUL1 findings in `knowledge/24_...md`.

## 1. Executive decision

| # | File (one-click download) | Estimated score | Lane-unique vs all compared | OK to download | OK to submit |
|---|---------------------------|-----------------|-------------------------------|----------------|--------------|
| 1 | `gems24-dprf1-stitched-oof-tworegime-20261026-81849d67c8bf-zeros.tif` (SHA-256 `c1257c1d…f0567f1`) — **[#1 UNSCORED UNIQUE-LANE CANDIDATE]** | **HOLDOUT-DTI 0.16379** [0.15045, 0.17739], `gems-segment-pooled-v1`, 60,988 withheld positives. Not a leaderboard forecast. | YES under the competing-method cut (max 3-px overlap 55.78% vs 43 method rasters; 54.94% vs 84 peer blobs; max \|ρ\| 0.3468). NOT unique under the literal all-registry cut (synthetic spacing-5 lattice `registry-039`); unresolved. | YES | **NO** — `gems-selector-v2-literal-quota-fail-closed`: `DO_NOT_SUBMIT` (literal G4, live quota unknown, replay certificate missing) |
| 2 | `gems24-drain5-negative-drainage-knickpoint-20261026-ff95d6fb3205-zeros.tif` (SHA-256 `4b171e8d92d49a595684b58d188fe4117b653ec9cda8263919c25802d6539e32`) — **[BEST LOCAL MEASUREMENT · DUPLICATE LANE — RESEARCH ONLY]** | **HOLDOUT-DTI 0.16950** [0.15627, 0.18343], same evaluator/count. Not a leaderboard forecast. | **NO** — 83.55% of dots within 3 px of DPRF1 (Rule-1 limit 70%) and 82.87% vs EUL1; yet ≤57.42% vs every other registry raster and ≤55.17% vs 84 peer blobs: it duplicates *our own family*, nothing external. | YES | **NO** — selector `DO_NOT_SUBMIT`; also never to be submitted alongside DPRF1 (would spend two slots on near-identical dots) |
| 3 | `gems24-eul1-negative-euler-contact-20261026-7f03fbe6eb71-zeros.tif` | HOLDOUT-DTI 0.16005 [0.14729, 0.17278]; paired −0.00375 vs replay (n.s.). | NO (86.57% vs DPRF1) | YES (research) | NO — closed negative; do not retune |

There is **no #2 unique candidate** yet: the two most recent "next lanes" both
failed uniqueness against the DPRF1 family (see §5). The synthetic
lattice-uniqueness question is **not resolved** for DPRF1 and is not resolvable
by this lane; it awaits a separate, prospective selector-policy decision that
must never retroactively edit the registry.

Note on bookkeeping: DRAIN5's run card (0.16950 > 0.16379) mechanically becomes
the *recorded point-best* that `gems.benchmarks` and selector gate G3 compare
against — the floor for future lanes, and nothing more. That automation is
correct, but it must never be read as "DRAIN5 is now the champion to submit":
the file's *points* are higher; its *lane* is closed as a duplicate.
`docs/data/current_best_review.json` will likewise name DRAIN5 through the same
deterministic scan; its own text states it is not a uniqueness or submission proof.

## 2. What was run (frozen spec, one full run)

DRAIN5 is a strict increment over the EUL1 experimental design with the evidence
class replaced: the 7 Euler N=0 channels are swapped for 7 label-free
**D8 drainage-network channels derived only from `dem_100m`** (the cached survey
band `det_elev`), three of them gating a re-weighted Regime B. Everything else —
the DPRF1 52-channel stack, negative sampling (100k/segment, `d_vis ≥ 3px`),
HGB depth-3 / 300 trees, stitched quadrant+diamond OOF, apron debias, two-regime
2.8 px submodular allocator, 37,654-dot budget, evaluator, registry, novelty,
C2ST, selector, packaging — is inherited byte-identically from the frozen DPRF1
pipeline, whose same-session replay (Arm 2) reproduced the recorded card
**bit-identically** for the third time (dti 0.1637924246971501, folds, bridge,
paired deltas).

The drainage physics is the first *routed* fluvial computation in the portfolio
(all prior terrain channels are local-window filters, including TRSG1's so-called
"drainage-break" features). On a 5,164,312-cell no-fill D8 network:

- `drn_logA` — log10(1+A) upslope area (catchment context);
- `drn_chan_dist` — distance to the A ≥ 100-cell (≥ 1 km²) channel skeleton;
- `drn_knick` — log10(1 + slope-gradient positive residual along channels):
  Wobus-style knickpoint residual `G − max(0, G_down, G_down2)` along the receiver chain;
- `drn_ksn` — log10(1 + S·A^0.45), the stream-power steepness index (tectonic uplift proxy);
- `drn_bend` — flow-direction change along the receiver (deflected-drainage capture);
- `drn_knick_lineament` — 31-px (3.1 km) **circular max-contrast lineament score over the knickpoint cloud** (the novel transform: cross-catchment knickpoint co-linearity is the fault signature; a single knickpoint is not);
- `drn_relict` — high-DEM × low-relief × low-channel-density relict-landscape flag.

Census: 1,727 endorheic sinks (0.033% of valid DEM cells) — the locked no-fill
policy is harmless at this magnitude and preserves the genuine Great Basin
sinks (playas) that pit-filling would erase. Channel cells (A ≥ 100): 395,567.
Runtime 1,001.4 s, peak RSS 3.16 GiB in a 3.8 GiB sandbox.
Code: `src/gems/drainage.py`, `scripts/run_drain5_lane.py`.

## 3. Results (*the* 3 arms; budget now spent)

All numbers `gems-segment-pooled-v1`, 60,988 withheld positives, α = 0.2, β = 0.8,
300 m triangular credit; 95% CIs normal-approximation over 4 equal-count truth chunks.

| Arm | Configuration | HOLDOUT-DTI | 95% CI | Paired Δ vs replay (same-session) | Fold wins |
|-----|---------------|------------:|--------|-----------------------------------|----------:|
| **1 — DRAIN5 primary** | 59ch + knickpoint-gated Regime B | **0.169504** | [0.156274, 0.183429] | **+0.005712 [+0.001361, +0.010028]** | **4/4** |
| 3 — channels-only | 59ch, legacy Regime B | 0.166398 | [0.153312, 0.180176] | +0.002606 [−0.001265, +0.006726] | 3/4 |
| 1 vs 3 (Regime-B gating) | — | — | — | **+0.003106 [+0.001302, +0.004994]** | **4/4** |
| 2 — no-drainage replay | 52ch DPRF1 control | 0.163792 | [0.150449, 0.177393] | bit-identical to recorded DPRF1 card | — |

Bridge evaluator (`bridge-report-visible-v1`) agrees: DRAIN5 0.18209 vs replay
0.17671, paired Δ +0.005372 [+0.000478, +0.010263], 4/4 folds. Sensitivity
(monotone squashes of the same pixel set — mathematics, not new information):
identity/binary 0.16950, √x 0.17086, x² 0.16869 (all over the replay).

Leakage canary **PASS 59/59** (both polarities, ≤ 0.90). The drainage channels
carry the strongest *marginal* evidence of any increment tried: solo pooled AUC
`drn_ksn` **0.6059**, `drn_knick_lineament` **0.5912**, `drn_chan_dist` 0.5354,
`drn_logA` 0.5251, `drn_knick` 0.5249, `drn_bend` 0.5203, `drn_relict` 0.5062 —
versus the Euler increment's 0.502–0.529. That ordering, plus the paired wins,
is good evidence the knickpoint/steepness signal is real geomorphology, not
leakage (all channels are catalogue-blind: DEM-only, so no `d_cat`/`d_vis`
construction anywhere near them; visible faults remain masked pixel-exactly).

Novelty (the verdict that matters), exact-file C2ST **PASS** (AUC 0.52679,
Holm p = 0.163) but final dots: **83.548% within 3 px of DPRF1** and 82.865% of
EUL1 — Rule 1 FAIL (> 70% = duplicate). Pre-placement surface rank-correlation
was fine (max |ρ| 0.537 ≤ 0.90). Distance profile is B2-like (min 2.24 px,
median 21.2 px, apron 22.6%, far-field > 20 px 52.2%) — the *geometry* is right;
the *dot identity* is the parent's. The selector receipt records the first-ever
pass of gate G3 (strictly-positive paired win over the recorded point-best) and
still returns `DO_NOT_SUBMIT` on G4 (literal lattice), live-quota, and replay
certificate. **Verdict: negative (duplicate lane). No Arm 4, no retune, no
KERN6-with-DRAIN5-dots reuse** — KERN6 in a future session is a *new*
preregistration that may use the drainage channels as evidence, never this dot set.

## 4. Why `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif` (GEMSDOE32) reports 0.2778 — PhD analysis, and whether a unique file can beat it

First, the evidence status, because it disciplines every sentence below: 0.2778
is an **UNVERIFIED-OWNER-REPORT**. The claim queue in the owner brief cites three
incompatible leaderboard ceilings (0.2778 for B2; elsewhere 0.3195; elsewhere
0.4413 — the latter attributed to a "Q-ARGMAX-B2-8PX / 8-bit quantization"
forecast that reads as a projection, not a receipt). None of the three is an
organizer receipt in git. The most conservative, file-pinned, reproducible claim
is 0.2778 on the specific SHA above, and its *construction* is fully verifiable
(`knowledge/14_h33_analysis_2026-10-25.md`): B2 = D2.8's 44,090 Poisson-thinned
H19-5 dots **minus 6,436 dots within 200 m of the catalogue**, zero added,
leaving — note the arithmetic — exactly **37,654** dots, 49.2% of them beyond
2 km from any catalogued fault. The 37,654-dot budget this portfolio's recent
lanes emit was adopted from that geometry; DRAIN5 inherits it deliberately.

Why does subtracting near-catalogue dots raise a distance-weighted Tversky score?
DTI = T / (T + 0.2·F + 0.8·N) with a 300 m triangular partial-credit kernel
(credit falls linearly to zero at 300 m). In that geometry, a dot ≤ 200 m from
a *catalogued* fault is nearly worthless and expensive:

1. **Credit duplication.** Its 300 m credit cone overlaps the cone it would earn
   against the very truths already catalogued/trained-on; the hidden-fault
   evaluation is, by construction, a surface where the catalogue is a *censored,
   discovery-biased* sample of truth — the undiscovered faults are precisely the
   ones not yet adjacent to mapped ones in the easy terrain. Near-catalogue dots
   re-claim already-claimed territory.
2. **Cheap-but-numerous FP mass.** Each false dot costs α = 0.2; ~6.4 k dots is
   ~1.3 k effective F mass removed at almost no T sacrifice (the truths they
   could hit are largely masked catalogue).
3. **Spacing ≈ kernel.** Poisson thinning at 2.8 px (280 m) just under the 300 m
   kernel makes adjacent credit cones nearly disjoint, so T is purchased at
   ~one dot per independent lottery ticket; denser lattices pay twice for the
   same covered truth.
4. **Far-field allocation.** With β = 0.8, a missed hidden fault (FNs) costs 4×
   a false dot. Sparse far-field coverage, where surface mapping is blind under
   alluvium, buys down N — B2 holds ~half its budget beyond 2 km.

The converse failure is measured *in this repository*, twice: GVC1, whose dots
collapse into the 2–5 px halo around catalogued faults (45.8%), scored 0.14876
HOLDOUT-DTI locally yet **owner-reported 0.0859 live**; and an owner-reported
live 0.0339 for a halo-heavy predecessor. Local-holdout gains from catalogue-hugging
do not transfer to the hidden-fault target. DRAIN5's parent (DPRF1) and DRAIN5
itself were built to the corrected geometry (52.2% far-field > 20 px, 22.6%
apron, 0 dots ≤ 2 px) — that axis is, so far as holdout evidence can say,
*saturated*.

**Can a unique submission beat 0.2778?** Two distinct questions are convolved in
that phrasing, and they must be separated:

- *Can a unique submission be a better hidden-fault detector than B2?*
  Plausibly yes — B2 is a thinned detector chain from another era of the
  portfolio (H19-5), and this session produced the first paired, replay-controlled
  evidence of a detector increment (drainage knickpoint steepness) beating our
  best current detector. The honest effect sizes are small in HOLDOUT-DTI
  (+0.0026 n.s. for channels alone; +0.0057 strict-positive with allocation
  gating) and the local holdout measures recovery of *catalogue-type*
  displacements, not necessarily discovery of the organizer's hidden set.
- *Does any local measurement licence a forecast "> 0.2778 on the leaderboard"?*
  **No.** HOLDOUT-DTI and the leaderboard score differ in the truth set, the
  censoring, and the base rate; no calibration mapping exists, and manufacturing
  one (e.g. the brief's own 0.4413-style quantization forecast) is exactly the
  "a projection written as a score" error this repository's protocol exists to
  prevent. The path to actually knowing is unchanged and owner-gated: settle the
  selector policy (quota receipt + replay certificate) and score DPRF1 once —
  the sole file whose dots are both strong *and* lane-unique. DRAIN5 revises the
  next-lane design; it does not create a second spendable artifact.

The ranked-hypothesis queue from the owner brief, as amended by this session:
(1) H24-KERN6 (DTI-kernel soft-label regression + rank allocation, drainage
channels built in *from the start*, novelty checked against DPRF1 *and* DRAIN5
*and* EUL1 surfaces — the soft-target geometry change is the current best theory
of how to keep the knickpoint signal while decorrelating dot placement);
(2) H24-SEGBAL7 (segment-balanced weights); (3) H24-INSAR4 (OPERA DISP-S1
InSAR) and (4) H24-3DEP8 (finer 3DEP DEM) remain network-unreachable from this
sandbox (only github.com / pypi answer; checked 2026-10-26T16:18Z) and were
again excluded, not attempted.

## 5. The parent-convergence result (the scientific deliverable)

Three independent evidence classes have now been appended to the DPRF1 parent
stack under the frozen allocator, and all three were re-quantized by that
allocator onto the parent's dot lattice: CUP1 91.2%, EUL1 86.57%, DRAIN5 83.55%
of final dots within 3 px of DPRF1. Surface rank-correlations stayed well below
the 0.90 tripwire every time (DRAIN5 max |ρ| 0.537) — **surface independence
does not survive shared top-2.8 px submodular placement**. The near-monotone
sequence (91.2 → 86.6 → 83.5) tracks how *marginal* each increment's evidence
is (Euler channels AUC ≈ 0.50–0.53 vs drainage 0.59–0.61), i.e. stronger
increment evidence *does* move a fraction of dots — DRAIN5 moved the most,
~16.5% of dots are new — but no planned channel class is plausibly strong
enough to push overlap under 70% while sharing the parent's 52 channels and
the parent's alloy of ~28.5 M candidate cells. Operational consequence, now a
standing rule context note: **a lane that wants uniqueness must change the
target and allocator geometry, not merely append channels** (KERN6's soft
distance-weighted targets with rank allocation is the queued realization).
Negative-duplicate logs like this one are the deliverable form the protocol
prescribes ("negative results are deliverables"); this receipt exists so no
future session re-buys the experiment.

## 6. Nine-site executive summary (DRAIN5 update)

Full machine receipt: `evidence/nine_site_executive_summary_drain5_20261026.json`
(built by `scripts/build_drain5_nine_site_summary.py` from SHA-verified
re-fetches of every sibling's inspected artifact at its pinned commit — local
caches never trusted without hash match). DRAIN5's 3-px dot-overlap against each
focus repository's inspected GeoTIFF:

| Repository | Inspected artifact (pinned commit) | Dots | DRAIN5 overlap (3 px) | Owner-reported best on that site (UNVERIFIED) |
|-----------|-------------------------------------|-----:|----------------------:|------------------------------------------------|
| GEMSDOE24 | `gems24-dprf1-…81849d67c8bf-zeros.tif` | 37,654 | **0.835476 — duplicate** | DPRF1 unscored locally; `h25-1-dotted-h19-5-d1-5` 0.2477 |
| GEMSDOE25 | `d28-b2-poisson300m-v1-…-zeros.tif` | 37,529 | 0.300473 | `dotted-h19-5-d2-8` 0.2600 |
| GEMSDOE27 | `2600rb-b2-2600-repro-bisector-…-zeros.tif` | 37,570 | 0.472752 | `topo-gap-closure` 0.2449 |
| GEMSDOE28 | `h36-rung31-halving-subdivision-…-zeros.tif` | 257,000 | 0.057019* | `h36-1-rung30-blind-r1` 0.2710 |
| GEMSDOE30 | `s30-c1-submodular-knapsack-site30-only-…-zeros.tif` | 37,727 | 0.414458 | `d28-poisson300m` 0.2600 |
| GEMSDOE31 | `gems31-u18-…-zeros.tif` | 37,654 | 0.350321 | `h27-4` 0.2708 (same surface lineage as GEMSDOE28's) |
| GEMSDOE32 | `h33-2-b2-h33-2-d2-8-…-zeros.tif` | 37,654 | 0.294232 | **`h33-h33-2-b2` 0.2778 (portfolio-best claim; §4)** |
| GEMSDOE33 | `gems33-submission-…-zeros.tif` | 33,571 | 0.280448 | `h33d-analog` 0.2632 |
| GEMSDOE36 | `a36-perceptron-submodular-…-zeros.tif` | 37,574 | 0.475116 | `anderson-geothermal-pinn` 0.2750 |

\* GEMSDOE28's inspected artifact emits 257,000 dots — a different operating
regime; overlap fraction is exposure-dominated and reported for completeness.

Reading: DRAIN5 sits *inside* the established 0.28–0.55 band of genuine
cross-site novelty everywhere except home. Its failure is local, exactly as
EUL1's was. Estimated-score table for submission purposes, with labels
preserved: DRAIN5 HOLDOUT-DTI 0.16950 (best local measurement), DPRF1
HOLDOUT-DTI 0.16379, EUL1 0.16005 — and **no file with an ORGANIZER-CONFIRMED
score at any site**; all sibling scores remain owner-reported until a receipt
from the submission page is pinned in git.

## 7. How submission *would* work (when something is finally OK to submit)

Owner-executed only — the agent never uploads (DrivenData ToS; project
`AGENTS.md`). Competition requirements
(https://www.drivendata.org/competitions/306/competition-doe-gems/ and the
official rules, https://docs.nlr.gov/docs/fy26osti/96647.pdf): a single-band
GeoTIFF matching the sample CRS/shape/geotransform with predicted values in
[0, 1], or a ZIP containing exactly one such GeoTIFF. The previously witnessed
portal rejection — *"Predicted values must be in range [0, 1]"* — is caused by
NaN-outside-footprint variants; for any authorized file always upload the
**`-zeros.tif`** variant (strict whole-array finite [0, 1]) and optionally paste
the ≤ 140-character note from its run card (DRAIN5's research-only note, 123
chars: "GeoDAWN det_elev D8 drainage knickpoint co-linearity on DPRF1 52ch
stitched-OOF stack. Holdout 0.170 +0.006 vs DPRF1; do not submit."). Before any
first upload, the standing pre-flight is: confirm the weekly quota on the
DrivenData submission page, verify the file's SHA-256 against the run card,
and run the repo's `--verify-recorded` verifiers.

Today's answer is unchanged: **submit nothing**; the first spendable artifact,
once the selector step's quota/replay items are settled, is DPRF1.

## 8. Receipts, reproduction, irregularities

- Run card: `evidence/drain5_run_card_20261026.json` (verbatim below);
  experiment/selector receipts: `evidence/drain5_experiment_20261026.json`,
  `evidence/drain5_selector_20261026.json`; downloads
  `docs/downloads/gems24-drain5-negative-drainage-knickpoint-20261026-ff95d6fb3205-zeros.tif`
  (+ NaN twin, single-TIF ZIP, validator/checks/preflight/note sidecars);
  preview `docs/assets/drain5-preview.png`.
- Verifiers (all executed post-run, all PASS):
  `python scripts/run_drain5_lane.py --verify-recorded`
  (checks frozen G3-aware: DRAIN5's own card is now the recorded point-best, so
  a fresh G3 compares the file against itself — the verifier excludes exactly
  that one gate and compares everything else);
  `run_dprf1_lane.py --verify-recorded`, `run_eul1_lane.py --verify-recorded`;
  an independent fresh-code audit (new rasterio session: ZIP single inner TIF
  byte-identical, strict finite {0,1}, sample grid/CRS/transform identical);
  `python -m pytest tests/test_drainage.py` (6 pass).
- Provenance notes (documentation-level, not irregularities): the regenerable
  cache `data/prepared/drainage7_features.npy` (+ `.diag.json`, containing
  sha256 of the DEM source and fill values — it stays out of git per repo
  convention) was first written by a pre-implementation timing check
  (`/tmp/drain_build_check.py`) using the committed `gems.drainage` builder, and
  the frozen runner recomputed its diagnostics deterministically from the
  rebuilt memmap; `ruff format` was applied to `src/gems/drainage.py` and
  `scripts/run_drain5_lane.py` after the frozen run (whitespace-only; PR #38/EUL1
  precedent) and `--verify-recorded` was re-run green afterwards.
  Pre-existing unrelated GitHub PR #7 (stale, 2026-10-24) was observed and
  left untouched.

## H24-DRAIN5 JSON run card (verbatim)

```json
{
  "schema_version": 2,
  "generated_utc": "2026-10-26T16:46:36.243994+00:00",
  "lane_id": "H24-DRAIN5",
  "preregistration": "knowledge/26_preregistered_DRAIN5_2026-10-26.md",
  "preregistration_commit": "3739d7daeeccb5fbca9a925c753f5883b2d18313",
  "experiments_run": 3,
  "experiment_budget_limit": 3,
  "elapsed_seconds": 1001.35,
  "peak_rss_mib": 3158.6,
  "hypothesis": "D8 drainage-network topology on the 100 m DEM \u2014 aligned channel knickpoints (downstream jumps in normalised steepness k_sn = slope * A^0.45) and flow-azimuth deflections across adjacent ephemeral washes \u2014 traces oblique/strike-slip and sheetwash-eroded piedmont faults whose interfluve scarps have been erased and that surface mapping and local-filter geomorphology miss. Seven label-free drainage channels (log flow accumulation, k_sn, knickpoint jump, knickpoint co-linearity lineament, channel distance, HAND, azimuth bend) added to the 52-channel DPRF1 stitched-OOF stack \u2014 and gating its concealed Regime-B allocation \u2014 recover held-out whole fault segments better than the identical pipeline without them.",
  "mechanism": "D8 steepest-descent routing (O'Callaghan & Mark 1984) on the Gaussian-smoothed (sigma 2 px) DEM with no depression filling (endorheic sinks terminate accumulation; sink census recorded in drainage_diagnostics) yields exact upslope area A by descending-elevation propagation. Stream-power steepness k_sn = S * A^0.45 (Flint 1974; Wobus et al. 2006) jumps downstream where a wash crosses an uplifting or laterally offset fault block; co-linear jumps across >=3 neighbouring washes and systematic azimuth bends localise the buried trace even where the scarp itself is gone. Supervised stitched-OOF, stratified near+far negatives, selective residualization (drainage channels protected as terrain), relief calibration, ridge sharpening, apron debiasing and the two-regime 300 m submodular allocator are reused unchanged from DPRF1, isolating the drainage increment.",
  "named_non_fault_mimic": "Resistant lithologic hogbacks (welded ash-flow tuff or dike ribs) producing lithologic knickpoints across parallel gullies, alluvial fan-lobe avulsion channels, Pleistocene Lake Lahontan recessional strandlines, and road borrow ditches \u2014 all of which bend or steepen ephemeral washes without any Quaternary faulting or geothermal upflow.",
  "holdout": {
    "label": "HOLDOUT-DTI",
    "evaluator_version": "gems-segment-pooled-v1",
    "TP_w": 9762.453935103526,
    "FP_w": 34256.795877469536,
    "FN_w": 51225.54606489648,
    "n_truth": 60988.0,
    "n_emitted": 38104.0,
    "dti": 0.16950396856353708,
    "n_withheld_positive_pixels": 60988,
    "n_unique_withheld_components": 3199,
    "ci95": {
      "level": 0.95,
      "interval": [
        0.1562741879960775,
        0.18342904482638064
      ],
      "method": "percentile spatial-block bootstrap of pooled TPw/FPw/FNw",
      "block_pixels": 100,
      "block_size_m": 10000,
      "n_blocks": 583,
      "resamples": 1999,
      "seed": 20261025,
      "limitation": "Internal-validation uncertainty; geologic structures may cross blocks. Not a hidden-score interval."
    },
    "folds": [
      {
        "fold": "NW",
        "TP_w": 1711.437759856225,
        "FP_w": 7810.336818744228,
        "FN_w": 8453.562240143776,
        "n_truth": 10165,
        "n_emitted": 8515,
        "dti": 0.17052383800801246,
        "coverage": 0.16836574125491638
      },
      {
        "fold": "NE_LidarGapHeavy",
        "TP_w": 2694.9820534994665,
        "FP_w": 9407.247561678076,
        "FN_w": 9816.017946500533,
        "n_truth": 12511,
        "n_emitted": 10528,
        "dti": 0.2168258694184407,
        "coverage": 0.21540900435612392
      },
      {
        "fold": "SW",
        "TP_w": 2424.2805566431243,
        "FP_w": 9602.007439462563,
        "FN_w": 18109.719443356877,
        "n_truth": 20534,
        "n_emitted": 10535,
        "dti": 0.1287288471967946,
        "coverage": 0.11806177835020572
      },
      {
        "fold": "SE",
        "TP_w": 2931.7535651047097,
        "FP_w": 7437.204057584669,
        "FN_w": 14846.24643489529,
        "n_truth": 17778,
        "n_emitted": 8526,
        "dti": 0.179904216311661,
        "coverage": 0.1649090766736815
      }
    ],
    "protocol": {
      "aggregation": "pooled TPw/FPw/FNw, not mean fold DTI",
      "buffer_m": 1500,
      "whole_components_hidden_everywhere": true,
      "visible_fault_mask": "pixel-exact, applied before credit and FP calculation",
      "catalogue_features": "must be constructed from fold.visible only",
      "alpha": 0.2,
      "beta": 0.8,
      "triangular_kernel_radius_m": 300
    }
  },
  "arms_same_evaluator": {
    "arm1_drain5_primary_59ch": {
      "dti": 0.16950396856353708,
      "ci95": [
        0.1562741879960775,
        0.18342904482638064
      ]
    },
    "arm3_channels_only_59ch": {
      "dti": 0.1663981140024072,
      "ci95": [
        0.15333626776502107,
        0.18042809146870123
      ]
    },
    "arm2_nodrain_52ch_replay": {
      "dti": 0.1637924246971501,
      "ci95": [
        0.15044621733051888,
        0.1773903019943756
      ]
    }
  },
  "paired_comparisons": {
    "arm1_vs_arm2_nodrain_replay": {
      "evaluator_version": "gems-segment-pooled-v1",
      "candidate_dti": 0.16950396856353708,
      "baseline_dti": 0.1637924246971501,
      "paired_delta_dti": 0.0057115438663869755,
      "paired_delta_ci95": [
        0.0013610518073050484,
        0.010033729621204543
      ],
      "ci95_strictly_positive": true,
      "fold_wins": 4,
      "n_folds": 4,
      "min_fold_delta": 0.0010458717870563128,
      "folds": [
        {
          "fold": "NW",
          "candidate_dti": 0.17052383800801246,
          "baseline_dti": 0.15424896557736514,
          "delta_dti": 0.01627487243064732,
          "candidate_wins": true
        },
        {
          "fold": "NE_LidarGapHeavy",
          "candidate_dti": 0.2168258694184407,
          "baseline_dti": 0.21227321465377372,
          "delta_dti": 0.004552654764666986,
          "candidate_wins": true
        },
        {
          "fold": "SW",
          "candidate_dti": 0.1287288471967946,
          "baseline_dti": 0.12768297540973828,
          "delta_dti": 0.0010458717870563128,
          "candidate_wins": true
        },
        {
          "fold": "SE",
          "candidate_dti": 0.179904216311661,
          "baseline_dti": 0.17442448661596,
          "delta_dti": 0.005479729695701013,
          "candidate_wins": true
        }
      ]
    },
    "arm3_vs_arm2_channel_effect": {
      "evaluator_version": "gems-segment-pooled-v1",
      "candidate_dti": 0.1663981140024072,
      "baseline_dti": 0.1637924246971501,
      "paired_delta_dti": 0.0026056893052570917,
      "paired_delta_ci95": [
        -0.0014365119507348755,
        0.006803978051124216
      ],
      "ci95_strictly_positive": false,
      "fold_wins": 3,
      "n_folds": 4,
      "min_fold_delta": -0.0011869988475173288,
      "folds": [
        {
          "fold": "NW",
          "candidate_dti": 0.16832992041770573,
          "baseline_dti": 0.15424896557736514,
          "delta_dti": 0.014080954840340582,
          "candidate_wins": true
        },
        {
          "fold": "NE_LidarGapHeavy",
          "candidate_dti": 0.21291583731492397,
          "baseline_dti": 0.21227321465377372,
          "delta_dti": 0.000642622661150255,
          "candidate_wins": true
        },
        {
          "fold": "SW",
          "candidate_dti": 0.12649597656222095,
          "baseline_dti": 0.12768297540973828,
          "delta_dti": -0.0011869988475173288,
          "candidate_wins": false
        },
        {
          "fold": "SE",
          "candidate_dti": 0.17584968609584054,
          "baseline_dti": 0.17442448661596,
          "delta_dti": 0.00142519947988054,
          "candidate_wins": true
        }
      ]
    },
    "arm1_vs_arm3_regime_gating_effect": {
      "evaluator_version": "gems-segment-pooled-v1",
      "candidate_dti": 0.16950396856353708,
      "baseline_dti": 0.1663981140024072,
      "paired_delta_dti": 0.003105854561129884,
      "paired_delta_ci95": [
        0.001721805023152463,
        0.00447801300152312
      ],
      "ci95_strictly_positive": true,
      "fold_wins": 4,
      "n_folds": 4,
      "min_fold_delta": 0.0021939175903067376,
      "folds": [
        {
          "fold": "NW",
          "candidate_dti": 0.17052383800801246,
          "baseline_dti": 0.16832992041770573,
          "delta_dti": 0.0021939175903067376,
          "candidate_wins": true
        },
        {
          "fold": "NE_LidarGapHeavy",
          "candidate_dti": 0.2168258694184407,
          "baseline_dti": 0.21291583731492397,
          "delta_dti": 0.003910032103516731,
          "candidate_wins": true
        },
        {
          "fold": "SW",
          "candidate_dti": 0.1287288471967946,
          "baseline_dti": 0.12649597656222095,
          "delta_dti": 0.0022328706345736415,
          "candidate_wins": true
        },
        {
          "fold": "SE",
          "candidate_dti": 0.179904216311661,
          "baseline_dti": 0.17584968609584054,
          "delta_dti": 0.004054530215820473,
          "candidate_wins": true
        }
      ]
    }
  },
  "recorded_point_best_comparison": {
    "recorded_best_lane": "H24-DPRF1",
    "recorded_best_dti": 0.1637924246971501,
    "recorded_best_source": "evidence/dprf1_run_card_20261026.json",
    "candidate_point_delta": 0.0057115438663869755,
    "candidate_beats_recorded_point": true,
    "arm2_replay_dti": 0.1637924246971501,
    "arm2_replay_bit_identical_to_recorded": true,
    "scope": "Recorded point comparison; the paired Arm1-vs-Arm2 bootstrap is the same-session replay comparison."
  },
  "paired_vs_baseline": {
    "ci95": [
      0.0013610518073050484,
      0.010033729621204543
    ],
    "delta_dti": 0.0057115438663869755,
    "baseline_name": "DRAIN5 Arm2 noDrain 52ch replay (DPRF1 configuration, in-session)",
    "baseline_dti": 0.1637924246971501
  },
  "baseline_reproduced": true,
  "paired_vs_current_best": {
    "baseline_dti": 0.1637924246971501,
    "evaluator_version": "gems-segment-pooled-v1",
    "n_withheld_positive_pixels": 60988,
    "baseline_replayed": true,
    "ci95": [
      0.0013610518073050484,
      0.010033729621204543
    ],
    "baseline_identity": "Arm2 in-session replay of the DPRF1 configuration (bit-identical pooled DTI to recorded DPRF1)"
  },
  "leakage_canary": {
    "passed": true,
    "n_features_checked": 59,
    "worst_feature": "gvc_elev_local_resid",
    "worst_pooled_auc": 0.38886309340749736,
    "worst_polarity_extremity": 0.6111369065925026,
    "drainage_channel_pooled_aucs": {
      "drn_log_accum": 0.49410203065279573,
      "drn_ksn": 0.6059191579973169,
      "drn_knick": 0.5066886611866251,
      "drn_knick_lineament": 0.5911611583073886,
      "drn_chan_dist": 0.5353673763510265,
      "drn_hand": 0.5073475085111498,
      "drn_bend": 0.4849072813045789
    },
    "oof_surface_auc": 0.6940300851747792
  },
  "drainage_diagnostics": {
    "valid_dem_cells": 5164312,
    "footprint_cells": 5167373,
    "sink_cells": 1727,
    "sink_fraction_of_valid": 0.0003344104693906952,
    "channel_cells_accum_ge_100": 395567,
    "accum_max_cells": 145429.0,
    "accum_median_cells": 8.0,
    "channel_finite_fraction_on_footprint": {
      "drn_log_accum": 0.9994076293698946,
      "drn_ksn": 0.9994076293698946,
      "drn_knick": 0.2818886888947246,
      "drn_knick_lineament": 0.9994076293698946,
      "drn_chan_dist": 0.9994076293698946,
      "drn_hand": 0.9994076293698946,
      "drn_bend": 0.2809853285218621
    },
    "labels_read": false,
    "channels": [
      "drn_log_accum",
      "drn_ksn",
      "drn_knick",
      "drn_knick_lineament",
      "drn_chan_dist",
      "drn_hand",
      "drn_bend"
    ],
    "regime_b_gate_names": [
      "drn_knick",
      "drn_knick_lineament",
      "drn_ksn"
    ],
    "inputs": [
      "det_elev"
    ],
    "routing": "D8 steepest descent (drop/distance), first-max tie-break, fixed neighbour order",
    "depression_policy": "no pit filling; Gaussian sigma=2 px smoothing; sinks terminate accumulation (endorheic)",
    "smooth_sigma_px": 2.0,
    "theta_ref": 0.45,
    "channel_min_accum_cells": 100.0,
    "knick_gate_accum_cells": 20.0
  },
  "correlation_overlap_vs_registry": {
    "total_registry_entries_checked": 61,
    "competing_method_rasters_checked": 60,
    "calibration_control_rasters_checked": 1,
    "peer_blobs_checked": 83,
    "peer_blobs_missing_from_cache": 0,
    "pre_placement_surface_max_abs_rank_correlation": 0.5370661066370517,
    "pre_placement_peers_max_abs_rank_correlation": 0.17938743250638262,
    "method_lane_passed": false,
    "method_lane_max_abs_rank_correlation": 0.7019156718307827,
    "method_lane_max_dot_overlap": 0.8354756466776438,
    "dot_overlap_within_3px_vs_dprf1": 0.8354756466776438,
    "peer_blobs_passed": true,
    "peer_blobs_max_dot_overlap": 0.5517342115047538,
    "peer_blobs_max_overlap_artifact": "GEMSDOE30:docs/downloads/gemsdoe30-sgmc-hedge-d10-85k-20261003-ac08b41e-zeros.tif",
    "literal_all_entries_passed": false,
    "literal_all_entries_max_dot_overlap": 0.9955648802252085,
    "calibration_control_rows": [
      {
        "registry_id": "registry-039",
        "file": "inputs/calibration/13gems_20261001_r13-lattice-s5_v2_nan-outside.tif",
        "footprint_sha256": "15bc7e7d4e21d284c42e4183bb7c63d087f67635818bd7b963d58f6beed44817",
        "raw_spearman": 0.0002542876077393035,
        "kernel_spearman": -0.000633768794586568,
        "candidate_dot_overlap_within_3px": 0.9955648802252085,
        "duplicate": true,
        "entry_role": "synthetic_spacing5_calibration_lattice"
      }
    ],
    "top_5_competing_comparators": [
      {
        "registry_id": "local-dprf1",
        "file": "docs/downloads/gems24-dprf1-stitched-oof-tworegime-20261026-81849d67c8bf-zeros.tif",
        "footprint_sha256": "788d0a645db0a8c0440cfcb907e940a14193158cbddd8daeb7d5c01521c1a425",
        "raw_spearman": 0.1268834227078601,
        "kernel_spearman": 0.7019156718307827,
        "candidate_dot_overlap_within_3px": 0.8354756466776438,
        "duplicate": true,
        "entry_role": "competing_method_lane"
      },
      {
        "registry_id": "local-eul1",
        "file": "docs/downloads/gems24-eul1-negative-euler-contact-20261026-eda170f04847-zeros.tif",
        "footprint_sha256": "27bcea204fac9ad9d8208f8b77b86bde62cf2c66405783ca91519f6d46e65e19",
        "raw_spearman": 0.12616950930181334,
        "kernel_spearman": 0.6911410048449719,
        "candidate_dot_overlap_within_3px": 0.8286503425930845,
        "duplicate": true,
        "entry_role": "competing_method_lane"
      },
      {
        "registry_id": "registry-045",
        "file": "inputs/gems16-h16-1-topo-geophys-baseline-ridges-20260930-df20f65e-nan.tif",
        "footprint_sha256": "38e2d5ed08c80c0dee29f61026692cd5c7ea4c22bf54a03381741fa6e13dbeba",
        "raw_spearman": 0.18001640137606498,
        "kernel_spearman": 0.364579472297829,
        "candidate_dot_overlap_within_3px": 0.574201944016572,
        "duplicate": false,
        "entry_role": "competing_method_lane"
      },
      {
        "registry_id": "registry-046",
        "file": "inputs/gems19-h19-4-multiline-corroborated-openness-thermal-pop-20260930-691e4dfa-allfinite.tif",
        "footprint_sha256": "8e8bdb2b746ee4c1acabff93d50d7095c06ed7c0ba7ae51b7d77036a5fa62784",
        "raw_spearman": 0.18036004499245348,
        "kernel_spearman": 0.3640558398789093,
        "candidate_dot_overlap_within_3px": 0.5650926860360121,
        "duplicate": false,
        "entry_role": "competing_method_lane"
      },
      {
        "registry_id": "registry-040",
        "file": "inputs/calibration/8GEMSDOE_Hedge-v2_submission.tif",
        "footprint_sha256": "79ddbc65bf4c3d5233a61a5cf44f5838f219fbf1bcd38238f23d88f3bec0e0ca",
        "raw_spearman": 0.15670092118144738,
        "kernel_spearman": 0.2218160032390502,
        "candidate_dot_overlap_within_3px": 0.5617729856057789,
        "duplicate": false,
        "entry_role": "competing_method_lane"
      }
    ]
  },
  "novelty": {
    "surface": {
      "max_abs_rank_correlation": 0.5370661066370517,
      "literal_all_entries_passed": true
    },
    "final_dots": {
      "max_abs_rank_correlation": 0.7019156718307827,
      "method_lane_max_dot_overlap": 0.8354756466776438,
      "method_lane_passed": false,
      "literal_all_entries_passed": false,
      "literal_duplicate_rows": [
        {
          "registry_id": "registry-039",
          "file": "inputs/calibration/13gems_20261001_r13-lattice-s5_v2_nan-outside.tif",
          "footprint_sha256": "15bc7e7d4e21d284c42e4183bb7c63d087f67635818bd7b963d58f6beed44817",
          "raw_spearman": 0.0002542876077393035,
          "kernel_spearman": -0.000633768794586568,
          "candidate_dot_overlap_within_3px": 0.9955648802252085,
          "duplicate": true,
          "entry_role": "synthetic_spacing5_calibration_lattice"
        },
        {
          "registry_id": "local-dprf1",
          "file": "docs/downloads/gems24-dprf1-stitched-oof-tworegime-20261026-81849d67c8bf-zeros.tif",
          "footprint_sha256": "788d0a645db0a8c0440cfcb907e940a14193158cbddd8daeb7d5c01521c1a425",
          "raw_spearman": 0.1268834227078601,
          "kernel_spearman": 0.7019156718307827,
          "candidate_dot_overlap_within_3px": 0.8354756466776438,
          "duplicate": true,
          "entry_role": "competing_method_lane"
        },
        {
          "registry_id": "local-eul1",
          "file": "docs/downloads/gems24-eul1-negative-euler-contact-20261026-eda170f04847-zeros.tif",
          "footprint_sha256": "27bcea204fac9ad9d8208f8b77b86bde62cf2c66405783ca91519f6d46e65e19",
          "raw_spearman": 0.12616950930181334,
          "kernel_spearman": 0.6911410048449719,
          "candidate_dot_overlap_within_3px": 0.8286503425930845,
          "duplicate": true,
          "entry_role": "competing_method_lane"
        }
      ]
    },
    "peers_final": {
      "max_dot_overlap_within_3px": 0.5517342115047538,
      "passed": true
    }
  },
  "off_catalogue_distance_profile": {
    "n_dots": 37654,
    "min_dist_px": 2.23606797749979,
    "median_dist_px": 21.213203435596427,
    "frac_le_2px": 0.0,
    "frac_2_to_5px": 0.16109842247835554,
    "frac_5_to_9px": 0.06474743719126785,
    "frac_2_to_9px_apron": 0.22584585966962342,
    "frac_9_to_20px": 0.25253625112869815,
    "frac_gt_20px_farfield": 0.5216178892016784
  },
  "off_catalogue_distance_profile_before_apron_debiasing": {
    "n_dots": 37654,
    "min_dist_px": 2.23606797749979,
    "median_dist_px": 17.0,
    "frac_le_2px": 0.0,
    "frac_2_to_5px": 0.22074679980878525,
    "frac_5_to_9px": 0.11850002655760344,
    "frac_2_to_9px_apron": 0.3392468263663887,
    "frac_9_to_20px": 0.20967227917352738,
    "frac_gt_20px_farfield": 0.4510808944600839
  },
  "exact_file_nuisance_audit": {
    "method": "Classifier two-sample test (Lopez-Paz & Oquab, ICLR 2017) with 10 km block label swaps",
    "labels_audited_first": true,
    "nuisance_families_only": [
      "block_1",
      "block_2",
      "block_3",
      "block_4",
      "claim_m",
      "road_m"
    ],
    "block_boundary_status": "derived_audited_not_official_coordinates",
    "labels_first": {
      "observed_auc": 0.5040084703386403,
      "fold_aucs": [
        0.5090975159687721,
        0.5246382471655577,
        0.502744437201213,
        0.479553681019018
      ],
      "null_p95": 0.5263710840715217,
      "margin_vs_p95": -0.022362613732881398,
      "raw_p_value": 0.43,
      "holm_p_value": 0.43
    },
    "candidate": {
      "file": "gems24-drain5-negative-drainage-knickpoint-20261026-ff95d6fb3205-zeros.tif",
      "sha256": "4b171e8d92d49a595684b58d188fe4117b653ec9cda8263919c25802d6539e32",
      "positive_pixels": 37654,
      "observed_auc": 0.5267903556669913,
      "fold_aucs": [
        0.4779582401246606,
        0.5968842378400698,
        0.5332809820745373,
        0.4990379626286976
      ],
      "null_p95": 0.520697459950348,
      "margin_vs_p95": 0.006092895716643287,
      "raw_p_value": 0.05,
      "holm_p_value": 0.1,
      "strict_gate_flagged": false,
      "strict_gate_passed": true
    }
  },
  "c2st_exact_file": {
    "labels_audited_first": true,
    "strict_gate_passed": true,
    "observed_auc": 0.5267903556669913,
    "holm_p_value": 0.1
  },
  "technical_gates": {
    "format_and_strict_0_1_range_passed": true,
    "leakage_canary_59ch_passed": true,
    "holdout_beats_recorded_dprf1_point_best": true,
    "paired_vs_nodrain_replay_ci95_gt_0": true,
    "competing_method_novelty_passed": false,
    "peer_blobs_novelty_passed": true,
    "exact_file_c2st_nuisance_passed": true,
    "stitched_oof_apron_debiasing_verified": true
  },
  "technical_promotion_gates_passed": false,
  "raster_sha256": "4b171e8d92d49a595684b58d188fe4117b653ec9cda8263919c25802d6539e32",
  "nan_outside_artifact": "gems24-drain5-negative-drainage-knickpoint-20261026-ff95d6fb3205-nan.tif",
  "nan_outside_sha256": "035fda761b6d9b2ede5424556ef1443627229fed4bc2080de164bc590e214a2b",
  "zip_artifact": "gems24-drain5-negative-drainage-knickpoint-20261026-ff95d6fb3205-zeros.zip",
  "zip_sha256": "c8070dee317bea29a32fd7663aae5f7d842701bfb64e51755083439d7a20ae90",
  "validator_output": {
    "sha256": "4b171e8d92d49a595684b58d188fe4117b653ec9cda8263919c25802d6539e32",
    "format_valid": true,
    "format_acceptable": true,
    "strict_whole_array_values_in_0_1": true,
    "no_nan_in_footprint": true,
    "footprint_range_0_1": true,
    "crs": "EPSG:32611",
    "shape": [
      3730,
      3292
    ],
    "positive_pixels": 37654
  },
  "submission_name": "gems24-drain5-negative-drainage-knickpoint-20261026-ff95d6fb3205-zeros.tif",
  "note": "GEMS24 DRAIN5 | D8 drainage knickpoint 59ch stitched-OOF | id ff95d6fb3205 | HOLDOUT-DTI 0.16950 | research; selector gated",
  "note_length": 123,
  "verdict": "negative",
  "ok_to_download": true,
  "ok_to_submit": false,
  "submission_authorized": false,
  "submission_slots_used": 0,
  "organizer_confirmed_score": null,
  "governance_hold_reasons": [
    "Parallel-Run Protocol Rule 6: promotion to a real weekly slot is a separate selector step",
    "gems-selector-v2 is negative-only: literal registry-039 spacing-5 lattice retained, live DrivenData quota unknown, independent positive replay certificate not implemented",
    "HOLDOUT-DTI is a local hide-and-recover measurement, not a leaderboard score or forecast"
  ],
  "selector_receipt": {
    "selector_version": "gems-selector-v2-literal-quota-fail-closed",
    "decided_utc": "2026-10-26T16:46:36.518409+00:00",
    "artifact": "gems24-drain5-negative-drainage-knickpoint-20261026-ff95d6fb3205-zeros.tif",
    "artifact_sha256": "4b171e8d92d49a595684b58d188fe4117b653ec9cda8263919c25802d6539e32",
    "human_inspection_used": false,
    "gates": {
      "artifact_hash_matches_run_card": true,
      "artifact_name_matches_run_card": true,
      "g1_format_strict_0_1": true,
      "g2_leakage_canary": true,
      "g3_holdout_beats_recorded_best_and_paired_baseline": true,
      "g4_registry_novelty": false,
      "g5_exact_file_c2st": true,
      "note_at_most_140_chars": true,
      "budget_and_no_slot_spent": true,
      "current_account_quota_independently_verified": false,
      "complete_independent_replay_certificate": false
    },
    "all_gates_passed": false,
    "ok_to_submit": false,
    "decision": "DO_NOT_SUBMIT",
    "quota_status": "unknown_BLOCKED_no_manual_confirmation_exception",
    "recorded_scientific_screen_passed": false,
    "current_point_best_source": "evidence/dprf1_run_card_20261026.json",
    "reasons": [
      "g4_registry_novelty: surface|rho|=0.5370661066370517, final|rho|=0.7019156718307827, method overlap=0.8354756466776438, peer overlap=0.5517342115047538",
      "current_account_quota_independently_verified: unknown; no quota verifier/receipt adapter implemented; no human-confirmation exception",
      "complete_independent_replay_certificate: not implemented; recorded flags and numeric summaries are screening evidence, not an independent promotion certificate"
    ],
    "scope": "Recorded-evidence screening and exact-file validation only; positive authorization is not implemented. Not an organizer score, quota record or acceptance guarantee. The agent never uploads."
  }
}
```
