# Data readiness and next scientific gate — 2026-10-25

## Decision

**Data placement is complete in this workspace; the scientific/promotion gate is not.** The restored competition feature raster and derived stack are local, hash-checked, and ignored by Git. No new experiment ran, no new submission TIFF was generated, and no submission slot was used. Existing candidates remain research-only / negative unless their separately recorded promotion gates change.

The supplied method-lane paragraph is absent. In addition, the literal registry overlap rule is non-discriminating for the recorded candidate support: the registered spacing-5 calibration lattice covers 99.87% of the footprint within 3 pixels and all of MTR1's supported domain. Do not generalize that measured coverage to an untested candidate; check each candidate surface and final dots against the exact registry bytes. Do not remove the lattice after seeing the result; obtain a prospective protocol decision on the status of synthetic calibration rasters before another experiment. Under the literal rule, the prior MTR1 and SAHG1 files are negative; a new candidate must pass the check on its exact support/dots before placement.

## Newly completed data readiness checks

Commands executed:

```bash
.venv/bin/python scripts/restore_data.py --access-mirrors
.venv/bin/python scripts/verify_data.py
.venv/bin/python scripts/prepare_data.py
.venv/bin/python scripts/run_sahg1_lane.py --verify-recorded
.venv/bin/python -m pytest -q
.venv/bin/ruff check src scripts tests
python -m compileall -q src scripts
node --check docs/assets/app.js
git diff --check
```

Observed results:

- `data/training_features.tif`: 418,912,844 bytes; SHA-256 `4371c82e3b8339b807bdffcf4ef59a225520fe2988d521be208ae33743123bc5`; restored from the owner-supplied public GitHub mirror at `buffedlizard55-lab/GEMSDOE`, ref `c0c06ac82178f26b94fce3397036ef8f12a2f3a0`. **Integrity verified; organizer provenance not authenticated.** This is not a bypass of the DrivenData login.
- Bridge verification: footprint `5,167,373` pixels matched expectation; `labels.tif` and `existing_faults.tif` had `60,988` positives each and XOR 0; `sample_submission.tif` had the same positive set. These are local pixel-set checks, not an organizer score.
- `data/prepared/features.npy`: shape `(5,167,373, 30)`, SHA-256 `a4ca25b2a18f6f6637f0247367cc6235a1366eb8475f77b18cd0285e62232dc8`; 27 model/base feature columns plus three arc descriptors. Input hashes and column names are in [`evidence/data_preparation.json`](../evidence/data_preparation.json). The large raw raster and prepared array are ignored by Git.
- `scripts/run_sahg1_lane.py --verify-recorded` returned `verified=true`, `experiment_rerun=false`, `ok_to_submit=false`, verdict `negative`. It reproduced/checked the frozen receipt only; it did not re-run the experiment.
- After the initial test run exposed the shallow checkout's missing source history, `git fetch --unshallow origin` restored the history required by the immutable receipt verifier. The complete test suite then passed: **181 tests passed**. Ruff, compileall, JavaScript syntax check, and `git diff --check` passed.

The tracked `data/manifest.json` and `evidence/data_verification.json` were refreshed by `scripts/verify_data.py`. The refreshed inventory omits `data/bridge/example_submission.tif` because that path is not present in this checkout; `sample_submission.tif` is present. This is an inventory irregularity, not evidence that the example file was downloaded.

## Review of the GEMSDOE32 high-scoring artifact claim

The user-provided `0.2778` for `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` is **not ORGANIZER-CONFIRMED** in the evidence available here: there is no artifact-linked submission-page receipt. The README's previously recorded peer forensics reconstruct geometric ancestry: the GEMSDOE32 raster has 37,654 positive dots, equals the 44,090-dot GEMSDOE25 raster after removal of dots within 200 m of the provided catalogue, and equals the GEMSDOE31 40,199-dot reference after an additional 2,545-dot catalogue-clearance removal. This supports an emission-budget / flank-pruning explanation, not a causal statement about geological discoveries or hidden-set TP/FP.

A plausible metric mechanism is that the asymmetric DTI (`alpha=0.2`, `beta=0.8`, 300 m triangular kernel) can reward reduced false-positive mass more than a corresponding loss of distant true-positive mass. That is only a hypothesis about the *metric geometry*. The hidden-set confusion components are unknown; local catalogue recovery is not a leaderboard score. The brief's `0.3195` and `0.4413` leaderboard figures conflict and neither is an artifact-linked receipt in this workspace. No claim that a new model beats either value is justified.

## Ranked hypotheses for a future, newly authorized experiment

No expected DTI is forecast. Ranking is decision priority by mechanism, likely leverage, and cost—not a prediction of leaderboard rank. “Not found” below means not found in the inspected repository code and the cited sibling summaries, not proof of global novelty.

| Rank | Hypothesis; layers / physical signature | Why it could locate a missing fault | Difference from inspected implementation | Mimic / data viability / cost |
|---|---|---|---|---|
| 1 | **Fold-local incremental SAHG1 × OOF multi-physics model**: existing strike-projected LiDAR scarp `G_strike`, stable-Th-controlled K/U alteration `R_alt`, and basement/strain step features joined to the 27-column cached model stack; train-only nuisance residualization. Target is *conditional interaction / incremental value*, not another weighted raster. | A concealed fault may co-locate directional surface deformation with a chemically mobile-element response and a basement discontinuity; the visible-fault-only holdout assesses recovery of held-out segments, not catalogue extension. | SAHG1 has a standalone result and an OOF multi-physics baseline exists, but the integrated fold-local feature/residualization test is the documented next step and has not been validated as a joint model. | Main mimics: acquisition block, roads/mining access, lithologic contact, and pluvial shorelines. Required feature stack is now staged and hash-checked locally; no new external source is needed. Medium implementation cost. Benefit unknown; highest priority because the comparison baseline exists. **Blocked before any experiment by absent lane assignment and the literal lattice-overlap gate.** |
| 2 | **Scale-consistent drainage diversion / paired channel offset**: available `det_elev` and local relief, deriving channel graphs and persistent along-channel displacement/azimuth across scales. | A fault may divert or offset drainage even where no scarp is preserved; compare channel geometry rather than ridge brightness. | The inspected feature stack contains DEM elevation/slope and relief, but no named drainage-graph displacement feature was found. Sibling summaries emphasize ridges, gap closure, lineaments, tips and stepovers rather than this graph relation. | Mimics: lithologic contacts, pluvial shorelines, road ditches, drainage capture. The existing elevation product is available but its resolution/coverage may limit small-channel mapping. Higher-resolution follow-up would require free official USGS 3DEP elevation tiles; the official portal is documented at [USGS 3DEP Data Tools](https://www.usgs.gov/3d-elevation-program/data-tools), but tile-by-tile coverage and byte receipts have **not** been checked here, so that variant is not yet viable. High cost. |
| 3 | **Multi-scale potential-field edge-phase concordance**: cached RTP/TMI and gravity anomalies/gradients; co-located edge phase and orientation persistence at more than one scale. | Basement discontinuities can be expressed in potential fields beneath alluvium without a visible surface break. | The baseline contains raw/gradient geophysics and generic multi-physics fitting; explicit cross-scale *edge-phase concordance* was not found by name in the inspected implementation. Redundancy risk is high. | Mimics: lithologic contacts, remanent magnetization, flight-line leveling seams. All required bands are already in the cached stack. Medium-high cost; gain unknown. |
| 4 | **Confound-controlled thermal/radiometric incremental-value test**: local GDR temperature/probe and GeoDAWN K/U/Th products conditioned on slope-position, relief, roads, claims and acquisition block; spatially blocked ablation rather than a site-proximity score. | A fault conduit can support thermal/chemical expression; ask whether this evidence adds localization beyond where people flew, drove, mined, or mapped. | Thermal/radiometric corroboration exists in previous methods, including the inspected GEMSDOE36 summary. Novelty would be the strict incremental-value and nuisance-residualization design, not the data layer itself. | Mimics: lithology, measurement siting, roads/claims, flight coverage. Existing local inputs exist; no new source required. Low-medium cost; high expected chance of a null. |

## Next action and stop rule

The top-ranked experiment must **not** run until there is an explicit assigned method paragraph and a prospective decision about the synthetic spacing-5 calibration raster in the novelty registry. It would then require, before dot placement: each raw feature and transform alone tested for leakage on the exact holdout (both AUC polarities); a pre-placement surface comparison; and an immutable fixed fold/buffer/seed. If these gates pass, use the shared evaluator, pooled DTI, and a spatial-block 95% CI, then compare against the same-protocol OOF baseline `0.13000` (HOLDOUT-DTI, `gems-segment-pooled-v1`, 60,988 withheld positives, 95% CI `[0.11565, 0.14396]`). No experiment may remove or relabel a comparator after observing its overlap. The 3-experiment / 2-hour budget remains unchanged.

## Three-pass review

1. **Pass 1 — complete the safe prerequisite:** restored the pinned owner mirror, checked label/footprint consistency, built the ignored feature cache, recorded the available hypotheses and verified the frozen SAHG1 receipt without rerunning its experiment.
2. **Pass 2 — bugs and assumptions:** the first test run failed because this checkout was shallow and lacked the frozen source commit; fetched full Git history, then the receipt test passed. Also found the rendered SAHG1 summary reported only method-lane / peer novelty and omitted the separate failing literal all-entry calibration-lattice comparison. Updated the site generator and rebuilt the page to disclose that failure. The missing `data/bridge/example_submission.tif` path in the old manifest was confirmed absent and is now omitted from the refreshed inventory.
3. **Pass 3 — acceptance re-check:** rebuilt the site from receipts; confirmed the research page shows four prospective hypotheses, source caveats, the run card and a negative / no-submission decision. Full suite: **181 tests passed**; Ruff, compileall, JS syntax check and `git diff --check` passed. No candidate experiment, new TIFF, upload or score claim was made.

## Trusted source links for manual review

- [USGS GeoDAWN official data release, DOI 10.5066/P93LGLVQ](https://www.sciencebase.gov/catalog/item/657e1d85d34e23d3533209f7) — supporting geophysical / acquisition provenance, not a unique fault label.
- [USGS 3DEP data tools](https://www.usgs.gov/3d-elevation-program/data-tools) — official potential source for higher-resolution elevation; tile coverage not checked in this session.
- [DrivenData GEMS problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) — required format / objective, but this site is not accessed automatically under the repository's competition-terms policy.
- [GEMSDOE32 project page](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html) — team-authored method and score claim; not an organizer receipt.
- [GEMSDOE25 project page](https://buffedlizard55-lab.github.io/GEMSDOE25/) — team-authored comparator description.
- [GEMSDOE31 project page](https://buffedlizard55-lab.github.io/GEMSDOE31/docs/) — team-authored comparator description.
- [GEMSDOE28 project page](https://buffedlizard55-lab.github.io/GEMSDOE28/) — team-authored comparator description.
- [GEMSDOE30 project page](https://buffedlizard55-lab.github.io/GEMSDOE30/) — team-authored comparator description.
- [GEMSDOE27 project page](https://buffedlizard55-lab.github.io/GEMSDOE27/) — team-authored comparator description.
- [GEMSDOE33 project page](https://buffedlizard55-lab.github.io/GEMSDOE33/) — team-authored comparator description.
- [GEMSDOE36 project page](https://buffedlizard55-lab.github.io/GEMSDOE36/docs/) — team-authored comparator description.
