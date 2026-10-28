# Submission integrity continuation — 2026-10-28

**NO NEW TIFF · DO NOT SUBMIT · NO COMPETITION SLOT USED.** The requested unique,
high-scoring file is not achieved. The [nine historical champions](historical-champions.html)
are research downloads only; their leaderboard estimates are not estimable. They
are old snapshots, not a complete current registry or organizer score receipts.
The [submission guide](executive-summary.html#submission-steps) explains the
future upload process; no present file is authorized by this review.

## B2 and the nine sites

The owner-reported, **unverified** historical GEMSDOE32 B2 result, 0.2778,
is the highest of the nine owner-named historical results; it is not an
ORGANIZER-CONFIRMED score. Prior [geometry replay](https://github.com/buffedlizard55-lab/GEMSDOE24/blob/fdd41b075a05e7df5b222e6e3644344cecc65746/evidence/oj1_priority_ancestry_replay.json)
records B2 as a subset of an older dot pattern. Removing prediction mass could
improve distance-weighted Tversky when the reduction in false-positive mass is
large relative to lost true-positive credit. The hidden truth and score receipt
are unavailable, so this is a plausible mechanism, not an established cause;
there is no defensible numerical prediction that another file would exceed it.
See [metric algebra](metric-integrity-20261026.md). The request's 0.3195 and
0.4413 current-leader claims conflict and were not independently checked.
Geothermal fault detection is not confirmation of a vent.

## Shared validator fix

The old `check_variants` checked finite in-footprint raw values but did not
reject a TIFF whose nodata or GDAL mask hides finite in-footprint pixels. It
also did not explicitly check the dataset driver. A TIFF extension does not
itself establish the driver. An all-finite, in-range raw array therefore did
not prove that a masked reader would see all those predictions. This is a
format ambiguity, **not an established explanation of the reported portal error**.

The shared validator now has a `strict=True` mode which requires the `GTiff`
driver, self-contained raster and template, and no masked in-footprint pixels.
The writer refuses stale output sidecars and masked predictions. The shared
writer CLI and exact-file preflight use strict mode. This addresses the related
risk independently identified in [concurrent PR #84](https://github.com/buffedlizard55-lab/GEMSDOE24/pull/84);
that PR also contains other changes not integrated by this review. Its legacy default is retained only for reproducing
frozen historical receipts; it does **not** imply those receipts were tested
against the new checks. TNR1 historical verification separately requires the
new checks before comparing its unchanged old receipt. Neither mode authorizes
a competition slot. A future selector must require strict checks, independent
science evidence and actual quota; the independent selector-receipt verifier
is not implemented. Masks can come from sidecars: preserve and control the
whole local file context, not only the TIFF's SHA, when auditing.

A new strict preflight of the existing S3DEP1 research artifact passed format
and whole-array range checks but still returned **DO_NOT_SUBMIT**; see the
[exact-file receipt](../evidence/s3dep1_strict_preflight_20261028_arena_f7f69bc3.json).
It does not refresh the old holdout, confirm portal acceptance, or establish
novelty. No TIFF was copied or generated in this continuation.

## Protocol and source limitations

The single method paragraph promised in the parallel protocol is not present.
The [ranked research directions](research-directions-20261027.md) remain
untested proposals, with stated mimics, costs and data limitations; the first
ideas overlap open PR #70 and cannot be claimed globally untried. The prepared
stack and main training raster are absent in this checkout. No new scientific
lane, canary or holdout was run. Do not invent an assignment, remove registry
entries or alter a stopped lane to evade a check.

The shared feasibility checker was rerun against its pinned template and
retained lattice. **Geometric bounds, not scores:** for 37,654 distinct
in-footprint dots, at least 82.34% must lie within three pixels of the lattice;
for 44,090, at least 84.92%. Both exceed the literal 70% threshold. This does
not prove plagiarism or full-registry duplication. Smaller budgets are not
thereby valid or scientifically useful. [Feasibility explanation](protocol-feasibility-20261027.md).

The [GitHub-only freshness feed](data/priority_feed.json) was refreshed this
session: all nine heads changed from their pinned review refs. A changed commit
is not evidence of changed submissions; no current-head raster audit, current
leaderboard, score receipt, portal validator, account quota or organizer
acceptance was obtained. The reference solution's [README at the checked
commit](https://github.com/drivendataorg/gems-prize-reference-solution/blob/aebe92f7c8a990f0e3443451b7a825d9afd6336b/README.md)
was inspected on GitHub and documents CPU and GPU options. Non-GitHub sources
such as [official rules](https://docs.nlr.gov/docs/fy26osti/96647.pdf), [USGS
GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and),
and [DrivenData](https://www.drivendata.org/competitions/306/competition-doe-gems/)
are review links only; outbound access to them is restricted in this runtime.
Mirror hashes establish byte identity, not organizer provenance.

## Next work

1. Coordinate the missing single-method lane and prospectively resolve the
   literal calibration-lattice policy without silently weakening either rule.
2. Restore the authorized feature cache, verify provenance, reconcile all
   current registry members and parallel lanes, and preregister no more than
   the permitted experiments. Follow the existing visible-fault-only,
   buffered-segment holdout and feature-canary protocol.
3. Check surface rank correlation before placement and dot overlap afterward;
   compare paired holdout uncertainty against a comparable benchmark. Run the
   strict read-back validator and use a separately verified selector and quota.
4. Preserve the exact artifact and organizer receipt if a candidate is later
   approved. Investigate the range rejection using its actual artifact and portal
   diagnostics rather than guessing that exterior NaNs caused it.

## Three verification passes

1. Reviewed the handoff, shared tools, local data, nine-site evidence and open
   parallel work. Refreshed nine GitHub refs and reran the geometric bound;
   neither constitutes a scientific experiment.
2. Added strict driver/mask checks and adversarial synthetic tests. The first
   full suite exposed breakage of frozen exact-receipt comparisons; retained
   legacy receipt format, made new preflights strict, and required TNR1's two
   new checks before comparing its historical receipt. No old receipt was
   rewritten to claim a new historical test.
3. Rebuilt the site, integrated concurrent main changes and reran the complete suite (**587 passed**), Ruff checks,
   formatter, JavaScript syntax and diff whitespace checks. Verified the exact
   S3DEP1 research artifact with strict preflight: format/range passed but
   submission authorization remained false. No browser-based visual review,
   live competition access, feature canary, scientific replay or new TIFF is
   claimed. [Run card](../evidence/session_f7f69bc3_run_card_20261028.json).
