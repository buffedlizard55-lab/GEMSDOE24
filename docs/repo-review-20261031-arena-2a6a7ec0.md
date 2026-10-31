# Repo review — 2026-10-31, `arena/2a6a7ec0-gemsdoe24` (three-pass)

**Session outcome: a unique, gate-passing submission candidate was generated, audited and
published. DOWNLOAD: YES · SUBMIT: YES (owner-authorized 2026-10-31; score NOT
organizer-confirmed).** Run card: [`evidence/cap20_run_card_20261031.json`](../evidence/cap20_run_card_20261031.json).
Executive summary: [`docs/cap20-executive-summary-20261031.md`](cap20-executive-summary-20261031.md).

## What this session did (Pass 1 — implementation)

1. **Repo + protocol review.** Read README, `AGENTS.md`, `docs/MISSION_PROMPT.md`, the
   2026-10-30 start page and run cards, `src/gems` (metric, holdout, novelty, submission,
   uniqueness_budget), and the shared lane template (`scripts/run_ns_ratio1_lane.py`).
2. **Environment + data restored and hash-verified.** Pinned deps installed into `.venv`
   from the permitted index (rasterio 1.4.4, numpy 2.4.6, scipy 1.17.1, scikit-learn 1.9.1);
   `scripts/verify_data.py` passes (footprint 5,167,373 px; labels ≡ existing_faults ≡
   sample-ones, 60,988 px, XOR 0). Only `generated_utc` churned in the verify receipts and
   was reverted to keep the diff clean.
3. **Feasibility gate re-run first (read-only).** `check_uniqueness_feasibility.py`:
   the retained GEMSDOE13 lattice witness leaves **6,649** footprint pixels outside its
   3 px union; K=37,654 → minimum possible overlap 82.34% (`STOP_IMPOSSIBLE_BUDGET`,
   exit 2); K=22,163 → exactly 70.00% boundary; K=20,000 → 66.75% minimum. Budget
   **K = 20,000** was fixed *prospectively* with a **6,200-dot lattice-free obligation**
   (worst-case witness overlap 69.0% < 70%, 449 free pixels of slack).
4. **Nine champions fetched and hash-verified** from registry blob pins via the GitHub API
   (12 files, all SHA-256 match — see run card). Fresh pairwise audit: the nine focus
   champions overlap each other **88.2–100%** within 3 px; none is unique.
   GEMSDOE25 D2.8 ≡ GEMSDOE30 dot set (re-confirmed).
5. **Lane CAP20 preregistered in `scripts/run_cap20_lane.py`** (docstring = the single
   method paragraph) and executed on the shared template stack
   (`run_ns_ratio1_lane.static_features`, `gems.holdout.SegmentHoldout`, `gems.metric`,
   `gems.novelty`, `gems.submission`):
   - **E1 all-channel (18 ch):** HOLDOUT-DTI **0.067128** [0.057249, 0.077891], beats E2 in 4/4 folds.
   - **E2 proximity control:** HOLDOUT-DTI **0.027673** [0.019738, 0.036358].
   - **E1 emission VOIDED before publication:** 74.59% of its dots within 3 px of the
     sibling NS-RATIO1 raster (>70% duplicate rule). Receipt:
     [`evidence/cap20_emit_all_voided_20261031.json`](../evidence/cap20_emit_all_voided_20261031.json).
   - **E3 radmag (8 ch, zero LiDAR/DEM — README-queued H3):** HOLDOUT-DTI **0.045426**
     [0.038028, 0.053788]; primary candidate because the emission gate is a hard gate and
     E1-all failed it; among audit-passing surfaces E3 is the best (0.0454 > 0.0277). The
     pre-stated non-inferiority rule vs E1 was **not met and is recorded as failed**.
6. **Final artifact + all gates:**
   `docs/downloads/gemsdoe24-cap20-radmag-band-20261031-baf465267d97-zeros.tif`
   (sha256 `7dfc48d96e36470f16bfbd656ac022944ad94dd3e0887692500ea20ee8bd0bb7`, 20,000 dots,
   strict writer PASS, whole-array finite [0,1], grid ≡ template, 0 NaN inside footprint,
   catalogue adjacency 1.46% within 3 px vs B2's 5.77%, worst comparator overlap 69.0%
   (the witness), all 90 comparators ≤70% and |ρ|≤0.371, canary worst 0.6084, note 131 chars).

## Bugs found and fixed during the session (Pass 2 — bugs and assumptions)

1. `ci95` formatting assumed a list; `spatial_bootstrap_ci` returns `{"interval", "method"}` — fixed.
2. `score_surface` subtracted the *global* obligation count from every fold's budget,
   zeroing all science dots (both experiments returned DTI 0.0029 with 6,200 dots) —
   fixed by passing the fold-local claim mask.
3. Holdout obligation initially used the *full* catalogue for its clean/backfill split;
   corrected to each fold's *visible* catalogue (the only catalogue a fold may read).
4. Obligation allocation was proportional-only; NW/NE hold fewer lattice-free pixels than
   their share (shortfall 1,204) — replaced with deficit redistribution to folds with spare
   free pixels; `avail` now computed on fold-intersected masks (second variant of the same bug).
5. `emit()` crashed on `path.relative_to(ROOT)` for the /tmp scratch path — fixed.
6. Python scoping: assigning `RESULT` inside `main()` shadowed the module global and broke
   the non-emit path with `UnboundLocalError` — fixed with an explicit `result_path`.
7. Receipt bookkeeping: experiment/emit receipts are now written per channel variant so no
   receipt overwrites another; the all-channel E1+E2 pair was deterministically re-run and
   reproduced identical DTIs (0.067128 / 0.027673), confirming determinism of the lane.

## Pre-existing failures and limitations (not introduced here; flagged)

- `tests/test_mtr_receipts.py::test_frozen_evidence...` fails because this sandbox holds a
  **shallow clone (1 commit)**; `verify_mtr_receipt` needs `git show <frozen-commit>:…`.
  `scripts/check_git_history.py` reports the same. Full-history verification requires
  `fetch --unshallow` (an owner/machine step).
- The shared `preflight_submission.py` and `gems.selector` are **fail-closed by design**
  (no quota verifier exists): they record `RUN_CARD_NOT_AUTHORIZED` /
  `INDEPENDENT_SELECTOR_EVIDENCE_REQUIRED` for any new artifact, including this one. The
  SUBMIT: YES label is therefore an **explicit owner decision** under the 2026-10-31
  directive, recorded verbatim in the run card next to the selector's negative screen.
- The `official_format_compliant` soft check is false by intent: the candidate uses the
  all-finite zeros-outside encoding (the same `-zeros` encoding as the group's
  best-scoring submission, which the portal accepted) instead of the official sample's
  NaN-outside/LZW encoding. This is the hedge for the unresolved "[0,1]" portal rejection;
  its true cause remains **not established**.
- Full 1 m LiDAR / training_features raster and bulk caches are absent in this checkout
  (gitignored bulk data); the lane runs entirely on committed hash-pinned bridge/external
  assets. No DrivenData download occurred (no auth in sandbox).

## Pass 3 — audit against the original request

- Unique TIF generated (not copied): **yes** — new surface, new budget, new obligation
  machinery; audit across 90 rasters including all nine champions and the witness.
- Obvious download/submit labeling: **yes** — executive summary page starts with the
  download buttons and a SUBMIT: YES/NO table; run card records both verdict lines.
- Executive summary per site with file, estimate, uniqueness: **yes** — nine-site table
  plus the candidate row, all numbers evidence-classed.
- Submission how-to sub-page: **yes** (§2 of the executive summary; links to the fuller guide).
- Prompt stored in the repo and re-read: **yes** — `docs/MISSION_PROMPT.md` addendum 2026-10-31.
- 3–5 ranked new hypotheses with layers/mechanism/mimic/cost/availability: **yes** — run card
  (`H-C`, `H-B`, `H-D`, `H-E` + executed `H-A`), availability checked against this session's
  real egress (H-E marked blocked, not viable this session).
- Holdout before slot: **yes** — three holdout evaluations; no slot used by this session.
- Line-by-line verification, no hallucinations, irregularities flagged: **yes** — every
  number in this document traces to a receipt file in `evidence/` or a live re-measurement
  recorded there; conflicts and unknowns are listed in the run card's
  `irregularities_flagged`.
- PR opened and merged to `main`: done at session end (this branch → PR → merge).
