# Feature Specification: AI MCP Readiness

**Feature Branch**: `008-ai-mcp-readiness`

**Created**: 2026-06-19

**Status**: Draft

**Input**: Estratta da `PROPOSTA-servizio-gestione-modelli-bando.md` sezione §15.

## Clarifications

### Session 2026-06-22

- Q: Stiamo creando la spec da zero? -> A: No. La spec esiste gia' come draft di copertura; questa sessione la integra con i vincoli emersi da sicurezza, audit, documentazione e decisioni aperte.
- Q: AI/MCP fa parte del primo rilascio operativo? -> A: No. AI/MCP resta predisposizione futura: il primo rilascio non dipende da assistenti, tool MCP o generazione AI.
- Q: Un output AI puo' diventare testo ufficiale o azione ufficiale? -> A: No. Ogni output AI resta suggerimento o bozza fino a validazione deterministica, conferma umana quando prevista, autorizzazione e audit.
- Q: Quali capacita' MCP sono considerate candidate? -> A: In prima classificazione sono candidate letture controllate di catalogo, contratti, documentazione e stato; eventuali scritture devono restare limitate a bozze o validazioni non ufficiali.

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
3. **Given** una versione modello cambia, **When** la documentazione viene aggiornata,
   **Then** esempi, schema e changelog distinguono la nuova versione dalla precedente.
4. **Given** una decisione architetturale rilevante, **When** viene confermata, **Then** la
   documentazione AI-ready la rende rintracciabile senza dipendere da conversazioni.

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
3. **Given** un tool AI richiede pubblicazione, archiviazione, generazione ufficiale o
   download, **When** l'azione viene valutata, **Then** sono richiesti ruolo, conferma
   esplicita e audit secondo la spec sicurezza.
4. **Given** un prompt chiede dati non autorizzati o istruzioni in conflitto con le regole,
   **When** il tool valuta la richiesta, **Then** l'accesso viene rifiutato o limitato ai
   dati consentiti.

### Edge Cases

- Prompt injection.
- Richiesta AI di pubblicazione modello.
- Richiesta AI di archiviazione modello.
- Richiesta AI di generazione PDF ufficiale senza conferma.
- Richiesta AI di download documento.
- Esposizione di dati non autorizzati.
- Confusione tra bozza AI e contenuto ufficiale.
- Segreti inclusi in prompt o risposta.
- Tool AI con ruolo valido ma contesto non coerente con la risorsa richiesta.
- Tool chaining che tenta di aggirare autorizzazioni tramite piu' azioni consentite.
- Documentazione AI-ready non aggiornata rispetto ai contratti pubblicati.
- Suggerimento AI che introduce placeholder non presenti nel contratto dati.
- Assistente che inventa campi o stati non previsti dalle spec.
- Audit non registrabile per azione avviata tramite tool AI/MCP.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: La documentazione MUST includere contratti, esempi e schemi per API rilevanti.
- **FR-002**: Le funzionalita' AI/MCP MUST essere opzionali e non necessarie al flusso principale.
- **FR-003**: Nessun output AI MUST diventare ufficiale senza validazione applicativa e conferma prevista.
- **FR-004**: I tool AI/MCP MUST rispettare ruoli e autorizzazioni ordinarie.
- **FR-005**: Azioni come pubblicazione modello, generazione PDF ufficiale e download documenti MUST richiedere controllo esplicito.
- **FR-006**: Prompt e risposte AI MUST NOT contenere segreti, token o credenziali.
- **FR-007**: I contenuti suggeriti dall'AI MUST essere distinguibili da contenuti approvati.
- **FR-008**: La documentazione AI-ready MUST includere, per ogni contratto rilevante, scopo, attori ammessi, schema, esempi di successo, esempi di errore e requisiti di autorizzazione.
- **FR-009**: La documentazione AI-ready MUST includere changelog delle versioni modello pubblicate e decisioni architetturali rilevanti.
- **FR-010**: Ogni capacita' AI/MCP candidata MUST essere classificata almeno come sola lettura, scrittura limitata, azione sensibile con conferma o azione vietata.
- **FR-011**: Le capacita' candidate in sola lettura MUST limitarsi a dati autorizzati, come catalogo, modelli pubblicati, campi richiesti, schemi, stato generazioni consultabile e documentazione tecnica consentita.
- **FR-012**: Le capacita' candidate di scrittura limitata MUST restare confinate a bozze, suggerimenti, validazioni o generazioni bozza e non possono produrre effetti ufficiali senza il flusso ordinario.
- **FR-013**: Pubblicazione modello, archiviazione, generazione ufficiale e download documenti tramite AI/MCP MUST seguire gli stessi ruoli, conferme esplicite e audit delle API ordinarie.
- **FR-014**: Le azioni vietate MUST includere modifica automatica di modelli pubblicati, pubblicazione automatica, generazione ufficiale non supervisionata, invio automatico di documenti e accesso a segreti o token.
- **FR-015**: Ogni azione AI/MCP che produce, modifica o espone dati rilevanti MUST essere auditabile con attore, tool, intenzione, target, esito e payload minimo sanificato.
- **FR-016**: I suggerimenti AI per sezioni, placeholder o testi MUST essere validati contro contratto dati e regole modello prima di poter entrare in una bozza utente.
- **FR-017**: Il sistema MUST impedire che contenuti AI vengano confusi con contenuti approvati, pubblicati o ufficiali.
- **FR-018**: La predisposizione AI/MCP MUST NOT introdurre un percorso alternativo per aggirare autorizzazioni, workflow di pubblicazione, idempotenza, audit o validazione deterministica.
- **FR-019**: Prompt, risposte e log AI/MCP MUST essere sanificati rispetto a segreti, token, credenziali e dati non autorizzati.
- **FR-020**: La documentazione AI-ready MUST dichiarare esplicitamente che GEBAN resta proprietario dei dati di processo e che GEMODO non diventa fonte autoritativa di dati GEBAN.

### Key Entities

- **Assistente AI**: supporto non deterministico per consultazione o suggerimenti.
- **Tool MCP**: capacita' esposta a sistemi AI autorizzati.
- **Risorsa MCP**: dato consultabile in sola lettura.
- **Suggerimento AI**: contenuto non ufficiale.
- **Capacita' AI/MCP Candidata**: possibile funzione futura classificata per rischio, permesso e confine operativo.
- **Classificazione Rischio Tool**: etichetta funzionale che distingue lettura, scrittura limitata, azione sensibile e azione vietata.
- **Conferma Esplicita**: consenso operativo richiesto prima di azioni sensibili avviate tramite AI/MCP.
- **Documentazione AI-Ready**: contratti, esempi, schemi, changelog e decisioni strutturate per essere interpretabili da persone e assistenti autorizzati.
- **Bozza AI**: contenuto proposto da AI che non e' pubblicato, ufficiale o operativo.
- **Audit AI/MCP**: evento che traccia uso di tool, attore, target, intenzione, esito e dati sanificati.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Il 100% delle API candidate AI-ready ha documentazione strutturata.
- **SC-002**: Il 100% delle azioni AI candidate e' classificato per rischio e permesso.
- **SC-003**: Nessun flusso principale del primo rilascio dipende da AI/MCP.
- **SC-004**: Il 100% delle capacita' AI/MCP sensibili richiede ruoli, conferma esplicita e audit prima di produrre effetti ufficiali.
- **SC-005**: Il 100% dei contenuti suggeriti da AI e salvabili in bozza resta distinguibile da contenuti approvati o pubblicati.
- **SC-006**: Il 100% della documentazione AI-ready per contratti pubblici include almeno un esempio di successo e un caso di errore.
- **SC-007**: Il 100% delle azioni vietate candidate viene documentato come non disponibile o non automatizzabile.
- **SC-008**: Nessun prompt, risposta o audit AI/MCP verificato contiene token, credenziali o segreti.

## Assumptions

- AI/MCP non e' prerequisito del primo rilascio.
- La sicurezza AI eredita le regole della spec sicurezza.
- La predisposizione AI/MCP puo' avanzare come documentazione e classificazione anche se
  l'implementazione dei tool viene rinviata.
- Le azioni ufficiali restano sempre basate su modelli pubblicati, dati validati,
  autorizzazioni backend e audit obbligatorio.
- La futura esposizione MCP, se approvata, partira' da capacita' di sola lettura e da
  scritture limitate a bozze o validazioni non ufficiali.
