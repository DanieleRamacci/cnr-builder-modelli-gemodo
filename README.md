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

- `specs/009-fondamenta-mock-test-qualita`

La feature attiva prepara fondamenta, mock, test, qualita', profili di integrazione,
modello documentale controllato, documentazione API e readiness open source/PA. Le
fasi 1-5 (`T001-T058`) sono implementate e verificate con 109 test reali; resta il
Polish (`T059-T064`). Vedi `docs/project-map.md` per lo stato aggiornato di tutte le
spec, incluso un avviso importante: `001`, `002` e `003` hanno gia' `plan.md`/`tasks.md`
ma risalgono al 19 giugno 2026, prima delle decisioni successive - vanno aggiornati e
ripianificati prima di implementarli.

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
specs/009-fondamenta-mock-test-qualita
```

## Prossimo Blocco Di Sviluppo

Per la feature attiva (`009`) resta solo il Polish (`T059-T064`): note di
documentazione generata, esempi API pubblicabili, validazione sintassi/YAML, build
MkDocs e revisione del quickstart contro gli output reali.

Dopo il Polish, prima di produrre un PDF vero servono, nell'ordine:

1. Propagare nelle `spec.md` di `001`, `002`, `003` le decisioni ormai `CONFERMATA`
   che le riguardano (vedi `docs/decision-register.yaml`), poi rigenerare i loro
   `plan.md`/`tasks.md` (sono fermi al 19 giugno 2026 e non li riflettono).
2. Completare il flusso Spec Kit (`plan` + `tasks`, non ancora esistenti) per
   `006-sicurezza-autorizzazioni-audit`, `004-generazione-documenti-pdf` e
   `005-storage-idempotenza-consultazione`.
3. Solo allora implementare `POST /documenti/genera`, stato e download: nessun
   renderer PDF esiste ancora oggi.

GitHub Pages esegue `scripts/generate-spec-docs.py` nel workflow
`.github/workflows/pages.yml` prima di pubblicare il sito.
