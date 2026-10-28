# Submission validator review — 2026-10-28

**SUBMIT: NO.** This review did not create a competition TIFF, run a geological experiment, or use a submission slot. The prompt refers to a single assigned method paragraph, but no such paragraph is present. Do not choose a lane or treat any historical download as a new unique candidate. See the [nine-site historical champion table](historical-champions.html), [submission guide](executive-summary.html), and [prospective hypotheses](research-directions-20261027.md).

## Finding: a finite prediction can still be masked

The shared `gems.submission.check_variants` on this branch reads the raw values and checks their range, but does not require every pixel within the sample footprint to be unmasked. A GeoTIFF can therefore have a finite, in-range pixel that GDAL reports as missing via a mask or nodata. This is a **local validator false pass**, not evidence that the organizer accepted or rejected a file. A submission must not be approved based on this validator alone.

Reproduction, using only a temporary synthetic raster and the existing template (not a competition candidate):

```sh
PYTHONPATH=src python - <<'PY'
import tempfile
from pathlib import Path
import numpy as np
import rasterio
from gems.submission import write_submission, check_variants

with tempfile.TemporaryDirectory() as d:
    template = 'data/bridge/sample_submission.tif'
    output = Path(d) / 'synthetic.tif'
    with rasterio.open(template) as src:
        footprint = np.isfinite(src.read(1))
    write_submission(np.full(footprint.shape, 0.5, np.float32), template, output)
    with rasterio.Env(GDAL_TIFF_INTERNAL_MASK=True):
        with rasterio.open(output, 'r+') as dst:
            mask = np.full(footprint.shape, 255, np.uint8)
            y, x = np.argwhere(footprint)[0]
            mask[y, x] = 0
            dst.write_mask(mask)
    result = check_variants(output, template)
    print('format_valid:', result['format_valid'], 'hard failures:', result['hard_failures'])
PY
```

Observed on the starting commit: `format_valid: True`, `hard failures: []`. This does not imply that all previously checked TIFFs have masks or that their bytes are invalid. Revalidate each exact artifact after integrating a fix. Sidecar masks also require attention because a TIFF hash alone does not bind separately stored files.

[Concurrent PR #84](https://github.com/buffedlizard55-lab/GEMSDOE24/pull/84) states that it hardens the same shared validator and sidecar handling. Its changes were not merged into this branch or independently replayed in this session. A small local patch that added a new hard check exposed a separate integration problem: archived receipt comparisons and the site build rejected the changed check schema. That patch was removed, not kept as a private fork. Merge/review the shared fix once, preserving historical receipts without mistaking them for fresh validation, and rerun the full suite and exact-file validations. Do not weaken the new check simply to match old receipts.

## Rechecked blockers

The shared read-only uniqueness checker was rerun against the hash-pinned retained lattice and template. For **37,654** and **44,090** in-footprint dots, the minimum overlaps are **82.34%** and **84.92%** respectively. These are geometric bounds, **not scores**, and both trigger the protocol's greater-than-70% stop. The check is not a complete registry audit. Do not retune a stopped lane or place dots in lattice holes to evade the policy. The new method assignment and prospective policy resolution are needed before an experiment can proceed.

The historical GEMSDOE32 B2 value **0.2778 is owner-reported and unverified**, not an organizer-confirmed receipt. The [prior ancestry analysis](session-review-b87d739e-20261028.md) provides a plausible false-positive/coverage tradeoff, not proof of the hidden-score mechanism. It is not possible to infer that a new candidate will beat it from the supplied numbers. The prompt's conflicting leaderboard snapshots are not a current verified feed.

## Test and access limits

A virtual environment was installed from `requirements.txt`; the reproducible geometry check exited 2 as designed. The site builder ran successfully on the unmodified shared validator; generated timestamp-only changes were discarded. After restoring shallow Git history, the full suite passed: **578 tests** in 249.40 seconds on the unmodified shared validator. This environment allows GitHub and package hosts, not the DrivenData portal, NLR, USGS or Dropbox. No current quota, organizer receipt, official data download or live leaderboard was verified. Existing cached external rasters and bridge rasters are present, but the main training raster/feature stack is absent in this checkout. Public source descriptions and their caveats are listed in the prospective hypotheses document.

## Three-pass review

1. **Audit and reproduce:** reviewed the standing instructions, the nine-site table, the shared writer and validator, and reran the hash-pinned geometric feasibility gate. Reproduced the masked-pixel false pass using a temporary synthetic TIFF.
2. **Adversarial integration review:** a local additional hard check caught the mask but broke archived-receipt comparisons and site generation; it was reverted. Inspected the concurrent PR's public diff, which includes footprint-mask and sidecar checks. Its integration and historical-receipt handling still need review; its CI status is not evidence of an organizer acceptance.
3. **Request recheck:** no method paragraph, current portal access or complete registry replay was available. No candidate, estimated hidden score, authorized download or new scientific conclusion was fabricated. Existing site summaries and prospective hypotheses are linked above; other site repositories were not changed.

## Next steps

1. Review and integrate the concurrent shared-validator fix, then rerun exact-file validators and full CI; verify both internal masks and external sidecars.
2. Obtain a prospective lane assignment and resolve the literal registry policy without excluding inconvenient comparators.
3. Restore the hash-checked feature stack, check per-channel provenance, run per-feature leakage canaries, preregister the bounded experiment, and evaluate with the shared buffered-segment pooled-DTI evaluator and paired uncertainty.
4. Check pre-placement surface and final-dot novelty across the full current registry, then use an independent selector and verified account quota. A format pass, a historical owner claim, or a scientific holdout alone does not authorize submission.

[Run card](data/session-mask-review-20261028.json) · [official reference solution](https://github.com/drivendataorg/gems-prize-reference-solution) · [competition format](https://www.drivendata.org/competitions/306/competition-doe-gems/data/).
