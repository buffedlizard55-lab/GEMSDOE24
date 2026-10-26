import io
import tarfile

import pytest

from gems import github_archive


def archive_bytes(files):
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w:gz") as archive:
        for path, data, kind in files:
            member = tarfile.TarInfo("project-ref/" + path)
            if kind == "symlink":
                member.type = tarfile.SYMTYPE
                member.linkname = "/etc/passwd"
            else:
                member.size = len(data)
            archive.addfile(member, io.BytesIO(data))
    return stream.getvalue()


def mock_archive(monkeypatch, raw):
    class Opener:
        def open(self, request, timeout):
            assert request.full_url.startswith("https://codeload.github.com/")
            assert timeout > 0
            return io.BytesIO(raw)

    monkeypatch.setattr(github_archive.urllib.request, "build_opener", lambda *args: Opener())


def test_archive_extracts_only_selected_regular_files_and_verifies_git_id(tmp_path, monkeypatch):
    data = b"a pinned small file\n"
    mock_archive(
        monkeypatch,
        archive_bytes([("docs/a.tif", data, "regular"), ("ignored.bin", b"bulk", "regular")]),
    )
    rows = github_archive.cache_archive(
        "owner/repo",
        "a" * 40,
        tmp_path,
        requested={"docs/a.tif": github_archive.git_blob_sha(data)},
    )
    assert len(rows) == 1 and rows[0]["cache_path"].read_bytes() == data
    assert not list(tmp_path.rglob("ignored.bin"))
    assert rows[0]["cache_path"].is_relative_to(tmp_path)


@pytest.mark.parametrize("path", ["../a.tif", "/tmp/a.tif", "a\\b.tif", ""])
def test_unsafe_requested_paths_fail_before_network(tmp_path, path):
    with pytest.raises(ValueError, match="Unsafe"):
        github_archive.cache_archive("owner/repo", "a" * 40, tmp_path, requested={path: None})


@pytest.mark.parametrize("kind", ["symlink", "oversized", "mismatch", "missing"])
def test_archive_cannot_silently_substitute_or_skip_a_registered_file(tmp_path, monkeypatch, kind):
    files = (
        []
        if kind == "missing"
        else [("a.tif", b"abc", "symlink" if kind == "symlink" else "regular")]
    )
    mock_archive(monkeypatch, archive_bytes(files))
    with pytest.raises(ValueError):
        github_archive.cache_archive(
            "owner/repo",
            "a" * 40,
            tmp_path,
            requested={"a.tif": "b" * 40 if kind == "mismatch" else None},
            max_file_bytes=1 if kind == "oversized" else 100,
        )


def test_archive_requires_immutable_ref_and_refuses_redirects(tmp_path):
    with pytest.raises(ValueError, match="immutable"):
        github_archive.cache_archive("owner/repo", "main", tmp_path, requested={"a": None})
    with pytest.raises(ValueError, match="redirect"):
        github_archive.NoRedirects().redirect_request(
            None, None, 302, "redirect", {}, "https://other.example/"
        )
