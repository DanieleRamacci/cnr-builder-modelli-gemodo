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

> **Priorita' 1 dal 2026-09-24 (decisione dell'utente).** Questa spec e' il
> builder vero: comporre il documento. Finche' non e' chiusa, ogni PDF esce
> marcato `DOCUMENTO DI TEST - NON UFFICIALE` (`generazione/renderer.py`) e
> GEBAN non puo' usare in produzione nulla di cio' che GEMODO produce. Lo
> spartiacque e' T020, che toglie quella marcatura: tutto cio' che viene prima
> serve ad arrivarci.
>
> La verifica di compatibilita' del contratto (`010` T056 e seguenti) e'
> stata **spostata dopo**: avvisa che un modello non rispecchia piu' il ramo,
> ma finche' i modelli non producono documenti ufficiali l'avviso arriva su
> qualcosa che nessuno sta ancora usando. Prima il modello serve a qualcosa,
> poi lo si sorveglia. Il lavoro gia' fatto per quella catena (T055, migration
> `0022`) resta pronto e non intralcia nulla.

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

- [x] T001 (`catalog/models.py`) Mapping ORM `SezioneModello` sulla tabella
      esistente `sezione_modello`, nessuna migration di struttura. Relazione
      `versione.sezioni` ordinata per `ordine`, con `cascade="all, delete-orphan"`:
      la sequenza e' parte del documento, non un dettaglio di presentazione,
      quindi non puo' dipendere da come il database restituisce le righe.
- [x] T002 (`app/documentale/schemas.py`, nuovo) `contenuto` serializza una
      lista di `BloccoDocumento`. **Scelta la seconda opzione prevista dal
      task**: i Pydantic sono stati *spostati* in un modulo condiviso, non
      importati da `quality`. `app/quality/` descrive la readiness della `009`
      - manifest, gate, coverage - e nessun modulo di dominio lo importa: farlo
      avrebbe invertito il verso della dipendenza, con il dominio che dipende
      da chi lo ispeziona. `quality/schemas.py` ri-esporta dallo stesso modulo,
      quindi la `009` vede gli stessi nomi e non esistono due definizioni che
      possono divergere.
- [x] T003 (`builder/repository.py::composizione_documentale`) Assembla il
      `ModelloDocumentaleControllato` dalle sezioni ordinate. I blocchi sono
      **rinumerati con un ordine progressivo globale**: due sezioni che
      internamente ripartono da zero si sovrapporrebbero una volta concatenate.
      `placeholder_usati` raccoglie l'unione senza duplicati, ed e' l'insieme
      che la validazione di US2 confrontera' con i campi del modello.
- [x] T004 (`builder/repository.py::clona_sezioni`, `crea_versione`,
      `builder/service.py`) Una versione nuova eredita le sezioni come gia'
      faceva con i campi, e l'edizione derivata pure: e' lo stesso bando in
      un'altra dimensione, non un documento diverso. La copia di `contenuto`
      e' **profonda**: condividendo la lista, modificare la bozza avrebbe
      cambiato anche il documento gia' pubblicato.
- [x] T005 [P] (`backend/tests/builder/test_sezioni_persistenza.py`) Cinque
      test su PostgreSQL reale: ordine dichiarato rispettato anche inserendo
      in ordine sparso, vincolo unico su `(versione, codice)`, cascata alla
      cancellazione, composizione che concatena e rinumera, eredita' che non
      condivide il contenuto. E' la prima cosa che esercita davvero la
      tabella, ferma e senza mapping dalla migration `0001`.

---

## Phase 3: User Story 1 - Comporre le sezioni di una versione (Priority: P1)

**Independent Test**: una versione in `BOZZA` accetta creazione, modifica e
riordino delle sezioni; una versione `PUBBLICATO` li rifiuta.

- [x] T006 [US1] (`builder/api.py::leggi_sezioni`, `service.py::sezioni`)
      `GET .../sezioni` con autorizzazione per contesto. Risponde anche con il
      **documento composto**, non solo con le sezioni: e' la forma in cui il
      documento si legge. Leggibile in qualunque stato, perche' vedere com'e'
      fatto un documento pubblicato e' lecito ed e' modificarlo che non lo e'.
      La versione deve appartenere al modello dell'URL: senza quel controllo un
      id di versione noto sarebbe bastato a scavalcare l'autorizzazione.
- [x] T007 [US1] (`builder/api.py::sostituisci_sezioni`,
      `repository.py::sostituisci_sezioni`) `PUT .../sezioni` sostituisce
      l'insieme: una sezione omessa viene rimossa. Il repository cancella e
      riscrive invece di riconciliare riga per riga - una riconciliazione
      dovrebbe comunque decidere cosa fare dei codici spariti, cioe'
      cancellare gli stessi record con piu' passaggi e piu' modi di sbagliare.
      **Il contratto `0.2.0` prevedeva `POST` piu' `PUT` per singola sezione**:
      descriveva anche campi che nella tabella non esistono (`id` intero,
      `obbligatoria`, `origine_template_id`), come i percorsi che la
      ricognizione del 2026-09-22 trovo' inesistenti. Riscritto (T023).
- [x] T008 [US1] (`builder/service.py::sostituisci_sezioni`) Scrittura solo in
      `BOZZA`, altrimenti `409 MODELLO_VERSIONE_NON_MODIFICABILE`. La risposta
      espone `modificabile`, cosi' il builder non deve dedurre da se' se il
      form e' scrivibile: la regola vive nel backend.
- [x] T009 [P] [US1] (`backend/tests/builder/test_sezioni_api.py`) Sei test
      HTTP su PostgreSQL reale: composizione, riordino come invio unico,
      rimozione per omissione, rifiuto su pubblicata con lettura ancora
      permessa, codici duplicati, blocco di tipo sconosciuto, versione di un
      altro modello, eredita' nell'edizione derivata.

---

## Phase 4: User Story 2 - Placeholder validati contro il contratto dati (Priority: P1)

**Independent Test**: una sezione che usa un placeholder non presente fra i
campi della versione non supera la validazione, e la versione non si pubblica.

- [x] T010 [US2] (`builder/service.py::_placeholder_ammessi`,
      `_valida_documento`) I placeholder ammessi sono i **codici** dei campi
      richiesti della versione - non le etichette, che cambiano senza cambiare
      il contratto - e arrivano a `validate_document_model` come
      `placeholder_contratto_dati`. Era il cablaggio che mancava: la funzione
      accettava gia' quel parametro e non aveva chiamanti.
- [x] T011 [US2] (`builder/service.py::sostituisci_sezioni`) La validazione
      scatta alla scrittura e risponde `400 PLACEHOLDER_NON_VALIDO` con
      **tutte** le violazioni nei `dettagli`, non la prima: chi sta componendo
      le corregge in un giro solo. La scrittura avviene nella stessa
      transazione, quindi un rifiuto non lascia sezioni a meta' - c'e' un test
      che rilegge e verifica che non sia rimasto nulla.
- [x] T012 [US2] (`builder/service.py::transizione`) **Cancello di
      pubblicazione**: la transizione a `PUBBLICATO` rivalida il documento e
      rifiuta se un placeholder non corrisponde ad alcun campo. Serve anche con
      T011 gia' attivo, perche' una versione puo' essere stata composta prima
      che la validazione esistesse, o i campi possono essere cambiati dopo. Da
      `PUBBLICATO` in poi il documento e' immutabile e genera output veri: un
      buco che arriva li' non si chiude piu' senza una versione nuova.
      Verificato che il test lo presidi davvero, rimuovendo il cancello e
      vedendolo fallire.
- [x] T013 [P] [US2] (`backend/tests/builder/test_placeholder_validazione.py`)
      Cinque test HTTP su PostgreSQL reale: placeholder del contratto ammesso,
      sconosciuto rifiutato senza lasciare scritture parziali, elenco completo
      delle violazioni su tre segnaposti in due sezioni, pubblicazione bloccata
      su una versione composta aggirando l'API, e caso normale che si pubblica
      senza ostacoli.
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
- [x] T023 [P] (`contracts/sezioni-placeholder-api.openapi.yaml` 0.3.0)
      Rotte sezioni riscritte sulla realta': `GET` + `PUT` d'insieme al posto
      di `POST` + `PUT` per singola sezione, `SezioneModello` con
      `codice`/`ordine`/`contenuto` al posto dei campi mai esistiti, e
      `BloccoDocumento` allineato al Pydantic condiviso. Restano da rivedere
      con i rispettivi task le rotte `/valida` e `/template-sezioni`.
      *(Originale: Contratto OpenAPI delle rotte sezioni in
      `specs/003-sezioni-placeholder-versionamento/contracts/sezioni-placeholder-api.openapi.yaml`,
      allineato alle rotte effettivamente esposte)*
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
