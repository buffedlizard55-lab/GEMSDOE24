# Repository review & submission decision — 2026-10-26 follow-up

## Executive decision

**No new submission is validated or authorized. Do not submit any file from this review.** The downloadable [DPRF1 GeoTIFF](downloads/gems24-dprf1-stitched-oof-tworegime-20261026-81849d67c8bf-zeros.tif) is a previously generated research artifact, not a new candidate and not an approval to submit. Its recorded local result is **HOLDOUT-DTI 0.16379** (95% CI **[0.15045, 0.17739]**; evaluator `gems-segment-pooled-v1`; **60,988 withheld positive pixels**). The recorded packet was checked without rerunning the experiment. Its literal 3-pixel overlap with the retained synthetic calibration lattice is **99.56%**, above the prescribed 70% limit; the selector remains `DO_NOT_SUBMIT`. The result is not an estimate of the hidden leaderboard score.

The requested nine-site values are historical owner reports, not organizer receipts. No estimate of a future competition score can be justified from these reports or the available hidden labels. The historical artifact listed for each site is therefore a reference identity only—not a recommendation to download, copy, or resubmit it.

| Site | Highest listed historical artifact | Reported value (provenance) | Unique / allowed for a new submission? | Current decision |
|---|---|---:|---|---|
| [GEMSDOE24](https://buffedlizard55-lab.github.io/GEMSDOE24/) | `h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan` | 0.2477 — OWNER-REPORTED, unverified | No; historical dotted H19 lineage | No recommended historical file |
| [GEMSDOE25](https://buffedlizard55-lab.github.io/GEMSDOE25/) | `dotted-h19-5-d2-8-20261002-e56ea318af89-nan` | 0.2600 — OWNER-REPORTED, unverified | No; its 44,090-dot geometry is also reported for GEMSDOE30 D2.8 | No recommended historical file |
| [GEMSDOE27](https://buffedlizard55-lab.github.io/GEMSDOE27/) | `topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan` | 0.2449 — OWNER-REPORTED, unverified | Not certified unique against every current site artifact | No recommended historical file |
| [GEMSDOE28](https://buffedlizard55-lab.github.io/GEMSDOE28/) | `h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan` | 0.2710 — OWNER-REPORTED, unverified | No; documented as H27-4 geometry plus 501 relay-rung dots | No recommended historical file |
| [GEMSDOE30](https://buffedlizard55-lab.github.io/GEMSDOE30/) | `d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca` | 0.2600 — OWNER-REPORTED, unverified | No; documented as pixel-identical in-footprint to GEMSDOE25 D2.8 | No recommended historical file |
| [GEMSDOE31](https://buffedlizard55-lab.github.io/GEMSDOE31/docs/) | `h27-4-solo-d28-20261004-8acb75e1-nan` | 0.2708 — OWNER-REPORTED, unverified | No; documented as D2.8 with near-catalogue dots removed | No recommended historical file |
| [GEMSDOE32](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html) | `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` | 0.2778 — OWNER-REPORTED, unverified | **No; prohibited to copy.** Documented as D2.8 minus 6,436 dots, adding no detections | Historical benchmark only; no recommended file |
| [GEMSDOE33](https://buffedlizard55-lab.github.io/GEMSDOE33/) | `h33d-analog-tip-stepover-r30-20261004-cb490425926e` | 0.2632 — OWNER-REPORTED, unverified | No; documented as H33-B2 plus analog dots | No recommended historical file |
| [GEMSDOE36](https://buffedlizard55-lab.github.io/GEMSDOE36/docs/) | `anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros` | 0.2750 — OWNER-REPORTED, unverified | No; documented as H33-B2 plus 1,200 PINN dots | No recommended historical file |

**Score interpretation:** the table preserves the owner-provided leaderboard claims and lineage evidence already recorded in this repository. No submission-page receipts are present, so none is `ORGANIZER-CONFIRMED`. In particular, the claims about the current leaderboard (0.3195 and 0.4413) conflict and were not verified here. The reported 0.2778 does not establish why H33-B2 scored as it did or predict a higher score. Catalogue-flank pruning is a plausible metric/emission explanation, not causal proof without the hidden truth.

## Prospective hypothesis ranking (not executed)

Relative rank is a research-priority judgment, not a numeric DTI forecast. Each candidate would need a preregistration, feature-alone two-polarity leakage canary, complete segment-buffer holdout, and pre-placement/final-dot uniqueness audit before any selection. The named process in the final column is a non-fault mimic.

| Rank | Layers and target signature | Why it could recover an unmapped fault | Difference from tested repo work | Expected benefit / cost / named mimic |
|---|---|---|---|---|
| 1 | LiDAR `upface_max`, `downface_max`, `strike`, `coh100`, `relief`; object-level paired, opposite-facing scarp strips with persistent width and aligned ends | A subtle buried graben can preserve paired low-relief margins where the fault catalog's mapped bedrock scarps are absent | Tests connected paired-object topology, not SAHG1 pointwise scarp/conduit fusion or OJ1 orientation junctions | Relative priority: highest of these ideas; magnitude unknown; medium cost. Mimic: fluvial terrace risers or irrigation banks. |
| 2 | DEM elevation/slope and a D8 drainage graph; detect offset channel continuations and bearing changes across valleys | Small displacement may redirect channels without preserving a crisp surface scarp | Graph connectivity and cross-valley controls, rather than the repo's local curvature/saddle or lineament features | Potentially useful but uncertain; high cost. Mimic: stream capture or lithologic control. Finer DEM would require USGS 3DEP, [official data tools](https://www.usgs.gov/3d-elevation-program/data-tools); availability was not checked from this restricted environment. |
| 3 | GeoDAWN K, Th, and U numerical channels; multi-scale signed spatial phase lag between parallel K-rank and Th/U-rank fronts | Differential mobility/alteration could offset a fracture-related alteration halo from a lithologic front beneath thin cover | Spatial offset across scales, rather than CRP1's compositional gradients; related enough to CRP1 that strict novelty review is required | Low-to-medium expected potential; medium cost. Mimic: slope-driven sediment transport or weathering. |
| 4 | GeoDAWN gravity/geophysical channels plus DEM slope; curvature of a gravity/basement boundary gated to low-relief cover | A buried range-front structure may remain visible geophysically while its scarp is obscured | Boundary curvature rather than EUL1's Euler contact solutions; overlap risk remains because both use potential-field data | Low-to-medium potential; low-to-medium cost. Mimic: an unfaulted pluton margin. |
| 5 | INGENIOUS deformation/seismic channels; normalized shear-to-dilatation contrast with multi-scale persistence | Distributed strike-slip deformation may be expressed in deformation proxies where mapped surface traces are incomplete | A new fixed physical partition only if it differs from TRSG1's seismic/geophysical fusion; substantial overlap risk | Uncertain and lower priority; high cost. Mimic: mining blasts or non-tectonic ground motion. |

### Top-candidate validation status and strict novelty correction

At the start of this follow-up, no single lane paragraph was available in the working checkout, so this review itself ran no experiment. A concurrent update to `main` subsequently supplied a preregistration and executed the exact top-ranked paired-scarp/dipole hypothesis as H24-PAIR1. This is a separate locked lane and is recorded in [`knowledge/25_preregistered_PAIR1_2026-10-26.md`](../knowledge/25_preregistered_PAIR1_2026-10-26.md), [`knowledge/26_PAIR1_findings_and_9site_executive_2026-10-26.md`](../knowledge/26_PAIR1_findings_and_9site_executive_2026-10-26.md), and [`evidence/pair1_run_card_20261026.json`](../evidence/pair1_run_card_20261026.json). No slot was used.

PAIR1 is **HOLDOUT-DTI 0.12711**, 95% CI **[0.11533, 0.14079]**, evaluator `gems-segment-pooled-v1`, **60,988 withheld positives**. Its paired difference from its own BASE is **HOLDOUT-DTI Δ −0.00147**, 95% CI **[−0.00353, +0.00069]**, with **0/4 folds won**; it did not beat even that matched BASE, much less the recorded DPRF1 point-best. No leaderboard score is estimated.

**Critical protocol correction:** PAIR1's run card reports method-only overlap 0.4490 across 48 competing rasters, but separately reports **0.994 final-dot overlap within 3 px of registry-039's lattice**. The owner's literal Rule 1 applies to *any* registry raster. Therefore the correct status under this request is **STRICT NOVELTY FAIL / duplicate / STOP**, regardless of 0 copied pixels or a method-only pass. A report that excludes the lattice from the limit is not compliant with the stated protocol. PAIR1 remains download-for-research only, **SUBMIT NO**, and must not be retuned.

The first-session absence of `data/prepared/` prevented this follow-up from independently replaying existing full-stack training. PAIR1 used its separately documented committed uint8 physical/LiDAR bands and is independently recorded in its own run card; its result is a negative deliverable, not an approval. Restore the gitignored 419 MB competition `training_features.tif` only if an assigned future lane requires it. Do not weaken the lattice control or use a submission slot until every literal uniqueness, leakage, comparable-holdout, quota, and independent replay requirement is met.

## Three-pass repository review

1. **Pass 1 — requirements and evidence:** read `AGENTS.md`, the preserved owner brief, current README decision, existing 9-site summaries, recent run cards and review notes. Confirmed that the full prompt is already preserved near the end of `README.md`; it should be maintained rather than duplicated. Identified the exact distinction between OWNER-REPORTED scores, HOLDOUT-DTI and organizer receipts.
2. **Pass 2 — implementation and edge-case review:** installed the pinned dev dependencies in ignored `.venv`. Initial full pytest run gave 367 passes and 2 failures because this workspace was a shallow clone missing historical commits required by source-provenance tests. Ran `git fetch --unshallow origin main` (no checkout/branch change), then reran: **369 passed**. This was a missing-history environment issue, not a failing test assertion against current implementation.
3. **Pass 3 — final verification:** after merging concurrent main updates, the full suite passed (**392 tests**, including regressions that require PAIR1's literal lattice-overlap failure to remain visible and the rebuildable site to link its negative result); `ruff check`, `ruff format --check`, `compileall`, and `git diff --check` passed. The recorded DPRF1 verifier returned `verified: true`, `experiment_rerun: false`, `verdict: negative`, and `ok_to_submit: false`. No score, raster, peer-source audit, or website deployment was independently regenerated by this review.

### Irregularities and limitations

- The exact historical submission artifacts are not all present in this repository as download files; the table records their identities, not live download links. Historical names and reported values are user-/owner-supplied context.
- No future leaderboard score can be honestly estimated from HOLDOUT-DTI alone. The only current measurable comparator cited here is a local recorded holdout, not a competition score.
- The local DPRF1 strict-format checks and method-only novelty results do not cancel its literal calibration-lattice overlap, unknown live quota, or missing independent positive replay certificate.
- VENT's archived run card and corresponding novelty/C2ST claims are quarantined because the historical runner used dummy fallback values. Do not interpret its old numerical/gate fields as trusted measurements pending an independent replay.
- DrivenData submission access/quota and the current official leaderboard were not checked. Official source links below are supplied for review, not represented as freshly retrieved.
- Current source refs have changed since historical pins; freshness is not proof that all changed artifacts were re-audited.

## Official/source links for verification

- [DrivenData competition overview/rules](https://www.drivendata.org/competitions/306/competition-doe-gems/)
- [DrivenData problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [DrivenData about](https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/)
- [DrivenData leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)
- [DrivenData reference solution](https://github.com/drivendataorg/gems-prize-reference-solution)
- [USGS GeoDAWN data release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
- [OpenEI GDR INGENIOUS submission](https://gdr.openei.org/submissions/1391)
- [USGS 3DEP tools](https://www.usgs.gov/3d-elevation-program/data-tools)

## Machine-readable review card

See [`evidence/repo_review_run_card_20261026.json`](../evidence/repo_review_run_card_20261026.json). Its null holdout fields mean **no new experiment was run**; the recorded DPRF1 comparison is separately labeled as an existing HOLDOUT-DTI result.
