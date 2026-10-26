# H24-EUL1 Preregistration Amendment A1 — vertical-derivative metrology (2026-10-26, pre-fit)

**Amends:** `knowledge/22_preregistered_EUL1_2026-10-26.md` §3 (locked at
`b841bf4d7c3227ccb126ed3acfa74ecbb1d2d217`). Recorded **before any holdout fit, canary
on labels, or raster export** in this session. The amendment changes *how the vertical
derivative `Fz` is obtained*; it changes no hypothesis, arm structure, acceptance
threshold, budget, evaluator, seed, or gate.

## What was found (label-free; physical fields only)

Pre-fit smoke test of `gems.euler.euler_solutions` on an 800×800 px crop of the real
stack returned **zero** accepted solutions under the preregistered plan (survey
`*_vg` bands as `Fz`). Diagnostics (no labels read):

| Check | Result |
|---|---|
| `corr(tmi_hg, \|∇ tmi\| per px)` | 0.9906, median ratio **exactly 2.0000** — survey horizontal derivatives use `(f[i+1]−f[i−1])` without the `/2` of `np.gradient` |
| `corr(tmi_vg, FFT \|k\| ∂_down tmi)` (central 1200² crop interior) | **0.973**, slope `tmi_vg = 0.00937 × fz_per_px` — the band is a genuine vertical derivative of `tmi` but at ~1/107 per-pixel scale (consistent with per-metre units) |
| `corr(tmi_vg, FFT ∂_down rtp)` | 0.790 — it is **not** the vertical derivative of `rtp` (the field the preregistration paired it with) |
| `corr(iso_grav_anom_vg, FFT ∂_down iso_grav_anom)` | **−0.008** — the band is not the vertical derivative of `iso_grav_anom` under any scale/sign (band-provenance irregularity; cf. existing `IR-BAND-PROVENANCE`) |
| Solved median depth with raw `tmi_vg` as `Fz(rtp)` | 163 px (16.3 km) — physically absurd; pure unit mismatch |

Euler homogeneity `x0·Fx + y0·Fy + z0·Fz = u·Fx + v·Fy` requires all three derivatives
in identical units for the *same* field. The preregistered band pairing violates that
for both fields, so the original implementation would have tested a units bug, not the
geological hypothesis.

## Amendment

`Fz` is computed self-consistently from each field itself via the exact harmonic
identity `Fz_down = IFFT(|k| · FFT(F))` in per-pixel units
(`gems.euler.fft_vertical_derivative`, mirror-pad + pad-zone cosine taper), validated
against the analytic vertical derivative of a synthetic harmonic field
(`tests/test_euler.py::test_fft_vertical_derivative_matches_analytic`, |corr| > 0.95
interior). Survey `*_vg` bands are used only for the recorded forensics table. Depth
remains `|z0|` (sign-convention invariant). All preregistered acceptance numbers are
unchanged (window 7×7, N=0, depth 0.5–15 px, |plan| ≤ 3.5 px, relative residual < 0.15).

Post-amendment label-free acceptance on the same crop: RTP 0.875% of valid windows
accepted (median depth 4.83 px = 483 m, median accepted rel. residual 0.125);
gravity 0.121% (median depth 11.07 px). Sparse acceptance is expected Euler behaviour
(single-contact windows are rare); thresholds were **not** loosened to chase density.

## Irregularity flagged

`IRR-EUL1-VG-BANDS (2026-10-26)`: `iso_grav_anom_vg` in the owner-bridge
`training_features.tif` (sha256 `4371c82e…`) is not the vertical derivative of
`iso_grav_anom` (corr −0.008), and `tmi_vg` pairs with `tmi`, not `rtp`, at ~1/107
per-pixel scale. Any prior lane that consumed `*_vg`/`*_hg` bands as generic features
is unaffected (tree models are scale-invariant per column and no lane used them as
matched derivative triples), but no future work should treat the `*_vg` bands as
certified derivatives of their same-prefix fields without repeating this check.
