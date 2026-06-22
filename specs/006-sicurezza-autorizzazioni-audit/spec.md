# Feature Specification: Sicurezza Autorizzazioni E Audit

**Feature Branch**: `006-sicurezza-autorizzazioni-audit`

**Created**: 2026-06-19

**Status**: Draft

**Input**: Estratta da `PROPOSTA-servizio-gestione-modelli-bando.md` sezioni §12, §8.11 e §12.9.

**Documento operativo collegato**: [keycloak-jwt.md](./keycloak-jwt.md)

## Clarifications

### Session 2026-06-22

- Q SEC-006-001: Come deve arrivare l'identita' utente da GEBAN a GEMODO nelle chiamate operative? -> A: Scelta provvisoria da confermare col team: GEBAN chiama GEMODO con un token delegato emesso da Keycloak per audience GEMODO, contenente sia il client chiamante `geban-backend` sia l'identita' dell'utente reale. Questa scelta resta aperta fino a conferma tecnica del team GEBAN/Keycloak.
- Q: Dove vengono gestiti utenti e ruoli applicativi? -> A: Utenti e assegnazione ruoli sono gestiti in Keycloak, non in GEMODO. GEMODO legge i ruoli dal JWT e applica autorizzazioni backend. Per il builder usa ruoli GEMODO; per chiamate da GEBAN usa ruoli/claim di generazione o consultazione.

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
4. **Given** GEBAN chiama GEMODO per un'operazione utente, **When** il token delegato viene
   validato, **Then** GEMODO identifica sia `geban-backend` sia l'utente reale.
5. **Given** un utente accede al builder GEMODO, **When** il JWT contiene un ruolo GEMODO
   valido, **Then** GEMODO abilita solo le azioni previste da quel ruolo.

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
- Token delegato con audience GEMODO valida ma senza identita' utente reale.
- Token con utente reale ma client chiamante diverso da `geban-backend`.
- Token con ruolo GEBAN di generazione usato per accedere al builder GEMODO.
- Token con ruolo GEMODO builder usato per generare documenti dal flusso GEBAN.
- Contesto GEBAN non coerente con l'azione richiesta.
- Audit fallito durante operazione sensibile.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Tutte le API protette MUST richiedere identita' verificabile.
- **FR-002**: Il servizio MUST verificare chiamante, audience, scadenza e ruoli o claim contestuali.
- **FR-003**: Il servizio MUST distinguere utenti builder, sistema GEBAN e client tecnici.
- **FR-003a**: Per le operazioni utente richieste da GEBAN, il servizio SHOULD ricevere un token delegato Keycloak con audience GEMODO, client chiamante `geban-backend` e identita' dell'utente reale; questa scelta e' provvisoria fino a conferma del team.
- **FR-003b**: Il servizio MUST considerare non valida una chiamata utente da GEBAN se non riesce a identificare sia il client chiamante autorizzato sia l'utente reale, salvo API tecniche esplicitamente censite.
- **FR-003c**: GEMODO MUST NOT gestire utenti, password o assegnazione ufficiale dei ruoli applicativi; tali responsabilita' restano in Keycloak o nel sistema identita' collegato.
- **FR-003d**: GEMODO MUST leggere dal JWT i ruoli applicativi e applicare autorizzazioni lato backend in base al canale: ruoli GEMODO per builder, ruoli/claim GEBAN per generazione e consultazione documenti.
- **FR-004**: Il servizio MUST applicare autorizzazioni lato backend.
- **FR-005**: Il servizio MUST supportare almeno i ruoli `GEMODO_ADMIN`, `GEMODO_MODELLI_GESTORE`, `GEMODO_MODELLI_VIEWER`, `DOCUMENTI_GENERATORE`, `DOCUMENTI_VIEWER` e `SYSTEM_GEBAN`.
- **FR-005a**: `GEMODO_ADMIN` MUST poter eseguire tutte le operazioni interne GEMODO.
- **FR-005b**: `GEMODO_MODELLI_GESTORE` MUST poter creare, modificare, pubblicare e archiviare modelli nel builder, salvo futura introduzione di ruoli approvativi separati.
- **FR-005c**: `DOCUMENTI_GENERATORE` MUST essere usato per richieste di generazione documenti provenienti dal flusso GEBAN; non abilita la gestione del builder GEMODO.
- **FR-006**: Il servizio MUST auditare creazione, modifica, revisione, pubblicazione e archiviazione modello.
- **FR-007**: Il servizio MUST auditare validazioni fallite, generazioni, download ed errori autorizzativi.
- **FR-008**: Nessun segreto, token o credenziale MUST essere esposto in log, audit o risposte applicative.

### Key Entities

- **Identita' Utente**: utente reale propagato o autenticato.
- **Client Chiamante**: sistema applicativo che invoca il servizio.
- **Ruolo Applicativo**: permesso funzionale.
- **Ruolo GEMODO**: ruolo applicativo letto dal JWT e valido per le funzionalita' interne GEMODO.
- **Ruolo/Claim GEBAN**: ruolo o claim contestuale letto dal JWT delegato e valido per generazione, download o consultazione nel flusso GEBAN.
- **Contesto GEBAN**: contesto operativo passato da GEBAN.
- **Audit Event**: registrazione di operazione rilevante.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Il 100% delle operazioni sensibili produce un audit event.
- **SC-002**: Il 100% delle richieste prive di autorizzazione adeguata viene rifiutato.
- **SC-003**: Il 100% delle generazioni autorizzate conserva attore o client tecnico responsabile.

## Assumptions

- Keycloak e JWT sono il modello autenticativo di riferimento.
- Utenti, password e assegnazione ruoli sono gestiti in Keycloak o nel sistema identita'
  collegato; GEMODO consuma i ruoli presenti nel JWT.
- Il ruolo approvatore separato per il builder non e' obbligatorio nella prima versione e
  potra' essere introdotto in seguito se il processo lo richiede.
- La modalita' token delegato GEBAN -> GEMODO e' una scelta provvisoria da confermare con il team tecnico prima dell'implementazione.
- Eventuali integrazioni future non fanno parte del perimetro operativo di questa spec.

## Open Decisions

- **SEC-006-001**: Confermare con il team GEBAN/Keycloak se le chiamate utente verso
  GEMODO useranno token delegato con audience GEMODO, client `geban-backend` e identita'
  utente reale nello stesso JWT.
