# GEMODO frontend

Interfaccia Angular 21 con [Design Angular Kit](https://github.com/italia/design-angular-kit)
e Bootstrap Italia. Spec di riferimento: `specs/007-frontend-builder-consultazione/`.
Le schermate presenti in `design_handoff_modellario/` seguono quel design
(FR-026 della spec 007).

## Aree implementate

- **Configurazione** (ruolo `GEMODO_ADMIN`): lista, creazione, configurazione e
  verifica delle integrazioni; struttura dei tipi documento.
- **Contesti / Builder** (ruolo gestore modelli): scelta contesto e
  integrazione, navigazione dell'albero discovery, creazione del modello in
  BOZZA con lingua e livello, edizione inglese derivata.
- Non ancora implementati: editor completo, revisione/pubblicazione da
  interfaccia, consultazione generazioni.

## Setup locale

```bash
cd frontend
npm ci
npm start          # dev server su http://localhost:4200, proxy /api verso il backend
```

Il proxy (`proxy.conf.js`) inoltra `/api`, `/openapi`, `/docs`, `/redoc` al backend.

## Variabili d'ambiente

| Variabile | Uso | Default |
| --- | --- | --- |
| `GEMODO_API_BASE_URL` | Backend di destinazione del proxy di sviluppo | `http://localhost:8000` |
| `KEYCLOAK_ISSUER_URL` | Issuer OIDC scritto in `runtime-config.json` all'avvio del container | `https://sso.test.si.cnr.it/auth/realms/cnr` |
| `KEYCLOAK_CLIENT_ID` | Client pubblico Keycloak (Authorization Code + PKCE) | `gemodo-frontend` |

Nel compose Coolify il client si imposta con `KEYCLOAK_FRONTEND_CLIENT_ID`.
`runtime-config.json` viene rigenerato all'avvio del container da
`scripts/genera-runtime-config.sh`: non contiene segreti.

## Test e qualita'

```bash
npm test -- --no-watch     # unit test Vitest
npm run lint               # eslint
npm run format:check       # prettier
npm run build              # build di produzione
npm run test:e2e:install   # una tantum: browser Playwright
npm run test:e2e           # e2e reali, richiedono lo stack locale
```

I test e2e non usano backend simulati: richiedono lo stack di
`infra/local/compose.yaml` (backend, Keycloak locale, discovery mock) e
leggono `GEMODO_FRONTEND_BASE_URL` (default `http://localhost:4200`),
`E2E_KEYCLOAK_URL` ed `E2E_DISCOVERY_URL`. Vedi `quickstart.md` della spec 007.

## Tipi API

I tipi TypeScript dei contratti si rigenerano con `scripts/genera-tipi-api.sh`.

## Deploy

Vedi `docs/frontend-server-test.md` e `docker-compose.coolify.yml`
(`frontend/Dockerfile`, target `production`, porta interna 80).
