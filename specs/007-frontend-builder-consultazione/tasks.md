# Tasks: Frontend Builder E Consultazione - Primo Incremento (MVP ADR 0002)

**Input**: Design documents from `/specs/007-frontend-builder-consultazione/`
(`plan.md`, `research.md`, `data-model.md`, `quickstart.md`, `spec.md` User Story 4/5)

**Scope**: solo l'MVP confermato dall'ADR 0002 - admin registra/verifica
un'integrazione (User Story 4, FR-021), manager naviga la struttura scoperta e
crea un modello di test (User Story 5, FR-022/FR-023). User Story 1/2/3 di
`spec.md` (editor completo, revisione/pubblicazione da interfaccia,
consultazione generazioni) restano scope futuro, non toccate da questi task.

**Vincolo grafico (FR-026)**: ogni task che implementa o modifica una schermata
presente in `design_handoff_modellario/screens.json` MUST seguirne struttura,
flusso e stile (design token del suo README, Titillium Web/Roboto Mono), adattati
ad Angular + design-angular-kit. Nessun layout alternativo dove esiste la
schermata; dove non esiste valgono solo i design token.

**Tests**: inclusi deliberatamente (non opzionali per questo progetto - vedi
lo stile gia' usato in tutte le spec precedenti, "scrivere i test per primi,
verificare che falliscano prima dell'implementazione", test reali contro
backend+mock-geban veri, mai mock della logica di dominio).

## Format: `[ID] [P?] [Story] Description`

## Incremento Contesti e backlog collegato

T039/T040 e T044 avviati 2026-09-18 su richiesta dell'utente per rendere
disponibili elenco e revisione/approvazione/pubblicazione dalla UI.
T041-T043 restano backlog distinto.

- [x] T044 [US2] Azioni di revisione/approvazione/pubblicazione sulla versione,
      conferma e gestione conflitti, public_id per prova API PDF; backend
      valida parent modello/versione e serializza transizioni. Verificare
      isolamento per contesto e flusso lista -> pubblicazione reale.
      Implementato 2026-09-18: conferma nativa, azioni per stato e public_id;
      controllo parent e lock backend. Playwright contro Keycloak/Postgres/
      backend/discovery reali passa creazione -> BOZZA -> PUBBLICATO.

- [x] T039 [US1] Pianificare e definire il contratto per Contesti: elenco
      modelli comprese bozze per contesto autorizzato, dati della tabella e
      permessi di lettura/creazione; distinguere integrazioni nello stesso contesto.
- [x] T040 [US1] Sostituire l'accesso Crea modello con Contesti, tab autorizzate,
      tabella modelli e azione Crea modello che riusa il flusso discovery.
      Conservare contesto/sorgente al ritorno e aggiornare lista dopo creazione;
      prevedere stati vuoto/caricamento/errore e test di isolamento backend/UI.
      Verifica 2026-09-18: 297 test backend non-e2e, 42 frontend, lint e build
      produzione passati. Playwright lifecycle reale e screenshot desktop/mobile
      verificati; lista paginata, contesti backend, ritorno con query contesto.
      Gate indipendente FAIL: Claude non autenticato e cache uv inaccessibile
      nel sandbox del gate; la suite equivalente fuori sandbox passa.
      Feature completa non certificata; T041-T043 e gli altri residui restano aperti.
- [x] T041 [US1] (backend gia' fatto in T053; chiude con T063) Generare codice e nome nel backend dalla categorizzazione
      validata, data e lingua: definire formato, unicita' concorrente e stabilita'.
      Rimuovere input liberi codice/nome/variante; variante derivata da metadati
      configurati o STANDARD, alternative solo controllate. Non usare varianti
      univoche per aggirare i vincoli di pubblicazione. Aggiornare contratti/test.
- [x] T042 [US1] (fatto in T049-T056; chiude con T063) Definire lingua modello persistita e selezione Italiano/IT,
      Inglese/EN con menu, validazione campi/disponibilita' backend. Coordinare le
      modifiche di dominio con 002 senza cambiare di nascosto i vincoli attuali.
- [x] T043 [US1] (fatto in T049-T060; chiude con T063) Pianificare livello professionale opzionale: menu dei valori
      ammessi per profilo e Tutti i livelli; livello scelto incluso nel nome
      e nello scope persistito, assenza copre tutti i livelli del solo profilo.
      Verificare struttura discovery e contratto campi comune prima di consentire
      selezione su nodi intermedi. Generico e specifico sono modelli distinti,
      con nomi rispettivamente senza/con livello e versioni proprie; nessun
      fallback automatico. Includere scope livello nel vincolo di pubblicazione
      per consentire coesistenza senza archiviazione reciproca. Coordinare
      catalogo/generazione con owner 002/001/004.
      Aggiornamento 2026-09-21: implementato da T047-T060 (lingua/livello,
      scope pubblicazione, form). Il punto "nessun fallback automatico" e' superato
      da FR-024 / DEC-007-FALLBACK-LIVELLO-CATALOGO (T082-T086). Si chiude con T063.

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

- [x] T011 [P] [US4] Unit test (Vitest) per il componente lista integrazioni:
      stato vuoto al primo avvio, badge di stato per `DEFINITO`/`CONNESSO`/
      `ERRORE`, in `frontend/src/features/configurazione/integrazioni-
      lista.component.spec.ts`
- [x] T012 [P] [US4] Unit test (Vitest) per il form di creazione: validazione
      lunghezza campi, gestione `409 INTEGRAZIONE_DUPLICATA` come errore di
      form, in `frontend/src/features/configurazione/integrazione-
      crea.component.spec.ts`
- [x] T013 [P] [US4] Unit test (Vitest) per il form di
      configurazione/verifica: gestione `409 REVISIONE_SUPERATA` (ricarica,
      non sovrascrive), `422 DESTINAZIONE_NON_APPROVATA`, `409
      VERIFICA_IN_CORSO`, esito `CONNESSO`/`ERRORE` con motivi sanificati,
      in `frontend/src/features/configurazione/integrazione-
      configura.component.spec.ts`
- [x] T014 (2026-09-21: ESEGUITO su stack reale, 3 e2e verdi - vedi quickstart.md 'Playwright su stack reale eseguito') [US4] Test e2e (Playwright) end-to-end: admin crea
      un'integrazione, la configura verso `mock-geban` reale, la verifica e
      vede lo stato finale corretto (Scenario 1 di `quickstart.md`), in
      `frontend/e2e/admin-integrazione.spec.ts`

### Implementation for User Story 4

- [x] T015 [P] [US4] `IntegrazioniAdminService` (chiamate tipizzate a
      `/api/v1/configurazione/integrazioni*`, usa T007/T008) in
      `frontend/src/features/configurazione/integrazioni-admin.service.ts`
- [x] T016 [US4] Componente lista integrazioni (tabella, stato vuoto, badge
      di stato) in
      `frontend/src/features/configurazione/integrazioni-lista.component.ts`
      (dipende da T011, T015)
- [x] T017 [US4] Componente creazione integrazione (form + validazione) in
      `frontend/src/features/configurazione/integrazione-crea.component.ts`
      (dipende da T012, T015)
- [x] T018 [US4] Componente configurazione/verifica integrazione (form URL/
      timeout, pulsante verifica con stato disabilitato durante la chiamata,
      visualizzazione esito) in
      `frontend/src/features/configurazione/integrazione-
      configura.component.ts` (dipende da T013, T015)
- [x] T019 [US4] Instradamento `/configurazione` e voce di navigazione
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
- [x] T021 [P] [US5] Unit test (Vitest) per la navigazione ad albero:
      profondita' variabile, stati caricamento/vuoto/`409
      INTEGRAZIONE_NON_CONNESSA`/errore di trasporto distinti, in
      `frontend/src/features/builder/struttura-albero.component.spec.ts`
- [x] T022 [P] [US5] Unit test (Vitest) per il form creazione modello:
      selezione percorso -> risoluzione categoria/tipologia, gestione errore
      `400` su percorso ambiguo, in
      `frontend/src/features/builder/modello-crea.component.spec.ts`
- [x] T023 (2026-09-21: ESEGUITO su stack reale, 3 e2e verdi - vedi quickstart.md 'Playwright su stack reale eseguito') [US5] Test e2e (Playwright) end-to-end: manager vede solo le
      integrazioni del proprio contesto, naviga fino a una foglia e crea un
      modello che risulta `BOZZA` anche da Swagger (Scenario 2 di
      `quickstart.md`), in `frontend/e2e/manager-crea-modello.spec.ts`

### Implementation for User Story 5

- [x] T024 [P] [US5] (SUPERATO 2026-09-21: nessun service dedicato, i componenti chiamano `ApiClient` tipizzato direttamente; da estrarre solo se serve a T091/T092) `BuilderManagerService` (chiamate tipizzate a
      `/api/v1/builder/integrazioni*` e `/api/v1/builder/modelli*`, usa
      T007/T008) in
      `frontend/src/features/builder/builder-manager.service.ts`
- [x] T025 [US5] Componente lista integrazioni manager in
      `frontend/src/features/builder/integrazioni-manager.component.ts`
      (dipende da T020, T024)
- [x] T026 [US5] (SUPERATO 2026-09-21: la navigazione ad albero vive dentro `modello-crea.component.ts`; il design 2a a tendine a cascata e' stato consegnato da T092) Componente navigazione ad albero (profondita' variabile,
      nessuna assunzione di forma fissa) in
      `frontend/src/features/builder/struttura-albero.component.ts`
      (dipende da T021, T024)
- [x] T027 [US5] Componente creazione modello di test (form, nessun editor
      di campi/sezioni) in
      `frontend/src/features/builder/modello-crea.component.ts` (dipende da
      T022, T024, T026)
- [x] T028 [US5] Instradamento `/builder` e voce di navigazione visibile solo
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

- [x] T035 (2026-09-21: tutte e tre le parti implementate e coperte da test - `session.interceptor` blocca l'invio con token scaduto, la lista distingue errore da vuoto e mostra `Da completare` senza URL, il login esplicito conserva `/configurazione/<id>`; aggiunto il test mancante su quest'ultima) Correzione dal collaudo server: refresh fallito non deve inviare
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

- [x] T029 [P] Aggiornare `README.md` e `docs/project-map.md` con le
      istruzioni reali di avvio del frontend (oggi descrivono solo il
      placeholder)
- [x] T030 [P] Aggiornare `frontend/README.md` (se assente, crearlo) con
      setup locale, variabili d'ambiente (`GEMODO_API_BASE_URL`,
      `KEYCLOAK_ISSUER_URL`, `KEYCLOAK_CLIENT_ID`) e comandi di test
- [x] T031 (2026-09-21: ESEGUITO su stack reale, 3 e2e verdi - vedi quickstart.md 'Playwright su stack reale eseguito') Eseguire l'intera suite (Vitest + Playwright e2e) contro
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

## Phase 6: User Story 1 - Categorizzare il modello per lingua e livello (Priority: P1)

**Goal**: creare modelli distinti per percorso discovery, lingua e livello
professionale senza duplicare in GEMODO le anagrafiche esterne.

**Independent Test**: dalla stessa foglia CTER il gestore crea CTER/tutti/IT,
CTER/tutti/EN e CTER/VI/IT; i tre modelli hanno codice/nome generati, lo stesso
contratto campi e identificativi distinti.

- [x] T047 [P] [US1] Aggiornare i contract test per lingua/livello e input senza codice, nome o variante in `backend/tests/builder/test_builder_modelli_contract.py`, `backend/tests/discovery/test_builder_docs.py` e `backend/tests/catalog/test_catalogo_modelli_api.py`
- [x] T048 [P] [US1] Aggiungere test dello schema discovery per `lingue_possibili`, livelli duplicati/non ammessi e metadati consentiti solo sulle foglie in `backend/tests/discovery/test_discovery.py`
- [x] T049 [US1] Creare migration `0016` con `modello_documento.lingua`, `modello_documento.livello_professionale`, vincolo lingua IT/EN e backfill compatibile in `backend/alembic/versions/0016_modello_lingua_livello.py`
- [x] T050 [US1] Estendere modello ORM e schemi builder con lingua/livello, rimuovendo codice/nome/variante dalla richiesta di creazione in `backend/app/catalog/models.py` e `backend/app/builder/schemas.py`
- [x] T051 [US1] Validare `lingue_possibili` e `livelli_possibili` sulla foglia discovery e aggiornare mock/fixture senza cataloghi locali in `backend/app/discovery/schemas.py`, `infra/local/discovery-mock/discovery.json` e `backend/tests/discovery/`
- [x] T052 [P] [US1] Aggiungere test backend per naming generato, unicita' concorrente, variante STANDARD, lingua/livello non ammessi e conservazione completa dei campi in `backend/tests/builder/test_builder_flow_api.py`
- [x] T053 [US1] Generare codice/nome e validare lingua/livello contro la foglia in `backend/app/builder/service.py`, persistendo i nuovi attributi tramite `backend/app/builder/repository.py`
- [x] T054 [P] [US1] Rigenerare i tipi TypeScript dai contratti aggiornati e aggiungere test del form senza input liberi in `frontend/src/shared/api-types/` e `frontend/src/features/builder/modello-crea.component.spec.ts`
- [x] T055 [US1] Sostituire codice/nome/variante con selettori lingua/livello alimentati dalla foglia e inviare tutti i campi nella versione in `frontend/src/features/builder/modello-crea.component.ts`
- [x] T056 [US1] Mostrare lingua e livello nella tabella Contesti e nei relativi test in `frontend/src/features/builder/integrazioni-manager.component.html` e `frontend/src/features/builder/integrazioni-manager.component.spec.ts`

## Phase 7: User Story 2 - Pubblicare scope lingua/livello indipendenti (Priority: P1)

**Goal**: pubblicare modelli generici/specifici e IT/EN senza archiviazione
reciproca, rendendo la combinazione selezionabile dal catalogo operativo.

**Independent Test**: pubblicare CTER/tutti/IT, CTER/tutti/EN e CTER/VI/IT
lascia tutte e tre le versioni PUBBLICATO; una nuova CTER/VI/IT archivia solo
la precedente dello stesso scope.

- [x] T057 [P] [US2] Aggiungere test di coesistenza e sostituzione selettiva per lingua/livello in `backend/tests/builder/test_builder_flow_api.py`
- [x] T058 [US2] Includere lingua/livello nella ricerca della versione pubblicata corrente in `backend/app/builder/repository.py` e `backend/app/builder/service.py`
- [x] T059 [P] [US2] Aggiungere test dei filtri e dei campi lingua/livello del catalogo in `backend/tests/catalog/test_catalogo_modelli_api.py`
- [x] T060 [US2] Esporre e filtrare lingua/livello nel catalogo operativo in `backend/app/catalog/api.py`, `backend/app/catalog/service.py`, `backend/app/catalog/repository.py` e `backend/app/catalog/schemas.py`

## Phase 8: Validazione incremento lingua/livello

- [x] T061 [P] Aggiornare stato feature e istruzioni operative in `README.md`, `frontend/README.md`, `docs/project-map.md` e `specs/007-frontend-builder-consultazione/quickstart.md`
- [x] T062 (2026-09-21: 317 backend non-e2e, 61 contratti/documentazione, 66 frontend unit, lint e build, 3 Playwright reali; esiti in quickstart.md) Eseguire test contratti, backend non-e2e, frontend unit/lint/build e Playwright lifecycle reale; registrare comandi ed esiti in `specs/007-frontend-builder-consultazione/quickstart.md`
- [x] T063 (2026-09-21: T047-T062 completi, umbrella T041-T043 chiusi) Chiudere gli umbrella task T041-T043 solo dopo il completamento di T047-T062 in `specs/007-frontend-builder-consultazione/tasks.md`

## Phase 9: Edizioni collegate e contratto di generazione

**Goal**: collegare implicitamente le edizioni per categorizzazione/livello e
ritirare il flag di generazione specifico dei bandi.

- [x] T064 [P] Aggiornare decision register, spec 001/004/007 e contratti OpenAPI eliminando la semantica `bando_inglese`
- [x] T065 [P] Sostituire la validazione condizionata dal flag con l'obbligatorieta' del contratto della versione in `backend/app/validation/` e relativi test
- [x] T066 [P] Verificare con test catalogo che l'assenza del filtro `lingua` restituisca tutte le edizioni pubblicate corrispondenti e che il filtro selezioni IT o EN
- [x] T067 [US1] Aggiungere dalla gestione modello l'azione di creazione edizione collegata, precompilando integrazione, tipo, percorso e livello senza persistere `famiglia_modello_id`
- [x] T068 [P] Aggiornare mock GEBAN, esempi pubblicabili e documentazione eliminando `bando_inglese` e la generazione implicita di due output
- [x] T069 Eseguire test validazione/generazione/catalogo, contract test e suite frontend interessata; registrare gli esiti nel quickstart

---

## Dependencies & Execution Order

- [x] T045 Impedire presenza demo nelle installazioni nuove (opt-in test),
      senza bonifica automatica degli ambienti gia' utilizzati.
- [x] T046 Eliminazione logica modello con API per-contesto, audit,
      esclusione da nuove operazioni e conferma UI; conservare PDF e versioni.
      Verifica: 299 test backend passati (12 e2e esclusi), piu test dedicato
      eliminazione non autorizzata passato; 43 test frontend, lint e build
      produzione passati. Conferma verificata con test UI, non nuovo collaudo
      browser end-to-end. Gate indipendente FAIL: report reviewer non valido
      e regressione interna bloccata; non dichiarare completa la feature.


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
- **Categorizzazione (Phase 6)**: T047/T048/T052 possono partire in parallelo;
  migration e contratti precedono servizio e frontend.
- **Pubblicazione (Phase 7)**: dipende dai nuovi attributi persistiti della
  Phase 6, ma i test T057/T059 possono essere scritti prima del runtime.
- **Validazione (Phase 8)**: dipende da Phase 6 e Phase 7 complete.

### Parallel Opportunities

- T002-T004 possono girare in parallelo dopo T001.
- T007, T009, T010 possono girare in parallelo dopo T006 (T007 aspetta
  comunque T006 per il contratto `builder-modelli`).
- T011-T013 possono girare in parallelo (file diversi, nessuna dipendenza).
- T015 puo' girare mentre T011-T014 vengono scritti (task diversi,
  implementazione vs test).
- T020-T022 possono girare in parallelo.
- US4 e US5 possono procedere interamente in parallelo dopo Phase 2.
- T047, T048 e T052 possono procedere in parallelo; T054 puo' partire dopo i
  contratti; T057 e T059 possono procedere in parallelo dopo T049/T050.

## Implementation Strategy

1. Completare Setup + Foundational (Phase 1-2) - nessuno schermo reale
   ancora, ma `docker compose up frontend` funziona e l'auth e' vera.
2. Completare User Story 4 (Phase 3) - primo schermo utilizzabile per
   davvero: un admin puo' registrare e verificare un'integrazione contro
   `mock-geban`. **Questo e' il primo momento in cui l'utente puo' provare
   qualcosa sull'interfaccia**, come richiesto.
3. Completare User Story 5 (Phase 4) - secondo schermo: un manager crea un
   modello di test navigando la struttura scoperta.
4. Completare categorizzazione lingua/livello (Phase 6), quindi pubblicazione
   indipendente e catalogo (Phase 7).
5. Validare l'incremento e chiudere T041-T043 (Phase 8).
6. Completare gli altri residui Polish (Phase 5) senza confonderli con il gate
   indipendente, rinviato su indicazione dell'utente.
7. **Non incluso in questo incremento**: editor visuale, composizione
   sezioni (FR-011), revisione/pubblicazione da interfaccia (User Story 2),
   consultazione generazioni (User Story 3) - tutti scope futuro, da
   pianificare come incrementi successivi di questa stessa spec quando
   servira'.

## Phase 10: Correzione catalogo multi-sorgente

**Goal**: consentire a GEBAN di vedere i modelli pubblicati anche quando la
configurazione contiene piu' tipi documento attivi con lo stesso codice.

- [x] T070 [P] Aggiungere test di regressione per due `TipoDocumento` attivi con lo stesso codice e modelli pubblicati autorizzati in `backend/tests/catalog/test_catalog_service_integration.py`
- [x] T071 Adeguare la risoluzione del catalogo per aggregare le sorgenti attive autorizzate senza `SORGENTE_AMBIGUA` in `backend/app/catalog/repository.py` e `backend/app/catalog/service.py`
- [x] T072 Eseguire test catalogo e prova HTTP della ricerca GEBAN, registrando l'esito in `specs/007-frontend-builder-consultazione/quickstart.md`

## Phase 11: Unicita' tipo documento e compatibilita' discovery GEBAN

**Goal**: impedire nuovi duplicati funzionali e rendere conforme la risposta
discovery reale concordata con GEBAN.

- [x] T073 [P] Aggiungere test dell'alias discovery `lingue`/`ENG` e del conflitto con la forma canonica in `backend/tests/discovery/`
- [x] T074 Normalizzare gli alias GEBAN al confine dell'adapter in `backend/app/discovery/schemas.py`
- [x] T075 [P] Aggiungere test che il builder riusi e associ un tipo non assegnato dello stesso contesto/codice e rifiuti proprietari differenti in `backend/tests/builder/test_builder_flow_api.py`
- [x] T076 (2026-09-21: `BuilderService._tipo_per_integrazione` riusa/associa/rifiuta con 409 `TIPO_DOCUMENTO_ALTRA_INTEGRAZIONE`; `configurazione` `crea` rifiuta duplicati non inattivi; 317 test backend passati) Impedire nuove righe attive duplicate per `(codice_contesto, codice)` nei servizi configurazione e builder in `backend/app/configurazione/service.py` e `backend/app/builder/service.py`
- [x] T077 Migliorare il messaggio di disattivazione dei tipi con modelli collegati e verificare la disattivazione per ID del duplicato incompleto
- [x] T078 Eseguire test discovery/configurazione/builder e validare la risposta live GEBAN con l'adapter aggiornato

## Phase 12: Reset controllato ambiente di test

**Goal**: rendere ripetibile da terminale del container backend il ripristino
completo del database di test senza dipendere dalla directory corrente.

- [x] T079 Aggiungere il comando protetto `gemodo-reset-database` all'immagine backend e al compose Coolify
- [x] T080 Documentare abilitazione, conferma, risultato e riavvio in `docs/frontend-server-test.md`
- [x] T081 Verificare sintassi dello script e build dell'immagine backend

## Phase 13: Fallback catalogo ed edizioni linguistiche derivate

**Goal**: esporre a GEBAN una ricerca deterministica con fallback sul solo
livello e consentire al gestore di creare una versione inglese realmente
collegata e clonata dal modello italiano.

**Independent Test**: pubblicare CTER/tutti/IT con derivato CTER/tutti/EN e
CTER/VI/IT; la ricerca VI restituisce il modello specifico, la ricerca di un
livello senza modello restituisce il generico con fallback dichiarato, e il
catalogo senza lingua annida EN dentro IT.

- [x] T082 [P] [US1] Aggiornare i contratti OpenAPI catalogo e builder con fallback, risposta annidata ed endpoint di derivazione in `specs/001-catalogo-contratto-geban/contracts/geban-catalog-api.openapi.yaml` e `specs/002-builder-modelli/contracts/builder-modelli-api.openapi.yaml`
- [x] T083 [P] [US1] Aggiungere test catalogo per match esatto, fallback esclusivamente `IS NULL`, filtro lingua e annidamento delle edizioni in `backend/tests/catalog/test_catalogo_modelli_api.py` e `backend/tests/builder/test_builder_flow_api.py`
- [x] T084 [P] [US1] Aggiungere test builder per clonazione atomica, associazione al padre, lingua duplicata e audit in `backend/tests/builder/test_builder_flow_api.py`
- [x] T085 [US1] Aggiungere migration e mapping ORM per `modello_documento.derivato_da_modello_id` in `backend/alembic/versions/0017_modello_derivato.py` e `backend/app/catalog/models.py`
- [x] T086 [US1] Implementare ricerca a due passi e serializzazione annidata con metadati fallback in `backend/app/catalog/repository.py`, `backend/app/catalog/service.py` e `backend/app/catalog/schemas.py`
- [x] T087 [US1] Implementare endpoint atomico di creazione edizione derivata con copia versione/campi e audit in `backend/app/builder/api.py`, `backend/app/builder/schemas.py`, `backend/app/builder/service.py` e `backend/app/builder/repository.py`
- [x] T088 [US1] Sostituire la precompilazione del wizard con l'azione dashboard "Crea versione inglese" e stati di conferma/errore in `frontend/src/features/builder/integrazioni-manager.component.ts`, `frontend/src/features/builder/integrazioni-manager.component.html` e relativi test
- [x] T089 [P] Verificare contratti, migration PostgreSQL, suite backend/frontend interessate e documentare richieste/risposte di prova in `specs/007-frontend-builder-consultazione/quickstart.md`
- [x] T090 Correggere l'esempio Swagger del catalogo affinche' un'edizione derivata mostri `lingua: EN` in `specs/001-catalogo-contratto-geban/contracts/geban-catalog-api.openapi.yaml`

## Riallineamento spunte (2026-09-21)

Verificato su codice reale prima di spuntare: 52 test Vitest passati (13 file),
`eslint` pulito, 218 test backend passati (96 saltati, 12 e2e esclusi),
adapter discovery validato sulla risposta live di
`geban-service.test.si.cnr.it/api/v1/gemodo/discovery`
(BANDO_CONCORSO, 10 tipologie). Le sole prove NON eseguite sono i test
Playwright su stack reale.

- Spuntati perche' implementati e coperti da test: T011-T013, T015-T019
  (componenti, service, route `/configurazione` con `adminGuard`, gestione
  `REVISIONE_SUPERATA`/`DESTINAZIONE_NON_APPROVATA`/`VERIFICA_IN_CORSO`/
  `INTEGRAZIONE_DUPLICATA`), T025, T027, T028 (voce `/builder` con `isManager`),
  T077 (messaggio e test di disattivazione per id), T078.
- Restano aperti, correttamente: T014/T023/T031 (Playwright su stack reale,
  sospesi), T021/T022 (test dedicati albero e percorso ambiguo mancanti),
  T024/T026 (superati, vedi note), T029/T030/T061 (`frontend/README.md`
  assente, `docs/project-map.md` dice ancora "frontend non implementato"),
  T035, T062/T063. T075/T076 chiusi dopo il riallineamento (vedi T076).

## Phase 14: Allineamento al design handoff (FR-026)

**Goal**: portare landing contesti e categorizzazione al design
`design_handoff_modellario/`, senza layout alternativi.

- [x] T091 (2026-09-21: `contesti-lista.component` su `/contesti` con card, ricerca e chip; metriche solo reali = integrazioni per contesto; `/builder` reindirizza; 62 test Vitest, lint e build passati; e2e aggiornato ma NON eseguito su stack reale) Landing contesti `/contesti` a card (schermata 1a: ricerca, filtri a chip, metriche) al posto delle tab in `frontend/src/features/builder/integrazioni-manager.component.*`, con test Vitest e verifica Playwright
- [x] T092 (2026-09-21: `modello-crea.component` con blocchi-livello dinamici L1..Ln, stepper a 3 passi, riepilogo laterale, Genera modello; 56 test Vitest, lint e build passati; `e2e/builder-lifecycle.spec.ts` aggiornato al nuovo flusso ma NON eseguito su stack reale) Categorizzazione a tendine a cascata (schermata 2a: select L1-L4 dipendenti, azzeramento a cascata, stepper 3 passi) al posto dell'albero cliccabile in `frontend/src/features/builder/modello-crea.component.*`, con test per percorso ambiguo (assorbe T021/T022/T026)
- [x] T093 [P] (2026-09-21: metriche sui modelli caricati, ricerca + filtri stato/lingua, tabella 1b e griglia 1c con toggle `?view=grid`, badge di stato del design; nessuna metrica inventata - solo conteggi reali della pagina caricata; 65 test Vitest, lint e build passati) Lista modelli `/contesti/:ctxId/modelli` in tabella (1b) con toggle griglia `?view=grid` (1c), stati vuoto/errore/caricamento


## Phase 15: Anteprima modello sulla schermata 2b ridotta (2026-09-22)

**Goal**: vedere i campi che l'API mette a disposizione per un modello, sulla
stessa pagina che diventera' l'editor quando `003` sara' implementata.

- [x] T094 [P] Unit test per l'anteprima: campi del contratto resi dall'API
      con codice, etichetta, tipo, lingua e obbligatorieta'; stati di
      caricamento, errore e modello senza versioni, in
      `frontend/src/features/builder/modello-anteprima.component.spec.ts`
- [x] T095 (2026-09-22) Schermata 2b in versione ridotta su `/modelli/:modelId/builder`:
      topbar con codice, versione e stato, pannello destro con i campi del
      contratto nello stile segnaposto del design, percorso di categorizzazione
      nel footer del pannello. Outline sezioni e foglio centrale restano vuoti
      con uno stato esplicito, non finti: i contenuti arrivano con `003`
- [x] T096 Collegamento dalla lista modelli (1b/1c) all'anteprima e ritorno,
      con verifica Playwright sul flusso reale

## Correzione allineamento a 1b (2026-09-22)

Segnalazione dell'utente: la lista modelli non era in linea con la schermata 1b
e la creazione dell'edizione inglese stava nel posto sbagliato.

- La tabella ha ora le colonne di 1b: Modello (nome che porta a 2b + codice),
  Tipo, Ver., Stato, Creazione, Azioni. Le azioni di riga sono "Modifica" piu'
  il kebab, che contiene la transizione di ciclo di vita e l'eliminazione.
- **"Crea versione inglese" e' stata spostata nell'anteprima del modello**,
  dov'e' il suo posto: la lista non offre piu' quell'azione.
- Due colonne del design non sono state realizzate perche' i dati non esistono:
  "Ultima modifica" (l'API espone `created_at`, non la modifica, e nessun
  autore) e "Utilizzi". Al posto della prima c'e' "Creazione"; la seconda e'
  omessa. Da riprendere se il backend le esporra'.
- Regressione trovata e corretta grazie all'e2e: la topbar dell'anteprima
  mandava la pagina in scroll orizzontale a 390px, perche' il codice generato
  e' lungo e aveva `nowrap`.

Verifica: 72 test Vitest, lint e build passati; 3 Playwright reali verdi su
stack dedicato.

## Phase: Filtri sull'elenco modelli (2026-09-23)

**Origine**: richiesta d'uso del 2026-09-23. Con 65 foglie di
categorizzazione live l'elenco unico e' gia' poco pratico, e con un secondo
sistema integrato diventa inutilizzabile.

- [x] T097 (parziale: stato e lingua) [FR-028] I due filtri gia' presenti
      nell'elenco modelli erano applicati **nel client** su `models()`, cioe'
      sulla sola pagina caricata - proprio il difetto che FR-028 vieta. Ora
      partono come richiesta al server e riportano alla prima pagina
- [x] T103 [FR-028] (`GET /builder/modelli/filtri`, `repository.voci_filtro`;
      tendine in `integrazioni-manager.component.html`) Filtri per tipologia,
      profilo e livello. Le voci vengono dai **modelli esistenti** nel
      contesto, non dall'albero live: l'elenco modelli non richiede discovery
      online e legarlo a GEBAN per riempire due tendine sarebbe una
      regressione di robustezza; inoltre l'albero offrirebbe combinazioni
      senza alcun modello. Una tendina compare solo se ha piu' di una voce
- [x] T104 [FR-028] (parametro `ricerca` su `GET /builder/modelli`) La
      ricerca testuale passa dal server e compone con gli altri filtri
- [ ] T105 [FR-028] **Nota sulla scala, da rivedere in futuro**: la ricerca usa
      `ILIKE '%testo%'` su nome e codice, che non puo' usare un indice. Con
      modelli nell'ordine delle centinaia e' irrilevante; se crescessero di
      ordini di grandezza servirebbe una ricerca vera (indice trigram
      `pg_trgm`, oppure una colonna `tsvector` con indice GIN). Non
      anticiparlo: va fatto quando il volume lo richiede, non prima
- [x] T098 [FR-028] (`sincronizzaUrl`/`ripristinaFiltriDaUrl` in
      `integrazioni-manager.component.ts`) Stato dei filtri riflesso nell'URL
      e ripristinato al caricamento
- [x] T099 [FR-028] (`builder/repository.py:lista_modelli`, `builder/api.py`,
      `FiltriModelli` in `builder/schemas.py`; contratto OpenAPI allineato;
      test in `backend/tests/builder/test_filtri_modelli.py`) Parametri di
      filtro su `GET /builder/modelli`, composti con `offset`/`limit`:
      `codice_tipo_documento`, `integrazione_id`, `codice_tipologia`,
      `codice_categoria`, `lingua`, `livello_professionale` (token `TUTTI`
      per i modelli senza livello), `variante`, `stato_versione`
- [x] T100 [P] [FR-028] (`test_filtri_modelli.py::test_filtro_senza_corrispondenze_e_elenco_vuoto_non_errore`
      e `::test_il_filtro_precede_la_paginazione`, piu' due test in
      `integrazioni-manager.component.spec.ts`) Test: filtro senza
      corrispondenze restituisce un elenco vuoto e non un errore; il filtro
      precede la paginazione
- [ ] T101 [FR-019 di `002`] Flusso varianti in interfaccia: alla creazione,
      se la categorizzazione e' gia' occupata, mostrare quale modello esiste e
      proporre la creazione di una variante chiedendo la descrizione; non
      mostrare alcuna sezione variante quando la categorizzazione e' libera.
      Stesso flusso raggiungibile dalla pagina di modifica di un modello
- [ ] T102 [FR-019 di `002`] Nell'elenco, raggruppare le varianti sotto il
      modello di base della loro categorizzazione, mostrando per ciascuna la
      descrizione scritta dal gestore
