# Implementation Plan: Fondamenta Mock Test E Qualita

**Branch**: `test` | **Date**: 2026-06-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/009-fondamenta-mock-test-qualita/spec.md`

## Summary

Definire le fondamenta verificabili del progetto GEMODO: ambiente locale ripetibile,
migrations e seed demo coerenti con le spec, mock GEBAN contract-first, scenari
end-to-end minimi, matrice di copertura, profili applicativi di integrazione, modello
documentale controllato, documentazione API navigabile, readiness open source/PA e
registro delle decisioni aperte.

L'approccio tecnico e' trattare questa feature come layer trasversale: prepara struttura,
contratti di qualita' e criteri di validazione che i task successivi useranno per
implementare backend, frontend, mock, dati demo, audit e test senza introdurre assunzioni
implicite.

Il piano recepisce inoltre il confine atteso tra Keycloak e GEMODO: Keycloak autentica
utenti e client tecnici e fornisce ruoli/claim generali; GEMODO mantiene le autorizzazioni
applicative fini su sistemi richiedenti, profili di integrazione, tipi documento,
categorie, modelli/versioni, contratti dati e operazioni.

Il piano recepisce anche il confine del builder visuale futuro: l'utente comporra' il
documento tramite blocchi e posizionamenti ammessi, senza scrivere HTML/CSS libero. La
prima fase deve quindi seedare un modello documentale controllato e versionato, usabile dal
renderer PDF e riusabile dal builder come sorgente dati.

Il piano recepisce infine il vincolo di pubblicazione e riuso: ogni API pubblica o di
integrazione deve avere OpenAPI versionato, esempi JSON, catalogo errori e documentazione
interattiva locale/test da stessa sorgente; il repository deve esporre una documentazione
navigabile per comprendere fasi Spec Kit, blocchi, decisioni, vincoli e guide operative.

## Technical Context

**Language/Version**: Python 3.12+ per backend, TypeScript moderno per frontend, YAML/JSON
per contratti e manifest di qualita'

**Primary Dependencies**: FastAPI, Pydantic, SQLAlchemy 2, Alembic, Angular, OpenAPI
tooling, Keycloak CNR di test reale (`sso.test.si.cnr.it`, realm `cnr`) via variabili
d'ambiente, con Keycloak containerizzato come fallback opzionale per sviluppo offline,
strumenti di orchestrazione ambiente locale

**API Documentation**: OpenAPI YAML versionati in `infra/openapi/`, esempi JSON
pubblicabili, catalogo errori, Swagger UI e ReDoc generati dalla stessa sorgente in
locale/test

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
tasks implementativi come assunzioni silenziose; sicurezza e audit seguono la spec 006;
Keycloak non diventa sorgente delle abilitazioni fini su modelli e contratti GEMODO;
il builder non espone HTML/CSS libero e usa una struttura documentale controllata;
endpoint pubblici o di integrazione non entrano in implementazione runtime senza OpenAPI,
esempi, catalogo errori e documentazione API navigabile; esempi e documentazione pubblica
non devono contenere segreti o dati reali

**Scale/Scope**: primo incremento trasversale per struttura di progetto, ambiente locale,
mock GEBAN, seed demo, contratti di qualita', scenari minimi, profili di integrazione,
modello documentale controllato, documentazione API, readiness open source/PA e registro
decisioni; fuori scope implementare tutte le feature applicative finali

**Reuse/Public Documentation**: README come punto di ingresso, MkDocs generato da
`scripts/generate-spec-docs.py`, pagine per roadmap Spec Kit, feature attiva, readiness
API, decisioni/vincoli e checklist open source/PA; licenza definitiva da confermare prima
della pubblicazione pubblica

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Result |
|---|---|---|
| Boundary Ownership | Il piano prevede mock GEBAN e contratti, non accesso diretto al DB GEBAN. | PASS |
| Contract-First Integration | I contratti di qualita' e mock richiedono OpenAPI/esempi prima dei task implementativi. | PASS |
| Configurable Document Models | Seed e migrations devono riflettere modelli configurabili, non logica hard-coded. | PASS |
| Versioning, Traceability, Reproducibility | Seed, scenari e matrice copertura tracciano versioni modello, generazioni, audit e idempotenza. | PASS |
| Security, Audit, Controlled AI | Il piano include Keycloak CNR di test reale (fallback locale opzionale), principal mock, profili applicativi GEMODO, scenari autorizzativi, audit e decisioni AI/MCP non bloccanti. | PASS |
| Public Documentation and Reuse Readiness | Il piano include OpenAPI, Swagger/ReDoc, esempi pubblicabili, portale MkDocs e readiness open source/PA. | PASS |

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
│   ├── integration-profiles.local.yaml
│   ├── document-models/
│   ├── keycloak/
│   ├── postgres/
│   └── documentale-mock/
└── openapi/
    ├── README.md
    ├── errors.md
    └── examples/

docs/
├── index.md
├── project-map.md
├── api-documentation.md
├── open-source-pa-readiness.md
└── spec-kit/
    ├── index.md
    ├── active-feature.md
    ├── api-readiness.md
    ├── roadmap.md
    └── decisions-and-vincoli.md

mock-geban/
├── README.md
├── scenarios/
└── payloads/

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
- Keycloak come sorgente di identita', client e ruoli/claim generali, con autorizzazioni
  fini gestite da GEMODO tramite profili applicativi versionati;
- modello documentale controllato come sorgente versionata che il builder visuale futuro
  manipolera' senza HTML/CSS libero;
- documentazione API contract-first con OpenAPI, esempi JSON, catalogo errori e Swagger/ReDoc;
- readiness open source/PA come documentazione testuale navigabile e pubblicabile;
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
| Security, Audit, Controlled AI | Scenari includono autorizzato/non autorizzato, distinzione token/ruoli Keycloak e autorizzazioni fini GEMODO; decisioni 006 e AI/MCP restano tracciate. | PASS |
| Public Documentation and Reuse Readiness | Contratti e task richiedono documentazione API navigabile, esempi demo sicuri e pagine di riuso PA. | PASS |
