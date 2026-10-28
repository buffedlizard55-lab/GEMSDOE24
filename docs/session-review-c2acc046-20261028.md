# Session review — 2026-10-28 (branch `arena/c2acc046-gemsdoe24`)

## Executive decision

**NO NEW TIFF · NO EXPERIMENT · NO COMPETITION SLOT · SUBMIT: NO for every file.**

No file in this session is approved for download-and-submit. The reasons are blockers that
I could check directly. They are not code failures. The full test suite passes and the linter is clean.

## What was verified in this session (reproducible)

| Check | Command / source | Result |
| --- | --- | --- |
| Git history | `git rev-parse --is-shallow-repository` | Was `true`; `git fetch --unshallow origin` made it `false`. Required: 6 tests fail on a shallow clone. |
| Full test suite | `.venv/bin/python -m pytest -q` | **578 passed** (about 4m10s) |
| Lint | `.venv/bin/ruff check .` | **All checks passed** |
| Uniqueness feasibility gate | `.venv/bin/python scripts/check_uniqueness_feasibility.py --dot-budget 37654 --dot-budget 44090` | **exit 2**. 37,654 dots: minimum overlap **82.34%** (limit 70%). 44,090 dots: minimum overlap **84.92%**. Largest budget not ruled out by this bound: **22,163** dots. This is a necessary geometric bound only, not a score or a registry audit. |
| Official rules | <https://docs.nlr.gov/docs/fy26osti/96647.pdf> (NLR GEMS Prize Official Rules, September 2026), read directly, Sections 1.1 and 3.2 | Quoted below. |

Official rules statements, verbatim (Section 3.2 "Process Overview"):
- "You must submit a single GeoTIFF with a single raster layer at 100-meter resolution containing your model's predictions of fault locations for the entirety of the GeoDAWN study area."
- "You can make multiple submissions, subject to the limits specified on the competition website (three submissions per week)."
- "Using the distance-weighted Tversky index metric published on the competition website, judges will score a user's or a team's chosen submission against ground-truth data."
- Generative-AI use must be disclosed in the narrative.

The rules do **not** contain a 70% overlap gate, a [0, 1] range statement, or a NaN convention. The 70% overlap rule and the lattice comparison come from the owner's parallel-run protocol and the repository's own gate, not from the rules PDF. This is recorded as an irregularity below.

Competition pages cited by the owner, **not fetched here** (manual review): <https://www.drivendata.org/competitions/306/competition-doe-gems/>, <https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/>, <https://github.com/drivendataorg/gems-prize-reference-solution>. The sandbox only reaches GitHub, npm and PyPI, so DrivenData, Dropbox and the USGS/ScienceBase sources could not be retrieved from here.

## Why 0.2778 (GEMSDOE32, H33-B2): what the repository's own evidence shows

Source record: `docs/data/historical_champions_20261028.json`, row 6.

- Owner-reported score: **0.2778**, status **OWNER-REPORTED / UNVERIFIED**. No organizer receipt is attached (`organizer_confirmed_scores: []`). No holdout result or leaderboard estimate exists (`holdout_dti: null`, `leaderboard_estimate: null`).
- Local pixel forensics recorded in that row: the file is "exactly the H27-4/D2.8 emission minus dots within 2 px of the public catalogue; 0 dots added" (cited as `evidence/priority_review_20261025.json`).
- Lattice overlap within 3 px: **99.92%** (`lattice_overlap_within_3px: 0.99915`). Literal uniqueness: **FAIL**.
- Its own format validator: `format_valid: true`, `ok_to_upload: false`, `submission_authorized: false`.

**Interpretation (a hypothesis, not a verified mechanism).** The file is a sibling of the D2.8 family (0.26 to 0.27 owner-reported), with dots that sit near the public fault catalogue removed. If the leaderboard rewards precision on faults that the public catalogue does not already contain, deleting catalogue-adjacent dots can raise the score. That mechanism has **not** been tested: no holdout was replayed, and no leaderboard receipt confirms the number. Its copy-like overlap with the registry also means it cannot be submitted under this repository's rules.

## Can we beat 0.2778? Not validated in this session

Scoring above 0.2778 needs a new, unrelated method that is validated on the spatially-blocked holdout before a slot is used. Three blockers prevent that here:

1. **No training data.** `data/training_features.tif` is absent (it is git-ignored and must come from the DrivenData login). `data/bridge/` holds only `labels.tif`, `existing_faults.tif` and `sample_submission.tif`. Without the feature stack, no holdout can be run faithfully. The restore path is `scripts/restore_data.py`.
2. **No assigned method lane.** The parallel-run protocol refers to "the single method paragraph below". No such paragraph is in the prompt, so no lane is assigned and no experiment can be attributed to one.
3. **Standard dot budgets fail the lattice gate.** 37,654 and 44,090 dots are impossible under the repository's 70% rule (see the feasibility table above). Shrinking the budget, moving dots or excluding the comparator to pass would be evasion, and the protocol forbids it.

## The "Predicted values must be in range [0, 1]" error: still unexplained

- `evidence/format_forensics.json` (a 2026-10-02 scan of 167 unique rasters from the owner's sibling repositories) found **no** raster with a value outside [0, 1] inside the scoring footprint. Its only anomalies were NaN inside the footprint in three early `5GEMSDOE` files.
- The organizer example mirror `data/bridge/sample_submission.tif` is also NaN outside the footprint (7,111,787 NaN cells, verified in `docs/repo-review-20261028-verified.md`). So NaN-outside alone is probably **not** the cause. The portal's actual validator behaviour is still unknown.
- Lowest-risk option for a future file: no NaN anywhere (the `-zeros.tif` convention). This is a hypothesis, not a fix.
- **Action for the owner:** copy the exact portal error page (or the validator detail, if the form shows one) into the repository. It is needed to close this item.

## Irregularities flagged for review

1. The owner's parallel-run protocol refers to a method paragraph that is absent from the prompt. Its numbered "[0.90]", "[70%]" and "[3]" placeholders were left as written.
2. The 70% overlap rule and the "[0, 1]" check are not in the official rules PDF. They are repository and protocol conventions, and should be labelled that way in any external message.
3. Leaderboard values 0.4413, 0.3195 and 0.2778 are **OWNER-REPORTED / UNVERIFIED**. None has an artifact-linked organizer receipt in this repository.
4. The prompt is repeated many times in the request and contains two conflicting submission-selection instructions (generate and submit now, and "do not pick submissions"). This session follows the protocol: no selection was made.
5. The README is over 3,500 lines of dated, partly superseded notes (already flagged in `docs/repo-review-20261028-verified.md`).
6. Open PRs with overlapping work (not merged or changed here): #91, #90, #84, #70, #61, #50, #43, #40, #7.

## What is needed to make progress (for the owner)

1. **Assign the method paragraph** for the parallel-run lane (or confirm that no new lane is to be run).
2. **Place `training_features.tif`** into `data/` on a machine with DrivenData access, then run `python scripts/prepare_data.py` and `python scripts/restore_data.py`. This cannot be done from the sandbox.
3. **Decide the lattice rule in writing.** At the standard budgets it cannot pass. Options: treat the retained calibration lattice as a comparator, or accept a smaller dot budget (at most 22,163 dots are not ruled out).
4. **Send the exact portal error text** (from the submission page) so the [0, 1] cause can be tested.
5. Once the above are in place, the next session should run one pre-registered experiment against the holdout, with the uniqueness gate checked first.

## Run card (negative, documentation only)

```json
{
  "session": "arena/c2acc046-gemsdoe24",
  "date_utc": "2026-10-28",
  "hypothesis": "None tested. Repository review plus a check of the H33-B2 (0.2778) record and the official rules.",
  "mechanism": "Not applicable. Verified: test suite (578 passed), ruff clean, uniqueness feasibility exit 2 at 37,654 and 44,090 dots (minimum overlap 82.34% and 84.92%).",
  "named_non_fault_process": "Not applicable.",
  "holdout_dti": null,
  "holdout_ci_95": null,
  "leaderboard_estimate": null,
  "correlation_overlap_vs_registry": "Not computed for a new raster. Repository record for H33-B2: lattice overlap within 3 px 0.99915.",
  "raster_sha256": null,
  "validator_output": "Not run on a new raster. Existing repo record for H33-B2: format_valid true, ok_to_upload false, submission_authorized false.",
  "submission_name": null,
  "submission_note": null,
  "verdict": "negative",
  "new_tiffs": 0,
  "new_experiments": 0,
  "competition_slots_used": 0
}
```
