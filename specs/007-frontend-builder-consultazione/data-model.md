# Phase 1 Data Model: Frontend Builder E Consultazione (MVP ADR 0002)

Il frontend non possiede dati propri: ogni entita' qui sotto e' una proiezione
di uno schema Pydantic gia' reale e testato lato backend (`backend/app/
configurazione/schemas.py`, `backend/app/builder/schemas.py`), i cui tipi
TypeScript vengono generati dagli OpenAPI pubblicati (vedi `research.md`),
non ridefiniti a mano qui. Questo documento fissa solo lo stato UI (view
model, transizioni, validazioni di form) che si aggiunge sopra quei dati.

## Area Admin (FR-021)

### `IntegrazioneAdmin` (proiezione di `IntegrazioneAdmin` backend)

Campi: `id`, `codice`, `nome`, `codice_contesto`, `modalita`, `revisione`,
`url | null`, `timeout_ms`, `stato`, `ultima_verifica | null`
(`{data, revisione, versione_contratto, esito, errori[]}`).

**Stato UI derivato da `stato`** (mai calcolato in autonomia dal frontend,
sempre quello che il backend restituisce):

- `DEFINITO` → badge neutro "Non verificato" (integrazione creata, URL non
  ancora configurato o riconfigurato dopo un cambio che richiede riverifica).
- `CONNESSO` → badge positivo "Connesso", mostra data/ora e versione
  contratto dell'ultima verifica riuscita.
- `ERRORE` → badge di errore, mostra `ultima_verifica.errori` (codice +
  messaggio sanificato, mai uno stack trace: il backend gia' sanifica, la UI
  non deve provare a "arricchire" l'errore con dettagli che non ha).

### Form di creazione (`IntegrazioneCreate`)

Campi richiesti: `codice` (1-100 char), `nome` (1-200 char), `codice_contesto`
(1-64 char). Validazione client-side solo di lunghezza/presenza (UX
immediata); l'unicita' del `codice` resta un controllo server-side
(`409 INTEGRAZIONE_DUPLICATA`) che la UI deve saper mostrare come errore di
form, non come errore generico.

### Form di configurazione (`IntegrazioneUpdate`)

Campi: `revisione_attesa` (letta dall'ultimo fetch, mai inserita a mano
dall'utente - la UI la porta con se' come stato nascosto del form),
`nome`, `url | null`, `timeout_ms` (1000-10000). Un submit con
`revisione_attesa` non piu' corrente MUST mostrare
`409 REVISIONE_SUPERATA` come "qualcun altro ha modificato questa
integrazione, ricarica" e ricaricare lo stato corrente - mai un retry
automatico silenzioso che rischierebbe di sovrascrivere una modifica
concorrente.

### Azione di verifica (`VerificaRequest`)

Un solo campo (`revisione_attesa`, stesso meccanismo del form sopra). La UI
MUST disabilitare il pulsante "Verifica" durante la chiamata (la verifica e'
sincrona lato backend e puo' richiedere fino al `timeout_ms` configurato) e
MUST gestire `409 VERIFICA_IN_CORSO` (un'altra verifica e' gia' in volo) come
stato informativo, non come errore bloccante.

## Area Manager (FR-022/FR-023)

Aggiornamento Contesti 2026-09-18: `ModelloGestioneResponse` estende il modello
con codice_contesto, integrazione_id, created_at e tutte le versioni (numero,
stato, UUID, public_id, data pubblicazione). La lista e' paginata per modelli,
non limitata alle versioni pubblicate, e non dipende dalla discovery online.
Lo stato UI comprende contesto selezionato nel query param, offset, caricamento,
errore di lettura distinto da vuoto, conferma pendente e transizione in corso.
I passi revisione/approvazione/pubblicazione ora avvengono dalla lista, non da
Swagger. La nota sul precedente MVP sotto resta storica per editor/campi.

### `IntegrazioneVisibile` (lista, proiezione di `IntegrazioneVisibile` backend)

Campi: `id`, `codice`, `nome`, `codice_contesto`. Gia' filtrata
server-side per contesto autorizzato (010 T083, T084) - la UI manager non
applica altri filtri di autorizzazione, mostra la lista cosi' com'e'.

### Navigazione struttura live (`StrutturaDisponibileResponse` / lista tipi documento)

Albero a profondita' variabile (tipologia → profilo → campi, o qualunque
forma la sorgente esterna restituisca - **mai assumere una profondita' fissa
lato frontend**, la 010 supporta esplicitamente alberi a profondita' libera).
Stato di caricamento MUST distinguere: caricamento in corso, lista vuota
(nessun tipo documento), `409 INTEGRAZIONE_NON_CONNESSA`, `502`/`504` (errore
di trasporto verso la sorgente esterna) - **mai** presentare un errore di
trasporto come "lista vuota".

### Form creazione modello (`CreaModelloRequest` -> `ModelloResponse`)

Input client: `codice_tipo_documento`, `integrazione_id`, percorso foglia
`percorso_categorizzazione`, `lingua` e `livello_professionale | null`.
`lingua` deve appartenere a `lingue_possibili`; il livello, quando presente,
deve appartenere a `livelli_possibili`. `null` significa tutti i livelli della
foglia. Il client non invia `codice`, `nome` o `variante`.

Output/persistenza `ModelloDocumento`: oltre alla categorizzazione conserva
`lingua` obbligatoria e `livello_professionale` nullable. Codice e nome sono
generati dal backend; variante sempre `STANDARD`. Non esistono tabelle locali
per profili, livelli o lingue.

Identita' funzionale e sostituzione della versione pubblicata corrente:
`tipo_documento_id + percorso_categorizzazione + livello_professionale +
lingua + variante`. Modelli generici/specifici e IT/EN possono coesistere e
non si archiviano reciprocamente.

Raggruppamento UI/catalogo delle edizioni: `integrazione_id +
tipo_documento_id + percorso_categorizzazione + livello_professionale`.
La lingua e' esclusa soltanto dalla chiave di raggruppamento; resta inclusa
nello scope di pubblicazione. Non esiste una colonna `famiglia_modello_id`.

La richiesta di generazione seleziona una sola `modello_versione_id`; non
contiene `bando_inglese`. Il contratto della versione determina tutti i campi
ammessi e obbligatori.

La versione iniziale conserva tutti i campi della foglia, senza filtrarli per
lingua o livello.

**Nessun editor di campi/sezioni in questo MVP**: dopo la creazione del
modello (stato `BOZZA`), la UI mostra l'esito (`ModelloResponse`) e un link
per proseguire da Swagger/API dirette per i passi successivi
(`crea_versione`, `invia_revisione`, `approva`, `pubblica`) - l'editor visuale
per questi passi e la composizione sezioni (FR-011) sono esplicitamente fuori
scope (vedi `plan.md` Summary).

## Stato client-side (non persistito, non un'entita' di dominio)

- Sessione Keycloak (token, ruoli/contesti decodificati solo per abilitare/
  disabilitare azioni in UI - mai per decidere un'autorizzazione).
- Bozza di form non salvata (creazione integrazione, creazione modello) -
  persa al refresh, nessun autosave in questo MVP (spec.md Edge Cases
  "Errore di salvataggio durante modifica bozza" si applica al builder pieno,
  fuori scope qui: qui la creazione e' un'unica submit atomica lato backend).
