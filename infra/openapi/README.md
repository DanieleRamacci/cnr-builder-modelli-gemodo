# OpenAPI, Swagger UI e ReDoc

Regola di progetto (costituzione, principio II - Contract-First Integration; spec
`009-fondamenta-mock-test-qualita`, FR-039..FR-041): ogni API pubblica o di integrazione
deve avere un contratto OpenAPI versionato **prima** dell'implementazione runtime
dell'endpoint, e la documentazione interattiva locale/test (Swagger UI, ReDoc o
equivalente) deve essere generata dalla stessa sorgente OpenAPI, mai da una copia
manuale o da uno schema runtime che puo' divergere dal contratto.

## Dove vivono i contratti

Ogni contratto OpenAPI versionato vive nella spec che lo possiede, non qui:

```text
specs/<NNN-nome-spec>/contracts/<nome-api>.openapi.yaml
```

`infra/openapi/` non duplica i contratti: aggrega riferimenti, esempi pubblicabili e il
catalogo errori condiviso, cosi' che backend, documentazione MkDocs e integratori esterni
abbiano un solo punto da cui partire.

## Inventario contratti (stato corrente)

| Contratto | Spec owner | API scope | Stato |
|---|---|---|---|
| [`configurazione-cataloghi-api.openapi.yaml`](../../specs/010-configurazione-cataloghi-integrazioni/contracts/configurazione-cataloghi-api.openapi.yaml) | `010` | Amministrazione integrazioni | US1/US2 e lettura dashboard implementate; connessione/verifica US3 pianificate; `/docs/configurazione-cataloghi`, `/redoc/configurazione-cataloghi` |
| [`builder-discovery-api.openapi.yaml`](../../specs/010-configurazione-cataloghi-integrazioni/contracts/builder-discovery-api.openapi.yaml) | `010` FR-016 | Builder, discovery ricorsiva, creazione modello/versione | Implementato; `/docs/builder-discovery`, `/redoc/builder-discovery` |
| [`geban-catalog-api.openapi.yaml`](../../specs/001-catalogo-contratto-geban/contracts/geban-catalog-api.openapi.yaml) | `001-catalogo-contratto-geban` | GEBAN (catalogo, campi, validazione) | Implementato |
| [`geban-discovery-endpoint.openapi.yaml`](../../specs/010-configurazione-cataloghi-integrazioni/contracts/geban-discovery-endpoint.openapi.yaml) | `010-configurazione-cataloghi-integrazioni` | **Non un'API GEMODO** — contratto che il sistema esterno GEBAN deve implementare (endpoint di discovery per `BANDO_CONCORSO`) | Consegnato al team GEBAN come riferimento (2026-09-15); combinazioni tipologia-profilo e meccanismo esatto del campo `livello` ancora da confermare con loro |
| Generazione documento/PDF | `004-generazione-documenti-pdf` | GEBAN | Da produrre prima dell'implementazione runtime |
| Stato, riferimento, download, idempotenza | `005-storage-idempotenza-consultazione` | GEBAN | Da produrre prima dell'implementazione runtime |
| API interne builder (tipi, categorie, modelli, versioni) | `002-builder-modelli` | ADMIN/BUILDER | Da produrre prima dell'implementazione runtime |

FR-016: categorie/tipologie esterne non sono piu' API interne del builder;
classificazione locale della 001 ritirata (404). La riga 002 indica solo
operazioni future non coperte dal contratto discovery della 010.
| API interne sezioni/placeholder | `003-sezioni-placeholder-versionamento` | ADMIN/BUILDER | Da produrre prima dell'implementazione runtime |
| Endpoint di sicurezza/introspezione applicativa | `006-sicurezza-autorizzazioni-audit` | INTERNO | Da produrre prima dell'implementazione runtime |

Nessun endpoint operativo deve entrare in implementazione runtime finche' la riga
corrispondente non ha un contratto OpenAPI versionato ed esempi pubblicabili (vedi
`errors.md` e `docs/api-documentation.md`).

## Pubblicazione Swagger UI / ReDoc in locale/test

Il backend (`backend/app/main.py`) espone la documentazione interattiva **direttamente
dai file YAML versionati** elencati sopra, non da uno schema generato a runtime:

- `GET /openapi/{spec}.yaml` restituisce il contratto versionato cosi' come committato.
- `GET /docs/{spec}` monta Swagger UI puntato su quell'URL.
- `GET /redoc/{spec}` monta ReDoc puntato sullo stesso URL.

In questo modo Swagger UI e ReDoc non possono divergere dalla sorgente OpenAPI: sono la
stessa sorgente, solo renderizzata. L'endpoint FastAPI nativo `/docs`/`/redoc` (schema
generato dai router implementati) resta disponibile in aggiunta, per lo sviluppo
incrementale dei singoli endpoint, ma il contratto committato resta la fonte di verita'
pubblicabile per gli integratori esterni.

Questi endpoint di pubblicazione vengono aggiunti man mano che le spec proprietarie
implementano i rispettivi router (`002`, `003`, `004`, `005`, `006`, `007`); la `009`
definisce solo la regola e l'inventario.

## Esempi pubblicabili

`infra/openapi/examples/` contiene esempi JSON verificati contro lo schema OpenAPI
reale (non solo scritti a mano):

- [`catalog-success.json`](examples/catalog-success.json): risposta di successo per
  `GET /catalogo/modelli` (schema `ModelloSearchResponse`).
- [`fields-contract-success.json`](examples/fields-contract-success.json): risposta di
  successo per `GET /catalogo/modelli/{modelloVersioneId}/campi-richiesti`, con
  `lingua` IT/EN e schema strict `additionalProperties=false`.
- [`validation-error.json`](examples/validation-error.json): risposta di errore
  funzionale per `POST /documenti/valida` con `bando_inglese=true`
  (schema `ValidazioneResponse`), coerente coi codici in `errors.md`.

Entrambi sono stati validati con `jsonschema` contro i componenti dello schema
`specs/001-catalogo-contratto-geban/contracts/geban-catalog-api.openapi.yaml` prima di
essere committati. Nessun esempio contiene token, secret, password, dati personali
reali o URL ambientali sensibili (FR-045).

`modello_id`/`modello_versione_id` sono tipizzati come interi in questo contratto. In
persistenza il backend mantiene UUID interni della baseline `009` e usa `public_id`
interi stabili per l'identificativo esposto a GEBAN.
