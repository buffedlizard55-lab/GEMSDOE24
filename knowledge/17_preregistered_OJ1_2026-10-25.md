# OJ1 preregistration and continuation audit — 2026-10-25

Read the full owner brief embedded in README first. Maximize P(Win); own the outcome without inventing a score.

## Scope and limits

The supplied protocol references a single assigned method paragraph, but none is present. OJ1 is explicitly a **provisional, unassigned research lane**, never a slot selection. Do not rerun stopped ASPC/MTR1/SAHG1/CON or the three UNIQUE experiments. Budget here: **one fixed experiment**, no tuning, maximum three experiments/two hours. Use shared SegmentHoldout, novelty checks, and submission writer; no private evaluator. Stop on any duplicate; do not try a second hypothesis to evade the lattice.

The priority registry is a pinned snapshot of nine team repositories, not all unpublished parallel work. Rehydrate comparison-only blobs via GitHub with exact SHA-256 verification. No previous submission is an input to OJ1. No automatic DrivenData access. Official hosts other than GitHub are outside this environment's network allowlist; scientific interpretations below are hypotheses, not freshly verified discoveries.

## Four new candidate operators, ranked before implementation

No numerical DTI improvements are projected. Ranking is qualitative judgment, not evidence. Novelty means absent as an explicit operator in the reviewed local source; it is not a global-priority claim.

| Rank | Operator and layers | Proposed missing-fault signature / rationale | Non-fault mimic | Difference from implemented work | Expected improvement / cost / feasibility |
|---|---|---|---|---|---|
| 1 | **OJ1: coherent orientation junctions**. Cached LiDAR `strike`, `coh100`, `step_max`, `lapneg_max`, `lappos_max`, `valid`. | Individual coherent scarps with inconsistent *neighborhood doubled-angle orientations*, weighted by step and balanced curvature. Hypothesis: a short cross-fault branch at a junction may be omitted from the mapped main trace. No catalogue distance/tip prior. Target is a fault trace, not a vent. | Dendritic channel confluences, road junctions, landslide scarps. | ASPC uses uphill-facing amplitude × curvature × cross-bank veto; SAHG1 uses strike persistence. OJ1 deliberately measures the converse: **orientation dispersion among individually coherent cells**. Prior tip-gradient proposal uses coherence loss, not circular orientation dispersion. | Highest among these speculative options, but likely recall penalty for long isolated faults; low CPU cost; all required team-derived caches present. **Selected once.** |
| 2 | **Radiometric compositional balance break**. Cached GeoDAWN K, Th, U. | Gradient of `log((K+epsilon)/sqrt((Th+epsilon)(U+epsilon)))` localized where K varies but the Th/U log-ratio is locally stable. Could isolate cross-cutting alteration fronts on short concealed branches. | Parent-rock compositional contact; transported radiometric sediment. | Existing stable-Th alteration uses scalar K/U contrasts. Proposed operator is a two-balance compositional gradient; not simply a K/Th enrichment score. | Uncertain, probably limited by flight-line resolution; low cost; caches present. Do not claim alteration without mineralogy. |
| 3 | **Antislope scarp en-echelon texture**. Cached LiDAR upface, downface, strike, coherence. | Local spatial autocorrelation of antislope-step *orientation residuals* along two offset parallel transects; tests distributed oblique splays rather than catalogue-tip continuation. Missing short splays can be suppressed by ridge continuity detectors. | Agricultural berms; repeated shorelines. | Not ASPC's local amplitude product or catalogue relay-rung methods; needs lagged cross-transect covariance. | Uncertain gain and substantial false-positive risk; medium cost; cached descriptors suffice for an approximate, not resolved, test. |
| 4 | **Radiometric/terrain support boundary negative control**. LiDAR valid fraction and GeoDAWN acquisition-block mask. | Test whether apparent junction enrichment persists away from coverage seams and separately within each survey block. This is a falsification experiment, **not a new physical fault detector**. | Mosaic seam / acquisition footprint. | Existing nuisance audits test predictability; this proposes an explicit support-boundary-stratified OJ1 ablation. | No projected gain; low cost; cached derived block coordinates are approximate, not official survey polygons. |

No candidate needs a new external download, and no unavailable data source is represented as viable. The low-resolution maxima cannot resolve subpixel crest/toe pairing or prove intersecting faults.

## Fixed OJ1 experiment

- Decode the quantization exactly from `data/external/lidar_scarp_features.json` (`0` missing, `1+round(254*t(x/xmax))`). Five signal channels plus valid fraction; test **every raw source and every intermediate transform separately** with shared leakage canary, both AUC polarities and every spatial fold.
- Support: template footprint AND every required encoded channel >0 AND decoded valid fraction >0.5. Missing cells contribute zero neighborhood weight, not a synthetic north-striking orientation.
- Compute `C = coh*cos(2*strike)`, `S = coh*sin(2*strike)`. A fixed 5×5 normalized window gives `dispersion = 1 - hypot(sum(C),sum(S))/sum(coh)`; require >=50% support in the window. Reflect-free constant-zero padding; denominator explicitly normalized by valid weights.
- `balance = 2*sqrt(lapneg*lappos)/(lapneg+lappos+1e-8)`. `step = decoded_step / 1 m/m` (already in [0,1]). `surface = dispersion * coh * balance * sqrt(step)` on supported cells. No label-derived normalization, learning, or feature selection.
- Shared `SegmentHoldout(buffer_px=15)`: whole segments withheld everywhere, quadrant buffers, pixel-exact visible mask, pooled DTI alpha=.2 beta=.8, 300 m triangular kernel; 1,999 spatial-block bootstrap draws. Dense public-catalogue proxy, not an estimated hidden score.
- Raw surface novelty against **every** raster in `registry/priority_rasters.json`, including calibration controls, before placement. If duplicate: log and stop; no dots, no TIFF.
- If surface passes and canaries pass: priority-Poisson emission with min separation 3 pixels, fixed budget `round(.0073*fold.valid.sum())`, eligible surface>0 and not fold.visible. Compare recorded same-protocol baseline using its full run card, not an assumed leaderboard conversion. Baseline remains independently unverified this session unless replayed.
- Final dots: same fixed emission on full support, public catalogue pixel-exactly excluded. Write via shared writer as **RESEARCH-NOT-SUBMISSION**; immediately check exact final-dot registry comparisons, then stop if duplicate. Preserve a negative packet only; no retuning, no selection, no upload. Final file is not scientifically unique when the literal overlap gate fails, even if bytes differ.
- Run card must retain exact numerical canaries, holdout version/positive count/CI, correlations and overlap, raster hash and validator. `submission_authorized=false` regardless of numerical success: selector/quota/exact-file nuisance audit are separate and not available to this lane.

## Continuation defects to fix without rewriting history

1. `build_unique_submission3.py` calls `DIST_DECAY_PX=300` a 300 m decay. At 100 m/pixel the executed decay was **30 km**, not 300 m. Its recorded result remains a result of the executed code, not the advertised local extension mechanism. Freeze the historical script rather than silently change its output or rerun the stopped lane.
2. Its leakage canary omitted catalogue proximity and the composite signal. Do not advertise complete feature screening for that packet.
3. `preflight._card_evidence` accepts a self-asserted, hash-bound promote/authorized card without actual gate or selector evidence. Remove that positive shortcut; an absent independently checked selector implementation must fail closed.
4. Site explanations that NaN *caused* the portal rejection are unsupported. Whole-array finite [0,1] verification rules out one possible cause only; local validation is not portal acceptance.

## Sources and verification boundaries

- Organizer-owned code: https://github.com/drivendataorg/gems-prize-reference-solution — verify reachable commit/README in this session. Training Tversky is not independent evidence for every evaluation detail.
- Official LiDAR parent program: https://www.usgs.gov/3d-elevation-program — manual-review link; current derived-cache metadata and hashes checked locally, not an independent official certification.
- Official GeoDAWN parent survey: https://doi.org/10.5066/P93LGLVQ — manual-review link; team radiometric products are quantized derived data.
- Structural geothermal context: https://www.osti.gov/servlets/purl/1724082 — retained reference, not fetched in this restricted environment. It does not verify OJ1's novel operator or its efficacy.
- Target/rules/manual review: https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/ and https://docs.nlr.gov/docs/fy26osti/96647.pdf — no portal automation. Competition target is fault mapping; geothermal permeability and vents are not direct labels.
