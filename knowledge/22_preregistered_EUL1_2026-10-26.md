# Preregistration: `H24-EUL1` — Euler-Deconvolution Basement-Contact Channels in Dual-Partition Stitched-OOF (2026-10-26)

**Status:** Locked prior to implementation of `src/gems/euler.py`, prior to any holdout fit,
and prior to exporting any raster in this session. Branch `arena/2ef68f55-gemsdoe24`,
base commit `17496743a9695974370512db64d8140ea1ccfd2f` (merge of PR #33).
**Session budget (PARALLEL-RUN PROTOCOL Rule 6):** at most 3 experimental arms, at most 2 hours
of experiment wall-clock, **zero** DrivenData slots. Promotion to a real slot is a separate
selector step; this session cannot issue `SUBMIT: YES` by construction (see §5).

---

## 1. Why `GEMSDOE32 h33-h33-2-b2` owner-reported 0.2778 — what is actually proven here

Every leaderboard number in the owner brief (including `0.2778`, `0.3195`, `0.4413`) is
**UNVERIFIED-OWNER-REPORT**: no artifact-linked DrivenData submission-page receipt is archived
in git, so nothing is labelled `ORGANIZER-CONFIRMED` (Rule 3). The two leader claims conflict
(`0.3195` vs `0.4413`); both are treated as unverified snapshots, not facts.

What *is* verified locally (re-checked this session: `scripts/run_dprf1_lane.py --verify-recorded`
passes; `knowledge/14_h33_analysis_2026-10-25.md`; `evidence/peer_forensics_20261025.json`):

1. **Ancestry is geometry, not geology.** B2's 37,654 positive pixels are exactly the
   44,090-dot `D2.8` Poisson-thinned `H19-5` set with 6,436 dots at catalogue distance
   `≤ 2 px` (200 m) deleted, and no added coordinates. Its advantage over `D2.8` (0.2600)
   and `D1.5` (0.2477) in the owner-reported ordering cannot be attributed to hidden-set
   TP/FP from here: with `DTI = T / (T + 0.2F + 0.8N)` (equivalent form of the
   distance-weighted Tversky, α=0.2, β=0.8, 300 m triangular kernel), deleting
   contributions `(t, f)` helps iff `t·(0.2F + 0.8N) < 0.2·T·f`; `t, f` on hidden truth are
   unknowable locally. The *testable* version of the lesson is: sparse (~2.8 px spacing),
   catalogue-cleared (`> 2 px`), far-field-weighted emission generalises; dense or
   near-catalogue emission does not.
2. **The 2026-10-25 live collapses were an emission bug, and it is now structurally fixed.**
   `GVC1` (owner-reported 0.0859) and siblings refit in-sample on the full catalogue with a
   `≥ 9 px` negative dead-zone, dumping 70.4% of dots into the unpenalised 200–900 m apron.
   `H24-DPRF1` (stitched-OOF, stratified `d_vis ≥ 3 px` negatives, apron quantile debiasing)
   cut that apron to 22.3% and restored 52.3% `> 2 km` far-field dots, reaching the repository
   point-best **HOLDOUT-DTI 0.16379** (95% CI [0.15045, 0.17739], `gems-segment-pooled-v1`,
   60,988 withheld positives, 4/4 folds). It is still `DOWNLOAD: YES · SUBMIT: NO` under
   `gems-selector-v2-literal-quota-fail-closed` (retained `registry-039` spacing-5 lattice,
   unknown live quota, no independent replay certificate).
3. **Therefore beating 0.2778 live requires a better *detector surface*, not more thinning.**
   B2 already saturates the copyable emission geometry; any unique raster must find
   fault pixels B2's `H19-5` parent missed, at the same sparse/cleared emission discipline,
   and must prove it on the spatially blocked holdout against the *current* point-best
   (`DPRF1` 0.16379) before any selector step. A HOLDOUT-DTI is not a leaderboard forecast:
   holdout truth is the (dense) mapped catalogue hidden in blocks; live truth is sparser
   unmapped faults. Only the paired, same-evaluator comparison is decision-grade.

---

## 2. Five ranked candidate hypotheses not yet tried in this repo

"Not tried" was checked against every lane module in `src/gems/` and every preregistration in
`knowledge/` (ASPC, MTR1, SAHG1, CON/CGB3, OJ1, GVC1, RSHG1, FUSE/HCW, CRP1, CUP1, TNR1,
TRSG1, DPRF1) plus sibling artifact names in `registry/owner_reported_scores_2026-10-26.json`.

| Rank | ID | Layers (all already local & SHA-pinned unless stated) | Physical signature / transform | Why it catches catalogue-*missing* faults | Named non-fault mimic | Difference from everything in this repo | Expected gain / cost / external-data verdict |
|---:|---|---|---|---|---|---|---|
| **1 (selected)** | **H24-EUL1** Euler-deconvolution basement contacts | `rtp`, `tmi_vg`, `iso_grav_anom`, `iso_grav_anom_vg` (prepared 30-ch stack from `training_features.tif`, USGS GeoDAWN DOI 10.5066/P93LGLVQ) + full DPRF1 52-ch stack | Moving-window (7×7 px) least-squares Euler homogeneity solutions at structural index **N=0** (vertical contact/step): `x0·Fx + y0·Fy + z0·Fz = u·Fx + v·Fy` per window (Thompson 1982; Reid et al. 1990); accept solutions with depth 50–1500 m, plan offset inside window, relative residual < 0.15; emit solution-*density*, median-depth, quality, gravity twins, 300 m gravity×magnetic cross-gradient co-alignment, and 8-azimuth lineament response of the density field (7 new channels) | Basin-and-Range normal faults offset magnetic/gravity basement hundreds of metres below alluvium; the *step* persists in potential fields where no scarp, LiDAR break or spring exists for Qfaults/INGENIOUS mappers to see. Solution clusters line up along the buried contact even when scalar tilt/gradient fields are diffuse | Unfaulted Mesozoic pluton–hornfels intrusive contacts and detrital-magnetite paleochannels also solve Euler N≈0; mitigation: solutions are only *channels* inside a supervised multi-physics model gated by hydrothermal/tilt/LiDAR evidence, never standalone dots | No lane in this repo solves Euler homogeneity. `MTR1` = 1-D RTP troughs; `CRP1/CUP1` = tilt/upward-continuation *persistence ratios*; `GVC1` has a 2 km grav–mag co-alignment scalar, not windowed depth solutions. Sibling repos used "euler" for catalogue-tip geometry (GEMSDOE28) or standalone depth-cluster dot threading (GEMSDOE40, owner-reported 0.036–0.098) — EUL1 is neither: fold-safe supervised channels + Euler-gated concealed-regime allocation, with a no-Euler paired ablation | Modest (+0.002…+0.010 HOLDOUT-DTI hoped, concentrated in `SW`/basin folds; no score forecast). Cost medium (one feature build ~minutes; reuse DPRF1 machinery). **No external data needed** — fully viable in-sandbox |
| 2 | **H24-DRAIN5** drainage knickpoints | `det_elev` (100 m, local); finer DEM = USGS 3DEP 1/3 arc-sec | D∞ flow accumulation `A(x)`, normalised channel steepness jump `Δ(A^0.45·|∇z|)`, co-linear knickpoints across ≥3 adjacent washes | Strike-slip/oblique faults lose scarps to sheetwash in 10³–10⁴ yr but keep aligned gully deflections/knickpoints | Lithologic hogbacks, fan-lobe avulsions, road ditches | No flow-routing anywhere in repo (all geomorphology is local 9×9 filters) | Uncertain at 100 m; high implementation cost (5.17M-cell routing without numba). 3DEP host `apps.nationalmap.gov` **unreachable from sandbox** (checked 2026-10-26T06:44Z: only `github.com` responds) → only the coarse 100 m variant is viable here; deferred |
| 3 | **H24-KERN6** DTI-kernel soft-label regression | DPRF1 52-ch stack; target from `fold.visible` only | Train `HistGradientBoostingRegressor` on kernel-credit target `y(x)=max_g (1−d(x,g)/3px)` instead of binary labels | Directly matches the 300 m credit geometry; may centre dots on fault cores rather than aprons | Smears probability onto parallel non-fault lineaments 100–300 m away | Every supervised lane here is binary classification; none regresses the metric kernel | Cheap, but it is an objective change, not new geological evidence; the submodular allocator already optimises kernel cover. Deferred behind Rank 1 |
| 4 | **H24-SLAB2** Walker Lane Riedel shear partitioning | `geod_shearrate`, `geod_dilaterate`, `geod_2ndinv`, `ieq_n100a15`, `deq_n100a15` | Shear/dilatation ratio × seismic density × oblique lineament anisotropy | Low-throw dextral shears lack scarps but carry microseismic strain | Mining-blast clusters; GPS interpolation seams | **Largely absorbed by TRSG1** (seismic structure-tensor fabric + moment excess already run, HOLDOUT-DTI 0.14644) — residual novelty too low to justify a fresh lane; listed for completeness, not selected | Low incremental value post-TRSG1; cheap; local data. Not viable as a *unique* lane |
| 5 | **H24-INSAR4** Sentinel-1 LOS velocity steps | NASA ASF DAAC `OPERA_L3_DISP-S1_V1` (free, official: https://asf.alaska.edu/datasets/daac/opera/) | Cross-strike `|∇⊥ v_LOS|` (mm/yr) at phreatic fault barriers in flat playas | Fault-gouge aquitards step poroelastic subsidence where DEM/LiDAR show nothing | Aquifer pinch-outs, evaporite heave | No radar data anywhere in the portfolio | Potentially high in playas but **not viable this session**: `asf.alaska.edu` unreachable from sandbox (checked 2026-10-26T06:44Z). Named source is free/official for an unrestricted machine; do not propose as runnable here |

---

## 3. Locked EUL1 protocol (reuse, don't rebuild — Rule 2)

Shared machinery, unchanged semantics: `gems.holdout.SegmentHoldout` (`gems-segment-pooled-v1`,
buffer 15 px, whole components hidden, visible masked pixel-exactly, pooled α=0.2/β=0.8/300 m),
`gems.dprf1` fold fitter (stratified `d_vis ≥ 3 px` negatives, selective residualization,
relief-conditioned calibration, ridge sharpening, stitched-OOF, apron debiasing,
two-regime submodular allocation), `gems.submission` writer, `gems.novelty`,
`gems.c2s2`, `gems.selector` v2. The only shared-code change permitted is a
backwards-compatible optional `extra_mm` extension of the DPRF1 fitter (default = exact DPRF1
behaviour; DPRF1 `--verify-recorded` must still pass). No private forks; no prior submission
pixels read by the detector (registry rasters are read *only* by the novelty audit).

**New channels (label-free, computed once from physical grids; exact formulas in `src/gems/euler.py`):**
`eul_rtp_density`, `eul_rtp_depth`, `eul_rtp_quality`, `eul_grav_density`, `eul_grav_depth`,
`eul_xgrad_coalign`, `eul_rtp_density_lineament`. Window 7×7 px; N=0; derivatives: horizontal
from central differences of the field (pixel units), vertical from the survey `*_vg` bands.
Acceptance (label-free, fixed now): `0.5 ≤ z0 ≤ 15 px`, `|x0|,|y0| ≤ 3.5 px`, relative residual
`< 0.15`. Density = accepted-solution count at the solved plan position, Gaussian σ=1.5 px;
depth/quality = density-weighted means, `NaN` where smoothed density is 0 (native HGB
missing-value routing). Euler channels join the selective-residualization set (they derive
from regional survey fields and could inherit block/flight-line structure).

**Three locked arms (same seed base `20261026`, budget 37,654 dots, spacing 2.8 px, clearance > 2 px):**
1. `Arm 1 EUL1-primary`: 59-channel model; Regime-B (32%) subsurface multiplier adds the three
   Euler density/quality channels to DPRF1's subsurface set.
2. `Arm 2 EUL1-noEuler` (paired ablation / replay control): exact 52-channel DPRF1 configuration
   through the same code path (`extra_mm=None`).
3. `Arm 3 EUL1-channelsOnly`: 59-channel model; Regime-B multiplier = DPRF1's legacy subsurface
   set only. Attribution: Arm3−Arm2 = channel effect; Arm1−Arm3 = regime-gating effect.

**Full-footprint export:** Arm 1 only, Dual-Partition Stitched-OOF (quadrant + 45° diamond) +
apron quantile debiasing; 0% in-sample pixels. Budget fixed at 37,654 *in advance* (B2-matched);
a budget-sensitivity curve may be *reported* from fold predictions but must not change the export.

## 4. Mandatory gates (all automated; zero human-inspector fallback)

1. **Canary (Rule 4):** every one of 59 channels solo on `SegmentHoldout.canary`, both
   polarities; `max(AUC, 1−AUC) ≤ 0.90` or halt.
2. **Holdout (Rule 3):** pooled HOLDOUT-DTI + 95% CI (`gems-segment-pooled-v1`, 60,988 withheld)
   for all arms; paired 10 km block-bootstrap Arm1 vs Arm2 and Arm1 vs replays; statement vs
   recorded point-best DPRF1 0.16379. No number may be written as a leaderboard score/projection.
3. **Novelty (Rule 1):** pre-placement surface **and** final dots vs the pinned registry
   (`priority_rasters.json` + local lanes incl. DPRF1/TRSG1 + 83 peer blobs):
   `|ρ| ≤ 0.90`, 3-px dot overlap `≤ 0.70` per competing-method raster. Literal all-entry
   result (incl. `registry-039` lattice) reported transparently; exceeding limits = duplicate,
   log and stop (no retuning, no dot-jittering to escape).
4. **C2ST:** exact-file spatial-block audit, labels first; strict gate AUC < 0.55.
5. **Format:** shared validator on exact bytes — single-band float32, template CRS/shape/
   transform, whole-array finite `[0,1]` for `-zeros.tif` (the reported portal
   "Predicted values must be in range [0, 1]" failure mode), NaN-outside twin, single-TIFF ZIP.
6. **Run card (Rule 5):** one JSON card (hypothesis, mechanism, mimic, HOLDOUT-DTI+CI,
   registry correlation/overlap, sha256, validator output, name + ≤140-char note,
   verdict promote/negative).

## 5. Decision ceiling, declared in advance

`gems.selector` v2 is a *negative-only* screen: literal lattice retained, live quota unknown,
positive replay certificate unimplemented. Therefore the best honest outcome of this session is
**"strongest unscored unique candidate — DOWNLOAD: YES · SUBMIT: NO (`DO_NOT_SUBMIT`), selector
step pending"**, exactly the ceiling DPRF1 reached. Claiming `SUBMIT: YES` would require (i) a
*prospective* selector-policy change separating synthetic calibration controls from competing
methods, (ii) an owner-recorded live-quota receipt, (iii) independent replay — none of which
this lane may grant itself after seeing results. If EUL1 fails to beat DPRF1's point-best or
fails novelty, verdict is `negative` and DPRF1 remains the #1 unscored candidate; that negative
result is a deliverable, not a reason to burn more experiments.

## 6. Official sources for manual review

- Competition/problem/metric: https://www.drivendata.org/competitions/306/competition-doe-gems/ · https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/ · leaderboard https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/ (never scraped; login-gated data not bypassed)
- Rules PDF: https://docs.nlr.gov/docs/fy26osti/96647.pdf
- Reference solution: https://github.com/drivendataorg/gems-prize-reference-solution (reachable; HTTP 200 checked 2026-10-26)
- USGS GeoDAWN survey: https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and · DOI 10.5066/P93LGLVQ
- OpenEI GDR INGENIOUS #1391: https://gdr.openei.org/submissions/1391 · https://gbcge.org/current-projects/ingenious/
- CRS EPSG:32611: https://epsg.io/32611 · Tversky index: https://en.wikipedia.org/wiki/Tversky_index
- Euler deconvolution method: Thompson (1982) *Geophysics* 47; Reid et al. (1990) *Geophysics* 55 (method citation; no external data taken from these)
- NASA ASF OPERA (Rank-5 source, deferred): https://asf.alaska.edu/datasets/daac/opera/

*Core values applied: Maximize P(Win) — spend the session on the only hypothesis class that can
add information B2/DPRF1 never saw; Own the Outcome — the gate decides, end-to-end, with no
manual inspection step and no invented score.*
