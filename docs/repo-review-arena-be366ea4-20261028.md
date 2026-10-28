# Arena review — historical champion overlap audit (2026-10-28)

## Decision

**No candidate is cleared to submit. No new TIFF, geology experiment, competition slot, or organizer score was created in this review.** In addition to the earlier e5 research TIFF (HOLDOUT-DTI 0.003802 [0.002061, 0.005718]), current `main` contains the already-generated VENTRAD (0.122343 [0.111099, 0.133661]) and Blind Upwell (0.068821 [0.058112, 0.079982]) candidates. All values are internal HOLDOUT-DTI on `gems-segment-pooled-v1` with 60,988 withheld positives, not organizer scores. Both newer values are below the repository's recorded 0.13000 comparable baseline; the recorded local point-best is 0.16606. All remain SUBMIT: NO.

## Three review passes

1. **Evidence and scope.** Reopened the nine exact historical champion TIFFs named in the existing pinned record, fetched at immutable GitHub commits, verified each recorded SHA-256, and read them through the shared raster/mask code. Compared final binary dots for the earlier e5, VENTRAD, and Blind Upwell files with each reference using the shared directed 3-pixel overlap metric. No exact dot-mask alias was found. Maximum candidate-dot overlaps were **0.24328594 (e5) vs GEMSDOE24**, **0.05932877 (VENTRAD) vs GEMSDOE27**, and **0.29529187 (Blind Upwell) vs GEMSDOE27**—all below 0.70 for this nine-file comparison. It does not cover current repository heads, all artifacts in those repositories, the 167-alias registry, other competitors, or pre-placement correlation for Blind Upwell. VENTRAD's run card separately records maximum absolute rank correlation 0.125639 but 0.998171 final-dot overlap with the spacing-5 lattice, so it fails the user's literal overlap stop rule.
2. **Implementation and failure behavior.** Added a repeatable audit command and machine-readable receipts for each existing generated candidate, plus offline tests for nine-site enumeration, pinned hashes, threshold behavior, exact-mask duplicates, and immutable source URLs. The generated summary page now presents the per-site overlaps and score provenance for the three files; the older-e5 featured-card renderer validates its receipt fail-closed. Tampered scope claims, hashes, or per-site results block rendering.
3. **Independent verification and user-facing status.** Reran the audits sequentially after verifying candidate-to-receipt identity. The current research-download page now labels each artifact's holdout and submit state, includes the per-site nine-file comparison for all three candidates, and links to all machine-readable receipts. It explicitly limits the comparison to historical files, labels owner score claims unverified, and retains **SUBMIT: NO**. No leaderboard estimate or new geological claim was added.

## Nine-file result — earlier e5 candidate

| Historical artifact | Candidate dots within 3 px of e5 | Score provenance |
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

| Existing generated candidate | Candidate-dot maximum among the nine files | Max site | Exact dot-mask alias | Submission state |
|---|---:|---|---|---|
| Earlier e5 research TIFF | 24.3286% | GEMSDOE24 | No | DO NOT SUBMIT; HOLDOUT-DTI 0.003802 |
| VENTRAD | 5.9329% | GEMSDOE27 | No | DO NOT SUBMIT; HOLDOUT-DTI 0.122343; lattice overlap 0.998171 |
| Blind Upwell | 29.5292% | GEMSDOE27 | No | DO NOT SUBMIT; HOLDOUT-DTI 0.068821; full registry not rerun |

The 0.2778 figure for GEMSDOE32 is still only an owner report. The repository's prior exact set-algebra review describes H33-B2 as a deletion-only 37,654-dot subset of D2.8, removing 6,436 dots within 200 m of the catalogue; the hidden-fault credit of those removed dots is unknown, so this does not establish why the reported score changed. These overlap audits compare final masks to nine historical TIFFs; they do not evaluate or causally explain GEMSDOE32's model, data, or score, infer a performance advantage, or forecast a leaderboard result. See the existing [`research review`](research.html) for the B2 algebra, the original [`nine-site summaries and download links`](historical-champions.html), and the new per-site candidate comparison in [`executive-summary-unique.html`](executive-summary-unique.html).

## Artifacts and verification

- Repeatable command: `python scripts/audit_historical_champion_overlap.py`
- Earlier e5 receipt: [`evidence/historical_champion_overlap_20261028.json`](../evidence/historical_champion_overlap_20261028.json)
- VENTRAD receipt: [`evidence/historical_champion_overlap_ventrad_20261028.json`](../evidence/historical_champion_overlap_ventrad_20261028.json)
- Blind Upwell receipt: [`evidence/historical_champion_overlap_blind_upwell_20261028.json`](../evidence/historical_champion_overlap_blind_upwell_20261028.json)
- Published receipt copies: [`data/historical_champion_overlap_20261028.json`](data/historical_champion_overlap_20261028.json), [`data/historical_champion_overlap_ventrad_20261028.json`](data/historical_champion_overlap_ventrad_20261028.json), [`data/historical_champion_overlap_blind_upwell_20261028.json`](data/historical_champion_overlap_blind_upwell_20261028.json)
- Builder: `scripts/build_site.py` copies all three receipts into the published data directory and validates the earlier-e5 featured-card receipt against its run card, pinned reference URLs/hashes, per-site values, maximum, aliases, and explicit non-authorization. The full test suite cross-checks the published VENTRAD/Blind Upwell matrix cells against their evidence JSON.
- Tests: **579 passed** with the full repository test suite after integrating current `main`. `ruff check .`, `ruff format --check .`, and `git diff --check` pass.

## Not resolved / next gates

- The 69-file local overlap receipt and this nine-historical-file check are not a full registry/current-head/pre-placement-surface uniqueness audit. Do not call the retained TIFF unique in the unrestricted sense or eligible to submit.
- The assigned single-method paragraph and separate weekly-slot selector/allowance remain absent. No slot is authorized.
- The present internal HOLDOUT-DTI is extremely low and not an organizer score. No live leaderboard access or organizer receipt exists.
- No geology experiment or hypothesis was added here because no assigned method paragraph authorizes a lane. The existing ranked, prospective hypothesis queue—with physical layers, missing-fault rationale, mimics, and source-access limits—is in [`portfolio-hypotheses-20261026.md`](portfolio-hypotheses-20261026.md) and the dated [`portfolio review`](portfolio-review-20261026.md); those recorded official-source claims were not freshly re-verified in this overlap-only audit.
- Do not restore `stash@{0}` wholesale; it predates the sync that brought merged PR #87 to this branch and overlaps its implementation.
