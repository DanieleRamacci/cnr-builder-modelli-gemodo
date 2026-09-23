# Tasks: Builder Modelli Documentali

> ## ⚠ RICONCILIAZIONE 2026-09-22 — T001-T064 SUPERATI
>
> **La funzionalita' di questa spec e' in esercizio.** Le caselle non spuntate
> da T001 a T064 descrivono un'**architettura di file** che non e' mai stata
> costruita, non lavoro mancante. Verifica condotta il 2026-09-22 confrontando
> i percorsi citati nei task con il codice su disco ed esercitando le API vere.
>
> **Esito: dei 47 percorsi citati, 35 non esistono.** L'implementazione ha
> adottato un modulo `builder` **piatto** invece della gerarchia pianificata:
>
> | Pianificato (inesistente) | Reale |
> | --- | --- |
> | `builder/api/{modelli,classificazione,pubblicazione,schemas,security}.py` | `builder/api.py`, `builder/schemas.py` |
> | `builder/service/{modelli,versioni,pubblicazione,workflow,audit}.py` | `builder/service.py`, `builder/audit.py` |
> | `builder/repository/{modelli,versioni,pubblicazione}.py` | `builder/repository.py` |
> | `builder/validation/*.py` | dentro `builder/service.py` |
> | migration `0005_builder_admin_workflow.py` | `0005` e' `classificazione_catalogo_geban` |
> | `tests/builder/contract/test_*.py` (8 file) | `tests/builder/test_builder_flow_api.py`, `test_builder_modelli_contract.py` |
>
> **Stato reale per user story:**
>
> | User story | Stato | Prova |
> | --- | --- | --- |
> | US1 — leggere la struttura disponibile | **IMPLEMENTATA** (la *storia* e' stata riscritta, i *task* no) | Attenzione: il titolo della Phase 3 qui sotto, "Configurare tipi e categorie documento", e' la versione **vecchia** della storia. `spec.md` la riscrive il 2026-09-15 in "Leggere la struttura disponibile per un tipo documento connesso", con FR-002 corretto "da gestione a lettura". Nella forma attuale e' implementata: `GET /tipi-documento/{codice}/struttura-disponibile` in `builder/api.py:166`, `service.struttura_disponibile` in `builder/service.py:159`. I task di Phase 3 che creano/scrivono tipi e categorie sono invece **annullati da `010` FR-016**, che ritira repository e API di classificazione: non esiste ne' deve esistere un `POST /api/v1/builder/tipi-documento`. |
> | US2 — gestire modelli e versioni | **IMPLEMENTATA** | `POST /modelli`, `GET /modelli`, `GET /modelli/{id}`, `DELETE /modelli/{id}`, `POST /modelli/{id}/versioni` in `builder/api.py`. Creazione modello esercitata end-to-end il 2026-09-22 contro discovery live. |
> | US3 — pubblicare e archiviare versioni | **IMPLEMENTATA** | `invia-revisione`, `approva`, `pubblica` in `builder/api.py`; tabella di transizione stati in `builder/service.py:37-38`; evento `VERSIONE_ARCHIVIATA` in `service.py:490`. |
> | Policy per dimensione (T065-T072) | **FATTA E SPUNTATA** | Unico blocco scritto contro il codice reale, infatti e' l'unico con le spunte corrette. |
>
> **RISOLTA il 2026-09-22** (`DEC-002-LEDGER-RISCRITTO-DAL-CODICE`): le Phase
> 1-6 sono state riscritte contro la struttura reale e rinumerate T001-T038.
> Il ledger ora dice il vero: **37 fatti, 6 aperti, 3 annullati**. Gli aperti
> sono lavoro genuino, non archeologia:
>
> | Task | Cosa manca davvero |
> | --- | --- |
> | T005 | `backend/app/builder/README.md` |
> | T032 | Route HTTP per `archivia` e `sospendi` (le transizioni esistono nel service, nessun endpoint le espone) |
> | T033 | Validazione di etichette-variante duplicate |
> | T036-T038 | Quickstart, seed di una variante personalizzata, nota di coerenza `001`/`002` in `project-map.md` |

**Input**: Design documents from `specs/002-builder-modelli/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/builder-modelli-api.openapi.yaml`, `quickstart.md`

**Tests**: Include unit, integration and contract tests because the feature defines protected administrative APIs, workflow states, uniqueness constraints, transactional publication and API contracts.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to
- Include exact file paths in descriptions

## Nota Implementazione 2026-09-16 (prima implementazione reale, letta prima di lavorare sui task sotto)

Nella sera del 2026-09-15/16 e' stata implementata una prima verticale reale
(non un prototipo) del builder, verificata su Postgres reale, per sbloccare
il flusso end-to-end "GEBAN genera un documento". Non segue la struttura a
file granulare descritta nei task sotto (`app/builder/api/`, `repository/`,
`service/`, `validation/` come sottopacchetti separati): usa moduli piatti
`backend/app/builder/{api,service,repository,schemas,audit}.py`, funzionalmente
equivalenti ma non file-per-file identici ai task. Chi riprende questi task
deve leggere prima cosa esiste davvero, non assumere che uno stato `[ ]`
significhi "niente scritto" ne' che uno stato `[x]` copra tutto cio' che il
task descrive.

**Reale e testato (`backend/tests/builder/test_builder_flow_api.py`, 7 test,
Postgres reale)**:
- `GET /api/v1/builder/tipi-documento/{codice}/struttura-disponibile` (US1
  riscritta 2026-09-15: sola lettura via `PortaDiscovery`/`AdapterLocale`
  reale, non le vecchie T014-T025).
- `POST /api/v1/builder/modelli`, `POST .../versioni` (US2): crea modello e
  versione, campi validati contro `RegistroContrattiDati` reale (7 campi,
  incluso `livello`).
- `POST .../invia-revisione`, `.../approva`, `.../pubblica` (US3): catena
  completa BOZZA->IN_REVISIONE->APPROVATO->PUBBLICATO, archiviazione
  automatica della precedente versione corrente della stessa variante,
  verificata a livello DB (non solo di risposta HTTP).
- Autorizzazione scoped per contesto (`DEC-001-CONTESTO-SOSTITUISCE-UFFICIO`,
  `verify_scrittura_su_contesto` in `backend/app/common/security.py`): test
  dedicato prova che un ruolo di gestore in un contesto NON autorizza la
  scrittura su un tipo documento di un contesto diverso, anche con lo stesso
  token multi-contesto.
- Fine a fine reale: dopo la pubblicazione, `POST /api/v1/documenti/valida` e
  `POST /api/v1/documenti/genera` (gia' implementati dalla `001`) chiamati
  contro il nuovo modello pubblicato hanno successo, senza modifiche a
  quel codice — prova concreta che l'endpoint di generazione e' davvero
  generico rispetto alla struttura del modello.

**Aggiornamento 2026-09-22**: tre dei gap elencati qui sotto sono stati chiusi
dopo il 2026-09-16 e l'elenco non era stato aggiornato. Chiusi: la bozza
derivata da una pubblicata (FR-006, `POST /modelli/{id}/edizioni-derivate`);
il vincolo **a livello DB** sulla versione pubblicata corrente (l'indice unico
parziale `uq_modello_versione_pubblicata_corrente` esiste fin da `0002`, quindi
la preoccupazione "solo applicativo" era gia' infondata quando fu scritta); il
contratto OpenAPI, oggi presente e verificato da un test. Restano veri: nessuna
route `archivia`/`sospendi`, nessuna validazione di etichette-variante
duplicate, nessun `README.md` di modulo. Vedi T029, T030, T034 e T032, T033,
T005.

**Deliberatamente NON fatto stasera (gap reali, non da assumere coperti)**:
- Nessun endpoint per modificare il contenuto di una versione gia' pubblicata
  ne' per derivare una bozza da una pubblicata (FR-005/FR-006) — esiste solo
  creazione di versioni nuove, l'immutabilita' non e' mai stata messa alla
  prova perche' non c'e' ancora un percorso di scrittura che la violerebbe.
- Nessuna route dedicata `archivia`/`sospendi` (la transizione
  PUBBLICATO->ARCHIVIATO/SOSPESO e' supportata dal service/`TRANSIZIONI_VALIDE`
  ma non ha ancora un endpoint HTTP che la esponga).
- Nessun vincolo **a livello DB** che impedisca due versioni `PUBBLICATO`
  correnti per la stessa variante in scrittura concorrente — solo
  applicativo (lettura-poi-scrivi in `transizione()`); accettabile per
  l'uso di stasera (un operatore alla volta), non per produzione multi-utente.
- Nessuna validazione esplicita di etichette-variante duplicate (Edge Case
  dedicato, non implementato).
- Nessun contratto OpenAPI (`contracts/builder-modelli-api.openapi.yaml` non
  esiste ancora) ne' pubblicazione Swagger/ReDoc per queste route — API
  interna, non ancora documentata come richiesto dal principio II della
  costituzione: da fare prima di qualunque rilascio esterno di queste route.
- Nessun modulo `backend/app/builder/README.md`.

---

## Phase 1: Setup (Shared Infrastructure)

**Riscritta 2026-09-22 dal codice reale** (`DEC-002-LEDGER-RISCRITTO-DAL-CODICE`).
La versione precedente pianificava i sottopacchetti `api/`, `repository/`,
`service/`, `validation/`: non sono mai esistiti. L'implementazione usa moduli
piatti, funzionalmente equivalenti. I task qui sotto descrivono cosa c'e'
davvero, con il percorso vero, e sono spuntati solo dove il file esiste.

- [x] T001 Modulo builder piatto in `backend/app/builder/`: `api.py` (279 righe),
      `service.py` (536), `repository.py` (236), `schemas.py` (149),
      `audit.py` (35), `integrazioni_service.py` (90)
- [x] T002 Test builder in `backend/tests/builder/`: `test_builder_flow_api.py`,
      `test_builder_modelli_contract.py`, `test_integrazioni_manager.py`,
      `test_policy_dimensione.py`
- [x] T003 Router builder montato in `backend/app/main.py` con prefisso
      `/api/v1/builder`
- [x] T004 Contratto OpenAPI in
      `specs/002-builder-modelli/contracts/builder-modelli-api.openapi.yaml`,
      verificato da `backend/tests/builder/test_builder_modelli_contract.py`
- [ ] T005 [P] Documentazione di modulo in `backend/app/builder/README.md`
      (ancora assente; unico elemento della Phase 1 non realizzato)

---

## Phase 2: Foundational (Blocking Prerequisites)

- [x] T006 Persistenza condivisa in `backend/app/catalog/models.py` senza
      tabelle duplicate: `TipoDocumento`, `ModelloDocumento`,
      `ModelloDocumentoVersione`, `ModelloCampoRichiesto`, `PolicyDimensione`,
      `AuditEventoModello`
- [x] T007 Migration del workflow builder: `0002_catalogo_modelli.py` aggiunge
      `variante`, validita', `pubblicato_at` e gli indici unici parziali
      `uq_modello_versione_pubblicata_corrente` (una sola versione
      `PUBBLICATO` per modello) e `uq_modello_documento_public_id`
- [x] T008 Regole di transizione stato in `backend/app/builder/service.py:37`
      (`TRANSIZIONI_VALIDE`: BOZZA -> IN_REVISIONE -> APPROVATO/BOZZA -> ...)
- [x] T009 Schemi Pydantic in `backend/app/builder/schemas.py`
      (`CreaModelloRequest`, `CreaVersioneRequest`, `VersioneResponse`,
      `PolicyDimensione*`, `ModelloDettaglioResponse`, ...)
- [x] T010 Autorizzazione per contesto tramite
      `verify_scrittura_su_contesto` di `backend/app/common/security.py`,
      richiamata da ogni scrittura del service
- [x] T011 Codici errore builder in `backend/app/common/errors.py`
      (`MODELLO_NON_TROVATO`, `CONTESTO_NON_VALIDO`,
      `DIMENSIONE_RICHIEDE_VALORE`, ...)
- [x] T012 Validazione di codici, varianti e identita' modello in
      `backend/app/builder/service.py` (`_slug`, `_identita_modello`)
- [x] T013 Audit dei cambi di stato in `backend/app/builder/audit.py`
      (`registra_evento`) su tabella `audit_evento_modello`

---

## Phase 3: User Story 1 - Leggere la struttura disponibile (Priority: P1)

**Attenzione al titolo storico**: fino al 2026-09-22 questa fase si chiamava
"Configurare tipi e categorie documento". `spec.md` ha riscritto la storia il
2026-09-15 in **sola lettura** (FR-002 corretto "da gestione a lettura"), e
`010` FR-016 ha ritirato repository e API di classificazione. I task di
creazione/modifica di tipi e categorie sono percio' **annullati nel merito**,
non solo mai eseguiti.

- [x] T014 `GET /api/v1/builder/tipi-documento/{codice}/struttura-disponibile`
      in `backend/app/builder/api.py:166`, servita da
      `BuilderService.struttura_disponibile` (`service.py:159`) tramite la
      porta discovery
- [x] T015 `GET /api/v1/builder/integrazioni` e
      `GET /api/v1/builder/integrazioni/{id}/tipi-documento` e `.../struttura`
      in `backend/app/builder/integrazioni_service.py`, filtrate per contesto
      autorizzato e stato CONNESSO
- [x] T016 Lettura limitata ai contesti del token, verificata da
      `test_integrazioni_manager.py::test_manager_sees_only_connected_integrations_authorized_in_their_context`
      e `::test_multicontext_token_does_not_leak_permission_across_contexts`
- [-] T017 ANNULLATO da `010` FR-016: creazione tipo documento dal builder
      (`POST /api/v1/builder/tipi-documento`). Non esiste e non deve esistere
- [-] T018 ANNULLATO da `010` FR-016: gestione categorie/tipologie locali dal
      builder
- [-] T019 ANNULLATO da `010` FR-016: repository di classificazione locale

---

## Phase 4: User Story 2 - Gestire modelli e versioni (Priority: P1)

- [x] T020 `POST /api/v1/builder/modelli` (`api.py:206`,
      `service.crea_modello:206`): risolve il percorso nell'albero discovery,
      applica le policy per dimensione, assegna variante e identita'
- [x] T021 `GET /api/v1/builder/modelli` e `GET /api/v1/builder/modelli/{id}`
      con paginazione e filtro per contesto
- [x] T022 `POST /api/v1/builder/modelli/{id}/versioni`
      (`service.crea_versione:388`) con clonazione dei campi richiesti
- [x] T023 `DELETE /api/v1/builder/modelli/{id}` (`service.elimina:509`):
      eliminazione logica con archiviazione delle versioni pubblicate e audit
- [x] T024 `GET /api/v1/builder/contesti` (`service.contesti:80`) tramite
      `contesti_con_permesso`
- [x] T025 Campi del contratto dati derivati dalla foglia discovery
      selezionata, non da dati locali (FR-003, FR-015)

---

## Phase 5: User Story 3 - Pubblicare e archiviare versioni (Priority: P1)

- [x] T026 `POST .../versioni/{id}/invia-revisione`, `.../approva`,
      `.../pubblica` in `backend/app/builder/api.py:253-279`, servite da
      `service.transizione:450`
- [x] T027 Archiviazione automatica della versione corrente precedente alla
      pubblicazione di una nuova, verificata a livello DB da
      `test_builder_flow_api.py`
- [x] T028 Immutabilita' delle versioni pubblicate: nessun percorso di
      scrittura sul contenuto di una versione `PUBBLICATO` (FR-005)
- [x] T029 `POST /api/v1/builder/modelli/{id}/edizioni-derivate`
      (`api.py:225`, `service.crea_edizione_derivata:294`): bozza derivata da
      una configurazione gia' pubblicata (FR-006). *Chiude il gap dichiarato
      aperto dalla nota del 2026-09-16*
- [x] T030 Al massimo una versione `PUBBLICATO` corrente per modello, imposta
      **a livello DB** dall'indice unico parziale
      `uq_modello_versione_pubblicata_corrente` di `0002` (FR-007).
      *Chiude il gap "solo applicativo" dichiarato dalla nota del 2026-09-16*
- [x] T031 Registrazione di chi crea, approva, pubblica o archivia (FR-008)
      tramite `audit.registra_evento` su `audit_evento_modello`
- [ ] T032 Route HTTP dedicate per `archivia` e `sospendi`: le transizioni
      PUBBLICATO -> ARCHIVIATO/SOSPESO sono ammesse da `TRANSIZIONI_VALIDE` e
      raggiungibili dal service, ma nessun endpoint le espone
- [ ] T033 Validazione esplicita di etichette-variante duplicate
      (Edge Case dedicato in `spec.md`, mai implementato)

---

## Phase 6: Polish & Cross-Cutting Concerns

- [x] T034 Contratto OpenAPI con esempi di successo ed errore, verificato da
      `test_builder_modelli_contract.py`
- [x] T035 Suite builder eseguita su Postgres reale (parte dei 354 test
      backend verdi al 2026-09-22)
- [ ] T036 [P] Aggiornare `specs/002-builder-modelli/quickstart.md` con le
      note di validazione effettive
- [ ] T037 [P] Dati seed per una variante standard e una personalizzata in
      `infra/local/postgres/seed-demo-catalog.yaml`
- [ ] T038 Registrare in `docs/project-map.md` l'esito del controllo di
      coerenza fra `001` e `002` su variante, versione e regole di sicurezza

---


## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies.
- **Foundational (Phase 2)**: depends on setup and blocks all user stories.
- **US1 (Phase 3)**: depends on foundational phase.
- **US2 (Phase 4)**: depends on foundational phase; full validation uses type/category data from US1.
- **US3 (Phase 5)**: depends on US2 version model and services.
- **Polish (Phase 6)**: depends on selected user stories being complete.

### Cross-Spec Dependencies

- `001` supplies the shared catalog model, common errors and JWT validation helpers. If those files are not yet implemented, complete the corresponding `001` foundational tasks before executing the builder runtime tasks.
- `009` supplies decision gate, documentation and demo seed conventions.
- `006` remains the authority for future fine-grained security, but `SEC-006-002` is already confirmed for this feature.

### User Story Dependencies

- **US1**: first productive increment; creates administrative classification APIs.
- **US2**: can start after foundational phase, but final validation depends on US1 entities.
- **US3**: depends on US2 because publication operates on versions.

### Parallel Opportunities

- T004-T005 can run in parallel after T001-T003.
- T008-T009 and T012-T013 can run in parallel during foundation.
- US1 tests T014-T018 can run in parallel.
- US2 tests T026-T031 can run in parallel.
- US3 tests T042-T049 can run in parallel.
- Polish tasks T059-T062 can run in parallel.

## Parallel Example: User Story 2

```text
Task: "Add integration tests for default STANDARD variant"
Task: "Add integration tests for duplicate variant rejection"
Task: "Add unit tests for version mutability and derived draft rules"
Task: "Implement model repository functions"
Task: "Implement version repository functions"
```

## Implementation Strategy

### Primo Incremento Produttivo

1. Complete Phase 1 and Phase 2.
2. Complete US1 to manage document types and categories through protected builder APIs.
3. Validate US1 independently with contract, authorization and integration tests.
4. Add US2 for model/version drafting and immutability.
5. Add US3 for approval, publication and archive workflow.

### Safety Rules

- Do not implement direct reads from GEBAN DB.
- Do not duplicate catalog tables or maintain a separate builder copy of catalog data.
- Do not expose non-`PUBBLICATO` versions to the catalog operative path.
- Do not update published content in place.
- Do not publish a new version without archiving the previous current version of the same variant in the same transaction.
- Do not rely on frontend checks for authorization; protected builder APIs must enforce JWT roles in the backend.


## Phase: Policy per dimensione della categorizzazione (2026-09-22)

**Goal**: rendere configurabile cio' che oggi e' scritto a mano nel codice -
la lingua esige sempre una scelta esplicita, il livello ammette un generico -
cosi' che una dimensione nuova aggiunta da un'integrazione non richieda una
modifica al codice.

**Owner**: `DEC-002-POLICY-DIMENSIONE-CATEGORIZZAZIONE`. Entita', API ed
enforcement vivono qui; la schermata amministrativa 4a/4b vive in `010`
(vedi Clarifications del 2026-09-22 in `010/spec.md`).

**Vincolo non negoziabile**: `PolicyDimensione` MUST restare separata da
`DefinizioneStruttura`/`StrutturaInput` del modulo `configurazione`. Quello e'
solo l'esempio presentazionale per il team GEBAN e non deve mai determinare il
comportamento a runtime.

**Independent Test**: un admin dichiara `consente_valore_generico=false` per
una dimensione nuova; il form di creazione modello smette di offrire "Tutti i
valori" per quella dimensione e due valori diversi producono due modelli
distinti, esattamente come accade oggi per la lingua.

- [x] T065 [P] Test di persistenza per `PolicyDimensione`: chiave logica
      `(tipo_documento_id, nome_dimensione)` unica, una riga sola per nome
      anche quando lo stesso nome ricompare su piu' foglie dell'albero, in
      `backend/tests/builder/test_policy_dimensione.py`
- [x] T066 [P] Test che l'applicazione della policy sostituisce il
      comportamento hardcoded: con `consente_valore_generico=false` la
      creazione senza valore esplicito e' rifiutata, con `true` e' ammessa e
      produce il modello generico; verificare che lingua e livello continuino a
      comportarsi come oggi quando le policy corrispondenti sono registrate, in
      `backend/tests/builder/test_builder_flow_api.py`
- [x] T067 [P] Test che una dimensione priva di policy registrata viene
      segnalata e non silenziosamente ignorata (`NodoDiscovery` ha gia'
      `extra="allow"`), in `backend/tests/discovery/`
- [x] T068 Migration e mapping ORM di `PolicyDimensione` in
      `backend/alembic/versions/` e `backend/app/catalog/models.py`
- [x] T069 API di lettura e scrittura delle policy per tipo documento,
      protetta da `GEMODO_ADMIN` in scrittura e leggibile dal gestore, con
      contratto OpenAPI aggiornato in
      `specs/002-builder-modelli/contracts/builder-modelli-api.openapi.yaml`
- [x] T070 Sostituire i controlli hardcoded su lingua e livello con la lettura
      della policy in `backend/app/builder/service.py` (oggi righe ~169 e ~176)
      e includere la dimensione nello scope di unicita' della pubblicazione
- [x] T071 (lettura `GET /builder/tipi-documento/{codice}/policy-dimensioni` con `dimensioni_non_configurate`; l'aggancio alla verifica endpoint di `010` 5b resta da fare con T093) Esporre le dimensioni prive di policy come segnalazione esplicita
      sia nella lettura della struttura live sia nella verifica dell'endpoint
      (consumata da `010` 4a e 5b)
- [x] T072 Migrazione dei dati esistenti: registrare `lingua=false` e
      `livello=true` per i tipi documento gia' presenti, cosi' che il
      comportamento non cambi al primo deploy

### Note di implementazione (2026-09-22)

- **`lingua` non puo' ammettere un generico**: `modello_documento.lingua` e'
  NOT NULL con vincolo IT/EN (`DEC-001-LINGUA-IT-EN`) ed e' esposta non
  nullabile anche nel catalogo verso GEBAN. Dichiararla generica viene rifiutato
  con `GENERICO_NON_SUPPORTATO` invece di essere accettato e poi salvato con un
  valore arbitrario. Renderla davvero generica richiede una modifica di schema e
  contratto in `001`: decisione non presa, non e' un residuo di questo task.
- **Nessun cambio di comportamento al primo deploy**: la migration `0018`
  registra `lingua=false` e `livello=true` per i tipi esistenti, e il builder
  registra le stesse due policy quando crea un tipo nuovo. Il ripiego in codice
  vale solo per un tipo che non le avesse.
- **Scope di unicita' della pubblicazione**: gia' comprendeva lingua e livello
  (`get_versione_pubblicata_corrente`). Generalizzarlo a dimensioni che non
  siano colonne dedicate richiede il refactor dei valori di dimensione, non
  previsto qui.

## Phase: Correzione difetti di eliminazione (2026-09-22)

- [x] T039 [FR-018] (migration `0019_edizione_derivata_esclude_eliminati.py`) Rendere parziale il vincolo `uq_modello_derivato_padre_lingua`
      (`WHERE stato <> 'ELIMINATO'`) con una migration, allineandolo a
      `get_edizione_derivata` che gia' esclude gli eliminati
- [x] T040 [FR-018] (`builder/service.py`, `IntegrityError` -> 409) Tradurre l'`IntegrityError` residuo su quel vincolo in
      `EDIZIONE_DERIVATA_DUPLICATA` (409), come gia' fa `configurazione/service.py`
      per i duplicati di tipo documento. Copre la corsa fra due richieste
      simultanee, che il solo indice parziale non elimina
- [x] T041 [FR-018] (`backend/tests/builder/test_eliminazione_e_pulizia.py`) Test del ciclo: crea derivata -> elimina -> ricrea la stessa
      lingua -> deve riuscire; e test che due creazioni concorrenti diano 409,
      mai 500

## Phase: Identita' e distinguibilita' dei modelli (2026-09-23)

- [ ] T042 [FR-019] Esporre `variante` in `CreaModelloRequest` e smettere di
      cablare `STANDARD` in `service.crea_modello:280`. Default `STANDARD`
      quando assente, come gia' prevede FR-003a
- [ ] T043 [FR-019] Rifiutare la creazione di un modello sulla stessa
      categorizzazione (tipo, percorso, lingua, livello) quando manca la
      descrizione di variante, con errore funzionale dedicato che dica
      **quale** modello esiste gia': e' il messaggio su cui il frontend
      costruisce la proposta di creare una variante. Rifiutare anche una
      descrizione di variante duplicata sulla stessa categorizzazione. Mai
      lasciare che la pubblicazione archivi in silenzio il modello precedente
- [ ] T044 [FR-019] Includere la variante nel nome generato da
      `_identita_modello`, cosi' che due modelli sulla stessa
      categorizzazione non ricevano lo stesso nome
- [ ] T045 [FR-019] Campo `nota` sul modello: testo libero, opzionale,
      scritto dal gestore, **distinto** da `nome` che resta generato e non
      modificabile. Obbligatorio solo quando il modello nasce come variante.
      Migration piu' campo in creazione e aggiornamento. In
      `_modello_catalogo_schema` il campo `descrizione` diventa `nome` senza
      nota, `nome - nota` con nota: non sostituire `nome` con `nota`
- [ ] T047 [FR-019] Generare il codice di variante lato sistema: il gestore
      fornisce solo la nota, mai il codice. Base `STANDARD`, poi `VARIANTE_1`,
      `VARIANTE_2` progressivi **fra le varianti aggiunte** (la prima variante
      dopo lo standard e' `VARIANTE_1`). Maiuscoli, senza spazi: viaggiano
      verso GEBAN e nei log. La numerazione va calcolata sotto il lock gia'
      preso per tipo documento, altrimenti due creazioni simultanee
      ottengono lo stesso codice
- [ ] T048 [FR-019] `POST /builder/modelli/{id}/varianti`: creare una variante
      a partire da un modello esistente, ereditandone categorizzazione,
      lingua e livello, chiedendo la sola descrizione. Distinta da
      `edizioni-derivate`, che cambia lingua e non variante
- [ ] T046 [P] [FR-019] Test: due modelli stessa categorizzazione varianti
      diverse coesistono pubblicati; stessa variante viene rifiutata; i nomi
      generati sono distinti
