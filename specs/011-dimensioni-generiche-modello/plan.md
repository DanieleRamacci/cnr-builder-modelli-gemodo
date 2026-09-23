# Implementation Plan: Dimensioni Generiche Del Modello

**Branch**: `011-dimensioni-generiche-modello` | **Date**: 2026-09-23 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/011-dimensioni-generiche-modello/spec.md`

## Summary

La categorizzazione di un modello smette di essere due colonne dedicate
(`lingua`, `livello_professionale`) e diventa un documento JSONB `dimensioni`
per nome di dimensione. Le sei superfici oggi cablate su quei due nomi —
enforcement, persistenza, identita', unicita' della pubblicazione, elenco al
builder, fallback del catalogo — passano a iterare sulle policy registrate per
il tipo documento. `PolicyDimensione` non cambia forma: cambia chi la fa
rispettare. Il contratto verso GEBAN si estende in modo additivo e non rompente.

L'approccio tecnico e' deciso in [research.md](research.md); lo schema in
[data-model.md](data-model.md); i due delta contrattuali in
[contracts/](contracts/); la verifica eseguibile in [quickstart.md](quickstart.md).

## Technical Context

**Language/Version**: Python 3.12+ (backend), TypeScript / Angular 21 (frontend)

**Primary Dependencies**: FastAPI >= 0.115, Pydantic >= 2.9, SQLAlchemy >= 2.0, Alembic >= 1.13

**API Documentation**: due delta OpenAPI in `contracts/`, da riversare negli
OpenAPI versionati serviti da Swagger UI e ReDoc. `catalogo-modelli-dimensioni.openapi.yaml`
porta un marcatore `x-gemodo-richiede-accordo` sul solo punto non approvato.

**Storage**: PostgreSQL. La feature usa JSONB e indice GIN: non e' sostituibile
da un backend che non li abbia.

**Testing**: pytest (`backend/tests/`: `builder/`, `catalog/`, `contract/`,
`integration/`, `e2e/`), Playwright per l'e2e frontend, Karma/Jasmine per gli
unit Angular.

**Target Platform**: Linux server in Docker, dietro Traefik.

**Project Type**: web service + frontend amministrativo (backend FastAPI,
frontend Angular).

**Performance Goals**: nessun obiettivo nuovo. L'unico rischio di regressione e'
la ricerca catalogo, che passa da filtro su colonna a uguaglianza/contenimento
JSONB: mitigato dall'indice GIN e da mantenere sotto osservazione, non da
ottimizzare in anticipo.

**Constraints**:

- il contratto verso GEBAN non puo' cambiare comportamento per le richieste che
  fa oggi (FR-008, Assumptions della spec);
- la migrazione deve preservare identita', pubblicazione e collegamento ai
  documenti generati (FR-007);
- una dimensione sparita dall'albero non puo' rendere illeggibile un modello
  (FR-009).

**Scale/Scope**: 65 foglie sull'albero GEBAN reale, 1047 campi. Il volume non e'
il problema; la generalita' lo e'.

**Reuse/Public Documentation**: `docs/` — contratto dati verso GEBAN, catalogo
errori (nuovo `DIMENSIONE_NON_DICHIARATA`), modello di configurazione delle
policy per dimensione. Da aggiornare nello stesso incremento, non dopo.

## Constitution Check

*GATE: passato prima di Phase 0, ri-verificato dopo Phase 1.*

| Principio | Esito | Nota |
| --- | --- | --- |
| I. Boundary Ownership | **Pass** | Le dimensioni le dichiara l'integrazione via discovery, GEMODO non legge il database GEBAN. La feature rafforza il confine: oggi una categorizzazione nuova richiede codice GEMODO, dopo non piu'. |
| II. Contract-First Integration | **Pass** | Due delta OpenAPI scritti prima dell'implementazione. `lingua` nullable e' schema-breaking ma behavior-safe: nessuna richiesta che GEBAN fa oggi cambia risposta, perche' `search_modelli` impone `tipo_documento` e tutti i tipi che GEBAN consuma dichiarano la lingua. Richiede una presa d'atto prima del rilascio, non un'approvazione preventiva. |
| III. Configurable Document Models | **Pass, principio portante** | E' la feature che rende vero il principio per la categorizzazione: «il servizio non deve cablare ogni documento generabile nella logica applicativa». |
| IV. Versioning, Traceability, Reproducibility | **Pass** | FR-007 e lo Scenario 6 del quickstart verificano che la migrazione preservi il legame documento generato → modello. L'idempotenza della generazione non passa dalle colonne rimosse. |
| V. Security, Audit, Controlled AI | **Pass** | Nessuna superficie di autorizzazione cambia. `MODELLO_CREATO` continua a essere registrato; il payload minimo dell'evento va esteso con le dimensioni, perche' altrimenti l'audit perde l'informazione che oggi ricava dalle colonne. **Da mettere a task.** |
| VI. Public Documentation and Reuse | **Pass, con lavoro** | Il catalogo errori guadagna `DIMENSIONE_NON_DICHIARATA`; il modello di configurazione delle policy va documentato per un integratore esterno. Task propri, non coda. |

**Nessuna violazione da giustificare.** Complexity Tracking resta vuoto.

Ri-verifica post-Phase 1: invariata. Il disegno non ha introdotto progetti,
livelli di astrazione o dipendenze nuove — ha tolto due colonne e sostituito
due chiamate letterali con un ciclo.

## Project Structure

### Documentation (this feature)

```text
specs/011-dimensioni-generiche-modello/
├── plan.md              # questo file
├── spec.md
├── research.md          # Phase 0 - sei decisioni DEC-011-*
├── data-model.md        # Phase 1 - schema e migrazione
├── quickstart.md        # Phase 1 - sette scenari eseguibili
├── contracts/
│   ├── builder-modelli-dimensioni.openapi.yaml    # interno, evolve senza GEBAN
│   └── catalogo-modelli-dimensioni.openapi.yaml   # verso GEBAN, additivo
├── checklists/
└── tasks.md             # Phase 2 - prodotto da /speckit.tasks, NON da qui
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── catalog/
│   │   ├── models.py        # ModelloDocumento: -lingua -livello_professionale +dimensioni
│   │   ├── schemas.py       # ModelloCatalogoSchema +dimensioni (additivo)
│   │   ├── service.py       # fallback governato da policy (FR-010)
│   │   ├── repository.py    # filtri su JSONB
│   │   └── api.py           # parametro dimensione[...] deepObject
│   ├── builder/
│   │   ├── service.py       # _verifica_dimensione in ciclo, _identita_modello,
│   │   │                    # _dimensioni_note, POLICY_DI_RIPIEGO, DIMENSIONI_SENZA_GENERICO
│   │   ├── repository.py    # get_versione_pubblicata_corrente, lista_modelli, voci_filtro
│   │   └── schemas.py       # CreaModelloRequest.dimensioni
│   ├── configurazione/
│   │   └── service.py       # _dimensioni_catalogo: GIA' GENERICO, non si tocca
│   └── discovery/
│       └── schemas.py       # NodoDiscovery extra="allow": GIA' GENERICO, non si tocca
├── alembic/versions/
│   └── 0020_dimensioni_modello.py       # nuova
└── tests/
    ├── builder/            # US1, US2 - enforcement e identita'
    ├── catalog/            # US3, FR-010 - unicita' e fallback
    ├── contract/           # FR-008 - non-regressione del contratto GEBAN
    ├── integration/        # FR-007 - migrazione su PostgreSQL con dati
    └── e2e/                # US5 - il caso `contratti` end-to-end

frontend/src/features/
├── builder/
│   └── modello-crea.component.ts        # form a dimensioni generiche, nessun default
└── configurazione/
    ├── dimensioni.component.html        # via [disabled]="...=== 'lingua'" (riga 166),
    │                                    # dentro l'avviso calcolato prima del salvataggio
    └── dimensioni.component.ts          # conteggi per l'avviso; resto gia' generico

mock-geban/                              # albero con `contratti`/`area_geografica`
docs/                                    # catalogo errori, contratto dati, policy
```

**Structure Decision**: struttura esistente, nessun modulo nuovo. Il lavoro si
concentra in `backend/app/builder/` e `backend/app/catalog/`; `configurazione/`
e `discovery/` sono gia' generici e vanno lasciati stare — e' un punto da
ripetere nei task, perche' la tentazione di "sistemarli" ci sara'.

## Ordine di implementazione

Le tre P1 sono in sequenza obbligata, non per priorita' ma per dipendenza: senza
un posto dove scrivere il valore non c'e' nulla da far rispettare, e senza valori
registrati non c'e' unicita' da calcolare.

| # | Blocco | Copre | Dipende da | Bloccato da fuori |
| --- | --- | --- | --- | --- |
| 1 | Schema + migration `0020` | FR-001, FR-007 | — | no |
| 2 | Enforcement in ciclo sulle policy | FR-002, FR-006 (US2) | 1 | no |
| 3 | Identita' e unicita' pubblicazione | FR-003, FR-004, FR-012 (US1, US3) | 1 | no |
| 4 | Dimensioni note dal vivo, mai dal codice | FR-005 | 2 | no |
| 5 | Fallback governato dalla policy | FR-010 | 2 | no |
| 6 | Contratto catalogo: `dimensioni` aggiunto, `lingua` nullable | FR-008, US4 | 3 | no |
| 7 | Frontend builder: dimensioni generiche + default dichiarato | FR-011 | 2 | no |
| 8 | Frontend policy: flag all'admin + avviso calcolato | FR-002, US4 | 5, 6 | no |
| 8b | Derivazione governata dalla policy | FR-013, FR-014 | 2, 6 | no |
| 9 | Caso `contratti` end-to-end, catalogo compreso | US5 | 1-8b | no |

**Nessun blocco dipende da una risposta esterna.** La prima stesura del piano
isolava l'esposizione nel catalogo dei tipi documento senza lingua come blocco
in attesa di GEBAN; DEC-011-CONTRATTO-GEBAN-ADDITIVO l'ha sciolto dopo aver
verificato che `search_modelli` richiede `tipo_documento` obbligatorio, quindi
GEBAN non riceve mai risposte miste e il campo nullable non e' mai esercitato
sulle richieste che fa oggi. Resta una **presa d'atto** da consegnare a GEBAN
prima del rilascio, che e' un task di consegna e non un'attesa.

Il blocco 8 e' nuovo rispetto alla prima stesura e nasce dalla sessione con
l'utente: `DIMENSIONI_SENZA_GENERICO` e il corrispondente `=== 'lingua'` nel
frontend spariscono, il flag della policy passa all'admin, e al loro posto la
schermata mostra la conseguenza calcolata dai dati. Vedi
DEC-011-POLICY-LINGUA-ALL-ADMIN.

## Rischi, dichiarati invece che scoperti dopo

- **I nomi dei modelli nuovi cambiano stile** (DEC-011-IDENTITA-SENZA-NOMI-CABLATI).
  Cambia solo il **nome leggibile**: `... - IT - VI - 2026-09-23` invece di
  `... - Livello VI - Italiano - ...`. Il **codice** usa gia' i valori grezzi e
  cambia solo l'ordine, che diventa alfabetico per nome dimensione.
  La convivenza fra i due stili si chiude se i modelli esistenti vengono
  cancellati prima del deploy, come l'utente ha indicato (T004b) — subordinato
  alla verifica che non abbiano documenti generati collegati.
- **Il fallback sulla lingua diventa attivabile per configurazione, e da chi.**
  E' il rischio piu' serio del piano e va capito nella sua forma concreta: se la
  policy della lingua del bando passasse a `consente_valore_generico = true`,
  GEBAN potrebbe chiedere `lingua=EN`, non trovare il modello inglese, ricevere
  il `modello_versione_id` del modello generico e generare **un documento che
  non e' inglese credendo di aver ottenuto quello che aveva chiesto**. Non un
  errore: un documento sbagliato consegnato in silenzio — esattamente cio' che
  `DEC-001-LINGUA-IT-EN` proteggeva. Si passa da un vincolo strutturale
  (irrappresentabile) a uno configurato (deliberatamente disattivabile).
  Mitigato dall'avviso calcolato del blocco 8 e dal test dello Scenario 5, non
  eliminato. **Precisazione da riportare nei task**: portare quella policy a
  generico non rende l'inglese impossibile — i modelli `lingua = EN` restano
  creabili — rende inaffidabile la distinzione.
- **Il check `lingua IN ('IT','EN')` sparisce dal database**. Il dominio resta
  presidiato dal confronto con `foglia.lingue_possibili`, che e' la fonte
  autorevole, ma `DEC-001-LINGUA-IT-EN` perde il suo custode nello schema e va
  riaperta come la spec chiede.
- **La ricerca catalogo cambia piano di esecuzione**. Da filtro su colonna a
  JSONB con GIN. Da osservare sui volumi reali, non da ottimizzare adesso.
- **Il downgrade della `0020` perde le dimensioni diverse da lingua e livello.**
  Inevitabile e documentato nella migration.

## Complexity Tracking

Nessuna violazione della Constitution da giustificare.
