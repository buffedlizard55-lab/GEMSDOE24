"""Upload data_external/ to branch `public-layers` via the GitHub git-data API
(blob -> tree -> commit -> ref). No git push on the runner: immune to push-loop
guards and detached-HEAD ref ambiguity. Single-file limit 100 MB is ample.
Runs only inside GitHub Actions (needs GITHUB_TOKEN + api.github.com).
Resilience: pushes SMALL files first (always lands, includes push.log), then
attempts large files; every call is logged to data_external/push.log."""
from __future__ import annotations

import base64
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

API = os.environ.get("GITHUB_API_URL", "https://api.github.com")
REPO = os.environ["GITHUB_REPOSITORY"]
TOKEN = os.environ["GITHUB_TOKEN"]
BRANCH = os.environ.get("PUSH_BRANCH", "public-layers")
DIR = Path(os.environ.get("PUSH_DIR", "data_external"))
LOGP = DIR / "push.log"
_LINES: list[str] = []


def log(m: str) -> None:
    print(m, flush=True)
    _LINES.append(m)
    try:
        LOGP.write_text("\n".join(_LINES) + "\n")
    except OSError:
        pass


def req(method: str, path: str, payload=None, timeout=300):
    r = urllib.request.Request(API + path, method=method,
                               data=None if payload is None else json.dumps(payload).encode(),
                               headers={"Authorization": f"Bearer {TOKEN}",
                                        "Accept": "application/vnd.github+json",
                                        "Content-Type": "application/json",
                                        "X-GitHub-Api-Version": "2022-11-28"})
    with urllib.request.urlopen(r, timeout=timeout) as resp:
        body = resp.read()
    return json.loads(body) if body else {}


def blob_sha(p: Path) -> str:
    b64 = base64.b64encode(p.read_bytes()).decode()
    return req("POST", f"/repos/{REPO}/git/blobs", {"content": b64, "encoding": "base64"})["sha"]


def push_files(files: list[Path], msg: str) -> str | None:
    try:
        base = req("GET", f"/repos/{REPO}/git/ref/heads/{BRANCH}")["object"]["sha"]
        tree = {"base_tree": base}
    except urllib.error.HTTPError as e:
        if e.code != 404:
            raise
        base, tree = None, {}
    entries = []
    for f in files:
        rel = str(f.relative_to(DIR.parent))
        sha = blob_sha(f)
        entries.append({"path": rel, "mode": "100644", "type": "blob", "sha": sha})
        log(f"blob ok {rel} ({f.stat().st_size/1e6:.1f} MB)")
    tree["tree"] = entries
    new_tree = req("POST", f"/repos/{REPO}/git/trees", tree)["sha"]
    parents = [base] if base else []
    commit = req("POST", f"/repos/{REPO}/git/commits",
                 {"message": msg, "tree": new_tree, "parents": parents})["sha"]
    if parents:
        req("PATCH", f"/repos/{REPO}/git/refs/heads/{BRANCH}", {"sha": commit, "force": True})
    else:
        req("POST", f"/repos/{REPO}/git/refs", {"ref": f"refs/heads/{BRANCH}", "sha": commit})
    log(f"PUSHED {BRANCH} @ {commit[:8]} with {len(entries)} files (base={bool(parents)})")
    return commit


def main() -> None:
    import datetime
    stamp = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    skip = lambda q: any(part in ("cty",) or part.startswith("tmp_") or part.endswith("_tmp") for part in q.parts)
    files = sorted(x for x in DIR.rglob("*") if x.is_file() and x != LOGP and not skip(x))
    small = [f for f in files if f.stat().st_size < 4_000_000]
    big = [f for f in files if f.stat().st_size >= 4_000_000]
    log(f"upload start {stamp}: {len(small)} small, {len(big)} large")
    try:
        push_files(small + ([LOGP] if LOGP.exists() else []), f"ci-fetch small artifacts {stamp}")
    except Exception as e:  # noqa: BLE001
        log(f"SMALL PUSH FAIL: {e!r}")
        try:
            if LOGP.exists():
                push_files([LOGP, DIR / "fetch_manifest.json"], f"ci-fetch failure log {stamp}")
        except Exception as e2:  # noqa: BLE001
            log(f"LOG PUSH FAIL: {e2!r}")
    for f in big:
        try:
            push_files([f, LOGP], f"ci-fetch artifact {f.name} {stamp}")
        except Exception as e:  # noqa: BLE001
            log(f"LARGE PUSH FAIL {f.name}: {e!r}")
            try:
                if LOGP.exists():
                    push_files([LOGP], f"ci-fetch push log {stamp}")
            except Exception as e2:  # noqa: BLE001
                log(f"LOG PUSH FAIL2: {e2!r}")


if __name__ == "__main__":
    try:
        main()
    finally:
        log("upload step done")
        sys.exit(0)

