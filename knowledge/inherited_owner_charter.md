# Inherited owner charter (preserved wording)

> Review the repo; ensure an easy one-click downloadable submission tif exists
> as the prompt describes; read the entire prompt. Formally test whether the
> "geology" signal is actually encoding field accessibility, then remove it:
> train a classifier two-sample test (the ML literature's distribution-shift
> detector, Lopez-Paz & Oquab, ICLR 2017) to distinguish pixels near a mapped
> fault from far pixels using ONLY non-geological confound features: distance to
> nearest road/trail, distance to historic mining claims, and which of GeoDAWN's
> four acquisition blocks (each with different line spacing and flight height) a
> pixel falls in. If it beats its own null distribution by a meaningful margin,
> that confirms the catalogue's shape is confounded by where geologists could
> physically get to (strengthens the scientific case, and identifies exactly
> what to residualize before training the real detector). Run on training labels
> first to validate the premise, then again on our own predicted raster before
> spending a submission slot; if predictions are equally explained by
> road/acquisition-block proximity, the gain is mapping-process overfitting, not
> discovery. A spatially-blocked holdout alone won't catch it since holdout
> faults come from the same biased catalogue. Study/analyze why 19GEMSDOE got the
> group's best live scores (h19-4 …691e4dfa-nan = 0.1894, h19-5 …e27054cf-nan =
> 0.1922) and whether we can beat 0.1894 (leader 0.3049 per user; site says
> 0.3168). Before implementing, produce 3–5 candidate geological hypotheses not
> yet tried, each naming: specific layer(s), the physical signature targeted
> (e.g. edge-detection/curvature transform), why it should catch a fault missing
> from the USGS/INGENIOUS catalogue, and how it differs from everything already
> in the repo; rank by expected DTI improvement and implementation cost;
> validate the top one on the spatially-blocked holdout; if new external data is
> needed, name the specific free official source and verify it is obtainable.
> Put this prompt into the repo README and treat it as the standing starting
> point each session; keep Arena Core Values ("Maximize P(Win)", "Own the
> Outcome") as a focal point. Fix the submission error the user hit — "Predicted
> values must be in range [0, 1]" — and give each tif a unique name plus a short
> DrivenData note; create an executive-summary subpage explaining exactly how to
> submit, obvious on the site's first screen. Autonomously complete the "data
> placement" blocker (download into data/, then prepare_data) with no manual
> input. Verify line by line against official sources with links for manual
> review; flag irregularities; no hallucinations; 3 passes; finish by opening
> and merging a PR to main, stating remaining work and limitations.

The complete uncondensed original chat was not available in this continuation.
This preserves the inherited charter verbatim; the root README records all
additional active constraints available in the session context. It is not
a claim to reproduce unseen text word for word.
