<!--
Sync Impact Report
Version change: 1.0.0 -> 1.1.0
Modified principles:
- I. Boundary Ownership: unchanged
- II. Contract-First Integration: expanded with API documentation gates
- III. Configurable Document Models: unchanged
- IV. Versioning, Traceability, and Reproducibility: unchanged
- V. Security, Audit, and Controlled AI: unchanged
- Added VI. Public Documentation and Reuse Readiness
Added sections:
- Public Documentation and Reuse Readiness principle
Removed sections:
- None
Templates requiring updates:
- .specify/templates/plan-template.md: updated
- .specify/templates/spec-template.md: reviewed, no change required
- .specify/templates/tasks-template.md: updated
Runtime guidance:
- README.md: updated
- AGENTS.md: reviewed, no change required
Follow-up TODOs:
- Confirm definitive open source license with project owner before public release
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

Every public or integration API MUST have a versioned OpenAPI contract, success
examples, functional error examples, authentication requirements, authorization
notes, and stable public names for endpoints, fields, states, and error codes
before runtime implementation starts. Local and test environments MUST expose
interactive API documentation suitable for validation by integrators, such as
Swagger UI and ReDoc generated from the same OpenAPI source.

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

### VI. Public Documentation and Reuse Readiness

The project MUST be maintained as software that can be inspected, reused, and
integrated by other public administrations. The repository MUST provide
versioned textual documentation for setup from zero, local development,
production deployment, architecture, configuration, API usage, security model,
data contracts, operational states, error catalog, testing, contribution,
security reporting, and release notes.

Documentation MUST be navigable from the repository README and the generated
documentation site. Generated documentation MUST be reproducible from repository
sources and MUST NOT require private knowledge, private documents, or local
machine state to understand the implemented behavior. Public examples MUST use
demo data only and MUST NOT contain secrets, credentials, real personal data, or
environment-specific tokens.

Before public release or registration for reuse, the repository MUST include a
license decision, contribution and security reporting guidance, installation and
deployment documentation, and enough API documentation for another
administration or integrator to call the service without reading the source
code.

Rationale: the service is intended for reuse and collaboration, so integration
and operational knowledge must be explicit, versioned, and safe to publish.

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
- OpenAPI, JSON examples, and model data contracts MUST be kept current for
  every API exposed to GEBAN or internal builder clients.
- Swagger UI, ReDoc, or equivalent generated API reference MUST be available in
  local/test environments from the versioned OpenAPI contracts.

## Development Workflow and Quality Gates

- Each feature MUST start with a Spec Kit specification under `specs/` before
  implementation tasks are generated.
- Specifications MUST define actors, scope, user stories, acceptance scenarios,
  functional requirements, key entities when relevant, edge cases, and measurable
  success criteria.
- Planning MUST identify integration contracts, data model, state transitions,
  idempotency behavior, security requirements, and audit events before tasks are
  implemented.
- Planning MUST identify OpenAPI outputs, example payloads, generated API
  documentation, and public reuse documentation for every API-bearing feature.
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
plan, tasks, contracts, documentation, and these principles.

**Version**: 1.1.0 | **Ratified**: 2026-06-19 | **Last Amended**: 2026-07-29
