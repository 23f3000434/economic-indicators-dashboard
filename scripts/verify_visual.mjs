// Normal-application visual evidence. No reference data enters production code.
import { readFile, writeFile, mkdir } from "node:fs/promises";
import { createRequire } from "node:module";
import assert from "node:assert/strict";
import { fileURLToPath } from "node:url";
const root = fileURLToPath(new URL("..", import.meta.url));
const require = createRequire(
  new URL("../frontend/package.json", import.meta.url),
);
const { chromium } = require("@playwright/test");
const svg = await readFile(
  process.argv[2] ||
    "/Users/ashu/Downloads/Economic Indicator Assignment/Economic Indicator Assignment.svg",
);
const credentials = JSON.parse(
  await readFile(root + "/.verification/local-access.json", "utf8"),
);
const output = root + "/.verification/completion/visual";
await mkdir(output, { recursive: true });
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
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto(process.env.LOCAL_FRONTEND_URL || "http://localhost:5175");
  await page.getByLabel("Username").fill(credentials.username);
  await page.getByLabel("Password", { exact: true }).fill(credentials.password);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await page.getByTestId("card-cpi_yoy_2024").waitFor();
  await page.waitForLoadState("networkidle");
  await page.evaluate(() => document.fonts.ready);
  for (const image of await page.locator(".panel-skin").all()) {
    await image.evaluate((n) => n.decode());
  }
  const cdp = await context.newCDPSession(page);
  await cdp.send("DOM.enable");
  await cdp.send("CSS.enable");
  const doc = await cdp.send("DOM.getDocument");
  const fonts = {};
  for (const selector of [
    "#gdp-title",
    ".kpi-value",
    ".kpi-label",
    ".ticker-item",
    ".ticker-item .manrope",
  ]) {
    const { nodeId } = await cdp.send("DOM.querySelector", {
      nodeId: doc.root.nodeId,
      selector,
    });
    fonts[selector] = (
      await cdp.send("CSS.getPlatformFontsForNode", { nodeId })
    ).fonts;
  }
  const geometry = await page.locator(".panel").evaluateAll((ns) =>
    ns.map((n) => {
      const r = n.getBoundingClientRect();
      const h = n.querySelector("h2");
      const cs = getComputedStyle(h);
      return {
        id: h.id,
        x: r.x,
        y: r.y,
        width: r.width,
        height: r.height,
        heading: {
          font: cs.fontFamily,
          weight: cs.fontWeight,
          size: cs.fontSize,
        },
      };
    }),
  );
  const factor = 1214 / 1248;
  for (const [i, g] of geometry.entries()) {
    assert(Math.abs(g.x - (i % 2 ? 636 : 30) * factor) < 0.1);
    assert(Math.abs(g.y - (162 + 568 * Math.floor(i / 2)) * factor) < 0.1);
    assert(Math.abs(g.width - (i % 2 ? 583 : 582) * factor) < 0.1);
    assert(Math.abs(g.height - 544 * factor) < 0.1);
  }
  assert(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  );
  await page.mouse.move(0, 0);
  await page.screenshot({
    path: output + "/application-1214x2159.png",
    fullPage: false,
  });
  const reference = await context.newPage();
  await reference.route("http://reference.invalid/assignment.svg", (r) =>
    r.fulfill({ body: svg, contentType: "image/svg+xml" }),
  );
  await reference.setContent(
    '<style>html,body{margin:0;background:#080808}img{display:block;width:1214px;height:auto}</style><img alt="Supplied design" src="http://reference.invalid/assignment.svg">',
  );
  await reference.locator("img").evaluate((n) => n.decode());
  await reference.screenshot({ path: output + "/reference-1214x2159.png" });
  await reference.close();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.waitForLoadState("networkidle");
  for (const p of await page.locator(".panel").all()) {
    await p.scrollIntoViewIfNeeded();
    await p
      .locator(".card-art img")
      .evaluateAll((ns) => Promise.all(ns.map((n) => n.decode())));
  }
  await page.evaluate(() => scrollTo(0, 0));
  assert(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  );
  await page.screenshot({
    path: output + "/application-mobile.png",
    fullPage: true,
  });
  await page
    .locator(".inflation-panel")
    .screenshot({ path: output + "/application-mobile-inflation.png" });
  assert.deepEqual(errors, []);
  await writeFile(
    output + "/geometry-fonts.json",
    JSON.stringify(
      {
        checked_at: new Date().toISOString(),
        viewport: { width: 1214, height: 2159 },
        mapping: {
          visual_frame: [1248, 2193],
          factor,
          canvas_height: 2193 * factor,
        },
        geometry,
        actual_platform_fonts: fonts,
        browser_errors: errors,
      },
      null,
      2,
    ) + "\n",
  );
  console.log(
    JSON.stringify({
      result: "passed",
      panels: geometry.length,
      actual_fonts: fonts,
    }),
  );
} finally {
  await browser.close();
}
