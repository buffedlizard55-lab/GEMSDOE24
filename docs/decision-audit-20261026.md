# Nine-site decision audit — 2026-10-26

## Outcome

**No new experiment. No new TIFF. No submission slot consumed. No approved submission.**
The requested newly generated, unique, high-performing submission remains unachieved.
The [executive table](executive-summary.html#nine-site-download-decisions) now directly
answers file availability, local evidence, leaderboard estimate, uniqueness and
SUBMIT YES/NO for all nine requested sites. [JSON packet](data/nine_site_download_decisions.json).
Only the already-existing DPRF1 research file is recommended for research download;
this does not claim it is the best submission across the nine sites.

### What was verified

- Shared read-only current-best review revalidated the exact DPRF1 SHA-256 and
  template grid through the shared selector/writer tools, without training.
- Recorded **HOLDOUT-DTI 0.16379**, 95% CI **[0.15045, 0.17739]**,
  evaluator `gems-segment-pooled-v1`, **60,988 withheld positive pixels**.
  Scientific training and bootstrap were **not** independently replayed.
- Literal all-entry final-dot overlap is recorded as **99.56%**, above the
  protocol's 70% stop threshold. Competing-method-only novelty is not the literal gate.
- Exact-file format checks pass: single band, no NaN/Inf inside footprint,
  values in [0,1], CRS/shape/transform match. Zero-filled outside differs from the
  inherited sample's NaN-outside convention: `official_format_compliant=false`.
  Format validity is not organizer acceptance or scientific authorization.
- Refreshed all nine GitHub source tips: all checks succeeded and all differ
  from frozen registry pins. Source freshness is not a fresh TIFF/score audit.
- Organizer reference repository main remains
  [`aebe92f7c8a990f0e3443451b7a825d9afd6336b`](https://github.com/drivendataorg/gems-prize-reference-solution/tree/aebe92f7c8a990f0e3443451b7a825d9afd6336b).
  This is code provenance, not a score receipt.

### H33-B2 explanation and estimate limitations

The inherited pixel comparison describes B2 as a subset removing near-catalogue
predictions, not new vent discovery. Under asymmetric distance-weighted Tversky,
removing low-credit false positives may improve the precision/recall tradeoff.
Hidden labels are unavailable: the causal explanation remains plausible, not
proved. The owner's historical result is UNVERIFIED-OWNER-REPORT, not an
ORGANIZER-CONFIRMED receipt. No validated mapping exists from this local holdout
to a hidden leaderboard result; a numerical forecast would be invented.
The prompt also supplies conflicting current-leader claims.

## Prospective scientific queue (not authorized or executed)

The prior review already ranked three candidate operators in
[the research queue](review-20261026.md#prospective-hypotheses--not-assigned-lanes-not-executed).
Do not relabel them as new experiments:

1. **Paired opposite-facing LiDAR strips** (`upface_max`, `downface_max`, `strike`,
   `coh100`, `relief`): object-level persistent width/end alignment could detect
   narrow, weakly mapped grabens; fluvial terraces and irrigation banks mimic it.
   Medium cost, highest qualitative incremental-benefit priority, not a score projection.
   Unlike pointwise SAHG1 or OJ1 junctions. Cached quantization/facing-information
   feasibility must be checked before trusting this operator.
2. **Signed radiometric-front displacement** (cached K/Th/U ranks): multi-width
   phase lag, not CRP1's compositional gradient, could expose alteration displaced
   from a lithologic front along a concealed permeable fracture. Downslope sediment
   transport/weathering mimic it. Medium cost, uncertain incremental benefit.
   Quantized ranks do not establish absolute chemistry.
3. **Directed multi-catchment drainage offsets** (DEM and derived drainage graph):
   coherent channel-bearing offsets might expose faults lacking continuous scarps.
   Stream capture, lithology and fan avulsion mimic it. High cost; not ready until
   exact DEM/cache is restored. Different from existing pointwise Hessian/knickpoint
   features. A finer-resolution upgrade would need official USGS 3DEP; its host is
   outside this sandbox's allowlist, so external availability is not newly verified.

No single-method lane paragraph is supplied. Prior lanes are explicitly stopped.
No experiments were run rather than silently assigning a lane or bypassing a
known stop condition. These hypotheses must face per-feature leakage canaries,
whole-segment buffered spatial holdout, paired comparison to the comparable current
best, and pre-placement/final registry checks before any promotion.

## Three passes

1. **Implementation:** read README, AGENTS, owner briefs, prior continuation,
   evaluator/writer/selector interfaces and current-best packet. Added a generated
   nine-site decision packet and accessible, horizontally scrollable table near
   the top of the overview and executive pages. No copied predictions or new data fork.
2. **Adversarial review:** tests reject unsafe filenames, changed raster hashes,
   malformed historical claims, omitted sites and positive authorization inputs.
   HTML is escaped. Removed an obsolete README VENT scientific-PASS claim; the
   integrity quarantine remains binding. Initial full-suite failures were missing
   source-history objects in the shallow checkout; `git fetch --unshallow origin`
   restored provenance without weakening a test.
3. **Final verification:** full suite, Ruff lint/format, compileall and diff checks;
   generated pages tested for all nine rows, no forecast and negative status.
   The final session card records exact verification results. No claim of a fresh
   browser audit or complete scientific replay.

## Next steps and access limits

1. Project coordination must supply the missing single-method lane and prospectively
   resolve the near-universal lattice-overlap blocker without rewriting old results.
2. Refresh artifact-level registry for changed peers, retaining immutable old pins.
3. Restore/hash-verify exact feature caches, preregister one eligible operator,
   canary every actual feature, and evaluate against current comparable best.
4. Implement independent replay-certificate verification and a legitimate account
   quota receipt adapter; manual confirmation is not a substitute.

Only GitHub and package registries are network-accessible here. Current DrivenData
leaderboard, authenticated data, weekly quota and submission receipts were not
retrieved. Official links retained for review—not claimed freshly read:
[problem](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/),
[USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and),
[INGENIOUS GDR](https://gdr.openei.org/submissions/1391),
[rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf).
The existing CPU pipeline disproves the inherited blanket claim that a GPU is
required for every training path. Neither high leaderboard performance nor geothermal
vent discovery is established by these cached proxy tests.

[Final JSON run card](data/decision_audit_run_card_20261026.json): 386 tests passed after integrating concurrent PRs #38 and #39; Ruff lint/format, compileall and diff checks passed.

Concurrent PR #38 wording corrections were preserved. A verification-only card was renamed outside the experimental `*run_card*.json` inventory after rechecking that it must not appear as a new scientific point-best. The final build resolves DPRF1 again; full tests passed after the correction.

Concurrent PR #39 metric-integrity corrections and tests were also preserved and the combined site rebuilt and retested.
