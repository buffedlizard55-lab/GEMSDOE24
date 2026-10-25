# Repository review — session verification, 2026-10-25

## Executive finding

The repository already contains the preregistered ASPC experiment and its uniquely generated TIFF. It is a **research deliverable only — NOT OK TO SUBMIT**. The requested stop/go gates correctly produce a negative promotion verdict; no slot was used. This session did not run a second model experiment, retune the frozen folds, claim a score above the reported GEMSDOE32 result, or upload anything.

The earlier [`2026-10-25_review_and_run_card.md`](2026-10-25_review_and_run_card.md) and [`2026-10-25_run_card.json`](2026-10-25_run_card.json) were initial pre-experiment records and have now been marked superseded. Their historical nulls must not be read as current experiment results. The active records are the [`ASPC run card`](aspc_run_card_20261025.json), [`full experiment receipt`](aspc_run_20261025.json), and [`ASPC findings`](../knowledge/10_ASPC_findings_2026-10-25.md).

## Pass 1 — repository and requested evidence

- Read `AGENTS.md`, the root `README.md`, the active owner brief, preregistration and findings, the public site pages, the shared evaluator/writer and the active run receipt.
- Confirmed the four preregistered hypotheses are described in `knowledge/09_preregistered_ASPC_2026-10-25.md`; ASPC was the single frozen experiment. The lane is explicitly provisional because the prompt contains no assigned method paragraph.
- Inspected the nine named repositories' downloadable raster registry. Restored 98 pinned references / 84 unique blobs through the existing GitHub-only restore tool; the script SHA-1-validates Git object identity and checks byte counts / SHA-256 before forensics. The working raster cache is ignored under `data/research/` and is not a repository deliverable.
- Reviewed open PR #7. It is still open and marked conflicting against `main`; it is a separate H24-3A road/potential-field change. No changes were made on that sibling branch and it was not merged.

## Pass 2 — independent checks and discrepancies fixed

- Re-ran the existing `scripts/review_peer_forensics.py`. It reports the named GEMSDOE32 H33-B2 raster has **37,654 dots**, with **0** within 200 m of the catalogue, and exactly matches the GEMSDOE25 44,090-dot D2.8 raster after removing all dots within 200 m; it is also the GEMSDOE31 40,199-dot reference after the additional 2,545-dot clearance. The GEMSDOE36 file contains H33-B2 plus 1,200 additional dots. This establishes geometric ancestry, not score causation.
- The reported H33-B2 `0.2778`, the supplied conflicting leaderboard values `0.3195` / `0.4413`, and other sibling numbers remain **UNVERIFIED-OWNER-REPORT / TEAM-PUBLISHED CLAIM**, not ORGANIZER-CONFIRMED. No organizer artifact receipt or current portal snapshot is present.
- Reopened both exact ASPC TIFF files using rasterio and checked against the pinned template. Primary research file: SHA-256 `7f5706e03866d826e83ba5298a7f3fbbcfacc3b3e74b957d726269b54714e7bd`; single-band float32; EPSG:32611; shape 3730×3292; transform `(100,0,243350,0,-100,4508550)`; all 5,167,373 in-footprint values finite and within [0,1], with values `{0,1}`. The allfinite/zeros-outside variant does not carry the template's NaN-outside encoding; it is explicitly labeled research-only. The companion NaN-outside variant has identical in-footprint predictions and SHA-256 `de1c22230f12011fb1f30cb137b7bef912ea250df4539a0bef8d0d25276c9218`.
- Verified the repo's existing run card: HOLDOUT-DTI `0.0855261252`, evaluator `segment-hide-recover-pooled-v1`, 60,988 withheld positives, 95% spatial-cluster CI `[0.0743998357, 0.0964827766]`; paired improvement over a fixed scarp control is `+0.0171670774`, CI `[+0.0089703698, +0.0246609543]`. This is **not** an organizer score and does not establish superiority to the current-best OOF model.
- Confirmed the registry novelty checks in the frozen receipt: maximum surface Spearman `0.1076904`, final-dot Spearman `0.0234629`, maximum candidate-dot fraction within 3 px of any one reviewed reference `0.5149519`; each is below the user's 0.90 / 0.70 duplicate thresholds. Scope is the pinned downloadable artifacts in nine repositories, not all unpublished or future registry rasters.
- Found and fixed a documentation inconsistency: the initial pre-experiment review still said no experiment, no registry artifacts and no TIFF existed. Preserved it as history but added explicit supersession notice and linked the active ASPC records. The old JSON run card now carries a machine-readable superseded status.

## Pass 3 — final implementation and acceptance verification

- Installed the pinned Python dependencies into the ignored `.venv` (system Python initially lacked NumPy/pytest); no data or generated cache was added to Git.
- `.venv/bin/python -m pytest -q`: **119 passed**.
- `.venv/bin/ruff check src scripts tests`: passed.
- Python `compileall`, `node --check docs/assets/app.js`, and `git diff --check`: passed.
- Exact TIFF validators and `submission_authorized=false` agree with the visible first-screen status and executive guide. The download is obvious, uniquely named, and conspicuously labeled **DO NOT SUBMIT**; the note is 93 characters, within the requested 140-character limit. The project does not upload to DrivenData.
- The run budget remains one fixed experiment (below the cap of three). No fresh candidate experiment was justified by this repository review: the active experiment is frozen, the parallel lane is unassigned, the current-best comparable OOF reconstruction is unavailable, and the exact-file nuisance audit is not complete. Creating another TIFF without passing those gates would contradict the protocol.

## Current run card summary

See [`aspc_run_card_20261025.json`](aspc_run_card_20261025.json) for the canonical machine-readable card. Summary:

- **Hypothesis:** ASPC antislope paired-curvature scarp.
- **Mechanism:** uphill-facing fraction × paired-curvature balance × channel-bank veto × step response × square-root coherence.
- **Named non-fault mimic:** rotational landslide headscarps and terrace risers.
- **HOLDOUT-DTI:** `0.0855261252` (segment-hide-recover-pooled-v1; 60,988 withheld positives; 95% CI `[0.0743998357, 0.0964827766]`).
- **Registry comparison:** surface max Spearman `0.1076904`; final-dot max Spearman `0.0234629`; maximum within-3-px candidate overlap `0.5149519`; all below duplicate thresholds in the reviewed scope.
- **Raster SHA-256:** `7f5706e03866d826e83ba5298a7f3fbbcfacc3b3e74b957d726269b54714e7bd` (zeros outside; research only).
- **Validator:** no NaN/Inf inside footprint; in-footprint [0,1]; CRS, shape and transform match. The NaN-outside companion matches the template outside convention; both remain unauthorized.
- **Submission name:** `gems24-aspc-20261025-6393e9d9b0df-RESEARCH-NOT-SUBMISSION-zeros.tif`.
- **Note:** `ASPC antislope/curvature with channel veto; research-only. No organizer score; do not submit.`
- **Verdict:** negative; `submission_authorized=false`; no slot spent.

## Remaining blockers and next work

1. Obtain an explicit coordinated method-lane assignment and a complete registry snapshot before starting another parallel method.
2. Reconstruct a comparable current-best OOF detector with fold-local catalogue features; the fixed scarp control is not an adequate replacement for this gate.
3. Run the required exact-file nuisance audit before promotion. Keep roads, claims and acquisition-block membership restricted to the declared audit family.
4. Verify any score only from an artifact-linked organizer receipt and the current submission page. The prompt's leader figures conflict and are not refreshed automatically; existing policy forbids robot access to DrivenData.
5. A separate selector must verify the actual weekly cap and decide whether any promoted artifact uses a slot. This repository does not upload.
6. The reported portal range error's cause remains unknown; the tested TIFF itself has only [0,1] values inside the official footprint. Do not infer the cause or claim portal acceptance.
7. Geological fault-trace mapping is not geothermal vent discovery, permeability, or commercial resource confirmation.
