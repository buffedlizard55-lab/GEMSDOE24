# H24-CGMK1 findings + nine-site executive summary — 2026-10-27 (arena/5ef84d43)

**Maximize P(Win) · Own the Outcome.**

## Decision first (obvious, automated, no human inspector)

| Question | Answer |
|---|---|
| Was a **new, unique TIFF generated** this session? | **YES** — `gems24-cgmk1-negative-signed-gravmag-condk-20261027T173413Z-62ca1c4977c5-zeros.tif`, SHA-256 `3258f3290390b92470e0eb9d92886f0ab1289df1abe46397fcfaf08f56b43070`, 37,654 binary dots, zero pixels copied from any previous submission. |
| OK to **download** it? | **YES (research/audit)** — one click from the [executive subpage](../docs/executive-summary-20261027-cgmk1.html) or [direct file](../docs/downloads/gems24-cgmk1-negative-signed-gravmag-condk-20261027T173413Z-62ca1c4977c5-zeros.tif). |
| OK to **submit** it? | **NO — DO NOT SUBMIT.** It fails the preregistered holdout floor by a wide margin. Spending a weekly slot on it would *lower* P(Win). |
| Is **any** file from the nine focus sites OK to submit today? | **NO.** Every row in the nine-site table below is `DO_NOT_SUBMIT` (details and per-site reasons in the table). There is no organizer-confirmed score for any file in this repository. |
| Slots spent this session | **0.** Experiments spent: 2 of the ≤3 preregistered budget (EXP-1 primary, EXP-2 control). Runtime 320 s. |

Suggested 108-char note, recorded for the artifact (not an instruction to upload):
`GEMS24 CGMK1 | signed grav-mag reversal + cond-K front, geophys-only | id 62ca1c4977c5 | not yet live-scored`

## What was run (preregistered before any result)

Preregistration [`32_preregistered_CGMK1_2026-10-27.md`](32_preregistered_CGMK1_2026-10-27.md)
(commits `9b280a3`, amendment `8dafdc5`; implementation `e8361d6`) ranks five
hypotheses — signed gravity–magnetic reversal + conditional-K (chosen, all inputs
cached), signed terrain-flexure dipole, OPERA DISP-S1 InSAR, Sentinel-2 SWIR,
USArray MT — and marks the last three **not viable in this sandbox** because
outbound egress is limited to GitHub/npm/PyPI, so NASA Earthdata/ASF, Copernicus
and IRIS EMC downloads cannot be obtained or verified here. Flagged irregularities
(no assigned lane paragraph; conflicting 0.4413/0.3195 leader claims; lattice
pigeonhole; unproven portal-error cause; band-6 provenance) are in the preregistration.

**Method (single lane).** Supervised HGB (recorded baseline-D3 hyperparameters, untuned)
on 37 channels: 16 raw magnetic/gravity/AEM/strain/seismic bands + `log(deq/ieq)`,
8 GeoDAWN radiometric ordinals, **8 new signed cross-gradient channels**
(sin/cos of the `rtp`–`iso_grav_anom` inter-field gradient angle, |∇sin| reversal,
log gradient-energy product; σ ∈ {1, 2.5} px), **4 new conditional-K channels**
(fold-fit OLS `K ~ Th + U + Th·U` residual, its gradient at two scales, gated front).
Excluded by design: the whole `det_elev` DEM trunk, all LiDAR, band-6 `tc`, all
catalogue-distance features. Shared tools only: `SegmentHoldout(buffer_px=15)`,
pooled DTI (α=0.2, β=0.8, 300 m triangular kernel), `priority_poisson`
(min-distance 3 px, >2 px catalogue clearance), `submission.write_submission`,
`novelty.compare_registry`. Training mirror restored and hash-verified
(SHA-256 `4371c82e…3bc5`); a matching hash proves integrity, **not** organizer provenance.

### Results — HOLDOUT-DTI (`gems-segment-pooled-v1`, 60,988 withheld positives)

| Arm | HOLDOUT-DTI | 95% CI | Folds NW / NE / SW / SE |
|---|---|---|---|
| **EXP-1 CGMK1 (37 ch, primary)** | **0.08868** | [0.07565, 0.10234] | 0.08756 / 0.13848 / 0.06415 / 0.07975 |
| EXP-2 matched control (25 ch, no new channels) | 0.08589 | [0.07276, 0.10016] | — |
| Selection floor (pre-run, `benchmarks.selection_floor`) | 0.17010 (KPL-36, unreplayed) | [0.15509, 0.18614] | — |
| Recorded local point-best (S3DEP1, not replayed here) | 0.16606 | [0.15186, 0.18034] | — |

Paired EXP-1 − EXP-2 = **+0.00279**, 95% CI **[−0.00222, +0.00768]** (spans zero), 3/4 folds
positive (SE −0.00456). The new operators neither demonstrably help nor hurt on this
holdout. Pooled EXP-1 components: TPw 5,049.54, FPw 35,716.26, FNw 55,938.46, emitted 38,104;
independently rescored from the saved fold dots with `metric.dti_score_fast` — identical to the
recorded value to full printed precision.

**Canary (leakage).** All 37 channels pass the two-polarity AUC ≤ 0.90 rule; worst is
`rad_K` (pooled AUC 0.4118, extremity 0.5882). New channels are individually weak on withheld
catalogue faults: cg_sin 0.5045/0.5035, cg_cos 0.5179/0.5185, cg_rev 0.4856/0.4834,
cg_magprod 0.5320/0.5343, kres 0.4331, kres_grad 0.4902/0.4869, kfront 0.4900. OOF surface
AUC 0.5804 (pass). Note `kres` AUC < 0.5: withheld faults sit on *lower* conditional-K
residuals than background — the opposite polarity to a naive K-enrichment story.

**Novelty (final dots, 39 locally present registry entries; scope limit below).**
Pre-placement surface max |Spearman ρ| = 0.2258; final max |ρ| (raw+kernel) = 0.3842 —
both ≤ 0.90 against every entry. Max directed 3-px overlap vs any *competing method* =
**62.05%** (the dense 161k-pixel GEMSDOE10 ctx-ridge reference, whose own density inflates
directed coverage); vs the modern trunk lanes it is 25.9% (DPRF1), 25.5% (S3DEP1),
25.7% (DKRN1), 24.7% (XVAR1) — the trunk exclusion demonstrably breaks the 71–87%
convergence that stopped those lanes. Literal all-entry result including the spacing-5
calibration lattice: overlap 100.00%, **FAIL**, with a pigeonhole minimum of 82.34% for any
37,654-dot in-footprint set (lattice covers 5,160,724 of 5,167,373 footprint pixels within
3 px; its Spearman ρ vs this candidate is −0.0003, i.e. overlap is coverage geometry, not
similarity). **Scope limit:** pinned cross-repo registry rasters under `data/research/`
are not present in this sandbox checkout, so full-registry novelty against every historical
peer TIFF is *not* established by this session — only the 39 local entries were compared.

**Format (the reported "[0, 1]" portal error).** The zeros-outside variant passes every
hard check: single-band float32, EPSG:32611, shape 3730×3292, template geotransform
`(100, 0, 243350, 0, −100, 4508550)`, zero NaN/Inf in the 5,167,373-px footprint, values
exactly {0, 1}, strict whole-array `((a>=0)&(a<=1)).all()` PASS, 37,654 in-footprint dots,
0 on catalogue, minimum catalogue distance 2.236 px. The ZIP contains exactly that TIFF
(SHA-verified). A NaN-outside twin is included for compatibility only. Which convention the
portal accepts is still **unproven** — the official text/sample use NaN outside, a strict
whole-array validator rejects NaN anywhere; interior out-of-range values are a third
possible cause of the historical error. Format PASS is necessary, never sufficient.

**Leaderboard figure: MODEL PROJECTION — NOT A SCORE.** Under the repository's lattice-calibrated
first-order model (`emission.model_dti`, holdout coverage 0.0828, τ = 0.0024445, φ swept 0–0.10,
τ swept ±20%), CGMK1 projects to **0.0530–0.0655** (central 0.0599 at τ×1.0, φ=0.05). The same
arithmetic projects the recorded holdout-best S3DEP1 to ≈0.112 and GVC1 (holdout 0.1488) to
≈0.100, while GVC1's owner-reported leaderboard value is 0.0859 — i.e. the projection is a
sensitivity device, not a forecast; hidden faults are unlikely to be credited like withheld
catalogue faults. No file here has an ORGANIZER-CONFIRMED score.

### Scientific interpretation (what the negative result actually measures)

Removing the DEM topography trunk drops catalogue hide-and-recover from ~0.16 to 0.089 while
cutting dot-overlap with trunk lanes from 71–87% to ~26%. That is quantitative evidence that
the segment holdout is dominated by **same-modality rediscovery**: the public catalogue was
largely mapped from topographic/lidar expression, so a holdout that hides catalogue segments
rewards detectors that read topography the same way, whether or not that is the modality in
which *unmapped* (hidden-label) faults express themselves. This does **not** license the
inverse claim that a weak-holdout geophysics detector will score well on hidden labels —
CGMK1's dots still cluster near the catalogue (19.4% within 3 px, 44.5% at 3–10 px, only
4.2% beyond 3 km) because the supervised target *is* the catalogue. Both statements are
bounded: holdout rank and hidden-fault rank can differ, and without artifact-linked
organizer receipts we have no calibrated bridge between them.

## Why did GEMSDOE32 B2 report 0.2778 — and can anything here beat it?

**Verified ancestry (computed masks, not narrative).**
`evidence/portfolio_artifact_audit_20261026.json#h33_ancestry` recomputed exact masks:
GEMSDOE25 D2.8 = GEMSDOE30 D2.8 (44,090 dots); B2 (37,654) equals D2.8 restricted to
distance-to-catalogue > 2 px — **6,436 dots removed, 0 added**. The same B2 also equals the
GEMSDOE28/31 H27-family mask (40,199) under the same >2 px rule (2,545 removed, 0 added), and
is a pure subset of the GEMSDOE36 mask (38,854; 1,200 removed, 0 added). B2 is therefore not a
new detector; it is one emission rule applied to converging H19-5 derivatives. Its reported
score (0.2778, `UNVERIFIED-OWNER-REPORT` — no artifact-linked receipt exists in any repo we
can inspect) and its parents' reported scores (D2.8 0.2600) differ by **+0.0178 from deletion alone**.

**Mechanism, in the metric's own algebra.** DTI = T/(0.2·T + 0.2·F + 0.8·G) with a 300 m
triangular kernel (α=0.2 FP weight, β=0.8 FN weight). Organizer staff clarification (linked in
`knowledge/31_…`): catalogue pixels are masked pixel-exactly, but new truth may lie within
300 m of a known trace, so near-catalogue "halo" dots at 1–2 px are **not** free — they pay
FP mass ≈ (1 − kernel proximity to the nearest hidden truth pixel) each. Deleting a set of
dots with lost credit `t` and removed FP mass `f` improves DTI iff
`t·(0.2F + 0.8G) < 0.2·T·f`. Two independent calibrations say the halo is exactly the
low-`t` population: (i) the blind spacing-5 lattice's reported 0.0904 implies hidden truth
G ≈ 12,632 px equivalent (τ = 0.244%), so at N ≈ 38–44k dots the FP term is the same order
as β·G and deleting ~6.4k near-zero-credit dots removes ~11% of the denominator;
(ii) the natural experiment on one surface (GEMSDOE10 solid ridge 161,366 px → 0.1280 vs
dotted 65,236 px → 0.1839) shows kernel-credit retention ≈ 0.80 at 0.40× the pixels —
sparse emission is a first-order lever in the sparse-truth regime. Feeding the repository's
own `emission.extrapolate_variant` the reported D2.8 → B2 change (τ as above, φ ∈ {0, .05, .1}):
the reported +0.0178 is quantitatively consistent **only with credit retention ≈ 0.999–1.002**
(break-even retention 0.934; retention 0.95 would predict ≈0.264, not 0.2778). In words:
*if* the reported pair is correctly attributed, the 6,436 halo dots earned essentially no
hidden-truth credit. That is a statement about emission geometry and the hidden label set's
relationship to mapped traces — plausibly, mappers already captured the surface trace, so
the 0–200 m halo of a known fault is rarely where a *new* fault pixel sits — not evidence
for any geothermal mechanism, and not a causal proof: hidden T/F/G per dot are unobservable,
the scores are owner-reported, and a dot can credit multiple truth pixels (`t` is not a
Bernoulli rate).

**Can a submission scoring above 0.2778 be generated from what is here?** Not honestly, today.
The principled route the evidence supports is: a surface at least as strong as the recorded
holdout leaders, emitted with sparse-truth-optimal geometry (kernel-cover thinning, halo
clearance, budget set by the marginal-credit rule `ΔTPw/ΔN > 0.2·D` rather than by holdout
recall). Three blockers prevent claiming or responsibly spending a slot on that route from
this session: (1) this session's unique surface is holdout-weak (0.0887 ≪ 0.1701 floor);
(2) the literal 70% novelty rule is unsatisfiable at the standard budget while the
space-filling lattice is a comparator, and this session may not self-exempt it;
(3) there is no artifact-linked organizer receipt calibrating holdout or model projections
to the leaderboard — the one paired point with a nominally same-evaluator holdout (GVC1
0.1488 → owner-reported 0.0859) moves *down*, so leaderboard rank cannot be inferred.
The conflicting 0.4413 / 0.3195 "leaderboard high" claims are both unverified; neither is
used as a target anywhere in this analysis.

## Nine-site executive table

Full machine-readable version: [`evidence/nine_site_executive_summary_cgmk1_20261027.json`](../evidence/nine_site_executive_summary_cgmk1_20261027.json)
(assembled programmatically by `scripts/build_cgmk1_ninesite.py` from the pinned
2026-10-27 nine-file audit and recorded run cards — no hand-copied numbers).
"Historical best" = highest owner-listed name per site, **UNVERIFIED-OWNER-REPORT**.
"Source-featured holdout" = the file pinned in the 2026-10-27 audit (different evaluators
per site — do not rank across rows). Leaderboard estimate is **none defensible** for every
row (no organizer receipt); the only numeric projections in this project are labelled model
projections, not scores.

| Site | Historical best (unverified) | Source-featured holdout evidence | Unique under literal rule? | Submit? |
|---|---|---|---|---|
| GEMSDOE24 | dotted h19-5 d1.5 — 0.2477 | H-UNIQUE-07: **INVALID** (full-catalogue support leaked into folds); local records: S3DEP1 HOLDOUT-DTI 0.16606, CGMK1 0.08868 (this session) | No (lattice ≥99.78%; CGMK1 passes competing-method test only) | **NO** |
| GEMSDOE25 | dotted h19-5 d2.8 — 0.2600 | H74: 0.03906 [0.02608, 0.04889], own evaluator, 25,308 withheld | No (100.00%) | **NO** |
| GEMSDOE27 | topo-gap-closure d1.5 — 0.2449 | H31: 0.04730 [0.04453, 0.04962], own evaluator, denominator disagreement unresolved | No (99.61%) | **NO** |
| GEMSDOE28 | h36-1 rung30 — 0.2710 | S22C: 0.12018 [0.10471, 0.13649], unbuffered protocol | No (99.62%) | **NO** |
| GEMSDOE30 | d28 poisson 44090 — 0.2600 | CSR-1: 0.15816 [0.14499, 0.17147], own evaluator, 60,988 | No (99.99%) | **NO** |
| GEMSDOE31 | h27-4 solo d28 — 0.2708 | H31-YM: 0.15496 [0.14011, 0.17012], own evaluator, 60,988 | No (99.05%) | **NO** |
| GEMSDOE32 | **h33-2 B2 — 0.2778** (highest focus claim) | H47: 0.11977 [0.10573, 0.13290], own evaluator, 22,232 | No (99.61%) | **NO** |
| GEMSDOE33 | h33d tip-stepover — 0.2632 | FSML2: 0.10308 [0.09414, 0.11294], `gems-segment-pooled-v1`, 60,988 | No (100.00%) | **NO** |
| GEMSDOE36 | anderson PINN — 0.2750 | KPL-36: 0.17010 [0.15509, 0.18614], `gems-segment-pooled-v1`, 60,988 (unreplayed here) | No (99.17%) | **NO** |

**Which single file is "best"?** By evidence class, not by unverified claims:
(1) highest *historical owner claim* = GEMSDOE32 B2 0.2778 (a deletion-only derivative —
resubmitting it or a near-copy is exactly what the uniqueness rules forbid);
(2) highest *recorded same-evaluator holdout point* = KPL-36 0.17010 (external record,
unreplayed; its file fails the literal lattice gate), then local S3DEP1 0.16606 (also
`DO_NOT_SUBMIT` on other gates);
(3) this session's *new unique* file = CGMK1 (competing-method novelty PASS, format PASS,
holdout FAIL). None is OK to submit. The "download this" research file on the site's first
screen remains clearly labelled `DO NOT SUBMIT`.

## How a submission will be made when (and only when) a file is promoted

1. Confirm the run card verdict is `promote` from a *separate selector step* and the weekly
   account allowance on the competition site (rules mention three per week; staff say the
   website limit prevails — actual remaining allowance was **not** checked by this project).
2. Download the `-zeros.tif` (or its single-TIFF `.zip`) from this repository's
   `docs/downloads/`; verify its SHA-256 against the run card before uploading anything.
3. On DrivenData competition 306 → *New submission*: choose the `.tif` (or `.zip` containing
   exactly that one TIFF). It must be single-band float32, EPSG:32611, with the submission
   format's shape and geotransform — all machine-checked by `submission.check_variants`.
4. Paste the run card's ≤140-character note into the **Note** field.
5. If the portal returns “Predicted values must be in range [0, 1]”, do **not** silently
   clamp or rescale: re-run `submission.check_variants`, confirm you picked the zeros
   variant (strict whole-array [0,1] PASS), and record the rejection with the file hash.
6. Record the artifact-linked receipt (file SHA-256 + displayed score) via
   `scripts/record_live_score.py`. Only that receipt can create an ORGANIZER-CONFIRMED score.

For CGMK1 specifically: **stop at step 0 — it is not promoted.**

## Limitations, irregularities carried forward, and next steps

- **No lane was assigned** in the prompt; CGMK1 is a disclosed self-assignment (collision
  risk with parallel sessions remains). Protocol items 2–6 were otherwise followed:
  shared tools fixed/used centrally, every number labelled, canaries before modelling,
  ≤3 experiments (2 used), zero slots, run card issued.
- Novelty scope is 39 **locally present** entries; the pinned cross-repo priority registry
  rasters (`data/research/…`) are absent in this sandbox, so "unique vs every peer file ever
  published" is **not** established. The competing-method pass and the literal lattice fail
  are both reported; resolving the lattice-comparator policy is a coordinator decision,
  not something to engineer around by deleting entries or moving dots.
- The training mirror is owner-supplied and hash-verified only; if it differs from organizer
  data, all local holdouts inherit that risk. Band-6 `tc` was excluded; GeoDAWN bytes are
  percentile ranks, so conditional-K results are ordinal, not concentration statements.
- Sandbox limits that blocked data work: no DrivenData authentication (competition files
  cannot be auto-downloaded), egress restricted to GitHub/npm/PyPI (NASA/Copernicus/IRIS
  layers for hypotheses 3–5 unobtainable here), 2 CPU / 3.8 GiB RAM (sufficient for this lane).
- **Do not retune CGMK1.** Next work, in order of P(Win) per slot:
  1. Obtain **one artifact-linked organizer receipt** for any already-submitted file and
     record it — without a single calibrated holdout↔leaderboard pair, every "estimate" is theatre.
  2. Coordinator decision on the lattice comparator class (method raster vs calibration
     control) so the novelty rule is satisfiable as written; until then every 37,654-dot
     file is `DO_NOT_SUBMIT` by construction.
  3. Fresh preregistration (new lane, not a CGMK1 tweak): test whether the CGMK1 channels
     add anything **on top of** the trunk with a pre-placement novelty pre-check that is
     expected to fail on overlap — or, better, run one of hypotheses 3–5 from an environment
     where the official OPERA/Sentinel-2/MT downloads are actually obtainable and checkable.
  4. Analysis-only: quantify emission budgets under sparse-truth reweighting of the existing
     holdout components (no new dots, no slot) to align the internal objective with the
     sparse-hidden-truth regime the lattice calibration implies.

## Parallel-session integration (PRs #67/#68, merged same day)

While this lane ran, two parallel sessions merged a pre-training uniqueness-feasibility
gate (`scripts/check_uniqueness_feasibility.py`, `gems.novelty.dot_budget_feasibility`,
`docs/feasibility-review-20261027.md`, `docs/protocol-feasibility-20261027.md`). Their
checker independently reproduces this document's lattice arithmetic exactly: 6,649
uncovered pixels, minimum overlap 0.8234184947 at 37,654 dots, maximum budget not ruled
out 22,163, exit 2 `STOP_IMPOSSIBLE_BUDGET` for the CGMK1 budget (verified locally after
the merge). Their review lists the signed gravity–magnetic reversal and conditional-K
residual as ranked-but-untested candidates #1/#2; CGMK1 is the same-day preregistered
execution of that combination, and its negative result above is now the measured answer
for the geophysics-only form. Neither workstream changes the other's verdict; the merge
kept both intact, and the post-merge suite is 521 passed.

## Three passes (this session)

1. **Implement + verify.** Restored hash-pinned data, preregistered, implemented
   `src/gems/cgmk1.py` + `scripts/run_cgmk1_lane.py`, ran EXP-1/EXP-2, wrote TIFF pair +
   ZIP + checks + run card.
2. **Bug/edge review.** Synthetic tests pinned the signed-angle operators; ruff caught a
   real closure-`del` hazard in the memmap writer (fixed pre-run); independent rescore of
   saved fold dots reproduced both pooled DTIs exactly; read-back verified SHA/CRS/shape/
   range/dot-count/catalogue-distance and ZIP byte-identity; benchmarks module re-read the
   new run card without lowering the floor.
3. **Request re-check.** Every number labelled HOLDOUT-DTI / UNVERIFIED-OWNER-REPORT /
   MODEL PROJECTION; uniqueness reported both ways; download-vs-submit made explicit on the
   README, AGENTS, and a new executive subpage; full test suite, site build and preview
   checked (receipts in the session PR).

## Sources (official, for manual review)

DrivenData competition 306 overview/metric: https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/ ·
about/resources: https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/ ·
rules PDF (NLR 96647): https://docs.nlr.gov/docs/fy26osti/96647.pdf ·
reference solution: https://github.com/drivendataorg/gems-prize-reference-solution ·
USGS GeoDAWN (DOI 10.5066/P93LGLVQ): https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and ·
GDR INGENIOUS #1391: https://gdr.openei.org/submissions/1391 ·
INGENIOUS project: https://gbcge.org/current-projects/ingenious/ ·
EPSG:32611: https://epsg.io/32611 ·
Tversky index: https://en.wikipedia.org/wiki/Tversky_index ·
staff clarifications linked in [`31_current_integrity_review_2026-10-27.md`](31_current_integrity_review_2026-10-27.md).
No DrivenData page was accessed by this session (egress allowlist; repository policy).
