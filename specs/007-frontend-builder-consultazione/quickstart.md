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
- Non esiste `famiglia_modello_id`: "Crea versione inglese" crea un modello
  autonomo con riferimento diretto al padre e clona l'ultima versione in BOZZA.
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
## Verifica catalogo multi-sorgente (2026-09-21)

Riprodotto il caso con due record `TipoDocumento` attivi aventi codice
`BANDO_CONCORSO` e contesto `geban`, uno dei quali privo di modelli. La ricerca
catalogo aggrega ora tutte le sorgenti attive autorizzate invece di fallire con
`SORGENTE_AMBIGUA`.

```text
GET /api/v1/catalogo/modelli?tipo_documento=BANDO_CONCORSO&profilo=COLLABORATORE_TECNICO_ER&codice_tipologia=TD
HTTP 200
modelli[0].modello_versione_id = 1
```

Verifiche eseguite:

```text
pytest tests/catalog/test_catalogo_modelli_api.py tests/catalog/test_campi_richiesti_api.py
5 passed

pytest tests/catalog/test_catalog_service_integration.py::test_catalog_service_aggregates_duplicate_active_document_types
1 passed (PostgreSQL reale)
```

## Fallback livello ed edizione inglese derivata (2026-09-21)

Scenario verificato su PostgreSQL temporaneo reale:

1. creato e pubblicato `BANDO_CONCORSO / TD / RICERCATORE / tutti / IT`;
2. creata dalla dashboard/API l'edizione derivata EN, con struttura e campi
   clonati in versione BOZZA, poi pubblicata separatamente;
3. creato e pubblicato `BANDO_CONCORSO / TD / RICERCATORE / VI / IT`;
4. verificato match esatto per VI e fallback al generico per V.

Creazione edizione inglese:

```http
POST /api/v1/builder/modelli/{modelloIdItaliano}/edizioni-derivate
Content-Type: application/json

{"lingua":"EN"}
```

La risposta `201` contiene un modello e una versione propri:

```json
{
  "id": "<uuid-modello-inglese>",
  "public_id": 24,
  "lingua": "EN",
  "livello_professionale": null,
  "derivato_da_modello_id": "<uuid-modello-italiano>",
  "versioni": [{"public_id": 24, "numero_versione": 1, "stato": "BOZZA"}]
}
```

Richiesta esatta, quando esiste CTER livello VI:

```http
GET /api/v1/catalogo/modelli?tipo_documento=BANDO_CONCORSO&profilo=RICERCATORE&codice_tipologia=TD&livello_professionale=VI
```

```json
{
  "fallback_applicato": false,
  "livello_richiesto": "VI",
  "livello_risolto": "VI",
  "modelli": [{"lingua": "IT", "livello_professionale": "VI", "edizioni_derivate": []}]
}
```

Richiesta livello V senza modello specifico:

```http
GET /api/v1/catalogo/modelli?tipo_documento=BANDO_CONCORSO&profilo=RICERCATORE&codice_tipologia=TD&livello_professionale=V
```

```json
{
  "fallback_applicato": true,
  "livello_richiesto": "V",
  "livello_risolto": null,
  "modelli": [
    {
      "lingua": "IT",
      "livello_professionale": null,
      "edizioni_derivate": [
        {"lingua": "EN", "livello_professionale": null, "modello_versione_id": 24}
      ]
    }
  ]
}
```

Ogni `modello_versione_id` resta generabile con una chiamata distinta a
`POST /api/v1/documenti/genera`. Il filtro `lingua=EN` restituisce l'edizione
EN al primo livello, senza il padre IT, e non applica fallback di lingua.

Verifiche eseguite:

```text
backend non-E2E: 314 passed, 12 E2E esclusi
contratti e documentazione API: 47 passed
frontend unit: 52 passed
frontend lint: passato
frontend build produzione: passato (warning di budget/CommonJS preesistenti)
```

## Riallineamento spunte e unicita' tipo documento (2026-09-21)

Verifiche eseguite:

```text
backend non-E2E: 317 passed, 12 E2E esclusi (Postgres reale via Testcontainers)
frontend unit: 52 passed (13 file)
frontend lint: passato
discovery live GEBAN (geban-service.test.si.cnr.it): CatalogoDiscovery valida BANDO_CONCORSO, 10 tipologie
Playwright su stack reale: NON eseguito (T014/T023/T031 restano aperti)
```

FR-024: creando un modello con `integrazione_id`, il builder riusa il tipo
documento non inattivo dello stesso `(codice_contesto, codice)`, lo associa se
non ha integrazione, risponde 409 `TIPO_DOCUMENTO_ALTRA_INTEGRAZIONE` se e' di
un'altra integrazione. `POST /configurazione/tipi-documento` risponde 409
`TIPO_DOCUMENTO_ALREADY_EXISTS` per lo stesso duplicato.

## Playwright su stack reale eseguito (2026-09-21) - T014/T023/T031

Prima esecuzione reale dei test e2e di questo incremento. Stack usato (non i
container di sviluppo gia' attivi sulla macchina, per non interferire):

```text
postgres  container usa-e-getta su 127.0.0.1:55432 (migrazioni alembic head)
keycloak  container usa-e-getta su localhost:8081, realm gemodo-local importato
          da infra/local/keycloak/realm-gemodo.local.json
backend   uvicorn locale su 127.0.0.1:8003, KEYCLOAK_ISSUER_URL sul realm locale,
          GEMODO_INTEGRAZIONI_ALLOWLIST=http://127.0.0.1:9100
discovery infra/local discovery-mock su 127.0.0.1:9100
frontend  ng serve su 4201 con GEMODO_API_BASE_URL=http://127.0.0.1:8003
```

Comando:

```bash
GEMODO_FRONTEND_BASE_URL=http://localhost:4201 \
E2E_KEYCLOAK_URL=http://localhost:8081/realms/gemodo-local \
E2E_DISCOVERY_URL=http://127.0.0.1:9100/discovery \
npx playwright test
```

Esito:

```text
3 passed
  smoke.spec.ts               the shell requires authentication before rendering anything
  admin-integrazione.spec.ts  admin creates, configures and verifies an integration end-to-end
  builder-lifecycle.spec.ts   ACE manager creates a draft and publishes from the context list
backend non-E2E: 317 passed, 12 esclusi
frontend unit: 66 passed, lint e build passati
```

Due correzioni necessarie per farli passare:

- `smoke.spec.ts` verificava un `h1` "GEMODO" senza autenticarsi, ma
  `onLoad: 'login-required'` non lascia alcuna pagina anonima: ora verifica il
  redirect all'identity provider.
- `builder-lifecycle.spec.ts` compilava ancora i campi codice/nome del modello,
  rimossi da T055: ora segue le tendine a cascata della schermata 2a e legge il
  nome generato dal backend.

**Il test lifecycle richiede un database pulito per il contesto `geban`**: FR-024
ammette un solo tipo documento non inattivo per `(codice_contesto, codice)`,
quindi una seconda esecuzione sullo stesso database ottiene
`TIPO_DOCUMENTO_ALTRA_INTEGRAZIONE`. Il contesto non puo' essere reso univoco
per esecuzione perche' deve essere fra quelli mappati in
`infra/local/integration-profiles.local.yaml` (FR-018). Usare
`gemodo-reset-database` (T079/T080) prima di rieseguire.
