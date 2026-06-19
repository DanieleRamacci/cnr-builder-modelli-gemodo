# Tasks: Builder Modelli Documentali

**Input**: Design documents from `specs/002-builder-modelli/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Include unit, integration and contract tests because the feature defines workflow
states, uniqueness constraints and API contracts that must be protected from regression.

**Organization**: Tasks are grouped by user story to enable independent implementation and
testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: FastAPI backend project structure and builder module skeleton.

- [ ] T001 Create builder module structure under `backend/app/modelli/`
- [ ] T002 Create test package structure under `backend/tests/modelli/`
- [ ] T003 [P] Add builder OpenAPI contract file to backend API docs from `specs/002-builder-modelli/contracts/builder-modelli-api.openapi.yaml`
- [ ] T004 [P] Configure Alembic migration location for builder tables in `backend/alembic/versions/`
- [ ] T005 [P] Add builder module package documentation in `backend/app/modelli/README.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared domain primitives required by all user stories.

**CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T006 Create `stato_modello_versione` enum migration in `backend/alembic/versions/`
- [ ] T007 Create shared error schemas and builder error codes in `backend/app/modelli/api/errors.py`
- [ ] T008 [P] Create `StatoModelloVersione` enum in `backend/app/modelli/domain/stati.py`
- [ ] T009 [P] Create base audit event type definitions in `backend/app/modelli/domain/audit.py`
- [ ] T010 Create transaction boundary convention for builder services in `backend/app/modelli/service/`
- [ ] T011 Create common validation helpers for codes, labels and active-state checks in `backend/app/modelli/validation/`
- [ ] T012 [P] Create shared FastAPI exception handlers in `backend/app/modelli/api/errors.py`

**Checkpoint**: Foundation ready - user story implementation can now begin.

---

## Phase 3: User Story 1 - Configurare tipi e categorie documento (Priority: P1) MVP

**Goal**: Gestire tipi documento e categorie attive/non attive.

**Independent Test**: dato un tipo documento e una categoria attivi, il gestore puo'
renderli disponibili alla configurazione di un modello.

### Tests for User Story 1

- [ ] T013 [P] [US1] Add contract tests for `/tipi-documento` in `backend/tests/modelli/contract/test_tipi_documento_api.py`
- [ ] T014 [P] [US1] Add contract tests for `/tipi-documento/{codice}/categorie` in `backend/tests/modelli/contract/test_categorie_documento_api.py`
- [ ] T015 [P] [US1] Add integration tests for type/category creation and duplicate handling in `backend/tests/modelli/integration/test_tipi_categorie.py`

### Implementation for User Story 1

- [ ] T016 [US1] Create `tipo_documento` migration in `backend/alembic/versions/`
- [ ] T017 [US1] Create `categoria_documento` migration with composite key in `backend/alembic/versions/`
- [ ] T018 [P] [US1] Create `TipoDocumento` SQLAlchemy model in `backend/app/modelli/domain/tipo_documento.py`
- [ ] T019 [P] [US1] Create `CategoriaDocumento` SQLAlchemy model in `backend/app/modelli/domain/categoria_documento.py`
- [ ] T020 [P] [US1] Create repositories for tipo and categoria in `backend/app/modelli/repository/`
- [ ] T021 [US1] Implement type/category validation in `backend/app/modelli/validation/classificazione.py`
- [ ] T022 [US1] Implement `TipoDocumentoService` in `backend/app/modelli/service/tipi_documento.py`
- [ ] T023 [US1] Implement `CategoriaDocumentoService` in `backend/app/modelli/service/categorie_documento.py`
- [ ] T024 [US1] Implement builder routers for types and categories in `backend/app/modelli/api/classificazione.py`
- [ ] T025 [US1] Record audit events for type/category create and update operations in `backend/app/modelli/service/audit.py`

**Checkpoint**: Tipi e categorie are independently usable by the builder backend.

---

## Phase 4: User Story 2 - Gestire modelli e versioni (Priority: P1)

**Goal**: Creare modelli, assegnare variante obbligatoria, creare versioni e impedire
modifiche dirette a versioni pubblicate.

**Independent Test**: dato un modello in bozza, il gestore puo' creare una versione,
modificarla e portarla a uno stato di revisione/pubblicazione.

### Tests for User Story 2

- [ ] T026 [P] [US2] Add contract tests for `/modelli` create/list in `backend/tests/modelli/contract/test_modelli_api.py`
- [ ] T027 [P] [US2] Add contract tests for `/modelli/{modelloId}/versioni` in `backend/tests/modelli/contract/test_versioni_api.py`
- [ ] T028 [P] [US2] Add integration tests for default `STANDARD` variant in `backend/tests/modelli/integration/test_varianti.py`
- [ ] T029 [P] [US2] Add integration tests for duplicate variant rejection in `backend/tests/modelli/integration/test_varianti.py`
- [ ] T030 [P] [US2] Add unit tests for version mutability rules in `backend/tests/modelli/unit/test_mutabilita_versione.py`

### Implementation for User Story 2

- [ ] T031 [US2] Create `modello_documento` migration with variant default and uniqueness rules in `backend/alembic/versions/`
- [ ] T032 [US2] Create `modello_documento_versione` migration in `backend/alembic/versions/`
- [ ] T033 [US2] Create `modello_campo_richiesto` migration in `backend/alembic/versions/`
- [ ] T034 [P] [US2] Create `ModelloDocumento` SQLAlchemy model in `backend/app/modelli/domain/modello_documento.py`
- [ ] T035 [P] [US2] Create `ModelloDocumentoVersione` SQLAlchemy model in `backend/app/modelli/domain/modello_versione.py`
- [ ] T036 [P] [US2] Create `ModelloCampoRichiesto` SQLAlchemy model in `backend/app/modelli/domain/campo_richiesto.py`
- [ ] T037 [P] [US2] Create repositories for model, version and required fields in `backend/app/modelli/repository/`
- [ ] T038 [US2] Implement `ModelloDocumentoService` with variant default `STANDARD` in `backend/app/modelli/service/modelli.py`
- [ ] T039 [US2] Implement `ModelloVersioneService` with bozza creation and derived version rules in `backend/app/modelli/service/versioni.py`
- [ ] T040 [US2] Implement immutability guard for `PUBBLICATO` versions in `backend/app/modelli/validation/versioni.py`
- [ ] T041 [US2] Implement model and version routers in `backend/app/modelli/api/modelli.py`
- [ ] T042 [US2] Record audit events for model creation and version modification in `backend/app/modelli/service/audit.py`

**Checkpoint**: Models and draft/derived versions are independently manageable.

---

## Phase 5: User Story 3 - Pubblicare e archiviare versioni modello (Priority: P1)

**Goal**: Pubblicare versioni approvate, archiviare versioni pubblicate e garantire una
sola versione pubblicata corrente per variante.

**Independent Test**: una versione non pubblicata non appare nel catalogo operativo; una
versione pubblicata valida appare nel catalogo.

### Tests for User Story 3

- [ ] T043 [P] [US3] Add contract tests for `/modelli/{modelloId}/versioni/{versioneId}/pubblica` in `backend/tests/modelli/contract/test_pubblicazione_api.py`
- [ ] T044 [P] [US3] Add contract tests for `/modelli/{modelloId}/versioni/{versioneId}/archivia` in `backend/tests/modelli/contract/test_archiviazione_api.py`
- [ ] T045 [P] [US3] Add integration tests for automatic archive of previous current version in `backend/tests/modelli/integration/test_pubblicazione.py`
- [ ] T046 [P] [US3] Add integration tests for preventing two current published versions in same variant in `backend/tests/modelli/integration/test_pubblicazione.py`
- [ ] T047 [P] [US3] Add integration tests for allowing separate published variants in same context in `backend/tests/modelli/integration/test_pubblicazione.py`

### Implementation for User Story 3

- [ ] T048 [US3] Implement allowed state transitions in `backend/app/modelli/service/versioni.py`
- [ ] T049 [US3] Implement transactional publication with automatic archive of previous current version in `backend/app/modelli/service/pubblicazione.py`
- [ ] T050 [US3] Implement archive and suspend operations in `backend/app/modelli/service/pubblicazione.py`
- [ ] T051 [US3] Implement publish/archive routers in `backend/app/modelli/api/pubblicazione.py`
- [ ] T052 [US3] Add database constraint or transactional lock strategy for one `PUBBLICATO` current version per variant in `backend/alembic/versions/`
- [ ] T053 [US3] Record audit events for approve, publish, archive and suspend transitions in `backend/app/modelli/service/audit.py`
- [ ] T054 [US3] Verify catalog compatibility with spec 001 data model in `backend/tests/modelli/integration/test_catalogo_compatibilita.py`

**Checkpoint**: Publication workflow is independently usable and catalog-safe.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Alignment, documentation and validation across the feature.

- [ ] T055 [P] Update generated API examples from `specs/002-builder-modelli/contracts/builder-modelli-api.openapi.yaml`
- [ ] T056 [P] Update seed/demo data for one standard variant and one custom variant in `backend/alembic/versions/`
- [ ] T057 [P] Add quickstart validation notes to `specs/002-builder-modelli/quickstart.md`
- [ ] T058 Run all builder pytest tests and record result in `specs/002-builder-modelli/quickstart.md`
- [ ] T059 Run cross-spec consistency check between specs 001 and 002 for variant/version rules in `docs/project-map.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies.
- **Foundational (Phase 2)**: depends on setup and blocks all user stories.
- **US1 (Phase 3)**: depends on foundational phase.
- **US2 (Phase 4)**: depends on foundational phase; implementation uses type/category data from US1 for full validation.
- **US3 (Phase 5)**: depends on US2 version model and services.
- **Polish (Phase 6)**: depends on selected user stories being complete.

### User Story Dependencies

- **US1**: first MVP increment; creates classification base.
- **US2**: can start after foundational phase, but final validation depends on US1 entities.
- **US3**: depends on US2 because publication operates on versions.

### Parallel Opportunities

- T003-T005 can run in parallel after T001-T002.
- T008-T009 and T012 can run in parallel during foundation.
- US1 tests T013-T015 can run in parallel.
- US1 entities/repositories T018-T020 can run in parallel after migrations.
- US2 tests T026-T030 can run in parallel.
- US2 entities T034-T037 can run in parallel after migrations.
- US3 tests T043-T047 can run in parallel.
- Polish tasks T055-T057 can run in parallel.

## Parallel Example: User Story 2

```text
Task: "Add integration tests for default STANDARD variant"
Task: "Add integration tests for duplicate variant rejection"
Task: "Create ModelloDocumento SQLAlchemy model"
Task: "Create ModelloDocumentoVersione SQLAlchemy model"
Task: "Create ModelloCampoRichiesto SQLAlchemy model"
```

## Implementation Strategy

### MVP First

1. Complete Phase 1 and Phase 2.
2. Complete US1 to manage document types and categories.
3. Validate US1 independently with contract and integration tests.
4. Add US2 for model/version drafting and immutability.
5. Add US3 for publication and archive workflow.

### Safety Rules

- Do not implement direct reads from GEBAN DB.
- Do not expose non-`PUBBLICATO` versions to the catalog operative path.
- Do not update published content in place.
- Do not publish a new version without archiving the previous current version of the same variant in the same transaction.
