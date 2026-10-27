#!/usr/bin/env python3
"""Step-6 any-in-cell preview PNG of the recorded CGMK1 dots (display only)."""

from __future__ import annotations

import json
import struct
import zlib
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
CARD = ROOT / "evidence/cgmk1_run_card_20261027.json"
OUT = ROOT / "docs/assets/cgmk1-preview.png"


def _chunk(tag: bytes, data: bytes) -> bytes:
    crc = zlib.crc32(tag + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)


def main() -> None:
    card = json.loads(CARD.read_text())
    tif = ROOT / card["submission"]["zeros_tif_path"]
    with rasterio.open(tif) as ds:
        dots = ds.read(1) > 0
    with rasterio.open(ROOT / "data/bridge/sample_submission.tif") as ds:
        fp = np.isfinite(ds.read(1))
    assert int(dots.sum()) == card["submission"]["positive_pixels"]
    step = 6
    h, w = fp.shape
    sh, sw = h // step, w // step
    fp_s = fp[: sh * step, : sw * step].reshape(sh, step, sw, step).any(axis=(1, 3))
    d_s = dots[: sh * step, : sw * step].reshape(sh, step, sw, step).any(axis=(1, 3))
    rgb = np.full((sh, sw, 3), (244, 241, 234), dtype=np.uint8)
    rgb[fp_s] = (221, 233, 229)
    rgb[d_s] = (18, 92, 148)
    raw = b"".join(b"\x00" + rgb[y].tobytes() for y in range(sh))
    ihdr = struct.pack(">IIBBBBB", sw, sh, 8, 2, 0, 0, 0)
    OUT.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", ihdr)
        + _chunk(b"IDAT", zlib.compress(raw, level=9))
        + _chunk(b"IEND", b"")
    )
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes) from {tif.name}")


if __name__ == "__main__":
    main()
