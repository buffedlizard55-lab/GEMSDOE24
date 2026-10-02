'use strict';

for (const button of document.querySelectorAll('[data-copy]')) {
  button.addEventListener('click', async () => {
    const target = document.querySelector(button.dataset.copy);
    const feedback = document.querySelector(button.dataset.feedback || '#copy-feedback');
    if (!target) return;
    try {
      if (!navigator.clipboard) throw new Error('Clipboard unavailable');
      await navigator.clipboard.writeText(target.textContent.trim());
      if (feedback) feedback.textContent = 'Copied. Reference only — no new slot recommended.';
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
    for (const node of document.querySelectorAll('[data-source-state]')) {
      node.textContent = data.status === 'failed' || data.status === 'stale' ? 'Fetch failed — showing last verified snapshot' : 'Latest verified snapshot, not a live scoring API';
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
