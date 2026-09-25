# Tasks: Dimensioni Generiche Del Modello

**Input**: Design documents from `/specs/011-dimensioni-generiche-modello/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

**Tests**: inclusi. La spec definisce un **Independent Test** per ogni user story
e il quickstart sette scenari eseguibili: i test non sono un extra, sono il modo
in cui queste storie si dichiarano finite.

**Organization**: raggruppati per user story. Le tre P1 sono in sequenza
obbligata per dipendenza tecnica, non per preferenza.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: parallelizzabile (file diversi, nessuna dipendenza)
- **[Story]**: US1..US5, o CONV per i conflitti trasversali

## Regola che vale per tutti i task

`backend/app/configurazione/service.py` (`_dimensioni_catalogo`) e
`backend/app/discovery/schemas.py` (`NodoDiscovery`) sono **gia' generici** e
**non vanno toccati**. Riconoscono qualunque dimensione grazie a `extra="allow"`.
Se un task sembra richiedere una modifica li', il task e' sbagliato.

**Prima eccezione dichiarata**: `configurazione/service.py:351`, dove il nome
della dimensione derivata da `livelli_possibili` passa da `livello` a
`livello_professionale` (T054). E' un rinomino, non un cambio di meccanismo.

**Seconda eccezione, scoperta implementando (2026-09-23)**: la regola qui sopra
era **sbagliata su `discovery/schemas.py`**. `extra="allow"` rende generica la
*lettura* delle dimensioni nuove, non la loro **validazione**:
`NodoDiscovery.verifica_struttura` rifiutava con `DISCOVERY_NON_CONFORME` ogni
foglia priva di `lingue_possibili`, quindi il tipo documento `CONTRATTI` - il
caso portante della spec - non poteva nemmeno entrare nel sistema. Era l'ultimo
privilegio della lingua, e stava **fuori da `builder/`**, dove il criterio di
successo di T053 cerca con il grep. Rimosso da T055.

---

## Phase 1: Setup

**Purpose**: l'albero con una dimensione mai vista, senza il quale nessuna storia
e' verificabile davvero.

- [x] T001 [P] Aggiungere al mock discovery un tipo documento `CONTRATTI` con
  foglia che dichiara `area_geografica: ["NORD", "CENTRO", "SUD"]`, **senza**
  `lingue` e **senza** `livelli_possibili`. E' il caso portante della spec:
  serve che arrivi da una risposta live, non da una fixture di test, altrimenti
  si verifica il mock invece del meccanismo.
  **Fatto in `infra/local/discovery-mock/discovery.json`**, non in
  `mock-geban/`: quest'ultimo e' lo scenario runner del flusso di generazione,
  mentre l'albero discovery e' servito dal mock nginx di `infra/local/`. I test
  di `tests/builder/test_dimensioni_generiche.py` **leggono quel file** e lo
  servono da un server HTTP reale, cosi' che il vincolo «risposta live, non
  fixture» regga anche in automatico.
- [x] T002 [P] Predisporre in `backend/tests/support/` un fixture PostgreSQL con
  modelli pubblicati **e documenti generati collegati**, da usare come stato di
  partenza della verifica di migrazione (T006). Senza documenti generati, FR-007
  non e' verificabile.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: FR-001 e FR-007. **Blocca ogni altra fase.** Senza un posto dove
scrivere il valore non c'e' nulla da far rispettare ne' da distinguere.

- [x] T003 [FR-001] In `backend/app/catalog/models.py`, su `ModelloDocumento`:
  aggiungere `dimensioni: Mapped[dict[str, str]] = mapped_column(JSONB,
  nullable=False, default=dict)`, rimuovere le colonne `lingua` e
  `livello_professionale`, rimuovere `CheckConstraint
  ck_modello_documento_lingua`, aggiungere
  `Index("ix_modello_documento_dimensioni", "dimensioni", postgresql_using="gin")`.
  Lasciare `variante` invariata (FR-012) e `uq_modello_documento_tipo_codice`
  invariato: e' la rete di sicurezza di FR-003.
- [x] T004 [FR-007] Scrivere `backend/alembic/versions/0020_dimensioni_modello.py`
  negli otto passi di [data-model.md](data-model.md#migrazione-0020): add column
  → popolamento → indice GIN → drop constraint → drop columns → `valore_default`
  su `policy_dimensione` → rinomina `livello` in `livello_professionale` (T054)
  → popolamento dei default che conservano il comportamento odierno
  (`lingua → 'IT'`, `livello_professionale → NULL`). Regola di popolamento delle
  dimensioni: `lingua` sempre presente; `livello_professionale` NULL **non**
  produce la chiave.
- [x] T004b [FR-007] **Verificare prima del deploy** se i modelli esistenti
  vanno conservati o cancellati. L'utente ha indicato che puo' cancellarli e
  ripartire pulito, il che chiuderebbe anche la convivenza fra i due stili di
  nome (T008). **Condizione da controllare**: che non esistano **documenti gia'
  generati** collegati a quei modelli — il legame documento → modello e'
  tracciabilita' richiesta dalla Constitution IV, e cancellare il modello lo
  spezzerebbe. Se sono tutti di prova, via libera. La migration va comunque
  scritta e testata (T006): girera' su qualunque cosa esista al momento.
  **Decisione 2026-09-25**: l'ambiente e' dev e l'utente conferma che documenti
  e modelli esistenti possono essere cancellati tutti. La cancellazione puo'
  essere eseguita dall'utente come reset dati pre-deploy; non cambia il codice e
  non elimina l'obbligo di mantenere testata la migration.
- [x] T005 [FR-007] Downgrade simmetrico nella stessa migration, e **docstring
  che dichiara la perdita**: un modello che valorizza dimensioni diverse da
  lingua e livello perde quei valori nel downgrade. Va scritto li', non scoperto
  dopo.
- [x] T006 [FR-007] Integration test su **PostgreSQL reale** in
  `backend/tests/integration/`: partendo dal fixture di T002, dopo `upgrade`
  verificare che `codice` e `nome` siano **identici**, le versioni pubblicate
  ancora `PUBBLICATO`, i documenti generati ancora collegati, e `dimensioni`
  popolato senza chiave `livello_professionale` dove la colonna era NULL. Poi
  `downgrade` e ricontrollo. **Non SQLite**: la feature poggia su uguaglianza e
  GIN su JSONB, un test su SQLite non prova nulla. Vedi anche `010/T073`.
- [x] T007 [FR-001] In `backend/app/builder/repository.py`, aggiornare
  `crea_modello` e le funzioni che leggono/scrivono le due colonne rimosse per
  passare da e verso `dimensioni`.

- [x] T055 [FR-005] [FR-006] **Rilassare il contratto discovery: la lingua non e'
  piu' obbligatoria sulla foglia** (deciso dall'utente il 2026-09-23, scoperto
  implementando i test di US5). In `backend/app/discovery/schemas.py`,
  `NodoDiscovery.verifica_struttura`: rimuovere «La foglia deve dichiarare almeno
  una lingua possibile», che rendeva non conforme l'intera risposta discovery di
  un tipo documento senza lingua. Allineare
  `specs/010-configurazione-cataloghi-integrazioni/contracts/geban-discovery-endpoint.openapi.yaml`
  (`lingue_possibili` opzionale, `info.version` a `0.6.0`) e
  `VERSIONE_CONTRATTO_DISCOVERY`. **E' un rilassamento**: ogni albero valido con
  la `0.5.0` resta valido e nessuna integrazione deve cambiare nulla, quindi non
  blocca il rilascio come farebbe una modifica rompente. **Senza questo task
  US5 e' impossibile**, non difficile: il tipo documento `CONTRATTI` non poteva
  entrare nel sistema. Deroga alla regola in testa a questo documento.
  **L'enum `IT`/`EN` su `lingue_possibili` e su `CampoDiscovery.lingua` resta**:
  toglierlo e' una decisione separata, non richiesta da US5.

**Checkpoint**: lo schema regge, i dati esistenti sono passati senza perdite.

---

## Phase 3: User Story 1 - Registrare il valore di una dimensione qualsiasi (P1)

**Goal**: due modelli che differiscono per una dimensione nuova sono davvero due
modelli diversi.

**Independent Test**: [quickstart.md](quickstart.md) Scenario 1.

- [x] T008 [US1] [FR-003] Riscrivere `_identita_modello` in
  `backend/app/builder/service.py:52`: comporre codice e nome dai valori di
  `dimensioni` presenti, **in ordine alfabetico di nome dimensione**, usando il
  valore grezzo. Eliminare `"Italiano"`, `"Inglese"`, `"Tutte le lingue"`,
  `"Livello X"`, `"Tutti i livelli"`. Vedi DEC-011-IDENTITA-SENZA-NOMI-CABLATI.
- [x] T009 [US1] In `backend/app/builder/schemas.py`, `CreaModelloRequest`:
  aggiungere `dimensioni: dict[str, str]` con validazione «nessun valore `null`,
  nessuna stringa vuota». Mantenere `lingua` e `livello_professionale` come
  campi di transizione **equivalenti** alle chiavi corrispondenti; indicare lo
  stesso nome due volte con valori diversi e' un errore, non una precedenza.
  Contratto: [builder-modelli-dimensioni.openapi.yaml](contracts/builder-modelli-dimensioni.openapi.yaml).
- [x] T010 [US1] In `backend/app/builder/repository.py`, riscrivere i filtri di
  `lista_modelli` (righe ~30-63) e `voci_filtro` (~120-135) da `DISTINCT` su
  colonna a `jsonb_each_text` / `dimensioni @> ...`. E' il costo accettato di
  DEC-011-PERSISTENZA-DIMENSIONI, circoscritto a questo file.
- [x] T011 [US1] [V] Estendere il payload minimo dell'evento `MODELLO_CREATO` in
  `crea_modello` con le dimensioni valorizzate. **Senza questo l'audit perde
  un'informazione che oggi ricava dalle colonne** — Constitution V.
- [x] T012 [US1] [FR-011] In
  `frontend/src/features/builder/modello-crea.component.ts`: il form genera un
  controllo per dimensione dichiarata dalla foglia e preseleziona
  `policy.valore_default` quando c'e', nulla quando e' `NULL`. Rimuovere
  `presetLingua`, che oggi cabla la lingua. Vedi DEC-011-DEFAULT-DIMENSIONE.
- [x] T012b [US1] [FR-011] Aggiungere `valore_default: str | None` a
  `PolicyDimensione` (`backend/app/catalog/models.py`), esporlo su
  `policy-dimensioni` e aggiungere il controllo nella schermata Dimensioni,
  accanto alla scelta della policy che gia' esiste. Un valore non piu' presente
  nell'albero live va **segnalato**, non cancellato (stesso principio di FR-009).
- [x] T013 [US1] [P] Test di integrazione in `backend/tests/builder/`: due
  modelli sulla stessa foglia che differiscono solo per `area_geografica`
  esistono entrambi, con **codici e nomi distinti**, e rileggono il proprio
  valore.
- [x] T014 [US1] [P] [FR-009] Test: rimossa `area_geografica` dall'albero live,
  i modelli che la valorizzano restano leggibili e restituiscono il proprio
  valore; il disallineamento e' **segnalato in lettura**, non corretto in
  silenzio. Scenario 7 del quickstart.
  Il dettaglio espone `dimensioni_non_disponibili`; l'elenco resta una lettura
  paginata senza chiamate discovery aggiuntive.
- [x] T015 [US1] [P] [FR-011] Unit test Angular in
  `modello-crea.component.spec.ts`: la preselezione proviene da
  `valore_default`, **mai** dall'ordine dell'albero. Il test deve **riordinare i
  valori** nella risposta discovery e verificare che la preselezione non cambi.
  E' l'unica forma che prova davvero FR-011: verificare che esca `IT` non
  distingue «default dichiarato» da «primo dell'elenco».

**Checkpoint**: US1 verificabile da sola.

---

## Phase 4: User Story 2 - Far rispettare la policy di ogni dimensione (P1)

**Goal**: dichiarare una policy smette di essere un gesto senza effetto.

**Independent Test**: [quickstart.md](quickstart.md) Scenario 2.

- [x] T016 [US2] [FR-002] In `backend/app/builder/service.py`, `crea_modello`:
  sostituire le **due chiamate letterali** a `_verifica_dimensione` con un ciclo
  sulle policy registrate per il tipo documento, incrociate con le dimensioni
  dichiarate dalla foglia. L'errore resta `DIMENSIONE_RICHIEDE_VALORE`, **lo
  stesso** usato oggi per lingua e livello: US2 chiede parita' di trattamento,
  non un errore nuovo.
- [x] T017 [US2] [FR-006] Rifiutare con `DIMENSIONE_NON_DICHIARATA` (400) una
  chiave di `dimensioni` che la foglia scelta non dichiara. Nuovo codice di
  errore: va nel catalogo errori (T048).
- [x] T018 [US2] [FR-005] Sostituire `_dimensioni_note`
  (`backend/app/builder/service.py:131`, oggi `return {"lingua", "livello"}`)
  con la derivazione da policy registrate + albero live. **La funzione sparisce**,
  non cambia corpo: `_dimensioni_catalogo` in `configurazione/service.py` fa gia'
  questo lavoro ed e' la fonte da riusare.
- [x] T019 [US2] Valutare `POLICY_DI_RIPIEGO`
  (`backend/app/builder/service.py:108`). **Resta**, ma solo come ripiego per un
  tipo documento privo di policy registrata — e' il comportamento che la
  migration `0018` ha gia' scritto per i tipi esistenti, quindi toglierlo
  cambierebbe il comportamento al deploy. Non e' enforcement cablato: e' un
  default di configurazione. Documentarlo nel codice perche' non venga scambiato
  per un residuo da rimuovere.
- [x] T020 [US2] [P] Test: registrata una policy `consente_valore_generico=false`
  su `area_geografica`, la creazione che la omette viene rifiutata con
  `DIMENSIONE_RICHIEDE_VALORE`; portata a `true`, la stessa creazione riesce con
  `dimensioni: {}`.
- [x] T021 [US2] [P] Test: una chiave non dichiarata dalla foglia produce
  `DIMENSIONE_NON_DICHIARATA`.

**Checkpoint**: la policy vale per qualunque dimensione.

---

## Phase 5: User Story 3 - Distinguere e pubblicare senza collisioni (P1)

**Goal**: due modelli che differiscono per una dimensione nuova restano entrambi
pubblicati.

**Independent Test**: [quickstart.md](quickstart.md) Scenario 3.

- [x] T022 [US3] [FR-004] [FR-012] Riscrivere `get_versione_pubblicata_corrente`
  (`backend/app/builder/repository.py:314`): il filtro passa da cinque colonne a
  `(tipo_documento_id, percorso_categorizzazione, variante, dimensioni)`, con
  `dimensioni` confrontato per **uguaglianza JSONB**. `variante` resta un termine
  **distinto** — FR-012, i due assi non si fondono.
- [x] T023 [US3] Aggiornare i chiamanti della firma cambiata (`lingua=`,
  `livello_professionale=` → `dimensioni=`) nel servizio di pubblicazione.
- [x] T024 [US3] [P] Test: due modelli pubblicati che differiscono solo per
  `area_geografica` **coesistono** entrambi in `PUBBLICATO`.
- [x] T025 [US3] [P] Test complementare, che l'unicita' non sia stata
  disattivata: una seconda versione **dello stesso modello** archivia ancora la
  precedente. Senza questo, T024 passerebbe anche con il controllo rotto.
- [x] T026 [US3] [P] Test: due creazioni simultanee sulla stessa combinazione di
  dimensioni (edge case della spec).
  **La premessa originale era falsa** e il task e' stato riscritto il
  2026-09-23: diceva «non producono due modelli gemelli —
  `uq_modello_documento_tipo_codice` deve intercettarlo», ma quel vincolo **non
  puo'** intercettarli, perche' `codice` termina con l'esadecimale dell'id del
  modello e due creazioni identiche producono comunque codici diversi. Non e'
  una regressione di 011: valeva gia' prima, con le due colonne. La protezione
  reale e' a valle, sullo **slot di pubblicazione** (FR-004): il gemello che
  pubblica per secondo archivia la versione del primo, quindi il catalogo non
  espone mai due versioni correnti sulla stessa combinazione. E' quella la
  proprieta' che il test blocca. Se invece si vuole impedire la **creazione**
  del gemello, serve un vincolo nuovo su `(tipo_documento_id, percorso,
  variante, dimensioni)` fra i modelli non eliminati: e' una decisione aperta,
  non un residuo di questa fase.

**Checkpoint**: le tre P1 sono chiuse. **Questo e' l'MVP**: chiude la domanda da
cui la spec nasce, tranne il caso `contratti` end-to-end.

---

## Phase 6: User Story 4 - La lingua smette di essere privilegiata (P2)

**Goal**: la regola della lingua e' una scelta configurata, non una costante.

**Independent Test**: [quickstart.md](quickstart.md) Scenari 5 e 5b.

- [x] T027 [US4] [FR-008] In `backend/app/catalog/schemas.py`,
  `ModelloCatalogoSchema`: aggiungere `dimensioni: dict[str, str]`, rendere
  `lingua` **nullable**, conservare `livello_professionale`. `lingua` e
  `livello_professionale` diventano proiezioni di `dimensioni`, non informazioni
  separate. Contratto:
  [catalogo-modelli-dimensioni.openapi.yaml](contracts/catalogo-modelli-dimensioni.openapi.yaml).
- [x] T028 [US4] [FR-010] Riscrivere il fallback in
  `backend/app/catalog/service.py:74-88`: da `if livello_professionale is not
  None` a un ciclo sulle dimensioni richieste la cui policy ha
  `consente_valore_generico = true`, **una alla volta, in ordine alfabetico**,
  fermandosi al primo risultato non vuoto. Vedi
  DEC-011-FALLBACK-GOVERNATO-DA-POLICY.
- [x] T029 [US4] Aggiungere `dimensioni_con_fallback: list[str]` a
  `ModelloSearchResponse`, conservando `fallback_applicato`,
  `livello_richiesto` e `livello_risolto`. Con piu' dimensioni generiche il
  booleano da solo non dice piu' cosa e' successo.
- [x] T030 [US4] In `backend/app/catalog/api.py`, accettare
  `?dimensione[nome]=valore` (deepObject) come forma generale, conservando
  `lingua` e `livello_professionale` come parametri equivalenti.
- [x] T031 [US4] **Rimuovere** `BuilderService.DIMENSIONI_SENZA_GENERICO` e il
  rifiuto `GENERICO_NON_SUPPORTATO` in `imposta_policy_dimensione`. Il codice di
  errore esce dal catalogo: va registrato come rimozione (T048).
- [x] T032 [US4] In
  `frontend/src/features/configurazione/dimensioni.component.html:166`,
  rimuovere `[disabled]="dimensione.nome === 'lingua'"` e la classe
  `[class.disabled]` corrispondente. Il flag passa all'admin.
- [x] T033 [US4] Aggiungere in `dimensioni.component.ts`/`.html` l'avviso
  **calcolato dai dati** prima di salvare una policy su «consente il generico»:
  quanti modelli pubblicati valorizzano la dimensione e se il catalogo la espone.
  **Sorgente dei conteggi**: estendere la risposta di
  `GET /api/v1/builder/tipi-documento/{codice}/policy-dimensioni` con, per ogni
  dimensione, `modelli_pubblicati_che_la_valorizzano: int`. Calcolarlo lato
  backend con una query su `dimensioni` (l'indice GIN di T003 la serve), **non**
  lato client scaricando i modelli: il conteggio deve valere su tutto il tipo
  documento, non sulla pagina corrente. Aggiornare di conseguenza il contratto
  [builder-modelli-dimensioni.openapi.yaml](contracts/builder-modelli-dimensioni.openapi.yaml).
  **Non deve conoscere la parola `lingua`**: e' il punto dell'intera decisione.
  Il testo descrive la conseguenza reale — il catalogo potra' restituire un
  modello che non valorizza la dimensione a una richiesta che chiede un valore
  preciso — non «non potrai piu' generare l'inglese», che sarebbe falso.
- [x] T034 [US4] [FR-013] [FR-014] Generalizzare la derivazione dalla lingua
  alla dimensione. In `backend/app/builder/repository.py:278`,
  `get_edizione_derivata(origine_id, lingua)` →
  `(origine_id, nome_dimensione, valore)`; in `crea_edizione_derivata`, il
  confronto `request.lingua == origine.lingua` diventa generico sul valore della
  dimensione scelta. Vincolo unico da `(derivato_da_modello_id, lingua)` a
  `(derivato_da_modello_id, nome_dimensione, valore)`.
  **`_raggruppa_edizioni` (`catalog/service.py:155`) NON si tocca**: lavora gia'
  solo su `derivato_da_modello_id`.
- [x] T034b [US4] [FR-014] La funzione «crea edizione collegata» e' **offerta**
  solo dove esiste una dimensione con `consente_valore_generico = false` di cui
  la foglia dichiara almeno due valori. Dove non esiste, il pulsante **non
  compare**: non e' un errore da gestire. Deriva dalla policy, mai da un elenco
  di nomi nel codice.
- [x] T034c [US4] [FR-014] Quando i candidati sono piu' di uno, **chiedere**:
  quale dimensione (se piu' d'una e' obbligatoria e multivalore) e quale valore
  (se le alternative al valore di origine sono piu' d'una). **Per il bando oggi
  non si chiede nulla**: unica dimensione obbligatoria `lingua`, due valori,
  quindi da `IT` l'unica alternativa e' `EN` — comportamento identico a oggi. La
  domanda serve al caso, richiesto dall'utente, di piu' di due lingue.
- [x] T034d [US4] [P] Test: su BANDO con IT/EN il flusso e' identico a oggi e
  non pone domande; aggiunta una terza lingua, chiede quale derivare; su un tipo
  documento senza dimensioni obbligatorie la funzione non e' offerta.
- [x] T035 [US4] [P] Test del rischio, il piu' importante di questa fase: con le
  policy di default, `GET /catalogo/modelli?lingua=EN` senza modello inglese
  **non** ripiega sul generico. Poi, portata la policy della lingua a `true`, il
  fallback **scatta** — verificando che sia la policy a governare, non il nome.
- [x] T036 [US4] [P] Unit test Angular: l'avviso compare anche su
  `area_geografica`, con i numeri di quella dimensione. Se comparisse solo per la
  lingua, sarebbe un nome cablato con un'interfaccia intorno.

- [x] T054 [US4] **Uniformare il nome a `livello_professionale`** (deciso
  dall'utente il 2026-09-23; l'alternativa «dichiarare una deroga» e' scartata).
  La prima stesura chiamava la dimensione `livello` nelle policy
  (`PolicyDimensione.nome_dimensione`, chiave di `dimensioni` e
  `POLICY_DI_RIPIEGO`), mentre la colonna rimossa e il campo di contratto si
  chiamano `livello_professionale`. Tenere i due nomi cablerebbe la traduzione
  fra `livello` e `livello_professionale` in `ModelloCatalogoSchema`,
  reintroducendo in piccolo il problema che la spec elimina. Da allineare:
  righe `PolicyDimensione` esistenti (migration `0020` passo 7), popolamento di
  T004, `POLICY_DI_RIPIEGO`, contratto, **e**
  `backend/app/configurazione/service.py:351`, che deriva oggi il nome `livello`
  da `livelli_possibili`. Quest'ultimo e' **l'unico punto** in cui quel file va
  toccato, in deroga alla regola generale in testa a questo documento.
  **Da fare prima di T027**, che altrimenti scrive la mappatura cablata.

**Checkpoint**: nessuna dimensione governa comportamento per nome. Fuori dal
criterio resta il solo `POLICY_DI_RIPIEGO` (T019), che non governa
comportamento ma fornisce il valore iniziale di una configurazione.

---

## Phase 7: User Story 5 - Un tipo documento con dimensioni proprie (P2)

**Goal**: il caso portante della spec, end-to-end.

**Independent Test**: [quickstart.md](quickstart.md) Scenario 4.

- [x] T037 [US5] [FR-006] Test e2e contro il mock di T001: creato un modello
  `CONTRATTI`, il record in `modello_documento` ha
  `dimensioni = {"area_geografica": "NORD"}` e **nessuna chiave `lingua`**.
  Verificare sul database, non solo sulla risposta API.
- [x] T038 [US5] [FR-008] Test: `GET /catalogo/modelli?tipo_documento=CONTRATTI`
  restituisce il modello con `lingua: null` e le sue dimensioni.
- [x] T039 [US5] **Controprova obbligatoria**:
  `GET /catalogo/modelli?tipo_documento=BANDO` restituisce ogni modello con
  `lingua` **presente e valorizzata**, come prima. E' la proprieta' su cui
  poggia DEC-011-CONTRATTO-GEBAN-ADDITIVO: il campo e' nullable nello schema ma
  mai nullo per le richieste che GEBAN fa oggi.
- [x] T040 [US5] Test: creare un'edizione derivata su un modello `CONTRATTI`
  fallisce con errore funzionale leggibile (verifica applicata di T034).
- [x] T041 [US5] [P] Playwright: percorso completo dall'interfaccia — registra
  integrazione, scopri `CONTRATTI`, configura la policy di `area_geografica`,
  crea due modelli, pubblicali entrambi.
  Chiuso 2026-09-24: `frontend/e2e/dimensioni-generiche.spec.ts`, **eseguito su
  stack reale** (Keycloak locale :8081, postgres :55432, backend :8003,
  discovery-mock :9100, `ng serve` :4202). Il test attraversa tutto il
  percorso e verifica le proprieta' della spec dall'interfaccia: nessun campo
  lingua sulla foglia `CONTRATTI` (FR-006), nomi generati diversi fra NORD e
  CENTRO (FR-003), entrambi i modelli `PUBBLICATO` a fine corsa - il secondo
  non archivia il primo (FR-004).
  **Due difetti trovati dall'esecuzione**, entrambi corretti con test unitario
  di regressione (verificato che fallisce senza la correzione):
  1. `modello-crea`: la risposta di `policy-dimensioni` arriva dopo la scelta
     della foglia e `inizializzaDimensioni` riscriveva le dimensioni con i
     default, cancellando il valore appena scelto dall'utente. Il bottone
     tornava disabilitato senza spiegazione. Ora una scelta gia' fatta non
     viene toccata; cambiando foglia invece si riparte da zero.
  2. `integrazioni-manager`: l'elenco modelli scriveva "Italiano/Inglese ·
     Tutti i livelli" leggendo `lingua` e `livello_professionale`, quindi
     attribuiva una lingua ai modelli `CONTRATTI`, che non ne hanno una
     (FR-006). Ora mostra le dimensioni davvero valorizzate, e niente se non
     ce ne sono.
  **Infrastruttura di test**, condivisa con la 007: la fixture Keycloak vive in
  `e2e/support/keycloak.ts`; la registrazione dell'origine fra i redirect URI
  del client e' passata al `globalSetup`/`globalTeardown` di Playwright, perche'
  serve a tutta la suite (il realm dichiara solo `localhost:4200`); la suite gira
  in serie (`workers: 1`), perche' i test condividono realm e database. Ogni
  test stubba `runtime-config.json` sul realm locale, cosi' non serve piu'
  modificare il file del deployment prima di lanciarli.
  **Resta il vincolo del database pulito**: per FR-024 i tipi documento
  appartengono a una sola integrazione per contesto, quindi una seconda corsa
  sullo stesso schema fallisce. Ripulire e rimigrare prima di rieseguire.

**Checkpoint**: la domanda da cui la spec nasce ha risposta «no, non serve
sviluppo».

---

## Phase 8: Convergenza - conflitti con decisioni gia' chiuse

**Purpose**: quattro conflitti reali trovati rileggendo le decisioni chiuse
altrove. **Nessuno e' opzionale**: sono documenti che dopo 011 direbbero il
falso.

- [x] T042 [CONV] **Conflitto con `007`: risolto correggendo `011`, non `007`.**
  `specs/007-frontend-builder-consultazione/spec.md:127-128` afferma che il
  meccanismo dell'edizione derivata «si generalizza a qualunque dimensione con
  `consente_valore_generico=false` una volta introdotta la policy». Contraddiceva
  la **prima** stesura di FR-013, che lo teneva sulla lingua. Dopo
  DEC-011-DERIVAZIONE-GOVERNATA-DA-POLICY le due spec dicono la stessa cosa:
  `007` aveva ragione. **Non modificare `007`**: verificare soltanto che il suo
  testo e il nuovo FR-013 siano leggibili come una sola regola, e annotare in
  `007` il rinvio a FR-013/FR-014 come implementazione.
- [x] T043 [CONV] **Conflitto con il contratto di `001`**:
  `specs/001-catalogo-contratto-geban/contracts/geban-catalog-api.openapi.yaml`
  ha `lingua` in `required` alla riga 320 (`ModelloCatalogo`). Va allineato a
  T027: nullable, piu' il campo `dimensioni`. **Anche
  `EdizioneDerivataCatalogo` (riga 368)** riceve lo stesso trattamento: dopo la
  riscrittura di FR-013 un'edizione derivata puo' esserlo su una dimensione
  diversa dalla lingua, quindi `lingua` obbligatoria non regge piu'.
  *(La prima stesura di questo task diceva il contrario, sulla base del vecchio
  FR-013.)*
- [x] T044 [CONV] Stesso file, riga 62: la descrizione del parametro
  `livello_professionale` dice «lingua e percorso non ricevono fallback». Dopo
  FR-010 il fallback dipende dalla policy, non dal nome: riscrivere senza
  elencare dimensioni.
- [x] T045 [CONV] **`specs/002-builder-modelli/tasks.md:381-388`** dice «`lingua`
  e' esposta non nullabile anche nel catalogo verso GEBAN» e «decisione non
  presa». Entrambe superate: annotare con la data e il rinvio a
  DEC-011-CONTRATTO-GEBAN-ADDITIVO, senza riscrivere la nota storica.
- [x] T046 [CONV] **`docs/decision-register.yaml`**, tre aggiornamenti:
  (a) `DEC-011-DIMENSIONI-GENERICHE` da `ASSUNTA_PROVVISORIA` a `CONFERMATA` —
  la sua `fase_bloccante: PLAN` e' soddisfatta, e va corretta l'assunzione «senza
  quella [decisione GEBAN] US4 e US5 non si chiudono», che il piano ha smentito;
  (b) `DEC-002-DEFAULT-VALORE-DIMENSIONE` da `APERTA` a `CONFERMATA`, assorbita
  da DEC-011-DEFAULT-DIMENSIONE; (c) registrare le sei decisioni nuove
  `DEC-011-*` di [research.md](research.md), che oggi vivono solo li'.
- [x] T046b [CONV] **Riaprire `DEC-001-LINGUA-IT-EN`**, come le Assumptions della
  spec richiedono esplicitamente («va riaperta da US4, non aggirata») e come
  nessun altro task fa. In `docs/decision-register.yaml` passa da `CONFERMATA` a
  `SUPERSEDUTA_PARZIALMENTE`. **Il merito resta valido**: italiano e inglese sono
  modelli distinti, GEBAN genera un documento per `modello_versione_id`. Cio' che
  cambia e' il **custode del vincolo**, che passa dallo schema — colonna NOT NULL
  piu' `CheckConstraint IN ('IT','EN')`, entrambi eliminati da T003 — alla policy
  della dimensione sul tipo documento. Registrare anche la conseguenza: il
  vincolo diventa disattivabile deliberatamente, mitigato da T033 e T035.
- [x] T047b [CONV] Conseguenze documentali di T055, da chiudere con la Phase 8:
  (a) registrare la decisione nuova `DEC-011-LINGUA-OPZIONALE-SULLA-FOGLIA` in
  `docs/decision-register.yaml`, con la motivazione e il fatto che e' un
  rilassamento; (b) verificare che `010/spec.md` e i suoi task non affermino
  ancora che la lingua e' obbligatoria sulla foglia; (c) aggiungere alla presa
  d'atto verso GEBAN (T051) la versione `0.6.0` del contratto discovery —
  anche qui **nessun lavoro richiesto**, ma il team va informato che un albero
  senza lingua e' ora accettato.
- [x] T047 [CONV] `DEC-007-FALLBACK-LIVELLO-CATALOGO` resta **valida nel merito**
  ma la sua formulazione elenca le dimensioni: annotare la generalizzazione
  operata da FR-010, conservando la motivazione sulla lingua come richiesto dalle
  Clarifications della spec.

---

## Phase 9: Polish e documentazione pubblica

**Purpose**: Constitution II e VI. Non coda: sono obblighi, non rifiniture.

- [x] T048 [P] Catalogo errori in `docs/`: **aggiungere**
  `DIMENSIONE_NON_DICHIARATA`, **rimuovere** `GENERICO_NON_SUPPORTATO`. Un codice
  che sparisce va segnato come rimosso, non cancellato in silenzio.
- [x] T049 [P] Riversare i due delta di [contracts/](contracts/) negli OpenAPI
  versionati serviti da Swagger UI e ReDoc, con gli esempi JSON.
- [x] T050 [P] Documentare in `docs/` il modello di configurazione delle policy
  per dimensione, leggibile da un integratore esterno che non ha accesso al
  codice (Constitution VI).
- [x] T051 **Consegna a GEBAN, a cura dell'utente**: presa d'atto su
  `ModelloCatalogoSchema.lingua` nullable — nessun lavoro richiesto, nessun
  cambiamento nelle risposte che ricevono oggi, eventuale ricompilazione del
  client generato. **Non blocca l'implementazione**, deve precedere il rilascio.
  Bozza pronta in `docs/presa-atto-geban-dimensioni-catalogo.md`.
- [x] T052 [P] **Segnalare a GEBAN il refuso `_em`** (`descrizione_em`,
  `medaglione_em`, che dovrebbero essere `_en`, sistematico su tutte e 65 le
  foglie): **gia' comunicato dall'utente il 2026-09-23**. Resta da verificare,
  quando GEBAN risponde, se i codici vengono corretti a monte o se GEMODO deve
  accettarli come sono in via definitiva.
- [x] T053 Verifica del criterio di successo:
  `grep -rn '"lingua"\|"livello"' backend/app/builder/` non deve trovare
  occorrenze che governino comportamento. **Decisione 2026-09-25**: il criterio
  letterale viene sostituito da un criterio semantico, perche' i bridge legacy
  richiesti da T009/T030 devono restare finche' i client usano ancora i campi
  storici. Sono ammesse solo queste occorrenze:
  (a) campi e filtri legacy `lingua`/`livello_professionale` in input/output,
  tradotti in o proiettati da `dimensioni`;
  (b) `POLICY_DI_RIPIEGO`, che inizializza la configurazione dei tipi esistenti;
  (c) commenti, test e nomi storici dei campi richiesti. Restano vietati `if`
  o rami applicativi che decidono enforcement, fallback, identita',
  pubblicazione o derivazione sulla base del nome `lingua` o `livello`.
  Verifica eseguita: le occorrenze rimaste nel builder sono bridge legacy,
  default di configurazione, proiezioni di risposta, commenti/test o lingua del
  singolo campo richiesto, non decisioni di business cablate sul nome della
  dimensione.

---

## Dependencies

```text
Phase 1 (T001-T002)  ──┐
                       ├─→ Phase 2 (T003-T007) ──┬─→ Phase 3 US1 (T008-T015)
                       │   BLOCCANTE             ├─→ Phase 4 US2 (T016-T021)
                       │                         └─→ Phase 5 US3 (T022-T026)
                       │                                      │
                       │                          Phase 4 ────┴──→ Phase 6 US4
                       │                                          (T054 → T027-T036)
                       │                                                      │
                       └──────────────────────────────────────→ Phase 7 US5 (T037-T041)

Phase 8 (T042-T047, T046b) → dopo le fasi che rendono veri quei documenti (6 e 7)
Phase 9 (T048-T053)        → T052 eseguibile subito; il resto a valle
```

**T054 precede T027** dentro la Phase 6: decide il nome della dimensione livello,
e T027 scrive la proiezione nel contratto. Farlo dopo significherebbe scrivere
una mappatura cablata e poi disfarla.

**Sequenza obbligata delle P1**: US1 → US2 → US3 non e' un ordine di priorita' ma
di dipendenza tecnica. Senza persistenza non c'e' enforcement; senza valori
registrati non c'e' unicita' da calcolare.

## Parallel opportunities

- **Phase 1**: T001 e T002 insieme.
- **Phase 3**: T013, T014, T015 dopo T008-T012.
- **Phase 4**: T020 e T021 dopo T016-T019.
- **Phase 5**: T024, T025, T026 dopo T022-T023.
- **Phase 6**: T035 e T036 dopo T027-T034. **T054 non e' parallelizzabile**:
  precede T027.
- **Phase 9**: T048, T049, T050, T052 fra loro. **T052 non dipende da nulla** e
  conviene farlo per primo, prima che il refuso entri in modelli pubblicati.

## Implementation strategy

**MVP = Phase 2 + Phase 3 + Phase 4 + Phase 5** (T003-T026). Chiude le tre P1 e
rende vera la premessa della spec: una dimensione nuova e' registrabile,
obbligabile e distinguibile. Manca solo il caso `contratti` visto da fuori.

**Incremento successivo**: Phase 6 + Phase 7, che chiudono US4 e US5 e rispondono
alla domanda letterale da cui la spec nasce.

**Non rinviare Phase 8**: quei documenti, dopo le fasi 6 e 7, direbbero il falso.
Un conflitto lasciato aperto e' esattamente il tipo di residuo che ha reso
necessaria questa spec.

- [x] T055b (`builder/repository.py`, `builder/service.py`, `configurazione/service.py`,
      `catalog/service.py`, `dimensioni.component.*`; test in
      `backend/tests/builder/test_policy_dimensione.py` e
      `frontend/.../dimensioni.component.spec.ts`)
      **FR-010 seconda clausola + FR-010b.** Rilevato collaudando le API reali
      il 2026-09-24: chiudere il generico di una dimensione rendeva
      irreperibile nel catalogo, **per ogni valore**, un modello gia'
      pubblicato che non la valorizzava, e l'avviso mostrato prima di salvare
      annunciava `0` perche' contava i modelli che la **valorizzano** - cioe'
      l'insieme opposto a quello colpito. Tre interventi: il conteggio
      dell'impatto guarda l'insieme giusto ed e' esposto anche in lettura
      (`modelli_pubblicati_senza_valore`); il cambio richiede `conferma_impatto`
      quando l'impatto e' maggiore di zero, senza mai essere rifiutato
      (vietarlo sarebbe un vicolo cieco, contro DEC-011-POLICY-LINGUA-ALL-ADMIN);
      il fallback del catalogo scatta comunque per i modelli gia' pubblicati,
      perche' la policy governa cosa si crea, non la reperibilita' del
      pubblicato. Vedi DEC-011-POLICY-NON-INVALIDA-IL-PUBBLICATO.
