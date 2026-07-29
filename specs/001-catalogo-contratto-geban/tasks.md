# Tasks: Catalogo Modelli E Contratto Dati GEBAN

**Input**: Design documents from `specs/001-catalogo-contratto-geban/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/geban-catalog-api.openapi.yaml`, `quickstart.md`

**Tests**: Included. The feature is contract-first and the plan requires pytest, httpx/FastAPI TestClient and Testcontainers PostgreSQL (or a real local PostgreSQL when Testcontainers/Docker is unavailable).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

**Regenerated 2026-07-29**: this file replaces the 2026-06-19 version to recepire the
decisions propagated from `009-fondamenta-mock-test-qualita` (tipologia GEBAN/SOL
validation, `lingua`/`bando_inglese` conditional requiredness) and to reconcile Setup
tasks with the backend skeleton `009` already created. See
`docs/decision-register.yaml` (`DEC-001-*`) and `docs/project-map.md` ("Stato
Plan/Tasks Delle Spec Operative") for context. Before starting implementation, run the
readiness gate for this spec:

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

As of 2026-07-29 the gate above lists nine decisions still blocking `TASKS` for this
spec. None of them block the tasks below, for reasons specific to each:

- `DEC-001-PROFILO-GEBAN`, `DEC-001-CONFIG-PROFILO-GEBAN`,
  `DEC-001-RELAZIONE-PROFILO-CATALOGO`, `DEC-001-API-PROFILO-GEBAN`: concern the GEBAN
  integration-profile filter, explicitly out of scope for this increment (FR-023) -
  no task below implements profile-based filtering.
- `DEC-006-CONFINE-KEYCLOAK-GEMODO`: owned by `006`; this feature already assumes the
  caller is pre-authorized (FR-017) and does not implement token/role validation.
- `DEC-001-CATEGORIE-INIZIALI`: affects seed *content* ("categorie demo minime"), not
  the catalog mechanism the tasks below implement.
- `DEC-001-VERSIONAMENTO-MAPPING-CAMPI`: concerns the re-publication workflow when a
  concorded field/placeholder changes - a later lifecycle question, not needed to
  ship the first catalog/contract/validation increment.
- `DEC-003-FORMATO-CAMPI-COMPLESSI` (owner `003`): the assumed structured-schema
  format is already what `ModelloCampoRichiesto.validazione` implements; no new
  requirement blocks these tasks.
- `DEC-001-CAMPI-COMUNI-GEBAN`: the *mechanism* (dynamic contract, no new entity) is
  settled by this plan; only the exact production field list remains pending with
  GEBAN, which is seed data, not code, for this increment.

If a later increment touches any of these areas directly, re-run the readiness gate
before generating new tasks for that part (FR-018).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Extend the FastAPI backend skeleton `009` already created; do not recreate
files that already exist.

- [ ] T001 Add this feature's dependencies (if any beyond `009`'s baseline) to the
      existing `backend/pyproject.toml` (created by `009` - extend, do not overwrite)
- [ ] T002 Mount this feature's routers on the existing `app` instance in
      `backend/app/main.py` (created by `009` with the Swagger/ReDoc publishing router
      - add `app.include_router(...)` calls, do not recreate the file)
- [ ] T003 Create settings module in `backend/app/core/settings.py` (new file inside the
      existing `backend/app/core/` package)
- [ ] T004 Create database session module in `backend/app/db/session.py` (new file
      inside the existing `backend/app/db/` package)
- [ ] T005 [P] Create catalog package under `backend/app/catalog/`
- [ ] T006 [P] Create validation package under `backend/app/validation/`
- [ ] T007 [P] Create common error and security package under `backend/app/common/`
- [ ] T008 [P] Create `backend/tests/catalog/__init__.py` and
      `backend/tests/validation/__init__.py` (new subpackages; `backend/tests/support/`
      already exists from `009` - add fixtures there, do not recreate the package)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared data model, migrations, repositories and error envelope that all user stories depend on.

**CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T009 Create catalog schema migration in
      `backend/alembic/versions/0002_catalogo_modelli.py`, extending the `009` baseline
      (`0001_initial_schema.py`) rather than redefining `tipo_documento` /
      `categoria_documento` / `modello_documento` / `modello_versione` /
      `campo_modello` - add the columns/constraints this feature needs
      (`variante`, `data_inizio_validita`, `data_fine_validita`, `pubblicato_at`,
      `lingua` on campo, unique constraint per variante corrente) via `ALTER TABLE`
- [ ] T010 Create `TipologiaBandoSOL` table migration in
      `backend/alembic/versions/0003_tipologia_bando_sol.py` (`codice`, `codice_sol`,
      `descrizione`, `attiva`) and FK `tipologia_bando_sol_id` (nullable) on
      `modello_documento`/`tipo_documento` per FR-020
- [ ] T011 [P] Create `TipoDocumento` SQLAlchemy model in `backend/app/catalog/models.py`
- [ ] T012 [P] Create `CategoriaDocumento` SQLAlchemy model in `backend/app/catalog/models.py`
- [ ] T013 [P] Create `TipologiaBandoSOL` SQLAlchemy model in `backend/app/catalog/models.py`
- [ ] T014 [P] Create `ModelloDocumento` SQLAlchemy model (with `variante`,
      `codice_tipologia` FK) in `backend/app/catalog/models.py`
- [ ] T015 [P] Create `ModelloDocumentoVersione` SQLAlchemy model in `backend/app/catalog/models.py`
- [ ] T016 [P] Create `ModelloCampoRichiesto` SQLAlchemy model, including `lingua`
      (`IT`/`EN`, default `IT`) in `backend/app/catalog/models.py`
- [ ] T017 Create catalog repository functions in `backend/app/catalog/repository.py`
- [ ] T018 Create common API error schemas in `backend/app/common/errors.py`
- [ ] T019 Create FastAPI exception handlers in `backend/app/common/errors.py`
- [ ] T020 Create catalog seed migration for demo data in
      `backend/alembic/versions/0004_seed_catalogo_demo.py`, loading the tipologie
      GEBAN/SOL and demo model already declared in
      `infra/local/postgres/seed-demo-catalog.yaml` (`009`) rather than hardcoding a
      second, divergent seed list
- [ ] T021 Create Testcontainers PostgreSQL fixtures in
      `backend/tests/support/postgres.py`, with a documented fallback to a real local
      PostgreSQL connection (`DATABASE_URL` env var) when Docker/Testcontainers is
      unavailable, matching the approach already used by `009` (see
      `backend/alembic/README.md`)

**Checkpoint**: Foundation ready; user story implementation can begin.

---

## Phase 3: User Story 1 - Consultare modelli pubblicati disponibili (Priority: P1) MVP

**Goal**: GEBAN can list document types, categories and published model versions for a
process context, with `codice_tipologia` validated against configured GEBAN/SOL
typologies (FR-020).

**Independent Test**: With demo data containing published and non-published versions,
catalog calls return only valid published versions in operative mode and archived
historical versions in historical mode; an unrecognized `codice_tipologia` returns
`TIPOLOGIA_SOL_NON_VALIDA`, not an empty list.

### Tests for User Story 1

- [ ] T022 [P] [US1] Add contract test for `GET /api/v1/catalogo/tipi-documento` in `backend/tests/catalog/test_catalogo_tipi_documento_api.py`
- [ ] T023 [P] [US1] Add contract test for `GET /api/v1/catalogo/tipi-documento/{codiceTipoDocumento}/categorie` in `backend/tests/catalog/test_catalogo_categorie_api.py`
- [ ] T024 [P] [US1] Add contract test for `GET /api/v1/catalogo/modelli` operative and historical modes in `backend/tests/catalog/test_catalogo_modelli_api.py`
- [ ] T025 [P] [US1] Add test for `codice_tipologia` rejecting an unconfigured value with `TIPOLOGIA_SOL_NON_VALIDA` (FR-020) in `backend/tests/catalog/test_catalogo_tipologia_sol.py`

### Implementation for User Story 1

- [ ] T026 [P] [US1] Create catalog response Pydantic schemas in `backend/app/catalog/schemas.py`
- [ ] T027 [US1] Implement catalog query service in `backend/app/catalog/service.py`
- [ ] T028 [US1] Implement catalog FastAPI router in `backend/app/catalog/api.py`
- [ ] T029 [US1] Add operative mode filtering for `PUBBLICATO` versions in `backend/app/catalog/service.py`
- [ ] T030 [US1] Add historical mode filtering by publication dates in `backend/app/catalog/service.py`
- [ ] T031 [US1] Add not-found and empty-result handling in `backend/app/catalog/api.py`
- [ ] T032 [US1] Validate `codice_tipologia` against `TipologiaBandoSOL` and raise
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

- [ ] T033 [P] [US2] Add contract test for `GET /api/v1/catalogo/modelli/{modelloVersioneId}/campi-richiesti` in `backend/tests/catalog/test_campi_richiesti_api.py`
- [ ] T034 [P] [US2] Add test for non-published version rejection in `backend/tests/catalog/test_campi_richiesti_api.py`
- [ ] T035 [P] [US2] Add test asserting each field response includes `lingua`
      (`IT`/`EN`, default `IT`) in `backend/tests/catalog/test_campi_richiesti_api.py`

### Implementation for User Story 2

- [ ] T036 [P] [US2] Create field contract Pydantic schemas, including `lingua`, in `backend/app/catalog/schemas.py`
- [ ] T037 [US2] Implement field contract service in `backend/app/catalog/service.py`
- [ ] T038 [US2] Add schema generation with `additionalProperties=false` in `backend/app/catalog/service.py`
- [ ] T039 [US2] Add `campi-richiesti` route to `backend/app/catalog/api.py`
- [ ] T040 [US2] Add conflict handling for non-published versions in `backend/app/common/errors.py`

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

- [ ] T041 [P] [US3] Add validation success test in `backend/tests/validation/test_validazione_payload_api.py`
- [ ] T042 [P] [US3] Add missing required field test in `backend/tests/validation/test_validazione_payload_api.py`
- [ ] T043 [P] [US3] Add wrong type test in `backend/tests/validation/test_validazione_payload_api.py`
- [ ] T044 [P] [US3] Add extra field rejection test in `backend/tests/validation/test_validazione_payload_api.py`
- [ ] T045 [P] [US3] Add non-published version validation failure test in `backend/tests/validation/test_validazione_payload_api.py`
- [ ] T046 [P] [US3] Add test: `bando_inglese=true` and a required `lingua=EN` field
      missing produces `CAMPO_INGLESE_MANCANTE` in `backend/tests/validation/test_validazione_bando_inglese.py`
- [ ] T047 [P] [US3] Add test: same payload with `bando_inglese=false` (or absent)
      does not require the `EN` field and returns `valido=true` in
      `backend/tests/validation/test_validazione_bando_inglese.py`

### Implementation for User Story 3

- [ ] T048 [P] [US3] Create validation request/response Pydantic schemas, including
      `bando_inglese: bool = False`, in `backend/app/validation/schemas.py`
- [ ] T049 [US3] Implement payload validation service in `backend/app/validation/service.py`
- [ ] T050 [US3] Implement required-field validation in `backend/app/validation/service.py`
- [ ] T051 [US3] Implement type validation for string, number, date, boolean, array and object in `backend/app/validation/service.py`
- [ ] T052 [US3] Implement extra-field rejection in `backend/app/validation/service.py`
- [ ] T053 [US3] Implement conditional requiredness for `lingua=EN` fields based on
      `bando_inglese`, raising `CAMPO_INGLESE_MANCANTE` per missing field, in
      `backend/app/validation/service.py`
- [ ] T054 [US3] Implement validation FastAPI router in `backend/app/validation/api.py`

**Checkpoint**: User Story 3 is independently testable through the validation endpoint.

---

## Phase 6: User Story 4 - Gestire errori funzionali comprensibili (Priority: P2)

**Goal**: GEBAN receives structured, stable functional errors for catalog, contract and
validation failures, consistent with `infra/openapi/errors.md` (`009`).

**Independent Test**: Invalid model version, invalid context, invalid tipologia and
invalid payload produce predictable error codes and messages.

### Tests for User Story 4

- [ ] T055 [P] [US4] Add error envelope tests in `backend/tests/common/test_api_error_response.py`
- [ ] T056 [P] [US4] Add invalid context error test in `backend/tests/catalog/test_catalogo_modelli_api.py`

### Implementation for User Story 4

- [ ] T057 [US4] Create domain exception hierarchy in `backend/app/common/errors.py`
- [ ] T058 [US4] Map validation error codes (`CAMPO_OBBLIGATORIO`, `TIPO_NON_VALIDO`,
      `CAMPO_NON_AMMESSO`, `CAMPO_INGLESE_MANCANTE`, `CONTESTO_NON_VALIDO`) in
      `backend/app/validation/errors.py`, keeping the codes aligned with
      `infra/openapi/errors.md`
- [ ] T059 [US4] Map catalog error codes (`MODELLO_VERSIONE_NON_PUBBLICATO`,
      `MODELLO_VERSIONE_NON_TROVATO`, `TIPOLOGIA_SOL_NON_VALIDA`) in
      `backend/app/catalog/errors.py`, keeping the codes aligned with
      `infra/openapi/errors.md`
- [ ] T060 [US4] Ensure routers return stable error envelope in `backend/app/common/errors.py`

**Checkpoint**: User Story 4 is independently testable through negative API scenarios.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Align documentation, contracts and quickstart validation.

- [ ] T061 [P] Update OpenAPI examples reflecting `lingua`/`bando_inglese` in
      `specs/001-catalogo-contratto-geban/contracts/geban-catalog-api.openapi.yaml`
      (structure already updated 2026-07-29; add runtime-verified examples once the
      endpoints exist)
- [ ] T062 [P] Update quickstart with concrete local FastAPI commands, replacing the
      placeholder prerequisites in `specs/001-catalogo-contratto-geban/quickstart.md`
- [ ] T063 Update `infra/openapi/README.md` inventory row for `001` from "Presente" to
      note the implemented endpoints, and add real success/error examples to
      `infra/openapi/examples/` generated from the running service (replacing the
      hand-built demo examples created by `009`)
- [ ] T064 Add README pointer to implemented backend commands in `README.md`
- [ ] T065 Run backend pytest suite (`uv run pytest -m "not e2e" or -k catalog or -k validation`, plus the full `009` suite to confirm no regression) and record result in `specs/001-catalogo-contratto-geban/quickstart.md`
- [ ] T066 Update `docs/quality-coverage-matrix.yaml` rows for FR-004, FR-005, FR-020,
      FR-021, FR-022 from `DA_COPRIRE`/conceptual to `COPERTO` once the corresponding
      tests pass, and update `docs/decision-register.yaml` entries
      `DEC-001-TIPOLOGIE-SOL` / `DEC-001-LINGUA-IT-EN` implementation notes if their
      `impatto` text needs to reflect the shipped behavior

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

- **US1 (P1)**: MVP entry point; no dependency on other user stories after Foundational.
- **US2 (P1)**: requires model version lookup and field persistence (including `lingua`) from Foundational.
- **US3 (P1)**: requires `modello_versione_id` lookup and field contract (including `lingua`) from US2.
- **US4 (P2)**: improves negative scenarios across US1-US3.

### Parallel Opportunities

- T005-T008 can run in parallel after T001-T004.
- T011-T016 can run in parallel after T009-T010.
- T022-T025 can run in parallel.
- T033-T035 can run in parallel.
- T041-T047 can run in parallel.
- T055-T056 can run in parallel.
- T061-T062 can run in parallel after implementation behavior is stable.

## Parallel Example: User Story 3

```text
Task: T041 Add validation success test in backend/tests/validation/test_validazione_payload_api.py
Task: T042 Add missing required field test in backend/tests/validation/test_validazione_payload_api.py
Task: T043 Add wrong type test in backend/tests/validation/test_validazione_payload_api.py
Task: T044 Add extra field rejection test in backend/tests/validation/test_validazione_payload_api.py
Task: T045 Add non-published version validation failure test in backend/tests/validation/test_validazione_payload_api.py
Task: T046 Add bando_inglese missing English field test in backend/tests/validation/test_validazione_bando_inglese.py
Task: T047 Add bando_inglese=false does-not-require-English test in backend/tests/validation/test_validazione_bando_inglese.py
```

## Implementation Strategy

### MVP First

1. Complete Phase 1 and Phase 2.
2. Complete Phase 3 (US1 catalogo, incluso `codice_tipologia`).
3. Validate catalog endpoints with demo data (seed condiviso con `009`).
4. Add Phase 4 and Phase 5 to complete contract and validation flow, incluso `bando_inglese`.

### Incremental Delivery

1. Catalogo tipi/categorie/modelli, con validazione tipologia GEBAN/SOL.
2. Contratto dati per `modello_versione_id`, incluso `lingua` per campo.
3. Validazione payload strict, incluso `bando_inglese`.
4. Error envelope and documentation polish.

## Notes

- All operative calls after catalog selection require `modello_versione_id` (int64,
  `DEC-001-IDENTIFICATIVI-MODELLO`).
- Campi extra in payload are blocking validation errors.
- `codice_tipologia` non riconosciuto e' un errore funzionale (`TIPOLOGIA_SOL_NON_VALIDA`),
  mai un filtro silenzioso.
- Campi `lingua=EN` sono obbligatori solo se `bando_inglese=true`.
- Profilo GEBAN versionato e autorizzazione fine restano fuori scope (FR-023); non
  aggiungere filtri per profilo qui senza prima chiudere `DEC-001-PROFILO-GEBAN`.
