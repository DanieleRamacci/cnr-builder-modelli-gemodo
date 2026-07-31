# Research - Sezioni Placeholder E Versionamento

## Decision: contenuto strutturato controllato

**Rationale**: le sezioni devono supportare documenti amministrativi con paragrafi, titoli,
liste, tabelle semplici e enfasi testuale, ma senza HTML libero. Un formato controllato
riduce rischi di sicurezza, ambiguita' di rendering e contenuti non validabili.

**Alternatives considered**:

- Solo testo semplice: troppo limitato per bandi e documenti amministrativi.
- HTML libero: scartato per rischi di validazione, sicurezza e riproducibilita' PDF.

## Decision: modello documentale `GEMODO_DOCUMENT_V1`

**Rationale**: la decisione confermata e' usare un editor visuale controllato, non un
editor HTML. Il backend salva una struttura versionata con blocchi ammessi, posizionamenti
controllati, asset versionati, stili consentiti e placeholder validati. Il prototipo della
`009` (`infra/local/document-models/` e `backend/app/quality/document_model.py`) diventa il
riferimento iniziale per il contratto della `003`.

**Alternatives considered**:

- HTML/CSS libero salvato dal builder: scartato per sicurezza, audit e riproducibilita'.
- Formato visuale deciso solo dal frontend: scartato perche' la validazione deve essere
  backend e contract-first.
- Template fissi senza struttura visuale: scartato perche' non abilita il builder
  documentale richiesto.

## Decision: sezioni proprie della versione modello

**Rationale**: la versione modello e' l'unita' di storicizzazione operativa. Salvare le
sezioni dentro la versione modello evita doppi livelli di versionamento e garantisce che
un modello pubblicato resti riproducibile senza dipendere da sezioni condivise mutate
successivamente.

**Alternatives considered**:

- Versionamento autonomo delle sezioni: rinviato a valutazione futura se emergera' un vero
  bisogno di libreria centrale versionata.
- Sezioni condivise live tra modelli: scartato perche' una modifica centrale potrebbe
  alterare modelli gia' approvati o pubblicati.

## Decision: template sezione solo copiabile

**Rationale**: una libreria di template puo' accelerare la composizione, ma il contenuto
copiato deve diventare proprieta' della versione modello. Gli aggiornamenti al template non
devono modificare retroattivamente versioni modello esistenti.

**Alternatives considered**:

- Template con riferimento vivo: scartato perche' rompe isolamento e riproducibilita'.
- Nessuna libreria template: possibile, ma meno utile per riusare testi standard.

## Decision: nessuna sezione condizionale nel perimetro corrente

**Rationale**: sezioni condizionali richiedono editor di regole, validazione aggiuntiva e
rendering piu' complesso. Il perimetro corrente mantiene sezioni sempre presenti quando
inserite nel modello.

**Alternatives considered**:

- Regole semplici su campi del payload: rinviate per evitare complessita' anticipata.
- Espressioni avanzate configurabili: scartate per questa fase.

## Decision: coerenza placeholder verificata alla pubblicazione

**Rationale**: il contratto dati deriva dai campi associati alla versione modello, non dal
testo delle sezioni. Prima della pubblicazione il backend deve comunque confrontare i
placeholder usati nel contenuto con quelli disponibili, cosi' da bloccare errori di
digitazione, contenuti copiati da altri modelli o dati incoerenti.

**Alternatives considered**:

- Fidarsi solo del frontend editor: scartato perche' API, import o bug possono introdurre
  contenuti incoerenti.
- Calcolare il contratto dati dai placeholder nel testo: scartato perche' il contratto deve
  restare esplicito e gestito dal builder.

## Decision: campi complessi con schema esplicito

**Rationale**: campi come liste di sedi, requisiti o tabelle non possono essere JSON libero.
GEBAN deve sapere quali sotto-campi mostrare e il backend deve poter validare tipi,
obbligatorieta' e vincoli.

**Alternatives considered**:

- JSON libero generico: scartato perche' non supporta maschere dinamiche affidabili.
- Solo campi semplici: troppo limitato per documenti reali.

## Decision: API `003` protette con ruoli builder

**Rationale**: sezioni, placeholder e schema campi complessi modificano il contenuto dei
modelli pubblicabili. Le API devono quindi usare lo stesso confine Keycloak della `002`:
letture con `GEMODO_MODELLI_VIEWER` o `GEMODO_MODELLI_GESTORE`, scritture e validazioni
di pubblicazione con `GEMODO_MODELLI_GESTORE`.

**Alternatives considered**:

- Demandare l'autorizzazione al frontend: scartato perche' viola la costituzione.
- Proteggere solo la pubblicazione: scartato perche' anche la composizione della bozza
  modifica configurazioni amministrative.
