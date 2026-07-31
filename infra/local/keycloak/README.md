# Keycloak locale/test

Decisione confermata (`SEC-006-001`, spec `006-sicurezza-autorizzazioni-audit`, 2026-07-29):
sviluppo e test puntano di default al **realm Keycloak CNR di test reale**
(`sso.test.si.cnr.it`, realm `cnr`), configurato tramite variabili d'ambiente:

- `KEYCLOAK_ISSUER_URL` (default `https://sso.test.si.cnr.it/auth/realms/cnr`)
- `KEYCLOAK_AUDIENCE` (default `gemodo-backend`)
- `KEYCLOAK_CLIENT_ID` / `KEYCLOAK_CLIENT_SECRET` per i client tecnici
- `KEYCLOAK_FRONTEND_CLIENT_ID` per il client pubblico del frontend

Nessun nome client o segreto e' hardcodato: la configurazione resta swappabile verso la
produzione senza cambi di modello applicativo (vedi FR-031).

## Client di test creati nel realm `cnr`

Vedi `docs/decision-register.yaml` (decisione sui client Keycloak GEMODO/GEBAN) per lo stato
aggiornato. Baseline attuale:

- `gemodo-frontend`: client pubblico SSO per operatori GEMODO (login utente).
- `gemodo-backend`: client confidenziale, audience delle API GEMODO.
- `geban-backend`: client tecnico server-to-server (client credentials) usato da GEBAN per
  chiamare le API operative GEMODO; ruolo applicativo atteso `DOCUMENTI_GENERATORE`.
- `geban-frontend`: placeholder, da verificare se gia' gestito dal team GEBAN.

GEMODO non gestisce password o segreti dei client: Keycloak resta l'unica sorgente di
identita', autenticazione e ruoli/claim generali (vedi `authorization-boundary.local.yaml`).

## SSO DEV per home e Swagger

La home DEV e Swagger catalogo usano `gemodo-frontend` con Authorization Code + PKCE.
Nel realm CNR di test reale il client pubblico deve includere:

- redirect URI: `https://dev-gemodo.concorsi.cnr.it/*`
- web origin: `https://dev-gemodo.concorsi.cnr.it`
- audience mapper nel token verso `gemodo-backend`

L'utente che prova le API da Swagger deve avere ruoli client su `gemodo-backend` coerenti
con l'endpoint: `DOCUMENTI_VIEWER` per catalogo/campi e `DOCUMENTI_GENERATORE` per
validazione payload. Questi ruoli su utente servono solo per il test interattivo SSO;
il flusso GEBAN operativo resta server-to-server con client tecnico `geban-backend`.

## Fallback offline: Keycloak containerizzato

Per sviluppo senza rete verso `sso.test.si.cnr.it` o per CI isolata, e' disponibile un
Keycloak containerizzato opzionale (`infra/local/compose.yaml`, profilo
`offline-keycloak`), importato dal manifest `realm-gemodo.local.json` in questa cartella.
Questo percorso non e' il default e non introduce un secondo modello applicativo: gli
stessi nomi di client, audience e ruoli restano coerenti tra i due ambienti.
