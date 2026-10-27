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
    ("S3DEP1", "evidence/s3dep1_run_card_20261026.json", "holdout"),
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


# Two out-of-tree source receipts are pinned separately from main-branch records.
# They are conservative prospective floors, not endorsed models or upload decisions.
EXTERNAL_RECORDS = (
    {
        "lane": "DRAIN5",
        "source": "evidence/external/drain5-pr50-48a5f80e.json",
        "sha256": "f8901f8fd57377b5e3334760880593c35130a49f9e36efccd1559910ccd5209d",
        "ref": "48a5f80e6e1598874dd13c1f6a38f6c327ab75e0",
        "git_blob": "4ed260c8fd943571a71117e7f669290408d78cde",
        "source_url": (
            "https://github.com/buffedlizard55-lab/GEMSDOE24/blob/"
            "48a5f80e6e1598874dd13c1f6a38f6c327ab75e0/"
            "evidence/drain5_run_card_20261026.json"
        ),
        "pull_request": "https://github.com/buffedlizard55-lab/GEMSDOE24/pull/50",
    },
    {
        "lane": "KPL-36",
        "source": "evidence/external/kpl36-61783525.json",
        "sha256": "9448983264018a95518f79da1f63ecfb0f981f740f11ceaeebf341abac8a8d04",
        "ref": "61783525af4aa6dcf8da0bc68b06fa38b89ed27a",
        "git_blob": "2b0662c5f67aa3a8d154dfd495cc8ede2b3a0aef",
        "source_url": (
            "https://github.com/buffedlizard55-lab/GEMSDOE36/blob/"
            "61783525af4aa6dcf8da0bc68b06fa38b89ed27a/"
            "evidence/kpl36_run_card_20261026.json"
        ),
    },
)


def selection_floor(root: Path) -> dict:
    """Return the highest declared local or pinned concurrent comparison floor.

    Neither scientific replay nor complete protocol equivalence is established by
    the shared evaluator/version/count. Missing or altered external evidence must
    fail closed, not silently lower the floor. The selector remains negative-only.
    """
    root = Path(root)
    points = [recorded_point_best(root)]
    for source in EXTERNAL_RECORDS:
        path = root / source["source"]
        if not path.is_file() or sha256_file(path) != source["sha256"]:
            raise ValueError("Pinned concurrent benchmark receipt missing or changed")
        card = json.loads(path.read_text())
        result = card.get("holdout", {})
        if source["lane"] == "KPL-36":
            # This peer receipt stores the primary measurement under its selected arm.
            if card.get("best_arm") != "EXP-3" or result.get("best_arm") != "EXP-3":
                raise ValueError("Peer benchmark selected arm changed")
            arm = result.get("arms", {}).get("EXP-3", {})
            result = {
                "label": result.get("label"),
                "evaluator_version": result.get("evaluator_version"),
                "n_withheld_positive_pixels": result.get("n_withheld_positive_pixels"),
                "dti": arm.get("dti"),
                "ci95": {"interval": arm.get("ci95")},
            }
        ci = result.get("ci95", {}).get("interval", [])
        dti = result.get("dti")
        if (
            result.get("label") != "HOLDOUT-DTI"
            or result.get("evaluator_version") != EVALUATOR
            or type(result.get("n_withheld_positive_pixels")) is not int
            or result.get("n_withheld_positive_pixels") != WITHHELD
            or type(dti) not in (float, int)
            or not math.isfinite(dti)
            or not 0 <= dti <= 1
            or not isinstance(ci, list)
            or len(ci) != 2
            or any(type(v) not in (float, int) or not math.isfinite(v) for v in ci)
            or not 0 <= ci[0] <= dti <= ci[1] <= 1
        ):
            raise ValueError("Malformed concurrent benchmark receipt")
        points.append(
            {
                "lane": source["lane"],
                "source": source["source"],
                "source_sha256": source["sha256"],
                "source_url": source["source_url"],
                "holdout": result,
                "source_reported_verdict": card.get("verdict"),
                "verdict": "not independently certified",
                "ok_to_submit": False,
                "scope": (
                    "Concurrent point estimate, not independently replayed; matching evaluator/count "
                    "does not prove protocol equivalence or certify the candidate."
                ),
            }
        )
    return max(points, key=lambda row: row["holdout"]["dti"])
