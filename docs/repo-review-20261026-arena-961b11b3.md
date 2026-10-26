# Repository review — 2026-10-26 (Arena review branch)

## Executive decision

**No new candidate or TIFF was generated in this review. Nothing is cleared to submit.** The current local research point-best is downloadable for audit, but it is **not** a competition submission recommendation. No experiment or weekly slot was used.

The operative parallel-run instructions do not identify a single method paragraph for this branch. The recorded `active_lane.json` is historical lane identity, not a new assignment. The existing queue says not to revive stopped methods or infer a lane from a different session. I therefore did not select a geological method and run it anyway. That would violate the experiment protocol and would not be a defensible route to a unique submission.

- **Current-main reference only:** `gems24-dprf1-stitched-oof-tworegime-20261026-81849d67c8bf-zeros.tif` — [download for research/audit; DO NOT SUBMIT](downloads/gems24-dprf1-stitched-oof-tworegime-20261026-81849d67c8bf-zeros.tif).
- **DPRF1 score:** **HOLDOUT-DTI** `gems-segment-pooled-v1` = `0.1637924247`, 95% CI `[0.1504462173, 0.1773903020]`, `60,988` withheld positives. This is source-recorded local validation, not an organizer score or a forecast of a leaderboard result.
- **Automated exact-file check:** format `PASS`; whole-array `[0,1]` `PASS`; exact template CRS/shape/transform `PASS`; scientific authorization `FAIL`; final-dot uniqueness `FAIL`; selector `DO_NOT_SUBMIT`.
- **No honest leaderboard estimate exists** for any historical raster in the nine-site table below. A prior owner-reported score is not an estimate or an organizer receipt.

The requested public leaderboard values `0.2778`, `0.3195`, and `0.4413` remain **OWNER-REPORTED / UNVERIFIED** in this repository. In particular, `0.3195` and `0.4413` conflict. No artifact-linked submission-page receipt was obtained. The project policy also prohibits automating DrivenData pages; this review did not visit the leaderboard, submission form, or authenticated data tab.

## Nine-site executive comparison

The linked GeoTIFFs are the highest historical entries supplied in the owner's request and pinned in the portfolio audit. The score column repeats **owner-reported** values only. The `NOT ESTIMABLE` field is deliberate: there is no common, independently replayed holdout plus receipt-linked calibration that supports projecting these values to the hidden leaderboard. “Exact matches” means exact scored-cell content among the selected cross-site artifacts. The stricter final-dot test is separate and compares all retained registry entries, including the synthetic spacing-5 calibration control.

| Site | Historical TIFF (download for audit/learning only) | Highest listed score | Cross-site exact match in audited set | Final-dot uniqueness under the stated protocol | Score estimate / submit? |
|---|---|---:|---|---|---|
| GEMSDOE24 | [H25-1 D1.5](https://github.com/buffedlizard55-lab/GEMSDOE24/blob/46f663dad1a1c3d8231e5de5dbad4ee4d19e8d56/docs/downloads/gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-allfinite.tif?raw=1) | **0.2477** — OWNER-REPORTED / UNVERIFIED | Exact content match with GEMSDOE30 | **FAIL**, max 3-px overlap `100%` | NOT ESTIMABLE · **DO NOT SUBMIT** |
| GEMSDOE25 | [Dotted H19-5 D2.8](https://github.com/buffedlizard55-lab/GEMSDOE25/blob/fac6dbe5852baa0f0125d00ecc5cb1c16872741a/docs/downloads/gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-zeros.tif?raw=1) | **0.2600** — OWNER-REPORTED / UNVERIFIED | Exact matches with GEMSDOE24, 30, 31, 32 and 33 | **FAIL**, max 3-px overlap `100%` | NOT ESTIMABLE · **DO NOT SUBMIT** |
| GEMSDOE27 | [Topo-gap closure D1.5](https://github.com/buffedlizard55-lab/GEMSDOE27/blob/cf8b4c201f2cc2ef649b6ca7cd32f235c2f6743a/docs/downloads/gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-allfinite.tif?raw=1) | **0.2449** — OWNER-REPORTED / UNVERIFIED | Exact content match with GEMSDOE28 | **FAIL**, max 3-px overlap `100%` | NOT ESTIMABLE · **DO NOT SUBMIT** |
| GEMSDOE28 | [H36-1 rung30](https://github.com/buffedlizard55-lab/GEMSDOE28/blob/12ec4fea4c97a7887a7ca8a06f9bd94c7609ea07/docs/downloads/gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-allfinite.tif?raw=1) | **0.2710** — OWNER-REPORTED / UNVERIFIED | No exact cross-site match in the selected files | **FAIL**, max 3-px overlap `100%` | NOT ESTIMABLE · **DO NOT SUBMIT** |
| GEMSDOE30 | [D28 Poisson 300 m](https://github.com/buffedlizard55-lab/GEMSDOE30/blob/35ce8911e2c3287eed973eacd12c252e8cb3f34c/docs/downloads/gemsdoe30-d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca.tif?raw=1) | **0.2600** — OWNER-REPORTED / UNVERIFIED | Exact matches with GEMSDOE24, 25, 31, 32 and 33 | **FAIL**, max 3-px overlap `100%` | NOT ESTIMABLE · **DO NOT SUBMIT** |
| GEMSDOE31 | [H27-4 solo D2.8](https://github.com/buffedlizard55-lab/GEMSDOE31/blob/784d3ae2dc1d247323378074257eba4353b3d087/docs/downloads/gemsdoe31-h27-4-solo-d28-20261004-8acb75e1-allfinite.tif?raw=1) | **0.2708** — OWNER-REPORTED / UNVERIFIED | Exact matches with GEMSDOE28 and 33 | **FAIL**, max 3-px overlap `100%` | NOT ESTIMABLE · **DO NOT SUBMIT** |
| GEMSDOE32 | [H33-B2](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/8b00ee91b9d6d7ef0e3762eb7bc0c92bee0928d1/docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif?raw=1) | **0.2778** — OWNER-REPORTED / UNVERIFIED; highest of these nine claims | No exact cross-site match in the selected files; it is a strict dot-subset of D2.8, not an independent method | **FAIL**, max 3-px overlap `100%` | NOT ESTIMABLE · **DO NOT SUBMIT** |
| GEMSDOE33 | [H33D analog tip/stepover](https://github.com/buffedlizard55-lab/GEMSDOE33/blob/adf1f45ae0030de5e63d07655eaeb1a0ea4d96f3/docs/downloads/GEMSDOE33-h33d-analog-tip-stepover-r30-20261004-cb490425926e.tif?raw=1) | **0.2632** — OWNER-REPORTED / UNVERIFIED | No exact cross-site match in the selected files | **FAIL**, max 3-px overlap `100%` | NOT ESTIMABLE · **DO NOT SUBMIT** |
| GEMSDOE36 | [Anderson geothermal PINN](https://github.com/buffedlizard55-lab/GEMSDOE36/blob/6dae4545076c4e5fc2be1cf348fe740ba9508a1d/docs/downloads/gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif?raw=1) | **0.2750** — OWNER-REPORTED / UNVERIFIED | No exact cross-site match in the selected files | **FAIL**, max 3-px overlap `99.9176%` | NOT ESTIMABLE · **DO NOT SUBMIT** |

**Interpretation:** none of these historical TIFs is a safe recommendation to upload. Some are exact cross-site content duplicates; others are not exact duplicates but still fail the explicit `>70% within 3 px` stop. The high overlap is driven in part by the retained synthetic spacing-5 lattice. That is a protocol failure, not evidence that every author copied another submission. The CSV, hashes, immutable source refs, and full comparator receipts are in [the nine-site portfolio table](data/portfolio_summary_20261026.csv) and [full artifact audit](data/portfolio_artifact_audit_20261026.json).

## Why GEMSDOE32 H33-B2 may have scored well — and what is not known

The `0.2778` number is not organizer-confirmed. The artifact audit establishes a geometric relationship: the D2.8 reference contains `44,090` dots; H33-B2 contains `37,654`, after removing `6,436` dots within `2` pixels / `200 m` of the public catalogue and adding no dots. H33-B2 is therefore a pruned subset of the D2.8 dot pattern, not evidence of a wholly independent detector. The historical GEMSDOE31 solo set also loses `2,545` dots and gains none when compared with B2; these are mask-algebra observations, not score explanations.

Under the repo's pooled distance-weighted Tversky form, `D = TP_w / (TP_w + 0.2 FP_w + 0.8 FN_w)` (ignoring its denominator epsilon), pruning helps only when the reduction in weighted false-positive cost exceeds the loss in recovered positive credit. Near-catalogue dots can be redundant for a hidden-fault target, so that mechanism is plausible. But the hidden `TP_w`, `FP_w`, and `FN_w` are unknown here; the loss term could dominate because false negatives carry weight `0.8`. No observed mask relation proves why the organizer score changed, establishes geothermal vents, or forecasts a score above `0.2778`.

The current-main local point-best is not a substitute for the H33-B2 score: its `HOLDOUT-DTI` `0.16379` is an internal spatial holdout, not a leaderboard estimate. The audited portfolio explicitly has no defensible numeric hidden-score projection.

## Prospective geology hypotheses (ranked; none run or assigned)

Ranks below are qualitative research priorities, **not predicted score gains**. The local peer audit corrected earlier ideas: scarp/graben pairing has already been implemented at GEMSDOE36; radiometric composition and seismic-saddle concepts overlap prior GEMSDOE24 lanes. The following operators are unexecuted in the reviewed local queue, but global novelty against every changed peer is not established by a name search.

| Rank / expected value / cost | Layers and physical signature | Why it could find an uncatalogued fault; named non-fault mimic | Difference / data readiness |
|---|---|---|---|
| 1 / uncertain, best benefit-to-cost hypothesis / medium-high | Raw RTP, TMI and isostatic gravity plus quantized `TMI_up150`; two-sided, azimuthal semivariogram/texture-change persistence across lags | A covered basement step may alter directional texture without a strong amplitude edge. Mimics: intrusive or remanence contacts and survey-leveling seams. | Tests a distribution/texture discontinuity, not another scalar gradient, Euler derivative or extra HGB feature stack. Required layers are in the hash-pinned local bridge/cache; physical support of quantized ranks must be respected. |
| 2 / uncertain, lower confidence / medium | Cached K/Th/U ranks; tangent-coherent signed spatial displacement (“phase lag”) between mobile-element fronts and a Th front | Fracture-controlled alteration can be spatially offset from a lithologic front, including under cover. Mimics: weathering and downslope sediment transport. | Spatial relation rather than CRP1/CUP1 compositional magnitude. Quantized ranks do not support claims about absolute concentrations. |
| 3 / uncertain / high | Raw RTP/TMI/gravity; local quadrature-filter phase congruency and cross-modality orientation agreement | A buried, low-amplitude discontinuity may retain phase alignment even where no scarp is exposed. Mimics: dikes, caldera margins and acquisition seams. | Phase consistency rather than scalar continuation/derivative or cross-depth amplitude persistence. Calibration and redundancy remain untested. |
| 4 / deferred / high | Absolute-elevation USGS 3DEP tiles plus existing LiDAR; graph of channel continuations and cross-catchment offsets | Repeated channel deflection could expose subtle displacement. Mimics: fan avulsion, stream capture and lithologic resistance. | Connectivity graph rather than a lineament detector. Not data-ready: the restored cache's terrain channel is detrended elevation, not an absolute DEM. The official [USGS 3DEP data tools](https://www.usgs.gov/3d-elevation-program/data-tools) are the required source, but access was not verified under this sandbox's host allowlist; do not call this candidate viable yet. |

No candidate was tested in this session because there is no supplied method paragraph/lane assignment, and the retained literal novelty policy has an additional geometric obstruction at the standard emission budget: for `37,654` dots, the audited spacing-5 lattice covers enough cells to force a minimum `82.34%` within-3-px overlap. This bound applies to that stated budget; it is not permission to shrink, move, or retune dots after seeing results. Any changed comparator policy or emission budget must be prospective and approved before the next experiment.

## Repository and pipeline review

### What I executed

1. Read the standing `README.md`/`AGENTS.md`, current portfolio audit, preregistration queue, shared evaluator/writer/preflight code, run cards, site source and open-PR status. The owner prompt is already preserved in the README as the normalized current request plus its archived full text; this report is linked from the current portfolio review, which the README links at the top.
2. The checkout began shallow. Initial test failures were solely historical-source verification failures (`git show` could not find preregistered commits). I fetched full commit history without changing branches; this is why local tests now match the CI `fetch-depth: 0` requirement.
3. Restored the owner-supplied mirrored `data/training_features.tif`: `418,912,844` bytes, SHA-256 `4371c82e3b8339b807bdffcf4ef59a225520fe2988d521be208ae33743123bc5`, at `buffedlizard55-lab/GEMSDOE` ref `c0c06ac82178f26b94fce3397036ef8f12a2f3a0`. This verifies mirror byte identity only; it does **not** independently authenticate organizer provenance.
4. Ran `scripts/prepare_data.py` successfully on CPU. It wrote the ignored, regenerable float32 cache `data/prepared/features.npy`, shape `(5,167,373, 30)`, SHA-256 `a4ca25b2a18f6f6637f0247367cc6235a1366eb8475f77b18cd0285e62232dc8`. Its metadata pins the template, source feature raster and LiDAR feature raster hashes. This resolves local input placement for future runs; it does not assign a lane or constitute a new experiment.
5. Re-ran the exact-file submission preflight on DPRF1 with the pinned sample-template hash. Terminal result: `FORMAT: True | STRICT_RANGE: True | SCIENTIFIC_AUTHORIZATION: False | SUBMISSION: DO_NOT_SUBMIT`. This demonstrates that the current zero-outside research artifact's stored values are in `[0,1]`; it does not establish the cause of the owner's earlier portal rejection or guarantee portal acceptance.
6. Verified frozen records without rerunning their experiments: `evaluate_holdout.py --verify-recorded`, `--verify-tnr1`, `--verify-gvc1`, and the recorded SAHG1, RSHG1, HCW/FUSE, DPRF1 and TRSG1 lane verifiers. Each returned its recorded negative/non-authorizing status. No training, new holdout, raster generation, upload or slot selection occurred.
7. Ran the site builder and offline source-feed checks. The built site reports `new_slot_eligible=false`, `no_scores_fabricated=true`, and `verdict=negative`. Site generation changed only volatile timestamps in generated JSON; those timestamp-only edits were reverted. The prior browser receipt audits desktop/mobile; no new browser installation was performed here.

### Three-pass completion record

- **Pass 1 — implement and verify:** reviewed the existing requirements/evidence, restored the hash-pinned owner mirror and CPU cache, checked the current exact TIF, and recorded the no-candidate/no-slot decision. No geological experiment was run because no method lane was assigned.
- **Pass 2 — defect and assumption review:** found that the Arena checkout was shallow, causing two history-provenance tests to fail despite the source being present on GitHub. Fetched history as CI requires, reran them successfully, and kept the owner-mirror provenance distinct from organizer authentication. Confirmed that a format/range pass does not bypass the selector and the literal duplicate gate.
- **Pass 3 — final requirements recheck:** re-ran the full suite, lint/format/syntax checks, parsed the run-card JSON, checked all report-relative links, rechecked data/artifact hashes and preflight, and verified the site status remains negative. The requested unique, higher-scoring, submit-ready TIFF remains unachieved and is explicitly not claimed.

### Reproducible checks on this branch

- Full test suite after unshallow fetch: **447 passed** (`python -m pytest -q`).
- Ruff lint: passed; Ruff format check: **180 files already formatted**.
- `compileall`, JavaScript syntax checks and `git diff --check`: passed.
- Owner-site offline verification and both offline feed schema checks: passed; they do not claim fresh web access.
- Site build: passed; no page HTML changed and no score/eligibility was fabricated.
- Exact DPRF1 preflight: format/range/grid pass, authorization fail, `DO_NOT_SUBMIT`.

### Important concurrent result (not integrated into this branch)

Open PR [#50](https://github.com/buffedlizard55-lab/GEMSDOE24/pull/50) reports H24-DRAIN5 `HOLDOUT-DTI` `0.16950` `[0.15627, 0.18343]` (`gems-segment-pooled-v1`, `60,988` withheld positives), paired increment `+0.00571` `[+0.00136, +0.01003]` over its replayed DPRF1 control. It also reports `83.55%` of candidate dots within 3 px of DPRF1, exceeding the `70%` stop, and its selector says `DO_NOT_SUBMIT`. It is an **unmerged concurrent PR**, not a result from this branch; it must not be silently called the current-main point-best or a leaderboard score. It merits review for its scientific and integrity record, not a slot.

### Limits that still block a successful submission

- No assigned single-method paragraph and no candidate passed the literal uniqueness gate. The current DPRF1 file also fails literal final-dot uniqueness: `99.5645%` overlap with the retained lattice and `86.6628%` with EUL1. Its recorded competing-method-only overlap is not a replacement for the all-entry rule.
- The current selector is deliberately fail-closed. Independent positive replay certification and a lawful, current account quota receipt are not implemented/available; no format validator can authorize an upload.
- DrivenData authentication and original data/leaderboard/submission-page access are unavailable here. The feature data restored above is an owner-supplied GitHub mirror, not a newly authenticated official copy. No automatic DrivenData access was attempted.
- Current public-score claims conflict and lack linked receipts. No cross-site leaderboard score calibration is available. The historical scores in the table cannot be used as forecasts.
- Nine pinned source repositories changed since the prior audit. Freshness is not pixel-level novelty; the existing cross-site audit is scoped to its pinned refs and must not be described as auditing every new commit.
- The previously reported portal range error's exact rejected artifact and cause are not documented. The current zeros variant passes the strict global numeric check, but local success is not an organizer acceptance receipt.

### Next work, in order

1. Resolve the missing method-lane assignment and comparator policy prospectively; keep the lattice and every control in the frozen registry until that decision is documented. Do not retune stopped lanes or move dots to clear the gate.
2. Update the nine-site source pins and pixel-audit changed artifacts in a new versioned registry before describing a candidate as globally unique.
3. Preregister only one ready candidate. Test each source and transform alone as a leakage canary, then use the shared segment-buffered holdout/evaluator and writer. Require a paired gain over the current comparable holdout best and both pre-placement surface and final-dot novelty before any slot discussion.
4. Complete an independent replay and a legitimate current quota/receipt verification path. Keep the agent non-uploading; a file-format pass is not a slot decision.
5. Keep the official review sources available for audit: [competition rules](https://www.drivendata.org/competitions/306/competition-doe-gems/), [problem and metric](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/), [reference solution](https://github.com/drivendataorg/gems-prize-reference-solution), [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and), [INGENIOUS](https://gbcge.org/current-projects/ingenious/), [OpenEI GDR 1391](https://gdr.openei.org/submissions/1391), and [EPSG:32611](https://epsg.io/32611). Those public links were not all fetched anew in this review; see the source receipts and access limitations rather than treating a link as fresh verification.

## Review run card

Machine-readable negative review card: [JSON](data/repo_review_run_card_20261026_961b11b3.json). It explicitly records no new holdout, no new raster, no new submission name and no promotion.
