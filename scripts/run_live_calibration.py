#!/usr/bin/env python3
"""How well do local proxies and nuisance-association tests rank the group's live-scored artifacts?

Reads ``registry/live_scores.json`` (owner-reported scores with provenance), fetches each artifact from its
pinned sibling-repo commit with ``gh api`` (SHA-256 verified; cached in ignored ``data/research/scored``),
and computes label-independent descriptors plus exact DTI against independent / catalogue-masked truths.
Correlations are reported for all artifacts and for the corroborated subset. Never consumes a slot.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt, label
from scipy.stats import kendalltau, spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems import c2s2, confounds, footprint, holdout, metric  # noqa: E402
from gems.thinning import neighbour_profile  # noqa: E402

CACHE = ROOT / "data/research/scored"
SEED = 20261002


def fetch(art: dict) -> Path:
    CACHE.mkdir(parents=True, exist_ok=True)
    dest = CACHE / f"{art['id']}.tif"
    if dest.exists() and hashlib.sha256(dest.read_bytes()).hexdigest() == art["sha256"]:
        return dest
    with open(dest, "wb") as fh:
        subprocess.run(
            [
                "gh",
                "api",
                f"repos/{art['repo']}/contents/{art['path']}?ref={art['repo_commit']}",
                "-H",
                "Accept: application/vnd.github.raw",
            ],
            stdout=fh,
            check=True,
        )
    if hashlib.sha256(dest.read_bytes()).hexdigest() != art["sha256"]:
        raise SystemExit(
            f"Hash mismatch for {art['id']}: pinned commit no longer serves the same bytes"
        )
    return dest


def corr(x, y):
    r = spearmanr(x, y)
    return {
        "spearman": float(r.statistic),
        "p": float(r.pvalue),
        "kendall": float(kendalltau(x, y).statistic),
        "n": int(len(x)),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=ROOT / "evidence/live_calibration.json")
    ap.add_argument("--audit-auc", action="store_true", help="also compute C2ST AUC per artifact")
    ap.add_argument("--samples", type=int, default=12000)
    args = ap.parse_args()
    ledger = json.loads((ROOT / "registry/live_scores.json").read_text())
    fp = footprint.load_footprint()
    with rasterio.open(ROOT / "data/bridge/labels.tif") as d:
        K = d.read(1) > 0
    with rasterio.open(ROOT / "data/external/derived_sgmc_faults_100m_u8.tif") as d:
        SG = (d.read(1) > 0) & fp
    with rasterio.open(ROOT / "data/external/lidar_scarp_features_u8.tif") as d:
        lidar_valid = d.read(12) > 0
    dK = distance_transform_edt(~K)
    truths = {
        "sgmc_far3": SG & ~K & (dK > 3),
        "sgmc_far10": SG & ~K & (dK > 10),
    }
    comp, nc = label(K, structure=np.ones((3, 3), int))
    rng = np.random.default_rng(SEED)
    pick = rng.random(nc + 1) < 0.20
    pick[0] = False
    t_sparse = pick[comp] & K
    truths["catalogue_sparse20_contaminated"] = t_sparse
    known = {k: (K & ~t_sparse if k.startswith("catalogue") else K) for k in truths}
    feats = purge = fold = None
    if args.audit_auc:
        with np.load(confounds.CONF / "confounds.npz") as cache:
            feats = confounds.classifier_features(cache)
        fold, _ = holdout.make_quadrant_folds(fp)
        h, w = fp.shape
        yy, xx = np.ogrid[:h, :w]
        spatial_block = (yy // 100) * ((w + 99) // 100) + xx // 100
        purge = {}
        for f_id in range(4):
            collar = distance_transform_edt(fold != f_id) <= 15
            purge[f_id] = np.unique(spatial_block[collar & fp])
    rows = []
    for art in ledger["artifacts"]:
        t0 = time.time()
        path = fetch(art)
        with rasterio.open(path) as d:
            a = d.read(1)
        a = np.where(np.isfinite(a), a, 0)
        a[~fp] = 0
        binary = bool(np.isin(a[fp], [0, 1]).all())
        pos = (a > 0) & fp
        out = pos & ~K
        row = {
            "id": art["id"],
            "label": art["label"],
            "score": art["owner_reported_public_score"],
            "corroboration": art["corroboration"],
            "binary": binary,
            "emitted": int(pos.sum()),
            "emitted_outside_catalogue": int(out.sum()),
            "share_within3_of_catalogue": float(((dK <= 3) & out).sum() / max(out.sum(), 1)),
            "share_within10_of_catalogue": float(((dK <= 10) & out).sum() / max(out.sum(), 1)),
            "share_in_lidar_area": float((out & lidar_valid).sum() / max(out.sum(), 1)),
            "geometry": neighbour_profile(out),
        }
        for name, truth in truths.items():
            if binary:
                r = metric.dti_score_fast(pos, truth, valid_mask=fp, catalogue_mask=known[name])
            else:
                r = metric.dti_components_exact(a, truth, valid_mask=fp, catalogue_mask=known[name])
            row[name] = {"dti": r["dti"], "coverage": r["coverage"], "n_truth": r["n_truth"]}
        if args.audit_auc and binary:
            near, far, _ = c2s2.near_far_masks(pos)
            X, y, f, info = c2s2.build_matrix(feats, near, far, fold, fp, args.samples, SEED)
            auc, _ = c2s2.spatial_cv_auc(
                c2s2.make_model(seed=SEED),
                X,
                y,
                f,
                groups=info["spatial_blocks"],
                purge_groups=purge,
            )
            row["nuisance_c2st_auc"] = float(auc)
        row["seconds"] = round(time.time() - t0, 1)
        rows.append(row)
        print(row["id"], row["score"], {k: round(row[k]["dti"], 4) for k in truths}, flush=True)
    score = np.array([r["score"] for r in rows])
    sub = np.array([r["corroboration"] == "owner_list_snapshot" for r in rows])
    features = {
        "sgmc_far3_dti": [r["sgmc_far3"]["dti"] for r in rows],
        "sgmc_far10_dti": [r["sgmc_far10"]["dti"] for r in rows],
        "catalogue_sparse20_dti_contaminated": [
            r["catalogue_sparse20_contaminated"]["dti"] for r in rows
        ],
        "log_emitted_outside_catalogue": [np.log(r["emitted_outside_catalogue"]) for r in rows],
        "share_within3_of_catalogue": [r["share_within3_of_catalogue"] for r in rows],
        "share_in_lidar_area": [r["share_in_lidar_area"] for r in rows],
    }
    if args.audit_auc:
        features["nuisance_c2st_auc"] = [r.get("nuisance_c2st_auc", np.nan) for r in rows]
    correlations = {}
    for k, v in features.items():
        v = np.array(v, float)
        ok = np.isfinite(v)
        correlations[k] = {
            "all_artifacts": corr(v[ok], score[ok]),
            "corroborated_only": corr(v[ok & sub], score[ok & sub]),
        }
    near = np.array([r["share_within3_of_catalogue"] for r in rows])
    hi = near >= 0.45
    result = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "ledger": "registry/live_scores.json",
        "score_provenance": "owner-reported public leaderboard values; not DrivenData receipts",
        "truth_definitions": {
            "sgmc_far3/10": "USGS SGMC geologic-map faults not in the catalogue and >3/10 px from it (independent of all training labels)",
            "catalogue_sparse20_contaminated": "20% of catalogue components as truth; contaminated because the artifacts were trained on the whole catalogue",
        },
        "artifacts": rows,
        "correlations_with_live_score": correlations,
        "near_catalogue_threshold": {
            "threshold": 0.45,
            "files_at_or_above": [r["id"] for r, h in zip(rows, hi) if h],
            "scores_at_or_above": [r["score"] for r, h in zip(rows, hi) if h],
            "all_at_or_above_below_0.047": bool((score[hi] <= 0.047).all()) if hi.any() else None,
            "others_at_or_below_0.047": int((score[~hi] <= 0.047).sum()),
            "others_total": int((~hi).sum()),
        },
        "interpretation": [
            "Local and independent proxies are weak rank predictors of the live score: holdout evidence is necessary, not sufficient.",
            "Catalogue-hugging emission fails on the live board.",
        ],
    }
    args.out.write_text(json.dumps(result, indent=2, default=float) + "\n")
    print(
        json.dumps(
            {k: result[k] for k in ("correlations_with_live_score", "near_catalogue_threshold")},
            indent=1,
            default=float,
        )
    )


if __name__ == "__main__":
    main()
