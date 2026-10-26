# Nine-site continuation — session c6ea4bb7, 2026-10-26

## Executive decision

**No new TIFF was generated. No file is approved for submission.** The requested
new, fully unique, high-scoring, submit-ready prediction remains unachieved.
There is no human-inspection exception. No competition slot was used.

[Download the existing DPRF1 research TIFF — DO NOT SUBMIT](downloads/gems24-dprf1-stitched-oof-tworegime-20261026-81849d67c8bf-zeros.tif).
The existing [executive submission guide](executive-summary.html) retains the
nine-site historical-best names, owner-reported values and submission steps.
[New nine-site artifact audit](artifact-audit.html) provides immutable source links
and a machine-readable inventory instead of implying that commit freshness
establishes current pixel uniqueness.

| File / purpose | Score estimate | Unique under the literal protocol? | Download / submit |
|---|---|---|---|
| Existing `gems24-dprf1-stitched-oof-tworegime-20261026-81849d67c8bf-zeros.tif` | Leaderboard estimate unavailable. Recorded **HOLDOUT-DTI 0.16379**, 95% CI **[0.15045, 0.17739]**, `gems-segment-pooled-v1`, **60,988 withheld positive pixels**; not rerun here | **No**: recorded all-entry final-dot overlap reaches **99.56%** vs registry-039 | Research download YES / submit NO |
| New candidate requested this session | Not generated or evaluated | Unknown | No file / submit NO |

Fresh shared-validator output confirms single band, finite [0,1] values, and
CRS/shape/geotransform match. The zero-outside variant does not match the cached
sample's NaN-outside/nodata convention (`official_format_compliant=false`).
Format acceptance by the organizer is not established. Exact-file SHA-256:
`c1257c1d4b5ac9cc0a8e29b0120c614fcaa1f38474bc1f6de98c0a1afb0567f1`.

## Pass 1 — continue the outstanding peer audit

The previous review's next steps were lane coordination, changed-peer auditing,
then scientific validation. No single-method paragraph is supplied here. Stopped
DPRF1-derived/residualization lanes cannot be retuned to escape a failed gate.
This session therefore implements the **Git-object inventory stage** of changed-peer
auditing, not a new geological experiment or completed current-raster audit.

`scripts/audit_priority_artifacts.py` resolves each main commit, reads the exact
commit's complete Git tree, and compares it to the frozen priority source pin.
The original registry is not edited. Missing/truncated trees fail closed; errors
remain unknown, not zero changes. Both the original and current object IDs and
immutable links are retained. ZIP members and LFS pointers are not implicitly
validated by this inventory. Scope is all tracked TIFF/ZIP paths, broader than
only published submission downloads; aliases and research inputs count as paths.

| Site | Added paths | Changed paths | Current pixel novelty / authorized download for submission |
|---|---:|---:|---|
| GEMSDOE24 | 36 | 0 | Not recomputed / none established |
| GEMSDOE25 | 46 | 0 | Not recomputed / none established |
| GEMSDOE27 | 37 | 0 | Not recomputed / none established |
| GEMSDOE28 | 32 | 0 | Not recomputed / none established |
| GEMSDOE30 | 14 | 0 | Not recomputed / none established |
| GEMSDOE31 | 59 | 0 | Not recomputed / none established |
| GEMSDOE32 | 36 | 1 | Not recomputed / none established |
| GEMSDOE33 | 36 | 0 | Not recomputed / none established |
| GEMSDOE36 | 15 | 0 | Not recomputed / none established |

Total: **311 added paths, one changed path, no removed paths**. These are not
performance measurements, distinct prediction counts or a current leaderboard.
[Full timestamped evidence](data/priority_artifact_inventory_20261026_session_c6ea4bb7.json).

### H33-B2 archive irregularity

The sole changed path is the H33-B2 zero-outside ZIP in GEMSDOE32. Downloaded both
Git blob versions via the GitHub API, checked their Git blob SHA-1 identities,
and inspected archive members in memory without extracting or using predictions.
The old 216-byte archive contains one zero-length `.zip`-named member. The newer
186,378-byte archive contains one 219,065-byte `.tif`-named member with TIFF magic.
[Byte-level receipt and immutable source URLs](data/h33_archive_inspection_c6ea4bb7.json).
This establishes an archive-member repair, not full raster validity or organizer
acceptance. It does not explain the owner's historical reported result.

The previous pixel-forensics explanation remains plausible, not proven: H33-B2
removed near-catalogue dots from H27-4 without adding dots. With pixel-exact known
fault masking, removing nearby redundant predictions can reduce false-positive
cost more than truth credit. We cannot determine its hidden-label causal benefit,
prove geothermal vents, or forecast an improvement over the owner-reported result.
Neither conflicting leaderboard-leader claim is organizer-confirmed.

## Ranked prospective research — not executed or assigned

Do not falsely relabel the previous review's unexecuted queue as newly discovered
hypotheses. These three remain prospective; rank is qualitative expected benefit
versus implementation cost, **not a numerical score projection**. Novelty against
all changed peer code remains unverified.

1. **Paired facing scarps:** cached LiDAR `upface_max`, `downface_max`, `strike`,
   `coh100`, `relief`; connected opposite-facing strips with stable width and aligned
   ends. Could expose narrow low-relief grabens missing from mapped range fronts.
   Non-fault mimic: fluvial terraces/irrigation banks. Object topology differs from
   existing pointwise conduit fusion and orientation junctions. Moderate potential,
   medium cost. First audit whether quantization preserves facing; locally cached
   layers suffice for that feasibility check, not yet for a validated detector.
2. **Radiometric front displacement:** K/Th/U channel ranks; signed spatial lag
   between parallel K and Th/U fronts across widths. Potential fracture-mediated
   alteration displaced from lithologic contacts under thin cover. Mimic: weathering
   and downslope sediment transport. Differs from CRP1's coincident compositional
   gradient; rank data cannot justify absolute concentration ratios. Uncertain
   benefit, medium cost; local quantized caches require support/unit auditing.
3. **Drainage graph offsets:** DEM-directed thalweg graph and repeated cross-valley
   channel-bearing discontinuities. Could recover faults lacking continuous scarps.
   Mimic: stream capture, fan avulsion and resistant lithologic contacts. Unlike
   pixelwise terrain Hessians, uses multi-catchment connectivity. Moderate potential,
   high cost; full prepared DEM cache must be restored/hash-checked first. Not
   experiment-ready. A higher-resolution upgrade requires official USGS 3DEP,
   whose availability cannot be checked under this sandbox's host allowlist.

No canary or new holdout was run: these are not promotion candidates. A future
assigned lane needs a preregistered current-best comparison and paired interval,
whole-segment buffered hide-and-recover, visible-only catalogue features, every
actual feature's two-polarity canary, surface novelty before placement and final-dot
novelty. No stopped lane, retained lattice control or threshold may be changed
post hoc to manufacture uniqueness.

## Pass 2 — verification and fixes

- Added regression tests for changed/added/removed/unchanged paths, malformed SHA,
  unsafe/duplicate paths, incomplete or mismatched trees, invalid sizes/modes,
  archives and symlinks. No Git metadata is labeled a pixel hash.
- Initial full-suite run: two historical provenance tests failed because the
  checkout was shallow. Fetched history with `git fetch --unshallow origin`;
  retained the tests and original-source requirements. Rerun: **389 passed**.
- Ruff lint and formatting checks pass. Existing shared writer, evaluator and
  selector remain unchanged; no private scientific fork.
- Existing open PR #7 is conflicting and belongs to another branch. Not modified
  or merged. This session only writes its assigned branch.

## Pass 3 — acceptance and next steps

The first-screen site notice links the new inventory, distinct from the historical
nine-site comparison. The README preserves the inherited owner prompt and its
current delta, with this continuation as a status addendum rather than a claimed
verbatim retranscription. Core values remain evidence-first: do not consume slots
on an unvalidated or duplicate candidate.

Outstanding, in order:
1. Coordinate an explicit single-method lane; none is present in this prompt.
2. Decode/hash/deduplicate the newly inventoried artifacts and audit current pixel
   content into a new versioned registry. Git SHA-1 identity is insufficient for
   spatial novelty; preserve all old comparisons and controls.
3. Resolve the near-domain-covering lattice constraint prospectively at project
   level; no policy exemption has been granted or applied here.
4. Restore the chosen lane's exact cached inputs, preregister and run within the
   budget. Do not promote unless it beats the current comparable holdout best.
5. Implement independent scientific replay and legitimate account-quota evidence
   before a positive selector path. A format pass or hand-entered boolean is not
   authorization. Existing project policy forbids automated DrivenData access.

## Sources and limitations

- Organizer reference solution: [verified current commit aebe92f7](https://github.com/drivendataorg/gems-prize-reference-solution/tree/aebe92f7c8a990f0e3443451b7a825d9afd6336b), checked via GitHub API this session. Not a score receipt.
- [Competition specification](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/), [prize PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf), [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and), [OpenEI INGENIOUS](https://gdr.openei.org/submissions/1391), [USGS 3DEP](https://www.usgs.gov/3d-elevation-program/data-tools): manual-review references, not freshly retrieved here. These hosts and Dropbox are outside the sandbox allowlist.
- GitHub sources establish repository contents, not scientific truth or independent
  organizer results. No claim of exhaustive new literature review, live leaderboard
  verification, full current-peer raster validation, or highest-achievable score.

### Final verification

Three passes completed. Final suite after integrating concurrent main PR #38: **390 passed**; Ruff lint passed, formatting
passed for 158 files, compileall and JavaScript syntax checks passed, and
`git diff --check` passed. New audit-page relative links resolve and its table
contains all nine sites. Shared current-best review no longer repeats the inherited
causal mechanism as a fresh verified conclusion; the source card remains unchanged.
[Session JSON run card](data/session_c6ea4bb7_run_card.json).
