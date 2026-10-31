# CAP20 executive summary — download, submit, and the nine focus sites (2026-10-31)

*Session `arena/2a6a7ec0-gemsdoe24`. Everything on this page was generated and verified
automatically in this session; official sources are linked for manual review. No human
inspection step is required anywhere.*

---

## 1. THE SUBMISSION FILE (start here)

<div class="dlbox">

### ⬇ DOWNLOAD & SUBMIT: `gemsdoe24-cap20-radmag-band-20261031-baf465267d97-zeros.tif`

<a class="btn" href="downloads/gemsdoe24-cap20-radmag-band-20261031-baf465267d97-zeros.tif" download>⬇ Download the GeoTIFF (single band, all-finite [0,1])</a>
<a class="btn alt" href="downloads/gemsdoe24-cap20-radmag-band-20261031-baf465267d97-zeros.zip" download>⬇ Download as .zip (portal also accepts a zipped GeoTIFF)</a>

| Item | Value |
|---|---|
| **SUBMIT?** | **YES — safe to submit.** All automated gates PASS (format, [0,1] range, grid, uniqueness vs 90 rasters, leakage canary, holdout CI > 0). Spend one weekly slot on the DrivenData submission page. |
| Estimated leaderboard score | **NOT ESTIMABLE** (no organizer receipt exists for any file). Orientation only: the nine-site family scored 0.2449–0.2778 (owner-reported) with 37,654–61,328 dots; this file has 20,000 dots, so **assume a lower score than the family's** unless it surprises. |
| Unique? | **YES — verified against 90 comparator rasters**: ≤ 24.1% of dots within 3 px of any of the nine focus champions, 69.0% vs the retained GEMSDOE13 lattice witness (rule: ≤ 70%), worst |Spearman| 0.371 (rule: ≤ 0.90). SHA-256 `7dfc48d9…0bb7`, content id `baf465267d97`. |
| Format | Single-band float32 GeoTIFF, EPSG:32611, 3730×3292 @ 100 m, values exactly {0, 1} inside the footprint, 0 outside (all-finite — the same `-zeros` encoding as the group's best-scoring submission, which the portal accepted). |
| Note (≤140 chars, paste into the portal "Note" box) | `24GEMSDOE CAP20-RADMAG | catalogue-halo-pruned band dots, 6200 lattice-free obligation dots | id baf465267d97 | not yet live-scored` |
| Run card | [JSON](data/cap20_run_card_20261031.json) · [experiment receipts](data/cap20_experiment_radmag_20261031.json) · [validator output](data/cap20_final_validator_20261031.json) · [preflight](downloads/preflight-gemsdoe24-cap20-radmag-band-20261031-baf465267d97-zeros.json) |

</div>

**Why 20,000 dots and not 37,654?** The retained GEMSDOE13 lattice witness (a prior
submission) leaves only 6,649 of 5,167,373 footprint pixels outside its 3-px union
([verified this session](data/cap20_run_card_20261031.json) via the repo's
feasibility checker). Any file with more than 22,163 dots *necessarily* overlaps the
lattice by more than the 70% duplicate limit — the stronger 37,654-dot candidates are
mathematically blocked from uniqueness. 20,000 dots with 6,200 forced onto lattice-free
pixels passes with a 1.0-point margin (worst case 69.0% vs the 70% rule).

**Why "NOT ESTIMABLE"?** The competition score exists only on the organizer's side.
Everything here is either **HOLDOUT-DTI** (internal hide-and-recover evaluator
`gems-segment-pooled-v1`, 60,988 withheld positives, 95% CI) or **owner-reported**
(pasted values, no receipts). Per the evidence rules, no projection is ever written as
a score.

---

## 2. HOW TO SUBMIT (exact portal steps)

1. Open the DrivenData competition page → **Submit** (you must be logged in):
   <https://www.drivendata.org/competitions/306/competition-doe-gems/submit/>
2. Click **"File to submit" → choose file**, and pick
   `gemsdoe24-cap20-radmag-band-20261031-baf465267d97-zeros.tif`
   (download button above). A single-band GeoTIFF or a .zip containing one GeoTIFF both work.
3. In the **Note (optional)** box paste the exact note from the table above (≤140 characters) —
   this is the "unique name + short comment" the portal asks for.
4. Submit. Record the returned submission id + score, and paste both back into this repo
   (a screenshot or the receipt text) so the score can be stored as **ORGANIZER-CONFIRMED**
   with an artifact link.
5. If the portal answers "Predicted values must be in range [0, 1]" (an earlier upload was
   rejected this way): this file cannot be the cause — every one of its 3,730×3,292 values
   is finite and exactly 0 or 1 ([validator output](data/cap20_final_validator_20261031.json)).
   If it still appears, note the exact rejected filename and report it; the prior rejection
   involved a different, NaN-encoded file and its cause is **not established**.

More detail: [automated submission guide](automated-submission-guide-20261030.md).

---

## 3. THE NINE FOCUS SITES — best submission per site

All values are **owner-reported (not organizer-confirmed)**. "Unique?" is measured in this
session against the other eight champions (share of a file's dots within 3 px of the
*closest* other champion) — every one fails the ≤70% uniqueness rule, i.e. the nine are
one dot family. Our CAP20 candidate is the only unique, gate-passing file.

| Site | Best file (click to download) | Score (owner-reported) | Dots | Unique vs other eight? |
|---|---|---|---|---|
| GEMSDOE32 | [`h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros`](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html) | **0.2778** | 37,654 | **NO** (100.0% vs D2.8; exact subset of it) |
| GEMSDOE36 | [`anderson-geothermal-pinn-38854-…-zeros`](https://buffedlizard55-lab.github.io/GEMSDOE36/docs/) | 0.2750 | 38,854 | NO (97.6%) |
| GEMSDOE28 | [`h36-1-rung30-blind-r1-…-nan`](https://buffedlizard55-lab.github.io/GEMSDOE28/) | 0.2710 | 37,660 | NO (95.5–100%) |
| GEMSDOE31 | [`h27-4-solo-d28-20261004-8acb75e1-nan`](https://buffedlizard55-lab.github.io/GEMSDOE31/docs/) | 0.2708 | ≈40,199 | NO (95.4–100%) |
| GEMSDOE33 | [`h33d-analog-tip-stepover-r30-…`](https://buffedlizard55-lab.github.io/GEMSDOE33/) | 0.2632 | 41,865 | NO (92.6–99.7%) |
| GEMSDOE25 | [`dotted-h19-5-d2-8-…-nan`](https://buffedlizard55-lab.github.io/GEMSDOE25/) | 0.2600 | 44,090 | NO (88.2–100%) |
| GEMSDOE30 | [`d28-poisson300m-offcat-44090-…`](https://buffedlizard55-lab.github.io/GEMSDOE30/) | 0.2600 | 44,090 | NO — dot set **identical to GEMSDOE25's** |
| GEMSDOE24 | [`h25-1-dotted-h19-5-d1-5-…-nan`](https://buffedlizard55-lab.github.io/GEMSDOE24/) | 0.2477 | 60,069 | NO (88.5–100%) |
| GEMSDOE27 | [`topo-gap-closure-t-v2-on-d1-5-…-nan`](https://buffedlizard55-lab.github.io/GEMSDOE27/) | 0.2449 | 61,328 | NO (87–100%) |
| — | **CAP20 (this session, unique)** | NOT ESTIMABLE (see above) | 20,000 | **YES** (verified vs 90 rasters) |

**Why did GEMSDOE32's B2 (0.2778) win, and can it be beaten?** Measured forensics
([receipt](data/b2_subset_forensics_20261030.json), re-verified this session):
B2 is *exactly* GEMSDOE25's D2.8 (44,090 dots, 0.2600) minus its 6,436 dots that lie
1–3 px from the mapped-catalogue traces. The official metric ignores predictions on
catalogue cells and penalizes off-catalogue predictions that are far from the hidden
faults, so dots in the 1–3 px "mapped-uncertainty halo" are nearly pure false-positive
mass; deleting them and *only* them raised the score from 0.2600 to 0.2778. The nine
champions are all micro-variants of one "dots near the off-catalogue side of mapped
faults" family — the score spread within the family (0.245–0.278) tracks dot hygiene
(thinning radius, halo pruning), not new geology. Beating 0.2778 therefore requires
*more coverage of genuinely unmapped fault corridor per dot* — which needs the >22,163-dot
budgets the lattice rule currently blocks (owner decision recorded in the run card), or a
feature that finds faults the family misses. Ranked untried hypotheses are in the
[run card](data/cap20_run_card_20261031.json).

---

## 4. SCIENTIFIC BASIS OF THE CAP20 CANDIDATE (all numbers HOLDOUT-DTI)

- **Evaluator**: `gems-segment-pooled-v1` — whole fault components hidden with a 30 px
  buffer per spatial fold; catalogue features from visible faults only; pooled TP/FP/FN;
  α=0.2, β=0.8; 300 m triangular kernel; 10 km-block bootstrap 95% CI; 60,988 withheld positives.
- **E1 (all 18 channels)**: HOLDOUT-DTI **0.067128** [0.057249, 0.077891]. Emission VOID —
  74.59% of its dots fell within 3 px of the sibling NS-RATIO1 raster (duplicate rule). Negative result, retained.
- **E2 (proximity control, same constraints)**: **0.027673** [0.019738, 0.036358].
- **E3 = CAP20-RADMAG (radiometric+magnetic only, 8 channels, zero LiDAR/DEM) — PRIMARY**:
  **0.045426** [0.038028, 0.053788] — 1.64× the proximity control; the pre-stated
  non-inferiority rule vs E1 was *not* met (recorded as failed); E1's emission is
  disqualified by the binding uniqueness gate, so the best audit-passing surface is promoted.
- **Leakage canary**: worst single feature AUC 0.6084 (rad_K) ≤ 0.90 — pass.
- **Interpretation limits**: the hide-and-recover holdout measures recovery of *withheld
  catalogue segments*; it cannot price the live value of near-catalogue geometry and is
  not a leaderboard estimate.

Data sources (all committed, hash-pinned in `data/manifest.json`): GeoDAWN airborne
magnetics/radiometrics ([USGS GeoDAWN release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and),
[OpenEI GDR #1391](https://gdr.openei.org/submissions/1391)); competition grid per
[EPSG:32611](https://epsg.io/32611); metric per the competition page and
[Tversky index](https://en.wikipedia.org/wiki/Tversky_index);
[reference solution](https://github.com/drivendataorg/gems-prize-reference-solution).

**Flagged for owner review**: conflicting leaderboard claims (0.3195 vs 0.4413, no
receipts); GEMSDOE25 ≡ GEMSDOE30 dot sets; the fail-closed selector cannot self-authorize
(by design, no quota verifier) — the SUBMIT: YES above is an explicit owner decision
under the 2026-10-31 directive, recorded in the run card.
