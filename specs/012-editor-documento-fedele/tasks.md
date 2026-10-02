---

description: "Task list per 012 - Editor documentale fedele al provvedimento reale"
---

# Tasks: Editor documentale fedele al provvedimento reale

**Input**: documenti di progetto in `/specs/012-editor-documento-fedele/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md),
[research.md](./research.md), [data-model.md](./data-model.md),
[contracts/](./contracts/)

**Tests**: inclusi. Questo progetto non ammette test che simulano la logica di
dominio: ogni verifica gira contro Postgres reale o contro il renderer reale.
Due criteri di successo (SC-004, SC-006) sono **verificabili solo** con un test,
quindi i task di test qui non sono accessori.

**Organization**: raggruppati per user story, cosi' che ciascuna sia
implementabile e collaudabile da sola.

## Format: `[ID] [P?] [Story] Descrizione`

- **[P]**: parallelizzabile (file diversi, nessuna dipendenza)
- **[Story]**: a quale user story appartiene

## Path Conventions

Applicazione web: `backend/app/`, `frontend/src/`, come da
[plan.md](./plan.md#source-code-repository-root).

## Ordine delle fasi

Le fasi **non** seguono la priorita' delle user story ma l'ordine di dipendenza
stabilito nel plan: US4 (P2) arriva prima di US3 (P2) perche' e' cio' che rende
verificabili US1 e US2, e senza di essa l'unico modo di guardare il risultato e'
pubblicare.

---

## Phase 1: Setup

**Purpose**: cio' che va messo a posto prima di toccare il dominio. Il contratto
va pubblicato **prima** del codice, non dopo (Principio II).

- [x] T001 Copiare i quattro `.ttf` di Titillium Web (regular, 700, italic,
      700italic) da `frontend/node_modules/bootstrap-italia/dist/fonts/Titillium_Web/`
      in `backend/app/generazione/fonts/`, con `OFL.txt` accanto.
      `node_modules/` non e' un percorso su cui il backend possa fare
      affidamento a runtime e `frontend/dist/` e' un artefatto di build
      (research.md R1).
      *Fatto 2026-10-01*: salvati come `TitilliumWeb-{Regular,Bold,Italic,BoldItalic}.ttf`;
      verificato con fontTools che tutte e quattro le varianti contengano
      virgolette curve, apostrofo tipografico, trattini, lettere accentate, `€`, `§`, `«»`.
- [x] T002 Fondere [`contracts/anteprima-api.openapi.yaml`](./contracts/anteprima-api.openapi.yaml)
      in `specs/002-builder-modelli/contracts/builder-modelli-api.openapi.yaml`
      e verificare che sia registrato in `PUBLISHED_CONTRACTS`
      (`backend/app/quality/openapi_docs.py`), cosi' che compaia in Swagger
      prima dell'implementazione.
      **Rinviato a T036 (decisione 2026-10-01)**: `test_builder_modelli_contract.py`
      impone che il contratto descriva solo rotte che il router espone davvero
      (difesa contro il contratto 0.2.0). Contratto e rotta entrano quindi
      **insieme**, nello stesso commit di T036; il test resta com'e'.
- [x] T003 [P] Estendere la colonna `Condizione` di
      `MODELLO_DOCUMENTALE_NON_VALIDO` in `infra/openapi/errors.md` per
      nominare anche il testo dei frammenti. **Nessun codice di errore nuovo**:
      quello esistente copre gia' questo caso (contracts/formato-documentale.md).

---

## Phase 2: Foundational (blocca tutte le storie)

**Purpose**: la forma nuova del paragrafo. Nessuna user story ha dove salvare
finche' questa fase non e' chiusa.

### Formato

- [x] T004 [P] Aggiungere `FrammentoTesto`, `ElementoElenco`,
      `AllineamentoTesto`, `TipoMarcatore` in
      `backend/app/documentale/schemas.py`.
- [x] T005 In `BloccoDocumento` (stesso file): **rimuovere** `contenuto`,
      aggiungere `frammenti`, `allineamento`, `elementi`; aggiungere `ELENCO` a
      `TipoBloccoDocumento`. `extra="forbid"` e' gia' attivo, quindi un blocco
      che porta ancora `contenuto` viene rifiutato senza scrivere altro codice.
- [x] T006 [P] Aggiungere `ELENCO` a `POSIZIONI_AMMESSE` in
      `backend/app/quality/document_model.py` (`BODY`, `COLUMN_LEFT`,
      `COLUMN_RIGHT`).

### Validazione (FR-002, SC-005)

- [x] T007 In `backend/app/quality/document_model.py`, validare: markup nel
      `testo` di un frammento; `livello` fuori da {0,1}; `elementi` su un blocco
      che non e' `ELENCO`; `collegamento` con schema diverso da
      `http`/`https`/`mailto`. Tutti producono
      `MODELLO_DOCUMENTALE_NON_VALIDO` (422), **rifiuto** e mai bonifica
      silenziosa.
      **Nota**: questo controllo oggi non esiste - il divieto e' applicato solo
      al booleano auto-dichiarato `contiene_html_libero` (research.md R6).
      E' codice nuovo, non un adeguamento.
- [x] T008 [P] Test di T007 in `backend/tests/`: `<b>` nel testo,
      `javascript:` nel collegamento, `livello: 2`, `elementi` su `PARAGRAFO`.
      Copre SC-005.

### Migrazione (FR-016, SC-004)

- [x] T009 Migrazione Alembic su `sezione_modello.contenuto` (JSONB):
      `{"contenuto": "x"}` diventa `{"frammenti": [{"testo": "x"}]}`,
      `contenuto: null` diventa `frammenti: []`. `downgrade` concatena i
      `testo`.
- [x] T010 Test della migrazione su Postgres reale (Testcontainers): righe
      prima, `upgrade`, righe dopo, `downgrade`, righe di nuovo come prima.
      *Fatto 2026-10-01*: `tests/integration/test_migrazione_frammenti_0024.py`,
      con un secondo test che documenta la perdita voluta al `downgrade`
      (enfasi, `ELENCO` -> `PARAGRAFO`, `allineamento`).
- [ ] T011 **SC-004, prima di eseguire la migrazione in qualunque ambiente**:
      generare il PDF di ogni versione pubblicata sullo stato precedente,
      conservarne il testo estratto, migrare, rigenerare, confrontare coppia per
      coppia. Si confronta il **testo estratto**, non i byte: un PDF contiene
      data di produzione e identificatori che cambiano a ogni generazione.
      Una differenza ferma la migrazione - non si corregge il confronto.
      *Strumento pronto 2026-10-01*: `backend/scripts/sc004_confronto_migrazione.py`
      (fasi `prima`/`dopo`). **Non ancora eseguito**: nessun ambiente con
      versioni pubblicate e' stato ancora migrato. Il task si chiude solo con
      l'esecuzione, ambiente per ambiente.
      *Prova generale 2026-10-01, in locale*: codice a `a915a0a` (prima della
      012), database alla 0023 con tre versioni pubblicate nella forma
      vecchia; fase `prima`; migrazione 0024-0025 col codice nuovo; fase
      `dopo`. Esito: **2 versioni confrontate, 0 differenze**; la terza,
      con virgolette curve, elencata a parte come "prima non si rendeva"
      (`FPDFUnicodeEncodingException`, research.md R1). Con un testo atteso
      alterato lo script segnala la differenza ed esce con codice 1. Lo
      strumento e' quindi provato; resta da **eseguire in produzione prima
      del redeploy** (il container migra da solo all'avvio). Il test online
      e' gia' migrato senza confronto: dati sacrificabili (011 T004b).
      **Come eseguirla in produzione**: la fase `prima` gira col codice
      precedente alla 012, la cui immagine non ha `pypdf`: si lancia da una
      macchina di sviluppo con il worktree pre-012 e `DATABASE_URL` verso il
      database di produzione, come nella prova generale; la fase `dopo` puo'
      girare nel container nuovo (`uv run --no-dev python
      scripts/sc004_confronto_migrazione.py dopo --file ...`), verificato.

### Renderer

- [x] T012 In `backend/app/generazione/renderer.py`, registrare Titillium Web
      nelle quattro varianti e sostituire ogni `Helvetica`.
- [x] T013 [P] Test: un paragrafo con virgolette curve, apostrofo tipografico,
      trattino lungo e lettere accentate arriva invariato nel testo estratto.
      Copre SC-006.
      **Questo test fallisce oggi, prima della feature**, e non con un carattere
      sbagliato: il core font solleva `FPDFUnicodeEncodingException`, che
      `GenerazioneDocumentiService.genera` cattura nel suo `except Exception`
      generico e trasforma in un documento `FALLITO` (research.md R1).
- [x] T014 Riscrivere `_rendi_blocco` sui frammenti: resa con
      `text_columns()` + `paragraph.write()`, cambiando variante di font fra un
      frammento e l'altro (research.md R2).
- [x] T015 Applicare `allineamento` esplicito, `GIUSTIFICATO` incluso. La
      tabella `_ALLINEAMENTO` che deriva l'allineamento dal posizionamento
      resta solo come default per i blocchi che non lo dichiarano.
- [x] T016 Far leggere al renderer il campo `stile` (`H1`/`H2`), che oggi
      **scrive il frontend e nessuno legge**. E' il difetto che la spec cita
      come gia' visibile; FR-008 non ammette che l'editor mostri un titolo e il
      PDF produca un paragrafo.
- [x] T017 Riscrivere `sostituisci_placeholder` per frammento invece che sulla
      stringa del blocco (FR-005).
- [x] T018 [P] Test: un segnaposto dentro un frammento in grassetto produce un
      valore in grassetto, e il paragrafo non si spezza (US1 scenario 3).
      *T004-T010, T012-T018 fatti 2026-10-01*: suite backend 463 test verdi su
      Postgres reale. **Attenzione**: da qui il frontend scrive ancora
      `contenuto` e il backend lo rifiuta (`extra="forbid"`): l'editor non
      salva finche' non sono chiusi T019-T022.

**Checkpoint**: il formato nuovo esiste, e' validato, migrato e reso. Le storie
possono partire.

---

## Phase 3: User Story 1 - Enfasi dentro il testo (P1)

**Goal**: il gestore scrive un "visto" selezionando le porzioni come farebbe in
Word.

**Independent Test**: comporre un singolo "visto" del bando di riferimento,
pubblicarlo, verificare grassetto e corsivo nel PDF. Vale da solo, senza elenchi
e senza cornice.

- [x] T019 In `frontend/src/features/builder/modello-anteprima.component.ts`,
      sostituire `contenteditable="plaintext-only"` (riga ~390) con un editor
      ricco controllato. Quel `plaintext-only` era obbligato finche' il
      paragrafo era una stringa sola: senza frammenti non c'era dove mettere il
      grassetto, quindi conservarlo sarebbe stato inutile.
- [x] T020 Abilitare B/I/U, che oggi sono nel markup ma **disabilitati**, e
      applicarli alla selezione (FR-006).
- [x] T021 [P] Modello dati lato frontend: un blocco porta frammenti, non una
      stringa.
- [x] T022 Serializzazione DOM -> frammenti alla scrittura, e frammenti -> DOM
      alla lettura. Unire i frammenti adiacenti con gli stessi attributi, per
      non accumulare frammenti spuri a ogni modifica.
- [x] T023 **Incolla da elaboratore di testi** (FR-017): leggere la
      rappresentazione HTML degli appunti, conservare enfasi, capoversi ed
      elenchi, scartare colori, font, rientri, immagini e tabelle. La
      conversione avviene **nel browser**: al servizio arrivano frammenti, mai
      markup.
      **Il dettaglio che non va dimenticato**: Word incolla spesso `1.`, `a)`
      come testo dentro il paragrafo. Sommati alla numerazione calcolata in resa
      darebbero `1. 1. Sono indetti...`. I marcatori scritti a mano vanno
      riconosciuti e rimossi quando l'elenco viene convertito (research.md R8).
- [x] T024 [P] Test Vitest: applicazione dell'enfasi su selezione parziale,
      enfasi annidate (grassetto e corsivo insieme), incolla da Word con
      marcatori di lista da rimuovere.
- [x] T025 Test e2e Playwright contro lo stack reale: comporre un "visto" del
      bando di riferimento, pubblicare, generare, verificare l'enfasi nel PDF
      (US1 scenari 1 e 2).
      *T019-T025 fatti 2026-10-01*. Conversioni in
      `frontend/src/features/builder/frammenti.ts` (16 test Vitest), editor in
      `modello-anteprima.component.ts` (4 test di componente nuovi, 143 totali).
      L'enfasi si applica sui frammenti e non con `document.execCommand`,
      deprecato e diverso per browser. L'e2e sta in `builder-lifecycle.spec.ts`
      e non in un file suo: discovery-mock offre due soli tipi documento, gia'
      presi dagli altri due e2e, e un terzo andrebbe in 409 per FR-024. Genera
      il PDF con `geban-backend`, a cui `tokenGeneratore()` assegna
      `DOCUMENTI_GENERATORE` solo per la durata del test, e verifica i font
      parola per parola con `backend/tests/support/pdf.py`. Suite e2e 4/4 su
      stack reale.
      **Anticipato dalla Phase 4, perche' l'incolla non stava in piedi senza**:
      l'editor mostra e modifica **tutti** i blocchi di una sezione (nucleo di
      T026) e un `ELENCO` con le sue voci, Invio/Backspace/Tab sulle voci e i
      pulsanti `1.`/`•` che convertono il paragrafo (parte di T028). Senza, i
      capoversi incollati dopo il primo sarebbero stati salvati e invisibili.
      **Divergenza aperta (FR-008) fino a T029**: l'editor mostra `1.`/`a)`,
      il PDF scrive le voci senza marcatore. Inoltre `composizione_documentale`
      passa al renderer i blocchi gia' concatenati, senza confini di sezione:
      T029 deve portarli, o l'azzeramento per sezione non e' implementabile.
      Corretti due difetti FR-008 trovati per strada nello SCSS: H1 in
      maiuscolo nell'editor ma non nel PDF, e ogni blocco giustificato
      nell'editor ma allineato a sinistra nel PDF.

**Checkpoint**: la parte piu' voluminosa del bando - i quaranta paragrafi
normativi - diventa componibile.

---

## Phase 4: User Story 2 - Struttura dell'articolato (P1)

**Goal**: intestazione dell'articolo centrata, commi numerati, lettere annidate,
testo giustificato.

**Independent Test**: ricostruire l'art. 3 del bando di riferimento e
verificarne la resa nel PDF. Dipende dalla Phase 2, non da US1.

- [x] T026 **Mostrare tutti i blocchi di una sezione** nell'editor, non solo il
      primo (FR-007). Oggi `testoSezione` legge `contenuto[0]`: qualunque blocco
      oltre il primo esiste nei dati e non si vede.
      Questo task sblocca anche la futura biblioteca dei "visti"
      (`docs/project-map.md:212`), che senza sezioni multi-blocco non potrebbe
      mostrare cio' che inserisce.
- [x] T027 Permettere all'editor di creare **tutti** i tipi di blocco del
      vocabolario, non solo paragrafi (FR-007).
- [x] T028 Blocco `ELENCO` nell'editor: due livelli, rientro e sporgenza con
      Tab e Shift-Tab, scelta del marcatore.
- [x] T029 Numerazione calcolata in resa nel renderer, con azzeramento dei
      contatori all'inizio di ogni sezione e a ogni blocco `TITOLO`
      (research.md R3). Nessun numero viene mai salvato nei dati.
- [x] T030 [P] Allineamento nella toolbar, giustificato incluso (FR-004).
- [x] T031 [P] Test: inserito un comma in mezzo a un articolo di tre commi, la
      numerazione resta coerente in tutto l'articolo (US2 scenario 1). E' la
      prova che la numerazione e' calcolata e non scritta.
- [x] T032 [P] Test: un elenco che attraversa un'interruzione di pagina
      prosegue la numerazione invece di ripartire (Edge Case).
      *T029, T031, T032 fatti 2026-10-01*: `marcatori_elenchi` nel renderer,
      voci con rientro sporgente (marcatore a sinistra, testo allineato dopo),
      marcatore e prima riga sempre sulla stessa pagina. I confini di sezione
      arrivano al renderer con `inizi_sezione(versione)` in
      `builder/repository.py`, senza cambiare `ModelloDocumentaleControllato`.
      L'editor usa la stessa regola anche in sola lettura. Test in
      `tests/generazione/test_numerazione_elenchi.py`; l'e2e verifica
      `1. ... a) ...` nel PDF generato. Chiusa la divergenza FR-008 aperta in
      Phase 3. Il numero dell'**articolo** resta scritto a mano (chiarimento
      del 2026-10-01 in spec.md).
- [x] T033 Test e2e: ricostruire l'art. 3 del bando di riferimento, generare,
      verificare annidamento, rientri e intestazione centrata (US2 scenari 2 e 3).
      *T026-T028, T030, T033 fatti 2026-10-01* (e T045, T046 di Phase 6, che
      erano lo stesso lavoro). L'editor crea paragrafo, titolo d'articolo
      (centrato), elenco, firma (`BOTTOM_RIGHT`, a destra) e interruzione di
      pagina, inseriti dopo il blocco selezionato dal pannello Blocchi; il
      pannello Proprieta' cambia tipo ed elimina. Invio apre un capoverso
      (Maiusc+Invio va a capo dentro), Backspace a inizio blocco lo riunisce
      al precedente. Allineamento e marcatore `a)` nella toolbar. Fuori dai
      tipi creabili: `TABELLA` (fuori scope), `LOGO` (niente asset),
      `FOOTER`/`INTESTAZIONE` (sono cornice, US3).
      L'e2e compone l'art. 3 del bando di riferimento solo da tastiera e
      pulsanti e verifica nel PDF numerazione, rientri e titolo centrato.
      **Tre difetti veri trovati dall'e2e, non dai test unitari**: (1) dopo un
      salvataggio automatico la selezione tornava alla prima sezione e il
      comando successivo colpiva il blocco sbagliato; (2) ogni passaggio fra
      blocchi faceva partire un salvataggio, che disabilitava la toolbar; (3)
      dopo Invio il cursore passava al blocco nuovo solo al disegno
      successivo, e i tasti battuti nel frattempo finivano nel blocco prima.
      **Limite noto**: il capoverso che nel bando continua un comma dopo le sue
      lettere ("Ai sensi dell'art. 38 comma 3...", art. 3 comma 1) diventa un
      paragrafo al margine: la numerazione regge, il rientro sotto il comma no.

**Checkpoint**: articolato e parte normativa sono entrambi componibili. E' il
grosso di SC-001.

---

## Phase 5: User Story 4 - Anteprima fedele del PDF (P2)

**Goal**: prima di pubblicare, il gestore vede il PDF che verrebbe generato.

**Independent Test**: aprire l'anteprima di una bozza e confrontarla col PDF
generato dopo la pubblicazione.

**Perche' qui e non dopo US3**: e' cio' che rende verificabile tutto quanto
precede. Senza, l'unico modo di guardare il risultato e' pubblicare.

- [x] T034 Metodo di anteprima in `backend/app/builder/service.py`: compone i
      blocchi e chiama `render_documento`, **senza importare lo storage**.
      Percorso separato da `GenerazioneDocumentiService.genera`, non un
      parametro `anteprima=True` su di esso: le tre negazioni di FR-010 nascono
      tutte da quel metodo (`hash_dati`, `esistente_per_chiave`,
      `registra_successo`), e un condizionale sbagliato li' produrrebbe un
      documento ufficiale non voluto. Separando, le negazioni sono vere per
      costruzione (research.md R4).
- [x] T035 Valori fac-simile per i segnaposto, derivati dall'etichetta del campo
      nella forma `«etichetta»`, cosi' che nel PDF si distingua a colpo d'occhio
      il segnaposto dal testo.
- [x] T036 Rotta `POST /builder/modelli/{modelloId}/versioni/{versioneId}/anteprima`
      in `backend/app/builder/api.py`, come da contratto. Autorizzazione con
      `verify_scrittura_su_contesto` - **non** `DOCUMENTI_GENERATORE`: e'
      un'azione di chi compone.
      **Assorbe T002**: nello stesso commit fondere
      `contracts/anteprima-api.openapi.yaml` nel contratto del builder (002,
      OpenAPI 3.0.3: adattare a `NotFound`/`Conflict`/`Errore` chiuso gia'
      presenti) e aggiungere il path all'elenco atteso in
      `test_builder_modelli_contract.py`.
- [x] T037 [P] Test di FR-010, che e' il cuore della storia: dopo un'anteprima,
      nessun `DocumentoGenerato` risulta registrato, e una generazione
      successiva con gli stessi dati **non** trova una chiave di idempotenza
      gia' consumata.
- [x] T038 [P] Test di autorizzazione: un token con soli permessi di
      generazione riceve 403; un gestore di un altro contesto riceve 404, non
      403 (non si rivela l'esistenza di cio' che non puo' vedere).
- [x] T039 [P] Test: anteprima su versione `PUBBLICATO` risponde 409.
- [x] T040 Frontend: il pulsante "Anteprima", che oggi fa solo `scrollIntoView`
      (riga ~1071), richiede e mostra il PDF vero.
- [x] T041 Test e2e SC-003: anteprima della bozza, pubblicazione, generazione
      con dati veri, confronto - struttura, ordine, enfasi e numerazione
      coincidono, differiscono solo i valori.
      *T034-T041 fatti 2026-10-01* (e T002, fuso in questo commit come
      deciso). `BuilderService.anteprima` usa solo il renderer, mai lo
      storage; fac-simile `«etichetta»`, `valori` facoltativi; 409 fuori
      bozza, 422 struttura non valida, 400 corpo non valido (convenzione del
      servizio). Autorizzazione: 403 a chi non e' gestore da nessuna parte,
      404 a chi e' gestore di un altro contesto. Frontend: il pulsante
      "Anteprima" salva prima, se serve (anche un salvataggio automatico in
      corso), poi mostra il PDF in una finestra con "Scarica"; verificato in
      Google Chrome che il visualizzatore lo rende (il Chromium headless di
      Playwright non ha il visualizzatore, l'e2e scarica il PDF e lo confronta).
      SC-003: a parita' di valori il corpo di anteprima e documento generato
      coincide frammento per frammento (test di backend), e l'e2e confronta
      anteprima e PDF finale differenti solo nei valori.

**Checkpoint**: da qui in avanti ogni cosa e' verificabile senza pubblicare.

---

## Phase 6: User Story 3 - Cornice della pagina (P2)

**Goal**: logo e numero di pagina su ogni pagina, interruzioni volute, blocco
firma in chiusura.

**Independent Test**: generare un documento di piu' pagine e verificare che logo
e numero compaiano su tutte, non solo sulla prima.

**Due attori distinti**: la cornice la configura l'amministratore sul tipo
documento; interruzione di pagina e firma restano al gestore nell'editor.

- [x] T042 [P] `CornicePagina` in `backend/app/documentale/schemas.py`
      (`logo_ref`, `intestazione`, `pie_pagina`, `numerazione_pagine`), con la
      stessa grammatica a frammenti del resto del formato.
- [x] T043 Migrazione Alembic: colonna JSONB `cornice_pagina` su
      `tipo_documento`.
- [x] T044 Renderer: intestazione e pie' di pagina ripetuti su **ogni** pagina,
      con numerazione. E' una cornice ricorrente, non i blocchi `LOGO`/`FOOTER`
      esistenti, che restano per i casi in cui compaiono una volta sola nel
      corpo.
- [x] T045 [P] `INTERRUZIONE_PAGINA` creabile dall'editor (FR-012).
- [x] T046 [P] Blocco `FIRMA` creabile dall'editor, allineato a destra (US3
      scenario 3).
- [x] T047 Configurazione della cornice in
      `frontend/src/features/configurazione/tipo-documento-struttura.component.ts`.
- [x] T048 [P] Test: documento di tre pagine, logo e numero su ciascuna (US3
      scenario 1); interruzione di pagina rispettata (scenario 2).
      *T042-T044, T047, T048 fatti 2026-10-01*. `CornicePagina` sul tipo
      documento (migrazione 0025, colonna caricata solo per il PDF), stesse
      regole dei frammenti piu' al massimo 3 righe di intestazione e 1 di pie'
      di pagina. Testata e pie' disegnati da `header()`/`footer()` di fpdf2,
      quindi anche sulle pagine aperte dall'a capo automatico; "Pagina N di M".
      Rotte `GET/PUT /configurazione/integrazioni/{id}/tipi-documento/{codice}/cornice`
      (contratto 010 0.4.0), solo GEMODO_ADMIN, con audit
      `CORNICE_PAGINA_CONFIGURATA`. Pagina "Cornice" accanto a "Configura
      policy". **Il logo**: `logo_ref` sceglie fra i loghi noti al servizio
      (`LOGHI`), non si carica; il file `backend/app/generazione/loghi/logo-ente.png`
      va fornito dall'ente e oggi manca, quindi la cornice esce senza logo e
      la pagina lo dice.

---

## Phase 7: User Story 5 - Collegamenti (P3)

**Goal**: collegamenti a portali e indirizzi PEC.

- [x] T049 [P] Resa del `collegamento` del frammento nel PDF, con il `testo`
      che resta leggibile dove il collegamento non e' cliccabile (FR-014).
- [x] T050 [P] Inserimento del collegamento dall'editor.
- [x] T051 [P] Test: collegamento cliccabile nel PDF; `javascript:` rifiutato
      (gia' coperto da T007, qui verificato dal percorso dell'editor).
      *T049-T051 fatti 2026-10-01*: nel PDF il collegamento e' cliccabile, blu
      e sottolineato, e il testo resta quello scritto. Nell'editor: pulsante
      nella toolbar, indirizzo in una barra sotto (resta fissa con la
      toolbar); email -> `mailto:`, `www.` -> `https://`, ogni altro schema
      rifiutato nel browser e dal servizio.

---

## Phase 8: Polish e trasversali

- [x] T052 Aggiornare la documentazione pubblica del formato documentale alla
      forma a frammenti. Un riusante che legga la documentazione attuale
      troverebbe descritta una struttura che non esiste piu' (Principio VI).
- [x] T053 Includere la licenza OFL del font nel repository e citarla dove si
      elencano le dipendenze di terze parti (Principio VI).
      *T052-T053 fatti 2026-10-01*: pagina pubblica `docs/formato-documentale.md`
      (nel menu MkDocs) con la forma attuale, la 003 rimanda li' dove
      descrive `contenuto`; la licenza OFL e' gia' in
      `backend/app/generazione/fonts/OFL.txt` ed e' citata nella tabella dei
      componenti di terze parti di `docs/open-source-pa-readiness.md`.
      Nota: `mkdocs build --strict` (pages.yml) fallisce per 15 link relativi
      preesistenti delle spec verso `../../docs/`, non introdotti qui.
- [x] T054 **Decidere se registrare un evento di audit per l'anteprima**
      (Principio V). Non e' una generazione e non compare nell'elenco di eventi
      della costituzione, quindi registrarla o no e' una scelta da prendere e
      motivare, non un'omissione da lasciare implicita.
      *Deciso 2026-10-01: nessun evento.* L'anteprima non cambia stato, non
      produce un documento e non lascia nulla da ricostruire; registrarla
      mescolerebbe consultazioni ai fatti del modello. Motivato nella
      docstring di `BuilderService.anteprima`, verificato da T037 (nessun
      evento in `audit_evento_modello`). Rivedibile se l'ente vuole sapere chi
      ha guardato cosa.
- [x] T055 [P] Aggiornare `docs/quality-coverage-matrix.yaml` per FR-001..FR-017.
      *Fatto 2026-10-01*: COV-102..118, COPERTO solo con un test eseguito;
      FR-011, FR-013, FR-014 DA_COPRIRE con il task che li chiude. Aggiunte
      anche COV-119/120 per 007 FR-035/FR-036, scoperti dal 2026-09-24: la
      CI (`check-coverage-matrix.py`) era gia' rossa per quei due.
- [x] T056 Eseguire [quickstart.md](./quickstart.md) per intero sullo stack
      reale, database pulito, e registrare l'esito di ciascun SC.
      *Esito 2026-10-01, stack reale e database pulito (e2e 4/4, backend 496,
      frontend 172)*:
      - **SC-001** (bando ricomponibile): parti automatizzate verdi - visto
        con enfasi, art. 3 con commi e lettere, firma; il confronto a occhio
        col bando reale e' T057, del product owner.
      - **SC-002** (nessuna sintassi): verde - l'e2e compone l'art. 3 solo con
        tastiera e pulsanti; T031 prova la rinumerazione.
      - **SC-003** (anteprima = PDF finale): verde - corpo identico frammento
        per frammento (backend), anteprima e documento differiscono solo nei
        valori (e2e).
      - **SC-004** (migrazione senza cambi di testo): verde in prova generale
        (T011); da eseguire in produzione.
      - **SC-005** (markup rifiutato): verde - `test_formato_frammenti.py`,
        anche dal percorso dell'editor per i collegamenti (T051).
      - **SC-006** (caratteri tipografici): verde - `test_sc006...` e l'e2e
        con le virgolette curve di Word.
- [ ] T057 **SC-001, la verifica che non si automatizza**: ricomporre nell'editor
      le tre parti del bando 367.501 CTER indicate nel quickstart e confrontarle
      col bando reale, che resta agli atti dell'ente. Non ne esiste una versione
      nel repository, ed e' corretto cosi': e' materiale illustrativo.

---

## Dependencies

```text
Phase 1 Setup
    v
Phase 2 Foundational  ← blocca tutto
    v
    +-- Phase 3 US1 (enfasi) ---+
    |                           |
    +-- Phase 4 US2 (articolato)+--> Phase 5 US4 (anteprima)
    |                           |
    +-- Phase 6 US3 (cornice) --+   indipendente, parallelizzabile
                                v
                            Phase 7 US5 (collegamenti)
                                v
                            Phase 8 Polish
```

- **US1 e US2 non dipendono l'una dall'altra**: entrambe dipendono dalla Phase 2.
- **US3 e' il percorso piu' indipendente**: tocca il tipo documento, non
  l'editor del modello. Puo' procedere in parallelo a US1/US2.
- **US4 dipende da cio' che c'e' da vedere**, quindi conviene dopo US1+US2, ma
  tecnicamente ha bisogno solo della Phase 2.

## Parallel execution

- Phase 2: T004+T006 insieme; poi T008, T012 (test), T018 sono `[P]`.
- Phase 3: T021 e T024 in parallelo al lavoro su T019/T020/T022.
- Phase 4 e Phase 6 sono due filoni che possono procedere in parallelo, su file
  diversi (`builder/` contro `configurazione/`).

## Implementation Strategy

**Il primo momento in cui si vede qualcosa** e' la fine della Phase 3: un
"visto" reale, con la sua enfasi, che arriva nel PDF. E' l'MVP di questa
feature e vale da solo.

**Il primo momento in cui si puo' giudicare** e' la fine della Phase 5: da li'
l'anteprima rende visibile il risultato senza dover pubblicare, e SC-001
diventa una verifica che si puo' ripetere invece di un collaudo finale.

**Una regola per la Phase 2**: T011 (il confronto SC-004) va eseguito **prima**
di applicare la migrazione in qualunque ambiente che contenga versioni
pubblicate, non dopo per confermare che sia andata bene.

---

## Da valutare: riscontri dall'uso sul server (2026-10-01)

Osservazioni del product owner provando l'editor in test online. Accolte il
2026-10-01 con le proposte indicate; per T062 scelto il nome libero, per T064
il comando `/` (le colonne a scorrimento indipendente restano non fatte).

*Fatto 2026-10-01*: menu "Stile" nella toolbar (Paragrafo, Titolo d'articolo,
Titolo 1/2, tre elenchi, Firma) e pulsante interruzione di pagina; Proprieta'
solo della sezione, con nome modificabile e controllo di unicita'; pannello
Blocchi tolto; sezione nuova con una riga vuota e il cursore dentro;
interruzione su riga vuota messa prima della riga, altrimenti dopo il blocco
con una riga nuova; comando `/` in `MenuSegnapostoComponent` (non si apre dentro
una parola, Esc lascia la `/`, il segnaposto eredita l'enfasi); toolbar fissa
dai 768 px in su. Test di componente riscritti sulla nuova interfaccia (162);
l'e2e inserisce il segnaposto con `/`, sceglie il titolo dal menu Stile,
verifica la toolbar dopo lo scorrimento e rinomina la sezione.

### Sezioni e blocchi: cosa agisce su cosa

- [x] T058 **Proprieta' sembra della sezione ma agisce sul blocco.** In cima
      "Titolo sezione", sotto "Stile blocco" e "Tipo blocco", che cambiano
      solo il blocco col cursore senza dire quale. Proposta: Proprieta' solo
      della sezione (nome, segnaposto usati, elimina); tutto cio' che riguarda
      il testo nella toolbar.
- [x] T059 **Due modi di fare un titolo**: "Tipo: Titolo d'articolo" e lo
      "Stile H1/H2", in toolbar e nel pannello. Proposta: un solo menu "Stile"
      nella toolbar, come in Word (Paragrafo, Titolo d'articolo, Sottotitolo,
      Elenco numerato, Elenco puntato, Firma), che mostra lo stile del punto in
      cui si e' e lo cambia li'; accanto "Inserisci" per interruzione e firma.
- [x] T060 **La sezione nuova nasce con un paragrafo vuoto** che resta sopra se
      si vuole iniziare con un titolo. Proposta: scegliere uno stile su una
      riga vuota la trasforma; inserire un blocco stando su una riga vuota la
      sostituisce invece di aggiungersi dopo.
- [x] T061 **Il pannello Blocchi ripete l'editor.** "Nel testo" duplica
      l'inserimento; i "Predefiniti" (Oggetto, Premesse, Dettaglio) sono resti
      del prototipo 2b con testo d'esempio. Proposta: togliere entrambi e
      lasciare il pannello alla biblioteca dei "visti" (futura 013).
- [x] T062 **Nome della sezione personalizzabile** ("Premesse", "Art. 1 -
      Oggetto del bando") al posto di `sezione-N`, mostrato nella struttura a
      sinistra. Il backend accetta gia' un `codice` libero fino a 128
      caratteri: basta renderlo modificabile con controllo di unicita', senza
      migrazione. Domanda aperta: nome libero, oppure legato in automatico al
      titolo d'articolo che la sezione contiene?

### Ergonomia del foglio

- [x] T063 **Toolbar sempre visibile scorrendo.** Oggi pagina, toolbar e
      colonne scorrono insieme: in un bando di 15 pagine la toolbar sparisce
      dopo il primo schermo. Da valutare `position: sticky` della topbar e
      della toolbar (va verificata la resa a 390 px, dove la toolbar va a capo
      su piu' righe e occuperebbe meta' schermo).
- [x] T064 **Segnaposto lontani dal punto in cui si scrive.** La lista sta
      nella colonna destra, che scorre con la pagina: per inserire un
      segnaposto a fondo documento bisogna risalire. Due strade da valutare,
      non esclusive:
      - **comando `/`** nell'editor: digitando `/` al cursore si apre l'elenco
        dei segnaposto, filtrabile scrivendo, e Invio inserisce quello scelto.
        Non tocca il layout; attenzione a non intercettare una `/` scritta come
        testo (date, "e/o"): il menu deve chiudersi con Esc e lasciare la `/`;
      - **colonne a scorrimento indipendente**: il foglio scorre, le colonne
        laterali restano ferme e scorrono per conto loro. Risolve anche
        T063 per la struttura a sinistra; su schermi stretti le colonne sono
        gia' impilate e il problema resta.

### Cornice rivista (riscontro del 2026-10-01 dopo la prova sul server)

Decisione del product owner (spec.md, chiarimento "Chi imposta la cornice").

- [x] T065 Formato: `IntestazionePagina` e `PiePagina` indipendenti con
      `maschera`; migrazione 0026 che converte la forma precedente e aggiunge
      `tipo_documento.logo_cornice`.
- [x] T066 Logo caricato dall'interfaccia: PNG/JPEG, al massimo 1 MB,
      verificato e ricodificato in PNG; lettura e rimozione.
- [x] T067 Rotte sotto `/builder/integrazioni/{id}/tipi-documento/{codice}/cornice`
      per il gestore del contesto e l'amministratore; quelle solo-admin sotto
      `/configurazione` si tolgono.
- [x] T068 Renderer: maschera "logo al centro, testo sotto"; spazio della
      testata calcolato da cio' che contiene.
- [x] T069 Pagina *Contesti -> <contesto> -> Impostazioni modelli*: tipi
      documento del contesto, e per ciascuno intestazione e pie' di pagina con
      scelta della maschera, logo, testo.
- [x] T070 Editor: scheda laterale "Intestazione e pie' di pagina" con la
      cornice del tipo del modello, o "Aggiungi intestazione/pie' di pagina";
      sul foglio la cornice vera al posto dell'intestazione e della firma finte
      del prototipo (FR-008).
      *T065-T070 fatti 2026-10-01*. Migrazione 0026 (conversione della forma
      precedente, colonna `logo_cornice`), logo verificato e ricodificato
      (`app/documentale/logo.py`: PNG/JPEG, 1 MB, 4000 px), rotte nel builder
      per gestore del contesto e admin (contratto 002 0.10.0; tolte da 010,
      ora 0.5.0), renderer con testata ad altezza calcolata. Interfaccia:
      *Contesti -> <contesto> -> Impostazioni modelli*, pagina con maschere,
      logo, testi e anteprima dal vivo (la stessa raggiunta dall'admin da
      Impostazioni); nell'editor scheda "Pagina" e cornice vera sul foglio,
      con "+ Aggiungi intestazione/pie' di pagina" se manca. Test: backend
      `test_cornice_api.py` (gestore sì, altro contesto no, logo nel PDF,
      file non immagine rifiutato), `test_cornice_pagina.py`,
      `test_migrazione_cornice_0026.py`; frontend `cornice-tipo`,
      `impostazioni-modelli`, editor; e2e con logo caricato e verificato nel
      PDF. `pillow` e `pypdf` diventano dipendenze dichiarate: `pypdf` mancava
      nell'immagine di produzione (`--no-dev`) e lo script di SC-004 non
      sarebbe partito.

### Riscontri del 2026-10-02 (ricomponendo il bando 367.501)

- [x] T071 **Testo copiato da PDF spezzato in un blocco per riga.** Il PDF
      mette un a capo a ogni riga visiva e l'incolla lo trattava come un
      capoverso: il titolo di cinque righe diventava cinque blocchi, non
      selezionabili insieme (ogni blocco e' un'area di scrittura a se', e il
      browser non estende una selezione da un'area all'altra). Ora le righe si
      uniscono finche' una non chiude la frase (`. ; : ! ?`), arriva una riga
      vuota, una voce di elenco, o un titolo tutto maiuscolo lascia il posto a
      testo normale; le parole spezzate col trattino si ricuciono. Limite
      noto: due righe maiuscole senza riga vuota fra loro si uniscono; si
      dividono con Invio. Test in `frammenti.spec.ts` sul testo del bando reale.
- [x] T072 **Ctrl+Z non funzionava.** Ogni riscrittura da programma (enfasi,
      incolla, Invio, segnaposto) azzerava la cronologia del browser, e
      dividere o unire blocchi non ci entrava mai. Ora l'editor ha la sua
      cronologia: stato del documento prima di ogni modifica, digitazione
      raggruppata (meno di un secondo fra due battute), Ctrl/Cmd+Z, Ctrl/Cmd+
      Maiusc+Z o Ctrl+Y, pulsanti nella toolbar, fino a 200 passi; si azzera
      quando si ricarica la versione. Test di componente ed e2e in Chromium.

### Editor a sezione unica con ProseMirror (decisione del 2026-10-02)

Riscontro: dentro una sezione non si puo' selezionare piu' di un capoverso alla
volta, perche' ogni blocco e' un'area di scrittura separata e il browser non
estende una selezione da un'area all'altra. Non e' correggibile restando cosi':
il product owner ha scelto di sostituire l'interno dell'editor con
**ProseMirror** (MIT), un editor per sezione che contiene tutti i suoi blocchi.
Resta uguale tutto cio' che sta fuori dall'editor: formato salvato, backend,
PDF, anteprima, cornice, toolbar, menu Stile, comando `/`.

La selezione si ferma al bordo della sezione, per scelta: il product owner
intende la sezione (per esempio "Art. 1") come un'unita' che in futuro si potra'
salvare e riusare fra modelli, con una categorizzazione ancora da definire
(fuori da questa spec). Una toolbar sola, sopra il foglio, agisce sulla
sezione in cui sta il cursore.

- [x] T073 Schema ProseMirror sul formato: `paragrafo` (allineamento, stile
      H1/H2), `titolo`, `firma`, `elenco` di `voce` (livello 0/1, marcatore),
      `interruzione`, `blocco_riservato` (tipi non gestiti, conservati
      intatti); marchi grassetto, corsivo, sottolineato, collegamento.
- [x] T074 Conversione blocchi <-> documento ProseMirror, con identificativi
      dei blocchi stabili e unici; test di andata e ritorno.
- [x] T075 Componente editor di sezione: tastiera (Invio, Maiusc+Invio, Tab
      sulle voci, uscita da un elenco), annulla del builder, incolla tramite
      `convertiAppunti`, comando `/`, collegamenti.
- [x] T076 Toolbar e menu Stile come comandi sulla selezione, anche su piu'
      blocchi; numerazione delle voci calcolata con le regole del PDF e
      disegnata fuori dal testo.
- [x] T077 Integrazione nella schermata 2b al posto degli editor per blocco;
      test di componente ed e2e riscritti; selezione e formattazione di piu'
      capoversi insieme verificate nel browser vero.

  Verifica del 2026-10-02: 184 test di componente e unita' (14 nuovi su schema
  e comandi, fra cui grassetto su titolo, capoversi ed elenco con una sola
  selezione, e testo incollato riselezionato intero); e2e `builder-lifecycle`
  su stack reale con il caso del riscontro (incolla da Word, Ctrl+A nella
  sezione, grassetto su tutto, Ctrl+Z), anteprima, pubblicazione e
  generazione con le verifiche sul PDF; build di produzione e immagini Coolify.
  Le scorciatoie valgono con Ctrl anche su Mac, come prima. Annulla e ripeti
  restano del builder (non la cronologia di ProseMirror), vedi research.md R9.

### Righe da PDF, foglio A4 e fogli visibili (riscontro del 2026-10-02, sera)

Riscontro sul server di test, versione 36: la sezione dei visti non si
giustificava. Causa nei dati: 118 capoversi di una riga ciascuno, uno per
ogni riga del PDF (incollati con l'editor per blocco), e una riga sola e'
l'ultima del suo capoverso, che il giustificato non allarga. Il product owner
chiede anche un foglio largo quanto la colonna e di vedere dove finisce ogni
pagina, per sapere quanto spazio prende cio' che si incolla.

- [x] T078 Il foglio dell'editor e' un A4 in scala (`--foglio-mm`, container
      query): 190 mm di testo su 210, corpo 11 pt con interlinea 1,35 e 2 mm
      dopo il capoverso, le stesse misure di `renderer.py`, cosi' che le righe
      vadano a capo dove ci vanno nel PDF. Usa tutta la colonna centrale fino a
      1060 px.
- [x] T079 "Unisci righe" (¶ nella toolbar): ricompone in capoversi le righe
      selezionate, con la stessa regola dell'incolla da PDF (`gruppiDiRighe`,
      ora condivisa); l'enfasi resta, le voci d'elenco restano voci e prendono
      il loro seguito. La regola diventa piu' precisa: una riga che chiude con
      un punto non chiude il capoverso se la successiva comincia in minuscolo
      o con una cifra ("n. 93 prot." / "0051080/2018").
- [x] T080 Dove comincia ogni pagina, misurato dal renderer:
      `GET .../versioni/{id}/impaginazione` (contratto 002 0.11.0) rende la
      bozza come l'anteprima e annota, per ogni pagina dopo la prima, sezione,
      blocco, voce e righe rimaste sopra. L'editor la chiede al caricamento e
      dopo ogni salvataggio e disegna "Pagina N" sulla riga giusta; in cima al
      foglio dice quante pagine ha il PDF.

  Verifica del 2026-10-02: test del renderer sul PDF vero (pagina, blocco e
  righe annotati corrispondono al testo estratto), API su PostgreSQL vero
  (pagine = pagine del PDF dell'anteprima, 409 sulle pubblicate, 403 a chi
  genera), 512 test backend, 188 frontend; e2e su stack reale con le 117 righe
  dei visti della versione 36: incollate una per capoverso, ricomposte con
  "Unisci righe", giustificate, salvate; i fogli disegnati sono tanti quante le
  pagine del PDF dell'anteprima. La posizione dentro un capoverso spezzato fra
  due pagine dipende dal fatto che browser e PDF vadano a capo nello stesso
  punto: con le stesse misure e lo stesso carattere succede quasi sempre, ma
  e' la riga del PDF, non quella dello schermo, a fare fede.

- [x] T081 I fogli seguono cio' che si scrive (riscontro del 2026-10-02: il
      confine di pagina scendeva insieme al testo spostato, invece di restare
      fermo sul foglio). `impaginazione` diventa `POST` e accetta le sezioni
      dello schermo, non salvate, senza scriverle; l'editor le manda dopo 400 ms
      di pausa a ogni modifica, e una misura vecchia non sostituisce mai quella
      nuova. Nello stesso giro: capoversi e voci hanno il corpo del PDF
      (Bootstrap Italia dava ai `<p>` 18 px e un'interlinea fissa), e il testo
      col cursore non ha piu' la cornice nera di focus di Bootstrap Italia.

  Verifica: test API (le sezioni inviate si misurano e non si salvano; il
  markup e' rifiutato come al salvataggio); e2e con cinque righe vuote in cima
  ai visti: il confine resta entro una riga dal punto in cui era sul foglio;
  corpo dei capoversi uguale a quello delle voci; nessuna cornice di focus.

