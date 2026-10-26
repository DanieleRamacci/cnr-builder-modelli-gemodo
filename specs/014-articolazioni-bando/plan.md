# Implementation Plan: Campi ripetibili e bando multiplo

**Branch**: `test` (il repository lavora su un branch unico; la feature e'
individuata da `.specify/feature.json`) | **Date**: 2026-10-26 | **Spec**:
[spec.md](./spec.md)

**Input**: Feature specification from `specs/014-articolazioni-bando/spec.md`

## Summary

Un bando puo' avere piu' sottobandi (articolazioni) con gli stessi campi.
L'integratore lo dichiara una volta sulla foglia del discovery, con un campo
`tipo: "array"` che elenca in `campi` i dati di ogni sottobando, e nei `dati`
manda un elemento `{codice, descrizione, campi}` per ogni sottobando.

In GEMODO il bando multiplo e' un **modello a se'**: il gestore lo sceglie alla
creazione, accanto al modello singolo della stessa combinazione, e lo
impagina con una **tabella** la cui riga si ripete per ogni sottobando. Il
catalogo dice quale modello e' multiplo e, senza filtro, restituisce solo i
singoli, cosi' le chiamate di oggi non cambiano.

Quattro blocchi di lavoro, in quest'ordine di dipendenza: contratto discovery
0.8.0; modello multiplo e copia dei sotto-campi; tabella vera nel formato,
nell'editor e nel PDF; validazione, generazione e catalogo.

## Technical Context

**Language/Version**: Python 3.12 (backend), TypeScript / Angular 21.2 (frontend)

**Primary Dependencies**: FastAPI, SQLAlchemy 2, Alembic, Pydantic v2, fpdf2
2.8.8; Angular, ProseMirror (model, state, view, transform, commands, keymap),
design-angular-kit / Bootstrap Italia. Nessuna dipendenza nuova
(`research.md` R11).

**API Documentation**: delta in
[`contracts/catalogo-multiplo.openapi.yaml`](./contracts/catalogo-multiplo.openapi.yaml)
e [`contracts/builder-multiplo.openapi.yaml`](./contracts/builder-multiplo.openapi.yaml),
da fondere nei contratti pubblicati (`backend/app/quality/openapi_docs.py`)
prima del codice. Discovery: `info.version` 0.8.0 nel contratto
`geban-discovery-endpoint.openapi.yaml` e schema in
[`contracts/discovery-0.8.0.schema.json`](./contracts/discovery-0.8.0.schema.json).
Formato: [`contracts/formato-tabella.md`](./contracts/formato-tabella.md).
Catalogo errori: un codice nuovo, `CODICE_ELEMENTO_DUPLICATO`
(`backend/app/common/errors.py`, `infra/openapi/errors.md`,
`docs/riferimento-api.md`).

**Storage**: PostgreSQL. Migrazione `0031`: `modello_documento.multiplo`,
`campo_modello.sotto_campi` (JSONB), indici di slot ricostruiti. Le righe
della tabella vivono nei blocchi, in `sezione_modello.contenuto` (JSONB): nessuna
colonna nuova per il formato.

**Testing**: pytest (unit, integration su Postgres reale, e2e); Vitest e
Playwright sul frontend; `test_documentazione_allineata.py` e
`npm run docs:check` per la documentazione.

**Target Platform**: servizio Linux containerizzato dietro Traefik; interfaccia
browser.

**Project Type**: applicazione web, backend + frontend nello stesso repository.

**Performance Goals**: nessuna soglia nuova. Riferimento: un bando con 10
articolazioni e una tabella di 5 colonne deve generarsi e misurarsi
nell'editor come un bando singolo di pari lunghezza.

**Constraints**: le chiamate di GEBAN di oggi (catalogo senza filtro, dati
senza articolazioni) devono dare lo stesso risultato (SC-002, SC-007); i
modelli pubblicati non cambiano (Principio IV); il formato resta chiuso
(Principio III).

**Scale/Scope**: un tipo documento reale (`BANDO_CONCORSO`), 65 foglie, una
integrazione esterna (GEBAN).

**Reuse/Public Documentation**: `docs/contratto-dati.md` (0.8.0 da "proposta"
ad "attiva", esempi singolo e multiplo), `docs/riferimento-api.md` (parametro
e campo `multiplo`, rotta nuova del builder, codice d'errore),
`docs/casi/geban.md`, `docs/integrazione-sistema-esterno.md` (scelta del
modello multiplo). Copia nell'app con `npm run docs:sync`.

## Constitution Check

*GATE: da superare prima della Fase 0. Ricontrollato dopo la Fase 1.*

| Principio | Esito | Motivo |
|---|---|---|
| I. Boundary Ownership | **Pass** | GEBAN resta padrone dei bandi e delle articolazioni; GEMODO riceve i dati per contratto e non li conserva oltre il registro gia' esistente. |
| II. Contract-First Integration | **Pass, con obbligo** | Discovery 0.8.0, catalogo e builder hanno contratti delta in `contracts/`. Obbligo: fonderli nei contratti pubblicati in Swagger prima del codice (task di Fase 2). |
| III. Configurable Document Models | **Pass** | Il bando multiplo e' configurazione: un attributo del modello e una riga di tabella marcata. Nessun bando cablato. `articolazioni` e' solo un codice convenzionale. |
| IV. Versioning, Traceability, Reproducibility | **Pass** | I sotto-campi entrano nella copia della versione (R2); i modelli esistenti diventano singoli senza modifiche; il formato e' additivo e i documenti pubblicati si rendono come prima. |
| V. Security, Audit, Controlled AI | **Pass** | Le rotte nuove usano le stesse verifiche di contesto (`verify_scrittura_su_contesto`, `DOCUMENTI_VIEWER` per il catalogo). `MODELLO_CREATO` porta `multiplo`. Nessuna funzione AI. |
| VI. Public Documentation and Reuse | **Pass, con obbligo** | Pagine `docs/` da aggiornare nello stesso lavoro, verificate da `test_documentazione_allineata.py`. Esempi con dati finti. |

**Esito**: nessuna violazione. Due obblighi, entrambi in Fase 2 dei task.

**Ricontrollo dopo la Fase 1**: confermato. Il data model non introduce stati
nuovi ne' eventi di audit nuovi; la rotta nuova del builder ricade nelle
regole del builder esistenti.

## Project Structure

### Documentation (this feature)

```text
specs/014-articolazioni-bando/
├── spec.md
├── plan.md              # questo file
├── research.md          # R1-R13
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── discovery-0.8.0.schema.json         # esistente
│   ├── discovery-bando-singolo.json         # esistente
│   ├── discovery-bando-articolato.json      # esistente
│   ├── dati-bando-singolo.json              # esistente
│   ├── dati-bando-articolato.json           # esistente
│   ├── catalogo-multiplo.openapi.yaml       # delta
│   ├── builder-multiplo.openapi.yaml        # delta
│   └── formato-tabella.md
├── checklists/requirements.md
└── tasks.md             # /speckit-tasks
```

### Source Code (repository root)

```text
backend/
├── alembic/versions/0031_modello_multiplo_sotto_campi.py   # nuova
├── app/discovery/schemas.py           # CampoDiscovery.campi, SottoCampoDiscovery, 0.8.0
├── app/documentale/schemas.py         # RigaTabella, CellaTabella, BloccoDocumento.righe
├── app/quality/document_model.py      # regole di struttura e segnaposti per righe ripetute
├── app/catalog/models.py              # multiplo, sotto_campi, indici di slot
├── app/catalog/schemas.py             # multiplo, CampoRichiestoSchema.campi
├── app/catalog/service.py             # filtro multiplo, schema items
├── app/catalog/repository.py          # filtro multiplo
├── app/catalog/api.py                 # parametro multiplo
├── app/builder/schemas.py             # CreaModelloRequest.multiplo, risposte
├── app/builder/service.py             # crea_modello, crea_versione, crea_multiplo, _valida_documento, anteprima
├── app/builder/repository.py          # slot con multiplo, clona_campi, composizione
├── app/builder/api.py                 # rotta /multiplo
├── app/validation/service.py          # elementi dei campi ripetibili
├── app/generazione/renderer.py        # espansione righe, tabella a griglia
└── app/common/errors.py               # CODICE_ELEMENTO_DUPLICATO

frontend/src/features/builder/
├── modello-crea.component.ts          # scelta Singolo/Multiplo, campi della versione
├── modello-anteprima.component.ts     # gruppo "Bando multiplo", avvisi FR-016h, crea multiplo dal singolo
├── documento-editor.ts                # nodi tabella/riga/cella, comandi, conversione
└── frammenti.ts                       # segnaposti nelle celle

docs/  contratto-dati.md, riferimento-api.md, integrazione-sistema-esterno.md, casi/geban.md
```

**Structure Decision**: applicazione web esistente; nessun modulo nuovo. Il
lavoro tocca i moduli gia' proprietari di ogni concetto.

## Ordine di dipendenza

1. **Contratti pubblicati** (delta fusi, errore nuovo nel catalogo): prima di
   tutto, Principio II.
2. **Discovery 0.8.0** (US1): indipendente; sblocca tutto il resto.
3. **Migrazione e modello multiplo** (US2, parte dati): `multiplo`, slot,
   `sotto_campi`, `crea_versione`.
4. **Formato tabella** (backend): schema, regole di struttura, resa a griglia
   per le righe fisse. Serve a 5 e 6.
5. **Editor** (US2, parte UI): tabella, riga ripetuta, gruppo "Bando multiplo",
   scelta alla creazione.
6. **Validazione, generazione, anteprima** (US3).
7. **Catalogo** (`multiplo`, `campi-richiesti`).
8. **Documentazione** e collaudo end-to-end con il bando 367.501.

US1 e la parte backend di 3-4 possono procedere in parallelo dopo il passo 1.

## Complexity Tracking

| Scelta | Perche' serve | Alternativa piu' semplice scartata |
|---|---|---|
| `multiplo` nello slot di categorizzazione (indici ricostruiti) | Singolo e multiplo della stessa combinazione devono coesistere pubblicati (FR-009f) | Usare la variante: mescola un asse deciso dal gestore con la forma del contratto dati (R3) |
| Tre nodi ProseMirror propri per la tabella | La tabella deve essere modificabile nell'editor, fedele al PDF | `prosemirror-tables`: porta funzioni che il formato non rappresenta (R11) |

## Stato aperto che i task devono affrontare

- Verifica di R7: enfasi per frammento nelle celle con `FPDF.table()` 2.8.8.
- Allineare la spec: base 0 dell'indice (R9) e il testo dell'Independent Test
  della US2 (modello multiplo).
