#!/usr/bin/env python3
"""Required-family C2ST on labels FIRST, then individual prediction rasters.

Never uses geological point inventories or label-derived mapping features as
confounds. Missing true block membership keeps the full-audit gate BLOCKED.
An association flag is not a causal conclusion. No submission is uploaded here.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems import c2s2, confounds, footprint, holdout  # noqa: E402
from gems.validator import sha256_file  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--permutations", type=int, default=199)
    ap.add_argument("--shifts", type=int, default=99)
    ap.add_argument("--samples", type=int, default=12000)
    ap.add_argument("--candidate", type=Path)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    if args.permutations < 199 or args.shifts < 99:
        raise SystemExit(
            "Confirmatory audit requires >=199 grouped permutations and >=99 shift diagnostics"
        )
    fp = footprint.load_footprint()
    prov = json.loads((confounds.CONF / "provenance.json").read_text())
    with np.load(confounds.CONF / "confounds.npz") as cache:
        feats = confounds.classifier_features(cache)
    fold, names = holdout.make_quadrant_folds(fp)
    h, w = fp.shape
    yy, xx = np.ogrid[:h, :w]
    spatial_block = (yy // 100) * ((w + 99) // 100) + xx // 100
    purge = {}
    for f_id in range(4):
        collar = distance_transform_edt(fold != f_id) <= 15
        purge[f_id] = np.unique(spatial_block[collar & fp])
    refs = [("labels", ROOT / "data/bridge/labels.tif")]
    refs += [(tag, next((ROOT / "inputs").glob(f"*{tag}*-nan.tif"))) for tag in ("h19-4", "h19-5")]
    if args.candidate:
        refs.append(("candidate", args.candidate.resolve()))
    protocol = {
        "version": 2,
        "labels_first": True,
        "scope": "full required-family audit"
        if prov["full_requested_audit_available"]
        else "PROVISIONAL available-family diagnostic; not the requested full audit",
        "code_sha256": {
            str(p.relative_to(ROOT)): sha256_file(p)
            for p in (ROOT / "src/gems/c2s2.py", ROOT / "src/gems/holdout.py", Path(__file__))
        },
        "environment": {k: version(k) for k in ("numpy", "scipy", "scikit-learn")},
        "feature_names": sorted(feats),
        "samples_per_class": args.samples,
        "permutations": args.permutations,
        "shifts": args.shifts,
        "seed": 20261002,
        "folds": names,
        "purge": "10 km groups touching held-out region plus 1.5 km collar are excluded from training",
        "effect_rule": "Holm p<=.05 AND AUC>=.55 AND margin over grouped-null p95>=.02",
        "shift_rule": "diagnostic only, not an exact p-value on a nonstationary irregular region",
    }
    fingerprint = hashlib.sha256(
        (
            json.dumps(protocol, sort_keys=True) + sha256_file(confounds.CONF / "confounds.npz")
        ).encode()
    ).hexdigest()
    path = ROOT / "evidence/accessibility_audit_v2.json"
    old = json.loads(path.read_text()) if path.exists() and not args.force else {}
    cached = old.get("references", {}) if old.get("fingerprint") == fingerprint else {}
    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "protocol": protocol,
        "fingerprint": fingerprint,
        "source_provenance": prov,
        "references": {},
        "full_requested_audit_complete": prov["full_requested_audit_available"],
        "block_boundary_status": prov.get("block_boundary_status", "missing"),
        "blocks_official_coordinates": prov.get("blocks_official_coordinates", False),
        "interpretation": "Association test; not causal proof and not a certification of fault discovery. Missing inputs are never replaced by geological proxies.",
    }
    for label, p in refs:
        t0 = time.time()
        digest = sha256_file(p)
        if label in cached and cached[label]["sha256"] == digest:
            report["references"][label] = cached[label]
            continue
        with rasterio.open(p) as d:
            if (
                d.shape != fp.shape
                or d.crs is None
                or d.crs.to_epsg() != 32611
                or d.transform != footprint.TRANSFORM
            ):
                raise SystemExit(f"Reference grid mismatch: {p}")
            values = d.read(1)
            if label != "labels" and (
                not np.isfinite(values[fp]).all() or not np.isin(values[fp], [0, 1]).all()
            ):
                raise SystemExit(
                    "This preregistered audit uses binary emitted support; soft predictions need a new prespecified support definition"
                )
            reference = (values > (0 if label == "labels" else 0.5)) & fp
        primary = c2s2.c2s2_test(
            label,
            reference,
            feats,
            fold,
            fp,
            n_null=args.permutations,
            n_per_class=args.samples,
            null_mode="grouped",
            seed=20261002,
            purge_groups=purge,
        ).as_dict()
        shift = c2s2.c2s2_test(
            label,
            reference,
            feats,
            fold,
            fp,
            n_null=args.shifts,
            n_per_class=args.samples,
            null_mode="shift",
            seed=20261002,
            purge_groups=purge,
            shift_fn=lambda dy, dx, ref=reference: np.roll(ref, (dy, dx), axis=(0, 1)),
        ).as_dict()
        # Same-pipeline single-family AUCs diagnose what the classifier uses;
        # these are descriptive, not additional uncorrected significance claims.
        near, far, _ = c2s2.near_far_masks(reference)
        ablation = {}
        for feature in sorted(feats):
            X, y, f, info = c2s2.build_matrix(
                {feature: feats[feature]}, near, far, fold, fp, args.samples, 20261002
            )
            from threadpoolctl import threadpool_limits

            with threadpool_limits(limits=2):
                auc, _ = c2s2.spatial_cv_auc(
                    c2s2.make_model(seed=20261002),
                    X,
                    y,
                    f,
                    groups=info["spatial_blocks"],
                    purge_groups=purge,
                )
            ablation[feature] = auc
        report["references"][label] = {
            "file": str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else p.name,
            "sha256": digest,
            "positive_pixels": int(reference.sum()),
            "primary": primary,
            "shift_diagnostic": shift,
            "single_feature_auc_descriptive": ablation,
            "seconds": time.time() - t0,
        }
        path.write_text(
            json.dumps(report, indent=2) + "\n"
        )  # recoverable checkpoint, not final verdict
        print(
            label,
            "auc",
            primary["observed_auc"],
            "grouped p",
            primary["p_value"],
            "shift diagnostic p",
            shift["p_value"],
            flush=True,
        )
    values = list(report["references"].values())
    adj = c2s2.holm_adjust([v["primary"]["p_value"] for v in values])
    for v, a in zip(values, adj):
        r = v["primary"]
        r["holm_p_value"] = a
        v["meaningful_access_association_available_features"] = bool(
            a <= 0.05 and r["observed_auc"] >= 0.55 and r["margin_vs_p95"] >= 0.02
        )
        v["full_requested_audit_gate_passed"] = bool(
            report["full_requested_audit_complete"]
            and not v["meaningful_access_association_available_features"]
        )
    report["complete_run"] = True
    report["submission_slot_spent"] = False
    path.write_text(json.dumps(report, indent=2) + "\n")
    print("DONE; full requested audit complete:", report["full_requested_audit_complete"])


if __name__ == "__main__":
    main()
