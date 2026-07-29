# Feature Specification: Catalogo Modelli E Contratto Dati GEBAN

**Feature Branch**: `001-catalogo-contratto-geban`

**Created**: 2026-06-19

**Status**: Draft - aggiornata 2026-07-29 con le decisioni propagate da `009-fondamenta-mock-test-qualita`

**Input**: User description: "Partendo da PROPOSTA-servizio-gestione-modelli-bando.md, crea la prima specifica solo per Catalogo modelli e contratto dati verso GEBAN. Includi attori, flusso GEBAN, modelli pubblicati, campi richiesti, validazione payload, errori e acceptance criteria. Escludi builder frontend, generazione PDF dettagliata e sicurezza dettagliata."

## Clarifications

### Session 2026-06-19

- Q: Come deve comportarsi la validazione quando il payload contiene campi non previsti dal contratto dati? -> A: I campi non previsti rendono il payload non valido.
- Q: Cosa succede se una versione modello viene archiviata tra consultazione catalogo e validazione payload? -> A: La validazione fallisce se la versione non e' piu' pubblicata o valida al momento della validazione.
- Q: Come deve funzionare il filtro temporale dei modelli? -> A: Il catalogo distingue modalita' operativa per modelli correnti/validi e modalita' storico per tutti i pubblicati filtrabili per data pubblicazione.
- Q: Possono esistere piu' versioni pubblicate equivalenti per lo stesso contesto? -> A: No, per stessa combinazione tipo documento, categoria, tipologia e variante esiste una sola versione pubblicata corrente; modelli simili coesistono come varianti distinte.
- Q: Come si evita ambiguita' quando esistono piu' modelli pubblicati nello stesso contesto? -> A: Il catalogo restituisce varianti distinte e le chiamate operative successive devono indicare obbligatoriamente il `modello_versione_id` scelto.

### Session 2026-07-29 (propagazione decisioni da `009`)

Questa sessione recepisce le decisioni chiarite o confermate nella spec trasversale
`009-fondamenta-mock-test-qualita` tra il 2026-06-22 e il 2026-07-29 (vedi
`docs/decision-register.yaml` per il registro completo con owner, stato e fase
bloccante di ciascuna). `plan.md`, `research.md`, `data-model.md`, il contratto
OpenAPI, `quickstart.md` e `tasks.md` di questa feature vengono aggiornati di
conseguenza nella stessa sessione.

- Q: Il catalogo deve validare la tipologia di processo (`codice_tipologia`) contro un
  elenco noto? -> A: Si (`DEC-001-TIPOLOGIE-SOL`, confermata). Il perimetro iniziale
  copre le tipologie GEBAN/SOL TDPNRR, CD, DIR, TD, CP, RS, CATP, TI, SDIP e MOB,
  ciascuna con codice SOL associato (vedi `infra/local/postgres/seed-demo-catalog.yaml`
  della `009`). Una tipologia non tra queste e' un errore funzionale, non un filtro
  vuoto silenzioso.
- Q: Il contratto dati deve gestire il flag `Bando Inglese` e i campi in lingua
  inglese? -> A: Si (`DEC-001-LINGUA-IT-EN`, confermata). Il payload di validazione
  include un campo booleano di contesto (`bando_inglese`); i campi del contratto dati
  marcati per la lingua inglese diventano obbligatori solo quando quel flag e' `true`.
  Il servizio non genera qui il documento in due lingue (compito della `004`): valida
  solo che i dati necessari siano presenti quando richiesti.
- Q: I campi comuni GEBAN (codice bando, numero posti, sedi, medaglione, PTA, flag
  inPA/Gazzetta, ecc., FR-029 di `009`) richiedono un meccanismo nuovo nel contratto
  dati? -> A: No. Sono dati di seed/configurazione del contratto dati dinamico gia'
  previsto da questa spec (`ModelloCampoRichiesto`), non un nuovo meccanismo. `Data
  inizio` resta volutamente esclusa dai campi gestiti (`DEC-001-CAMPI-COMUNI-GEBAN`).
- Q: Bando multiplo (padre/figli) e ribando richiedono un nuovo meccanismo di
  validazione? -> A: No, non per questa feature. Restano rappresentati come dati
  strutturati dentro il contratto dati dinamico esistente (`DEC-001-BANDO-MULTIPLO`,
  `DEC-001-RIBANDO`, entrambe confermate); la generazione del documento unico sul
  padre e la gestione di protocollo/numero del ribando sono responsabilita' della
  `004`/`005`.
- Q: Il catalogo deve gia' filtrare i modelli in base a un profilo GEBAN versionato
  (categorie, modelli e placeholder concordati)? -> A: Non ancora. Il profilo GEBAN
  versionato resta una decisione parzialmente aperta (`DEC-001-PROFILO-GEBAN`,
  `DEC-001-CONFIG-PROFILO-GEBAN`, `DEC-001-RELAZIONE-PROFILO-CATALOGO`,
  `DEC-001-API-PROFILO-GEBAN`): questa feature continua a esporre catalogo e campi
  richiesti in base allo stato di pubblicazione; l'autorizzazione fine per sistema
  richiedente/profilo di integrazione (`GEBAN_RECLUTAMENTO_V1`, vedi
  `infra/local/integration-profiles.local.yaml` della `009`) resta responsabilita'
  della `006` e non e' ancora un filtro del catalogo.
- Q: `modello_versione_id` resta un intero o diventa una stringa come negli
  identificativi demo della `009` (es. `demo-bando-concorso-standard-v1`)? -> A:
  Resta intero (int64), coerente con il contratto OpenAPI gia' pubblicato da questa
  feature (`DEC-001-IDENTIFICATIVI-MODELLO`, ancora `ASSUNTA_PROVVISORIA`: la
  conferma definitiva richiede allineamento con GEBAN prima dell'implementazione). Gli
  identificativi stringa nei manifest demo della `009` restano solo etichette
  leggibili nei manifest di qualita', non il formato dell'API.
- Q: La sicurezza delle chiamate operative cambia per questa feature? -> A: No.
  `SEC-006-001` (confermata dalla `006`) conferma che GEBAN chiama con token tecnico
  `geban-backend`; questa feature continua ad assumere che il chiamante sia gia'
  autorizzato (FR-017/Assumptions), senza validare qui token o ruoli.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Consultare modelli pubblicati disponibili (Priority: P1)

Come sistema GEBAN, voglio ottenere l'elenco dei modelli documentali pubblicati e validi
per un contesto di processo, cosi' da mostrare all'utente solo scelte utilizzabili.

**Why this priority**: senza un catalogo filtrato di modelli pubblicati, GEBAN non puo'
iniziare il flusso operativo di scelta del modello.

**Independent Test**: dato un catalogo con modelli in stati diversi, la storia e'
verificabile controllando che GEBAN riceva solo versioni pubblicate, valide e coerenti con
tipo documento, categoria, tipologia e data di riferimento.

**Acceptance Scenarios**:

1. **Given** esistono modelli in bozza, approvati, pubblicati e archiviati, **When** GEBAN
   richiede i modelli disponibili per un contesto valido, **Then** riceve solo versioni
   pubblicate e valide per quel contesto.
2. **Given** per il contesto esiste un solo modello pubblicato valido, **When** GEBAN
   consulta il catalogo, **Then** il risultato contiene un solo modello selezionabile.
3. **Given** nessun modello pubblicato e valido corrisponde al contesto, **When** GEBAN
   consulta il catalogo, **Then** il risultato comunica l'assenza di modelli utilizzabili
   senza esporre modelli non pubblicati.
4. **Given** GEBAN o un client autorizzato richiede la consultazione storica, **When** il
   servizio riceve filtri di pubblicazione, **Then** restituisce versioni archiviate o
   storiche, ordinate o filtrabili per data di pubblicazione.
5. **Given** per lo stesso contesto esistono piu' varianti pubblicate, **When** GEBAN
   consulta il catalogo, **Then** il servizio restituisce le varianti pubblicate correnti
   con i rispettivi identificativi di versione, permettendo a GEBAN o all'utente di
   selezionare quella da usare.

---

### User Story 2 - Ottenere il contratto dati del modello (Priority: P1)

Come sistema GEBAN, voglio ottenere i campi richiesti da una versione modello pubblicata,
cosi' da costruire la maschera dinamica senza duplicare la logica dei modelli.

**Why this priority**: il contratto dati e' la base per raccogliere dati coerenti con il
modello selezionato.

**Independent Test**: dato un modello pubblicato con campi obbligatori e facoltativi, la
storia e' verificabile controllando che GEBAN riceva campo, etichetta, tipo, ordine,
obbligatorieta' e vincoli di validazione.

**Acceptance Scenarios**:

1. **Given** una versione modello pubblicata dichiara campi richiesti, **When** GEBAN
   richiede il contratto dati, **Then** riceve tutti i campi ordinati con metadati e
   vincoli necessari alla compilazione.
2. **Given** una versione modello non e' pubblicata, **When** GEBAN richiede il contratto
   dati, **Then** il servizio ne impedisce l'uso operativo.
3. **Given** un campo e' facoltativo, **When** GEBAN riceve il contratto dati, **Then**
   il campo e' marcato come non obbligatorio ma resta descritto con tipo e vincoli.

---

### User Story 3 - Validare il payload prima della generazione (Priority: P1)

Come sistema GEBAN, voglio validare il payload compilato dall'utente contro il contratto
del modello, cosi' da intercettare errori prima della generazione documentale.

**Why this priority**: la validazione deterministica del payload evita documenti generati
con dati incompleti, incompatibili o non coerenti con il modello.

**Independent Test**: dato un contratto dati noto, la storia e' verificabile inviando
payload validi e non validi e controllando esito, lista errori, campo coinvolto e motivo
dell'errore.

**Acceptance Scenarios**:

1. **Given** il payload contiene tutti i campi obbligatori con valori coerenti, **When**
   GEBAN richiede la validazione, **Then** il servizio restituisce esito valido e nessun
   errore.
2. **Given** il payload omette un campo obbligatorio, **When** GEBAN richiede la
   validazione, **Then** il servizio restituisce esito non valido con errore riferito al
   campo mancante.
3. **Given** il payload contiene un valore con tipo non coerente, **When** GEBAN richiede
   la validazione, **Then** il servizio restituisce esito non valido con errore riferito al
   campo e al tipo atteso.
4. **Given** il payload contiene campi non previsti dal contratto, **When** GEBAN richiede
   la validazione, **Then** il servizio restituisce esito non valido e segnala i campi non
   ammessi.

---

### User Story 4 - Gestire errori funzionali comprensibili (Priority: P2)

Come sistema GEBAN, voglio ricevere errori funzionali strutturati e comprensibili, cosi'
da mostrare messaggi utili all'utente e decidere se correggere dati, cambiare modello o
interrompere il flusso.

**Why this priority**: gli errori sono necessari per rendere usabile il flusso, ma il
catalogo, il contratto dati e la validazione positiva sono il nucleo MVP.

**Independent Test**: la storia e' verificabile simulando contesti non validi, modelli
non pubblicati, payload errati e richieste incoerenti.

**Acceptance Scenarios**:

1. **Given** GEBAN richiede un modello inesistente, **When** il servizio risponde, **Then**
   l'errore indica che il modello non e' disponibile per l'uso operativo.
2. **Given** GEBAN richiede una validazione per una versione modello non pubblicata,
   **When** il servizio risponde, **Then** l'errore impedisce la validazione operativa.
3. **Given** la richiesta non contiene il contesto minimo necessario, **When** il servizio
   risponde, **Then** l'errore indica quali informazioni sono mancanti o non coerenti.

### Edge Cases

- Il contesto GEBAN contiene tipo documento valido ma categoria non attiva.
- Il contesto GEBAN contiene categoria valida ma nessun modello pubblicato alla data di
  riferimento.
- Il catalogo viene richiesto in modalita' storico per vedere versioni archiviate o non
  operative.
- Due versioni pubblicate della stessa variante risultano correnti nello stesso momento:
  il servizio deve trattare la situazione come anomalia di catalogo.
- Piu' modelli simili sono pubblicati per lo stesso contesto ma con varianti diverse: il
  servizio li restituisce come opzioni distinte.
- Il contratto dati include campi array o object che richiedono una struttura interna
  definita.
- Il payload contiene valori vuoti per campi obbligatori.
- Il payload contiene campi facoltativi non valorizzati.
- La versione modello viene archiviata dopo essere stata proposta a GEBAN ma prima della
  validazione del payload: la validazione deve fallire e richiedere a GEBAN di ricaricare
  il catalogo.
- `codice_tipologia` non corrisponde a nessuna tipologia GEBAN/SOL configurata.
- Il payload ha `bando_inglese: true` ma uno o piu' campi obbligatori in lingua
  inglese sono assenti o vuoti.
- Il payload ha `bando_inglese: false` (o assente) e valorizza comunque campi in
  lingua inglese: restano ammessi come facoltativi, non generano errore da soli.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Il servizio MUST esporre a GEBAN i tipi documento disponibili per l'uso
  operativo.
- **FR-002**: Il servizio MUST esporre a GEBAN le categorie disponibili per un tipo
  documento attivo.
- **FR-003**: Il servizio MUST restituire a GEBAN solo versioni modello in stato
  `PUBBLICATO` e valide per il contesto richiesto quando il catalogo e' usato in modalita'
  operativa.
- **FR-004**: Il servizio MUST filtrare i modelli disponibili per tipo documento,
  categoria, eventuale tipologia di processo e data di riferimento quando presente.
- **FR-005**: Il servizio MUST impedire l'uso operativo di versioni modello in stato
  diverso da `PUBBLICATO`.
- **FR-006**: Il servizio MUST restituire per ogni modello disponibile almeno
  identificativo modello, identificativo versione, codice, descrizione, variante, numero
  versione e periodo di validita'.
- **FR-006c**: Il servizio MUST consentire a GEBAN di selezionare una specifica versione
  pubblicata tramite `modello_versione_id`.
- **FR-006d**: Le chiamate operative successive alla consultazione catalogo MUST indicare
  obbligatoriamente il `modello_versione_id` scelto; il servizio MUST NOT applicare un
  fallback automatico all'ultima versione pubblicata.
- **FR-006e**: Per la stessa combinazione di tipo documento, categoria, tipologia e
  variante, il catalogo operativo MUST esporre al massimo una versione pubblicata
  corrente.
- **FR-006a**: Il servizio MUST supportare una modalita' di consultazione storica che
  restituisce versioni archiviate, filtrabili per data di pubblicazione e ordinabili
  cronologicamente.
- **FR-006b**: Le date di validita' della versione modello MUST essere opzionali; una
  versione pubblicata senza data fine resta valida finche' non viene archiviata, sospesa o
  sostituita secondo le regole del modello.
- **FR-007**: Il servizio MUST restituire a GEBAN il contratto dati associato a una
  versione modello pubblicata.
- **FR-008**: Il contratto dati MUST includere per ogni campo almeno codice, etichetta,
  tipo dato, obbligatorieta', ordine e vincoli di validazione disponibili.
- **FR-009**: Il contratto dati MUST distinguere campi obbligatori e campi facoltativi.
- **FR-010**: Il contratto dati MUST consentire a GEBAN di costruire una maschera di
  compilazione senza replicare la logica dei modelli.
- **FR-011**: Il servizio MUST validare il payload ricevuto da GEBAN contro il contratto
  dati della versione modello selezionata.
- **FR-012**: La validazione MUST verificare presenza dei campi obbligatori, tipi dato,
  vincoli dichiarati, assenza di campi non previsti e coerenza con la versione modello
  pubblicata.
- **FR-012a**: La validazione MUST verificare lo stato corrente della versione modello
  selezionata e fallire se la versione non e' piu' `PUBBLICATO`.
- **FR-013**: La validazione MUST restituire un esito positivo quando il payload rispetta
  il contratto dati.
- **FR-014**: La validazione MUST restituire un esito negativo con errori strutturati
  quando il payload non rispetta il contratto dati.
- **FR-015**: Ogni errore di validazione MUST indicare almeno il campo coinvolto, un codice
  errore e un messaggio funzionale.
- **FR-016**: Il servizio MUST comunicare in modo distinto assenza di modelli, modello non
  utilizzabile, contratto dati non disponibile e payload non valido.
- **FR-017**: Il servizio MUST mantenere il confine di responsabilita': GEBAN raccoglie i
  dati del processo, mentre il servizio modelli definisce contratto dati e validazione.
- **FR-018**: Il servizio MUST NOT richiedere letture dirette dal database GEBAN per
  completare catalogo, contratto dati o validazione payload.
- **FR-019**: La specifica di questa feature MUST NOT includere builder frontend,
  generazione PDF dettagliata, firma, protocollo o pubblicazione.
- **FR-020**: Quando la richiesta di catalogo o validazione indica `codice_tipologia`,
  il servizio MUST verificare che corrisponda a una tipologia GEBAN/SOL configurata
  (perimetro iniziale: TDPNRR, CD, DIR, TD, CP, RS, CATP, TI, SDIP, MOB) e MUST
  restituire un errore funzionale distinto quando non corrisponde, invece di un
  risultato vuoto silenzioso.
- **FR-021**: Il contratto dati di un campo MUST poter dichiarare una lingua (`IT` o
  `EN`); un campo in lingua `EN` MUST essere obbligatorio solo quando il payload
  contiene un flag di contesto `bando_inglese` con valore `true`, e facoltativo
  altrimenti.
- **FR-022**: La validazione payload MUST verificare la presenza dei campi obbligatori
  in lingua inglese quando `bando_inglese` e' `true`, e MUST restituire un errore
  funzionale distinto per ciascun campo inglese mancante.
- **FR-023**: Il servizio MUST continuare a esporre catalogo e contratto dati in base
  allo stato di pubblicazione della versione modello; l'autorizzazione fine per
  sistema richiedente e profilo di integrazione (es. profilo GEBAN versionato) resta
  fuori scope di questa feature e appartiene alla `006` finche' `DEC-001-PROFILO-GEBAN`
  non viene chiusa.

### Key Entities *(include if feature involves data)*

- **Tipo Documento**: famiglia documentale generale disponibile nel catalogo, ad esempio
  bando di concorso, graduatoria, decreto, comunicazione o verbale.
- **Categoria Documento**: classificazione interna collegata a un tipo documento, usata
  per filtrare i modelli disponibili.
- **Modello Documento**: contenitore logico di un modello selezionabile da GEBAN quando
  esiste almeno una versione pubblicata valida.
- **Variante Modello**: etichetta funzionale obbligatoria che distingue modelli simili per
  stesso tipo, categoria e tipologia; `STANDARD` rappresenta la variante predefinita.
- **Versione Modello**: versione specifica del modello, con stato, numero versione,
  periodo di validita' opzionale e identificativo usato da GEBAN per contratto dati,
  validazione e generazione.
- **Campo Richiesto**: elemento del contratto dati, con codice, etichetta, tipo,
  obbligatorieta', ordine e vincoli.
- **Contratto Dati**: insieme dei campi e delle regole che GEBAN usa per costruire la
  maschera e preparare il payload.
- **Payload Di Validazione**: dati inviati da GEBAN per verificare la conformita' al
  contratto della versione modello selezionata.
- **Errore Di Validazione**: errore funzionale associato a un campo o alla richiesta,
  composto da codice e messaggio comprensibile.
- **Tipologia Bando SOL**: tipologia di processo condivisa con GEBAN (`codice_tipologia`),
  con codice SOL associato per l'integrazione GEBAN-SOL; perimetro iniziale TDPNRR, CD,
  DIR, TD, CP, RS, CATP, TI, SDIP, MOB.

## Decisioni Aperte Collegate

Le decisioni che riguardano questa feature vivono nel registro centrale
`docs/decision-register.yaml` (owner `009`), non duplicate qui, per evitare che le due
copie divergano nel tempo. Voci con `owner_spec: specs/001-catalogo-contratto-geban` o
`specs/001-catalogo-contratto-geban` in `spec_interessate`:

`DEC-001-TIPOLOGIE-SOL` (confermata), `DEC-001-CATEGORIE-INIZIALI`,
`DEC-006-CONFINE-KEYCLOAK-GEMODO`, `DEC-001-PROFILO-GEBAN`,
`DEC-001-CONFIG-PROFILO-GEBAN`, `DEC-001-IDENTIFICATIVI-MODELLO`,
`DEC-001-RELAZIONE-PROFILO-CATALOGO`, `DEC-001-API-PROFILO-GEBAN`,
`DEC-006-AUTORIZZAZIONI-PROFILO-GEBAN`, `DEC-001-VERSIONAMENTO-MAPPING-CAMPI`,
`DEC-003-FORMATO-CAMPI-COMPLESSI`, `DEC-001-LINGUA-IT-EN` (confermata),
`DEC-001-CAMPI-COMUNI-GEBAN`, `DEC-001-BANDO-MULTIPLO` (confermata),
`DEC-001-RIBANDO` (confermata).

Prima di generare nuovi task implementativi su una parte impattata da una decisione
non confermata, verificare `backend/app/quality/readiness_gate.py` (vedi
`docs/decision-workflow.md`).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Nel 100% delle consultazioni catalogo, GEBAN riceve solo versioni modello
  pubblicate e valide per il contesto richiesto.
- **SC-002**: Nel 100% dei contratti dati restituiti, ogni campo contiene codice,
  etichetta, tipo, obbligatorieta' e ordine.
- **SC-003**: Nel 100% dei payload non validi, la risposta di validazione contiene almeno
  un errore con campo o ambito richiesta, codice errore e messaggio funzionale.
- **SC-004**: Un operatore GEBAN puo' arrivare dalla scelta del tipo documento alla lista
  dei campi da compilare senza consultare documentazione tecnica esterna.
- **SC-005**: Nessun modello in stato diverso da `PUBBLICATO` viene presentato come
  utilizzabile a GEBAN.
- **SC-006**: Tutti gli scenari primari della feature sono verificabili senza generare un
  PDF ufficiale.
- **SC-007**: La consultazione storica consente di recuperare versioni archiviate senza
  renderle utilizzabili per generazioni operative.
- **SC-008**: Quando esistono piu' varianti pubblicate per lo stesso contesto, GEBAN puo'
  identificare e usare esplicitamente la variante scelta tramite `modello_versione_id`.

## Assumptions

- Il documento sorgente `PROPOSTA-servizio-gestione-modelli-bando.md` e' la fonte iniziale
  per questa specifica.
- GEBAN e' il sistema che raccoglie i dati di processo e presenta all'utente la maschera
  dinamica.
- Il servizio modelli e' la fonte del catalogo, del contratto dati e delle regole di
  validazione del payload.
- La sicurezza dettagliata viene trattata in una feature separata; questa specifica assume
  che il chiamante sia gia' autorizzato secondo le regole di progetto.
- La generazione PDF dettagliata viene trattata in una feature separata; questa specifica
  si ferma alla validazione del payload e alla preparazione del flusso verso la generazione.
- Il builder frontend e le API amministrative di creazione modello sono fuori scope per
  questa feature.
- La data di riferimento non obbliga ogni modello ad avere una scadenza: serve a
  selezionare la versione corrente quando sono definite finestre temporali.
- `modello_versione_id` resta un identificativo intero (int64); il formato
  definitivo e' tracciato come decisione aperta (`DEC-001-IDENTIFICATIVI-MODELLO`),
  non bloccante per questo incremento.
- Il profilo GEBAN versionato e l'autorizzazione fine per sistema richiedente
  restano fuori scope: il catalogo filtra solo per stato di pubblicazione, non ancora
  per profilo di integrazione (`DEC-001-PROFILO-GEBAN`).
- I campi comuni GEBAN, la gestione di bando multiplo e ribando sono dati del
  contratto dati dinamico esistente, non richiedono nuove entita' di dominio in
  questa feature.
