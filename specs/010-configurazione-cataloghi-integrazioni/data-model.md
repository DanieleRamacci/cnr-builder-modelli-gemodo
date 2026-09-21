# Data Model - Configurazione Cataloghi E Integrazioni

## Target Confermato - Integrazione Per Software

Persistenza target implementata con 0012/0013; onboarding HTTP, resolver
registrato e viste manager ancora nei task T081-T084, non gia' operativi.
MappaDiscovery implementata: cataloghi indicizzati per codice, non vuoti,
identita' codice coerente e alberi validati tutti prima di cache. Catalogo
per singolo tipo e' una selezione della stessa mappa; nessuna chiamata per
livello. Cache copie profonde per namespace/sorgente/revisione/URL, RAM.

ADR 0002 sostituisce l'associazione endpoint/tipo documento delle migration
0010/0011. Il target non e' ancora il runtime: servono nuove migration e
contratti, preservando gli identificativi e i dati proprietari esistenti.

### Integrazione

Implementazione T079 in due revisioni: 0012 crea registro vuoto e audit
integrazione, aggiunge TipoDocumento.integrazione_id nullable con FK composita
che impone il medesimo codice_contesto. Nessun backfill automatico: modelli e
tipi esistenti mantengono gli ID e proprieta' non associata. Unicita' globale
dei codici resta temporaneamente fino all'adeguamento consumer nella seconda
revisione. Questa fondazione non attiva nuove sorgenti operative.
Codice_contesto massimo 64 caratteri, coerente con TipoDocumento esistente.
Seconda revisione 0013 implementata: endpoint per software, namespace scoped e archivio inerte
degli esiti precedenti; runtime legacy da rimuovere nei task T081/T082.
Downgrade 0012 ammesso solo se registro e audit sono vuoti e nessun tipo e'
associato: altrimenti blocco esplicito, non perdita silenziosa di configurazioni
o audit. Backup prima di qualsiasi migrazione sul DB operativo.

EndpointIntegrazione non ha piu' tipo_documento_id o FK schema d'esempio:
integrazione_id univoco, timeout 1..10s, revisione/contratto verificati, esito/data
e prenotazione tentativo_id/scadenza (entrambi presenti o assenti). Per stati
CONNESSO/ERRORE sono obbligatori i metadati della verifica. Esiti precedenti in
endpoint_integrazione_storico senza ORM o letture runtime; nessun import nel
registro. Codici univoci per integrazione; indice univoco per tipi non associati.
Downgrade 0013 rifiutato se ci sono nuovi endpoint o codici duplicati; altrimenti
restaura esattamente la tabella precedente. Associazione tramite servizio interno
amministrativo, esplicita, con contesto uguale e audit atomico, senza trasferire
un tipo gia' associato a un altro software. Nessun nuovo endpoint HTTP di
associazione e' esposto in questo incremento.

UUID stabile, codice interno univoco, nome visualizzato, codice_contesto,
modalita' SINGOLO_ENDPOINT, versione_configurazione positiva e timestamp.
Creazione solo admin, nessuna riga inserita automaticamente per GEBAN.
codice_contesto e' la chiave esatta del JWT e non una sorgente di ruoli.
Con tipi/modelli gia' associati, cambiarlo richiede una migrazione esplicita
di ownership/permessi, non una rinomina che trasferisce implicitamente l'accesso.

TipoDocumento aggiunge integrazione_id (nullable per storico non associato e
futuro self-service). I tipi operativi integrati sono identificati da
integrazione_id + codice esterno; codici uguali in sorgenti diverse sono distinti.
codice_contesto del tipo deve coincidere con quello della sorgente associata.
La configurazione minima del tipo necessaria a un modello non equivale a
importare tutti i tipi/categorie/campi restituiti dal discovery.

### EndpointIntegrazione Target

integrazione_id sostituisce tipo_documento_id: relazione 0..1/1:1 con il
software. URL configurabile, timeout, stato DEFINITO/CONNESSO/ERRORE,
data/esito/motivi ultimo test, versione_configurazione_verificata e
versione_contratto_comune_verificata. Il riferimento a SchemaDiscoveryGenerato
non e' prerequisito dell'attivazione; gli esempi non determinano la forma comune.

CONNESSO richiede verifica riuscita dell'intera risposta per URL/revisione
correnti e contratto comune corrente. Il verifier controlla atomicamente
che la configurazione non sia cambiata durante HTTP; un esito superato non
sovrascrive lo stato nuovo. URL modificato -> DEFINITO; test fallito -> ERRORE.
Una modifica ai soli esempi proprietari non disconnette la sorgente target.

### Discovery E Audit Target

La porta viene estesa in T080 per leggere tutti i CatalogoDiscovery della
sorgente; la selezione di uno specifico tipo rimane un'operazione sul risultato
in memoria. Cache per sorgente/configurazione, indice temporaneo dei percorsi,
nessuna tabella catalogo o import automatico delle categorie.
Il resolver include l'integrazione, mai il solo codice tipo documento.

Audit amministrativo esteso per integrazione anche prima che esista un tipo
o modello: creazione, modifica URL/configurazione, verifica e relativa revisione.
Conservare l'audit per tipo esistente senza inventare collegamenti a GEBAN.
Righe legacy non associate non diventano integrazioni operative attraverso
seed/env; l'admin esegue un'associazione esplicita seguita da nuova verifica.

Relazioni target:

```text
Integrazione 1--0..1 EndpointIntegrazione
Integrazione 1--N TipoDocumento (solo configurazioni necessarie ai modelli)
TipoDocumento 1--N ModelloDocumento -> versioni/contratti propri
Integrazione 1--N Audit integrazione
```

**Rilevamento attributi non riconosciuti (2026-09-21, design handoff 5b)**: la
verifica endpoint (User Story 3/FR-008) confronta gli attributi extra
(`NodoDiscovery` ha gia' `extra="allow"`, li accetta ma li ignora a runtime)
contro le `PolicyDimensione` registrate (entita' di `002`, riusata qui) e
segnala quelli privi di policy come controllo distinto dell'esito di verifica
("Attributi non riconosciuti: N"), con link diretto alla schermata di
configurazione della policy (User Story 5). Non e' un meccanismo separato
dall'adapter discovery generico - vive nello stesso punto dove la risposta
viene gia' validata (FR-011).

## Design Reference — schermate (design_handoff_modellario, 2026-09-21)

| id | schermata | rotta | User Story | stato |
| --- | --- | --- | --- | --- |
| 4a | configure-dimensions | `/configurazione/tipi-documento/:codice/dimensioni` | US5 (nuova) | proposta, posizionamento 010 vs 007 ancora aperto nel design stesso |
| 4b | configure-dimensions (stati) | idem | US5 | stati caricamento/errore, non schermata a se' |
| 5a | new-context | `/configurazione/contesti/nuovo` | US1 + US2 | proposta, sostituisce/precisa il flusso testuale esistente |
| 5b | integration-health | `/configurazione/contesti/:ctxId/integrazione` | US3, visualizza anche FR-015 (rinviato) | proposta |

**Vincolo di implementazione (FR-026 di `007`)**: quando una di queste
schermate viene pianificata, l'implementazione MUST seguirne struttura,
organizzazione e stile visivo cosi' come documentati in
`design_handoff_modellario/`, non un layout alternativo. Questo NON si
applica retroattivamente all'editor struttura tipo documento (US1)
implementato il 2026-09-21, prima che 5a esistesse nel design - quel flusso
resta un editor a form senza una schermata dedicata a cui allinearsi.

## Entita' riusate, non ridefinite qui

Riallineamento FR-016 del 2026-09-17: le entita' di classificazione elencate
sotto sono storiche e devono essere rimosse dal runtime/schema head.
`ModelloDocumento` conserva `codice_categoria`, `codice_tipologia` e
`percorso_categorizzazione` (JSON array) al posto delle vecchie FK.
I contratti delle versioni rimangono in `ModelloCampoRichiesto`.
Non si salva l'albero esterno o un registro separato dei suoi campi.
TipoDocumento resta configurazione GEMODO per ownership/abilitazione,
non elenco copiato dal servizio esterno. Il vecchio AdapterLocale viene ritirato;
self-service richiede una nuova sorgente proprietaria canonica, mai un fallback
per un tipo integrato. La vecchia firma locale di T054 resta evidenza storica.

Si riusano `TipoDocumento.codice_contesto` e le entita' proprietarie dei
modelli/versioni della 001/002. La migration 0008 resta storica; il registro
globale e le classificazioni introdotti in precedenza sono eliminati in 0009.
La definizione/esempio per documentazione non e' una replica della risposta
esterna e va progettata come configurazione proprietaria separata.

## Porta Di Discovery (canonica, `DEC-002-PORTS-ADAPTERS-DISCOVERY`)

Questa spec e' dove la porta astratta e l'adapter HTTP vengono effettivamente
progettati e implementati (`backend/app/discovery/`, vedi `plan.md`); la `002`
la consuma senza ridefinirla (vedi nota in
`specs/002-builder-modelli/data-model.md`).

```text
PortaDiscovery.catalogo_discovery(codice_tipo_documento, forza_aggiornamento=False) -> CatalogoDiscovery
```

`CatalogoDiscovery` contiene codice tipo documento, metadati e nodi ricorsivi.
Un nodo contiene codice, descrizione, attributi e alternativamente figli o
campi della foglia. I DTO sono indipendenti da SQLAlchemy e uguali per
qualsiasi implementazione della porta. Il percorso completo dei codici identifica
un ramo; codici duplicati fra fratelli sono errore, fra rami diversi sono ammessi.
Il nome di un livello non determina il parsing. La porta ridotta e la
compatibilita' locale di T054 sono storiche; FR-016 elimina quel percorso.

La porta espone i dati operativi reali del contesto nel momento in cui vengono
richiesti. Lo `SchemaDiscoveryGenerato` documenta e valida la forma comune che
un endpoint integrato deve rispettare, ma non e' la sorgente autoritativa dei
valori restituiti dall'endpoint HTTP. Per un tipo documento integrato, tipologie,
profili, attributi e campi disponibili sono quelli ottenuti dall'API esterna
registrata; il modello GEMODO salva la struttura scelta a partire da quella
risposta.

### AdapterHTTP

Chiama l'endpoint registrato in `EndpointIntegrazione.url` per un tipo
documento integrato.

- Gestisce la paginazione stile HAL/Spring Data REST (`_embedded`/`_links`/
  `page`) in modo trasparente, assemblando il risultato completo prima di
  restituirlo (FR-011).
- Cache **in memoria di processo**, TTL breve (minuti, non ore), mai una
  tabella DB — confermato 2026-09-15, vedi `research.md`. Serve solo a rendere
  fluida la navigazione a livelli nella stessa sessione operatore, non e' mai
  la fonte per il controllo live di compatibilita': `forza_aggiornamento=True`
  esclude la cache. La validazione dei valori rimane contro il contratto
  immutabile del modello; il confronto con il catalogo corrente e' distinto.
- Se il sistema esterno non risponde ed e' scaduta la cache: solleva un errore
  funzionale di connessione. La porta non restituisce mai una lista vuota per
  distinguerla da "nessun dato disponibile" — le due situazioni non devono
  essere confondibili lato chiamante.

## Entities

### DefinizioneStruttura (design US1/US2, 2026-09-17)

Configurazione proprietaria per documentazione, mai risposta scaricata da GEBAN.
Ogni salvataggio crea una revisione: UUID, tipo_documento_id, versione positiva,
contenuto JSON object (tipologie, profili, combinazioni, campi), created_at.
Unicita' tipo/versione. Le revisioni precedenti non vengono sovrascritte;
gli attributi nella tabella AttributoProfilo rappresentano la sola revisione
corrente, mentre il JSON storico conserva la definizione completa originale.
Una definizione puo' essere incompleta; solo una definizione completa puo'
generare lo schema/esempio. Codici univoci, combinazioni e riferimenti attributo
sono validati prima del salvataggio. Il servizio serializza gli aggiornamenti
con lock sul TipoDocumento, senza usare il catalogo esterno.

SchemaDiscoveryGenerato aggiunge definizione_struttura_id (nullable solo per
compatibilita' con la fondazione 0010); le nuove generazioni valorizzano sempre
il riferimento. Il runtime precedente azzera l'abilitazione dell'endpoint
quando cambia la definizione. Questo comportamento e' legacy: nel target ADR
0002 un esempio illustrativo modificato non disconnette l'integrazione; T081
deve rimuovere il collegamento, preservando versioni/schemi/modelli passati.

### AuditEventoConfigurazione (design 2026-09-17)

UUID, tipo_documento_id, tipo_evento, soggetto_id, client_id, payload_minimo JSON,
created_at. Non richiede un modello esistente. Registra revisioni/id/versioni
senza copiare URL, credenziali o il contenuto della definizione nell'audit.
La scrittura audit e' nella stessa transazione della relativa operazione.

### AttributoProfilo *(configurazione d'esempio, FR-003)*

Fondazione implementata dalla migration 0010. Questa tabella conserva solo
attributi dell'esempio/definizione GEMODO; nessun adapter HTTP vi scrive dati
ricevuti da GEBAN. Il repository US1 e' implementato per le revisioni
proprietarie; non e' usato per popolare il catalogo esterno.

Attributo aggiuntivo opzionale su un profilo/categoria, i cui valori ammessi e
default variano per profilo — generalizza il caso "livello" osservato su
`/api/v1/profili` di GEBAN (`livelliPossibili`/`livelloBase`).

Fields:

- `id`
- `tipo_documento_id` e `percorso_profilo`: riferimento nella definizione
  proprietaria/esempio, mai FK a una categoria del catalogo esterno.
- `codice`: identificativo funzionale dell'attributo (es. `livello`).
- `valori_ammessi`: lista di valori ammessi per questo profilo (JSON).
- `valore_default`: opzionale.
- `created_at`
- `updated_at`

Validation:

- chiave logica: `tipo_documento_id + percorso_profilo + codice`.
- `percorso_profilo` e' un array JSON non vuoto; il default, se presente,
  appartiene a `valori_ammessi`. Unicita' e appartenenza sono vincoli DB.
- `valori_ammessi` non vuoto se l'attributo e' referenziato da un campo
  obbligatorio (vedi `ModelloCampoRichiesto.validazione` sotto).

### EndpointIntegrazione Legacy *(migration 0010, superata da ADR 0002)*

Schema presente nelle fondazioni 0010/0011, non target del nuovo onboarding.
Le regole per tipo/schema generato sotto sono storiche e da migrare con T079.

Fields:

- `id`
- `tipo_documento_id`: 1:1 con il tipo documento (un solo endpoint di
  discovery per tipo documento in questo incremento).
- `url`
- `timeout_ms`: 1000..30000, default 5000; configurazione del futuro test HTTP.
- `stato`: `DEFINITO` (registrato, non ancora verificato con successo),
  `CONNESSO` (ultimo test riuscito contro la versione corrente dello schema),
  `ERRORE` (ultimo test fallito).
- `schema_discovery_generato_id_verificato`: quale versione dello schema e'
  stata usata per l'ultimo test riuscito; opzionale.
- `esito_ultimo_test`: messaggio funzionale (es. "attributo obbligatorio X
  mancante", "tipo dato non valido", "connessione rifiutata").
- `data_ultimo_test`
- `created_at`
- `updated_at`

Validation:

- `stato` parte sempre da `DEFINITO` alla registrazione.
- Una FK composita impedisce di associare uno schema verificato a un diverso
  tipo documento. `CONNESSO` richiede schema verificato e data del test.
  La verifica contro la versione corrente e l'approvazione dell'URL sono
  responsabilita' del futuro servizio US3, non della sola migration 0010.
- `stato` diventa `CONNESSO` solo se il test di connessione (FR-008) valida la
  risposta contro la forma comune dello `SchemaDiscoveryGenerato` **corrente** del
  tipo documento. Valori reali diversi dagli esempi restano validi se rispettano
  quella forma.
- se la definizione struttura viene ridefinita dopo che l'endpoint e'
  `CONNESSO` (nuova versione di `SchemaDiscoveryGenerato`), `stato` torna a
  `DEFINITO` finche' non viene rieseguito un test contro la nuova versione —
  un endpoint verificato contro uno schema superato non resta silenziosamente
  "connesso" (coerente con l'edge case di ridefinizione in `spec.md`, che
  protegge i modelli gia' pubblicati ma non esonera l'endpoint dal ri-test).
- un tipo documento resta non utilizzabile per la creazione di modelli finche'
  `stato != CONNESSO` (FR-009), tranne il caso self-service (nessuna riga qui).

### SchemaDiscoveryGenerato *(nuova, FR-006/FR-007)*

Schema/esempio JSON generato dalla definizione struttura (User Story 1),
versionato. E' sia la documentazione consegnata al team esterno sia il
riferimento con cui il test di connessione (FR-008) valida la **forma** della
risposta reale.

Fields:

- `id`
- `tipo_documento_id`
- `versione`: intero, incrementale per tipo documento.
- `contenuto`: il JSON generato (albero di categorizzazione, struttura dei nodi,
  struttura dei campi, tipi dato, attributi profilo-dipendenti, data di validita'
  della forma contrattuale — stessa forma di
  `docs/adr/0001-esempio-discovery-geban.json`). I valori mostrati sono esempi o
  semi iniziali, non l'elenco autoritativo dei valori reali che l'endpoint
  integrato potra' restituire.
- `generato_il`
- `generato_da`: identita' dell'operatore (audit).

Validation:

- `versione` univoca per `tipo_documento_id`, sempre crescente.
- La migration 0010 impone versione positiva e contenuto JSON object;
  incremento monotono e immutabilita' sono responsabilita' del servizio US2.
- generabile solo se la definizione e' completa: almeno una tipologia, un
  profilo, un campo (User Story 1, Acceptance Scenario 3) — altrimenti errore
  che indica cosa manca.
- una nuova generazione non cancella le versioni precedenti (referenziate da
  `EndpointIntegrazione.schema_discovery_generato_id_verificato` per audit di
  "contro quale versione era stato verificato l'endpoint").

### ModelloCampoRichiesto *(riferimento, `001`)* — nota sul campo profilo-dipendente

Quando un campo del contratto dati (FR-005) e' marcato come dipendente da un
`AttributoProfilo` invece che con opzioni fisse, il campo `validazione` (gia'
esistente su `ModelloCampoRichiesto`, `001`) porta un riferimento simbolico
invece di un elenco statico:

```json
{"fonte_opzioni": "profilo.livello", "default": "profilo.livello_base"}
```

Risolto a runtime (in fase di creazione modello, mai in fase di generazione
documento — a quel punto il valore scelto e' gia' nello snapshot dati) contro
`AttributoProfilo` del profilo scelto per quel modello, via
gli attributi del nodo selezionato in `CatalogoDiscovery`.

## Verifica di compatibilita' della versione modello (decisione 2026-09-17)

Metadati associati alla versione modello: percorso esterno dei codici,
versione dell'algoritmo di firma, SHA-256, definizioni delle dipendenze usate
e dei campi obbligatori del ramo alla creazione, data/esito/differenze dell'ultima
verifica. Riutilizzare le definizioni gia' nel contratto del modello; conservare
solo quelle ulteriori necessarie a spiegare il confronto, mai tutto il catalogo.
La collocazione persistente e la migration vanno definite in T055 prima del codice.

La firma ordina chiavi/campi e insiemi di opzioni, include default e vincoli,
esclude `validita` variabile e dettagli descrittivi. La selezione corrente
comprende dipendenze del modello e tutti i campi obbligatori del ramo, per
rilevare anche nuovi obbligatori; campi opzionali non usati sono esclusi.
La scomparsa del percorso o di una dipendenza e' rilevata prima del calcolo.
Una firma diversa avvia un diff; non equivale automaticamente a incompatibilita'.

Esiti distinti dallo stato di pubblicazione: `ALLINEATO`,
`COMPATIBILE_CON_VARIAZIONI`, `DA_AGGIORNARE`, `NON_VERIFICABILE`.
Il controllo conserva data e motivo senza modificare il contenuto pubblicato.
Una verifica fallita non si presenta come una precedente verifica positiva.
Il runner indicizza una risposta per integrazione/ciclo in memoria, evita
esecuzioni sovrapposte e notifica le transizioni di esito. Intervallo e timeout
sono configurabili; definire i valori operativi nei task di progettazione.

Compatibilita' GEBAN iniziale: l'adapter normalizza `livelloBase` in
`livello_base`; se entrambi sono presenti e discordanti segnala errore.
Un attributo profilo non rende implicitamente vincolato un campo senza regola
esplicita: il collegamento del campo `livello` alle opzioni va documentato nel
profilo di integrazione. Nessuna correzione automatica dei codici `*_em`.

## Relationships Legacy (0010/0011, Non Target ADR 0002)

```text
TipoDocumento 1--1 EndpointIntegrazione (0..1, solo se integrato)
TipoDocumento 1--N SchemaDiscoveryGenerato (versioni)
TipoDocumento 1--N AttributoProfilo (scoped al percorso nella definizione proprietaria)
EndpointIntegrazione N--1 SchemaDiscoveryGenerato (schema_discovery_generato_id_verificato, opzionale)
ModelloCampoRichiesto N--1 AttributoProfilo (tramite validazione.fonte_opzioni, risolto per codice non per FK rigida)
```

## State Transitions Legacy - EndpointIntegrazione

```text
(nessuna riga) -> DEFINITO   [registrazione URL, FR-008]
DEFINITO -> CONNESSO          [test di connessione riuscito contro schema corrente]
DEFINITO -> ERRORE            [test di connessione fallito]
ERRORE -> CONNESSO            [nuovo test riuscito]
ERRORE -> ERRORE              [nuovo test ancora fallito, esito aggiornato]
CONNESSO -> DEFINITO          [ridefinizione struttura: nuova versione schema, ri-verifica necessaria]
```

Rules:

- solo `CONNESSO` rende il tipo documento utilizzabile per creare modelli
  (FR-009); questa regola e' enforced dalla porta di discovery, non da un
  controllo duplicato nel builder.
- la sorgente self-service rimane rinviata, non si deduce dalla mancanza di endpoint.
