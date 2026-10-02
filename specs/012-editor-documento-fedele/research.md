# Research: Editor documentale fedele al provvedimento reale

**Fase 0 di** `specs/012-editor-documento-fedele/plan.md` | **Data**: 2026-09-29

Le quattro domande di scope sono gia' chiuse nelle Clarifications della spec. Qui
si risolve cio' che restava incerto sul **come**, e dove possibile lo si risolve
provandolo, non deducendolo.

---

## R1 - Il renderer attuale non sa scrivere i caratteri italiani

**Decisione**: incorporare **Titillium Web** (licenza OFL) nel backend, in
quattro varianti (regolare, grassetto, corsivo, grassetto-corsivo), e smettere
di usare il font di base Helvetica.

**Rationale**: non e' una preferenza estetica, e' un difetto verificato.
`backend/app/generazione/renderer.py` usa `Helvetica`, che e' un *core font*
PDF limitato a latin-1. Provato sul serio con la libreria installata:

```
>>> p.multi_cell(0, 6, 'virgolette curve “Riordino” trattino – apostrofo ’')
FPDFUnicodeEncodingException: Character "“" at index 17 ... is outside the
range of characters supported by the font used: "helvetica".
```

Non e' una degradazione silenziosa: **solleva un'eccezione**, che in
`GenerazioneDocumentiService.genera` finisce nel `except Exception` generico e
diventa un documento in stato `FALLITO`. Oggi quindi un bando che contenga una
virgoletta curva - cioe' il bando di riferimento, e qualunque testo incollato da
Word - non si genera affatto. SC-006 non e' un miglioramento di rifinitura: e'
la riparazione di un blocco.

Titillium Web e' scelto perche' e' il font delle linee guida di design per i
siti della PA italiana, e' **gia' presente nel repository** come dipendenza del
frontend (`frontend/node_modules/bootstrap-italia/dist/fonts/Titillium_Web/`,
con il suo `OFL.txt`), e copre latin-ext. Il documento generato dal backend e
l'interfaccia che lo compone useranno lo stesso carattere, il che aiuta FR-008.

**Alternatives considered**: DejaVu Sans (copertura Unicode piu' ampia, ma
estranea all'identita' PA e non gia' nel progetto); Noto Sans (stessa
obiezione); restare su Helvetica normalizzando i caratteri in ASCII (rifiutata:
trasformerebbe il testo del provvedimento, che e' esattamente cio' che SC-006
vieta).

**Conseguenza operativa**: i `.ttf` vanno **copiati** sotto il backend (es.
`backend/app/generazione/fonts/`) con il file di licenza accanto.
`node_modules/` non e' un percorso su cui il backend possa fare affidamento a
runtime, e `frontend/dist/` e' un artefatto di build.

---

## R2 - Enfasi mista dentro un paragrafo giustificato

**Decisione**: rendere i frammenti con l'API a paragrafi di fpdf2
(`FPDF.text_columns(...)` + `paragraph.write(...)`), cambiando font fra un
frammento e l'altro.

**Rationale**: era il punto tecnicamente piu' a rischio dell'intera feature -
giustificare un testo significa distribuire lo spazio sulla riga, e farlo
quando la riga contiene pezzi con font diversi non e' scontato. Provato con
fpdf2 2.8.8 su un "visto" reale a cinque frammenti (grassetto, normale,
corsivo, grassetto-corsivo) in un paragrafo giustificato. Il testo estratto dal
PDF prodotto:

```
'VISTO il  Decreto  Legislativo  4  giugno  2003,  n.  127,  recante  “Riordino
del  Consiglio  Nazionale  delle  Ricerche”,  e\nsuccessive modificazioni – in
particolare l’art. 4 – nonché le disposizioni attuative ivi richiamate;'
```

con i quattro font effettivamente incorporati nel file
(`TitilliumWeb`, `TitilliumWebBold`, `TitilliumWebItalic`,
`TitilliumWebBoldItalic`). La spaziatura dilatata nella prima riga e compatta
nell'ultima e' la giustificazione al lavoro. Tutti i caratteri tipografici
italiani sono sopravvissuti alla prova.

**Alternatives considered**: `multi_cell(markdown=True)`, che fpdf2 offre e che
interpreta `**grassetto**` nel testo - rifiutata perche' reintrodurrebbe
proprio la sintassi nel contenuto che la clarification sull'enfasi ha escluso,
e obbligherebbe a proteggere gli asterischi presenti nel testo reale.
`write_html()` - rifiutata: fa entrare l'HTML dalla porta di servizio, contro
il Principio III.

**Residuo dichiarato**: la verifica e' su testo estratto e font incorporati, non
visiva - su questa macchina non c'e' un rasterizzatore PDF. Il confronto visivo
col bando reale fa comunque parte di SC-001 e va fatto da chi lo possiede.

---

## R3 - Dove riparte la numerazione

**Decisione**: i contatori di elenco si azzerano **all'inizio di ogni sezione e
a ogni blocco di tipo `TITOLO`**; l'elemento di lista non porta mai il numero,
solo `livello` e `marcatore`.

**Rationale**: FR-015 chiede che la numerazione riparta "all'inizio di ogni
articolo", ma il formato non ha una nozione di articolo. Ce l'ha pero' di
titolo: nel bando di riferimento ogni articolo si apre con `Art. N - Rubrica`,
che e' un `TITOLO`. Legare l'azzeramento al titolo usa la struttura che il
documento gia' ha, invece di inventare un contenitore "articolo" che il gestore
dovrebbe ricordarsi di creare.

**Alternatives considered**: un blocco contenitore `ARTICOLO` esplicito (piu'
preciso, ma aggiunge un concetto all'editor e un annidamento al formato, e
nessuno dei due e' richiesto da un requisito); numerazione continua sull'intero
documento (contraddice FR-015 e il documento reale).

**Conseguenza**: l'annidamento resta a due livelli (FR-003), quindi due
contatori, non una pila arbitraria. Un elenco che attraversa un'interruzione di
pagina prosegue: i contatori appartengono alla composizione, non alla pagina.

---

**Limite accettato (2026-10-01)**: il numero dell'articolo non e' calcolato.
Inserire un articolo fra l'1 e il 2 lascia "Art. 2" com'e', e il gestore
rinumera a mano. Alternativa tenuta per dopo: una sezione marcata come articolo,
con "Art. N" calcolato dalla posizione e il gestore che scrive solo la rubrica.
Spostare una sezione con Su/Giu' rinumererebbe tutto.

## R4 - L'anteprima non deve poter diventare una generazione

**Decisione**: un percorso separato che condivide il **renderer** ma non il
**servizio di generazione**: nuova rotta sul builder, che compone i blocchi,
sostituisce i segnaposto con valori fac-simile e restituisce i byte del PDF,
senza toccare `StorageDocumentiService`.

**Rationale**: FR-010 impone tre negazioni (nessun documento registrato,
nessuna idempotenza consumata, nessun permesso di generazione). Guardando
`GenerazioneDocumentiService.genera`, tutte e tre nascono da li': e' quel
metodo che calcola `hash_dati`, interroga `esistente_per_chiave` e chiama
`registra_successo`. Riusare `genera` con un parametro `anteprima=True`
significherebbe difendere quelle tre negazioni con dei condizionali dentro il
percorso ufficiale - e un condizionale sbagliato in quel punto produce un
documento ufficiale non voluto. Separare i percorsi rende le negazioni vere per
costruzione: il codice dell'anteprima non importa nemmeno lo storage.

Cio' che va condiviso e' `render_documento`, perche' e' esattamente FR-008: se
anteprima e PDF finale non escono dalla **stessa** funzione, torneranno a
divergere come e' gia' successo con H1/H2.

**Autorizzazione**: l'anteprima e' un'azione di chi compone, quindi
`verify_scrittura_su_contesto` sul tipo documento del modello - lo stesso
controllo che gia' protegge la scrittura delle sezioni - non
`DOCUMENTI_GENERATORE`.

**Valori fac-simile**: derivati dai campi richiesti della versione
(`etichetta`/tipo), nella forma `«etichetta»`, cosi' che nel PDF di anteprima si
riconosca a colpo d'occhio cosa e' segnaposto e cosa e' testo. Il documento
resta marcato `DOCUMENTO DI TEST - NON UFFICIALE` come tutto il resto, piu' una
marcatura di anteprima.

**Alternatives considered**: anteprima resa nel browser dal frontend (rifiutata:
sarebbe una seconda implementazione, cioe' il difetto che FR-008 vuole
chiudere); anteprima che genera un documento in stato `BOZZA` nello storage
(rifiutata: FR-010 lo vieta, e sporcherebbe l'archivio con documenti che nessuno
ha chiesto).

---

## R5 - Migrare le sezioni gia' salvate

**Decisione**: una migrazione Alembic che riscrive `sezione_modello.contenuto`
(JSONB) trasformando ogni blocco `{"contenuto": "testo"}` in
`{"frammenti": [{"testo": "testo"}]}`, con `downgrade` simmetrico.

**Rationale**: FR-016 chiede una sola forma nel formato. I blocchi vivono in una
colonna JSONB (`backend/app/catalog/models.py:191`), quindi la conversione e'
una riscrittura di dati, non un cambio di schema relazionale.

**Il punto delicato, da dichiarare**: la migrazione tocca anche le sezioni di
versioni **gia' pubblicate**, e il Principio III dice che il contenuto
pubblicato non si sovrascrive, si versiona. La deviazione e' consapevole e
circoscritta: qui non cambia il *contenuto* del provvedimento ma la sua
*codifica*, e un frammento unico senza enfasi e' semanticamente la stessa
stringa di prima. La garanzia non e' l'argomento: e' SC-004, cioe' generare i
PDF prima della migrazione, rigenerarli dopo e confrontare il contenuto
estratto. Se un documento cambia, la migrazione e' sbagliata e va fermata.

**Alternatives considered**: doppia forma accettata dal renderer (scartata nella
clarification: due strade di resa che divergono nel tempo); versionare il
formato blocco per blocco (costo sproporzionato per una conversione che e'
senza perdita).

---

## R6 - Il divieto di HTML oggi non e' applicato al testo

**Decisione**: introdurre un controllo reale sul testo dei frammenti alla
scrittura delle sezioni, che rifiuta il contenuto con un errore funzionale.

**Rationale**: FR-002 dice "con la stessa forza di oggi". Verificata quale sia,
oggi, quella forza: `backend/app/quality/document_model.py:85` rifiuta un
modello solo se il **booleano auto-dichiarato** `contiene_html_libero` e' vero.
Nessun punto del codice guarda dentro `contenuto`. Un client che scriva
`<b>VISTO</b>` lasciando il flag a `false` passa indisturbato, e il renderer
oggi stampa quei tag come testo letterale. "La stessa forza di oggi" e' dunque
**nessuna forza**, e riprodurla non sarebbe conforme a FR-002.

La rappresentazione a frammenti chiude il problema per costruzione sul lato
resa - `testo` non viene mai interpretato, quindi nessun markup puo' produrre
effetti - ma non basta a soddisfare FR-002, che chiede un **rifiuto**, non
un'innocuita'. Serve quindi un controllo esplicito in scrittura, con un codice
di errore proprio nel catalogo condiviso.

**Alternatives considered**: ripulire il markup in silenzio (vietato
esplicitamente da FR-002); fidarsi dei frammenti e non controllare nulla
(lascia FR-002 non implementato e SC-005 non verificabile).

---

## R7 - Dove vive la cornice di pagina

**Decisione**: sul **tipo documento**, in una colonna JSONB dedicata, con la
stessa grammatica del resto del formato (frammenti, non testo libero).

**Rationale**: e' la clarification sulla cornice, applicata. Metterla sul tipo
documento significa che la si configura dove gia' si configura la struttura del
tipo documento, che l'editor del modello non la mostra e che nessun gestore la
puo' sbagliare. Il logo resta un riferimento ad asset: gli asset versionati sono
fuori dal perimetro di questo incremento (come gia' annota il renderer), quindi
in questo incremento il logo e' un riferimento risolto dal renderer a un file
noto, non un sistema di gestione asset.

**L'eccezione per modello e' rinviata, e costa poco rinviarla**: aggiungerla
domani significa aggiungere una sovrascrittura opzionale su una cornice che
esiste gia', non riprogettare. E' stato confermato con chi decide.

---

## R8 - Incollare da Word

**Decisione**: incolla **di base** dentro US1. Si conservano grassetto, corsivo,
sottolineato, capoversi ed elenchi; tutto il resto viene scartato. La traduzione
avviene **nel browser**, e verso il backend partono gia' frammenti.

**Rationale**: gli appunti di Word portano piu' rappresentazioni dello stesso
testo in parallelo, fra cui una HTML che descrive l'enfasi. L'editor oggi la
butta via per una ragione precisa: `contenteditable="plaintext-only"`
(`frontend/src/features/builder/modello-anteprima.component.ts:390`), scelta
obbligata finche' un paragrafo era una stringa sola e il grassetto non aveva
dove stare. Con i frammenti quel posto esiste, quindi il vincolo cade.

Il punto che tiene in piedi il Principio III: l'HTML di Word viene interpretato
e **scartato nel browser**. Non raggiunge mai il backend, che continua a
ricevere solo frammenti - testo puro con attributi booleani. Il divieto di HTML
non viene allentato, non viene nemmeno sfiorato.

| Da Word | Esito |
|---|---|
| grassetto, corsivo, sottolineato | attributi del frammento |
| capoversi | blocchi `PARAGRAFO` distinti |
| elenchi puntati e numerati | blocco `ELENCO` |
| colori, dimensioni, font, rientri, tabulazioni | scartati |
| immagini, note a pie' di pagina, campi automatici | scartati |
| tabelle | scartate in questo incremento (la spec le dichiara fuori scope) |

**La complicazione vera, da non scoprire a meta' implementazione**: Word incolla
spesso `1.`, `2.`, `a)` come **testo dentro il paragrafo**, non come lista vera.
Sommato alla numerazione calcolata in resa (FR-015) produrrebbe `1. 1. Sono
indetti...`. L'incolla deve quindi riconoscere e rimuovere i marcatori scritti a
mano quando converte in `ELENCO`.

**Perche' "di base" e non di piu'**: il product owner ha chiarito che i visti
finiranno in una **biblioteca di blocchi riutilizzabili**
(`docs/project-map.md:212`, futura spec `013`), da cui si pescano invece di
riscriverli. Con la biblioteca, i quaranta visti si incollano **una volta
sola** per popolarla, non a ogni bando: l'incolla torna a essere una comodita'
di caricamento, non la via d'ingresso quotidiana. Serve pero' fin da subito,
perche' e' con quello che la biblioteca verra' riempita la prima volta.

**Alternatives considered**: rimandare l'incolla alla `013` - scartata perche'
il lavoro si sposterebbe soltanto, dato che i visti devono comunque entrare da
qualche parte. Incolla completo con tabelle e immagini - scartata: gli asset
versionati non esistono ancora e le tabelle del bando stanno negli allegati,
fuori dal documento principale.

## R9 - Un'area di scrittura per sezione (2026-10-02)

**Decisione**: il testo di una sezione e' **un solo editor ProseMirror**
(`frontend/src/features/builder/editor-sezione.component.ts`), con uno schema
che ricalca `GEMODO_DOCUMENT_V1` e nient'altro
(`frontend/src/features/builder/documento-editor.ts`). Prima ogni blocco era
un `contenteditable` a se'.

**Rationale**: il browser non estende una selezione da un `contenteditable`
all'altro. Con un'area per blocco, selezionare tre capoversi per metterli in
grassetto, o riselezionare cio' che si e' appena incollato, non era possibile:
non un difetto correggibile, ma il limite di quella forma. Riscriverla a mano
su un solo `contenteditable` vorrebbe dire reimplementare cio' che un editor
strutturato gia' fa (mappatura fra DOM e modello, incolla, selezione su nodi
non testuali), cioe' la parte che si rompe da browser a browser.

**Cosa resta uguale**: il formato salvato (lo schema non ammette nulla che il
formato non ammetta, e la conversione da e verso i blocchi e' testata in andata
e ritorno), il backend, il PDF, l'anteprima, la cornice; toolbar, menu Stile e
comando `/` sono diventati comandi sulla selezione. L'HTML degli appunti lo
interpreta ancora `convertiAppunti`; cio' che si copia dall'editor stesso lo
riconosce ProseMirror e lo rimette con la sua struttura.

**Scelte interne**:

- le voci d'elenco sono nodi piatti (`voce`, con livello e marcatore), non
  annidati: Invio, Tab e Backspace restano operazioni su un capoverso; le voci
  consecutive con lo stesso `id` sono un blocco `ELENCO`;
- gli `id` dei blocchi restano unici a ogni modifica (un plugin rinomina i
  duplicati che nascono dividendo o incollando);
- i marcatori delle voci sono calcolati con le regole di `marcatori_elenchi` e
  disegnati fuori dal testo;
- annulla e ripeti restano del builder intero, non della sezione, cosi' che
  anche aggiungere, spostare o rinominare una sezione si annulli;
- un blocco che l'editor non sa modificare (una tabella) resta nel documento
  intatto e non modificabile.

**Alternatives considered**: un `contenteditable` unico gestito a mano -
scartato per la ragione sopra. Syncfusion Document Editor - scartato: licenza
commerciale e un modello documentale proprio (DOCX/SFDT) da riconvertire al
nostro, cioe' l'opposto di un formato chiuso. Un editor per l'intero documento
invece che per sezione - possibile con lo stesso schema, ma la sezione come
unita' e' una scelta di prodotto (riuso futuro), non solo tecnica.

