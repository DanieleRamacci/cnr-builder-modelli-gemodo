# Implementation Plan: Frontend Builder E Consultazione

**Branch**: `test` | **Date**: 2026-09-18 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/007-frontend-builder-consultazione/spec.md`

## Summary

Questo incremento copre solo l'MVP confermato dalla Clarification "Decisione MVP
2026-09-17 - ADR 0002" in `spec.md`: un'interfaccia Angular con Design Angular
Kit per (a) l'admin che registra, configura e verifica un'integrazione (FR-021),
e (b) il manager che naviga la struttura scoperta live di un'integrazione
connessa e crea un modello di test in BOZZA senza editor (FR-022/FR-023). Tutte
le API necessarie esistono gia' e sono verificate (specs 010, 002 - vertical
slice reale, 004/005). L'editor visuale, la composizione manuale delle sezioni
(FR-011) e la consultazione generazioni (User Story 3, P2) restano fuori scope:
obiettivi successivi, non prerequisiti di questo MVP. Le User Story 1/2 piene
(gestione completa modelli/sezioni, revisione/pubblicazione da interfaccia)
restano scope futuro oltre questo incremento.

## Technical Context

**Language/Version**: TypeScript 5.9 su Angular 21.2 (standalone components,
signals, nessun `NgModule`).

**Primary Dependencies**: `@angular/*` 21.2.x, `design-angular-kit` 21.2.0 (con
`@ngx-translate/core`/`@ngx-translate/http-loader` `^17.0.0` e
`bootstrap-italia` `^2.17.4`; peer-compatibile con Angular 21.2, verificato su
npm e installato per davvero il 2026-09-18 - vedi `research.md` per la
correzione sul nome pacchetto corretto), `keycloak-js` + `keycloak-angular`
per OIDC Authorization Code + PKCE contro il client Keycloak gia' provisionato
`gemodo-frontend` (vedi `infra/local/compose.yaml` e
`gemodo_allowed_interactive_clients` in `backend/app/core/settings.py`).

**API Documentation**: consumo diretto dei contratti OpenAPI gia' pubblicati e
verificati da `backend/app/quality/openapi_docs.py`
(`PUBLISHED_CONTRACTS`): `integrazioni` (`/openapi/integrazioni.yaml`,
admin), `configurazione-cataloghi` (admin, letture dashboard),
`builder-discovery` (letture manager). **Gap trovato**: esiste gia'
`specs/002-builder-modelli/contracts/builder-modelli-api.openapi.yaml`
(creazione/versioni/pubblicazione modello) ma non e' registrato in
`PUBLISHED_CONTRACTS` - non ha mai uno Swagger/ReDoc reale ne' e' mai stato
verificato contro l'implementazione effettiva di `backend/app/builder/api.py`
dopo i riallineamenti T081-T083. Chiuderlo (verificare e pubblicare) e'
Foundational per questo incremento, prima di generare un client tipizzato da
un contratto potenzialmente disallineato.

**Storage**: N/A lato frontend (nessuno stato server-side proprietario; la
sorgente di verita' resta sempre il backend).

**Testing**: Vitest (default Angular 21 per gli unit test dei componenti/
servizi) + Playwright per test e2e reali contro il backend reale (Postgres +
mock-geban via `infra/local/compose.yaml`), coerente con la
regola di questo progetto di verificare per davvero, non solo con mock UI.

**Target Platform**: browser desktop moderni (ultime 2 versioni Chrome/
Firefox/Edge), nessun requisito mobile in questo MVP.

**Project Type**: web application (frontend Angular + backend FastAPI gia'
esistente, comunicazione via HTTP/JSON + Bearer JWT).

**Performance Goals**: nessun requisito quantitativo per questo MVP (basso
numero di utenti interni, non un servizio ad alto traffico); interazioni admin/
manager devono restare percepibili come immediate (< 1s) sulla rete CNR
interna, senza soglia formale misurata in questo incremento.

**Constraints**: il frontend MUST NOT diventare fonte autoritativa di
autorizzazione, stato di pubblicazione, audit o disponibilita' file (spec.md
Assumptions); ogni azione sensibile passa comunque dal controllo backend gia'
implementato (010 T081-083).

**Scale/Scope**: 2 aree funzionali in questo incremento (admin integrazioni,
manager creazione modello di test), non l'intero builder/consultazione della
spec.

**Reuse/Public Documentation**: `README.md` e `docs/project-map.md` vanno
aggiornati con come avviare il frontend reale (oggi descrivono solo il
placeholder); nessun impatto sulla documentazione di sicurezza/architettura
oltre menzionare che l'enforcement resta sempre lato backend.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Boundary Ownership**: PASS. Il frontend non legge/scrive mai GEBAN
  direttamente; parla solo con le API GEMODO gia' esistenti.
- **II. Contract-First Integration**: PASS con un'azione Foundational
  (vedi sopra, gap `builder-modelli-api.openapi.yaml` non pubblicato) da
  chiudere prima della generazione del client tipizzato. Tutti gli altri
  contratti necessari a questo MVP sono gia' pubblicati e verificati.
- **III. Configurable Document Models**: N/A per questo incremento (nessuna
  logica di documento hard-codata nel frontend; la struttura viene letta
  dalla discovery live).
- **IV. Versioning, Traceability, Reproducibility**: PASS. Il frontend non
  introduce stato proprio; ogni azione (creazione, verifica) passa dalle API
  gia' audit-tate.
- **V. Security, Audit, Controlled AI**: PASS. Autenticazione via Keycloak
  JWT reale (nessun bypass), enablement UI su ruolo/contesto ma enforcement
  sempre server-side (gia' vero oggi per tutte le API consumate).
- **VI. Public Documentation and Reuse Readiness**: azione richiesta (non
  bloccante per iniziare, ma prima della consegna di questo incremento):
  aggiornare `README.md`/`docs/project-map.md` con le istruzioni reali di
  avvio frontend.

Nessuna violazione che richieda Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/007-frontend-builder-consultazione/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md         # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (contratti UI-specifici, se servono)
└── tasks.md             # Phase 2 output (/speckit-tasks - non creato qui)
```

### Source Code (repository root)

```text
backend/            # gia' esistente, nessuna modifica architetturale attesa
                     # (solo il fix di pubblicazione OpenAPI Foundational sopra)

frontend/            # gia' scaffolded come placeholder (007), diventa reale qui
├── package.json      # oggi placeholder ("gli script reali vengono introdotti
│                      # dai task della spec 007") - sostituito da un vero
│                      # progetto Angular in questo incremento
├── src/
│   ├── app/           # shell, routing, auth guard Keycloak
│   ├── features/
│   │   ├── configurazione/   # NUOVO: schermate admin integrazioni (FR-021)
│   │   ├── builder/          # ESISTENTE (placeholder) -> manager: naviga
│   │   │                     # struttura live + crea modello di test (FR-022/023)
│   │   └── generazioni/      # ESISTENTE (placeholder), FUORI SCOPE in questo
│   │                          # incremento (User Story 3, P2)
│   └── shared/         # ESISTENTE (placeholder): client HTTP tipizzato
│                        # generato dagli OpenAPI, interceptor auth, componenti
│                        # Design Angular Kit condivisi
└── e2e/                # NUOVO: scenari Playwright reali (admin registra+
                          # verifica un'integrazione contro mock-geban; manager
                          # crea un modello di test end-to-end)
```

**Structure Decision**: riuso della struttura placeholder gia' presente in
`frontend/` (creata quando questa spec era ancora "Draft"), aggiungendo solo
`features/configurazione/` (non previsto al momento dello scaffold, perche'
FR-021..023 sono arrivati con l'ADR 0002 il 2026-09-17). `features/
generazioni/` resta un placeholder vuoto: non viene toccato in questo
incremento. Nessuna cartella `builder/editor` o simile viene creata - l'MVP
usa solo le schermate di navigazione/creazione, non un editor.

## Complexity Tracking

Nessuna violazione della Constitution Check da giustificare.
