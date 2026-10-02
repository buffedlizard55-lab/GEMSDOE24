"""Upload data_external/ to branch `public-layers` via the GitHub git-data API
(blob -> tree -> commit -> ref). No git push on the runner: immune to push-loop
guards and detached-HEAD ref ambiguity. Single-file limit 100 MB is ample.
Runs only inside GitHub Actions (needs GITHUB_TOKEN + api.github.com)."""
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


def req(method: str, path: str, payload=None, accepts="application/vnd.github+json"):
    r = urllib.request.Request(API + path, method=method,
                               data=None if payload is None else json.dumps(payload).encode(),
                               headers={"Authorization": f"Bearer {TOKEN}",
                                        "Accept": accepts,
                                        "Content-Type": "application/json",
                                        "X-GitHub-Api-Version": "2022-11-28"})
    with urllib.request.urlopen(r, timeout=300) as resp:
        body = resp.read()
    return json.loads(body) if body else {}


def blob_sha(p: Path) -> str:
    b64 = base64.b64encode(p.read_bytes()).decode()
    return req("POST", f"/repos/{REPO}/git/blobs", {"content": b64, "encoding": "base64"})["sha"]


def main() -> None:
    files = sorted(x for x in DIR.rglob("*") if x.is_file())
    if not files:
        print("nothing to upload")
        return
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
        try:
            sha = blob_sha(f)
        except Exception as e:  # noqa: BLE001
            print(f"BLOB FAIL {rel}: {e}", file=sys.stderr)
            raise
        entries.append({"path": rel, "mode": "100644", "type": "blob", "sha": sha})
        print(f"blob ok {rel} ({f.stat().st_size/1e6:.1f} MB)", flush=True)
    tree["tree"] = entries
    new_tree = req("POST", f"/repos/{REPO}/git/trees", tree)["sha"]
    parents = [base] if base else []
    import datetime
    msg = f"ci-fetch artifacts {datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')}"
    commit = req("POST", f"/repos/{REPO}/git/commits", {"message": msg, "tree": new_tree, "parents": parents})["sha"]
    if parents:
        req("PATCH", f"/repos/{REPO}/git/refs/heads/{BRANCH}", {"sha": commit, "force": True})
    else:
        req("POST", f"/repos/{REPO}/git/refs", {"ref": f"refs/heads/{BRANCH}", "sha": commit})
    print(f"PUSHED {BRANCH} @ {commit[:8]} with {len(entries)} files")


if __name__ == "__main__":
    main()
