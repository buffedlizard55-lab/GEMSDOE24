"""Fail-closed identity checks for published research downloads, not promotion."""

from __future__ import annotations

import json
from pathlib import Path

from .validator import sha256_file


def research_receipt(downloads: Path, row: dict, *, template: Path | None = None) -> dict:
    """Bind filename, bytes and all format decisions; optionally revalidate the raster.

    Static Pages builds can check retained receipts without bulk inputs. Independent
    audits must supply the pinned organizer template to reopen and recheck bytes.
    No receipt can grant authorization through this research-only entry point.
    """
    name = row["file"]
    if not isinstance(name, str) or Path(name).name != name or not name.endswith(".tif"):
        raise ValueError("Research filename must be a local TIFF basename")
    path = downloads / name
    digest = sha256_file(path)
    checks = json.loads(path.with_suffix(".checks.json").read_text())
    if digest != row["sha256"] or checks.get("sha256") != digest:
        raise ValueError("Research bytes and format receipt identity disagree")
    if checks.get("file") != name:
        raise ValueError("Research format receipt filename disagrees")
    if row.get("submission_authorized") is not False:
        raise ValueError("Research row must explicitly deny authorization")
    if row.get("validator_output", checks) != checks:
        raise ValueError("Embedded validator output disagrees with sidecar")
    if checks.get("format_valid") is not True or checks.get("format_acceptable") is not True:
        raise ValueError("Research format receipt is not passing")
    if checks.get("hard_failures") != [] or not checks.get("checks"):
        raise ValueError("Research receipt has missing checks or hard failures")
    if any(
        c.get("hard_requirement") and c.get("pass") is not True for c in checks["checks"].values()
    ):
        raise ValueError("Research receipt contradicts a hard requirement")
    if checks.get("submission_authorized") is not False or checks.get("ok_to_upload") is not False:
        raise ValueError("Research receipt cannot grant upload authorization")
    if template is not None:
        from .submission import check_variants

        fresh = check_variants(path, template)
        # New shared-validator versions may add this explanatory annotation.
        # Ignore only that non-decision prose, never a check or authorization flag.
        fresh_comparable = {k: v for k, v in fresh.items() if k != "upload_authorization"}
        recorded_comparable = {k: v for k, v in checks.items() if k != "upload_authorization"}
        if fresh_comparable != recorded_comparable:
            raise ValueError("Fresh exact-file validation disagrees with retained receipt")
    return checks
