import { defineConfig, devices } from '@playwright/test';

/**
 * Real-browser e2e against the real backend + mock-geban started via
 * infra/local/compose.yaml (specs/007-frontend-builder-consultazione/quickstart.md).
 * Never point this at a mocked backend - that defeats the point of these tests.
 */
export default defineConfig({
  testDir: './e2e',
  // Il realm locale dichiara solo `http://localhost:4200`: il setup registra
  // l'origine effettiva della suite fra i redirect URI e la toglie alla fine.
  globalSetup: './e2e/support/global-setup.ts',
  globalTeardown: './e2e/support/global-teardown.ts',
  // Serie, non parallelo: questi test condividono un realm Keycloak e un
  // database. In parallelo si pestano i piedi sul client `gemodo-frontend`
  // (redirect URI aggiunti e ripristinati a vicenda) e sui vincoli di
  // unicita' del contesto `geban`.
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: 'list',
  use: {
    baseURL: process.env['GEMODO_FRONTEND_BASE_URL'] ?? 'http://localhost:4200',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
});
