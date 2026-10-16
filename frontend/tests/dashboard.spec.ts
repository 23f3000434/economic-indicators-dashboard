import { expect, test, type Page } from '@playwright/test';
import type { Dashboard, IndicatorPanel, Measurement, PeriodKind } from '../src/contracts';

const API = 'http://localhost:8001';
const PASSWORD = 'Test-only password 93!';
async function login(page: Page, username = 'analyst') {
  await page.goto('/');
  await page.getByLabel('Username').fill(username);
  await page.getByLabel('Password', { exact: true }).fill(PASSWORD);
  const response = page.waitForResponse((r) => r.url().endsWith('/api/v1/dashboard') && r.status() === 200);
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  const data = (await (await response).json()) as Dashboard;
  await expect(page.getByTestId('card-cpi_yoy_2024')).toHaveText('5.54%');
  return data;
}
const panelAt = (data: Dashboard, id: string) => data.panels.find((p) => p.id === id) as IndicatorPanel;
const pointAt = (panel: IndicatorPanel, id: string, key: string) =>
  panel.series.find((s) => s.id === id)!.points.find((p) => p.period.key === key)!;
// Independent expected display from the accepted fixture values/API references.
function expected(point: Measurement, signed = false) {
  if (point.value === null) return '—';
  const raw = Number(point.value);
  const numeric = (point.definition.unit === 'inr_crore' ? raw / 100000 : raw).toFixed(2);
  return point.definition.unit === 'inr_crore'
    ? `₹${numeric} L cr`
    : point.definition.unit === 'usd_billion'
      ? `$${signed && raw > 0 ? '+' : ''}${numeric} B`
      : numeric + '%';
}
async function openDetails(page: Page, id: string) {
  const dialog = page.getByRole('dialog');
  if (await dialog.count()) await dialog.getByRole('button', { name: /^Close / }).click();
  await page
    .locator(`.${id}-panel`)
    .getByRole('button', { name: /Details & data/ })
    .click();
  return page.getByRole('dialog');
}
async function closeDetails(page: Page) {
  await page
    .getByRole('dialog')
    .getByRole('button', { name: /^Close / })
    .click();
}
async function checkSummary(page: Page, panel: IndicatorPanel, id: string, kind: PeriodKind) {
  const summary = panel.summaries.find((s) => s.current.series_id === id && s.period_kind === kind)!;
  const point = pointAt(panel, id, summary.current.period_key);
  await openDetails(page, panel.id);
  await expect(page.getByTestId(`card-${id}`)).toHaveText(expected(point, id === 'trade_balance'));
  await expect(page.getByTestId(`table-${id}-${point.period.key}`)).toHaveText(
    expected(point, id === 'trade_balance'),
  );
  await closeDetails(page);
  return point;
}

test.beforeEach(async ({ request, page }) => {
  const { now } = await (await request.post(API + '/__test/reset')).json();
  await page.clock.install({ time: now });
});

test('complete interface agrees with canonical API and uses supplied artwork at desktop size', async ({
  page,
}) => {
  const data = await login(page);
  for (const [panelId, id] of [
    ['trade', 'trade_exports'],
    ['trade', 'trade_imports'],
    ['trade', 'trade_balance'],
    ['gst', 'gst_fy_total'],
    ['gst', 'gst_fy_average'],
    ['expenditure', 'expenditure_total'],
    ['expenditure', 'expenditure_capital'],
  ]) {
    await checkSummary(page, panelAt(data, panelId), id, 'fiscal_year');
  }
  await checkSummary(page, panelAt(data, 'inflation'), 'cpi_yoy_2024', 'month');
  await expect(page.getByTestId('card-inflation_target')).toHaveText('4.00%');
  await checkSummary(page, panelAt(data, 'debt'), 'debt_india', 'fiscal_year');
  await checkSummary(page, panelAt(data, 'debt'), 'debt_us', 'calendar_year');
  await expect(page.locator('.market-strip')).toContainText('CLOSED');
  await expect(page.locator('.market-strip')).toContainText('74,315.61');
  await expect(page.locator('.market-strip')).not.toContainText(/live/i);
  await expect(page.locator('.gst-panel')).toContainText('excl. compensation cess');
  const trade = page.locator('.trade-panel');
  await trade.locator('.recharts-bar-rectangle').first().hover();
  const first = panelAt(data, 'trade')
    .series.find((s) => s.id === 'trade_exports')!
    .points.find((p) => p.period.kind === 'fiscal_year')!;
  await expect(page.locator('.chart-tooltip[data-chart="trade"]')).toContainText(expected(first));
  await openDetails(page, 'trade');
  await expect(page.getByTestId(`table-trade_exports-${first.period.key}`)).toHaveText(expected(first));
  await closeDetails(page);
  await page.mouse.move(0, 0);
  await page.waitForLoadState('networkidle');
  const geometry = await page.locator('.panel').evaluateAll((panels) =>
    panels.map((p) => {
      const r = p.getBoundingClientRect();
      return { x: r.x, y: r.y, width: r.width, height: r.height };
    }),
  );
  expect(geometry).toHaveLength(6);
  expect(Math.abs(geometry[0].x - 29)).toBeLessThanOrEqual(1);
  expect(geometry[0].width).toBeCloseTo((582 * 1214) / 1248, 2);
  expect(geometry[0].height).toBeCloseTo((544 * 1214) / 1248, 2);
  expect(geometry[2].y - geometry[0].y).toBeCloseTo((568 * 1214) / 1248, 2);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  expect(
    await page
      .locator('.kpi-value')
      .evaluateAll((nodes) => nodes.every((n) => n.scrollWidth <= n.clientWidth)),
  ).toBe(true);
  for (const image of await page.locator('.panel-skin').all()) {
    await image.scrollIntoViewIfNeeded();
    await image.evaluate((n) => (n as HTMLImageElement).decode());
  }
  expect(
    await page
      .locator('.panel-skin')
      .evaluateAll((ns) => ns.every((n) => (n as HTMLImageElement).naturalWidth > 0)),
  ).toBe(true);
  const fonts = await page.locator('#gdp-title').evaluate((n) => ({
    family: getComputedStyle(n).fontFamily,
    size: getComputedStyle(n).fontSize,
    weight: getComputedStyle(n).fontWeight,
  }));
  expect(fonts).toEqual({ family: 'Roboto, sans-serif', size: '20px', weight: '500' });
  await page.screenshot({ path: '../.verification/frontend-desktop.png', fullPage: true });
});

test('period controls, history and legend toggles select canonical values in fixed panels', async ({
  page,
}) => {
  const data = await login(page);
  const shape = await page.locator('.trade-panel').boundingBox();
  await openDetails(page, 'trade');
  await page.getByLabel('trade reporting period').selectOption('fiscal_year_to_date');
  await expect(page.locator('.observations tbody tr')).toHaveCount(4);
  await closeDetails(page);
  await checkSummary(page, panelAt(data, 'trade'), 'trade_exports', 'fiscal_year_to_date');
  await checkSummary(page, panelAt(data, 'trade'), 'trade_balance', 'fiscal_year_to_date');
  const imports = page.locator('.trade-panel').getByRole('button', { name: 'Imports', exact: true });
  await imports.click();
  await expect(imports).toHaveAttribute('aria-pressed', 'false');
  await openDetails(page, 'trade');
  await expect(page.getByRole('columnheader', { name: 'Imports', exact: true })).toHaveCount(0);
  await closeDetails(page);
  await imports.click();
  await openDetails(page, 'gst');
  await page.getByLabel('gst reporting period').selectOption('month');
  await expect(page.locator('.observations tbody tr')).toHaveCount(12);
  await page.getByLabel('gst history window').selectOption('24');
  await expect(page.locator('.observations tbody tr')).toHaveCount(24);
  await closeDetails(page);
  await checkSummary(page, panelAt(data, 'gst'), 'gst_gross_ex_cess', 'month');
  await openDetails(page, 'expenditure');
  await page.getByLabel('expenditure reporting period').selectOption('fiscal_year_to_date');
  await closeDetails(page);
  await checkSummary(page, panelAt(data, 'expenditure'), 'expenditure_total', 'fiscal_year_to_date');
  await openDetails(page, 'gdp');
  await page.getByLabel('GDP history window').selectOption('3');
  await expect(page.locator('.observations tbody tr')).toHaveCount(3);
  await closeDetails(page);
  await expect(page.locator('.gdp-panel .recharts-bar-rectangle')).toHaveCount(6);
  expect(await page.locator('.trade-panel').boundingBox()).toEqual(shape);
});
test('CPI bases and gaps remain separate and dated policy never extends', async ({ page }) => {
  await login(page);
  await openDetails(page, 'inflation');
  await expect(page.getByTestId('table-inflation_target-2026-03')).toHaveText('—');
  await expect(page.getByTestId('table-inflation_target-2026-04')).toHaveText('4.00%');
  await page.getByLabel('CPI methodology').selectOption('cpi_yoy_2012');
  await page.getByLabel('inflation history window').selectOption('600');
  await expect(page.getByTestId('card-inflation_target')).toHaveText('—');
  await expect(page.getByTestId('table-cpi_yoy_2012-2020-04')).toHaveText('—');
  await expect(page.getByTestId('table-cpi_yoy_2012-2020-05')).toHaveText('—');
  await closeDetails(page);
  const path = await page.locator('.inflation-panel .recharts-area-curve').getAttribute('d');
  expect((path?.match(/M/g) || []).length).toBeGreaterThanOrEqual(2);
  await openDetails(page, 'inflation');
  await page.getByLabel('CPI methodology').selectOption('cpi_yoy_2024');
  await closeDetails(page);
  await expect(page.getByTestId('card-cpi_yoy_2024')).toHaveText('5.54%');
});

test('independent provider failures retain observations and recover without blanking other panels', async ({
  page,
  request,
}) => {
  await login(page);
  const original = await page.getByTestId('card-gst_fy_total').innerText();
  await request.post(API + '/__test/group/gst/failure');
  await request.post(API + '/__test/group/inflation_policy/failure');
  await page.getByRole('button', { name: 'Refresh stored dashboard data' }).click();
  await expect(page.locator('.gst-panel .status')).toHaveText('stale');
  await expect(page.locator('.inflation-panel .panel-notice')).toContainText(
    'inflation policy · retained data · timeout',
  );
  await expect(page.getByTestId('card-gst_fy_total')).toHaveText(original);
  await expect(page.getByTestId('card-cpi_yoy_2024')).toHaveText('5.54%');
  await expect(page.locator('.trade-panel .status')).toHaveText('Stored data');
  await expect(page.locator('.gdp-panel .status')).toHaveText('Stored data');
  await request.post(API + '/__test/group/gst/success');
  await request.post(API + '/__test/group/inflation_policy/success');
  await page.getByRole('button', { name: 'Refresh stored dashboard data' }).click();
  await expect(page.locator('.gst-panel .status')).toHaveText('Stored data');
  await expect(page.locator('.inflation-panel .status')).toHaveText('Stored data');
});

test('offline polling retains the full interface and reconnects automatically', async ({ page, context }) => {
  await login(page);
  await context.setOffline(true);
  await page.getByRole('button', { name: 'Refresh stored dashboard data' }).click();
  await expect(page.getByRole('alert')).toContainText('Connection lost');
  await expect(page.getByTestId('card-trade_exports')).toHaveText('$441.78 B');
  await expect(page.getByTestId('card-cpi_yoy_2024')).toHaveText('5.54%');
  await context.setOffline(false);
  await expect(page.getByRole('alert')).toHaveCount(0);
  await expect(page.getByTestId('card-gst_fy_total')).toHaveText('₹22.27 L cr');
});

test('single-flight requests are cancelled on logout and late responses cannot cross accounts', async ({
  page,
  context,
}) => {
  const snapshot = await login(page);
  let release!: () => void;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  let requests = 0;
  await page.route('**/api/v1/dashboard', async (route) => {
    requests++;
    await gate;
    await route.fulfill({ json: snapshot }).catch(() => {});
  });
  await page.getByRole('button', { name: 'Refresh stored dashboard data' }).click();
  // Several timer ticks while the same request is held must not start more reads.
  await page.clock.fastForward(180000);
  expect(requests).toBe(1);
  await page.getByRole('button', { name: /Sign out/ }).click();
  await expect(page.getByTestId('card-gst_fy_total')).toHaveCount(0);
  release();
  await page.unroute('**/api/v1/dashboard');
  await page.getByLabel('Username').fill('reviewer');
  await page.getByLabel('Password', { exact: true }).fill(PASSWORD);
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page.locator('.account')).toContainText('reviewer');
  await expect(page.getByTestId('card-cpi_yoy_2024')).toHaveText('5.54%');
  expect((await context.cookies()).find((c) => c.name === 'dev_refresh')?.httpOnly).toBe(true);
});

test('keyboard controls, focus return, chart inspection and accessible data alternatives work', async ({
  page,
}) => {
  await login(page);
  const trigger = page.locator('.gdp-panel').getByRole('button', { name: /Details & data/ });
  await trigger.focus();
  await page.keyboard.press('Enter');
  const select = page.getByLabel('GDP history window');
  await select.focus();
  expect(await select.evaluate((n) => getComputedStyle(n).outlineStyle)).not.toBe('none');
  await select.selectOption('3');
  const table = page.getByRole('region', { name: 'GDP observations table' });
  await table.focus();
  await page.keyboard.press('ArrowDown');
  await expect(table).toBeFocused();
  await page.keyboard.press('Escape');
  await expect(trigger).toBeFocused();
  const world = page.locator('.gdp-panel').getByRole('button', { name: 'World', exact: true });
  await world.focus();
  await page.keyboard.press('Space');
  await expect(world).toHaveAttribute('aria-pressed', 'false');
  const chart = page.locator('.gdp-panel').getByRole('application');
  await chart.focus();
  await page.keyboard.press('ArrowRight');
  await expect(page.locator('.chart-tooltip[data-chart="gdp"]')).toContainText('India');
});

test('component errors are isolated and retry reads repaired data', async ({ page }) => {
  await login(page);
  await page.route(
    '**/api/v1/dashboard',
    async (route) => {
      const response = await route.fetch();
      const data = await response.json();
      data.panels.find((p: IndicatorPanel) => p.id === 'gst').series = null;
      await route.fulfill({ response, json: data });
    },
    { times: 1 },
  );
  await page.getByRole('button', { name: 'Refresh stored dashboard data' }).click();
  await expect(page.getByRole('heading', { name: /GST Tax Collection could not open/ })).toBeVisible();
  await expect(page.getByTestId('card-trade_exports')).toHaveText('$441.78 B');
  await page.getByRole('button', { name: 'Retry panel' }).click();
  await expect(page.getByTestId('card-gst_fy_total')).toHaveText('₹22.27 L cr');
});

test('failed lazy download has a reload recovery path without losing the session', async ({ page }) => {
  await page.route(/(?:\/src\/IndicatorPanel\.tsx|\/assets\/IndicatorPanel-[^/]+\.js)/, (route) =>
    route.abort(),
  );
  await page.goto('/');
  await page.getByLabel('Username').fill('analyst');
  await page.getByLabel('Password', { exact: true }).fill(PASSWORD);
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Reload application' }).first()).toBeVisible();
  await expect(page.getByTestId('card-gdp_india')).toHaveText('7.57%');
  await page.unroute(/(?:\/src\/IndicatorPanel\.tsx|\/assets\/IndicatorPanel-[^/]+\.js)/);
  await page.getByRole('button', { name: 'Reload application' }).first().click();
  await expect(page.getByTestId('card-cpi_yoy_2024')).toHaveText('5.54%');
});

test('empty and mobile states remain useful without horizontal overflow', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await login(page);
  await expect(page.getByTestId('card-expenditure_total')).toHaveText('₹49.05 L cr');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  expect(
    await page
      .locator('.kpi-value')
      .evaluateAll((nodes) => nodes.every((n) => n.scrollWidth <= n.clientWidth)),
  ).toBe(true);
  await page.mouse.move(0, 0);
  await page.screenshot({ path: '../.verification/frontend-mobile.png', fullPage: true });
  await page
    .locator('.inflation-panel')
    .screenshot({ path: '../.verification/frontend-mobile-inflation.png' });
  await page.route(
    '**/api/v1/dashboard',
    async (route) => {
      const response = await route.fetch();
      const data = await response.json();
      const panel = data.panels.find((p: IndicatorPanel) => p.id === 'trade');
      panel.series = [];
      panel.summaries = [];
      panel.state = 'empty';
      await route.fulfill({ response, json: data });
    },
    { times: 1 },
  );
  await page.getByRole('button', { name: 'Refresh stored dashboard data' }).click();
  await expect(page.getByTestId('card-trade_exports')).toHaveText('—');
  await expect(page.locator('.trade-panel .chart-empty')).toContainText('No stored observations');
  await expect(page.getByTestId('card-cpi_yoy_2024')).toHaveText('5.54%');
});

test('all panel slots reserve their final geometry while the aggregate is loading', async ({ page }) => {
  for (const viewport of [
    { width: 1214, height: 2159 },
    { width: 390, height: 844 },
  ]) {
    await page.setViewportSize(viewport);
    let release!: () => void;
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });
    await page.route('**/api/v1/dashboard', async (route) => {
      await gate;
      await route.continue().catch(() => {});
    });
    if (viewport.width === 1214) {
      await page.goto('/');
      await page.getByLabel('Username').fill('analyst');
      await page.getByLabel('Password', { exact: true }).fill(PASSWORD);
      await page.getByRole('button', { name: 'Sign in', exact: true }).click();
    } else await page.reload();
    await expect(page.locator('.panel[aria-busy="true"]')).toHaveCount(6);
    const boxes = await page
      .locator('.panel')
      .evaluateAll((nodes) => nodes.map((n) => n.getBoundingClientRect().height));
    release();
    await page.unroute('**/api/v1/dashboard');
    await expect(page.getByTestId('card-cpi_yoy_2024')).toHaveText('5.54%');
    const ready = await page
      .locator('.panel')
      .evaluateAll((nodes) => nodes.map((n) => n.getBoundingClientRect().height));
    for (let i = 0; i < 6; i++)
      expect(
        Math.abs(boxes[i] - ready[i]),
        `${viewport.width} panel ${i} ${JSON.stringify({ boxes, ready })}`,
      ).toBeLessThanOrEqual(1);
  }
});

test('an interrupted slow API read has a bounded retry path and keeps prior data', async ({ page }) => {
  await login(page);
  let release!: () => void;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route('**/api/v1/dashboard', async (route) => {
    await gate;
    await route.continue().catch(() => {});
  });
  await page.getByRole('button', { name: 'Refresh stored dashboard data' }).click();
  // AbortSignal.timeout uses active browser time, independently of the test's economic clock.
  await expect(page.getByRole('alert')).toContainText('Connection lost', { timeout: 15000 });
  await expect(page.getByTestId('card-gst_fy_total')).toHaveText('₹22.27 L cr');
  await expect(page.getByRole('button', { name: 'Refresh stored dashboard data' })).toBeEnabled();
  release();
  await page.unroute('**/api/v1/dashboard');
  await page.getByRole('button', { name: 'Retry connection' }).click();
  await expect(page.getByRole('alert')).toHaveCount(0);
});

test('real-format market snapshots use backend comparisons, retain independent failures and recover', async ({
  page,
  request,
}) => {
  const data = await login(page);
  await expect(page.locator('.market-strip')).toContainText('CLOSED');
  for (const quote of data.ticker) {
    expect(quote.value).not.toBeNull();
    await expect(page.locator('.ticker-item').filter({ hasText: quote.label }).first()).toContainText(
      quote.exchange,
    );
  }
  await page.getByRole('button', { name: /CLOSED.*Market quote/ }).click();
  await expect(page.getByRole('dialog')).toContainText('72,781.89');
  await expect(page.getByRole('dialog')).toContainText('last price minus net change');
  await closeDetails(page);
  await request.post(API + '/__test/group/market_nse/failure');
  await page.getByRole('button', { name: 'Refresh stored dashboard data' }).click();
  await expect(page.locator('.ticker-item').filter({ hasText: 'NIFTY BANK' }).first()).toContainText('STALE');
  await expect(page.locator('.ticker-item').filter({ hasText: 'SENSEX' }).first()).toContainText('CLOSED');
  await expect(page.getByTestId('card-gdp_india')).toHaveText('7.57%');
  await request.post(API + '/__test/group/market_nse/success');
  await page.getByRole('button', { name: 'Refresh stored dashboard data' }).click();
  await expect(page.locator('.ticker-item').filter({ hasText: 'NIFTY BANK' }).first()).toContainText(
    'CLOSED',
  );
  await page.route('**/api/v1/ticker', (r) => r.abort());
  await page.getByRole('button', { name: 'Refresh stored dashboard data' }).click();
  await expect(page.locator('.ticker-item').first()).toContainText('connection lost');
  await expect(page.locator('.ticker-item').first()).toContainText('74,315.61');
  await page.unroute('**/api/v1/ticker');
  await page.getByRole('button', { name: 'Refresh stored dashboard data' }).click();
  await expect(page.locator('.ticker-item').first()).toContainText('CLOSED');
});

test('ticker polling has its own single-flight boundary and cancels on account changes', async ({ page }) => {
  const data = await login(page);
  await page.waitForLoadState('networkidle');
  let release!: () => void;
  const gate = new Promise<void>((r) => {
    release = r;
  });
  let reads = 0;
  await page.route('**/api/v1/ticker', async (route) => {
    reads++;
    await gate;
    await route
      .fulfill({
        json: {
          schema_version: '1',
          generated_at: data.generated_at,
          ticker: data.ticker,
          collection_groups: data.collection_groups,
        },
      })
      .catch(() => {});
  });
  await page.clock.fastForward(90000);
  expect(reads).toBe(1);
  await page.getByRole('button', { name: /Sign out/ }).click();
  await expect(page.locator('.ticker-item')).toHaveCount(0);
  release();
  await page.unroute('**/api/v1/ticker');
  await expect(page.locator('.ticker-item')).toHaveCount(0);
  await page.getByLabel('Username').fill('reviewer');
  await page.getByLabel('Password', { exact: true }).fill(PASSWORD);
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page.locator('.account')).toContainText('reviewer');
  await expect(page.locator('.market-strip')).toContainText('CLOSED');
});

test('an initial ticker read failure marks the aggregate fallback stale and retries independently', async ({
  page,
}) => {
  await page.route('**/api/v1/ticker', (r) => r.abort());
  await login(page);
  await expect(page.locator('.ticker-item').first()).toContainText('STALE · connection lost');
  await expect(page.locator('.ticker-item').first()).toContainText('74,315.61');
  await expect(page.getByTestId('card-gdp_india')).toHaveText('7.57%');
  await page.unroute('**/api/v1/ticker');
  await page.getByRole('button', { name: 'Refresh stored dashboard data' }).click();
  await expect(page.locator('.ticker-item').first()).toContainText('CLOSED');
});

test('logout from another tab closes an open authenticated market dialog', async ({ page, context }) => {
  await login(page);
  const other = await context.newPage();
  await other.clock.install({ time: await page.evaluate(() => Date.now()) });
  await other.goto('/');
  await expect(other.getByTestId('card-gdp_india')).toHaveText('7.57%');
  await page.getByRole('button', { name: /CLOSED.*Market quote/ }).click();
  await expect(page.getByRole('dialog')).toBeVisible();
  await other.getByRole('button', { name: /Sign out/ }).click();
  await expect(page.getByRole('dialog')).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Sign in', exact: true })).toBeVisible();
  await expect(page.locator('.ticker-item')).toHaveCount(0);
});
