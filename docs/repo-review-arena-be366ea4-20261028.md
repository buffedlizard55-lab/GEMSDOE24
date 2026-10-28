# Arena review — historical champion overlap audit (2026-10-28)

## Decision

**Retain the existing research TIFF for download only; SUBMIT: NO. No new TIFF, geological experiment, competition slot, or score claim was created in this review.** The already-retained candidate is `24gems-interior-offlattice-geothermal-20261028T164358Z-e5a3c34b27db-zeros.tif` (SHA-256 `379bf97792355bb48acec703939537a62bb8492705997e043c235bd9029c44db`). Its internal HOLDOUT-DTI remains 0.003802 (95% CI 0.002061–0.005718; `gems-segment-pooled-v1`, 60,988 withheld positives); it is not organizer-confirmed and does not support a leaderboard estimate.

## Three review passes

1. **Evidence and scope.** Reopened the nine exact historical champion TIFFs named in the existing pinned record, fetched at immutable GitHub commits, verified each recorded SHA-256, and read them through the shared raster/mask code. Compared the retained candidate's final binary dots with each reference using the shared directed 3-pixel overlap metric. No exact dot-mask alias was found. Maximum candidate-dot overlap was **0.24328593996840442 against GEMSDOE24**, below the 0.70 stop threshold. This result applies to these nine historical files only; it does not cover current repository heads, all artifacts in those repositories, the 167-alias registry, other competitors, or the candidate's pre-placement continuous surface/rank correlation.
2. **Implementation and failure behavior.** Added a repeatable audit command, a machine-readable receipt, and offline tests for nine-site enumeration, pinned hashes, the 0.70 boundary, exact-mask duplicates, and immutable source URLs. The site builder now consumes the receipt fail-closed, cross-checks its pinned hashes/URLs against the historical artifact record, and displays the per-site overlaps and score provenance on the landing page and submission guide. A tampered scope claim or per-site result blocks the build.
3. **Independent verification and user-facing status.** Reran the nine-file audit from the saved pinned refs, regenerated the site, and checked that the download remains explicitly marked **SUBMIT: NO** and **NOT ESTIMABLE**. The page says that the nine-file result is not full-registry uniqueness, and labels every historical score as owner-reported/unverified. No leaderboard estimate or new geological claim was added.

## Nine-file result

| Historical artifact | Candidate dots within 3 px | Score provenance |
|---|---:|---|
| GEMSDOE24 | 24.33% | owner-reported / unverified (0.2477) |
| GEMSDOE27 | 24.33% | owner-reported / unverified (0.2449) |
| GEMSDOE25 | 22.43% | owner-reported / unverified (0.26) |
| GEMSDOE30 | 22.43% | owner-reported / unverified (0.26) |
| GEMSDOE33 | 20.92% | owner-reported / unverified (0.2632) |
| GEMSDOE31 | 19.53% | owner-reported / unverified (0.2708) |
| GEMSDOE28 | 19.08% | owner-reported / unverified (0.271) |
| GEMSDOE32 | 17.06% | owner-reported / unverified (0.2778) |
| GEMSDOE36 | 17.06% | owner-reported / unverified (0.275) |

The 0.2778 figure for GEMSDOE32 is still only an owner report. The repository's prior exact set-algebra review describes H33-B2 as a deletion-only 37,654-dot subset of D2.8, removing 6,436 dots within 200 m of the catalogue; the hidden-fault credit of those removed dots is unknown, so this does not establish why the reported score changed. This audit compares the candidate mask to one historical final TIFF; it does not evaluate or causally explain GEMSDOE32's model, data, or score, infer a performance advantage, or forecast a leaderboard result. See the existing [`research review`](research.html) for the B2 algebra, the original [`nine-site summaries and download links`](historical-champions.html), and the new per-site candidate comparison at the top of [`executive-summary.html`](executive-summary.html).

## Artifacts and verification

- Repeatable command: `python scripts/audit_historical_champion_overlap.py`
- Full receipt: [`evidence/historical_champion_overlap_20261028.json`](../evidence/historical_champion_overlap_20261028.json)
- Published receipt: [`data/historical_champion_overlap_20261028.json`](data/historical_champion_overlap_20261028.json)
- Builder: `scripts/build_site.py`; it verifies candidate SHA, comparison count and identity, pinned reference URLs/hashes, measured maximum, exact aliases, and explicit non-authorization before rendering.
- Tests: **578 passed** with the full repository test suite. `ruff check .`, `ruff format --check .`, and `git diff --check` pass.

## Not resolved / next gates

- The 69-file local overlap receipt and this nine-historical-file check are not a full registry/current-head/pre-placement-surface uniqueness audit. Do not call the retained TIFF unique in the unrestricted sense or eligible to submit.
- The assigned single-method paragraph and separate weekly-slot selector/allowance remain absent. No slot is authorized.
- The present internal HOLDOUT-DTI is extremely low and not an organizer score. No live leaderboard access or organizer receipt exists.
- No geology experiment or hypothesis was added here because no assigned method paragraph authorizes a lane. The existing ranked, prospective hypothesis queue—with physical layers, missing-fault rationale, mimics, and source-access limits—is in [`portfolio-hypotheses-20261026.md`](portfolio-hypotheses-20261026.md) and the dated [`portfolio review`](portfolio-review-20261026.md); those recorded official-source claims were not freshly re-verified in this overlap-only audit.
- Do not restore `stash@{0}` wholesale; it predates the sync that brought merged PR #87 to this branch and overlaps its implementation.
