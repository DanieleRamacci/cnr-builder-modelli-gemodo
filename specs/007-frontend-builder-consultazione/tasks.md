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

- [ ] T006 Verificare `specs/002-builder-modelli/contracts/
      builder-modelli-api.openapi.yaml` contro l'implementazione reale di
      `backend/app/builder/api.py` (drift atteso dopo i riallineamenti
      discovery/integrazioni T081-T083 della 010) e correggerlo; registrarlo
      in `PUBLISHED_CONTRACTS` (`backend/app/quality/openapi_docs.py`) cosi'
      da avere `/docs/builder-modelli` e `/redoc/builder-modelli` reali
      (gap Foundational gia' descritto in `research.md`) - **task lato
      backend**, prerequisito di T008
- [ ] T007 [P] Generare i tipi TypeScript dai 4 contratti OpenAPI necessari
      (`integrazioni`, `configurazione-cataloghi`, `builder-discovery`,
      `builder-modelli`, quest'ultimo dopo T006) via `openapi-typescript`,
      script `frontend/scripts/genera-tipi-api.sh` + output in
      `frontend/src/shared/api-types/`
- [ ] T008 Implementare il client HTTP condiviso (wrapper sottile su
      `HttpClient`, non un SDK generato) in
      `frontend/src/shared/api-client.ts`, con mappatura esplicita
      dell'envelope di errore backend (`{codice, messaggio}`) verso un tipo
      UI-friendly, senza logica di retry automatico sui conflitti
      ottimistici (`REVISIONE_SUPERATA` resta un caso da gestire nel
      componente chiamante, mai nascosto qui)
- [ ] T009 [P] Implementare il modulo di autenticazione Keycloak
      (`keycloak-js` + `keycloak-angular`, Authorization Code + PKCE, client
      id `gemodo-frontend`) in `frontend/src/app/auth/`, incluso
      l'interceptor Bearer che il client HTTP (T008) usa per ogni chiamata
- [ ] T010 [P] Implementare la shell applicativa (layout, navigazione,
      componenti Design Angular Kit condivisi) in `frontend/src/app/shell/`

**Checkpoint**: un utente autenticato via Keycloak vede la shell vuota;
nessuna chiamata API reale ancora cablata a uno schermo.

---

## Phase 3: User Story 4 - Registrare e verificare un'integrazione (Priority: P1) 🎯 MVP

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

- [ ] T020 [P] [US5] Unit test (Vitest) per la lista integrazioni manager:
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
- [ ] T032 Rivedere `docs/decision-register.yaml` per collegare eventuali
      decisioni aperte specifiche di questo incremento (se emerse durante
      l'implementazione - nessuna nota gia' oggi)

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
