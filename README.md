# CNR GEBAN - Builder Modelli GEMODO

Repository di progetto per il servizio Gestione Modelli e Generazione Documenti
integrato con GEBAN.

## Stato

Il repository usa GitHub Spec Kit per guidare specifiche, piano tecnico e task.
Il documento sorgente iniziale e':

- `PROPOSTA-servizio-gestione-modelli-bando.md`

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
specs/006-sicurezza-autorizzazioni-audit
```
