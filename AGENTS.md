<!-- SPECKIT START -->
Before working on this project, read:

1. `.specify/memory/constitution.md` for non-negotiable project principles.
2. `docs/project-map.md` for proposal-section coverage and spec ownership.
3. `.specify/feature.json` to identify the active feature for Spec Kit commands.
4. `specs/006-sicurezza-autorizzazioni-audit/plan.md` for the current technical plan.
5. The active feature's `spec.md` before changing requirements.

The current active feature is `specs/006-sicurezza-autorizzazioni-audit`.

Do not implement application code before the active feature has `tasks.md`.

Implementation tracking rules:

- Work only on the active feature declared in `.specify/feature.json`.
- Complete or explicitly suspend tasks for the active feature.
- Do not start tasks from another spec without updating `.specify/feature.json` and getting user confirmation.
- Mark every completed task as `[x]` in the active feature's `tasks.md`.
- If a task is left partially done, add an `IN CORSO` note or a residual sub-task in `tasks.md`.
<!-- SPECKIT END -->

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
