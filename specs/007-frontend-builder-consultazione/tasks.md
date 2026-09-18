# Tasks: Frontend Builder E Consultazione - Primo Incremento (MVP ADR 0002)

**Input**: Design documents from `/specs/007-frontend-builder-consultazione/`
(`plan.md`, `research.md`, `data-model.md`, `quickstart.md`, `spec.md` User Story 4/5)

**Scope**: solo l'MVP confermato dall'ADR 0002 - admin registra/verifica
un'integrazione (User Story 4, FR-021), manager naviga la struttura scoperta e
crea un modello di test (User Story 5, FR-022/FR-023). User Story 1/2/3 di
`spec.md` (editor completo, revisione/pubblicazione da interfaccia,
consultazione generazioni) restano scope futuro, non toccate da questi task.

**Tests**: inclusi deliberatamente (non opzionali per questo progetto - vedi
lo stile gia' usato in tutte le spec precedenti, "scrivere i test per primi,
verificare che falliscano prima dell'implementazione", test reali contro
backend+mock-geban veri, mai mock della logica di dominio).

## Format: `[ID] [P?] [Story] Description`

## Phase 1: Setup

- [x] T038 Correggere DISCOVERY_NON_CONFIGURATA nella creazione: trasmettere
      integrazione_id, risolvere tipo per sorgente/codice e mantenere ownership
      nelle versioni. Verificare conflitto con tipi legacy e contesti non autorizzati.
      CHIUSO 2026-09-18: contratto/tipi frontend aggiornati, creazione scoped
      senza modificare tipi legacy e versioni con ownership persistita.
      295 test backend non-e2e e 38 frontend passati; lint/formato passati.
      Review indipendente resta pendente: adev FAIL per Claude non autenticato
      e cache uv non accessibile nel sandbox del gate. Suite equivalente
      eseguita con permessi di test passata. Deploy Coolify non eseguito.

- [x] T037 Correggere autorizzazione ACE dei client interattivi: derivare
      permessi dai mapping per contesto senza iscrizione nei profili tecnici;
      documentare ADR 0003 e verificare isolamento, ruoli sconosciuti e client tecnici.
      Implementato il 2026-09-18; 33 test common, 292 test backend non-e2e
      e 38 test frontend passati. Review indipendente residua: Claude non
      autenticato (adev FAIL, nessun esito di revisione valido).

**Purpose**: sostituire il placeholder `frontend/package.json` con un vero
progetto Angular, avviabile da `infra/local/compose.yaml`.

- [x] T001 *(2026-09-18)* Sostituire `frontend/package.json` con un vero
      progetto Angular 21.2 (standalone, signals) generato via `ng new`,
      preservando la struttura placeholder gia' presente (`src/app`,
      `src/features/builder`, `src/features/generazioni`, `src/shared`)
      invece di rigenerarla da zero; aggiunto `design-angular-kit` 21.2.0
      con i suoi peer `@ngx-translate/core`/`@ngx-translate/http-loader` e
      `bootstrap-italia` (vedi `research.md` per la correzione sul nome
      pacchetto reale). Verificato con `ng build` reale (successo).
- [x] T002 [P] *(2026-09-18)* Vitest (gia' default Angular 21) per gli unit
      test in `frontend/` - verificato con `ng test --watch=false` reale
      (2 test passati, `app.spec.ts` aggiornato per la nuova shell minimale).
- [x] T003 [P] *(2026-09-18)* Playwright per gli e2e in `frontend/e2e/`,
      puntato di default a `http://localhost:4200`. Verificato per davvero:
      `ng serve` reale in background + `playwright test` contro il server
      vero (non solo config statica) - vedi `e2e/smoke.spec.ts` (test
      placeholder, i veri scenari arrivano con US4/US5).
- [x] T004 [P] *(2026-09-18)* ESLint/Prettier in `frontend/` - `ng add
      @angular-eslint/schematics` si e' rivelato rotto su questo workspace
      (falso positivo di version-mismatch anche con `@21` esplicito, non
      applicava la configurazione); risolto installando `angular-eslint@21`
      + `eslint@10` manualmente e scrivendo `eslint.config.js` a mano.
      Verificato con `eslint .` (0 errori) e `prettier --check` reali dopo
      un `prettier --write` iniziale.
- [x] T005 *(2026-09-18)* Scritto `frontend/Dockerfile` (dev, `node:24-slim`
      + `ng serve --host 0.0.0.0`, coerente con lo stile gia' usato da
      `backend/Dockerfile`) e `.dockerignore`. Verificato per davvero:
      `docker build` + `docker run` reali, app raggiungibile su `:4200` dal
      host.
      **Aggiornamento 2026-09-18 (richiesto dall'utente dopo la domanda "cosa
      posso provare dopo il push")**: trovato un problema reale - il deploy
      Coolify (`docker-compose.coolify.yml`) buildava il servizio `frontend`
      dal `Dockerfile` di *root* (la vecchia pagina statica placeholder
      `deploy/coolify-test/`), completamente scollegato dalla vera app
      Angular. Un push non avrebbe mostrato nulla di nuovo. Risolto: `frontend/
      Dockerfile` e' ora multi-stage con due target espliciti (nessun default,
      entrambi i compose li richiamano esplicitamente) - `dev` (invariato,
      `ng serve`) e `production` (`ng build --configuration production` +
      nginx statico su `:80`, con `scripts/docker-entrypoint-nginx.sh` che
      rigenera `runtime-config.json` dai veri env var del container a
      startup, stesso pattern di T009). `docker-compose.coolify.yml` aggiornato
      per puntare `frontend` a `frontend/Dockerfile` target `production`; la
      vecchia pagina statica spostata in un nuovo servizio `docs` separato
      (non persa - l'utente ha chiesto esplicitamente di spostarla, non
      cancellarla, per darle un dominio proprio in Coolify) con un link
      opzionale mostrato nel footer della shell quando configurato
      (`GEMODO_EXTERNAL_DOCS_URL` -> `runtime-config.json`
      `externalDocsUrl`, vedi `shell.component.ts`).
      **Bug reale trovato e risolto durante la verifica** (non a
      compile-time - solo avviando il container per davvero): `nginx.conf`
      con `proxy_pass http://backend:8000` (hostname statico) fa fallire
      l'avvio di nginx con `host not found in upstream` se `backend` non e'
      ancora risolvibile via DNS al caricamento della configurazione (crash
      totale del container, non solo un errore sulle route proxate) -
      risolto con `resolver 127.0.0.11` (DNS interno Docker) + `proxy_pass`
      su variabile, che forza la risoluzione al momento della richiesta
      invece che una sola volta all'avvio.
      Verificato per davvero, entrambi i target: `docker build`+`docker run`
      reali per `dev` e per `production` (quest'ultimo anche con un Keycloak
      locale reale, confermando via Playwright lo stesso redirect corretto
      gia' visto in T010 - il flusso funziona identico sia in `ng serve` che
      nella build di produzione statica dietro nginx).

**Checkpoint**: `docker compose up -d frontend` in `infra/local/` avvia una
vera app Angular (anche vuota) sulla porta 4200. **Verificato** (build/run
Docker manuale, non ancora attraverso il compose completo - quello richiede
anche `backend`/`postgres` su, rimandato al checkpoint di fine Foundational).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: infrastruttura condivisa da entrambe le user story di questo
incremento (client HTTP tipizzato, autenticazione, shell applicativa).

**⚠️ CRITICAL**: nessun task di User Story 4/5 puo' iniziare prima che questa
fase sia completa.

- [x] T006 *(2026-09-18)* Verificato `specs/002-builder-modelli/contracts/
      builder-modelli-api.openapi.yaml` contro `backend/app/builder/api.py`:
      drift totale, non solo parziale - la 0.2.0 descriveva un CRUD
      tipi-documento/categorie mai implementato cosi' (quello spazio e' ora
      coperto in sola lettura da `integrazioni-api.openapi.yaml`,
      `/builder/integrazioni/*`) e transizioni
      (`bozza-derivata`/`archivia`/`sospendi`) inesistenti, mentre mancavano
      le 6 route reali (`struttura-disponibile`, creazione modello/versione,
      `invia-revisione`/`approva`/`pubblica`). Riscritto interamente (0.3.0),
      scope ridotto a cio' che `integrazioni-api.openapi.yaml` non gia'
      copre. Registrato in `PUBLISHED_CONTRACTS`
      (`backend/app/quality/openapi_docs.py`) e in
      `infra/openapi/README.md`. Verificato per davvero: nuovo
      `backend/tests/builder/test_builder_modelli_contract.py` (validita'
      strutturale incl. `$ref` esterno cross-spec, esempi validati contro i
      propri schema, regressione esplicita sulle route che NON devono
      esistere), piu' `/openapi/builder-modelli.yaml`, `/docs/builder-modelli`,
      `/redoc/builder-modelli` interrogati via `TestClient` reale (200 su
      tutti e tre). Suite completa: 295 passati, 0 falliti.
- [x] T007 [P] *(2026-09-18)* Generati i tipi TypeScript dai 4 contratti
      OpenAPI necessari (`integrazioni`, `configurazione-cataloghi`,
      `builder-discovery`, `builder-modelli`) via `openapi-typescript`,
      script `frontend/scripts/genera-tipi-api.sh` (portabile su bash 3.2 di
      macOS - niente array associativi) + output in
      `frontend/src/shared/api-types/*.d.ts`. Verificato per davvero: il
      `$ref` cross-spec di `builder-modelli-api.openapi.yaml` verso
      `geban-discovery-endpoint.openapi.yaml` (in `010`, non nella stessa
      cartella di `002`) risolto correttamente in `StrutturaTipoDocumento`;
      `tsc --noEmit` pulito sui file generati; `ng build` invariato.
- [x] T008 *(2026-09-18)* Implementato il client HTTP condiviso (wrapper
      sottile su `HttpClient`, non un SDK generato) in
      `frontend/src/shared/api-client.ts`, con mappatura esplicita
      dell'envelope di errore backend (`{codice, messaggio}`) verso `ApiError`
      (`frontend/src/shared/api-error.ts`), senza logica di retry automatico
      sui conflitti ottimistici. **Trovato e risolto un problema reale non
      previsto in `research.md`**: il backend non ha `CORSMiddleware` (nessun
      match nel codice), quindi il browser non puo' chiamare
      `http://localhost:8000` direttamente da `http://localhost:4200` (origini
      diverse). Aggiunto `frontend/proxy.conf.js` (letto da `ng serve` tramite
      `angular.json` `serve.options.proxyConfig`, target da
      `GEMODO_API_BASE_URL`) cosi' il browser parla solo con l'origine del
      dev-server e non serve CORS lato backend; corretto anche il valore di
      `GEMODO_API_BASE_URL` in `infra/local/compose.yaml`
      (era `http://localhost:8000`, sbagliato per la rete Docker interna dove
      gira il proxy - ora `http://backend:8000`). Verificato per davvero: un
      backend fittizio reale su `:8000` raggiunto con successo tramite
      `curl http://localhost:4200/api/v1/test` con `ng serve` + proxy attivi.
      4 unit test Vitest reali (`api-client.spec.ts`, incl. mappatura errore
      409 e fallback su risposta senza envelope) - 6/6 test totali passati.
- [x] T009 [P] *(2026-09-18)* Implementato il modulo di autenticazione
      Keycloak (`keycloak-angular@21` + `keycloak-js`, Authorization Code +
      PKCE `S256`, client id `gemodo-frontend`) in
      `frontend/src/app/auth/` (`keycloak-config.ts` per il parsing di
      `KEYCLOAK_ISSUER_URL`, `keycloak.providers.ts` per `provideKeycloak` +
      `includeBearerTokenInterceptor` limitato a `/^\/api\//`).
      **Problema reale trovato durante l'implementazione, non previsto in
      `research.md`**: l'issuer/client id non possono essere costanti a
      build-time (differiscono per ambiente) ma il builder esbuild di
      Angular NON sostituisce `process.env` a build-time come farebbe Vite
      (verificato con un build di prova: il riferimento resta
      `process.env[...]` nel bundle, che lancerebbe `ReferenceError` in
      browser). Risolto con un pattern di runtime-config standard:
      `public/runtime-config.json` (default committato con gli stessi
      valori di default del backend), rigenerato dai veri env var del
      container a *startup* (non build) da
      `scripts/genera-runtime-config.sh`, richiamato dal `CMD` del
      `Dockerfile` prima di `ng serve`; `main.ts` lo recupera con `fetch`
      prima di chiamare `bootstrapApplication` (`app.config.ts` e' ora una
      funzione `buildAppConfig(runtimeConfig)`, non piu' una costante
      statica).
      **Verificato per davvero, non solo a compile-time**: avviato un
      Keycloak reale standalone (stessa immagine/stesso import di realm di
      `infra/local/compose.yaml` `keycloak-local`, solo su porta 8081 per
      evitare un conflitto locale) con il realm `gemodo-local` gia'
      preparato in questo repo (redirect URI `http://localhost:4200/*` gia'
      registrato). Un browser reale (Playwright, non un mock) che apre
      l'app viene rediretto correttamente alla vera pagina di login
      Keycloak con `client_id=gemodo-frontend`,
      `redirect_uri=http://localhost:4200/`, `response_type=code`,
      `code_challenge_method=S256` e un `code_challenge` presente - prova
      concreta che l'intero flusso Authorization Code + PKCE e' cablato
      correttamente end-to-end. 3 nuovi unit test Vitest
      (`keycloak-config.spec.ts`) - 9/9 test totali passati.
      **Aggiornamento T010**: il login completo (non solo il redirect) e'
      stato poi verificato per davvero - vedi sotto.
      **Aggiornamento 2026-09-18, Coolify**: il backend rifiutava token appena
      emessi con `jwt_validation=ImmatureSignatureError` quando l'orologio tra
      Keycloak/browser/backend aveva uno scarto minimo. Aggiunto
      `KEYCLOAK_JWT_LEEWAY_SECONDS` (default 60) alla validazione PyJWT e ai
      compose, con test mirati su `iat`/`nbf` futuri entro/fuori tolleranza.
- [x] T010 [P] *(2026-09-18)* Implementata la shell applicativa
      (`frontend/src/app/shell/`) con `design-angular-kit` reale
      (`it-header`/`it-navbar`/`it-navbar-item`/`it-footer`, brand "GEMODO",
      link a `/configurazione` e `/builder`), non un placeholder.
      Configurato `provideDesignAngularKit()`, l'import SCSS di
      `bootstrap-italia`, gli asset (icone + i18n) in `angular.json`.
      **Tre problemi reali trovati e risolti durante l'implementazione**:
      (1) il budget di bundle di produzione (1MB) era troppo basso per
      Design Angular Kit + Bootstrap Italia (bundle reale ~2.09MB/439KB
      gzip) - alzato a un budget realistico (warning 1.5MB, errore 3MB);
      (2) `bootstrap-italia` e' CommonJS-only e Vitest (non `ng build`, che
      usa esbuild e non ha problemi) falliva con "Named export non
      trovato" - risolto con `vitest.config.ts` (`test.server.deps.inline`,
      non `optimizeDeps.include` da solo, che NON basta per l'ambiente di
      test); (3) **bug reale di markup**: `it-navbar` richiede il proprio
      contenuto avvolto in un elemento con l'attributo `navItems` (stesso
      pattern di `it-header`), non semplicemente `<it-navbar-item>` come
      figli diretti - senza quel wrapper i link di navigazione compilavano
      senza errori ma non venivano MAI proiettati nel DOM finale
      (`<ul class="navbar-nav"></ul>` vuoto), un bug silenzioso che
      un'ispezione visiva superficiale o un test che verifica solo
      l'assenza di errori console non avrebbe mai trovato.
      **Verificato con un login Keycloak reale e completo, non solo il
      redirect (aggiornamento rispetto a T009)**: creato un utente di test
      reale con ruolo `GEMODO_ADMIN` via API admin di Keycloak sul realm
      locale `gemodo-local`, login end-to-end con Playwright (username/
      password reali compilati nel vero form di Keycloak, submit, redirect
      di ritorno), poi verificato nel DOM risultante: header/footer
      presenti, testo del brand corretto, **link di navigazione con testo
      e `href` corretti** (questo e' il controllo che ha trovato il bug
      del markup sopra - un controllo piu' superficiale sarebbe passato),
      zero errori console, screenshot reale che conferma lo stile
      istituzionale Bootstrap Italia applicato correttamente (non solo CSS
      di default del browser). 9/9 test Vitest passati, `eslint .` pulito
      (corretto anche un problema reale trovato qui: `eslint.config.js` non
      escludeva `dist/`, quindi un lint dopo una build veniva eseguito
      anche sui `.d.ts` di terze parti copiati come asset).

**Checkpoint** (aggiornato): un utente autenticato via Keycloak vede la
shell reale (header/nav/footer Design Angular Kit, non vuota) - **verificato
per davvero con un login end-to-end completo**, non solo a compile-time.
Nessuna chiamata API di dominio ancora cablata a uno schermo (arriva con
User Story 4).

---

## Phase 3: User Story 4 - Registrare e verificare un'integrazione (Priority: P1) 🎯 MVP

**IN CORSO (2026-09-18, ripresa del lavoro di Claude)**: T011-T013 e
T015-T019 hanno codice nel worktree, ma restano da verificare integralmente
contro i requisiti prima della chiusura. Vitest: 25 test passati; lint,
Prettier e TypeScript passati. Build di produzione verificata con successo
fuori dal sandbox (il codice 134 e' riproducibile solo nel sandbox).
T014 e' scritto ma non ancora eseguito: serve uno stack con Keycloak e
discovery HTTP reali. Corretto il contesto di build backend del compose
locale per allinearlo ai COPY del Dockerfile; `docker compose build backend`
verificato con successo. Il servizio `mock-geban`
attuale non espone l'endpoint discovery descritto nel quickstart: questo
prerequisito va completato prima del checkpoint US4 e di T031.

- [x] T033 [US4] *(2026-09-18)* Prerequisito di collaudo emerso alla ripresa: predisporre
      un discovery HTTP reale con dati demo conformi al contratto 0.4.0,
      relativo avvio ripetibile e allowlist locale. Il compose punta a
      `mock-geban/`, che non contiene un Dockerfile e oggi contiene solo
      il runner scenari. Allineare il quickstart alla configurazione
      effettivamente collaudata, prima di eseguire T014/T023/T031.
      Implementato `infra/local/discovery-mock/` con nginx e dati demo;
      avviato con compose e validato via HTTP reale usando `AdapterHTTP`.
      Il servizio sostituisce la definizione non avviabile del runner nel
      compose. I test e2e completi restano da eseguire.

**Checkpoint server di test (2026-09-18)**: immagine frontend target
`production` compilata con successo; 26 test Vitest, lint e Prettier
passati. Corretto il caricamento fallito della pagina configurazione
(errore visibile e Riprova) e impedite azioni concorrenti di salvataggio/
verifica. Istruzioni in `docs/frontend-server-test.md`. Le modifiche sono
locali: deploy possibile dopo pubblicazione sul branch usato da Coolify.
Questo checkpoint non certifica US4: T014 e review indipendente restano
aperti. La review configurata con Claude non parte senza autenticazione.

**Goal**: un admin crea, configura e verifica un'integrazione dall'interfaccia,
senza mai chiamare l'API a mano (`spec.md` User Story 4, FR-021).

**Independent Test**: vedi `quickstart.md` Scenario 1.

### Tests for User Story 4

> Scrivere questi test per primi, verificare che falliscano prima
> dell'implementazione (coerente con lo stile gia' usato per le spec 001/002/010).

- [ ] T011 [P] [US4] Unit test (Vitest) per il componente lista integrazioni:
      stato vuoto al primo avvio, badge di stato per `DEFINITO`/`CONNESSO`/
      `ERRORE`, in `frontend/src/features/configurazione/integrazioni-
      lista.component.spec.ts`
- [ ] T012 [P] [US4] Unit test (Vitest) per il form di creazione: validazione
      lunghezza campi, gestione `409 INTEGRAZIONE_DUPLICATA` come errore di
      form, in `frontend/src/features/configurazione/integrazione-
      crea.component.spec.ts`
- [ ] T013 [P] [US4] Unit test (Vitest) per il form di
      configurazione/verifica: gestione `409 REVISIONE_SUPERATA` (ricarica,
      non sovrascrive), `422 DESTINAZIONE_NON_APPROVATA`, `409
      VERIFICA_IN_CORSO`, esito `CONNESSO`/`ERRORE` con motivi sanificati,
      in `frontend/src/features/configurazione/integrazione-
      configura.component.spec.ts`
- [ ] T014 [US4] Test e2e (Playwright) end-to-end: admin crea
      un'integrazione, la configura verso `mock-geban` reale, la verifica e
      vede lo stato finale corretto (Scenario 1 di `quickstart.md`), in
      `frontend/e2e/admin-integrazione.spec.ts`

### Implementation for User Story 4

- [ ] T015 [P] [US4] `IntegrazioniAdminService` (chiamate tipizzate a
      `/api/v1/configurazione/integrazioni*`, usa T007/T008) in
      `frontend/src/features/configurazione/integrazioni-admin.service.ts`
- [ ] T016 [US4] Componente lista integrazioni (tabella, stato vuoto, badge
      di stato) in
      `frontend/src/features/configurazione/integrazioni-lista.component.ts`
      (dipende da T011, T015)
- [ ] T017 [US4] Componente creazione integrazione (form + validazione) in
      `frontend/src/features/configurazione/integrazione-crea.component.ts`
      (dipende da T012, T015)
- [ ] T018 [US4] Componente configurazione/verifica integrazione (form URL/
      timeout, pulsante verifica con stato disabilitato durante la chiamata,
      visualizzazione esito) in
      `frontend/src/features/configurazione/integrazione-
      configura.component.ts` (dipende da T013, T015)
- [ ] T019 [US4] Instradamento `/configurazione` e voce di navigazione
      visibile solo con ruolo `GEMODO_ADMIN` nel token (abilitazione UI, mai
      autorizzazione - il backend gia' applica `require_admin`), in
      `frontend/src/app/app.routes.ts`

**Checkpoint**: User Story 4 completa e testabile indipendentemente da User
Story 5.

---

## Phase 4: User Story 5 - Creare un modello di test dalla struttura scoperta (Priority: P1)

**Goal**: un manager naviga la struttura live di un'integrazione connessa del
proprio contesto e crea un modello di test in BOZZA (`spec.md` User Story 5,
FR-022/FR-023).

**Independent Test**: vedi `quickstart.md` Scenario 2.

### Tests for User Story 5

- [x] T020 [P] [US5] Unit test (Vitest) per la lista integrazioni manager:
      isolamento multi-contesto riflesso in UI (solo le integrazioni del
      proprio contesto, anche con token multi-contesto - vedi
      `test_multicontext_token_does_not_leak_permission_across_contexts`
      lato backend), in
      `frontend/src/features/builder/integrazioni-manager.component.spec.ts`
- [ ] T021 [P] [US5] Unit test (Vitest) per la navigazione ad albero:
      profondita' variabile, stati caricamento/vuoto/`409
      INTEGRAZIONE_NON_CONNESSA`/errore di trasporto distinti, in
      `frontend/src/features/builder/struttura-albero.component.spec.ts`
- [ ] T022 [P] [US5] Unit test (Vitest) per il form creazione modello:
      selezione percorso -> risoluzione categoria/tipologia, gestione errore
      `400` su percorso ambiguo, in
      `frontend/src/features/builder/modello-crea.component.spec.ts`
- [ ] T023 [US5] Test e2e (Playwright) end-to-end: manager vede solo le
      integrazioni del proprio contesto, naviga fino a una foglia e crea un
      modello che risulta `BOZZA` anche da Swagger (Scenario 2 di
      `quickstart.md`), in `frontend/e2e/manager-crea-modello.spec.ts`

### Implementation for User Story 5

- [ ] T024 [P] [US5] `BuilderManagerService` (chiamate tipizzate a
      `/api/v1/builder/integrazioni*` e `/api/v1/builder/modelli*`, usa
      T007/T008) in
      `frontend/src/features/builder/builder-manager.service.ts`
- [ ] T025 [US5] Componente lista integrazioni manager in
      `frontend/src/features/builder/integrazioni-manager.component.ts`
      (dipende da T020, T024)
- [ ] T026 [US5] Componente navigazione ad albero (profondita' variabile,
      nessuna assunzione di forma fissa) in
      `frontend/src/features/builder/struttura-albero.component.ts`
      (dipende da T021, T024)
- [ ] T027 [US5] Componente creazione modello di test (form, nessun editor
      di campi/sezioni) in
      `frontend/src/features/builder/modello-crea.component.ts` (dipende da
      T022, T024, T026)
- [ ] T028 [US5] Instradamento `/builder` e voce di navigazione visibile solo
      se il token ha un contesto con permesso gestore (abilitazione UI, mai
      autorizzazione - il backend gia' applica `verify_scrittura_su_contesto`),
      in `frontend/src/app/app.routes.ts`

**Checkpoint**: User Story 5 completa e testabile indipendentemente; insieme
a User Story 4, l'MVP ADR 0002 e' completo.

---

## Phase 5: Polish & Cross-Cutting Concerns

- [x] T036 Diagnosi 401 immediatamente dopo login sul server: forzare nuovo
      accesso con prompt login; distinguere rifiuto backend da refresh
      fallito e registrare nei log solo la classe di errore JWT, audience
      non corrispondente o Bearer assente. IN CORSO: 37 test frontend e 16
      test JWT passati, lint/formato/build passati. Diagnosi server ancora
      aperta: risposta ACCESSO_NON_AUTENTICATO e header Bearer presente
      confermati dall'utente. Serve il motivo di rifiuto nei log backend;
      non esclusa rimozione header nel percorso proxy.
      CHIUSO 2026-09-18: causa ImmatureSignatureError identificata e corretta
      con leeway JWT configurabile; log server successivi forniti dall'utente
      confermano GET/PUT/verifica con 200. La nota IN CORSO sopra e' storica.

- [ ] T035 Correzione dal collaudo server: refresh fallito non deve inviare
      richieste con token scaduto; lista distingue errore da vuoto e mostra
      record senza URL come Da completare. Login esplicito mantiene il
      percorso dell'integrazione salvata. IN CORSO: 36 test frontend passati
      e lint passato; verifica finale e collaudo server residui. Confermato
      nel backend il commit prima della configurazione dell'endpoint.

- [x] T034 Shell/profilo e home richiesti nel collaudo server: nome e icona
      utente, token su richiesta, logout, accesso admin/manager e messaggio
      di mancata autorizzazione. Verificati con test home/profilo e build
      Angular; il collaudo grafico e il login reale sul server restano in T031.

**IN CORSO US5**: selettore di tutti i contesti del token, lista integrazioni
autorizzata dal backend, tipi live, navigazione ricorsiva e creazione modello
con versione BOZZA. I task T020-T028 restano aperti fino ai test previsti.
Verifica di questo incremento: 32 test Vitest passati, lint, Prettier e
build produzione passati. Il flusso creazione e' verificato a livello HTTP
unitario, non ancora end-to-end contro lo stack reale. Gate adev FAIL:
reviewer Claude non autenticato e sei test di discovery bloccati dal
sandbox sull'apertura dei socket. Server dev disponibile su porta 4201.

- [ ] T029 [P] Aggiornare `README.md` e `docs/project-map.md` con le
      istruzioni reali di avvio del frontend (oggi descrivono solo il
      placeholder)
- [ ] T030 [P] Aggiornare `frontend/README.md` (se assente, crearlo) con
      setup locale, variabili d'ambiente (`GEMODO_API_BASE_URL`,
      `KEYCLOAK_ISSUER_URL`, `KEYCLOAK_CLIENT_ID`) e comandi di test
- [ ] T031 Eseguire l'intera suite (Vitest + Playwright e2e) contro
      `infra/local/compose.yaml` reale (non solo unitaria, coerente con la
      pratica gia' seguita per le altre spec) e registrare l'esito in
      `quickstart.md`
- [x] T032 Rivedere `docs/decision-register.yaml` per collegare eventuali
      decisioni aperte specifiche di questo incremento (se emerse durante
      l'implementazione - nessuna nota gia' oggi)
      Registrata DEC-007-ACCESSO-ACE-CONTESTI e ADR 0003, 2026-09-18.

## Residui dopo correzione ACE (2026-09-18)

Le altre spec non sono dichiarate complete da questa correzione condivisa.
006 ha gia' i task implementativi chiusi; ADR 0003 aggiorna il contratto
di accesso utenti. 002/010 restano owner dei rispettivi residui funzionali.
Il gate indipendente resta pendente per tutte le spec interessate: reviewer
Claude non autenticato. Il comando regressione interno ad adev ha inoltre
fallito per accesso sandbox alla cache uv; la stessa suite eseguita con
permessi di test ha passato 292 test. Nessun PASS del gate viene dichiarato.

T014/T023/T031: SOSPESI per questo incremento di sicurezza, collaudo browser
su stack reale ancora necessario. T011-T013/T015-T019 e T021-T030/T035:
stato precedente conservato; i test presenti passano, ma le verifiche
integrali dei singoli requisiti e dei workflow non sono sostituite dai test ACE.
US5 non e' completata dalla sola correzione di accesso.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: nessuna dipendenza, primo passo.
- **Foundational (Phase 2)**: dipende da Phase 1; blocca Phase 3 e Phase 4
  per intero (nessuno schermo puo' chiamare un'API senza client tipizzato e
  autenticazione).
- **US4 (Phase 3)** e **US5 (Phase 4)**: entrambe dipendono solo da Phase 2,
  sono indipendenti fra loro (US5 richiede un'integrazione gia' `CONNESSO`
  per essere provata end-to-end, ma non richiede che gli *schermi* di US4
  esistano - puo' essere provata con un'integrazione creata via Swagger o
  fixture, come gia' fa `integrazione_connessa` lato backend). Possono
  procedere in parallelo se piu' persone lavorano sul frontend.
- **Polish (Phase 5)**: dipende da Phase 3 e Phase 4 complete.

### Parallel Opportunities

- T002-T004 possono girare in parallelo dopo T001.
- T007, T009, T010 possono girare in parallelo dopo T006 (T007 aspetta
  comunque T006 per il contratto `builder-modelli`).
- T011-T013 possono girare in parallelo (file diversi, nessuna dipendenza).
- T015 puo' girare mentre T011-T014 vengono scritti (task diversi,
  implementazione vs test).
- T020-T022 possono girare in parallelo.
- US4 e US5 possono procedere interamente in parallelo dopo Phase 2.

## Implementation Strategy

1. Completare Setup + Foundational (Phase 1-2) - nessuno schermo reale
   ancora, ma `docker compose up frontend` funziona e l'auth e' vera.
2. Completare User Story 4 (Phase 3) - primo schermo utilizzabile per
   davvero: un admin puo' registrare e verificare un'integrazione contro
   `mock-geban`. **Questo e' il primo momento in cui l'utente puo' provare
   qualcosa sull'interfaccia**, come richiesto.
3. Completare User Story 5 (Phase 4) - secondo schermo: un manager crea un
   modello di test navigando la struttura scoperta.
4. Completare Polish (Phase 5).
5. **Non incluso in questo incremento**: editor visuale, composizione
   sezioni (FR-011), revisione/pubblicazione da interfaccia (User Story 2),
   consultazione generazioni (User Story 3) - tutti scope futuro, da
   pianificare come incrementi successivi di questa stessa spec quando
   servira'.
