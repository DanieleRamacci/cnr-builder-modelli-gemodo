# Feature Specification: Campi ripetibili e articolazioni del bando nel contratto dati

**Feature Branch**: `test`

**Created**: 2026-10-07

**Status**: Draft (chiarimenti 2026-10-07; una decisione aperta, vedi FR-016)

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

**Independent Test**: dato un modello creato da una foglia con un campo
ripetibile, il pannello delle etichette mostra un gruppo per la procedura
principale e un gruppo collassabile per il campo ripetibile, con le etichette
dei sotto-campi.

**Acceptance Scenarios**:

1. **Given** una foglia con campi principali e un campo ripetibile
   `articolazioni`, **When** il gestore apre l'editor del modello, **Then** vede
   due gruppi distinti: dati della procedura e "Articolazioni del bando".
2. **Given** `codice_bando` presente sia fra i campi principali sia fra i
   sotto-campi, **When** il gestore consulta le etichette, **Then** i due
   compaiono nei rispettivi gruppi e non sono intercambiabili.
3. **Given** molti gruppi, **When** il gestore apre il pannello, **Then** puo'
   comprimere ed espandere i gruppi.

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
2. **Given** un sotto-campo obbligatorio mancante nell'articolazione `TEMA_A`,
   **When** si chiama `valida` o `genera`, **Then** l'errore ha
   `campo = "articolazioni[TEMA_A].campi.numero_posti"` e codice
   `CAMPO_OBBLIGATORIO`.
3. **Given** due elementi con lo stesso `codice`, **When** si valida, **Then**
   l'errore e' `CODICE_ELEMENTO_DUPLICATO` sul campo `articolazioni`.
4. **Given** un sotto-campo non dichiarato, **When** si valida, **Then**
   l'errore e' `CAMPO_NON_AMMESSO` con il percorso dell'elemento.

---

### Edge Cases

- Nessun campo ripetibile: bando singolo, nessuna regressione.
- Campo ripetibile obbligatorio con lista vuota: dati non validi
  (`CAMPO_OBBLIGATORIO`). Non obbligatorio e assente o vuoto: il documento si
  comporta come bando singolo.
- Elemento senza `descrizione`: dati non validi (`CAMPO_OBBLIGATORIO` su
  `articolazioni[<codice>].descrizione`); la descrizione e' il testo che
  identifica l'articolazione nel documento e negli errori.
- Elemento senza `codice` o con `codice` vuoto: dati non validi; il percorso
  usa l'indice, `articolazioni[1]`.
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
- **FR-016**: [NEEDS CLARIFICATION: come il modello impagina gli elementi.
  Proposta: un blocco `ripetuto per ogni elemento di <campo>` nel formato
  `GEMODO_DOCUMENT_V1`, con segnaposti relativi all'elemento
  (`{{articolazioni.descrizione}}`, `{{articolazioni.campi.numero_posti}}`).
  Alternativa: riferimenti alla singola articolazione per codice, possibile solo
  se i codici sono fissati nel discovery, in contrasto con l'edge case sul
  numero variabile.]

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

### Key Entities *(include if feature involves data)*

- **Campo ripetibile**: campo del contratto con `tipo: "array"` e `campi`.
  Dichiara la forma di un elemento, non gli elementi.
- **Sotto-campo**: campo dichiarato dentro un campo ripetibile; stessa forma di
  un campo principale, tipo scalare.
- **Elemento** (per i bandi: articolazione): istanza nei `dati`, con `codice`,
  `descrizione`, `campi`.
- **Gruppo etichette**: raggruppamento visuale nel builder.

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

## Assumptions

- L'endpoint GEBAN reale restituisce l'albero completo
  (`BANDO_CONCORSO.nodi[]`, `figli`, `campi`); la variante a collegamenti
  successivi (`url_figli`) non e' usata.
- `codice` resta l'identificativo tecnico, `descrizione` il testo leggibile;
  non si introducono `id` o `etichetta` sugli elementi.
- GEBAN puo' inviare la lista delle articolazioni nei `dati` quando la
  procedura e' multi-articolazione.
