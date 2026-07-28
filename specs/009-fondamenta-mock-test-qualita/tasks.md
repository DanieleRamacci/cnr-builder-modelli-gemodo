# Tasks: Fondamenta Mock Test E Qualita

**Input**: Design documents from `specs/009-fondamenta-mock-test-qualita/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md),
[data-model.md](./data-model.md), [quality-readiness-contract.yaml](./contracts/quality-readiness-contract.yaml),
[mock-geban-scenarios.yaml](./contracts/mock-geban-scenarios.yaml), [quickstart.md](./quickstart.md)

**Tests**: Test tasks are included because the feature explicitly defines mock, quality and
end-to-end validation scenarios.

**Organization**: Tasks are grouped by user story to enable independent implementation and
testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel with other tasks in the same phase if dependencies are met.
- **[Story]**: User story label from `spec.md`.
- Every task includes an exact target file path.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the repository structure and baseline configuration required by the
foundation feature.

- [ ] T001 Create backend, frontend, infra and mock directory skeletons in `backend/`, `frontend/`, `infra/local/`, `infra/openapi/`, `mock-geban/`
- [ ] T002 Create backend project manifest with FastAPI, Pydantic, SQLAlchemy, Alembic and pytest dependencies in `backend/pyproject.toml`
- [ ] T003 Create backend application entrypoint and package markers in `backend/app/main.py`, `backend/app/__init__.py`, `backend/app/core/__init__.py`, `backend/app/db/__init__.py`, `backend/app/quality/__init__.py`
- [ ] T004 Create backend test package structure in `backend/tests/contract/__init__.py`, `backend/tests/integration/__init__.py`, `backend/tests/e2e/__init__.py`, `backend/tests/support/__init__.py`
- [ ] T005 [P] Create frontend project manifest placeholder aligned to Angular planning in `frontend/package.json`
- [ ] T006 [P] Create frontend source placeholders for builder and generazioni features in `frontend/src/app/.gitkeep`, `frontend/src/features/builder/.gitkeep`, `frontend/src/features/generazioni/.gitkeep`, `frontend/src/shared/.gitkeep`
- [ ] T007 [P] Create local infrastructure placeholder files and service healthcheck notes in `infra/local/compose.yaml`, `infra/local/frontend/README.md`, `infra/local/keycloak/README.md`, `infra/local/postgres/README.md`, `infra/local/documentale-mock/README.md`
- [ ] T008 [P] Create mock GEBAN baseline documentation and folders in `mock-geban/README.md`, `mock-geban/scenarios/.gitkeep`, `mock-geban/payloads/.gitkeep`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Define shared quality contracts, configuration loaders and validation helpers
that block all user stories.

**CRITICAL**: No user story work should begin until this phase is complete.

- [ ] T009 Create quality manifest schema models for AmbienteLocale, ServizioLocale, SeedDemo, ScenarioEndToEnd, MatriceCopertura, DecisioneAperta and VerificaAmbiente in `backend/app/quality/schemas.py`
- [ ] T010 Create YAML manifest loading utility with validation errors in `backend/app/quality/manifest_loader.py`
- [ ] T011 Create shared quality error types for prerequisito mancante, contratto non valido, seed sensibile and decisione bloccante in `backend/app/quality/errors.py`
- [ ] T012 Create local quality manifest seed from `quality-readiness-contract.yaml` in `infra/local/quality-readiness.local.yaml`
- [ ] T013 Create mock scenario manifest seed from `mock-geban-scenarios.yaml` in `mock-geban/scenarios/minimum-e2e.yaml`
- [ ] T014 [P] Create pytest configuration for backend contract, integration and e2e markers in `backend/pytest.ini`
- [ ] T015 [P] Create backend test fixtures for loading quality manifests and mock scenarios in `backend/tests/support/quality_fixtures.py`
- [ ] T016 [P] Create OpenAPI aggregation placeholder for future GEBAN-facing contracts in `infra/openapi/README.md`
- [ ] T017 Document the blocking rule for open decisions before implementation in `docs/project-map.md`

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel.

---

## Phase 3: User Story 1 - Preparare fondamenta tecniche (Priority: P1) MVP

**Goal**: A new developer can start from documented setup, verify required local services,
apply migrations and load demo data.

**Independent Test**: Run the environment verification against the local manifest and
receive PASS when required services are available, or prerequisito-mancante errors when
they are not.

### Tests for User Story 1

- [ ] T018 [P] [US1] Create contract test for quality readiness manifest required sections in `backend/tests/contract/test_quality_readiness_contract.py`
- [ ] T019 [P] [US1] Create integration test for local environment verification PASS/PARTIAL/FAIL outcomes, including frontend healthcheck, in `backend/tests/integration/test_environment_verification.py`
- [ ] T020 [P] [US1] Create integration test that rejects seed demo entries with real or sensitive data in `backend/tests/integration/test_seed_demo_validation.py`

### Implementation for User Story 1

- [ ] T021 [P] [US1] Implement AmbienteLocale and ServizioLocale validation logic in `backend/app/quality/environment.py`
- [ ] T022 [P] [US1] Implement SeedDemo validation logic with mandatory demo marker and sensitive-data guard in `backend/app/quality/seed_demo.py`
- [ ] T023 [US1] Implement VerificaAmbiente service that evaluates backend, frontend, database, identity, storage and mock service healthchecks in `backend/app/quality/environment_verifier.py`
- [ ] T024 [US1] Implement CLI entrypoint for local environment verification in `backend/app/quality/cli.py`
- [ ] T025 [US1] Create initial schema baseline migration and migration ownership documentation in `backend/alembic/versions/0001_initial_schema.py`, `backend/alembic/README.md`
- [ ] T026 [US1] Create demo seed catalog manifest for highlighted GEBAN/SOL typologies TDPNRR, CD, DIR, TD, CP, RS, CATP, TI, SDIP and MOB, including SOL codes and demo categories, in `infra/local/postgres/seed-demo-catalog.yaml`
- [ ] T027 [US1] Create Keycloak local realm planning manifest with configurable GEMODO user roles, GEBAN technical client placeholder and mock principal notes in `infra/local/keycloak/realm-gemodo.local.json`
- [ ] T028 [US1] Create documentale mock readiness manifest in `infra/local/documentale-mock/readiness.yaml`
- [ ] T029 [US1] Update setup validation steps for services, migrations and seed demo in `specs/009-fondamenta-mock-test-qualita/quickstart.md`

**Checkpoint**: User Story 1 can be validated independently with environment readiness,
migrations/seed checks and no dependency on GEBAN reale.

---

## Phase 4: User Story 2 - Usare mock GEBAN e scenari end-to-end (Priority: P1)

**Goal**: The mock GEBAN can exercise public contracts for catalog, schema, validation,
generation, status and download scenarios without using internal GEMODO shortcuts.

**Independent Test**: Run mock scenario validation and confirm the six minimum scenarios
are mapped to contracts and expected outcomes.

### Tests for User Story 2

- [ ] T030 [P] [US2] Create contract test validating `mock-geban/scenarios/minimum-e2e.yaml` against `specs/009-fondamenta-mock-test-qualita/contracts/mock-geban-scenarios.yaml` in `backend/tests/contract/test_mock_geban_scenarios_contract.py`
- [ ] T031 [P] [US2] Create integration test for mock GEBAN valid flow catalog-to-status in `backend/tests/e2e/test_mock_geban_valid_flow.py`
- [ ] T032 [P] [US2] Create integration test for payload invalid, idempotent retry, idempotent conflict, failed generation and unauthorized access scenarios in `backend/tests/e2e/test_mock_geban_error_flows.py`

### Implementation for User Story 2

- [ ] T033 [P] [US2] Implement ScenarioEndToEnd schema parsing and validation in `backend/app/quality/scenario.py`
- [ ] T034 [P] [US2] Create mock GEBAN payload for valid BANDO_CONCORSO generation with common fields, selected model version and optional `Bando Inglese` data in `mock-geban/payloads/bando-concorso-valid.json`
- [ ] T035 [P] [US2] Create mock GEBAN payload for invalid BANDO_CONCORSO validation covering missing required fields, invalid SOL typology and missing English fields when `Bando Inglese` is true in `mock-geban/payloads/bando-concorso-invalid.json`
- [ ] T036 [US2] Implement mock GEBAN scenario runner skeleton using public contract names in `mock-geban/scenario_runner.py`
- [ ] T037 [US2] Implement guard that rejects mock scenarios using internal API or database shortcuts in `backend/app/quality/mock_contract_guard.py`
- [ ] T038 [US2] Create expected outcomes manifest for E2E-001 through E2E-006, including two outputs for English-enabled generation, in `mock-geban/scenarios/expected-outcomes.yaml`
- [ ] T039 [US2] Create audit expectations manifest for generation, download, conflict and authorization denial in `infra/local/audit-expectations.yaml`
- [ ] T040 [US2] Add mock GEBAN usage and scenario execution notes in `mock-geban/README.md`
- [ ] T041 [US2] Update quickstart scenarios for valid flow, error flow, idempotency and unauthorized access in `specs/009-fondamenta-mock-test-qualita/quickstart.md`

**Checkpoint**: User Story 2 can be validated independently through mock GEBAN scenario
manifests and e2e tests against public contracts.

---

## Phase 5: User Story 3 - Governare decisioni aperte (Priority: P2)

**Goal**: Open decisions are tracked with owner, impact, provisional assumption and
blocking phase so they cannot become silent implementation assumptions.

**Independent Test**: Validate the decision register and coverage matrix; every critical
decision has owner, impacted specs, status and blocking phase.

### Tests for User Story 3

- [ ] T042 [P] [US3] Create contract test for decision register required fields and statuses in `backend/tests/contract/test_open_decisions_contract.py`
- [ ] T043 [P] [US3] Create integration test for blocking critical decisions before implementation readiness in `backend/tests/integration/test_open_decision_gates.py`
- [ ] T044 [P] [US3] Create integration test for coverage matrix mapping scenarios to requirements and contracts in `backend/tests/integration/test_coverage_matrix.py`

### Implementation for User Story 3

- [ ] T045 [P] [US3] Implement DecisioneAperta schema and state transition validation in `backend/app/quality/decision.py`
- [ ] T046 [P] [US3] Implement MatriceCopertura schema and coverage status validation in `backend/app/quality/coverage.py`
- [ ] T047 [US3] Create initial open decisions register for proposal section 17 in `docs/decision-register.yaml`
- [ ] T048 [US3] Create coverage matrix linking E2E scenarios, requirements including FR-027 through FR-030, and spec owners in `docs/quality-coverage-matrix.yaml`
- [ ] T049 [US3] Implement readiness gate that fails on silent critical assumptions in `backend/app/quality/readiness_gate.py`
- [ ] T050 [US3] Document decision update workflow and propagation to spec owners in `docs/decision-workflow.md`

**Checkpoint**: User Story 3 can be validated independently by checking decision register,
coverage matrix and readiness gate outcomes.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final verification and documentation updates across the foundation feature.

- [ ] T051 [P] Update project map status for `009-fondamenta-mock-test-qualita` after selected implementation scope is completed in `docs/project-map.md`
- [ ] T052 [P] Add generated documentation notes for quality manifests and mock GEBAN in `README.md`
- [ ] T053 [P] Add concrete success and functional error examples for mock-facing contracts in `infra/openapi/examples/catalog-success.json`, `infra/openapi/examples/validation-error.json`, `infra/openapi/README.md`
- [ ] T054 Run Python syntax and YAML validation for `backend/app/quality/`, `infra/local/`, `mock-geban/` and `docs/*.yaml`
- [ ] T055 Run MkDocs generation and strict build with `scripts/generate-spec-docs.py` and `mkdocs build --strict`
- [ ] T056 Review `specs/009-fondamenta-mock-test-qualita/quickstart.md` against implemented task outputs and update expected outcomes

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies.
- **Foundational (Phase 2)**: depends on Phase 1 completion and blocks all user stories.
- **User Story 1 (Phase 3)**: depends on Phase 2; delivers MVP foundation readiness.
- **User Story 2 (Phase 4)**: depends on Phase 2; can run after or alongside US1 if shared manifests are stable.
- **User Story 3 (Phase 5)**: depends on Phase 2; can run alongside US1/US2 but should be complete before implementation readiness is claimed.
- **Polish (Phase 6)**: depends on selected user stories being complete.

### User Story Dependencies

- **US1 - Preparare fondamenta tecniche**: MVP; no dependency on US2 or US3 after foundation.
- **US2 - Usare mock GEBAN e scenari end-to-end**: depends on foundational manifests; benefits from US1 seed and environment files but remains independently testable through scenario manifests.
- **US3 - Governare decisioni aperte**: depends on foundational schemas; independent from runtime mock execution.

### Within Each User Story

- Tests are written before implementation tasks.
- Schema/model tasks precede services and runners.
- Manifest and documentation tasks follow the corresponding validation logic.
- Each story reaches a checkpoint before moving to polish.

## Parallel Opportunities

- Setup tasks T005-T008 can run in parallel after T001.
- Foundational tasks T014-T016 can run in parallel after T009-T013 are scoped.
- US1 tests T018-T020 can run in parallel.
- US1 validation components T021 and T022 can run in parallel.
- US2 tests T030-T032 can run in parallel.
- US2 payload tasks T034 and T035 can run in parallel with T033.
- US3 tests T042-T044 can run in parallel.
- US3 schema tasks T045 and T046 can run in parallel.
- Polish documentation tasks T051-T053 can run in parallel.

## Parallel Example: User Story 1

```bash
Task: "Create contract test for quality readiness manifest required sections in backend/tests/contract/test_quality_readiness_contract.py"
Task: "Create integration test for local environment verification PASS/PARTIAL/FAIL outcomes in backend/tests/integration/test_environment_verification.py"
Task: "Create integration test that rejects seed demo entries with real or sensitive data in backend/tests/integration/test_seed_demo_validation.py"
```

## Parallel Example: User Story 2

```bash
Task: "Create mock GEBAN payload for valid BANDO_CONCORSO generation in mock-geban/payloads/bando-concorso-valid.json"
Task: "Create mock GEBAN payload for invalid BANDO_CONCORSO validation in mock-geban/payloads/bando-concorso-invalid.json"
Task: "Create audit expectations manifest for generation, download, conflict and authorization denial in infra/local/audit-expectations.yaml"
```

## Parallel Example: User Story 3

```bash
Task: "Implement DecisioneAperta schema and state transition validation in backend/app/quality/decision.py"
Task: "Implement MatriceCopertura schema and coverage status validation in backend/app/quality/coverage.py"
Task: "Create initial open decisions register for proposal section 17 in docs/decision-register.yaml"
```

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 setup.
2. Complete Phase 2 foundational schemas, manifests and fixtures.
3. Complete Phase 3 User Story 1.
4. Stop and validate environment readiness, migrations/seed demo and prerequisiti.

### Incremental Delivery

1. Add US1 for repeatable local foundation.
2. Add US2 for mock GEBAN and e2e scenario readiness.
3. Add US3 for decision governance and implementation gates.
4. Run Polish tasks and regenerate documentation.

### Parallel Team Strategy

After Phase 2:

- Developer A: US1 environment and seed readiness.
- Developer B: US2 mock GEBAN scenarios.
- Developer C: US3 decision register and coverage matrix.

## Notes

- `[P]` tasks touch separate files or can be split safely after prerequisites.
- `[US1]`, `[US2]`, `[US3]` map to the user stories in `spec.md`.
- `tasks.md` is generated only for planning; no task is implemented until explicitly started.
- Open decisions from spec 006 remain provisional and must be revisited before implementing impacted runtime security behavior.
