# Feature Specification: Sezioni Placeholder E Versionamento

**Feature Branch**: `003-sezioni-placeholder-versionamento`

**Created**: 2026-06-19

**Status**: Draft

**Input**: Estratta da `PROPOSTA-servizio-gestione-modelli-bando.md` sezioni §5.5, §6, §8.7-§8.9 e §16.3.

## Clarifications

### Session 2026-06-19

- Q: Quale formato deve usare il contenuto delle sezioni? -> A: Contenuto strutturato controllato: paragrafi, titoli, liste, tabelle semplici, grassetto/corsivo e placeholder; HTML libero escluso.
- Q: Come si verifica la coerenza tra placeholder nell'editor e placeholder disponibili? -> A: Il contratto dati deriva dai campi associati al modello; alla pubblicazione il backend confronta i placeholder usati nel contenuto con quelli disponibili e blocca placeholder non presenti o obbligatori mancanti. Il builder deve favorire inserimento da selettore/chip per ridurre errori manuali.
- Q: Come devono essere descritti i campi complessi? -> A: I campi complessi devono avere schema strutturato con sotto-campi, tipi, obbligatorieta' e vincoli; non sono ammessi come JSON libero generico.
- Q: Le sezioni devono avere versionamento autonomo? -> A: No per ora. Le sezioni sono proprie della versione modello, modificabili solo quando la versione modello e' in bozza; una nuova versione modello copia le sezioni dalla precedente. Una eventuale libreria sezioni e' solo template copiabile. Il versionamento autonomo delle sezioni potra' essere valutato in futuro se necessario.
- Q: Sono previste sezioni condizionali? -> A: No per ora. Le sezioni inserite nel modello sono sempre presenti; il perimetro corrente non include sezioni condizionali basate su regole o valori del payload.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Gestire sezioni della versione modello (Priority: P1)

Come gestore modelli, voglio comporre le sezioni proprie di una versione modello, cosi'
da definire il contenuto documentale che verra' storicizzato insieme alla versione modello.

**Why this priority**: il contenuto del documento deve essere riproducibile tramite la
versione modello, senza dipendere da sezioni condivise modificate altrove.

**Independent Test**: una versione modello in bozza puo' avere sezioni create, ordinate e
modificate; una versione modello pubblicata non consente modifiche dirette alle sezioni.

**Acceptance Scenarios**:

1. **Given** una versione modello in bozza, **When** il gestore aggiunge una sezione,
   **Then** la sezione viene salvata come parte della versione modello.
2. **Given** una versione modello in bozza, **When** il gestore modifica testo, ordine o
   obbligatorieta' delle sezioni, **Then** le modifiche aggiornano quella bozza.
3. **Given** una versione modello pubblicata, **When** il gestore prova a modificare le
   sezioni, **Then** il sistema impedisce la modifica diretta.
4. **Given** il gestore compone il testo di una sezione, **When** usa formattazione
   ammessa, **Then** puo' salvare contenuti strutturati con paragrafi, titoli, liste,
   tabelle semplici, grassetto/corsivo e placeholder.
5. **Given** il gestore crea una nuova versione modello da una versione precedente,
   **When** la nuova versione viene inizializzata, **Then** copia anche le sezioni dalla
   versione precedente.
6. **Given** esiste una libreria di sezioni template, **When** il gestore usa un template,
   **Then** il contenuto viene copiato nella versione modello e non resta collegato come
   riferimento vivo.
7. **Given** una sezione e' inserita nella versione modello, **When** il modello viene
   pubblicato o generato, **Then** la sezione e' considerata sempre presente nel perimetro
   corrente.

---

### User Story 2 - Dichiarare placeholder e campi complessi (Priority: P1)

Come gestore modelli, voglio usare placeholder dichiarati nel contratto dati, cosi' da
evitare testi che richiedono dati non forniti da GEBAN.

**Why this priority**: placeholder non dichiarati generano documenti incompleti o non
validabili.

**Independent Test**: una versione modello non puo' essere pubblicata se contiene
placeholder non dichiarati nei campi richiesti.

**Acceptance Scenarios**:

1. **Given** una sezione contiene `{{NUM_POSTI}}`, **When** il modello viene validato,
   **Then** il campo `NUM_POSTI` deve risultare nel contratto dati.
2. **Given** una sezione contiene un placeholder non dichiarato, **When** il gestore tenta
   la pubblicazione, **Then** il sistema blocca o segnala l'anomalia.
3. **Given** un campo complesso come sedi, **When** il contratto viene definito, **Then**
   la struttura attesa deve essere descritta in modo verificabile.
4. **Given** il gestore inserisce placeholder nell'editor, **When** salva o valida la
   sezione, **Then** il builder deve usare i placeholder disponibili del modello e ridurre
   l'inserimento manuale libero.
5. **Given** una versione modello viene pubblicata, **When** il backend valida il contenuto
   delle sezioni, **Then** confronta i placeholder usati con quelli associati al modello e
   blocca placeholder non disponibili o obbligatori mancanti.
6. **Given** un campo complesso come `SEDI` o `REQUISITI`, **When** il gestore lo definisce,
   **Then** deve indicare sotto-campi, tipi, obbligatorieta' e vincoli necessari alla
   compilazione e validazione.

### Edge Cases

- Placeholder duplicati in piu' sezioni.
- Placeholder dichiarato ma non usato.
- Placeholder obbligatorio associato al modello ma non usato nel contenuto editor.
- Campo complesso con array vuoto.
- Campo complesso privo di schema dei sotto-campi.
- Campo complesso valorizzato con sotto-campi non previsti.
- Sezione creata direttamente nella versione modello senza partire da template.
- Cambio ordine sezioni su versione modello gia' pubblicata.
- Tentativo di salvare contenuto con HTML libero o elementi non ammessi.
- Inserimento manuale di un placeholder con errore di battitura.
- Aggiornamento di un template di libreria gia' copiato in versioni modello esistenti.
- Richiesta di mostrare una sezione solo in base a valori del payload: fuori perimetro
  corrente.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Il sistema MUST gestire sezioni proprie della versione modello.
- **FR-001a**: Il sistema MUST rappresentare il contenuto sezione come contenuto strutturato controllato con paragrafi, titoli, liste, tabelle semplici, grassetto/corsivo e placeholder.
- **FR-001b**: Il sistema MUST impedire HTML libero o formattazioni non ammesse nel contenuto delle sezioni.
- **FR-001c**: Il sistema MUST consentire modifiche alle sezioni solo quando la versione modello e' in stato modificabile.
- **FR-001d**: Il sistema MUST impedire modifiche dirette alle sezioni di una versione modello pubblicata.
- **FR-001e**: Quando viene creata una nuova versione modello da una precedente, il sistema MUST copiare anche le sezioni nella nuova versione.
- **FR-001f**: Una eventuale libreria sezioni MUST essere trattata come sorgente di template copiabili, non come riferimento vivo condiviso tra modelli.
- **FR-001g**: Il versionamento autonomo delle sezioni e' escluso dal perimetro corrente e potra' essere valutato in futuro se necessario.
- **FR-001h**: Il sistema MUST trattare le sezioni inserite nella versione modello come sempre presenti nel perimetro corrente.
- **FR-001i**: Il sistema MUST NOT supportare sezioni condizionali basate su regole o valori del payload nel perimetro corrente.
- **FR-002**: Il sistema MUST associare sezioni e voci direttamente alla versione modello.
- **FR-003**: Ogni voce modello MUST mantenere ordine e obbligatorieta'.
- **FR-004**: Il sistema MUST supportare placeholder nel testo delle sezioni.
- **FR-004a**: Il builder SHOULD consentire l'inserimento dei placeholder tramite selezione da quelli associati al modello, evitando quando possibile la digitazione manuale del codice placeholder.
- **FR-005**: Il sistema MUST validare che i placeholder usati nel contenuto editor siano presenti tra i campi/placeholder associati al modello.
- **FR-005a**: Il sistema MUST bloccare la pubblicazione quando il contenuto editor usa placeholder non disponibili per il modello.
- **FR-005b**: Il sistema MUST bloccare la pubblicazione quando un placeholder obbligatorio associato al modello non risulta usato nel contenuto o in una regola esplicita del modello.
- **FR-006**: Il sistema MUST impedire la pubblicazione di modelli con placeholder non risolti o non dichiarati.
- **FR-007**: Il sistema MUST descrivere campi complessi con schema strutturato di sotto-campi, tipi, obbligatorieta' e vincoli.
- **FR-007a**: Il sistema MUST impedire campi complessi definiti come JSON libero generico quando sono usati per il contratto dati verso GEBAN.
- **FR-007b**: Il sistema MUST validare i valori dei campi complessi rispetto allo schema dei sotto-campi dichiarato.
- **FR-008**: Il sistema MUST mantenere lo storico del contenuto sezioni tramite le versioni modello pubblicate.

### Key Entities

- **Sezione Modello**: sezione propria di una specifica versione modello.
- **Template Sezione**: contenuto opzionale copiabile in una versione modello; dopo la copia non aggiorna automaticamente i modelli esistenti.
- **Contenuto Strutturato Sezione**: contenuto controllato composto da blocchi e formattazioni ammesse, non HTML libero.
- **Voce Modello**: elemento ordinato della composizione modello.
- **Placeholder**: riferimento testuale a un campo richiesto.
- **Placeholder Disponibile**: placeholder associato alla versione modello e quindi esposto nel contratto dati.
- **Placeholder Usato**: placeholder presente nel contenuto strutturato o in una regola esplicita della versione modello.
- **Schema Dati**: descrizione strutturata dei campi richiesti.
- **Campo Complesso**: campo di tipo array, object, lista di oggetti, tabella o sezione ripetibile che richiede sotto-campi dichiarati.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Il 100% dei placeholder presenti in un modello pubblicabile e' dichiarato nel contratto dati.
- **SC-002**: Il 100% delle sezioni di una versione modello pubblicata resta immutabile e riproducibile tramite quella versione modello.
- **SC-003**: Il 100% dei campi complessi ha una struttura documentata prima della pubblicazione del modello.

## Assumptions

- Il contenuto sezione non usa HTML libero; eventuali dettagli tecnici del formato
  controllato saranno definiti nel planning.
- Le sezioni non hanno versionamento autonomo nel perimetro corrente; lo storico e'
  garantito dalla versione modello.
- Una libreria sezioni, se presente, fornisce template copiabili e non sezioni condivise
  vive tra piu' modelli.
- La risoluzione dei placeholder durante rendering/PDF e' approfondita nella spec generazione.
