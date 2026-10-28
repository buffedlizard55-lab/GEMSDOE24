# Repository review — no submission authorized

**Outcome: NO new unique submission TIFF, NO upload, NO leaderboard projection.** The
[historical nine-site table](historical-champions.html) provides pinned research-only
files and the owner-reported historical results, not verified organizer receipts.
The [submission guide](executive-summary.html) is not permission to submit these files.

## What this review changed

The historical table previously displayed an unconditional “Format PASS” even though
the recorded validator has a separate `outside_is_nan_official_text` check that fails
for all nine all-finite variants. Its generator now displays the recorded local and
exterior-NaN checks separately, treating missing results as failures/unknown. It does
not alter a TIFF or decide what the portal accepts. These files passed the local
hard checks, including grid and in-footprint finite range, and the strict whole-array
no-NaN variant; the different exterior check fails. This tension is an **irregularity**,
not a diagnosis of the reported portal error. The [full evidence](data/historical_champions_20261028.json)
was recorded previously, not independently refreshed here.

## Science and blockers

B2's reported result of 0.2778 is **owner-reported, unverified**, not an
organizer-confirmed score. The prior [geometry replay](https://github.com/buffedlizard55-lab/GEMSDOE24/blob/fdd41b075a05e7df5b222e6e3644344cecc65746/evidence/oj1_priority_ancestry_replay.json)
records catalogue-proximal dot removal relative to earlier patterns. Improved
false-positive tradeoff is plausible but cannot be established without hidden labels.
There is no validated basis for estimating whether a new file exceeds that result.
The two different leaderboard numbers supplied in the request are unverified snapshots.

The required single-method lane paragraph is absent. The existing
[ranked research directions](research-directions-20261027.md) are proposals, not a
lane assignment; some overlap concurrent work. Neither a new feature canary nor a
holdout experiment was run. The ordinary 37,654- and 44,090-dot budgets have a
necessary minimum overlap of 82.34% and 84.92%, respectively, with a retained lattice;
this is **geometry, not a score**. This fresh read-only calculation exits 2 as expected.
Do not evade the gate by moving dots into lattice holes or excluding the comparator.
Neither the training raster nor prepared feature stack is present in this checkout.
Quota, organizer receipt, hidden labels, full current registry, and portal acceptance
are not independently verified. Access is restricted to GitHub and package hosts;
no inference is made about other sites' present state.

## Three review passes

1. Inspected the standing instructions, evidence and historical table. Recomputed the
   necessary-only uniqueness bound using the shared tool. Corrected the table's
   generator and regenerated the page from the existing evidence without retesting
   or rewriting historical files.
2. Added a regression test checking actual per-file flags and a failing local check.
   The first test run caught a misplaced variable and the generation command needed a
   script import path; both were corrected. Targeted tests and lint passed.
3. Ran the full test suite. Initially six historical-receipt tests failed because
   this checkout was shallow; fetched the existing history, without changing branches,
   and reran: 579 tests passed. No evidence tests were weakened. The requested new
   TIFF and prospective holdout remain unmet, not implicitly passed by these tests.

## Concurrent finding

The newly integrated [validator review](session-review-20261028-mask.md) reports a synthetic finite but GDAL-masked footprint pixel that the current shared validator accepts. This is an additional local false-pass risk; the historical local results do not certify masks. Coordinate the shared fix before any selector can authorize a file. That finding was not reproduced in this continuation.

## Next steps

Coordinate the missing method assignment and a prospective resolution of the literal
lattice rule. Only then restore/authenticate required cached inputs, preregister the
allowed lane, run feature-level canaries and the shared buffered whole-segment holdout,
compare with the prospective best and all registry entries, and validate the exact
file. A separate fail-closed selector must verify quota and all promotion evidence;
no human raster inspection should substitute for automated checks.

For manual source review: [DrivenData problem](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/),
[official reference implementation](https://github.com/drivendataorg/gems-prize-reference-solution),
and [USGS GeoDAWN release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and).
These non-GitHub official pages were not fetched during this session.
