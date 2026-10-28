# Repository review — 2026-10-28 (Arena branch `arena/c81bb5d5-gemsdoe24`)

## Decision

**No new TIFF, geological experiment, score projection, or competition-slot use. Do not submit any file on the basis of this review.** The requested outcome—a new, unique, high-scoring submission—is not achieved. The parallel-run protocol refers to one assigned method paragraph, but no method paragraph is present in the active brief. Inventing a lane or selecting a candidate from an old research queue would violate the protocol. The repository's frozen feasibility check also shows that the usual 37,654-dot budget cannot satisfy the literal `>70%` 3-pixel overlap stop against the retained lattice control. Neither the rule nor a stopped lane was changed.

There is **no defensible leaderboard score estimate** for a new TIFF. The executive site already has a nine-site summary and submission guide at [`docs/executive-summary.html#current-focus-files`](executive-summary.html#current-focus-files). The table's inspected files are pinned to source revisions from 2026-10-27, not freshly audited against each repository's 2026-10-28 head. Its historical score claims are not organizer receipts. Treat those files as research/audit downloads only, not as files approved to submit.

## Review scope and checks performed

This review was performed in three passes. No downloaded competition data, external layer or site content was treated as independently verified merely because a local copy or historical receipt exists.

| Check | Result |
| --- | --- |
| Branch and initial worktree | `arena/c81bb5d5-gemsdoe24`; clean at start; HEAD `fdd41b0` (the checked-out main snapshot). |
| History needed by tests | Initial clone was shallow. `git fetch --unshallow origin` completed; this made the full-history tests runnable. |
| Pinned project environment | Created ignored `.venv/` and installed `.[dev]` from the repository's pinned `pyproject.toml`; no tracked dependency files changed. |
| Full automated suite | `.venv/bin/python -m pytest -q`: **552 passed** in 202.48 seconds. |
| Lint and format | `.venv/bin/ruff check .`: passed. `.venv/bin/ruff format --check .`: 310 files already formatted. |
| Syntax / patch hygiene | `python -m compileall -q src scripts`, `node --check docs/assets/app.js`, and `git diff --check`: passed. |
| Frozen-count check | `python scripts/check_protocol_feasibility.py --dots 37654`: necessary lower bound 82.341849%; `submission_authorized: false`. This is arithmetic on a frozen audit, not a fresh raster audit. |
| Raster-backed feasibility check | `python scripts/check_uniqueness_feasibility.py --dot-budget 37654 --dot-budget 44090`: re-opened its pinned template and lattice witness; respectively 82.341849% and 84.919483% minimum overlap; expected exit 2. It produced no candidate surface, dots, TIFF or score. |
| Data required for a new holdout | `data/training_features.tif` and a prepared feature cache are absent in this checkout. The checked-in bridge rasters and external audit layers do not substitute for the full training stack. |
| Current organizer state | No DrivenData leaderboard, submission portal, receipt or account quota was checked. No organizer-confirmed score was obtained. |

The `82.341849%`/`84.919483%` values are **necessary lower bounds against one retained witness**, not actual candidate overlaps, not a full registry census, not proof of copying, and not HOLDOUT-DTI. The corresponding tool result explicitly leaves both pre-placement correlation and final-dot checks `NOT RUN` because no candidate was created.

## Nine-site executive summary: evidence, not a submission recommendation

The following is the pinned 2026-10-27 source-artifact audit represented in the repository. The “historical maximum” values are the owner-reported values supplied in the project record, **not organizer-confirmed scores**. The last-column local HOLDOUT-DTI numbers are source-recorded and not replayed in this review; they are not estimates of the leaderboard. Different sites used different holdout definitions, counts and evaluators, so the figures are not directly rankable as one common benchmark.

| Site | Historical highest claim in the supplied record (unverified) | Pinned inspected file | Source-recorded local holdout (not replayed here) | Literal 3-px lattice overlap | Decision |
| --- | ---: | --- | --- | ---: | --- |
| GEMSDOE24 | 0.2477 | [`24gems-catalogue-offset-geothermal-proximity-20261027T114303Z-578c30176163-zeros.tif`](https://github.com/buffedlizard55-lab/GEMSDOE24/raw/a1ecb683a9fda2aa4612f27e28896ebb8b19ad08/docs/downloads/24gems-catalogue-offset-geothermal-proximity-20261027T114303Z-578c30176163-zeros.tif) | Invalid; full-catalogue support affected fold placement | 99.7795% | Research only; submit NO |
| GEMSDOE25 | 0.2600 | [`gems25-h74-rmps-subsurf-catfree-b2-37654-20261026-3751606e1ce5-zeros.tif`](https://github.com/buffedlizard55-lab/GEMSDOE25/raw/227347d0f1beb420c0dd2a7dd4079ddc6389f5ab/docs/downloads/gems25-h74-rmps-subsurf-catfree-b2-37654-20261026-3751606e1ce5-zeros.tif) | 0.039057; evaluator `gems25.metric.dti_binary`; 25,308 withheld; CI [0.026077, 0.048895] | 100.0000% | Research only; submit NO |
| GEMSDOE27 | 0.2449 | [`gems27-h31-drcg-wl-celf28-20261026-cf8e1bbef244-allfinite.tif`](https://github.com/buffedlizard55-lab/GEMSDOE27/raw/6c34f5b7cb7756d23c258df051318b7b11cd9ab4/docs/downloads/gems27-h31-drcg-wl-celf28-20261026-cf8e1bbef244-allfinite.tif) | 0.047302; `gems27.metric` / buffered-v2; 120,778 withheld; CI [0.044527, 0.049619]; denominator discrepancy noted | 99.6149% | Research only; submit NO |
| GEMSDOE28 | 0.2710 | [`gems28-s22-ctxhgb-20261026-e23dabcec6e2-allfinite.tif`](https://github.com/buffedlizard55-lab/GEMSDOE28/raw/f78c1e8fdc2fb95b0f5915e1e95ff82a8f1aa309/docs/downloads/gems28-s22-ctxhgb-20261026-e23dabcec6e2-allfinite.tif) | 0.120177; 36,596 withheld; CI [0.104706, 0.136492]; source says unbuffered | 99.6176% | Research only; submit NO |
| GEMSDOE30 | 0.2600 | [`gems30-CSR1-44090-20261026-502fb5948335-zeros.tif`](https://github.com/buffedlizard55-lab/GEMSDOE30/raw/3c3d7255fdbb3a94375eff086522463a8eaca449/docs/downloads/gems30-CSR1-44090-20261026-502fb5948335-zeros.tif) | 0.158162; `component-holdout-v3-blockstats-20261025`; 60,988 withheld; CI [0.144986, 0.171474] | 99.9864% | Research only; submit NO |
| GEMSDOE31 | 0.2708 | [`gemsdoe31-h31y-regime-mosaic-37654-20261026-66162f1f-zeros.tif`](https://github.com/buffedlizard55-lab/GEMSDOE31/raw/abd9a45cc7adf046d7d3829eb6e8c980943f462d/docs/downloads/gemsdoe31-h31y-regime-mosaic-37654-20261026-66162f1f-zeros.tif) | 0.154964; `gems57-pooled-hide-v2`; 60,988 withheld; CI [0.140107, 0.170117] | 99.0466% | Research only; submit NO |
| GEMSDOE32 | **0.2778** | [`gemsdoe32-h47-ldgi-dualhorizon-corridor-37654-20261026T230609Z-0eb8a25c-zeros.tif`](https://github.com/buffedlizard55-lab/GEMSDOE32/raw/1398109a23f04a2ace71c1bd2f527cfba87860b5/docs/downloads/gemsdoe32-h47-ldgi-dualhorizon-corridor-37654-20261026T230609Z-0eb8a25c-zeros.tif) | 0.119765; `GEMSDOE32-HIDE-RECOVER-v3.0`; 22,232 withheld; CI [0.105732, 0.132895] | 99.6149% | H33-B2 is a historical benchmark only; current inspected file is research-only; submit NO |
| GEMSDOE33 | 0.2632 | [`gemsdoe33-fsml2-cc-37654-20261026-6fd4410bbaee-zeros.tif`](https://github.com/buffedlizard55-lab/GEMSDOE33/raw/122e2240a835c9c84831943ee3489dbb48fd6e85/docs/downloads/gemsdoe33-fsml2-cc-37654-20261026-6fd4410bbaee-zeros.tif) | 0.103077; `gems-segment-pooled-v1`; 60,988 withheld; CI [0.094144, 0.112941] | 100.0000% | Research only; submit NO |
| GEMSDOE36 | 0.2750 | [`gemsdoe36-kpl36-exp3-20261026-fc869911e88c-zeros.tif`](https://github.com/buffedlizard55-lab/GEMSDOE36/raw/61783525af4aa6dcf8da0bc68b06fa38b89ed27a/docs/downloads/gemsdoe36-kpl36-exp3-20261026-fc869911e88c-zeros.tif) | 0.170100; `gems-segment-pooled-v1`; 60,988 withheld; CI [0.155089, 0.186138] | 99.1687% | Research only; submit NO |

**File-to-download guidance:** the linked files can be downloaded for research/audit, but **none is OK to submit under the current literal uniqueness gate**. “Unique bytes” or a passing format check does not mean scientifically unique. The full page has the per-file evidence and format checks; it does not grant submission authorization. **Leaderboard estimate for all rows: NOT ESTIMABLE.**

### What the H33-B2 `0.2778` does and does not establish

The score is **owner-reported / unverified** in the supplied record; this checkout contains no artifact-linked organizer submission receipt for it. Repository forensics record that H33-B2's 37,654-dot mask is a subset of the 44,090-dot D2.8 emission after removing 6,436 public-catalogue-proximal dots, with no new dots added. This establishes an emission-mask relationship in that forensic record, not a causal relationship to hidden faults. A reduction in false-positive mass is one plausible explanation for a better score, but the hidden true-positive/false-positive contributions are unavailable, so neither mechanism nor score lift is identified. Do not copy H33-B2 or call 0.2778 an estimate for a new submission.

The prompt also cites `0.3195` and `0.4413` leaderboard snapshots. They conflict with the other supplied figures and are not authenticated by a current official leaderboard receipt in this review. They remain **unverified claims**, not a current leaderboard baseline. The recorded local S3DEP1 point (`HOLDOUT-DTI 0.166060`, `gems-segment-pooled-v1`, 60,988 withheld, 95% CI [0.151858, 0.180339]) is also not an organizer score; its existing selector verdict is negative.

## Geological ideas: ranked only, not assigned, not validated, not claimed globally novel

Three candidate concepts already appear in the current integrity review. They are reproduced as a *research queue*, not promoted as “untried”: the local code/record search cannot rule out overlapping parallel work or unpublished methods. The required paragraph is absent, the prepared stack is missing, and the 37,654-dot budget has a decisive necessary-condition failure. Therefore no candidate can be responsibly selected for the requested holdout in this pass. No expected DTI gain is stated.

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
