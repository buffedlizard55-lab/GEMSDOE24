# Pre-training feasibility: fresh raster readback, not a new submission

**DOWNLOAD: research only · SUBMIT: NO.** The requested high-scoring unique
GeoTIFF has **not** been achieved. No geological lane was chosen, no prediction
surface or TIFF was generated, no new holdout was evaluated and no slot was used.

[Executive nine-site table](executive-summary.html#current-focus-files) ·
[Feasibility page](submission-readiness.html) ·
[Fresh geometric receipt](data/uniqueness_feasibility_20261027.json).

## Finding and implementation

The prior review's lattice argument was remeasured from the exact template and
registered reference raster. The new command checks file SHA-256, reference
in-footprint content SHA-256, single-band alignment (CRS, shape, transform),
nonempty finite footprint and finite reference values in [0,1]. It then uses
the existing shared `classify_space_filling_control` inclusive 3-pixel union.
The reference is retained in the registry; no calibration exemption is added.

There are 5,167,373 footprint pixels and only 6,649 uncovered pixels. For K
**distinct in-footprint** positive cells, the minimum overlap with this reference
is `max(0, K - 6649) / K`. This is a necessary geometric bound, not HOLDOUT-DTI,
not an organizer score, not a score projection and not proof of copied geology.

| Diagnostic dot budget | Lower overlap bound | Result of this one necessary gate |
|---:|---:|---|
| 20,000 | 66.7550% | Not ruled out; NOT PASS |
| 22,163 | 69.9995% | Not ruled out; NOT PASS |
| 22,164 | 70.0009% | STOP: impossible |
| 37,654 | 82.3418% | STOP: impossible |
| 44,090 | 84.9195% | STOP: impossible |

The boundary is checked exactly, not using rounded percentages. These are
arithmetic diagnostics, **not experiments searching for a permissible budget**.
Do not alter a stopped lane's budget or place dots in lattice holes to evade
the rule. A smaller candidate can still fail actual overlap, rank correlation,
leakage, bias, comparative holdout, replay, or quota gates. A single decisive
witness proves failure but cannot certify a full registry pass.

```sh
python scripts/check_uniqueness_feasibility.py \
  --dot-budget 37654 --dot-budget 44090
```

Exit 2 means an impossible requested budget; exit 0 means only not ruled out.
Malformed, missing or changed evidence raises an error. The new check is a
pre-training command and shared API, **not a claim that every historical runner
has been retrofitted**. Stopped runners remain stopped.

## Concurrent-work integration

While this work was in progress, PR #67 merged an arithmetic-only check over
frozen audit counts. Its evidence is preserved. Rather than keep two formulas,
`scripts/check_protocol_feasibility.py` and the fresh raster checker now share
`gems.uniqueness_budget.bounds`, a standard-library-only exact-rational core.
The old command remains usable without NumPy. The fresh command adds raster
remeasurement, content/grid checks, multi-budget diagnostics and explicit stop
exit status. Neither can authorize a slot. Invalid booleans, floats and
non-rational thresholds now fail closed in the shared core.

## Scientific queue: ranked before implementation, not assigned

The existing three unexecuted hypotheses are retained rather than relabelled
as new discoveries. No global cross-repository novelty claim is made. Their
qualitative ordering is a research priority, **not an estimated DTI gain**.

| Rank | Specific inputs and signature | Why it might reveal a missing fault; difference from implemented work | Named non-fault mimic | Expected benefit / cost |
|---|---|---|---|---|
| 1 | `rtp`, `iso_grav_anom`, `det_elev`: signed gravity–magnetic cross-gradient orientation reversal along an independently derived terrain tangent | A buried splay could change the relative field orientation even without a mapped surface trace. Unlike unsigned topo–magnetic TMCG or GVC1/EUL1 magnitude/co-alignment | Intrusive contacts, remanence and acquisition seams | Highest qualitative information per cost; unknown DTI; medium CPU/memory |
| 2 | Cached GeoDAWN K/Th/U ranks: training-fold conditional K-rank residual and cross-normal residual front with low Th/U-rank change | Alteration along a concealed permeable branch might differ from parent-lithology trends. Unlike CRP1 rank fronts or SAHG1 fixed contrasts, this conditions the residual | Arkosic sorting, moisture and weathering boundaries | Second; unknown DTI; medium cost; quantized ranks do not establish chemistry |
| 3 | `det_elev`, `det_local_relief`, `depth_to_base_surf`, `geod_dilaterate`, `geod_shearrate`: separated, oppositely signed terrain-curvature lobes around a basement step | Broad bending could survive above a buried fault with no crisp scarp. Unlike RSHG1 pointwise Hessians and CON conductivity saddles | Terrace–valley pairs, dunes and alluvial fan curvature | Third; unknown DTI; medium cost; coarse grids limit localization |

The top idea is **not tested**: the operative request still lacks its promised
single-method lane paragraph, and the literal novelty policy blocks the common
budgets independently of geology. Do not infer a holdout result from a rationale.
All input descriptions inherit the existing cache provenance caveats; this
session fetched no new official geological dataset or claimed it obtainable.
Any eventual test must preregister a lane and budget, restore/hash-verify shared
caches, canary every actual feature, derive catalogue features only from visible
segments, run the shared buffered hide-and-recover evaluator, compare to the
comparable best with paired uncertainty, and check full pre-placement and final
novelty. Fault recovery is not geothermal-vent confirmation.

## B2, score estimates and download status

The previous exact-mask ancestry audit supports deletion-only emission for B2,
not a new independently learned geological surface. Reduced false-positive mass
could improve DTI **only if** removed true-positive credit is sufficiently low;
hidden labels are unavailable. The owner-reported 0.2778 is not artifact-linked
ORGANIZER-CONFIRMED evidence. No defensible numeric leaderboard estimate or
promise of beating it follows. See the [metric-integrity analysis](metric-integrity-20261026.md).
The prompt's 0.3195 and 0.4413 leader claims are conflicting unverified snapshots.

The existing executive table preserves one exact source-featured research file
per focus site, and distinguishes those files from the owner's historical
highest claims. All nine selected files fail the retained lattice comparator;
none is a new-slot recommendation. This continuation's source feed refresh is
**commit freshness only**, not a new raster census or scientific replay.

For the reported [0,1] rejection, use the existing shared writer/validator and
strict whole-array finite-range check. Exterior NaNs can fail a strict portal
check, but no authenticated error trace was fetched here and NaN is not proven
to be the sole cause. Grid/range validity never overrides scientific eligibility.

## Source verification and access

Freshly read through GitHub API only:

- [Organizer reference README at aebe92f](https://github.com/drivendataorg/gems-prize-reference-solution/blob/aebe92f7c8a990f0e3443451b7a825d9afd6336b/README.md):
  instructs data placement in `data/` and provides CPU-only as well as GPU paths.
  [Read receipt](../evidence/official_reference_review_20261027.json).
- Nine GitHub main-commit refs, timestamped in [portfolio freshness](data/portfolio_freshness.json).
  This does not verify their new predictions or scores. Registry/audit pins stay immutable.

Reference links retained for manual review, **not fetched this session**:
[competition problem](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/),
[data](https://www.drivendata.org/competitions/306/competition-doe-gems/data/),
[GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and),
[INGENIOUS GDR 1391](https://gdr.openei.org/submissions/1391),
[rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf).
This sandbox permits GitHub and package registries, not unrestricted official
source downloads. No DrivenData login, leaderboard, weekly quota, acceptance or
score receipt was retrieved. No credentials or human inspection were requested.

## Three-pass verification and follow-up

1. Implement the shared necessary bound, fresh hash/grid/content readback CLI,
   JSON receipt and first-screen site link. Preserve all historical TIFF bytes.
2. Exhaustively verify the bound over all covered sets and candidate subsets of
   a six-pixel footprint; test strict 70% equality, actual budget boundary,
   invalid types/counts, changed/missing hashes and comparator paths, CLI exit
   semantics, HTML escaping and negative-only authorization.
3. Rebuild site; run full tests, lint, format and compile/diff checks. Final
   outcomes are recorded in the session card, not inferred from historical runs.

**Next actions:** coordination must provide the single method paragraph and
prospectively resolve the space-filling-control policy; no unilateral exemption.
Then refresh/replay relevant peer artifacts, restore authenticated/pinned caches,
preregister one feasible lane and run the shared scientific gates. A separate
selector must require actual account allowance before promotion. Do not spend a
weekly slot on the current artifacts. The high-scoring unique-TIFF goal remains
unfinished; repeated audit-only continuations are not scientific progress toward
that goal unless the coordination/data blockers are resolved.


### Final verification outcomes

**510 pytest tests passed** after integration; six dependency-free unittest tests
also passed. Ruff check and format, compileall, JavaScript syntax and diff checks
passed. The shared Chromium audit checked **14 desktop/mobile page combinations**,
including both versions of the executive guide, exact research-TIFF download
hashes, clipboard notes, all nine table rows, and the new readiness page. Final
receipt: **zero detected accessibility violations**, no page errors and no page
horizontal overflow. These local checks are not a claim of remote Pages deployment
or organizer acceptance.

Pass 2 caught a concurrently merged root-link regression and focusability of
mobile horizontal-scroll regions; both were fixed and retested. No raster bytes
were changed. The session card is deliberately a non-experimental review receipt,
not entered into the scientific run-card/point-best inventory:
[JSON card](https://github.com/buffedlizard55-lab/GEMSDOE24/blob/main/evidence/uniqueness_feasibility_review_20261027.json).
