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
modello documentale controllato, documentazione API e readiness open source/PA.

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

Per la feature attiva il blocco iniziale e':

- `T001-T008`: skeleton backend, frontend, infra e mock.
- `T009-T025`: manifest qualita', loader, profili integrazione, confine Keycloak/GEMODO,
  modello documentale controllato, API documentation readiness e open source/PA readiness.

Per l'MVP API + PDF servira' poi completare il flusso Spec Kit operativo di:

- `004-generazione-documenti-pdf`
- `005-storage-idempotenza-consultazione`

Queste spec devono produrre plan, data model, OpenAPI, quickstart e tasks prima di
implementare `POST /documenti/genera`, stato e download.

GitHub Pages esegue `scripts/generate-spec-docs.py` nel workflow
`.github/workflows/pages.yml` prima di pubblicare il sito.
