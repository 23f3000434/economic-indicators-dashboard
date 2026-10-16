import { test, expect, type Page } from '@playwright/test';
import type { Dashboard, Panel as GdpPanel, IndicatorPanel } from '../src/contracts';

const API = 'http://localhost:8001';
test.beforeEach(async ({ page, request }) => {
  const { now } = await (await request.post(API + '/__test/reset')).json();
  await page.clock.install({ time: now });
});
async function login(page: Page) {
  await page.goto('/');
  await page.getByLabel('Username').fill('analyst');
  await page.getByLabel('Password', { exact: true }).fill('Test-only password 93!');
  const response = page.waitForResponse((r) => r.url().endsWith('/api/v1/dashboard') && r.status() === 200);
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page.getByTestId('card-gdp_india')).toHaveText('7.57%');
  await expect(page.locator('.ticker-item')).toHaveCount(6);
  return (await (await response).json()) as Dashboard;
}
const tip = (page: Page, id: string) => page.locator(`.chart-tooltip[data-chart="${id}"]`);
async function plot(page: Page, id: string) {
  const grid = page.getByTestId(`${id}-chart`).locator('.recharts-cartesian-grid');
  await grid.scrollIntoViewIfNeeded();
  return (await grid.boundingBox())!;
}
function display(value: string | null, unit: string, signed = false) {
  if (value == null) return '—';
  const raw = Number(value);
  const number = (unit === 'inr_crore' ? raw / 100000 : raw).toLocaleString('en-IN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  return unit === 'inr_crore'
    ? `₹${number} L cr`
    : unit === 'usd_billion'
      ? `$${signed && raw > 0 ? '+' : ''}${number} B`
      : `${number}%`;
}

test('interaction pass: all six charts share compact canonical periods, values and active marks', async ({
  page,
}) => {
  const data = await login(page);
  const shape = await page.locator('.panel').evaluateAll((nodes) =>
    nodes.map((n) => {
      const r = n.getBoundingClientRect();
      return { x: r.x, y: r.y, w: r.width, h: r.height };
    }),
  );
  for (const panel of data.panels) {
    const id = panel.id,
      chart = page.getByTestId(`${id}-chart`);
    await chart.focus();
    await page.keyboard.press('End');
    const tooltip = tip(page, id);
    await expect(tooltip).toBeVisible();
    await expect(chart.locator('.chart-crosshair')).toHaveCount(2);
    if (['gdp', 'trade', 'gst', 'expenditure'].includes(id)) {
      const crosshairX = Number(await chart.locator('.chart-crosshair').first().getAttribute('x1'));
      const tickX = Number(await chart.locator('.recharts-xAxis-tick-labels text').last().getAttribute('x'));
      expect(crosshairX).toBeCloseTo(tickX, 4);
    }
    const key = (await tooltip.getAttribute('data-period'))!;
    for (const row of await tooltip.locator('.tooltip-row').all()) {
      const sid = (await row.getAttribute('data-series'))!;
      let value: string | null = null,
        unit = 'percent';
      if (id === 'gdp') {
        const s = (panel as GdpPanel).series.find((s) => s.id === sid)!;
        value = s.points.find((p) => p.period_key === key)?.value ?? null;
      } else {
        const p = panel as IndicatorPanel;
        const s = p.series.find((s) => s.id === sid);
        const point = s?.points.find(
          (p) => (id === 'debt' ? p.period.start.slice(0, 4) : p.period.key) === key,
        );
        value = point?.value ?? null;
        unit = s?.unit || 'percent';
        if (sid === 'inflation_target') {
          const month = p.series
            .find((s) => s.id === 'cpi_yoy_2024')!
            .points.find((p) => p.period.key === key)!;
          const policy = p.policies.find(
            (p) => p.validity.start <= month.period.start && month.period.end <= p.validity.end,
          );
          value = policy
            ? p.series
                .find((s) => s.id === policy.target.series_id)!
                .points.find((p) => p.period.key === policy.target.period_key)!.value
            : null;
        }
      }
      await expect(row.locator('b')).toHaveText(display(value, unit, sid === 'trade_balance'));
    }
    await expect(tooltip).not.toContainText(/Published|Retrieved|https:|publication note/i);
    const style = await tooltip.evaluate((n) => ({
      size: getComputedStyle(n).fontSize,
      background: getComputedStyle(n).backgroundColor,
      parent: n.parentElement?.tagName,
      z: getComputedStyle(n).zIndex,
      height: n.getBoundingClientRect().height,
    }));
    expect(style.size).toBe('14px');
    expect(style.background).toBe('rgb(8, 22, 37)');
    expect(style.parent).toBe('BODY');
    expect(Number(style.z)).toBeGreaterThanOrEqual(1000);
    expect(style.height).toBeLessThan(230);
    expect(await chart.locator('.chart-active-bar, .chart-active-point').count()).toBeGreaterThan(0);
    await page.keyboard.press('Escape');
    await expect(page.getByRole('tooltip')).toHaveCount(0);
  }
  expect(
    await page.locator('.panel').evaluateAll((nodes) =>
      nodes.map((n) => {
        const r = n.getBoundingClientRect();
        return { x: r.x, y: r.y, w: r.width, h: r.height };
      }),
    ),
  ).toEqual(shape);
  await page
    .locator('.gdp-panel')
    .getByRole('button', { name: /Details & data/ })
    .click();
  await page.getByRole('dialog').getByText('Methodology, sources and observation notes').click();
  await expect(page.locator('.observation-details')).toContainText('Published');
  await expect(page.locator('.observation-details')).toContainText('api.worldbank.org');
});

test('interaction pass: pointer period changes, shared series, pinning, dismissal and missing bars', async ({
  page,
  request,
}) => {
  await login(page);
  // Both bars in one period must resolve to the same category, including
  // the right-hand World bar beyond the category centre.
  const bars = page.getByTestId('gdp-chart').locator('.recharts-bar-rectangle');
  await bars.nth(0).hover();
  await expect(tip(page, 'gdp')).toHaveAttribute('data-period', '2021');
  await bars.nth(5).hover();
  await expect(tip(page, 'gdp')).toHaveAttribute('data-period', '2021');
  for (const id of ['gdp', 'debt', 'trade', 'gst', 'inflation', 'expenditure']) {
    const r = await plot(page, id);
    await page.mouse.move(r.x + r.width * 0.12, r.y + r.height / 2);
    await expect(tip(page, id)).toBeVisible();
    const first = await tip(page, id).getAttribute('data-period');
    await page.mouse.move(r.x + r.width * 0.88, r.y + r.height / 2);
    await expect(tip(page, id)).not.toHaveAttribute('data-period', first!);
    const count = id === 'trade' || id === 'expenditure' ? 3 : 2;
    await expect(tip(page, id).locator('.tooltip-row')).toHaveCount(count);
    await page.mouse.click(r.x + r.width * 0.88, r.y + r.height / 2);
    await expect(tip(page, id)).toHaveAttribute('data-pinned', 'true');
    await page.mouse.move(0, 0);
    await expect(tip(page, id)).toBeVisible();
    await page.mouse.click(0, 0);
    await expect(page.getByRole('tooltip')).toHaveCount(0);
  }
  await page.locator('.trade-panel').getByRole('button', { name: 'Imports', exact: true }).click();
  const trade = page.getByTestId('trade-chart');
  await trade.focus();
  await page.keyboard.press('End');
  await expect(tip(page, 'trade').locator('[data-series="trade_imports"]')).toHaveCount(0);
  await expect(tip(page, 'trade').locator('.tooltip-row')).toHaveCount(2);
  await request.post(API + '/__test/collect/missing');
  await page.getByRole('button', { name: 'Refresh stored dashboard data' }).click();
  await page.getByTestId('gdp-chart').focus();
  await page.keyboard.press('Home');
  await page.keyboard.press('ArrowRight');
  await page.keyboard.press('ArrowRight');
  await expect(tip(page, 'gdp')).toHaveAttribute('data-period', '2023');
  await expect(tip(page, 'gdp').locator('[data-series="gdp_india"]')).toContainText('Missing');
  await expect(tip(page, 'gdp').locator('[data-series="gdp_india"] b')).toHaveText('—');
  await expect(tip(page, 'gdp').locator('[data-series="gdp_world"] b')).toHaveText('—');
  await expect(page.getByTestId('gdp-chart').locator('.chart-active-bar')).toHaveCount(0);
});

test.describe('touch interaction pass', () => {
  test.use({ viewport: { width: 390, height: 844 }, hasTouch: true });
  test('tap selection flips and clamps the opaque tooltip, then dismisses on a second tap', async ({
    page,
  }) => {
    await login(page);
    const r = await plot(page, 'expenditure');
    const x = r.x + r.width * 0.92,
      y = r.y + r.height * 0.85;
    await page.touchscreen.tap(x, y);
    const tooltip = tip(page, 'expenditure');
    await expect(tooltip).toBeVisible();
    await expect(tooltip).toHaveAttribute('data-pinned', 'true');
    const box = (await tooltip.boundingBox())!;
    expect(box.x).toBeGreaterThanOrEqual(8);
    expect(box.y).toBeGreaterThanOrEqual(8);
    expect(box.x + box.width).toBeLessThanOrEqual(382);
    expect(box.y + box.height).toBeLessThanOrEqual(836);
    await page.screenshot({ path: '../.verification/interaction-mobile.png' });
    await page.touchscreen.tap(x, y);
    await expect(page.getByRole('tooltip')).toHaveCount(0);
  });
});

test('interaction pass: seamless ticker pauses, allows manual scrolling and preserves phase over two polls', async ({
  page,
}) => {
  await page.emulateMedia({ reducedMotion: 'no-preference' });
  await login(page);
  const track = page.locator('.ticker-track'),
    first = track.locator('.ticker-group').first();
  await page.mouse.move(0, 200);
  const initial = await track.evaluate((n) => n.scrollLeft);
  await page.clock.runFor(1000);
  expect(await track.evaluate((n) => n.scrollLeft)).toBeGreaterThan(initial + 20);
  await track.hover();
  const paused = await track.evaluate((n) => n.scrollLeft);
  await page.clock.runFor(1000);
  expect(await track.evaluate((n) => n.scrollLeft)).toBeCloseTo(paused, 0);
  await track.focus();
  await page.mouse.move(0, 200);
  await page.clock.runFor(500);
  expect(await track.evaluate((n) => n.scrollLeft)).toBeCloseTo(paused, 0);
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.locator('#gdp-title').click();
  const stopped = await track.evaluate((n) => n.scrollLeft);
  await page.clock.runFor(1000);
  expect(await track.evaluate((n) => n.scrollLeft)).toBeCloseTo(stopped, 0);
  await track.hover();
  await page.mouse.wheel(180, 0);
  await expect.poll(() => track.evaluate((n) => n.scrollLeft)).toBeGreaterThan(stopped + 50);
  await page.mouse.move(0, 200);
  const width = await first.evaluate((n) => parseFloat(getComputedStyle(n).width));
  const gap = await first.evaluate(
    (n) => n.getBoundingClientRect().right - n.lastElementChild!.getBoundingClientRect().right,
  );
  expect(Math.abs(gap)).toBeLessThan(1);
  await track.evaluate((n, w) => {
    n.scrollLeft = w - 1;
  }, width);
  await page.emulateMedia({ reducedMotion: 'no-preference' });
  await page.clock.runFor(2000);
  expect(await track.evaluate((n) => n.scrollLeft)).toBeLessThan(80);
  expect(await first.innerText()).toBe(await track.locator('.ticker-group').last().innerText());
  await track.evaluate((n) => {
    n.scrollLeft = 250;
  });
  const original = await first.elementHandle();
  for (let cycle = 0; cycle < 2; cycle++) {
    const response = page.waitForResponse((r) => r.url().endsWith('/api/v1/ticker') && r.status() === 200);
    await page.clock.fastForward(30000);
    await response;
    expect(await track.evaluate((n) => n.scrollLeft)).toBeGreaterThan(245);
    expect(await first.evaluate((n, old) => n === old, original)).toBe(true);
    await expect(first).toContainText('CLOSED');
    await expect(first).not.toContainText('LIVE');
  }
});
