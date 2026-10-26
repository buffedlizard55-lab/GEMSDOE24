# Current owner request — portfolio session, 2026-10-26 16:12 UTC

Read this at every session start, with README and AGENTS. This is an explicitly
**normalized requirements record, not a claimed verbatim transcript**. The full
previously preserved owner message and its long site catalogue remain embedded
in README and in `owner_brief_2026-10-26.md`. This addendum records the current
request's priority and differences; it does not replace or erase those records.

## Highest urgency (owner wording)

> MUST GENERATE A UNIQUE TIF SUBMISSION FOR THE COMPETITION. DO NOT COPY A PREVIOUS SUBMISSION UNLESS IT'S FOR LEARNING AND EDUCATION. BUT WE MUST GENERATE A UNIQUE TIF SUBMISSION. IT MUST BE OBVIOUS WHETHER IT IS OK TO DOWNLOAD AND SUBMIT THE GENERATED TIF SUBMISSION.

Focus on **GEMSDOE24, GEMSDOE25, GEMSDOE27, GEMSDOE28, GEMSDOE30, GEMSDOE31,
GEMSDOE32, GEMSDOE33 and GEMSDOE36**. Review every focus site, learn from the
highest listed submissions, and provide a clear executive table stating the
exact downloadable file, estimated score or evidence limitation, uniqueness,
and whether it is actually okay to submit. Do not copy prior predictions or
call new filenames/bytes scientific uniqueness. The project's automated gates,
not a human inspector, decide the file's status.

## Parallel-run protocol (operative constraints)

1. Stay in the single assigned method paragraph. That paragraph is absent in
   this message; do not claim a lane was assigned. If rank correlation with a
   registry raster exceeds 0.90, or more than 70% of candidate dots lie within
   3 px of any registry raster, log duplicate and stop. Check before placement
   and on final dots; no after-the-fact exemption or registry-driven dot moving.
2. Reuse the cached feature stack, `evaluate_holdout.py`, and
   `submission_writer.py`. Fix shared tools centrally, not private forks.
   Hide whole fault segments with a buffer, derive catalogue features from
   visible faults only, mask visible faults exactly, and pool DTI components
   with alpha 0.2, beta 0.8, 300 m triangular kernel.
3. Every performance result must be HOLDOUT-DTI with evaluator version,
   withheld-positive count and 95% CI, or ORGANIZER-CONFIRMED from an
   artifact-linked submission-page receipt. A projection is never a score.
   Prompt values without receipts remain explicitly unverified owner claims.
4. Test every actual feature/transform alone on the holdout; AUC above 0.90
   means suspected leakage until disproven. Existing stricter two-polarity
   canary checks remain in force.
5. End with one JSON run card: hypothesis, mechanism, named non-fault mimic,
   holdout/CI, registry correlation and overlap, exact raster SHA-256,
   finite/range/grid validator, name, note of at most 140 characters, and
   promote/negative verdict. Negative results are deliverables.
6. At most three experiments or two hours. Promotion to a real weekly slot is
   a separate selector decision under the actual submission-page allowance.
   Never spend a slot on a hypothesis that has not beaten the current
   comparable holdout best. Do not retune stopped lanes.

## Scientific and engineering outcome requested

- Before implementation, rank three to five untried geological hypotheses by
  expected DTI benefit (qualitative until measured) and cost. Name exact layers,
  physical transform, rationale for finding uncatalogued faults, distinction
  from previous methods, and non-fault alternatives. Verify required free,
  official external sources are obtainable before calling an idea viable.
- Explain why the reported GEMSDOE32 H33-B2 result may have improved; distinguish
  observed pixel geometry from an unobservable hidden-label causal explanation.
  Research geothermal systems critically, but do not mistake fault proxies for
  verified geothermal vents or guaranteed productive reservoirs.
- Review prior next steps first. Restore available inputs autonomously; use
  `scripts/download_competition_data.sh` / `scripts/prepare_data.py` where
  appropriate. Do not pretend an unavailable official host is accessible or
  require credentials in chat. The inherited statement that training requires
  a GPU is subject to source verification, not an unquestioned assumption.
- Produce a clean GitHub Pages site with the main download/status at the start,
  a dedicated executive submission guide, a unique filename and short note.
  Prevent invalid finite/range/grid output; investigate the reported portal
  error "Predicted values must be in range [0, 1]" without guessing its cause.
  A local file check is not a guarantee of organizer acceptance.
- Keep official provenance, immutable file hashes, limitations and irregularities
  in auditable tables with review links. Maintain a current source-activity feed
  without misrepresenting it as a live leaderboard. No automatic DrivenData
  access under the standing project policy; no secret requests or fake receipts.
- Maximize P(Win) and Own the Outcome: act on engineering defects, preserve
  negative evidence, and do not spend scarce slots on cosmetic changes.
- Preserve this request in README as the starting point for later sessions.
  Complete three passes: implement/verify, fix bugs/assumptions/edge cases, then
  recheck all requirements and quality. Open a PR from the fixed Arena branch,
  merge after checks, distinguish merge from deployment, and state remaining
  work/access limits honestly. Do not claim the central TIFF goal is achieved
  when it is not.

## Current focus-site owner claims (not authenticated scores)

The latest message explicitly repeats the following newer-batch claims as well
as the historical maxima. They are included in
`registry/owner_reported_scores_2026-10-26.json`; none becomes an organizer receipt
merely by appearing in another site's README.

| Site | Highest listed historical owner claim | Newer listed claim / identity |
|---|---|---|
| GEMSDOE24 | 0.2477, H25-1 D1.5 | 0.0859, `gems24-gvc1-negative-geothermal-lineament-submod-20261025-abe8e51c719d-zeros` |
| GEMSDOE25 | 0.2600, D2.8 | 0.0742, `gems25-h66-mgd-flank-sapd3-0-k3p5-20261025-da617550a0e9-zeros` |
| GEMSDOE27 | 0.2449, topo-gap closure | 0.2190, `gems27-h29-hydrothermal-piedmont-celf-20261025-511898747886-allfinite` |
| GEMSDOE28 | 0.2710, H36-1 rung30 | 0.0217, `gems28-s18-mxtp-20261025-3e95505c011a-allfinite` |
| GEMSDOE30 | 0.2600, D2.8 | 0.1462, `gems30-MSDB1-edge44090-20261025-e7856ec3f14a` |
| GEMSDOE31 | 0.2708, H27-4 solo D2.8 | No newer score supplied |
| GEMSDOE32 | 0.2778, `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` | No newer score supplied |
| GEMSDOE33 | 0.2632, H33D analog tip/stepover | No newer score supplied |
| GEMSDOE36 | 0.2750, Anderson-geothermal | No newer score supplied |

The message also gives conflicting current-leader claims **0.4413** and
**0.3195**. Preserve both as unverified, not as a current leaderboard snapshot.
The full historical catalogue through GEMSDOE92 remains in the preserved brief;
this session prioritizes the nine named sites rather than claiming every artifact
from every listed site has been scientifically replayed.

## Official/manual-review starting points supplied by the owner

- [Competition and submission account](https://www.drivendata.org/competitions/306/competition-doe-gems/)
- [Problem and metric](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [About/resources](https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/)
- [Data](https://www.drivendata.org/competitions/306/competition-doe-gems/data/)
- [Leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)
- [Official reference solution](https://github.com/drivendataorg/gems-prize-reference-solution)
- [Rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf)
- [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
- [INGENIOUS project](https://gbcge.org/current-projects/ingenious/)
- [OpenEI GDR 1391](https://gdr.openei.org/submissions/1391)
- [EPSG:32611 reference](https://epsg.io/32611)

The supplied Dropbox data links and original repeated requirements remain in
the full preserved owner brief in README. This addendum is not evidence that
any of these hosts was accessed. Access status belongs in the session's source
receipt. Outbound access in this sandbox is restricted to GitHub/codeload and
package registries.
