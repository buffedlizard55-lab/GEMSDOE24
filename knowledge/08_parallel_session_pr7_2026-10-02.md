# Parallel-session PR #7 — observed state, cross-checks and reconciliation (2026-10-02)

Status: **open, unmerged, conflicting.** Written after this session's PRs #5 and #6 had merged
(`main` = `7407039`). Everything below was read from GitHub and from the other branch; nothing from
that branch was executed, copied into this branch or modified. This session did not push to it.

## 1. What was observed (17:40 UTC)

| Item | Value |
|---|---|
| PR | [#7](https://github.com/buffedlizard55-lab/GEMSDOE24/pull/7) "Verify buffered road sources and test H24-3A" |
| Author / branch | same GitHub account; branch `arena/01a0fd2e-gemsdoe24` (this session is `arena/01a0fc3e-gemsdoe24`) |
| Opened | 2026-10-02 17:37:10 UTC — 3.5 minutes after PR #6 merged (17:33:34) |
| Base | `a2b4444` (the same base this session started from); it has not seen PRs #5/#6 |
| Head | `aaaba1f8`, 9 commits dated 15:31–17:35 UTC; 40 files, +15,707 / −3,492 |
| Relative to `main` | 9 commits ahead, 21 behind; `mergeable = CONFLICTING`, state `DIRTY` |
| Its own check | "Reliability" workflow on its head passed (as reported in its PR body) |

Read-only dry run (`git merge-tree --write-tree --name-only origin/main <head>`) conflicts in
**20 paths**: `.github/workflows/bridge-audit-inputs.yml` (deleted on main, modified there),
`.github/workflows/buffered-roads.yml`, `.github/workflows/tests.yml`, `README.md`,
`data/external/audit_sources/tiger_road_distance_m.tif`, `…/tiger_road_receipt.json`,
`docs/data/access_inputs.json`, `docs/data/audit.json`, `docs/data/review_passes.json`,
`docs/data/source_health.json`, `docs/executive-summary.html`, `docs/index.html`, `docs/research.html`,
`docs/sources.html`, `evidence/access_inputs.json`, `evidence/h24_2_experiment.json`,
`evidence/review_passes.json`, `evidence/site_build.json`, `index.html`, `scripts/build_site.py`,
`scripts/fetch_official_roads.py`, `scripts/run_geology_audit.py`.

Its `docs/index.html` first-screen download is the **reference H19-5** (`gems24-reference-h19-5-…`);
`main`'s first screen is the **dotted primary** (`gems24-h25-1-dotted-h19-5-d1-5-…`).

## 2. What it contains that `main` lacks (read, not re-run)

1. An official Census TIGER 2024 road raster with an explicit MTFCC policy that **excludes S1750**
   (183 features): raster sha256 `459af5cf2247d07580af42f737533863749166cd42027a0d340745ceb3ed21b8`,
   1,141,492 seed pixels, source CRS EPSG:4269 recorded, per-county hashes.
2. A "v3" labels-first audit on road + closed-claim distance only. It treats the four acquisition
   blocks as unavailable, so it calls itself incomplete.
3. **H24-3A** (multi-scale potential-field contact persistence): preregistered, run, **not promoted**.
   New code `src/gems/scale_space.py`, `scripts/run_h24_3a_experiment.py` and tests.

## 3. Cross-checks between the two sessions (independent, same code lineage)

| Quantity | This session (`main`) | PR #7 | Agreement |
|---|---|---|---|
| H19-4 / H19-5 audit input files | sha256 `89109a3b…` / `ec1f9b56…` | `89109a3b…` / `ec1f9b56…` | byte-identical |
| H19-4 as emitted, 4-quadrant DTI (dense / sparse) | 0.1704 / 0.0685 | 0.1704 / 0.0685 | identical |
| H19-5 as emitted | 0.1694 / 0.0681 | 0.1694 / 0.0681 | identical |
| Single-feature AUC, claim distance: labels / H19-4 / H19-5 | 0.4942358 / 0.5796882 / 0.5849734 | 0.4942358 / 0.5796882 / 0.5849734 | bit-identical |
| Single-feature AUC, road distance: labels / H19-4 / H19-5 | 0.5222024 / 0.5225838 / 0.5048221 | 0.5220348 / 0.5225838 / 0.5048252 | within 1.7e-4 (H19-4 bit-identical); the two road rasters differ (§5) |
| Primary classifier AUC: labels / H19-4 / H19-5 | 0.4958 / 0.5558 / 0.5630 | 0.5302 / 0.5626 / 0.5670 | not identical (different features and folds, §4) |

## 4. Where the two audits differ, and why the flags differ

| | This session (`evidence/accessibility_audit_v2.json`) | PR #7 (`evidence/accessibility_audit_v3.json`) |
|---|---|---|
| Features | road, claims **and the derived four-block raster** | road and claims only |
| Null / rule | grouped refitted nulls; Holm over 6 rasters; flag = Holm p ≤ .05, AUC ≥ .55, margin ≥ .02 | 199 shift nulls; Holm over its 4 rasters; flag needs shift-tail Holm p ≤ .05, AUC ≥ .55 **and** margin over shift-null p95 ≥ .02 |
| Labels | 0.4958, Holm 0.625 | 0.5302, shift p 0.175, Holm 0.28 |
| H19-4 / H19-5 | 0.5558 / 0.5630, Holm 0.030 each → **flagged** | 0.5626 / 0.5670, shift p 0.08 / 0.07, Holm 0.28 → **not flagged** (margin −0.0071 / −0.0057) |

The measured associations agree (claim proximity ≈ 0.58 for both H19 files); the two **decision rules**
differ. Neither is the organizers' audit. The disagreement is not evidence that either session is wrong;
it is a reason not to quote one flag without its rule. On PR #7's own numbers the H19 files sit above
AUC .55 but inside the shift-null p95 (0.570–0.573).

Block stance also differs: this session derived the four blocks from the official GeoDAWN Figure 1
and audited them against published line-km (status `derived_audited_not_official_coordinates`);
PR #7 declares block membership unavailable. Official coordinates are in fact unpublished (S3 profile
archives return 403), so both statements are true at their own level of strictness.

## 5. The S1750 difference between the two road rasters (measured)

* Official definition: **S1750 = "Internal U.S. Census Bureau use"** (Census 2023 TIGER/Line Technical
  Documentation, Appendix E, row S1750 — read in full:
  <https://www2.census.gov/geo/pdfs/maps-data/data/tiger/tgrshp2023/TGRSHP2023_TechDoc_E.pdf>; the
  2019 and 2020 editions show the same wording in search excerpts only; the 2024 edition was not read).
  The same appendix lists walkway S1710, stairway S1720, alley S1730, parking-lot road S1780,
  bike path S1820 and bridle path S1830 as "Road/Path Features", so "road/vehicular-trail" was too narrow
  a description for both rasters.
* `main`'s raster (`data/external/audit_sources/tiger_road_distance_m.tif`, sha256 `e5350423…`,
  1,141,630 seed px) includes the 183 S1750 features. PR #7's excludes them (1,141,492 seed px).
* Measured on the shared grid (3730 × 3292, same transform and CRS): **56 of 5,167,373 finite pixels
  differ (0.0011 %)**; 11 by more than 100 m; maximum change 300 m; none above 500 m; no NaN mismatch.
  Direct effect on the audit's descriptive road-distance AUCs (§3): at most 1.7e-4 (labels), 3e-6 (H19-5),
  0 (H19-4). That is about 30x smaller than the closest flag margin (flagged classifier AUC 0.5553 vs. the
  .55 rule = 0.0053), which makes a flipped flag very unlikely - an expectation, not a measurement: the
  full classifier audit was **not** re-run with the S1750-free raster.
* Fix (deferred to reconciliation): an explicit MTFCC allowlist in `scripts/fetch_official_roads.py`, then
  a regenerated raster and receipt from the official CI run. Changing the script without regenerating
  would leave the committed receipt inconsistent, so it was not done here.

## 6. H24-3A as reported by PR #7 (quoted from `evidence/h24_3a_experiment.json` on its head; not reproduced)

Design (its words): same four contiguous quadrants, 20 km training exclusion collar, nuisance fitted on
training data only, 27 baseline geology features + 3 persistence features, road and claim distance as the only
nuisance families (no block raster), 4 arms. Mean 4-quadrant DTI:

| Arm | Dense | Sparse |
|---|---|---|
| physics_raw | 0.1311 | 0.0456 |
| physics + persistence, raw | 0.1382 | 0.0521 |
| physics, residualized | 0.1431 | 0.0531 |
| physics + persistence, residualized | 0.1498 | 0.0552 |
| H19-4 as emitted (reference diagnostic) | 0.1704 | 0.0685 |
| H19-5 as emitted (reference diagnostic) | 0.1694 | 0.0681 |

Its decision fields: `candidate_beats_paired_baselines: false`, `candidate_beats_historical_diagnostics: false`,
`promoted: false`, `submission_slot_spent: false`. Paired gate: the raw arm passes; the residualized arm
fails (sparse-fold wins 2 of 4). Against H19-4 the candidate is lower by 0.0206 dense / 0.0133 sparse.

Reading (mine, labelled as such): on its own harness the persistence features add +0.0071 dense /
+0.0065 sparse (raw) and +0.0067 / +0.0021 (residualized), yet every arm stays below the as-emitted H19
diagnostics. Its absolute levels are **not comparable** with this session's `h24_2_experiment.json`
(physics_raw 0.1517 / 0.0584) because the harness differs (20 km collar vs. this session's design); only the
shared as-emitted rows agree exactly. Treat H24-3A as a recorded negative result pending a rerun; H24-4A
(directional residual variogram) remains untested.

## 7. Reconciliation plan (recommendation; the owner decides)

1. **Do not merge PR #7 as it stands and do not resolve its conflicts in favour of its side.** Doing so
   would replace `main`'s dotted first-screen download, the six-reference audit, the evidence-driven site
   generator, the README charter and the removal of `bridge-audit-inputs.yml`.
2. Rebase that branch onto current `main`; for the 20 conflicted paths keep `main`'s version, except
   re-run `scripts/build_site.py` afterwards instead of hand-merging generated pages.
3. Port only its genuinely new work: `src/gems/scale_space.py`, `scripts/run_h24_3a_experiment.py`, their
   tests, `evidence/h24_3a_experiment.json`, its H24-3A preregistration text, the S1750-excluding road policy
   with a regenerated raster/receipt, and the v3 audit **as an additional record beside v2**, with each flag
   shown together with its rule (§4).
4. After the port: run the full test suite, re-run the audit with the regenerated road raster, rebuild the
   site, and merge with a fresh PR.
5. Prevention: `AGENTS.md` now requires listing open PRs and `arena/*` branches at session start.
