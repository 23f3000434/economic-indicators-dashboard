import assert from "node:assert/strict";
import { configuration, headers } from "./build_frontend.mjs";
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
assert(policy.includes("connect-src https://api.example.org;"));
assert(!policy.includes("script-src 'self' 'unsafe-inline'"));
assert(!policy.includes("localhost") && !policy.includes("connect-src *"));
console.log("Frontend deployment origin/CSP checks passed (8 configurations).");
