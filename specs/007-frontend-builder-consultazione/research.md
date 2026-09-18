# Phase 0 Research: Frontend Builder E Consultazione (MVP ADR 0002)

## Framework e design system

**Decision**: Angular 21.2 (standalone components, signals) + `design-angular-kit`
21.2.0, con i suoi peer dependency `@ngx-translate/core`/`@ngx-translate/http-loader`
`^17.0.0` e `bootstrap-italia` `^2.17.4`.

**Rationale**: la Clarification "Decisione MVP 2026-09-17 - ADR 0002" in
`spec.md` conferma Angular + Design Angular Kit e rimanda al piano tecnico la
scelta delle versioni compatibili. **Correzione 2026-09-18**: la prima verifica
via `raw.githubusercontent.com/italia/design-angular-kit/main/package.json`
aveva letto il `package.json` di root del monorepo (`design-angular-kit-bundle`,
privato, uso interno di build) e non il pacchetto pubblicato realmente su npm -
`npm view design-angular-kit-bundle` risponde `404 Unpublished on
2025-02-11`. Il pacchetto pubblico reale, verificato con `npm search`/
`npm view` (non solo il repo GitHub), e' **`design-angular-kit`** (senza
suffisso `-bundle`), 21.2.0, peer `@angular/*` `^21.0.0` - compatibile con
Angular 21.2. Installato e verificato per davvero in questo incremento:
`npm install design-angular-kit@21.2.0 @ngx-translate/core@^17.0.0
@ngx-translate/http-loader@^17.0.0 bootstrap-italia@^2.17.4` in uno scaffold
Angular 21.2.24 pulito, seguito da `ng build` completato con successo.

**Alternatives considered**: nessuna - lo stack e' gia' deciso a livello di
spec/ADR, questa ricerca serve solo a fissare le versioni esatte compatibili,
non a scegliere fra framework.

## Testing

**Decision**: Vitest per gli unit test (componenti/servizi), Playwright per
gli e2e reali contro backend+mock-geban.

**Rationale**: Vitest e' il test runner di default di Angular CLI a partire
dalla 21 (Karma e' deprecato); usarlo evita di reintrodurre una dipendenza in
via di dismissione. Playwright e' lo strumento e2e standard di Angular CLI
dalla dismissione di Protractor ed esegue in un browser reale - coerente con
la regola di questo progetto (vedi memoria di sessione) di verificare
davvero, non solo con assert su mock. Gli scenari e2e per questo MVP puntano
al backend reale + `mock-geban` gia' presenti in
`infra/local/compose.yaml`, non a un backend fittizio lato frontend.

**Alternatives considered**: Karma/Jasmine (scartato, deprecato in Angular
21); Cypress (scartato, nessun vantaggio su Playwright per questo progetto e
Playwright e' gia' l'opzione di prima classe di Angular CLI).

## Consumo delle API

**Decision**: client HTTP tipizzato generato dagli OpenAPI gia' pubblicati
(`openapi-typescript` per i tipi, wrapper sottile su `HttpClient` per le
chiamate), non un generatore di client completo (es. `openapi-generator`).

**Rationale**: i contratti `integrazioni`, `configurazione-cataloghi` e
`builder-discovery` sono gia' reali e serviti da
`backend/app/quality/openapi_docs.py`. Generare solo i *tipi* (non un intero
SDK con la sua logica di retry/interceptor) lascia al frontend il controllo
esplicito sulla UX dei casi non banali gia' nel contratto (es.
`REVISIONE_SUPERATA` su un conflitto ottimistico in `configura_integrazione`
- serve una rilettura e un messaggio distinto per l'utente, non un retry
automatico silenzioso). Un generatore di client completo aggiungerebbe una
dipendenza pesante e una sua run-time da mantenere per un guadagno marginale
su un MVP di due schermate.

**Gap trovato, da chiudere prima (Foundational)**: `specs/002-builder-modelli/
contracts/builder-modelli-api.openapi.yaml` esiste ma non e' registrato in
`PUBLISHED_CONTRACTS` (`backend/app/quality/openapi_docs.py`) - niente
Swagger/ReDoc reale, e non e' mai stato riverificato contro
`backend/app/builder/api.py` dopo i riallineamenti discovery/integrazioni di
T081-T083. Va verificato e pubblicato prima di generare tipi da un contratto
potenzialmente disallineato (altrimenti la UI manager si affiderebbe a forme
di richiesta/risposta sbagliate).

**Alternatives considered**: `openapi-generator-cli` con il template
`typescript-angular` (scartato per il motivo sopra); scrivere i tipi a mano
(scartato, drift garantito contro il contratto reale, viola lo spirito del
Principio II).

## Autenticazione

**Decision**: `keycloak-js` + `keycloak-angular`, Authorization Code + PKCE,
client id `gemodo-frontend` (gia' provisionato e nell'allowlist backend).

**Rationale**: `gemodo-frontend` e' gia' il client id atteso da
`infra/local/compose.yaml` e da `gemodo_allowed_interactive_clients` in
`backend/app/core/settings.py` - nessuna nuova configurazione Keycloak lato
backend richiesta. PKCE e' lo standard per una SPA pubblica (nessun client
secret nel browser). Il frontend abilita/disabilita azioni in base a
ruolo/contesto del token SOLO per UX (spec.md FR-008); l'enforcement
autoritativo resta sempre lato backend, gia' vero oggi per ogni API
consumata da questo MVP.

**Alternatives considered**: token statico/mock per lo sviluppo locale
(disponibile solo come comodo per lo sviluppo via
`GEMODO_USE_MOCK_PRINCIPAL` lato backend, MAI come sostituto del flusso
Keycloak reale nell'app - stessa distinzione gia' fatta nei test backend fra
principal mockati e JWT reali).

## Gestione dello stato

**Decision**: Angular signals nativi, nessuna libreria di state management
(NgRx/Akita) per questo incremento.

**Rationale**: due aree funzionali, nessuno stato condiviso complesso fra
feature non correlate; introdurre NgRx per un MVP di questa dimensione
sarebbe un'astrazione prematura. Rivalutare se/quando la consultazione
generazioni (User Story 3) e il builder pieno (User Story 1/2) vengono
pianificati.

**Alternatives considered**: NgRx (scartato per lo scope attuale, non
escluso per incrementi futuri piu' grandi).
