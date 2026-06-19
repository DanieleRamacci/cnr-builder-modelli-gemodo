# Feature Specification: Frontend Builder E Consultazione

**Feature Branch**: `007-frontend-builder-consultazione`

**Created**: 2026-06-19

**Status**: Draft

**Input**: Estratta da `PROPOSTA-servizio-gestione-modelli-bando.md` sezioni §11 e §16.6.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Gestire modelli da interfaccia builder (Priority: P1)

Come gestore modelli, voglio usare un'interfaccia dedicata per configurare tipi,
categorie, modelli, campi e sezioni, cosi' da lavorare senza interventi tecnici sul codice.

**Why this priority**: il builder e' lo strumento operativo degli utenti interni.

**Independent Test**: un gestore puo' completare la configurazione base di un modello in
bozza dall'interfaccia.

**Acceptance Scenarios**:

1. **Given** un gestore autorizzato, **When** accede al builder, **Then** puo' gestire
   elementi coerenti con i propri ruoli.
2. **Given** un modello in bozza, **When** il gestore modifica campi e sezioni, **Then**
   vede lo stato aggiornato prima della pubblicazione.

---

### User Story 2 - Revisionare e pubblicare da interfaccia (Priority: P1)

Come approvatore modelli, voglio revisionare, pubblicare o archiviare versioni modello,
cosi' da controllare il catalogo operativo esposto a GEBAN.

**Why this priority**: la pubblicazione richiede un controllo umano.

**Independent Test**: un approvatore puo' portare una versione pronta a stato pubblicato
o archiviato secondo i permessi.

**Acceptance Scenarios**:

1. **Given** una versione pronta, **When** l'approvatore la pubblica, **Then** diventa
   visibile nel catalogo operativo.
2. **Given** una versione pubblicata, **When** viene archiviata, **Then** non e' piu'
   proposta per nuove generazioni.

---

### User Story 3 - Consultare generazioni (Priority: P2)

Come utente autorizzato, voglio consultare le generazioni documento, cosi' da vedere
stato, payload, esito validazione, riferimento file e audit.

**Why this priority**: la consultazione serve al supporto operativo e alla verifica.

**Independent Test**: una generazione esistente puo' essere trovata con filtri funzionali
e consultata nei suoi metadati.

**Acceptance Scenarios**:

1. **Given** esistono generazioni, **When** l'utente filtra per sistema e tipo documento,
   **Then** vede solo risultati coerenti con filtri e autorizzazioni.
2. **Given** una generazione fallita, **When** viene aperta, **Then** sono visibili esito e
   motivazione funzionale.

### Edge Cases

- Utente senza ruolo adeguato.
- Modello con validazioni incomplete.
- Generazione senza file disponibile.
- Lista vuota.
- Errore di salvataggio durante modifica bozza.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: L'interfaccia MUST permettere gestione di tipi documento e categorie secondo autorizzazione.
- **FR-002**: L'interfaccia MUST permettere gestione di modelli, versioni, campi e sezioni.
- **FR-003**: L'interfaccia MUST distinguere bozza, revisione, pubblicazione e archiviazione.
- **FR-004**: L'interfaccia MUST mostrare errori di validazione del modello prima della pubblicazione.
- **FR-005**: L'interfaccia MUST permettere consultazione di generazioni, stato, payload, validazione e riferimento file.
- **FR-006**: L'interfaccia MUST rispettare le autorizzazioni applicative definite dalla spec sicurezza.
- **FR-007**: GEBAN MUST NOT usare questo frontend per compilare dati di processo.

### Key Entities

- **Utente Builder**: operatore interno del servizio modelli.
- **Schermata Modello**: vista di gestione modello/versione.
- **Schermata Campi**: vista di gestione contratto dati.
- **Schermata Sezioni**: vista di gestione contenuti.
- **Schermata Generazioni**: vista di consultazione documenti generati.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un gestore autorizzato puo' creare una bozza modello completa senza modifiche al codice.
- **SC-002**: Un approvatore autorizzato puo' pubblicare o archiviare una versione modello dall'interfaccia.
- **SC-003**: Un utente autorizzato puo' consultare stato e metadati di una generazione esistente.

## Assumptions

- Le API backend necessarie sono definite nelle spec builder, generazione, storage e sicurezza.
- Il design visuale dettagliato verra' definito dopo la conferma dello stack frontend.

