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
`spec.md`, sessione "Session 2026-07-29"): validazione tipologia GEBAN/SOL, metadato
lingua sui campi e dipendenza dallo scheletro backend e dai
manifest di qualita' gia' creati dalla `009` (`backend/pyproject.toml`,
`backend/app/main.py`, `backend/alembic/`, `infra/local/postgres/seed-demo-catalog.yaml`).
Questa feature **estende** quello scheletro, non lo ricrea.

**Aggiornamento 2026-07-31**: il piano recepisce il chiarimento sul confine
Keycloak/GEMODO: la `001` implementa gia' la protezione minima delle proprie API
operative con JWT Bearer Keycloak (firma/JWKS, issuer, audience `gemodo-backend`,
scadenza, client tecnico `geban-backend` e ruoli `DOCUMENTI_GENERATORE` /
`DOCUMENTI_VIEWER`). Audit completo, autorizzazioni fini per profilo GEBAN, builder e
workflow sicurezza restano nella `006`.

**Aggiornamento 2026-09-14 (secondo incremento)**: riprende `DEC-001-PROFILO-GEBAN` e
le decisioni collegate (ora `CONFERMATA`, vedi `research.md` e `data-model.md`
aggiornati). Introduce: enforcement del perimetro contrattuale per profilo di
integrazione dentro le route catalogo/validazione esistenti (FR-025..FR-027); un
registro di contratti dati riusabili scoped per tipo documento (FR-028..FR-029); la
distinzione fra proprieta' di scrittura e `Applicazione`/`ProfiloDiIntegrazione`
(consumo, indipendentemente da chi possiede — FR-031); la generalizzazione di
`TipologiaBandoSOL` a `TipologiaDocumento`, scoped per tipo documento invece che
globale; e il passaggio del manifest profili da YAML-in-memoria a dati persistiti
seedabili (FR-030). Nota 2026-09-15/16: i riferimenti originari a `Ufficio`
proprietario, campo `ufficio:` e file+deploy come meccanismo di onboarding sono stati
superseduti da `DEC-001-CONTESTO-SOSTITUISCE-UFFICIO` e dalla spec `010`: la proprieta'
di scrittura e' `TipoDocumento.codice_contesto`, mentre onboarding/registrazione
endpoint sono responsabilita' della `010`.

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
a una tipologia GEBAN/SOL configurata (FR-020); tutti i campi obbligatori del contratto
della versione selezionata sono richiesti (FR-021, FR-022); le route operative richiedono JWT
Keycloak valido con audience `gemodo-backend`, client `geban-backend` per il canale GEBAN
e ruolo coerente (`DOCUMENTI_VIEWER` per consultazione, `DOCUMENTI_GENERATORE` per
validazione).

**Constraints (secondo incremento, 2026-09-14; riallineate 2026-09-16)**: ogni richiesta catalogo/validazione
deve risolvere il profilo di integrazione del chiamante e verificare tipo documento,
categoria, tipologia e `modello_versione_id` contro il suo perimetro ammesso
(FR-025..FR-027), con errore `PROFILO_INTEGRAZIONE_NON_ABILITATO` distinto dall'elenco vuoto; ogni
`TipoDocumento` deve avere un `codice_contesto` proprietario (FR-031,
`DEC-001-CONTESTO-SOSTITUISCE-UFFICIO`); ogni riferimento in
`contratti_dati_ammessi` deve corrispondere a un contratto dati esistente nel registro,
altrimenti il caricamento fallisce (FR-029). La configurazione/onboarding dei dati di
struttura e la registrazione endpoint sono demandate alla `010`, non a una tabella
`Ufficio` o a un file+deploy come sorgente definitiva;
`codice_tipologia` e il codice errore `TIPOLOGIA_SOL_NON_VALIDA` restano invariati nel
contratto pubblico nonostante il rename interno `TipologiaBandoSOL` ->
`TipologiaDocumento`.

**Scale/Scope**: primo incremento backend per catalogo, contratto dati, validazione e
protezione JWT minima delle API; fuori scope builder frontend, generazione PDF
dettagliata, storage documentale, audit completo. Secondo incremento (2026-09-14):
enforcement del perimetro per profilo, proprieta' via `codice_contesto`, registro
contratti dati, generalizzazione tipologia. Fuori scope della `001`: interfaccia
amministrativa di onboarding/configurazione cataloghi, registrazione endpoint e
discovery live, ora tracciate nella `010`; grant cross-contesto avanzati restano fuori
da questo incremento.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Result |
|---|---|---|
| Boundary Ownership | Il piano non prevede letture/scritture DB GEBAN; GEBAN passa contesto e payload tramite API. | PASS |
| Contract-First Integration | Le API sono documentate in `contracts/geban-catalog-api.openapi.yaml` prima dei task. | PASS |
| Configurable Document Models | Tipi, categorie, modelli, versioni e campi richiesti sono dati persistiti/configurati. | PASS |
| Versioning, Traceability, Reproducibility | Le API operative usano `modello_versione_id`; validazione verifica stato pubblicato corrente. | PASS |
| Security, Audit, Controlled AI | La feature implementa JWT Bearer Keycloak minimo sulle API operative; audit completo e autorizzazioni fini restano in spec 006. | PASS |

### Constitution Check - secondo incremento (2026-09-14)

| Principle | Check | Result |
|---|---|---|
| Boundary Ownership | Il perimetro per-profilo/contesto resta interno a GEMODO; nessuna nuova lettura/scrittura verso il DB GEBAN. | PASS |
| Contract-First Integration | Nuovo codice errore `PROFILO_INTEGRAZIONE_NON_ABILITATO` documentato in `data-model.md`; contratto OpenAPI pubblico va aggiornato prima dell'implementazione (`DEC-001-API-PROFILO-GEBAN`), non durante. | PASS (azione richiesta prima dei task) |
| Configurable Document Models | Registro contratti dati e proprieta' via `codice_contesto` sono dati configurati/persistiti, non hard-coded; la costituzione nomina esplicitamente graduatorie fra i tipi documento futuri attesi, coerente con la generalizzazione fatta ora. | PASS |
| Versioning, Traceability, Reproducibility | Nessun impatto: `modello_versione_id` e stato versione restano centrali; il rename `TipologiaDocumento` non tocca identificativi pubblici. | PASS |
| Security, Audit, Controlled AI | Collega l'autorizzazione applicativa (006, gia' implementata) al perimetro catalogo (001, non ancora); backend continua a essere l'unico punto di enforcement autoritativo. | PASS |

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
- Lingua determinata dalla versione modello; il payload non contiene un flag
  specifico del contesto (`DEC-001-LINGUA-IT-EN`, revisione 2026-09-21).
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

## Phase 0/1 - Secondo incremento (2026-09-14)

Output:

- [research.md](./research.md), sezione "Secondo incremento (2026-09-14)": decisioni
  storiche su registro contratti dati, generalizzazione tipologia, profili su dati
  persistiti ed enforcement nelle route esistenti. Le parti su `Ufficio` sono state
  supersedute dalla sezione "Quarto incremento (2026-09-15)".
- [data-model.md](./data-model.md): `TipologiaDocumento` (rinominata da
  `TipologiaBandoSOL`), `RegistroContrattiDati`, `ProfiloDiIntegrazione`
  (riferimento), `TipoDocumento.codice_contesto`, nuovo codice errore
  `PROFILO_INTEGRAZIONE_NON_ABILITATO`, relazioni aggiornate. L'entita' `Ufficio` e'
  rimossa.

**Non ancora prodotto per questo incremento** (da fare durante la generazione dei
task, quando le scelte implementative esatte — nomi endpoint di dependency injection,
schema di risposta errore — saranno fissate):

- Aggiornamento di `contracts/geban-catalog-api.openapi.yaml` con `PROFILO_INTEGRAZIONE_NON_ABILITATO`.
- Nuovi scenari in `quickstart.md` per il perimetro per-profilo e la distinzione
  contesto proprietario/Applicazione.
- Migration Alembic (`0008` e successive) per `codice_contesto`, registro contratti
  dati e generalizzazione tipologia; nessuna tabella `ufficio`.

Questo e' un ambito di lavoro deliberatamente lasciato a `tasks.md`, non un buco nel
piano: la costituzione richiede contratti espliciti "prima dell'implementazione", non
prima della pianificazione — le decisioni architetturali (chi possiede cosa, come si
autorizza, come si generalizza) sono chiuse; i dettagli di wire format restano legati
alla sequenza dei task.

## Terzo incremento (2026-09-15): cascading ADR 0001

**Aggiornamento**: `docs/adr/0001-ownership-dati-esterni-e-onboarding-contesti.md`
(deciso dopo una riunione col team GEBAN/ACE) cambia la sorgente di
`CategoriaDocumento`, `TipologiaDocumento`, `ClassificazioneCatalogo` e
`RegistroContrattiDati` per un tipo documento integrato: da seed permanente
posseduto da GEMODO a cache locale a TTL breve, sincronizzata da un adapter HTTP
verso l'endpoint di discovery registrato per quel tipo documento
(`DEC-001-OWNERSHIP-DATI-ESTERNI`, `DEC-002-PORTS-ADAPTERS-DISCOVERY`). Vedi
[data-model.md](./data-model.md), sezione "Nota Sull'Ownership Dei Dati".

**Dipendenza esplicita**: lo schema esatto dell'adapter (tabella
`endpoint_integrazione`, meccanismo di cache/TTL, gestione paginazione, test di
connessione) e' progettato in `specs/010-configurazione-cataloghi-integrazioni`
(nuova spec dedicata all'interfaccia di amministrazione che genera il contratto
atteso e registra l'endpoint), non duplicato qui. La `001` referenzia quello
schema quando disponibile, invece di riprogettarlo.

**Impatto su `tasks.md`**: i task `T077`-`T079` e `T085` del secondo incremento
(Phase 8, seed locale per contesto/tipologie/contratti dati) restano validi per
l'uso come fixture di un adapter locale/mock (sviluppo e test senza rete verso
GEBAN); il caricamento in produzione della categorizzazione di `BANDO_CONCORSO`
passa pero' dall'adapter HTTP configurato in `010`, non piu' esclusivamente dalla
migration che rilegge il file. Annotazioni aggiunte direttamente su ciascun task
interessato in `tasks.md`, senza rinumerare i task esistenti.

**Non cambia**: l'enforcement del perimetro per profilo (User Story 5, FR-025..
FR-027) e la generalizzazione `TipologiaDocumento` restano identici a come
pianificati nel secondo incremento — l'ADR cambia *da dove arrivano i dati*, non
*come si applica il perimetro* su di essi.

## Quarto incremento (2026-09-15): il contesto del token sostituisce Ufficio

**Aggiornamento**: `DEC-001-CONTESTO-SOSTITUISCE-UFFICIO` (CONFERMATA) supersede
`DEC-001-UFFICIO-PROPRIETARIO`. Non esiste piu' un'entita'/tabella `Ufficio`
separata: `TipoDocumento` porta un campo diretto `codice_contesto` che deve
corrispondere a una chiave `contexts.<codice_contesto>.roles` nel token del
chiamante (meccanismo gia' implementato in `backend/app/common/security.py` per
GEBAN, mai esteso con una nuova entita'). Un utente con piu' contesti nel token
vede/gestisce l'unione dei tipi documento associati a ciascuno, verificati
**separatamente** — mai come permessi gia' appiattiti su tutti i contesti insieme
(vedi `data-model.md`, entita' `Ufficio` rimossa, e nota su `DEC-002-SORGENTE-
UFFICIO-TOKEN` nel registro decisioni per il rischio di permission bleed che
questo evita).

**Impatto su `tasks.md`**: `T085` riscritto (aggiunge `tipo_documento.
codice_contesto`, nessuna tabella `ufficio` ne' FK); `T086` non piu' necessario
(nessun modello SQLAlchemy `Ufficio` da aggiungere); `T077` riscritto (campo
diretto `codice_contesto:` nel seed, nessuna sezione `uffici:`); `T095`
rinominato da "cross-ufficio" a "cross-contesto" (stesso comportamento, nome
corretto).

**Impatto sulla sicurezza (rilevante per `002`/`006`)**: l'autorizzazione di
scrittura per un `TipoDocumento` specifico MUST essere risolta guardando SOLO il
contesto corrispondente a `codice_contesto` nel token del chiamante, non la lista
di `internal_permissions` gia' derivata e appiattita su tutti i contesti presenti
(`PrincipalGEMODO.ruoli`, oggi flat). Serve una funzione di autorizzazione
scoped-per-contesto distinta dal pattern `ensure_roles(principal, ruoli)` gia' in
uso per i permessi non scoped (es. `DOCUMENTI_VIEWER`); vedi `002/plan.md`.

**Non cambia**: la distinzione concettuale proprieta'(scrittura)/consumo(lettura-
generazione) fra `TipoDocumento` e `ProfiloDiIntegrazione` (FR-025..FR-031)
resta la stessa — cambia solo il meccanismo con cui si rappresenta "chi
possiede", non il principio.
