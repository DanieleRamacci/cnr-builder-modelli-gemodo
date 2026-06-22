# Tasks: Sezioni Placeholder E Versionamento

**Input**: Design documents from `specs/003-sezioni-placeholder-versionamento/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Include unit, integration and contract tests because section immutability,
placeholder validation and complex-field schemas directly affect publication correctness.

**Organization**: Tasks are grouped by user story to enable independent implementation and
testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Extend the backend builder module with sections, templates and placeholder validation areas.

- [ ] T001 Create sections package structure under `backend/app/modelli/sezioni/`
- [ ] T002 Create placeholder validation package under `backend/app/modelli/placeholder/`
- [ ] T003 Create complex field schema package under `backend/app/modelli/campi_complessi/`
- [ ] T004 [P] Create contract test package under `backend/tests/modelli/contract/sezioni/`
- [ ] T005 [P] Create integration test package under `backend/tests/modelli/integration/sezioni/`
- [ ] T006 [P] Add OpenAPI contract reference from `specs/003-sezioni-placeholder-versionamento/contracts/sezioni-placeholder-api.openapi.yaml` to backend API docs

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Database and domain primitives shared by section and placeholder stories.

**CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T007 Create `sezione_modello` migration in `backend/alembic/versions/`
- [ ] T008 Create `template_sezione` migration in `backend/alembic/versions/`
- [ ] T009 Create `campo_complesso_schema` and `sotto_campo_schema` migration in `backend/alembic/versions/`
- [ ] T010 [P] Create `SezioneModello` SQLAlchemy model in `backend/app/modelli/sezioni/models.py`
- [ ] T011 [P] Create `TemplateSezione` SQLAlchemy model in `backend/app/modelli/sezioni/models.py`
- [ ] T012 [P] Create `CampoComplessoSchema` and `SottoCampoSchema` SQLAlchemy models in `backend/app/modelli/campi_complessi/models.py`
- [ ] T013 [P] Create Pydantic schemas for structured section content in `backend/app/modelli/sezioni/schemas.py`
- [ ] T014 [P] Create validation error codes for sections and placeholders in `backend/app/modelli/placeholder/errors.py`
- [ ] T015 Create repository functions for sections and templates in `backend/app/modelli/sezioni/repository.py`
- [ ] T016 Create repository functions for complex-field schemas in `backend/app/modelli/campi_complessi/repository.py`

**Checkpoint**: Foundation ready - user story implementation can now begin.

---

## Phase 3: User Story 1 - Gestire sezioni della versione modello (Priority: P1) Prima versione funzionante

**Goal**: Create, update, order and copy sections owned by a model version, while preventing changes to published model versions.

**Independent Test**: A draft model version can create and edit sections; a published model version rejects direct section edits.

### Tests for User Story 1

- [ ] T017 [P] [US1] Add contract tests for `GET /modelli/{modelloId}/versioni/{versioneId}/sezioni` in `backend/tests/modelli/contract/sezioni/test_list_sezioni_api.py`
- [ ] T018 [P] [US1] Add contract tests for creating and updating sections in `backend/tests/modelli/contract/sezioni/test_upsert_sezioni_api.py`
- [ ] T019 [P] [US1] Add integration tests for draft section create/update/order in `backend/tests/modelli/integration/sezioni/test_sezioni_bozza.py`
- [ ] T020 [P] [US1] Add integration tests for rejecting section edits on published versions in `backend/tests/modelli/integration/sezioni/test_sezioni_immutabili.py`
- [ ] T021 [P] [US1] Add integration tests for copying sections into a derived model version in `backend/tests/modelli/integration/sezioni/test_copia_sezioni_versione.py`

### Implementation for User Story 1

- [ ] T022 [P] [US1] Implement structured content validation in `backend/app/modelli/sezioni/validation.py`
- [ ] T023 [US1] Implement `SezioneModelloService` create/update/list operations in `backend/app/modelli/sezioni/service.py`
- [ ] T024 [US1] Enforce model-version mutability before section changes in `backend/app/modelli/sezioni/service.py`
- [ ] T025 [US1] Implement section copy service for derived model versions in `backend/app/modelli/sezioni/copy_service.py`
- [ ] T026 [US1] Implement sections FastAPI router in `backend/app/modelli/sezioni/api.py`
- [ ] T027 [US1] Register sections router in `backend/app/main.py`
- [ ] T028 [US1] Record audit events for section create/update/copy in `backend/app/modelli/service/audit.py`

**Checkpoint**: Sections are owned by model versions and immutable after publication.

---

## Phase 4: User Story 2 - Dichiarare placeholder e campi complessi (Priority: P1)

**Goal**: Validate placeholder usage against fields associated to the model version and define explicit schemas for complex fields.

**Independent Test**: A model version cannot pass validation if sections contain placeholders not associated with the model, or if complex fields lack explicit sub-field schema.

### Tests for User Story 2

- [ ] T029 [P] [US2] Add unit tests for extracting placeholders from structured content in `backend/tests/modelli/unit/test_placeholder_parser.py`
- [ ] T030 [P] [US2] Add integration tests for unavailable placeholder rejection in `backend/tests/modelli/integration/sezioni/test_placeholder_validation.py`
- [ ] T031 [P] [US2] Add integration tests for required placeholder missing in `backend/tests/modelli/integration/sezioni/test_placeholder_validation.py`
- [ ] T032 [P] [US2] Add contract tests for `/modelli/{modelloId}/versioni/{versioneId}/sezioni/valida` in `backend/tests/modelli/contract/sezioni/test_validazione_sezioni_api.py`
- [ ] T033 [P] [US2] Add contract tests for complex field schema endpoint in `backend/tests/modelli/contract/sezioni/test_schema_campi_complessi_api.py`
- [ ] T034 [P] [US2] Add integration tests for complex field sub-field validation in `backend/tests/modelli/integration/sezioni/test_campi_complessi.py`

### Implementation for User Story 2

- [ ] T035 [P] [US2] Implement placeholder parser for structured content in `backend/app/modelli/placeholder/parser.py`
- [ ] T036 [US2] Implement placeholder availability validator in `backend/app/modelli/placeholder/validation.py`
- [ ] T037 [US2] Implement required-placeholder usage validator in `backend/app/modelli/placeholder/validation.py`
- [ ] T038 [US2] Implement section validation service in `backend/app/modelli/sezioni/validation_service.py`
- [ ] T039 [P] [US2] Implement Pydantic schemas for complex-field schema requests in `backend/app/modelli/campi_complessi/schemas.py`
- [ ] T040 [US2] Implement complex-field schema service in `backend/app/modelli/campi_complessi/service.py`
- [ ] T041 [US2] Implement complex-field schema router in `backend/app/modelli/campi_complessi/api.py`
- [ ] T042 [US2] Add section validation route to `backend/app/modelli/sezioni/api.py`
- [ ] T043 [US2] Ensure publication workflow calls section/placeholder validation in `backend/app/modelli/service/pubblicazione.py`

**Checkpoint**: Placeholder and complex-field validation are ready for publication gating.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, examples and consistency with adjacent specs.

- [ ] T044 [P] Update OpenAPI examples in `specs/003-sezioni-placeholder-versionamento/contracts/sezioni-placeholder-api.openapi.yaml`
- [ ] T045 [P] Add demo template and section seed data in `backend/alembic/versions/`
- [ ] T046 [P] Update quickstart validation notes in `specs/003-sezioni-placeholder-versionamento/quickstart.md`
- [ ] T047 Run all section/placeholder pytest tests and record result in `specs/003-sezioni-placeholder-versionamento/quickstart.md`
- [ ] T048 Run cross-spec consistency check against specs 001 and 002 for `modello_versione_id`, fields and publication rules in `docs/project-map.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies.
- **Foundational (Phase 2)**: depends on setup and blocks all user stories.
- **US1 (Phase 3)**: depends on foundational phase.
- **US2 (Phase 4)**: depends on foundational phase and integrates with US1 section data.
- **Polish (Phase 5)**: depends on selected user stories being complete.

### User Story Dependencies

- **US1**: first functional increment; creates and protects sections owned by model versions.
- **US2**: can start after foundational phase but final publication validation depends on US1 section persistence.

### Parallel Opportunities

- T004-T006 can run in parallel after T001-T003.
- T010-T014 can run in parallel after migrations are planned.
- US1 tests T017-T021 can run in parallel.
- US2 tests T029-T034 can run in parallel.
- T035 and T039 can run in parallel before validator/service integration.
- Polish tasks T044-T046 can run in parallel.

## Parallel Example: User Story 2

```text
Task: "Add unit tests for extracting placeholders from structured content"
Task: "Add integration tests for unavailable placeholder rejection"
Task: "Add integration tests for required placeholder missing"
Task: "Add contract tests for section validation endpoint"
Task: "Implement placeholder parser for structured content"
Task: "Implement Pydantic schemas for complex-field schema requests"
```

## Implementation Strategy

### Prima Versione Funzionante

1. Complete Phase 1 and Phase 2.
2. Complete US1 to manage sections owned by a model version.
3. Validate that published model versions reject direct section edits.
4. Add US2 to gate publication through placeholder and complex-field validation.

### Safety Rules

- Do not add autonomous section versioning in this feature.
- Do not add conditional sections in this feature.
- Do not allow HTML libero in section content.
- Do not derive the GEBAN contract from section text; use fields associated with the model version.
- Do not publish a model version if section content uses unavailable placeholders.
