# Repository review — 2026-10-29

**Outcome: review complete; no new scientific experiment, prediction raster, score estimate, or competition slot. SUBMIT: NO.** This review does not satisfy the separate request for a new high-scoring TIFF. No file is newly authorized for upload.

## Executive assessment

The repository has a substantial, unusually auditable research and submission-safety stack: shared holdout/evaluation, raster validation/writing, novelty preflight, evidence receipts, historical artifact audits, static executive pages, and broad automated tests. The current state does **not** support generating a defensible new competition entry. In this checkout, the complete organizer training-feature raster and prepared cache are absent; the parallel-run instructions do not provide an assigned single-method paragraph; and the required retained-lattice novelty preflight stops the conventional documented dot budgets. There is no basis to invent a replacement lane, call a projection a score, or relabel any historical TIFF as submit-ready.

The historical nine-site page is useful as a research index, but explicitly covers pinned artifacts rather than current heads. Its score column is a reported historical claim, not a projected score; every leaderboard estimate is NOT ESTIMABLE. In particular, GEMSDOE32's reported 0.2778 is OWNER-REPORTED / UNVERIFIED, not ORGANIZER-CONFIRMED. The account's actual submission quota, portal acceptance, and the cause of the reported range error remain unknown.

## Findings

### High — no scientifically/ procedurally eligible new artifact can be produced from this state

- The active protocol says the assigned lane is one specific method paragraph. No such paragraph is present in the supplied request or current standing instructions. Prior hypotheses are proposals only; selecting one here would violate the parallel-run boundary.
- `data/training_features.tif` and the full prepared feature stack are absent. Small bridge rasters and derivative/external layers are not substitutes for the source stack required by the existing runner.
- The shared necessary-condition checker was run with the retained registry, template, and lattice witness. Its 3-pixel witness coverage is 5,160,724 of 5,167,373 footprint pixels (99.8713%). For 37,654 and 44,090 distinct in-footprint dots, it gives minimum overlap lower bounds of 82.3418% and 84.9195%, respectively, above the protocol's 70% limit. Both invocations correctly exit 2 (`STOP_IMPOSSIBLE_BUDGET`). These are geometric lower bounds against one witness, not measured overlaps for a new candidate, not a complete registry census, not evidence of copying, and not performance scores. They do not establish that every smaller budget fails. Do not tune a stopped lane, target uncovered cells, or remove a comparator to bypass the gate.
- Consequently, no new surface/final-dot registry test, leakage canary, buffered whole-segment holdout, validation of a new prediction TIFF, or submission selector was run. No new TIFF or slot was produced.

### High — historical leader claims are not current score evidence

`docs/historical-champions.html` and associated receipts provide pinned download identities and local format/novelty context. They do not establish current-head completeness or organizer scores. The GEMSDOE32 B2 entry's 0.2778 is an unverified owner report. The historical explanation that it pruned catalogue-adjacent dots offers a plausible precision/recall mechanism only; hidden labels and artifact-linked organizer receipts are unavailable here, so neither causality nor an estimated leaderboard score follows. The request's conflicting leaderboard snapshots are likewise not verified standings.

### Medium — README's old session header can mislead users about the active branch

The top of `README.md` calls a prior Arena branch the “Current session” and links its review/run card. This review adds a clearly dated top-level continuation for the active session branch and identifies older session records as historical. The full mission prompt is already included later in README; this change does not paste a second copy.

### Concurrent main update — negative research raster is not submission-ready

While this PR was open, other sessions merged their work to `main`. Their generated GEO1 TIFF is now part of the repository, but was not generated or selected in this review. It is an **easy-to-download research result; SUBMIT: NO**: the exact file is [`GEMSDOE24-geo1-concealed-conduit-rad-mag-lidar-20261029-8c9946590ca7-zeros.tif`](downloads/GEMSDOE24-geo1-concealed-conduit-rad-mag-lidar-20261029-8c9946590ca7-zeros.tif), SHA-256 `ee37d94deb3545af1f814df61ec5acd7addafe01a4833384c2e25d1a5e6b384d`. Its recorded **HOLDOUT-DTI** is `0.1426949` (`gems-segment-pooled-v1`, 60,988 withheld positives, 95% CI `[0.1322931, 0.1523671]`); this is not a leaderboard estimate. The run card records 99.2538% final-dot overlap within 3 px against the retained lattice, which fails the 70% gate. Re-running the shared exact-file preflight reproduced `FORMAT: True | STRICT_RANGE: True | SCIENTIFIC_AUTHORIZATION: False | SUBMISSION: DO_NOT_SUBMIT`. Its local range/grid checks pass, but `official_format_compliant` is false because the artifact has zero rather than NaN outside the footprint and no NaN nodata tag. **Do not submit it.** The concurrent branch's evidence is in [`docs/data/geo1_run_card.json`](data/geo1_run_card.json), [`docs/data/geo1_download.json`](data/geo1_download.json), and [`docs/executive-summary-9sites.html`](executive-summary-9sites.html).

This does not change the conclusion that this review ran no experiment and generated no candidate. It shows why format/range validity, a local holdout result, and surface novelty must not be collapsed into an upload recommendation.

## Environment note — full Git history is required for frozen evidence checks

The checkout initially arrived as a shallow clone. Running the complete suite before restoring history produced six failures in tests that intentionally inspect original preregistration commits/source blobs; the failures were missing Git objects, not failed scientific assertions. After `git fetch --unshallow origin main`, those commits were available and the complete suite passed. The CI workflow already requests `fetch-depth: 0` and runs its history precheck, so this is a local checkout prerequisite rather than a proposed CI change.

## Source-hashed runner lint exception

After integrating concurrent `main`, `ruff check .` and `ruff format --check .` reported findings in `scripts/build_unique_geothermal_submission.py`. Its exact source hash is retained in `evidence/geo1_experiment.json`; editing or formatting the file in this review would invalidate that receipt. I left the scientific runner byte-for-byte unchanged and added it to Ruff's exclusions, following the existing treatment of a frozen source-hashed runner. This is a narrowly scoped lint exception, not a claim that the script itself is lint-clean; future development should occur in a new lane/source file with a separate reproducible receipt.

## Three review passes

1. **Inspect and reproduce:** read `README.md`, `AGENTS.md`, `docs/MISSION_PROMPT.md`, the latest review, the shared submission/evaluation/novelty code, and relevant site/evidence files. Confirmed the absent full feature stack and no assigned method. Installed the repository's pinned development dependencies in ignored `.venv/`; no tracked project dependency or code was changed.
2. **Adversarial checks:** ran the feasibility checker at both documented diagnostic budgets; verified its fail-closed exit code and bound; ran the full test suite in a shallow checkout, traced the six historical-verification failures to absent Git commits, then restored full history. Checked website and workflow source for the historical-only/NOT ESTIMABLE disclaimers and full-history CI checkout configuration.
3. **Recheck:** reran the complete suite after restoring history: **663 passed**. `ruff check .`, `ruff format --check .`, and `git diff --check` passed. Both feasibility checks returned exit 2 with the recorded lower bounds. No prediction TIFF, holdout result, fresh site audit, leaderboard value, organizer receipt, or quota was created or verified.

## Recommended next work

1. Provide a prospective, single-method lane assignment and an explicit resolution of the retained-lattice comparator policy. Do not weaken or evade current gates within a lane.
2. Restore the training raster/cache and template from an allowed source, hash-check the exact bytes, and establish provenance/semantics before any experiment. DrivenData login data and non-GitHub official portals are unavailable in this runtime; an owner mirror is not automatically official provenance.
3. Audit the current heads/artifacts of all nine named repositories before claiming novelty. Use the shared cached stack, evaluator and writer; withhold whole buffered segments; derive catalogue features from visible faults only; mask exact pixels; run per-feature leakage canaries; evaluate pooled 300 m DTI with confidence intervals; compare paired results to a replayable best; run both pre-placement surface and final-dot registry checks.
4. Implement and independently verify a hash-bound selector receipt and current quota check before promoting a specific TIFF. A format pass or local zero-outside test does not establish organizer acceptance. Retain the exact submission-page receipt to diagnose the reported range rejection and establish an ORGANIZER-CONFIRMED score.
5. Keep the nine-site table explicitly historical until every current head and artifact is audited. Do not publish a numerical leaderboard estimate without a validated calibration method; presently the estimate is NOT ESTIMABLE.

## Sources and artifacts

- [DrivenData competition overview](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) · [competition data](https://www.drivendata.org/competitions/306/competition-doe-gems/data/) · [leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)
- [NLR competition rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf) · [USGS GeoDAWN data page](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) · [OpenEI INGENIOUS](https://gdr.openei.org/submissions/1391)
- The links above are provided for manual review; this session did not fetch non-GitHub sources. The repo's pinned historical audit and the original user-provided score claims are not substitutes for current official receipts.
- [Nine-site historical comparison](historical-champions.html) · [submission guide](executive-summary.html) · [uniqueness feasibility page](submission-readiness.html) · [standing mission](MISSION_PROMPT.md)
- [Machine-readable review card](../evidence/session_30d63154_run_card_20261029.json)
