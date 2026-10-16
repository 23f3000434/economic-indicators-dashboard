// Vercel Hobby build entry. Public origins are compiled here; no server secrets.
import { spawnSync } from "node:child_process";
import { writeFile, readFile, rm } from "node:fs/promises";
import { fileURLToPath } from "node:url";

export function configuration(env) {
  const api = new URL(env.VITE_API_BASE_URL || "");
  const frontend = new URL(env.FRONTEND_ORIGIN || "");
  const domain = env.COOKIE_SITE_DOMAIN || "";
  const proxy = env.VITE_AUTH_SAME_ORIGIN_PROXY === "true";
  for (const url of [api, frontend]) {
    if (
      url.protocol !== "https:" ||
      url.username ||
      url.password ||
      url.pathname !== "/" ||
      url.search ||
      url.hash ||
      url.port ||
      (!proxy && (!domain.includes(".") || !url.hostname.endsWith("." + domain)))
    )
      throw new Error(
        "Build requires exact separate HTTPS origins, and either explicit auth proxy mode or shared COOKIE_SITE_DOMAIN; no paths, ports or credentials.",
      );
  }
  if (api.hostname === frontend.hostname)
    throw new Error("Use separate frontend/API HTTPS subdomains.");
  return { api: api.origin, frontend: frontend.origin, proxy };
}

export function headers(api) {
  return `/*
  Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self'; font-src 'self'; connect-src 'self' ${api}; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'
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
  if (process.versions.node !== expectedNode && !(process.env.VERCEL === "1" && process.versions.node.split(".")[0] === "22"))
    throw new Error(`Deployment build requires Node ${expectedNode}.`);
  const config = configuration(process.env);
  if (process.env.VERCEL === '1' && config.proxy) {
    const routing = JSON.parse(await readFile(new URL('../vercel.json', import.meta.url), 'utf8'));
    const auth = routing.rewrites?.find((r) => r.source === '/api/v1/auth/:path*');
    if (auth?.destination !== config.api + '/api/v1/auth/:path*')
      throw new Error('Auth rewrite must target the compiled API origin. Generate/review vercel.json first.');
  }
  const root = fileURLToPath(new URL("..", import.meta.url));
  const run = (args) => {
    const result = spawnSync("npm", args, {
      cwd: root,
      stdio: "inherit",
      env: {
        ...process.env,
        VITE_API_BASE_URL: config.api,
        VITE_AUTH_SAME_ORIGIN_PROXY: String(config.proxy),
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
      auth_origin: config.proxy ? config.frontend : config.api,
      node_version: process.versions.node,
    }) + "\n",
  );
  const manifest = JSON.parse(
    await readFile(root + "/frontend/public/design/assets.json", "utf8"),
  );
  console.log(
    `Prepared frontend build for ${config.frontend}; ${manifest.assets.length} original artwork sources.`,
  );
}
if (process.argv[1] === fileURLToPath(import.meta.url)) await build();
