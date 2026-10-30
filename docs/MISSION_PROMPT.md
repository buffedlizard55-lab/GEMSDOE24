# GEMS DOE 24 — Current Mission Prompt

**Normalized from the user's project request and standing protocol. Last reviewed: 2026-10-30.** Read this file and the current top of `README.md` at the start of every project session. Dated session notes are historical; the latest review and receipts control when facts conflict.

## Objective

Maximize the probability of winning the DrivenData GEMS DOE competition by producing a genuinely new, scientifically defensible, sufficiently unique GeoTIFF—only if every scientific, novelty, format, provenance, and separate-selector gate passes. Be explicit about when an artifact is merely downloadable for research and when it is actually authorized to submit.

**Core values:** **Maximize P(Win)** · **Own the Outcome**.

## Scope and requested deliverables

Focus sites: **GEMSDOE24, GEMSDOE25, GEMSDOE27, GEMSDOE28, GEMSDOE30, GEMSDOE31, GEMSDOE32, GEMSDOE33, and GEMSDOE36**.

The user asks for:

1. A reviewed and improved GEMS DOE project, with a per-site executive summary that gives the exact downloadable file, score provenance/estimate, and measured uniqueness against the other focus sites.
2. A genuinely unique TIFF, never a copied or renamed old emission, plus an easy shared-tool validation flow and a clear **OK TO DOWNLOAD / OK TO SUBMIT** decision.
3. Analysis of GEMSDOE32 B2's reported 0.2778 that separates pixel geometry from any unverified explanation of hidden score changes.
4. Three to five untried geological hypotheses **before implementation**. For each, specify layers and physical signature, why catalogue mapping may miss the fault, difference from repository implementations, qualitative expected benefit and cost, and principal non-fault mimic. Validate only the top assigned lane on spatially blocked holdout before any weekly slot. Related old proposals or implementations must be disclosed; do not relabel them novel.
5. Free official-source attribution and an obtainability check before treating any new-data-dependent idea as viable. If the official host, exact footprint product, and acquisition cannot be verified, mark that idea **NOT VIABLE / NOT VERIFIED** and do not run it.
6. Three review passes, line-by-line source/evidence checks, irregularity flags, a concise updated README mission, a requested PR, and a merge to `main` only when safe.

## Current status — 2026-10-30

- Current branch: `arena/5b3e6982-gemsdoe24`. No experiment, new surface, candidate dots, new TIFF, portal upload, or submission slot was used in this review.
- The single-method assignment paragraph is **missing**. Hypotheses may be ranked and documented, but no hypothesis may be selected or run until the lane is explicitly assigned.
- The training raster and prepared cache are restored and hash-checked, but the raster came from an owner-supplied GitHub mirror, **not an organizer-authenticated source**. See the current review for hashes and data lineage.
- GEO1's source-recorded HOLDOUT-DTI is **invalid**: the pinned runner masks fold eligibility using the full catalogue rather than only fold-visible catalogue faults. Its recorded nonzero TP count is inconsistent with that eligibility path. Its DTI/CI must not be advertised, ranked, or used for promotion. See `evidence/geo1_holdout_leakage_audit_20261030.json`.
- The standard **37,654**- and **44,090**-dot budgets fail the registry-lattice necessary bound: minimum 3-px overlaps are **82.3418%** and **84.9195%**, exceeding the 70% stop rule. The upper budget not ruled out by this bound is 22,163; that is not a uniqueness pass. No surface or dots were generated.
- The earlier nine-complement research TIFF is locally format-valid and range-valid inside the footprint, but fails the broader literal uniqueness gate and has a preflight decision of **DO_NOT_SUBMIT**. Its local validation is not organizer acceptance.
- B2's 0.2778 is **OWNER-REPORTED / UNVERIFIED**. Pinned pixel forensics record B2 as a deletion-only 37,654-dot subset of a 44,090-dot D2.8 pattern after removing 6,436 catalogue-adjacent cells, and also as a subset of a distinct 40,199-dot D2.8-family pattern after removing 2,545; no B2 dots were added. Neither relation reveals hidden TP/FP mass or proves why the reported score changed. See `evidence/oj1_priority_ancestry_replay.json` and `evidence/priority_review_20261025.json`.
- A GitHub-only feed checked at 2026-10-30T22:48:16Z found all 9 priority-repository `main` refs advanced since the pinned historical artifact audit. Those new heads/files were not inspected; see `docs/data/priority_feed.json`. Every estimated leaderboard score remains **NOT ESTIMABLE** without an organizer receipt. No live leaderboard, portal, quota, or current official organizer source was freshly checked.

## Ranked geological hypotheses — proposals only, not lane assignments

These are narrowly scoped transformations of already-staged local bands. The novelty claim is only that the exact operation was not found in the inspected executable source; related radiometric, conductivity, gravity, residualization, and edge ideas exist in the repository. They are not certified novel across all external branches/repositories, are not score projections, and must not be run without an explicit lane paragraph.

| Rank | Layers and proposed signature | Why a catalogue fault may be missing; difference from inspected implementations | Qualitative expected benefit / cost | Named non-fault mimic; external data |
|---|---|---|---|---|
| 1 | `cond_surf`, `depth_to_base_surf`, `det_elev` and a staged acquisition-block nuisance channel. Within each training fold, estimate a robust background conductivity surface conditioned on sediment/basement depth, elevation and the locally derived acquisition-block proxy; test for a spatially persistent, elongated positive residual corridor crossing a basement-depth step. The block proxy is not official flight-block coordinates; its source receipt reports ~4.9 px mean figure-boundary residual. | Concealed permeable faults may channel fluids beneath basin fill while remaining unmapped at the surface. Existing code/proposals include conductivity saddles and contour-component persistence; this is a different *conditional basin-fill/background residual* question, not generic conductivity edge detection. | Medium–high potential to reduce basin-clay false positives; medium implementation and audit cost. No numerical gain is asserted. | Saline groundwater, playa clay, lacustrine sediment, or an acquisition seam. Uses staged local layers; no new external source is required. |
| 2 | `iso_grav_anom`, `depth_to_base_surf`, `iso_grav_anom_hg` and optional `det_elev_slope`. Form a depth-conditioned basin-fill gravity null; test a signed gravity residual and cross-normal edge pair that persists across scales and intersects a mapped basement-depth step. | A blind basement offset may be obscured by broad basin-fill mass. Existing local code/proposals cover potential-field gradients, Euler deconvolution, Hessian invariants, cross-gradients, and directional variograms; the new claim is specifically the physically conditioned gravity-compensation residual, not those methods. | Medium potential, medium–high cost (null fitting, boundary control and leakage canaries). | Lateral lithology/density contact, intrusive body, or survey leveling seam. Uses staged local layers; no new external source is required. |
| 3 | GeoDAWN radiometric `K`, `Th`, `U` plus contractor `ThK`/`UTh`. In a local neighborhood, form centered log-ratio coordinates and detect a multiscale *change in joint compositional covariance/orientation* aligned with an independent basement step, rather than summing scalar channel gradients. | Blind hydrothermal alteration can create a narrow multielement transition without a preserved surface scarp. Existing CRP1/MTR1/SAHG1 methods use scalar ratios, depletion, or individual fronts; this tests the joint covariance change point. It is related to prior radiometric work, not an unqualified new-data discovery. | Low–medium potential; medium–high statistical and compute cost; strong confounding risk. | Lithologic boundary, soil sorting, moisture/vegetation, or radiometric survey seam. Uses staged local data; no new external source is required. |

If a candidate later requires an un-staged layer, first identify the exact free official dataset, official endpoint, footprint coverage, license, and reproducible retrieval receipt. A remembered URL or owner mirror is not an obtainability check. No external-data candidate is certified viable by this list.

## Hard scientific and operational gates

1. **Single assigned lane:** stay in the explicit assigned method paragraph. Missing assignment is a stop, not permission to choose a proposal.
2. **Reuse shared tools:** use the prepared feature cache, `scripts/evaluate_holdout.py`, `scripts/submission_writer.py`, and shared validation/novelty tools. Fix shared defects once; no private evaluator or writer forks.
3. **Holdout integrity:** hide whole connected fault segments with the declared buffer; all catalogue-derived features and eligibility masks use only that fold's visible catalogue; mask visible faults pixel-exactly; pool TP/FP/FN before DTI; alpha 0.2, beta 0.8, 300 m triangular kernel. A full-catalogue eligibility mask invalidates the holdout.
4. **Leakage canaries:** evaluate each feature alone; either-polarity AUC above 0.90 is suspected leakage until disproven. A passing feature-only canary does not excuse an eligibility or provenance leak.
5. **Uniqueness before placement and after dots:** compare rank correlation against every registry raster; stop if absolute rank correlation exceeds 0.90 or if more than 70% of any candidate's dots fall within 3 px of any one registry raster. Do not remove comparators, target holes in a calibration lattice, tune a stopped budget, or substitute filename/hash uniqueness.
6. **Scores and uncertainty:** label each valid internal result **HOLDOUT-DTI** and include evaluator version, withheld-positive count, and 95% CI. Label an organizer result **ORGANIZER-CONFIRMED** only with an artifact-linked receipt. Otherwise say **OWNER-REPORTED / UNVERIFIED** or **NOT ESTIMABLE**. Never call a projection a score.
7. **Submission is a separate selector:** no upload or weekly slot in this work. A format-valid TIFF is not submission authorization. No human-inspection fallback may override a failed automated gate.
8. **Budgets:** at most 3 experiments or 2 hours, whichever comes first. Do not spend the selector's weekly slot budget.
9. **Review/PR:** perform three explicit review passes: (1) task and evidence scope, (2) source/data/metric integrity, (3) tests, docs, UI, and final diff. Create a PR from the assigned branch and merge only when all checks pass and no scientific guardrail is weakened.
10. **End with one JSON run card** containing hypothesis, mechanism, named non-fault mimic, holdout result or `NOT RUN`, registry surface correlation/dot overlap or `NOT RUN`, raster SHA-256 or `null`, validator output, submission name and <=140-character note, and `promote` or `negative` verdict. If no experiment ran, say so explicitly.

## Non-negotiable download/submission language

- A research file can be labelled **DOWNLOAD: YES (research) · SUBMIT: NO**.
- A submission may be labelled **OK TO SUBMIT** only after the exact TIFF hash passes the applicable automated format checks, scientific promotion, pre-placement and post-dot uniqueness gates, and the separate selector. Local preflight alone is not enough.
- For every focus-site row, provide the exact pinned download and state the measured uniqueness scope. Do not imply “unique” means globally novel when only the nine-site comparison was performed.
- If any required evidence is missing or contradictory, fail closed and explain what evidence is missing; do not invent a score, receipt, source, or data provenance.
