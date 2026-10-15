import { defineConfig } from '@playwright/test';
import { fileURLToPath } from 'node:url';

export default defineConfig({
  testDir: './tests',
  fullyParallel: false,
  workers: 1,
  timeout: 35000,
  expect: { timeout: 8000 },
  use: {
    baseURL: 'http://localhost:5174',
    reducedMotion: 'reduce',
    viewport: { width: 1214, height: 2159 },
    launchOptions: {
      executablePath:
        process.env.CHROME_PATH ||
        (process.platform === 'darwin'
          ? '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
          : undefined),
    },
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure',
  },
  reporter: [['list'], ['html', { open: 'never' }]],
  webServer: [
    {
      command:
        'PYTHONPATH=backend .venv/bin/python -m uvicorn tests.browser_server:app --host localhost --port 8001 --no-access-log',
      cwd: fileURLToPath(new URL('..', import.meta.url)),
      url: 'http://localhost:8001/healthz',
      reuseExistingServer: false,
    },
    {
      command: process.env.E2E_PREVIEW
        ? 'npm run preview -- --port 5174 --strictPort --outDir ../.verification/browser-dist'
        : 'npm run dev -- --port 5174 --strictPort',
      url: 'http://localhost:5174',
      reuseExistingServer: false,
      env: { VITE_API_BASE_URL: 'http://localhost:8001' },
    },
  ],
});
