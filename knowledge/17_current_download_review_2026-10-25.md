# Current download review — three passes

Scope: frozen evidence review and packaging validation, not a new lane or experiment.
The owner prompt is already preserved in README and `knowledge/owner_brief_2026-10-25.md`.

## Pass 1 — implementation and exact-file check

Added `scripts/verify_current_download.py` using shared `check_variants`, not a
private validator. Reopened the current first-screen TIFF: SHA-256 matches,
single-band float32, EPSG:32611, shape 3730 × 3292, exact template transform,
no NaN anywhere, all values in [0,1]. Receipt:
`evidence/current_download_revalidation.json`. No TIFF was generated or copied.
No new holdout measurement, novelty claim, or competition submission was made.

## Pass 2 — evidence and edge cases

Added seven tests for the real file and altered authorization, verdict, hash,
path traversal, excessive note length, and missing receipt. Compared every
recorded validator field against fresh output. Corrected unsupported hidden-set
causal/optimality assertions in the H33 and CON notes. Corrected the site's
contradictory "catalogue-independent" description of its visible-fault-guided
candidate and removed a misleading blanket canary certification: the frozen
card lists K and Th/K AUCs, not a complete per-transform provenance audit.
No historical experiment receipt was rewritten. Historical build scripts and
other archived reports are not promotion authority.

## Pass 3 — regression and remaining requirements

Full suite: 188 passed after fetching full Git history for immutable MTR source
verification. Changed-file Ruff checks and `git diff --check` passed.
Environment required a fresh ignored virtualenv; installed available dependency
versions, not a claim of reproducing the future-dated exact lock versions.
Initial full-suite collection lacked pandas; installed it. Subsequent MTR test
failed on shallow history; fetched history and reran successfully, without
weakening the verifier.

The requested new unique submit-ready file is NOT delivered: the three recorded
unique experiments already ended negative, novelty failed, and no explicit
single-method assignment was supplied. Standing instructions forbid retuning
stopped lanes. The existing research-only download is accessible, but range
validity is not submission authorization. It also differs from the official
NaN-outside convention; zeros-outside is a portal-compatibility variant, not
proof of organizer acceptance.

Next session: prospectively resolve lane/registry scope, then test the ranked
incremental fold-local fusion hypothesis with bounded memory and training-only
normalization. Require all feature canaries, surface checks before placement,
final-dot checks, comparable HOLDOUT-DTI improvement and exact-file nuisance
validation before any selector decision. Restore/cache missing registry bytes
before claiming novelty. Do not equate geological plausibility with vent detection.

No official sites outside the allowed network hosts were freshly verified.
External scores remain owner-reported; official source URLs in the analysis are
manual-review pointers. PR #7 remains conflicting and untouched; do not merge
its stale competing work incidentally.
