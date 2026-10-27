'use strict';
// Optional local browser audit. No model execution and no external navigation.
// npm --prefix data/research/tnr1/browser-tools install playwright-core@1.64.1 @sparticuz/chromium@153.0.0 axe-core@4.14.0
// node scripts/audit_tnr1_site.cjs http://127.0.0.1:8080/
const path = require('node:path');
const fs = require('node:fs/promises');
const crypto = require('node:crypto');
const assert = require('node:assert/strict');
const root = path.resolve(__dirname, '..');
const modules = path.join(root, 'data/research/tnr1/browser-tools/node_modules');
const {chromium: playwright} = require(path.join(modules, 'playwright-core'));
const {default: chromium, inflate, setupLambdaEnvironment} = require(path.join(modules, '@sparticuz/chromium/build/index.js'));
const axeSource = path.join(modules, 'axe-core/axe.min.js');
const base = new URL(process.argv[2]);

async function main() {
  const card = JSON.parse(await fs.readFile(path.join(root, 'evidence/s3dep1_run_card_20261026.json'), 'utf8'));
  const currentBest = JSON.parse(await fs.readFile(path.join(root, 'docs/data/current_best_review.json'), 'utf8'));
  assert.equal(currentBest.submission_name, card.submission_name);
  assert.equal(currentBest.raster_sha256, card.raster_sha256);
  const noteCard = card;
  const libs = await inflate(path.join(modules, '@sparticuz/chromium/bin/al2023.tar.br'));
  setupLambdaEnvironment(path.join(libs, 'lib'));
  const browser = await playwright.launch({args: chromium.args.filter(value => value !== "--single-process"), executablePath: await chromium.executablePath(), headless: true});
  const receipt = {checked_utc: new Date().toISOString(), base_origin: base.origin, browser: browser.version(), experiments_run: 0, external_requests_blocked: [], errors: [], pages: []};
  try {
    for (const [device, viewport] of [['desktop', {width: 1440, height: 1000}], ['mobile', {width: 390, height: 844}]]) {
      const context = await browser.newContext({viewport, permissions: ['clipboard-read', 'clipboard-write'], acceptDownloads: true});
      await context.route('**/*', async route => {
        const url = new URL(route.request().url());
        if (url.origin !== base.origin) {
          receipt.external_requests_blocked.push(url.origin);
          await route.abort();
        } else await route.continue();
      });
      const page = await context.newPage();
      page.on('pageerror', error => receipt.errors.push(error.message));
      for (const relative of ['', 'docs/index.html', 'executive-summary.html', 'docs/executive-summary.html']) {
        const response = await page.goto(new URL(relative, base).href, {waitUntil: 'networkidle'});
        assert.equal(response.status(), 200);
        const link = page.getByRole('link', {name: /Download current point-best research TIFF/}).first();
        const box = await link.boundingBox();
        assert(box && box.x >= 0 && box.x + box.width <= viewport.width + 1);
        assert(box.y >= 0 && box.y + box.height <= viewport.height, `First-screen download off-screen: ${device} ${relative} ${JSON.stringify(box)}`);
        assert(await page.getByText('NOT OK TO SUBMIT.', {exact: false}).first().isVisible());
        assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, `Horizontal overflow: ${device} ${relative}`);
        const historical = page.locator('details[id^="historical-"]').first();
        assert.equal(await historical.getAttribute('open'), null);
        assert.equal(await page.locator('#portfolio-historical tbody tr').count(), 9);
        assert.equal(await page.locator('#portfolio-current tbody tr').count(), 9);
        assert.equal(await page.locator('#portfolio-historical .portfolio-mobile > article').count(), 9);
        assert.equal(await page.locator('#portfolio-historical .portfolio-mobile').isVisible(), device === 'mobile');
        assert.equal(await page.locator('#current-focus-files tbody tr').count(), 9);
        assert.equal(await page.locator('#current-focus-files .portfolio-mobile > article').count(), 9);
        assert.equal(await page.locator('#current-focus-files .portfolio-mobile').isVisible(), device === 'mobile');
        assert.equal(await page.locator('#current-focus-files tbody tr strong').filter({hasText: 'NO'}).count(), 9);
        assert(await page.getByText('all nine fail the literal 70% overlap rule').first().isVisible());
        if (!relative) await page.screenshot({path: path.join(root, `logs/tnr1-${device}.png`), fullPage: true});
        const [download] = await Promise.all([page.waitForEvent('download'), link.click()]);
        assert.equal(download.suggestedFilename(), card.submission_name);
        const bytes = await fs.readFile(await download.path());
        const digest = crypto.createHash('sha256').update(bytes).digest('hex');
        assert.equal(digest, card.raster_sha256);
        await page.locator('#current-download-details > summary').click();
        await page.locator('[data-copy="#note-current-best"]').click();
        await page.waitForFunction(() => document.querySelector('#current-best-feedback')?.textContent === 'Copied to clipboard.');
        assert.equal(await page.evaluate(() => navigator.clipboard.readText()), noteCard.note);
        await page.addScriptTag({path: axeSource});
        const accessibility = await page.evaluate(async () => {
          const result = await axe.run(document.querySelector('main'), {runOnly: {type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'best-practice']}});
          return result.violations.map(v => ({id: v.id, impact: v.impact, description: v.description, nodes: v.nodes.map(n => n.target)}));
        });
        receipt.pages.push({device, page: relative || 'index.html', download_sha256: digest, first_screen_download: true, clipboard_matches: true, no_horizontal_overflow: true, accessibility_violations: accessibility});
      }
      for (const relative of ['docs/research.html', 'docs/sources.html']) {
        await page.goto(new URL(relative, base).href, {waitUntil: 'networkidle'});
        await page.addScriptTag({path: axeSource});
        const accessibility = await page.evaluate(async () => {
          const result = await axe.run(document.querySelector('main'), {runOnly: {type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'best-practice']}});
          return result.violations.map(v => ({id: v.id, impact: v.impact, nodes: v.nodes.map(n => n.target)}));
        });
        receipt.pages.push({device, page: relative, no_horizontal_overflow: await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), accessibility_violations: accessibility});
      }

      await page.getByText('Show the complete source / owner-claim table', {exact: true}).click();
      assert.equal(await page.locator('#all-owner-sites tbody tr').count(), 92);
      const expandedAccess = await page.evaluate(async () => {
        const result = await axe.run(document.querySelector('#all-owner-sites'));
        return result.violations.map(v => ({id: v.id, impact: v.impact, nodes: v.nodes.map(n => n.target)}));
      });
      receipt.pages.at(-1).owner_table_rows = 92;
      receipt.pages.at(-1).accessibility_violations.push(...expandedAccess);
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
      await context.close();
    }
    assert(receipt.pages.every(row => row.no_horizontal_overflow));
    assert.deepEqual(receipt.errors, []);
    assert.deepEqual(receipt.external_requests_blocked, []);
    await fs.writeFile(path.join(root, 'logs/tnr1-browser-audit.json'), JSON.stringify(receipt, null, 2) + '\n');
    console.log(JSON.stringify(receipt, null, 2));
    assert(receipt.pages.every(row => row.accessibility_violations.length === 0), 'Accessibility violations in receipt');
  } finally { await browser.close(); }
}
main().catch(error => { console.error(error); process.exitCode = 1; });
