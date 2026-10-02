# GEMS DOE 24 — evidence before a leaderboard slot

**Goal: maximize the chance of winning DOE GEMS / DrivenData #306 through sound
geological inference, reproducible experiments and honest validation.** A goal
is not a score forecast or a guarantee of winning.

> **Maximize P(Win).** Prefer verified scientific leverage over cosmetic model
> changes, submission fishing or comfortable busywork.
>
> **Own the Outcome.** Resolve data placement and engineering blockers
> autonomously; report negative results and genuine remaining constraints rather
> than passing an unavailable source off as a completed experiment.

[Project site](https://buffedlizard55-lab.github.io/GEMSDOE24/index.html) ·
[Submission/executive guide](docs/executive-summary.html) ·
[Preregistered hypotheses](knowledge/02_preregistered_2026-10-02.md) ·
[Source review](knowledge/03_verified_sources_2026-10-02.md)

## Current decision

<!-- STATUS:START -->
**No new slot-eligible candidate; no slot consumed.** H19-5 remains a
format-validated reference with owner-reported original public DTI **0.1922**.
The official leader snapshot is **0.3195** (2026-10-02; not an artifact-linked
score for this repo).

Fresh physics → arc+residualized local dense/sparse DTI:
**0.15169 / 0.05843 →
0.15568 / 0.06321**.
These gains are below H19-4/H19-5 as-emitted diagnostics; original current-best
OOF reconstruction is absent. They do not predict a new leaderboard score.

The full requested audit is **BLOCKED**: four-block geography is unverified and
legacy road clipping leaves boundary coverage uncertified. Official buffered
road acquisition is implemented but its workflow could not run after GitHub
authentication/push failed. Claim distances are official, quality-filtered and
buffered. Exact experimental-raster audit complete: **True**
(provisional available inputs, never a full-source pass).

Reference: [`gems24-reference-h19-5-20261002-80d47e1ab2ee-nan.tif`](docs/downloads/gems24-reference-h19-5-20261002-80d47e1ab2ee-nan.tif).
Public PR/merge/deployment are **not claimed**; GitHub reconnection is required.
<!-- STATUS:END -->

## Standing session charter — read this at the start of every session

This section preserves **all active requirements available in this session's
context**, including corrections and scope decisions. The inherited owner's
original quoted charter is also reproduced below. The complete uncondensed
original chat was unavailable in this continuation; do not misrepresent this
record as a verbatim copy of unseen text.

1. Review this repository and the group's websites/source code; resume genuine
   next steps from earlier sessions before proposing duplicate work. Work
   autonomously without asking for data placement, feature preparation or
   routine design decisions. Download/restore into `data/`, prepare, train,
   predict and validate as far as verified inputs and permissions permit.
2. Aim to finish at the top of the leaderboard using PhD-level scientific
   judgment. Verify factual assertions against **official, trusted sources**,
   link them for manual review, collect auditable data/source/knowledge tables
   for subsequent projects, and flag irregularities. Never fabricate scores,
   access, causal discovery, source availability or completion.
3. Study why H19-4 and H19-5 are the group's highest **owner-reported** results:
   `gems19-h19-4-multi-line-physical-corroboration-20261001-691e4dfa-nan`
   **0.1894**, and
   `gems19-h19-5-openness-thermal-corroboration-20261001-e27054cf-nan`
   **0.1922**. H19-5 already exceeds 0.1894. The owner's leader snapshot 0.3049
   and the inherited site snapshot 0.3168 are historical, not current facts.
   Do not infer the score of a particular file from a public account's score
   without an artifact-linked organizer receipt.
4. Before implementing a new detector, write **3–5 genuinely unimplemented
   hypotheses relative to the reviewed work**. Each must name the precise
   layers, physical transform/signature, missing-fault rationale, distinction
   from reviewed methods, expected DTI benefit and implementation cost. Rank
   them. If external data are needed, name a free official source and verify
   practical availability; otherwise explicitly defer that hypothesis. Novelty
   is not a claim about unseen competitors' work.
5. Run a classifier two-sample audit motivated by **Lopez-Paz & Oquab, ICLR
   2017**. Distinguish pixels near mapped faults from far pixels using **only**
   road/trail distance, historic mining-claim distance and categorical membership
   of the **four GeoDAWN operational acquisition blocks**. No geothermal wells,
   sinter, vents, probes, mineral-occurrence substitutions, fault-distance
   features, mapped-fault confidence, or label-derived seams may enter this
   nuisance-only test.
6. Audit **training labels first**, then each relevant prediction raster, and
   the **exact final candidate** before any slot. Refit classifiers for null
   replicates and use spatial separation, effect-size safeguards and declared
   multiplicity control. If meaningful association appears, remove/residualize
   measured confounds on **training-region pixels only**, refit the detector and
   re-evaluate. A spatial holdout from the same catalogue is not sufficient by
   itself to certify robustness to the mapping process.
7. Scientific correction to the owner's premise: C2ST detects **distributional
   association**, not its cause. Roads/claims can themselves correlate with
   geology; non-rejection does not prove absence of bias. This implementation
   explicitly adapts the paper's held-out accuracy statistic to a prespecified
   AUC with refitted spatial randomizations. Block exchangeability is assumed;
   torus shifts on a nonstationary, irregular footprint are sensitivity
   diagnostics, not an exact spatial null.
8. **Never spend a weekly slot unless the candidate beats the CURRENT comparable
   spatially blocked holdout best.** Validate the top hypothesis on the frozen
   protocol, require paired true retraining gains and the exact-raster bias
   audit, and never treat re-ranking an already-binary submission as retraining.
   Missing original H19 OOF reconstruction or a required source blocks
   certification; an arbitrary easier baseline is not enough.
9. Submission: a **single-band float32 GeoTIFF**, matching the template's CRS,
   shape and geotransform, with **finite [0,1] values inside** and NaN outside the
   official footprint. Fix the owner's rejection, “Predicted values must be in
   range [0, 1]”. Give every artifact a unique name/content identifier, an
   obvious **one-click `.tif` download at the beginning of the site**, a separate
   short submission comment and a dedicated executive-summary/instructions
   subpage. Format validity does not authorize a scientific promotion. A
   zeros-outside fallback is separately labelled, not silently substituted for
   the official NaN convention.
10. Clean up GitHub Pages and implement a timestamped automated source feed.
    Distinguish owner reports, team-authored claims, official snapshots, computed
    diagnostics and hypotheses. Unknown scores, including unreported 22/23
    results, remain unknown. Never republish a renamed reference as a new win.
11. Review in **three passes**: (i) implement and verify against sources;
    (ii) find and fix bugs, assumptions and edge cases;
    (iii) recheck this original acceptance scope, reliability and code. Keep the
    review record and limitations. Open a PR from the session branch and merge
    through GitHub if the configured connection permits it; never silently claim
    a merge or a public deployment that did not occur.
12. Arena's **Maximize P(Win)** and **Own the Outcome** remain focal. Follow the
    session's fixed Arena branch, never create/write an orphan data branch, never
    ask for GitHub credentials, and preserve large regenerable datasets outside
    Git. If GitHub authentication fails, the platform connection needs
    reconnection; this is not permission to forge a merge or bypass authentication.

### Inherited quoted owner prompt

> Review the repo; ensure an easy one-click downloadable submission tif exists
> as the prompt describes; read the entire prompt. Formally test whether the
> "geology" signal is actually encoding field accessibility, then remove it:
> train a classifier two-sample test (the ML literature's distribution-shift
> detector, Lopez-Paz & Oquab, ICLR 2017) to distinguish pixels near a mapped
> fault from far pixels using ONLY non-geological confound features: distance to
> nearest road/trail, distance to historic mining claims, and which of GeoDAWN's
> four acquisition blocks (each with different line spacing and flight height) a
> pixel falls in. If it beats its own null distribution by a meaningful margin,
> that confirms the catalogue's shape is confounded by where geologists could
> physically get to (strengthens the scientific case, and identifies exactly
> what to residualize before training the real detector). Run on training labels
> first to validate the premise, then again on our own predicted raster before
> spending a submission slot; if predictions are equally explained by
> road/acquisition-block proximity, the gain is mapping-process overfitting, not
> discovery. A spatially-blocked holdout alone won't catch it since holdout
> faults come from the same biased catalogue. Study/analyze why 19GEMSDOE got the
> group's best live scores (h19-4 …691e4dfa-nan = 0.1894, h19-5 …e27054cf-nan =
> 0.1922) and whether we can beat 0.1894 (leader 0.3049 per user; site says
> 0.3168). Before implementing, produce 3–5 candidate geological hypotheses not
> yet tried, each naming: specific layer(s), the physical signature targeted
> (e.g. edge-detection/curvature transform), why it should catch a fault missing
> from the USGS/INGENIOUS catalogue, and how it differs from everything already
> in the repo; rank by expected DTI improvement and implementation cost;
> validate the top one on the spatially-blocked holdout; if new external data is
> needed, name the specific free official source and verify it is obtainable.
> Put this prompt into the repo README and treat it as the standing starting
> point each session; keep Arena Core Values ("Maximize P(Win)", "Own the
> Outcome") as a focal point. Fix the submission error the user hit — "Predicted
> values must be in range [0, 1]" — and give each tif a unique name plus a short
> DrivenData note; create an executive-summary subpage explaining exactly how to
> submit, obvious on the site's first screen. Autonomously complete the "data
> placement" blocker (download into data/, then prepare_data) with no manual
> input. Verify line by line against official sources with links for manual
> review; flag irregularities; no hallucinations; 3 passes; finish by opening
> and merging a PR to main, stating remaining work and limitations.

The causal and acquisition-spacing statements in that quote are **the request,
not verified conclusions**. Official evidence distinguishes two survey-resolution
areas from four operational blocks; see the source review.

## Reproduce the active pipeline

Python 3.11; CPU-only. Install the recorded package versions:

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/pip install --no-deps -e .
.venv/bin/python -m pytest -q
.venv/bin/ruff check src scripts tests
```

Data placement is autonomous and hash-pinned; no manual Dropbox download is
needed. The 419 MB raster and 592 MiB derived matrix remain ignored:

```bash
.venv/bin/python scripts/restore_data.py --roads
.venv/bin/python scripts/prepare_data.py
.venv/bin/python scripts/build_confounds.py --force
.venv/bin/python scripts/run_geology_audit.py
```

If and only if the four operational blocks remain unavailable, the following
**explicitly exploratory** command records that limitation and keeps promotion
blocked. It does not waive the owner's no-slot requirement:

```bash
.venv/bin/python scripts/run_h24_2_experiment.py --allow-partial-audit-inputs
.venv/bin/python scripts/run_geology_audit.py \
  --candidate out/h24-2a-residualized-experimental.tif
.venv/bin/python scripts/build_site.py
```

`out/` contains the reproducible experimental raster and serialized detector;
these are not advertised as a winning submission. Packaging a new candidate
fails closed unless the matched current-best holdout, training-only intervention,
complete required-family audit and exact file identity all pass:

```bash
.venv/bin/python scripts/build_submission24.py \
  out/h24-2a-residualized-experimental.tif --hyp h24-2a
```

The reference-only bypass verifies the **full pinned H19-5 source hash**, not an
arbitrary `--mirror-of` string. Its comment explicitly says no new score:

```bash
.venv/bin/python scripts/build_submission24.py \
  inputs/gems19-h19-5-powerlaw-budget-multiline-corroborated-20260930-e27054cf-nan.tif \
  --mirror-of h19-5
```

The exact source basename is discoverable with `ls inputs/*h19-5*-nan.tif`.
Nothing in these commands submits to DrivenData or spends a slot.

## What is verified, and what is not

- **Integrity:** the restored owner bridge is pinned to its original hashes,
  including training raster `4371c82e…`, labels `7ba308cc…` and template
  `2176d08e…`. This proves mirror consistency, **not independent organizer
  authentication** of every original byte or band description. Ambiguous
  thermal-conductivity/earthquake aliases are excluded from the new detector.
- **Preparation:** 5,167,373 footprint rows × 30 float32 descriptors; 27 base
  physical/LiDAR columns and three fixed annular descriptors. No training label
  is an input to the arc transform. Global unlabelled physical context and
  normalization are transductive; fitted model/nuisance scaling is training-only.
- **Access data:** real TIGER road/vehicular-trail geometries and BLM **closed
  mining claims**, not MRDS. Claims are PLSS legal-land approximations, not exact
  stake locations or historic workings. Quality prefixes are parsed, unknown/
  degraded records and implausibly broad polygons excluded; 20 km padded seed
  grids preserve source geometry outside the output rectangle, but the inherited
  road mirror was itself tightly clipped: actual nearest-road certification at
  that source boundary remains incomplete. Official buffered road acquisition
  is implemented and blocked by GitHub authentication; this is not a source pass.
- **Acquisition:** Area 1 has priority in the Area 1/2 overlap. Those are **not
  the four operational blocks**. The official report identifies Winnemucca,
  Fallon, Hawthorne and Tonopah, but the fetched geographic extent/flight-path
  inventories do not provide independently verified four-block polygons.
- **Audit:** 199 grouped refitted randomizations, 99 shifts, four spatial folds
  with purged 10 km groups and 1.5 km collars; Holm correction and AUC/effect
  thresholds. Results with Area 1/2 only are labelled provisional and cannot
  pass the required full audit.
- **Experiment:** physics / physics+arc × raw / nuisance-residualized; identical
  splits and frozen detector settings. Four quadrants, whole-component
  supervised exclusion, fixed 2.45% maximum ridge budget, no zero padding.
  Score surfaces include complete NMS halos; catalogue masking occurs **after**
  NMS. Dense and 20%-component sparse truth are simulations using the incomplete
  provided catalogue, not hidden new-fault ground truth.
- **Current-best comparison:** H19 outputs are scored **as emitted** as a
  conservative diagnostic veto. The original H19 OOF caches are absent; these
  diagnostics do not reconstruct the original 0.21413 / 0.08667 claims or certify
  a same-protocol win over the current-best model.
- **Format:** full grid/CRS/dtype/range and pixel-content checks; exact and binary
  DTI both exclude known predictions and known truth. ZIP is one flat `.tif`;
  note is separate. Float32 content hashes distinguish soft probabilities, not
  just thresholded support. A green format check is **not** a green promotion.

## Evidence and repository map

| Path | Role |
|---|---|
| `src/gems/` | exact/binary DTI, safe ridge selection, physical descriptors, strict nuisance inputs, spatial C2ST, training-only residualization, packaging and promotion |
| `scripts/restore_data.py`, `prepare_data.py` | reproducible large-input restoration and preparation |
| `scripts/run_geology_audit.py` | labels first, individual references, then the exact candidate; source/code/environment fingerprints |
| `scripts/run_h24_2_experiment.py` | paired fresh spatial refits and blocked promotion decision |
| `evidence/data_restore.json`, `data_preparation.json` | full input and matrix hashes; provenance caveats |
| `evidence/group_review.json` | all 21 supplied project source pages, pinned commits and consulted files |
| `evidence/access_inputs.json`, `accessibility_audit_v2.json` | actual nuisance families, missing inputs, refitted nulls and effect gates |
| `evidence/h24_2_experiment.json` | all four arms/folds, historical diagnostics, exact experimental-raster receipt |
| `evidence/review_passes.json`, `registry/irregularities.json` | three-pass review, failures and remaining limitations |
| `data/external/audit_sources/` | small official USGS documents, buffered BLM distance bridge and source receipts; raw bulk is external |
| `docs/` | clean site, executive instructions, one-click reference and timestamped source feed |
| `knowledge/` | standing charter, ranked hypotheses, verified sources and interpretation |
| `evidence/archive/`, `archive/legacy/` | superseded reports/code, clearly invalid for promotion; never silently reused |

## Publication and automation

- The official-source fetch workflow is read-only. The small audit bridge uses
  ordinary Git **only on the fixed session branch**; no `public-layers` branch is
  created or updated. Actions' blob host was unreachable from the sandbox, so
  only small derived evidence was bridged; original bulk remains external.
- The website workflow builds a Pages artifact, refreshes official-source
  snapshots on a schedule and never commits generated feed updates to main.
  Publication requires a successful merge/deployment and valid GitHub access.
  A local/live Arena preview is not evidence of a public Pages deployment.
- Reconnect GitHub in Arena if authentication returns 401; never provide tokens,
  passwords or 2FA codes in chat. Do not claim a PR/merge succeeded without its
  returned URL/status.
- Follow organizer limits and current rules on licensed external data, source
  disclosure, AI disclosure and final submission selection. Confirm the
  rules/platform deadline discrepancy through the organizer rather than guessing.

## Next actions that matter

1. Reconnect GitHub and run the implemented official buffered-road acquisition;
   then audit labels first and refit all arms on the corrected source. The
   clipped-road version is explicitly provisional. Obtain coordinate-verified operational block boundaries (or an authoritative
   source-to-block flight-line mapping with a declared, audited derivation).
   Never infer them from the labels, a constant raster or nearest base station.
2. Reconstruct the current H19 spatial OOF reference under the **same** masked
   metric/split protocol; record input/code hashes and disclose transductive
   steps. Do not promote against only a weaker freshly invented baseline.
3. Use the first experiment's negative/positive results as evidence, not a
   hindsight hyperparameter search. Test preregistered common-resolution contact
   persistence or directional variograms next; raw drainage-offset work remains
   deferred until 3DEP coverage is byte-verified.
4. Obtain independent fault/expert validation before claiming discovery. A
   contact, scarp, intrusion rim, road cut and mapped fault can be equifinal in
   these fields. The private leaderboard and Phase 2 expert assessment are not
   available local truth.
5. Complete the authenticated PR/merge and Pages checks if the connection permits;
   then verify the public `.tif` HTTP link, not merely the repository file.
