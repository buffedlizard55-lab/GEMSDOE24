#!/usr/bin/env python3
"""Extract a compact, label-free flight/line/date/position table from the official
GeoDAWN radiometric profile CSVs (USGS ScienceBase item 657e1d85d34e23d3533209f7).

Why: the official report states that the survey was split into four acquisition
blocks, each with its own base of operations, and gives the fixed-wing flight
number range of each block. The flight-path shapefiles carry only ``Line``; the
profile databases carry ``Line``, ``flight``, ``date``, ``x`` and ``y``. This
script exports only what is needed to *derive and audit* block membership:

* one summary row per (area, line, flight, date): fiducial count, bbox, centroid,
  along-line length and mean terrain clearance,
* a thinned fiducial sample (about one point per 500 m of line) for assigning
  every raster pixel to the nearest acquisition fiducial.

Nothing here touches labels. Raw bulk files are streamed and never committed.
Run on GitHub-hosted CI (ScienceBase is unreachable from the Arena sandbox) or
locally; ``--local-zip`` supports offline tests with a synthetic archive.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import re
import sys
import time
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/external/audit_sources"
ITEM = "https://www.sciencebase.gov/catalog/item/657e1d85d34e23d3533209f7?format=json"
WANTED = {"a1": "22103_spec_a1_csv.zip", "a2": "22103_spec_a2_csv.zip"}
STEP_M = 500.0  # target along-line spacing of the exported fiducial sample
MAX_GAP_M = 2000.0  # a longer jump between consecutive fiducials is not flight line length
KEYS = ["line", "flight", "date"]
REQUIRED = {"line", "flight", "x", "y"}
OPTIONAL = {"date", "dem", "drape", "gps_elev", "calc_radar"}


def normalise(name: str) -> str:
    return re.sub(r"^[\s/#'\"]+|[\s'\"]+$", "", str(name)).strip().lower()


def sniff_header(lines: list[str]) -> tuple[int, list[str]]:
    """Return (zero-based header row, normalised names). Fails loudly if absent."""
    for i, raw in enumerate(lines):
        cells = [normalise(c) for c in raw.rstrip("\r\n").split(",")]
        if REQUIRED <= set(cells):
            return i, cells
    raise ValueError("No header row containing Line/flight/x/y in the first lines")


def parse_stream(opener, area: str, *, chunk_rows: int = 400_000, step_m: float = STEP_M):
    """Stream one CSV. ``opener`` returns a fresh binary file object each call."""
    with opener() as fh:
        head = [fh.readline().decode("utf-8", "replace") for _ in range(200)]
    header_row, names = sniff_header(head)
    usecols = [i for i, n in enumerate(names) if n in REQUIRED | OPTIONAL]
    used = [names[i] for i in usecols]
    acc: dict[tuple, dict] = {}
    samples: list[pd.DataFrame] = []
    prev = None  # last row of the previous chunk (for continuity)
    carry_cum = 0.0  # along-line distance accumulated in the open line
    rows_total = 0
    first_rows: list[str] = []
    with opener() as fh:
        reader = pd.read_csv(
            io.TextIOWrapper(fh, encoding="utf-8", errors="replace"),
            skiprows=header_row + 1,
            header=None,
            usecols=usecols,
            names=None,
            chunksize=chunk_rows,
            dtype=str,
            low_memory=False,
        )
        for chunk in reader:
            chunk.columns = [names[i] for i in sorted(usecols)]
            if not first_rows:
                first_rows = chunk.head(2).astype(str).agg(",".join, axis=1).tolist()
            for c in ("x", "y", "dem", "drape", "gps_elev", "calc_radar"):
                if c in chunk:
                    chunk[c] = pd.to_numeric(chunk[c], errors="coerce")
            if "date" not in chunk:
                chunk["date"] = ""
            chunk["line"] = chunk["line"].astype(str).str.strip()
            chunk["flight"] = pd.to_numeric(chunk["flight"], errors="coerce")
            chunk = chunk.dropna(subset=["x", "y", "flight"]).reset_index(drop=True)
            if chunk.empty:
                continue
            chunk["flight"] = chunk["flight"].astype(int)
            rows_total += len(chunk)
            if prev is not None:
                joined = pd.concat([prev, chunk], ignore_index=True)
                offset = 1
            else:
                joined, offset = chunk, 0
            # Plain numpy/object arrays: pandas 3 string dtypes would return
            # nullable-boolean arrays that do not compose with numpy masks.
            lv = joined["line"].to_numpy(dtype=object)
            dv = joined["date"].to_numpy(dtype=object)
            fv = joined["flight"].to_numpy()
            same = (lv[1:] == lv[:-1]) & (fv[1:] == fv[:-1]) & (dv[1:] == dv[:-1])
            same = np.asarray(same, dtype=bool)
            dx = np.diff(joined["x"].to_numpy(dtype=float))
            dy = np.diff(joined["y"].to_numpy(dtype=float))
            seg = np.hypot(dx, dy)
            ok = same & (seg < MAX_GAP_M)
            seg = np.where(ok, seg, 0.0)
            gap = same & (seg == 0.0) & (np.hypot(dx, dy) >= MAX_GAP_M)
            seg_full = np.r_[0.0, seg][offset:]
            same_full = np.r_[False, same][offset:]
            gap_full = np.r_[False, gap][offset:]
            chunk["seg_m"] = seg_full
            chunk["same_prev"] = same_full
            chunk["new_run"] = ~same_full
            chunk["gap"] = gap_full
            if "calc_radar" in chunk:
                chunk["clear"] = chunk["calc_radar"]
            elif "gps_elev" in chunk and "dem" in chunk:
                chunk["clear"] = chunk["gps_elev"] - chunk["dem"]
            else:
                chunk["clear"] = np.nan
            chunk["drape_h"] = (
                chunk["drape"] - chunk["dem"] if {"drape", "dem"} <= set(chunk) else np.nan
            )
            grouped = chunk.groupby(KEYS, sort=False)
            stats = grouped.agg(
                n=("x", "size"),
                sx=("x", "sum"),
                sy=("y", "sum"),
                xmin=("x", "min"),
                xmax=("x", "max"),
                ymin=("y", "min"),
                ymax=("y", "max"),
                km=("seg_m", "sum"),
                gaps=("gap", "sum"),
                runs=("new_run", "sum"),
                clear_sum=("clear", "sum"),
                clear_n=("clear", "count"),
                drape_sum=("drape_h", "sum"),
                drape_n=("drape_h", "count"),
            )
            for key, r in stats.iterrows():
                a = acc.get(key)
                if a is None:
                    acc[key] = r.to_dict()
                else:
                    for f in ("n", "sx", "sy", "km", "gaps", "runs", "clear_sum", "clear_n"):
                        a[f] += r[f]
                    a["drape_sum"] += r["drape_sum"]
                    a["drape_n"] += r["drape_n"]
                    a["xmin"] = min(a["xmin"], r["xmin"])
                    a["xmax"] = max(a["xmax"], r["xmax"])
                    a["ymin"] = min(a["ymin"], r["ymin"])
                    a["ymax"] = max(a["ymax"], r["ymax"])
            # Thinned sample: first fiducial of every new run plus the first fiducial
            # of each new ``step_m`` along-line bin. ``carry_cum`` is the along-line
            # distance already accumulated in a run that continues across chunks.
            n = len(chunk)
            sp = chunk["same_prev"].to_numpy()
            sg = chunk["seg_m"].to_numpy()
            new_line = ~sp
            idx = np.arange(n)
            run_start = np.maximum.accumulate(np.where(new_line, idx, 0))
            cs = np.cumsum(sg)
            within = cs - (cs[run_start] - sg[run_start])
            continues = bool(sp[0])
            if continues:
                within = within + np.where(run_start == 0, carry_cum, 0.0)
            bins = np.floor(within / step_m)
            first_prev_bin = np.floor(carry_cum / step_m) if continues else -1.0
            prev_bin = np.r_[first_prev_bin, bins[:-1]]
            keep = new_line | (bins != prev_bin)
            carry_cum = float(within[-1])
            take = chunk.loc[keep, ["line", "flight", "date", "x", "y", "clear"]].copy()
            take["area"] = area
            samples.append(take)
            prev = chunk.tail(1)[["line", "flight", "date", "x", "y"]]
    rows = []
    for (line, flight, date), a in acc.items():
        n = max(int(a["n"]), 1)
        rows.append(
            {
                "area": area,
                "line": line,
                "flight": int(flight),
                "date": date,
                "n_fiducials": int(a["n"]),
                "x_mean": a["sx"] / n,
                "y_mean": a["sy"] / n,
                "xmin": a["xmin"],
                "xmax": a["xmax"],
                "ymin": a["ymin"],
                "ymax": a["ymax"],
                "km": a["km"] / 1000.0,
                "gaps_over_2km": int(a["gaps"]),
                "runs": int(a["runs"]),
                "clearance_mean_m": a["clear_sum"] / a["clear_n"] if a["clear_n"] else np.nan,
                "drape_height_mean_m": a["drape_sum"] / a["drape_n"] if a["drape_n"] else np.nan,
            }
        )
    summary = pd.DataFrame(rows)
    sample = pd.concat(samples, ignore_index=True) if samples else pd.DataFrame()
    info = {
        "header_row": header_row,
        "columns_used": used,
        "rows": rows_total,
        "first_rows": first_rows,
        "groups": len(summary),
    }
    return summary, sample, info


def md5_sha256(path: Path):
    m, s = hashlib.md5(), hashlib.sha256()  # noqa: S324 - ScienceBase publishes MD5
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            m.update(block)
            s.update(block)
    return m.hexdigest(), s.hexdigest()


def download(url: str, dest: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "GEMS-reproducible-source-audit/3.0"})
    last = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=600) as r, open(dest, "wb") as out:
                if r.status != 200:
                    raise ValueError(f"HTTP {r.status}")
                while True:
                    block = r.read(1 << 20)
                    if not block:
                        break
                    out.write(block)
            return
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(2 ** (attempt + 1))
    raise RuntimeError(f"download failed after retries: {last}")


def process_zip(path: Path, area: str):
    summaries, samples, members = [], [], []
    with zipfile.ZipFile(path) as z:
        csvs = sorted(n for n in z.namelist() if n.lower().endswith(".csv"))
        if not csvs:
            raise RuntimeError(f"No CSV member in {path.name}: {z.namelist()[:10]}")
        for name in csvs:
            t0 = time.time()
            summary, sample, info = parse_stream(lambda n=name: z.open(n), area)
            info.update(member=name, seconds=round(time.time() - t0, 1))
            members.append(info)
            summaries.append(summary)
            samples.append(sample)
            print(json.dumps({k: v for k, v in info.items() if k != "first_rows"}), flush=True)
    return pd.concat(summaries, ignore_index=True), pd.concat(samples, ignore_index=True), members


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workdir", type=Path, default=ROOT / "data/raw/geodawn_profiles")
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--local-zip", nargs=2, metavar=("AREA", "PATH"), action="append")
    args = ap.parse_args()
    args.workdir.mkdir(parents=True, exist_ok=True)
    args.out.mkdir(parents=True, exist_ok=True)
    receipt = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "item": ITEM,
        "doi": "10.5066/P93LGLVQ",
        "step_m": STEP_M,
        "files": [],
        "label_free": True,
    }
    jobs = []
    if args.local_zip:
        jobs = [(a, Path(p), None, None) for a, p in args.local_zip]
    else:
        item = json.loads(
            urllib.request.urlopen(
                urllib.request.Request(
                    ITEM, headers={"User-Agent": "GEMS-reproducible-source-audit/3.0"}
                ),
                timeout=120,
            ).read()
        )
        files = {f["name"]: f for f in item.get("files", [])}
        for area, name in WANTED.items():
            rec = files.get(name)
            if rec is None:
                raise SystemExit(f"Official file not attached to ScienceBase item: {name}")
            dest = args.workdir / name
            t0 = time.time()
            download(rec["url"], dest)
            print("downloaded", name, dest.stat().st_size, f"{time.time() - t0:.0f}s", flush=True)
            jobs.append((area, dest, rec.get("checksum", {}).get("value"), rec))
    all_summary, all_sample = [], []
    for area, path, expected_md5, rec in jobs:
        md5, sha = md5_sha256(path)
        entry = {
            "area": area,
            "file": path.name,
            "bytes": path.stat().st_size,
            "md5": md5,
            "sha256": sha,
            "sciencebase_md5": expected_md5,
            "md5_matches_sciencebase": (md5 == expected_md5) if expected_md5 else None,
        }
        if expected_md5 and md5 != expected_md5:
            raise SystemExit(f"Checksum mismatch for {path.name}: {md5} != {expected_md5}")
        summary, sample, members = process_zip(path, area)
        entry["members"] = members
        receipt["files"].append(entry)
        all_summary.append(summary)
        all_sample.append(sample)
    summary = pd.concat(all_summary, ignore_index=True).sort_values(
        ["area", "flight", "date", "line"]
    )
    sample = pd.concat(all_sample, ignore_index=True)
    summary.to_csv(args.out / "geodawn_line_flight_summary.csv", index=False, float_format="%.3f")
    buf = io.StringIO()
    sample.to_csv(buf, index=False, float_format="%.1f")
    with gzip.open(args.out / "geodawn_fiducial_sample.csv.gz", "wt", compresslevel=9) as gz:
        gz.write(buf.getvalue())
    receipt["summary_rows"] = int(len(summary))
    receipt["sample_rows"] = int(len(sample))
    receipt["total_km_by_area"] = {
        a: float(summary.loc[summary["area"] == a, "km"].sum()) for a in summary["area"].unique()
    }
    receipt["flights_by_area"] = {
        a: sorted(int(f) for f in summary.loc[summary["area"] == a, "flight"].unique())
        for a in summary["area"].unique()
    }
    (args.out / "geodawn_profile_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({k: v for k, v in receipt.items() if k != "files"}, indent=2)[:3000])


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001
        print(f"FATAL {type(exc).__name__}: {exc}", file=sys.stderr)
        raise
