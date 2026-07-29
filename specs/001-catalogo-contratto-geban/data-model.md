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
- se presente, `codice_tipologia` deve corrispondere a una `TipologiaBandoSOL`
  configurata (FR-020).

### TipologiaBandoSOL

Tipologia di processo GEBAN/SOL, condivisa con il dominio SOL (`DEC-001-TIPOLOGIE-SOL`).

Fields:

- `codice`: identificativo funzionale usato come `codice_tipologia`, ad esempio `TD`.
- `codice_sol`: codice atteso dall'integrazione GEBAN-SOL, ad esempio
  `F:jconon_call_tdet:folder`.
- `descrizione`
- `attiva`
- `created_at`

Validation:

- `codice` obbligatorio e univoco.
- perimetro iniziale: TDPNRR, CD, DIR, TD, CP, RS, CATP, TI, SDIP, MOB (seed demo in
  `infra/local/postgres/seed-demo-catalog.yaml` della `009`); il dominio SOL completo
  puo' estendere l'elenco in seguito senza cambiare il contratto API.

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
- `lingua`: `IT` o `EN`, default `IT` (FR-021, `DEC-001-LINGUA-IT-EN`).
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
- un campo con `lingua = EN` e `obbligatorio = true` e' richiesto in validazione solo
  quando il payload contiene `bando_inglese = true`; altrimenti resta facoltativo
  (FR-021, FR-022). Campi con `lingua = IT` seguono `obbligatorio` senza condizioni.

### ValidazionePayload

Non necessariamente tabella persistente nella feature 001; rappresenta il risultato della
validazione.

Fields:

- `valido`: boolean.
- `errori`: lista di `ErroreValidazione`.
- `modello_versione_id`
- `bando_inglese`: boolean opzionale nel payload, default `false`; quando `true`
  attiva l'obbligatorieta' dei campi con `lingua = EN` (FR-021, FR-022).

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
- `TIPOLOGIA_SOL_NON_VALIDA` (FR-020): `codice_tipologia` non corrisponde a una
  `TipologiaBandoSOL` configurata.
- `CAMPO_INGLESE_MANCANTE` (FR-022): campo con `lingua = EN` obbligatorio assente
  quando `bando_inglese = true`.

Questi codici sono coerenti con `infra/openapi/errors.md` (catalogo errori
trasversale della `009`); eventuali nuovi codici funzionali di questa feature vanno
aggiunti in entrambi i posti.

## Relationships

```text
TipoDocumento 1--N CategoriaDocumento
TipoDocumento 1--N ModelloDocumento
CategoriaDocumento 1--N ModelloDocumento
TipologiaBandoSOL 1--N ModelloDocumento
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
