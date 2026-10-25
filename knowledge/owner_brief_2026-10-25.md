# Owner prompt — active requirements received 2026-10-25

This is an operational transcription with repetitions consolidated, not a claim of a byte-for-byte transcript of the chat. It supplements the older verbatim brief. Read this and the README at the beginning of every session. Historical numbers are owner assertions, not verified organizer receipts.

## Highest urgency

> MUST GENERATE A UNIQUE TIF SUBMISSION FOR THE COMPETITION. DO NOT COPY A PREVIOUS SUBMISSION UNLESS IT'S FOR LEARNING AND EDUCATION. BUT WE MUST GENERATE A UNIQUE TIF SUBMISSION. IT MUST BE OBVIOUS WHETHER IT IS OK TO DOWNLOAD AND SUBMIT THE GENERATED TIF SUBMISSION.

Review the repo and work on real next steps from previous sessions first. Focus on the best submissions named by the owner from **GEMSDOE24, GEMSDOE25, GEMSDOE27, GEMSDOE28, GEMSDOE30, GEMSDOE31, GEMSDOE32, GEMSDOE33 and GEMSDOE36**. Study source code and actual emitted rasters, not just method names. Generate a genuinely new prediction, not a renamed or repackaged prior prediction. A failed scientific test is still a deliverable; do not falsely mark it ready to submit.

## Parallel-run protocol (priority)

1. **LANE:** The session is one of several. Stay in the assigned single-method lane. Surface rank correlation above 0.90 with any registry raster, or more than 70% of candidate dots within 3 px of one registry raster, means duplicate: log and stop. Check before placement and on final dots. No single method paragraph was actually supplied in this message; do not silently assert an assignment.
2. **REUSE, DON'T REBUILD:** Use the template's cached feature stack and shared holdout evaluator/submission writer. Hide-and-recover must withhold whole fault segments with a buffer; derive every catalogue feature from visible faults only; mask visible faults pixel-exactly; score pooled DTI, alpha 0.2, beta 0.8, 300 m triangular kernel. Fix shared defects once in the template and report them; no private evaluator forks.
3. **NUMBER PROVENANCE:** A score is HOLDOUT-DTI (version, withheld-positive count, 95% CI) or ORGANIZER-CONFIRMED (artifact-linked submission-page receipt). A projection is never a score. Unverified owner assertions must not be forced into either verified category.
4. **LEAKAGE CANARY:** Test each feature alone on the holdout before trusting it; AUC above 0.90 means leakage until disproved. Preserve failed tests.
5. **RUN CARD:** End with one JSON card: hypothesis; mechanism; named non-fault mimic; holdout DTI and CI; registry correlation/overlap; raster SHA256; validator results (no NaN inside footprint, [0,1], CRS/shape/transform match); unique submission name and <=140-character note; verdict promote/negative. Negative results count.
6. **BUDGET:** Stop after 3 experiments or 2 hours. Do not select actual submissions: promotion to a real slot belongs to a separate selector, within the current submission-page weekly cap.

## Specific research question and evidence handling

The owner names `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` from [GEMSDOE32](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html) and reports **0.2778**. Explain what is actually known about why/how that artifact improved, and whether a higher result can be supported, with PhD-level scientific judgment. The same brief calls **0.4413** a current high score and later calls **0.3195** the current high score. These conflict; neither is a verified current leaderboard result here. Never infer an exact-file score from a team-account leaderboard row.

The owner's named nine-site results (all **UNVERIFIED-OWNER-REPORT**, no organizer receipt supplied):

| Site | Owner-named artifact | Owner assertion, not a verified score |
|---|---|---|
| [GEMSDOE24](https://buffedlizard55-lab.github.io/GEMSDOE24/) | h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan | 0.2477 |
| [GEMSDOE25](https://buffedlizard55-lab.github.io/GEMSDOE25/) | dotted-h19-5-d2-8-20261002-e56ea318af89-nan | 0.2600 |
| [GEMSDOE27](https://buffedlizard55-lab.github.io/GEMSDOE27/) | topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan | 0.2449 |
| [GEMSDOE28](https://buffedlizard55-lab.github.io/GEMSDOE28/) | h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan | 0.2710 |
| [GEMSDOE30](https://buffedlizard55-lab.github.io/GEMSDOE30/) | d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca | 0.2600 |
| [GEMSDOE31](https://buffedlizard55-lab.github.io/GEMSDOE31/docs/) | h27-4-solo-d28-20261004-8acb75e1-nan | 0.2708 |
| [GEMSDOE32](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html) | h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros | 0.2778 |
| [GEMSDOE33](https://buffedlizard55-lab.github.io/GEMSDOE33/) | h33d-analog-tip-stepover-r30-20261004-cb490425926e | 0.2632 |
| [GEMSDOE36](https://buffedlizard55-lab.github.io/GEMSDOE36/docs/) | anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros | 0.2750 |

The wider historical list is context, not authorization to reproduce those emissions or a requirement to run every past method. Evaluate the named best artifacts first. Keep unverified submissions and score claims distinct from measured local results.

## Geological discovery, hypotheses and data

Before implementation, produce 3–5 genuinely unimplemented geological hypotheses. Each names precise layers, physical transform/signature, why it might find a fault missing from USGS/INGENIOUS rather than merely repeat the catalogue, how it differs from existing work, and the non-fault mechanism that can mimic it. Rank by expected DTI benefit and implementation cost; do not fabricate numerical forecasts. Validate the top candidate on spatially blocked holdout before any weekly slot; do not spend a slot unless it beats the current comparable holdout best. If a new source is needed, identify a free official source and check obtainability before calling the idea viable.

Deep research, literature analysis and auditable source/knowledge tables should support geothermal science and reusable future projects. Be contrarian but physically grounded. Fault geometry, geothermal vents, permeability and commercially viable resources are different claims: do not conflate them. Keep official trusted links, factual verification boundaries, current feed timestamps and irregularities. Verify implementation line by line with tests; do not promise absence of every possible hallucination or pretend unread sources were read.

Resolve routine data placement and engineering autonomously. The historical instruction about GPU training being ready after data placement is a premise to audit, not proof it remains true. Use available cached official-derived inputs; do not claim downloads/training that did not happen. State network, authentication, provenance and current-best reconstruction limits. Never ask for GitHub credentials.

## Submission generation and user interface

A single-band GeoTIFF `.tif` (or `.zip` containing one GeoTIFF) must match the submission template's CRS, shape and geotransform. Values inside the footprint must be finite and in [0,1]. Preserve explicit outside-footprint encoding. Reopen the exact generated bytes, hash them and attach validator output. Address the prior portal error **“Predicted values must be in range [0, 1]”** without asserting an unverified cause. Give the artifact a unique name/content identity and a short **Note (optional)**, <=140 characters for this lane.

Make one-click TIFF download and a conspicuous download/submit status the first thing on the site and executive summary. Clean, simple GitHub Pages UI; organized research and official-source links. Create a dedicated executive-summary/submission-guide subpage. Scientific inspection/gates must be automated through the project; an opaque “ask a human inspector” must not stand in for validation. A failed gate must visibly block authorization, not hide behind a format-green badge. Actual weekly selection is separate, and the project does not auto-upload.

## Official and data links to retain for review

- [Competition](https://www.drivendata.org/competitions/306/competition-doe-gems/), [problem/metric](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/), [about/resources](https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/), [data](https://www.drivendata.org/competitions/306/competition-doe-gems/data/), [leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/).
- [Organizer reference solution](https://github.com/drivendataorg/gems-prize-reference-solution).
- [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and), [INGENIOUS](https://gbcge.org/current-projects/ingenious/), [GDR 1391](https://gdr.openei.org/submissions/1391).
- [Prize rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf); [EPSG:32611](https://epsg.io/32611); [Tversky background](https://en.wikipedia.org/wiki/Tversky_index) (background, not organizer authority).
- Owner-supplied Dropbox mirrors: [rules](https://www.dropbox.com/scl/fi/aemhtutjgcp6tr3tint94/GEMS_96647.pdf?rlkey=rek210cj2smnmzb8n0sla1vmd&st=wz4kofki&dl=0), [template](https://www.dropbox.com/scl/fi/6rgvnuady818ol8yqgis4/example_submission.tif?rlkey=kbykilvau066xuogoosbf4cq8&st=8junzdyw&dl=0), [existing faults](https://www.dropbox.com/scl/fi/t7fyt03qdh9egyme0itwo/existing_faults.tif?rlkey=yiao96uluqdkipf0h5vju71jf&st=rnino7ya&dl=0), [features](https://www.dropbox.com/scl/fi/3vz9o0wwavi26xaeoxlwr/gems-geodawn-numerical-features.tif?rlkey=je8d8fepqfbst9lnwsq9rkplu&st=zj1lag1r&dl=0), [DEM links PDF](https://www.dropbox.com/scl/fi/ig0mban712ns1atphgphe/Digital-elevation-model-links-JSON.pdf?rlkey=zm77f1vbtt2if8hlruymptnu3&st=srhhir10&dl=0). Mirrors are not independent organizer provenance.

Existing repository policy prohibits automated DrivenData access, including leaderboard scraping. Do not bypass it or silently claim a continuously updated leaderboard. An automated official-source health snapshot is not a live competition feed.

## Core values and delivery

**Maximize P(Win):** weigh risk, tradeoffs and evidence, not comfortable busywork or cosmetic submission fishing. **Own the Outcome:** resolve problems within available authority, retain failures, preserve reproducibility and report genuine limitations.

Work autonomously, through **three passes**: implement/verify; review bugs, edge cases and assumptions and fix them; recheck against original acceptance criteria and improve quality. Do not stop after the first pass. Provide the full requirement status and future work. Open a pull request from the session branch and merge it onto main if checks and permissions permit. Never claim a PR, merge or deployment without evidence. Do not change another parallel session's branch or merge its conflicting work by overwrite.
