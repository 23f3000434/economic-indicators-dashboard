import assert from "node:assert/strict";
import { configuration, headers } from "./build_frontend.mjs";
import { vercelConfiguration } from "./configure_vercel.mjs";
const valid = {
  VITE_API_BASE_URL: "https://api.example.org",
  FRONTEND_ORIGIN: "https://dashboard.example.org",
  COOKIE_SITE_DOMAIN: "example.org",
};
assert.equal(configuration(valid).api, "https://api.example.org");
for (const VITE_API_BASE_URL of [
  "",
  "http://localhost:8010",
  "https://api.example.org/path",
  "https://evil.org",
  "https://dashboard.example.org",
  "https://api.example.org:8443",
  "https://user:secret@api.example.org",
]) {
  assert.throws(() => configuration({ ...valid, VITE_API_BASE_URL }));
}
const policy = headers(configuration(valid).api);
assert(policy.includes("connect-src 'self' https://api.example.org;"));
assert(!policy.includes("script-src 'self' 'unsafe-inline'"));
assert(!policy.includes("localhost") && !policy.includes("connect-src *"));
console.log("Frontend deployment origin/CSP checks passed (8 configurations).");

const provider = configuration({ VITE_API_BASE_URL: 'https://economic-api.onrender.com', FRONTEND_ORIGIN: 'https://economic-dashboard.vercel.app', VITE_AUTH_SAME_ORIGIN_PROXY: 'true' });
assert(provider.proxy && provider.api.endsWith('.onrender.com'));
assert.throws(() => configuration({ VITE_API_BASE_URL: 'https://economic-api.onrender.com', FRONTEND_ORIGIN: 'https://economic-dashboard.vercel.app' }));
const routes = vercelConfiguration({ VITE_API_BASE_URL: provider.api, FRONTEND_ORIGIN: provider.frontend, VITE_AUTH_SAME_ORIGIN_PROXY: 'true' });
assert.deepEqual(routes.rewrites, [{ source: '/api/v1/auth/:path*', destination: provider.api + '/api/v1/auth/:path*' }]);
assert(routes.headers[0].headers.some((h) => h.key === 'Content-Security-Policy' && h.value.includes("connect-src 'self' " + provider.api + ';')));
