# Implementation Plan: Sicurezza Autorizzazioni E Audit

**Branch**: `006-sicurezza-autorizzazioni-audit` | **Date**: 2026-09-14 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/006-sicurezza-autorizzazioni-audit/spec.md`

**Note**: Piano aggiornato per supportare il flusso ACE/context roles richiesto dal
team GEBAN, mantenendo compatibile il doppio tecnico `geban-backend` per test/CI.

## Summary

GEMODO deve accettare JWT Keycloak emessi dal realm CNR solo quando firma, issuer,
scadenza e audience sono validi, e deve autorizzare le operazioni usando permessi
applicativi interni. I permessi possono arrivare direttamente da
`resource_access.gemodo-backend.roles` oppure essere derivati dai ruoli ACE presenti in
`contexts.<app>.roles` tramite mapping configurabile.

La configurazione di destinazione viene centralizzata nel profilo di integrazione
`infra/local/integration-profiles.local.yaml`: nello stesso profilo GEBAN sono censiti
client ammessi, audience attesa, contesto token, perimetro catalogo/documenti ammesso e
mappatura ruoli esterni -> permessi GEMODO. Il catalogo puro resta in
`infra/local/postgres/seed-demo-catalog.yaml` e continua a definire le entita' di dominio,
non le autorizzazioni.

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: Python 3.12

**Primary Dependencies**: FastAPI, Pydantic v2, SQLAlchemy, PyYAML, PyJWT, httpx

**API Documentation**: OpenAPI/Swagger/ReDoc gia' pubblicati per API catalogo/GEBAN;
questa feature aggiorna la documentazione sicurezza e il contratto di configurazione
autorizzativa, senza introdurre nuovi endpoint pubblici.

**Storage**: PostgreSQL per dominio/catalogo/audit esistenti; YAML versionato per profili
di integrazione locali e mapping ruoli.

**Testing**: pytest (`backend/tests/common`, `backend/tests/integration`, `backend/tests/e2e`)

**Target Platform**: Backend web service Linux/container, ambienti locale/test CNR.

**Project Type**: Web service backend FastAPI con frontend/browser SSO previsto da spec
successive.

**Performance Goals**: autorizzazione JWT e mapping ruoli eseguiti in memoria per singola
richiesta, senza round-trip verso Keycloak o database autorizzativo.

**Constraints**: audience `gemodo-backend` sempre obbligatoria; nessun ruolo esterno
hard-coded negli endpoint; nessun token o secret in log/audit; configurazione modificabile
per nuovi applicativi senza cambiare contratti pubblici.

**Scale/Scope**: primo contesto reale `geban`, client ACE comunicato `geri-angular-public`
o equivalente; supporto generalizzato a piu' contesti/applicativi.

**Reuse/Public Documentation**: [keycloak-jwt.md](./keycloak-jwt.md), contratto
`contracts/authorization-mapping.schema.yaml`, quickstart di verifica token/config,
eventuali note README/docs sicurezza se collegate dal portale documentale.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**I. Boundary Ownership**: PASS. GEBAN/ACE restano fonte di processo e ruoli; GEMODO
valida token e applica autorizzazioni proprie senza leggere DB GEBAN.

**II. Contract-First Integration**: PASS. Il mapping e le claim attese sono documentati
prima del codice in [keycloak-jwt.md](./keycloak-jwt.md) e nel contratto YAML.

**III. Configurable Document Models**: PASS. La mappatura autorizzativa resta separata dal
catalogo puro e riferisce codici pubblici/versionati, senza hard-code endpoint.

**IV. Versioning, Traceability, and Reproducibility**: PASS. La configurazione e'
versionata nel repository; gli audit devono registrare attore/client/contesto senza token.

**V. Security, Audit, and Controlled AI**: PASS. JWT Keycloak, audience, client ammessi e
ruoli/claim contestuali sono obbligatori; AI/MCP resta soggetto allo stesso modello.

**VI. Public Documentation and Reuse Readiness**: PASS. La feature produce documenti
testuali versionati e pubblicabili, senza segreti o token reali.

## Project Structure

### Documentation (this feature)

```text
specs/006-sicurezza-autorizzazioni-audit/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```text
backend/
├── app/
│   ├── common/security.py                 # JWT principal, role extraction, guards
│   ├── core/settings.py                   # issuer/audience/allowed clients settings
│   └── quality/
│       ├── integration_profile.py         # loader/validator profili integrazione
│       └── schemas.py                     # schema Pydantic profili/mapping
└── tests/
    ├── common/test_security_jwt.py        # token, roles, authorization guards
    ├── integration/test_*                 # profili e manifest
    └── support/                           # fixture token/profili

infra/local/
├── integration-profiles.local.yaml        # client ammessi, contesti, mapping ruoli
├── keycloak/realm-gemodo.local.json       # doppio locale/test Keycloak
└── postgres/seed-demo-catalog.yaml        # catalogo dominio, non autorizzazioni
```

**Structure Decision**: feature backend/config/documentale. La mappatura ruoli esterni
viene implementata nel profilo di integrazione per sistema richiedente, riusando il loader
YAML esistente e normalizzando i permessi nel layer `common/security.py`.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |
