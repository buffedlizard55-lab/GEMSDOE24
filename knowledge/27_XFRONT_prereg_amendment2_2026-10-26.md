# Preregistration amendment #2 — H24-XFRONT ablation arm and arm-selection rule (filed **before** any endpoint) — 2026-10-26

Amends `knowledge/25_preregistered_XFRONT_2026-10-26.md` (`3ebb375`) and
amendment #1 (`knowledge/26_XFRONT_prereg_amendment_2026-10-26.md`).
Filed after the **leakage canary only** — a leakage diagnostic, which reports
per-feature AUC against withheld truth and is explicitly *not* a DTI, not a
promotion statistic and not the lane endpoint. **No holdout DTI, no novelty
result and no emitted raster existed when this amendment was written.**

## A5. Two pre-specified arms

| Arm | Score | Meaning |
|---|---|---|
| **A — `XFRONT`** (primary) | `C · E_R` on `Σw ≥ 2` | corroboration × excess orientation coherence over the rotation null |
| **B — `XFRONT-C`** (pre-specified ablation) | `C` on the identical `Σw ≥ 2` eligible set | corroboration magnitude alone; drops the orientation-null factor |

Arm B is a **mechanism control**, not a fallback: it is the only way to
attribute a lane result to the corroboration term or to the null term. Both
arms share the identical eligible set, emission operator, spacing, clearance,
budget grid and evaluation code.

## A6. Arm selection rule (extends §3.4, same statistic)

The preregistered selection statistic — **mean over the four folds of the
sparse-simulated DTI** — now selects the pair `(arm, budget)` over
`{A, B} × {15 000, 20 000, 25 000, 30 000, 37 654, 45 000}`; ties break to the
smaller budget, then to arm A. The **dense** HOLDOUT-DTI is then reported for
the selected pair and for every other pair, and is never used for selection.
This matches the repo's standing rule that emission/thinning policy must be
judged on the density-matched simulation rather than on the dense catalogue
(`AGENTS.md`, "dense-catalogue holdout is a different regime").

## A7. Why this is not post-hoc tuning

Nothing observed so far is an endpoint: the canary AUC is a leakage screen with
a fixed 0.90 threshold, and both arms were constructible before it ran (arm B
is arm A minus one factor). The rule in A6 is written before either DTI series
exists. No arm, budget, spacing, clearance, seed, scale or modality is changed
after the run.

## A8. Paired comparison for the run card

`paired_vs_baseline` = arm A vs. arm B at the selected budget (same evaluator,
same folds, paired 10 km block bootstrap). `paired_vs_current_best` is recorded
with `baseline_replayed = False`: replaying `H24-DPRF1`'s 52-channel
dual-partition stitched-OOF model is out of this session's compute budget, and
the selector must therefore fail G3 rather than be given a fabricated replay.
