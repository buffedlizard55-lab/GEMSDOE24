# Continuation review — 2026-10-28

**No new candidate, score estimate or competition submission. SUBMIT: NO.**
The [nine-site research-download table](executive-summary.html#current-focus-files)
and [ranked prospective ideas](research-directions-20261027.md) remain historical
snapshots, not current-head or leaderboard verification. The proposed first two
ideas overlap work in another PR; their novelty is not established. The user
specified a single-method lane but supplied no method paragraph, so this session
did not independently choose one, generate a surface or run a geological experiment.

## Previous-session next step completed

Added `scripts/check_git_history.py` and invoked it at the start of reliability
CI, before historical receipt verification. It fails closed when Git is absent,
the directory is not a repository, Git returns an unexpected value, or the
checkout is shallow. A full checkout is **necessary, not proof** that a
particular pinned commit exists or that its ancestry is correct; the existing
individual verifiers retain that responsibility. The check is read-only.

## Three passes and results

1. **Implement:** reviewed the active brief, instructions, previous review,
   shared writer, CI and the prior research plan; added the history preflight.
   Its message directed this shallow clone to `git fetch --unshallow origin`;
   fetching the history made the guard pass. No branches were switched.
2. **Adversarial review:** tested full, shallow, non-repository, missing Git and
   unexpected-output cases. Verified that the new check never asserts that the
   historical receipts themselves are correct. The pinned raster preflight was
   independently rerun: at 37,654 and 44,090 distinct in-footprint dots its
   lattice witness implies at least 82.34% and 84.92% overlap, respectively,
   above the literal 70% stop threshold. This is geometry, **not a score** or
   proof of copying; a smaller budget is not automatically acceptable.
3. **Recheck:** after installing the pinned Python dependencies and restoring
   full history, the complete suite passed: **557 tests**. `ruff check src
   scripts tests` and `ruff format --check src scripts tests` passed. The
   scientific holdout was not run, nor were a new raster, registry-wide novelty
   comparison, leakage canaries, portal validation or source refresh performed.
   Existing recorded results were not replayed by this review.

## Evidence and uncertainty

The reported GEMSDOE32 B2 **0.2778 is owner-reported and unverified**, not an
artifact-linked organizer receipt. Its deletion-only emission history motivates
an emission-geometry hypothesis, but cannot establish why hidden-label performance
was high or whether a different raster would exceed it. The prompt's leaderboard
claims conflict; no live leaderboard was checked and no numeric leaderboard
projection is justified. A GeoTIFF's range and grid checks alone do not approve it
for upload or explain the reported portal rejection.

Manual reference links, not newly fetched here: [competition overview](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/),
[submission page](https://www.drivendata.org/competitions/306/competition-doe-gems/data/),
[official rules](https://docs.nlr.gov/docs/fy26osti/96647.pdf),
[reference implementation](https://github.com/drivendataorg/gems-prize-reference-solution),
[USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and).
This sandbox only permits outbound access to GitHub and package registries, so no
fresh official non-GitHub source, account quota or receipt was verified.
Owner-mirrored rasters are not automatically organizer-authenticated.

## Next steps

- A coordinator must supply the assigned method paragraph and resolve the
  calibration-lattice policy prospectively; this session did not relax either.
- Restore the missing training raster and feature cache from a permitted source,
  verify provenance and input hashes, then run feature-only leakage canaries and
  the shared buffered-segment evaluator for the assigned lane. Compare with a
  genuinely comparable best and paired uncertainty; keep experiments within budget.
- Check the complete current registry on the surface and final dots, validate the
  exact file by reading it back, and use the separate selector and actual quota
  before any upload. Investigate the portal rejection rather than assuming NaNs
  caused it. Confirm licensing and exact coverage before using new external data.
- Refresh all nine site snapshots and organizer receipts when access permits;
  distinguish source reports, holdout metrics and verified organizer results.

The [prior full review](repo-review-20261028-verified.md) and
[feasibility analysis](protocol-feasibility-20261027.md) contain more detail.
