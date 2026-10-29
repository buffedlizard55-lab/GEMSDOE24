# Repo review — 2026-10-29 (`arena/1d1bdb94-gemsdoe24`)

**Verdict: NO SUBMISSION-AUTHORIZED TIFF · NO NEW EXPERIMENT · SUBMIT: NO.**

This review re-verified the repository's gates and the official competition text. It did not produce a new prediction raster, because the blockers below are unchanged. Every number here is labelled by source. No leaderboard estimate is established.

## 1. Environment and repo integrity (verified here)

| Check | Result | Note |
|---|---|---|
| Checkout | Shallow clone. `git fetch --unshallow` restored history. | Six receipt tests failed on the shallow clone (missing commits `4f251952ee71` etc.). They pass on full history. This is a sandbox artifact, not a repo defect. |
| Full test suite | **663 passed** (full history) | Run 2026-10-29 in this branch. |
| `ruff check .` | All checks passed | |
| Python deps | `requirements.txt` installed into `.venv` (gitignored) | numpy 2.4.6, rasterio 1.4.4 |

## 2. Official sources (checked here)

- Competition problem description: <https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/> (fetched 2026-10-29, 2 chunks).
  - Metric: distance-weighted Tversky, alpha = 0.2, beta = 0.8, triangular kernel R = 300 m (3 px). Quoted text on the page.
  - Submission requirements (quoted): EPSG:32611, 100 m, same bounds as training data, "data outside the bounds is null or nan", single layer, **float32**, values between 0 and 1.
  - The page says the sample "predicts total fault absence."
- Official leaderboard: <https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/> (fetched 2026-10-29; the page has no visible timestamp; chunk 0 read).
  - Visible top rows: **#1 0.4544**, **#2 0.3916**, **#3 0.3911**.
  - **Irregularity:** the owner-cited figures 0.4413 and 0.3195 are not the top of this snapshot. Neither is the current #1 score. Snapshot time is unknown, so the figures cannot be reconciled from here.
- Official reference solution: <https://github.com/drivendataorg/gems-prize-reference-solution> at commit `aebe92f7c8a990f0e3443451b7a825d9afd6336b` (2026-06-16, "initial commit").
  - Output cell: `y_out = np.zeros(...)`, filled with sigmoid probabilities, then `unpatchify`, then written with the labels' CRS and transform. It writes **zeros** over the whole raster, not NaN.
- Competition data: DrivenData's data page requires login. Not accessible from this sandbox. `training_features.tif` is therefore absent (see §5).

## 3. Format and range evidence (local, reproducible)

Files checked with rasterio 1.4.4 and `scripts/preflight_submission.py` (exact bytes; nothing uploaded):

| File | Source | dtype | NaN | value range | Preflight |
|---|---|---|---|---|---|
| `data/bridge/sample_submission.tif` | repo; manifest sha `2176d08e…35cbc` | float32 | 7,111,787 (outside footprint) | 0.0–1.0 finite | FORMAT True · STRICT_RANGE **False** |
| `docs/downloads/gems24-dprf1-…-zeros.tif` | repo | float32 | 0 | 0.0–1.0 | FORMAT True · STRICT_RANGE **True** |
| `docs/downloads/gems24-dprf1-…-nan.tif` | repo | float32 | 7,111,787 | 0.0–1.0 finite | FORMAT True · STRICT_RANGE **False** |
| `gemsdoe32-h33-h33-2-b2-…-zeros.tif` | GitHub `buffedlizard55-lab/GEMSDOE32` @ `0ffda716…` (2026-10-29); sha `c55bafc4…ab6fa9` matches the recorded hash | float32 | 0 | 0.0–1.0 (37,654 ones) | FORMAT True · STRICT_RANGE **True** |

Findings:

1. **The "zeros" variant passes every local range check; the "nan" variant fails the strict whole-array check.** The owner's "Predicted values must be in range [0, 1]" error is consistent with a NaN-outside file under a strict whole-array check. This is **not established**: the portal's exact check is unknown.
2. **The organizer's own sample is NaN-outside and also fails the strict whole-array check.** So either the portal ignores NaN, or the sample would also be rejected. The sample alone cannot settle which.
3. The official text says data outside the bounds "is null or nan." Read literally, "bounds" means the raster extent, which here is the whole 3730 × 3292 grid. Both conventions are then compliant. Zeros-over-the-grid is what the reference notebook writes. The reading is an interpretation, not a portal-verified fact.
4. **Irregularity:** `data/bridge/sample_submission.tif` is **not** the all-absence template the official page describes. Its 60,988 positive pixels are identical in position to `data/bridge/labels.tif` (`np.array_equal` = True). The local "sample" is therefore a copy of the known catalogue labels, not an absence template. Its provenance against the DrivenData original is unverified (the official file is behind login). Do not use it as a blank template.

## 4. Uniqueness gate (project protocol) — still infeasible at standard budgets

`scripts/check_uniqueness_feasibility.py` (run here):

- Registry witness: the spacing-5 lattice `inputs/calibration/13gems_20261001_r13-lattice-s5_v2_nan-outside.tif`, covering 99.87% of the footprint within 3 px (6,649 uncovered pixels).
- Exact pigeonhole bound: any candidate with *n* distinct in-footprint dots overlaps the lattice in at least *n* − 6,649 dots.
  - 37,654 dots: minimum overlap **82.34%** > 70% → `STOP_IMPOSSIBLE_BUDGET`, exit 2.
  - 44,090 dots: minimum overlap **84.92%** → exit 2.
  - Largest budget not ruled out by this bound: **22,163** dots.
- Scope: this is one necessary gate, not a complete registry audit. It is an arithmetic consequence of the owner's rule plus a registry lattice. It is not a bug and must not be evaded by shrinking, shifting or exempting a file.

**Decision needed from the owner (cannot be resolved by code):** does the 70%/3-px rule apply to a registry raster that is itself a space-filling lattice? If yes, no candidate above ~22k dots can be unique, and the 37k-dot leaders cannot be unique. If the lattice is out of scope, the registry must be redefined in writing before any lane runs.

## 5. Why nothing new was generated

- `data/training_features.tif` (the competition's feature stack) is absent. Access needs DrivenData login; the sandbox allows only github, codeload, api.github, registry.npmjs, pypi and files.pythonhosted.
- No assigned single method paragraph exists in the owner brief. Inventing one would be a private lane, which the protocol forbids.
- The uniqueness gate fails at standard budgets (§4).
- Without the feature stack, no holdout DTI can be measured. Any "estimated score" would be a projection and is therefore not written.

## 6. The 0.2778 question (what is and is not established)

- **Established:** the GEMSDOE32 file `gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif` exists at the GitHub repo HEAD checked, its SHA-256 matches the recorded hash, and it is a binary float32 file (37,654 ones, zeros elsewhere) that passes strict range and format checks.
- **Established (official text):** the metric weights FN 4× more than FP (beta 0.8 vs alpha 0.2). Under the distance-weighted definition, a prediction within 300 m of a true fault earns kernel-weighted credit, and a false positive is penalized only by its distance from a true fault.
- **Research hypothesis (not verified):** a dense binary set of ~37k one-pixel dots spread along the catalogue-adjacent corridors gains recall at low FP cost under alpha 0.2. Whether that caused 0.2778 depends on the hidden labels, which are not public. This is a mechanism to test, not a finding.
- **Not established:** that 0.2778 is an organizer score. The page has no receipt. It is **OWNER-REPORTED / UNVERIFIED**.
- Beating 0.2778 would need a new validated method. The current gate blocks every 37k-dot variant of this family.

## 7. Irregularities flagged for review

1. The local `data/bridge/sample_submission.tif` contains known-catalogue positives, contrary to the official "total fault absence" description (§3.4).
2. Owner-cited leaderboard figures (0.4413, 0.3195) differ from the official snapshot top (0.4544).
3. Six receipt tests fail on a shallow clone (sandbox artifact; §1).
4. The owner's "[0,1]" rejection has no confirmed cause; NaN-outside and the strict range check disagree with the sample (§3.1–3.2).
5. The 70%/3-px rule and a space-filling registry lattice are jointly infeasible (§4). The owner must decide.

## 8. Next steps (in priority order)

1. **Owner decision:** rule on the lattice registry question in writing (§4). Nothing else can unlock a unique submission.
2. **Owner action:** download `training_features.tif` and `sample_submission.tif` from the DrivenData data page (login), and record their SHA-256 so the local bridge copy can be checked against the original.
3. **Owner action, one test:** submit one **zeros** file and one **NaN** file to the portal as research receipts, noting that a slot is consumed. This is the only way to settle the [0,1] question. Do not submit without the owner's explicit approval.
4. Once the feature stack exists, run the frozen holdout (`scripts/evaluate_holdout.py`) on a single prospectively specified lane, with the leakage canary, before any uniqueness check.

## 9. Sources and reproducibility

- Preflight: `.venv/bin/python scripts/preflight_submission.py <file>` (no upload).
- Feasibility: `.venv/bin/python scripts/check_uniqueness_feasibility.py --dot-budget 37654` (exit 2).
- Run card: `evidence/session_1d1bdb94_20261029_run_card.json`.
