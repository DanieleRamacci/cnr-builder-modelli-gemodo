# Feature Specification: Frontend Builder E Consultazione

**Feature Branch**: `007-frontend-builder-consultazione`

**Created**: 2026-06-19

**Status**: Draft

**Input**: Estratta da `PROPOSTA-servizio-gestione-modelli-bando.md` sezioni §11 e §16.6.

## Clarifications

### Session 2026-06-22

- Q: Stiamo creando la spec da zero? -> A: No. La spec esiste gia' come draft di copertura; questa sessione la integra con decisioni emerse da builder, sezioni, storage/idempotenza e sicurezza.
- Q: Qual e' il confine con GEBAN? -> A: GEBAN non usa il frontend GEMODO per compilare dati di processo; GEBAN usa le API catalogo/contratto, costruisce la propria maschera e invia richieste di generazione.
- Q: Le autorizzazioni sono applicate dal frontend? -> A: Il frontend abilita, nasconde o disabilita azioni in base a ruolo e contesto, ma il controllo autoritativo resta sempre nel servizio backend secondo la spec sicurezza.
- Q: Il design visuale e lo stack frontend fanno parte di questa spec? -> A: No. Questa spec definisce funzioni, flussi e stati utente; stack e dettagli visuali saranno definiti nel piano tecnico.

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
3. **Given** una versione pubblicata, **When** il gestore vuole modificarne il contenuto,
   **Then** l'interfaccia indirizza alla creazione o modifica di una bozza derivata e non
   consente modifica diretta della versione pubblicata.
4. **Given** il gestore compone sezioni con placeholder, **When** inserisce contenuti,
   **Then** l'interfaccia propone placeholder disponibili e mostra anomalie funzionali
   senza richiedere digitazione tecnica libera.

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
3. **Given** una versione con errori di contratto dati o placeholder, **When** l'utente
   tenta la pubblicazione, **Then** l'interfaccia mostra i blocchi restituiti dal servizio
   e non presenta la pubblicazione come riuscita.
4. **Given** un utente senza ruolo approvativo richiesto, **When** accede a una versione
   pubblicabile, **Then** non puo' completare pubblicazione o archiviazione dall'interfaccia.

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
3. **Given** una generazione completata, **When** l'utente autorizzato la apre, **Then**
   vede stato, versione modello, tipo output, bozza/ufficiale, metadati file e azioni di
   download consentite.
4. **Given** una generazione non recuperabile o non ancora completata, **When** l'utente
   richiede il download, **Then** l'interfaccia mostra uno stato coerente e non suggerisce
   che il file sia disponibile.

### Edge Cases

- Utente senza ruolo adeguato.
- Token scaduto o sessione non piu' autorizzata.
- Utente con ruolo GEBAN di generazione che tenta accesso al builder GEMODO.
- Utente builder che tenta consultazione o download non consentiti.
- Modello con validazioni incomplete.
- Versione modello pubblicata o archiviata mentre un utente sta modificando una bozza collegata.
- Tentativo di pubblicare una versione non approvata quando il workflow richiede approvazione separata.
- Placeholder non disponibili o campi complessi incompleti durante composizione sezioni.
- Generazione senza file disponibile.
- Generazione con riferimento documentale non recuperabile.
- Download richiesto per generazione fallita, annullata o non completata.
- Payload o snapshot dati non visualizzabile per autorizzazione insufficiente.
- Lista vuota.
- Errore di salvataggio durante modifica bozza.
- Errore funzionale restituito dal servizio che non deve esporre token, segreti o dettagli tecnici.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: L'interfaccia MUST permettere gestione di tipi documento e categorie secondo autorizzazione.
- **FR-002**: L'interfaccia MUST permettere gestione di modelli, versioni, campi e sezioni.
- **FR-003**: L'interfaccia MUST distinguere bozza, revisione, pubblicazione e archiviazione.
- **FR-004**: L'interfaccia MUST mostrare errori di validazione del modello prima della pubblicazione.
- **FR-005**: L'interfaccia MUST permettere consultazione di generazioni, stato, payload, validazione e riferimento file.
- **FR-006**: L'interfaccia MUST rispettare le autorizzazioni applicative definite dalla spec sicurezza.
- **FR-007**: GEBAN MUST NOT usare questo frontend per compilare dati di processo.
- **FR-008**: L'interfaccia MUST mostrare o abilitare azioni coerenti con ruolo, stato della risorsa e contesto operativo, fermo restando che l'autorizzazione definitiva e' applicata dal servizio backend.
- **FR-009**: L'interfaccia MUST gestire i workflow di versione modello `BOZZA`, `IN_REVISIONE`, `APPROVATO`, `PUBBLICATO`, `ARCHIVIATO` e `SOSPESO` coerentemente con le spec builder e sicurezza.
- **FR-010**: L'interfaccia MUST impedire modifica diretta di contenuti, campi e sezioni di versioni pubblicate e deve rendere chiara la creazione o modifica di bozze derivate.
- **FR-011**: L'interfaccia MUST supportare la composizione di sezioni con contenuto strutturato controllato e placeholder selezionabili tra quelli disponibili per la versione modello.
- **FR-012**: L'interfaccia MUST mostrare blocchi di pubblicazione relativi a campi richiesti, placeholder, schema dati, sezioni e validazioni di modello.
- **FR-013**: L'interfaccia MUST rendere evidente quando una generazione e' bozza o ufficiale.
- **FR-014**: L'interfaccia MUST consentire ricerca o filtro delle generazioni per criteri funzionali almeno su sistema richiedente, tipo documento/categoria, stato, periodo e autorizzazioni applicabili.
- **FR-015**: L'interfaccia MUST mostrare per una generazione consultabile almeno stato, timestamp, sistema richiedente, versione modello, tipo output, esito validazione, riferimento file quando disponibile e motivazione funzionale in caso di errore.
- **FR-016**: L'interfaccia MUST consentire download solo quando stato e autorizzazione lo permettono e deve mostrare stati distinti per file non disponibile, generazione fallita, riferimento non recuperabile e accesso non autorizzato.
- **FR-017**: L'interfaccia MUST NOT esporre payload completo, snapshot dati, audit dettagliato o metadati sensibili a utenti non autorizzati.
- **FR-018**: L'interfaccia MUST mostrare stati vuoti, caricamento, errore funzionale e salvataggio fallito in modo comprensibile per l'utente, senza presentare come completate operazioni non confermate dal servizio.
- **FR-019**: Le azioni sensibili avviate dall'interfaccia, incluse pubblicazione, archiviazione, consultazione rilevante e download, MUST essere coerenti con gli eventi audit previsti dalla spec sicurezza.
- **FR-020**: L'interfaccia MUST mantenere separati i percorsi operativi del builder GEMODO dalla consultazione/generazione documenti del flusso GEBAN.

### Key Entities

- **Utente Builder**: operatore interno del servizio modelli.
- **Utente Consultazione**: utente o client autorizzato a visualizzare stato e metadati di generazioni documento.
- **Schermata Modello**: vista di gestione modello/versione.
- **Schermata Campi**: vista di gestione contratto dati.
- **Schermata Sezioni**: vista di gestione contenuti.
- **Schermata Generazioni**: vista di consultazione documenti generati.
- **Azione UI Autorizzata**: comando visibile o eseguibile in base a ruolo, stato risorsa e contesto, con enforcement finale backend.
- **Stato UI Versione Modello**: rappresentazione utente dello stato della versione modello e delle transizioni ammesse.
- **Filtro Consultazione Generazioni**: criterio funzionale usato per trovare generazioni consultabili.
- **Vista Dettaglio Generazione**: pagina o pannello che mostra stato, metadati, validazione, riferimento file e azioni consentite.
- **Errore Funzionale UI**: messaggio comprensibile che traduce un blocco applicativo senza esporre dettagli tecnici o sensibili.
- **Payload Consultabile**: dati ricevuti o snapshot visualizzabili solo quando autorizzazione e finalita' lo consentono.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un gestore autorizzato puo' creare una bozza modello completa senza modifiche al codice.
- **SC-002**: Un approvatore autorizzato puo' pubblicare o archiviare una versione modello dall'interfaccia.
- **SC-003**: Un utente autorizzato puo' consultare stato e metadati di una generazione esistente.
- **SC-004**: Il 100% delle azioni non consentite dal ruolo o dallo stato della risorsa non viene presentato come completabile dall'interfaccia e resta comunque rifiutabile dal backend.
- **SC-005**: Il 100% dei blocchi di pubblicazione restituiti dal servizio viene mostrato all'utente come errore funzionale comprensibile.
- **SC-006**: Il 100% delle generazioni consultate distingue stato, bozza/ufficiale, disponibilita' file e autorizzazione al download.
- **SC-007**: Il 100% delle schermate principali del builder e della consultazione gestisce lista vuota, errore funzionale e salvataggio o download non riuscito.
- **SC-008**: Nessun flusso utente previsto richiede a GEBAN di compilare dati nel frontend GEMODO.

## Assumptions

- Le API backend necessarie sono definite nelle spec builder, generazione, storage e sicurezza.
- Il design visuale dettagliato verra' definito dopo la conferma dello stack frontend.
- La nomenclatura dei ruoli applicativi segue la spec sicurezza, inclusi i ruoli `GEMODO_*`, `DOCUMENTI_*` e `SYSTEM_GEBAN`.
- Il frontend non e' fonte autoritativa per autorizzazioni, stato di pubblicazione, audit, idempotenza o disponibilita' file.
- La consultazione del payload completo e degli audit dettagliati e' limitata ai casi autorizzati e non sostituisce la fonte dati GEBAN.
