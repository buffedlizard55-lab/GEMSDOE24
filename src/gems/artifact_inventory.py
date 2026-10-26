"""Git object inventory, deliberately NOT a raster or submission validator."""

from __future__ import annotations

import re
from pathlib import PurePosixPath

SCOPE = "All tracked .tif/.tiff/.zip blobs; archives and LFS pointers not decoded"


def git_sha(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{40}", value):
        raise ValueError("Expected a full Git SHA-1 object ID")
    return value


def inventory(tree, expected_tree_sha):
    """Reject partial trees: missing artifacts must never masquerade as removals."""
    if not isinstance(tree, dict) or tree.get("truncated") is not False:
        raise ValueError("Tree completeness not established")
    if git_sha(tree.get("sha")) != git_sha(expected_tree_sha):
        raise ValueError("Tree does not match the resolved immutable commit")
    if not isinstance(tree.get("tree"), list):
        raise ValueError("Missing tree entries")
    result, seen = {}, set()
    for item in tree["tree"]:
        path = item.get("path")
        if (
            not isinstance(path, str)
            or not path
            or path.startswith("/")
            or ".." in PurePosixPath(path).parts
            or path in seen
        ):
            raise ValueError("Unsafe or duplicate Git path")
        seen.add(path)
        if item.get("type") != "blob" or PurePosixPath(path).suffix.lower() not in {
            ".tif",
            ".tiff",
            ".zip",
        }:
            continue
        size = item.get("size")
        if type(size) is not int or size < 0:
            raise ValueError("Missing or invalid blob size")
        mode = item.get("mode")
        if mode not in {"100644", "100755", "120000"}:
            raise ValueError("Unexpected blob mode")
        result[path] = {
            "git_blob_sha1": git_sha(item.get("sha")),
            "bytes": size,
            "mode": mode,
            "content_validation": "not_performed",
        }
    return result


def compare(before, after):
    rows = []
    for path in sorted(before.keys() | after.keys()):
        old, new = before.get(path), after.get(path)
        state = (
            "added"
            if old is None
            else "removed"
            if new is None
            else "unchanged"
            if old == new
            else "changed"
        )
        rows.append({"path": path, "change": state, "before": old, "after": new})
    return rows


def summarize(rows):
    return {
        state: sum(r["change"] == state for r in rows)
        for state in ("added", "changed", "removed", "unchanged")
    }
