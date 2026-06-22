# Implementation Plan: Sezioni Placeholder E Versionamento

**Branch**: `main` | **Date**: 2026-06-19 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/003-sezioni-placeholder-versionamento/spec.md`

## Summary

Realizzare il dominio backend per le sezioni proprie della versione modello, il contenuto
strutturato controllato, la gestione dei placeholder e gli schemi dei campi complessi.
La feature estende il builder della 002 e alimenta il contratto dati della 001, senza
introdurre versionamento autonomo delle sezioni, sezioni condizionali o rendering PDF.

Le sezioni appartengono direttamente a una `modello_versione_id`: sono modificabili solo
quando la versione modello e' in stato modificabile, vengono copiate quando nasce una
nuova versione modello e restano immutabili quando la versione modello e' pubblicata.

## Technical Context

**Language/Version**: Python 3.12+

**Primary Dependencies**: FastAPI, Pydantic, SQLAlchemy 2, Alembic, OpenAPI tooling

**Storage**: PostgreSQL

**Testing**: pytest, httpx/FastAPI TestClient, repository/service integration tests,
contract tests against OpenAPI examples

**Target Platform**: backend web service / internal builder APIs

**Project Type**: backend domain API

**Performance Goals**: administrative builder requests under 500 ms p95 on seeded/demo data;
publication validation deterministic and bounded by number of sections/placeholders in one
model version.

**Constraints**: no direct read/write of GEBAN DB; no HTML libero in section content; no
autonomous section versioning in current scope; no conditional sections in current scope;
published model versions remain immutable.

**Scale/Scope**: initial administrative dataset: hundreds of model versions, tens of
sections per model version, hundreds of placeholders/complex-field definitions across
models.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| Boundary Ownership | PASS | Sections and placeholders belong to service model configuration; no GEBAN DB access. |
| Contract-First Integration | PASS | Placeholder and complex-field schema rules preserve the 001 contract data flow. |
| Configurable Document Models | PASS | Sections, placeholders and field schemas are persisted/configured, not hard-coded. |
| Versioning, Traceability, Reproducibility | PASS | Section history is guaranteed by immutable published model versions. |
| Security, Audit, Controlled AI | PASS | State-changing builder actions remain audit-relevant; detailed roles stay in spec 006. |

Post-design re-check: PASS. Data model and contracts preserve model-version ownership and
do not introduce live shared sections that could mutate published documents.

## Project Structure

### Documentation (this feature)

```text
specs/003-sezioni-placeholder-versionamento/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── sezioni-placeholder-api.openapi.yaml
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

**Structure Decision**: questa feature estende il modulo backend `modelli` gia' previsto
dalla 002. Il frontend editor resta nella spec 007; il rendering/PDF resta nella spec 004.

## Phase 0: Research

Output: [research.md](./research.md)

Decisioni principali:

- contenuto sezione strutturato e controllato, senza HTML libero;
- sezioni proprie della versione modello, senza versionamento autonomo;
- eventuale libreria sezioni solo come template copiabile;
- niente sezioni condizionali nel perimetro corrente;
- placeholder disponibili derivati dai campi associati alla versione modello;
- pubblicazione bloccata se il contenuto usa placeholder non disponibili o manca un
  placeholder obbligatorio;
- campi complessi descritti con schema esplicito dei sotto-campi.

## Phase 1: Design & Contracts

Output:

- [data-model.md](./data-model.md)
- [contracts/sezioni-placeholder-api.openapi.yaml](./contracts/sezioni-placeholder-api.openapi.yaml)
- [quickstart.md](./quickstart.md)

The design exposes internal builder APIs for section composition and validation. GEBAN-facing
contract APIs remain owned by spec 001.

## Complexity Tracking

No constitution violations requiring complexity exceptions.
