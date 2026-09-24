import { test, expect } from '@playwright/test';
import { ISSUER } from './support/keycloak';

// Verifica che il setup Playwright funzioni contro un `ng serve` reale.
// Non esiste alcuna pagina anonima: `onLoad: 'login-required'` (keycloak.providers.ts)
// redirige subito all'identity provider, quindi lo smoke test verifica proprio
// quel redirect. Gli scenari reali sono in admin-integrazione.spec.ts e
// builder-lifecycle.spec.ts (quickstart.md della spec 007).
test('the shell requires authentication before rendering anything', async ({ page }) => {
  // Senza stub il dev server servirebbe il runtime-config del deployment, che
  // punta al SSO CNR: il test finirebbe su un issuer che qui non c'e'.
  await page.route('**/runtime-config.json', (route) =>
    route.fulfill({
      json: { keycloakIssuerUrl: ISSUER, keycloakClientId: 'gemodo-frontend', externalDocsUrl: '' },
    }),
  );
  await page.goto('/');
  await page.waitForURL(/\/protocol\/openid-connect\/auth/);
  await expect(page.locator('#kc-login')).toBeVisible();
});
