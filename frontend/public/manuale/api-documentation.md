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

## Stato Attuale (2026-09-22)

Tutti i contratti del flusso verso un sistema esterno sono pubblicati e serviti
da `/docs`:

- `001-catalogo-contratto-geban`: ricerca modelli, campi richiesti, validazione.
- `004-generazione-documenti-pdf`: generazione reale del documento.
- `005-storage-idempotenza-consultazione`: stato e download.
- `010-configurazione-cataloghi-integrazioni`: forma dell'endpoint di discovery
  che il sistema esterno deve esporre, piu' i contratti amministrativi.
- `002-builder-modelli`: API del builder, non destinate a sistemi esterni.
- `009-fondamenta-mock-test-qualita` governa readiness, esempi, mock e gate.

**Per integrare un sistema esterno partire da
[API per un sistema esterno](api-per-geban.md)**, non da questa pagina: qui
stanno le regole di progetto sulla documentazione, li' il flusso concreto.

## API MVP Da Coprire

Requisito soddisfatto: generazione, stato e download hanno contratto, esempi,
errori funzionali, autenticazione, autorizzazioni e comportamento idempotente
documentati e coperti da test. Le rotte reali sono
`POST /documenti/genera`, `GET /documenti/{riferimento}` e
`GET /documenti/{riferimento}/download` (non `generazioni/{id}`, forma mai
implementata).

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

- [API per un sistema esterno](api-per-geban.md)
- [Indice interattivo dei contratti](/docs) (backend in esecuzione)
- [API readiness generata](spec-kit/api-readiness.md)
- [Catalogo OpenAPI 001](spec-kit/specs/001-catalogo-contratto-geban/contracts/geban-catalog-api.openapi.yaml)
- [Project map](project-map.md)

I seguenti percorsi vivono fuori dalla cartella `docs/` pubblicata dal sito (fanno
parte del repository, non della documentazione generata): `infra/openapi/README.md`
(inventario contratti e pubblicazione Swagger/ReDoc), `infra/openapi/errors.md`
(catalogo errori funzionali), `infra/openapi/examples/catalog-success.json` ed
`infra/openapi/examples/validation-error.json` (esempi pubblicabili).
