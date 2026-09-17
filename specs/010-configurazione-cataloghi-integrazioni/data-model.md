# Data Model - Configurazione Cataloghi E Integrazioni

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

### AttributoProfilo *(nuova, FR-003)*

Fondazione implementata dalla migration 0010. Questa tabella conserva solo
attributi dell'esempio/definizione GEMODO; nessun adapter HTTP vi scrive dati
ricevuti da GEBAN. Il repository US1 resta sospeso finche' il design della
definizione proprietaria completa non e' riallineato.

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

### EndpointIntegrazione *(nuova, FR-008/FR-009)*

Endpoint di discovery registrato per un tipo documento integrato. Assente per
un tipo documento self-service (FR-010).

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

## Relationships

```text
TipoDocumento 1--1 EndpointIntegrazione (0..1, solo se integrato)
TipoDocumento 1--N SchemaDiscoveryGenerato (versioni)
TipoDocumento 1--N AttributoProfilo (scoped al percorso nella definizione proprietaria)
EndpointIntegrazione N--1 SchemaDiscoveryGenerato (schema_discovery_generato_id_verificato, opzionale)
ModelloCampoRichiesto N--1 AttributoProfilo (tramite validazione.fonte_opzioni, risolto per codice non per FK rigida)
```

## State Transitions - EndpointIntegrazione

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
- un tipo documento self-service e' sempre utilizzabile subito dopo User
  Story 1 (SC-003), non entra mai in questo stato-macchina.
