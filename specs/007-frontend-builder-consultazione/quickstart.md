# Quickstart: Frontend Builder E Consultazione (MVP ADR 0002)

Scenario end-to-end che prova che l'MVP funziona per davvero: un admin
registra e verifica un'integrazione contro un servizio discovery reale
(`mock-geban`), poi un manager naviga la struttura scoperta e crea un
modello di test in BOZZA - lo stesso flusso descritto dall'utente come
obiettivo di questo incremento.

## Prerequisiti

- Docker in esecuzione.
- `infra/local/compose.yaml` con almeno i servizi minimi di default
  (`postgres`, `backend`, `frontend`, `discovery-mock`) - vedi
  `infra/local/README.md` per l'avvio.
- Migrazioni Alembic applicate (`alembic upgrade head` dentro il servizio
  `backend`, o all'avvio se gia' automatizzato dal compose).
- Un utente/token Keycloak con ruolo `GEMODO_ADMIN` per lo scenario admin, e
  un token con `contexts.<contesto>.roles` che mappi a
  `GEMODO_MODELLI_GESTORE` nel contesto scelto per lo scenario manager
  (vedi `infra/local/integration-profiles.local.yaml`
  per i mapping reali gia' configurati, es. `ROLE_MANAGER#geban`).

## Setup

```bash
cd infra/local
docker compose up -d postgres backend frontend discovery-mock
# verifica che mock-geban esponga un endpoint discovery raggiungibile dal
# backend: http://discovery-mock/discovery
```

Apri `http://localhost:4200`.

Per il discovery locale configurare l'origine `http://discovery-mock:80`
in `GEMODO_INTEGRAZIONI_ALLOWLIST_PRIVATO` prima di avviare il backend.
Il servizio `discovery-mock` serve dati demo conformi al contratto ad
albero completo, non la proposta PER_NODI. Il runner `mock-geban` e' distinto.
Per il collaudo sul server seguire [frontend-server-test.md](../../docs/frontend-server-test.md).

## Scenario 1 - Admin registra e verifica un'integrazione

1. Accedi come utente `GEMODO_ADMIN`.
2. Nella schermata integrazioni, la tabella e' vuota al primo avvio (nessun
   seed - FR-021, coerente con `test_create_starts_disconnected_and_rejects_
   duplicate_code`).
3. Crea una nuova integrazione: codice, nome, `codice_contesto` (es.
   `geban`). **Atteso**: appare in lista con stato "Non verificato"
   (`DEFINITO`), nessun URL configurato.
4. Configura l'URL discovery di `mock-geban` (deve rientrare
   nell'allowlist di deployment - vedi `GEMODO_INTEGRAZIONI_ALLOWLIST`/
   `_PRIVATO` nel compose locale). **Atteso**: un URL non in allowlist mostra
   `422 DESTINAZIONE_NON_APPROVATA` in modo comprensibile, non un errore
   generico.
5. Avvia la verifica. **Atteso**: dopo la chiamata (sincrona, puo' richiedere
   fino al `timeout_ms` configurato) lo stato passa a "Connesso" con
   data/versione contratto visibili, oppure a "Errore" con i motivi
   sanificati se `mock-geban` non risponde nella forma attesa.

## Scenario 2 - Manager naviga e crea un modello di test

1. Accedi come utente con ruolo GESTORE nel contesto dell'integrazione appena
   connessa.
2. Nella schermata builder, l'integrazione connessa e autorizzata per il
   proprio contesto e' visibile in lista (e **solo** quella - vedi
   `test_manager_sees_only_connected_integrations_authorized_in_their_
   context` e `test_multicontext_token_does_not_leak_permission_across_
   contexts`).
3. Naviga l'albero (tipologia → profilo → campi, o qualunque forma
   restituita) fino a una foglia.
4. Crea un modello di test: codice, nome, variante. **Atteso**: risposta
   `201` con lo stato `BOZZA`; nessun editor di campi/sezioni si apre (fuori
   scope, vedi `plan.md`).
5. Prosegui da Swagger (`/docs/builder-modelli`, una volta chiuso il gap
   Foundational descritto in `research.md`) per versione/pubblicazione, poi
   `/docs/generazione-documenti` per generare e scaricare un PDF di test -
   la stessa prova end-to-end gia' fatta a livello API in
   `backend/tests/builder/test_builder_flow_api.py::
   test_flusso_completo_creazione_pubblicazione_e_generazione_documento`,
   ora raggiungibile a partire dall'interfaccia invece che solo da Swagger.

## Esito atteso

Entrambi gli scenari devono completarsi senza mai richiedere un intervento
diretto sul database o una chiamata Swagger per i passi coperti da questo
MVP (creazione/verifica integrazione, navigazione, creazione modello) - solo
i passi esplicitamente fuori scope (versione/pubblicazione/generazione)
restano su Swagger fino a un incremento futuro.
