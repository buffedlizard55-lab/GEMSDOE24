# Follow-up review: frozen research release, not another experiment

## Decision

**Download for research: yes. Submit to competition: NO.** This session did not
create a second detector, tune confirmation folds, select a competition slot, or
claim a new prediction by renaming the existing file. The existing unique ASPC
prediction remains the deliverable. No assigned single-method paragraph or matched
current-best OOF reconstruction has appeared; these are real scientific blockers.

Read the current requirements in `owner_brief_2026-10-25.md` and the README before
resuming. The earlier four ranked hypotheses and frozen experiment remain in
`09_preregistered_ASPC_2026-10-25.md`; do not describe them as newly proposed here.
The original findings and complete run card remain authoritative recorded evidence.

## Three review passes

1. **Implementation and verification:** reviewed active README/agent instructions,
   preregistration, findings, run card, shared writer, release renderer, tests and
   PR #7 metadata. Installed the project and testing dependencies. Baseline suite:
   119 passing tests. Independently reopened both downloadable TIFFs through the
   shared `submission.check_variants`; no private validator was introduced.
2. **Bugs and edge cases:** found that download rendering trusted stored format
   receipts after checking hashes rather than rerunning the shared validator.
   Added `gems.release_audit.verify_research_release`, invoked before rendering.
   It rejects disagreement between fresh validation, sidecar receipts, report and
   card; identity/authorization/holdout/note disagreement; altered bytes; changed
   companion predictions; and wrong outside-footprint conventions. Added negative
   regression tests. Also supplied the missing `dev` install extra, so
   `pip install -e '.[dev]'` actually installs the full test environment.
3. **Acceptance recheck:** built the site with exact-file revalidation, ran the
   complete test suite, lint, formatting and diff checks. Verified conspicuous
   first-screen research-only download and executive guide through site tests.
   Preserved negative promotion and zero slot usage. No scientific confirmation
   folds or new hypothesis experiments were run in this session.

Fresh format evidence: `evidence/release_revalidation_20261025.json`.
Reproduce without network or confirmation-fold reuse:

```bash
python -m pip install -e '.[dev]'
python scripts/verify_research_release.py
python scripts/build_site.py
python -m pytest -q
```

This audit checks recorded-evidence consistency and actual output bytes; it does
not independently reproduce the historic feature-stack experiment or prove absence
of leakage. Rank-correlation and overlap figures remain the frozen registry
measurements, not new comparisons against a globally current registry.

## Scientific answer and source boundaries

The nine-site forensics already show that H33-B2 is the D2.8 geometry with a
catalogue-clearance prune, not evidence of a new geological detector. See
`10_ASPC_findings_2026-10-25.md` for exact subset tests and the pruning inequality.
Precision/coverage tradeoffs are a plausible explanation, not a verified causal
explanation of private-label performance. The owner's score claims lack
artifact-linked organizer receipts. A higher leaderboard score is not established.
Fault detection does not establish discovery of geothermal vents.

Source/code links for manual review:

- [Organizer reference solution](https://github.com/drivendataorg/gems-prize-reference-solution)
- [Competition metric description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [Rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf)
- [USGS GeoDAWN parent DOI](https://doi.org/10.5066/P93LGLVQ)
- [USGS 3DEP parent source](https://www.usgs.gov/3d-elevation-program)
- [GEMSDOE32 code/artifacts](https://github.com/buffedlizard55-lab/GEMSDOE32)

These are retained provenance/manual-review links, not newly fetched official
scientific literature. No current leaderboard, receipt, rules revision or weekly
cap was verified. Automated DrivenData access remains prohibited by repository
policy. The sandbox permits only GitHub and package hosts; inaccessible official
sources are not described as freshly obtained.

## Next work, in priority order

1. Obtain the coordinated lane and authoritative current registry; do not invent
   either. No new experiment is justified merely to produce another filename.
2. Reconstruct the current-best algorithm on the shared hide-and-recover folds,
   regenerating catalogue-derived features from visible faults only. A historical
   submitted TIFF is not an uncontaminated OOF benchmark.
3. After lane coordination, preregister one unused hypothesis from the existing
   ranked list and compare on a new, appropriately reserved confirmation design.
4. Complete the exact-file nuisance audit only if that candidate remains eligible.
   Separate automated promotion from selector slot allocation and organizer receipt.
5. PR #7 remains open and was not merged or overwritten. Its historical work is not
   new evidence and requires a separate conflict-aware reconciliation.

This review owns the engineering outcome without pretending it resolves the
missing scientific comparison. Negative evidence remains a useful deliverable.

## Parallel integration addendum

During final fetch, main advanced to `a60a25a` with the MTR1 negative experiment.
Merged that history into this session branch, preserving its active site, full
owner prompt, research files and shared evaluator changes. MTR1 is now the active
first-screen download; ASPC is retained parallel research, not the active release.
The exact-file revalidation fix also applies to MTR1's active site renderer.
Historical receipts are preserved: every recorded validator field must match fresh
validation, while additive explanatory fields from a newer validator are allowed.
No scientific result was recomputed or reclassified. The merged suite contains
148 tests (the earlier 128 count was before parallel integration).

The parallel MTR1 report identifies a dense calibration lattice that triggers the
radius-3 overlap rule even for unrelated methods. This must be resolved prospectively
by protocol coordination, never by dropping a comparator after seeing results.
Read `11_MTR1_findings_2026-10-25.md` before any future experiment; the authoritative
shared registry is broader than ASPC's historical nine-repository registry.
