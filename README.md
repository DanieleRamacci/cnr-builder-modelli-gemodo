# CNR GEBAN - Builder Modelli GEMODO

Repository di progetto per il servizio Gestione Modelli e Generazione Documenti
integrato con GEBAN.

## Stato Del Progetto

Il repository usa GitHub Spec Kit per guidare specifiche, piano tecnico e task.
Il documento sorgente iniziale e':

- `PROPOSTA-servizio-gestione-modelli-bando.md`

Branch:

- `main`: produzione
- `test`: sviluppo/test/Coolify

Feature attiva:

- `specs/001-catalogo-contratto-geban`

La feature `009-fondamenta-mock-test-qualita` e' completa (`T001-T064`) e ha preparato
fondamenta, mock, test, profili di integrazione, modello documentale controllato,
documentazione API e readiness open source/PA. La feature `001-catalogo-contratto-geban`
implementa catalogo GEBAN, contratto campi, validazione payload e sicurezza JWT minima
per le route operative. La
feature `002-builder-modelli` ha stati/versioni confermati, piano e task aggiornati, e
gate `TASKS` verde. La feature `003-sezioni-placeholder-versionamento`:
formato visuale controllato confermato, piano e task aggiornati al 2026-07-31, e gate
`TASKS` verde.

## Provare Il Backend In Locale

```bash
cd backend
uv sync

uv run gemodo-quality verifica-ambiente      # healthcheck reali dell'ambiente locale
uv run pytest                                 # suite di test reale (109 test)
uv run uvicorn app.main:app --reload          # backend acceso su http://localhost:8000
# http://localhost:8000/docs/geban-catalog    -> Swagger UI del contratto 001
# http://localhost:8000/redoc/geban-catalog   -> ReDoc dello stesso contratto

uv run python ../mock-geban/scenario_runner.py --scenario E2E-001 \
  --payload bando-concorso-valid.json         # piano di uno scenario mock GEBAN
```

Comandi rapidi per le API `001` in locale, con principal mock solo per sviluppo/test:

```bash
cd backend
export GEMODO_USE_MOCK_PRINCIPAL=true
uv run alembic upgrade head
uv run uvicorn app.main:app --reload

curl -s "http://localhost:8000/api/v1/catalogo/modelli?tipo_documento=BANDO_CONCORSO&profilo=COLLABORATORE_TECNICO_ER&codice_tipologia=TD"
curl -s http://localhost:8000/api/v1/catalogo/modelli/1/campi-richiesti
```

Manifest e strumenti di qualita' principali:

Dal 2026-09-17 il catalogo esterno locale e le API di classificazione sono
dismessi (`010` FR-016, migration `0009`). Prima del deploy fare backup DB:
il downgrade richiede un ripristino. Il builder usa discovery HTTP risolta
dal registro integrazioni (`010`, `POST /api/v1/configurazione/integrazioni`,
CONNESSO dopo verifica); senza integrazione connessa risponde 503/409, mai
con dati di seed.
Modelli GEMODO, versioni e relativi contratti restano persistenti.
Configurazione e prova: [incremento discovery](specs/010-configurazione-cataloghi-integrazioni/incremento-discovery.md).

- `infra/local/quality-readiness.local.yaml`: readiness complessiva della feature 009.
- `infra/local/integration-profiles.local.yaml`: profili di integrazione GEBAN/GEMODO.
- `infra/local/document-models/`: modello documentale controllato demo.
- `mock-geban/`: mock del sistema chiamante GEBAN, scenari e payload demo.
- `docs/decision-register.yaml`: registro delle decisioni aperte (§17 proposta).
- `docs/quality-coverage-matrix.yaml`: matrice requisiti/scenari/contratti/owner.

## Documentazione Navigabile

La documentazione web viene generata dagli artefatti Spec Kit e dai file in `docs/`.

Per generare e vedere il sito in locale:

```bash
python3 scripts/generate-spec-docs.py
mkdocs serve
```

Entrate principali:

- `docs/index.md`: home della documentazione.
- `docs/spec-kit/index.md`: indice generato delle spec.
- `docs/spec-kit/active-feature.md`: feature attiva e blocco di partenza.
- `docs/spec-kit/roadmap.md`: lettura per fasi e stato artefatti.
- `docs/spec-kit/api-readiness.md`: copertura OpenAPI e API mancanti.
- `docs/spec-kit/decisions-and-vincoli.md`: decisioni chiarite, vincoli e blocchi.
- `docs/project-map.md`: mappa proposta -> spec owner.
- `docs/api-documentation.md`: regole API, OpenAPI, Swagger/ReDoc ed esempi.
- `docs/open-source-pa-readiness.md`: checklist riuso open source/PA.

I file generati sotto `docs/spec-kit/` non vanno modificati a mano: rigenerare la
documentazione dopo ogni modifica agli artefatti Spec Kit.

## Flusso Spec Kit

Usare le skill installate in `.agents/skills/` tramite l'agente AI:

```text
$speckit-constitution  # principi globali del progetto
$speckit-specify       # specifica funzionale di una feature
$speckit-clarify       # chiarimenti mirati prima del piano
$speckit-plan          # piano tecnico, data model, contratti
$speckit-checklist     # checklist qualita' requisiti
$speckit-tasks         # task implementativi
$speckit-analyze       # coerenza spec/plan/tasks
$speckit-implement     # implementazione
$speckit-converge      # riallineamento finale
```

## Regole Di Base

- La costituzione vive in `.specify/memory/constitution.md`.
- La mappa completa proposta -> aree -> spec vive in `docs/project-map.md`.
- Le feature vivono in `specs/<numero>-<nome-feature>/`.
- `PROPOSTA-servizio-gestione-modelli-bando.md` resta la fonte iniziale da cui
  estrarre specifiche piu' piccole.
- Lo stack tecnico corrente e' backend Python FastAPI, PostgreSQL/Alembic e frontend
  Angular.
- Non implementare codice prima di avere almeno `spec.md`, `plan.md` e
  `tasks.md` per la feature corrente.
- Non implementare endpoint pubblici o di integrazione prima di avere OpenAPI versionato,
  esempi JSON pubblicabili, catalogo errori e documentazione interattiva locale/test.
- Gli esempi e la documentazione pubblicabile devono usare solo dati demo e non devono
  contenere token, secret, credenziali, dati personali reali o URL ambientali sensibili.

## Spec Di Copertura

```text
specs/001-catalogo-contratto-geban/
specs/002-builder-modelli/
specs/003-sezioni-placeholder-versionamento/
specs/004-generazione-documenti-pdf/
specs/005-storage-idempotenza-consultazione/
specs/006-sicurezza-autorizzazioni-audit/
specs/007-frontend-builder-consultazione/
specs/008-ai-mcp-readiness/
specs/009-fondamenta-mock-test-qualita/
```

La feature attiva per il prossimo comando Spec Kit e':

```text
specs/001-catalogo-contratto-geban
```

## Prossimo Blocco Di Sviluppo

Per il codice applicativo la `001` ora fornisce la base API usabile da GEBAN per catalogo,
campi richiesti e validazione payload. Il prossimo blocco applicativo resta `002`, poi
`003`; la `003` riusa modello versione, pubblicazione, errori comuni e validazione JWT
condivisa.

Dopo la `001`, prima di produrre un PDF vero servono, nell'ordine:

1. Implementare la `002-builder-modelli` seguendo i 64 task aggiornati, con API builder
   protette da Keycloak e dominio catalogo condiviso con la `001`.
2. Implementare la `003-sezioni-placeholder-versionamento` seguendo i 69 task aggiornati,
   con `GEMODO_DOCUMENT_V1`, placeholder validati e campi complessi strutturati.
3. Completare il flusso Spec Kit (`plan` + `tasks`, dove mancanti o superati) per
   `006-sicurezza-autorizzazioni-audit`, `004-generazione-documenti-pdf` e
   `005-storage-idempotenza-consultazione`.
4. Solo allora sostituire lo stub `POST /documenti/genera` con generazione PDF reale,
   stato e download: lo stub attuale valida token/dati e restituisce solo un messaggio
   placeholder del futuro link.

GitHub Pages esegue `scripts/generate-spec-docs.py` nel workflow
`.github/workflows/pages.yml` prima di pubblicare il sito.

## Deploy Coolify Test

Per pubblicare l'ambiente DEV su `dev-gemodo.concorsi.cnr.it`, usare in Coolify la
modalita' Docker Compose:

```text
Build Pack: Docker Compose
Base Directory: /
Docker Compose Location: /docker-compose.coolify.yml
Domains for frontend: http://dev-gemodo.concorsi.cnr.it:80
```

Il compose applicativo avvia:

- `frontend`: pagina pubblica Nginx con link a Swagger/ReDoc/OpenAPI e proxy verso il backend.
- `backend`: FastAPI GEMODO, migration Alembic all'avvio, API `001` protette da Keycloak.
- `postgres`: database persistente per catalogo, contratti dati e seed demo.

Non impostare port mapping host manuali: il servizio `frontend` espone internamente la
porta `80` e Coolify genera la route del proxy verso quella porta. Le route `/api`,
`/docs`, `/redoc`, `/openapi` e `/health` vengono inoltrate al backend.

Variabili Coolify di riferimento:

```text
deploy/coolify.env.example
```

In test reale lasciare `GEMODO_USE_MOCK_PRINCIPAL=false`; il mock principal serve solo
per prove locali senza Keycloak. La home DEV usa login SSO CNR con client pubblico
`gemodo-frontend`; Swagger catalogo usa lo stesso client con Authorization Code + PKCE.
Per far funzionare le chiamate API con token utente, il client Keycloak `gemodo-frontend`
deve avere redirect URI e web origin per `https://dev-gemodo.concorsi.cnr.it/*`, audience
`gemodo-backend` nel token, e l'utente deve avere ruoli client su `gemodo-backend`
coerenti con l'endpoint (`DOCUMENTI_VIEWER` e, per validazione, `DOCUMENTI_GENERATORE`).
