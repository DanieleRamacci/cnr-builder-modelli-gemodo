# Feature Specification: Storage Idempotenza E Consultazione

**Feature Branch**: `005-storage-idempotenza-consultazione`

**Created**: 2026-06-19

**Status**: Draft

**Input**: Estratta da `PROPOSTA-servizio-gestione-modelli-bando.md` sezioni §9.7-§9.8, §11.2, §13, §14 e §16.4.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Salvare e restituire riferimento documentale (Priority: P1)

Come GEBAN, voglio ricevere un riferimento al documento generato, cosi' da proseguire il
workflow senza dipendere dal dettaglio tecnico dello storage.

**Why this priority**: il riferimento documentale e' l'output operativo verso GEBAN.

**Independent Test**: una generazione completata espone stato, riferimento, nome file e
metadati minimi.

**Acceptance Scenarios**:

1. **Given** un documento generato correttamente, **When** GEBAN consulta lo stato,
   **Then** riceve il riferimento documentale e i metadati disponibili.
2. **Given** un documento non ancora generato, **When** GEBAN consulta lo stato, **Then**
   riceve uno stato coerente con l'avanzamento.

---

### User Story 2 - Gestire idempotenza di generazione (Priority: P1)

Come GEBAN, voglio poter ripetere una richiesta senza creare duplicati, cosi' da gestire
retry tecnici in modo sicuro.

**Why this priority**: le integrazioni tra sistemi devono tollerare retry.

**Independent Test**: la stessa richiesta ripetuta con stessi dati restituisce lo stesso
documento; stessi identificativi con dati diversi producono conflitto.

**Acceptance Scenarios**:

1. **Given** una richiesta gia' completata, **When** GEBAN la ripete con stessi dati,
   **Then** il servizio restituisce il documento gia' generato.
2. **Given** stessa chiave idempotente ma dati diversi, **When** GEBAN ripete la richiesta,
   **Then** il servizio restituisce conflitto.

---

### User Story 3 - Consultare generazioni e download (Priority: P2)

Come utente autorizzato o sistema GEBAN, voglio consultare stato e scaricare documenti
generati, cosi' da verificare l'esito e recuperare il file quando consentito.

**Why this priority**: consultazione e download sono necessari dopo la generazione.

**Independent Test**: una generazione esistente puo' essere consultata e scaricata solo se
lo stato e le autorizzazioni lo consentono.

**Acceptance Scenarios**:

1. **Given** un documento generato, **When** viene richiesto il download, **Then** il
   servizio restituisce il file o il riferimento scaricabile.
2. **Given** una generazione fallita, **When** viene consultata, **Then** il servizio
   espone lo stato fallito e l'errore funzionale.

### Edge Cases

- Retry dopo timeout di rete.
- Storage non disponibile.
- Documento generato ma riferimento non salvato.
- Download richiesto per documento inesistente.
- Rigenerazione volontaria dopo correzione dati.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Il sistema MUST salvare un riferimento documentale per ogni documento generato con successo.
- **FR-002**: Il sistema MUST conservare nome file, hash quando disponibile, data generazione e stato.
- **FR-003**: Il sistema MUST esporre lo stato di una generazione.
- **FR-004**: Il sistema MUST consentire download o recupero del documento secondo autorizzazione.
- **FR-005**: Il sistema MUST applicare idempotenza su sistema richiedente, contesto esterno, versione modello e tipo output.
- **FR-006**: Richieste ripetute con stessi dati MUST restituire il documento esistente.
- **FR-007**: Richieste ripetute con stessa chiave ma dati diversi MUST restituire conflitto.
- **FR-008**: Il sistema MUST distinguere generazioni richieste, validate, generate, fallite e annullate.

### Key Entities

- **Documento Generato**: record di generazione.
- **Riferimento Documentale**: URI o identificativo restituito a GEBAN.
- **Chiave Idempotente**: combinazione funzionale che identifica una richiesta ripetibile.
- **Stato Generazione**: stato corrente della generazione.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Il 100% dei documenti generati con successo espone un riferimento recuperabile.
- **SC-002**: Il 100% dei retry identici non crea duplicati.
- **SC-003**: Il 100% dei retry con dati divergenti sulla stessa chiave produce conflitto.

## Assumptions

- Lo storage definitivo verra' confermato prima del piano tecnico.
- La politica esatta di rigenerazione volontaria richiede chiarimento.
- Le regole dettagliate di autorizzazione download sono nella spec sicurezza.

