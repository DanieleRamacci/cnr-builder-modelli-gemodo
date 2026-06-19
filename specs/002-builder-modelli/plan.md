# Implementation Plan: Builder Modelli Documentali

**Branch**: `main` | **Date**: 2026-06-19 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/002-builder-modelli/spec.md`

## Summary

Realizzare il dominio backend del builder modelli: gestione di tipi documento,
categorie, modelli, varianti obbligatorie, versioni, stati e pubblicazione. La feature
produce il catalogo di configurazione usato dalla 001, senza includere il frontend builder
e senza implementare generazione PDF o sicurezza dettagliata.

La regola centrale e' che ogni modello appartiene a tipo/categoria/tipologia/variante,
con variante obbligatoria e default `STANDARD`; per la stessa variante puo' esistere al
massimo una versione `PUBBLICATO` corrente. Quando una nuova versione della stessa variante
viene pubblicata, la precedente passa automaticamente ad `ARCHIVIATO`.

## Technical Context

**Language/Version**: Python 3.12+

**Primary Dependencies**: FastAPI, Pydantic, SQLAlchemy 2, Alembic, OpenAPI tooling

**Storage**: PostgreSQL

**Testing**: pytest, httpx/FastAPI TestClient, repository/service integration tests,
contract tests against OpenAPI examples

**Target Platform**: backend web service deployed for internal service APIs

**Project Type**: backend web service / domain API

**Performance Goals**: builder APIs are administrative; normal requests should complete
within 500 ms p95 on seeded/demo data. Publication must remain transactional.

**Constraints**: no direct read/write of GEBAN DB; only published versions are visible to
GEBAN catalog; published content is immutable; audit hooks required for state changes;
security details are delegated to spec 006 but backend must expose authorization points.

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
| Security, Audit, Controlled AI | PASS | Feature records audit-relevant events; detailed roles are delegated to spec 006. |

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
├── app/modelli/
│   ├── api/
│   ├── domain/
│   ├── repository/
│   ├── service/
│   └── validation/
├── alembic/versions/
└── tests/modelli/
    ├── contract/
    ├── integration/
    └── unit/
```

**Structure Decision**: questa feature implementa solo backend/domain API. Il frontend
builder resta nella spec 007; la sicurezza dettagliata nella spec 006; sezioni e
placeholder nella spec 003.

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

## Phase 1: Design & Contracts

Output:

- [data-model.md](./data-model.md)
- [contracts/builder-modelli-api.openapi.yaml](./contracts/builder-modelli-api.openapi.yaml)
- [quickstart.md](./quickstart.md)

The design deliberately exposes internal builder APIs separately from GEBAN catalog APIs.
The GEBAN-facing contract remains owned by spec 001.

## Complexity Tracking

No constitution violations requiring complexity exceptions.
