# Feature Specification: AI MCP Readiness

**Feature Branch**: `008-ai-mcp-readiness`

**Created**: 2026-06-19

**Status**: Draft

**Input**: Estratta da `PROPOSTA-servizio-gestione-modelli-bando.md` sezione §15.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Mantenere documentazione AI-ready (Priority: P2)

Come team di progetto, voglio documentazione strutturata e aggiornata, cosi' da rendere il
servizio comprensibile anche da assistenti interni futuri.

**Why this priority**: AI/MCP non e' nel primo rilascio, ma la documentazione strutturata
riduce costo di integrazione futura.

**Independent Test**: le API e i contratti principali hanno esempi e descrizioni coerenti.

**Acceptance Scenarios**:

1. **Given** una API esposta a GEBAN, **When** viene documentata, **Then** include schema,
   esempi e casi di errore.
2. **Given** un modello pubblicato, **When** viene esposto il contratto dati, **Then** la
   struttura e' interpretabile da sistemi esterni autorizzati.

---

### User Story 2 - Preparare esposizione MCP controllata (Priority: P3)

Come architetto del servizio, voglio predisporre un futuro accesso MCP limitato e sicuro,
cosi' da abilitare assistenti interni senza compromettere documenti ufficiali.

**Why this priority**: e' evoluzione futura, non blocco MVP.

**Independent Test**: le capacita' candidate sono classificate in lettura, scrittura
limitata e azioni vietate.

**Acceptance Scenarios**:

1. **Given** un tool AI di consultazione, **When** accede a catalogo e contratti, **Then**
   vede solo dati autorizzati.
2. **Given** un tool AI propone testo, **When** la proposta viene usata, **Then** resta
   bozza/suggerimento fino a validazione umana e applicativa.

### Edge Cases

- Prompt injection.
- Richiesta AI di pubblicazione modello.
- Esposizione di dati non autorizzati.
- Confusione tra bozza AI e contenuto ufficiale.
- Segreti inclusi in prompt o risposta.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: La documentazione MUST includere contratti, esempi e schemi per API rilevanti.
- **FR-002**: Le funzionalita' AI/MCP MUST essere opzionali e non necessarie al flusso principale.
- **FR-003**: Nessun output AI MUST diventare ufficiale senza validazione applicativa e conferma prevista.
- **FR-004**: I tool AI/MCP MUST rispettare ruoli e autorizzazioni ordinarie.
- **FR-005**: Azioni come pubblicazione modello, generazione PDF ufficiale e download documenti MUST richiedere controllo esplicito.
- **FR-006**: Prompt e risposte AI MUST NOT contenere segreti, token o credenziali.
- **FR-007**: I contenuti suggeriti dall'AI MUST essere distinguibili da contenuti approvati.

### Key Entities

- **Assistente AI**: supporto non deterministico per consultazione o suggerimenti.
- **Tool MCP**: capacita' esposta a sistemi AI autorizzati.
- **Risorsa MCP**: dato consultabile in sola lettura.
- **Suggerimento AI**: contenuto non ufficiale.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Il 100% delle API candidate AI-ready ha documentazione strutturata.
- **SC-002**: Il 100% delle azioni AI candidate e' classificato per rischio e permesso.
- **SC-003**: Nessun flusso principale del primo rilascio dipende da AI/MCP.

## Assumptions

- AI/MCP non e' prerequisito del primo rilascio.
- La sicurezza AI eredita le regole della spec sicurezza.

