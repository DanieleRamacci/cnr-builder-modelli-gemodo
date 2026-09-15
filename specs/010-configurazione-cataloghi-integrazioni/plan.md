# Implementation Plan: Configurazione Cataloghi E Integrazioni

**Branch**: `010-configurazione-cataloghi-integrazioni` | **Date**: 2026-09-15 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/010-configurazione-cataloghi-integrazioni/spec.md`

## Summary

Interfaccia di amministrazione con cui un operatore GEMODO definisce un tipo
documento (tipologie, profili/categorie, campi del contratto dati), genera da
quella definizione lo schema/esempio JSON che un sistema esterno deve
implementare per integrarsi (sostituendo il percorso file+deploy), registra
l'endpoint di discovery fornito dal sistema esterno e ne verifica la conformita'
prima di marcare il tipo documento come "connesso" e quindi utilizzabile per
creare modelli. Introduce il pattern Ports & Adapters
(`DEC-002-PORTS-ADAPTERS-DISCOVERY`) come modulo condiviso: il builder (`002`)
e questa spec interrogano sempre una porta astratta, mai una sorgente concreta.

Chiarito nel corso della progettazione (2026-09-15): questa spec eroga anche il
sostituto funzionale delle tre API GEBAN-facing di classificazione gia'
implementate dalla `001` e ora ritirate
(`DEC-001-RITIRO-ENDPOINT-CLASSIFICAZIONE`) — non un endpoint runtime, ma la
documentazione/contratto generato da FR-006.

## Technical Context

**Language/Version**: Python 3.12+ (coerente con `001`/`002`)

**Primary Dependencies**: FastAPI, Pydantic, SQLAlchemy 2, Alembic, `httpx`
(client HTTP per l'adapter di discovery esterno, gestione paginazione stile
HAL/Spring Data REST come osservato su GEBAN), moduli condivisi
`app.catalog` (modelli/repository `001`) e `app.common.security` (JWT Keycloak)

**API Documentation**: nuovo contratto OpenAPI amministrativo
(`contracts/configurazione-cataloghi-api.openapi.yaml`), distinto dal contratto
GEBAN-facing della `001` — questa e' un'API interna GEMODO, mai chiamata da un
sistema esterno

**Storage**: PostgreSQL. Nuove tabelle: `attributo_profilo`,
`endpoint_integrazione`, `schema_discovery_generato` (versionato). Riusa
`tipo_documento`/`categoria_documento`/`tipologia_bando_sol` di
`app.catalog.models` (`001`), incluso il campo diretto
`tipo_documento.codice_contesto` (`DEC-001-CONTESTO-SOSTITUISCE-UFFICIO`,
2026-09-15 — nessuna tabella `ufficio` separata). Dipende dalla tabella
`registro_contratti_dati` che la `001` ha progettato (Phase 8,
`DEC-001-REGISTRO-CONTRATTI-DATI`) ma non ancora implementato in codice (T085,
`T087` di `001/tasks.md` sono ancora `[ ]`) — vedi Dependencies.

**Testing**: pytest, httpx/FastAPI TestClient, test reali su Postgres (nessun
mock del DB), test del client HTTP dell'adapter con un server di prova locale
(no chiamate a GEBAN reale nei test automatici)

**Target Platform**: backend web service, stesso deployment di `001`/`002`

**Project Type**: backend web service / dominio amministrativo interno

**Performance Goals**: le API amministrative non sono ad alta frequenza
(operazione occasionale, non per-request GEBAN); 500ms p95 su dati demo e'
sufficiente. Il test di connessione (FR-008) puo' richiedere piu' tempo per la
paginazione HAL, non e' nel percorso critico di generazione documenti.

**Constraints**: nessuna scrittura sul DB di un sistema esterno; la porta di
discovery MUST restare l'unico punto da cui il builder legge
categorie/tipologie/campi disponibili (mai lettura diretta della tabella
locale da parte del builder per un tipo documento integrato); cache
dell'adapter HTTP MUST essere in memoria di processo, mai una tabella DB
persistente (deciso 2026-09-15, vedi Clarifications spec.md); un'irraggiungibilita'
del sistema esterno durante la navigazione MUST produrre un errore funzionale
esplicito, mai un elenco vuoto silenzioso.

**Scale/Scope**: primo caso reale GEBAN/`BANDO_CONCORSO` (7 profili, 10
tipologie verificati); decine di tipi documento nel tempo, non centinaia.

**Reuse/Public Documentation**: `docs/adr/0001-ownership-dati-esterni-e-onboarding-contesti.md`
resta il documento di riferimento architetturale; questa spec produce il
contratto OpenAPI amministrativo e aggiorna `docs/project-map.md` a fine
implementazione.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| Boundary Ownership | PASS | Nessuna lettura/scrittura diretta del DB di un sistema esterno; ogni dato esterno arriva via endpoint di discovery registrato esplicitamente. |
| Contract-First Integration | PASS | FR-006/FR-007 rendono il contratto atteso esplicito e consegnabile prima che il sistema esterno implementi l'endpoint; nuovo OpenAPI amministrativo versionato prima dell'implementazione runtime. |
| Configurable Document Models | PASS | Tipo documento/tipologie/profili/campi restano dati configurati tramite interfaccia, non hard-coded; nessun endpoint generato dinamicamente per tipo documento (confermato nella sessione 2026-09-15). |
| Versioning, Traceability, and Reproducibility | PASS | FR-013 impone versionamento della definizione; `Schema Di Discovery Generato` e' versionato; una ridefinizione non invalida modelli gia' pubblicati (riuso dello snapshot gia' garantito da `002`/`004`). |
| Security, Audit, and Controlled AI | PASS | FR-012 richiede ruolo amministrativo distinto, dettagliato con `006`; ogni azione di definizione/registrazione/test-connessione e' un evento auditabile. |
| Public Documentation and Reuse Readiness | PASS | Il contratto amministrativo e gli esempi (incluso `docs/adr/0001-esempio-discovery-geban.json`) sono pubblicabili come esempi demo, nessun dato reale. |

Post-design re-check: PASS. Il data model aggiunge tre entita' nuove e riusa
quelle di `001` senza introdurre un secondo set di tabelle
tipo/categoria/tipologia.

## Project Structure

### Documentation (this feature)

```text
specs/010-configurazione-cataloghi-integrazioni/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── configurazione-cataloghi-api.openapi.yaml   # API amministrativa GEMODO (FR-001..FR-009)
│   └── geban-discovery-endpoint.openapi.yaml       # contratto che GEBAN deve implementare (non un'API GEMODO), consegnato 2026-09-15 come deliverable manuale prima ancora dell'implementazione di FR-006
└── tasks.md
```

### Source Code (repository root)

```text
backend/
├── app/discovery/                  # porta astratta + adapter, condiviso con 002
│   ├── port.py                     # PortaDiscovery (interfaccia astratta)
│   ├── adapter_locale.py           # legge CategoriaDocumento/TipologiaBandoSOL/RegistroContrattiDati locali
│   ├── adapter_http.py             # chiama endpoint registrato, gestisce paginazione HAL, cache in-memory a TTL breve
│   ├── cache.py                    # cache in-memory di processo (mai tabella DB)
│   └── schemas.py                  # DTO condivisi fra adapter
├── app/configurazione/
│   ├── api.py                      # endpoint amministrativi FR-001..FR-009
│   ├── models.py                   # AttributoProfilo, EndpointIntegrazione, SchemaDiscoveryGenerato
│   ├── repository.py
│   ├── service.py                  # generazione schema (FR-006), test di connessione (FR-008)
│   └── schemas.py
├── app/catalog/
│   ├── models.py                   # riusato: TipoDocumento (incluso codice_contesto), CategoriaDocumento, TipologiaBandoSOL (+ RegistroContrattiDati da 001/Phase 8)
│   └── repository.py
├── app/common/
│   ├── errors.py
│   └── security.py                 # riusato per il ruolo amministrativo FR-012
├── alembic/versions/
└── tests/
    ├── discovery/                  # unit/integration su adapter locale e HTTP (server di prova)
    └── configurazione/
        ├── contract/
        ├── integration/
        └── unit/
```

**Structure Decision**: nuovo modulo `backend/app/discovery/` per la porta
astratta e i due adapter — condiviso da questa spec (registrazione/test
endpoint, navigazione a livelli) e dalla `002` (scelta campi/placeholder in
fase di creazione modello) — evita che il builder duplichi la logica di
chiamata HTTP/cache. Nuovo modulo `backend/app/configurazione/` per il dominio
amministrativo proprio di questa spec (definizione struttura, generazione
contratto, registrazione endpoint, dashboard). Riusa `app.catalog` per le
entita' che restano di proprieta' della `001`.

## Phase 0: Research

Output: [research.md](./research.md)

## Phase 1: Design & Contracts

Output:

- [data-model.md](./data-model.md)
- [contracts/configurazione-cataloghi-api.openapi.yaml](./contracts/configurazione-cataloghi-api.openapi.yaml)
- [quickstart.md](./quickstart.md)

## Dependencies

- `001-catalogo-contratto-geban`: possiede `TipoDocumento`/`CategoriaDocumento`/
  `TipologiaBandoSOL` e il campo diretto `TipoDocumento.codice_contesto`
  (`DEC-001-CONTESTO-SOSTITUISCE-UFFICIO`, 2026-09-15 — nessuna tabella `Ufficio`
  da coordinare), e progetta (non ancora implementato) `RegistroContrattiDati`
  (Phase 8, T085, T087). **Ordine di implementazione**: le migration di
  `codice_contesto`/`RegistroContrattiDati` devono esistere prima delle tabelle
  di questa spec che le referenziano (`attributo_profilo` referenzia
  indirettamente il profilo/categoria della `001`); se `001` non le ha ancora
  implementate quando si inizia l'implementazione di `010`, questa spec le crea
  come parte del proprio primo blocco di migration invece di duplicare la
  decisione di schema gia' presa in `001/data-model.md`.
- `002-builder-modelli`: consuma la porta di discovery (`app.discovery.port`)
  prodotta da questa spec; nessuna duplicazione della logica adapter.
- `006-sicurezza-autorizzazioni-audit`: definisce il ruolo amministrativo
  distinto richiesto da FR-012.
- `DEC-001-RITIRO-ENDPOINT-CLASSIFICAZIONE`: il completamento della User Story 2
  (generazione contratto) sblocca T108 di `001/tasks.md` (rimozione delle tre
  API di classificazione legacy) — questa spec deve esistere ed essere
  funzionante prima che quel task possa essere eseguito.

## Complexity Tracking

No constitution violations requiring complexity exceptions.
