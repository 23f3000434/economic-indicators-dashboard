// Cold local-browser measurements. Never seeds data or writes credentials into evidence.
import { readFile, writeFile, mkdir } from "node:fs/promises";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import assert from "node:assert/strict";
const root = fileURLToPath(new URL("..", import.meta.url));
const require = createRequire(
  new URL("../frontend/package.json", import.meta.url),
);
const { chromium } = require("@playwright/test");
const phase = process.env.MEASUREMENT_PHASE || "baseline";
assert(/^[a-z0-9-]+$/.test(phase));
const site = process.env.LOCAL_FRONTEND_URL || "http://localhost:5175";
assert.equal(new URL(site).hostname, "localhost");
const credentials = JSON.parse(
  await readFile(root + "/.verification/local-access.json", "utf8"),
);
const output = root + "/.verification/hardening";
await mkdir(output, { recursive: true });
const browser = await chromium.launch({
  executablePath:
    process.env.CHROME_PATH ||
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
});
const runs = [];
try {
  for (const [name, width, height, dpr] of [
    ["desktop", 1214, 2159, 1],
    ["mobile", 390, 844, 1],
    ["desktop-retina", 1214, 2159, 2],
    ["mobile-retina", 390, 844, 2],
  ]) {
    const context = await browser.newContext({
      viewport: { width, height },
      deviceScaleFactor: dpr,
      reducedMotion: "reduce",
    });
    const page = await context.newPage();
    const cdp = await context.newCDPSession(page);
    await cdp.send("Network.enable");
    await cdp.send("Network.setCacheDisabled", { cacheDisabled: true });
    const requests = new Map();
    const errors = [];
    page.on("pageerror", (e) => errors.push(e.message));
    cdp.on("Network.responseReceived", ({ requestId, response }) =>
      requests.set(requestId, {
        path: new URL(response.url).pathname,
        origin: new URL(response.url).origin,
        status: response.status,
        mime: response.mimeType,
        bytes: 0,
      }),
    );
    cdp.on("Network.loadingFinished", ({ requestId, encodedDataLength }) => {
      const request = requests.get(requestId);
      if (request) request.bytes = encodedDataLength;
    });
    const snapshot = () => ({
      requests: requests.size,
      total_transfer_bytes: [...requests.values()].reduce(
        (n, r) => n + r.bytes,
        0,
      ),
      artwork_transfer_bytes: [...requests.values()]
        .filter((r) => r.path.startsWith("/design/"))
        .reduce((n, r) => n + r.bytes, 0),
      artwork_paths: [...requests.values()]
        .filter((r) => r.path.startsWith("/design/"))
        .map((r) => r.path),
    });
    const started = performance.now();
    await page.goto(site);
    await page.getByRole("button", { name: "Sign in", exact: true }).waitFor();
    await page.waitForLoadState("networkidle");
    const signedOut = snapshot();
    await page.getByLabel("Username").fill(credentials.username);
    await page
      .getByLabel("Password", { exact: true })
      .fill(credentials.password);
    const loginAt = performance.now();
    await page.getByRole("button", { name: "Sign in", exact: true }).click();
    await page
      .getByTestId("card-cpi_yoy_2024")
      .filter({ hasText: "%" })
      .waitFor();
    await page.waitForLoadState("networkidle");
    const initial = snapshot();
    const readyMs = performance.now() - loginAt;
    const before = await page
      .locator(".panel-skin, .card-art img")
      .evaluateAll((nodes) =>
        nodes.map((img) => ({
          complete: img.complete && img.naturalWidth > 0,
          loading: img.loading,
          src: new URL(img.currentSrc || img.src).pathname,
          y: img.getBoundingClientRect().y,
        })),
      );
    // Visit every panel, since a single jump to the bottom need not load intervening lazy images.
    for (const panel of await page.locator(".panel").all()) {
      await panel.scrollIntoViewIfNeeded();
      await panel
        .locator(".panel-skin, .card-art img")
        .evaluateAll((nodes) => Promise.all(nodes.map((img) => img.decode())));
    }
    await page.waitForLoadState("networkidle");
    await page.mouse.move(0, 0);
    await page.screenshot({
      path: output + `/${phase}-${name}.png`,
      fullPage: true,
    });
    const full = snapshot();
    const layout = await page.locator(".panel").evaluateAll((nodes) =>
      nodes.map((n) => {
        const r = n.getBoundingClientRect();
        return { width: r.width, height: r.height };
      }),
    );
    assert(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    );
    assert.deepEqual(errors, []);
    runs.push({
      name,
      viewport: { width, height, dpr },
      signed_out: signedOut,
      signed_in_initial: initial,
      after_scroll: full,
      initial_card_images: before,
      login_to_dashboard_ready_ms: readyMs,
      total_measurement_ms: performance.now() - started,
      panel_geometry: layout,
      requests: [...requests.values()],
    });
    await page.getByRole("button", { name: /Sign out/ }).click();
    await page.getByRole("button", { name: "Sign in", exact: true }).waitFor();
    await context.close();
  }
  const report = {
    checked_at: new Date().toISOString(),
    phase,
    browser: browser.version(),
    method:
      "Fresh Chrome contexts, HTTP cache disabled; unthrottled local HTTP preview. CDP encodedDataLength includes response overhead. No production/CDN performance claim.",
    runs,
  };
  await writeFile(
    output + `/${phase}-performance.json`,
    JSON.stringify(report, null, 2) + "\n",
  );
  console.log(
    JSON.stringify(
      runs.map((r) => ({
        name: r.name,
        initial_artwork: r.signed_in_initial.artwork_transfer_bytes,
        full_artwork: r.after_scroll.artwork_transfer_bytes,
        total: r.after_scroll.total_transfer_bytes,
        initial_images: r.initial_card_images,
      })),
    ),
  );
} finally {
  await browser.close();
}
