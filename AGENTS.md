<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan
at specs/012-editor-documento-fedele/plan.md
<!-- SPECKIT END -->

## Documentazione di riferimento

Le pagine in `docs/` descrivono il sistema per integratori, utenti e agenti. Prima di lavorare su un'area, leggere la pagina corrispondente:

- `docs/architettura.md`: componenti, concetti, cosa e' conservato e cosa e' letto dal vivo, modularita', sicurezza, limiti noti.
- `docs/contratto-dati.md`: discovery (un discovery per integrazione, con piu' tipi documento), campi, conformita', validazione dei dati, campi ripetibili 0.8.0 proposti (spec 014).
- `docs/integrazione-sistema-esterno.md`: flusso generico per un sistema esterno.
- `docs/riferimento-api.md`: tutte le rotte con permessi e contratti OpenAPI, codici di errore, lacune note.
- `docs/casi/geban.md`: valori concreti di GEBAN (prima integrazione).

Regole:

- **Il codice prevale sulla documentazione.** Prima di affermare un comportamento, verificarlo nel codice; la versione attiva del contratto discovery e' `VERSIONE_CONTRATTO_DISCOVERY` in `backend/app/discovery/schemas.py`.
- **Se codice e documentazione divergono, la pagina si corregge nello stesso lavoro.** `backend/tests/contract/test_documentazione_allineata.py` confronta con il codice rotte, contratti, codici di errore, esempi di discovery, versione attiva, stati e profilo GEBAN; `cd frontend && npm run docs:check` verifica che la copia mostrata nell'app sia allineata e che i link interni funzionino (dopo una modifica a `docs/`: `npm run docs:sync`).

<!-- adev-standard:begin -->
## AI Development Standard

This repository follows the local AI Development Standard recorded in `.specify/config/standard.yml`.

Use GitHub Spec Kit's workflow without replacing core commands:

```text
constitution -> specify -> clarify -> plan -> tasks -> analyze -> implement -> review -> converge
```

`review` is the AI Development Standard quality gate. `converge` remains responsible for checking alignment between intent and current codebase and appending remaining work to `tasks.md`.

A feature is not complete until independent verification has passed. The reviewer must run in an isolated session and must not receive developer reasoning or conversation history. The reviewer may receive only the constitution, spec, plan, task file, resulting repository, diff, available tests, and deterministic test results.

The independent reviewer must actively look for bugs, regressions, missing requirements, partial implementations, edge cases, weak error handling, security issues, insufficient tests, unrequested changes, compatibility issues, and indirect impact on shared code. The PASS/FAIL outcome is determined by configured policy, not by free-form reviewer judgment.

Before implementation or review, read `.specify/config/tools.yml`. This file is an operational policy, not only an `adev doctor` checklist.

For every tool with `enabled: true`:

- verify the current state with `adev doctor` or an equivalent deterministic check;
- treat the tool as part of the project's operating standard;
- use it when its status is `READY` and its `use_when` conditions apply;
- report `NOT_INSTALLED`, `NOT_CONFIGURED`, `PROJECT_NOT_INITIALIZED`, or `DISABLED` states instead of silently ignoring the tool;
- treat `required: true` tools that are not `READY` as blocking quality-gate problems;
- treat `required: false` tools that are not `READY` as visible, non-blocking operational recommendations;
- do not install global tools automatically without explicit user consent or a dedicated flag/configuration;
- respect `initialize.automatic: false` and do not initialize project tool state automatically.

Use structural tools such as CodeGraph or TokenSave to reduce context size, reduce token usage, analyze dependency impact, and avoid unnecessary full-repository reads when their policy says they apply.
<!-- adev-standard:end -->

<!-- CODEGRAPH_START -->
## CodeGraph

In repositories indexed by CodeGraph (a `.codegraph/` directory exists at the repo root), reach for it BEFORE grep/find or reading files when you need to understand or locate code:

- **MCP tool** (when available): `codegraph_explore` answers most code questions in one call — the relevant symbols' verbatim source plus the call paths between them, including dynamic-dispatch hops grep can't follow. Name a file or symbol in the query to read its current line-numbered source. If it's listed but deferred, load it by name via tool search.
- **Shell** (always works): `codegraph explore "<symbol names or question>"` prints the same output.

If there is no `.codegraph/` directory, skip CodeGraph entirely — indexing is the user's decision.
<!-- CODEGRAPH_END -->
