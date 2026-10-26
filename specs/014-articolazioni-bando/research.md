# Research: Campi ripetibili e bando multiplo

**Fase 0 di** `specs/014-articolazioni-bando/plan.md` | **Data**: 2026-10-26

Le decisioni di scope sono nelle Clarifications della spec (sessioni 2026-10-07
e 2026-10-26). Qui si decide il **come**, partendo da cio' che il codice fa
oggi, verificato leggendolo.

---

## R1 - Contratto discovery 0.8.0: `campi` sul campo e grammatica chiusa

**Decisione**: `CampoDiscovery` (`backend/app/discovery/schemas.py:17`) acquista
`campi: tuple[SottoCampoDiscovery, ...] | None`. `SottoCampoDiscovery` ha la
stessa forma di un campo, senza `campi` e con `tipo` limitato a `string`,
`number`, `date`, `boolean`. Il campo diventa `extra="forbid"`; un validatore
`mode="before"` toglie prima le chiavi che iniziano con `_`. Vincoli:
`campi` solo su `tipo: "array"`, non vuoto, codici unici.
`VERSIONE_CONTRATTO_DISCOVERY` passa a `"0.8.0"`, insieme a `info.version` del
contratto `specs/010-.../contracts/geban-discovery-endpoint.openapi.yaml`.

**Rationale**: oggi `CampoDiscovery` non dichiara `extra`, quindi Pydantic usa
`ignore` e una chiave sconosciuta sparisce senza segnale (verificato: il
modello letto con `campi` dentro perde la chiave). FR-004 chiede l'opposto. Il
percorso del punto difforme e' gia' prodotto da `_dettagli_validazione`
(`backend/app/discovery/adapter_http.py:32`) per ogni `ValidationError`, quindi
basta che l'errore nasca nel modello.

Il 2026-10-26 l'albero GEBAN di test (65 foglie) usa solo le sei chiavi
standard; un albero con `articolazioni` aggiunto su una foglia e' valido
contro `contracts/discovery-0.8.0.schema.json` (provato). SC-001 regge.

**Alternatives considered**: `extra="allow"` con controllo a mano delle chiavi
(duplica cio' che Pydantic fa gia'); un tipo `"ripetibile"` al posto di
`array` + `campi` (scartato il 2026-10-07: un secondo vocabolario).

**Impatto da sapere**: `CampoInput` (`backend/app/configurazione/schemas.py:50`),
la struttura definita dall'amministratore, **eredita** da `CampoDiscovery`:
la grammatica nuova vale anche li' senza codice in piu' (FR-006). La
schermata di amministrazione non offre ancora un editor dei sotto-campi:
questo incremento li accetta e li valida via API, l'editor visuale resta
fuori (vedi R12).

---

## R2 - Dove si salvano i sotto-campi della versione

**Decisione**: colonna nuova `campo_modello.sotto_campi` (JSONB, nullable),
copia dei sotto-campi della foglia al momento della creazione della versione.
Una riga di `campo_modello` per il campo ripetibile, come per ogni campo; i
sotto-campi stanno dentro di essa.

**Rationale**: la versione e' una fotografia immutabile (Principio IV) e i
sotto-campi si leggono sempre tutti insieme al loro campo. Righe figlie con
una chiave verso il padre aggiungerebbero join e vincoli senza un caso d'uso
che le interroghi da sole. `clona_campi`
(`backend/app/builder/repository.py:592`) copia gia' `opzioni` e
`validazione` con `deepcopy`: si aggiunge `sotto_campi` allo stesso modo, e
nuove versioni, varianti ed edizioni derivate li ereditano.

**Alternatives considered**: tabella `campo_modello_sotto_campo` (piu'
normalizzata, nessun beneficio misurabile); riuso di `opzioni` (gia' usata per
le opzioni dei campi, significati mescolati).

---

## R3 - Modello multiplo: un attributo del modello, parte dello slot

**Decisione**: colonna `modello_documento.multiplo` (boolean, not null,
default false). Lo slot di categorizzazione diventa
`(tipo_documento, percorso, dimensioni, multiplo, variante)`:

- gli indici unici `uq_modello_slot_variante` e `uq_modello_slot_nota`
  (`backend/app/catalog/models.py:72-87`) includono `multiplo`;
- `modelli_sullo_slot` e `get_versione_pubblicata_corrente`
  (`backend/app/builder/repository.py:344`, `:618`) filtrano per `multiplo`,
  cosi' pubblicare il multiplo non archivia il singolo (FR-009f);
- `_identita_modello` (`backend/app/builder/service.py:133`) aggiunge una
  parte `MULTIPLO` al codice e "(bando multiplo)" al nome, altrimenti singolo
  e multiplo STANDARD dello stesso slot genererebbero lo stesso codice e
  violerebbero `uq_modello_documento_tipo_codice`;
- varianti ed edizioni derivate ereditano `multiplo` dal modello di origine.

**Rationale**: `variante` ha gia' un significato (la decide il gestore con una
nota, FR-019 della 002) e "multiplo" non e' una variante: e' un'altra forma
del contratto dati. Metterlo in `dimensioni` lo farebbe sembrare una
dimensione dichiarata dall'integrazione, e il fallback delle policy
(`_fallback_per_policy`) lo tratterebbe come tale.

**Alternatives considered**: variante con codice riservato `MULTIPLO`
(mescola due assi e si scontra con la numerazione delle varianti);
dimensione `multiplo` (vedi sopra).

---

## R4 - Cosa entra nella versione di un modello singolo e di uno multiplo

**Decisione**: `crea_versione` (`backend/app/builder/service.py:797`) applica
FR-009b lato server:

- modello singolo: un campo ripetibile della foglia nella richiesta e'
  `CAMPO_NON_AMMESSO` (400);
- modello multiplo: tutti i campi ripetibili della foglia sono inclusi; se la
  richiesta ne omette uno, `CAMPO_NON_AMMESSO` con messaggio che dice quale
  manca.

Nella copia del modello multiplo il campo ripetibile ha `obbligatorio = true`
anche se la foglia dice `false` (FR-016c): la foglia vale per singoli e
multipli, la versione vale solo per i multipli.

Il frontend (`modello-crea.component.ts:565`, oggi manda **tutti** i campi
della foglia) manda i campi coerenti con la scelta; il server resta l'autorita'.

**Conseguenza**: FR-016g si ottiene senza codice nuovo in validazione. Un
modello singolo non ha `articolazioni` fra i campi, e
`PayloadValidationService` (`backend/app/validation/service.py:44`) risponde
gia' `CAMPO_NON_AMMESSO` per ogni chiave fuori contratto.

---

## R5 - Segnaposti dell'elemento

**Decisione**: dentro una riga ripetuta su `<campo>` sono ammessi
`{{<campo>.codice}}`, `{{<campo>.descrizione}}` e
`{{<campo>.campi.<sotto-campo>}}`. `{{<campo>}}` da solo non e' mai un
segnaposto ammesso (FR-015: nessuna lista grezza).

**Rationale**: la regex dei segnaposti dell'editor
(`frontend/src/features/builder/frammenti.ts:83`, `[A-Za-z0-9_.-]+`) accetta
gia' i punti, e `placeholder_usati` dei blocchi si ricalcola dal testo
(`documento-editor.ts:565`). Il namespace con il codice del campo evita
collisioni: `numero_posti` del padre e `articolazioni.campi.numero_posti`
sono stringhe diverse (US2, scenario 2).

**Validazione in pubblicazione** (`_valida_documento`,
`backend/app/builder/service.py:879`): l'insieme ammesso oggi e' "codici dei
campi della versione" (`_placeholder_ammessi`). Diventa a due livelli:
principali ammessi solo fuori dalle righe ripetute, segnaposti di elemento
ammessi solo nelle righe ripetute dello stesso campo (FR-016b). La regola
vive in `backend/app/quality/document_model.py`, dove gia' stanno le altre
violazioni di struttura, e ritorna tutte le violazioni insieme.

---

## R6 - La tabella nel formato `GEMODO_DOCUMENT_V1`

**Stato attuale, verificato**: `BloccoDocumento` di tipo `TABELLA`
(`backend/app/documentale/schemas.py:145`) ha solo `colonne: list[str]` e i
`frammenti` del blocco. Il renderer stampa le colonne unite da `" | "` e sotto
il testo (`backend/app/generazione/renderer.py:434`). L'editor non offre la
tabella (`frontend/src/features/builder/documento-editor.ts:75`) e la
conserva come blocco "riservato" non modificabile (`:355`).

**Decisione**: estensione additiva del blocco `TABELLA`:

```
righe: list[RigaTabella]              # vuota = forma attuale
RigaTabella { celle: list[CellaTabella], ripeti_per: str | None }
CellaTabella { frammenti: list[FrammentoTesto] }
```

`colonne` resta l'intestazione (testo semplice, niente segnaposti). Ogni riga
ha tante celle quante colonne. Il formato resta `GEMODO_DOCUMENT_V1`: la
chiave nuova e' facoltativa e i documenti esistenti restano validi senza
migrazione dei dati.

**Alternatives considered**: tabella come sequenza di blocchi riga (rompe
l'unita' della tabella in impaginazione); celle a stringa semplice (perde
grassetto e corsivo, che il resto del formato ha dalla 012).

---

## R7 - Resa della tabella nel PDF

**Decisione**: `FPDF.table()` di fpdf2 2.8.8 (versione installata), con la
riga di intestazione da `colonne` e una riga per ogni riga del modello dopo
l'espansione. Testo delle celle con il font del documento (Titillium, 012 R1)
e l'enfasi del frammento.

**Rationale**: `table()` gestisce bordi, larghezze, a capo nella cella e
interruzione di pagina con ripetizione dell'intestazione: scriverlo a mano
con `multi_cell` sarebbe codice da mantenere per un risultato peggiore.

**Verificato in implementazione (2026-10-26)**: `table()` della 2.8.8 mescola
varianti di font in una cella solo interpretando `markdown=True`, che il
renderer esclude. Una cella ha quindi l'enfasi comune a **tutti** i suoi
frammenti (`_stile_cella` in `renderer.py`); un grassetto su una parte sola
della cella non si rende.

---

## R8 - Espansione delle righe in generazione e in anteprima

**Decisione**: `sostituisci_placeholder` (`renderer.py:499`) espande una riga
con `ripeti_per = <campo>` in una riga per elemento di `dati[<campo>]`,
nell'ordine della lista (FR-016a), sostituendo i segnaposti dell'elemento con
i valori di quell'elemento. Un sotto-campo facoltativo assente diventa cella
vuota (FR-016d). I segnaposti principali seguono la regola attuale
(`PlaceholderSenzaValore` se manca il valore).

Anteprima (`anteprima`, `backend/app/builder/service.py:946`): oggi riempie
ogni segnaposto con «etichetta». Per le righe ripetute costruisce **due**
elementi d'esempio, con valori «Etichetta (1)» e «Etichetta (2)» (FR-016f).
La stessa funzione serve l'impaginazione misurata (012 T080), quindi le pagine
mostrate nell'editor contano anche le righe d'esempio.

---

## R9 - Validazione dei dati di un campo ripetibile

**Decisione**: in `PayloadValidationService.validate_payload`, per un campo
della versione con `sotto_campi`:

1. il valore deve essere una lista (altrimenti `TIPO_NON_VALIDO` sul campo);
2. lista vuota su campo obbligatorio: `CAMPO_OBBLIGATORIO` sul campo;
3. per ogni elemento: oggetto con `codice` stringa non vuota, `descrizione`
   stringa non vuota, `campi` oggetto; chiavi diverse da queste tre:
   `CAMPO_NON_AMMESSO`;
4. `codice` ripetuto: `CODICE_ELEMENTO_DUPLICATO` sul campo (codice nuovo);
5. dentro `campi`: obbligatorieta', tipo (riusa `_matches_type`), chiavi non
   dichiarate.

Percorsi (FR-012): `articolazioni[TEMA_A].campi.numero_posti`; senza codice
valido `articolazioni[0]`. **L'indice parte da 0**, come nella lista JSON che
l'integratore ha inviato. La spec viene allineata (l'esempio
`articolazioni[1]` non diceva la base).

Gli errori di tutti gli elementi si raccolgono insieme, come gia' accade per i
campi principali.

---

## R10 - Catalogo: `multiplo` nella risposta e nel filtro

**Decisione**: `ModelloCatalogoSchema` (`backend/app/catalog/schemas.py:36`)
acquista `multiplo: bool`. `GET /api/v1/catalogo/modelli` accetta
`multiplo: bool = false` e lo passa a `list_published_model_versions`. Senza
parametro il filtro vale `false` (FR-009h, SC-007). Le edizioni derivate
annidate seguono il modello di origine.

`campi-richiesti` (`_json_schema_for_field`, `catalog/service.py:301`) per un
campo con sotto-campi produce `type: array`, `minItems: 1` se obbligatorio, e
`items` con `codice`, `descrizione`, `campi` (con le proprieta', i required e
`additionalProperties: false`) (FR-013). `CampoRichiestoSchema` porta anche
`campi` con i sotto-campi, per chi legge l'elenco e non lo schema.

---

## R11 - Editor: tabella su ProseMirror senza dipendenze nuove

**Decisione**: nodi propri nello schema dell'editor
(`documento-editor.ts:248`): `tabella` (attributo `colonne`), `riga`
(attributo `ripeti_per`), `cella` (contenuto inline, come il paragrafo).
Comandi: inserisci tabella (colonne iniziali), aggiungi/togli riga e colonna,
marca/smarca riga ripetuta scegliendo il campo ripetibile. Conversione
documento <-> blocchi nelle funzioni gia' esistenti (`:511`, `:562`).

**Rationale**: `prosemirror-tables` non e' fra le dipendenze
(`frontend/package.json`) e porta celle unite, selezione rettangolare e
ridimensionamento, che il formato non rappresenta. Una tabella a griglia fissa
si esprime con tre nodi.

**Alternatives considered**: `prosemirror-tables` (vedi sopra); tabella
modificabile in un dialogo fuori dall'editor (rompe la fedelta' dell'editor
al documento, contro la 012).

---

## R12 - Fuori da questo incremento, deciso

- Editor visuale dei sotto-campi nella struttura definita dall'amministratore
  (`tipo-documento-struttura.component.ts`): la grammatica vale via API
  (R1); la schermata mostra i sotto-campi in sola lettura.
- Avvisi di FR-016h calcolati anche lato server: sono **non bloccanti** e
  servono a chi scrive, quindi li calcola il builder; il server applica solo il
  blocco (due righe ripetute sullo stesso campo nella stessa tabella).
- Rilevazione dei cambiamenti dell'albero sotto modelli pubblicati: e' la
  spec futura sul monitoraggio (010 T056, T117).

---

## R13 - Migrazione e deploy

**Decisione**: migrazione `0031` (ultima presente: `0030_registro_attivita`):
`modello_documento.multiplo` con default `false`, `campo_modello.sotto_campi`
nullable, ricostruzione dei due indici di slot con `multiplo`. Solo schema,
nessun dato riscritto; i modelli esistenti diventano singoli, che e' cio' che
sono.

Il backend esegue `alembic upgrade head` all'avvio: la migrazione va
annunciata prima del redeploy, anche se non tocca dati.
