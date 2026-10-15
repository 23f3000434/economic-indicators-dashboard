// Live application smoke check: no fixture inputs. Credentials remain in an ignored owner-only file.
import { readFile, writeFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import assert from 'node:assert/strict';

const root = fileURLToPath(new URL('..', import.meta.url));
const require = createRequire(new URL('../frontend/package.json', import.meta.url));
const { chromium } = require('@playwright/test');
const frontend = process.env.LOCAL_FRONTEND_URL || 'http://localhost:5173';
const api = process.env.LOCAL_API_URL || 'http://localhost:8010';
const credentialsPath = process.env.LOCAL_SMOKE_CREDENTIALS || root + '/.verification/local-access.json';
const credentials = JSON.parse(await readFile(credentialsPath, 'utf8'));
assert.equal((await fetch(api + '/healthz')).status, 200);
assert.equal((await fetch(api + '/api/v1/panels/gdp')).status, 401);
const browser = await chromium.launch({ executablePath: process.env.CHROME_PATH || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' });
try {
  const context = await browser.newContext({ viewport: { width: 1214, height: 2159 } });
  const page = await context.newPage();
  const errors = [], origins = new Set();
  let access = '';
  page.on('pageerror', error => errors.push(error.message));
  page.on('request', request => {
    if (request.resourceType() === 'fetch') origins.add(new URL(request.url()).origin);
    const value = request.headers().authorization;
    if (value?.startsWith('Bearer ')) access = value.slice(7);
  });
  await page.goto(frontend);
  await page.getByLabel('Username').fill(credentials.username);
  await page.getByLabel('Password', { exact: true }).fill(credentials.password);
  const response = page.waitForResponse(response => response.url() === api + '/api/v1/panels/gdp' && response.status() === 200);
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  const panel = await (await response).json();
  assert.equal(panel.state, 'ready');
  for (const series of panel.series) {
    const summary = panel.summaries.find(s => s.series_id === series.id);
    const point = series.points.find(p => p.period_key === summary.current_period_key);
    const formatted = Number(point.value).toLocaleString('en-IN', { maximumFractionDigits: 2, minimumFractionDigits: 2 }) + '%';
    await page.getByTestId('card-' + series.id).filter({ hasText: formatted }).waitFor();
    assert.equal(await page.getByTestId(`table-${series.id}-${point.period_key}`).innerText(), formatted);
  }
  assert.deepEqual(await page.evaluate(() => [Object.keys(localStorage), Object.keys(sessionStorage)]), [[], []]);
  await page.reload();
  await page.getByTestId('card-gdp_india').filter({ hasText: '%' }).waitFor();
  const cookie = (await context.cookies()).find(c => c.name === 'dev_refresh');
  assert(cookie?.httpOnly && !cookie.secure && cookie.sameSite === 'Strict' && cookie.expires > Date.now()/1000);
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
  const geometry = await page.locator('.gdp-panel').boundingBox();
  await page.screenshot({ path: root + '/.verification/live-desktop.png', fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
  await page.screenshot({ path: root + '/.verification/live-mobile.png', fullPage: true });
  const timings = [];
  for (let i = 0; i < 10; i++) {
    const start = performance.now();
    const read = await fetch(api + '/api/v1/panels/gdp', { headers: { Authorization: 'Bearer ' + access } });
    assert.equal(read.status, 200);
    timings.push(performance.now() - start);
  }
  await page.getByRole('button', { name: /Sign out/ }).click();
  await page.getByRole('button', { name: 'Sign in', exact: true }).waitFor();
  assert.equal((await fetch(api + '/api/v1/me', { headers: { Authorization: 'Bearer ' + access } })).status, 401);
  assert.deepEqual([...origins], [api]);
  assert.deepEqual(errors, []);
  const report = { checked_at: new Date().toISOString(), frontend, api, source: 'live World Bank observations stored by application collector',
    checks: ['unauthenticated read denied', 'login', 'protected stored read', 'canonical card/table agreement', 'reload renewal', 'memory-only JWT', 'persistent HttpOnly local cookie', 'desktop/mobile no horizontal overflow', 'API-only browser data fetches', 'logout revokes prior access JWT', 'no browser runtime errors'],
    gdp_panel_geometry: geometry, read_latency_ms: { min: Math.min(...timings), max: Math.max(...timings) },
    cookie: { name: cookie.name, httpOnly: cookie.httpOnly, secure: cookie.secure, sameSite: cookie.sameSite }, panel };
  await writeFile(root + '/docs/evidence/2026-10-15/gdp-slice-live.json', JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify({ result: 'passed', checks: report.checks.length, read_latency_ms: report.read_latency_ms, gdp_panel_geometry: geometry }));
} finally { await browser.close(); }
