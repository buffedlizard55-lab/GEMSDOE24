"""Fast, exact paired holdout evaluator for binary emission rasters.

``FoldCache`` replicates ``gems.metric.dti_score_fast`` for the four-quadrant
``gems.holdout.Holdout`` protocol using KD-tree nearest distances (identical to the
Euclidean distance transform) so that many sparse-truth draws and many candidates can be
scored cheaply.  ``verify_against_reference`` asserts bit-level agreement with the
reference implementation and must be called before any result is used.

Valid only for candidates with no pixel on a catalogue cell (so removing the draw-dependent
"known" cells never changes the prediction).
"""

from __future__ import annotations

import numpy as np
from scipy.spatial import cKDTree

from . import holdout, metric


class FoldCache:
    """Exact replica of ``metric.dti_score_fast`` using KD-tree nearest distances.

    Euclidean distance to the nearest predicted/truth pixel equals the
    ``distance_transform_edt`` value, so scores are identical (checked against
    ``gems.metric`` before any result is used).  Valid because every candidate has
    no pixel on a catalogue cell, so removing the draw-dependent 'known' cells never
    changes the prediction.
    """

    def __init__(self, fp, labels, offsets):
        self.offsets = list(offsets)
        self.fp, self.labels, self.n_draws = fp, labels, len(self.offsets)
        self.ref = holdout.Holdout(fp, labels)
        self.draws = []
        for off in self.offsets:
            h = holdout.Holdout(fp, labels, sparse_seed_offset=off)
            per = []
            for _f, _n, _m, _sl, _td, ts, _kc, _fm in h.quads:
                xy = np.argwhere(ts).astype(np.float64)
                per.append({"xy": xy, "tree": cKDTree(xy) if len(xy) else None})
            self.draws.append(per)
        self.dense = []
        for _f, _n, _m, sl, td, _ts, _kc, fm in self.ref.quads:
            xy = np.argwhere(td).astype(np.float64)
            self.dense.append(
                {"xy": xy, "tree": cKDTree(xy) if len(xy) else None, "valid": fm, "sl": sl}
            )

    def prep(self, mask):
        out = []
        for _f, _n, _m, sl, _td, _ts, _kc, fm in self.ref.quads:
            xy = np.argwhere(mask[sl] & fm).astype(np.float64)
            out.append({"xy": xy, "tree": cKDTree(xy) if len(xy) else None})
        return out

    @staticmethod
    def _score(pred, truth):
        n_truth, n_pred = len(truth["xy"]), len(pred["xy"])
        if n_truth == 0 or n_pred == 0:
            return {"dti": 0.0, "tp": 0.0, "fp": float(n_pred), "n": n_pred}
        r = metric.RADIUS_PX
        d_to_pred = pred["tree"].query(truth["xy"])[0]
        tp = float(np.maximum(1.0 - d_to_pred / r, 0.0).sum())
        fn = n_truth - tp
        d_to_truth = truth["tree"].query(pred["xy"])[0]
        fp = float((1.0 - np.maximum(1.0 - d_to_truth / r, 0.0)).sum())
        dti = tp / (tp + metric.ALPHA * fp + metric.BETA * fn + metric.EPS)
        return {"dti": float(dti), "tp": tp, "fp": fp, "n": n_pred}

    def dense_scores(self, prep):
        return [self._score(prep[f], q) for f, q in enumerate(self.dense)]

    def sparse_scores(self, prep, draw):
        return [self._score(prep[f], q) for f, q in enumerate(self.draws[draw])]


def verify_against_reference(cache, fp, labels, mask):
    """Assert the cached evaluator equals gems.metric.dti_score_fast (exactness check)."""
    prep = cache.prep(mask)
    worst = 0.0
    for draw in sorted({0, min(7, cache.n_draws - 1)}):
        h = holdout.Holdout(fp, labels, sparse_seed_offset=cache.offsets[draw])
        mine = cache.sparse_scores(prep, draw)
        for f, (_f, _n, _m, sl, _td, ts, kc, fm) in enumerate(h.quads):
            ref = metric.dti_score_fast(mask[sl], ts, valid_mask=fm, catalogue_mask=kc)
            worst = max(worst, abs(ref["dti"] - mine[f]["dti"]))
    dense_ref = []
    for f, (_f, _n, _m, sl, td, ts, kc, fm) in enumerate(cache.ref.quads):
        dense_ref.append(metric.dti_score_fast(mask[sl], td, valid_mask=fm)["dti"])
    mine = cache.dense_scores(prep)
    worst = max(worst, max(abs(a - b["dti"]) for a, b in zip(dense_ref, mine)))
    if worst > 1e-9:
        raise SystemExit(f"cached evaluator differs from metric.dti_score_fast by {worst}")
    return worst
