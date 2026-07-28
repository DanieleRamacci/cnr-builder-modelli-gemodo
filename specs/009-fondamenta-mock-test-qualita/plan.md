# Implementation Plan: Fondamenta Mock Test E Qualita

**Branch**: `main` | **Date**: 2026-06-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/009-fondamenta-mock-test-qualita/spec.md`

## Summary

Definire le fondamenta verificabili del progetto GEMODO: ambiente locale ripetibile,
migrations e seed demo coerenti con le spec, mock GEBAN contract-first, scenari
end-to-end minimi, matrice di copertura e registro delle decisioni aperte.

L'approccio tecnico e' trattare questa feature come layer trasversale: prepara struttura,
contratti di qualita' e criteri di validazione che i task successivi useranno per
implementare backend, frontend, mock, dati demo, audit e test senza introdurre assunzioni
implicite.

## Technical Context

**Language/Version**: Python 3.12+ per backend, TypeScript moderno per frontend, YAML/JSON
per contratti e manifest di qualita'

**Primary Dependencies**: FastAPI, Pydantic, SQLAlchemy 2, Alembic, Angular, OpenAPI
tooling, Keycloak locale, strumenti di orchestrazione ambiente locale

**Storage**: PostgreSQL per dati applicativi; documentale locale/mock nascosto dietro
riferimento documentale stabile; file YAML/JSON versionati per manifest qualita'

**Testing**: pytest, httpx/FastAPI TestClient, Testcontainers PostgreSQL dove utile,
test e2e guidati da mock GEBAN, controlli di coerenza su OpenAPI/esempi/manifest

**Target Platform**: ambiente locale e runtime Linux/container per sviluppo e validazione

**Project Type**: applicazione web-service con frontend amministrativo, backend API,
mock di integrazione e suite di qualita' trasversale

**Performance Goals**: setup locale e scenari minimi devono essere ripetibili e adatti a
feedback di sviluppo; le verifiche e2e devono privilegiare copertura contrattuale rispetto
al carico

**Constraints**: nessuna dipendenza dal DB GEBAN; nessun dato reale nei seed demo; mock
GEBAN allineato ai contratti pubblici; decisioni aperte critiche non possono entrare in
tasks implementativi come assunzioni silenziose; sicurezza e audit seguono la spec 006

**Scale/Scope**: primo incremento trasversale per struttura di progetto, ambiente locale,
mock GEBAN, seed demo, contratti di qualita', scenari minimi e registro decisioni; fuori
scope implementare tutte le feature applicative finali

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Result |
|---|---|---|
| Boundary Ownership | Il piano prevede mock GEBAN e contratti, non accesso diretto al DB GEBAN. | PASS |
| Contract-First Integration | I contratti di qualita' e mock richiedono OpenAPI/esempi prima dei task implementativi. | PASS |
| Configurable Document Models | Seed e migrations devono riflettere modelli configurabili, non logica hard-coded. | PASS |
| Versioning, Traceability, Reproducibility | Seed, scenari e matrice copertura tracciano versioni modello, generazioni, audit e idempotenza. | PASS |
| Security, Audit, Controlled AI | Il piano include Keycloak locale, scenari autorizzativi, audit e decisioni AI/MCP non bloccanti. | PASS |

## Project Structure

### Documentation (this feature)

```text
specs/009-fondamenta-mock-test-qualita/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── mock-geban-scenarios.yaml
│   └── quality-readiness-contract.yaml
└── checklists/
    └── requirements.md
```

### Source Code (repository root)

```text
backend/
├── pyproject.toml
├── alembic/
│   └── versions/
├── app/
│   ├── main.py
│   ├── core/
│   ├── db/
│   ├── catalog/
│   ├── builder/
│   ├── generation/
│   ├── storage/
│   ├── security/
│   └── quality/
└── tests/
    ├── contract/
    ├── integration/
    ├── e2e/
    └── support/

frontend/
├── package.json
├── src/
│   ├── app/
│   ├── features/
│   │   ├── builder/
│   │   └── generazioni/
│   └── shared/
└── tests/

infra/
├── local/
│   ├── compose.yaml
│   ├── keycloak/
│   ├── postgres/
│   └── documentale-mock/
└── openapi/

mock-geban/
├── README.md
├── scenarios/
└── payloads/

docs/
└── project-map.md
```

**Structure Decision**: la `009` stabilisce la struttura target e i contratti trasversali
che i task successivi popoleranno. La repo oggi contiene principalmente Spec Kit e
documentazione; la creazione dei sorgenti applicativi avverra' in `/speckit-tasks` e
implementazione, non in questa fase.

## Complexity Tracking

Nessuna violazione costituzionale rilevata.

## Phase 0: Research

Output: [research.md](./research.md)

Decisioni chiave:

- ambiente locale containerizzato e ripetibile come default di planning;
- stack della proposta assunto per planning: FastAPI, Angular, PostgreSQL, Keycloak,
  documentale mock e OpenAPI;
- mock GEBAN guidato dai contratti pubblici e non da scorciatoie interne;
- seed demo marcati e privi di dati reali;
- registro decisioni aperte con owner, impatto, assunzione e fase bloccata;
- matrice copertura come ponte tra spec, scenari, contratti e task futuri.

## Phase 1: Design & Contracts

Output:

- [data-model.md](./data-model.md)
- [contracts/quality-readiness-contract.yaml](./contracts/quality-readiness-contract.yaml)
- [contracts/mock-geban-scenarios.yaml](./contracts/mock-geban-scenarios.yaml)
- [quickstart.md](./quickstart.md)

## Post-Design Constitution Check

| Principle | Check | Result |
|---|---|---|
| Boundary Ownership | Data model e contratti distinguono GEBAN mock, servizio GEMODO e storage/documentale. | PASS |
| Contract-First Integration | Contratti YAML definiscono readiness, scenari mock, esempi richiesti e copertura. | PASS |
| Configurable Document Models | Seed demo e coverage richiedono tipi, categorie, modelli e versioni configurabili. | PASS |
| Versioning, Traceability, Reproducibility | Scenari minimi coprono versione modello, idempotenza, stato, riferimento e audit. | PASS |
| Security, Audit, Controlled AI | Scenari includono autorizzato/non autorizzato; decisioni 006 e AI/MCP restano tracciate. | PASS |
