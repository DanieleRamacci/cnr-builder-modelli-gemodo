# Tasks: Configurazione Cataloghi E Integrazioni

**Input**: Design documents from `specs/010-configurazione-cataloghi-integrazioni/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`

**Tests**: inclusi (stesso standard di `001`/`002`: nessun mock del DB, test reali su Postgres).

**Organization**: task raggruppati per user story (P1: US1-US3, P2: US4), piu' Setup/Foundational/Polish.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Setup

- [x] T001 Creare lo scheletro dei moduli `backend/app/discovery/` e
      `backend/app/configurazione/` (`__init__.py`, struttura da `plan.md`)
      Discovery presente; configurazione include __init__, models, security,
      api, schemas, repository e service (ripresa US1/US2).
- [x] T002 [P] Completare `contracts/configurazione-cataloghi-api.openapi.yaml`
      come contratto amministrativo pre-runtime: path, payload, risposte
      success/error con esempi, security scheme `KeycloakBearer` riusato da
      `001`, note di autorizzazione collegate a T014. Questo task e' un gate di
      contract-first: nessun endpoint runtime T021/T029/T040/T045 puo' iniziare
      prima che il contratto sia allineato.
      Contratto v0.2 riallineato prima delle route US1/US2: envelope errori,
      ruoli, tipi campo, definizione proprietaria e revisione, esempi. Le route
      US3 restano pianificate; riallineamento runtime futuro obbligatorio T047.

---

## Phase 2: Foundational (Blocking Prerequisites)

**⚠️ CRITICAL**: nessuna user story puo' iniziare prima che questa fase sia completa.
Il contratto OpenAPI amministrativo (T002) e la decisione autorizzativa (T014)
fanno parte dei prerequisiti bloccanti per rispettare il gate contract-first.

- [x] T003 *(soddisfatta dalla migration `001`/`0008`, 2026-09-16;
      `DEC-001-CONTESTO-SOSTITUISCE-UFFICIO`: niente tabella
      `ufficio`)* Migration `tipo_documento.codice_contesto` (schema gia' deciso
      in `specs/001-catalogo-contratto-geban/data-model.md`) — gia' introdotta
      da `backend/alembic/versions/0008_contesto_registro_contratti_audit.py`;
      non riprogettare lo schema
- [x] T004 *(soddisfatta dalla migration `001`/`0008`, 2026-09-16)* Migration
      `registro_contratti_dati` (schema gia' deciso in `001`) — gia' introdotta
      da `backend/alembic/versions/0008_contesto_registro_contratti_audit.py`
- [x] T005 [P] Migration `attributo_profilo` (`data-model.md`), 0010:
      solo attributi dell'esempio proprietario, nessuna replica GEBAN.
- [x] T006 [P] Migration `endpoint_integrazione` (`data-model.md`), 0010
- [x] T007 [P] Migration `schema_discovery_generato` (`data-model.md`), 0010
- [x] T008 Modelli SQLAlchemy `AttributoProfilo`, `EndpointIntegrazione`,
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
- [x] T011 [P] *(2026-09-17: TTL 60s configurabile, capienza limitata,
      copie isolate, riempimenti sincronizzati, nessun fallback scaduto)*
      Implementare la cache in memoria di processo (TTL breve, mai
      persistente) in `backend/app/discovery/cache.py`
- [x] T012 *(2026-09-17: risposta completa e envelope HAL documentato,
      parsing ricorsivo, cache escludibile, limiti e errori espliciti;
      lettura reale GEBAN riuscita, nessun collegamento automatico al builder)*
      Implementare `AdapterHTTP` in `backend/app/discovery/adapter_http.py`
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
      L'adapter HTTP e' ora verificato anche sul vero endpoint GEBAN;
      la selezione runtime dell'adapter nel builder resta T041. `AdapterLocale`
      (T010) legge solo le tabelle locali `001`, a 2 livelli fissi perche'
      quella e' la forma reale locale di `BANDO_CONCORSO`, non un vincolo
      sui dati che GEBAN potra' restituire.)*
- [x] T013 [P] *(2026-09-17)* Server HTTP locale che simula la risposta
      completa e l'envelope HAL documentato (`_embedded.discovery`/`_links.next`)
      in `backend/tests/discovery/conftest.py`, usato
      dai test di trasporto reale/paginazione; i test di errore usano trasporti
      controllati. Nessun test automatico chiama GEBAN reale.
- [x] T014 Applicare `GEMODO_ADMIN` gia' previsto in `006` FR-005/FR-005a
      al contratto e ai guard amministrativi FR-012; testare rifiuto del solo
      `GEMODO_MODELLI_GESTORE`. Bloccante per T021/T029/T040/T045;
      nessun nuovo ruolo o mapping implicito dei ruoli GEBAN.
      Guard riusabile `app.configurazione.security.require_configurazione_admin`;
      test 401/403 e successo admin. Gli endpoint non sono ancora implementati;
      la loro applicazione del guard sara' verificata nei contract test US1-US4.

**Checkpoint**: porta di discovery e tabelle pronte — le user story possono partire.

---

## Phase 3: User Story 1 - Definire la struttura di un tipo documento (Priority: P1) 🎯 MVP

**Goal**: un operatore definisce tipo documento, tipologie, profili, campi (incluso un campo dipendente da un attributo profilo) tramite l'albero JSON.

**Independent Test**: creare un tipo documento con almeno una tipologia/profilo/campo e vederlo salvato come "definito, non connesso" senza generare nulla.

### Tests for User Story 1

- [x] T015 [P] [US1] Contract test per la definizione struttura in
      `backend/tests/configurazione/contract/test_definizione_struttura_api.py`
- [x] T016 [P] [US1] Integration test: creazione completa (tipo + tipologia +
      profilo + campo) -> stato "definito, non connesso" (Acceptance Scenario 1)
      in `backend/tests/configurazione/integration/test_definizione_struttura.py`
- [x] T017 (2026-09-22: coperto da `test_onboarding_contratti.py`, dove lo stesso campo `soglia` eredita tre opzioni da FORN e due da SERV senza portarne di proprie; la risoluzione simbolica nel builder live resta fuori scope di questo test, vedi US5) [P] [US1] Integration test: campo che referenzia un
      `AttributoProfilo` non richiede opzioni proprie, le eredita dal profilo
      scelto (Acceptance Scenario 2)
      IN CORSO: ereditarieta' risolta nell'esempio generato e testata;
      la risoluzione dei riferimenti simbolici nel builder live resta da fare.
- [x] T018 [P] [US1] Integration test: tipo documento senza tipologie resta
      "incompleto" — guardia riusata da US2 (Acceptance Scenario 3)

### Implementation for User Story 1

- [x] T019 [P] [US1] Repository della definizione/esempio proprietario in
      `backend/app/configurazione/repository.py`: riusa `TipoDocumento`, mai
      categorie/tipologie/registro globali ritirati da FR-016. Design T074:
      revisioni JSON proprietarie, non discovery ricevuti dall'esterno.
- [x] T020 [US1] `DefinizioneStrutturaService` (crea/aggiorna tipo documento +
      tipologie + profili + campi in un'unica transazione) in
      `backend/app/configurazione/service.py` — depende da T019
- [x] T021 [US1] Endpoint `POST /configurazione/tipi-documento` e
      `PUT /configurazione/tipi-documento/{codice}/struttura` in
      `backend/app/configurazione/api.py`, protetti dal ruolo FR-012 (T014)
- [x] T022 [US1] Validazione "definizione completa" (almeno una
      tipologia/profilo/campo) riusata come guardia da US2 — depende da T020
- [x] T023 [US1] Evento audit per ogni creazione/modifica struttura

**Checkpoint**: User Story 1 funzionante e testabile in isolamento.

---

## Phase 4: User Story 2 - Generare il contratto/documentazione per l'integratore (Priority: P1)

**Goal**: dalla definizione (US1) generare uno schema/esempio JSON versionato da consegnare a un team esterno.

**Independent Test**: definizione completa -> schema generato scaricabile, coerente con `docs/adr/0001-esempio-discovery-geban.json`.

### Tests for User Story 2

- [x] T024 [P] [US2] Contract test per generazione/export schema in
      `backend/tests/configurazione/contract/test_schema_discovery_api.py`
- [x] T025 [P] [US2] Integration test: schema generato da una definizione
      equivalente al caso GEBAN coerente con la forma di
      `docs/adr/0001-esempio-discovery-geban.json`
- [x] T026 [P] [US2] Integration test: generazione bloccata su definizione
      incompleta, errore indica cosa manca (Acceptance Scenario, riusa T018)

### Implementation for User Story 2

- [x] T027 [US2] Repository `SchemaDiscoveryGenerato` (versionamento
      incrementale per tipo documento) in `backend/app/configurazione/repository.py`
- [x] T028 [US2] Service di generazione: proietta la struttura (T019-T020) nel
      JSON schema/esempio della forma comune (albero, nodi, struttura campi,
      tipi dato, attributi profilo-dipendenti, data di validita') — depende da
      T022, T027
- [x] T029 [US2] Endpoint `POST /configurazione/tipi-documento/{codice}/schema-discovery`
      (genera nuova versione) e `GET .../schema-discovery/{versione}` (esporta,
      FR-007), protetti dal ruolo FR-012 (T014)
- [x] T030 [US2] Evento audit di generazione/esportazione

**Checkpoint**: User Story 1+2 funzionanti — un tipo documento puo' essere definito e il suo contratto generato e consegnato, anche senza ancora registrare un endpoint.

---

## Phase 5: User Story 3 - Registrare l'endpoint e attivare l'integrazione (Priority: P1)

**Goal**: registrare l'URL fornito dal team esterno, verificarne la conformita' allo schema generato, portare il tipo documento a "connesso".

**Independent Test**: un endpoint di prova conforme porta lo stato a "connesso"; uno non conforme o irraggiungibile resta "non connesso" con errore esplicito.

### Tests for User Story 3

- [x] T031 (contratto `configurazione-cataloghi-api.openapi.yaml` validato da `tests/configurazione/test_integration_contract.py` e `test_contract_foundation.py`, piu' `test_versioned_admin_documentation_available`; il file indicato nel task non esiste, la copertura vive nei contract test esistenti) [P] [US3] Contract test per registrazione/verifica endpoint in
      `backend/tests/configurazione/contract/test_endpoint_integrazione_api.py`
- [x] T032 (`test_verify_end_to_end_connects_against_a_real_server`) [P] [US3] Integration test: endpoint conforme -> stato `CONNESSO`
      (Acceptance Scenario 1)
- [x] T033 (`test_verify_maps_unreachable_and_non_conformant_responses` piu' `tests/discovery/test_discovery.py::test_invalid_structure_is_functional_error`; le soglie fini restano ASSUNTA_PROVVISORIA come da nota) [P] [US3] Integration test: endpoint con forma non conforme allo
      schema comune (attributi obbligatori mancanti, tipi dato errati, nodo non
      valido) -> stato `ERRORE`, mai `CONNESSO` (Acceptance Scenario 2). Un
      endpoint con valori reali diversi dagli esempi ma conforme alla forma
      comune deve invece restare valido. *(nota: la soglia esatta errore vs
      avviso per metadati non attesi resta `ASSUNTA_PROVVISORIA` su
      `DEC-001-VERSIONING-RIFERIMENTI-ESTERNI`; questo test copre solo il caso
      gia' deciso — forma non valida = errore, non silenziosamente accettata —
      non le soglie fini)*
- [x] T034 (`test_verify_maps_unreachable_and_non_conformant_responses`) [P] [US3] Integration test: endpoint irraggiungibile in fase di
      registrazione -> stato `ERRORE` con messaggio esplicito, non stato
      ambiguo (Edge Case)
- [x] T035 (`tests/builder/test_integrazioni_manager.py::test_transport_failure_maps_to_502_not_503` e `test_non_conformant_shape_maps_to_502`: 502 `DISCOVERY_NON_DISPONIBILE`, mai lista vuota) [P] [US3] Integration test: endpoint irraggiungibile durante la
      *creazione di un modello* (non la registrazione) -> `PortaDiscovery`
      solleva errore funzionale di connessione, mai un menu vuoto silenzioso
      (Acceptance Scenario 3) — test diretto contro `AdapterHTTP`/`PortaDiscovery`
      (T009-T012), indipendente dal builder `002` non ancora implementato
- [ ] T036 RINVIATO con FR-010 fuori dall'incremento FR-016: nel runtime corrente l'assenza di URL produce `DISCOVERY_NON_CONFIGURATA`, non self-service. Non riaprire finche' FR-010 non rientra in scope. [P] [US3] Integration test: tipo documento self-service, nessuna
      riga `EndpointIntegrazione`, utilizzabile subito dopo US1 (Acceptance
      Scenario 4, SC-003)
- [x] T037 (`test_renaming_preserves_connection_but_changing_url_requires_reverification` e `test_removing_the_url_deletes_the_endpoint_row`: dopo il pivot FR-017 la verifica e' legata a URL/revisione dell'integrazione, non allo schema del tipo documento; `richiede_riverifica` riporta lo stato a DEFINITO) [P] [US3] Integration test: ridefinizione struttura dopo
      `CONNESSO` riporta lo stato a `DEFINITO` finche' non c'e' un nuovo test
      riuscito contro la nuova versione dello schema (state transition,
      `data-model.md`)

### Implementation for User Story 3

- [x] T038 (`repository.endpoint`, con lock) [US3] Repository `EndpointIntegrazione` in
      `backend/app/configurazione/repository.py`
- [x] T039 (`IntegrazioniService.verifica`: allowlist di egress, revisione ottimistica, tentativo con scadenza contro verifiche concorrenti) [US3] Service di test di connessione: chiama `AdapterHTTP` (T012)
      contro l'URL registrato, valida la forma della risposta contro lo
      `SchemaDiscoveryGenerato` corrente (T027), senza pretendere che i valori
      reali coincidano con gli esempi, e aggiorna `stato`/`esito_ultimo_test`
      — depende da T012, T027, T038
- [x] T040 SUPERATO nella forma: dopo FR-017 l'endpoint e' dell'integrazione, non del tipo documento. Rotte reali `PUT /configurazione/integrazioni/{id}` (registra) e `POST /configurazione/integrazioni/{id}/verifica` (ri-testa), protette da `require_admin`. [US3] Endpoint `POST /configurazione/tipi-documento/{codice}/endpoint-integrazione`
      (registra + testa) e `POST .../endpoint-integrazione/verifica` (ri-testa),
      protetti dal ruolo FR-012 (T014)
- [x] T041 (`discovery_per_tipo` in `app/discovery/configuration.py` solleva `INTEGRAZIONE_NON_CONNESSA` se lo stato non e' CONNESSO, senza interrogare l'adapter) [US3] Collegare `PortaDiscovery.catalogo_discovery` allo stato
      `EndpointIntegrazione.stato`: un tipo documento non `CONNESSO` (e non
      self-service) MUST rifiutare la richiesta con errore esplicito invece di
      interrogare l'adapter (FR-009) — depende da T009, T038
- [x] T042 (`AuditEventoIntegrazione`: INTEGRAZIONE_CONFIGURATA, TIPO_ASSOCIATO ed esiti di verifica) [US3] Evento audit di registrazione/test/ri-verifica

**Checkpoint**: User Story 1-3 (tutte P1) complete — il flusso di onboarding end-to-end funziona per un tipo documento integrato o self-service.

---

## Phase 6: User Story 4 - Vedere lo stato di connessione nella dashboard (Priority: P2)

**Goal**: vista aggregata dello stato di ogni tipo documento configurato.

**Independent Test**: la dashboard mostra correttamente definito/connesso/errore per tipi documento in stati diversi.

### Tests for User Story 4

- [x] T043 [P] [US4] Contract test per la vista dashboard in
      `backend/tests/configurazione/contract/test_dashboard_stato_api.py`
- [x] T044 [P] [US4] Integration test: stato corretto per tipi documento in
      stati diversi (Acceptance Scenario 1)

### Implementation for User Story 4

- [x] T045 [US4] Endpoint `GET /configurazione/tipi-documento` (vista
      amministrativa aggregata con stato ed esito ultimo test) in
      `backend/app/configurazione/api.py` — endpoint interno, non il sostituto
      della `listTipiDocumento` GEBAN-facing ritirata (`DEC-001-RITIRO-
      ENDPOINT-CLASSIFICAZIONE`): quella non aveva un pubblico interno, questa
      si', sono contratti diversi nonostante il nome simile
- [x] T046 [US4] Query aggregata in `backend/app/configurazione/repository.py`
      (join `TipoDocumento` + `EndpointIntegrazione` + ultima
      `SchemaDiscoveryGenerato`) — depende da T038, T027

**Checkpoint**: tutte le user story funzionanti indipendentemente.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [x] T047 (2026-09-22: contratto allineato all'implementazione; trovata e corretta una difformita' reale nel manifest di qualita', che dichiarava due API ritirate e ometteva `POST /documenti/genera`, piu' un nuovo contract test che impedisce il ripetersi silenzioso) [P] Verificare che
      `contracts/configurazione-cataloghi-api.openapi.yaml` resti allineato
      all'implementazione effettiva e agli esempi success/error gia' definiti
      in T002 per FR-001..FR-009
- [x] T048 [P] Verificare Swagger/ReDoc locale per il nuovo contratto
      (Costituzione, principio VI)
- [x] T049 (2026-09-22: `quickstart.md` scritto sull'esito di un test reale, `tests/configurazione/test_onboarding_contratti.py`, con un tipo CONTRATTO_APPALTO estraneo al dominio dei bandi: definizione -> schema -> esportazione -> endpoint CONNESSO su server HTTP vero) [P] Scrivere `quickstart.md`: scenario end-to-end con una fixture
      tipo-Contratti (diversa da `BANDO_CONCORSO`, per dimostrare che il motore
      e' generico — vedi conversazione 2026-09-15), definizione -> generazione
      schema -> registrazione endpoint mock (T013) -> stato `CONNESSO`
- [x] T050 (2026-09-22: T108 risultava gia' eseguito nel codice e nel contratto; verificata l'assenza di consumatori residui e chiuso in `001/tasks.md`) Eseguire `specs/001-catalogo-contratto-geban/tasks.md` T108 (ritiro
      delle tre API di classificazione legacy) — solo ora sbloccato, come da
      `plan.md` Dependencies; non eseguire T108 prima che T029 (esportazione
      schema) sia funzionante
- [x] T051 (2026-09-22: stato US1-US3 aggiornato, pivot FR-017 spiegato, chiusura di T108 riportata anche nella riga di `001`) Aggiornare `docs/project-map.md` con lo stato effettivamente
      implementato di questa spec
- [x] T052 (2026-09-22: 319 passati, 12 esclusi, su PostgreSQL reale; esiti in `quickstart.md`) Eseguire la suite pytest completa su Postgres reale (non mock) e
      registrare l'esito in `quickstart.md`

---

## Dependencies & Execution Order

### Riallineamento discovery e verifica variazioni (2026-09-17)

- [x] T053 *(2026-09-17: DTO ricorsivi, validazione e test dedicati)*
      Progettare DTO ricorsivi e `PortaDiscovery.catalogo_discovery`
      secondo `data-model.md`; aggiungere test su profondita' variabile,
      figli/campi esclusivi, codici duplicati fra fratelli e ricerca per percorso.
      T009 e' completata solo nella forma storica, non soddisfa questa estensione.
      Prerequisito di T012/T041 e T054.
- [x] T054 *(2026-09-17: nuovo metodo canonico e metodi legacy dell'adapter
      locale mantenuti; test di regressione su Postgres reale)*
      Evolvere porta e adapter locale mantenendo i consumatori esistenti
      funzionanti; documentare compatibilita' dei metodi storici, test di regressione
      builder su Postgres reale. Nessun parser HTTP a livelli fissi.
- [ ] T055 [FR-014] Progettare persistenza per versione modello e migration
      dei metadati di firma/dipendenze/esito; definire algoritmo versionato,
      normalizzazione e matrice blocco/avviso, compresi nuovi obbligatori,
      attributi usati e campo opzionale necessario al modello. Aggiornare
      contratto amministrativo prima di esporre esiti runtime.
- [ ] T056 [FR-014] Implementare firma SHA-256 e confronto con il contratto
      della versione modello; testare ordinamenti, timestamp variabili,
      ramo scomparso, nuovi obbligatori, opzionali non usati e variazioni di
      tipo/vincoli. Dipende da T053-T055 e dal contratto allineato.
- [ ] T057 [FR-015] Implementare runner configurabile con una risposta per
      integrazione/ciclo, indice temporaneo in memoria, no sovrapposizioni,
      timeout/retry limitati ed esito NON_VERIFICABILE per errori esterni.
      Testare che non scarichi il catalogo per ogni modello. Dipende da T012/T056.
- [ ] T058 [FR-015] Esporre data/esito/motivi della verifica nella dashboard,
      auditare transizioni e notificare cambiamenti di esito senza duplicati.
      Dipende da T055-T057 e T045; mantenere separata la pubblicazione.
- [x] T059 [P] Riallineare il riferimento documentale alla porta condivisa in
      `specs/002-builder-modelli/data-model.md` alla porta canonica della 010;
      rilievo MEDIUM della review indipendente 2026-09-17, non nuovo task
      implementativo del builder 002.
- [x] T060 [P] Consolidare `DISCOVERY_NON_CONFORME` e
      `DISCOVERY_NON_DISPONIBILE` in `app.common.errors.ErrorCode`, mantenendo
      nomi e status pubblici invariati; rilievo MEDIUM della review 2026-09-17.

Questi task devono precedere il checkpoint finale T051/T052. T055 chiude
le soglie fini di compatibilita' prima di T056; il controllo di generazione
rimane da pianificare nella spec 004. T050, appartenente alla 001, non e'
autorizzato implicitamente dal completamento della 010: rispettare il cambio
di feature previsto da AGENTS.md.

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

- T005-T007 (migration ancora aperte) possono girare in parallelo dopo T001-T002.
- T010, T011 possono girare in parallelo dopo T009.
- T015-T018, T024-T026, T031-T037, T043-T044 (test di ciascuna user story)
  possono girare in parallelo fra loro all'interno della stessa fase.
- T047-T049 possono girare in parallelo dopo che il comportamento e' stabile.

## Parallel Example: User Story 3

```text
Task: T032 Endpoint conforme -> CONNESSO
Task: T033 Endpoint con forma non conforme -> ERRORE
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

### Incremento implementativo 2026-09-17

Perimetro: T011-T013 e T053-T054, infrastruttura discovery condivisa.
Il builder esistente usa ancora i metodi locali legacy dell'AdapterLocale:
T041 e l'onboarding US1-US4 non sono completati. Non si dichiara pronta la pagina
per creare modelli dai dati live GEBAN. Non si modificano generazione ufficiale,
regole di unicita' delle varianti o versioni pubblicate.
T001-T002/T005-T008/T014 e tutte le user story non completate sono esplicitamente
SOSPESI per questo incremento, da riprendere col flusso Spec Kit.
T055-T058 sono SOSPESI finche' persistenza e policy fini sono progettate;
la firma approvata non e' ancora implementata.
Il rischio residuo e' l'assenza di selezione dell'adapter registrato e di controllo
dei modelli esistenti: l'incremento non abilita la nuova integrazione in produzione.

Verifica: suite finale non-e2e 189 passati, 12 e2e esclusi; discovery + builder
48 passati su HTTP locale/Postgres reale. Il client reale
ha letto 10 tipologie, 65 foglie e 16 campi per TD/RICERCATORE.
Revisione indipendente `adev review`: PASS il 2026-09-17, report in
`.adev/last-review.yml`. Nessun rilievo HIGH/CRITICAL; due MEDIUM tracciati
in T059/T060. Checklist requisiti assente: rilievo LOW da recuperare prima
del completamento della feature. La PASS riguarda questo incremento,
non dichiara completata la feature 010 o le altre feature del repository.

### Decisione registrata 2026-09-17 - lavoro da pianificare

La verifica autonoma delle variazioni tramite firma SHA-256 del ramo e confronto
con il contratto del modello e' approvata e descritta in `spec.md`.
Questo non marca completata alcuna implementazione. Al prossimo riallineamento
di plan/data-model/tasks occorre dettagliare persistenza della firma per versione,
normalizzazione, confronto compatibilita', runner con una chiamata per integrazione,
esiti non verificabili e test su modifiche rilevanti/non rilevanti.
Il controllo prima della generazione va coordinato con la spec 004 senza iniziare
qui task appartenenti a un'altra feature. Frequenza e soglie blocco/avviso
restano aperte; non si dichiara risolta tutta DEC-001-VERSIONING-RIFERIMENTI-ESTERNI.

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

## Phase 8: Convergence - dismissione catalogo esterno locale (2026-09-17)

La decisione FR-016 sostituisce il precedente vincolo T050/T108 per il ritiro
delle API legacy. Per questo incremento T004/T009/T010/T054 sono storici,
non architettura da conservare. US1-US4, firme e runner restano sospesi;
non si dichiara completato T041 con una configurazione operativa dell'URL.

- [x] T061 [FR-016] Allineare il contratto builder alla struttura ricorsiva
      e alla selezione tramite percorso generico prima delle modifiche runtime.
- [x] T062 [FR-016] Migration 0009: migrare riferimenti dei modelli a codici
      e percorso, eliminare FK e tabelle del catalogo esterno locale e il registro
      globale legacy. Preservare identificativi, versioni, campi e audit.
- [x] T063 [FR-016] Eliminare ORM/repository/API/DTO legacy e AdapterLocale;
      conservare ricerca dei soli modelli GEMODO e contratti delle loro versioni.
- [x] T064 [FR-016] Collegare il builder a discovery HTTP tramite URL esplicito
      configurato per tipo documento, senza seed/fallback locale; selezionare
      foglie per percorso e usare esclusivamente i loro campi nelle versioni.
- [x] T065 [FR-016] Testare su Postgres reale preservazione dei dati migrati,
      assenza delle tabelle ritirate e flusso HTTP -> modello -> pubblicazione;
      coprire profondita' variabile, ambiguita', errori e isolamento dei rami.
- [x] T066 [FR-016] Documentare configurazione, migrazione non reversibile
      senza backup, ritiro API e stato residuo; suite deterministica e review
      indipendente prima di dichiarare conclusa questa dismissione.
      Suite: 206 test passati, 12 e2e esclusi. Review indipendente PASS:
      `.adev/reviews/review-20260917T113248Z.json`. Nessuna migrazione su DB
      operativo. Rilievi documentali residui tracciati in T072; tooling T071.

## Phase 9: Convergence - rilievi review indipendente

- [x] T067 [FR-016] Riallineare spec/task/research/quickstart 001, matrice
      copertura, catalogo errori e fixture mock alla ricerca v0.4: filtri sui
      modelli proprietari, lista vuota senza corrispondenze, nessuna allowlist
      locale. Non dichiarare invariata la vecchia semantica dell'errore tipologia.
- [x] T068 [FR-016] Esplicitare in FR-010, US3 scenario 4 e SC-003 il rinvio
      self-service fuori dall'incremento di dismissione; progettare la sorgente
      proprietaria distinta dal catalogo esterno prima dei task US1/T036.
- [x] T069 [FR-016] Evitare che la cache serializzi HTTP per chiavi diverse;
      test di concorrenza, deduplicazione per chiave e sblocco su errore.
- [x] T070 [P] Checklist qualita' dei requisiti per il perimetro di dismissione.
- [ ] T071 [P] SOSPESO: il CLI adev censisce documenti markdown ma non YAML
      OpenAPI; segnalare il gap di tracking per 001/010 e pianificare correzione
      del tooling senza modificare globalmente il CLI o falsificare il ledger.
      Rilievo MEDIUM, non bloccante secondo la policy; review esplicita del diff
      dei contratti resta obbligatoria anche quando needs_review non cambia.

- [x] T072 [P] Riallineare i data-model storici 001/002 al ritiro FR-016,
      rendendo esplicita la prevalenza del modello canonico 010 e la natura
      storica delle vecchie entita'/relazioni; registrare Angular con Design
      Angular Kit per il frontend futuro, senza avviare task della spec 007.

## Phase 10: Ripresa fondazioni amministrative (2026-09-17)

Incremento autorizzato: T005-T008/T014. Migration 0010 introduce solo
configurazione proprietaria ed esempi, senza seed esterni o nuovi fallback.
T001/T002 sono IN CORSO; T019 e US1-US4 non sono dichiarati completati.
T055-T058 restano sospesi sulla classificazione delle differenze, richiesta
al product owner. Nessuna migrazione viene eseguita sul DB operativo.

- [ ] T073 [P] Verificare fondazioni con PostgreSQL reale (vincoli,
      isolamento per tipo, upgrade/downgrade 0010), sicurezza 401/403/admin,
      regressioni complete e review indipendente; documentare esito e residui.
      IN CORSO: 8 test mirati passati su PostgreSQL reale; suite finale
      214 passati, 12 e2e esclusi, nessuno saltato (24.17s).
      Review indipendente bloccata dalla policy di esecuzione:
      invio del repository/diff a Claude richiede autorizzazione esplicita
      dell'utente. Il PASS precedente copre solo FR-016, non questo incremento.
      AGGIORNAMENTO 2026-09-22: la parte tecnica e' verificata. Suite completa
      319 passati, 12 e2e esclusi, su PostgreSQL reale. Giro migrazioni provato
      davvero su un database dedicato: `upgrade head` -> `downgrade 0009` ->
      `upgrade head` pulito. `downgrade base` si ferma a 0009 con un errore
      esplicito e voluto ("rollback richiede ripristino del backup pre-0009",
      FR-016): il rifiuto e' atomico, il database resta a head. Sicurezza
      coperta da `test_admin_routes_reject_non_admin_principals`. Resta aperto
      solo per la review indipendente, che l'utente ha rinviato a software
      completato.
      Aggiornamento successivo: utente ha rinviato esplicitamente review e
      soglie hash/runner. Suite finale US1/US2: 221 passati, 12 e2e esclusi,
      nessuno saltato; 15 mirati. Non reiterare richiesta di review esterna.

## Phase 11: Convergence - persistenza proprietaria US1/US2

- [x] T074 [US1] FR-001..FR-005/FR-013 (missing): progettare e migrare
      `definizione_struttura` versionata con JSON proprietario per tipo;
      collegare gli schemi generati alla revisione usata. Non salvare discovery
      esterni, non riusare categorie/tipologie legacy. Prerequisito di T019.
- [x] T075 [US1] Costituzione V/T023/T030 (missing): introdurre audit
      amministrativo per tipo documento, separato dall'audit che richiede
      un modello; creazione/modifica/generazione/export in transazioni atomiche.
- [ ] T076 [US1] US1/US2 (partial): verificare contratto/runtime, revisioni,
      incompletezza, riferimenti attributi, isolamento e regressioni; pubblicare
      Swagger/ReDoc ed esempi operativi. Review esterna rinviata su richiesta
      dell'utente: non dichiarare completata la feature senza quality gate.
      IN CORSO: implementazione e controlli locali presenti in
      `tests/configurazione/test_onboarding.py` e `test_contract_foundation.py`
      (coprono anche T015/T016/T018/T024-T026/T043-T044). Review rinviata.
      Verifica locale finale: 221 passati, 12 e2e esclusi, nessuno saltato
      (26.35s); 15 test mirati amministrativi. `git diff --check` pulito.
      AGGIORNAMENTO 2026-09-22: contratto e runtime riverificati (319 passati),
      con una difformita' reale trovata e corretta nel manifest di qualita'
      (T047) ed esempi operativi ora in `quickstart.md` su un tipo estraneo al
      dominio dei bandi. Resta aperto solo per la review indipendente rinviata.

### Stato Corrente Prevalente Sulle Note Storiche

US1/US2 backend e lettura aggregata dashboard implementati. Una revisione
d'esempio viene salvata per tipo; export storico immutato e audit atomico.
T017 resta parziale sulla risoluzione live nel builder, T036 self-service
rinviato, T031-T042 connessione e selezione registrata ancora da implementare.
Il backend builder continua a usare URL operativi espliciti; non si dichiara
completato T041. Il frontend Angular/Design Angular Kit resta nella spec 007.
Hash/runner T055-T058 e review esterna sono rinviati dall'utente.
T073/T076 restano IN CORSO sul quality gate; nessuna richiesta di invio a
Claude viene reiterata in questo incremento. La feature 010 non e' completa.

## Phase 12: Integrazione Per Software E Handoff MVP

Prevale ADR 0002: endpoint per software, non per tipo. T031-T046 vanno letti
nel nuovo perimetro; i passaggi che richiedevano uno schema d'esempio per
connettere sono superati da T078-T084. Le spunte storiche documentano incrementi
precedenti, non certificano il nuovo flusso. US1/US2 rimangono strumenti opzionali.
Feature attiva invariata; nessun task applicativo di altre spec viene avviato.

- [x] T077 Formalizzare ADR 0002, 010 FR-017..FR-021, piano e data-model:
      registro vuoto, contesto JWT, singolo URL per software, forma comune
      indipendente dagli esempi e PDF di test senza editor visuale.
- [x] T078 Definire `contracts/integrazioni-api.openapi.yaml` prima del runtime:
      CRUD/configurazione admin e verifica, letture manager filtrate, identita'
      sorgente, esiti/versioni, errori e compatibilita' delle API per tipo.
      Definire URL approvati/SSRF, autenticazione sorgente se richiesta,
      timeout/limiti e sanificazione; non pubblicare route non implementate.
      Contratto 0.1.0 e `contracts/integrazioni-policy.md` presenti;
      registro admin, letture manager, revisione/tentativo, egress deny-default,
      timeout e compatibilita' descritti. Validazione strutturale locale passata:
      YAML, 8 operazioni, 51 riferimenti, security e stato planned verificati;
      Validazione OpenAPI completa passata, riferimenti esterni inclusi.
      Sei test contrattuali passati (4 nuovi, 2 precedenti), esempi validati.
      Validatore aggiunto al gruppo dev e lockfile; nessun update di dipendenze
      preesistenti. Compatibilita' legacy e nuove route additive nella policy;
      adeguamento contratto admin precedente richiesto in T079 prima di codici
      duplicati. Nessun endpoint di questo contratto operativo.
- [x] T079 Migrare Integrazione software e proprieta' Endpoint, revisione di
      configurazione, identita' tipo scoped per integrazione e audit autonomo.
      Preservare modelli/versioni/ID pubblici/campi/sezioni/generazioni/audit;
      niente GEBAN automatico da seed/env/token. Legacy associato esplicitamente
      con nuova verifica; test upgrade/downgrade e vincoli PostgreSQL.
      Prima di implementare: definire associazione legacy, archivio degli esiti
      vecchi e downgrade senza ricostruire cataloghi esterni; adeguare contratto
      admin e repository per identita' tipo scoped prima di codici duplicati.
      IN CORSO: primo incremento 0012 implementato per registro/audit e FK
      ownership nullable senza backfill; unicita' globale preservata fino al
      secondo incremento endpoint/namespace. Downgrade rifiutato con dati
      registro/audit o tipi associati. Nessuna associazione implicita attiva.
      Test mirato PostgreSQL reale passato: vincoli, upgrade/downgrade,
      registro vuoto con tipi legacy e preservazione integrale delle righe
      modello/versione, UUID e public_id. Nessuna migrazione sul DB operativo.
      Regressioni finali: 226 passati, 12 e2e esclusi, nessuno saltato (28.82s).
      Review indipendente rinviata come richiesto; feature non completa.
      Incremento 0013 concluso: endpoint software senza FK esempi, archivio
      storico inerte senza ORM/fallback, namespace scoped e legacy null univoco.
      Associazione interna admin esplicita/auditata, senza trasferimento owner;
      niente connessione automatica. Codici ambigui rifiutati da repository,
      catalogo e builder; lista catalogo vincolata al tipo UUID risolto.
      Contratti admin/builder/catalogo aggiornati con 409 SORGENTE_AMBIGUA.
      Test PostgreSQL upgrade/downgrade/storico/unicita'/associazione passati;
      nessuna migrazione sul DB operativo. Esposizione HTTP resta T081.
- [x] T080 Estendere PortaDiscovery/AdapterHTTP alla mappa intera multi-tipo;
      validare tutte le radici, cache/indici solo RAM per sorgente e revisione.
      Paginazione trasparente non equivale a modalita' PER_NODI.
      Implementati MappaDiscovery e lettura integrale condivisa da navigazione
      per tipo, HAL multi-tipo e validazione di tutte le radici; chiavi JSON
      duplicate rifiutate. Cache namespace/sorgente/revisione, copie isolate,
      niente salvataggi DB. T081/T082 devono passare lo scope da registro DB.
      Test discovery/configurazione: 72 passati, nessuno saltato (12.44s).
- [x] T081 Implementare registro/configurazione/verifica admin del contratto
      T078; successo riferito a revisione corrente e forma comune, non esempio.
      URL modificato richiede verifica; test su revisione superata non connette.
      Implementati `POST/GET /configurazione/integrazioni`, `GET/PUT .../{id}`,
      `POST .../{id}/verifica` (`backend/app/configurazione/{api,service}.py`,
      nuovo `IntegrazioniService`). Configurazione con controllo ottimistico su
      `revisione` (409 REVISIONE_SUPERATA); cambio URL/timeout invalida stato a
      DEFINITO e cancella l'esito precedente, cambio solo nome conserva
      CONNESSO/ERRORE; URL null elimina la riga `endpoint_integrazione`.
      Verifica sincrona senza cache (`AdapterHTTP(..., forza_aggiornamento=True)`
      su T080), su tutta la mappa multi-tipo; prenotazione atomica del
      tentativo (`tentativo_id`/`tentativo_scadenza`) rilasciata prima della
      chiamata HTTP (nessuna transazione DB aperta durante l'I/O) e riconfermata
      dopo, applicando il risultato solo se tentativo e revisione sono ancora
      correnti (altrimenti 409 REVISIONE_SUPERATA senza cambiare stato); un
      tentativo scaduto non blocca una nuova verifica. Errori di trasporto/
      timeout mappati a esito NON_RAGGIUNGIBILE, forma non conforme a
      NON_CONFORME, entrambi a stato ERRORE.
      Nuovo `backend/app/discovery/egress.py`: destinazione approvata solo se
      nell'allowlist di deployment (`GEMODO_INTEGRAZIONI_ALLOWLIST`, vuota di
      default) e con IP risolti pubblici; un'origine anche in
      `GEMODO_INTEGRAZIONI_ALLOWLIST_PRIVATO` e' l'eccezione di deployment
      esplicita che ammette HTTP e IP privati/loopback (fixture di test).
      Verifica applicata sia in configurazione sia immediatamente prima della
      chiamata HTTP di verifica; NON implementa il pinning della connessione
      all'IP risolto (protezione da DNS rebinding) ne' la matrice avversariale
      completa (redirect, HAL ciclico, rebinding) — quello resta T084.
      13 nuovi test reali in `backend/tests/configurazione/test_integrazioni_admin.py`
      (Postgres reale via Testcontainers, server HTTP locale reale per la
      verifica, nessun mock della logica di dominio); regressione locale
      `pytest -m "not e2e"`: 248 passati (12 e2e esclusi) al momento di questo
      task; non ancora pubblicato in Swagger/ReDoc a quel punto (T082/T083
      completati subito dopo nella stessa sessione, vedi sotto).
- [x] T082 Sostituire resolver operativo da ambiente con integrazioni CONNESSE
      registrate; rimuovere bypass `GEMODO_DISCOVERY_ENDPOINTS`, senza fallback
      locale o import automatico. Aggiornare documentazione operativa e test.
      `backend/app/discovery/configuration.py` riscritto: `discovery_per_tipo`
      ora prende `(db, tipo)`, risolve `tipo.integrazione_id` sul registro
      (`EndpointIntegrazione.stato == 'CONNESSO'`), nessuna lettura di
      `os.environ`. Nessuna integrazione -> `DISCOVERY_NON_CONFIGURATA` (503,
      come il comportamento legacy); integrazione non `CONNESSO` ->
      `INTEGRAZIONE_NON_CONNESSA` (409, nuovo codice dal contratto T078).
      Cache RAM condivisa (`CacheDiscovery`) con scope `integrazione:{id}:
      revisione:{revisione_verificata}`, cosi' una riverifica invalida
      implicitamente le voci precedenti. `backend/app/builder/service.py`
      aggiornato per passare il `TipoDocumento` gia' risolto invece dello
      scartare e richiedere solo il codice.
      Migrato `backend/tests/builder/test_builder_flow_api.py`: fixture
      `integrazione_connessa` crea/rimuove una `Integrazione`+
      `EndpointIntegrazione` CONNESSO reale (Postgres) puntata al server HTTP
      locale di test, sostituendo `GEMODO_DISCOVERY_ENDPOINTS`; il test
      `test_missing_or_invalid_config_does_not_fall_back_to_seed` (5 varianti
      dell'env var) sostituito da due test mirati sul nuovo registro (nessuna
      integrazione -> 503; integrazione DEFINITO/ERRORE -> 409), nessuna
      regressione sulle 13 asserzioni restanti del file (18 test, 18 passati).
      Documentazione operativa aggiornata (README.md, docs/project-map.md,
      specs/002-builder-modelli/data-model.md, infra/local/compose.yaml,
      docker-compose.coolify.yml): rimosso `GEMODO_DISCOVERY_ENDPOINTS`,
      introdotte `GEMODO_INTEGRAZIONI_ALLOWLIST`/`_PRIVATO` (T081) al suo posto
      nei compose file. `specs/010-.../fondazioni-amministrative.md` non
      toccato: e' nota storica esplicita, non stato corrente.
- [x] T083 Implementare letture manager: integrazioni autorizzate, radici,
      navigazione ricorsiva e campi foglia; verificare contesto prima dell'HTTP.
      Adeguare touchpoint condivisi e riferimenti sorgente senza avviare task
      di creazione modello/PDF/frontend appartenenti alle altre spec.
      Nuovo `backend/app/builder/integrazioni_service.py`
      (`IntegrazioniManagerService`) + route in `backend/app/builder/api.py`:
      `GET /builder/integrazioni`, `GET .../{ id }/tipi-documento`,
      `GET .../{id}/tipi-documento/{codice}/struttura`. Autorizzazione per
      singolo contesto (mai `principal.ruoli` appiattito): nuovo
      `contesti_con_permesso` in `backend/app/common/security.py`, fattorizzato
      da `verify_scrittura_su_contesto` senza cambiarne il comportamento.
      Integrazione non trovata o contesto non autorizzato -> stessa risposta
      404 `RISORSA_NON_TROVATA` (nessuna differenza osservabile, l'esistenza di
      un'integrazione di un altro contesto non e' mai rivelata); non `CONNESSO`
      -> 409 `INTEGRAZIONE_NON_CONNESSA`; il contesto e' verificato prima di
      costruire l'`AdapterHTTP`, mai dopo. Errori di trasporto/conformita'
      rimappati esplicitamente a 502 e timeout a 504 (le route `/builder/`
      precedenti restano su 503, semantica invariata) — vedi
      `IntegrazioniManagerService._mappa`. Radici = chiavi della mappa
      multi-tipo (`sorted(mappa.cataloghi)`), non i nodi di un singolo
      catalogo; "nessun import DB" rispettato (solo lettura live via
      `AdapterHTTP`, cache in RAM). 9 nuovi test reali in
      `backend/tests/builder/test_integrazioni_manager.py` (Postgres +
      server HTTP locale reali), incl. prova diretta che un contesto non
      autorizzato non genera mai la richiesta HTTP (`requests == []`).
      Contratto `integrazioni-api.openapi.yaml`: rimosso
      `x-implementation-status: planned` (tutte le 8 operazioni sono ora
      reali) e pubblicato in Swagger/ReDoc (`/docs/integrazioni`,
      `/redoc/integrazioni`, voce aggiunta a
      `backend/app/quality/openapi_docs.py`); descrizione aggiornata per
      riflettere T081-T083 fatti e T084 aperto.
      `backend/tests/configurazione/test_integration_contract.py` aggiornato
      di conseguenza (asserisce l'assenza del flag, non piu' `"planned"`).
      Regressione locale `pytest -m "not e2e"`: 256 passati, 12 esclusi.
      **Ancora aperto**: T084 (matrice avversaria SSRF/rebinding/concorrenza),
      T047/T049-T052/T055-058/T071/T073/T076 (polish/hardening gia' annotati
      sopra).
- [x] T084 *(2026-09-17/18)* Testare registro vuoto anche con seed/env/token, due
      tipi su un URL, una radice invalida, codici uguali in sorgenti diverse, token
      multicontesto, permessi non appiattiti, concorrenza modifica URL/verifica,
      isolamento dei metadati admin, SSRF/limiti/errori e regressioni
      PostgreSQL/HTTP reali.
      La maggior parte della matrice era gia' reale e verificata da T078-T083:
      registro vuoto/nessun seed (T079, "registro vuoto con tipi legacy"), due tipi
      su un URL (`test_tipi_documento_and_struttura_reflect_the_live_multi_type_map`),
      radice invalida (parametrizzazione `test_invalid_structure_is_functional_error`
      + `test_pagination_rejects_invalid_or_unsafe_pages`), codici ambigui fra
      sorgenti diverse (`SORGENTE_AMBIGUA`, `test_software_endpoint_migration.py`),
      redirect/downgrade/HAL ciclico/cross-origin gia' rifiutati e testati
      (`follow_redirects=False` per-request + verifica origine su ogni `next_href`).
      Trovati e chiusi in questo incremento i due gap reali rimasti:
      (1) `discovery_per_tipo` (T082) non ri-validava mai la destinazione contro
      l'allowlist dopo la connessione iniziale - una volta `CONNESSO`, restava
      valido per sempre anche se l'allowlist di deployment veniva ristretta in
      seguito; ora rivalida su ogni risoluzione (`backend/app/discovery/
      configuration.py`), nuovo test
      `test_connected_integration_falling_out_of_the_allowlist_is_denied_on_next_read`
      in `backend/tests/builder/test_builder_flow_api.py` (ha anche richiesto
      correggere il fixture `integrazione_connessa`, che inseriva la riga
      `CONNESSO` via SQL diretto senza mai passare dall'allowlist come farebbe una
      verifica reale); (2) nessun test provava la vera race fra una verifica in
      volo e una riconfigurazione concorrente con thread reali (solo interleaving
      simulato via UPDATE SQL pre-seeded) - nuovo
      `test_reconfiguring_url_while_a_verify_is_in_flight_wins_the_race` in
      `backend/tests/configurazione/test_integrazioni_admin.py` (server HTTP reale
      con blocco via `threading.Event`, non sleep) prova che il ricontrollo
      post-I/O di tentativo_id/revisione impedisce davvero alla verifica stale di
      sovrascrivere la riconfigurazione concorrente. Aggiunto anche
      `test_multicontext_token_does_not_leak_permission_across_contexts` in
      `backend/tests/builder/test_integrazioni_manager.py` (il fixture
      `manager_client` esistente copriva solo un token a contesto singolo).
      **Residuo dichiarato, non implementato**: il vero pinning della connessione
      all'IP risolto (protezione da DNS rebinding fra il check di approvazione e
      la richiesta HTTP reale) resta fuori scope per questo MVP - richiederebbe un
      transport HTTP custom (SNI/Host separati dall'IP di connessione) non
      banale da verificare correttamente; accettato perche' l'URL e' configurato
      da un `GEMODO_ADMIN` fidato, non input arbitrario di un chiamante esterno.
      Suite completa su Postgres reale: 291 passati, 1 skip preesistente non
      collegato a questo task, 0 falliti.
- [x] T085 Propagare requisiti MVP alle spec owner 001..007 senza cambiare
      feature; registrare dipendenze e stato reale nel documento MVP.
- [x] T086 Verificare coerenza documentale locale, identificativi e link del
      nuovo perimetro; riportare residui contrattuali prima di implementare.
      Non sostituisce review indipendente T073/T076, rinviata dall'utente.
      Verificati identificativi FR/task senza duplicati e 9 link locali validi;
      `git diff --check` pulito. Residui: contratto T078 e policy extra 001
      FR-033 da pianificare prima dei rispettivi cambi runtime; migrazione
      e nuovi flussi non implementati in questo aggiornamento documentale.

- [x] T087 Registrare il gap di autorizzazione API consumatore nelle spec owner
      001 FR-034..FR-038 e 006 FR-014..FR-017, con accettazione mono/multicontesto,
      negazione sicura e protezione contro ID indovinati e payload falsificati.
      Handoff bloccante prima dell'uso operativo: aggiornare plan/contratti/tasks
      001/006 e implementare enforcement e test dopo cambio feature autorizzato.
      Nessun codice modificato; questo task completa la formalizzazione, non
      il controllo runtime. T078/T083/T084 devono rispettare tali requisiti.

- [x] T088 [T079] Implementare primo incremento 0012 del registro software,
      audit autonomo e FK ownership/contesto nullable, senza seed/backfill e
      senza rimuovere l'unicita' globale prima dell'adeguamento dei consumer.
      Test PostgreSQL reale passato; T079 resta IN CORSO su endpoint/namespace
      e associazione legacy. Non certifica API admin, manager o PDF disponibili.

## Riallineamento spunte US3 (2026-09-22)

Verificato sul codice prima di spuntare, non a memoria: 97 test passati fra
`tests/configurazione` e `tests/discovery` su Postgres reale, zero skip.
La User Story 3 era gia' implementata, ma sotto la forma introdotta dal pivot
FR-017 del 2026-09-17: l'endpoint appartiene all'Integrazione, non al
TipoDocumento. I task T038-T042 erano stati scritti prima di quel pivot e
descrivono rotte che non esistono piu'; la funzione c'e' tutta.

Copertura reale aggiuntiva non prevista dai task originali: revisione
ottimistica (`REVISIONE_SUPERATA`), allowlist di egress con rifiuto degli IP
privati dietro un host pubblico, verifica concorrente con tentativo a scadenza,
e la corsa fra riconfigurazione dell'URL e verifica in volo.

T036 resta aperto ma RINVIATO insieme a FR-010: non e' lavoro residuo di questo
incremento.
