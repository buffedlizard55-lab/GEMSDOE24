#!/usr/bin/env python3
"""Summarise the official GeoDAWN flight-path shapefiles (label-free) for block derivation.

The report (USGS ScienceBase 657e1d85d34e23d3533209f7, DOI 10.5066/P93LGLVQ) says the survey was flown
as four acquisition blocks with independent bases and publishes each block's line-kilometres
(Winnemucca 62,530 · Fallon 43,500 · Hawthorne 21,400 · Tonopah 21,600; total 149,030). The flight-path
shapefiles carry only ``Line`` and geometry, so this script exports per-line length/extent plus a thinned
vertex sample. A block derivation from these is only accepted if it reproduces the published totals.

Anonymous HTTPS only; every download is verified against the ScienceBase MD5 and the recorded size.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import sys
import time
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import shapefile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/external/audit_sources"
ITEM = "https://www.sciencebase.gov/catalog/item/657e1d85d34e23d3533209f7?format=json"
FILES = {"a1": "area1_flight_path.zip", "a2": "area2_flight_path.zip"}
STEP_M = 500.0


def line_stats(points, parts, step_m=STEP_M):
    """Length (m), extent, mean heading and a ~step_m vertex sample over all parts of one line."""
    pts = np.asarray(points, float)[:, :2]
    bounds = list(parts) + [len(pts)]
    length, sample = 0.0, []
    for a, b in zip(bounds[:-1], bounds[1:]):
        seg = pts[a:b]
        if len(seg) < 2:
            if len(seg):
                sample.append(seg[0])
            continue
        d = np.hypot(*np.diff(seg, axis=0).T)
        cum = np.r_[0.0, np.cumsum(d)]
        length += float(cum[-1])
        keep = np.r_[True, np.floor(cum[1:] / step_m) != np.floor(cum[:-1] / step_m)]
        sample.extend(seg[keep])
    first, last = pts[0], pts[-1]
    heading = float(np.degrees(np.arctan2(last[0] - first[0], last[1] - first[1])) % 180.0)
    return {
        "n_pts": int(len(pts)),
        "km": length / 1000.0,
        "xmin": float(pts[:, 0].min()),
        "xmax": float(pts[:, 0].max()),
        "ymin": float(pts[:, 1].min()),
        "ymax": float(pts[:, 1].max()),
        "x_mean": float(pts[:, 0].mean()),
        "y_mean": float(pts[:, 1].mean()),
        "heading_deg": heading,
    }, np.asarray(sample)


def read_zip_shapefile(zbytes: bytes):
    z = zipfile.ZipFile(io.BytesIO(zbytes))
    stem = next(n[:-4] for n in z.namelist() if n.lower().endswith(".shp"))
    return shapefile.Reader(
        shp=io.BytesIO(z.read(stem + ".shp")),
        shx=io.BytesIO(z.read(stem + ".shx")),
        dbf=io.BytesIO(z.read(stem + ".dbf")),
    )


def summarise(reader, area):
    fields = [f[0] for f in reader.fields[1:]]
    if "Line" not in fields:
        raise ValueError(f"No Line field in {fields}")
    rows, samples = [], []
    for sr in reader.iterShapeRecords():
        rec = dict(zip(fields, sr.record))
        stats, sample = line_stats(sr.shape.points, sr.shape.parts or [0])
        rows.append({"area": area, "line": str(rec["Line"]).strip(), **stats})
        for x, y in sample:
            samples.append((area, str(rec["Line"]).strip(), round(float(x), 1), round(float(y), 1)))
    return pd.DataFrame(rows), pd.DataFrame(samples, columns=["area", "line", "x", "y"])


def download(rec, dest, attempts=3):
    last = None
    for k in range(attempts):
        try:
            req = urllib.request.Request(
                rec["url"], headers={"User-Agent": "GEMS-reproducible-source-audit/3.0"}
            )
            with urllib.request.urlopen(req, timeout=900) as r:
                data = r.read()
            md5 = hashlib.md5(data).hexdigest()  # noqa: S324 - ScienceBase publishes MD5
            want = (rec.get("checksum") or {}).get("value")
            if data[:4] != b"PK\x03\x04" or len(data) != int(rec.get("size") or len(data)):
                raise ValueError(f"not the archive: {len(data)} bytes, head={data[:60]!r}")
            if want and md5 != want:
                raise ValueError(f"MD5 {md5} != ScienceBase {want}")
            dest.write_bytes(data)
            return data, md5
        except Exception as e:  # noqa: BLE001
            last = e
            print("download attempt failed:", repr(e)[:300], flush=True)
            time.sleep(2 ** (k + 1))
    raise RuntimeError(f"download failed: {last}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workdir", type=Path, default=ROOT / "data/raw/geodawn_paths")
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--local-zip", nargs=2, metavar=("AREA", "PATH"), action="append")
    args = ap.parse_args()
    args.workdir.mkdir(parents=True, exist_ok=True)
    args.out.mkdir(parents=True, exist_ok=True)
    receipt = {"generated_utc": datetime.now(timezone.utc).isoformat(), "item": ITEM, "files": []}
    frames, samples = [], []
    if args.local_zip:
        sources = [(a, Path(p).read_bytes(), None, Path(p).name) for a, p in args.local_zip]
    else:
        item = json.loads(
            urllib.request.urlopen(
                urllib.request.Request(
                    ITEM, headers={"User-Agent": "GEMS-reproducible-source-audit/3.0"}
                ),
                timeout=120,
            ).read()
        )
        by_name = {f["name"]: f for f in item.get("files", [])}
        sources = []
        for area, name in FILES.items():
            rec = by_name.get(name)
            if rec is None:
                raise SystemExit(f"not attached to the item: {name}")
            print(
                "record",
                json.dumps({k: rec.get(k) for k in ("name", "size", "checksum", "url")}),
                flush=True,
            )
            data, md5 = download(rec, args.workdir / name)
            sources.append((area, data, md5, name))
    for area, data, md5, name in sources:
        t0 = time.time()
        df, sm = summarise(read_zip_shapefile(data), area)
        frames.append(df)
        samples.append(sm)
        receipt["files"].append(
            {
                "area": area,
                "file": name,
                "bytes": len(data),
                "md5": md5,
                "sha256": hashlib.sha256(data).hexdigest(),
                "lines": int(len(df)),
                "km": float(df["km"].sum()),
                "seconds": round(time.time() - t0, 1),
            }
        )
        print(json.dumps(receipt["files"][-1]), flush=True)
    summary = pd.concat(frames, ignore_index=True)
    sample = pd.concat(samples, ignore_index=True)
    summary.to_csv(args.out / "geodawn_flight_line_summary.csv", index=False, float_format="%.3f")
    buf = io.StringIO()
    sample.to_csv(buf, index=False)
    with gzip.open(args.out / "geodawn_flight_path_sample.csv.gz", "wt", compresslevel=9) as gz:
        gz.write(buf.getvalue())
    receipt["total_km"] = float(summary["km"].sum())
    receipt["lines"] = int(len(summary))
    receipt["sample_rows"] = int(len(sample))
    (args.out / "geodawn_flight_path_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({k: v for k, v in receipt.items() if k != "files"}), flush=True)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001
        print(f"FATAL {type(exc).__name__}: {exc}", file=sys.stderr)
        raise
