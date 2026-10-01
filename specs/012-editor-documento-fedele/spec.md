# Feature Specification: Editor documentale fedele al provvedimento reale

**Feature Branch**: `012-editor-documento-fedele`

**Created**: 2026-09-29

**Status**: Draft

**Input**: User description: "sviluppare il builder in modo che sia il piu' vicino
possibile a un Word, perche' gia' con l'impostazione attuale si veda come verra'
il documento, e dopo con l'anteprima si veda effettivamente come verrebbe il PDF
generato. Esempio di riferimento: bando CNR n. 367.501 CTER."

**Documento di riferimento**: `BANDO 367.501 CTER gare e contratti pubblici_signed.pdf`
(15 pagine, CNR, firmato 22/07/2025). Non e' un esempio inventato: e' un bando
realmente pubblicato, **composto oggi a mano in Word**. Serve percio' a due
cose insieme: mostra come il lavoro viene svolto adesso, e fissa il livello che
il builder deve raggiungere perche' valga la pena sostituire quel Word.

E' materiale illustrativo, non un artefatto che il repository debba
conservare: chi verifica SC-001 confronta il documento ricomposto
nell'editor con il bando reale, che resta agli atti dell'ente.

## Perche' questa spec esiste

Il builder oggi compone documenti fatti di **paragrafi di testo semplice**. Il
bando reale non e' fatto cosi'. Confrontando il documento di riferimento con il
formato documentale attuale (`app/documentale/schemas.py`, blocchi tipizzati con
`contenuto` testuale) emergono elementi che **non sono rappresentabili**:

| Elemento del bando reale | Oggi |
|---|---|
| `**VISTO** il D.Lgs 127/2003 *"Riordino del CNR"*` - grassetto e corsivo **dentro lo stesso paragrafo** | non rappresentabile: il blocco ha un solo testo, senza enfasi |
| Elenchi numerati `1. 2. 3.` con annidati `a) b) c)` e spunte `✓` | non rappresentabile |
| `Art. 1 - Posti a concorso` centrato, `D E C R E T A` centrato | il posizionamento esiste, ma l'editor non lo espone |
| Logo CNR in testa a **ogni** pagina, numero di pagina in fondo a ogni pagina | i tipi `LOGO`/`FOOTER` esistono come blocchi singoli, non come cornice ricorrente |
| Testo giustificato | non esprimibile |
| Collegamenti (`inpa.gov.it`, indirizzi PEC) | non rappresentabili |
| Blocco firma in fondo, allineato a destra | il tipo `FIRMA` esiste, l'editor non lo crea |

I circa quaranta "visti" del bando sono **tutti** del primo tipo: parola chiave
in grassetto, poi testo con i titoli di legge in corsivo. Senza enfasi dentro il
paragrafo, quella parte del bando - la piu' voluminosa - non si puo' comporre.

C'e' anche una conseguenza gia' visibile oggi, che questa spec chiude: la
toolbar dell'editor offre H1/H2, ma il renderer PDF non legge quell'attributo.
Chi compone vede un titolo e ottiene un paragrafo qualunque.

## Clarifications

### Session 2026-09-29

- Q: Come si rappresenta l'enfasi dentro un paragrafo, dato che HTML e CSS
  liberi restano vietati? → A: **Frammenti tipizzati**. Il paragrafo diventa
  una sequenza ordinata di frammenti, ognuno con i propri attributi di enfasi.
  Sono dati, non sintassi: nessun carattere speciale da proteggere, nessun
  interprete da difendere, e il divieto del Principio III resta intatto senza
  eccezioni. E' anche la forma su cui si mapperebbe un futuro export `.docx`.
- Q: La cornice di pagina appartiene al tipo documento o al singolo modello? →
  A: **Al tipo documento**. Il logo e' unificato per tutti i documenti CNR; i
  testi di intestazione (ufficio e simili) possono differire da un tipo
  documento all'altro, ma non da un modello all'altro. Un'eventuale eccezione
  per singolo modello e' rinviata: aggiungerla dopo e' additivo (un
  sovrascrittura opzionale su una cornice che gia' esiste), non una
  riprogettazione.
- Q: La numerazione di commi e lettere e' generata dal sistema o scritta dal
  gestore? → A: **Automatica**. L'elemento di lista porta solo il livello e il
  tipo di marcatore; il numero lo calcola il renderer, e riparte dentro ogni
  articolo.
- Q: Il numero dell'articolo ("Art. 1", "Art. 2") si aggiorna da solo se si
  inserisce un articolo in mezzo? (2026-10-01) → A: **No, per ora resta scritto
  a mano** nel testo del `TITOLO`; si valuta dopo l'uso. La numerazione
  automatica copre commi e lettere (FR-015), non gli articoli. Aggiungerla dopo
  e' additivo: le intestazioni hanno la forma regolare `Art. N - Rubrica`, che
  una migrazione puo' riconoscere e convertire. Restano fuori in ogni caso i
  rinvii nel testo ("ai sensi dell'art. 4 comma 2"), che sono testo e non
  seguono una rinumerazione.
- Q: Che peso ha l'incolla da Word, dato che il bando oggi si compone a mano in
  Word? → A: **Incolla di base dentro US1**, non rifinitura. Si conservano
  enfasi, capoversi ed elenchi; colori, font, rientri, immagini e tabelle si
  scartano. La conversione avviene **nel browser**: al backend arrivano
  frammenti, mai HTML. Serve perche' e' con l'incolla che si popolera' la
  biblioteca dei "visti" (futura spec `013`) la prima volta - dopodiche' i
  visti si pescano da li' e l'incolla torna una comodita'.
- Q: I paragrafi gia' salvati come stringa semplice come convivono con il nuovo
  formato? → A: **Convertiti una volta**, con una migrazione, in un unico
  frammento senza enfasi. Stesso testo, quindi stesso documento generato; ma da
  quel momento nel sistema esiste **una sola** forma di paragrafo, non due
  strade di rendering che possono divergere - che e' esattamente il difetto
  gia' visto con H1/H2.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Enfasi dentro il testo (Priority: P1)

Il gestore scrive un "visto": la parola `VISTO` in grassetto, il titolo della
legge in corsivo, il resto normale - tutto dentro lo stesso capoverso,
selezionando le porzioni come farebbe in Word.

**Why this priority**: e' il volume del bando. Senza questo non si compone la
parte normativa, che sono quaranta paragrafi su quindici pagine. Ed e' l'unica
funzione per cui oggi i pulsanti esistono **disabilitati**: chi apre l'editor
vede B/I/U spenti e non capisce perche'.

**Independent Test**: comporre un singolo "visto" del bando di riferimento,
pubblicarlo e verificare che il PDF riporti grassetto e corsivo dove servono.
Vale da solo, anche senza liste e senza cornice di pagina.

**Acceptance Scenarios**:

1. **Given** un paragrafo con una porzione selezionata, **When** il gestore
   applica il grassetto, **Then** solo quella porzione risulta in grassetto,
   nell'editor e nel PDF generato.
2. **Given** un paragrafo con grassetto e corsivo su porzioni diverse,
   **When** il documento viene generato, **Then** entrambe le enfasi
   sopravvivono e il resto del testo resta normale.
3. **Given** un segnaposto dentro una porzione in grassetto, **When** GEBAN
   fornisce il valore, **Then** il valore sostituito **eredita** il grassetto e
   la sostituzione non spezza il paragrafo.
4. **Given** un modello pubblicato prima di questa funzione, **When** viene
   generato, **Then** produce esattamente il documento di prima.
5. **Given** un "visto" copiato da un documento Word, **When** il gestore lo
   incolla nell'editor, **Then** grassetto e corsivo sono conservati, la
   formattazione non rappresentabile e' scartata, e nulla di cio' che viene
   inviato al servizio e' markup.

### User Story 2 - Struttura dell'articolato (Priority: P1)

Il gestore costruisce gli articoli: intestazione dell'articolo centrata, commi
numerati, lettere annidate, testo giustificato.

**Why this priority**: e' l'altra meta' del bando. Un provvedimento senza
articoli numerati non e' un provvedimento; e la numerazione e' cio' a cui il
testo stesso si riferisce ("ai sensi dell'art. 4 comma 2 lett. c").

**Independent Test**: ricostruire l'art. 3 del bando di riferimento - commi
numerati con lettere annidate - e verificarne la resa nel PDF.

**Acceptance Scenarios**:

1. **Given** un articolo con tre commi, **When** il gestore inserisce un comma
   in mezzo, **Then** la numerazione resta coerente in tutto l'articolo.
2. **Given** un comma con un elenco a lettere, **When** il documento viene
   generato, **Then** l'annidamento e il rientro sono visibili nel PDF.
3. **Given** un'intestazione di articolo, **When** viene generata, **Then**
   risulta centrata e in evidenza, distinta dal corpo.

### User Story 3 - Cornice della pagina (Priority: P2)

Logo istituzionale in testa a ogni pagina, numero di pagina in fondo,
interruzioni di pagina volute, blocco firma in chiusura.

La storia ha **due attori distinti** (FR-011): logo e piè di pagina li
configura l'amministratore una volta sul tipo documento; interruzione di pagina
e blocco firma restano nelle mani del gestore, dentro l'editor, perche'
dipendono da dove cade il contenuto di quel singolo documento.

**Why this priority**: senza, il documento e' leggibile ma non e' un atto:
manca l'identita' dell'ente e la numerazione che rende citabile una pagina.
Sta dopo US1 e US2 perche' il contenuto viene prima della cornice.

**Independent Test**: generare un documento di piu' pagine e verificare che
logo e numero compaiano su tutte, non solo sulla prima.

**Acceptance Scenarios**:

1. **Given** un documento di tre pagine, **When** viene generato, **Then**
   logo e numero di pagina compaiono su ciascuna.
2. **Given** un'interruzione di pagina inserita dal gestore, **When** il
   documento viene generato, **Then** il contenuto successivo inizia su una
   pagina nuova.
3. **Given** un blocco firma, **When** il documento viene generato, **Then**
   compare in chiusura, allineato a destra.

### User Story 4 - Anteprima fedele del PDF (Priority: P2)

Prima di pubblicare, il gestore chiede l'anteprima e vede il PDF che verrebbe
generato, con valori fac-simile al posto dei segnaposto.

**Why this priority**: e' il controllo finale, ma soprattutto e' cio' che
rende verificabile tutto il resto. Oggi il pulsante "Anteprima" scorre la
pagina e basta, e il foglio dell'editor e il renderer PDF sono **due
implementazioni diverse** che possono divergere senza che nessuno se ne
accorga - ed e' gia' successo con H1/H2.

**Independent Test**: aprire l'anteprima di una bozza e confrontarla con il PDF
generato dopo la pubblicazione: struttura, ordine, enfasi e numerazione devono
coincidere.

**Acceptance Scenarios**:

1. **Given** una versione in bozza, **When** il gestore chiede l'anteprima,
   **Then** riceve un PDF con valori fac-simile, marcato come tale.
2. **Given** un'anteprima richiesta, **When** viene prodotta, **Then** **non**
   risulta alcun documento generato ne' viene consumata l'idempotenza: e'
   un'anteprima, non una generazione.
3. **Given** la stessa versione pubblicata e generata con dati veri, **When**
   si confrontano i due PDF, **Then** differiscono solo per i valori.

### User Story 5 - Collegamenti (Priority: P3)

Il gestore inserisce collegamenti a portali e indirizzi PEC.

**Why this priority**: il bando reale ne contiene diversi, ma un collegamento
non cliccabile resta leggibile come testo. E' la perdita piu' tollerabile.

**Independent Test**: inserire un collegamento e verificare che sia cliccabile
nel PDF e leggibile comunque se il lettore non li supporta.

### Edge Cases

- **Segnaposto dentro una porzione formattata**: la sostituzione deve
  conservare l'enfasi e non spezzare il frammento. Vale anche per un segnaposto
  a cavallo fra due porzioni con enfasi diverse.
- **Lista che prosegue oltre l'interruzione di pagina**: la numerazione continua,
  non riparte.
- **Caratteri tipografici italiani**: il bando reale usa virgolette curve,
  apostrofi tipografici e trattini lunghi. Devono arrivare nel PDF invariati,
  non trasformati in `?` o rimossi.
- **Documento lungo**: il riferimento e' 15 pagine con ~40 paragrafi normativi e
  20 articoli. Non e' un caso limite teorico: e' la dimensione normale.
- **Modelli pubblicati prima di questa funzione**: continuano a generare lo
  stesso identico documento. Il Principio IV lo impone e non e' negoziabile.
- **Enfasi annidate** (grassetto e corsivo insieme sulla stessa porzione).
- **Un gestore incolla testo da Word**: cosa entra e cosa viene scartato deve
  essere prevedibile, e non deve poter introdurre markup arbitrario. Non e' un
  caso raro: e' il modo in cui il contenuto esistente entra la prima volta,
  perche' i bandi oggi si scrivono in Word. Coperto da FR-017, dentro US1.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Il formato documentale MUST poter rappresentare enfasi
  (grassetto, corsivo, sottolineato) su **porzioni** di un paragrafo, non solo
  sul paragrafo intero. La rappresentazione MUST essere una **sequenza
  ordinata di frammenti**, ciascuno con il proprio testo e i propri attributi
  di enfasi; il testo di un frammento MUST essere testo puro, privo di
  qualunque sintassi di marcatura.
- **FR-002**: Il formato MUST restare chiuso: nessun HTML ne' CSS libero
  accettato, con la stessa forza di oggi. Un contenuto che tenta di
  introdurre markup MUST essere rifiutato alla scrittura, non ripulito in
  silenzio. Nessun carattere del testo di un frammento MUST assumere
  significato speciale: il formato non introduce alcun linguaggio di
  marcatura, nemmeno ridotto.
- **FR-003**: Il formato MUST poter rappresentare elenchi numerati e puntati
  con **almeno due livelli** di annidamento.
- **FR-015**: La numerazione degli elenchi MUST essere **generata in fase di
  resa**, non scritta nel contenuto: l'elemento di lista dichiara il proprio
  livello e il tipo di marcatore (numerico, alfabetico, puntato), mai il numero
  gia' calcolato. La numerazione MUST ripartire all'inizio di ogni articolo.
- **FR-004**: Il formato MUST poter esprimere l'allineamento del testo, incluso
  il giustificato.
- **FR-005**: La sostituzione dei segnaposto MUST conservare l'enfasi della
  porzione che li contiene.
- **FR-006**: L'editor MUST permettere di applicare enfasi, elenchi e
  allineamento **selezionando il testo**, senza che il gestore scriva alcuna
  sintassi.
- **FR-007**: L'editor MUST poter creare tutti i tipi di blocco che il
  documento richiede, non solo paragrafi, e MUST mostrare **tutti** i blocchi
  di una sezione, non soltanto il primo.
- **FR-008**: Cio' che l'editor mostra e cio' che il PDF produce MUST
  corrispondere per struttura, ordine, enfasi e numerazione. Dove la
  corrispondenza non e' possibile, l'editor MUST dirlo invece di mostrare un
  risultato che il PDF non riprodurra'.
- **FR-009**: Il sistema MUST produrre un'anteprima PDF di una versione in
  **bozza**, con valori fac-simile al posto dei segnaposto e marcata come
  anteprima.
- **FR-010**: L'anteprima MUST NOT registrare un documento generato, MUST NOT
  consumare l'idempotenza e MUST NOT richiedere i permessi di generazione: e'
  un'azione di chi compone, non di chi genera.
- **FR-011**: Il documento MUST poter dichiarare una cornice di pagina - logo,
  intestazione, piè di pagina con numero - che si ripete su **ogni** pagina.
  La cornice MUST appartenere al **tipo documento**, non al singolo modello: si
  configura una volta, e il gestore del modello non la compone ne' la puo'
  sbagliare. Il logo MUST essere lo stesso per tutti i documenti dell'ente; i
  testi di intestazione MUST poter differire fra tipi documento diversi.
- **FR-012**: Il gestore MUST poter inserire un'interruzione di pagina
  esplicita.
- **FR-013**: I modelli gia' pubblicati MUST generare lo stesso **documento
  visibile** di prima di questa funzione: stesso testo, stesso ordine dei
  blocchi, stessa impaginazione. (Non si richiede identita' dei file: un PDF
  contiene data di produzione e identificatori interni che cambiano a ogni
  generazione.)
- **FR-017**: L'editor MUST accettare testo incollato da un elaboratore di
  testi conservandone enfasi, capoversi ed elenchi, e scartando tutto il resto
  in modo **prevedibile**. La conversione MUST avvenire prima dell'invio al
  servizio: il contenuto trasmesso MUST essere gia' nella forma a frammenti,
  mai markup. I marcatori di elenco scritti come testo (`1.`, `a)`) MUST essere
  rimossi quando l'elenco viene riconosciuto, per non sommarsi alla numerazione
  generata (FR-015).
- **FR-016**: I paragrafi gia' salvati in forma testuale MUST essere convertiti
  una volta sola in un frammento unico privo di enfasi. Il formato MUST
  ammettere **una sola** rappresentazione del paragrafo: nessun percorso di
  resa alternativo per i contenuti preesistenti.
- **FR-014**: Il documento MUST poter contenere collegamenti ipertestuali, che
  restano leggibili come testo dove non sono cliccabili.

### Key Entities

- **Frammento di testo**: porzione di un paragrafo con il proprio testo (puro,
  senza sintassi) e i propri attributi di enfasi. E' l'entita' nuova su cui
  poggia FR-001; un paragrafo diventa una sequenza ordinata di frammenti
  invece di una stringa, e i paragrafi esistenti diventano un frammento solo
  (FR-016).
- **Elenco**: sequenza ordinata di elementi, ciascuno con un livello di
  annidamento e un tipo di marcatore (numerico, alfabetico, puntato). Il numero
  mostrato **non** e' un attributo dell'elemento: lo calcola la resa (FR-015).
- **Cornice di pagina**: gli elementi che si ripetono su ogni pagina - logo,
  intestazione, piè di pagina - distinti dai blocchi del corpo, che compaiono
  una volta sola nel punto in cui stanno. Appartiene al **tipo documento**
  (FR-011), quindi vive nella configurazione del tipo documento e non
  nell'editor del modello.
- **Blocco documentale** (esistente): si estende con allineamento ed elenco;
  il suo `contenuto` testuale diventa una sequenza di frammenti.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Il bando di riferimento (367.501 CTER) e' **ricomponibile**
  nell'editor, e il PDF generato ne riproduce struttura, enfasi, elenchi e
  numerazione. E' il criterio principale: un documento reale, non un esempio
  costruito per passare.
- **SC-002**: Un gestore che non conosce alcun linguaggio di marcatura compone
  un articolo con elenco annidato **senza scrivere sintassi**.
- **SC-003**: Anteprima e PDF finale della stessa versione coincidono per
  struttura, ordine, enfasi e numerazione; differiscono solo per i valori.
- **SC-004**: Ogni modello pubblicato prima di questa funzione genera lo stesso
  documento visibile di prima - testo, ordine dei blocchi e impaginazione
  coincidono - verificato confrontando il contenuto estratto dai due PDF, non
  i file.
- **SC-005**: Nessun contenuto con HTML o CSS libero viene accettato dal
  formato, con la stessa copertura di prova che esiste oggi.
- **SC-006**: I caratteri tipografici italiani del documento di riferimento
  arrivano nel PDF invariati.

## Assumptions

- **Fedelta' significa struttura, non pixel.** L'editor gira in un browser, il
  PDF lo produce un motore diverso: font, sillabazione e andare a capo
  differiranno. Cio' che deve coincidere e' l'ordine dei blocchi, l'enfasi,
  la numerazione e gli allineamenti. Promettere identita' tipografica sarebbe
  una promessa che non si puo' mantenere, e la prima differenza verrebbe letta
  come un difetto.
- **La biblioteca dei "visti" resta fuori da questa spec.** I quaranta
  paragrafi normativi del bando sono anche il caso d'uso dei blocchi
  riutilizzabili, gia' registrati in `docs/project-map.md` come ambito da
  specificare a parte. Questa spec rende **componibile** quel contenuto; non
  affronta come conservarlo e riusarlo fra modelli. Sono due problemi diversi e
  vanno tenuti separati.
- **L'export `.docx` resta fuori.** Il contratto non esiste e la decisione di
  prodotto non e' presa. La scelta di rappresentazione dell'enfasi (vedi
  Clarifications) ne condiziona pero' il costo futuro, e questo e' un motivo
  per preferire una forma che vi si mappi.
- **Le tabelle non sono nel bando di riferimento** - compaiono negli allegati,
  fuori dal documento principale. Il tipo `TABELLA` esiste gia' nel formato:
  questa spec non lo estende ne' lo rimuove.
- **La marcatura `DOCUMENTO DI TEST - NON UFFICIALE` resta.** ADR 0002 dice che
  un percorso di generazione ufficiale non esiste ancora, e `003` T020 vieta di
  toglierla prima. Rendere il documento fedele non lo rende ufficiale.
