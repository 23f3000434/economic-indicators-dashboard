import { expect, test, type Page } from '@playwright/test';
// Uses only the explicit test harness; the ordinary preview collects live World Bank data.

const API = 'http://localhost:8001';
const PASSWORD = 'Test-only password 93!';
async function signIn(page: Page) {
  await page.goto('/');
  await page.getByLabel('Username').fill('analyst');
  await page.getByLabel('Password', { exact: true }).fill(PASSWORD);
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page.getByTestId('card-gdp_india')).toHaveText('7.57%');
}
test.beforeEach(async ({ request, page }) => {
  const response = await request.post(API + '/__test/reset');
  const { now } = await response.json();
  await page.clock.install({ time: now });
});

test('login, canonical values, reload, memory-only JWT and database-only browser traffic', async ({
  page,
  context,
}) => {
  const dataHosts = new Set<string>();
  page.on('request', (request) => {
    if (request.resourceType() === 'fetch') dataHosts.add(new URL(request.url()).origin);
  });
  const errors: string[] = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await signIn(page);
  await expect(page.getByTestId('card-gdp_world')).toHaveText('2.92%');
  await page
    .locator('.gdp-panel')
    .getByRole('button', { name: /Details & data/ })
    .click();
  await expect(
    page.getByRole('dialog').getByRole('columnheader', { name: 'India · FY', exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole('dialog').getByRole('columnheader', { name: 'World · CY', exact: true }),
  ).toBeVisible();
  await expect(page.getByTestId('table-gdp_india-2025')).toHaveText('7.57%');
  await page.getByRole('button', { name: 'Close GDP reporting and data' }).click();
  await expect(page.locator('.gdp-panel .kpis').getByText('FY 2025–26', { exact: true })).toBeVisible();
  await expect(page.locator('.gdp-panel .kpis').getByText('CY 2025', { exact: true })).toBeVisible();
  await expect(page.getByRole('heading', { name: /Government Expenditure/ })).toBeVisible();
  await expect(page.locator('.gdp-panel .recharts-bar-rectangle')).toHaveCount(10);
  await page.locator('.gdp-panel .recharts-bar-rectangle').first().hover();
  await expect(page.locator('.chart-tooltip')).toContainText('FY 2021–22');
  expect(await page.evaluate(() => [Object.keys(localStorage), Object.keys(sessionStorage)])).toEqual([
    [],
    [],
  ]);
  expect((await context.cookies()).find((c) => c.name === 'dev_refresh')?.httpOnly).toBe(true);
  await page.reload();
  await expect(page.getByTestId('card-gdp_india')).toHaveText('7.57%');
  expect([...dataHosts]).toEqual([API]);
  expect(errors).toEqual([]);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.screenshot({ path: '../.verification/browser-desktop.png', fullPage: true });
});

test('reserved geometry, connection retry, stale retention, missing gap and recovery', async ({
  page,
  request,
}) => {
  let release!: () => void;
  const blocked = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route('**/api/v1/dashboard', async (route) => {
    await blocked;
    await route.continue();
  });
  await page.goto('/');
  await page.getByLabel('Username').fill('analyst');
  await page.getByLabel('Password', { exact: true }).fill(PASSWORD);
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page.getByRole('heading', { name: /GDP Growth/ })).toBeVisible();
  const loadingBox = await page.locator('.gdp-panel').boundingBox();
  release();
  await expect(page.getByTestId('card-gdp_india')).toHaveText('7.57%');
  const readyBox = await page.locator('.gdp-panel').boundingBox();
  expect(Math.abs(loadingBox!.height - readyBox!.height)).toBeLessThanOrEqual(1);
  await page.unroute('**/api/v1/dashboard');
  await page.route('**/api/v1/dashboard', (route) => route.abort());
  await page.getByRole('button', { name: 'Refresh stored dashboard data' }).click();
  await expect(page.getByRole('alert')).toContainText('Connection lost');
  await expect(page.getByTestId('card-gdp_india')).toHaveText('7.57%');
  await page.unroute('**/api/v1/dashboard');
  await page.getByRole('button', { name: 'Retry connection' }).click();
  await expect(page.getByRole('alert')).toHaveCount(0);
  await request.post(API + '/__test/collect/failure');
  await page.getByRole('button', { name: 'Refresh stored dashboard data' }).click();
  await expect(page.getByText(/Retained data · timeout/)).toBeVisible();
  await expect(page.getByTestId('card-gdp_india')).toHaveText('7.57%');
  await request.post(API + '/__test/collect/missing');
  await page.getByRole('button', { name: 'Refresh stored dashboard data' }).click();
  await page
    .locator('.gdp-panel')
    .getByRole('button', { name: /Details & data/ })
    .click();
  await expect(page.getByTestId('table-gdp_india-2023')).toHaveText('—');
  await page.getByRole('button', { name: 'Close GDP reporting and data' }).click();
  await expect(page.locator('.gdp-panel .recharts-bar-rectangle')).toHaveCount(8);
  await request.post(API + '/__test/collect/success');
  await page.getByRole('button', { name: 'Refresh stored dashboard data' }).click();
  await page
    .locator('.gdp-panel')
    .getByRole('button', { name: /Details & data/ })
    .click();
  await expect(page.getByTestId('table-gdp_india-2023')).not.toHaveText('—');
  await page.getByRole('button', { name: 'Close GDP reporting and data' }).click();
  await expect(page.locator('.gdp-panel .status.ready')).toHaveText('Stored data');
});

test('automatic renewal, absolute expiry and logout revocation across tabs', async ({
  page,
  context,
  request,
}) => {
  await signIn(page);
  const other = await context.newPage();
  await other.clock.install({ time: (await (await request.post(API + '/__test/advance/0')).json()).now });
  await other.goto('/');
  await expect(other.getByTestId('card-gdp_india')).toHaveText('7.57%');
  let renewed = 0;
  page.on('response', (response) => {
    if (response.url().endsWith('/auth/refresh') && response.status() === 200) renewed++;
  });
  await request.post(API + '/__test/advance/901');
  await page.clock.fastForward(901000);
  await other.clock.fastForward(901000);
  await page.getByRole('button', { name: 'Refresh stored dashboard data' }).click();
  await expect.poll(() => renewed).toBeGreaterThan(0);
  await expect(page.getByTestId('card-gdp_india')).toHaveText('7.57%');
  await page.getByRole('button', { name: /Sign out/ }).click();
  await expect(page.getByRole('button', { name: 'Sign in', exact: true })).toBeVisible();
  await expect(other.getByRole('button', { name: 'Sign in', exact: true })).toBeVisible();
  await page.getByLabel('Username').fill('analyst');
  await page.getByLabel('Password', { exact: true }).fill(PASSWORD);
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page.getByTestId('card-gdp_india')).toHaveText('7.57%');
  await request.post(API + '/__test/advance/604801');
  await page.getByRole('button', { name: 'Refresh stored dashboard data' }).click();
  await expect(page.getByRole('button', { name: 'Sign in', exact: true })).toBeVisible();
});

test('concurrent tabs without Web Locks and refresh response loss recover without login', async ({
  page,
  context,
  request,
}) => {
  await context.addInitScript(() => {
    Object.defineProperty(navigator, 'locks', { value: undefined });
  });
  await signIn(page);
  const other = await context.newPage();
  const now = (await (await request.post(API + '/__test/advance/0')).json()).now;
  await other.clock.install({ time: now });
  // The server completes rotation, but the first response never reaches this browser.
  await page.route(
    '**/api/v1/auth/refresh',
    async (route) => {
      await route.fetch();
      await route.abort();
    },
    { times: 1 },
  );
  await Promise.all([page.reload(), other.goto('/')]);
  await expect(other.getByTestId('card-gdp_india')).toHaveText('7.57%');
  await expect(page.getByRole('button', { name: 'Retry connection' })).toBeVisible();
  await page.getByRole('button', { name: 'Retry connection' }).click();
  await expect(page.getByTestId('card-gdp_india')).toHaveText('7.57%');
  await request.post(API + '/__test/advance/31');
  // The cookie arrives, but a truncated body prevents confirmation. Reload recovers the pending token.
  await page.route(
    '**/api/v1/auth/refresh',
    async (route) => {
      const response = await route.fetch();
      await route.fulfill({ response, body: '{' });
    },
    { times: 1 },
  );
  await page.reload();
  await expect(page.getByRole('button', { name: 'Retry connection' })).toBeVisible();
  await page.getByRole('button', { name: 'Retry connection' }).click();
  await expect(page.getByTestId('card-gdp_india')).toHaveText('7.57%');
  // Lost confirm response is safe to retry after the server has already committed it.
  await page.route(
    '**/api/v1/auth/confirm',
    async (route) => {
      await route.fetch();
      await route.abort();
    },
    { times: 1 },
  );
  await page.reload();
  await expect(page.getByTestId('card-gdp_india')).toHaveText('7.57%');
});

test('mobile layout stays within viewport', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await signIn(page);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await expect(page.getByTestId('card-gdp_world')).toBeVisible();
  await page.screenshot({ path: '../.verification/browser-mobile.png', fullPage: true });
});

test('a late confirmed renewal cannot undo another tab logout or account change', async ({
  page,
  context,
}) => {
  await context.addInitScript(() => Object.defineProperty(navigator, 'locks', { value: undefined }));
  await signIn(page);
  const other = await context.newPage();
  await other.clock.install({ time: await page.evaluate(() => Date.now()) });
  await other.goto('/');
  await expect(other.getByTestId('card-gdp_india')).toHaveText('7.57%');
  let release!: () => void;
  let reached!: () => void;
  const held = new Promise<void>((resolve) => {
    release = resolve;
  });
  const confirmed = new Promise<void>((resolve) => {
    reached = resolve;
  });
  await page.route(
    '**/api/v1/auth/confirm',
    async (route) => {
      const response = await route.fetch();
      reached();
      await held;
      await route.fulfill({ response });
    },
    { times: 1 },
  );
  await page.reload();
  await confirmed;
  await other.getByRole('button', { name: /Sign out/ }).click();
  await expect(page.getByRole('button', { name: 'Sign in', exact: true })).toBeVisible();
  release();
  await expect(page.getByTestId('card-gdp_india')).toHaveCount(0);
  await other.getByLabel('Username').fill('reviewer');
  await other.getByLabel('Password', { exact: true }).fill(PASSWORD);
  await other.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page.locator('.account')).toContainText('reviewer');
  await expect(page.getByTestId('card-gdp_india')).toHaveText('7.57%');
  await expect(other.locator('.account')).toContainText('reviewer');
});

test('obsolete proactive renewal cannot add an error to a newer account dashboard', async ({
  page,
  context,
  request,
}) => {
  await context.addInitScript(() => Object.defineProperty(navigator, 'locks', { value: undefined }));
  await signIn(page);
  const other = await context.newPage();
  await other.clock.install({ time: await page.evaluate(() => Date.now()) });
  await other.goto('/');
  await expect(other.getByTestId('card-gdp_india')).toHaveText('7.57%');
  let release!: () => void;
  let reached!: () => void;
  const held = new Promise<void>((resolve) => {
    release = resolve;
  });
  const confirmed = new Promise<void>((resolve) => {
    reached = resolve;
  });
  await page.route(
    '**/api/v1/auth/confirm',
    async (route) => {
      const response = await route.fetch();
      reached();
      await held;
      await route.fulfill({ response });
    },
    { times: 1 },
  );
  await request.post(API + '/__test/advance/901');
  await page.clock.fastForward(901000);
  await confirmed;
  await other.reload();
  await expect(other.getByTestId('card-gdp_india')).toHaveText('7.57%');
  await other.getByRole('button', { name: /Sign out/ }).click();
  await other.getByLabel('Username').fill('reviewer');
  await other.getByLabel('Password', { exact: true }).fill(PASSWORD);
  await other.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page.locator('.account')).toContainText('reviewer');
  await expect(page.getByTestId('card-gdp_india')).toHaveText('7.57%');
  const delivered = page.waitForResponse((r) => r.url().endsWith('/auth/confirm'));
  release();
  await delivered;
  await page.clock.runFor(100);
  await expect(page.getByRole('alert')).toHaveCount(0);
});
