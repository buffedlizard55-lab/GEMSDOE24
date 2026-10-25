# ASPC findings, critical review and next session

> **Integration note, 2026-10-25:** this is the preserved ASPC session report, not
> a current winner recommendation. A concurrent MTR session subsequently restored
> the full 419 MB input (ignored by Git); the original statement below about it
> remaining unassembled describes the ASPC checkout at its run time. MTR1's
> broader registry included a local dense calibration lattice not in ASPC's
> pinned published-download registry. Their novelty claims have different scopes,
> and their fold/collar/bootstrap policies differ. Both promotion verdicts remain
> negative. See [MTR1 findings and integration review](11_MTR1_findings_2026-10-25.md).

## Executive decision

**Download: yes, as research. Submit: NO.** One unique prediction TIFF was generated from decoded cached LiDAR descriptors, not copied or re-ranked from a prior submission. Automated scientific gate status is negative for promotion. There is no discretionary human-inspection escape hatch and no competition upload.

- **HOLDOUT-DTI**: `segment-hide-recover-pooled-v1`, **60,988 scored withheld positives**, **0.085526**, 95% spatial cluster-bootstrap CI **[0.074400, 0.096483]**.
- **HOLDOUT-DTI control**: same evaluator/positives, **0.068359**, 95% CI **[0.056789, 0.080394]**.
- **HOLDOUT-DTI paired difference**: same evaluator/positives, **+0.017167**, 95% CI **[+0.008970, +0.024661]**. This is favorable screening evidence against the fixed scarp control, **not** proof of beating the current best.
- Exact experimental evidence: [`evidence/aspc_run_20261025.json`](../evidence/aspc_run_20261025.json). Compact JSON run card: [`evidence/aspc_run_card_20261025.json`](../evidence/aspc_run_card_20261025.json).

The CI is conditional on one fixed four-quadrant catalogue partition, with whole components hidden and a buffered training exclusion. Raster components are only a proxy for expert fault segments. No catalogue-based surface features or learned scaling are used. The classifier-learning buffers are enforced in the shared fold definition but have no fitted parameters to affect in this analytical method. Twenty-kilometre clusters may not remove all long-range dependence. No inference about private labels follows from this CI.

## Why the reported GEMSDOE32 artifact did well: evidence versus hypothesis

**COMPUTED-ARTIFACT-FORENSICS**, not score evidence:

1. The named H33-B2 file has **37,654** dots, no dots within **200 m** of the catalogue, and no on-catalogue positives.
2. Its emitted geometry is **exactly** the GEMSDOE25 D2.8 reference with all dots at catalogue distance <=200 m removed. That reference has **44,090** dots; **6,436** disappear and **zero** are added.
3. It is also **exactly** the GEMSDOE31 named reference with the next clearance step applied: **2,545** additional dots are removed.
4. GEMSDOE36's named file contains **every** H33-B2 dot plus **1,200** additional dots. Therefore its independent-sounding method name is not evidence of independent detection geometry.
5. All nine named files' hashes, catalogue clearances and Jaccard similarities are recomputable with `scripts/review_peer_forensics.py`, using [`evidence/peer_forensics_20261025.json`](../evidence/peer_forensics_20261025.json) and the pinned registry. The nine-repository registry has **98** downloadable references / **84** unique blobs; one **32×48** format-demo blob is explicitly excluded from competition-grid comparisons, leaving **83** prediction blobs. Mirrors/encodings are not separate geological discoveries.

**INFERENCE**, not verified hidden-label causality: dot thinning may lower repeated false-positive mass while retaining much of a 300 m triangular kernel's credit. Clearing catalogue flanks may further help if the removed dots have little hidden-fault credit. However catalogue pixels being excluded does **not** imply their neighbours are all false positives. New geometry of an existing fault may be adjacent. A claim of "no loss of true positives" cannot be verified here and is not adopted.

For DTI `s=T/(T+αF+β(N−T))`, a prune that loses weighted TP `L` and removes FP penalty `M` helps iff `α*T*M > L*(α*F+β*N)` (fixed truth count N). This is an algebraic condition, not a forecast. Geometry alone cannot identify L or M on the hidden set.

**UNVERIFIED-OWNER-REPORT**: the supplied `0.2778` is not ORGANIZER-CONFIRMED. GEMSDOE32's fetched README calls that file unscored at publication. Likewise the conflicting leaderboard figures in the brief have no fresh organizer snapshot. They are not promoted into a verified score ledger. The answer to "can we beat it?" is **possible but not established**; this lane does not justify a claim of a higher leaderboard result.

## Leakage and novelty gates

- **DIAGNOSTIC-AUC**: all eight raw input bands and six intermediate/combined factors were tested independently in all four folds (56 tests). Observed AUC range **0.451287–0.589727**; none exceeds the protocol threshold or its inverse. Passing a canary does not prove absence of every leakage mechanism.
- **COMPUTED-NOVELTY**: full common finite footprint, not a sample. Maximum surface Spearman **0.107690**. Maximum final-dot Spearman **0.023463**. Maximum candidate-to-one-reference coverage within inclusive 3 px **0.514952**, below the **0.70** stop threshold. All non-demo registry blobs were compared; reference-to-candidate coverage is also recorded.
- Scope is the nine repositories' pinned downloadable artifacts, **not** every unpublished registry raster in all parallel sessions. The missing assigned method paragraph remains an explicit blocker. ASPC is a provisional research lane, not a silently invented coordinated assignment.

## Automated format and promotion decisions

The exact allfinite TIFF is single-band float32, EPSG:32611, shape 3730×3292, affine `(100,0,243350,0,-100,4508550)`, zero NaN/Inf inside the footprint, and values 0 or 1 everywhere. The primary SHA-256 is `7f5706e03866d826e83ba5298a7f3fbbcfacc3b3e74b957d726269b54714e7bd`.

The existing writer/validator was reused. The misleading format-only `ok_to_upload` alias now fails closed; `format_acceptable` is the explicit format result and `submission_authorized` stays false. A zero-outside file differs from the pinned template's NaN convention, which the validator reports explicitly. Portal acceptance is **not verified**. The original range-error cause is unknown.

Promotion blockers: no assigned parallel lane; no matched current-best OOF reconstruction; no exact-file nuisance audit for this new candidate; no separate selector approval or verified current weekly cap. The candidate improves a fixed low-cost control, but that cannot substitute for the best-method comparison. No slot spent.

## Source audit

| Claim | Source / evidence actually inspected | Verification limit |
|---|---|---|
| Fault-detection target; Tversky training weights; CPU is supported | [Organizer-owned reference repo](https://github.com/drivendataorg/gems-prize-reference-solution), pinned tree and notebook hash in peer forensics | Reference training loss is not independent verification of the distance-weighted scoring implementation. |
| Survey provenance, independent blocks and magnetic/radiometric acquisition | Cached official USGS contractor report and metadata in `data/external/audit_sources/`; [ScienceBase](https://www.sciencebase.gov/catalog/item/657e1d85d34e23d3533209f7), [DOI](https://doi.org/10.5066/P93LGLVQ) | Parent source was cached, not re-fetched directly under current network restrictions. Acquisition-block raster is team-derived, not official coordinates. |
| LiDAR band meaning and quantization | Cached metadata plus raster band descriptions, SHA-256 verified against manifest; [team derivation workflow](https://github.com/buffedlizard55-lab/7GEMSDOE/actions/runs/36266555805), parent [USGS 3DEP](https://www.usgs.gov/3d-elevation-program) | Derived maxima are not official faults or a resolved 1 m trace. Incomplete tile coverage; no new official download asserted. |
| Competition metric/rules/leaderboard | [Problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/), [rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf), [leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) retained for manual review | Not fetched this session. Existing policy forbids automated DrivenData access; no receipt or current cap verification. |

No new external data is required for the four preregistered candidate ideas. Scientific literature and data not actually reachable or cached are not presented as newly read. The geological mechanisms are hypotheses; the experiment, not a citation, tests this particular operator.

## Reproducibility and limitations

```bash
.venv/bin/python scripts/review_peer_registry.py   # restore pinned GitHub blobs, hash-verify
.venv/bin/python scripts/run_aspc_lane.py         # one fixed run; refuses to overwrite a recorded experiment
.venv/bin/python scripts/review_peer_forensics.py # verify nine named artifacts' ancestry
.venv/bin/python scripts/build_site.py            # current lane supersedes historical recommendations
.venv/bin/python -m pytest -q
```

The recorded run completed in about 86 seconds after dependencies/data registry were ready. An initial preflight (before placement/scoring) found the explicitly named GEMSDOE36 format demo at the wrong grid size. That failed run is retained in `evidence/aspc_preflight_failure_20261025.json`; the exclusion and bootstrap tile aggregation correction occurred **before any holdout outcomes were observed**. No model retuning or second hypothesis was tried.

This checkout already has the descriptors needed for this analytical ranking. Full original competition features remain unassembled; no U-Net training or GPU work was necessary or claimed. Bulk mirrors remain ignored. GitHub access is sufficient for the chosen experiment; DrivenData credentials, hidden labels, an unrestricted network or new source downloads were not used.

## Next-session order

1. Read README and the latest owner requirements, then this result and the preregistration. Keep Maximize P(Win) / Own the Outcome grounded in negative evidence, not submission pressure.
2. Obtain a coordinated method-lane assignment and an authoritative shared registry snapshot. Do not drift into siblings' lanes.
3. Reconstruct the actual current-best detector OOF with catalogue features regenerated from visible faults and the same segment-pooled evaluator. An as-emitted scored TIFF is **not** this reconstruction.
4. Reconcile PR #7 without overwriting main's newer safety/site work. Its potential-field persistence result is already negative; do not repeat it as a new idea.
5. Only then preregister a new independently motivated test (e.g. stable-Th controlled radiometric contrast) and update the matched benchmark. Run the full nuisance audit only for a candidate still eligible for promotion.
6. A separate selector, not this lane, verifies the current portal cap and chooses whether any promoted candidate deserves a slot. Store an artifact-linked organizer receipt before labeling a score ORGANIZER-CONFIRMED.

Fault geometry is a proxy for one part of geothermal prospectivity, not proof of an accessible hot reservoir or a newly discovered vent.
