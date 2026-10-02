# AI-assisted development disclosure (starting draft for the prize narrative)

The official rules ([§3.2](https://docs.nlr.gov/docs/fy26osti/96647.pdf)) allow generative AI but require the
narrative to state **the extent to which it was used and how**. This file is the factual starting point; the
competitor remains responsible for accuracy, authenticity and authorship representations.

* **Tooling.** Arena.ai Agent Mode (several large language models) working in a sandboxed checkout of this repository,
  with read access to the owner's public sibling repositories and to public web pages. It cannot sign in to DrivenData and
  never uploads a submission; the owner performs every upload.
* **What the AI did in this repository.** Wrote and ran essentially all code under `src/`, `scripts/` and `tests/`, built the
  GitHub Pages site and the evidence/registry files, designed and executed the frozen experiments and audits, and wrote the
  knowledge documents. Earlier sessions on the same branch were also AI-assisted; their work was merged unchanged.
* **What humans did.** The owner wrote the brief, supplied the competition files through their own mirrors, ran the sibling
  projects whose rasters and scores are analysed here, and decides which file (if any) to submit.
* **Where AI judgement is most likely to be wrong.** (1) Calibration and extrapolation rest on two scores that appear only in
  the brief (`registry/live_scores.json`, `task_statement_only`); (2) the "model score" for the new files is a first-order model,
  not a measurement; (3) block membership is derived from an official figure, not published coordinates; (4) the cause of the
  original portal error is unknown. Each is flagged where it is used (`registry/irregularities.json`).
* **How claims are checked.** Frozen preregistrations committed before runs (`knowledge/04_*`), bit-exact evaluator tests, an
  independent plain-rasterio verifier for every shipped file, hash-pinned inputs, and a rule that unknowns stay unknown.
* **Data.** Only the competition files supplied by the owner and public/official sources named in `docs/data/sources.json`
  (USGS ScienceBase/3DEP, U.S. Census TIGER, BLM, DOE GDR). Check each licence before the narrative and confirm that any external
  data can be shared with the sponsor, as the rules require.
