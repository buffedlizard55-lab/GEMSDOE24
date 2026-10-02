#!/usr/bin/env python3
"""Restore hash-pinned competition inputs and official-source mirror assets.

Reads public GitHub blobs through gh, never writes another branch or stores tokens.
Large downloads/caches stay ignored. Small bridge files already shipped here are
verified before use. Organizer authentication is NOT bypassed: the owner supplied
these mirrors. A bridge hash is an integrity receipt, not organizer certification.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems.validator import sha256_file  # noqa: E402

CORE_REF = "c0c06ac82178f26b94fce3397036ef8f12a2f3a0"
CORE_HASH = "4371c82e3b8339b807bdffcf4ef59a225520fe2988d521be208ae33743123bc5"


def gh_bytes(repo: str, path: str, ref: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".partial")
    try:
        with tmp.open("wb") as out:
            subprocess.run(
                [
                    "gh",
                    "api",
                    f"repos/{repo}/contents/{path}?ref={ref}",
                    "-H",
                    "Accept: application/vnd.github.raw",
                ],
                stdout=out,
                check=True,
            )
        tmp.replace(dest)
    finally:
        tmp.unlink(missing_ok=True)
    return dest


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--access-mirrors",
        "--roads",
        action="store_true",
        help="also restore TIGER roads (not claims)",
    )
    args = ap.parse_args()
    manifest = json.loads((ROOT / "data" / "manifest.json").read_text())["files"]
    checked = []
    for name in ("bridge/labels.tif", "bridge/existing_faults.tif", "bridge/sample_submission.tif"):
        p = ROOT / "data" / name
        actual = sha256_file(p)
        if actual != manifest[name]["sha256"]:
            raise SystemExit(f"Integrity mismatch: {name}")
        checked.append({"file": name, "sha256": actual, "verified": True})
    features = ROOT / "data" / "training_features.tif"
    if not features.exists() or sha256_file(features) != CORE_HASH:
        parts = ROOT / "data" / "raw" / "bridge_parts"
        names = [f"gems-geodawn-numerical-features.tif.part-{i:03}" for i in range(5)]

        def get(name: str) -> Path:
            p = parts / name
            if not p.exists():
                gh_bytes("buffedlizard55-lab/GEMSDOE", f"data/bridge/{name}", CORE_REF, p)
            return p

        with ThreadPoolExecutor(max_workers=3) as ex:
            downloaded = list(ex.map(get, names))
        tmp = features.with_suffix(".partial")
        with tmp.open("wb") as out:
            for p in downloaded:
                with p.open("rb") as src:
                    for chunk in iter(lambda: src.read(1 << 20), b""):
                        out.write(chunk)
        if sha256_file(tmp) != CORE_HASH:
            tmp.unlink(missing_ok=True)
            raise SystemExit("Competition bridge hash mismatch; refusing to use it")
        tmp.replace(features)
        # Assembly is cheap to repeat, avoid retaining duplicate 419 MB parts.
        for p in downloaded:
            p.unlink()
    checked.append(
        {
            "file": "training_features.tif",
            "sha256": sha256_file(features),
            "bytes": features.stat().st_size,
            "verified": True,
            "mirror_ref": CORE_REF,
            "provenance_status": "owner-supplied bridge, not organizer-authenticated",
        }
    )
    if args.access_mirrors:
        road_manifest = json.loads((ROOT / "data/road_mirror_manifest.json").read_text())
        repo, ref = road_manifest["repo"], road_manifest["ref"]

        def restore(row: dict) -> dict:
            path = row["path"]
            p = ROOT / "data/raw/access_mirrors" / Path(path).name
            if not p.exists() or sha256_file(p) != row["sha256"]:
                gh_bytes(repo, path, ref, p)
            actual = sha256_file(p)
            if actual != row["sha256"]:
                raise SystemExit(f"Pinned TIGER mirror integrity mismatch: {p.name}")
            return {
                "file": str(p.relative_to(ROOT)),
                "sha256": actual,
                "mirror_ref": ref,
                "remote_path": path,
            }

        with ThreadPoolExecutor(max_workers=4) as ex:
            checked.extend(ex.map(restore, road_manifest["files"]))
    receipt = {
        "files": checked,
        "integrity_only": True,
        "warning": "Hash-pinned mirrors do not certify organizer provenance. No mining-claim or four-block proxy is silently substituted.",
    }
    (ROOT / "evidence" / "data_restore.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
