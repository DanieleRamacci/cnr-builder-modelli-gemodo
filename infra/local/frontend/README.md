# Frontend locale

Servizio `frontend` dell'ambiente locale GEMODO (`infra/local/compose.yaml`).

- Placeholder di planning: gli script Angular reali (`ng serve`, `ng build`, `ng test`)
  vengono introdotti dai task della spec `007-frontend-builder-consultazione`.
- In locale espone la porta `4200` e chiama il backend su `GEMODO_API_BASE_URL`
  (default `http://localhost:8000`).
- Il login utente usa SSO Keycloak (`KEYCLOAK_ISSUER_URL`, `KEYCLOAK_CLIENT_ID`, default
  `gemodo-frontend`), coerente con `sso.test.si.cnr.it` realm `cnr` in test.

## Healthcheck

Fino all'implementazione della `007`, la verifica ambiente (`VerificaAmbiente`) tratta il
frontend come `PARTIAL`/prerequisito non soddisfatto se il container non risponde su
`4200`, senza bloccare gli scenari mock GEBAN che non richiedono UI.
