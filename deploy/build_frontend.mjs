// Cloudflare Pages build entry. Vite values are compiled here, never runtime-injected.
import { spawnSync } from "node:child_process";
import { writeFile, readFile, rm } from "node:fs/promises";
import { fileURLToPath } from "node:url";

export function configuration(env) {
  const api = new URL(env.VITE_API_BASE_URL || "");
  const frontend = new URL(env.FRONTEND_ORIGIN || "");
  const domain = env.COOKIE_SITE_DOMAIN || "";
  for (const url of [api, frontend]) {
    if (
      url.protocol !== "https:" ||
      url.username ||
      url.password ||
      url.pathname !== "/" ||
      url.search ||
      url.hash ||
      url.port ||
      !domain.includes(".") ||
      !url.hostname.endsWith("." + domain)
    )
      throw new Error(
        "Build requires exact HTTPS frontend/API subdomains of COOKIE_SITE_DOMAIN, without paths, ports or credentials.",
      );
  }
  if (api.hostname === frontend.hostname)
    throw new Error("Use separate frontend/API HTTPS subdomains.");
  return { api: api.origin, frontend: frontend.origin };
}

export function headers(api) {
  return `/*
  Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self'; font-src 'self'; connect-src ${api}; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'
  X-Content-Type-Options: nosniff
  Referrer-Policy: no-referrer
  X-Frame-Options: DENY
  Strict-Transport-Security: max-age=31536000
  Permissions-Policy: camera=(), microphone=(), geolocation=()
/
  Cache-Control: no-cache
/index.html
  Cache-Control: no-cache
/build-config.json
  Cache-Control: no-cache
/assets/*
  Cache-Control: public, max-age=31536000, immutable
/design/*
  Cache-Control: public, max-age=31536000, immutable
`;
}

export async function build() {
  const expectedNode = (
    await readFile(new URL("../.node-version", import.meta.url), "utf8")
  ).trim();
  if (process.versions.node !== expectedNode)
    throw new Error(`Deployment build requires Node ${expectedNode}.`);
  const config = configuration(process.env);
  const root = fileURLToPath(new URL("..", import.meta.url));
  const run = (args) => {
    const result = spawnSync("npm", args, {
      cwd: root,
      stdio: "inherit",
      env: {
        ...process.env,
        VITE_API_BASE_URL: config.api,
        npm_config_cache: root + "/.verification/npm-cache",
        npm_config_logs_dir: root + "/.verification/npm-logs",
      },
    });
    if (result.status !== 0) throw new Error("Locked frontend build failed.");
  };
  run(["ci", "--prefix", "frontend"]);
  run(["run", "build", "--prefix", "frontend"]);
  await rm(root + "/frontend/dist/design/assets.json"); // engineering provenance stays in Git, outside immutable asset routes
  await rm(root + "/frontend/dist/design/layout.json");
  await writeFile(root + "/frontend/dist/_headers", headers(config.api));
  // Only this safe origin is exposed in build metadata; never copy server environment variables.
  await writeFile(
    root + "/frontend/dist/build-config.json",
    JSON.stringify({
      api_origin: config.api,
      frontend_origin: config.frontend,
    }) + "\n",
  );
  const manifest = JSON.parse(
    await readFile(root + "/frontend/public/design/assets.json", "utf8"),
  );
  console.log(
    `Prepared Pages build for ${config.frontend}; ${manifest.assets.length} original artwork sources.`,
  );
}
if (process.argv[1] === fileURLToPath(import.meta.url)) await build();
