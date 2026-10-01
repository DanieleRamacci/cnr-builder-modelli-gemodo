# Formato documentale `GEMODO_DOCUMENT_V1`

Questa pagina descrive la forma con cui GEMODO conserva il corpo di un
documento (un bando, un contratto) e da cui produce il PDF. Serve a chi
integra GEMODO, a chi ne riusa il codice e a chi deve leggere i dati senza
passare dall'editor.

Il formato è **chiuso**: non contiene HTML, CSS né script, e nessun carattere
del testo ha un significato speciale. Tutto ciò che il documento può essere è
descritto qui. Ciò che non è descritto non è ammesso, e viene **rifiutato** al
salvataggio, mai ripulito in silenzio.

Fonte normativa: `specs/012-editor-documento-fedele` (spec, data-model,
contracts/formato-documentale.md); le regole sono applicate in
`backend/app/quality/document_model.py`.

## Struttura

Una **versione** di un modello contiene una sequenza ordinata di **sezioni**
(per esempio "Premesse", "Art. 1 - Indizione"). Ogni sezione contiene una
sequenza ordinata di **blocchi**. La sezione ha un nome (`codice`, libero fino
a 128 caratteri, unico nella versione) e un `ordine`.

La **cornice di pagina** (logo, intestazione, piè di pagina) non è un blocco:
appartiene al tipo documento e si configura a parte (vedi sotto).

## Blocco

```json
{
  "id": "art3-b2",
  "tipo": "PARAGRAFO",
  "posizionamento": "BODY",
  "allineamento": "GIUSTIFICATO",
  "ordine": 1,
  "stile": null,
  "frammenti": [
    { "testo": "VISTO", "grassetto": true },
    { "testo": " il Decreto Legislativo 4 giugno 2003, n. 127, recante " },
    { "testo": "“Riordino del Consiglio Nazionale delle Ricerche”", "corsivo": true },
    { "testo": ";" }
  ],
  "elementi": [],
  "placeholder_usati": []
}
```

| Campo | Significato |
|---|---|
| `id` | identificatore del blocco, unico nella sezione |
| `tipo` | vedi la tabella dei tipi |
| `posizionamento` | dove sta il blocco nella pagina; ammesso secondo il tipo |
| `allineamento` | `SINISTRA`, `CENTRO`, `DESTRA`, `GIUSTIFICATO`; se assente lo deduce il posizionamento |
| `ordine` | posizione nella sezione |
| `stile` | `H1` o `H2` per un paragrafo reso come titolo; altrimenti `null` |
| `frammenti` | il testo, come sequenza di frammenti (vedi sotto) |
| `elementi` | solo per `ELENCO`: le voci |
| `placeholder_usati` | i segnaposto `{{campo}}` presenti nel testo |

Fino alla spec 012 il testo stava in un campo `contenuto` di tipo stringa.
**Quel campo non esiste più**: un blocco che lo porta è rifiutato. I dati
esistenti sono stati convertiti dalla migrazione `0024`.

### Tipi e posizionamenti

| Tipo | Posizionamenti ammessi | Note |
|---|---|---|
| `PARAGRAFO` | `BODY`, `COLUMN_LEFT`, `COLUMN_RIGHT` | |
| `TITOLO` | `TOP`, `BODY` | l'intestazione d'articolo; fa ripartire la numerazione degli elenchi |
| `ELENCO` | `BODY`, `COLUMN_LEFT`, `COLUMN_RIGHT` | testo negli `elementi`, `frammenti` vuoto |
| `FIRMA` | `BOTTOM_LEFT`, `BOTTOM_RIGHT`, `BOTTOM_CENTER` | |
| `INTERRUZIONE_PAGINA` | `BODY` | nessun testo |
| `TABELLA` | `BODY` | richiede `colonne` |
| `LOGO`, `INTESTAZIONE`, `FOOTER`, `COLONNE` | vedi `POSIZIONI_AMMESSE` | per ciò che compare una volta sola; ciò che si ripete su ogni pagina è la cornice |

## Frammento

Una porzione di testo con la propria enfasi. Le tre enfasi sono combinabili.

| Campo | Tipo | Default |
|---|---|---|
| `testo` | stringa, testo puro | obbligatorio |
| `grassetto` | booleano | `false` |
| `corsivo` | booleano | `false` |
| `sottolineato` | booleano | `false` |
| `collegamento` | stringa `http:`, `https:` o `mailto:` | assente |

Un a capo dentro lo stesso capoverso è il carattere `\n` nel testo. Un
capoverso nuovo è un blocco nuovo.

Un **collegamento** è cliccabile nel PDF e il suo testo resta quello scritto,
quindi si legge anche su carta. Ogni altro schema (`javascript:`, `file:`...)
è rifiutato.

## Elenco

```json
{
  "tipo": "ELENCO",
  "frammenti": [],
  "elementi": [
    { "livello": 0, "marcatore": "NUMERICO",   "frammenti": [{ "testo": "Per la partecipazione sono richiesti:" }] },
    { "livello": 1, "marcatore": "ALFABETICO", "frammenti": [{ "testo": "cittadinanza di uno degli Stati membri dell'Unione Europea;" }] },
    { "livello": 1, "marcatore": "ALFABETICO", "frammenti": [{ "testo": "età non inferiore a 18 anni;" }] }
  ]
}
```

- `livello`: `0` o `1`. Un terzo livello è rifiutato.
- `marcatore`: `NUMERICO` (`1.`), `ALFABETICO` (`a)`), `PUNTATO` (cerchio
  pieno al primo livello, vuoto al secondo).
- **Nessuna voce porta il proprio numero.** Lo calcola la resa: inserendo una
  voce in mezzo, le successive si rinumerano. Il contatore del primo livello
  prosegue fra gli elenchi della stessa sezione e riparte all'inizio di ogni
  sezione e a ogni blocco `TITOLO`; quello del secondo livello riparte a ogni
  voce di primo livello. Le voci puntate non consumano numeri.
- Rientri come in Word: marcatore a 0,63 cm, testo a 1,27 cm, più 1,27 cm per
  il secondo livello. Il testo che va a capo resta allineato al testo.

Il **numero dell'articolo** ("Art. 3") è testo del `TITOLO`, scritto da chi
compone: non è calcolato (decisione del 2026-10-01, rivedibile).

## Segnaposto

Un segnaposto è `{{codice_campo}}` dentro il `testo` di un frammento, e deve
corrispondere a un campo del contratto dati della versione. In generazione è
sostituito **dentro il frammento che lo contiene**: il valore ne eredita
l'enfasi e il capoverso non si spezza. Un segnaposto spezzato fra due frammenti
con enfasi diverse non è un segnaposto.

Nell'**anteprima** di una bozza (`POST .../versioni/{id}/anteprima`) ogni
segnaposto diventa «etichetta del campo». L'anteprima usa lo stesso renderer
della generazione e non registra alcun documento.

## Cornice di pagina

Appartiene al **tipo documento**, non al modello: vale per tutti i modelli di
quel tipo, nell'anteprima e nei documenti generati. La impostano il gestore del
contesto e l'amministratore, da *Contesti -> <contesto> -> Impostazioni modelli*
(`PUT /api/v1/builder/integrazioni/{id}/tipi-documento/{codice}/cornice`).

Intestazione e piè di pagina sono **indipendenti**: ciascuno può mancare, e
ciascuno ha la sua maschera.

```json
{
  "intestazione": {
    "maschera": "LOGO_CENTRO_TESTO_SOTTO",
    "con_logo": true,
    "testo": [
      { "testo": "Consiglio Nazionale delle Ricerche", "grassetto": true },
      { "testo": "\nUfficio Reclutamento del Personale" }
    ]
  },
  "pie_pagina": {
    "maschera": "TESTO_SINISTRA_NUMERO_DESTRA",
    "testo": [{ "testo": "Piazzale Aldo Moro 7 - 00185 Roma" }],
    "numerazione_pagine": true
  }
}
```

| Maschera | Resa |
|---|---|
| `LOGO_CENTRO_TESTO_SOTTO` | logo centrato, fino a tre righe centrate sotto, una linea a separare dal corpo |
| `TESTO_SINISTRA_NUMERO_DESTRA` | una riga di testo a sinistra, "Pagina N di M" a destra |

- La testata non ha un'altezza fissa: il corpo comincia sotto ciò che contiene.
- Il **logo** non sta nel JSON: è un'immagine per tipo documento, caricata con
  `PUT .../cornice/logo` (PNG o JPEG, al massimo 1 MB). Il servizio la apre come
  immagine e ne conserva una copia PNG ricodificata, così che metadati o
  contenuti accodati non arrivino al PDF. `con_logo` dice solo se usarla.

## Errori

| Codice | HTTP | Quando |
|---|---|---|
| `MODELLO_DOCUMENTALE_NON_VALIDO` | 422 | markup nel testo, collegamento con schema non ammesso, livello di elenco fuori da {0, 1}, `elementi` su un blocco che non è `ELENCO`, cornice non valida |
| `PLACEHOLDER_NON_VALIDO` | 400 | in pubblicazione, segnaposto non presenti fra i campi della versione |

Ogni risposta d'errore elenca **tutte** le violazioni in `dettagli`, così che
si possano correggere in un solo giro. Catalogo completo:
`infra/openapi/errors.md`.
