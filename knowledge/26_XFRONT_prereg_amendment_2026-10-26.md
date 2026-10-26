# Preregistration amendment #1 — H24-XFRONT (committed **before** the experiment run) — 2026-10-26

Amends `knowledge/25_preregistered_XFRONT_2026-10-26.md` (commit `3ebb375`).
Filed **before any holdout number, canary or novelty result existed**; only a
400×400 px smoke test on the operator's numerical behaviour had been run.

## A1. Corroboration must involve at least two layers (definitional fix)

With one contributing layer the weighted mean resultant length is
`|w·e^{2iθ}|/w ≡ 1` **by construction**, so neither `R_obs` nor `R_null` is
defined as a corroboration measure there; the smoke test confirmed the
degenerate signature (`coherence` median `0.957`, `null_coherence` median
`0.849`, driven almost entirely by single-layer pixels: median total weight
`0.82` of a possible `6`).

**Amendment:** `MIN_TOTAL_WEIGHT = 1.0` → **`2.0`**, i.e. a pixel must be
corroborated by the equivalent of **two fully-weighted independent layers**
(weight ramp unchanged: `w_m = clip((p_m − 0.70)/0.30, 0, 1)`). This is the
meaning of "cross-modal corroboration", not a tuning parameter; it is not
chosen to improve any score, and no score has been observed.

## A2. Null statistic evaluated on the eligible set only (identical maths)

The preregistered null is unchanged in definition — per draw, each layer's
orientation field is translated by an independent random integer offset with
each component uniform on ±[40, 400] px, weights held fixed, toroidal wrap with
the outside-footprint orientation replaced by a seeded sample of the
inside-footprint distribution. Only the **implementation** changes: the draw
loop is evaluated on the flat index list of eligible pixels (gather from the
2-D orientation field at the translated coordinates) instead of materialising
`np.roll` copies of the full 12.3 M-pixel grid. The arrays are therefore
bit-comparable to the 2-D formulation up to float32 associativity, and the
speed-up is what makes the full-grid 19-draw null affordable on this sandbox.

## A3. Not amended

Modalities, scales (σ = 1.2, 3.0 px), weight floor (0.70), draw count (19),
shift range (40–400 px), seed (20261026), emission operator
(`priority_poisson`, `min_dist = 2.8 px`), catalogue clearance (2.0 px), the
budget grid, the selection statistic (sparse-simulated DTI), the primary
endpoint, the novelty gates and the stop rules are **unchanged**.

## A4. Why the translation null is kept rather than a uniform-angle null

The smoke test shows the six orientation fields share a strong **regional
structural grain**, so even a 40–400 px translation leaves substantial
orientation agreement. A uniform-random-angle null would therefore declare
almost every pixel "significant" and would merely rediscover the grain. The
translation null asks the question this lane is actually about: *is this
particular place more co-oriented than other places carrying the same local
edge strengths?* It is the conservative choice and it is retained.
