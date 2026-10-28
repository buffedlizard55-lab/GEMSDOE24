"""Static feed age and Git provenance preflight must fail closed."""

from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "check_git_history", ROOT / "scripts/check_git_history.py"
)
history = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(history)


def test_history_detects_real_shallow_checkout(tmp_path):
    origin = tmp_path / "origin"
    subprocess.run(["git", "init", "-q", str(origin)], check=True)
    subprocess.run(
        ["git", "-C", str(origin), "config", "user.email", "test@example.org"], check=True
    )
    subprocess.run(["git", "-C", str(origin), "config", "user.name", "test"], check=True)
    for text in ("one", "two"):
        (origin / "file.txt").write_text(text)
        subprocess.run(["git", "-C", str(origin), "add", "file.txt"], check=True)
        subprocess.run(["git", "-C", str(origin), "commit", "-qm", text], check=True)
    shallow = tmp_path / "shallow"
    subprocess.run(
        ["git", "clone", "-q", "--depth", "1", origin.as_uri(), str(shallow)], check=True
    )
    assert history.check_history(origin)[0] is True
    ok, message = history.check_history(shallow)
    assert ok is False and "Shallow checkout" in message
    subprocess.run(["git", "-C", str(shallow), "fetch", "-q", "--unshallow"], check=True)
    assert history.check_history(shallow)[0] is True


def test_history_refuses_non_repository(tmp_path):
    ok, message = history.check_history(tmp_path)
    assert ok is False and "Cannot check git history" in message


def test_browser_freshness_uses_source_timestamp_not_fetch_time():
    # Run the real browser script in a minimal mocked DOM without external requests.
    script = r"""
const vm = require('node:vm');
const fs = require('node:fs');
const assert = require('node:assert/strict');
const source = fs.readFileSync('docs/assets/app.js', 'utf8');
let data = {};
const state = {textContent: ''};
const ctx = {
  document: {
    querySelectorAll: q => q === '[data-source-state]' ? [state] : [],
    querySelector: q => q === 'meta[name="source-feed"]' ? {content: 'feed.json'} : null
  },
  fetch: async () => ({ok: true, json: async () => data}),
  setInterval: () => {}, console
};
vm.createContext(ctx);
vm.runInContext(source, ctx);
const now = Date.parse('2026-10-28T12:00:00Z');
assert.equal(ctx.sourceFreshness('2026-10-28T00:00:00Z', now), 'recent');
assert.equal(ctx.sourceFreshness('2026-10-27T23:59:59Z', now), 'old');
assert.equal(ctx.sourceFreshness('2026-10-28', now), 'unknown');
assert.equal(ctx.sourceFreshness('2026-10-28T12:06:00Z', now), 'unknown');
assert.equal(ctx.sourceFreshness('not a date', now), 'unknown');
assert.equal(ctx.sourceFreshness('2026-02-30T00:00:00Z', now), 'unknown');
assert.equal(ctx.sourceFreshness('2026-10-28T11:00:00+00:00', now), 'recent');
(async () => {
  data = {scope:'GitHub source freshness only', status:'checked', checked_utc:'2000-01-01T00:00:00Z'};
  await ctx.refreshSourceFeed();
  assert.match(state.textContent, /over 12 hours old/);
  data = {status:'human_read_snapshot', checked_utc:new Date().toISOString(), last_success_utc:'2000-01-01T00:00:00Z'};
  await ctx.refreshSourceFeed();
  assert.match(state.textContent, /over 12 hours old/);
  data = {scope:'GitHub source freshness only', status:'stale', checked_utc:new Date().toISOString()};
  await ctx.refreshSourceFeed();
  assert.match(state.textContent, /failed or are unknown/);
})().catch(e => { console.error(e); process.exitCode = 1; });
"""
    subprocess.run(["node", "-e", script], cwd=ROOT, check=True, capture_output=True, text=True)
