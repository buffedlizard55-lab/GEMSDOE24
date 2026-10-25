# H24-FUSE findings — 2026-10-25 (negative; stopped at the duplicate gate)

**Status:** `verdict: negative` · `ok_to_download: false` · `ok_to_submit: false` · no artifact packaged · no slot spent · no ORGANIZER-CONFIRMED score.
Run card: [`evidence/fuse_run_card_20261025.json`](../evidence/fuse_run_card_20261025.json) (derived deterministically from the recorded stop by `scripts/run_fuse_lane.py --write-card`).
Record: [`evidence/fuse_experiment_20261025.json`](../evidence/fuse_experiment_20261025.json). Preregistration: [`knowledge/15_preregistered_next_gen_2026-10-25.md`](15_preregistered_next_gen_2026-10-25.md), Rank 1.

## 1. Hypothesis tested

Adding the four SAHG1-engineered channels (`G_sat`, `R_alt`, `B_step`, `H_conduit`) to the 27 prepared base channels of the same fold-local HistGradientBoosting learner used by the reconstructed OOF baseline should lift holdout DTI above the recorded baseline (0.13000).

## 2. Result (all numbers HOLDOUT-DTI, evaluator `gems-segment-pooled-v1`, 60,988 withheld positives)

| Arm | HOLDOUT-DTI | 95% CI (10 km blocks, 1,999 draws) |
|---|---|---|
| Reconstructed OOF multi-physics HGB (27 ch.) | 0.1299968 | [0.11565, 0.14396] |
| **H24-FUSE** (27 + 4 SAHG1 ch.) | **0.1299501** | [0.11479, 0.14476] |
| Paired Δ (FUSE − baseline) | −0.0000467 | [−0.00420, +0.00396] |

- The baseline reproduces the recorded value (0.129997) to the last digit, so the harness is trustworthy.
- FUSE is **statistically tied** with the baseline. The paired interval spans zero in both directions. Extra SAHG1 channels add no measurable holdout signal to the learner. This is a negative result and a deliverable.
- The prior SAHG1 hand-crafted product scored 0.09672 (see `knowledge/13_SAHG1_findings_2026-10-25.md`). Learning from its channels recovers the baseline level, but not more.

## 3. Gates

| Gate | Result |
|---|---|
| Leakage canary (31 features, each alone, both polarities, threshold 0.90) | PASS. Max pooled AUC 0.592. |
| Surface novelty before placement (46 method lanes) | PASS. Max abs rank ρ 0.347. |
| Final-dot novelty, method lanes, all-dot overlap ≤3 px (limit 0.70) | **FAIL → STOP.** Over 0.70: registry-006 (`gems27-h28-1-edge-coherence-plus-t-v2…`) at **0.7416**; registry-016 (`gems28-h37-1-probe-union-pool-r1…`) at **0.7394**; registry-040 (0.7048), -041 (0.7189), -042 (0.7073), all classified as competing method lanes whose files sit in `inputs/calibration/`. |
| Peer-blob check (83 blobs) | FAIL. Max dot overlap 0.7416 (`peer_blob_novelty` in the record; the blob that hits it is not named there). |
| Literal all-entry check (includes synthetic lattice registry-039) | FAIL. Overlap 1.0 (known, non-discriminating). |
| Exact-file C2ST nuisance audit | Not run. The protocol stops before packaging, so the audit was skipped. |

**Note:** the card lists six over-limit entries, including the lattice (039). The method-lane duplicates are 006, 016, 040, 041, 042.

**Decision:** the protocol says "log it as a duplicate and stop." The runner records the stop and does not write a TIFF. There is no downloadable FUSE file.

## 4. Why the final dots collide with other lanes (mechanism, not a fix)

Every competing lane places dots on the same LiDAR-visible ridge and scarp geometry, which is the strongest visible signal in the footprint. The 3-px directional overlap rule therefore reaches 0.4–0.6 for almost any ridge-driven emitter (in the record, most method lanes sit between 0.34 and 0.58; registry-043 is 0.63; registry-006 and -016 are about 0.74), so only a few specific placements reach 0.70+. A learned model trained on the same visible catalogue and the same LiDAR channels converges on that ridge set. Passing the 3-px rule requires **either** a different placement geometry **or** a different signal class (subsurface-only or alteration-only). It is not achieved by changing the score surface.

## 5. Attempt log (budget: 3 experiments)

1. **Attempt 1** printed the holdout arms, then crashed on a missing peer-blob cache (`data/research/peer_review`). No record was written. The cache was restored with `scripts/review_peer_registry.py` (GitHub pinned blobs, 84 unique files).
2. **Attempt 2** completed, but its final-dot novelty call omitted `dots=final_dots`, so overlap came back `None` and `literal_all_entries_passed` was a **false pass**. Found on review, before any conclusion. Its TIFFs and records were deleted. Nothing from it is cited.
3. **Attempt 3** is the recorded run (the corrected call). It stopped at the duplicate gate.

No HGB, sampling, seed or budget parameter changed across attempts. Attempts 1 and 2 are disclosed in `ATTEMPT_NOTE` in the record. Attempt 2's bug is the reason the budget is now spent.

## 6. Irregularities for review

1. **H33 analysis citation.** `knowledge/14_h33_analysis_2026-10-25.md` §1 and §5 cite `registry/live_scores.json` as a source for the owner-reported 0.2778. That file does **not** contain 0.2778 (its `warning` field says owner-reported; the value is absent). The only source for 0.2778 in the repository is the owner brief (`knowledge/owner_brief_2026-10-25.md`) and documents that quote it. The citation should be corrected. Not corrected in this session.
2. **Conflicting leaders.** The brief states 0.3195 and 0.4413 as the "current high" and 0.2778 as the H33-B2 score. None of these are ORGANIZER-CONFIRMED in the repository. The live leaderboard was not automatically read (DrivenData automation is forbidden by `AGENTS.md`).
3. **Role classification.** Registry-040/041/042 are classified `competing_method_lane` although their files live in `inputs/calibration/`. Under that classification they count as duplicates (0.7048, 0.7189, 0.7073). Whether they should be re-classified as calibration controls is a registry-governance question for review, not something this run changed. Registry-043 sits at 0.6320. Registry-039 (lattice) is 1.0 and is treated as a calibration control.
4. **Owner mirror integrity only.** Restored inputs are hash-pinned to owner-supplied GitHub mirrors (`buffedlizard55-lab/GEMSDOE`). Hashes verify integrity, not organizer provenance.
5. **`data/bridge/example_submission.tif`** is still absent; `sample_submission.tif` is present (pre-existing irregularity).
6. **Tests.** The clone was shallow, so `verify_mtr_receipt` could not find its pinned source commit. `git fetch --unshallow` fixed it (local operation; no code change). Full suite: 183 passed.

## 7. What this does and does not mean

- It **does not** mean the learner cannot beat 0.13000. A single fixed run with one channel set failed. The preregistered next steps are different.
- It **does** mean SAHG1 channels, as a fold-local extra input, carry no new holdout signal beyond the 27 base channels.
- Dot overlap, not holdout DTI, is the binding constraint for a new lane in this repo. Any new idea must be checked for the 3-px overlap first.

## 8. Recommended next steps (not run; each needs its own preregistration)

1. **Placement decorrelation (preregister first).** Exclude pixels within 3 px of any method-lane registry raster *before* Poisson-disk placement, then re-score holdout. This is a new lane, not a tuned FUSE.
2. **Test ranks 2–5 of the preregistration** (H24-CON already negative; H24-TIP, H24-RAD, H24-DEP remain untested). Each needs a holdout gate and a novelty gate before placement.
3. **Obtain the official leaderboard receipt** through the owner's manual check, if the owner wants a verified score for H33-B2. Do not automate DrivenData access.
4. **Fix the H33 citation** (irregularity 1) and add the FUSE card to the site and README status block (done in README; site rebuild deferred).
5. **Re-verify the H33-B2 forensic claims** (0 dots within 200 m of catalogue; pixel counts) directly from the artifact bytes before relying on them.

## 9. Sources for manual review

- Competition problem page: https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/
- Leaderboard (human-read only; not automated): https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/
- Reference solution: https://github.com/drivendataorg/gems-prize-reference-solution
- Submission format PDF: https://docs.nlr.gov/docs/fy26osti/96647.pdf
- GeoDAWN (USGS ScienceBase): https://www.sciencebase.gov/catalog/item/657e1d85d34e23d3533209f7
- Tversky index (metric family): https://en.wikipedia.org/wiki/Tversky_index
