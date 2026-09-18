import { test, expect, request, type APIRequestContext } from '@playwright/test';

// Isolated local Keycloak only: this fixture emulates ACE claims per throwaway user.
const issuer = 'http://localhost:8081/realms/gemodo-local';
const realmAdmin = 'http://localhost:8081/admin/realms/gemodo-local';
let admin: APIRequestContext;
let userId: string;
let clientId: string;
let mapperId: string;
let previousClient: Record<string, unknown>;
let previousProfile: { attributes: Record<string, unknown>[] };
const username = `lifecycle-${Date.now()}`;
const password = 'local-lifecycle-test-1';

test.beforeAll(async () => {
  const auth = await request.newContext();
  const response = await auth.post(
    'http://localhost:8081/realms/master/protocol/openid-connect/token',
    {
      form: {
        client_id: 'admin-cli',
        grant_type: 'password',
        username: 'admin',
        password: 'admin',
      },
    },
  );
  expect(response.ok()).toBeTruthy();
  const token = (await response.json()).access_token;
  await auth.dispose();
  admin = await request.newContext({ extraHTTPHeaders: { Authorization: `Bearer ${token}` } });
  previousProfile = await (await admin.get(`${realmAdmin}/users/profile`)).json();
  expect(
    (
      await admin.put(`${realmAdmin}/users/profile`, {
        data: {
          ...previousProfile,
          attributes: [
            ...previousProfile.attributes,
            {
              name: 'test_ace_contexts',
              displayName: 'Test ACE contexts',
              permissions: { view: ['admin'], edit: ['admin'] },
              multivalued: false,
            },
          ],
        },
      })
    ).ok(),
  ).toBeTruthy();
  const clients = await (await admin.get(`${realmAdmin}/clients?clientId=gemodo-frontend`)).json();
  clientId = clients[0].id;
  previousClient = await (await admin.get(`${realmAdmin}/clients/${clientId}`)).json();
  expect(
    (
      await admin.put(`${realmAdmin}/clients/${clientId}`, {
        data: {
          ...previousClient,
          redirectUris: [
            ...(previousClient['redirectUris'] as string[]),
            'http://127.0.0.1:4202/*',
          ],
          webOrigins: [...(previousClient['webOrigins'] as string[]), 'http://127.0.0.1:4202'],
        },
      })
    ).ok(),
  ).toBeTruthy();
  const mapper = await admin.post(`${realmAdmin}/clients/${clientId}/protocol-mappers/models`, {
    data: {
      name: username,
      protocol: 'openid-connect',
      protocolMapper: 'oidc-usermodel-attribute-mapper',
      config: {
        'user.attribute': 'test_ace_contexts',
        'claim.name': 'contexts',
        'jsonType.label': 'JSON',
        'access.token.claim': 'true',
        'id.token.claim': 'false',
        'userinfo.token.claim': 'false',
        multivalued: 'false',
      },
    },
  });
  expect(mapper.status()).toBe(201);
  mapperId = mapper.headers()['location'].split('/').pop()!;
  const created = await admin.post(`${realmAdmin}/users`, {
    data: {
      username,
      enabled: true,
      emailVerified: true,
      firstName: 'Demo',
      lastName: 'Manager',
      email: `${username}@example.test`,
      attributes: {
        test_ace_contexts: [JSON.stringify({ geban: { roles: ['ROLE_MANAGER#geban'] } })],
      },
      credentials: [{ type: 'password', value: password, temporary: false }],
    },
  });
  expect(created.status()).toBe(201);
  userId = created.headers()['location'].split('/').pop()!;
  const user = await (await admin.get(`${realmAdmin}/users/${userId}`)).json();
  expect(user.attributes?.test_ace_contexts).toHaveLength(1);
  const backend = (
    await (await admin.get(`${realmAdmin}/clients?clientId=gemodo-backend`)).json()
  )[0];
  const role = await (
    await admin.get(`${realmAdmin}/clients/${backend.id}/roles/GEMODO_ADMIN`)
  ).json();
  expect(
    (
      await admin.post(`${realmAdmin}/users/${userId}/role-mappings/clients/${backend.id}`, {
        data: [role],
      })
    ).ok(),
  ).toBeTruthy();
});

test.afterAll(async () => {
  if (!admin) return;
  if (userId) await admin.delete(`${realmAdmin}/users/${userId}`);
  if (mapperId)
    await admin.delete(`${realmAdmin}/clients/${clientId}/protocol-mappers/models/${mapperId}`);
  if (previousClient)
    await admin.put(`${realmAdmin}/clients/${clientId}`, { data: previousClient });
  if (previousProfile) await admin.put(`${realmAdmin}/users/profile`, { data: previousProfile });
  await admin.dispose();
});

test('ACE manager creates a draft and publishes from the context list', async ({
  page,
}, testInfo) => {
  await page.route('**/runtime-config.json', (route) =>
    route.fulfill({
      json: {
        keycloakIssuerUrl: issuer,
        keycloakClientId: 'gemodo-frontend',
        externalDocsUrl: '',
      },
    }),
  );
  const errors: string[] = [];
  page.on('pageerror', (e) => errors.push(e.message));
  await page.goto('/');
  await page.locator('#username').fill(username);
  await page.locator('#password').fill(password);
  await page.locator('#kc-login').click();
  await page.getByRole('link', { name: 'Integrazione servizi', exact: true }).last().click();
  await page.getByRole('link', { name: 'Nuova integrazione' }).click();
  await page.locator('#codice').fill(`LIFECYCLE_${Date.now()}`);
  await page.locator('#nome').fill('Discovery lifecycle');
  await page.locator('#codiceContesto').fill('geban');
  await page.locator('button[type=submit]').click();
  await page.locator('#url').fill('http://127.0.0.1:9100/discovery');
  await page.getByRole('button', { name: 'Salva configurazione' }).click();
  await page.getByRole('button', { name: 'Verifica', exact: true }).click();
  await expect(page.getByText('Connesso', { exact: true })).toBeVisible();
  const sourceId = new URL(page.url()).pathname.split('/').pop()!;
  await page.getByRole('link', { name: 'Contesti', exact: true }).click();
  await expect(page.getByRole('button', { name: 'geban', exact: true })).toBeVisible();
  await page.locator(`a[href^="/builder/${sourceId}"]`).click();
  await page.locator('#tipo').selectOption('BANDO_CONCORSO');
  await page.getByRole('button', { name: 'DEMO - Tempo determinato', exact: true }).click();
  await page.getByRole('button', { name: 'DEMO - Ricercatore', exact: true }).click();
  const modelName = `Modello lifecycle ${Date.now()}`;
  await page.locator('#codice').fill(`QA_${Date.now()}`);
  await page.locator('#nome').fill(modelName);
  await page.getByRole('button', { name: 'Crea modello in bozza' }).click();
  await expect(page.getByRole('status')).toContainText('BOZZA');
  await page.getByRole('link', { name: 'Torna ai modelli' }).click();
  const row = page.getByRole('row').filter({ hasText: modelName });
  for (const action of ['Invia in revisione', 'Approva', 'Pubblica']) {
    await row.getByRole('button', { name: action, exact: true }).click();
    await expect(page.getByRole('dialog')).toBeVisible();
    await page.getByRole('button', { name: 'Conferma', exact: true }).click();
  }
  await expect(row).toContainText('PUBBLICATO');
  await expect(row).toContainText('ID API:');
  await page.screenshot({ path: testInfo.outputPath('contesti-desktop.png'), fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: testInfo.outputPath('contesti-mobile.png'), fullPage: true });
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),
  ).toBeTruthy();
  expect(errors).toEqual([]);
});
