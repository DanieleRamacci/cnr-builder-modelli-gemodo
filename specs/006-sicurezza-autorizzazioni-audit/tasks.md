# Tasks: Sicurezza Autorizzazioni E Audit

**Input**: Design documents from `specs/006-sicurezza-autorizzazioni-audit/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md),
[data-model.md](./data-model.md), [contracts/authorization-mapping.schema.yaml](./contracts/authorization-mapping.schema.yaml),
[quickstart.md](./quickstart.md)

**Tests**: Test tasks are included because the feature protects security-sensitive JWT
authorization, mapping and integration-profile behavior.

**Organization**: Tasks are grouped by user story to enable independent implementation and
testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel with other tasks in the same phase if dependencies are met.
- **[Story]**: User story label from `spec.md`.
- Every task includes an exact target file path.

## Phase 1: Setup

**Purpose**: Confirm feature artifacts and shared policy before application changes.

- [x] T001 Verify active feature and checklist state in `.specify/feature.json` and `specs/006-sicurezza-autorizzazioni-audit/checklists/requirements.md`
- [x] T002 [P] Verify tool policy state from `.specify/config/tools.yml` and record blocking/non-blocking constraints before implementation
- [x] T003 [P] Confirm implementation files and tests impacted by JWT/config mapping in `backend/app/common/security.py`, `backend/app/quality/schemas.py`, `backend/app/quality/integration_profile.py`, `backend/tests/common/test_security_jwt.py`, and `backend/tests/integration`

---

## Phase 2: Foundational

**Purpose**: Extend configuration shape before user stories depend on it.

- [x] T004 Add typed schema for `token_contexts` and external `role_mappings` in `backend/app/quality/schemas.py`
- [x] T005 Add GEBAN ACE client/context/role mapping to `infra/local/integration-profiles.local.yaml`
- [x] T006 [P] Add support fixtures for ACE client/context mappings in `backend/tests/support/integration_profiles.py`
- [x] T007 [P] Add JWT test helper support for arbitrary `aud`, `resource_access` roles and `contexts.<app>.roles` in `backend/tests/support/security.py`
- [x] T008 Add integration-profile validation coverage for ACE context and role mappings in `backend/tests/integration/test_integration_profiles.py`

**Checkpoint**: YAML configuration can represent ACE clients and role mappings.

---

## Phase 3: User Story 1 - Proteggere Le API Con Identita' Verificabile (Priority: P1)

**Goal**: Reject invalid or misdirected tokens before authorization logic runs.

**Independent Test**: Token without valid `aud=gemodo-backend`, valid issuer/signature or
configured client is rejected.

### Tests for User Story 1

- [x] T009 [P] [US1] Add JWT tests for ACE token accepted only with configured client and `aud=gemodo-backend` in `backend/tests/common/test_security_jwt.py`
- [x] T010 [P] [US1] Add JWT tests for ACE token rejection when audience is missing/wrong or client is not configured in `backend/tests/common/test_security_jwt.py`

### Implementation for User Story 1

- [x] T011 [US1] Extend security principal extraction to support configured ACE clients without weakening audience validation in `backend/app/common/security.py`

**Checkpoint**: Identity validation works for both `geban-backend` test client and ACE real clients.

---

## Phase 4: User Story 2 - Autorizzare Azioni Per Ruolo E Contesto (Priority: P1)

**Goal**: Normalize direct GEMODO roles and ACE/GEBAN context roles into GEMODO permissions.

**Independent Test**: `ROLE_MANAGER#geban` can derive builder management; `ROLE_USER#geban`,
`ROLE_COORDINATOR#geban` and `ROLE_GESTORE#geban` can generate documents but cannot manage
models.

### Tests for User Story 2

- [x] T012 [P] [US2] Add JWT tests mapping `contexts.geban.roles` generation roles to `DOCUMENTI_GENERATORE` in `backend/tests/common/test_security_jwt.py`
- [x] T013 [P] [US2] Add JWT tests that only `ROLE_MANAGER#geban` derives `GEMODO_MODELLI_GESTORE` in `backend/tests/common/test_security_jwt.py`
- [x] T014 [P] [US2] Add integration tests that unknown external roles do not derive permissions in `backend/tests/integration/test_integration_profiles.py`

### Implementation for User Story 2

- [x] T015 [US2] Implement configurable external-role normalization from `contexts.<app>.roles` to GEMODO permissions in `backend/app/common/security.py`
- [x] T016 [US2] Add builder role constants/guards needed by the mapping in `backend/app/common/security.py`

**Checkpoint**: Endpoint guards keep using GEMODO permissions, while ACE role names stay in configuration.

---

## Phase 5: User Story 3 - Auditare Operazioni Rilevanti (Priority: P1)

**Goal**: Preserve audit-safe identity context and avoid exposing tokens/secrets.

**Independent Test**: Authorization failures retain sanitized reason/context and never expose
the raw token.

### Tests for User Story 3

- [x] T017 [P] [US3] Add regression tests ensuring authorization errors for ACE tokens do not expose JWT material in `backend/tests/common/test_security_jwt.py`

### Implementation for User Story 3

- [x] T018 [US3] Preserve sanitized client/context metadata on `PrincipalGEMODO` for later audit use in `backend/app/common/security.py`

**Checkpoint**: Principal contains enough non-secret context for future audit events.

---

## Phase 6: Polish & Cross-Cutting

- [x] T019 [P] Update operational Keycloak/configuration documentation in `specs/006-sicurezza-autorizzazioni-audit/keycloak-jwt.md`
- [x] T020 [P] Update quickstart expected config/tests in `specs/006-sicurezza-autorizzazioni-audit/quickstart.md`
- [x] T021 Run targeted test suite from `backend/` with `uv run pytest tests/common/test_security_jwt.py tests/integration/test_integration_profiles.py`
- [x] T022 Run broader non-e2e validation from `backend/` with `uv run pytest -m "not e2e"`
- [x] T023 Review task completion against `specs/006-sicurezza-autorizzazioni-audit/spec.md` and mark all completed tasks `[x]` in `specs/006-sicurezza-autorizzazioni-audit/tasks.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies.
- **Foundational (Phase 2)**: depends on Setup and blocks user stories.
- **User Stories (Phase 3-5)**: depend on Foundational; US1 should complete before US2
  because mapping relies on principal/token validation.
- **Polish (Phase 6)**: depends on selected user stories.

### User Story Dependencies

- **US1**: first security increment; required before accepting ACE role claims.
- **US2**: depends on US1 validation and config schema.
- **US3**: can be implemented after principal model exists from US1/US2.

### Parallel Opportunities

- T002 and T003 can run in parallel.
- T006 and T007 can run in parallel after T004/T005 shape is known.
- T009 and T010 can run together.
- T012, T013 and T014 can run together after foundational tasks.
- T019 and T020 can run together after implementation stabilizes.

## Parallel Example: User Story 2

```bash
Task: "Add JWT tests mapping contexts.geban.roles generation roles to DOCUMENTI_GENERATORE in backend/tests/common/test_security_jwt.py"
Task: "Add JWT tests that only ROLE_MANAGER#geban derives GEMODO_MODELLI_GESTORE in backend/tests/common/test_security_jwt.py"
Task: "Add integration tests that unknown external roles do not derive permissions in backend/tests/integration/test_integration_profiles.py"
```

## Implementation Strategy

### MVP First

Complete US1 and US2: accept valid ACE/GEBAN tokens with `aud=gemodo-backend`, configured
client, and mapped `contexts.geban.roles`; keep existing `geban-backend` direct role tests
green.

### Incremental Delivery

1. Extend config schema and YAML.
2. Add failing tests for ACE tokens and mapping.
3. Implement principal normalization and guards.
4. Run targeted tests.
5. Update docs and run broader validation.
