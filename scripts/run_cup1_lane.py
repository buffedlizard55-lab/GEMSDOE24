#!/usr/bin/env python3
"""Execute the preregistered H24-CUP1 experiment (knowledge/20_*, 2026-10-26).

Reuses shared tools only: ``SegmentHoldout`` (gems-segment-pooled-v1),
``gems.gvc.fit_predict_calibrated_hgb`` / ``submodular_dti_allocate``,
``gems.novelty``, ``gems.c2s2`` and ``scripts/submission_writer.py``.
Arms: B-GVC (base30+GVC18 matched baseline) vs E-CUP (base30+GVC18+CUP16).
Writes evidence/cup1_experiment_20261026.json + evidence/cup1_run_card_20261026.json
and a first-screen research TIFF under docs/downloads/. Never uploads anything.
"""

from __future__ import annotations

import gc
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
import run_gvc1_pipeline as gpipe  # noqa: E402  (shared helpers; GVC1 itself not rerun)

from gems import cup, footprint, gvc, holdout, novelty, submission  # noqa: E402
from gems.metric import dti_score_fast  # noqa: E402
from gems.validator import sha256_file  # noqa: E402

WORK = ROOT / "data/work_cup1"
EXPERIMENT_JSON = ROOT / "evidence/cup1_experiment_20261026.json"
RUN_CARD_JSON = ROOT / "evidence/cup1_run_card_20261026.json"
C2ST_JSON = ROOT / "evidence/cup1_c2st_audit_20261026.json"
DOWNLOAD_JSON = ROOT / "docs/data/cup1_download.json"
PREREG_PATH = ROOT / "knowledge/20_preregistered_CUP1_2026-10-26.md"
PREREG_COMMIT = "3c441c5"
FULL_DOT_BUDGET = 37654
SEED = 20261026
RECORDED_BEST_HOLDOUT = 0.14876  # frozen GVC1 receipt, gems-segment-pooled-v1


def _save_json(obj: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n")


def _combine_extra(gvc_mm, cup_mm, out_path: Path) -> np.ndarray:
    if out_path.exists():
        mm = np.load(out_path, mmap_mode="r")
        if mm.shape == (gvc_mm.shape[0], gvc_mm.shape[1] + cup_mm.shape[1]):
            return mm
    mm = np.lib.format.open_memmap(
        out_path, mode="w+", dtype=np.float32,
        shape=(gvc_mm.shape[0], gvc_mm.shape[1] + cup_mm.shape[1]),
    )
    for s in range(0, gvc_mm.shape[0], 500_000):
        e = min(s + 500_000, gvc_mm.shape[0])
        mm[s:e, : gvc_mm.shape[1]] = gvc_mm[s:e]
        mm[s:e, gvc_mm.shape[1]:] = cup_mm[s:e]
    mm.flush()
    del mm
    return np.load(out_path, mmap_mode="r")


def _batched_canary(context, fp, stacks: list[tuple[np.ndarray, list[str]]]) -> dict[str, Any]:
    fp_ids = np.flatnonzero(fp.ravel())
    specs = [(n, si, c) for si, (_, names) in enumerate(stacks) for c, n in enumerate(names)]
    merged: dict[str, Any] = {}
    template: dict[str, Any] = {}
    for start in range(0, len(specs), 8):
        fdict: dict[str, np.ndarray] = {}
        for name, si, col in specs[start:start + 8]:
            grid = np.full(fp.shape, np.nan, dtype=np.float32)
            grid.ravel()[fp_ids] = stacks[si][0][:, col]
            fdict[name] = grid
        res = context.canary(fdict, seed=SEED, max_per_class=15000)
        if not template:
            template = {k: v for k, v in res.items() if k != "features"}
        merged.update(res["features"])
        del fdict
        gc.collect()
    template["passed"] = not any(v["leakage_suspected"] for v in merged.values())
    template["features"] = merged
    return template


def _registry_entries(fp: np.ndarray) -> list[dict[str, Any]]:
    entries = list(json.loads((ROOT / "registry/priority_rasters.json").read_text())["unique_rasters"])
    seen = {e["footprint_sha256"] for e in entries}
    for p in sorted((ROOT / "docs/downloads").glob("*.tif")):
        with rasterio.open(p) as ds:
            if ds.shape != fp.shape:
                continue
            a = ds.read(1)
        fp_sha = hashlib.sha256(np.asarray(a[fp], dtype="<f4").tobytes()).hexdigest()
        if fp_sha in seen:
            continue
        seen.add(fp_sha)
        entries.append({
            "id": f"local-{p.stem[:40]}",
            "file": str(p.relative_to(ROOT)),
            "cache_path": str(p.relative_to(ROOT)),
            "footprint_sha256": fp_sha,
        })
    return entries


def _sgmc_sparse(dots: np.ndarray, fp, catalogue) -> float:
    with rasterio.open(ROOT / "data/external/derived_sgmc_faults_100m_u8.tif") as ds:
        sgmc = (ds.read(1) > 0) & fp
    truth = sgmc & ~catalogue & (distance_transform_edt(~catalogue) > 10)
    return float(dti_score_fast(dots > 0.5, truth, valid_mask=fp, catalogue_mask=catalogue)["dti"])


def main() -> None:
    if EXPERIMENT_JSON.exists():
        raise SystemExit("CUP1 experiment already recorded; no implicit rerun.")
    t0 = time.monotonic()
    WORK.mkdir(parents=True, exist_ok=True)
    fp = footprint.load_footprint()
    template = ROOT / "data/bridge/sample_submission.tif"
    with rasterio.open(template) as t_ds:
        transform = t_ds.transform
    with rasterio.open(ROOT / "data/bridge/labels.tif") as l_ds:
        catalogue = (l_ds.read(1) > 0) & fp

    meta = json.loads((ROOT / "data/prepared/features.json").read_text())
    base_npy = ROOT / "data/prepared/features.npy"
    if sha256_file(base_npy) != meta["sha256"]:
        raise SystemExit("Prepared feature-stack SHA-256 mismatch")
    base_mm = np.load(base_npy, mmap_mode="r")
    base_names = list(meta["names"])

    print("[1/6] Building GVC18 (shared) + CUP16 features...", flush=True)
    gvc_npy = WORK / "gvc1_features.npy"
    if gvc_npy.exists() and np.load(gvc_npy, mmap_mode="r").shape == (int(fp.sum()), 18):
        gvc_mm = np.load(gvc_npy, mmap_mode="r")
        gvc_names = list(gvc.GVC1_FEATURE_NAMES)
    else:
        _, gvc_names = gvc.build_gvc1_features(ROOT, base_mm, base_names, fp, transform, gvc_npy)
        gvc_mm = np.load(gvc_npy, mmap_mode="r")
    cup_npy = WORK / "cup1_features.npy"
    if cup_npy.exists() and np.load(cup_npy, mmap_mode="r").shape == (int(fp.sum()), 16):
        cup_mm = np.load(cup_npy, mmap_mode="r")
        cup_names = list(cup.CUP_FEATURE_NAMES)
    else:
        _, cup_names = cup.build_cup_features(ROOT, base_mm, base_names, fp, cup_npy)
        cup_mm = np.load(cup_npy, mmap_mode="r")
    extra_mm = _combine_extra(gvc_mm, cup_mm, WORK / "extra_gvc_cup.npy")
    c2st_feats, _nuis_mm, nuis_prov = gpipe._load_verified_nuisance(ROOT, fp, WORK)

    ckpt_path = WORK / "stage_a_checkpoint.json"
    dots_cup_npy, dots_bgvc_npy = WORK / "full_dots_cup.npy", WORK / "full_dots_bgvc.npy"
    if ckpt_path.exists() and dots_cup_npy.exists() and dots_bgvc_npy.exists():
        print("[2-4/6] Loading stage-A checkpoint...", flush=True)
        ck = json.loads(ckpt_path.read_text())
        canary, sum_b, sum_e, paired = ck["canary"], ck["sum_bgvc"], ck["sum_cup"], ck["paired"]
        nov_surf, nov_dots, fold_meta = ck["nov_surf"], ck["nov_dots"], ck["fold_meta"]
        full_meta = ck["full_meta"]
        stage_a_elapsed = float(ck["elapsed"])
        full_dots = np.load(dots_cup_npy)
        full_dots_b = np.load(dots_bgvc_npy)
    else:
        context = holdout.SegmentHoldout(fp, catalogue, buffer_px=15)
        print("[2/6] Leakage canary (base30+GVC18+CUP16, two polarities)...", flush=True)
        canary = _batched_canary(context, fp, [(base_mm, base_names), (gvc_mm, gvc_names), (cup_mm, cup_names)])
        aucs = [v["pooled_auc"] for v in canary["features"].values()]
        print(f"      passed={canary['passed']} AUC range=[{min(aucs):.4f},{max(aucs):.4f}]", flush=True)
        if not canary["passed"]:
            raise SystemExit("Leakage canary >0.90; halting without fitting")

        print("[3/6] 4-fold SegmentHoldout: B-GVC vs E-CUP...", flush=True)
        total_offcat = int((fp & ~catalogue).sum())
        preds_b, preds_e, fold_meta = [], [], []
        for f in context.folds:
            fid, fname = int(f["id"]), f["name"]
            k_fold = int(round(FULL_DOT_BUDGET * int((f["valid"] & ~f["visible"]).sum()) / total_offcat))
            t_f = time.monotonic()
            surf_b, m_b = gvc.fit_predict_calibrated_hgb(base_mm, gvc_mm, None,
                train_mask=f["train"], visible_mask=f["visible"], predict_mask=f["valid"],
                footprint=fp, seed=SEED + fid, residualize=False)
            p_b = gvc.submodular_dti_allocate(surf_b, f["valid"], f["visible"], budget=k_fold,
                min_spacing_px=2.5, catalogue_clearance_px=2.0)
            del surf_b
            gc.collect()
            surf_e, m_e = gvc.fit_predict_calibrated_hgb(base_mm, extra_mm, None,
                train_mask=f["train"], visible_mask=f["visible"], predict_mask=f["valid"],
                footprint=fp, seed=SEED + fid, residualize=False)
            p_e = gvc.submodular_dti_allocate(surf_e, f["valid"], f["visible"], budget=k_fold,
                min_spacing_px=2.5, catalogue_clearance_px=2.0)
            del surf_e
            gc.collect()
            preds_b.append(p_b)
            preds_e.append(p_e)
            s_b, _ = context.score_fold(p_b, f)
            s_e, _ = context.score_fold(p_e, f)
            print(f"      {fname:<18} k={k_fold:,} B-GVC={s_b['dti']:.5f} E-CUP={s_e['dti']:.5f} ({time.monotonic()-t_f:.0f}s)", flush=True)
            fold_meta.append({"fold": fname, "k_fold_budget": k_fold, "bgvc": m_b, "cup": m_e})
        sum_b = context.summarize(preds_b, ci_draws=1999)
        sum_e = context.summarize(preds_e, ci_draws=1999)
        paired = context.compare_paired(preds_e, preds_b, ci_draws=1999, seed=SEED)
        print(f"      POOLED B-GVC={sum_b['dti']:.5f} E-CUP={sum_e['dti']:.5f} paired d={paired['paired_delta_dti']:+.5f} CI={paired['paired_delta_ci95']}", flush=True)
        del preds_b, preds_e
        gc.collect()

        print("[4/6] Full-footprint fits + novelty (surface & final dots)...", flush=True)
        full_surf_b, full_meta_b = gvc.fit_predict_calibrated_hgb(base_mm, gvc_mm, None,
            train_mask=fp, visible_mask=catalogue, predict_mask=fp, footprint=fp,
            seed=SEED + 99, residualize=False)
        full_dots_b = gvc.submodular_dti_allocate(full_surf_b, fp, catalogue, budget=FULL_DOT_BUDGET,
            min_spacing_px=2.5, catalogue_clearance_px=2.0)
        del full_surf_b
        gc.collect()
        full_surf, full_meta_e = gvc.fit_predict_calibrated_hgb(base_mm, extra_mm, None,
            train_mask=fp, visible_mask=catalogue, predict_mask=fp, footprint=fp,
            seed=SEED + 99, residualize=False)
        full_dots = gvc.submodular_dti_allocate(full_surf, fp, catalogue, budget=FULL_DOT_BUDGET,
            min_spacing_px=2.5, catalogue_clearance_px=2.0)
        entries = _registry_entries(fp)
        nov_surf = novelty.compare_prospective_registry(full_surf, fp, entries, ROOT)
        nov_dots = novelty.compare_prospective_registry(full_dots, fp, entries, ROOT, dots=(full_dots > 0.5))
        print(f"      novelty: surf method_pass={nov_surf['method_lane_passed']} | dots method_pass={nov_dots['method_lane_passed']} max_ov={nov_dots['method_lane_max_dot_overlap']}", flush=True)
        del full_surf
        gc.collect()
        full_meta = {"bgvc": full_meta_b, "cup": full_meta_e}
        np.save(dots_cup_npy, full_dots)
        np.save(dots_bgvc_npy, full_dots_b)
        stage_a_elapsed = time.monotonic() - t0
        _save_json({"canary": canary, "sum_bgvc": sum_b, "sum_cup": sum_e, "paired": paired,
                    "nov_surf": nov_surf, "nov_dots": nov_dots, "fold_meta": fold_meta,
                    "full_meta": full_meta, "elapsed": stage_a_elapsed}, ckpt_path)

    print("[5/6] SGMC sparse diagnostic + exact-file C2ST...", flush=True)
    sgmc = {"cup1": _sgmc_sparse(full_dots, fp, catalogue),
            "bgvc_matched": _sgmc_sparse(full_dots_b, fp, catalogue)}
    gvc1_tif = ROOT / "docs/downloads/gems24-gvc1-negative-geothermal-lineament-submod-20261025-abe8e51c719d-zeros.tif"
    if gvc1_tif.exists():
        with rasterio.open(gvc1_tif) as ds:
            sgmc["gvc1_frozen_file"] = _sgmc_sparse(ds.read(1), fp, catalogue)
    tmp_tif = WORK / "cup1_zeros.tif"
    gpipe._write_via_shared_cli(full_dots, tmp_tif, template, "zero", WORK / "cup1_tmp.npy")
    c2st_report = gpipe._run_c2st_family(fp, c2st_feats, nuis_prov,
        [("labels", ROOT / "data/bridge/labels.tif"), ("cup1", tmp_tif)])
    _save_json(c2st_report, C2ST_JSON)
    c2st_ref = c2st_report["references"]["cup1"]
    c2st_ok = bool(c2st_ref["strict_c2st_gate_passed"])
    print(f"      SGMC={sgmc} C2ST pass={c2st_ok} AUC={c2st_ref['primary']['observed_auc']:.4f}", flush=True)

    print("[6/6] Packaging via shared submission_writer.py...", flush=True)
    nov_ok = bool(nov_surf["method_lane_passed"] and nov_dots["method_lane_passed"])
    paired_ok = bool(paired["ci95_strictly_positive"])
    beat_best = bool(sum_e["dti"] > RECORDED_BEST_HOLDOUT)
    slug = "cup1-compfront-upcont-submod" if nov_ok else "cup1-negative-compfront-upcont-submod"
    content_id = submission.scored_content_id(full_dots, fp, catalogue)
    downloads = ROOT / "docs/downloads"
    zeros_name = submission.make_filename("gems24", slug, "20261026", content_id, "zeros")
    nan_name = submission.make_filename("gems24", slug, "20261026", content_id, "nan")
    zeros_path, nan_path = downloads / zeros_name, downloads / nan_name
    chk_zeros = gpipe._write_via_shared_cli(full_dots, zeros_path, template, "zero", WORK / "f_z.npy")
    chk_nan = gpipe._write_via_shared_cli(full_dots, nan_path, template, "nan", WORK / "f_n.npy")
    if not (chk_zeros["format_valid"] and chk_nan["format_valid"]):
        raise SystemExit("Exact-file format validator failed")
    zip_path = submission.zip_single(zeros_path, downloads / zeros_name.replace(".tif", ".zip"))

    technical = {
        "format_and_unit_range_valid": bool(chk_zeros["format_valid"] and chk_nan["format_valid"]),
        "leakage_canary_passed": bool(canary["passed"]),
        "paired_cup_minus_bgvc_ci95_gt_0": paired_ok,
        "pooled_holdout_beats_recorded_best_0.14876": beat_best,
        "competing_method_uniqueness_passed": nov_ok,
        "strict_c2st_nuisance_audit_passed": c2st_ok,
    }
    governance = {
        "literal_all_entries_uniqueness_incl_spacing5_lattice": bool(
            nov_surf["literal_all_entries_passed"] and nov_dots["literal_all_entries_passed"]),
        "assigned_coordinator_lane_present": False,
        "independent_selector_quota_certificate_implemented": False,
    }
    selector_eligible = all(technical.values())
    verdict = "promote" if selector_eligible else "negative"
    reasons = [f"Technical gate failed: {k}" for k, v in technical.items() if not v]
    if not nov_ok:
        top = max((r for r in nov_dots["rows"] if r.get("entry_role") == "competing_method_lane"),
                  key=lambda r: r["candidate_dot_overlap_within_3px"] or 0.0, default=None)
        if top:
            reasons.append(f"Max competing 3px overlap {top['candidate_dot_overlap_within_3px']:.4f} vs {top['registry_id']} ({top['file']})")
    reasons.append("Separate selector/quota certificate not implemented; weekly cap unknown (no slot is spent by this session).")

    if selector_eligible:
        note = f"GEMS24 CUP1 | comp-front+upcont persist submod 37.7k | gates PASS selector-eligible | id {content_id}"
    else:
        note = f"GEMS24 CUP1 | comp-front+upcont submod | NEGATIVE gate stop; DO NOT SUBMIT | id {content_id}"
    assert len(note) <= 140, len(note)
    (downloads / f"note-{zeros_name[:-4]}.txt").write_text(note + "\n")
    _save_json({"zero_outside": chk_zeros, "nan_outside": chk_nan,
                "zeros_zip_file": zip_path.name, "zeros_zip_sha256": sha256_file(zip_path)},
               downloads / f"checks-{zeros_name[:-4]}.json")

    def _slim(n):
        rows = sorted(n["rows"], key=lambda r: (r["candidate_dot_overlap_within_3px"]
                        if r["candidate_dot_overlap_within_3px"] is not None else abs(r["raw_spearman"] or 0)), reverse=True)[:10]
        out = {k: v for k, v in n.items() if k not in ("rows", "calibration_control_rows")}
        out["top_comparators"] = rows
        return out

    elapsed = round(stage_a_elapsed + (time.monotonic() - t0 - stage_a_elapsed), 2) if False else round(time.monotonic() - t0, 2)
    experiment = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "hypothesis": "H24-CUP1",
        "preregistration": str(PREREG_PATH.relative_to(ROOT)),
        "preregistration_commit": PREREG_COMMIT,
        "preregistration_sha256": sha256_file(PREREG_PATH),
        "experiments_executed": 1, "maximum_experiments_budget": 3, "elapsed_seconds": elapsed,
        "environment": {k: version(k) for k in ("numpy", "scipy", "scikit-learn", "rasterio")},
        "prediction_inputs_include_registry_rasters": False,
        "feature_names_base_30": base_names, "feature_names_gvc_18": gvc_names, "feature_names_cup_16": cup_names,
        "canary": canary, "fold_fit_metadata": fold_meta, "full_fit_metadata": full_meta,
        "holdout_results": {"B_GVC_matched": sum_b, "E_CUP1": sum_e},
        "paired_cup_minus_bgvc": paired,
        "recorded_current_best_holdout_dti": RECORDED_BEST_HOLDOUT,
        "sgmc_sparse_diagnostic_not_a_gate": sgmc,
        "novelty": {"surface_before_placement": _slim(nov_surf), "final_dots": _slim(nov_dots)},
        "c2st_audit_file": str(C2ST_JSON.relative_to(ROOT)),
        "technical_gates": technical, "governance_gates": governance,
        "selector_eligible_all_technical_gates": selector_eligible,
    }
    _save_json(experiment, EXPERIMENT_JSON)

    card = {
        "hypothesis": "H24-CUP1: multi-scale K/Th/U compositional ratio-grid fronts + RTP-to-TMI_up150 paired-trough persistence, as learned HGB channels on base30+GVC18, emitted by the shared 300 m submodular allocator (37,654 dots, 2.5 px spacing, 2 px catalogue clearance)",
        "mechanism": "Hydrothermal K-metasomatism/U remobilisation along blind faults creates narrow compositional fronts cross-cutting lithology; deep-seated demagnetised fault zones persist under 150 m upward continuation while surficial noise attenuates. Neither needs a scarp or catalogue tip.",
        "named_non_fault_mimic": "Transported arkosic sediment front / lithologic contact (radiometrics); magnetite-poor palaeochannel persisting with depth (magnetics)",
        "holdout_dti": {"label": "HOLDOUT-DTI", "evaluator_version": sum_e["evaluator_version"],
                        "dti": sum_e["dti"], "ci95": sum_e["ci95"],
                        "n_withheld_positive_pixels": sum_e["n_withheld_positive_pixels"],
                        "matched_baseline_bgvc_dti": sum_b["dti"],
                        "paired_delta": paired["paired_delta_dti"], "paired_delta_ci95": paired["paired_delta_ci95"],
                        "recorded_current_best": RECORDED_BEST_HOLDOUT},
        "correlation_overlap_vs_registry": {
            "surface_method_lane_max_abs_rho": nov_surf["method_lane_max_abs_rank_correlation"],
            "final_method_lane_max_abs_rho": nov_dots["method_lane_max_abs_rank_correlation"],
            "final_max_competing_overlap_within_3px": nov_dots["method_lane_max_dot_overlap"],
            "method_lane_passed": nov_ok,
            "literal_all_entries_passed": governance["literal_all_entries_uniqueness_incl_spacing5_lattice"]},
        "raster_sha256": sha256_file(zeros_path),
        "nan_companion_sha256": sha256_file(nan_path),
        "validator_output": chk_zeros, "nan_validator_output": chk_nan,
        "c2st_nuisance_audit": {"candidate_auc": c2st_ref["primary"]["observed_auc"],
                                "candidate_holm_p": c2st_ref["primary"].get("holm_p_value"),
                                "strict_c2st_gate_passed": c2st_ok},
        "sgmc_sparse_diagnostic": sgmc,
        "technical_gates": technical, "governance_gates": governance,
        "submission_name": zeros_name, "nan_submission_name": nan_name, "zip_submission_name": zip_path.name,
        "note": note, "note_length": len(note),
        "verdict": verdict,
        "ok_to_download": True,
        "ok_to_submit": False,
        "submit_state": ("SELECTOR-ELIGIBLE: all technical gates PASS; separate selector/quota step still required before any weekly slot"
                         if selector_eligible else "DO_NOT_SUBMIT: automatic gate failure, see reasons"),
        "reasons": reasons,
        "organizer_score": None,
        "score_labelling": "No organizer-confirmed score exists for this artifact; HOLDOUT-DTI is local only, never a leaderboard projection.",
    }
    _save_json(card, RUN_CARD_JSON)
    _save_json({**card, "download_path": f"downloads/{zeros_name}", "nan_download_path": f"downloads/{nan_name}",
                "zip_download_path": f"downloads/{zip_path.name}"}, DOWNLOAD_JSON)
    print(json.dumps({"verdict": verdict, "holdout_dti": sum_e["dti"], "file": zeros_name,
                      "sha256": card["raster_sha256"], "note": note}, indent=2), flush=True)


if __name__ == "__main__":
    main()
