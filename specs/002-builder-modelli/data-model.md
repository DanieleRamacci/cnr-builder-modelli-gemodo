# Data Model - Builder Modelli Documentali

## Nota Di Riallineamento (2026-09-15, Cascading ADR 0001)

Aggiornamento vincolante 2026-09-17 (`010` FR-016): categorie, tipologie,
classificazione e registro globale legacy sono dismessi, non piu' entita'
locali riusabili. Le sezioni storiche sotto non autorizzano a reintrodurli.
`ModelloDocumento` conserva codici e `percorso_categorizzazione`, senza FK
al catalogo esterno; versioni, struttura documentale, campi e audit sono
GEMODO-owned e restano persistenti. Fonte canonica: data-model della 010.

Il testo che segue fino alla porta di discovery e' una nota storica superata
da FR-016: non descrive entita' riusabili o adapter locali correnti.

`TipoDocumento`, `CategoriaDocumento`, `TipologiaDocumento` e
`RegistroContrattiDati` sono definite per intero in
`specs/001-catalogo-contratto-geban/data-model.md` (che possiede queste entita';
questo documento le riusa, non le ridefinisce). Le sezioni sotto sono state
scritte prima della `DEC-001-CONTESTO-SOSTITUISCE-UFFICIO`/`DEC-001-OWNERSHIP-
DATI-ESTERNI` e restano come riferimento storico delle chiavi/validazioni
condivise, ma per la semantica aggiornata (chi possiede cosa, cache vs seed per
un tipo documento integrato) fa fede `001`. In particolare, per il builder:

- Una scrittura (creare/modificare categoria, tipologia, modello) e' autorizzata
  solo se il token del gestore chiamante contiene il `codice_contesto` del tipo
  documento target, con un ruolo che in quel contesto deriva
  `GEMODO_MODELLI_GESTORE` (FR-014, `002`; `DEC-001-CONTESTO-SOSTITUISCE-UFFICIO`
  — nessuna entita' `Ufficio`, verifica scoped al singolo contesto, mai sulla
  lista di permessi appiattita su tutti i contesti del token).
- Il builder non legge mai direttamente `CategoriaDocumento`/`TipologiaDocumento`/
  `RegistroContrattiDati` come se fossero sempre dati locali: passa sempre dalla
  **porta di discovery** descritta sotto, che puo' risolversi in una lettura
  locale (self-service) o in una cache sincronizzata da un adapter HTTP esterno
  (tipo documento integrato, es. GEBAN) — vedi `DEC-002-PORTS-ADAPTERS-DISCOVERY`.

### Porta Di Discovery (Ports & Adapters, `DEC-002-PORTS-ADAPTERS-DISCOVERY`)

Interfaccia astratta che il builder usa per sapere cosa e' disponibile per un tipo
documento, indipendentemente da dove arrivano i dati. Progettata e implementata
nel modulo `backend/app/discovery/` dalla
`specs/010-configurazione-cataloghi-integrazioni/data-model.md`, che e' la fonte
canonica della firma esatta — qui solo un riferimento per il builder, non
ridefinirla se cambia li'.

```text
PortaDiscovery.catalogo_discovery(codice_tipo_documento, forza_aggiornamento=False) -> CatalogoDiscovery
CatalogoDiscovery.indice_percorsi() -> dict[tuple[str, ...], NodoDiscovery]
```

Implementazione integrata corrente; self-service resta da progettare secondo
la 010, non viene simulato col vecchio catalogo:
- **AdapterHTTP**: chiama l'endpoint di discovery registrato per il tipo
  documento (tipo documento integrato, es. GEBAN), con cache **in memoria di
  processo** a TTL breve (mai una tabella DB — deciso 2026-09-15, vedi
  `specs/010-configurazione-cataloghi-integrazioni/research.md`); gestisce la
  paginazione in modo trasparente al chiamante (FR-011). Se il sistema esterno
  e' irraggiungibile oltre la finestra di cache, il builder riceve un errore
  funzionale di connessione, mai un elenco vuoto silenzioso.

Il builder dipende dalla porta astratta. Nel runtime corrente l'URL e'
configurato operativamente tramite `GEMODO_DISCOVERY_ENDPOINTS`; onboarding
amministrativo e selezione per stato sono ancora task aperti nella 010.

## Entities (Archivio Storico, Non Schema Runtime)

Le entita', validazioni e relazioni seguenti documentano il progetto precedente.
Per lo schema corrente fa fede il data-model della 010: nessuna CategoriaDocumento
o TipologiaBandoSOL persistente, nessuna FK verso tali entita'. I riferimenti del
modello sono codici e `percorso_categorizzazione`, verificati sulla discovery HTTP.

### TipoDocumento

Famiglia generale del documento, condivisa con il catalogo della `001`.

Fields:

- `codice`: identificativo funzionale univoco.
- `descrizione`
- `attivo`
- `created_at`
- `updated_at`

Validation:

- `codice` obbligatorio e univoco.
- un tipo non attivo non puo' essere usato per nuovi modelli operativi.

### CategoriaDocumento

Classificazione interna collegata a un tipo documento, condivisa con il catalogo della
`001`.

Fields:

- `codice_tipo_documento`
- `codice`
- `descrizione`
- `attiva`
- `created_at`
- `updated_at`

Validation:

- chiave logica: `codice_tipo_documento + codice`.
- una categoria non attiva non puo' essere usata per nuovi modelli operativi.

### ModelloDocumento

Contenitore logico di una variante documentale, condiviso con il catalogo della `001`.

Fields:

- `id`
- `codice`: identificativo funzionale.
- `descrizione`
- `codice_tipo_documento`
- `codice_categoria`
- `codice_tipologia`: opzionale.
- `variante`: obbligatoria; default `STANDARD`.
- `attivo`
- `created_at`
- `updated_at`

Validation:

- deve riferire tipo e categoria esistenti.
- `variante` non puo' essere vuota; se manca viene assegnata `STANDARD`.
- la combinazione `codice_tipo_documento + codice_categoria + codice_tipologia + variante`
  identifica una variante funzionale.
- due varianti con la stessa etichetta non possono coesistere nello stesso contesto.
- se presente, `codice_tipologia` deve riferire una `TipologiaBandoSOL` configurata.

### TipologiaBandoSOL

Tipologia di processo GEBAN/SOL condivisa con la `001`.

Fields:

- `codice`
- `codice_sol`
- `descrizione`
- `attiva`
- `created_at`

Validation:

- `codice` obbligatorio e univoco.
- l'elenco iniziale e' quello confermato nella `001`: TDPNRR, CD, DIR, TD, CP, RS,
  CATP, TI, SDIP, MOB.

### ModelloDocumentoVersione

Configurazione versionata del modello.

Fields:

- `id`: identificativo tecnico, usato come `modello_versione_id`.
- `modello_documento_id`
- `numero_versione`
- `stato`: `BOZZA`, `IN_REVISIONE`, `APPROVATO`, `PUBBLICATO`, `ARCHIVIATO`, `SOSPESO`.
- `data_inizio_validita`: opzionale.
- `data_fine_validita`: opzionale.
- `pubblicato_at`: valorizzato quando lo stato diventa `PUBBLICATO`.
- `derivata_da_versione_id`: opzionale, valorizzata quando nasce da versione pubblicata.
- `motivo_versione`: opzionale.
- `creato_da`
- `approvato_da`
- `pubblicato_da`
- `archiviato_da`
- `created_at`
- `updated_at`

Validation:

- `numero_versione` e' univoco per `modello_documento_id`.
- una versione `PUBBLICATO` non puo' essere modificata nel contenuto.
- modifiche a una versione `PUBBLICATO` creano una nuova versione `BOZZA` derivata.
- per la stessa combinazione tipo/categoria/tipologia/variante puo' esistere al massimo
  una versione `PUBBLICATO` corrente.
- pubblicare una nuova versione archivia automaticamente la precedente `PUBBLICATO` della
  stessa variante.
- `BOZZA`, `IN_REVISIONE`, `APPROVATO`, `ARCHIVIATO` e `SOSPESO` non sono visibili nel
  catalogo operativo.
- la transizione a `APPROVATO` e poi `PUBBLICATO` puo' essere eseguita da
  `GEMODO_MODELLI_GESTORE` nel primo rilascio.

### ModelloCampoRichiesto

Campo dinamico richiesto da una versione modello.

Fields:

- `id`
- `modello_documento_versione_id`
- `codice`
- `etichetta`
- `descrizione`
- `tipo_dato`: `string`, `number`, `date`, `boolean`, `array`, `object`.
- `lingua`: `IT` o `EN`, default `IT`.
- `obbligatorio`
- `ordine`
- `formato`: opzionale.
- `valore_default`: opzionale.
- `opzioni`: opzionale.
- `validazione`: opzionale.
- `created_at`
- `updated_at`

Validation:

- chiave logica: `modello_documento_versione_id + codice`.
- `ordine` univoco per versione modello.
- campi richiesti sono modificabili solo quando la versione e' in stato modificabile.
- campi complessi usano schema JSON strutturato con sotto-campi, tipi, obbligatorieta',
  ordine e vincoli per array/object, in coerenza con la `001`.

### AuditEventoModello

Evento funzionale da registrare per cambiamenti del builder.

Fields:

- `id`
- `tipo_evento`: `MODELLO_CREATO`, `VERSIONE_CREATA`, `VERSIONE_MODIFICATA`,
  `VERSIONE_APPROVATA`, `VERSIONE_PUBBLICATA`, `VERSIONE_ARCHIVIATA`,
  `VERSIONE_SOSPESA`.
- `soggetto_id`
- `client_id`
- `ruoli`
- `modello_documento_id`
- `modello_documento_versione_id`: opzionale.
- `payload_minimo`
- `created_at`

Validation:

- ogni transizione di stato deve generare un evento audit.
- l'audit deve usare l'identita' ricostruita dal JWT Keycloak.

### PrincipalGEMODOBuilder

Identita' applicativa ricostruita dal JWT Keycloak per proteggere le API builder.

Fields:

- `subject`
- `client_id`
- `audience`
- `issuer`
- `ruoli`

Validation:

- token con firma valida tramite JWKS, issuer atteso, audience `gemodo-backend` e
  scadenza non superata.
- letture builder consentite a `GEMODO_MODELLI_VIEWER` o `GEMODO_MODELLI_GESTORE`.
- scritture e transizioni consentite solo a `GEMODO_MODELLI_GESTORE`.

## Relationships (Archivio Storico, Superato Da FR-016)

```text
TipoDocumento 1--N CategoriaDocumento
TipoDocumento 1--N ModelloDocumento
CategoriaDocumento 1--N ModelloDocumento
TipologiaBandoSOL 1--N ModelloDocumento
ModelloDocumento 1--N ModelloDocumentoVersione
ModelloDocumentoVersione 1--N ModelloCampoRichiesto
ModelloDocumentoVersione 0--1 ModelloDocumentoVersione (derivata_da_versione_id)
ModelloDocumentoVersione 1--N AuditEventoModello
PrincipalGEMODOBuilder 1--N Operazione API builder (runtime)
```

## State Transitions

```text
BOZZA -> IN_REVISIONE
IN_REVISIONE -> BOZZA
IN_REVISIONE -> APPROVATO
APPROVATO -> PUBBLICATO
PUBBLICATO -> ARCHIVIATO
PUBBLICATO -> SOSPESO
SOSPESO -> ARCHIVIATO
```

Rules:

- solo `BOZZA` e versioni tornate a `BOZZA` sono modificabili nel contenuto.
- `APPROVATO` non e' operativo per GEBAN.
- `PUBBLICATO` e' operativo solo se e' la versione corrente della variante.
- pubblicazione e archiviazione automatica della precedente corrente devono essere
  atomiche.
- versioni gia' usate da generazioni storiche non vengono cancellate.
- tutte le transizioni via API builder richiedono `PrincipalGEMODOBuilder` autorizzato.
