# Repository review — 2026-10-28 (Arena branch `arena/c81bb5d5-gemsdoe24`)

## Decision

**No new TIFF, geological experiment, score projection, or competition-slot use. Do not submit any file on the basis of this review.** The requested outcome—a new, unique, high-scoring submission—is not achieved. The parallel-run protocol refers to one assigned method paragraph, but no method paragraph is present in the active brief. Inventing a lane or selecting a candidate from an old research queue would violate the protocol. The repository's frozen feasibility check also shows that the usual 37,654-dot budget cannot satisfy the literal `>70%` 3-pixel overlap stop against the retained lattice control. Neither the rule nor a stopped lane was changed.

There is **no defensible leaderboard score estimate** for a new TIFF. The earlier source-featured nine-site table remains at [`docs/executive-summary.html#current-focus-files`](executive-summary.html#current-focus-files); its files are pinned to 2026-10-27 refs. The merged `main` also adds a separate readback of the nine exact owner-named historical champions at [`docs/historical-champions.html`](historical-champions.html), with a [machine-readable receipt](data/historical_champions_20261028.json). This later readback used immutable historical commits, not the latest heads; the GitHub freshness feed reports all nine focus repositories changed after its portfolio pins. Neither table is a current-head exhaustive artifact audit, organizer receipt, or submission approval. Treat the downloads as research/audit files only.

## Review scope and checks performed

This review was performed in three passes. No downloaded competition data, external layer or site content was treated as independently verified merely because a local copy or historical receipt exists.

| Check | Result |
| --- | --- |
| Branch and initial worktree | `arena/c81bb5d5-gemsdoe24`; clean at start; HEAD `fdd41b0` (the checked-out main snapshot). |
| History needed by tests | Initial clone was shallow. `git fetch --unshallow origin` completed; this made the full-history tests runnable. |
| Pinned project environment | Created ignored `.venv/` and installed `.[dev]` from the repository's pinned `pyproject.toml`; no tracked dependency files changed. |
| Full automated suite | `.venv/bin/python -m pytest -q` after integrating the merged-main additions and formatting their two unformatted files: **564 passed** (final run; see below). |
| Lint and format | `.venv/bin/ruff check .`: passed. `.venv/bin/ruff format --check .`: 318 files already formatted after normalizing two newly merged files. |
| Syntax / patch hygiene | `python -m compileall -q src scripts`, `node --check docs/assets/app.js`, and `git diff --check`: passed. |
| Frozen-count check | `python scripts/check_protocol_feasibility.py --dots 37654`: necessary lower bound 82.341849%; `submission_authorized: false`. This is arithmetic on a frozen audit, not a fresh raster audit. |
| Raster-backed feasibility check | `python scripts/check_uniqueness_feasibility.py --dot-budget 37654 --dot-budget 44090`: re-opened its pinned template and lattice witness; respectively 82.341849% and 84.919483% minimum overlap; expected exit 2. It produced no candidate surface, dots, TIFF or score. |
| Historical champion artifact review | The merged-main [receipt](data/historical_champions_20261028.json) reports nine immutable-commit files read back at 2026-10-28T16:12Z, all local-format-valid but all above 99.90% lattice overlap; GEMSDOE25/30 are exact in-footprint aliases. This continuation reviewed that receipt/table; it did not re-download them. |
| Focus-source freshness | The GitHub-only feed stamped 2026-10-28T16:07:47Z says all nine main refs changed since earlier pins. It is not a latest-head artifact or score audit. |
| Data required for a new holdout | `data/training_features.tif` and a prepared feature cache are absent in this checkout. The checked-in bridge rasters and external audit layers do not substitute for the full training stack. |
| Current organizer state | No DrivenData leaderboard, submission portal, receipt or account quota was checked. No organizer-confirmed score was obtained. |

The `82.341849%`/`84.919483%` values are **necessary lower bounds against one retained witness**, not actual candidate overlaps, not a full registry census, not proof of copying, and not HOLDOUT-DTI. The corresponding tool result explicitly leaves both pre-placement correlation and final-dot checks `NOT RUN` because no candidate was created.

## Nine-site executive summary: historical champions, not submit recommendations

The merged-main report [`docs/historical-champions.html`](historical-champions.html) and its [hash-bound JSON](data/historical_champions_20261028.json) are the best available exact-file summary for the nine historical champions named in the request. The report read back nine artifacts at immutable GitHub commits on 2026-10-28; it is scoped to those nine named artifacts, not latest heads or every file in the nine repositories. The independent, older `current_focus_nine_file_audit_20261027.json` concerns source-featured research artifacts and must not be confused with the champion files below.

All nine champion rasters pass the local single-band/grid/in-footprint range validator, but all fail the literal 3-pixel lattice overlap rule. These overlap percentages are geometry, **not scores**. The report records no organizer-confirmed scores, no leaderboard estimates, and no local holdout for these historical files. It also finds GEMSDOE25 and GEMSDOE30 are exact in-footprint aliases despite different file bytes.

| Site | Exact historical champion download | Owner-reported claim (unverified) | Leaderboard estimate | 3-px lattice overlap / uniqueness | In-footprint alias | Decision |
| --- | --- | ---: | --- | ---: | --- | --- |
| GEMSDOE24 | [`gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-allfinite.tif`](https://github.com/buffedlizard55-lab/GEMSDOE24/raw/07345ea0604953d7efb858d9cfbc21e20c7aca0b/docs/downloads/gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-allfinite.tif) | 0.2477 | **NOT ESTIMABLE** | 99.9218% / FAIL | None among these nine | Research download; submit NO |
| GEMSDOE25 | [`gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-zeros.tif`](https://github.com/buffedlizard55-lab/GEMSDOE25/raw/04333cc3fbf7486c56e0324fd07aee684be614dc/docs/downloads/gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-zeros.tif) | 0.2600 | **NOT ESTIMABLE** | 99.9161% / FAIL | GEMSDOE30 | Research download; submit NO |
| GEMSDOE27 | [`gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-allfinite.tif`](https://github.com/buffedlizard55-lab/GEMSDOE27/raw/b8dd298e10884afffa05436673ac73aeaf850b8c/docs/downloads/gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-allfinite.tif) | 0.2449 | **NOT ESTIMABLE** | 99.9234% / FAIL | None among these nine | Research download; submit NO |
| GEMSDOE28 | [`gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-allfinite.tif`](https://github.com/buffedlizard55-lab/GEMSDOE28/raw/78e724f95337a6528b1248be5c113c6d6d502891/docs/downloads/gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-allfinite.tif) | 0.2710 | **NOT ESTIMABLE** | 99.9097% / FAIL | None among these nine | Research download; submit NO |
| GEMSDOE30 | [`gemsdoe30-d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca.tif`](https://github.com/buffedlizard55-lab/GEMSDOE30/raw/3d5bec2af5f29291617f97c9e2dfe443be6f55c3/docs/downloads/gemsdoe30-d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca.tif) | 0.2600 | **NOT ESTIMABLE** | 99.9161% / FAIL | GEMSDOE25 | Research download; submit NO |
| GEMSDOE31 | [`gemsdoe31-h27-4-solo-d28-20261004-8acb75e1-allfinite.tif`](https://github.com/buffedlizard55-lab/GEMSDOE31/raw/cf13282fcd86290f1539f0a86446c8ba7205a79b/docs/downloads/gemsdoe31-h27-4-solo-d28-20261004-8acb75e1-allfinite.tif) | 0.2708 | **NOT ESTIMABLE** | 99.9179% / FAIL | None among these nine | Research download; submit NO |
| GEMSDOE32 | [`gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif`](https://github.com/buffedlizard55-lab/GEMSDOE32/raw/012e17b2a115c3c0d5e7885bea625bf9657c99fc/docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif) | **0.2778 — highest claim in this nine-site set** | **NOT ESTIMABLE** | 99.9150% / FAIL | None among these nine | Benchmark only; research download; submit NO |
| GEMSDOE33 | [`GEMSDOE33-h33d-analog-tip-stepover-r30-20261004-cb490425926e.tif`](https://github.com/buffedlizard55-lab/GEMSDOE33/raw/f52533110fe62cd03e77f1228e9e5ecac412c463/docs/downloads/GEMSDOE33-h33d-analog-tip-stepover-r30-20261004-cb490425926e.tif) | 0.2632 | **NOT ESTIMABLE** | 99.9140% / FAIL | None among these nine | Research download; submit NO |
| GEMSDOE36 | [`gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif`](https://github.com/buffedlizard55-lab/GEMSDOE36/raw/c9ad59ec6f969ed931d089a03044c1567a633e84/docs/downloads/gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif) | 0.2750 | **NOT ESTIMABLE** | 99.9176% / FAIL | None among these nine | Research download; submit NO |

**Clear action:** H33-B2 is the highest owner-reported historical claim in these nine sites, but it is neither organizer-confirmed nor unique under the specified registry test. It is **not OK to submit**. The linked TIFFs are downloadable for research only. Do not submit any row from this table. The exact downloaded file hashes and all format checks are in the machine-readable receipt. The source-featured newer research artifacts and their recorded holdouts are reported separately on the [older executive page](executive-summary.html#current-focus-files); those holdouts are not measurements of these historical champions and must not be mixed into this table.

### What the H33-B2 `0.2778` does and does not establish

The score is **owner-reported / unverified** in the supplied record; this checkout contains no artifact-linked organizer submission receipt for it. The [prior hash-bound geometry replay](../evidence/oj1_priority_ancestry_replay.json) records that H33-B2's 37,654-dot mask is a subset of the 44,090-dot D2.8 emission after removing 6,436 public-catalogue-proximal dots, with no new dots added; that replay also records a relationship to a separate GEMSDOE31 parent. This establishes emission-mask ancestry, not a causal relationship to hidden faults.

A plausible metric mechanism is reduction of false-positive mass: with hidden truth mass `G`, weighted true-positive credit `T`, and false-positive mass `F`, the project metric is `T / (0.2*T + 0.2*F + 0.8*G)`. Deleting dots can improve the ratio if false-positive savings outweigh lost true credit; the exact condition and limitations are reviewed in [`docs/metric-integrity-20261026.md`](metric-integrity-20261026.md). Here the hidden `T`, `F`, `G` and deletion losses/savings are unavailable, and a dot may contribute credit to multiple nearby truth pixels. So pruning is a scientifically plausible explanation, **not an identified cause**. The score cannot tell us how much of the reported difference is true-positive retention, false-positive reduction, split/evaluator differences, or reporting error. Do not copy H33-B2 or call 0.2778 an estimate for a new submission.

The prompt also cites `0.3195` and `0.4413` leaderboard snapshots. They conflict with the other supplied figures and are not authenticated by a current official leaderboard receipt in this review. They remain **unverified claims**, not a current leaderboard baseline. The recorded local S3DEP1 point (`HOLDOUT-DTI 0.166060`, `gems-segment-pooled-v1`, 60,988 withheld, 95% CI [0.151858, 0.180339]) is also not an organizer score; its existing selector verdict is negative.

## Geological ideas: ranked only, not assigned, not validated, not claimed globally novel

Three candidate concepts already appear in the current integrity review. They are reproduced as a *research queue*, not promoted as “untried”: the merged-main review records that open PR #70 overlaps the signed gravity–magnetic and conditional-potassium concepts, and no global search can certify novelty. The flexure-pair concept remains a proposal, not an assigned lane. The separate ASTER mineral-transition idea is not listed as viable: exact official product coverage, obtainability and utility were not established. The required paragraph is absent, the prepared stack is missing, and the 37,654-dot budget has a decisive necessary-condition failure. Therefore no candidate can be responsibly selected for the requested holdout in this pass. No expected DTI gain is stated.

| Rank | Layers and physical signature | Why a missing fault might be exposed; distinction from methods already reviewed | Named non-fault mimic | Qualitative value / cost; availability status |
| --- | --- | --- | --- | --- |
| 1 | Cached magnetic `rtp`, gravity `iso_grav_anom`, and `det_elev`; smooth at preregistered scales and test a **signed gravity–magnetic cross-gradient orientation reversal** along an independently derived terrain-line tangent | A concealed splay may perturb relative field orientation without a mapped surface scarp. Differs from the reviewed unsigned topo–magnetic cross-gradient (TMCG) and magnitude/co-alignment methods. | Intrusive contacts, remanent magnetization, or survey seams | Highest qualitative information-per-cost; medium CPU/memory; DTI unknown. The complete cached feature stack is absent here, so feasibility is not established. Source catalogues: [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and). Specific data availability/coverage for a new run was not rechecked. |
| 2 | Cached GeoDAWN K/Th/U byte channels; fold-training-only conditional K-rank residual and cross-normal residual front, gated on low Th/U-rank change | Hydrothermal alteration across a concealed branch could depart from parent-lithology trends. Differs from fixed contrasts/rank fronts by conditioning potassium rank on thorium/uranium ranks within training folds. | Arkosic sorting, moisture, or weathering/lithology boundaries | Second; medium cost; DTI unknown. Required cached channels are not present as a complete ready feature stack in this checkout. Data catalogue: [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and); new acquisition availability not verified. |
| 3 | Cached `det_elev`, `det_local_relief`, `depth_to_base_surf`, `geod_dilaterate`, and `geod_shearrate`; detect separated, opposite-signed terrain-flexure curvature lobes over a basement-depth step | Broad bending may preserve structural evidence where a crisp scarp is absent. Differs from pointwise Hessian curvature (RSHG1) and conductivity saddle (CON). | Erosional terrace/valley pairs, dunes, or alluvial-fan curvature | Third; medium cost; DTI unknown. Required prepared layers are absent here. The public [OpenEI GDR INGENIOUS submission #1391](https://gdr.openei.org/submissions/1391) is a catalogue pointer, not proof that any particular product is downloadable, suitable, licensed for this use, or covers the target. |

No external dataset is proposed as a currently viable dependency: the exact resource, obtainability, coverage and license would have to be checked before a lane is preregistered. This follows the request's source-verification requirement without treating a catalogue page as a successful download. The competition's [official rules](https://docs.nlr.gov/docs/fy26osti/96647.pdf), [problem page](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/), [reference solution](https://github.com/drivendataorg/gems-prize-reference-solution), and [EPSG:32611 definition](https://epsg.io/32611) are retained for manual review. No DrivenData page was accessed for this review.

## Bugs, irregularities and next actions

1. **README maintenance:** it is very long and accumulates superseded session reports. This note and the linked active brief should be the entry point; historical records should be archived in a separate maintenance change rather than silently edited.
2. **Stale site snapshot:** the nine-site artifact audit is pinned to 2026-10-27 refs. Do not say its file selection, exact artifact, score or uniqueness result is current on 2026-10-28 without refreshing and verifying each source and artifact.
3. **Contradictory leaderboard values:** `0.2778`, `0.3195`, and `0.4413` are not receipt-verified here. No estimate is supplied.
4. **Portal range error:** the cause remains unknown. A local range check cannot establish what the portal rejected; do not assume NaN outside footprint is the cause or claim acceptance. The submission format and portal behavior need an official receipt/error detail.
5. **No training stack:** `data/training_features.tif` and prepared caches are absent. Do not run `prepare_data.py`, restore from an unauthenticated mirror, or claim the prior holdout is reproducible without approved source provenance.
6. **Protocol conflict:** the method paragraph and prospective resolution of the lattice comparator are needed before a new experiment. Do not change dot budgets or evade the lattice; do not spend a submission slot.
7. **Future gate sequence:** for an assigned lane only, reuse the shared holdout/evaluator/writer; derive catalogue-based features only from visible faults; test each feature alone for leakage; run pre-placement surface novelty and final-dot overlap against the full pinned registry; require paired HOLDOUT-DTI evidence beating a comparable locked baseline; then use the separate selector and actual quota evidence. A format-valid TIFF alone is not submission-ready.

## Three-pass self-review

1. **Implement/review:** checked the branch, governing protocol and current repo entry points; reopened the pinned nine-site audit; ran the dependency-free and raster-backed feasibility checks. No candidate was generated.
2. **Adversarial review:** distinguished owner-reported leaderboard values, source-recorded holdouts, arithmetic lower bounds, and organizer-confirmed scores; flagged stale source revisions and absent data; made no projection or causal claim about B2.
3. **Original-request audit:** confirmed the branch, README links, score/uniqueness table, limitations, official manual-review sources, research-only download instructions and fail-closed verdict. Full tests/lint/syntax checks passed. The requested new unique higher-scoring TIFF remains unfinished by design because the explicit method-lane and novelty constraints block a valid run.

## Run card (documentation-only negative result)

```json
{
  "hypothesis": "No geological hypothesis tested: the active parallel-run protocol names a single assigned method paragraph, but none is present.",
  "mechanism": "Read-only repository review, nine-site frozen-evidence review, full automated test/lint checks, and one-witness necessary uniqueness feasibility calculation; no prediction mechanism evaluated.",
  "named_non_fault_mimic": "Not applicable; no candidate surface or geological signal was generated.",
  "holdout_dti": null,
  "holdout_ci95": null,
  "holdout_status": "NOT RUN; no candidate, withheld-positive count, or evaluator run.",
  "correlation_or_overlap_vs_registry": "No candidate surface correlation or final-dot overlap. Raster-backed feasibility found 82.341849% minimum overlap for K=37654 and 84.919483% for K=44090 against the pinned lattice witness; necessary bounds only.",
  "raster_sha256": null,
  "validator_output": "No candidate raster; NaN/range/CRS/shape/transform validation not applicable. The pinned reference/template passed the feasibility tool's identity/grid/value checks. New experiment output: none.",
  "submission_name": null,
  "submission_note": "No candidate generated; no submission authorized.",
  "verdict": "negative"
}
```
