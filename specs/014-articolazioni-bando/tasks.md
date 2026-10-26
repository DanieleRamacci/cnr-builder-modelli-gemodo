---

description: "Task list per 014 - Campi ripetibili e bando multiplo"
---

# Tasks: Campi ripetibili e bando multiplo

**Input**: documenti di progetto in `/specs/014-articolazioni-bando/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md),
[research.md](./research.md), [data-model.md](./data-model.md),
[contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Tests**: inclusi. Il progetto non ammette test che simulano la logica di
dominio: le verifiche girano contro Postgres reale, il renderer reale e
l'editor reale.

**Organization**: raggruppati per user story, cosi' che ciascuna sia
implementabile e collaudabile da sola.

## Format: `[ID] [P?] [Story] Descrizione`

- **[P]**: parallelizzabile (file diversi, nessuna dipendenza)
- **[Story]**: a quale user story appartiene

## Path Conventions

Applicazione web: `backend/app/`, `frontend/src/`, come da
[plan.md](./plan.md#source-code-repository-root).

---

## Phase 1: Setup (contratti prima del codice, Principio II)

- [x] T001 [P] Fondere [contracts/catalogo-multiplo.openapi.yaml](./contracts/catalogo-multiplo.openapi.yaml)
      in `specs/001-catalogo-contratto-geban/contracts/geban-catalog-api.openapi.yaml`
      (parametro `multiplo`, campo `multiplo`, `CampoRichiesto.campi`, esempio multiplo)
      *Fatto 2026-10-26: contratto 0.10.0, marcato "in sviluppo" nella descrizione.*
- [x] T002 [P] Fondere [contracts/builder-multiplo.openapi.yaml](./contracts/builder-multiplo.openapi.yaml)
      in `specs/002-builder-modelli/contracts/builder-modelli-api.openapi.yaml`
      (`multiplo` in creazione e risposte, rotta `POST /modelli/{modelloId}/multiplo`,
      `sotto_campi`, regola FR-009b su `/versioni`)
      *Fatto 2026-10-26 (0.15.0), tranne la rotta `/multiplo`:
      `test_builder_modelli_contract.py` ammette solo rotte che il router ha
      gia', quindi entra nel contratto con T024. Tipi del frontend rigenerati.*
- [x] T003 [P] Portare `info.version` a 0.8.0 in
      `specs/010-configurazione-cataloghi-integrazioni/contracts/geban-discovery-endpoint.openapi.yaml`,
      con `campi` sul campo, `SottoCampo` e la regola delle chiavi `_` (allineato a
      [contracts/discovery-0.8.0.schema.json](./contracts/discovery-0.8.0.schema.json))
      *Fatto 2026-10-26: esempio con `articolazioni`, valido per lo schema
      0.8.0 e accettato dal codice 0.7.0. Fino a T012 il contratto dice 0.8.0
      e `VERSIONE_CONTRATTO_DISCOVERY` 0.7.0: senza rischi per GEBAN, perche'
      un albero conforme alla 0.8.0 e' accettato anche dal codice 0.7.0. I tre
      rami "non sviluppati" di `ALTRO_TIPO_DOCUMENTO_ESEMPIO` non sono validi
      per il codice (nodo senza figli ne' campi): difetto preesistente, non
      toccato.*
- [x] T004 [P] Aggiungere `CODICE_ELEMENTO_DUPLICATO` a `backend/app/common/errors.py`,
      `infra/openapi/errors.md` e al catalogo errori di `docs/riferimento-api.md`
      *Fatto 2026-10-26, con `npm run docs:sync`.*

**Checkpoint**: i contratti in Swagger mostrano la forma nuova; nessun codice ancora.

---

## Phase 2: Foundational (prerequisiti di tutte le storie)

- [x] T005 Migrazione `backend/alembic/versions/0031_modello_multiplo_sotto_campi.py`:
      `modello_documento.multiplo` boolean not null default false;
      `campo_modello.sotto_campi` JSONB nullable; ricostruire
      `uq_modello_slot_variante` e `uq_modello_slot_nota` con `multiplo`
      (data-model §2). Downgrade simmetrico.
- [x] T006 Mappare le colonne in `backend/app/catalog/models.py`
      (`ModelloDocumento.multiplo`, `ModelloCampoRichiesto.sotto_campi`, indici).
- [x] T007 [P] Test di migrazione su Postgres reale in `backend/tests/integration/`:
      modelli esistenti diventano `multiplo = false`; singolo e multiplo STANDARD
      dello stesso slot coesistono; due multipli STANDARD dello stesso slot no.
- [x] T008 [P] `RigaTabella`, `CellaTabella` e `BloccoDocumento.righe` in
      `backend/app/documentale/schemas.py` (research R6). Test: un documento
      senza `righe` resta valido e identico.
- [x] T009 `clona_campi` copia `sotto_campi` (`backend/app/builder/repository.py:592`).

**Checkpoint**: schema e formato pronti; nessun comportamento visibile cambiato.

---

## Phase 3: User Story 1 - Dichiarare un campo ripetibile nel discovery (P1) 🎯 MVP

**Goal**: GEMODO legge e valida il contratto 0.8.0.

**Independent Test**: una foglia con `articolazioni` (`tipo: "array"` + `campi`)
supera il test di connessione e i sotto-campi sono conservati; una foglia
senza campi ripetibili si legge come oggi.

### Tests

- [x] T010 [P] [US1] Test in `backend/tests/discovery/`: albero con
      `articolazioni` -> `CONFORME`, sotto-campi conservati; albero GEBAN 0.7.0
      reale salvato come fixture -> `CONFORME` invariato (SC-001); campo
      `array` senza `campi` -> `CONFORME` e, in validazione, una lista
      semplice di valori resta accettata come oggi (FR-005).
- [x] T011 [P] [US1] Test dei rifiuti con percorso: `campi` su tipo non
      `array`; `campi` vuota; sotto-campo `array`/`object`; codici duplicati
      in `campi`; chiave sconosciuta nel campo; chiave `_comment` ammessa.

### Implementation

- [x] T012 [US1] `CampoDiscovery.campi`, `SottoCampoDiscovery`, `extra="forbid"`
      con scarto delle chiavi `_` in `backend/app/discovery/schemas.py`;
      `VERSIONE_CONTRATTO_DISCOVERY = "0.8.0"` (research R1). Nello stesso
      task: versione attiva 0.8.0 in `docs/contratto-dati.md` (e nelle pagine
      che la citano), poi `test_documentazione_allineata.py` e
      `npm run docs:sync && npm run docs:check` verdi. Il codice prevale e la
      pagina si corregge nello stesso lavoro (`.claude/CLAUDE.md`).
- [x] T013 [US1] Verificare che i dettagli di `_dettagli_validazione`
      (`backend/app/discovery/adapter_http.py:32`) riportino nome della chiave e
      percorso per i casi di T011; correggere dove no.
- [x] T014 [US1] *(anche: il modulo ora conserva i sotto-campi al salvataggio, che prima avrebbe perso in silenzio)* Struttura definita dall'amministratore: test che `CampoInput`
      accetti e validi `campi` con le stesse regole (FR-006), e che
      l'esportazione della struttura (`esporta`, `documentazione` in
      `backend/app/configurazione/service.py`) riporti i `campi`; la schermata
      `tipo-documento-struttura.component.ts` mostra i sotto-campi in sola
      lettura (research R12).

**Checkpoint**: US1 collaudabile da sola (quickstart §1).

---

## Phase 4: User Story 2 - Modello multiplo e tabella nel builder (P1)

**Goal**: il gestore crea un modello multiplo, vede le etichette del
sottobando in un gruppo proprio e impagina i sottobandi con una riga di
tabella ripetuta.

**Independent Test**: quickstart §2.

### Tests

- [x] T015 [P] [US2] Test API in `backend/tests/builder/`: creazione con
      `multiplo: true` su foglia con campi ripetibili (ok) e senza
      (`CONTESTO_NON_VALIDO`); codice e nome con `MULTIPLO`; pubblicare il
      multiplo non archivia il singolo (FR-009f); nessuna rotta permette di
      cambiare `multiplo` dopo la creazione (un campo `multiplo` nelle
      richieste di modifica e' rifiutato) e varianti ed edizioni derivate lo
      ereditano.
- [x] T016 [P] [US2] Test di `crea_versione`: singolo con campo ripetibile ->
      `CAMPO_NON_AMMESSO`; multiplo senza campo ripetibile ->
      `CAMPO_NON_AMMESSO`; multiplo salva `sotto_campi` e `obbligatorio = true`
      sul campo ripetibile anche se la foglia dice `false` (FR-016c).
- [x] T017 [P] [US2] Test delle regole di pubblicazione (data-model §3), tutte
      le violazioni raccolte insieme: multiplo senza riga ripetuta (FR-009d);
      segnaposto di elemento fuori riga; principale dentro riga (FR-016b);
      `{{articolazioni}}` da solo (FR-015); due righe ripetute nella stessa
      tabella (FR-016h); `ripeti_per` su un singolo; celle != colonne.
- [x] T018 [P] [US2] Test di `POST /modelli/{id}/multiplo`: copia le sezioni
      dell'ultima versione del singolo; partenza gia' multipla ->
      `CONTESTO_NON_VALIDO`; multiplo gia' esistente ->
      `MODELLO_VARIANTE_DUPLICATA` con il modello che occupa lo slot.
- [x] T019 [P] [US2] Test del renderer: tabella con `righe` resa a griglia,
      intestazione ripetuta a cambio pagina; tabella senza `righe` resa come
      oggi (verifica sul testo estratto dal PDF con pypdf).

### Implementation - backend

- [x] T020 [US2] `CreaModelloRequest.multiplo` e risposte del modello in
      `backend/app/builder/schemas.py` e `backend/app/builder/api.py`.
- [x] T021 [US2] `crea_modello`: rifiuto di `multiplo` su foglia senza campi
      ripetibili; `multiplo` nello slot (`_variante_per_slot`,
      `modelli_sullo_slot`), in `_identita_modello` e nell'audit
      `MODELLO_CREATO` (`backend/app/builder/service.py`, `repository.py`).
- [x] T022 [US2] `get_versione_pubblicata_corrente` filtra per `multiplo`
      (`backend/app/builder/repository.py:618`); varianti ed edizioni derivate
      ereditano `multiplo` (`crea_variante`, `crea_edizione_derivata`).
- [x] T023 [US2] `crea_versione`: regola FR-009b e copia di `sotto_campi`, con
      `obbligatorio = true` per il multiplo (research R4).
- [x] T024 [US2] Rotta `POST /api/v1/builder/modelli/{modelloId}/multiplo` e
      servizio `crea_multiplo` (FR-009e), con audit. Nello stesso task: la
      rotta nel contratto del builder (da [contracts/builder-multiplo.openapi.yaml](./contracts/builder-multiplo.openapi.yaml)),
      nell'elenco di `test_builder_modelli_contract.py` e in
      `docs/riferimento-api.md`.
- [x] T025 [US2] Regole di struttura e segnaposti per le righe ripetute in
      `backend/app/quality/document_model.py` e cablaggio in
      `_valida_documento` (`backend/app/builder/service.py:879`), con insieme
      ammesso a due livelli (research R5). `placeholder_usati` include le celle
      (`backend/app/builder/repository.py`, composizione).
- [x] T026 [US2] *(R7 verificata: una cella ha un'enfasi sola, quella comune a tutti i suoi frammenti)* Resa a griglia della `TABELLA` con `FPDF.table()` in
      `backend/app/generazione/renderer.py:434`; verificare l'enfasi per
      frammento nelle celle (research R7) e annotare l'esito in research.md.
- [x] T027 [US2] Anteprima e impaginazione: due elementi d'esempio
      «Etichetta (1)», «Etichetta (2)» per le righe ripetute (FR-016f,
      research R8), in `anteprima` (`backend/app/builder/service.py:946`).
- [x] T028 [US2] Dettaglio modello: `multiplo` e `sotto_campi` nelle risposte
      (`backend/app/builder/api.py:124`); rigenerare i tipi del frontend.

### Implementation - frontend

- [x] T029 [US2] `modello-crea.component.ts`: scelta "Bando singolo" / "Bando
      multiplo" solo se la foglia ha campi ripetibili (FR-009a); `createVersion`
      manda i campi coerenti con la scelta (research R4).
- [x] T030 [US2] Pannello segnaposti in `modello-anteprima.component.ts`:
      gruppo "Dati del bando" e gruppo collassabile "Bando multiplo -
      `etichetta` del campo" con i segnaposti `{{<campo>.codice}}`,
      `{{<campo>.descrizione}}`, `{{<campo>.campi.<sotto>}}` (FR-008, FR-009c);
      nel singolo il gruppo non c'e'.
- [x] T031 [US2] Nodi `tabella`, `riga`, `cella` in `documento-editor.ts`
      (research R11): conversione blocchi <-> documento, rendering nel foglio
      A4, comandi inserisci tabella, aggiungi/togli riga e colonna,
      intestazione modificabile.
- [x] T032 [US2] Comando "ripeti per ogni ..." sulla riga, con scelta del campo
      ripetibile della versione; la riga ripetuta e' marcata in modo visibile.
      Disponibile solo nei modelli multipli.
- [x] T033 [US2] Controlli prima della pubblicazione in
      `modello-anteprima.component.ts` (`blocchiDocumento`), allineati a T025;
      avvisi non bloccanti di FR-016h (stesso campo in piu' tabelle, con dove;
      stesso segnaposto due volte nella riga).
- [x] T034 [US2] Azione "Crea bando multiplo" dal modello singolo (T024), solo
      se la foglia ha campi ripetibili e il multiplo non esiste ancora.
- [x] T035 [P] [US2] Test Vitest per T029-T033 (scelta alla creazione, gruppi,
      conversione tabella <-> blocchi, riga ripetuta, avvisi).
- [x] T036 [US2] Test Playwright su stack reale: quickstart §2 dal punto 1 al 7.
      *Fatto 2026-10-26: `frontend/e2e/bando-multiplo.spec.ts`, passato su stack
      reale (creazione multiplo, tabella con riga ripetuta e totale,
      pubblicazione, catalogo con `multiplo=true`, PDF del 367.501). Il
      discovery-mock ha una foglia `DEMO - Collaboratore Tecnico E.R.` con
      `articolazioni`. Gli altri e2e passano, tranne il controllo finale di
      `builder-lifecycle.spec.ts` (pagina Registro attivita' piu' larga di 390
      px): fallisce identico anche senza le modifiche della 014, difetto
      preesistente della 013.*

**Checkpoint**: US2 collaudabile (quickstart §2); un modello singolo esistente
si apre, si modifica e si pubblica come prima.

---

## Phase 5: User Story 3 - Validare, generare e trovare il modello multiplo (P2)

**Goal**: una richiesta con le articolazioni produce un solo PDF con la
tabella espansa; errori con il percorso dell'elemento; il catalogo distingue
singolo e multiplo.

**Independent Test**: quickstart §3 e §4.

### Tests

- [x] T037 [P] [US3] Test di validazione su Postgres reale in
      `backend/tests/validation/`: tutti i casi di data-model §4, con i
      percorsi esatti e l'indice da 0; errori di piu' elementi raccolti insieme;
      `articolazioni` a un singolo -> `CAMPO_NON_AMMESSO` (FR-016g); modello
      multiplo pubblicato, poi la foglia aggiunge un sotto-campo obbligatorio:
      la validazione usa ancora i sotto-campi salvati nella versione (edge case
      sullo snapshot).
- [x] T038 [P] [US3] Test di generazione: 367.501 con tre tematiche -> un PDF,
      tre righe nell'ordine dei dati, Totale 10 (SC-003, SC-004); sotto-campo
      facoltativo assente -> cella vuota (FR-016d); nessuna lista grezza nel
      testo (FR-015).
- [x] T039 [P] [US3] Test del catalogo: senza `multiplo` stessi risultati di
      prima (SC-007) e mai modelli multipli; `multiplo=true` solo multipli;
      `campi-richiesti` con `campi` e `items` (FR-013), schema valido contro un
      payload d'esempio.

### Implementation

- [x] T040 [US3] Validazione degli elementi in
      `backend/app/validation/service.py` (research R9).
- [x] T041 [US3] Espansione delle righe ripetute in `sostituisci_placeholder`
      (`backend/app/generazione/renderer.py:499`), research R8.
- [x] T042 [US3] Catalogo: parametro `multiplo` (`backend/app/catalog/api.py`),
      filtro in `list_published_model_versions`, `multiplo` in
      `ModelloCatalogoSchema`, `campi` in `CampoRichiestoSchema`, `items` in
      `_json_schema_for_field` (`backend/app/catalog/service.py:301`). Le
      edizioni derivate annidate (es. EN) seguono il filtro del modello di
      origine (`_raggruppa_edizioni`).

**Checkpoint**: quickstart §3 e §4 passano su stack reale.

---

## Phase 6: Polish & documentazione

- [x] T043 [P] `docs/contratto-dati.md`: grammatica, regole di conformita',
      validazione degli elementi, esempi singolo e multiplo (FR-017, SC-006);
      togliere le marcature "proposta" (la versione attiva e' gia' stata
      aggiornata in T012). Una riga di glossario: "campo ripetibile" e'
      la regola generale, `articolazioni` il codice usato per i bandi,
      "sottobando" o "tematica" l'elemento, l'etichetta e' quella del
      discovery.
- [x] T044 [P] `docs/riferimento-api.md` (parametro e campo `multiplo`, rotta
      `/multiplo`, errore nuovo), `docs/integrazione-sistema-esterno.md` (come
      scegliere il modello multiplo), `docs/casi/geban.md` (evoluzione: da
      proposta ad attiva), `docs/architettura.md` se cita la 0.7.0.
- [x] T045 Togliere le note "in sviluppo" della 014 dai contratti (catalogo
      0.10.0, builder 0.15.0) e da `docs/riferimento-api.md`
      (`CODICE_ELEMENTO_DUPLICATO`). Aggiornare `test_documentazione_allineata.py` dove serve; eseguirlo;
      `cd frontend && npm run docs:sync && npm run docs:check`.
- [x] T046 *(2026-10-26: backend 619 passati con Postgres reale, frontend 238, build ok)* Suite complete backend e frontend, build di produzione; quickstart
      §5 (un modello singolo esistente genera lo stesso PDF di prima).
- [ ] T047 Nota di deploy: la migrazione 0031 parte all'avvio del backend;
      annunciarla prima del redeploy. Testo per GEBAN: aggiungere
      `articolazioni` alle foglie, cercare con `multiplo=true` per i bandi con
      tematiche, mandare gli elementi in `dati`.
- [ ] T048 Hook `after_implement`: `speckit.adev-quality.review` (obbligatorio).

---

## Dependencies & Execution Order

- **Phase 1** -> tutto il resto (Principio II).
- **Phase 2** dopo Phase 1; blocca US2 e US3.
- **US1** (Phase 3) dipende solo da Phase 1: puo' partire subito dopo T003.
- **US2** dipende da Phase 2 e, per leggere i sotto-campi dal vivo, da T012.
- **US3** dipende da US2 per i modelli multipli pubblicati (T020-T026); T040 e
  T042 possono iniziare dopo T023.
- **Phase 6** alla fine; T043 puo' iniziare dopo US1.

### Dentro le storie

Test prima dell'implementazione, e devono fallire prima. Backend prima del
frontend nella US2 (T020-T028 prima di T029-T036).

## Parallel Example: dopo Phase 2

```text
T010, T011 (test US1)            | T015-T019 (test US2)
T012-T014 (impl US1)             | T020-T024 (impl US2, backend dati)
```

## Implementation Strategy

1. **MVP = US1**: GEBAN puo' gia' pubblicare `articolazioni` e GEMODO le
   riconosce e valida la forma.
2. **US2**: il gestore costruisce e pubblica il modello multiplo.
3. **US3**: GEBAN genera i bandi multipli e li trova nel catalogo.
4. Rilascio in test dopo US3, con il testo per GEBAN (T047).
