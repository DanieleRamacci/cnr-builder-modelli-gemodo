# Quickstart: Frontend Builder E Consultazione (MVP ADR 0002)

Scenario end-to-end che prova che l'MVP funziona per davvero: un admin
registra e verifica un'integrazione contro un servizio discovery reale
(`mock-geban`), poi un manager naviga la struttura scoperta e crea un
modello di test in BOZZA - lo stesso flusso descritto dall'utente come
obiettivo di questo incremento.

## Prerequisiti

- Docker in esecuzione.
- `infra/local/compose.yaml` con almeno i servizi minimi di default
  (`postgres`, `backend`, `frontend`, `discovery-mock`) - vedi
  `infra/local/README.md` per l'avvio.
- Migrazioni Alembic applicate (`alembic upgrade head` dentro il servizio
  `backend`, o all'avvio se gia' automatizzato dal compose).
- Un utente/token Keycloak con ruolo `GEMODO_ADMIN` per lo scenario admin, e
  un token con `contexts.<contesto>.roles` che mappi a
  `GEMODO_MODELLI_GESTORE` nel contesto scelto per lo scenario manager
  (vedi `infra/local/integration-profiles.local.yaml`
  per i mapping reali gia' configurati, es. `ROLE_MANAGER#geban`).

## Setup

```bash
cd infra/local
docker compose up -d postgres backend frontend discovery-mock
# verifica che mock-geban esponga un endpoint discovery raggiungibile dal
# backend: http://discovery-mock/discovery
```

Apri `http://localhost:4200`.

Per il discovery locale configurare l'origine `http://discovery-mock:80`
in `GEMODO_INTEGRAZIONI_ALLOWLIST_PRIVATO` prima di avviare il backend.
Il servizio `discovery-mock` serve dati demo conformi al contratto ad
albero completo, non la proposta PER_NODI. Il runner `mock-geban` e' distinto.
Per il collaudo sul server seguire [frontend-server-test.md](../../docs/frontend-server-test.md).

## Scenario 1 - Admin registra e verifica un'integrazione

1. Accedi come utente `GEMODO_ADMIN`.
2. Nella schermata integrazioni, la tabella e' vuota al primo avvio (nessun
   seed - FR-021, coerente con `test_create_starts_disconnected_and_rejects_
   duplicate_code`).
3. Crea una nuova integrazione: codice, nome, `codice_contesto` (es.
   `geban`). **Atteso**: appare in lista con stato "Non verificato"
   (`DEFINITO`), nessun URL configurato.
4. Configura l'URL discovery di `mock-geban` (deve rientrare
   nell'allowlist di deployment - vedi `GEMODO_INTEGRAZIONI_ALLOWLIST`/
   `_PRIVATO` nel compose locale). **Atteso**: un URL non in allowlist mostra
   `422 DESTINAZIONE_NON_APPROVATA` in modo comprensibile, non un errore
   generico.
5. Avvia la verifica. **Atteso**: dopo la chiamata (sincrona, puo' richiedere
   fino al `timeout_ms` configurato) lo stato passa a "Connesso" con
   data/versione contratto visibili, oppure a "Errore" con i motivi
   sanificati se `mock-geban` non risponde nella forma attesa.

## Scenario 2 - Manager naviga e crea un modello di test

1. Accedi come utente con ruolo GESTORE nel contesto dell'integrazione appena
   connessa.
2. Nella schermata builder, l'integrazione connessa e autorizzata per il
   proprio contesto e' visibile in lista (e **solo** quella - vedi
   `test_manager_sees_only_connected_integrations_authorized_in_their_
   context` e `test_multicontext_token_does_not_leak_permission_across_
   contexts`).
3. Naviga l'albero (tipologia → profilo → campi, o qualunque forma
   restituita) fino a una foglia.
4. Scegli lingua e, se disponibile, un livello professionale oppure "Tutti i
   livelli". Codice, nome e variante non sono campi editabili. **Atteso**:
   risposta `201` con codice/nome generati e modello distinto per lingua e
   livello; la versione `BOZZA` conserva tutti i campi della foglia.
5. Prosegui da Swagger (`/docs/builder-modelli`, una volta chiuso il gap
   Foundational descritto in `research.md`) per versione/pubblicazione, poi
   `/docs/generazione-documenti` per generare e scaricare un PDF di test -
   la stessa prova end-to-end gia' fatta a livello API in
   `backend/tests/builder/test_builder_flow_api.py::
   test_flusso_completo_creazione_pubblicazione_e_generazione_documento`,
   ora raggiungibile a partire dall'interfaccia invece che solo da Swagger.

## Esito atteso

### Incremento Contesti e pubblicazione (verificato 2026-09-18)

1. Aprire Contesti con un token ACE avente ROLE_MANAGER#geban.
2. Selezionare la tab geban: la lista include bozze e versioni pubblicate;
   Crea modello usa le integrazioni connesse del contesto.
3. Creare un modello dal flusso discovery corrente e tornare ai modelli.
4. Sulla versione BOZZA, scegliere Invia in revisione e confermare.
5. Scegliere Approva e confermare, poi Pubblica e confermare.
6. Verificare stato PUBBLICATO e ID API della versione, utilizzabile come
   modello_versione_id nelle API documenti. Generazione PDF resta via API.

Questo incremento sostituisce il passo Swagger per le transizioni dello
Scenario 2; editor completo resta fuori dall'implementazione corrente.
Esito: 297 test backend non-e2e, 42 test frontend e Playwright lifecycle reale
passati; build produzione/lint passati, screenshot desktop/mobile controllati.
Review indipendente non superata: reviewer Claude non autenticato.

Il test `frontend/e2e/builder-lifecycle.spec.ts` usa soltanto il realm locale
gemodo-local su localhost:8081, un utente temporaneo e un mapper di attributo
JSON che emula contexts ACE. Assegna solo GEMODO_ADMIN per predisporre
l'integrazione: gestione modelli deriva esclusivamente da ROLE_MANAGER#geban.
Non modifica il realm CNR. Il backend deve usare lo stesso issuer e approvare
http://127.0.0.1:9100 per discovery. Frontend su 127.0.0.1:4202, proxy al backend.

```bash
cd frontend
GEMODO_FRONTEND_BASE_URL=http://127.0.0.1:4202 npx playwright test e2e/builder-lifecycle.spec.ts
```

Entrambi gli scenari devono completarsi senza mai richiedere un intervento
diretto sul database o una chiamata Swagger per i passi coperti da questo
MVP (creazione/verifica integrazione, navigazione, creazione modello) - solo
i passi esplicitamente fuori scope (versione/pubblicazione/generazione)
restano su Swagger fino a un incremento futuro.

## Verifica riallineamento lingua/livello (2026-09-21)

- Il catalogo senza filtro `lingua` restituisce tutte le edizioni pubblicate
  che condividono categorizzazione e livello; `lingua=IT|EN` restringe il
  risultato.
- Non esiste `famiglia_modello_id`: "Crea edizione collegata" precompila
  integrazione, tipo, percorso e livello e crea un nuovo modello autonomo.
- `POST /documenti/valida` e `POST /documenti/genera` non accettano piu'
  `bando_inglese`; una chiamata usa una sola `modello_versione_id` e produce
  un solo documento.

Verifiche eseguite:

```text
backend non-E2E: 306 passed, 12 deselected
backend E2E mock: 12 passed, 306 deselected
frontend unit: 43 passed
frontend lint: passato
frontend build produzione: passato
git diff --check: passato
```

Resta da ripetere il lifecycle Playwright reale per chiudere T062 e il gate
indipendente rimane rinviato su indicazione dell'utente.
