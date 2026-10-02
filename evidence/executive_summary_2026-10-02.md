# GEMS DOE 24 — completed experiment, blocked promotion

## Decision

**No new weekly slot. No verified new leaderboard improvement.**

H19-5’s owner-reported **0.1922** already exceeds H19-4’s **0.1894**. The official
2026-10-02 leaderboard snapshot is **DARD 0.3195**, not the older .3049/.3168
snapshots. Account scores do not independently authenticate a particular file.

The new candidate produces modest paired learning gains, but is below both H19
as-emitted diagnostics. Original current-best OOF reconstruction is absent, and
required source coverage is incomplete. It therefore remains an experiment.

## What ran

- Restored the 419 MB owner feature bridge, with full pinned hashes; prepared a
  592 MiB matrix of 5,167,373 × 30 float32 physical/LiDAR descriptors.
- Read all 21 supplied project source pages and selected method/registry code,
  preserving commits and source hashes.
- Preregistered four ranked hypotheses before new detector implementation;
  tested H24-2A directional annular gradient/rim support.
- Acquired official USGS documents and BLM closed claims anonymously on CI:
  702,794 case IDs checked, 197,346 unique accepted legal-land geometries.
- Audited training labels first, then individual H19 outputs.
- Refit physics / physics+arc, each raw / training-only nuisance-residualized,
  across four spatial regions: 16 detector fits, whole-component supervised
  exclusion, 1.5 km collar, fixed 2.45% maximum ridge budget, no zero backfill.
- Produced a full experimental GeoTIFF and audited that exact SHA-256.
- Completed three review passes; 55 tests, lint/style checks, package build,
  JavaScript syntax, local links and download checksum checks pass.

## Actual local results

These are catalogue simulations, **not public leaderboard scores**.

| Method | Dense DTI | Sparse DTI |
|---|---:|---:|
| Physics raw | .15169 | .05843 |
| Physics + arc raw | .15308 | .05961 |
| Physics residualized | .15245 | .05775 |
| Physics + arc residualized | **.15568** | **.06321** |
| H19-4 as-emitted diagnostic | .17043 | .06850 |
| H19-5 as-emitted diagnostic | .16944 | .06813 |

Candidate versus matched physics raw: **+.00399 dense / +.00479 sparse**;
3/4 sparse folds improve, no fold loses >.01. It also beats the matched
residualized baseline, but fails the stronger historical diagnostic veto.
As-emitted historical outputs are not reconstructed OOF models.

## Available-input nuisance audit

Only clipped-source road proximity, true closed-claim distance and the available
Area1 membership indicator enter these tests. **Not the full required audit.**

| Raster | Held-out AUC | Holm p | Margin vs grouped-null p95 | Meaningful available-input flag |
|---|---:|---:|---:|---|
| Labels | .52833 | .020 | .00804 | No |
| H19-4 | .56596 | .020 | .04602 | Yes |
| H19-5 | .56459 | .020 | .04740 | Yes |
| Exact new candidate | .53477 | .020 | .01567 | No |

The effect rule requires adjusted p≤.05 **and** AUC≥.55 **and** margin≥.02.
A small p-value alone is insufficient. The candidate's available-input flag
falls below this rule, but this is **not proof of unbiased geological discovery**.
Roads/claims can correlate with real geology; C2ST is association, not causal
identification. The paper's accuracy statistic is adapted explicitly to AUC.

199 grouped null refits and 99 valid shift diagnostics were used per raster.
The candidate had one geometry shift with a single-class held-out fold; undefined
AUC is not replaced by chance. The correction retries on cohort support only,
records the rejection and never filters by statistic. This conditional shift
sensitivity test is not an exact spatial null. Grouped primary remains unchanged.

## Why H19 is plausible, not causally explained

The reviewed H19 mixtures are dominated by shared topographic/scarp terms:
92% L3/L4 weight in H19-4's covered area versus 90% in H19-5, with changed internal
openness/thermal/tip weights, gap CDF matching and 2.50%/2.45% requested budgets.
Thin well-localized candidates and false-positive restraint plausibly help DTI.

The “four independent lines” wording is not statistical independence: inputs and
priors are shared. Byte inspection finds 123,779 / 121,131 positive pixels, both
zero at all 60,988 catalogue pixels; Jaccard .777234. The reported .0028 score
difference is not a controlled causal ablation, nor proof of new faults.

## Deliverables

- Clean local/live website with direct first-screen reference download,
  research/results and source-audit pages.
- Dedicated `docs/executive-summary.html` with exact upload checks and a separate
  short copyable submission comment.
- Unique reference:
  `gems24-reference-h19-5-20261002-80d47e1ab2ee-nan.tif`.
  Single-band float32, EPSG:32611, 3730×3292, 100 m, finite [0,1] inside,
  NaN outside. Full SHA-256:
  `ec1f9b56b83ce33cad781ceb9f104b18fb4f2ff785263a4e89616af4aabdee8d`.
  It is byte-identical to H19-5, not a new prediction. Do not repeat-upload it.
- Separately labelled zeros-outside fallback, single-TIFF ZIP and format receipt.
- Small rejected experimental raster/model retained under
  `evidence/experiments/h24-2a-clipped-road-v1/`, not advertised for a slot.
- Auditable JSON/CSV experiment, audit, source, provenance, irregularity and
  three-pass receipts; README/AGENTS standing charter and reproduction commands.
- Scheduled read-only source refresh / Pages artifact workflow implemented;
  stale and unknown snapshots are labelled, never invented.

## Remaining work and honest blockers

1. **Operational blocks:** verified coordinates/membership for Winnemucca,
   Fallon, Hawthorne and Tonopah are absent. Area1/Area2 are not four blocks.
2. **Road boundaries:** the original mirror clips to a tight geographic window.
   Padding the seed raster cannot recover missing outside-window roads. Official
   buffered acquisition is implemented, but its workflow did not execute after
   GitHub authentication/push failed. Current results remain provisional.
3. **Current-best OOF:** reconstruct the H19 source/artifact/cache under the same
   masked split/metric protocol. Diagnostics alone cannot certify the original
   .21413/.08667 claims or a same-protocol best-model win.
4. **Scientific validity:** incomplete catalogue negatives, transductive physical
   context and residual variance dependence remain. Annular support can respond
   to non-fault contacts/erosion; independent expert/field evidence is needed.
5. **Provenance:** owner-mirror hashes are not independent organizer authentication;
   ambiguous aliases were excluded. Initial preregistration does not enumerate
   every numeric implementation setting; this is disclosed, not rewritten.
6. **GitHub publication:** REST/GraphQL returned 401 and push had no usable
   credentials. Reconnect GitHub in Arena. No PR, merge, buffered-road CI success
   or public Pages deployment is claimed. All local work is saved on the fixed
   session branch; the live preview is not a public-deployment receipt.
7. **Original prompt:** the full uncondensed text was unavailable. The inherited
   quoted charter and all active available constraints are preserved; unseen
   wording or missing links are not fabricated.

After reconnection: run buffered roads; obtain operational memberships; audit
labels first; rerun the frozen arms on corrected sources; reproduce the current
best; audit the exact candidate; promote only on a genuine win. Common-resolution
contact persistence / directional variograms remain ranked next hypotheses;
raw 3DEP drainage-offset work is deferred until coverage is byte-verified.
