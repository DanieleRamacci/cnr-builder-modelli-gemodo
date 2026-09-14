# Review Findings 2026-09-01 - ADev, Codex, Claude

## Purpose

Questo file raccoglie gli esiti delle review eseguite sul repository
`builder-modello-bando` per permettere a un agente AI o a un processo Spec Kit di
generare specifiche di correzione, ulteriori analisi o task di remediation.

Il file distingue:

- finding applicativi sulla feature attiva `001-catalogo-contratto-geban`;
- finding sul workflow ADev/Spec Kit e sulla portabilita' della configurazione;
- stato dei test e dei quality gate;
- problemi gia' riscontrati da Codex e da Claude/ADev.

## Context

- Data review: 2026-09-01
- Branch: `chore/adopt-adev-standard`
- Commit HEAD osservato: `97f58a28837b31344f81dc6056f3030e65d17b4d`
- Feature attiva rilevata da `.specify/feature.json`: `specs/001-catalogo-contratto-geban`
- Report ADev principale: `.adev/reviews/review-20260901T140814Z.json`
- Report reviewer Claude: `.adev/reviews/run-20260901T140814Z/review-primary.json`
- Review manuale Codex: eseguita in chat con CodeGraph, TokenSave, letture mirate e pytest.

## ADev Behavior Assessment

ADev ora si comporta meglio rispetto alla prima esecuzione.

La prima review ADev era fallita per motivi tecnici:

- reviewer Claude non trusted sul workspace;
- comando regressione fallito in sandbox per accesso alla cache `uv`.

Dopo reinstallazione del tool locale e `adev adopt . --apply`, `adev doctor .` rileva:

- `adev` come tool esplicito e `READY`;
- `review_config` `READY`;
- `quality_extension` `READY`;
- `codegraph` `READY`;
- `tokensave` `READY`.

La review ADev successiva ha prodotto un report valido:

- `reviewer_id`: `primary`
- `provider`: `claude_code`
- `valid`: `true`
- `message`: `Claude Code reviewer completed`
- `finding_count`: `11`
- `verdict`: `FAIL`

Questa esecuzione ha incluso la feature attiva e ha trovato anche bug applicativi
coerenti con la review Codex. Quindi il comportamento aggiornato e' coerente con
l'obiettivo di review indipendente, ma il gate fallisce correttamente per regressioni
e finding bloccanti.

## Verification Results

### Tool Readiness

Comando:

```bash
adev doctor .
```

Risultato rilevante:

```text
git                  READY
spec_kit             READY
review_config        READY
quality_extension    READY
adev                 READY
codegraph            READY
tokensave            READY
```

### Regression Suite

Comando ADev configurato:

```bash
uv --directory backend run pytest -m "not e2e"
```

Risultato:

```text
116 passed, 14 skipped, 12 deselected
exit_code: 1
```

Motivo del fallimento: pytest intercetta `ResourceWarning` per socket non chiusi
durante il cleanup. Con `backend/pytest.ini` che imposta `filterwarnings = error`,
questi warning diventano errore bloccante.

### E2E Suite

Comando eseguito manualmente:

```bash
uv run pytest -m e2e
```

Risultato:

```text
12 passed, 130 deselected
exit_code: 0
```

## Application Findings

### APP-001 - Historical Catalog Mode Never Returns Archived Versions

- Severity: HIGH
- Source: Codex manual review, Claude/ADev review
- Finding type: application
- Files:
  - `backend/app/catalog/repository.py`
  - `specs/001-catalogo-contratto-geban/contracts/geban-catalog-api.openapi.yaml`
  - `backend/alembic/versions/0004_seed_catalogo_demo.py`
  - `backend/alembic/versions/0006_riallinea_modelli_demo_classificazione.py`
- Related requirements:
  - FR-006a
  - US1 Acceptance Scenario 4
  - SC-007

Problem:

`_published_versions_stmt()` applica sempre:

```python
ModelloDocumentoVersione.stato == STATO_PUBBLICATO
```

anche quando `historical=True`. Quindi la modalita' `STORICO` non puo' restituire
versioni `ARCHIVIATO` o storiche, nonostante la spec richieda recupero storico di
versioni archiviate.

Additional issue:

Il contratto OpenAPI `ModelloCatalogo.stato` dichiara solo `PUBBLICATO`, quindi anche
il contratto pubblico contraddice la modalita' storico prevista.

Recommended remediation:

- In modalita' `STORICO`, includere almeno `ARCHIVIATO` e gli stati storici previsti
  dal data model, senza esporli in modalita' operativa.
- Aggiornare OpenAPI per consentire gli stati restituiti dallo storico.
- Seedare almeno una versione `ARCHIVIATO`.
- Aggiungere test che dimostrino:
  - `STORICO` restituisce una versione archiviata;
  - `OPERATIVA` non restituisce la stessa versione;
  - `campi-richiesti` e `documenti/valida` continuano a rifiutare versioni non operative.

### APP-002 - Payload Validation Ignores Declared Field Constraints

- Severity: HIGH
- Source: Codex manual review, Claude/ADev review
- Finding type: application
- Files:
  - `backend/app/validation/service.py`
  - `backend/alembic/versions/0004_seed_catalogo_demo.py`
  - `backend/alembic/versions/0006_riallinea_modelli_demo_classificazione.py`
- Related requirements:
  - FR-011
  - FR-012
  - US3

Problem:

`PayloadValidationService.validate_payload()` controlla:

- versione esistente;
- stato pubblicato;
- campi extra;
- presenza campo;
- tipo base tramite `_matches_type()`.

Non legge ne' applica `ModelloCampoRichiesto.validazione`.

I seed dichiarano vincoli reali:

```json
{"minLength": 1}
{"minimum": 1}
```

ma il servizio puo' accettare payload come:

```json
{
  "codice_bando": "",
  "numero_posti": 0
}
```

se i tipi base sono corretti.

Recommended remediation:

- Applicare i vincoli in `field.validazione` dopo il type check.
- Coprire almeno:
  - `minLength`;
  - `maxLength`;
  - `minimum`;
  - `maximum`;
  - `pattern`;
  - `enum`, se previsto nei contratti.
- Decidere il codice errore:
  - riuso di `TIPO_NON_VALIDO`; oppure
  - nuovo codice tipo `VINCOLO_NON_RISPETTATO`, da aggiungere a `infra/openapi/errors.md`
    e OpenAPI.
- Aggiungere test per stringhe vuote e `numero_posti=0`.

### APP-003 - Empty Values Satisfy Required Field Check

- Severity: MEDIUM
- Source: Codex manual review, Claude/ADev review
- Finding type: application
- File: `backend/app/validation/service.py`
- Related requirements:
  - Edge case: valori vuoti per campi obbligatori
  - FR-012
  - FR-014

Problem:

La presenza e' calcolata cosi':

```python
value_present = field.codice in request.dati and request.dati[field.codice] is not None
```

Quindi `""`, `[]` e `{}` risultano presenti. Per stringhe obbligatorie, `""` passa
anche `_matches_type()` perche' e' una stringa.

Recommended remediation:

- Trattare stringhe vuote o whitespace-only come assenti per campi obbligatori.
- Decidere se liste/oggetti vuoti siano ammessi in base al vincolo del campo.
- Aggiungere test specifici per:
  - stringa vuota su campo obbligatorio IT;
  - stringa vuota su campo obbligatorio EN con `bando_inglese=true`;
  - array/object vuoti quando il contratto li vieta.

### APP-004 - Complex Array/Object Fields Are Not Structurally Validated

- Severity: MEDIUM
- Source: Codex manual review, Claude/ADev review
- Finding type: application
- File: `backend/app/validation/service.py`
- Related requirements:
  - FR-008a
  - FR-012
  - Edge cases sui sotto-campi array/object

Problem:

Per `array` e `object`, `_matches_type()` controlla solo:

```python
isinstance(value, list)
isinstance(value, dict)
```

Non vengono validati:

- sotto-campi obbligatori;
- tipi dei sotto-campi;
- campi extra;
- vincoli annidati;
- `additionalProperties=false` per oggetti annidati.

Inoltre `ModelloCampoRichiesto` non espone ancora una colonna/schema dedicata ai
sotto-campi complessi, quindi il modello dati non supporta pienamente FR-008a.

Recommended remediation:

- Estendere il data model per rappresentare lo schema annidato dei campi complessi.
- Aggiornare migrazioni e Pydantic schema.
- Validare struttura annidata in `PayloadValidationService`.
- Aggiungere test per object/array con:
  - sotto-campo mancante;
  - tipo errato;
  - campo extra;
  - elemento array non conforme.

### APP-005 - Direct Access By Model Version ID Ignores Validity Window

- Severity: HIGH
- Source: Codex manual review
- Finding type: application
- Files:
  - `backend/app/catalog/service.py`
  - `backend/app/validation/service.py`
  - `backend/app/catalog/repository.py`
- Related requirements:
  - FR-003
  - FR-005
  - FR-006b
  - FR-006f
  - FR-012a

Problem:

`campi-richiesti` e `documenti/valida` recuperano la versione da `public_id` e
controllano solo:

```python
version.stato == STATO_PUBBLICATO
```

Non verificano:

- `data_inizio_validita`;
- `data_fine_validita`;
- `data_riferimento` nel payload di validazione.

Conseguenza: una versione pubblicata ma scaduta o non ancora valida puo' essere usata
direttamente se GEBAN conserva il `modello_versione_id`.

Recommended remediation:

- Centralizzare una funzione tipo `is_versione_operativa(version, data_riferimento)`.
- Usarla sia in catalogo operativo, sia in `get_campi_richiesti`, sia in
  `validate_payload`.
- Se il payload include `data_riferimento`, usarla per la validazione; altrimenti usare
  la data corrente.
- Aggiungere test per versione:
  - pubblicata ma futura;
  - pubblicata ma scaduta;
  - valida alla data_riferimento esplicita;
  - non valida alla data_riferimento esplicita.

### APP-006 - Inactive Categories Can Be Returned By search_modelli

- Severity: MEDIUM
- Source: Codex manual review
- Finding type: application
- File: `backend/app/catalog/repository.py`
- Related requirements:
  - FR-004
  - Edge case: profilo non attivo

Problem:

`list_published_model_versions()` joina `CategoriaDocumento`, ma non filtra:

```python
CategoriaDocumento.stato == STATO_ATTIVO
```

Un modello collegato a profilo/categoria inattiva puo' quindi restare selezionabile
nel catalogo.

Recommended remediation:

- Aggiungere filtro su categoria attiva nella query operativa.
- Decidere se lo storico deve includere categorie inattive.
- Aggiungere test con categoria inattiva e modello pubblicato.

### APP-007 - Current-Version Uniqueness Constraint Does Not Match FR-006e

- Severity: MEDIUM
- Source: Codex manual review
- Finding type: application/database
- File: `backend/alembic/versions/0002_catalogo_modelli.py`
- Related requirements:
  - FR-006e
  - Edge case: due versioni pubblicate correnti nello stesso contesto

Problem:

Il vincolo DB:

```sql
CREATE UNIQUE INDEX uq_modello_versione_pubblicata_corrente
ON modello_versione (modello_documento_id)
WHERE stato = 'PUBBLICATO'
```

impedisce piu' versioni pubblicate dello stesso `modello_documento_id`, ma FR-006e
richiede al massimo una versione pubblicata corrente per combinazione:

```text
tipo documento + profilo + tipologia + variante
```

Inoltre il servizio non rileva come anomalia due versioni correnti nello stesso
contesto se appartengono a modelli diversi.

Recommended remediation:

- Definire se la garanzia deve essere DB-level, service-level o entrambe.
- Se DB-level: valutare indice parziale su colonne normalizzate o vincolo tramite
  modello di dominio che renda la combinazione direttamente vincolabile.
- Se service-level: rilevare duplicati nel risultato operativo e restituire errore
  funzionale di anomalia catalogo.
- Aggiungere test per due modelli pubblicati correnti stesso tipo/profilo/tipologia/variante.

### APP-008 - Auth Bypass Toggle Has No Environment Guard

- Severity: LOW
- Source: Claude/ADev review
- Finding type: application/security
- File: `backend/app/common/security.py`
- Related requirements:
  - Security and controlled AI principle
  - FR-017a
  - FR-017b

Problem:

`require_principal()` ritorna `mock_principal()` quando:

```python
settings.gemodo_use_mock_principal
```

e il principal mock concede ruoli documentali. Il default e' `False`, ma basta una
env var per disabilitare i controlli JWT senza guardia esplicita su ambiente locale/test.

Recommended remediation:

- Aggiungere `APP_ENV` o equivalente.
- Consentire mock principal solo con `APP_ENV in {"local", "test"}`.
- Fallire startup o richiesta se mock principal e' attivo in ambiente non consentito.
- Loggare warning esplicito quando il mock e' attivo.

## Test And Coverage Findings

### TEST-001 - P1 Service Tests Are Skipped In The Deterministic Gate

- Severity: HIGH
- Source: Claude/ADev review
- Finding type: application/test coverage
- Files:
  - `backend/tests/validation/test_validazione_payload_api.py`
  - `backend/tests/catalog/test_catalog_service_integration.py`
  - `backend/tests/support/postgres.py`
- Related requirements:
  - FR-003
  - FR-004
  - FR-011 through FR-015
  - FR-012a
  - FR-020
  - FR-021
  - FR-022

Problem:

Nel gate deterministico:

```text
test_catalog_service_integration.py sssss
test_validazione_payload_api.py sssssssss
```

I test P1 reali saltano se Docker/Testcontainers non e' disponibile e `DATABASE_URL`
non e' impostato.

I test che restano attivi usano spesso servizi fake tramite dependency override e non
esercitano il repository/servizio reale.

Recommended remediation:

- Aggiungere unit test senza Docker per `CatalogService` e `PayloadValidationService`.
- Usare fake repository/sessione controllata o SQLite solo se compatibile con il modello.
- In alternativa, rendere PostgreSQL disponibile nel gate e trattare skip dei test P1
  come failure.

### TEST-002 - Regression Command Exits Non-Zero Because Of ResourceWarnings

- Severity: HIGH
- Source: Codex manual review, Claude/ADev review
- Finding type: workflow/test reliability
- File: `backend/pytest.ini`

Problem:

Il comando:

```bash
uv --directory backend run pytest -m "not e2e"
```

produce pass/skip ma termina con exit code 1 per:

```text
PytestUnraisableExceptionWarning
ResourceWarning: unclosed <socket.socket ...>
```

`filterwarnings = error` rende questi warning fatali.

Recommended remediation:

- Chiudere correttamente i client/socket che generano warning.
- Non nascondere il problema abbassando il livello warning finche' non e' compresa la
  sorgente.
- Dopo il fix, il comando deve terminare con exit code 0.

### TEST-003 - TestClient Instances Are Not Closed

- Severity: MEDIUM
- Source: Claude/ADev review
- Finding type: test reliability
- Files:
  - `backend/tests/catalog/test_catalogo_modelli_api.py`
  - `backend/tests/catalog/test_catalogo_categorie_api.py`
  - `backend/tests/catalog/test_catalogo_tipologia_sol.py`
  - `backend/tests/catalog/test_catalogo_tipi_documento_api.py`
  - `backend/tests/catalog/test_campi_richiesti_api.py`
  - `backend/tests/common/test_api_error_response.py`
  - `backend/tests/common/test_security_jwt.py`
  - `backend/tests/validation/test_validazione_payload_api.py`

Problem:

Diversi test usano:

```python
TestClient(app).get(...)
```

oppure fixture che fanno `yield TestClient(app)` senza context manager. Questo puo'
lasciare aperti transport/socket e causare il fallimento del gate.

Recommended remediation:

- Usare:

```python
with TestClient(app) as client:
    ...
```

- Oppure creare fixture condivisa che chiude il client.

## Workflow And Traceability Findings

### WF-001 - tasks.md References Completed Artifacts That Do Not Exist

- Severity: LOW
- Source: Codex manual review, Claude/ADev review
- Finding type: workflow/traceability
- File: `specs/001-catalogo-contratto-geban/tasks.md`

Problem:

Task completati puntano a file inesistenti:

- `backend/tests/validation/test_validazione_bando_inglese.py`
- `backend/app/validation/errors.py`
- `backend/app/catalog/errors.py`

Il comportamento esiste in altri file, ma la tracciabilita' task -> repo e' inesatta.

Recommended remediation:

- Aggiornare `tasks.md` con i file reali:
  - `backend/tests/validation/test_validazione_payload_api.py`;
  - `backend/app/common/errors.py`.
- Oppure creare i moduli indicati se si vuole mantenere quella separazione.

### WF-002 - Quickstart Test Evidence Is Not Reproducible

- Severity: LOW
- Source: Claude/ADev review
- Finding type: workflow/documentation
- File: `specs/001-catalogo-contratto-geban/quickstart.md`

Problem:

Il quickstart registra:

```text
126 passed, 12 deselected
```

ma il gate ora produce:

```text
116 passed, 14 skipped, 12 deselected
exit_code: 1
```

Recommended remediation:

- Aggiornare la sezione verifica test con:
  - exit code;
  - skip count;
  - prerequisiti Docker/PostgreSQL;
  - risultato dopo la correzione del gate.

### WF-003 - ADev Review Artifacts Are Not Gitignored

- Severity: LOW
- Source: Claude/ADev previous review
- Finding type: workflow/repo hygiene
- File: `.gitignore`

Problem:

`.adev/` contiene report con path assoluti, output test e dati di sessione. Non dovrebbe
essere committata accidentalmente.

Recommended remediation:

- Aggiungere `.adev/` o almeno `.adev/reviews/` a `.gitignore`.
- Valutare se mantenere solo un report sintetico versionato in `docs/`, come questo file.

### WF-004 - Agent/MCP Local Config May Be Non-Portable

- Severity: MEDIUM
- Source: Claude/ADev previous review
- Finding type: workflow/portability
- Files:
  - `.claude/settings.json`
  - `.mcp.json`

Problem:

Alcune configurazioni locali possono includere path assoluti come:

```text
/opt/homebrew/bin/tokensave
```

Questo non e' portabile su Linux, CI, macOS Intel o macchine senza Homebrew.

Recommended remediation:

- Usare `tokensave` via `PATH`, se il file e' da versionare.
- Oppure gitignorare configurazioni macchina-locali.
- Tenere nel repository solo configurazioni portabili.

### WF-005 - ADev Hook Is Blocking And Depends On Tool Availability

- Severity: improved after latest adopt
- Source: Claude/ADev previous review and follow-up verification
- Finding type: workflow/tooling
- Files:
  - `.specify/extensions/adev-quality/extension.yml`
  - `.specify/config/tools.yml`

Problem before latest update:

L'hook `after_implement` chiamava `adev review` ma `adev` non era dichiarato come tool
controllato.

Current state:

Dopo reinstallazione e `adev adopt . --apply`, `adev doctor .` ora riporta:

```text
adev READY required for quality_gate, spec_kit_extension, independent_review
```

Recommended remediation:

- Verificare che `.specify/config/tools.yml` aggiornato venga mantenuto.
- Documentare nei prerequisiti di sviluppo che `adev` e' richiesto per il gate.

## Tooling Findings

### TOOL-001 - TokenSave Index Served From main, Not Review Branch

- Severity: INFO
- Source: TokenSave status, Claude/ADev review
- Finding type: tooling

Problem:

TokenSave segnala che il branch `chore/adopt-adev-standard` non e' tracciato e serve
l'indice da `main`.

Impact:

Non e' bloccante perche' CodeGraph era aggiornato e TokenSave e' opzionale, ma le query
TokenSave non rappresentano esattamente il branch corrente.

Recommended remediation:

- Se serve impact analysis TokenSave sul branch corrente, eseguire:

```bash
tokensave branch add chore/adopt-adev-standard
tokensave sync
```

solo con consenso dell'utente.

## Suggested Fix Specification Scope

Creare una o piu' spec/task di correzione. Possibile suddivisione:

### Correction Spec A - Stabilizzazione Quality Gate

Scope:

- chiudere `TestClient`;
- eliminare `ResourceWarning`;
- rendere `pytest -m "not e2e"` exit code 0;
- aggiungere `.adev/` a `.gitignore`;
- aggiornare quickstart evidence.

Acceptance criteria:

- `uv --directory backend run pytest -m "not e2e"` termina con exit code 0;
- `adev review .` non fallisce per regressione test;
- nessun report runtime `.adev/reviews/` viene proposto da `git status`.

### Correction Spec B - Validazione Payload Conforme Al Contratto

Scope:

- applicare `field.validazione`;
- trattare valori vuoti;
- gestire vincoli string/number;
- introdurre o riusare codici errore coerenti con OpenAPI;
- aggiungere test deterministici senza Docker.

Acceptance criteria:

- `numero_posti=0` produce errore;
- stringhe obbligatorie vuote producono errore;
- vincoli dichiarati nel contratto sono applicati server-side;
- test P1 non saltano in ambiente senza Docker.

### Correction Spec C - Catalogo Storico E Validita' Versioni

Scope:

- correggere modalita' `STORICO`;
- aggiornare OpenAPI stati storico;
- controllare finestre di validita' su accesso diretto per `modello_versione_id`;
- filtrare categorie inattive;
- gestire anomalia versioni correnti duplicate.

Acceptance criteria:

- `STORICO` restituisce versioni archiviate;
- `OPERATIVA` restituisce solo pubblicate e valide;
- validazione e campi-richiesti rifiutano versioni scadute/future/non operative;
- categorie inattive non sono selezionabili in operativo;
- duplicati correnti per stesso contesto sono impediti o segnalati.

### Correction Spec D - ADev Review Scope And Ledger

Scope:

- mantenere `active_feature` nello scope review;
- distinguere finding application/workflow/tooling;
- decidere se review deve includere solo feature attiva o tutte le feature pending;
- gestire `009` gia' implementata ma non passata dal gate;
- evitare che feature spec-only `002`-`008` vengano trattate come implementate.

Acceptance criteria:

- ADev report include feature attiva e documenti correlati;
- report separa application/workflow/tooling;
- feature implementate hanno stato review chiaro;
- feature non implementate restano fuori dai finding applicativi salvo dipendenze reali.

## Recommended Fix Order

1. Stabilizzare test/gate: `TestClient`, socket warnings, `.adev/` gitignore.
2. Correggere validazione payload: vincoli, valori vuoti, test deterministici.
3. Correggere catalogo: storico, date validita', categorie inattive, duplicati correnti.
4. Aggiornare task/quickstart/OpenAPI/error catalog.
5. Rilanciare:

```bash
adev doctor .
uv --directory backend run pytest -m "not e2e"
uv --directory backend run pytest -m e2e
adev review .
```

6. Se il codice fix viene scritto da Claude, usare Codex come reviewer indipendente o
   eseguire una seconda review manuale Codex mirata alla feature attiva.
