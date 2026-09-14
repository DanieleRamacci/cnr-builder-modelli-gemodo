# Feature Specification: Sicurezza Autorizzazioni E Audit

**Feature Branch**: `006-sicurezza-autorizzazioni-audit`

**Created**: 2026-06-19

**Status**: Draft - aggiornata 2026-09-14 con modalita' ACE/context roles

**Input**: Estratta da `PROPOSTA-servizio-gestione-modelli-bando.md` sezioni §12, §8.11 e §12.9.

**Documento operativo collegato**: [keycloak-jwt.md](./keycloak-jwt.md)

## Clarifications

### Session 2026-09-14 (seconda sessione, perimetro contrattuale e propagazione da `001`)

- Q: `DEC-006-AUTORIZZAZIONI-PROFILO-GEBAN` (owner di questa spec) e' risolta? -> A:
  **Confermata**, in due parti. La parte ruoli/claim/audience/client e' implementata
  (vedi sessione sotto: JWT, `aud=gemodo-backend`, client `geban-backend`/
  `geri-angular-public`, ruoli diretti e ruoli ACE mappati via `role_mappings` in
  `backend/app/common/security.py`). La parte "impedire l'uso da chiamanti non
  autorizzati al profilo" era invece scoperta: verificato che
  `is_operazione_autorizzata()` e le liste `categorie_ammessi`/`tipologie_ammessi`/
  `modelli_versioni_ammessi` di `ProfiloDiIntegrazione` hanno un solo chiamante in
  tutto il repo (`backend/tests/support/fake_gemodo_client.py`, un fixture di test),
  non le route reali — qualunque chiamante con ruolo
  `DOCUMENTI_VIEWER`/`DOCUMENTI_GENERATORE` puo' oggi interrogare categorie/tipologie/
  modelli di qualunque profilo. La direzione per chiuderlo e' confermata nella `001`
  (`DEC-001-RELAZIONE-PROFILO-CATALOGO`): enforcement dentro le route
  catalogo/validazione gia' esistenti, con errore distinto per "fuori perimetro" vs
  "nel perimetro senza modello". Non ancora implementato.
- Q: Servono endpoint dedicati al profilo GEBAN? -> A: No (`DEC-001-API-PROFILO-GEBAN`,
  confermata nella `001`). L'enforcement per profilo resta dentro le route esistenti;
  introduce pero' nuovi codici errore funzionali nel contratto OpenAPI della `001`, da
  coordinare con GEBAN quando implementati.
- Q: Il registro contratti dati (`contratti_dati_ammessi`) e' di proprieta' di GEBAN o
  di un concetto piu' generale? -> A: Di un tipo documento, ereditata dall'Ufficio che
  lo possiede (`DEC-001-REGISTRO-CONTRATTI-DATI` e `DEC-001-UFFICIO-PROPRIETARIO`,
  confermate nella `001`) — non del sistema richiedente/applicazione che lo consuma.
  Rilevante per questa spec perche' distingue l'autorizzazione di scrittura
  (Ufficio proprietario) da quella di lettura/generazione (profilo consumer, gia'
  ambito di questa spec).
- Q: Come si autorizza un gestore modelli (`002`, `GEMODO_MODELLI_GESTORE`) a
  scrivere solo per il proprio Ufficio? -> A: Confermato (`DEC-002-GESTORE-UFFICIO-
  MAPPING`). Nessun meccanismo di autorizzazione nuovo: il gestore arriva dallo
  stesso `contexts.<app>.roles` ACE gia' costruito per il consumo. `role_mappings`
  (schema in `009`) guadagna un campo `ufficio:` sulle voci il cui
  `internal_permissions` include `GEMODO_MODELLI_GESTORE`, configurato a mano
  dall'admin GEMODO in coordinamento con chi gestisce ACE/Keycloak — stesso
  processo operativo gia' in uso per configurare `role_mappings` oggi.

### Session 2026-09-14

- Q: Il client reale GEBAN per l'integrazione e' `geban-backend` o un client ACE gia'
  esistente? -> A: Il team GEBAN ha indicato l'uso del client CNR/ACE che emette token
  dal realm `cnr` su `https://sso.test.si.cnr.it/auth/realms/cnr`; negli esempi ricevuti
  il client chiamante risulta `geri-angular-public`, il token contiene audience
  `gemodo-backend`, ruoli GEMODO in `resource_access.gemodo-backend.roles` e ruoli ACE
  nel claim `contexts.geban.roles`. Il client `geban-backend` resta valido come doppio
  tecnico di test/CI, ma l'integrazione reale deve supportare client ACE configurati e
  autorizzati.
- Q: GEMODO deve usare direttamente i ruoli ACE/GEBAN o continuare a usare solo ruoli
  client `gemodo-backend`? -> A: GEMODO deve continuare a ragionare internamente con
  permessi applicativi propri (`DOCUMENTI_VIEWER`, `DOCUMENTI_GENERATORE`,
  `GEMODO_MODELLI_VIEWER`, `GEMODO_MODELLI_GESTORE`, ecc.) ma puo' derivarli anche da
  ruoli esterni presenti nel token ACE tramite una mappa configurabile per contesto
  applicativo. I ruoli ACE non devono essere hard-coded nelle autorizzazioni endpoint.
- Q: Quali ruoli ACE/GEBAN autorizzano la creazione/generazione di documenti? -> A:
  `ROLE_GESTORE#geban`, `ROLE_MANAGER#geban`, `ROLE_COORDINATOR#geban` e
  `ROLE_USER#geban` abilitano la generazione/creazione di documenti nel flusso GEBAN,
  mappandosi al permesso GEMODO `DOCUMENTI_GENERATORE`; per la sola consultazione possono
  mappare anche a `DOCUMENTI_VIEWER`.
- Q: Quale ruolo ACE/GEBAN puo' creare o gestire modelli nel builder GEMODO? -> A: Solo
  `ROLE_MANAGER#geban` puo' essere mappato a un permesso di gestione modelli
  (`GEMODO_MODELLI_GESTORE`) per il perimetro GEBAN. Gli altri ruoli GEBAN non devono
  abilitare creazione, modifica, pubblicazione o archiviazione modelli.
- Q: L'audience `gemodo-backend` resta obbligatoria se si leggono i ruoli ACE? -> A: Si.
  Ogni token accettato dalle API GEMODO deve contenere audience `gemodo-backend`; il
  claim `contexts.geban.roles` prova il contesto/ruolo GEBAN, ma non sostituisce la
  destinazione del token verso GEMODO.
- Q: Come deve essere configurato il mapper ACE indicato dal team GEBAN? -> A: Sul client
  che emette il token verso GEMODO deve essere aggiunto o verificato un mapper ACE con
  contesto `geban`, `Add to access token` attivo e `Add to ID token`/`userinfo` non
  necessari. Il mapper deve produrre il claim `contexts.geban.roles`; se il client serve
  piu' applicativi, GEMODO considera solo i contesti presenti nella propria mappa
  autorizzativa.
- Q: Come si gestiscono altri applicativi o futuri tipi documento? -> A: La lettura dei
  ruoli esterni deve essere generalizzata per contesto (`contexts.<app>.roles`) e
  regolata da mapping configurabile che indichi sistema richiedente, contesto token,
  ruolo esterno, permesso GEMODO derivato e, dove necessario, tipo documento o API
  abilitate. Nuovi applicativi o ruoli non devono richiedere modifiche sparse al codice.

### Session 2026-07-29

- Q SEC-006-001: Come deve arrivare l'identita' utente da GEBAN a GEMODO nelle chiamate operative? -> A: **Risolto.** GEBAN chiama GEMODO con un token tecnico Keycloak (client credentials) del client `geban-backend`, con ruolo applicativo `DOCUMENTI_GENERATORE` assegnato al client stesso. L'identita' dell'utente reale e il contesto GEBAN (bando, azioni autorizzate) viaggiano nel payload della richiesta come dati applicativi e di audit, non come claim del token. L'autorizzazione resta sempre basata sul token verificato (client + ruolo), mai sul payload. Il token delegato/token exchange (identita' utente reale nel JWT) resta documentato come possibile evoluzione futura se un requisito di audit piu' stringente lo richiedera', ma non e' necessario per la prima release: evita una dipendenza da funzionalita' Keycloak non standard e da sviluppo aggiuntivo lato backend GEBAN. Questa decisione e' estesa dalla sessione 2026-09-14 per includere token ACE reali con ruoli in `contexts.geban.roles`.
- Q: Dove vengono gestiti utenti e ruoli applicativi? -> A: Utenti e assegnazione ruoli sono gestiti in Keycloak, non in GEMODO. GEMODO legge i ruoli dal JWT e applica autorizzazioni backend. Per il builder usa ruoli GEMODO; per chiamate da GEBAN usa ruoli/claim di generazione o consultazione.
- Q: Come trattare revisione e approvazione modello rispetto ai ruoli builder? -> A: La prima versione deve supportare il flusso minimo con gestore abilitato anche alla pubblicazione; la specifica riserva pero' ruoli separati di revisore e approvatore, attivabili se il processo CNR richiede separazione dei compiti prima dell'implementazione.
- Q: Il contesto autorizzativo nel payload puo' sostituire il JWT? -> A: No. Il payload puo' arricchire audit e contesto applicativo, ma autenticazione e autorizzazione derivano sempre dal token e dai claim verificabili (client chiamante e ruolo), mai dal contenuto del payload.
- Q: I ruoli applicativi GEMODO sono ruoli realm o ruoli client in Keycloak? -> A: Ruoli client, definiti sul client `gemodo-backend`. Il realm Keycloak (`cnr`) e' condiviso con altre applicazioni CNR: usare ruoli realm creerebbe rischio di collisione di nomi e inquinerebbe la lista ruoli condivisa. I ruoli GEMODO devono comparire nel JWT sotto `resource_access.gemodo-backend.roles`, mai come `realm_access.roles`.
- Q SEC-006-002: La prima release richiede separazione effettiva tra gestore, revisore e approvatore? -> A: **Risolto.** No. Per ora l'approvazione coincide con la pubblicazione: il ruolo `GEMODO_MODELLI_GESTORE` che porta il modello da `BOZZA` a `PUBBLICATO` vale come approvazione. Non e' richiesto un passaggio di approvazione da parte di altri ruoli. I ruoli riservati `GEMODO_MODELLI_REVISORE` e `GEMODO_MODELLI_APPROVATORE` restano definiti ma inattivi, da valutare e attivare in futuro se il processo CNR richiedera' un'approvazione da parte di altri soggetti.

### Session 2026-06-22

- Q: Le decisioni `SEC-006-001` e `SEC-006-002` bloccano la prosecuzione della definizione? -> A: No. Si procede con le assunzioni provvisorie gia' documentate; le decisioni restano da riaprire quando arrivera' la risposta del team e comunque prima dell'implementazione. (`SEC-006-001` e `SEC-006-002` risolte nella sessione 2026-07-29.)

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
2. **Given** il processo richiede approvatore separato e un utente non ha ruolo di
   approvazione, **When** tenta pubblicazione modello, **Then** il servizio la impedisce.
3. **Given** GEBAN propaga un contesto utente autorizzato, **When** richiede generazione,
   **Then** il servizio puo' collegare richiesta, utente e contesto.
4. **Given** GEBAN chiama GEMODO per una generazione documento, **When** il token tecnico
   `geban-backend` con ruolo `DOCUMENTI_GENERATORE` viene validato, **Then** GEMODO autorizza
   la richiesta e registra utente reale e contesto GEBAN ricevuti nel payload ai fini di audit.
5. **Given** un utente accede al builder GEMODO, **When** il JWT contiene un ruolo GEMODO
   valido, **Then** GEMODO abilita solo le azioni previste da quel ruolo.
6. **Given** il processo richiede approvatore separato, **When** un gestore tenta di
   pubblicare una versione, **Then** il servizio richiede un ruolo approvativo distinto.
7. **Given** un token ACE valido contiene `contexts.geban.roles` con
   `ROLE_COORDINATOR#geban`, **When** viene richiesta una generazione documento GEBAN,
   **Then** GEMODO deriva il permesso `DOCUMENTI_GENERATORE` tramite mapping configurato
   e autorizza la richiesta solo se audience, client e contesto sono coerenti.
8. **Given** un token ACE valido contiene `contexts.geban.roles` con `ROLE_USER#geban`,
   **When** l'utente tenta di accedere al builder modelli, **Then** GEMODO non abilita
   creazione, modifica, pubblicazione o archiviazione modelli.
9. **Given** un token ACE valido contiene `contexts.geban.roles` con
   `ROLE_MANAGER#geban`, **When** l'utente accede al builder modelli per il perimetro
   GEBAN, **Then** GEMODO puo' derivare il permesso `GEMODO_MODELLI_GESTORE` tramite
   mapping configurato.

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
4. **Given** un'azione ufficiale avviata tramite tool AI/MCP, **When** l'azione richiede
   pubblicazione, archiviazione, generazione ufficiale o download, **Then** valgono gli
   stessi ruoli, conferme e audit delle API ordinarie.

### Edge Cases

- Chiamata tecnica senza utente reale.
- Token valido ma privo di ruolo applicativo.
- Token tecnico `geban-backend` valido ma payload privo di contesto utente coerente.
- Token con ruolo `DOCUMENTI_GENERATORE` ma client chiamante diverso da `geban-backend`.
- Token con ruolo GEBAN di generazione usato per accedere al builder GEMODO.
- Token con ruolo GEMODO builder usato per generare documenti dal flusso GEBAN.
- Token ACE con audience corretta ma senza `contexts.geban.roles`.
- Token ACE con `contexts.geban.roles` valido ma senza audience `gemodo-backend`.
- Token ACE con piu' contesti (`geri`, `geban`, altri): GEMODO considera solo i contesti
  configurati per il sistema richiedente o per il builder.
- Ruolo ACE nuovo o rinominato non presente nella mappa configurata.
- Ruolo ACE GEBAN di generazione usato per gestire modelli senza mapping esplicito.
- Client ACE diverso da quello ammesso che presenta un claim `contexts.geban.roles`.
- Contesto GEBAN non coerente con l'azione richiesta.
- Contesto autorizzativo nel payload coerente con la richiesta ma non supportato da claim
  verificabili nel token.
- Audit fallito durante operazione sensibile.
- Chiamata AI/MCP con ruolo valido ma senza conferma esplicita per azione ufficiale.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Tutte le API protette MUST richiedere identita' verificabile.
- **FR-002**: Il servizio MUST verificare chiamante, audience, scadenza e ruoli o claim contestuali.
- **FR-003**: Il servizio MUST distinguere utenti builder, sistema GEBAN e client tecnici.
- **FR-003a**: Per le operazioni di generazione richieste da GEBAN, il servizio MUST
  ricevere un token Keycloak con audience GEMODO, client chiamante autorizzato e permesso
  applicativo `DOCUMENTI_GENERATORE` (o `DOCUMENTI_VIEWER` per consultazione) ricavabile
  da ruoli client GEMODO o da mapping configurato di ruoli esterni ACE/GEBAN.
- **FR-003b**: Il servizio MUST considerare non valida una chiamata di generazione da
  GEBAN se il token non identifica un client chiamante autorizzato (`geban-backend` di
  test/CI o client ACE reale configurato) e un ruolo/permesso applicativo richiesto; il
  servizio MUST inoltre rifiutare la richiesta se il payload non contiene un contesto
  utente/GEBAN coerente con l'azione richiesta, anche se il token e' valido.
- **FR-003c**: GEMODO MUST NOT gestire utenti, password o assegnazione ufficiale dei ruoli applicativi; tali responsabilita' restano in Keycloak o nel sistema identita' collegato.
- **FR-003d**: GEMODO MUST leggere dal JWT i ruoli applicativi e applicare autorizzazioni lato backend in base al canale: ruoli GEMODO per builder, ruoli/claim GEBAN per generazione e consultazione documenti.
- **FR-004**: Il servizio MUST applicare autorizzazioni lato backend.
- **FR-005**: Il servizio MUST supportare almeno i ruoli `GEMODO_ADMIN`, `GEMODO_MODELLI_GESTORE`, `GEMODO_MODELLI_VIEWER`, `DOCUMENTI_GENERATORE`, `DOCUMENTI_VIEWER` e `SYSTEM_GEBAN`; deve inoltre riservare i ruoli `GEMODO_MODELLI_REVISORE` e `GEMODO_MODELLI_APPROVATORE` per eventuale separazione di revisione e pubblicazione.
- **FR-005a**: `GEMODO_ADMIN` MUST poter eseguire tutte le operazioni interne GEMODO.
- **FR-005b**: `GEMODO_MODELLI_GESTORE` MUST poter creare, modificare, pubblicare e archiviare modelli nel builder, salvo futura introduzione di ruoli approvativi separati.
- **FR-005c**: `DOCUMENTI_GENERATORE` MUST essere usato per richieste di generazione documenti provenienti dal flusso GEBAN; non abilita la gestione del builder GEMODO.
- **FR-005d**: Se i ruoli approvativi separati vengono attivati, pubblicazione e archiviazione MUST essere consentite solo a `GEMODO_ADMIN` o `GEMODO_MODELLI_APPROVATORE`; la richiesta di revisione MUST restare consentita a `GEMODO_ADMIN`, `GEMODO_MODELLI_GESTORE` o `GEMODO_MODELLI_REVISORE` secondo il workflow definito.
- **FR-005e**: Tutti i ruoli applicativi GEMODO MUST essere definiti come ruoli client sul client `gemodo-backend` in Keycloak (`resource_access.gemodo-backend.roles`), MUST NOT essere definiti come ruoli realm, per evitare collisioni di nomi nel realm Keycloak condiviso con altre applicazioni CNR.
- **FR-005f**: Il servizio MUST supportare mapping configurabile da ruoli esterni presenti
  in claim di contesto (`contexts.<app>.roles`) verso permessi applicativi GEMODO, senza
  hardcodare i ruoli esterni nelle singole API.
- **FR-005g**: Per il contesto `geban`, i ruoli esterni `ROLE_GESTORE#geban`,
  `ROLE_MANAGER#geban`, `ROLE_COORDINATOR#geban` e `ROLE_USER#geban` MUST poter derivare
  il permesso `DOCUMENTI_GENERATORE` per la generazione documenti GEBAN quando client,
  audience e contesto sono validi.
- **FR-005h**: Per il builder modelli nel perimetro GEBAN, solo `ROLE_MANAGER#geban` MAY
  derivare il permesso `GEMODO_MODELLI_GESTORE`; gli altri ruoli GEBAN di generazione
  documenti MUST NOT abilitare gestione modelli.
- **FR-005i**: Un token con ruoli esterni ACE/GEBAN MUST contenere audience
  `gemodo-backend`; la presenza di `contexts.geban.roles` senza audience GEMODO non e'
  sufficiente per accedere alle API GEMODO.
- **FR-005j**: La configurazione di client ammessi e mapping ruoli esterni MUST poter
  rappresentare piu' applicativi sorgente, indicando per ciascuno contesto token,
  sistema richiedente, ruoli esterni riconosciuti, permessi GEMODO derivati e perimetro
  funzionale autorizzato.
- **FR-006**: Il servizio MUST auditare creazione, modifica, revisione, pubblicazione e archiviazione modello.
- **FR-007**: Il servizio MUST auditare validazioni fallite, generazioni, download ed errori autorizzativi.
- **FR-008**: Nessun segreto, token o credenziale MUST essere esposto in log, audit o risposte applicative.
- **FR-009**: Il contesto/autorizzazione trasmesso nel payload da GEBAN MUST essere usato solo come contesto applicativo e audit; non puo' sostituire un token valido con ruoli o claim verificabili.
- **FR-010**: Le API accessibili tramite `SYSTEM_GEBAN` MUST essere esplicitamente censite e non possono includere operazioni utente ordinarie salvo decisione documentata.
- **FR-011**: Ogni audit event MUST contenere almeno tipo aggregate, identificativo target, tipo evento, attore o client, esito, timestamp e payload minimo sanificato; per rifiuti autorizzativi deve includere il motivo applicativo del rifiuto senza esporre segreti.
- **FR-012**: Un'operazione sensibile MUST NOT essere considerata completata con successo se l'audit obbligatorio non viene registrato o non e' ricostruibile.
- **FR-013**: I tool AI/MCP che leggono o scrivono dati GEMODO MUST rispettare gli stessi ruoli, contesti e audit delle API ordinarie; pubblicazione, archiviazione, generazione ufficiale e download richiedono conferma esplicita quando invocati tramite AI/MCP.

### Key Entities

- **Identita' Utente**: utente reale propagato o autenticato.
- **Client Chiamante**: sistema applicativo che invoca il servizio.
- **Ruolo Applicativo**: permesso funzionale.
- **Ruolo GEMODO**: ruolo applicativo letto dal JWT e valido per le funzionalita' interne GEMODO.
- **Ruolo/Claim GEBAN**: ruolo o claim contestuale letto dal JWT delegato e valido per generazione, download o consultazione nel flusso GEBAN.
- **Contesto GEBAN**: contesto operativo passato da GEBAN.
- **Contesto Token Esterno**: claim verificabile nel token, ad esempio
  `contexts.geban.roles`, che identifica ruoli del chiamante in un applicativo sorgente.
- **Mapping Ruoli Esterni**: configurazione che trasforma ruoli di un contesto esterno in
  permessi applicativi GEMODO, limitandoli per sistema richiedente, API o tipo documento
  quando necessario.
- **Contesto Autorizzativo Payload**: dati di supporto inviati da GEBAN per audit e
  coerenza applicativa, non sostitutivi del token.
- **API Tecnica Censita**: operazione server-to-server esplicitamente autorizzata per
  client tecnici o batch.
- **Operazione Sensibile**: azione che modifica configurazioni, produce o espone documenti,
  o rifiuta una richiesta per ragioni di sicurezza.
- **Audit Event**: registrazione di operazione rilevante.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Il 100% delle operazioni sensibili produce un audit event.
- **SC-002**: Il 100% delle richieste prive di autorizzazione adeguata viene rifiutato.
- **SC-003**: Il 100% delle generazioni autorizzate conserva attore o client tecnico responsabile.
- **SC-004**: Il 100% degli audit event verificati non contiene JWT completi, refresh token,
  client secret, password o credenziali tecniche.
- **SC-005**: Il 100% delle chiamate tecniche accettate e' riconducibile a una API censita
  per `SYSTEM_GEBAN` o client equivalente.
- **SC-006**: Il 100% dei token ACE accettati per GEBAN contiene audience
  `gemodo-backend`, client chiamante ammesso e almeno un ruolo riconosciuto in
  `contexts.geban.roles` o in `resource_access.gemodo-backend.roles`.
- **SC-007**: Nessun ruolo ACE/GEBAN diverso da `ROLE_MANAGER#geban` abilita operazioni di
  gestione modelli nei test autorizzativi.
- **SC-008**: L'aggiunta di un nuovo applicativo sorgente o di un nuovo ruolo esterno
  richiede solo aggiornamento della configurazione di mapping e della documentazione
  operativa, non cambiamenti di contratto pubblico.

## Assumptions

- Keycloak e JWT sono il modello autenticativo di riferimento.
- Utenti, password e assegnazione ruoli sono gestiti in Keycloak o nel sistema identita'
  collegato; GEMODO consuma i ruoli presenti nel JWT.
- Per la prima release l'approvazione modello coincide con la pubblicazione fatta da
  `GEMODO_MODELLI_GESTORE` (o `GEMODO_ADMIN`); non e' richiesta separazione tra gestore,
  revisore e approvatore (`SEC-006-002`, risolta il 2026-07-29).
- I ruoli `GEMODO_MODELLI_REVISORE` e `GEMODO_MODELLI_APPROVATORE` restano definiti ma
  inattivi; potranno essere attivati in futuro senza cambiare il contratto API se il
  processo CNR richiedera' un'approvazione da parte di altri soggetti oltre al gestore.
- La modalita' token tecnico (client credentials) GEBAN -> GEMODO con contesto utente nel
  payload resta supportata per test/CI (`SEC-006-001`, risolta il 2026-07-29); il token
  delegato/token exchange resta possibile evoluzione futura, non bloccante.
- Il flusso ACE indicato dal team GEBAN estende `SEC-006-001`: il client tecnico di test
  `geban-backend` resta supportato, mentre i token ACE reali possono portare identita' e
  ruoli utente nel claim `contexts.geban.roles`.
- Per i token ACE ricevuti dal team GEBAN, l'issuer resta
  `https://sso.test.si.cnr.it/auth/realms/cnr` e l'audience GEMODO attesa resta
  `gemodo-backend`.
- Il client id ACE effettivo e' case-sensitive e deve essere censito tra i client
  chiamanti ammessi; gli esempi ricevuti mostrano `azp` pari a `geri-angular-public`.
- Eventuali integrazioni future sono incluse solo come requisito di configurabilita' del
  mapping ruoli esterni, non come implementazione di regole specifiche gia' note.

## Deferred Decisions

Nessuna decisione bloccante differita al momento. `SEC-006-001` e `SEC-006-002` sono
risolte; la modalita' ACE/context roles e' ora parte del perimetro della spec. Restano da
confermare durante il planning i nomi esatti dei client ACE da ammettere nei diversi
ambienti e il formato operativo della configurazione di mapping.
