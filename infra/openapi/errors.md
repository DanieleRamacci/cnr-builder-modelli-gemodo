# Catalogo Errori Funzionali

Elenco stabile dei codici errore pubblici esposti dalle API GEMODO verso GEBAN e altri
sistemi richiedenti (`CatalogoErroriFunzionali`, `backend/app/quality/schemas.py`). Ogni
riga e' referenziabile da un contratto OpenAPI tramite `catalogo_errori_ref` (vedi
`infra/openapi/README.md`) e dagli scenari end-to-end del mock GEBAN
(`mock-geban/scenarios/`).

I messaggi pubblici sono sanificati: nessuno stack trace, segreto o dettaglio tecnico
interno (FR-045). Il payload di errore segue la forma gia' definita dal contratto
`001-catalogo-contratto-geban` (`ErrorResponse { codice, messaggio }`,
`ErroreValidazione { campo, codice, messaggio }`).

| Codice | HTTP status | Api scope | Messaggio pubblico | Condizione | Azione suggerita | Audit | Spec owner |
|---|---|---|---|---|---|---|---|
| `CAMPO_OBBLIGATORIO_MANCANTE` | 400 | GEBAN | Campo obbligatorio mancante nel payload | Un campo richiesto dal contratto dati del modello non e' presente o e' vuoto | Verificare i campi richiesti restituiti da `GET /catalogo/modelli/{id}/campi-richiesti` | No | `001-catalogo-contratto-geban` |
| `TIPOLOGIA_SOL_NON_VALIDA` | 400 | GEBAN | Tipologia bando non riconosciuta | Il codice tipologia inviato non corrisponde a una tipologia SOL supportata (TDPNRR, CD, DIR, TD, CP, RS, CATP, TI, SDIP, MOB) | Usare uno dei codici tipologia pubblicati nel catalogo | No | `001-catalogo-contratto-geban` |
| `CAMPI_INGLESI_MANCANTI` | 400 | GEBAN | Campi inglesi mancanti per bando in lingua inglese | `Bando Inglese` e' `Si` ma mancano uno o piu' campi inglesi richiesti dal modello | Inviare i campi inglesi indicati a video dall'utente insieme al payload | No | `001-catalogo-contratto-geban` |
| `MODELLO_NON_TROVATO` | 404 | GEBAN | Modello o versione non trovati o non pubblicati | `modello_versione_id` non esiste o non e' in stato `PUBBLICATO` alla data richiesta | Richiedere nuovamente il catalogo modelli validi alla data di inserimento | No | `002-builder-modelli` |
| `GENERAZIONE_CONFLITTO_IDEMPOTENTE` | 409 | GEBAN | Richiesta in conflitto con una generazione esistente | Stessa chiave di idempotenza (sistema richiedente, external context id, model version id, tipo output) ma dati divergenti da una generazione gia' registrata | Verificare i dati inviati o usare una nuova chiave se si tratta di un nuovo bando/ribando | Si | `005-storage-idempotenza-consultazione` |
| `GENERAZIONE_FALLITA` | 422 | GEBAN | Generazione documento non completata | Il rendering PDF o la validazione server-side non sono andati a buon fine | Consultare lo stato generazione; ripetere la richiesta dopo la correzione | Si | `004-generazione-documenti-pdf` |
| `DOCUMENTO_NON_DISPONIBILE` | 404 | GEBAN | Documento non disponibile per il download | Il riferimento documentale non esiste, e' scaduto o la generazione non e' `COMPLETATA` | Consultare lo stato generazione prima di richiedere il download | No | `005-storage-idempotenza-consultazione` |
| `ACCESSO_NON_AUTENTICATO` | 401 | GEBAN, BUILDER, ADMIN | Token mancante o non valido | Il JWT Keycloak e' assente, scaduto o con firma/issuer/audience non validi | Ottenere un nuovo token dal client tecnico o dalla sessione SSO | Si | `006-sicurezza-autorizzazioni-audit` |
| `PROFILO_INTEGRAZIONE_NON_ABILITATO` | 403 | GEBAN | Client o profilo non abilitato per l'operazione richiesta | Il token e' valido ma il client/sistema richiedente non ha un profilo di integrazione GEMODO attivo che autorizza tipo documento, categoria, modello o operazione | Verificare il profilo di integrazione associato al sistema richiedente | Si | `006-sicurezza-autorizzazioni-audit` |
| `MODELLO_DOCUMENTALE_NON_VALIDO` | 422 | BUILDER, ADMIN | Struttura del modello documentale non valida | Il modello contiene HTML/CSS/script liberi, blocchi non ammessi, placeholder non presenti nel contratto dati o asset non referenziati correttamente | Correggere la struttura usando solo blocchi, stili, asset e placeholder ammessi | No | `003-sezioni-placeholder-versionamento` |

## Note

- Gli errori con `Audit: Si` devono generare un evento audit secondo
  `infra/local/audit-expectations.yaml` (introdotto dalla User Story 2).
- Nuovi codici errore vanno aggiunti qui **prima** di essere restituiti da un endpoint
  runtime, mantenendo coerenza con il relativo contratto OpenAPI (FR-040, FR-042).
