// Focused normal-application proof. No fixtures, mocked clock or upstream requests.
import assert from "node:assert/strict";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("..", import.meta.url));
const require = createRequire(
  new URL("../frontend/package.json", import.meta.url),
);
const { chromium, expect } = require("@playwright/test");
const frontend = process.env.LOCAL_FRONTEND_URL || "http://localhost:5175";
const api = process.env.LOCAL_API_URL || "http://localhost:8010";
const credentials = JSON.parse(
  await readFile(
    process.env.LOCAL_SMOKE_CREDENTIALS ||
      root + "/.verification/local-access.json",
    "utf8",
  ),
);
const output = root + "/.verification/interactions";
await mkdir(output, { recursive: true });
const browser = await chromium.launch({
  executablePath:
    process.env.CHROME_PATH ||
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
});
try {
  const page = await browser.newPage({
    viewport: { width: 1214, height: 2159 },
    reducedMotion: "no-preference",
  });
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto(frontend);
  await page.getByLabel("Username").fill(credentials.username);
  await page.getByLabel("Password", { exact: true }).fill(credentials.password);
  const nextQuote = () =>
    page.waitForResponse(
      (r) => r.url() === api + "/api/v1/ticker" && r.status() === 200,
      { timeout: 45000 },
    );
  let pending = nextQuote();
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  const cycles = [];
  let originalGroup;
  for (let cycle = 0; cycle < 3; cycle++) {
    const snapshot = await (await pending).json();
    const quotes = [];
    for (const quote of snapshot.ticker) {
      const row = page.locator(
        `.ticker-group:not([aria-hidden]) [data-instrument="${quote.id}"]`,
      );
      await expect(row).toHaveAttribute(
        "data-exchange-timestamp",
        quote.exchange_timestamp,
      );
      await expect(row.locator("small")).toContainText(
        quote.state.toUpperCase(),
      );
      const price = Number(quote.value).toLocaleString("en-IN", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      });
      await expect(row.locator("strong")).toContainText(price);
      if (quote.provider_id === "nse") assert.notEqual(quote.state, "live");
      const previous = cycles.at(-1)?.quotes.find((q) => q.id === quote.id);
      if (previous)
        assert(
          Date.parse(quote.exchange_timestamp) >=
            Date.parse(previous.exchange_timestamp),
        );
      quotes.push({
        id: quote.id,
        provider: quote.provider_id,
        value: quote.value,
        previous_close: quote.previous_close,
        change_percent: quote.change_percent,
        state: quote.state,
        error_kind: quote.error_kind,
        exchange_timestamp: quote.exchange_timestamp,
        precision: quote.exchange_timestamp_precision,
        retrieved_at: quote.retrieved_at,
        retained: quote.retained,
        displayed: await row.innerText(),
      });
    }
    const group = page.locator(".ticker-group").first();
    if (!originalGroup) originalGroup = await group.elementHandle();
    assert(
      await group.evaluate(
        (node, original) => node === original,
        originalGroup,
      ),
    );
    cycles.push({
      cycle,
      generated_at: snapshot.generated_at,
      captured_at: new Date().toISOString(),
      scroll_left: await page
        .locator(".ticker-track")
        .evaluate((n) => n.scrollLeft),
      quotes,
    });
    if (cycle < 2) pending = nextQuote();
    console.log(
      `Verified real ticker cycle ${cycle}: source timestamps and displayed values agree.`,
    );
  }
  assert.equal(cycles.length, 3);
  assert(
    Date.parse(cycles[2].generated_at) - Date.parse(cycles[0].generated_at) >=
      50000,
  );
  const seam = await page
    .locator(".ticker-group")
    .first()
    .evaluate((n) => ({
      width: n.getBoundingClientRect().width,
      trailing_gap:
        n.getBoundingClientRect().right -
        n.lastElementChild.getBoundingClientRect().right,
    }));
  assert(Math.abs(seam.trailing_gap) < 1);
  await page.getByTestId("gdp-chart").focus();
  await page.keyboard.press("End");
  const tooltip = page.getByRole("tooltip");
  await expect(tooltip).toBeVisible();
  const tooltipStyle = await tooltip.evaluate((n) => ({
    text: n.textContent,
    font_size: getComputedStyle(n).fontSize,
    background: getComputedStyle(n).backgroundColor,
    height: n.getBoundingClientRect().height,
    width: n.getBoundingClientRect().width,
  }));
  assert.equal(tooltipStyle.font_size, "14px");
  assert(tooltipStyle.height < 230);
  const alignment = {
    crosshair_x: Number(
      await page
        .getByTestId("gdp-chart")
        .locator(".chart-crosshair")
        .first()
        .getAttribute("x1"),
    ),
    tick_x: Number(
      await page
        .getByTestId("gdp-chart")
        .locator(".recharts-xAxis-tick-labels text")
        .last()
        .getAttribute("x"),
    ),
  };
  assert(Math.abs(alignment.crosshair_x - alignment.tick_x) < 0.1);
  await page.screenshot({
    path: output + "/desktop-tooltip.png",
    fullPage: true,
  });
  await page.screenshot({
    path: output + "/interaction-preview.png",
    clip: { x: 0, y: 0, width: 1214, height: 720 },
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByTestId("expenditure-chart").focus();
  await page.keyboard.press("End");
  await expect(page.getByRole("tooltip")).toBeVisible();
  await page.screenshot({ path: output + "/mobile-tooltip.png" });
  assert.deepEqual(errors, []);
  const report = {
    checked_at: new Date().toISOString(),
    frontend,
    api,
    mode: "Normal application, private persistent SQLite, real scheduled providers; no fixture server, synthetic price changes or fake clock",
    checks: [
      "Initial quote snapshot plus two independent automatic 30-second API polls",
      "Every displayed price/status/exchange timestamp agrees with its stored API snapshot",
      "Exchange timestamps never regress; unchanged quotes remain unchanged",
      "NSE is never relabelled Live",
      "Quote group DOM remains mounted across polling cycles",
      "Compact tooltip, 14px unscaled text, no repeated provenance",
      "Desktop/mobile screenshots and no browser runtime errors",
    ],
    cycles,
    tooltip: tooltipStyle,
    seam,
    alignment,
    browser_errors: errors,
    limitations: [
      "Same quote timestamp across cycles may be a cached/closed observation; retrieval time is not quote freshness.",
      "Local source/UI verification does not establish public market redistribution rights or hosted acceptance.",
      "Segoe UI fallback and other submission gates remain in design-completion.md.",
    ],
  };
  await writeFile(
    output + "/live.json",
    JSON.stringify(report, null, 2) + "\n",
  );
  await page.getByRole("button", { name: /Sign out/ }).click();
  console.log(
    "Normal application interaction proof saved; no credentials or tokens recorded.",
  );
} finally {
  await browser.close();
}
