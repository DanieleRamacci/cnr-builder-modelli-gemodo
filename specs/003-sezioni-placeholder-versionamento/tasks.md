# Tasks: Sezioni Placeholder E Versionamento

> ## ⚠ RICONCILIAZIONE 2026-09-22 — QUESTO ELENCO E' SUPERATO
>
> **Non eseguire i task sottostanti senza prima ripianificare.** Le caselle
> non spuntate qui sotto **non** misurano lavoro arretrato: misurano la
> distanza fra un piano scritto all'inizio e un'implementazione che ha preso
> un'altra strada. Verifica condotta il 2026-09-22 confrontando ogni percorso
> citato nei task con il codice su disco.
>
> **Esito della verifica: dei 54 percorsi citati, 51 non esistono.**
>
> - L'intera gerarchia pianificata `backend/app/builder/sections/`,
>   `placeholders/`, `complex_fields/`, `document_model/`, `service/`, `api/`
>   non e' mai stata creata. Il modulo `builder` reale e' piatto:
>   `api.py`, `service.py`, `repository.py`, `schemas.py`.
> - Le migration pianificate `0006_sections_document_model` e
>   `0007_complex_field_schema` non esistono; quei due numeri sono occupati da
>   `0006_riallinea_modelli_demo_classificazione` e
>   `0007_riallinea_nomenclatura_geban`, lavoro di tutt'altra natura.
> - Nessuno dei 19 file di test pianificati esiste.
>
> **Stato reale per user story:**
>
> | User story | Stato | Prova |
> | --- | --- | --- |
> | US1 — sezioni della versione modello | **NON IMPLEMENTATA** | La tabella `sezione_modello` esiste da `0001_initial_schema`, ma `SezioneModello` non e' referenziata da alcun file in `backend/app`: e' una tabella morta. Nessuna API sezioni. |
> | US2 — placeholder e campi complessi | **PARZIALE, ALTROVE** | La validazione placeholder vive in `backend/app/generazione/` (spec `004`) e in `backend/app/quality/`. Non esiste come funzione del builder. |
> | US3 — modello documentale controllato `GEMODO_DOCUMENT_V1` | **FATTA, DI PROPRIETA' DI `009`** | Implementata in `backend/app/quality/document_model.py`, che dichiara esplicitamente come propri requisiti `spec 009, FR-036..FR-038`. Non passera' mai da `builder/document_model/`. |
>
> **DECISO il 2026-09-22 con l'utente** (`DEC-003-CORPO-DOCUMENTO-RIPIANIFICATO`):
> `003` **rientra in scope** ed e' stata ripianificata. Il piano che segue
> sostituisce i 69 task originali.
>
> La ragione della decisione, in una frase: senza `003` GEMODO non produce un
> bando ma una scheda dati. Il PDF odierno e' un elenco etichetta/valore
> (`generazione/service.py:57-63`) marcato `DOCUMENTO DI TEST - NON UFFICIALE`;
> un bando reale e' testo con segnaposto dentro i paragrafi, e quel testo oggi
> non ha dove vivere.
>
> La ripianificazione ha trovato una situazione **migliore** del previsto: la
> tabella `sezione_modello` ha gia' la forma giusta, i Pydantic del documento
> controllato esistono, e `validate_document_model` accetta gia'
> `placeholder_contratto_dati` ma non ha chiamanti. Il lavoro e' **cablare
> pezzi esistenti**, non costruirli. Da 69 task a 24, di cui 8 gia' chiusi
> dalla ricognizione.
>
> Le tre domande aperte sono risolte cosi': US1 serve e usa la tabella
> esistente (non si elimina nulla); US3 resta di `009` e si usa invece di
> riscriverla; US2 vive qui come cancello di pubblicazione, mentre la
> sostituzione dei valori a runtime resta di `004`.

**Input**: Design documents from `specs/003-sezioni-placeholder-versionamento/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/sezioni-placeholder-api.openapi.yaml`, `quickstart.md`

**Tests**: Include unit, integration and contract tests because section immutability, controlled document model validation, placeholder validation and complex-field schemas directly affect publication correctness.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to
- Include exact file paths in descriptions

## Phase 1: Ricognizione — cosa esiste gia' (nessun lavoro, solo vincoli)

Questa fase non produce codice: fissa i fatti verificati il 2026-09-22, perche'
il piano precedente e' fallito proprio per aver assunto invece di verificare.

- [x] R01 La tabella `sezione_modello` esiste da `0001_initial_schema` ed e'
      **gia' della forma giusta**: `modello_versione_id` (FK CASCADE su
      `modello_versione`), `codice`, `ordine`, `contenuto` JSONB, vincolo unico
      `(modello_versione_id, codice)`. Va **usata**, non eliminata ne' ricreata
- [x] R02 `ModelloDocumentaleControllato` e `BloccoDocumento` esistono in
      `backend/app/quality/schemas.py:325-380`, con `modello_versione_id`,
      `blocchi`, `placeholder_usati`, `asset`, `stili_ammessi` e i flag
      `contiene_html_libero`/`css`/`script`
- [x] R03 `validate_document_model` in `backend/app/quality/document_model.py:69`
      accetta gia' il parametro `placeholder_contratto_dati: set[str] | None`:
      e' esattamente FR-005. Ha **zero chiamanti**: va cablato, non scritto
- [x] R04 Il vocabolario dei blocchi (`LOGO`, `INTESTAZIONE`, `TITOLO`,
      `PARAGRAFO`, `TABELLA`, `COLONNE`, `FIRMA`, `FOOTER`,
      `INTERRUZIONE_PAGINA`) e la grammatica di posizionamento
      (`POSIZIONI_AMMESSE`) sono implementati e testati: FR-009 e FR-010 sono
      **gia' soddisfatti**, di proprieta' di `009`
- [x] R05 La generazione odierna e' un elenco etichetta/valore:
      `generazione/service.py:57-63` costruisce `righe` da
      `list_required_fields` e chiama `render_pdf(titolo, righe)`. Ogni PDF
      porta `DOCUMENTO DI TEST - NON UFFICIALE` (`generazione/renderer.py:13`)
- [x] R06 I campi del contratto dati della versione sono in
      `ModelloCampoRichiesto` (tabella `campo_modello`), leggibili con
      `catalog_repository.list_required_fields(db, versione_id)`: e' la
      sorgente dei placeholder ammessi per FR-005

---

## Phase 2: Persistenza del corpo documentale (Blocking Prerequisites)

**Goal**: il corpo del documento diventa un dato della **versione** modello, non
del modello: e' cosi' che FR-008 ottiene lo storico e FR-005 di `002`
l'immutabilita' dopo la pubblicazione, senza inventare un secondo meccanismo.

- [ ] T001 Mapping ORM `SezioneModello` in `backend/app/catalog/models.py`,
      accanto a `ModelloDocumentoVersione`, sulla tabella esistente
      `sezione_modello`. Nessuna migration di struttura: la tabella c'e' gia'
      (R01). Relazione `versione.sezioni` ordinata per `ordine`
- [ ] T002 In `contenuto` (JSONB) si serializza una lista di `BloccoDocumento`
      gia' definiti in `quality/schemas.py`. **Non** duplicare quei Pydantic in
      `builder`: importarli. Se la separazione fra moduli lo rende scomodo,
      spostarli in un modulo condiviso invece di ricopiarli
- [ ] T003 Funzione di composizione che, data una versione, assembla il
      `ModelloDocumentaleControllato` completo dalle sue sezioni ordinate, in
      `backend/app/builder/repository.py`
- [ ] T004 Estendere `clona_campi`/`crea_versione` in
      `backend/app/builder/repository.py:114-187` perche' una versione nuova
      erediti anche le sezioni della precedente, come gia' fa con i campi
- [ ] T005 [P] Test di persistenza: sezioni ordinate, vincolo unico su
      `(versione, codice)`, cancellazione a cascata con la versione, in
      `backend/tests/builder/test_sezioni_persistenza.py`

---

## Phase 3: User Story 1 - Comporre le sezioni di una versione (Priority: P1)

**Independent Test**: una versione in `BOZZA` accetta creazione, modifica e
riordino delle sezioni; una versione `PUBBLICATO` li rifiuta.

- [ ] T006 [US1] `GET /api/v1/builder/modelli/{modelloId}/versioni/{versioneId}/sezioni`
      in `backend/app/builder/api.py`, con autorizzazione per contesto tramite
      `verify_scrittura_su_contesto` come ogni altra rotta del builder
- [ ] T007 [US1] `PUT .../sezioni` che sostituisce l'intero insieme di sezioni
      della versione (stessa semantica di `010`: ogni submit e' una definizione
      completa, non una modifica incrementale)
- [ ] T008 [US1] Rifiuto di qualunque scrittura su una versione non in `BOZZA`,
      con errore funzionale esplicito (`MODELLO_VERSIONE_NON_MODIFICABILE`):
      FR-005 di `002` finalmente messo alla prova da un percorso di scrittura
      che potrebbe violarlo
- [ ] T009 [P] [US1] Test: composizione su bozza, rifiuto su pubblicata,
      riordino, eredita' delle sezioni in una versione derivata, in
      `backend/tests/builder/test_sezioni_api.py`

---

## Phase 4: User Story 2 - Placeholder validati contro il contratto dati (Priority: P1)

**Independent Test**: una sezione che usa un placeholder non presente fra i
campi della versione non supera la validazione, e la versione non si pubblica.

- [ ] T010 [US2] Derivare l'insieme dei placeholder ammessi dai
      `ModelloCampoRichiesto` della versione (R06) e passarlo a
      `validate_document_model(..., placeholder_contratto_dati=...)`:
      e' il cablaggio che R03 aspetta. FR-004, FR-005
- [ ] T011 [US2] Chiamare la validazione alla scrittura delle sezioni (T007),
      restituendo l'elenco completo delle violazioni, non la prima
- [ ] T012 [US2] **Cancello di pubblicazione**: `service.transizione` verso
      `PUBBLICATO` rifiuta una versione con placeholder non dichiarati o non
      risolti. FR-006. Questo e' il punto in cui `003` protegge davvero `004`
- [ ] T013 [P] [US2] Test: placeholder sconosciuto rifiutato alla scrittura;
      pubblicazione bloccata; messaggio che elenca tutte le violazioni, in
      `backend/tests/builder/test_placeholder_validazione.py`
- [ ] T014 [US2] Campi complessi (FR-007): decidere se lo schema di sotto-campi
      serve gia' ora. L'albero GEBAN reale osservato il 2026-09-22 non espone
      alcun campo complesso (65 foglie, nessuna chiave extra), quindi questo
      task **resta aperto senza urgenza**: non inventare la struttura prima di
      avere un caso reale

---

## Phase 5: User Story 3 - Modello documentale controllato

**Gia' implementata, di proprieta' di `009`** (`DEC-003-CORPO-DOCUMENTO-RIPIANIFICATO`).
Non riscrivere: usare.

- [x] T015 [US3] Vocabolario blocchi, grammatica di posizionamento, rifiuto di
      HTML/CSS/script liberi, asset referenziati per id: implementati in
      `backend/app/quality/document_model.py`, dichiarati dal suo stesso
      docstring come `spec 009, FR-036..FR-038`
- [-] T016 [US3] SUPERATO: creare `backend/app/builder/document_model/`.
      Il validatore vive in `quality/` e li' resta
- [ ] T017 [US3] Trasferire formalmente la proprieta' di FR-009, FR-010 e
      FR-011 a `009` nella matrice di copertura, oppure dichiarare in `spec.md`
      che `003` li eredita. Oggi sono coperti da righe COV con
      `spec_owner: 009`: la titolarita' va scritta una volta sola

---

## Phase 6: Dal PDF di test al documento reale

**Goal**: il punto di arrivo dell'intera spec. Finche' questa fase non e'
chiusa, GEMODO produce una scheda dati, non un bando.

- [ ] T018 Estendere `backend/app/generazione/renderer.py` perche' renda una
      lista di `BloccoDocumento` invece di coppie etichetta/valore, rispettando
      tipo e posizionamento. Mantenere la funzione pura: blocchi in, byte PDF
      fuori, nessun I/O
- [ ] T019 Sostituire i placeholder con i valori di `request.dati` al momento
      della generazione, in `backend/app/generazione/service.py`. Un
      placeholder senza valore e' un errore funzionale esplicito, mai una
      stringa vuota silenziosa
- [ ] T020 Rimuovere la marcatura `DOCUMENTO DI TEST - NON UFFICIALE` **solo**
      quando esiste un percorso ufficiale: oggi ADR 0002 dice che non esiste.
      Coordinare con `004`, che possiede la generazione ufficiale. Non
      rimuoverla come effetto collaterale di questa fase
- [ ] T021 [P] Test end-to-end: modello con sezioni e placeholder, pubblicato,
      poi `POST /api/v1/documenti/genera` produce un PDF che contiene il testo
      composto con i valori sostituiti, in `backend/tests/e2e/`

---

## Phase 7: Allineamento

- [ ] T022 [P] Righe di copertura in `docs/quality-coverage-matrix.yaml` per i
      FR di `003` via via che vengono chiusi, e rimozione delle voci
      corrispondenti da `docs/coverage-baseline.yaml` (il cricchetto puo' solo
      restringersi)
- [ ] T023 [P] Contratto OpenAPI delle rotte sezioni in
      `specs/003-sezioni-placeholder-versionamento/contracts/sezioni-placeholder-api.openapi.yaml`,
      allineato alle rotte effettivamente esposte
- [ ] T024 Scenario eseguibile nel quickstart di `009`, sul modello dello
      Scenario 11: comporre sezioni, tentare un placeholder non valido,
      pubblicare, generare

---

## Dipendenze

- Phase 2 blocca tutto il resto.
- Phase 3 precede Phase 4 (non si validano sezioni che non si possono scrivere).
- T012 (cancello di pubblicazione) precede Phase 6: non ha senso rendere un
  documento che non e' stato validato.
- Phase 6 richiede il coordinamento con `004` su cio' che e' ufficiale.
- `008` e' bloccata da questa spec (`DEC-008-AI-MCP-FUORI-SCOPE`).

## Nota di metodo

Il piano precedente contava 69 task e ne ha realizzati zero, perche' descriveva
54 percorsi di cui 51 non sono mai esistiti. Questo piano ne conta 24, di cui 8
gia' chiusi dalla ricognizione, e ogni task nuovo cita un file che esiste oggi
oppure dichiara esplicitamente di crearlo. Se durante l'implementazione la
struttura diverge da quanto scritto qui, **si aggiorna questo file nello stesso
commit**: e' la regola che mancava e che ha prodotto la deriva.
