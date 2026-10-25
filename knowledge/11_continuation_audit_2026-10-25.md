# Continuation review — 2026-10-25

## Decision

**Negative / NOT OK TO SUBMIT.** This continuation audits the existing ASPC
research artifact; it does not create a new detector, rename a prior submission,
rerun confirmation folds or assert that the user's requested submission goal is
complete. No new method paragraph was supplied. Zero new experiments, zero slots.
The owner's reiterated requirements remain in the README and linked active brief.

## Pass 1 — repository and actual downloads

Read the README, standing instructions, current owner brief, ASPC preregistration,
findings, run card, shared writer, receipt tests and current site renderer. Fetched
GitHub branch state and inspected open PR #7. It is conflicting and describes an
already-negative persistence experiment; did not merge it or overwrite its work.

Recreated the CPU environment with `requirements.txt` plus editable installation.
`pip install -e . pytest` alone lacks research/test dependencies (pandas and BS4
among others); the README now uses the full requirements installation.

Fresh validation of both TIFFs against `data/bridge/sample_submission.tif` exactly
matches retained sidecars. Audit receipt:
`evidence/research_download_audit_20261025.json`. These checks use the existing
`gems.submission.check_variants`, not a private writer/evaluator. Historical
HOLDOUT-DTI remains in the run card, with version, withheld count and CI; it was
not re-estimated or converted to a leaderboard forecast.

## Pass 2 — defects and adversarial checks

The Pages renderer previously checked the companion's byte digest but did not
check its format sidecar, authorization or agreement with the run card. The
primary receipt was also less strictly cross-checked than it should be.

Added shared `gems.receipts.research_receipt` to bind both encodings to filename,
bytes, passing checks, no hard failures and explicit denial of upload authority.
The renderer compares primary card validation and complete companion identity.
The read-only audit command optionally reopens rasters via the shared validator;
static builds only inspect hash-bound receipts because bulk data is not staged.
Receipt consistency is not a digital signature and cannot establish scientific
truth if all evidence is maliciously rewritten together.

Tests cover both encodings: altered bytes, altered filenames, path traversal,
missing authorization, upload permission, hard failures, contradictory range
checks and inconsistent embedded validation. Integration tests ensure Pages
refuses a build granting upload permission to either research download.

## Pass 3 — original requirements and limitations

- 139 tests pass; Ruff lint and format checks pass; JS syntax and `git diff --check`
  pass. Site builds successfully; scratch-build tests check local links and the
  first-screen download and negative status. A local build is not proof of public deployment.
- Four ranked geological hypotheses were already preregistered in
  `09_preregistered_ASPC_2026-10-25.md`; don't relabel them untried discoveries.
- The existing unique research prediction remains downloadable. No new unique
  prediction was generated in this continuation. Repackaging it would not satisfy
  the user's requirement for another unique submission.
- No matched current-best OOF evidence means the high-scoring promotion gate
  cannot pass. A shipped TIFF is not an OOF detector reconstruction.
- No assigned lane: do not invent one, tune the recorded confirmation folds or
  evade the duplicate thresholds. Current novelty evidence is scoped to the
  pinned nine-site registry, not every unpublished parallel experiment.
- Exact-file nuisance audit remains missing for ASPC. Format validation is not
  geological validation or organizer portal acceptance.
- No artifact-linked organizer receipt verifies the owner's GEMSDOE32 result or
  conflicting leader snapshots. Do not report them as ORGANIZER-CONFIRMED.
- No new external scientific source was fetched or claimed verified. Source
  links and evidence distinctions are in `10_ASPC_findings_2026-10-25.md`.

## Answer and next-session order

Existing nine-artifact forensics show H33-B2 is exactly the D2.8 dot set with
catalogue-distance <=200 m dots removed. Its apparent advantage may be reduced
false-positive mass without commensurate loss of triangular-kernel recall; hidden
labels are unavailable, so neither causal benefit nor a higher future score can
be established. A geothermal vent discovery is not proven by a fault prediction.

1. Coordinate a single-method lane and current shared registry snapshot.
2. Reconstruct the actual best detector on visible-only buffered whole-segment
   folds using the shared pooled evaluator; catalogue-derived features must be
   regenerated per fold. Preserve its predictions and uncertainty as a benchmark.
3. Only then preregister an independent candidate; prioritize an untouched
   stable-Th-controlled radiometric contrast if assigned to that lane, with
   explicit sediment-sorting/oxidation-front controls. No numeric forecast.
4. Require current-best improvement plus leakage, novelty, nuisance and exact-file
   gates before selector consideration. Selector verifies the current weekly cap;
   this lane never uploads or spends a slot.
5. Resolve conflicting PR #7 separately without dropping newer safety work.
