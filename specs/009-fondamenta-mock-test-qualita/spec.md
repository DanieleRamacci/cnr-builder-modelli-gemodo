# Feature Specification: Fondamenta Mock Test E Qualita

**Feature Branch**: `009-fondamenta-mock-test-qualita`

**Created**: 2026-06-19

**Status**: Draft

**Input**: Estratta da `PROPOSTA-servizio-gestione-modelli-bando.md` sezioni §16.1, §16.2, §16.7 e §17; integrata con `Processo bandi di concorso V 2 - 060726 (dettaglio sviluppo).docx`.

## Clarifications

### Session 2026-06-22

- Q: Stiamo creando la spec da zero? -> A: No. La spec esiste gia' come draft di copertura; questa sessione la integra come spec trasversale per mock, test, dati demo, qualita' e decisioni aperte.
- Q: Questa spec decide lo stack tecnico definitivo? -> A: No. Lo stack proposto resta input di pianificazione; questa spec richiede che l'ambiente e i controlli siano ripetibili e coerenti con le spec, senza bloccare qui scelte implementative.
- Q: I mock sostituiscono il collaudo con GEBAN reale? -> A: No. I mock servono a sviluppo e verifica ripetibile dei contratti; l'allineamento con GEBAN reale resta una verifica successiva di integrazione.
- Q: Come trattare le decisioni aperte di §17? -> A: Ogni decisione deve avere owner, impatto, assunzione provvisoria e fase entro cui va chiusa; non puo' diventare una scelta implicita nei piani.

### Session 2026-07-07

- Q: Il contratto campi GEBAN-GEMODO resta dinamico o serve anche un profilo fisso/versionato di integrazione GEBAN con mappatura campi gia' concordata? -> A: Serve una gestione ibrida: GEMODO deve poter definire un profilo GEBAN versionato, riservato alle chiamate GEBAN, in cui categorie, sottocategorie e placeholder/campi ammessi per ogni modello sono gia' concordati; le API continuano comunque a esporre catalogo e campi richiesti a GEBAN.
- Q: Il flag italiano/inglese indica lingua finale, documento bilingue, obbligatorieta' dei campi inglesi o sezioni/placeholder? -> A: Decisione ancora aperta; vanno chiesti dettagli sul fatto che servano due documenti separati, documenti con visto anche in inglese e traduzione completa, oppure documenti misti con testo italiano e inglese nello stesso output.
- Q: I punti emersi dal flusso GEBAN-GEMODO devono essere considerati gia' definiti o domande aperte? -> A: Sono punti da definire e da trasformare in risposte esplicite prima di pianificare o implementare profilo GEBAN, autorizzazioni, mapping campi, lingua, bandi multipli/ribando e stampa/pubblicazione esterna.

### Session 2026-07-28

- Q: Nel bando multiplo il documento viene prodotto per il padre o anche per ogni figlio? -> A: Si produce un documento/PDF unico da firmare, riferito al bando padre, che contiene nell'articolo dei requisiti tutti i requisiti e i dati dei bandi figli; tra padre e figli cambiano solo sedi, requisiti e numero di posti.
- Q: Nel ribando si riusa il bando precedente o si genera un nuovo documento? -> A: Il ribando riparte come nuovo bando: genera un nuovo documento con numero protocollo e numero bando diversi, include nei visti il riferimento al bando vecchio e la motivazione del ribando, non invia a SOL lo stesso bando con un nuovo codice.
- Q: Nel ribando possono cambiare contenuti e va mantenuta tracciabilita'? -> A: Generalmente dati, date, requisiti, posti, allegati e motivazioni non cambiano, ma il processo riparte come nuovo bando; deve restare storico/tracciabilita' tra bando originario e ribando anche nella procedura informatizzata.
- Q: Come viene gestito oggi il bando in inglese? -> A: Attualmente viene prodotto un estratto sintetico del bando piu' le linee di attivita' per i direttori; questa prassi storica viene superata dalla direzione chiarita nella risposta successiva, che richiede il modello integrale tradotto.
- Q: Quale direzione va presa per il bando in inglese nel nuovo flusso GEBAN-GEMODO? -> A: Va previsto il modello integrale tradotto. GEBAN invia l'informazione `Bando Inglese` Si/No e, quando serve, anche i campi in inglese indicati a video dall'utente; GEMODO usa la stessa tipologia modello e restituisce due output/modelli, italiano e inglese.
- Q: Quali tipologie iniziali GEBAN deve gestire tra quelle SOL? -> A: Le tipologie evidenziate nel documento GEBAN sono TDPNRR, CD, DIR, TD, CP, RS, CATP, TI, SDIP e MOB, ciascuna associata al codice SOL atteso per l'integrazione GEBAN-SOL.
- Q: Qual e' il flusso contrattuale GEBAN-GEMODO per scegliere e generare il modello? -> A: GEBAN condivide con GEMODO il dominio tipologie; dopo scelta di tipologia e data inserimento e dopo valorizzazione dei campi obbligatori, chiama GEMODO per ottenere i modelli validi alla data, conserva la versione scelta e richiede il PDF inviando versione modello e dati obbligatori.
- Q: Quale linea Keycloak proponiamo per utenti GEMODO e chiamate GEBAN? -> A: Per utenti GEMODO si propone login SSO Keycloak con client/ruoli GEMODO. Per GEBAN si propone chiamata backend-to-backend: GEBAN autorizza l'utente sul bando, poi `geban-backend` chiama `gemodo-backend` con token tecnico; utente reale e contesto bando passano nel payload per audit, tracciabilita' e idempotenza. La configurazione esatta dei client resta da confermare con il team Keycloak/GEBAN.
- Q: Keycloak deve decidere direttamente quali tipologie, categorie o modelli un utente o sistema puo' usare? -> A: No. Keycloak resta sorgente di identita', autenticazione, client tecnici e ruoli/claim generali; GEMODO mantiene l'autorizzazione applicativa fine tramite sistemi richiedenti e profili di integrazione versionati, associando client, stato, tipi documento, categorie, tipologie, modelli/versioni, contratti dati e permessi operativi.
- Q: Come si separano operatori umani GEMODO e applicazioni chiamanti come GEBAN, GRADUATORIE o CHECKIN? -> A: Gli operatori umani entrano in GEMODO con token SSO e ruoli/claim che abilitano admin, builder o consultazione per uno o piu' profili applicativi; le applicazioni chiamanti usano client tecnici autorizzati e sono registrate in GEMODO come sistemi richiedenti con profili di integrazione. GEMODO non gestisce password o credenziali, ma governa quali profili, modelli e operazioni sono disponibili.
- Q: Come deve essere salvata la struttura visuale del documento senza builder nella prima fase e con builder in futuro? -> A: Il modello deve usare una sorgente documentale strutturata e versionata, composta da pagina, margini, regioni, blocchi ammessi, posizionamenti controllati, stili consentiti, asset, tabelle, firme e placeholder. L'utente del builder futuro non scrive HTML o CSS libero: lavora in un editor visuale limitato tipo word processor controllato; GEMODO salva e valida la struttura, poi il renderer produce internamente il formato necessario al PDF.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Preparare fondamenta tecniche (Priority: P1)

Come team di sviluppo, voglio un ambiente coerente per backend, frontend, database,
documentale mock e identita', cosi' da implementare e validare le feature in modo
ripetibile.

**Why this priority**: senza fondamenta non si possono eseguire plan/tasks delle feature.

**Independent Test**: un nuovo sviluppatore puo' avviare l'ambiente locale seguendo una
guida e ottenere servizi minimi pronti.

**Acceptance Scenarios**:

1. **Given** un ambiente locale pulito, **When** vengono eseguiti i comandi documentati,
   **Then** i servizi minimi risultano disponibili.
2. **Given** uno schema dati iniziale, **When** vengono applicate le migrations, **Then**
   le entita' principali sono create.
3. **Given** dati demo caricati, **When** il team avvia i controlli minimi, **Then** trova
   tipi, categorie, modelli demo, ruoli e stati coerenti con le spec.
4. **Given** un servizio minimo non disponibile, **When** viene eseguita la verifica
   ambiente, **Then** il problema e' segnalato come prerequisito non soddisfatto.

---

### User Story 2 - Usare mock GEBAN e scenari end-to-end (Priority: P1)

Come team di progetto, voglio mock e scenari di test per GEBAN, cosi' da validare catalogo,
campi, validazione, generazione e download senza dipendere dal sistema reale.

**Why this priority**: i mock riducono dipendenze esterne durante sviluppo e collaudo.

**Independent Test**: il mock puo' interrogare catalogo, ottenere campi e inviare payload
di validazione/generazione.

**Acceptance Scenarios**:

1. **Given** il servizio locale avviato, **When** il mock GEBAN consulta il catalogo,
   **Then** riceve modelli pubblicati demo.
2. **Given** un payload demo valido, **When** il mock GEBAN lo invia, **Then** il flusso
   arriva almeno alla validazione corretta.
3. **Given** un payload demo non valido, **When** il mock GEBAN lo invia, **Then** il flusso
   restituisce errori funzionali coerenti con il contratto dati.
4. **Given** una richiesta ripetuta dal mock GEBAN, **When** usa la stessa chiave e gli
   stessi dati, **Then** il comportamento idempotente e' verificabile nello scenario.
5. **Given** una generazione demo completata, **When** il mock o un utente autorizzato
   consulta stato e download, **Then** il flusso distingue stato, riferimento e
   autorizzazione.

---

### User Story 3 - Governare decisioni aperte (Priority: P2)

Come team di progetto, voglio tracciare decisioni ancora da confermare, cosi' da non
bloccare la copertura ma impedire scelte implicite.

**Why this priority**: molte decisioni della proposta hanno impatto su planning e tasks.

**Independent Test**: ogni decisione aperta ha owner di spec e stato.

**Acceptance Scenarios**:

1. **Given** una decisione da confermare, **When** viene registrata, **Then** ha spec owner
   e impatto previsto.
2. **Given** una decisione confermata, **When** viene aggiornata, **Then** la spec collegata
   riflette la scelta.
3. **Given** una decisione ancora aperta, **When** viene generato un piano tecnico, **Then**
   il piano esplicita l'assunzione provvisoria oppure rinvia le attivita' bloccate.
4. **Given** una decisione critica non chiusa, **When** si tenta di avviare implementazione
   della parte impattata, **Then** il rischio e il blocco residuo sono tracciati.

### Edge Cases

- Ambiente locale avviato solo parzialmente.
- Seed incoerente con le spec.
- Seed demo che contiene dati reali o sensibili.
- Mock non allineato ai contratti.
- Mock GEBAN che accetta payload non validi rispetto allo schema pubblicato.
- Profilo GEBAN versionato non allineato al contratto dati pubblicato o ai placeholder disponibili nel modello.
- Chiamata non GEBAN che tenta di usare modelli o profili riservati al profilo GEBAN.
- Scenario end-to-end che passa senza verificare stato, riferimento documento o audit.
- Decisione aperta usata implicitamente nel piano.
- Decisione aperta chiusa in una spec ma non propagata alle spec dipendenti.
- Assunzione provvisoria superata da una risposta del team GEBAN/Keycloak.
- Test end-to-end che dipende da servizi esterni non disponibili.
- Fallimento autorizzativo non coperto dagli scenari di qualita'.
- Rigenerazione/idempotenza verificata solo nel caso positivo.
- Documentazione di setup non aggiornata dopo variazioni di ambiente.
- Bando multiplo testato come documenti separati per figlio invece che come PDF unico del padre con dati dei figli.
- Ribando trattato come ripubblicazione dello stesso documento invece che come nuovo bando collegato al precedente.
- Bando inglese trattato come estratto ridotto invece che come secondo output integrale tradotto quando `Bando Inglese` e' Si.
- Payload di generazione privo dei campi inglesi obbligatori quando viene richiesto il bando inglese.
- Tipologia bando GEBAN non mappata al codice SOL condiviso.
- Mock GEBAN che seleziona un modello senza conservare e reinviare la versione modello scelta.
- Chiamata GEBAN-GEMODO implementata assumendo token utente o token exchange obbligatorio prima della conferma Keycloak.
- Dati utente e contesto bando messi nel token tecnico invece che nel payload applicativo.
- Token Keycloak valido ma privo di ruolo o claim coerente con il profilo applicativo richiesto in GEMODO.
- Utente con ruolo builder generico che modifica modelli riservati a GEBAN senza autorizzazione fine sul profilo di integrazione.
- Client tecnico autorizzato in Keycloak che tenta di usare un modello, categoria o tipo output non abilitato dal profilo applicativo GEMODO.
- Builder visuale che permette HTML, CSS o script liberi invece di blocchi documentali ammessi.
- Template demo che posiziona logo, intestazione, firme, tabelle o colonne senza struttura controllata e validabile.
- Asset grafico usato nel modello senza riferimento versionato, hash o autorizzazione.
- Firma o blocco posizionato in modo non supportato dal formato controllato.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Il progetto MUST definire setup minimo per backend, frontend, database, documentale mock e identita' locale.
- **FR-002**: Il progetto MUST definire schema dati iniziale coerente con le spec.
- **FR-003**: Il progetto MUST includere dati demo per tipi documento, categorie e modelli.
- **FR-004**: Il progetto MUST includere mock GEBAN per catalogo, campi, validazione e generazione.
- **FR-005**: Il progetto MUST includere scenari end-to-end dal catalogo al download.
- **FR-006**: Il progetto MUST tracciare decisioni aperte con spec owner.
- **FR-007**: Il progetto MUST impedire che decisioni aperte critiche diventino assunzioni silenziose nel piano.
- **FR-008**: Il setup minimo MUST includere una verifica di disponibilita' dei servizi necessari e deve distinguere prerequisiti mancanti da errori applicativi.
- **FR-009**: Le migrations e lo schema iniziale MUST coprire le entita' necessarie a tipi, categorie, modelli, versioni, campi, sezioni, generazioni documento e audit, secondo le spec owner.
- **FR-010**: I seed demo MUST essere marcati come demo, ripetibili e privi di dati reali o sensibili.
- **FR-011**: I dati demo MUST includere almeno un modello pubblicato utilizzabile dal mock GEBAN e almeno un caso non pubblicabile o non valido per verificare errori funzionali.
- **FR-012**: Il mock GEBAN MUST usare gli stessi contratti pubblici previsti per catalogo, campi/schema, validazione, generazione, stato e download.
- **FR-013**: Gli scenari end-to-end MUST coprire almeno flusso valido, payload non valido, retry idempotente, conflitto idempotente, generazione fallita e accesso non autorizzato.
- **FR-014**: Gli scenari di qualita' MUST verificare che eventi sensibili siano auditabili secondo la spec sicurezza.
- **FR-015**: Ogni contratto esposto a GEBAN o al mock MUST avere esempi funzionali coerenti con dati demo e casi di errore.
- **FR-016**: Il progetto MUST mantenere una matrice di copertura che collega scenari di test, user story, requisiti e spec owner.
- **FR-017**: Le decisioni aperte MUST riportare stato, owner, impatto, assunzione provvisoria, spec interessate e fase entro cui vanno chiuse.
- **FR-018**: Le decisioni critiche per implementazione o integrazione MUST essere chiuse o esplicitamente sospese prima di generare task implementativi sulla parte impattata.
- **FR-019**: La documentazione di setup MUST permettere a un nuovo componente del team di avviare ambiente, caricare dati demo ed eseguire gli scenari minimi senza conoscenza implicita.
- **FR-020**: La qualita' minima MUST includere controlli su coerenza contratti, validazioni dati, generazione documento, idempotenza, autorizzazioni, audit e consultazione/download.
- **FR-021**: Il progetto MUST tracciare come decisione aperta la configurazione di un profilo GEBAN versionato, con categorie, sottocategorie, modelli richiamabili, placeholder/campi concordati e autorizzazioni associate.
- **FR-022**: Gli scenari di qualita' per il bando inglese MUST assumere una traduzione integrale: GEBAN invia `Bando Inglese` Si/No e i campi inglesi richiesti quando il flag e' Si; GEMODO usa la stessa tipologia modello e restituisce due output/modelli, italiano e inglese.
- **FR-023**: Il progetto MUST mantenere come punti da chiarire, con owner e fase bloccante, le decisioni emerse sul flusso GEBAN-GEMODO prima che diventino requisiti implementativi.
- **FR-024**: Gli scenari di qualita' per bando multiplo MUST assumere un PDF unico da firmare, prodotto sul bando padre, che include nell'articolo dei requisiti i requisiti e i dati dei bandi figli; sedi, requisiti e numero di posti possono differire tra figli.
- **FR-025**: Gli scenari di qualita' per ribando MUST assumere un nuovo bando con nuovo documento, numero protocollo e numero bando distinti, riferimenti nei visti al bando originario e motivazione del ribando, senza riuso dello stesso documento SOL con nuovo codice.
- **FR-026**: Gli scenari di qualita' MUST verificare la tracciabilita' tra bando originario e ribando, inclusi rimandi e collegamenti disponibili nella procedura informatizzata.
- **FR-027**: I seed demo e i contratti di qualita' MUST includere le tipologie GEBAN iniziali evidenziate nel documento condiviso, con codice SOL associato: TDPNRR, CD, DIR, TD, CP, RS, CATP, TI, SDIP e MOB.
- **FR-028**: Il mock GEBAN MUST esercitare il flusso catalogo in cui GEBAN sceglie tipologia e data inserimento, riceve i modelli validi alla data, conserva la versione modello scelta e reinvia tale versione con i dati obbligatori per la generazione.
- **FR-029**: I contratti demo MUST includere almeno i campi comuni GEBAN previsti dal documento condiviso: codice bando, numero posti, bando multiplo e riferimento, titolo e descrizione ridotta IT/EN, sede prescelta, struttura di riferimento IT/EN, sede di lavoro IT/EN, profilo/livello, tipo selezione, medaglione IT/EN, ribando e riferimento, PTA, flag inPA/Gazzetta e progetto di riferimento dove applicabile.
- **FR-030**: I contratti demo MUST escludere `Data inizio` dal payload obbligatorio, perche' il documento GEBAN indica che non va gestita.
- **FR-031**: Le fondamenta sicurezza MUST restare configurabili finche' Keycloak non conferma client, audience e ruoli; in locale/test devono supportare un principal mock senza hardcodare token exchange o nomi client definitivi.
- **FR-032**: Gli scenari GEBAN-GEMODO MUST assumere come baseline proposta token tecnico `geban-backend` verso `gemodo-backend`, con utente reale e contesto bando nel payload applicativo per audit, tracciabilita' e idempotenza.
- **FR-033**: Il progetto MUST distinguere utenti umani, client tecnici e sistemi richiedenti; GEMODO non deve gestire password o credenziali, ma deve modellare profili applicativi che autorizzano sistemi e utenti su tipi documento, categorie, tipologie, modelli/versioni, contratti dati e operazioni.
- **FR-034**: Gli scenari di qualita' MUST verificare che Keycloak fornisca identita', client, audience e ruoli/claim generali, mentre GEMODO applica l'autorizzazione fine sui propri profili di integrazione e sugli oggetti documentali configurati.
- **FR-035**: Gli scenari admin/builder MUST assumere che un operatore possa vedere o modificare solo i profili e i modelli per cui il token abilita l'accesso e per cui GEMODO ha una regola applicativa coerente; un admin applicativo autorizzato puo' governare sistemi richiedenti, profili, stati e abilitazioni senza gestire credenziali.
- **FR-036**: I seed demo e i contratti di qualita' MUST rappresentare la struttura visuale del documento come modello documentale controllato e versionato, non come HTML/CSS libero inserito dall'utente.
- **FR-037**: Il modello documentale controllato MUST supportare almeno pagina e margini, intestazione, logo/asset, titolo, paragrafi, tabelle semplici, colonne controllate, firme posizionabili, footer, interruzioni pagina, stili ammessi e placeholder selezionabili.
- **FR-038**: Gli scenari di qualita' MUST verificare che il builder futuro sia assunto come editor visuale limitato che manipola la struttura controllata del modello e che il renderer PDF possa usare un formato tecnico generato internamente senza esporre HTML libero all'utente.

### Key Entities

- **Ambiente Locale**: insieme dei servizi minimi per sviluppo.
- **Migration**: evoluzione versionata dello schema dati.
- **Seed Demo**: dati iniziali per test e mock.
- **Mock GEBAN**: simulatore del sistema chiamante.
- **Decisione Aperta**: scelta progettuale da confermare.
- **Verifica Ambiente**: controllo che indica se i servizi minimi sono pronti.
- **Scenario End-to-End**: flusso verificabile che attraversa piu' spec senza dipendere da GEBAN reale.
- **Matrice Di Copertura**: collegamento tra requisiti, scenari, contratti e spec owner.
- **Assunzione Provvisoria**: scelta documentata usata temporaneamente fino a conferma.
- **Contratto Demo**: esempio di richiesta, risposta o errore allineato ai dati demo.
- **Blocco Critico**: decisione o prerequisito che impedisce planning o implementazione sicura di una parte.
- **Profilo Integrazione GEBAN**: configurazione versionata che associa GEBAN a categorie, sottocategorie, modelli richiamabili, placeholder/campi concordati e regole di autorizzazione per le chiamate operative.
- **Sistema Richiedente**: applicazione esterna o modulo autorizzato a consumare contratti e generazione documenti GEMODO, ad esempio GEBAN, GRADUATORIE o CHECKIN.
- **Client Applicativo**: identita' tecnica riconosciuta da Keycloak e associata in GEMODO a uno o piu' sistemi richiedenti e profili di integrazione.
- **Profilo Di Integrazione**: configurazione applicativa versionata, non credenziale, che collega sistema richiedente, client, stato, tipi documento, categorie, tipologie, modelli/versioni, contratti dati e permessi operativi.
- **Bando Multiplo**: bando con padre e figli rappresentato, per la generazione, da un unico PDF del padre che contiene i dati rilevanti dei figli.
- **Ribando**: nuovo bando collegato a un bando originario, con nuovo documento e nuovi riferimenti amministrativi.
- **Bando Inglese**: richiesta GEBAN che, se attiva, produce oltre al modello italiano anche un modello/output inglese integrale tradotto usando i campi inglesi trasmessi.
- **Tipologia Bando SOL**: tipologia condivisa tra GEBAN e GEMODO, con codice SOL che GEBAN usera' nell'integrazione verso SOL.
- **Campo Comune GEBAN**: dato della bozza bando inviato a GEMODO per generazione e, in parte, usato da GEBAN per SOL.
- **Principal GEMODO**: identita' applicativa ricostruita da token Keycloak reale o mock locale, con tipo chiamante, ruoli e contesto minimo.
- **Client Tecnico GEBAN**: client Keycloak server-to-server autorizzato a chiamare le API operative GEMODO per conto del sistema GEBAN.
- **Modello Documentale Controllato**: sorgente strutturata e versionata del layout e contenuto del documento, composta da pagina, blocchi, regioni, stili ammessi, asset e placeholder; non e' HTML libero.
- **Blocco Documento**: elemento visuale ammesso nel modello, ad esempio intestazione, logo, titolo, paragrafo, tabella, colonna, firma, footer o interruzione pagina.
- **Asset Documento**: logo, immagine o risorsa grafica referenziata dal modello con identificativo, versione e hash quando disponibile.
- **Renderer PDF**: componente che trasforma modello documentale controllato e dati validati in PDF server-side, usando eventuali formati tecnici intermedi non modificabili liberamente dall'utente.

### Decision Ownership

- **Nome definitivo del servizio**: owner `009`, impatto su documentazione e naming pubblico; assunzione corrente `GEMODO`.
- **Stati definitivi di approvazione/pubblicazione modello**: owner `002` e `006`; assunzione corrente stati separati `BOZZA`, `IN_REVISIONE`, `APPROVATO`, `PUBBLICATO`, `ARCHIVIATO`, `SOSPESO`.
- **Lista iniziale tipologie GEBAN/SOL**: owner `001` e `002`; decisione confermata dal documento GEBAN: il dominio SOL completo viene preimpostato in anagrafica GEBAN, ma il perimetro iniziale GEBAN per l'ufficio reclutamento centrale include le tipologie evidenziate TDPNRR `F:jconon_call_tdet_pnrr:folder`, CD `F:jconon_call_comandi_distacchi:folder`, DIR `F:jconon_call_director:folder`, TD `F:jconon_call_tdet:folder`, CP `F:jconon_call_tind:folder_concorsi_pubblici`, RS `F:jconon_call_tind:folder_reclutamento_speciale`, CATP `F:jconon_call_tind:folder_categorie_protette`, TI `F:jconon_call_tind:folder`, SDIP `F:jconon_call_employees:folder` e MOB `F:jconon_call_mobility:folder`. Fase bloccante: seed demo e contratto catalogo della `001`.
- **Lista iniziale categorie per `BANDO_CONCORSO`**: owner `001` e `002`; assunzione corrente categorie demo minime.
- **Regole definitive di idempotenza e rigenerazione**: owner `005`; assunzione corrente nuova chiave funzionale o revisione esplicita per rigenerazione volontaria.
- **Storage definitivo per PDF**: owner `005` con supporto `004`; assunzione corrente riferimento documentale stabile indipendente dal backend fisico.
- **Regole di sicurezza per API catalogo e generazione**: owner `006`; assunzione corrente da confermare: utenti GEMODO con login SSO e ruoli GEMODO; chiamate operative GEBAN tramite token tecnico `geban-backend` verso audience/client API GEMODO, con utente reale e contesto bando nel payload per audit. Token exchange/on-behalf-of resta variante possibile solo se confermata dal team Keycloak/GEBAN.
- **Confine Keycloak/GEMODO nelle autorizzazioni applicative**: owner `006` con supporto `001`, `002`, `007` e `009`; decisione di comportamento attesa: Keycloak autentica utenti e client, valida audience e fornisce ruoli/claim generali, mentre GEMODO decide l'accesso fine a profili di integrazione, tipi documento, categorie, tipologie, modelli/versioni, contratti e operazioni. GEMODO non conserva password o segreti dei chiamanti. Fase bloccante: `PLAN` della `006` e data model dei profili in `001`/`002` prima di implementare autorizzazioni reali.
- **Profilo GEBAN versionato e mappatura campi concordata**: owner `001` con supporto `002`, `003`, `004`, `006` e `009`; assunzione corrente confermata come direzione funzionale: gestione ibrida con profilo GEBAN creato in GEMODO, versionato tramite configurazione, che associa categorie, sottocategorie, modelli richiamabili da GEBAN e placeholder/campi gia' concordati per la generazione. Le API restano disponibili per esporre catalogo e campi richiesti, ma lato creazione modello l'operatore GEMODO deve poter usare i placeholder fissati per il profilo GEBAN. Fase bloccante: `PLAN`/`TASKS` della `001`, `002`, `003` e `006` prima di implementare contratto dati operativo, builder e autorizzazioni.
- **Configurazione del profilo GEBAN**: owner `001` e `002` con supporto `009`; da definire formato della configurazione, se file versionato o dati gestiti nel builder, stati del profilo, approvazione/pubblicazione, archiviazione e propagazione ai modelli gia' pubblicati. Fase bloccante: `PLAN` della `001` e `002`.
- **Identificativi e mapping modello GEBAN-GEMODO**: owner `001`; decisione parzialmente chiarita: GEBAN deve ricevere da GEMODO la lista dei modelli validi alla data, far scegliere all'utente il modello/versione, conservare la versione scelta in tabella GEBAN e reinviarla con i dati obbligatori per la generazione. Resta da formalizzare nel contratto API il nome tecnico dell'identificativo, coerente con `modello_versione_id`, e il mapping con eventuali codici profilo o codici GEBAN. Fase bloccante: contratto API della `001`.
- **Relazione tra profilo GEBAN e catalogo GEMODO**: owner `001` e `002`; da definire relazione esatta tra profilo, tipo documento, categoria, sottocategoria, tipologia, variante, modello e versione modello pubblicata. Fase bloccante: data model e catalogo operativo.
- **API specifiche per profilo GEBAN**: owner `001` con supporto `006`; da definire se bastano catalogo e campi esistenti o se servono endpoint dedicati per recuperare modelli/campi filtrati dal profilo GEBAN. Fase bloccante: contratto OpenAPI.
- **Autorizzazioni del profilo GEBAN**: owner `006` con supporto `001`; da definire ruoli, claim, audience, client e regole che autorizzano GEBAN a usare solo profili/modelli consentiti, impedendo l'uso da chiamanti non GEBAN. Fase bloccante: implementazione sicurezza e audit.
- **Versionamento mapping campi e versione modello**: owner `001`, `002` e `003`; da definire cosa succede quando cambia un campo concordato o un placeholder: nuova versione profilo, nuova versione modello, bozza derivata o entrambe. Fase bloccante: pubblicazione modello e validazione placeholder.
- **Formato dei campi complessi**: owner `003` con supporto `001`; assunzione corrente schema strutturato con sotto-campi, tipi, obbligatorieta' e vincoli.
- **Formato visuale del modello documentale**: owner `003` con supporto `004`, `007` e `009`; decisione di comportamento attesa: il builder deve essere un editor visuale controllato, non un editor HTML. La struttura salvata deve essere un modello documentale versionato con blocchi ammessi, posizionamenti controllati, asset versionati, stili consentiti e placeholder validati. Fase bloccante: `PLAN`/`TASKS` della `003`, `004` e `007` prima di implementare builder visuale e rendering definitivo.
- **Gestione lingua italiano/inglese del bando**: owner `001` e `004` con supporto `003`; decisione confermata: nel nuovo flusso va previsto il modello inglese integrale tradotto. GEBAN invia il flag `Bando Inglese` Si/No e, se Si, i campi inglesi compilati a video; GEMODO usa la stessa tipologia modello e restituisce due output/modelli, italiano e inglese. Fase bloccante: contratto dati, validazione campi IT/EN e generazione documento.
- **Campi comuni GEBAN per generazione**: owner `001` con supporto `003`, `004` e `009`; decisione parzialmente chiarita dal documento GEBAN: il payload comune deve coprire codice bando, numero posti, bando multiplo/riferimento, titolo e descrizione ridotta IT/EN, sedi e strutture IT/EN, profilo/livello, tipo selezione, medaglione IT/EN, ribando/riferimento, PTA, flag inPA/Gazzetta e progetto di riferimento per TD/TDPNRR; `Data inizio` non va gestita. Fase bloccante: contratto dati della `001` e scenari mock.
- **Client Keycloak GEMODO e GEBAN**: owner `006` con supporto `009`; decisione proposta in attesa di conferma: configurare accesso utenti GEMODO con client/ruoli GEMODO e chiamate GEBAN-GEMODO con token tecnico server-to-server. Da confermare se CNR preferisce due client `gemodo-frontend`/`gemodo-backend` o un unico client GEMODO, se esiste gia' `geban-backend`, audience attesa, ruoli tecnici e dati audit disponibili nel payload. Fase bloccante: implementazione sicurezza reale, non Phase 1/2 della `009`.
- **Bando multiplo**: owner `001`, `004` e `005`; decisione confermata: in presenza di bando padre e uno o piu' bandi figli si genera un unico documento/PDF da firmare, riferito al padre, che contiene nell'articolo dei requisiti tutti i requisiti e i dati dei figli. Le ipotesi di documento separato per ogni figlio, parti proprie del figlio o riferimenti padre nel documento figlio sono scartate nel perimetro corrente; tra figli possono cambiare sedi, requisiti e numero di posti. Fase bloccante: aggiornamento contratto dati e scenari di generazione.
- **Ribando**: owner `001`, `004` e `005`; decisione confermata: GEBAN passa un bando di riferimento, ma GEMODO deve trattare il ribando come nuovo bando e generare un nuovo documento con nuovo protocollo, nuovo numero bando e riferimenti nei visti al bando originario e alla motivazione del ribando. Non si invia a SOL lo stesso bando con nuovo codice. Generalmente i contenuti non cambiano, ma il processo riparte come nuovo bando e deve mantenere storico/tracciabilita' tra originario e ribando anche nella procedura informatizzata. Fase bloccante: contratto dati, idempotenza, generazione e riferimento documentale.
- **Stampa, pubblicazione SOL e responsabilita' post-generazione**: owner `004` e `005` con supporto GEBAN/SOL; da definire se GEMODO deve solo generare e restituire PDF/riferimento oppure se deve supportare passaggi ulteriori verso SOL, stampa, nuova pubblicazione o recupero per moduli downstream. Fase bloccante: confine generazione/storage prima di implementare integrazioni esterne.
- **Necessita' di generare solo PDF o anche altri formati**: owner `004` e `005`; assunzione corrente PDF come output prioritario, tipo output esplicito nei contratti.
- **Priorita' futura di integrazione AI/MCP**: owner `008` con vincoli `006`; assunzione corrente non prerequisito del primo rilascio.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un ambiente locale documentato puo' avviare tutti i servizi minimi del progetto.
- **SC-002**: Il 100% delle decisioni di §17 ha owner nella project map.
- **SC-003**: Almeno uno scenario end-to-end copre catalogo, campi, validazione, generazione e consultazione stato.
- **SC-004**: Il 100% dei seed demo usati nei test e nei mock e' marcato come demo e non contiene dati reali o sensibili.
- **SC-005**: Il 100% degli scenari end-to-end minimi e' collegato ad almeno una user story o requisito di una spec owner.
- **SC-006**: Il 100% dei contratti usati dal mock GEBAN ha esempi di successo e almeno un esempio di errore funzionale.
- **SC-007**: Il 100% delle decisioni critiche aperte indica fase bloccata o assunzione provvisoria prima della generazione dei task implementativi.
- **SC-008**: Gli scenari minimi coprono almeno un caso autorizzato e un caso non autorizzato per consultazione o download.
- **SC-009**: Il 100% dei modelli demo usati per generazione ha struttura documentale controllata, versionata e priva di HTML/CSS libero o script inseriti dall'utente.

## Assumptions

- Lo stack indicato nella proposta e' input iniziale ma verra' confermato nel planning.
- I test dettagliati vengono generati nei task delle singole feature.
- I mock sono strumenti di sviluppo e verifica contrattuale, non sostituiscono collaudo
  con GEBAN reale.
- Le decisioni ancora aperte possono essere pianificate con assunzioni esplicite solo se
  la parte impattata non entra in implementazione senza conferma o sospensione documentata.
- Gli scenari minimi devono restare coerenti con sicurezza, audit, idempotenza e confini
  GEBAN/GEMODO gia' definiti nelle spec collegate.
- Keycloak e' assunto come sorgente di identita', ruoli/claim generali e client tecnici;
  GEMODO resta proprietario dei profili applicativi e delle autorizzazioni fini sui propri
  modelli, contratti e operazioni.
- Il builder visuale futuro non consentira' all'utente di scrivere HTML/CSS libero; la
  prima fase usera' seed/configurazioni per lo stesso modello documentale controllato che
  il builder manipolera' in seguito.
- Le risposte raccolte il 2026-07-28 chiudono il trattamento di bando multiplo, ribando,
  lingua inglese integrale e tipologie iniziali GEBAN/SOL come input per le spec owner
  `001`, `002`, `003`, `004` e `005`.
