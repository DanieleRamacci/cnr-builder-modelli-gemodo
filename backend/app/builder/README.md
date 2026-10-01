# Modulo `builder`

Il lato di chi **compone** i modelli: crearli sulla categorizzazione scoperta
dall'integrazione, scriverne il corpo, vederne l'anteprima, portarli in
revisione e pubblicarli. La **generazione** dei documenti non sta qui
(`app/generazione`), e nemmeno la configurazione delle integrazioni
(`app/configurazione`).

Spec di riferimento: `002-builder-modelli` (modelli, versioni, varianti),
`003-sezioni-placeholder-versionamento` (corpo del documento),
`011-dimensioni-generiche-modello` (dimensioni), `012-editor-documento-fedele`
(formato a frammenti, anteprima), `007` (profilo, FR-034).

## File

| File | Contenuto |
|---|---|
| `api.py` | rotte `/api/v1/builder/*`; nessuna regola di dominio, solo HTTP |
| `service.py` | `BuilderService`: tutte le regole e tutte le autorizzazioni per contesto |
| `repository.py` | accesso ai dati; `composizione_documentale`, `inizi_sezione`, `cornice_del_tipo` per la resa |
| `schemas.py` | richieste e risposte delle rotte |
| `integrazioni_service.py` | integrazioni visibili al gestore (lettura, solo CONNESSE e del suo contesto) |
| `audit.py` | `registra_evento`: un evento per ogni creazione e transizione |

## Rotte

| Rotta | Cosa fa |
|---|---|
| `GET /profilo` | contesti, ruoli e permessi dell'utente, calcolati con la mappatura vera |
| `GET /contesti` | i contesti in cui l'utente può gestire modelli |
| `GET /integrazioni`, `.../tipi-documento`, `.../struttura` | cosa offre l'integrazione connessa |
| `GET /tipi-documento/{codice}/struttura-disponibile`, `/policy-dimensioni` | albero e policy per il form di creazione |
| `GET/POST /modelli`, `GET /modelli/filtri`, `GET/DELETE /modelli/{id}` | elenco, creazione, dettaglio, eliminazione |
| `POST /modelli/{id}/varianti`, `/edizioni-derivate`, `/versioni` | varianti, edizioni collegate, versioni nuove |
| `GET/PUT /modelli/{id}/versioni/{id}/sezioni` | il corpo del documento |
| `POST /modelli/{id}/versioni/{id}/anteprima` | il PDF della bozza con valori fac-simile |
| `POST .../invia-revisione`, `/approva`, `/pubblica`, `/sospendi`, `/archivia` | ciclo di vita |
| `GET/PUT /integrazioni/{id}/tipi-documento/{codice}/cornice`, `GET/PUT/DELETE .../cornice/logo` | intestazione, piè di pagina e logo del tipo documento (gestore del contesto o admin) |
| `GET /modelli/{id}/cornice` | la cornice che il modello eredita, per la scheda "Pagina" dell'editor |

Contratto: `specs/002-builder-modelli/contracts/builder-modelli-api.openapi.yaml`.
`tests/builder/test_builder_modelli_contract.py` verifica che il contratto
descriva solo rotte che esistono: una rotta nuova entra con il suo contratto.

## Regole che non vanno rotte

- **L'autorizzazione è per contesto, mai sull'unione dei contesti del token**
  (DEC-001-CONTESTO-SOSTITUISCE-UFFICIO). Ogni scrittura passa da
  `verify_scrittura_su_contesto` con il contesto del tipo documento, che si
  conosce solo dopo averlo letto: per questo il controllo sta nel servizio e
  non nella rotta.
- **Una versione appartiene al modello indicato nell'URL**
  (`_versione_del_modello`): senza, conoscere un id di versione darebbe
  accesso a modelli di altri contesti.
- **Il corpo si modifica solo in `BOZZA`** (002 FR-005). Dopo, `PUT .../sezioni`
  risponde 409. Le transizioni ammesse sono in `TRANSIZIONI_VALIDE`.
- **`PUT .../sezioni` sostituisce l'insieme intero**, non una sezione: il
  riordino arriva in un colpo solo.
- **Il testo è a frammenti** (012). Il markup è rifiutato con
  `MODELLO_DOCUMENTALE_NON_VALIDO`, mai ripulito. Le regole sono in
  `app/quality/document_model.py`; la forma è descritta in
  `docs/formato-documentale.md`.
- **L'anteprima non è una generazione** (012 FR-010). `BuilderService.anteprima`
  usa solo il renderer e non importa lo storage: niente documento registrato,
  niente idempotenza, niente audit. Non trasformarla in un parametro di
  `GenerazioneDocumentiService.genera`.
- **La cornice è del tipo documento, non del modello.** La scrivono il gestore
  del contesto dell'integrazione e l'amministratore
  (`IntegrazioniService._mappa_live(..., consenti_gestore=True)`). Il logo si
  conserva solo ricodificato (`app/documentale/logo.py`): mai il file ricevuto.
- **Il profilo è la fonte dei permessi per l'interfaccia** (007 T115). Se cambia
  la mappatura ruoli -> permessi, l'interfaccia la segue senza modifiche; non
  ricostruire regole sui ruoli nel frontend.

## Test

Tutti su PostgreSQL reale (Testcontainers) e via HTTP. I principali:
`test_builder_flow_api.py` (fixture comuni, creazione e ciclo di vita),
`test_sezioni_*.py`, `test_formato_frammenti.py`, `test_anteprima_api.py`,
`test_profilo_api.py`, `test_varianti_modello.py`, `test_dimensioni_generiche.py`.
Il percorso completo dall'interfaccia è `frontend/e2e/builder-lifecycle.spec.ts`.
