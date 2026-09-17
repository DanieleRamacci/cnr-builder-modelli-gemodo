# Feature Specification: Configurazione Cataloghi E Integrazioni

**Feature Branch**: `010-configurazione-cataloghi-integrazioni`

**Created**: 2026-09-15

**Status**: Draft

**Input**: Nata da `docs/adr/0001-ownership-dati-esterni-e-onboarding-contesti.md` e
dalla sessione di lavoro 2026-09-14/15: GEMODO non copia piu' la categorizzazione di
un sistema esterno come sorgente di verita' (vedi `DEC-001-OWNERSHIP-DATI-ESTERNI`),
e l'onboarding di un tipo documento (definizione struttura, generazione del
contratto atteso, registrazione dell'endpoint) avviene tramite un'interfaccia di
amministrazione, non un file di configurazione (`DEC-001-ONBOARDING-STRUTTURA-
DOCUMENTO`).

## Clarifications

### Session 2026-09-17: integrazione per software e MVP senza editor

- Q: Da dove nasce la voce GEBAN nell'admin? -> A: Da una creazione esplicita
  dell'admin; l'elenco integrazioni parte vuoto. Nessun seed, token o URL
  configurato crea automaticamente un'integrazione operativa.
- Q: Cosa registra l'admin? -> A: Nome, codice stabile, contesto esatto del JWT
  e un singolo endpoint discovery per software. L'integrazione e' distinta
  dai tipi documento; un endpoint puo' restituire piu' tipi nel suo contesto.
- Q: Qual e' il prerequisito della verifica? -> A: La configurazione dell'URL
  e la forma comune versionata, non una definizione d'esempio per ciascun tipo.
  La verifica valida tutti i tipi/nodi/campi restituiti, senza imporre valori
  o numero di livelli degli esempi. Multi-endpoint PER_NODI e' rinviato.
- Q: Chi crea il modello? -> A: Un manager con permesso nel contesto target;
  se autorizzato in due contesti li vede entrambi. Naviga il discovery reale
  fino alla foglia e crea una BOZZA di test, senza editor visuale. PDF minimo
  non ufficiale dopo il normale workflow; owner 001/002/003/004/005/007.

Decisione canonica: [ADR 0002](../../docs/adr/0002-integrazioni-contesti-modelli-test.md).
Sostituisce il design dell'endpoint per tipo documento. US1/US2 restano strumenti
facoltativi di documentazione, non prerequisiti dell'onboarding del software.

### Session 2026-09-17: dismissione del catalogo esterno locale

Il catalogo delle categorie/tipologie/combinazioni GEBAN non viene persistito
in GEMODO. Si rimuovono ORM, repository e API di classificazione del vecchio
flusso, oltre al fallback del builder sul seed locale. I modelli creati in
GEMODO, le versioni, il contratto selezionato e lo storico restano persistenti:
sono prodotti del servizio, non una replica del catalogo GEBAN.
Il modello conserva codici e percorso esterno, senza FK a tabelle di
classificazione locale. Prima della creazione modello/versione la selezione
deve essere verificata su una foglia della porta ricorsiva.
Questa decisione sostituisce le precedenti note di riuso delle entita'
CategoriaDocumento/TipologiaBandoSOL/ClassificazioneCatalogo della 001.
La configurazione self-service e la documentazione di esempio sono distinte
dal catalogo GEBAN; non giustificano un fallback per un'integrazione non connessa.

### Session 2026-09-15

- Q: Serve imporre un solo endpoint HTTP a ogni sistema che si integra? -> A: No.
  Si standardizza il *contratto logico* (dato un tipo documento, restituisci
  tipologie/profili/campi con una data di validita'), non il numero di chiamate
  HTTP necessarie a comporlo. Un client HTTP generico gestisce la paginazione
  (pattern HAL gia' osservato su un'API reale di GEBAN) in modo trasparente, dietro
  l'adapter — la definizione della struttura e la generazione del contratto non
  devono sapere se dietro c'e' una chiamata o dieci (`DEC-002-PORTS-ADAPTERS-
  DISCOVERY`).
- Q: Come si evita di far reinserire dati standard ripetuti (es. gli stessi campi
  per ogni combinazione tipologia/profilo)? -> A: I campi del contratto dati sono
  definiti una volta, allo stesso livello delle tipologie, non duplicati dentro
  ogni combinazione. Un campo i cui valori ammessi dipendono dal profilo scelto
  (es. il "livello" trovato su `/api/v1/profili` di GEBAN: Ricercatore I/II/III,
  Funzionario di Amministrazione IV/V) referenzia un attributo definito una sola
  volta sul profilo, invece di essere ridefinito per ogni combinazione.
- Q: Quale forma ha l'interfaccia di definizione in questo primo incremento? -> A:
  Una visualizzazione JSON ad albero (nodi collassabili/espandibili), non un
  wizard con form/matrice dedicati per ogni passo. Scelta esplicita per partire
  velocemente; puo' evolvere in un'interfaccia piu' guidata in un secondo tempo,
  senza cambiare lo schema logico sottostante.
- Q: Il caso GEBAN e' gia' concreto o solo un esempio teorico? -> A: Concreto.
  `docs/adr/0001-esempio-discovery-geban.json` e' il primo caso reale — costruito
  sui codici verificati sugli endpoint di test di GEBAN il 2026-09-15 — usato come
  riferimento per questa spec, non ancora come file consumato a runtime.

### Session 2026-09-15 (seconda parte)

- Q: Le tre API GEBAN-facing di classificazione gia' implementate dalla `001`
  (`/catalogo/tipi-documento`, `/profili`, `/classificazione`) restano nel
  contratto pubblico? -> A: No, si ritirano
  (`DEC-001-RITIRO-ENDPOINT-CLASSIFICAZIONE`). GEBAN possiede gia' la propria
  categorizzazione, non ha bisogno di richiederla a GEMODO. Lo schema/esempio
  generato da FR-006 e' il sostituto funzionale: non un endpoint runtime nostro,
  ma la documentazione che dice agli sviluppatori esterni come strutturare
  l'endpoint di discovery che loro devono esporre verso GEMODO. Il contratto
  GEBAN-facing verso la `001` si riduce a `/catalogo/modelli`,
  `/campi-richiesti`, `/documenti/valida`, `/documenti/genera` — tutte relative
  a cosa ha GEMODO, mai a cosa possiede il sistema esterno.
- Q: Quando l'operatore GEMODO naviga l'albero tipologia/profilo/campi per creare
  un nuovo modello (FR-011, interrogazione live della porta di discovery) e il
  sistema esterno integrato e' irraggiungibile in quel momento, si usa una cache
  locale? -> A: Cache breve **in memoria di processo** soltanto (nessuna tabella
  DB persistente) per fluidita' di navigazione; se il sistema esterno resta
  irraggiungibile oltre quella finestra, la navigazione si ferma e restituisce un
  errore funzionale di connessione — mai un elenco vuoto o dati stantii silenziosi
  (coerente con l'Acceptance Scenario 3 della User Story 3).

### Session 2026-09-16

- Q: Lo schema/esempio generato da GEMODO vincola anche i valori reali
  restituiti dall'API integrata? -> A: No. La documentazione di integrazione
  vincola la **forma logica comune** dell'endpoint di discovery (albero
  ricorsivo, nodi, foglie, campi e struttura dei tipi dato), non una fotografia
  statica delle tipologie/profili/campi reali. Per un contesto integrato
  (GEBAN o futuro sistema esterno), i dati operativi usati per creare un
  modello arrivano dall'API del sistema integrato tramite `PortaDiscovery`; il
  modello salva nel DB lo snapshot/struttura scelta in funzione di quei dati
  reali. Gli esempi consegnati agli integratori sono illustrativi: il test di
  connessione fallisce se la risposta non rispetta la forma comune o manca di
  attributi obbligatori, non solo perche' i valori restituiti differiscono dagli
  esempi.

## User Scenarios & Testing *(mandatory)*

### Decisione 2026-09-17: verifica autonoma delle variazioni GEBAN (rinviata nel MVP)

GEBAN espone il discovery completo su
`https://geban-service.test.si.cnr.it/api/v1/gemodo/discovery`.
Non si richiedono ID numerici o versioni esterne per ogni campo. GEMODO
identifica il ramo con il percorso completo dei codici e conserva sulla versione
del modello una firma SHA-256 dei dati rilevanti alla creazione. I codici devono
essere stabili: una modifica semantica non esposta nella risposta non e' rilevabile.

La firma usa chiavi ordinate, campi ordinati per codice e opzioni ordinate dove
l'ordine non ha significato. Include percorso, definizioni rilevanti dei campi
(codice, tipo, obbligatorieta', vincoli), attributi utilizzati e default.
Esclude timestamp di acquisizione, `validita` variabile a ogni richiesta e
dettagli puramente descrittivi. Rileva anche nuovi campi obbligatori nel ramo;
nuovi campi opzionali non utilizzati non rendono da soli il modello incompatibile.

Il controllo recupera il catalogo corrente e ricalcola la firma del ramo.
Una firma diversa avvia il confronto con il contratto immutabile del modello:
la firma da sola non spiega la differenza e non determina automaticamente
l'obsolescenza. Un percorso scomparso viene segnalato esplicitamente.
Non si conserva una replica persistente dell'intero catalogo GEBAN: si salvano
solo contratto del modello, firma, data/esito verifica e differenze rilevanti.

Un runner periodico recupera una risposta per integrazione e ciclo, indicizza
i rami in memoria e confronta i modelli interessati. Un'indisponibilita' esterna
produce un esito non verificabile, non una dichiarazione di obsolescenza.
Il controllo e' previsto anche prima della nuova generazione ufficiale, con
ownership del percorso di generazione nella spec 004. Frequenza, timeout,
politica di indisponibilita' e soglie di blocco/avviso restano da dettagliare.
Le versioni pubblicate non si aggiornano automaticamente.

### User Story 1 - Definire la struttura di un tipo documento (Priority: P1)

Come operatore GEMODO, voglio definire — tramite una visualizzazione JSON ad
albero — un tipo documento con le sue tipologie, profili e campi del contratto
dati, cosi' da avere un'unica sorgente per generare sia la documentazione per un
integratore esterno sia, in un incremento self-service successivo, una
definizione proprietaria GEMODO (non il registro globale legacy).

**Why this priority**: questo passo abilita la generazione della documentazione
d'esempio US2. Non blocca creazione/verifica dell'integrazione software US3.

**Independent Test**: un operatore puo' creare un tipo documento con almeno una
tipologia, un profilo e un campo, e vederlo salvato come "definito" senza che sia
ancora utilizzabile per creare modelli.

**Acceptance Scenarios**:

1. **Given** nessun tipo documento con quel codice esiste, **When** l'operatore lo
   definisce con tipologie/profili/campi tramite l'albero JSON, **Then** la
   definizione viene salvata con stato "definito, non connesso".
2. **Given** un profilo ha un attributo aggiuntivo (es. livello) con valori
   ammessi e un default, **When** un campo del contratto dati referenzia
   quell'attributo, **Then** il campo non richiede una lista di opzioni propria —
   le eredita dal profilo scelto in fase di creazione modello.
3. **Given** una definizione incompleta (es. un tipo documento senza nessuna
   tipologia), **When** l'operatore prova a generare il contratto (User Story 2),
   **Then** il sistema impedisce la generazione e segnala cosa manca.

---

### User Story 2 - Generare il contratto/documentazione per l'integratore (Priority: P1)

Come operatore GEMODO, voglio che la definizione della User Story 1 produca
automaticamente uno schema/esempio JSON che descrive la forma logica comune
della risposta attesa dall'endpoint di discovery, cosi' da consegnarlo a un
team di sviluppo esterno senza ambiguita' su come strutturare la propria API.

**Why this priority**: e' il meccanismo che sostituisce il "far indovinare" al
team esterno cosa GEMODO si aspetta — nucleo del cambio di paradigma di questa
spec.

**Independent Test**: dato un tipo documento completamente definito, l'operatore
ottiene uno schema/esempio scaricabile che chiarisce forma comune e tipi dato;
un endpoint di prova con valori diversi dagli esempi ma conforme alla forma
comune viene accettato dal test di connessione della User Story 3.

**Acceptance Scenarios**:

1. **Given** una definizione completa, **When** l'operatore genera il contratto,
   **Then** ottiene un JSON Schema/esempio con struttura dell'albero, struttura
   dei campi, tipi dato e data di validita' della forma contrattuale.
2. **Given** il contratto e' stato generato, **When** l'operatore lo esporta,
   **Then** puo' scaricarlo o copiarlo per consegnarlo a un team esterno.

---

### User Story 3 - Registrare l'endpoint e attivare l'integrazione (Priority: P1)

Come admin GEMODO, voglio creare da zero un'integrazione per software, indicare
nome, codice_contesto e URL discovery singolo e verificarne la forma comune,
cosi' che i tipi documento restituiti diventino navigabili dai manager autorizzati.
Non devo prima definire categorie/campi o generare esempi per quei tipi.

**Why this priority**: senza un endpoint registrato e verificato, un tipo
documento integrato resta definito ma inutilizzabile — evita che un operatore
inizi a creare modelli contro un'integrazione che non funziona ancora.

**Independent Test**: su un elenco vuoto creare un software demo con contesto e
URL; verificare una risposta con due tipi documento e nessuna definizione
d'esempio locale. Entrambi sono disponibili ai manager di quel contesto solo
dopo CONNESSO. Una risposta non conforme o irraggiungibile produce ERRORE.

**Acceptance Scenarios**:

1. **Given** un'integrazione creata dall'admin con contesto e URL, **When**
   la verifica della forma comune riesce su tutti i tipi restituiti, **Then**
   l'integrazione risulta CONNESSO senza richiedere US1/US2.
2. **Given** un endpoint registrato restituisce una risposta che viola la forma
   comune versionata, **When** viene testato, **Then** il sistema
   segnala l'errore e non marca il contesto come connesso.
3. **Given** un endpoint registrato e' temporaneamente irraggiungibile in fase di
   *creazione modello* (non di sola consultazione), **When** un operatore prova a
   creare un modello, **Then** l'operazione fallisce con errore esplicito, non con
   un menu vuoto silenzioso.
4. **RINVIATO fuori dall'incremento FR-016**: **Given** un tipo documento self-service (nessun sistema esterno), **When**
   l'operatore lo configura, **Then** il flusso si ferma alla User Story 1/2:
   nessuna registrazione di endpoint richiesta, il contesto risulta subito
   utilizzabile tramite una sorgente proprietaria canonica da implementare in
   US1/T036. Nel runtime dell'incremento FR-016, assenza di URL produce 503:
   non implica self-service e non abilita alcun fallback locale.

---

### User Story 4 - Vedere lo stato di connessione nella dashboard (Priority: P2)

Come operatore GEMODO, voglio vedere in una dashboard quali contesti documentali
sono definiti ma non ancora connessi e quali sono attivi, cosi' da sapere cosa
manca prima che un utente possa creare modelli per quel contesto.

**Why this priority**: migliora l'operativita' ma non blocca il flusso principale
(le User Story 1-3 bastano a rendere un'integrazione funzionante anche senza
questa vista).

**Independent Test**: la dashboard admin elenca le integrazioni create,
non i tipi documento dedotti dai seed; mostra nome, contesto, endpoint,
stato, data ed esito. Su installazione senza configurazioni l'elenco e' vuoto.

**Acceptance Scenarios**:

1. **Given** esistono integrazioni in stati diversi, **When** l'operatore apre
   la dashboard, **Then** vede per ciascuna lo stato corrente e, se applicabile,
   l'esito dell'ultimo test di connessione.

### Edge Cases

- Un endpoint registrato che non rispetta la forma comune dello schema generato
  (attributi obbligatori mancanti, tipi dato errati, nodi con `figli` e `campi`
  insieme, o struttura non ricorsivamente leggibile).
- Un endpoint irraggiungibile al momento della registrazione (test di connessione
  fallito) — il contesto resta "non connesso", non entra in uno stato ambiguo.
- Un tipo documento definito ma mai connesso: deve restare non utilizzabile per la
  creazione di modelli, non generare un errore generico non distinguibile da altri.
- Due integrazioni espongono lo stesso codice tipo documento: l'identita'
  include l'integrazione, senza mescolare dati o permessi.
- Token con ruolo manager in un contesto e solo lettura in un altro: il secondo
  non abilita creazione modello. L'autorizzazione precede la chiamata HTTP.
- URL modificato mentre una verifica e' in corso: l'esito della vecchia URL
  non abilita la configurazione nuova. Una risposta parzialmente conforme
  (un tipo valido e uno invalido) non abilita l'integrazione intera.
- Ridefinizione di una struttura (tipologie/profili/campi) per un tipo documento
  gia' connesso e con modelli pubblicati: i modelli esistenti non devono essere
  invalidati silenziosamente (FR-013).
- Un attributo profilo-dipendente (es. livello) i cui valori ammessi cambiano nel
  tempo lato sistema esterno: firma e contratto del modello consentono il
  confronto anche senza una data di validita' esterna stabile.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Il sistema MUST fornire un'interfaccia di amministrazione per
  definire un tipo documento (codice, nome, `codice_contesto` che ne autorizza
  la scrittura — `DEC-001-CONTESTO-SOSTITUISCE-UFFICIO`, nessuna entita' Ufficio
  separata).
- **FR-002**: Il sistema MUST permettere di definire, per un tipo documento, una o
  piu' tipologie (codice, descrizione, riferimento esterno opzionale).
- **FR-003**: Il sistema MUST permettere di definire, per un tipo documento, uno o
  piu' profili/categorie (codice, descrizione) con attributi aggiuntivi opzionali
  (nome attributo, valori ammessi, valore di default) per rappresentare dati come
  il "livello" che variano per profilo.
- **FR-004**: Il sistema MUST permettere di definire le combinazioni ammesse fra
  tipologia e profilo per un tipo documento.
- **FR-005**: Il sistema MUST permettere di definire i campi del contratto dati
  (codice, etichetta, tipo, lingua, obbligatorieta', ordine, validazione), incluso
  marcare un campo come dipendente da un attributo profilo definito in FR-003
  invece che con opzioni fisse.
- **FR-006**: Il sistema MUST generare, dalla definizione, uno schema/esempio JSON
  che rappresenta la forma logica comune della risposta attesa dall'endpoint di
  discovery di un sistema esterno integrato (albero di categorizzazione, nodi,
  foglie, struttura dei campi, tipi dato, data di validita'). Lo schema/esempio
  MUST NOT essere trattato come sorgente autoritativa dei valori reali che
  l'endpoint integrato restituira'.
- **FR-007**: Il sistema MUST permettere di esportare la documentazione generata
  in FR-006 per consegnarla a un team di sviluppo esterno.
- **FR-008**: Il sistema MUST permettere di registrare l'URL di un endpoint
  esterno sull'integrazione software e verificare l'intera risposta contro la
  forma comune versionata prima di marcarla CONNESSO. Non sono necessari
  definizioni o schemi d'esempio locali; valori diversi dagli esempi sono validi.
- **FR-009**: Un tipo documento integrato senza un endpoint registrato e
  verificato MUST restare non utilizzabile per la creazione di modelli; questo
  stato MUST essere visibile in una dashboard (User Story 4).
- **FR-010** *(RINVIATO fuori dall'incremento FR-016, non criterio di chiusura
  della dismissione)*: un futuro tipo documento self-service MUST usare una
  definizione proprietaria GEMODO tramite PortaDiscovery senza endpoint esterno.
  Non usare le tabelle/AdapterLocale legacy ritirati. Progettazione della
  sorgente richiesta prima di US1/T036; nel runtime corrente una URL mancante
  produce DISCOVERY_NON_CONFIGURATA, non attiva implicitamente self-service.
- **FR-011**: Il client HTTP che interroga un endpoint registrato MUST gestire
  trasparentemente la paginazione se presente, assemblando il risultato completo
  prima di restituirlo al resto del sistema — la definizione (FR-001..FR-007) MUST
  restare indipendente da questo dettaglio di trasporto.
- **FR-012**: L'accesso a questa interfaccia di amministrazione MUST essere
  riservato a `GEMODO_ADMIN`, gia' previsto dalla `006` FR-005/FR-005a,
  distinto da `GEMODO_MODELLI_GESTORE` (che
  opera sui modelli di un tipo documento gia' connesso, non sulla sua
  definizione). Il backend applica il ruolo, senza attribuirlo implicitamente
  ai ruoli GEBAN di gestione modelli.
- **FR-013**: Ogni definizione (tipo documento, tipologie, profili, campi) MUST
  essere versionata: una modifica dopo che il contesto e' gia' connesso e in uso
  MUST NOT invalidare silenziosamente i modelli gia' creati con la struttura
  precedente.
- **FR-014** *(rinviato nel MVP, non requisito del primo PDF di test)*: Il sistema MUST conservare sulla versione modello percorso,
  firma SHA-256 versionata e contratto necessario al confronto dei dati esterni,
  senza una replica persistente del catalogo. Il confronto MUST rilevare nuovi
  campi obbligatori, dipendenze modificate/rimosse e percorsi scomparsi, ignorando
  timestamp variabili e modifiche a rami o campi opzionali non utilizzati.
- **FR-015** *(rinviato nel MVP insieme alle soglie)*: Il sistema MUST prevedere una verifica periodica con una risposta
  per integrazione/ciclo, esiti distinti dalla pubblicazione e motivi visibili.
  Un errore esterno MUST risultare non verificabile, mai allineato od obsoleto
  per il solo errore di connessione. Il controllo alla generazione appartiene
  alla `004` e richiede la politica di indisponibilita' esplicita.
- **FR-016**: Il sistema MUST dismettere il catalogo esterno locale: tabelle
  categorie/tipologie/combinazioni, FK dai modelli, repository e API di
  classificazione ritirate e adapter locale del vecchio builder. Una migration
  MUST preservare identificativi/versioni/contratti dei modelli, convertendo
  i riferimenti precedenti in codici/percorso. Il builder MUST usare il discovery
  della sorgente integrata e rifiutare una sorgente non configurata, senza seed
  o dati locali di fallback. La ricerca di modelli GEMODO pubblicati resta locale,
  filtrata sui riferimenti del modello, senza ricopiare cataloghi esterni.
- **FR-017**: Il sistema MUST gestire un'Integrazione distinta dal TipoDocumento,
  con identificativo stabile, codice univoco, nome, codice_contesto e modalita'
  SINGOLO_ENDPOINT. Nessun GEBAN preinstallato, dedotto o hardcoded nell'elenco.
- **FR-018**: codice_contesto MUST corrispondere esattamente alla chiave contexts
  del JWT. Configurarlo MUST NOT assegnare contesti/ruoli, sostituire mapping
  della 006 o attribuire permessi attraverso il solo nome del software.
- **FR-019**: Il discovery MUST identificare tipi/percorso rispetto
  all'integrazione sorgente, supportare piu' tipi dallo stesso endpoint e
  mantenerne categorie/campi in memoria, mai importarli come catalogo DB.
- **FR-020**: Le viste manager MUST filtrare le sorgenti per permesso nel
  singolo contesto e stato CONNESSO; piu' contesti autorizzati sono cumulabili
  senza propagare permessi dall'uno all'altro. Il backend verifica lo stesso scope.
- **FR-021**: La verifica MUST mostrare data/esito/motivi sanificati e la
  configurazione verificata; nessun successo obsoleto o risposta parzialmente
  conforme abilita la sorgente. Cambiare URL richiede nuova verifica; cambiare
  esempi illustrativi non modifica l'esito della forma comune.

### Key Entities *(include if feature involves data)*

- **Tipo Documento**: configurazione proprietaria GEMODO con `codice_contesto`,
  non replica del catalogo esterno. Nessuna entita' Ufficio separata.
- **Integrazione**: software sorgente creato dall'admin, con nome, contesto,
  identificativo e endpoint; non una voce ricavata dal catalogo dei modelli.
- **Nodi/Campi Discovery**: categorie/tipologie/profili e definizioni di campo
  della risposta esterna, tenuti in memoria; nessuna tabella locale di catalogo.
- **Modello/Versione/Campo Richiesto**: entita' proprietarie persistenti,
  con percorso selezionato e contratto della sola versione, senza FK esterne.
- **Definizione Proprietaria Self-service** *(rinviata, FR-010)*: futura
  sorgente locale esplicita tramite PortaDiscovery, distinta dagli esempi
  destinati a integrazioni esterne. Il registro globale legacy non esiste piu'.
- **Attributo Profilo** *(nuova)*: attributo aggiuntivo opzionale su un profilo
  (nome, valori ammessi, valore di default) — generalizza il caso "livello".
  Referenziato da un Campo Richiesto per rendere le sue opzioni dipendenti dal
  profilo scelto in fase di creazione modello.
- **Endpoint Di Integrazione** *(nuova)*: unico URL registrato per software
  integrato, stato (definito / connesso / errore ultima verifica), esito e data
  dell'ultimo test di connessione.
- **Schema Di Discovery Generato** *(nuova)*: rappresentazione JSON Schema/esempio
  prodotta dalla definizione (FR-006), versionata, usata sia come documentazione
  per l'integratore; il test FR-008 usa direttamente il contratto comune
  versionato, non richiede questa generazione. Non contiene la lista autoritativa e
  definitiva dei valori operativi: quelli arrivano dall'API integrata.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un operatore puo' definire un nuovo tipo documento completo
  (almeno una tipologia, un profilo, un campo) e ottenere lo schema generato senza
  scrivere codice.
- **SC-002**: Un endpoint registrato che non rispetta la forma comune versionata
  viene segnalato nel test di verifica, prima di consentire la creazione di
  modelli. Un esempio locale non e' prerequisito ne' autorita' sui valori.
- **SC-003** *(RINVIATO fuori dall'incremento FR-016)*: Un tipo documento self-service diventa utilizzabile per la
  creazione di modelli subito dopo la definizione (User Story 1), senza dover
  passare per la User Story 3.
- **SC-004**: Nessun modello pubblicato viene invalidato da una successiva
  modifica alla definizione del suo tipo documento (FR-013).
- **SC-005**: Senza creazioni admin, la lista integrazioni e' vuota anche con
  token GEBAN, modelli demo o URL di ambiente presenti.
- **SC-006**: Un admin puo' verificare una sorgente con almeno due tipi
  documento senza creare definizioni d'esempio; un tipo non conforme impedisce CONNESSO.
- **SC-007**: Nei test con due contesti, nessuna lettura/creazione manager
  autorizzata in un contesto accede a dati o permessi dell'altro senza titolo.

## Assumptions

- Questa spec nasce da `docs/adr/0001-ownership-dati-esterni-e-onboarding-
  contesti.md` e dalle decisioni confermate `DEC-001-OWNERSHIP-DATI-ESTERNI`,
  `DEC-001-ONBOARDING-STRUTTURA-DOCUMENTO`, `DEC-002-PORTS-ADAPTERS-DISCOVERY`.
- Il primo caso d'uso reale e' GEBAN/`BANDO_CONCORSO`; lo schema di riferimento
  per questo caso e' `docs/adr/0001-esempio-discovery-geban.json` (esempio da
  consegnare al team GEBAN, non ancora un file consumato a runtime).
- La sezione admin integrazioni usa tabella/lista e dettaglio con nome, contesto,
  URL e risultati verifica. L'albero JSON resta per la documentazione US1/US2,
  non obbliga l'admin a definire il catalogo reale. Le UI sono owner 007.
- Fuori scope di questa spec: l'editor visuale del documento/sezioni/placeholder
  (`003`), la generazione PDF (`004`), la gestione granulare di permessi oltre a
  ruolo+contesto (`006`, FR-012 rimanda li' il dettaglio).
- Le combinazioni tipologia-profilo e il meccanismo esatto degli attributi
  profilo-dipendenti (FR-003) per il caso GEBAN restano da validare con il loro
  team prima che l'integrazione reale vada in produzione (vedi note
  `_confermato: false` residue in `docs/adr/0001-esempio-discovery-geban.json`).
- La documentazione di integrazione e gli esempi servono a comunicare la forma
  comune da implementare; la struttura effettivamente salvata in un modello GEMODO
  nasce dai dati restituiti dall'endpoint integrato al momento della creazione del
  modello.
