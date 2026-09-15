# Feature Specification: Configurazione Cataloghi E Integrazioni

**Feature Branch**: `010-configurazione-cataloghi-integrazioni`

**Created**: 2026-09-15

**Status**: Draft

**Input**: Nata da `docs/adr/0001-ownership-dati-esterni-e-onboarding-contesti.md` e
dalla sessione di lavoro 2026-09-14/15: GEMODO non copia piu' la categorizzazione di
un sistema esterno come sorgente di verita' (vedi `DEC-001-OWNERSHIP-DATI-ESTERNI`),
e l'onboarding di un tipo documento (definizione struttura, generazione del
contratto atteso, registrazione dell'endpoint) avviene tramite un'interfaccia di
amministrazione, non un file di configurazione (`DEC-001-ONBOARDING-STRUTTURA-
DOCUMENTO`).

## Clarifications

### Session 2026-09-15

- Q: Serve imporre un solo endpoint HTTP a ogni sistema che si integra? -> A: No.
  Si standardizza il *contratto logico* (dato un tipo documento, restituisci
  tipologie/profili/campi con una data di validita'), non il numero di chiamate
  HTTP necessarie a comporlo. Un client HTTP generico gestisce la paginazione
  (pattern HAL gia' osservato su un'API reale di GEBAN) in modo trasparente, dietro
  l'adapter — la definizione della struttura e la generazione del contratto non
  devono sapere se dietro c'e' una chiamata o dieci (`DEC-002-PORTS-ADAPTERS-
  DISCOVERY`).
- Q: Come si evita di far reinserire dati standard ripetuti (es. gli stessi campi
  per ogni combinazione tipologia/profilo)? -> A: I campi del contratto dati sono
  definiti una volta, allo stesso livello delle tipologie, non duplicati dentro
  ogni combinazione. Un campo i cui valori ammessi dipendono dal profilo scelto
  (es. il "livello" trovato su `/api/v1/profili` di GEBAN: Ricercatore I/II/III,
  Funzionario di Amministrazione IV/V) referenzia un attributo definito una sola
  volta sul profilo, invece di essere ridefinito per ogni combinazione.
- Q: Quale forma ha l'interfaccia di definizione in questo primo incremento? -> A:
  Una visualizzazione JSON ad albero (nodi collassabili/espandibili), non un
  wizard con form/matrice dedicati per ogni passo. Scelta esplicita per partire
  velocemente; puo' evolvere in un'interfaccia piu' guidata in un secondo tempo,
  senza cambiare lo schema logico sottostante.
- Q: Il caso GEBAN e' gia' concreto o solo un esempio teorico? -> A: Concreto.
  `docs/adr/0001-esempio-discovery-geban.json` e' il primo caso reale — costruito
  sui codici verificati sugli endpoint di test di GEBAN il 2026-09-15 — usato come
  riferimento per questa spec, non ancora come file consumato a runtime.

### Session 2026-09-15 (seconda parte)

- Q: Le tre API GEBAN-facing di classificazione gia' implementate dalla `001`
  (`/catalogo/tipi-documento`, `/profili`, `/classificazione`) restano nel
  contratto pubblico? -> A: No, si ritirano
  (`DEC-001-RITIRO-ENDPOINT-CLASSIFICAZIONE`). GEBAN possiede gia' la propria
  categorizzazione, non ha bisogno di richiederla a GEMODO. Lo schema/esempio
  generato da FR-006 e' il sostituto funzionale: non un endpoint runtime nostro,
  ma la documentazione che dice agli sviluppatori esterni come strutturare
  l'endpoint di discovery che loro devono esporre verso GEMODO. Il contratto
  GEBAN-facing verso la `001` si riduce a `/catalogo/modelli`,
  `/campi-richiesti`, `/documenti/valida`, `/documenti/genera` — tutte relative
  a cosa ha GEMODO, mai a cosa possiede il sistema esterno.
- Q: Quando l'operatore GEMODO naviga l'albero tipologia/profilo/campi per creare
  un nuovo modello (FR-011, interrogazione live della porta di discovery) e il
  sistema esterno integrato e' irraggiungibile in quel momento, si usa una cache
  locale? -> A: Cache breve **in memoria di processo** soltanto (nessuna tabella
  DB persistente) per fluidita' di navigazione; se il sistema esterno resta
  irraggiungibile oltre quella finestra, la navigazione si ferma e restituisce un
  errore funzionale di connessione — mai un elenco vuoto o dati stantii silenziosi
  (coerente con l'Acceptance Scenario 3 della User Story 3).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Definire la struttura di un tipo documento (Priority: P1)

Come operatore GEMODO, voglio definire — tramite una visualizzazione JSON ad
albero — un tipo documento con le sue tipologie, profili e campi del contratto
dati, cosi' da avere un'unica sorgente per generare sia la documentazione per un
integratore esterno sia, per un contesto self-service, il Registro Contratti Dati
interno.

**Why this priority**: senza questo passo nessun altro passo del flusso di
onboarding (generazione contratto, registrazione endpoint) puo' iniziare.

**Independent Test**: un operatore puo' creare un tipo documento con almeno una
tipologia, un profilo e un campo, e vederlo salvato come "definito" senza che sia
ancora utilizzabile per creare modelli.

**Acceptance Scenarios**:

1. **Given** nessun tipo documento con quel codice esiste, **When** l'operatore lo
   definisce con tipologie/profili/campi tramite l'albero JSON, **Then** la
   definizione viene salvata con stato "definito, non connesso".
2. **Given** un profilo ha un attributo aggiuntivo (es. livello) con valori
   ammessi e un default, **When** un campo del contratto dati referenzia
   quell'attributo, **Then** il campo non richiede una lista di opzioni propria —
   le eredita dal profilo scelto in fase di creazione modello.
3. **Given** una definizione incompleta (es. un tipo documento senza nessuna
   tipologia), **When** l'operatore prova a generare il contratto (User Story 2),
   **Then** il sistema impedisce la generazione e segnala cosa manca.

---

### User Story 2 - Generare il contratto/documentazione per l'integratore (Priority: P1)

Come operatore GEMODO, voglio che la definizione della User Story 1 produca
automaticamente uno schema/esempio JSON che descrive esattamente la risposta
attesa dall'endpoint di discovery, cosi' da consegnarlo a un team di sviluppo
esterno senza ambiguita' su cosa implementare.

**Why this priority**: e' il meccanismo che sostituisce il "far indovinare" al
team esterno cosa GEMODO si aspetta — nucleo del cambio di paradigma di questa
spec.

**Independent Test**: dato un tipo documento completamente definito, l'operatore
ottiene uno schema/esempio scaricabile che, se implementato letteralmente da un
endpoint di prova, viene accettato dal test di connessione della User Story 3.

**Acceptance Scenarios**:

1. **Given** una definizione completa, **When** l'operatore genera il contratto,
   **Then** ottiene un JSON Schema/esempio con tipo documento, tipologie,
   profili, campi e data di validita'.
2. **Given** il contratto e' stato generato, **When** l'operatore lo esporta,
   **Then** puo' scaricarlo o copiarlo per consegnarlo a un team esterno.

---

### User Story 3 - Registrare l'endpoint e attivare l'integrazione (Priority: P1)

Come operatore GEMODO, voglio registrare l'URL dell'endpoint fornito dal team
esterno e verificarne la conformita' allo schema generato, cosi' che il contesto
documentale diventi "connesso" e disponibile per la creazione di modelli.

**Why this priority**: senza un endpoint registrato e verificato, un tipo
documento integrato resta definito ma inutilizzabile — evita che un operatore
inizi a creare modelli contro un'integrazione che non funziona ancora.

**Independent Test**: registrando un endpoint di prova che rispetta lo schema, il
tipo documento passa a "connesso"; registrando un endpoint che non rispetta lo
schema (campi mancanti o extra) o irraggiungibile, resta "non connesso" con un
errore esplicito.

**Acceptance Scenarios**:

1. **Given** un tipo documento definito (User Story 1) con contratto generato
   (User Story 2), **When** l'operatore registra un endpoint e il test di
   connessione ha successo, **Then** il tipo documento risulta "connesso".
2. **Given** un endpoint registrato restituisce campi non previsti dal contratto
   generato, **When** viene testato, **Then** il sistema segnala l'errore e non
   marca il contesto come connesso.
3. **Given** un endpoint registrato e' temporaneamente irraggiungibile in fase di
   *creazione modello* (non di sola consultazione), **When** un operatore prova a
   creare un modello, **Then** l'operazione fallisce con errore esplicito, non con
   un menu vuoto silenzioso.
4. **Given** un tipo documento self-service (nessun sistema esterno), **When**
   l'operatore lo configura, **Then** il flusso si ferma alla User Story 1/2:
   nessuna registrazione di endpoint richiesta, il contesto risulta subito
   utilizzabile tramite l'adapter locale del Registro Contratti Dati.

---

### User Story 4 - Vedere lo stato di connessione nella dashboard (Priority: P2)

Come operatore GEMODO, voglio vedere in una dashboard quali contesti documentali
sono definiti ma non ancora connessi e quali sono attivi, cosi' da sapere cosa
manca prima che un utente possa creare modelli per quel contesto.

**Why this priority**: migliora l'operativita' ma non blocca il flusso principale
(le User Story 1-3 bastano a rendere un'integrazione funzionante anche senza
questa vista).

**Independent Test**: la dashboard mostra correttamente lo stato di ogni tipo
documento configurato (definito / connesso / errore ultima verifica).

**Acceptance Scenarios**:

1. **Given** esistono tipi documento in stati diversi, **When** l'operatore apre
   la dashboard, **Then** vede per ciascuno lo stato corrente e, se applicabile,
   l'esito dell'ultimo test di connessione.

### Edge Cases

- Un endpoint registrato che non rispetta lo schema generato (campi mancanti o
  extra rispetto al contratto).
- Un endpoint irraggiungibile al momento della registrazione (test di connessione
  fallito) — il contesto resta "non connesso", non entra in uno stato ambiguo.
- Un tipo documento definito ma mai connesso: deve restare non utilizzabile per la
  creazione di modelli, non generare un errore generico non distinguibile da altri.
- Ridefinizione di una struttura (tipologie/profili/campi) per un tipo documento
  gia' connesso e con modelli pubblicati: i modelli esistenti non devono essere
  invalidati silenziosamente (FR-013).
- Un attributo profilo-dipendente (es. livello) i cui valori ammessi cambiano nel
  tempo lato sistema esterno: la data di validita' del contratto (User Story 2)
  permette di distinguere modelli creati con versioni diverse della definizione.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Il sistema MUST fornire un'interfaccia di amministrazione per
  definire un tipo documento (codice, nome, `codice_contesto` che ne autorizza
  la scrittura — `DEC-001-CONTESTO-SOSTITUISCE-UFFICIO`, nessuna entita' Ufficio
  separata).
- **FR-002**: Il sistema MUST permettere di definire, per un tipo documento, una o
  piu' tipologie (codice, descrizione, riferimento esterno opzionale).
- **FR-003**: Il sistema MUST permettere di definire, per un tipo documento, uno o
  piu' profili/categorie (codice, descrizione) con attributi aggiuntivi opzionali
  (nome attributo, valori ammessi, valore di default) per rappresentare dati come
  il "livello" che variano per profilo.
- **FR-004**: Il sistema MUST permettere di definire le combinazioni ammesse fra
  tipologia e profilo per un tipo documento.
- **FR-005**: Il sistema MUST permettere di definire i campi del contratto dati
  (codice, etichetta, tipo, lingua, obbligatorieta', ordine, validazione), incluso
  marcare un campo come dipendente da un attributo profilo definito in FR-003
  invece che con opzioni fisse.
- **FR-006**: Il sistema MUST generare, dalla definizione, uno schema/esempio JSON
  che rappresenta la risposta attesa dall'endpoint di discovery di un sistema
  esterno integrato (tipo documento, tipologie, profili, campi, data di validita').
- **FR-007**: Il sistema MUST permettere di esportare la documentazione generata
  in FR-006 per consegnarla a un team di sviluppo esterno.
- **FR-008**: Il sistema MUST permettere di registrare l'URL di un endpoint
  esterno per un tipo documento definito, e di eseguire un test di connessione che
  verifichi la conformita' della risposta allo schema generato in FR-006 prima di
  marcare il contesto come connesso.
- **FR-009**: Un tipo documento integrato senza un endpoint registrato e
  verificato MUST restare non utilizzabile per la creazione di modelli; questo
  stato MUST essere visibile in una dashboard (User Story 4).
- **FR-010**: Per un tipo documento self-service (nessun sistema esterno), il
  flusso MUST usare l'adapter locale del Registro Contratti Dati di GEMODO,
  rendendo il contesto utilizzabile senza richiedere la registrazione di un
  endpoint (`DEC-002-PORTS-ADAPTERS-DISCOVERY`).
- **FR-011**: Il client HTTP che interroga un endpoint registrato MUST gestire
  trasparentemente la paginazione se presente, assemblando il risultato completo
  prima di restituirlo al resto del sistema — la definizione (FR-001..FR-007) MUST
  restare indipendente da questo dettaglio di trasporto.
- **FR-012**: L'accesso a questa interfaccia di amministrazione MUST essere
  riservato a un ruolo amministrativo distinto da `GEMODO_MODELLI_GESTORE` (che
  opera sui modelli di un tipo documento gia' connesso, non sulla sua
  definizione) — meccanismo esatto di autorizzazione da dettagliare con la `006`.
- **FR-013**: Ogni definizione (tipo documento, tipologie, profili, campi) MUST
  essere versionata: una modifica dopo che il contesto e' gia' connesso e in uso
  MUST NOT invalidare silenziosamente i modelli gia' creati con la struttura
  precedente.

### Key Entities *(include if feature involves data)*

- **Tipo Documento** (incluso `codice_contesto`), **Categoria/Profilo Documento**,
  **Tipologia Documento**, **Campo Richiesto** *(riferimento, definite in `001`)*:
  questa spec ne aggiunge l'interfaccia di *creazione/definizione*, non ridefinisce
  le entita' stesse. Nessuna entita' `Ufficio` (`DEC-001-CONTESTO-SOSTITUISCE-
  UFFICIO`, 2026-09-15): il proprietario di un tipo documento e' un campo diretto
  (`codice_contesto`), non un'entita' separata da amministrare qui.
- **Registro Contratti Dati** *(riferimento, `001`)*: destinazione della
  definizione per un tipo documento self-service.
- **Attributo Profilo** *(nuova)*: attributo aggiuntivo opzionale su un profilo
  (nome, valori ammessi, valore di default) — generalizza il caso "livello".
  Referenziato da un Campo Richiesto per rendere le sue opzioni dipendenti dal
  profilo scelto in fase di creazione modello.
- **Endpoint Di Integrazione** *(nuova)*: URL registrato per un tipo documento
  integrato, stato (definito / connesso / errore ultima verifica), esito e data
  dell'ultimo test di connessione.
- **Schema Di Discovery Generato** *(nuova)*: rappresentazione JSON Schema/esempio
  prodotta dalla definizione (FR-006), versionata, usata sia come documentazione
  per l'integratore sia come riferimento per validare le risposte reali
  dell'endpoint registrato (FR-008).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un operatore puo' definire un nuovo tipo documento completo
  (almeno una tipologia, un profilo, un campo) e ottenere lo schema generato senza
  scrivere codice.
- **SC-002**: Un endpoint registrato che non rispetta lo schema generato viene
  segnalato al momento della registrazione (test di connessione), non alla prima
  chiamata in produzione durante la creazione di un modello.
- **SC-003**: Un tipo documento self-service diventa utilizzabile per la
  creazione di modelli subito dopo la definizione (User Story 1), senza dover
  passare per la User Story 3.
- **SC-004**: Nessun modello pubblicato viene invalidato da una successiva
  modifica alla definizione del suo tipo documento (FR-013).

## Assumptions

- Questa spec nasce da `docs/adr/0001-ownership-dati-esterni-e-onboarding-
  contesti.md` e dalle decisioni confermate `DEC-001-OWNERSHIP-DATI-ESTERNI`,
  `DEC-001-ONBOARDING-STRUTTURA-DOCUMENTO`, `DEC-002-PORTS-ADAPTERS-DISCOVERY`.
- Il primo caso d'uso reale e' GEBAN/`BANDO_CONCORSO`; lo schema di riferimento
  per questo caso e' `docs/adr/0001-esempio-discovery-geban.json` (esempio da
  consegnare al team GEBAN, non ancora un file consumato a runtime).
- L'interfaccia di questo primo incremento e' una visualizzazione JSON ad albero
  collassabile/espandibile, scelta esplicita per partire velocemente; puo'
  evolvere in un'interfaccia piu' guidata (form/matrice) in un secondo tempo senza
  cambiare lo schema logico sottostante (FR-001..FR-007 restano gli stessi
  indipendentemente dalla UI che li implementa).
- Fuori scope di questa spec: l'editor visuale del documento/sezioni/placeholder
  (`003`), la generazione PDF (`004`), la gestione granulare di permessi oltre a
  ruolo+contesto (`006`, FR-012 rimanda li' il dettaglio).
- Le combinazioni tipologia-profilo e il meccanismo esatto degli attributi
  profilo-dipendenti (FR-003) per il caso GEBAN restano da validare con il loro
  team prima che l'integrazione reale vada in produzione (vedi note
  `_confermato: false` residue in `docs/adr/0001-esempio-discovery-geban.json`).
