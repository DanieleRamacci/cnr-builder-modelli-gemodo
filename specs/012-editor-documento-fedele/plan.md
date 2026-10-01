# Implementation Plan: Editor documentale fedele al provvedimento reale

**Branch**: `test` (il repository lavora su un branch unico; la feature e'
individuata da `.specify/feature.json`) | **Date**: 2026-09-29 | **Spec**:
[spec.md](./spec.md)

**Input**: Feature specification from `specs/012-editor-documento-fedele/spec.md`

## Summary

Il formato documentale sa rappresentare solo paragrafi di testo semplice, e il
bando reale non e' fatto cosi'. Questo incremento cambia **la forma del
paragrafo**: da una stringa a una sequenza di frammenti, ciascuno con la propria
enfasi. Da li' discende tutto il resto - elenchi annidati con numerazione
calcolata in resa, allineamento esplicito compreso il giustificato, cornice di
pagina sul tipo documento, collegamenti - piu' un'anteprima PDF della bozza che
esce dallo **stesso** renderer del documento finale, perche' e' l'unico modo di
impedire che editor e PDF tornino a divergere.

Due difetti gia' presenti si chiudono qui, non come rifinitura ma perche' la
feature li attraversa: il renderer ignora `stile`, quindi l'editor mostra H1/H2
e il PDF produce un paragrafo qualunque; e il renderer usa un font che non
conosce le virgolette curve, quindi oggi un testo incollato da Word non produce
un documento sbagliato - **non produce alcun documento** (`research.md` R1).

## Technical Context

**Language/Version**: Python 3.12 (backend), TypeScript / Angular 21.2 (frontend)

**Primary Dependencies**: FastAPI, SQLAlchemy 2, Alembic, Pydantic v2, fpdf2
2.8.8; Angular, design-angular-kit / Bootstrap Italia

**API Documentation**: contratto nuovo in
[`contracts/anteprima-api.openapi.yaml`](./contracts/anteprima-api.openapi.yaml),
da fondere nel contratto del builder
(`specs/002-builder-modelli/contracts/builder-modelli-api.openapi.yaml`) e
registrare in `PUBLISHED_CONTRACTS` (`backend/app/quality/openapi_docs.py`)
prima dell'implementazione. Forma dei blocchi in
[`contracts/formato-documentale.md`](./contracts/formato-documentale.md).
Catalogo errori: nessun codice nuovo, si riusa
`MODELLO_DOCUMENTALE_NON_VALIDO` estendendone la condizione in
`infra/openapi/errors.md`.

**Storage**: PostgreSQL. I blocchi vivono in `sezione_modello.contenuto`
(JSONB, `backend/app/catalog/models.py:191`); la cornice di pagina aggiunge una
colonna JSONB su `tipo_documento`.

**Testing**: pytest (unit / integration su Postgres via Testcontainers / e2e);
Vitest e Playwright sul frontend

**Target Platform**: servizio Linux containerizzato dietro Traefik; interfaccia
browser

**Project Type**: applicazione web, backend + frontend nello stesso repository

**Performance Goals**: nessuna soglia nuova. Il riferimento e' un documento di
15 pagine con ~40 paragrafi normativi e ~20 articoli, che la spec dichiara
essere la dimensione **normale**, non il caso limite: l'anteprima deve restare
un'azione interattiva, non un lavoro in coda.

**Constraints**: il formato resta chiuso (nessun HTML, CSS o script, Principio
III); i modelli gia' pubblicati devono continuare a generare lo stesso documento
visibile (Principio IV, FR-013); l'anteprima non puo' registrare documenti ne'
consumare l'idempotenza (FR-010).

**Scale/Scope**: un tipo documento reale in produzione (`BANDO_CONCORSO`), un
solo client di scrittura delle sezioni (l'editor del builder).

**Reuse/Public Documentation**: `docs/api-per-geban.md` non cambia - GEBAN non
scrive sezioni e non chiede anteprime. Vanno aggiornati il catalogo errori,
la documentazione del formato documentale e le note di licenza per il font
incorporato (OFL).

## Constitution Check

*GATE: da superare prima della Fase 0. Ricontrollato dopo la Fase 1.*

| Principio | Esito | Motivo |
|---|---|---|
| I. Boundary Ownership | **Pass** | Il formato documentale e' interamente di GEMODO. Nulla di questa feature legge o scrive dati GEBAN: l'enfasi, gli elenchi e la cornice descrivono il documento, non l'anagrafica. |
| II. Contract-First Integration | **Pass, con obbligo** | La rotta di anteprima e la forma nuova dei blocchi sono contratti, ed esistono come artefatti **prima** del codice. L'obbligo: fonderli nel contratto del builder e pubblicarli in Swagger prima di implementare, non dopo. |
| III. Configurable Document Models | **Pass** | Nessun documento viene cablato nel codice: si estende il vocabolario (un tipo di blocco, gli attributi di enfasi e allineamento), e il bando resta interamente dato. Il divieto di HTML/CSS non viene toccato - anzi, R6 mostra che oggi non e' applicato al testo e questa feature lo applica per la prima volta. |
| IV. Versioning, Traceability, Reproducibility | **Pass con deviazione dichiarata** | Vedi Complexity Tracking: la migrazione riscrive la codifica di sezioni gia' pubblicate. L'anteprima e' conforme per costruzione (percorso separato dallo storage, R4). |
| V. Security, Audit, Controlled AI | **Pass** | L'anteprima e' autorizzata come una scrittura sul contesto del tipo documento (`verify_scrittura_su_contesto`), non come una generazione. Nessuna funzione AI coinvolta. Da decidere in fase task: se registrare un evento di audit per l'anteprima - non e' una generazione, ma e' un'azione su un modello. |
| VI. Public Documentation and Reuse | **Pass, con obbligo** | Il font incorporato porta una licenza (OFL) che va inclusa con i file. Il formato documentale va documentato nella forma nuova, altrimenti un riusante legge una struttura che non esiste piu'. |

**Esito**: nessuna violazione bloccante. Due obblighi (contratto pubblicato
prima del codice; licenza del font) e una deviazione dichiarata.

## Project Structure

### Documentation (this feature)

```text
specs/012-editor-documento-fedele/
├── plan.md                              # questo file
├── spec.md
├── research.md                          # Fase 0 - R1..R8
├── data-model.md                        # Fase 1
├── quickstart.md                        # Fase 1 - come si prova ogni SC
├── contracts/
│   ├── anteprima-api.openapi.yaml       # rotta nuova
│   └── formato-documentale.md           # forma dei blocchi
└── tasks.md                             # Fase 2 - NON prodotto da speckit-plan
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── documentale/
│   │   └── schemas.py            # FrammentoTesto, ElementoElenco, CornicePagina,
│   │                             # AllineamentoTesto; BloccoDocumento senza `contenuto`
│   ├── generazione/
│   │   ├── renderer.py           # frammenti, elenchi numerati in resa, giustificato,
│   │   │                         # `stile` finalmente letto, font Titillium
│   │   ├── fonts/                # NUOVO: Titillium Web .ttf + OFL.txt
│   │   └── service.py            # invariato nella logica: cambia cio' che passa al renderer
│   ├── builder/
│   │   ├── api.py                # NUOVO: POST .../versioni/{id}/anteprima
│   │   └── service.py            # composizione anteprima; nessun accesso allo storage
│   ├── quality/
│   │   └── document_model.py     # validazione: markup nel testo, livello, collegamenti
│   └── catalog/
│       └── models.py             # tipo_documento.cornice_pagina
├── migrations/versions/          # NUOVO: contenuto -> frammenti; colonna cornice
└── tests/                        # unit renderer, integration sezioni+anteprima, e2e SC-004

frontend/src/features/
├── builder/
│   └── modello-anteprima.component.ts   # B/I/U abilitati, elenchi, allineamento,
│                                        # anteprima che scarica il PDF vero
└── configurazione/
    └── tipo-documento-struttura.component.ts  # cornice di pagina
```

**Structure Decision**: struttura esistente, nessun modulo nuovo. Il punto di
gravita' e' `backend/app/documentale/schemas.py`, che e' gia' la sede del
formato e da cui `app/quality/schemas.py` importa - quindi una definizione
sola, non due che possono divergere. L'unica directory nuova e'
`backend/app/generazione/fonts/`.

## Ordine di dipendenza

Non e' l'ordine di priorita' delle user story: US1 e US2 sono entrambe P1, ma
non sono indipendenti in implementazione.

1. **Formato + migrazione + validazione** (fondamenta). Senza, nessuna storia
   ha dove salvare. Include il font Unicode, perche' senza quello il renderer
   nuovo fallisce sugli stessi caratteri di oggi.
2. **US1 - enfasi** (P1). Blocca sull'esito di R8 (incolla da Word) per la sola
   parte di scope.
3. **US2 - articolato** (P1). Dipende da 1, non da US1.
4. **US4 - anteprima** (P2). Va presto nonostante la priorita': e' cio' che
   rende verificabili US1 e US2, e l'alternativa e' pubblicare per vedere.
5. **US3 - cornice** (P2). Tocca il tipo documento, non l'editor: percorso
   indipendente, parallelizzabile.
6. **US5 - collegamenti** (P3).

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| La migrazione riscrive `sezione_modello.contenuto` di versioni **gia' pubblicate**, mentre il Principio III vuole che il contenuto pubblicato si versioni invece di essere sovrascritto | FR-016 impone una sola forma nel formato. Lasciare le versioni pubblicate nella forma vecchia significherebbe due strade di resa permanenti - esattamente la divergenza che questa spec chiude | Accettare entrambe le forme: scartata dall'utente nella clarification, e ricreerebbe il difetto H1/H2 su scala maggiore. Versionare il formato blocco per blocco: costo sproporzionato per una conversione senza perdita |
| | **Perche' e' accettabile**: cambia la codifica, non il contenuto. Un frammento unico senza enfasi e' la stessa stringa di prima | **Come si dimostra**, invece di affermarlo: SC-004 confronta il testo estratto dai PDF prima e dopo la migrazione. Una differenza ferma la migrazione |

## Stato aperto che i task devono affrontare

Una cosa sola resta da decidere, ed e' meglio dirla qui che scoprirla durante
l'implementazione:

- **Audit dell'anteprima** (Principio V): l'anteprima non e' una generazione e
  non compare nell'elenco di eventi della costituzione. Se registrarla o no e'
  una scelta, non un'omissione.
