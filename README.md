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
documentazione API e readiness open source/PA. Il prossimo blocco operativo e' la
feature `001-catalogo-contratto-geban`: `spec.md`, `plan.md` e `tasks.md` sono gia'
aggiornati alle decisioni del 2026-07-29 e al chiarimento sicurezza del 2026-07-31.
Il readiness gate per `TASKS` e' verde; l'implementazione puo' partire da `T001`. Vedi
`docs/project-map.md`.

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

Manifest e strumenti di qualita' principali:

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

Per la feature attiva (`001`) il readiness gate per `TASKS` e' verde. Il lavoro
successivo e' avviare l'implementazione da `T001` in
`specs/001-catalogo-contratto-geban/tasks.md`, includendo la protezione JWT Keycloak
minima prevista dai task foundational.

Dopo la `001`, prima di produrre un PDF vero servono, nell'ordine:

1. Propagare nelle `spec.md` di `002` e `003` le decisioni ormai `CONFERMATA`
   che le riguardano (vedi `docs/decision-register.yaml`), poi rigenerare i loro
   `plan.md`/`tasks.md` (sono fermi al 19 giugno 2026 e non li riflettono).
2. Completare il flusso Spec Kit (`plan` + `tasks`, dove mancanti o superati) per
   `006-sicurezza-autorizzazioni-audit`, `004-generazione-documenti-pdf` e
   `005-storage-idempotenza-consultazione`.
3. Solo allora implementare `POST /documenti/genera`, stato e download: nessun
   renderer PDF esiste ancora oggi.

GitHub Pages esegue `scripts/generate-spec-docs.py` nel workflow
`.github/workflows/pages.yml` prima di pubblicare il sito.

## Deploy Coolify Test

Per pubblicare la pagina statica di stato su `dev-gemodo.concorsi.cnr.it`, usare in
Coolify la modalita' Docker Compose:

```text
Build Pack: Docker Compose
Base Directory: /
Docker Compose Location: /docker-compose.coolify.yml
Domains for frontend: http://dev-gemodo.concorsi.cnr.it:80
```

Non impostare port mapping host manuali: il servizio `frontend` espone internamente la
porta `80` e Coolify genera la route del proxy verso quella porta.
