# Data Model - Configurazione Cataloghi E Integrazioni

## Entita' riusate, non ridefinite qui

`TipoDocumento` (incluso il campo diretto `codice_contesto`,
`DEC-001-CONTESTO-SOSTITUISCE-UFFICIO`, 2026-09-15 — nessuna entita' `Ufficio`),
`CategoriaDocumento` (profilo), `TipologiaBandoSOL` (tipologia),
`RegistroContrattiDati` sono di proprieta' della `001`
(`specs/001-catalogo-contratto-geban/data-model.md`). Questa spec aggiunge
l'interfaccia con cui un operatore le *crea/definisce* e tre entita' nuove che
non hanno posto naturale altrove. `codice_contesto` e `RegistroContrattiDati`
sono progettati in `001` ma non ancora implementati in codice (`001/tasks.md`
T085, T087): l'implementazione di questa spec crea quelle migration se `001`
non le ha ancora create, riusando lo schema gia' deciso li' senza
riprogettarlo.

## Porta Di Discovery (canonica, `DEC-002-PORTS-ADAPTERS-DISCOVERY`)

Questa spec e' dove la porta astratta e i due adapter vengono effettivamente
progettati e implementati (`backend/app/discovery/`, vedi `plan.md`); la `002`
la consuma senza ridefinirla (vedi nota in
`specs/002-builder-modelli/data-model.md`).

```text
PortaDiscovery.tipologie_disponibili(codice_tipo_documento) -> list[TipologiaDisponibile]
PortaDiscovery.profili_disponibili(codice_tipo_documento, codice_tipologia) -> list[ProfiloDisponibile]
PortaDiscovery.attributi_profilo(codice_tipo_documento, codice_profilo) -> list[AttributoDisponibile]
PortaDiscovery.campi_disponibili(codice_tipo_documento) -> list[CampoDisponibile]
```

I quattro DTO di ritorno (`TipologiaDisponibile`, `ProfiloDisponibile`,
`AttributoDisponibile`, `CampoDisponibile`) sono strutture leggere,
indipendenti da SQLAlchemy: stessa forma sia che arrivino da
`AdapterLocale` (letti da `CategoriaDocumento`/`TipologiaBandoSOL`/
`RegistroContrattiDati` locali) sia da `AdapterHTTP` (deserializzati dalla
risposta esterna). Il chiamante (builder `002`, o la definizione struttura di
questa spec) non distingue mai i due casi.

### AdapterLocale

Legge direttamente le tabelle `001` per un tipo documento self-service.
Nessuna cache: sono gia' dati locali.

### AdapterHTTP

Chiama l'endpoint registrato in `EndpointIntegrazione.url` per un tipo
documento integrato.

- Gestisce la paginazione stile HAL/Spring Data REST (`_embedded`/`_links`/
  `page`) in modo trasparente, assemblando il risultato completo prima di
  restituirlo (FR-011).
- Cache **in memoria di processo**, TTL breve (minuti, non ore), mai una
  tabella DB — confermato 2026-09-15, vedi `research.md`. Serve solo a rendere
  fluida la navigazione a livelli nella stessa sessione operatore, non e' mai
  la fonte per validazione o generazione documento (quelle leggono sempre
  `ModelloCampoRichiesto`, dati di `001` gia' snapshottati alla creazione del
  modello).
- Se il sistema esterno non risponde ed e' scaduta la cache: solleva un errore
  funzionale di connessione. La porta non restituisce mai una lista vuota per
  distinguerla da "nessun dato disponibile" — le due situazioni non devono
  essere confondibili lato chiamante.

## Entities

### AttributoProfilo *(nuova, FR-003)*

Attributo aggiuntivo opzionale su un profilo/categoria, i cui valori ammessi e
default variano per profilo — generalizza il caso "livello" osservato su
`/api/v1/profili` di GEBAN (`livelliPossibili`/`livelloBase`).

Fields:

- `id`
- `categoria_documento_id`: riferimento al profilo/categoria (`001`) a cui
  questo attributo appartiene.
- `codice`: identificativo funzionale dell'attributo (es. `livello`).
- `valori_ammessi`: lista di valori ammessi per questo profilo (JSON).
- `valore_default`: opzionale.
- `created_at`
- `updated_at`

Validation:

- chiave logica: `categoria_documento_id + codice`.
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
- `stato`: `DEFINITO` (registrato, non ancora verificato con successo),
  `CONNESSO` (ultimo test riuscito contro la versione corrente dello schema),
  `ERRORE` (ultimo test fallito).
- `schema_discovery_generato_id_verificato`: quale versione dello schema e'
  stata usata per l'ultimo test riuscito; opzionale.
- `esito_ultimo_test`: messaggio funzionale (es. "campo X non previsto dalla
  risposta", "connessione rifiutata").
- `data_ultimo_test`
- `created_at`
- `updated_at`

Validation:

- `stato` parte sempre da `DEFINITO` alla registrazione.
- `stato` diventa `CONNESSO` solo se il test di connessione (FR-008) valida la
  risposta contro lo `SchemaDiscoveryGenerato` **corrente** del tipo
  documento.
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
riferimento con cui il test di connessione (FR-008) valida la risposta reale.

Fields:

- `id`
- `tipo_documento_id`
- `versione`: intero, incrementale per tipo documento.
- `contenuto`: il JSON generato (tipo documento, tipologie, profili, campi,
  attributi profilo-dipendenti, data di validita' — stessa forma di
  `docs/adr/0001-esempio-discovery-geban.json`).
- `generato_il`
- `generato_da`: identita' dell'operatore (audit).

Validation:

- `versione` univoca per `tipo_documento_id`, sempre crescente.
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
`PortaDiscovery.attributi_profilo`.

## Relationships

```text
TipoDocumento 1--1 EndpointIntegrazione (0..1, solo se integrato)
TipoDocumento 1--N SchemaDiscoveryGenerato (versioni)
CategoriaDocumento 1--N AttributoProfilo
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
