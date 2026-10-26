# Feature Specification: Campi ripetibili e articolazioni del bando nel contratto dati

**Feature Branch**: `test`

**Created**: 2026-10-07

**Status**: Implementata 2026-10-26 (chiarimenti 2026-10-07 e 2026-10-26)

**Input**: User description: "Estendere la struttura nodo/foglia gia' condivisa
con GEBAN per rappresentare un documento unico che puo' ricevere piu' insiemi di
etichette omologhe, distinguendo le etichette della procedura principale da
quelle delle articolazioni/sottobandi nel builder. Mantenere invariata la forma
dei bandi singoli. Usare la grammatica gia' condivisa: `codice`, `descrizione`,
`campi`; non introdurre un secondo linguaggio `id`/`etichetta`. La segnalazione
di etichetta gia' inserita e' una miglioria futura, non in questa spec."

Riferimento consultabile per integratori e agenti: `docs/contratto-dati.md`.
Esempi JSON di questa spec: [contracts/](contracts/).

## Clarifications

### Session 2026-10-07

- Q: Le articolazioni sono un concetto riservato del contratto o un caso di una
  regola generale? → A: Caso di una regola generale. Il contratto introduce il
  **campo ripetibile**: un campo con `tipo: "array"` puo' dichiarare `campi`,
  l'elenco dei sotto-campi di ogni elemento. `articolazioni` e' solo il `codice`
  convenzionale per i bandi; un altro tipo documento puo' usare `lotti`, `sedi`
  o altro senza cambiare il contratto.
- Q: Nel discovery si elencano le articolazioni reali? → A: No. Il discovery
  dichiara la **forma** di un elemento (i sotto-campi). Le articolazioni reali,
  con `codice` e `descrizione`, esistono solo nei `dati` della richiesta di
  validazione e generazione, perche' il loro numero cambia da procedura a
  procedura.
- Q: La grammatica del campo diventa aperta? → A: No, resta chiusa. Si aggiunge
  una sola chiave (`campi`), ammessa solo sui campi di tipo `array`. Le chiavi
  sconosciute dentro un campo, oggi scartate in silenzio, diventano un errore
  esplicito di discovery non conforme; quelle che iniziano con `_` restano
  annotazioni ignorate. Verificato il 2026-10-07 sull'albero GEBAN di test
  (65 foglie, 852 campi): i campi usano solo `codice`, `etichetta`, `tipo`,
  `obbligatorio`, `ordine`, `descrizione`, quindi la regola non rompe
  l'integrazione attuale.
- Q: Quanti livelli di annidamento? → A: Uno. I sotto-campi di un campo
  ripetibile non possono essere a loro volta di tipo `array` o `object`.
  Un livello in piu' richiede una nuova versione del contratto.
- Q: Le istanze nei dati usano `etichetta`? → A: No. Ogni elemento usa
  `codice` (tecnico, unico nell'elenco), `descrizione` (leggibile) e `campi`
  (mappa codice -> valore). `etichetta` resta solo sulla dichiarazione dei campi
  nel discovery, come oggi.

### Session 2026-10-26

- Q: Tutti gli elementi di un campo ripetibile hanno gli stessi sotto-campi? →
  A: Si'. Verificato con GEBAN e il PO: le articolazioni di uno stesso bando
  hanno gli stessi sotto-campi; cambiano i valori e il numero degli elementi,
  non la forma. Le alternative discusse - etichette fisse per articolazione
  (`codice_bando_tematica_a`), sotto-campi diversi fra articolazioni (es. una
  tematica con due sedi), modello dedicato al singolo bando - restano fuori
  da questa spec.
- Q: Come il modello impagina gli elementi (FR-016)? → A: Con una **riga di
  tabella ripetuta**. Il gestore scrive nel builder una tabella con una riga
  i cui segnaposti si riferiscono all'elemento (es. codice e posti
  dell'articolazione); in generazione la riga si ripete una volta per ogni
  elemento, nell'ordine in cui arrivano nei dati. Il modello non conosce ne'
  il numero ne' i codici degli elementi.
- Q: Un modello creato da una foglia con un campo ripetibile lo usa sempre? →
  A: No. Il **modello multiplo** e' una scelta esplicita del gestore alla
  creazione, separata dal modello singolo, non un derivato (in GEMODO
  "derivato" significa altra lingua o altro livello). Il modello singolo non
  include i campi ripetibili; il modello multiplo li include e li mostra in una
  sezione evidente. Motivo: senza la distinzione ogni modello della foglia
  vedrebbe le etichette dei sottobandi, e un modello che non le usa
  accetterebbe le articolazioni senza stamparle.
- Q: Il catalogo deve dire se un modello e' multiplo? → A: Si' (rivede la
  prima risposta dello stesso giorno, data prima della decisione sul modello
  multiplo separato). Per la stessa combinazione possono esistere un modello
  singolo e uno multiplo, e chi chiama deve scegliere: la risposta porta
  `multiplo` e la ricerca accetta il filtro `multiplo`. Senza filtro il
  catalogo restituisce i soli modelli singoli, cosi' le chiamate di oggi non
  cambiano comportamento.
- Q: Le tabelle esistono gia' nel builder? → A: Solo nel formato del
  documento (`TABELLA` con `colonne`). L'editor non permette di crearle e il
  PDF le stampa come testo con le colonne separate da `|`. Questa spec
  comprende la tabella vera, nell'editor e nel PDF.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Dichiarare un campo ripetibile nel discovery (Priority: P1)

Come integratore (GEBAN o altro sistema), voglio dichiarare sulla foglia un
campo ripetibile con i suoi sotto-campi, cosi' che GEMODO sappia che una
procedura puo' contenere piu' articolazioni, ognuna con gli stessi campi, senza
appiattirli in nomi artificiali come `codice_bando_01`.

**Why this priority**: senza questa dichiarazione GEMODO vede solo un campo
`array` senza struttura e non puo' ne' mostrarne i sotto-campi ne' validarli.

**Independent Test**: una foglia che dichiara `articolazioni` con `tipo: "array"`
e `campi` supera il test di connessione; la struttura letta conserva i
sotto-campi. Una foglia senza campi ripetibili si legge come oggi.

**Acceptance Scenarios**:

1. **Given** una foglia senza campi ripetibili, **When** GEMODO legge il
   discovery, **Then** il risultato e' identico a quello del contratto 0.7.0.
2. **Given** un campo `tipo: "array"` con `campi` validi, **When** GEMODO legge
   il discovery, **Then** il campo e i suoi sotto-campi sono conservati.
3. **Given** `campi` su un campo che non e' `array`, oppure un sotto-campo di
   tipo `array`/`object`, oppure codici di sotto-campo duplicati, **When** si
   esegue il test di connessione, **Then** l'esito e' `NON_CONFORME` con il
   percorso del punto difforme.
4. **Given** una chiave sconosciuta dentro un campo (non prefissata da `_`),
   **When** si esegue il test di connessione, **Then** l'esito e'
   `NON_CONFORME` con il nome della chiave e il percorso; la chiave non viene
   piu' scartata in silenzio.

---

### User Story 2 - Mostrare etichette raggruppate nel builder (Priority: P1)

Come gestore modelli, voglio vedere le etichette della procedura principale
separate da quelle di ciascun campo ripetibile, cosi' da inserire nel modello il
campo corretto senza confonderlo con un campo omonimo.

**Why this priority**: mischiare tutte le etichette in una sola lista rende
facile inserire il campo sbagliato.

**Independent Test**: dato un modello multiplo creato da una foglia con un
campo ripetibile, il pannello delle etichette mostra un gruppo per la
procedura principale e un gruppo collassabile "Bando multiplo" per il campo
ripetibile, con le etichette dei sotto-campi; il modello singolo della stessa
foglia non mostra il secondo gruppo.

**Acceptance Scenarios**:

1. **Given** una foglia con campi principali e un campo ripetibile
   `articolazioni` e un modello creato come "Bando multiplo", **When** il
   gestore apre l'editor del modello, **Then** vede due gruppi distinti: dati
   della procedura e una sezione "Bando multiplo" con le etichette del
   sottobando.
1a. **Given** la stessa foglia e un modello creato come "Bando singolo",
   **When** il gestore apre l'editor, **Then** non vede le etichette del
   sottobando.
2. **Given** `codice_bando` presente sia fra i campi principali sia fra i
   sotto-campi, **When** il gestore consulta le etichette, **Then** i due
   compaiono nei rispettivi gruppi e non sono intercambiabili.
3. **Given** molti gruppi, **When** il gestore apre il pannello, **Then** puo'
   comprimere ed espandere i gruppi.
4. **Given** il gestore inserisce una tabella con intestazione "Codice |
   Posti | Sede" e una riga con i segnaposti dell'elemento, **When** salva,
   **Then** la riga e' marcata come ripetuta per ogni elemento di
   `articolazioni` e il modello si pubblica.
5. **Given** una riga ripetuta che contiene un segnaposto della procedura
   principale o di un altro campo ripetibile, **When** il gestore pubblica,
   **Then** la pubblicazione e' bloccata con il segnaposto e la riga
   interessati.

---

### User Story 3 - Validare e generare un documento unico (Priority: P2)

Come sistema richiedente, voglio inviare una sola richiesta con i dati della
procedura e le sue articolazioni, cosi' che GEMODO produca un unico documento.

**Why this priority**: conferma il confine funzionale: il multi-bando e' una
struttura dati dentro lo stesso documento, non una moltiplicazione del flusso.

**Independent Test**: una richiesta con due articolazioni produce un solo PDF;
una richiesta con un sotto-campo obbligatorio mancante produce un errore con il
percorso dell'elemento.

**Acceptance Scenarios**:

1. **Given** una richiesta con la procedura principale e due articolazioni,
   **When** il modello usa campi di entrambi i livelli, **Then** viene prodotto
   un solo documento.
1a. **Given** il bando 367.501 con 10 posti e tre articolazioni (2, 5 e 3
   posti), **When** si genera con un modello che ha una riga ripetuta,
   **Then** la tabella del PDF ha tre righe, nell'ordine dei dati, ciascuna
   con i valori della propria articolazione, e il totale del padre resta 10.
1b. **Given** la stessa richiesta senza articolazioni verso il modello
   multiplo, **When** si genera, **Then** l'errore e' `CAMPO_OBBLIGATORIO` su
   `articolazioni` e nessun documento viene prodotto (FR-016c).
1c. **Given** una richiesta con articolazioni verso il modello singolo della
   stessa combinazione, **When** si valida, **Then** l'errore e'
   `CAMPO_NON_AMMESSO` su `articolazioni` (FR-016g).
2. **Given** un sotto-campo obbligatorio mancante nell'articolazione `TEMA_A`,
   **When** si chiama `valida` o `genera`, **Then** l'errore ha
   `campo = "articolazioni[TEMA_A].campi.numero_posti"` e codice
   `CAMPO_OBBLIGATORIO`.
3. **Given** due elementi con lo stesso `codice`, **When** si valida, **Then**
   l'errore e' `CODICE_ELEMENTO_DUPLICATO` sul campo `articolazioni`.
4. **Given** un sotto-campo non dichiarato, **When** si valida, **Then**
   l'errore e' `CAMPO_NON_AMMESSO` con il percorso dell'elemento.
5. **Given** per TD, Collaboratore Tecnico E.R., IT, livello V sono pubblicati
   un modello singolo e uno multiplo, **When** GEBAN cerca nel catalogo senza
   il filtro `multiplo`, **Then** riceve solo il modello singolo, con
   `multiplo: false`, come prima della 014 (FR-009h, SC-007).
6. **Given** la stessa situazione, **When** GEBAN cerca con `multiplo=true`,
   **Then** riceve solo il modello multiplo, con `multiplo: true`, e i suoi
   `campi-richiesti` descrivono gli elementi di `articolazioni` (FR-009g,
   FR-013).

---

### Edge Cases

- Nessun campo ripetibile: bando singolo, nessuna regressione.
- Modello multiplo con lista vuota o assente: dati non validi
  (`CAMPO_OBBLIGATORIO`, FR-016c), anche se nel discovery il campo e'
  `obbligatorio: false`; quel valore serve a far valere la foglia anche per i
  modelli singoli.
- Modello singolo che riceve `articolazioni`: `CAMPO_NON_AMMESSO` (FR-016g).
- Elemento senza `descrizione`: dati non validi (`CAMPO_OBBLIGATORIO` su
  `articolazioni[<codice>].descrizione`); la descrizione e' il testo che
  identifica l'articolazione nel documento e negli errori.
- Elemento senza `codice` o con `codice` vuoto: dati non validi; il percorso
  usa l'indice nella lista, a partire da 0: il secondo elemento e'
  `articolazioni[1]`.
- Un sotto-campo ha lo stesso codice di un campo principale: ammesso, il
  contesto (gruppo nel builder, percorso nei dati) li distingue.
- Il numero di articolazioni cambia fra una procedura e l'altra: il modello non
  dipende dal numero ne' dai codici degli elementi.
- Chiave con prefisso `_` dentro un campo (es. `_comment`): ignorata, come
  annotazione.
- La foglia cambia i sotto-campi dopo la pubblicazione di un modello: il modello
  pubblicato continua a validare con la copia salvata (snapshot), come gia'
  avviene per i campi principali.

## Requirements *(mandatory)*

### Functional Requirements

#### Contratto discovery (versione 0.8.0, additiva rispetto alla 0.7.0)

- **FR-001**: La struttura nodo/foglia e la forma dei campi esistenti MUST
  restare invariate: ogni albero valido con la 0.7.0 resta valido con la 0.8.0,
  salvo i campi che oggi portano chiavi sconosciute (vedi FR-004).
- **FR-002**: Un campo con `tipo: "array"` MAY dichiarare `campi`, elenco non
  vuoto di sotto-campi con la stessa forma di `CampoContrattoDati`.
- **FR-003**: `campi` su un campo di tipo diverso da `array`, un sotto-campo di
  tipo `array` o `object`, o codici di sotto-campo duplicati MUST rendere il
  discovery non conforme, con il percorso del punto difforme.
- **FR-004**: Una chiave non prevista dalla grammatica del campo MUST rendere il
  discovery non conforme, con il nome della chiave e il percorso; le chiavi che
  iniziano con `_` MUST essere ignorate come annotazioni.
- **FR-005**: Un campo `array` senza `campi` resta ammesso e conserva il
  significato attuale (lista di valori senza struttura dichiarata).
- **FR-006**: La stessa grammatica MUST valere per la definizione della
  struttura da interfaccia di amministrazione, che usa gia' lo stesso modello di
  campo, e per il contratto esportato verso l'integratore.

#### Modello e builder

- **FR-007**: La versione di un modello MUST salvare i sotto-campi di un campo
  ripetibile nella propria copia del contratto dati, come gia' fa per i campi
  principali.
- **FR-008**: Il builder MUST mostrare i campi principali separati da quelli di
  ciascun campo ripetibile, in gruppi collassabili, con l'`etichetta` del campo
  ripetibile come titolo del gruppo.
- **FR-009**: Il builder MUST NOT presentare una lista piatta che mescoli campi
  principali e sotto-campi.
- **FR-009a**: Alla creazione di un modello su una foglia che dichiara almeno
  un campo ripetibile, il gestore MUST scegliere fra "Bando singolo" e "Bando
  multiplo"; su una foglia senza campi ripetibili la scelta non compare e il
  modello e' singolo.
- **FR-009b**: La versione di un modello singolo MUST NOT includere i campi
  ripetibili della foglia; quella di un modello multiplo MUST includerli.
- **FR-009c**: Nel builder di un modello multiplo i campi ripetibili MUST
  comparire in una sezione distinta e marcata come "Bando multiplo"; nel
  builder di un modello singolo MUST NOT comparire.
- **FR-009d**: Un modello multiplo MUST NOT essere pubblicato se non contiene
  almeno una riga ripetuta (FR-016) per ciascun campo ripetibile che include.
- **FR-009e**: Il gestore MAY creare un modello multiplo partendo dal testo di
  un modello singolo della stessa combinazione; il risultato e' un modello a
  se', marcato multiplo, non una variante ne' un'edizione derivata.
- **FR-009f**: Un modello singolo e un modello multiplo della stessa
  combinazione (tipo documento, percorso, dimensioni) MUST poter coesistere
  senza richiedere una nota di variante; due modelli multipli della stessa
  combinazione seguono la regola attuale delle varianti.

#### Catalogo

- **FR-009g**: La risposta della ricerca modelli MUST indicare per ogni
  modello `multiplo` (true/false).
- **FR-009h**: La ricerca modelli MUST accettare il filtro `multiplo`; senza
  filtro MUST restituire i soli modelli singoli, cosi' che le chiamate
  esistenti non cambino risultato.

#### Dati, validazione e generazione

- **FR-010**: Nei `dati`, un campo ripetibile MUST essere una lista di elementi
  `{ "codice", "descrizione", "campi": { <codice sotto-campo>: valore } }`.
- **FR-011**: La validazione MUST controllare ogni elemento contro i sotto-campi
  salvati nella versione: obbligatorieta', tipo, campi non ammessi, codice
  elemento presente e unico, descrizione presente.
- **FR-012**: Gli errori sugli elementi MUST usare il percorso
  `<campo>[<codice elemento>].campi.<sotto-campo>`, oppure
  `<campo>[<indice>]` quando il codice manca.
- **FR-013**: Lo schema JSON restituito da `campi-richiesti` MUST descrivere gli
  elementi del campo ripetibile (`items`), cosi' che l'integratore possa
  validare prima di inviare.
- **FR-014**: La generazione MUST produrre un solo documento per richiesta.
- **FR-015**: La generazione MUST NOT scrivere nel documento la
  rappresentazione grezza di una lista.
- **FR-016**: Il modello impagina gli elementi di un campo ripetibile con una
  **riga di tabella ripetuta** (decisione 2026-10-26). Nel formato
  `GEMODO_DOCUMENT_V1` una riga di tabella MAY dichiarare il campo ripetibile
  su cui si ripete; i suoi segnaposti si riferiscono all'elemento corrente:
  `{{articolazioni.codice}}`, `{{articolazioni.descrizione}}`,
  `{{articolazioni.campi.<sotto-campo>}}`.
- **FR-016a**: In generazione la riga ripetuta MUST produrre una riga per ogni
  elemento, nell'ordine dei dati, con i valori di quell'elemento.
- **FR-016b**: Una riga ripetuta MUST NOT contenere segnaposti della procedura
  principale ne' di un altro campo ripetibile, e un segnaposto di elemento
  MUST NOT stare fuori da una riga ripetuta; la pubblicazione del modello e'
  bloccata con l'indicazione del punto.
- **FR-016c**: Per un modello multiplo i campi ripetibili inclusi MUST essere
  trattati come obbligatori con almeno un elemento: lista vuota o assente
  produce `CAMPO_OBBLIGATORIO`, quindi la tabella non esce mai vuota. Un bando
  senza articolazioni usa il modello singolo.
- **FR-016g**: Un modello singolo che riceve un campo ripetibile nei `dati`
  MUST rispondere `CAMPO_NON_AMMESSO` su quel campo, non ignorarlo.
- **FR-016h**: Doppioni nel modello multiplo (decisione 2026-10-26):
  - due o piu' righe ripetute sullo stesso campo ripetibile **nella stessa
    tabella** MUST bloccare la pubblicazione, indicando la tabella;
  - righe ripetute sullo stesso campo ripetibile in **tabelle diverse** sono
    ammesse (es. "Codice | Posti" in un articolo e "Codice | Sede" in un
    altro); il builder MUST mostrare un avviso non bloccante con il numero di
    tabelle e dove si trovano;
  - lo stesso segnaposto ripetuto **nella stessa riga** MUST produrre un avviso
    non bloccante.
- **FR-016d**: Un sotto-campo facoltativo assente in un elemento MUST produrre
  una cella vuota, non il segnaposto ne' un errore.
- **FR-016e**: Il builder MUST permettere di creare e modificare una tabella
  (intestazione, righe, celle con testo e segnaposti) e di marcare una riga
  come ripetuta scegliendo il campo ripetibile; il PDF MUST stampare la
  tabella come griglia, non come testo separato da `|`.
- **FR-016f**: L'anteprima del builder MUST mostrare la riga ripetuta con
  almeno due elementi d'esempio, cosi' che il gestore veda l'effetto della
  ripetizione senza dati reali.

#### Documentazione

- **FR-017**: La pagina `docs/contratto-dati.md` MUST
  descrivere la grammatica, le regole di conformita' del discovery, la
  validazione dei dati e gli esempi singolo e multiplo, distinguendo cio' che e'
  attivo da cio' che arriva con questa spec.

### Out of Scope

- Avviso al gestore quando inserisce un'etichetta gia' presente nel modello:
  miglioria futura, non bloccante.
- Piu' di un livello di annidamento.
- Rinominare i campi in `codice_bando_01`, `codice_bando_02`: non ammesso.
- Generare un documento per ogni articolazione.
- Sotto-campi diversi fra elementi dello stesso campo ripetibile (es. una
  tematica con due sedi e una con una): escluso dalla verifica con GEBAN del
  2026-10-26.
- Etichette fisse per singola articolazione nel builder
  (`codice_bando_tematica_a`) e modello dedicato al singolo bando: discussi il
  2026-10-26, non adottati.
- Ripetere capoversi o sezioni fuori da una tabella: la sola unita' ripetuta
  e' la riga di tabella.
- Scegliere in automatico il modello multiplo in generazione quando arrivano
  articolazioni a un modello singolo: scartato il 2026-10-26 a favore della
  scelta esplicita nel catalogo (FR-009g/h).

### Key Entities *(include if feature involves data)*

- **Campo ripetibile**: campo del contratto con `tipo: "array"` e `campi`.
  Dichiara la forma di un elemento, non gli elementi.
- **Sotto-campo**: campo dichiarato dentro un campo ripetibile; stessa forma di
  un campo principale, tipo scalare.
- **Elemento** (per i bandi: articolazione): istanza nei `dati`, con `codice`,
  `descrizione`, `campi`.
- **Gruppo etichette**: raggruppamento visuale nel builder.
- **Modello multiplo**: modello scelto come "Bando multiplo" alla creazione;
  include i campi ripetibili della foglia e li impagina con righe ripetute.
  Coesiste con il modello singolo della stessa combinazione.
- **Riga ripetuta**: riga di tabella del modello che si ripete per ogni
  elemento di un campo ripetibile.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: L'albero GEBAN di test attuale supera il test di connessione con
  il contratto 0.8.0 senza modifiche lato GEBAN.
- **SC-002**: Un contratto di bando singolo esistente resta utilizzabile senza
  modifiche e senza cambiamenti visibili nel pannello etichette.
- **SC-003**: Una foglia con un campo ripetibile di almeno 5 sotto-campi e una
  richiesta con almeno 3 elementi vengono lette, validate e generate senza
  mescolare valori di elementi diversi.
- **SC-004**: Ogni richiesta multi-articolazione produce un solo documento.
- **SC-005**: Ogni errore su un sotto-campo riporta il campo ripetibile,
  l'elemento e il sotto-campo.
- **SC-006**: La documentazione consegnabile include esempi validi di discovery
  e di dati per bando singolo e multi-articolazione, verificati contro i
  contratti.
- **SC-007**: Le chiamate al catalogo senza filtro `multiplo` restituiscono
  gli stessi modelli di prima dell'introduzione dei modelli multipli.
- **SC-008**: Nessuna richiesta con articolazioni produce un documento senza
  di esse: o le stampa un modello multiplo, o un modello singolo la rifiuta.

## Assumptions

- L'endpoint GEBAN reale restituisce l'albero completo
  (`BANDO_CONCORSO.nodi[]`, `figli`, `campi`); la variante a collegamenti
  successivi (`url_figli`) non e' usata.
- `codice` resta l'identificativo tecnico, `descrizione` il testo leggibile;
  non si introducono `id` o `etichetta` sugli elementi.
- GEBAN puo' inviare la lista delle articolazioni nei `dati` quando la
  procedura e' multi-articolazione.
