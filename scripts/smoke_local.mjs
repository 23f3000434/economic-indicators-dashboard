// Normal application acceptance: no fixtures. Credentials and snapshots remain ignored.
import { readFile, writeFile } from "node:fs/promises";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import assert from "node:assert/strict";

const root = fileURLToPath(new URL("..", import.meta.url));
const require = createRequire(
  new URL("../frontend/package.json", import.meta.url),
);
const { chromium } = require("@playwright/test");
const frontend = process.env.LOCAL_FRONTEND_URL || "http://localhost:5175";
const api = process.env.LOCAL_API_URL || "http://localhost:8010";
const credentials = JSON.parse(
  await readFile(
    process.env.LOCAL_SMOKE_CREDENTIALS ||
      root + "/.verification/local-access.json",
    "utf8",
  ),
);
assert.equal((await fetch(api + "/healthz")).status, 200);
assert.equal((await fetch(api + "/api/v1/dashboard")).status, 401);
const browser = await chromium.launch({
  executablePath:
    process.env.CHROME_PATH ||
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
});
try {
  const context = await browser.newContext({
    viewport: { width: 1214, height: 2159 },
    reducedMotion: "reduce",
  });
  const page = await context.newPage();
  const errors = [],
    origins = new Set(),
    agreement = [];
  let access = "";
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("request", (r) => {
    if (r.resourceType() === "fetch") origins.add(new URL(r.url()).origin);
    const bearer = r.headers().authorization;
    if (bearer?.startsWith("Bearer ")) access = bearer.slice(7);
  });
  await page.goto(frontend);
  await page.getByLabel("Username").fill(credentials.username);
  await page.getByLabel("Password", { exact: true }).fill(credentials.password);
  const response = page.waitForResponse(
    (r) => r.url() === api + "/api/v1/dashboard" && r.status() === 200,
  );
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  const dashboard = await (await response).json();
  for (const panel of dashboard.panels) {
    if (panel.id === "debt") {
      assert.equal(panel.availability, "blocked");
      await page
        .getByTestId("card-debt_india")
        .filter({ hasText: "—" })
        .waitFor();
      continue;
    }
    assert(["ready", "stale"].includes(panel.state));
    const ids =
      panel.id === "gdp"
        ? ["gdp_india", "gdp_world"]
        : panel.id === "trade"
          ? ["trade_exports", "trade_imports", "trade_balance"]
          : panel.id === "gst"
            ? ["gst_fy_total", "gst_fy_average"]
            : panel.id === "inflation"
              ? ["cpi_yoy_2024"]
              : ["expenditure_total", "expenditure_capital"];
    for (const id of ids) {
      const summary = panel.summaries.find((s) =>
        panel.id === "gdp"
          ? s.series_id === id
          : s.current.series_id === id &&
            s.period_kind ===
              (panel.id === "inflation" ? "month" : "fiscal_year"),
      );
      const key =
        panel.id === "gdp"
          ? summary.current_period_key
          : summary.current.period_key;
      const series = panel.series.find((s) => s.id === id);
      const point = series.points.find(
        (p) => (panel.id === "gdp" ? p.period_key : p.period.key) === key,
      );
      const raw = Number(point.value);
      const value = (
        series.unit === "inr_crore" ? raw / 100000 : raw
      ).toLocaleString("en-IN", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      });
      const display =
        point.value === null
          ? "—"
          : series.unit === "percent"
            ? value + "%"
            : series.unit === "inr_crore"
              ? `₹${value} L cr`
              : `$${id === "trade_balance" && raw > 0 ? "+" : ""}${value} B`;
      await page
        .getByTestId("card-" + id)
        .filter({ hasText: display })
        .waitFor();
      assert.equal(
        await page.getByTestId(`table-${id}-${key}`).innerText(),
        display,
      );
      agreement.push({
        series: id,
        period_key: key,
        value: point.value,
        unit: series.unit,
        display,
        retained: point.retained,
      });
    }
  }
  assert.deepEqual(
    await page.evaluate(() => [
      Object.keys(localStorage),
      Object.keys(sessionStorage),
    ]),
    [[], []],
  );
  await page.reload();
  await page
    .getByTestId("card-cpi_yoy_2024")
    .filter({ hasText: "%" })
    .waitFor();
  const cookie = (await context.cookies()).find(
    (c) => c.name === "dev_refresh",
  );
  assert(
    cookie?.httpOnly &&
      !cookie.secure &&
      cookie.sameSite === "Strict" &&
      cookie.expires > Date.now() / 1000,
  );
  assert(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  );
  await page.waitForLoadState("networkidle");
  await page.mouse.move(0, 0);
  const geometry = await page.locator(".panel").evaluateAll((nodes) =>
    nodes.map((n) => {
      const r = n.getBoundingClientRect();
      return { x: r.x, y: r.y, width: r.width, height: r.height };
    }),
  );
  await page.screenshot({
    path: root + "/.verification/live-full-desktop.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  assert(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  );
  await page.screenshot({
    path: root + "/.verification/live-full-mobile.png",
    fullPage: true,
  });
  const timings = [];
  for (let i = 0; i < 5; i++) {
    const started = performance.now();
    assert.equal(
      (
        await fetch(api + "/api/v1/dashboard", {
          headers: { Authorization: "Bearer " + access },
        })
      ).status,
      200,
    );
    timings.push(performance.now() - started);
  }
  await page.getByRole("button", { name: /Sign out/ }).click();
  await page.getByRole("button", { name: "Sign in", exact: true }).waitFor();
  assert.equal(
    (
      await fetch(api + "/api/v1/dashboard", {
        headers: { Authorization: "Bearer " + access },
      })
    ).status,
    401,
  );
  assert.deepEqual([...origins], [api]);
  assert.deepEqual(errors, []);
  const report = {
    checked_at: new Date().toISOString(),
    frontend,
    api,
    mode: "Normal application factory and persistent private SQLite; no test harness or fixtures",
    checks: [
      "unauthenticated aggregate denied",
      "login",
      "canonical card/table agreement across all implemented panels",
      "actual debt/market unavailable states",
      "reload renewal",
      "memory-only JWT",
      "persistent HttpOnly local cookie",
      "desktop/mobile no horizontal overflow",
      "API-only browser data fetches",
      "logout revokes prior access JWT",
      "no browser runtime errors",
    ],
    canonical_agreement: agreement,
    panels: dashboard.panels.map((p) => ({ id: p.id, state: p.state })),
    ticker: dashboard.ticker,
    collection_groups: dashboard.collection_groups,
    desktop_panel_geometry: geometry,
    read_latency_ms: { min: Math.min(...timings), max: Math.max(...timings) },
    cookie: {
      name: cookie.name,
      httpOnly: cookie.httpOnly,
      secure: cookie.secure,
      sameSite: cookie.sameSite,
    },
  };
  await writeFile(
    process.env.LOCAL_SMOKE_REPORT || root + "/.verification/live-ui.json",
    JSON.stringify(report, null, 2) + "\n",
  );
  console.log(
    JSON.stringify({
      result: "passed",
      checks: report.checks.length,
      canonical_values: agreement.length,
      read_latency_ms: report.read_latency_ms,
    }),
  );
} finally {
  await browser.close();
}
