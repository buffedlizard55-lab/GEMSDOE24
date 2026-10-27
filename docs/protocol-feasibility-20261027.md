# Submission readiness: no new file authorized

**DOWNLOAD FOR RESEARCH: YES · SUBMIT: NO.**

The [nine-site executive table](executive-summary.html#current-focus-files) already
provides immutable downloads, exact-file evidence, source-recorded holdouts,
historical owner claims and individual negative verdicts. This continuation
produced no new TIFF, scientific experiment, score estimate or submission slot.
It does not establish a highest-scoring file for any site.

## A necessary-condition check before another experiment

The frozen [exact-file audit](../evidence/current_focus_nine_file_audit_20261027.json)
records 5,160,724 footprint pixels covered within 3 pixels of the retained lattice,
and 6,649 uncovered pixels. For any candidate with N distinct positive pixels
inside that same footprint, at most 6,649 can escape the lattice neighborhood.
Thus its directed overlap is at least `max(0, N - 6649) / N`.

For N = 37,654, that lower bound is **82.3418%**, already greater than the
literal 70% ceiling. A candidate with more than **22,163** dots cannot pass this
particular gate, even if every available uncovered pixel were used. This is
geometry, **not HOLDOUT-DTI, not ORGANIZER-CONFIRMED, and not a score projection**.
A smaller candidate is not thereby unique, scientifically useful or authorized.
Do not concentrate predictions in lattice holes merely to evade this check.
The bound assumes positive pixels are distinct and entirely inside the audited
footprint. It does not apply to another grid or a different comparator.

Reproduce without any scientific Python dependencies:

```sh
python scripts/check_protocol_feasibility.py --dots 37654
python -m unittest discover -s tests -p test_protocol_feasibility.py -v
```

[Arithmetic receipt](../evidence/protocol_feasibility_20261027.json) pins the
input audit's SHA-256. This session did **not** independently remeasure its
rasters, refresh its source commits, or rerun its holdouts.

## Scientific priorities and protocol conflict

The [existing ranked three-candidate plan](../knowledge/31_current_integrity_review_2026-10-27.md)
proposes signed gravity–magnetic reversal, lithology-conditioned ordinal
potassium fronts, and separated terrain-flexure dipoles. They are untested
hypotheses, not new discoveries or measured DTI improvements. Preserve their
specific layers, mimics, provenance caveats and preregistration requirements;
this review does not claim they are absent from every peer repository.

The operative prompt still lacks its promised **single method paragraph**.
Selecting a lane autonomously would violate the parallel-run restriction.
The registry-control policy also needs an explicit coordinator decision: the
current literal rule remains binding, including the space-filling lattice.
No exception was added, and stopped lanes must not be rerun or nudged.

The earlier B2 0.2778 claim is owner-reported, not an artifact-linked organizer
receipt. Its deletion-only emission history supports an emission-geometry
hypothesis; it does not reveal hidden labels or prove why its score arose.
The prompt's 0.3195 and 0.4413 claims conflict and cannot establish today's
leaderboard. There is no defensible numeric leaderboard estimate here.
The competition predicts fault structure relevant to geothermal exploration;
a high local fault-recovery metric does not establish a geothermal vent.

## Access and verification limits

This runtime permits outbound requests only to GitHub and package registries.
No new official geological source was fetched or asserted obtainable. No
DrivenData account, quota, receipt or leaderboard was accessed. The source
links in the prior scientific review are manual-review references, not fresh
verification by this session. No credentials or human inspection are requested
as a substitute for validation. A missing lane and policy conflict are explicit
coordination blockers, not format-validator failures.

## Three passes

1. Read README, AGENTS, the prior integrity review and frozen nine-file receipt.
   Added an offline exact-rational necessary-condition calculation.
2. Tested equality at 70%, zero uncovered cells, invalid inputs, candidates
   smaller than the uncovered area and fail-closed authorization. Six tests passed.
3. Checked the request against the deliverable: retained all research-only
   warnings; no claimed new TIFF, replay, live feed, estimated score or positive
   submission verdict. The full scientific suite was not run in this continuation;
   the initial runtime lacks NumPy and the scientific dependency environment.

**Next session:** obtain the assigned lane and explicit registry-control policy,
then validate that lane through the shared holdout/writer, single-feature
canaries and both novelty gates. Compare prospectively against the recorded
reference with paired uncertainty before a separate slot selector considers it.
Never upload merely because a TIFF passes shape and range checks.
