# Implementation Plan: Sezioni Placeholder E Versionamento

**Branch**: `003-sezioni-placeholder-versionamento` | **Date**: 2026-07-31 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/003-sezioni-placeholder-versionamento/spec.md`

## Summary

Realizzare il dominio backend per le sezioni proprie della versione modello, il modello
documentale controllato `GEMODO_DOCUMENT_V1`, la gestione dei placeholder e gli schemi dei
campi complessi.
La feature estende il builder della 002 e alimenta il contratto dati della 001, senza
introdurre versionamento autonomo delle sezioni, sezioni condizionali o rendering PDF.

Le sezioni appartengono direttamente a una `modello_versione_id`: sono modificabili solo
quando la versione modello e' in stato modificabile, vengono copiate quando nasce una
nuova versione modello e restano immutabili quando la versione modello e' pubblicata.
Il builder non salva HTML/CSS/script libero: salva blocchi ammessi, posizionamenti
controllati, asset versionati, stili consentiti e placeholder validati.

## Technical Context

**Language/Version**: Python 3.12+

**Primary Dependencies**: FastAPI, Pydantic, SQLAlchemy 2, Alembic, PyYAML/OpenAPI tooling,
JWT/JWKS security helpers shared with `001`/`002`, controlled document model validators
from `009`

**Storage**: PostgreSQL

**Testing**: pytest, httpx/FastAPI TestClient, repository/service integration tests,
contract tests against OpenAPI examples

**Target Platform**: backend web service / internal builder APIs

**Project Type**: backend domain API

**Performance Goals**: administrative builder requests under 500 ms p95 on seeded/demo data;
publication validation deterministic and bounded by number of sections/placeholders in one
model version.

**Constraints**: no direct read/write of GEBAN DB; no HTML/CSS/script libero in section
content; no autonomous section versioning in current scope; no conditional sections in
current scope; published model versions remain immutable; protected APIs enforce backend
authorization.

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
| Security, Audit, Controlled AI | PASS | State-changing builder actions require Keycloak builder roles and remain audit-relevant. |
| Public Documentation and Reuse Readiness | PASS | Section/placeholder API OpenAPI and controlled document examples are versioned. |

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
├── app/builder/
│   ├── sections/
│   ├── placeholders/
│   ├── complex_fields/
│   └── document_model/
├── app/catalog/
│   ├── models.py
│   └── service.py
├── app/common/
│   ├── errors.py
│   └── security.py
├── alembic/versions/
└── tests/builder/
    ├── contract/
    ├── integration/
    └── unit/
```

**Structure Decision**: questa feature estende il modulo backend `builder` previsto dalla
`002`, riusando modello versione, campi richiesti, sicurezza ed errori comuni. Il frontend
editor resta nella spec `007`; il rendering/PDF resta nella spec `004`.

## Phase 0: Research

Output: [research.md](./research.md)

Decisioni principali:

- modello documentale controllato `GEMODO_DOCUMENT_V1`, senza HTML/CSS/script libero;
- blocchi ammessi: `LOGO`, `INTESTAZIONE`, `TITOLO`, `PARAGRAFO`, `TABELLA`, `COLONNE`,
  `FIRMA`, `FOOTER`, `INTERRUZIONE_PAGINA`;
- asset versionati e stili consentiti;
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

The controlled document model produced here is the input for the PDF renderer in `004`; any
HTML or CSS needed by a renderer is an internal conversion artifact, never user-authored
builder content.

## Dependencies

- `001-catalogo-contratto-geban`: field contract, placeholder availability and complex
  field schema compatibility.
- `002-builder-modelli`: model version lifecycle, mutability checks, publication workflow
  and builder authorization roles.
- `009-fondamenta-mock-test-qualita`: prototype validator and demo format in
  `infra/local/document-models/`.

## Complexity Tracking

No constitution violations requiring complexity exceptions.
