# Data Model - Builder Modelli Documentali

## Entities

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

## Relationships

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
