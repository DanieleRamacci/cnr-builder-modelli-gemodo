<!-- CODEGRAPH_START -->
## CodeGraph

In repositories indexed by CodeGraph (a `.codegraph/` directory exists at the repo root), reach for it BEFORE grep/find or reading files when you need to understand or locate code:

- **MCP tool** (when available): `codegraph_explore` answers most code questions in one call — the relevant symbols' verbatim source plus the call paths between them, including dynamic-dispatch hops grep can't follow. Name a file or symbol in the query to read its current line-numbered source. If it's listed but deferred, load it by name via tool search.
- **Shell** (always works): `codegraph explore "<symbol names or question>"` prints the same output.

If there is no `.codegraph/` directory, skip CodeGraph entirely — indexing is the user's decision.
<!-- CODEGRAPH_END -->

## Contratto dati e discovery

Prima di leggere, modificare o spiegare il discovery, i campi del contratto dati o la validazione dei `dati`, consultare `docs/contratto-dati.md`: e' il riferimento unico (grammatica, conformita', flessibilita', campi ripetibili 0.8.0 proposti dalla spec 014). Tenere distinta la versione attiva (`VERSIONE_CONTRATTO_DISCOVERY` in `backend/app/discovery/schemas.py`) da quella proposta.
