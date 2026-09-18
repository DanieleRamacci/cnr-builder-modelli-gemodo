import { test, expect } from '@playwright/test';

// Proves the Playwright setup itself works end-to-end against a real `ng serve`.
// The real scenario tests (admin registers an integration, manager creates a test
// model - see specs/007-frontend-builder-consultazione/quickstart.md) land with
// User Story 4/5 in tasks.md, once there is something real to test.
test('the shell loads', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('h1')).toContainText('GEMODO');
});
