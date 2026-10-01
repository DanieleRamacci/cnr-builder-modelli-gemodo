# Contratto: formato documentale `GEMODO_DOCUMENT_V1`, forma a frammenti

**Fase 1 di** `specs/012-editor-documento-fedele/plan.md` | **Data**: 2026-09-29

Questo e' un contratto, non una nota interna: la forma dei blocchi viaggia sul
corpo di `PUT /builder/modelli/{modelloId}/versioni/{versioneId}/sezioni`
(`backend/app/builder/api.py:366`) e viene riletta dalla generazione. Chiunque
scriva sezioni - oggi il solo editor del builder - dipende da questa forma.

Il nome del formato **non cambia**: resta `GEMODO_DOCUMENT_V1`, perche' i
principi che lo definiscono (struttura controllata, nessun HTML, nessun CSS,
nessuno script) sono gli stessi. Cambia la forma del paragrafo, e vecchia e
nuova non coesistono: la migrazione converte tutto (FR-016).

## Blocco, forma nuova

```json
{
  "id": "b-0007",
  "tipo": "PARAGRAFO",
  "posizionamento": "BODY",
  "allineamento": "GIUSTIFICATO",
  "ordine": 7,
  "stile": null,
  "frammenti": [
    { "testo": "VISTO", "grassetto": true },
    { "testo": " il Decreto Legislativo 4 giugno 2003, n. 127, recante " },
    { "testo": "“Riordino del Consiglio Nazionale delle Ricerche”", "corsivo": true },
    { "testo": ";" }
  ],
  "placeholder_usati": []
}
```

Il campo `contenuto` **non esiste piu'**. Un blocco che lo porta viene
rifiutato: `extra="forbid"` e' gia' la regola del formato
(`DocumentaleBaseModel`), quindi il rifiuto e' automatico e non va scritto.

### Frammento

| Campo | Tipo | Default | Note |
|---|---|---|---|
| `testo` | string | obbligatorio | testo puro; nessun carattere ha significato speciale |
| `grassetto` | boolean | `false` | |
| `corsivo` | boolean | `false` | |
| `sottolineato` | boolean | `false` | |
| `collegamento` | string | assente | `http`, `https` o `mailto` soltanto |

Le tre enfasi sono combinabili.

### Elenco

```json
{
  "id": "b-0012",
  "tipo": "ELENCO",
  "posizionamento": "BODY",
  "allineamento": "GIUSTIFICATO",
  "ordine": 12,
  "frammenti": [],
  "elementi": [
    { "livello": 0, "marcatore": "NUMERICO",   "frammenti": [{ "testo": "Sono indetti i seguenti concorsi:" }] },
    { "livello": 1, "marcatore": "ALFABETICO", "frammenti": [{ "testo": "un posto presso la sede di Roma" }] },
    { "livello": 1, "marcatore": "ALFABETICO", "frammenti": [{ "testo": "un posto presso la sede di Milano" }] }
  ]
}
```

**Nessun elemento dichiara il proprio numero.** `1.`, `a)`, `b)` li calcola la
resa (FR-015). I contatori si azzerano all'inizio di ogni sezione e a ogni
blocco `TITOLO`.

`livello` ammette `0` e `1`. Un `2` e' rifiutato: meglio un errore esplicito che
un terzo livello reso come il secondo.

### Allineamento

`SINISTRA` | `CENTRO` | `DESTRA` | `GIUSTIFICATO`. Omesso, vale `SINISTRA`.

Resta distinto da `posizionamento`, che dice **dove** sta il blocco e non come
si dispone il testo al suo interno.

## Cornice di pagina

Non viaggia su questo contratto: appartiene al tipo documento (FR-011) e si
imposta con le rotte `.../tipi-documento/{codice}/cornice` del builder
(contratto 002). E' qui solo per dire esplicitamente che **non** e' un blocco:
`LOGO` e `FOOTER` restano tipi di blocco per i casi in cui compaiono una volta
sola nel corpo, mentre cio' che si ripete su ogni pagina e' la cornice.
Forma (rivista il 2026-10-01): intestazione e pie' di pagina indipendenti, con
maschera; il logo e' un'immagine per tipo documento, non un campo del JSON.
Descrizione completa in `docs/formato-documentale.md`.

## Errori

Nessun codice nuovo. Il catalogo condiviso (`infra/openapi/errors.md`) ha gia'
il codice giusto, e questa spec lo riusa invece di inventarne uno:

| Codice | HTTP | Quando, da questa spec |
|---|---|---|
| `MODELLO_DOCUMENTALE_NON_VALIDO` | 422 | testo di un frammento contenente markup; `livello` fuori da {0,1}; `elementi` su un blocco che non e' `ELENCO`; `collegamento` con schema non ammesso |

La descrizione del codice in catalogo dice gia' "il modello contiene HTML/CSS/
script liberi, blocchi non ammessi": e' esattamente questo caso. Va pero'
**esteso il suo `Condizione`** per nominare anche il testo dei frammenti,
perche' oggi quel controllo non esiste affatto - il divieto e' applicato solo a
un booleano auto-dichiarato (`research.md` R6).

## Compatibilita'

Un client che invii la forma vecchia riceve 422. E' accettabile e voluto:
l'unico client esistente e' l'editor del builder, che viene aggiornato nello
stesso incremento, e il formato ha una sola forma per scelta esplicita (FR-016).
