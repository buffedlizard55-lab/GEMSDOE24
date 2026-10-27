# Active owner brief — 2026-10-27 review session

**Normalized requirements record, not a verbatim transcript.** Read this brief, the README and `AGENTS.md` at the start of future work. The long historical owner prompt and site-score catalogues remain archived in `README.md`; this addendum records the operative requirements and the current status.

## Objective and scope

Build a reproducible, evidence-first project for the DOE GEMS fault-mapping competition. The immediate focus sites are **GEMSDOE24, GEMSDOE25, GEMSDOE27, GEMSDOE28, GEMSDOE30, GEMSDOE31, GEMSDOE32, GEMSDOE33 and GEMSDOE36**. The output should make it unmistakable which exact GeoTIFF can be downloaded, what its evidence means, whether it is unique under the stated protocol, and whether it is actually authorized to submit. Do not call a historical file “best to submit” unless its evidence and all release gates support that decision.

The owner asks for a unique, scientifically justified GeoTIFF, a transparent analysis of GEMSDOE32 H33-B2 (reported 0.2778), a current source feed, research-grounded hypotheses, automated validation, a submission guide, and an end-to-end review with a PR merged to `main`. “Maximize P(Win)” and “Own the Outcome” are the project values.

## Non-negotiable research and release protocol

- **No copying, renaming or cosmetic perturbation of previous predictions.** A numerical/grid-valid file is not automatically unique, scientifically useful, or authorized.
- **One assigned method lane only.** The parallel-run prompt requires a single geological-method paragraph, but the active request does not identify one. Candidate ranking is planning, not a lane assignment. Do not choose a lane, rerun a stopped lane, or create a private fork to bypass a missing assignment.
- Reuse the shared cached feature stack, `scripts/evaluate_holdout.py` and `scripts/submission_writer.py`. Fix a shared tool once if needed; do not build a lane-specific substitute.
- Hide complete fault segments with a buffer; derive catalogue-based features only from visible faults; mask visible-fault pixels exactly; pool DTI with alpha 0.2, beta 0.8 and the 300 m triangular kernel. Test every source/derived feature alone; AUC above 0.90 is a leakage alarm until resolved.
- Check each candidate surface against the registry **before placement** and final dots afterward. Stop if absolute rank correlation is above 0.90 or more than 70% of candidate dots lie within 3 pixels of one registry raster. Do not change a stopped budget, move dots to evade the comparison, or silently exempt a registry control.
- At most three experiments or two hours. No weekly submission slot is used during screening. Promotion is a separate selector step and must respect the actual account quota.
- Label scientific measurements **HOLDOUT-DTI** with evaluator/version, withheld-positive count and 95% CI. Label an external leaderboard result **ORGANIZER-CONFIRMED** only when copied from an artifact-linked submission receipt. Owner reports, internal holdouts, geometric overlap and projections are distinct evidence classes; a projection is never a score.
- End a scientific run with one JSON card: hypothesis, mechanism, named non-fault mimic, holdout and CI, registry comparisons, raster SHA-256, validator results, filename, <=140-character note and `promote`/`negative` verdict. Negative results are deliverables.

## Data, sources and reporting

- Prefer free, public, official data; record exact source, version, license, coverage and hashes. A mirror hash proves byte integrity, not organizer provenance.
- The competition data page may require DrivenData authentication. Do not solicit or store credentials. The current sandbox can reach GitHub/API and package registries, but not DrivenData, USGS, NLR or OpenEI hosts. Links to those sites are manual-review references unless a dated receipt demonstrates fresh access.
- If an idea requires a new external data source, name the specific free official product and verify coverage/access before calling the idea viable. Otherwise prefer existing cached channels and state their provenance limits.
- The static site should present download status and the submission guide before any historical score table. The `[0,1]` requirement is checked by a read-back validator; do not guess that NaN alone caused a portal error.
- Keep a timestamped GitHub source-freshness feed separate from a leaderboard feed. GitHub commit freshness does not authenticate a score or refresh an artifact audit.

## Current blockers and decision rule

The request contains no standalone method paragraph. The current nine-file evidence is a pinned audit, not a complete re-audit of current `main` commits. The live GitHub-only freshness check reports source movement; it is not a score feed. Open PR #70 contains a CGMK1 implementation of the older signed magnetic–gravity / conditional-potassium proposals, so they are not certified untried; open PR #61 separately covers B2. Both are unmerged/dirty and neither assigns a lane here. The retained spacing-5 lattice is a space-filling calibration raster, and the literal 70%/3-pixel rule makes historical 37,654- and 44,090-dot budgets mathematically impossible against that witness. Smaller budgets are not thereby unique, useful, or approved. Do not weaken this rule without a prospective, explicit protocol decision.

The raw `data/training_features.tif` and prepared feature cache are absent from this checkout. `scripts/restore_data.py` can assemble a pinned **owner-supplied GitHub mirror**; that is not organizer authentication. No numerical estimate of a hidden leaderboard score is supported by the present evidence. In particular, H33-B2's 0.2778 and the prompt's 0.3195/0.4413 leader snapshots are unverified and conflicting.

## Session-start sequence

1. Read this brief, `README.md`, `AGENTS.md`, the current executive table, current freshness JSON and the latest integrity review.
2. Check whether a method paragraph was actually assigned. If absent, perform only non-experimental audit/documentation work.
3. Check data/cache presence and provenance before a method is proposed as runnable.
4. Rank three to five locally unimplemented hypotheses qualitatively; do not fabricate numerical DTI gains. Validate one only after the method lane and protocol are resolved, before any slot.
5. Perform three passes: implement/verify, adversarial bug/assumption review, then original-request/completeness recheck. Keep the branch fixed, open a PR from it, and merge only after reviewing checks.
