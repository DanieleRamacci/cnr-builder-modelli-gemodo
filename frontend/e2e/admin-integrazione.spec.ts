import { test, expect, request as playwrightRequest, type APIRequestContext } from '@playwright/test';

/**
 * Real end-to-end admin flow (007 tasks.md T014, spec.md User Story 4, quickstart.md
 * Scenario 1): create an integration, configure it against a real discovery
 * endpoint, verify it, see the CONNESSO outcome - all through the real UI against a
 * real backend, not a mocked one.
 *
 * Requires a running stack (infra/local/compose.yaml: postgres + backend, or the
 * equivalent started manually) reachable at GEMODO_FRONTEND_BASE_URL (default
 * http://localhost:4200, proxied to the backend) and a Keycloak instance reachable
 * at E2E_KEYCLOAK_URL (default http://localhost:8081/realms/gemodo-local, the
 * offline realm at infra/local/keycloak/realm-gemodo.local.json) with its admin
 * REST API enabled - the test provisions its own throwaway admin user via that API
 * rather than depending on one existing beforehand, the same "own its fixtures"
 * discipline as the backend's Testcontainers-based tests.
 *
 * Also requires a real discovery HTTP endpoint that the backend's egress allowlist
 * (GEMODO_INTEGRAZIONI_ALLOWLIST[_PRIVATO]) approves, reachable at
 * E2E_DISCOVERY_URL (default http://127.0.0.1:9100/discovery) and returning a
 * valid BANDO_CONCORSO discovery fragment.
 */

const KEYCLOAK_URL = process.env['E2E_KEYCLOAK_URL'] ?? 'http://localhost:8081/realms/gemodo-local';
const KEYCLOAK_ADMIN_USERNAME = process.env['E2E_KEYCLOAK_ADMIN_USERNAME'] ?? 'admin';
const KEYCLOAK_ADMIN_PASSWORD = process.env['E2E_KEYCLOAK_ADMIN_PASSWORD'] ?? 'admin';
const DISCOVERY_URL = process.env['E2E_DISCOVERY_URL'] ?? 'http://127.0.0.1:9100/discovery';

function realmBaseUrl(): { serverUrl: string; realm: string } {
  const marker = '/realms/';
  const index = KEYCLOAK_URL.indexOf(marker);
  return { serverUrl: KEYCLOAK_URL.slice(0, index), realm: KEYCLOAK_URL.slice(index + marker.length) };
}

let adminContext: APIRequestContext;
let testUsername: string;
let testPassword: string;
let userId: string | undefined;

test.beforeAll(async () => {
  const { serverUrl, realm } = realmBaseUrl();
  adminContext = await playwrightRequest.newContext();
  const tokenResponse = await adminContext.post(`${serverUrl}/realms/master/protocol/openid-connect/token`, {
    form: { client_id: 'admin-cli', username: KEYCLOAK_ADMIN_USERNAME, password: KEYCLOAK_ADMIN_PASSWORD, grant_type: 'password' },
  });
  expect(tokenResponse.ok(), 'Keycloak admin login failed - is the realm reachable and admin-cli enabled?').toBeTruthy();
  const { access_token: adminToken } = await tokenResponse.json();
  const authHeader = { Authorization: `Bearer ${adminToken}` };

  testUsername = `e2e-admin-${Date.now()}`;
  testPassword = 'e2e-test-password-1';
  const createResponse = await adminContext.post(`${serverUrl}/admin/realms/${realm}/users`, {
    headers: authHeader,
    data: {
      username: testUsername,
      enabled: true,
      emailVerified: true,
      firstName: 'E2E',
      lastName: 'Admin',
      email: `${testUsername}@example.test`,
      credentials: [{ type: 'password', value: testPassword, temporary: false }],
    },
  });
  expect(createResponse.status()).toBe(201);

  const usersResponse = await adminContext.get(`${serverUrl}/admin/realms/${realm}/users?username=${testUsername}`, { headers: authHeader });
  const [user] = await usersResponse.json();
  userId = user.id;

  const clientsResponse = await adminContext.get(`${serverUrl}/admin/realms/${realm}/clients?clientId=gemodo-backend`, { headers: authHeader });
  const [client] = await clientsResponse.json();

  const roleResponse = await adminContext.get(`${serverUrl}/admin/realms/${realm}/clients/${client.id}/roles/GEMODO_ADMIN`, { headers: authHeader });
  const role = await roleResponse.json();

  const assignResponse = await adminContext.post(`${serverUrl}/admin/realms/${realm}/users/${userId}/role-mappings/clients/${client.id}`, {
    headers: authHeader,
    data: [role],
  });
  expect(assignResponse.status()).toBe(204);
});

test.afterAll(async () => {
  if (!userId) {
    return;
  }
  const { serverUrl, realm } = realmBaseUrl();
  const tokenResponse = await adminContext.post(`${serverUrl}/realms/master/protocol/openid-connect/token`, {
    form: { client_id: 'admin-cli', username: KEYCLOAK_ADMIN_USERNAME, password: KEYCLOAK_ADMIN_PASSWORD, grant_type: 'password' },
  });
  const { access_token: adminToken } = await tokenResponse.json();
  await adminContext.delete(`${serverUrl}/admin/realms/${realm}/users/${userId}`, { headers: { Authorization: `Bearer ${adminToken}` } });
  await adminContext.dispose();
});

test('admin creates, configures and verifies an integration end-to-end', async ({ page }) => {
  const codice = `E2E_${Date.now()}`;

  await page.goto('/');
  await page.fill('#username', testUsername);
  await page.fill('#password', testPassword);
  await Promise.all([page.waitForURL('**/', { timeout: 15000 }), page.click('#kc-login')]);

  // The "no auto-seeding" acceptance criterion (spec.md FR-021, quickstart.md
  // Scenario 1) is a fresh-database property already proven for real by the
  // backend's own test (test_create_starts_disconnected_and_rejects_duplicate_code);
  // this e2e run does not own an isolated database, so it only asserts on its own
  // codice, never on global emptiness.
  await page.click('text=Configurazione');
  await page.waitForURL('**/configurazione');
  await expect(page.locator('body')).not.toContainText(codice);

  await page.click('text=Nuova integrazione');
  await page.waitForURL('**/configurazione/nuova');
  await page.fill('#codice', codice);
  await page.fill('#nome', 'Integrazione e2e');
  await page.fill('#codiceContesto', 'geban');
  await page.click('button[type=submit]');
  await page.waitForURL(/\/configurazione\/[0-9a-f-]{36}$/, { timeout: 10000 });
  await expect(page.locator('body')).toContainText('Non verificato');

  await page.fill('#url', DISCOVERY_URL);
  await page.click('button:has-text("Salva configurazione")');
  await expect(page.locator('#url')).toHaveValue(DISCOVERY_URL);

  await page.click('button:has-text("Verifica")');
  await expect(page.locator('body')).toContainText('Connesso', { timeout: 10000 });
});
