# Tasks: Catalogo Modelli E Contratto Dati GEBAN

**Riallineamento 2026-09-17 (010 FR-016)**: catalogo esterno locale e API
classificazione ritirati. Goal/task del primo incremento sotto sono storico;
per FR-020 vale la ricerca v0.4 aggiornata nella spec: filtro senza
corrispondenze -> 200/modelli vuoti, non TIPOLOGIA_SOL_NON_VALIDA.
Task di rinomina tabelle del catalogo T080-T084 sono SUPERATI/SOSPESI.

**Input**: Design documents from `specs/001-catalogo-contratto-geban/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/geban-catalog-api.openapi.yaml`, `quickstart.md`

**Tests**: Included. The feature is contract-first and the plan requires pytest, httpx/FastAPI TestClient and Testcontainers PostgreSQL (or a real local PostgreSQL when Testcontainers/Docker is unavailable).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

**Regenerated 2026-07-29**: this file replaces the 2026-06-19 version to recepire the
decisions propagated from `009-fondamenta-mock-test-qualita` (tipologia GEBAN/SOL
validation, `lingua`/`bando_inglese` conditional requiredness) and to reconcile Setup
tasks with the backend skeleton `009` already created. See
`docs/decision-register.yaml` (`DEC-001-*`) and `docs/project-map.md` for context.

**Updated 2026-07-31**: the blocking decisions for `TASKS` on `001` were either
confirmed or explicitly suspended. The feature now includes minimum Keycloak JWT
protection for its operative APIs (`DEC-006-CONFINE-KEYCLOAK-GEMODO` confirmed):
issuer/JWKS, audience `gemodo-backend`, client `geban-backend` for GEBAN calls and
roles `DOCUMENTI_VIEWER` / `DOCUMENTI_GENERATORE`. Audit completo, profilo GEBAN
versionato and fine-grained authorization remain in `006`/later specs. Before starting
implementation, run the readiness gate for this spec:

```bash
cd backend
uv run python -c "
from pathlib import Path
from app.quality.readiness_gate import load_decision_register, valuta_readiness
from app.quality.schemas import FaseBloccante
decisioni = load_decision_register(Path('../docs/decision-register.yaml'))
esito = valuta_readiness(decisioni, fase_richiesta=FaseBloccante.TASKS, spec_target='specs/001-catalogo-contratto-geban')
print('pronto:', esito.pronto, [d.id for d in esito.blocchi])
"
```

Expected result after the 2026-07-31 clarification pass: `pronto: True` and no blocking
decisions for `specs/001-catalogo-contratto-geban`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Extend the FastAPI backend skeleton `009` already created; do not recreate
files that already exist.

- [x] T001 Add this feature's dependencies (`pyjwt[crypto]`, `httpx`, testcontainers
      if used) to the existing `backend/pyproject.toml` (created by `009` - extend, do
      not overwrite)
- [x] T002 Mount this feature's routers on the existing `app` instance in
      `backend/app/main.py` (created by `009` with the Swagger/ReDoc publishing router
      - add `app.include_router(...)` calls, do not recreate the file)
- [x] T003 Create settings module in `backend/app/core/settings.py` (new file inside the
      existing `backend/app/core/` package)
- [x] T004 Create database session module in `backend/app/db/session.py` (new file
      inside the existing `backend/app/db/` package)
- [x] T005 [P] Create catalog package under `backend/app/catalog/`
- [x] T006 [P] Create validation package under `backend/app/validation/`
- [x] T007 [P] Create common error and security package under `backend/app/common/`
- [x] T008 [P] Create `backend/tests/catalog/__init__.py`,
      `backend/tests/validation/__init__.py` and `backend/tests/common/__init__.py`
      (new subpackages; `backend/tests/support/` already exists from `009` - add
      fixtures there, do not recreate the package)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared data model, migrations, repositories and error envelope that all user stories depend on.

**CRITICAL**: No user story work can begin until this phase is complete.

- [x] T009 Create catalog schema migration in
      `backend/alembic/versions/0002_catalogo_modelli.py`, extending the `009` baseline
      (`0001_initial_schema.py`) rather than redefining `tipo_documento` /
      `categoria_documento` / `modello_documento` / `modello_versione` /
      `campo_modello` - add the columns/constraints this feature needs
      (`variante`, `data_inizio_validita`, `data_fine_validita`, `pubblicato_at`,
      `lingua` on campo, unique constraint per variante corrente) via `ALTER TABLE`
- [x] T010 Create `TipologiaBandoSOL` table migration in
      `backend/alembic/versions/0003_tipologia_bando_sol.py` (`codice`, `codice_sol`,
      `descrizione`, `attiva`) and FK `tipologia_bando_sol_id` (nullable) on
      `modello_documento`/`tipo_documento` per FR-020
- [x] T011 [P] Create `TipoDocumento` SQLAlchemy model in `backend/app/catalog/models.py`
- [x] T012 [P] Create `CategoriaDocumento` SQLAlchemy model in `backend/app/catalog/models.py`
- [x] T013 [P] Create `TipologiaBandoSOL` SQLAlchemy model in `backend/app/catalog/models.py`
- [x] T014 [P] Create `ModelloDocumento` SQLAlchemy model (with `variante`,
      `codice_tipologia` FK) in `backend/app/catalog/models.py`
- [x] T015 [P] Create `ModelloDocumentoVersione` SQLAlchemy model in `backend/app/catalog/models.py`
- [x] T016 [P] Create `ModelloCampoRichiesto` SQLAlchemy model, including `lingua`
      (`IT`/`EN`, default `IT`) in `backend/app/catalog/models.py`
- [x] T017 Create catalog repository functions in `backend/app/catalog/repository.py`
- [x] T018 Create common API error schemas in `backend/app/common/errors.py`
- [x] T019 Create FastAPI exception handlers in `backend/app/common/errors.py`
- [x] T020 Create catalog seed migration for demo data in
      `backend/alembic/versions/0004_seed_catalogo_demo.py`, loading the tipologie
      GEBAN/SOL and demo model already declared in
      `infra/local/postgres/seed-demo-catalog.yaml` (`009`) rather than hardcoding a
      second, divergent seed list
- [x] T021 Create Testcontainers PostgreSQL fixtures in
      `backend/tests/support/postgres.py`, with a documented fallback to a real local
      PostgreSQL connection (`DATABASE_URL` env var) when Docker/Testcontainers is
      unavailable, matching the approach already used by `009` (see
      `backend/alembic/README.md`)
- [x] T022 [P] Add Keycloak settings (`KEYCLOAK_ISSUER_URL`, `KEYCLOAK_AUDIENCE`,
      JWKS URL/cache TTL, mock-principal toggle) in `backend/app/core/settings.py`,
      aligned with `infra/local/keycloak/authorization-boundary.local.yaml`
- [x] T023 [P] Create security principal schemas and role constants for `geban-backend`,
      `DOCUMENTI_VIEWER` and `DOCUMENTI_GENERATORE` in `backend/app/common/security.py`
- [x] T024 [P] Create JWT/security test helpers for signed tokens, wrong audience,
      wrong client and missing roles in `backend/tests/support/security.py`
- [x] T025 [P] Add security tests for missing token, invalid audience, expired token,
      wrong client and missing role in `backend/tests/common/test_security_jwt.py`
- [x] T026 Implement JWKS-backed JWT verification (signature, issuer, audience,
      expiration, `azp`/client and `resource_access.gemodo-backend.roles`) in
      `backend/app/common/security.py`
- [x] T027 Implement FastAPI dependencies `require_documenti_viewer` and
      `require_documenti_generatore`, including mock principal support only when
      explicitly enabled, in `backend/app/common/security.py`
- [x] T028 Add authentication/authorization error mapping (`ACCESSO_NON_AUTENTICATO`,
      `ACCESSO_NON_AUTORIZZATO`) to `backend/app/common/errors.py` and keep codes
      aligned with `infra/openapi/errors.md`

**Checkpoint**: Foundation ready; user story implementation can begin.

---

## Phase 3: User Story 1 - Consultare modelli pubblicati disponibili (Priority: P1)

**Goal**: GEBAN can list document types, profiles and published model versions for a
process context, with `codice_tipologia` validated against configured GEBAN/SOL
typologies (FR-020).

**Independent Test**: With demo data containing published and non-published versions,
catalog calls return only valid published versions in operative mode and archived
historical versions in historical mode. In v0.4 an unmatched `codice_tipologia`
returns an empty list; the old allowlist/error behavior is retired.

### Tests for User Story 1

- [x] T029 [P] [US1] Add contract test for `GET /api/v1/catalogo/tipi-documento` in `backend/tests/catalog/test_catalogo_tipi_documento_api.py`
- [x] T030 [P] [US1] Add contract test for `GET /api/v1/catalogo/tipi-documento/{codiceTipoDocumento}/profili` in `backend/tests/catalog/test_catalogo_categorie_api.py`
- [x] T031 [P] [US1] Add contract test for `GET /api/v1/catalogo/modelli` operative and historical modes in `backend/tests/catalog/test_catalogo_modelli_api.py`
- [x] T032 [P] [US1] Add test for `codice_tipologia` rejecting an unconfigured value with `TIPOLOGIA_SOL_NON_VALIDA` (FR-020) in `backend/tests/catalog/test_catalogo_tipologia_sol.py`

### Implementation for User Story 1

- [x] T033 [P] [US1] Create catalog response Pydantic schemas in `backend/app/catalog/schemas.py`
- [x] T034 [US1] Implement catalog query service in `backend/app/catalog/service.py`
- [x] T035 [US1] Implement catalog FastAPI router in `backend/app/catalog/api.py`
- [x] T036 [US1] Add operative mode filtering for `PUBBLICATO` versions in `backend/app/catalog/service.py`
- [x] T037 [US1] Add historical mode filtering by publication dates in `backend/app/catalog/service.py`
- [x] T038 [US1] Add not-found and empty-result handling in `backend/app/catalog/api.py`
- [x] T039 [US1] Validate `codice_tipologia` against `TipologiaBandoSOL` and raise
      `TIPOLOGIA_SOL_NON_VALIDA` for unknown codes in `backend/app/catalog/service.py`

**Checkpoint**: User Story 1 is independently testable through catalog endpoints.

---

## Phase 4: User Story 2 - Ottenere il contratto dati del modello (Priority: P1)

**Goal**: GEBAN can request fields and schema for the selected `modello_versione_id`,
including each field's `lingua` (FR-021).

**Independent Test**: Given a published model version with required, optional and
English-language fields, GEBAN receives ordered field metadata (including `lingua`)
and a schema with strict additional-property behavior.

### Tests for User Story 2

- [x] T040 [P] [US2] Add contract test for `GET /api/v1/catalogo/modelli/{modelloVersioneId}/campi-richiesti` in `backend/tests/catalog/test_campi_richiesti_api.py`
- [x] T041 [P] [US2] Add test for non-published version rejection in `backend/tests/catalog/test_campi_richiesti_api.py`
- [x] T042 [P] [US2] Add test asserting each field response includes `lingua`
      (`IT`/`EN`, default `IT`) in `backend/tests/catalog/test_campi_richiesti_api.py`

### Implementation for User Story 2

- [x] T043 [P] [US2] Create field contract Pydantic schemas, including `lingua`, in `backend/app/catalog/schemas.py`
- [x] T044 [US2] Implement field contract service in `backend/app/catalog/service.py`
- [x] T045 [US2] Add schema generation with `additionalProperties=false` in `backend/app/catalog/service.py`
- [x] T046 [US2] Add `campi-richiesti` route to `backend/app/catalog/api.py`
- [x] T047 [US2] Add conflict handling for non-published versions in `backend/app/common/errors.py`

**Checkpoint**: User Story 2 is independently testable by requesting a contract for a selected model version.

---

## Phase 5: User Story 3 - Validare il payload prima della generazione (Priority: P1)

**Goal**: GEBAN can validate a dynamic payload against the selected model version
contract, including conditional English-field requiredness driven by `bando_inglese`
(FR-021, FR-022).

**Independent Test**: Valid payloads return `valido=true`; missing required fields,
wrong types, extra fields, non-published versions and missing required English fields
(when `bando_inglese=true`) return structured validation errors; the same payload
without `bando_inglese` does not require the English fields.

### Tests for User Story 3

- [x] T048 [P] [US3] Add validation success test in `backend/tests/validation/test_validazione_payload_api.py`
- [x] T049 [P] [US3] Add missing required field test in `backend/tests/validation/test_validazione_payload_api.py`
- [x] T050 [P] [US3] Add wrong type test in `backend/tests/validation/test_validazione_payload_api.py`
- [x] T051 [P] [US3] Add extra field rejection test in `backend/tests/validation/test_validazione_payload_api.py`
- [x] T052 [P] [US3] Add non-published version validation failure test in `backend/tests/validation/test_validazione_payload_api.py`
- [x] T053 [P] [US3] Add test: `bando_inglese=true` and a required `lingua=EN` field
      missing produces `CAMPO_INGLESE_MANCANTE` in `backend/tests/validation/test_validazione_bando_inglese.py`
- [x] T054 [P] [US3] Add test: same payload with `bando_inglese=false` (or absent)
      does not require the `EN` field and returns `valido=true` in
      `backend/tests/validation/test_validazione_bando_inglese.py`

### Implementation for User Story 3

- [x] T055 [P] [US3] Create validation request/response Pydantic schemas, including
      `bando_inglese: bool = False`, in `backend/app/validation/schemas.py`
- [x] T056 [US3] Implement payload validation service in `backend/app/validation/service.py`
- [x] T057 [US3] Implement required-field validation in `backend/app/validation/service.py`
- [x] T058 [US3] Implement type validation for string, number, date, boolean, array and object in `backend/app/validation/service.py`
- [x] T059 [US3] Implement extra-field rejection in `backend/app/validation/service.py`
- [x] T060 [US3] Implement conditional requiredness for `lingua=EN` fields based on
      `bando_inglese`, raising `CAMPO_INGLESE_MANCANTE` per missing field, in
      `backend/app/validation/service.py`
- [x] T061 [US3] Implement validation FastAPI router in `backend/app/validation/api.py`

**Checkpoint**: User Story 3 is independently testable through the validation endpoint.

---

## Phase 6: User Story 4 - Gestire errori funzionali comprensibili (Priority: P2)

**Goal**: GEBAN receives structured, stable functional errors for catalog, contract and
validation failures, consistent with `infra/openapi/errors.md` (`009`).

**Independent Test**: Invalid model version, invalid context, invalid tipologia and
invalid payload produce predictable error codes and messages.

### Tests for User Story 4

- [x] T062 [P] [US4] Add error envelope tests in `backend/tests/common/test_api_error_response.py`
- [x] T063 [P] [US4] Add invalid context error test in `backend/tests/catalog/test_catalogo_modelli_api.py`

### Implementation for User Story 4

- [x] T064 [US4] Create domain exception hierarchy in `backend/app/common/errors.py`
- [x] T065 [US4] Map validation error codes (`CAMPO_OBBLIGATORIO`, `TIPO_NON_VALIDO`,
      `CAMPO_NON_AMMESSO`, `CAMPO_INGLESE_MANCANTE`, `CONTESTO_NON_VALIDO`) in
      `backend/app/validation/errors.py`, keeping the codes aligned with
      `infra/openapi/errors.md`
- [x] T066 [US4] Map catalog error codes (`MODELLO_VERSIONE_NON_PUBBLICATO`,
      `MODELLO_VERSIONE_NON_TROVATO`, `TIPOLOGIA_SOL_NON_VALIDA`) in
      `backend/app/catalog/errors.py`, keeping the codes aligned with
      `infra/openapi/errors.md`
- [x] T067 [US4] Ensure routers return stable error envelope in `backend/app/common/errors.py`

**Checkpoint**: User Story 4 is independently testable through negative API scenarios.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Align documentation, contracts and quickstart validation.

- [x] T068 [P] Update OpenAPI examples reflecting `lingua`/`bando_inglese` in
      `specs/001-catalogo-contratto-geban/contracts/geban-catalog-api.openapi.yaml`
      (structure already updated 2026-07-29; add runtime-verified examples once the
      endpoints exist)
- [x] T069 [P] Update quickstart with concrete local FastAPI commands, replacing the
      placeholder prerequisites in `specs/001-catalogo-contratto-geban/quickstart.md`
- [x] T070 Update `infra/openapi/README.md` inventory row for `001` from "Presente" to
      note the implemented endpoints, and add real success/error examples to
      `infra/openapi/examples/` generated from the running service (replacing the
      hand-built demo examples created by `009`)
- [x] T071 Add README pointer to implemented backend commands in `README.md`
- [x] T072 Run backend pytest suite (`uv run pytest -m "not e2e" or -k catalog or -k validation`, plus the full `009` suite to confirm no regression) and record result in `specs/001-catalogo-contratto-geban/quickstart.md`
- [x] T073 Update `docs/quality-coverage-matrix.yaml` rows for FR-004, FR-005, FR-020,
      FR-021, FR-022 from `DA_COPRIRE`/conceptual to `COPERTO` once the corresponding
      tests pass, and update `docs/decision-register.yaml` entries
      `DEC-001-TIPOLOGIE-SOL` / `DEC-001-LINGUA-IT-EN` implementation notes if their
      `impatto` text needs to reflect the shipped behavior
- [x] T074 Align the GEBAN catalog classification tree by adding
      `GET /api/v1/catalogo/tipi-documento/{codiceTipoDocumento}/classificazione`,
      seeding GEBAN/SOL typologies mapped to profiles, and keeping SOL
      technical folder codes internal instead of user-facing
- [x] T075 Add `POST /api/v1/documenti/genera` placeholder endpoint for GEBAN API
      collaudo, reusing payload validation and returning an explicit future-download
      message instead of a real PDF link
- [x] T076 Add Alembic `0006` data realignment migration so deployments that already
      applied the older `0005` receive the updated profiles, classification tree and
      demo models for each configured typology/profile combination

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies; several tasks extend files `009` already created (see per-task notes).
- **Foundational (Phase 2)**: depends on Setup completion; blocks all user stories.
- **US1 Catalogo (Phase 3)**: depends on Foundational.
- **US2 Contratto dati (Phase 4)**: depends on Foundational and reuses catalog version lookup.
- **US3 Validazione payload (Phase 5)**: depends on US2 contract logic (including `lingua`).
- **US4 Errori funzionali (Phase 6)**: can begin after Foundational but final integration depends on US1-US3.
- **Polish (Phase 7)**: depends on desired user stories being complete.

### User Story Dependencies

- **US1 (P1)**: first productive entry point; no dependency on other user stories after Foundational.
- **US2 (P1)**: requires model version lookup and field persistence (including `lingua`) from Foundational.
- **US3 (P1)**: requires `modello_versione_id` lookup and field contract (including `lingua`) from US2.
- **US4 (P2)**: improves negative scenarios across US1-US3.

### Parallel Opportunities

- T005-T008 can run in parallel after T001-T004.
- T011-T016 can run in parallel after T009-T010.
- T022-T025 can run in parallel after T003/T007/T008.
- T029-T032 can run in parallel.
- T040-T042 can run in parallel.
- T048-T054 can run in parallel.
- T062-T063 can run in parallel.
- T068-T069 can run in parallel after implementation behavior is stable.

## Parallel Example: User Story 3

```text
Task: T048 Add validation success test in backend/tests/validation/test_validazione_payload_api.py
Task: T049 Add missing required field test in backend/tests/validation/test_validazione_payload_api.py
Task: T050 Add wrong type test in backend/tests/validation/test_validazione_payload_api.py
Task: T051 Add extra field rejection test in backend/tests/validation/test_validazione_payload_api.py
Task: T052 Add non-published version validation failure test in backend/tests/validation/test_validazione_payload_api.py
Task: T053 Add bando_inglese missing English field test in backend/tests/validation/test_validazione_bando_inglese.py
Task: T054 Add bando_inglese=false does-not-require-English test in backend/tests/validation/test_validazione_bando_inglese.py
```

## Implementation Strategy

### Primo Incremento Produttivo

1. Complete Phase 1 and Phase 2.
2. Complete Phase 3 (US1 catalogo, incluso `codice_tipologia`).
3. Validate catalog endpoints with demo data (seed condiviso con `009`).
4. Add Phase 4 and Phase 5 to complete contract and validation flow, incluso `bando_inglese`.

### Incremental Delivery

1. Catalogo tipi/profili/modelli, con validazione tipologia GEBAN/SOL.
2. Protezione JWT minima sulle route operative (`DOCUMENTI_VIEWER` per consultazione,
   `DOCUMENTI_GENERATORE` per validazione).
3. Contratto dati per `modello_versione_id`, incluso `lingua` per campo.
4. Validazione payload strict, incluso `bando_inglese`.
5. Error envelope and documentation polish.

## Notes

Riallineamento documentale 010 FR-016, 2026-09-17: T029/T030 e la validazione
locale di T032/T039 sono evidenze storiche ritirate, non requisiti runtime.
T080-T084 sono SUPERATI/SOSPESI: non rinominare/reintrodurre tabelle del catalogo
eliminate da migration 0009. Semantica corrente v0.4: codice_tipologia e profilo
filtrano i soli modelli GEMODO, senza corrispondenze -> 200/modelli vuoti.
Le note storiche su TIPOLOGIA_SOL_NON_VALIDA non prevalgono su FR-020 aggiornato.
Questa modifica non esegue nuovi task implementativi della 001.

- All operative calls after catalog selection require `modello_versione_id` (int64,
  `DEC-001-IDENTIFICATIVI-MODELLO`).
- Campi extra in payload are blocking validation errors.
- `codice_tipologia` senza modelli corrispondenti restituisce lista vuota (v0.4).
- Campi `lingua=EN` sono obbligatori solo se `bando_inglese=true`.
- API operative protette: catalogo/campi richiedono token valido con
  `DOCUMENTI_VIEWER` o `DOCUMENTI_GENERATORE`; validazione payload richiede
  `DOCUMENTI_GENERATORE`.
- Profilo GEBAN versionato e autorizzazione fine restano fuori scope (FR-023); non
  aggiungere filtri per profilo qui senza prima chiudere `DEC-001-PROFILO-GEBAN`.

---

## Secondo Incremento (2026-09-14): Perimetro Per-Profilo, Ufficio, Registro Contratti Dati

`DEC-001-PROFILO-GEBAN` e le decisioni collegate sono ora `CONFERMATA` (vedi
`docs/decision-register.yaml`, `research.md`, `data-model.md`). FR-025..FR-031,
User Story 5. Numerazione task continua da T076.

## Phase 8: Foundational (secondo incremento)

**Purpose**: schema DB, seed e loader per profili/uffici/registro contratti dati.
Blocca la Phase 9 (nessuna route puo' verificare un perimetro che non esiste ancora
come dato interrogabile).

**⚠️ CRITICAL**: nessun lavoro della User Story 5 puo' iniziare prima che questa fase
sia completa.

**Nota 2026-09-15 (cascading ADR 0001, terzo incremento — vedi `plan.md`)**: per
`BANDO_CONCORSO`, `seed-demo-catalog.yaml` (T077-T079) e le migration che lo
rileggono (T080, T087) restano valide per popolare un **adapter locale/mock**
(sviluppo e test senza rete verso GEBAN) — non sono piu' la sorgente di
produzione. In produzione, categorie/tipologie/contratto dati di `BANDO_CONCORSO`
vengono sincronizzati da un adapter HTTP verso l'endpoint registrato in
`specs/010-configurazione-cataloghi-integrazioni` (schema dell'adapter progettato
li', non qui). I task T077-T092 sotto restano eseguibili cosi' come scritti; le
annotazioni puntuali segnano dove la sourcing di produzione cambia.

- [ ] T077 [P] *(2026-09-15, `DEC-001-CONTESTO-SOSTITUISCE-UFFICIO`: riscritta,
      non piu' `uffici:`/`ufficio:`)* Aggiungere campo `codice_contesto: geban` a
      ogni voce di `tipi_documento:` in
      `infra/local/postgres/seed-demo-catalog.yaml` — nessuna sezione `uffici:`
      separata da creare, il contesto e' un valore diretto sul tipo documento.
      *(2026-09-15/16: NON ancora fatto — il valore in DB e' stato popolato da
      T085 con un backfill diretto via SQL nella migration, non rileggendo
      questo file; corretto per l'unico tipo documento reale di stasera
      (BANDO_CONCORSO), ma questo task resta aperto per restare coerenti col
      resto del seed quando arrivera' un secondo tipo documento)*
- [ ] T078 [P] Rinominare `tipologie_sol:` in `tipologie:` in
      `infra/local/postgres/seed-demo-catalog.yaml`: ogni voce guadagna
      `tipo_documento: BANDO_CONCORSO` e `codice_sol` viene rinominato
      `riferimento_esterno`. *(2026-09-15: da qui in poi questo file e' fixture
      per l'adapter locale/mock, non piu' seed di produzione per BANDO_CONCORSO)*
- [ ] T079 [P] Aggiungere sezione `contratti_dati:` a
      `infra/local/postgres/seed-demo-catalog.yaml` che definisce
      `bando-concorso-common-fields-v1` (codice, `tipo_documento: BANDO_CONCORSO`,
      versione, campi ricalcati da `CAMPI_DEMO`/`ModelloCampoRichiesto`).
      *(2026-09-15: stessa nota di T078 — fixture per adapter locale/mock)*
- [ ] T080 *(2026-09-16: numero migration aggiornato da `0008` a `0009` — `0008`
      e' stato preso da T085, implementata prima perche' necessaria stasera)*
      Migration Alembic `0009` in
      `backend/alembic/versions/0009_generalizza_tipologia_documento.py`: rinomina
      tabella `tipologia_bando_sol` -> `tipologia_documento`, aggiunge
      `tipo_documento_id` (FK), cambia il vincolo univoco a
      `(tipo_documento_id, codice)`, rinomina `codice_sol` -> `riferimento_esterno`
      (nullable), rimuove la colonna vestigiale
      `tipo_documento.tipologia_bando_sol_id` (verificato: non usata da nessun
      codice reale), rilegge `seed-demo-catalog.yaml` aggiornato (T078) per
      ripopolare (stesso pattern upsert/disattiva-stale di `0005`-`0007`). *(2026-
      09-15: la rinomina/generalizzazione dello schema resta valida cosi' com'e';
      il refresh periodico di queste righe in produzione per BANDO_CONCORSO passa
      pero' dall'adapter HTTP di `010`, non solo da questa migration one-shot)*
- [ ] T081 [P] Rinominare `TipologiaBandoSOL` -> `TipologiaDocumento` in
      `backend/app/catalog/models.py`, aggiungere relazione/FK
      `tipo_documento_id`, rinominare `codice_sol` -> `riferimento_esterno`
      (nullable)
- [ ] T082 Aggiornare `get_tipologia_sol_by_codice` in
      `backend/app/catalog/repository.py` per filtrare anche per
      `tipo_documento_id` (depends on T080, T081)
- [ ] T083 Aggiornare riferimenti a `TipologiaBandoSOL`/`codice_sol` in
      `backend/app/catalog/service.py` e `backend/app/catalog/schemas.py`
      (nessun cambio del contratto pubblico: `codice_tipologia` e
      `TIPOLOGIA_SOL_NON_VALIDA` restano invariati)
- [ ] T084 [P] Aggiornare fixture e test esistenti che referenziano
      `TipologiaBandoSOL`/`codice_sol` in `backend/tests/catalog/`,
      `backend/tests/support/`, `backend/tests/integration/test_seed_demo_validation.py`
- [x] T085 *(implementata 2026-09-16, `DEC-001-CONTESTO-SOSTITUISCE-UFFICIO`:
      niente piu' tabella `Ufficio`)* Migration Alembic
      `backend/alembic/versions/0008_contesto_registro_contratti_audit.py`:
      aggiunge `tipo_documento.codice_contesto` (`String`, `NOT NULL`), NESSUNA
      nuova tabella `ufficio`, NESSUN FK. Backfill diretto via SQL
      (`codice_contesto = 'geban'` per `BANDO_CONCORSO`, l'unico tipo documento
      reale) invece di rileggere `seed-demo-catalog.yaml` — T077 resta aperto,
      vedi la sua nota; se/quando arriva un secondo tipo documento questa
      migration va estesa a leggere dal seed invece di restare hardcoded.
      Verificato su Postgres reale (`alembic upgrade head` pulito, colonna letta
      correttamente via SQLAlchemy).
- [ ] T086 *(2026-09-15: non piu' necessaria — non esiste piu' un modello
      SQLAlchemy `Ufficio` da aggiungere; `codice_contesto` in T085 e' gia' un
      campo diretto su `TipoDocumento`, nessuna relazione separata)*
- [x] T087 (parziale, `registro_contratti_dati` — 2026-09-16) / [ ] (rimane,
      `sistema_richiedente`/`client_applicativo`/`profilo_integrazione` come
      tabelle DB) — Migration Alembic
      `backend/alembic/versions/0008_contesto_registro_contratti_audit.py` (non
      `0010`, riusa la stessa migration di T085): crea `registro_contratti_dati`
      (`tipo_documento_id`, `codice`, `versione`, `campi` JSONB, `stato`),
      popolata con `bando-concorso-common-fields-v1` (i 7 campi reali, incluso
      `livello`) via SQL diretto invece che rileggendo una sezione
      `contratti_dati:` di `seed-demo-catalog.yaml` (che non esiste ancora, vedi
      T079). **Non fatto**: `sistema_richiedente`/`client_applicativo`/
      `profilo_integrazione` restano tabelle NON create — `_configured_sistemi`
      in `security.py` legge ancora `infra/local/integration-profiles.local.yaml`
      via cache in memoria, invariato (T088-T092 sotto restano da fare per
      davvero, non solo la parte registro contratti dati). *(le tabelle
      sistema_richiedente/profilo_integrazione restano possedute da GEMODO senza
      cambiamenti — sono "chi puo' consumare cosa", non il contenuto del
      catalogo. Solo `registro_contratti_dati` per BANDO_CONCORSO segue la
      stessa nota di T078/T079/T080: fixture locale, sincronizzata in
      produzione dall'adapter di `010`)*
- [ ] T088 [P] Aggiungere modelli SQLAlchemy per le nuove tabelle in un nuovo
      `backend/app/quality/models.py`, stessa forma dei Pydantic gia' esistenti in
      `backend/app/quality/schemas.py`
- [ ] T089 Aggiungere loader DB-backed (`load_sistemi_richiedenti_db` o simile) in
      `backend/app/quality/integration_profile.py` che sostituisce
      `load_sistemi_richiedenti`/`_load_sistemi_richiedenti_cached` leggendo dalle
      tabelle invece che dal file YAML in cache eterna, restituendo gli stessi
      Pydantic `SistemaRichiedente`/`ProfiloDiIntegrazione` (depends on T087, T088)
- [ ] T090 Aggiornare `_configured_sistemi` in `backend/app/common/security.py`
      per usare il loader DB-backed (T089) invece di
      `_load_sistemi_richiedenti_cached` sullo YAML
- [ ] T091 Validare i riferimenti di `contratti_dati_ammessi` al caricamento
      (FR-029): il loader (T089) MUST rifiutare un `ProfiloDiIntegrazione` che
      referenzia un `RegistroContrattiDati` inesistente, non ignorarlo
      silenziosamente, in `backend/app/quality/integration_profile.py`
- [ ] T092 [P] Aggiungere test reali su Postgres per il loader DB-backed e la
      validazione T091 in `backend/tests/integration/test_integration_profiles_db.py`

**Checkpoint**: profili, uffici e registro contratti dati sono dati reali
interrogabili dal DB; `security.py` non dipende piu' dalla cache YAML in memoria
per la risoluzione del profilo.

---

## Phase 9: User Story 5 - Applicare il perimetro contrattuale del profilo (Priority: P1) 🎯

**Goal**: le API catalogo/validazione rifiutano esplicitamente le richieste fuori dal
perimetro del profilo del chiamante, invece di rispondere con un elenco vuoto
indistinguibile o, peggio, con i dati di un altro profilo.

**Independent Test**: dato un profilo GEBAN con perimetro noto, chiamare le API con
valori dentro e fuori dal perimetro e verificare che le risposte siano
distinguibili (vedi Acceptance Scenarios della User Story 5 in `spec.md`).

### Tests for User Story 5

> **NOTE**: scrivere questi test per primi, verificare che falliscano prima
> dell'implementazione (coerente con lo stile gia' usato per US1-US4).

- [ ] T093 [P] [US5] Aggiungere test: richiesta con tipo documento fuori dal
      perimetro del profilo restituisce `PROFILO_INTEGRAZIONE_NON_ABILITATO` in
      `backend/tests/catalog/test_perimetro_profilo_api.py` (nuovo file)
- [ ] T094 [P] [US5] Aggiungere test: categoria/tipologia nel perimetro ma senza
      modello pubblicato restituisce elenco vuoto, non l'errore (regressione
      esplicita rispetto al comportamento del primo incremento) nello stesso file
- [ ] T095 [P] [US5] Aggiungere test: `modello_versione_id` concesso via
      `modelli_versioni_ammessi` di un tipo documento con `codice_contesto`
      diverso da quello "principale" del profilo viene comunque autorizzato
      (concessione cross-contesto) nello stesso file
- [ ] T096 [P] [US5] Aggiungere test end-to-end con profilo GEBAN reale caricato
      dalle tabelle DB (non fixture in-memory) in
      `backend/tests/e2e/test_perimetro_profilo_geban.py`

### Implementation for User Story 5

- [ ] T097 [US5] Aggiungere `ErrorCode.PROFILO_INTEGRAZIONE_NON_ABILITATO` in
      `backend/app/common/errors.py` (codice gia' descritto in
      `infra/openapi/errors.md`, mai wired a codice reale prima d'ora)
- [ ] T098 [US5] Aggiungere funzione di risoluzione profilo (da `client_id`/contesto
      di `PrincipalGEMODO`) in `backend/app/common/security.py`, riusando
      `_configured_sistemi` (T090)
- [ ] T099 [US5] Aggiungere funzione di verifica perimetro in
      `backend/app/quality/integration_profile.py`, riusando `is_operazione_
      autorizzata`/`_valore_ammesso` gia' esistenti (oggi usate solo dal fixture
      `fake_gemodo_client.py`) invece di duplicarne la logica (depends on T098)
- [ ] T100 [US5] Collegare la verifica perimetro (T099) alle route in
      `backend/app/catalog/api.py` (`search_modelli`, `list_profili_documento`,
      `get_classificazione_documento`, `get_campi_richiesti`), passando il
      `PrincipalGEMODO` reale invece di scartarlo con `_: PrincipalGEMODO`
- [ ] T101 [US5] Collegare la verifica perimetro (T099) a
      `backend/app/validation/api.py` per `POST /documenti/valida` e
      `POST /documenti/genera`
- [ ] T102 [US5] Verificare che l'elenco vuoto resti invariato quando
      categoria/tipologia sono nel perimetro senza modello pubblicato (nessuna
      regressione sul comportamento del primo incremento, vedi T094)

**Checkpoint**: User Story 5 e' completa e testabile indipendentemente; il gap
trovato il 2026-09-14 (allow-list mai collegata alle route reali) e' chiuso.

---

## Phase 10: Polish & Cross-Cutting Concerns (secondo incremento)

- [ ] T103 [P] Aggiornare
      `specs/001-catalogo-contratto-geban/contracts/geban-catalog-api.openapi.yaml`
      con `PROFILO_INTEGRAZIONE_NON_ABILITATO` (esempio errore, status 403)
- [ ] T104 [P] Aggiungere uno scenario dedicato in
      `specs/001-catalogo-contratto-geban/quickstart.md` per il perimetro
      per-profilo (chiamata dentro vs fuori dal perimetro)
- [ ] T105 Aggiornare `docs/quality-coverage-matrix.yaml` per FR-025..FR-031 da
      `DA_COPRIRE` a `COPERTO`
- [ ] T106 Eseguire la suite pytest completa su Postgres reale (non solo unitaria,
      coerente con T072 del primo incremento) e registrare l'esito in
      `specs/001-catalogo-contratto-geban/quickstart.md`
- [ ] T107 Aggiornare `docs/project-map.md` e l'`impatto` delle decisioni in
      `docs/decision-register.yaml` per riflettere lo stato effettivamente
      implementato (oggi descrivono solo la direzione confermata)
- [ ] T108 *(2026-09-15, `DEC-001-RITIRO-ENDPOINT-CLASSIFICAZIONE`)* Ritirare da
      `contracts/geban-catalog-api.openapi.yaml` le tre operazioni
      `listTipiDocumento`, `listProfiliDocumento`, `getClassificazioneDocumento`
      (`/catalogo/tipi-documento`, `/catalogo/tipi-documento/{codice}/profili`,
      `/catalogo/tipi-documento/{codice}/classificazione`), rimuovere le relative
      route/test in `backend/app/catalog/api.py` e
      `backend/tests/catalog/test_catalogo_categorie_api.py`/
      `test_catalogo_tipi_documento_api.py`, e verificare che nessun'altra parte
      del sistema (mock GEBAN incluso) dipenda ancora da queste risposte prima di
      rimuoverle. Bloccato finche' `010` non eroga la generazione del contratto di
      discovery (sostituto funzionale) — non rimuovere le tre API prima che quella
      capacita' esista, per non lasciare GEBAN senza modo di scoprire la forma
      attesa del proprio endpoint.

---

## Dependencies & Execution Order - Secondo Incremento

### Phase Dependencies

- **Foundational (Phase 8)**: dipende dal primo incremento gia' completo (Phase 1-7);
  blocca la Phase 9 per intero — nessuna route puo' verificare un perimetro contro
  dati che non esistono ancora.
- **US5 (Phase 9)**: dipende da Phase 8 completa.
- **Polish (Phase 10)**: dipende da Phase 9 completa.

### Parallel Opportunities

- T077-T079 possono girare in parallelo (file diversi/sezioni diverse dello stesso
  seed, nessuna dipendenza fra loro).
- T081, T086, T088 possono girare in parallelo dopo le rispettive migration.
- T084 puo' girare in parallelo dopo T080-T083.
- T092 puo' girare in parallelo dopo T089-T091.
- T093-T096 possono girare in parallelo (stesso file di test ma scenari
  indipendenti, o file separati come indicato).
- T103-T104 possono girare in parallelo dopo che il comportamento e' stabile.

## Parallel Example: User Story 5

```text
Task: T093 Add out-of-perimeter test in backend/tests/catalog/test_perimetro_profilo_api.py
Task: T094 Add in-perimeter-no-model regression test in backend/tests/catalog/test_perimetro_profilo_api.py
Task: T095 Add cross-contesto grant test in backend/tests/catalog/test_perimetro_profilo_api.py
Task: T096 Add real e2e test in backend/tests/e2e/test_perimetro_profilo_geban.py
```

## Implementation Strategy - Secondo Incremento

1. Completare la Phase 8 (schema, seed, loader) — nessun comportamento API cambia
   ancora in questa fase, solo dati e infrastruttura.
2. Completare la Phase 9 (US5) — qui il comportamento API cambia: verificare con la
   suite reale su Postgres che nessuna regressione tocchi US1-US4 del primo
   incremento.
3. Completare la Phase 10 (polish, contratto OpenAPI, coverage matrix).
4. **Non incluso in questo incremento** (per decisione esplicita, vedi `spec.md`
   Session 2026-09-14): interfaccia web di amministrazione per creare
   Uffici/tipi documento/associare Applicazioni; enforcement lato scrittura di
   FR-031 (nessun endpoint di creazione modello esiste ancora: e' scope della
   `002`, non implementabile qui).

## Notes - Secondo Incremento

- Nessuna migration storica (`0001`-`0007`) va modificata: solo nuove migration
  (`0008`, `0009`, `0010`).
- Il rename `TipologiaBandoSOL` -> `TipologiaDocumento` e' interno: `codice_tipologia`
  e `TIPOLOGIA_SOL_NON_VALIDA` restano invariati nel contratto pubblico.
- FR-031 (proprieta' via `codice_contesto` sul lato scrittura,
  `DEC-001-CONTESTO-SOSTITUISCE-UFFICIO`, 2026-09-15) e' modellata a livello di
  schema in questo incremento (T085) ma la sua *enforcement* (chi puo' editare
  cosa) resta bloccata sull'esistenza di endpoint di scrittura, che appartengono
  alla `002` non ancora implementata — non inventare qui un endpoint di scrittura solo
  per testare FR-031.
- **2026-09-15 (cascading ADR 0001)**: prima di eseguire in produzione la parte di
  T080/T087 che riguarda `BANDO_CONCORSO`, verificare che
  `specs/010-configurazione-cataloghi-integrazioni` abbia un adapter di discovery
  funzionante e un endpoint registrato — altrimenti il refresh di produzione della
  categorizzazione GEBAN non ha sorgente. Le stesse migration restano comunque
  eseguibili in locale/test per popolare l'adapter mock, senza questa dipendenza.
- **2026-09-15 (`DEC-001-RITIRO-ENDPOINT-CLASSIFICAZIONE`)**: `listTipiDocumento`,
  `listProfiliDocumento`, `getClassificazioneDocumento` restano nel contratto
  pubblico *solo* fino a T108. Non sono piu' il modo corretto per GEBAN di
  scoprire la propria categorizzazione (la possiede gia'): quel bisogno e'
  coperto dal contratto/documentazione di discovery generato da `010`, non da un
  endpoint runtime GEMODO. Nessun nuovo consumatore va aggiunto a queste tre API
  nel frattempo.

---

## Terzo Incremento (2026-09-17): Enforcement Per-Contesto Lato Consumatore

Clarification "Sicurezza API Per Contesto - 2026-09-17" in `spec.md`: il controllo
generale `DOCUMENTI_VIEWER`/`DOCUMENTI_GENERATORE` non basta, ogni richiesta va
autorizzata anche sul contesto proprietario del modello. FR-034..FR-038, sezione
"Accettazione Sicurezza Per Contesto". Numerazione task continua da T108.

**Attenzione a non confondere questo asse con la Phase 9 sopra (US5, FR-025..027,
T093-T102, ancora `[ ]` e non iniziata)**: quello e' il perimetro *fine-grained* per
profilo di integrazione (quali categorie/tipologie/`modello_versione_id` specifici un
profilo puo' vedere, via `ProfiloDiIntegrazione`/`is_operazione_autorizzata`), non
ancora implementato. Questo incremento e' invece il gate *per-contesto* (a quale
`codice_contesto` appartiene il tipo documento, e se il token ha un ruolo mappato per
quel contesto specifico, via `ruoli_contesto`/`role_mappings`,
`DEC-001-CONTESTO-SOSTITUISCE-UFFICIO` applicata ai consumatori). Le due verifiche
restano complementari e indipendenti: US5/FR-025..027 resta lavoro futuro aperto.

**Goal**: nessuna API consumatore (ricerca catalogo, campi richiesti, validazione,
generazione, stato/download documento) concede accesso, dati o effetti su un modello
il cui `codice_contesto` non e' autorizzato dal token del chiamante — ne' in ricerca
(403 sanificato su perimetro esplicito) ne' via ID diretto (404 sanificato,
indistinguibile da risorsa inesistente).

- [x] T109 [P] Aggiungere test end-to-end reali su Postgres (Testcontainers) che
      coprono gli scenari 1, 2, 4, 5, 6 di "Accettazione Sicurezza Per Contesto" e il
      comportamento con il flag disattivato, in
      `backend/tests/common/test_autorizzazione_per_contesto.py` (nuovo file). Usa il
      manifest reale (`infra/local/integration-profiles.local.yaml`) e la forma
      esatta del JWT ACE (`contexts.<nome>.roles`), non un doppio mockato.
- [x] T110 Aggiungere `verifica_permesso_contesto()` e la costante
      `ROLE_DOCUMENTI_VIEWER`/`ROLE_DOCUMENTI_GENERATORE` gia' esistenti in
      `backend/app/common/security.py`, dietro il nuovo flag
      `GEMODO_ENFORCE_CONTESTO_CONSUMATORE` (default off) in
      `backend/app/core/settings.py` — rollout graduale: a flag spento il
      comportamento odierno resta invariato per non rompere chiamanti/test esistenti.
- [x] T111 Collegare T110 a `backend/app/catalog/service.py`: `search_modelli` nega
      con 403 sanificato su un filtro esplicito fuori perimetro (FR-034);
      `get_campi_richiesti` nega con 404 sanificato indistinguibile da versione
      inesistente (FR-035/FR-037).
- [x] T112 Collegare T110 a `backend/app/validation/service.py`
      (`validate_payload`): stessa risposta 404 sanificata di una versione
      inesistente quando il contesto non e' autorizzato (FR-035/FR-037/FR-038,
      l'autorizzazione precede la validazione dati).
- [x] T113 Collegare T110 a `backend/app/storage/service.py` (`stato`,
      `contenuto_per_download`) e passare il `PrincipalGEMODO` reale attraverso
      `backend/app/generazione/service.py` fino a `validate_payload` (FR-035/FR-037).
- [ ] T114 Aggiungere un test esplicito per lo scenario 3 di "Accettazione Sicurezza
      Per Contesto" (due contesti nello stesso token, permesso di generazione solo
      nel primo: il secondo nega la generazione ma consente comunque la
      consultazione se il ruolo li' mappa solo `DOCUMENTI_VIEWER`) — non ancora
      coperto da T109, che testa solo l'isolamento VIEWER tra contesti, non la
      distinzione VIEWER/GENERATORE all'interno del secondo contesto.
- [ ] T115 Decidere e documentare quando `GEMODO_ENFORCE_CONTESTO_CONSUMATORE`
      passa da `false` a `true` di default (readiness per l'uso operativo citata
      dalla clarification 2026-09-17), aggiornare `docs/decision-register.yaml` e
      `docs/quality-coverage-matrix.yaml` (FR-034..038 non hanno ancora una riga in
      quel file) di conseguenza.

**Checkpoint**: verificato per davvero su Postgres reale (Testcontainers) il
2026-09-17 — `pytest -m integration` 141 passed (0 skipped), `pytest -q` (suite
completa) 289 passed. Due bug reali trovati e corretti nel fixture di test durante
la verifica (non nell'implementazione): `_principal()` non popolava `ruoli`
aggregato, causando 403 dal gate di route prima del controllo per-contesto;
`_crea_versione()` non impostava `public_id` su `ModelloDocumento`, causando un 500
in `search_modelli`. T114/T115 restano aperti.
