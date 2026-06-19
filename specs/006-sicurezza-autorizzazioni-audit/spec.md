# Feature Specification: Sicurezza Autorizzazioni E Audit

**Feature Branch**: `006-sicurezza-autorizzazioni-audit`

**Created**: 2026-06-19

**Status**: Draft

**Input**: Estratta da `PROPOSTA-servizio-gestione-modelli-bando.md` sezioni §12, §8.11, §12.9 e §15.3.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Proteggere le API con identita' verificabile (Priority: P1)

Come servizio modelli, voglio accettare solo chiamate con identita' e contesto verificabili,
cosi' da proteggere catalogo, builder, generazione e download.

**Why this priority**: nessun flusso operativo puo' essere sicuro senza identita' certa.

**Independent Test**: chiamate senza identita' valida non accedono a risorse protette.

**Acceptance Scenarios**:

1. **Given** una richiesta senza credenziali valide, **When** accede a una risorsa
   protetta, **Then** il servizio la rifiuta.
2. **Given** una richiesta con identita' valida ma audience non coerente, **When** accede
   al servizio, **Then** il servizio la rifiuta.

---

### User Story 2 - Autorizzare azioni per ruolo e contesto (Priority: P1)

Come amministratore del servizio, voglio che ogni azione sia consentita solo a ruoli o
contesti autorizzati, cosi' da separare builder, generazione, consultazione e chiamate
tecniche.

**Why this priority**: ruoli e contesto impediscono modifiche o generazioni improprie.

**Independent Test**: un utente con ruolo insufficiente non puo' pubblicare modelli o
generare documenti.

**Acceptance Scenarios**:

1. **Given** un gestore modelli, **When** modifica una bozza, **Then** l'azione e'
   consentita se il ruolo e' adeguato.
2. **Given** un utente senza ruolo di approvazione, **When** tenta pubblicazione modello,
   **Then** il servizio la impedisce.
3. **Given** GEBAN propaga un contesto utente autorizzato, **When** richiede generazione,
   **Then** il servizio puo' collegare richiesta, utente e contesto.

---

### User Story 3 - Auditare operazioni rilevanti (Priority: P1)

Come responsabile applicativo, voglio auditare le operazioni sensibili, cosi' da poter
ricostruire chi ha fatto cosa e quando.

**Why this priority**: il servizio produce documenti amministrativi ufficiali.

**Independent Test**: ogni operazione sensibile crea un evento audit con attore, azione,
target e timestamp.

**Acceptance Scenarios**:

1. **Given** una pubblicazione modello, **When** l'operazione si conclude, **Then** viene
   registrato un audit event.
2. **Given** una generazione documento, **When** l'operazione si conclude o fallisce,
   **Then** viene registrato l'esito.
3. **Given** un errore autorizzativo, **When** il servizio rifiuta la richiesta, **Then**
   l'evento viene auditato.

### Edge Cases

- Chiamata tecnica senza utente reale.
- Token valido ma privo di ruolo applicativo.
- Contesto GEBAN non coerente con l'azione richiesta.
- Tentativo AI/MCP di eseguire azione non consentita.
- Audit fallito durante operazione sensibile.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Tutte le API protette MUST richiedere identita' verificabile.
- **FR-002**: Il servizio MUST verificare chiamante, audience, scadenza e ruoli o claim contestuali.
- **FR-003**: Il servizio MUST distinguere utenti builder, sistema GEBAN e client tecnici.
- **FR-004**: Il servizio MUST applicare autorizzazioni lato backend.
- **FR-005**: Il servizio MUST supportare ruoli per amministrazione modelli, revisione, approvazione, generazione, consultazione e chiamate tecniche.
- **FR-006**: Il servizio MUST auditare creazione, modifica, revisione, pubblicazione e archiviazione modello.
- **FR-007**: Il servizio MUST auditare validazioni fallite, generazioni, download ed errori autorizzativi.
- **FR-008**: I tool AI/MCP futuri MUST rispettare le stesse autorizzazioni delle API ordinarie.
- **FR-009**: Nessun segreto, token o credenziale MUST essere esposto in log, audit o output AI.

### Key Entities

- **Identita' Utente**: utente reale propagato o autenticato.
- **Client Chiamante**: sistema applicativo che invoca il servizio.
- **Ruolo Applicativo**: permesso funzionale.
- **Contesto GEBAN**: contesto operativo passato da GEBAN.
- **Audit Event**: registrazione di operazione rilevante.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Il 100% delle operazioni sensibili produce un audit event.
- **SC-002**: Il 100% delle richieste prive di autorizzazione adeguata viene rifiutato.
- **SC-003**: Il 100% delle generazioni autorizzate conserva attore o client tecnico responsabile.

## Assumptions

- Keycloak e JWT sono il modello autenticativo di riferimento.
- Le policy precise di ruolo possono essere raffinate durante `clarify`.
- La sicurezza AI/MCP resta coerente con questa spec anche se AI non e' nel primo rilascio.

