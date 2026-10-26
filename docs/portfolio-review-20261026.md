# Nine-site artifact audit — 2026-10-26

**DOWNLOAD existing research: YES. SUBMIT: NO. New TIFFs: 0. New experiments: 0. Slots used: 0.**

The requested new, higher-performing, genuinely unique submission **was not
achieved**. This review completes the previously unfinished artifact audit and
data placement; it does not rebrand an older prediction as a new result.

[Executive download / submission guide](executive-summary.html) ·
[Nine-site CSV](data/portfolio_summary_20261026.csv) ·
[Complete artifact audit](data/portfolio_artifact_audit_20261026.json) ·
[Source freshness](data/portfolio_freshness.json) ·
[Official-source claim checks](data/portfolio_source_claims_20261026.json) ·
[One session run card — negative](data/portfolio_run_card_20261026.json).

## 1. What was actually verified

The audit finished at **2026-10-26 16:49:11 UTC**, against nine immutable refs
captured earlier in this session. It reopened **326 TIFF files**: **315** remote
files and **11** local historical references. There are **167** distinct valid
in-footprint contents, **157** encoding/content aliases and **2** format rejects.
**169** files pass both the shared format check and the strict whole-array
finite `[0,1]` variant. These are file statistics, not scientific scores.

Discovery covers every TIFF under `docs/` at those refs, two archived GEMSDOE33
legacy candidates, and the retained local input/calibration references. It does
**not** claim to cover every TIFF from all 92 sites, every historical commit,
or feature rasters outside those publication paths. The discovery snapshot and
registry account for every selected file, including the rejects. Changed refs
are reported separately in the source feed; a later commit is not silently
assumed to contain the same artifacts.

For the nine highest historical owner-claimed artifacts and nine current
source-featured research files, the shared `gems.novelty.compare_registry`
recomputed final-dot comparisons against **166 or 167** distinct comparator
contents. Only each file's own encoding variants were excluded. Cross-site
exact copies, other method names and **all controls** were retained. Raw rank
correlation covers all **5,167,373** footprint cells; triangular-kernel
correlation uses the shared deterministic sample. Dot overlap uses every
candidate dot and an **inclusive Euclidean 3-pixel** radius.

**All 18 named artifacts fail the current literal final-dot rule.** No original
continuous pre-placement surface was independently replayed, no new holdout was
run, and no artifact-linked organizer score receipt was obtained. Final binary
maps cannot be substituted for original pre-placement surfaces.

## 2. Current best: useful research, not a submission

DPRF1 remains only the **recorded local point-best**, not a verified cross-site
winner. Its archived result is **HOLDOUT-DTI 0.1637924246971501**, evaluator
`gems-segment-pooled-v1`, **60,988** withheld positives, **95% CI
[0.15045, 0.17739]**. This session checked its bytes and final geometry; it did
not independently rerun the training or evaluate new hidden labels.

- File: `gems24-dprf1-stitched-oof-tworegime-20261026-81849d67c8bf-zeros.tif`
- SHA-256: `c1257c1d4b5ac9cc0a8e29b0120c614fcaa1f38474bc1f6de98c0a1afb0567f1`
- [Research download](downloads/gems24-dprf1-stitched-oof-tworegime-20261026-81849d67c8bf-zeros.tif)
- All stored pixels finite `[0,1]`, single-band float32, exact template grid.
- **Fresh directed overlap: 86.6628% against EUL1, as well as 99.5645%
  against the lattice.** The first is a real current-method comparison, not
  the synthetic control. Thus removing the lattice alone would not make
  DPRF1 pass this snapshot.
- EUL1's earlier comparison in the reverse direction is not interchangeable:
  the rule measures the fraction of the **candidate's** dots near a reference.
  This is a geometric duplicate flag, not proof that either implementation
  copied the other.

The table's “estimated leaderboard score” is **not estimable**, for every file.
No common, independently replayed holdout or receipt-linked calibration across
these methods was established. Reusing related family variants as independent
calibration samples would be misleading. An owner claim is not a verified
score, and a local HOLDOUT-DTI is not a forecast.

## 3. Why H33-B2 might have helped — what is proved and what is not

**The 0.2778 association is OWNER-REPORTED / UNVERIFIED, not
ORGANIZER-CONFIRMED.** The prompt also supplies conflicting public-leader claims
0.4413 and 0.3195; neither was authenticated as a current score.

The freshly reopened masks establish, with zero XOR:

1. GEMSDOE25 D2.8 and GEMSDOE30 D2.8 contain the same **44,090** predictions
   inside the template, despite different file encodings/hashes.
2. H33-B2 equals that D2.8 set after deleting **6,436** dots at distance at most
   **2 px / 200 m** from the public catalogue. **37,654** remain; zero are added.
3. From GEMSDOE31's **40,199**-dot solo set, H33-B2 deletes **2,545** and adds zero.
4. The historical GEMSDOE36 Anderson file contains all H33-B2 dots plus **1,200**.

Under the mandated pooled DTI implementation,

`D = T / (T + 0.2 F + 0.8 (G - T))`,

where `T` is weighted recovered-positive credit, `F` is weighted false-positive
cost and `G` is positive mass. Deleting a group of dots improves this ratio only
if its false-positive reduction outweighs lost truth credit. With lost credit
`L` and removed false-positive cost `S`, the condition is

`L (0.2 F + 0.8 G) < 0.2 T S`.

Consequently, removing redundant catalogue halos is a **plausible** reason for
improvement if those removed dots had little new-fault credit. The hidden `T`,
`F`, `G`, `L`, `S` are unavailable. The mask algebra neither proves hidden-label
causality nor justifies inventing another score by pruning further. Reusing
H33-B2 would be a duplicate, not an independent geological discovery.

### Corrections to overly simple inherited ancestry statements

- The named GEMSDOE28 rung30 artifact has **37,660** dots, not the implied
  **40,700** from “solo +501.” Relative to H33-B2 it contains **11,412** other
  dots and omits **11,406** H33-B2 dots. Do not call it a simple superset of B2.
- The named GEMSDOE33 H33D file has **41,865** dots, not **44,090** from the
  shorthand “B2 +6,436.” It contains **10,251** other dots and omits **6,040**
  H33-B2 dots. The exact-superposition claim is not supported by these bytes.
- The current binary footprint and finite sample mask are identical:
  **5,167,373** cells and zero XOR. The historical prose count **5,167,378**
  must not be described as a measured current five-cell mask difference.

Frozen prior receipts remain intact. These corrections are in a new, versioned
review, not silent rewrites of historical evidence.

## 4. New integrity/format findings

| Finding | Exact evidence and implication |
|---|---|
| GEMSDOE31 CSDU NaN companion | SHA `774c7c5aa3784d7c52dc67870e1cc8b0e0a34d1697092ad9f3b08c33dcaf2546`; **2,610,312** nonfinite values **inside** the actual sample footprint. Shared validator rejects it. |
| CSDU allfinite file | SHA `bc3681c49fef1df1610cba81cd1064d22f17c28a1812ac9ac233858925e3ea73`; **4,000** total positive pixels, but only **2,101** inside, **1,899** outside, and **32** on the public catalogue. Numerical format PASS does not validate the source's zero-catalogue-overlap/footprint claims. |
| GEMSDOE36 format demo | `GEMS36_FORMAT_TEST_NOT_SUBMISSION.tif` is **32 × 48**, not the competition grid. Preserved as an explicit reject, not a candidate. |
| GEMSDOE27 H31 | Its pinned page/card says promote under a narrower comparison set. The fresh literal audit fails. README declares **289,180** withheld-positive occurrences; its run card declares **120,778**. This denominator conflict was not independently reconciled, so the summary does not adopt a scientific score for it. |
| Source range-error guarantees | Allfinite `[0,1]` is a local numerical property, not proof of portal acceptance. The exact cause of the owner's prior rejection remains unknown. |
| VENT | Previously quarantined fabricated fallback gate values remain untrusted. No promotion or score forecast uses them. |

The fresh official reference notebook writes one band with the label CRS and
transform and does **not** set nodata in the shown writer. The shared local
`official_format_compliant` field encodes the inherited sample's NaN-outside
convention; this review did not independently authenticate a current portal
requirement for that convention. The two facts must not be conflated.

## 5. An automatic stop before another standard-budget experiment

The retained spacing-5 lattice covers **5,160,724** template cells within
inclusive 3 px, leaving **6,649** uncovered. For any `K = 37,654` distinct dots
inside the template, at least `K - 6,649 = 31,005` must fall in that covered set.

`minimum overlap = 31,005 / 37,654 = 0.8234184947150369 > 0.70`.

This is a geometric lower bound, not a scientific duplication test or hidden
score. It applies to the stated budget, not every conceivable smaller budget.
No control was excluded, no threshold changed and no dots were moved to exploit
uncovered holes. A smaller budget is not automatically viable or permitted as
an evasion. The single assigned method paragraph is still absent. No stopped
lane was revived.

## 6. Corrected geological queue, data readiness and official sources

Four hypotheses were ranked before implementation. The current peer audit then
found **GEMSDOE36 H36-GPS already implements scarp/graben pairing**, so that
mechanism was removed from the untried queue. This is a useful negative finding,
not a reason to rename it.

The amended order is:

1. **Two-sided directional texture/semivariogram change** in raw RTP/TMI and
   gravity, checked against `TMI_up150`. Covered basement steps may change
   texture without a strong edge. Mimic: intrusive contacts and leveling seams.
2. **Signed spatial lag of radiometric fronts**, not another K/Th/U magnitude
   product. Mimic: differential weathering and hillslope transport. Quantized
   ranks cannot establish physical concentration ratios.
3. **Cross-modality quadrature phase congruency**, not the already-tested
   scalar continuation/derivative operators. Mimic: dikes, calderas and seams.
4. **Multi-catchment offset graph — deferred**, because the restored band is
   detrended elevation, not an absolute DEM suitable for hydrologic routing.
   An independently obtainable absolute USGS 3DEP source was not verified here.

These are unexecuted local operators, not invented brand-new scientific
concepts or proven globally unique methods. Exact layers, mechanism,
non-fault alternatives, qualitative benefit/cost and readiness are in
[`26_portfolio_plan_corrections_2026-10-26.md`](portfolio-hypotheses-20261026.md).
The top one was **not** run under an invented lane assignment or despite the
preflight obstruction. No numerical benefit or expected leaderboard score is
claimed for any of them.

**Data placement completed:** restored `training_features.tif`, **418,912,844
bytes**, SHA-256 `4371c82e3b8339b807bdffcf4ef59a225520fe2988d521be208ae33743123bc5`.
Prepared **5,167,373 × 30** feature matrix, SHA-256
`a4ca25b2a18f6f6637f0247367cc6235a1366eb8475f77b18cd0285e62232dc8`.
The source is the pinned owner mirror, **not organizer-authenticated**. Bulk
inputs/caches remain ignored, and may need restoration in a fresh sandbox.
The fresh official README explicitly supports CPU execution; a GPU is not a
prerequisite for this data preparation.

Official GitHub source freshly verified at
[`aebe92f7c8a990f0e3443451b7a825d9afd6336b`](https://github.com/drivendataorg/gems-prize-reference-solution/tree/aebe92f7c8a990f0e3443451b7a825d9afd6336b):
fault-detection target, Tversky training loss alpha/beta, writer metadata and CPU
support. The public notebook's training loss does not independently certify
this repository's distance-weighted evaluator.

[USGS GeoDAWN](https://doi.org/10.5066/P93LGLVQ),
[USGS 3DEP](https://www.usgs.gov/3d-elevation-program/data-tools),
[OpenEI GDR 1391](https://gdr.openei.org/submissions/1391) and
[DOE/NLR rules](https://docs.nlr.gov/docs/fy26osti/96647.pdf) remain official
review leads from the preserved metadata. Their hosts are outside this
sandbox's outbound allowlist; they were **not freshly fetched**. No automatic
DrivenData access, organizer score lookup or live quota check occurred.
A fault hypothesis is not proof of a vent or productive geothermal reservoir.

## 7. Shared-tool fixes and reproducibility

- API registry caching now honors `--cache-dir`, validates full commit refs and
  Git blob hashes, and namespaces files by owner/repository/ref. A mutable
  path cannot silently reuse another ref's bytes.
- Frozen registry restoration preserves original JSON/IDs and restores cache
  bytes rather than rewriting old evidence. A changed footprint policy,
  membership, hash or validity requires a new versioned manifest.
- This audit explicitly records the sample-template footprint and keeps both
  rejected files, not only successful downloads.
- Cached feature reuse checks the actual feature hash, every input hash,
  expected channel ordering, shape and float32 dtype. Cache presence alone
  no longer counts as validation.
- The central lattice-bound helper rejects broadcastable/malformed masks,
  NaN/negative radii, bad coverage thresholds and invalid candidate counts.
  Its lower bound is tested against exhaustive small-grid enumeration.
- The executive renderer recomputes every duplicate decision from recorded
  statistics, requires every comparator/target, checks source-card hashes and
  rejects invented forecasts or a positive authorization. A tiny numerical
  domain tolerance handles accumulated rank-correlation roundoff near 1;
  the actual 0.90 / 0.70 stop thresholds are unchanged.

Restore the frozen audit's cache without overwriting the manifest:

```bash
python scripts/cache_priority_registry.py \
  --transport api --footprint-policy sample-template \
  --snapshot registry/priority_source_snapshot_20261026_portfolio.json \
  --manifest registry/priority_rasters_20261026_portfolio.json \
  --cache-dir data/research/portfolio_20261026T1612Z/cache
python scripts/audit_priority_portfolio.py --resume
python scripts/build_site.py
python -m pytest -q
```

The audit does not need feature restoration to compare saved rasters. For the
separate raw-data prerequisite: `python scripts/restore_data.py`, then
`python scripts/prepare_data.py`. Neither command trains a new candidate.
Source freshness is checked on the Pages schedule against the new audit's pins;
it does not automatically create a new raster audit or leaderboard result.

## 8. Remaining work — no hidden positive fallback

1. Establish a prospective assigned lane/protocol that can actually satisfy the
   literal rule; do not retroactively exempt controls or optimize into holes.
2. Use an independently replayable, common buffered holdout before claiming
   cross-site scientific superiority. Test every actual feature in both
   canary polarities; derive all catalogue features from visible faults.
3. Reconcile the source denominator and artifact inconsistencies identified
   here. Treat newer commits as unaudited until their bytes are checked.
4. The independent replay certificate and current-account quota evidence path
   remain unavailable. No human sign-off substitutes for either or for a
   failed scientific/novelty gate.
5. A genuinely new model must beat the current comparable best and every gate
   before the separate selector can consider a weekly slot. No such file has
   been created in this session.

Values: **Maximize P(Win)** by distinguishing useful evidence from optimistic
labels. **Own the Outcome** by fixing shared defects, making downloads honest,
and refusing to turn a negative result into an upload recommendation.
