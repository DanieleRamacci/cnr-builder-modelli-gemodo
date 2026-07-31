# Implementation Plan: Catalogo Modelli E Contratto Dati GEBAN

**Branch**: `test` | **Date**: 2026-06-19 (piano aggiornato 2026-07-29) | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/001-catalogo-contratto-geban/spec.md`

## Summary

Implementare API backend protette da JWT Keycloak che permettono a GEBAN di consultare
tipi documento, categorie e versioni modello pubblicate, ottenere il contratto dati di
una specifica versione tramite `modello_versione_id`, e validare un payload dinamico
prima della generazione documento.

L'approccio tecnico e' un servizio REST Python FastAPI con persistenza PostgreSQL,
migrations Alembic, validazione payload guidata da metadati/schema del modello tramite
Pydantic e contratti OpenAPI versionati.

**Aggiornamento 2026-07-29**: il piano recepisce le decisioni propagate da `009` (vedi
`spec.md`, sessione "Session 2026-07-29"): validazione tipologia GEBAN/SOL, campi con
lingua condizionata da `bando_inglese`, e la dipendenza dallo scheletro backend e dai
manifest di qualita' gia' creati dalla `009` (`backend/pyproject.toml`,
`backend/app/main.py`, `backend/alembic/`, `infra/local/postgres/seed-demo-catalog.yaml`).
Questa feature **estende** quello scheletro, non lo ricrea.

**Aggiornamento 2026-07-31**: il piano recepisce il chiarimento sul confine
Keycloak/GEMODO: la `001` implementa gia' la protezione minima delle proprie API
operative con JWT Bearer Keycloak (firma/JWKS, issuer, audience `gemodo-backend`,
scadenza, client tecnico `geban-backend` e ruoli `DOCUMENTI_GENERATORE` /
`DOCUMENTI_VIEWER`). Audit completo, autorizzazioni fini per profilo GEBAN, builder e
workflow sicurezza restano nella `006`.

## Technical Context

**Language/Version**: Python 3.12+

**Primary Dependencies**: FastAPI, Pydantic, SQLAlchemy 2, Alembic, PyJWT/cryptography
per validazione JWT/JWKS, httpx per recupero JWKS, OpenAPI tooling - stesso stack e
stesso progetto backend gia' avviato dalla `009`
(`backend/pyproject.toml`), non un progetto separato

**Storage**: PostgreSQL (stessa istanza/schema della `009`, baseline
`backend/alembic/versions/0001_initial_schema.py`; questa feature aggiunge le proprie
migrations sopra quella baseline, vedi `backend/alembic/README.md` per l'ownership)

**Testing**: pytest, httpx/FastAPI TestClient, Testcontainers PostgreSQL (o PostgreSQL
locale reale se Testcontainers/Docker non e' disponibile nell'ambiente di sviluppo -
vedi `backend/pytest.ini` della `009` per i marker `contract`/`integration`/`e2e` gia'
configurati)

**Target Platform**: backend web service deployabile su runtime Linux/container

**Project Type**: web-service

**Performance Goals**: risposte catalogo e contratto dati entro soglie compatibili con UI
GEBAN interattiva; validazione payload deterministica e senza dipendenze dal DB GEBAN

**Constraints**: nessuna lettura diretta del DB GEBAN; solo versioni `PUBBLICATO` correnti
per variante esposte in modalita' operativa; `modello_versione_id` obbligatorio per
contratto dati e validazione payload (resta intero int64, `DEC-001-IDENTIFICATIVI-MODELLO`;
in persistenza la baseline `009` mantiene UUID interni e la `001` espone un `public_id`
intero stabile);
campi non previsti nel payload sono errore bloccante; `codice_tipologia` deve corrispondere
a una tipologia GEBAN/SOL configurata (FR-020); campi con `lingua: EN` sono obbligatori
solo se `bando_inglese: true` (FR-021, FR-022); le route operative richiedono JWT
Keycloak valido con audience `gemodo-backend`, client `geban-backend` per il canale GEBAN
e ruolo coerente (`DOCUMENTI_VIEWER` per consultazione, `DOCUMENTI_GENERATORE` per
validazione); profilo GEBAN versionato e autorizzazione fine restano fuori scope
(`DEC-001-PROFILO-GEBAN`, owner `006`)

**Scale/Scope**: primo incremento backend per catalogo, contratto dati, validazione e
protezione JWT minima delle API; fuori scope builder frontend, generazione PDF
dettagliata, storage documentale, audit completo e autorizzazioni fini per profilo

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Result |
|---|---|---|
| Boundary Ownership | Il piano non prevede letture/scritture DB GEBAN; GEBAN passa contesto e payload tramite API. | PASS |
| Contract-First Integration | Le API sono documentate in `contracts/geban-catalog-api.openapi.yaml` prima dei task. | PASS |
| Configurable Document Models | Tipi, categorie, modelli, versioni e campi richiesti sono dati persistiti/configurati. | PASS |
| Versioning, Traceability, Reproducibility | Le API operative usano `modello_versione_id`; validazione verifica stato pubblicato corrente. | PASS |
| Security, Audit, Controlled AI | La feature implementa JWT Bearer Keycloak minimo sulle API operative; audit completo e autorizzazioni fini restano in spec 006. | PASS |

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
├── pyproject.toml            # esiste gia' (009): aggiungere dipendenze proprie, non ricreare
├── pytest.ini                 # esiste gia' (009): marker contract/integration/e2e gia' configurati
├── alembic/
│   ├── env.py                 # esiste gia' (009)
│   └── versions/
│       └── 0001_initial_schema.py   # baseline (009): 001 aggiunge migrations successive
├── app/
│   ├── main.py                # esiste gia' (009, con router Swagger/ReDoc): 001 monta i propri router qui
│   ├── core/
│   │   ├── __init__.py        # esiste gia' (009)
│   │   └── settings.py        # NUOVO in questa feature
│   ├── catalog/                # NUOVO in questa feature
│   │   ├── api.py
│   │   ├── models.py
│   │   ├── repository.py
│   │   ├── schemas.py
│   │   └── service.py
│   ├── common/                 # NUOVO in questa feature
│   │   ├── errors.py
│   │   └── security.py
│   ├── db/
│   │   ├── __init__.py        # esiste gia' (009)
│   │   └── session.py         # NUOVO in questa feature
│   └── validation/              # NUOVO in questa feature
│       ├── api.py
│       ├── schemas.py
│       └── service.py
└── tests/
    ├── support/                # esiste gia' (009, con fixture quality_fixtures.py ecc.): aggiungere fixture proprie, non ricreare il package
    ├── common/                  # NUOVO in questa feature per errori/sicurezza comuni
    ├── catalog/                 # NUOVO in questa feature
    └── validation/               # NUOVO in questa feature
```

**Structure Decision**: per la feature 001 si crea solo il backend, riusando lo
scheletro applicativo gia' avviato dalla `009` (stesso `pyproject.toml`, stesso
`app/main.py`, stessa baseline Alembic). Il frontend builder, la generazione PDF e lo
storage documentale appartengono a spec successive.

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
- Tipologia GEBAN/SOL validata contro un elenco configurato, non stringa libera
  (`DEC-001-TIPOLOGIE-SOL`).
- Campo con `lingua` e obbligatorieta' condizionata da `bando_inglese`, senza un
  secondo meccanismo di validazione (`DEC-001-LINGUA-IT-EN`).
- Campi comuni GEBAN, bando multiplo e ribando restano dati del contratto dinamico
  esistente, non nuove entita' di dominio.
- JWT Keycloak Bearer e' validato gia' nella `001` per le route operative; il principal
  ricostruito contiene client, audience e ruoli minimi, senza gestire credenziali in
  GEMODO.
- `modello_versione_id` resta intero (int64); profilo GEBAN e autorizzazione fine
  restano fuori scope di questa feature.

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
| Security, Audit, Controlled AI | Le API operative della `001` includono validazione JWT Keycloak minima coerente con `SEC-006-001`; audit completo e profili restano alla `006`. | PASS |
