<!-- CODEGRAPH_START -->
## CodeGraph

In repositories indexed by CodeGraph (a `.codegraph/` directory exists at the repo root), reach for it BEFORE grep/find or reading files when you need to understand or locate code:

- **MCP tool** (when available): `codegraph_explore` answers most code questions in one call — the relevant symbols' verbatim source plus the call paths between them, including dynamic-dispatch hops grep can't follow. Name a file or symbol in the query to read its current line-numbered source. If it's listed but deferred, load it by name via tool search.
- **Shell** (always works): `codegraph explore "<symbol names or question>"` prints the same output.

If there is no `.codegraph/` directory, skip CodeGraph entirely — indexing is the user's decision.
<!-- CODEGRAPH_END -->

## Documentazione di riferimento

Le pagine in `docs/` descrivono il sistema per integratori, utenti e agenti. Prima di lavorare su un'area, leggere la pagina corrispondente:

- `docs/architettura.md`: componenti, concetti, cosa e' conservato e cosa e' letto dal vivo, modularita', sicurezza, limiti noti.
- `docs/contratto-dati.md`: discovery (un discovery per integrazione, con piu' tipi documento), campi, conformita', validazione dei dati, campi ripetibili 0.8.0 proposti (spec 014).
- `docs/integrazione-sistema-esterno.md`: flusso generico per un sistema esterno.
- `docs/riferimento-api.md`: tutte le rotte con permessi e contratti OpenAPI, codici di errore, lacune note.
- `docs/casi/geban.md`: valori concreti di GEBAN (prima integrazione).

Regole:

- **Il codice prevale sulla documentazione.** Prima di affermare un comportamento, verificarlo nel codice; la versione attiva del contratto discovery e' `VERSIONE_CONTRATTO_DISCOVERY` in `backend/app/discovery/schemas.py`.
- **Se codice e documentazione divergono, la pagina si corregge nello stesso lavoro.** `backend/tests/contract/test_documentazione_allineata.py` confronta con il codice rotte, contratti, codici di errore, esempi di discovery, versione attiva, stati e profilo GEBAN; `cd frontend && npm run docs:check` verifica che la copia mostrata nell'app sia allineata e che i link interni funzionino (dopo una modifica a `docs/`: `npm run docs:sync`).
