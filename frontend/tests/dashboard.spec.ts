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
async function checkSummary(page: Page, panel: IndicatorPanel, id: string, kind: PeriodKind) {
  const summary = panel.summaries.find((s) => s.current.series_id === id && s.period_kind === kind)!;
  const point = pointAt(panel, id, summary.current.period_key);
  await expect(page.getByTestId(`card-${id}`)).toHaveText(expected(point, id === 'trade_balance'));
  await expect(page.getByTestId(`table-${id}-${point.period.key}`)).toHaveText(
    expected(point, id === 'trade_balance'),
  );
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
  await expect(page.locator('.debt-panel .status')).toHaveText('unavailable');
  await expect(page.getByTestId('card-debt_india')).toHaveText('—');
  await expect(page.getByTestId('card-debt_us')).toHaveText('—');
  await expect(page.locator('.market-strip')).toContainText('Unavailable');
  await expect(page.locator('.market-strip')).not.toContainText(/live/i);
  await expect(page.locator('.gst-panel')).toContainText('excluding compensation cess');
  const trade = page.locator('.trade-panel');
  await trade.locator('.recharts-bar-rectangle').first().hover();
  const first = panelAt(data, 'trade')
    .series.find((s) => s.id === 'trade_exports')!
    .points.find((p) => p.period.kind === 'fiscal_year')!;
  await expect(trade.locator('.chart-tooltip')).toContainText(expected(first));
  await expect(page.getByTestId(`table-trade_exports-${first.period.key}`)).toHaveText(expected(first));
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
  expect(geometry[0].width).toBe(566);
  expect(geometry[0].height).toBe(630);
  expect(geometry[2].y - geometry[0].y).toBe(654);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  expect(
    await page
      .locator('.kpi-value')
      .evaluateAll((nodes) => nodes.every((n) => n.scrollWidth <= n.clientWidth)),
  ).toBe(true);
  const assets = await page.locator('.card-art').evaluateAll(async (nodes) => {
    return await Promise.all(
      nodes.map(async (n) => {
        const bg = getComputedStyle(n).backgroundImage;
        const url = bg.match(/url\(["']?(.*?)["']?\)/)?.[1];
        if (!url) return false;
        const image = new Image();
        image.src = url;
        await image.decode();
        const r = n.getBoundingClientRect(),
          card = n.parentElement!.getBoundingClientRect();
        return (
          image.naturalWidth > 0 &&
          image.naturalHeight > 0 &&
          r.width > 0 &&
          r.height > 0 &&
          r.left >= card.left &&
          r.right <= card.right &&
          r.bottom <= card.bottom
        );
      }),
    );
  });
  expect(assets.every(Boolean)).toBe(true);
  await page.screenshot({ path: '../.verification/frontend-desktop.png', fullPage: true });
});

test('period controls, history and legend toggles select the same cards, plots, tooltip and table', async ({
  page,
}) => {
  const data = await login(page);
  let reads = 0;
  page.on('request', (r) => {
    if (r.url().endsWith('/api/v1/dashboard')) reads++;
  });
  await page.getByLabel('trade reporting period').selectOption('fiscal_year_to_date');
  await checkSummary(page, panelAt(data, 'trade'), 'trade_exports', 'fiscal_year_to_date');
  await checkSummary(page, panelAt(data, 'trade'), 'trade_imports', 'fiscal_year_to_date');
  await checkSummary(page, panelAt(data, 'trade'), 'trade_balance', 'fiscal_year_to_date');
  await expect(page.locator('.trade-panel .observations tbody tr')).toHaveCount(2);
  const imports = page.locator('.trade-panel').getByRole('button', { name: 'Imports', exact: true });
  await imports.click();
  await expect(imports).toHaveAttribute('aria-pressed', 'false');
  await expect(
    page.locator('.trade-panel .observations').getByRole('columnheader', { name: 'Imports', exact: true }),
  ).toHaveCount(0);
  await expect(page.getByTestId('card-trade_imports')).not.toHaveText('—');
  await imports.click();
  await expect(
    page.locator('.trade-panel .observations').getByRole('columnheader', { name: 'Imports', exact: true }),
  ).toBeVisible();
  await page.getByLabel('gst reporting period').selectOption('fiscal_year_to_date');
  await checkSummary(page, panelAt(data, 'gst'), 'gst_fytd_average', 'fiscal_year_to_date');
  await page.getByLabel('gst reporting period').selectOption('month');
  await checkSummary(page, panelAt(data, 'gst'), 'gst_gross_ex_cess', 'month');
  await expect(page.locator('.gst-panel .observations tbody tr')).toHaveCount(12);
  await page.getByLabel('gst history window').selectOption('24');
  await expect(page.locator('.gst-panel .observations tbody tr')).toHaveCount(24);
  await page.getByLabel('expenditure reporting period').selectOption('fiscal_year_to_date');
  await checkSummary(page, panelAt(data, 'expenditure'), 'expenditure_total', 'fiscal_year_to_date');
  await checkSummary(page, panelAt(data, 'expenditure'), 'expenditure_capital', 'fiscal_year_to_date');
  await page.getByLabel('GDP history window').selectOption('3');
  await expect(page.locator('.gdp-panel .recharts-bar-rectangle')).toHaveCount(6);
  await expect(page.locator('.gdp-panel tbody tr')).toHaveCount(3);
  await page.getByLabel('GDP history window').selectOption('50');
  await expect(page.locator('.gdp-panel .recharts-bar-rectangle')).toHaveCount(10);
  expect(reads).toBe(0); // controls only select stored canonical observations
});

test('CPI bases and missing months stay separate; dated policy never extends beyond its window', async ({
  page,
}) => {
  await login(page);
  await expect(page.getByTestId('table-inflation_target-2026-03')).toHaveText('—');
  await expect(page.getByTestId('table-inflation_target-2026-04')).toHaveText('4.00%');
  await page.getByLabel('CPI methodology').selectOption('cpi_yoy_2012');
  await page.getByLabel('inflation history window').selectOption('600');
  await expect(page.getByTestId('card-cpi_yoy_2024')).toHaveCount(0);
  await expect(page.getByTestId('card-inflation_target')).toHaveText('—');
  await expect(page.getByTestId('table-cpi_yoy_2012-2020-04')).toHaveText('—');
  await expect(page.getByTestId('table-cpi_yoy_2012-2020-05')).toHaveText('—');
  const path = await page.locator('.inflation-panel .recharts-area-curve').getAttribute('d');
  expect((path?.match(/M/g) || []).length).toBeGreaterThanOrEqual(2);
  expect(
    await page
      .locator('.inflation-panel .recharts-line-curve')
      .evaluateAll((paths) => paths.every((p) => !p.getAttribute('d'))),
  ).toBe(true);
  await page.getByLabel('CPI methodology').selectOption('cpi_yoy_2024');
  await expect(page.getByTestId('card-cpi_yoy_2024')).toHaveText('5.54%');
  await expect(page.getByTestId('card-inflation_target')).toHaveText('4.00%');
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

test('keyboard controls, focus visibility, chart inspection and table alternatives work', async ({
  page,
}) => {
  await login(page);
  const window = page.getByLabel('GDP history window');
  await window.focus();
  await window.selectOption('3');
  expect(await window.evaluate((n) => getComputedStyle(n).outlineStyle)).not.toBe('none');
  const world = page.locator('.gdp-panel').getByRole('button', { name: 'World', exact: true });
  await world.focus();
  await page.keyboard.press('Space');
  await expect(world).toHaveAttribute('aria-pressed', 'false');
  await expect(
    page.locator('.gdp-panel .observations').getByRole('columnheader', { name: /World/ }),
  ).toHaveCount(0);
  const table = page.getByRole('region', { name: 'GDP observations table' });
  await table.focus();
  await page.keyboard.press('ArrowDown');
  await expect(table).toBeFocused();
  const chart = page.locator('.gdp-panel').getByRole('application');
  await chart.focus();
  await page.keyboard.press('ArrowRight');
  await expect(page.locator('.gdp-panel .chart-tooltip')).toContainText('India');
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
  await expect(page.getByRole('heading', { name: /GST Collection could not open/ })).toBeVisible();
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
