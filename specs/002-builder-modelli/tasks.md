# Tasks: Builder Modelli Documentali

**Input**: Design documents from `specs/002-builder-modelli/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/builder-modelli-api.openapi.yaml`, `quickstart.md`

**Tests**: Include unit, integration and contract tests because the feature defines protected administrative APIs, workflow states, uniqueness constraints, transactional publication and API contracts.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Builder API skeleton over the shared catalog domain.

- [ ] T001 Create builder package structure `api/`, `repository/`, `service/`, `validation/` under `backend/app/builder/`
- [ ] T002 Create builder test package structure `contract/`, `integration/`, `unit/` under `backend/tests/builder/`
- [ ] T003 Register a builder router include point in `backend/app/main.py`
- [ ] T004 [P] Add builder OpenAPI contract publication wiring for `specs/002-builder-modelli/contracts/builder-modelli-api.openapi.yaml` in the existing API docs support
- [ ] T005 [P] Add builder module documentation in `backend/app/builder/README.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared builder primitives required by all user stories.

**CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T006 Extend the shared catalog persistence design in `backend/app/catalog/models.py` without introducing duplicate `tipo_documento`, `categoria_documento`, `modello_documento` or `modello_versione` tables
- [ ] T007 Create builder workflow migration in `backend/alembic/versions/0005_builder_admin_workflow.py` for state metadata, audit table and publication uniqueness constraints
- [ ] T008 [P] Create builder workflow enum and transition rules in `backend/app/builder/service/workflow.py`
- [ ] T009 [P] Create builder Pydantic schemas in `backend/app/builder/api/schemas.py`
- [ ] T010 Create builder authorization dependencies using `backend/app/common/security.py` in `backend/app/builder/api/security.py`
- [ ] T011 Add builder error codes including `ACCESSO_NON_AUTENTICATO`, `ACCESSO_NON_AUTORIZZATO`, `MODELLO_VERSIONE_NON_MODIFICABILE` and `VERSIONE_CORRENTE_DUPLICATA` in `backend/app/common/errors.py`
- [ ] T012 [P] Create builder validation helpers for codes, labels, active state and duplicate variants in `backend/app/builder/validation/classificazione.py`
- [ ] T013 Create builder audit service for model/version state changes in `backend/app/builder/service/audit.py`

**Checkpoint**: Foundation ready; user story implementation can now begin.

---

## Phase 3: User Story 1 - Configurare tipi e categorie documento (Priority: P1)

**Goal**: Gestire tipi documento e categorie attive/non attive.

**Independent Test**: dato un tipo documento e una categoria attivi, il gestore puo' renderli disponibili alla configurazione di un modello.

### Tests for User Story 1

- [ ] T014 [P] [US1] Add contract tests for protected `GET /api/v1/builder/tipi-documento` and `POST /api/v1/builder/tipi-documento` in `backend/tests/builder/contract/test_tipi_documento_api.py`
- [ ] T015 [P] [US1] Add contract tests for protected `GET /api/v1/builder/tipi-documento/{codice}/categorie` and `POST /api/v1/builder/tipi-documento/{codice}/categorie` in `backend/tests/builder/contract/test_categorie_documento_api.py`
- [ ] T016 [P] [US1] Add authorization tests for viewer versus manager on type/category routes in `backend/tests/builder/contract/test_builder_auth_api.py`
- [ ] T017 [P] [US1] Add integration tests for type/category creation, update and duplicate handling in `backend/tests/builder/integration/test_tipi_categorie.py`
- [ ] T018 [P] [US1] Add integration tests that inactive types/categories cannot be selected for new models in `backend/tests/builder/integration/test_tipi_categorie.py`

### Implementation for User Story 1

- [ ] T019 [US1] Implement type/category repository functions over shared catalog models in `backend/app/builder/repository/classificazione.py`
- [ ] T020 [US1] Implement `TipoDocumentoBuilderService` in `backend/app/builder/service/tipi_documento.py`
- [ ] T021 [US1] Implement `CategoriaDocumentoBuilderService` in `backend/app/builder/service/categorie_documento.py`
- [ ] T022 [US1] Implement type/category FastAPI routes in `backend/app/builder/api/classificazione.py`
- [ ] T023 [US1] Apply `require_modelli_viewer` to read routes and `require_modelli_gestore` to write routes in `backend/app/builder/api/classificazione.py`
- [ ] T024 [US1] Persist audit events for type/category create and update operations in `backend/app/builder/service/audit.py`
- [ ] T025 [US1] Register builder classification routes in `backend/app/builder/api/__init__.py`

**Checkpoint**: Tipi e categorie are independently usable through protected builder APIs.

---

## Phase 4: User Story 2 - Gestire modelli e versioni (Priority: P1)

**Goal**: Creare modelli, assegnare variante obbligatoria, creare versioni e impedire modifiche dirette a versioni pubblicate.

**Independent Test**: dato un modello in bozza, il gestore puo' creare una versione, modificarla e portarla a uno stato di revisione/pubblicazione.

### Tests for User Story 2

- [ ] T026 [P] [US2] Add contract tests for protected `GET /api/v1/builder/modelli` and `POST /api/v1/builder/modelli` in `backend/tests/builder/contract/test_modelli_api.py`
- [ ] T027 [P] [US2] Add contract tests for protected `POST /api/v1/builder/modelli/{modelloId}/versioni` in `backend/tests/builder/contract/test_versioni_api.py`
- [ ] T028 [P] [US2] Add contract tests for `PUT /api/v1/builder/modelli/{modelloId}/versioni/{versioneId}` immutability errors in `backend/tests/builder/contract/test_versioni_api.py`
- [ ] T029 [P] [US2] Add integration tests for default `STANDARD` variant in `backend/tests/builder/integration/test_varianti.py`
- [ ] T030 [P] [US2] Add integration tests for duplicate variant rejection in `backend/tests/builder/integration/test_varianti.py`
- [ ] T031 [P] [US2] Add unit tests for version mutability and derived draft rules in `backend/tests/builder/unit/test_mutabilita_versione.py`

### Implementation for User Story 2

- [ ] T032 [US2] Extend shared catalog models with builder-only version metadata in `backend/app/catalog/models.py`
- [ ] T033 [US2] Implement model repository functions in `backend/app/builder/repository/modelli.py`
- [ ] T034 [US2] Implement version repository functions in `backend/app/builder/repository/versioni.py`
- [ ] T035 [US2] Implement `ModelloDocumentoBuilderService` with variant default `STANDARD` in `backend/app/builder/service/modelli.py`
- [ ] T036 [US2] Implement `ModelloVersioneBuilderService` with draft creation and derived version rules in `backend/app/builder/service/versioni.py`
- [ ] T037 [US2] Implement immutability guard for `PUBBLICATO` versions in `backend/app/builder/validation/versioni.py`
- [ ] T038 [US2] Implement model and version FastAPI routes in `backend/app/builder/api/modelli.py`
- [ ] T039 [US2] Apply `require_modelli_viewer` to model/version reads and `require_modelli_gestore` to writes in `backend/app/builder/api/modelli.py`
- [ ] T040 [US2] Persist audit events for model creation and version modification in `backend/app/builder/service/audit.py`
- [ ] T041 [US2] Register model/version routes in `backend/app/builder/api/__init__.py`

**Checkpoint**: Models and draft/derived versions are independently manageable through protected builder APIs.

---

## Phase 5: User Story 3 - Pubblicare e archiviare versioni modello (Priority: P1)

**Goal**: Pubblicare versioni approvate, archiviare versioni pubblicate e garantire una sola versione pubblicata corrente per variante.

**Independent Test**: una versione non pubblicata non appare nel catalogo operativo; una versione pubblicata valida appare nel catalogo.

### Tests for User Story 3

- [ ] T042 [P] [US3] Add contract tests for `POST /api/v1/builder/modelli/{modelloId}/versioni/{versioneId}/approva` in `backend/tests/builder/contract/test_approvazione_api.py`
- [ ] T043 [P] [US3] Add contract tests for `POST /api/v1/builder/modelli/{modelloId}/versioni/{versioneId}/pubblica` in `backend/tests/builder/contract/test_pubblicazione_api.py`
- [ ] T044 [P] [US3] Add contract tests for archive and suspend routes in `backend/tests/builder/contract/test_archiviazione_api.py`
- [ ] T045 [P] [US3] Add authorization tests proving only `GEMODO_MODELLI_GESTORE` can approve, publish, archive or suspend in `backend/tests/builder/contract/test_builder_auth_api.py`
- [ ] T046 [P] [US3] Add integration tests for automatic archive of previous current version in `backend/tests/builder/integration/test_pubblicazione.py`
- [ ] T047 [P] [US3] Add integration tests for preventing two current published versions in same variant in `backend/tests/builder/integration/test_pubblicazione.py`
- [ ] T048 [P] [US3] Add integration tests for allowing separate published variants in same context in `backend/tests/builder/integration/test_pubblicazione.py`
- [ ] T049 [P] [US3] Add integration test that the `001` catalog sees only the current published version in `backend/tests/builder/integration/test_catalogo_compatibilita.py`

### Implementation for User Story 3

- [ ] T050 [US3] Implement approval transition in `backend/app/builder/service/workflow.py`
- [ ] T051 [US3] Implement transactional publication with automatic archive of previous current version in `backend/app/builder/service/pubblicazione.py`
- [ ] T052 [US3] Implement archive and suspend operations in `backend/app/builder/service/pubblicazione.py`
- [ ] T053 [US3] Implement publication repository locking or uniqueness strategy in `backend/app/builder/repository/pubblicazione.py`
- [ ] T054 [US3] Implement approve, publish, archive and suspend FastAPI routes in `backend/app/builder/api/pubblicazione.py`
- [ ] T055 [US3] Apply `require_modelli_gestore` to all state transition routes in `backend/app/builder/api/pubblicazione.py`
- [ ] T056 [US3] Persist audit events for approve, publish, archive and suspend transitions in `backend/app/builder/service/audit.py`
- [ ] T057 [US3] Ensure catalog service in `backend/app/catalog/service.py` filters only current `PUBBLICATO` versions after builder publication
- [ ] T058 [US3] Register publication routes in `backend/app/builder/api/__init__.py`

**Checkpoint**: Publication workflow is independently usable and catalog-safe.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Alignment, documentation and validation across the feature.

- [ ] T059 [P] Update success and error examples for the builder OpenAPI contract in `specs/002-builder-modelli/contracts/builder-modelli-api.openapi.yaml`
- [ ] T060 [P] Update seed/demo data for one standard variant and one custom variant in `infra/local/postgres/seed-demo-catalog.yaml`
- [ ] T061 [P] Add completed validation notes to `specs/002-builder-modelli/quickstart.md`
- [ ] T062 [P] Update generated Spec Kit documentation from `scripts/generate-spec-docs.py`
- [ ] T063 Run builder pytest tests and related catalog compatibility tests from `backend/`
- [ ] T064 Run cross-spec consistency check between specs `001` and `002` for variant/version/security rules and record status in `docs/project-map.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies.
- **Foundational (Phase 2)**: depends on setup and blocks all user stories.
- **US1 (Phase 3)**: depends on foundational phase.
- **US2 (Phase 4)**: depends on foundational phase; full validation uses type/category data from US1.
- **US3 (Phase 5)**: depends on US2 version model and services.
- **Polish (Phase 6)**: depends on selected user stories being complete.

### Cross-Spec Dependencies

- `001` supplies the shared catalog model, common errors and JWT validation helpers. If those files are not yet implemented, complete the corresponding `001` foundational tasks before executing the builder runtime tasks.
- `009` supplies decision gate, documentation and demo seed conventions.
- `006` remains the authority for future fine-grained security, but `SEC-006-002` is already confirmed for this feature.

### User Story Dependencies

- **US1**: first productive increment; creates administrative classification APIs.
- **US2**: can start after foundational phase, but final validation depends on US1 entities.
- **US3**: depends on US2 because publication operates on versions.

### Parallel Opportunities

- T004-T005 can run in parallel after T001-T003.
- T008-T009 and T012-T013 can run in parallel during foundation.
- US1 tests T014-T018 can run in parallel.
- US2 tests T026-T031 can run in parallel.
- US3 tests T042-T049 can run in parallel.
- Polish tasks T059-T062 can run in parallel.

## Parallel Example: User Story 2

```text
Task: "Add integration tests for default STANDARD variant"
Task: "Add integration tests for duplicate variant rejection"
Task: "Add unit tests for version mutability and derived draft rules"
Task: "Implement model repository functions"
Task: "Implement version repository functions"
```

## Implementation Strategy

### Primo Incremento Produttivo

1. Complete Phase 1 and Phase 2.
2. Complete US1 to manage document types and categories through protected builder APIs.
3. Validate US1 independently with contract, authorization and integration tests.
4. Add US2 for model/version drafting and immutability.
5. Add US3 for approval, publication and archive workflow.

### Safety Rules

- Do not implement direct reads from GEBAN DB.
- Do not duplicate catalog tables or maintain a separate builder copy of catalog data.
- Do not expose non-`PUBBLICATO` versions to the catalog operative path.
- Do not update published content in place.
- Do not publish a new version without archiving the previous current version of the same variant in the same transaction.
- Do not rely on frontend checks for authorization; protected builder APIs must enforce JWT roles in the backend.
