# 04 · Preregistration — H25-1 "Dotted H19" (frozen before any new holdout contact)

Date: 2026-10-02 · Session branch `arena/01a0fc3e-gemsdoe24` · Status: **FROZEN**.
Everything below was written before `scripts/run_dotting_validation.py` was run on the
H19/H16 rasters. Results are recorded separately in `evidence/dotting_validation.json`.

## 1. Question

Does keeping a deterministic geodesic Poisson-disk **subset** of the already-emitted H19-5 mask
(`src/gems/thinning.py::dot_thin`, no pixel added, no label or score read) raise the exact DTI on a
spatially blocked holdout, especially when truth is sparse?

## 2. Why this is a hypothesis worth a gate (and what it is not)

* **Mechanism (exact, from the organizer's metric).** A truth pixel at distance `d` from the nearest
  emitted pixel earns `1 − d/3`; every emitted pixel costs false-positive mass. A solid 1-px line
  spends ≈3× the false-positive mass of a ~3-px dotted line for ≈1.3× the on-line credit.
* **Evidence already in the group's record** (all team-authored, not organizer receipts):
  GEMSDOE10 `HYPOTHESES.md`/`reports/h28_blocked.json` (density-matched blocked holdout, three fields:
  dotting +23–28 %, "dominant effect", 24/24 simulated-truth wins, margin grows as truth gets
  sparser; budget reduction alone ≤ +0.006). H25 (solid, 161,366 non-catalogue px) and H28 (dotted,
  65,236 px) share the identical probability field `6452ae1d00…`; owner-reported public scores:
  H25 **0.1280**, H28 **0.1839** (the H28 value appears only in this session's task statement; an
  earlier verbatim snapshot in GEMSDOE21's README shows it blank — treat as unconfirmed).
* **Gap.** The best live files (H19-4/H19-5/H16-1) are *blobby segments*: 39–41 % of their pixels have
  ≥3 emitted 8-neighbours, mean component ≈4.3–4.5 px. Dotting was never applied to that field.
* **Not geology.** It adds no fault evidence. It re-spends false-positive mass. It cannot find a fault
  H19 missed; it can only make H19's hits cheaper. Geological hypotheses are ranked separately in
  `05_*`.

## 3. Frozen design

* **Emissions.** Primary: H19-5 as emitted (`inputs/*h19-5*-nan.tif`, sha256 `ec1f9b56b83c…`).
  Replicates: H19-4, H16-1. Retrodiction pair (no thinning): `g10_h25ctx` vs `g10_h28dot`.
  Catalogue pixels are removed from the emission first (the scorer masks them), then thinned.
* **Operator.** `dot_thin(E, d)`, `d ∈ {1 (solid), 1.5, 2.0, 2.4, 2.8, 3.2, 3.6, 4.2, 5.0}`.
* **Folds.** `holdout.make_quadrant_folds` (NW, NE, SW, SE). Dev = NW, NE, SW. Confirmation = SE.
  Emission outside the evaluated quadrant is ignored (mirrors a public-subset score).
* **Truth families** (known catalogue masked everywhere; exact `metric` formulas):
  * sparse: catalogue components kept at fraction ½ and ¼ (3 draws each); SGMC-minus-catalogue faults
    ≥10 px from the catalogue (independent geologist-mapped traces) kept at ½ and ¼ (3 draws each);
  * full density (non-inferiority only): `catdense` (repo dense protocol) and `sgmc_far10_full`.
* **Selection of d\*.** Maximise the mean *relative* DTI gain over solid across **dev folds × the 4
  sparse families × draws**. Ties → larger d. Confirmation fold and full-density families are not
  used for the choice.
* **Eligibility gates on d\* (all required):**
  * G1 confirmation fold: mean over sparse families ΔDTI > 0 and ≥ +5 % relative;
  * G2 win-rate ≥ 75 % over all sparse cells (4 folds × 4 families × 3 draws = 48);
  * G3 cell-block bootstrap (resample fold×family blocks, 2,000 draws) lower 5 % bound of the mean
    relative gain > 0;
  * G4 full-density non-inferiority on dev folds: mean ΔDTI ≥ −0.010;
  * G5 replicates (H19-4, H16-1) show the same sign of mean sparse gain at d\*.
* **Retrodiction check (not a gate).** Does the same harness predict the *sign and rough size* of the
  owner-reported H25 → H28 live change? Reported either way.

## 4. Interpretation limits (frozen)

* Eligibility is **necessary, not sufficient**. Measured this session: proxy-vs-live rank correlations
  are weak (SGMC-far10 ρ = +0.33, n = 24; the group's own dense proxy ρ = +0.17, n = 15).
* A pass authorises *considering* a slot; it does not predict a live score. Unknown scores stay unknown.
* The exact candidate file must still pass the format validator, the exact-file accessibility audit and
  the promotion rule before any packaging as a downloadable submission.
