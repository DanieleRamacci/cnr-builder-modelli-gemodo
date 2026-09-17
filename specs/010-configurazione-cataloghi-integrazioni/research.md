# Research - Configurazione Cataloghi E Integrazioni

Nessun "NEEDS CLARIFICATION" residuo nel Technical Context del `plan.md`: le
scelte tecniche riusano stack e convenzioni gia' validate da `001`/`002`. Questo
documento registra le decisioni di design specifiche di questa spec, emerse
nella sessione di lavoro 2026-09-15 (dopo la spec.md gia' chiarita).

## Decision: modulo condiviso `app.discovery` per la porta e i due adapter

**Rationale**: sia questa spec (registrazione/test endpoint, navigazione a
livelli in fase di definizione) sia la `002` (scelta campi/placeholder in fase
di creazione modello) devono interrogare "quali categorie/tipologie/campi sono
disponibili per questo tipo documento" senza sapere se la risposta viene da
`AdapterLocale` o `AdapterHTTP` (`DEC-002-PORTS-ADAPTERS-DISCOVERY`). Un modulo
unico evita che la logica di chiamata HTTP, paginazione e cache venga
duplicata o diverga fra le due spec.

**Alternatives considered**:

- Duplicare l'adapter dentro `002` e dentro `010` — scartato: rischio concreto
  di divergenza silenziosa (es. una gestisce la paginazione, l'altra no) gia'
  visto come problema nella cascading di `DEC-002-PORTS-ADAPTERS-DISCOVERY`.
- Mettere la porta dentro `app.catalog` (dove vivono le entita' che espone) —
  scartato: `app.catalog` e' dominio della `001` (GEBAN-facing), mentre la
  porta e' infrastruttura condivisa fra builder e configurazione; tenerla
  separata rende esplicita la dipendenza nel verso corretto (`002`/`010`
  dipendono da `app.discovery`, non viceversa).

## Decision: cache dell'adapter HTTP in memoria di processo, nessuna tabella persistente

**Rationale**: confermato esplicitamente dal product owner (2026-09-15). Per
un tipo documento self-service la sorgente resta sempre locale (`AdapterLocale`,
nessuna cache necessaria). Per un tipo documento integrato, la definizione
struttura (User Story 1) e l'esecuzione dei modelli gia' pubblicati
(`ModelloCampoRichiesto`, dati di `001`) non leggono mai la categorizzazione
esterna — solo la *creazione di un nuovo modello* (navigazione a livelli) la
interroga, ed e' un'azione occasionale, non una API ad alta frequenza. Una
cache persistente introdurrebbe di nuovo il problema che l'ADR 0001 ha
risolto (copia locale di dati non piu' posseduti da GEMODO, che puo'
disallinearsi silenziosamente dalla sorgente). Una cache in memoria di breve
durata copre solo la fluidita' della sessione di navigazione di un singolo
operatore, non sopravvive a un riavvio del processo, e non e' mai la fonte per
nessuna decisione di validazione o generazione documento.

**Alternatives considered**:

- Cache persistente con TTL (ore) — scartata: riapre esattamente il dubbio
  sollevato dal product owner ("perche' ce li salviamo dentro il DB se non
  copiamo piu' i dati?"); il volume/frequenza d'uso (creazione modello,
  occasionale) non giustifica il costo di mantenere una tabella sincronizzata.
- Nessuna cache, chiamata live ad ogni click di navigazione livello per
  livello — scartata: peggiora l'esperienza dell'operatore senza un beneficio
  di correttezza (i livelli sono aperti/chiusi nella stessa sessione breve).

**Comportamento su indisponibilita'**: se il sistema esterno non risponde
oltre la finestra della cache in memoria, la navigazione si ferma e restituisce
un errore funzionale di connessione — mai un elenco vuoto silenzioso (Edge
Case gia' presente in `spec.md`, Acceptance Scenario 3 US3). Questo vale sia
in fase di creazione modello (`002`) sia in fase di test di connessione
(FR-008).

## Decision: le tre API GEBAN-facing di classificazione della `001` sono il caso concreto che rende necessaria questa spec

**Rationale**: `GET /catalogo/tipi-documento`, `/profili`, `/classificazione`
(implementate nel primo incremento della `001`) rispecchiavano verso GEBAN una
categorizzazione letta da seed locale — corretto quando GEMODO era la
sorgente di verita', sbagliato dopo `DEC-001-OWNERSHIP-DATI-ESTERNI`: GEBAN
non ha bisogno di richiedere a GEMODO il proprio stesso catalogo.
`DEC-001-RITIRO-ENDPOINT-CLASSIFICAZIONE` (2026-09-15) le ritira dal contratto
pubblico. Lo `Schema Di Discovery Generato` di questa spec (FR-006/FR-007) e'
il sostituto funzionale, ma con una differenza categorica: non e' un endpoint
runtime chiamato da GEBAN, e' un contratto/documentazione consegnato una volta
a un team di sviluppo esterno. `001/tasks.md` traccia la rimozione effettiva
del codice come T108, bloccata finche' questa spec non eroga la generazione
del contratto.

**Alternatives considered**:

- Mantenere le tre API e ripuntarle sull'adapter di discovery (proxy live) —
  scartata per il caso GEBAN: non risulta un bisogno reale (GEBAN non deve
  chiedere a noi la propria categorizzazione); resta un'opzione aperta solo se
  un futuro sistema integrato diverso da GEBAN chiedesse esplicitamente questa
  vista — non e' il caso ora, non progettarla preventivamente.

## Decision: il contratto di discovery vincola la forma comune, non i valori reali

**Rationale**: la documentazione generata da GEMODO serve agli sviluppatori del
sistema integrato per sapere come deve essere strutturata la risposta
(`DiscoveryResponse`, albero ricorsivo, nodi, foglie, campi e tipi dato). Non e'
una copia dei dati di classificazione e non deve diventare una sorgente
autoritativa parallela. Per un tipo documento integrato, la creazione di un
modello legge tipologie/profili/campi dall'API registrata tramite `AdapterHTTP`;
il modello salva nel DB la struttura scelta a partire da quei dati reali. Questo
preserva `DEC-001-OWNERSHIP-DATI-ESTERNI`: GEMODO conosce la forma del contratto,
ma il sistema esterno resta proprietario dei valori di classificazione.

**Validation boundary**: il test di connessione deve rifiutare risposte che non
rispettano la forma comune (attributi obbligatori mancanti, tipi dato errati,
nodi non validi), ma non deve rifiutare una risposta solo perche' i valori reali
differiscono dagli esempi pubblicati nella documentazione.

**Alternatives considered**:

- Trattare lo schema/esempio generato come lista autoritativa di valori ammessi —
  scartato: ricreerebbe una copia locale dei dati esterni e contraddirebbe il
  cambio di paradigma dell'ADR 0001.
- Accettare qualunque JSON dall'endpoint registrato — scartato: senza forma comune
  il builder non potrebbe navigare e salvare modelli in modo deterministico.

## Decision: paginazione HAL gestita internamente all'adapter HTTP

**Rationale**: gia' chiarito in `spec.md` (FR-011) e osservato su
`/api/v1/tipoSols` di GEBAN (envelope `_embedded`/`_links`/`page`, pattern
Spring Data REST). L'adapter assembla il risultato completo prima di
restituirlo alla porta astratta — la definizione struttura (User Story 1) e il
builder (`002`) non devono mai sapere quante chiamate HTTP sono state fatte.

**Alternatives considered**: esporre la paginazione al chiamante (streaming) —
scartata, non necessaria alla scala attesa (decine di tipologie/profili per
tipo documento, non migliaia) e complica inutilmente sia l'interfaccia di
definizione sia il builder.

## Assunzione provvisoria da esplicitare: `DEC-001-VERSIONING-RIFERIMENTI-ESTERNI`

**Stato**: `ASSUNTA_PROVVISORIA`, blocca la fase `TASKS` per questa spec
(verificato con `valuta_readiness`, 2026-09-15). Il meccanismo esatto — come si
mostra la data di validita' del riferimento esterno, quali soglie generano
errore vs avviso quando un endpoint registrato restituisce dati non attesi
rispetto allo `Schema Di Discovery Generato` — resta da chiudere col product
owner ("vediamo").

**Come viene esplicitata, non silenziata**: `tasks.md` marca esplicitamente i
task che dipendono da questo dettaglio (validazione dati esterni non attesi,
FR-013 in dettaglio) come bloccati da questa decisione, invece di
implementarli assumendo silenziosamente una soglia. I task di sola definizione
struttura (User Story 1) e generazione contratto (User Story 2) non dipendono
da questo dettaglio e possono procedere.
