# Feature Specification: Generazione Documenti PDF

**Feature Branch**: `004-generazione-documenti-pdf`

**Created**: 2026-06-19

**Status**: Draft

**Input**: Estratta da `PROPOSTA-servizio-gestione-modelli-bando.md` sezioni §9.6, §13 e §16.5.

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

### Edge Cases

- Template con placeholder non risolti.
- Errore durante rendering.
- Errore durante produzione file.
- Differenza tra bozza e ufficiale non marcata.
- Richiesta di formato non supportato.

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

### Key Entities

- **Richiesta Generazione**: richiesta di produzione documento.
- **Documento Generato**: risultato della generazione.
- **PDF Bozza**: documento non ufficiale.
- **PDF Ufficiale**: documento ufficiale tracciato.
- **Snapshot Dati**: dati validati usati per generare il documento.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Il 100% dei documenti ufficiali e' collegato a modello versione e snapshot dati.
- **SC-002**: Il 100% delle richieste con payload non valido non produce file ufficiale.
- **SC-003**: Il 100% dei documenti generati distingue bozza e ufficiale.

## Assumptions

- La conservazione e il download sono approfonditi nella spec storage/idempotenza.
- Firma, protocollo e pubblicazione restano fuori scope.

