# Tasks: Catalogo Modelli E Contratto Dati GEBAN

**Input**: Design documents from `specs/001-catalogo-contratto-geban/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/geban-catalog-api.openapi.yaml`, `quickstart.md`

**Tests**: Included. The feature is contract-first and the plan requires pytest, httpx/FastAPI TestClient and Testcontainers PostgreSQL.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the FastAPI backend skeleton required by all user stories.

- [ ] T001 Create backend Python project descriptor in `backend/pyproject.toml`
- [ ] T002 Create FastAPI application entry point in `backend/app/main.py`
- [ ] T003 Create base settings module in `backend/app/core/settings.py`
- [ ] T004 Create database session module in `backend/app/db/session.py`
- [ ] T005 [P] Create catalog package under `backend/app/catalog/`
- [ ] T006 [P] Create validation package under `backend/app/validation/`
- [ ] T007 [P] Create common error and security package under `backend/app/common/`
- [ ] T008 [P] Create test support package in `backend/tests/support/`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared data model, migrations, repositories and error envelope that all user stories depend on.

**CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T009 Create initial catalog schema migration in `backend/alembic/versions/001_catalogo_modelli.py`
- [ ] T010 [P] Create `TipoDocumento` SQLAlchemy model in `backend/app/catalog/models.py`
- [ ] T011 [P] Create `CategoriaDocumento` SQLAlchemy model in `backend/app/catalog/models.py`
- [ ] T012 [P] Create `ModelloDocumento` SQLAlchemy model in `backend/app/catalog/models.py`
- [ ] T013 [P] Create `ModelloDocumentoVersione` SQLAlchemy model in `backend/app/catalog/models.py`
- [ ] T014 [P] Create `ModelloCampoRichiesto` SQLAlchemy model in `backend/app/catalog/models.py`
- [ ] T015 Create catalog repository functions in `backend/app/catalog/repository.py`
- [ ] T016 Create common API error schemas in `backend/app/common/errors.py`
- [ ] T017 Create FastAPI exception handlers in `backend/app/common/errors.py`
- [ ] T018 Create catalog seed migration for demo data in `backend/alembic/versions/002_seed_catalogo_demo.py`
- [ ] T019 Create Testcontainers PostgreSQL fixtures in `backend/tests/support/postgres.py`

**Checkpoint**: Foundation ready; user story implementation can begin.

---

## Phase 3: User Story 1 - Consultare modelli pubblicati disponibili (Priority: P1) MVP

**Goal**: GEBAN can list document types, categories and published model versions for a process context.

**Independent Test**: With demo data containing published and non-published versions, catalog calls return only valid published versions in operative mode and archived historical versions in historical mode.

### Tests for User Story 1

- [ ] T020 [P] [US1] Add contract test for `GET /api/v1/catalogo/tipi-documento` in `backend/tests/catalog/test_catalogo_tipi_documento_api.py`
- [ ] T021 [P] [US1] Add contract test for `GET /api/v1/catalogo/tipi-documento/{codiceTipoDocumento}/categorie` in `backend/tests/catalog/test_catalogo_categorie_api.py`
- [ ] T022 [P] [US1] Add contract test for `GET /api/v1/catalogo/modelli` operative and historical modes in `backend/tests/catalog/test_catalogo_modelli_api.py`

### Implementation for User Story 1

- [ ] T023 [P] [US1] Create catalog response Pydantic schemas in `backend/app/catalog/schemas.py`
- [ ] T024 [US1] Implement catalog query service in `backend/app/catalog/service.py`
- [ ] T025 [US1] Implement catalog FastAPI router in `backend/app/catalog/api.py`
- [ ] T026 [US1] Add operative mode filtering for `PUBBLICATO` versions in `backend/app/catalog/service.py`
- [ ] T027 [US1] Add historical mode filtering by publication dates in `backend/app/catalog/service.py`
- [ ] T028 [US1] Add not-found and empty-result handling in `backend/app/catalog/api.py`

**Checkpoint**: User Story 1 is independently testable through catalog endpoints.

---

## Phase 4: User Story 2 - Ottenere il contratto dati del modello (Priority: P1)

**Goal**: GEBAN can request fields and schema for the selected `modello_versione_id`.

**Independent Test**: Given a published model version with required and optional fields, GEBAN receives ordered field metadata and a schema with strict additional-property behavior.

### Tests for User Story 2

- [ ] T029 [P] [US2] Add contract test for `GET /api/v1/catalogo/modelli/{modelloVersioneId}/campi-richiesti` in `backend/tests/catalog/test_campi_richiesti_api.py`
- [ ] T030 [P] [US2] Add test for non-published version rejection in `backend/tests/catalog/test_campi_richiesti_api.py`

### Implementation for User Story 2

- [ ] T031 [P] [US2] Create field contract Pydantic schemas in `backend/app/catalog/schemas.py`
- [ ] T032 [US2] Implement field contract service in `backend/app/catalog/service.py`
- [ ] T033 [US2] Add schema generation with `additionalProperties=false` in `backend/app/catalog/service.py`
- [ ] T034 [US2] Add `campi-richiesti` route to `backend/app/catalog/api.py`
- [ ] T035 [US2] Add conflict handling for non-published versions in `backend/app/common/errors.py`

**Checkpoint**: User Story 2 is independently testable by requesting a contract for a selected model version.

---

## Phase 5: User Story 3 - Validare il payload prima della generazione (Priority: P1)

**Goal**: GEBAN can validate a dynamic payload against the selected model version contract.

**Independent Test**: Valid payloads return `valido=true`; missing required fields, wrong types, extra fields and non-published versions return structured validation errors.

### Tests for User Story 3

- [ ] T036 [P] [US3] Add validation success test in `backend/tests/validation/test_validazione_payload_api.py`
- [ ] T037 [P] [US3] Add missing required field test in `backend/tests/validation/test_validazione_payload_api.py`
- [ ] T038 [P] [US3] Add wrong type test in `backend/tests/validation/test_validazione_payload_api.py`
- [ ] T039 [P] [US3] Add extra field rejection test in `backend/tests/validation/test_validazione_payload_api.py`
- [ ] T040 [P] [US3] Add non-published version validation failure test in `backend/tests/validation/test_validazione_payload_api.py`

### Implementation for User Story 3

- [ ] T041 [P] [US3] Create validation request/response Pydantic schemas in `backend/app/validation/schemas.py`
- [ ] T042 [US3] Implement payload validation service in `backend/app/validation/service.py`
- [ ] T043 [US3] Implement required-field validation in `backend/app/validation/service.py`
- [ ] T044 [US3] Implement type validation for string, number, date, boolean, array and object in `backend/app/validation/service.py`
- [ ] T045 [US3] Implement extra-field rejection in `backend/app/validation/service.py`
- [ ] T046 [US3] Implement validation FastAPI router in `backend/app/validation/api.py`

**Checkpoint**: User Story 3 is independently testable through the validation endpoint.

---

## Phase 6: User Story 4 - Gestire errori funzionali comprensibili (Priority: P2)

**Goal**: GEBAN receives structured, stable functional errors for catalog, contract and validation failures.

**Independent Test**: Invalid model version, invalid context and invalid payload produce predictable error codes and messages.

### Tests for User Story 4

- [ ] T047 [P] [US4] Add error envelope tests in `backend/tests/common/test_api_error_response.py`
- [ ] T048 [P] [US4] Add invalid context error test in `backend/tests/catalog/test_catalogo_modelli_api.py`

### Implementation for User Story 4

- [ ] T049 [US4] Create domain exception hierarchy in `backend/app/common/errors.py`
- [ ] T050 [US4] Map validation error codes in `backend/app/validation/errors.py`
- [ ] T051 [US4] Map catalog error codes in `backend/app/catalog/errors.py`
- [ ] T052 [US4] Ensure routers return stable error envelope in `backend/app/common/errors.py`

**Checkpoint**: User Story 4 is independently testable through negative API scenarios.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Align documentation, contracts and quickstart validation.

- [ ] T053 [P] Update OpenAPI examples in `specs/001-catalogo-contratto-geban/contracts/geban-catalog-api.openapi.yaml`
- [ ] T054 [P] Update quickstart with concrete local FastAPI commands in `specs/001-catalogo-contratto-geban/quickstart.md`
- [ ] T055 Add README pointer to implemented backend commands in `README.md`
- [ ] T056 Run backend pytest suite and record result in `specs/001-catalogo-contratto-geban/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies.
- **Foundational (Phase 2)**: depends on Setup completion; blocks all user stories.
- **US1 Catalogo (Phase 3)**: depends on Foundational.
- **US2 Contratto dati (Phase 4)**: depends on Foundational and reuses catalog version lookup.
- **US3 Validazione payload (Phase 5)**: depends on US2 contract logic.
- **US4 Errori funzionali (Phase 6)**: can begin after Foundational but final integration depends on US1-US3.
- **Polish (Phase 7)**: depends on desired user stories being complete.

### User Story Dependencies

- **US1 (P1)**: MVP entry point; no dependency on other user stories after Foundational.
- **US2 (P1)**: requires model version lookup and field persistence from Foundational.
- **US3 (P1)**: requires `modello_versione_id` lookup and field contract from US2.
- **US4 (P2)**: improves negative scenarios across US1-US3.

### Parallel Opportunities

- T005-T008 can run in parallel after T001-T004.
- T010-T014 can run in parallel after T009.
- T020-T022 can run in parallel.
- T029-T030 can run in parallel.
- T036-T040 can run in parallel.
- T047-T048 can run in parallel.
- T053-T054 can run in parallel after implementation behavior is stable.

## Parallel Example: User Story 3

```text
Task: T036 Add validation success test in backend/tests/validation/test_validazione_payload_api.py
Task: T037 Add missing required field test in backend/tests/validation/test_validazione_payload_api.py
Task: T038 Add wrong type test in backend/tests/validation/test_validazione_payload_api.py
Task: T039 Add extra field rejection test in backend/tests/validation/test_validazione_payload_api.py
Task: T040 Add non-published version validation failure test in backend/tests/validation/test_validazione_payload_api.py
```

## Implementation Strategy

### MVP First

1. Complete Phase 1 and Phase 2.
2. Complete Phase 3 (US1 catalogo).
3. Validate catalog endpoints with demo data.
4. Add Phase 4 and Phase 5 to complete contract and validation flow.

### Incremental Delivery

1. Catalogo tipi/categorie/modelli.
2. Contratto dati per `modello_versione_id`.
3. Validazione payload strict.
4. Error envelope and documentation polish.

## Notes

- All operative calls after catalog selection require `modello_versione_id`.
- Campi extra in payload are blocking validation errors.
