# Data Model: Editor documentale fedele al provvedimento reale

**Fase 1 di** `specs/012-editor-documento-fedele/plan.md` | **Data**: 2026-09-29

Il formato documentale resta `GEMODO_DOCUMENT_V1` per nome e per principio -
struttura controllata, nessun HTML, nessun CSS, nessuno script - e cambia nella
forma del paragrafo. Le definizioni vivono in
`backend/app/documentale/schemas.py`, che e' gia' la sede del formato.

## Che cosa cambia, in una riga

Un paragrafo non e' piu' **una stringa**; e' **una sequenza di frammenti**.

Tutto il resto di questo documento discende da li'.

---

## Entita' nuove

### `FrammentoTesto`

Porzione di paragrafo con i propri attributi di enfasi. E' l'entita' su cui
poggia FR-001.

| Campo | Tipo | Regole |
|---|---|---|
| `testo` | `str` | Testo puro. Nessun carattere ha significato speciale: il formato non definisce alcun linguaggio di marcatura (FR-002). Non puo' contenere markup (R6). |
| `grassetto` | `bool` | default `false` |
| `corsivo` | `bool` | default `false` |
| `sottolineato` | `bool` | default `false` |
| `collegamento` | `str \| None` | URL o `mailto:`; default assente. Il `testo` resta leggibile dove il collegamento non e' cliccabile (FR-014). |

Le enfasi sono **combinabili**: grassetto e corsivo insieme sono un caso reale
del bando ed e' fra gli Edge Cases. In resa corrispondono alla variante
grassetto-corsivo del font (R1, R2).

### `ElementoElenco`

| Campo | Tipo | Regole |
|---|---|---|
| `livello` | `int` | `0` o `1`. Due livelli, come chiede FR-003; un terzo livello e' rifiutato invece di essere reso male. |
| `marcatore` | `TipoMarcatore` | `NUMERICO` \| `ALFABETICO` \| `PUNTATO` |
| `frammenti` | `list[FrammentoTesto]` | il testo dell'elemento, con la sua enfasi |

**Il numero mostrato non e' un campo.** Lo calcola la resa (FR-015). Un
elemento non sa di essere il terzo: sa di essere di livello 0, numerico, e in
quale posizione della sequenza si trova.

### `CornicePagina`

Cio' che si ripete su ogni pagina. Appartiene al **tipo documento**, non al
modello (FR-011).

| Campo | Tipo | Regole |
|---|---|---|
| `logo_ref` | `str \| None` | riferimento al logo istituzionale |
| `intestazione` | `list[FrammentoTesto]` | i testi di testata, che possono differire fra tipi documento |
| `pie_pagina` | `list[FrammentoTesto]` | testo fisso del pie' di pagina |
| `numerazione_pagine` | `bool` | default `true` |

---

## Entita' modificate

### `BloccoDocumento`

| Campo | Prima | Dopo |
|---|---|---|
| `contenuto` | `str \| None` | **rimosso** (FR-016: una sola forma) |
| `frammenti` | - | `list[FrammentoTesto]`, default vuoto |
| `allineamento` | - | `AllineamentoTesto`, default `SINISTRA` (FR-004) |
| `elementi` | - | `list[ElementoElenco]`, default vuoto; ammesso solo su `ELENCO` |
| `stile` | `str \| None`, **ignorato dal renderer** | invariato nella forma, ma ora **letto** dalla resa |

Gli altri campi (`id`, `tipo`, `posizionamento`, `ordine`, `placeholder_usati`,
`regole_layout`, `asset_ref`, `colonne`) restano com'erano.

`stile` merita una riga a parte: esiste gia', il frontend lo scrive con `H1`/`H2`,
e `_rendi_blocco` non lo guarda mai. E' il difetto che la spec cita come gia'
visibile; qui smette di esserlo, perche' FR-008 non ammette che l'editor mostri
un titolo e il PDF produca un paragrafo.

### `TipoBloccoDocumento`

Si aggiunge **`ELENCO`**. I tipi esistenti (`INTESTAZIONE`, `LOGO`, `TITOLO`,
`PARAGRAFO`, `TABELLA`, `COLONNE`, `FIRMA`, `FOOTER`, `INTERRUZIONE_PAGINA`)
restano tutti: nessuno viene rimosso o rinominato.

### `AllineamentoTesto` (nuova enumerazione)

`SINISTRA` | `CENTRO` | `DESTRA` | `GIUSTIFICATO`.

E' distinto da `PosizionamentoBlocco`, che c'e' gia' e descrive **dove** sta il
blocco nella pagina (`TOP`, `BODY`, `BOTTOM_RIGHT`...). Oggi il renderer deriva
l'allineamento dal posizionamento tramite una tabella di conversione: e' un
ripiego, perche' un paragrafo nel `BODY` puo' essere giustificato o centrato e
il posizionamento non sa dirlo. Con `allineamento` esplicito quella derivazione
resta solo come default per i blocchi che non lo dichiarano.

### `TipoDocumento`

Una colonna nuova, `cornice_pagina` (JSONB, annullabile), che serializza una
`CornicePagina`. Nulla di quanto esiste cambia forma.

---

## Regole di validazione

Si aggiungono a quelle gia' applicate in
`backend/app/quality/document_model.py`, che restano.

1. **Nessun markup nel testo** (FR-002, SC-005): il `testo` di un frammento che
   contiene markup e' **rifiutato alla scrittura** con errore funzionale. Mai
   ripulito in silenzio. Oggi questo controllo non esiste (R6): e' nuovo.
2. **Annidamento massimo**: `ElementoElenco.livello` ∈ {0, 1}.
3. **`elementi` solo su `ELENCO`**; `frammenti` vuoti su `ELENCO` e
   `INTERRUZIONE_PAGINA`, popolati altrove.
4. **Posizionamento ammesso** per `ELENCO`: `BODY`, `COLUMN_LEFT`,
   `COLUMN_RIGHT`, come `PARAGRAFO`.
5. **Collegamento**: solo schemi `http`, `https`, `mailto`. Un `javascript:`
   e' markup attivo travestito da URL e va rifiutato con lo stesso errore del
   punto 1.
6. **Segnaposto**: invariata la regola esistente (ogni segnaposto usato da un
   blocco dev'essere dichiarato in `placeholder_usati`), estesa al fatto che
   `placeholder_usati` ora si calcola sull'unione dei `testo` dei frammenti e
   degli elementi di elenco.

## Sostituzione dei segnaposto

`sostituisci_placeholder` opera oggi sulla stringa `contenuto`. Diventa una
sostituzione **per frammento**, il che soddisfa FR-005 senza sforzo: il valore
sostituito eredita l'enfasi del frammento che lo conteneva, perche' resta
dentro quel frammento.

Il caso a cavallo - un segnaposto spezzato fra due frammenti con enfasi diverse
- non e' rappresentabile e non deve esserlo: `{{numero_posti}}` scritto meta' in
grassetto e meta' no non e' un segnaposto, e' due pezzi di testo. L'editor lo
impedisce tenendo il segnaposto dentro un frammento solo; la validazione lo
rileva perche' quel segnaposto non risulterebbe in `placeholder_usati`.

## Migrazione

Una migrazione Alembic sulla colonna JSONB `sezione_modello.contenuto`
(`backend/app/catalog/models.py:191`):

```
{"tipo": "PARAGRAFO", "contenuto": "VISTO il D.Lgs 127/2003"}
   ->
{"tipo": "PARAGRAFO", "frammenti": [{"testo": "VISTO il D.Lgs 127/2003"}]}
```

`contenuto: null` diventa `frammenti: []`. `downgrade` concatena i `testo` dei
frammenti, che e' esatto per i dati prodotti dalla migrazione e con perdita
dell'enfasi per quelli creati dopo: e' il comportamento corretto, perche'
tornare al formato vecchio *significa* perdere cio' che il formato vecchio non
sa rappresentare.

La migrazione tocca anche versioni pubblicate. E' una riscrittura di codifica,
non di contenuto, e la prova che sia davvero cosi' non e' l'argomento ma
SC-004: PDF generati prima, migrazione, PDF rigenerati, confronto del contenuto
estratto. Una differenza ferma la migrazione.

## Stato e transizioni

Nessuna transizione di stato nuova. Le sezioni restano scrivibili **solo in
BOZZA** (`002` FR-005, gia' applicato in `BuilderService.sostituisci_sezioni`),
e l'anteprima si chiede su una versione in BOZZA senza modificarne lo stato: e'
una lettura che produce un file, non un passaggio di ciclo di vita.
