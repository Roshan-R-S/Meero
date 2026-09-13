import { defineConfig, devices } from '@playwright/test';

const port = process.env.E2E_PORT || '5175';
const baseURL = `http://127.0.0.1:${port}`;

export default defineConfig({
  testDir: './tests/e2e',
  // 60 s per test: Vite cold-start module transformation can take 30–50 s on
  // shared CI runners; 30 s caused intermittent first-test timeouts.
  timeout: 60 * 1000,
  // Retry once in CI so a cold-start flake self-heals without masking real
  // failures (a test must fail twice consecutively to be reported as failed).
  retries: process.env.CI ? 1 : 0,
  expect: { timeout: 8000 },
  reporter: [['list'], ['html', { open: 'never' }]],
  webServer: {
    command: `pnpm run dev --host 127.0.0.1 --port ${port}`,
    url: baseURL,
    reuseExistingServer: !process.env.CI,
    timeout: 120 * 1000,
  },
  use: {
    baseURL,
    headless: true,
    viewport: { width: 1280, height: 720 },
    actionTimeout: 0,
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
});
