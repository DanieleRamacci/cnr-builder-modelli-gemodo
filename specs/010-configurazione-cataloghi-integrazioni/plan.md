# Implementation Plan: Configurazione Cataloghi E Integrazioni

**Branch**: `010-configurazione-cataloghi-integrazioni` | **Date**: 2026-09-15 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/010-configurazione-cataloghi-integrazioni/spec.md`

## Summary

Interfaccia di amministrazione con cui un operatore GEMODO definisce un tipo
documento (tipologie, profili/categorie, campi del contratto dati), genera da
quella definizione lo schema/esempio JSON che descrive la forma comune che un
sistema esterno deve implementare per integrarsi (sostituendo il percorso
file+deploy), registra
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

**Frontend pianificato (decisione 2026-09-17)**: Angular con
[Design Angular Kit](https://github.com/italia/design-angular-kit) per le
interfacce di amministrazione e builder (owner frontend: spec 007).
Versioni compatibili da fissare nel piano frontend. Nessuna interfaccia builder
e' implementata nell'incremento FR-016: `app.builder` e' un modulo backend API.

**Language/Version**: Python 3.12+ (coerente con `001`/`002`)

**Primary Dependencies**: FastAPI, Pydantic, SQLAlchemy 2, Alembic, `httpx`
(client HTTP per l'adapter di discovery esterno, gestione paginazione stile
HAL/Spring Data REST come osservato su GEBAN), moduli condivisi
`app.catalog` (modelli/repository `001`) e `app.common.security` (JWT Keycloak)

**API Documentation**: nuovo contratto OpenAPI amministrativo
(`contracts/configurazione-cataloghi-api.openapi.yaml`), distinto dal contratto
GEBAN-facing della `001` — questa e' un'API interna GEMODO, mai chiamata da un
sistema esterno. Il contratto amministrativo e' un prerequisito bloccante per
l'implementazione runtime degli endpoint: deve dichiarare path, payload,
risposte success/error, security scheme Keycloak e note di autorizzazione prima
che inizino le user story che espongono API.

**Storage**: PostgreSQL. Nuove tabelle: `attributo_profilo`,
`endpoint_integrazione`, `schema_discovery_generato` (versionato). Riusa
`tipo_documento` di `app.catalog.models` (`001`), incluso il campo diretto
`tipo_documento.codice_contesto` (`DEC-001-CONTESTO-SOSTITUISCE-UFFICIO`,
2026-09-15 — nessuna tabella `ufficio` separata). FR-016 ritira categorie,
tipologie, classificazione e registro globale con migration 0009. Le
definizioni/esempi per documentazione sono configurazione proprietaria distinta,
non tabelle del catalogo esterno. Onboarding e attributi locali restano da
implementare; nessuna FK verso categorie esterne nella loro progettazione.

**Testing**: pytest, httpx/FastAPI TestClient, test reali su Postgres (nessun
mock del DB), test del client HTTP dell'adapter con un server di prova locale
(no chiamate a GEBAN reale nei test automatici)

Ripresa fondazioni 2026-09-17: migration 0010 crea le tre tabelle
amministrative senza dati/seed GEBAN. Vincoli DB su unicita' per tipo,
versione positiva, default attributo ammesso, timeout e schema verificato
appartenente allo stesso tipo. Il guard amministrativo riusa autenticazione
e ruolo `GEMODO_ADMIN`, senza derivarlo da `GEMODO_MODELLI_GESTORE`.
Gli endpoint e i servizi US1-US4 non sono ancora implementati; l'URL runtime
del backend builder resta configurato tramite `GEMODO_DISCOVERY_ENDPOINTS`.

**Target Platform**: backend web service, stesso deployment di `001`/`002`

**Project Type**: backend web service / dominio amministrativo interno

**Performance Goals**: le API amministrative non sono ad alta frequenza
(operazione occasionale, non per-request GEBAN); 500ms p95 su dati demo e'
un obiettivo indicativo, non un criterio di accettazione o SLA verificato.
Il test di connessione (FR-008) puo' richiedere piu' tempo per la
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

Post-design re-check FR-016: PASS. La dismissione mantiene il tipo documento
configurato e i modelli proprietari; nessun set locale di tabelle esterne.

## Project Structure

### Documentation (this feature)

```text
specs/010-configurazione-cataloghi-integrazioni/
├── plan.md
├── research.md
├── data-model.md
├── contracts/
│   ├── configurazione-cataloghi-api.openapi.yaml   # API amministrativa GEMODO (FR-001..FR-009), gate pre-runtime
│   └── geban-discovery-endpoint.openapi.yaml       # contratto che GEBAN deve implementare (non un'API GEMODO), consegnato 2026-09-15 come deliverable manuale prima ancora dell'implementazione di FR-006
└── tasks.md
```

Output pianificati ma non ancora presenti: `quickstart.md` (T049/T052).
Il contratto `contracts/configurazione-cataloghi-api.openapi.yaml` e' presente
come deliverable di design e va mantenuto allineato prima di implementare gli
endpoint runtime.

### Source Code (repository root)

```text
backend/
├── app/discovery/                  # porta astratta + adapter, condiviso con 002
│   ├── port.py                     # PortaDiscovery (interfaccia astratta)
│   ├── configuration.py            # configurazione operativa esplicita, nessun fallback locale
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
│   ├── models.py                   # TipoDocumento, modelli GEMODO, versioni/contratti/audit
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

### Dismissione approvata 2026-09-17 (FR-016)

Migration 0009: backfill dei codici categoria/tipologia e del percorso sui modelli,
drop delle vecchie FK e delle tre tabelle di classificazione, ritiro del registro
campi esterno locale inutilizzato. Preservare modelli, versioni, campi e audit.
Non riscrivere migration storiche gia' applicate. Il downgrade non puo'
ricostruire gli elenchi esterni cancellati: documentare ripristino da backup.
Aggiornare ORM/repository/catalog API/builder e test come touch-point condivisi
della 010. Rimuovere AdapterLocale e dataclass legacy; porta ricorsiva unica.
La configurazione iniziale dell'URL e' operativa per sorgente/tipo documento;
la registrazione amministrativa completa rimane US3. Nessun URL reale hardcoded
nel dominio e nessun fallback a categorie/campi seed.
Aggiornare il contratto builder prima di cambiare struttura-disponibile in
risposta ricorsiva e prima di accettare percorsi generici. Catalogo modelli
pubblicati e validazione del contratto versione rimangono funzioni GEMODO.
I precedenti paragrafi che riusano tabelle di classificazione sono storici e
sono superati da questo riallineamento.

### Riallineamento 2026-09-17 prima dell'implementazione

Il discovery completo GEBAN e' disponibile. Si mantiene la modalita albero
completo per il primo collegamento; PER_NODI rimane un contratto di esempio,
non un prerequisito runtime di questo incremento.
La porta canonica restituisce nodi ricorsivi (`data-model.md`), non impone
tipologia/profilo come livelli fissi. Evoluzione e compatibilita' dei consumatori
esistenti sono lavoro esplicito T053/T054.
Autorizzazione amministrativa: `GEMODO_ADMIN` della `006`, senza nuovo ruolo.
Verifica delle variazioni: firma per ramo/dipendenze, diff sul contratto modello,
runner con indice in memoria e nessuna replica DB del catalogo (T055-T058).
Il controllo prima della generazione ufficiale e' lavoro della `004`; non si
inizia codice di altre feature con questa pianificazione.
La selezione corrente dei campi include nuovi obbligatori e dipendenze utilizzate.
La migration dei metadati per versione si progetta in T055, prima di T056.
La policy di indisponibilita' e il perimetro di unicita' della pubblicazione
richiedono conferma; la decisione nel registro non e' ancora chiusa integralmente.

Output: [research.md](./research.md)

## Phase 1: Design & Contracts

Output:

- [data-model.md](./data-model.md)
- [contracts/configurazione-cataloghi-api.openapi.yaml](./contracts/configurazione-cataloghi-api.openapi.yaml)
- [contracts/geban-discovery-endpoint.openapi.yaml](./contracts/geban-discovery-endpoint.openapi.yaml)

Pending planned outputs, tracked in `tasks.md`:

- `quickstart.md` (T049/T052), scenario end-to-end documentato dopo comportamento
  stabile.

## Dependencies

- `001-catalogo-contratto-geban`: modulo condiviso dei modelli GEMODO e del
  tipo documento con contesto. FR-016 elimina dal runtime le entita'
  esterne legacy; la storia delle migration 0001-0008 resta immutabile.
- `002-builder-modelli`: consuma la porta di discovery (`app.discovery.port`)
  prodotta da questa spec; nessuna duplicazione della logica adapter.
- `006-sicurezza-autorizzazioni-audit`: definisce il ruolo amministrativo
  distinto richiesto da FR-012.
- `DEC-001-RITIRO-ENDPOINT-CLASSIFICAZIONE`: il precedente prerequisito US2
  e' sostituito dalla decisione esplicita FR-016. Il ritiro viene eseguito
  nei task T061-T066 della feature attiva 010, non eseguendo task di un'altra spec.

## Complexity Tracking

No constitution violations requiring complexity exceptions.
