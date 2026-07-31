# Implementation Plan: Builder Modelli Documentali

**Branch**: `002-builder-modelli` | **Date**: 2026-07-31 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/002-builder-modelli/spec.md`

## Summary

Realizzare il dominio backend del builder modelli: gestione di tipi documento,
categorie, modelli, varianti obbligatorie, versioni, stati e pubblicazione. La feature
produce il catalogo di configurazione usato dalla 001, senza includere il frontend builder
e senza includere generazione PDF, storage o profili integrazione GEBAN dedicati.

La regola centrale e' che ogni modello appartiene a tipo/categoria/tipologia/variante,
con variante obbligatoria e default `STANDARD`; per la stessa variante puo' esistere al
massimo una versione `PUBBLICATO` corrente. Quando una nuova versione della stessa variante
viene pubblicata, la precedente passa automaticamente ad `ARCHIVIATO`.

Le API interne builder sono protette da JWT Keycloak lato backend. Le letture richiedono
`GEMODO_MODELLI_VIEWER` o `GEMODO_MODELLI_GESTORE`; creazione, modifica, approvazione,
pubblicazione, archiviazione e sospensione richiedono `GEMODO_MODELLI_GESTORE`. Nel primo
rilascio la pubblicazione del gestore vale anche come approvazione, in coerenza con
`SEC-006-002`.

## Technical Context

**Language/Version**: Python 3.12+

**Primary Dependencies**: FastAPI, Pydantic, SQLAlchemy 2, Alembic, PyYAML/OpenAPI tooling,
JWT/JWKS security helpers shared with `001`

**Storage**: PostgreSQL

**Testing**: pytest, httpx/FastAPI TestClient, repository/service integration tests,
contract tests against OpenAPI examples

**Target Platform**: backend web service deployed for internal service APIs

**Project Type**: backend web service / domain API

**Performance Goals**: builder APIs are administrative; normal requests should complete
within 500 ms p95 on seeded/demo data. Publication must remain transactional.

**Constraints**: no direct read/write of GEBAN DB; only published versions are visible to
GEBAN catalog; published content is immutable; audit hooks required for state changes;
builder APIs must enforce backend authorization, not rely on frontend enablement.

**Scale/Scope**: initial administrative dataset: tens of document types, hundreds of
models/variants, thousands of versions/fields over time.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| Boundary Ownership | PASS | Builder owns document model configuration; no GEBAN DB access. |
| Contract-First Integration | PASS | Internal builder contracts and 001 catalog compatibility are documented before implementation. |
| Configurable Document Models | PASS | Types, categories, models, variants, versions and fields are persisted/configured. |
| Versioning, Traceability, Reproducibility | PASS | Published versions are immutable; replacements create new versions and archive prior current version. |
| Security, Audit, Controlled AI | PASS | Feature enforces Keycloak JWT roles for builder APIs and records audit-relevant events. |
| Public Documentation and Reuse Readiness | PASS | Builder API OpenAPI and examples are versioned before runtime implementation. |

Post-design re-check: PASS. Generated data model and contracts preserve the same boundaries
and do not introduce direct GEBAN coupling.

## Project Structure

### Documentation (this feature)

```text
specs/002-builder-modelli/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── builder-modelli-api.openapi.yaml
└── tasks.md
```

### Source Code (repository root)

```text
backend/
├── app/builder/
│   ├── api/
│   ├── repository/
│   ├── service/
│   └── validation/
├── app/catalog/
│   ├── models.py
│   └── repository.py
├── app/common/
│   ├── errors.py
│   └── security.py
├── alembic/versions/
└── tests/builder/
    ├── contract/
    ├── integration/
    └── unit/
```

**Structure Decision**: questa feature implementa API amministrative e servizi builder in
`backend/app/builder/`, riusando modelli e repository condivisi del catalogo in
`backend/app/catalog/` definiti dalla `001`. Non deve introdurre un secondo set di tabelle
`tipo_documento`, `categoria_documento`, `modello_documento` o `modello_versione`.
Il frontend builder resta nella spec `007`; sezioni, placeholder e layout nella spec `003`.

## Phase 0: Research

Output: [research.md](./research.md)

Decisioni principali:

- variante modello distinta dalla versione modello;
- variante obbligatoria con default `STANDARD`;
- versione pubblicata immutabile;
- pubblicazione transazionale con archiviazione automatica della precedente versione
  corrente della stessa variante;
- stati workflow separati: `BOZZA`, `IN_REVISIONE`, `APPROVATO`, `PUBBLICATO`,
  `ARCHIVIATO`, `SOSPESO`.
- protezione backend Keycloak con ruoli builder `GEMODO_MODELLI_VIEWER` e
  `GEMODO_MODELLI_GESTORE`.

## Phase 1: Design & Contracts

Output:

- [data-model.md](./data-model.md)
- [contracts/builder-modelli-api.openapi.yaml](./contracts/builder-modelli-api.openapi.yaml)
- [quickstart.md](./quickstart.md)

The design deliberately exposes internal builder APIs separately from GEBAN catalog APIs.
The GEBAN-facing contract remains owned by spec 001. Both API surfaces use the same
published model/version data, so the builder implementation must update the shared catalog
domain rather than duplicate persistence.

## Dependencies

- `001-catalogo-contratto-geban`: shared catalog models, catalog filtering rules, common
  security/error helpers and GEBAN-facing OpenAPI.
- `009-fondamenta-mock-test-qualita`: documentation portal, decision gate, demo seed
  conventions and API documentation checks.
- `006-sicurezza-autorizzazioni-audit`: authoritative security model; for this feature the
  confirmed first-release rule is `GEMODO_MODELLI_GESTORE` can approve and publish.

## Complexity Tracking

No constitution violations requiring complexity exceptions.
