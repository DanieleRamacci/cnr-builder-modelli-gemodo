# Feature Specification: Storage Idempotenza E Consultazione

**Feature Branch**: `005-storage-idempotenza-consultazione`

**Created**: 2026-06-19

**Status**: Draft

**Input**: Estratta da `PROPOSTA-servizio-gestione-modelli-bando.md` sezioni §9.7-§9.8, §11.2, §13, §14 e §16.4.

## Clarifications

### Session 2026-06-22

- Q: Stiamo creando la spec da zero? -> A: No. La spec esiste gia' come draft di copertura; questa sessione la integra con decisioni e vincoli emersi da generazione PDF, sicurezza/audit e proposta sorgente.
- Q: Qual e' lo storage definitivo? -> A: La spec non vincola il backend fisico. Il servizio deve restituire a GEBAN un riferimento documentale stabile; documentale, storage compatibile S3 o altro backend approvato restano dettagli nascosti dal contratto.
- Q: Come gestire la rigenerazione volontaria dopo correzione dati? -> A: Una rigenerazione volontaria deve usare una nuova chiave funzionale, ad esempio nuovo contesto esterno, revisione esplicita o tipo output distinto; la stessa chiave con dati diversi resta conflitto.
- Q: Qual e' il confine con la generazione PDF? -> A: La spec `004` copre produzione deterministica del file e fallimenti di rendering; questa spec copre persistenza del riferimento, stato consultabile, download/recupero e idempotenza.

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
3. **Given** un documento ufficiale generato correttamente, **When** il riferimento viene
   restituito a GEBAN, **Then** il riferimento non espone il dettaglio fisico dello storage.

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
3. **Given** GEBAN vuole rigenerare dopo una correzione dati, **When** invia una richiesta
   con nuova revisione o nuovo contesto esplicito, **Then** il servizio la tratta come una
   nuova generazione tracciata.

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
3. **Given** un utente o client non autorizzato, **When** richiede download o stato,
   **Then** il servizio rifiuta l'accesso e l'evento e' auditabile.

### Edge Cases

- Retry dopo timeout di rete.
- Storage non disponibile.
- Documento generato ma riferimento non salvato.
- Download richiesto per documento inesistente.
- Rigenerazione volontaria dopo correzione dati.
- Stessa chiave idempotente con tipo output diverso.
- Stessa chiave idempotente con payload semanticamente uguale ma ordinamento dei campi
  diverso.
- File presente nello storage ma metadati di generazione incompleti.
- Riferimento documentale non piu' recuperabile.
- Download richiesto per generazione non completata o fallita.
- Richiesta di stato/download con token valido ma contesto GEBAN non coerente.
- Audit di download o rifiuto autorizzativo non registrabile.

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
- **FR-009**: Il riferimento restituito a GEBAN MUST essere stabile e utilizzabile dai moduli autorizzati senza esporre dettagli fisici dello storage.
- **FR-010**: Il sistema MUST conservare per ogni generazione sistema richiedente, contesto esterno, versione modello, tipo output, bozza/ufficiale, stato, timestamp, attore o client responsabile, esito validazione, snapshot dati minimo e riferimento file quando disponibile.
- **FR-011**: Il sistema MUST usare una rappresentazione normalizzata dei dati rilevanti per confrontare richieste idempotenti e distinguere retry identici da richieste divergenti.
- **FR-012**: Una rigenerazione volontaria dopo correzione dati MUST richiedere una nuova chiave funzionale o revisione esplicita; non puo' sovrascrivere una generazione gia' associata alla stessa chiave con dati diversi.
- **FR-013**: Se il file viene prodotto ma il riferimento documentale non viene salvato o non e' recuperabile, lo stato MUST rendere evidente l'anomalia e non presentare la generazione come completata correttamente.
- **FR-014**: Download e consultazione stato MUST rispettare le autorizzazioni definite nella spec sicurezza e devono essere auditabili.
- **FR-015**: Il sistema MUST auditare download, consultazione di stato rilevante, conflitti idempotenti e fallimenti di storage secondo la spec sicurezza.
- **FR-016**: Il sistema MUST restituire errori funzionali distinti per documento inesistente, non autorizzato, non ancora disponibile, fallito, conflitto idempotente e riferimento non recuperabile.
- **FR-017**: Il sistema MUST NOT esporre snapshot dati, payload completo o dettagli storage a utenti o client non autorizzati.
- **FR-018**: Gli stati di generazione esposti a GEBAN MUST essere coerenti con il contratto pubblico e non dipendere da nomi interni del backend storage.

### Key Entities

- **Documento Generato**: record di generazione.
- **Riferimento Documentale**: URI o identificativo restituito a GEBAN.
- **Chiave Idempotente**: combinazione funzionale che identifica una richiesta ripetibile.
- **Stato Generazione**: stato corrente della generazione.
- **Revisione Generazione**: identificatore funzionale usato quando GEBAN richiede una
  nuova generazione volontaria dopo correzione dati.
- **Snapshot Dati Generazione**: dati minimi conservati per riproducibilita', idempotenza
  e audit, senza diventare fonte autoritativa GEBAN.
- **Metadati Documento**: nome file, tipo output, hash, timestamp, stato, attore/client e
  riferimento file quando disponibile.
- **Errore Storage**: anomalia nel salvataggio o recupero del riferimento documentale.
- **Evento Download**: audit event relativo al recupero o tentativo di recupero del
  documento.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Il 100% dei documenti generati con successo espone un riferimento recuperabile.
- **SC-002**: Il 100% dei retry identici non crea duplicati.
- **SC-003**: Il 100% dei retry con dati divergenti sulla stessa chiave produce conflitto.
- **SC-004**: Il 100% dei download riusciti e dei download rifiutati e' auditabile.
- **SC-005**: Il 100% delle generazioni presentate come completate contiene riferimento,
  stato, timestamp, versione modello e tipo output.
- **SC-006**: Il 100% delle rigenerazioni volontarie accettate usa una nuova chiave
  funzionale o revisione esplicita.
- **SC-007**: Il 100% degli stati esposti distingue correttamente generazione richiesta,
  completata, fallita, annullata e riferimento non recuperabile quando applicabile.

## Assumptions

- Il backend fisico di storage verra' confermato nel piano tecnico; la spec richiede un
  riferimento documentale stabile e nasconde il dettaglio fisico a GEBAN.
- La politica di rigenerazione volontaria usa come default nuova chiave funzionale o
  revisione esplicita; la stessa chiave con dati diversi resta conflitto.
- Le regole dettagliate di autorizzazione download sono nella spec sicurezza.
- La produzione deterministica del PDF e' approfondita nella spec generazione.
- Il riferimento documentale deve restare adatto a GEBAN e ai moduli downstream
  autorizzati, senza rendere GEMODO fonte autoritativa dei dati GEBAN.
