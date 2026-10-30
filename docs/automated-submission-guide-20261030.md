# Automated validation and submission guide — 2026-10-30

## Current decision

**There is no submission-authorized TIFF. Do not upload any file from this repository or the historical table.** This guide describes a fail-closed workflow for a future candidate. Local generation and validation are automatable; access to DrivenData and upload are not automated by this project agent. A successful file-format check does not authorize a competition slot.

## 1. Confirm prerequisites before generating a file

1. Read [`README.md`](../README.md), [`MISSION_PROMPT.md`](MISSION_PROMPT.md), and [`AGENTS.md`](../AGENTS.md).
2. Confirm the user-assigned single-method paragraph exists. If it is absent, stop; do not invent or restart a lane.
3. Preregister one lane, named input layers, transforms, non-fault mimics, controls, leakage checks, and holdout design before running it. Verify any external data source is officially free and actually obtainable before calling the idea viable.
4. Enforce the experiment/time budget and retain negative results. Do not spend a weekly slot during research.

## 2. Run the shared scientific and novelty gates

- Reuse the shared feature stack and [`scripts/evaluate_holdout.py`](../scripts/evaluate_holdout.py). Hide whole fault segments with a spatial buffer; derive catalogue features only from visible faults; apply the visible-fault mask exactly; report pooled DTI with α=0.2, β=0.8, and the 300 m triangular kernel.
- Test each source feature/transform alone for leakage. AUC >0.90 is suspected leakage until disproven.
- Compare the pre-placement surface and final dots against every comparable registry raster. Stop if absolute rank correlation >0.90 or >70% of candidate dots are within 3 px of any one raster. Do not reduce or retune a stopped budget, move dots into comparator holes, or remove/alter a registry entry.
- A candidate must beat the comparable current best by the required 2–3% with the preregistered evidence. Weekly-slot consideration is a separate selector decision and requires independently verified quota. No slot is approved here.

## 3. Write and locally validate one GeoTIFF

Only after the research and novelty gates pass, serialize the final prediction through the shared writer. It rejects overwriting the input or template and validates a temporary output before replacing the requested destination. Its JSON output is a local format receipt—not a scientific selector, organizer authorization, or portal-acceptance guarantee.

Example for an already computed two-dimensional prediction array:

```bash
.venv/bin/python scripts/submission_writer.py \
  path/to/prediction.npy \
  docs/downloads/gems24-<lane>-<date>-<content-id>.tif \
  --template data/bridge/sample_submission.tif \
  --outside nan
```

For an aligned single-band prediction GeoTIFF, pass its path instead of the `.npy`. Check the command's JSON output and the exact file again. The expected template is EPSG:32611, 3730×3292 at 100 m, with the exact affine tuple `(100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)` in the project validator's order. Confirm one float32 band, finite in-footprint values in [0,1], no masked cells in the footprint, and exact CRS/shape/transform against the pinned template. Keep the unique artifact name and record its SHA-256.

The writer supports `--outside nan` and `--outside zero`. The supplied template uses an exterior NaN convention, while an all-finite zero-outside variant can satisfy a whole-array range test but differs from that convention. The portal's interpretation and the cause of the reported range error have not been verified in this review; neither encoding is claimed organizer-approved. Preserve both the template and exact local receipt; do not silently rewrite a failed file.

## 4. Create the audit card and decision

Keep a JSON run card beside the result containing at least:

- lane/hypothesis, physical mechanism, named non-fault mimic, preregistration and source hashes;
- holdout label, evaluator version, withheld-positive count, 95% CI, buffer, visible-only catalogue and masking evidence;
- feature-only leakage results, pre-placement rank correlations, final-dot overlaps, registry version/hash, and exact TIFF SHA-256;
- template/format checks, unique filename, note ≤140 characters, number of experiments and slots used;
- explicit `DOWNLOAD: research only` or `DOWNLOAD: submission candidate`, and a fail-closed `SUBMIT: NO/YES` verdict from the separately authorized selector.

Do not convert an internal HOLDOUT-DTI or an owner-reported number into a leaderboard estimate. Use `NOT ESTIMABLE` unless a calibrated estimate is independently justified; use `ORGANIZER-CONFIRMED` only when an artifact-linked receipt exists.

## 5. User-controlled portal step (only after selector approval)

The project agent does not automate DrivenData access or upload. If a future artifact is positively authorized and the owner chooses to use a slot:

1. The owner signs into the official [GEMS competition submissions page](https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/).
2. Upload only the exact authorized single-band `.tif` named in the selector receipt; do not upload a ZIP or a historical research artifact.
3. Enter the exact short note (≤140 characters) recorded in the run card.
4. Save the organizer's artifact-linked receipt, timestamp, and returned score. Verify the receipt identifies the exact artifact before labeling anything `ORGANIZER-CONFIRMED`.
5. If the portal rejects the file, preserve the exact response and artifact hash; investigate range, footprint encoding, CRS, shape, transform, or other requirements without guessing. A local pass is not evidence of acceptance.

## Current-session evidence links

- [Three-pass review](repo-review-20261030-arena-6a29c5b2.md)
- [Nine historical champion downloads and decisions](historical-champions.html)
- [Fixed-budget uniqueness feasibility](submission-readiness.html)
- [GitHub freshness receipt](data/portfolio_freshness.json)
- [Recorded S3DEP1 negative run card](data/s3dep1_run_card.json)
