# Feature Specification: Sezioni Placeholder E Versionamento

**Feature Branch**: `003-sezioni-placeholder-versionamento`

**Created**: 2026-06-19

**Status**: Draft

**Input**: Estratta da `PROPOSTA-servizio-gestione-modelli-bando.md` sezioni §5.5, §6, §8.7-§8.9 e §16.3.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Gestire sezioni riusabili (Priority: P1)

Come gestore modelli, voglio mantenere una libreria di sezioni riusabili e versionate,
cosi' da comporre modelli documentali coerenti e storicizzati.

**Why this priority**: senza sezioni versionate il modello non e' riproducibile.

**Independent Test**: una sezione creata e versionata puo' essere associata a una versione
modello senza perdere lo storico delle versioni precedenti.

**Acceptance Scenarios**:

1. **Given** una nuova sezione, **When** il gestore la salva, **Then** viene creata una
   versione iniziale.
2. **Given** una sezione gia' pubblicata o usata, **When** cambia il testo, **Then** viene
   creata una nuova versione.
3. **Given** una versione modello, **When** il gestore aggiunge sezioni, **Then** ogni voce
   conserva ordine, obbligatorieta' e riferimento alla versione sezione.

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

### Edge Cases

- Placeholder duplicati in piu' sezioni.
- Placeholder dichiarato ma non usato.
- Campo complesso con array vuoto.
- Sezione libera senza riferimento a catalogo.
- Cambio ordine sezioni su versione gia' pubblicata.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Il sistema MUST gestire una libreria di sezioni con versioni storicizzate.
- **FR-002**: Il sistema MUST associare sezioni versionate alle versioni modello.
- **FR-003**: Ogni voce modello MUST mantenere ordine e obbligatorieta'.
- **FR-004**: Il sistema MUST supportare placeholder nel testo delle sezioni.
- **FR-005**: Il sistema MUST validare che i placeholder usati siano dichiarati nel contratto dati.
- **FR-006**: Il sistema MUST impedire la pubblicazione di modelli con placeholder non risolti o non dichiarati.
- **FR-007**: Il sistema MUST descrivere campi complessi in modo sufficiente alla validazione.
- **FR-008**: Il sistema MUST mantenere storico delle versioni sezione usate da ogni modello.

### Key Entities

- **Sezione Catalogo**: sezione riusabile.
- **Versione Sezione**: testo versionato della sezione.
- **Voce Modello**: elemento ordinato della composizione modello.
- **Placeholder**: riferimento testuale a un campo richiesto.
- **Schema Dati**: descrizione strutturata dei campi richiesti.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Il 100% dei placeholder presenti in un modello pubblicabile e' dichiarato nel contratto dati.
- **SC-002**: Il 100% delle sezioni usate da una versione modello mantiene riferimento alla versione sezione.
- **SC-003**: Il 100% dei campi complessi ha una struttura documentata prima della pubblicazione del modello.

## Assumptions

- Il formato definitivo del contenuto testuale verra' confermato durante il planning.
- La risoluzione dei placeholder durante rendering/PDF e' approfondita nella spec generazione.

