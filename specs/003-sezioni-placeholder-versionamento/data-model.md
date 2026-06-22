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

### ContenutoStrutturatoSezione

Rappresentazione controllata del testo della sezione.

Fields:

- `blocchi`: elenco ordinato di blocchi consentiti.
- `placeholder_usati`: elenco derivato o salvato dei placeholder presenti.

Block types ammessi:

- `paragrafo`
- `titolo`
- `lista`
- `tabella_semplice`

Inline marks ammessi:

- `grassetto`
- `corsivo`
- `placeholder`

Validation:

- HTML libero non ammesso.
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
