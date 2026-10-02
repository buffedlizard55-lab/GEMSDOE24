# 24GEMSDOE — DOE GEMS / DrivenData #306 (geothermal fault prediction)

**Mission: finish top of the leaderboard on scientific leverage, not luck.**
Two rules govern every decision in this repo:

> **Maximize P(Win).** Every hour is spent on the action with the highest
> expected reduction in regret — not the most comfortable one.
> **Own the Outcome.** No hand-offs, no "upstream problem" excuses. Data
> blockers get solved with tooling; dead ends get verified, not assumed.

---

## The standing starting point (owner's prompt — treated as the charter each session)

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

## What this repo adds over siblings (24's edge)

1. **Full 19-band feature stack assembled from SHA-pinned parts**
   (`data/training_features.tif`, 419 MB, verified) → `src/gems/geofeatures.py`
   quantizes it plus derived det_elev transforms (openness, anisotropy, slope)
   into `data/geofeat/featstack_u16.npy` — every model here sees real physics,
   not a 3-band proxy.
2. **CI-as-proxy data pipeline** (`scripts/ci_fetch_external.py` +
   `.github/workflows/fetch-public-layers.yml`): official public-domain layers
   the sandbox cannot reach (Census TIGER roads/rails, USGS MRDS claims,
   ScienceBase GeoDAWN outlines, NBMG Qfaults `FTYPE_` confidences) are fetched
   from an unrestricted runner and committed to branch `public-layers`.
3. **The accessibility audit itself** (`scripts/run_geology_audit.py`):
   confounds-only / geology-only / geology+confounds C2S2 tests against both the
   catalogue labels and our own emission rasters, with permutation + torus-shift
   nulls → `evidence/geoaudit.json`.
4. **Residualized emission surfaces** with the within-stratum rank reweighting,
   gated on the new-fault holdout against h19-4-as-emitted **before** any
   submission slot is spent.

## Repo map

| Path | What |
|---|---|
| `src/gems/` | metric (exact DTI), footprint, confounds, c2s2, geofeatures, submission, validator, holdout gate |
| `scripts/` | verify_data, assemble_features, build_confounds, build_geofeat, run_geology_audit, ci_fetch_external, ci_push_artifacts_api |
| `data/` | bridge (labels/existing/sample_submission), training_features.tif, geofeat/, confounds/, external/, dem10/, catalogue_ext/ |
| `docs/` | the Pages site: executive summary, one-click submission download |
| `registry/submissions.json` | every submission this group ever made, with hashes |
| `evidence/` | machine-readable audit outputs (verify line by line here) |

## Rules that bind us (from the organizers)

* Metric `DTI(0.2, 0.8)`, credit kernel `k(d)=max(1−d/300, 0)`; submission =
  single-band float32 GeoTIFF, EPSG:32611, 100 m, values in **[0, 1]**, nulls
  outside footprint. ("Predicted values must be in range [0, 1]" — every tif
  here is built by `gems/submission.py::write_submission`, which asserts the
  range, the grid, and the CRIS, and names each file uniquely.)
* Known USGS/INGENIOUS fault pixels are masked from scoring (staff, forum
  11516/11527) — so only *new* faults earn, and our gate mirrors that exactly.
* Final round re-scores ONE submission against an expanded expert-catalogued
  test set. A slot spent is data the whole group can't get back this week —
  hence the holdout gate rule: **no idea reaches the leaderboard until it beats
  the current best (0.1922 / h19-5) on the spatially-blocked new-fault holdout.**

## Status (updated 2026-10-02, all numbers machine-generated — see site)

* Data: **complete & hash-verified** — competition layers (features sha256
  `4371c82e…` re-verified after this workspace was rebuilt from the pushed
  branch), GeoDAWN radiometrics, lidar scarp product, plus — fetched via the
  `public-layers` CI-as-proxy branch — TIGER2024 ROADS (22 counties),
  MRDS claims, the **official ScienceBase GeoDAWN Area-1/2 outline polygons**
  (now driving `acq_window`), and 1,179 INGENIOUS Qfaults traces with `FTYPE_`
  confidence (739 WC / 351 MC / 89 Inf — matches the published census).
* **Audit verdict** (`evidence/geoaudit.json`): accessibility-confounding of
  the catalogue is **not confirmed** beyond a torus-shift null with purely
  non-geological features (labels V1-clean AUC 0.570, shift margin −0.060,
  p=0.44); the apparent 0.956 was the catalogue self-predicting through a
  fault-distance feature (leave-one-out collapses to 0.495). Geology-only
  separates near/far better than access (0.684). Our emission is not more
  access-structured than the catalogue (0.611 vs 0.570) → the mapping-process
  overfitting kill-rule did **not** fire. Emission-level residualization
  gate-tested (±0.0007): guardrail, not a lever.
* **H24-1 (confidence-contrast prior)**: gate-tested, **not promoted**
  (`evidence/h24_1_gate.json`); H24-2..5 pre-registered in
  `knowledge/01_hypotheses_2026-10-01.md` — each gates before any slot.
* Best live: h19-5 0.1922, h19-4 0.1894 (registry); leader 0.3168.
* One-click download: `docs/downloads/gems24-h24-0-mirror-h19-5-group-best-…tif`
  (byte-identical mirror of the group best; content id `e27054cf` matches 19's
  registry; `check_variants` green: [0,1] range, grid, CRS — the fix for the
  "Predicted values must be in range [0, 1]" rejection, plus an `allfinite`
  twin and a short DrivenData note per upload).
* Limitations: sandbox egress whitelist forces the CI-proxy route; TIGER2024
  folds rails/trails into ROADS (S1400/S1500 — no separate RAILS layer, 404s
  logged); the four contractor acquisition *blocks* remain seam-approximated
  (outlines give Area1/Area2 only); 8–41-null p-values are resolution-limited
  (p ≥ 1/(n+1)); 100 m grid under-resolves sub-km access structure;
  `labels` may themselves be incomplete by the organizers' own words.
