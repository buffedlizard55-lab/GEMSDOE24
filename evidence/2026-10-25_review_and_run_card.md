# HISTORICAL INITIAL REVIEW — SUPERSEDED

> This file records an early pre-experiment stop from 2026-10-25. Its statements that no experiment was run, no registry rasters were available, and no TIFF was generated are **historical and superseded** by [`evidence/aspc_run_card_20261025.json`](aspc_run_card_20261025.json), [`evidence/aspc_run_20261025.json`](aspc_run_20261025.json), and [`knowledge/10_ASPC_findings_2026-10-25.md`](../knowledge/10_ASPC_findings_2026-10-25.md). The later record reports one preregistered ASPC experiment, a unique research-only TIFF, and a negative promotion verdict. Do not use this file as the current run card.

# GEMSDOE24 repository review and experiment decision — 2026-10-25

## Scope and evidence boundary

This review follows the current request's three-experiment/two-hour cap and duplicate-lane rule. It is a repository/site review, not an organizer score audit. The linked sibling sites were read at the user-provided URLs; their own descriptions, scores, and projections are **team-published claims**, not organizer receipts. The numbers below are labelled at point of use to avoid promoting those claims into confirmed results.

- GEMSDOE24 reports H25-1 dotted-H19-5 and an owner-reported H19-5 anchor; its page says the candidate is unscored and owner decision required: https://buffedlizard55-lab.github.io/GEMSDOE24/
- GEMSDOE25 describes D2.8 as a conditional model result, not slot-approved: https://buffedlizard55-lab.github.io/GEMSDOE25/
- GEMSDOE27 describes T-v2 gap closure, while noting limits of catalogue-proxy validation: https://buffedlizard55-lab.github.io/GEMSDOE27/
- GEMSDOE28 describes H36-1 / H38-1 and their holdout status, including a failed far-field arm: https://buffedlizard55-lab.github.io/GEMSDOE28/
- GEMSDOE30 describes the D2.8 off-catalogue emission and its source's reported score; it explicitly says the exact file is a re-encoding, not a new model: https://buffedlizard55-lab.github.io/GEMSDOE30/
- GEMSDOE31 reports H27-4 and detector-union proxy results: https://buffedlizard55-lab.github.io/GEMSDOE31/docs/
- GEMSDOE32 explains H33-2-B2 as a flank-pruned H27-4 base and explicitly calls its projected score a model, not a score: https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html
- GEMSDOE33's page contains ambitious PINN / analogue-transfer claims, but also states its score attribution is unsupported: https://buffedlizard55-lab.github.io/GEMSDOE33/
- GEMSDOE36 describes an Anderson-PINN candidate, but provides no organizer-confirmed artifact receipt on the page reviewed: https://buffedlizard55-lab.github.io/GEMSDOE36/docs/

The specific H33 value **0.2778 is TEAM-PUBLISHED / OWNER-REPORTED, not ORGANIZER-CONFIRMED** based on the source material available in this checkout. The values **0.3195**, **0.2708**, **0.2750**, **0.2632**, **0.2600**, **0.2477**, and **0.2449** in those pages or the prompt likewise must not be attributed to this new candidate or treated as receipts. GEMSDOE32 itself says no organizer score exists for its artifact. These are external claims about other artifacts, not this session's HOLDOUT-DTI.

## Why the reported high-scoring family may work (not causal proof)

The best-supported mechanistic explanation across the pages is a combination of (i) high spatial association of emitted pixels with a topographic/structural detector family and (ii) budget geometry: removing redundant emissions with little triangular-kernel credit can improve an asymmetric distance-weighted Tversky objective. GEMSDOE32 says its B=2 flank-pruned file removed catalog-adjacent pixels; GEMSDOE31 and GEMSDOE28 discuss similar pruning and spacing/repacking. This is plausible metric arithmetic, not proof that those pixels correspond to faults or that a specific geological mechanism caused the reported score. The holdout catalogue is an imperfect proxy for genuinely missing faults; it may reward catalogue-adjacency and cannot independently validate novel hidden structures. The pages themselves report proxy disagreement, failed arms, and model projections. Consequently, extrapolating from a sibling site's reported result to a new public score is unsound.

## Ranked candidate hypotheses (research proposals, not tested results)

Novelty is bounded to inspected active code (`src/gems/*.py`), its documented hypotheses, and the linked pages above. Because this ecosystem has many sibling repositories and the linked pages are not their full source trees, “not found” does not prove globally unprecedented.

| Rank | Hypothesis and layers | Physical signature / missing-fault rationale | Difference found in this repo / sibling-page scan | Expected benefit (planning only) / cost |
|---|---|---|---|---|
| 1 | **Scale-consistent drainage-divide deflection**: DEM-derived channel centerlines, local valley azimuth, and lidar scarp orientation already represented in the feature stack. | Detect a persistent, fault-normal drainage deflection or paired channel offset whose orientation remains coherent across DEM scales; this targets subtle, unmapped structures expressed as displaced drainage, not simply a bright scarp or a catalogue extension. Main mimic: lithologic contact, beheaded stream, road/ditch, or glacial/tectonic drainage capture. | The active pipeline has relief/slope/scarp and lineament-family features, but no named drainage-network displacement/deflection graph feature was found in the inspected code and page summaries. Sibling projects did explore terrain ridges, gap closure, and lineaments; this is a distinct geomorphic relation, not a claim that drainage has never been tried anywhere. | Unknown; plausible small positive if held-out gains survive confound controls. Medium-high cost: derive stable channel graph, line correspondence, controls, and fold-local features. No defensible numeric projection. |
| 2 | **Multi-scale potential-field edge phase concordance**: RTP/TMI and gravity anomaly plus their existing gradient layers. | A lineament supported by phase/edge-location agreement across magnetic and gravity scales may reveal basement discontinuity beneath alluvium, where no surface scarp exists. Mimics: lithologic boundaries, survey leveling seams, remanent magnetization. | Existing code exposes raw/gradient fields and arc features, and sibling pages describe multi-physics fusion; the proposal changes the target to cross-scale edge-phase *co-location*, which was not found by name in inspected sources. Strong redundancy risk. | Unknown and probably limited because related geophysical fusion is mature here. High cost; leakage canary and acquisition-block controls essential. |
| 3 | **Drainage-network topology at fault intersections**: DEM drainage graph, existing fault-tip/junction geometry only from visible training segments. | Persistent stream capture / aligned tributary junction asymmetry near independently inferred structural intersections could identify concealed relays and stepovers. Mimic: basin outlet control, lithologic contrasts, anthropogenic channels. | Sibling pages already describe tip protection, stepovers, and topological graph features; this candidate is only distinct if the drainage graph is a separately engineered observation and all fault-derived inputs remain fold-local. | Unknown; medium cost. High risk of rediscovering the already-tested step-over family. |
| 4 | **Hydrothermal surface-response negative-control contrast**: official geothermal well/probe/thermal layers plus DEM-derived slope-position and local relief. | Test whether thermal/alteration evidence adds fault-localization beyond elevation, accessibility, and survey block; target concealed active conduits rather than the fault trace itself. Mimic: roads, hot springs controlled by lithology, measurement siting bias. | Thermal/geothermal corroboration has appeared in sibling pages (including GEMSDOE36), so this is not a new raw-data feature; novelty would be a preregistered confound-controlled *incremental-value* test. | Expected gain unknown; low implementation cost, high chance of null/negative. Official source data availability must be verified and all probe data kept training-fold local. |

**Ranking is decision priority, not predicted DTI.** Candidate 1 is selected for a future test only because it has a mechanism distinct from generic ridge/scarp and its inputs appear to exist locally. It is not implemented or validated in this session.

## Three review passes performed

1. **Initial implementation/review:** inspected active instructions, README status/charter, repository files, active holdout/writer implementations, and existing evidence; read the linked sibling pages. Recorded the scope and evidence-class boundaries above.
2. **Bug/assumption review:** verified that the required training raster/cache and exact sibling raster bytes are absent; confirmed the evaluator API named in the requested protocol is not a repository path. Rejected inference of uniqueness, score, or holdout result from page text or projections.
3. **Acceptance re-check:** compared the run-card requirements against available evidence. Required scientific/duplicate checks cannot be run, therefore emitted a negative card and withheld a purported submission. Ran the existing repository test suite from an isolated `.venv`: **105 tests passed** (test result, not HOLDOUT-DTI or organizer score).

## Experiment/unique-file gate: STOP (negative result)

The requested experiment could not be run honestly in this checkout. `data/bridge/sample_submission.tif`, `data/bridge/labels.tif`, external derived rasters, and historical candidate rasters exist, but the required `data/training_features.tif`, cached feature matrix/stack, and generated holdout cache do not. The active checkout also lacks `out/` candidate outputs. The `src/gems/holdout.py` implementation exists, but a script named exactly `evaluate_holdout.py` and the requested `submission_writer.py` are not present; the available writer is `scripts/build_submission24.py`, which is a packaging tool, not a substitute for the requested evaluator. Therefore there is no valid way to derive training-fold-only features, withhold whole fault segments with the requested buffer, run the required feature-alone leakage canaries, obtain paired DTI confidence intervals, or certify a candidate against the current holdout best.

The duplicate-lane check is likewise not complete: the linked pages expose summaries and selected links but the registry raster bytes for all sites are not present locally. The user-specified surface rank-correlation and final-dot 3-px overlap checks cannot be truthfully reported without those exact raster bytes and the shared footprint/template alignment. No transformation of an old submission can be called a unique scientific candidate without these checks.

**No experiment was launched; experiment count = 0. No HOLDOUT-DTI number or 95% CI exists for this session. No unique TIF was generated. No weekly submission slot should be spent.** This is an intentional protocol stop, not an assertion that no future improvement is possible. A named, newly generated file cannot simultaneously meet the user's own validation and duplicate-drift requirements with the missing inputs; generating an arbitrary file would be a compliance failure.

## Run card (negative)

```json
{
  "hypothesis": "Scale-consistent drainage-divide deflection; ranked first for a future test, not implemented",
  "mechanism": "DEM-derived channel offsets/deflections with orientation persistence across scales could expose subtle unmapped structures",
  "named_non_fault_mimic": "Lithologic contact or anthropogenic drainage/road ditch",
  "holdout_dti": null,
  "holdout_dti_status": "NOT RUN: feature stack/cache and training_features.tif missing; no evaluator result or 95% CI",
  "withheld_positives": null,
  "withheld_positives_status": "NOT RUN",
  "correlation_overlap_vs_registry": null,
  "correlation_overlap_status": "NOT CHECKED: exact sibling registry raster bytes unavailable locally; do not infer uniqueness",
  "raster_sha256": null,
  "validator_output": {
    "no_nan_inside_footprint": "NOT RUN (no candidate TIFF)",
    "values_in_0_1": "NOT RUN (no candidate TIFF)",
    "crs_shape_transform_match": "NOT RUN (no candidate TIFF)",
    "template_available": true,
    "candidate_available": false
  },
  "submission_name": null,
  "submission_note": null,
  "verdict": "negative"
}
```

## Concrete unblock sequence

1. Restore the competition feature TIFF and the matching prepared/cache outputs using the repository's documented data restore and preparation scripts; verify hashes against receipts before using them.
2. Resolve the shared-tool naming/protocol gap once in the common pipeline: identify the correct evaluator and writer entry points, and add/repair the whole-segment buffered holdout and pixel-exact visible-fault masking required by this run card.
3. Freeze the exact fold geometry and seeds; test each feature alone before any ensemble. Any AUC above 0.90 is a leakage alarm until explained. Report pooled DTI with alpha 0.2, beta 0.8, 300 m triangular kernel, withheld positive count, evaluator version, and block-bootstrap 95% CI.
4. Download/obtain the exact candidate registry rasters from the specified sites (only from permitted hosts/means); compare rank-correlation on the surface before placement, then 3-px dot overlap and correlation on final dots. Stop if either user's threshold is exceeded.
5. Only if a fresh, non-duplicate candidate beats the current comparable holdout best should the shared writer emit a uniquely named TIFF. Re-open and independently validate bytes; offer it as downloadable only with an explicit status and distinct note. No automatic DrivenData access/upload.
