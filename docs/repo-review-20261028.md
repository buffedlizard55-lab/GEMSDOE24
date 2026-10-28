# Repository review — 2026-10-28

## Executive decision

**No new submission TIFF; no experiment or competition slot used; do not submit any file on the basis of this review.** This is a documentation and validation review only. The parallel-run instruction requires work inside one assigned method paragraph, but no such paragraph is identified in the active brief. Selecting a lane from the research queue would violate that constraint. The previously documented lattice bound also rules out the standard 37,654-dot budget under the literal 70% overlap gate; this is a geometric feasibility result, not a score or a reason to change the budget or place dots strategically.

The repository contains an extensive evidence trail, submission writer/validator, holdout tooling, site generator, source freshness records and a nine-site table. These are useful foundations, but do not support the requested claim that a new unique TIFF beats a particular leaderboard score: live leaderboard access, a verified organizer receipt, current source artifact re-audit, comparable fresh holdout, and an assigned method are absent.

## Review scope and verified checks

- Confirmed the active branch is `arena/31593f7c-gemsdoe24`; initial worktree was clean.
- Read the README start section, standing `AGENTS.md`, normalized active owner brief, existing nine-site audit and prior feasibility review.
- Checked the frozen feasibility tool: `python scripts/check_protocol_feasibility.py --dots 37654` reports the bound from the pinned count receipt. Its reported 82.3418% minimum overlap is explicitly **not HOLDOUT-DTI, not an organizer result, and not a full registry audit**.
- Ran `python -m unittest discover -s tests -p test_protocol_feasibility.py -v`: **6 tests passed**.
- Attempted `python -m pytest -q`: unavailable because this runtime's system Python has no `pytest` module. No attempt was made to install dependencies or run a different environment; therefore the full test suite remains **not run in this review**.
- The research queue in `docs/research-directions-20261027.md` lists four ranked, untested operators. They are plans only; no score lift or global novelty is established. The active data/cache limitations and source-fetch boundaries are detailed in the current owner brief.

## Findings / issues to resolve

1. **Blocking protocol ambiguity:** the user-provided parallel-run text references a single method paragraph but does not provide one. Do not infer it from the ranked candidate list. A coordinator must assign the paragraph/lane.
2. **Blocking registry-control conflict:** the retained lattice is a calibration raster but the literal comparator rule also counts it. The fixed standard dot budget necessarily fails the stated overlap ceiling against this witness. A policy owner must prospectively decide whether the witness is a valid novelty comparator; until then, do not remove it, weaken the gate, or evade it by changing placement.
3. **No current, comparable performance estimate:** owner-reported 0.2778 (and inconsistent 0.3195/0.4413 snapshots) are not artifact-linked organizer confirmations. Existing HOLDOUT-DTI records are source-recorded, version/split-specific and not freshly replayed here. Do not label them leaderboard projections.
4. **Stale-by-design nine-site inventory:** the frozen audit is pinned to source revisions. Its prior freshness check detected later source movement; that feed is historical and does not audit new artifacts. Re-audit exact artifacts and receipts against current heads before describing any file as current.
5. **Data/test environment:** the active brief says the raw training raster and prepared feature cache are absent. The owner-mirror restore path is not organizer authentication. Full pytest could not run in this runtime. No new official geological layer's access/coverage was independently verified here.
6. **Submission status must remain fail-closed:** old research TIFFs are not newly generated or authorized. A passing format validator alone cannot establish scientific merit, uniqueness, score improvement or weekly-slot eligibility.

## Required next steps

1. Receive the exact assigned method paragraph and prospective written resolution of the calibration-lattice comparison policy.
2. Restore required data only from an allowed source; record provenance separately from byte hashes and verify the cached stack against its manifest.
3. Re-audit current focus-site artifacts/receipts; rerun the full test suite in the project's pinned environment.
4. For only the assigned hypothesis, preregister at most three arms; test each feature alone for leakage; run the shared buffered whole-segment holdout and paired uncertainty comparison to a protocol-comparable baseline.
5. Check surface novelty before placement and final-dot overlap afterward. Apply exact-format read-back validation and the separate selector. No slot until every gate passes and quota is confirmed.

## Three-pass self-review

1. **Initial review:** read the governing brief and repo state; ran the standalone frozen-count checker and its unit tests.
2. **Adversarial pass:** separated frozen source claims from fresh measurements; identified missing pytest and the difference between a feasibility bound and an actual novelty result; did not interpret scores as projections.
3. **Requirement pass:** confirmed no new TIFF, candidate, holdout, organizer score, quota check or submission occurred; left the protocol's lane and registry gates unchanged. This review does not claim the requested higher-scoring submission was produced.

## Run card (documentation-only negative result)

```json
{
  "hypothesis": "No geological hypothesis tested; method lane is unassigned.",
  "mechanism": "Documentation and frozen-count feasibility audit only; no raster prediction mechanism.",
  "named_non_fault_mimic": "Not applicable; no geological signal was tested.",
  "holdout_dti": null,
  "holdout_ci95": null,
  "holdout_status": "NOT RUN; no new experiment or withheld-positive count",
  "correlation_or_overlap_vs_registry": "No candidate surface or final dots generated. Frozen geometry receipt reports 82.3418% necessary minimum overlap for 37,654 dots against one lattice witness; this is not a candidate novelty measurement.",
  "raster_sha256": null,
  "validator_output": "No new raster to validate; no NaN/range/CRS/shape/transform result for a candidate.",
  "submission_name": null,
  "submission_note": "No candidate generated; no submission authorized.",
  "verdict": "negative"
}
```
