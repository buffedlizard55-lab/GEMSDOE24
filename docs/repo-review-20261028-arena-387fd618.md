# Repository review — 2026-10-28 (Arena branch `arena/387fd618-gemsdoe24`)

**Outcome: no new TIFF, no scientific experiment, no submission slot, and no authorized submission.** The requested high-scoring unique submission is not achieved. No leaderboard score is estimated.

This review is scoped to the repository state available in this checkout. It is not a fresh scientific replay, complete audit of every remote site head, verification of organizer scores, or confirmation of DrivenData account quota.

## Pass 1 — understand the project and its evidence

Read `AGENTS.md`, the current owner brief, the feasibility review, the nine-site summary, the current focus-file audit, and the current best/selector receipts before acting. The repository has a well-developed research and publication pipeline: shared holdout evaluation, TIFF preflight/writer, source/feed auditing, static-site content, evidence receipts, tests, and explicit fail-closed promotion rules.

The requested nine-site work is represented in `docs/executive-summary.html`, `docs/portfolio-executive-summary.md`, and JSON audit receipts. Historical best values in the supplied request (including GEMSDOE32 H33-B2 `0.2778`) are owner-reported absent an artifact-linked organizer receipt. They are not organizer-confirmed scores. The candidate-site comparison also mixes different holdout evaluators and splits; therefore those values cannot support a valid cross-site ranking or hidden-leaderboard estimate. The web executive table explicitly shows **NOT ESTIMABLE** and **SUBMIT: NO**.

The current recorded local point-best is documented as S3DEP1, HOLDOUT-DTI `0.166060`, evaluator `gems-segment-pooled-v1`, 60,988 withheld positives, 95% CI `[0.151858, 0.180339]`. This is a recorded internal result, not an organizer score, was not replayed in this review, and fails submission selection gates. Its run card reports maximum registered-method 3-pixel dot overlap `0.71318` (DKRN1), beyond the protocol's 0.70 limit; the separate literal all-entry registry comparison also fails. Do not submit it.

## Pass 2 — adversarial checks and execution limits

- The stated single-method lane paragraph is absent. `AGENTS.md` and the current owner brief prohibit inventing a lane, restarting stopped lanes, or generating a new experiment/TIFF in this continuation. The protocol's 3-experiment / 2-hour ceiling is not permission to bypass the missing assignment.
- The frozen calibration-lattice receipt reports 6,649 uncovered footprint pixels. The separate, dependency-light arithmetic checker was run against the frozen audit; for 44,090 points it reports a minimum directed overlap of `0.8491948` (84.92%), necessarily above the 70% threshold. It is a necessary-condition bound, not evidence of scientific copying, a score, or a complete registry pass. The fresh raster-based feasibility checker could not run because NumPy is not installed in this runtime.
- `python -m compileall -q src scripts tests` completed successfully. A read-only JSON parse of the `docs/data` and top-level `evidence` JSON files checked 286 files; none failed parsing.
- `python -m pytest -q` could not start: `pytest` is absent. Do not describe the suite as passed in this environment. Likewise, `check_uniqueness_feasibility.py` could not start because NumPy is absent. No dependencies were installed and no environment or data files were altered.
- The active source audit is pinned to 2026-10-27 references and explicitly does not audit newer source heads or all live artifacts. A source freshness signal is not an artifact audit.

No submission file was opened as a candidate for promotion and no portal or leaderboard was accessed. There is no independent selector/quota receipt.

## Pass 3 — requirements and next actions

The project contains substantial implementations of the requested executive summary, submission guide, unique-artifact checks, source feed and evidence handling. The remaining blockers are material, not cosmetic:

1. Obtain the coordinator's exact, single-method lane paragraph and resolve the collision between the literal all-registry 70% uniqueness rule and the retained space-filling lattice before a scientific run. Do not remove the lattice or move dots into its gaps to evade the rule.
2. Recreate the pinned Python environment and run the full test suite plus fresh raster/registry checks. Keep outputs and dependency versions attached to the review.
3. Refresh all nine focus-site heads and audit exact current artifacts (file identity, score provenance/receipt, grid/range, cross-site duplicates and registry overlap). Existing audits are time-pinned and cannot substantiate current-head claims.
4. Before calling a hypothesis untried, compare it against the repository and concurrent PR work; the existing research-direction note says the top two concepts overlap open PR #70. The ASTER-alteration and GeoDAWN sources are official public references, but exact footprint coverage and downloadable tile availability remain unverified in this checkout.
5. Only after assignment and feasibility: preregister, test each feature/missingness channel in isolation, enforce fold-local hide-and-recover, measure the pre-placement surface and final dots against the refreshed registry, and stop on any threshold breach. Compare HOLDOUT-DTI using the same evaluator, withheld positives and confidence-interval method as the baseline. Promote only through a separate verified selector and account quota check.
6. Obtain an artifact-linked Organizer-confirmed submission receipt before labeling any score as confirmed. A valid TIFF format check alone cannot authorize upload or guarantee the portal's [0,1] acceptance.

### Candidate hypotheses already documented (not newly certified as untried)

`docs/research-directions-20261027.md` ranks four proposals qualitatively, without promising a score: (1) signed gravity–magnetic cross-gradient reversal using `rtp` and `iso_grav_anom`, oriented by `det_elev` tangent; (2) fold-fitted conditional ordinal potassium front from GeoDAWN K/Th/U; (3) separated signed terrain-curvature lobes tied to basement-depth gradient; and (4) offset ASTER mineral-alteration transitions relative to geophysical fronts. It names possible non-fault mimics and implementation costs. However, PR #70 was identified in the previous review as overlapping the first two, so those are not safe to describe as novel or untried until code-level comparison. The ASTER candidate needs an official source-to-footprint coverage check before viability; no external raster was fetched here. No candidate was validated on holdout in this review.

## Final run-card-style status

```json
{
  "hypothesis": null,
  "mechanism": null,
  "named_non_fault_mimic": null,
  "holdout_dti": null,
  "holdout_ci95": null,
  "holdout_evaluator": null,
  "withheld_positives": null,
  "correlation_overlap_vs_registry": "No new surface or dots generated; current recorded S3DEP1 receipt reports 0.71318 overlap with DKRN1 and fails the 0.70 competing-method limit.",
  "raster_sha256": null,
  "validator_output": "No new raster to validate; current best review's recorded S3DEP1 file passes its format checks but is not submission-authorized.",
  "submission_name": null,
  "submission_note": null,
  "verdict": "negative"
}
```
