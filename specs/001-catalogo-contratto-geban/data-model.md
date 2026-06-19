# Data Model - Catalogo Modelli E Contratto Dati GEBAN

## Entities

### TipoDocumento

Rappresenta una famiglia documentale generale.

Fields:

- `codice`: identificativo funzionale, univoco.
- `descrizione`: testo descrittivo.
- `attivo`: indica se il tipo e' usabile per configurazioni operative.
- `created_at`
- `updated_at`

Validation:

- `codice` obbligatorio e univoco.
- tipi non attivi non vengono proposti come nuovi elementi operativi.

### CategoriaDocumento

Classificazione interna collegata a un tipo documento.

Fields:

- `codice_tipo_documento`: riferimento a `TipoDocumento`.
- `codice`: identificativo categoria.
- `descrizione`
- `attiva`
- `created_at`
- `updated_at`

Validation:

- chiave logica: `codice_tipo_documento + codice`.
- categorie non attive non vengono proposte per nuovi filtri operativi.

### ModelloDocumento

Contenitore logico di un modello.

Fields:

- `id`
- `codice`: identificativo funzionale del modello.
- `descrizione`
- `codice_tipo_documento`
- `codice_categoria`
- `codice_tipologia`: opzionale, dipende dal processo GEBAN.
- `variante`: etichetta funzionale obbligatoria; default `STANDARD`.
- `attivo`
- `created_at`
- `updated_at`

Validation:

- il modello deve riferire tipo e categoria esistenti.
- `variante` non puo' essere vuota; se manca viene assegnata `STANDARD`.
- la combinazione `codice_tipo_documento + codice_categoria + codice_tipologia + variante`
  identifica una variante funzionale nel catalogo.

### ModelloDocumentoVersione

Versione specifica selezionabile da GEBAN.

Fields:

- `id`: `modello_versione_id` usato da GEBAN.
- `modello_documento_id`
- `numero_versione`
- `stato`: `BOZZA`, `IN_REVISIONE`, `APPROVATO`, `PUBBLICATO`, `ARCHIVIATO`, `SOSPESO`.
- `data_inizio_validita`: opzionale.
- `data_fine_validita`: opzionale.
- `pubblicato_at`: obbligatorio quando lo stato diventa `PUBBLICATO`.
- `created_at`
- `updated_at`

Validation:

- solo `PUBBLICATO` e' utilizzabile in modalita' operativa.
- per la stessa combinazione di tipo documento, categoria, tipologia e variante puo'
  esistere al massimo una versione `PUBBLICATO`.
- quando una nuova versione della stessa variante diventa `PUBBLICATO`, la precedente
  versione `PUBBLICATO` passa ad `ARCHIVIATO`.
- piu' varianti pubblicate possono essere visibili nello stesso contesto; la scelta
  operativa usa sempre `modello_versione_id`.
- una versione non piu' `PUBBLICATO` non e' validabile per uso operativo.
- le modifiche contenutistiche a una versione pubblicata creano una bozza derivata e non
  aggiornano direttamente la versione pubblicata.

### ModelloCampoRichiesto

Campo dichiarato nel contratto dati di una versione modello.

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
- `opzioni`: opzionale, struttura per valori ammessi o metadati.
- `validazione`: opzionale, vincoli dichiarativi.
- `created_at`
- `updated_at`

Validation:

- chiave logica: `modello_documento_versione_id + codice`.
- `ordine` univoco per versione modello.
- campi extra nel payload sono errore.

### ValidazionePayload

Non necessariamente tabella persistente nella feature 001; rappresenta il risultato della
validazione.

Fields:

- `valido`: boolean.
- `errori`: lista di `ErroreValidazione`.
- `modello_versione_id`

### ErroreValidazione

Errore funzionale restituito a GEBAN.

Fields:

- `campo`: opzionale per errori di richiesta generale.
- `codice`: codice errore stabile.
- `messaggio`: messaggio funzionale.

Common error codes:

- `CAMPO_OBBLIGATORIO`
- `TIPO_NON_VALIDO`
- `CAMPO_NON_AMMESSO`
- `MODELLO_VERSIONE_NON_PUBBLICATO`
- `MODELLO_VERSIONE_NON_TROVATO`
- `CONTESTO_NON_VALIDO`

## Relationships

```text
TipoDocumento 1--N CategoriaDocumento
TipoDocumento 1--N ModelloDocumento
CategoriaDocumento 1--N ModelloDocumento
ModelloDocumento 1--N ModelloDocumentoVersione
ModelloDocumentoVersione 1--N ModelloCampoRichiesto
ModelloDocumentoVersione 1--N ValidazionePayload (runtime)
ValidazionePayload 1--N ErroreValidazione
```

## State Rules

- `BOZZA`, `IN_REVISIONE`, `APPROVATO`, `ARCHIVIATO`, `SOSPESO` non sono operative per GEBAN.
- `PUBBLICATO` e' l'unico stato operativo.
- Il contratto dati e la validazione richiedono sempre `modello_versione_id`.
- Il servizio non sceglie automaticamente l'ultima versione pubblicata.
- Il catalogo operativo espone al massimo una versione `PUBBLICATO` per variante.
- Le versioni precedenti della stessa variante sono `ARCHIVIATO` e disponibili solo nello
  storico.
- Il catalogo puo' esporre piu' varianti pubblicate per lo stesso tipo/categoria/tipologia.
