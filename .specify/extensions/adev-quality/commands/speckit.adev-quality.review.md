---
description: Run the AI Development Standard independent review quality gate.
---

## Goal

Run `adev review` from the repository root after implementation and before final workflow completion.

The review is independent verification. It complements `speckit.converge`: review focuses on bugs, regressions, missing requirements, security, test evidence, and unintended changes; converge remains responsible for checking current codebase alignment with spec, plan, and tasks and appending remaining work to `tasks.md`.

## Execution

Run:

```bash
adev review
```

The command MUST fail closed if configured regression checks fail, reviewer reports are malformed, or blocking findings are present according to `.specify/config/review.yml`.
