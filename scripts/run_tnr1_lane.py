#!/usr/bin/env python3
"""One fixed TNR1 research experiment with shared holdout/writer and literal stops."""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import numpy as np  # noqa: E402
import rasterio  # noqa: E402
from run_hcw_lane import build_engineered_features, load_nuisance_matrix  # noqa: E402
from scipy.ndimage import distance_transform_edt  # noqa: E402
from sklearn.ensemble import HistGradientBoostingClassifier  # noqa: E402
from threadpoolctl import threadpool_limits  # noqa: E402

from gems import c2s2, emission, holdout, novelty, submission  # noqa: E402
from gems.github_archive import safe_relative  # noqa: E402
from gems.preflight import preflight  # noqa: E402
from gems.targeted_residual import (  # noqa: E402
    ENGINEERED_NAMES,
    HGB_PARAMS,
    TargetedResidualizer,
)
from gems.validator import sha256_file  # noqa: E402

SEED = 20261026
CHUNK = 75000
BUDGET = 0.0073
REGISTRY = ROOT / "registry/tnr1_union_20261026.json"
TEMPLATE = ROOT / "data/bridge/sample_submission.tif"
CARD = ROOT / "evidence/tnr1_run_card_20261026.json"
REPORT = ROOT / "evidence/tnr1_experiment_20261026.json"
WORK = ROOT / "data/research/tnr1/run"
PREREG = ROOT / "knowledge/20_preregistered_TNR1_2026-10-26.md"
PREREG_COMMIT = "8cd6782"


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".partial")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def array_sha(values):
    return hashlib.sha256(np.ascontiguousarray(values).tobytes()).hexdigest()


def batches_canary(context, named_vectors, fp_ids, *, group_size=4):
    """Memory-bounded adapter to the central canary, not another AUC implementation."""
    all_rows, pending, template_report = {}, {}, None

    def flush():
        nonlocal template_report
        if not pending:
            return
        result = context.canary(pending, seed=SEED)
        template_report = result
        all_rows.update(result["features"])
        pending.clear()
        gc.collect()

    for name, vector in named_vectors:
        if name in all_rows or name in pending:
            raise ValueError("Canary feature names must be unique")
        values = np.asarray(vector)
        if values.shape != (len(fp_ids),):
            raise ValueError("Canary vector must cover every footprint cell")
        grid = np.full(context.footprint.shape, np.nan, np.float32)
        grid.ravel()[fp_ids] = values
        pending[name] = grid
        if len(pending) >= group_size:
            flush()
    flush()
    if template_report is None:
        raise ValueError("No actual inputs were screened")
    return {
        **template_report,
        "features": all_rows,
        "feature_count": len(all_rows),
        "passed": not any(row["leakage_suspected"] for row in all_rows.values()),
    }


def sample_training(fp_ids, train, visible, seed):
    """Catalogue-derived sampling depends only on visible faults, never hidden truth."""
    if train.shape != visible.shape or not visible.any():
        raise ValueError("Aligned nonempty visible catalogue required")
    distance = distance_transform_edt(~visible)
    positive = np.flatnonzero((train & visible).ravel()[fp_ids])
    negative = np.flatnonzero((train & ~visible & (distance >= 9)).ravel()[fp_ids])
    del distance
    if not len(positive) or not len(negative):
        raise ValueError("Both train classes required")
    rng = np.random.default_rng(seed)
    pos = rng.choice(positive, min(20000, len(positive)), replace=False)
    neg = rng.choice(negative, min(60000, len(negative)), replace=False)
    training = np.r_[pos, neg]
    y = np.r_[np.ones(len(pos), np.int8), np.zeros(len(neg), np.int8)]
    pool = np.flatnonzero(train.ravel()[fp_ids])
    uniform = np.random.default_rng(seed + 100).choice(pool, min(30000, len(pool)), replace=False)
    if not train.ravel()[fp_ids[np.r_[training, uniform]]].all():
        raise AssertionError("Sampling escaped the training mask")
    return training, y, uniform


def fit_models(stack, engineered, nuisance, names, fp_ids, train, visible, seed, *, control):
    selected, y, uniform = sample_training(fp_ids, train, visible, seed)

    def features(indices):
        return np.column_stack([np.asarray(stack[indices, :27]), engineered[indices]]).astype(
            np.float32
        )

    intervention = TargetedResidualizer(names).fit(nuisance[uniform], features(uniform))
    raw_train = features(selected)
    model = HistGradientBoostingClassifier(**HGB_PARAMS).fit(
        intervention.transform(nuisance[selected], raw_train), y
    )
    raw = HistGradientBoostingClassifier(**HGB_PARAMS).fit(raw_train, y) if control else None
    return (
        model,
        raw,
        intervention,
        {
            "positive_training_rows": int(y.sum()),
            "negative_training_rows": int((y == 0).sum()),
            "uniform_fit_rows_sha256": array_sha(uniform.astype("<i8")),
            "supervised_rows_sha256": array_sha(selected.astype("<i8")),
            "training_mask_sha256": array_sha(train),
            "visible_catalogue_sha256": array_sha(visible),
            "all_sampled_rows_inside_train": True,
            "catalogue_distance_source": "visible faults only, >=9 px negative buffer",
            "intervention": intervention.receipt(),
        },
    )


def nuisance_audit(name, reference, nuisance, nuisance_names, fp_ids, context):
    features = {}
    for i, key in enumerate(nuisance_names):
        arr = np.full(context.footprint.shape, np.nan, np.float32)
        arr.ravel()[fp_ids] = nuisance[:, i]
        features[key] = arr
    result = c2s2.c2s2_test(
        name,
        reference,
        features,
        context.fold_grid,
        context.footprint,
        n_per_class=8000,
        n_null=99,
        seed=SEED,
    ).as_dict()
    return result


def verify_diagnostic_algebra(card, report, root):
    """Verify recorded diagnostic arithmetic, never refit or rerun a canary/model."""
    registry_path = root / REGISTRY.relative_to(ROOT)
    if sha256_file(registry_path) != report["inputs"][REGISTRY.relative_to(ROOT).as_posix()]:
        raise ValueError("Frozen TNR1 registry changed")
    entries = json.loads(registry_path.read_text())["unique_rasters"]
    expected = {row["id"]: (row["file"], row["footprint_sha256"]) for row in entries}
    if len(expected) != report["registry_unique_rasters"]:
        raise ValueError("TNR1 comparator count changed")
    for stage, result in card["correlation_overlap_vs_registry"].items():
        rows = result["rows"]
        identities = {row["registry_id"]: (row["file"], row["footprint_sha256"]) for row in rows}
        if (
            identities != expected
            or len(rows) != len(expected)
            or result["registry_unique_rasters"] != len(expected)
            or result["stage"] != stage
        ):
            raise ValueError("TNR1 omitted/replaced a frozen comparator")
        if (result["rank_limit"], result["overlap_limit"], result["overlap_distance_px"]) != (
            0.90,
            0.70,
            3,
        ):
            raise ValueError("TNR1 novelty thresholds changed")
        rank_values, overlaps = [], []
        for row in rows:
            ranks = [
                row[key] for key in ("raw_spearman", "kernel_spearman") if row[key] is not None
            ]
            overlap = row["candidate_dot_overlap_within_3px"]
            if any(not np.isfinite(value) or abs(value) > 1 for value in ranks):
                raise ValueError("Invalid TNR1 correlation")
            if stage == "final_dots":
                if overlap is None or not np.isfinite(overlap) or not 0 <= overlap <= 1:
                    raise ValueError("Invalid TNR1 final overlap")
                overlaps.append(overlap)
            elif overlap is not None:
                raise ValueError("Pre-placement TNR1 receipt contains placed-dot overlap")
            duplicate = any(abs(value) > 0.90 for value in ranks) or (
                overlap is not None and overlap > 0.70
            )
            if row["duplicate"] is not duplicate:
                raise ValueError("TNR1 literal duplicate flag disagrees")
            rank_values.extend(abs(value) for value in ranks)
        if result["passed"] is not (not any(row["duplicate"] for row in rows)):
            raise ValueError("TNR1 novelty summary disagrees")
        maximum = max(rank_values, default=None)
        if result["max_abs_rank_correlation"] != maximum or result["max_dot_overlap"] != max(
            overlaps, default=None
        ):
            raise ValueError("TNR1 maximum correlation/overlap disagrees")
    for key in ("raw_feature_canary", "oof_transform_canary"):
        result = card.get(key)
        if result is None:
            continue
        if (
            result["threshold"] != 0.90
            or result["two_polarities_checked"] is not True
            or result["feature_count"] != len(result["features"])
        ):
            raise ValueError("TNR1 canary scope/threshold changed")
        for row in result["features"].values():
            aucs = [row["pooled_auc"], *[fold["auc"] for fold in row["folds"]]]
            if any(not np.isfinite(value) or not 0 <= value <= 1 for value in aucs):
                raise ValueError("Invalid recorded TNR1 AUC")
            flagged = any(max(value, 1 - value) > 0.90 for value in aucs)
            if row["leakage_suspected"] is not flagged:
                raise ValueError("TNR1 canary must check both AUC polarities")
        if result["passed"] is not (
            not any(row["leakage_suspected"] for row in result["features"].values())
        ):
            raise ValueError("TNR1 canary summary disagrees")
    paired = card.get("paired_comparison")
    if paired:
        delta = card["holdout"]["dti"] - card["matched_control_holdout"]["dti"]
        if (
            not np.isclose(paired["paired_delta_dti"], delta, atol=1e-14)
            or paired["candidate_dti"] != card["holdout"]["dti"]
            or paired["baseline_dti"] != card["matched_control_holdout"]["dti"]
            or paired["ci95_strictly_positive"] is not (paired["paired_delta_ci95"][0] > 0)
        ):
            raise ValueError("TNR1 paired comparison disagrees")
    for result in card.get("recorded_baseline_comparisons", {}).values():
        baseline_path = root / result["source"]
        safe_relative(result["source"])
        if sha256_file(baseline_path) != result["source_sha256"]:
            raise ValueError("TNR1 recorded comparator source changed")
        source = json.loads(baseline_path.read_text())
        field = (
            "holdout" if "gvc1" in result["source"] else "reconstructed_oof_multiphysics_baseline"
        )
        if (
            result["holdout"] != source[field]
            or result["baseline_replayed_this_session"] is not False
        ):
            raise ValueError("TNR1 baseline provenance disagrees")
        comparable = (
            result["holdout"]["protocol"] == card["holdout"]["protocol"]
            and result["holdout"]["evaluator_version"] == card["holdout"]["evaluator_version"]
            and result["holdout"]["n_withheld_positive_pixels"]
            == card["holdout"]["n_withheld_positive_pixels"]
        )
        if result["same_declared_protocol"] is not comparable or result[
            "candidate_point_estimate_higher"
        ] is not (comparable and card["holdout"]["dti"] > result["holdout"]["dti"]):
            raise ValueError("TNR1 current-best comparison disagrees")
    audit = card.get("exact_file_nuisance_audit")
    if audit:
        if audit["candidate_sha256"] != card["raster_sha256"]:
            raise ValueError("TNR1 nuisance audit names another artifact")
        results = [audit["labels_first"], audit["candidate"]]
        for result, adjusted in zip(results, c2s2.holm_adjust([r["p_value"] for r in results])):
            flagged = bool(
                adjusted <= 0.05
                and result["observed_auc"] >= 0.55
                and result["margin_vs_p95"] >= 0.02
            )
            if (
                not np.isclose(result["holm_p_value"], adjusted, atol=1e-14)
                or result["n_null"] != 99
                or result["null_kind"] != "grouped"
                or not np.isclose(
                    result["margin_vs_p95"],
                    result["observed_auc"] - result["null_auc_p95"],
                    atol=1e-14,
                )
                or result["strict_gate_flagged"] is not flagged
            ):
                raise ValueError("TNR1 C2ST decision arithmetic changed")
        if audit["passed"] is not (not audit["candidate"]["strict_gate_flagged"]):
            raise ValueError("TNR1 nuisance audit summary disagrees")
    if (
        report["hgb_parameters"] != HGB_PARAMS
        or report["prediction_inputs_include_prior_submission_pixels"] is not False
    ):
        raise ValueError("TNR1 frozen model/input declaration changed")


def verify_recorded(root=ROOT, *, source_history=True):
    """Reopen exact files and replay recorded algebra only; no experiment rerun."""
    card_path, report_path = root / CARD.relative_to(ROOT), root / REPORT.relative_to(ROOT)
    card, report = json.loads(card_path.read_text()), json.loads(report_path.read_text())
    if report.get("run_card") != card:
        raise ValueError("TNR1 report/card identity disagrees")
    if (
        any(card.get(key) is not False for key in ("ok_to_submit", "submission_authorized"))
        or card.get("verdict") != "negative"
    ):
        raise ValueError("TNR1 research cannot authorize a slot")
    if card.get("submission_slots_used") != 0 or card.get("experiments_run") != 1:
        raise ValueError("TNR1 budget or slot record changed")
    if json.loads((root / "docs/data/tnr1_run_card.json").read_text()) != card:
        raise ValueError("Published TNR1 card disagrees")
    for result in (card.get("holdout"), card.get("matched_control_holdout")):
        if result is None:
            continue
        if (
            result.get("label") != "HOLDOUT-DTI"
            or result.get("evaluator_version") != holdout.MTR_EVALUATOR_VERSION
        ):
            raise ValueError("TNR1 holdout version/label changed")
        pooled = holdout.pooled_components(result["folds"])
        for key in ("dti", "TP_w", "FP_w", "FN_w", "n_truth", "n_emitted"):
            if not np.isclose(result[key], pooled[key], rtol=1e-12, atol=1e-10):
                raise ValueError(f"TNR1 pooled {key} disagrees")
        if result["n_withheld_positive_pixels"] != pooled["n_truth"]:
            raise ValueError("TNR1 withheld count changed")
    verify_diagnostic_algebra(card, report, root)
    if card.get("organizer_confirmed_score") is not None:
        raise ValueError("TNR1 has no organizer-confirmed receipt")
    if source_history:
        if report["preregistration_commit"] != PREREG_COMMIT:
            raise ValueError("TNR1 preregistration identity changed")
        subprocess.check_call(
            ["git", "merge-base", "--is-ancestor", PREREG_COMMIT, report["execution_commit"]],
            cwd=root,
        )
        registry_name = REGISTRY.relative_to(ROOT).as_posix()
        original_registry = subprocess.check_output(
            ["git", "show", f"{report['execution_commit']}:{registry_name}"], cwd=root
        )
        if hashlib.sha256(original_registry).hexdigest() != report["inputs"][registry_name]:
            raise ValueError("TNR1 registry was not the committed pre-execution union")
        for path, expected in report["code_sha256"].items():
            raw = subprocess.check_output(
                ["git", "show", f"{report['execution_commit']}:{path}"], cwd=root
            )
            if hashlib.sha256(raw).hexdigest() != expected:
                raise ValueError("Executed TNR1 source fingerprint disagrees")
        if sha256_file(root / PREREG.relative_to(ROOT)) != report["preregistration_sha256"]:
            raise ValueError("TNR1 preregistration changed")
    name = card.get("submission_name")
    if name is None:
        return card
    if Path(name).name != name or not name.endswith("-zeros.tif"):
        raise ValueError("Unsafe TNR1 artifact name")
    note = card.get("note")
    if not isinstance(note, str) or not 0 < len(note) <= 140 or "DO NOT SUBMIT" not in note:
        raise ValueError("Invalid TNR1 note")
    path = root / "docs/downloads" / name
    fresh = submission.check_variants(path, root / "data/bridge/sample_submission.tif")
    if (
        not submission.recorded_validation_matches(fresh, card["validator_output"])
        or fresh["sha256"] != card["raster_sha256"]
    ):
        raise ValueError("TNR1 exact-file format/hash receipt changed")
    if (
        not fresh["format_valid"]
        or not fresh["checks"]["variant_strict_whole_array_no_nan_allowed"]["pass"]
    ):
        raise ValueError("TNR1 zero variant must be finite [0,1] everywhere")
    if (path.with_suffix(".note.txt")).read_text().strip() != note:
        raise ValueError("TNR1 note file disagrees")
    twin = card["nan_outside_companion"]
    if Path(twin["file"]).name != twin["file"] or not twin["file"].endswith("-nan.tif"):
        raise ValueError("Unsafe TNR1 companion name")
    twin_path = root / "docs/downloads" / twin["file"]
    if not submission.recorded_validation_matches(
        submission.check_variants(twin_path, root / "data/bridge/sample_submission.tif"),
        twin["validator_output"],
    ):
        raise ValueError("TNR1 companion receipt changed")
    with rasterio.open(root / "data/bridge/sample_submission.tif") as ds:
        fp = np.isfinite(ds.read(1))
    with rasterio.open(path) as ds, rasterio.open(twin_path) as ts:
        primary, companion = ds.read(1), ts.read(1)
    if not np.array_equal(primary[fp], companion[fp]) or not np.isnan(companion[~fp]).all():
        raise ValueError("TNR1 companion predictions or outside convention changed")
    pre = json.loads(path.with_suffix(".preflight.json").read_text())
    if (
        pre.get("artifact", {}).get("sha256") != fresh["sha256"]
        or pre.get("decision", {}).get("ready_to_submit") is not False
        or pre.get("decision", {}).get("submission_status") != "DO_NOT_SUBMIT"
    ):
        raise ValueError("TNR1 preflight is stale or permissive")
    fresh_preflight = preflight(
        path,
        root / "data/bridge/sample_submission.tif",
        run_card_path=card_path,
        expected_template_sha256=report["inputs"]["data/bridge/sample_submission.tif"],
    )
    # Paths vary between the execution machine, local clones and CI. The
    # current validator may add hard checks, all of which must pass, while
    # every issuance-time format finding and all other fields must still match.
    pre["run_card"]["path"] = fresh_preflight["run_card"]["path"]
    old_format = pre.pop("format_validation")
    new_format = fresh_preflight.pop("format_validation")
    if (
        not submission.recorded_validation_matches(new_format, old_format)
        or pre != fresh_preflight
        or card.get("ok_to_download") is not True
    ):
        raise ValueError("TNR1 exact-file preflight no longer reproduces")
    return card


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-recorded", action="store_true")
    args = parser.parse_args()
    if args.verify_recorded:
        card = verify_recorded()
        print(
            json.dumps(
                {"verified": True, "experiment_rerun": False, "run_card": card},
                indent=2,
                allow_nan=False,
            )
        )
        return
    if REPORT.exists() or CARD.exists() or (WORK / "started.json").exists():
        raise SystemExit("TNR1 already attempted; no reruns or tuning. Use --verify-recorded.")
    started = time.monotonic()
    with rasterio.open(TEMPLATE) as ds:
        fp = np.isfinite(ds.read(1))
    with rasterio.open(ROOT / "data/bridge/labels.tif") as ds:
        catalogue = fp & (ds.read(1) > 0)
    fp_ids = np.flatnonzero(fp)
    registry = json.loads(REGISTRY.read_text())
    for row in registry["unique_rasters"]:
        if sha256_file(ROOT / safe_relative(row["cache_path"])) != row["sha256"]:
            raise ValueError("Registry bytes unavailable/changed before experiment")
    preparation = json.loads((ROOT / "data/prepared/features.json").read_text())
    stack_path = ROOT / "data/prepared/features.npy"
    if sha256_file(stack_path) != preparation["sha256"] or preparation["base_count"] != 27:
        raise ValueError("Cached stack identity changed")
    for path, digest in preparation["inputs"].items():
        if sha256_file(ROOT / safe_relative(path)) != digest:
            raise ValueError("Prepared-stack parent changed")
    context = holdout.SegmentHoldout(fp, catalogue, buffer_px=15)
    surfaces, support, input_hashes = build_engineered_features(fp)
    engineered = np.column_stack([surfaces[name][fp] for name in ENGINEERED_NAMES]).astype(
        np.float32
    )
    stack = np.load(stack_path, mmap_mode="r")
    names = preparation["names"][:27] + list(ENGINEERED_NAMES)
    nuisance, nuisance_names, nuisance_provenance = load_nuisance_matrix(fp)
    if nuisance_names != ["road_m", "claim_m", "block_1", "block_2", "block_3", "block_4"]:
        raise ValueError("Only the prescribed nuisance families may enter TNR1")
    if nuisance_provenance.get("missing_required"):
        raise ValueError("Required nuisance source missing")
    execution_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], text=True, cwd=ROOT
    ).strip()
    code_paths = (
        "scripts/run_tnr1_lane.py",
        "scripts/run_hcw_lane.py",
        "src/gems/targeted_residual.py",
        "src/gems/residualize.py",
        "src/gems/sahg1.py",
        "src/gems/holdout.py",
        "src/gems/novelty.py",
        "src/gems/emission.py",
        "src/gems/metric.py",
        "src/gems/submission.py",
        "src/gems/confounds.py",
        "src/gems/c2s2.py",
    )
    code_hashes = {path: sha256_file(ROOT / path) for path in code_paths}
    for path, expected in code_hashes.items():
        committed = subprocess.check_output(["git", "show", f"{execution_commit}:{path}"], cwd=ROOT)
        if hashlib.sha256(committed).hexdigest() != expected:
            raise ValueError("Commit all executed scientific code before running TNR1")
    card = {
        "hypothesis": "H24-TNR1: selective nuisance removal preserves deformation evidence lost by all-channel residualization",
        "mechanism": "31-channel fold-local HGB; training-only residualization of 12 non-topographic/composite channels, 19 terrain/strain channels unchanged; 3-px Poisson emission",
        "named_non_fault_mimic": "Tilted volcanic tuff cuestas and pluvial lake shorelines intersecting mining/access corridors",
        "lane_status": "autonomously selected unassigned research; explicit coordinator method paragraph absent",
        "holdout": None,
        "matched_control_holdout": None,
        "correlation_overlap_vs_registry": {},
        "raster_sha256": None,
        "validator_output": None,
        "submission_name": None,
        "note": "TNR1 targeted non-topographic residualization | research only; DO NOT SUBMIT",
        "verdict": "negative",
        "ok_to_download": False,
        "ok_to_submit": False,
        "submission_authorized": False,
        "organizer_confirmed_score": None,
        "submission_slots_used": 0,
        "experiments_run": 1,
        "candidate_arms": 1,
        "matched_controls": 1,
    }
    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "preregistration": str(PREREG.relative_to(ROOT)),
        "preregistration_commit": PREREG_COMMIT,
        "preregistration_sha256": sha256_file(PREREG),
        "execution_commit": execution_commit,
        "code_sha256": code_hashes,
        "inputs": {**input_hashes, str(REGISTRY.relative_to(ROOT)): sha256_file(REGISTRY)},
        "registry_scope": registry["scope"],
        "registry_unique_rasters": len(registry["unique_rasters"]),
        "model_columns": names,
        "hgb_parameters": HGB_PARAMS,
        "nuisance_provenance": nuisance_provenance,
        "support_pixels": int(support.sum()),
        "prediction_inputs_include_prior_submission_pixels": False,
        "fixed_physical_feature_preprocessing": "SAHG1 label-free survey-wide robust sigmoid is transductive, not newly train-only calibrated",
        "training_folds": [],
        "maximum_experiments": 3,
        "maximum_session_seconds": 7200,
    }
    save(
        WORK / "started.json",
        {"execution_commit": execution_commit, "started_utc": report["generated_utc"]},
    )

    def finish(reason):
        card["stopped_reason"] = reason
        report["elapsed_seconds"] = time.monotonic() - started
        report["run_card"] = card
        save(CARD, card)
        save(REPORT, report)
        save(ROOT / "docs/data/tnr1_run_card.json", card)
        if card["submission_name"]:
            path = ROOT / "docs/downloads" / card["submission_name"]
            save(
                path.with_suffix(".preflight.json"),
                preflight(
                    path,
                    TEMPLATE,
                    run_card_path=CARD,
                    expected_template_sha256=sha256_file(TEMPLATE),
                ),
            )
        print(json.dumps(card, indent=2, allow_nan=False), flush=True)

    def timed_out():
        return time.monotonic() - started >= 7200

    try:
        print(
            "1. Shared per-feature leakage canaries; raw inputs, missingness, support and physical factors",
            flush=True,
        )

        def raw_vectors(stack, engineered, surfaces):
            for i, name in enumerate(names):
                values = stack[:, i] if i < 27 else engineered[:, i - 27]
                yield "input/" + name, values
                if not np.isfinite(values).all():
                    yield "missingness/" + name, np.isfinite(values).astype(np.float32)
            for name, surface in surfaces.items():
                yield "physical_factor/" + name, surface[fp]
            yield "verified_9x9_support", support[fp].astype(np.float32)

        card["raw_feature_canary"] = batches_canary(
            context, raw_vectors(stack, engineered, surfaces), fp_ids
        )
        del surfaces
        gc.collect()
        if not card["raw_feature_canary"]["passed"]:
            return finish("leakage-canary: raw source/transform; stopped before training")
        if timed_out():
            return finish("time budget before training")
        print("2. Nuisance-only C2ST: training labels first", flush=True)
        label_audit = nuisance_audit(
            "training_labels_first", catalogue, nuisance, nuisance_names, fp_ids, context
        )
        report["label_nuisance_audit"] = label_audit
        oof = np.zeros(fp.shape, np.float32)
        oof_raw = np.zeros(fp.shape, np.float32)
        residual_values = np.lib.format.open_memmap(
            WORK / "oof_residualized_inputs.npy",
            mode="w+",
            dtype=np.float32,
            shape=(len(fp_ids), 12),
        )
        residual_values[:] = np.nan
        print(
            "3. One fixed candidate and raw control, fold-local training/chunked inference",
            flush=True,
        )
        with threadpool_limits(limits=2):
            for fold in context.folds:
                if timed_out():
                    return finish("time budget within OOF training; incomplete experiment")
                if np.isin(
                    context.components[fold["visible"]], fold["hidden_component_ids"]
                ).any() or np.any(fold["train"] & fold["valid"]):
                    raise AssertionError(
                        "Hidden components or validation cells leaked into training"
                    )
                model, raw_model, intervention, training_receipt = fit_models(
                    stack,
                    engineered,
                    nuisance,
                    names,
                    fp_ids,
                    fold["train"],
                    fold["visible"],
                    SEED + int(fold["id"]),
                    control=True,
                )
                valid_ids = np.flatnonzero(fold["valid"].ravel()[fp_ids])
                for start in range(0, len(valid_ids), CHUNK):
                    ids = valid_ids[start : start + CHUNK]
                    values = np.column_stack([stack[ids, :27], engineered[ids]]).astype(np.float32)
                    transformed = intervention.transform(nuisance[ids], values)
                    unchanged = intervention.unchanged_indices
                    if not np.array_equal(
                        values[:, unchanged], transformed[:, unchanged], equal_nan=True
                    ):
                        raise AssertionError("TNR1 altered a protected terrain/strain column")
                    residual_values[ids] = transformed[:, intervention.indices]
                    oof.ravel()[fp_ids[ids]] = model.predict_proba(transformed)[:, 1]
                    oof_raw.ravel()[fp_ids[ids]] = raw_model.predict_proba(values)[:, 1]
                report["training_folds"].append(
                    {
                        "fold": fold["name"],
                        "hidden_components_absent_from_visible": True,
                        **training_receipt,
                    }
                )
                residual_values.flush()
                print(f"   Completed {fold['name']}", flush=True)
                del model, raw_model, intervention
                gc.collect()

        def residual_vectors(residual_values, oof):
            for i, name in enumerate(TargetedResidualizer(names).targets):
                yield "oof_residual/" + name, residual_values[:, i]
            yield "oof_model_surface", oof[fp]

        card["oof_transform_canary"] = batches_canary(
            context, residual_vectors(residual_values, oof), fp_ids
        )
        del residual_values
        if not card["oof_transform_canary"]["passed"]:
            return finish(
                "leakage-canary: OOF residualized input/surface; stopped before placement"
            )
        if timed_out():
            return finish("time budget before final training")
        print(
            "4. Same fixed model refitted on the full visible catalogue; no old predictions read",
            flush=True,
        )
        final_surface = np.zeros(fp.shape, np.float32)
        with threadpool_limits(limits=2):
            model, _, intervention, report["full_catalogue_training"] = fit_models(
                stack,
                engineered,
                nuisance,
                names,
                fp_ids,
                fp,
                catalogue,
                SEED + 4,
                control=False,
            )
            for start in range(0, len(fp_ids), CHUNK):
                ids = np.arange(start, min(start + CHUNK, len(fp_ids)))
                values = np.column_stack([stack[ids, :27], engineered[ids]]).astype(np.float32)
                final_surface.ravel()[fp_ids[ids]] = model.predict_proba(
                    intervention.transform(nuisance[ids], values)
                )[:, 1]
        del model, intervention, stack, engineered
        gc.collect()
        print("5. Literal all-entry continuous-surface check BEFORE any placement", flush=True)
        before = novelty.compare_registry(final_surface, fp, registry["unique_rasters"], ROOT)
        card["correlation_overlap_vs_registry"]["surface_before_placement"] = before
        if not before["passed"]:
            return finish("duplicate-surface: literal gate; no dots or TIFF generated")
        if timed_out():
            return finish("time budget before placement")
        print(
            "6. Shared pooled HOLDOUT-DTI, bootstrap CI and paired raw-control comparison",
            flush=True,
        )
        predictions, controls = [], []
        for fold in context.folds:
            eligible = support & fold["valid"] & ~fold["visible"]
            budget = round(BUDGET * int(fold["valid"].sum()))
            predictions.append(emission.priority_poisson(oof, eligible, budget, min_dist=3))
            controls.append(emission.priority_poisson(oof_raw, eligible, budget, min_dist=3))
        card["holdout"] = context.summarize(predictions)
        card["matched_control_holdout"] = context.summarize(controls)
        card["paired_comparison"] = context.compare_paired(predictions, controls, seed=SEED)
        comparisons = {}
        for key, file, field in (
            ("recorded_current_highest_gvc1", "evidence/gvc1_run_card_20261025.json", "holdout"),
            (
                "recorded_oof_multiphysics_baseline",
                "evidence/sahg1_run_card_20261025.json",
                "reconstructed_oof_multiphysics_baseline",
            ),
        ):
            result = json.loads((ROOT / file).read_text())[field]
            comparable = (
                result["protocol"] == card["holdout"]["protocol"]
                and result["evaluator_version"] == card["holdout"]["evaluator_version"]
                and result["n_withheld_positive_pixels"]
                == card["holdout"]["n_withheld_positive_pixels"]
            )
            comparisons[key] = {
                "label": "HOLDOUT-DTI",
                "source": file,
                "source_sha256": sha256_file(ROOT / file),
                "holdout": result,
                "same_declared_protocol": comparable,
                "baseline_replayed_this_session": False,
                "candidate_point_estimate_higher": comparable
                and card["holdout"]["dti"] > result["dti"],
                "paired_best_model_replay_available": False,
            }
        card["recorded_baseline_comparisons"] = comparisons
        del predictions, controls, oof, oof_raw
        gc.collect()
        if timed_out():
            return finish("time budget before final placement")
        final = emission.priority_poisson(
            final_surface, support & fp & ~catalogue, round(BUDGET * int(fp.sum())), min_dist=3
        )
        content = submission.scored_content_id(final, fp, catalogue)
        name = f"gems24-tnr1-{content}-20261026-RESEARCH-NOT-SUBMISSION-zeros.tif"
        path = ROOT / "docs/downloads" / name
        twin_path = path.with_name(name.replace("-zeros.tif", "-nan.tif"))
        submission.write_submission(final, TEMPLATE, path, outside="zero")
        submission.write_submission(final, TEMPLATE, twin_path, outside="nan")
        card.update(
            submission_name=name,
            raster_sha256=sha256_file(path),
            validator_output=submission.check_variants(path, TEMPLATE),
            note=f"TNR1 selective survey/access residuals; terrain intact | id {content} | research; DO NOT SUBMIT",
        )
        card["nan_outside_companion"] = {
            "file": twin_path.name,
            "validator_output": submission.check_variants(twin_path, TEMPLATE),
        }
        path.with_suffix(".note.txt").write_text(card["note"] + "\n")
        card["ok_to_download"] = (
            card["validator_output"]["format_valid"]
            and card["validator_output"]["checks"]["variant_strict_whole_array_no_nan_allowed"][
                "pass"
            ]
        )
        if not card["ok_to_download"] or len(card["note"]) > 140:
            return finish("exact-file format/note gate failed")
        print(
            "7. Reopen exact final TIFF for nuisance-only C2ST, before final duplicate stop",
            flush=True,
        )
        with rasterio.open(path) as ds:
            exact_dots = fp & (ds.read(1) > 0)
        candidate_audit = nuisance_audit(
            name, exact_dots, nuisance, nuisance_names, fp_ids, context
        )
        adjusted = c2s2.holm_adjust([label_audit["p_value"], candidate_audit["p_value"]])
        for result, p_value in zip((label_audit, candidate_audit), adjusted):
            result["holm_p_value"] = p_value
            result["strict_gate_flagged"] = bool(
                p_value <= 0.05
                and result["observed_auc"] >= 0.55
                and result["margin_vs_p95"] >= 0.02
            )
        card["exact_file_nuisance_audit"] = {
            "labels_first": label_audit,
            "candidate": candidate_audit,
            "candidate_sha256": sha256_file(path),
            "passed": not candidate_audit["strict_gate_flagged"],
            "block_boundary_status": "derived_audited_not_official_coordinates",
            "interpretation": "Association test only; non-rejection does not certify unbiased geological discovery",
        }
        print(
            "8. Exact final-dot registry check; stop immediately on any literal duplicate",
            flush=True,
        )
        after = novelty.compare_registry(
            final.astype(np.float32), fp, registry["unique_rasters"], ROOT, dots=final
        )
        card["correlation_overlap_vs_registry"]["final_dots"] = after
        if not after["passed"]:
            return finish(
                "duplicate-final-dots: stopped with unchanged negative research TIFF; no tuning or slot selection"
            )
        return finish(
            "research complete; assignment, independent current-best replay and selector/current quota evidence absent"
        )
    except Exception as exc:
        finish(f"execution failure; no retry: {type(exc).__name__}: {exc}")
        raise


if __name__ == "__main__":
    main()
