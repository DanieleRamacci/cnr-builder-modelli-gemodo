# Data Model - Sezioni Placeholder E Versionamento

## Entities

### SezioneModello

Sezione propria di una specifica versione modello.

Fields:

- `id`
- `modello_documento_versione_id`
- `ordine`
- `titolo`: opzionale.
- `obbligatoria`
- `contenuto_strutturato`
- `origine_template_id`: opzionale, valorizzato solo per tracciabilita' della copia.
- `created_at`
- `updated_at`

Validation:

- `ordine` e' univoco per `modello_documento_versione_id`.
- la sezione e' modificabile solo se la versione modello e' in stato modificabile.
- sezioni di versioni modello pubblicate non sono modificabili direttamente.
- la sezione e' sempre presente nel modello; condizioni su payload sono fuori perimetro.

### ModelloDocumentaleControllato

Struttura `GEMODO_DOCUMENT_V1` versionata salvata dal builder visuale controllato.

Fields:

- `id`
- `modello_versione_id`
- `formato`: `GEMODO_DOCUMENT_V1`
- `pagina`
- `regioni`
- `blocchi`: elenco ordinato di blocchi documento consentiti.
- `asset`: elenco asset documentali versionati.
- `stili_ammessi`
- `placeholder_usati`: elenco derivato o salvato dei placeholder presenti.
- `contiene_html_libero`: deve essere `false`.
- `contiene_css_libero`: deve essere `false`.
- `contiene_script`: deve essere `false`.

Validation:

- HTML libero, CSS libero e script non sono ammessi.
- ogni blocco deve usare tipo, posizionamento, stile, asset e placeholder consentiti.
- ogni placeholder del modello deve essere coerente con il contratto dati della versione.

### BloccoDocumento

Elemento controllato della struttura documentale.

Fields:

- `id`
- `tipo`: `LOGO`, `INTESTAZIONE`, `TITOLO`, `PARAGRAFO`, `TABELLA`, `COLONNE`,
  `FIRMA`, `FOOTER`, `INTERRUZIONE_PAGINA`.
- `posizionamento`: `TOP`, `BODY`, `INLINE`, `COLUMN_LEFT`, `COLUMN_RIGHT`,
  `BOTTOM_LEFT`, `BOTTOM_RIGHT`, `BOTTOM_CENTER`.
- `ordine`
- `contenuto`: opzionale.
- `stile`: opzionale, deve appartenere a `stili_ammessi`.
- `asset_ref`: opzionale.
- `colonne`: obbligatorie per `TABELLA` e `COLONNE`.
- `placeholder_usati`

Validation:

- il posizionamento deve essere compatibile con il tipo blocco.
- `TABELLA` deve dichiarare colonne.
- `COLONNE` deve dichiarare almeno due colonne.
- ogni `asset_ref` deve esistere tra gli asset del modello.

### AssetDocumento

Asset referenziabile da blocchi del modello.

Fields:

- `id`
- `tipo`: ad esempio `LOGO` o `IMMAGINE`.
- `nome`
- `versione`
- `storage_ref`
- `hash_file`: opzionale finche' lo storage definitivo non e' implementato.
- `dimensioni_consentite`

Validation:

- gli asset sono referenziati per id/versione/storage/hash, non incorporati come contenuto
  libero.
- un asset non dichiarato non puo' essere usato da un blocco.

### ContenutoStrutturatoSezione

Vista compatibile della sezione dentro il modello documentale controllato.

Fields:

- `blocchi`: elenco ordinato di blocchi consentiti.
- `placeholder_usati`: elenco derivato o salvato dei placeholder presenti.

Block types ammessi:

- `LOGO`
- `INTESTAZIONE`
- `TITOLO`
- `PARAGRAFO`
- `TABELLA`
- `COLONNE`
- `FIRMA`
- `FOOTER`
- `INTERRUZIONE_PAGINA`

Inline marks ammessi:

- `grassetto`
- `corsivo`
- `placeholder`

Validation:

- HTML libero non ammesso.
- CSS libero e script non ammessi.
- formattazioni non previste non ammesse.
- placeholder devono rispettare il formato canonico del progetto.

### TemplateSezione

Template opzionale copiabile dentro una versione modello.

Fields:

- `id`
- `codice`
- `descrizione`
- `contenuto_strutturato`
- `attivo`
- `created_at`
- `updated_at`

Validation:

- quando usato, il contenuto viene copiato in `SezioneModello`.
- modifiche successive al template non aggiornano sezioni gia' copiate.
- il template non e' un riferimento vivo condiviso tra modelli.

### PlaceholderDisponibile

Placeholder associato alla versione modello tramite i campi richiesti definiti nella 002 e
usati dal contratto dati della 001.

Fields:

- `modello_documento_versione_id`
- `codice`
- `obbligatorio`
- `tipo_dato`
- `schema_campo_id`: opzionale per campi complessi.

Validation:

- il contratto dati verso GEBAN deriva da questi campi associati, non dai placeholder nel
  contenuto.

### PlaceholderUsato

Placeholder presente nel contenuto strutturato o in una regola esplicita della versione
modello.

Fields:

- `modello_documento_versione_id`
- `sezione_modello_id`
- `codice`
- `posizione`: opzionale.

Validation:

- ogni placeholder usato deve esistere tra i placeholder disponibili.
- ogni placeholder obbligatorio disponibile deve risultare usato nel contenuto o in una
  regola esplicita del modello.

### CampoComplessoSchema

Schema esplicito per campi complessi.

Fields:

- `id`
- `modello_campo_richiesto_id`
- `tipo`: `object`, `array`, `lista_oggetti`, `tabella`, `sezione_ripetibile`.
- `sotto_campi`
- `created_at`
- `updated_at`

Validation:

- un campo complesso non puo' essere JSON libero generico.
- ogni sotto-campo dichiara codice, tipo, obbligatorieta' e vincoli.
- i valori ricevuti da GEBAN devono rispettare lo schema.

### SottoCampoSchema

Elemento dello schema di un campo complesso.

Fields:

- `codice`
- `etichetta`
- `tipo_dato`: `string`, `number`, `date`, `boolean`, `array`, `object`.
- `obbligatorio`
- `ordine`
- `vincoli`: opzionale.

Validation:

- `codice` univoco nello stesso schema.
- sotto-campi non previsti nel payload sono errore di validazione.

## Relationships

```text
ModelloDocumentoVersione 1--N SezioneModello
TemplateSezione 0--N SezioneModello (solo origine copia)
ModelloDocumentoVersione 1--1 ModelloDocumentaleControllato
ModelloDocumentaleControllato 1--N BloccoDocumento
ModelloDocumentaleControllato 0--N AssetDocumento
ModelloDocumentoVersione 1--N PlaceholderDisponibile
SezioneModello 1--N PlaceholderUsato
ModelloCampoRichiesto 0--1 CampoComplessoSchema
CampoComplessoSchema 1--N SottoCampoSchema
```

## State Rules

- Le sezioni sono modificabili solo se la versione modello e' modificabile.
- La pubblicazione della versione modello richiede validazione di coerenza sezioni,
  placeholder e campi complessi.
- Pubblicare una versione modello rende immutabile il contenuto delle sue sezioni.
- Creare una nuova versione modello da una precedente copia anche le sezioni.
- Aggiornare un template sezione non modifica le sezioni gia' copiate.
- Sezioni condizionali basate su payload sono fuori perimetro corrente.
- Il renderer PDF della `004` puo' trasformare internamente `GEMODO_DOCUMENT_V1`, ma il
  builder non salva HTML/CSS/script libero.
