# Submission wording continuation — 2026-10-26

## Decision

**DOWNLOAD existing research: YES. SUBMIT: NO. New TIFFs: none. Experiments: none. Slots used: none.**
The requested new high-scoring, literal-gate-unique submission is not achieved.
Read the full owner prompt embedded in README, the current owner briefs, and
`knowledge/22_current_best_review_2026-10-26.md` before further work.

## Pass 1 — implementation and exact-file check

Reviewed standing instructions, previous review, shared selector, current-best
review utility and generated executive page. Reopened DPRF1 with
`python scripts/review_current_best.py`; its recorded hash matches, the cached
template grid matches, and all pixels are finite and within [0,1]. This verifies
file format, not training provenance or organizer acceptance. The zero-outside
variant still differs from the sample's NaN-outside convention.

The EUL1 site packet contradicted the current decision by calling DPRF1 the
“single best unscored unique candidate” and the only supported submission.
Corrected the **generator**, not only generated HTML: DPRF1 is a recorded local
point-best, not a literal-gate-unique or submit-ready candidate. No gate, control,
threshold, scientific receipt or negative result was changed.

## Pass 2 — regression review

Added a scratch-site-build regression test covering both visible pages and
README. Initial suite had two failures due to unavailable historical Git objects
in this shallow checkout; fetched full history rather than weakening provenance
tests. The exact-file validator and site builder completed successfully.

## Pass 3 — request and scope review

Rechecked the generator output and current-best selector. The nine-site executive
table and download links already exist. Their inherited scores are not new
organizer receipts, and sibling holdouts cannot establish a cross-site winner.
No defensible calibrated hidden-score estimate exists. The explanation that
H33-B2 pruning reduces redundant false-positive cost is plausible, not a proven
hidden-label causal conclusion. The task predicts missing faults, not verified
geothermal vents.

The prior review already ranks three unexecuted geological hypotheses (directed
multi-catchment offset graph; magnetic/gravity two-sided texture front; quadrature
phase-congruency front). Do not call these validated or externally novel. No
single-method assignment is present, raw feature caches are absent, and the
literal spacing-5 comparator veto remains binding. Do not run another lane or
retune stopped methods to evade it. No new external source was fetched in this
continuation. Official review links and their access scope are recorded in the
prior review; the network permits GitHub and package registries only. No current
DrivenData score, quota or organizer acceptance has been verified.

## Next work

1. Resolve the prospective lane assignment and literal-control-policy conflict
   before any new experiment; do not exempt a control after seeing a result.
2. Restore raw cached features using documented provenance and hashes.
3. Implement independent scientific replay and authenticated quota evidence
   adapters before any positive selector authorization.
4. Harmonize sibling holdouts before claiming cross-site superiority; retain
   unknown hidden-score estimates as unknown.

Values: maximize probability of winning through evidence, not optimistic score
claims; own the outcome by preserving negative results and blocking unsafe uploads.

Final verification: **370 tests passed**; targeted Ruff and `git diff --check` pass.
Run card: [`submission_wording_review_20261026.json`](../evidence/submission_wording_review_20261026.json).
