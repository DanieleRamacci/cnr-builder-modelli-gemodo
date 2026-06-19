# Implementation Plan: Catalogo Modelli E Contratto Dati GEBAN

**Branch**: `main` | **Date**: 2026-06-19 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/001-catalogo-contratto-geban/spec.md`

## Summary

Implementare le API backend che permettono a GEBAN di consultare tipi documento,
categorie e versioni modello pubblicate, ottenere il contratto dati di una specifica
versione tramite `modello_versione_id`, e validare un payload dinamico prima della
generazione documento.

L'approccio tecnico e' un servizio REST Python FastAPI con persistenza PostgreSQL,
migrations Alembic, validazione payload guidata da metadati/schema del modello tramite
Pydantic e contratti OpenAPI versionati.

## Technical Context

**Language/Version**: Python 3.12+

**Primary Dependencies**: FastAPI, Pydantic, SQLAlchemy 2, Alembic, python-jose/PyJWT,
OpenAPI tooling

**Storage**: PostgreSQL

**Testing**: pytest, httpx/FastAPI TestClient, Testcontainers PostgreSQL

**Target Platform**: backend web service deployabile su runtime Linux/container

**Project Type**: web-service

**Performance Goals**: risposte catalogo e contratto dati entro soglie compatibili con UI
GEBAN interattiva; validazione payload deterministica e senza dipendenze dal DB GEBAN

**Constraints**: nessuna lettura diretta del DB GEBAN; solo versioni `PUBBLICATO` correnti
per variante esposte in modalita' operativa; `modello_versione_id` obbligatorio per
contratto dati e validazione payload; campi non previsti nel payload sono errore bloccante

**Scale/Scope**: primo incremento backend per catalogo, contratto dati e validazione; fuori
scope builder frontend, generazione PDF dettagliata, storage documentale e sicurezza
dettagliata oltre al rispetto dei vincoli costituzionali

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Result |
|---|---|---|
| Boundary Ownership | Il piano non prevede letture/scritture DB GEBAN; GEBAN passa contesto e payload tramite API. | PASS |
| Contract-First Integration | Le API sono documentate in `contracts/geban-catalog-api.openapi.yaml` prima dei task. | PASS |
| Configurable Document Models | Tipi, categorie, modelli, versioni e campi richiesti sono dati persistiti/configurati. | PASS |
| Versioning, Traceability, Reproducibility | Le API operative usano `modello_versione_id`; validazione verifica stato pubblicato corrente. | PASS |
| Security, Audit, Controlled AI | La feature assume API protette; dettagli ruoli/audit sono in spec dedicata, senza violare il principio. | PASS |

## Project Structure

### Documentation (this feature)

```text
specs/001-catalogo-contratto-geban/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── geban-catalog-api.openapi.yaml
├── checklists/
│   └── requirements.md
└── tasks.md
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
│   │   └── settings.py
│   ├── catalog/
│   │   ├── api.py
│   │   ├── models.py
│   │   ├── repository.py
│   │   ├── schemas.py
│   │   └── service.py
│   ├── common/
│   │   ├── errors.py
│   │   └── security.py
│   ├── db/
│   │   └── session.py
│   └── validation/
│       ├── api.py
│       ├── schemas.py
│       └── service.py
└── tests/
    ├── catalog/
    ├── validation/
    └── support/
```

**Structure Decision**: per la feature 001 si crea solo il backend. Il frontend builder,
la generazione PDF e lo storage documentale appartengono a spec successive.

## Complexity Tracking

Nessuna violazione costituzionale rilevata.

## Phase 0: Research

Output: [research.md](./research.md)

Decisioni chiave:

- Stack backend Python FastAPI/PostgreSQL/Alembic coerente con la scelta aggiornata.
- API REST contract-first con OpenAPI.
- Validazione payload strict: campi extra non ammessi.
- Variante modello distinta da versione modello.
- Versione operativa selezionata sempre tramite `modello_versione_id`.
- Al massimo una versione pubblicata corrente per tipo/categoria/tipologia/variante.

## Phase 1: Design & Contracts

Output:

- [data-model.md](./data-model.md)
- [contracts/geban-catalog-api.openapi.yaml](./contracts/geban-catalog-api.openapi.yaml)
- [quickstart.md](./quickstart.md)

## Post-Design Constitution Check

| Principle | Check | Result |
|---|---|---|
| Boundary Ownership | Data model contiene solo dati del servizio modelli e non replica DB GEBAN. | PASS |
| Contract-First Integration | Contratto OpenAPI definito per catalogo, contratto dati e validazione. | PASS |
| Configurable Document Models | Entita' supportano modelli e campi configurabili. | PASS |
| Versioning, Traceability, Reproducibility | `modello_versione_id` e stato versione sono centrali nel modello dati. | PASS |
| Security, Audit, Controlled AI | Nessuna scelta contraria; la protezione API verra' cablata in coerenza con spec 006. | PASS |
