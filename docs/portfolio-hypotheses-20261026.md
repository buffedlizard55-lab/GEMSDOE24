# Prospective-queue corrections after inspecting current peer artifacts

Session e78615fb; no geological experiment or candidate placement occurred.
This amendment corrects assumptions from `25_portfolio_plan_2026-10-26.md`
before any geological test. It is not outcome-driven model tuning.

## Corrections established from actual inputs/source

1. **Do not call scarp-polarity/graben pairing untried across the focus sites.**
   GEMSDOE36 already implemented `gps_graben_pair`, `gps_graben_pair_wide` and
   conjugate scarp-line features using `upface_max`/`downface_max` and regional
   slope. An object-topology extension may differ, but the mechanism is not
   a new lane by itself. This removes the initial first-ranked suggestion from
   the ready queue. Verified source:
   [H36-GPS preregistration](https://github.com/buffedlizard55-lab/GEMSDOE36/blob/6dae4545076c4e5fc2be1cf348fe740ba9508a1d/knowledge/h36_preregistration_2026-10-25.md)
   and [implementation](https://github.com/buffedlizard55-lab/GEMSDOE36/blob/6dae4545076c4e5fc2be1cf348fe740ba9508a1d/src/gemsdoe36/h36_features.py).
2. **Correct the specific magnetic source.** The local
   `geodawn_extensions_u8.tif` has `ThK`, `UK`, `UTh`, `TMI_up150`; it does not
   contain RTP. RTP, TMI and isostatic gravity are in the restored 19-band
   `data/training_features.tif`, with names defined by
   `src/gems/geofeatures.py`. The 30-channel prepared cache was restored and
   byte-verified. Extension values are quantized ranks, not physical units.
3. **Do not route hydrology on a detrended elevation band as if it were an
   absolute DEM.** The prepared channel is `det_elev`, not the absolute DEM
   assumed in earlier proposals. A physically interpretable drainage graph
   needs an absolute-elevation source with verified coverage. Official source:
   USGS 3DEP via the National Map. The original host is outside the sandbox's
   allowlist. A peer source claims an Actions fetch; that is not this session's
   independent availability check. The drainage idea is not ready to run here.
4. **The five-cell footprint difference was a historical count discrepancy,
   not reproduced as a current mask difference.** Directly comparing the
   committed run-length footprint to `isfinite(sample_submission.tif)` gives
   identical masks, both 5,167,373 cells, zero XOR. Some old prose says
   5,167,378; do not repeat that as a freshly measured geometric difference.
   No frozen score or historical mask was rewritten.

## Corrected ranking: unexecuted local operators, not assigned lanes

No measured improvement is claimed. Expected improvement is qualitative and
uncertain. Exact operator absence was checked against local implemented lanes;
complete global/peer method novelty is not established by filename search.
All would need their own prospective assignment, feature-by-feature canaries,
shared buffered whole-segment holdout, current-best paired comparison, surface
novelty before placement, final-dot novelty and exact-file validation.

| Rank / expected benefit / cost | Specific layers and operator | Missing-catalogue rationale / non-fault mimic | Distinction and readiness |
|---|---|---|---|
| 1 / uncertain, best benefit-to-cost hypothesis / medium-high | Raw `rtp`, `tmi`, `iso_grav_anom` plus quantized `TMI_up150`; two-sided azimuthal semivariogram changes across a front, requiring persistence across lags and modalities | A covered basement step can change texture without a high-amplitude edge. Mimic: an intrusive contact, remanence boundary or survey leveling seam. | Distribution/texture discontinuity, not an Euler derivative, scalar gradient, or extra HGB channels on a parent. Data present; physical interpretation must respect quantized support. No experiment run. |
| 2 / uncertain, lower confidence / medium | Cached K/Th/U ranks with valid masks; tangent-coherent signed spatial displacement of mobile-element fronts relative to a Th front | Alteration may be offset from lithology along a fracture missed by surface mapping. Mimic: hillslope transport and weathering. | Spatial phase lag, not CRP1/CUP1 compositional magnitude. Data present; cannot infer absolute concentrations from ranks. No experiment run. |
| 3 / uncertain / high | Raw RTP/TMI/gravity; local quadrature-filter phase congruency with cross-modality orientation agreement | A low-amplitude buried discontinuity may retain phase alignment without an exposed scarp. Mimic: dikes, caldera margins or acquisition seams. | Local phase agreement rather than already-tested cross-depth amplitude persistence. Data present; calibration/support and redundancy need testing. No experiment run. |
| Deferred / unknown / high | Absolute USGS 3DEP DEM and existing LiDAR support; directed multi-catchment channel-offset graph | Repeated wash deflection may locate subtle displacement. Mimic: fan avulsion, capture and lithologic control. | Not currently data-ready: detrended elevation is inadequate. No newly obtainable official DEM was verified in this session. |

The literal lattice is retained. Its coverage gives a mathematical obstruction
at the portfolio's usual 37,654-dot budget, so this is a **research queue, not
authorized experiments or a request to place dots in uncovered holes**. A smaller
budget is not automatically feasible, high-scoring or an escape permission.
No hypothesis was advanced to a weekly slot or turned into a fake submission.
