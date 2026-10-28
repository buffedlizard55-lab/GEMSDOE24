# Repository review — 2026-10-28 (verified checks, branch `arena/9e77df06-gemsdoe24`)

## Executive decision

**NO NEW TIFF · NO EXPERIMENT · NO COMPETITION SLOT · DO NOT SUBMIT ANY FILE ON THE BASIS OF THIS REVIEW.**

The repository is healthy in code terms: the full test suite passes and the linter is clean. It is not yet a source of a
submission that can be justified as higher-scoring. The reasons are protocol and evidence gaps, listed below, not code failures.
Nothing in this review is a leaderboard estimate.

## What was verified in this session (reproducible commands)

| Check | Command | Result |
| --- | --- | --- |
| Full test suite (after restoring full git history) | `.venv/bin/python -m pytest -q` | **552 passed** (about 3m45s) |
| Lint | `.venv/bin/ruff check .` | **All checks passed** |
| Shallow-clone effect | `git fetch --unshallow origin` | Before this, **6 tests failed** (5 files) because they need the original commit objects; after it, all pass. CI already uses `fetch-depth: 0`. |
| Downloaded GeoTIFFs under `docs/downloads/` | `rasterio` read-back | 57 files: all float32, EPSG:32611, all finite values within **[0, 1]**. 29 `-zeros.tif` files have no NaN; 24 `-nan.tif` files have NaN outside the footprint; 4 `-allfinite.tif` files have no NaN. |
| Organizer example mirror `data/bridge/sample_submission.tif` | `rasterio` read-back | EPSG:32611, shape (3730, 3292), float32, values in [0, 1], **7,111,787 NaN cells** (NaN outside footprint). |

## Official sources (for manual review)

- NLR-hosted GEMS Prize Official Rules, read directly this session: <https://docs.nlr.gov/docs/fy26osti/96647.pdf>.
  Verified statements (Section 3.2, "Submission"): a single GeoTIFF with a single raster layer at **100-meter** resolution
  covering the entire GeoDAWN study area; a distance-weighted Tversky index metric; a limit of **three submissions per week**.
  The rules also require disclosure of generative-AI use in the submission narrative.
- Competition pages cited by the owner (not fetched here; manual review): <https://www.drivendata.org/competitions/306/competition-doe-gems/>,
  <https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/>, <https://github.com/drivendataorg/gems-prize-reference-solution>.
- Projection reference for the CRS in use: <https://epsg.io/32611> (UTM zone 11N).

## Findings and irregularities (flagged for review)

1. **The "Predicted values must be in range [0, 1]" cause is not established.** The repo's notes attribute it to NaN outside the footprint.
   But the organizer example mirror also uses NaN outside the footprint and is in range. So NaN alone is probably not the cause, and
   the repo should not assume it is. Open question: what the portal's validator actually reads (nodata handling, dtype, or a different file).
   The `-zeros.tif` files are the lowest-risk option because they contain no NaN at all.
2. **The leaderboard snapshots disagree.** The owner prompt cites 0.4413, 0.3195 and 0.2778. None is artifact-linked to an organizer receipt here. Treat all as **OWNER-REPORTED / UNVERIFIED**.
3. **Protocol blockers remain.** The active brief has no assigned parallel-run method paragraph (a method lane must be assigned before a new experiment).
   The retained calibration-lattice comparator makes the standard 37,654-dot budget fail the literal 70% overlap gate (lower bound 82.34%, per
   `scripts/check_uniqueness_feasibility.py`). These are policy decisions for the owner, not code defects.
4. **Local holdout numbers are not replayed here.** The repo's HOLDOUT-DTI values (for example S3DEP1 0.166060, KPL-36 0.17010 as an external record)
   are source-recorded. The raw training raster and feature cache are absent in a fresh clone, so no new holdout was run.
5. **README length.** The README is about 3,500 lines, with dated sections that partly supersede each other. The active brief and this file are the
   current entry points; consider moving historical sections to `knowledge/archive/`.
6. **Branch naming.** The same-day review on `main` (`docs/repo-review-20261028.md`) was written for branch `arena/31593f7c-gemsdoe24`. This session's branch is `arena/9e77df06-gemsdoe24`. Both are recorded here; neither is renamed.

## What should happen next (in priority order)

1. Owner decision: assign the parallel-run method paragraph, and decide in writing whether the retained calibration lattice counts as a novelty comparator.
2. Determine the portal's real validator behaviour. Ask the organizer or check the submission page for an error detail, rather than guessing. Test candidate files by reading them back, not by assumption.
3. Restore the training raster and cached feature stack from an allowed source (see `scripts/restore_data.py`), record provenance separately from hashes, and rerun the holdout only for an assigned method.
4. Keep CI on full history (`fetch-depth: 0`); add a guard that fails with a clear message when history is shallow.
5. Shorten the README to a current-status page with links to the active brief.

## Run card (documentation-only negative result)

```json
{
  "hypothesis": "No new geological hypothesis tested in this review; method lane unassigned.",
  "mechanism": "Repository review: test suite, lint, read-back of existing GeoTIFFs and organizer example mirror.",
  "named_non_fault_mimic": "Not applicable; no prediction raster generated.",
  "holdout_dti": null,
  "holdout_ci95": null,
  "holdout_status": "NOT RUN; no new experiment",
  "correlation_or_overlap_vs_registry": "Not computed for a new candidate; no candidate generated.",
  "raster_sha256": null,
  "validator_output": "Existing files only: 57 downloads read back float32 EPSG:32611, values within [0,1]; 24 contain NaN outside footprint. Organizer mirror sample_submission.tif also has NaN outside footprint and values within [0,1].",
  "submission_name": null,
  "submission_note": "No candidate generated; no submission authorized.",
  "verdict": "negative"
}
```
