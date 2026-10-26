# Owner brief addendum — 2026-10-26 (summary; verbatim base brief stays in owner_brief_2026-10-25.md)

Read at every session start together with `knowledge/owner_brief_2026-10-25.md` and the README decision.

- Focus sites: GEMSDOE24, 25, 27, 28, 30, 31, 32, 33, 36. Highest owner-reported group
  artifact: GEMSDOE32 `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` (0.2778, unverified).
  Leader claims in the brief (0.3195 / 0.4413) conflict and are unverified.
- MUST generate a **unique** TIF (never copy a previous submission; learning only),
  with an unmistakable first-screen DOWNLOAD / SUBMIT state, unique filename and a
  ≤140-character portal note. Validation is automated end-to-end — no human-inspector
  fallback. Portal previously rejected a file with "Predicted values must be in range
  [0, 1]": the primary download must be strict whole-array finite [0,1] (zeros outside).
- Parallel-run protocol: single lane; duplicate if rank |ρ|>0.90 or >70% of dots within
  3 px of one registry raster (check surface + final dots); reuse shared feature stack,
  holdout evaluator and submission writer; label every number HOLDOUT-DTI or
  ORGANIZER-CONFIRMED; per-feature leakage canary (AUC>0.90 = leakage); end with one
  JSON run card; budget ≤3 experiments or 2 hours; promotion is a separate selector step.
- Preregister 3–5 untried geological hypotheses (layers, physical signature, why a
  missing-catalogue fault, difference from implemented methods, ranked by expected
  DTI/cost); validate the top candidate on the segment holdout before any slot; name a
  specific free official source before proposing anything needing new external data.
- Core values: Maximize P(Win); Own the Outcome. Verify line by line; no hallucinations;
  flag irregularities. Never automate DrivenData access; the agent never uploads.
- This session additionally: create a PR from the session branch and merge it to main;
  report remaining work and limitations for the next session.

Session outcome pointer: `knowledge/21_CUP1_findings_2026-10-26.md` (CUP1: new holdout
point best 0.15038, verdict negative — paired CI + parent-overlap gates).
