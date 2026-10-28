'use strict';

for (const button of document.querySelectorAll('[data-copy]')) {
  button.addEventListener('click', async () => {
    const target = document.querySelector(button.dataset.copy);
    const feedback = document.querySelector(button.dataset.feedback || '#copy-feedback');
    if (!target) return;
    try {
      if (!navigator.clipboard) throw new Error('Clipboard unavailable');
      await navigator.clipboard.writeText(target.textContent.trim());
      if (feedback) feedback.textContent = 'Copied to clipboard.';
    } catch (_) {
      if (feedback) feedback.textContent = 'Please select and copy the plain-text comment below.';
    }
  });
}

function sourceDate(value) {
  if (!value) return 'time unavailable';
  if (value.length === 10) return `${value} (date-only source review)`;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? 'time unavailable' : date.toISOString().replace('T', ' ').slice(0, 19) + ' UTC';
}

// A successful fetch of a static JSON file does not mean its underlying checks are fresh.
// The Pages job is scheduled every six hours; two missed intervals triggers a warning.
function sourceFreshness(value, now = Date.now()) {
  if (typeof value !== 'string') return 'unknown';
  const match = /^(\d{4})-(\d{2})-(\d{2})T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/.exec(value);
  if (!match) return 'unknown';
  const [, year, month, day] = match.map(Number);
  if (year < 1900) return 'unknown';
  const calendar = new Date(Date.UTC(year, month - 1, day));
  if (calendar.getUTCFullYear() !== year || calendar.getUTCMonth() !== month - 1 || calendar.getUTCDate() !== day) return 'unknown';
  const timestamp = Date.parse(value);
  if (!Number.isFinite(timestamp) || timestamp > now + 300000) return 'unknown';
  return now - timestamp > 12 * 60 * 60 * 1000 ? 'old' : 'recent';
}

async function refreshSourceFeed() {
  const path = document.querySelector('meta[name="source-feed"]')?.content;
  if (!path) return;
  try {
    const response = await fetch(path, {cache: 'no-store'});
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    const board = data.leaderboard;
    if (board && typeof board.best_score === 'number' && Number.isFinite(board.best_score) && board.best_score >= 0 && board.best_score <= 1) {
      for (const node of document.querySelectorAll('[data-leader-score]')) node.textContent = board.best_score.toFixed(4);
      for (const node of document.querySelectorAll('[data-leader-name]')) node.textContent = board.participant || 'Participant not recorded';
    }
    for (const node of document.querySelectorAll('[data-source-time]')) {
      node.textContent = sourceDate(data.last_success_utc || data.checked_utc);
    }
    // For a leaderboard snapshot, the separate automatic source check cannot refresh
    // the human-read leaderboard timestamp. A date-only timestamp is unknown.
    const freshness = sourceFreshness(data.scope?.startsWith('GitHub') ? data.checked_utc : data.last_success_utc);
    const freshnessWarning = freshness === 'old'
      ? ' Source check is over 12 hours old; current state unknown.'
      : freshness === 'unknown' ? ' Source check time is unavailable or invalid; current state unknown.' : '';
    for (const node of document.querySelectorAll('[data-source-state]')) {
      const state = data.scope?.startsWith('GitHub')
        ? (data.status === 'checked' ? 'GitHub source freshness only — no score verification or automatic promotion' : 'Some GitHub checks failed or are unknown — pinned experiment unchanged')
        : (data.status === 'failed' || data.status === 'stale' ? 'Fetch failed — showing last verified snapshot' : 'Recorded snapshot, not a live scoring API');
      node.textContent = state + freshnessWarning;
    }
    const feed = document.querySelector('#source-feed-list');
    if (feed && Array.isArray(data.updates)) {
      feed.replaceChildren();
      for (const item of data.updates.slice(0, 5)) {
        const row = document.createElement('li');
        const title = document.createElement('strong');
        title.textContent = item.title || 'Source update';
        const detail = document.createElement('small');
        detail.textContent = `${item.kind || 'Source'} · ${sourceDate(item.checked_utc || data.checked_utc)}`;
        const link = document.createElement('a');
        if (typeof item.url === 'string' && item.url.startsWith('https://')) {
          link.href = item.url;
          link.rel = 'noopener noreferrer';
          link.target = '_blank';
        }
        link.append(title);
        row.append(link, detail);
        feed.append(row);
      }
    }
  } catch (_) {
    for (const node of document.querySelectorAll('[data-source-state]')) {
      node.textContent = 'Feed unavailable — static snapshot retained; verify the official source';
    }
  }
}
refreshSourceFeed();
setInterval(refreshSourceFeed, 300000);
