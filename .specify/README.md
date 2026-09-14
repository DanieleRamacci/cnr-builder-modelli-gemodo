# Spec Kit and AI Development Standard

This project uses GitHub Spec Kit as the primary workflow.

`adev` is installed as a bootstrapper and quality/tooling extension for Spec Kit. It does not replace the Spec Kit workflow and should not be treated as a parallel process.

## Normal Workflow

Use the standard Spec Kit flow for feature work:

```text
constitution -> specify -> clarify -> plan -> tasks -> analyze -> implement -> converge
```

The AI Development Standard review gate is configured as a Spec Kit hook after implementation. The hook runs `speckit.adev-quality.review`, which invokes `adev review` as the underlying quality gate.

## Human Editing Points

- `AGENTS.md`: operating instructions for coding agents.
- `.specify/config/tools.yml`: support-tool policy, including enabled/required tools and when agents should use them.
- `.specify/config/review.yml`: independent review gate policy, providers, regression commands, and blocking severities.
- `.specify/config/standard.yml`: standard metadata and workflow declaration.
- `.specify/memory/constitution.md`: project constitution and standard amendments.

## Usually Do Not Edit

- `.specify/extensions/adev-quality/`: packaged Spec Kit extension files.
- `.specify/extensions.yml`: generated extension and hook registration.
- `.specify/extensions/.registry`: Spec Kit extension registry when supported.

## Useful Diagnostics

Run these only when you want to inspect or debug the setup:

```bash
adev doctor .
adev adopt .
adev review .
```

`adev review` is available as a manual fallback, but the intended daily flow is to use Spec Kit and let the configured hook run the review gate.
