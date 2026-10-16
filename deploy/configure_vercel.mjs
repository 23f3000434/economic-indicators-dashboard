// Generate reviewable public routing configuration after the API URL is known.
import { writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { configuration, headers } from './build_frontend.mjs';

export function vercelConfiguration(env) {
  const config = configuration(env);
  if (!config.proxy) throw new Error('Free provider URLs require explicit auth proxy mode.');
  const csp = headers(config.api).split('\n').find((line) => line.trim().startsWith('Content-Security-Policy:')).trim().slice('Content-Security-Policy: '.length);
  return {
    $schema: 'https://openapi.vercel.sh/vercel.json',
    buildCommand: 'node deploy/build_frontend.mjs',
    installCommand: 'npm ci --prefix frontend',
    outputDirectory: 'frontend/dist',
    rewrites: [{ source: '/api/v1/auth/:path*', destination: config.api + '/api/v1/auth/:path*' }],
    headers: [
      { source: '/(.*)', headers: [
        { key: 'Content-Security-Policy', value: csp },
        { key: 'X-Content-Type-Options', value: 'nosniff' },
        { key: 'Referrer-Policy', value: 'no-referrer' },
        { key: 'X-Frame-Options', value: 'DENY' },
        { key: 'Strict-Transport-Security', value: 'max-age=31536000' },
        { key: 'Permissions-Policy', value: 'camera=(), microphone=(), geolocation=()' },
      ] },
      { source: '/api/v1/auth/:path*', headers: [{ key: 'Cache-Control', value: 'no-store' }] },
      { source: '/assets/:path*', headers: [{ key: 'Cache-Control', value: 'public, max-age=31536000, immutable' }] },
      { source: '/design/:path*', headers: [{ key: 'Cache-Control', value: 'public, max-age=31536000, immutable' }] },
    ],
  };
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  await writeFile(new URL('../vercel.json', import.meta.url), JSON.stringify(vercelConfiguration(process.env), null, 2) + '\n', { flag: 'wx' });
  console.log('Created vercel.json with public origins only; review and commit before deploying.');
}
