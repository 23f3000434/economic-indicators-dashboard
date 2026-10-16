import assert from "node:assert/strict";
import { readdir, readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
const directory = fileURLToPath(new URL("../frontend/dist/", import.meta.url));
async function files(path) {
  const entries = await readdir(path, { withFileTypes: true });
  return (
    await Promise.all(
      entries.map((e) =>
        e.isDirectory() ? files(path + e.name + "/") : [path + e.name],
      ),
    )
  ).flat();
}
const paths = await files(directory);
assert(
  !paths.some(
    (p) =>
      /\.(sqlite3?|db|env|py|gz)$/.test(p) ||
      /\/(tests|fixtures|data)\//.test(p),
  ),
);
const scripts = await Promise.all(
  paths.filter((p) => p.endsWith(".js")).map((p) => readFile(p, "utf8")),
);
for (const script of scripts) {
  assert(!script.includes("/__test/"));
  assert(!script.includes("Test-only password"));
  assert(!script.includes("localhost:8001"));
  assert(!script.includes("localhost:8010"));
}
const policy = await readFile(directory + "_headers", "utf8");
const config = JSON.parse(
  await readFile(directory + "build-config.json", "utf8"),
);
assert(scripts.some((s) => s.includes(config.api_origin)));
assert(policy.includes("connect-src 'self' " + config.api_origin + ";"));
assert(
  paths
    .filter((p) => p.endsWith(".webp"))
    .every((p) => /-[0-9]+-[a-f0-9]{12}\.webp$/.test(p)),
);
assert(
  paths
    .filter((p) => p.endsWith(".svg") && p.includes("/design/"))
    .every((p) => /-layout-(?:[12]x|mobile)-[a-f0-9]{12}\.svg$/.test(p)),
);
console.log(
  "Production frontend contains no fixture/control data or local API URLs; configured origin/CSP/hash assets verified.",
);
