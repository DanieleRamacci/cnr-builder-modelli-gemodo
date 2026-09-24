import { expect, request, type APIRequestContext, type Page } from '@playwright/test';

/**
 * Utente usa-e-getta sul Keycloak locale, con claim ACE emulati.
 *
 * Vale **solo** contro il realm isolato `gemodo-local` su localhost:8081: crea
 * un utente, un mapper di attributo che emula il claim `contexts` e allarga i
 * redirect URI del client. Niente di tutto questo tocca il realm CNR.
 *
 * Il contesto DEVE essere fra quelli mappati in
 * `infra/local/integration-profiles.local.yaml` (`ROLE_MANAGER#geban` ->
 * permessi GEMODO, FR-018): un codice arbitrario non concede alcun permesso.
 */
export const ISSUER = 'http://localhost:8081/realms/gemodo-local';
const REALM_ADMIN = 'http://localhost:8081/admin/realms/gemodo-local';

export type UtenteUsaEGetta = {
  username: string;
  password: string;
  /** Rimette il realm com'era: utente, mapper, client e profilo. */
  rimuovi: () => Promise<void>;
};

export async function creaUtenteUsaEGetta(opzioni: {
  /** Prefisso del nome utente, per riconoscere chi ha lasciato residui. */
  prefisso: string;
  contesto: string;
}): Promise<UtenteUsaEGetta> {
  const username = `${opzioni.prefisso}-${Date.now()}`;
  const password = `local-${opzioni.prefisso}-test-1`;
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
  const admin = await request.newContext({
    extraHTTPHeaders: { Authorization: `Bearer ${token}` },
  });

  const previousProfile: { attributes: Record<string, unknown>[] } = await (
    await admin.get(`${REALM_ADMIN}/users/profile`)
  ).json();
  expect(
    (
      await admin.put(`${REALM_ADMIN}/users/profile`, {
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

  const clients = await (await admin.get(`${REALM_ADMIN}/clients?clientId=gemodo-frontend`)).json();
  const clientId = clients[0].id;

  const mapper = await admin.post(`${REALM_ADMIN}/clients/${clientId}/protocol-mappers/models`, {
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
  const mapperId = mapper.headers()['location'].split('/').pop()!;

  const created = await admin.post(`${REALM_ADMIN}/users`, {
    data: {
      username,
      enabled: true,
      emailVerified: true,
      firstName: 'Demo',
      lastName: 'Manager',
      email: `${username}@example.test`,
      attributes: {
        test_ace_contexts: [
          JSON.stringify({ [opzioni.contesto]: { roles: [`ROLE_MANAGER#${opzioni.contesto}`] } }),
        ],
      },
      credentials: [{ type: 'password', value: password, temporary: false }],
    },
  });
  expect(created.status()).toBe(201);
  const userId = created.headers()['location'].split('/').pop()!;
  const user = await (await admin.get(`${REALM_ADMIN}/users/${userId}`)).json();
  expect(user.attributes?.test_ace_contexts).toHaveLength(1);

  // GEMODO_ADMIN serve solo a predisporre l'integrazione: la gestione dei
  // modelli deriva esclusivamente da ROLE_MANAGER sul contesto.
  const backend = (
    await (await admin.get(`${REALM_ADMIN}/clients?clientId=gemodo-backend`)).json()
  )[0];
  const role = await (
    await admin.get(`${REALM_ADMIN}/clients/${backend.id}/roles/GEMODO_ADMIN`)
  ).json();
  expect(
    (
      await admin.post(`${REALM_ADMIN}/users/${userId}/role-mappings/clients/${backend.id}`, {
        data: [role],
      })
    ).ok(),
  ).toBeTruthy();

  return {
    username,
    password,
    rimuovi: async () => {
      await admin.delete(`${REALM_ADMIN}/users/${userId}`);
      await admin.delete(`${REALM_ADMIN}/clients/${clientId}/protocol-mappers/models/${mapperId}`);
      await admin.put(`${REALM_ADMIN}/users/profile`, { data: previousProfile });
      await admin.dispose();
    },
  };
}

/**
 * Login reale sul Keycloak locale.
 *
 * `runtime-config.json` del dev server punta al SSO CNR: qui viene sostituito
 * per la sola durata del test, altrimenti il browser finirebbe sull'issuer
 * sbagliato e non troverebbe mai l'utente appena creato.
 */
export async function accedi(page: Page, utente: UtenteUsaEGetta): Promise<void> {
  await page.route('**/runtime-config.json', (route) =>
    route.fulfill({
      json: { keycloakIssuerUrl: ISSUER, keycloakClientId: 'gemodo-frontend', externalDocsUrl: '' },
    }),
  );
  await page.goto('/');
  await page.locator('#username').fill(utente.username);
  await page.locator('#password').fill(utente.password);
  await page.locator('#kc-login').click();
}

/**
 * Gli elementi il cui bordo destro esce dalla pagina.
 *
 * Non solo "scrolla / non scrolla": se sborda dice quale elemento, altrimenti
 * la diagnosi tocca a chi legge il fallimento a freddo.
 */
export async function bordiSforati(page: Page): Promise<string[]> {
  return page.evaluate(() => {
    const limite = document.documentElement.clientWidth;
    return [...document.querySelectorAll('body *')]
      .filter((el) => el.getBoundingClientRect().right > limite + 1)
      .map((el) => `${el.tagName.toLowerCase()}.${el.className}`.trim())
      .slice(0, 6);
  });
}

/**
 * Token di amministrazione del realm locale.
 *
 * Esportato perche' serve anche fuori dai test, nel setup globale.
 */
export async function contestoAdmin(): Promise<APIRequestContext> {
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
  if (!response.ok()) throw new Error(`Keycloak locale non raggiungibile su ${ISSUER}`);
  const token = (await response.json()).access_token;
  await auth.dispose();
  return request.newContext({ extraHTTPHeaders: { Authorization: `Bearer ${token}` } });
}

/**
 * Registra (o toglie) l'origine da cui gira la suite fra i redirect URI del
 * client.
 *
 * Il realm ne dichiara uno solo, `http://localhost:4200`: qualunque altra
 * porta - e `127.0.0.1` al posto di `localhost`, che per Keycloak e' un'altra
 * origine - darebbe "Invalid parameter: redirect_uri" prima ancora della
 * pagina di login. Vale per tutta la suite, non per un singolo test, quindi
 * sta nel setup globale.
 */
export async function registraOrigine(origine: string, attiva: boolean): Promise<void> {
  const admin = await contestoAdmin();
  const clients = await (await admin.get(`${REALM_ADMIN}/clients?clientId=gemodo-frontend`)).json();
  const client = await (await admin.get(`${REALM_ADMIN}/clients/${clients[0].id}`)).json();
  const redirect = new Set<string>(client.redirectUris ?? []);
  const origini = new Set<string>(client.webOrigins ?? []);
  if (attiva) {
    redirect.add(`${origine}/*`);
    origini.add(origine);
  } else {
    redirect.delete(`${origine}/*`);
    origini.delete(origine);
  }
  await admin.put(`${REALM_ADMIN}/clients/${clients[0].id}`, {
    data: { ...client, redirectUris: [...redirect], webOrigins: [...origini] },
  });
  await admin.dispose();
}

export type { APIRequestContext };
