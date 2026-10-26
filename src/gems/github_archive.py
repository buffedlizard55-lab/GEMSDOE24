"""Public, hash-verified GitHub archive transport for regenerable caches.

Uses the public codeload endpoint, not authenticated API quota or portal access.
Only requested regular files are written; archive paths are never extracted.
"""

from __future__ import annotations

import hashlib
import re
import tarfile
import urllib.request
from pathlib import Path, PurePosixPath


class NoRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("Archive redirects are refused; only the pinned codeload host is allowed")


def safe_relative(value: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if not value or path.is_absolute() or ".." in path.parts or "\\" in value:
        raise ValueError("Unsafe archive/cache path")
    return path


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def cache_archive(repo, ref, cache_dir, *, requested=None, select=None, max_file_bytes=60_000_000):
    """Cache selected regular files under ``cache_dir/repo/ref`` with identities.

    ``requested`` maps exact paths to optional expected Git-blob SHA1s. When
    discovering a new snapshot, ``select`` chooses paths; no arbitrary tar member
    is ever passed to extract(). Missing requested files are a hard failure.
    """
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        raise ValueError("Expected a GitHub owner/repository")
    if not re.fullmatch(r"[a-f0-9]{40}", ref):
        raise ValueError("Archive ref must be a complete immutable commit SHA")
    if (requested is None) == (select is None):
        raise ValueError("Specify exact requested files or one discovery selector")
    if max_file_bytes < 1:
        raise ValueError("Positive archive member limit required")
    if requested is not None:
        for path in requested:
            safe_relative(path)
    base = Path(cache_dir) / repo.split("/")[-1] / ref
    rows, found = [], set()
    url = f"https://codeload.github.com/{repo}/tar.gz/{ref}"
    request = urllib.request.Request(url, headers={"User-Agent": "GEMS24-research-cache/1"})
    opener = urllib.request.build_opener(NoRedirects)
    with (
        opener.open(request, timeout=180) as response,
        tarfile.open(fileobj=response, mode="r|gz") as archive,
    ):
        for member in archive:
            parts = PurePosixPath(member.name).parts
            if len(parts) < 2:
                continue
            relative = str(PurePosixPath(*parts[1:]))
            wanted = relative in requested if requested is not None else select(relative)
            if not wanted:
                continue
            safe_relative(relative)
            if not member.isfile() or member.size < 0 or member.size > max_file_bytes:
                raise ValueError(f"Invalid or oversized requested archive member: {relative}")
            if relative in found:
                raise ValueError(f"Duplicate archive member: {relative}")
            stream = archive.extractfile(member)
            if stream is None:
                raise ValueError(f"Unreadable archive member: {relative}")
            raw = stream.read(max_file_bytes + 1)
            if len(raw) != member.size:
                raise ValueError(f"Truncated or oversized archive member: {relative}")
            blob = git_blob_sha(raw)
            if requested is not None and requested[relative] not in (None, blob):
                raise ValueError(f"Git blob mismatch: {repo}@{ref}/{relative}")
            destination = base / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            temporary = destination.with_suffix(destination.suffix + ".partial")
            temporary.write_bytes(raw)
            temporary.replace(destination)
            rows.append(
                {"path": relative, "blob_sha": blob, "bytes": len(raw), "cache_path": destination}
            )
            found.add(relative)
            if requested is not None and found == set(requested):
                break
    if requested is not None and found != set(requested):
        raise ValueError(f"Requested archive files missing: {sorted(set(requested) - found)}")
    return rows
