# Specification Quality Checklist: Sicurezza Autorizzazioni E Audit

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-06-19
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details beyond project-level authentication constraint
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic where possible for a security feature
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No unrelated implementation details leak into specification

## Notes

- Draft di copertura. Keycloak/JWT e' un vincolo di costituzione/proposta, non una scelta nuova.
- Documento operativo collegato: `keycloak-jwt.md`.
- Decisione `SEC-006-001` **risolta il 2026-07-29** e aggiornata il 2026-09-14: token
  tecnico Keycloak `geban-backend` mantenuto per test/CI; integrazione reale GEBAN
  supportata anche con token ACE, audience `gemodo-backend` e ruoli in
  `contexts.geban.roles`.
- Utenti, password e assegnazione ruoli restano in Keycloak; GEMODO consuma JWT e applica autorizzazioni backend.
- Validazione aggiornata il 2026-06-22 dopo estensione requisiti su matrice ruoli, audit
  minimo, API tecniche censite e AI/MCP.
- Decisione `SEC-006-002` **risolta il 2026-07-29**: nessuna separazione effettiva tra
  gestore, revisore e approvatore nella prima release; la pubblicazione fatta da
  `GEMODO_MODELLI_GESTORE` vale come approvazione. Ruoli revisore/approvatore restano
  riservati e inattivi per un'eventuale attivazione futura.
- Aggiornamento 2026-09-14: la spec include la modalita' ACE/context roles per GEBAN.
  I token ACE devono avere issuer `https://sso.test.si.cnr.it/auth/realms/cnr`,
  audience `gemodo-backend`, client chiamante censito e ruoli in `contexts.geban.roles`
  mappati a permessi GEMODO.
- Mapping iniziale GEBAN confermato: `ROLE_GESTORE#geban`, `ROLE_MANAGER#geban`,
  `ROLE_COORDINATOR#geban` e `ROLE_USER#geban` possono derivare
  `DOCUMENTI_GENERATORE`; solo `ROLE_MANAGER#geban` puo' derivare
  `GEMODO_MODELLI_GESTORE` per il builder nel perimetro GEBAN.
- Nessuna decisione bloccante differita al momento; la feature puo' passare alla
  pianificazione.
