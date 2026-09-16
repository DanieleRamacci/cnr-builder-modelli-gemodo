# Tasks: Configurazione Cataloghi E Integrazioni

**Input**: Design documents from `specs/010-configurazione-cataloghi-integrazioni/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`

**Tests**: inclusi (stesso standard di `001`/`002`: nessun mock del DB, test reali su Postgres).

**Organization**: task raggruppati per user story (P1: US1-US3, P2: US4), piu' Setup/Foundational/Polish.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Setup

- [ ] T001 Creare lo scheletro dei moduli `backend/app/discovery/` e
      `backend/app/configurazione/` (`__init__.py`, struttura da `plan.md`)
- [ ] T002 [P] Creare `contracts/configurazione-cataloghi-api.openapi.yaml` con
      security scheme `KeycloakBearer` riusato da `001`, error catalog stub

---

## Phase 2: Foundational (Blocking Prerequisites)

**⚠️ CRITICAL**: nessuna user story puo' iniziare prima che questa fase sia completa.

- [ ] T003 *(2026-09-15, `DEC-001-CONTESTO-SOSTITUISCE-UFFICIO`: niente tabella
      `ufficio`)* Migration `tipo_documento.codice_contesto` (schema gia' deciso
      in `specs/001-catalogo-contratto-geban/data-model.md`) — creare solo se
      `001/tasks.md` T085 non l'ha gia' introdotta; non riprogettare lo schema
- [ ] T004 Migration `registro_contratti_dati` (schema gia' deciso in `001`,
      stessa cautela di T003 rispetto a `001/tasks.md` T087)
- [ ] T005 [P] Migration `attributo_profilo` (`data-model.md`)
- [ ] T006 [P] Migration `endpoint_integrazione` (`data-model.md`)
- [ ] T007 [P] Migration `schema_discovery_generato` (`data-model.md`)
- [ ] T008 Modelli SQLAlchemy `AttributoProfilo`, `EndpointIntegrazione`,
      `SchemaDiscoveryGenerato` in `backend/app/configurazione/models.py`
- [x] T009 *(implementata 2026-09-16, forma ridotta)* Interfaccia astratta
      `PortaDiscovery` e DTO in `backend/app/discovery/port.py`/`schemas.py`:
      `tipologie_disponibili`/`campi_disponibili` implementati e testati (via
      `backend/tests/builder/test_builder_flow_api.py`, non un test dedicato al
      modulo discovery). **Non incluso**: `profili_disponibili`/
      `attributi_profilo` come metodi separati del port (per stasera i profili
      sono annidati dentro `TipologiaDisponibile.profili`, niente
      `AttributoDisponibile`/`AttributoProfilo` — il campo `livello` resta un
      campo normale del registro contratti dati, non ancora un attributo
      profilo-dipendente risolto dinamicamente). Aggiornare quando si
      implementa T005/T008 (`AttributoProfilo`).
- [x] T010 [P] *(implementata 2026-09-16)* `AdapterLocale` in
      `backend/app/discovery/adapter_locale.py`, legge `ClassificazioneCatalogo`/
      `TipologiaBandoSOL`/`CategoriaDocumento`/`RegistroContrattiDati` reali —
      verificato su Postgres reale, non solo unit test in memoria.
- [ ] T011 [P] Implementare la cache in memoria di processo (TTL breve, mai
      persistente) in `backend/app/discovery/cache.py`
- [ ] T012 Implementare `AdapterHTTP` in `backend/app/discovery/adapter_http.py`
      (client `httpx`, paginazione HAL trasparente, usa T011, solleva errore
      funzionale di connessione se il sistema esterno non risponde oltre la
      finestra di cache — depende da T009-T011). *(2026-09-16, chiarito dal
      product owner: il parsing dell'albero DEVE essere generico/ricorsivo —
      cammina i `nodi[]`/`figli[]` della risposta a qualunque profondita' il
      sistema esterno la fornisca, mai un parser scritto assumendo un numero
      fisso di livelli (es. "sempre tipologia poi profilo") — coerente con
      `NodoCategorizzazione` in
      `specs/010-configurazione-cataloghi-integrazioni/contracts/
      geban-discovery-endpoint.openapi.yaml`. L'unica parte a forma fissa e'
      il singolo campo (`CampoContrattoDati`), letto solo sui nodi foglia.
      Nessun codice oggi legge dal vero endpoint GEBAN — `AdapterLocale`
      (T010) legge solo le tabelle locali `001`, a 2 livelli fissi perche'
      quella e' la forma reale locale di `BANDO_CONCORSO`, non un vincolo
      sui dati che GEBAN potra' restituire.)*
- [ ] T013 [P] Server di test locale che simula l'envelope HAL di GEBAN
      (`_embedded`/`_links`/`page`) in `backend/tests/discovery/support/`, usato
      da tutti i test dell'adapter HTTP invece di chiamare GEBAN reale
- [ ] T014 Coordinare con `006` il ruolo amministrativo di FR-012 (distinto da
      `GEMODO_MODELLI_GESTORE`); bloccante per T021/T029/T040/T045 se il ruolo
      non esiste ancora nella `006`

**Checkpoint**: porta di discovery e tabelle pronte — le user story possono partire.

---

## Phase 3: User Story 1 - Definire la struttura di un tipo documento (Priority: P1) 🎯 MVP

**Goal**: un operatore definisce tipo documento, tipologie, profili, campi (incluso un campo dipendente da un attributo profilo) tramite l'albero JSON.

**Independent Test**: creare un tipo documento con almeno una tipologia/profilo/campo e vederlo salvato come "definito, non connesso" senza generare nulla.

### Tests for User Story 1

- [ ] T015 [P] [US1] Contract test per la definizione struttura in
      `backend/tests/configurazione/contract/test_definizione_struttura_api.py`
- [ ] T016 [P] [US1] Integration test: creazione completa (tipo + tipologia +
      profilo + campo) -> stato "definito, non connesso" (Acceptance Scenario 1)
      in `backend/tests/configurazione/integration/test_definizione_struttura.py`
- [ ] T017 [P] [US1] Integration test: campo che referenzia un
      `AttributoProfilo` non richiede opzioni proprie, le eredita dal profilo
      scelto (Acceptance Scenario 2)
- [ ] T018 [P] [US1] Integration test: tipo documento senza tipologie resta
      "incompleto" — guardia riusata da US2 (Acceptance Scenario 3)

### Implementation for User Story 1

- [ ] T019 [P] [US1] Repository di scrittura per
      `TipoDocumento`/`CategoriaDocumento`/`TipologiaBandoSOL`/`AttributoProfilo`
      in `backend/app/configurazione/repository.py` (riusa modelli `001` per le
      prime tre, non li ridefinisce)
- [ ] T020 [US1] `DefinizioneStrutturaService` (crea/aggiorna tipo documento +
      tipologie + profili + campi in un'unica transazione) in
      `backend/app/configurazione/service.py` — depende da T019
- [ ] T021 [US1] Endpoint `POST /configurazione/tipi-documento` e
      `PUT /configurazione/tipi-documento/{codice}/struttura` in
      `backend/app/configurazione/api.py`, protetti dal ruolo FR-012 (T014)
- [ ] T022 [US1] Validazione "definizione completa" (almeno una
      tipologia/profilo/campo) riusata come guardia da US2 — depende da T020
- [ ] T023 [US1] Evento audit per ogni creazione/modifica struttura

**Checkpoint**: User Story 1 funzionante e testabile in isolamento.

---

## Phase 4: User Story 2 - Generare il contratto/documentazione per l'integratore (Priority: P1)

**Goal**: dalla definizione (US1) generare uno schema/esempio JSON versionato da consegnare a un team esterno.

**Independent Test**: definizione completa -> schema generato scaricabile, coerente con `docs/adr/0001-esempio-discovery-geban.json`.

### Tests for User Story 2

- [ ] T024 [P] [US2] Contract test per generazione/export schema in
      `backend/tests/configurazione/contract/test_schema_discovery_api.py`
- [ ] T025 [P] [US2] Integration test: schema generato da una definizione
      equivalente al caso GEBAN coerente con la forma di
      `docs/adr/0001-esempio-discovery-geban.json`
- [ ] T026 [P] [US2] Integration test: generazione bloccata su definizione
      incompleta, errore indica cosa manca (Acceptance Scenario, riusa T018)

### Implementation for User Story 2

- [ ] T027 [US2] Repository `SchemaDiscoveryGenerato` (versionamento
      incrementale per tipo documento) in `backend/app/configurazione/repository.py`
- [ ] T028 [US2] Service di generazione: proietta la struttura (T019-T020) nel
      JSON schema/esempio (tipo documento, tipologie, profili, campi, attributi
      profilo-dipendenti, data di validita') — depende da T022, T027
- [ ] T029 [US2] Endpoint `POST /configurazione/tipi-documento/{codice}/schema-discovery`
      (genera nuova versione) e `GET .../schema-discovery/{versione}` (esporta,
      FR-007), protetti dal ruolo FR-012 (T014)
- [ ] T030 [US2] Evento audit di generazione/esportazione

**Checkpoint**: User Story 1+2 funzionanti — un tipo documento puo' essere definito e il suo contratto generato e consegnato, anche senza ancora registrare un endpoint.

---

## Phase 5: User Story 3 - Registrare l'endpoint e attivare l'integrazione (Priority: P1)

**Goal**: registrare l'URL fornito dal team esterno, verificarne la conformita' allo schema generato, portare il tipo documento a "connesso".

**Independent Test**: un endpoint di prova conforme porta lo stato a "connesso"; uno non conforme o irraggiungibile resta "non connesso" con errore esplicito.

### Tests for User Story 3

- [ ] T031 [P] [US3] Contract test per registrazione/verifica endpoint in
      `backend/tests/configurazione/contract/test_endpoint_integrazione_api.py`
- [ ] T032 [P] [US3] Integration test: endpoint conforme -> stato `CONNESSO`
      (Acceptance Scenario 1)
- [ ] T033 [P] [US3] Integration test: endpoint con campi mancanti/extra
      rispetto allo schema -> stato `ERRORE`, mai `CONNESSO` (Acceptance
      Scenario 2) — *(nota: la soglia esatta errore vs avviso per dati non
      attesi resta `ASSUNTA_PROVVISORIA` su `DEC-001-VERSIONING-RIFERIMENTI-
      ESTERNI`; questo test copre solo il caso gia' deciso — campo non
      dichiarato = errore, non silenziosamente accettato — non le soglie fini)*
- [ ] T034 [P] [US3] Integration test: endpoint irraggiungibile in fase di
      registrazione -> stato `ERRORE` con messaggio esplicito, non stato
      ambiguo (Edge Case)
- [ ] T035 [P] [US3] Integration test: endpoint irraggiungibile durante la
      *creazione di un modello* (non la registrazione) -> `PortaDiscovery`
      solleva errore funzionale di connessione, mai un menu vuoto silenzioso
      (Acceptance Scenario 3) — test diretto contro `AdapterHTTP`/`PortaDiscovery`
      (T009-T012), indipendente dal builder `002` non ancora implementato
- [ ] T036 [P] [US3] Integration test: tipo documento self-service, nessuna
      riga `EndpointIntegrazione`, utilizzabile subito dopo US1 (Acceptance
      Scenario 4, SC-003)
- [ ] T037 [P] [US3] Integration test: ridefinizione struttura dopo
      `CONNESSO` riporta lo stato a `DEFINITO` finche' non c'e' un nuovo test
      riuscito contro la nuova versione dello schema (state transition,
      `data-model.md`)

### Implementation for User Story 3

- [ ] T038 [US3] Repository `EndpointIntegrazione` in
      `backend/app/configurazione/repository.py`
- [ ] T039 [US3] Service di test di connessione: chiama `AdapterHTTP` (T012)
      contro l'URL registrato, confronta la risposta con lo
      `SchemaDiscoveryGenerato` corrente (T027), aggiorna `stato`/`esito_ultimo_test`
      — depende da T012, T027, T038
- [ ] T040 [US3] Endpoint `POST /configurazione/tipi-documento/{codice}/endpoint-integrazione`
      (registra + testa) e `POST .../endpoint-integrazione/verifica` (ri-testa),
      protetti dal ruolo FR-012 (T014)
- [ ] T041 [US3] Collegare `PortaDiscovery.*_disponibili` allo stato
      `EndpointIntegrazione.stato`: un tipo documento non `CONNESSO` (e non
      self-service) MUST rifiutare la richiesta con errore esplicito invece di
      interrogare l'adapter (FR-009) — depende da T009, T038
- [ ] T042 [US3] Evento audit di registrazione/test/ri-verifica

**Checkpoint**: User Story 1-3 (tutte P1) complete — il flusso di onboarding end-to-end funziona per un tipo documento integrato o self-service.

---

## Phase 6: User Story 4 - Vedere lo stato di connessione nella dashboard (Priority: P2)

**Goal**: vista aggregata dello stato di ogni tipo documento configurato.

**Independent Test**: la dashboard mostra correttamente definito/connesso/errore per tipi documento in stati diversi.

### Tests for User Story 4

- [ ] T043 [P] [US4] Contract test per la vista dashboard in
      `backend/tests/configurazione/contract/test_dashboard_stato_api.py`
- [ ] T044 [P] [US4] Integration test: stato corretto per tipi documento in
      stati diversi (Acceptance Scenario 1)

### Implementation for User Story 4

- [ ] T045 [US4] Endpoint `GET /configurazione/tipi-documento` (vista
      amministrativa aggregata con stato ed esito ultimo test) in
      `backend/app/configurazione/api.py` — endpoint interno, non il sostituto
      della `listTipiDocumento` GEBAN-facing ritirata (`DEC-001-RITIRO-
      ENDPOINT-CLASSIFICAZIONE`): quella non aveva un pubblico interno, questa
      si', sono contratti diversi nonostante il nome simile
- [ ] T046 [US4] Query aggregata in `backend/app/configurazione/repository.py`
      (join `TipoDocumento` + `EndpointIntegrazione` + ultima
      `SchemaDiscoveryGenerato`) — depende da T038, T027

**Checkpoint**: tutte le user story funzionanti indipendentemente.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [ ] T047 [P] Completare `contracts/configurazione-cataloghi-api.openapi.yaml`
      con esempi di successo/errore per FR-001..FR-009
- [ ] T048 [P] Verificare Swagger/ReDoc locale per il nuovo contratto
      (Costituzione, principio VI)
- [ ] T049 [P] Scrivere `quickstart.md`: scenario end-to-end con una fixture
      tipo-Contratti (diversa da `BANDO_CONCORSO`, per dimostrare che il motore
      e' generico — vedi conversazione 2026-09-15), definizione -> generazione
      schema -> registrazione endpoint mock (T013) -> stato `CONNESSO`
- [ ] T050 Eseguire `specs/001-catalogo-contratto-geban/tasks.md` T108 (ritiro
      delle tre API di classificazione legacy) — solo ora sbloccato, come da
      `plan.md` Dependencies; non eseguire T108 prima che T029 (esportazione
      schema) sia funzionante
- [ ] T051 Aggiornare `docs/project-map.md` con lo stato effettivamente
      implementato di questa spec
- [ ] T052 Eseguire la suite pytest completa su Postgres reale (non mock) e
      registrare l'esito in `quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: nessuna dipendenza.
- **Foundational (Phase 2)**: dipende da Setup; blocca tutte le user story.
- **US1 (Phase 3)**: dipende da Foundational; nessuna dipendenza da altre US.
- **US2 (Phase 4)**: dipende da Foundational + il modello di dati di US1
  (T019-T022), ma e' testabile senza US3.
- **US3 (Phase 5)**: dipende da Foundational + schema generato da US2 (T027-T029)
  — il test di connessione confronta contro quello schema.
- **US4 (Phase 6)**: dipende da US1+US3 (legge lo stato che producono).
- **Polish (Phase 7)**: dipende da tutte le user story desiderate.

### Parallel Opportunities

- T003-T007 (migration) possono girare in parallelo dopo T001-T002.
- T010, T011 possono girare in parallelo dopo T009.
- T015-T018, T024-T026, T031-T037, T043-T044 (test di ciascuna user story)
  possono girare in parallelo fra loro all'interno della stessa fase.
- T047-T049 possono girare in parallelo dopo che il comportamento e' stabile.

## Parallel Example: User Story 3

```text
Task: T032 Endpoint conforme -> CONNESSO
Task: T033 Endpoint con campi mancanti/extra -> ERRORE
Task: T034 Endpoint irraggiungibile in registrazione -> ERRORE esplicito
Task: T035 Endpoint irraggiungibile in creazione modello -> errore di connessione
Task: T036 Self-service, nessun endpoint richiesto
Task: T037 Ridefinizione dopo CONNESSO -> torna DEFINITO
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Completare Phase 1-2 (Setup, Foundational).
2. Completare Phase 3 (US1).
3. **STOP e VALIDARE**: un operatore puo' definire un tipo documento completo,
   nient'altro ancora funziona (nessun contratto generato, nessun endpoint
   registrabile) — coerente con SC-001 preso da solo.

### Incremental Delivery

1. Setup + Foundational -> porta di discovery pronta.
2. US1 -> definizione struttura (MVP).
3. US2 -> generazione contratto (sblocca la consegna a un team esterno, e in
   prospettiva T108 di `001`).
4. US3 -> registrazione endpoint, integrazione realmente attivabile.
5. US4 -> visibilita' operativa (non blocca nessuna delle precedenti).

## Notes

- Nessun endpoint viene mai generato dinamicamente per tipo documento (vedi
  conversazione 2026-09-15): tutte le operazioni di questa spec restano sui
  quattro endpoint fissi elencati in T021/T029/T040/T045 — cambiano solo i
  dati che leggono/scrivono.
- La cache dell'adapter HTTP (T011-T012) MUST restare in memoria di processo:
  non introdurre una tabella DB per "velocizzare" la navigazione — e'
  esattamente il pattern che l'ADR 0001 ha eliminato.
- `DEC-001-VERSIONING-RIFERIMENTI-ESTERNI` resta `ASSUNTA_PROVVISORIA` e blocca
  formalmente la fase `TASKS` per questa spec: T033 e T039 implementano solo
  la parte gia' decisa (dati non attesi = errore funzionale, mai accettazione
  silenziosa); la visualizzazione della data di validita' del riferimento e le
  soglie fini errore/avviso restano da chiudere col product owner prima di
  chiudere definitivamente T039/T045-T046 in produzione — non inventare qui
  una soglia non decisa.
- `001/tasks.md` T108 (ritiro API di classificazione legacy) dipende da T050 di
  questa spec, non il contrario: non rimuovere le API GEBAN-facing prima che
  il sostituto (US2) sia realmente funzionante.
