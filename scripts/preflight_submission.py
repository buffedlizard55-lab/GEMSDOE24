#!/usr/bin/env python3
"""Fail-closed exact-file preflight for a GEMS GeoTIFF; never uploads anything.

Examples
--------
# Reproduce the active research artifact's explicit DO_NOT_SUBMIT decision.
.venv/bin/python scripts/preflight_submission.py \
  docs/downloads/gems24-aspc-20261025-6393e9d9b0df-RESEARCH-NOT-SUBMISSION-zeros.tif \
  --run-card evidence/aspc_run_card_20261025.json \
  --output docs/downloads/gems24-aspc-20261025-6393e9d9b0df-RESEARCH-NOT-SUBMISSION-zeros.preflight.json

The program reports format, strict whole-array range compatibility, hash-bound
scientific authorization and the <=140-character note independently.  A format
pass alone is never printed as authorization to use a competition slot.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems.preflight import concise_status, preflight  # noqa: E402

DEFAULT_TEMPLATE = ROOT / "data/bridge/sample_submission.tif"


def _pinned_template_sha256(template: Path) -> str | None:
    """Use the repository's pinned mirror hash only for its named template."""
    if template.resolve() != DEFAULT_TEMPLATE.resolve():
        return None
    manifest_path = ROOT / "data/manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text())
        value = manifest["files"]["bridge/sample_submission.tif"]["sha256"]
    except (OSError, KeyError, TypeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, str) else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", type=Path, help="exact .tif bytes to inspect")
    parser.add_argument(
        "--template",
        type=Path,
        default=DEFAULT_TEMPLATE,
        help="submission-grid template (default: pinned bridge sample)",
    )
    parser.add_argument(
        "--run-card",
        type=Path,
        default=None,
        help="hash-bound promotion run card; omitted means DO_NOT_SUBMIT",
    )
    notes = parser.add_mutually_exclusive_group()
    notes.add_argument("--note", default=None, help="exact optional submission note")
    notes.add_argument("--note-file", type=Path, default=None, help="file containing the exact note")
    parser.add_argument(
        "--expected-template-sha256",
        default=None,
        help="pin a custom template by SHA-256; required for OK_TO_SUBMIT with custom templates",
    )
    parser.add_argument("--output", type=Path, default=None, help="write full JSON receipt here")
    args = parser.parse_args()

    note = args.note
    if args.note_file is not None:
        note = args.note_file.read_text().rstrip("\r\n")
    expected = args.expected_template_sha256 or _pinned_template_sha256(args.template)
    report = preflight(
        args.artifact,
        args.template,
        run_card_path=args.run_card,
        note=note,
        expected_template_sha256=expected,
    )
    encoded = json.dumps(report, indent=2, allow_nan=False) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded)
    print(concise_status(report))
    print(json.dumps(report["decision"], indent=2, allow_nan=False))
    # A negative scientific decision is an expected research outcome, not a
    # process error.  Callers should inspect the JSON rather than infer success
    # from a non-zero exit code.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
