# H24-PAIR1 Findings & Nine-Site Executive Summary — 2026-10-26 (this session)

## 0. The obvious answer first

**Download (research):** `docs/downloads/gems24-pair1-graben-dipole-oof-20261026-842a5212d85c-zeros.tif`
SHA-256 `ecf16ef684ce2823e2888c101bd0b47d0661e7dacbba8bb6915db118925d0f93` · 37,654 dots · strict whole-array [0,1] PASS (0 NaN).
**Submit: NO.** PAIR1 is a clean negative (below). **The single best unscored unique
candidate in this repo remains DPRF1** (`gems24-dprf1-stitched-oof-tworegime-20261026-81849d67c8bf-zeros.tif`,
recorded HOLDOUT-DTI 0.16379 [0.15045, 0.17739]) — also **DOWNLOAD YES / SUBMIT NO**
under `gems-selector-v2-literal-quota-fail-closed` (literal lattice, unknown live
quota, no independent replay certificate). No file anywhere in the nine focus sites
is honestly labelable `OK_TO_SUBMIT` today. Any page that says otherwise is guessing
about hidden labels and quota it cannot see.

### Required executive table — file to download, estimated score, uniqueness

Score labels follow Protocol Rule 3. "Estimate" = HOLDOUT-DTI only. There is **no
defensible leaderboard projection**: holdout truth is the *public catalogue*
(~60,988 px), hidden truth is sparse *new* faults; the repo's own calibration
(h25→h28) had the wrong sign, and the one holdout→live pair on record here
(GVC1 0.14876 → owner-reported live 0.0859, ratio 0.58) is a single confounded
point. Publishing a numeric live forecast would be a hallucination.

| # | File to download | Estimated score (labelled) | Unique vs all other focus-site submissions? | OK to submit? |
|---|---|---|---|---|
| 1 | `gems24-dprf1-stitched-oof-tworegime-20261026-81849d67c8bf-zeros.tif` (GEMSDOE24, recorded) | **HOLDOUT-DTI 0.16379** [0.15045, 0.17739], `gems-segment-pooled-v1`, 60,988 withheld. Not replayable here (needs gitignored 419 MB training raster). | **Method-unique YES** (57/57 competing rasters ≤55.8% 3-px overlap, recorded); **literal NO** (99.56% vs synthetic spacing-5 lattice). Not a duplicate of any scored file. | **NO** — selector v2 `DO_NOT_SUBMIT` (quota/replay/lattice). If a human overrides governance, this is the only evidence-supported file. |
| 2 | `gems24-pair1-graben-dipole-oof-20261026-842a5212d85c-zeros.tif` (**new this session**) | **HOLDOUT-DTI 0.12711** [0.11533, 0.14079], same evaluator/count. Paired Δ vs own BASE −0.00147 [−0.00353, +0.00069], 0/4 folds. | **YES** — fresh this session: max 3-px overlap 0.4490, max \|ρ\| 0.1471 across 48 locally available registry rasters (lattice 0.994 reported separately). Shares 0 copied pixels with any prior file. | **NO** — negative result, worse than BASE and DPRF1. Research only. Do not retune. |
| 3 | All historical winners (H33-B2 0.2778, PINN 0.2750, H36-1 0.2710, H27-4 0.2708, H33D 0.2632, D2.8 0.2600, D28 0.2600, D1.5 0.2477, topo-gap 0.2449) | **OWNER-REPORTED / UNVERIFIED** live values from the brief; zero artifact-linked organizer receipts exist in this repo. | **NO** — one ancestry (H19-5 → D2.8 → B2/PINN/H33D subsets & supersets, pixel-verified in prior sessions). Resubmitting any of them re-measures a known number and wastes a weekly slot. | **NO — DO NOT COPY / DO NOT RESUBMIT.** |

### Per-site verdict (focus nine)

| Site | Best historical (OWNER-REPORTED, unverified) | Best unscored unique candidate | Verdict |
|---|---|---|---|
| GEMSDOE24 | h25-1-dotted-h19-5-d1-5 · 0.2477 | **DPRF1** (HOLDOUT-DTI 0.16379) → then PAIR1 (0.12711, negative) | DPRF1 only candidate; SUBMIT NO (selector) |
| GEMSDOE25 | dotted-h19-5-d2-8 · 0.2600 | none better (H66-MGD scored 0.0742) | DO NOT RESUBMIT |
| GEMSDOE27 | topo-gap-closure-t-v2 · 0.2449 | H29-CELF already scored 0.2190 (best scored unique method) | DO NOT RESUBMIT (already scored) |
| GEMSDOE28 | h36-1-rung30-blind-r1 · 0.2710 | none (S18-MXTP 0.0217) | DO NOT SUBMIT |
| GEMSDOE30 | d28-poisson300m-offcat · 0.2600 (= D2.8) | none (MSDB1 0.1462) | DO NOT RESUBMIT |
| GEMSDOE31 | h27-4-solo-d28 · 0.2708 | HVDC (sibling holdout 0.1247, not harmonized) | SIBLING RESEARCH ONLY |
| GEMSDOE32 | **h33-h33-2-b2 · 0.2778** (highest listed) | none — B2 prohibited to copy | DO NOT COPY |
| GEMSDOE33 | h33d-analog-tip-stepover · 0.2632 | none (holdout FAIL) | DO NOT SUBMIT |
| GEMSDOE36 | anderson-geothermal-pinn · 0.2750 (= B2 + 1,200 dots) | none | DO NOT SUBMIT |

## 1. Why did GEMSDOE32 H33-B2 (0.2778, owner-reported) top the list? (PhD-level answer)

Full derivation: `knowledge/22_phd_analysis_GEMSDOE32_and_9site_2026-10-26.md`.
Verified ancestry (pixel forensics, prior sessions): H19-5 surface (121,131 px) →
Poisson thinning D1.5 (60,069) → D2.8 (44,090) → **B2 = D2.8 minus every dot within
2 px (200 m) of the public catalogue (37,654; zero dots added)**. B2 introduced **no
new geology**. Its gain is metric geometry: with DTI = TPw/(TPw + 0.2·FPw + 0.8·FNw)
and triangular credit K(d)=max(0,1−d/300 m), a dot 100–200 m from a *mapped* fault
earns FP mass whenever it misses hidden truth, while the chance a mappable fault
was missed *that close* to a mapped one is low. Deleting those dots improves DTI
iff t·(0.2F₀+0.8N) < 0.2T₀·f — plausibly satisfied in the ≤200 m apron. Differences
B2 vs PINN (+0.0028), vs H36-1 (+0.0068), vs H27-4 (+0.0070) are within plausible
noise; with no hidden labels and no organizer receipts, causality is untestable.
**Can we beat 0.2778?** Unknown and unforecastable from local data. The only
evidence-based path: (a) keep >200 m clearance + 300 m Poisson geometry, (b) use a
stitched-OOF surface (never in-sample — GVC1's collapse to 0.0859 is the warning),
(c) push far-field (>20 px) allocation toward the footprint share. DPRF1 already
implements (a)–(c) with the best local holdout; authorizing it through the separate
selector step and obtaining one ORGANIZER-CONFIRMED receipt would calibrate
everything after it. The brief's two "current top" claims (0.3195 vs 0.4413)
conflict; neither is verified here.

## 2. Five candidate hypotheses generated this session (ranked; top one executed)

| Rank | Hypothesis | Layers / transform | Why it could catch catalogue-missing faults | Mimic | Status |
|---|---|---|---|---|---|
| 1 | **H24-PAIR1 graben pairing** (EXECUTED) | lidar upface/downface/lapneg/lappos/coh100: two-sided min-pairing + crest→base dipole | Paired graben scarps under alluvium; catalogue biased to single range fronts | Terraces, levees, road cuts, Lahontan ridges | **NEGATIVE** (§3) |
| 2 | Radiometric front phase-lag | ext ThK/UTh/UK + rad K/Th/U: signed spatial offset between mobile-U and immobile-Th fronts | Fracture-hosted U displacement off a lithologic front under thin cover | Downslope transport, weathering | Feasible with cache; queued, not run (budget) |
| 3 | SGMC gap completion | `derived_sgmc_faults_100m_u8.tif` distance + gap bridging | State-map faults absent from QFaults catalogue | Map generalization error | Weak prior (GEMSDOE16 h18-4 live 0.0360) |
| 4 | Drainage-offset graph | DEM thalweg azimuth offsets across catchments | Buried transverse faults offset washes coherently | Stream capture, strandlines | **Not viable here**: needs DEM stack absent in checkout (USGS 3DEP https://www.usgs.gov/3d-elevation-program — unreachable from sandbox allowlist) |
| 5 | Magnetic worm persistence | TMI multi-scale upward continuation | Deep basement steps persist with height; shallow volcanics decay | Dike swarms | **Not viable here**: cache holds only TMI_up150 quantized; raw RTP/TMI grids are in GeoDAWN archives not present (DOI 10.5066/P93LGLVQ) |

## 3. PAIR1 result (3 preregistered experiments, all reported)

- Exp 1 BASE (22 cached channels): HOLDOUT-DTI **0.12858** [0.11702, 0.14206] —
  replicates recorded `oof_multiphysics_hgb_d3` 0.13000 within feature-stack
  difference, confirming evaluator identity in this checkout.
- Exp 2 PAIR1 (+4 operators): **0.12711** [0.11533, 0.14079]; paired Δ **−0.00147**
  [−0.00353, +0.00069], **0/4 folds**. The pairing operators add no hide-and-recover
  skill at 100 m aggregate scale (pair_same canary AUC 0.580 — real but redundant
  with up/downface already in the tree).
- Exp 3 clearance 3 px: **identical** (0.12711) — zero fold dots fell in
  2 < d_visible ≤ 3 px; ablation non-discriminating (disclosed, budget spent).
- Canaries: 26/26 PASS (worst two-polarity AUC 0.588, rad_K ≤ 0.90). Novelty:
  max overlap 0.4490 / |ρ| 0.1471 vs 48 competing rasters → genuinely unique lane.
  Format: strict [0,1] PASS, CRS/shape/transform exact. Verdict **negative**;
  **do not retune PAIR1** (offsets, weights, seed, budget are frozen by preregistration).

## 4. The "[0,1]" portal error — root cause and fix (verified line by line)

The official sample itself contains NaN outside the footprint (7,111,787 cells).
A strict whole-array checker `((a>=0)&(a<=1)).all()` fails on *any* NaN — that is
the reproduced failure mode (`gems.submission.check_variants`,
`variant_strict_whole_array_no_nan_allowed`). Fix, already applied to every
`-zeros.tif` in `docs/downloads/`: outside-footprint = 0.0, single-band float32,
no nodata-NaN. Independently re-verified this session on the PAIR1 file:
`((a>=0)&(a<=1)).all() == True`, 0 NaN/Inf in all 12,279,160 cells. **Always upload
the `-zeros.tif` (or its single-TIFF `.zip`), never the `-nan.tif` twin, to a strict
checker.** How to submit (when/if a future selector authorizes): DrivenData
competition page → Submit → file = `-zeros.tif`/`.zip` → paste the packet's ≤140-char
note (PAIR1's, for format reference only: `GEMS24 PAIR1 | graben pair+dipole 26ch OOF | id 842a5212d85c | HOLDOUT-DTI 0.12711 | research; DO NOT SUBMIT`)
→ verify SHA-256 against the run card → keep the submission-page receipt before
calling any score ORGANIZER-CONFIRMED. This project never automates DrivenData.

## 5. Limitations & next steps (ordered)

1. Restore the 419 MB competition training raster (owner-authenticated download) —
   without it DPRF1-class 52-channel lanes cannot be replayed or beaten fairly here.
2. Resolve governance blockers prospectively: lattice-control policy, machine-verifiable
   weekly-quota evidence, independent replay certificate. No human-inspector override.
3. Next viable lane from §2: radiometric front phase-lag (cache-ready), preregistered,
   must beat BASE 0.12858 paired-CI>0 *and* approach DPRF1 0.16379 to matter.
4. Obtain one ORGANIZER-CONFIRMED receipt (DPRF1 via selector step) to calibrate
   holdout→live transfer; until then all live numbers stay OWNER-REPORTED.

Official sources: competition https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/ ·
reference solution https://github.com/drivendataorg/gems-prize-reference-solution ·
USGS GeoDAWN https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and (DOI 10.5066/P93LGLVQ) ·
INGENIOUS https://gdr.openei.org/submissions/1391 · https://gbcge.org/current-projects/ingenious/ ·
EPSG:32611 https://epsg.io/32611 · Tversky https://en.wikipedia.org/wiki/Tversky_index ·
rules https://docs.nlr.gov/docs/fy26osti/96647.pdf
