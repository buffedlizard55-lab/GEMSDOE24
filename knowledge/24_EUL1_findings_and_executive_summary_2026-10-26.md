# H24-EUL1 Findings & Updated Executive Summary (2026-10-26) — Euler increment is negative; DPRF1 remains the one obvious candidate

- **Lane:** `H24-EUL1` Euler-deconvolution (N=0 contact) channels on the DPRF1 stitched-OOF stack
- **Preregistration:** [`22_preregistered_EUL1_2026-10-26.md`](22_preregistered_EUL1_2026-10-26.md) @ `b841bf4d7c3227ccb126ed3acfa74ecbb1d2d217`; pre-fit metrology amendment [`23_EUL1_prereg_amendment_2026-10-26.md`](23_EUL1_prereg_amendment_2026-10-26.md)
- **New unique TIF generated this session:** `docs/downloads/gems24-eul1-negative-euler-contact-20261026-eda170f04847-zeros.tif`
  SHA-256 `4a65a49914bbd93107e429d06e316f35f3f1d04b957b8f8af12a0d952c28708a` · 37,654 dots · strict whole-array `[0,1]` PASS
- **Verdict: NEGATIVE — DOWNLOAD: YES · SUBMIT: NO.** Zero slots spent. Zero human-inspector fallback.

---

## 0. The obvious answer first (what to submit, per site)

**The single best unscored unique file across all nine focus sites remains DPRF1**, generated
2026-10-26 in this repo and *replayed bit-identically inside this EUL1 session*
(Arm-2 pooled HOLDOUT-DTI `0.1637924246971501` and CI `[0.15044621733051888, 0.1773903019943756]`
match the recorded card to the last digit):

> **File:** `gems24-dprf1-stitched-oof-tworegime-20261026-81849d67c8bf-zeros.tif`
> **SHA-256:** `c1257c1d4b5ac9cc0a8e29b0120c614fcaa1f38474bc1f6de98c0a1afb0567f1`
> **Note (≤140 chars):** `GEMS24 DPRF1 | 52ch stitched-OOF 2-regime submod | id 81849d67c8bf | HOLDOUT-DTI 0.16379 | research; DO NOT SUBMIT`
> **Status today: DOWNLOAD YES · SUBMIT NO** — not because of any science gate (10/10 competing-method
> technical gates PASS), but because the separate selector step has not authorized a slot:
> live DrivenData weekly quota is unknown from the sandbox, the literal registry retains the
> synthetic spacing-5 lattice (`registry-039`), and no independent replay certificate exists.
> **If you override that governance hold manually, this — and only this — is the file the local
> evidence supports.** Every other unscored file in the portfolio is locally worse, and every
> already-scored file would waste a slot re-measuring a known number.

**EUL1 (today's new file) must not be submitted**: it is worse than DPRF1 on the preregistered
holdout (`0.16005` vs `0.16379`, paired Δ `−0.00375`) *and* 86.57% of its dots lie within 3 px
of DPRF1's dots, so it is a duplicate lane under Rule 1. It is a valid-format research download
and a clean negative measurement. Per-site verdicts are in §5.

## 1. Why did `GEMSDOE32 h33-h33-2-b2` get 0.2778, and can we beat it? (PhD-level answer, evidence-bounded)

**Provenance discipline:** `0.2778` — like the conflicting `0.3195` / `0.4413` "current leader"
figures in the brief — is **UNVERIFIED-OWNER-REPORT**. No artifact-linked DrivenData receipt is in
git, so it is never called ORGANIZER-CONFIRMED here, and no number in this document is a score
forecast.

**What is geometrically proven** (`knowledge/14_h33_analysis_2026-10-25.md`, peer forensics):
B2 (37,654 dots) = `D2.8` (44,090 Poisson-thinned `H19-5` dots) with all 6,436 dots at catalogue
distance ≤200 m deleted and **zero dots added**. So B2 contains no new geological detections
relative to its parent. Under the distance-weighted Tversky
`DTI = T / (T + 0.2F + 0.8N)` form (α=0.2 FP weight, β=0.8 FN weight, 300 m triangular credit),
deleting contribution `(t, f)` improves the score iff `t·(0.2F + 0.8N) < 0.2·T·f`. B2's deleted
near-catalogue belt is precisely where a thinned ridge surface carries the worst ratio of that
kind: dots there mostly duplicate 300 m credit already delivered by neighbours while adding FP
mass next to *already-masked* known faults, whereas the retained far-field dots
(49.2% at `>2 km`, vs 55.1% of footprint) buy unique credit on unmapped segments. Sparse
(≈2.8 px), catalogue-cleared (`>2 px`), far-field-tilted emission is therefore the transferable
lesson — and it is fully baked into DPRF1/EUL1's allocator (37,654 dots, 0% ≤2 px, 52.3–52.4%
`>2 km`). **That geometry is now saturated**: every post-B2 portfolio gain must come from a
better *detector surface*, i.e. finding fault pixels the `H19-5` parent never ranked highly.

**Why most 2026-10-25 unique attempts scored badly live despite good holdouts** is also proven
here: in-sample refits with a ≥900 m negative dead-zone memorised 200–900 m aprons around the
catalogue (GVC1: holdout 0.14876 → owner-reported live 0.0859, 70.4% apron dots). DPRF1's
stitched-OOF + stratified negatives + apron debiasing is the structural cure, which is why it —
not any B2 copy — is the correct champion to carry forward.

**Can a unique submission beat 0.2778?** Honest answer: *possible, unproven, and not claimable
today.* HOLDOUT-DTI hides *mapped* segments (dense regime); the leaderboard hides *unmapped*
faults (sparse regime, ~0.24% density by lattice calibration vs ~1.18% mapped). The two are
correlated through detector quality but not interchangeable, so no local number licenses a
">0.2778" claim. The decision-grade procedure is exactly what this session executed: beat the
current holdout point-best in a *paired* same-evaluator test while passing novelty, then let one
authorized slot produce an ORGANIZER-CONFIRMED calibration receipt. EUL1 failed that test;
DPRF1 has passed every local test and awaits only the selector/quota step.

## 2. What EUL1 did (one lane, 3 locked arms)

Euler deconvolution solves, in every 7×7 px window, the homogeneity system
`x0·Fx + y0·Fy + z0·Fz = u·Fx + v·Fy` at structural index N=0 (vertical contact; Thompson 1982,
Reid 1990). Accepted tight solutions (depth 50–1500 m, in-window, rel. residual <0.15) were
accumulated into density/depth/quality channels for RTP and gravity, plus a gravity×magnetic
cross-gradient co-alignment and the solution-density lineament — 7 label-free channels on top of
DPRF1's 52, with the concealed Regime-B multiplier gated by the Euler densities. Pre-fit band
forensics (amendment A1) replaced the inconsistent survey `*_vg` bands with self-consistent FFT
`|k|` vertical derivatives (`tmi_vg` is really ∂(`tmi`)×0.00990/px, corr 0.9965;
`iso_grav_anom_vg` is not ∂(`iso_grav_anom`) at all, corr −0.19 on the builder crop / −0.01 on
the exploratory crop). Full-grid solution census: RTP 47,322 accepted (0.92% of valid windows,
median depth 477 m, **100% signed depths below the plane** — a strong convention sanity check),
gravity 5,601 (0.11%, median 1,100 m).

## 3. Results (all HOLDOUT-DTI, `gems-segment-pooled-v1`, 60,988 withheld positives)

| Arm | Pooled DTI | 95% CI | NW | NE-LidarGap | SW | SE |
|---|---:|---|---:|---:|---:|---:|
| **Arm 1 EUL1-primary (59ch + Euler Regime-B)** | **0.16005** | [0.14729, 0.17278] | 0.15439 | 0.20509 | 0.12330 | 0.17165 |
| Arm 3 channels-only (59ch, legacy Regime-B) | 0.15989 | [0.14691, 0.17302] | 0.15369 | 0.20501 | 0.12415 | 0.17062 |
| Arm 2 no-Euler replay (= DPRF1, bit-identical) | **0.16379** | [0.15045, 0.17739] | 0.15425 | 0.21227 | 0.12768 | 0.17442 |

Paired 10 km block-bootstrap (1,999 draws):
- Arm1 − Arm2 (total Euler effect): **−0.00375**, 95% CI [−0.00825, +0.00074], **1/4 folds won**
- Arm3 − Arm2 (channel effect): **−0.00390**, 95% CI [−0.00819, +0.00021], **0/4 folds won**
- Arm1 − Arm3 (Regime-B Euler gating): +0.00015, 95% CI [−0.00108, +0.00144], 3/4 folds (null)

Gates: 59/59 leakage canaries PASS (Euler solo pooled AUCs only 0.502–0.529 — weak marginal
signal, no leakage); pre-placement surface novelty PASS (max |ρ| 0.543 vs 59 competing methods,
0.176 vs 83 peers); **final-dot novelty FAIL — 86.57% of dots within 3 px of DPRF1** (next
highest: 55.7%; peers 55.2%); exact-file C2ST PASS (AUC 0.5184, Holm p=0.260); strict `[0,1]`
format PASS; distance profile healthy (0% ≤2 px, 22.2% apron, 52.4% far-field). Selector v2:
`DO_NOT_SUBMIT` (G3 holdout, G4 novelty, quota, replay certificate).

## 4. Interpretation — why Euler did not add (and the portfolio-level lesson)

1. **Redundancy.** The stack already contains the same basement-step information in smoother
   form (Miller–Singh tilt gradients, `gvc_basement_step_grad`, `sahg_b_step`, 2 km grav–mag
   co-alignment). Euler re-encodes it as sparse, high-variance point solutions; the trees spend
   splits on it and lose a little everywhere (0/4 folds for channels alone) — classical feature
   dilution with a correlated, noisier view of the same physics.
2. **Scale mismatch.** Classical Euler works on upward-continued, smoothed grids with windows
   matched to source depth; at raw 100 m sampling, 98% of windows are not single-contact
   dominated (rel. residual ≥0.15), and accepted clusters include the named mimic — unfaulted
   pluton/hornfels contacts and magnetite paleochannels — which the supervised model cannot
   fully discount because the same channels help slightly in NW.
3. **Gravity Euler is nearly empty** (5,601 solutions, 1.1 km median depth): the isostatic
   field is too long-wavelength for 700 m windows. It contributed mostly missingness patterns.
4. **Lane-uniqueness is now the binding constraint.** CUP1 ended 91.2% on top of its GVC1
   parent; EUL1 ends 86.6% on top of DPRF1. Incremental channels on a strong parent cannot
   clear the 70% Rule-1 ceiling, because a good surface + the same 300 m allocator necessarily
   re-selects the same ridge lattice. DPRF1 itself passed at 55.8% only because it changed the
   *training geometry* (negatives, calibration, regimes, stitched-OOF) relative to *its*
   predecessors. Future lanes must change where dots can go — different target definition,
   allocator, or evidence geometry — not merely append features.

This does **not** disprove Euler deconvolution for Great Basin basement mapping; it rejects
*this preregistered configuration as an increment to this stack*, consistent with sibling
standalone Euler lanes (owner-reported 0.036–0.098 in GEMSDOE40). Do not retune it.

## 5. Nine-site executive summary (updated; scores UNVERIFIED-OWNER-REPORT unless stated)

Receipt: [`evidence/nine_site_executive_summary_eul1_20261026.json`](../evidence/nine_site_executive_summary_eul1_20261026.json)
(supersedes the DPRF1 receipt, which is kept unmodified). All eight sibling artifacts were
re-fetched this session at their pinned commits and verified byte-identical to the recorded
SHA-256 values before any overlap was recomputed.

| Site | Historical best (owner-reported) | Latest unique artifact examined | Status | EUL1 3-px overlap | Obvious verdict |
|---|---|---|---|---:|---|
| **GEMSDOE24** | `h25-1-dotted-h19-5-d1-5` 0.2477 | **DPRF1** `…81849d67c8bf-zeros` HOLDOUT-DTI **0.16379**; EUL1 0.16005 (negative) | DPRF1 unscored; EUL1 unscored | 86.6% vs DPRF1 | **#1 candidate portfolio-wide = DPRF1 file above (selector step pending). DO NOT SUBMIT EUL1.** |
| GEMSDOE25 | `dotted-h19-5-d2-8` 0.2600 | `h66-mgd…da617550a0e9` scored 0.0742 | already scored | 30.4% | DO NOT RESUBMIT (apron collapse) |
| GEMSDOE27 | `topo-gap-closure…d1-5` 0.2449 | `h29-…celf…511898747886` scored **0.2190** | already scored | 45.2% | Best already-scored 2026-10-25 unique method; do not duplicate |
| GEMSDOE28 | `h36-1-rung30-blind-r1` 0.2710 | `s18-mxtp…3e95505c011a` scored 0.0217 | already scored, holdout FAIL | 5.7% | DO NOT SUBMIT |
| GEMSDOE30 | `d28-poisson300m…44090` 0.2600 | `MSDB1…e7856ec3f14a` scored 0.1462 | already scored | 40.7% | DO NOT RESUBMIT |
| GEMSDOE31 | `h27-4-solo-d28` 0.2708 | `h31-hvdc…43714168` unscored, own holdout PASS | unscored sibling | 34.9% | Secondary unscored sibling; locally weaker apron profile than DPRF1 |
| GEMSDOE32 | **`h33-h33-2-b2` 0.2778** | `h-geo-conduit…2d0d0c5e` unscored, repo says DO NOT SUBMIT | B2 prohibited copy | 29.4% | DO NOT SUBMIT; B2 is a reference, never a resubmission |
| GEMSDOE33 | `h33d-analog…r30` 0.2632 | `a33-l1…85c94a805a34` unscored, own holdout FAIL | negative | 27.7% | DO NOT SUBMIT |
| GEMSDOE36 | `anderson…pinn-38854` 0.2750 | none valid (legacy copied/leaky retired) | no candidate | 45.7% (vs PINN artifact) | DO NOT SUBMIT |

## 6. Next steps (ranked by P(Win); no further experiments this session — budget spent)

1. **Selector step for DPRF1** (separate from any lane): record the live DrivenData weekly-quota
   state from the submission page into a dated receipt, prospectively separate the synthetic
   spacing-5 calibration lattice from competing methods in the selector policy, and implement
   the independent replay certificate. Until then every file in the portfolio is correctly
   `SUBMIT: NO`. If authorized, submit DPRF1's `-zeros.tif` (or its single-TIFF ZIP) with the
   note in §0 and archive the portal receipt via `scripts/record_live_score.py`.
2. **Next lane must break parent convergence**: preregister either `H24-DRAIN5` (flow-routing
   knickpoint graph — genuinely new evidence geometry; coarse 100 m version runnable here) or
   `H24-KERN6` (DTI-kernel soft-label regression — new target geometry), each with a dot-overlap
   pre-check design, instead of more channels on DPRF1.
3. **On an unrestricted machine:** `H24-INSAR4` (NASA ASF OPERA DISP-S1, free/official) remains
   the only wholly independent sensor physics not yet tested; unreachable from this sandbox
   (checked 2026-10-26: only `github.com`/`pypi.org` respond).

## 7. Limitations, irregularities, framing integrity

- No ORGANIZER-CONFIRMED score exists for any file discussed; `0.3195` vs `0.4413` leader claims
  conflict and are unverified. Fault recovery is a structural proxy, not geothermal-vent discovery.
- `IRR-EUL1-VG-BANDS`: bridge `*_vg` bands are not certified derivatives of their same-prefix
  fields (see amendment). Recorded in `registry/irregularities.json`.
- `IRR-EUL1-FOOTPRINT-COUNT`: one DPRF1 preregistration table quotes 5,167,378 footprint pixels;
  the template/footprint actually used everywhere contains **5,167,373** (Δ=5 px, documentation
  only — all computation uses `gems.footprint.load_footprint()`).
- The committed DPRF1 runner's `main()` does not itself emit the selector-receipt fields present
  in its run card (they were attached by the parallel selector step); EUL1's runner emits the
  complete card including `selector_receipt` and verifies byte-consistency. Noted for audit; no
  recorded DPRF1 number changes (its receipts re-verify exactly, and its holdout replayed
  bit-identically here).
- Euler depth uses `|z0|`; with FFT (z-down) derivatives 99.6–100% of accepted solutions already
  have positive signed depth, so this costs nothing on this data.
- Sandbox limits: DrivenData, NLR, USGS, OpenEI and NASA hosts unreachable (only GitHub/PyPI);
  competition data are the hash-pinned owner bridge (`4371c82e…`), integrity-verified but not
  organizer-authenticated. 3.8 GiB RAM / 2 CPU; EUL1 peaked at 3,162 MiB, 987 s.

## 8. JSON run card (Rule 5 — canonical copy in `evidence/eul1_run_card_20261026.json`)

```json
{
  "lane_id": "H24-EUL1",
  "hypothesis": "Euler N=0 contact solution clusters trace buried basement faults missed by surface mapping; as supervised channels + Regime-B gates on the DPRF1 stack they improve whole-segment hide-and-recover.",
  "mechanism": "7x7 windowed least-squares Euler homogeneity (Thompson 1982; Reid et al. 1990) on RTP/gravity with self-consistent FFT vertical derivatives; accepted solutions accumulate along faulted contacts.",
  "named_non_fault_mimic": "Unfaulted Mesozoic pluton-hornfels intrusive contacts and detrital-magnetite paleochannels",
  "holdout": {"label": "HOLDOUT-DTI", "evaluator_version": "gems-segment-pooled-v1", "dti": 0.16004597938259862, "ci95": [0.14728857870804618, 0.17278397417915392], "n_withheld_positive_pixels": 60988},
  "paired_vs_dprf1_replay_bit_identical": {"delta_dti": -0.003746445314551483, "ci95": [-0.008251864687596965, 0.0007377867788703488], "fold_wins": "1/4"},
  "correlation_overlap_vs_registry": {"surface_max_abs_rho": 0.5432, "final_max_abs_rho": 0.7579, "final_max_3px_overlap_competing": 0.8657, "overlap_vs_dprf1": 0.8657, "peers_max_3px_overlap": 0.5524, "literal_lattice_overlap": 0.9956, "duplicate": true},
  "raster_sha256": "4a65a49914bbd93107e429d06e316f35f3f1d04b957b8f8af12a0d952c28708a",
  "validator": {"no_nan_in_footprint": true, "strict_whole_array_0_1": true, "crs_shape_transform_match": true, "positive_pixels": 37654},
  "submission_name": "gems24-eul1-negative-euler-contact-20261026-eda170f04847-zeros.tif",
  "note": "GEMS24 EUL1 | Euler N0 contact 59ch stitched-OOF | id eda170f04847 | HOLDOUT-DTI 0.16005 | research; selector gated",
  "verdict": "negative",
  "ok_to_download": true,
  "ok_to_submit": false,
  "organizer_confirmed_score": null
}
```
