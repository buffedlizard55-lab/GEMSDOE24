"""Line-by-line verification of every data asset committed in this repository.

Checks performed on each raster:
  * SHA-256 + byte size (compared against the 19GEMSDOE registry where a reference exists)
  * CRS / transform / shape / dtype / band count vs the official grid
    (EPSG:32611, 100 m, 3292 x 3730, transform (100,0,243350,0,-100,4508550))
  * footprint statistics (pixels>0 inside the 5,167,373-pixel scored footprint)
  * labels.tif vs existing_faults.tif vs sample_submission.tif pixel-set identities
  * submission candidates (inputs/): range [0,1] on all footprint pixels, NaN outside

Writes evidence/data_verification.json and data/bridge/manifest.json.
Every "expected" value below was itself transcribed from the sibling repository
19GEMSDOE/evidence/data_verification.json (a prior session's measured record); a
mismatch is reported, never silently tolerated.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems.footprint import load_footprint  # noqa: E402

OFFICIAL = {
    "width": 3292,
    "height": 3730,
    "crs": "EPSG:32611",
    "transform": [100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0],
}
# Reference hashes transcribed from 19GEMSDOE evidence (prior session measurement).
EXPECTED_SHA = {
    "labels.tif": "7ba308ccdc4418b31a178f4f1ef21aaa6e152e4028f2f6f64b01f7eb25ae4093",
    "training_features.tif": "4371c82e3b8339b807bdffcf4ef59a225520fe2988d521be208ae33743123bc5",
}
# H19-4 / H19-4-allfinite SHA-256 published by 19GEMSDOE/docs/index.html
EXPECTED_SHA_SUBS = {
    "gems19-h19-4-multiline-corroborated-openness-thermal-pop-20260930-691e4dfa-nan.tif": "89109a3bd2cd3b12e7a0f388113c519843acfc9c4f46825affefc3e63dd99b22",
}


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def raster_info(p: Path) -> dict:
    with rasterio.open(p) as s:
        info = {
            "shape": [s.height, s.width],
            "count": s.count,
            "dtype": s.dtypes[0],
            "crs": str(s.crs),
            "transform": list(s.transform)[:6] if s.transform else None,
        }
        band1 = s.read(1, masked=False).astype(np.float32)
    fp = load_footprint()
    info["sha256"] = sha256(p)
    info["bytes"] = p.stat().st_size
    if band1.shape == fp.shape:
        info["grid_matches_official"] = (
            info["crs"] == OFFICIAL["crs"]
            and info["shape"] == [OFFICIAL["height"], OFFICIAL["width"]]
            and np.allclose(info["transform"], OFFICIAL["transform"])
        )
        inside = band1[fp]
        info["inside_footprint"] = {
            "n": int(fp.sum()),
            "n_finite": int(np.isfinite(inside).sum()),
            "min": float(np.nanmin(inside)) if np.isfinite(inside).any() else None,
            "max": float(np.nanmax(inside)) if np.isfinite(inside).any() else None,
            "n_positive": int(np.nansum(inside > 0)),
            "n_nan": int(np.isnan(inside).sum()),
        }
        outside = band1[~fp]
        info["outside_footprint"] = {
            "n": int((~fp).sum()),
            "all_nan": bool(np.all(np.isnan(outside))),
            "n_nonzero": int(np.nansum(outside != 0)),
        }
    return info


def main() -> None:
    (ROOT / "evidence").mkdir(exist_ok=True)
    report: dict = {
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "official_grid": OFFICIAL,
        "files": {},
        "identity_checks": {},
        "anomalies": [],
    }
    targets = []
    for d in ["data/bridge", "data/external", "inputs"]:
        for p in sorted((ROOT / d).glob("*")):
            if p.suffix.lower() in {".tif", ".tiff"}:
                targets.append(p)
    rasters: dict[str, np.ndarray] = {}
    for p in targets:
        info = raster_info(p)
        report["files"][f"{p.parent.name}/{p.name}"] = info
        if info.get("grid_matches_official") is False:
            report["anomalies"].append(f"{p.name}: grid does not match official template")
        with rasterio.open(p) as s:
            if s.count == 1 and s.height == OFFICIAL["height"]:
                rasters[p.name] = s.read(1)
        for key, exp in EXPECTED_SHA.items():
            if p.name == key and info["sha256"] != exp:
                report["anomalies"].append(f"{p.name}: sha256 != registry reference {exp[:12]}")
        for key, exp in EXPECTED_SHA_SUBS.items():
            if p.name == key:
                info["registry_expected_sha256"] = exp
                if info["sha256"] != exp:
                    report["anomalies"].append(f"{p.name}: sha256 != 19GEMSDOE site sha")

    fp = load_footprint()
    report["footprint"] = {
        "pixels": int(fp.sum()),
        "expected": 5_167_373,
        "match": int(fp.sum()) == 5_167_373,
    }
    if "labels.tif" in rasters and "existing_faults.tif" in rasters:
        lab = rasters["labels.tif"] > 0
        exf = rasters["existing_faults.tif"] > 0
        report["identity_checks"]["labels_eq_existing_faults_on_footprint"] = {
            "labels_px": int(lab[fp].sum()),
            "existing_px": int(exf[fp].sum()),
            "xor": int(np.logical_xor(lab, exf)[fp].sum()),
        }
        if int(np.logical_xor(lab, exf)[fp].sum()) != 0:
            report["anomalies"].append(
                "labels.tif != existing_faults.tif on footprint (expected identical: catalogue)"
            )
    if "labels.tif" in rasters and "sample_submission.tif" in rasters:
        lab = rasters["labels.tif"] > 0
        ss = rasters["sample_submission.tif"]
        onelike = np.isclose(ss, 1.0)
        report["identity_checks"]["sample_submission_is_known_faults"] = {
            "sample_n_ones": int(onelike[fp].sum()),
            "equals_labels_set": bool(np.array_equal(onelike[fp], lab[fp])),
        }
    for p in Path(ROOT / "inputs").glob("*-nan.tif"):
        a = rasters[p.name]
        inside = a[fp]
        ok = bool(
            np.isfinite(inside).all() and np.nanmin(inside) >= 0.0 and np.nanmax(inside) <= 1.0
        )
        report["identity_checks"][f"range_ok[{p.name}]"] = {
            "min": float(np.nanmin(inside)),
            "max": float(np.nanmax(inside)),
            "n_nonfinite_inside": int(np.count_nonzero(~np.isfinite(inside))),
            "pass": ok,
        }
        if not ok:
            report["anomalies"].append(
                f"{p.name}: values outside [0,1] or non-finite inside footprint"
            )

    out = ROOT / "evidence" / "data_verification.json"
    out.write_text(json.dumps(report, indent=2) + "\n")

    manifest = {
        "generated_utc": report["generated_utc"],
        "note": "Small bridge + external assets committed for reproducibility. "
        "Competition originals: https://www.drivendata.org/competitions/306/competition-doe-gems/data/ "
        "(login required). External sources documented in registry/sources.json.",
        "files": {
            k: {"sha256": v["sha256"], "bytes": v["bytes"]} for k, v in report["files"].items()
        },
    }
    (ROOT / "data" / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(
        json.dumps(
            {
                "anomalies": report["anomalies"],
                "footprint": report["footprint"],
                "labels": report["identity_checks"].get("labels_eq_existing_faults_on_footprint"),
                "sample": report["identity_checks"].get("sample_submission_is_known_faults"),
            },
            indent=1,
        )
    )


if __name__ == "__main__":
    main()
