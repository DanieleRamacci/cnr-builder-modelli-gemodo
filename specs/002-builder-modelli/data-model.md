# Data Model - Builder Modelli Documentali

## Entities

### TipoDocumento

Famiglia generale del documento.

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

Classificazione interna collegata a un tipo documento.

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

Contenitore logico di una variante documentale.

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

### ModelloDocumentoVersione

Configurazione versionata del modello.

Fields:

- `id`: identificativo tecnico, usato come `modello_versione_id`.
- `modello_documento_id`
- `numero_versione`
- `stato`: `BOZZA`, `IN_REVISIONE`, `APPROVATO`, `PUBBLICATO`, `ARCHIVIATO`, `SOSPESO`.
- `data_inizio_validita`: opzionale.
- `data_fine_validita`: opzionale.
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

### ModelloCampoRichiesto

Campo dinamico richiesto da una versione modello.

Fields:

- `id`
- `modello_documento_versione_id`
- `codice`
- `etichetta`
- `descrizione`
- `tipo_dato`: `string`, `number`, `date`, `boolean`, `array`, `object`.
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

### AuditEventoModello

Evento funzionale da registrare per cambiamenti del builder.

Fields:

- `id`
- `tipo_evento`: `MODELLO_CREATO`, `VERSIONE_CREATA`, `VERSIONE_MODIFICATA`,
  `VERSIONE_APPROVATA`, `VERSIONE_PUBBLICATA`, `VERSIONE_ARCHIVIATA`,
  `VERSIONE_SOSPESA`.
- `soggetto_id`
- `modello_documento_id`
- `modello_documento_versione_id`: opzionale.
- `payload_minimo`
- `created_at`

Validation:

- ogni transizione di stato deve generare un evento audit.
- l'audit non sostituisce il dettaglio sicurezza della spec 006.

## Relationships

```text
TipoDocumento 1--N CategoriaDocumento
TipoDocumento 1--N ModelloDocumento
CategoriaDocumento 1--N ModelloDocumento
ModelloDocumento 1--N ModelloDocumentoVersione
ModelloDocumentoVersione 1--N ModelloCampoRichiesto
ModelloDocumentoVersione 0--1 ModelloDocumentoVersione (derivata_da_versione_id)
ModelloDocumentoVersione 1--N AuditEventoModello
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
