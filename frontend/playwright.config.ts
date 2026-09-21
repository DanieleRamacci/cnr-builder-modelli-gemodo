import { defineConfig, devices } from '@playwright/test';

/**
 * Real-browser e2e against the real backend + mock-geban started via
 * infra/local/compose.yaml (specs/007-frontend-builder-consultazione/quickstart.md).
 * Never point this at a mocked backend - that defeats the point of these tests.
 */
export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  retries: 0,
  reporter: 'list',
  use: {
    baseURL: process.env['GEMODO_FRONTEND_BASE_URL'] ?? 'http://localhost:4200',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
});
