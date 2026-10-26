# Data Model: Campi ripetibili e bando multiplo

**Fase 1 di** `specs/014-articolazioni-bando/plan.md` | **Data**: 2026-10-26

Le decisioni sono motivate in [research.md](./research.md). Qui la forma.

## 1. Contratto discovery 0.8.0 (in memoria, non persistito)

### CampoDiscovery (esteso)

| Chiave | Tipo | Obbl. | Regole |
|---|---|---|---|
| `codice` | string | si' | non vuoto; unico fra i campi della foglia |
| `etichetta` | string | si' | |
| `tipo` | `string`/`number`/`date`/`boolean`/`array`/`object` | si' | |
| `obbligatorio` | boolean | si' | |
| `ordine` | intero >= 1 | si' | |
| `descrizione` | string | no | |
| `lingua` | `IT`/`EN` | no | invariato dalla 0.7.0 |
| `validazione` | oggetto | no | invariato |
| `campi` | lista di SottoCampoDiscovery | no | **nuovo**; solo con `tipo: "array"`; non vuota; codici unici |
| `_<qualsiasi>` | qualsiasi | no | annotazione, ignorata |
| altre chiavi | | | **non conforme** (FR-004) |

### SottoCampoDiscovery (nuovo)

Come CampoDiscovery, con due differenze: `tipo` solo `string`, `number`,
`date`, `boolean`; nessuna chiave `campi`.

Errori (esito `NON_CONFORME`, con percorso): `campi` su tipo diverso da
`array`; `campi` vuota; sotto-campo `array`/`object`; codici duplicati in
`campi`; chiave sconosciuta.

## 2. Persistenza (migrazione 0031)

### modello_documento

| Colonna | Tipo | Note |
|---|---|---|
| `multiplo` | boolean not null default false | **nuova**. Fissata alla creazione, non modificabile. Ereditata da varianti ed edizioni derivate. |

Indici di slot ricostruiti:

- `uq_modello_slot_variante`: `(tipo_documento_id, percorso_categorizzazione, dimensioni, multiplo, variante)` dove `stato <> 'ELIMINATO'`
- `uq_modello_slot_nota`: `(tipo_documento_id, percorso_categorizzazione, dimensioni, multiplo, nota)` dove `stato <> 'ELIMINATO' AND nota IS NOT NULL`

Identita' generata: codice con parte `MULTIPLO`, nome con "(bando multiplo)",
solo per i modelli multipli.

### campo_modello

| Colonna | Tipo | Note |
|---|---|---|
| `sotto_campi` | JSONB nullable | **nuova**. Lista ordinata di `{codice, etichetta, tipo, obbligatorio, ordine, descrizione?, validazione?}`. Valorizzata solo per i campi ripetibili. Copiata da `clona_campi`. |

Regole sulla versione:

| Modello | Campi ripetibili della foglia | `obbligatorio` del campo ripetibile |
|---|---|---|
| singolo | **esclusi** (richiesta che li include: `CAMPO_NON_AMMESSO`) | n/a |
| multiplo | **tutti inclusi** (richiesta che ne omette uno: `CAMPO_NON_AMMESSO`) | sempre `true` (FR-016c) |

## 3. Formato documentale `GEMODO_DOCUMENT_V1` (esteso, additivo)

### BloccoDocumento di tipo TABELLA

| Chiave | Tipo | Note |
|---|---|---|
| `colonne` | list[string] | intestazione; testo semplice; almeno una (regola esistente) |
| `righe` | list[RigaTabella] | **nuova**, default vuota. Vuota = forma attuale, resa come oggi |

### RigaTabella (nuova)

| Chiave | Tipo | Note |
|---|---|---|
| `celle` | list[CellaTabella] | tante quante `colonne` |
| `ripeti_per` | string \| null | codice di un campo ripetibile della versione; null = riga fissa |

### CellaTabella (nuova)

| Chiave | Tipo | Note |
|---|---|---|
| `frammenti` | list[FrammentoTesto] | stesse regole dei frammenti (niente markup, collegamenti ammessi) |

`placeholder_usati` del blocco include i segnaposti delle celle.

### Regole di struttura (blocco della pubblicazione)

| Regola | Errore | Requisito |
|---|---|---|
| numero di celle diverso dal numero di colonne | `MODELLO_DOCUMENTALE_NON_VALIDO` | R6 |
| `ripeti_per` che non e' un campo ripetibile della versione | `PLACEHOLDER_NON_VALIDO` | FR-016 |
| segnaposto di elemento fuori da una riga ripetuta sul suo campo | `PLACEHOLDER_NON_VALIDO` | FR-016b |
| segnaposto principale dentro una riga ripetuta | `PLACEHOLDER_NON_VALIDO` | FR-016b |
| `{{<campo ripetibile>}}` da solo, ovunque | `PLACEHOLDER_NON_VALIDO` | FR-015 |
| modello multiplo senza riga ripetuta per un suo campo ripetibile | `PLACEHOLDER_NON_VALIDO` | FR-009d |
| due righe ripetute sullo stesso campo nella stessa tabella | `PLACEHOLDER_NON_VALIDO` | FR-016h |
| modello singolo con `ripeti_per` | `PLACEHOLDER_NON_VALIDO` | FR-009b |

Avvisi non bloccanti, calcolati dal builder (FR-016h): righe ripetute sullo
stesso campo in piu' tabelle; stesso segnaposto due volte nella stessa riga.

### Segnaposti

| Forma | Dove | Valore in generazione |
|---|---|---|
| `{{codice}}` | fuori dalle righe ripetute | `dati.codice` (regola attuale) |
| `{{<campo>.codice}}` | riga ripetuta su `<campo>` | `codice` dell'elemento |
| `{{<campo>.descrizione}}` | riga ripetuta su `<campo>` | `descrizione` dell'elemento |
| `{{<campo>.campi.<sotto>}}` | riga ripetuta su `<campo>` | valore del sotto-campo; assente -> cella vuota |

## 4. Dati di validazione e generazione

### Elemento di un campo ripetibile

```
{ "codice": string non vuota, unica nella lista,
  "descrizione": string non vuota,
  "campi": { <codice sotto-campo>: valore } }
```

### Errori

| Caso | `campo` | `codice` |
|---|---|---|
| valore non lista | `articolazioni` | `TIPO_NON_VALIDO` |
| lista vuota o assente (multiplo) | `articolazioni` | `CAMPO_OBBLIGATORIO` |
| elemento non oggetto | `articolazioni[0]` | `TIPO_NON_VALIDO` |
| elemento senza codice | `articolazioni[0].codice` | `CAMPO_OBBLIGATORIO` |
| chiave extra nell'elemento senza codice | `articolazioni[0].<chiave>` | `CAMPO_NON_AMMESSO` |
| descrizione mancante | `articolazioni[TEMA_A].descrizione` | `CAMPO_OBBLIGATORIO` |
| codice ripetuto | `articolazioni` | `CODICE_ELEMENTO_DUPLICATO` (**nuovo**) |
| chiave extra nell'elemento | `articolazioni[TEMA_A].<chiave>` | `CAMPO_NON_AMMESSO` |
| sotto-campo obbligatorio mancante | `articolazioni[TEMA_A].campi.numero_posti` | `CAMPO_OBBLIGATORIO` |
| sotto-campo del tipo sbagliato | `articolazioni[TEMA_A].campi.numero_posti` | `TIPO_NON_VALIDO` |
| sotto-campo non dichiarato | `articolazioni[TEMA_A].campi.<x>` | `CAMPO_NON_AMMESSO` |
| `articolazioni` a un modello singolo | `articolazioni` | `CAMPO_NON_AMMESSO` (regola attuale) |

L'indice parte da 0.

## 5. Catalogo

| Dove | Cambiamento |
|---|---|
| `GET /api/v1/catalogo/modelli` | parametro `multiplo` (boolean, default `false`) |
| `ModelloCatalogoSchema` | `multiplo: boolean` |
| `CampoRichiestoSchema` | `campi`: sotto-campi, solo per i campi ripetibili |
| `schema` di `campi-richiesti` | `items` per i campi ripetibili; `minItems: 1` se obbligatori |

## 6. Builder

| Dove | Cambiamento |
|---|---|
| `POST /api/v1/builder/modelli` | `multiplo: boolean` (default `false`); `true` solo se la foglia ha campi ripetibili, altrimenti `CONTESTO_NON_VALIDO` |
| `POST /api/v1/builder/modelli/{modelloId}/multiplo` | **nuova**: crea il modello multiplo della stessa combinazione copiando le sezioni dell'ultima versione del modello singolo (FR-009e) |
| risposte del modello | `multiplo: boolean` |
| dettaglio versione, `campi[]` | `sotto_campi` per i campi ripetibili |

## 7. Audit

`MODELLO_CREATO` porta `multiplo` nel `payload_minimo`. La creazione da un
singolo registra anche il modello di partenza. Nessun tipo di evento nuovo.
