# Repository continuation — 2026-10-28

**SUBMIT: NO. No new TIFF, geological experiment or competition slot.** The requested
high-scoring unique submission is not achieved. [Nine-site table and research-only
files](executive-summary.html#current-focus-files) · [Historical maxima and exact
research links](portfolio-executive-summary.md) · [Submission guide](executive-summary.html#submission-steps).
The historical values are owner-reported, not authenticated organizer receipts.
None of the listed files is an approved new submission; a numerical leaderboard
estimate is not supported.

## What changed and what was verified

- Refreshed both nine-repository GitHub-only freshness feeds at
  **2026-10-28 16:08 UTC**. All nine main refs differ from the October 27
  nine-file audit pins. [Feed receipt](data/portfolio_freshness.json). This checks
  commit IDs only, not TIFF content, current scores, or the full registry. It
  does not establish that a repository's submissions actually changed.
- Re-measured the pinned template and lattice with
  `python scripts/check_uniqueness_feasibility.py --dot-budget 37654` after
  installing the pinned dependencies. The command exits 2: at least **82.34%**
  of any 37,654 distinct in-footprint dots must overlap that comparator within
  3 pixels. This is a necessary geometric bound, not HOLDOUT-DTI, evidence of
  copying, or permission to place dots in the holes. The lattice remains in the
  registry. Neither surface nor candidate-dot novelty was measured this session.
- The source-feed UI now warns when a successful static JSON fetch contains a
  check older than 12 hours. Missing, date-only, malformed or implausibly future
  timestamps are unknown. A new scientific-source check cannot make an old
  human-read leaderboard snapshot fresh. The 12-hour interval is a project UI
  policy based on the six-hour schedule, not an organizer guarantee. Static
  table source statuses are explicitly dated and remain snapshots.
- Concurrent PR #80 independently merged the same preflight into main. During
  integration we retained its shared `python scripts/check_git_history.py` and
  single CI step instead of keeping a private duplicate. Shallow or unavailable
  Git history fails with a specific diagnostic;
  a non-shallow repository is necessary but does not prove any individual commit
  or scientific result. A fresh clone can be repaired with
  `git fetch --unshallow origin` when GitHub access is permitted.
- This checkout was shallow; it was unshallowed and pinned Python requirements
  were installed locally. These environment changes are not a training run.
  The training raster and prepared feature stack are absent here. Small bridge
  files exist; matching their local hashes or labels does not prove that a mirror
  was authenticated by the organizer.

## H33-B2 and next work

The historical owner reports **0.2778**, not ORGANIZER-CONFIRMED. Prior pinned
pixel forensics describe a deletion-only subset of D2.8 that removes some dots
near public faults. Under asymmetric distance-weighted Tversky, removing redundant
false-positive mass can raise the score if the lost hidden-truth credit is small
enough; the hidden labels are unavailable, so this is a hypothesis, not the
identified cause. See the [algebra and provenance limits](metric-integrity-20261026.md).
A genuinely independent method could do better, but no reliable numerical estimate
or guarantee follows from the existing records.

The [research queue](research-directions-20261027.md) contains four ranked
prospective directions, physical layers, non-fault mimics, costs and access
caveats. They are not certified globally untried: open PR #70 overlaps the first
ideas. No single method paragraph is assigned in the current prompt, and the
literal lattice policy blocks common dot budgets. Do not choose or retune a
lane, exclude the comparator, or consume a weekly slot to evade those rules.
After an assigned lane and prospective policy resolution: restore and verify the
shared feature cache, canary every feature, run buffered whole-segment holdout
and comparable paired uncertainty, check full registry at both stages, run the
shared writer/read-back validator, and invoke the separate selector with actual
account allowance. Scientific novelty and format validity are different gates.

## Independent source references and access limitations

[Organizer reference solution](https://github.com/drivendataorg/gems-prize-reference-solution)
was accessible on GitHub; [competition rules](https://docs.nlr.gov/docs/fy26osti/96647.pdf),
[problem statement](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/),
[submission page](https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/),
[USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
and [INGENIOUS](https://gdr.openei.org/submissions/1391) are review links, not
freshly fetched in this restricted runtime. No current portal score, quota,
error trace or organizer acceptance was obtained. The prior range-rejection
cause remains unknown; finite zero-outside encoding may reduce one risk but is
not proof of acceptance. The platform's outbound allowlist excludes these hosts.
No credentials or unauthenticated portal automation were used.

## Three passes

1. Reviewed the standing instructions, recent continuation, scientific gates,
   shared evaluator/writer and source feed; refreshed GitHub refs and independently
   checked the lattice/template necessary bound.
2. Added stale/unknown feed warnings; reconciled the concurrently merged shared
   shallow-history preflight. Regression
   tests cover actual shallow and non-repository checkouts, exact age boundary,
   invalid/future timestamps, source failure, and old leaderboard vs new source time.
3. Rebuilt the site from recorded evidence and checked the original request:
   research downloads remain visibly **DO NOT SUBMIT**, no output is passed off
   as an organizer score or a new model, and the outstanding scientific goal
   remains explicit. The complete post-integration suite passed 560 tests; Ruff,
   Node syntax and diff checks passed. [Session run card](../evidence/2026-10-28_freshness_continuation_run_card.json).
