#!/usr/bin/env python3
"""Execute or verify the preregistered H24-DRAIN5 drainage-network lane.

Spec locked before implementation in ``knowledge/26_preregistered_DRAIN5_2026-10-26.md``:

- Adds 7 label-free D8 drainage-network channels (flow accumulation, normalised
  channel steepness k_sn, downstream knickpoint jump, knickpoint co-linearity,
  channel distance, HAND, flow-azimuth bend; ``gems.drainage``, input ``det_elev``
  only) to the proven 52-channel DPRF1 stack = 59 channels, reusing the shared
  ``gems.dprf1`` fold fitter (stratified ``d_vis >= 3 px`` negatives, selective
  residualization, relief-conditioned calibration, ridge sharpening), the shared
  ``gems.holdout.SegmentHoldout`` evaluator, ``gems.submission`` writer,
  ``gems.novelty``, ``gems.c2s2`` and ``gems.selector`` v2. No private forks.
  Drainage channels are terrain-derived and are NOT selectively residualized.
- 3 locked arms on ``gems-segment-pooled-v1`` (60,988 withheld positives):
  Arm 1 DRAIN5-primary (59ch, drainage-gated Regime B), Arm 2 DRAIN5-noDrain
  (exact 52ch DPRF1 replay ablation), Arm 3 DRAIN5-channelsOnly (59ch, legacy
  Regime B).
- Full-footprint export is Arm 1 only, Dual-Partition Stitched-OOF + apron debiasing,
  budget fixed in advance at 37,654 dots. Zero prior submission pixels are read by
  the detector; registry rasters are read only by the novelty audit.
- Never contacts DrivenData; never spends a weekly submission slot. The selector
  v2 receipt is computed on the exact bytes and is fail-closed by construction.
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import os
import resource
import struct
import subprocess
import sys
import time
import zipfile
import zlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import numpy as np  # noqa: E402
import rasterio  # noqa: E402
from scipy.ndimage import distance_transform_edt  # noqa: E402
from scipy.stats import rankdata  # noqa: E402

from gems import (  # noqa: E402
    c2s2,
    confounds,
    dprf1,
    drainage,
    footprint,
    gvc,
    holdout,
    novelty,
    selector,
    submission,
)
from gems.validator import sha256_file  # noqa: E402

SEED = 20261026
GVC_BASE_SEED = 20261025
FULL_DOT_BUDGET = 37654
PREREG_PATH = "knowledge/26_preregistered_DRAIN5_2026-10-26.md"
PREREG_COMMIT = "3739d7daeeccb5fbca9a925c753f5883b2d18313"

GVC_MEMMAP = ROOT / "data/prepared/gvc1_features.npy"
SAHG4_MEMMAP = ROOT / "data/prepared/sahg4_features.npy"
DRAINAGE_MEMMAP = ROOT / "data/prepared/drainage7_features.npy"
EXPERIMENT_JSON = ROOT / "evidence/drain5_experiment_20261026.json"
RUN_CARD_JSON = ROOT / "evidence/drain5_run_card_20261026.json"
SELECTOR_JSON = ROOT / "evidence/drain5_selector_20261026.json"
DOCS_RUN_CARD_JSON = ROOT / "docs/data/drain5_run_card.json"
DOCS_SELECTOR_JSON = ROOT / "docs/data/drain5_selector.json"
DOCS_DOWNLOAD_JSON = ROOT / "docs/data/drain5_download.json"
PREVIEW_PNG = ROOT / "docs/assets/drain5-preview.png"

RECORDED_DPRF1_DTI = 0.1637924246971501


def save_json(obj: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n")


def peak_rss_mib() -> float:
    return float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) / 1024.0


def strict_whole_array_ok(check_dict: dict[str, Any]) -> bool:
    return bool(
        check_dict.get("checks", {})
        .get("variant_strict_whole_array_no_nan_allowed", {})
        .get("pass")
    )


def _png_chunk(tag: bytes, data: bytes) -> bytes:
    crc = zlib.crc32(tag + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)


def write_preview(dots: np.ndarray, fp: np.ndarray, out_path: Path, step: int = 6) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    h, w = fp.shape
    sh, sw = h // step, w // step
    fp_small = fp[: sh * step, : sw * step].reshape(sh, step, sw, step).any(axis=(1, 3))
    d_small = dots[: sh * step, : sw * step].reshape(sh, step, sw, step).any(axis=(1, 3))
    rgb = np.full((sh, sw, 3), (244, 241, 234), dtype=np.uint8)
    rgb[fp_small] = (224, 232, 226)
    rgb[d_small] = (180, 83, 9)
    raw = b"".join(b"\x00" + rgb[y].tobytes() for y in range(sh))
    ihdr = struct.pack(">IIBBBBB", sw, sh, 8, 2, 0, 0, 0)
    png = (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", ihdr)
        + _png_chunk(b"IDAT", zlib.compress(raw, level=9))
        + _png_chunk(b"IEND", b"")
    )
    out_path.write_bytes(png)


def run_batched_canary(
    context: holdout.SegmentHoldout,
    fp: np.ndarray,
    sources: list[tuple[str, np.ndarray, list[str]]],
    *,
    batch_size: int = 4,
) -> dict[str, Any]:
    """Two-polarity single-feature canary over every channel of every memmap source."""
    fp_ids = np.flatnonzero(fp.ravel())
    specs: list[tuple[str, int, int]] = []  # (feature name, source index, column)
    for si, (_src_name, _mm, names) in enumerate(sources):
        for col, name in enumerate(names):
            specs.append((name, si, col))
    merged: dict[str, Any] = {}
    last_meta: dict[str, Any] = {}
    for start in range(0, len(specs), batch_size):
        batch = specs[start : start + batch_size]
        fdict: dict[str, np.ndarray] = {}
        for name, si, col in batch:
            grid = np.full(fp.shape, np.nan, dtype=np.float32)
            grid.ravel()[fp_ids] = sources[si][1][:, col]
            fdict[name] = grid
        rep = context.canary(fdict, seed=GVC_BASE_SEED, max_per_class=15000)
        merged.update(rep["features"])
        last_meta = rep
        del fdict
        gc.collect()
    passed = not any(v["leakage_suspected"] for v in merged.values())
    worst_name = max(
        merged, key=lambda k: max(merged[k]["pooled_auc"], 1.0 - merged[k]["pooled_auc"])
    )
    worst_auc = merged[worst_name]["pooled_auc"]
    drn_rows = {k: v["pooled_auc"] for k, v in merged.items() if k.startswith("drn_")}
    return {
        "diagnostic": last_meta["diagnostic"],
        "evaluator_version": last_meta["evaluator_version"],
        "threshold": last_meta["threshold"],
        "two_polarities_checked": True,
        "passed": passed,
        "n_features_checked": len(merged),
        "worst_feature": worst_name,
        "worst_pooled_auc": worst_auc,
        "worst_polarity_extremity": max(worst_auc, 1.0 - worst_auc),
        "drainage_channel_pooled_aucs": drn_rows,
        "features": merged,
        "interpretation": last_meta["interpretation"],
    }


LOCAL_LANE_CANDIDATES: list[tuple[str, str]] = [
    (
        "local-aspc",
        "docs/downloads/gems24-aspc-20261025-6393e9d9b0df-RESEARCH-NOT-SUBMISSION-zeros.tif",
    ),
    (
        "local-mtr1",
        "docs/downloads/gems24-mtr1-negative-paired-trough-20261025-ed7243e6d163-zeros.tif",
    ),
    (
        "local-sahg1",
        "docs/downloads/gems24-sahg1-strike-hydro-geomorph-20261025-13d01f28d5db-zeros.tif",
    ),
    (
        "local-con",
        "docs/downloads/gems24-con-claycap-strain-saddle-20261025-ded121060878-zeros.tif",
    ),
    (
        "local-unique03",
        "docs/downloads/24gems-doer-fault-guided-k-20261025T220208Z-dedb860f7e83-zeros.tif",
    ),
    ("local-oj1", "docs/downloads/gems24-oj1-3eef450351de-RESEARCH-NOT-SUBMISSION-zeros.tif"),
    ("local-fuse-hcw", "docs/downloads/gems24-fuse-fuse-hcw-hgb-20261025-3fd41218a10a-zeros.tif"),
    ("local-rshg1", "docs/downloads/gems24-rshg1-regime-hydro-hgb-20261025-98f69d77e868-zeros.tif"),
    (
        "local-gvc1",
        "docs/downloads/gems24-gvc1-negative-geothermal-lineament-submod-20261025-abe8e51c719d-zeros.tif",
    ),
    (
        "local-crp1",
        "docs/downloads/gems24-crp1-compfront-xdepth-saddle-20261026-c679a967f700-zeros.tif",
    ),
    (
        "local-cup1",
        "docs/downloads/gems24-cup1-negative-compfront-upcont-submod-20261026-35a808f4514a-zeros.tif",
    ),
    (
        "local-tnr1",
        "docs/downloads/gems24-tnr1-56dfd14b88db-20261026-RESEARCH-NOT-SUBMISSION-zeros.tif",
    ),
    (
        "local-trsg1",
        "docs/downloads/gems24-trsg1-tworegime-seismic-geo-oof-20261026-7f301fc433f0-zeros.tif",
    ),
    (
        "local-dprf1",
        "docs/downloads/gems24-dprf1-stitched-oof-tworegime-20261026-81849d67c8bf-zeros.tif",
    ),
    (
        "local-eul1",
        "docs/downloads/gems24-eul1-negative-euler-contact-20261026-eda170f04847-zeros.tif",
    ),
]


def local_lane_entries(fp: np.ndarray, existing_shas: set[str]) -> list[dict[str, Any]]:
    """All local GEMSDOE24 method-lane GeoTIFFs (incl. DPRF1) for the novelty audit."""
    seen = set(existing_shas)
    out: list[dict[str, Any]] = []
    for eid, rel in LOCAL_LANE_CANDIDATES:
        p = ROOT / rel
        if not p.exists():
            continue
        with rasterio.open(p) as ds:
            a = ds.read(1)
        fp_sha = hashlib.sha256(np.asarray(a[fp], dtype="<f4").tobytes()).hexdigest()
        if fp_sha in seen:
            continue
        seen.add(fp_sha)
        out.append(
            {
                "id": eid,
                "repo": "buffedlizard55-lab/GEMSDOE24",
                "file": rel,
                "cache_path": rel,
                "sha256": sha256_file(p),
                "footprint_sha256": fp_sha,
                "positive_pixels": int((a[fp] > 0).sum()),
            }
        )
    return out


def check_peer_blobs(
    surface: np.ndarray, dots: np.ndarray | None, fp: np.ndarray
) -> dict[str, Any]:
    """Check all competition-grid blobs in registry/peer_rasters_20261025.json."""
    peer_reg = json.loads((ROOT / "registry/peer_rasters_20261025.json").read_text())["entries"]
    blobs: dict[str, dict[str, Any]] = {}
    for row in peer_reg:
        if row.get("role") == "format_demo_not_submission":
            continue
        blobs.setdefault(row["blob"], row)
    surf_ranks = rankdata(surface[fp])
    dot_ranks = rankdata(dots[fp].astype(np.float32)) if dots is not None else None
    max_surf_rho = 0.0
    max_dot_rho = 0.0
    max_overlap = 0.0
    max_overlap_file = None
    checked = 0
    missing = 0
    for row in blobs.values():
        p = ROOT / row["cache_path"]
        if not p.exists():
            missing += 1
            continue
        with rasterio.open(p) as ds:
            if ds.shape != fp.shape:
                continue
            a = ds.read(1)
        checked += 1
        s_rho = novelty.rank_correlation(surf_ranks, a[fp])
        if s_rho is not None:
            max_surf_rho = max(max_surf_rho, abs(float(s_rho)))
        if dots is not None and dot_ranks is not None:
            d_rho = novelty.rank_correlation(dot_ranks, a[fp])
            if d_rho is not None:
                max_dot_rho = max(max_dot_rho, abs(float(d_rho)))
            ov = novelty.dot_overlap(dots > 0.5, fp & np.isfinite(a) & (a > 0))[
                "candidate_within_3px_of_reference"
            ]
            if ov is not None and float(ov) > max_overlap:
                max_overlap = float(ov)
                max_overlap_file = f"{row['repo']}:{row['path']}"
    passed = (
        checked > 0
        and max_surf_rho <= 0.90
        and (dots is None or (max_dot_rho <= 0.90 and max_overlap <= 0.70))
    )
    return {
        "peer_unique_blobs_checked": checked,
        "peer_blobs_missing_from_cache": missing,
        "max_abs_surface_spearman": max_surf_rho,
        "max_abs_dot_spearman": max_dot_rho if dots is not None else None,
        "max_dot_overlap_within_3px": max_overlap if dots is not None else None,
        "max_overlap_peer_artifact": max_overlap_file,
        "passed": passed,
    }


def compute_distance_profile(
    dots_bool: np.ndarray, catalogue: np.ndarray, fp: np.ndarray
) -> dict[str, Any]:
    dist_cat = distance_transform_edt(~catalogue)
    d = dist_cat[dots_bool & fp]
    return {
        "n_dots": int(len(d)),
        "min_dist_px": float(d.min()) if len(d) else None,
        "median_dist_px": float(np.median(d)) if len(d) else None,
        "frac_le_2px": float(np.mean(d <= 2.0)) if len(d) else 0.0,
        "frac_2_to_5px": float(np.mean((d > 2.0) & (d <= 5.0))) if len(d) else 0.0,
        "frac_5_to_9px": float(np.mean((d > 5.0) & (d <= 9.0))) if len(d) else 0.0,
        "frac_2_to_9px_apron": float(np.mean((d > 2.0) & (d <= 9.0))) if len(d) else 0.0,
        "frac_9_to_20px": float(np.mean((d > 9.0) & (d <= 20.0))) if len(d) else 0.0,
        "frac_gt_20px_farfield": float(np.mean(d > 20.0)) if len(d) else 0.0,
    }


def run_exact_file_c2st(
    zeros_tif_path: Path, catalogue: np.ndarray, fp: np.ndarray
) -> dict[str, Any]:
    """Audit labels first, then the exact emitted GeoTIFF on road/claim/4-block confounds."""
    confounds.build_all(force=False)
    with np.load(confounds.CONF / "confounds.npz") as npz:
        cfeat = confounds.classifier_features(npz)
    fold_grid, _ = holdout.make_quadrant_folds(fp)
    label_res = c2s2.c2s2_test(
        "training_labels_first",
        catalogue,
        cfeat,
        fold_grid,
        fp,
        n_per_class=8000,
        n_null=99,
        seed=GVC_BASE_SEED,
    )
    with rasterio.open(zeros_tif_path) as ds:
        cand_mask = (ds.read(1) > 0.5) & fp
    cand_res = c2s2.c2s2_test(
        "h24_drain5_exact_file",
        cand_mask,
        cfeat,
        fold_grid,
        fp,
        n_per_class=8000,
        n_null=99,
        seed=GVC_BASE_SEED,
    )
    adj_p = c2s2.holm_adjust([label_res.p_value, cand_res.p_value])
    flagged = bool(
        adj_p[1] <= 0.05 and cand_res.observed_auc >= 0.55 and cand_res.margin_vs_p95 >= 0.02
    )
    return {
        "method": "Classifier two-sample test (Lopez-Paz & Oquab, ICLR 2017) with 10 km block label swaps",
        "labels_audited_first": True,
        "nuisance_families_only": sorted(cfeat.keys()),
        "block_boundary_status": "derived_audited_not_official_coordinates",
        "labels_first": {
            "observed_auc": float(label_res.observed_auc),
            "fold_aucs": [float(x) for x in label_res.fold_aucs],
            "null_p95": float(label_res.null_auc_p95),
            "margin_vs_p95": float(label_res.margin_vs_p95),
            "raw_p_value": float(label_res.p_value),
            "holm_p_value": float(adj_p[0]),
        },
        "candidate": {
            "file": zeros_tif_path.name,
            "sha256": sha256_file(zeros_tif_path),
            "positive_pixels": int(cand_mask.sum()),
            "observed_auc": float(cand_res.observed_auc),
            "fold_aucs": [float(x) for x in cand_res.fold_aucs],
            "null_p95": float(cand_res.null_auc_p95),
            "margin_vs_p95": float(cand_res.margin_vs_p95),
            "raw_p_value": float(cand_res.p_value),
            "holm_p_value": float(adj_p[1]),
            "strict_gate_flagged": flagged,
            "strict_gate_passed": not flagged,
        },
    }


def verify_recorded() -> dict[str, Any]:
    """Verify frozen DRAIN5 receipts, GeoTIFF variants, ZIP, selector, preflight, note."""
    for p in (
        EXPERIMENT_JSON,
        RUN_CARD_JSON,
        SELECTOR_JSON,
        DOCS_RUN_CARD_JSON,
        DOCS_SELECTOR_JSON,
        DOCS_DOWNLOAD_JSON,
        PREVIEW_PNG,
    ):
        if not p.exists():
            raise SystemExit(f"Missing recorded DRAIN5 artifact: {p}")
    exp = json.loads(EXPERIMENT_JSON.read_text())
    card = json.loads(RUN_CARD_JSON.read_text())
    docs_card = json.loads(DOCS_RUN_CARD_JSON.read_text())
    saved_sel = json.loads(SELECTOR_JSON.read_text())
    docs_sel = json.loads(DOCS_SELECTOR_JSON.read_text())
    dl = json.loads(DOCS_DOWNLOAD_JSON.read_text())
    if card != docs_card or saved_sel != docs_sel:
        raise SystemExit("Evidence and docs/data DRAIN5 run cards or selector receipts disagree")
    if card.get("selector_receipt") != saved_sel:
        raise SystemExit("DRAIN5 run card embedded selector receipt disagrees with selector file")

    template = ROOT / "data/bridge/sample_submission.tif"
    zeros_path = ROOT / "docs/downloads" / card["submission_name"]
    nan_path = ROOT / "docs/downloads" / card["nan_outside_artifact"]
    zip_path = ROOT / "docs/downloads" / card["zip_artifact"]
    checks_path = ROOT / "docs/downloads" / dl["checks_file"]
    note_path = ROOT / "docs/downloads" / dl["note_file"]
    preflight_path = zeros_path.with_suffix(".preflight.json")
    dl_sel_path = zeros_path.with_suffix(".selector.json")

    fresh_sel = selector.verify_selector(zeros_path, template, card)
    ok_sel = bool(fresh_sel["ok_to_submit"]) and fresh_sel["decision"] == "OK_TO_SUBMIT"
    # NOTE: after DRAIN5's own card lands in evidence/, a fresh selector import may read
    # DRAIN5 itself as the recorded point-best (if it won), flipping only the G3 gate.
    # Gate-by-gate equality with the issuance-time receipt is therefore checked on all
    # gates except G3, whose issuance-time value is preserved in the saved receipt.
    saved_gates = dict(saved_sel.get("gates") or {})
    fresh_gates = dict(fresh_sel.get("gates") or {})
    g3 = "g3_holdout_beats_recorded_best_and_paired_baseline"
    saved_gates.pop(g3, None)
    fresh_gates.pop(g3, None)
    if (
        saved_gates != fresh_gates
        or saved_sel.get("decision") != fresh_sel.get("decision")
        or json.loads(dl_sel_path.read_text()) != saved_sel
        or card.get("ok_to_submit") is not ok_sel
        or dl.get("ok_to_submit") is not ok_sel
        or (card.get("verdict") == "promote") is not ok_sel
    ):
        raise SystemExit("DRAIN5 run card/download disagrees with independent gems.selector receipt")

    if sha256_file(zeros_path) != card["raster_sha256"] or dl["sha256"] != card["raster_sha256"]:
        raise SystemExit("DRAIN5 zero-outside GeoTIFF SHA-256 mismatch")
    if (
        sha256_file(nan_path) != card["nan_outside_sha256"]
        or dl["nan_sha256"] != card["nan_outside_sha256"]
    ):
        raise SystemExit("DRAIN5 NaN-outside GeoTIFF SHA-256 mismatch")
    if sha256_file(zip_path) != card["zip_sha256"] or dl["zip_sha256"] != card["zip_sha256"]:
        raise SystemExit("DRAIN5 ZIP SHA-256 mismatch")
    with zipfile.ZipFile(zip_path) as zf:
        if zf.namelist() != [zeros_path.name]:
            raise SystemExit("DRAIN5 ZIP entry list invalid")
        if hashlib.sha256(zf.read(zeros_path.name)).hexdigest() != card["raster_sha256"]:
            raise SystemExit("DRAIN5 ZIP inner GeoTIFF hash mismatch")

    fresh_zero = submission.check_variants(zeros_path, template)
    fresh_nan = submission.check_variants(nan_path, template)
    recorded_checks = json.loads(checks_path.read_text())
    if (
        not fresh_zero["format_valid"]
        or not fresh_nan["format_valid"]
        or not strict_whole_array_ok(fresh_zero)
        or recorded_checks["zero_outside"]["sha256"] != card["raster_sha256"]
        or recorded_checks["nan_outside"]["sha256"] != card["nan_outside_sha256"]
    ):
        raise SystemExit("DRAIN5 exact-file format/range validator check failed")

    note_text = note_path.read_text().strip()
    if len(note_text) > 140 or note_text != card["note"] or note_text != dl["note"]:
        raise SystemExit("DRAIN5 note missing, mismatched, or >140 chars")

    pre = json.loads(preflight_path.read_text())
    if (
        pre.get("artifact", {}).get("sha256") != card["raster_sha256"]
        or pre.get("run_card", {}).get("artifact_sha256_matches") is not True
        or pre.get("run_card", {}).get("artifact_name_matches") is not True
        or pre.get("decision", {}).get("submission_status") != "DO_NOT_SUBMIT"
        or pre.get("decision", {}).get("ready_to_submit") is not False
        or pre.get("portal_range_diagnostic", {}).get("strict_whole_array_values_in_0_1")
        is not True
    ):
        raise SystemExit("DRAIN5 preflight receipt missing, stale, or not fail-closed")

    return {
        "verified": True,
        "experiment_rerun": False,
        "submission_name": card["submission_name"],
        "raster_sha256": card["raster_sha256"],
        "holdout_dti": card["holdout"]["dti"],
        "arm2_nodrain_dti": exp["arms"]["arm2_nodrain_52ch_replay"]["holdout"]["dti"],
        "arm3_channels_only_dti": exp["arms"]["arm3_channels_only"]["holdout"]["dti"],
        "beats_recorded_dprf1_point": bool(card["holdout"]["dti"] > RECORDED_DPRF1_DTI),
        "c2st_auc": card["exact_file_nuisance_audit"]["candidate"]["observed_auc"],
        "competing_method_novelty_passed": card["correlation_overlap_vs_registry"][
            "method_lane_passed"
        ],
        "competing_method_max_3px_overlap": card["correlation_overlap_vs_registry"][
            "method_lane_max_dot_overlap"
        ],
        "farfield_gt20px_fraction": card["off_catalogue_distance_profile"]["frac_gt_20px_farfield"],
        "verdict": card["verdict"],
        "ok_to_submit": card["ok_to_submit"],
        "selector_decision": fresh_sel["decision"],
        "selector_version": fresh_sel["selector_version"],
        "preregistration": exp["preregistration"],
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--verify-recorded", action="store_true")
    args = ap.parse_args()
    if args.verify_recorded:
        print(json.dumps(verify_recorded(), indent=2, allow_nan=False))
        return
    if EXPERIMENT_JSON.exists():
        raise SystemExit(
            "H24-DRAIN5 experiment already recorded and frozen. No implicit rerun; use --verify-recorded."
        )

    t0 = time.monotonic()
    fp = footprint.load_footprint()
    fp_ids = np.flatnonzero(fp.ravel())
    template = ROOT / "data/bridge/sample_submission.tif"
    with rasterio.open(template) as t_ds:
        transform = t_ds.transform
        tmpl_shape = (t_ds.height, t_ds.width)
        tmpl_crs = str(t_ds.crs)
    with rasterio.open(ROOT / "data/bridge/labels.tif") as l_ds:
        catalogue = (l_ds.read(1) > 0) & fp

    prep_meta = json.loads((ROOT / "data/prepared/features.json").read_text())
    prep_path = ROOT / "data/prepared/features.npy"
    if sha256_file(prep_path) != prep_meta["sha256"]:
        raise SystemExit("Prepared 30-channel feature-stack SHA-256 mismatch")
    base_mm = np.load(prep_path, mmap_mode="r")
    base_names: list[str] = list(prep_meta["names"])

    print("[1/8] Building/loading 52-channel DPRF1 stack + 7 drainage channels...", flush=True)
    if GVC_MEMMAP.exists():
        gvc_mm = np.load(GVC_MEMMAP, mmap_mode="r")
        if gvc_mm.shape != (len(fp_ids), len(gvc.GVC1_FEATURE_NAMES)):
            gvc_mm, gvc_names = gvc.build_gvc1_features(
                ROOT, base_mm, base_names, fp, transform, GVC_MEMMAP
            )
            gvc_mm = np.load(GVC_MEMMAP, mmap_mode="r")
        else:
            gvc_names = list(gvc.GVC1_FEATURE_NAMES)
    else:
        _, gvc_names = gvc.build_gvc1_features(ROOT, base_mm, base_names, fp, transform, GVC_MEMMAP)
        gvc_mm = np.load(GVC_MEMMAP, mmap_mode="r")
    sahg_mm, sahg_names = dprf1.build_sahg4_memmap(ROOT, base_mm, base_names, fp, SAHG4_MEMMAP)
    names52 = base_names + gvc_names + sahg_names
    assert len(names52) == 52
    drain_mm, drainage_names, drain_diag = drainage.build_drainage_memmap(
        ROOT, base_mm, base_names, fp, DRAINAGE_MEMMAP
    )
    names59 = names52 + drainage_names
    assert len(names59) == 59
    print(
        f"      59-channel stack ready. Drainage census: sinks="
        f"{drain_diag['sink_cells']:,} ({100 * drain_diag['sink_fraction_of_valid']:.3f}% of valid), "
        f"channel cells (A>=100)={drain_diag['channel_cells_accum_ge_100']:,}, "
        f"max A={drain_diag['accum_max_cells']:,.0f} cells; RSS={peak_rss_mib():.1f} MiB",
        flush=True,
    )

    context = holdout.SegmentHoldout(fp, catalogue, buffer_px=15)
    print("[2/8] Two-polarity leakage canary across all 59 channels...", flush=True)
    canary = run_batched_canary(
        context,
        fp,
        [
            ("base", base_mm, base_names),
            ("gvc", gvc_mm, gvc_names),
            ("sahg", sahg_mm, sahg_names),
            ("drainage", drain_mm, drainage_names),
        ],
        batch_size=4,
    )
    print(
        f"      Canary passed={canary['passed']} | worst={canary['worst_feature']} "
        f"(pooled AUC={canary['worst_pooled_auc']:.4f}) | Drainage AUCs="
        f"{ {k: round(v, 4) for k, v in canary['drainage_channel_pooled_aucs'].items()} }",
        flush=True,
    )
    if not canary["passed"]:
        raise SystemExit("HALT: Single-feature leakage canary exceeded threshold 0.90")

    conf_prov = confounds.build_all(force=False)
    with np.load(confounds.CONF / "confounds.npz") as c_npz:
        cdict = confounds.classifier_features(c_npz)
        nuis_keys = ["road_m", "claim_m", "block_1", "block_2", "block_3", "block_4"]
        nuisance_fp = np.column_stack(
            [cdict[k].ravel()[fp_ids].astype(np.float32, copy=False) for k in nuis_keys]
        )
    del cdict
    gc.collect()

    selective_extra: tuple[str, ...] = ()  # locked: drainage channels are terrain-derived, not residualized
    total_offcat = int((fp & (~catalogue)).sum())

    print(
        "[3/8] 4-fold SegmentHoldout: Arm1 DRAIN5 (59ch+DrainRegimeB), Arm3 channelsOnly, Arm2 noDrain replay...",
        flush=True,
    )
    oof_quad_sharp = np.zeros(fp.shape, dtype=np.float32)
    oof_quad_cond = np.zeros(fp.shape, dtype=np.float32)
    preds_arm1: list[np.ndarray] = []
    preds_arm2: list[np.ndarray] = []
    preds_arm3: list[np.ndarray] = []
    fold_meta: list[dict[str, Any]] = []

    for fold in context.folds:
        fid = int(fold["id"])
        fname = fold["name"]
        tf0 = time.monotonic()
        f_offcat = int((fold["valid"] & (~fold["visible"])).sum())
        k_fold = int(round(FULL_DOT_BUDGET * f_offcat / total_offcat))

        # Arm 1 + Arm 3 share one 59-channel fit; they differ only in the Regime-B multiplier.
        p_s1, p_c1, p_c1_legacy, m_a1 = dprf1.fit_and_predict_fold(
            base_mm,
            gvc_mm,
            sahg_mm,
            nuisance_fp,
            names59,
            fp,
            fp_ids,
            train_mask=fold["train"],
            visible_mask=fold["visible"],
            predict_mask=fold["valid"],
            neg_mode="stratified_d3",
            seed=SEED + 10 * fid,
            extra_mm=drain_mm,
            regime_b_extra_names=drainage.DRAIN5_REGIME_B_NAMES,
            selective_extra_names=selective_extra,
            return_legacy_conduit=True,
        )
        p_s1 = dprf1.debiased_apron_surface(p_s1, fold["valid"], fold["visible"])
        p_c1 = dprf1.debiased_apron_surface(p_c1, fold["valid"], fold["visible"])
        p_c1_legacy = dprf1.debiased_apron_surface(p_c1_legacy, fold["valid"], fold["visible"])
        oof_quad_sharp += p_s1
        oof_quad_cond += p_c1
        d_arm1 = dprf1.two_regime_submodular_allocate(
            p_s1,
            p_c1,
            fold["valid"],
            fold["visible"],
            budget=k_fold,
            primary_share=0.68,
            min_spacing_px=2.8,
            catalogue_clearance_px=2.0,
        )
        d_arm3 = dprf1.two_regime_submodular_allocate(
            p_s1,
            p_c1_legacy,
            fold["valid"],
            fold["visible"],
            budget=k_fold,
            primary_share=0.68,
            min_spacing_px=2.8,
            catalogue_clearance_px=2.0,
        )
        preds_arm1.append((d_arm1 > 0.5).astype(np.uint8))
        preds_arm3.append((d_arm3 > 0.5).astype(np.uint8))
        del p_s1, p_c1, p_c1_legacy, d_arm1, d_arm3
        gc.collect()

        # Arm 2: exact 52-channel DPRF1 configuration through the same code path.
        p_s2, p_c2, m_a2 = dprf1.fit_and_predict_fold(
            base_mm,
            gvc_mm,
            sahg_mm,
            nuisance_fp,
            names52,
            fp,
            fp_ids,
            train_mask=fold["train"],
            visible_mask=fold["visible"],
            predict_mask=fold["valid"],
            neg_mode="stratified_d3",
            seed=SEED + 10 * fid,
        )
        p_s2 = dprf1.debiased_apron_surface(p_s2, fold["valid"], fold["visible"])
        p_c2 = dprf1.debiased_apron_surface(p_c2, fold["valid"], fold["visible"])
        d_arm2 = dprf1.two_regime_submodular_allocate(
            p_s2,
            p_c2,
            fold["valid"],
            fold["visible"],
            budget=k_fold,
            primary_share=0.68,
            min_spacing_px=2.8,
            catalogue_clearance_px=2.0,
        )
        preds_arm2.append((d_arm2 > 0.5).astype(np.uint8))
        del p_s2, p_c2, d_arm2
        gc.collect()

        r1, _ = context.score_fold(preds_arm1[-1], fold)
        r3, _ = context.score_fold(preds_arm3[-1], fold)
        r2, _ = context.score_fold(preds_arm2[-1], fold)
        print(
            f"      Fold {fname:18s} | k={k_fold:,} | DRAIN5={r1['dti']:.5f} | "
            f"ChanOnly={r3['dti']:.5f} | noDrain(replay)={r2['dti']:.5f} "
            f"({time.monotonic() - tf0:.1f}s, RSS={peak_rss_mib():.1f} MiB)",
            flush=True,
        )
        fold_meta.append(
            {"fold": fname, "k_fold_budget": k_fold, "arm1_59ch": m_a1, "arm2_52ch": m_a2}
        )

    sum_arm1 = context.summarize(preds_arm1, ci_draws=1999)
    sum_arm2 = context.summarize(preds_arm2, ci_draws=1999)
    sum_arm3 = context.summarize(preds_arm3, ci_draws=1999)
    paired = {
        "arm1_vs_arm2_nodrain_replay": context.compare_paired(
            preds_arm1, preds_arm2, ci_draws=1999, seed=SEED
        ),
        "arm3_vs_arm2_channel_effect": context.compare_paired(
            preds_arm3, preds_arm2, ci_draws=1999, seed=SEED
        ),
        "arm1_vs_arm3_regime_gating_effect": context.compare_paired(
            preds_arm1, preds_arm3, ci_draws=1999, seed=SEED
        ),
    }
    print(
        f"      POOLED HOLDOUT-DTI | Arm1(DRAIN5)={sum_arm1['dti']:.5f} {sum_arm1['ci95']['interval']} | "
        f"Arm3(chanOnly)={sum_arm3['dti']:.5f} | Arm2(noDrain replay)={sum_arm2['dti']:.5f} | "
        f"recorded DPRF1={RECORDED_DPRF1_DTI:.5f}",
        flush=True,
    )
    del preds_arm1, preds_arm2, preds_arm3
    gc.collect()

    oof_canary = context.canary(
        {"drain5_quad_oof_sharp": oof_quad_sharp}, seed=GVC_BASE_SEED, max_per_class=15000
    )
    if not oof_canary["passed"]:
        raise SystemExit("HALT: Quadrant OOF surface flagged leakage canary")

    print("[4/8] Partition 2 (Rotated45 Diamond OOF) for Arm 1 stitched export...", flush=True)
    rot45_folds = dprf1.make_rotated45_segment_folds(fp, catalogue, buffer_px=15)
    oof_rot45_sharp = np.zeros(fp.shape, dtype=np.float32)
    oof_rot45_cond = np.zeros(fp.shape, dtype=np.float32)
    for rfold in rot45_folds:
        rfid = int(rfold["id"])
        ps_r, pc_r, _m = dprf1.fit_and_predict_fold(
            base_mm,
            gvc_mm,
            sahg_mm,
            nuisance_fp,
            names59,
            fp,
            fp_ids,
            train_mask=rfold["train"],
            visible_mask=rfold["visible"],
            predict_mask=rfold["valid"],
            neg_mode="stratified_d3",
            seed=SEED + 500 + 17 * rfid,
            extra_mm=drain_mm,
            regime_b_extra_names=drainage.DRAIN5_REGIME_B_NAMES,
            selective_extra_names=selective_extra,
        )
        oof_rot45_sharp += ps_r
        oof_rot45_cond += pc_r
        del ps_r, pc_r
        gc.collect()

    stitched_sharp_raw = (0.50 * oof_quad_sharp + 0.50 * oof_rot45_sharp).astype(np.float32)
    stitched_cond_raw = (0.50 * oof_quad_cond + 0.50 * oof_rot45_cond).astype(np.float32)
    del oof_rot45_sharp, oof_rot45_cond, oof_quad_sharp, oof_quad_cond
    gc.collect()

    stitched_sharp = dprf1.debiased_apron_surface(stitched_sharp_raw, fp, catalogue)
    stitched_cond = dprf1.debiased_apron_surface(stitched_cond_raw, fp, catalogue)
    pre_placement_surface = (0.68 * stitched_sharp + 0.32 * stitched_cond).astype(np.float32)

    print("[5/8] Pre-placement novelty audit (surface) vs pinned registry + peers...", flush=True)
    priority_reg = json.loads((ROOT / "registry/priority_rasters.json").read_text())
    existing_shas = {e["footprint_sha256"] for e in priority_reg["unique_rasters"]}
    extra_locals = local_lane_entries(fp, existing_shas)
    pre_nov_methods = novelty.compare_prospective_registry(
        pre_placement_surface,
        fp,
        priority_reg["unique_rasters"],
        ROOT,
        sample_size=200_000,
        extra_entries=extra_locals,
    )
    pre_nov_peers = check_peer_blobs(pre_placement_surface, None, fp)
    print(
        f"      Surface: method_passed={pre_nov_methods['method_lane_passed']} "
        f"(max |rho|={pre_nov_methods['method_lane_max_abs_rank_correlation']}), "
        f"peers checked={pre_nov_peers['peer_unique_blobs_checked']} passed={pre_nov_peers['passed']} "
        f"(max |rho|={pre_nov_peers['max_abs_surface_spearman']:.4f}, missing={pre_nov_peers['peer_blobs_missing_from_cache']})",
        flush=True,
    )
    if not pre_nov_methods["method_lane_passed"] or not pre_nov_peers["passed"]:
        raise SystemExit(
            "HALT: Pre-placement surface exceeded 0.90 rank-correlation limit (duplicate lane)"
        )

    print("[6/8] Final 37,654-dot allocation + final-dot novelty audit...", flush=True)
    final_dots = dprf1.two_regime_submodular_allocate(
        stitched_sharp,
        stitched_cond,
        fp,
        catalogue,
        budget=FULL_DOT_BUDGET,
        primary_share=0.68,
        min_spacing_px=2.8,
        catalogue_clearance_px=2.0,
    )
    dots_undebiased_diag = dprf1.two_regime_submodular_allocate(
        stitched_sharp_raw,
        stitched_cond_raw,
        fp,
        catalogue,
        budget=FULL_DOT_BUDGET,
        primary_share=0.68,
        min_spacing_px=2.8,
        catalogue_clearance_px=2.0,
    )
    dist_profile = compute_distance_profile(final_dots > 0.5, catalogue, fp)
    dist_profile_undebiased = compute_distance_profile(dots_undebiased_diag > 0.5, catalogue, fp)
    del dots_undebiased_diag, stitched_sharp_raw, stitched_cond_raw
    gc.collect()

    final_nov_methods = novelty.compare_prospective_registry(
        pre_placement_surface,
        fp,
        priority_reg["unique_rasters"],
        ROOT,
        dots=final_dots > 0.5,
        sample_size=200_000,
        extra_entries=extra_locals,
    )
    final_nov_peers = check_peer_blobs(pre_placement_surface, final_dots, fp)
    comp_nov_ok = bool(final_nov_methods["method_lane_passed"] and final_nov_peers["passed"])
    # Exact overlap vs the reigning DPRF1 candidate, for the executive summary.
    dprf1_overlap = None
    for row in final_nov_methods["rows"]:
        if "dprf1-stitched-oof" in str(row.get("file", "")):
            dprf1_overlap = row.get("candidate_dot_overlap_within_3px")
    print(
        f"      Final dots ({dist_profile['n_dots']:,}): competing={final_nov_methods['competing_method_rasters_count']} "
        f"passed={final_nov_methods['method_lane_passed']} max_overlap={final_nov_methods['method_lane_max_dot_overlap']} "
        f"(vs DPRF1 {dprf1_overlap}); peers passed={final_nov_peers['passed']} "
        f"max_overlap={final_nov_peers['max_dot_overlap_within_3px']}; "
        f"apron2-9={100 * dist_profile['frac_2_to_9px_apron']:.1f}% farfield>20={100 * dist_profile['frac_gt_20px_farfield']:.1f}%",
        flush=True,
    )

    print("[7/8] Writing GeoTIFF pair + ZIP; exact-file C2ST audit...", flush=True)
    slug = (
        "drain5-drainage-knickpoint-stitched-oof"
        if comp_nov_ok
        else "drain5-negative-drainage-knickpoint"
    )
    content_id = submission.scored_content_id(final_dots, fp, catalogue)
    downloads = ROOT / "docs/downloads"
    zeros_name = submission.make_filename("gems24", slug, "20261026", content_id, "zeros")
    nan_name = submission.make_filename("gems24", slug, "20261026", content_id, "nan")
    zeros_path = submission.write_submission(
        final_dots.astype(np.float32), template, downloads / zeros_name, outside="zero"
    )
    nan_path = submission.write_submission(
        final_dots.astype(np.float32), template, downloads / nan_name, outside="nan"
    )
    zip_name = zeros_name.replace(".tif", ".zip")
    zip_path = submission.zip_single(zeros_path, downloads / zip_name)

    zero_raw_checks = submission.check_variants(zeros_path, template)
    nan_raw_checks = submission.check_variants(nan_path, template)
    if (
        not zero_raw_checks["format_valid"]
        or not nan_raw_checks["format_valid"]
        or not strict_whole_array_ok(zero_raw_checks)
    ):
        raise SystemExit("Exact-file format/strict-range validator failed")

    checks_payload = {
        "zero_outside": {"file": zeros_name, "submission_authorized": False, **zero_raw_checks},
        "nan_outside": {"file": nan_name, "submission_authorized": False, **nan_raw_checks},
        "zeros_zip_file": zip_name,
        "zeros_zip_sha256": sha256_file(zip_path),
    }
    checks_file = f"checks-{zeros_name[:-4]}.json"
    save_json(checks_payload, downloads / checks_file)

    c2st_report = run_exact_file_c2st(zeros_path, catalogue, fp)
    print(
        f"      C2ST strict pass={c2st_report['candidate']['strict_gate_passed']} "
        f"(AUC={c2st_report['candidate']['observed_auc']:.4f}, Holm p={c2st_report['candidate']['holm_p_value']:.3f})",
        flush=True,
    )
    write_preview(final_dots > 0.5, fp, PREVIEW_PNG)

    note = (
        f"GEMS24 DRAIN5 | D8 drainage knickpoint 59ch stitched-OOF | id {content_id} | "
        f"HOLDOUT-DTI {sum_arm1['dti']:.5f} | research; selector gated"
    )
    if len(note) > 140:
        raise AssertionError(f"Note length {len(note)} exceeds 140 characters")
    note_file = f"note-{zeros_name[:-4]}.txt"
    (downloads / note_file).write_text(note + "\n")

    comp_rows_sorted = sorted(
        [
            r
            for r in final_nov_methods["rows"]
            if r.get("entry_role") == "competing_method_lane"
            and r.get("candidate_dot_overlap_within_3px") is not None
        ],
        key=lambda r: float(r["candidate_dot_overlap_within_3px"]),
        reverse=True,
    )
    literal_dup_rows = [r for r in final_nov_methods["rows"] if r.get("duplicate")]

    p_vs_arm2 = paired["arm1_vs_arm2_nodrain_replay"]
    replay_matches_recorded = bool(abs(sum_arm2["dti"] - RECORDED_DPRF1_DTI) < 1e-12)
    beats_point_best = bool(sum_arm1["dti"] > RECORDED_DPRF1_DTI)
    paired_ci = [float(p_vs_arm2["paired_delta_ci95"][0]), float(p_vs_arm2["paired_delta_ci95"][1])]

    technical_gates = {
        "format_and_strict_0_1_range_passed": True,
        "leakage_canary_59ch_passed": bool(canary["passed"]),
        "holdout_beats_recorded_dprf1_point_best": beats_point_best,
        "paired_vs_nodrain_replay_ci95_gt_0": bool(p_vs_arm2["ci95_strictly_positive"]),
        "competing_method_novelty_passed": bool(final_nov_methods["method_lane_passed"]),
        "peer_blobs_novelty_passed": bool(final_nov_peers["passed"]),
        "exact_file_c2st_nuisance_passed": bool(c2st_report["candidate"]["strict_gate_passed"]),
        "stitched_oof_apron_debiasing_verified": bool(
            dist_profile["frac_gt_20px_farfield"] >= 0.35 and dist_profile["frac_le_2px"] == 0.0
        ),
    }
    all_technical_passed = all(technical_gates.values())

    elapsed = round(time.monotonic() - t0, 2)
    run_card: dict[str, Any] = {
        "schema_version": 2,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "lane_id": "H24-DRAIN5",
        "preregistration": PREREG_PATH,
        "preregistration_commit": PREREG_COMMIT,
        "experiments_run": 3,
        "experiment_budget_limit": 3,
        "elapsed_seconds": elapsed,
        "peak_rss_mib": round(peak_rss_mib(), 1),
        "hypothesis": (
            "D8 drainage-network topology on the 100 m DEM — aligned channel knickpoints "
            "(downstream jumps in normalised steepness k_sn = slope * A^0.45) and flow-azimuth "
            "deflections across adjacent ephemeral washes — traces oblique/strike-slip and "
            "sheetwash-eroded piedmont faults whose interfluve scarps have been erased and that "
            "surface mapping and local-filter geomorphology miss. Seven label-free drainage "
            "channels (log flow accumulation, k_sn, knickpoint jump, knickpoint co-linearity "
            "lineament, channel distance, HAND, azimuth bend) added to the 52-channel DPRF1 "
            "stitched-OOF stack — and gating its concealed Regime-B allocation — recover "
            "held-out whole fault segments better than the identical pipeline without them."
        ),
        "mechanism": (
            "D8 steepest-descent routing (O'Callaghan & Mark 1984) on the Gaussian-smoothed "
            "(sigma 2 px) DEM with no depression filling (endorheic sinks terminate accumulation; "
            "sink census recorded in drainage_diagnostics) yields exact upslope area A by descending-"
            "elevation propagation. Stream-power steepness k_sn = S * A^0.45 (Flint 1974; "
            "Wobus et al. 2006) jumps downstream where a wash crosses an uplifting or laterally "
            "offset fault block; co-linear jumps across >=3 neighbouring washes and systematic "
            "azimuth bends localise the buried trace even where the scarp itself is gone. "
            "Supervised stitched-OOF, stratified near+far negatives, selective residualization "
            "(drainage channels protected as terrain), relief calibration, ridge sharpening, "
            "apron debiasing and the two-regime 300 m submodular allocator are reused unchanged "
            "from DPRF1, isolating the drainage increment."
        ),
        "named_non_fault_mimic": (
            "Resistant lithologic hogbacks (welded ash-flow tuff or dike ribs) producing "
            "lithologic knickpoints across parallel gullies, alluvial fan-lobe avulsion "
            "channels, Pleistocene Lake Lahontan recessional strandlines, and road borrow "
            "ditches — all of which bend or steepen ephemeral washes without any Quaternary "
            "faulting or geothermal upflow."
        ),
        "holdout": sum_arm1,
        "arms_same_evaluator": {
            "arm1_drain5_primary_59ch": {
                "dti": sum_arm1["dti"],
                "ci95": sum_arm1["ci95"]["interval"],
            },
            "arm3_channels_only_59ch": {
                "dti": sum_arm3["dti"],
                "ci95": sum_arm3["ci95"]["interval"],
            },
            "arm2_nodrain_52ch_replay": {
                "dti": sum_arm2["dti"],
                "ci95": sum_arm2["ci95"]["interval"],
            },
        },
        "paired_comparisons": paired,
        "recorded_point_best_comparison": {
            "recorded_best_lane": "H24-DPRF1",
            "recorded_best_dti": RECORDED_DPRF1_DTI,
            "recorded_best_source": "evidence/dprf1_run_card_20261026.json",
            "candidate_point_delta": float(sum_arm1["dti"] - RECORDED_DPRF1_DTI),
            "candidate_beats_recorded_point": beats_point_best,
            "arm2_replay_dti": float(sum_arm2["dti"]),
            "arm2_replay_bit_identical_to_recorded": replay_matches_recorded,
            "scope": "Recorded point comparison; the paired Arm1-vs-Arm2 bootstrap is the same-session replay comparison.",
        },
        "paired_vs_baseline": {
            "ci95": paired_ci,
            "delta_dti": float(p_vs_arm2["paired_delta_dti"]),
            "baseline_name": "DRAIN5 Arm2 noDrain 52ch replay (DPRF1 configuration, in-session)",
            "baseline_dti": float(sum_arm2["dti"]),
        },
        "baseline_reproduced": True,
        "paired_vs_current_best": {
            "baseline_dti": float(sum_arm2["dti"]),
            "evaluator_version": "gems-segment-pooled-v1",
            "n_withheld_positive_pixels": 60988,
            "baseline_replayed": True,
            "ci95": paired_ci,
            "baseline_identity": (
                "Arm2 in-session replay of the DPRF1 configuration"
                + (
                    " (bit-identical pooled DTI to recorded DPRF1)"
                    if replay_matches_recorded
                    else f" (recorded DPRF1 {RECORDED_DPRF1_DTI}; replay differs, see experiment record)"
                )
            ),
        },
        "leakage_canary": {
            "passed": canary["passed"],
            "n_features_checked": canary["n_features_checked"],
            "worst_feature": canary["worst_feature"],
            "worst_pooled_auc": canary["worst_pooled_auc"],
            "worst_polarity_extremity": canary["worst_polarity_extremity"],
            "drainage_channel_pooled_aucs": canary["drainage_channel_pooled_aucs"],
            "oof_surface_auc": oof_canary["features"]["drain5_quad_oof_sharp"]["pooled_auc"],
        },
        "drainage_diagnostics": drain_diag,
        "correlation_overlap_vs_registry": {
            "total_registry_entries_checked": final_nov_methods["registry_unique_rasters"],
            "competing_method_rasters_checked": final_nov_methods["competing_method_rasters_count"],
            "calibration_control_rasters_checked": final_nov_methods[
                "calibration_control_rasters_count"
            ],
            "peer_blobs_checked": final_nov_peers["peer_unique_blobs_checked"],
            "peer_blobs_missing_from_cache": final_nov_peers["peer_blobs_missing_from_cache"],
            "pre_placement_surface_max_abs_rank_correlation": pre_nov_methods[
                "method_lane_max_abs_rank_correlation"
            ],
            "pre_placement_peers_max_abs_rank_correlation": pre_nov_peers[
                "max_abs_surface_spearman"
            ],
            "method_lane_passed": final_nov_methods["method_lane_passed"],
            "method_lane_max_abs_rank_correlation": final_nov_methods[
                "method_lane_max_abs_rank_correlation"
            ],
            "method_lane_max_dot_overlap": final_nov_methods["method_lane_max_dot_overlap"],
            "dot_overlap_within_3px_vs_dprf1": dprf1_overlap,
            "peer_blobs_passed": final_nov_peers["passed"],
            "peer_blobs_max_dot_overlap": final_nov_peers["max_dot_overlap_within_3px"],
            "peer_blobs_max_overlap_artifact": final_nov_peers["max_overlap_peer_artifact"],
            "literal_all_entries_passed": final_nov_methods["literal_all_entries_passed"],
            "literal_all_entries_max_dot_overlap": final_nov_methods["max_dot_overlap"],
            "calibration_control_rows": final_nov_methods["calibration_control_rows"],
            "top_5_competing_comparators": comp_rows_sorted[:5],
        },
        "novelty": {
            "surface": {
                "max_abs_rank_correlation": pre_nov_methods["method_lane_max_abs_rank_correlation"],
                "literal_all_entries_passed": bool(pre_nov_methods["literal_all_entries_passed"]),
            },
            "final_dots": {
                "max_abs_rank_correlation": final_nov_methods[
                    "method_lane_max_abs_rank_correlation"
                ],
                "method_lane_max_dot_overlap": final_nov_methods["method_lane_max_dot_overlap"],
                "method_lane_passed": bool(final_nov_methods["method_lane_passed"]),
                "literal_all_entries_passed": bool(final_nov_methods["literal_all_entries_passed"]),
                "literal_duplicate_rows": literal_dup_rows,
            },
            "peers_final": {
                "max_dot_overlap_within_3px": final_nov_peers["max_dot_overlap_within_3px"],
                "passed": bool(final_nov_peers["passed"]),
            },
        },
        "off_catalogue_distance_profile": dist_profile,
        "off_catalogue_distance_profile_before_apron_debiasing": dist_profile_undebiased,
        "exact_file_nuisance_audit": c2st_report,
        "c2st_exact_file": {
            "labels_audited_first": True,
            "strict_gate_passed": bool(c2st_report["candidate"]["strict_gate_passed"]),
            "observed_auc": c2st_report["candidate"]["observed_auc"],
            "holm_p_value": c2st_report["candidate"]["holm_p_value"],
        },
        "technical_gates": technical_gates,
        "technical_promotion_gates_passed": all_technical_passed,
        "raster_sha256": zero_raw_checks["sha256"],
        "nan_outside_artifact": nan_name,
        "nan_outside_sha256": nan_raw_checks["sha256"],
        "zip_artifact": zip_name,
        "zip_sha256": checks_payload["zeros_zip_sha256"],
        "validator_output": {
            "sha256": zero_raw_checks["sha256"],
            "format_valid": zero_raw_checks["format_valid"],
            "format_acceptable": zero_raw_checks["format_acceptable"],
            "strict_whole_array_values_in_0_1": strict_whole_array_ok(zero_raw_checks),
            "no_nan_in_footprint": zero_raw_checks["checks"]["footprint_all_finite"]["pass"],
            "footprint_range_0_1": zero_raw_checks["checks"]["footprint_range_0_1"]["pass"],
            "crs": tmpl_crs,
            "shape": list(tmpl_shape),
            "positive_pixels": int((final_dots[fp] > 0.5).sum()),
        },
        "submission_name": zeros_name,
        "note": note,
        "note_length": len(note),
        "verdict": "negative",
        "ok_to_download": True,
        "ok_to_submit": False,
        "submission_authorized": False,
        "submission_slots_used": 0,
        "organizer_confirmed_score": None,
        "governance_hold_reasons": [
            "Parallel-Run Protocol Rule 6: promotion to a real weekly slot is a separate selector step",
            "gems-selector-v2 is negative-only: literal registry-039 spacing-5 lattice retained, live DrivenData quota unknown, independent positive replay certificate not implemented",
            "HOLDOUT-DTI is a local hide-and-recover measurement, not a leaderboard score or forecast",
        ],
    }

    print("[8/8] Selector v2 receipt on exact bytes + preflight + records...", flush=True)
    sel_receipt = selector.verify_selector(zeros_path, template, run_card)
    run_card["selector_receipt"] = sel_receipt
    print(
        f"      Selector: {sel_receipt['decision']} | gates="
        f"{ {k: v for k, v in sel_receipt['gates'].items()} }",
        flush=True,
    )
    save_json(sel_receipt, SELECTOR_JSON)
    save_json(sel_receipt, DOCS_SELECTOR_JSON)
    save_json(sel_receipt, zeros_path.with_suffix(".selector.json"))
    save_json(run_card, RUN_CARD_JSON)
    save_json(run_card, DOCS_RUN_CARD_JSON)

    preflight_out = downloads / f"{zeros_name[:-4]}.preflight.json"
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/preflight_submission.py"),
            str(zeros_path),
            "--run-card",
            str(RUN_CARD_JSON),
            "--output",
            str(preflight_out),
        ],
        cwd=ROOT,
        check=True,
    )

    download_record = {
        "lane_id": "H24-DRAIN5",
        "file": zeros_name,
        "sha256": zero_raw_checks["sha256"],
        "nan_file": nan_name,
        "nan_sha256": nan_raw_checks["sha256"],
        "zip_file": zip_name,
        "zip_sha256": checks_payload["zeros_zip_sha256"],
        "checks_file": checks_file,
        "preflight_file": preflight_out.name,
        "selector_file": zeros_path.with_suffix(".selector.json").name,
        "note_file": note_file,
        "note": note,
        "pixel_count": int((final_dots[fp] > 0.5).sum()),
        "holdout_dti": sum_arm1["dti"],
        "holdout_ci95": sum_arm1["ci95"]["interval"],
        "arm2_nodrain_replay_dti": float(sum_arm2["dti"]),
        "arm3_channels_only_dti": float(sum_arm3["dti"]),
        "recorded_dprf1_dti": RECORDED_DPRF1_DTI,
        "beats_recorded_dprf1_point": beats_point_best,
        "paired_delta_vs_nodrain": float(p_vs_arm2["paired_delta_dti"]),
        "paired_delta_ci95_vs_nodrain": paired_ci,
        "c2st_auc": c2st_report["candidate"]["observed_auc"],
        "c2st_holm_p": c2st_report["candidate"]["holm_p_value"],
        "competing_method_novelty_passed": final_nov_methods["method_lane_passed"],
        "competing_method_max_3px_overlap": final_nov_methods["method_lane_max_dot_overlap"],
        "dot_overlap_within_3px_vs_dprf1": dprf1_overlap,
        "peer_blobs_novelty_passed": final_nov_peers["passed"],
        "peer_blobs_max_3px_overlap": final_nov_peers["max_dot_overlap_within_3px"],
        "farfield_gt20px_fraction": dist_profile["frac_gt_20px_farfield"],
        "technical_promotion_gates_passed": all_technical_passed,
        "ok_to_download": True,
        "ok_to_submit": False,
        "submission_authorized": False,
        "verdict": "negative",
        "selector_decision": sel_receipt["decision"],
        "competing_method_rasters_checked": final_nov_methods["competing_method_rasters_count"],
    }
    save_json(download_record, DOCS_DOWNLOAD_JSON)

    experiment_record = {
        "generated_utc": run_card["generated_utc"],
        "lane_id": "H24-DRAIN5",
        "preregistration": PREREG_PATH,
        "preregistration_commit": PREREG_COMMIT,
        "elapsed_seconds": elapsed,
        "peak_rss_mib": run_card["peak_rss_mib"],
        "feature_names_59": names59,
        "feature_names_52_prefix": names52,
        "drainage_feature_names": drainage_names,
        "drainage_regime_b_names": list(drainage.DRAIN5_REGIME_B_NAMES),
        "selective_residualized": sorted(set(dprf1.SELECTIVE_RESID_NAMES) | set(selective_extra)),
        "drainage_diagnostics": drain_diag,
        "canary": canary,
        "fold_fit_metadata": fold_meta,
        "arms": {
            "arm1_drain5_primary": {"holdout": sum_arm1},
            "arm2_nodrain_52ch_replay": {"holdout": sum_arm2},
            "arm3_channels_only": {"holdout": sum_arm3},
        },
        "paired_comparisons": paired,
        "novelty": {
            "pre_placement_methods": {k: v for k, v in pre_nov_methods.items() if k != "rows"},
            "pre_placement_peers": pre_nov_peers,
            "final_dots_methods": final_nov_methods,
            "final_dots_peers": final_nov_peers,
        },
        "off_catalogue_distance_profile": dist_profile,
        "off_catalogue_distance_profile_before_apron_debiasing": dist_profile_undebiased,
        "c2st_audit": c2st_report,
        "nuisance_provenance": conf_prov,
        "ok_to_submit": False,
        "run_card": run_card,
    }
    save_json(experiment_record, EXPERIMENT_JSON)
    print(
        f"Done in {elapsed:.1f}s (peak RSS {run_card['peak_rss_mib']:.1f} MiB). "
        f"DRAIN5 HOLDOUT-DTI={sum_arm1['dti']:.5f} vs replay={sum_arm2['dti']:.5f} "
        f"(recorded DPRF1 {RECORDED_DPRF1_DTI:.5f}); technical_gates_all={all_technical_passed}; "
        f"selector={sel_receipt['decision']}; verdict=negative (fail-closed).",
        flush=True,
    )


if __name__ == "__main__":
    main()
