<!--
Sync Impact Report
Version change: template -> 1.0.0
Modified principles:
- Placeholder principle 1 -> I. Boundary Ownership
- Placeholder principle 2 -> II. Contract-First Integration
- Placeholder principle 3 -> III. Configurable Document Models
- Placeholder principle 4 -> IV. Versioning, Traceability, and Reproducibility
- Placeholder principle 5 -> V. Security, Audit, and Controlled AI
Added sections:
- Domain Constraints
- Development Workflow and Quality Gates
Removed sections:
- None
Templates requiring updates:
- .specify/templates/plan-template.md: reviewed, no change required
- .specify/templates/spec-template.md: reviewed, no change required
- .specify/templates/tasks-template.md: reviewed, no change required
Runtime guidance:
- README.md: updated to reflect the installed Spec Kit workflow
- AGENTS.md: reviewed, no change required
Follow-up TODOs:
- None
-->

# CNR GEBAN Builder Modelli Constitution

## Core Principles

### I. Boundary Ownership

GEBAN MUST remain the owner of the administrative process, users, workflow,
official bando state, and upstream data collection. The Gestione Modelli e
Generazione Documenti service MUST remain the owner of document types,
categories, model versions, required fields, sections, validation of received
payloads, PDF generation metadata, and document-generation audit.

The service MUST NOT read or write the GEBAN database directly. Any feature
that needs GEBAN data MUST receive it through an explicit API contract or
event-style integration.

Rationale: the service boundary prevents hidden coupling and keeps document
generation independently evolvable.

### II. Contract-First Integration

Every integration with GEBAN MUST be described through explicit request,
response, validation, and error contracts before implementation. Published
catalog APIs MUST expose only published and currently valid model versions.
Generation APIs MUST validate incoming payloads against the selected model
contract before producing a document.

Contracts MUST define identity of the requesting system, external context id,
model version id, data payload, validation result, generated-document reference,
and conflict behavior for idempotent requests.

Rationale: GEBAN builds dynamic screens and workflows from these contracts, so
ambiguous contracts create implementation risk in both systems.

### III. Configurable Document Models

The service MUST NOT hard-code every generable document in application logic.
Document types, categories, model versions, required fields, validation rules,
sections, placeholders, and publication state MUST be managed as configuration
or persisted domain data through the builder workflow.

Only published model versions MAY be used by GEBAN for operative generation.
Changes to a published model or section MUST create a new version rather than
overwriting content already used for generated documents.

Rationale: the first use case is bando generation, but the design must also
support graduatorie, verbali, decreti, comunicazioni, and future document types.

### IV. Versioning, Traceability, and Reproducibility

Every generated document MUST be traceable to the exact model version, section
versions, input-data snapshot, validation result, requester identity, generation
time, storage reference, and file hash when available. Official PDFs MUST be
generated server-side from published models and validated data.

Generation MUST be idempotent for the combination of requesting system,
external context id, model version id, and output type. A repeated request with
the same key and same data MUST return the existing generated document; the
same key with different data MUST produce a conflict response.

Rationale: administrative documents require reproducibility, auditability, and
safe retry behavior.

### V. Security, Audit, and Controlled AI

All protected APIs MUST require Keycloak-issued JWT Bearer tokens with valid
signature, issuer, audience, expiration, caller identity, and application roles
or contextual claims. Backend authorization MUST enforce all relevant rules;
frontend enablement alone is never sufficient.

Audit events MUST be recorded for model creation, model version changes,
review, publication, archiving, validation failures, document generation,
PDF download, and authorization errors.

AI/MCP features MUST remain optional support capabilities. AI output MUST NOT
be considered official unless it passes deterministic validation, human
confirmation where required, authorization checks, and audit. AI tools MUST NOT
expose secrets, tokens, or credentials and MUST obey the same authorization
model as ordinary APIs.

Rationale: the service handles official administrative documents and must keep
responsibility, authorization, and audit explicit.

## Domain Constraints

- The service MUST return document references suitable for GEBAN and downstream
  modules; the underlying storage can be documentale, S3-compatible storage, or
  another approved backend hidden behind the service contract.
- PDF bozza and PDF ufficiale MUST be distinguishable in state, metadata, and
  audit.
- Snapshot data MUST contain only the data needed for document generation and
  audit; it MUST NOT become the authoritative source for GEBAN or external
  anagrafiche.
- Public API names, field names, states, and error codes MUST be documented
  before implementation.
- OpenAPI, JSON examples, and model data contracts SHOULD be kept current for
  every API exposed to GEBAN or internal builder clients.

## Development Workflow and Quality Gates

- Each feature MUST start with a Spec Kit specification under `specs/` before
  implementation tasks are generated.
- Specifications MUST define actors, scope, user stories, acceptance scenarios,
  functional requirements, key entities when relevant, edge cases, and measurable
  success criteria.
- Planning MUST identify integration contracts, data model, state transitions,
  idempotency behavior, security requirements, and audit events before tasks are
  implemented.
- Tasks MUST be traceable to user stories, requirements, contracts, or
  constitution principles.
- Implementation MUST NOT proceed when the plan violates a MUST principle unless
  the constitution is explicitly amended first.
- Generated artifacts and code changes MUST preserve the distinction between
  GEBAN ownership, service ownership, and storage/documentale ownership.

## Governance

This constitution supersedes ad hoc task files, chat instructions, and feature
plans when there is a conflict. Feature specifications, plans, contracts, and
tasks MUST be adjusted to comply with these principles.

Amendments require an explicit constitution update, a version bump, and a sync
impact report describing affected principles, templates, and follow-up work.
Versioning follows semantic versioning:

- MAJOR for removing or redefining governance principles in a way that changes
  prior obligations.
- MINOR for adding principles, sections, or materially expanded obligations.
- PATCH for wording clarifications that do not change obligations.

Before implementation, plans MUST pass the Constitution Check. Before delivery,
the feature artifacts SHOULD be analyzed for alignment across specification,
plan, tasks, contracts, and these principles.

**Version**: 1.0.0 | **Ratified**: 2026-06-19 | **Last Amended**: 2026-06-19
