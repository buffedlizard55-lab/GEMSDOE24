"""Read-only inventory of declared same-evaluator records, not a promotion gate.

A later point-best record must not be hidden by comparing a new candidate only
to an easier old benchmark. Matching label/version/count is not an independent
certificate of protocol equivalence, leakage control, a paired gain or novelty.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

from .validator import sha256_file

EVALUATOR = "gems-segment-pooled-v1"
WITHHELD = 60988
RECORDS = (
    ("GVC1", "evidence/gvc1_run_card_20261025.json", "holdout"),
    ("CRP1", "evidence/crp1_run_card_20261026.json", "holdout"),
    ("CUP1", "evidence/cup1_run_card_20261026.json", "holdout_dti"),
    ("TNR1", "evidence/tnr1_run_card_20261026.json", "holdout"),
    ("DPRF1", "evidence/dprf1_run_card_20261026.json", "holdout"),
    ("TRSG1", "evidence/trsg1_run_card_20261026.json", "holdout"),
)


def recorded_points(root: Path) -> list[dict]:
    root = Path(root)
    rows = []
    known = {source: (lane, key) for lane, source, key in RECORDS}
    for source in known:
        if not (root / source).is_file():
            raise ValueError(f"Known benchmark missing: {source}; cannot lower the floor")
    for path in sorted((root / "evidence").glob("*run_card*.json")):
        source = path.relative_to(root).as_posix()
        card = json.loads(path.read_text())
        if not isinstance(card, dict):
            if source in known:
                raise ValueError("Known benchmark is not an object")
            continue
        lane, key = known.get(source, (path.name.split("_run_card")[0].upper(), None))
        if key is None:
            key = next(
                (k for k in ("holdout", "holdout_dti") if isinstance(card.get(k), dict)), None
            )
        result = card.get(key) if key else None
        if not isinstance(result, dict):
            if source in known:
                raise ValueError("Known benchmark is missing its primary result")
            continue
        if (
            result.get("label") != "HOLDOUT-DTI"
            or result.get("evaluator_version") != EVALUATOR
            or result.get("n_withheld_positive_pixels") != WITHHELD
        ):
            if source in known:
                raise ValueError("Known benchmark no longer has the declared evaluator/count")
            continue  # Other metric/split records are not comparable even by declaration.
        dti = result.get("dti")
        ci = result.get("ci95")
        interval = ci.get("interval") if isinstance(ci, dict) else ci
        if isinstance(ci, list):
            result = {
                **result,
                "ci95": {
                    "level": 0.95,
                    "interval": ci,
                    "scope": "Normalized recorded CI list; no bootstrap replay",
                },
            }
        if (
            type(dti) not in (float, int)
            or not math.isfinite(dti)
            or not 0 <= dti <= 1
            or not isinstance(interval, list)
            or len(interval) != 2
            or any(type(x) not in (float, int) or not math.isfinite(x) for x in interval)
            or not 0 <= interval[0] <= interval[1] <= 1
        ):
            raise ValueError("Malformed benchmark DTI/CI")
        rows.append(
            {
                "lane": lane,
                "source": source,
                "source_sha256": sha256_file(path),
                "holdout": result,
                "verdict": card.get("verdict"),
                "ok_to_submit": card.get("ok_to_submit"),
                "scope": "Recorded point estimate; no independent protocol/paired-gain/novelty certification",
            }
        )
    return sorted(rows, key=lambda row: row["holdout"]["dti"], reverse=True)


def recorded_point_best(root: Path) -> dict:
    rows = recorded_points(root)
    if not rows:
        raise ValueError("No known benchmark receipt; cannot assume an easier current best")
    return rows[0]
