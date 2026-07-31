# Tasks: Sezioni Placeholder E Versionamento

**Input**: Design documents from `specs/003-sezioni-placeholder-versionamento/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/sezioni-placeholder-api.openapi.yaml`, `quickstart.md`

**Tests**: Include unit, integration and contract tests because section immutability, controlled document model validation, placeholder validation and complex-field schemas directly affect publication correctness.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Extend the protected builder backend with sections, document model, placeholders and complex fields.

- [ ] T001 Create sections package structure under `backend/app/builder/sections/`
- [ ] T002 Create placeholder validation package under `backend/app/builder/placeholders/`
- [ ] T003 Create complex field schema package under `backend/app/builder/complex_fields/`
- [ ] T004 Create controlled document model package under `backend/app/builder/document_model/`
- [ ] T005 [P] Create contract test package under `backend/tests/builder/contract/sections/`
- [ ] T006 [P] Create integration test package under `backend/tests/builder/integration/sections/`
- [ ] T007 [P] Create unit test package under `backend/tests/builder/unit/document_model/`
- [ ] T008 [P] Add OpenAPI contract publication wiring for `specs/003-sezioni-placeholder-versionamento/contracts/sezioni-placeholder-api.openapi.yaml` in the existing API docs support

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Database, schemas, security and validation primitives shared by section and placeholder stories.

**CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T009 Create sections/document-model migration in `backend/alembic/versions/0006_sections_document_model.py`
- [ ] T010 Create complex field schema migration in `backend/alembic/versions/0007_complex_field_schema.py`
- [ ] T011 [P] Create `SezioneModello` and `TemplateSezione` SQLAlchemy mappings in `backend/app/builder/sections/models.py`
- [ ] T012 [P] Create `ModelloDocumentaleControllato`, `BloccoDocumento` and `AssetDocumento` persistence mappings in `backend/app/builder/document_model/models.py`
- [ ] T013 [P] Create `CampoComplessoSchema` and `SottoCampoSchema` SQLAlchemy mappings in `backend/app/builder/complex_fields/models.py`
- [ ] T014 [P] Create Pydantic schemas for sections and templates in `backend/app/builder/sections/schemas.py`
- [ ] T015 [P] Create Pydantic schemas for `GEMODO_DOCUMENT_V1` in `backend/app/builder/document_model/schemas.py`
- [ ] T016 [P] Create Pydantic schemas for complex-field schema requests in `backend/app/builder/complex_fields/schemas.py`
- [ ] T017 Add section, placeholder and document-model error codes in `backend/app/common/errors.py`
- [ ] T018 Create authorization helpers reusing `require_modelli_viewer` and `require_modelli_gestore` in `backend/app/builder/api/security.py`
- [ ] T019 Create audit event helpers for section/template/document-model changes in `backend/app/builder/service/audit.py`

**Checkpoint**: Foundation ready; user story implementation can now begin.

---

## Phase 3: User Story 1 - Gestire sezioni della versione modello (Priority: P1)

**Goal**: Create, update, order and copy sections owned by a model version, while preventing changes to published model versions.

**Independent Test**: A draft model version can create and edit sections; a published model version rejects direct section edits.

### Tests for User Story 1

- [ ] T020 [P] [US1] Add contract tests for protected `GET /api/v1/builder/modelli/{modelloId}/versioni/{versioneId}/sezioni` in `backend/tests/builder/contract/sections/test_list_sezioni_api.py`
- [ ] T021 [P] [US1] Add contract tests for protected create/update section routes in `backend/tests/builder/contract/sections/test_upsert_sezioni_api.py`
- [ ] T022 [P] [US1] Add authorization tests for viewer versus manager on section routes in `backend/tests/builder/contract/sections/test_sections_auth_api.py`
- [ ] T023 [P] [US1] Add integration tests for draft section create/update/order in `backend/tests/builder/integration/sections/test_sezioni_bozza.py`
- [ ] T024 [P] [US1] Add integration tests for rejecting section edits on published versions in `backend/tests/builder/integration/sections/test_sezioni_immutabili.py`
- [ ] T025 [P] [US1] Add integration tests for copying sections into a derived model version in `backend/tests/builder/integration/sections/test_copia_sezioni_versione.py`
- [ ] T026 [P] [US1] Add integration tests proving template updates do not mutate copied sections in `backend/tests/builder/integration/sections/test_template_copiabili.py`

### Implementation for User Story 1

- [ ] T027 [US1] Implement section repository functions in `backend/app/builder/sections/repository.py`
- [ ] T028 [US1] Implement template repository functions in `backend/app/builder/sections/template_repository.py`
- [ ] T029 [US1] Implement `SezioneModelloService` create/update/list/reorder operations in `backend/app/builder/sections/service.py`
- [ ] T030 [US1] Enforce model-version mutability before section changes using `backend/app/builder/service/workflow.py` in `backend/app/builder/sections/service.py`
- [ ] T031 [US1] Implement section copy service for derived model versions in `backend/app/builder/sections/copy_service.py`
- [ ] T032 [US1] Implement template copy service in `backend/app/builder/sections/template_service.py`
- [ ] T033 [US1] Implement sections and template FastAPI routes in `backend/app/builder/sections/api.py`
- [ ] T034 [US1] Apply `require_modelli_viewer` to reads and `require_modelli_gestore` to writes in `backend/app/builder/sections/api.py`
- [ ] T035 [US1] Record audit events for section create/update/reorder/copy/template operations in `backend/app/builder/service/audit.py`
- [ ] T036 [US1] Register section routes in `backend/app/builder/api/__init__.py`

**Checkpoint**: Sections are owned by model versions and immutable after publication.

---

## Phase 4: User Story 2 - Dichiarare placeholder e campi complessi (Priority: P1)

**Goal**: Validate placeholder usage against fields associated to the model version and define explicit schemas for complex fields.

**Independent Test**: A model version cannot pass validation if sections contain placeholders not associated with the model, or if complex fields lack explicit sub-field schema.

### Tests for User Story 2

- [ ] T037 [P] [US2] Add unit tests for extracting placeholders from `GEMODO_DOCUMENT_V1` blocks in `backend/tests/builder/unit/document_model/test_placeholder_parser.py`
- [ ] T038 [P] [US2] Add integration tests for unavailable placeholder rejection in `backend/tests/builder/integration/sections/test_placeholder_validation.py`
- [ ] T039 [P] [US2] Add integration tests for required placeholder missing in `backend/tests/builder/integration/sections/test_placeholder_validation.py`
- [ ] T040 [P] [US2] Add contract tests for `POST /api/v1/builder/modelli/{modelloId}/versioni/{versioneId}/sezioni/valida` in `backend/tests/builder/contract/sections/test_validazione_sezioni_api.py`
- [ ] T041 [P] [US2] Add contract tests for complex field schema endpoint in `backend/tests/builder/contract/sections/test_schema_campi_complessi_api.py`
- [ ] T042 [P] [US2] Add integration tests for complex field sub-field validation in `backend/tests/builder/integration/sections/test_campi_complessi.py`

### Implementation for User Story 2

- [ ] T043 [P] [US2] Implement placeholder parser for sections and document model blocks in `backend/app/builder/placeholders/parser.py`
- [ ] T044 [US2] Implement placeholder availability validator against `backend/app/catalog/models.py` fields in `backend/app/builder/placeholders/validation.py`
- [ ] T045 [US2] Implement required-placeholder usage validator in `backend/app/builder/placeholders/validation.py`
- [ ] T046 [US2] Implement section validation service in `backend/app/builder/sections/validation_service.py`
- [ ] T047 [US2] Implement complex-field schema repository in `backend/app/builder/complex_fields/repository.py`
- [ ] T048 [US2] Implement complex-field schema service in `backend/app/builder/complex_fields/service.py`
- [ ] T049 [US2] Implement complex-field schema router in `backend/app/builder/complex_fields/api.py`
- [ ] T050 [US2] Add section validation route to `backend/app/builder/sections/api.py`
- [ ] T051 [US2] Ensure publication workflow calls section/placeholder/complex-field validation in `backend/app/builder/service/pubblicazione.py`

**Checkpoint**: Placeholder and complex-field validation are ready for publication gating.

---

## Phase 5: User Story 3 - Validare modello documentale controllato (Priority: P1)

**Goal**: Store and validate `GEMODO_DOCUMENT_V1` without HTML/CSS/script libero, with allowed blocks, positions, assets, styles and placeholders.

**Independent Test**: A valid controlled model passes validation; a model with free HTML, free CSS, script, invalid block position or unknown asset is rejected.

### Tests for User Story 3

- [ ] T052 [P] [US3] Add unit tests for allowed block type and position validation in `backend/tests/builder/unit/document_model/test_document_model_validation.py`
- [ ] T053 [P] [US3] Add unit tests for rejecting HTML, CSS and script flags in `backend/tests/builder/unit/document_model/test_document_model_validation.py`
- [ ] T054 [P] [US3] Add unit tests for asset reference and style validation in `backend/tests/builder/unit/document_model/test_document_model_validation.py`
- [ ] T055 [P] [US3] Add contract tests for protected `PUT /api/v1/builder/modelli/{modelloId}/versioni/{versioneId}/document-model` in `backend/tests/builder/contract/sections/test_document_model_api.py`
- [ ] T056 [P] [US3] Add contract tests for document-model validation endpoint in `backend/tests/builder/contract/sections/test_document_model_api.py`
- [ ] T057 [P] [US3] Add integration test loading `infra/local/document-models/bando-concorso-standard-v1.yaml` in `backend/tests/builder/integration/sections/test_document_model_demo.py`

### Implementation for User Story 3

- [ ] T058 [P] [US3] Port controlled document validation from `backend/app/quality/document_model.py` into runtime builder service `backend/app/builder/document_model/validation.py`
- [ ] T059 [US3] Implement document-model repository functions in `backend/app/builder/document_model/repository.py`
- [ ] T060 [US3] Implement document-model save and validate service in `backend/app/builder/document_model/service.py`
- [ ] T061 [US3] Implement document-model FastAPI routes in `backend/app/builder/document_model/api.py`
- [ ] T062 [US3] Apply `require_modelli_viewer` to validation reads and `require_modelli_gestore` to save/validate-for-publication routes in `backend/app/builder/document_model/api.py`
- [ ] T063 [US3] Register document-model routes in `backend/app/builder/api/__init__.py`

**Checkpoint**: `GEMODO_DOCUMENT_V1` is validated as runtime builder data and ready for renderer handoff in `004`.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, examples and consistency with adjacent specs.

- [ ] T064 [P] Update success and error examples in `specs/003-sezioni-placeholder-versionamento/contracts/sezioni-placeholder-api.openapi.yaml`
- [ ] T065 [P] Add demo template, sections and controlled document seed data in `infra/local/document-models/bando-concorso-standard-v1.yaml`
- [ ] T066 [P] Update quickstart validation notes in `specs/003-sezioni-placeholder-versionamento/quickstart.md`
- [ ] T067 [P] Update generated Spec Kit documentation from `scripts/generate-spec-docs.py`
- [ ] T068 Run section/placeholder/document-model pytest tests and related `001`/`002` compatibility tests from `backend/`
- [ ] T069 Run cross-spec consistency check against specs `001`, `002`, `004` and `007` for `modello_versione_id`, fields, publication rules and controlled renderer input in `docs/project-map.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies.
- **Foundational (Phase 2)**: depends on setup and blocks all user stories.
- **US1 (Phase 3)**: depends on foundational phase.
- **US2 (Phase 4)**: depends on foundational phase and integrates with US1 section data.
- **US3 (Phase 5)**: depends on foundational phase and integrates with US1/US2 validation.
- **Polish (Phase 6)**: depends on selected user stories being complete.

### Cross-Spec Dependencies

- `001` supplies field contracts and placeholder availability.
- `002` supplies model version lifecycle, mutability checks, publication workflow and builder roles.
- `004` consumes `GEMODO_DOCUMENT_V1` as renderer input.
- `007` provides the frontend editor over this controlled backend contract.
- `009` supplies the prototype controlled model and validator used as implementation reference.

### User Story Dependencies

- **US1**: first productive increment; creates and protects sections owned by model versions.
- **US2**: can start after foundational phase but final publication validation depends on US1 section persistence.
- **US3**: can start after foundational phase, but full validation depends on placeholder and section rules from US1/US2.

### Parallel Opportunities

- T005-T008 can run in parallel after T001-T004.
- T011-T016 can run in parallel after migrations are planned.
- US1 tests T020-T026 can run in parallel.
- US2 tests T037-T042 can run in parallel.
- US3 tests T052-T057 can run in parallel.
- Polish tasks T064-T067 can run in parallel.

## Parallel Example: User Story 3

```text
Task: "Add unit tests for allowed block type and position validation"
Task: "Add unit tests for rejecting HTML, CSS and script flags"
Task: "Add unit tests for asset reference and style validation"
Task: "Add contract tests for protected document-model route"
Task: "Port controlled document validation into runtime builder service"
```

## Implementation Strategy

### Primo Incremento Produttivo

1. Complete Phase 1 and Phase 2.
2. Complete US1 to manage sections owned by a model version.
3. Validate that published model versions reject direct section edits.
4. Add US2 to gate publication through placeholder and complex-field validation.
5. Add US3 to persist and validate `GEMODO_DOCUMENT_V1` as renderer input.

### Safety Rules

- Do not add autonomous section versioning in this feature.
- Do not add conditional sections in this feature.
- Do not allow HTML/CSS/script libero in builder-authored content.
- Do not derive the GEBAN contract from section text; use fields associated with the model version.
- Do not publish a model version if section content uses unavailable placeholders.
- Do not save assets as free embedded content; reference id/version/storage/hash.
- Do not rely on frontend checks for authorization; protected builder APIs must enforce JWT roles in the backend.
