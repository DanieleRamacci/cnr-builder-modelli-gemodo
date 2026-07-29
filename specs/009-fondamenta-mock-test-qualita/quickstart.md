# Quickstart - Fondamenta Mock Test E Qualita

Questa guida descrive come validare la feature `009` dopo l'implementazione dei task.
Non sostituisce i test automatici e non richiede accesso a GEBAN reale.

## Prerequisiti

- ambiente locale documentato;
- backend, frontend, PostgreSQL, Keycloak, documentale mock e mock GEBAN disponibili;
- migrations applicate;
- seed demo caricati e marcati come `DEMO`;
- contratti pubblici disponibili per catalogo, campi/schema, validazione, generazione,
  stato e download;
- OpenAPI versionati, esempi JSON pubblicabili, catalogo errori e Swagger/ReDoc locale/test
  disponibili per le API pianificate;
- documentazione navigabile generata da repository e raggiungibile dal README;
- registro decisioni aperte aggiornato.

## Scenario 1 - Verifica ambiente locale

1. Avviare l'ambiente locale (`docker compose -f infra/local/compose.yaml up`, o solo i
   servizi necessari) seguendo `infra/local/*/README.md`.
2. Eseguire la verifica ambiente:

   ```bash
   cd backend
   uv sync
   uv run gemodo-quality verifica-ambiente
   ```

3. Controllare l'esito (`PASS`/`PARTIAL`/`FAIL`, exit code `0`/`1`/`2`) e il dettaglio
   per servizio stampato dal comando.

Expected:

- backend, PostgreSQL, Keycloak e documentale mock (obbligatori) determinano `PASS`
  quando tutti raggiungibili; frontend e mock-GEBAN sono verificati ma non obbligatori
  finche' le spec `007`/User Story 2 non li implementano, quindi una loro assenza porta
  al piu' a `PARTIAL`, mai a un falso `PASS` silenzioso ne' a un `FAIL` bloccante;
- ogni servizio mancante e' segnalato con `tipo: prerequisito_mancante`, distinto da un
  eventuale `errore_applicativo` (FR-008);
- nessun controllo richiede accesso al DB GEBAN.

## Scenario 2 - Migrations e seed demo

1. Applicare le migrations su database locale pulito:

   ```bash
   cd backend
   DATABASE_URL=postgresql+psycopg://gemodo:gemodo@localhost:5432/gemodo uv run alembic upgrade head
   ```

2. Consultare il catalogo seed demo in
   `infra/local/postgres/seed-demo-catalog.yaml` (`seeds` + `catalogo`); il caricamento
   effettivo nel database e' compito delle spec proprietarie (`001`/`002`) quando
   generano i propri task implementativi - la `009` garantisce solo che schema e
   manifest siano coerenti e privi di dati reali.
3. Verificare presenza di tipo documento (`BANDO_CONCORSO`), categoria (`DEMO`),
   tipologie GEBAN/SOL (TDPNRR, CD, DIR, TD, CP, RS, CATP, TI, SDIP, MOB), modello
   pubblicato demo (`demo-bando-concorso-standard-v1`) e un caso non pubblicabile
   (`demo-bando-concorso-html-libero-non-valido`).

Expected:

- le tabelle baseline (`tipo_documento`, `categoria_documento`, `tipologia_bando`,
  `modello_documento`, `modello_versione`, `campo_modello`, `sezione_modello`,
  `generazione_documento`, `evento_audit`) sono create, vedi `backend/alembic/README.md`
  per l'ownership di ciascuna;
- tutti i seed dichiarati in `seed-demo-catalog.yaml` hanno `marcatura_demo: DEMO` e
  `dati_sensibili: false`;
- esiste almeno un modello pubblicato utilizzabile dal mock GEBAN e almeno un caso non
  pubblicabile/non valido (FR-011).

## Scenario 3 - Mock GEBAN flusso valido

Le spec `004`/`005`/`006` non hanno ancora `plan.md`/`tasks.md` propri; `001` li ha
gia' ma restano fermi alla sessione di chiarimento del 2026-06-19 e non riflettono le
decisioni successive (vedi `docs/project-map.md`, sezione "Stato Plan/Tasks Delle Spec
Operative"). In nessun caso esiste oggi un endpoint HTTP GEMODO reale da chiamare
(vedi `AGENTS.md`). Fino ad allora:

1. Risolvere il piano dello scenario (dry run, nessuna chiamata di rete):

   ```bash
   cd backend
   uv run python ../mock-geban/scenario_runner.py --scenario E2E-001 --payload bando-concorso-valid.json
   ```

2. Eseguire lo scenario end-to-end contro il client fake che rispetta lo stesso
   protocollo `ClienteGemodo` (`backend/tests/support/fake_gemodo_client.py`),
   riusando l'autorizzazione reale (`backend/app/quality/integration_profile.py`):

   ```bash
   uv run pytest tests/e2e/test_mock_geban_valid_flow.py -v
   ```

Expected:

- il piano usa solo le operazioni pubbliche di `backend/app/quality/mock_contract_guard.py`
  (`catalogo_modelli`, `campi_richiesti`, `valida_payload`, `genera_documento`,
  `stato_generazione`), mai scorciatoie interne;
- il payload demo valido (`bando-concorso-valid.json`) viene validato senza errori;
- la generazione produce due output, italiano e inglese (`bando_inglese: true`, FR-022),
  coerenti con `mock-geban/scenarios/expected-outcomes.yaml`;
- lo stato risulta `COMPLETATA` e consultabile.

## Scenario 4 - Errori funzionali e idempotenza

```bash
cd backend
uv run pytest tests/e2e/test_mock_geban_error_flows.py -v -k "e2e_002 or e2e_003 or e2e_004"
```

1. Il payload demo non valido (`bando-concorso-invalid.json`) viene inviato: campo
   obbligatorio mancante, tipologia SOL non valida e campi inglesi mancanti.
2. Una generazione valida viene ripetuta con la stessa chiave di idempotenza e gli
   stessi dati.
3. La stessa chiave viene ripetuta con dati divergenti (es. `numero_posti` diverso).

Expected:

- il payload non valido produce gli errori funzionali attesi
  (`CAMPO_OBBLIGATORIO_MANCANTE`, `TIPOLOGIA_SOL_NON_VALIDA`, `CAMPI_INGLESI_MANCANTI`,
  vedi `infra/openapi/errors.md`);
- il retry identico restituisce la generazione esistente (`riutilizzato: true`), senza
  duplicati;
- il retry con dati divergenti produce `GENERAZIONE_CONFLITTO_IDEMPOTENTE`;
- conflitto e fallimenti attesi sono elencati in `infra/local/audit-expectations.yaml`.

## Scenario 5 - Accesso non autorizzato

```bash
cd backend
uv run pytest tests/e2e/test_mock_geban_error_flows.py -v -k "e2e_006"
```

1. Un client con profilo di integrazione non attivo (`GEBAN_RECLUTAMENTO_V1` in stato
   `BOZZA` invece di `ATTIVO`) richiede stato e download.

Expected:

- stato e download restituiscono `PROFILO_INTEGRAZIONE_NON_ABILITATO`, nessun payload o
  file esposto;
- l'accesso viene rifiutato anche se il client tecnico e' di per se' riconosciuto
  (identita' Keycloak valida ma profilo GEMODO non coerente, vedi
  `infra/local/keycloak/authorization-boundary.local.yaml`);
- l'evento autorizzativo e' previsto da `infra/local/audit-expectations.yaml`
  (`audit-autorizzazione-negata`).

## Scenario 6 - Matrice copertura e decisioni aperte

```bash
cd backend
uv run pytest tests/contract/test_open_decisions_contract.py tests/integration/test_open_decision_gates.py tests/integration/test_coverage_matrix.py -v
```

1. Aprire `docs/decision-register.yaml` (28 decisioni, incluse `SEC-006-001`/`SEC-006-002`)
   e `docs/quality-coverage-matrix.yaml` (43 righe, copertura FR-027..FR-045 e dei sei
   scenari E2E minimi).
2. Verificare che ogni scenario minimo sia collegato a spec owner, requisito e contratto.
3. Verificare che ogni decisione critica abbia owner, assunzione provvisoria (o stato
   confermato) e fase bloccante, ed eseguire il gate per una spec target, es.:

   ```bash
   uv run python -c "
   from pathlib import Path
   from app.quality.readiness_gate import load_decision_register, valuta_readiness
   from app.quality.schemas import FaseBloccante
   decisioni = load_decision_register(Path('../docs/decision-register.yaml'))
   esito = valuta_readiness(decisioni, fase_richiesta=FaseBloccante.TASKS, spec_target='specs/001-catalogo-contratto-geban')
   print('pronto:', esito.pronto, [d.id for d in esito.blocchi])
   "
   ```

Expected:

- nessuna decisione critica entra nei task come assunzione silenziosa (ogni decisione
  non `CONFERMATA` ha `assunzione_provvisoria` esplicita, anche quando dichiara
  "nessuna assunzione proposta");
- gli scenari minimi coprono valido, payload non valido, retry idempotente, conflitto,
  fallimento e accesso non autorizzato;
- le parti bloccate da decisioni aperte sono esplicite: al momento della stesura,
  `valuta_readiness` segnala `TASKS` non pronto per `specs/001-catalogo-contratto-geban`
  a causa di decisioni ancora `APERTA`/`ASSUNTA_PROVVISORIA` (es.
  `DEC-001-CONFIG-PROFILO-GEBAN`, `DEC-001-IDENTIFICATIVI-MODELLO`) - comportamento
  atteso, non un difetto.

## Scenario 7 - Profili integrazione e confine Keycloak/GEMODO

1. Aprire il manifest locale dei profili di integrazione.
2. Verificare che `GEBAN` sia registrato come sistema richiedente con client tecnico,
   audience attesa, ruoli/claim generali e profilo applicativo.
3. Verificare che il profilo indichi tipi documento, categorie, modelli/versioni,
   contratti e operazioni abilitate.
4. Simulare un client con token valido ma profilo GEMODO mancante o non coerente.

Expected:

- GEMODO non conserva password, segreti o credenziali dei client;
- Keycloak fornisce identita', client, audience e ruoli/claim generali;
- GEMODO applica autorizzazioni fini su profilo, modello, contratto e operazione;
- un token valido ma non associato a un profilo GEMODO coerente non abilita generazione,
  download o modifica dei modelli.

## Scenario 8 - Modello documentale controllato

1. Aprire il seed demo del modello documentale controllato.
2. Verificare che dichiari pagina, margini, regioni, blocchi ammessi, stili, asset,
   placeholder e posizionamenti controllati.
3. Verificare che siano presenti esempi per intestazione/logo, titolo, paragrafo, tabella o
   colonne e firma posizionata.
4. Verificare che non siano presenti HTML libero, CSS libero o script.

Expected:

- il modello demo usa una struttura controllata e versionata;
- logo e asset sono referenziati tramite identificativo e versione;
- placeholder e campi sono coerenti con il contratto dati;
- il builder futuro potra' manipolare la stessa struttura tramite editor visuale limitato;
- il renderer PDF usa eventuali formati tecnici intermedi senza esporre HTML/CSS libero
  all'utente.

## Scenario 9 - Documentazione API OpenAPI/Swagger/ReDoc

1. Aprire il manifest di readiness API e i contratti OpenAPI versionati.
2. Verificare che ogni API pubblica o di integrazione abbia endpoint, schemi, stati, codici
   errore, autenticazione, autorizzazioni e riferimenti agli esempi.
3. Avviare la documentazione interattiva locale/test.
4. Verificare che Swagger UI e ReDoc, o equivalenti, siano generati dalla stessa sorgente
   OpenAPI.
5. Verificare che gli esempi JSON contengano solo dati demo.

Expected:

- nessun endpoint operativo viene implementato senza OpenAPI versionato;
- esempi di successo ed errore funzionale sono leggibili e coerenti con il contratto;
- Swagger/ReDoc non divergono dal contratto versionato;
- esempi e documentazione non contengono token, secret, password, dati personali reali o URL
  ambientali sensibili.

## Scenario 10 - Documentazione navigabile e riuso PA

1. Aprire il README del repository.
2. Seguire i link verso documentazione MkDocs, project map, costituzione e feature attiva.
3. Verificare che siano leggibili fasi Spec Kit, blocchi, decisioni, vincoli, contratti API
   e quickstart.
4. Aprire la pagina di readiness open source/PA.
5. Verificare lo stato di licenza, setup, sviluppo, produzione, architettura,
   configurazione, sicurezza, contributi, segnalazione vulnerabilita', test e release.

Expected:

- un revisore trova proposta, costituzione, feature attiva, stato spec, blocchi e decisioni
  in massimo tre passaggi;
- la licenza e' tracciata come `DA_CONFERMARE` finche' non viene decisa;
- la documentazione e' in formato testuale versionabile;
- non sono richiesti documenti privati o conoscenza implicita per capire scelte e vincoli.
