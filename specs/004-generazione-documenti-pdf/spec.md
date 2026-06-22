# Feature Specification: Generazione Documenti PDF

**Feature Branch**: `004-generazione-documenti-pdf`

**Created**: 2026-06-19

**Status**: Draft

**Input**: Estratta da `PROPOSTA-servizio-gestione-modelli-bando.md` sezioni §9.6, §13 e §16.5.

## Clarifications

### Session 2026-06-22

- Q: Stiamo creando la spec da zero? -> A: No. La spec esiste gia' come draft di copertura; questa sessione la integra con decisioni e vincoli emersi da catalogo/contratto dati, sezioni/placeholder, storage/idempotenza e sicurezza/audit.
- Q: La generazione deve rivalidare il payload o fidarsi di una validazione precedente? -> A: La generazione deve usare payload conforme al contratto dati della versione modello selezionata e deve impedire la produzione se la versione non e' piu' pubblicata o se il payload non e' coerente al momento della richiesta.
- Q: Qual e' il confine con storage e idempotenza? -> A: Questa spec copre produzione deterministica del documento, distinzione bozza/ufficiale, metadati e fallimenti di rendering; conservazione, download, stato consultabile e regole di retry/idempotenza restano nella spec `005-storage-idempotenza-consultazione`.
- Q: Qual e' il confine con sicurezza e audit? -> A: Questa spec richiede che generazione e fallimenti siano auditabili e associati ad attore o client; ruoli, token e regole autorizzative sono definiti nella spec `006-sicurezza-autorizzazioni-audit`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Generare una bozza documento (Priority: P1)

Come GEBAN, voglio richiedere una generazione bozza a partire da modello pubblicato e dati
validati, cosi' da verificare il documento prima dell'uso ufficiale.

**Why this priority**: la bozza riduce il rischio prima della generazione ufficiale.

**Independent Test**: dati modello pubblicato e payload valido, il sistema produce una
bozza distinguibile dal documento ufficiale.

**Acceptance Scenarios**:

1. **Given** modello pubblicato e payload valido, **When** GEBAN richiede una bozza,
   **Then** il sistema genera un documento marcato come bozza.
2. **Given** payload non valido, **When** GEBAN richiede generazione, **Then** il sistema
   non genera il documento e restituisce errori funzionali.
3. **Given** una bozza generata, **When** viene consultata nei metadati, **Then** risulta
   distinguibile da un documento ufficiale e non utilizzabile come atto definitivo.

---

### User Story 2 - Generare un PDF ufficiale tracciabile (Priority: P1)

Come GEBAN, voglio generare un PDF ufficiale tracciabile, cosi' da proseguire il flusso
amministrativo con un documento riproducibile.

**Why this priority**: il PDF ufficiale e' il prodotto principale del servizio.

**Independent Test**: una generazione ufficiale conserva modello/versione, snapshot dati,
hash, timestamp e riferimento documentale.

**Acceptance Scenarios**:

1. **Given** modello pubblicato e payload valido, **When** GEBAN richiede PDF ufficiale,
   **Then** il sistema genera un documento ufficiale con metadati completi.
2. **Given** il modello non e' pubblicato, **When** viene richiesta generazione ufficiale,
   **Then** il sistema impedisce la generazione.
3. **Given** una versione modello pubblicata con sezioni e placeholder dichiarati,
   **When** viene generato il PDF ufficiale, **Then** il contenuto prodotto e'
   ricostruibile da versione modello, sezioni, placeholder risolti e snapshot dati.

---

### User Story 3 - Gestire fallimenti di generazione (Priority: P1)

Come GEBAN, voglio ricevere un esito funzionale chiaro quando la generazione non riesce,
cosi' da correggere dati, scegliere un modello valido o ripetere il flusso senza produrre
documenti ambigui.

**Why this priority**: un errore non tracciato o non comprensibile puo' bloccare il
processo amministrativo o lasciare dubbi sullo stato del documento.

**Independent Test**: richieste con modello non utilizzabile, placeholder non risolti o
errore di rendering non producono PDF ufficiale e restituiscono motivazione funzionale.

**Acceptance Scenarios**:

1. **Given** la versione modello e' stata archiviata dopo la compilazione in GEBAN,
   **When** viene richiesta generazione, **Then** il sistema impedisce la produzione e
   indica che il modello non e' piu' utilizzabile.
2. **Given** restano placeholder non risolti, **When** viene richiesta generazione,
   **Then** il sistema non produce il PDF e restituisce errore funzionale.
3. **Given** avviene un errore di rendering o produzione file, **When** la richiesta
   fallisce, **Then** il sistema restituisce esito fallito senza esporre dettagli tecnici
   o dati sensibili.

### Edge Cases

- Template con placeholder non risolti.
- Versione modello archiviata, sospesa o sostituita dopo la validazione ma prima della
  generazione.
- Payload valido in precedenza ma non piu' coerente con la versione modello al momento
  della generazione.
- Errore durante rendering.
- Errore durante produzione file.
- Differenza tra bozza e ufficiale non marcata.
- Richiesta di formato non supportato.
- Richiesta di generazione ufficiale tramite tool AI/MCP senza conferma o audit richiesti.
- Fallimento dopo produzione file ma prima della disponibilita' del riferimento
  documentale, da trattare secondo la spec storage/idempotenza.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Il sistema MUST generare documenti solo da modelli pubblicati e payload validati.
- **FR-002**: Il sistema MUST distinguere bozza e ufficiale.
- **FR-003**: Il sistema MUST risolvere placeholder usando lo snapshot dei dati validati.
- **FR-004**: Il sistema MUST impedire la generazione se restano placeholder non risolti.
- **FR-005**: Il sistema MUST produrre metadati di generazione per ogni documento.
- **FR-006**: Il sistema MUST associare ogni documento a modello versione e dati usati.
- **FR-007**: Il sistema MUST restituire esito funzionale chiaro in caso di fallimento.
- **FR-008**: Il sistema MUST calcolare o ricevere un identificativo verificabile del file generato quando disponibile.
- **FR-009**: La richiesta di generazione MUST indicare esplicitamente la versione modello selezionata; il sistema MUST NOT applicare fallback automatico all'ultima versione pubblicata.
- **FR-010**: Prima di produrre un documento, il sistema MUST verificare che la versione modello sia ancora pubblicata e utilizzabile per generazioni operative.
- **FR-011**: Il sistema MUST usare le sezioni e i contenuti associati alla versione modello selezionata, senza leggere contenuti modificabili o template vivi non storicizzati.
- **FR-012**: Il sistema MUST trattare il contenuto del documento come deterministico rispetto a versione modello, sezioni, placeholder e snapshot dati validati.
- **FR-013**: I metadati di generazione MUST distinguere almeno tipo output, bozza/ufficiale, stato/esito, timestamp, versione modello, snapshot dati, attore o client responsabile e identificativo file quando disponibile.
- **FR-014**: Il sistema MUST auditare richiesta, successo e fallimento di generazione secondo le regole della spec sicurezza.
- **FR-015**: Gli errori di generazione MUST essere funzionali e sanificati; non devono esporre segreti, token, stack trace o dettagli tecnici non necessari.
- **FR-016**: La generazione ufficiale richiesta tramite AI/MCP MUST rispettare validazione deterministica, autorizzazione, conferma esplicita e audit prima di produrre un documento ufficiale.
- **FR-017**: Nel perimetro corrente il formato operativo supportato e' PDF; richieste di formati non supportati MUST essere rifiutate con errore funzionale.
- **FR-018**: Il salvataggio del file, lo stato consultabile, il download e la gestione dei retry MUST seguire la spec storage/idempotenza e non sostituire i requisiti di questa feature.

### Key Entities

- **Richiesta Generazione**: richiesta di produzione documento.
- **Documento Generato**: risultato della generazione.
- **PDF Bozza**: documento non ufficiale.
- **PDF Ufficiale**: documento ufficiale tracciato.
- **Snapshot Dati**: dati validati usati per generare il documento.
- **Esito Generazione**: risultato funzionale della richiesta, positivo o fallito, con
  motivazione e metadati minimi.
- **Metadati Generazione**: informazioni necessarie a distinguere output, stato, attore,
  modello, snapshot, timestamp e identificativo file quando disponibile.
- **Contenuto Renderizzato**: documento prodotto risolvendo sezioni e placeholder della
  versione modello con lo snapshot dati validato.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Il 100% dei documenti ufficiali e' collegato a modello versione e snapshot dati.
- **SC-002**: Il 100% delle richieste con payload non valido non produce file ufficiale.
- **SC-003**: Il 100% dei documenti generati distingue bozza e ufficiale.
- **SC-004**: Il 100% delle richieste con versione modello non piu' pubblicata viene
  rifiutato senza produrre PDF ufficiale.
- **SC-005**: Il 100% dei fallimenti di generazione restituisce un esito funzionale
  sanificato e auditabile.
- **SC-006**: Il 100% dei PDF ufficiali generati e' ricostruibile da versione modello,
  sezioni, placeholder risolti e snapshot dati.

## Assumptions

- La conservazione e il download sono approfonditi nella spec storage/idempotenza.
- La gestione di retry, conflitti idempotenti e stato consultabile e' approfondita nella
  spec storage/idempotenza.
- La validazione del payload e la scelta esplicita della versione modello derivano dalla
  spec catalogo/contratto dati.
- Le sezioni e i placeholder usati dal rendering sono quelli storicizzati nella versione
  modello secondo la spec sezioni/placeholder.
- Autorizzazione, attore responsabile e audit sono definiti dalla spec sicurezza.
- Nel perimetro corrente l'output operativo e' PDF; altri formati richiedono decisione o
  feature dedicata.
- Firma, protocollo e pubblicazione restano fuori scope.
