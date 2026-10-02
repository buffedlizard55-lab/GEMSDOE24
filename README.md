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
[Remaining untested hypotheses](knowledge/04_remaining_hypotheses_2026-10-02.md) ·
[Source review](knowledge/03_verified_sources_2026-10-02.md)

## Current decision

<!-- STATUS:START -->
**No new slot-eligible candidate; no slot consumed.** H19-5 remains a format-validated reference with owner-reported original public DTI **0.1922**. The official leaderboard snapshot on 2026-10-02 showed DARD at **0.3195** (#1); rows at **0.1922** and **0.1894** were present but are not linked to these raster hashes.

H24-3A paired residualized holdout: **0.14980 / 0.05523** vs residualized physics **0.14305 / 0.05306**. It fails the preregistered sparse-fold gate and trails H19-4/5 as-emitted local diagnostics. These local DTI values do not forecast a public score.

The official 2024 Census road/path bridge now passes complete county/window checks: 32 counties, 20 km buffer, explicit Road/Path MTFCC allowlist, S1750 excluded. The full three-family C2ST is still **BLOCKED** because verified four-block pixel membership is missing. Labels first, then H19-4, H19-5 and exact H24-3A were tested using the two available families only; no available-family association met the declared effect rule. No causality or absence of bias is inferred.

Reference: [`gems24-reference-h19-5-20261002-80d47e1ab2ee-nan.tif`](docs/downloads/gems24-reference-h19-5-20261002-80d47e1ab2ee-nan.tif). New experimental exact raster is format valid but **not recommended to upload**. PR/merge/public deployment are recorded separately; this local build is not publication proof.
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
   AUC with refitted spatial randomizations. The primary non-wrapping translation
   null is a stationarity-based sensitivity diagnostic, not an exact spatial
   randomization p-value; Area1/Area2 never substitute for the four blocks.
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
.venv/bin/python scripts/restore_data.py
.venv/bin/python scripts/prepare_data.py
.venv/bin/python scripts/build_confounds.py --force
.venv/bin/python scripts/run_geology_audit.py
```

The official road source bridge is already restored on this branch. If and
only if four-block membership remains unavailable, run the current H24-3A
experiment with the explicit partial-input flag; it records the missing family
and cannot promote a candidate or spend a slot:

```bash
.venv/bin/python scripts/run_h24_3a_experiment.py --allow-partial-audit-inputs
.venv/bin/python scripts/run_geology_audit.py \
  --candidate out/h24-3a-contact-persistence-20261002-experimental.tif
.venv/bin/python scripts/build_site.py
```

The current exact experimental raster is retained under ignored `out/` for
review only. It passes the format checker but fails the paired sparse-fold and
H19 diagnostic gates; do **not** package or upload it. The promotion tool stays
fail-closed for a future candidate unless the comparable current-best holdout,
training-only intervention, complete three-family audit and exact file identity
all pass. Packaging is not an upload command.

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
- **Preparation:** 5,167,373 footprint rows × 30 float32 owner-bridge descriptors;
  27 base physical/LiDAR columns and three fixed annular descriptors. H24-3A adds
  three upward-continuation persistence descriptors in a separate ignored cache.
  Full-scene transforms use unlabeled physical context; nuisance regression,
  standardization and imputation are fitted on training-region pixels only.
- **Access data:** official TIGER 2024 Road/Path geometries and BLM **closed
  mining claims**, not MRDS. The road bridge checks 32 complete CA/NV counties,
  covers a 20 km buffer around the output window and excludes 183 S1750
  internal-use features under the official MTFCC documentation. Its raster SHA-256
  is `459af5cf…`; the receipt records county EPSG:4269, URLs, sizes and hashes.
  TIGER still is not a complete hiking-network or travel-time model. BLM claim
  polygons are PLSS legal-land approximations, not exact stakes/workings; the
  documented quality policy rejects unknown/degraded records and broad polygons.
- **Acquisition:** Area 1 has priority in the Area 1/2 overlap. Those are **not
  the four operational blocks**. The official report identifies Winnemucca,
  Fallon, Hawthorne and Tonopah, but the fetched geographic extent/flight-path
  inventories do not provide independently verified four-block polygons.
- **Audit:** v3 tested labels first, then H19-4, H19-5 and the exact H24-3A
  raster, using 12,000 samples/class and 199 valid non-wrapping mask translations
  with classifier refits. Only road/claim distances were available; Holm-adjusted
  shift diagnostics were 0.28 and no raster met the available-family effect rule.
  This is provisional, not proof of no bias: true four-block membership is still
  missing. The superseded v2 Area1/toroidal results must not be used.
- **Experiment:** physics / physics+potential-field persistence × raw /
  training-only residualized; same four quadrant folds and HGB settings. H24-3A
  uses upward-continuation scales 100/200/400 m and a preregistered 20 km training
  collar for its nonlocal transform. Whole components touching held-out regions
  are excluded; maximum ridge budget is 2.45%, no zero padding, complete NMS halos
  are used, and catalogue masking occurs **after** NMS. Dense and 20%-component
  sparse truth remain simulations on the incomplete catalogue, not hidden
  new-fault ground truth. The candidate fails the residualized sparse-fold gate
  and loses to H19-4/5 as-emitted diagnostics.
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
| `scripts/run_h24_3a_experiment.py`, `src/gems/scale_space.py` | preregistered multi-height potential-field contact persistence and paired holdout |
| `scripts/run_geology_audit.py` | labels first, then H19-4/H19-5 and exact candidate; v3 spatial-shift audit |
| `evidence/data_restore.json`, `data_preparation.json` | full input and matrix hashes; provenance caveats |
| `evidence/group_review.json` | all 21 supplied project source pages, pinned commits and consulted files |
| `evidence/access_inputs.json`, `accessibility_audit_v3.json` | official road/claim families, missing true block membership, shift-null diagnostics |
| `evidence/h24_3a_experiment.json` | preregistered four-arm/fold results, historical comparisons and exact raster receipt |
| `evidence/official_roads_initial_crs_failure.json` | superseded CRS-check failure; resolution history; not current source status |
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

1. Obtain machine-readable true membership for Winnemucca, Fallon, Hawthorne and
   Tonopah from an official GIS boundary or defensible, independently verified
   line-to-block mapping. Do not infer it from labels, Area1/Area2, a constant
   raster, latitude seams or nearest base towns. This is the remaining blocker
   for the requested full nuisance audit.
2. Once verified blocks exist, rebuild the strict three-family C2ST with the
   same labels-first order, spatial refits, non-wrapping shift diagnostic, Holm
   control and effect-size threshold. Clearly label the shift tail as an
   approximate stationarity sensitivity analysis. Re-audit the exact final file.
3. Reconstruct the current-best H19 spatial OOF under the same masked metric and
   split protocol, with hashes and transductive steps disclosed. H24-3A was
   tested and did not pass promotion; do not rerun it to tune against the folds.
   H24-4A directional residual variograms are the next untested registered
   hypothesis; H24-6 remains deferred until full official 3DEP tile bytes and
   study-wide coverage are verified.
4. Obtain independent fault/expert validation before claiming discovery. A
   contact, scarp, intrusion rim, road cut and mapped fault can be equifinal in
   these fields. The private leaderboard and Phase 2 expert assessment are not
   available local truth.
5. Open a PR from this fixed session branch, verify required checks, and merge
   only if authorized and all checks pass. Then verify any public deployment;
   neither a repository file nor a local site build proves a deployed URL.
