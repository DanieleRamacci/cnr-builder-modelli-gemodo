# Documentazione API

Questa pagina definisce come devono essere documentate le API GEMODO prima dello
sviluppo runtime degli endpoint.

## Regola Di Progetto

- Ogni API pubblica o di integrazione deve avere un contratto OpenAPI versionato.
- Swagger UI e ReDoc, o equivalenti, devono essere generati dalla stessa sorgente OpenAPI.
- Ogni flusso rilevante deve avere esempi JSON pubblicabili di successo e di errore.
- Endpoint, campi, stati e codici errore pubblici devono essere stabili e documentati.
- Gli esempi non devono contenere token, secret, password, dati personali reali o URL
  ambientali sensibili.

## Stato Attuale

- `001-catalogo-contratto-geban` ha gia' un contratto OpenAPI per catalogo, campi
  richiesti e validazione payload.
- `004-generazione-documenti-pdf` deve ancora produrre OpenAPI per la generazione PDF.
- `005-storage-idempotenza-consultazione` deve ancora produrre OpenAPI per stato,
  riferimento, download e idempotenza.
- `009-fondamenta-mock-test-qualita` governa readiness, esempi, mock e gate.

## API MVP Da Coprire

Prima di implementare il flusso API + PDF devono essere documentati almeno:

- `POST /documenti/genera`
- `GET /documenti/generazioni/{id}/stato`
- `GET /documenti/generazioni/{id}/download` o endpoint/riferimento equivalente

Per ciascuno devono essere presenti request, response, stati, errori funzionali,
autenticazione JWT/OIDC, autorizzazioni GEMODO, esempi e comportamento idempotente.

## Documentazione Interattiva Locale/Test

Swagger UI e ReDoc vengono pubblicati dal backend a partire dagli stessi file OpenAPI
versionati elencati sotto ogni spec proprietaria, senza copie manuali (vedi
`infra/openapi/README.md` per il meccanismo `GET /openapi/{spec}.yaml` +
`GET /docs/{spec}` + `GET /redoc/{spec}`). L'inventario aggiornato dei contratti
presenti e mancanti vive in `infra/openapi/README.md`; il catalogo errori funzionali
condiviso vive in `infra/openapi/errors.md`.

## Esempi Pubblicabili

`infra/openapi/examples/catalog-success.json` (successo, `GET /catalogo/modelli`) e
`infra/openapi/examples/validation-error.json` (errore funzionale,
`POST /documenti/valida`) sono i primi due esempi validati contro lo schema OpenAPI
reale della `001` (FR-042). Solo dati demo, nessun segreto o dato reale.

## Link

- [API readiness generata](spec-kit/api-readiness.md)
- [Catalogo OpenAPI 001](spec-kit/specs/001-catalogo-contratto-geban/contracts/geban-catalog-api.openapi.yaml)
- [Project map](project-map.md)

I seguenti percorsi vivono fuori dalla cartella `docs/` pubblicata dal sito (fanno
parte del repository, non della documentazione generata): `infra/openapi/README.md`
(inventario contratti e pubblicazione Swagger/ReDoc), `infra/openapi/errors.md`
(catalogo errori funzionali), `infra/openapi/examples/catalog-success.json` ed
`infra/openapi/examples/validation-error.json` (esempi pubblicabili).
