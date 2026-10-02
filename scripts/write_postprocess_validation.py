#!/usr/bin/env python3
"""Write the promotion-path validation record for the frozen primary selection.

Reads ``evidence/h24_e1_operator_comparison.json`` (selection and confirmation already frozen by
``knowledge/04_preregistered_emission_2026-10-02.md`` sections 5-6) and the exact source raster, and writes
``evidence/h24_e1_validation_primary.json`` in the schema ``gems.promotion.require_postprocess_evidence``
reads. Nothing is re-selected here.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems.validator import sha256_file  # noqa: E402

H19_5_SHA = "ec1f9b56b83ce33cad781ceb9f104b18fb4f2ff785263a4e89616af4aabdee8d"


def main() -> None:
    comp = json.loads((ROOT / "evidence/h24_e1_operator_comparison.json").read_text())
    sel = comp["frozen_selection"]
    primary = sel["primary"]
    if not primary or not sel["primary_passes_confirmation"]:
        raise SystemExit("No primary candidate passed the frozen selection and confirmation")
    row = comp["bases"]["h19-5"]["candidates"][primary]
    if row["kind"] != "dot_thin":
        raise SystemExit(
            "The frozen primary is not a dot_thin raster; this record covers dot_thin only"
        )
    d = float(row["param"])
    src = ROOT / f"out/h25-1-dotthin-d{d:g}-h19-5.tif"
    ref = next((ROOT / "inputs").glob("*h19-5*-nan.tif"))
    record = {
        "preregistration": "knowledge/04_preregistered_emission_2026-10-02.md (sections 5-6)",
        "protocol": {
            "transform_reads_labels_or_scores": False,
            "operator": "gems.thinning.dot_thin on H19-5 with catalogue pixels removed first",
            "selection_draw_offsets": comp["selection_draw_offsets"],
            "confirmation_draw_offsets": comp["confirmation_draw_offsets"],
            "selection_rule": "legacy holdout.gate on selection draws, highest model-extrapolated public score, "
            "confirmed on disjoint draws",
        },
        "sources": {"h19_5": {"path": str(ref.relative_to(ROOT)), "sha256": sha256_file(ref)}},
        "selection_and_gates": {
            "selected_d": d,
            "eligible": bool(sel["primary_passes_confirmation"]) and sha256_file(ref) == H19_5_SHA,
            "eligible_on_selection_draws_ranked": sel[
                "eligible_on_selection_draws_ranked_by_model_score"
            ],
            "legacy_gate_selection": row["selection"]["legacy_gate"],
            "legacy_gate_confirmation": row["confirmation"]["legacy_gate"],
            "selection_summary": {
                k: row["selection"][k]
                for k in (
                    "mean_dense_dti",
                    "mean_sparse_dti",
                    "paired_sparse_gain_rel",
                    "model_public_score",
                )
            },
            "confirmation_summary": {
                k: row["confirmation"][k]
                for k in (
                    "mean_dense_dti",
                    "mean_sparse_dti",
                    "paired_sparse_gain_rel",
                    "model_public_score",
                )
            },
        },
        "candidate": {
            "path": str(src.relative_to(ROOT)),
            "sha256": sha256_file(src),
            "positive_pixels": row["n"],
            "pixel_fraction_of_h19_5": row["pixel_fraction"],
        },
        "slot_spent": False,
    }
    out = ROOT / "evidence/h24_e1_validation_primary.json"
    out.write_text(json.dumps(record, indent=2) + "\n")
    print(
        json.dumps(record["selection_and_gates"]["legacy_gate_selection"]["rules"]),
        record["candidate"],
    )


if __name__ == "__main__":
    main()
